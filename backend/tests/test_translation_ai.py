from time import perf_counter

import pytest
from sqlalchemy import insert, select

from app.api.profile_extraction import ensure_initial_revision
from app.core.config import Settings
from app.models.entities import AuditEvent
from app.models.translation import TranslationExample
from app.models.translation_ai import AIInvocation
from app.translation_ai.policy import AIProcessingPolicy
from app.schemas.translation_ai import TranslationRetrievalRequest
from app.translation_ai.prompt import PromptPackage, TranslationPromptBuilder
from app.translation_ai.provider import AzureOpenAITranslationProvider, DisabledTranslationProvider, MockTranslationProvider, TranslationAIError, get_translation_provider
from app.translation_ai.retrieval import TranslationRetrievalService
from app.ai.governance import AIGovernanceViolation


def create_pair(client, db, machine, *, name="Synthetic spindle pair", post="REV-12", allowed=True, verified=True, cl="SPINDL/RPM,800,CLW", gc="S800 M03"):
    revision = ensure_initial_revision(machine, db); db.commit()
    row = client.post("/api/translations", json={
        "machine_profile_id": machine.id, "machine_profile_revision_id": revision.id,
        "name": name, "post_processor_name": "Synthetic Post", "post_processor_revision": post,
        "operation_type": "turning", "cl_source_text": cl, "gcode_source_text": gc,
        "source_provenance": "Synthetic Phase 10 fixture", "ai_processing_allowed": False,
    }).json()
    stored = db.get(TranslationExample, row["id"]); stored.verification_status = "verified_successful" if verified else "candidate"; stored.ai_processing_allowed = allowed; db.commit()
    return stored, revision


def test_provider_factory_and_safe_status(client):
    assert isinstance(get_translation_provider(Settings(translation_ai_provider="mock")), MockTranslationProvider)
    assert isinstance(get_translation_provider(Settings(translation_ai_provider="disabled")), DisabledTranslationProvider)
    assert isinstance(get_translation_provider(Settings(translation_ai_provider="azure_openai")), AzureOpenAITranslationProvider)
    response = client.get("/api/ai/translation/provider-status")
    assert response.status_code == 200
    body = response.json(); assert body["provider"] == "mock" and body["public_web"] is False and body["external_processing"] is False
    assert "api_key" not in body and "endpoint" not in body and "token" not in body


def test_retrieval_filters_consent_status_machine_post_and_never_calls_ai(client, db_session, machine_profile, monkeypatch):
    allowed, revision = create_pair(client, db_session, machine_profile)
    create_pair(client, db_session, machine_profile, name="Candidate excluded", allowed=True, verified=False, cl="SPINDL/RPM,900,CLW", gc="S900 M03")
    create_pair(client, db_session, machine_profile, name="No consent excluded", allowed=False, cl="SPINDL/RPM,1000,CLW", gc="S1000 M03")
    called = False
    def forbidden(*_args, **_kwargs):
        nonlocal called; called = True; raise AssertionError("provider must not run during retrieval")
    monkeypatch.setattr(MockTranslationProvider, "explain_translation", forbidden)
    response = client.post("/api/ai/translation/retrieve", json={"machine_profile_id": machine_profile.id, "machine_profile_revision_id": revision.id, "post_processor_revision": "REV-12", "operation_type": "turning", "cl_text": "SPINDL/RPM,1200,CLW"})
    assert response.status_code == 200, response.text
    result = response.json(); assert [item["example_id"] for item in result["examples"]] == [allowed.id]
    assert result["retrieval_scope"] == "exact_machine_exact_post" and result["ai_called"] is False and called is False


def test_revision_and_post_fallback_are_explicit(client, db_session, machine_profile):
    row, revision = create_pair(client, db_session, machine_profile, post="OLD-POST")
    strict = client.post("/api/ai/translation/retrieve", json={"machine_profile_id": machine_profile.id, "machine_profile_revision_id": revision.id, "post_processor_revision": "NEW-POST", "cl_text": "SPINDL/RPM,1200,CLW"}).json()
    assert strict["examples"] == []
    widened = client.post("/api/ai/translation/retrieve", json={"machine_profile_id": machine_profile.id, "machine_profile_revision_id": revision.id, "post_processor_revision": "NEW-POST", "cl_text": "SPINDL/RPM,1200,CLW", "allow_revision_fallback": True}).json()
    assert widened["examples"][0]["example_id"] == row.id and widened["retrieval_scope"] == "same_machine_cross_post"


@pytest.mark.parametrize("status", ["candidate", "invalid", "deprecated"])
def test_unverified_lifecycle_statuses_never_enter_retrieval(client, db_session, machine_profile, status):
    row, revision = create_pair(client, db_session, machine_profile, name=f"Excluded {status}", cl=f"SPINDL/RPM,{700 + len(status)},CLW", gc=f"S{700 + len(status)} M03")
    row.verification_status = status; db_session.commit()
    result = client.post("/api/ai/translation/retrieve", json={"machine_profile_id": machine_profile.id, "machine_profile_revision_id": revision.id, "post_processor_revision": "REV-12", "cl_text": "SPINDL/RPM,1200,CLW"}).json()
    assert row.id not in {item["example_id"] for item in result["examples"]}


def test_cross_machine_examples_are_excluded_without_explicit_fallback(client, db_session, machine_profile):
    other_data = client.post("/api/machines", json={"name":"Other synthetic machine","manufacturer":"F","model":"M","controller_name":"Fanuc-style","machine_type":"mill","axis_count":3,"supported_work_offsets":["G54"],"approved_g_codes":[],"approved_m_codes":[],"restricted_commands":[]}).json()
    from app.models.entities import MachineProfile
    other = db_session.get(MachineProfile, other_data["id"])
    other_row, _ = create_pair(client, db_session, other, name="Other machine pair")
    own_row, revision = create_pair(client, db_session, machine_profile, name="Exact machine pair", cl="SPINDL/RPM,801,CLW", gc="S801 M03")
    result = client.post("/api/ai/translation/retrieve", json={"machine_profile_id": machine_profile.id, "machine_profile_revision_id": revision.id, "cl_text":"SPINDL/RPM,1200,CLW"}).json()
    ids = {item["example_id"] for item in result["examples"]}
    assert own_row.id in ids and other_row.id not in ids


def test_cross_machine_fallback_is_explicit_and_uses_authoritative_controller(client, db_session, machine_profile):
    from app.models.entities import MachineProfile
    other_data = client.post("/api/machines", json={"name":"Same controller fallback machine","manufacturer":"F","model":"M","controller_name":machine_profile.controller_name,"machine_type":"mill","axis_count":3,"supported_work_offsets":["G54"],"approved_g_codes":[],"approved_m_codes":[],"restricted_commands":[]}).json()
    other = db_session.get(MachineProfile, other_data["id"])
    other_row, _ = create_pair(client, db_session, other, name="Controller-family pair")
    revision = ensure_initial_revision(machine_profile, db_session); db_session.commit()
    result = client.post("/api/ai/translation/retrieve", json={"machine_profile_id": machine_profile.id, "machine_profile_revision_id": revision.id, "controller_name": "caller-supplied-wrong-value", "cl_text":"SPINDL/RPM,1200,CLW", "allow_machine_family_fallback": True, "allow_revision_fallback": True}).json()
    assert other_row.id in {item["example_id"] for item in result["examples"]}
    assert result["examples"][0]["machine"] == other.name
    assert any("authoritative" in warning for warning in result["warnings"])


def test_policy_and_prompt_data_minimization(client, db_session, machine_profile):
    row, revision = create_pair(client, db_session, machine_profile)
    decision = AIProcessingPolicy().example_allowed(row, machine_profile.id); assert decision.allowed
    package = TranslationPromptBuilder().build(machine=machine_profile, revision_id=revision.id, cl_text="SPINDL/RPM,1200,CLW", examples=[row])
    assert str(row.id) in package.user and "SPINDL/RPM,800,CLW" in package.user
    assert row.cl_source_hash not in package.user and "source_provenance" not in package.user and "original_filename" not in package.user
    row.ai_processing_allowed = False
    assert AIProcessingPolicy().example_allowed(row, machine_profile.id).reason_code == "AI_PROCESSING_NOT_ALLOWED"


def test_mock_explanation_is_retired_before_prompt_or_invocation(client, db_session, machine_profile):
    row, revision = create_pair(client, db_session, machine_profile)
    payload = {"retrieval": {"machine_profile_id": machine_profile.id, "machine_profile_revision_id": revision.id, "post_processor_revision": "REV-12", "operation_type": "turning", "cl_text": "SPINDL / RPM,1200,CLW"}, "example_ids": [row.id]}
    response = client.post("/api/ai/translation/explain", json=payload)
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "AI_CL_NCL_TRANSMISSION_PROHIBITED"
    assert db_session.scalar(select(AIInvocation)) is None
    assert db_session.scalar(select(AuditEvent).where(AuditEvent.event_type == "translation_ai_request_blocked_by_policy"))


def test_policy_block_prevents_provider_and_prompt_for_nonconsented_example(client, db_session, machine_profile, monkeypatch):
    row, revision = create_pair(client, db_session, machine_profile, allowed=False)
    monkeypatch.setattr(TranslationPromptBuilder, "build", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("prompt builder must not run")))
    monkeypatch.setattr(MockTranslationProvider, "explain_translation", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("provider must not run")))
    response = client.post("/api/ai/translation/explain", json={"retrieval": {"machine_profile_id": machine_profile.id, "machine_profile_revision_id": revision.id, "cl_text": "SPINDL/RPM,1200,CLW"}, "example_ids": [row.id]})
    assert response.status_code == 410 and response.json()["detail"]["code"] == "AI_CL_NCL_TRANSMISSION_PROHIBITED"


def test_explanation_rejects_example_outside_current_retrieval_scope(client, db_session, machine_profile, monkeypatch):
    eligible, revision = create_pair(client, db_session, machine_profile, post="CURRENT")
    excluded, _ = create_pair(client, db_session, machine_profile, name="Old post", post="OLD", cl="SPINDL/RPM,900,CLW", gc="S900 M03")
    monkeypatch.setattr(MockTranslationProvider, "explain_translation", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("provider must not run")))
    response = client.post("/api/ai/translation/explain", json={"retrieval": {"machine_profile_id": machine_profile.id, "machine_profile_revision_id": revision.id, "post_processor_revision": "CURRENT", "cl_text": "SPINDL/RPM,1200,CLW"}, "example_ids": [excluded.id]})
    assert eligible.id != excluded.id
    assert response.status_code == 410 and response.json()["detail"]["code"] == "AI_CL_NCL_TRANSMISSION_PROHIBITED"


def test_individual_consent_requires_acknowledgement_and_audits(client, db_session, machine_profile):
    row, _ = create_pair(client, db_session, machine_profile, allowed=False)
    original = {"cl": row.cl_source_text, "gcode": row.gcode_source_text, "cl_hash": row.cl_source_hash, "gcode_hash": row.gcode_source_hash, "revision": row.machine_profile_revision_id, "status": row.verification_status}
    blank = client.post(f"/api/translations/{row.id}/ai-processing-consent", json={"allowed": True, "reviewer_label": "", "acknowledgement": True})
    assert blank.status_code == 422
    denied = client.post(f"/api/translations/{row.id}/ai-processing-consent", json={"allowed": True, "reviewer_label": "Reviewer", "acknowledgement": False})
    assert denied.status_code == 422
    enabled = client.post(f"/api/translations/{row.id}/ai-processing-consent", json={"allowed": True, "reviewer_label": "R&D Test Reviewer", "acknowledgement": True, "note": "Approved for controlled excerpts."})
    assert enabled.status_code == 200 and enabled.json()["ai_processing_allowed"] is True
    db_session.refresh(row)
    assert {"cl": row.cl_source_text, "gcode": row.gcode_source_text, "cl_hash": row.cl_source_hash, "gcode_hash": row.gcode_source_hash, "revision": row.machine_profile_revision_id, "status": row.verification_status} == original
    event = db_session.scalar(select(AuditEvent).where(AuditEvent.event_type == "translation_ai_consent_enabled")); assert event.metadata_json["allowed"] is True and event.metadata_json["reviewer_label"] == "R&D Test Reviewer"
    eligible = client.post("/api/ai/translation/retrieve", json={"machine_profile_id": machine_profile.id, "machine_profile_revision_id": row.machine_profile_revision_id, "post_processor_revision": row.post_processor_revision, "operation_type": row.operation_type, "cl_text": "SPINDL/RPM,1200,CLW"}).json()
    assert row.id in {item["example_id"] for item in eligible["examples"]}
    no_confirmation = client.post(f"/api/translations/{row.id}/ai-processing-consent", json={"allowed": False, "reviewer_label": "R&D Test Reviewer", "acknowledgement": False})
    assert no_confirmation.status_code == 422
    disabled = client.post(f"/api/translations/{row.id}/ai-processing-consent", json={"allowed": False, "reviewer_label": "R&D Test Reviewer", "acknowledgement": True})
    assert disabled.status_code == 200 and disabled.json()["ai_processing_allowed"] is False
    assert db_session.scalar(select(AuditEvent).where(AuditEvent.event_type == "translation_ai_consent_disabled"))
    ineligible = client.post("/api/ai/translation/retrieve", json={"machine_profile_id": machine_profile.id, "machine_profile_revision_id": row.machine_profile_revision_id, "post_processor_revision": row.post_processor_revision, "operation_type": row.operation_type, "cl_text": "SPINDL/RPM,1200,CLW"}).json()
    assert row.id not in {item["example_id"] for item in ineligible["examples"]}


def test_unverified_example_cannot_enable_ai_consent(client, db_session, machine_profile):
    row, _ = create_pair(client, db_session, machine_profile, allowed=False, verified=False)
    response = client.post(f"/api/translations/{row.id}/ai-processing-consent", json={"allowed": True, "reviewer_label": "Reviewer", "acknowledgement": True})
    assert response.status_code == 409 and db_session.get(TranslationExample, row.id).ai_processing_allowed is False


def test_azure_failures_are_typed_and_redacted():
    class RateLimit(Exception): status_code = 429
    class Auth(Exception): status_code = 401
    assert AzureOpenAITranslationProvider._safe_error(RateLimit("secret-key-value")).code == "PROVIDER_RATE_LIMITED"
    error = AzureOpenAITranslationProvider._safe_error(Auth("secret-key-value"))
    assert error.code == "PROVIDER_AUTHENTICATION_FAILED" and "secret-key-value" not in error.safe_message
    class Timeout(Exception): pass
    class Service(Exception): status_code = 503
    class Content(Exception): code = "content_filter"
    assert AzureOpenAITranslationProvider._safe_error(Timeout("secret")).code == "PROVIDER_TIMEOUT"
    assert AzureOpenAITranslationProvider._safe_error(Service("secret")).retryable
    assert AzureOpenAITranslationProvider._safe_error(Content("secret")).code == "PROVIDER_CONTENT_FILTERED"


def test_azure_translation_provider_blocks_cl_before_transport(monkeypatch):
    settings = Settings(translation_ai_provider="azure_openai", azure_openai_endpoint="https://example.openai.azure.com", azure_openai_deployment="synthetic")
    provider = AzureOpenAITranslationProvider(settings)
    class Response: output_text = "not-json"
    class Responses:
        @staticmethod
        def create(**_kwargs): return Response()
    class Client: responses = Responses()
    monkeypatch.setattr(provider, "_client", lambda: Client())
    with pytest.raises(AIGovernanceViolation) as raised:
        provider.explain_translation(PromptPackage("system", "user", [1]), "SPINDL/RPM,1200,CLW")
    assert raised.value.code == "AI_CL_NCL_TRANSMISSION_PROHIBITED"


def test_azure_translation_provider_never_reaches_content_filter_transport(monkeypatch):
    settings = Settings(translation_ai_provider="azure_openai", azure_openai_endpoint="https://example.openai.azure.com", azure_openai_deployment="synthetic")
    provider = AzureOpenAITranslationProvider(settings)
    class Error: code = "content_filter"
    class Response: error = Error(); incomplete_details = None; output_text = ""
    class Responses:
        @staticmethod
        def create(**_kwargs): return Response()
    class Client: responses = Responses()
    monkeypatch.setattr(provider, "_client", lambda: Client())
    with pytest.raises(AIGovernanceViolation) as raised:
        provider.explain_translation(PromptPackage("system", "user", [1]), "SPINDL/RPM,1200,CLW")
    assert raised.value.code == "AI_CL_NCL_TRANSMISSION_PROHIBITED"


@pytest.mark.parametrize("count", [10, 100, 1_000, 10_000])
def test_retrieval_scales_without_embeddings(db_session, machine_profile, count):
    revision = ensure_initial_revision(machine_profile, db_session); db_session.commit()
    rows = [{
        "machine_profile_id": machine_profile.id, "machine_profile_revision_id": revision.id,
        "name": f"Synthetic retrieval {index}", "post_processor_name": "Synthetic Post", "post_processor_revision": "PERF-1",
        "operation_type": "turning", "cl_source_text": f"SPINDL/RPM,{800 + index},CLW", "cl_source_hash": f"{index + 1:064x}",
        "gcode_source_text": f"S{800 + index} M03", "gcode_source_hash": f"{index + 20_001:064x}",
        "verification_status": "verified_successful", "machine_context_snapshot_json": {}, "tooling_context_json": {}, "setup_context_json": {},
        "cl_parse_summary_json": {}, "gcode_parse_summary_json": {}, "parsed_cl_records_json": [], "parsed_gcode_blocks_json": [],
        "validation_summary_json": {}, "ai_processing_allowed": True,
    } for index in range(count)]
    db_session.execute(insert(TranslationExample), rows); db_session.commit()
    start = perf_counter(); result = TranslationRetrievalService(db_session).retrieve(TranslationRetrievalRequest(machine_profile_id=machine_profile.id, machine_profile_revision_id=revision.id, post_processor_revision="PERF-1", operation_type="turning", cl_text="SPINDL/RPM,1200,CLW", max_examples=5)); elapsed = perf_counter() - start
    assert len(result.examples) == 5 and result.ai_called is False and elapsed < 5

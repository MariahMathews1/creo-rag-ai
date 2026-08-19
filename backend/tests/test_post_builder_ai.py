import pytest
from sqlalchemy import select

from app.ai.governance import AIGovernanceViolation, CL_NCL_EXTERNAL_AI_ALLOWED, enforce_post_builder_ai_policy
from app.api.profile_extraction import ensure_initial_revision
from app.core.config import Settings
from app.models.entities import DocumentType, ProcessingStatus, SourceDocument
from app.models.translation_ai import AIInvocation
from app.post_builder_ai.provider import AzureOpenAIPostBuilderProvider, DisabledPostBuilderProvider, MockPostBuilderProvider, get_post_builder_provider


def request(machine_id: int, revision_id: int, **extra):
    return {"machine_profile_id": machine_id, "machine_profile_revision_id": revision_id, "selected_post_section": "spindle", **extra}


def test_central_policy_rejects_cl_ncl_part_geometry_and_toolpath():
    assert CL_NCL_EXTERNAL_AI_ALLOWED is False
    for payload, code in [
        ({"cl_text": "SPINDL/RPM,1200,CLW"}, "AI_CL_NCL_TRANSMISSION_PROHIBITED"),
        ({"notes": "GOTO/1.0,2.0,3.0"}, "AI_CL_NCL_TRANSMISSION_PROHIBITED"),
        ({"part_geometry": {"diameter": 1}}, "AI_PART_SPECIFIC_DATA_PROHIBITED"),
        ({"toolpath": [{"x": 1}]}, "AI_PART_SPECIFIC_DATA_PROHIBITED"),
    ]:
        with pytest.raises(AIGovernanceViolation) as raised: enforce_post_builder_ai_policy(payload)
        assert raised.value.code == code


def test_provider_factory_uses_separate_post_builder_contract():
    assert isinstance(get_post_builder_provider(Settings(post_builder_ai_provider="mock")), MockPostBuilderProvider)
    assert isinstance(get_post_builder_provider(Settings(post_builder_ai_provider="disabled")), DisabledPostBuilderProvider)
    provider = get_post_builder_provider(Settings(post_builder_ai_provider="azure_openai"))
    assert isinstance(provider, AzureOpenAIPostBuilderProvider)
    assert not hasattr(provider, "translate_cl") and not hasattr(provider, "generate_gcode")


def test_machine_profile_is_allowed_and_mock_response_is_draft_audited(client, db_session, machine_profile):
    revision = ensure_initial_revision(machine_profile, db_session)
    revision.max_spindle_rpm = 2400; revision.approved_m_codes_json = ["M03", "M04", "M05"]
    db_session.commit()
    response = client.post("/api/ai/post-builder/sections/draft", json=request(machine_profile.id, revision.id))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["section_key"] == "spindle" and body["advisory_only"] is True
    assert all(rule["review_status"] == "draft" for rule in body["draft_rules"])
    invocation = db_session.scalar(select(AIInvocation).where(AIInvocation.operation_type == "post_builder_section"))
    assert invocation and invocation.translation_example_ids_json == [] and invocation.input_hash
    assert invocation.provider_metadata_json["section"] == "spindle"


def test_approved_machine_document_excerpt_is_allowed(client, db_session, machine_profile):
    revision = ensure_initial_revision(machine_profile, db_session)
    document = SourceDocument(machine_profile_id=machine_profile.id, title="Synthetic controller manual", document_type=DocumentType.CONTROLLER_MANUAL,
        extracted_text="M03 starts the spindle clockwise.", processing_status=ProcessingStatus.READY)
    db_session.add(document); db_session.commit()
    response = client.post("/api/ai/post-builder/sections/draft", json=request(machine_profile.id, revision.id,
        relevant_document_excerpts=[{"document_id": document.id, "excerpt": "M03 starts the spindle clockwise.", "page": 84, "external_processing_approved": True}]))
    assert response.status_code == 200, response.text
    assert response.json()["source_reference_ids"] == [document.id]


@pytest.mark.parametrize("field,value,code", [
    ("cl_text", "LOADTL/1", "AI_CL_NCL_TRANSMISSION_PROHIBITED"),
    ("ncl_text", "FROM/0,0,0", "AI_CL_NCL_TRANSMISSION_PROHIBITED"),
    ("part_geometry", {"x": 1}, "AI_PART_SPECIFIC_DATA_PROHIBITED"),
    ("toolpath", [{"x": 1, "z": 2}], "AI_PART_SPECIFIC_DATA_PROHIBITED"),
])
def test_post_builder_endpoint_rejects_sensitive_fields_before_provider(client, db_session, machine_profile, monkeypatch, field, value, code):
    revision = ensure_initial_revision(machine_profile, db_session); db_session.commit()
    monkeypatch.setattr(MockPostBuilderProvider, "draft_post_section", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("provider must not run")))
    response = client.post("/api/ai/post-builder/sections/draft", json=request(machine_profile.id, revision.id, **{field: value}))
    assert response.status_code == 422 and response.json()["detail"]["code"] == code


def test_legacy_translation_ai_endpoint_is_gone_even_with_consent(client, db_session, machine_profile):
    revision = ensure_initial_revision(machine_profile, db_session); db_session.commit()
    response = client.post("/api/ai/translation/explain", json={"retrieval": {"machine_profile_id": machine_profile.id, "machine_profile_revision_id": revision.id, "cl_text": "SPINDL/RPM,1200,CLW"}, "example_ids": [1]})
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "AI_CL_NCL_TRANSMISSION_PROHIBITED"


def test_post_builder_provider_status_exposes_policy(client):
    body = client.get("/api/ai/post-builder/provider-status").json()
    assert body["provider"] == "mock" and body["cl_ncl_ai_access"] == "prohibited" and body["public_web"] is False

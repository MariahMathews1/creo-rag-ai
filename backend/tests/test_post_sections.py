import pytest
from sqlalchemy import select

from app.api.profile_extraction import ensure_initial_revision
from app.models.entities import AuditEvent, DocumentChunk, DocumentType, ProcessingStatus, SourceDocument
from app.models.gpost import GPostDraftVersion, PostSectionDraft
from app.models.translation_ai import AIInvocation
from app.post_builder_ai.provider import MockPostBuilderProvider, PostBuilderProviderResult


def setup_phase11(client, db, machine, *, evidence_text="Spindle clockwise M03, counterclockwise M04, stop M05. Maximum RPM 10000."):
    revision = ensure_initial_revision(machine, db); revision.status = "approved"; revision.approved_at = revision.created_at; db.commit()
    document = SourceDocument(machine_profile_id=machine.id, title="FICTIONAL Controller Manual", document_type=DocumentType.CONTROLLER_MANUAL,
        processing_status=ProcessingStatus.READY, extracted_text=evidence_text)
    db.add(document); db.flush()
    chunk = DocumentChunk(document_id=document.id, machine_profile_id=machine.id, chunk_index=0, page_start=84, page_end=84,
        section_title="Spindle Control", content=evidence_text, content_hash="9" * 64, token_estimate=20)
    db.add(chunk); db.commit()
    policy = client.post(f"/api/documents/{document.id}/post-builder-ai-policy", json={"allowed": True, "reviewer_label": "R&D Reviewer", "acknowledgement": True})
    assert policy.status_code == 200 and policy.json()["ai_post_builder_allowed"] is True
    draft = client.post(f"/api/machines/{machine.id}/gpost-drafts", json={"machine_profile_revision_id": revision.id,
        "name": "Fictional Phase 11 Post", "controller_family": "fanuc_mill", "selected_document_ids": [document.id], "reference_program_ids": []}).json()
    return revision, document, chunk, draft


def test_contextual_readiness_and_deterministic_evidence(client, db_session, machine_profile):
    _, document, chunk, draft = setup_phase11(client, db_session, machine_profile)
    rows = client.get(f"/api/post-builder/{draft['id']}/readiness").json()
    by_key = {row["section_key"]: row for row in rows}
    assert by_key["spindle"]["readiness"] in {"ready", "ready_with_review"}
    assert by_key["cycles"]["readiness"] == "deferred" and by_key["cycles"]["draft_allowed"] is False
    assert by_key["spindle"]["known_machine_facts"] != by_key["tooling"]["known_machine_facts"]
    evidence = client.post(f"/api/post-builder/{draft['id']}/sections/spindle/retrieve-evidence", json={}).json()
    assert evidence[0]["evidence_id"] == chunk.id and evidence[0]["document_id"] == document.id
    assert evidence[0]["ai_eligible"] is True and "spindle" in evidence[0]["matched_terms"]
    assembled = client.get(f"/api/post-builder/{draft['id']}/assembled").json()
    assert assembled["status"] in {"setup", "needs_information"}
    assert assembled["required_area_count"] == 8
    assert len(assembled["components"]) == 9
    assert next(item for item in assembled["components"] if item["section_key"] == "cycles")["state"] == "deferred"
    assert assembled["native_gpost_export"] == "not_configured"


def test_spindle_draft_review_version_and_whole_post_snapshot(client, db_session, machine_profile):
    _, _, chunk, draft = setup_phase11(client, db_session, machine_profile)
    route = f"/api/post-builder/{draft['id']}/sections/spindle"
    response = client.post(f"{route}/draft", json={"evidence_ids": [chunk.id], "context_reviewed": True, "evidence_mode": "refresh"})
    assert response.status_code == 200, response.text
    first = response.json(); assert first["status"] == "needs_review" and first["section_version"] == 1
    assert {rule["rule_key"] for rule in first["rules"]} == {"spindle_clockwise_start", "spindle_counterclockwise_start", "spindle_stop"}
    assert all(rule["status"] == "needs_review" and rule["evidence_ids_json"] == [chunk.id] for rule in first["rules"])
    rules = first["rules"]
    accepted = client.post(f"{route}/rules/{rules[0]['id']}/accept", json={"reviewer_label": "Post Engineer"})
    assert accepted.json()["status"] == "accepted"
    edited = client.post(f"{route}/rules/{rules[1]['id']}/edit-accept", json={"reviewer_label": "Post Engineer", "edited_template": "G97 S{{rpm}} M04", "reason": "Site-reviewed mode"})
    assert edited.json()["engineer_template"] == "G97 S{{rpm}} M04" and edited.json()["ai_draft_template"] != edited.json()["engineer_template"]
    needed = client.post(f"{route}/rules/{rules[2]['id']}/needs-information", json={"reviewer_label": "Post Engineer", "reason": "Confirm stop sequencing"})
    assert needed.json()["status"] == "needs_more_information"
    assert client.get(route).json()["status"] == "needs_more_information"
    second = client.post(f"{route}/draft", json={"evidence_ids": [chunk.id], "context_reviewed": True, "evidence_mode": "same"}).json()
    assert second["section_version"] == 2
    versions = client.get(f"{route}/versions").json(); assert [row["section_version"] for row in versions] == [2, 1]
    compared = client.get(f"{route}/compare?left=1&right=2").json(); assert compared["left_version"] == 1
    exported = client.get(f"/api/gpost-drafts/{draft['id']}/export?format=json").json()
    assert exported["post_sections"][0]["section_key"] == "spindle"
    assert exported["post_sections"][0]["rules"][0]["ai_draft_template"]
    markdown = client.get(f"/api/gpost-drafts/{draft['id']}/export?format=markdown").text
    assert "AI-assisted post sections" in markdown and "Evidence sources" in markdown
    next_post = client.post(f"/api/gpost-drafts/{draft['id']}/versions")
    assert next_post.status_code == 201
    snapshot = db_session.scalar(select(GPostDraftVersion).where(GPostDraftVersion.gpost_draft_id == next_post.json()["id"]))
    assert snapshot.change_summary_json["post_sections_preserved"] == 1


@pytest.mark.parametrize("field,value", [("cl_text", "GOTO/1,2,3"), ("ncl_text", "LOADTL/1"), ("toolpath", [{"x": 1}]),
    ("part_coordinates", {"x": 1}), ("program_gcode", "G00 X1") , ("translation_example", {"cl_source": "SPINDL/RPM,1"})])
def test_phase11_policy_blocks_before_provider(client, db_session, machine_profile, monkeypatch, field, value):
    _, _, _, draft = setup_phase11(client, db_session, machine_profile)
    monkeypatch.setattr(MockPostBuilderProvider, "draft_post_section", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("provider called")))
    response = client.post(f"/api/post-builder/{draft['id']}/sections/spindle/draft", json={"context_reviewed": True, field: value})
    assert response.status_code == 422 and response.json()["detail"]["code"] == "POST_BUILDER_POLICY_PROHIBITED_CONTENT"


def test_invalid_ai_evidence_reference_is_rejected(client, db_session, machine_profile, monkeypatch):
    _, _, chunk, draft = setup_phase11(client, db_session, machine_profile)
    def invalid(*_args, **_kwargs):
        return PostBuilderProviderResult(payload={"section_key": "spindle", "status": "draft", "draft_rules": [{"rule_key": "x", "name": "X", "condition": "machine-level", "output_behavior": "M03", "evidence_reference_ids": [999], "review_status": "draft"}], "draft_templates": [], "missing_information": [], "assumptions": [], "source_reference_ids": [999], "warnings": []}, provider_metadata={"provider": "mock"})
    monkeypatch.setattr(MockPostBuilderProvider, "draft_post_section", invalid)
    response = client.post(f"/api/post-builder/{draft['id']}/sections/spindle/draft", json={"evidence_ids": [chunk.id], "context_reviewed": True})
    assert response.status_code == 422 and response.json()["detail"]["code"] == "INVALID_AI_EVIDENCE_REFERENCE"
    assert db_session.scalar(select(PostSectionDraft)) is None


def test_no_automatic_ai_and_audit_contains_no_sensitive_payload(client, db_session, machine_profile):
    _, _, chunk, draft = setup_phase11(client, db_session, machine_profile)
    client.get(f"/api/post-builder/{draft['id']}/readiness")
    client.post(f"/api/post-builder/{draft['id']}/sections/spindle/retrieve-evidence", json={})
    assert db_session.scalar(select(AIInvocation)) is None
    client.post(f"/api/post-builder/{draft['id']}/sections/spindle/draft", json={"evidence_ids": [chunk.id], "context_reviewed": True})
    invocation = db_session.scalar(select(AIInvocation).where(AIInvocation.operation_type == "post_section_draft"))
    serialized = str(invocation.provider_metadata_json).lower()
    assert invocation.translation_example_ids_json == [] and invocation.input_hash
    assert not any(term in serialized for term in ["cl_text", "ncl_text", "toolpath", "part_coordinates", "production_gcode"])

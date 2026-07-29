from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from app.models.entities import (
    AuditEvent,
    DocumentChunk,
    DocumentType,
    ProcessingStatus,
    SourceDocument,
)
from app.models.profile_extraction import ProfileFieldProposal


def add_fixture_document(db, machine_id):
    content = (
        Path(__file__).parent / "fixtures" / "kls_1840n_profile_spec.md"
    ).read_text()
    document = SourceDocument(
        machine_profile_id=machine_id,
        title="KLS deterministic review fixture",
        document_type=DocumentType.SPECIFICATION_DOCUMENT,
        original_filename="kls_1840n_profile_spec.md",
        mime_type="text/markdown",
        processing_status=ProcessingStatus.READY,
        extracted_text=content,
    )
    db.add(document)
    db.flush()
    db.add(DocumentChunk(
        document_id=document.id,
        machine_profile_id=machine_id,
        chunk_index=0,
        section_title="Specifications",
        content=content,
        content_hash=sha256(content.encode()).hexdigest(),
        token_estimate=len(content.split()),
    ))
    db.commit()
    db.refresh(document)
    return document


def start_review_run(client, machine_id, document_id):
    response = client.post(
        f"/api/machines/{machine_id}/profile-extraction-runs",
        json={
            "document_ids": [document_id],
            "target_machine_type": "lathe",
            "selected_machine_variant": "KLS-1840N",
            "field_categories": [],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def proposal_map(db, run_id):
    return {
        item.field_key: item
        for item in db.scalars(
            select(ProfileFieldProposal).where(
                ProfileFieldProposal.extraction_run_id == run_id
            )
        )
    }


def test_review_summary_queue_search_filters_and_readiness(
    client, db_session, machine_profile,
):
    document = add_fixture_document(db_session, machine_profile.id)
    run = start_review_run(client, machine_profile.id, document.id)

    summary_response = client.get(
        f"/api/profile-extraction-runs/{run['id']}/review-summary"
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["total"] == 144
    assert summary["pending"] == 144
    assert summary["reviewed"] == 0
    assert summary["draft_ready"] is False
    assert summary["documentation_coverage"] == run["summary_json"][
        "documentation_coverage"
    ]
    assert sum(item["total"] for item in summary["category_summaries"]) == 144

    search_response = client.get(
        f"/api/profile-extraction-runs/{run['id']}/review-queue",
        params={
            "queue": "all",
            "search": "KLS-1840N",
            "category": "identity",
            "has_evidence": True,
        },
    )
    assert search_response.status_code == 200
    search = search_response.json()
    assert search["total"] >= 1
    assert {
        item["field_key"] for item in search["items"]
    } <= {
        "manufacturer", "machine_model", "model", "machine_type",
        "machine_variant",
    }

    high_response = client.get(
        f"/api/profile-extraction-runs/{run['id']}/review-queue",
        params={"queue": "high-confidence", "sort_by": "confidence",
                "sort_direction": "desc"},
    )
    assert high_response.status_code == 200
    assert all(
        item["confidence"] >= summary["confidence_high_threshold"]
        for item in high_response.json()["items"]
    )

    proposals = proposal_map(db_session, run["id"])
    for proposal in proposals.values():
        proposal.review_status = "deferred"
    db_session.commit()
    ready = client.get(
        f"/api/profile-extraction-runs/{run['id']}/review-summary"
    ).json()
    assert ready["pending"] == 0
    assert ready["review_progress_percent"] == 100
    assert ready["draft_ready"] is True
    assert ready["documentation_coverage"] == summary["documentation_coverage"]


def test_protected_batch_accept_has_partial_failures_and_audit_trail(
    client, db_session, machine_profile,
):
    document = add_fixture_document(db_session, machine_profile.id)
    run = start_review_run(client, machine_profile.id, document.id)
    proposals = proposal_map(db_session, run["id"])

    eligible = proposals["manufacturer"]
    eligible.proposal_status = "found"
    eligible.confidence = .99
    eligible.normalized_value_json = "Kent USA"
    eligible.requires_exact_machine_verification = False
    eligible.safety_relevant = False
    eligible.variant_applicability_json = []

    conflict = proposals["max_spindle_rpm"]
    conflict.proposal_status = "conflicting"
    conflict.confidence = .99
    conflict.requires_exact_machine_verification = False
    conflict.safety_relevant = False

    uncited = proposals["machine_model"]
    uncited.proposal_status = "found"
    uncited.confidence = .99
    uncited.normalized_value_json = "KLS-1840N"
    uncited.requires_exact_machine_verification = False
    uncited.safety_relevant = False
    uncited.evidence.clear()
    db_session.commit()

    no_ack = client.post(
        f"/api/profile-extraction-runs/{run['id']}/proposals/batch-review",
        json={
            "proposal_ids": [eligible.id],
            "action": "accept",
            "confirmation": {"acknowledge_advisory_only": False},
        },
    ).json()
    assert no_ack["succeeded"] == []
    assert no_ack["failed"][0]["reason"] == "advisory_acknowledgment_required"

    response = client.post(
        f"/api/profile-extraction-runs/{run['id']}/accept-eligible-high-confidence",
        json={
            "proposal_ids": [eligible.id, conflict.id, uncited.id],
            "confirmation": {"acknowledge_advisory_only": True},
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["succeeded"] == [eligible.id]
    assert {
        item["proposal_id"]: item["reason"] for item in result["failed"]
    } == {
        conflict.id: "unresolved_conflict",
        uncited.id: "missing_citation",
    }

    db_session.refresh(eligible)
    assert eligible.review_status == "accepted"
    assert eligible.reviewed_value_json == eligible.proposed_value_json
    event_types = set(db_session.scalars(select(AuditEvent.event_type)))
    assert "profile_field_accepted" in event_types
    assert "high_confidence_batch_reviewed" in event_types


def test_batch_rejects_controller_only_physical_claim_and_logs_bulk_defer(
    client, db_session, machine_profile,
):
    document = add_fixture_document(db_session, machine_profile.id)
    run = start_review_run(client, machine_profile.id, document.id)
    proposals = proposal_map(db_session, run["id"])
    physical = proposals["x_travel"]
    physical.proposal_status = "found"
    physical.confidence = .99
    physical.normalized_value_json = 279.4
    physical.requires_exact_machine_verification = False
    physical.safety_relevant = False
    physical.variant_applicability_json = []
    document.document_type = DocumentType.CONTROLLER_MANUAL
    deferred = proposals["z_travel"]
    db_session.commit()

    rejected = client.post(
        f"/api/profile-extraction-runs/{run['id']}/proposals/batch-review",
        json={
            "proposal_ids": [physical.id],
            "action": "accept",
            "confirmation": {"acknowledge_advisory_only": True},
        },
    ).json()
    assert rejected["succeeded"] == []
    assert rejected["failed"] == [{
        "proposal_id": physical.id,
        "reason": "controller_evidence_cannot_prove_installed_machine_claim",
    }]

    defer_response = client.post(
        f"/api/profile-extraction-runs/{run['id']}/proposals/batch-review",
        json={
            "proposal_ids": [physical.id, deferred.id, 999999],
            "action": "defer",
        },
    )
    assert defer_response.status_code == 200
    deferred_result = defer_response.json()
    assert deferred_result["succeeded"] == [physical.id, deferred.id]
    assert deferred_result["failed"] == [{
        "proposal_id": 999999,
        "reason": "proposal_not_in_run",
    }]
    assert "batch_review_applied" in set(
        db_session.scalars(select(AuditEvent.event_type))
    )

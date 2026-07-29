from sqlalchemy import select

from app.api.profile_extraction import ensure_initial_revision
from app.models.entities import AuditEvent


PROGRAM_A = """%
O1840
(FICTIONAL SAMPLE - NOT FOR MACHINE USE)
N10 G20 G18 G40 G80 G90
N20 G54
N30 G50 S2000
N40 G96 S500 M03
N50 T0101
N60 G00 X2.0 Z0.1
N70 G01 X1.0 F0.01
N80 M09
N90 M05
N100 G28 U0 W0
N110 M30
%
"""
PROGRAM_B = PROGRAM_A.replace("O1840", "O1841").replace("T0101", "T0202")
CURRENT = PROGRAM_A.replace("N80 M09\n", "").replace("N110 M30", "N110 M02")


def create_reference(client, machine_id, revision_id, name, source, post="POST-1"):
    response = client.post(
        f"/api/machines/{machine_id}/reference-programs",
        json={
            "machine_profile_revision_id": revision_id,
            "name": name,
            "source_text": source,
            "original_filename": f"{name}.nc",
            "program_type": "turning",
            "controller_name": "FANUC",
            "controller_version": "0i-TF",
            "post_processor_name": "Creo fictional post",
            "post_processor_revision": post,
            "approval_status": "approved_reference",
            "machine_variant": "KLS-1840N",
            "units": "inch",
            "ai_processing_allowed": False,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def parse_and_qualify(client, program_id):
    parsed = client.post(f"/api/reference-programs/{program_id}/parse")
    assert parsed.status_code == 200, parsed.text
    eligible = client.post(
        f"/api/reference-programs/{program_id}/mark-eligible",
        json={"reason": "Explicit fixture suitability review completed."},
    )
    assert eligible.status_code == 200, eligible.text
    return eligible.json()


def test_reference_import_duplicate_parse_eligibility_and_scope(
    client, db_session, machine_profile,
):
    revision = ensure_initial_revision(machine_profile, db_session)
    db_session.commit()
    first = create_reference(
        client, machine_profile.id, revision.id, "reference-a", PROGRAM_A,
    )
    assert first["eligibility_status"] == "pending"
    assert first["approval_status"] == "approved_reference"
    assert first["ai_processing_allowed"] is False
    duplicate = client.post(
        f"/api/machines/{machine_profile.id}/reference-programs",
        json={
            "machine_profile_revision_id": revision.id,
            "name": "duplicate",
            "source_text": PROGRAM_A,
            "original_filename": "duplicate.nc",
            "program_type": "turning",
        },
    )
    assert duplicate.status_code == 409
    eligible = parse_and_qualify(client, first["id"])
    assert eligible["eligibility_status"] == "eligible"
    detail = client.get(f"/api/reference-programs/{first['id']}").json()
    assert detail["blocks"]
    assert detail["validation_summary_json"]["block_count"] > 5
    assert detail["source_integrity_json"]["sha256"] == first["file_hash"]

    different = create_reference(
        client, machine_profile.id, revision.id, "reference-other-post",
        PROGRAM_B.replace("O1841", "O2841"), "POST-2",
    )
    parse_and_qualify(client, different["id"])
    mixed = client.post(
        f"/api/machines/{machine_profile.id}/standard-extraction-runs",
        json={
            "machine_profile_revision_id": revision.id,
            "reference_program_ids": [first["id"], different["id"]],
        },
    )
    assert mixed.status_code == 422
    assert "different post revisions" in mixed.json()["detail"]


def test_standard_extraction_frequency_evidence_review_and_approval(
    client, db_session, machine_profile,
):
    revision = ensure_initial_revision(machine_profile, db_session)
    db_session.commit()
    programs = [
        create_reference(client, machine_profile.id, revision.id, "a", PROGRAM_A),
        create_reference(client, machine_profile.id, revision.id, "b", PROGRAM_B),
    ]
    for item in programs:
        parse_and_qualify(client, item["id"])
    run_response = client.post(
        f"/api/machines/{machine_profile.id}/standard-extraction-runs",
        json={
            "machine_profile_revision_id": revision.id,
            "reference_program_ids": [item["id"] for item in programs],
            "post_processor_revision": "POST-1",
        },
    )
    assert run_response.status_code == 200, run_response.text
    run = run_response.json()
    assert run["summary_json"]["eligible_program_count"] == 2
    proposals = client.get(
        f"/api/standard-extraction-runs/{run['id']}/proposals"
    ).json()
    assert len(proposals) >= 10
    assert all(item["evidence"] for item in proposals)
    assert all(item["review_status"] == "pending" for item in proposals)
    assert any(item["convention_type"] == "conditional_pattern" for item in proposals)
    assert any(item["frequency_classification"] == "universal_observed"
               for item in proposals)

    for index, proposal in enumerate(proposals):
        status = "accepted" if index < 5 else "rejected"
        response = client.put(
            f"/api/standard-conventions/{proposal['id']}/review",
            json={
                "review_status": status,
                "review_note": (
                    "Accepted after scope and evidence review."
                    if status == "accepted" else "Weak or unsuitable convention."
                ),
            },
        )
        assert response.status_code == 200, response.text
    draft_response = client.post(
        f"/api/standard-extraction-runs/{run['id']}/apply-to-draft",
        json={"name": "Fictional KLS organizational standard"},
    )
    assert draft_response.status_code == 200, draft_response.text
    draft = draft_response.json()
    assert draft["status"] == "draft"
    assert len(draft["conventions"]) == 5
    submitted = client.post(
        f"/api/standard-profiles/{draft['id']}/submit-for-review",
        json={"note": "Independent review requested."},
    )
    assert submitted.status_code == 200
    approved = client.post(
        f"/api/standard-profiles/{draft['id']}/approve",
        json={"note": "Explicit approval after qualified review."},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    report = client.get(
        f"/api/standard-profiles/{draft['id']}/report?format=json"
    )
    assert report.status_code == 200
    assert report.json()["historical_similarity_is_not_certification"] is True


def test_full_program_comparison_exception_similarity_stale_and_report(
    client, db_session, machine_profile,
):
    revision = ensure_initial_revision(machine_profile, db_session)
    db_session.commit()
    programs = [
        create_reference(client, machine_profile.id, revision.id, "a", PROGRAM_A),
        create_reference(client, machine_profile.id, revision.id, "b", PROGRAM_B),
    ]
    for item in programs:
        parse_and_qualify(client, item["id"])
    run = client.post(
        f"/api/machines/{machine_profile.id}/standard-extraction-runs",
        json={
            "machine_profile_revision_id": revision.id,
            "reference_program_ids": [item["id"] for item in programs],
            "post_processor_revision": "POST-1",
        },
    ).json()
    proposals = client.get(
        f"/api/standard-extraction-runs/{run['id']}/proposals"
    ).json()
    for proposal in proposals:
        response = client.put(
            f"/api/standard-conventions/{proposal['id']}/review",
            json={
                "review_status": "accepted",
                "review_note": "Accepted after evidence and applicability review.",
            },
        )
        assert response.status_code == 200
    standard = client.post(
        f"/api/standard-extraction-runs/{run['id']}/apply-to-draft",
        json={"name": "Comparison fixture standard"},
    ).json()
    approved = client.post(
        f"/api/standard-profiles/{standard['id']}/approve",
        json={"note": "Explicit approval."},
    )
    assert approved.status_code == 200

    analysis = client.post("/api/analyses", json={
        "name": "Phase 6 comparison fixture",
        "machine_profile_id": machine_profile.id,
        "cl_source": None,
        "gcode_source": CURRENT,
    }).json()
    client.post(f"/api/analyses/{analysis['id']}/run")
    comparison_response = client.post(
        f"/api/analyses/{analysis['id']}/standard-comparisons",
        json={
            "standard_profile_id": standard["id"],
            "reference_program_id": programs[0]["id"],
        },
    )
    assert comparison_response.status_code == 200, comparison_response.text
    comparison = comparison_response.json()
    assert comparison["historical_similarity_is_not_certification"] is True
    types = {item["comparison_type"] for item in comparison["findings"]}
    assert "matches" in types
    assert "missing" in types
    assert "unexpected" in types
    assert "not_applicable" in types
    difference = next(
        item for item in comparison["findings"]
        if item["comparison_type"] in {"missing", "unexpected"}
    )
    classified = client.put(
        f"/api/standard-comparison-findings/{difference['id']}/exception",
        json={
            "classification": "requires_investigation",
            "note": "Reason unknown; qualified review required.",
        },
    )
    assert classified.status_code == 200
    assert classified.json()["status"] == "classified_exception"
    similar = client.get(
        f"/api/analyses/{analysis['id']}/similar-reference-programs"
    ).json()
    assert len(similar) == 2
    assert similar[0]["similarity_score"] >= similar[1]["similarity_score"]
    side = client.get(
        f"/api/standard-comparisons/{comparison['id']}/side-by-side"
    ).json()
    assert any(item["type"] == "changed" for item in side["sections"])
    assert "deterministic_findings" in side
    report = client.get(
        f"/api/standard-comparisons/{comparison['id']}/report?format=markdown"
    )
    assert report.status_code == 200
    assert "Historical similarity is not certification" in report.text

    client.post(
        f"/api/reference-programs/{programs[0]['id']}/mark-ineligible",
        json={"reason": "Fixture stale-state check."},
    )
    stale = client.get(
        f"/api/standard-comparisons/{comparison['id']}"
    ).json()
    assert stale["stale"] is True
    event_types = set(db_session.scalars(select(AuditEvent.event_type)))
    assert "program_standard_comparison_completed" in event_types
    assert "program_difference_classified" in event_types
    assert "comparison_report_exported" in event_types

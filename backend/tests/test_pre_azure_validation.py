import pytest

from app.api.profile_extraction import ensure_initial_revision
from app.validation.diagnostics import GPostDiagnosticParser, fil_static_checks


def create_record(client, db_session, machine_profile):
    revision = ensure_initial_revision(machine_profile, db_session); db_session.commit()
    response = client.post(f"/api/machines/{machine_profile.id}/gpost-drafts", json={
        "machine_profile_revision_id": revision.id, "name": "Fictional Validation Post",
        "controller_family": "fanuc_mill", "selected_document_ids": [], "reference_program_ids": [],
    })
    assert response.status_code == 201
    return response.json()


def validation_payload(kind, result="PASS", **values):
    return {"post_version_id": None, "validation_type": kind, "name": f"{kind} Run 01",
        "performed_by": "Fictional NC Programmer", "performed_at": None, "environment": "Local R&D",
        "result": result, "notes": "FICTIONAL R&D DATA — NOT FOR MACHINE USE",
        "attachment_reference": None, "external_tool": values.get("external_tool"),
        "external_reference": values.get("external_reference"), "test_program_name": values.get("test_program_name"),
        "findings_count": 0, "blocking_findings_count": 0, "references_json": [], "ai_used": False}


def test_validation_policy_gates_timeline_and_vericut_handoff(client, db_session, machine_profile):
    record = create_record(client, db_session, machine_profile); rid = record["id"]
    policy = client.put(f"/api/post-records/{rid}/validation-policy", json={"name": "Fictional Lathe R&D",
        "required_validation_types_json": ["Configuration Review", "G-POST Compilation", "VERICUT Simulation", "NC Programmer Review"],
        "optional_validation_types_json": ["Dry Run"], "source": "Fictional site policy", "reviewer": "R&D Engineer"})
    assert policy.status_code == 200
    for kind in ("Configuration Review", "G-POST Compilation", "NC Programmer Review"):
        assert client.post(f"/api/post-records/{rid}/validation-records", json=validation_payload(kind)).status_code == 201
    assert client.get(f"/api/post-records/{rid}/summary").json()["validation"]["gates_satisfied"] is False
    vericut = client.post(f"/api/post-records/{rid}/validation-records", json=validation_payload("VERICUT Simulation",
        "PASS_WITH_FINDINGS", external_tool="VERICUT", external_reference="fictional-report-04.pdf",
        test_program_name="Synthetic 2-Axis Turning Qualification A"))
    assert vericut.status_code == 201 and vericut.json()["external_tool"] == "VERICUT"
    summary = client.get(f"/api/post-records/{rid}/summary").json()
    assert summary["validation"]["gates_satisfied"] is True
    timeline = client.get(f"/api/post-records/{rid}/validation-timeline").json()
    assert timeline["version"] == 1 and len(timeline["events"]) == 4
    handoff = client.get(f"/api/post-records/{rid}/validation-handoff").json()
    assert handoff["does_not_run_vericut"] is True and len(handoff["checklist"]) == 5


def test_diagnostic_parser_findings_resolution_and_question(client, db_session, machine_profile):
    record = create_record(client, db_session, machine_profile); rid = record["id"]
    logic = client.post(f"/api/post-records/{rid}/custom-logic", json={"name": "Spindle Override", "category": "Spindle",
        "reason": "Fictional test", "implementation_type": "FIL / CIMFIL", "status": "needs_review",
        "evidence_ids_json": [], "site_standard_ids_json": [], "source_format": "Site verification required",
        "source_reference": None, "reviewer": None, "review_note": None}).json()
    static = client.post(f"/api/post-records/{rid}/custom-logic/{logic['id']}/static-check", json={"source": "IF (A[1)"})
    assert static.status_code == 200 and static.json()["advisory_only"] is True
    assert static.json()["compiler_authority"] == "Installed G-POST environment"
    validation = client.post(f"/api/post-records/{rid}/validation-records", json=validation_payload("G-POST Compilation", "FAIL")).json()
    listing = "\n".join(["INFO [I001] compilation started", "WARNING [W102] formatting directive line 41",
        "ERROR [E500] Undefined variable SPDMAX in Spindle Override line 482", "FATAL [F900] compile stopped", "unstructured ERROR site format"])
    parsed = client.post(f"/api/post-records/{rid}/validation-records/{validation['id']}/diagnostics/parse",
        json={"listing_text": listing, "file_name": "fictional.lst", "create_findings": True})
    assert parsed.status_code == 200
    assert {row["severity"] for row in parsed.json()} == {"INFO", "WARNING", "ERROR", "FATAL", "UNKNOWN"}
    error = next(row for row in parsed.json() if row["code"] == "E500")
    assert error["custom_logic_reference_id"] == logic["id"] and error["line_reference"] == 482
    findings = client.get(f"/api/post-records/{rid}/validation-findings").json()
    assert len(findings) == 3
    item = findings[0]
    resolved = client.put(f"/api/post-records/{rid}/validation-findings/{item['id']}", json={**item,
        "status": "Resolved", "resolution_note": "Reviewed manually"})
    assert resolved.status_code == 200 and resolved.json()["status"] == "Resolved"
    question = client.post(f"/api/post-records/{rid}/validation-findings/{findings[1]['id']}/open-question")
    assert question.status_code == 201 and question.json()["related_type"] == "validation_finding"
    package = client.get(f"/api/post-records/{rid}/export?format=json").text
    assert "gpost_diagnostics" in package and "validation_findings" in package
    assert listing not in package


def test_parser_malformed_large_safety_and_fil_static_checks():
    parser = GPostDiagnosticParser()
    unknown = parser.parse("fictional unrecognized listing format")
    assert unknown[0].severity == "UNKNOWN"
    with pytest.raises(ValueError, match="2 MB"):
        parser.parse("X" * 2_000_001)
    assert fil_static_checks("")[0]["code"] == "FIL_EMPTY"
    assert fil_static_checks("IF (A[1)")[0]["code"] == "FIL_UNBALANCED"

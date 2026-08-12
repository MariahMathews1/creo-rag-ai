from sqlalchemy import select

from app.api.profile_extraction import ensure_initial_revision
from app.models.entities import AuditEvent


def translation_payload(machine, revision, **updates):
    value = {
        "machine_profile_id": machine.id, "machine_profile_revision_id": revision.id,
        "name": "Fictional spindle and motion pair", "post_processor_name": "Fictional Site Post",
        "post_processor_revision": "REV-12", "operation_type": "milling", "operation_name": "Face",
        "cl_source_text": "PPRINT/FICTIONAL SAMPLE - NOT FOR MACHINE USE\nLOADTL/2\nSPINDL/RPM,1200,CLW\nFEDRAT/IPM,12\nCOOLNT/ON\nRAPID\nGOTO/1,2,3\nFINI",
        "gcode_source_text": "(FICTIONAL SAMPLE - NOT FOR MACHINE USE)\nG20 G17 G40 G49 G80 G90 G94\nT2 M06\nS1200 M03\nF12\nM08\nG00 X1 Y2 Z3\nM30",
        "verification_status": "candidate", "part_identifier": "PART-FICTIONAL",
        "program_identifier": "O9001", "project_identifier": "DEMO-P8",
        "source_system": "Fictional controlled archive", "source_provenance": "Synthetic paired fixture.",
        "verification_basis": "Fictional test evidence only", "ai_processing_allowed": False,
    }
    value.update(updates); return value


def setup_revision(db, machine):
    revision = ensure_initial_revision(machine, db); db.commit(); return revision


def test_crud_hash_parse_validation_duplicate_and_machine_revision(client, db_session, machine_profile):
    revision = setup_revision(db_session, machine_profile)
    response = client.post("/api/translations", json=translation_payload(machine_profile, revision))
    assert response.status_code == 201, response.text
    row = response.json()
    assert len(row["cl_source_hash"]) == len(row["gcode_source_hash"]) == 64
    assert row["cl_parse_summary_json"]["cl_record_count"] >= 7
    assert row["gcode_parse_summary_json"]["gcode_block_count"] >= 7
    assert "blocking_count" in row["validation_summary_json"]
    assert row["machine_context_snapshot_json"]["id"] == revision.id
    assert row["ai_processing_allowed"] is False
    duplicate = client.post("/api/translations", json=translation_payload(machine_profile, revision))
    assert duplicate.headers["X-Duplicate-Translation-Example"] == "true"
    assert duplicate.json()["id"] == row["id"]
    updated = client.put(f"/api/translations/{row['id']}", json={"description": "Reviewed metadata"})
    assert updated.status_code == 200 and updated.json()["description"] == "Reviewed metadata"


def test_machine_ownership_and_reference_program_isolation(client, db_session, machine_profile):
    revision = setup_revision(db_session, machine_profile)
    other = client.post("/api/machines", json={"name":"Other","manufacturer":"F","model":"M","controller_name":"FANUC","machine_type":"mill","axis_count":3,"supported_work_offsets":["G54"],"approved_g_codes":[],"approved_m_codes":[],"restricted_commands":[]}).json()
    response = client.post("/api/translations", json=translation_payload(machine_profile, revision, machine_profile_id=other["id"]))
    assert response.status_code == 422


def test_verification_transitions_gate_acknowledgement_and_final_immutability(client, db_session, machine_profile):
    revision = setup_revision(db_session, machine_profile)
    row = client.post("/api/translations", json=translation_payload(machine_profile, revision)).json()
    premature = client.post(f"/api/translations/{row['id']}/verify", json={"note":"Reviewed historical pair in test.","reviewer_label":"Reviewer","acknowledgement":True})
    assert premature.status_code == 409
    reviewed = client.post(f"/api/translations/{row['id']}/review", json={"note":"Qualified review completed.","reviewer_label":"Reviewer"})
    assert reviewed.json()["verification_status"] == "reviewed"
    no_ack = client.post(f"/api/translations/{row['id']}/verify", json={"note":"Historical match reviewed and justified.","reviewer_label":"Reviewer"})
    assert no_ack.status_code == 422
    verified = client.post(f"/api/translations/{row['id']}/verify", json={"note":"Historical match reviewed and justified against controlled records.","reviewer_label":"Reviewer","acknowledgement":True})
    assert verified.status_code == 200, verified.text
    assert verified.json()["verification_status"] == "verified_successful"
    assert client.put(f"/api/translations/{row['id']}", json={"name":"Overwrite"}).status_code == 409
    deprecated = client.post(f"/api/translations/{row['id']}/deprecate", json={"note":"Post revision retired.","reviewer_label":"Reviewer"})
    assert deprecated.json()["verification_status"] == "deprecated"


def test_invalid_transition_and_blocking_finding_justification(client, db_session, machine_profile):
    revision = setup_revision(db_session, machine_profile)
    row = client.post("/api/translations", json=translation_payload(machine_profile, revision, name="Invalid pair", cl_source_text="FINI", gcode_source_text="G00 X999999\nM30")).json()
    invalid = client.post(f"/api/translations/{row['id']}/invalidate", json={"note":"Known mismatched source pair.","reviewer_label":"Reviewer"})
    assert invalid.json()["verification_status"] == "invalid"
    second = client.post("/api/translations", json=translation_payload(machine_profile, revision, name="Blocking pair", cl_source_text="PPRINT/BLOCK\nFINI", gcode_source_text="G00 X999998\nM30")).json()
    client.post(f"/api/translations/{second['id']}/review", json={"note":"Review complete.","reviewer_label":"Reviewer"})
    if second["validation_summary_json"]["blocking_count"]:
        short = client.post(f"/api/translations/{second['id']}/verify", json={"note":"Too short","reviewer_label":"Reviewer","acknowledgement":True})
        assert short.status_code == 422


def test_alignment_cardinality_unmatched_manual_and_review(client, db_session, machine_profile):
    revision = setup_revision(db_session, machine_profile)
    row = client.post("/api/translations", json=translation_payload(machine_profile, revision)).json()
    result = client.post(f"/api/translations/{row['id']}/alignment")
    assert result.status_code == 200, result.text
    alignment = result.json(); assert alignment["links"]
    assert any(link["link_type"] == "one_to_one" for link in alignment["links"])
    assert any(link["link_type"] == "many_to_one" for link in alignment["links"])
    assert any(link["link_type"] == "unmatched" and link["cl_record_start"] is None for link in alignment["links"])
    assert any(link["link_type"] == "unmatched" and link["gcode_block_start"] is None for link in alignment["links"])
    tool = next(link for link in alignment["links"] if "same_tool_number" in link["match_reasons_json"])
    assert client.post(f"/api/translation-alignment-links/{tool['id']}/confirm").json()["review_status"] == "confirmed"
    unmatched = next(link for link in alignment["links"] if link["link_type"] == "unmatched")
    assert client.post(f"/api/translation-alignment-links/{unmatched['id']}/reject").json()["review_status"] == "rejected"
    manual = client.post(f"/api/translation-alignments/{alignment['id']}/links", json={"cl_record_start":1,"cl_record_end":2,"gcode_block_start":1,"gcode_block_end":2,"link_type":"many_to_many","review_status":"edited","notes":"Manual span","reviewed_by_label":"Reviewer"})
    assert manual.status_code == 200 and manual.json()["link_type"] == "many_to_many"
    one_to_many = client.post(f"/api/translation-alignments/{alignment['id']}/links", json={"cl_record_start":2,"cl_record_end":2,"gcode_block_start":2,"gcode_block_end":3,"link_type":"one_to_many","review_status":"edited","notes":"Expanded manual span","reviewed_by_label":"Reviewer"})
    assert one_to_many.status_code == 200 and one_to_many.json()["link_type"] == "one_to_many"


def test_explorer_machine_post_grouping_summary_gpost_evidence_and_audit(client, db_session, machine_profile):
    revision = setup_revision(db_session, machine_profile)
    row = client.post("/api/translations", json=translation_payload(machine_profile, revision)).json()
    alignment = client.post(f"/api/translations/{row['id']}/alignment").json()
    for link in alignment["links"]:
        if link["cl_record_start"] is not None and link["gcode_block_start"] is not None:
            client.post(f"/api/translation-alignment-links/{link['id']}/confirm")
        else: client.post(f"/api/translation-alignment-links/{link['id']}/reject")
    client.post(f"/api/translations/{row['id']}/review", json={"note":"Reviewed.","reviewer_label":"Reviewer"})
    verified = client.post(f"/api/translations/{row['id']}/verify", json={"note":"Verified fictional historical output with controlled context.","reviewer_label":"Reviewer","acknowledgement":True})
    assert verified.status_code == 200, verified.text
    groups = client.get("/api/translations/explorer?command=SPINDL").json()
    assert groups and groups[0]["machine_profile_id"] == machine_profile.id and groups[0]["post_revision"] == "REV-12"
    assert "{rpm}" in groups[0]["cl_pattern"] and "{rpm}" in groups[0]["gcode_pattern"]
    summary = client.get("/api/translations/summary").json(); assert summary["verified"] == 1
    draft = client.post(f"/api/machines/{machine_profile.id}/gpost-drafts", json={"machine_profile_revision_id":revision.id,"name":"Evidence draft","controller_family":"fanuc_mill","selected_document_ids":[],"reference_program_ids":[],"manual_configuration_acknowledged":True}).json()
    mapping = next(m for m in client.get(f"/api/gpost-drafts/{draft['id']}/mappings").json() if m["mapping_key"] == "spindl_cw")
    evidence = client.get(f"/api/gpost-mappings/{mapping['id']}/historical-translation-evidence").json()
    assert evidence["verified_example_count"] == 1 and evidence["mapping_changed"] is False
    events = set(db_session.scalars(select(AuditEvent.event_type).where(AuditEvent.event_type.like("translation_%"))))
    assert {"translation_example_created","translation_alignment_created","translation_alignment_confirmed","translation_example_verified"} <= events

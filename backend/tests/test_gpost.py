from sqlalchemy import select

from app.api.profile_extraction import ensure_initial_revision
from app.models.entities import AuditEvent, DocumentChunk, DocumentType, MachineProfile, MachineType, SourceDocument
from app.models.profile_extraction import MachineProfileRevision


def create_draft(client, db_session, machine_profile, **overrides):
    revision = ensure_initial_revision(machine_profile, db_session)
    db_session.commit()
    payload = {
        "machine_profile_revision_id": revision.id,
        "name": "Fictional VM-3 G-POST Draft",
        "controller_family": "fanuc_mill",
        "selected_document_ids": [],
        "reference_program_ids": [],
    }
    payload.update(overrides)
    return client.post(f"/api/machines/{machine_profile.id}/gpost-drafts", json=payload)


def test_create_machine_scoped_draft_with_initial_mapping_coverage(client, db_session, machine_profile):
    response = create_draft(client, db_session, machine_profile)
    assert response.status_code == 201
    draft = response.json()
    assert draft["machine_profile_id"] == machine_profile.id
    assert draft["machine_profile_revision_id"]
    assert draft["safety_notice"] == "R&D ONLY · NON-PRODUCTION · NOT VALIDATED FOR MACHINE USE"
    mappings = client.get(f"/api/gpost-drafts/{draft['id']}/mappings").json()
    by_key = {item["mapping_key"]: item for item in mappings}
    assert {"loadtl", "spindl_cw", "spindl_ccw", "spindl_off", "fedrat", "coolnt_on", "coolnt_off", "rapid", "goto", "fini"} <= by_key.keys()
    assert by_key["spindl_cw"]["template_key"] == "spindle_start_cw"
    assert by_key["spindl_cw"]["output_template"] is None
    assert by_key["spindl_cw"]["effective_output_template"] == "S{rpm:g} M03"
    assert by_key["loadtl"]["required_for_v1"] is True
    assert by_key["multax"]["support_status"] in {"not_applicable", "not_implemented"}
    assert draft["review_summary_json"]["required"] == 10


def test_revision_and_document_ownership_are_enforced(client, db_session, machine_profile):
    other = MachineProfile(name="Other lathe", manufacturer="Other", model="L1", controller_name="FANUC", machine_type=MachineType.LATHE)
    db_session.add(other); db_session.commit()
    other_revision = ensure_initial_revision(other, db_session)
    foreign_document = SourceDocument(machine_profile_id=other.id, title="Other manual", document_type=DocumentType.MACHINE_MANUAL)
    db_session.add(foreign_document); db_session.commit()
    wrong_revision = create_draft(client, db_session, machine_profile, machine_profile_revision_id=other_revision.id)
    assert wrong_revision.status_code == 422
    leaked_document = create_draft(client, db_session, machine_profile, selected_document_ids=[foreign_document.id])
    assert leaked_document.status_code == 422


def test_mapping_review_and_machine_scoped_document_evidence(client, db_session, machine_profile):
    document = SourceDocument(machine_profile_id=machine_profile.id, title="Controller programming manual", document_type=DocumentType.PROGRAMMING_MANUAL)
    db_session.add(document); db_session.flush()
    chunk = DocumentChunk(document_id=document.id, machine_profile_id=machine_profile.id, chunk_index=0, content="M06 changes the selected tool.", content_hash="a" * 64, token_estimate=7)
    db_session.add(chunk); db_session.commit()
    draft = create_draft(client, db_session, machine_profile, selected_document_ids=[document.id]).json()
    mapping = next(item for item in client.get(f"/api/gpost-drafts/{draft['id']}/mappings").json() if item["cl_command"] == "LOADTL")
    response = client.put(f"/api/gpost-mappings/{mapping['id']}", json={
        "template_override": "T{tool} M06", "uses_override": True, "review_status": "accepted_with_edit",
        "review_note": "Verified against selected manual.", "source_type": "document",
        "source_document_id": document.id, "source_chunk_id": chunk.id,
        "source_page": 42, "source_section": "Tool change", "source_excerpt": "M06 changes the selected tool.",
        "source_authority": "controller_manufacturer",
    })
    assert response.status_code == 200
    assert response.json()["review_status"] == "accepted_with_edit"
    assert response.json()["effective_output_template"] == "T{tool} M06"
    evidence = client.post(f"/api/gpost-mappings/{mapping['id']}/evidence", json={
        "source_type": "document", "document_id": document.id,
        "document_chunk_id": chunk.id, "page": 42, "section": "Tool change",
        "excerpt": "M06 changes the selected tool.",
        "authority_level": "controller_manufacturer",
    })
    assert evidence.status_code == 201
    assert evidence.json()["document_id"] == document.id
    events = list(db_session.scalars(select(AuditEvent).where(AuditEvent.event_type == "gpost_mapping_edited")))
    assert events and "source_excerpt" not in events[-1].metadata_json


def test_preview_reuses_parsers_rules_and_retains_traceability(client, db_session, machine_profile):
    draft = create_draft(client, db_session, machine_profile).json()
    cl = """LOADTL/2
SPINDL/RPM,2500,CLW
FEDRAT/IPM,12
COOLNT/ON
RAPID
GOTO/1,2,3
GOTO/2,3,4
COOLNT/OFF
FINI
"""
    response = client.post(f"/api/gpost-drafts/{draft['id']}/preview", json={"cl_source": cl})
    assert response.status_code == 200
    preview = response.json()
    assert "T2 M06" in preview["generated_gcode"]
    assert "S2500 M03" in preview["generated_gcode"]
    assert "G00 X1 Y2 Z3" in preview["generated_gcode"]
    assert preview["parser_version"] == "gcode-parser-v1"
    assert preview["rule_set_version"] == "validation-v1"
    assert preview["traceability_json"]
    spindle_trace = next(item for item in preview["traceability_json"] if item["cl_command"] == "SPINDL")
    assert spindle_trace["source_cl_line"] == 2
    assert spindle_trace["mapping_id"]
    assert spindle_trace["state_before"] != spindle_trace["state_after"]


def test_multiaxis_and_family_mismatch_block_preview_without_disappearing(client, db_session, machine_profile):
    draft = create_draft(client, db_session, machine_profile).json()
    preview = client.post(f"/api/gpost-drafts/{draft['id']}/preview", json={"cl_source": "MULTAX/ON\nTLAXIS/0,0,1\nFINI"}).json()
    assert preview["status"] == "blocked"
    assert {item["command"] for item in preview["unsupported_commands_json"]} == {"MULTAX", "TLAXIS"}

    lathe_family = create_draft(client, db_session, machine_profile, name="Mismatch", controller_family="fanuc_lathe").json()
    blocked = client.post(f"/api/gpost-drafts/{lathe_family['id']}/preview", json={"cl_source": "FINI"}).json()
    assert blocked["status"] == "blocked"
    assert any(item["code"] == "GPOST_TEMPLATE_FAMILY_MISMATCH" for item in blocked["warnings_json"])


def test_current_cl_preflight_ignores_irrelevant_mappings_and_warns_for_unreviewed(client, db_session, machine_profile):
    draft = create_draft(client, db_session, machine_profile).json()
    mappings = client.get(f"/api/gpost-drafts/{draft['id']}/mappings").json()
    unrelated = next(item for item in mappings if item["mapping_key"] == "multax")
    assert unrelated["support_status"] != "supported"
    result = client.post(f"/api/gpost-drafts/{draft['id']}/preflight", json={"cl_source": "SPINDL/RPM,1200,CLW\nFINI"}).json()
    assert result["generation_allowed"] is True
    assert result["required_behavior_keys"] == ["spindl_cw", "fini"]
    assert "multax" not in result["unsupported_required_behaviors"]
    assert set(result["unreviewed_behavior_keys"]) == {"spindl_cw", "fini"}
    assert result["generation_allowed_with_warning"] is True


def test_current_cl_preflight_blocks_only_unsupported_current_behavior(client, db_session, machine_profile):
    draft = create_draft(client, db_session, machine_profile).json()
    result = client.post(f"/api/gpost-drafts/{draft['id']}/preflight", json={"cl_source": "CYCLE/THREAD\nFINI"}).json()
    assert result["generation_allowed"] is False
    assert "cycle" in result["unsupported_required_behaviors"]
    blocker = next(item for item in result["blocking_issues"] if item["code"] == "GPOST_UNSUPPORTED_CURRENT_CL")
    assert blocker["action"] == "configure_mapping"


def test_versioning_compare_exports_and_audit_events(client, db_session, machine_profile):
    first = create_draft(client, db_session, machine_profile).json()
    templates = dict(first["templates_json"]); templates["comment"] = "[{text}]"
    assert client.put(f"/api/gpost-drafts/{first['id']}", json={"templates_json": templates}).status_code == 200
    second = client.post(f"/api/gpost-drafts/{first['id']}/versions").json()
    assert second["version"] == 2
    assert client.get(f"/api/gpost-drafts/{first['id']}").json()["status"] == "superseded"
    mapping = next(item for item in client.get(f"/api/gpost-drafts/{second['id']}/mappings").json() if item["mapping_key"] == "fedrat")
    client.put(f"/api/gpost-mappings/{mapping['id']}", json={"template_override": "F{feed:g} (EDITED)", "uses_override": True, "review_status": "accepted_with_edit"})
    diff = client.get(f"/api/gpost-drafts/{first['id']}/compare/{second['id']}").json()
    assert "fedrat" in diff["templates_changed"]
    json_export = client.get(f"/api/gpost-drafts/{second['id']}/export?format=json")
    markdown_export = client.get(f"/api/gpost-drafts/{second['id']}/export?format=markdown")
    assert "NOT VALIDATED FOR MACHINE USE" in json_export.text
    assert "NON-PRODUCTION" in markdown_export.text
    event_types = set(db_session.scalars(select(AuditEvent.event_type).where(AuditEvent.event_type.like("gpost_%"))))
    assert {"gpost_draft_created", "gpost_version_created", "gpost_exported"} <= event_types


def test_shared_template_changes_flow_to_mapping_and_override_can_reset(client, db_session, machine_profile):
    draft = create_draft(client, db_session, machine_profile).json()
    mapping = next(item for item in client.get(f"/api/gpost-drafts/{draft['id']}/mappings").json() if item["mapping_key"] == "spindl_cw")
    templates = dict(draft["templates_json"]); templates["spindle_start_cw"] = "S{rpm:g} M13"
    assert client.put(f"/api/gpost-drafts/{draft['id']}", json={"templates_json": templates}).status_code == 200
    updated = next(item for item in client.get(f"/api/gpost-drafts/{draft['id']}/mappings").json() if item["id"] == mapping["id"])
    assert updated["effective_output_template"] == "S{rpm:g} M13"
    override = client.put(f"/api/gpost-mappings/{mapping['id']}", json={"template_override": "S{rpm:g} M03 (LOCAL)", "uses_override": True, "review_status": "accepted_with_edit"}).json()
    assert override["effective_output_template"].endswith("(LOCAL)")
    reset = client.post(f"/api/gpost-mappings/{mapping['id']}/reset-override").json()
    assert reset["uses_override"] is False
    assert reset["effective_output_template"] == "S{rpm:g} M13"


def test_support_and_review_states_are_separate_and_progress_uses_required_only(client, db_session, machine_profile):
    draft = create_draft(client, db_session, machine_profile).json()
    mappings = client.get(f"/api/gpost-drafts/{draft['id']}/mappings").json()
    multax = next(item for item in mappings if item["mapping_key"] == "multax")
    assert multax["support_status"] in {"not_applicable", "not_implemented"}
    assert multax["review_status"] in {"pending", "deferred"}
    loadtl = next(item for item in mappings if item["mapping_key"] == "loadtl")
    client.put(f"/api/gpost-mappings/{loadtl['id']}", json={"review_status": "accepted"})
    refreshed = client.get(f"/api/gpost-drafts/{draft['id']}").json()["review_summary_json"]
    assert refreshed["required"] == 10
    assert refreshed["reviewed"] == 1
    assert refreshed["needs_review"] == 9


def test_profile_machine_type_snapshot_mismatch_and_missing_source_block_preflight(client, db_session, machine_profile):
    draft = create_draft(client, db_session, machine_profile).json()
    row = db_session.get(__import__("app.models.gpost", fromlist=["GPostDraft"]).GPostDraft, draft["id"])
    row.machine_type = "lathe"
    revision = db_session.get(MachineProfileRevision, row.machine_profile_revision_id)
    revision.controller_name = "Haas NGC"
    revision.controller_manufacturer = "Haas"
    db_session.commit()
    preview = client.post(f"/api/gpost-drafts/{draft['id']}/preview", json={"cl_source": "FINI"}).json()
    codes = {item.get("code") for item in preview["warnings_json"]}
    assert "GPOST_MACHINE_TYPE_SNAPSHOT_MISMATCH" in codes
    assert "GPOST_CONTROLLER_FAMILY_MISMATCH" in codes
    assert "GPOST_SOURCE_ACKNOWLEDGEMENT_REQUIRED" not in codes


def test_draft_creation_requires_approved_profile_revision(client, db_session, machine_profile):
    revision = ensure_initial_revision(machine_profile, db_session)
    revision.status = "under_review"
    db_session.commit()
    response = client.post(f"/api/machines/{machine_profile.id}/gpost-drafts", json={
        "machine_profile_revision_id": revision.id, "name": "Unapproved revision",
        "controller_family": "fanuc_mill", "selected_document_ids": [], "reference_program_ids": [],
    })
    assert response.status_code == 422
    assert "approved machine profile revision" in response.json()["detail"]


def test_optional_evidence_and_monotonic_versions(client, db_session, machine_profile):
    first = create_draft(client, db_session, machine_profile, manual_configuration_acknowledged=True).json()
    assert first["reference_program_ids_json"] == [] and first["standard_profile_id"] is None
    templates = dict(first["templates_json"]); templates["comment"] = "[{text}]"
    client.put(f"/api/gpost-drafts/{first['id']}", json={"templates_json": templates})
    second = client.post(f"/api/gpost-drafts/{first['id']}/versions").json()
    templates = dict(second["templates_json"]); templates["comment"] = "/* {text} */"
    client.put(f"/api/gpost-drafts/{second['id']}", json={"templates_json": templates})
    third = client.post(f"/api/gpost-drafts/{second['id']}/versions").json()
    assert [first["version"], second["version"], third["version"]] == [1, 2, 3]
    assert [item["id"] for item in client.get(f"/api/gpost-drafts/{third['id']}/versions").json()] == [third["id"], second["id"], first["id"]]


def test_version_creation_rejects_duplicate_snapshot(client, db_session, machine_profile):
    draft = create_draft(client, db_session, machine_profile).json()
    response = client.post(f"/api/gpost-drafts/{draft['id']}/versions")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "GPOST_NO_VERSION_CHANGES"


def test_duplicate_archive_and_delete_retention(client, db_session, machine_profile):
    source = create_draft(client, db_session, machine_profile, name="Logical Post").json()
    duplicate = client.post(f"/api/gpost-drafts/{source['id']}/duplicate")
    assert duplicate.status_code == 201
    assert duplicate.json()["version"] == 1 and duplicate.json()["created_from_draft_id"] is None
    assert duplicate.json()["name"] == "Logical Post Copy"
    assert client.get(f"/api/gpost-drafts/{source['id']}/versions").json()[0]["id"] == source["id"]
    assert client.post(f"/api/gpost-drafts/{duplicate.json()['id']}/archive").json()["status"] == "archived"
    assert client.delete(f"/api/gpost-drafts/{duplicate.json()['id']}").status_code == 204

    templates = dict(source["templates_json"]); templates["comment"] = "[{text}]"
    client.put(f"/api/gpost-drafts/{source['id']}", json={"templates_json": templates})
    version = client.post(f"/api/gpost-drafts/{source['id']}/versions").json()
    blocked = client.delete(f"/api/gpost-drafts/{version['id']}")
    assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == "GPOST_DELETE_RETENTION_BLOCKED"


def test_kent_style_lathe_scenario_uses_lathe_defaults_and_blocks_multiaxis(client, db_session):
    created = client.post("/api/machines", json={
        "name": "Kent KLS R&D G-POST Verification", "manufacturer": "Kent USA",
        "model": "KLS-1840N public test", "controller_name": "FANUC-style",
        "controller_manufacturer": "FANUC", "controller_model": "0i-TF Plus",
        "machine_type": "lathe", "axis_count": 2, "x_min": -10, "x_max": 10,
        "z_min": -40, "z_max": 5, "max_spindle_rpm": 3000, "max_feed_rate": 200,
        "supported_work_offsets": ["G54"],
        "approved_g_codes": ["G00", "G01", "G18", "G20", "G40", "G54", "G80", "G90", "G99"],
        "approved_m_codes": ["M03", "M04", "M05", "M08", "M09", "M30"],
        "restricted_commands": ["G96"], "safe_start_template": "G20 G18 G40 G80 G90 G99",
        "program_end_template": "M05 M09 M30",
    })
    assert created.status_code == 201
    lathe = created.json()
    revision_id = lathe["active_revision_id"]
    draft_response = client.post(f"/api/machines/{lathe['id']}/gpost-drafts", json={
        "machine_profile_revision_id": revision_id, "name": "Kent FANUC Lathe Draft",
        "controller_family": "fanuc_lathe", "selected_document_ids": [],
        "reference_program_ids": [],
    })
    assert draft_response.status_code == 201
    draft = draft_response.json()
    assert draft["templates_json"]["plane_selection"] == "G18"
    assert "M06" not in draft["templates_json"]["tool_change"]
    normal = client.post(f"/api/gpost-drafts/{draft['id']}/preview", json={
        "cl_source": "LOADTL/101\nSPINDL/RPM,1200,CLW\nFEDRAT/IPR,.01\nCOOLNT/ON\nRAPID\nGOTO/2,99,-1\nGOTO/1,.25\nFINI",
    }).json()
    assert "T0101" in normal["generated_gcode"]
    assert "G18" in normal["generated_gcode"]
    assert "Y99" not in normal["generated_gcode"]
    assert "X2 Z-1" in normal["generated_gcode"]
    assert "X1 Z0.25 F0.01" in normal["generated_gcode"]
    multiaxis = client.post(f"/api/gpost-drafts/{draft['id']}/preview", json={
        "cl_source": "MULTAX/ON\nFINI",
    }).json()
    assert multiaxis["status"] == "blocked"
    assert multiaxis["unsupported_commands_json"][0]["command"] == "MULTAX"

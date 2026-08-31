from app.api.profile_extraction import ensure_initial_revision
from app.models.profile_extraction import ProfileExtractionRun, ProfileFieldProposal


def create_record(client, db_session, machine_profile):
    revision = ensure_initial_revision(machine_profile, db_session); db_session.commit()
    response = client.post(f"/api/machines/{machine_profile.id}/gpost-drafts", json={
        "machine_profile_revision_id": revision.id, "name": "VM-3 Engineering Post Record",
        "controller_family": "fanuc_mill", "selected_document_ids": [], "reference_program_ids": [],
    })
    assert response.status_code == 201
    return response.json()


def test_machine_knowledge_ofg_traceability_and_review(client, db_session, machine_profile):
    record = create_record(client, db_session, machine_profile)
    facts = client.get(f"/api/post-records/{record['id']}/machine-knowledge")
    assert facts.status_code == 200
    assert len(facts.json()) == 21
    spindle = next(item for item in facts.json() if item["fact_key"] == "max_spindle_rpm")
    assert spindle["status"] == "confirmed"
    assert spindle["post_review_status"] == "available_from_machine"
    assert any(item["label"] == "Maximum Spindle Speed" for item in spindle["used_by"])
    settings = client.get(f"/api/post-records/{record['id']}/ofg-settings").json()
    assert len(settings) >= 20
    assert {item["category"] for item in settings} >= {"Machine & Axes", "File Formats", "Motion", "Machine Codes"}
    assert all(item["relevance_class"] != "advanced" for item in settings)
    assert all(item["ofg_menu_path_status"] in {"verified_from_reference", "site_verification_needed", "not_verified"} for item in settings)
    assert len(client.get(f"/api/post-records/{record['id']}/machine-knowledge").json()) == 21
    setting = next(item for item in settings if item["setting_key"] == "maximum_spindle_speed")
    assert setting["source_machine_facts"][0]["id"] == spindle["id"]
    assert setting["ofg_menu_path"] == "Spindle → Direct RPM"
    assert setting["ofg_menu_path_status"] == "verified_from_reference"
    reviewed_fact = client.put(f"/api/post-records/{record['id']}/machine-knowledge/{spindle['id']}", json={
        key: value for key, value in spindle.items()
        if key not in {"id", "post_record_id", "used_by", "reviewed_at", "created_at", "updated_at"}
    })
    assert reviewed_fact.status_code == 200
    assert reviewed_fact.json()["post_review_status"] == "reviewed_for_post"
    advanced = client.get(f"/api/post-records/{record['id']}/ofg-settings?include_advanced=true").json()
    assert any(item["relevance_class"] == "advanced" for item in advanced)
    summary = client.get(f"/api/post-records/{record['id']}/summary").json()
    assert summary["ofg_configuration"]["total"] == len(settings)
    setting["status"] = "reviewed"; setting["reviewer"] = "NC Engineer"
    source_facts = setting.pop("source_machine_facts")
    response = client.put(f"/api/post-records/{record['id']}/ofg-settings/{setting['id']}", json={
        key: value for key, value in setting.items() if key not in {"id", "post_record_id", "reviewed_at", "created_at", "updated_at"}
    })
    assert response.status_code == 200 and response.json()["status"] == "reviewed"
    assert response.json()["source_machine_facts"] == source_facts


def test_site_standard_scope_application_and_conflict(client, db_session, machine_profile):
    record = create_record(client, db_session, machine_profile)
    standard = client.post("/api/site-standards", json={"name": "Tool Change Safe Retract", "description": "Site convention",
        "scope": "controller_family", "applicable_machine_types_json": ["mill"], "applicable_controller_families_json": ["fanuc_mill"],
        "applicable_machine_ids_json": [], "category": "Tooling", "rule": "Retract to the approved safe position before tool change.",
        "validation_requirements_json": ["VERICUT Simulation"],
        "source": "Site SOP 12", "status": "reviewed", "reviewer": "Manufacturing Engineering", "version": 1,
        "effective_date": None, "notes": None}).json()
    applied = client.post(f"/api/post-records/{record['id']}/site-standards", json={"site_standard_id": standard["id"],
        "status": "applied", "conflict_status": "requires_review", "conflict_note": "Manual permits current position.",
        "reviewer": "NC Engineer", "review_note": "Site override requires review."})
    assert applied.status_code == 201
    assert applied.json()["standard"]["scope"] == "controller_family"
    summary = client.get(f"/api/post-records/{record['id']}/summary").json()
    assert summary["site_standards"]["conflicts"] == 1
    assert any(item["type"] == "site_standard" for item in summary["blockers"])
    assert "VERICUT Simulation" in summary["validation"]["required_gates"]


def test_custom_logic_questions_validation_and_exports(client, db_session, machine_profile):
    record = create_record(client, db_session, machine_profile); record_id = record["id"]
    ofg_setting = client.get(f"/api/post-records/{record_id}/ofg-settings").json()[0]
    logic = client.post(f"/api/post-records/{record_id}/custom-logic", json={"name": "G74 Grooving Output",
        "category": "Cycles", "reason": "Standard OFG settings do not represent the reviewed behavior.",
        "related_ofg_setting_id": ofg_setting["id"], "desired_behavior": "Emit reviewed machine-level grooving behavior.",
        "runtime_trigger": "Approved G74 cycle request",
        "implementation_type": "FIL / CIMFIL", "status": "needs_draft", "evidence_ids_json": [],
        "site_standard_ids_json": [], "source_format": "Site verification required", "source_reference": None,
        "reviewer": None, "review_note": None})
    assert logic.status_code == 201
    assert logic.json()["related_ofg_setting_id"] == ofg_setting["id"]
    linked_setting = next(item for item in client.get(f"/api/post-records/{record_id}/ofg-settings").json() if item["id"] == ofg_setting["id"])
    assert linked_setting["custom_logic_id"] == logic.json()["id"]
    assert linked_setting["status"] == "custom_logic_required"
    question = client.post(f"/api/post-records/{record_id}/open-questions", json={"question_type": "controller_option",
        "title": "Confirm G74 option", "description": None, "severity": "blocking", "related_type": "custom_logic",
        "related_id": logic.json()["id"], "source_context": "Programming manual p.210", "owner": "NC Programmer",
        "status": "waiting_on_nc_programmer", "resolution": None})
    assert question.status_code == 201
    generated = client.post(f"/api/post-records/{record_id}/open-questions", json={"question_type": "system_missing_information",
        "title": "Generated missing value", "description": "Required machine knowledge is not confirmed.", "severity": "warning",
        "related_type": "machine_fact", "related_id": None, "source_context": None, "owner": None, "status": "open", "resolution": None})
    assert generated.status_code == 201
    visible_questions = client.get(f"/api/post-records/{record_id}/open-questions").json()
    assert [item["title"] for item in visible_questions] == ["Confirm G74 option"]
    assert client.get(f"/api/post-records/{record_id}/summary").json()["open_questions"]["open"] == 1
    validation = client.post(f"/api/post-records/{record_id}/validation-records", json={"post_version_id": None,
        "validation_type": "Controlled Test CL Run", "performed_by": "NC Programmer", "performed_at": None,
        "environment": "Creo/G-POST local", "result": "passed_with_findings", "notes": "Local test only.",
        "references_json": ["Synthetic Turning Test A"], "ai_used": False})
    assert validation.status_code == 201 and validation.json()["ai_used"] is False
    for fmt in ("markdown", "json", "csv"):
        export = client.get(f"/api/post-records/{record_id}/export?format={fmt}")
        assert export.status_code == 200
        assert "native G-POST" in export.text or "native_gpost_post" in export.text or "OFG Location" in export.text
    assert "G74 Grooving Output" in client.get(f"/api/post-records/{record_id}/export?format=markdown").text
    assert "Controlled Test Post" in client.get(f"/api/post-records/{record_id}/export?format=json").text


def test_version_snapshot_and_clone_include_engineering_package(client, db_session, machine_profile):
    record = create_record(client, db_session, machine_profile); record_id = record["id"]
    settings = client.get(f"/api/post-records/{record_id}/ofg-settings").json()
    setting = settings[0]; setting.pop("source_machine_facts")
    payload = {key: value for key, value in setting.items() if key not in {"id", "post_record_id", "reviewed_at", "created_at", "updated_at"}}
    payload["status"] = "reviewed"; payload["review_note"] = "Reviewed for version snapshot"
    assert client.put(f"/api/post-records/{record_id}/ofg-settings/{setting['id']}", json=payload).status_code == 200
    version = client.post(f"/api/gpost-drafts/{record_id}/versions")
    assert version.status_code == 201 and version.json()["version"] == 2
    cloned = client.get(f"/api/post-records/{version.json()['id']}/ofg-settings").json()
    assert any(item["review_note"] == "Reviewed for version snapshot" for item in cloned)
    historical_fact = client.get(f"/api/post-records/{record_id}/machine-knowledge").json()[0]
    immutable = client.put(f"/api/post-records/{record_id}/machine-knowledge/{historical_fact['id']}", json={
        key: value for key, value in historical_fact.items()
        if key not in {"id", "post_record_id", "used_by", "reviewed_at", "created_at", "updated_at"}
    })
    assert immutable.status_code == 409
    comparison = client.get(f"/api/post-records/{version.json()['id']}/compare/{record_id}")
    assert comparison.status_code == 200
    assert comparison.json()["left"]["version"] == 2
    assert comparison.json()["right"]["version"] == 1
    assert client.post(f"/api/gpost-drafts/{version.json()['id']}/versions").status_code == 409


def test_manual_machine_information_persists_traceability_and_updates_existing_post(client, db_session, machine_profile):
    record = create_record(client, db_session, machine_profile)
    payload = {"fact_key": "max_spindle_rpm", "value": "3210", "unit": "RPM", "source_basis": "engineer_entry",
        "document_id": None, "source_detail": "Installed-machine review", "notes": "Verified by local engineer.",
        "review_status": "confirmed", "proposal_id": None}
    created = client.post(f"/api/machines/{machine_profile.id}/machine-information/manual", json=payload)
    assert created.status_code == 201
    assert created.json()["value"] == 3210
    assert created.json()["unit"] == "rpm"
    assert created.json()["source_label"] == "Engineer Entry"
    listed = client.get(f"/api/machines/{machine_profile.id}/machine-information").json()
    assert [(item["fact_key"], item["review_status"]) for item in listed] == [("max_spindle_rpm", "confirmed")]
    facts = client.get(f"/api/post-records/{record['id']}/machine-knowledge").json()
    spindle = [item for item in facts if item["fact_key"] == "max_spindle_rpm"]
    assert len(spindle) == 1
    assert spindle[0]["value_json"] == 3210 and spindle[0]["source_label"] == "Engineer Entry"
    setting = next(item for item in client.get(f"/api/post-records/{record['id']}/ofg-settings").json() if item["setting_key"] == "maximum_spindle_speed")
    assert setting["value_json"] == 3210 and setting["status"] == "needs_review"
    payload.update(value="3000", review_status="needs_review")
    assert client.post(f"/api/machines/{machine_profile.id}/machine-information/manual", json=payload).status_code == 201
    facts = client.get(f"/api/post-records/{record['id']}/machine-knowledge").json()
    assert len([item for item in facts if item["fact_key"] == "max_spindle_rpm"]) == 1
    assert next(item for item in facts if item["fact_key"] == "max_spindle_rpm")["status"] == "needs_review"
    axis_entry = client.post(f"/api/machines/{machine_profile.id}/machine-information/manual", json={
        "fact_key": "x_travel", "value": "11", "unit": "in",
        "source_basis": "installed_machine_configuration", "document_id": None,
        "source_detail": "Machine inspection", "notes": None,
        "review_status": "confirmed", "proposal_id": None,
    })
    assert axis_entry.status_code == 201
    listed = client.get(f"/api/machines/{machine_profile.id}/machine-information").json()
    assert {item["fact_key"] for item in listed} == {"max_spindle_rpm", "x_travel"}
    axis_limits = next(item for item in client.get(f"/api/post-records/{record['id']}/ofg-settings").json()
                       if item["setting_key"] == "axis_limits")
    assert axis_limits["value_json"]["X"] == 11
    discarded = client.delete(f"/api/machines/{machine_profile.id}/machine-information/x_travel")
    assert discarded.status_code == 204
    listed = client.get(f"/api/machines/{machine_profile.id}/machine-information").json()
    assert {item["fact_key"] for item in listed} == {"max_spindle_rpm"}
    facts = client.get(f"/api/post-records/{record['id']}/machine-knowledge").json()
    assert next(item for item in facts if item["fact_key"] == "x_travel")["value_json"] == [-20, 20]
    axis_limits = next(item for item in client.get(f"/api/post-records/{record['id']}/ofg-settings").json()
                       if item["setting_key"] == "axis_limits")
    assert axis_limits["value_json"]["X"] == [-20, 20]
    assert client.delete(f"/api/machines/{machine_profile.id}/machine-information/x_travel").status_code == 404


def test_manual_entry_resolves_matching_missing_extraction_proposal(client, db_session, machine_profile):
    revision = ensure_initial_revision(machine_profile, db_session)
    run = ProfileExtractionRun(machine_profile_id=machine_profile.id, target_revision_id=revision.id, status="review_required",
        provider_name="mock", selected_document_ids_json=[], settings_json={"target_machine_type": "mill"}, summary_json={})
    db_session.add(run); db_session.flush()
    proposal = ProfileFieldProposal(extraction_run_id=run.id, field_key="x_travel", field_label="X-axis travel",
        field_category="axis_limits", proposed_value_json=None, normalized_value_json=None, unit=None, confidence=0,
        proposal_status="not_found", review_status="pending", extraction_method="deterministic_regex")
    db_session.add(proposal); db_session.commit()
    response = client.post(f"/api/machines/{machine_profile.id}/machine-information/manual", json={"fact_key": "x_travel",
        "value": "11", "unit": "in", "source_basis": "installed_machine_configuration", "document_id": None,
        "source_detail": "Machine inspection", "notes": None, "review_status": "needs_review", "proposal_id": proposal.id})
    assert response.status_code == 201
    reviewed = client.get(f"/api/profile-field-proposals/{proposal.id}").json()
    assert reviewed["review_status"] == "manually_entered" and reviewed["reviewed_value_json"] == 11
    summary = client.get(f"/api/profile-extraction-runs/{run.id}/review-summary").json()
    assert summary["not_found_pending"] == 0 and summary["manually_entered"] == 1

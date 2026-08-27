from app.api.profile_extraction import ensure_initial_revision


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
    logic = client.post(f"/api/post-records/{record_id}/custom-logic", json={"name": "G74 Grooving Output",
        "category": "Cycles", "reason": "Standard OFG settings do not represent the reviewed behavior.",
        "implementation_type": "FIL / CIMFIL", "status": "needs_draft", "evidence_ids_json": [],
        "site_standard_ids_json": [], "source_format": "Site verification required", "source_reference": None,
        "reviewer": None, "review_note": None})
    assert logic.status_code == 201
    question = client.post(f"/api/post-records/{record_id}/open-questions", json={"question_type": "controller_option",
        "title": "Confirm G74 option", "description": None, "severity": "blocking", "related_type": "custom_logic",
        "related_id": logic.json()["id"], "source_context": "Programming manual p.210", "owner": "NC Programmer",
        "status": "waiting_on_nc_programmer", "resolution": None})
    assert question.status_code == 201
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

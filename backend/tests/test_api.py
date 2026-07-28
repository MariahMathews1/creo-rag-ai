def profile_payload(**overrides):
    payload = {
        "name": "Demo Mill",
        "manufacturer": "Fictional",
        "model": "DM-100",
        "controller_name": "Fanuc-style",
        "machine_type": "mill",
        "axis_count": 3,
        "x_min": -20,
        "x_max": 20,
        "y_min": -10,
        "y_max": 10,
        "z_min": -5,
        "z_max": 15,
        "max_spindle_rpm": 10000,
        "max_feed_rate": 500,
        "rapid_z_review_threshold": 0,
        "supported_work_offsets": ["g54"],
        "approved_g_codes": ["g0", "G01", "G17", "G20", "G40", "G49", "G54", "G80", "G90"],
        "approved_m_codes": ["m3", "M05", "M09", "M30"],
        "restricted_commands": ["g91", "m0"],
        "safe_start_template": "G17 G20 G40 G49 G80 G90",
        "program_end_template": "M5 M9 G49 M30",
    }
    payload.update(overrides)
    return payload


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "Creo NC Post Assistant API",
    }


def test_machine_creation_normalizes_commands(client):
    response = client.post("/api/machines", json=profile_payload())
    assert response.status_code == 201
    assert response.json()["approved_g_codes"][:2] == ["G00", "G01"]
    assert response.json()["approved_m_codes"][0] == "M03"
    assert response.json()["restricted_commands"][-1] == "M00"


def test_invalid_machine_limits_return_422(client):
    response = client.post(
        "/api/machines", json=profile_payload(x_min=20, x_max=-20)
    )
    assert response.status_code == 422
    assert "minimum must be less than maximum" in str(response.json())


def test_machine_update_get_and_delete(client):
    created_payload = profile_payload()
    profile_id = client.post("/api/machines", json=created_payload).json()["id"]
    created_payload["max_spindle_rpm"] = 9000
    updated = client.put(f"/api/machines/{profile_id}", json=created_payload)
    assert updated.status_code == 200
    assert updated.json()["max_spindle_rpm"] == 9000
    assert client.get(f"/api/machines/{profile_id}").status_code == 200
    assert client.delete(f"/api/machines/{profile_id}").status_code == 204
    assert client.get(f"/api/machines/{profile_id}").status_code == 404


def test_missing_machine_returns_404(client):
    assert client.get("/api/machines/9999").status_code == 404


def test_analysis_creation_rejects_missing_machine(client):
    response = client.post(
        "/api/analyses",
        json={"name": "Review", "machine_profile_id": 999, "gcode_source": "M30"},
    )
    assert response.status_code == 422


def test_analysis_list_tolerates_legacy_null_snapshot(
    client, db_session, machine_profile
):
    from app.models.entities import AnalysisProject

    legacy_project = AnalysisProject(
        name="Legacy review",
        machine_profile_id=machine_profile.id,
        machine_profile_snapshot_json=None,
    )
    db_session.add(legacy_project)
    db_session.commit()

    response = client.get("/api/analyses")

    assert response.status_code == 200
    legacy_response = next(
        project for project in response.json() if project["id"] == legacy_project.id
    )
    assert legacy_response["machine_profile_snapshot_json"] == {}


def test_full_analysis_integration_and_rerun(client):
    profile_id = client.post("/api/machines", json=profile_payload()).json()["id"]
    created = client.post(
        "/api/analyses",
        json={
            "name": "Problem review",
            "machine_profile_id": profile_id,
            "cl_source": "",
            "gcode_source": "G54\nG00 X25 Z-4\nS12000 M03",
        },
    )
    assert created.status_code == 201
    assert created.json()["advisory_only"] is True
    analysis_id = created.json()["id"]

    first_run = client.post(f"/api/analyses/{analysis_id}/run")
    assert first_run.status_code == 200
    assert first_run.json()["project"]["status"] == "blocked"
    assert first_run.json()["advisory_only"] is True
    assert "does not certify" in first_run.json()["safety_notice"]
    first_rule_ids = {item["rule_id"] for item in first_run.json()["findings"]}
    assert {"AXIS_X_LIMIT", "SPINDLE_MAX_RPM", "SAFE_START_MISSING"} <= first_rule_ids

    stored = client.get(f"/api/analyses/{analysis_id}/findings")
    assert stored.status_code == 200
    assert len(stored.json()) == len(first_run.json()["findings"])

    source_update = client.put(
        f"/api/analyses/{analysis_id}/gcode-source",
        json={
            "text": "G17 G20 G40 G49 G80 G90 G54\n"
            "G01 X1 F20\nM05 M09 G49 M30"
        },
    )
    assert source_update.status_code == 200
    second_run = client.post(f"/api/analyses/{analysis_id}/run")
    assert second_run.status_code == 200
    assert second_run.json()["project"]["status"] == "passed"
    assert not [
        finding
        for finding in second_run.json()["findings"]
        if finding["severity"] in {"blocking", "warning"}
    ]
    stored_again = client.get(f"/api/analyses/{analysis_id}/findings").json()
    assert stored_again == second_run.json()["findings"]


def test_warning_only_analysis_is_review_required(client):
    payload = profile_payload()
    profile_id = client.post("/api/machines", json=payload).json()["id"]
    created = client.post(
        "/api/analyses",
        json={
            "name": "Feed review",
            "machine_profile_id": profile_id,
            "gcode_source": "G17 G20 G40 G49 G80 G90 G54\n"
            "G01 X1 F501\nM30",
        },
    )
    result = client.post(f"/api/analyses/{created.json()['id']}/run")
    assert result.json()["project"]["status"] == "review_required"
    assert any(item["rule_id"] == "FEED_MAX_RATE" for item in result.json()["findings"])

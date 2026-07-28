from app.cl_parser import CLParser


def test_cl_parser_commands_modal_state_and_variations():
    source = """
    $$ comment
    units / inches
    LOADTL/8
    SPINDL / RPM, 2500, CLW
    COOLNT/FLOOD
    RAPID
    GOTO / 1.0, 2.0, 3.0
    FEDRAT / IPM, 18.5
    goto/2,3,4,0,0,1
    PPRINT / OPERATION: ROUGH POCKET
    CIRCLE / 2,3,4,0,0,1,1
    MYSTERY / 1X
    """
    result = CLParser().parse(source)
    commands = [record.command for record in result.records]
    assert commands == [
        "COMMENT", "UNITS", "LOADTL", "SPINDL", "COOLNT", "RAPID",
        "GOTO", "FEDRAT", "GOTO", "PPRINT", "CIRCLE", "UNKNOWN",
    ]
    first_goto, second_goto = result.records[6], result.records[8]
    assert first_goto.coordinates == {"X": 1.0, "Y": 2.0, "Z": 3.0}
    assert first_goto.motion_type == "rapid"
    assert second_goto.coordinates["K"] == 1.0
    assert second_goto.state_after["tool_axis"] == {"I": 0.0, "J": 0.0, "K": 1.0}
    assert second_goto.feed_rate == 18.5
    assert second_goto.tool_number == 8
    assert second_goto.spindle_speed == 2500
    assert second_goto.coolant_state == "flood"
    assert result.units == "inch"


def test_cl_parser_empty_blank_from_and_malformed_do_not_crash():
    assert CLParser().parse("\n \n").records == []
    result = CLParser().parse("FROM / 0, 0, 1\nGOTO / 1.BAD, 2, 3")
    assert result.records[0].motion_type == "reference"
    assert result.records[1].parse_errors


def test_traceability_api_workflow_persistence_review_report_and_stale(
    client, machine_profile
):
    project = client.post(
        "/api/analyses",
        json={"name": "Traceability", "machine_profile_id": machine_profile.id},
    ).json()
    cl = (
        "$$ FICTIONAL SAMPLE - NOT FOR MACHINE USE\nUNITS/INCHES\n"
        "LOADTL/8\nSPINDL/RPM,2500,CLW\nCOOLNT/FLOOD\nRAPID\n"
        "GOTO/1,2,.5\nFEDRAT/IPM,18.5\nGOTO/1,2,-.25\nFINI"
    )
    gcode = (
        "(FICTIONAL SAMPLE - NOT FOR MACHINE USE)\nG20 G90\nT08\nM06\n"
        "S2500 M03\nM08\nG00 X1 Y2 Z.5\nG01 Z-.25 F18.5\nM09\nM30"
    )
    assert client.post(
        f"/api/analyses/{project['id']}/cl-source", data={"text": cl}
    ).status_code == 200
    assert client.post(
        f"/api/analyses/{project['id']}/gcode-source", data={"text": gcode}
    ).status_code == 200
    assert client.post(f"/api/analyses/{project['id']}/parse-cl").json()["record_count"] == 10
    assert client.post(f"/api/analyses/{project['id']}/parse-gcode").json()["record_count"] == 10
    run = client.post(f"/api/analyses/{project['id']}/alignment-runs")
    assert run.status_code == 200
    run_data = run.json()
    assert run_data["advisory_only"] is True
    assert run_data["alignment_is_inferred"] is True
    links = client.get(f"/api/alignment-runs/{run_data['id']}/links").json()
    assert links
    assert any(link["link_type"] == "one_to_many" for link in links)
    assert any(link["link_type"] == "many_to_one" for link in links)
    confirmed = client.post(f"/api/alignment-links/{links[0]['id']}/confirm").json()
    assert confirmed["status"] == "confirmed"
    report = client.get(
        f"/api/alignment-runs/{run_data['id']}/report", params={"format": "markdown"}
    )
    assert report.status_code == 200
    assert "does not certify" in report.text
    new_run = client.post(
        f"/api/alignment-runs/{run_data['id']}/recalculate"
    ).json()
    assert new_run["version"] == 2
    carried = client.get(f"/api/alignment-runs/{new_run['id']}/links").json()
    assert any(link["status"] == "confirmed" for link in carried)
    client.put(
        f"/api/analyses/{project['id']}/cl-source",
        json={"text": cl + "\nPPRINT/CHANGED"},
    )
    runs = client.get(f"/api/analyses/{project['id']}/alignment-runs").json()
    assert all(value["stale"] for value in runs)

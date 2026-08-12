from time import perf_counter

from app.cl_parser.parser import CLParser
from app.parsers.gcode import GCodeParser
from app.services.toolpath.service import build_toolpath


def test_cl_rapid_feed_tool_change_and_lathe_xz_warning():
    records = CLParser().parse("LOADTL/2\nFROM/0,0,0\nRAPID\nGOTO/2,0,1\nFEDRAT/IPM,8\nGOTO/1,0,-2").records
    result = build_toolpath(cl_records=records, machine_type="lathe", source="cl")
    assert result.default_view == "XZ"
    assert {s.motion_type for s in result.segments} >= {"tool_change", "rapid", "linear"}
    assert result.bounds.max_x == 2 and result.bounds.min_z == -2
    assert "DIAMETER_RADIUS_MODE_UNKNOWN" in {w["code"] for w in result.warnings}


def test_gcode_absolute_incremental_coordinate_context_and_findings():
    blocks = GCodeParser().parse("G21 G17 G90 G54\nG00 X1 Y2 Z3\nG91 G01 X2 Y-1 F10\nG53 G00 Z0").blocks
    result = build_toolpath(gcode_blocks=blocks, machine_type="mill", source="gcode", findings=[{"id": 7, "line_number": 3}, {"id": 8, "line_number": 3}])
    motions = [s for s in result.segments if s.end_point]
    assert motions[1].end_point.x == 3 and motions[1].end_point.y == 1
    assert motions[1].finding_ids == [7, 8]
    assert result.coordinate_context == "mixed" and result.default_view == "XY"


def test_ijk_arcs_all_planes_and_helical_metadata():
    for plane, source in {
        "G17": "G17 G90\nG00 X1 Y0 Z0\nG03 X0 Y1 I-1 J0 Z1",
        "G18": "G18 G90\nG00 X1 Z0 Y0\nG02 X0 Z-1 I-1 K0 Y1",
        "G19": "G19 G90\nG00 Y1 Z0 X0\nG03 Y0 Z1 J-1 K0 X1",
    }.items():
        result = build_toolpath(gcode_blocks=GCodeParser().parse(source).blocks, machine_type="mill", source="gcode")
        arc = next(s for s in result.segments if s.motion_type.startswith("arc"))
        assert arc.plane == plane and arc.center_point and len(arc.path_points) >= 8 and arc.helical


def test_r_arc_and_unresolved_arc_are_not_silently_straightened():
    resolved = build_toolpath(gcode_blocks=GCodeParser().parse("G17 G90\nG00 X0 Y0\nG02 X2 Y0 R1").blocks, source="gcode")
    assert next(s for s in resolved.segments if s.motion_type == "arc_cw").path_points
    unresolved = build_toolpath(gcode_blocks=GCodeParser().parse("G17 G90\nG00 X0 Y0\nG03 X2 Y0").blocks, source="gcode")
    arc = next(s for s in unresolved.segments if s.motion_type == "arc_ccw")
    assert not arc.visualizable and not arc.path_points
    assert "UNRESOLVED_ARC" in {w["code"] for w in unresolved.warnings}


def test_alignment_overlay_and_conservative_spatial_comparison():
    cl = CLParser().parse("FROM/0,0,0\nGOTO/1,2,3").records
    gc = GCodeParser().parse("G90\nG01 X1 Y2 Z3").blocks
    result = build_toolpath(cl_records=cl, gcode_blocks=gc, source="both", alignment_by_cl={1:(9,["gcode-1"])}, alignment_by_gc={1:(9,["cl-1"])})
    assert next(s for s in result.segments if s.id == "cl-1").alignment_link_id == 9
    assert result.comparison_summary["matching_geometry"] == 1


def test_unknown_offset_multiaxis_and_ten_thousand_segment_performance():
    source = "MULTAX/ON\nFROM/0,0,0\n" + "\n".join(f"GOTO/{i},0,0,0,0,1" for i in range(10_001))
    start = perf_counter(); result = build_toolpath(cl_records=CLParser().parse(source).records, source="cl"); duration = perf_counter()-start
    assert result.summary["segments"] == 10_003 and result.summary["visualization_simplified"] is True
    assert "MULTIAXIS_VISUALIZATION_LIMITED" in {w["code"] for w in result.warnings}
    assert duration < 5


def test_translation_and_analysis_toolpath_endpoints(client, db_session, machine_profile):
    from app.api.profile_extraction import ensure_initial_revision
    revision=ensure_initial_revision(machine_profile,db_session);db_session.commit()
    payload={"machine_profile_id":machine_profile.id,"machine_profile_revision_id":revision.id,"name":"Visual pair","post_processor_name":"UNKNOWN","operation_type":"turning","cl_source_text":"FROM/0,0,0\nGOTO/1,0,-1","gcode_source_text":"G18 G90\nG01 X1 Z-1"}
    row=client.post("/api/translations",json=payload).json()
    response=client.get(f"/api/translations/{row['id']}/toolpath?source=both")
    assert response.status_code==200 and response.json()["default_view"]=="XY"
    project=client.post("/api/analyses",json={"name":"Visual analysis","machine_profile_id":machine_profile.id,"cl_source":payload["cl_source_text"],"gcode_source":payload["gcode_source_text"]}).json()
    assert client.get(f"/api/analyses/{project['id']}/toolpath").json()["segments"]


def test_gpost_preview_toolpath_endpoint(client, db_session, machine_profile):
    from app.api.profile_extraction import ensure_initial_revision
    revision=ensure_initial_revision(machine_profile,db_session);db_session.commit()
    draft=client.post(f"/api/machines/{machine_profile.id}/gpost-drafts",json={"machine_profile_revision_id":revision.id,"name":"Visual draft","controller_family":"fanuc_mill","selected_document_ids":[],"reference_program_ids":[],"manual_configuration_acknowledged":True}).json()
    preview=client.post(f"/api/gpost-drafts/{draft['id']}/preview",json={"cl_source":"LOADTL/1\nRAPID\nGOTO/1,2,3\nFINI"})
    assert preview.status_code==200,preview.text
    response=client.get(f"/api/gpost-preview-runs/{preview.json()['id']}/toolpath?source=both")
    assert response.status_code==200 and {s["source_type"] for s in response.json()["segments"]}=={"cl","gcode"}

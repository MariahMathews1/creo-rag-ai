from app.parsers.gcode import GCodeParser


def test_compact_tokens_coordinates_and_normalization():
    result = GCodeParser().parse("N0100g00x+01.250y-2.500z0.100f018.5s02500t06m03")
    block = result.blocks[0]
    assert block.original_text == "N0100g00x+01.250y-2.500z0.100f018.5s02500t06m03"
    assert block.sequence_number == 100
    assert block.g_codes == ["G00"]
    assert block.m_codes == ["M03"]
    assert block.coordinates == {"X": 1.25, "Y": -2.5, "Z": 0.1}
    assert block.feed_rate == 18.5
    assert block.spindle_speed == 2500
    assert block.tool_number == 6


def test_comments_program_number_and_comment_only_lines():
    result = GCodeParser().parse(
        "O1001 (FACING OP)\n(comment only)\nG0 X0 ; move to start"
    )
    assert result.blocks[0].program_number == 1001
    assert result.blocks[0].comments == ["(FACING OP)"]
    assert result.blocks[1].cleaned_text == ""
    assert result.blocks[1].comments == ["(comment only)"]
    assert result.blocks[2].comments == ["; move to start"]


def test_complete_modal_state_tracking():
    result = GCodeParser().parse(
        "G90 G17 G20 G54\n"
        "T6 M6\n"
        "S2500 M3 M8\n"
        "G43 G1 X1 F18.5\n"
        "G40 G49 M5 M9"
    )
    cutting = result.blocks[3].modal_state
    assert cutting.distance_mode == "G90"
    assert cutting.motion_mode == "G01"
    assert cutting.plane == "G17"
    assert cutting.units == "G20"
    assert cutting.work_offset == "G54"
    assert cutting.feed_rate == 18.5
    assert cutting.spindle_speed == 2500
    assert cutting.selected_tool == 6
    assert cutting.active_tool == 6
    assert cutting.coolant_state == "flood"
    assert cutting.spindle_state == "clockwise"
    assert result.blocks[-1].modal_state.coolant_state == "off"
    assert result.blocks[-1].modal_state.spindle_state == "off"


def test_malformed_tokens_do_not_abort_remaining_program():
    result = GCodeParser().parse("G1 X1 UNKNOWN\nG1 X2")
    assert result.errors
    assert "UNKNOWN" in result.blocks[0].parse_errors[0]
    assert len(result.blocks) == 2
    assert result.blocks[1].coordinates["X"] == 2


def test_blank_lines_are_ignored_but_source_line_numbers_are_preserved():
    result = GCodeParser().parse("\n\nG01 X1\n\nM30")
    assert [block.line_number for block in result.blocks] == [3, 5]


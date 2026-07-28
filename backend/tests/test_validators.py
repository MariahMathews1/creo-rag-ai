from app.models.entities import Severity
from app.parsers.gcode import GCodeParser
from app.validators.engine import ValidationEngine


def validate(program, machine_profile):
    parsed = GCodeParser(set(machine_profile.supported_work_offsets)).parse(program)
    return ValidationEngine().validate(parsed, machine_profile)


def by_rule(findings, rule_id):
    return [finding for finding in findings if finding.rule_id == rule_id]


def complete_program(body: str) -> str:
    return (
        "G17 G20 G40 G49 G80 G90 G54\n"
        f"{body}\n"
        "M05 M09 G40 G49 M30"
    )


def test_each_axis_limit_has_a_stable_rule_id(machine_profile):
    findings = validate(complete_program("G00 X21 Y-11 Z16"), machine_profile)
    assert by_rule(findings, "AXIS_X_LIMIT")
    assert by_rule(findings, "AXIS_Y_LIMIT")
    assert by_rule(findings, "AXIS_Z_LIMIT")
    assert "does not prove" in by_rule(findings, "AXIS_X_LIMIT")[0].description


def test_spindle_and_feed_limits(machine_profile):
    findings = validate(complete_program("S10001 M03\nG01 X1 F501"), machine_profile)
    assert by_rule(findings, "SPINDLE_MAX_RPM")[0].severity == Severity.BLOCKING
    assert by_rule(findings, "FEED_MAX_RATE")[0].severity == Severity.WARNING


def test_restricted_and_unapproved_commands(machine_profile):
    findings = validate(complete_program("G91\nG28"), machine_profile)
    assert by_rule(findings, "RESTRICTED_COMMAND")
    assert by_rule(findings, "UNAPPROVED_COMMAND")


def test_empty_approved_lists_do_not_warn(machine_profile):
    machine_profile.approved_g_codes = []
    machine_profile.approved_m_codes = []
    findings = validate(complete_program("G28"), machine_profile)
    assert not by_rule(findings, "UNAPPROVED_COMMAND")


def test_work_offset_must_appear_before_first_cutting_feed(machine_profile):
    program = "G17 G20 G40 G49 G80 G90\nG01 X1 F20\nG54\nM30"
    finding = by_rule(validate(program, machine_profile), "WORK_OFFSET_MISSING")[0]
    assert finding.line_number == 2


def test_tool_change_requires_selection(machine_profile):
    findings = validate(complete_program("M06"), machine_profile)
    assert by_rule(findings, "TOOL_CHANGE_WITHOUT_SELECTION")


def test_safe_start_uses_command_presence_not_string_matching(machine_profile):
    good = "N10 G90 G80\nN20 G49 G40\nN30 G20 G17 G54\nM30"
    assert not by_rule(validate(good, machine_profile), "SAFE_START_MISSING")
    assert by_rule(validate("G54\nG01 X1\nM30", machine_profile), "SAFE_START_MISSING")


def test_recognized_program_end_is_accepted(machine_profile):
    assert not by_rule(
        validate("G17 G20 G40 G49 G80 G90 G54\nM30", machine_profile),
        "PROGRAM_END_MISSING",
    )
    assert by_rule(
        validate("G17 G20 G40 G49 G80 G90 G54\nM05", machine_profile),
        "PROGRAM_END_MISSING",
    )


def test_compensation_active_at_end(machine_profile):
    program = "G17 G20 G40 G49 G80 G90 G54\nG41 G43 G01 X1\nM30"
    findings = validate(program, machine_profile)
    assert by_rule(findings, "CUTTER_COMP_ACTIVE_AT_END")
    assert by_rule(findings, "TOOL_LENGTH_COMP_ACTIVE_AT_END")


def test_rapid_z_rule_uses_configured_threshold_and_heuristic_wording(machine_profile):
    machine_profile.rapid_z_review_threshold = 0.5
    finding = by_rule(
        validate(complete_program("G00 Z0.25"), machine_profile),
        "RAPID_Z_REVIEW",
    )[0]
    assert "not proof of a collision" in finding.description


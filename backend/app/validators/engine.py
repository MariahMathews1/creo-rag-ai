"""Reusable deterministic validation rules for parsed CNC programs."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import re

from app.models.entities import MachineProfile, Severity
from app.parsers.gcode import ParseResult, ParsedGCodeBlock, normalize_code


@dataclass(slots=True)
class ValidationResult:
    rule_id: str
    severity: Severity
    category: str
    title: str
    description: str
    recommendation: str
    line_number: int | None = None
    source_line: str | None = None
    confidence: float = 1.0


@dataclass(slots=True)
class ValidationContext:
    parsed: ParseResult
    profile: MachineProfile


def finding(
    rule: "ValidationRule",
    message: str,
    recommendation: str,
    block: ParsedGCodeBlock | None = None,
    *,
    severity: Severity | None = None,
    title: str | None = None,
    confidence: float = 1.0,
) -> ValidationResult:
    return ValidationResult(
        rule_id=rule.rule_id,
        severity=severity or rule.default_severity,
        category=rule.category,
        title=title or rule.name,
        description=message,
        recommendation=recommendation,
        line_number=block.line_number if block else None,
        source_line=block.original_text if block else None,
        confidence=confidence,
    )


def template_codes(template: str | None) -> set[str]:
    if not template:
        return set()
    return {
        normalize_code(letter, value)
        for letter, value in re.findall(
            r"\b([GM])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))",
            template.upper(),
        )
    }


def normalized_profile_codes(values: list[str] | None) -> set[str]:
    normalized: set[str] = set()
    for raw in values or []:
        match = re.fullmatch(
            r"\s*([GM])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*", raw, re.I
        )
        normalized.add(normalize_code(*match.groups()) if match else raw.strip().upper())
    return normalized


class ValidationRule(ABC):
    """Typed rule contract with stable metadata and a deterministic validator."""

    rule_id: str
    name: str
    description: str
    default_severity: Severity
    category: str

    @abstractmethod
    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        """Return zero or more explainable findings."""


class ParseErrorRule(ValidationRule):
    rule_id = "PARSE_ERROR"
    name = "G-code line requires syntax review"
    description = "Reports tokens the baseline parser could not interpret."
    default_severity = Severity.WARNING
    category = "syntax"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for block in context.parsed.blocks:
            for error in block.parse_errors:
                results.append(
                    finding(
                        self,
                        error,
                        "Review the original controller syntax and confirm the parser configuration.",
                        block,
                    )
                )
        return results


class AxisLimitRule(ValidationRule):
    name = "Programmed axis value exceeds configured travel"
    description = "Checks explicitly programmed axis words against profile limits."
    default_severity = Severity.BLOCKING
    category = "machine_limits"

    def __init__(self, axis: str):
        self.axis = axis
        self.rule_id = f"AXIS_{axis}_LIMIT"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        lower = getattr(context.profile, f"{self.axis.lower()}_min")
        upper = getattr(context.profile, f"{self.axis.lower()}_max")
        results: list[ValidationResult] = []
        for block in context.parsed.blocks:
            if self.axis not in block.coordinates:
                continue
            value = block.coordinates[self.axis]
            if (lower is not None and value < lower) or (
                upper is not None and value > upper
            ):
                results.append(
                    finding(
                        self,
                        f"Programmed {self.axis} value {value:g} on line "
                        f"{block.line_number} is outside the configured minimum "
                        f"{lower if lower is not None else 'not set'} and maximum "
                        f"{upper if upper is not None else 'not set'}. This commanded-value "
                        "check does not prove the physical tool position is safe because work "
                        "offsets, transformations, and machine coordinates can affect motion.",
                        "Stop review and verify the coordinate system, offsets, workholding, "
                        "tooling, and machine travel before simulation.",
                        block,
                        title=f"{self.axis}-axis command exceeds configured travel",
                    )
                )
        return results


class SpindleLimitRule(ValidationRule):
    rule_id = "SPINDLE_MAX_RPM"
    name = "Spindle command exceeds configured maximum"
    description = "Checks explicit S words against the configured maximum RPM."
    default_severity = Severity.BLOCKING
    category = "machine_limits"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        maximum = context.profile.max_spindle_rpm
        if maximum is None:
            return []
        return [
            finding(
                self,
                f"Programmed spindle speed S{block.spindle_speed:g} exceeds the "
                f"configured maximum of {maximum:g} RPM.",
                "Correct the spindle command and verify the cutting tool and holder limits.",
                block,
            )
            for block in context.parsed.blocks
            if block.spindle_speed is not None and block.spindle_speed > maximum
        ]


class FeedLimitRule(ValidationRule):
    rule_id = "FEED_MAX_RATE"
    name = "Feed command exceeds configured maximum"
    description = "Checks explicit F words against the configured maximum feed rate."
    default_severity = Severity.WARNING
    category = "machine_limits"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        maximum = context.profile.max_feed_rate
        if maximum is None:
            return []
        return [
            finding(
                self,
                f"Programmed feed F{block.feed_rate:g} exceeds the configured maximum "
                f"of {maximum:g}. Units depend on the active unit and feed modes.",
                "Verify the feed value, units, feed mode, tooling, and approved process.",
                block,
            )
            for block in context.parsed.blocks
            if block.feed_rate is not None and block.feed_rate > maximum
        ]


class RestrictedCommandRule(ValidationRule):
    rule_id = "RESTRICTED_COMMAND"
    name = "Restricted command detected"
    description = "Reports every G or M command restricted by the profile."
    default_severity = Severity.BLOCKING
    category = "commands"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        restricted = normalized_profile_codes(context.profile.restricted_commands)
        return [
            finding(
                self,
                f"{code} is explicitly restricted by the selected machine profile.",
                "Remove or replace the command only after qualified programmer review.",
                block,
                title=f"Restricted command {code}",
            )
            for block in context.parsed.blocks
            for code in [*block.g_codes, *block.m_codes]
            if code in restricted
        ]


class UnapprovedCommandRule(ValidationRule):
    rule_id = "UNAPPROVED_COMMAND"
    name = "Command is not on the approved list"
    description = "Reports commands omitted from a non-empty profile approval list."
    default_severity = Severity.WARNING
    category = "commands"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        approved_g = normalized_profile_codes(context.profile.approved_g_codes)
        approved_m = normalized_profile_codes(context.profile.approved_m_codes)
        results: list[ValidationResult] = []
        for block in context.parsed.blocks:
            for code in block.g_codes:
                if approved_g and code not in approved_g:
                    results.append(
                        finding(
                            self,
                            f"{code} is absent from the configured approved G-code list.",
                            "Confirm controller support and company approval.",
                            block,
                            title=f"Unapproved command {code}",
                        )
                    )
            for code in block.m_codes:
                if approved_m and code not in approved_m:
                    results.append(
                        finding(
                            self,
                            f"{code} is absent from the configured approved M-code list.",
                            "Confirm controller support and company approval.",
                            block,
                            title=f"Unapproved command {code}",
                        )
                    )
        return results


class WorkOffsetRule(ValidationRule):
    rule_id = "WORK_OFFSET_MISSING"
    name = "Work offset is missing before cutting movement"
    description = "Looks for G54–G59 before the first cutting-feed movement."
    default_severity = Severity.WARNING
    category = "work_offsets"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        recognized = {"G54", "G55", "G56", "G57", "G58", "G59"}
        observed = False
        for block in context.parsed.blocks:
            if any(code in recognized for code in block.g_codes):
                observed = True
            if block.is_cutting_feed:
                if observed:
                    return []
                return [
                    finding(
                        self,
                        "No recognized G54–G59 work offset appears before the first "
                        "cutting-feed movement.",
                        "Confirm the intended work coordinate system before simulation.",
                        block,
                    )
                ]
        return []


class ToolChangeRule(ValidationRule):
    rule_id = "TOOL_CHANGE_WITHOUT_SELECTION"
    name = "Tool change has no selected tool"
    description = "Requires a T word before or on a block containing M06."
    default_severity = Severity.BLOCKING
    category = "tooling"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        selected_tool: int | None = None
        results: list[ValidationResult] = []
        for block in context.parsed.blocks:
            if block.tool_number is not None:
                selected_tool = block.tool_number
            if "M06" in block.m_codes and selected_tool is None:
                results.append(
                    finding(
                        self,
                        "M06 occurs before any tool-selection T word was parsed.",
                        "Select and verify the intended tool before the tool-change command.",
                        block,
                    )
                )
        return results


class SafeStartRule(ValidationRule):
    rule_id = "SAFE_START_MISSING"
    name = "Configured safe-start commands are missing"
    description = "Checks command presence in the first ten command-bearing blocks."
    default_severity = Severity.BLOCKING
    category = "program_structure"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        expected = template_codes(context.profile.safe_start_template)
        if not expected:
            return []
        early = [
            block
            for block in context.parsed.blocks
            if block.g_codes or block.m_codes
        ][:10]
        observed = {
            code for block in early for code in [*block.g_codes, *block.m_codes]
        }
        missing = expected - observed
        if not missing:
            return []
        return [
            finding(
                self,
                f"Expected near the beginning but not found: {', '.join(sorted(missing))}.",
                "Add or verify the approved safe-start commands before simulation.",
                early[0] if early else None,
            )
        ]


class ProgramEndRule(ValidationRule):
    rule_id = "PROGRAM_END_MISSING"
    name = "Program-ending command is missing"
    description = "Checks the ending region for M02, M30, or the configured template."
    default_severity = Severity.BLOCKING
    category = "program_structure"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        ending = context.parsed.blocks[-10:]
        observed = {
            code for block in ending for code in [*block.g_codes, *block.m_codes]
        }
        expected = template_codes(context.profile.program_end_template)
        if {"M02", "M30"} & observed or (expected and expected.issubset(observed)):
            return []
        expected_text = ", ".join(sorted(expected)) if expected else "M02 or M30"
        return [
            finding(
                self,
                f"No recognized M02/M30 end command or complete configured ending "
                f"sequence ({expected_text}) was detected near program completion.",
                "Verify shutdown, compensation cancellation, retract behavior, and "
                "the approved program-ending sequence.",
                ending[-1] if ending else None,
            )
        ]


class CutterCompensationRule(ValidationRule):
    rule_id = "CUTTER_COMP_ACTIVE_AT_END"
    name = "Cutter compensation remains active at program end"
    description = "Reports a final G41 or G42 state without G40 cancellation."
    default_severity = Severity.WARNING
    category = "modal_state"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        if not context.parsed.blocks:
            return []
        final = context.parsed.blocks[-1]
        state = final.modal_state.cutter_compensation
        if state not in {"G41", "G42"}:
            return []
        return [
            finding(
                self,
                f"The final tracked cutter-compensation state is {state}.",
                "Verify an appropriate G40 cancellation before program completion.",
                final,
            )
        ]


class ToolLengthCompensationRule(ValidationRule):
    rule_id = "TOOL_LENGTH_COMP_ACTIVE_AT_END"
    name = "Tool-length compensation remains active at program end"
    description = "Reports a final G43 or G44 state without cancellation."
    default_severity = Severity.WARNING
    category = "modal_state"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        if not context.parsed.blocks:
            return []
        final = context.parsed.blocks[-1]
        state = final.modal_state.tool_length_compensation
        if state not in {"G43", "G44"}:
            return []
        return [
            finding(
                self,
                f"The final tracked tool-length compensation state is {state}.",
                "Verify the configured cancellation behavior, commonly G49, before completion.",
                final,
            )
        ]


class RapidZRule(ValidationRule):
    rule_id = "RAPID_Z_REVIEW"
    name = "Rapid Z move requires review"
    description = "Heuristically flags rapid Z targets below the profile threshold."
    default_severity = Severity.WARNING
    category = "motion"

    def validate(self, context: ValidationContext) -> list[ValidationResult]:
        threshold = context.profile.rapid_z_review_threshold
        if threshold is None:
            threshold = 0.0
        return [
            finding(
                self,
                f"Rapid motion commands Z{block.coordinates['Z']:g}, below the configured "
                f"review threshold Z{threshold:g}. This heuristic is not proof of a collision.",
                "Review clearance, offsets, fixture height, retract strategy, and simulation.",
                block,
                confidence=0.85,
            )
            for block in context.parsed.blocks
            if block.is_rapid
            and "Z" in block.coordinates
            and block.coordinates["Z"] < threshold
        ]


DEFAULT_RULES: tuple[ValidationRule, ...] = (
    ParseErrorRule(),
    AxisLimitRule("X"),
    AxisLimitRule("Y"),
    AxisLimitRule("Z"),
    SpindleLimitRule(),
    FeedLimitRule(),
    RestrictedCommandRule(),
    UnapprovedCommandRule(),
    WorkOffsetRule(),
    ToolChangeRule(),
    SafeStartRule(),
    ProgramEndRule(),
    CutterCompensationRule(),
    ToolLengthCompensationRule(),
    RapidZRule(),
)


class ValidationEngine:
    """Run configured deterministic rules; AI is never part of this path."""

    def __init__(self, rules: tuple[ValidationRule, ...] = DEFAULT_RULES):
        self.rules = rules

    def validate(
        self, parsed: ParseResult, profile: MachineProfile
    ) -> list[ValidationResult]:
        context = ValidationContext(parsed=parsed, profile=profile)
        return [
            result
            for rule in self.rules
            for result in rule.validate(context)
        ]

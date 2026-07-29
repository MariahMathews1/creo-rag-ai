from collections import Counter
from dataclasses import asdict
from difflib import SequenceMatcher
import re

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.analysis_projects import (
    revision_snapshot,
    validation_profile_from_snapshot,
)
from app.models.entities import AnalysisFinding, AnalysisProject, Severity
from app.models.profile_extraction import MachineProfileRevision
from app.models.program_standards import (
    ProgramComparisonFinding,
    ProgramComparisonRun,
    ReferenceProgram,
    ReferenceProgramBlock,
    StandardConvention,
    StandardConventionEvidence,
    StandardExtractionRun,
)
from app.parsers.gcode import GCodeParser, ParsedGCodeBlock
from app.validators.engine import ValidationEngine

PARSER_VERSION = "gcode-parser-v1"
RULE_SET_VERSION = "validation-v1"
ALGORITHM_VERSION = "standards-v1"
COMPARISON_VERSION = "comparison-v1"


def parse_reference_program(program: ReferenceProgram, db: Session) -> ReferenceProgram:
    revision = db.get(MachineProfileRevision, program.machine_profile_revision_id)
    if not revision:
        raise ValueError("Machine-profile revision does not exist")
    machine = revision_snapshot(revision)
    profile = validation_profile_from_snapshot(machine)
    parsed = GCodeParser(set(profile.supported_work_offsets or [])).parse(
        program.source_text
    )
    validation = ValidationEngine().validate(parsed, profile)
    db.execute(delete(ReferenceProgramBlock).where(
        ReferenceProgramBlock.reference_program_id == program.id
    ))
    previous_state: dict = {}
    for index, block in enumerate(parsed.blocks):
        state_after = asdict(block.modal_state)
        db.add(ReferenceProgramBlock(
            reference_program_id=program.id,
            block_index=index,
            line_number=block.line_number,
            original_text=block.original_text,
            cleaned_text=block.cleaned_text,
            sequence_number=block.sequence_number,
            program_number=block.program_number,
            g_codes_json=block.g_codes,
            m_codes_json=block.m_codes,
            coordinates_json=block.coordinates,
            comments_json=block.comments,
            state_before_json=previous_state,
            state_after_json=state_after,
            parse_errors_json=block.parse_errors,
            parser_version=PARSER_VERSION,
        ))
        previous_state = state_after
    blocking = sum(item.severity == Severity.BLOCKING for item in validation)
    warning = sum(item.severity == Severity.WARNING for item in validation)
    program_numbers = [
        block.program_number for block in parsed.blocks
        if block.program_number is not None
    ]
    if program_numbers:
        program.program_number = str(program_numbers[0])
    program.parsing_status = "parsed_with_findings" if validation else "parsed"
    program.parser_version = PARSER_VERSION
    program.rule_set_version = RULE_SET_VERSION
    program.validation_summary_json = {
        "block_count": len(parsed.blocks),
        "parse_error_count": len(parsed.errors),
        "finding_count": len(validation),
        "blocking_count": blocking,
        "warning_count": warning,
        "findings": [{
            "rule_id": item.rule_id,
            "severity": item.severity.value,
            "title": item.title,
            "line_number": item.line_number,
        } for item in validation],
    }
    if blocking and program.eligibility_status == "pending":
        program.eligibility_status = "requires_review"
        program.eligibility_reason = (
            f"{blocking} blocking deterministic finding(s) require suitability review."
        )
    db.flush()
    return program


def _codes(block: ReferenceProgramBlock) -> set[str]:
    return set([*block.g_codes_json, *block.m_codes_json])


def _exec_blocks(program: ReferenceProgram) -> list[ReferenceProgramBlock]:
    return [
        block for block in program.blocks
        if block.cleaned_text and block.cleaned_text != "%"
    ]


def _find_code(
    blocks: list[ReferenceProgramBlock], codes: set[str]
) -> ReferenceProgramBlock | None:
    return next((block for block in blocks if _codes(block) & codes), None)


def frequency_classification(support: int, total: int) -> str:
    if total < 2:
        return "insufficient_evidence"
    ratio = support / total
    if ratio == 1:
        return "universal_observed"
    if ratio >= .75:
        return "common"
    if ratio >= .4:
        return "occasional"
    return "exceptional"


def _pattern_specs(programs: list[ReferenceProgram]) -> list[dict]:
    offsets = Counter()
    for program in programs:
        for block in _exec_blocks(program):
            offsets.update(code for code in block.g_codes_json if code in {
                "G54", "G55", "G56", "G57", "G58", "G59",
            })
    common_offset = offsets.most_common(1)[0][0] if offsets else "G54"
    return [
        {"key": "percent_delimiters", "category": "program_structure",
         "title": "Program uses opening and closing percent delimiters",
         "type": "required_presence", "scope": "whole", "codes": [],
         "predicate": lambda p, b: (
             p.source_text.strip().startswith("%")
             and p.source_text.strip().endswith("%"), b[0] if b else None)},
        {"key": "program_number", "category": "program_structure",
         "title": "Program includes an O-number", "type": "format_pattern",
         "scope": "whole", "codes": [],
         "predicate": lambda p, b: (
             any(x.program_number is not None for x in b),
             next((x for x in b if x.program_number is not None), None))},
        {"key": "safe_start_units", "category": "safe_start",
         "title": "Safe start selects units", "type": "required_presence",
         "scope": "start", "codes": ["G20", "G21"],
         "predicate": lambda p, b: (bool(_find_code(b[:10], {"G20", "G21"})),
                                    _find_code(b[:10], {"G20", "G21"}))},
        {"key": "safe_start_plane", "category": "safe_start",
         "title": "Safe start selects a working plane", "type": "required_presence",
         "scope": "start", "codes": ["G17", "G18", "G19"],
         "predicate": lambda p, b: (bool(_find_code(b[:10], {"G17", "G18", "G19"})),
                                    _find_code(b[:10], {"G17", "G18", "G19"}))},
        {"key": "safe_start_absolute", "category": "safe_start",
         "title": "Safe start selects absolute positioning", "type": "required_presence",
         "scope": "start", "codes": ["G90"],
         "predicate": lambda p, b: (bool(_find_code(b[:10], {"G90"})),
                                    _find_code(b[:10], {"G90"}))},
        {"key": "safe_start_cancellations", "category": "safe_start",
         "title": "Safe start cancels compensation and cycles",
         "type": "ordered_sequence", "scope": "start",
         "codes": ["G40", "G49", "G80"],
         "predicate": lambda p, b: (
             {"G40", "G80"} <= set().union(*[_codes(x) for x in b[:10]]) if b else False,
             b[min(4, len(b) - 1)] if b else None)},
        {"key": "common_work_offset", "category": "coordinates_offsets",
         "title": f"Programs commonly select {common_offset}",
         "type": "preferred_value", "scope": "whole", "codes": [common_offset],
         "predicate": lambda p, b, code=common_offset: (
             bool(_find_code(b, {code})), _find_code(b, {code}))},
        {"key": "coolant_off_end", "category": "program_ending",
         "title": "Coolant is turned off before program end",
         "type": "required_presence", "scope": "end", "codes": ["M09"],
         "predicate": lambda p, b: (bool(_find_code(b[-12:], {"M09"})),
                                    _find_code(b[-12:], {"M09"}))},
        {"key": "spindle_stop_end", "category": "program_ending",
         "title": "Spindle is stopped before program end",
         "type": "required_presence", "scope": "end", "codes": ["M05"],
         "predicate": lambda p, b: (bool(_find_code(b[-12:], {"M05"})),
                                    _find_code(b[-12:], {"M05"}))},
        {"key": "reference_return_end", "category": "program_ending",
         "title": "Program ending includes reference return",
         "type": "allowed_set", "scope": "end", "codes": ["G28", "G53"],
         "predicate": lambda p, b: (bool(_find_code(b[-12:], {"G28", "G53"})),
                                    _find_code(b[-12:], {"G28", "G53"}))},
        {"key": "m30_end", "category": "program_ending",
         "title": "Program ends with M30", "type": "required_presence",
         "scope": "end", "codes": ["M30"],
         "predicate": lambda p, b: (bool(_find_code(b[-6:], {"M30"})),
                                    _find_code(b[-6:], {"M30"}))},
        {"key": "sequence_numbers", "category": "formatting",
         "title": "Executable blocks use sequence numbers",
         "type": "frequency_pattern", "scope": "whole", "codes": [],
         "predicate": lambda p, b: (
             bool(b) and sum(x.sequence_number is not None for x in b) / len(b) >= .6,
             next((x for x in b if x.sequence_number is not None), None))},
        {"key": "parenthesis_comments", "category": "formatting",
         "title": "Comments use parenthesis style", "type": "format_pattern",
         "scope": "whole", "codes": [],
         "predicate": lambda p, b: (
             bool(re.search(r"\\([^)]*\\)", p.source_text)),
             next((x for x in b if x.comments_json), None))},
        {"key": "css_clamp", "category": "spindle",
         "title": "G96 constant-surface-speed use is preceded by a spindle clamp",
         "type": "conditional_pattern", "scope": "conditional",
         "codes": ["G50"], "condition_codes": ["G96"],
         "predicate": lambda p, b: _css_clamp(b)},
        {"key": "drilling_cycle_cancel", "category": "motion_cycles",
         "title": "A drilling cycle is cancelled with G80 before the next operation",
         "type": "conditional_pattern", "scope": "conditional",
         "codes": ["G80"], "condition_codes": ["G81", "G82", "G83"],
         "predicate": lambda p, b: _conditional_followup(
             b, {"G81", "G82", "G83"}, {"G80"}
         )},
        {"key": "tool_call_format", "category": "tool_change",
         "title": "Programs use explicit T-word tool calls",
         "type": "format_pattern", "scope": "whole", "codes": [],
         "predicate": lambda p, b: (
             any(re.search(r"\\bT\\d+", x.cleaned_text, re.I) for x in b),
             next((x for x in b if re.search(r"\\bT\\d+", x.cleaned_text, re.I)), None))},
    ]


def _css_clamp(blocks: list[ReferenceProgramBlock]):
    css_index = next(
        (index for index, block in enumerate(blocks) if "G96" in block.g_codes_json),
        None,
    )
    if css_index is None:
        return True, None
    clamp = _find_code(blocks[max(0, css_index - 8):css_index], {"G50"})
    return bool(clamp), clamp or blocks[css_index]


def _conditional_followup(
    blocks: list[ReferenceProgramBlock],
    condition_codes: set[str],
    expected_codes: set[str],
):
    condition_index = next(
        (index for index, block in enumerate(blocks)
         if _codes(block) & condition_codes),
        None,
    )
    if condition_index is None:
        return True, None
    match = _find_code(blocks[condition_index + 1:], expected_codes)
    return bool(match), match or blocks[condition_index]


def extract_conventions(
    run: StandardExtractionRun,
    programs: list[ReferenceProgram],
    db: Session,
) -> list[StandardConvention]:
    db.execute(delete(StandardConvention).where(
        StandardConvention.extraction_run_id == run.id
    ))
    total = len(programs)
    conventions: list[StandardConvention] = []
    post_versions = sorted({
        item.post_processor_revision or item.post_processor_version or "unspecified"
        for item in programs
    })
    for spec in _pattern_specs(programs):
        observations = []
        for program in programs:
            blocks = _exec_blocks(program)
            supports, evidence_block = spec["predicate"](program, blocks)
            observations.append((program, supports, evidence_block, blocks))
        support = sum(item[1] for item in observations)
        percentage = round(support / max(total, 1) * 100, 1)
        classification = frequency_classification(support, total)
        convention = StandardConvention(
            extraction_run_id=run.id,
            convention_key=spec["key"],
            category=spec["category"],
            title=spec["title"],
            description=(
                f"Observed in {support} of {total} eligible programs. "
                "Frequency is historical evidence, not an organizational requirement "
                "until a reviewer accepts this proposal."
            ),
            convention_type=spec["type"],
            expected_pattern_json={
                "scope": spec["scope"],
                "codes": spec.get("codes", []),
            },
            condition_json=(
                {"codes_present": spec["condition_codes"]}
                if spec.get("condition_codes") else {}
            ),
            expected_behavior_json=(
                {"codes_present_before_condition": spec.get("codes", [])}
                if spec.get("condition_codes") else {}
            ),
            applicability_json={
                "machine_profile_revision_ids": [run.machine_profile_revision_id],
                "post_processor_versions": post_versions,
                "program_types": sorted({item.program_type for item in programs}),
                "units": sorted({item.units for item in programs if item.units}),
            },
            severity="review_recommended",
            confidence=round(support / max(total, 1), 3),
            support_count=support,
            eligible_program_count=total,
            support_percentage=percentage,
            frequency_classification=classification,
            proposal_status=(
                "conflicting" if 0 < support < total
                else "proposed" if support else "insufficient_evidence"
            ),
            review_status="pending",
            safety_relevant=spec["category"] in {
                "safe_start", "program_ending", "spindle", "tool_change",
            },
        )
        db.add(convention)
        db.flush()
        for program, supports, block, blocks in observations:
            fallback = (
                blocks[-1] if spec["scope"] == "end" and blocks
                else blocks[0] if blocks else None
            )
            cited = block or fallback
            db.add(StandardConventionEvidence(
                standard_convention_id=convention.id,
                reference_program_id=program.id,
                gcode_block_id=cited.id if cited else None,
                line_start=cited.line_number if cited else None,
                line_end=cited.line_number if cited else None,
                excerpt=cited.original_text if cited else "(No matching executable block)",
                evidence_type="supporting" if supports else "contradicting",
                match_context_json={
                    "post_processor_revision": (
                        program.post_processor_revision
                        or program.post_processor_version
                    ),
                    "program_type": program.program_type,
                    "heuristic": True,
                },
            ))
        conventions.append(convention)
    run.status = "review_required"
    run.summary_json = {
        "eligible_program_count": total,
        "proposal_count": len(conventions),
        "conflict_count": sum(
            item.proposal_status == "conflicting" for item in conventions
        ),
        "post_processor_revisions": post_versions,
        "heterogeneous": len(post_versions) > 1,
        "frequency_is_not_requirement": True,
    }
    return conventions


def _parsed_analysis(project: AnalysisProject):
    return GCodeParser().parse(project.gcode_source or "")


def _analysis_blocks(project: AnalysisProject) -> list[ParsedGCodeBlock]:
    return [
        block for block in _parsed_analysis(project).blocks
        if block.cleaned_text and block.cleaned_text != "%"
    ]


def _matches_convention(
    convention: StandardConvention,
    project: AnalysisProject,
) -> tuple[str, ParsedGCodeBlock | None, dict]:
    blocks = _analysis_blocks(project)
    expected = convention.expected_pattern_json or {}
    codes = set(expected.get("codes") or [])
    scope = expected.get("scope", "whole")
    selected = blocks[:10] if scope == "start" else blocks[-12:] if scope == "end" else blocks
    condition_codes = set((convention.condition_json or {}).get("codes_present") or [])
    if condition_codes and not any(
        set(block.g_codes) & condition_codes for block in blocks
    ):
        return "not_applicable", None, {"condition_observed": False}
    if convention.convention_key == "percent_delimiters":
        matched = (
            (project.gcode_source or "").strip().startswith("%")
            and (project.gcode_source or "").strip().endswith("%")
        )
        return ("matches" if matched else "missing"), None, {"observed": matched}
    if convention.convention_key == "program_number":
        block = next((item for item in blocks if item.program_number is not None), None)
        return ("matches" if block else "missing"), block, {
            "program_number": block.program_number if block else None
        }
    if convention.convention_key == "sequence_numbers":
        ratio = sum(item.sequence_number is not None for item in blocks) / max(len(blocks), 1)
        return ("matches" if ratio >= .6 else "differs"), blocks[0] if blocks else None, {
            "sequence_number_percentage": round(ratio * 100, 1)
        }
    if convention.convention_key == "parenthesis_comments":
        matched = bool(re.search(r"\([^)]*\)", project.gcode_source or ""))
        return ("matches" if matched else "differs"), blocks[0] if blocks else None, {
            "parenthesis_comments": matched
        }
    if convention.convention_key == "tool_call_format":
        block = next(
            (item for item in blocks if re.search(r"\bT\d+", item.cleaned_text, re.I)),
            None,
        )
        return ("matches" if block else "missing"), block, {"tool_call_seen": bool(block)}
    block = next(
        (item for item in selected if set([*item.g_codes, *item.m_codes]) & codes),
        None,
    )
    return ("matches" if block else "missing"), block, {
        "observed_codes": sorted(set().union(*[
            set([*item.g_codes, *item.m_codes]) for item in selected
        ]) if selected else set())
    }


def compare_program(
    comparison: ProgramComparisonRun,
    project: AnalysisProject,
    conventions: list[StandardConvention],
    db: Session,
) -> ProgramComparisonRun:
    db.execute(delete(ProgramComparisonFinding).where(
        ProgramComparisonFinding.comparison_run_id == comparison.id
    ))
    counts = Counter()
    for convention in conventions:
        comparison_type, block, observed = _matches_convention(convention, project)
        counts[comparison_type] += 1
        descriptions = {
            "matches": "Matches a recurring organizational pattern.",
            "missing": "The current program omits a pattern accepted in this standard.",
            "differs": "The current program differs from previously reviewed examples.",
            "not_applicable": "The convention condition was not observed in this program.",
        }
        db.add(ProgramComparisonFinding(
            comparison_run_id=comparison.id,
            standard_convention_id=convention.id,
            severity=(
                "review_recommended"
                if comparison_type in {"missing", "differs"} else "informational"
            ),
            status="open",
            title=convention.title,
            description=descriptions[comparison_type],
            line_number=block.line_number if block else None,
            source_line=block.original_text if block else None,
            expected_pattern_json=convention.expected_pattern_json,
            observed_pattern_json=observed,
            comparison_type=comparison_type,
            recommendation=(
                "Review applicability to the exact machine, setup, operation, and post "
                "revision. The reason for this difference is unknown."
                if comparison_type in {"missing", "differs"}
                else "No action inferred; historical similarity is not certification."
            ),
        ))
    # An explicit ending command outside the accepted M30 pattern remains a
    # historical difference, not a deterministic safety violation.
    unusual = next(
        (block for block in _analysis_blocks(project) if "M02" in block.m_codes),
        None,
    )
    if unusual:
        counts["unexpected"] += 1
        db.add(ProgramComparisonFinding(
            comparison_run_id=comparison.id,
            standard_convention_id=None,
            severity="review_recommended",
            status="open",
            title="Unexpected alternate program end",
            description="M02 differs from the accepted M30 organizational pattern.",
            line_number=unusual.line_number,
            source_line=unusual.original_text,
            expected_pattern_json={"codes": ["M30"]},
            observed_pattern_json={"codes": ["M02"]},
            comparison_type="unexpected",
            recommendation=(
                "Review the programmer intent and post revision; do not modify the "
                "standard automatically from this exception."
            ),
        ))
    comparison.status = "completed"
    comparison.completed_at = __import__(
        "app.models.entities", fromlist=["utc_now"]
    ).utc_now()
    comparison.summary_json = {
        "finding_count": sum(counts.values()),
        **{key: counts[key] for key in (
            "matches", "differs", "missing", "unexpected", "not_applicable",
        )},
        "deterministic_finding_count": db.scalar(
            select(func.count(AnalysisFinding.id)).where(
                AnalysisFinding.analysis_project_id == project.id
            )
        ) or 0,
        "historical_similarity_is_not_certification": True,
    }
    return comparison


def similarity(program: ReferenceProgram, project: AnalysisProject) -> tuple[float, list[str], list[str]]:
    current = _parsed_analysis(project)
    current_codes = set().union(*[
        set([*block.g_codes, *block.m_codes]) for block in current.blocks
    ]) if current.blocks else set()
    reference_codes = set().union(*[
        _codes(block) for block in program.blocks
    ]) if program.blocks else set()
    union = current_codes | reference_codes
    code_score = len(current_codes & reference_codes) / max(len(union), 1)
    reasons = ["Same machine profile"]
    differences = []
    if program.machine_profile_revision_id == project.machine_profile_revision_id:
        reasons.append("Same machine-profile revision")
        revision_score = 1
    else:
        differences.append("Different machine-profile revision")
        revision_score = 0
    if current_codes & reference_codes:
        reasons.append(
            f"{len(current_codes & reference_codes)} shared normalized command families"
        )
    differences.extend(
        f"Only in reference: {code}" for code in sorted(reference_codes - current_codes)[:5]
    )
    score = round((code_score * .8 + revision_score * .2) * 100, 1)
    return score, reasons, differences


def line_sections(current: str, reference: str) -> list[dict]:
    left = current.splitlines()
    right = reference.splitlines()
    matcher = SequenceMatcher(a=right, b=left, autojunk=False)
    sections = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        sections.append({
            "type": {
                "equal": "common", "insert": "added",
                "delete": "removed", "replace": "changed",
            }[tag],
            "reference_line_start": i1 + 1,
            "current_line_start": j1 + 1,
            "reference_lines": right[i1:i2],
            "current_lines": left[j1:j2],
        })
    return sections

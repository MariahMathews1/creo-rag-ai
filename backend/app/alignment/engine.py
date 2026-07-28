from dataclasses import dataclass
import math
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alignment.events import ManufacturingEvent, cl_event, gcode_event
from app.cl_parser.normalization import convert_value
from app.core.config import Settings
from app.models.entities import AnalysisProject, utc_now
from app.models.traceability import (
    AlignmentIssue, AlignmentLink, AlignmentRun, CLRecord, GCodeBlock,
)

SAFETY_NOTICE = (
    "CL-to-G-code alignment is an analytical aid only. It does not certify "
    "post-processor correctness, machining safety, or production readiness. "
    "Review and simulation by a qualified CNC programmer remain required."
)


@dataclass(slots=True)
class Candidate:
    cl: ManufacturingEvent
    gcode: ManufacturingEvent
    score: float
    reasons: list[str]
    mismatches: list[str]
    components: dict[str, float]


def _percent_match(left: float | None, right: float | None, tolerance: float) -> bool:
    if left is None or right is None:
        return False
    return abs(left - right) / max(abs(left), 1.0) * 100 <= tolerance


def score_candidate(
    cl: ManufacturingEvent,
    gc: ManufacturingEvent,
    settings: Settings,
    cl_units: str | None,
    gc_units: str | None,
    total: int,
) -> Candidate:
    reasons: list[str] = []
    mismatches: list[str] = []
    components: dict[str, float] = {}
    compatible = cl.event_type == gc.event_type or {
        cl.event_type, gc.event_type
    } <= {"feed", "motion"}
    components["event_type"] = 1.0 if compatible else 0.0
    if compatible:
        reasons.append(f"Compatible {cl.event_type} manufacturing event")
    order_delta = abs(cl.order_index / max(total, 1) - gc.order_index / max(total, 1))
    components["order"] = max(0.0, 1.0 - order_delta * 2)
    if components["order"] > 0.7:
        reasons.append("Relative source order is consistent")
    if (
        cl.event_type in {"tool", "motion", "arc", "cycle"}
        and gc.event_type in {"tool", "motion", "arc", "cycle"}
        and cl.tool_number is not None and gc.tool_number is not None
    ):
        components["tool"] = 1.0 if cl.tool_number == gc.tool_number else 0.0
        (reasons if components["tool"] else mismatches).append(
            "Tool numbers match" if components["tool"] else
            f"Tool mismatch: CL T{cl.tool_number}, G-code T{gc.tool_number}"
        )
    if cl.feed_rate is not None and gc.feed_rate is not None:
        components["feed"] = 1.0 if _percent_match(
            cl.feed_rate, gc.feed_rate, settings.alignment_feed_tolerance_percent
        ) else 0.0
        (reasons if components["feed"] else mismatches).append(
            "Feed values are within tolerance" if components["feed"] else
            f"Feed mismatch: CL {cl.feed_rate:g}, G-code {gc.feed_rate:g}"
        )
    if cl.spindle_speed is not None and gc.spindle_speed is not None:
        components["spindle"] = 1.0 if _percent_match(
            cl.spindle_speed, gc.spindle_speed,
            settings.alignment_spindle_tolerance_percent,
        ) else 0.0
        (reasons if components["spindle"] else mismatches).append(
            "Spindle values are within tolerance" if components["spindle"] else
            f"Spindle mismatch: CL {cl.spindle_speed:g}, G-code {gc.spindle_speed:g}"
        )
    if cl.coolant_state and gc.coolant_state:
        components["coolant"] = 1.0 if cl.coolant_state == gc.coolant_state else 0.0
        (reasons if components["coolant"] else mismatches).append(
            "Coolant states match" if components["coolant"] else "Coolant states differ"
        )
    common_axes = set(cl.coordinates) & set(gc.coordinates) & {"X", "Y", "Z"}
    if common_axes:
        if cl_units and gc_units:
            distances = [
                abs(convert_value(cl.coordinates[a], cl_units, gc_units) - gc.coordinates[a])
                for a in common_axes
            ]
            components["coordinates"] = 1.0 if max(distances) <= settings.alignment_coordinate_tolerance else 0.0
            (reasons if components["coordinates"] else mismatches).append(
                "Coordinates match within normalized tolerance" if components["coordinates"]
                else "Coordinate values differ; offsets or transformations may apply"
            )
            if cl_units != gc_units:
                reasons.append(f"Converted CL {cl_units} coordinates to {gc_units}")
        else:
            components["coordinates"] = 0.35
            mismatches.append("Units are unknown; coordinate comparison confidence reduced")
    weights = {"event_type": .30, "order": .15, "coordinates": .25, "tool": .20,
               "feed": .15, "spindle": .15, "coolant": .15}
    present = sum(weights[key] for key in components)
    score = sum(components[key] * weights[key] for key in components) / max(present, 0.01)
    if not compatible:
        score *= 0.35
    return Candidate(cl, gc, round(min(score, 1.0), 4), reasons, mismatches, components)


def run_alignment(project: AnalysisProject, db: Session, settings: Settings) -> AlignmentRun:
    started = perf_counter()
    cl_records = list(db.scalars(select(CLRecord).where(
        CLRecord.analysis_project_id == project.id
    ).order_by(CLRecord.record_index)))
    blocks = list(db.scalars(select(GCodeBlock).where(
        GCodeBlock.analysis_project_id == project.id
    ).order_by(GCodeBlock.block_index)))
    version = (db.scalar(select(AlignmentRun.version).where(
        AlignmentRun.analysis_project_id == project.id
    ).order_by(AlignmentRun.version.desc()).limit(1)) or 0) + 1
    for old in project.alignment_runs:
        old.stale = old.stale or (
            old.source_integrity_json.get("cl_hash") != project.cl_file_hash
            or old.source_integrity_json.get("gcode_hash") != project.gcode_file_hash
        )
    run = AlignmentRun(
        analysis_project_id=project.id, version=version,
        settings_json={
            "min_confidence": settings.alignment_min_confidence,
            "coordinate_tolerance": settings.alignment_coordinate_tolerance,
            "candidate_window": settings.alignment_candidate_window,
        },
        source_integrity_json={
            "cl_hash": project.cl_file_hash, "gcode_hash": project.gcode_file_hash,
            "machine_updated_at": project.machine_profile.updated_at.isoformat(),
            "parser_versions": ["cl-parser-v1", "gcode-parser-v1"],
        },
    )
    db.add(run); db.flush()
    cl_events = [cl_event(value) for value in cl_records]
    gc_events = [gcode_event(value) for value in blocks]
    cl_units = next((r.state_after_json.get("units") for r in cl_records if r.state_after_json.get("units")), None)
    gc_units = next((b.state_after_json.get("units") for b in blocks if b.state_after_json.get("units")), None)
    gc_units = {"G20": "inch", "G21": "mm"}.get(gc_units, gc_units)
    candidates: list[Candidate] = []
    total = max(len(cl_events), len(gc_events))
    alignable_types = {
        "tool", "spindle", "feed", "coolant", "motion", "arc", "cycle",
        "stop", "completion",
    }
    for ce in cl_events:
        if ce.event_type not in alignable_types:
            continue
        projected = int(ce.order_index / max(len(cl_events), 1) * len(gc_events))
        for ge in gc_events[max(0, projected-settings.alignment_candidate_window):projected+settings.alignment_candidate_window+1]:
            if ge.event_type not in alignable_types:
                continue
            candidate = score_candidate(ce, ge, settings, cl_units, gc_units, total)
            if candidate.score >= settings.alignment_min_confidence:
                candidates.append(candidate)
    candidates.sort(key=lambda value: (-value.score, value.cl.order_index, value.gcode.order_index))
    used_cl: set[int] = set()
    used_gc: set[int] = set()
    linked_pairs: set[tuple[int, int]] = set()
    cl_to_gc: dict[int, int] = {}
    for candidate in candidates:
        if candidate.cl.source_record_id in used_cl or candidate.gcode.source_record_id in used_gc:
            continue
        used_cl.add(candidate.cl.source_record_id); used_gc.add(candidate.gcode.source_record_id)
        linked_pairs.add((candidate.cl.source_record_id, candidate.gcode.source_record_id))
        cl_to_gc[candidate.cl.source_record_id] = candidate.gcode.source_record_id
        db.add(AlignmentLink(
            alignment_run_id=run.id, cl_record_id=candidate.cl.source_record_id,
            gcode_block_id=candidate.gcode.source_record_id,
            link_type="direct", confidence=candidate.score,
            match_reasons_json=candidate.reasons,
            mismatch_reasons_json=candidate.mismatches,
            score_components_json=candidate.components,
        ))
    # Specialized one-to-many tool output (for example separate T08 and M06 blocks).
    for ce in (event for event in cl_events if event.event_type == "tool"):
        tool_outputs = [
            ge for ge in gc_events
            if ge.event_type == "tool" and ge.tool_number == ce.tool_number
        ]
        if len(tool_outputs) > 1:
            for ge in tool_outputs:
                if (ce.source_record_id, ge.source_record_id) in linked_pairs:
                    continue
                candidate = score_candidate(ce, ge, settings, cl_units, gc_units, total)
                db.add(AlignmentLink(
                    alignment_run_id=run.id, cl_record_id=ce.source_record_id,
                    gcode_block_id=ge.source_record_id, link_type="one_to_many",
                    confidence=max(candidate.score, settings.alignment_medium_confidence),
                    match_reasons_json=["Tool load may emit selection and change blocks", *candidate.reasons],
                    mismatch_reasons_json=candidate.mismatches,
                    score_components_json=candidate.components,
                ))
                linked_pairs.add((ce.source_record_id, ge.source_record_id))
                used_cl.add(ce.source_record_id); used_gc.add(ge.source_record_id)
    # RAPID is state for the following GOTO; both may explain one G00 block.
    for index, record in enumerate(cl_records[:-1]):
        following = cl_records[index + 1]
        if record.command == "RAPID" and following.command == "GOTO":
            gcode_id = cl_to_gc.get(following.id)
            if gcode_id and (record.id, gcode_id) not in linked_pairs:
                db.add(AlignmentLink(
                    alignment_run_id=run.id, cl_record_id=record.id,
                    gcode_block_id=gcode_id, link_type="many_to_one",
                    confidence=settings.alignment_medium_confidence,
                    match_reasons_json=["RAPID modal state applies to the following CL motion"],
                    mismatch_reasons_json=["Relationship is contextual rather than geometric"],
                    score_components_json={"specialized_rapid_rule": 1.0},
                ))
                used_cl.add(record.id)
    for record in cl_records:
        if record.id not in used_cl and record.command not in {"COMMENT"}:
            db.add(AlignmentIssue(
                alignment_run_id=run.id, issue_type=(
                    "unsupported_cl_command" if record.command == "UNKNOWN"
                    else "unmatched_cl_record"
                ), cl_record_id=record.id, title="CL record requires review",
                description="No deterministic candidate met the alignment threshold.",
                recommendation="Review whether this record is state-only, suppressed, cycle-absorbed, or missing from output.",
            ))
    for block in blocks:
        if block.id not in used_gc and block.cleaned_text:
            db.add(AlignmentIssue(
                alignment_run_id=run.id, issue_type="unmatched_gcode_block",
                gcode_block_id=block.id, title="G-code block requires review",
                description="No deterministic CL candidate met the alignment threshold.",
                recommendation="Review for post-added setup, safety, macro, header, or footer behavior.",
            ))
    db.flush()
    links = list(run.links)
    high = sum(link.confidence >= settings.alignment_high_confidence for link in links)
    medium = sum(settings.alignment_medium_confidence <= link.confidence < settings.alignment_high_confidence for link in links)
    low = len(links) - high - medium
    summary = {
        "cl_record_count": len(cl_records), "gcode_block_count": len(blocks),
        "proposed_link_count": len(links), "high_confidence_link_count": high,
        "medium_confidence_link_count": medium, "low_confidence_link_count": low,
        "unmatched_cl_record_count": sum(i.cl_record_id is not None for i in run.issues),
        "unmatched_gcode_block_count": sum(i.gcode_block_id is not None for i in run.issues),
        "confirmed_link_count": 0, "rejected_link_count": 0,
        "traceability_coverage": round(len(used_cl) / max(len(cl_records), 1) * 100, 1),
        "review_required": True, "advisory_only": True,
    }
    run.summary_json = summary
    run.metrics_json = {
        "alignment_duration_ms": round((perf_counter()-started)*1000, 2),
        "peak_candidate_count": len(candidates), "link_count": len(links),
        "issue_count": len(run.issues),
    } if settings.enable_alignment_debug else {}
    run.status = "review_required"
    run.completed_at = utc_now()
    project.alignment_status = "review_required"
    project.alignment_version = version
    project.alignment_summary_json = summary
    db.commit(); db.refresh(run)
    return run

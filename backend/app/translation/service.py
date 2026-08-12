from dataclasses import asdict
from hashlib import sha256
import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.analysis_projects import revision_snapshot, validation_profile_from_snapshot
from app.cl_parser.parser import CLParser
from app.models.entities import MachineProfile
from app.models.profile_extraction import MachineProfileRevision
from app.models.translation import TranslationAlignment, TranslationAlignmentLink, TranslationExample
from app.parsers.gcode import GCodeParser
from app.validators.engine import ValidationEngine

ALGORITHM_VERSION = "translation-alignment-v1"


def normalize_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"


def source_hash(value: str) -> str:
    return sha256(normalize_text(value).encode()).hexdigest()


def parse_and_validate(example: TranslationExample, machine: MachineProfile, revision: MachineProfileRevision) -> None:
    cl = CLParser().parse(example.cl_source_text)
    gc = GCodeParser(set(revision.supported_work_offsets_json or machine.supported_work_offsets or [])).parse(example.gcode_source_text)
    example.parsed_cl_records_json = [{"index": r.record_index, "line": r.line_number, "text": r.original_text,
        "command": r.original_command or r.command, "tool": r.tool_number, "rpm": r.spindle_speed, "feed": r.feed_rate,
        "coolant": r.coolant_state, "motion": r.motion_type, "coordinates": r.coordinates, "errors": r.parse_errors} for r in cl.records]
    example.parsed_gcode_blocks_json = [{"index": i, "line": b.line_number, "text": b.original_text,
        "g_codes": b.g_codes, "m_codes": b.m_codes, "tool": b.tool_number, "rpm": b.spindle_speed,
        "feed": b.feed_rate, "motion": b.modal_state.motion_mode, "coordinates": b.coordinates,
        "arc_offsets": b.arc_offsets, "arc_radius": b.arc_radius,
        "plane": b.modal_state.plane, "distance_mode": b.modal_state.distance_mode,
        "work_offset": b.work_offset, "state_before": asdict(b.state_before),
        "comments": b.comments, "errors": b.parse_errors} for i, b in enumerate(gc.blocks)]
    example.cl_parse_summary_json = {"cl_record_count": len(cl.records), "cl_parse_error_count": sum(bool(r.parse_errors) for r in cl.records), "fatal": False}
    example.gcode_parse_summary_json = {"gcode_block_count": len(gc.blocks), "gcode_parse_error_count": sum(bool(b.parse_errors) for b in gc.blocks), "fatal": False}
    findings = ValidationEngine().validate(gc, validation_profile_from_snapshot(revision_snapshot(revision, machine)))
    values = [{**asdict(f), "severity": f.severity.value} for f in findings]
    example.validation_summary_json = {"blocking_count": sum(v["severity"] == "blocking" for v in values),
        "warning_count": sum(v["severity"] == "warning" for v in values),
        "informational_count": sum(v["severity"] == "informational" for v in values), "findings": values}


def _signals(cl: dict, gc: dict) -> list[str]:
    reasons = []
    cmd = cl["command"]
    if cmd == "LOADTL" and gc.get("tool") is not None: reasons.append("same_tool_number" if cl.get("tool") == gc.get("tool") else "tool_call")
    if cmd == "SPINDL" and (gc.get("rpm") is not None or set(gc.get("m_codes", [])) & {"M03", "M04", "M05"}): reasons += ["same_spindle_speed"] if cl.get("rpm") == gc.get("rpm") else ["spindle_event"]
    if cmd == "FEDRAT" and gc.get("feed") is not None: reasons.append("same_feed" if cl.get("feed") == gc.get("feed") else "feed_event")
    if cmd == "COOLNT" and set(gc.get("m_codes", [])) & {"M07", "M08", "M09"}: reasons.append("coolant_event")
    if cmd == "RAPID" and "G00" in gc.get("g_codes", []): reasons.append("rapid_motion")
    if cmd in {"GOTO", "FROM"} and gc.get("coordinates"): reasons.append("coordinate_motion")
    if cmd == "FINI" and set(gc.get("m_codes", [])) & {"M02", "M30"}: reasons.append("program_end")
    return reasons


def generate_alignment(db: Session, example: TranslationExample) -> TranslationAlignment:
    for old in list(example.alignments): db.delete(old)
    db.flush()
    alignment = TranslationAlignment(translation_example_id=example.id, status="proposed", algorithm_version=ALGORITHM_VERSION)
    db.add(alignment); db.flush()
    cl_rows, gc_rows = example.parsed_cl_records_json, example.parsed_gcode_blocks_json
    used_cl: set[int] = set(); used_gc: set[int] = set(); cursor = 0
    for position, cl in enumerate(cl_rows):
        if int(cl["index"]) in used_cl:
            continue
        best = None
        for gc in gc_rows[cursor:]:
            reasons = _signals(cl, gc)
            if reasons: best = (gc, reasons); break
        if not best: continue
        gc, reasons = best; ci, gi = int(cl["index"]), int(gc["index"])
        # RAPID followed by GOTO commonly collapses into one G00 block. Capture
        # the pair when RAPID is visited so advancing the G-code cursor does not
        # leave the following GOTO unmatched.
        following = cl_rows[position + 1] if position + 1 < len(cl_rows) else None
        if cl["command"] == "RAPID" and following and following["command"] == "GOTO" and "G00" in gc.get("g_codes", []):
            start, ci, link_type = ci, int(following["index"]), "many_to_one"
            used_cl.update({start, ci}); reasons.append("adjacent_sequence")
        else: start, link_type = ci, "one_to_one"
        link = TranslationAlignmentLink(alignment_id=alignment.id, cl_record_start=start, cl_record_end=ci,
            gcode_block_start=gi, gcode_block_end=gi, link_type=link_type, confidence=.9 if reasons else .5,
            review_status="proposed", match_reasons_json=reasons + ["relative_sequence"])
        alignment.links.append(link); used_cl.add(ci); used_gc.add(gi); cursor = gi + 1
    for cl in cl_rows:
        if int(cl["index"]) not in used_cl:
            alignment.links.append(TranslationAlignmentLink(alignment_id=alignment.id, cl_record_start=int(cl["index"]), cl_record_end=int(cl["index"]),
                link_type="unmatched", confidence=0, review_status="proposed", match_reasons_json=["unmatched_cl"]))
    for gc in gc_rows:
        if int(gc["index"]) not in used_gc:
            alignment.links.append(TranslationAlignmentLink(alignment_id=alignment.id, gcode_block_start=int(gc["index"]), gcode_block_end=int(gc["index"]),
                link_type="unmatched", confidence=0, review_status="proposed", match_reasons_json=["unmatched_gcode_or_post_generated"]))
    db.flush(); refresh_alignment(alignment); return alignment


def refresh_alignment(alignment: TranslationAlignment) -> None:
    links = list(alignment.links)
    matched_cl = {i for l in links if l.review_status != "rejected" and l.cl_record_start is not None and l.gcode_block_start is not None for i in range(l.cl_record_start, (l.cl_record_end or l.cl_record_start)+1)}
    total_cl = len(alignment.example.parsed_cl_records_json)
    alignment.summary_json = {"link_count": len(links), "confirmed": sum(l.review_status in {"confirmed", "edited"} for l in links),
        "proposed": sum(l.review_status == "proposed" for l in links), "rejected": sum(l.review_status == "rejected" for l in links),
        "unmatched_cl": sum(l.cl_record_start is not None and l.gcode_block_start is None for l in links),
        "unmatched_gcode": sum(l.cl_record_start is None and l.gcode_block_start is not None for l in links),
        "coverage_percent": round(len(matched_cl)/max(1,total_cl)*100,1)}
    alignment.status = "reviewed" if links and all(l.review_status != "proposed" for l in links) else "proposed"


def normalize_cl_pattern(text: str) -> str:
    value = text.upper().strip()
    if value.startswith("SPINDL/"): return re.sub(r"RPM\s*,?\s*[+-]?\d+(?:\.\d+)?", "RPM,{rpm}", value)
    if value.startswith("LOADTL/"): return re.sub(r"LOADTL\s*/\s*\d+", "LOADTL / {tool}", value)
    if value.startswith("FEDRAT/"): return re.sub(r"([+-]?\d+(?:\.\d+)?)", "{feed}", value, count=1)
    return re.sub(r"[+-]?\d+(?:\.\d+)?", "{value}", value)


def normalize_gcode_pattern(text: str, command: str | None) -> str:
    value = text.upper().strip()
    if command == "SPINDL": value = re.sub(r"S\s*\d+(?:\.\d+)?", "S{rpm}", value)
    elif command == "LOADTL": value = re.sub(r"T\s*\d+", "T{tool}", value)
    elif command == "FEDRAT": value = re.sub(r"F\s*\d+(?:\.\d+)?", "F{feed}", value)
    else: value = re.sub(r"([XYZIJKR])\s*[+-]?\d+(?:\.\d+)?", r"\1{value}", value)
    return value

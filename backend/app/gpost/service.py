from dataclasses import asdict, dataclass, field
from hashlib import sha256
import re
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.analysis_projects import revision_snapshot, validation_profile_from_snapshot
from app.cl_parser.models import ParsedCLRecord
from app.cl_parser.parser import CLParser
from app.models.entities import AuditEvent, DocumentChunk, MachineProfile, SourceDocument, utc_now
from app.models.gpost import GPostDraft, GPostDraftVersion, GPostMapping, GPostPreviewRun
from app.models.profile_extraction import MachineProfileRevision
from app.models.program_standards import OrganizationalStandardProfile, ReferenceProgram
from app.parsers.gcode import GCodeParser
from app.validators.engine import ValidationEngine

SAFETY_NOTICE = "R&D ONLY · NON-PRODUCTION · NOT VALIDATED FOR MACHINE USE"
REQUIRED_COMMANDS = {"LOADTL", "SPINDL", "FEDRAT", "COOLNT", "GOTO", "FINI"}
RECOGNIZED_UNSUPPORTED = {"CIRCLE", "ARC", "CYCLE", "CUTCOM", "MULTAX", "TLAXIS", "GOHOME", "OPSTOP"}


@dataclass(slots=True)
class GPostState:
    units: str | None = None
    active_plane: str | None = None
    distance_mode: str | None = "absolute"
    feed_mode: str | None = None
    current_position: dict[str, float] = field(default_factory=dict)
    selected_tool: int | None = None
    active_tool: int | None = None
    work_offset: str | None = None
    spindle_state: str = "off"
    spindle_direction: str | None = None
    spindle_speed: float | None = None
    coolant_state: str = "off"
    cutter_compensation: str | None = None
    tool_length_compensation: str | None = None
    canned_cycle_state: str | None = None
    machine_coordinate_override: bool = False
    multiaxis_state: bool = False
    rapid_mode: bool = False

    def snapshot(self) -> dict:
        return asdict(self)


def family_compatible(machine_type: str, family: str) -> bool:
    is_lathe = machine_type in {"lathe", "turning_center", "vertical_lathe"}
    if family == "fanuc_lathe":
        return is_lathe
    if family in {"fanuc_mill", "haas_mill"}:
        return not is_lathe and machine_type != "mill-turn"
    return True


def default_templates(revision: MachineProfileRevision, family: str) -> dict[str, str]:
    lathe = family == "fanuc_lathe"
    units = "G21" if revision.units == "mm" else "G20"
    templates = {
        "program_header": "%\n(O{program_number} R&D PREVIEW)",
        "safe_start": revision.safe_start_template or f"{units} {'G18' if lathe else 'G17'} G40 G80 G90",
        "units": units,
        "plane_selection": "G18" if lathe else "G17",
        "distance_mode": "G90",
        "feed_mode": "G99" if lathe else "G94",
        "work_offset": (revision.supported_work_offsets_json or ["G54"])[0],
        "tool_selection": "T{tool:04d}" if lathe else "T{tool}",
        "tool_change": revision.tool_change_template or ("T{tool:04d}" if lathe else "T{tool} M06"),
        "spindle_start_cw": "S{rpm:g} M03",
        "spindle_start_ccw": "S{rpm:g} M04",
        "spindle_stop": "M05",
        "coolant_on": "M08",
        "coolant_off": "M09",
        "rapid_move": "G00 {coordinates}",
        "linear_feed_move": "G01 {coordinates}{feed}",
        "arc_cw": "G02 {coordinates}",
        "arc_ccw": "G03 {coordinates}",
        "canned_cycle": "",
        "cycle_cancel": "G80",
        "reference_return": "G28",
        "program_end": revision.program_end_template or "M05\nM09\nM30",
        "footer": "%",
    }
    return templates


def capability_snapshot(revision: MachineProfileRevision) -> dict:
    axes = [axis for axis in ("X", "Y", "Z", "A", "B", "C") if getattr(revision, f"{axis.lower()}_min", None) is not None or axis in "XYZ"[: revision.axis_count or 0]]
    return {
        "configured_axes": axes,
        "axis_count": revision.axis_count,
        "spindle_limits": {"min": revision.min_spindle_rpm, "max": revision.max_spindle_rpm},
        "feed_limit": revision.max_feed_rate,
        "work_offsets": revision.supported_work_offsets_json or [],
        "supported_g_codes": revision.approved_g_codes_json or [],
        "supported_m_codes": revision.approved_m_codes_json or [],
        "restricted_commands": revision.restricted_commands_json or [],
        "unknown_capabilities": [key for key, value in {
            "max_spindle_rpm": revision.max_spindle_rpm,
            "max_feed_rate": revision.max_feed_rate,
            "controller_version": revision.controller_version,
        }.items() if value is None],
    }


def initial_mappings(draft: GPostDraft) -> list[GPostMapping]:
    t = draft.templates_json
    supported = {
        "LOADTL": ("stateful", t["tool_change"]),
        "SPINDL": ("conditional", t["spindle_start_cw"]),
        "FEDRAT": ("stateful", "F{feed:g}"),
        "COOLNT": ("conditional", t["coolant_on"]),
        "RAPID": ("stateful", None),
        "GOTO": ("conditional", t["linear_feed_move"]),
        "FROM": ("stateful", None),
        "FINI": ("template", t["program_end"]),
        "PPRINT": ("direct", "({text})"),
    }
    rows = [GPostMapping(
        gpost_draft_id=draft.id, mapping_key=command.lower(), cl_command=command,
        mapping_type=kind, output_template=template, supported=True,
        confidence=0.6, source_type="machine_profile_template",
        machine_type_scope=draft.machine_type, dialect_scope=draft.controller_family,
        review_status="pending",
    ) for command, (kind, template) in supported.items()]
    for command in sorted(RECOGNIZED_UNSUPPORTED):
        rows.append(GPostMapping(
            gpost_draft_id=draft.id, mapping_key=command.lower(), cl_command=command,
            mapping_type="unsupported", output_template=None, supported=False,
            confidence=None, source_type="capability_registry",
            machine_type_scope=draft.machine_type, dialect_scope=draft.controller_family,
            review_status="deferred",
            review_note="Recognized but unsupported or partially modeled in this R&D draft.",
        ))
    return rows


def validate_ownership(db: Session, machine_id: int, revision_id: int, document_ids: list[int], standard_id: int | None, reference_ids: list[int]):
    revision = db.get(MachineProfileRevision, revision_id)
    if revision is None or revision.machine_profile_id != machine_id:
        raise ValueError("Profile revision does not belong to the selected machine")
    if revision.status not in {"draft", "under_review", "approved", "active"}:
        raise ValueError("Profile revision is not available for R&D draft generation")
    documents = list(db.scalars(select(SourceDocument).where(SourceDocument.id.in_(document_ids)))) if document_ids else []
    if len(documents) != len(set(document_ids)) or any(item.machine_profile_id != machine_id for item in documents):
        raise ValueError("Every selected document must belong to the selected machine")
    standard = db.get(OrganizationalStandardProfile, standard_id) if standard_id else None
    if standard_id and (standard is None or standard.machine_profile_id != machine_id):
        raise ValueError("Standard profile does not belong to the selected machine")
    programs = list(db.scalars(select(ReferenceProgram).where(ReferenceProgram.id.in_(reference_ids)))) if reference_ids else []
    if len(programs) != len(set(reference_ids)) or any(item.machine_profile_id != machine_id for item in programs):
        raise ValueError("Every reference program must belong to the selected machine")
    return revision


def snapshot_draft(draft: GPostDraft, mappings: list[GPostMapping]) -> dict:
    return {
        "draft": {
            "name": draft.name, "version": draft.version, "status": draft.status,
            "controller_family": draft.controller_family, "machine_type": draft.machine_type,
            "selected_document_ids": draft.selected_document_ids_json,
            "standard_profile_id": draft.standard_profile_id,
            "reference_program_ids": draft.reference_program_ids_json,
            "templates": draft.templates_json, "warnings": draft.warnings_json,
        },
        "mappings": [{
            "mapping_key": m.mapping_key, "cl_command": m.cl_command,
            "mapping_type": m.mapping_type, "output_template": m.output_template,
            "conditions": m.conditions_json, "supported": m.supported,
            "review_status": m.review_status, "source_document_id": m.source_document_id,
        } for m in mappings],
    }


def audit(db: Session, event_type: str, draft: GPostDraft, **metadata):
    db.add(AuditEvent(event_type=event_type, machine_profile_id=draft.machine_profile_id,
                      metadata_json={"gpost_draft_id": draft.id, **metadata}))


def _format(template: str, values: dict) -> str:
    try:
        return template.format(**values).strip()
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Template could not be rendered: {exc}") from exc


def _coords(record: ParsedCLRecord, machine_type: str) -> str:
    allowed = {"X", "Z"} if machine_type in {"lathe", "turning_center", "vertical_lathe"} else {"X", "Y", "Z"}
    return " ".join(f"{axis}{value:g}" for axis, value in record.coordinates.items() if axis in allowed)


def generate_preview(db: Session, draft: GPostDraft, cl_source: str) -> GPostPreviewRun:
    mappings = {m.cl_command: m for m in db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == draft.id))}
    parsed_cl = CLParser().parse(cl_source)
    state = GPostState(active_plane="G18" if draft.controller_family == "fanuc_lathe" else "G17")
    output: list[str] = ["(R&D ONLY - NON-PRODUCTION - NOT VALIDATED FOR MACHINE USE)"]
    output.extend(line for line in draft.templates_json.get("safe_start", "").splitlines() if line.strip())
    if draft.templates_json.get("work_offset"):
        output.append(draft.templates_json["work_offset"])
    trace: list[dict] = []
    unsupported: list[dict] = []
    missing: list[dict] = []
    warnings: list[dict] = []

    if not family_compatible(draft.machine_type, draft.controller_family):
        warnings.append({"category": "Blocking Configuration Issue", "message": "Machine type and controller template family conflict."})
    for mapping in mappings.values():
        if mapping.supported and mapping.dialect_scope and mapping.dialect_scope != draft.controller_family:
            warnings.append({"category": "Controller Compatibility", "mapping_id": mapping.id,
                             "message": f"{mapping.cl_command} is scoped to {mapping.dialect_scope}, not {draft.controller_family}."})
        if mapping.supported and mapping.machine_type_scope and mapping.machine_type_scope != draft.machine_type:
            warnings.append({"category": "Machine Compatibility", "mapping_id": mapping.id,
                             "message": f"{mapping.cl_command} is scoped to {mapping.machine_type_scope}, not {draft.machine_type}."})

    for record in parsed_cl.records:
        command = record.original_command or record.command
        if command in {"COMMENT", "PARTNO", "MACHIN", "UNITS", "CUTTER", "SEQNO"}:
            continue
        mapping = mappings.get(command)
        if mapping is None:
            item = {"line": record.line_number, "command": command, "reason": "No mapping exists"}
            (missing if command in REQUIRED_COMMANDS else unsupported).append(item)
            continue
        if not mapping.supported or mapping.mapping_type == "unsupported":
            unsupported.append({"line": record.line_number, "command": command, "mapping_id": mapping.id,
                                "reason": mapping.review_note or "Recognized but unsupported"})
            continue
        before = state.snapshot()
        generated: list[str] = []
        values = {
            "tool": record.tool_number or 0, "rpm": record.spindle_speed or 0,
            "feed": record.feed_rate or 0, "coordinates": _coords(record, draft.machine_type),
            "text": " ".join(record.parameters),
        }
        try:
            if command == "LOADTL":
                state.selected_tool = record.tool_number
                state.active_tool = record.tool_number
                if mapping.output_template: generated = [_format(mapping.output_template, values)]
            elif command == "SPINDL":
                direction = next((v for v in record.parameters if v in {"CLW", "CCLW", "OFF"}), "CLW")
                state.spindle_speed = record.spindle_speed
                state.spindle_direction = direction
                state.spindle_state = "off" if direction == "OFF" else "on"
                template = draft.templates_json["spindle_stop"] if direction == "OFF" else draft.templates_json["spindle_start_ccw"] if direction == "CCLW" else mapping.output_template
                if template: generated = [_format(template, values)]
            elif command == "FEDRAT":
                state.feed_mode = next((v for v in record.parameters if v in {"IPM", "MMPM", "IPR"}), state.feed_mode)
                if mapping.output_template: generated = [_format(mapping.output_template, values)]
            elif command == "COOLNT":
                requested = (record.parameters[0] if record.parameters else "ON").upper()
                state.coolant_state = "off" if requested == "OFF" else requested.lower()
                template = draft.templates_json["coolant_off"] if requested == "OFF" else mapping.output_template
                if template: generated = [_format(template, values)]
            elif command == "RAPID":
                state.rapid_mode = True
            elif command in {"GOTO", "FROM"}:
                state.current_position.update({k: v for k, v in record.coordinates.items() if k in {"X", "Y", "Z"}})
                if command == "GOTO":
                    template = draft.templates_json["rapid_move"] if state.rapid_mode else mapping.output_template
                    if template: generated = [_format(template, values)]
                    state.rapid_mode = False
            elif command == "FINI":
                if mapping.output_template: generated = mapping.output_template.splitlines()
            elif mapping.output_template:
                generated = [_format(mapping.output_template, values)]
        except ValueError as exc:
            warnings.append({"category": "Blocking Configuration Issue", "line": record.line_number, "message": str(exc)})
        for line in [line for line in generated if line]:
            output.append(line)
            trace.append({
                "generated_block_index": len(output) - 1, "source_cl_line": record.line_number,
                "source_cl_text": record.original_text, "cl_command": command,
                "mapping_id": mapping.id, "mapping_version": draft.version,
                "template_used": mapping.output_template, "state_before": before,
                "state_after": state.snapshot(), "generated_gcode": line,
                "source_evidence": {"document_id": mapping.source_document_id,
                    "chunk_id": mapping.source_chunk_id, "page": mapping.source_page,
                    "section": mapping.source_section, "excerpt": mapping.source_excerpt},
                "warnings": [],
            })

    multiaxis = [item for item in unsupported if item["command"] in {"MULTAX", "TLAXIS"}]
    blocking = bool(warnings or missing or multiaxis)
    gcode = "\n".join(output)
    parsed_gcode = GCodeParser(set(draft.machine_profile_snapshot_json.get("supported_work_offsets_json") or [])).parse(gcode)
    validation_profile = validation_profile_from_snapshot(draft.machine_profile_snapshot_json)
    findings = ValidationEngine().validate(parsed_gcode, validation_profile)
    parser_diagnostics = list(parsed_gcode.errors)
    serialized_findings = [{**asdict(item), "severity": item.severity.value} for item in findings]
    traceable_record_count = len([
        record for record in parsed_cl.records
        if (record.original_command or record.command) not in {
            "COMMENT", "PARTNO", "MACHIN", "UNITS", "CUTTER", "SEQNO", "RAPID", "FROM",
        }
    ])
    blocking_findings = sum(item.severity.value == "blocking" for item in findings)
    blocking = blocking or bool(parser_diagnostics) or blocking_findings > 0
    status = "blocked" if blocking else "generated"
    run = GPostPreviewRun(
        gpost_draft_id=draft.id, status=status, cl_file_hash=sha256(cl_source.encode()).hexdigest(),
        generated_gcode=gcode, parser_diagnostics_json=parser_diagnostics,
        deterministic_findings_json=serialized_findings, unsupported_commands_json=unsupported,
        missing_mappings_json=missing, warnings_json=warnings, traceability_json=trace,
        summary_json={
            "cl_record_count": len(parsed_cl.records), "generated_block_count": len(trace),
            "traceability_coverage": round(len(trace) / max(1, traceable_record_count) * 100, 1),
            "parser_error_count": len(parser_diagnostics), "deterministic_finding_count": len(findings),
            "blocking_finding_count": blocking_findings,
            "can_validate_for_rnd": not blocking,
            "safety_notice": SAFETY_NOTICE,
        },
    )
    db.add(run)
    audit(db, "gpost_preview_blocked" if blocking else "gpost_preview_generated", draft,
          status=status, cl_file_hash=run.cl_file_hash, generated_block_count=len(trace))
    db.commit(); db.refresh(run)
    return run


def compare_drafts(db: Session, left: GPostDraft, right: GPostDraft) -> dict:
    def by_key(draft_id):
        return {m.mapping_key: m for m in db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == draft_id))}
    a, b = by_key(left.id), by_key(right.id)
    shared = a.keys() & b.keys()
    return {
        "left_draft_id": left.id, "right_draft_id": right.id,
        "mappings_added": sorted(b.keys() - a.keys()), "mappings_removed": sorted(a.keys() - b.keys()),
        "templates_changed": sorted(k for k in shared if a[k].output_template != b[k].output_template),
        "conditions_changed": sorted(k for k in shared if a[k].conditions_json != b[k].conditions_json),
        "evidence_changed": sorted(k for k in shared if (a[k].source_document_id, a[k].source_chunk_id) != (b[k].source_document_id, b[k].source_chunk_id)),
        "warnings_added": [w for w in right.warnings_json if w not in left.warnings_json],
        "warnings_resolved": [w for w in left.warnings_json if w not in right.warnings_json],
    }


def markdown_export(draft: GPostDraft, mappings: list[GPostMapping]) -> str:
    lines = [f"# {draft.name} v{draft.version}", "", f"> **{SAFETY_NOTICE}**", "",
             f"- Machine profile: {draft.machine_profile_id}", f"- Profile revision: {draft.machine_profile_revision_id}",
             f"- Controller family: {draft.controller_family}", f"- Machine type: {draft.machine_type}",
             f"- R&D status: {draft.status}", "", "## Mappings", "",
             "| CL command | Type | Output template | Review | Source |", "| --- | --- | --- | --- | --- |"]
    for m in mappings:
        lines.append(f"| {m.cl_command} | {m.mapping_type} | {(m.output_template or '—').replace(chr(10), '<br>')} | {m.review_status} | {m.source_type} |")
    lines += ["", "## Unsupported features", "", *(f"- {item}" for item in draft.unsupported_features_json),
              "", "## Warnings", "", *(f"- {item}" for item in draft.warnings_json), "", SAFETY_NOTICE]
    return "\n".join(lines)

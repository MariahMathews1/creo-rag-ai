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
REQUIRED_COMMANDS = {"LOADTL", "SPINDL", "FEDRAT", "COOLNT", "RAPID", "GOTO", "FINI"}
RECOGNIZED_UNSUPPORTED = {"CIRCLE", "ARC", "CYCLE", "CUTCOM", "MULTAX", "TLAXIS", "GOHOME", "OPSTOP"}

MAPPING_DEFINITIONS = (
    ("loadtl", "LOADTL", "Tool selection / load", "Tooling", "tool_change", {}, True),
    ("spindl_cw", "SPINDL", "Clockwise spindle start", "Spindle", "spindle_start_cw", {"direction": "CLW"}, True),
    ("spindl_ccw", "SPINDL", "Counter-clockwise spindle start", "Spindle", "spindle_start_ccw", {"direction": "CCLW"}, True),
    ("spindl_off", "SPINDL", "Spindle stop", "Spindle", "spindle_stop", {"direction": "OFF"}, True),
    ("fedrat", "FEDRAT", "Feed rate command", "Motion", "feed_rate", {}, True),
    ("coolnt_on", "COOLNT", "Coolant on", "Coolant", "coolant_on", {"mode": "ON"}, True),
    ("coolnt_off", "COOLNT", "Coolant off", "Coolant", "coolant_off", {"mode": "OFF"}, True),
    ("rapid", "RAPID", "Enable rapid positioning", "Motion", "rapid_move", {}, True),
    ("goto", "GOTO", "Positioning / cutting move", "Motion", "linear_feed_move", {}, True),
    ("from", "FROM", "Initial positioning context", "Coordinates", None, {}, False),
    ("fini", "FINI", "End of CL program", "Program Control", "program_end", {}, True),
    ("pprint", "PPRINT", "Program comment", "Program Control", "comment", {}, False),
)

TEMPLATE_LABELS = {
    "program_header": "Program Header", "safe_start": "Safe Start", "tool_selection": "Tool Selection",
    "tool_change": "Tool Change", "spindle_start_cw": "Clockwise Start",
    "spindle_start_ccw": "Counter-clockwise Start", "spindle_stop": "Spindle Stop",
    "feed_rate": "Feed Rate", "coolant_on": "Coolant On", "coolant_off": "Coolant Off",
    "rapid_move": "Rapid Move", "linear_feed_move": "Feed Move", "units": "Units",
    "plane_selection": "Plane Selection", "distance_mode": "Distance Mode", "feed_mode": "Feed Mode",
    "work_offset": "Work Offset", "reference_return": "Reference Return", "program_end": "Program End",
    "footer": "Footer", "comment": "Program Comment",
}


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


def is_lathe_machine(machine_type: str | None) -> bool:
    normalized = (machine_type or "").lower().replace("-", "_").replace(" ", "_")
    return "lathe" in normalized or normalized in {"turning_center", "turning", "vertical_turning_center"}


def family_compatible(machine_type: str, family: str) -> bool:
    is_lathe = is_lathe_machine(machine_type)
    if family == "fanuc_lathe":
        return is_lathe
    if family in {"fanuc_mill", "haas_mill"}:
        return not is_lathe and machine_type != "mill-turn"
    return True


def controller_family_compatible(revision: MachineProfileRevision, family: str) -> bool:
    controller = " ".join(filter(None, (
        revision.controller_manufacturer, revision.controller_name, revision.controller_model,
    ))).lower()
    if family.startswith("fanuc_"):
        return "fanuc" in controller
    if family == "haas_mill":
        return "haas" in controller
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
        "feed_rate": "F{feed:g}",
        "work_offset": (revision.supported_work_offsets_json or ["G54"])[0],
        "tool_selection": "T{tool:04d}" if lathe else "T{tool}",
        "tool_change": revision.tool_change_template or ("T{tool:04d}" if lathe else "T{tool} M06"),
        "spindle_start_cw": "S{rpm:g} M03",
        "spindle_start_ccw": "S{rpm:g} M04",
        "spindle_stop": "M05",
        "coolant_on": "M08",
        "coolant_off": "M09",
        "rapid_move": "G00 {coordinates}",
        "linear_feed_move": "G01 {coordinates} F{feed:g}",
        "arc_cw": "G02 {coordinates}",
        "arc_ccw": "G03 {coordinates}",
        "canned_cycle": "",
        "cycle_cancel": "G80",
        "reference_return": "G28",
        "program_end": revision.program_end_template or "M05\nM09\nM30",
        "footer": "%",
        "comment": "({text})",
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
    rows = [GPostMapping(
        gpost_draft_id=draft.id, mapping_key=key, cl_command=command,
        mapping_type="conditional" if conditions else "stateful", output_template=None,
        template_key=template_key, template_override=None, uses_override=False,
        support_status="supported", required_for_v1=required, description=description,
        conditions_json={**conditions, "category": category}, supported=True,
        confidence=0.6, source_type="machine_profile_template",
        machine_type_scope=draft.machine_type, dialect_scope=draft.controller_family,
        review_status="pending",
    ) for key, command, description, category, template_key, conditions, required in MAPPING_DEFINITIONS]
    low_axis_machine = int(draft.capability_snapshot_json.get("axis_count") or 0) <= 3
    for command in sorted(RECOGNIZED_UNSUPPORTED):
        not_applicable = low_axis_machine and command in {"MULTAX", "TLAXIS"}
        rows.append(GPostMapping(
            gpost_draft_id=draft.id, mapping_key=command.lower(), cl_command=command,
            mapping_type="unsupported", output_template=None, supported=False,
            template_key=None, uses_override=False,
            support_status="not_applicable" if not_applicable else "not_implemented",
            required_for_v1=False,
            description={
                "MULTAX": "Multiaxis mode", "TLAXIS": "Tool-axis orientation", "CIRCLE": "Circular geometry",
                "ARC": "Arc motion", "CYCLE": "Canned cycle", "CUTCOM": "Cutter compensation",
                "GOHOME": "Reference return", "OPSTOP": "Optional stop",
            }.get(command, "Advanced CL behavior"),
            confidence=None, source_type="capability_registry",
            machine_type_scope=draft.machine_type, dialect_scope=draft.controller_family,
            review_status="pending" if not_applicable else "deferred",
            review_note=("Selected machine has no multiaxis configuration." if not_applicable
                         else "Known command; generation support is not implemented in V1."),
        ))
    return rows


def effective_template(draft: GPostDraft, mapping: GPostMapping) -> str | None:
    if mapping.uses_override:
        return mapping.template_override
    if mapping.template_key:
        return draft.templates_json.get(mapping.template_key)
    return mapping.output_template


def review_summary(mappings: list[GPostMapping]) -> dict:
    required = [item for item in mappings if item.required_for_v1 and item.support_status != "not_applicable"]
    reviewed = [item for item in required if item.review_status in {"accepted", "accepted_with_edit"}]
    return {
        "required": len(required), "reviewed": len(reviewed), "needs_review": len(required) - len(reviewed),
        "not_applicable": sum(item.support_status == "not_applicable" for item in mappings),
        "not_implemented": sum(item.support_status == "not_implemented" for item in mappings),
        "blocking": sum(item.support_status == "unsupported_required" for item in mappings),
        "percent": round(len(reviewed) / max(1, len(required)) * 100),
        "total_known": len(mappings),
    }


def setup_issues(db: Session, draft: GPostDraft, mappings: list[GPostMapping]) -> list[dict]:
    issues: list[dict] = []
    revision = db.get(MachineProfileRevision, draft.machine_profile_revision_id)
    if revision is None:
        issues.append({"code": "GPOST_PROFILE_REVISION_MISSING", "message": "Selected immutable machine profile revision is unavailable."})
    else:
        if revision.status not in {"approved", "active"}:
            issues.append({"code": "GPOST_PROFILE_REVISION_NOT_APPROVED", "message": "The selected machine profile revision is not approved."})
        if draft.machine_type != revision.machine_type:
            issues.append({"code": "GPOST_MACHINE_TYPE_SNAPSHOT_MISMATCH", "message": f"Draft machine type {draft.machine_type} does not match profile revision machine type {revision.machine_type}."})
        if not controller_family_compatible(revision, draft.controller_family):
            issues.append({"code": "GPOST_CONTROLLER_FAMILY_MISMATCH", "message": "Controller identity and controller template family conflict."})
    if not family_compatible(draft.machine_type, draft.controller_family):
        issues.append({"code": "GPOST_TEMPLATE_FAMILY_MISMATCH", "message": "Machine type and controller template family conflict."})
    if not draft.templates_json or not draft.templates_json.get("safe_start"):
        issues.append({"code": "GPOST_BASE_TEMPLATE_MISSING", "message": "Base configuration template is not loaded."})
    return issues


def mapping_key_for_record(record: ParsedCLRecord) -> str:
    command = record.original_command or record.command
    if command == "SPINDL":
        direction = next((value for value in record.parameters if value in {"CLW", "CCLW", "OFF"}), "CLW")
        return {"CLW": "spindl_cw", "CCLW": "spindl_ccw", "OFF": "spindl_off"}[direction]
    if command == "COOLNT":
        mode = (record.parameters[0] if record.parameters else "ON").upper()
        return "coolnt_off" if mode == "OFF" else "coolnt_on"
    return command.lower()


def current_cl_preflight(db: Session, draft: GPostDraft, cl_source: str) -> dict:
    """Derive generation readiness only from behavior used by the submitted CL."""
    mapping_rows = list(db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == draft.id)))
    mappings = {mapping.mapping_key: mapping for mapping in mapping_rows}
    parsed = CLParser().parse(cl_source)
    ignored = {"COMMENT", "PARTNO", "MACHIN", "UNITS", "CUTTER", "SEQNO"}
    required_keys: list[str] = []
    for record in parsed.records:
        if (record.original_command or record.command) in ignored:
            continue
        key = mapping_key_for_record(record)
        if key not in required_keys:
            required_keys.append(key)
    required = [mappings[key] for key in required_keys if key in mappings]
    missing = [key for key in required_keys if key not in mappings]
    supported = [item.mapping_key for item in required if item.support_status == "supported" and (effective_template(draft, item) is not None or item.mapping_key in {"rapid", "from"})]
    reviewed = [item.mapping_key for item in required if item.mapping_key in supported and item.review_status in {"accepted", "accepted_with_edit"}]
    unsupported = [item.mapping_key for item in required if item.mapping_key not in supported]
    blockers = setup_issues(db, draft, mapping_rows)
    if parsed.error_count:
        blockers.append({"code": "GPOST_CL_PARSE_ERROR", "title": "CL Input Needs Review", "message": f"{parsed.error_count} CL record(s) contain parser diagnostics.", "action": "review_cl"})
    if missing or unsupported:
        labels = missing + unsupported
        blockers.append({"code": "GPOST_UNSUPPORTED_CURRENT_CL", "title": "Unsupported CL Behavior", "message": f"No usable post behavior is configured for: {', '.join(labels)}.", "behavior_keys": labels, "action": "configure_mapping"})
    for issue in blockers:
        issue.setdefault("title", "Post Configuration Needs Attention")
        issue.setdefault("action", "change_template" if "MISMATCH" in issue["code"] else "open_configuration")
    unreviewed = [key for key in supported if key not in reviewed]
    warnings = []
    if unreviewed:
        warnings.append({"code": "GPOST_UNREVIEWED_CURRENT_CL", "message": f"{len(unreviewed)} supported behavior(s) have not been manually reviewed.", "behavior_keys": unreviewed})
    if not draft.selected_document_ids_json:
        warnings.append({"code": "GPOST_NO_DOCUMENT_EVIDENCE", "message": "No machine document is selected as supporting evidence."})
    return {
        "machine_ready": not any(item["code"].startswith("GPOST_PROFILE") or item["code"].startswith("GPOST_MACHINE") for item in blockers),
        "post_context_ready": not any("MISMATCH" in item["code"] or item["code"] == "GPOST_BASE_TEMPLATE_MISSING" for item in blockers),
        "cl_parse_status": "parsed" if not parsed.error_count else "needs_review",
        "cl_record_count": len(parsed.records),
        "required_behavior_keys": required_keys,
        "supported_behavior_keys": supported,
        "reviewed_behavior_keys": reviewed,
        "unreviewed_behavior_keys": unreviewed,
        "unsupported_required_behaviors": missing + unsupported,
        "blocking_issues": blockers,
        "warnings": warnings,
        "generation_allowed": not blockers,
        "generation_allowed_with_warning": not blockers and bool(warnings),
    }


def validate_ownership(db: Session, machine_id: int, revision_id: int, document_ids: list[int], standard_id: int | None, reference_ids: list[int]):
    revision = db.get(MachineProfileRevision, revision_id)
    if revision is None or revision.machine_profile_id != machine_id:
        raise ValueError("Profile revision does not belong to the selected machine")
    if revision.status not in {"approved", "active"}:
        raise ValueError("An approved machine profile revision is required for G-POST V1")
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
            "manual_configuration_acknowledged": draft.manual_configuration_acknowledged,
            "templates": draft.templates_json, "warnings": draft.warnings_json,
        },
        "mappings": [{
            "mapping_key": m.mapping_key, "cl_command": m.cl_command,
            "mapping_type": m.mapping_type, "template_key": m.template_key,
            "template_override": m.template_override, "uses_override": m.uses_override,
            "effective_output_template": effective_template(draft, m),
            "conditions": m.conditions_json, "support_status": m.support_status,
            "required_for_v1": m.required_for_v1,
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


def _machine_coordinates(record: ParsedCLRecord, machine_type: str) -> dict[str, float]:
    coordinates = dict(record.coordinates)
    if is_lathe_machine(machine_type):
        # The generic CL parser assigns positional two-axis records as X/Y.
        # For a lathe, the second positional coordinate is Z when no explicit
        # third coordinate was supplied.
        if "Z" not in coordinates and "Y" in coordinates:
            coordinates["Z"] = coordinates["Y"]
        return {axis: value for axis, value in coordinates.items() if axis in {"X", "Z"}}
    return {axis: value for axis, value in coordinates.items() if axis in {"X", "Y", "Z"}}


def _coords(record: ParsedCLRecord, machine_type: str) -> str:
    return " ".join(f"{axis}{value:g}" for axis, value in _machine_coordinates(record, machine_type).items())


def generate_preview(db: Session, draft: GPostDraft, cl_source: str) -> GPostPreviewRun:
    mapping_rows = list(db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == draft.id)))
    mappings = {m.mapping_key: m for m in mapping_rows}
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

    blockers = setup_issues(db, draft, mapping_rows)
    warnings.extend({"category": "Blocking Setup Issue", **item} for item in blockers)
    for mapping in mapping_rows:
        if mapping.support_status == "supported" and mapping.dialect_scope and mapping.dialect_scope != draft.controller_family:
            warnings.append({"category": "Controller Compatibility", "mapping_id": mapping.id,
                             "message": f"{mapping.cl_command} is scoped to {mapping.dialect_scope}, not {draft.controller_family}."})
        if mapping.support_status == "supported" and mapping.machine_type_scope and mapping.machine_type_scope != draft.machine_type:
            warnings.append({"category": "Machine Compatibility", "mapping_id": mapping.id,
                             "message": f"{mapping.cl_command} is scoped to {mapping.machine_type_scope}, not {draft.machine_type}."})

    for record in parsed_cl.records:
        command = record.original_command or record.command
        if command in {"COMMENT", "PARTNO", "MACHIN", "UNITS", "CUTTER", "SEQNO"}:
            continue
        variant = mapping_key_for_record(record)
        mapping = mappings.get(variant)
        if mapping is None:
            item = {"line": record.line_number, "command": command, "reason": "No mapping exists"}
            (missing if command in REQUIRED_COMMANDS else unsupported).append(item)
            continue
        if mapping.support_status != "supported":
            unsupported.append({"line": record.line_number, "command": command, "mapping_id": mapping.id,
                                "support_status": mapping.support_status,
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
            template = effective_template(draft, mapping)
            if command == "LOADTL":
                state.selected_tool = record.tool_number
                state.active_tool = record.tool_number
                if template: generated = [_format(template, values)]
            elif command == "SPINDL":
                direction = next((v for v in record.parameters if v in {"CLW", "CCLW", "OFF"}), "CLW")
                state.spindle_speed = record.spindle_speed
                state.spindle_direction = direction
                state.spindle_state = "off" if direction == "OFF" else "on"
                if template: generated = [_format(template, values)]
            elif command == "FEDRAT":
                state.feed_mode = next((v for v in record.parameters if v in {"IPM", "MMPM", "IPR"}), state.feed_mode)
                if template: generated = [_format(template, values)]
            elif command == "COOLNT":
                requested = (record.parameters[0] if record.parameters else "ON").upper()
                state.coolant_state = "off" if requested == "OFF" else requested.lower()
                if template: generated = [_format(template, values)]
            elif command == "RAPID":
                state.rapid_mode = True
            elif command in {"GOTO", "FROM"}:
                state.current_position.update(_machine_coordinates(record, draft.machine_type))
                if command == "GOTO":
                    move_mapping = mappings.get("rapid") if state.rapid_mode else mapping
                    move_template = effective_template(draft, move_mapping) if move_mapping else template
                    if move_template: generated = [_format(move_template, values)]
                    state.rapid_mode = False
            elif command == "FINI":
                if template: generated = template.splitlines()
            elif template:
                generated = [_format(template, values)]
        except ValueError as exc:
            warnings.append({"category": "Blocking Configuration Issue", "line": record.line_number, "message": str(exc)})
        for line in [line for line in generated if line]:
            output.append(line)
            trace.append({
                "generated_block_index": len(output) - 1, "source_cl_line": record.line_number,
                "source_cl_text": record.original_text, "cl_command": command,
                "mapping_id": mapping.id, "mapping_version": draft.version,
                "template_key": mapping.template_key, "uses_override": mapping.uses_override,
                "template_used": effective_template(draft, mapping), "state_before": before,
                "state_after": state.snapshot(), "generated_gcode": line,
                "source_evidence": {"document_id": mapping.source_document_id,
                    "chunk_id": mapping.source_chunk_id, "page": mapping.source_page,
                    "section": mapping.source_section, "excerpt": mapping.source_excerpt},
                "warnings": [],
            })

    multiaxis = [item for item in unsupported if item["command"] in {"MULTAX", "TLAXIS"}]
    unsupported_required = [item for item in unsupported if item.get("support_status") == "unsupported_required"]
    actual_not_implemented = [item for item in unsupported if item.get("support_status") == "not_implemented"]
    blocking = bool(blockers or missing or multiaxis or unsupported_required or actual_not_implemented)
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
    if blockers:
        blocking_cause = "Template Conflict" if any(item["code"] == "GPOST_TEMPLATE_FAMILY_MISMATCH" for item in blockers) else "Setup Issue"
    elif unsupported_required or actual_not_implemented or multiaxis:
        blocking_cause = "Unsupported Required Mapping"
    elif parser_diagnostics:
        blocking_cause = "Parser Error"
    elif blocking_findings:
        blocking_cause = "Machine Limit"
    elif missing:
        blocking_cause = "Missing Mapping"
    else:
        blocking_cause = None
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
            "blocking_cause": blocking_cause,
            "setup_issues": blockers,
            "review_progress": review_summary(mapping_rows),
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
        "templates_changed": sorted(
            set(k for k in left.templates_json.keys() | right.templates_json.keys()
                if left.templates_json.get(k) != right.templates_json.get(k))
            | set(k for k in shared if (
                a[k].template_key, a[k].template_override, a[k].uses_override, a[k].output_template
            ) != (
                b[k].template_key, b[k].template_override, b[k].uses_override, b[k].output_template
            ))
        ),
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
             "| CL command | Template source | Effective template | Support | Review |", "| --- | --- | --- | --- | --- | --- |"]
    for m in mappings:
        template = effective_template(draft, m)
        source = "Mapping override" if m.uses_override else f"Configuration: {m.template_key or 'none'}"
        lines.append(f"| {m.cl_command} | {source} | {(template or '—').replace(chr(10), '<br>')} | {m.support_status} | {m.review_status} |")
    lines += ["", "## Unsupported features", "", *(f"- {item}" for item in draft.unsupported_features_json),
              "", "## Warnings", "", *(f"- {item}" for item in draft.warnings_json), "", SAFETY_NOTICE]
    return "\n".join(lines)

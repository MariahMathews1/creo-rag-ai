from dataclasses import dataclass, field

from app.models.traceability import CLRecord, GCodeBlock


@dataclass(slots=True)
class ManufacturingEvent:
    source_type: str
    source_record_id: int
    event_type: str
    order_index: int
    coordinates: dict[str, float] = field(default_factory=dict)
    tool_number: int | None = None
    spindle_speed: float | None = None
    feed_rate: float | None = None
    coolant_state: str | None = None
    motion_type: str | None = None
    text_labels: list[str] = field(default_factory=list)


def cl_event(record: CLRecord) -> ManufacturingEvent:
    event_type = {
        "LOADTL": "tool", "SPINDL": "spindle", "FEDRAT": "feed",
        "COOLNT": "coolant", "RAPID": "rapid_state", "GOTO": "motion",
        "FROM": "reference", "CIRCLE": "arc", "ARC": "arc",
        "CYCLE": "cycle", "OPSTOP": "stop", "FINI": "completion",
        "PPRINT": "comment",
    }.get(record.command, "state" if record.command != "UNKNOWN" else "unsupported")
    return ManufacturingEvent(
        "cl", record.id, event_type, record.record_index,
        record.coordinates_json or {}, record.tool_number, record.spindle_speed,
        record.feed_rate, record.coolant_state, record.motion_type,
        [record.operation_name] if record.operation_name else [],
    )


def gcode_event(block: GCodeBlock) -> ManufacturingEvent:
    gs, ms = set(block.g_codes_json or []), set(block.m_codes_json or [])
    if block.tool_number is not None or "M06" in ms:
        event_type = "tool"
    elif ms & {"M03", "M04", "M05"} or block.spindle_speed is not None:
        event_type = "spindle"
    elif ms & {"M07", "M08", "M09"}:
        event_type = "coolant"
    elif gs & {f"G{i}" for i in range(73, 90)}:
        event_type = "cycle"
    elif gs & {"G02", "G03"}:
        event_type = "arc"
    elif block.coordinates_json:
        event_type = "motion"
    elif ms & {"M00", "M01"}:
        event_type = "stop"
    elif ms & {"M02", "M30"}:
        event_type = "completion"
    elif "(" in block.original_text or ";" in block.original_text:
        event_type = "comment"
    else:
        event_type = "state"
    coolant = "flood" if "M08" in ms else "mist" if "M07" in ms else "off" if "M09" in ms else None
    return ManufacturingEvent(
        "gcode", block.id, event_type, block.block_index,
        block.coordinates_json or {}, block.tool_number or block.active_tool,
        block.spindle_speed, block.feed_rate, coolant, block.motion_mode, [],
    )

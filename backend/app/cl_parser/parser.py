from dataclasses import dataclass, field
import re

from app.cl_parser.models import CLState, ParsedCLRecord

SUPPORTED = {
    "PARTNO", "MACHIN", "UNITS", "MULTAX", "LOADTL", "CUTTER", "SPINDL",
    "FEDRAT", "COOLNT", "RAPID", "GOTO", "FROM", "CIRCLE", "ARC", "TLAXIS",
    "GOHOME", "PPRINT", "INSERT", "SEQNO", "OPSTOP", "REWIND", "FINI",
    "CYCLE", "INTOL", "OUTTOL", "TOLER", "CUTCOM", "DELAY", "MODE",
    "CLAMP", "ROTABL", "INDEX", "TRANS", "ORIGIN", "MSYS", "CSYS",
}
NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")


@dataclass(slots=True)
class CLParseResult:
    records: list[ParsedCLRecord] = field(default_factory=list)
    units: str | None = None

    @property
    def error_count(self) -> int:
        return sum(bool(record.parse_errors) for record in self.records)


class CLParser:
    version = "cl-parser-v1"

    def parse(self, source: str) -> CLParseResult:
        result = CLParseResult()
        state = CLState()
        for line_number, original in enumerate(source.splitlines(), 1):
            stripped = original.strip()
            if not stripped:
                continue
            try:
                record = self._parse_line(len(result.records), line_number, original, state)
            except Exception as exc:
                record = ParsedCLRecord(
                    len(result.records), line_number, original, stripped.upper(),
                    "UNKNOWN", parse_errors=[f"Unable to parse record: {exc}"],
                    state_before=state.snapshot(), state_after=state.snapshot(),
                )
            result.records.append(record)
        result.units = state.units
        return result

    def _parse_line(
        self, index: int, line_number: int, original: str, state: CLState
    ) -> ParsedCLRecord:
        normalized = re.sub(r"\s+", " ", original.strip()).upper()
        before = state.snapshot()
        if normalized.startswith("$$") or normalized.startswith("/*"):
            return ParsedCLRecord(
                index, line_number, original, normalized, "COMMENT",
                comments=[original.strip()], state_before=before, state_after=before,
            )
        left, separator, right = normalized.partition("/")
        original_command = left.strip().split()[0] if left.strip() else None
        command = original_command or "UNKNOWN"
        if command == "CYCLE" and right.strip() == "OFF":
            command = "CYCLE"
        known = command in SUPPORTED
        rendered = command if known else "UNKNOWN"
        raw_parameters = right if separator else " ".join(left.strip().split()[1:])
        parameters = [value.strip() for value in raw_parameters.split(",") if value.strip()]
        numeric: list[float] = []
        errors: list[str] = []
        for value in parameters:
            token = value.split("=", 1)[-1].strip()
            if NUMBER.match(token):
                numeric.append(float(token))
            elif re.search(r"\d", token) and token not in {
                "RPM", "CLW", "CCLW", "ON", "OFF", "FLOOD", "MIST",
                "INCH", "INCHES", "MM", "MMPM", "IPM",
            }:
                errors.append(f"Unsupported numeric parameter: {value}")
        record = ParsedCLRecord(
            index, line_number, original, normalized, rendered,
            original_command=original_command, parameters=parameters,
            numeric_parameters=numeric, parse_errors=errors, state_before=before,
        )
        self._apply(record, state)
        record.state_after = state.snapshot()
        return record

    def _apply(self, record: ParsedCLRecord, state: CLState) -> None:
        command, values, numbers = record.command, record.parameters, record.numeric_parameters
        if command == "UNITS" and values:
            state.units = "mm" if values[0] in {"MM", "MILLIMETERS"} else "inch"
        elif command == "MULTAX":
            state.multi_axis_mode = not values or values[0] not in {"OFF", "0"}
        elif command == "LOADTL" and numbers:
            record.tool_number = state.current_tool = int(numbers[0])
        elif command == "CUTTER":
            state.cutter_geometry = numbers
        elif command == "FEDRAT" and numbers:
            record.feed_rate = state.feed_rate = numbers[-1]
            state.feed_mode = next((v for v in values if v in {"IPM", "MMPM", "IPR"}), None)
        elif command == "SPINDL":
            record.spindle_speed = next((n for n in numbers if n >= 0), None)
            state.spindle_speed = record.spindle_speed
            state.spindle_direction = next((v for v in values if v in {"CLW", "CCLW", "OFF"}), None)
        elif command == "COOLNT":
            state.coolant_state = record.coolant_state = values[0].lower() if values else "on"
        elif command == "RAPID":
            state.rapid_mode = True
            record.motion_type = "rapid_state"
        elif command in {"GOTO", "FROM"}:
            axes = ["X", "Y", "Z", "I", "J", "K"]
            record.coordinates = dict(zip(axes, numbers[:6]))
            state.current_position = {
                key: value for key, value in record.coordinates.items() if key in {"X", "Y", "Z"}
            }
            if len(numbers) >= 6:
                state.tool_axis = {key: record.coordinates[key] for key in ("I", "J", "K")}
            record.motion_type = (
                "reference" if command == "FROM" else "rapid" if state.rapid_mode else "feed"
            )
            if command == "GOTO":
                state.rapid_mode = False
        elif command == "TLAXIS" and len(numbers) >= 3:
            state.tool_axis = record.coordinates = dict(zip(("I", "J", "K"), numbers[:3]))
        elif command in {"CIRCLE", "ARC"}:
            axes = ["X", "Y", "Z", "I", "J", "K", "R"]
            record.coordinates = dict(zip(axes, numbers[:7]))
            record.motion_type = "arc"
            if len(numbers) < 4:
                record.parse_errors.append("Arc geometry is incomplete; equivalence requires review.")
        elif command == "CUTCOM" and values:
            state.cutter_compensation = values[0]
        elif command in {"CSYS", "MSYS", "ORIGIN", "TRANS"}:
            state.coordinate_system = record.normalized_text
        elif command == "SEQNO" and numbers:
            state.sequence_number = int(numbers[0])
        elif command == "PPRINT":
            text = " ".join(values).strip()
            record.operation_name = text
            if "OPERATION" in text:
                state.active_operation = text.split(":", 1)[-1].strip()
        record.operation_name = record.operation_name or state.active_operation
        record.tool_number = record.tool_number or state.current_tool
        record.feed_rate = record.feed_rate if record.feed_rate is not None else state.feed_rate
        record.spindle_speed = (
            record.spindle_speed if record.spindle_speed is not None else state.spindle_speed
        )
        record.coolant_state = record.coolant_state or state.coolant_state

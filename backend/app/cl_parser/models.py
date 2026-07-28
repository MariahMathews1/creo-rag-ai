from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class CLState:
    units: str | None = None
    current_position: dict[str, float] = field(default_factory=dict)
    tool_axis: dict[str, float] = field(default_factory=dict)
    current_tool: int | None = None
    cutter_geometry: list[float] = field(default_factory=list)
    feed_rate: float | None = None
    feed_mode: str | None = None
    spindle_speed: float | None = None
    spindle_direction: str | None = None
    coolant_state: str | None = None
    rapid_mode: bool = False
    cutter_compensation: str | None = None
    active_operation: str | None = None
    multi_axis_mode: bool | None = None
    coordinate_system: str | None = None
    sequence_number: int | None = None

    def snapshot(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ParsedCLRecord:
    record_index: int
    line_number: int
    original_text: str
    normalized_text: str
    command: str
    original_command: str | None = None
    parameters: list[str] = field(default_factory=list)
    numeric_parameters: list[float] = field(default_factory=list)
    named_parameters: dict[str, str | float] = field(default_factory=dict)
    coordinates: dict[str, float] = field(default_factory=dict)
    motion_type: str | None = None
    tool_number: int | None = None
    spindle_speed: float | None = None
    feed_rate: float | None = None
    coolant_state: str | None = None
    operation_name: str | None = None
    comments: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
    state_before: dict = field(default_factory=dict)
    state_after: dict = field(default_factory=dict)

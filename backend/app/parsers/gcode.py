"""Conservative, controller-configurable parsing for common Fanuc-style G-code."""

from dataclasses import dataclass, field, replace
import re

WORD_PATTERN = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
PAREN_COMMENT_PATTERN = re.compile(r"\([^)]*\)")


def normalize_code(letter: str, value: str) -> str:
    """Normalize G/M commands to two digits while retaining decimal subcodes."""

    letter = letter.upper()
    numeric = float(value)
    if not numeric.is_integer():
        return f"{letter}{numeric:g}"
    integer = int(numeric)
    rendered = f"{integer:02d}" if 0 <= integer < 10 else str(integer)
    return f"{letter}{rendered}"


@dataclass(slots=True)
class ModalState:
    """Basic tracked controller state; this is not a machine simulation."""

    motion_mode: str | None = None
    distance_mode: str | None = None
    plane: str | None = None
    units: str | None = None
    work_offset: str | None = None
    cutter_compensation: str | None = None
    tool_length_compensation: str | None = None
    feed_mode: str | None = None
    feed_rate: float | None = None
    spindle_speed: float | None = None
    selected_tool: int | None = None
    active_tool: int | None = None
    coolant_state: str = "off"
    spindle_state: str = "off"

    @property
    def motion(self) -> str | None:
        """Compatibility name retained for existing consumers."""

        return self.motion_mode


@dataclass(slots=True)
class ParsedGCodeBlock:
    line_number: int
    original_text: str
    cleaned_text: str
    sequence_number: int | None = None
    g_codes: list[str] = field(default_factory=list)
    m_codes: list[str] = field(default_factory=list)
    coordinates: dict[str, float] = field(default_factory=dict)
    arc_offsets: dict[str, float] = field(default_factory=dict)
    arc_radius: float | None = None
    feed_rate: float | None = None
    spindle_speed: float | None = None
    tool_number: int | None = None
    comments: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
    program_number: int | None = None
    work_offset: str | None = None
    modal_state: ModalState = field(default_factory=ModalState)
    state_before: ModalState = field(default_factory=ModalState)

    @property
    def source(self) -> str:
        return self.original_text

    @property
    def errors(self) -> list[str]:
        return self.parse_errors

    @property
    def is_rapid(self) -> bool:
        return "G00" in self.g_codes or self.modal_state.motion_mode == "G00"

    @property
    def is_cutting_feed(self) -> bool:
        return bool(self.coordinates) and self.modal_state.motion_mode in {"G01", "G02", "G03"}


# Backwards-compatible public name for early imports.
ParsedBlock = ParsedGCodeBlock


@dataclass(slots=True)
class ParseResult:
    blocks: list[ParsedGCodeBlock] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class GCodeParser:
    """Parse common word-address syntax without allowing one bad line to abort."""

    DEFAULT_WORK_OFFSETS = {"G54", "G55", "G56", "G57", "G58", "G59", "G54.1"}

    def __init__(self, work_offset_codes: set[str] | None = None):
        configured = work_offset_codes or self.DEFAULT_WORK_OFFSETS
        self.work_offset_codes = {
            self._normalize_command_text(code) for code in configured
        }

    @staticmethod
    def _normalize_command_text(code: str) -> str:
        match = re.fullmatch(r"\s*([GM])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*", code, re.I)
        if not match:
            return code.strip().upper()
        return normalize_code(*match.groups())

    def parse(self, program: str) -> ParseResult:
        result = ParseResult()
        modal = ModalState()
        for line_number, original_text in enumerate(program.splitlines(), start=1):
            if not original_text.strip():
                continue
            try:
                block = self._parse_line(line_number, original_text, modal)
            except Exception as exc:  # malformed input must not stop the full review
                message = f"Unable to parse line: {exc}"
                block = ParsedGCodeBlock(
                    line_number=line_number,
                    original_text=original_text,
                    cleaned_text=original_text.strip(),
                    parse_errors=[message],
                    modal_state=replace(modal),
                )
            result.blocks.append(block)
            result.errors.extend(
                f"Line {line_number}: {message}" for message in block.parse_errors
            )
        return result

    def _parse_line(
        self, line_number: int, original_text: str, modal: ModalState
    ) -> ParsedGCodeBlock:
        comments = [match.group(0) for match in PAREN_COMMENT_PATTERN.finditer(original_text)]
        without_parentheses = PAREN_COMMENT_PATTERN.sub(" ", original_text)
        code_portion = without_parentheses
        if ";" in code_portion:
            code_portion, semicolon_comment = code_portion.split(";", 1)
            comments.append(f";{semicolon_comment}")
        cleaned_text = code_portion.strip()
        upper = cleaned_text.upper()
        block = ParsedGCodeBlock(
            line_number=line_number,
            original_text=original_text,
            cleaned_text=cleaned_text,
            comments=comments,
            modal_state=replace(modal), state_before=replace(modal),
        )

        if not upper or upper == "%":
            return block

        consumed_spans: list[tuple[int, int]] = []
        for match in WORD_PATTERN.finditer(upper):
            consumed_spans.append(match.span())
            letter, raw_value = match.groups()
            letter = letter.upper()
            try:
                value = float(raw_value)
                if letter == "G":
                    block.g_codes.append(normalize_code(letter, raw_value))
                elif letter == "M":
                    block.m_codes.append(normalize_code(letter, raw_value))
                elif letter in {"X", "Y", "Z", "A", "B", "C", "U", "V", "W"}:
                    block.coordinates[letter] = value
                elif letter in {"I", "J", "K"}:
                    block.arc_offsets[letter] = value
                elif letter == "R":
                    block.arc_radius = value
                elif letter == "S":
                    block.spindle_speed = value
                elif letter == "F":
                    block.feed_rate = value
                elif letter == "T":
                    block.tool_number = int(value)
                elif letter == "N":
                    block.sequence_number = int(value)
                elif letter == "O":
                    block.program_number = int(value)
            except (OverflowError, ValueError):
                block.parse_errors.append(f"Invalid {letter} word: {raw_value}")

        residue = list(upper)
        for start, end in consumed_spans:
            residue[start:end] = " " * (end - start)
        unexpected = re.sub(r"[\s/%]+", " ", "".join(residue)).strip()
        if unexpected:
            block.parse_errors.append(f"Unrecognized or malformed text: {unexpected}")

        self._update_modal(modal, block)
        block.modal_state = replace(modal)
        block.work_offset = modal.work_offset
        return block

    def _update_modal(self, modal: ModalState, block: ParsedGCodeBlock) -> None:
        for code in block.g_codes:
            if code in {"G00", "G01", "G02", "G03"}:
                modal.motion_mode = code
            elif code in {"G17", "G18", "G19"}:
                modal.plane = code
            elif code in {"G20", "G21"}:
                modal.units = code
            elif code in {"G90", "G91"}:
                modal.distance_mode = code
            elif code in {"G93", "G94", "G95"}:
                modal.feed_mode = code
            elif code in self.work_offset_codes:
                modal.work_offset = code
            elif code in {"G40", "G41", "G42"}:
                modal.cutter_compensation = code
            elif code in {"G43", "G44", "G49"}:
                modal.tool_length_compensation = code

        if block.feed_rate is not None:
            modal.feed_rate = block.feed_rate
        if block.spindle_speed is not None:
            modal.spindle_speed = block.spindle_speed
        if block.tool_number is not None:
            modal.selected_tool = block.tool_number

        for code in block.m_codes:
            if code in {"M03", "M04"}:
                modal.spindle_state = "clockwise" if code == "M03" else "counterclockwise"
            elif code == "M05":
                modal.spindle_state = "off"
            elif code in {"M07", "M08"}:
                modal.coolant_state = "mist" if code == "M07" else "flood"
            elif code == "M09":
                modal.coolant_state = "off"
            elif code == "M06" and modal.selected_tool is not None:
                modal.active_tool = modal.selected_tool

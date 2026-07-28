from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.entities import MachineType
from app.parsers.gcode import normalize_code


def _normalize_commands(values: list[str]) -> list[str]:
    """Normalize command lists once at the API boundary and remove duplicates."""

    normalized: list[str] = []
    for raw in values:
        command = raw.strip().upper()
        if not command:
            continue
        if command[0] in {"G", "M"}:
            try:
                command = normalize_code(command[0], command[1:])
            except ValueError:
                pass
        if command not in normalized:
            normalized.append(command)
    return normalized


class MachineProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    manufacturer: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    controller_name: str = Field(min_length=1, max_length=120)
    controller_manufacturer: str | None = Field(default=None, max_length=120)
    controller_model: str | None = Field(default=None, max_length=120)
    controller_version: str | None = None
    machine_type: MachineType = MachineType.MILL
    axis_count: int = Field(default=3, gt=0, le=12)
    x_min: float | None = None
    x_max: float | None = None
    y_min: float | None = None
    y_max: float | None = None
    z_min: float | None = None
    z_max: float | None = None
    max_spindle_rpm: float | None = Field(default=None, gt=0)
    max_feed_rate: float | None = Field(default=None, gt=0)
    rapid_z_review_threshold: float | None = None
    supported_work_offsets: list[str] = Field(default_factory=list)
    approved_g_codes: list[str] = Field(default_factory=list)
    approved_m_codes: list[str] = Field(default_factory=list)
    restricted_commands: list[str] = Field(default_factory=list)
    safe_start_template: str | None = None
    tool_change_template: str | None = None
    program_end_template: str | None = None
    notes: str | None = None

    @field_validator(
        "supported_work_offsets",
        "approved_g_codes",
        "approved_m_codes",
        "restricted_commands",
        mode="before",
    )
    @classmethod
    def normalize_command_lists(cls, value):
        if value is None:
            return []
        return _normalize_commands(list(value))

    @model_validator(mode="after")
    def validate_ranges(self):
        for axis in ("x", "y", "z"):
            lower = getattr(self, f"{axis}_min")
            upper = getattr(self, f"{axis}_max")
            if lower is not None and upper is not None and lower >= upper:
                raise ValueError(f"{axis.upper()} minimum must be less than maximum")
        return self


class MachineProfileCreate(MachineProfileBase):
    pass


class MachineProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    manufacturer: str | None = Field(default=None, min_length=1, max_length=120)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    controller_name: str | None = Field(default=None, min_length=1, max_length=120)
    controller_manufacturer: str | None = Field(default=None, max_length=120)
    controller_model: str | None = Field(default=None, max_length=120)
    controller_version: str | None = None
    machine_type: MachineType | None = None
    axis_count: int | None = Field(default=None, gt=0, le=12)
    x_min: float | None = None
    x_max: float | None = None
    y_min: float | None = None
    y_max: float | None = None
    z_min: float | None = None
    z_max: float | None = None
    max_spindle_rpm: float | None = Field(default=None, gt=0)
    max_feed_rate: float | None = Field(default=None, gt=0)
    rapid_z_review_threshold: float | None = None
    supported_work_offsets: list[str] | None = None
    approved_g_codes: list[str] | None = None
    approved_m_codes: list[str] | None = None
    restricted_commands: list[str] | None = None
    safe_start_template: str | None = None
    tool_change_template: str | None = None
    program_end_template: str | None = None
    notes: str | None = None

    @field_validator(
        "supported_work_offsets",
        "approved_g_codes",
        "approved_m_codes",
        "restricted_commands",
        mode="before",
    )
    @classmethod
    def normalize_optional_command_lists(cls, value):
        if value is None:
            return value
        return _normalize_commands(list(value))


class MachineProfileRead(MachineProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    active_revision_id: int | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

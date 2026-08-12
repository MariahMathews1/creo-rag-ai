from typing import Literal

from pydantic import BaseModel, Field


class ToolpathPoint(BaseModel):
    x: float | None = None; y: float | None = None; z: float | None = None
    a: float | None = None; b: float | None = None; c: float | None = None
    u: float | None = None; v: float | None = None; w: float | None = None


class ToolpathSegment(BaseModel):
    id: str; source_type: Literal["cl", "gcode"]
    source_record_id: int | None = None; source_line_start: int; source_line_end: int
    operation_id: str | None = None; tool_number: int | None = None
    motion_type: Literal["rapid", "linear", "arc_cw", "arc_ccw", "cycle", "tool_change", "non_motion", "unsupported"]
    start_point: ToolpathPoint | None = None; end_point: ToolpathPoint | None = None
    center_point: ToolpathPoint | None = None; radius: float | None = None
    path_points: list[ToolpathPoint] = Field(default_factory=list)
    plane: str | None = None; feed_rate: float | None = None; spindle_speed: float | None = None
    rapid: bool = False; arc_direction: str | None = None; helical: bool = False
    tool_axis: ToolpathPoint | None = None; alignment_link_id: int | None = None
    aligned_segment_ids: list[str] = Field(default_factory=list)
    finding_ids: list[int] = Field(default_factory=list); sequence_index: int
    visualizable: bool = True; unmatched: bool = False; geometry_status: str | None = None
    metadata_json: dict = Field(default_factory=dict)


class ToolpathBounds(BaseModel):
    min_x: float | None = None; max_x: float | None = None
    min_y: float | None = None; max_y: float | None = None
    min_z: float | None = None; max_z: float | None = None


class ToolpathResponse(BaseModel):
    source: str; machine_type: str; default_view: str; coordinate_context: str
    segments: list[ToolpathSegment]; bounds: ToolpathBounds; summary: dict
    warnings: list[dict]; comparison_summary: dict = Field(default_factory=dict)
    advisory_only: Literal[True] = True
    safety_notice: str = "TOOLPATH VISUALIZATION ONLY — Parsed programmed motion; no stock removal, fixture/tool geometry, collision detection, machine dynamics, or final-part prediction."

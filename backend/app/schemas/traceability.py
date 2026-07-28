from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

SAFETY_NOTICE = (
    "CL-to-G-code alignment is an analytical aid only. It does not certify "
    "post-processor correctness, machining safety, or production readiness. "
    "Review and simulation by a qualified CNC programmer remain required."
)


class AdvisoryModel(BaseModel):
    advisory_only: bool = True
    alignment_is_inferred: bool = True
    manual_review_required: bool = True
    safety_notice: str = SAFETY_NOTICE


class SourcePairRead(BaseModel):
    analysis_id: int
    cl_source: str | None
    gcode_source: str | None
    cl_original_filename: str | None
    gcode_original_filename: str | None
    cl_file_hash: str | None
    gcode_file_hash: str | None
    cl_processing_status: str
    gcode_processing_status: str
    alignment_status: str


class ParseSummary(AdvisoryModel):
    record_count: int
    parsed_count: int
    unsupported_count: int
    error_count: int
    units: str | None
    tool_count: int
    motion_record_count: int
    duration_ms: float


class CLRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    analysis_project_id: int
    record_index: int
    line_number: int
    original_text: str
    normalized_text: str
    command: str
    original_command: str | None
    parameters_json: list
    coordinates_json: dict
    motion_type: str | None
    tool_number: int | None
    spindle_speed: float | None
    feed_rate: float | None
    coolant_state: str | None
    operation_name: str | None
    parse_errors_json: list


class GCodeBlockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    analysis_project_id: int
    block_index: int
    line_number: int
    original_text: str
    cleaned_text: str
    g_codes_json: list
    m_codes_json: list
    coordinates_json: dict
    motion_mode: str | None
    tool_number: int | None
    active_tool: int | None
    feed_rate: float | None
    spindle_speed: float | None
    parse_errors_json: list


class AlignmentRunRead(AdvisoryModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    analysis_project_id: int
    version: int
    status: str
    algorithm_version: str
    settings_json: dict
    summary_json: dict
    metrics_json: dict
    source_integrity_json: dict
    stale: bool
    started_at: datetime
    completed_at: datetime | None


class AlignmentLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    alignment_run_id: int
    cl_record_id: int | None
    gcode_block_id: int | None
    link_type: str
    confidence: float
    match_reasons_json: list
    mismatch_reasons_json: list
    score_components_json: dict
    status: str
    review_note: str | None
    review_label: str | None
    assigned_by: str | None
    reviewed_at: datetime | None


class LinkUpdate(BaseModel):
    cl_record_id: int | None = None
    gcode_block_id: int | None = None
    link_type: str = Field(default="manual")
    status: str = Field(default="modified", pattern="^(proposed|confirmed|rejected|modified)$")
    review_note: str | None = Field(default=None, max_length=2000)
    review_label: str | None = Field(default=None, max_length=50)

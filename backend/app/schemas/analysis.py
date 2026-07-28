from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.entities import ProjectStatus, Severity

SAFETY_NOTICE = (
    "This analysis does not certify the CNC program for production. "
    "Review, simulation, and approval by a qualified CNC programmer are required."
)


class AnalysisProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    machine_profile_id: int
    cl_source: str | None = None
    gcode_source: str | None = None


class SourceTextUpdate(BaseModel):
    text: str


class AnalysisProjectRead(AnalysisProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    cl_original_filename: str | None = None
    gcode_original_filename: str | None = None
    cl_file_hash: str | None = None
    gcode_file_hash: str | None = None
    cl_processing_status: str = "not_provided"
    gcode_processing_status: str = "not_provided"
    alignment_status: str = "not_started"
    alignment_version: int = 0
    alignment_summary_json: dict = Field(default_factory=dict)
    last_analyzed_at: datetime | None = None
    machine_profile_revision_id: int | None = None
    machine_profile_snapshot_json: dict = Field(default_factory=dict)
    advisory_only: bool = True
    safety_notice: str = SAFETY_NOTICE

    @field_validator("alignment_summary_json", "machine_profile_snapshot_json", mode="before")
    @classmethod
    def normalize_legacy_json_objects(cls, value):
        """Keep legacy rows with nullable JSON columns readable by the API."""
        return value or {}


class AnalysisFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_project_id: int
    severity: Severity
    category: str
    title: str
    description: str
    line_number: int | None
    source_line: str | None
    rule_id: str
    recommendation: str
    confidence: float
    created_at: datetime


class AnalysisRunResponse(BaseModel):
    project: AnalysisProjectRead
    findings: list[AnalysisFindingRead]
    advisory_only: bool = True
    safety_notice: str = SAFETY_NOTICE


class AIExplanationRequest(BaseModel):
    content_type: str = Field(pattern="^(gcode|cl|findings)$")
    text: str | None = None


class AIExplanationResponse(BaseModel):
    advisory: bool = True
    provider: str = "mock"
    explanation: str

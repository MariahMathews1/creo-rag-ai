from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MachineFactWrite(BaseModel):
    category: str = Field(min_length=1, max_length=60)
    fact_key: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=180)
    value_json: Any | None = None
    unit: str | None = None
    status: str = "needs_review"
    post_review_status: str = "available_from_machine"
    source_document_id: int | None = None
    source_label: str | None = None
    source_location: str | None = None
    reviewer: str | None = None
    review_note: str | None = None


class MachineFactRead(MachineFactWrite, ORMRead):
    id: int
    post_record_id: int
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    used_by: list[dict] = Field(default_factory=list)


class OFGSettingWrite(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    subsection: str | None = None
    setting_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    value_json: Any | None = None
    unit: str | None = None
    status: str = "unmapped"
    source_machine_fact_ids_json: list[int] = Field(default_factory=list)
    source_document_evidence_ids_json: list[int] = Field(default_factory=list)
    site_standard_ids_json: list[int] = Field(default_factory=list)
    requires_custom_logic: bool = False
    custom_logic_id: int | None = None
    ofg_menu_path: str | None = None
    ofg_menu_path_status: str = "not_verified"
    relevance_class: str = "core"
    relevance_label: str = "required_for_post"
    is_applicable: bool = True
    user_selected: bool = False
    source_type: str = "Unknown"
    source_reference: str | None = None
    structured_value_json: Any | None = None
    code_status: str | None = None
    reviewer: str | None = None
    review_note: str | None = None


class OFGSettingRead(OFGSettingWrite, ORMRead):
    id: int
    post_record_id: int
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    source_machine_facts: list[dict] = Field(default_factory=list)


class SiteStandardWrite(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    scope: str
    applicable_machine_types_json: list[str] = Field(default_factory=list)
    applicable_controller_families_json: list[str] = Field(default_factory=list)
    applicable_machine_ids_json: list[int] = Field(default_factory=list)
    category: str
    rule: str = Field(min_length=1)
    validation_requirements_json: list[str] = Field(default_factory=list)
    source: str | None = None
    status: str = "needs_review"
    reviewer: str | None = None
    version: int = 1
    effective_date: datetime | None = None
    notes: str | None = None


class SiteStandardRead(SiteStandardWrite, ORMRead):
    id: int
    created_at: datetime
    updated_at: datetime


class StandardApplicationWrite(BaseModel):
    site_standard_id: int
    status: str = "applied"
    conflict_status: str = "none"
    conflict_note: str | None = None
    reviewer: str | None = None
    review_note: str | None = None


class StandardApplicationRead(StandardApplicationWrite, ORMRead):
    id: int
    post_record_id: int
    created_at: datetime
    updated_at: datetime
    standard: SiteStandardRead


class CustomLogicWrite(BaseModel):
    related_ofg_setting_id: int | None = None
    name: str = Field(min_length=1, max_length=180)
    category: str
    reason: str = Field(min_length=1)
    desired_behavior: str | None = None
    runtime_trigger: str | None = None
    implementation_type: str = "FIL / CIMFIL"
    status: str = "identified"
    evidence_ids_json: list[int] = Field(default_factory=list)
    site_standard_ids_json: list[int] = Field(default_factory=list)
    source_format: str = "Site verification required"
    source_reference: str | None = None
    reviewer: str | None = None
    review_note: str | None = None


class CustomLogicRead(CustomLogicWrite, ORMRead):
    id: int
    post_record_id: int
    created_at: datetime
    updated_at: datetime


class OpenQuestionWrite(BaseModel):
    question_type: str
    title: str = Field(min_length=1, max_length=220)
    description: str | None = None
    severity: str = "warning"
    related_type: str | None = None
    related_id: int | None = None
    source_context: str | None = None
    owner: str | None = None
    status: str = "open"
    resolution: str | None = None


class OpenQuestionRead(OpenQuestionWrite, ORMRead):
    id: int
    post_record_id: int
    created_at: datetime
    updated_at: datetime


class ValidationRecordWrite(BaseModel):
    post_version_id: int | None = None
    validation_type: str
    name: str | None = None
    performed_by: str = Field(min_length=1, max_length=100)
    performed_at: datetime | None = None
    environment: str | None = None
    result: str
    notes: str | None = None
    attachment_reference: str | None = None
    external_tool: str | None = None
    external_reference: str | None = None
    test_program_name: str | None = None
    findings_count: int = Field(default=0, ge=0)
    blocking_findings_count: int = Field(default=0, ge=0)
    references_json: list[str] = Field(default_factory=list)
    ai_used: bool = False

    @field_validator("validation_type")
    @classmethod
    def supported_type(cls, value: str) -> str:
        allowed = {"Configuration Review", "OFG Entry Review", "FIL Static Review", "G-POST Compilation",
                   "Controlled Test Post", "Local NC Review", "VERICUT Simulation", "NC Programmer Review",
                   "Dry Run", "Site Qualification"}
        aliases = {"Controlled Test CL Run": "Controlled Test Post", "Simulation": "VERICUT Simulation"}
        value = aliases.get(value, value)
        if value not in allowed: raise ValueError("Unsupported validation type")
        return value

    @field_validator("result")
    @classmethod
    def supported_result(cls, value: str) -> str:
        normalized = value.upper().replace(" ", "_")
        aliases = {"PASSED": "PASS", "PASSED_WITH_FINDINGS": "PASS_WITH_FINDINGS", "FAILED": "FAIL", "INCOMPLETE": "NEEDS_REVIEW"}
        normalized = aliases.get(normalized, normalized)
        if normalized not in {"NOT_STARTED", "PASS", "PASS_WITH_FINDINGS", "FAIL", "NEEDS_REVIEW", "BLOCKED", "NOT_APPLICABLE"}:
            raise ValueError("Unsupported validation result")
        return normalized


class ValidationRecordRead(ValidationRecordWrite, ORMRead):
    id: int
    post_record_id: int
    performed_at: datetime
    created_at: datetime


class ValidationFindingWrite(BaseModel):
    severity: str = "WARNING"
    category: str = "Engineering"
    title: str = Field(min_length=1, max_length=220)
    description: str | None = None
    related_ofg_setting_id: int | None = None
    related_custom_logic_id: int | None = None
    related_site_standard_id: int | None = None
    status: str = "Open"
    resolution_note: str | None = None

    @field_validator("severity")
    @classmethod
    def finding_severity(cls, value: str) -> str:
        value = value.upper()
        if value not in {"INFO", "WARNING", "ERROR", "FATAL", "UNKNOWN"}: raise ValueError("Unsupported finding severity")
        return value

    @field_validator("status")
    @classmethod
    def finding_status(cls, value: str) -> str:
        aliases = {"open": "Open", "investigating": "Investigating", "resolved": "Resolved",
                   "accepted_for_r&d": "Accepted for R&D", "deferred": "Deferred"}
        value = aliases.get(value.lower().replace(" ", "_"), value)
        if value not in {"Open", "Investigating", "Resolved", "Accepted for R&D", "Deferred"}: raise ValueError("Unsupported finding status")
        return value


class ValidationFindingRead(ValidationFindingWrite, ORMRead):
    id: int
    validation_record_id: int
    created_at: datetime
    updated_at: datetime


class ValidationPolicyWrite(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    required_validation_types_json: list[str] = Field(default_factory=lambda: ["Configuration Review", "G-POST Compilation", "NC Programmer Review"])
    optional_validation_types_json: list[str] = Field(default_factory=lambda: ["Controlled Test Post", "VERICUT Simulation", "Dry Run"])
    source: str | None = None
    reviewer: str | None = None


class ValidationPolicyRead(ValidationPolicyWrite, ORMRead):
    id: int
    post_record_id: int
    updated_at: datetime


class DiagnosticParseRequest(BaseModel):
    listing_text: str = Field(min_length=1, max_length=2_000_000)
    file_name: str | None = Field(default=None, max_length=240)
    create_findings: bool = True


class DiagnosticRead(ORMRead):
    id: int
    validation_record_id: int
    severity: str
    code: str | None
    message: str
    line_reference: int | None
    source_reference: str | None
    custom_logic_reference_id: int | None
    raw_excerpt: str
    created_at: datetime


class PostRecordSummary(BaseModel):
    post_record_id: int
    status: str
    machine_knowledge: dict
    ofg_configuration: dict
    site_standards: dict
    custom_logic: dict
    open_questions: dict
    validation: dict
    blockers: list[dict]
    next_action: dict
    native_gpost_integration: dict

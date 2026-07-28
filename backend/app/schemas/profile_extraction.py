from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

SAFETY_NOTICE = (
    "Extracted machine-profile values are proposals based on uploaded documents. "
    "They must be reviewed against the exact machine configuration, controller "
    "version, options, controlled documentation, and organizational standards before use."
)


class AdvisoryExtraction(BaseModel):
    advisory_only: bool = True
    machine_profile_is_draft: bool = True
    qualified_review_required: bool = True
    safety_notice: str = SAFETY_NOTICE


class ExtractionStart(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=20)
    target_machine_type: str
    selected_machine_variant: str | None = None
    field_categories: list[str] = Field(default_factory=list)


class ExtractionRunRead(AdvisoryExtraction):
    model_config = ConfigDict(from_attributes=True)
    id: int
    machine_profile_id: int
    target_revision_id: int | None
    status: str
    provider_name: str
    model_name: str | None
    extraction_schema_version: str
    selected_document_ids_json: list
    settings_json: dict
    summary_json: dict
    detected_variants_json: list
    selected_machine_variant: str | None
    started_at: datetime
    completed_at: datetime | None
    failure_message: str | None


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: int
    document_title: str
    document_type: str
    document_chunk_id: int
    citation_number: int
    page_start: int | None
    page_end: int | None
    section_title: str | None
    excerpt: str
    raw_value_text: str | None
    normalized_value_json: object | None
    unit: str | None
    relevance_score: float
    evidence_type: str


class ProposalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    extraction_run_id: int
    field_key: str
    field_label: str
    field_category: str
    proposed_value_json: object | None
    normalized_value_json: object | None
    unit: str | None
    confidence: float
    confidence_components_json: dict
    proposal_status: str
    review_status: str
    reviewed_value_json: object | None
    review_note: str | None
    reviewed_by: str | None
    requires_exact_machine_verification: bool
    safety_relevant: bool
    interpretation_note: str | None
    variant_applicability_json: list
    evidence: list[EvidenceRead] = Field(default_factory=list)


class ProposalReview(BaseModel):
    review_status: str = Field(pattern="^(accepted|accepted_with_edit|rejected|deferred|manually_entered|not_applicable)$")
    reviewed_value: object | None = None
    unit: str | None = None
    review_note: str | None = Field(default=None, max_length=2000)


class ApplyDraftRequest(BaseModel):
    base_strategy: str = Field(pattern="^(active|blank|selected_revision)$")
    source_revision_id: int | None = None
    review_summary: str | None = None


class RevisionRead(AdvisoryExtraction):
    model_config = ConfigDict(from_attributes=True)
    id: int
    machine_profile_id: int
    revision_number: int
    status: str
    source_type: str
    created_from_revision_id: int | None
    name: str
    manufacturer: str | None
    model: str | None
    controller_name: str | None
    controller_manufacturer: str | None
    controller_model: str | None
    controller_version: str | None
    machine_type: str | None
    axis_count: int | None
    x_min: float | None
    x_max: float | None
    y_min: float | None
    y_max: float | None
    z_min: float | None
    z_max: float | None
    min_spindle_rpm: float | None
    max_spindle_rpm: float | None
    max_feed_rate: float | None
    rapid_traverse_rate: float | None
    units: str | None
    supported_work_offsets_json: list
    approved_g_codes_json: list
    approved_m_codes_json: list
    restricted_commands_json: list
    safe_start_template: str | None
    tool_change_template: str | None
    program_end_template: str | None
    machine_configuration_json: dict
    capabilities_json: dict
    notes: str | None
    review_summary: str | None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None


class ApprovalRequest(BaseModel):
    exact_machine_applicability_confirmed: bool
    safety_notice_acknowledged: bool
    review_note: str = Field(min_length=3, max_length=2000)


class RejectionRequest(BaseModel):
    review_note: str = Field(min_length=3, max_length=2000)

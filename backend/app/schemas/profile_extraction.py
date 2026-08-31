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


class ManualInformationWrite(BaseModel):
    fact_key: str = Field(min_length=1, max_length=100)
    value: object
    unit: str | None = Field(default=None, max_length=30)
    source_basis: str = Field(min_length=1, max_length=40)
    document_id: int | None = None
    source_detail: str | None = Field(default=None, max_length=300)
    notes: str | None = Field(default=None, max_length=2000)
    review_status: str = Field(pattern="^(confirmed|needs_review)$")
    proposal_id: int | None = None


class ManualInformationRead(BaseModel):
    id: int
    machine_profile_id: int
    revision_id: int
    fact_key: str
    label: str
    category: str
    value: object
    unit: str | None
    source_basis: str
    source_label: str
    source_detail: str | None
    notes: str | None
    review_status: str
    proposal_id: int | None


class ManualInformationFieldRead(BaseModel):
    fact_key: str
    label: str
    category: str
    data_type: str
    units: list[str]


class ReviewCategorySummary(BaseModel):
    category: str
    total: int
    reviewed: int
    pending: int
    conflicts: int
    complete: bool


class ReviewSummaryRead(BaseModel):
    run_id: int
    machine_profile_id: int
    machine_name: str
    selected_variant: str | None
    run_status: str
    documents_analyzed: int
    total: int
    found: int
    not_found: int
    conflicting: int
    ambiguous: int
    pending: int
    accepted: int
    accepted_with_edit: int
    rejected: int
    deferred: int
    manually_entered: int
    not_applicable: int
    found_pending: int
    not_found_pending: int
    conflict_pending: int
    ambiguous_pending: int
    high_confidence_eligible: int
    safety_low_confidence_pending: int
    remaining_required_review: int
    reviewed: int
    review_progress_percent: float
    documentation_coverage: float
    category_summaries: list[ReviewCategorySummary]
    draft_ready: bool
    approval_ready: bool
    variant_rerun_required: bool
    readiness_reasons: list[str]
    recommended_next_queue: str | None
    confidence_high_threshold: float
    confidence_medium_threshold: float


class ReviewQueueRead(BaseModel):
    queue: str
    total: int
    page: int
    page_size: int
    items: list[ProposalRead]


class BatchReviewConfirmation(BaseModel):
    acknowledge_advisory_only: bool = False


class BatchReviewRequest(BaseModel):
    proposal_ids: list[int] = Field(min_length=1, max_length=500)
    action: str = Field(pattern="^(accept|defer|reject|not_applicable)$")
    confirmation: BatchReviewConfirmation = Field(
        default_factory=BatchReviewConfirmation
    )


class BatchReviewFailure(BaseModel):
    proposal_id: int
    reason: str


class BatchReviewResponse(BaseModel):
    succeeded: list[int]
    failed: list[BatchReviewFailure]
    summary: ReviewSummaryRead


class AcceptEligibleHighConfidenceRequest(BaseModel):
    proposal_ids: list[int] | None = Field(default=None, max_length=500)
    confirmation: BatchReviewConfirmation


class ReviewEventRequest(BaseModel):
    event_type: str = Field(
        pattern=(
            "^(review_queue_opened|field_batch_selected|source_drawer_opened|"
            "source_drawer_closed|guided_review_started|guided_review_completed|"
            "review_filter_changed)$"
        )
    )
    queue: str | None = Field(default=None, max_length=50)
    proposal_id: int | None = None
    document_id: int | None = None
    selected_count: int | None = Field(default=None, ge=0, le=500)


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

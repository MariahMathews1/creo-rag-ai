from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SAFETY_NOTICE = (
    "Similarity to previously approved programs does not certify machining safety, "
    "post-processor correctness, setup correctness, or production readiness. "
    "Qualified review and simulation remain required."
)

ProgramType = Literal[
    "turning", "milling", "drilling", "threading", "boring", "facing",
    "grooving", "parting", "mill_turn", "setup", "test", "other",
]
ApprovalStatus = Literal[
    "unreviewed", "externally_reviewed", "approved_reference", "deprecated",
    "rejected_reference", "unknown",
]
EligibilityStatus = Literal["pending", "eligible", "ineligible", "requires_review"]


class AdvisoryBoundary(BaseModel):
    advisory_only: bool = True
    historical_similarity_is_not_certification: bool = True
    qualified_review_required: bool = True
    safety_notice: str = SAFETY_NOTICE


class ReferenceProgramCreate(BaseModel):
    machine_profile_revision_id: int
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    source_text: str = Field(min_length=1)
    original_filename: str | None = None
    program_type: ProgramType = "other"
    controller_name: str | None = None
    controller_version: str | None = None
    controller_variant: str | None = None
    post_processor_name: str | None = None
    post_processor_version: str | None = None
    post_processor_revision: str | None = None
    part_identifier: str | None = None
    operation_identifier: str | None = None
    material: str | None = None
    units: str | None = None
    machine_variant: str | None = None
    installed_options_json: list = Field(default_factory=list)
    tooling_context_json: dict = Field(default_factory=dict)
    workholding_context_json: dict = Field(default_factory=dict)
    coordinate_system_context_json: dict = Field(default_factory=dict)
    approval_status: ApprovalStatus = "unreviewed"
    approved_by_label: str | None = None
    ai_processing_allowed: bool = False


class ReferenceProgramUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    program_type: ProgramType | None = None
    controller_name: str | None = None
    controller_version: str | None = None
    controller_variant: str | None = None
    post_processor_name: str | None = None
    post_processor_version: str | None = None
    post_processor_revision: str | None = None
    part_identifier: str | None = None
    operation_identifier: str | None = None
    material: str | None = None
    units: str | None = None
    machine_variant: str | None = None
    installed_options_json: list | None = None
    tooling_context_json: dict | None = None
    workholding_context_json: dict | None = None
    coordinate_system_context_json: dict | None = None
    approval_status: ApprovalStatus | None = None
    approved_by_label: str | None = None
    ai_processing_allowed: bool | None = None


class ReferenceProgramRead(AdvisoryBoundary):
    model_config = ConfigDict(from_attributes=True)
    id: int
    machine_profile_id: int
    machine_profile_revision_id: int
    source_document_id: int | None
    superseded_by_id: int | None
    name: str
    description: str | None
    original_filename: str | None
    file_hash: str
    program_number: str | None
    program_type: str
    controller_name: str | None
    controller_version: str | None
    controller_variant: str | None
    post_processor_name: str | None
    post_processor_version: str | None
    post_processor_revision: str | None
    part_identifier: str | None
    operation_identifier: str | None
    material: str | None
    units: str | None
    machine_variant: str | None
    installed_options_json: list
    tooling_context_json: dict
    workholding_context_json: dict
    coordinate_system_context_json: dict
    approval_status: str
    eligibility_status: str
    eligibility_reason: str | None
    approved_by_label: str | None
    approved_at: datetime | None
    parsing_status: str
    parser_version: str | None
    rule_set_version: str | None
    validation_summary_json: dict
    source_integrity_json: dict
    ai_processing_allowed: bool
    valid_from: datetime | None
    valid_to: datetime | None
    imported_at: datetime
    created_at: datetime
    updated_at: datetime


class EligibilityRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ReferenceProgramBlockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference_program_id: int
    block_index: int
    line_number: int
    original_text: str
    cleaned_text: str
    sequence_number: int | None
    program_number: int | None
    g_codes_json: list
    m_codes_json: list
    coordinates_json: dict
    comments_json: list
    state_before_json: dict
    state_after_json: dict
    parse_errors_json: list
    parser_version: str


class ReferenceProgramDetail(ReferenceProgramRead):
    blocks: list[ReferenceProgramBlockRead] = Field(default_factory=list)


class StandardExtractionCreate(BaseModel):
    machine_profile_revision_id: int
    reference_program_ids: list[int] = Field(min_length=1, max_length=500)
    post_processor_revision: str | None = None
    settings: dict = Field(default_factory=dict)


class StandardExtractionRunRead(AdvisoryBoundary):
    model_config = ConfigDict(from_attributes=True)
    id: int
    machine_profile_id: int
    machine_profile_revision_id: int
    status: str
    selected_reference_program_ids_json: list
    algorithm_version: str
    settings_json: dict
    summary_json: dict
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    failure_message: str | None


class ConventionEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    standard_convention_id: int
    reference_program_id: int
    gcode_block_id: int | None
    line_start: int | None
    line_end: int | None
    excerpt: str
    evidence_type: str
    match_context_json: dict
    program_name: str | None = None


class StandardConventionRead(AdvisoryBoundary):
    model_config = ConfigDict(from_attributes=True)
    id: int
    standard_profile_id: int | None
    extraction_run_id: int | None
    convention_key: str
    category: str
    title: str
    description: str
    convention_type: str
    expected_pattern_json: dict
    condition_json: dict
    expected_behavior_json: dict
    applicability_json: dict
    severity: str
    confidence: float
    support_count: int
    eligible_program_count: int
    support_percentage: float
    frequency_classification: str
    proposal_status: str
    review_status: str
    review_note: str | None
    safety_relevant: bool
    reviewed_at: datetime | None
    evidence: list[ConventionEvidenceRead] = Field(default_factory=list)


class ConventionReviewRequest(BaseModel):
    review_status: Literal[
        "accepted", "accepted_with_edit", "rejected", "deferred"
    ]
    expected_pattern_json: dict | None = None
    review_note: str | None = None


class ConventionBatchReviewRequest(BaseModel):
    convention_ids: list[int] = Field(min_length=1, max_length=500)
    review_status: Literal["accepted", "rejected", "deferred"]
    acknowledge_frequency_is_not_requirement: bool = False


class StandardDraftRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)


class StandardProfileRead(AdvisoryBoundary):
    model_config = ConfigDict(from_attributes=True)
    id: int
    machine_profile_id: int
    machine_profile_revision_id: int
    name: str
    revision_number: int
    status: str
    source_program_ids_json: list
    source_document_ids_json: list
    created_from_revision_id: int | None
    summary_json: dict
    stale: bool
    stale_reasons_json: list
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    superseded_at: datetime | None
    conventions: list[StandardConventionRead] = Field(default_factory=list)


class StandardDecisionRequest(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class ComparisonCreate(BaseModel):
    standard_profile_id: int
    reference_program_id: int | None = None


class ComparisonFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    comparison_run_id: int
    standard_convention_id: int | None
    severity: str
    status: str
    title: str
    description: str
    line_number: int | None
    source_line: str | None
    expected_pattern_json: dict
    observed_pattern_json: dict
    comparison_type: str
    recommendation: str
    exception_classification: str | None
    exception_note: str | None
    created_at: datetime


class ComparisonRunRead(AdvisoryBoundary):
    model_config = ConfigDict(from_attributes=True)
    id: int
    analysis_project_id: int
    machine_profile_revision_id: int
    standard_profile_id: int
    reference_program_id: int | None
    status: str
    summary_json: dict
    parser_version: str
    algorithm_version: str
    standard_revision_snapshot_json: dict
    stale: bool
    stale_reasons_json: list
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    failure_message: str | None
    findings: list[ComparisonFindingRead] = Field(default_factory=list)


class ExceptionRequest(BaseModel):
    classification: Literal[
        "expected_exception", "different_operation_type", "different_post_revision",
        "different_machine_option", "intentional_programmer_choice",
        "requires_investigation", "standard_should_be_updated", "unknown",
    ]
    note: str = Field(min_length=1, max_length=2000)


class SimilarProgramRead(BaseModel):
    program: ReferenceProgramRead
    similarity_score: float
    match_reasons: list[str]
    differences: list[str]
    advisory_only: bool = True
    historical_similarity_is_not_certification: bool = True
    qualified_review_required: bool = True
    safety_notice: str = SAFETY_NOTICE


class SideBySideRead(AdvisoryBoundary):
    comparison_id: int
    current_program: str
    reference_program: str
    sections: list[dict]
    source_metadata: dict
    deterministic_findings: list[dict]
    convention_findings: list[ComparisonFindingRead]

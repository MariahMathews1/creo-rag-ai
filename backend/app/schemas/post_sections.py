from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SectionKey = Literal["program_structure", "tooling", "spindle", "coolant", "feed", "motion", "coordinates", "program_end", "cycles"]
ReadinessStatus = Literal["ready", "ready_with_review", "needs_information", "blocked", "deferred"]
RuleReviewAction = Literal["accept", "edit_accept", "reject", "needs_information"]


class MachineFactRead(BaseModel):
    key: str
    label: str
    value: object | None
    status: Literal["known", "needs_review", "unknown", "not_applicable"]
    critical: bool = False
    source: str


class PostSectionReadinessRead(BaseModel):
    section_key: SectionKey
    label: str
    readiness: ReadinessStatus
    manual_setup_readiness: ReadinessStatus
    ai_drafting_readiness: ReadinessStatus
    known_machine_facts: list[MachineFactRead]
    missing_information: list[str]
    warnings: list[str]
    conflicts: list[dict]
    evidence_count: int
    reviewed_rule_count: int
    current_draft_status: str
    draft_allowed: bool


class PostBuilderEvidenceRead(BaseModel):
    evidence_id: int
    document_id: int
    document_title: str
    document_type: str
    page_start: int | None
    page_end: int | None
    section_title: str | None
    excerpt: str
    relevance_score: float
    matched_terms: list[str]
    ai_eligible: bool
    conflict_labels: list[str] = Field(default_factory=list)


class EvidenceSelectionRequest(BaseModel):
    query: str | None = Field(default=None, max_length=500)


class PostSectionGenerateRequest(BaseModel):
    evidence_ids: list[int] = Field(default_factory=list, max_length=12)
    evidence_mode: Literal["same", "refresh"] = "refresh"
    context_reviewed: bool


class PostRuleReviewRequest(BaseModel):
    reviewer_label: str = Field(min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=2000)
    edited_template: str | None = Field(default=None, max_length=4000)


class PostRuleDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_key: str
    name: str
    description: str | None
    condition: str
    output_behavior: str
    ai_draft_template: str | None
    engineer_template: str | None
    required_machine_facts_json: list
    evidence_ids_json: list
    assumptions_json: list
    warnings_json: list
    status: str
    review_reason: str | None
    reviewer_label: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PostSectionDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    gpost_draft_id: int
    section_key: SectionKey
    section_version: int
    status: str
    source_type: str
    machine_context_snapshot_json: dict
    draft_templates_json: list
    missing_information_json: list
    assumptions_json: list
    warnings_json: list
    source_evidence_json: list
    ai_generated: bool
    provider: str | None
    model: str | None
    prompt_version: str | None
    response_schema_version: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    rules: list[PostRuleDraftRead]
    advisory_only: Literal[True] = True


class PostSectionCompareRead(BaseModel):
    left_version: int
    right_version: int
    rules_added: list[str]
    rules_removed: list[str]
    templates_changed: list[str]
    evidence_changed: bool
    assumptions_changed: bool

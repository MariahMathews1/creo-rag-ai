from typing import Literal

from pydantic import BaseModel, Field


PostSectionKey = Literal["program_structure", "tooling", "spindle", "coolant", "motion", "coordinates", "feed", "cycles", "program_end"]


class ApprovedDocumentExcerpt(BaseModel):
    document_id: int
    excerpt: str = Field(min_length=1, max_length=4000)
    page: int | None = None
    section: str | None = None
    external_processing_approved: Literal[True]


class PostBuilderRequest(BaseModel):
    machine_profile_id: int
    machine_profile_revision_id: int | None = None
    post_draft_id: int | None = None
    selected_post_section: PostSectionKey
    existing_reviewed_rules: list[dict] = Field(default_factory=list, max_length=30)
    relevant_document_excerpts: list[ApprovedDocumentExcerpt] = Field(default_factory=list, max_length=8)


class DraftPostRule(BaseModel):
    rule_key: str
    name: str
    condition: str
    output_behavior: str
    evidence_reference_ids: list[int] = Field(default_factory=list)
    review_status: Literal["draft"] = "draft"


class PostBuilderSectionResponse(BaseModel):
    section_key: PostSectionKey
    status: Literal["draft", "needs_machine_information"]
    draft_rules: list[DraftPostRule]
    draft_templates: list[dict]
    missing_information: list[str]
    assumptions: list[str]
    source_reference_ids: list[int]
    warnings: list[str]
    provider_metadata: dict
    invocation_id: int
    advisory_only: Literal[True] = True
    safety_notice: str = "R&D MACHINE-LEVEL POST ASSISTANCE ONLY · ENGINEER REVIEW REQUIRED"


class PostBuilderProviderStatus(BaseModel):
    provider: Literal["disabled", "mock", "azure_openai"]
    configured: bool
    reachable: bool | None
    authentication_mode: str | None
    deployment: str | None
    model: str | None
    external_processing: bool
    public_web: Literal[False] = False
    data_source: str = "Approved Machine Knowledge and Selected Machine-Level Document Excerpts"
    mode: Literal["R&D Post Development"] = "R&D Post Development"
    cl_ncl_ai_access: Literal["prohibited"] = "prohibited"
    error_code: str | None = None

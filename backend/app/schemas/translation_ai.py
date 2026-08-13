from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderStatus(BaseModel):
    provider: Literal["disabled", "mock", "azure_openai"]
    configured: bool
    reachable: bool | None
    authentication_mode: str | None
    deployment: str | None
    model: str | None
    external_processing: bool
    public_web: Literal[False] = False
    data_source: str = "Verified Internal Translation Examples Only"
    mode: Literal["R&D"] = "R&D"
    error_code: str | None = None


class TranslationRetrievalRequest(BaseModel):
    machine_profile_id: int
    machine_profile_revision_id: int | None = None
    controller_name: str | None = None
    controller_version: str | None = None
    post_processor_name: str | None = None
    post_processor_revision: str | None = None
    operation_type: str | None = None
    cl_text: str = Field(min_length=1, max_length=20_000)
    max_examples: int = Field(default=5, ge=1, le=8)
    allow_revision_fallback: bool = False
    allow_machine_family_fallback: bool = False


class RetrievedTranslationExample(BaseModel):
    example_id: int
    name: str
    machine_profile_id: int
    machine: str
    machine_profile_revision_id: int
    controller: str | None
    post_revision: str | None
    operation: str
    cl_excerpt: str
    gcode_excerpt: str
    cl_pattern_match: Literal["strong", "related", "none"]
    alignment_coverage: float
    verification_status: str
    retrieval_reasons: list[str]
    ai_processing_allowed: bool


class TranslationRetrievalResponse(BaseModel):
    retrieval_scope: str
    examples: list[RetrievedTranslationExample]
    eligible_count: int
    public_web: Literal[False] = False
    ai_called: Literal[False] = False
    warnings: list[str] = Field(default_factory=list)


class TranslationExplanationRequest(BaseModel):
    retrieval: TranslationRetrievalRequest
    example_ids: list[int] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def unique_examples(self):
        self.example_ids = list(dict.fromkeys(self.example_ids))
        return self


class AIConsentRequest(BaseModel):
    allowed: bool
    reviewer_label: str = Field(min_length=1, max_length=120)
    acknowledgement: bool
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def acknowledge_change(self):
        if not self.acknowledgement:
            raise ValueError("Explicit acknowledgement is required to change AI-processing permission")
        return self


class TranslationExplanationResponse(BaseModel):
    status: str
    input_cl: str
    interpreted_operation: str | None
    suggested_mapping_pattern: str | None
    short_rationale: str
    example_ids: list[int]
    uncertainties: list[str]
    unsupported_features: list[str]
    warnings: list[str]
    provider_metadata: dict
    invocation_id: int
    advisory_only: Literal[True] = True
    safety_notice: str = "R&D ADVISORY INTERPRETATION ONLY · NOT EXECUTABLE G-CODE"


class AIInvocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    provider: str
    operation_type: str
    machine_profile_id: int
    machine_profile_revision_id: int | None
    translation_example_ids_json: list
    input_hash: str
    prompt_template_version: str
    response_schema_version: str
    response_status: str
    external_processing: bool
    provider_metadata_json: dict
    token_usage_json: dict
    duration_ms: int | None
    created_at: datetime

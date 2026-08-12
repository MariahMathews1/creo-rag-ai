from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DraftStatus = Literal["draft", "under_review", "review_required", "validated_for_rnd", "superseded", "archived"]
MappingType = Literal["direct", "stateful", "conditional", "template", "cycle", "unsupported", "manual"]
ReviewStatus = Literal["pending", "accepted", "accepted_with_edit", "rejected", "deferred"]
SupportStatus = Literal["supported", "not_applicable", "unsupported_required", "not_implemented"]


class GPostDraftCreate(BaseModel):
    machine_profile_revision_id: int
    name: str = Field(min_length=1, max_length=180)
    controller_family: Literal["fanuc_mill", "fanuc_lathe", "haas_mill", "generic_research"]
    selected_document_ids: list[int] = Field(default_factory=list)
    standard_profile_id: int | None = None
    reference_program_ids: list[int] = Field(default_factory=list)
    manual_configuration_acknowledged: bool = False


class GPostDraftUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    status: DraftStatus | None = None
    selected_document_ids: list[int] | None = None
    standard_profile_id: int | None = None
    reference_program_ids: list[int] | None = None
    templates_json: dict[str, str] | None = None
    manual_configuration_acknowledged: bool | None = None


class GPostEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_type: str
    document_id: int | None
    document_chunk_id: int | None
    reference_program_id: int | None
    standard_convention_id: int | None
    page: int | None
    section: str | None
    excerpt: str | None
    authority_level: str | None
    metadata_json: dict


class GPostEvidenceCreate(BaseModel):
    source_type: Literal["document", "reference_program", "standard_convention", "manual_configuration"]
    document_id: int | None = None
    document_chunk_id: int | None = None
    reference_program_id: int | None = None
    standard_convention_id: int | None = None
    page: int | None = None
    section: str | None = None
    excerpt: str | None = None
    authority_level: str | None = None
    metadata_json: dict = Field(default_factory=dict)


class GPostMappingBase(BaseModel):
    mapping_key: str = Field(min_length=1, max_length=100)
    cl_command: str = Field(min_length=1, max_length=40)
    mapping_type: MappingType
    output_template: str | None = None
    template_key: str | None = None
    template_override: str | None = None
    uses_override: bool = False
    support_status: SupportStatus = "supported"
    required_for_v1: bool = False
    description: str | None = None
    conditions_json: dict = Field(default_factory=dict)
    required_state_json: dict = Field(default_factory=dict)
    resulting_state_json: dict = Field(default_factory=dict)
    machine_type_scope: str | None = None
    dialect_scope: str | None = None
    supported: bool = True
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_type: str = "manual_configuration"
    source_document_id: int | None = None
    source_chunk_id: int | None = None
    source_page: int | None = None
    source_section: str | None = None
    source_excerpt: str | None = None
    source_authority: str | None = None
    review_status: ReviewStatus = "pending"
    review_note: str | None = None

    @model_validator(mode="after")
    def unsupported_has_no_template(self):
        if self.mapping_type == "unsupported" and self.support_status == "supported":
            self.support_status = "not_implemented"
        if self.support_status != "supported":
            self.supported = False
        return self


class GPostMappingCreate(GPostMappingBase):
    pass


class GPostMappingUpdate(BaseModel):
    mapping_key: str | None = None
    cl_command: str | None = None
    mapping_type: MappingType | None = None
    output_template: str | None = None
    template_key: str | None = None
    template_override: str | None = None
    uses_override: bool | None = None
    support_status: SupportStatus | None = None
    required_for_v1: bool | None = None
    description: str | None = None
    conditions_json: dict | None = None
    required_state_json: dict | None = None
    resulting_state_json: dict | None = None
    machine_type_scope: str | None = None
    dialect_scope: str | None = None
    supported: bool | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_type: str | None = None
    source_document_id: int | None = None
    source_chunk_id: int | None = None
    source_page: int | None = None
    source_section: str | None = None
    source_excerpt: str | None = None
    source_authority: str | None = None
    review_status: ReviewStatus | None = None
    review_note: str | None = None


class GPostMappingRead(GPostMappingBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    gpost_draft_id: int
    evidence: list[GPostEvidenceRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    effective_output_template: str | None = None


class GPostDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    machine_profile_id: int
    machine_profile_revision_id: int
    created_from_draft_id: int | None
    name: str
    version: int
    status: DraftStatus
    controller_family: str
    machine_type: str
    selected_document_ids_json: list[int]
    standard_profile_id: int | None
    reference_program_ids_json: list[int]
    manual_configuration_acknowledged: bool
    capability_snapshot_json: dict
    machine_profile_snapshot_json: dict
    templates_json: dict
    unsupported_features_json: list
    warnings_json: list
    review_summary_json: dict
    created_at: datetime
    updated_at: datetime
    superseded_at: datetime | None
    advisory_only: Literal[True] = True
    safety_notice: str = "R&D ONLY · NON-PRODUCTION · NOT VALIDATED FOR MACHINE USE"


class PreviewRequest(BaseModel):
    cl_source: str = Field(min_length=1)


class PreviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    gpost_draft_id: int
    status: str
    generated_gcode: str
    parser_diagnostics_json: list
    deterministic_findings_json: list
    unsupported_commands_json: list
    missing_mappings_json: list
    warnings_json: list
    traceability_json: list
    summary_json: dict
    parser_version: str
    rule_set_version: str
    created_at: datetime
    safety_notice: str = "R&D ONLY · NON-PRODUCTION · NOT VALIDATED FOR MACHINE USE"


class VersionCompareRead(BaseModel):
    left_draft_id: int
    right_draft_id: int
    mappings_added: list[str]
    mappings_removed: list[str]
    templates_changed: list[str]
    conditions_changed: list[str]
    evidence_changed: list[str]
    warnings_added: list
    warnings_resolved: list


class RndValidationRequest(BaseModel):
    acknowledge_rnd_only: bool

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

VerificationStatus = Literal["unknown", "candidate", "reviewed", "verified_successful", "deprecated", "invalid"]
OperationType = Literal["turning", "facing", "boring", "drilling", "threading", "grooving", "parting", "milling", "pocketing", "contouring", "tapping", "reaming", "setup", "test", "other"]


class TranslationCreate(BaseModel):
    machine_profile_id: int
    machine_profile_revision_id: int
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    controller_name: str | None = None
    controller_version: str | None = None
    post_processor_name: str | None = None
    post_processor_revision: str | None = None
    operation_type: OperationType = "other"
    operation_name: str | None = None
    cl_source_text: str = Field(min_length=1)
    cl_original_filename: str | None = None
    gcode_source_text: str = Field(min_length=1)
    gcode_original_filename: str | None = None
    verification_status: Literal["unknown", "candidate", "reviewed"] = "candidate"
    part_identifier: str | None = None
    program_identifier: str | None = None
    project_identifier: str | None = None
    tooling_context_json: dict = Field(default_factory=dict)
    setup_context_json: dict = Field(default_factory=dict)
    source_system: str | None = None
    source_repository: str | None = None
    work_order_reference: str | None = None
    imported_by_label: str | None = None
    source_provenance: str | None = None
    verification_basis: str | None = None
    verification_note: str | None = None
    reference_program_id: int | None = None
    ai_processing_allowed: bool = False


class TranslationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    post_processor_name: str | None = None
    post_processor_revision: str | None = None
    operation_type: OperationType | None = None
    operation_name: str | None = None
    part_identifier: str | None = None
    program_identifier: str | None = None
    project_identifier: str | None = None
    tooling_context_json: dict | None = None
    setup_context_json: dict | None = None
    source_system: str | None = None
    source_repository: str | None = None
    work_order_reference: str | None = None
    imported_by_label: str | None = None
    source_provenance: str | None = None
    verification_basis: str | None = None
    verification_note: str | None = None
    ai_processing_allowed: bool | None = None


class StatusRequest(BaseModel):
    note: str = Field(min_length=1)
    reviewer_label: str = Field(min_length=1)
    acknowledgement: bool = False


class TranslationPreviewRequest(BaseModel):
    machine_profile_id: int
    machine_profile_revision_id: int
    cl_source_text: str = Field(min_length=1)
    gcode_source_text: str = Field(min_length=1)


class LinkCreate(BaseModel):
    cl_record_start: int | None = Field(default=None, ge=0)
    cl_record_end: int | None = Field(default=None, ge=0)
    gcode_block_start: int | None = Field(default=None, ge=0)
    gcode_block_end: int | None = Field(default=None, ge=0)
    link_type: Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many", "manual", "unmatched"]
    confidence: float = Field(default=0, ge=0, le=1)
    review_status: Literal["proposed", "confirmed", "rejected", "edited"] = "proposed"
    match_reasons_json: list = Field(default_factory=list)
    notes: str | None = None
    reviewed_by_label: str | None = None

    @model_validator(mode="after")
    def validate_spans(self):
        if self.cl_record_start is None and self.gcode_block_start is None:
            raise ValueError("At least one CL or G-code span is required")
        if self.cl_record_start is not None and self.cl_record_end is not None and self.cl_record_end < self.cl_record_start:
            raise ValueError("CL span end must not precede its start")
        if self.gcode_block_start is not None and self.gcode_block_end is not None and self.gcode_block_end < self.gcode_block_start:
            raise ValueError("G-code span end must not precede its start")
        return self


class LinkUpdate(BaseModel):
    cl_record_start: int | None = Field(default=None, ge=0)
    cl_record_end: int | None = Field(default=None, ge=0)
    gcode_block_start: int | None = Field(default=None, ge=0)
    gcode_block_end: int | None = Field(default=None, ge=0)
    link_type: Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many", "manual", "unmatched"] | None = None
    review_status: Literal["proposed", "confirmed", "rejected", "edited"] | None = None
    notes: str | None = None
    reviewed_by_label: str | None = None


class LinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; alignment_id: int
    cl_record_start: int | None; cl_record_end: int | None
    gcode_block_start: int | None; gcode_block_end: int | None
    link_type: str; confidence: float; review_status: str
    match_reasons_json: list; notes: str | None; reviewed_by_label: str | None
    created_at: datetime; updated_at: datetime


class AlignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; translation_example_id: int; status: str; algorithm_version: str
    summary_json: dict; created_at: datetime; updated_at: datetime
    links: list[LinkRead] = Field(default_factory=list)


class TranslationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; machine_profile_id: int; machine_profile_revision_id: int; reference_program_id: int | None
    name: str; description: str | None; controller_name: str | None; controller_version: str | None
    post_processor_name: str | None; post_processor_revision: str | None
    operation_type: str; operation_name: str | None
    cl_source_text: str; cl_source_hash: str; cl_original_filename: str | None
    gcode_source_text: str; gcode_source_hash: str; gcode_original_filename: str | None
    verification_status: str; part_identifier: str | None; program_identifier: str | None; project_identifier: str | None
    tooling_context_json: dict; setup_context_json: dict; machine_context_snapshot_json: dict
    source_system: str | None; source_repository: str | None; work_order_reference: str | None
    imported_by_label: str | None; source_provenance: str | None; verification_basis: str | None; verification_note: str | None
    cl_parse_summary_json: dict; gcode_parse_summary_json: dict; parsed_cl_records_json: list; parsed_gcode_blocks_json: list
    validation_summary_json: dict; ai_processing_allowed: bool
    created_at: datetime; updated_at: datetime; reviewed_at: datetime | None; verified_at: datetime | None; deprecated_at: datetime | None
    alignments: list[AlignmentRead] = Field(default_factory=list)
    advisory_only: Literal[True] = True
    safety_notice: str = "R&D DATASET ONLY · VERIFIED HISTORICAL EVIDENCE IS NOT PRODUCTION AUTHORIZATION"


class DatasetSummary(BaseModel):
    total: int; candidates: int; reviewed: int; verified: int; deprecated: int; invalid: int
    by_machine: list[dict]; by_post_revision: list[dict]; by_operation: list[dict]

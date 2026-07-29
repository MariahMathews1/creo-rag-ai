from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.entities import utc_now


class ReferenceProgram(Base):
    __tablename__ = "reference_programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"), index=True)
    machine_profile_revision_id: Mapped[int] = mapped_column(
        ForeignKey("machine_profile_revisions.id"), index=True
    )
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_documents.id"), nullable=True
    )
    superseded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("reference_programs.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_text: Mapped[str] = mapped_column(Text)
    program_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    program_type: Mapped[str] = mapped_column(String(30), default="other")
    controller_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    controller_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    controller_variant: Mapped[str | None] = mapped_column(String(120), nullable=True)
    post_processor_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    post_processor_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    post_processor_revision: Mapped[str | None] = mapped_column(String(80), nullable=True)
    part_identifier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    operation_identifier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    material: Mapped[str | None] = mapped_column(String(80), nullable=True)
    units: Mapped[str | None] = mapped_column(String(20), nullable=True)
    machine_variant: Mapped[str | None] = mapped_column(String(120), nullable=True)
    installed_options_json: Mapped[list] = mapped_column(JSON, default=list)
    tooling_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    workholding_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    coordinate_system_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    approval_status: Mapped[str] = mapped_column(String(30), default="unreviewed")
    eligibility_status: Mapped[str] = mapped_column(String(30), default="pending")
    eligibility_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parsing_status: Mapped[str] = mapped_column(String(30), default="pending")
    parser_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rule_set_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    validation_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_integrity_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_processing_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
    blocks: Mapped[list["ReferenceProgramBlock"]] = relationship(
        back_populates="reference_program", cascade="all, delete-orphan"
    )


class ReferenceProgramBlock(Base):
    __tablename__ = "reference_program_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference_program_id: Mapped[int] = mapped_column(
        ForeignKey("reference_programs.id"), index=True
    )
    block_index: Mapped[int] = mapped_column(Integer)
    line_number: Mapped[int] = mapped_column(Integer)
    original_text: Mapped[str] = mapped_column(Text)
    cleaned_text: Mapped[str] = mapped_column(Text)
    sequence_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    program_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    g_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    m_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    coordinates_json: Mapped[dict] = mapped_column(JSON, default=dict)
    comments_json: Mapped[list] = mapped_column(JSON, default=list)
    state_before_json: Mapped[dict] = mapped_column(JSON, default=dict)
    state_after_json: Mapped[dict] = mapped_column(JSON, default=dict)
    parse_errors_json: Mapped[list] = mapped_column(JSON, default=list)
    parser_version: Mapped[str] = mapped_column(String(40), default="gcode-parser-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    reference_program: Mapped[ReferenceProgram] = relationship(back_populates="blocks")


class StandardExtractionRun(Base):
    __tablename__ = "standard_extraction_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"), index=True)
    machine_profile_revision_id: Mapped[int] = mapped_column(
        ForeignKey("machine_profile_revisions.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="processing")
    selected_reference_program_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    algorithm_version: Mapped[str] = mapped_column(String(40), default="standards-v1")
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class OrganizationalStandardProfile(Base):
    __tablename__ = "organizational_standard_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"), index=True)
    machine_profile_revision_id: Mapped[int] = mapped_column(
        ForeignKey("machine_profile_revisions.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(180))
    revision_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    source_program_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    source_document_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    created_from_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizational_standard_profiles.id"), nullable=True
    )
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)
    stale_reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    conventions: Mapped[list["StandardConvention"]] = relationship(
        back_populates="standard_profile"
    )


class StandardConvention(Base):
    __tablename__ = "standard_conventions"

    id: Mapped[int] = mapped_column(primary_key=True)
    standard_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizational_standard_profiles.id"), nullable=True, index=True
    )
    extraction_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("standard_extraction_runs.id"), nullable=True, index=True
    )
    convention_key: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    convention_type: Mapped[str] = mapped_column(String(40))
    expected_pattern_json: Mapped[dict] = mapped_column(JSON, default=dict)
    condition_json: Mapped[dict] = mapped_column(JSON, default=dict)
    expected_behavior_json: Mapped[dict] = mapped_column(JSON, default=dict)
    applicability_json: Mapped[dict] = mapped_column(JSON, default=dict)
    severity: Mapped[str] = mapped_column(String(30), default="informational")
    confidence: Mapped[float] = mapped_column(Float, default=0)
    support_count: Mapped[int] = mapped_column(Integer, default=0)
    eligible_program_count: Mapped[int] = mapped_column(Integer, default=0)
    support_percentage: Mapped[float] = mapped_column(Float, default=0)
    frequency_classification: Mapped[str] = mapped_column(
        String(30), default="insufficient_evidence"
    )
    proposal_status: Mapped[str] = mapped_column(String(30), default="proposed")
    review_status: Mapped[str] = mapped_column(String(30), default="pending")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    safety_relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
    standard_profile: Mapped[OrganizationalStandardProfile | None] = relationship(
        back_populates="conventions"
    )
    evidence: Mapped[list["StandardConventionEvidence"]] = relationship(
        back_populates="convention", cascade="all, delete-orphan"
    )


class StandardConventionEvidence(Base):
    __tablename__ = "standard_convention_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    standard_convention_id: Mapped[int] = mapped_column(
        ForeignKey("standard_conventions.id"), index=True
    )
    reference_program_id: Mapped[int] = mapped_column(
        ForeignKey("reference_programs.id"), index=True
    )
    gcode_block_id: Mapped[int | None] = mapped_column(
        ForeignKey("reference_program_blocks.id"), nullable=True
    )
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    excerpt: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(30))
    match_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    convention: Mapped[StandardConvention] = relationship(back_populates="evidence")
    reference_program: Mapped[ReferenceProgram] = relationship()


class ProgramComparisonRun(Base):
    __tablename__ = "program_comparison_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_project_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_projects.id"), index=True
    )
    machine_profile_revision_id: Mapped[int] = mapped_column(
        ForeignKey("machine_profile_revisions.id")
    )
    standard_profile_id: Mapped[int] = mapped_column(
        ForeignKey("organizational_standard_profiles.id")
    )
    reference_program_id: Mapped[int | None] = mapped_column(
        ForeignKey("reference_programs.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="processing")
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    parser_version: Mapped[str] = mapped_column(String(40), default="gcode-parser-v1")
    algorithm_version: Mapped[str] = mapped_column(String(40), default="comparison-v1")
    standard_revision_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)
    stale_reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings: Mapped[list["ProgramComparisonFinding"]] = relationship(
        back_populates="comparison_run", cascade="all, delete-orphan"
    )


class ProgramComparisonFinding(Base):
    __tablename__ = "program_comparison_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    comparison_run_id: Mapped[int] = mapped_column(
        ForeignKey("program_comparison_runs.id"), index=True
    )
    standard_convention_id: Mapped[int | None] = mapped_column(
        ForeignKey("standard_conventions.id"), nullable=True
    )
    severity: Mapped[str] = mapped_column(String(30), default="informational")
    status: Mapped[str] = mapped_column(String(30), default="open")
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_pattern_json: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_pattern_json: Mapped[dict] = mapped_column(JSON, default=dict)
    comparison_type: Mapped[str] = mapped_column(String(30))
    recommendation: Mapped[str] = mapped_column(Text)
    exception_classification: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    exception_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    comparison_run: Mapped[ProgramComparisonRun] = relationship(back_populates="findings")


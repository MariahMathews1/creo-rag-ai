from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.entities import utc_now


class GPostDraft(Base):
    __tablename__ = "gpost_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"), index=True)
    machine_profile_revision_id: Mapped[int] = mapped_column(ForeignKey("machine_profile_revisions.id"), index=True)
    created_from_draft_id: Mapped[int | None] = mapped_column(ForeignKey("gpost_drafts.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(180))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    controller_family: Mapped[str] = mapped_column(String(40))
    machine_type: Mapped[str] = mapped_column(String(40))
    selected_document_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    standard_profile_id: Mapped[int | None] = mapped_column(ForeignKey("organizational_standard_profiles.id"), nullable=True)
    reference_program_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    capability_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    machine_profile_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    templates_json: Mapped[dict] = mapped_column(JSON, default=dict)
    unsupported_features_json: Mapped[list] = mapped_column(JSON, default=list)
    warnings_json: Mapped[list] = mapped_column(JSON, default=list)
    review_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    mappings: Mapped[list["GPostMapping"]] = relationship(back_populates="draft", cascade="all, delete-orphan")
    preview_runs: Mapped[list["GPostPreviewRun"]] = relationship(back_populates="draft", cascade="all, delete-orphan")


class GPostDraftVersion(Base):
    __tablename__ = "gpost_draft_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    gpost_draft_id: Mapped[int] = mapped_column(ForeignKey("gpost_drafts.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    change_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class GPostMapping(Base):
    __tablename__ = "gpost_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    gpost_draft_id: Mapped[int] = mapped_column(ForeignKey("gpost_drafts.id"), index=True)
    mapping_key: Mapped[str] = mapped_column(String(100), index=True)
    cl_command: Mapped[str] = mapped_column(String(40), index=True)
    mapping_type: Mapped[str] = mapped_column(String(30))
    output_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    required_state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    resulting_state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    machine_type_scope: Mapped[str | None] = mapped_column(String(40), nullable=True)
    dialect_scope: Mapped[str | None] = mapped_column(String(40), nullable=True)
    supported: Mapped[bool] = mapped_column(default=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_type: Mapped[str] = mapped_column(String(40), default="manual_configuration")
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)
    source_chunk_id: Mapped[int | None] = mapped_column(ForeignKey("document_chunks.id"), nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_section: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_authority: Mapped[str | None] = mapped_column(String(40), nullable=True)
    review_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    draft: Mapped[GPostDraft] = relationship(back_populates="mappings")
    evidence: Mapped[list["GPostMappingEvidence"]] = relationship(back_populates="mapping", cascade="all, delete-orphan")


class GPostMappingEvidence(Base):
    __tablename__ = "gpost_mapping_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    gpost_mapping_id: Mapped[int] = mapped_column(ForeignKey("gpost_mappings.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(40))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)
    document_chunk_id: Mapped[int | None] = mapped_column(ForeignKey("document_chunks.id"), nullable=True)
    reference_program_id: Mapped[int | None] = mapped_column(ForeignKey("reference_programs.id"), nullable=True)
    standard_convention_id: Mapped[int | None] = mapped_column(ForeignKey("standard_conventions.id"), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(300), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    authority_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    mapping: Mapped[GPostMapping] = relationship(back_populates="evidence")


class GPostPreviewRun(Base):
    __tablename__ = "gpost_preview_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    gpost_draft_id: Mapped[int] = mapped_column(ForeignKey("gpost_drafts.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    cl_file_hash: Mapped[str] = mapped_column(String(64))
    generated_gcode: Mapped[str] = mapped_column(Text, default="")
    parser_diagnostics_json: Mapped[list] = mapped_column(JSON, default=list)
    deterministic_findings_json: Mapped[list] = mapped_column(JSON, default=list)
    unsupported_commands_json: Mapped[list] = mapped_column(JSON, default=list)
    missing_mappings_json: Mapped[list] = mapped_column(JSON, default=list)
    warnings_json: Mapped[list] = mapped_column(JSON, default=list)
    traceability_json: Mapped[list] = mapped_column(JSON, default=list)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    parser_version: Mapped[str] = mapped_column(String(40), default="gcode-parser-v1")
    rule_set_version: Mapped[str] = mapped_column(String(40), default="validation-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    draft: Mapped[GPostDraft] = relationship(back_populates="preview_runs")

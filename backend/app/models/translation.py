from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.entities import utc_now


class TranslationExample(Base):
    __tablename__ = "translation_examples"
    __table_args__ = (
        UniqueConstraint("machine_profile_revision_id", "cl_source_hash", "gcode_source_hash", name="uq_translation_revision_pair_hash"),
        Index("ix_translation_machine_status", "machine_profile_id", "verification_status"),
        Index("ix_translation_ai_retrieval", "machine_profile_id", "verification_status", "ai_processing_allowed", "post_processor_revision", "operation_type"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"), index=True)
    machine_profile_revision_id: Mapped[int] = mapped_column(ForeignKey("machine_profile_revisions.id"), index=True)
    reference_program_id: Mapped[int | None] = mapped_column(ForeignKey("reference_programs.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    controller_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    controller_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    post_processor_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    post_processor_revision: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    operation_type: Mapped[str] = mapped_column(String(40), default="other", index=True)
    operation_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    cl_source_text: Mapped[str] = mapped_column(Text)
    cl_source_hash: Mapped[str] = mapped_column(String(64), index=True)
    cl_original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gcode_source_text: Mapped[str] = mapped_column(Text)
    gcode_source_hash: Mapped[str] = mapped_column(String(64), index=True)
    gcode_original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="candidate", index=True)
    part_identifier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    program_identifier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    project_identifier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tooling_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    setup_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    machine_context_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_system: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_repository: Mapped[str | None] = mapped_column(String(240), nullable=True)
    work_order_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    imported_by_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_provenance: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    cl_parse_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    gcode_parse_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    parsed_cl_records_json: Mapped[list] = mapped_column(JSON, default=list)
    parsed_gcode_blocks_json: Mapped[list] = mapped_column(JSON, default=list)
    validation_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_processing_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    alignments: Mapped[list["TranslationAlignment"]] = relationship(back_populates="example", cascade="all, delete-orphan")


class TranslationAlignment(Base):
    __tablename__ = "translation_alignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    translation_example_id: Mapped[int] = mapped_column(ForeignKey("translation_examples.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="proposed")
    algorithm_version: Mapped[str] = mapped_column(String(50), default="translation-alignment-v1")
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    example: Mapped[TranslationExample] = relationship(back_populates="alignments")
    links: Mapped[list["TranslationAlignmentLink"]] = relationship(back_populates="alignment", cascade="all, delete-orphan")


class TranslationAlignmentLink(Base):
    __tablename__ = "translation_alignment_links"
    __table_args__ = (Index("ix_translation_link_alignment_status", "alignment_id", "review_status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    alignment_id: Mapped[int] = mapped_column(ForeignKey("translation_alignments.id"), index=True)
    cl_record_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cl_record_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gcode_block_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gcode_block_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    link_type: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column(Float, default=0)
    review_status: Mapped[str] = mapped_column(String(30), default="proposed", index=True)
    match_reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    alignment: Mapped[TranslationAlignment] = relationship(back_populates="links")

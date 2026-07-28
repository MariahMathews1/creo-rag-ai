from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.entities import SourceDocument, utc_now


class MachineProfileRevision(Base):
    __tablename__ = "machine_profile_revisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"), index=True)
    revision_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    source_type: Mapped[str] = mapped_column(String(30), default="manual_entry")
    created_from_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    controller_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    controller_manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    controller_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    controller_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    machine_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    axis_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    x_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    x_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    z_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    z_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    a_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    a_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    b_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    b_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    c_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    c_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_spindle_rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_spindle_rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_feed_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    rapid_traverse_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    units: Mapped[str | None] = mapped_column(String(20), nullable=True)
    supported_work_offsets_json: Mapped[list] = mapped_column(JSON, default=list)
    approved_g_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    approved_m_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    restricted_commands_json: Mapped[list] = mapped_column(JSON, default=list)
    safe_start_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_change_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    program_end_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    machine_configuration_json: Mapped[dict] = mapped_column(JSON, default=dict)
    capabilities_json: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProfileExtractionRun(Base):
    __tablename__ = "profile_extraction_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"), index=True)
    target_revision_id: Mapped[int | None] = mapped_column(ForeignKey("machine_profile_revisions.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="processing")
    provider_name: Mapped[str] = mapped_column(String(50), default="mock")
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    extraction_schema_version: Mapped[str] = mapped_column(String(30), default="profile-v1")
    selected_document_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    detected_variants_json: Mapped[list] = mapped_column(JSON, default=list)
    selected_machine_variant: Mapped[str | None] = mapped_column(String(120), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposals: Mapped[list["ProfileFieldProposal"]] = relationship(back_populates="extraction_run", cascade="all, delete-orphan")


class ProfileFieldProposal(Base):
    __tablename__ = "profile_field_proposals"
    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_run_id: Mapped[int] = mapped_column(ForeignKey("profile_extraction_runs.id"), index=True)
    field_key: Mapped[str] = mapped_column(String(100), index=True)
    field_label: Mapped[str] = mapped_column(String(160))
    field_category: Mapped[str] = mapped_column(String(50), index=True)
    proposed_value_json: Mapped[object | None] = mapped_column(JSON, nullable=True)
    normalized_value_json: Mapped[object | None] = mapped_column(JSON, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    confidence_components_json: Mapped[dict] = mapped_column(JSON, default=dict)
    proposal_status: Mapped[str] = mapped_column(String(30), index=True)
    review_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    reviewed_value_json: Mapped[object | None] = mapped_column(JSON, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(50), default="deterministic_regex")
    requires_exact_machine_verification: Mapped[bool] = mapped_column(Boolean, default=False)
    safety_relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    interpretation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    variant_applicability_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extraction_run: Mapped[ProfileExtractionRun] = relationship(back_populates="proposals")
    evidence: Mapped[list["ProfileFieldEvidence"]] = relationship(back_populates="field_proposal", cascade="all, delete-orphan")


class ProfileFieldEvidence(Base):
    __tablename__ = "profile_field_evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    field_proposal_id: Mapped[int] = mapped_column(ForeignKey("profile_field_proposals.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"))
    document_chunk_id: Mapped[int] = mapped_column(ForeignKey("document_chunks.id"))
    citation_number: Mapped[int] = mapped_column(Integer)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    excerpt: Mapped[str] = mapped_column(Text)
    raw_value_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    normalized_value_json: Mapped[object | None] = mapped_column(JSON, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float)
    evidence_type: Mapped[str] = mapped_column(String(30), default="supporting")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    field_proposal: Mapped[ProfileFieldProposal] = relationship(back_populates="evidence")
    document: Mapped["SourceDocument"] = relationship()

    @property
    def document_title(self) -> str:
        return self.document.title

    @property
    def document_type(self) -> str:
        return self.document.document_type.value


class MachineProfileFieldSource(Base):
    __tablename__ = "machine_profile_field_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    machine_profile_revision_id: Mapped[int] = mapped_column(ForeignKey("machine_profile_revisions.id"), index=True)
    field_key: Mapped[str] = mapped_column(String(100))
    value_json: Mapped[object | None] = mapped_column(JSON, nullable=True)
    source_type: Mapped[str] = mapped_column(String(40))
    document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_chunk_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_field_proposal_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(30))
    reviewed_by: Mapped[str] = mapped_column(String(50), default="local_user")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

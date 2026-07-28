from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    """Return a UTC timestamp stored without timezone metadata for SQLite."""

    return datetime.now(UTC).replace(tzinfo=None)


class MachineType(StrEnum):
    MILL = "mill"
    LATHE = "lathe"
    MILL_TURN = "mill-turn"
    TURNING_CENTER = "turning_center"
    MACHINING_CENTER = "machining_center"
    VERTICAL_MILL = "vertical_mill"
    HORIZONTAL_MILL = "horizontal_mill"
    VERTICAL_LATHE = "vertical_lathe"
    OTHER = "other"


class DocumentType(StrEnum):
    CONTROLLER_MANUAL = "controller_manual"
    MACHINE_MANUAL = "machine_manual"
    PROGRAMMING_MANUAL = "programming_manual"
    COMPANY_STANDARD = "company_standard"
    APPROVED_PROGRAM = "approved_program"
    SETUP_DOCUMENT = "setup_document"
    POST_PROCESSOR_DOCUMENT = "post_processor_document"
    OPERATOR_MANUAL = "operator_manual"
    SPECIFICATION_DOCUMENT = "specification_document"
    MAINTENANCE_MANUAL = "maintenance_manual"
    PARAMETER_LIST = "parameter_list"
    MACHINE_CONFIGURATION_DOCUMENT = "machine_configuration_document"
    PURCHASE_SPECIFICATION = "purchase_specification"
    OTHER = "other"


class ProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class AnswerStatus(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FAILED = "failed"


class QuestionCategory(StrEnum):
    COMMAND_MEANING = "command_meaning"
    CYCLE_SUPPORT = "cycle_support"
    MACHINE_LIMIT = "machine_limit"
    SETUP_REQUIREMENT = "setup_requirement"
    TOOL_CHANGE = "tool_change"
    WORK_OFFSET = "work_offset"
    SPINDLE = "spindle"
    FEED = "feed"
    COOLANT = "coolant"
    ALARM = "alarm"
    POST_PROCESSOR = "post_processor"
    GENERAL = "general"


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    PASSED = "passed"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class Severity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFORMATIONAL = "informational"


class MachineProfile(Base):
    __tablename__ = "machine_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    manufacturer: Mapped[str] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(120))
    controller_name: Mapped[str] = mapped_column(String(120))
    controller_manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    controller_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    controller_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    machine_type: Mapped[MachineType] = mapped_column(Enum(MachineType))
    axis_count: Mapped[int] = mapped_column(Integer, default=3)
    x_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    x_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    z_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    z_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_spindle_rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_feed_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    rapid_z_review_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    supported_work_offsets: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_g_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_m_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    restricted_commands: Mapped[list[str]] = mapped_column(JSON, default=list)
    safe_start_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_change_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    program_end_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
    active_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    documents: Mapped[list["SourceDocument"]] = relationship(
        back_populates="machine_profile", cascade="all, delete-orphan"
    )
    projects: Mapped[list["AnalysisProject"]] = relationship(
        back_populates="machine_profile", cascade="all, delete-orphan"
    )


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"))
    title: Mapped[str] = mapped_column(String(200))
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType))
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    controller_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    controller_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stored_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), default=ProcessingStatus.UPLOADED
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_data: Mapped[list[dict]] = mapped_column(JSON, default=list)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    machine_profile: Mapped[MachineProfile] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"), index=True)
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    token_estimate: Mapped[int] = mapped_column(Integer)
    embedding_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    embedding_vector: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    document: Mapped[SourceDocument] = relationship(back_populates="chunks")


class ManualQuestionSession(Base):
    __tablename__ = "manual_question_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    questions: Mapped[list["ManualQuestion"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ManualQuestion(Base):
    __tablename__ = "manual_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("manual_question_sessions.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    category: Mapped[QuestionCategory] = mapped_column(
        Enum(QuestionCategory), default=QuestionCategory.GENERAL
    )
    answer: Mapped[str] = mapped_column(Text)
    answer_status: Mapped[AnswerStatus] = mapped_column(Enum(AnswerStatus))
    unresolved_questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_name: Mapped[str] = mapped_column(String(80))
    retrieval_debug: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    session: Mapped[ManualQuestionSession] = relationship(back_populates="questions")
    citations: Mapped[list["AnswerCitation"]] = relationship(
        back_populates="manual_question", cascade="all, delete-orphan"
    )


class AnswerCitation(Base):
    __tablename__ = "answer_citations"

    id: Mapped[int] = mapped_column(primary_key=True)
    manual_question_id: Mapped[int] = mapped_column(ForeignKey("manual_questions.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"))
    document_chunk_id: Mapped[int] = mapped_column(ForeignKey("document_chunks.id"))
    citation_number: Mapped[int] = mapped_column(Integer)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    excerpt: Mapped[str] = mapped_column(Text)
    relevance_score: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    manual_question: Mapped[ManualQuestion] = relationship(back_populates="citations")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    machine_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis_project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    manual_question_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class AnalysisProject(Base):
    __tablename__ = "analysis_projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"))
    cl_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    gcode_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    cl_original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gcode_original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cl_file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gcode_file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cl_processing_status: Mapped[str] = mapped_column(String(20), default="not_provided")
    gcode_processing_status: Mapped[str] = mapped_column(String(20), default="not_provided")
    alignment_status: Mapped[str] = mapped_column(String(20), default="not_started")
    alignment_version: Mapped[int] = mapped_column(Integer, default=0)
    alignment_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    machine_profile_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    machine_profile_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    machine_profile: Mapped[MachineProfile] = relationship(back_populates="projects")
    findings: Mapped[list["AnalysisFinding"]] = relationship(
        back_populates="analysis_project", cascade="all, delete-orphan"
    )
    cl_records: Mapped[list["CLRecord"]] = relationship(
        back_populates="analysis_project", cascade="all, delete-orphan"
    )
    gcode_blocks: Mapped[list["GCodeBlock"]] = relationship(
        back_populates="analysis_project", cascade="all, delete-orphan"
    )
    alignment_runs: Mapped[list["AlignmentRun"]] = relationship(
        back_populates="analysis_project", cascade="all, delete-orphan"
    )


class AnalysisFinding(Base):
    __tablename__ = "analysis_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_project_id: Mapped[int] = mapped_column(ForeignKey("analysis_projects.id"))
    severity: Mapped[Severity] = mapped_column(Enum(Severity))
    category: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_id: Mapped[str] = mapped_column(String(80), index=True)
    recommendation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    analysis_project: Mapped[AnalysisProject] = relationship(back_populates="findings")

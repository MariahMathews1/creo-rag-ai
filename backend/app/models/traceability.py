from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.entities import utc_now


class CLRecord(Base):
    __tablename__ = "cl_records"
    __table_args__ = (
        Index("ix_cl_project_record", "analysis_project_id", "record_index"),
        Index("ix_cl_project_line", "analysis_project_id", "line_number"),
        Index("ix_cl_project_command", "analysis_project_id", "command"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_project_id: Mapped[int] = mapped_column(ForeignKey("analysis_projects.id"))
    record_index: Mapped[int] = mapped_column(Integer)
    line_number: Mapped[int] = mapped_column(Integer)
    original_text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    command: Mapped[str] = mapped_column(String(40), index=True)
    original_command: Mapped[str | None] = mapped_column(String(80), nullable=True)
    parameters_json: Mapped[list] = mapped_column(JSON, default=list)
    numeric_parameters_json: Mapped[list] = mapped_column(JSON, default=list)
    named_parameters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    coordinates_json: Mapped[dict] = mapped_column(JSON, default=dict)
    motion_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tool_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spindle_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    feed_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    coolant_state: Mapped[str | None] = mapped_column(String(30), nullable=True)
    operation_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    state_before_json: Mapped[dict] = mapped_column(JSON, default=dict)
    state_after_json: Mapped[dict] = mapped_column(JSON, default=dict)
    parse_errors_json: Mapped[list] = mapped_column(JSON, default=list)
    parser_version: Mapped[str] = mapped_column(String(40), default="cl-parser-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    analysis_project: Mapped["AnalysisProject"] = relationship(back_populates="cl_records")


class GCodeBlock(Base):
    __tablename__ = "gcode_blocks"
    __table_args__ = (
        Index("ix_gcode_project_block", "analysis_project_id", "block_index"),
        Index("ix_gcode_project_line", "analysis_project_id", "line_number"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_project_id: Mapped[int] = mapped_column(ForeignKey("analysis_projects.id"))
    block_index: Mapped[int] = mapped_column(Integer)
    line_number: Mapped[int] = mapped_column(Integer)
    original_text: Mapped[str] = mapped_column(Text)
    cleaned_text: Mapped[str] = mapped_column(Text)
    sequence_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    program_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    g_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    m_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    coordinates_json: Mapped[dict] = mapped_column(JSON, default=dict)
    feed_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    spindle_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    tool_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_tool: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_offset: Mapped[str | None] = mapped_column(String(20), nullable=True)
    motion_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    state_before_json: Mapped[dict] = mapped_column(JSON, default=dict)
    state_after_json: Mapped[dict] = mapped_column(JSON, default=dict)
    parse_errors_json: Mapped[list] = mapped_column(JSON, default=list)
    parser_version: Mapped[str] = mapped_column(String(40), default="gcode-parser-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    analysis_project: Mapped["AnalysisProject"] = relationship(back_populates="gcode_blocks")


class AlignmentRun(Base):
    __tablename__ = "alignment_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_project_id: Mapped[int] = mapped_column(ForeignKey("analysis_projects.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="processing")
    algorithm_version: Mapped[str] = mapped_column(String(40), default="deterministic-v1")
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_integrity_json: Mapped[dict] = mapped_column(JSON, default=dict)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    analysis_project: Mapped["AnalysisProject"] = relationship(back_populates="alignment_runs")
    links: Mapped[list["AlignmentLink"]] = relationship(back_populates="alignment_run", cascade="all, delete-orphan")
    issues: Mapped[list["AlignmentIssue"]] = relationship(back_populates="alignment_run", cascade="all, delete-orphan")


class AlignmentLink(Base):
    __tablename__ = "alignment_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    alignment_run_id: Mapped[int] = mapped_column(ForeignKey("alignment_runs.id"), index=True)
    cl_record_id: Mapped[int | None] = mapped_column(ForeignKey("cl_records.id"), nullable=True, index=True)
    gcode_block_id: Mapped[int | None] = mapped_column(ForeignKey("gcode_blocks.id"), nullable=True, index=True)
    link_type: Mapped[str] = mapped_column(String(30), default="direct")
    confidence: Mapped[float] = mapped_column(Float)
    match_reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    mismatch_reasons_json: Mapped[list] = mapped_column(JSON, default=list)
    score_components_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assigned_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    alignment_run: Mapped[AlignmentRun] = relationship(back_populates="links")
    cl_record: Mapped[CLRecord | None] = relationship()
    gcode_block: Mapped[GCodeBlock | None] = relationship()


class AlignmentIssue(Base):
    __tablename__ = "alignment_issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    alignment_run_id: Mapped[int] = mapped_column(ForeignKey("alignment_runs.id"), index=True)
    issue_type: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    cl_record_id: Mapped[int | None] = mapped_column(ForeignKey("cl_records.id"), nullable=True)
    gcode_block_id: Mapped[int | None] = mapped_column(ForeignKey("gcode_blocks.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assigned_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    alignment_run: Mapped[AlignmentRun] = relationship(back_populates="issues")


from app.models.entities import AnalysisProject  # noqa: E402,F401

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.entities import utc_now


class AIInvocation(Base):
    __tablename__ = "ai_invocations"
    __table_args__ = (
        Index("ix_ai_invocation_machine_created", "machine_profile_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    operation_type: Mapped[str] = mapped_column(String(50), index=True)
    machine_profile_id: Mapped[int] = mapped_column(ForeignKey("machine_profiles.id"), index=True)
    machine_profile_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    translation_example_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    prompt_template_version: Mapped[str] = mapped_column(String(40))
    response_schema_version: Mapped[str] = mapped_column(String(40))
    response_status: Mapped[str] = mapped_column(String(50), index=True)
    external_processing: Mapped[bool] = mapped_column(Boolean, default=False)
    provider_metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    token_usage_json: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

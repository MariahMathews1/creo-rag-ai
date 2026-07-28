"""Phase 3 manual knowledge system.

Revision ID: 20260727_01
"""
from alembic import op
import sqlalchemy as sa

from app.db.base import Base
from app import models  # noqa: F401

revision = "20260727_01"
down_revision = None
branch_labels = None
depends_on = None


SOURCE_COLUMNS = {
    "manufacturer": sa.Column("manufacturer", sa.String(120), nullable=True),
    "controller_name": sa.Column("controller_name", sa.String(120), nullable=True),
    "controller_version": sa.Column("controller_version", sa.String(80), nullable=True),
    "stored_filename": sa.Column("stored_filename", sa.String(255), nullable=True),
    "mime_type": sa.Column("mime_type", sa.String(120), nullable=True),
    "file_size_bytes": sa.Column("file_size_bytes", sa.Integer(), nullable=True),
    "processing_status": sa.Column("processing_status", sa.String(10), nullable=True),
    "processing_error": sa.Column("processing_error", sa.Text(), nullable=True),
    "page_count": sa.Column("page_count", sa.Integer(), nullable=True),
    "page_data": sa.Column("page_data", sa.JSON(), nullable=True),
    "uploaded_at": sa.Column("uploaded_at", sa.DateTime(), nullable=True),
    "processed_at": sa.Column("processed_at", sa.DateTime(), nullable=True),
    "updated_at": sa.Column("updated_at", sa.DateTime(), nullable=True),
}


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("source_documents")}
    for name, column in SOURCE_COLUMNS.items():
        if name not in existing:
            op.add_column("source_documents", column)
    op.execute(
        "UPDATE source_documents SET processing_status='READY' "
        "WHERE processing_status IS NULL"
    )
    op.execute(
        "UPDATE source_documents SET page_data='[]' WHERE page_data IS NULL"
    )


def downgrade() -> None:
    for table in (
        "audit_events", "answer_citations", "manual_questions",
        "manual_question_sessions", "document_chunks",
    ):
        op.drop_table(table)


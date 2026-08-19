"""Phase 11 AI-assisted post section drafting.

Revision ID: 20260818_01
Revises: 20260814_01
"""
from alembic import op
import sqlalchemy as sa

from app.models.gpost import PostRuleDraft, PostSectionDraft

revision = "20260818_01"
down_revision = "20260814_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    source_columns = {column["name"] for column in inspector.get_columns("source_documents")}
    if "ai_post_builder_allowed" not in source_columns:
        op.add_column("source_documents", sa.Column("ai_post_builder_allowed", sa.Boolean(), nullable=False, server_default=sa.false()))
    source_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("source_documents")}
    if "ix_source_documents_ai_post_builder_allowed" not in source_indexes:
        op.create_index("ix_source_documents_ai_post_builder_allowed", "source_documents", ["ai_post_builder_allowed"])
    PostSectionDraft.__table__.create(bind=bind, checkfirst=True)
    PostRuleDraft.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    PostRuleDraft.__table__.drop(bind=bind, checkfirst=True)
    PostSectionDraft.__table__.drop(bind=bind, checkfirst=True)
    inspector = sa.inspect(bind)
    if "ix_source_documents_ai_post_builder_allowed" in {index["name"] for index in inspector.get_indexes("source_documents")}:
        op.drop_index("ix_source_documents_ai_post_builder_allowed", table_name="source_documents")
    if "ai_post_builder_allowed" in {column["name"] for column in sa.inspect(bind).get_columns("source_documents")}:
        op.drop_column("source_documents", "ai_post_builder_allowed")

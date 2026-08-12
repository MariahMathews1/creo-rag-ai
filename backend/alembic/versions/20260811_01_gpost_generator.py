"""Add the R&D-only G-POST Generator domain.

Revision ID: 20260811_01
Revises: 20260729_01
"""
from alembic import op

from app.db.base import Base
from app import models  # noqa: F401

revision = "20260811_01"
down_revision = "20260729_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    for table in (
        "gpost_preview_runs",
        "gpost_mapping_evidence",
        "gpost_mappings",
        "gpost_draft_versions",
        "gpost_drafts",
    ):
        op.drop_table(table)

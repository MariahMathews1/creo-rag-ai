"""Phase 6 approved-program standards and comparisons.

Revision ID: 20260729_01
Revises: 20260728_03
"""
from alembic import op

from app.db.base import Base
from app import models  # noqa: F401

revision = "20260729_01"
down_revision = "20260728_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    for table in (
        "program_comparison_findings",
        "program_comparison_runs",
        "standard_convention_evidence",
        "standard_conventions",
        "organizational_standard_profiles",
        "standard_extraction_runs",
        "reference_program_blocks",
        "reference_programs",
    ):
        op.drop_table(table)

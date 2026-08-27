"""Pre-Azure validation records, findings, policy, and diagnostics.

Revision ID: 20260819_04
Revises: 20260819_03
"""
from alembic import op
import sqlalchemy as sa

from app.models.gpost import GPostDiagnostic, ValidationFinding, ValidationPolicy

revision = "20260819_04"
down_revision = "20260819_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns("post_validation_records")}
    additions = (
        sa.Column("name", sa.String(180), nullable=True),
        sa.Column("attachment_reference", sa.String(500), nullable=True),
        sa.Column("external_tool", sa.String(100), nullable=True),
        sa.Column("external_reference", sa.String(500), nullable=True),
        sa.Column("test_program_name", sa.String(240), nullable=True),
        sa.Column("findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocking_findings_count", sa.Integer(), nullable=False, server_default="0"),
    )
    with op.batch_alter_table("post_validation_records") as batch:
        for column in additions:
            if column.name not in existing: batch.add_column(column)
    for model in (ValidationFinding, ValidationPolicy, GPostDiagnostic):
        model.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for model in (GPostDiagnostic, ValidationPolicy, ValidationFinding):
        model.__table__.drop(bind=bind, checkfirst=True)
    existing = {column["name"] for column in sa.inspect(bind).get_columns("post_validation_records")}
    with op.batch_alter_table("post_validation_records") as batch:
        for name in ("blocking_findings_count", "findings_count", "test_program_name", "external_reference",
                     "external_tool", "attachment_reference", "name"):
            if name in existing: batch.drop_column(name)

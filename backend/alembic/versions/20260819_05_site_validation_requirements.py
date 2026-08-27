"""Allow Site Standards to add validation gates.

Revision ID: 20260819_05
Revises: 20260819_04
"""
from alembic import op
import sqlalchemy as sa

revision = "20260819_05"
down_revision = "20260819_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("site_standards")}
    if "validation_requirements_json" not in columns:
        with op.batch_alter_table("site_standards") as batch:
            batch.add_column(sa.Column("validation_requirements_json", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("site_standards")}
    if "validation_requirements_json" in columns:
        with op.batch_alter_table("site_standards") as batch:
            batch.drop_column("validation_requirements_json")

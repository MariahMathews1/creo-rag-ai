"""Store units with manually entered Machine Information.

Revision ID: 20260827_03
Revises: 20260827_02
"""
from alembic import op
import sqlalchemy as sa

revision = "20260827_03"
down_revision = "20260827_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("machine_profile_field_sources")
    }
    if "unit" not in columns:
        with op.batch_alter_table("machine_profile_field_sources") as batch:
            batch.add_column(sa.Column("unit", sa.String(30), nullable=True))


def downgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("machine_profile_field_sources")
    }
    if "unit" in columns:
        with op.batch_alter_table("machine_profile_field_sources") as batch:
            batch.drop_column("unit")

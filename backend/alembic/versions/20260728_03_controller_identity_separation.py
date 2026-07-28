"""Separate controller manufacturer/model from the physical machine model.

Revision ID: 20260728_03
Revises: 20260728_02
"""
from alembic import op
import sqlalchemy as sa

revision = "20260728_03"
down_revision = "20260728_02"
branch_labels = None
depends_on = None


def _add_missing(table: str, columns: dict[str, sa.Column]) -> None:
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns(table)}
    for name, column in columns.items():
        if name not in existing:
            op.add_column(table, column)


def upgrade() -> None:
    controller_columns = {
        "controller_manufacturer": sa.Column(
            "controller_manufacturer", sa.String(length=120), nullable=True,
        ),
        "controller_model": sa.Column(
            "controller_model", sa.String(length=120), nullable=True,
        ),
    }
    _add_missing("machine_profiles", controller_columns)
    _add_missing("machine_profile_revisions", {
        "controller_manufacturer": sa.Column(
            "controller_manufacturer", sa.String(length=120), nullable=True,
        ),
        "controller_model": sa.Column(
            "controller_model", sa.String(length=120), nullable=True,
        ),
    })
    # Deliberately do not rewrite approved revisions whose model is "F".
    # A reviewed extraction draft can repair that identity explicitly.


def downgrade() -> None:
    with op.batch_alter_table("machine_profile_revisions") as batch:
        batch.drop_column("controller_model")
        batch.drop_column("controller_manufacturer")
    with op.batch_alter_table("machine_profiles") as batch:
        batch.drop_column("controller_model")
        batch.drop_column("controller_manufacturer")

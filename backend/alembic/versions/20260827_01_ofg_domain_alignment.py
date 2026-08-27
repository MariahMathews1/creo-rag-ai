"""Add machine-specific OFG checklist metadata.

Revision ID: 20260827_01
Revises: 20260819_05
"""
from alembic import op
import sqlalchemy as sa

revision = "20260827_01"
down_revision = "20260819_05"
branch_labels = None
depends_on = None


COLUMNS = (
    sa.Column("subsection", sa.String(120), nullable=True),
    sa.Column("relevance_class", sa.String(20), nullable=False, server_default="core"),
    sa.Column("relevance_label", sa.String(30), nullable=False, server_default="required_for_post"),
    sa.Column("is_applicable", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("user_selected", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("source_type", sa.String(50), nullable=False, server_default="Unknown"),
    sa.Column("source_reference", sa.String(500), nullable=True),
    sa.Column("structured_value_json", sa.JSON(), nullable=True),
    sa.Column("code_status", sa.String(30), nullable=True),
)


def upgrade() -> None:
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns("ofg_settings")}
    with op.batch_alter_table("ofg_settings") as batch:
        for column in COLUMNS:
            if column.name not in existing: batch.add_column(column)
        batch.alter_column("ofg_menu_path_status", existing_type=sa.String(20), type_=sa.String(40))
    # Old path status meant only that the application had no verified reference.
    op.execute(sa.text("UPDATE ofg_settings SET ofg_menu_path_status = 'not_verified' WHERE ofg_menu_path_status IN ('unverified', 'verified')"))


def downgrade() -> None:
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns("ofg_settings")}
    op.execute(sa.text("UPDATE ofg_settings SET ofg_menu_path_status = 'unverified' WHERE length(ofg_menu_path_status) > 20"))
    with op.batch_alter_table("ofg_settings") as batch:
        batch.alter_column("ofg_menu_path_status", existing_type=sa.String(40), type_=sa.String(20))
        for name in reversed([column.name for column in COLUMNS]):
            if name in existing: batch.drop_column(name)

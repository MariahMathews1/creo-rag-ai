"""Add Post input review state and OFG-linked custom logic.

Revision ID: 20260827_02
Revises: 20260827_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20260827_02"
down_revision = "20260827_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    fact_columns = {column["name"] for column in sa.inspect(bind).get_columns("machine_knowledge_facts")}
    if "post_review_status" not in fact_columns:
        with op.batch_alter_table("machine_knowledge_facts") as batch:
            batch.add_column(sa.Column("post_review_status", sa.String(30), nullable=False, server_default="available_from_machine"))
            batch.create_index("ix_machine_knowledge_facts_post_review_status", ["post_review_status"])
    logic_columns = {column["name"] for column in sa.inspect(bind).get_columns("custom_logic_items")}
    with op.batch_alter_table("custom_logic_items") as batch:
        if "related_ofg_setting_id" not in logic_columns:
            batch.add_column(sa.Column("related_ofg_setting_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_custom_logic_ofg_setting", "ofg_settings", ["related_ofg_setting_id"], ["id"])
            batch.create_index("ix_custom_logic_items_related_ofg_setting_id", ["related_ofg_setting_id"])
        if "desired_behavior" not in logic_columns: batch.add_column(sa.Column("desired_behavior", sa.Text(), nullable=True))
        if "runtime_trigger" not in logic_columns: batch.add_column(sa.Column("runtime_trigger", sa.String(300), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    logic_columns = {column["name"] for column in sa.inspect(bind).get_columns("custom_logic_items")}
    with op.batch_alter_table("custom_logic_items") as batch:
        if "runtime_trigger" in logic_columns: batch.drop_column("runtime_trigger")
        if "desired_behavior" in logic_columns: batch.drop_column("desired_behavior")
        if "related_ofg_setting_id" in logic_columns:
            batch.drop_index("ix_custom_logic_items_related_ofg_setting_id")
            batch.drop_column("related_ofg_setting_id")
    fact_columns = {column["name"] for column in sa.inspect(bind).get_columns("machine_knowledge_facts")}
    if "post_review_status" in fact_columns:
        with op.batch_alter_table("machine_knowledge_facts") as batch:
            batch.drop_index("ix_machine_knowledge_facts_post_review_status")
            batch.drop_column("post_review_status")

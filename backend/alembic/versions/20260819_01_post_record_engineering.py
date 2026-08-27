"""Post Record engineering system of record.

Revision ID: 20260819_01
Revises: 20260818_01
"""
from alembic import op
import sqlalchemy as sa

from app.models.gpost import (CustomLogicItem, MachineKnowledgeFact, OFGSetting, OpenQuestion,
    PostStandardApplication, PostValidationRecord, SiteStandard)

revision = "20260819_01"
down_revision = "20260818_01"
branch_labels = None
depends_on = None


TABLES = [MachineKnowledgeFact, OFGSetting, SiteStandard, PostStandardApplication,
          CustomLogicItem, OpenQuestion, PostValidationRecord]


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("post_rule_drafts")}
    if "engineering_classification" not in columns:
        op.add_column("post_rule_drafts", sa.Column("engineering_classification", sa.String(30),
            nullable=False, server_default="UNKNOWN"))
        op.create_index("ix_post_rule_drafts_engineering_classification", "post_rule_drafts", ["engineering_classification"])
    for model in TABLES:
        model.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for model in reversed(TABLES):
        model.__table__.drop(bind=bind, checkfirst=True)
    columns = {column["name"] for column in sa.inspect(bind).get_columns("post_rule_drafts")}
    if "engineering_classification" in columns:
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes("post_rule_drafts")}
        if "ix_post_rule_drafts_engineering_classification" in indexes:
            op.drop_index("ix_post_rule_drafts_engineering_classification", table_name="post_rule_drafts")
        op.drop_column("post_rule_drafts", "engineering_classification")

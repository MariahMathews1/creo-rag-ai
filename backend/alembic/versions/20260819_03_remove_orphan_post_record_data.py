"""Remove orphaned additive Post Record package rows.

Revision ID: 20260819_03
Revises: 20260819_02
"""
from alembic import op

revision = "20260819_03"
down_revision = "20260819_02"
branch_labels = None
depends_on = None

TABLES = (
    "post_open_questions", "ofg_settings", "machine_knowledge_facts",
    "post_standard_applications", "custom_logic_items", "post_validation_records",
)


def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        bind.exec_driver_sql(
            f"DELETE FROM {table} WHERE post_record_id NOT IN (SELECT id FROM gpost_drafts)"
        )


def downgrade() -> None:
    # Deleted orphan rows cannot be meaningfully recreated.
    pass

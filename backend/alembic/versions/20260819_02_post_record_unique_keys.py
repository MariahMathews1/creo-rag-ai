"""Make default Post Record engineering keys unique.

Revision ID: 20260819_02
Revises: 20260819_01
"""
from alembic import op

revision = "20260819_02"
down_revision = "20260819_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Retain the earliest canonical default row and remove only same-record/key copies.
    bind.exec_driver_sql("""
        DELETE FROM post_open_questions
        WHERE related_type = 'machine_fact'
          AND related_id IN (
            SELECT f.id FROM machine_knowledge_facts f
            WHERE f.id NOT IN (
              SELECT MIN(k.id) FROM machine_knowledge_facts k
              GROUP BY k.post_record_id, k.fact_key
            )
          )
    """)
    bind.exec_driver_sql("""
        DELETE FROM ofg_settings
        WHERE id NOT IN (
          SELECT MIN(id) FROM ofg_settings GROUP BY post_record_id, setting_key
        )
    """)
    bind.exec_driver_sql("""
        DELETE FROM machine_knowledge_facts
        WHERE id NOT IN (
          SELECT MIN(id) FROM machine_knowledge_facts GROUP BY post_record_id, fact_key
        )
    """)
    with op.batch_alter_table("machine_knowledge_facts") as batch:
        batch.create_unique_constraint("uq_machine_fact_record_key", ["post_record_id", "fact_key"])
    with op.batch_alter_table("ofg_settings") as batch:
        batch.create_unique_constraint("uq_ofg_setting_record_key", ["post_record_id", "setting_key"])


def downgrade() -> None:
    with op.batch_alter_table("ofg_settings") as batch:
        batch.drop_constraint("uq_ofg_setting_record_key", type_="unique")
    with op.batch_alter_table("machine_knowledge_facts") as batch:
        batch.drop_constraint("uq_machine_fact_record_key", type_="unique")

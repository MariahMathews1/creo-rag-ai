"""Add G-POST V1 template-reference and review semantics.

Revision ID: 20260812_01
Revises: 20260811_01
"""
import sqlalchemy as sa
from alembic import op

revision = "20260812_01"
down_revision = "20260811_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The preceding G-POST migration creates from current SQLAlchemy metadata,
    # so a brand-new database can already contain these columns. Existing V1
    # databases do not. Inspect first so both upgrade paths remain valid.
    inspector = sa.inspect(op.get_bind())
    draft_columns = {item["name"] for item in inspector.get_columns("gpost_drafts")}
    if "manual_configuration_acknowledged" not in draft_columns:
        with op.batch_alter_table("gpost_drafts") as batch:
            batch.add_column(sa.Column("manual_configuration_acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()))

    mapping_columns = {item["name"] for item in inspector.get_columns("gpost_mappings")}
    additions = (
        sa.Column("template_key", sa.String(length=100), nullable=True),
        sa.Column("template_override", sa.Text(), nullable=True),
        sa.Column("uses_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("support_status", sa.String(length=30), nullable=False, server_default="supported"),
        sa.Column("required_for_v1", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.String(length=240), nullable=True),
    )
    missing_columns = [column for column in additions if column.name not in mapping_columns]
    if missing_columns:
        with op.batch_alter_table("gpost_mappings") as batch:
            for column in missing_columns:
                batch.add_column(column)

    inspector = sa.inspect(op.get_bind())
    mapping_indexes = {item["name"] for item in inspector.get_indexes("gpost_mappings")}
    with op.batch_alter_table("gpost_mappings") as batch:
        for index_name, column_name in (
            ("ix_gpost_mappings_template_key", "template_key"),
            ("ix_gpost_mappings_support_status", "support_status"),
            ("ix_gpost_mappings_required_for_v1", "required_for_v1"),
        ):
            if index_name not in mapping_indexes:
                batch.create_index(index_name, [column_name])

    # Backfill V1 semantics for drafts created before this migration. Preserve
    # legacy output text as a fallback while moving known mappings to references.
    connection = op.get_bind()
    template_by_key = {
        "loadtl": ("tool_change", "Tool selection / load"),
        "fedrat": ("feed_rate", "Feed rate command"),
        "rapid": ("rapid_move", "Enable rapid positioning"),
        "goto": ("linear_feed_move", "Positioning / cutting move"),
        "fini": ("program_end", "End of CL program"),
        "pprint": ("comment", "Program comment"),
    }
    for mapping_key, (template_key, description) in template_by_key.items():
        connection.execute(sa.text("""
            UPDATE gpost_mappings SET template_key=:template_key, description=:description,
              required_for_v1=:required, support_status='supported'
            WHERE mapping_key=:mapping_key
        """), {"template_key": template_key, "description": description,
                 "required": mapping_key in {"loadtl", "fedrat", "rapid", "goto", "fini"}, "mapping_key": mapping_key})
    connection.execute(sa.text("""
        UPDATE gpost_mappings SET mapping_key='spindl_cw', template_key='spindle_start_cw',
          description='Clockwise spindle start', required_for_v1=1,
          conditions_json='{"direction":"CLW","category":"Spindle"}', support_status='supported'
        WHERE mapping_key='spindl'
    """))
    connection.execute(sa.text("""
        UPDATE gpost_mappings SET mapping_key='coolnt_on', template_key='coolant_on',
          description='Coolant on', required_for_v1=1,
          conditions_json='{"mode":"ON","category":"Coolant"}', support_status='supported'
        WHERE mapping_key='coolnt'
    """))
    connection.execute(sa.text("""
        UPDATE gpost_mappings SET support_status=CASE WHEN cl_command IN ('MULTAX','TLAXIS')
          THEN 'not_applicable' ELSE 'not_implemented' END, required_for_v1=0,
          description=CASE cl_command WHEN 'MULTAX' THEN 'Multiaxis mode'
            WHEN 'TLAXIS' THEN 'Tool-axis orientation' ELSE 'Advanced CL behavior' END
        WHERE supported=0 OR mapping_type='unsupported'
    """))
    # Split the two legacy multi-behavior mappings without deleting stored data.
    for key, template_key, description, conditions in (
        ("spindl_ccw", "spindle_start_ccw", "Counter-clockwise spindle start", '{"direction":"CCLW","category":"Spindle"}'),
        ("spindl_off", "spindle_stop", "Spindle stop", '{"direction":"OFF","category":"Spindle"}'),
        ("coolnt_off", "coolant_off", "Coolant off", '{"mode":"OFF","category":"Coolant"}'),
    ):
        source_key = "spindl_cw" if key.startswith("spindl") else "coolnt_on"
        connection.execute(sa.text("""
            INSERT INTO gpost_mappings (
              gpost_draft_id, mapping_key, cl_command, mapping_type, output_template,
              template_key, template_override, uses_override, support_status, required_for_v1,
              description, conditions_json, required_state_json, resulting_state_json,
              machine_type_scope, dialect_scope, supported, confidence, source_type,
              source_document_id, source_chunk_id, source_page, source_section, source_excerpt,
              source_authority, review_status, review_note, created_at, updated_at
            )
            SELECT gpost_draft_id, :key, cl_command, 'conditional', NULL,
              :template_key, NULL, 0, 'supported', 1, :description, :conditions,
              required_state_json, resulting_state_json, machine_type_scope, dialect_scope,
              1, confidence, source_type, source_document_id, source_chunk_id, source_page,
              source_section, source_excerpt, source_authority, 'pending', NULL, created_at, updated_at
            FROM gpost_mappings source
            WHERE source.mapping_key=:source_key AND NOT EXISTS (
              SELECT 1 FROM gpost_mappings existing
              WHERE existing.gpost_draft_id=source.gpost_draft_id AND existing.mapping_key=:key
            )
        """), {"key": key, "template_key": template_key, "description": description,
                 "conditions": conditions, "source_key": source_key})


def downgrade() -> None:
    with op.batch_alter_table("gpost_mappings") as batch:
        batch.drop_index("ix_gpost_mappings_required_for_v1")
        batch.drop_index("ix_gpost_mappings_support_status")
        batch.drop_index("ix_gpost_mappings_template_key")
        for column in ("description", "required_for_v1", "support_status", "uses_override", "template_override", "template_key"):
            batch.drop_column(column)
    with op.batch_alter_table("gpost_drafts") as batch:
        batch.drop_column("manual_configuration_acknowledged")

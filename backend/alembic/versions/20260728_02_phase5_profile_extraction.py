"""Phase 5 profile extraction and revision history.

Revision ID: 20260728_02
Revises: 20260728_01
"""
from alembic import op
import json
import sqlalchemy as sa

from app.db.base import Base
from app import models  # noqa: F401

revision = "20260728_02"
down_revision = "20260728_01"
branch_labels = None
depends_on = None


def _add_missing(table: str, columns: dict[str, sa.Column]) -> None:
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns(table)}
    for name, column in columns.items():
        if name not in existing:
            op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()
    _add_missing("machine_profiles", {
        "active_revision_id": sa.Column("active_revision_id", sa.Integer(), nullable=True),
        "archived_at": sa.Column("archived_at", sa.DateTime(), nullable=True),
    })
    _add_missing("analysis_projects", {
        "machine_profile_revision_id": sa.Column("machine_profile_revision_id", sa.Integer(), nullable=True),
        "machine_profile_snapshot_json": sa.Column("machine_profile_snapshot_json", sa.JSON(), nullable=True),
    })
    Base.metadata.create_all(bind=bind)
    op.execute("""
        INSERT INTO machine_profile_revisions (
          machine_profile_id, revision_number, status, source_type, name,
          manufacturer, model, controller_name, controller_version, machine_type,
          axis_count, x_min, x_max, y_min, y_max, z_min, z_max,
          max_spindle_rpm, max_feed_rate, supported_work_offsets_json,
          approved_g_codes_json, approved_m_codes_json, restricted_commands_json,
          safe_start_template, tool_change_template, program_end_template, notes,
          machine_configuration_json, capabilities_json, review_summary,
          created_at, updated_at, approved_at
        )
        SELECT mp.id, 1, 'approved', 'imported', mp.name, mp.manufacturer, mp.model,
          mp.controller_name, mp.controller_version, mp.machine_type, mp.axis_count,
          mp.x_min, mp.x_max, mp.y_min, mp.y_max, mp.z_min, mp.z_max,
          mp.max_spindle_rpm, mp.max_feed_rate, mp.supported_work_offsets,
          mp.approved_g_codes, mp.approved_m_codes, mp.restricted_commands,
          mp.safe_start_template, mp.tool_change_template, mp.program_end_template,
          mp.notes, '{}', '{}',
          'Initial approved compatibility revision created by Phase 5 migration.',
          mp.created_at, mp.updated_at, mp.updated_at
        FROM machine_profiles mp
        WHERE NOT EXISTS (
          SELECT 1 FROM machine_profile_revisions r WHERE r.machine_profile_id=mp.id
        )
    """)
    op.execute("""
        UPDATE machine_profiles SET active_revision_id=(
          SELECT id FROM machine_profile_revisions r
          WHERE r.machine_profile_id=machine_profiles.id
          ORDER BY revision_number DESC LIMIT 1
        ) WHERE active_revision_id IS NULL
    """)
    op.execute("""
        UPDATE analysis_projects SET machine_profile_revision_id=(
          SELECT active_revision_id FROM machine_profiles mp
          WHERE mp.id=analysis_projects.machine_profile_id
        ) WHERE machine_profile_revision_id IS NULL
    """)
    revision_rows = bind.execute(sa.text("""
        SELECT ap.id AS project_id, r.*
        FROM analysis_projects ap
        JOIN machine_profile_revisions r ON r.id=ap.machine_profile_revision_id
        WHERE ap.machine_profile_snapshot_json IS NULL
           OR ap.machine_profile_snapshot_json='{}'
    """)).mappings()
    snapshot_keys = (
        "id", "revision_number", "manufacturer", "model", "controller_name",
        "controller_version", "machine_type", "axis_count", "x_min", "x_max",
        "y_min", "y_max", "z_min", "z_max", "max_spindle_rpm",
        "max_feed_rate", "rapid_traverse_rate", "supported_work_offsets_json",
        "approved_g_codes_json", "approved_m_codes_json",
        "restricted_commands_json", "safe_start_template",
        "tool_change_template", "program_end_template",
    )
    for row in revision_rows:
        snapshot = {key: row[key] for key in snapshot_keys}
        snapshot["rapid_z_review_threshold"] = None
        bind.execute(
            sa.text("""
                UPDATE analysis_projects
                SET machine_profile_snapshot_json=:snapshot
                WHERE id=:project_id
            """),
            {"snapshot": json.dumps(snapshot), "project_id": row["project_id"]},
        )


def downgrade() -> None:
    for table in (
        "machine_profile_field_sources", "profile_field_evidence",
        "profile_field_proposals", "profile_extraction_runs",
        "machine_profile_revisions",
    ):
        op.drop_table(table)

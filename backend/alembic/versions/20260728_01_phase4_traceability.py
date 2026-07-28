"""Phase 4 CL/G-code traceability.

Revision ID: 20260728_01
Revises: 20260727_01
"""
from alembic import op
import sqlalchemy as sa

from app.db.base import Base
from app import models  # noqa: F401

revision = "20260728_01"
down_revision = "20260727_01"
branch_labels = None
depends_on = None

PROJECT_COLUMNS = {
    "cl_original_filename": sa.Column("cl_original_filename", sa.String(255), nullable=True),
    "gcode_original_filename": sa.Column("gcode_original_filename", sa.String(255), nullable=True),
    "cl_file_hash": sa.Column("cl_file_hash", sa.String(64), nullable=True),
    "gcode_file_hash": sa.Column("gcode_file_hash", sa.String(64), nullable=True),
    "cl_processing_status": sa.Column("cl_processing_status", sa.String(20), nullable=True),
    "gcode_processing_status": sa.Column("gcode_processing_status", sa.String(20), nullable=True),
    "alignment_status": sa.Column("alignment_status", sa.String(20), nullable=True),
    "alignment_version": sa.Column("alignment_version", sa.Integer(), nullable=True),
    "alignment_summary_json": sa.Column("alignment_summary_json", sa.JSON(), nullable=True),
    "last_analyzed_at": sa.Column("last_analyzed_at", sa.DateTime(), nullable=True),
}


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    existing = {column["name"] for column in sa.inspect(bind).get_columns("analysis_projects")}
    for name, column in PROJECT_COLUMNS.items():
        if name not in existing:
            op.add_column("analysis_projects", column)
    op.execute("UPDATE analysis_projects SET cl_processing_status=CASE WHEN cl_source IS NULL THEN 'not_provided' ELSE 'pending' END WHERE cl_processing_status IS NULL")
    op.execute("UPDATE analysis_projects SET gcode_processing_status=CASE WHEN gcode_source IS NULL THEN 'not_provided' ELSE 'pending' END WHERE gcode_processing_status IS NULL")
    op.execute("UPDATE analysis_projects SET alignment_status='not_started' WHERE alignment_status IS NULL")
    op.execute("UPDATE analysis_projects SET alignment_version=0 WHERE alignment_version IS NULL")
    op.execute("UPDATE analysis_projects SET alignment_summary_json='{}' WHERE alignment_summary_json IS NULL")


def downgrade() -> None:
    for table in ("alignment_issues", "alignment_links", "alignment_runs", "gcode_blocks", "cl_records"):
        op.drop_table(table)

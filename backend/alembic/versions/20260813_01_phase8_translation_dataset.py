"""Phase 8 verified CL/G-code translation dataset.

Revision ID: 20260813_01
Revises: 20260812_02
"""
from alembic import op
from app.models.translation import TranslationAlignment, TranslationAlignmentLink, TranslationExample

revision = "20260813_01"
down_revision = "20260812_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    TranslationExample.__table__.create(bind=bind, checkfirst=True)
    TranslationAlignment.__table__.create(bind=bind, checkfirst=True)
    TranslationAlignmentLink.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    TranslationAlignmentLink.__table__.drop(bind=bind, checkfirst=True)
    TranslationAlignment.__table__.drop(bind=bind, checkfirst=True)
    TranslationExample.__table__.drop(bind=bind, checkfirst=True)

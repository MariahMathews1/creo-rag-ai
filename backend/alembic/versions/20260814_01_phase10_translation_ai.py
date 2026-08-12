"""Phase 10 controlled translation AI invocation audit.

Revision ID: 20260814_01
Revises: 20260813_01
"""
from alembic import op

from app.models.translation import TranslationExample
from app.models.translation_ai import AIInvocation

revision = "20260814_01"
down_revision = "20260813_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    AIInvocation.__table__.create(bind=bind, checkfirst=True)
    next(index for index in TranslationExample.__table__.indexes if index.name == "ix_translation_ai_retrieval").create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    next(index for index in TranslationExample.__table__.indexes if index.name == "ix_translation_ai_retrieval").drop(bind=bind, checkfirst=True)
    AIInvocation.__table__.drop(bind=bind, checkfirst=True)

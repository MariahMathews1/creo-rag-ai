from alembic import command
from alembic.config import Config

from app.core.config import PROJECT_ROOT, get_settings


def upgrade_database() -> None:
    """Upgrade the configured database to the repository migration head."""

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", get_settings().resolved_database_url)
    command.upgrade(config, "head")

"""Small development-only compatibility migrations.

The proof of concept intentionally avoids a migration framework for now, but
existing local databases still need additive schema changes to remain usable.
"""

from sqlalchemy import Engine, inspect, text


def apply_development_migrations(engine: Engine) -> None:
    """Apply safe, idempotent SQLite changes after ORM table creation."""

    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    if "machine_profiles" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("machine_profiles")}
        if "rapid_z_review_threshold" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE machine_profiles "
                        "ADD COLUMN rapid_z_review_threshold FLOAT"
                    )
                )
    if "analysis_projects" in inspector.get_table_names():
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE analysis_projects SET status = 'PASSED' "
                    "WHERE status = 'ANALYZED'"
                )
            )
            connection.execute(
                text(
                    "UPDATE analysis_projects SET status = 'REVIEW_REQUIRED' "
                    "WHERE status = 'NEEDS_REVIEW'"
                )
            )

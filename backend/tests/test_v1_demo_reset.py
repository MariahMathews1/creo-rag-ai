import pytest

from app.models.entities import MachineProfile, MachineType
from app.scripts.reset_v1_demo import archive_legacy_demo_rows, assert_safe_reset


def machine(name: str) -> MachineProfile:
    return MachineProfile(
        name=name,
        manufacturer="Test",
        model="T-1",
        controller_name="Test Controller",
        machine_type=MachineType.LATHE,
        axis_count=2,
    )


def test_reset_refuses_production_and_non_sqlite_without_override():
    with pytest.raises(RuntimeError, match="APP_ENVIRONMENT"):
        assert_safe_reset("production", "sqlite:///production.db")
    with pytest.raises(RuntimeError, match="non-SQLite"):
        assert_safe_reset("development", "postgresql://example/prod")
    assert_safe_reset("production", "postgresql://example/prod", True)


def test_reset_archives_only_known_legacy_demo_machines(db_session):
    real = machine("Plant 4 Production Lathe")
    legacy = machine("Fictional Phase 11 Post Builder Demo")
    canonical = machine("KLS-1840N V1 Demo")
    db_session.add_all([real, legacy, canonical])
    db_session.commit()

    archived, _ = archive_legacy_demo_rows(db_session)
    db_session.refresh(real)
    db_session.refresh(legacy)
    db_session.refresh(canonical)

    assert archived == [legacy.name]
    assert legacy.archived_at is not None
    assert real.archived_at is None
    assert canonical.archived_at is None

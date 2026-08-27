"""Safely restore the single fictional V1 walkthrough without touching user data."""
from __future__ import annotations

import argparse

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.entities import MachineProfile, utc_now
from app.models.gpost import GPostDraft
from app.scripts import seed_v1_demo


SAFE_ENVIRONMENTS = {"development", "demo", "local", "test"}
PRIMARY_MACHINE_NAMES = set(seed_v1_demo.MACHINE_ALIASES)
LEGACY_DEMO_MARKERS = (
    "Fictional VMC-850 Manual Demo",
    "Fictional Phase 11 Post Builder Demo",
    "Fictional KLS-1840N Approved Program Demo",
    "Fictional LT-200 Profile Extraction Demo",
    "Fictional KLS Phase 8 Translation Demo",
    "QA-3X",
    "Phase 2 Verification",
)


def assert_safe_reset(environment: str, database_url: str, allow_non_development_database: bool = False) -> None:
    """Refuse ambiguous or production-like targets unless the operator explicitly overrides."""
    normalized = environment.strip().lower()
    if normalized not in SAFE_ENVIRONMENTS and not allow_non_development_database:
        raise RuntimeError(
            f"Refusing demo reset in APP_ENVIRONMENT={environment!r}. "
            "Use --allow-non-development-database only after verifying the target."
        )
    if not database_url.startswith("sqlite") and not allow_non_development_database:
        raise RuntimeError(
            "Refusing demo reset for a non-SQLite database. "
            "Use --allow-non-development-database only after verifying the target."
        )


def archive_legacy_demo_rows(db: Session) -> tuple[list[str], list[str]]:
    """Archive only rows whose names match the project's known disposable demo fixtures."""
    machine_filters = [MachineProfile.name.ilike(f"%{marker}%") for marker in LEGACY_DEMO_MARKERS]
    legacy_machines = list(db.scalars(select(MachineProfile).where(or_(*machine_filters))))
    legacy_machine_ids = [machine.id for machine in legacy_machines if machine.name not in PRIMARY_MACHINE_NAMES]
    archived_machines: list[str] = []
    for machine in legacy_machines:
        if machine.name in PRIMARY_MACHINE_NAMES:
            continue
        if machine.archived_at is not None:
            continue
        machine.archived_at = utc_now()
        archived_machines.append(machine.name)

    draft_filters = [GPostDraft.name.ilike(f"%{marker}%") for marker in LEGACY_DEMO_MARKERS]
    if legacy_machine_ids:
        draft_filters.append(GPostDraft.machine_profile_id.in_(legacy_machine_ids))
    archived_drafts: list[str] = []
    for draft in db.scalars(select(GPostDraft).where(or_(*draft_filters))):
        if draft.status == "archived":
            continue
        draft.status = "archived"
        draft.superseded_at = draft.superseded_at or utc_now()
        archived_drafts.append(draft.name)
    db.commit()
    return archived_machines, archived_drafts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-non-development-database",
        action="store_true",
        help="Explicitly override the environment/SQLite guard after verifying the target.",
    )
    args = parser.parse_args()
    settings = get_settings()
    assert_safe_reset(
        settings.app_environment,
        settings.resolved_database_url,
        args.allow_non_development_database,
    )

    print(f"Demo reset target: {settings.resolved_database_url}")
    print(f"Environment: {settings.app_environment}")
    print("Action: archive known disposable legacy demos, then restore the canonical KLS walkthrough.")
    print("User-created machines, documents, Post Records, and schema are retained.")
    with SessionLocal() as db:
        machines, drafts = archive_legacy_demo_rows(db)
    print(f"Archived legacy demo machines: {len(machines)}")
    print(f"Archived legacy demo Post Records: {len(drafts)}")
    seed_v1_demo.main()


if __name__ == "__main__":
    main()

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import MachineProfile
from app.schemas.machine_profile import (
    MachineProfileCreate,
    MachineProfileRead,
    MachineProfileUpdate,
)

router = APIRouter(prefix="/machines", tags=["machine profiles"])


def _get_or_404(profile_id: int, db: Session) -> MachineProfile:
    profile = db.get(MachineProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Machine profile not found")
    return profile


@router.post("", response_model=MachineProfileRead, status_code=status.HTTP_201_CREATED)
def create_machine_profile(payload: MachineProfileCreate, db: Session = Depends(get_db)):
    profile = MachineProfile(**payload.model_dump())
    db.add(profile)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A machine profile with this name already exists"
        ) from exc
    db.refresh(profile)
    from app.api.profile_extraction import ensure_initial_revision
    ensure_initial_revision(profile, db)
    db.commit()
    return profile


@router.get("", response_model=list[MachineProfileRead])
def list_machine_profiles(db: Session = Depends(get_db)):
    return db.scalars(select(MachineProfile).order_by(MachineProfile.name)).all()


@router.get("/{profile_id}", response_model=MachineProfileRead)
def get_machine_profile(profile_id: int, db: Session = Depends(get_db)):
    return _get_or_404(profile_id, db)


def _apply_update(
    profile_id: int,
    payload: MachineProfileCreate | MachineProfileUpdate,
    db: Session,
) -> MachineProfile:
    profile = _get_or_404(profile_id, db)
    changes = payload.model_dump(exclude_unset=True)
    merged = MachineProfileRead.model_validate(profile).model_dump()
    merged.update(changes)
    # Reuse the complete create schema to validate range relationships after a partial update.
    MachineProfileCreate.model_validate(merged)
    for field, value in changes.items():
        setattr(profile, field, value)
    if changes:
        from app.models.program_standards import (
            OrganizationalStandardProfile, ProgramComparisonRun,
        )
        from sqlalchemy import update
        standards = list(db.scalars(select(
            OrganizationalStandardProfile.id
        ).where(
            OrganizationalStandardProfile.machine_profile_id == profile.id
        )))
        db.execute(update(OrganizationalStandardProfile).where(
            OrganizationalStandardProfile.machine_profile_id == profile.id
        ).values(
            stale=True,
            stale_reasons_json=["Machine profile changed"],
        ))
        if standards:
            db.execute(update(ProgramComparisonRun).where(
                ProgramComparisonRun.standard_profile_id.in_(standards)
            ).values(
                stale=True,
                stale_reasons_json=["Machine profile changed"],
            ))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A machine profile with this name already exists"
        ) from exc
    db.refresh(profile)
    return profile


@router.put("/{profile_id}", response_model=MachineProfileRead)
def replace_machine_profile(
    profile_id: int, payload: MachineProfileCreate, db: Session = Depends(get_db)
):
    """Replace a machine profile using the same validation as creation."""

    return _apply_update(profile_id, payload, db)


@router.patch("/{profile_id}", response_model=MachineProfileRead, include_in_schema=False)
def patch_machine_profile(
    profile_id: int, payload: MachineProfileUpdate, db: Session = Depends(get_db)
):
    """Compatibility partial update for early proof-of-concept clients."""

    return _apply_update(profile_id, payload, db)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = _get_or_404(profile_id, db)
    db.delete(profile)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

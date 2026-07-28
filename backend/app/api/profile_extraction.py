from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import (
    AuditEvent, DocumentType, MachineProfile, ProcessingStatus, SourceDocument, utc_now,
)
from app.models.profile_extraction import (
    MachineProfileFieldSource, MachineProfileRevision, ProfileExtractionRun,
    ProfileFieldProposal,
)
from app.profile_extraction.registry import FIELD_MAP
from app.profile_extraction.service import execute_extraction
from app.profile_extraction.units import UNIT_ALIASES, normalize_unit
from app.schemas.profile_extraction import (
    ApplyDraftRequest, ApprovalRequest, ExtractionRunRead, ExtractionStart,
    ProposalRead, ProposalReview, RejectionRequest, RevisionRead,
)

router = APIRouter(tags=["profile extraction"])
REVISION_FIELDS = {
    "manufacturer", "model", "controller_name", "controller_manufacturer",
    "controller_model", "controller_version", "machine_type",
    "axis_count", "x_min", "x_max", "y_min", "y_max", "z_min", "z_max",
    "min_spindle_rpm", "max_spindle_rpm", "max_feed_rate", "rapid_traverse_rate",
    "safe_start_template", "tool_change_template", "program_end_template",
}
SUPPORTED_EXTRACTION_DOCUMENT_TYPES = {
    DocumentType.CONTROLLER_MANUAL, DocumentType.MACHINE_MANUAL,
    DocumentType.PROGRAMMING_MANUAL, DocumentType.COMPANY_STANDARD,
    DocumentType.APPROVED_PROGRAM, DocumentType.SETUP_DOCUMENT,
    DocumentType.POST_PROCESSOR_DOCUMENT, DocumentType.OPERATOR_MANUAL,
    DocumentType.SPECIFICATION_DOCUMENT, DocumentType.MAINTENANCE_MANUAL,
    DocumentType.PARAMETER_LIST, DocumentType.MACHINE_CONFIGURATION_DOCUMENT,
    DocumentType.PURCHASE_SPECIFICATION,
}


def machine_or_404(machine_id: int, db: Session) -> MachineProfile:
    value = db.get(MachineProfile, machine_id)
    if not value: raise HTTPException(404, "Machine profile not found")
    return value


def ensure_initial_revision(machine: MachineProfile, db: Session) -> MachineProfileRevision:
    if machine.active_revision_id:
        value = db.get(MachineProfileRevision, machine.active_revision_id)
        if value: return value
    existing = db.scalar(select(MachineProfileRevision).where(
        MachineProfileRevision.machine_profile_id == machine.id,
        MachineProfileRevision.status == "approved",
    ).order_by(MachineProfileRevision.revision_number.desc()))
    if existing:
        machine.active_revision_id = existing.id; db.flush(); return existing
    revision = MachineProfileRevision(
        machine_profile_id=machine.id, revision_number=1, status="approved",
        source_type="imported", name=machine.name, manufacturer=machine.manufacturer,
        model=machine.model, controller_name=machine.controller_name,
        controller_manufacturer=machine.controller_manufacturer,
        controller_model=machine.controller_model,
        controller_version=machine.controller_version, machine_type=machine.machine_type.value,
        axis_count=machine.axis_count, x_min=machine.x_min, x_max=machine.x_max,
        y_min=machine.y_min, y_max=machine.y_max, z_min=machine.z_min, z_max=machine.z_max,
        max_spindle_rpm=machine.max_spindle_rpm, max_feed_rate=machine.max_feed_rate,
        supported_work_offsets_json=machine.supported_work_offsets,
        approved_g_codes_json=machine.approved_g_codes,
        approved_m_codes_json=machine.approved_m_codes,
        restricted_commands_json=machine.restricted_commands,
        safe_start_template=machine.safe_start_template,
        tool_change_template=machine.tool_change_template,
        program_end_template=machine.program_end_template, notes=machine.notes,
        review_summary="Initial compatibility revision migrated from the existing profile.",
        approved_at=utc_now(),
    )
    db.add(revision); db.flush(); machine.active_revision_id = revision.id; db.flush()
    return revision


@router.post("/machines/{machine_id}/profile-extraction-runs", response_model=ExtractionRunRead)
def start_extraction(machine_id: int, payload: ExtractionStart, db: Session = Depends(get_db)):
    machine = machine_or_404(machine_id, db)
    documents = list(db.scalars(select(SourceDocument).where(
        SourceDocument.id.in_(payload.document_ids)
    )))
    if len(documents) != len(set(payload.document_ids)):
        raise HTTPException(422, "One or more selected documents do not exist")
    if any(document.machine_profile_id != machine.id for document in documents):
        raise HTTPException(422, "Every selected document must belong to this machine")
    if any(document.processing_status != ProcessingStatus.READY for document in documents):
        raise HTTPException(422, "Every selected document must be processed and ready")
    if not any(document.document_type in SUPPORTED_EXTRACTION_DOCUMENT_TYPES for document in documents):
        raise HTTPException(422, "At least one supported document type must be selected")
    active = ensure_initial_revision(machine, db)
    running = db.scalar(select(ProfileExtractionRun).where(
        ProfileExtractionRun.machine_profile_id == machine.id,
        ProfileExtractionRun.target_revision_id == active.id,
        ProfileExtractionRun.status.in_(("pending", "processing")),
    ))
    if running:
        raise HTTPException(409, "An extraction is already running for the active revision")
    run = ProfileExtractionRun(
        machine_profile_id=machine.id, target_revision_id=active.id, status="processing",
        provider_name=get_settings().profile_extraction_provider,
        model_name=get_settings().profile_extraction_model or None,
        selected_document_ids_json=list(dict.fromkeys(payload.document_ids)),
        selected_machine_variant=payload.selected_machine_variant,
        settings_json={"target_machine_type": payload.target_machine_type,
                       "field_categories": payload.field_categories,
                       "active_revision_id": active.id},
    )
    db.add(run)
    db.add(AuditEvent(event_type="profile_extraction_started",
                      machine_profile_id=machine.id,
                      metadata_json={"document_ids": payload.document_ids}))
    db.commit(); db.refresh(run)
    try:
        execute_extraction(run, db, get_settings())
    except Exception as exc:
        run.status = "failed"; run.failure_message = str(exc)[:500]; db.commit()
        db.add(AuditEvent(event_type="profile_extraction_failed",
                          machine_profile_id=machine.id,
                          metadata_json={"run_id": run.id}))
        db.commit()
    db.refresh(run); return run


@router.get("/machines/{machine_id}/profile-extraction-runs", response_model=list[ExtractionRunRead])
def list_runs(machine_id: int, db: Session = Depends(get_db)):
    machine_or_404(machine_id, db)
    return db.scalars(select(ProfileExtractionRun).where(
        ProfileExtractionRun.machine_profile_id == machine_id
    ).order_by(ProfileExtractionRun.id.desc())).all()


@router.get("/profile-extraction-runs/{run_id}", response_model=ExtractionRunRead)
def get_run(run_id: int, db: Session = Depends(get_db)):
    value = db.get(ProfileExtractionRun, run_id)
    if not value: raise HTTPException(404, "Extraction run not found")
    return value


@router.get("/profile-extraction-runs/{run_id}/proposals", response_model=list[ProposalRead])
def list_proposals(
    run_id: int, category: str | None = None, proposal_status: str | None = None,
    review_status: str | None = None, confidence_min: float = Query(0, ge=0, le=1),
    safety_relevant: bool | None = None, requires_verification: bool | None = None,
    sort_by: str = Query("field_category", pattern="^(field_category|field_name|confidence|proposal_status|review_status)$"),
    sort_direction: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=250),
    db: Session = Depends(get_db),
):
    query = select(ProfileFieldProposal).options(selectinload(ProfileFieldProposal.evidence)).where(
        ProfileFieldProposal.extraction_run_id == run_id,
        ProfileFieldProposal.confidence >= confidence_min,
    )
    if category: query = query.where(ProfileFieldProposal.field_category == category)
    if proposal_status: query = query.where(ProfileFieldProposal.proposal_status == proposal_status)
    if review_status: query = query.where(ProfileFieldProposal.review_status == review_status)
    if safety_relevant is not None: query = query.where(ProfileFieldProposal.safety_relevant == safety_relevant)
    if requires_verification is not None: query = query.where(ProfileFieldProposal.requires_exact_machine_verification == requires_verification)
    sort_columns = {
        "field_category": ProfileFieldProposal.field_category,
        "field_name": ProfileFieldProposal.field_label,
        "confidence": ProfileFieldProposal.confidence,
        "proposal_status": ProfileFieldProposal.proposal_status,
        "review_status": ProfileFieldProposal.review_status,
    }
    order = sort_columns[sort_by]
    order = order.desc() if sort_direction == "desc" else order.asc()
    return db.scalars(query.order_by(order, ProfileFieldProposal.field_label).offset((page-1)*page_size).limit(page_size)).all()


@router.get("/profile-field-proposals/{proposal_id}", response_model=ProposalRead)
def get_proposal(proposal_id: int, db: Session = Depends(get_db)):
    value = db.scalar(select(ProfileFieldProposal).options(
        selectinload(ProfileFieldProposal.evidence)
    ).where(ProfileFieldProposal.id == proposal_id))
    if not value: raise HTTPException(404, "Field proposal not found")
    return value


def refresh_documentation_coverage(run_id: int, db: Session) -> None:
    run = db.get(ProfileExtractionRun, run_id)
    proposals = list(db.scalars(select(ProfileFieldProposal).where(
        ProfileFieldProposal.extraction_run_id == run_id
    )))
    valid = sum(
        proposal.review_status in {
            "accepted", "accepted_with_edit", "manually_entered",
        }
        or (
            proposal.proposal_status in {"found", "derived"}
            and proposal.review_status not in {"rejected", "deferred", "not_applicable"}
        )
        for proposal in proposals
    )
    summary = dict(run.summary_json)
    summary["reviewed_value_count"] = sum(
        proposal.review_status != "pending" for proposal in proposals
    )
    summary["documentation_coverage"] = round(valid / max(len(proposals), 1) * 100, 1)
    run.summary_json = summary


@router.put("/profile-field-proposals/{proposal_id}/review", response_model=ProposalRead)
def review_proposal(proposal_id: int, payload: ProposalReview, db: Session = Depends(get_db)):
    proposal = db.get(ProfileFieldProposal, proposal_id)
    if not proposal: raise HTTPException(404, "Field proposal not found")
    if payload.unit and normalize_unit(payload.unit) is None:
        raise HTTPException(422, "Unsupported unit")
    changed = payload.review_status in {"accepted_with_edit", "manually_entered"}
    conflict_resolution = proposal.proposal_status == "conflicting" and payload.review_status in {"accepted", "accepted_with_edit", "manually_entered"}
    low_acceptance = proposal.confidence < get_settings().profile_extraction_min_recommended_confidence and payload.review_status in {"accepted", "accepted_with_edit"}
    if (changed or conflict_resolution or low_acceptance or (
        proposal.safety_relevant and payload.review_status == "manually_entered"
    )) and not payload.review_note:
        raise HTTPException(422, "A review note is required for this action")
    if changed and payload.reviewed_value is None:
        raise HTTPException(422, "A reviewed value is required")
    proposal.review_status = payload.review_status
    proposal.reviewed_value_json = payload.reviewed_value if changed else (
        proposal.proposed_value_json if payload.review_status == "accepted" else None
    )
    proposal.review_note = payload.review_note
    proposal.reviewed_by = "local_user"; proposal.reviewed_at = utc_now()
    if payload.unit: proposal.unit = normalize_unit(payload.unit)
    event = {
        "accepted": "profile_field_accepted", "accepted_with_edit": "profile_field_edited",
        "rejected": "profile_field_rejected", "deferred": "profile_field_deferred",
        "manually_entered": "profile_field_manually_entered",
        "not_applicable": "profile_field_deferred",
    }[payload.review_status]
    db.add(AuditEvent(event_type=event, machine_profile_id=proposal.extraction_run.machine_profile_id,
                      metadata_json={"proposal_id": proposal.id, "field_key": proposal.field_key}))
    refresh_documentation_coverage(proposal.extraction_run_id, db)
    db.commit()
    return get_proposal(proposal.id, db)


def _revision_data(revision: MachineProfileRevision) -> dict:
    return {column.name: getattr(revision, column.name) for column in MachineProfileRevision.__table__.columns
            if column.name not in {"id", "revision_number", "status", "created_at", "updated_at", "approved_at"}}


@router.post("/profile-extraction-runs/{run_id}/apply-to-draft")
def apply_to_draft(run_id: int, payload: ApplyDraftRequest, db: Session = Depends(get_db)):
    run = db.get(ProfileExtractionRun, run_id)
    if not run or run.status not in {"completed", "review_required"}:
        raise HTTPException(422, "A completed or review-required run is required")
    machine = machine_or_404(run.machine_profile_id, db)
    active = ensure_initial_revision(machine, db)
    if payload.base_strategy == "active":
        base = active
    elif payload.base_strategy == "selected_revision":
        base = db.get(MachineProfileRevision, payload.source_revision_id or 0)
        if not base or base.machine_profile_id != machine.id:
            raise HTTPException(422, "Selected base revision is invalid")
    else:
        base = None
    number = (db.scalar(select(func.max(MachineProfileRevision.revision_number)).where(
        MachineProfileRevision.machine_profile_id == machine.id
    )) or 0) + 1
    data = _revision_data(base) if base else {
        "machine_profile_id": machine.id, "name": machine.name,
        "manufacturer": None, "model": None, "controller_name": None,
        "machine_type": run.settings_json.get("target_machine_type"),
    }
    data.update(machine_profile_id=machine.id, revision_number=number, status="draft",
                source_type="document_extraction", created_from_revision_id=base.id if base else None,
                review_summary=payload.review_summary)
    revision = MachineProfileRevision(**data)
    db.add(revision); db.flush()
    proposals = list(db.scalars(select(ProfileFieldProposal).options(
        selectinload(ProfileFieldProposal.evidence)
    ).where(ProfileFieldProposal.extraction_run_id == run.id)))
    applied = []
    for proposal in proposals:
        if proposal.review_status not in {"accepted", "accepted_with_edit", "manually_entered"}:
            continue
        value = proposal.reviewed_value_json
        if proposal.field_key == "machine_model":
            revision.model = value
        elif proposal.field_key in REVISION_FIELDS:
            setattr(revision, proposal.field_key, value)
        elif proposal.field_key == "supported_work_offsets":
            revision.supported_work_offsets_json = value or []
        elif proposal.field_category == "capabilities":
            revision.capabilities_json = {**revision.capabilities_json, proposal.field_key: value}
        else:
            revision.machine_configuration_json = {**revision.machine_configuration_json, proposal.field_key: value}
        evidence = proposal.evidence[0] if proposal.evidence else None
        db.add(MachineProfileFieldSource(
            machine_profile_revision_id=revision.id, field_key=proposal.field_key,
            value_json=value, source_type="manual_entry" if proposal.review_status == "manually_entered" else "document_extraction",
            document_id=evidence.document_id if evidence else None,
            document_chunk_id=evidence.document_chunk_id if evidence else None,
            profile_field_proposal_id=proposal.id,
            page_start=evidence.page_start if evidence else None,
            page_end=evidence.page_end if evidence else None,
            section_title=evidence.section_title if evidence else None,
            excerpt=evidence.excerpt if evidence else None,
            review_status=proposal.review_status, review_note=proposal.review_note,
        ))
        applied.append(proposal.field_key)
    if base:
        copied_keys = {
            "manufacturer", "model", "controller_name", "controller_version",
            "controller_manufacturer", "controller_model",
            "machine_type", "axis_count", "x_min", "x_max", "y_min", "y_max",
            "z_min", "z_max", "min_spindle_rpm", "max_spindle_rpm",
            "max_feed_rate", "rapid_traverse_rate", "supported_work_offsets_json",
            "restricted_commands_json", "safe_start_template",
            "tool_change_template", "program_end_template",
        }
        for field_key in sorted(copied_keys - set(applied)):
            value = getattr(base, field_key, None)
            if value is not None and value != []:
                db.add(MachineProfileFieldSource(
                    machine_profile_revision_id=revision.id, field_key=field_key,
                    value_json=value, source_type="copied_from_revision",
                    review_status="accepted", reviewed_by="local_user",
                    review_note=f"Copied from explicitly selected revision {base.id}.",
                ))
    run.target_revision_id = revision.id
    db.add(AuditEvent(event_type="profile_draft_created", machine_profile_id=machine.id,
                      metadata_json={"run_id": run.id, "revision_id": revision.id,
                                     "applied_fields": applied}))
    db.commit(); db.refresh(revision)
    return {"revision": RevisionRead.model_validate(revision),
            "comparison": compare_values(active, revision),
            "applied_field_keys": applied}


@router.post("/profile-extraction-runs/{run_id}/rerun", response_model=ExtractionRunRead)
def rerun(
    run_id: int, selected_machine_variant: str | None = Query(None),
    db: Session = Depends(get_db),
):
    old = db.get(ProfileExtractionRun, run_id)
    if not old: raise HTTPException(404, "Extraction run not found")
    if (
        selected_machine_variant
        and old.detected_variants_json
        and selected_machine_variant not in old.detected_variants_json
    ):
        raise HTTPException(422, "Selected machine variant was not detected in this run")
    payload = ExtractionStart(
        document_ids=old.selected_document_ids_json,
        target_machine_type=old.settings_json.get("target_machine_type", "other"),
        selected_machine_variant=selected_machine_variant or old.selected_machine_variant,
        field_categories=old.settings_json.get("field_categories", []),
    )
    if selected_machine_variant:
        db.add(AuditEvent(
            event_type="profile_variant_selected",
            machine_profile_id=old.machine_profile_id,
            metadata_json={"run_id": old.id, "variant": selected_machine_variant},
        ))
        db.commit()
    return start_extraction(old.machine_profile_id, payload, db)


@router.post("/profile-extraction-runs/{run_id}/cancel", response_model=ExtractionRunRead)
def cancel(run_id: int, db: Session = Depends(get_db)):
    run = db.get(ProfileExtractionRun, run_id)
    if not run: raise HTTPException(404, "Extraction run not found")
    if run.status in {"completed", "review_required", "failed"}:
        raise HTTPException(409, "Completed extraction runs cannot be cancelled")
    run.status = "cancelled"; db.commit(); return run


@router.get("/machines/{machine_id}/revisions", response_model=list[RevisionRead])
def list_revisions(machine_id: int, db: Session = Depends(get_db)):
    machine = machine_or_404(machine_id, db); ensure_initial_revision(machine, db); db.commit()
    return db.scalars(select(MachineProfileRevision).where(
        MachineProfileRevision.machine_profile_id == machine_id
    ).order_by(MachineProfileRevision.revision_number.desc())).all()


@router.get("/machine-profile-revisions/{revision_id}", response_model=RevisionRead)
def get_revision(revision_id: int, db: Session = Depends(get_db)):
    value = db.get(MachineProfileRevision, revision_id)
    if not value: raise HTTPException(404, "Profile revision not found")
    return value


def compare_values(left: MachineProfileRevision, right: MachineProfileRevision):
    keys = ["manufacturer", "model", "controller_name", "controller_manufacturer",
            "controller_model", "controller_version", "machine_type",
            "axis_count", "x_min", "x_max", "y_min", "y_max", "z_min", "z_max",
            "max_spindle_rpm", "max_feed_rate", "rapid_traverse_rate",
            "supported_work_offsets_json", "restricted_commands_json",
            "safe_start_template", "program_end_template", "capabilities_json",
            "machine_configuration_json"]
    return [{"field_key": key, "current": getattr(left, key), "proposed": getattr(right, key),
             "changed": getattr(left, key) != getattr(right, key)} for key in keys]


@router.get("/machine-profile-revisions/{revision_id}/compare/{other_revision_id}")
def compare_revisions(revision_id: int, other_revision_id: int, db: Session = Depends(get_db)):
    left, right = db.get(MachineProfileRevision, revision_id), db.get(MachineProfileRevision, other_revision_id)
    if not left or not right or left.machine_profile_id != right.machine_profile_id:
        raise HTTPException(404, "Comparable revisions not found")
    return {"left_revision_id": left.id, "right_revision_id": right.id,
            "fields": compare_values(left, right)}


@router.post("/machine-profile-revisions/{revision_id}/submit-for-review", response_model=RevisionRead)
def submit_revision(revision_id: int, db: Session = Depends(get_db)):
    revision = db.get(MachineProfileRevision, revision_id)
    if not revision or revision.status != "draft":
        raise HTTPException(422, "A draft revision is required")
    revision.status = "under_review"
    db.add(AuditEvent(event_type="profile_revision_submitted",
                      machine_profile_id=revision.machine_profile_id,
                      metadata_json={"revision_id": revision.id}))
    db.commit(); return revision


@router.post("/machine-profile-revisions/{revision_id}/approve", response_model=RevisionRead)
def approve_revision(revision_id: int, payload: ApprovalRequest, db: Session = Depends(get_db)):
    revision = db.get(MachineProfileRevision, revision_id)
    if not revision or revision.status not in {"draft", "under_review"}:
        raise HTTPException(422, "A draft or under-review revision is required")
    if not payload.exact_machine_applicability_confirmed or not payload.safety_notice_acknowledged:
        raise HTTPException(422, "Exact-machine applicability and the safety notice must be acknowledged")
    required = ["manufacturer", "model", "machine_type", "controller_name"]
    if any(not getattr(revision, key) for key in required):
        raise HTTPException(422, "Core identity fields require reviewed values before approval")
    run = db.scalar(select(ProfileExtractionRun).where(
        ProfileExtractionRun.target_revision_id == revision.id
    ).order_by(ProfileExtractionRun.id.desc()))
    if run:
        proposals = list(db.scalars(select(ProfileFieldProposal).where(
            ProfileFieldProposal.extraction_run_id == run.id
        )))
        pending = [proposal.field_key for proposal in proposals if proposal.review_status == "pending"]
        if pending:
            raise HTTPException(
                422,
                "Every extraction proposal must be reviewed or intentionally deferred before approval",
            )
        unresolved_conflicts = [
            proposal.field_key for proposal in proposals
            if proposal.proposal_status == "conflicting"
            and proposal.review_status not in {
                "accepted_with_edit", "manually_entered", "rejected",
                "deferred", "not_applicable",
            }
        ]
        if unresolved_conflicts:
            raise HTTPException(422, "Conflicting evidence remains unresolved")
    machine = machine_or_404(revision.machine_profile_id, db)
    previous = db.get(MachineProfileRevision, machine.active_revision_id) if machine.active_revision_id else None
    if previous and previous.id != revision.id:
        previous.status = "superseded"
        db.add(AuditEvent(event_type="profile_revision_superseded",
                          machine_profile_id=machine.id,
                          metadata_json={"revision_id": previous.id}))
    revision.status = "approved"; revision.approved_at = utc_now()
    revision.review_summary = payload.review_note
    machine.active_revision_id = revision.id
    for key in ("manufacturer", "model", "controller_name", "controller_manufacturer",
                "controller_model", "controller_version",
                "axis_count", "x_min", "x_max", "y_min", "y_max", "z_min", "z_max",
                "max_spindle_rpm", "max_feed_rate", "safe_start_template",
                "tool_change_template", "program_end_template", "notes"):
        value = getattr(revision, key)
        if value is not None: setattr(machine, key, value)
    if revision.machine_type:
        from app.models.entities import MachineType
        value = revision.machine_type if revision.machine_type in {item.value for item in MachineType} else "other"
        machine.machine_type = MachineType(value)
    machine.supported_work_offsets = revision.supported_work_offsets_json
    machine.approved_g_codes = revision.approved_g_codes_json
    machine.approved_m_codes = revision.approved_m_codes_json
    machine.restricted_commands = revision.restricted_commands_json
    db.add(AuditEvent(event_type="profile_revision_approved",
                      machine_profile_id=machine.id,
                      metadata_json={"revision_id": revision.id}))
    db.commit(); return revision


@router.post("/machine-profile-revisions/{revision_id}/reject", response_model=RevisionRead)
def reject_revision(revision_id: int, payload: RejectionRequest, db: Session = Depends(get_db)):
    revision = db.get(MachineProfileRevision, revision_id)
    if not revision or revision.status not in {"draft", "under_review"}:
        raise HTTPException(422, "A draft or under-review revision is required")
    revision.status = "rejected"; revision.review_summary = payload.review_note
    db.add(AuditEvent(event_type="profile_revision_rejected",
                      machine_profile_id=revision.machine_profile_id,
                      metadata_json={"revision_id": revision.id}))
    db.commit(); return revision

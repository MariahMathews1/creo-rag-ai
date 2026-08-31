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
from app.models.gpost import GPostDraft, MachineKnowledgeFact, OFGSetting
from app.ofg.domain import DEFINITIONS
from app.profile_extraction.registry import FIELD_MAP
from app.profile_extraction.service import execute_extraction
from app.profile_extraction.units import UNIT_ALIASES, normalize_unit
from app.schemas.profile_extraction import (
    AcceptEligibleHighConfidenceRequest, ApplyDraftRequest, ApprovalRequest,
    BatchReviewFailure, BatchReviewRequest, BatchReviewResponse,
    ExtractionRunRead, ExtractionStart, ProposalRead, ProposalReview,
    ManualInformationFieldRead, ManualInformationRead, ManualInformationWrite,
    RejectionRequest, ReviewCategorySummary, ReviewEventRequest,
    ReviewQueueRead, ReviewSummaryRead, RevisionRead,
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
REVIEW_STATUSES = {
    "pending", "accepted", "accepted_with_edit", "rejected", "deferred",
    "manually_entered", "not_applicable",
}
PHYSICAL_CLAIM_CATEGORIES = {
    "axis_limits", "spindle", "feed_and_motion", "tooling", "workholding",
    "capabilities", "safety_and_setup",
}
MANUAL_SOURCE_BASIS = {
    "engineer_entry": "Engineer Entry", "installed_machine_configuration": "Installed Machine Configuration",
    "machine_nameplate": "Machine Nameplate", "machine_manual": "Machine Manual",
    "controller_manual": "Controller Manual", "site_standard": "Site Standard",
    "other_approved_source": "Other Approved Source",
}
MANUAL_FIELD_KEYS = (
    "manufacturer", "model", "machine_type", "controller_name", "controller_manufacturer", "controller_model",
    "controller_version", "axis_count", "x_travel", "y_travel", "z_travel", "max_spindle_rpm",
    "max_feed_rate", "rapid_traverse_rate", "supported_work_offsets", "supported_g_codes", "supported_m_codes",
    "canned_cycles", "turning_cycles", "drilling_cycles", "tool_change_template", "safe_start_commands",
    "coolant_start_template", "program_number_format", "sequence_number_format",
)
MANUAL_CATEGORY_LABELS = {
    "identity": "Identity", "controller": "Controller", "axis_limits": "Axes / Kinematics", "spindle": "Spindle",
    "feed_and_motion": "Feed / Motion", "tooling": "Tooling", "coolant": "Coolant",
    "programming": "Programming / Codes", "programming_codes": "Programming / Codes",
    "capabilities": "Cycles / Capabilities", "safety_and_setup": "Additional Machine Information",
}
PROFILE_TO_POST_FACT = {
    "machine_type": "machine_type", "controller_name": "controller", "controller_model": "controller",
    "axis_count": "axes", "x_travel": "x_travel", "y_travel": "y_travel", "z_travel": "z_travel",
    "max_spindle_rpm": "max_spindle_rpm", "max_feed_rate": "max_feed_rate",
    "supported_work_offsets": "work_offsets", "canned_cycles": "supported_cycles", "turning_cycles": "supported_cycles",
    "drilling_cycles": "supported_cycles", "tool_change_template": "tool_change", "safe_start_commands": "safe_start",
    "coolant_start_template": "coolant_on",
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


def _manual_category(definition) -> str:
    return MANUAL_CATEGORY_LABELS.get(definition.category, definition.category.replace("_", " ").title())


def _manual_value_on_revision(revision: MachineProfileRevision, field_key: str, value: object) -> None:
    if field_key == "machine_model":
        revision.model = str(value)
    elif field_key in REVISION_FIELDS:
        setattr(revision, field_key, value)
    elif field_key == "supported_work_offsets":
        revision.supported_work_offsets_json = value if isinstance(value, list) else [value]
    elif field_key == "supported_g_codes":
        revision.approved_g_codes_json = value if isinstance(value, list) else [value]
    elif field_key == "supported_m_codes":
        revision.approved_m_codes_json = value if isinstance(value, list) else [value]
    elif FIELD_MAP[field_key].category == "capabilities":
        revision.capabilities_json = {**(revision.capabilities_json or {}), field_key: value}
    else:
        revision.machine_configuration_json = {**(revision.machine_configuration_json or {}), field_key: value}


def _clear_manual_value_on_revision(revision: MachineProfileRevision, field_key: str) -> None:
    if field_key in REVISION_FIELDS:
        setattr(revision, field_key, None)
    elif field_key == "supported_work_offsets":
        revision.supported_work_offsets_json = []
    elif field_key == "supported_g_codes":
        revision.approved_g_codes_json = []
    elif field_key == "supported_m_codes":
        revision.approved_m_codes_json = []
    elif FIELD_MAP[field_key].category == "capabilities":
        values = dict(revision.capabilities_json or {}); values.pop(field_key, None)
        revision.capabilities_json = values
    else:
        values = dict(revision.machine_configuration_json or {}); values.pop(field_key, None)
        revision.machine_configuration_json = values


def _manual_value_from_revision(revision: MachineProfileRevision, field_key: str, *, effective: bool = False) -> object | None:
    if field_key in REVISION_FIELDS:
        return getattr(revision, field_key)
    if field_key == "supported_work_offsets": return revision.supported_work_offsets_json
    if field_key == "supported_g_codes": return revision.approved_g_codes_json
    if field_key == "supported_m_codes": return revision.approved_m_codes_json
    if FIELD_MAP[field_key].category == "capabilities":
        return (revision.capabilities_json or {}).get(field_key)
    value = (revision.machine_configuration_json or {}).get(field_key)
    if value is None and effective and field_key in {"x_travel", "y_travel", "z_travel"}:
        axis = field_key[0]
        limits = [getattr(revision, f"{axis}_min"), getattr(revision, f"{axis}_max")]
        return limits if any(item is not None for item in limits) else None
    return value


def _copy_field_source(source: MachineProfileFieldSource, revision_id: int) -> MachineProfileFieldSource:
    return MachineProfileFieldSource(
        machine_profile_revision_id=revision_id, field_key=source.field_key,
        value_json=source.value_json, unit=source.unit, source_type=source.source_type,
        document_id=source.document_id, document_chunk_id=source.document_chunk_id,
        profile_field_proposal_id=source.profile_field_proposal_id,
        page_start=source.page_start, page_end=source.page_end,
        section_title=source.section_title, excerpt=source.excerpt,
        review_status=source.review_status, reviewed_by=source.reviewed_by,
        review_note=source.review_note,
    )


def _sync_machine_from_revision(machine: MachineProfile, revision: MachineProfileRevision) -> None:
    for key in ("manufacturer", "model", "controller_name", "controller_manufacturer", "controller_model", "controller_version",
                "axis_count", "x_min", "x_max", "y_min", "y_max", "z_min", "z_max", "max_spindle_rpm", "max_feed_rate",
                "safe_start_template", "tool_change_template", "program_end_template", "notes"):
        value = getattr(revision, key)
        if value is not None: setattr(machine, key, value)
    machine.supported_work_offsets = revision.supported_work_offsets_json
    machine.approved_g_codes = revision.approved_g_codes_json
    machine.approved_m_codes = revision.approved_m_codes_json


def _sync_manual_value_to_posts(db: Session, machine_id: int, field_key: str, value: object | None, unit: str | None,
                                source_label: str, source_detail: str | None, review_status: str,
                                review_note: str = "Manually entered machine information.",
                                setting_source_type: str = "Engineer Entry") -> None:
    post_key = PROFILE_TO_POST_FACT.get(field_key)
    if not post_key: return
    definition = next((item for item in DEFINITIONS if item.fact_key == post_key), None)
    for draft in db.scalars(select(GPostDraft).where(GPostDraft.machine_profile_id == machine_id,
                                                      GPostDraft.status.notin_(("archived", "superseded")))):
        fact = db.scalar(select(MachineKnowledgeFact).where(MachineKnowledgeFact.post_record_id == draft.id,
                                                            MachineKnowledgeFact.fact_key == post_key))
        if fact is None:
            fact = MachineKnowledgeFact(post_record_id=draft.id, fact_key=post_key,
                name=definition.name if definition else FIELD_MAP[field_key].display_name,
                category=definition.category if definition else _manual_category(FIELD_MAP[field_key]))
            db.add(fact); db.flush()
        fact.value_json = value; fact.unit = unit
        fact.status = review_status if value is not None else "unknown"
        fact.post_review_status = "available_from_machine" if review_status == "confirmed" and value is not None else "needs_information"
        fact.source_label = source_label; fact.source_location = source_detail; fact.reviewer = "Local Engineer"
        fact.review_note = review_note
        for setting in db.scalars(select(OFGSetting).where(OFGSetting.post_record_id == draft.id)):
            if fact.id not in (setting.source_machine_fact_ids_json or []): continue
            if setting.setting_key == "axis_limits":
                axis_facts = list(db.scalars(select(MachineKnowledgeFact).where(
                    MachineKnowledgeFact.post_record_id == draft.id,
                    MachineKnowledgeFact.fact_key.in_(("x_travel", "y_travel", "z_travel")),
                )))
                setting.value_json = {
                    item.fact_key[0].upper(): item.value_json
                    for item in axis_facts if item.value_json is not None
                }
            else:
                setting.value_json = value
            setting.unit = unit
            setting.source_type = setting_source_type
            if setting.status not in {"reviewed", "not_applicable"}:
                setting.status = "needs_review" if review_status == "confirmed" else "needs_information"


@router.get("/machines/{machine_id}/machine-information/fields", response_model=list[ManualInformationFieldRead])
def list_manual_information_fields(machine_id: int, db: Session = Depends(get_db)):
    machine_or_404(machine_id, db)
    return [ManualInformationFieldRead(fact_key=key, label=FIELD_MAP[key].display_name,
        category=_manual_category(FIELD_MAP[key]), data_type=FIELD_MAP[key].data_type,
        units=list(FIELD_MAP[key].allowed_units)) for key in MANUAL_FIELD_KEYS if key in FIELD_MAP]


@router.get("/machines/{machine_id}/machine-information", response_model=list[ManualInformationRead])
def list_manual_information(machine_id: int, db: Session = Depends(get_db)):
    machine = machine_or_404(machine_id, db); revision = ensure_initial_revision(machine, db); db.commit()
    rows = list(db.scalars(select(MachineProfileFieldSource).where(
        MachineProfileFieldSource.machine_profile_revision_id == revision.id).order_by(MachineProfileFieldSource.id.desc())))
    result, seen = [], set()
    for row in rows:
        if row.field_key in seen or row.field_key not in FIELD_MAP: continue
        seen.add(row.field_key); definition = FIELD_MAP[row.field_key]
        result.append(ManualInformationRead(id=row.id, machine_profile_id=machine.id, revision_id=revision.id,
            fact_key=row.field_key, label=definition.display_name, category=_manual_category(definition), value=row.value_json,
            unit=row.unit, source_basis=row.source_type, source_label=MANUAL_SOURCE_BASIS.get(row.source_type, row.source_type.replace("_", " ").title()),
            source_detail=row.section_title, notes=row.review_note, review_status=row.review_status,
            proposal_id=row.profile_field_proposal_id))
    return result


@router.post("/machines/{machine_id}/machine-information/manual", response_model=ManualInformationRead, status_code=201)
def save_manual_information(machine_id: int, payload: ManualInformationWrite, db: Session = Depends(get_db)):
    machine = machine_or_404(machine_id, db)
    if payload.fact_key not in MANUAL_FIELD_KEYS or payload.fact_key not in FIELD_MAP: raise HTTPException(422, "Unsupported Machine Information field")
    if payload.source_basis not in MANUAL_SOURCE_BASIS: raise HTTPException(422, "Unsupported source/basis")
    definition = FIELD_MAP[payload.fact_key]
    unit = normalize_unit(payload.unit) if payload.unit else None
    if payload.unit and unit is None: raise HTTPException(422, "Unsupported unit")
    if unit and definition.allowed_units and unit not in definition.allowed_units: raise HTTPException(422, "Unit is not valid for this field")
    value = payload.value
    if definition.data_type in {"number", "integer"}:
        try: value = int(value) if definition.data_type == "integer" else float(value)
        except (TypeError, ValueError): raise HTTPException(422, "A numeric value is required")
    document = db.get(SourceDocument, payload.document_id) if payload.document_id else None
    if payload.document_id and (not document or document.machine_profile_id != machine.id): raise HTTPException(422, "Document must belong to this machine")
    active = ensure_initial_revision(machine, db)
    number = (db.scalar(select(func.max(MachineProfileRevision.revision_number)).where(MachineProfileRevision.machine_profile_id == machine.id)) or 0) + 1
    data = _revision_data(active); data.update(machine_profile_id=machine.id, revision_number=number, status="approved",
        source_type="manual_entry", created_from_revision_id=active.id, review_summary=payload.notes, approved_at=utc_now())
    revision = MachineProfileRevision(**data); _manual_value_on_revision(revision, payload.fact_key, value)
    db.add(revision); db.flush(); active.status = "superseded"; machine.active_revision_id = revision.id; _sync_machine_from_revision(machine, revision)
    prior_sources = list(db.scalars(select(MachineProfileFieldSource).where(
        MachineProfileFieldSource.machine_profile_revision_id == active.id,
        MachineProfileFieldSource.field_key != payload.fact_key,
    )))
    for prior in prior_sources:
        db.add(_copy_field_source(prior, revision.id))
    source = MachineProfileFieldSource(machine_profile_revision_id=revision.id, field_key=payload.fact_key, value_json=value,
        unit=unit, source_type=payload.source_basis, document_id=payload.document_id, profile_field_proposal_id=payload.proposal_id,
        section_title=payload.source_detail, review_status=payload.review_status, reviewed_by="local_user", review_note=payload.notes)
    db.add(source); db.flush()
    if payload.proposal_id:
        proposal = db.get(ProfileFieldProposal, payload.proposal_id)
        if not proposal or proposal.extraction_run.machine_profile_id != machine.id or proposal.field_key != payload.fact_key:
            raise HTTPException(422, "The missing-information item does not match this machine field")
        proposal.review_status = "manually_entered"; proposal.reviewed_value_json = value; proposal.unit = unit
        proposal.review_note = payload.notes or f"Entered manually from {MANUAL_SOURCE_BASIS[payload.source_basis]}."
        proposal.reviewed_by = "local_user"; proposal.reviewed_at = utc_now(); refresh_documentation_coverage(proposal.extraction_run_id, db)
    source_label = document.title if document else MANUAL_SOURCE_BASIS[payload.source_basis]
    _sync_manual_value_to_posts(db, machine.id, payload.fact_key, value, unit, source_label, payload.source_detail, payload.review_status)
    db.add(AuditEvent(event_type="machine_information_manually_entered", machine_profile_id=machine.id,
        metadata_json={"field_key": payload.fact_key, "review_status": payload.review_status, "proposal_id": payload.proposal_id}))
    db.commit()
    return ManualInformationRead(id=source.id, machine_profile_id=machine.id, revision_id=revision.id,
        fact_key=payload.fact_key, label=definition.display_name, category=_manual_category(definition), value=value, unit=unit,
        source_basis=payload.source_basis, source_label=source_label, source_detail=payload.source_detail, notes=payload.notes,
        review_status=payload.review_status, proposal_id=payload.proposal_id)


@router.delete("/machines/{machine_id}/machine-information/{field_key}", status_code=204)
def discard_machine_information(machine_id: int, field_key: str, db: Session = Depends(get_db)):
    machine = machine_or_404(machine_id, db)
    if field_key not in MANUAL_FIELD_KEYS or field_key not in FIELD_MAP:
        raise HTTPException(404, "Machine Information field not found")
    active = ensure_initial_revision(machine, db)
    current_source = db.scalar(select(MachineProfileFieldSource).where(
        MachineProfileFieldSource.machine_profile_revision_id == active.id,
        MachineProfileFieldSource.field_key == field_key,
    ).order_by(MachineProfileFieldSource.id.desc()))
    if current_source is None:
        raise HTTPException(404, "Machine Information entry not found")

    baseline_revision = db.get(MachineProfileRevision, active.created_from_revision_id) if active.created_from_revision_id else None
    baseline_source = None
    while baseline_revision:
        candidate = db.scalar(select(MachineProfileFieldSource).where(
            MachineProfileFieldSource.machine_profile_revision_id == baseline_revision.id,
            MachineProfileFieldSource.field_key == field_key,
        ).order_by(MachineProfileFieldSource.id.desc()))
        copied_current_extraction = (
            current_source.source_type not in MANUAL_SOURCE_BASIS and candidate is not None
            and candidate.source_type == current_source.source_type
            and candidate.profile_field_proposal_id == current_source.profile_field_proposal_id
            and candidate.document_chunk_id == current_source.document_chunk_id
            and candidate.value_json == current_source.value_json
        )
        if candidate is None or (current_source.source_type in MANUAL_SOURCE_BASIS and candidate.source_type not in MANUAL_SOURCE_BASIS):
            baseline_source = candidate; break
        if current_source.source_type not in MANUAL_SOURCE_BASIS and not copied_current_extraction:
            baseline_source = candidate; break
        baseline_revision = db.get(MachineProfileRevision, baseline_revision.created_from_revision_id) if baseline_revision.created_from_revision_id else None

    number = (db.scalar(select(func.max(MachineProfileRevision.revision_number)).where(
        MachineProfileRevision.machine_profile_id == machine.id)) or 0) + 1
    data = _revision_data(active); data.update(
        machine_profile_id=machine.id, revision_number=number, status="approved",
        source_type="manual_discard", created_from_revision_id=active.id,
        review_summary=f"Discarded current {FIELD_MAP[field_key].display_name} entry.", approved_at=utc_now(),
    )
    revision = MachineProfileRevision(**data)
    _clear_manual_value_on_revision(revision, field_key)
    if baseline_revision:
        baseline_value = _manual_value_from_revision(baseline_revision, field_key)
        if baseline_value is not None: _manual_value_on_revision(revision, field_key, baseline_value)
    db.add(revision); db.flush()
    for source in db.scalars(select(MachineProfileFieldSource).where(
        MachineProfileFieldSource.machine_profile_revision_id == active.id,
        MachineProfileFieldSource.field_key != field_key,
    )):
        db.add(_copy_field_source(source, revision.id))
    if baseline_source:
        db.add(_copy_field_source(baseline_source, revision.id))
    active.status = "superseded"; machine.active_revision_id = revision.id
    _sync_machine_from_revision(machine, revision)
    if hasattr(machine, field_key): setattr(machine, field_key, getattr(revision, field_key))
    effective_value = _manual_value_from_revision(revision, field_key, effective=True)
    source_label = "Previous Machine Information" if baseline_source else f"Machine profile revision {revision.revision_number}"
    _sync_manual_value_to_posts(
        db, machine.id, field_key, effective_value, baseline_source.unit if baseline_source else None,
        source_label, baseline_source.section_title if baseline_source else None,
        baseline_source.review_status if baseline_source else "needs_review",
        review_note="Current Machine Information entry discarded; previous machine context restored where available.",
        setting_source_type="Machine Knowledge",
    )
    db.add(AuditEvent(event_type="machine_information_discarded", machine_profile_id=machine.id,
        metadata_json={"field_key": field_key, "discarded_source_type": current_source.source_type,
                       "restored_revision_id": baseline_revision.id if baseline_revision else None}))
    db.commit()


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


def _proposals_for_run(run_id: int, db: Session) -> list[ProfileFieldProposal]:
    return list(db.scalars(
        select(ProfileFieldProposal)
        .options(selectinload(ProfileFieldProposal.evidence))
        .where(ProfileFieldProposal.extraction_run_id == run_id)
        .order_by(ProfileFieldProposal.field_category, ProfileFieldProposal.field_label)
    ))


def _batch_accept_block_reason(
    proposal: ProfileFieldProposal,
    run: ProfileExtractionRun,
) -> str | None:
    settings = get_settings()
    if proposal.review_status != "pending":
        return "already_reviewed"
    if proposal.proposal_status == "conflicting":
        return "unresolved_conflict"
    if proposal.proposal_status == "ambiguous":
        return "ambiguous"
    if proposal.proposal_status != "found":
        return "proposal_not_found"
    if proposal.confidence < settings.profile_extraction_high_confidence:
        return "below_high_confidence_threshold"
    if proposal.normalized_value_json is None:
        return "normalized_value_missing"
    if not proposal.evidence:
        return "missing_citation"
    if not any(item.evidence_type == "supporting" for item in proposal.evidence):
        return "missing_supporting_citation"
    if any(item.evidence_type == "conflicting" for item in proposal.evidence):
        return "conflicting_evidence"
    if proposal.requires_exact_machine_verification:
        return "exact_machine_verification_required"
    if proposal.safety_relevant:
        return "safety_relevant_requires_individual_review"
    if (
        run.selected_machine_variant
        and proposal.variant_applicability_json
        and run.selected_machine_variant not in proposal.variant_applicability_json
    ):
        return "variant_not_applicable"
    evidence_types = {item.document_type for item in proposal.evidence}
    if (
        proposal.field_category in PHYSICAL_CLAIM_CATEGORIES
        and evidence_types
        and evidence_types <= {DocumentType.CONTROLLER_MANUAL.value}
    ):
        return "controller_evidence_cannot_prove_installed_machine_claim"
    return None


def _review_summary(
    run: ProfileExtractionRun,
    proposals: list[ProfileFieldProposal],
    db: Session,
) -> ReviewSummaryRead:
    settings = get_settings()
    machine = machine_or_404(run.machine_profile_id, db)
    counts = {
        status: sum(item.review_status == status for item in proposals)
        for status in REVIEW_STATUSES
    }
    pending = counts["pending"]
    category_summaries = []
    for category in sorted({item.field_category for item in proposals}):
        items = [item for item in proposals if item.field_category == category]
        category_pending = sum(item.review_status == "pending" for item in items)
        category_summaries.append(ReviewCategorySummary(
            category=category,
            total=len(items),
            reviewed=len(items) - category_pending,
            pending=category_pending,
            conflicts=sum(
                item.proposal_status == "conflicting"
                and item.review_status == "pending"
                for item in items
            ),
            complete=category_pending == 0,
        ))
    conflict_pending = sum(
        item.proposal_status == "conflicting" and item.review_status == "pending"
        for item in proposals
    )
    ambiguous_pending = sum(
        item.proposal_status == "ambiguous" and item.review_status == "pending"
        for item in proposals
    )
    high_eligible = sum(
        _batch_accept_block_reason(item, run) is None for item in proposals
    )
    safety_low_pending = sum(
        item.review_status == "pending"
        and item.safety_relevant
        and item.confidence < settings.profile_extraction_high_confidence
        for item in proposals
    )
    variant_rerun_required = (
        len(run.detected_variants_json or []) > 1
        and not run.selected_machine_variant
    )
    readiness_reasons = []
    if pending:
        readiness_reasons.append(f"{pending} proposals still require intentional review")
    if conflict_pending:
        readiness_reasons.append(f"{conflict_pending} conflicts remain unresolved")
    if safety_low_pending:
        readiness_reasons.append(
            f"{safety_low_pending} low-confidence safety-relevant fields require review"
        )
    if variant_rerun_required:
        readiness_reasons.append("Select and re-run the exact machine variant")
    draft_ready = not readiness_reasons
    revision = (
        db.get(MachineProfileRevision, run.target_revision_id)
        if run.target_revision_id else None
    )
    identity_ready = bool(
        revision
        and revision.manufacturer
        and revision.model
        and revision.machine_type
        and revision.controller_name
    )
    approval_ready = bool(
        draft_ready
        and revision
        and revision.status in {"draft", "under_review"}
        and identity_ready
    )
    found_pending = sum(
        item.review_status == "pending"
        and item.proposal_status in {"found", "derived"}
        for item in proposals
    )
    not_found_pending = sum(
        item.review_status == "pending" and item.proposal_status == "not_found"
        for item in proposals
    )
    recommended = None
    if conflict_pending:
        recommended = "conflicts"
    elif high_eligible:
        recommended = "high-confidence"
    elif any(
        item.review_status == "pending"
        and item.proposal_status == "found"
        and settings.profile_extraction_medium_confidence
        <= item.confidence
        < settings.profile_extraction_high_confidence
        for item in proposals
    ):
        recommended = "medium-confidence"
    elif any(
        item.review_status == "pending"
        and item.proposal_status == "found"
        and item.confidence < settings.profile_extraction_medium_confidence
        for item in proposals
    ):
        recommended = "low-confidence"
    elif not_found_pending:
        recommended = "not-found"
    reviewed = len(proposals) - pending
    return ReviewSummaryRead(
        run_id=run.id,
        machine_profile_id=run.machine_profile_id,
        machine_name=machine.name,
        selected_variant=run.selected_machine_variant,
        run_status=run.status,
        documents_analyzed=len(run.selected_document_ids_json or []),
        total=len(proposals),
        found=sum(item.proposal_status in {"found", "derived"} for item in proposals),
        not_found=sum(item.proposal_status == "not_found" for item in proposals),
        conflicting=sum(item.proposal_status == "conflicting" for item in proposals),
        ambiguous=sum(item.proposal_status == "ambiguous" for item in proposals),
        pending=pending,
        accepted=counts["accepted"],
        accepted_with_edit=counts["accepted_with_edit"],
        rejected=counts["rejected"],
        deferred=counts["deferred"],
        manually_entered=counts["manually_entered"],
        not_applicable=counts["not_applicable"],
        found_pending=found_pending,
        not_found_pending=not_found_pending,
        conflict_pending=conflict_pending,
        ambiguous_pending=ambiguous_pending,
        high_confidence_eligible=high_eligible,
        safety_low_confidence_pending=safety_low_pending,
        remaining_required_review=pending,
        reviewed=reviewed,
        review_progress_percent=round(reviewed / max(len(proposals), 1) * 100, 1),
        documentation_coverage=float(
            (run.summary_json or {}).get("documentation_coverage", 0)
        ),
        category_summaries=category_summaries,
        draft_ready=draft_ready,
        approval_ready=approval_ready,
        variant_rerun_required=variant_rerun_required,
        readiness_reasons=readiness_reasons,
        recommended_next_queue=recommended,
        confidence_high_threshold=settings.profile_extraction_high_confidence,
        confidence_medium_threshold=settings.profile_extraction_medium_confidence,
    )


@router.get(
    "/profile-extraction-runs/{run_id}/review-summary",
    response_model=ReviewSummaryRead,
)
def get_review_summary(run_id: int, db: Session = Depends(get_db)):
    run = db.get(ProfileExtractionRun, run_id)
    if not run:
        raise HTTPException(404, "Extraction run not found")
    return _review_summary(run, _proposals_for_run(run_id, db), db)


def _matches_queue(
    proposal: ProfileFieldProposal,
    queue: str,
    settings,
) -> bool:
    if queue == "all":
        return True
    if queue == "needs-review":
        return proposal.review_status == "pending"
    if queue == "conflicts":
        return (
            proposal.review_status == "pending"
            and proposal.proposal_status == "conflicting"
        )
    if queue == "high-confidence":
        return (
            proposal.review_status == "pending"
            and proposal.proposal_status == "found"
            and proposal.confidence >= settings.profile_extraction_high_confidence
        )
    if queue == "medium-confidence":
        return (
            proposal.review_status == "pending"
            and proposal.proposal_status == "found"
            and settings.profile_extraction_medium_confidence
            <= proposal.confidence
            < settings.profile_extraction_high_confidence
        )
    if queue == "low-confidence":
        return (
            proposal.review_status == "pending"
            and proposal.proposal_status == "found"
            and proposal.confidence < settings.profile_extraction_medium_confidence
        )
    if queue == "not-found":
        return (
            proposal.review_status == "pending"
            and proposal.proposal_status == "not_found"
        )
    expected_status = {
        "deferred": "deferred",
        "accepted": "accepted",
        "rejected": "rejected",
        "manual-entries": "manually_entered",
        "not-applicable": "not_applicable",
    }.get(queue)
    return bool(expected_status and proposal.review_status == expected_status)


@router.get(
    "/profile-extraction-runs/{run_id}/review-queue",
    response_model=ReviewQueueRead,
)
def get_review_queue(
    run_id: int,
    queue: str = Query("needs-review"),
    search: str | None = Query(default=None, max_length=200),
    category: str | None = None,
    proposal_status: str | None = None,
    review_status: str | None = None,
    confidence_min: float = Query(0, ge=0, le=1),
    confidence_max: float = Query(1, ge=0, le=1),
    safety_relevant: bool | None = None,
    requires_verification: bool | None = None,
    has_evidence: bool | None = None,
    has_conflicting_evidence: bool | None = None,
    source_document_id: int | None = None,
    source_authority: str | None = None,
    claim_scope: str | None = None,
    machine_variant: str | None = None,
    sort_by: str = Query(
        "priority",
        pattern=(
            "^(priority|field_name|field_category|confidence|proposal_status|"
            "review_status|evidence_count)$"
        ),
    ),
    sort_direction: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(250, ge=1, le=500),
    db: Session = Depends(get_db),
):
    run = db.get(ProfileExtractionRun, run_id)
    if not run:
        raise HTTPException(404, "Extraction run not found")
    settings = get_settings()
    items = [
        item for item in _proposals_for_run(run_id, db)
        if _matches_queue(item, queue, settings)
    ]
    if category:
        items = [item for item in items if item.field_category == category]
    if proposal_status:
        items = [item for item in items if item.proposal_status == proposal_status]
    if review_status:
        items = [item for item in items if item.review_status == review_status]
    items = [
        item for item in items
        if confidence_min <= item.confidence <= confidence_max
    ]
    if safety_relevant is not None:
        items = [item for item in items if item.safety_relevant == safety_relevant]
    if requires_verification is not None:
        items = [
            item for item in items
            if item.requires_exact_machine_verification == requires_verification
        ]
    if has_evidence is not None:
        items = [item for item in items if bool(item.evidence) == has_evidence]
    if has_conflicting_evidence is not None:
        items = [
            item for item in items
            if any(evidence.evidence_type == "conflicting" for evidence in item.evidence)
            == has_conflicting_evidence
        ]
    if source_document_id is not None:
        items = [
            item for item in items
            if any(evidence.document_id == source_document_id for evidence in item.evidence)
        ]
    if source_authority:
        items = [
            item for item in items
            if any(evidence.document_type == source_authority for evidence in item.evidence)
        ]
    if claim_scope:
        items = [item for item in items if item.field_category == claim_scope]
    if machine_variant:
        items = [
            item for item in items
            if not item.variant_applicability_json
            or machine_variant in item.variant_applicability_json
        ]
    if search:
        lowered = search.casefold()
        items = [
            item for item in items
            if lowered in " ".join([
                item.field_label,
                item.field_key,
                item.field_category,
                str(item.proposed_value_json),
                str(item.reviewed_value_json),
                item.review_note or "",
                *[
                    f"{evidence.document_title} {evidence.excerpt}"
                    for evidence in item.evidence
                ],
            ]).casefold()
        ]
    priority = {"conflicting": 0, "ambiguous": 1, "found": 2, "not_found": 3}
    sorters = {
        "priority": lambda item: (
            priority.get(item.proposal_status, 4),
            -item.confidence,
            item.field_label.casefold(),
        ),
        "field_name": lambda item: item.field_label.casefold(),
        "field_category": lambda item: item.field_category,
        "confidence": lambda item: item.confidence,
        "proposal_status": lambda item: item.proposal_status,
        "review_status": lambda item: item.review_status,
        "evidence_count": lambda item: len(item.evidence),
    }
    items.sort(
        key=sorters[sort_by],
        reverse=sort_direction == "desc",
    )
    total = len(items)
    sliced = items[(page - 1) * page_size:page * page_size]
    return ReviewQueueRead(
        queue=queue,
        total=total,
        page=page,
        page_size=page_size,
        items=[ProposalRead.model_validate(item) for item in sliced],
    )


def refresh_documentation_coverage(run_id: int, db: Session) -> None:
    run = db.get(ProfileExtractionRun, run_id)
    proposals = list(db.scalars(select(ProfileFieldProposal).where(
        ProfileFieldProposal.extraction_run_id == run_id
    )))
    summary = dict(run.summary_json)
    summary["reviewed_value_count"] = sum(
        proposal.review_status != "pending" for proposal in proposals
    )
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
    summary = _review_summary(
        proposal.extraction_run,
        _proposals_for_run(proposal.extraction_run_id, db),
        db,
    )
    if summary.draft_ready:
        db.add(AuditEvent(
            event_type="draft_readiness_reached",
            machine_profile_id=proposal.extraction_run.machine_profile_id,
            metadata_json={"run_id": proposal.extraction_run_id},
        ))
    db.commit()
    return get_proposal(proposal.id, db)


def _apply_batch_review(
    run: ProfileExtractionRun,
    payload: BatchReviewRequest,
    db: Session,
    *,
    high_confidence_workflow: bool = False,
) -> BatchReviewResponse:
    requested_ids = list(dict.fromkeys(payload.proposal_ids))
    proposals = {
        item.id: item for item in _proposals_for_run(run.id, db)
        if item.id in requested_ids
    }
    succeeded: list[int] = []
    failed: list[BatchReviewFailure] = []
    if payload.action == "accept" and not payload.confirmation.acknowledge_advisory_only:
        failed = [
            BatchReviewFailure(
                proposal_id=proposal_id,
                reason="advisory_acknowledgment_required",
            )
            for proposal_id in requested_ids
        ]
        return BatchReviewResponse(
            succeeded=[],
            failed=failed,
            summary=_review_summary(run, _proposals_for_run(run.id, db), db),
        )
    status_by_action = {
        "accept": "accepted",
        "defer": "deferred",
        "reject": "rejected",
        "not_applicable": "not_applicable",
    }
    event_by_action = {
        "accept": "profile_field_accepted",
        "defer": "profile_field_deferred",
        "reject": "profile_field_rejected",
        "not_applicable": "profile_field_deferred",
    }
    for proposal_id in requested_ids:
        proposal = proposals.get(proposal_id)
        reason = None
        if proposal is None:
            reason = "proposal_not_in_run"
        elif payload.action == "accept":
            reason = _batch_accept_block_reason(proposal, run)
        elif proposal.review_status != "pending":
            reason = "already_reviewed"
        if reason:
            failed.append(BatchReviewFailure(
                proposal_id=proposal_id,
                reason=reason,
            ))
            continue
        proposal.review_status = status_by_action[payload.action]
        proposal.reviewed_value_json = (
            proposal.proposed_value_json if payload.action == "accept" else None
        )
        proposal.review_note = (
            "Accepted through protected high-confidence batch review."
            if high_confidence_workflow
            else f"Batch action: {payload.action}."
        )
        proposal.reviewed_by = "local_user"
        proposal.reviewed_at = utc_now()
        succeeded.append(proposal.id)
        db.add(AuditEvent(
            event_type=event_by_action[payload.action],
            machine_profile_id=run.machine_profile_id,
            metadata_json={
                "proposal_id": proposal.id,
                "field_key": proposal.field_key,
                "batch": True,
            },
        ))
    if succeeded:
        db.add(AuditEvent(
            event_type=(
                "high_confidence_batch_reviewed"
                if high_confidence_workflow
                else "batch_review_applied"
            ),
            machine_profile_id=run.machine_profile_id,
            metadata_json={
                "run_id": run.id,
                "action": payload.action,
                "succeeded_ids": succeeded,
                "failed_count": len(failed),
            },
        ))
        refresh_documentation_coverage(run.id, db)
        post_summary = _review_summary(run, _proposals_for_run(run.id, db), db)
        if post_summary.draft_ready:
            db.add(AuditEvent(
                event_type="draft_readiness_reached",
                machine_profile_id=run.machine_profile_id,
                metadata_json={"run_id": run.id},
            ))
        db.commit()
    return BatchReviewResponse(
        succeeded=succeeded,
        failed=failed,
        summary=_review_summary(run, _proposals_for_run(run.id, db), db),
    )


@router.post(
    "/profile-extraction-runs/{run_id}/proposals/batch-review",
    response_model=BatchReviewResponse,
)
def batch_review_proposals(
    run_id: int,
    payload: BatchReviewRequest,
    db: Session = Depends(get_db),
):
    run = db.get(ProfileExtractionRun, run_id)
    if not run:
        raise HTTPException(404, "Extraction run not found")
    return _apply_batch_review(run, payload, db)


@router.post(
    "/profile-extraction-runs/{run_id}/accept-eligible-high-confidence",
    response_model=BatchReviewResponse,
)
def accept_eligible_high_confidence(
    run_id: int,
    payload: AcceptEligibleHighConfidenceRequest,
    db: Session = Depends(get_db),
):
    run = db.get(ProfileExtractionRun, run_id)
    if not run:
        raise HTTPException(404, "Extraction run not found")
    proposals = _proposals_for_run(run.id, db)
    proposal_ids = payload.proposal_ids or [
        item.id for item in proposals
        if item.review_status == "pending"
        and item.confidence >= get_settings().profile_extraction_high_confidence
    ]
    if not proposal_ids:
        raise HTTPException(422, "No high-confidence proposals were selected")
    return _apply_batch_review(
        run,
        BatchReviewRequest(
            proposal_ids=proposal_ids,
            action="accept",
            confirmation=payload.confirmation,
        ),
        db,
        high_confidence_workflow=True,
    )


@router.post("/profile-extraction-runs/{run_id}/review-events", status_code=204)
def record_review_event(
    run_id: int,
    payload: ReviewEventRequest,
    db: Session = Depends(get_db),
):
    run = db.get(ProfileExtractionRun, run_id)
    if not run:
        raise HTTPException(404, "Extraction run not found")
    metadata = {
        "run_id": run.id,
        "queue": payload.queue,
        "proposal_id": payload.proposal_id,
        "document_id": payload.document_id,
        "selected_count": payload.selected_count,
    }
    db.add(AuditEvent(
        event_type=payload.event_type,
        machine_profile_id=run.machine_profile_id,
        metadata_json={
            key: value for key, value in metadata.items() if value is not None
        },
    ))
    db.commit()


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

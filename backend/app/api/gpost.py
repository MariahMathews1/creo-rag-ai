import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.gpost.service import (
    SAFETY_NOTICE, audit, capability_snapshot, compare_drafts, default_templates,
    controller_family_compatible, family_compatible, generate_preview, initial_mappings, markdown_export, review_summary,
    revision_snapshot, snapshot_draft, validate_ownership,
)
from app.models.entities import DocumentChunk, MachineProfile, SourceDocument, utc_now
from app.models.gpost import GPostDraft, GPostDraftVersion, GPostMapping, GPostMappingEvidence, GPostPreviewRun
from app.models.profile_extraction import MachineProfileRevision
from app.models.program_standards import ReferenceProgram, StandardConvention
from app.schemas.gpost import (
    GPostDraftCreate, GPostDraftRead, GPostDraftUpdate, GPostEvidenceCreate, GPostEvidenceRead, GPostMappingCreate,
    GPostMappingRead, GPostMappingUpdate, PreviewRead, PreviewRequest,
    RndValidationRequest, VersionCompareRead,
)

router = APIRouter(tags=["G-POST Generator"])


def draft_or_404(draft_id: int, db: Session) -> GPostDraft:
    draft = db.get(GPostDraft, draft_id)
    if draft is None:
        raise HTTPException(404, "G-POST draft not found")
    return draft


def mapping_or_404(mapping_id: int, db: Session) -> GPostMapping:
    mapping = db.scalar(select(GPostMapping).options(selectinload(GPostMapping.evidence)).where(GPostMapping.id == mapping_id))
    if mapping is None:
        raise HTTPException(404, "G-POST mapping not found")
    return mapping


def ownership_error(callable_):
    try:
        return callable_()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/machines/{machine_id}/gpost-drafts", response_model=GPostDraftRead, status_code=status.HTTP_201_CREATED)
def create_draft(machine_id: int, payload: GPostDraftCreate, db: Session = Depends(get_db)):
    machine = db.get(MachineProfile, machine_id)
    if machine is None:
        raise HTTPException(404, "Machine profile not found")
    revision = ownership_error(lambda: validate_ownership(
        db, machine_id, payload.machine_profile_revision_id, payload.selected_document_ids,
        payload.standard_profile_id, payload.reference_program_ids,
    ))
    machine_type = revision.machine_type or machine.machine_type.value
    templates = default_templates(revision, payload.controller_family)
    warnings = []
    if not family_compatible(machine_type, payload.controller_family):
        warnings.append({"category": "Blocking Setup Issue", "code": "GPOST_TEMPLATE_FAMILY_MISMATCH", "message": "Machine type and controller template family conflict."})
    if not controller_family_compatible(revision, payload.controller_family):
        warnings.append({"category": "Blocking Setup Issue", "code": "GPOST_CONTROLLER_FAMILY_MISMATCH", "message": "Controller identity and controller template family conflict."})
    capabilities = capability_snapshot(revision)
    if capabilities["unknown_capabilities"]:
        warnings.append({"category": "Missing Documentation", "message": "Unknown capabilities: " + ", ".join(capabilities["unknown_capabilities"])})
    draft = GPostDraft(
        machine_profile_id=machine_id, machine_profile_revision_id=revision.id,
        name=payload.name, version=1, status="review_required",
        controller_family=payload.controller_family, machine_type=machine_type,
        selected_document_ids_json=payload.selected_document_ids,
        standard_profile_id=payload.standard_profile_id,
        reference_program_ids_json=payload.reference_program_ids,
        manual_configuration_acknowledged=payload.manual_configuration_acknowledged,
        capability_snapshot_json=capabilities,
        machine_profile_snapshot_json=revision_snapshot(revision, machine),
        templates_json=templates,
        unsupported_features_json=sorted(["CIRCLE", "ARC", "CYCLE", "CUTCOM", "MULTAX", "TLAXIS", "GOHOME", "OPSTOP"]),
        warnings_json=warnings,
        review_summary_json={},
    )
    db.add(draft); db.flush()
    db.add_all(initial_mappings(draft))
    db.flush()
    mappings = list(db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == draft.id)))
    draft.review_summary_json = review_summary(mappings)
    db.add(GPostDraftVersion(gpost_draft_id=draft.id, version=1, snapshot_json=snapshot_draft(draft, mappings), change_summary_json={"created": True}))
    audit(db, "gpost_draft_created", draft, version=1)
    if payload.selected_document_ids:
        audit(db, "gpost_document_reference_added", draft, document_ids=payload.selected_document_ids)
    db.commit(); db.refresh(draft)
    return draft


@router.get("/machines/{machine_id}/gpost-drafts", response_model=list[GPostDraftRead])
def list_drafts(machine_id: int, db: Session = Depends(get_db)):
    if db.get(MachineProfile, machine_id) is None:
        raise HTTPException(404, "Machine profile not found")
    return list(db.scalars(select(GPostDraft).where(GPostDraft.machine_profile_id == machine_id).order_by(GPostDraft.updated_at.desc())))


@router.get("/gpost-drafts/{draft_id}", response_model=GPostDraftRead)
def get_draft(draft_id: int, db: Session = Depends(get_db)):
    return draft_or_404(draft_id, db)


@router.put("/gpost-drafts/{draft_id}", response_model=GPostDraftRead)
def update_draft(draft_id: int, payload: GPostDraftUpdate, db: Session = Depends(get_db)):
    draft = draft_or_404(draft_id, db)
    if draft.status in {"superseded", "archived"}:
        raise HTTPException(409, "Historical or archived G-POST drafts cannot be overwritten")
    data = payload.model_dump(exclude_unset=True)
    document_ids = data.pop("selected_document_ids", draft.selected_document_ids_json)
    reference_ids = data.pop("reference_program_ids", draft.reference_program_ids_json)
    standard_id = data.get("standard_profile_id", draft.standard_profile_id)
    ownership_error(lambda: validate_ownership(db, draft.machine_profile_id, draft.machine_profile_revision_id, document_ids, standard_id, reference_ids))
    added_documents = sorted(set(document_ids) - set(draft.selected_document_ids_json))
    draft.selected_document_ids_json = document_ids
    draft.reference_program_ids_json = reference_ids
    for key, value in data.items():
        if key == "status" and value == "validated_for_rnd":
            raise HTTPException(422, "Use the R&D validation endpoint with explicit acknowledgement")
        setattr(draft, key, value)
    if added_documents:
        audit(db, "gpost_document_reference_added", draft, document_ids=added_documents)
    db.commit(); db.refresh(draft)
    return draft


@router.post("/gpost-drafts/{draft_id}/versions", response_model=GPostDraftRead, status_code=status.HTTP_201_CREATED)
def create_version(draft_id: int, db: Session = Depends(get_db)):
    old = draft_or_404(draft_id, db)
    next_version = (db.scalar(select(func.max(GPostDraft.version)).where(GPostDraft.machine_profile_id == old.machine_profile_id, GPostDraft.name == old.name)) or 0) + 1
    new = GPostDraft(
        machine_profile_id=old.machine_profile_id, machine_profile_revision_id=old.machine_profile_revision_id,
        created_from_draft_id=old.id, name=old.name, version=next_version, status="review_required",
        controller_family=old.controller_family, machine_type=old.machine_type,
        selected_document_ids_json=list(old.selected_document_ids_json), standard_profile_id=old.standard_profile_id,
        reference_program_ids_json=list(old.reference_program_ids_json), capability_snapshot_json=dict(old.capability_snapshot_json),
        manual_configuration_acknowledged=old.manual_configuration_acknowledged,
        machine_profile_snapshot_json=dict(old.machine_profile_snapshot_json), templates_json=dict(old.templates_json),
        unsupported_features_json=list(old.unsupported_features_json), warnings_json=list(old.warnings_json),
        review_summary_json=dict(old.review_summary_json),
    )
    db.add(new); db.flush()
    originals = list(db.scalars(select(GPostMapping).options(selectinload(GPostMapping.evidence)).where(GPostMapping.gpost_draft_id == old.id)))
    for item in originals:
        clone = GPostMapping(gpost_draft_id=new.id, **{key: getattr(item, key) for key in (
            "mapping_key", "cl_command", "mapping_type", "output_template", "template_key", "template_override",
            "uses_override", "support_status", "required_for_v1", "description", "conditions_json", "required_state_json",
            "resulting_state_json", "machine_type_scope", "dialect_scope", "supported", "confidence", "source_type",
            "source_document_id", "source_chunk_id", "source_page", "source_section", "source_excerpt", "source_authority",
            "review_status", "review_note")})
        db.add(clone); db.flush()
        for evidence in item.evidence:
            db.add(GPostMappingEvidence(gpost_mapping_id=clone.id, **{key: getattr(evidence, key) for key in (
                "source_type", "document_id", "document_chunk_id", "reference_program_id", "standard_convention_id",
                "page", "section", "excerpt", "authority_level", "metadata_json")}))
    old.status = "superseded"; old.superseded_at = utc_now()
    db.flush()
    copied = list(db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == new.id)))
    db.add(GPostDraftVersion(gpost_draft_id=new.id, version=next_version, snapshot_json=snapshot_draft(new, copied), change_summary_json={"created_from_draft_id": old.id}))
    audit(db, "gpost_version_created", new, created_from_draft_id=old.id, version=next_version)
    db.commit(); db.refresh(new)
    return new


@router.post("/gpost-drafts/{draft_id}/archive", response_model=GPostDraftRead)
def archive_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = draft_or_404(draft_id, db); draft.status = "archived"; db.commit(); db.refresh(draft); return draft


@router.get("/gpost-drafts/{draft_id}/mappings", response_model=list[GPostMappingRead])
def list_mappings(draft_id: int, db: Session = Depends(get_db)):
    draft_or_404(draft_id, db)
    return list(db.scalars(select(GPostMapping).options(selectinload(GPostMapping.evidence)).where(GPostMapping.gpost_draft_id == draft_id).order_by(GPostMapping.cl_command)))


def validate_mapping_source(db: Session, draft: GPostDraft, document_id: int | None, chunk_id: int | None):
    if document_id is None and chunk_id is None:
        return
    document = db.get(SourceDocument, document_id) if document_id else None
    chunk = db.get(DocumentChunk, chunk_id) if chunk_id else None
    if document is None or document.machine_profile_id != draft.machine_profile_id or document.id not in draft.selected_document_ids_json:
        raise HTTPException(422, "Mapping evidence must be a selected document owned by this draft's machine")
    if chunk_id and (chunk is None or chunk.document_id != document.id or chunk.machine_profile_id != draft.machine_profile_id):
        raise HTTPException(422, "Evidence chunk does not belong to the selected machine document")


@router.post("/gpost-drafts/{draft_id}/mappings", response_model=GPostMappingRead, status_code=status.HTTP_201_CREATED)
def create_mapping(draft_id: int, payload: GPostMappingCreate, db: Session = Depends(get_db)):
    draft = draft_or_404(draft_id, db)
    validate_mapping_source(db, draft, payload.source_document_id, payload.source_chunk_id)
    mapping = GPostMapping(gpost_draft_id=draft.id, **payload.model_dump())
    db.add(mapping); db.flush(); audit(db, "gpost_mapping_created", draft, mapping_id=mapping.id, cl_command=mapping.cl_command)
    db.commit(); return mapping_or_404(mapping.id, db)


@router.put("/gpost-mappings/{mapping_id}", response_model=GPostMappingRead)
def update_mapping(mapping_id: int, payload: GPostMappingUpdate, db: Session = Depends(get_db)):
    mapping = mapping_or_404(mapping_id, db); draft = draft_or_404(mapping.gpost_draft_id, db)
    if draft.status in {"superseded", "archived"}:
        raise HTTPException(409, "Historical or archived mappings cannot be overwritten")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("support_status") == "not_applicable" and mapping.required_for_v1 and not changes.get("review_note"):
        raise HTTPException(422, "Required V1 behavior needs an explicit capability reason before it can be marked not applicable")
    if "output_template" in changes and "template_override" not in changes:
        changes["template_override"] = changes.pop("output_template")
        changes["uses_override"] = True
    document_id = changes.get("source_document_id", mapping.source_document_id)
    chunk_id = changes.get("source_chunk_id", mapping.source_chunk_id)
    validate_mapping_source(db, draft, document_id, chunk_id)
    old_status = mapping.review_status
    for key, value in changes.items(): setattr(mapping, key, value)
    mapping.supported = mapping.support_status == "supported"
    if mapping.uses_override and mapping.template_override is None:
        raise HTTPException(422, "A mapping override requires template_override text")
    all_mappings = list(db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == draft.id)))
    draft.review_summary_json = review_summary(all_mappings)
    event = {"accepted": "gpost_mapping_accepted", "accepted_with_edit": "gpost_mapping_edited", "rejected": "gpost_mapping_rejected"}.get(mapping.review_status, "gpost_mapping_edited")
    audit(db, event, draft, mapping_id=mapping.id, previous_review_status=old_status, review_status=mapping.review_status)
    db.commit(); return mapping_or_404(mapping.id, db)


@router.post("/gpost-mappings/{mapping_id}/reset-override", response_model=GPostMappingRead)
def reset_mapping_override(mapping_id: int, db: Session = Depends(get_db)):
    mapping = mapping_or_404(mapping_id, db); draft = draft_or_404(mapping.gpost_draft_id, db)
    if draft.status in {"superseded", "archived"}:
        raise HTTPException(409, "Historical or archived mappings cannot be overwritten")
    mapping.template_override = None
    mapping.uses_override = False
    if mapping.review_status == "accepted_with_edit":
        mapping.review_status = "pending"
    mappings = list(db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == draft.id)))
    draft.review_summary_json = review_summary(mappings)
    audit(db, "gpost_mapping_override_reset", draft, mapping_id=mapping.id)
    db.commit()
    return mapping_or_404(mapping.id, db)


@router.post("/gpost-mappings/{mapping_id}/evidence", response_model=GPostEvidenceRead, status_code=status.HTTP_201_CREATED)
def add_mapping_evidence(mapping_id: int, payload: GPostEvidenceCreate, db: Session = Depends(get_db)):
    mapping = mapping_or_404(mapping_id, db); draft = draft_or_404(mapping.gpost_draft_id, db)
    if payload.source_type == "document":
        validate_mapping_source(db, draft, payload.document_id, payload.document_chunk_id)
    elif payload.source_type == "reference_program":
        program = db.get(ReferenceProgram, payload.reference_program_id) if payload.reference_program_id else None
        if program is None or program.machine_profile_id != draft.machine_profile_id or program.id not in draft.reference_program_ids_json:
            raise HTTPException(422, "Reference-program evidence must be selected and owned by this draft's machine")
    elif payload.source_type == "standard_convention":
        convention = db.get(StandardConvention, payload.standard_convention_id) if payload.standard_convention_id else None
        if convention is None or convention.standard_profile_id != draft.standard_profile_id:
            raise HTTPException(422, "Standard evidence must belong to the draft's selected standard profile")
    evidence = GPostMappingEvidence(gpost_mapping_id=mapping.id, **payload.model_dump())
    db.add(evidence); audit(db, "gpost_mapping_edited", draft, mapping_id=mapping.id, evidence_source_type=payload.source_type)
    db.commit(); db.refresh(evidence); return evidence


@router.post("/gpost-drafts/{draft_id}/preview", response_model=PreviewRead)
def preview(draft_id: int, payload: PreviewRequest, db: Session = Depends(get_db)):
    return generate_preview(db, draft_or_404(draft_id, db), payload.cl_source)


@router.get("/gpost-drafts/{draft_id}/warnings")
def warnings(draft_id: int, db: Session = Depends(get_db)):
    draft = draft_or_404(draft_id, db)
    latest = db.scalar(select(GPostPreviewRun).where(GPostPreviewRun.gpost_draft_id == draft.id).order_by(GPostPreviewRun.created_at.desc()))
    return {"configuration": draft.warnings_json, "preview": latest.warnings_json if latest else []}


@router.get("/gpost-drafts/{draft_id}/traceability")
def traceability(draft_id: int, db: Session = Depends(get_db)):
    draft_or_404(draft_id, db)
    latest = db.scalar(select(GPostPreviewRun).where(GPostPreviewRun.gpost_draft_id == draft_id).order_by(GPostPreviewRun.created_at.desc()))
    return {"preview_run_id": latest.id if latest else None, "traceability": latest.traceability_json if latest else [], "safety_notice": SAFETY_NOTICE}


@router.post("/gpost-drafts/{draft_id}/validate-for-rnd", response_model=GPostDraftRead)
def validate_for_rnd(draft_id: int, payload: RndValidationRequest, db: Session = Depends(get_db)):
    draft = draft_or_404(draft_id, db)
    latest = db.scalar(select(GPostPreviewRun).where(GPostPreviewRun.gpost_draft_id == draft.id).order_by(GPostPreviewRun.created_at.desc()))
    if not payload.acknowledge_rnd_only:
        raise HTTPException(422, "R&D-only acknowledgement is required")
    if latest is None or not latest.summary_json.get("can_validate_for_rnd"):
        raise HTTPException(409, "The latest preview does not meet R&D validation criteria")
    draft.status = "validated_for_rnd"; db.commit(); db.refresh(draft); return draft


@router.get("/gpost-drafts/{draft_id}/compare/{other_draft_id}", response_model=VersionCompareRead)
def compare(draft_id: int, other_draft_id: int, db: Session = Depends(get_db)):
    left, right = draft_or_404(draft_id, db), draft_or_404(other_draft_id, db)
    if left.machine_profile_id != right.machine_profile_id or left.name != right.name:
        raise HTTPException(422, "Only versions of the same machine-scoped draft can be compared")
    return compare_drafts(db, left, right)


@router.get("/gpost-drafts/{draft_id}/export")
def export_draft(draft_id: int, format: str = Query("json", pattern="^(json|markdown)$"), db: Session = Depends(get_db)):
    draft = draft_or_404(draft_id, db)
    mappings = list(db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == draft.id).order_by(GPostMapping.cl_command)))
    audit(db, "gpost_exported", draft, format=format); db.commit()
    if format == "markdown":
        return Response(markdown_export(draft, mappings), media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="gpost-draft-v{draft.version}.md"'})
    payload = snapshot_draft(draft, mappings)
    payload.update({"machine_profile_snapshot": draft.machine_profile_snapshot_json, "capability_snapshot": draft.capability_snapshot_json,
                    "unsupported_features": draft.unsupported_features_json, "safety_notice": SAFETY_NOTICE,
                    "labels": ["R&D ONLY", "NON-PRODUCTION", "NOT VALIDATED FOR MACHINE USE"]})
    return Response(json.dumps(payload, indent=2, default=str), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="gpost-draft-v{draft.version}.json"'})

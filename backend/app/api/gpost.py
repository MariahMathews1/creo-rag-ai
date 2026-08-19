from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.gpost.service import (
    SAFETY_NOTICE, audit, capability_snapshot, compare_drafts, default_templates,
    controller_family_compatible, current_cl_preflight, family_compatible, generate_preview, initial_mappings, review_summary,
    revision_snapshot, snapshot_draft, validate_ownership,
)
from app.gpost.exporters import get_post_draft_exporter
from app.models.entities import DocumentChunk, MachineProfile, SourceDocument, utc_now
from app.models.gpost import GPostDraft, GPostDraftVersion, GPostMapping, GPostMappingEvidence, GPostPreviewRun, PostRuleDraft, PostSectionDraft
from app.models.profile_extraction import MachineProfileRevision
from app.models.program_standards import ReferenceProgram, StandardConvention
from app.models.translation import TranslationAlignment, TranslationAlignmentLink, TranslationExample
from app.translation.service import normalize_cl_pattern, normalize_gcode_pattern
from app.schemas.gpost import (
    GPostDraftCreate, GPostDraftRead, GPostDraftUpdate, GPostEvidenceCreate, GPostEvidenceRead, GPostMappingCreate, GPostPreflightRead,
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


@router.get("/gpost-mappings/{mapping_id}/historical-translation-evidence")
def historical_translation_evidence(mapping_id: int, db: Session = Depends(get_db)):
    mapping = mapping_or_404(mapping_id, db)
    draft = draft_or_404(mapping.gpost_draft_id, db)
    examples = list(db.scalars(select(TranslationExample).options(
        selectinload(TranslationExample.alignments).selectinload(TranslationAlignment.links)
    ).where(TranslationExample.machine_profile_id == draft.machine_profile_id,
            TranslationExample.verification_status == "verified_successful")).unique())
    rows = []
    for example in examples:
        for alignment in example.alignments:
            for link in alignment.links:
                if link.review_status not in {"confirmed", "edited"} or link.cl_record_start is None or link.gcode_block_start is None:
                    continue
                cl = example.parsed_cl_records_json[link.cl_record_start]
                if cl.get("command") != mapping.cl_command: continue
                gc = example.parsed_gcode_blocks_json[link.gcode_block_start]
                rows.append({"translation_example_id": example.id, "name": example.name,
                    "post_revision": example.post_processor_revision, "operation": example.operation_type,
                    "cl_pattern": normalize_cl_pattern(cl["text"]),
                    "gcode_pattern": normalize_gcode_pattern(gc["text"], cl["command"])})
    return {"mapping_id": mapping.id, "machine_profile_id": draft.machine_profile_id,
            "cl_command": mapping.cl_command, "verified_example_count": len({row["translation_example_id"] for row in rows}),
            "observations": rows, "read_only": True, "mapping_changed": False}


def ownership_error(callable_):
    try:
        return callable_()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def logical_post_versions(db: Session, draft: GPostDraft) -> list[GPostDraft]:
    """Return only the connected version lineage for one logical post."""
    candidates = list(db.scalars(select(GPostDraft).where(GPostDraft.machine_profile_id == draft.machine_profile_id)))
    connected = {draft.id}
    changed = True
    while changed:
        changed = False
        for item in candidates:
            if item.id in connected or item.created_from_draft_id in connected:
                before = len(connected); connected.add(item.id)
                if item.created_from_draft_id is not None: connected.add(item.created_from_draft_id)
                changed = changed or len(connected) != before
    return sorted((item for item in candidates if item.id in connected), key=lambda item: item.version, reverse=True)


def latest_section_rows(db: Session, draft_id: int) -> list[PostSectionDraft]:
    return list(db.scalars(select(PostSectionDraft).options(selectinload(PostSectionDraft.rules)).where(
        PostSectionDraft.gpost_draft_id == draft_id,
        PostSectionDraft.id.in_(select(func.max(PostSectionDraft.id)).where(
            PostSectionDraft.gpost_draft_id == draft_id).group_by(PostSectionDraft.section_key)),
    )).unique())


def version_snapshot(db: Session, draft: GPostDraft) -> dict:
    mappings = list(db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == draft.id)))
    snapshot = snapshot_draft(draft, mappings)
    snapshot["post_sections"] = [{
        "section_key": section.section_key, "section_version": section.section_version, "status": section.status,
        "rules": [{"rule_key": rule.rule_key, "status": rule.status,
                   "template": rule.engineer_template or rule.ai_draft_template,
                   "evidence_ids": rule.evidence_ids_json} for rule in section.rules],
    } for section in sorted(latest_section_rows(db, draft.id), key=lambda item: item.section_key)]
    return snapshot


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
    db.add(GPostDraftVersion(gpost_draft_id=draft.id, version=1, snapshot_json=version_snapshot(db, draft), change_summary_json={"created": True}))
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


@router.get("/gpost-drafts/{draft_id}/versions", response_model=list[GPostDraftRead])
def list_versions(draft_id: int, db: Session = Depends(get_db)):
    return logical_post_versions(db, draft_or_404(draft_id, db))


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
    lineage = logical_post_versions(db, old)
    latest_saved = db.scalar(select(GPostDraftVersion).where(GPostDraftVersion.gpost_draft_id == old.id).order_by(GPostDraftVersion.created_at.desc()))
    current_snapshot = version_snapshot(db, old)
    if latest_saved:
        saved = dict(latest_saved.snapshot_json)
        saved.setdefault("post_sections", [])
        if current_snapshot == saved:
            raise HTTPException(409, {"code": "GPOST_NO_VERSION_CHANGES", "message": f"No changes since v{old.version}."})
    next_version = max(item.version for item in lineage) + 1
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
    section_rows = latest_section_rows(db, old.id)
    for section in section_rows:
        section_clone = PostSectionDraft(gpost_draft_id=new.id, section_key=section.section_key, section_version=section.section_version,
            status=section.status, source_type="whole_post_version_snapshot", machine_context_snapshot_json=dict(section.machine_context_snapshot_json),
            draft_templates_json=list(section.draft_templates_json), missing_information_json=list(section.missing_information_json),
            assumptions_json=list(section.assumptions_json), warnings_json=list(section.warnings_json), source_evidence_json=list(section.source_evidence_json),
            ai_generated=section.ai_generated, provider=section.provider, model=section.model, prompt_version=section.prompt_version,
            response_schema_version=section.response_schema_version, reviewed_at=section.reviewed_at)
        db.add(section_clone); db.flush()
        for rule in section.rules:
            db.add(PostRuleDraft(post_section_draft_id=section_clone.id, rule_key=rule.rule_key, name=rule.name, description=rule.description,
                condition=rule.condition, output_behavior=rule.output_behavior, ai_draft_template=rule.ai_draft_template,
                engineer_template=rule.engineer_template, required_machine_facts_json=list(rule.required_machine_facts_json),
                evidence_ids_json=list(rule.evidence_ids_json), assumptions_json=list(rule.assumptions_json), warnings_json=list(rule.warnings_json),
                status=rule.status, review_reason=rule.review_reason, reviewer_label=rule.reviewer_label, reviewed_at=rule.reviewed_at))
    old.status = "superseded"; old.superseded_at = utc_now()
    db.flush()
    copied = list(db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == new.id)))
    snapshot = version_snapshot(db, new)
    snapshot["accepted_post_sections"] = [{"section_key": item.section_key, "section_version": item.section_version, "status": item.status,
        "rules": [{"rule_key": rule.rule_key, "status": rule.status, "template": rule.engineer_template or rule.ai_draft_template,
                   "evidence_ids": rule.evidence_ids_json, "reviewer": rule.reviewer_label} for rule in item.rules]}
        for item in section_rows if item.status == "accepted"]
    db.add(GPostDraftVersion(gpost_draft_id=new.id, version=next_version, snapshot_json=snapshot, change_summary_json={"created_from_draft_id": old.id, "post_sections_preserved": len(section_rows)}))
    audit(db, "gpost_version_created", new, created_from_draft_id=old.id, version=next_version)
    db.commit(); db.refresh(new)
    return new


@router.post("/gpost-drafts/{draft_id}/archive", response_model=GPostDraftRead)
def archive_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = draft_or_404(draft_id, db); draft.status = "archived"
    audit(db, "gpost_draft_archived", draft); db.commit(); db.refresh(draft); return draft


@router.post("/gpost-drafts/{draft_id}/duplicate", response_model=GPostDraftRead, status_code=status.HTTP_201_CREATED)
def duplicate_draft(draft_id: int, db: Session = Depends(get_db)):
    source = draft_or_404(draft_id, db)
    duplicate = GPostDraft(machine_profile_id=source.machine_profile_id, machine_profile_revision_id=source.machine_profile_revision_id,
        created_from_draft_id=None, name=f"{source.name} Copy", version=1, status="review_required",
        controller_family=source.controller_family, machine_type=source.machine_type,
        selected_document_ids_json=list(source.selected_document_ids_json), standard_profile_id=source.standard_profile_id,
        reference_program_ids_json=list(source.reference_program_ids_json), capability_snapshot_json=dict(source.capability_snapshot_json),
        manual_configuration_acknowledged=source.manual_configuration_acknowledged,
        machine_profile_snapshot_json=dict(source.machine_profile_snapshot_json), templates_json=dict(source.templates_json),
        unsupported_features_json=list(source.unsupported_features_json), warnings_json=list(source.warnings_json),
        review_summary_json=dict(source.review_summary_json))
    db.add(duplicate); db.flush()
    for item in db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == source.id)):
        db.add(GPostMapping(gpost_draft_id=duplicate.id, **{key: getattr(item, key) for key in (
            "mapping_key", "cl_command", "mapping_type", "output_template", "template_key", "template_override", "uses_override",
            "support_status", "required_for_v1", "description", "conditions_json", "required_state_json", "resulting_state_json",
            "machine_type_scope", "dialect_scope", "supported", "confidence", "source_type", "source_document_id", "source_chunk_id",
            "source_page", "source_section", "source_excerpt", "source_authority", "review_status", "review_note")}))
    for section in latest_section_rows(db, source.id):
        clone = PostSectionDraft(gpost_draft_id=duplicate.id, section_key=section.section_key, section_version=1,
            status=section.status, source_type="duplicated_post_configuration", machine_context_snapshot_json=dict(section.machine_context_snapshot_json),
            draft_templates_json=list(section.draft_templates_json), missing_information_json=list(section.missing_information_json),
            assumptions_json=list(section.assumptions_json), warnings_json=list(section.warnings_json), source_evidence_json=list(section.source_evidence_json),
            ai_generated=section.ai_generated, provider=section.provider, model=section.model, prompt_version=section.prompt_version,
            response_schema_version=section.response_schema_version, reviewed_at=section.reviewed_at)
        db.add(clone); db.flush()
        for rule in section.rules:
            db.add(PostRuleDraft(post_section_draft_id=clone.id, rule_key=rule.rule_key, name=rule.name, description=rule.description,
                condition=rule.condition, output_behavior=rule.output_behavior, ai_draft_template=rule.ai_draft_template,
                engineer_template=rule.engineer_template, required_machine_facts_json=list(rule.required_machine_facts_json),
                evidence_ids_json=list(rule.evidence_ids_json), assumptions_json=list(rule.assumptions_json), warnings_json=list(rule.warnings_json),
                status=rule.status, review_reason=rule.review_reason, reviewer_label=rule.reviewer_label, reviewed_at=rule.reviewed_at))
    db.flush()
    db.add(GPostDraftVersion(gpost_draft_id=duplicate.id, version=1, snapshot_json=version_snapshot(db, duplicate),
                             change_summary_json={"duplicated_from_draft_id": source.id}))
    audit(db, "gpost_draft_duplicated", duplicate, duplicated_from_draft_id=source.id)
    db.commit(); db.refresh(duplicate); return duplicate


@router.delete("/gpost-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = draft_or_404(draft_id, db)
    lineage = logical_post_versions(db, draft)
    if len(lineage) > 1 or draft.status == "superseded":
        raise HTTPException(409, {"code": "GPOST_DELETE_RETENTION_BLOCKED",
            "message": "This post has immutable version history and cannot be deleted. Archive it instead."})
    audit(db, "gpost_draft_deleted", draft, retained_audit=True)
    db.execute(delete(GPostDraftVersion).where(GPostDraftVersion.gpost_draft_id == draft.id))
    db.delete(draft); db.commit()


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


@router.post("/gpost-drafts/{draft_id}/preflight", response_model=GPostPreflightRead)
def preflight(draft_id: int, payload: PreviewRequest, db: Session = Depends(get_db)):
    return current_cl_preflight(db, draft_or_404(draft_id, db), payload.cl_source)


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
    sections = list(db.scalars(select(PostSectionDraft).options(selectinload(PostSectionDraft.rules)).where(
        PostSectionDraft.gpost_draft_id == draft.id,
        PostSectionDraft.id.in_(select(func.max(PostSectionDraft.id)).where(PostSectionDraft.gpost_draft_id == draft.id).group_by(PostSectionDraft.section_key)),
    ).order_by(PostSectionDraft.section_key)).unique())
    audit(db, "gpost_exported", draft, format=format); db.commit()
    exported = get_post_draft_exporter(format).export(draft, mappings, sections)
    return Response(exported.content, media_type=exported.media_type, headers={"Content-Disposition": f'attachment; filename="post-builder-draft-v{draft.version}.{exported.extension}"'})

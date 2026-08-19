import json
from hashlib import sha256
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ai.governance import AIGovernanceViolation, enforce_post_builder_ai_policy
from app.api.post_builder_ai import machine_context, provider_error
from app.db.session import get_db
from app.models.entities import AuditEvent, DocumentChunk, MachineProfile
from app.models.gpost import GPostDraft, GPostMapping, PostRuleDraft, PostSectionDraft
from app.models.profile_extraction import MachineProfileRevision
from app.models.translation_ai import AIInvocation
from app.post_builder_ai.provider import POST_BUILDER_PROMPT_VERSION, POST_BUILDER_RESPONSE_VERSION, get_post_builder_provider
from app.post_builder_ai.sections import SECTION_LABELS, PostBuilderEvidenceRetrievalService, section_readiness
from app.schemas.post_builder_ai import ApprovedDocumentExcerpt, PostBuilderRequest
from app.schemas.post_sections import (EvidenceSelectionRequest, PostBuilderEvidenceRead, PostRuleDraftRead,
    PostRuleReviewRequest, PostSectionCompareRead, PostSectionDraftRead, PostSectionGenerateRequest, PostSectionReadinessRead)
from app.translation_ai.provider import TranslationAIError
from app.models.entities import utc_now

router = APIRouter(prefix="/post-builder", tags=["Post Builder Sections"])
REQUIRED_COMPONENTS = tuple(key for key in SECTION_LABELS if key != "cycles")


def draft_or_404(draft_id: int, db: Session) -> GPostDraft:
    row = db.get(GPostDraft, draft_id)
    if row is None: raise HTTPException(404, "Post Builder draft not found")
    return row


def revision_for(draft: GPostDraft, db: Session) -> MachineProfileRevision:
    row = db.get(MachineProfileRevision, draft.machine_profile_revision_id)
    if row is None: raise HTTPException(409, "Machine profile revision is unavailable")
    return row


def validate_section(section: str) -> str:
    if section not in SECTION_LABELS: raise HTTPException(404, "Post section not found")
    return section


def section_row_or_404(draft_id: int, section: str, db: Session, version: int | None = None) -> PostSectionDraft:
    query = select(PostSectionDraft).options(selectinload(PostSectionDraft.rules)).where(PostSectionDraft.gpost_draft_id == draft_id, PostSectionDraft.section_key == section)
    query = query.where(PostSectionDraft.section_version == version) if version else query.order_by(PostSectionDraft.section_version.desc())
    row = db.scalar(query)
    if row is None: raise HTTPException(404, "Post section draft not found")
    return row


@router.get("/{draft_id}/readiness", response_model=list[PostSectionReadinessRead])
def readiness(draft_id: int, db: Session = Depends(get_db)):
    draft = draft_or_404(draft_id, db); revision = revision_for(draft, db)
    return [section_readiness(db, draft, revision, key) for key in SECTION_LABELS]


@router.get("/{draft_id}/sections", response_model=list[PostSectionDraftRead])
def list_sections(draft_id: int, db: Session = Depends(get_db)):
    draft_or_404(draft_id, db)
    return list(db.scalars(select(PostSectionDraft).options(selectinload(PostSectionDraft.rules)).where(PostSectionDraft.gpost_draft_id == draft_id).order_by(PostSectionDraft.section_key, PostSectionDraft.section_version.desc())).unique())


@router.get("/{draft_id}/assembled")
def assembled_post(draft_id: int, db: Session = Depends(get_db)):
    """Deterministically assemble the latest component states into one R&D post configuration."""
    draft = draft_or_404(draft_id, db); revision = revision_for(draft, db)
    rows = list(db.scalars(select(PostSectionDraft).options(selectinload(PostSectionDraft.rules)).where(
        PostSectionDraft.gpost_draft_id == draft.id).order_by(PostSectionDraft.section_version.desc())).unique())
    latest = {}
    for row in rows: latest.setdefault(row.section_key, row)
    evidence_rows = PostBuilderEvidenceRetrievalService(db).eligible_rows(draft)
    reviewed_rules = list(db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == draft.id,
        GPostMapping.review_status.in_(["accepted", "accepted_with_edit"]))))
    components = []
    for key, label in SECTION_LABELS.items():
        row = latest.get(key)
        readiness_state = section_readiness(db, draft, revision, key, evidence_rows, reviewed_rules, row)
        if key == "cycles": state = "deferred"
        elif row and row.status == "accepted": state = "reviewed"
        elif row and row.status == "needs_more_information": state = "needs_information"
        elif row: state = "needs_review"
        elif readiness_state["ai_drafting_readiness"] == "needs_information": state = "needs_information"
        else: state = "not_started"
        rules = [] if row is None else [{"rule_key": rule.rule_key, "name": rule.name, "condition": rule.condition,
            "template": rule.engineer_template or rule.ai_draft_template or rule.output_behavior, "status": rule.status,
            "evidence_ids": rule.evidence_ids_json, "reviewer": rule.reviewer_label} for rule in row.rules]
        components.append({"section_key": key, "label": label, "state": state, "required": key in REQUIRED_COMPONENTS,
            "section_version": row.section_version if row else None, "rules": rules,
            "missing_information": readiness_state["missing_information"] + ([] if row is None else row.missing_information_json),
            "evidence_count": readiness_state["evidence_count"]})
    counts = {state: sum(item["state"] == state for item in components) for state in
              ("reviewed", "needs_review", "needs_information", "not_started", "deferred")}
    required = [item for item in components if item["required"]]
    if draft.status == "archived": overall = "archived"
    elif all(item["state"] == "reviewed" for item in required): overall = "reviewed_rnd_draft"
    elif any(item["state"] == "needs_information" for item in required): overall = "needs_information"
    elif required and all(item["state"] in {"reviewed", "needs_review"} for item in required): overall = "ready_for_review"
    elif any(item["state"] != "not_started" for item in required): overall = "building"
    else: overall = "setup"
    return {"draft_id": draft.id, "name": draft.name, "status": overall, "required_area_count": len(REQUIRED_COMPONENTS),
        "counts": counts, "components": components, "ready_for_complete_review": overall == "reviewed_rnd_draft",
        "advisory_only": True, "native_gpost_export": "not_configured"}


@router.get("/{draft_id}/sections/{section_key}", response_model=PostSectionDraftRead)
def get_section(draft_id: int, section_key: str, db: Session = Depends(get_db)):
    draft_or_404(draft_id, db); return section_row_or_404(draft_id, validate_section(section_key), db)


@router.post("/{draft_id}/sections/{section_key}/retrieve-evidence", response_model=list[PostBuilderEvidenceRead])
def retrieve_evidence(draft_id: int, section_key: str, payload: EvidenceSelectionRequest, db: Session = Depends(get_db)):
    draft = draft_or_404(draft_id, db); section = validate_section(section_key)
    rows = PostBuilderEvidenceRetrievalService(db).retrieve(draft, section, payload.query)
    db.add(AuditEvent(event_type="post_builder_evidence_retrieved", machine_profile_id=draft.machine_profile_id,
        metadata_json={"post_draft_id": draft.id, "section": section, "evidence_ids": [row["evidence_id"] for row in rows], "provider_called": False}))
    db.commit(); return rows


@router.post("/{draft_id}/sections/{section_key}/draft", response_model=PostSectionDraftRead)
def generate_section(draft_id: int, section_key: str, raw_payload: dict, db: Session = Depends(get_db)):
    try: enforce_post_builder_ai_policy(raw_payload)
    except AIGovernanceViolation as exc:
        db.add(AuditEvent(event_type="post_builder_ai_request_blocked_by_policy", metadata_json={"code": "POST_BUILDER_POLICY_PROHIBITED_CONTENT", "reason": exc.code, "field": exc.field})); db.commit()
        raise HTTPException(422, {"code": "POST_BUILDER_POLICY_PROHIBITED_CONTENT", "message": exc.message, "field": exc.field})
    payload = PostSectionGenerateRequest.model_validate(raw_payload)
    if not payload.context_reviewed: raise HTTPException(422, {"code": "POST_BUILDER_CONTEXT_REVIEW_REQUIRED", "message": "Review AI context before drafting."})
    draft = draft_or_404(draft_id, db); section = validate_section(section_key); revision = revision_for(draft, db)
    state = section_readiness(db, draft, revision, section)
    if not state["draft_allowed"]: raise HTTPException(409, {"code": "POST_SECTION_NOT_READY", "message": "Resolve section readiness issues before drafting.", "readiness": state})
    eligible = PostBuilderEvidenceRetrievalService(db).retrieve(draft, section)
    by_id = {row["evidence_id"]: row for row in eligible}
    if any(value not in by_id for value in payload.evidence_ids): raise HTTPException(422, {"code": "POST_BUILDER_EVIDENCE_INVALID", "message": "Every selected evidence item must be eligible for this machine and section."})
    selected = [by_id[value] for value in payload.evidence_ids]
    existing = db.scalar(select(PostSectionDraft).options(selectinload(PostSectionDraft.rules)).where(PostSectionDraft.gpost_draft_id == draft.id,
        PostSectionDraft.section_key == section).order_by(PostSectionDraft.section_version.desc()))
    reviewed_rules = [] if not existing else [{"rule_key": rule.rule_key, "output_behavior": rule.engineer_template or rule.ai_draft_template}
        for rule in existing.rules if rule.status in {"accepted", "edited_and_accepted"}]
    provider_request = PostBuilderRequest(machine_profile_id=draft.machine_profile_id, machine_profile_revision_id=revision.id,
        post_draft_id=draft.id, selected_post_section=section, existing_reviewed_rules=reviewed_rules,
        relevant_document_excerpts=[ApprovedDocumentExcerpt(document_id=item["evidence_id"], excerpt=item["excerpt"], page=item["page_start"], section=item["section_title"], external_processing_approved=True) for item in selected])
    machine = db.get(MachineProfile, draft.machine_profile_id)
    context = machine_context(machine, revision, draft, section)
    outbound = {"request": provider_request.model_dump(), "machine_context": context}
    try: enforce_post_builder_ai_policy(outbound)
    except AIGovernanceViolation as exc: raise HTTPException(422, {"code": "POST_BUILDER_POLICY_PROHIBITED_CONTENT", "message": exc.message})
    provider = get_post_builder_provider(); input_hash = sha256(json.dumps(outbound, sort_keys=True, default=str).encode()).hexdigest()
    invocation = AIInvocation(provider=provider.name, operation_type="post_section_draft", machine_profile_id=draft.machine_profile_id,
        machine_profile_revision_id=revision.id, translation_example_ids_json=[], input_hash=input_hash,
        prompt_template_version=POST_BUILDER_PROMPT_VERSION, response_schema_version=POST_BUILDER_RESPONSE_VERSION,
        response_status="requested", external_processing=provider.external_processing,
        provider_metadata_json={"post_draft_id": draft.id, "post_draft_version": draft.version, "section": section, "evidence_ids": payload.evidence_ids})
    db.add(invocation); db.commit(); db.refresh(invocation); started = perf_counter()
    try: result = provider.draft_post_section(provider_request, context)
    except TranslationAIError as exc:
        invocation.response_status = exc.code; db.commit(); raise provider_error(exc)
    allowed = set(payload.evidence_ids); returned = set(result.payload.get("source_reference_ids", []))
    rule_refs = {evidence_id for rule in result.payload.get("draft_rules", []) for evidence_id in rule.get("evidence_reference_ids", [])}
    invalid = (returned | rule_refs) - allowed
    if invalid:
        invocation.response_status = "INVALID_AI_EVIDENCE_REFERENCE"; db.commit()
        raise HTTPException(422, {"code": "INVALID_AI_EVIDENCE_REFERENCE", "message": "Provider cited evidence that was not supplied."})
    next_version = (db.scalar(select(func.max(PostSectionDraft.section_version)).where(PostSectionDraft.gpost_draft_id == draft.id, PostSectionDraft.section_key == section)) or 0) + 1
    if existing and existing.status not in {"accepted", "edited_and_accepted"}: existing.status = "superseded"
    row = PostSectionDraft(gpost_draft_id=draft.id, section_key=section, section_version=next_version, status="needs_review",
        machine_context_snapshot_json=context, draft_templates_json=result.payload.get("draft_templates", []),
        missing_information_json=result.payload.get("missing_information", []), assumptions_json=result.payload.get("assumptions", []),
        warnings_json=result.payload.get("warnings", []), source_evidence_json=selected, provider=provider.name,
        model=result.provider_metadata.get("model"), prompt_version=POST_BUILDER_PROMPT_VERSION, response_schema_version=POST_BUILDER_RESPONSE_VERSION)
    db.add(row); db.flush()
    for item in result.payload.get("draft_rules", []):
        db.add(PostRuleDraft(post_section_draft_id=row.id, rule_key=item["rule_key"], name=item["name"],
            description=item.get("description"), condition=item["condition"], output_behavior=item["output_behavior"],
            ai_draft_template=item["output_behavior"], required_machine_facts_json=[], evidence_ids_json=item.get("evidence_reference_ids", []),
            assumptions_json=result.payload.get("assumptions", []), warnings_json=result.payload.get("warnings", []), status="needs_review"))
    invocation.duration_ms = round((perf_counter() - started) * 1000); invocation.response_status = "needs_review"
    invocation.provider_metadata_json = {**invocation.provider_metadata_json, **result.provider_metadata, "post_section_draft_id": row.id}
    invocation.token_usage_json = result.token_usage
    db.add(AuditEvent(event_type="post_section_drafted", machine_profile_id=draft.machine_profile_id, metadata_json={"post_draft_id": draft.id,
        "section": section, "section_version": next_version, "evidence_ids": payload.evidence_ids, "invocation_id": invocation.id, "input_hash": input_hash}))
    db.commit()
    return section_row_or_404(draft.id, section, db, next_version)


def _rule_and_section(draft_id: int, section: str, rule_id: int, db: Session):
    row = section_row_or_404(draft_id, validate_section(section), db)
    rule = next((item for item in row.rules if item.id == rule_id), None)
    if rule is None: raise HTTPException(404, "Post rule draft not found")
    return row, rule


def _review(draft_id: int, section: str, rule_id: int, action: str, payload: PostRuleReviewRequest, db: Session):
    row, rule = _rule_and_section(draft_id, section, rule_id, db)
    if action == "edit_accept" and not payload.edited_template: raise HTTPException(422, "Edited template is required")
    statuses = {"accept": "accepted", "edit_accept": "edited_and_accepted", "reject": "rejected", "needs_information": "needs_more_information"}
    rule.status = statuses[action]; rule.reviewer_label = payload.reviewer_label; rule.review_reason = payload.reason; rule.reviewed_at = utc_now()
    if action == "edit_accept": rule.engineer_template = payload.edited_template
    if action == "needs_information" and payload.reason and payload.reason not in row.missing_information_json:
        row.missing_information_json = [*row.missing_information_json, payload.reason]
    accepted = {"accepted", "edited_and_accepted"}
    row.status = "accepted" if row.rules and all(item.status in accepted for item in row.rules) else ("needs_more_information" if any(item.status == "needs_more_information" for item in row.rules) else "needs_review")
    if row.status == "accepted": row.reviewed_at = utc_now()
    draft = draft_or_404(draft_id, db)
    db.add(AuditEvent(event_type=f"post_rule_{action}", machine_profile_id=draft.machine_profile_id, metadata_json={"post_draft_id": draft.id,
        "section": section, "section_version": row.section_version, "rule_id": rule.id, "reviewer_label": payload.reviewer_label, "reason": payload.reason}))
    db.commit(); db.refresh(rule); return rule


@router.post("/{draft_id}/sections/{section_key}/rules/{rule_id}/accept", response_model=PostRuleDraftRead)
def accept_rule(draft_id: int, section_key: str, rule_id: int, payload: PostRuleReviewRequest, db: Session = Depends(get_db)): return _review(draft_id, section_key, rule_id, "accept", payload, db)

@router.post("/{draft_id}/sections/{section_key}/rules/{rule_id}/edit-accept", response_model=PostRuleDraftRead)
def edit_accept_rule(draft_id: int, section_key: str, rule_id: int, payload: PostRuleReviewRequest, db: Session = Depends(get_db)): return _review(draft_id, section_key, rule_id, "edit_accept", payload, db)

@router.post("/{draft_id}/sections/{section_key}/rules/{rule_id}/reject", response_model=PostRuleDraftRead)
def reject_rule(draft_id: int, section_key: str, rule_id: int, payload: PostRuleReviewRequest, db: Session = Depends(get_db)): return _review(draft_id, section_key, rule_id, "reject", payload, db)

@router.post("/{draft_id}/sections/{section_key}/rules/{rule_id}/needs-information", response_model=PostRuleDraftRead)
def needs_information_rule(draft_id: int, section_key: str, rule_id: int, payload: PostRuleReviewRequest, db: Session = Depends(get_db)): return _review(draft_id, section_key, rule_id, "needs_information", payload, db)

@router.get("/{draft_id}/sections/{section_key}/versions", response_model=list[PostSectionDraftRead])
def section_versions(draft_id: int, section_key: str, db: Session = Depends(get_db)):
    draft_or_404(draft_id, db); section = validate_section(section_key)
    return list(db.scalars(select(PostSectionDraft).options(selectinload(PostSectionDraft.rules)).where(PostSectionDraft.gpost_draft_id == draft_id, PostSectionDraft.section_key == section).order_by(PostSectionDraft.section_version.desc())).unique())


@router.get("/{draft_id}/sections/{section_key}/compare", response_model=PostSectionCompareRead)
def compare_sections(draft_id: int, section_key: str, left: int = Query(...), right: int = Query(...), db: Session = Depends(get_db)):
    a = section_row_or_404(draft_id, validate_section(section_key), db, left); b = section_row_or_404(draft_id, section_key, db, right)
    ar, br = {item.rule_key: item for item in a.rules}, {item.rule_key: item for item in b.rules}
    return {"left_version": left, "right_version": right, "rules_added": sorted(br.keys() - ar.keys()), "rules_removed": sorted(ar.keys() - br.keys()),
        "templates_changed": sorted(key for key in ar.keys() & br.keys() if ar[key].ai_draft_template != br[key].ai_draft_template),
        "evidence_changed": a.source_evidence_json != b.source_evidence_json, "assumptions_changed": a.assumptions_json != b.assumptions_json}

import json
from hashlib import sha256
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.governance import AIGovernanceViolation, enforce_post_builder_ai_policy
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import AuditEvent, MachineProfile, SourceDocument
from app.models.gpost import GPostDraft
from app.models.profile_extraction import MachineProfileRevision
from app.models.translation_ai import AIInvocation
from app.post_builder_ai.provider import POST_BUILDER_PROMPT_VERSION, POST_BUILDER_RESPONSE_VERSION, get_post_builder_provider
from app.schemas.post_builder_ai import PostBuilderProviderStatus, PostBuilderRequest, PostBuilderSectionResponse
from app.translation_ai.provider import TranslationAIError

router = APIRouter(prefix="/ai/post-builder", tags=["Post Builder AI"])


def policy_error(exc: AIGovernanceViolation) -> HTTPException:
    return HTTPException(422, {"code": exc.code, "message": exc.message, "field": exc.field})


def provider_error(exc: TranslationAIError) -> HTTPException:
    status = 503 if exc.retryable or exc.code in {"AI_PROVIDER_DISABLED", "PROVIDER_NOT_CONFIGURED", "PROVIDER_SDK_UNAVAILABLE"} else 422
    if exc.code == "PROVIDER_RATE_LIMITED": status = 429
    return HTTPException(status, {"code": exc.code, "message": exc.safe_message})


def machine_context(machine: MachineProfile, revision: MachineProfileRevision | None, draft: GPostDraft | None, section: str) -> dict:
    source = revision or machine
    common = {
        "machine": {"id": machine.id, "manufacturer": machine.manufacturer, "model": machine.model, "machine_type": str(machine.machine_type), "axis_count": machine.axis_count},
        "controller": {"name": source.controller_name, "manufacturer": source.controller_manufacturer, "model": source.controller_model, "version": source.controller_version},
        "units": getattr(source, "units", None),
    }
    section_fields = {
        "spindle": {"max_spindle_rpm": source.max_spindle_rpm, "approved_m_codes": getattr(source, "approved_m_codes_json", machine.approved_m_codes)},
        "feed": {"max_feed_rate": source.max_feed_rate, "feed_mode": getattr(source, "feed_mode", None)},
        "coordinates": {"work_offsets": getattr(source, "supported_work_offsets_json", machine.supported_work_offsets), "axis_travel": {axis: [getattr(source, f"{axis}_min", None), getattr(source, f"{axis}_max", None)] for axis in ("x", "y", "z")}},
        "cycles": {"approved_g_codes": getattr(source, "approved_g_codes_json", machine.approved_g_codes)},
    }
    template_keys = {
        "program_structure": ["program_header", "safe_start", "footer"], "tooling": ["tool_selection", "tool_change"],
        "spindle": ["spindle_start_cw", "spindle_start_ccw", "spindle_stop"], "coolant": ["coolant_on", "coolant_off"],
        "motion": ["rapid_move", "linear_feed_move"], "coordinates": ["units", "plane_selection", "distance_mode", "work_offset", "reference_return"],
        "feed": ["feed_mode", "feed_rate"], "cycles": ["canned_cycle", "cycle_cancel"], "program_end": ["program_end", "footer"],
    }
    templates = (draft.templates_json if draft else {}) or {}
    common["section_facts"] = section_fields.get(section, {})
    common["templates"] = {key: templates.get(key) for key in template_keys.get(section, []) if templates.get(key)}
    return common


@router.get("/provider-status", response_model=PostBuilderProviderStatus)
def provider_status(check_reachability: bool = Query(False), db: Session = Depends(get_db)):
    settings = get_settings(); provider = get_post_builder_provider(settings)
    status = provider.health_check() if provider.name != "azure_openai" or check_reachability else {"configured": bool(settings.azure_openai_endpoint and settings.azure_openai_deployment), "reachable": None, "authentication_mode": settings.azure_openai_auth_mode, "deployment": settings.azure_openai_deployment or None, "model": settings.azure_openai_model or None}
    db.add(AuditEvent(event_type="post_builder_provider_status_viewed", metadata_json={"provider": provider.name, "network_probe": bool(check_reachability)})); db.commit()
    return PostBuilderProviderStatus(provider=provider.name, external_processing=provider.external_processing, **status)


@router.post("/sections/draft", response_model=PostBuilderSectionResponse)
def draft_section(raw_payload: dict, db: Session = Depends(get_db)):
    try:
        enforce_post_builder_ai_policy(raw_payload)
        payload = PostBuilderRequest.model_validate(raw_payload)
    except AIGovernanceViolation as exc:
        db.add(AuditEvent(event_type="post_builder_ai_request_blocked_by_policy", metadata_json={"code": exc.code, "field": exc.field})); db.commit()
        raise policy_error(exc)
    except ValidationError as exc:
        raise HTTPException(422, {"code": "POST_BUILDER_REQUEST_INVALID", "message": "Post Builder request is invalid.", "errors": exc.errors()}) from exc
    machine = db.get(MachineProfile, payload.machine_profile_id)
    if machine is None: raise HTTPException(404, "Machine profile not found")
    revision = db.get(MachineProfileRevision, payload.machine_profile_revision_id) if payload.machine_profile_revision_id else None
    if revision and revision.machine_profile_id != machine.id: raise HTTPException(422, "Machine-profile revision does not belong to selected machine")
    draft = db.get(GPostDraft, payload.post_draft_id) if payload.post_draft_id else None
    if draft and draft.machine_profile_id != machine.id: raise HTTPException(422, "Post draft does not belong to selected machine")
    allowed_document_types = {"machine_manual", "controller_manual", "programming_manual", "post_processor_document", "operator_manual", "specification_document", "parameter_list", "machine_configuration_document"}
    for excerpt in payload.relevant_document_excerpts:
        document = db.get(SourceDocument, excerpt.document_id)
        if document is None or document.machine_profile_id != machine.id: raise HTTPException(422, {"code": "POST_BUILDER_DOCUMENT_SCOPE_INVALID", "message": "Every excerpt must belong to the selected machine."})
        if str(document.document_type) not in allowed_document_types and getattr(document.document_type, "value", None) not in allowed_document_types: raise HTTPException(422, {"code": "POST_BUILDER_DOCUMENT_TYPE_INVALID", "message": "Only machine-level documentation excerpts are allowed."})
    context = machine_context(machine, revision, draft, payload.selected_post_section)
    try: enforce_post_builder_ai_policy({"request": payload.model_dump(), "machine_context": context})
    except AIGovernanceViolation as exc: raise policy_error(exc)
    provider = get_post_builder_provider(); context_hash = sha256(json.dumps({"request": payload.model_dump(), "machine_context": context}, sort_keys=True).encode()).hexdigest()
    invocation = AIInvocation(provider=provider.name, operation_type="post_builder_section", machine_profile_id=machine.id,
        machine_profile_revision_id=revision.id if revision else None, translation_example_ids_json=[], input_hash=context_hash,
        prompt_template_version=POST_BUILDER_PROMPT_VERSION, response_schema_version=POST_BUILDER_RESPONSE_VERSION,
        response_status="requested", external_processing=provider.external_processing,
        provider_metadata_json={"post_draft_id": draft.id if draft else None, "section": payload.selected_post_section, "source_document_ids": [item.document_id for item in payload.relevant_document_excerpts]})
    db.add(invocation); db.add(AuditEvent(event_type="post_builder_section_requested", machine_profile_id=machine.id, metadata_json={"provider": provider.name, "post_draft_id": draft.id if draft else None, "section": payload.selected_post_section, "source_document_ids": [item.document_id for item in payload.relevant_document_excerpts], "input_hash": context_hash})); db.commit(); db.refresh(invocation)
    started = perf_counter()
    try:
        result = provider.draft_post_section(payload, context)
        invocation.duration_ms = round((perf_counter() - started) * 1000); invocation.response_status = str(result.payload["status"]); invocation.provider_metadata_json = {**invocation.provider_metadata_json, **result.provider_metadata}; invocation.token_usage_json = result.token_usage
        db.add(AuditEvent(event_type="post_builder_section_completed", machine_profile_id=machine.id, metadata_json={"invocation_id": invocation.id, "section": payload.selected_post_section})); db.commit()
        return PostBuilderSectionResponse(**result.payload, provider_metadata={**result.provider_metadata, "prompt_template_version": POST_BUILDER_PROMPT_VERSION, "response_schema_version": POST_BUILDER_RESPONSE_VERSION, "external_processing": provider.external_processing, "public_web": False}, invocation_id=invocation.id)
    except AIGovernanceViolation as exc:
        invocation.response_status = exc.code; db.commit(); raise policy_error(exc)
    except TranslationAIError as exc:
        invocation.duration_ms = round((perf_counter() - started) * 1000); invocation.response_status = exc.code; invocation.provider_metadata_json = {**invocation.provider_metadata_json, "error_code": exc.code}; db.commit(); raise provider_error(exc)

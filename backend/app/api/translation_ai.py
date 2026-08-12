from hashlib import sha256
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import AuditEvent, MachineProfile
from app.models.translation import TranslationAlignment, TranslationExample
from app.models.translation_ai import AIInvocation
from app.schemas.translation_ai import AIInvocationRead, ProviderStatus, TranslationExplanationRequest, TranslationExplanationResponse, TranslationRetrievalRequest, TranslationRetrievalResponse
from app.translation_ai.policy import AIProcessingPolicy
from app.translation_ai.prompt import TRANSLATION_AI_RESPONSE_SCHEMA_VERSION, TRANSLATION_EXPLANATION_PROMPT_VERSION, TranslationPromptBuilder
from app.translation_ai.provider import TranslationAIError, get_translation_provider
from app.translation_ai.retrieval import TranslationRetrievalService

router = APIRouter(prefix="/ai/translation", tags=["Translation AI"])


def audit(db: Session, event: str, machine_id: int | None = None, **metadata):
    db.add(AuditEvent(event_type=event, machine_profile_id=machine_id, metadata_json=metadata))


def safe_http_error(error: TranslationAIError) -> HTTPException:
    status = 503 if error.retryable else 422
    if error.code == "PROVIDER_RATE_LIMITED": status = 429
    if error.code in {"PROVIDER_AUTHENTICATION_FAILED", "PROVIDER_NOT_CONFIGURED", "PROVIDER_SDK_UNAVAILABLE"}: status = 503
    return HTTPException(status, {"code": error.code, "message": error.safe_message})


@router.get("/provider-status", response_model=ProviderStatus)
def provider_status(check_reachability: bool = Query(default=False), db: Session = Depends(get_db)):
    settings = get_settings(); provider = get_translation_provider(settings)
    if provider.name == "azure_openai" and not check_reachability:
        status = {"configured": bool(settings.azure_openai_endpoint and settings.azure_openai_deployment), "reachable": None, "authentication_mode": settings.azure_openai_auth_mode, "deployment": settings.azure_openai_deployment or None, "model": settings.azure_openai_model or None}
    else:
        status = provider.health_check()
    event = "azure_provider_health_checked" if provider.name == "azure_openai" and check_reachability else "translation_provider_status_viewed"
    audit(db, event, provider=provider.name, reachable=status.get("reachable"), network_probe=bool(provider.name == "azure_openai" and check_reachability)); db.commit()
    return ProviderStatus(provider=provider.name, external_processing=provider.external_processing, public_web=False, **status)


@router.post("/retrieve", response_model=TranslationRetrievalResponse)
def retrieve_examples(payload: TranslationRetrievalRequest, db: Session = Depends(get_db)):
    result = TranslationRetrievalService(db).retrieve(payload)
    audit(db, "translation_retrieval_run", payload.machine_profile_id, scope=result.retrieval_scope, example_ids=[item.example_id for item in result.examples], eligible_count=result.eligible_count, ai_called=False); db.commit()
    return result


@router.post("/explain", response_model=TranslationExplanationResponse)
def explain_translation(payload: TranslationExplanationRequest, db: Session = Depends(get_db)):
    settings = get_settings(); provider = get_translation_provider(settings); policy = AIProcessingPolicy()
    provider_decision = policy.provider_allowed(provider.name)
    if not provider_decision.allowed:
        audit(db, "translation_ai_request_blocked_by_policy", payload.retrieval.machine_profile_id, reason_code=provider_decision.reason_code); db.commit()
        raise HTTPException(422, {"code": provider_decision.reason_code, "message": provider_decision.explanation})
    machine = db.get(MachineProfile, payload.retrieval.machine_profile_id)
    if machine is None: raise HTTPException(404, "Machine profile not found")
    examples = list(db.scalars(select(TranslationExample).options(selectinload(TranslationExample.alignments).selectinload(TranslationAlignment.links)).where(TranslationExample.id.in_(payload.example_ids))))
    by_id = {row.id: row for row in examples}; examples = [by_id[value] for value in payload.example_ids if value in by_id]
    decision = policy.require_examples(examples, payload.retrieval.machine_profile_id, allow_machine_family_fallback=payload.retrieval.allow_machine_family_fallback, controller_name=machine.controller_name)
    if not decision.allowed:
        audit(db, "translation_ai_request_blocked_by_policy", machine.id, reason_code=decision.reason_code, requested_example_ids=payload.example_ids); db.commit()
        raise HTTPException(422, {"code": decision.reason_code, "message": decision.explanation})
    retrieved = TranslationRetrievalService(db).retrieve(payload.retrieval)
    eligible_ids = {item.example_id for item in retrieved.examples}
    if not set(payload.example_ids).issubset(eligible_ids):
        audit(db, "translation_ai_request_blocked_by_policy", machine.id, reason_code="AI_CONTEXT_SELECTION_INVALID", requested_example_ids=payload.example_ids, eligible_example_ids=sorted(eligible_ids)); db.commit()
        raise HTTPException(422, {"code": "AI_CONTEXT_SELECTION_INVALID", "message": "Every selected example must come from the current verified retrieval result."})
    prompt = TranslationPromptBuilder().build(machine=machine, revision_id=payload.retrieval.machine_profile_revision_id, cl_text=payload.retrieval.cl_text, examples=examples)
    invocation = AIInvocation(provider=provider.name, operation_type="translation_explanation", machine_profile_id=machine.id,
        machine_profile_revision_id=payload.retrieval.machine_profile_revision_id, translation_example_ids_json=prompt.example_ids,
        input_hash=sha256(payload.retrieval.cl_text.encode()).hexdigest(), prompt_template_version=TRANSLATION_EXPLANATION_PROMPT_VERSION,
        response_schema_version=TRANSLATION_AI_RESPONSE_SCHEMA_VERSION, response_status="requested", external_processing=provider.external_processing)
    db.add(invocation); audit(db, "translation_ai_explanation_requested", machine.id, provider=provider.name, example_ids=prompt.example_ids); db.commit(); db.refresh(invocation)
    start = perf_counter()
    try:
        result = provider.explain_translation(prompt, payload.retrieval.cl_text)
        invocation.duration_ms = round((perf_counter() - start) * 1000); invocation.response_status = str(result.payload.get("status", "completed")); invocation.provider_metadata_json = result.provider_metadata; invocation.token_usage_json = result.token_usage
        audit(db, "translation_ai_explanation_completed", machine.id, invocation_id=invocation.id, duration_ms=invocation.duration_ms); db.commit()
        return TranslationExplanationResponse(**result.payload, provider_metadata={**result.provider_metadata, "prompt_template_version": TRANSLATION_EXPLANATION_PROMPT_VERSION, "response_schema_version": TRANSLATION_AI_RESPONSE_SCHEMA_VERSION, "external_processing": provider.external_processing, "public_web": False}, invocation_id=invocation.id)
    except TranslationAIError as exc:
        invocation.duration_ms = round((perf_counter() - start) * 1000); invocation.response_status = exc.code; invocation.provider_metadata_json = {"provider": provider.name, "error_code": exc.code}
        event = "translation_ai_request_cancelled" if exc.code == "PROVIDER_CONTENT_FILTERED" else "translation_ai_explanation_failed"
        audit(db, event, machine.id, invocation_id=invocation.id, error_code=exc.code); db.commit()
        raise safe_http_error(exc)


@router.get("/invocations", response_model=list[AIInvocationRead])
def list_invocations(machine_profile_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    query = select(AIInvocation).order_by(AIInvocation.created_at.desc())
    if machine_profile_id is not None: query = query.where(AIInvocation.machine_profile_id == machine_profile_id)
    return list(db.scalars(query.limit(200)))


@router.get("/invocations/{invocation_id}", response_model=AIInvocationRead)
def get_invocation(invocation_id: int, db: Session = Depends(get_db)):
    row = db.get(AIInvocation, invocation_id)
    if row is None: raise HTTPException(404, "AI invocation not found")
    return row

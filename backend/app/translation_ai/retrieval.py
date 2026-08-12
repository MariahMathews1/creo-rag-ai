import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import MachineProfile
from app.models.translation import TranslationAlignment, TranslationExample
from app.schemas.translation_ai import RetrievedTranslationExample, TranslationRetrievalRequest, TranslationRetrievalResponse


def command_signature(text: str) -> set[str]:
    return {match.group(1).upper() for match in re.finditer(r"(?m)^\s*([A-Z][A-Z0-9_]*)\s*(?:/|$)", text.upper())}


def compact_excerpt(text: str, signatures: set[str], limit: int = 800) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    matching = [line for line in lines if line.split("/", 1)[0].strip().upper() in signatures]
    selected = matching[:8] or lines[:8]
    return "\n".join(selected)[:limit]


class TranslationRetrievalService:
    """Database-only retrieval. This service never invokes an AI provider."""

    def __init__(self, db: Session):
        self.db = db

    def retrieve(self, request: TranslationRetrievalRequest) -> TranslationRetrievalResponse:
        machine = self.db.get(MachineProfile, request.machine_profile_id)
        if machine is None:
            return TranslationRetrievalResponse(retrieval_scope="exact_machine", examples=[], eligible_count=0, warnings=["Machine profile not found."])
        authoritative_controller = machine.controller_name
        query = select(TranslationExample).options(
            selectinload(TranslationExample.alignments).selectinload(TranslationAlignment.links)
        ).where(
            TranslationExample.verification_status == "verified_successful",
            TranslationExample.ai_processing_allowed.is_(True),
        )
        if not request.allow_machine_family_fallback:
            query = query.where(TranslationExample.machine_profile_id == request.machine_profile_id)
        elif authoritative_controller:
            query = query.where(TranslationExample.controller_name == authoritative_controller)
        candidates = list(self.db.scalars(query.limit(10_000)))
        signature = command_signature(request.cl_text)
        scored: list[tuple[int, TranslationExample, list[str], str]] = []
        for row in candidates:
            reasons: list[str] = []
            score = 0
            if row.machine_profile_id == request.machine_profile_id:
                reasons.append("exact_machine"); score += 100
            elif request.allow_machine_family_fallback:
                reasons.append("explicit_machine_family_fallback"); score += 5
            else:
                continue
            if request.machine_profile_revision_id and row.machine_profile_revision_id == request.machine_profile_revision_id:
                reasons.append("exact_revision"); score += 20
            elif request.machine_profile_revision_id and not request.allow_revision_fallback:
                continue
            if request.post_processor_revision and row.post_processor_revision == request.post_processor_revision:
                reasons.append("exact_post_revision"); score += 30
            elif request.post_processor_revision and not request.allow_revision_fallback:
                continue
            if request.controller_name and row.controller_name == request.controller_name:
                reasons.append("exact_controller"); score += 15
            if request.operation_type and row.operation_type == request.operation_type:
                reasons.append("same_operation"); score += 15
            row_signature = command_signature(row.cl_source_text)
            overlap = signature & row_signature
            strength = "strong" if signature and signature <= row_signature else "related" if overlap else "none"
            if overlap:
                reasons.append("matching_cl_pattern"); score += 25 + len(overlap)
            if not reasons:
                continue
            scored.append((score, row, reasons, strength))
        scored.sort(key=lambda item: (-item[0], item[1].id))
        selected = scored[:request.max_examples]
        machine_ids = {row.machine_profile_id for _, row, _, _ in selected}
        machine_names = dict(self.db.execute(
            select(MachineProfile.id, MachineProfile.name).where(MachineProfile.id.in_(machine_ids))
        ).all()) if machine_ids else {}
        scope = "exact_machine_exact_post" if request.post_processor_revision and all("exact_post_revision" in item[2] for item in selected) else "same_machine_cross_post" if not request.allow_machine_family_fallback else "explicit_machine_family_same_controller"
        results = []
        for _, row, reasons, strength in selected:
            alignment = row.alignments[-1] if row.alignments else None
            results.append(RetrievedTranslationExample(
                example_id=row.id, name=row.name, machine_profile_id=row.machine_profile_id,
                machine=machine_names.get(row.machine_profile_id, f"Machine #{row.machine_profile_id}"),
                machine_profile_revision_id=row.machine_profile_revision_id,
                controller=row.controller_name, post_revision=row.post_processor_revision,
                operation=row.operation_type, cl_excerpt=compact_excerpt(row.cl_source_text, signature),
                gcode_excerpt=compact_excerpt(row.gcode_source_text, set()), cl_pattern_match=strength,
                alignment_coverage=float((alignment.summary_json if alignment else {}).get("coverage_percent", 0)),
                verification_status=row.verification_status, retrieval_reasons=reasons,
                ai_processing_allowed=row.ai_processing_allowed,
            ))
        warnings = [] if results else ["AI_CONTEXT_NOT_AVAILABLE: no verified, consented examples matched the selected scope."]
        if request.controller_name and request.controller_name != authoritative_controller:
            warnings.append("The request controller label was ignored; the selected machine profile is authoritative.")
        return TranslationRetrievalResponse(retrieval_scope=scope, examples=results, eligible_count=len(results), warnings=warnings)

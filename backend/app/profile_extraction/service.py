from dataclasses import dataclass
import re

from sqlalchemy import select
from sqlalchemy.orm import Session, defer

from app.core.config import Settings
from app.documents.retrieval import RetrievedChunk
from app.models.entities import AuditEvent, DocumentChunk, SourceDocument, utc_now
from app.models.profile_extraction import (
    ProfileExtractionRun, ProfileFieldEvidence, ProfileFieldProposal,
)
from app.profile_extraction.providers import (
    MockProfileExtractionProvider, OpenAICompatibleProfileExtractionProvider,
)
from app.profile_extraction.registry import FIELD_REGISTRY, ProfileFieldDefinition
from app.profile_extraction.units import normalize_physical_value, normalize_unit

UNIT_TEXT = (
    r"inches?\s+per\s+minute|inches?/min(?:ute)?|in/min|ipm|mm/min|"
    r"rpm|inches?|in\b|mm\b|hp\b|kw\b|kilograms?|kg\b|pounds?|lbs?\b"
)
NUMBER_UNIT = rf"([0-9][0-9,]*(?:\.[0-9]+)?)\s*({UNIT_TEXT})?"
PATTERNS = {
    "x_travel": rf"(?:x[- ]axis travel|x travel|x stroke|cross[- ]slide travel|cross[- ]slide stroke)\s*[:\-]?\s*{NUMBER_UNIT}",
    "y_travel": rf"(?:y[- ]axis travel|y travel|y stroke)\s*[:\-]?\s*{NUMBER_UNIT}",
    "z_travel": rf"(?:z[- ]axis travel|z travel|z stroke|longitudinal travel|longitudinal stroke)\s*[:\-]?\s*{NUMBER_UNIT}",
    "max_spindle_rpm": rf"(?:maximum spindle speed|max(?:imum)? spindle rpm)\s*[:\-]?\s*{NUMBER_UNIT}",
    "min_spindle_rpm": rf"(?:minimum spindle speed|min(?:imum)? spindle rpm)\s*[:\-]?\s*{NUMBER_UNIT}",
    "max_feed_rate": rf"(?:maximum cutting feed|max(?:imum)? feed rate)\s*[:\-]?\s*{NUMBER_UNIT}",
    "rapid_traverse_rate": rf"(?<!axis )(?<!axis-)(?:rapid traverse|rapid rate)\s*[:\-]?\s*{NUMBER_UNIT}",
    "turret_station_count": r"(?:turret stations?|station turret)\s*[:\-]?\s*([0-9]+)",
    "tool_capacity": r"(?:tool capacity|tool changer capacity)\s*[:\-]?\s*([0-9]+)",
    "tool_station_count": r"(?:tool[- ]post station count|tool station count|automatic tool post)\s*[:\-]?\s*([0-9]+|one|two|three|four|five|six|eight|ten|twelve)",
    "chuck_size": rf"(?:chuck size|chuck diameter)\s*[:\-]?\s*{NUMBER_UNIT}",
    "maximum_bar_capacity": rf"(?:maximum )?bar capacity\s*[:\-]?\s*{NUMBER_UNIT}",
    "spindle_bore": rf"(?:spindle bore|spindle through hole)\s*[:\-]?\s*{NUMBER_UNIT}",
    "spindle_power": rf"(?:standard )?(?:spindle motor power|spindle motor|spindle power)\s*[:\-]?\s*{NUMBER_UNIT}",
    "net_weight": rf"net weight\s*[:\-]?\s*{NUMBER_UNIT}",
    "gross_weight": rf"gross weight\s*[:\-]?\s*{NUMBER_UNIT}",
    "axis_count": r"axis count\s*[:\-]?\s*([0-9]+)",
}
STRING_PATTERNS = {
    "manufacturer": r"(?m)^\s*manufacturer\s*[:\-]\s*([^\n]+)",
    "model": r"(?m)^\s*(?:machine )?model\s*[:\-]\s*([^\n]+)",
    "machine_model": r"(?m)^\s*machine model\s*[:\-]\s*([^\n]+)",
    "controller_name": r"(?m)^\s*(?:controller name|controller|control system)\s*[:\-]\s*([^\n]+)",
    "controller_manufacturer": r"(?m)^\s*controller manufacturer\s*[:\-]\s*([^\n]+)",
    "controller_model": r"(?m)^\s*controller model\s*[:\-]\s*([^\n]+)",
    "controller_version": r"(?m)^\s*(?:controller|software) version\s*[:\-]\s*([^\n]+)",
    "machine_type": r"(?m)^\s*machine type\s*[:\-]\s*([^\n]+)",
    "spindle_nose": r"(?m)^\s*spindle nose\s*[:\-]\s*([^\n]+)",
    "spindle_taper": r"(?m)^\s*spindle taper\s*[:\-]\s*([^\n]+)",
}
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "eight": 8, "ten": 10, "twelve": 12,
}
MODEL_PATTERN = re.compile(r"\b[A-Z]{2,5}-\d{2,5}[A-Z]*\b")


@dataclass(slots=True)
class Candidate:
    value: object
    unit: str | None
    raw: str
    authority: float
    optional: bool
    chunk: DocumentChunk
    document_id: int
    document_type: str
    heading: str | None
    method: str


def _document_type_value(document_or_type) -> str:
    if isinstance(document_or_type, str):
        return document_or_type
    value = document_or_type.document_type
    return value.value if hasattr(value, "value") else str(value)


def _authority(document_type: str, definition: ProfileFieldDefinition) -> float:
    return 1.0 if document_type in definition.preferred_document_types else 0.75


def _extract_values(definition, chunk: DocumentChunk, document_or_type):
    """Legacy free-text fallback kept separate from structured key-value parsing."""
    document_type = _document_type_value(document_or_type)
    text = chunk.content
    values: list[tuple[object, str | None, str, float, bool]] = []
    if definition.field_key in PATTERNS:
        for match in re.finditer(PATTERNS[definition.field_key], text, re.I):
            raw = match.group(0)
            numeric_text = match.group(1).replace(",", "")
            if numeric_text.lower() in NUMBER_WORDS:
                value = NUMBER_WORDS[numeric_text.lower()]
            else:
                value = int(float(numeric_text)) if definition.data_type == "integer" else float(numeric_text)
            unit = normalize_unit(match.group(2) if len(match.groups()) > 1 else None)
            optional = bool(re.search(r"\b(optional|option|opt\.?|if equipped)\b", raw, re.I))
            values.append((value, unit, raw, _authority(document_type, definition), optional))
    elif definition.field_key in STRING_PATTERNS:
        match = re.search(STRING_PATTERNS[definition.field_key], text, re.I)
        if match:
            values.append((match.group(1).strip(" ."), None, match.group(0),
                           _authority(document_type, definition), False))
    elif definition.field_key == "supported_work_offsets":
        codes = sorted(set(re.findall(r"\bG5[4-9]\b|\bG54\.1\b", text.upper())))
        if codes:
            values.append((codes, None, " ".join(codes),
                           _authority(document_type, definition), False))
    elif definition.field_key in {"safe_start_template", "program_end_template"}:
        label = "safe start" if definition.field_key.startswith("safe") else "program end"
        match = re.search(rf"{label}(?: example| requirements?)?\s*[:\-]\s*([^\n]+)", text, re.I)
        if match:
            values.append((match.group(1).strip(), None, match.group(0),
                           _authority(document_type, definition), False))
    elif definition.data_type == "boolean":
        for term in definition.search_terms:
            match = re.search(rf"([^\n]*\b{re.escape(term)}\b[^\n]*)", text, re.I)
            if match:
                raw = match.group(1)
                optional = bool(re.search(r"\b(optional|option|available option|if equipped)\b", raw, re.I))
                negative = bool(re.search(r"\b(no|not available|unsupported|not present)\b", raw, re.I))
                values.append((False if negative else True, None, raw,
                               _authority(document_type, definition), optional))
    return values


def _variants(text: str) -> set[str]:
    return {
        value.upper() for value in MODEL_PATTERN.findall(text)
        if not value.upper().startswith("RS-")
    }


def _retrieval_score(
    definition: ProfileFieldDefinition, chunk: DocumentChunk,
    document_type: str, selected_variant: str | None,
) -> tuple[float, list[str]]:
    physical_categories = {
        "machine_geometry", "axis_limits", "spindle", "feed_and_motion",
        "tooling", "workholding", "capabilities",
    }
    if (
        definition.category in physical_categories
        and document_type in {"controller_manual", "programming_manual"}
        and document_type not in definition.preferred_document_types
    ):
        return 0, []
    lowered = chunk.content.lower()
    matches = [term for term in definition.search_terms if term.lower() in lowered]
    if not matches:
        return 0, []
    exact_label = any(
        re.search(rf"(?mi)^\s*{re.escape(term)}\s*:", chunk.content)
        for term in matches
    )
    variant_score = .2 if selected_variant and selected_variant.lower() in lowered else 0
    score = _authority(document_type, definition) + (.5 if exact_label else 0) + variant_score
    return score, matches


def _normalized(value: object, unit: str | None):
    if isinstance(value, (int, float)) and not isinstance(value, bool) and unit:
        return normalize_physical_value(float(value), unit)
    return value


def _excerpt(chunk: DocumentChunk, raw: str) -> str:
    compact_raw = " ".join(raw.split())
    if compact_raw:
        return compact_raw[:700]
    return chunk.content[:700]


def execute_extraction(run: ProfileExtractionRun, db: Session, settings: Settings) -> None:
    documents = list(db.scalars(select(SourceDocument).where(
        SourceDocument.id.in_(run.selected_document_ids_json)
    )))
    rows = db.execute(
        select(
            DocumentChunk, SourceDocument.id, SourceDocument.title,
            SourceDocument.document_type,
        )
        .options(defer(DocumentChunk.embedding_vector))
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.document_id.in_(run.selected_document_ids_json))
    ).all()
    variants = sorted(set().union(*(_variants(document.extracted_text or "") for document in documents)))
    document_variants = {
        document.id: _variants(document.extracted_text or "") for document in documents
    }
    run.detected_variants_json = variants
    categories = set(run.settings_json.get("field_categories") or [])
    definitions = [definition for definition in FIELD_REGISTRY
                   if not categories or definition.category in categories]
    provider = (
        OpenAICompatibleProfileExtractionProvider()
        if settings.profile_extraction_provider == "openai_compatible"
        else MockProfileExtractionProvider()
    )
    found = conflicts = ambiguous = missing = 0
    for definition in definitions:
        scored_rows = []
        for chunk, document_id, document_title, document_type_enum in rows:
            document_type = (
                document_type_enum.value
                if hasattr(document_type_enum, "value") else str(document_type_enum)
            )
            score, matched_terms = _retrieval_score(
                definition, chunk, document_type, run.selected_machine_variant,
            )
            if score:
                scored_rows.append((
                    score, chunk, document_id, document_title,
                    document_type, matched_terms,
                ))
        scored_rows.sort(key=lambda item: (-item[0], item[1].id))
        selected_rows = scored_rows[:settings.profile_extraction_top_k]
        retrieved_chunks = [
            RetrievedChunk(
                document_id=document_id, document_title=document_title,
                document_type=document_type, chunk_id=chunk.id,
                page_start=chunk.page_start, page_end=chunk.page_end,
                section_title=chunk.section_title, content=chunk.content,
                relevance_score=round(score / 1.7, 4),
            )
            for score, chunk, document_id, document_title, document_type, _ in selected_rows
        ]
        machine_context = {
            "machine_profile_id": run.machine_profile_id,
            "target_machine_type": run.settings_json.get("target_machine_type"),
            "selected_machine_variant": run.selected_machine_variant,
            "detected_variants": variants,
            "document_excerpts_are_untrusted": True,
        }
        structured = provider.extract_field_candidates(
            definition, retrieved_chunks, machine_context,
        )
        row_by_chunk = {item[1].id: item for item in selected_rows}
        candidates: list[Candidate] = []
        for item in structured:
            for chunk_id in item.evidence_chunk_ids:
                score, chunk, document_id, _, document_type, _ = row_by_chunk[chunk_id]
                candidates.append(Candidate(
                    value=item.value, unit=item.unit, raw=item.raw_value_text or "",
                    authority=_authority(document_type, definition),
                    optional=item.optional_alternative, chunk=chunk,
                    document_id=document_id, document_type=document_type,
                    heading=item.heading_context, method="structured_key_value",
                ))
        dedupe = {
            (str(candidate.value), candidate.unit, candidate.chunk.id)
            for candidate in candidates
        }
        for _, chunk, document_id, _, document_type, _ in selected_rows:
            chunk_variants = _variants(chunk.content)
            if (
                run.selected_machine_variant and chunk_variants
                and run.selected_machine_variant.upper() not in chunk_variants
            ):
                continue
            if (
                run.selected_machine_variant
                and definition.category in {
                    "machine_geometry", "axis_limits", "spindle",
                    "feed_and_motion", "tooling", "workholding", "capabilities",
                }
                and len(document_variants.get(document_id, set())) > 1
                and chunk_variants != {run.selected_machine_variant.upper()}
            ):
                continue
            if (
                structured
                and definition.category in {
                    "machine_geometry", "axis_limits", "spindle",
                    "feed_and_motion", "tooling", "workholding", "capabilities",
                }
                and len(document_variants.get(document_id, set())) > 1
            ):
                # An exact structured value for the selected variant outranks an
                # unstructured multi-column family table whose column mapping is unknown.
                continue
            for value, unit, raw, authority, optional in _extract_values(
                definition, chunk, document_type,
            ):
                if definition.field_key == "spindle_power" and unit not in {"hp", "kW"}:
                    continue
                key = (str(value), unit, chunk.id)
                if key in dedupe:
                    continue
                candidates.append(Candidate(
                    value=value, unit=unit, raw=raw, authority=authority,
                    optional=optional, chunk=chunk, document_id=document_id,
                    document_type=document_type, heading=chunk.section_title,
                    method="deterministic_regex",
                ))
                dedupe.add(key)

        base_candidates = [candidate for candidate in candidates if not candidate.optional]
        optional_candidates = [candidate for candidate in candidates if candidate.optional]
        considered = base_candidates or optional_candidates
        distinct = {(str(candidate.value), candidate.unit) for candidate in considered}
        status = "not_found"
        proposed = normalized = unit = note = None
        confidence = 0.0
        requires_verification = definition.optional_capability
        if considered:
            first = considered[0]
            proposed, unit = first.value, first.unit
            normalized = _normalized(proposed, unit)
            if len(distinct) > 1:
                status, confidence = "conflicting", 0.35
                note = (
                    "Selected applicable documents contain different base values; "
                    "no value was chosen automatically."
                )
                conflicts += 1
            elif not base_candidates:
                status, confidence = "ambiguous", 0.55
                note = (
                    "Only optional or option-dependent evidence was found; "
                    "installation on the exact machine is not established."
                )
                requires_verification = True
                ambiguous += 1
            elif (
                isinstance(proposed, (int, float)) and not isinstance(proposed, bool)
                and definition.allowed_units and unit is None
            ):
                status, confidence = "ambiguous", 0.5
                note = "A value was found without an explicit supported unit."
                ambiguous += 1
            elif (
                len(variants) > 1
                and definition.category in {"axis_limits", "spindle", "tooling", "capabilities"}
                and not run.selected_machine_variant
            ):
                status, confidence = "ambiguous", 0.55
                note = "Multiple machine variants were detected; select exact applicability."
                requires_verification = True
                ambiguous += 1
            else:
                status = "found"
                agreeing = sum(
                    1 for candidate in base_candidates
                    if str(candidate.value) == str(proposed) and candidate.unit == unit
                )
                confidence = min(0.98, 0.76 + .12 * first.authority + .05 * min(agreeing, 2))
                found += 1
            if optional_candidates:
                alternative_text = ", ".join(
                    f"{candidate.value:g} {candidate.unit or ''}".strip()
                    if isinstance(candidate.value, (int, float)) else str(candidate.value)
                    for candidate in optional_candidates
                )
                note = (
                    f"{note + ' ' if note else ''}Optional alternative(s) documented: "
                    f"{alternative_text}. Exact-machine verification is required."
                )
                requires_verification = True
        else:
            missing += 1

        diagnostics = {
            "search_terms": list(definition.search_terms),
            "retrieved_chunk_ids": [item.chunk_id for item in retrieved_chunks],
            "key_value_label_matched": any(
                candidate.method == "structured_key_value" for candidate in candidates
            ),
            "candidate_count": len(candidates),
            "rejected_candidates": [] if candidates else [{
                "reason": (
                    "No configured key-value label or validated free-text value matched."
                    if retrieved_chunks else "No field-specific chunks matched the search terms."
                )
            }],
            "selected_variant": run.selected_machine_variant,
            "document_authority": [
                {
                    "document_id": item.document_id,
                    "document_type": item.document_type,
                    "score": item.relevance_score,
                } for item in retrieved_chunks
            ],
            "field_normalization": normalized,
        }
        confidence_components = {
            "explicit_term": bool(retrieved_chunks),
            "evidence_count": len(candidates),
            "structured_key_value_count": sum(
                candidate.method == "structured_key_value" for candidate in candidates
            ),
            "optional_alternative_count": len(optional_candidates),
        }
        if settings.enable_profile_extraction_debug:
            confidence_components["diagnostics"] = diagnostics
        proposal = ProfileFieldProposal(
            extraction_run_id=run.id, field_key=definition.field_key,
            field_label=definition.display_name, field_category=definition.category,
            proposed_value_json=proposed, normalized_value_json=normalized, unit=unit,
            confidence=confidence, proposal_status=status,
            confidence_components_json=confidence_components,
            requires_exact_machine_verification=requires_verification,
            safety_relevant=definition.safety_relevance, interpretation_note=note,
            variant_applicability_json=(
                [run.selected_machine_variant] if run.selected_machine_variant else variants
            ),
            extraction_method=(
                "structured_key_value"
                if any(candidate.method == "structured_key_value" for candidate in candidates)
                else "deterministic_regex"
            ),
        )
        db.add(proposal)
        db.flush()
        for index, candidate in enumerate(candidates, 1):
            is_conflict = (
                status == "conflicting"
                and (str(candidate.value), candidate.unit)
                != (str(considered[0].value), considered[0].unit)
            )
            db.add(ProfileFieldEvidence(
                field_proposal_id=proposal.id, document_id=candidate.document_id,
                document_chunk_id=candidate.chunk.id, citation_number=index,
                page_start=candidate.chunk.page_start, page_end=candidate.chunk.page_end,
                section_title=candidate.heading or candidate.chunk.section_title,
                excerpt=_excerpt(candidate.chunk, candidate.raw),
                raw_value_text=candidate.raw[:200],
                normalized_value_json=_normalized(candidate.value, candidate.unit),
                unit=candidate.unit, relevance_score=round(candidate.authority, 2),
                evidence_type=(
                    "contextual" if candidate.optional and base_candidates
                    else "conflicting" if is_conflict else "supporting"
                ),
            ))
        db.add(AuditEvent(
            event_type="profile_field_proposed",
            machine_profile_id=run.machine_profile_id,
            metadata_json={
                "run_id": run.id, "proposal_id": proposal.id,
                "field_key": definition.field_key, "status": status,
            },
        ))
    run.summary_json = {
        "field_count": len(definitions), "found_count": found,
        "not_found_count": missing, "conflict_count": conflicts,
        "ambiguous_count": ambiguous, "detected_variant_count": len(variants),
        "failed_field_count": 0,
        "documentation_coverage": round(found / max(len(definitions), 1) * 100, 1),
    }
    run.status = "review_required"
    run.completed_at = utc_now()
    db.add(AuditEvent(
        event_type="profile_extraction_completed",
        machine_profile_id=run.machine_profile_id,
        metadata_json={"run_id": run.id, **run.summary_json},
    ))
    db.commit()

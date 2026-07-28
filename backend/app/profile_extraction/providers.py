from dataclasses import dataclass
import re
from typing import Protocol

from app.documents.retrieval import RetrievedChunk
from app.profile_extraction.registry import ProfileFieldDefinition
from app.profile_extraction.units import normalize_unit


@dataclass(slots=True)
class ExtractedFieldCandidate:
    value: object | None
    unit: str | None
    evidence_chunk_ids: list[int]
    confidence: float
    status: str
    interpretation_note: str | None
    requires_exact_machine_verification: bool
    raw_value_text: str | None = None
    optional_alternative: bool = False
    heading_context: str | None = None


class ProfileExtractionProvider(Protocol):
    def extract_field_candidates(
        self, field_definition: ProfileFieldDefinition,
        retrieved_chunks: list[RetrievedChunk], machine_context: dict,
    ) -> list[ExtractedFieldCandidate]: ...


ALLOWED_CANDIDATE_STATUSES = {
    "found", "not_found", "ambiguous", "conflicting", "unsupported",
}


def validate_candidates(
    definition: ProfileFieldDefinition,
    candidates: list[ExtractedFieldCandidate],
    retrieved_chunks: list[RetrievedChunk],
) -> list[ExtractedFieldCandidate]:
    """Reject ungrounded or ill-typed structured provider output."""
    allowed_chunk_ids = {item.chunk_id for item in retrieved_chunks}
    expected_types = {
        "string": str, "number": (int, float), "integer": int,
        "boolean": bool, "list": list, "object": dict,
    }
    for candidate in candidates:
        if candidate.status not in ALLOWED_CANDIDATE_STATUSES:
            raise ValueError("Provider returned an unsupported candidate status")
        if not 0 <= candidate.confidence <= 1:
            raise ValueError("Provider confidence must be between zero and one")
        if not set(candidate.evidence_chunk_ids).issubset(allowed_chunk_ids):
            raise ValueError("Provider returned a citation outside the retrieval context")
        expected = expected_types.get(definition.data_type)
        if candidate.value is not None and expected and not isinstance(candidate.value, expected):
            raise ValueError("Provider returned a value with the wrong field type")
        if candidate.unit:
            normalized = normalize_unit(candidate.unit)
            if normalized is None or (
                definition.allowed_units and normalized not in definition.allowed_units
            ):
                raise ValueError("Provider returned an unsupported unit")
    return candidates


class MockProfileExtractionProvider:
    """Deterministic structured key-value extractor used by tests and local runs."""
    name = "mock"

    def extract_field_candidates(self, field_definition, retrieved_chunks, machine_context):
        candidates: list[ExtractedFieldCandidate] = []
        selected_variant = machine_context.get("selected_machine_variant")
        for chunk in retrieved_chunks:
            variants = {
                token.upper()
                for token in re.findall(r"\b[A-Z]{2,5}-\d{2,5}[A-Z]*\b", chunk.content)
                if not token.upper().startswith("RS-")
            }
            if selected_variant and variants and selected_variant.upper() not in variants:
                continue
            entries = _key_value_entries(chunk.content, chunk.section_title)
            extracted = _extract_structured_value(field_definition, entries)
            for value, unit, raw, optional, heading in extracted:
                candidates.append(ExtractedFieldCandidate(
                    value=value, unit=unit, evidence_chunk_ids=[chunk.chunk_id],
                    confidence=.94 if unit or field_definition.data_type in {
                        "string", "boolean", "integer", "object",
                    } else .72,
                    status="ambiguous" if optional else "found",
                    interpretation_note=(
                        "The source explicitly labels this value as optional; "
                        "installation on the exact machine is not established."
                        if optional else None
                    ),
                    requires_exact_machine_verification=optional,
                    raw_value_text=raw, optional_alternative=optional,
                    heading_context=heading,
                ))
        return validate_candidates(field_definition, candidates, retrieved_chunks)


class OpenAICompatibleProfileExtractionProvider(MockProfileExtractionProvider):
    """Structured-output boundary; excerpts are untrusted data, never instructions.

    A future transport must delimit excerpts, request only the typed schema, then
    pass decoded output through ``validate_candidates`` before persistence.
    """
    name = "openai_compatible"


@dataclass(frozen=True, slots=True)
class _KeyValueEntry:
    label: str
    normalized_label: str
    value: str
    raw: str
    heading: str | None


def _normalize_label(value: str) -> str:
    value = value.lower().replace("–", "-").replace("—", "-")
    value = re.sub(r"[-_/()]+", " ", value)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9. ]", "", value)).strip()


def _key_value_entries(content: str, initial_heading: str | None) -> list[_KeyValueEntry]:
    heading = initial_heading
    entries: list[_KeyValueEntry] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip() or heading
            continue
        match = re.match(r"^\s*[-*]?\s*([^:]{2,120})\s*:\s*(\S.+?)\s*$", line)
        if match:
            label, value = match.group(1).strip(), match.group(2).strip()
            entries.append(_KeyValueEntry(
                label=label, normalized_label=_normalize_label(label),
                value=value, raw=f"{label}: {value}", heading=heading,
            ))
    return entries


UNIT_PATTERN = (
    r"inches?\s+per\s+minute|inches?/min(?:ute)?|in/min|ipm|mm/min|"
    r"rpm|inches?|in\b|mm\b|hp\b|kw\b|kilograms?|kg\b|pounds?|lbs?\b"
)


def _number_unit(value: str) -> tuple[float | None, str | None]:
    match = re.search(rf"([-+]?\d[\d,]*(?:\.\d+)?)\s*({UNIT_PATTERN})?", value, re.I)
    if not match:
        return None, None
    number = float(match.group(1).replace(",", ""))
    return number, normalize_unit(match.group(2))


def _matches_label(definition: ProfileFieldDefinition, label: str) -> bool:
    aliases = {
        _normalize_label(definition.display_name),
        _normalize_label(definition.field_key),
        *(_normalize_label(term) for term in definition.search_terms),
    }
    return label in aliases or (
        label.endswith(" present") and label.removesuffix(" present") in aliases
    )


def _optional(entry: _KeyValueEntry) -> bool:
    return bool(re.search(
        r"\b(optional|option|opt\.?|if equipped)\b",
        f"{entry.label} {entry.value}", re.I,
    ))


def _extract_structured_value(
    definition: ProfileFieldDefinition, entries: list[_KeyValueEntry],
) -> list[tuple[object, str | None, str, bool, str | None]]:
    key = definition.field_key
    if key == "overall_dimensions":
        direct = next((entry for entry in entries if entry.normalized_label in {
            "overall dimensions", "overall dimension",
        }), None)
        if direct:
            values = re.findall(r"\d[\d,]*(?:\.\d+)?", direct.value)
            unit_match = re.search(UNIT_PATTERN, direct.value, re.I)
            if len(values) >= 3:
                unit = normalize_unit(unit_match.group(0)) if unit_match else None
                return [({
                    "length": float(values[0].replace(",", "")),
                    "width": float(values[1].replace(",", "")),
                    "height": float(values[2].replace(",", "")),
                    "unit": unit,
                }, None, direct.raw, _optional(direct), direct.heading)]
        dimensions = {
            entry.normalized_label.removeprefix("overall "): entry
            for entry in entries if entry.normalized_label in {
                "overall length", "overall width", "overall height",
            }
        }
        if len(dimensions) == 3:
            parsed = {name: _number_unit(entry.value) for name, entry in dimensions.items()}
            units = {unit for _, unit in parsed.values() if unit}
            if all(value is not None for value, _ in parsed.values()) and len(units) <= 1:
                first = dimensions["length"]
                return [({
                    **{name: value for name, (value, _) in parsed.items()},
                    "unit": next(iter(units), None),
                }, None, " | ".join(entry.raw for entry in dimensions.values()),
                    any(_optional(entry) for entry in dimensions.values()), first.heading)]
        return []

    matched = [entry for entry in entries if _matches_label(definition, entry.normalized_label)]
    output: list[tuple[object, str | None, str, bool, str | None]] = []
    for entry in matched:
        optional = _optional(entry)
        if key in {"min_spindle_rpm", "max_spindle_rpm"}:
            numbers = [
                float(value.replace(",", ""))
                for value in re.findall(r"\d[\d,]*(?:\.\d+)?", entry.value)
            ]
            if not numbers:
                continue
            value = min(numbers) if key.startswith("min_") else max(numbers)
            unit_match = re.search(r"\brpm\b", entry.value, re.I)
            output.append((value, "rpm" if unit_match else None, entry.raw, optional, entry.heading))
        elif key in {
            "maximum_rapid_rate_x", "maximum_rapid_rate_z",
            "rapid_traverse_rate_x", "rapid_traverse_rate_z",
        }:
            numbers = [
                float(value.replace(",", ""))
                for value in re.findall(r"\d[\d,]*(?:\.\d+)?", entry.value)
            ]
            if not numbers:
                continue
            paired = len(numbers) >= 2 and "z x" in entry.normalized_label
            axis = "x" if key.endswith("_x") else "z"
            value = numbers[1 if paired and axis == "x" else 0]
            unit_match = re.search(UNIT_PATTERN, entry.value, re.I)
            unit = normalize_unit(unit_match.group(0)) if unit_match else None
            output.append((value, unit, entry.raw, optional, entry.heading))
        elif definition.data_type == "boolean":
            lowered = entry.value.strip().lower()
            if lowered in {"yes", "true", "present", "standard", "included"}:
                output.append((True, None, entry.raw, optional, entry.heading))
            elif lowered in {"no", "false", "absent", "not present"}:
                output.append((False, None, entry.raw, optional, entry.heading))
        elif definition.data_type == "integer":
            number, _ = _number_unit(entry.value)
            if number is None:
                word = re.search(r"\b(one|two|three|four|five|six|eight|ten|twelve)\b", entry.value, re.I)
                words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                         "six": 6, "eight": 8, "ten": 10, "twelve": 12}
                number = words.get(word.group(1).lower()) if word else None
            if number is not None:
                output.append((int(number), None, entry.raw, optional, entry.heading))
        elif definition.data_type == "number":
            number, unit = _number_unit(entry.value)
            if number is not None:
                output.append((number, unit, entry.raw, optional, entry.heading))
        elif definition.data_type == "string":
            output.append((entry.value.strip(), None, entry.raw, optional, entry.heading))
    return output

from dataclasses import dataclass
import json
import re

import httpx

from app.core.config import Settings
from app.documents.retrieval import RetrievedChunk

SAFETY_NOTICE = (
    "This response is for technical reference only. Machine documentation, "
    "simulation, and approval by a qualified CNC programmer remain required."
)
INSUFFICIENT = (
    "The uploaded documents do not provide enough evidence to answer this question "
    "reliably. Review the controlled machine or controller documentation, or upload "
    "the relevant manual section."
)
FORBIDDEN = (
    "safe to run", "production ready", "certified", "collision free",
    "guaranteed correct", "fully verified",
)

GROUNDED_SYSTEM_PROMPT = """You are a citation-grounded CNC manual reference assistant.
Answer only from the supplied excerpts. Cite claims with [1], [2], etc. Never invent
pages, sections, or sources. Distinguish documentation from interpretation, preserve
controller distinctions, surface conflicts and incomplete evidence, and never provide
production approval or machine-safety assurance. Return JSON with answer_status,
answer, cited_chunk_ids, and unresolved_questions."""


@dataclass(slots=True)
class GroundedAnswer:
    answer_status: str
    answer: str
    cited_chunk_ids: list[int]
    unresolved_questions: list[str]


class GroundedAnswerProvider:
    name = "mock"
    model = "grounded-extractive-v1"

    def answer(self, question: str, evidence: list[RetrievedChunk]) -> GroundedAnswer:
        if not evidence:
            return GroundedAnswer("insufficient_evidence", INSUFFICIENT, [], [])
        stop = {"what", "does", "this", "that", "with", "from", "machine", "controller",
                "support", "installed", "explain", "context"}
        question_terms = {
            term for term in re.findall(r"[a-z0-9.]+", question.lower())
            if len(term) > 2 and term not in stop
        }
        evidence_terms = set(re.findall(
            r"[a-z0-9.]+", " ".join(item.content for item in evidence).lower()
        ))
        if len(question_terms & evidence_terms) < min(2, len(question_terms)):
            return GroundedAnswer("insufficient_evidence", INSUFFICIENT, [], [])
        command = re.search(r"\b[GM]\s*0*\d+(?:\.\d+)?\b", question.upper())
        if command:
            normalized = command.group(0).replace(" ", "")
            number = normalized[1:]
            normalized = normalized[0] + (number.zfill(2) if number.isdigit() and int(number) < 10 else number)
            evidence = [
                item for item in evidence if normalized.lower() in item.content.lower()
            ]
            if not evidence:
                return GroundedAnswer("insufficient_evidence", INSUFFICIENT, [], [])
        affirmative_sources: set[int] = set()
        negative_sources: set[int] = set()
        for item in evidence:
            lowered = item.content.lower()
            if re.search(r"\b(?:does not support|not supported|unsupported|prohibited)\b", lowered):
                negative_sources.add(item.document_id)
            if re.search(r"\b(?:supports?|supported|commands?|performs?)\b", lowered):
                affirmative_sources.add(item.document_id)
        if affirmative_sources and negative_sources and (
            affirmative_sources - negative_sources or negative_sources - affirmative_sources
        ):
            return GroundedAnswer(
                "insufficient_evidence",
                INSUFFICIENT,
                [],
                ["The uploaded documents contain conflicting statements that require controlled-document review."],
            )
        ranked_excerpts: list[tuple[int, float, RetrievedChunk, str]] = []
        for evidence_index, item in enumerate(evidence):
            candidates = [
                value.strip(" \n#")
                for value in re.split(r"(?<=[.!?])\s+|\n{2,}", item.content)
                if value.strip(" \n#")
            ]
            best: tuple[float, str] | None = None
            for candidate in candidates:
                candidate_terms = set(re.findall(r"[a-z0-9.]+", candidate.lower()))
                overlap = len(question_terms & candidate_terms)
                if not overlap:
                    continue
                score = overlap + (
                    0.5
                    if command and normalized.lower() in candidate.lower()
                    else 0
                )
                if (
                    best is None
                    or score > best[0]
                    or (score == best[0] and len(candidate) > len(best[1]))
                ):
                    best = (score, candidate)
            if best:
                ranked_excerpts.append(
                    (int(best[0]), item.relevance_score, item, best[1][:420])
                )
        ranked_excerpts.sort(key=lambda value: (-value[0], -value[1]))
        chosen = ranked_excerpts[:3]
        if not chosen:
            return GroundedAnswer("insufficient_evidence", INSUFFICIENT, [], [])
        selected = [value[2] for value in chosen]
        excerpts = [
            f"{value[3]} [{index}]" for index, value in enumerate(chosen, 1)
        ]
        answer = "Based on the provided documentation, " + " ".join(excerpts)
        return GroundedAnswer(
            "answered", answer, [item.chunk_id for item in selected],
            ["Confirm the cited text against the controlled document revision."],
        )


class OpenAICompatibleGroundedProvider(GroundedAnswerProvider):
    name = "openai_compatible"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.openai_chat_model
        if not settings.openai_api_key or not self.model:
            raise ValueError("OpenAI-compatible chat requires an API key and model.")

    def answer(self, question: str, evidence: list[RetrievedChunk]) -> GroundedAnswer:
        if not evidence:
            return GroundedAnswer("insufficient_evidence", INSUFFICIENT, [], [])
        context = "\n\n".join(
            f"[{index}] chunk_id={item.chunk_id}, document={item.document_title}, "
            f"page={item.page_start}, section={item.section_title}\n{item.content}"
            for index, item in enumerate(evidence, 1)
        )
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": GROUNDED_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {question}\n\nEvidence:\n{context}"},
            ],
        }
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}
        with httpx.Client(timeout=45) as client:
            response = client.post(
                f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
                headers=headers, json=payload,
            )
            response.raise_for_status()
        data = json.loads(response.json()["choices"][0]["message"]["content"])
        return GroundedAnswer(
            data.get("answer_status", "insufficient_evidence"),
            data.get("answer", INSUFFICIENT),
            [int(value) for value in data.get("cited_chunk_ids", [])],
            list(data.get("unresolved_questions", [])),
        )


def get_answer_provider(settings: Settings) -> GroundedAnswerProvider:
    return (
        GroundedAnswerProvider()
        if settings.ai_provider == "mock"
        else OpenAICompatibleGroundedProvider(settings)
    )


def validate_grounded_answer(
    answer: GroundedAnswer, evidence: list[RetrievedChunk]
) -> GroundedAnswer:
    if answer.answer_status != "answered":
        return GroundedAnswer(
            "insufficient_evidence", INSUFFICIENT, [], answer.unresolved_questions
        )
    available = {item.chunk_id for item in evidence}
    markers = {int(value) for value in re.findall(r"\[(\d+)\]", answer.answer)}
    valid_ids = [value for value in answer.cited_chunk_ids if value in available]
    if (
        not valid_ids
        or not markers
        or any(phrase in answer.answer.lower() for phrase in FORBIDDEN)
        or any(marker < 1 or marker > len(evidence) for marker in markers)
        or markers != set(range(1, len(valid_ids) + 1))
    ):
        return GroundedAnswer("insufficient_evidence", INSUFFICIENT, [], [])
    return GroundedAnswer("answered", answer.answer, valid_ids, answer.unresolved_questions)

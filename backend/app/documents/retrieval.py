from dataclasses import dataclass
import math
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.documents.embeddings import EmbeddingProvider
from app.models.entities import DocumentChunk, DocumentType, ProcessingStatus, SourceDocument


@dataclass(slots=True)
class RetrievedChunk:
    document_id: int
    document_title: str
    document_type: str
    chunk_id: int
    page_start: int | None
    page_end: int | None
    section_title: str | None
    content: str
    relevance_score: float


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right)) / (
        math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right)) or 1
    )


def _terms(text: str) -> set[str]:
    return {
        term for term in re.findall(r"[a-z0-9.]+", text.lower())
        if len(term) > 2 or re.fullmatch(r"[gm]\d+(?:\.\d+)?", term)
    }


def retrieve(
    db: Session,
    machine_profile_id: int,
    question: str,
    provider: EmbeddingProvider,
    settings: Settings,
    document_types: list[DocumentType] | None = None,
) -> tuple[list[RetrievedChunk], dict]:
    query = (
        select(DocumentChunk, SourceDocument)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.machine_profile_id == machine_profile_id,
            SourceDocument.processing_status == ProcessingStatus.READY,
        )
    )
    if document_types:
        query = query.where(SourceDocument.document_type.in_(document_types))
    rows = db.execute(query).all()
    query_vector = provider.embed_texts([question])[0]
    question_terms = _terms(question)
    scored: list[tuple[float, DocumentChunk, SourceDocument]] = []
    for chunk, document in rows:
        vector_score = cosine(query_vector, chunk.embedding_vector or [])
        content_terms = _terms(chunk.content)
        keyword_score = len(question_terms & content_terms) / max(1, len(question_terms))
        score = 0.55 * vector_score + 0.45 * keyword_score
        scored.append((score, chunk, document))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    selected = [item for item in scored if item[0] >= settings.retrieval_min_score][
        : settings.retrieval_top_k
    ]
    results = [
        RetrievedChunk(
            document.id, document.title, document.document_type.value, chunk.id,
            chunk.page_start, chunk.page_end, chunk.section_title, chunk.content,
            round(score, 4),
        )
        for score, chunk, document in selected
    ]
    debug = {
        "query": question,
        "minimum_threshold": settings.retrieval_min_score,
        "selected_chunk_ids": [item.chunk_id for item in results],
        "rejected_chunks": [
            {"chunk_id": chunk.id, "score": round(score, 4)}
            for score, chunk, _ in scored if score < settings.retrieval_min_score
        ][:20],
    }
    return results, debug


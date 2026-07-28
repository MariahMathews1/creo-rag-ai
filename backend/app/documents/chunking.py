from dataclasses import dataclass
from hashlib import sha256
import re

from app.documents.extractors.base import ExtractedPage


@dataclass(slots=True)
class ChunkDraft:
    chunk_index: int
    page_start: int
    page_end: int
    section_title: str | None
    content: str
    content_hash: str
    token_estimate: int


def _section(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()[:300] or None
        if stripped and len(stripped) < 100 and stripped.upper() == stripped:
            return stripped[:300]
    return None


def chunk_pages(
    pages: list[ExtractedPage], target_size: int = 900, overlap: int = 150
) -> list[ChunkDraft]:
    """Chunk each page independently using character targets and overlap."""

    chunks: list[ChunkDraft] = []
    index = 0
    for page in pages:
        text = re.sub(r"\n{3,}", "\n\n", page.text).strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(len(text), start + target_size)
            if end < len(text):
                boundary = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end))
                if boundary > start + target_size // 2:
                    end = boundary + 1
            content = text[start:end].strip()
            if content:
                chunks.append(
                    ChunkDraft(
                        index, page.page_number, page.page_number, _section(content),
                        content, sha256(content.encode()).hexdigest(),
                        max(1, len(content) // 4),
                    )
                )
                index += 1
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
    return chunks


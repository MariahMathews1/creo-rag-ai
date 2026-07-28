from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class ExtractedPage:
    page_number: int
    text: str
    character_count: int


class DocumentExtractor(Protocol):
    def extract(self, path: Path) -> list[ExtractedPage]: ...


class ExtractionError(ValueError):
    """A user-actionable document extraction failure."""


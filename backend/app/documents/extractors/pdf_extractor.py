from pathlib import Path

from pypdf import PdfReader

from app.documents.extractors.base import ExtractedPage, ExtractionError


class PDFExtractor:
    def extract(self, path: Path) -> list[ExtractedPage]:
        try:
            reader = PdfReader(path)
        except Exception as exc:
            raise ExtractionError(f"PDF could not be opened: {exc}") from exc
        pages: list[ExtractedPage] = []
        for number, page in enumerate(reader.pages, 1):
            try:
                text = (page.extract_text() or "").strip()
            except Exception:
                text = ""
            pages.append(ExtractedPage(number, text, len(text)))
        if not any(page.text for page in pages):
            raise ExtractionError(
                "No extractable text was found. This file may contain scanned images "
                "and may require OCR, which is not supported in this version."
            )
        return pages


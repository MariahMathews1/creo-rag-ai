from pathlib import Path

from app.documents.extractors.base import ExtractedPage, ExtractionError


class TextExtractor:
    def extract(self, path: Path) -> list[ExtractedPage]:
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
        text = text.strip()
        if not text:
            raise ExtractionError("The uploaded text document is empty after decoding.")
        return [ExtractedPage(1, text, len(text))]


class MarkdownExtractor(TextExtractor):
    pass


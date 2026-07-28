from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from uuid import uuid4

from app.core.config import Settings

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


@dataclass(slots=True)
class StoredFile:
    original_filename: str
    stored_filename: str
    stored_path: Path
    mime_type: str
    size: int
    file_hash: str


def safe_original_name(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._ -]", "_", name)[:255] or "document"


def store_upload(filename: str, content: bytes, settings: Settings) -> StoredFile:
    original = safe_original_name(filename)
    extension = Path(original).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type. Upload a PDF, TXT, or MD document.")
    if not content:
        raise ValueError("The uploaded file is empty.")
    maximum = settings.max_document_upload_mb * 1024 * 1024
    if len(content) > maximum:
        raise ValueError(
            f"File exceeds the configured {settings.max_document_upload_mb} MB limit."
        )
    storage = settings.document_storage_dir.resolve()
    storage.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}{extension}"
    stored_path = (storage / stored_filename).resolve()
    if storage not in stored_path.parents:
        raise ValueError("Invalid storage path.")
    stored_path.write_bytes(content)
    return StoredFile(
        original, stored_filename, stored_path, MIME_TYPES[extension],
        len(content), sha256(content).hexdigest(),
    )


def delete_stored_file(path: str | None, settings: Settings) -> None:
    if not path:
        return
    storage = settings.document_storage_dir.resolve()
    candidate = Path(path).resolve()
    if storage in candidate.parents and candidate.is_file():
        candidate.unlink()


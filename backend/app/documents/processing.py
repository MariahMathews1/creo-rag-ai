from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.documents.chunking import chunk_pages
from app.documents.embeddings import get_embedding_provider
from app.documents.extractors.pdf_extractor import PDFExtractor
from app.documents.extractors.text_extractor import MarkdownExtractor, TextExtractor
from app.models.entities import AuditEvent, DocumentChunk, ProcessingStatus, SourceDocument, utc_now


def process_document(document: SourceDocument, db: Session, settings: Settings) -> None:
    document.processing_status = ProcessingStatus.PROCESSING
    document.processing_error = None
    db.commit()
    try:
        path = Path(document.stored_path or "")
        extractor = (
            PDFExtractor() if path.suffix.lower() == ".pdf"
            else MarkdownExtractor() if path.suffix.lower() == ".md"
            else TextExtractor()
        )
        pages = extractor.extract(path)
        drafts = chunk_pages(
            pages, settings.document_chunk_size, settings.document_chunk_overlap
        )
        if not drafts:
            raise ValueError("No meaningful text chunks could be created.")
        provider = get_embedding_provider(settings)
        vectors = provider.embed_texts([draft.content for draft in drafts])
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        for draft, vector in zip(drafts, vectors):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    machine_profile_id=document.machine_profile_id,
                    chunk_index=draft.chunk_index,
                    page_start=draft.page_start,
                    page_end=draft.page_end,
                    section_title=draft.section_title,
                    content=draft.content,
                    content_hash=draft.content_hash,
                    token_estimate=draft.token_estimate,
                    embedding_provider=provider.name,
                    embedding_model=provider.model,
                    embedding_vector=vector,
                )
            )
        document.page_count = len(pages)
        document.page_data = [
            {"page_number": page.page_number, "text": page.text,
             "character_count": page.character_count}
            for page in pages
        ]
        document.extracted_text = "\n\n".join(
            f"--- Page {page.page_number} ---\n{page.text}" for page in pages
        )
        document.processing_status = ProcessingStatus.READY
        document.processed_at = utc_now()
        db.add(AuditEvent(
            event_type="document_processed",
            machine_profile_id=document.machine_profile_id,
            document_id=document.id,
            metadata_json={"page_count": len(pages), "chunk_count": len(drafts)},
        ))
    except Exception as exc:
        document.processing_status = ProcessingStatus.FAILED
        document.processing_error = str(exc)
        db.add(AuditEvent(
            event_type="document_processing_failed",
            machine_profile_id=document.machine_profile_id,
            document_id=document.id,
            metadata_json={"error": str(exc)[:500]},
        ))
    db.commit()
    db.refresh(document)


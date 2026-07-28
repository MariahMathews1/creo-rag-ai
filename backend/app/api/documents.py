from pathlib import Path
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.session import get_db
from app.documents.processing import process_document
from app.documents.storage import delete_stored_file, store_upload
from app.models.entities import (
    AuditEvent, DocumentChunk, DocumentType, MachineProfile, SourceDocument,
)
from app.schemas.documents import DocumentContent, DocumentRead, SearchResult

router = APIRouter(tags=["documents"])


def document_or_404(document_id: int, db: Session) -> SourceDocument:
    document = db.get(SourceDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    return document


@router.post(
    "/machines/{machine_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    machine_id: int,
    title: str = Form(...),
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    machine = db.get(MachineProfile, machine_id)
    if machine is None:
        raise HTTPException(404, "Machine profile not found")
    content = await file.read()
    settings = get_settings()
    try:
        stored = store_upload(file.filename or "document", content, settings)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    duplicate = db.scalar(
        select(SourceDocument).where(
            SourceDocument.machine_profile_id == machine_id,
            SourceDocument.file_hash == stored.file_hash,
        )
    )
    if duplicate:
        stored.stored_path.unlink(missing_ok=True)
        raise HTTPException(
            409,
            {"message": "This file is already attached to the machine profile.",
             "existing_document_id": duplicate.id},
        )
    document = SourceDocument(
        machine_profile_id=machine_id,
        title=title.strip() or stored.original_filename,
        document_type=document_type,
        manufacturer=machine.manufacturer,
        controller_name=machine.controller_name,
        controller_version=machine.controller_version,
        original_filename=stored.original_filename,
        stored_filename=stored.stored_filename,
        stored_path=str(stored.stored_path),
        mime_type=stored.mime_type,
        file_size_bytes=stored.size,
        file_hash=stored.file_hash,
    )
    db.add(document)
    db.flush()
    db.add(AuditEvent(
        event_type="document_uploaded", machine_profile_id=machine_id,
        document_id=document.id,
        metadata_json={"filename": stored.original_filename, "size": stored.size},
    ))
    db.commit()
    db.refresh(document)
    process_document(document, db, settings)
    return document


@router.get("/machines/{machine_id}/documents", response_model=list[DocumentRead])
def list_documents(machine_id: int, db: Session = Depends(get_db)):
    if db.get(MachineProfile, machine_id) is None:
        raise HTTPException(404, "Machine profile not found")
    return db.scalars(
        select(SourceDocument)
        .where(SourceDocument.machine_profile_id == machine_id)
        .order_by(SourceDocument.uploaded_at.desc())
    ).all()


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, db: Session = Depends(get_db)):
    return document_or_404(document_id, db)


@router.get("/documents/{document_id}/content", response_model=DocumentContent)
def get_document_content(document_id: int, db: Session = Depends(get_db)):
    document = document_or_404(document_id, db)
    chunks = db.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    ).all()
    return DocumentContent(
        document=document, pages=document.page_data or [],
        extracted_text=document.extracted_text, chunks=chunks,
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = document_or_404(document_id, db)
    settings = get_settings()
    path = document.stored_path
    machine_id = document.machine_profile_id
    db.delete(document)
    db.commit()
    delete_stored_file(path, settings)
    with db.begin():
        db.add(AuditEvent(
            event_type="document_deleted", machine_profile_id=machine_id,
            document_id=document_id, metadata_json={},
        ))
    return Response(status_code=204)


@router.post("/documents/{document_id}/reprocess", response_model=DocumentRead)
def reprocess_document(document_id: int, db: Session = Depends(get_db)):
    document = document_or_404(document_id, db)
    if not document.stored_path or not Path(document.stored_path).is_file():
        raise HTTPException(422, "Stored document file is missing.")
    process_document(document, db, get_settings())
    return document


@router.get("/machines/{machine_id}/documents/search", response_model=list[SearchResult])
def search_documents(
    machine_id: int,
    q: str = Query(min_length=1),
    document_type: DocumentType | None = None,
    page: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    query = (
        select(DocumentChunk, SourceDocument)
        .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.machine_profile_id == machine_id)
    )
    if document_type:
        query = query.where(SourceDocument.document_type == document_type)
    if page:
        query = query.where(DocumentChunk.page_start <= page, DocumentChunk.page_end >= page)
    terms = [term.lower() for term in re.findall(r"[A-Za-z0-9.]+", q)]
    results = []
    for chunk, document in db.execute(query).all():
        lowered = chunk.content.lower()
        if all(term in lowered for term in terms):
            position = min((lowered.find(term) for term in terms), default=0)
            snippet = chunk.content[max(0, position - 100): position + 400]
            results.append(SearchResult(
                document_id=document.id, document_title=document.title,
                document_type=document.document_type, chunk_id=chunk.id,
                page_start=chunk.page_start, page_end=chunk.page_end,
                section_title=chunk.section_title, snippet=snippet,
            ))
    return results[:50]


@router.post("/documents/{document_id}/citation-open", status_code=204)
def citation_opened(document_id: int, db: Session = Depends(get_db)):
    document = document_or_404(document_id, db)
    db.add(AuditEvent(
        event_type="document_citation_opened",
        machine_profile_id=document.machine_profile_id,
        document_id=document.id, metadata_json={},
    ))
    db.commit()
    return Response(status_code=204)


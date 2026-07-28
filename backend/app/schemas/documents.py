from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.entities import (
    AnswerStatus, DocumentType, ProcessingStatus, QuestionCategory,
)
from app.documents.answering import SAFETY_NOTICE


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    machine_profile_id: int
    title: str
    document_type: DocumentType
    manufacturer: str | None
    controller_name: str | None
    controller_version: str | None
    original_filename: str | None
    mime_type: str | None
    file_size_bytes: int | None
    file_hash: str | None
    processing_status: ProcessingStatus
    processing_error: str | None
    page_count: int | None
    uploaded_at: datetime
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    chunk_index: int
    page_start: int | None
    page_end: int | None
    section_title: str | None
    content: str
    content_hash: str
    token_estimate: int


class DocumentContent(BaseModel):
    document: DocumentRead
    pages: list[dict]
    extracted_text: str | None
    chunks: list[ChunkRead]


class SearchResult(BaseModel):
    document_id: int
    document_title: str
    document_type: DocumentType
    chunk_id: int
    page_start: int | None
    page_end: int | None
    section_title: str | None
    snippet: str


class ManualSessionCreate(BaseModel):
    machine_profile_id: int
    title: str = Field(min_length=1, max_length=200)


class ManualSessionRead(ManualSessionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class QuestionCreate(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    document_types: list[DocumentType] = Field(default_factory=list)
    category: QuestionCategory = QuestionCategory.GENERAL


class CitationRead(BaseModel):
    citation_number: int
    document_id: int
    document_title: str
    document_type: DocumentType
    document_chunk_id: int
    page_start: int | None
    page_end: int | None
    section_title: str | None
    excerpt: str
    relevance_score: float


class ManualQuestionRead(BaseModel):
    id: int
    session_id: int
    question: str
    category: QuestionCategory
    answer_status: AnswerStatus
    answer: str
    unresolved_questions: list[str]
    provider_name: str
    model_name: str | None
    created_at: datetime
    citations: list[CitationRead]
    retrieval_debug: dict | None = None
    advisory_only: bool = True
    grounded_in_uploaded_documents: bool = True
    production_approval_required: bool = True
    safety_notice: str = SAFETY_NOTICE


class ManualSessionDetail(ManualSessionRead):
    questions: list[ManualQuestionRead]


class CommandExplanationRequest(BaseModel):
    command: str = Field(min_length=1, max_length=20)
    context: str = Field(default="", max_length=2000)


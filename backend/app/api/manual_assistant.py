import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.documents.answering import (
    INSUFFICIENT, get_answer_provider, validate_grounded_answer,
)
from app.documents.embeddings import get_embedding_provider
from app.documents.retrieval import retrieve
from app.models.entities import (
    AnswerCitation, AnswerStatus, AuditEvent, DocumentType, MachineProfile,
    ManualQuestion, ManualQuestionSession, QuestionCategory, SourceDocument,
)
from app.parsers.gcode import normalize_code
from app.schemas.documents import (
    CitationRead, CommandExplanationRequest, ManualQuestionRead,
    ManualSessionCreate, ManualSessionDetail, ManualSessionRead, QuestionCreate,
)

router = APIRouter(tags=["manual assistant"])


def session_or_404(session_id: int, db: Session) -> ManualQuestionSession:
    session = db.get(ManualQuestionSession, session_id)
    if not session:
        raise HTTPException(404, "Manual question session not found")
    return session


def question_response(question: ManualQuestion, db: Session) -> ManualQuestionRead:
    citations = []
    for citation in sorted(question.citations, key=lambda item: item.citation_number):
        document = db.get(SourceDocument, citation.document_id)
        citations.append(CitationRead(
            citation_number=citation.citation_number,
            document_id=citation.document_id,
            document_title=document.title if document else "Deleted document",
            document_type=document.document_type if document else DocumentType.OTHER,
            document_chunk_id=citation.document_chunk_id,
            page_start=citation.page_start, page_end=citation.page_end,
            section_title=citation.section_title, excerpt=citation.excerpt,
            relevance_score=citation.relevance_score,
        ))
    return ManualQuestionRead(
        id=question.id, session_id=question.session_id, question=question.question,
        category=question.category, answer_status=question.answer_status,
        answer=question.answer, unresolved_questions=question.unresolved_questions or [],
        provider_name=question.provider_name, model_name=question.model_name,
        created_at=question.created_at, citations=citations,
        retrieval_debug=question.retrieval_debug,
    )


def answer_question(
    session: ManualQuestionSession, payload: QuestionCreate, db: Session
) -> ManualQuestionRead:
    settings = get_settings()
    db.add(AuditEvent(
        event_type="manual_question_submitted",
        machine_profile_id=session.machine_profile_id,
        metadata_json={"category": payload.category.value},
    ))
    evidence, debug = retrieve(
        db, session.machine_profile_id, payload.question,
        get_embedding_provider(settings), settings, payload.document_types or None,
    )
    provider = get_answer_provider(settings)
    grounded = validate_grounded_answer(provider.answer(payload.question, evidence), evidence)
    status_value = (
        AnswerStatus.ANSWERED if grounded.answer_status == "answered"
        else AnswerStatus.INSUFFICIENT_EVIDENCE
    )
    question = ManualQuestion(
        session_id=session.id, question=payload.question, category=payload.category,
        answer=grounded.answer if grounded.answer else INSUFFICIENT,
        answer_status=status_value, unresolved_questions=grounded.unresolved_questions,
        model_name=provider.model, provider_name=provider.name,
        retrieval_debug=debug if settings.enable_retrieval_debug else None,
    )
    db.add(question)
    db.flush()
    for number, chunk_id in enumerate(grounded.cited_chunk_ids, 1):
        item = next((entry for entry in evidence if entry.chunk_id == chunk_id), None)
        if item:
            db.add(AnswerCitation(
                manual_question_id=question.id, document_id=item.document_id,
                document_chunk_id=item.chunk_id, citation_number=number,
                page_start=item.page_start, page_end=item.page_end,
                section_title=item.section_title, excerpt=item.content[:600],
                relevance_score=item.relevance_score,
            ))
    db.add(AuditEvent(
        event_type=(
            "manual_answer_generated" if status_value == AnswerStatus.ANSWERED
            else "manual_answer_insufficient"
        ),
        machine_profile_id=session.machine_profile_id,
        manual_question_id=question.id, metadata_json={"citation_count": len(grounded.cited_chunk_ids)},
    ))
    db.commit()
    db.refresh(question)
    return question_response(question, db)


@router.post("/manual-sessions", response_model=ManualSessionRead, status_code=201)
def create_session(payload: ManualSessionCreate, db: Session = Depends(get_db)):
    if db.get(MachineProfile, payload.machine_profile_id) is None:
        raise HTTPException(404, "Machine profile not found")
    session = ManualQuestionSession(**payload.model_dump())
    db.add(session); db.commit(); db.refresh(session)
    return session


@router.get("/manual-sessions", response_model=list[ManualSessionRead])
def list_sessions(machine_profile_id: int | None = None, db: Session = Depends(get_db)):
    query = select(ManualQuestionSession).order_by(ManualQuestionSession.updated_at.desc())
    if machine_profile_id:
        query = query.where(ManualQuestionSession.machine_profile_id == machine_profile_id)
    return db.scalars(query).all()


@router.get("/manual-sessions/{session_id}", response_model=ManualSessionDetail)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = session_or_404(session_id, db)
    questions = db.scalars(
        select(ManualQuestion).where(ManualQuestion.session_id == session_id)
        .order_by(ManualQuestion.created_at)
    ).all()
    return ManualSessionDetail(
        **ManualSessionRead.model_validate(session).model_dump(),
        questions=[question_response(item, db) for item in questions],
    )


@router.post(
    "/manual-sessions/{session_id}/questions",
    response_model=ManualQuestionRead, status_code=201,
)
def create_question(
    session_id: int, payload: QuestionCreate, db: Session = Depends(get_db)
):
    return answer_question(session_or_404(session_id, db), payload, db)


@router.get(
    "/manual-sessions/{session_id}/questions", response_model=list[ManualQuestionRead]
)
def list_questions(session_id: int, db: Session = Depends(get_db)):
    session_or_404(session_id, db)
    questions = db.scalars(
        select(ManualQuestion).where(ManualQuestion.session_id == session_id)
        .order_by(ManualQuestion.created_at)
    ).all()
    return [question_response(item, db) for item in questions]


@router.get("/manual-questions/{question_id}", response_model=ManualQuestionRead)
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = db.get(ManualQuestion, question_id)
    if not question:
        raise HTTPException(404, "Manual question not found")
    return question_response(question, db)


@router.post(
    "/machines/{machine_id}/explain-command", response_model=ManualQuestionRead
)
def explain_command(
    machine_id: int,
    payload: CommandExplanationRequest,
    db: Session = Depends(get_db),
):
    if db.get(MachineProfile, machine_id) is None:
        raise HTTPException(404, "Machine profile not found")
    match = re.fullmatch(r"\s*([GM])\s*(\d+(?:\.\d+)?)\s*", payload.command, re.I)
    if not match:
        raise HTTPException(422, "Command must be a G-code or M-code such as G84.")
    command = normalize_code(*match.groups())
    session = ManualQuestionSession(
        machine_profile_id=machine_id, title=f"Command explanation: {command}"
    )
    db.add(session); db.commit(); db.refresh(session)
    return answer_question(
        session,
        QuestionCreate(
            question=f"Explain {command} for this machine. Context: {payload.context}",
            category=QuestionCategory.COMMAND_MEANING,
            document_types=[
                DocumentType.CONTROLLER_MANUAL, DocumentType.PROGRAMMING_MANUAL,
            ],
        ),
        db,
    )


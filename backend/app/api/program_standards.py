import csv
from datetime import datetime
from hashlib import sha256
import io
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.analysis_projects import _get_project_or_404
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import (
    AnalysisFinding, AuditEvent, DocumentType, MachineProfile,
    ProcessingStatus, SourceDocument, utc_now,
)
from app.models.profile_extraction import MachineProfileRevision
from app.models.program_standards import (
    OrganizationalStandardProfile, ProgramComparisonFinding,
    ProgramComparisonRun, ReferenceProgram, StandardConvention,
    StandardConventionEvidence, StandardExtractionRun,
)
from app.program_standards.service import (
    ALGORITHM_VERSION, COMPARISON_VERSION, PARSER_VERSION,
    compare_program, extract_conventions, line_sections,
    parse_reference_program, similarity,
)
from app.schemas.program_standards import (
    ComparisonCreate, ComparisonFindingRead, ComparisonRunRead,
    ConventionBatchReviewRequest, ConventionReviewRequest, EligibilityRequest,
    ExceptionRequest, ReferenceProgramCreate, ReferenceProgramDetail,
    ReferenceProgramRead, ReferenceProgramUpdate, SAFETY_NOTICE,
    SideBySideRead, SimilarProgramRead, StandardDecisionRequest,
    StandardDraftRequest, StandardExtractionCreate, StandardExtractionRunRead,
    StandardConventionRead, StandardProfileRead,
)

router = APIRouter(tags=["approved programs and standards"])
ALLOWED_EXTENSIONS = {".nc", ".tap", ".gcode", ".cnc", ".txt", ".mpf"}


def _machine(machine_id: int, db: Session) -> MachineProfile:
    item = db.get(MachineProfile, machine_id)
    if not item:
        raise HTTPException(404, "Machine profile not found")
    return item


def _program(program_id: int, db: Session) -> ReferenceProgram:
    item = db.scalar(
        select(ReferenceProgram)
        .options(selectinload(ReferenceProgram.blocks))
        .where(ReferenceProgram.id == program_id)
    )
    if not item:
        raise HTTPException(404, "Reference program not found")
    return item


def _run(run_id: int, db: Session) -> StandardExtractionRun:
    item = db.get(StandardExtractionRun, run_id)
    if not item:
        raise HTTPException(404, "Standard extraction run not found")
    return item


def _standard(standard_id: int, db: Session) -> OrganizationalStandardProfile:
    item = db.scalar(
        select(OrganizationalStandardProfile)
        .options(
            selectinload(OrganizationalStandardProfile.conventions)
            .selectinload(StandardConvention.evidence)
            .selectinload(StandardConventionEvidence.reference_program)
        )
        .where(OrganizationalStandardProfile.id == standard_id)
    )
    if not item:
        raise HTTPException(404, "Programming standard not found")
    machine = db.get(MachineProfile, item.machine_profile_id)
    reasons = list(item.stale_reasons_json or [])
    if machine and machine.active_revision_id != item.machine_profile_revision_id:
        reasons.append("Active machine-profile revision changed")
    if item.summary_json.get("algorithm_version") not in {None, ALGORITHM_VERSION}:
        reasons.append("Convention extraction algorithm changed")
    source_hashes = item.summary_json.get("source_hashes", {})
    sources = list(db.scalars(select(ReferenceProgram).where(
        ReferenceProgram.id.in_(item.source_program_ids_json or [-1])
    )))
    for source in sources:
        if source.eligibility_status != "eligible":
            reasons.append(f"Reference program {source.id} is no longer eligible")
        if source_hashes.get(str(source.id)) not in {None, source.file_hash}:
            reasons.append(f"Reference program {source.id} source hash changed")
        if source.parser_version not in {None, PARSER_VERSION}:
            reasons.append(f"Reference program {source.id} parser version changed")
    if reasons:
        item.stale = True
        item.stale_reasons_json = sorted(set(reasons))
    return item


def _comparison(comparison_id: int, db: Session) -> ProgramComparisonRun:
    item = db.scalar(
        select(ProgramComparisonRun)
        .options(selectinload(ProgramComparisonRun.findings))
        .where(ProgramComparisonRun.id == comparison_id)
    )
    if not item:
        raise HTTPException(404, "Program comparison not found")
    return item


def _audit(db: Session, event: str, *, machine_id=None, analysis_id=None, metadata=None):
    db.add(AuditEvent(
        event_type=event,
        machine_profile_id=machine_id,
        analysis_project_id=analysis_id,
        metadata_json=metadata or {},
    ))


def _validate_revision(machine_id: int, revision_id: int, db: Session):
    revision = db.get(MachineProfileRevision, revision_id)
    if not revision or revision.machine_profile_id != machine_id:
        raise HTTPException(422, "Machine-profile revision does not belong to this machine")
    return revision


def _mark_dependent_state_stale(program: ReferenceProgram, reason: str, db: Session):
    standards = db.scalars(select(OrganizationalStandardProfile)).all()
    standard_ids = []
    for standard in standards:
        if program.id in (standard.source_program_ids_json or []):
            standard.stale = True
            standard.stale_reasons_json = sorted(set([
                *(standard.stale_reasons_json or []), reason,
            ]))
            standard_ids.append(standard.id)
    for comparison in db.scalars(select(ProgramComparisonRun).where(
        ProgramComparisonRun.standard_profile_id.in_(standard_ids or [-1])
    )):
        comparison.stale = True
        comparison.stale_reasons_json = sorted(set([
            *(comparison.stale_reasons_json or []), reason,
        ]))


async def _reference_payload(request: Request, machine_id: int, db: Session):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        raw = await request.json()
        payload = ReferenceProgramCreate.model_validate(raw)
        return payload, payload.source_text.encode(), payload.original_filename
    form = await request.form()
    uploaded = form.get("file")
    pasted = str(form.get("source_text") or "")
    file_bytes = await uploaded.read() if hasattr(uploaded, "read") else pasted.encode()
    filename = getattr(uploaded, "filename", None) or str(
        form.get("original_filename") or "pasted-program.nc"
    )
    metadata_raw = form.get("metadata")
    metadata = json.loads(str(metadata_raw)) if metadata_raw else {
        key: value for key, value in form.items()
        if key not in {"file", "source_text", "metadata"}
    }
    metadata["source_text"] = file_bytes.decode("utf-8", errors="strict")
    metadata.setdefault("original_filename", filename)
    payload = ReferenceProgramCreate.model_validate(metadata)
    return payload, file_bytes, filename


@router.post(
    "/machines/{machine_id}/reference-programs",
    response_model=ReferenceProgramRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reference_program(
    machine_id: int, request: Request, db: Session = Depends(get_db),
):
    _machine(machine_id, db)
    try:
        payload, raw_bytes, filename = await _reference_payload(request, machine_id, db)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(422, f"Invalid reference-program payload: {exc}") from exc
    _validate_revision(machine_id, payload.machine_profile_revision_id, db)
    if len(raw_bytes) > get_settings().max_program_source_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Program exceeds the configured upload limit")
    if filename and Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Unsupported CNC program file extension")
    digest = sha256(raw_bytes).hexdigest()
    duplicate = db.scalar(select(ReferenceProgram).where(
        ReferenceProgram.machine_profile_id == machine_id,
        ReferenceProgram.file_hash == digest,
    ))
    if duplicate:
        raise HTTPException(409, f"Duplicate reference program (existing id {duplicate.id})")
    data = payload.model_dump(exclude={"source_text"})
    source = SourceDocument(
        machine_profile_id=machine_id,
        title=f"Reference program: {payload.name}",
        document_type=DocumentType.APPROVED_PROGRAM,
        original_filename=filename,
        mime_type="text/plain",
        file_size_bytes=len(raw_bytes),
        extracted_text=payload.source_text,
        file_hash=digest,
        processing_status=ProcessingStatus.READY,
        page_count=1,
        page_data=[{"page_number": 1, "text": payload.source_text}],
        processed_at=utc_now(),
    )
    db.add(source)
    db.flush()
    program = ReferenceProgram(
        machine_profile_id=machine_id,
        source_document_id=source.id,
        file_hash=digest,
        source_text=payload.source_text,
        source_integrity_json={
            "sha256": digest, "byte_count": len(raw_bytes), "stored_path_exposed": False,
        },
        **data,
    )
    db.add(program)
    db.flush()
    _audit(db, "reference_program_imported", machine_id=machine_id, metadata={
        "reference_program_id": program.id,
        "file_hash": digest,
        "approval_status": program.approval_status,
        "eligibility_status": "pending",
        "ai_processing_allowed": program.ai_processing_allowed,
    })
    db.commit()
    db.refresh(program)
    return program


@router.get(
    "/machines/{machine_id}/reference-programs",
    response_model=list[ReferenceProgramRead],
)
def list_reference_programs(
    machine_id: int,
    eligibility_status: str | None = None,
    approval_status: str | None = None,
    program_type: str | None = None,
    db: Session = Depends(get_db),
):
    _machine(machine_id, db)
    query = select(ReferenceProgram).where(
        ReferenceProgram.machine_profile_id == machine_id
    )
    if eligibility_status:
        query = query.where(ReferenceProgram.eligibility_status == eligibility_status)
    if approval_status:
        query = query.where(ReferenceProgram.approval_status == approval_status)
    if program_type:
        query = query.where(ReferenceProgram.program_type == program_type)
    return db.scalars(query.order_by(ReferenceProgram.updated_at.desc())).all()


@router.get("/reference-programs/{program_id}", response_model=ReferenceProgramDetail)
def get_reference_program(program_id: int, db: Session = Depends(get_db)):
    return _program(program_id, db)


@router.put("/reference-programs/{program_id}", response_model=ReferenceProgramRead)
def update_reference_program(
    program_id: int, payload: ReferenceProgramUpdate, db: Session = Depends(get_db),
):
    program = _program(program_id, db)
    previous_scope = (
        program.controller_version, program.post_processor_revision,
        program.machine_variant, program.approval_status,
    )
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(program, key, value)
    current_scope = (
        program.controller_version, program.post_processor_revision,
        program.machine_variant, program.approval_status,
    )
    if previous_scope != current_scope:
        _mark_dependent_state_stale(program, "Reference-program applicability changed", db)
    _audit(db, "reference_program_updated", machine_id=program.machine_profile_id,
           metadata={"reference_program_id": program.id})
    db.commit()
    db.refresh(program)
    return program


@router.delete("/reference-programs/{program_id}", status_code=204)
def delete_reference_program(program_id: int, db: Session = Depends(get_db)):
    program = _program(program_id, db)
    program.approval_status = "deprecated"
    program.eligibility_status = "ineligible"
    program.eligibility_reason = "Deprecated through delete request; history preserved."
    _mark_dependent_state_stale(program, "Reference program deprecated", db)
    _audit(db, "reference_program_deprecated", machine_id=program.machine_profile_id,
           metadata={"reference_program_id": program.id})
    db.commit()


@router.post("/reference-programs/{program_id}/parse", response_model=ReferenceProgramDetail)
def parse_program(program_id: int, db: Session = Depends(get_db)):
    program = _program(program_id, db)
    try:
        parse_reference_program(program, db)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    _audit(db, "reference_program_parsed", machine_id=program.machine_profile_id,
           metadata={
               "reference_program_id": program.id,
               "parser_version": program.parser_version,
               "validation_summary": program.validation_summary_json,
           })
    db.commit()
    return _program(program.id, db)


@router.post("/reference-programs/{program_id}/mark-eligible", response_model=ReferenceProgramRead)
def mark_eligible(
    program_id: int, payload: EligibilityRequest, db: Session = Depends(get_db),
):
    program = _program(program_id, db)
    if not program.parsing_status.startswith("parsed"):
        raise HTTPException(422, "Parse the program before marking it eligible")
    if program.approval_status not in {"externally_reviewed", "approved_reference"}:
        raise HTTPException(
            422, "Only externally reviewed or approved-reference programs may be eligible"
        )
    program.eligibility_status = "eligible"
    program.eligibility_reason = payload.reason
    _audit(db, "reference_program_marked_eligible",
           machine_id=program.machine_profile_id,
           metadata={"reference_program_id": program.id, "reason": payload.reason})
    db.commit()
    db.refresh(program)
    return program


@router.post("/reference-programs/{program_id}/mark-ineligible", response_model=ReferenceProgramRead)
def mark_ineligible(
    program_id: int, payload: EligibilityRequest, db: Session = Depends(get_db),
):
    program = _program(program_id, db)
    program.eligibility_status = "ineligible"
    program.eligibility_reason = payload.reason
    _mark_dependent_state_stale(program, "Reference program became ineligible", db)
    _audit(db, "reference_program_marked_ineligible",
           machine_id=program.machine_profile_id,
           metadata={"reference_program_id": program.id, "reason": payload.reason})
    db.commit()
    db.refresh(program)
    return program


def _validate_extraction_programs(
    machine_id: int, payload: StandardExtractionCreate, db: Session,
) -> list[ReferenceProgram]:
    programs = list(db.scalars(
        select(ReferenceProgram)
        .options(selectinload(ReferenceProgram.blocks))
        .where(ReferenceProgram.id.in_(payload.reference_program_ids))
    ))
    if len(programs) != len(set(payload.reference_program_ids)):
        raise HTTPException(422, "One or more reference programs do not exist")
    if any(item.machine_profile_id != machine_id for item in programs):
        raise HTTPException(422, "Reference program ownership mismatch")
    if any(item.machine_profile_revision_id != payload.machine_profile_revision_id
           for item in programs):
        raise HTTPException(422, "Do not mix machine-profile revisions automatically")
    if any(item.eligibility_status != "eligible" for item in programs):
        raise HTTPException(422, "Only explicitly eligible programs may be extracted")
    if any(not item.parsing_status.startswith("parsed") for item in programs):
        raise HTTPException(422, "All reference programs must be parsed")
    post_versions = {
        item.post_processor_revision or item.post_processor_version or "unspecified"
        for item in programs
    }
    if payload.post_processor_revision:
        programs = [
            item for item in programs
            if (
                item.post_processor_revision or item.post_processor_version
            ) == payload.post_processor_revision
        ]
        if not programs:
            raise HTTPException(422, "No eligible program matches the requested post revision")
    elif len(post_versions) > 1:
        raise HTTPException(
            422,
            "Reference programs use different post revisions; select one revision explicitly",
        )
    scope = {
        (item.controller_version, item.machine_variant, tuple(item.installed_options_json or []))
        for item in programs
    }
    if len(scope) > 1:
        raise HTTPException(
            422, "Reference applicability is heterogeneous; split controller/variant/options"
        )
    return programs


@router.post(
    "/machines/{machine_id}/standard-extraction-runs",
    response_model=StandardExtractionRunRead,
)
def create_standard_extraction(
    machine_id: int, payload: StandardExtractionCreate, db: Session = Depends(get_db),
):
    _machine(machine_id, db)
    _validate_revision(machine_id, payload.machine_profile_revision_id, db)
    programs = _validate_extraction_programs(machine_id, payload, db)
    run = StandardExtractionRun(
        machine_profile_id=machine_id,
        machine_profile_revision_id=payload.machine_profile_revision_id,
        selected_reference_program_ids_json=[item.id for item in programs],
        algorithm_version=ALGORITHM_VERSION,
        settings_json={
            **payload.settings,
            "post_processor_revision": payload.post_processor_revision,
            "deterministic_only": True,
            "external_ai_used": False,
        },
    )
    db.add(run)
    db.flush()
    extract_conventions(run, programs, db)
    run.completed_at = utc_now()
    _audit(db, "standard_extraction_completed", machine_id=machine_id, metadata={
        "run_id": run.id, "program_ids": run.selected_reference_program_ids_json,
        "algorithm_version": ALGORITHM_VERSION,
    })
    db.commit()
    db.refresh(run)
    return run


@router.get(
    "/machines/{machine_id}/standard-extraction-runs",
    response_model=list[StandardExtractionRunRead],
)
def list_standard_extractions(machine_id: int, db: Session = Depends(get_db)):
    _machine(machine_id, db)
    return db.scalars(select(StandardExtractionRun).where(
        StandardExtractionRun.machine_profile_id == machine_id
    ).order_by(StandardExtractionRun.created_at.desc())).all()


@router.get(
    "/standard-extraction-runs/{run_id}",
    response_model=StandardExtractionRunRead,
)
def get_standard_extraction(run_id: int, db: Session = Depends(get_db)):
    return _run(run_id, db)


def _convention_read(convention: StandardConvention) -> StandardConventionRead:
    value = StandardConventionRead.model_validate(convention)
    for index, evidence in enumerate(convention.evidence):
        value.evidence[index].program_name = evidence.reference_program.name
    return value


@router.get(
    "/standard-extraction-runs/{run_id}/proposals",
    response_model=list[StandardConventionRead],
)
def list_convention_proposals(
    run_id: int,
    category: str | None = None,
    review_status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    _run(run_id, db)
    query = (
        select(StandardConvention)
        .options(
            selectinload(StandardConvention.evidence)
            .selectinload(StandardConventionEvidence.reference_program)
        )
        .where(StandardConvention.extraction_run_id == run_id)
    )
    if category:
        query = query.where(StandardConvention.category == category)
    if review_status:
        query = query.where(StandardConvention.review_status == review_status)
    conventions = list(db.scalars(query.order_by(
        StandardConvention.category, StandardConvention.title
    )))
    if search:
        term = search.casefold()
        conventions = [
            item for item in conventions
            if term in f"{item.title} {item.description} {item.convention_key}".casefold()
            or any(term in evidence.excerpt.casefold() for evidence in item.evidence)
        ]
    return [_convention_read(item) for item in conventions]


@router.put("/standard-conventions/{convention_id}/review", response_model=StandardConventionRead)
def review_convention(
    convention_id: int, payload: ConventionReviewRequest, db: Session = Depends(get_db),
):
    convention = db.get(StandardConvention, convention_id)
    if not convention:
        raise HTTPException(404, "Convention not found")
    if payload.review_status == "accepted_with_edit":
        if not payload.expected_pattern_json or not payload.review_note:
            raise HTTPException(422, "Edited acceptance requires a pattern and review note")
        convention.expected_pattern_json = payload.expected_pattern_json
    if payload.review_status in {"rejected", "deferred"} and not payload.review_note:
        raise HTTPException(422, "Rejecting or deferring requires a review note")
    convention.review_status = payload.review_status
    convention.review_note = payload.review_note
    convention.reviewed_at = utc_now()
    run = _run(convention.extraction_run_id, db)
    _audit(db, "standard_convention_reviewed", machine_id=run.machine_profile_id,
           metadata={
               "convention_id": convention.id,
               "review_status": convention.review_status,
               "frequency_classification": convention.frequency_classification,
           })
    db.commit()
    convention = db.scalar(
        select(StandardConvention)
        .options(
            selectinload(StandardConvention.evidence)
            .selectinload(StandardConventionEvidence.reference_program)
        ).where(StandardConvention.id == convention.id)
    )
    return _convention_read(convention)


@router.post("/standard-extraction-runs/{run_id}/proposals/batch-review")
def batch_review_conventions(
    run_id: int, payload: ConventionBatchReviewRequest, db: Session = Depends(get_db),
):
    run = _run(run_id, db)
    if (
        payload.review_status == "accepted"
        and not payload.acknowledge_frequency_is_not_requirement
    ):
        raise HTTPException(422, "Acknowledge that frequency is not a requirement")
    conventions = list(db.scalars(select(StandardConvention).where(
        StandardConvention.extraction_run_id == run.id,
        StandardConvention.id.in_(payload.convention_ids),
    )))
    succeeded, failed = [], []
    by_id = {item.id: item for item in conventions}
    for convention_id in payload.convention_ids:
        item = by_id.get(convention_id)
        reason = None
        if not item:
            reason = "convention_not_in_run"
        elif item.review_status != "pending":
            reason = "already_reviewed"
        elif payload.review_status == "accepted" and (
            item.proposal_status == "conflicting" or item.safety_relevant
        ):
            reason = "individual_review_required"
        if reason:
            failed.append({"convention_id": convention_id, "reason": reason})
            continue
        item.review_status = payload.review_status
        item.review_note = "Protected batch review; frequency is not authority."
        item.reviewed_at = utc_now()
        succeeded.append(item.id)
    _audit(db, "standard_convention_batch_reviewed",
           machine_id=run.machine_profile_id,
           metadata={"run_id": run.id, "succeeded": succeeded, "failed": failed})
    db.commit()
    return {"succeeded": succeeded, "failed": failed}


@router.post(
    "/standard-extraction-runs/{run_id}/apply-to-draft",
    response_model=StandardProfileRead,
)
def apply_standard_draft(
    run_id: int, payload: StandardDraftRequest, db: Session = Depends(get_db),
):
    run = _run(run_id, db)
    proposals = list(db.scalars(
        select(StandardConvention)
        .options(selectinload(StandardConvention.evidence))
        .where(StandardConvention.extraction_run_id == run.id)
    ))
    pending = [item for item in proposals if item.review_status == "pending"]
    accepted = [
        item for item in proposals
        if item.review_status in {"accepted", "accepted_with_edit"}
    ]
    if pending:
        raise HTTPException(409, f"{len(pending)} convention proposals remain pending")
    if not accepted:
        raise HTTPException(409, "At least one convention must be accepted")
    revision_number = (db.scalar(select(func.max(
        OrganizationalStandardProfile.revision_number
    )).where(
        OrganizationalStandardProfile.machine_profile_id == run.machine_profile_id
    )) or 0) + 1
    standard = OrganizationalStandardProfile(
        machine_profile_id=run.machine_profile_id,
        machine_profile_revision_id=run.machine_profile_revision_id,
        name=payload.name,
        revision_number=revision_number,
        status="draft",
        source_program_ids_json=run.selected_reference_program_ids_json,
        summary_json={
            "accepted_convention_count": len(accepted),
            "algorithm_version": run.algorithm_version,
            "source_hashes": {
                str(program.id): program.file_hash
                for program in db.scalars(select(ReferenceProgram).where(
                    ReferenceProgram.id.in_(run.selected_reference_program_ids_json)
                ))
            },
            "frequency_is_not_requirement": True,
        },
    )
    db.add(standard)
    db.flush()
    for source in accepted:
        clone = StandardConvention(
            standard_profile_id=standard.id,
            # Preserve extraction provenance in the standard summary/source IDs
            # without returning approved standard copies as run proposals.
            extraction_run_id=None,
            convention_key=source.convention_key,
            category=source.category,
            title=source.title,
            description=source.description,
            convention_type=source.convention_type,
            expected_pattern_json=source.expected_pattern_json,
            condition_json=source.condition_json,
            expected_behavior_json=source.expected_behavior_json,
            applicability_json=source.applicability_json,
            severity=source.severity,
            confidence=source.confidence,
            support_count=source.support_count,
            eligible_program_count=source.eligible_program_count,
            support_percentage=source.support_percentage,
            frequency_classification=source.frequency_classification,
            proposal_status=source.proposal_status,
            review_status=source.review_status,
            review_note=source.review_note,
            safety_relevant=source.safety_relevant,
            reviewed_at=source.reviewed_at,
        )
        db.add(clone)
        db.flush()
        for evidence in source.evidence:
            db.add(StandardConventionEvidence(
                standard_convention_id=clone.id,
                reference_program_id=evidence.reference_program_id,
                gcode_block_id=evidence.gcode_block_id,
                line_start=evidence.line_start,
                line_end=evidence.line_end,
                excerpt=evidence.excerpt,
                evidence_type=evidence.evidence_type,
                match_context_json=evidence.match_context_json,
            ))
    _audit(db, "standard_draft_created", machine_id=run.machine_profile_id,
           metadata={"run_id": run.id, "standard_id": standard.id})
    db.commit()
    return _standard(standard.id, db)


@router.post("/standard-extraction-runs/{run_id}/rerun", response_model=StandardExtractionRunRead)
def rerun_standard_extraction(run_id: int, db: Session = Depends(get_db)):
    previous = _run(run_id, db)
    return create_standard_extraction(
        previous.machine_profile_id,
        StandardExtractionCreate(
            machine_profile_revision_id=previous.machine_profile_revision_id,
            reference_program_ids=previous.selected_reference_program_ids_json,
            post_processor_revision=(previous.settings_json or {}).get(
                "post_processor_revision"
            ),
            settings=previous.settings_json,
        ),
        db,
    )


@router.get(
    "/machines/{machine_id}/standard-profiles",
    response_model=list[StandardProfileRead],
)
def list_standards(machine_id: int, db: Session = Depends(get_db)):
    _machine(machine_id, db)
    ids = list(db.scalars(select(OrganizationalStandardProfile.id).where(
        OrganizationalStandardProfile.machine_profile_id == machine_id
    ).order_by(OrganizationalStandardProfile.revision_number.desc())))
    return [_standard(item, db) for item in ids]


@router.get("/standard-profiles/{standard_id}", response_model=StandardProfileRead)
def get_standard(standard_id: int, db: Session = Depends(get_db)):
    return _standard(standard_id, db)


@router.post("/standard-profiles/{standard_id}/submit-for-review", response_model=StandardProfileRead)
def submit_standard(
    standard_id: int, payload: StandardDecisionRequest, db: Session = Depends(get_db),
):
    standard = _standard(standard_id, db)
    if standard.status != "draft":
        raise HTTPException(409, "Only a draft can be submitted")
    standard.status = "under_review"
    standard.summary_json = {**standard.summary_json, "submission_note": payload.note}
    _audit(db, "standard_submitted_for_review",
           machine_id=standard.machine_profile_id,
           metadata={"standard_id": standard.id})
    db.commit()
    return _standard(standard.id, db)


@router.post("/standard-profiles/{standard_id}/approve", response_model=StandardProfileRead)
def approve_standard(
    standard_id: int, payload: StandardDecisionRequest, db: Session = Depends(get_db),
):
    standard = _standard(standard_id, db)
    if standard.status not in {"draft", "under_review"}:
        raise HTTPException(409, "Only a draft or under-review standard can be approved")
    for previous in db.scalars(select(OrganizationalStandardProfile).where(
        OrganizationalStandardProfile.machine_profile_id == standard.machine_profile_id,
        OrganizationalStandardProfile.status == "approved",
        OrganizationalStandardProfile.id != standard.id,
    )):
        previous.status = "superseded"
        previous.superseded_at = utc_now()
    standard.status = "approved"
    standard.approved_at = utc_now()
    standard.summary_json = {**standard.summary_json, "approval_note": payload.note}
    _audit(db, "standard_explicitly_approved",
           machine_id=standard.machine_profile_id,
           metadata={"standard_id": standard.id, "note": payload.note})
    db.commit()
    return _standard(standard.id, db)


@router.post("/standard-profiles/{standard_id}/reject", response_model=StandardProfileRead)
def reject_standard(
    standard_id: int, payload: StandardDecisionRequest, db: Session = Depends(get_db),
):
    standard = _standard(standard_id, db)
    if standard.status == "approved":
        raise HTTPException(409, "An approved historical standard cannot be rejected")
    standard.status = "rejected"
    standard.summary_json = {**standard.summary_json, "rejection_note": payload.note}
    _audit(db, "standard_rejected", machine_id=standard.machine_profile_id,
           metadata={"standard_id": standard.id})
    db.commit()
    return _standard(standard.id, db)


@router.get("/standard-profiles/{standard_id}/compare/{other_id}")
def compare_standard_revisions(
    standard_id: int, other_id: int, db: Session = Depends(get_db),
):
    left, right = _standard(standard_id, db), _standard(other_id, db)
    if left.machine_profile_id != right.machine_profile_id:
        raise HTTPException(422, "Standards belong to different machines")
    left_map = {item.convention_key: item for item in left.conventions}
    right_map = {item.convention_key: item for item in right.conventions}
    return {
        "left_standard_id": left.id, "right_standard_id": right.id,
        "added": sorted(set(right_map) - set(left_map)),
        "removed": sorted(set(left_map) - set(right_map)),
        "changed": sorted(
            key for key in set(left_map) & set(right_map)
            if left_map[key].expected_pattern_json != right_map[key].expected_pattern_json
        ),
        "advisory_only": True,
        "historical_similarity_is_not_certification": True,
        "qualified_review_required": True,
        "safety_notice": SAFETY_NOTICE,
    }


@router.post(
    "/analyses/{analysis_id}/standard-comparisons",
    response_model=ComparisonRunRead,
)
def create_comparison(
    analysis_id: int, payload: ComparisonCreate, db: Session = Depends(get_db),
):
    project = _get_project_or_404(analysis_id, db)
    if not project.gcode_source:
        raise HTTPException(422, "Analysis has no G-code source")
    standard = _standard(payload.standard_profile_id, db)
    if standard.status != "approved":
        raise HTTPException(409, "Only an explicitly approved standard may be compared")
    if standard.machine_profile_id != project.machine_profile_id:
        raise HTTPException(422, "Standard belongs to a different machine")
    if standard.machine_profile_revision_id != project.machine_profile_revision_id:
        raise HTTPException(
            422, "Standard and analysis use different machine-profile revisions"
        )
    reference = None
    if payload.reference_program_id:
        reference = _program(payload.reference_program_id, db)
        if reference.id not in standard.source_program_ids_json:
            raise HTTPException(422, "Reference program is outside this standard dataset")
    comparison = ProgramComparisonRun(
        analysis_project_id=project.id,
        machine_profile_revision_id=project.machine_profile_revision_id,
        standard_profile_id=standard.id,
        reference_program_id=reference.id if reference else None,
        parser_version=PARSER_VERSION,
        algorithm_version=COMPARISON_VERSION,
        standard_revision_snapshot_json={
            "id": standard.id,
            "revision_number": standard.revision_number,
            "updated_at": standard.updated_at.isoformat(),
            "machine_profile_revision_id": standard.machine_profile_revision_id,
        },
    )
    db.add(comparison)
    db.flush()
    compare_program(comparison, project, standard.conventions, db)
    _audit(db, "program_standard_comparison_completed",
           machine_id=project.machine_profile_id, analysis_id=project.id,
           metadata={
               "comparison_id": comparison.id,
               "standard_id": standard.id,
               "reference_program_id": comparison.reference_program_id,
           })
    db.commit()
    return _comparison(comparison.id, db)


@router.get(
    "/analyses/{analysis_id}/standard-comparisons",
    response_model=list[ComparisonRunRead],
)
def list_comparisons(analysis_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(analysis_id, db)
    ids = list(db.scalars(select(ProgramComparisonRun.id).where(
        ProgramComparisonRun.analysis_project_id == analysis_id
    ).order_by(ProgramComparisonRun.created_at.desc())))
    return [_comparison(item, db) for item in ids]


@router.get("/standard-comparisons/{comparison_id}", response_model=ComparisonRunRead)
def get_comparison(comparison_id: int, db: Session = Depends(get_db)):
    comparison = _comparison(comparison_id, db)
    standard = _standard(comparison.standard_profile_id, db)
    if standard.status != "approved" or standard.stale:
        comparison.stale = True
        comparison.stale_reasons_json = sorted(set([
            *(comparison.stale_reasons_json or []), "Standard changed or became stale",
        ]))
        db.commit()
    return comparison


@router.get(
    "/standard-comparisons/{comparison_id}/findings",
    response_model=list[ComparisonFindingRead],
)
def get_comparison_findings(comparison_id: int, db: Session = Depends(get_db)):
    _comparison(comparison_id, db)
    return db.scalars(select(ProgramComparisonFinding).where(
        ProgramComparisonFinding.comparison_run_id == comparison_id
    ).order_by(ProgramComparisonFinding.line_number, ProgramComparisonFinding.id)).all()


@router.put(
    "/standard-comparison-findings/{finding_id}/exception",
    response_model=ComparisonFindingRead,
)
def classify_exception(
    finding_id: int, payload: ExceptionRequest, db: Session = Depends(get_db),
):
    finding = db.get(ProgramComparisonFinding, finding_id)
    if not finding:
        raise HTTPException(404, "Comparison finding not found")
    finding.exception_classification = payload.classification
    finding.exception_note = payload.note
    finding.status = "classified_exception"
    comparison = _comparison(finding.comparison_run_id, db)
    project = _get_project_or_404(comparison.analysis_project_id, db)
    _audit(db, "program_difference_classified",
           machine_id=project.machine_profile_id, analysis_id=project.id,
           metadata={
               "finding_id": finding.id,
               "classification": payload.classification,
           })
    db.commit()
    db.refresh(finding)
    return finding


@router.get(
    "/analyses/{analysis_id}/similar-reference-programs",
    response_model=list[SimilarProgramRead],
)
def similar_programs(
    analysis_id: int, limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(analysis_id, db)
    programs = list(db.scalars(
        select(ReferenceProgram)
        .options(selectinload(ReferenceProgram.blocks))
        .where(
            ReferenceProgram.machine_profile_id == project.machine_profile_id,
            ReferenceProgram.eligibility_status == "eligible",
        )
    ))
    ranked = []
    for program in programs:
        score, reasons, differences = similarity(program, project)
        ranked.append(SimilarProgramRead(
            program=ReferenceProgramRead.model_validate(program),
            similarity_score=score,
            match_reasons=reasons,
            differences=differences,
        ))
    return sorted(ranked, key=lambda item: item.similarity_score, reverse=True)[:limit]


@router.get(
    "/standard-comparisons/{comparison_id}/side-by-side",
    response_model=SideBySideRead,
)
def side_by_side(comparison_id: int, db: Session = Depends(get_db)):
    comparison = _comparison(comparison_id, db)
    project = _get_project_or_404(comparison.analysis_project_id, db)
    reference = (
        _program(comparison.reference_program_id, db)
        if comparison.reference_program_id else None
    )
    if not reference:
        standard = _standard(comparison.standard_profile_id, db)
        reference = _program(standard.source_program_ids_json[0], db)
    deterministic = list(db.scalars(select(AnalysisFinding).where(
        AnalysisFinding.analysis_project_id == project.id
    )))
    return SideBySideRead(
        comparison_id=comparison.id,
        current_program=project.gcode_source or "",
        reference_program=reference.source_text,
        sections=line_sections(project.gcode_source or "", reference.source_text),
        source_metadata={
            "reference_program_id": reference.id,
            "reference_program_name": reference.name,
            "file_hash": reference.file_hash,
            "post_processor_revision": reference.post_processor_revision,
            "machine_profile_revision_id": reference.machine_profile_revision_id,
        },
        deterministic_findings=[{
            "id": item.id, "severity": item.severity.value,
            "title": item.title, "line_number": item.line_number,
            "finding_type": "deterministic_validation",
        } for item in deterministic],
        convention_findings=[
            ComparisonFindingRead.model_validate(item)
            for item in comparison.findings
        ],
    )


def _standard_report_payload(standard: OrganizationalStandardProfile):
    return {
        "advisory_only": True,
        "historical_similarity_is_not_certification": True,
        "qualified_review_required": True,
        "safety_notice": SAFETY_NOTICE,
        "standard": {
            "id": standard.id, "name": standard.name,
            "revision_number": standard.revision_number,
            "status": standard.status,
            "machine_profile_id": standard.machine_profile_id,
            "machine_profile_revision_id": standard.machine_profile_revision_id,
            "source_program_ids": standard.source_program_ids_json,
            "summary": standard.summary_json,
        },
        "accepted_conventions": [{
            "key": item.convention_key, "category": item.category,
            "title": item.title, "pattern": item.expected_pattern_json,
            "support": f"{item.support_count}/{item.eligible_program_count}",
            "exceptions": sum(
                evidence.evidence_type in {"contradicting", "exception"}
                for evidence in item.evidence
            ),
            "review_note": item.review_note,
        } for item in standard.conventions],
    }


def _response_report(payload: dict, format: str, filename: str):
    if format == "json":
        return Response(json.dumps(payload, indent=2), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{filename}.json"'})
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["category", "title", "comparison_type", "line", "note"])
        rows = payload.get("findings") or payload.get("accepted_conventions") or []
        for row in rows:
            writer.writerow([
                row.get("category", ""), row.get("title", ""),
                row.get("comparison_type", row.get("support", "")),
                row.get("line_number", ""), row.get("exception_note", row.get("review_note", "")),
            ])
        return Response(output.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'})
    lines = [
        f"# {filename.replace('-', ' ').title()}", "",
        f"> {SAFETY_NOTICE}", "",
        "Historical similarity is not certification.", "",
        "```json", json.dumps(payload, indent=2), "```", "",
    ]
    return Response("\n".join(lines), media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="{filename}.md"'})


@router.get("/standard-profiles/{standard_id}/report")
def standard_report(
    standard_id: int,
    format: str = Query("markdown", pattern="^(markdown|json|csv)$"),
    db: Session = Depends(get_db),
):
    standard = _standard(standard_id, db)
    _audit(db, "standard_report_exported", machine_id=standard.machine_profile_id,
           metadata={"standard_id": standard.id, "format": format})
    db.commit()
    return _response_report(
        _standard_report_payload(standard), format,
        f"programming-standard-v{standard.revision_number}",
    )


@router.get("/standard-comparisons/{comparison_id}/report")
def comparison_report(
    comparison_id: int,
    format: str = Query("markdown", pattern="^(markdown|json|csv)$"),
    db: Session = Depends(get_db),
):
    comparison = _comparison(comparison_id, db)
    project = _get_project_or_404(comparison.analysis_project_id, db)
    standard = _standard(comparison.standard_profile_id, db)
    deterministic = list(db.scalars(select(AnalysisFinding).where(
        AnalysisFinding.analysis_project_id == project.id
    )))
    payload = {
        "advisory_only": True,
        "historical_similarity_is_not_certification": True,
        "qualified_review_required": True,
        "safety_notice": SAFETY_NOTICE,
        "machine_profile_id": project.machine_profile_id,
        "machine_profile_revision_id": comparison.machine_profile_revision_id,
        "standard": {
            "id": standard.id, "revision_number": standard.revision_number,
            "source_program_ids": standard.source_program_ids_json,
            "source_hashes": standard.summary_json.get("source_hashes", {}),
        },
        "summary": comparison.summary_json,
        "findings": [{
            "title": item.title, "comparison_type": item.comparison_type,
            "line_number": item.line_number, "source_line": item.source_line,
            "expected": item.expected_pattern_json,
            "observed": item.observed_pattern_json,
            "exception_classification": item.exception_classification,
            "exception_note": item.exception_note,
        } for item in comparison.findings],
        "deterministic_findings": [{
            "title": item.title, "severity": item.severity.value,
            "line_number": item.line_number, "rule_id": item.rule_id,
        } for item in deterministic],
    }
    _audit(db, "comparison_report_exported",
           machine_id=project.machine_profile_id, analysis_id=project.id,
           metadata={"comparison_id": comparison.id, "format": format})
    db.commit()
    return _response_report(payload, format, f"program-comparison-{comparison.id}")

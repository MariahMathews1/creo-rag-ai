import json
from collections import Counter

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.analysis_projects import revision_snapshot
from app.db.session import get_db
from app.models.entities import AuditEvent, MachineProfile, utc_now
from app.models.profile_extraction import MachineProfileRevision
from app.models.program_standards import ReferenceProgram
from app.models.translation import TranslationAlignment, TranslationAlignmentLink, TranslationExample
from app.schemas.translation import AlignmentRead, DatasetSummary, LinkCreate, LinkRead, LinkUpdate, StatusRequest, TranslationCreate, TranslationPreviewRequest, TranslationRead, TranslationUpdate
from app.schemas.translation_ai import AIConsentRequest
from app.translation.service import generate_alignment, normalize_cl_pattern, normalize_gcode_pattern, normalize_text, parse_and_validate, refresh_alignment, source_hash

router = APIRouter(tags=["Translation Examples"])
STATUS_TRANSITIONS = {"unknown": {"candidate", "invalid"}, "candidate": {"reviewed", "invalid"}, "reviewed": {"verified_successful", "invalid"}, "verified_successful": {"deprecated"}, "deprecated": set(), "invalid": set()}


def example_query():
    return select(TranslationExample).options(selectinload(TranslationExample.alignments).selectinload(TranslationAlignment.links))


def example_or_404(example_id: int, db: Session) -> TranslationExample:
    row = db.scalar(example_query().where(TranslationExample.id == example_id))
    if row is None: raise HTTPException(404, "Translation example not found")
    return row


def context(machine_id: int, revision_id: int, reference_id: int | None, db: Session):
    machine = db.get(MachineProfile, machine_id); revision = db.get(MachineProfileRevision, revision_id)
    if machine is None: raise HTTPException(404, "Machine profile not found")
    if revision is None or revision.machine_profile_id != machine_id: raise HTTPException(422, "Machine-profile revision does not belong to selected machine")
    if reference_id:
        reference = db.get(ReferenceProgram, reference_id)
        if reference is None or reference.machine_profile_id != machine_id: raise HTTPException(422, "Reference program does not belong to selected machine")
    return machine, revision


def audit(db: Session, event: str, row: TranslationExample, **metadata):
    db.add(AuditEvent(event_type=event, machine_profile_id=row.machine_profile_id, metadata_json={"translation_example_id": row.id, **metadata}))


def create_row(payload: TranslationCreate, db: Session, response: Response | None = None):
    machine, revision = context(payload.machine_profile_id, payload.machine_profile_revision_id, payload.reference_program_id, db)
    cl_text, gc_text = normalize_text(payload.cl_source_text), normalize_text(payload.gcode_source_text)
    cl_hash, gc_hash = source_hash(cl_text), source_hash(gc_text)
    existing = db.scalar(example_query().where(TranslationExample.machine_profile_revision_id == revision.id,
        TranslationExample.cl_source_hash == cl_hash, TranslationExample.gcode_source_hash == gc_hash))
    if existing:
        if response is not None: response.headers["X-Duplicate-Translation-Example"] = "true"
        return existing
    data = payload.model_dump(exclude={
        "cl_source_text", "gcode_source_text", "controller_name",
        "controller_version",
    })
    row = TranslationExample(**data, cl_source_text=cl_text, gcode_source_text=gc_text,
        cl_source_hash=cl_hash, gcode_source_hash=gc_hash,
        controller_name=payload.controller_name or revision.controller_name or machine.controller_name,
        controller_version=payload.controller_version or revision.controller_version,
        machine_context_snapshot_json=revision_snapshot(revision, machine))
    parse_and_validate(row, machine, revision)
    if revision.status not in {"approved", "active"}:
        row.verification_note = "WARNING: created against a non-approved machine-profile revision."
    db.add(row); db.flush(); audit(db, "translation_example_created", row, status=row.verification_status)
    db.commit(); return example_or_404(row.id, db)


@router.post("/translations", response_model=TranslationRead, status_code=status.HTTP_201_CREATED)
def create_translation(payload: TranslationCreate, response: Response, db: Session = Depends(get_db)):
    return create_row(payload, db, response)


@router.post("/translations/{example_id}/ai-processing-consent", response_model=TranslationRead)
def set_ai_processing_consent(example_id: int, payload: AIConsentRequest, db: Session = Depends(get_db)):
    row = example_or_404(example_id, db)
    row.ai_processing_allowed = payload.allowed
    audit(db, "translation_ai_processing_consent_changed", row, allowed=payload.allowed, reviewer_label=payload.reviewer_label)
    db.commit()
    return example_or_404(example_id, db)


@router.post("/translations/import", response_model=TranslationRead, status_code=status.HTTP_201_CREATED)
async def import_translation(metadata_json: str = Form(...), cl_file: UploadFile = File(...), gcode_file: UploadFile = File(...), db: Session = Depends(get_db)):
    allowed_cl, allowed_gc = {".cl", ".ncl", ".apt", ".txt"}, {".nc", ".tap", ".gcode", ".txt"}
    def suffix(name): return "." + (name or "").lower().rsplit(".", 1)[-1] if "." in (name or "") else ""
    if suffix(cl_file.filename) not in allowed_cl or suffix(gcode_file.filename) not in allowed_gc: raise HTTPException(422, "Unsupported CL/NCL or G-code file extension")
    try:
        metadata = json.loads(metadata_json); metadata.update({"cl_source_text": (await cl_file.read()).decode("utf-8-sig"),
            "gcode_source_text": (await gcode_file.read()).decode("utf-8-sig"), "cl_original_filename": cl_file.filename, "gcode_original_filename": gcode_file.filename})
        payload = TranslationCreate.model_validate(metadata)
    except Exception as exc: raise HTTPException(422, f"Invalid paired-file import: {exc}") from exc
    return create_row(payload, db)


@router.get("/translations", response_model=list[TranslationRead])
def list_translations(machine_id: int | None = None, machine_profile_revision_id: int | None = None, controller: str | None = None,
    post_revision: str | None = None, operation: str | None = None, verification_status: str | None = None,
    search: str | None = None, include_inactive: bool = False, db: Session = Depends(get_db)):
    q = example_query()
    if not include_inactive: q = q.where(TranslationExample.verification_status.notin_(["deprecated", "invalid"]))
    if machine_id: q = q.where(TranslationExample.machine_profile_id == machine_id)
    if machine_profile_revision_id: q = q.where(TranslationExample.machine_profile_revision_id == machine_profile_revision_id)
    if controller: q = q.where(TranslationExample.controller_name == controller)
    if post_revision: q = q.where(TranslationExample.post_processor_revision == post_revision)
    if operation: q = q.where(TranslationExample.operation_type == operation)
    if verification_status: q = q.where(TranslationExample.verification_status == verification_status)
    if search:
        term = f"%{search}%"; q = q.where(or_(TranslationExample.name.ilike(term), TranslationExample.part_identifier.ilike(term), TranslationExample.program_identifier.ilike(term), TranslationExample.project_identifier.ilike(term)))
    return list(db.scalars(q.order_by(TranslationExample.updated_at.desc())).unique())


@router.get("/translations/summary", response_model=DatasetSummary)
def translations_summary(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(TranslationExample)))
    count = Counter(r.verification_status for r in rows)
    def grouped(attr): return [{attr: key or "unknown", "count": value} for key, value in Counter(getattr(r, attr) for r in rows).items()]
    return DatasetSummary(total=len(rows), candidates=count["candidate"], reviewed=count["reviewed"], verified=count["verified_successful"], deprecated=count["deprecated"], invalid=count["invalid"],
        by_machine=grouped("machine_profile_id"), by_post_revision=grouped("post_processor_revision"), by_operation=grouped("operation_type"))


@router.post("/translations/preview")
def preview_translation(payload: TranslationPreviewRequest, db: Session = Depends(get_db)):
    machine, revision = context(payload.machine_profile_id, payload.machine_profile_revision_id, None, db)
    cl_text, gcode_text = normalize_text(payload.cl_source_text), normalize_text(payload.gcode_source_text)
    row = TranslationExample(
        machine_profile_id=machine.id, machine_profile_revision_id=revision.id,
        name="Unsaved translation preview", cl_source_text=cl_text,
        cl_source_hash=source_hash(cl_text), gcode_source_text=gcode_text,
        gcode_source_hash=source_hash(gcode_text), verification_status="candidate",
    )
    parse_and_validate(row, machine, revision)
    return {
        "cl_source_hash": row.cl_source_hash, "gcode_source_hash": row.gcode_source_hash,
        "cl_parse_summary_json": row.cl_parse_summary_json,
        "gcode_parse_summary_json": row.gcode_parse_summary_json,
        "validation_summary_json": row.validation_summary_json,
        "machine_context_snapshot_json": revision_snapshot(revision, machine),
        "revision_warning": None if revision.status in {"approved", "active"} else "Selected revision is not approved and cannot support verified-successful status.",
        "advisory_only": True,
    }


@router.get("/translations/explorer")
def translation_explorer(command: str | None = None, machine_id: int | None = None, post_revision: str | None = None,
    operation: str | None = None, verification_status: str = "verified_successful", db: Session = Depends(get_db)):
    q = example_query().where(TranslationExample.verification_status == verification_status)
    if machine_id: q = q.where(TranslationExample.machine_profile_id == machine_id)
    if post_revision: q = q.where(TranslationExample.post_processor_revision == post_revision)
    if operation: q = q.where(TranslationExample.operation_type == operation)
    groups = Counter()
    for row in db.scalars(q).unique():
        machine = db.get(MachineProfile, row.machine_profile_id)
        for alignment in row.alignments:
            for link in alignment.links:
                if link.review_status not in {"confirmed", "edited"} or link.cl_record_start is None or link.gcode_block_start is None: continue
                cl = row.parsed_cl_records_json[link.cl_record_start]; gc = row.parsed_gcode_blocks_json[link.gcode_block_start]
                if command and cl["command"] != command.upper(): continue
                cp, gp = normalize_cl_pattern(cl["text"]), normalize_gcode_pattern(gc["text"], cl["command"])
                groups[(row.machine_profile_id, machine.name if machine else "Unknown", row.controller_name, row.post_processor_revision, row.operation_type, cl["command"], cp, gp)] += 1
    return [{"machine_profile_id": key[0], "machine": key[1], "controller": key[2], "post_revision": key[3], "operation": key[4], "cl_command": key[5], "cl_pattern": key[6], "gcode_pattern": key[7], "count": count}
            for key, count in groups.items()]


@router.get("/translations/{example_id}", response_model=TranslationRead)
def get_translation(example_id: int, db: Session = Depends(get_db)): return example_or_404(example_id, db)


@router.get("/translations/{example_id}/history")
def translation_history(example_id: int, db: Session = Depends(get_db)):
    row = example_or_404(example_id, db)
    events = db.scalars(select(AuditEvent).where(AuditEvent.machine_profile_id == row.machine_profile_id).order_by(AuditEvent.created_at.desc())).all()
    return [{"id": event.id, "event_type": event.event_type, "metadata_json": event.metadata_json, "created_at": event.created_at}
            for event in events if event.metadata_json.get("translation_example_id") == row.id]


@router.put("/translations/{example_id}", response_model=TranslationRead)
def update_translation(example_id: int, payload: TranslationUpdate, db: Session = Depends(get_db)):
    row = example_or_404(example_id, db)
    if row.verification_status in {"verified_successful", "deprecated", "invalid"}: raise HTTPException(409, "Final-status examples are immutable")
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(row,k,v)
    audit(db, "translation_example_updated", row); db.commit(); return example_or_404(row.id, db)


def transition(row: TranslationExample, target: str, payload: StatusRequest, db: Session):
    if target not in STATUS_TRANSITIONS.get(row.verification_status, set()): raise HTTPException(409, f"Cannot transition {row.verification_status} to {target}")
    revision = db.get(MachineProfileRevision, row.machine_profile_revision_id)
    if target == "verified_successful":
        issues = []
        if not payload.acknowledgement: issues.append("Explicit historical-translation acknowledgement is required")
        if not row.cl_source_hash or not row.gcode_source_hash: issues.append("Both source hashes are required")
        if row.cl_parse_summary_json.get("fatal") or row.gcode_parse_summary_json.get("fatal"): issues.append("Fatal parser failure is unresolved")
        if not row.post_processor_name and row.post_processor_name != "UNKNOWN": issues.append("Post processor name or UNKNOWN marker is required")
        if revision is None or revision.machine_profile_id != row.machine_profile_id: issues.append("Machine revision identity mismatch")
        if revision and revision.status not in {"approved", "active"}: issues.append("Machine-profile revision is not approved")
        if row.validation_summary_json.get("blocking_count") and len(payload.note.strip()) < 20: issues.append("Blocking findings require a substantive review justification")
        if issues: raise HTTPException(422, {"message":"Verification gate failed", "issues":issues})
    prior_status = row.verification_status
    row.verification_status = target; row.verification_note = payload.note; row.imported_by_label = payload.reviewer_label
    if target == "reviewed": row.reviewed_at = utc_now()
    if target == "verified_successful": row.verified_at = utc_now()
    if target == "deprecated": row.deprecated_at = utc_now()
    event = {"verified_successful":"translation_example_verified", "deprecated":"translation_example_deprecated", "invalid":"translation_example_invalidated"}.get(target,"translation_example_status_changed")
    audit(db,event,row,from_status=prior_status,to_status=target); db.commit(); return example_or_404(row.id,db)


@router.post("/translations/{example_id}/review", response_model=TranslationRead)
def review_translation(example_id: int, payload: StatusRequest, db: Session = Depends(get_db)): return transition(example_or_404(example_id,db),"reviewed",payload,db)
@router.post("/translations/{example_id}/candidate", response_model=TranslationRead)
def candidate_translation(example_id: int, payload: StatusRequest, db: Session = Depends(get_db)): return transition(example_or_404(example_id,db),"candidate",payload,db)
@router.post("/translations/{example_id}/verify", response_model=TranslationRead)
def verify_translation(example_id: int, payload: StatusRequest, db: Session = Depends(get_db)): return transition(example_or_404(example_id,db),"verified_successful",payload,db)
@router.post("/translations/{example_id}/deprecate", response_model=TranslationRead)
def deprecate_translation(example_id: int, payload: StatusRequest, db: Session = Depends(get_db)): return transition(example_or_404(example_id,db),"deprecated",payload,db)
@router.post("/translations/{example_id}/invalidate", response_model=TranslationRead)
def invalidate_translation(example_id: int, payload: StatusRequest, db: Session = Depends(get_db)): return transition(example_or_404(example_id,db),"invalid",payload,db)


@router.post("/translations/{example_id}/alignment", response_model=AlignmentRead)
def create_alignment(example_id: int, db: Session = Depends(get_db)):
    row=example_or_404(example_id,db); alignment=generate_alignment(db,row); audit(db,"translation_alignment_created",row,alignment_id=alignment.id); db.commit(); return db.scalar(select(TranslationAlignment).options(selectinload(TranslationAlignment.links)).where(TranslationAlignment.id==alignment.id))
@router.get("/translations/{example_id}/alignment", response_model=AlignmentRead | None)
def get_alignment(example_id: int, db: Session = Depends(get_db)):
    example_or_404(example_id,db); return db.scalar(select(TranslationAlignment).options(selectinload(TranslationAlignment.links)).where(TranslationAlignment.translation_example_id==example_id).order_by(TranslationAlignment.id.desc()))
@router.post("/translation-alignments/{alignment_id}/links", response_model=LinkRead)
def create_link(alignment_id:int,payload:LinkCreate,db:Session=Depends(get_db)):
    a=db.get(TranslationAlignment,alignment_id)
    if not a: raise HTTPException(404,"Alignment not found")
    validate_link_bounds(a, payload.model_dump())
    link=TranslationAlignmentLink(alignment_id=alignment_id,**payload.model_dump()); a.links.append(link); db.flush(); refresh_alignment(a)
    audit(db,"translation_manual_link_created",a.example,alignment_id=a.id,link_id=link.id); db.commit(); db.refresh(link); return link
@router.put("/translation-alignment-links/{link_id}",response_model=LinkRead)
def update_link(link_id:int,payload:LinkUpdate,db:Session=Depends(get_db)):
    link=db.get(TranslationAlignmentLink,link_id)
    if not link: raise HTTPException(404,"Alignment link not found")
    changes = payload.model_dump(exclude_unset=True)
    validate_link_bounds(link.alignment, {"cl_record_start": changes.get("cl_record_start", link.cl_record_start), "cl_record_end": changes.get("cl_record_end", link.cl_record_end), "gcode_block_start": changes.get("gcode_block_start", link.gcode_block_start), "gcode_block_end": changes.get("gcode_block_end", link.gcode_block_end)})
    for k,v in changes.items(): setattr(link,k,v)
    if payload.review_status is None: link.review_status="edited"
    refresh_alignment(link.alignment); db.commit(); db.refresh(link); return link


def validate_link_bounds(alignment: TranslationAlignment, values: dict):
    cl_start, cl_end = values.get("cl_record_start"), values.get("cl_record_end")
    gc_start, gc_end = values.get("gcode_block_start"), values.get("gcode_block_end")
    if cl_start is None and gc_start is None: raise HTTPException(422, "At least one CL or G-code span is required")
    cl_end = cl_start if cl_end is None else cl_end; gc_end = gc_start if gc_end is None else gc_end
    if cl_start is not None and (cl_end < cl_start or cl_end >= len(alignment.example.parsed_cl_records_json)): raise HTTPException(422, "CL span is outside this example")
    if gc_start is not None and (gc_end < gc_start or gc_end >= len(alignment.example.parsed_gcode_blocks_json)): raise HTTPException(422, "G-code span is outside this example")
def review_link(link_id:int,target:str,db:Session):
    link=db.get(TranslationAlignmentLink,link_id)
    if not link: raise HTTPException(404,"Alignment link not found")
    link.review_status=target; refresh_alignment(link.alignment); audit(db,f"translation_alignment_{target}",link.alignment.example,link_id=link.id); db.commit(); db.refresh(link); return link
@router.post("/translation-alignment-links/{link_id}/confirm",response_model=LinkRead)
def confirm_link(link_id:int,db:Session=Depends(get_db)): return review_link(link_id,"confirmed",db)
@router.post("/translation-alignment-links/{link_id}/reject",response_model=LinkRead)
def reject_link(link_id:int,db:Session=Depends(get_db)): return review_link(link_id,"rejected",db)

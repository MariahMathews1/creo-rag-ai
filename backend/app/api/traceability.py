from dataclasses import asdict
from hashlib import sha256
import csv
from io import StringIO
from time import perf_counter

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.alignment.engine import SAFETY_NOTICE, run_alignment
from app.cl_parser import CLParser
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import AnalysisProject, AuditEvent, utc_now
from app.models.traceability import AlignmentIssue, AlignmentLink, AlignmentRun, CLRecord, GCodeBlock
from app.parsers.gcode import GCodeParser
from app.schemas.traceability import (
    AlignmentLinkRead, AlignmentRunRead, CLRecordRead, GCodeBlockRead,
    LinkUpdate, ParseSummary, SourcePairRead,
)

router = APIRouter(tags=["traceability"])
CL_EXTENSIONS = {".ncl", ".cl", ".cls", ".apt", ".txt"}
GCODE_EXTENSIONS = {".nc", ".tap", ".gcode", ".ngc", ".txt"}


def project_or_404(analysis_id: int, db: Session) -> AnalysisProject:
    value = db.get(AnalysisProject, analysis_id)
    if not value:
        raise HTTPException(404, "Analysis project not found")
    return value


def _invalidate(project: AnalysisProject, db: Session) -> None:
    active_ids = list(db.scalars(select(AlignmentRun.id).where(
        AlignmentRun.analysis_project_id == project.id, AlignmentRun.stale.is_(False)
    )))
    db.execute(update(AlignmentRun).where(
        AlignmentRun.analysis_project_id == project.id
    ).values(stale=True))
    for run_id in active_ids:
        db.add(AuditEvent(
            event_type="alignment_marked_stale", machine_profile_id=project.machine_profile_id,
            analysis_project_id=project.id, metadata_json={"alignment_run_id": run_id},
        ))
    project.alignment_status = "not_started"
    project.alignment_summary_json = {}


async def _read_source(file: UploadFile | None, text: str | None, kind: str) -> tuple[str, str | None]:
    if file:
        content = await file.read()
        if not content:
            raise HTTPException(422, "Source file is empty")
        settings = get_settings()
        if len(content) > settings.max_program_source_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"Source exceeds {settings.max_program_source_upload_mb} MB")
        extension = "." + file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
        allowed = CL_EXTENSIONS if kind == "cl" else GCODE_EXTENSIONS
        if extension not in allowed:
            raise HTTPException(422, f"Unsupported {kind.upper()} source extension")
        try:
            source = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            source = content.decode("latin-1")
        return source, file.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] if file.filename else None
    if not text or not text.strip():
        raise HTTPException(422, "Source text or file is required")
    if len(text.encode()) > get_settings().max_program_source_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Source text exceeds configured limit")
    return text, None


async def _set_source(
    analysis_id: int, kind: str, db: Session, file: UploadFile | None, text: str | None
) -> SourcePairRead:
    project = project_or_404(analysis_id, db)
    source, filename = await _read_source(file, text, kind)
    if kind == "cl" and not any(token in source.upper() for token in ("GOTO", "PARTNO", "MACHIN", "LOADTL", "PPRINT")):
        raise HTTPException(422, "Content does not appear to contain CL/NCL records")
    if kind == "gcode" and not any(token in source.upper() for token in ("G0", "G1", "M30", "%", "O")):
        raise HTTPException(422, "Content does not appear to contain G-code")
    setattr(project, f"{kind}_source", source)
    setattr(project, f"{kind}_original_filename", filename)
    setattr(project, f"{kind}_file_hash", sha256(source.encode()).hexdigest())
    setattr(project, f"{kind}_processing_status", "pending")
    db.execute(delete(CLRecord if kind == "cl" else GCodeBlock).where(
        (CLRecord if kind == "cl" else GCodeBlock).analysis_project_id == project.id
    ))
    _invalidate(project, db)
    db.add(AuditEvent(
        event_type=f"{kind}_source_uploaded", machine_profile_id=project.machine_profile_id,
        analysis_project_id=project.id,
        metadata_json={"filename": filename, "hash": getattr(project, f"{kind}_file_hash")},
    ))
    db.commit(); db.refresh(project)
    return _source_response(project)


def _source_response(project: AnalysisProject) -> SourcePairRead:
    return SourcePairRead(
        analysis_id=project.id, cl_source=project.cl_source, gcode_source=project.gcode_source,
        cl_original_filename=project.cl_original_filename,
        gcode_original_filename=project.gcode_original_filename,
        cl_file_hash=project.cl_file_hash, gcode_file_hash=project.gcode_file_hash,
        cl_processing_status=project.cl_processing_status,
        gcode_processing_status=project.gcode_processing_status,
        alignment_status=project.alignment_status,
    )


@router.post("/analyses/{analysis_id}/cl-source", response_model=SourcePairRead)
async def upload_cl_source(analysis_id: int, file: UploadFile | None = File(None), text: str | None = Form(None), db: Session = Depends(get_db)):
    return await _set_source(analysis_id, "cl", db, file, text)


@router.post("/analyses/{analysis_id}/gcode-source", response_model=SourcePairRead)
async def upload_gcode_source(analysis_id: int, file: UploadFile | None = File(None), text: str | None = Form(None), db: Session = Depends(get_db)):
    return await _set_source(analysis_id, "gcode", db, file, text)


@router.get("/analyses/{analysis_id}/sources", response_model=SourcePairRead)
def get_sources(analysis_id: int, db: Session = Depends(get_db)):
    return _source_response(project_or_404(analysis_id, db))


@router.delete("/analyses/{analysis_id}/{kind}-source", status_code=204)
def delete_source(analysis_id: int, kind: str, db: Session = Depends(get_db)):
    if kind not in {"cl", "gcode"}:
        raise HTTPException(404, "Unknown source type")
    project = project_or_404(analysis_id, db)
    setattr(project, f"{kind}_source", None); setattr(project, f"{kind}_file_hash", None)
    setattr(project, f"{kind}_original_filename", None)
    setattr(project, f"{kind}_processing_status", "not_provided")
    db.execute(delete(CLRecord if kind == "cl" else GCodeBlock).where(
        (CLRecord if kind == "cl" else GCodeBlock).analysis_project_id == project.id
    ))
    _invalidate(project, db); db.commit()


@router.post("/analyses/{analysis_id}/parse-cl", response_model=ParseSummary)
def parse_cl(analysis_id: int, db: Session = Depends(get_db)):
    project = project_or_404(analysis_id, db)
    if not project.cl_source:
        raise HTTPException(422, "CL source is required")
    started = perf_counter(); parsed = CLParser().parse(project.cl_source)
    db.execute(delete(CLRecord).where(CLRecord.analysis_project_id == project.id))
    for record in parsed.records:
        db.add(CLRecord(
            analysis_project_id=project.id, record_index=record.record_index,
            line_number=record.line_number, original_text=record.original_text,
            normalized_text=record.normalized_text, command=record.command,
            original_command=record.original_command, parameters_json=record.parameters,
            numeric_parameters_json=record.numeric_parameters,
            named_parameters_json=record.named_parameters,
            coordinates_json=record.coordinates, motion_type=record.motion_type,
            tool_number=record.tool_number, spindle_speed=record.spindle_speed,
            feed_rate=record.feed_rate, coolant_state=record.coolant_state,
            operation_name=record.operation_name, state_before_json=record.state_before,
            state_after_json=record.state_after, parse_errors_json=record.parse_errors,
        ))
    project.cl_processing_status = "parsed"
    db.add(AuditEvent(event_type="cl_source_parsed", machine_profile_id=project.machine_profile_id,
                      analysis_project_id=project.id, metadata_json={"record_count": len(parsed.records)}))
    db.commit()
    return ParseSummary(
        record_count=len(parsed.records),
        parsed_count=sum(r.command != "UNKNOWN" and not r.parse_errors for r in parsed.records),
        unsupported_count=sum(r.command == "UNKNOWN" for r in parsed.records),
        error_count=parsed.error_count, units=parsed.units,
        tool_count=len({r.tool_number for r in parsed.records if r.tool_number is not None}),
        motion_record_count=sum(r.motion_type in {"rapid", "feed", "arc"} for r in parsed.records),
        duration_ms=round((perf_counter()-started)*1000, 2),
    )


@router.post("/analyses/{analysis_id}/parse-gcode", response_model=ParseSummary)
def parse_gcode(analysis_id: int, db: Session = Depends(get_db)):
    project = project_or_404(analysis_id, db)
    if not project.gcode_source:
        raise HTTPException(422, "G-code source is required")
    started = perf_counter()
    parsed = GCodeParser(set(project.machine_profile.supported_work_offsets or [])).parse(project.gcode_source)
    db.execute(delete(GCodeBlock).where(GCodeBlock.analysis_project_id == project.id))
    for index, block in enumerate(parsed.blocks):
        state = asdict(block.modal_state)
        db.add(GCodeBlock(
            analysis_project_id=project.id, block_index=index, line_number=block.line_number,
            original_text=block.original_text, cleaned_text=block.cleaned_text,
            sequence_number=block.sequence_number, program_number=block.program_number,
            g_codes_json=block.g_codes, m_codes_json=block.m_codes,
            coordinates_json=block.coordinates, feed_rate=block.feed_rate,
            spindle_speed=block.spindle_speed, tool_number=block.tool_number,
            active_tool=block.modal_state.active_tool, work_offset=block.work_offset,
            motion_mode=block.modal_state.motion_mode, state_before_json=asdict(block.state_before),
            state_after_json=state, parse_errors_json=block.parse_errors,
        ))
    project.gcode_processing_status = "parsed"; project.last_analyzed_at = utc_now()
    db.add(AuditEvent(event_type="gcode_source_parsed", machine_profile_id=project.machine_profile_id,
                      analysis_project_id=project.id, metadata_json={"block_count": len(parsed.blocks)}))
    db.commit()
    units = next((b.modal_state.units for b in parsed.blocks if b.modal_state.units), None)
    return ParseSummary(
        record_count=len(parsed.blocks), parsed_count=sum(not b.parse_errors for b in parsed.blocks),
        unsupported_count=0, error_count=sum(bool(b.parse_errors) for b in parsed.blocks),
        units={"G20": "inch", "G21": "mm"}.get(units, units),
        tool_count=len({b.tool_number for b in parsed.blocks if b.tool_number is not None}),
        motion_record_count=sum(bool(b.coordinates) for b in parsed.blocks),
        duration_ms=round((perf_counter()-started)*1000, 2),
    )


@router.get("/analyses/{analysis_id}/cl-records", response_model=list[CLRecordRead])
def list_cl_records(analysis_id: int, page: int = Query(1, ge=1), page_size: int = Query(200, ge=1, le=500), command: str | None = None, motion_type: str | None = None, db: Session = Depends(get_db)):
    query = select(CLRecord).where(CLRecord.analysis_project_id == analysis_id)
    if command: query = query.where(CLRecord.command == command.upper())
    if motion_type: query = query.where(CLRecord.motion_type == motion_type)
    return db.scalars(query.order_by(CLRecord.record_index).offset((page-1)*page_size).limit(page_size)).all()


@router.get("/analyses/{analysis_id}/cl-records/{record_id}", response_model=CLRecordRead)
def get_cl_record(analysis_id: int, record_id: int, db: Session = Depends(get_db)):
    value = db.get(CLRecord, record_id)
    if not value or value.analysis_project_id != analysis_id: raise HTTPException(404, "CL record not found")
    return value


@router.get("/analyses/{analysis_id}/gcode-blocks", response_model=list[GCodeBlockRead])
def list_gcode_blocks(analysis_id: int, page: int = Query(1, ge=1), page_size: int = Query(200, ge=1, le=500), motion_type: str | None = None, db: Session = Depends(get_db)):
    query = select(GCodeBlock).where(GCodeBlock.analysis_project_id == analysis_id)
    if motion_type: query = query.where(GCodeBlock.motion_mode == motion_type)
    return db.scalars(query.order_by(GCodeBlock.block_index).offset((page-1)*page_size).limit(page_size)).all()


@router.post("/analyses/{analysis_id}/alignment-runs", response_model=AlignmentRunRead)
def start_alignment(analysis_id: int, db: Session = Depends(get_db)):
    project = project_or_404(analysis_id, db)
    if project.cl_processing_status != "parsed": parse_cl(analysis_id, db)
    if project.gcode_processing_status != "parsed": parse_gcode(analysis_id, db)
    db.add(AuditEvent(event_type="alignment_started", machine_profile_id=project.machine_profile_id,
                      analysis_project_id=project.id, metadata_json={}))
    run = run_alignment(project, db, get_settings())
    db.add(AuditEvent(event_type="alignment_completed", machine_profile_id=project.machine_profile_id,
                      analysis_project_id=project.id, metadata_json={"run_id": run.id, "version": run.version}))
    db.commit(); return run


@router.get("/analyses/{analysis_id}/alignment-runs", response_model=list[AlignmentRunRead])
def list_alignment_runs(analysis_id: int, db: Session = Depends(get_db)):
    return db.scalars(select(AlignmentRun).where(AlignmentRun.analysis_project_id == analysis_id).order_by(AlignmentRun.version.desc())).all()


@router.get("/alignment-runs/{run_id}", response_model=AlignmentRunRead)
def get_alignment_run(run_id: int, db: Session = Depends(get_db)):
    value = db.get(AlignmentRun, run_id)
    if not value: raise HTTPException(404, "Alignment run not found")
    return value


@router.get("/alignment-runs/{run_id}/links", response_model=list[AlignmentLinkRead])
def get_links(run_id: int, confidence_min: float = Query(0, ge=0, le=1), confidence_max: float = Query(1, ge=0, le=1), status: str | None = None, db: Session = Depends(get_db)):
    query = select(AlignmentLink).where(AlignmentLink.alignment_run_id == run_id, AlignmentLink.confidence >= confidence_min, AlignmentLink.confidence <= confidence_max)
    if status: query = query.where(AlignmentLink.status == status)
    return db.scalars(query.order_by(AlignmentLink.id)).all()


@router.post("/alignment-runs/{run_id}/links", response_model=AlignmentLinkRead)
def create_manual_link(run_id: int, payload: LinkUpdate, db: Session = Depends(get_db)):
    run = db.get(AlignmentRun, run_id)
    if not run: raise HTTPException(404, "Alignment run not found")
    if payload.cl_record_id is None or payload.gcode_block_id is None:
        raise HTTPException(422, "Manual links require CL and G-code record IDs")
    link = AlignmentLink(
        alignment_run_id=run.id, cl_record_id=payload.cl_record_id,
        gcode_block_id=payload.gcode_block_id, link_type="manual", confidence=0.0,
        match_reasons_json=["Created by local qualified reviewer"],
        mismatch_reasons_json=[], score_components_json={}, status="modified",
        review_note=payload.review_note, review_label=payload.review_label,
        assigned_by="local_user", reviewed_at=utc_now(),
    )
    db.add(link)
    db.add(AuditEvent(event_type="manual_alignment_created",
                      analysis_project_id=run.analysis_project_id,
                      metadata_json={"run_id": run.id}))
    db.commit(); db.refresh(link); return link


@router.get("/alignment-runs/{run_id}/issues")
def get_issues(run_id: int, db: Session = Depends(get_db)):
    return db.scalars(select(AlignmentIssue).where(AlignmentIssue.alignment_run_id == run_id).order_by(AlignmentIssue.id)).all()


@router.put("/alignment-issues/{issue_id}")
def label_issue(issue_id: int, label: str = Form(...), db: Session = Depends(get_db)):
    issue = db.get(AlignmentIssue, issue_id)
    if not issue: raise HTTPException(404, "Alignment issue not found")
    issue.label = label; issue.assigned_by = "local_user"; db.commit(); db.refresh(issue)
    return issue


def _review(link_id: int, status: str, db: Session) -> AlignmentLink:
    link = db.get(AlignmentLink, link_id)
    if not link: raise HTTPException(404, "Alignment link not found")
    link.status = status; link.assigned_by = "local_user"; link.reviewed_at = utc_now()
    _refresh_review_counts(link.alignment_run, db)
    db.add(AuditEvent(event_type=f"alignment_link_{status}", analysis_project_id=link.alignment_run.analysis_project_id,
                      metadata_json={"link_id": link.id, "run_id": link.alignment_run_id}))
    db.commit(); db.refresh(link); return link


def _refresh_review_counts(run: AlignmentRun, db: Session) -> None:
    db.flush()
    summary = dict(run.summary_json or {})
    summary["confirmed_link_count"] = db.scalar(select(func.count()).select_from(
        AlignmentLink
    ).where(AlignmentLink.alignment_run_id == run.id, AlignmentLink.status == "confirmed")) or 0
    summary["rejected_link_count"] = db.scalar(select(func.count()).select_from(
        AlignmentLink
    ).where(AlignmentLink.alignment_run_id == run.id, AlignmentLink.status == "rejected")) or 0
    run.summary_json = summary


@router.post("/alignment-links/{link_id}/confirm", response_model=AlignmentLinkRead)
def confirm_link(link_id: int, db: Session = Depends(get_db)): return _review(link_id, "confirmed", db)


@router.post("/alignment-links/{link_id}/reject", response_model=AlignmentLinkRead)
def reject_link(link_id: int, db: Session = Depends(get_db)): return _review(link_id, "rejected", db)


@router.put("/alignment-links/{link_id}", response_model=AlignmentLinkRead)
def update_link(link_id: int, payload: LinkUpdate, db: Session = Depends(get_db)):
    link = db.get(AlignmentLink, link_id)
    if not link: raise HTTPException(404, "Alignment link not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(link, key, value)
    link.assigned_by = "local_user"; link.reviewed_at = utc_now()
    _refresh_review_counts(link.alignment_run, db)
    db.add(AuditEvent(event_type="alignment_link_modified", analysis_project_id=link.alignment_run.analysis_project_id,
                      metadata_json={"link_id": link.id}))
    db.commit(); db.refresh(link); return link


@router.post("/alignment-runs/{run_id}/recalculate", response_model=AlignmentRunRead)
def recalculate(run_id: int, db: Session = Depends(get_db)):
    prior = db.get(AlignmentRun, run_id)
    if not prior: raise HTTPException(404, "Alignment run not found")
    reviewed = [l for l in prior.links if l.status in {"confirmed", "rejected", "modified"}]
    new = run_alignment(prior.analysis_project, db, get_settings())
    for old in reviewed:
        match = next((l for l in new.links if l.cl_record_id == old.cl_record_id and l.gcode_block_id == old.gcode_block_id), None)
        if match:
            match.status, match.review_note, match.review_label = old.status, old.review_note, old.review_label
            match.assigned_by, match.reviewed_at = old.assigned_by, old.reviewed_at
    db.commit(); db.refresh(new); return new


@router.get("/alignment-runs/{run_id}/report")
def export_report(run_id: int, format: str = Query("markdown", pattern="^(markdown|json|csv)$"), db: Session = Depends(get_db)):
    run = db.get(AlignmentRun, run_id)
    if not run: raise HTTPException(404, "Alignment run not found")
    project = run.analysis_project
    links, issues = list(run.links), list(run.issues)
    payload = {
        "project": {"id": project.id, "name": project.name, "machine_profile_id": project.machine_profile_id},
        "source_integrity": run.source_integrity_json, "algorithm_version": run.algorithm_version,
        "settings": run.settings_json, "summary": run.summary_json,
        "links": [{"id": l.id, "cl_record_id": l.cl_record_id, "gcode_block_id": l.gcode_block_id,
                   "confidence": l.confidence, "status": l.status, "reasons": l.match_reasons_json,
                   "review_note": l.review_note} for l in links],
        "issues": [{"type": i.issue_type, "title": i.title, "description": i.description} for i in issues],
        "validation_findings": [
            {"rule_id": finding.rule_id, "severity": finding.severity.value,
             "line_number": finding.line_number, "title": finding.title}
            for finding in project.findings
        ],
        "safety_notice": SAFETY_NOTICE,
    }
    db.add(AuditEvent(event_type="traceability_report_exported", machine_profile_id=project.machine_profile_id,
                      analysis_project_id=project.id, metadata_json={"run_id": run.id, "format": format}))
    db.commit()
    if format == "json": return payload
    if format == "csv":
        output = StringIO(); writer = csv.writer(output)
        writer.writerow(["link_id", "cl_record_id", "gcode_block_id", "confidence", "status", "reasons"])
        for link in links: writer.writerow([link.id, link.cl_record_id, link.gcode_block_id, link.confidence, link.status, "; ".join(link.match_reasons_json)])
        return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="traceability-v{run.version}.csv"'})
    lines = [f"# Traceability Report — {project.name}", "", f"Alignment v{run.version} · {run.algorithm_version}", "",
             "## Summary", "", *[f"- {key.replace('_', ' ').title()}: {value}" for key, value in run.summary_json.items()],
             "", "## Mappings", ""]
    lines += [f"- Link {l.id}: CL {l.cl_record_id} → G-code {l.gcode_block_id}; confidence {l.confidence:.2f}; {l.status}; {'; '.join(l.match_reasons_json)}" for l in links]
    lines += ["", "## Issues", ""] + [f"- {i.issue_type}: {i.description}" for i in issues]
    lines += ["", "## Deterministic validation findings", ""] + [
        f"- {finding.severity.value}: {finding.rule_id} — {finding.title}"
        for finding in project.findings
    ]
    lines += ["", "## Safety notice", "", SAFETY_NOTICE]
    return Response("\n".join(lines), media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="traceability-v{run.version}.md"'})

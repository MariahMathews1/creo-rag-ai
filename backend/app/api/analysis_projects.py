from fastapi import APIRouter, Depends, HTTPException, status
from hashlib import sha256
from types import SimpleNamespace
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.ai.provider import MockAIProvider
from app.db.session import get_db
from app.models.entities import (
    AnalysisFinding,
    AnalysisProject,
    MachineProfile,
    ProjectStatus,
    Severity,
)
from app.parsers.gcode import GCodeParser
from app.schemas.analysis import (
    AIExplanationRequest,
    AIExplanationResponse,
    AnalysisFindingRead,
    AnalysisProjectCreate,
    AnalysisProjectRead,
    AnalysisRunResponse,
    SourceTextUpdate,
)
from app.validators.engine import ValidationEngine
from app.models.traceability import AlignmentRun

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _get_project_or_404(project_id: int, db: Session) -> AnalysisProject:
    project = db.get(AnalysisProject, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Analysis project not found")
    return project


@router.post("", response_model=AnalysisProjectRead, status_code=status.HTTP_201_CREATED)
def create_analysis_project(payload: AnalysisProjectCreate, db: Session = Depends(get_db)):
    machine = db.get(MachineProfile, payload.machine_profile_id)
    if machine is None:
        raise HTTPException(status_code=422, detail="Selected machine profile does not exist")
    project = AnalysisProject(**payload.model_dump())
    from app.api.profile_extraction import ensure_initial_revision
    revision = ensure_initial_revision(machine, db)
    project.machine_profile_revision_id = revision.id
    project.machine_profile_snapshot_json = revision_snapshot(revision, machine)
    if project.cl_source:
        project.cl_file_hash = sha256(project.cl_source.encode()).hexdigest()
        project.cl_processing_status = "pending"
    if project.gcode_source:
        project.gcode_file_hash = sha256(project.gcode_source.encode()).hexdigest()
        project.gcode_processing_status = "pending"
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def revision_snapshot(revision, machine=None) -> dict:
    keys = (
        "id", "revision_number", "manufacturer", "model", "controller_name",
        "controller_manufacturer", "controller_model", "controller_version",
        "machine_type", "axis_count", "x_min", "x_max",
        "y_min", "y_max", "z_min", "z_max", "max_spindle_rpm",
        "max_feed_rate", "rapid_traverse_rate", "supported_work_offsets_json",
        "approved_g_codes_json", "approved_m_codes_json",
        "restricted_commands_json", "safe_start_template",
        "tool_change_template", "program_end_template",
    )
    snapshot = {key: getattr(revision, key) for key in keys}
    snapshot["rapid_z_review_threshold"] = (
        getattr(machine, "rapid_z_review_threshold", None) if machine else None
    )
    return snapshot


def validation_profile_from_snapshot(snapshot: dict):
    """Build the immutable validation view captured when the analysis was created."""
    return SimpleNamespace(
        x_min=snapshot.get("x_min"), x_max=snapshot.get("x_max"),
        y_min=snapshot.get("y_min"), y_max=snapshot.get("y_max"),
        z_min=snapshot.get("z_min"), z_max=snapshot.get("z_max"),
        max_spindle_rpm=snapshot.get("max_spindle_rpm"),
        max_feed_rate=snapshot.get("max_feed_rate"),
        rapid_z_review_threshold=snapshot.get("rapid_z_review_threshold"),
        supported_work_offsets=snapshot.get("supported_work_offsets_json") or [],
        approved_g_codes=snapshot.get("approved_g_codes_json") or [],
        approved_m_codes=snapshot.get("approved_m_codes_json") or [],
        restricted_commands=snapshot.get("restricted_commands_json") or [],
        safe_start_template=snapshot.get("safe_start_template"),
        tool_change_template=snapshot.get("tool_change_template"),
        program_end_template=snapshot.get("program_end_template"),
    )


@router.get("", response_model=list[AnalysisProjectRead])
def list_analysis_projects(db: Session = Depends(get_db)):
    return db.scalars(
        select(AnalysisProject).order_by(AnalysisProject.updated_at.desc())
    ).all()


@router.get("/{project_id}", response_model=AnalysisProjectRead)
def get_analysis_project(project_id: int, db: Session = Depends(get_db)):
    return _get_project_or_404(project_id, db)


@router.put("/{project_id}/cl-source", response_model=AnalysisProjectRead)
def submit_cl_source(
    project_id: int, payload: SourceTextUpdate, db: Session = Depends(get_db)
):
    project = _get_project_or_404(project_id, db)
    project.cl_source = payload.text
    project.cl_file_hash = sha256(payload.text.encode()).hexdigest()
    project.cl_processing_status = "pending"
    project.alignment_status = "not_started"
    db.execute(update(AlignmentRun).where(
        AlignmentRun.analysis_project_id == project.id
    ).values(stale=True))
    project.status = ProjectStatus.DRAFT
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}/gcode-source", response_model=AnalysisProjectRead)
def submit_gcode_source(
    project_id: int, payload: SourceTextUpdate, db: Session = Depends(get_db)
):
    project = _get_project_or_404(project_id, db)
    project.gcode_source = payload.text
    project.gcode_file_hash = sha256(payload.text.encode()).hexdigest()
    project.gcode_processing_status = "pending"
    project.alignment_status = "not_started"
    db.execute(update(AlignmentRun).where(
        AlignmentRun.analysis_project_id == project.id
    ).values(stale=True))
    project.status = ProjectStatus.DRAFT
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/run", response_model=AnalysisRunResponse)
def run_analysis(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    if not project.gcode_source or not project.gcode_source.strip():
        raise HTTPException(status_code=422, detail="G-code source is required before analysis")
    if not project.machine_profile_revision_id or not project.machine_profile_snapshot_json:
        from app.api.profile_extraction import ensure_initial_revision
        from app.models.profile_extraction import MachineProfileRevision
        revision = (
            db.get(MachineProfileRevision, project.machine_profile_revision_id)
            if project.machine_profile_revision_id else None
        ) or ensure_initial_revision(project.machine_profile, db)
        project.machine_profile_revision_id = revision.id
        project.machine_profile_snapshot_json = revision_snapshot(revision, project.machine_profile)

    validation_profile = validation_profile_from_snapshot(project.machine_profile_snapshot_json)
    parsed = GCodeParser(
        set(validation_profile.supported_work_offsets or [])
    ).parse(project.gcode_source)
    results = ValidationEngine().validate(parsed, validation_profile)
    db.execute(
        delete(AnalysisFinding).where(
            AnalysisFinding.analysis_project_id == project.id
        )
    )
    for result in results:
        db.add(
            AnalysisFinding(
                analysis_project_id=project.id,
                severity=result.severity,
                category=result.category,
                title=result.title,
                description=result.description,
                line_number=result.line_number,
                source_line=result.source_line,
                rule_id=result.rule_id,
                recommendation=result.recommendation,
                confidence=result.confidence,
            )
        )
    if any(result.severity == Severity.BLOCKING for result in results):
        project.status = ProjectStatus.BLOCKED
    elif any(result.severity == Severity.WARNING for result in results):
        project.status = ProjectStatus.REVIEW_REQUIRED
    else:
        project.status = ProjectStatus.PASSED
    db.commit()
    db.refresh(project)
    findings = db.scalars(
        select(AnalysisFinding)
        .where(AnalysisFinding.analysis_project_id == project.id)
        .order_by(AnalysisFinding.line_number, AnalysisFinding.id)
    ).all()
    return AnalysisRunResponse(project=project, findings=findings)


@router.get("/{project_id}/findings", response_model=list[AnalysisFindingRead])
def get_findings(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(project_id, db)
    return db.scalars(
        select(AnalysisFinding)
        .where(AnalysisFinding.analysis_project_id == project_id)
        .order_by(AnalysisFinding.line_number, AnalysisFinding.id)
    ).all()


@router.post("/{project_id}/ai-explanation", response_model=AIExplanationResponse)
def request_ai_explanation(
    project_id: int, payload: AIExplanationRequest, db: Session = Depends(get_db)
):
    project = _get_project_or_404(project_id, db)
    provider = MockAIProvider()
    if payload.content_type == "gcode":
        explanation = provider.explain_gcode(payload.text or project.gcode_source or "")
    elif payload.content_type == "cl":
        explanation = provider.explain_cl_data(payload.text or project.cl_source or "")
    else:
        explanation = provider.summarize_findings(payload.text or "")
    return AIExplanationResponse(explanation=explanation)

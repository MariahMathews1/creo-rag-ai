from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.cl_parser.parser import CLParser
from app.db.session import get_db
from app.models.entities import AnalysisFinding, AnalysisProject
from app.models.gpost import GPostPreviewRun
from app.models.traceability import AlignmentLink, AlignmentRun, CLRecord, GCodeBlock
from app.models.translation import TranslationAlignment, TranslationExample
from app.parsers.gcode import GCodeParser
from app.services.toolpath.models import ToolpathResponse
from app.services.toolpath.service import build_toolpath

router = APIRouter(tags=["Toolpath Visualization"])


def source_param(source: str = Query("both", pattern="^(cl|gcode|both)$")) -> str:
    return source


@router.get("/analyses/{analysis_id}/toolpath", response_model=ToolpathResponse)
def analysis_toolpath(analysis_id: int, source: str = Depends(source_param), db: Session = Depends(get_db)):
    project = db.get(AnalysisProject, analysis_id)
    if not project: raise HTTPException(404, "Analysis project not found")
    cl = CLParser().parse(project.cl_source or "").records
    gc = GCodeParser(set(project.machine_profile.supported_work_offsets or [])).parse(project.gcode_source or "").blocks
    findings = list(db.scalars(select(AnalysisFinding).where(AnalysisFinding.analysis_project_id == project.id)))
    cl_links: dict[int, tuple[int, list[str]]] = {}; gc_links: dict[int, tuple[int, list[str]]] = {}
    run = db.scalar(select(AlignmentRun).where(AlignmentRun.analysis_project_id == project.id).order_by(AlignmentRun.version.desc()))
    if run:
        for link in db.scalars(select(AlignmentLink).options(selectinload(AlignmentLink.cl_record), selectinload(AlignmentLink.gcode_block)).where(AlignmentLink.alignment_run_id == run.id)):
            if link.cl_record and link.gcode_block:
                cl_links[link.cl_record.record_index] = (link.id, [f"gcode-{link.gcode_block.block_index}"])
                gc_links[link.gcode_block.block_index] = (link.id, [f"cl-{link.cl_record.record_index}"])
    return build_toolpath(cl_records=cl, gcode_blocks=gc, machine_type=project.machine_profile.machine_type.value, source=source, findings=findings, alignment_by_cl=cl_links, alignment_by_gc=gc_links)


@router.get("/translations/{example_id}/toolpath", response_model=ToolpathResponse)
def translation_toolpath(example_id: int, source: str = Depends(source_param), db: Session = Depends(get_db)):
    row = db.scalar(select(TranslationExample).options(selectinload(TranslationExample.alignments).selectinload(TranslationAlignment.links)).where(TranslationExample.id == example_id))
    if not row: raise HTTPException(404, "Translation example not found")
    cl_links: dict[int, tuple[int, list[str]]] = {}; gc_links: dict[int, tuple[int, list[str]]] = {}
    alignment = row.alignments[-1] if row.alignments else None
    if alignment:
        for link in alignment.links:
            if link.review_status not in {"confirmed", "edited"}: continue
            cl_ids = range(link.cl_record_start, (link.cl_record_end if link.cl_record_end is not None else link.cl_record_start)+1) if link.cl_record_start is not None else []
            gc_ids = range(link.gcode_block_start, (link.gcode_block_end if link.gcode_block_end is not None else link.gcode_block_start)+1) if link.gcode_block_start is not None else []
            for index in cl_ids: cl_links[index] = (link.id, [f"gcode-{value}" for value in gc_ids])
            for index in gc_ids: gc_links[index] = (link.id, [f"cl-{value}" for value in cl_ids])
    machine_type = str(row.machine_context_snapshot_json.get("machine_type") or "other")
    return build_toolpath(cl_records=row.parsed_cl_records_json, gcode_blocks=row.parsed_gcode_blocks_json, machine_type=machine_type, source=source, alignment_by_cl=cl_links, alignment_by_gc=gc_links)


@router.get("/gpost-preview-runs/{preview_id}/toolpath", response_model=ToolpathResponse)
def gpost_preview_toolpath(preview_id: int, source: str = Depends(source_param), db: Session = Depends(get_db)):
    preview = db.scalar(select(GPostPreviewRun).options(selectinload(GPostPreviewRun.draft)).where(GPostPreviewRun.id == preview_id))
    if not preview: raise HTTPException(404, "G-POST preview not found")
    trace = sorted(preview.traceability_json, key=lambda item: int(item.get("source_cl_line") or 0))
    cl_source = "\n".join(dict.fromkeys(str(item.get("source_cl_text") or "") for item in trace if item.get("source_cl_text")))
    cl = CLParser().parse(cl_source).records; gc = GCodeParser().parse(preview.generated_gcode).blocks
    cl_links={}; gc_links={}
    for gc_index,item in enumerate(trace):
        cl_index=max(0,int(item.get("source_cl_line") or 1)-1); link_id=int(item.get("mapping_id") or 0) or None
        cl_links[cl_index]=(link_id,[f"gcode-{gc_index}"]); gc_links[gc_index]=(link_id,[f"cl-{cl_index}"])
    return build_toolpath(cl_records=cl,gcode_blocks=gc,machine_type=preview.draft.machine_type,source=source,alignment_by_cl=cl_links,alignment_by_gc=gc_links)

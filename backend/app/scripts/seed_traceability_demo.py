from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from app.api.analysis_projects import run_analysis
from app.api.traceability import export_report, parse_cl, parse_gcode, start_alignment
from app.core.config import BACKEND_ROOT, PROJECT_ROOT
from app.db.alembic import upgrade_database
from app.db.session import SessionLocal
from app.models.entities import AnalysisProject, MachineProfile
from app.models.traceability import AlignmentLink, CLRecord, GCodeBlock


def main() -> None:
    upgrade_database()
    with SessionLocal() as db:
        machine = db.scalar(select(MachineProfile).where(
            MachineProfile.name == "Fictional VMC-850 Manual Demo"
        ))
        if machine is None:
            raise RuntimeError("Run seed_manual_demo before seed_traceability_demo")
        project = db.scalar(select(AnalysisProject).where(
            AnalysisProject.name == "Fictional Pocket Traceability Demo"
        ))
        if project is None:
            project = AnalysisProject(
                name="Fictional Pocket Traceability Demo",
                machine_profile_id=machine.id,
            )
            db.add(project); db.commit(); db.refresh(project)
        sample_dir = PROJECT_ROOT / "sample-data" / "traceability"
        project.cl_source = (sample_dir / "fictional-pocket-operation.cl").read_text()
        project.gcode_source = (sample_dir / "fictional-pocket-operation.nc").read_text()
        project.cl_original_filename = "fictional-pocket-operation.cl"
        project.gcode_original_filename = "fictional-pocket-operation.nc"
        project.cl_file_hash = sha256(project.cl_source.encode()).hexdigest()
        project.gcode_file_hash = sha256(project.gcode_source.encode()).hexdigest()
        project.cl_processing_status = project.gcode_processing_status = "pending"
        db.commit()
        cl_summary = parse_cl(project.id, db)
        gcode_summary = parse_gcode(project.id, db)
        validation = run_analysis(project.id, db)
        run = start_alignment(project.id, db)
        links = list(db.scalars(select(AlignmentLink).where(
            AlignmentLink.alignment_run_id == run.id
        ).order_by(AlignmentLink.confidence.desc())))
        low_links = [link for link in links if .45 <= link.confidence < .70]
        added_low = False
        if not low_links:
            cl_record = db.scalar(select(CLRecord).where(
                CLRecord.analysis_project_id == project.id
            ).order_by(CLRecord.record_index))
            gcode_block = db.scalar(select(GCodeBlock).where(
                GCodeBlock.analysis_project_id == project.id
            ).order_by(GCodeBlock.block_index.desc()))
            deliberate = AlignmentLink(
                alignment_run_id=run.id, cl_record_id=cl_record.id,
                gcode_block_id=gcode_block.id, link_type="weak", confidence=.46,
                match_reasons_json=["Deliberate fictional low-confidence demo proposal"],
                mismatch_reasons_json=["Event types and source positions are inconsistent"],
                score_components_json={"demo_fixture": .46}, status="proposed",
            )
            db.add(deliberate); db.commit(); db.refresh(deliberate)
            links.append(deliberate)
            added_low = True
        if links:
            links[0].status = "confirmed"; links[0].assigned_by = "local_user"
            rejected = min(links, key=lambda value: value.confidence)
            rejected.status = "rejected"; rejected.assigned_by = "local_user"
            rejected.review_note = "Deliberately reviewed low-confidence demo proposal."
            summary = dict(run.summary_json)
            if added_low:
                summary["proposed_link_count"] += 1
                summary["low_confidence_link_count"] += 1
            summary["confirmed_link_count"] = 1
            summary["rejected_link_count"] = 1
            run.summary_json = summary
            project.alignment_summary_json = summary
            db.commit()
        response = export_report(run.id, "markdown", db)
        report_path = BACKEND_ROOT / "data" / "traceability-demo-report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_bytes(response.body)
        print(f"project_id={project.id} alignment_run_id={run.id} version={run.version}")
        print(f"cl_records={cl_summary.record_count} gcode_blocks={gcode_summary.record_count}")
        print(f"validation_findings={len(validation.findings)} summary={run.summary_json}")
        print(f"confirmed_link_id={links[0].id if links else None}")
        print(f"rejected_link_id={rejected.id if links else None} confidence={rejected.confidence if links else None}")
        print(f"report={report_path}")


if __name__ == "__main__":
    main()

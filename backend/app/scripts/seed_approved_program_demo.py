"""Seed the deterministic Phase 6 approved-program demonstration."""
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from app.api.analysis_projects import (
    create_analysis_project, run_analysis,
)
from app.api.profile_extraction import ensure_initial_revision
from app.api.program_standards import (
    apply_standard_draft, approve_standard, comparison_report,
    create_comparison,
)
from app.core.config import PROJECT_ROOT
from app.db.alembic import upgrade_database
from app.db.session import SessionLocal
from app.models.entities import MachineProfile, MachineType
from app.models.program_standards import (
    ReferenceProgram, StandardConvention, StandardExtractionRun,
)
from app.program_standards.service import (
    ALGORITHM_VERSION, extract_conventions, parse_reference_program,
)
from app.schemas.analysis import AnalysisProjectCreate
from app.schemas.program_standards import (
    ComparisonCreate, StandardDecisionRequest, StandardDraftRequest,
)
from app.models.entities import utc_now

CORPUS = (
    PROJECT_ROOT / "sample-data" / "approved-programs" / "fictional-kls-1840n"
)
REPORT_PATH = PROJECT_ROOT / "backend" / "data" / "approved-program-demo-report.md"


def main() -> None:
    upgrade_database()
    with SessionLocal() as db:
        machine = db.scalar(select(MachineProfile).where(
            MachineProfile.name == "Fictional KLS-1840N Approved Program Demo"
        ))
        if not machine:
            machine = MachineProfile(
                name="Fictional KLS-1840N Approved Program Demo",
                manufacturer="Kent USA (fictional demo context)",
                model="KLS-1840N",
                controller_name="FANUC 0i-TF fictional configuration",
                controller_manufacturer="FANUC",
                controller_model="0i-TF",
                controller_version="DEMO-ONLY",
                machine_type=MachineType.LATHE,
                axis_count=2,
                x_min=-11, x_max=11, z_min=-38, z_max=38,
                max_spindle_rpm=2000, max_feed_rate=394,
                supported_work_offsets=["G54", "G55"],
                approved_g_codes=[
                    "G00", "G01", "G18", "G20", "G28", "G40", "G50",
                    "G54", "G76", "G80", "G90", "G96", "G97",
                ],
                approved_m_codes=["M02", "M03", "M05", "M09", "M30"],
                restricted_commands=[],
                safe_start_template="G20 G18 G40 G80 G90",
                program_end_template="M09 M05 G28 U0 W0 M30",
                notes="FICTIONAL SAMPLE — NOT FOR MACHINE USE",
            )
            db.add(machine); db.flush()
        revision = ensure_initial_revision(machine, db)
        revision.status = "approved"
        revision.approved_at = revision.approved_at or utc_now()
        machine.active_revision_id = revision.id
        db.commit()

        references = []
        for path in sorted(CORPUS.glob("*.nc")):
            source = path.read_text()
            digest = sha256(source.encode()).hexdigest()
            program = db.scalar(select(ReferenceProgram).where(
                ReferenceProgram.machine_profile_id == machine.id,
                ReferenceProgram.original_filename == path.name,
            ))
            if not program:
                is_deprecated = path.name == "deprecated.nc"
                program = ReferenceProgram(
                    machine_profile_id=machine.id,
                    machine_profile_revision_id=revision.id,
                    name=path.stem.replace("-", " ").title(),
                    original_filename=path.name,
                    file_hash=digest,
                    source_text=source,
                    program_type="turning",
                    controller_name="FANUC",
                    controller_version="DEMO-ONLY",
                    post_processor_name="Creo fictional post",
                    post_processor_revision=(
                        "POST-B" if path.name == "different-post.nc" else "POST-A"
                    ),
                    part_identifier=path.stem.upper(),
                    units="inch",
                    machine_variant="KLS-1840N",
                    approval_status=(
                        "deprecated" if is_deprecated else "approved_reference"
                    ),
                    eligibility_status="pending",
                    ai_processing_allowed=False,
                    source_integrity_json={
                        "sha256": digest, "fictional_sample": True,
                        "not_for_machine_use": True,
                    },
                )
                db.add(program); db.flush()
            else:
                program.source_text = source
                program.file_hash = digest
                program.source_integrity_json = {
                    "sha256": digest, "fictional_sample": True,
                    "not_for_machine_use": True,
                }
            parse_reference_program(program, db)
            if path.name.startswith("eligible-") or path.name == "different-post.nc":
                program.eligibility_status = "eligible"
                program.eligibility_reason = (
                    "Explicit fictional demo eligibility; never for machine use."
                )
            else:
                program.eligibility_status = "ineligible"
                program.eligibility_reason = (
                    "Excluded demo exception, deprecated source, or comparison input."
                )
            references.append(program)
        db.commit()

        eligible = [
            item for item in references
            if item.original_filename.startswith("eligible-")
        ]
        run = StandardExtractionRun(
            machine_profile_id=machine.id,
            machine_profile_revision_id=revision.id,
            selected_reference_program_ids_json=[item.id for item in eligible],
            algorithm_version=ALGORITHM_VERSION,
            settings_json={
                "post_processor_revision": "POST-A",
                "deterministic_only": True,
                "external_ai_used": False,
            },
        )
        db.add(run); db.flush()
        conventions = extract_conventions(run, eligible, db)
        run.completed_at = utc_now()
        for convention in conventions:
            convention.review_status = (
                "rejected" if convention.convention_key == "sequence_numbers"
                else "accepted"
            )
            convention.review_note = (
                "Explicitly accepted after fictional evidence review."
                if convention.review_status == "accepted"
                else "Rejected one weak formatting convention."
            )
            convention.reviewed_at = utc_now()
        db.commit()

        standard = apply_standard_draft(
            run.id,
            StandardDraftRequest(name="Fictional KLS-1840N Programming Standard"),
            db,
        )
        standard = approve_standard(
            standard.id,
            StandardDecisionRequest(
                note="Explicit fictional demo approval; not for machine use."
            ),
            db,
        )
        current = (CORPUS / "current-comparison.nc").read_text()
        analysis = create_analysis_project(
            AnalysisProjectCreate(
                name="Fictional KLS-1840N approved-program comparison",
                machine_profile_id=machine.id,
                gcode_source=current,
            ),
            db,
        )
        run_analysis(analysis.id, db)
        comparison = create_comparison(
            analysis.id,
            ComparisonCreate(
                standard_profile_id=standard.id,
                reference_program_id=eligible[0].id,
            ),
            db,
        )
        report = comparison_report(comparison.id, "markdown", db)
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_bytes(report.body)

        refreshed = db.get(StandardExtractionRun, run.id)
        proposals = db.scalars(select(StandardConvention).where(
            StandardConvention.extraction_run_id == run.id
        )).all()
        print("Phase 6 fictional approved-program demo complete")
        print(f"machine_id={machine.id} revision_id={revision.id}")
        print(f"reference_programs={len(references)} eligible_post_a={len(eligible)}")
        print(f"different_post_identified={any(item.post_processor_revision == 'POST-B' for item in references)}")
        print(f"standard_extraction_run_id={refreshed.id} proposals={len(proposals)}")
        print(f"standard_id={standard.id} status={standard.status}")
        print(f"analysis_id={analysis.id} comparison_id={comparison.id}")
        print(f"comparison_summary={comparison.summary_json}")
        print(f"report={REPORT_PATH}")
        print("historical_similarity_is_not_certification=true")


if __name__ == "__main__":
    main()

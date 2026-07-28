from sqlalchemy import select

from app.api.profile_extraction import (
    apply_to_draft, ensure_initial_revision, review_proposal, start_extraction,
)
from app.core.config import PROJECT_ROOT, get_settings
from app.db.alembic import upgrade_database
from app.db.session import SessionLocal
from app.documents.processing import process_document
from app.documents.storage import store_upload
from app.models.entities import DocumentType, MachineProfile, MachineType, SourceDocument
from app.models.profile_extraction import ProfileFieldProposal
from app.schemas.profile_extraction import ApplyDraftRequest, ExtractionStart, ProposalReview


SAMPLES = (
    ("fictional-lathe-operator-manual.md", "Fictional LT-200 Operator Manual", DocumentType.OPERATOR_MANUAL),
    ("fictional-lathe-programming-manual.md", "Fictional Orion 30T Programming Manual", DocumentType.PROGRAMMING_MANUAL),
    ("fictional-lathe-specification-sheet.md", "Fictional LT-200 Specification Sheet", DocumentType.SPECIFICATION_DOCUMENT),
    ("fictional-lathe-conflicting-specification.md", "Fictional LT-200 Conflicting Specification", DocumentType.SPECIFICATION_DOCUMENT),
)


def main() -> None:
    upgrade_database()
    settings = get_settings()
    with SessionLocal() as db:
        machine = db.scalar(select(MachineProfile).where(
            MachineProfile.name == "Fictional LT-200 Profile Extraction Demo"
        ))
        if machine is None:
            machine = MachineProfile(
                name="Fictional LT-200 Profile Extraction Demo",
                manufacturer="Northstar Machine Works", model="LT-200",
                controller_name="Orion 30T", controller_version="4.7",
                machine_type=MachineType.LATHE, axis_count=2,
                x_min=None, x_max=None, y_min=None, y_max=None,
                z_min=None, z_max=None, max_spindle_rpm=3500,
                max_feed_rate=None, rapid_z_review_threshold=0,
                supported_work_offsets=["G54"], approved_g_codes=[],
                approved_m_codes=[], restricted_commands=[],
                safe_start_template=None, tool_change_template=None,
                program_end_template=None,
                notes="FICTIONAL SAMPLE — NOT FOR MACHINE USE",
            )
            db.add(machine); db.commit(); db.refresh(machine)
        initial = ensure_initial_revision(machine, db)
        db.commit()

        document_ids: list[int] = []
        sample_dir = PROJECT_ROOT / "sample-data" / "profile-extraction"
        for filename, title, document_type in SAMPLES:
            content = (sample_dir / filename).read_bytes()
            stored = store_upload(filename, content, settings)
            document = db.scalar(select(SourceDocument).where(
                SourceDocument.machine_profile_id == machine.id,
                SourceDocument.file_hash == stored.file_hash,
            ))
            if document is None:
                document = SourceDocument(
                    machine_profile_id=machine.id, title=title,
                    document_type=document_type, manufacturer=machine.manufacturer,
                    controller_name=machine.controller_name,
                    original_filename=stored.original_filename,
                    stored_filename=stored.stored_filename,
                    stored_path=str(stored.stored_path), mime_type=stored.mime_type,
                    file_size_bytes=stored.size, file_hash=stored.file_hash,
                )
                db.add(document); db.commit(); db.refresh(document)
                process_document(document, db, settings)
            else:
                stored.stored_path.unlink(missing_ok=True)
            document_ids.append(document.id)

        run = start_extraction(machine.id, ExtractionStart(
            document_ids=document_ids, target_machine_type="lathe",
            selected_machine_variant="LT-200",
            field_categories=[
                "identity", "controller", "axis_limits", "spindle",
                "feed_and_motion", "tooling", "workholding",
                "programming", "capabilities", "safety_and_setup",
            ],
        ), db)
        proposals = {
            item.field_key: item for item in db.scalars(select(ProfileFieldProposal).where(
                ProfileFieldProposal.extraction_run_id == run.id
            ))
        }

        if proposals["manufacturer"].proposal_status == "found":
            review_proposal(proposals["manufacturer"].id, ProposalReview(
                review_status="accepted",
            ), db)
        review_proposal(proposals["z_travel"].id, ProposalReview(
            review_status="accepted_with_edit", reviewed_value=22,
            unit="inch", review_note="Confirmed fictional value for demo review.",
        ), db)
        review_proposal(proposals["controller_version"].id, ProposalReview(
            review_status="rejected",
            review_note="Deliberate demo rejection; exact installed software is unconfirmed.",
        ), db)
        review_proposal(proposals["max_spindle_rpm"].id, ProposalReview(
            review_status="manually_entered", reviewed_value=4000,
            unit="rpm",
            review_note="Resolved the deliberate 4,000/4,500 RPM conflict to the base fictional configuration.",
        ), db)

        result = apply_to_draft(run.id, ApplyDraftRequest(
            base_strategy="active",
            review_summary="Partially reviewed fictional extraction demo; deliberately left unapproved.",
        ), db)
        revision = result["revision"]
        print(f"machine_id={machine.id} active_revision_id={initial.id}")
        print(f"run_id={run.id} status={run.status} variants={run.detected_variants_json}")
        print(
            f"found={run.summary_json.get('found_count')} "
            f"ambiguous={run.summary_json.get('ambiguous_count')} "
            f"conflicts={run.summary_json.get('conflict_count')} "
            f"not_found={run.summary_json.get('not_found_count')}"
        )
        print(
            f"draft_revision_id={revision.id} revision=v{revision.revision_number} "
            f"status={revision.status} active_unchanged={machine.active_revision_id == initial.id}"
        )
        print(f"applied_fields={result['applied_field_keys']}")


if __name__ == "__main__":
    main()

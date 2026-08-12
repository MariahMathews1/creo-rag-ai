"""Seed five synthetic Phase 8 CL/G-code pairs without external services."""
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.api.analysis_projects import revision_snapshot
from app.api.profile_extraction import ensure_initial_revision
from app.core.config import PROJECT_ROOT
from app.db.alembic import upgrade_database
from app.db.session import SessionLocal
from app.models.entities import AuditEvent, MachineProfile, MachineType, utc_now
from app.models.translation import TranslationExample
from app.translation.service import generate_alignment, normalize_text, parse_and_validate, source_hash

CORPUS = PROJECT_ROOT / "sample-data" / "translations" / "fictional-kls"


def main() -> None:
    upgrade_database()
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    with SessionLocal() as db:
        machine = db.scalar(select(MachineProfile).where(MachineProfile.name == "Fictional KLS Phase 8 Translation Demo"))
        if not machine:
            machine = MachineProfile(
                name="Fictional KLS Phase 8 Translation Demo", manufacturer="Fictional Training Systems",
                model="KLS-DEMO", controller_name="FANUC fictional context",
                controller_manufacturer="FANUC", controller_model="DEMO-ONLY",
                controller_version="SIMULATED", machine_type=MachineType.LATHE, axis_count=2,
                x_min=-20, x_max=20, z_min=-40, z_max=10, max_spindle_rpm=2000,
                max_feed_rate=100, supported_work_offsets=["G54", "G55"],
                approved_g_codes=["G00", "G01", "G18", "G20", "G40", "G80", "G90", "G94", "G97"],
                approved_m_codes=["M02", "M03", "M05", "M08", "M09", "M30"],
                restricted_commands=[], safe_start_template="G20 G18 G40 G80 G90 G94",
                tool_change_template="T{tool:02d}{tool:02d}", program_end_template="M09 M05 M30",
                notes="FICTIONAL SAMPLE — NOT FOR MACHINE USE",
            )
            db.add(machine); db.flush()
        # Reassert synthetic identity on reruns so a previously seeded demo can
        # never inherit stale controller labels from local experimentation.
        machine.manufacturer = "Fictional Training Systems"; machine.model = "KLS-DEMO"
        machine.controller_name = "FANUC fictional context"; machine.controller_manufacturer = "FANUC"
        machine.controller_model = "DEMO-ONLY"; machine.controller_version = "SIMULATED"
        revision = ensure_initial_revision(machine, db); revision.status = "approved"
        revision.name = machine.name; revision.manufacturer = machine.manufacturer; revision.model = machine.model
        revision.controller_name = machine.controller_name; revision.controller_manufacturer = machine.controller_manufacturer
        revision.controller_model = machine.controller_model; revision.controller_version = machine.controller_version
        revision.approved_at = revision.approved_at or utc_now(); machine.active_revision_id = revision.id; db.flush()

        seeded: list[TranslationExample] = []
        confirmed_links = 0
        for item in manifest:
            cl_path, gc_path = CORPUS / f"{item['slug']}.cl", CORPUS / f"{item['slug']}.nc"
            cl_text, gc_text = normalize_text(cl_path.read_text()), normalize_text(gc_path.read_text())
            row = db.scalar(select(TranslationExample).where(
                TranslationExample.machine_profile_revision_id == revision.id,
                TranslationExample.cl_source_hash == source_hash(cl_text),
                TranslationExample.gcode_source_hash == source_hash(gc_text),
            ))
            if not row:
                row = TranslationExample(
                    machine_profile_id=machine.id, machine_profile_revision_id=revision.id,
                    name=item["name"], description="Synthetic paired fixture for the governed Phase 8 demo.",
                    controller_name=revision.controller_name, controller_version=revision.controller_version,
                    post_processor_name="Fictional Site Lathe Post", post_processor_revision=item["post_revision"],
                    operation_type=item["operation_type"], operation_name=item["name"],
                    cl_source_text=cl_text, cl_source_hash=source_hash(cl_text), cl_original_filename=cl_path.name,
                    gcode_source_text=gc_text, gcode_source_hash=source_hash(gc_text), gcode_original_filename=gc_path.name,
                    verification_status="candidate", part_identifier=f"FICTIONAL-{item['slug'].upper()}",
                    project_identifier="PHASE8-DEMO", tooling_context_json={"fictional": True},
                    setup_context_json={"not_for_machine_use": True},
                    machine_context_snapshot_json=revision_snapshot(revision, machine),
                    source_system="Synthetic repository fixture", source_repository=str(CORPUS),
                    imported_by_label="seed_translation_demo", source_provenance="Authored fictional sample; no proprietary source.",
                    verification_basis="Demo-only controlled review; never a production qualification.",
                    ai_processing_allowed=False,
                )
                db.add(row); db.flush()
                db.add(AuditEvent(event_type="translation_example_created", machine_profile_id=machine.id, metadata_json={"translation_example_id": row.id, "seeded": True}))
            row.controller_name = revision.controller_name; row.controller_version = revision.controller_version
            row.machine_context_snapshot_json = revision_snapshot(revision, machine)
            parse_and_validate(row, machine, revision)
            alignment = generate_alignment(db, row)
            for link in alignment.links:
                link.review_status = "confirmed" if link.cl_record_start is not None and link.gcode_block_start is not None else "rejected"
                link.reviewed_by_label = "Fictional demo reviewer"
                confirmed_links += link.review_status == "confirmed"
            row.reviewed_at = row.reviewed_at or utc_now()
            row.verification_note = "Fictional demo review completed; this is not production authorization."
            if item["status"] == "candidate":
                row.verification_status = "candidate"
            else:
                row.verification_status = "verified_successful" if item["status"] == "verified_successful" else "deprecated"
                row.verified_at = row.verified_at or utc_now()
                if item["status"] == "deprecated": row.deprecated_at = row.deprecated_at or utc_now()
            seeded.append(row)
        db.commit()
        counts = Counter(row.verification_status for row in seeded)
        print("Phase 8 fictional translation dataset seeded")
        print(f"machine_id={machine.id} revision_id={revision.id} revision_status={revision.status}")
        print(f"pairs={len(seeded)} candidate={counts['candidate']} verified_successful={counts['verified_successful']} deprecated={counts['deprecated']}")
        print(f"alignments={len(seeded)} confirmed_links={confirmed_links}")
        print("cl_parsed=true gcode_parsed=true deterministic_validation=true")
        print("external_ai_used=false ai_processing_allowed=false")
        print("FICTIONAL SAMPLE — NOT FOR MACHINE USE")


if __name__ == "__main__":
    main()

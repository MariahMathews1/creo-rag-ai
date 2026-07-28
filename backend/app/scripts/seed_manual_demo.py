from pathlib import Path

from sqlalchemy import select

from app.api.manual_assistant import answer_question
from app.core.config import PROJECT_ROOT, get_settings
from app.db.alembic import upgrade_database
from app.db.session import SessionLocal
from app.documents.processing import process_document
from app.documents.storage import store_upload
from app.models.entities import (
    DocumentType, MachineProfile, MachineType, ManualQuestionSession, SourceDocument,
)
from app.schemas.documents import QuestionCreate


def main() -> None:
    upgrade_database()
    settings = get_settings()
    with SessionLocal() as db:
        machine = db.scalar(
            select(MachineProfile).where(
                MachineProfile.name == "Fictional VMC-850 Manual Demo"
            )
        )
        if not machine:
            machine = MachineProfile(
                name="Fictional VMC-850 Manual Demo",
                manufacturer="Example Machine Works", model="VMC-850-PoC",
                controller_name="Example Control EC-3X", controller_version="POC-1",
                machine_type=MachineType.MILL, axis_count=3,
                x_min=-20, x_max=20, y_min=-12, y_max=12, z_min=-5, z_max=18,
                max_spindle_rpm=10000, max_feed_rate=500,
                rapid_z_review_threshold=0, supported_work_offsets=["G54"],
                approved_g_codes=[], approved_m_codes=[], restricted_commands=[],
                safe_start_template="G17 G20 G40 G49 G80 G90 G94",
                program_end_template="M05 M09 G40 G49 M30",
                notes="FICTIONAL SAMPLE — NOT FOR MACHINE USE",
            )
            db.add(machine); db.commit(); db.refresh(machine)

        manuals = [
            ("fictional-3-axis-mill-controller-manual.md",
             "Fictional EC-3X Controller Manual", DocumentType.CONTROLLER_MANUAL),
            ("fictional-company-programming-standard.md",
             "Fictional Company Programming Standard", DocumentType.COMPANY_STANDARD),
            ("fictional-post-processor-notes.md",
             "Fictional Post-Processor Notes", DocumentType.POST_PROCESSOR_DOCUMENT),
        ]
        for filename, title, document_type in manuals:
            source = PROJECT_ROOT / "sample-data" / "manuals" / filename
            content = source.read_bytes()
            stored = store_upload(filename, content, settings)
            existing = db.scalar(select(SourceDocument).where(
                SourceDocument.machine_profile_id == machine.id,
                SourceDocument.file_hash == stored.file_hash,
            ))
            if existing:
                stored.stored_path.unlink(missing_ok=True)
                continue
            document = SourceDocument(
                machine_profile_id=machine.id, title=title,
                document_type=document_type, manufacturer=machine.manufacturer,
                controller_name=machine.controller_name,
                controller_version=machine.controller_version,
                original_filename=stored.original_filename,
                stored_filename=stored.stored_filename,
                stored_path=str(stored.stored_path), mime_type=stored.mime_type,
                file_size_bytes=stored.size, file_hash=stored.file_hash,
            )
            db.add(document); db.commit(); db.refresh(document)
            process_document(document, db, settings)

        session = ManualQuestionSession(
            machine_profile_id=machine.id, title="Phase 3 manual demo"
        )
        db.add(session); db.commit(); db.refresh(session)
        supported = answer_question(
            session,
            QuestionCreate(question="Does this controller support rigid tapping?"),
            db,
        )
        unsupported = answer_question(
            session,
            QuestionCreate(question="What laser probing cycle is installed?"),
            db,
        )
        print(f"machine_id={machine.id} session_id={session.id}")
        print(
            f"supported_status={supported.answer_status.value} "
            f"citations={[item.document_id for item in supported.citations]}"
        )
        print(f"unsupported_status={unsupported.answer_status.value}")


if __name__ == "__main__":
    main()


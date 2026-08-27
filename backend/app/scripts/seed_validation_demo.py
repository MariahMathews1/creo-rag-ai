"""Seed fictional pre-Azure validation metadata; never stores production artifacts."""
from sqlalchemy import select

from app.db.alembic import upgrade_database
from app.db.session import SessionLocal
from app.models.gpost import GPostDraft, PostValidationRecord, ValidationFinding, ValidationPolicy


def main() -> None:
    upgrade_database()
    with SessionLocal() as db:
        draft = db.scalar(select(GPostDraft).order_by(GPostDraft.id))
        if draft is None:
            print("Create a fictional Post Record before seeding validation data.")
            return
        policy = db.scalar(select(ValidationPolicy).where(ValidationPolicy.post_record_id == draft.id))
        if policy is None:
            db.add(ValidationPolicy(post_record_id=draft.id, name="Fictional R&D Validation Policy",
                required_validation_types_json=["Configuration Review", "G-POST Compilation", "VERICUT Simulation", "NC Programmer Review"],
                optional_validation_types_json=["Controlled Test Post", "Dry Run"], source="FICTIONAL R&D DATA", reviewer="Fictional Engineer"))
        existing = {row.validation_type for row in db.scalars(select(PostValidationRecord).where(PostValidationRecord.post_record_id == draft.id))}
        for kind, result, tool in (("G-POST Compilation", "PASS", "G-POST"),
                                   ("Controlled Test Post", "PASS_WITH_FINDINGS", "G-POST"),
                                   ("VERICUT Simulation", "PASS", "VERICUT"),
                                   ("NC Programmer Review", "NEEDS_REVIEW", None)):
            if kind in existing: continue
            row = PostValidationRecord(post_record_id=draft.id, validation_type=kind, name=f"Fictional {kind}",
                performed_by="Fictional NC Programmer", environment="FICTIONAL LOCAL R&D", result=result,
                notes="FICTIONAL R&D DATA — NOT FOR MACHINE USE", external_tool=tool,
                external_reference="fictional-report-reference" if tool == "VERICUT" else None,
                test_program_name="Synthetic 2-Axis Turning Qualification A", ai_used=False)
            db.add(row); db.flush()
            if result == "PASS_WITH_FINDINGS":
                db.add(ValidationFinding(validation_record_id=row.id, severity="WARNING", category="Synthetic Diagnostic",
                    title="Fictional formatting warning", description="Synthetic fixture only.", status="Open"))
                row.findings_count = 1
        db.commit()
        print(f"Fictional validation data seeded for post_record_id={draft.id}")
        print("FICTIONAL R&D DATA — NOT FOR MACHINE USE — external_ai_used=false")


if __name__ == "__main__":
    main()

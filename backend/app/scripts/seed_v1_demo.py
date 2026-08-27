"""Seed the fictional KLS-1840N V1 clarity-pass walkthrough."""
from sqlalchemy import select

from app.api.post_records import ensure_defaults
from app.db.alembic import upgrade_database
from app.db.session import SessionLocal
from app.gpost.service import capability_snapshot, default_templates, initial_mappings, revision_snapshot
from app.models.entities import DocumentType, MachineProfile, MachineType, ProcessingStatus, SourceDocument, utc_now
from app.models.gpost import (
    CustomLogicItem,
    GPostDraft,
    MachineKnowledgeFact,
    OFGSetting,
    OpenQuestion,
    PostStandardApplication,
    SiteStandard,
)
from app.models.profile_extraction import MachineProfileRevision


MACHINE_NAME = "KLS-1840N Demo"
MACHINE_ALIASES = (MACHINE_NAME, "KLS-1840N V1 Demo")
DRAFT_NAME = "KLS-1840N FANUC Demo Post"
DRAFT_ALIASES = (DRAFT_NAME, "KLS-1840N Demo Post")
DOCUMENT_TITLE = "KLS Machine Manual — Fictional Demo"
DOCUMENT_ALIASES = (DOCUMENT_TITLE, "KLS-1840N Fictional Machine Manual")
STANDARD_NAME = "Tool Change Safe Retract"
LOGIC_NAME = "G74 Grooving Behavior"
LOGIC_ALIASES = (LOGIC_NAME, "G74 Cycle Behavior")


def demo_revision(machine: MachineProfile, db) -> MachineProfileRevision:
    revision = db.scalar(
        select(MachineProfileRevision).where(
            MachineProfileRevision.machine_profile_id == machine.id,
            MachineProfileRevision.name.in_(MACHINE_ALIASES),
        )
    )
    if revision is not None:
        revision.name = MACHINE_NAME
        return revision
    revision_numbers = list(
        db.scalars(
            select(MachineProfileRevision.revision_number).where(
                MachineProfileRevision.machine_profile_id == machine.id
            )
        )
    )
    revision = MachineProfileRevision(
        machine_profile_id=machine.id,
        revision_number=max(revision_numbers, default=0) + 1,
        status="approved",
        source_type="demo_seed",
        name=MACHINE_NAME,
        manufacturer=machine.manufacturer,
        model=machine.model,
        controller_name=machine.controller_name,
        controller_manufacturer=machine.controller_manufacturer,
        controller_model=machine.controller_model,
        controller_version=machine.controller_version,
        machine_type=machine.machine_type.value,
        axis_count=machine.axis_count,
        x_min=machine.x_min,
        x_max=machine.x_max,
        y_min=machine.y_min,
        y_max=machine.y_max,
        z_min=machine.z_min,
        z_max=machine.z_max,
        max_spindle_rpm=machine.max_spindle_rpm,
        max_feed_rate=machine.max_feed_rate,
        supported_work_offsets_json=machine.supported_work_offsets,
        approved_g_codes_json=machine.approved_g_codes,
        approved_m_codes_json=machine.approved_m_codes,
        restricted_commands_json=machine.restricted_commands,
        safe_start_template=machine.safe_start_template,
        tool_change_template=machine.tool_change_template,
        program_end_template=machine.program_end_template,
        notes="FICTIONAL SAMPLE — NOT FOR MACHINE USE",
        review_summary="Immutable fictional V1 walkthrough revision.",
        approved_at=utc_now(),
    )
    db.add(revision)
    db.flush()
    return revision


def main() -> None:
    upgrade_database()
    with SessionLocal() as db:
        machine = db.scalar(select(MachineProfile).where(MachineProfile.name.in_(MACHINE_ALIASES)))
        if machine is None:
            machine = MachineProfile(
                name=MACHINE_NAME,
                manufacturer="KENT USA (fictional demo context)",
                model="KLS-1840N",
                controller_name="FANUC-style fictional demo controller",
                controller_manufacturer="FANUC",
                controller_model="Fictional 0i-T context",
                controller_version="DEMO ONLY",
                machine_type=MachineType.LATHE,
                axis_count=2,
                x_min=-9,
                x_max=9,
                z_min=-40,
                z_max=0,
                max_spindle_rpm=2000,
                max_feed_rate=100,
                supported_work_offsets=["G54", "G55"],
                approved_g_codes=["G00", "G01", "G18", "G40", "G54", "G74", "G80", "G90", "G94"],
                approved_m_codes=["M03", "M04", "M05", "M08", "M09", "M30"],
                restricted_commands=[],
                safe_start_template="G18 G40 G80 G90 G94",
                tool_change_template="G00 X{safe_x} Z{safe_z}\nT{tool}",
                program_end_template="M05\nM09\nM30",
                notes="FICTIONAL SAMPLE — NOT FOR MACHINE USE",
            )
            db.add(machine)
            db.flush()

        # Reapply the canonical walkthrough context on every run so reset/seed is deterministic.
        machine.name = MACHINE_NAME
        machine.manufacturer = "KENT USA — FICTIONAL DEMO"
        machine.model = "KLS-1840N"
        machine.controller_name = "FANUC-style fictional demo controller"
        machine.controller_manufacturer = "FANUC"
        machine.controller_model = "Fictional 0i-T context"
        machine.controller_version = "DEMO ONLY"
        machine.machine_type = MachineType.LATHE
        machine.axis_count = 2
        machine.x_min, machine.x_max = -9, 9
        machine.y_min, machine.y_max = None, None
        machine.z_min, machine.z_max = -40, 0
        machine.max_spindle_rpm = 2000
        machine.max_feed_rate = 100
        machine.supported_work_offsets = ["G54", "G55"]
        machine.approved_g_codes = ["G00", "G01", "G18", "G40", "G54", "G74", "G80", "G90", "G94"]
        machine.approved_m_codes = ["M03", "M04", "M05", "M08", "M09", "M30"]
        machine.restricted_commands = []
        machine.safe_start_template = "G18 G40 G80 G90 G94"
        machine.tool_change_template = "G00 X{safe_x} Z{safe_z}\nT{tool}"
        machine.program_end_template = "M05\nM09\nM30"
        machine.notes = "FICTIONAL SAMPLE — NOT FOR MACHINE USE"
        machine.archived_at = None

        revision = demo_revision(machine, db)
        revision.name = MACHINE_NAME
        revision.manufacturer = machine.manufacturer
        revision.model = machine.model
        revision.controller_name = machine.controller_name
        revision.controller_manufacturer = machine.controller_manufacturer
        revision.controller_model = machine.controller_model
        revision.controller_version = machine.controller_version
        revision.machine_type = machine.machine_type.value
        revision.axis_count = machine.axis_count
        revision.x_min, revision.x_max = machine.x_min, machine.x_max
        revision.y_min, revision.y_max = machine.y_min, machine.y_max
        revision.z_min, revision.z_max = machine.z_min, machine.z_max
        revision.max_spindle_rpm = machine.max_spindle_rpm
        revision.max_feed_rate = machine.max_feed_rate
        revision.supported_work_offsets_json = machine.supported_work_offsets
        revision.approved_g_codes_json = machine.approved_g_codes
        revision.approved_m_codes_json = machine.approved_m_codes
        revision.restricted_commands_json = machine.restricted_commands
        revision.capabilities_json = {
            **(revision.capabilities_json or {}),
            "tool_change": False,
            "operator_messages": False,
            "custom_fil": False,
        }
        revision.safe_start_template = machine.safe_start_template
        revision.tool_change_template = machine.tool_change_template
        revision.program_end_template = machine.program_end_template
        revision.status = "approved"
        revision.approved_at = revision.approved_at or utc_now()
        machine.active_revision_id = revision.id

        evidence_text = (
            "FICTIONAL DEMO MANUAL. Maximum spindle speed is 2,000 RPM (p. 42). "
            "A 100 IPM maximum feed-rate value is listed but awaits engineering confirmation (p. 50). "
            "M03 commands clockwise spindle rotation, M04 commands counter-clockwise rotation, "
            "and M05 stops the spindle (p. 56). The G74 cycle description is ambiguous and "
            "requires engineering review (p. 74). This text is not approved for machine use."
        )
        document = db.scalar(
            select(SourceDocument).where(
                SourceDocument.machine_profile_id == machine.id,
                SourceDocument.title.in_(DOCUMENT_ALIASES),
            )
        )
        if document is None:
            document = SourceDocument(
                machine_profile_id=machine.id,
                title=DOCUMENT_TITLE,
                document_type=DocumentType.MACHINE_MANUAL,
                manufacturer="Fictional demo source",
                controller_name=machine.controller_name,
                original_filename="kls-1840n-fictional-demo-manual.txt",
                mime_type="text/plain",
                extracted_text=evidence_text,
                page_count=84,
                processing_status=ProcessingStatus.READY,
                ai_post_builder_allowed=False,
            )
            db.add(document)
            db.flush()
        document.title = DOCUMENT_TITLE
        document.extracted_text = evidence_text
        document.processing_status = ProcessingStatus.READY

        draft = db.scalar(
            select(GPostDraft).where(
                GPostDraft.machine_profile_id == machine.id,
                GPostDraft.name.in_(DRAFT_ALIASES),
            )
        )
        if draft is None:
            draft = GPostDraft(
                machine_profile_id=machine.id,
                machine_profile_revision_id=revision.id,
                name=DRAFT_NAME,
                version=1,
                status="building",
                controller_family="fanuc_lathe",
                machine_type="lathe",
                selected_document_ids_json=[document.id],
                capability_snapshot_json=capability_snapshot(revision),
                machine_profile_snapshot_json=revision_snapshot(revision, machine),
                templates_json=default_templates(revision, "fanuc_lathe"),
                warnings_json=["FICTIONAL SAMPLE — NOT FOR MACHINE USE"],
                review_summary_json={},
            )
            db.add(draft)
            db.flush()
            db.add_all(initial_mappings(draft))
            db.commit()

        draft.name = DRAFT_NAME
        draft.status = "building"
        draft.machine_profile_revision_id = revision.id
        draft.selected_document_ids_json = [document.id]
        draft.capability_snapshot_json = capability_snapshot(revision)
        draft.machine_profile_snapshot_json = revision_snapshot(revision, machine)
        draft.templates_json = default_templates(revision, "fanuc_lathe")
        db.commit()

        ensure_defaults(db, draft)
        facts = {
            item.fact_key: item
            for item in db.scalars(
                select(MachineKnowledgeFact).where(MachineKnowledgeFact.post_record_id == draft.id)
            )
        }
        profile_fact_values = {
            "machine_type": "lathe",
            "controller": machine.controller_model,
            "axes": 2,
            "x_travel": [-9, 9],
            "z_travel": [-40, 0],
            "tool_change": draft.templates_json["tool_change"],
            "work_offsets": ["G54", "G55"],
            "safe_start": draft.templates_json["safe_start"],
            "program_end": draft.templates_json["program_end"],
        }
        for key, value in profile_fact_values.items():
            fact = facts[key]
            fact.value_json = value
            fact.status = "confirmed"
            fact.source_document_id = None
            fact.source_label = f"Machine configuration revision {revision.revision_number}"
            fact.source_location = "Reviewed machine profile"
            fact.reviewer = "Fictional Demo Engineer"
            fact.reviewed_at = utc_now()
        facts["y_travel"].value_json = None
        facts["y_travel"].status = "not_applicable"
        facts["y_travel"].source_document_id = None
        facts["y_travel"].source_label = f"Machine configuration revision {revision.revision_number}"
        facts["y_travel"].source_location = "Two-axis lathe configuration"
        facts["y_travel"].reviewer = "Fictional Demo Engineer"
        facts["y_travel"].reviewed_at = utc_now()
        fact_values = {
            "max_spindle_rpm": (2000, "RPM", "p. 42", "confirmed"),
            "max_feed_rate": (100, "IPM", "p. 50", "needs_review"),
            "spindle_cw": ("M03", None, "p. 56", "confirmed"),
            "spindle_ccw": ("M04", None, "p. 56", "confirmed"),
            "spindle_stop": ("M05", None, "p. 56", "confirmed"),
            "supported_cycles": (["G74"], None, "p. 74", "confirmed"),
        }
        for key, (value, unit, location, status) in fact_values.items():
            fact = facts[key]
            fact.value_json = value
            fact.unit = unit
            fact.status = status
            fact.source_document_id = document.id
            fact.source_label = DOCUMENT_TITLE
            fact.source_location = location
            fact.reviewer = "Fictional Demo Engineer" if status == "confirmed" else None
            fact.reviewed_at = utc_now() if status == "confirmed" else None
            fact.review_note = "Fictional walkthrough evidence; site verification required."

        settings = {
            item.setting_key: item
            for item in db.scalars(select(OFGSetting).where(OFGSetting.post_record_id == draft.id))
        }
        for setting in settings.values():
            if not setting.source_machine_fact_ids_json:
                continue
            source_fact = next(
                (item for item in facts.values() if item.id == setting.source_machine_fact_ids_json[0]),
                None,
            )
            if source_fact is not None:
                setting.value_json = source_fact.value_json
                setting.unit = source_fact.unit
                if source_fact.status == "confirmed" and setting.status == "needs_information":
                    setting.status = "mapped"
        for setting_key, fact_key in {
            "machine_type": "machine_type",
            "maximum_spindle_speed": "max_spindle_rpm",
            "program_start": "safe_start",
            "program_end": "program_end",
            "linear_motion": "linear_move",
            "rapid_motion": "rapid_move",
        }.items():
            setting = settings[setting_key]
            fact = facts[fact_key]
            setting.value_json = fact.value_json
            setting.unit = fact.unit
            setting.status = "reviewed"
            setting.source_machine_fact_ids_json = [fact.id]
            setting.source_document_evidence_ids_json = [document.id]
            setting.reviewer = "Fictional Demo Engineer"
            setting.reviewed_at = utc_now()
            setting.source_type = "Machine Knowledge"

        # The demo deliberately leaves site-dependent file formatting unresolved.
        for setting_key in ("mcd_extension", "decimal_format", "sequence_numbers", "mcd_address_format"):
            settings[setting_key].status = "needs_review"
            settings[setting_key].source_type = "OFG Reference"

        standard = db.scalar(select(SiteStandard).where(SiteStandard.name == STANDARD_NAME))
        if standard is None:
            standard = SiteStandard(
                name=STANDARD_NAME,
                description="Fictional site practice for safe turret indexing.",
                scope="specific_machine",
                applicable_machine_types_json=["lathe"],
                applicable_controller_families_json=["fanuc_lathe"],
                applicable_machine_ids_json=[machine.id],
                category="Tooling",
                rule="Retract to the reviewed safe X/Z position before turret indexing.",
                validation_requirements_json=["NC Programmer Review"],
                source="Fictional Site SOP",
                status="reviewed",
                reviewer="Fictional Demo Engineer",
                version=1,
                notes="FICTIONAL SAMPLE — NOT FOR MACHINE USE",
            )
            db.add(standard)
            db.flush()

        application = db.scalar(
            select(PostStandardApplication).where(
                PostStandardApplication.post_record_id == draft.id,
                PostStandardApplication.site_standard_id == standard.id,
            )
        )
        if application is None:
            application = PostStandardApplication(
                post_record_id=draft.id,
                site_standard_id=standard.id,
                status="applied",
                conflict_status="none",
                reviewer="Fictional Demo Engineer",
                review_note="Applied for the V1 walkthrough.",
            )
            db.add(application)
        tool_change = settings["tool_change"]
        tool_change.site_standard_ids_json = [standard.id]

        logic = db.scalar(
            select(CustomLogicItem).where(
                CustomLogicItem.post_record_id == draft.id,
                CustomLogicItem.name.in_(LOGIC_ALIASES),
            )
        )
        if logic is None:
            logic = CustomLogicItem(
                post_record_id=draft.id,
                name=LOGIC_NAME,
                category="Cycles",
                reason="Standard OFG configuration does not represent the required G74 behavior clearly enough for approval.",
                implementation_type="To be determined",
                status="needs_review",
                evidence_ids_json=[document.id],
                site_standard_ids_json=[],
                source_format="Site verification required",
                reviewer=None,
                review_note="Implementation may use FIL/CIMFIL; this has not been verified.",
            )
            db.add(logic)
            db.flush()
        logic.name = LOGIC_NAME
        logic.reason = "The exact historically approved G74 grooving output is not yet confirmed by the fictional source evidence."
        logic.implementation_type = "Potential FIL/CIMFIL customization — verification required"
        logic.status = "needs_review"
        logic.evidence_ids_json = [document.id]
        logic.source_format = "Site verification required"
        logic.reviewer = None
        logic.review_note = "Potential implementation only; verify in the local G-POST environment."
        cycle_setting = settings["lathe_cycles"]
        cycle_setting.value_json = facts["supported_cycles"].value_json
        cycle_setting.status = "custom_logic_required"
        cycle_setting.source_machine_fact_ids_json = [facts["supported_cycles"].id]
        cycle_setting.source_document_evidence_ids_json = [document.id]
        cycle_setting.requires_custom_logic = True
        cycle_setting.custom_logic_id = logic.id
        cycle_setting.source_type = "Machine Knowledge"

        question = db.scalar(
            select(OpenQuestion).where(
                OpenQuestion.post_record_id == draft.id,
                OpenQuestion.title.in_(("Confirm exact G74 behavior", "G74 behavior")),
            )
        )
        if question is None:
            question = OpenQuestion(
                post_record_id=draft.id,
                question_type="custom_logic",
                related_type="custom_logic",
                related_id=logic.id,
            )
            db.add(question)
        question.title = "Confirm exact G74 behavior"
        question.description = "Confirm the historically approved machine-level G74 grooving output before implementation."
        question.question_type = "custom_logic"
        question.related_type = "custom_logic"
        question.related_id = logic.id
        question.severity = "warning"
        question.source_context = f"{DOCUMENT_TITLE}, p. 74"
        question.owner = "NC Programmer"
        question.status = "open"
        question.resolution = None

        confirmed_ids = {fact.id for fact in facts.values() if fact.status in {"confirmed", "not_applicable"}}
        for stale_question in db.scalars(
            select(OpenQuestion).where(
                OpenQuestion.post_record_id == draft.id,
                OpenQuestion.related_type == "machine_fact",
                OpenQuestion.related_id.in_(confirmed_ids),
            )
        ):
            stale_question.status = "resolved"
            stale_question.resolution = "Resolved by the reviewed fictional demo machine profile."

        # The canonical walkthrough intentionally contains one—and only one—question record.
        for stale_question in db.scalars(
            select(OpenQuestion).where(
                OpenQuestion.post_record_id == draft.id,
                OpenQuestion.id != question.id,
            )
        ):
            db.delete(stale_question)

        db.commit()
        print("V1 fictional KLS demo seeded")
        print(f"machine_id={machine.id} revision_id={revision.id} post_record_id={draft.id}")
        print(f"document_id={document.id} site_standard_id={standard.id} custom_logic_id={logic.id}")
        print("FICTIONAL SAMPLE — NOT FOR MACHINE USE")


if __name__ == "__main__":
    main()

"""Seed a fictional Phase 11 section-drafting workspace without external AI."""
from hashlib import sha256

from sqlalchemy import select

from app.api.profile_extraction import ensure_initial_revision
from app.db.alembic import upgrade_database
from app.db.session import SessionLocal
from app.gpost.service import capability_snapshot, default_templates, initial_mappings, revision_snapshot
from app.models.entities import DocumentChunk, DocumentType, MachineProfile, MachineType, ProcessingStatus, SourceDocument, utc_now
from app.models.gpost import GPostDraft, PostRuleDraft, PostSectionDraft


def main() -> None:
    upgrade_database()
    with SessionLocal() as db:
        machine = db.scalar(select(MachineProfile).where(MachineProfile.name == "Fictional Phase 11 Post Builder Demo"))
        if machine is None:
            machine = MachineProfile(
                name="Fictional Phase 11 Post Builder Demo", manufacturer="Fictional Training Systems", model="PB-11",
                controller_name="FANUC fictional context", controller_manufacturer="FANUC", controller_model="DEMO-ONLY",
                controller_version="SIMULATED", machine_type=MachineType.MILL, axis_count=3, max_spindle_rpm=8000,
                max_feed_rate=200, supported_work_offsets=["G54", "G55"], approved_g_codes=["G00", "G01", "G17", "G40", "G80", "G90", "G94"],
                approved_m_codes=["M03", "M04", "M05", "M08", "M09", "M30"], restricted_commands=[],
                safe_start_template="G17 G40 G80 G90 G94", tool_change_template="T{tool} M06", program_end_template="M05\nM09\nM30",
                notes="FICTIONAL SAMPLE — NOT FOR MACHINE USE",
            )
            db.add(machine); db.flush()
        revision = ensure_initial_revision(machine, db)
        revision.status = "approved"; revision.approved_at = revision.approved_at or utc_now(); machine.active_revision_id = revision.id
        evidence_text = "Fictional controller evidence: M03 starts clockwise spindle rotation, M04 starts counter-clockwise rotation, and M05 stops the spindle."
        document = db.scalar(select(SourceDocument).where(SourceDocument.machine_profile_id == machine.id, SourceDocument.title == "Fictional Phase 11 Controller Evidence"))
        if document is None:
            document = SourceDocument(machine_profile_id=machine.id, title="Fictional Phase 11 Controller Evidence",
                document_type=DocumentType.CONTROLLER_MANUAL, processing_status=ProcessingStatus.READY,
                extracted_text=evidence_text, page_count=1, ai_post_builder_allowed=True)
            db.add(document); db.flush()
        document.ai_post_builder_allowed = True
        chunk = db.scalar(select(DocumentChunk).where(DocumentChunk.document_id == document.id, DocumentChunk.chunk_index == 0))
        if chunk is None:
            chunk = DocumentChunk(document_id=document.id, machine_profile_id=machine.id, chunk_index=0, page_start=1, page_end=1,
                section_title="Fictional spindle control", content=evidence_text, content_hash=sha256(evidence_text.encode()).hexdigest(), token_estimate=22)
            db.add(chunk); db.flush()
        draft = db.scalar(select(GPostDraft).where(GPostDraft.machine_profile_id == machine.id, GPostDraft.name == "Fictional Phase 11 AI-assisted Post"))
        if draft is None:
            draft = GPostDraft(machine_profile_id=machine.id, machine_profile_revision_id=revision.id, name="Fictional Phase 11 AI-assisted Post",
                version=1, status="review_required", controller_family="fanuc_mill", machine_type="mill", selected_document_ids_json=[document.id],
                capability_snapshot_json=capability_snapshot(revision), machine_profile_snapshot_json=revision_snapshot(revision, machine),
                templates_json=default_templates(revision, "fanuc_mill"), warnings_json=["R&D only; no production authorization."], review_summary_json={})
            db.add(draft); db.flush(); db.add_all(initial_mappings(draft))
        section = db.scalar(select(PostSectionDraft).where(PostSectionDraft.gpost_draft_id == draft.id, PostSectionDraft.section_key == "spindle"))
        if section is None:
            evidence = {"evidence_id": chunk.id, "document_id": document.id, "document_title": document.title, "page_start": 1,
                "page_end": 1, "section_title": chunk.section_title, "excerpt": evidence_text, "ai_eligible": True}
            section = PostSectionDraft(gpost_draft_id=draft.id, section_key="spindle", section_version=1, status="needs_review",
                source_type="mock_ai_seed", machine_context_snapshot_json={"controller": revision.controller_model, "max_spindle_rpm": revision.max_spindle_rpm},
                source_evidence_json=[evidence], assumptions_json=["Synthetic demo context only."], warnings_json=["Engineer review required."],
                ai_generated=True, provider="mock", model="deterministic-fixture", prompt_version="post-section-draft-v2", response_schema_version="post-section-draft-response-v2")
            db.add(section); db.flush()
            for key, name, condition, template in [
                ("spindle_clockwise_start", "Clockwise Spindle Start", "clockwise spindle requested", "S{rpm:g} M03"),
                ("spindle_counterclockwise_start", "Counter-clockwise Spindle Start", "counter-clockwise spindle requested", "S{rpm:g} M04"),
                ("spindle_stop", "Spindle Stop", "spindle stop requested", "M05"),
            ]:
                db.add(PostRuleDraft(post_section_draft_id=section.id, rule_key=key, name=name, condition=condition,
                    output_behavior=template, ai_draft_template=template, required_machine_facts_json=["controller", "max_spindle_rpm"],
                    evidence_ids_json=[chunk.id], status="needs_review", warnings_json=["Not accepted automatically."]))
        db.commit()
        print("Phase 11 fictional Post Builder demo seeded")
        print(f"machine_id={machine.id} revision_id={revision.id} draft_id={draft.id} section=spindle")
        print("provider=mock external_ai_used=false rules_status=needs_review")
        print("cl_ncl_included=false part_geometry_included=false production_gcode_included=false")
        print("FICTIONAL SAMPLE — NOT FOR MACHINE USE")


if __name__ == "__main__":
    main()

"""Deterministic Phase 11 section readiness and evidence retrieval."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session, load_only

from app.models.entities import DocumentChunk, DocumentType, ProcessingStatus, SourceDocument
from app.models.gpost import GPostDraft, GPostMapping, PostSectionDraft
from app.models.profile_extraction import MachineProfileRevision

SECTION_LABELS = {
    "program_structure": "Program Structure", "tooling": "Tooling", "spindle": "Spindle", "coolant": "Coolant",
    "feed": "Feed", "motion": "Motion", "coordinates": "Coordinates", "program_end": "Program End", "cycles": "Cycles",
}
SECTION_VOCABULARY = {
    "program_structure": ["program header", "program number", "safe start", "initialization", "units", "plane", "absolute", "incremental", "program end"],
    "tooling": ["tool", "tool change", "turret", "offset", "tool call", "tool station"],
    "spindle": ["spindle", "rpm", "clockwise", "counterclockwise", "m03", "m04", "m05", "g96", "g97", "css"],
    "coolant": ["coolant", "flood", "mist", "m08", "m09"],
    "feed": ["feed", "ipm", "ipr", "g94", "g95", "feed mode"],
    "motion": ["rapid", "linear", "arc", "g00", "g01", "g02", "g03"],
    "coordinates": ["work offset", "g54", "g55", "reference return", "machine coordinate", "g53", "g28"],
    "program_end": ["m02", "m30", "rewind", "program end"],
    "cycles": ["canned cycle", "thread cycle", "g71", "g76", "cycle"],
}
AI_ELIGIBLE_DOCUMENT_TYPES = {
    DocumentType.MACHINE_MANUAL, DocumentType.CONTROLLER_MANUAL, DocumentType.PROGRAMMING_MANUAL,
    DocumentType.SPECIFICATION_DOCUMENT, DocumentType.POST_PROCESSOR_DOCUMENT, DocumentType.COMPANY_STANDARD,
    DocumentType.PARAMETER_LIST, DocumentType.MACHINE_CONFIGURATION_DOCUMENT,
}


def _template(draft: GPostDraft, key: str):
    return (draft.templates_json or {}).get(key)


def section_facts(revision: MachineProfileRevision, draft: GPostDraft, section: str) -> list[dict]:
    common = [
        ("controller", "Controller", revision.controller_model or revision.controller_name, True),
        ("machine_type", "Machine Type", revision.machine_type, True),
    ]
    specific = {
        "program_structure": [("safe_start", "Safe Start", _template(draft, "safe_start") or revision.safe_start_template, True), ("units", "Units", revision.units or _template(draft, "units"), True), ("plane", "Default Plane", _template(draft, "plane_selection"), False)],
        "tooling": [("tool_change", "Tool Change", _template(draft, "tool_change") or revision.tool_change_template, True), ("tool_selection", "Tool Selection", _template(draft, "tool_selection"), True)],
        "spindle": [("max_spindle_rpm", "Maximum RPM", revision.max_spindle_rpm, True), ("spindle_cw", "Clockwise", _template(draft, "spindle_start_cw"), True), ("spindle_ccw", "Counter-clockwise", _template(draft, "spindle_start_ccw"), True), ("spindle_stop", "Stop", _template(draft, "spindle_stop"), True), ("speed_mode", "Speed Mode", _template(draft, "spindle_mode"), False)],
        "coolant": [("coolant_on", "Flood / Coolant On", _template(draft, "coolant_on"), True), ("coolant_off", "Coolant Off", _template(draft, "coolant_off"), True), ("mist", "Mist", _template(draft, "coolant_mist"), False)],
        "feed": [("feed_mode", "Feed Mode", _template(draft, "feed_mode"), True), ("feed_format", "Feed Format", _template(draft, "feed_rate"), True), ("feed_limit", "Feed Limit", revision.max_feed_rate, False)],
        "motion": [("rapid", "Rapid", _template(draft, "rapid_move"), True), ("linear", "Linear", _template(draft, "linear_feed_move"), True), ("arc_cw", "Arc CW", _template(draft, "arc_cw"), False), ("arc_ccw", "Arc CCW", _template(draft, "arc_ccw"), False)],
        "coordinates": [("work_offsets", "Work Offsets", revision.supported_work_offsets_json, True), ("distance_mode", "Distance Mode", _template(draft, "distance_mode"), True), ("reference_return", "Reference Return", _template(draft, "reference_return"), False)],
        "program_end": [("program_end", "Program End", _template(draft, "program_end") or revision.program_end_template, True), ("spindle_stop", "Spindle Stop", _template(draft, "spindle_stop"), False), ("coolant_off", "Coolant Off", _template(draft, "coolant_off"), False)],
        "cycles": [("cycle_support", "Cycle Support", None, True)],
    }
    rows = common + specific.get(section, [])
    result = []
    for key, label, value, critical in rows:
        known = value is not None and value != "" and value != []
        result.append({"key": key, "label": label, "value": value, "status": "known" if known else "unknown", "critical": critical, "source": "approved machine profile / post draft"})
    return result


class PostBuilderEvidenceRetrievalService:
    def __init__(self, db: Session): self.db = db

    def eligible_rows(self, draft: GPostDraft):
        """Load the eligible source corpus once for callers evaluating every section."""
        statement = (select(DocumentChunk, SourceDocument)
                     .options(load_only(DocumentChunk.id, DocumentChunk.document_id, DocumentChunk.machine_profile_id,
                                        DocumentChunk.page_start, DocumentChunk.page_end, DocumentChunk.section_title,
                                        DocumentChunk.content),
                              load_only(SourceDocument.id, SourceDocument.title, SourceDocument.document_type,
                                        SourceDocument.processing_status, SourceDocument.ai_post_builder_allowed))
                     .join(SourceDocument, SourceDocument.id == DocumentChunk.document_id)
                     .where(DocumentChunk.machine_profile_id == draft.machine_profile_id,
                            SourceDocument.ai_post_builder_allowed.is_(True),
                            SourceDocument.document_type.in_(AI_ELIGIBLE_DOCUMENT_TYPES),
                            SourceDocument.processing_status == ProcessingStatus.READY))
        if draft.selected_document_ids_json:
            statement = statement.where(SourceDocument.id.in_(draft.selected_document_ids_json))
        return self.db.execute(statement).all()

    def retrieve(self, draft: GPostDraft, section: str, query: str | None = None, limit: int = 12,
                 source_rows=None) -> list[dict]:
        terms = SECTION_VOCABULARY[section] + ([query.lower()] if query else [])
        rows = []
        for chunk, document in source_rows if source_rows is not None else self.eligible_rows(draft):
            lowered = chunk.content.lower(); matched = [term for term in terms if term in lowered]
            if not matched: continue
            score = min(1.0, len(set(matched)) / max(3, len(SECTION_VOCABULARY[section]) / 3))
            rows.append({"evidence_id": chunk.id, "document_id": document.id, "document_title": document.title,
                         "document_type": document.document_type.value, "page_start": chunk.page_start, "page_end": chunk.page_end,
                         "section_title": chunk.section_title, "excerpt": chunk.content[:1200], "relevance_score": round(score, 3),
                         "matched_terms": sorted(set(matched)), "ai_eligible": True, "conflict_labels": []})
        rows.sort(key=lambda item: (-item["relevance_score"], item["evidence_id"]))
        self._mark_conflicts(rows)
        return rows[:limit]

    @staticmethod
    def _mark_conflicts(rows: list[dict]) -> None:
        commands = {}
        for row in rows:
            found = set(re.findall(r"\b[GM]\d{2,3}\b", row["excerpt"].upper()))
            for term in row["matched_terms"]:
                commands.setdefault(term, set()).update(found)
        conflicting = {term for term, values in commands.items() if len(values) > 1 and term not in {"spindle", "coolant", "motion", "program end"}}
        for row in rows:
            row["conflict_labels"] = [f"Conflicting command evidence for {term}" for term in row["matched_terms"] if term in conflicting]


def section_readiness(db: Session, draft: GPostDraft, revision: MachineProfileRevision, section: str,
                      source_rows=None, reviewed_rules=None, latest: PostSectionDraft | None = None) -> dict:
    facts = section_facts(revision, draft, section)
    evidence = PostBuilderEvidenceRetrievalService(db).retrieve(draft, section, source_rows=source_rows)
    category = SECTION_LABELS[section].lower()
    if reviewed_rules is None:
        reviewed_rules = list(db.scalars(select(GPostMapping).where(GPostMapping.gpost_draft_id == draft.id,
            GPostMapping.review_status.in_(["accepted", "accepted_with_edit"]))))
    related_reviewed = [rule for rule in reviewed_rules if category in str((rule.conditions_json or {}).get("category", "")).lower() or section in rule.mapping_key.lower()]
    missing = [item["label"] for item in facts if item["critical"] and item["status"] == "unknown"]
    conflicts = [{"type": "conflicting_evidence", "message": label} for row in evidence for label in row["conflict_labels"]]
    if latest is None:
        latest = db.scalar(select(PostSectionDraft).where(PostSectionDraft.gpost_draft_id == draft.id, PostSectionDraft.section_key == section).order_by(PostSectionDraft.section_version.desc()))
    if section == "cycles": readiness = "deferred"
    elif missing: readiness = "needs_information"
    elif conflicts: readiness = "ready_with_review"
    else: readiness = "ready"
    manual = "needs_information" if missing else ("ready_with_review" if conflicts else "ready")
    evidence_basis = bool(evidence or related_reviewed or (revision.status in {"approved", "active"} and any(item["status"] == "known" for item in facts[2:])))
    ai_readiness = "deferred" if section == "cycles" else (readiness if evidence_basis else "needs_information")
    warnings = [] if evidence_basis else ["Approved evidence or reviewed machine-level knowledge is required for AI-assisted drafting."]
    return {"section_key": section, "label": SECTION_LABELS[section], "readiness": ai_readiness,
            "manual_setup_readiness": manual, "ai_drafting_readiness": ai_readiness, "known_machine_facts": facts,
            "missing_information": missing, "warnings": warnings, "conflicts": conflicts, "evidence_count": len(evidence),
            "reviewed_rule_count": len(related_reviewed), "current_draft_status": latest.status if latest else "not_started",
            "draft_allowed": ai_readiness in {"ready", "ready_with_review"} and section != "cycles"}

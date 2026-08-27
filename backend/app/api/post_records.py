"""Structured Post Record engineering data and development-package exports."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import MachineProfile, SourceDocument, utc_now
from app.models.gpost import (CustomLogicItem, GPostDiagnostic, GPostDraft, MachineKnowledgeFact, OFGSetting, OpenQuestion,
    PostRuleDraft, PostSectionDraft, PostStandardApplication, PostValidationRecord, SiteStandard,
    ValidationFinding, ValidationPolicy)
from app.models.profile_extraction import MachineProfileRevision
from app.ofg.domain import (CODE_STATUSES, DEFINITIONS, PATH_STATUSES, SOURCE_TYPES, applicable_for_progress,
    evaluate_relevance)
from app.schemas.post_records import (CustomLogicRead, CustomLogicWrite, MachineFactRead, MachineFactWrite,
    OFGSettingRead, OFGSettingWrite, OpenQuestionRead, OpenQuestionWrite, PostRecordSummary,
    DiagnosticParseRequest, DiagnosticRead, SiteStandardRead, SiteStandardWrite,
    StandardApplicationRead, StandardApplicationWrite, ValidationFindingRead, ValidationFindingWrite,
    ValidationPolicyRead, ValidationPolicyWrite, ValidationRecordRead, ValidationRecordWrite)
from app.validation.diagnostics import GPostDiagnosticParser, fil_static_checks

router = APIRouter(tags=["Post Records"])

FACT_STATUS = {"confirmed", "needs_review", "unknown", "conflicting", "not_applicable"}
OFG_STATUS = {"unmapped", "mapped", "needs_review", "needs_information", "conflicting", "reviewed", "not_applicable", "custom_logic_required"}
DEFAULT_REQUIRED_GATES = ["Configuration Review", "G-POST Compilation", "NC Programmer Review"]
DEFAULT_OPTIONAL_GATES = ["Controlled Test Post", "Local NC Review", "VERICUT Simulation", "Dry Run"]
_DEFAULT_INITIALIZATION_LOCK = threading.Lock()


def record_or_404(record_id: int, db: Session) -> GPostDraft:
    record = db.get(GPostDraft, record_id)
    if record is None: raise HTTPException(404, "Post Record not found")
    return record


def editable_record(record_id: int, db: Session) -> GPostDraft:
    record = record_or_404(record_id, db)
    if record.status in {"superseded", "archived"}:
        raise HTTPException(409, "Historical or archived Post Records are read-only")
    return record


def row_or_404(model, row_id: int, record_id: int, db: Session):
    editable_record(record_id, db)
    row = db.get(model, row_id)
    if row is None or row.post_record_id != record_id: raise HTTPException(404, "Post Record item not found")
    return row


def _value(draft: GPostDraft, revision: MachineProfileRevision, key: str):
    values = {
        "machine_type": revision.machine_type, "controller": revision.controller_model or revision.controller_name,
        "axes": revision.axis_count, "x_travel": [revision.x_min, revision.x_max], "y_travel": [revision.y_min, revision.y_max],
        "z_travel": [revision.z_min, revision.z_max], "max_spindle_rpm": revision.max_spindle_rpm,
        "max_feed_rate": revision.max_feed_rate, "work_offsets": revision.supported_work_offsets_json,
        "safe_start": draft.templates_json.get("safe_start"), "tool_change": draft.templates_json.get("tool_change"),
        "spindle_cw": draft.templates_json.get("spindle_start_cw"), "spindle_ccw": draft.templates_json.get("spindle_start_ccw"),
        "spindle_stop": draft.templates_json.get("spindle_stop"), "coolant_on": draft.templates_json.get("coolant_on"),
        "coolant_off": draft.templates_json.get("coolant_off"), "feed_mode": draft.templates_json.get("feed_mode"),
        "rapid_move": draft.templates_json.get("rapid_move"), "linear_move": draft.templates_json.get("linear_feed_move"),
        "program_end": draft.templates_json.get("program_end"), "supported_cycles": None,
    }
    value = values[key]
    if isinstance(value, list) and not any(item is not None for item in value): return None
    return value


FACT_DEFS = [
    ("General", "machine_type", "Machine Type", None), ("General", "controller", "Controller", None),
    ("Kinematics / Axes", "axes", "Controlled Axes", None), ("Kinematics / Axes", "x_travel", "X Travel", None),
    ("Kinematics / Axes", "y_travel", "Y Travel", None), ("Kinematics / Axes", "z_travel", "Z Travel", None),
    ("Tooling", "tool_change", "Tool Change Behavior", None), ("Spindle", "max_spindle_rpm", "Maximum Spindle RPM", "RPM"),
    ("Spindle", "spindle_cw", "Spindle Clockwise Command", None), ("Spindle", "spindle_ccw", "Spindle Counter-clockwise Command", None),
    ("Spindle", "spindle_stop", "Spindle Stop Command", None), ("Coolant", "coolant_on", "Coolant On Command", None),
    ("Coolant", "coolant_off", "Coolant Off Command", None), ("Feed", "feed_mode", "Feed Mode", None),
    ("Feed", "max_feed_rate", "Maximum Feed Rate", None), ("Motion", "rapid_move", "Rapid Motion Format", None),
    ("Motion", "linear_move", "Linear Motion Format", None), ("Coordinates", "work_offsets", "Supported Work Offsets", None),
    ("Cycles", "supported_cycles", "Supported Cycles", None), ("Program Structure", "safe_start", "Safe Start Behavior", None),
    ("Program End", "program_end", "Program End Behavior", None),
]

def _structured_default(kind: str | None, revision: MachineProfileRevision) -> object | None:
    if kind == "address_format":
        addresses = ["G", "M", "X", "Z"] if "lathe" in (revision.machine_type or "").lower() else ["G", "M", "X", "Y", "Z"]
        return [{"address": item, "description": None, "output_order": index + 1,
                 "before_alias": None, "after_alias": None, "metric_format": None, "inch_format": None,
                 "status": "unknown", "source": "Unknown"} for index, item in enumerate(addresses)]
    if kind == "sequence_numbers":
        return {"maximum": None, "start": None, "increment": None, "frequency": None,
                "block_delete": None, "optional_output": None}
    if kind == "file_extension": return {"extension": None}
    if kind == "address_output": return {"decimal_character": None, "address_spacing": None, "address_case": None}
    if kind == "cycle_capabilities": return {"supported": [], "unresolved": True}
    if kind == "code_table": return []
    return None


def _setting_fact_keys(key: str, primary: str | None) -> list[str]:
    if key == "axis_limits": return ["x_travel", "y_travel", "z_travel"]
    if key == "spindle_codes": return ["spindle_cw", "spindle_ccw", "spindle_stop"]
    if key == "coolant_flood": return ["coolant_on"]
    if key == "coolant_off": return ["coolant_off"]
    return [primary] if primary else []


def _setting_value(definition, facts_by_key: dict[str, MachineKnowledgeFact]) -> object | None:
    keys = _setting_fact_keys(definition.key, definition.fact_key)
    if definition.key == "axis_limits":
        values = {key.removesuffix("_travel").upper(): facts_by_key[key].value_json for key in keys if key in facts_by_key}
        return values or None
    if definition.key == "spindle_codes":
        return {key.removeprefix("spindle_").upper(): facts_by_key[key].value_json for key in keys if key in facts_by_key}
    if keys and keys[0] in facts_by_key: return facts_by_key[keys[0]].value_json
    return None


def ensure_defaults(db: Session, draft: GPostDraft) -> None:
    # The workspace loads facts, settings, and summary concurrently. Serialize lazy
    # initialization and fill by stable key so those requests cannot create copies.
    with _DEFAULT_INITIALIZATION_LOCK:
        revision = db.get(MachineProfileRevision, draft.machine_profile_revision_id)
        if revision is None: return
        existing_facts = {row.fact_key: row for row in db.scalars(select(MachineKnowledgeFact).where(
            MachineKnowledgeFact.post_record_id == draft.id))}
        for category, key, name, unit in FACT_DEFS:
            if key in existing_facts: continue
            value = _value(draft, revision, key)
            fact = MachineKnowledgeFact(post_record_id=draft.id, category=category, fact_key=key, name=name,
                value_json=value, unit=unit, status="confirmed" if value not in (None, "", []) else "unknown",
                source_label=f"Machine configuration revision {revision.revision_number}", source_location="Reviewed machine profile")
            db.add(fact); db.flush(); existing_facts[key] = fact
        existing_settings = {row.setting_key: row for row in db.scalars(select(OFGSetting).where(OFGSetting.post_record_id == draft.id))}
        definition_keys = {definition.key for definition in DEFINITIONS}
        for key, legacy in existing_settings.items():
            if key not in definition_keys:
                # Preserve older checklist rows for history/export without letting replaced generic rows
                # inflate the current machine-specific checklist or its progress.
                legacy.is_applicable = False
                legacy.relevance_class = "conditional"
                legacy.relevance_label = "not_applicable"
        capabilities = revision.capabilities_json or {}
        for definition in DEFINITIONS:
            row = existing_settings.get(definition.key)
            relevance = evaluate_relevance(definition, machine_type=revision.machine_type, axis_count=revision.axis_count,
                controller=" ".join(filter(None, (revision.controller_manufacturer, revision.controller_name, revision.controller_model))),
                capabilities=capabilities, user_selected=bool(row and row.user_selected))
            fact_keys = _setting_fact_keys(definition.key, definition.fact_key)
            source_facts = [existing_facts[key] for key in fact_keys if key in existing_facts]
            if row is None:
                value = _setting_value(definition, existing_facts)
                structured = _structured_default(definition.structured_kind, revision)
                known_source = bool(source_facts and any(fact.status == "confirmed" for fact in source_facts))
                row = OFGSetting(post_record_id=draft.id, setting_key=definition.key, display_name=definition.name,
                    value_json=value, unit=source_facts[0].unit if len(source_facts) == 1 else None,
                    status="needs_review" if known_source or structured is not None else "needs_information",
                    source_machine_fact_ids_json=[fact.id for fact in source_facts],
                    source_type="Machine Knowledge" if source_facts else "OFG Reference",
                    structured_value_json=structured, code_status="unknown" if definition.structured_kind == "code_table" else None,
                    **relevance)
                db.add(row); existing_settings[definition.key] = row
            # Definition metadata is synchronized; reviewed values and notes are preserved.
            row.category = definition.category; row.subsection = definition.subsection
            row.display_name = definition.name; row.description = definition.purpose
            row.ofg_menu_path = definition.path; row.ofg_menu_path_status = definition.path_status
            row.relevance_class = relevance["relevance_class"]
            row.relevance_label = relevance["relevance_label"]
            row.is_applicable = relevance["is_applicable"]
            if row.source_type == "Unknown": row.source_type = "Machine Knowledge" if row.source_machine_fact_ids_json else "OFG Reference"
            if row.structured_value_json is None and definition.structured_kind and row.value_json is None:
                row.structured_value_json = _structured_default(definition.structured_kind, revision)
            if row.code_status is None and definition.structured_kind == "code_table": row.code_status = "unknown"
        existing_question_fact_ids = set(db.scalars(select(OpenQuestion.related_id).where(
            OpenQuestion.post_record_id == draft.id, OpenQuestion.related_type == "machine_fact")))
        for fact in existing_facts.values():
            if fact.status == "unknown" and fact.id not in existing_question_fact_ids:
                db.add(OpenQuestion(post_record_id=draft.id, question_type="machine_knowledge", title=f"Confirm {fact.name}",
                    description="Required machine knowledge is not confirmed.", related_type="machine_fact", related_id=fact.id,
                    severity="warning", source_context=fact.source_label, status="open"))
        db.commit()


def fact_read(row: MachineKnowledgeFact, settings: list[OFGSetting]) -> dict:
    data = MachineFactRead.model_validate(row).model_dump()
    data["used_by"] = [{"type": "ofg_setting", "id": item.id, "label": item.display_name}
                       for item in settings if row.id in item.source_machine_fact_ids_json]
    return data


def setting_read(row: OFGSetting, facts: dict[int, MachineKnowledgeFact]) -> dict:
    data = OFGSettingRead.model_validate(row).model_dump()
    data["source_machine_facts"] = [{"id": fact.id, "name": fact.name, "value": fact.value_json,
                                      "status": fact.status, "source": fact.source_label,
                                      "source_location": fact.source_location}
                                     for fact_id in row.source_machine_fact_ids_json if (fact := facts.get(fact_id))]
    return data


@router.get("/post-records/{record_id}/machine-knowledge", response_model=list[MachineFactRead])
def list_facts(record_id: int, db: Session = Depends(get_db)):
    draft = record_or_404(record_id, db); ensure_defaults(db, draft)
    facts = list(db.scalars(select(MachineKnowledgeFact).where(MachineKnowledgeFact.post_record_id == record_id).order_by(MachineKnowledgeFact.category, MachineKnowledgeFact.name)))
    settings = list(db.scalars(select(OFGSetting).where(OFGSetting.post_record_id == record_id)))
    return [fact_read(row, settings) for row in facts]


@router.post("/post-records/{record_id}/machine-knowledge", response_model=MachineFactRead, status_code=201)
def create_fact(record_id: int, payload: MachineFactWrite, db: Session = Depends(get_db)):
    editable_record(record_id, db)
    if payload.status not in FACT_STATUS: raise HTTPException(422, "Unsupported Machine Knowledge status")
    row = MachineKnowledgeFact(post_record_id=record_id, **payload.model_dump(), reviewed_at=utc_now() if payload.status == "confirmed" else None)
    db.add(row); db.commit(); db.refresh(row); return fact_read(row, [])


@router.put("/post-records/{record_id}/machine-knowledge/{item_id}", response_model=MachineFactRead)
def update_fact(record_id: int, item_id: int, payload: MachineFactWrite, db: Session = Depends(get_db)):
    row = row_or_404(MachineKnowledgeFact, item_id, record_id, db)
    if payload.status not in FACT_STATUS: raise HTTPException(422, "Unsupported Machine Knowledge status")
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    row.reviewed_at = utc_now() if payload.status == "confirmed" else None
    db.commit(); db.refresh(row)
    settings = list(db.scalars(select(OFGSetting).where(OFGSetting.post_record_id == record_id)))
    return fact_read(row, settings)


@router.delete("/post-records/{record_id}/machine-knowledge/{item_id}", status_code=204)
def delete_fact(record_id: int, item_id: int, db: Session = Depends(get_db)):
    db.delete(row_or_404(MachineKnowledgeFact, item_id, record_id, db)); db.commit(); return Response(status_code=204)


@router.get("/post-records/{record_id}/ofg-settings", response_model=list[OFGSettingRead])
def list_ofg(record_id: int, include_advanced: bool = Query(False), db: Session = Depends(get_db)):
    draft = record_or_404(record_id, db); ensure_defaults(db, draft)
    facts = {row.id: row for row in db.scalars(select(MachineKnowledgeFact).where(MachineKnowledgeFact.post_record_id == record_id))}
    visibility = ((OFGSetting.is_applicable.is_(True)) | (OFGSetting.relevance_class == "advanced")) if include_advanced else (
        OFGSetting.is_applicable.is_(True) & (OFGSetting.relevance_class != "advanced"))
    query = select(OFGSetting).where(OFGSetting.post_record_id == record_id, visibility)
    rows = list(db.scalars(query.order_by(OFGSetting.category, OFGSetting.display_name)))
    return [setting_read(row, facts) for row in rows]


@router.post("/post-records/{record_id}/ofg-settings", response_model=OFGSettingRead, status_code=201)
def create_ofg(record_id: int, payload: OFGSettingWrite, db: Session = Depends(get_db)):
    editable_record(record_id, db)
    if payload.status not in OFG_STATUS: raise HTTPException(422, "Unsupported OFG status")
    validate_ofg_metadata(payload)
    row = OFGSetting(post_record_id=record_id, **payload.model_dump(), reviewed_at=utc_now() if payload.status == "reviewed" else None)
    db.add(row); db.commit(); db.refresh(row)
    facts = {row.id: row for row in db.scalars(select(MachineKnowledgeFact).where(MachineKnowledgeFact.post_record_id == record_id))}
    return setting_read(row, facts)


@router.put("/post-records/{record_id}/ofg-settings/{item_id}", response_model=OFGSettingRead)
def update_ofg(record_id: int, item_id: int, payload: OFGSettingWrite, db: Session = Depends(get_db)):
    row = row_or_404(OFGSetting, item_id, record_id, db)
    if payload.status not in OFG_STATUS: raise HTTPException(422, "Unsupported OFG status")
    validate_ofg_metadata(payload)
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    row.reviewed_at = utc_now() if payload.status == "reviewed" else None
    db.commit(); db.refresh(row)
    facts = {item.id: item for item in db.scalars(select(MachineKnowledgeFact).where(MachineKnowledgeFact.post_record_id == record_id))}
    return setting_read(row, facts)


def validate_ofg_metadata(payload: OFGSettingWrite) -> None:
    if payload.source_type not in SOURCE_TYPES: raise HTTPException(422, "Unsupported OFG source type")
    if payload.ofg_menu_path_status not in PATH_STATUSES: raise HTTPException(422, "Unsupported OFG path verification status")
    if payload.code_status is not None and payload.code_status not in CODE_STATUSES:
        raise HTTPException(422, "Unsupported code availability status")
    if payload.relevance_class not in {"core", "conditional", "advanced"}:
        raise HTTPException(422, "Unsupported OFG relevance class")


@router.delete("/post-records/{record_id}/ofg-settings/{item_id}", status_code=204)
def delete_ofg(record_id: int, item_id: int, db: Session = Depends(get_db)):
    db.delete(row_or_404(OFGSetting, item_id, record_id, db)); db.commit(); return Response(status_code=204)


@router.get("/site-standards", response_model=list[SiteStandardRead])
def list_standards(db: Session = Depends(get_db)):
    return list(db.scalars(select(SiteStandard).order_by(SiteStandard.name)))


@router.post("/site-standards", response_model=SiteStandardRead, status_code=201)
def create_standard(payload: SiteStandardWrite, db: Session = Depends(get_db)):
    row = SiteStandard(**payload.model_dump()); db.add(row); db.commit(); db.refresh(row); return row


@router.put("/site-standards/{item_id}", response_model=SiteStandardRead)
def update_standard(item_id: int, payload: SiteStandardWrite, db: Session = Depends(get_db)):
    row = db.get(SiteStandard, item_id)
    if row is None: raise HTTPException(404, "Site Standard not found")
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    db.commit(); db.refresh(row); return row


@router.delete("/site-standards/{item_id}", status_code=204)
def delete_standard(item_id: int, db: Session = Depends(get_db)):
    row = db.get(SiteStandard, item_id)
    if row is None: raise HTTPException(404, "Site Standard not found")
    if db.scalar(select(PostStandardApplication.id).where(PostStandardApplication.site_standard_id == item_id).limit(1)):
        raise HTTPException(409, "Remove this standard from Post Records before deleting it")
    db.delete(row); db.commit(); return Response(status_code=204)


def application_read(row: PostStandardApplication, standard: SiteStandard) -> dict:
    data = StandardApplicationRead.model_validate({**row.__dict__, "standard": standard}).model_dump(); return data


@router.get("/post-records/{record_id}/site-standards", response_model=list[StandardApplicationRead])
def list_applications(record_id: int, db: Session = Depends(get_db)):
    record_or_404(record_id, db)
    rows = list(db.scalars(select(PostStandardApplication).where(PostStandardApplication.post_record_id == record_id)))
    return [application_read(row, db.get(SiteStandard, row.site_standard_id)) for row in rows]


@router.post("/post-records/{record_id}/site-standards", response_model=StandardApplicationRead, status_code=201)
def apply_standard(record_id: int, payload: StandardApplicationWrite, db: Session = Depends(get_db)):
    editable_record(record_id, db); standard = db.get(SiteStandard, payload.site_standard_id)
    if standard is None: raise HTTPException(404, "Site Standard not found")
    existing = db.scalar(select(PostStandardApplication).where(PostStandardApplication.post_record_id == record_id,
        PostStandardApplication.site_standard_id == payload.site_standard_id))
    if existing: raise HTTPException(409, "Site Standard is already applied")
    row = PostStandardApplication(post_record_id=record_id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row); return application_read(row, standard)


@router.put("/post-records/{record_id}/site-standards/{item_id}", response_model=StandardApplicationRead)
def update_application(record_id: int, item_id: int, payload: StandardApplicationWrite, db: Session = Depends(get_db)):
    row = row_or_404(PostStandardApplication, item_id, record_id, db)
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    standard = db.get(SiteStandard, row.site_standard_id); db.commit(); db.refresh(row); return application_read(row, standard)


@router.delete("/post-records/{record_id}/site-standards/{item_id}", status_code=204)
def remove_application(record_id: int, item_id: int, db: Session = Depends(get_db)):
    db.delete(row_or_404(PostStandardApplication, item_id, record_id, db)); db.commit(); return Response(status_code=204)


def _crud_list(model, record_id: int, db: Session):
    record_or_404(record_id, db); return list(db.scalars(select(model).where(model.post_record_id == record_id).order_by(model.updated_at.desc())))


@router.get("/post-records/{record_id}/custom-logic", response_model=list[CustomLogicRead])
def list_logic(record_id: int, db: Session = Depends(get_db)): return _crud_list(CustomLogicItem, record_id, db)

@router.post("/post-records/{record_id}/custom-logic", response_model=CustomLogicRead, status_code=201)
def create_logic(record_id: int, payload: CustomLogicWrite, db: Session = Depends(get_db)):
    editable_record(record_id, db); row = CustomLogicItem(post_record_id=record_id, **payload.model_dump()); db.add(row); db.commit(); db.refresh(row); return row

@router.put("/post-records/{record_id}/custom-logic/{item_id}", response_model=CustomLogicRead)
def update_logic(record_id: int, item_id: int, payload: CustomLogicWrite, db: Session = Depends(get_db)):
    row = row_or_404(CustomLogicItem, item_id, record_id, db)
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    db.commit(); db.refresh(row); return row

@router.delete("/post-records/{record_id}/custom-logic/{item_id}", status_code=204)
def delete_logic(record_id: int, item_id: int, db: Session = Depends(get_db)):
    db.delete(row_or_404(CustomLogicItem, item_id, record_id, db)); db.commit(); return Response(status_code=204)


@router.post("/post-records/{record_id}/custom-logic/{item_id}/static-check")
def static_check_logic(record_id: int, item_id: int, payload: dict, db: Session = Depends(get_db)):
    row_or_404(CustomLogicItem, item_id, record_id, db)
    source = payload.get("source")
    if not isinstance(source, str) or len(source.encode("utf-8")) > 1_000_000:
        raise HTTPException(422, "FIL source must be local text no larger than 1 MB")
    return {"advisory_only": True, "compiler_authority": "Installed G-POST environment",
        "findings": fil_static_checks(source, payload.get("known_identifiers") or [])}


@router.get("/post-records/{record_id}/open-questions", response_model=list[OpenQuestionRead])
def list_questions(record_id: int, db: Session = Depends(get_db)): return _crud_list(OpenQuestion, record_id, db)

@router.post("/post-records/{record_id}/open-questions", response_model=OpenQuestionRead, status_code=201)
def create_question(record_id: int, payload: OpenQuestionWrite, db: Session = Depends(get_db)):
    editable_record(record_id, db); row = OpenQuestion(post_record_id=record_id, **payload.model_dump()); db.add(row); db.commit(); db.refresh(row); return row

@router.put("/post-records/{record_id}/open-questions/{item_id}", response_model=OpenQuestionRead)
def update_question(record_id: int, item_id: int, payload: OpenQuestionWrite, db: Session = Depends(get_db)):
    row = row_or_404(OpenQuestion, item_id, record_id, db)
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    db.commit(); db.refresh(row); return row

@router.delete("/post-records/{record_id}/open-questions/{item_id}", status_code=204)
def delete_question(record_id: int, item_id: int, db: Session = Depends(get_db)):
    db.delete(row_or_404(OpenQuestion, item_id, record_id, db)); db.commit(); return Response(status_code=204)


@router.get("/post-records/{record_id}/validation-records", response_model=list[ValidationRecordRead])
def list_validations(record_id: int, db: Session = Depends(get_db)):
    record_or_404(record_id, db); return list(db.scalars(select(PostValidationRecord).where(PostValidationRecord.post_record_id == record_id).order_by(PostValidationRecord.performed_at.desc())))

@router.post("/post-records/{record_id}/validation-records", response_model=ValidationRecordRead, status_code=201)
def create_validation(record_id: int, payload: ValidationRecordWrite, db: Session = Depends(get_db)):
    editable_record(record_id, db); data = payload.model_dump(); performed = data.pop("performed_at") or utc_now()
    row = PostValidationRecord(post_record_id=record_id, performed_at=performed, **data); db.add(row); db.commit(); db.refresh(row); return row

@router.put("/post-records/{record_id}/validation-records/{item_id}", response_model=ValidationRecordRead)
def update_validation(record_id: int, item_id: int, payload: ValidationRecordWrite, db: Session = Depends(get_db)):
    row = row_or_404(PostValidationRecord, item_id, record_id, db); data = payload.model_dump()
    data["performed_at"] = data["performed_at"] or row.performed_at
    for key, value in data.items(): setattr(row, key, value)
    db.commit(); db.refresh(row); return row

@router.delete("/post-records/{record_id}/validation-records/{item_id}", status_code=204)
def delete_validation(record_id: int, item_id: int, db: Session = Depends(get_db)):
    row = row_or_404(PostValidationRecord, item_id, record_id, db)
    db.execute(delete(ValidationFinding).where(ValidationFinding.validation_record_id == row.id))
    db.execute(delete(GPostDiagnostic).where(GPostDiagnostic.validation_record_id == row.id))
    db.delete(row); db.commit(); return Response(status_code=204)


def validation_or_404(record_id: int, validation_id: int, db: Session, editable: bool = False) -> PostValidationRecord:
    (editable_record if editable else record_or_404)(record_id, db)
    row = db.get(PostValidationRecord, validation_id)
    if row is None or row.post_record_id != record_id: raise HTTPException(404, "Validation record not found")
    return row


def sync_finding_counts(db: Session, validation: PostValidationRecord) -> None:
    rows = list(db.scalars(select(ValidationFinding).where(ValidationFinding.validation_record_id == validation.id)))
    open_rows = [row for row in rows if row.status in {"Open", "Investigating"}]
    validation.findings_count = len(rows)
    validation.blocking_findings_count = sum(row.severity in {"ERROR", "FATAL"} for row in open_rows)


@router.get("/post-records/{record_id}/validation-findings", response_model=list[ValidationFindingRead])
def list_findings(record_id: int, db: Session = Depends(get_db)):
    record_or_404(record_id, db)
    return list(db.scalars(select(ValidationFinding).join(PostValidationRecord).where(
        PostValidationRecord.post_record_id == record_id).order_by(ValidationFinding.created_at.desc())))


@router.post("/post-records/{record_id}/validation-records/{validation_id}/findings", response_model=ValidationFindingRead, status_code=201)
def create_finding(record_id: int, validation_id: int, payload: ValidationFindingWrite, db: Session = Depends(get_db)):
    validation = validation_or_404(record_id, validation_id, db, editable=True)
    row = ValidationFinding(validation_record_id=validation.id, **payload.model_dump()); db.add(row); db.flush()
    sync_finding_counts(db, validation); db.commit(); db.refresh(row); return row


@router.put("/post-records/{record_id}/validation-findings/{finding_id}", response_model=ValidationFindingRead)
def update_finding(record_id: int, finding_id: int, payload: ValidationFindingWrite, db: Session = Depends(get_db)):
    editable_record(record_id, db); row = db.get(ValidationFinding, finding_id)
    if row is None: raise HTTPException(404, "Validation finding not found")
    validation = validation_or_404(record_id, row.validation_record_id, db)
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    sync_finding_counts(db, validation); db.commit(); db.refresh(row); return row


@router.post("/post-records/{record_id}/validation-findings/{finding_id}/open-question", response_model=OpenQuestionRead, status_code=201)
def finding_to_question(record_id: int, finding_id: int, db: Session = Depends(get_db)):
    editable_record(record_id, db); finding = db.get(ValidationFinding, finding_id)
    if finding is None: raise HTTPException(404, "Validation finding not found")
    validation_or_404(record_id, finding.validation_record_id, db)
    row = OpenQuestion(post_record_id=record_id, question_type="validation_finding", title=finding.title,
        description=finding.description, severity="blocking" if finding.severity in {"ERROR", "FATAL"} else "warning",
        related_type="validation_finding", related_id=finding.id, source_context=f"Validation record #{finding.validation_record_id}",
        owner="NC Programmer", status="open")
    db.add(row); db.commit(); db.refresh(row); return row


@router.get("/post-records/{record_id}/validation-policy", response_model=ValidationPolicyRead)
def get_validation_policy(record_id: int, db: Session = Depends(get_db)):
    record_or_404(record_id, db); row = db.scalar(select(ValidationPolicy).where(ValidationPolicy.post_record_id == record_id))
    if row is None:
        return {"id": 0, "post_record_id": record_id, "name": "Default R&D Validation",
            "required_validation_types_json": DEFAULT_REQUIRED_GATES, "optional_validation_types_json": DEFAULT_OPTIONAL_GATES,
            "source": "Application default; site engineering must review", "reviewer": None, "updated_at": utc_now()}
    return row


@router.put("/post-records/{record_id}/validation-policy", response_model=ValidationPolicyRead)
def update_validation_policy(record_id: int, payload: ValidationPolicyWrite, db: Session = Depends(get_db)):
    editable_record(record_id, db); row = db.scalar(select(ValidationPolicy).where(ValidationPolicy.post_record_id == record_id))
    if row is None: row = ValidationPolicy(post_record_id=record_id); db.add(row)
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    db.commit(); db.refresh(row); return row


@router.get("/post-records/{record_id}/validation-timeline")
def validation_timeline(record_id: int, db: Session = Depends(get_db)):
    draft = record_or_404(record_id, db)
    rows = list(db.scalars(select(PostValidationRecord).where(PostValidationRecord.post_record_id == record_id)
        .order_by(PostValidationRecord.performed_at.asc(), PostValidationRecord.id.asc())))
    return {"post_record_id": record_id, "version": draft.version,
        "events": [{"id": row.id, "type": row.validation_type, "name": row.name, "result": row.result,
                    "performed_by": row.performed_by, "performed_at": row.performed_at,
                    "findings_count": row.findings_count} for row in rows]}


@router.get("/post-records/{record_id}/validation-handoff")
def validation_handoff(record_id: int, db: Session = Depends(get_db)):
    draft = record_or_404(record_id, db); summary = summary_data(db, draft)
    validations = list(db.scalars(select(PostValidationRecord).where(PostValidationRecord.post_record_id == record_id)))
    latest = {row.validation_type: row for row in sorted(validations, key=lambda item: item.performed_at)}
    logic = list(db.scalars(select(CustomLogicItem).where(CustomLogicItem.post_record_id == record_id)))
    machine = db.get(MachineProfile, draft.machine_profile_id)
    passed = lambda kind: kind in latest and latest[kind].result in {"PASS", "PASS_WITH_FINDINGS", "NOT_APPLICABLE"}
    return {"post_record_id": record_id, "post_version": draft.version, "machine": machine.name,
        "controller": machine.controller_model or machine.controller_name, "current_validation_status": summary["validation"]["status"],
        "outstanding_configuration_issues": len(summary["blockers"]),
        "custom_fil_status": "Reviewed" if logic and all(item.status in {"reviewed", "not_applicable"} for item in logic) else "Review required" if logic else "None identified",
        "development_package_url": f"/api/post-records/{record_id}/export?format=markdown",
        "checklist": [
            {"key": "gpost_configuration_entered", "label": "G-POST configuration entered", "complete": passed("OFG Entry Review")},
            {"key": "fil_compiled", "label": "FIL compiled", "complete": not logic or passed("G-POST Compilation")},
            {"key": "controlled_test_post", "label": "Controlled test post created", "complete": passed("Controlled Test Post")},
            {"key": "local_nc_output", "label": "NC output generated locally", "complete": passed("Local NC Review")},
            {"key": "ready_for_vericut", "label": "Ready for VERICUT", "complete": not summary["blockers"] and passed("Controlled Test Post")},
        ], "does_not_run_vericut": True}


@router.get("/post-records/{record_id}/diagnostics", response_model=list[DiagnosticRead])
def list_diagnostics(record_id: int, db: Session = Depends(get_db)):
    record_or_404(record_id, db)
    return list(db.scalars(select(GPostDiagnostic).join(PostValidationRecord).where(
        PostValidationRecord.post_record_id == record_id).order_by(GPostDiagnostic.id)))


@router.post("/post-records/{record_id}/validation-records/{validation_id}/diagnostics/parse", response_model=list[DiagnosticRead])
def parse_diagnostics(record_id: int, validation_id: int, payload: DiagnosticParseRequest, db: Session = Depends(get_db)):
    validation = validation_or_404(record_id, validation_id, db, editable=True)
    logic = list(db.scalars(select(CustomLogicItem).where(CustomLogicItem.post_record_id == record_id)))
    try: parsed = GPostDiagnosticParser().parse(payload.listing_text, [(row.id, row.name) for row in logic])
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    db.execute(delete(GPostDiagnostic).where(GPostDiagnostic.validation_record_id == validation.id))
    created = []
    for item in parsed:
        row = GPostDiagnostic(validation_record_id=validation.id, **item.__dict__); db.add(row); db.flush(); created.append(row)
        if payload.create_findings and item.severity in {"WARNING", "ERROR", "FATAL"}:
            db.add(ValidationFinding(validation_record_id=validation.id, severity=item.severity, category="G-POST Diagnostic",
                title=item.message[:220], description=item.raw_excerpt, related_custom_logic_id=item.custom_logic_reference_id,
                status="Open"))
    digest = hashlib.sha256(payload.listing_text.encode("utf-8")).hexdigest()
    validation.external_tool = validation.external_tool or "G-POST diagnostic listing"
    validation.external_reference = payload.file_name or validation.external_reference
    validation.references_json = list(dict.fromkeys([*validation.references_json, f"sha256:{digest}"]))
    db.flush(); sync_finding_counts(db, validation); db.commit()
    for row in created: db.refresh(row)
    return created


def engineering_snapshot(db: Session, draft: GPostDraft) -> dict:
    ensure_defaults(db, draft)
    def serial(value): return value.isoformat() if isinstance(value, datetime) else value
    def rows(model): return [{key: serial(value) for key, value in row.__dict__.items() if not key.startswith("_")}
                             for row in db.scalars(select(model).where(model.post_record_id == draft.id))]
    snapshot = {"machine_knowledge": rows(MachineKnowledgeFact), "ofg_settings": rows(OFGSetting),
            "site_standard_applications": rows(PostStandardApplication), "custom_logic": rows(CustomLogicItem),
            "open_questions": rows(OpenQuestion), "validation_records": rows(PostValidationRecord)}
    validation_ids = [row["id"] for row in snapshot["validation_records"]]
    snapshot["validation_findings"] = [{key: serial(value) for key, value in row.__dict__.items() if not key.startswith("_")}
        for row in db.scalars(select(ValidationFinding).where(ValidationFinding.validation_record_id.in_(validation_ids)))] if validation_ids else []
    snapshot["gpost_diagnostics"] = [{key: serial(value) for key, value in row.__dict__.items() if not key.startswith("_")}
        for row in db.scalars(select(GPostDiagnostic).where(GPostDiagnostic.validation_record_id.in_(validation_ids)))] if validation_ids else []
    policy = db.scalar(select(ValidationPolicy).where(ValidationPolicy.post_record_id == draft.id))
    snapshot["validation_policy"] = ({key: serial(value) for key, value in policy.__dict__.items() if not key.startswith("_")} if policy else
        {"name": "Default R&D Validation", "required_validation_types_json": DEFAULT_REQUIRED_GATES,
         "optional_validation_types_json": DEFAULT_OPTIONAL_GATES, "source": "Application default; site review required"})
    return snapshot


def clone_engineering_record(db: Session, source_id: int, target_id: int) -> None:
    maps: dict[type, dict[int, int]] = {}
    for model in (MachineKnowledgeFact, CustomLogicItem, PostValidationRecord):
        maps[model] = {}
        for row in db.scalars(select(model).where(model.post_record_id == source_id)):
            values = {column.name: getattr(row, column.name) for column in model.__table__.columns
                      if column.name not in {"id", "post_record_id", "created_at", "updated_at"}}
            if model is PostValidationRecord: values["post_version_id"] = None
            clone = model(post_record_id=target_id, **values); db.add(clone); db.flush(); maps[model][row.id] = clone.id
    fact_map = maps[MachineKnowledgeFact]; logic_map = maps[CustomLogicItem]
    ofg_map = {}
    for row in db.scalars(select(OFGSetting).where(OFGSetting.post_record_id == source_id)):
        values = {column.name: getattr(row, column.name) for column in OFGSetting.__table__.columns
                  if column.name not in {"id", "post_record_id", "created_at", "updated_at"}}
        values["source_machine_fact_ids_json"] = [fact_map[item] for item in row.source_machine_fact_ids_json if item in fact_map]
        values["custom_logic_id"] = logic_map.get(row.custom_logic_id)
        clone = OFGSetting(post_record_id=target_id, **values); db.add(clone); db.flush(); ofg_map[row.id] = clone.id
    related_maps = {"machine_fact": fact_map, "ofg_setting": ofg_map, "custom_logic": logic_map}
    for row in db.scalars(select(OpenQuestion).where(OpenQuestion.post_record_id == source_id)):
        values = {column.name: getattr(row, column.name) for column in OpenQuestion.__table__.columns
                  if column.name not in {"id", "post_record_id", "created_at", "updated_at"}}
        if row.related_type in related_maps: values["related_id"] = related_maps[row.related_type].get(row.related_id)
        db.add(OpenQuestion(post_record_id=target_id, **values))
    for row in db.scalars(select(PostStandardApplication).where(PostStandardApplication.post_record_id == source_id)):
        values = {column.name: getattr(row, column.name) for column in PostStandardApplication.__table__.columns
                  if column.name not in {"id", "post_record_id", "created_at", "updated_at"}}
        db.add(PostStandardApplication(post_record_id=target_id, **values))
    validation_map = maps[PostValidationRecord]
    for row in db.scalars(select(ValidationFinding).where(ValidationFinding.validation_record_id.in_(validation_map.keys()))):
        values = {column.name: getattr(row, column.name) for column in ValidationFinding.__table__.columns
                  if column.name not in {"id", "validation_record_id", "created_at", "updated_at"}}
        values["related_ofg_setting_id"] = ofg_map.get(row.related_ofg_setting_id)
        values["related_custom_logic_id"] = logic_map.get(row.related_custom_logic_id)
        db.add(ValidationFinding(validation_record_id=validation_map[row.validation_record_id], **values))
    for row in db.scalars(select(GPostDiagnostic).where(GPostDiagnostic.validation_record_id.in_(validation_map.keys()))):
        values = {column.name: getattr(row, column.name) for column in GPostDiagnostic.__table__.columns
                  if column.name not in {"id", "validation_record_id", "created_at"}}
        values["custom_logic_reference_id"] = logic_map.get(row.custom_logic_reference_id)
        db.add(GPostDiagnostic(validation_record_id=validation_map[row.validation_record_id], **values))
    policy = db.scalar(select(ValidationPolicy).where(ValidationPolicy.post_record_id == source_id))
    if policy:
        db.add(ValidationPolicy(post_record_id=target_id, name=policy.name,
            required_validation_types_json=list(policy.required_validation_types_json),
            optional_validation_types_json=list(policy.optional_validation_types_json), source=policy.source, reviewer=policy.reviewer))


def delete_engineering_record(db: Session, record_id: int) -> None:
    """Remove the additive package for a draft that is eligible for hard deletion."""
    validation_ids = list(db.scalars(select(PostValidationRecord.id).where(PostValidationRecord.post_record_id == record_id)))
    if validation_ids:
        db.execute(delete(ValidationFinding).where(ValidationFinding.validation_record_id.in_(validation_ids)))
        db.execute(delete(GPostDiagnostic).where(GPostDiagnostic.validation_record_id.in_(validation_ids)))
    db.execute(delete(ValidationPolicy).where(ValidationPolicy.post_record_id == record_id))
    for model in (OpenQuestion, OFGSetting, MachineKnowledgeFact, PostStandardApplication,
                  CustomLogicItem, PostValidationRecord):
        db.execute(delete(model).where(model.post_record_id == record_id))


def summary_data(db: Session, draft: GPostDraft) -> dict:
    ensure_defaults(db, draft)
    facts = list(db.scalars(select(MachineKnowledgeFact).where(MachineKnowledgeFact.post_record_id == draft.id)))
    settings = list(db.scalars(select(OFGSetting).where(OFGSetting.post_record_id == draft.id)))
    applicable_settings = [row for row in settings if applicable_for_progress(row)]
    standards = list(db.scalars(select(PostStandardApplication).where(PostStandardApplication.post_record_id == draft.id)))
    logic = list(db.scalars(select(CustomLogicItem).where(CustomLogicItem.post_record_id == draft.id)))
    questions = list(db.scalars(select(OpenQuestion).where(OpenQuestion.post_record_id == draft.id)))
    validations = list(db.scalars(select(PostValidationRecord).where(
        PostValidationRecord.post_record_id == draft.id
    ).order_by(PostValidationRecord.performed_at.desc(), PostValidationRecord.id.desc())))
    policy = db.scalar(select(ValidationPolicy).where(ValidationPolicy.post_record_id == draft.id))
    required_gates = list(policy.required_validation_types_json if policy else DEFAULT_REQUIRED_GATES)
    applied_standard_ids = [row.site_standard_id for row in standards if row.status == "applied"]
    if applied_standard_ids:
        for standard in db.scalars(select(SiteStandard).where(SiteStandard.id.in_(applied_standard_ids))):
            required_gates.extend(standard.validation_requirements_json)
    required_gates = list(dict.fromkeys(required_gates))
    latest_by_type = {}
    for row in validations:
        latest_by_type.setdefault(row.validation_type, row)
    passing_results = {"PASS", "PASS_WITH_FINDINGS", "NOT_APPLICABLE", "PASSED", "PASSED_WITH_FINDINGS"}
    gate_status = {gate: (latest_by_type[gate].result if gate in latest_by_type else "NOT_STARTED") for gate in required_gates}
    gates_satisfied = bool(required_gates) and all(result.upper() in passing_results for result in gate_status.values())
    findings = list(db.scalars(select(ValidationFinding).join(PostValidationRecord).where(
        PostValidationRecord.post_record_id == draft.id)))
    open_findings = [row for row in findings if row.status in {"Open", "Investigating"}]
    confirmed = sum(row.status in {"confirmed", "not_applicable"} for row in facts)
    reviewed_settings = sum(row.status == "reviewed" for row in applicable_settings)
    reviewed_logic = sum(row.status in {"reviewed", "rejected", "deferred"} for row in logic)
    open_questions = [row for row in questions if row.status not in {"resolved", "deferred"}]
    blocking_questions = [row for row in open_questions if row.severity == "blocking"]
    conflicts = [row for row in standards if row.conflict_status != "none"]
    blockers = ([{"type": "machine_fact", "id": row.id, "title": row.name, "reason": row.status} for row in facts if row.status in {"unknown", "conflicting"}] +
                [{"type": "ofg_setting", "id": row.id, "title": row.display_name, "reason": row.status} for row in applicable_settings if row.status in {"needs_information", "conflicting"}] +
                [{"type": "site_standard", "id": row.id, "title": "Site Standard Conflict", "reason": row.conflict_note or "Review required"} for row in conflicts])
    if draft.status == "archived": overall = "archived"
    elif validations: overall = "rnd_validated" if gates_satisfied and not blockers and not open_questions and not open_findings else "under_validation"
    elif blockers or blocking_questions: overall = "needs_information"
    elif facts and confirmed == len(facts) and applicable_settings and reviewed_settings == len(applicable_settings) and reviewed_logic == len(logic): overall = "ready_for_engineering_review"
    elif confirmed or reviewed_settings or standards or logic: overall = "building"
    else: overall = "setup"
    if confirmed < len(facts): next_action = {"label": "Continue Machine Knowledge Review", "path": "machine-knowledge"}
    elif reviewed_settings < len(applicable_settings): next_action = {"label": "Continue OFG Configuration", "path": "ofg-configuration"}
    elif open_questions: next_action = {"label": "Resolve Open Questions", "path": "review-validation"}
    elif reviewed_logic < len(logic): next_action = {"label": "Review Custom Logic", "path": "custom-logic"}
    else: next_action = {"label": "Begin Engineering Review", "path": "review-validation"}
    return {"post_record_id": draft.id, "status": overall,
        "machine_knowledge": {"reviewed": confirmed, "total": len(facts)},
        "ofg_configuration": {"reviewed": reviewed_settings, "total": len(applicable_settings)},
        "site_standards": {"applied": sum(row.status == "applied" for row in standards), "total": len(standards), "conflicts": len(conflicts)},
        "custom_logic": {"identified": len(logic), "reviewed": reviewed_logic},
        "open_questions": {"open": len(open_questions), "total": len(questions)},
        "validation": {"count": len(validations), "status": "NOT_STARTED" if not validations else validations[0].result,
            "required_gates": required_gates, "gate_status": gate_status, "gates_satisfied": gates_satisfied,
            "open_findings": len(open_findings),
            "stages": {
                "configuration_review": latest_by_type.get("Configuration Review").result if latest_by_type.get("Configuration Review") else "NOT_STARTED",
                "gpost_test": next((latest_by_type[item].result for item in ("Controlled Test Post", "G-POST Compilation") if item in latest_by_type), "NOT_STARTED"),
                "vericut": latest_by_type.get("VERICUT Simulation").result if latest_by_type.get("VERICUT Simulation") else "NOT_STARTED",
                "engineering_review": latest_by_type.get("NC Programmer Review").result if latest_by_type.get("NC Programmer Review") else "NOT_STARTED",
            }},
        "blockers": blockers, "next_action": next_action,
        "native_gpost_integration": {"status": "not_verified", "label": "Not Verified",
            "explanation": "This application produces reviewed engineering configuration data. Native G-POST/Option File Generator behavior requires validation in the installed site environment."}}


@router.get("/post-records/{record_id}/summary", response_model=PostRecordSummary)
def get_summary(record_id: int, db: Session = Depends(get_db)): return summary_data(db, record_or_404(record_id, db))


@router.get("/post-records/{record_id}/legacy-rules")
def list_legacy_rules(record_id: int, db: Session = Depends(get_db)):
    record_or_404(record_id, db)
    rows = db.execute(select(PostRuleDraft, PostSectionDraft).join(PostSectionDraft,
        PostSectionDraft.id == PostRuleDraft.post_section_draft_id).where(PostSectionDraft.gpost_draft_id == record_id)).all()
    return [{"id": rule.id, "section": section.section_key, "name": rule.name,
             "classification": rule.engineering_classification, "status": rule.status,
             "presentation": "Needs Classification" if rule.engineering_classification == "UNKNOWN" else rule.engineering_classification}
            for rule, section in rows]


@router.put("/post-records/{record_id}/legacy-rules/{rule_id}/classification")
def classify_legacy_rule(record_id: int, rule_id: int, payload: dict, db: Session = Depends(get_db)):
    editable_record(record_id, db)
    row = db.execute(select(PostRuleDraft, PostSectionDraft).join(PostSectionDraft,
        PostSectionDraft.id == PostRuleDraft.post_section_draft_id).where(PostRuleDraft.id == rule_id,
        PostSectionDraft.gpost_draft_id == record_id)).first()
    if row is None: raise HTTPException(404, "Legacy post rule not found")
    classification = payload.get("classification")
    if classification not in {"STANDARD_OFG", "CUSTOM_LOGIC", "SITE_STANDARD", "UNKNOWN"}:
        raise HTTPException(422, "Unsupported engineering classification")
    row[0].engineering_classification = classification; db.commit()
    return {"id": row[0].id, "classification": classification}


@router.get("/post-records/{record_id}/compare/{other_record_id}")
def compare_post_records(record_id: int, other_record_id: int, db: Session = Depends(get_db)):
    left = record_or_404(record_id, db); right = record_or_404(other_record_id, db)
    if left.machine_profile_id != right.machine_profile_id:
        raise HTTPException(422, "Post Record versions must belong to the same machine")
    left_data = engineering_snapshot(db, left); right_data = engineering_snapshot(db, right)
    def changed(section: str, key: str):
        def normalized(row): return {name: value for name, value in row.items() if name not in {"id", "post_record_id", "created_at", "updated_at"}}
        a = {row[key]: normalized(row) for row in left_data[section]}; b = {row[key]: normalized(row) for row in right_data[section]}
        return sorted(item for item in a.keys() | b.keys() if a.get(item) != b.get(item))
    return {"left": {"id": left.id, "version": left.version}, "right": {"id": right.id, "version": right.version},
        "machine_knowledge_changed": changed("machine_knowledge", "fact_key"),
        "ofg_settings_changed": changed("ofg_settings", "setting_key"),
        "custom_logic_changed": changed("custom_logic", "name"),
        "open_questions_changed": changed("open_questions", "title"),
        "site_standard_applications_changed": changed("site_standard_applications", "site_standard_id"),
        "validation_record_count": {"left": len(left_data["validation_records"]), "right": len(right_data["validation_records"])}}


def package_data(db: Session, draft: GPostDraft) -> dict:
    machine = db.get(MachineProfile, draft.machine_profile_id)
    documents = list(db.scalars(select(SourceDocument).where(SourceDocument.id.in_(draft.selected_document_ids_json)))) if draft.selected_document_ids_json else []
    snapshot = engineering_snapshot(db, draft); summary = summary_data(db, draft)
    standards = {row.id: row for row in db.scalars(select(SiteStandard))}
    snapshot["site_standards"] = [{"application": app, "standard": {key: value for key, value in standards[app["site_standard_id"]].__dict__.items() if not key.startswith("_")}}
                                  for app in snapshot["site_standard_applications"] if app["site_standard_id"] in standards]
    return {"package_type": "Post Development Package", "native_gpost_post": False,
        "native_gpost_integration": summary["native_gpost_integration"], "post_record": {"id": draft.id, "name": draft.name, "version": draft.version, "status": summary["status"]},
        "machine": {"id": machine.id, "name": machine.name, "manufacturer": machine.manufacturer, "model": machine.model,
                    "machine_type": draft.machine_type, "controller": machine.controller_model or machine.controller_name},
        "summary": summary, **snapshot,
        "sources": [{"id": row.id, "title": row.title, "classification": row.document_type.value,
                     "ai_eligibility": "allowed" if row.ai_post_builder_allowed else "not_allowed"} for row in documents]}


def markdown_package(data: dict) -> str:
    lines = [f"# {data['post_record']['name']} — Post Development Package", "",
        "> R&D engineering record. This is not a native G-POST post and is not production approval.", "",
        f"- Version: v{data['post_record']['version']}", f"- Status: {data['post_record']['status'].replace('_', ' ').title()}",
        f"- Machine: {data['machine']['name']}", f"- Controller: {data['machine']['controller']}", "",
        "## Reviewed Machine Knowledge", "", "| Category | Fact | Value | Status | Source |", "|---|---|---|---|---|"]
    for row in data["machine_knowledge"]:
        lines.append(f"| {row['category']} | {row['name']} | {json.dumps(row['value_json']) if row['value_json'] is not None else '—'} | {row['status']} | {row.get('source_label') or '—'} {row.get('source_location') or ''} |")
    lines += ["", "## OFG Configuration Checklist", "", "| Category | Setting | Value | Relevance | Source | Status | OFG Location | Reference Status | Custom Logic |", "|---|---|---|---|---|---|---|---|---|"]
    for row in data["ofg_settings"]:
        value = row["value_json"] if row["value_json"] is not None else row.get("structured_value_json")
        lines.append(f"| {row['category']} | {row['display_name']} | {json.dumps(value) if value is not None else '—'} | {row.get('relevance_label', 'unknown')} | {row.get('source_type', 'Unknown')} | {row['status']} | {row.get('ofg_menu_path') or 'Not verified'} | {row.get('ofg_menu_path_status', 'not_verified')} | {'Yes' if row['requires_custom_logic'] else 'No'} |")
    lines += ["", "## Site Standards", ""] + [f"- {row['standard']['name']} — {row['application']['status']}" for row in data["site_standards"]]
    lines += ["", "## Custom Logic", ""] + [f"- {row['name']} — {row['status']}: {row['reason']}" for row in data["custom_logic"]]
    lines += ["", "## Open Questions", ""] + [f"- {row['title']} — {row['status']}" for row in data["open_questions"]]
    lines += ["", "## Validation Records", ""] + [f"- {row['validation_type']} — {row['result']} ({row['performed_by']})" for row in data["validation_records"]]
    policy = data["validation_policy"]
    lines += ["", "## Validation Policy", "", f"- {policy['name']}",
        f"- Required gates: {', '.join(policy['required_validation_types_json'])}"]
    lines += ["", "## G-POST Diagnostic Summary", "",
        f"- Parsed diagnostics: {len(data['gpost_diagnostics'])}",
        f"- Validation findings: {len(data['validation_findings'])}"]
    for row in data["gpost_diagnostics"]:
        lines.append(f"- {row['severity']} {row.get('code') or ''}: {row['message']} (line {row.get('line_reference') or '—'})")
    lines += ["", "## Sensitive Artifact Boundary", "",
        "CL, NCL, CAD/part geometry, production NC, VERICUT project data, and full diagnostic files are not included by default. Only reviewed metadata, hashes, and references are exported."]
    lines += ["", "## Native G-POST Integration", "", "**Not Verified.** Final implementation/compilation remains in the governed Creo G-POST / Option File Generator environment."]
    return "\n".join(lines) + "\n"


@router.get("/post-records/{record_id}/export")
def export_package(record_id: int, format: str = "markdown", db: Session = Depends(get_db)):
    draft = record_or_404(record_id, db); data = package_data(db, draft)
    if format == "json":
        return Response(json.dumps(data, default=str, indent=2), media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="post-record-{record_id}-rnd.json"'})
    if format == "csv":
        output = io.StringIO(); writer = csv.writer(output)
        writer.writerow(["Category", "Setting", "Value", "Relevance", "Status", "Source Type", "Source", "OFG Location", "Reference Status", "Custom Logic Required", "Engineer Note"])
        facts = {row["id"]: row for row in data["machine_knowledge"]}
        for row in data["ofg_settings"]:
            sources = "; ".join(facts[item]["name"] for item in row["source_machine_fact_ids_json"] if item in facts)
            value = row["value_json"] if row["value_json"] is not None else row.get("structured_value_json")
            writer.writerow([row["category"], row["display_name"], json.dumps(value) if value is not None else "",
                row.get("relevance_label", "unknown"), row["status"], row.get("source_type", "Unknown"), sources,
                row.get("ofg_menu_path") or "Not verified", row.get("ofg_menu_path_status", "not_verified"),
                "Yes" if row["requires_custom_logic"] else "No", row.get("review_note") or ""])
        return Response(output.getvalue(), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="post-record-{record_id}-ofg-checklist.csv"'})
    if format != "markdown": raise HTTPException(422, "Supported formats: markdown, json, csv")
    return Response(markdown_package(data), media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="post-record-{record_id}-development-package.md"'})

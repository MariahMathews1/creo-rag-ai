from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from app.models.entities import (
    DocumentChunk, DocumentType, MachineProfile, MachineType, ProcessingStatus,
    SourceDocument,
)
from app.models.profile_extraction import (
    MachineProfileFieldSource, MachineProfileRevision, ProfileFieldProposal,
)
from app.profile_extraction.providers import (
    ExtractedFieldCandidate, MockProfileExtractionProvider, validate_candidates,
)
from app.profile_extraction.registry import FIELD_MAP
from app.profile_extraction.units import normalize_physical_value, normalize_unit
from app.documents.retrieval import RetrievedChunk
from app.core.config import get_settings


def add_document(db, machine_id, content, *, document_type=DocumentType.MACHINE_MANUAL,
                 status=ProcessingStatus.READY, title="Fictional manual"):
    document = SourceDocument(
        machine_profile_id=machine_id, title=title, document_type=document_type,
        original_filename="fictional.md", mime_type="text/markdown",
        processing_status=status, extracted_text=content,
    )
    db.add(document); db.flush()
    if status == ProcessingStatus.READY:
        db.add(DocumentChunk(
            document_id=document.id, machine_profile_id=machine_id,
            chunk_index=0, page_start=None, page_end=None,
            section_title="Specifications", content=content,
            content_hash=sha256(content.encode()).hexdigest(),
            token_estimate=max(1, len(content.split())),
        ))
    db.commit(); db.refresh(document)
    return document


def start_run(client, machine_id, document_ids, categories):
    return client.post(f"/api/machines/{machine_id}/profile-extraction-runs", json={
        "document_ids": document_ids, "target_machine_type": "mill",
        "selected_machine_variant": None, "field_categories": categories,
    })


def test_safe_unit_normalization_preserves_original_value():
    assert normalize_unit("IN") == "inch"
    converted = normalize_physical_value(12.5, "inch")
    assert converted == {
        "original_value": 12.5, "original_unit": "inch",
        "normalized_value": 317.5, "normalized_unit": "mm",
        "conversion_formula": "inch × 25.4",
    }
    assert normalize_physical_value(10, "ipm")["normalized_value"] == 254
    assert normalize_physical_value(5, "hp")["normalized_unit"] == "kW"
    assert normalize_unit("made-up-unit") is None


def test_provider_validation_rejects_invalid_citation_and_type():
    definition = FIELD_MAP["max_spindle_rpm"]
    chunks = [RetrievedChunk(
        document_id=1, document_title="Fictional", document_type="machine_manual",
        chunk_id=7, page_start=1, page_end=1, section_title="Spindle",
        content="Maximum spindle speed: 4000 rpm", relevance_score=.9,
    )]
    valid = ExtractedFieldCandidate(4000, "rpm", [7], .9, "found", None, False)
    assert validate_candidates(definition, [valid], chunks) == [valid]
    invalid = ExtractedFieldCandidate("fast", "rpm", [99], .9, "found", None, False)
    try:
        validate_candidates(definition, [invalid], chunks)
        assert False, "invalid structured output must be rejected"
    except ValueError:
        pass
    provider = MockProfileExtractionProvider()
    first = provider.extract_field_candidates(definition, chunks, {})
    second = provider.extract_field_candidates(definition, chunks, {})
    assert first == second
    assert first[0].value == 4000
    assert first[0].evidence_chunk_ids == [7]


def test_kls_key_value_regression_extracts_distinct_machine_fields(
    client, db_session, machine_profile,
):
    fixture = (
        Path(__file__).parent / "fixtures" / "kls_1840n_profile_spec.md"
    ).read_text()
    document = add_document(
        db_session, machine_profile.id, fixture,
        document_type=DocumentType.SPECIFICATION_DOCUMENT,
        title="KLS deterministic fixture",
    )
    response = start_run(client, machine_profile.id, [document.id], [])
    assert response.status_code == 200, response.text
    run = response.json()
    proposals = {
        item["field_key"]: item for item in client.get(
            f"/api/profile-extraction-runs/{run['id']}/proposals?page_size=250"
        ).json()
    }
    expected = {
        "manufacturer": ("Kent USA", None),
        "machine_model": ("KLS-1840N", None),
        "machine_type": ("CNC lathe", None),
        "controller_manufacturer": ("FANUC", None),
        "controller_model": ("FANUC 0i-Mate TF", None),
        "x_travel": (11, "inch"),
        "z_travel": (38, "inch"),
        "min_spindle_rpm": (100, "rpm"),
        "max_spindle_rpm": (2000, "rpm"),
        "spindle_power": (7.5, "hp"),
        "rapid_traverse_rate_x": (315, "ipm"),
        "rapid_traverse_rate_z": (394, "ipm"),
        "tool_station_count": (4, None),
        "spindle_bore": (3, "inch"),
        "spindle_nose": ("D8", None),
        "spindle_taper": ("MT No. 7", None),
        "chuck_size": (10, "inch"),
        "tailstock_present": (True, None),
        "coolant_present": (True, None),
        "automatic_lubrication_present": (True, None),
        "net_weight": (5236, "lb"),
        "gross_weight": (5720, "lb"),
    }
    for key, (value, unit) in expected.items():
        proposal = proposals[key]
        assert proposal["proposal_status"] == "found", key
        assert proposal["proposed_value_json"] == value, key
        assert proposal["unit"] == unit, key
        assert proposal["evidence"], key
        assert proposal["evidence"][0]["document_chunk_id"]
    assert proposals["overall_dimensions"]["proposed_value_json"] == {
        "length": 100.0, "width": 55.0, "height": 67.0, "unit": "inch",
    }
    power = proposals["spindle_power"]
    assert power["requires_exact_machine_verification"] is True
    assert "Optional alternative(s) documented: 10 hp" in power["interpretation_note"]
    assert any(
        item["evidence_type"] == "contextual"
        and item["normalized_value_json"]["original_value"] == 10
        for item in power["evidence"]
    )
    assert proposals["x_min"]["proposal_status"] == "not_found"
    assert proposals["z_max"]["proposal_status"] == "not_found"
    assert proposals["rapid_traverse_rate"]["proposal_status"] == "not_found"
    assert run["summary_json"]["documentation_coverage"] > 8.2


def test_variant_rerun_is_immutable_and_recalculates_applicability(
    client, db_session, machine_profile,
):
    content = (
        "Machine model: KLS-1840N\n"
        "Manual variants: KLS-1840N and KLS-2660N\n"
        "X-axis travel: 11 inches\n"
    )
    document = add_document(
        db_session, machine_profile.id, content,
        document_type=DocumentType.SPECIFICATION_DOCUMENT,
    )
    original = start_run(
        client, machine_profile.id, [document.id], ["identity", "axis_limits"],
    ).json()
    original_proposals = client.get(
        f"/api/profile-extraction-runs/{original['id']}/proposals?page_size=250"
    ).json()
    original_x = next(item for item in original_proposals if item["field_key"] == "x_travel")
    assert original_x["proposal_status"] == "ambiguous"
    rerun = client.post(
        f"/api/profile-extraction-runs/{original['id']}/rerun"
        "?selected_machine_variant=KLS-1840N"
    )
    assert rerun.status_code == 200, rerun.text
    updated = rerun.json()
    assert updated["id"] != original["id"]
    assert updated["selected_machine_variant"] == "KLS-1840N"
    updated_proposals = client.get(
        f"/api/profile-extraction-runs/{updated['id']}/proposals?page_size=250"
    ).json()
    updated_x = next(item for item in updated_proposals if item["field_key"] == "x_travel")
    assert updated_x["proposal_status"] == "found"
    preserved = client.get(
        f"/api/profile-extraction-runs/{original['id']}/proposals?page_size=250"
    ).json()
    assert preserved == original_proposals


def test_structured_aliases_ranges_pairs_and_number_words(
    client, db_session, machine_profile,
):
    document = add_document(
        db_session, machine_profile.id,
        "Machine model: KLS-1840N\n"
        "Cross-slide travel: 11 inches\n"
        "Longitudinal travel: 38 inches\n"
        "Spindle speeds: 100-2000 RPM\n"
        "Rapid traverse speed (Z/X-axis): 394/315 inches per minute\n"
        "Automatic tool post: Four positions\n",
        document_type=DocumentType.SPECIFICATION_DOCUMENT,
    )
    run = start_run(
        client, machine_profile.id, [document.id],
        ["identity", "axis_limits", "spindle", "feed_and_motion", "tooling"],
    ).json()
    proposals = {
        item["field_key"]: item for item in client.get(
            f"/api/profile-extraction-runs/{run['id']}/proposals?page_size=250"
        ).json()
    }
    assert proposals["x_travel"]["proposed_value_json"] == 11
    assert proposals["z_travel"]["proposed_value_json"] == 38
    assert proposals["min_spindle_rpm"]["proposed_value_json"] == 100
    assert proposals["max_spindle_rpm"]["proposed_value_json"] == 2000
    assert proposals["rapid_traverse_rate_x"]["proposed_value_json"] == 315
    assert proposals["rapid_traverse_rate_z"]["proposed_value_json"] == 394
    assert proposals["tool_station_count"]["proposed_value_json"] == 4


def test_debug_not_found_diagnostics_are_explainable(
    client, db_session, machine_profile,
):
    settings = get_settings()
    prior = settings.enable_profile_extraction_debug
    settings.enable_profile_extraction_debug = True
    try:
        document = add_document(
            db_session, machine_profile.id, "Machine model: KLS-1840N",
            document_type=DocumentType.SPECIFICATION_DOCUMENT,
        )
        run = start_run(
            client, machine_profile.id, [document.id], ["axis_limits"],
        ).json()
        proposals = client.get(
            f"/api/profile-extraction-runs/{run['id']}/proposals?page_size=250"
        ).json()
        x_travel = next(
            item for item in proposals if item["field_key"] == "x_travel"
        )
        diagnostics = x_travel["confidence_components_json"]["diagnostics"]
        assert diagnostics["search_terms"]
        assert diagnostics["retrieved_chunk_ids"] == []
        assert diagnostics["key_value_label_matched"] is False
        assert diagnostics["rejected_candidates"][0]["reason"]
        assert diagnostics["selected_variant"] is None
        assert diagnostics["document_authority"] == []
        assert diagnostics["field_normalization"] is None
    finally:
        settings.enable_profile_extraction_debug = prior


def test_machine_model_repair_creates_draft_without_rewriting_approved_revision(
    client, db_session, machine_profile,
):
    fixture = (
        Path(__file__).parent / "fixtures" / "kls_1840n_profile_spec.md"
    ).read_text()
    document = add_document(
        db_session, machine_profile.id, fixture,
        document_type=DocumentType.SPECIFICATION_DOCUMENT,
    )
    run = start_run(
        client, machine_profile.id, [document.id], ["identity", "controller"],
    ).json()
    approved_before = db_session.get(
        MachineProfileRevision, machine_profile.active_revision_id
    )
    approved_before.model = "F"
    db_session.commit()
    proposals = client.get(
        f"/api/profile-extraction-runs/{run['id']}/proposals?page_size=250"
    ).json()
    machine_model = next(
        item for item in proposals if item["field_key"] == "machine_model"
    )
    reviewed = client.put(
        f"/api/profile-field-proposals/{machine_model['id']}/review",
        json={"review_status": "accepted"},
    )
    assert reviewed.status_code == 200
    draft = client.post(
        f"/api/profile-extraction-runs/{run['id']}/apply-to-draft",
        json={
            "base_strategy": "active",
            "review_summary": "Explicit machine/controller identity repair draft.",
        },
    ).json()["revision"]
    db_session.refresh(approved_before)
    db_session.refresh(machine_profile)
    assert draft["model"] == "KLS-1840N"
    assert draft["status"] == "draft"
    assert approved_before.model == "F"
    assert approved_before.status == "approved"
    assert machine_profile.active_revision_id == approved_before.id


def test_extraction_detects_conflict_variants_missing_and_real_citations(
    client, db_session, machine_profile,
):
    first = add_document(
        db_session, machine_profile.id,
        "Manufacturer: Example\nMachine model: VM-3\nController: Orion 40M\n"
        "Maximum spindle speed: 4,000 rpm\nX-axis travel: 20 inches\n"
        "Models VM-30 and VM-30X. Live tooling: optional.",
        document_type=DocumentType.OPERATOR_MANUAL, title="Operator manual",
    )
    second = add_document(
        db_session, machine_profile.id,
        "Maximum spindle speed: 4,500 rpm\nModels VM-30 and VM-30X.",
        document_type=DocumentType.SPECIFICATION_DOCUMENT, title="Option sheet",
    )
    response = start_run(
        client, machine_profile.id, [first.id, second.id],
        ["identity", "axis_limits", "spindle", "capabilities"],
    )
    assert response.status_code == 200, response.text
    run = response.json()
    assert run["advisory_only"] is True
    assert run["machine_profile_is_draft"] is True
    assert run["qualified_review_required"] is True
    assert run["summary_json"]["conflict_count"] >= 1
    assert run["summary_json"]["not_found_count"] >= 1
    assert run["detected_variants_json"] == ["VM-30", "VM-30X"]

    proposals = client.get(
        f"/api/profile-extraction-runs/{run['id']}/proposals"
    ).json()
    spindle = next(item for item in proposals if item["field_key"] == "max_spindle_rpm")
    assert spindle["proposal_status"] == "conflicting"
    assert {item["document_title"] for item in spindle["evidence"]} == {
        "Operator manual", "Option sheet",
    }
    assert all(item["document_chunk_id"] for item in spindle["evidence"])
    x_min = next(item for item in proposals if item["field_key"] == "x_min")
    assert x_min["proposal_status"] == "not_found"


def test_document_selection_validation(client, db_session, machine_profile):
    unsupported = add_document(
        db_session, machine_profile.id, "Other notes",
        document_type=DocumentType.OTHER,
    )
    assert start_run(client, machine_profile.id, [unsupported.id], ["identity"]).status_code == 422
    pending = add_document(
        db_session, machine_profile.id, "Manual", status=ProcessingStatus.UPLOADED,
    )
    assert start_run(client, machine_profile.id, [pending.id], ["identity"]).status_code == 422
    other_machine = MachineProfile(
        name="Other machine", manufacturer="Other", model="O-1",
        controller_name="Other", machine_type=MachineType.MILL, axis_count=3,
    )
    db_session.add(other_machine); db_session.commit()
    foreign = add_document(db_session, other_machine.id, "Manufacturer: Other")
    assert start_run(client, machine_profile.id, [foreign.id], ["identity"]).status_code == 422
    assert start_run(client, 99999, [foreign.id], ["identity"]).status_code == 404


def test_review_draft_approval_supersedes_and_preserves_provenance(
    client, db_session, machine_profile,
):
    document = add_document(
        db_session, machine_profile.id,
        "Manufacturer: Example\nMachine model: VM-3\nMachine type: mill\n"
        "Controller: Fanuc-style\nMaximum spindle speed: 8,000 rpm",
    )
    response = start_run(
        client, machine_profile.id, [document.id],
        ["identity", "controller", "spindle"],
    )
    run = response.json()
    proposals = client.get(
        f"/api/profile-extraction-runs/{run['id']}/proposals"
    ).json()
    for proposal in proposals:
        if proposal["field_key"] == "max_spindle_rpm":
            payload = {
                "review_status": "accepted_with_edit", "reviewed_value": 8000,
                "unit": "rpm", "review_note": "Reviewed fictional test limit.",
            }
        elif proposal["proposal_status"] == "found":
            payload = {"review_status": "accepted"}
        else:
            payload = {
                "review_status": "deferred",
                "review_note": "Intentionally deferred because it was not documented.",
            }
        reviewed = client.put(
            f"/api/profile-field-proposals/{proposal['id']}/review", json=payload
        )
        assert reviewed.status_code == 200, reviewed.text

    draft_response = client.post(
        f"/api/profile-extraction-runs/{run['id']}/apply-to-draft",
        json={"base_strategy": "active", "review_summary": "Reviewed test draft"},
    )
    assert draft_response.status_code == 200, draft_response.text
    draft = draft_response.json()["revision"]
    machine_before = client.get(f"/api/machines/{machine_profile.id}").json()
    assert machine_before["active_revision_id"] != draft["id"]
    blocked = client.post(
        f"/api/machine-profile-revisions/{draft['id']}/approve",
        json={
            "exact_machine_applicability_confirmed": False,
            "safety_notice_acknowledged": True, "review_note": "No confirmation",
        },
    )
    assert blocked.status_code == 422
    approved = client.post(
        f"/api/machine-profile-revisions/{draft['id']}/approve",
        json={
            "exact_machine_applicability_confirmed": True,
            "safety_notice_acknowledged": True,
            "review_note": "Exact fictional test machine reviewed.",
        },
    )
    assert approved.status_code == 200, approved.text
    revisions = client.get(f"/api/machines/{machine_profile.id}/revisions").json()
    assert revisions[0]["status"] == "approved"
    assert revisions[-1]["status"] == "superseded"
    comparison = client.get(
        f"/api/machine-profile-revisions/{draft['id']}/compare/{revisions[-1]['id']}"
    )
    assert comparison.status_code == 200
    assert db_session.scalar(select(MachineProfileFieldSource).where(
        MachineProfileFieldSource.machine_profile_revision_id == draft["id"],
        MachineProfileFieldSource.field_key == "max_spindle_rpm",
    )) is not None
    rejected_draft = client.post(
        f"/api/profile-extraction-runs/{run['id']}/apply-to-draft",
        json={"base_strategy": "blank", "review_summary": "Blank rejection test"},
    ).json()["revision"]
    rejected = client.post(
        f"/api/machine-profile-revisions/{rejected_draft['id']}/reject",
        json={"review_note": "Rejected test revision."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_analysis_uses_stored_revision_snapshot(client, db_session, machine_profile):
    created = client.post("/api/analyses", json={
        "name": "Snapshot test", "machine_profile_id": machine_profile.id,
        "gcode_source": "G90 G54\nS9000 M03\nM30",
    })
    assert created.status_code == 201, created.text
    project = created.json()
    assert project["machine_profile_revision_id"]
    assert project["machine_profile_snapshot_json"]["max_spindle_rpm"] == 10000
    machine_profile.max_spindle_rpm = 100
    db_session.commit()
    result = client.post(f"/api/analyses/{project['id']}/run")
    assert result.status_code == 200, result.text
    assert not any(
        item["rule_id"] == "SPINDLE_MAX_RPM"
        for item in result.json()["findings"]
    )
    unchanged = client.get(f"/api/analyses/{project['id']}").json()
    assert unchanged["machine_profile_snapshot_json"]["max_spindle_rpm"] == 10000

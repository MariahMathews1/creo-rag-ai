from types import SimpleNamespace

from app.ofg.domain import DEFINITION_BY_KEY, applicable_for_progress, evaluate_relevance


def relevant(key: str, machine_type: str, axes: int, **kwargs):
    return evaluate_relevance(DEFINITION_BY_KEY[key], machine_type=machine_type, axis_count=axes, **kwargs)


def test_simple_lathe_and_mill_relevance_is_machine_specific():
    assert relevant("feed_upr", "lathe", 2)["relevance_label"] == "applicable"
    assert relevant("mill_cycles", "lathe", 2)["is_applicable"] is False
    assert relevant("mill_cycles", "vertical_mill", 3)["is_applicable"] is True
    assert relevant("feed_upr", "vertical_mill", 3)["relevance_label"] == "not_applicable"


def test_axis_and_capability_rules_hide_advanced_content_until_relevant_or_selected():
    assert relevant("multax", "vertical_mill", 3)["is_applicable"] is False
    assert relevant("multax", "vertical_mill", 5)["relevance_label"] == "advanced"
    assert relevant("multax", "vertical_mill", 3, user_selected=True)["is_applicable"] is True
    assert relevant("operator_messages", "lathe", 2, capabilities={"operator_messages": False})["is_applicable"] is False
    assert relevant("controller_specific_cycles", "vertical_mill", 5, controller="FANUC 31i")["is_applicable"] is False
    assert relevant("controller_specific_cycles", "vertical_mill", 5, controller="Siemens 840D")["is_applicable"] is True


def test_progress_excludes_irrelevant_and_not_applicable_settings():
    assert applicable_for_progress(SimpleNamespace(is_applicable=True, status="reviewed")) is True
    assert applicable_for_progress(SimpleNamespace(is_applicable=False, status="reviewed")) is False
    assert applicable_for_progress(SimpleNamespace(is_applicable=True, status="not_applicable")) is False


def test_reference_paths_and_structured_concepts_are_explicit():
    address = DEFINITION_BY_KEY["mcd_address_format"]
    assert address.path == "File Formats → MCD File → MCD File Format"
    assert address.structured_kind == "address_format"
    assert DEFINITION_BY_KEY["mcd_extension"].structured_kind == "file_extension"
    assert DEFINITION_BY_KEY["custom_fil"].path_status == "site_verification_needed"

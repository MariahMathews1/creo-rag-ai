"""Machine-specific OFG checklist definitions grounded in the collected OFG reference.

This catalog describes engineering checklist metadata only. It does not claim to
generate, import, or validate a native option file in an installed G-POST site.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CATEGORIES = (
    "Machine & Axes", "Transforms & Output", "File Formats", "Program Start / End", "Motion", "Cycles",
    "Machine Codes", "Tooling / Cutter Compensation", "Spindle", "Coolant", "Feedrates",
    "Operator Messages", "Advanced / Custom",
)
SOURCE_TYPES = {
    "Machine Knowledge", "Controller Documentation", "OFG Reference", "Site Standard",
    "Existing Post Reference", "Engineer Entry", "Unknown",
}
PATH_STATUSES = {"verified_from_reference", "site_verification_needed", "not_verified"}
CODE_STATUSES = {"defined", "not_available", "not_required", "unknown"}


@dataclass(frozen=True)
class OFGSettingDefinition:
    key: str
    name: str
    category: str
    subsection: str
    purpose: str
    path: str | None
    relevance: str = "core"
    machine_families: tuple[str, ...] = ("mill", "lathe")
    minimum_axes: int = 0
    fact_key: str | None = None
    structured_kind: str | None = None
    path_status: str = "verified_from_reference"
    controller_tokens: tuple[str, ...] = ()


def d(key: str, name: str, category: str, subsection: str, purpose: str, path: str | None,
      relevance: str = "core", families: tuple[str, ...] = ("mill", "lathe"), axes: int = 0,
      fact: str | None = None, structured: str | None = None,
      path_status: str = "verified_from_reference", controller: tuple[str, ...] = ()) -> OFGSettingDefinition:
    return OFGSettingDefinition(key, name, category, subsection, purpose, path, relevance, families, axes, fact, structured, path_status, controller)


DEFINITIONS = (
    d("machine_type", "Machine Type", "Machine & Axes", "Machine", "Defines the base machine category used by OFG.", "Type, Specs, & Axes → Machine → Machine Type", fact="machine_type"),
    d("controlled_axes", "Controlled Axes", "Machine & Axes", "Axes", "Records the controlled linear and rotary axes.", "Type, Specs, & Axes → Axes → Axis Values", fact="axes"),
    d("axis_limits", "Axis Limit Checking", "Machine & Axes", "Axes", "Records axis travel limits and limit-checking requirements.", "Type, Specs, & Axes → Axes → Axis Limit Checking", fact="axis_limits"),
    d("transformation_output", "Transformation and Output Mode", "Transforms & Output", "Output", "Records transformation and coordinate-output choices.", "Transforms & Output → Output", "conditional", axes=4),
    d("mcd_address_format", "MCD Address Format", "File Formats", "MCD File", "Defines address descriptions, output order, aliases, and metric/inch formats.", "File Formats → MCD File → MCD File Format", structured="address_format"),
    d("decimal_format", "General Address Output", "File Formats", "MCD File", "Defines decimal, spacing, and address-case conventions.", "File Formats → MCD File → General Address Output", structured="address_output"),
    d("mcd_extension", "MCD File Extension", "File Formats", "File Type", "Records the site-reviewed output extension without assuming .nc.", "File Formats → File Type", structured="file_extension"),
    d("sequence_numbers", "Sequence Numbers", "File Formats", "Sequence Numbers", "Defines maximum, start, increment, frequency, block-delete, and optional-output behavior.", "File Formats → Sequence Numbers", structured="sequence_numbers"),
    d("program_start", "Program Start", "Program Start / End", "Start of Program", "Defines reviewed start-of-program behavior.", "Start/End → Start Prog", fact="safe_start"),
    d("program_end", "Program End", "Program Start / End", "End of Program", "Defines reviewed end-of-program behavior.", "Start/End → General", fact="program_end"),
    d("default_prep_codes", "Default Preparatory Modes", "Program Start / End", "Default Prep Codes", "Records default preparatory modes only when supported by evidence or site standards.", "Start/End → Default Prep Codes", structured="code_table"),
    d("linear_motion", "Linear Motion", "Motion", "Linear", "Defines linear interpolation output behavior.", "Motion → Linear", fact="linear_move"),
    d("rapid_motion", "Rapid Motion", "Motion", "Rapid", "Defines rapid positioning output behavior.", "Motion → Rapid", fact="rapid_move"),
    d("circular_motion", "Circular Motion", "Motion", "Circular", "Defines circular interpolation behavior and format.", "Motion → Circular → General", structured="circular_motion"),
    d("plane_selection", "Circular Plane Selection", "Motion", "Circular", "Records plane-selection behavior for circular output.", "Motion → Circular → Plane", "conditional", families=("mill",), structured="code_table"),
    d("lathe_cycles", "Lathe Cycle Configuration", "Cycles", "Cycle Motion", "Records controller-supported turning cycle behavior; unresolved support remains unknown.", "Motion → Cycles → Cycle Motion", "conditional", families=("lathe",), fact="supported_cycles", structured="cycle_capabilities"),
    d("mill_cycles", "Mill Cycle Configuration", "Cycles", "Cycle Motion", "Records controller-supported holemaking cycle behavior; unsupported cycles are not assumed.", "Motion → Cycles → Cycle Motion", "conditional", families=("mill",), fact="supported_cycles", structured="cycle_capabilities"),
    d("prep_codes", "Preparatory (G) Codes", "Machine Codes", "Prep Codes", "Records G-code definitions and Defined/Not Available/Not Required/Unknown state.", "Machine Codes → Prep/G Codes", structured="code_table"),
    d("aux_codes", "Auxiliary (M) Codes", "Machine Codes", "Aux Codes", "Records M-code definitions without converting unavailable or not-required values to zero.", "Machine Codes → Aux/M Codes", structured="code_table"),
    d("tool_change", "Tool Change", "Tooling / Cutter Compensation", "Tool Change", "Defines reviewed tool-change behavior.", "Tool Change → General", fact="tool_change"),
    d("cutter_compensation", "Cutter Compensation", "Tooling / Cutter Compensation", "Cutter Compensation", "Records controller-supported cutter compensation behavior.", "Machine Codes → Cutter Comp → 2-3 Axis", "conditional", families=("mill",), structured="code_table"),
    d("spindle_codes", "Spindle Codes", "Spindle", "Codes", "Records spindle direction and stop code assignments.", "Spindle → Codes / Aux", structured="code_table"),
    d("maximum_spindle_speed", "Maximum Spindle Speed", "Spindle", "Direct RPM", "Records the reviewed maximum spindle speed.", "Spindle → Direct RPM", fact="max_spindle_rpm"),
    d("coolant_flood", "Flood Coolant", "Coolant", "Coolant Codes", "Records flood-coolant on behavior when available.", "Machine Codes → Coolant", structured="code_table"),
    d("coolant_off", "Coolant Off", "Coolant", "Coolant Codes", "Records coolant-off behavior when available.", "Machine Codes → Coolant", structured="code_table"),
    d("feed_upm", "Feed Per Minute (UPM)", "Feedrates", "UPM", "Records feed-per-minute output behavior.", "Feedrates → UPM", fact="feed_mode"),
    d("feed_upr", "Feed Per Revolution (UPR)", "Feedrates", "UPR", "Records feed-per-revolution behavior; unavailable remains Not Available rather than zero.", "Feedrates → UPR", "conditional", families=("lathe",), structured="code_table"),
    d("operator_messages", "Operator Messages", "Operator Messages", "INSERT", "Records how operator messages are emitted.", "Operator Messages → INSERT", "conditional"),
    d("multax", "MULTAX Motion", "Advanced / Custom", "MULTAX", "Records multi-axis motion behavior for machines with rotary capability.", "Motion → Cycles → MULTAX", "advanced", axes=4),
    d("five_axis_comp", "5-Axis Cutter Compensation", "Advanced / Custom", "Cutter Compensation", "Records five-axis cutter compensation when machine capability requires it.", "Machine Codes → Cutter Comp → 5 Axis", "advanced", families=("mill",), axes=5),
    d("right_angle_head", "Right-Angle Head", "Advanced / Custom", "Right Angle Head", "Records right-angle-head transforms only when explicitly selected.", "Transforms & Output → Right Angle Head", "advanced", families=("mill",)),
    d("controller_specific_cycles", "Controller-Specific Advanced Cycles", "Advanced / Custom", "Cycles", "Records Siemens or UG-specific cycle behavior only when explicitly selected.", "Motion → Cycles → Siemens / UG", "advanced", controller=("siemens", "ug")),
    d("custom_fil", "Custom FIL / CIMFIL Reference", "Advanced / Custom", "FIL", "Tracks custom logic references; it does not create native FIL logic.", "Advanced → FIL", "advanced", path_status="site_verification_needed"),
)

DEFINITION_BY_KEY = {item.key: item for item in DEFINITIONS}


def machine_family(machine_type: str | None) -> str:
    value = (machine_type or "").lower().replace("-", "_").replace(" ", "_")
    if any(token in value for token in ("lathe", "turn", "slant_bed")):
        return "lathe"
    if any(token in value for token in ("mill", "machining", "router")):
        return "mill"
    return "other"


def evaluate_relevance(definition: OFGSettingDefinition, *, machine_type: str | None, axis_count: int | None,
                       controller: str | None = None,
                       capabilities: dict[str, Any] | None = None, user_selected: bool = False) -> dict[str, Any]:
    """Return one stable relevance decision for API, progress, exports, and UI."""
    family = machine_family(machine_type)
    axes = axis_count or 0
    family_match = family in definition.machine_families
    axes_match = not definition.minimum_axes or axes >= definition.minimum_axes
    controller_value = (controller or "").lower()
    controller_match = not definition.controller_tokens or any(token in controller_value for token in definition.controller_tokens)
    capability_key = definition.key
    capability_match = not capabilities or capabilities.get(capability_key, True) is not False
    applicable = bool(user_selected or (family_match and axes_match and controller_match and capability_match))
    if definition.relevance == "advanced":
        label = "advanced" if applicable or user_selected else "not_applicable"
    elif not applicable:
        label = "not_applicable"
    elif definition.relevance == "conditional":
        label = "applicable"
    else:
        label = "required_for_post"
    return {"relevance_class": definition.relevance, "relevance_label": label, "is_applicable": applicable}


def applicable_for_progress(setting: Any) -> bool:
    advanced_selected = getattr(setting, "relevance_class", "core") != "advanced" or getattr(setting, "user_selected", False)
    return bool(setting.is_applicable and setting.status != "not_applicable" and advanced_selected)

"""Central governance boundary for every external AI request."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

CL_NCL_EXTERNAL_AI_ALLOWED = False
PART_SPECIFIC_EXTERNAL_AI_ALLOWED = False
PART_GEOMETRY_EXTERNAL_AI_ALLOWED = False

SENSITIVE_FIELD_FRAGMENTS = {
    "cl_text", "cl_source", "ncl_text", "ncl_source", "toolpath", "part_geometry",
    "feature_geometry", "part_coordinates", "fixture_geometry", "production_gcode",
    "production_toolpath", "part_identifier", "program_identifier", "machining_sequence",
    "translation_example", "gcode_excerpt", "cl_excerpt", "apt_source",
    "production_program", "program_gcode", "cad_model", "cad_geometry",
    "step_geometry", "iges_geometry", "creo_part", "customer_design",
    "proprietary_print", "geometric_feature_data", "vericut_project",
    "vericut_geometry", "part_specific_diagnostic", "sensitive_listing",
    "test_program_content", "part_specific_nc",
}
CL_NCL_MARKERS = re.compile(r"(?i)(?:\b(?:CL|NCL)\b|\bGOTO\s*/|\bFROM\s*/|\bLOADTL\s*/|\bFEDRAT\s*/|\bSPINDL\s*/|\bPPRINT\s*/|\bCYCLE\s*/)")
CAD_GEOMETRY_MARKERS = re.compile(r"(?i)(?:ISO-10303-21|\bIGES\s+(?:entity|geometry)|\bSTEP\s+geometry|Creo\s+part\s+geometry|\.(?:step|stp|iges|igs)\b)")


class AIGovernanceViolation(Exception):
    def __init__(self, code: str, message: str, field: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


def _walk(value: object, path: str = "request"):
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield str(key).lower(), child, child_path
            yield from _walk(child, child_path)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def enforce_post_builder_ai_policy(payload: Mapping[str, object]) -> None:
    """Reject part-specific or CL/NCL content before any provider can be selected."""
    for key, value, path in _walk(payload):
        if any(fragment in key for fragment in SENSITIVE_FIELD_FRAGMENTS):
            code = "AI_CL_NCL_TRANSMISSION_PROHIBITED" if "cl_" in key or "ncl_" in key or "translation_example" in key else "AI_PART_SPECIFIC_DATA_PROHIBITED"
            raise AIGovernanceViolation(code, "CL/NCL and part-specific machining data are prohibited from external AI context.", path)
        if isinstance(value, str) and CL_NCL_MARKERS.search(value):
            raise AIGovernanceViolation("AI_CL_NCL_TRANSMISSION_PROHIBITED", "CL/NCL content is prohibited from external AI context.", path)
        if isinstance(value, str) and CAD_GEOMETRY_MARKERS.search(value):
            raise AIGovernanceViolation("AI_PART_SPECIFIC_DATA_PROHIBITED", "CAD and part geometry are prohibited from external AI context.", path)


def prohibit_translation_ai() -> None:
    raise AIGovernanceViolation(
        "AI_CL_NCL_TRANSMISSION_PROHIBITED",
        "The legacy CL/NCL-to-AI workflow is retired. CL/NCL cannot be sent to any external AI provider.",
    )

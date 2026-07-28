from dataclasses import dataclass
from typing import Protocol

from app.cl_parser.models import ParsedCLRecord
from app.parsers.gcode import ParsedGCodeBlock


@dataclass(slots=True)
class AlignmentExplanation:
    explanation: str
    advisory_only: bool = True
    alignment_is_inferred: bool = True
    manual_review_required: bool = True


class AlignmentExplanationProvider(Protocol):
    def explain_alignment(
        self,
        cl_records: list[ParsedCLRecord],
        gcode_blocks: list[ParsedGCodeBlock],
        deterministic_reasons: list[str],
        machine_context: dict,
    ) -> AlignmentExplanation: ...


class MockAlignmentExplanationProvider:
    """Plain-language rendering only; it cannot create or rescore a mapping."""

    def explain_alignment(
        self,
        cl_records: list[ParsedCLRecord],
        gcode_blocks: list[ParsedGCodeBlock],
        deterministic_reasons: list[str],
        machine_context: dict,
    ) -> AlignmentExplanation:
        reasons = "; ".join(deterministic_reasons) or "No deterministic reason was supplied"
        return AlignmentExplanation(
            f"The proposed relationship is based on these deterministic observations: "
            f"{reasons}. The mapping remains inferred and requires qualified review."
        )

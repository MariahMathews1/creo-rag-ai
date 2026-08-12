import json
import re
from dataclasses import dataclass

from app.models.entities import MachineProfile
from app.models.translation import TranslationExample

TRANSLATION_EXPLANATION_PROMPT_VERSION = "translation-explanation-v1"
TRANSLATION_AI_RESPONSE_SCHEMA_VERSION = "translation-ai-response-v1"


@dataclass(frozen=True)
class PromptPackage:
    system: str
    user: str
    example_ids: list[int]


class TranslationPromptBuilder:
    def build(self, *, machine: MachineProfile, revision_id: int | None, cl_text: str, examples: list[TranslationExample]) -> PromptPackage:
        verified = []
        for row in examples:
            cl_excerpt, gcode_excerpt = self._aligned_excerpt(row, cl_text)
            verified.append({
                "example_id": row.id,
                "machine_profile_id": row.machine_profile_id,
                "post_processor_name": row.post_processor_name,
                "post_processor_revision": row.post_processor_revision,
                "operation_type": row.operation_type,
                "cl_excerpt": cl_excerpt,
                "gcode_excerpt": gcode_excerpt,
                "alignment_coverage": (row.alignments[-1].summary_json if row.alignments else {}).get("coverage_percent", 0),
            })
        machine_context = {
            "machine_profile_id": machine.id, "name": machine.name,
            "machine_type": machine.machine_type.value, "controller": machine.controller_name,
            "profile_revision_id": revision_id, "axis_count": machine.axis_count,
            "known_limits": {"x": [machine.x_min, machine.x_max], "y": [machine.y_min, machine.y_max], "z": [machine.z_min, machine.z_max]},
        }
        system = (
            "You are an R&D-only CNC translation interpretation assistant. Explain observed mappings from supplied verified examples only. "
            "Preserve unknown or unsupported input instead of inventing behavior. Do not claim production readiness, omit uncertainty, "
            "provide a full executable program, use public-web knowledge, or expose hidden reasoning. Return only the requested structured fields."
        )
        user = "\n\n".join([
            "MACHINE_CONTEXT\n" + json.dumps(machine_context, sort_keys=True),
            "VERIFIED_EXAMPLES\n" + json.dumps(verified, sort_keys=True),
            "NEW_CL_INPUT\n" + cl_text[:20_000],
            "OUTPUT_CONTRACT\nReturn status, input_cl, interpreted_operation, suggested_mapping_pattern, short_rationale, example_ids, uncertainties, unsupported_features, and warnings. Never return executable full-program G-code.",
        ])
        return PromptPackage(system=system, user=user, example_ids=[row.id for row in examples])

    @staticmethod
    def _excerpt(text: str) -> str:
        return "\n".join(line for line in text.splitlines() if line.strip())[:1_200]

    def _aligned_excerpt(self, row: TranslationExample, input_cl: str) -> tuple[str, str]:
        commands = {match.group(1).upper() for match in re.finditer(r"(?m)^\s*([A-Z][A-Z0-9_]*)\s*(?:/|$)", input_cl.upper())}
        cl_rows = row.parsed_cl_records_json or []
        gc_rows = row.parsed_gcode_blocks_json or []
        cl_indexes = {index for index, item in enumerate(cl_rows) if str(item.get("command") or "").upper() in commands}
        gc_indexes: set[int] = set()
        alignment = row.alignments[-1] if row.alignments else None
        if alignment:
            for link in alignment.links:
                if link.review_status not in {"confirmed", "edited"} or link.cl_record_start is None or link.gcode_block_start is None:
                    continue
                cl_span = set(range(link.cl_record_start, (link.cl_record_end if link.cl_record_end is not None else link.cl_record_start) + 1))
                if cl_span & cl_indexes:
                    gc_indexes.update(range(link.gcode_block_start, (link.gcode_block_end if link.gcode_block_end is not None else link.gcode_block_start) + 1))
        cl_values = [str(cl_rows[index].get("text") or "") for index in sorted(cl_indexes) if index < len(cl_rows)]
        gc_values = [str(gc_rows[index].get("text") or "") for index in sorted(gc_indexes) if index < len(gc_rows)]
        return ("\n".join(cl_values)[:1_200] or self._excerpt(row.cl_source_text), "\n".join(gc_values)[:1_200] or self._excerpt(row.gcode_source_text))

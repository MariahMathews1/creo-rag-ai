"""Explicit Post Builder export boundary.

Current exporters are research/review artifacts. A proprietary site G-POST
exporter can implement this contract later without changing draft governance.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json

from app.gpost.service import SAFETY_NOTICE, markdown_export, snapshot_draft
from app.models.gpost import GPostDraft, GPostMapping, PostSectionDraft


@dataclass(frozen=True)
class PostDraftExport:
    content: str
    media_type: str
    extension: str


class PostDraftExporter(ABC):
    @abstractmethod
    def export(self, draft: GPostDraft, mappings: list[GPostMapping], sections: list[PostSectionDraft] | None = None) -> PostDraftExport: ...


def section_payload(section: PostSectionDraft) -> dict:
    return {
        "section_key": section.section_key,
        "section_version": section.section_version,
        "status": section.status,
        "source_type": section.source_type,
        "draft_templates": section.draft_templates_json,
        "missing_information": section.missing_information_json,
        "assumptions": section.assumptions_json,
        "warnings": section.warnings_json,
        "source_evidence": section.source_evidence_json,
        "provider": section.provider,
        "rules": [{
            "rule_key": rule.rule_key,
            "name": rule.name,
            "condition": rule.condition,
            "output_behavior": rule.output_behavior,
            "ai_draft_template": rule.ai_draft_template,
            "engineer_template": rule.engineer_template,
            "evidence_ids": rule.evidence_ids_json,
            "status": rule.status,
            "review_reason": rule.review_reason,
            "reviewer_label": rule.reviewer_label,
            "reviewed_at": rule.reviewed_at,
        } for rule in section.rules],
    }


class JSONResearchExporter(PostDraftExporter):
    def export(self, draft: GPostDraft, mappings: list[GPostMapping], sections: list[PostSectionDraft] | None = None) -> PostDraftExport:
        payload = snapshot_draft(draft, mappings)
        payload.update({
            "machine_profile_snapshot": draft.machine_profile_snapshot_json,
            "capability_snapshot": draft.capability_snapshot_json,
            "unsupported_features": draft.unsupported_features_json,
            "safety_notice": SAFETY_NOTICE,
            "labels": ["R&D ONLY", "NON-PRODUCTION", "NOT VALIDATED FOR MACHINE USE"],
            "post_sections": [section_payload(section) for section in sections or []],
        })
        return PostDraftExport(json.dumps(payload, indent=2, default=str), "application/json", "json")


class MarkdownReviewExporter(PostDraftExporter):
    def export(self, draft: GPostDraft, mappings: list[GPostMapping], sections: list[PostSectionDraft] | None = None) -> PostDraftExport:
        content = markdown_export(draft, mappings)
        if sections:
            content += "\n\n## AI-assisted post sections\n"
            for section in sections:
                content += f"\n### {section.section_key} — draft {section.section_version} ({section.status})\n"
                content += f"\nEvidence sources: {len(section.source_evidence_json)}; assumptions: {len(section.assumptions_json)}; warnings: {len(section.warnings_json)}.\n"
                for rule in section.rules:
                    template = rule.engineer_template or rule.ai_draft_template or rule.output_behavior
                    content += f"\n- **{rule.name}** — `{rule.status}` — `{template}`"
                    if rule.reviewer_label:
                        content += f" — reviewer: {rule.reviewer_label}"
                    content += "\n"
        return PostDraftExport(content, "text/markdown", "md")


def get_post_draft_exporter(format_name: str) -> PostDraftExporter:
    return MarkdownReviewExporter() if format_name == "markdown" else JSONResearchExporter()

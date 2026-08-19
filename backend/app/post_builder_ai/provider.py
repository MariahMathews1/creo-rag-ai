import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.ai.governance import enforce_post_builder_ai_policy
from app.core.config import Settings, get_settings
from app.schemas.post_builder_ai import PostBuilderRequest
from app.translation_ai.provider import AzureOpenAITranslationProvider, TranslationAIError

POST_BUILDER_PROMPT_VERSION = "post-section-draft-v2"
POST_BUILDER_RESPONSE_VERSION = "post-section-draft-response-v2"


@dataclass
class PostBuilderProviderResult:
    payload: dict
    provider_metadata: dict
    token_usage: dict = field(default_factory=dict)


class PostBuilderAIProvider(ABC):
    name: str
    external_processing: bool

    @abstractmethod
    def health_check(self) -> dict: ...

    @abstractmethod
    def draft_post_section(self, request: PostBuilderRequest, machine_context: dict) -> PostBuilderProviderResult: ...

    def analyze_machine_knowledge(self, request: PostBuilderRequest, machine_context: dict) -> PostBuilderProviderResult:
        return self.draft_post_section(request, machine_context)

    def suggest_post_structure(self, request: PostBuilderRequest, machine_context: dict) -> PostBuilderProviderResult:
        return self.draft_post_section(request, machine_context)

    def explain_post_rule(self, request: PostBuilderRequest, machine_context: dict) -> PostBuilderProviderResult:
        return self.draft_post_section(request, machine_context)

    def compare_post_rule(self, request: PostBuilderRequest, machine_context: dict) -> PostBuilderProviderResult:
        return self.draft_post_section(request, machine_context)

    def identify_missing_post_information(self, request: PostBuilderRequest, machine_context: dict) -> PostBuilderProviderResult:
        return self.draft_post_section(request, machine_context)

    def suggest_post_revision_change(self, request: PostBuilderRequest, machine_context: dict) -> PostBuilderProviderResult:
        return self.draft_post_section(request, machine_context)


class DisabledPostBuilderProvider(PostBuilderAIProvider):
    name = "disabled"
    external_processing = False

    def health_check(self) -> dict:
        return {"configured": False, "reachable": False, "authentication_mode": None, "deployment": None, "model": None}

    def draft_post_section(self, request: PostBuilderRequest, machine_context: dict) -> PostBuilderProviderResult:
        raise TranslationAIError("AI_PROVIDER_DISABLED", "Post Builder AI provider is disabled.")


def _mock_rules(section: str, context: dict, evidence_ids: list[int]) -> tuple[list[dict], list[str]]:
    templates = context.get("templates", {})
    definitions = {
        "program_structure": [("safe_start", "Safe Program Start", "program initialization", "safe_start"), ("program_header", "Program Header", "program begins", "program_header")],
        "tooling": [("tool_selection", "Tool Selection", "tool station requested", "tool_selection"), ("tool_change", "Tool Change", "selected tool activated", "tool_change")],
        "spindle": [("spindle_clockwise_start", "Clockwise Spindle Start", "spindle requested clockwise", "spindle_start_cw"), ("spindle_counterclockwise_start", "Counter-clockwise Spindle Start", "spindle requested counter-clockwise", "spindle_start_ccw"), ("spindle_stop", "Spindle Stop", "spindle stop requested", "spindle_stop")],
        "coolant": [("coolant_on", "Flood Coolant On", "flood coolant requested", "coolant_on"), ("coolant_off", "Coolant Off", "coolant stop requested", "coolant_off")],
        "feed": [("feed_mode", "Feed Mode", "feed mode initialization", "feed_mode"), ("feed_format", "Feed Formatting", "feed value requested", "feed_rate")],
        "motion": [("rapid_motion", "Rapid Motion", "machine-level rapid move formatting", "rapid_move"), ("linear_motion", "Linear Motion", "machine-level linear move formatting", "linear_feed_move"), ("arc_cw", "Clockwise Arc", "clockwise arc formatting", "arc_cw"), ("arc_ccw", "Counter-clockwise Arc", "counter-clockwise arc formatting", "arc_ccw")],
        "coordinates": [("work_offset", "Work Offset", "work coordinate initialization", "work_offset"), ("distance_mode", "Distance Mode", "coordinate mode initialization", "distance_mode"), ("reference_return", "Reference Return", "machine reference return requested", "reference_return")],
        "program_end": [("spindle_stop", "End Spindle Stop", "program completion", "spindle_stop"), ("coolant_off", "End Coolant Off", "program completion", "coolant_off"), ("program_end", "Program End", "program completion", "program_end")],
    }
    rules, missing = [], []
    for key, name, condition, template_key in definitions.get(section, []):
        output = templates.get(template_key)
        if output:
            rules.append({"rule_key": key, "name": name, "condition": condition, "output_behavior": output, "evidence_reference_ids": evidence_ids, "review_status": "draft"})
        else:
            missing.append(f"{name} convention")
    if not rules and not missing: missing = [f"Reviewed machine-level {section.replace('_', ' ')} behavior"]
    return rules, missing


class MockPostBuilderProvider(PostBuilderAIProvider):
    name = "mock"
    external_processing = False

    def health_check(self) -> dict:
        return {"configured": True, "reachable": True, "authentication_mode": "none", "deployment": "local-deterministic-fixture", "model": "mock-post-builder-v1"}

    def draft_post_section(self, request: PostBuilderRequest, machine_context: dict) -> PostBuilderProviderResult:
        policy_payload = {"request": request.model_dump(), "machine_context": machine_context}
        enforce_post_builder_ai_policy(policy_payload)
        evidence_ids = [item.document_id for item in request.relevant_document_excerpts]
        rules, missing = _mock_rules(request.selected_post_section, machine_context, evidence_ids)
        return PostBuilderProviderResult(payload={
            "section_key": request.selected_post_section,
            "status": "draft" if rules else "needs_machine_information",
            "draft_rules": rules, "draft_templates": [], "missing_information": missing,
            "assumptions": ["Mock output uses only the supplied machine-level context."],
            "source_reference_ids": evidence_ids,
            "warnings": ["Mock provider output remains a draft until explicit engineer review."],
        }, provider_metadata={"provider": self.name, "model": "mock-post-builder-v1"})


class AzureOpenAIPostBuilderProvider(PostBuilderAIProvider):
    name = "azure_openai"
    external_processing = True

    def __init__(self, settings: Settings):
        self.settings = settings
        self.azure_transport = AzureOpenAITranslationProvider(settings)

    def health_check(self) -> dict:
        return self.azure_transport.health_check()

    def draft_post_section(self, request: PostBuilderRequest, machine_context: dict) -> PostBuilderProviderResult:
        outbound = {"machine_context": machine_context, "selected_post_section": request.selected_post_section,
                    "existing_reviewed_rules": request.existing_reviewed_rules,
                    "relevant_document_excerpts": [item.model_dump() for item in request.relevant_document_excerpts]}
        enforce_post_builder_ai_policy(outbound)
        schema = {
            "type": "object", "additionalProperties": False,
            "required": ["section_key", "status", "draft_rules", "draft_templates", "missing_information", "assumptions", "source_reference_ids", "warnings"],
            "properties": {
                "section_key": {"type": "string"}, "status": {"type": "string", "enum": ["draft", "needs_machine_information"]},
                "draft_rules": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["rule_key", "name", "condition", "output_behavior", "evidence_reference_ids", "review_status"], "properties": {"rule_key": {"type": "string"}, "name": {"type": "string"}, "condition": {"type": "string"}, "output_behavior": {"type": "string"}, "evidence_reference_ids": {"type": "array", "items": {"type": "integer"}}, "review_status": {"type": "string", "enum": ["draft"]}}}},
                "draft_templates": {"type": "array", "items": {"type": "object"}}, "missing_information": {"type": "array", "items": {"type": "string"}},
                "assumptions": {"type": "array", "items": {"type": "string"}}, "source_reference_ids": {"type": "array", "items": {"type": "integer"}}, "warnings": {"type": "array", "items": {"type": "string"}},
            },
        }
        instructions = "Generate advisory machine-level post configuration assistance only. Never request or infer CL/NCL, part geometry, toolpaths, or production G-code. Identify missing machine facts, cite only supplied evidence IDs, label assumptions, and keep every rule in draft status for engineer review."
        try:
            response = self.azure_transport._client().responses.create(model=self.settings.azure_openai_deployment, instructions=instructions,
                input=json.dumps(outbound, sort_keys=True), text={"format": {"type": "json_schema", "name": "post_builder_section", "strict": True, "schema": schema}}, store=False)
            payload = json.loads(response.output_text)
            allowed_ids = {item.document_id for item in request.relevant_document_excerpts}
            if set(payload.get("source_reference_ids", [])) - allowed_ids:
                raise TranslationAIError("PROVIDER_INVALID_RESPONSE", "Provider returned an unapproved evidence identifier.")
            usage = getattr(response, "usage", None)
            return PostBuilderProviderResult(payload=payload, provider_metadata={"provider": self.name, "deployment": self.settings.azure_openai_deployment, "model": self.settings.azure_openai_model or self.settings.azure_openai_deployment, "response_id": getattr(response, "id", None)}, token_usage=usage.model_dump() if hasattr(usage, "model_dump") else {})
        except TranslationAIError:
            raise
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            raise TranslationAIError("PROVIDER_INVALID_RESPONSE", "Azure OpenAI returned an invalid structured response.") from exc
        except Exception as exc:
            raise self.azure_transport._safe_error(exc) from exc


def get_post_builder_provider(settings: Settings | None = None) -> PostBuilderAIProvider:
    settings = settings or get_settings()
    mode = settings.post_builder_ai_provider.lower().strip()
    if mode == "azure_openai":
        return AzureOpenAIPostBuilderProvider(settings)
    if mode == "mock":
        return MockPostBuilderProvider()
    return DisabledPostBuilderProvider()

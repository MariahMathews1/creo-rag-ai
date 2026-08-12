from dataclasses import dataclass

from app.models.translation import TranslationExample


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason_code: str
    explanation: str


class AIProcessingPolicy:
    """Single enforcement point for external translation-AI processing."""

    allowed_modes = {"mock", "azure_openai"}

    def provider_allowed(self, mode: str) -> PolicyDecision:
        if mode not in self.allowed_modes:
            return PolicyDecision(False, "AI_PROVIDER_DISABLED", "Translation AI provider is disabled.")
        return PolicyDecision(True, "PROVIDER_ALLOWED", "Configured translation provider may be invoked by explicit request.")

    def example_allowed(self, example: TranslationExample, machine_profile_id: int, *, allow_machine_family_fallback: bool = False, controller_name: str | None = None) -> PolicyDecision:
        if example.machine_profile_id != machine_profile_id:
            if not allow_machine_family_fallback:
                return PolicyDecision(False, "CROSS_MACHINE_CONTEXT_BLOCKED", "Example belongs to a different machine and fallback was not explicitly allowed.")
            if not controller_name or example.controller_name != controller_name:
                return PolicyDecision(False, "MACHINE_FAMILY_CONTEXT_BLOCKED", "Cross-machine fallback requires the same explicitly selected controller.")
        if example.verification_status != "verified_successful":
            return PolicyDecision(False, "EXAMPLE_NOT_VERIFIED", "Only verified-successful examples are eligible.")
        if not example.ai_processing_allowed:
            return PolicyDecision(False, "AI_PROCESSING_NOT_ALLOWED", "Example has no external AI-processing consent.")
        return PolicyDecision(True, "EXAMPLE_ALLOWED", "Verified, machine-scoped, and explicitly consented example.")

    def require_examples(self, examples: list[TranslationExample], machine_profile_id: int, *, allow_machine_family_fallback: bool = False, controller_name: str | None = None) -> PolicyDecision:
        if not examples:
            return PolicyDecision(False, "AI_CONTEXT_NOT_AVAILABLE", "No eligible verified examples were selected.")
        for example in examples:
            decision = self.example_allowed(example, machine_profile_id, allow_machine_family_fallback=allow_machine_family_fallback, controller_name=controller_name)
            if not decision.allowed:
                return decision
        return PolicyDecision(True, "AI_CONTEXT_ALLOWED", "All selected examples satisfy processing policy.")

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings, get_settings
from app.ai.governance import prohibit_translation_ai
from app.translation_ai.prompt import PromptPackage


class TranslationAIError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.retryable = retryable


@dataclass
class ProviderResult:
    payload: dict
    provider_metadata: dict
    token_usage: dict = field(default_factory=dict)


class TranslationAIProvider(ABC):
    name: str
    external_processing: bool

    @abstractmethod
    def health_check(self) -> dict: ...

    @abstractmethod
    def explain_translation(self, prompt: PromptPackage, input_cl: str) -> ProviderResult: ...

    def translate_segment(self, *_args, **_kwargs):
        raise TranslationAIError("TRANSLATION_NOT_ENABLED", "Executable translation is not enabled in Phase 10.")

    def compare_candidate(self, *_args, **_kwargs):
        raise TranslationAIError("CANDIDATE_COMPARISON_NOT_ENABLED", "AI candidate comparison is not enabled in Phase 10.")


class DisabledTranslationProvider(TranslationAIProvider):
    name = "disabled"
    external_processing = False

    def health_check(self) -> dict:
        return {"configured": False, "reachable": False, "authentication_mode": None, "deployment": None, "model": None}

    def explain_translation(self, prompt: PromptPackage, input_cl: str) -> ProviderResult:
        prohibit_translation_ai()


class MockTranslationProvider(TranslationAIProvider):
    name = "mock"
    external_processing = False

    def health_check(self) -> dict:
        return {"configured": True, "reachable": True, "authentication_mode": "none", "deployment": "local-deterministic-fixture", "model": "mock-translation-v1"}

    def explain_translation(self, prompt: PromptPackage, input_cl: str) -> ProviderResult:
        prohibit_translation_ai()


class AzureOpenAITranslationProvider(TranslationAIProvider):
    name = "azure_openai"
    external_processing = True

    def __init__(self, settings: Settings):
        self.settings = settings

    def _client(self):
        if not self.settings.azure_openai_endpoint or not self.settings.azure_openai_deployment:
            raise TranslationAIError("PROVIDER_NOT_CONFIGURED", "Azure OpenAI endpoint and deployment are required.")
        try:
            from openai import OpenAI
            if self.settings.azure_openai_auth_mode == "api_key":
                if not self.settings.azure_openai_api_key:
                    raise TranslationAIError("PROVIDER_NOT_CONFIGURED", "Azure OpenAI API-key authentication is not configured.")
                credential: Any = self.settings.azure_openai_api_key
            else:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider
                credential = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
            return OpenAI(
                base_url=self.settings.azure_openai_endpoint.rstrip("/") + "/openai/v1/",
                api_key=credential, timeout=self.settings.translation_ai_timeout_seconds,
                max_retries=self.settings.translation_ai_max_retries,
            )
        except TranslationAIError:
            raise
        except ImportError as exc:
            raise TranslationAIError("PROVIDER_SDK_UNAVAILABLE", "Azure provider dependencies are not installed.") from exc
        except Exception as exc:
            raise self._safe_error(exc) from exc

    @staticmethod
    def _safe_error(exc: Exception) -> TranslationAIError:
        name = type(exc).__name__.lower(); status = getattr(exc, "status_code", None)
        if status in {401, 403} or "authentication" in name: return TranslationAIError("PROVIDER_AUTHENTICATION_FAILED", "Azure OpenAI authentication failed.")
        if status == 429 or "ratelimit" in name: return TranslationAIError("PROVIDER_RATE_LIMITED", "Azure OpenAI rate limit was reached.", retryable=True)
        if "timeout" in name: return TranslationAIError("PROVIDER_TIMEOUT", "Azure OpenAI request timed out.", retryable=True)
        if status and status >= 500: return TranslationAIError("PROVIDER_UNAVAILABLE", "Azure OpenAI is temporarily unavailable.", retryable=True)
        if "contentfilter" in name or "content_filter" in str(getattr(exc, "code", "")): return TranslationAIError("PROVIDER_CONTENT_FILTERED", "Azure content filtering prevented a response.")
        return TranslationAIError("PROVIDER_REQUEST_FAILED", "Azure OpenAI request failed.")

    def health_check(self) -> dict:
        try:
            self._client().models.retrieve(self.settings.azure_openai_deployment)
            return {"configured": True, "reachable": True, "authentication_mode": self.settings.azure_openai_auth_mode, "deployment": self.settings.azure_openai_deployment, "model": self.settings.azure_openai_model or None}
        except TranslationAIError as exc:
            configured = bool(self.settings.azure_openai_endpoint and self.settings.azure_openai_deployment)
            return {"configured": configured, "reachable": False, "authentication_mode": self.settings.azure_openai_auth_mode, "deployment": self.settings.azure_openai_deployment or None, "model": self.settings.azure_openai_model or None, "error_code": exc.code}

    def explain_translation(self, prompt: PromptPackage, input_cl: str) -> ProviderResult:
        prohibit_translation_ai()
        schema = {
            "type": "object", "additionalProperties": False,
            "required": ["status", "input_cl", "interpreted_operation", "suggested_mapping_pattern", "short_rationale", "example_ids", "uncertainties", "unsupported_features", "warnings"],
            "properties": {
                "status": {"type": "string"}, "input_cl": {"type": "string"},
                "interpreted_operation": {"type": ["string", "null"]}, "suggested_mapping_pattern": {"type": ["string", "null"]},
                "short_rationale": {"type": "string"}, "example_ids": {"type": "array", "items": {"type": "integer"}},
                "uncertainties": {"type": "array", "items": {"type": "string"}}, "unsupported_features": {"type": "array", "items": {"type": "string"}},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
        }
        try:
            response = self._client().responses.create(
                model=self.settings.azure_openai_deployment,
                instructions=prompt.system, input=prompt.user,
                text={"format": {"type": "json_schema", "name": "translation_explanation", "strict": True, "schema": schema}},
                store=False,
            )
            provider_error = getattr(response, "error", None)
            incomplete = getattr(response, "incomplete_details", None)
            response_code = str(getattr(provider_error, "code", "") or getattr(incomplete, "reason", ""))
            if "content_filter" in response_code:
                raise TranslationAIError("PROVIDER_CONTENT_FILTERED", "Azure content filtering prevented a response.")
            if provider_error:
                raise TranslationAIError("PROVIDER_REQUEST_FAILED", "Azure OpenAI returned a failed response.")
            payload = json.loads(response.output_text)
            if set(payload.get("example_ids", [])) - set(prompt.example_ids):
                raise TranslationAIError("PROVIDER_INVALID_RESPONSE", "Provider returned unapproved example identifiers.")
            usage = getattr(response, "usage", None)
            usage_data = usage.model_dump() if hasattr(usage, "model_dump") else {}
            return ProviderResult(payload=payload, provider_metadata={"provider": self.name, "deployment": self.settings.azure_openai_deployment, "model": self.settings.azure_openai_model or self.settings.azure_openai_deployment, "response_id": getattr(response, "id", None)}, token_usage=usage_data)
        except TranslationAIError:
            raise
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            raise TranslationAIError("PROVIDER_INVALID_RESPONSE", "Azure OpenAI returned an invalid structured response.") from exc
        except Exception as exc:
            raise self._safe_error(exc) from exc


def get_translation_provider(settings: Settings | None = None) -> TranslationAIProvider:
    settings = settings or get_settings()
    mode = settings.translation_ai_provider.lower().strip()
    if mode == "azure_openai": return AzureOpenAITranslationProvider(settings)
    if mode == "mock": return MockTranslationProvider()
    return DisabledTranslationProvider()

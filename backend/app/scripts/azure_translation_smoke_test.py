"""Optional synthetic Azure connectivity test. Never loads repository programs."""
import sys

from app.core.config import get_settings
from app.translation_ai.prompt import PromptPackage
from app.translation_ai.provider import AzureOpenAITranslationProvider, TranslationAIError


def main() -> int:
    settings = get_settings()
    if settings.translation_ai_provider != "azure_openai":
        print("SKIPPED: TRANSLATION_AI_PROVIDER is not azure_openai")
        return 0
    provider = AzureOpenAITranslationProvider(settings)
    status = provider.health_check()
    print({key: value for key, value in status.items() if key != "endpoint"})
    if not status.get("reachable"):
        print("FAILED: provider is not reachable")
        return 1
    prompt = PromptPackage(
        system="R&D synthetic translation-pattern explanation only. Return structured output; no executable program.",
        user='VERIFIED_EXAMPLES\n[{"example_id":1,"cl_excerpt":"SPINDL / RPM,800,CLW","gcode_excerpt":"S800 M03"},{"example_id":2,"cl_excerpt":"SPINDL / RPM,1500,CLW","gcode_excerpt":"S1500 M03"}]\nNEW_CL_INPUT\nSPINDL / RPM,1200,CLW',
        example_ids=[1, 2],
    )
    try:
        result = provider.explain_translation(prompt, "SPINDL / RPM,1200,CLW")
        print({"success": True, "status": result.payload.get("status"), "pattern": result.payload.get("suggested_mapping_pattern"), "example_ids": result.payload.get("example_ids")})
        return 0
    except TranslationAIError as exc:
        print({"success": False, "error_code": exc.code, "message": exc.safe_message})
        return 1


if __name__ == "__main__":
    sys.exit(main())

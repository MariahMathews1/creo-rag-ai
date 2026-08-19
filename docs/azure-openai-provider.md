# Historical Azure OpenAI translation provider (retired direction)

> This document records the previous Phase 10 experiment. The translation provider can no longer be invoked: every CL/NCL explanation/translation path is rejected by centralized policy with `AI_CL_NCL_TRANSMISSION_PROHIBITED`. Current Azure work is limited to machine-level Post Builder assistance; see [the current plan](azure-openai-integration-plan.md).

Phase 10 adds a dedicated `TranslationAIProvider` boundary. It is intentionally separate from the Manual Assistant provider and supports `disabled`, `mock`, and `azure_openai` modes. `mock` is the default and makes no network calls.

## Authentication and client

The Azure implementation uses the official Python `openai` SDK against the Azure OpenAI v1 base URL:

`https://<resource>.openai.azure.com/openai/v1/`

Preferred authentication is Microsoft Entra ID through `DefaultAzureCredential` and `get_bearer_token_provider` with the `https://cognitiveservices.azure.com/.default` scope. This permits local developer identity, workload identity, Azure CLI identity, or managed identity according to the normal credential chain. `AZURE_OPENAI_API_KEY` is an explicit fallback when `AZURE_OPENAI_AUTH_MODE=api_key`.

Required Azure configuration:

- `TRANSLATION_AI_PROVIDER=azure_openai`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_AUTH_MODE=entra_id|api_key`
- optionally `AZURE_OPENAI_MODEL` for safe display metadata

Credentials remain server-side environment values. They are not logged, persisted, returned by provider-status APIs, or bundled into the frontend.

## Provider behavior

The first external operation is explanation only. The provider uses the Responses API with a strict JSON schema and `store=false`. It cannot produce or approve a full executable CNC program through this milestone. The endpoint never enables public-web tools.

The provider receives:

- a minimized machine context;
- explicitly selected, verified-successful and consented translation excerpts;
- the new user-entered CL segment;
- a versioned safety instruction and response contract.

Manuals, unrelated programs, credentials, local paths, raw database rows, and unapproved examples are not included.

## Errors and retries

The provider converts Azure/SDK failures into redacted application codes:

- `PROVIDER_AUTHENTICATION_FAILED`
- `PROVIDER_TIMEOUT`
- `PROVIDER_RATE_LIMITED`
- `PROVIDER_UNAVAILABLE`
- `PROVIDER_CONTENT_FILTERED`
- `PROVIDER_INVALID_RESPONSE`
- `PROVIDER_REQUEST_FAILED`

Only the SDK's conservative transient retry behavior is configured. Policy blocks and invalid requests are never retried. Raw exception text is not returned to the frontend.

## Health and audit

`GET /api/ai/translation/provider-status` is metadata-only and does not contact Azure. An explicit `?check_reachability=true` performs the health probe. AI invocations store hashes, selected example IDs, prompt/schema versions, safe provider metadata, status, duration, and optional usage—not prompts, credentials, or hidden reasoning.

The optional synthetic smoke test is:

```bash
cd backend
.venv/bin/python -m app.scripts.azure_translation_smoke_test
```

It skips unless Azure mode is explicitly enabled and sends only fictional spindle examples.

## Enterprise deployment

For production infrastructure, prefer managed identity, grant only the required Azure Cognitive Services OpenAI User RBAC role, restrict network access with private endpoints, and use private DNS. If keys are unavoidable, keep them in Azure Key Vault and inject them at runtime. An API gateway may add organization-level rate limits, egress controls, request IDs, and audit correlation, but must not log CNC prompt content by default.

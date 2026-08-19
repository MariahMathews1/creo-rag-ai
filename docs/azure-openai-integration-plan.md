# Azure OpenAI integration plan: Post Builder only

Azure OpenAI is an optional, explicitly configured implementation of `PostBuilderAIProvider`. It may assist during machine-level post development. It must never receive CL/NCL, part geometry, features, fixtures, coordinates, toolpaths, machining sequences, production G-code, or part identifiers.

## Provider modes

- `disabled`: no drafting provider.
- `mock`: deterministic local development/test fixture; default.
- `azure_openai`: organization-approved external Post Builder provider.

The Azure transport retains Entra ID/managed identity preference, safe failure mapping, health checks, timeouts, and server-only secrets. Configuration uses `POST_BUILDER_AI_PROVIDER` plus the existing `AZURE_OPENAI_*` transport settings. Public-web retrieval is disabled.

## Allowed minimized context

- machine ID/display name/type and immutable revision ID;
- controller manufacturer/model/version;
- machine axes, configured limits, capabilities, and post template values;
- one selected post section;
- existing engineer-reviewed machine-level post rules for that section;
- explicitly approved, relevant machine/controller document excerpts and their citation IDs.

The central policy scans raw requests before schema coercion/provider selection. The external implementation enforces it again on the exact outbound object. Violations return a typed policy error before network activity.

## Structured output

The provider returns only draft rules/templates, missing information, assumptions, source reference IDs, and warnings. Citation IDs must belong to the supplied allowlist. Every rule remains `draft`; no response can update a rule, approve a post, generate executable programs, or bypass deterministic validation.

## Audit and operations

`AIInvocation` records provider/deployment identifiers, draft/section/document IDs, prompt/response schema versions, request hashes, status, duration, and safe usage metadata. It does not persist prompts, secrets, hidden reasoning, CL/NCL, or part-specific data.

Production enablement requires organizational security and data-processing approval, private networking/egress controls where required, least-privilege Azure RBAC, region/retention review, rate limits, incident procedures, and validation of the engineering workflow. Runtime Creo/G-POST execution does not call Azure.

## Phase 11 implementation status

The provider now sits behind persistent section drafts and rule-level review. The eight draftable sections are program structure, tooling, spindle, coolant, feed, motion, coordinates, and program end. Cycles remain deferred and cannot invoke the provider. Contextual readiness, deterministic evidence retrieval, explicit context review, and returned-reference allowlisting all run before a section draft is persisted. Azure remains optional; the deterministic local mock is the default development path.

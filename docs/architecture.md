# Architecture notes

Pre-Azure validation adds `ValidationPolicy`, extended `PostValidationRecord`, `ValidationFinding`, and `GPostDiagnostic`. The local `GPostDiagnosticParser` normalizes supported listing messages without AI or full-file persistence. VERICUT remains external and is represented only through manual handoff and validation metadata.

## Post Record engineering layer

The primary product architecture is an additive Post Record layer over the existing `GPostDraft` lineage. `MachineKnowledgeFact`, `OFGSetting`, `SiteStandard`, `PostStandardApplication`, `CustomLogicItem`, `OpenQuestion`, and `PostValidationRecord` provide manual-first engineering state. Phase 11 `PostSectionDraft`/`PostRuleDraft` data remains for compatibility and is classified independently from the primary workflow. Whole-record versions embed a Post Development Package snapshot. Azure is not required.

The current architecture is retained, but the primary R&D direction is now AI-assisted post development: immutable machine-profile revisions provide authoritative context; approved machine/controller excerpts provide cited technical evidence; reviewed post rules and deterministic validation remain authoritative; and `PostBuilderAIProvider` produces draft machine-level suggestions only. Historical CL/G-code pairs remain local secondary validation evidence. See [R&D governance pivot](rd-governance-pivot-post-builder.md).

The proof of concept is a monorepo with two deployable processes:

- `backend`: FastAPI, Pydantic, SQLAlchemy, and SQLite. Deterministic parsing and validation live here.
- `frontend`: React, TypeScript, and Vite. It calls the backend over JSON HTTP.

The parser produces line-preserving blocks and modal state for local deterministic workflows. Those blocks never enter Post Builder AI context. The rules engine consumes local data and a machine profile, then emits explainable findings. AI can draft post-development proposals but cannot mutate accepted rules, deterministic findings, or runtime programs.

Phase 10 uses a separate translation provider path: centralized policy filters exact-machine verified/consented records, internal SQL retrieval ranks them, a versioned prompt builder minimizes aligned excerpts, and a mock or Azure provider returns strict structured interpretation. Retrieval and page loading never call Azure. The frontend has no Azure SDK or credentials.

Future manual ingestion should calculate hashes, store extracted text in `SourceDocument`, and retain citations at chunk or section level. It should not be mixed into the deterministic rules until controller-specific requirements are represented as reviewed configuration.

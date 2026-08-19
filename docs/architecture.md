# Architecture notes

The current architecture is retained, but the primary R&D direction is now AI-assisted post development: immutable machine-profile revisions provide authoritative context; approved machine/controller excerpts provide cited technical evidence; reviewed post rules and deterministic validation remain authoritative; and `PostBuilderAIProvider` produces draft machine-level suggestions only. Historical CL/G-code pairs remain local secondary validation evidence. See [R&D governance pivot](rd-governance-pivot-post-builder.md).

The proof of concept is a monorepo with two deployable processes:

- `backend`: FastAPI, Pydantic, SQLAlchemy, and SQLite. Deterministic parsing and validation live here.
- `frontend`: React, TypeScript, and Vite. It calls the backend over JSON HTTP.

The parser produces line-preserving blocks and modal state for local deterministic workflows. Those blocks never enter Post Builder AI context. The rules engine consumes local data and a machine profile, then emits explainable findings. AI can draft post-development proposals but cannot mutate accepted rules, deterministic findings, or runtime programs.

Phase 10 uses a separate translation provider path: centralized policy filters exact-machine verified/consented records, internal SQL retrieval ranks them, a versioned prompt builder minimizes aligned excerpts, and a mock or Azure provider returns strict structured interpretation. Retrieval and page loading never call Azure. The frontend has no Azure SDK or credentials.

Future manual ingestion should calculate hashes, store extracted text in `SourceDocument`, and retain citations at chunk or section level. It should not be mixed into the deterministic rules until controller-specific requirements are represented as reviewed configuration.

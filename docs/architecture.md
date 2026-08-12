# Architecture notes

The current architecture is retained, but its R&D evidence hierarchy has changed: immutable machine-profile revisions provide exact context; manuals provide documented technical evidence; verified CL/G-code pairs provide the primary evidence of site-specific translation behavior; deterministic rules remain authoritative; and the optional translation-AI provider is explanation-only and advisory. See [R&D translation strategy](rd-translation-strategy.md).

The proof of concept is a monorepo with two deployable processes:

- `backend`: FastAPI, Pydantic, SQLAlchemy, and SQLite. Deterministic parsing and validation live here.
- `frontend`: React, TypeScript, and Vite. It calls the backend over JSON HTTP.

The parser produces line-preserving blocks and modal state. The rules engine consumes those blocks and a machine profile, then emits explainable findings. The advisory AI interface is downstream of deterministic analysis and cannot mutate its results.

Phase 10 uses a separate translation provider path: centralized policy filters exact-machine verified/consented records, internal SQL retrieval ranks them, a versioned prompt builder minimizes aligned excerpts, and a mock or Azure provider returns strict structured interpretation. Retrieval and page loading never call Azure. The frontend has no Azure SDK or credentials.

Future manual ingestion should calculate hashes, store extracted text in `SourceDocument`, and retain citations at chunk or section level. It should not be mixed into the deterministic rules until controller-specific requirements are represented as reviewed configuration.

# Architecture notes

The proof of concept is a monorepo with two deployable processes:

- `backend`: FastAPI, Pydantic, SQLAlchemy, and SQLite. Deterministic parsing and validation live here.
- `frontend`: React, TypeScript, and Vite. It calls the backend over JSON HTTP.

The parser produces line-preserving blocks and modal state. The rules engine consumes those blocks and a machine profile, then emits explainable findings. The advisory AI interface is downstream of deterministic analysis and cannot mutate its results.

Future manual ingestion should calculate hashes, store extracted text in `SourceDocument`, and retain citations at chunk or section level. It should not be mixed into the deterministic rules until controller-specific requirements are represented as reviewed configuration.


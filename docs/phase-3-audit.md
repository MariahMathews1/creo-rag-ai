# Phase 3 audit

| Problem | Cause | Fix |
| --- | --- | --- |
| `SourceDocument` lacked processing and secure-storage metadata. | It was a future-facing Phase 1 model. | Added lifecycle, page, file, controller, error, and processing fields without storing binary content in SQLite. |
| Database evolution depended on `create_all`. | Phase 2 used a lightweight compatibility helper. | Added Alembic and a non-destructive migration for existing data and all Phase 3 tables. |
| No upload security boundary existed. | Documents were not previously accepted. | Added extension, size, empty-file, basename, generated-name, resolved-path, MIME, hash, duplicate, and deletion controls. |
| No extraction, chunking, embedding, or retrieval pipeline existed. | Manual knowledge was outside Phase 2. | Added page-aware extractors, character-based chunks, deterministic mock embeddings, filtered retrieval, top-k, and thresholds. |
| AI output was not citation-grounded. | The initial provider returned placeholders. | Added grounded output validation, stored citation snapshots, forbidden-claim rejection, and mandatory insufficient evidence. |
| The frontend had no manual-reference workflow. | It covered deterministic analysis only. | Added document management/viewer, technical reference sessions, citations, search, and analysis-context actions. |
| Document and answer activity was not auditable. | Those workflows did not exist. | Added scoped audit events without logging API keys or full document text. |

The deterministic validator remains independent. Manual answers cannot alter findings or analysis status.


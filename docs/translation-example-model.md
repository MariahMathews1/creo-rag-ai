# Translation example model

Phase 8 stores a `TranslationExample` as an immutable-context pair of normalized Creo CL/NCL and historical G-code. Required identity is the machine, exact machine-profile revision, name, both sources, and verification status. SHA-256 hashes are calculated after newline normalization; a unique constraint on revision plus both hashes detects exact duplicate evidence without collapsing evidence from different revisions.

The record retains controller/post/operation metadata, optional part/program/project identifiers, tooling and setup context, provenance labels, parse snapshots, deterministic validation summary, review timestamps, and `ai_processing_allowed` (default false). Original filenames are metadata only; uploaded code is never executed.

`TranslationAlignment` belongs only to a translation example. Its links use nullable inclusive CL and G-code spans, allowing one-to-one, one-to-many, many-to-one, many-to-many, manual, and explicit unmatched relationships. Machine-profile revision and machine-context snapshot preserve historical meaning if the active machine profile later changes.

See migration `20260813_01` and `backend/app/models/translation.py` for the exact schema.

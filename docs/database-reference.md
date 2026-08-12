# Database reference

SQLite is the proof-of-concept store. Alembic migration `20260811_01` adds the G-POST tables documented in [G-POST architecture](gpost-generator-architecture.md) without altering existing rows.

Machine context is enforced through foreign keys plus application-level ownership checks. Drafts reference an exact `machine_profile_revisions` row and carry immutable capability/profile snapshots so later profile edits do not reinterpret a historical run.

JSON columns preserve templates, state, warnings, review summaries, traceability, and version snapshots. Source CL is hashed for preview identity; audit metadata stores the hash and counts, not the full source.

Alembic migration `20260813_01` adds `translation_examples`, `translation_alignments`, and `translation_alignment_links`. Examples reference exact machine-profile revisions, snapshot the machine context, store normalized sources and SHA-256 hashes, and enforce revision-scoped pair uniqueness. Alignment links use nullable inclusive spans to preserve one/many/manual/unmatched relationships. Indexes cover machine, revision, status, operation, post revision, hashes, and alignment-review queries. Existing tables and rows are preserved.

Alembic migration `20260814_01` adds `ai_invocations`. It records provider and operation identifiers, machine/revision IDs, selected TranslationExample IDs, an input SHA-256 hash, prompt/schema versions, safe response status/metadata, external-processing flag, duration, and optional token usage. It intentionally stores neither credentials nor complete prompt/input content. A composite TranslationExample index supports machine/status/consent/post/operation retrieval.

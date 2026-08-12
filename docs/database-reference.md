# Database reference

SQLite is the proof-of-concept store. Alembic migration `20260811_01` adds the G-POST tables documented in [G-POST architecture](gpost-generator-architecture.md) without altering existing rows.

Machine context is enforced through foreign keys plus application-level ownership checks. Drafts reference an exact `machine_profile_revisions` row and carry immutable capability/profile snapshots so later profile edits do not reinterpret a historical run.

JSON columns preserve templates, state, warnings, review summaries, traceability, and version snapshots. Source CL is hashed for preview identity; audit metadata stores the hash and counts, not the full source.

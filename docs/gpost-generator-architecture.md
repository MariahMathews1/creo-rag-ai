# G-POST Generator architecture

The G-POST Generator is a separate, machine-scoped R&D workflow. It creates advisory draft post configurations; it does not connect to Creo or a CNC, execute programs, or approve production posts.

## Data flow

1. A `GPostDraft` captures an exact machine-profile revision, capability snapshot, selected machine-owned document IDs, optional approved standard, and selected approved reference programs.
2. `GPostMapping` records translate recognized CL commands by referencing shared configuration templates. Explicit per-mapping overrides are exceptional and visible; unsupported records remain persisted and visible.
3. The existing `CLParser` produces normalized records and source-line provenance.
4. The stateful G-POST service renders draft G-code and records a trace for every emitted block.
5. The existing `GCodeParser` reparses that output.
6. The existing `ValidationEngine` checks the reparsed output against the immutable profile snapshot.
7. `GPostPreviewRun` preserves diagnostics, findings, unsupported commands, missing mappings, warnings, and traceability without storing source CL in audit events.

Machine ownership is checked at every draft and evidence boundary. Documents, revisions, standards, and reference programs from a different machine are rejected.

## Domain tables

- `gpost_drafts`: versioned working configurations and immutable machine context.
- `gpost_draft_versions`: serialized version snapshots and change summaries.
- `gpost_mappings`: CL mapping logic, template references/overrides, support status, V1 applicability, and independent review state.
- `gpost_mapping_evidence`: document, approved-program, and standard evidence links.
- `gpost_preview_runs`: generated R&D output and closed-loop validation results.

Audit events use existing `audit_events` storage and contain identifiers/hashes only, never full CNC programs or manuals.

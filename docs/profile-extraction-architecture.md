# Profile extraction architecture

## Safety boundary

Extraction is advisory and creates proposals only. Every run response declares
that it is advisory, draft-only, and requires qualified review. Extraction never
executes code, generates production G-code, approves a revision, or changes the
active profile.

## Pipeline

1. Validate the machine and selected ready, machine-owned documents.
2. Detect explicit model/variant tokens.
3. Select typed field definitions by category.
4. Search chunks using each definition’s configured terms.
5. Parse deterministic candidates and retain raw source text.
6. Normalize only allowlisted physical units while preserving originals.
7. classify missing units, optional capabilities, variants, and disagreements.
8. Persist every proposal, confidence component, and real chunk citation.
9. Require a user disposition for each field.
10. Apply accepted/edited/manual values to an explicitly based draft.

The default `mock` configuration is deterministic and offline. The
`OpenAICompatibleProfileExtractionProvider` is a structured-output boundary for a
future transport. Any future output must pass type, unit, confidence, status, and
retrieval-context citation validation. Uploaded excerpts are delimited untrusted
data and cannot supply instructions to the provider.

## Confidence and conflict logic

Confidence combines explicit terminology, an extractable value, source
authority, evidence count, unit presence, variant applicability, option
dependency, and conflict state. Current deterministic found values are capped at
0.98; missing-unit and optional/variant outcomes are low; disagreements are 0.35.
Confidence is evidence metadata, not a safety or correctness score.

Different values or units become `conflicting`; the service never selects the
higher, lower, first-authoritative, or apparently safer value. Multiple variants
make physical/option fields ambiguous unless exact applicability was selected.
An option statement proves only that an option exists, not that it is installed.

## Review, draft, and provenance

Review actions are accept, accept with edit, reject, defer, manual entry, and not
applicable. Edits, conflict resolution, low-confidence acceptance, and manual
safety values require notes. Applying a run requires an explicit active, blank,
or selected-prior basis. The new revision remains `draft`; copied and extracted
fields receive `MachineProfileFieldSource` records.

Approval is a separate endpoint with exact-machine and safety acknowledgments.
It rejects pending proposals or unresolved conflicts, supersedes the prior
approved revision, points the machine to the new revision, and records audit
events. All runs, proposals, evidence, review records, and revisions remain.

## Debugging

`ENABLE_PROFILE_EXTRACTION_DEBUG` is off by default. Debug data is limited to
field definitions, terms, retrieved chunks/scores, normalized candidates,
confidence components, and conflict classifications. Hidden model reasoning,
secrets, full manuals, and storage paths are never exposed.

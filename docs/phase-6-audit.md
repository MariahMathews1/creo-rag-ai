# Phase 6 audit

## Existing support

Before Phase 6, `SourceDocument` already recognized `approved_program`, but it
treated that value as a document-retrieval category. It did not store approval,
eligibility, machine-revision, controller, post revision, part, operation,
applicability, or AI-transmission metadata. `AnalysisProject` preserved G-code
hashes and immutable machine-revision snapshots. `GCodeParser`, modal state,
`GCodeBlock`, `ValidationEngine`, `AnalysisFinding`, `AuditEvent`, and the
traceability JSON/Markdown/CSV exports were reusable.

The frontend could upload manuals and run analyses, but it had no reference
program library, eligibility gate, standard extraction/review, standard revision
history, organizational findings, similar-program retrieval, side-by-side view,
exception workflow, or standard/comparison reports.

## Missing persistence and migrations

Phase 6 adds reference programs and their parsed blocks; deterministic standard
extraction runs; versioned organizational standards; convention proposals and
program-line evidence; comparison runs/findings; applicability, exception, and
stale-state metadata. Migration `20260729_01` creates these additive tables and
does not reinterpret historical analysis findings.

## Fixes applied

- Program import uses hashes, ownership checks, extension/size validation, no
  execution, no absolute response paths, and pending eligibility by default.
- Parsing reuses the existing deterministic parser, modal-state tracker,
  machine-revision snapshot, and validation engine.
- Blocking deterministic findings change suitability to `requires_review`
  without silently deleting or excluding the program.
- Extraction accepts only explicitly eligible, parsed, machine-revision and
  applicability-compatible programs. Mixed post revisions require an explicit
  filter.
- Convention frequency, contradictions, heuristic conditions, applicability,
  and exact program lines are visible. Frequency never auto-accepts a proposal.
- Standards are inactive drafts until explicit approval; prior approved
  standards are preserved as superseded.
- Comparisons keep deterministic findings separate from organizational
  differences and include the required historical-similarity safety boundary.
- Reference scope/eligibility changes mark dependent standards and comparisons
  stale without deleting history.

## Risks and bounded limitations

The initial algorithm detects structured command and formatting patterns; it is
not a CNC semantic-equivalence engine or simulator. Logical side-by-side
sections use deterministic sequence diffing. Applicability comparisons are
strict equality checks on governed metadata. The API stores program source in
the local database for this proof of concept; production deployments should add
encryption, access control, retention policy, and malware/content scanning.

## Verification record

Migration `20260729_01` was applied to the local SQLite database. The fictional
demo imported 10 programs: six compatible POST-A eligible sources, one eligible
POST-B source kept outside the extraction dataset, and three ineligible
deprecated/exception/comparison inputs. All 10 prohibit external AI processing.

The final demo run produced 16 convention proposals, explicitly approved
standard revision 3, and comparison 3 with 12 matches, two missing conventions,
one unexpected difference, and one not-applicable conditional convention. The
report preserved deterministic findings in a separate collection and included
all four required safety-boundary fields.

Automated verification completed with 58 backend tests and 31 frontend tests.
Frontend TypeScript checking and the Vite production build also passed.

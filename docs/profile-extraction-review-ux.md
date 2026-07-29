# Profile extraction review workspace

Open an extraction run and use the queue bar to work in risk-first order:
conflicts, eligible high confidence, medium confidence, low confidence, then
not-found fields. `Needs review` includes every pending field; disposition
queues retain deferred, accepted, rejected, manual, and not-applicable work.

The guided dashboard shows authoritative server counts. Review progress is the
number of fields with an intentional disposition. Documentation coverage is the
fraction of registry fields for which the extraction found evidence. Neither
percentage is a safety, correctness, completeness, or production-readiness
score.

Search matches field labels, keys, values, interpretation notes, document
titles, sections, and excerpts. Filters include category, proposal and review
status, confidence range, safety relevance, verification requirement, evidence,
source, claim scope, and variant. Active filters appear as removable chips.
Queue, view, field, search, filters, and open citation are encoded in the URL.

## Review controls

- `A` accept, `E` accept with edit, `R` reject, `D` defer, and `M` manual entry.
- `N`/`P` select next/previous, `/` focuses search, `S` toggles evidence, and
  `?` opens shortcut help.
- Shortcuts are disabled while typing or while a dialog is open.
- Auto-advance moves to the next visible pending field after success.
- Compact table and category checklist modes support faster scanning without
  weakening the review actions.

Batch accept is deliberately narrow and always requires advisory
acknowledgement. Conflicts, safety-relevant values, exact-machine verification,
weak or missing evidence, and ambiguous applicability require individual
review. Batch defer/reject/not-applicable still produces per-field and aggregate
audit events.

## Evidence and drafts

Open a citation in the source drawer to retain queue, filter, field, and scroll
context. Review document type, section, page, excerpt, raw text, normalized
value, evidence role, and relevance. Controller documentation cannot by itself
prove physical installed-machine claims.

When every field has an intentional disposition and variant issues are
resolved, the readiness panel enables draft creation. Choose the draft basis,
inspect the human-readable current-to-proposed comparison, and explicitly
acknowledge before approval. A created draft remains inactive until approved.


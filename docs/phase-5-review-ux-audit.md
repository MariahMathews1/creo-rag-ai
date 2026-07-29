# Phase 5 review UX audit

## Baseline findings

The original review page loaded proposal records into one three-column screen.
It exposed the extraction data, but it did not provide a guided review system
for a large profile:

- the frontend requested the proposal endpoint without a page size, so only the
  first 100 of the KLS-1840N run's 144 fields were available;
- counts and completion were inferred in the browser and were not authoritative;
- documentation coverage could be confused with review progress;
- there were no task queues, full-text search, advanced filters, sorting,
  category completion, dense views, or batch dispositions;
- selected field, filters, and source context were not deep-linkable;
- citations navigated away from the review instead of preserving context;
- mutation success, rollback, auto-advance, unsaved edits, keyboard operation,
  and explicit draft readiness were incomplete;
- draft application and approval existed, but their prerequisites and comparison
  were not presented as a clear final gate.

The backend already preserved important safety properties: individual review
dispositions were audited, drafts were inactive, approval was explicit, and
unresolved proposals prevented draft creation. These behaviors were retained.

## Implemented remediation

The review workspace now has a server-owned summary, paginated/filterable queue
API, category completion, separate review and documentation progress, strong
proposal/review status labels, URL-backed field and filter state, source drawer,
three density modes, keyboard navigation, optimistic mutations with rollback,
protected batch actions, variant gating, and an explicit readiness panel.

Protected high-confidence acceptance excludes conflicts, ambiguity, missing
normalization or citations, conflicting evidence, safety-relevant fields,
exact-machine verification requirements, variant mismatch, and physical claims
supported only by controller documentation. Confidence remains prioritization
metadata, not proof.

## Route and ownership audit

| Concern | Owner |
| --- | --- |
| Proposal detail and individual disposition | Existing proposal routes |
| Counts, progress, readiness, next queue | `GET .../review-summary` |
| Queue membership, search, filters, sorting, pagination | `GET .../review-queue` |
| Protected multi-field disposition | `POST .../proposals/batch-review` |
| Safe high-confidence shortcut | `POST .../accept-eligible-high-confidence` |
| Review interaction audit events | `POST .../review-events` |
| Field, queue, view, filters, citation | URL query state |
| Expanded categories and scroll position | Session storage |

## Remaining bounded limitations

- The current local API returns evidence with each queue record. For substantially
  larger registries, proposal detail/evidence should be fetched lazily.
- The in-route source drawer renders extracted text and page metadata. It does
  not implement embedded PDF page rendering.
- Virtualized rows are not needed at the current 144-field registry size; CSS
  containment and server pagination provide the present performance boundary.

## Public-corpus verification

On 2026-07-29 the actual stored public corpus was run again as extraction 19
against the selected KLS-1840N variant. The three inputs were already processed
through the document pipeline:

| Input | Pages | Chunks | Status |
| --- | ---: | ---: | --- |
| KLS Series brochure PDF | 5 | 11 | ready |
| KLS-1840N deterministic Markdown specification | 1 | 2 | ready |
| FANUC 0i Model F Plus parameter manual PDF | 774 | 2,426 | ready |

The run produced 144 proposals: 26 found, 117 not found, one conflict, and no
ambiguous or failed fields. The full queue returned all 144 records. A warm
local TestClient measurement returned the summary in 31.7 ms and the complete
queue in 36.2 ms.

Key proposals were manufacturer `Kent USA`, machine model `KLS-1840N`,
controller model `0i-Mate TF`, X travel `11 inch`, Z travel `38 inch`, maximum
spindle speed `2000 rpm`, standard spindle power `7.5 hp`, X rapid
`315 ipm`, and Z rapid `394 ipm`. Each cited the one-page deterministic
specification. Travel, rapid, and maximum-RPM proposals remained individual
review items because they are safety relevant; spindle power remained individual
because an optional 10 hp alternative requires exact-machine verification.

The backend and frontend were temporarily served and returned HTTP 200 for the
summary and deep-linked review route, then both processes were stopped. No
interactive browser surface was available in the test environment, so visual
viewport and assistive-technology checks remain on the manual checklist.

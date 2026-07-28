# Machine-profile revisions

`MachineProfile` remains the stable local machine identity and compatibility
surface. `active_revision_id` identifies the configuration used for new work.
Configuration history lives in `MachineProfileRevision`.

## States

- `draft`: editable/reviewable and never active automatically.
- `under_review`: explicitly submitted, still inactive.
- `approved`: explicitly acknowledged and active.
- `superseded`: a previously approved revision retained for history.
- `rejected`: retained with its review summary.

Sources are `manual_entry`, `document_extraction`, `imported`,
`copied_revision`, or `mixed`. Creating a draft requires choosing the current
active revision, a blank draft, or a named prior revision as its basis.

Approval requires a draft/under-review state, exact machine/controller
applicability acknowledgment, safety-notice acknowledgment, reviewed core
identity, intentional review of proposals, and no unresolved conflict. Approval
updates the compatibility fields only after those checks and preserves the
previous revision as superseded.

## Analysis snapshots

New analyses resolve the active approved revision and store both its ID and a
JSON snapshot of the exact limits, commands, offsets, and templates used. The
deterministic validator reads that snapshot. Approving a later revision does not
recalculate or alter an old analysis. A future explicit compare action may mark
old results stale, but must not silently recompute them.

Migration `20260728_02` creates an initial approved compatibility revision for
each existing machine and backfills analysis references/snapshots without
removing legacy data.

# Phase 5 review UX test checklist

## Automated

- [x] Server summary counts, category totals, progress, coverage separation, and
  readiness.
- [x] Queue search, category/evidence filtering, confidence sorting, and
  pagination response.
- [x] Protected accept acknowledgement, partial failure reasons, controller-only
  physical-claim exclusion, per-field audit, and batch audit.
- [x] Dashboard, queues, status labels, URL state, keyboard suppression,
  auto-advance, source drawer, batch confirmation, compact/checklist views,
  inactive draft comparison, approval gate, optimistic rollback, unsaved edit,
  and variant rerun.
- [x] Complete backend suite, complete frontend suite, TypeScript check, and
  production build.

## Manual KLS-1840N

- [ ] Open the actual completed KLS-1840N extraction run.
- [ ] Confirm all 144 proposals are represented, including fields after the old
  100-record cutoff.
- [ ] Verify x travel, z travel, spindle RPM, controller, and manufacturer
  citations in the source drawer.
- [ ] Exercise conflicts, high-confidence, not-found, accepted, deferred, and
  manual queues.
- [ ] Apply and remove filters; reload a copied URL and confirm state restoration.
- [ ] Review one field with auto-advance on and another with it off.
- [ ] Confirm typing suppresses shortcuts and an unsaved edit blocks navigation.
- [ ] Inspect 1280 px, tablet, and narrow mobile layouts at 100% and 200% zoom.
- [ ] Confirm focus visibility, dialog Escape behavior, screen-reader status
  announcements, and reduced-motion behavior.
- [ ] Confirm the protected batch preview explains every excluded field.
- [ ] Resolve all fields in a disposable run, create an inactive draft, inspect
  comparison, and verify approval needs explicit acknowledgement.


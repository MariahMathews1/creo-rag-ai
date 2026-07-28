# Phase 5 manual test checklist

- [ ] Start the application and run `alembic upgrade head`.
- [ ] Run `python -m app.scripts.seed_profile_extraction_demo`.
- [ ] Open the fictional LT-200 machine and confirm its uploaded documents.
- [ ] Start an extraction and select an exact machine variant.
- [ ] Confirm run status, processed/found/not-found/conflict/ambiguous counts.
- [ ] Review identity, axis travel, and maximum spindle RPM.
- [ ] Open one supporting and one conflicting citation at its source.
- [ ] Accept a proposal.
- [ ] Edit and accept a proposal with a note.
- [ ] Reject and defer proposals.
- [ ] Enter a manual value with a note.
- [ ] Resolve the spindle conflict without automatically choosing a value.
- [ ] Create a draft from the active revision and compare changes.
- [ ] Confirm the draft did not become active.
- [ ] Submit the draft for review.
- [ ] Check the exact-machine acknowledgment and approve explicitly.
- [ ] Confirm the old revision remains as superseded.
- [ ] Create and run an analysis; inspect its revision ID and snapshot.
- [ ] Approve another revision and confirm the old analysis snapshot is unchanged.
- [ ] Restart both services and confirm persistence.

At every step confirm the UI describes proposals and documentation coverage, not
certification, completeness, production readiness, or guaranteed safety.

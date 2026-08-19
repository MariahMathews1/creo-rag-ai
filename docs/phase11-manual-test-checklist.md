# Phase 11 manual test checklist

Use fictional data only. Nothing in this checklist authorizes machine use.

- [ ] Run migrations and `make seed-post-builder-demo`.
- [ ] Set `POST_BUILDER_AI_PROVIDER=mock`, start backend/frontend, and open the fictional post draft.
- [ ] Confirm the banner says AI assists post development only and no CL/NCL input exists.
- [ ] Confirm eight supported section cards plus visible deferred Cycles.
- [ ] Confirm manual and AI readiness differ where evidence is insufficient.
- [ ] Open Spindle and verify three columns: machine facts, eligible evidence, and R&D action.
- [ ] Review AI Context and confirm CL/NCL, part geometry, and production programs say `NOT INCLUDED`.
- [ ] Generate once and verify three mock spindle rules all require review.
- [ ] Accept one rule, edit-and-accept one, and mark one Needs More Information; verify the section aggregate.
- [ ] Regenerate and confirm a new section version while earlier decisions remain accessible.
- [ ] Compare the latest two section versions.
- [ ] Create a whole-post version and confirm section state/reviewer history carries forward.
- [ ] Export JSON and Markdown; confirm rules, templates, evidence, assumptions, warnings, and review data are present and labeled R&D only.
- [ ] Disable the evidence document's AI policy and confirm it disappears from retrieval.
- [ ] Try another machine's document ID and confirm it is rejected.
- [ ] Confirm Cycles cannot generate.
- [ ] Inspect audit records and confirm hashes/IDs exist but no prohibited payload content exists.

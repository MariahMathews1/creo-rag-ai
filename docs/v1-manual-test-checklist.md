# V1 manual test checklist

- [ ] Dashboard loads six status summaries and quick actions.
- [ ] Add and edit a machine; controller and limit fields persist.
- [ ] Upload a document for one machine and confirm cross-machine isolation.
- [ ] Find Information in Documents and confirm clear fields individually and in a batch.
- [ ] Add a translation pair; open Paired Code and Toolpath.
- [ ] Advanced exposes patterns, AI experiment, provenance, alignment, and history.
- [ ] Create a G-POST draft through Select Machine → Confirm Post Context → Create Draft.
- [ ] Generate an R&D draft from CL/NCL and inspect Results, Toolpath, and Evidence.
- [ ] Advanced Post Configuration exposes templates, mappings, validation, and versions.
- [ ] Ask Machine Assistant a machine-specific question and open a citation.
- [ ] Run G-code Review and inspect a deterministic finding.
- [ ] Confirm safety notices remain visible and no output is presented as production-ready.

## Pre-Azure Post Builder workflow

- [ ] Search for KLS-1840N; filter by machine, active status, and updated date.
- [ ] Open a post's More menu; verify rename, duplicate, archive, and delete/retention explanation.
- [ ] Show archived posts with the Archived view.
- [ ] Create a post for KLS-1840N; verify Reference Programs are absent, Machine Configuration is Current, and FANUC Lathe is selected automatically.
- [ ] Verify Overview clearly shows build progress, needs attention, and source knowledge.
- [ ] Open Machine Knowledge; inspect a compact checklist, drill into Spindle, update a value, and verify status refreshes.
- [ ] Open Build Post; verify the page describes one post, contextual actions, the Ready to Draft explanation, and deferred Cycles.
- [ ] Draft one component with the mock provider and verify Drafted / Needs Review plus updated overall progress.
- [ ] Open Review; verify only actionable components appear and accepted/edited/rejected rules update Complete Post.
- [ ] Create a meaningful version; verify monotonic numbering, a clear current version, read-only history, and no unrelated machine drafts.
- [ ] Attempt a version without changes and verify “No changes since vN.”
- [ ] Open Sources; enable an eligible machine-level source and verify Allowed. Attempt an ineligible source and verify the reason/remediation.
- [ ] Verify no screen implies production approval or native G-POST export compatibility.

# V1 manual test checklist

## Pre-Azure validation and VERICUT handoff

- [ ] Confirm no CAD geometry workflow or collision-guarantee wording exists.
- [ ] Record Configuration Review and G-POST Compilation results.
- [ ] Parse a fictional local listing and inspect deterministic diagnostics without an AI call.
- [ ] Link only deterministically resolved diagnostics to Custom Logic; keep unknown sources unknown.
- [ ] Create and manually resolve a finding and optionally create an Open Question.
- [ ] Open Prepare for VERICUT Validation and inspect its readiness checklist.
- [ ] Record VERICUT `PASS_WITH_FINDINGS` with a fictional report reference.
- [ ] Confirm timeline/export metadata excludes CL/NC/CAD/full listing content.
- [ ] Confirm all actions work with the AI provider disabled.

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

## Post Record information architecture

- [ ] Confirm primary tabs are Overview, Machine Knowledge, OFG Configuration, Site Standards, Custom Logic, Review & Validation, Versions, and Sources.
- [ ] Confirm Historical Post Examples, G-code Review, Toolpath Viewer, FIL/CIMFIL, and technical details are under Advanced Tools.
- [ ] Search/filter Machine Knowledge; open Maximum Spindle RPM and verify source/page, reviewer state, and Used By mapping.
- [ ] Open an OFG spindle setting and verify source facts, status, custom-logic flag, and Unverified menu path.
- [ ] Create/apply a scoped Site Standard and record a conflict that requires review.
- [ ] Identify Custom Logic and confirm the specialist editor link plus “Site verification required” source format.
- [ ] Add/resolve an Open Question and record manual validation with AI Used = No.
- [ ] Create a version after an OFG change; verify the package snapshot and no-change rejection.
- [ ] Export Markdown, R&D JSON, and CSV OFG checklist with evidence/review state.
- [ ] Confirm no `.opt` compatibility, shop-floor approval, or production-ready claim appears.

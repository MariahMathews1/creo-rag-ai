# Phase 11 — AI-assisted post section drafting

Phase 11 adds a governed R&D workflow for drafting machine-level post behavior one section at a time. It is not a CL/NCL translator, G-code generator, runtime postprocessor, or production approval system.

## Supported sections

`program_structure`, `tooling`, `spindle`, `coolant`, `feed`, `motion`, `coordinates`, and `program_end` can be drafted after their contextual readiness gate passes. `cycles` remains visible but is always **Deferred / Needs Information** and cannot invoke AI.

Readiness distinguishes manual setup from AI-assisted drafting. Known profile facts can make manual configuration possible, while AI drafting additionally requires explicitly eligible, relevant evidence or accepted same-section rules. Unknown facts stay unknown.

## Workflow

1. Open a machine-scoped post draft and select one section.
2. Review the machine facts and deterministic evidence retrieval result.
3. Select allowed evidence and inspect the outbound context preview.
4. Explicitly generate a structured R&D draft.
5. Accept, edit-and-accept, reject, or request information for each rule.
6. Regenerate into a new immutable section version when needed.
7. Compare section versions, create a whole-post version, or export JSON/Markdown for review.

Generated rules begin at `needs_review`. They never update an accepted rule in place. Whole-post versioning copies the latest section state and reviewer history. JSON and Markdown exports contain templates, evidence references, assumptions, warnings, and review decisions, but remain non-production artifacts.

## Boundary

AI context can contain an approved machine-profile revision, one section, accepted machine-level rules from that same section, and eligible machine/controller document excerpts. CL/NCL, part geometry, part/toolpath coordinates, production programs, G-code, and historical translation pairs are prohibited. Creo/G-POST remains the runtime processor.

Run the fictional demo with `make seed-post-builder-demo`; enable `POST_BUILDER_AI_PROVIDER=mock` for deterministic local drafting.

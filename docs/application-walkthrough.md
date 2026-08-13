# Application walkthrough

> V1 navigation and terminology are documented in [V1 NC programmer workflow](v1-product-workflow.md). The detailed material below remains useful for advanced engineering workflows.

G-POST now evaluates readiness against the current CL input. Supported but unreviewed behavior is warned; unrelated mappings do not block the preview. See [Current-CL G-POST preflight](v1-gpost-preflight.md).

The primary workflows remain Dashboard, Machine Profiles, Documents, Manual Assistant, Analysis/Traceability, Profile Extraction, Approved Programs, and Standards. G-POST Generator is an additional top-level tab.

Open **G-POST Generator** to see the dense table of existing versioned drafts. Creating a draft is a guided three-step flow: select a contextualized machine row, review source readiness and blockers, then confirm the draft name, revision, and controller family.

Opening a draft navigates to `/gpost/{draft_id}`. A compact header permanently identifies the machine, controller, version, and status. Overview, Sources, Configuration, Mappings, Test, Validation, and Versions progressively disclose the workflow. Mapping filters, selection, source drawer, and test-result view are URL-backed so review context survives tab changes and evidence inspection. CL/NCL input appears only on Test, where generated code uses a numbered code viewer and the trace table links each emitted block back to CL and mapping state.

Use machine cards to open the generator in context. From a document viewer, **Use as G-POST Reference** opens the generator with that machine/document preselected; it does not create mappings automatically.

Open **Translation Examples** at `/translations` to inspect dataset counts, filter active pairs, import paired source files, or explore confirmed verified patterns. Import is a guided machine-revision, source-pair, and provenance flow; every new normal import is a candidate. Detail pages show immutable identity/hashes, split parsed sources, explicit alignment proposals and unmatched records, deterministic findings, and gated reviewer transitions. The explorer visibly separates machine, controller, post revision, and operation contexts. Historical evidence exposed to G-POST is read-only.

Open **Toolpath** within Analysis, a Translation Example, or a completed G-POST preview to inspect parsed programmed motion. Select XY/XZ/YZ, toggle CL/G-code/rapid/feed/findings/alignment, filter tools/operations, and step through sequence. Selecting a segment preserves its source line, alignment, and finding identity. Explicit coordinate/geometry warnings explain what is not known. The view is never a material-removal simulation.
# Controlled AI retrieval and interpretation

Open **Translation Examples → AI Retrieval Preview**. Select an exact machine and revision, enter the post/operation context and a CL segment, then choose **Find Similar Verified Examples**. Retrieval remains internal and reports that no AI call occurred. Review and select the returned examples before choosing **Generate AI Interpretation**. The result shows its provider, example IDs, uncertainty, and audit invocation.

Individual Translation Example detail pages expose explicit AI-processing permission. G-POST mapping detail offers the same read-only retrieval/interpretation workflow without changing the mapping.

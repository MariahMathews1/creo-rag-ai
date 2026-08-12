# Application walkthrough

The primary workflows remain Dashboard, Machine Profiles, Documents, Manual Assistant, Analysis/Traceability, Profile Extraction, Approved Programs, and Standards. G-POST Generator is an additional top-level tab.

Open **G-POST Generator** to see the dense table of existing versioned drafts. Creating a draft is a guided three-step flow: select a contextualized machine row, review source readiness and blockers, then confirm the draft name, revision, and controller family.

Opening a draft navigates to `/gpost/{draft_id}`. A compact header permanently identifies the machine, controller, version, and status. Overview, Sources, Configuration, Mappings, Test, Validation, and Versions progressively disclose the workflow. Mapping filters, selection, source drawer, and test-result view are URL-backed so review context survives tab changes and evidence inspection. CL/NCL input appears only on Test, where generated code uses a numbered code viewer and the trace table links each emitted block back to CL and mapping state.

Use machine cards to open the generator in context. From a document viewer, **Use as G-POST Reference** opens the generator with that machine/document preselected; it does not create mappings automatically.

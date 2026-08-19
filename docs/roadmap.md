# Development roadmap

## V1 product simplification — complete

Primary navigation, Dashboard, Machines, Documents, Post Builder, Historical Post Examples, Machine Assistant, and G-code Review now follow the post-engineering workflow. See [V1 UI reduction decisions](v1-ui-reduction-decisions.md).

## V1 usability polish and contextual status semantics — complete

Action hierarchy, shared menus, simplified toolpath controls, contextual G-POST statuses, and current-CL preflight refine the V1 workflow without expanding generation scope.

## Phase 7 — Verified CL/G-code Translation Dataset Foundation

Define the trust model, conceptual entity, provenance, verification states, machine isolation, operation taxonomy, data boundaries, and reuse plan. This architectural milestone does not add storage or an explorer.

## Phase 8 — Verified CL/G-code Translation Dataset Foundation (implemented)

Implemented versioned storage, import/deduplication, provenance review, verification governance, flexible CL/G-code span alignment, machine-isolated exploration, fictional demo data, and read-only historical G-POST mapping evidence.

## Phase 9 — Toolpath Visualization and Visual Traceability (implemented)

Implemented lathe X/Z and mill XY/XZ/YZ Canvas views with programmed-motion, line/alignment/finding traceability, supported arc geometry, accessibility table, and large-program simplification. Material removal remains explicitly separate.

## Phase 10 — Azure OpenAI translation experiment infrastructure (historical)

Implemented a controlled translation experiment. The direction is now retired: CL/NCL provider invocation is prohibited, while local retrieval/alignment remains for historical research and regression evidence.

## Phase 11 — AI-assisted Post Builder section drafting (implemented)

Implemented a separate `PostBuilderAIProvider`, centralized prohibition of CL/NCL and part-specific provider context, deterministic section evidence retrieval, contextual readiness, immutable structured section/rule drafts, rule-level review, version comparison, exports, audit, fictional seed data, and a three-column Post Builder UI. Cycles remain deferred. See [Phase 11 section drafting](phase11-post-section-drafting.md).

## Phase 12 — Machine-knowledge curation and post-rule coverage

Improve document excerpt approval, missing-information workflows, machine capability coverage, evidence citations, and machine-level post rule completeness.

## Phase 13 — Site-format exporter and controlled post validation

Implement a proprietary site/PTC export adapter only after the target format is verified. Add controlled fixtures, deterministic rule checks, version comparison, simulation/prove-out evidence, and qualified approval gates.

## Phase 14 — Runtime integration (no AI)

Integrate only approved post artifacts into the Creo/G-POST runtime. Runtime CL/NCL to G-code translation remains deterministic and contains no AI provider call.

## Later investigations

- deterministic document extraction and optional MATLAB evaluation/interchange;
- advanced historical evidence integration into G-POST mappings;
- qualified simulation integrations and stronger enterprise controls.

# R&D governance pivot: AI-assisted Post Builder

## Post Record information-architecture update

The user-facing product no longer treats independent AI-generated sections as its primary model. The governed system of record is a Post Record: reviewed Machine Knowledge, OFG requirements, Site Standards, Custom Logic, Open Questions, validation records, sources, and versions. AI remains optional, explicit, machine-document scoped, and subordinate to engineer review. Phase 11 section drafts are retained as compatible internal data.

## Current hypothesis

> A controlled AI assistant may reduce the effort required to develop and maintain machine-specific post-processor configurations by combining approved machine-profile data, structured machine/controller documentation, deterministic extraction, and reviewed machine-level programming conventions—without exposing part-specific CL/NCL or using AI during runtime post processing.

AI is a development-time assistant, never the runtime translator.

The approved runtime remains:

```text
Creo CL/NCL -> approved Creo/G-POST post -> machine-specific G-code
```

The development workflow is:

```text
Approved machine profile + approved machine-level document excerpts
                           |
                           v
                PostBuilderAIProvider
                           |
                           v
             draft machine-level post rules
                           |
                           v
       engineer review -> deterministic validation -> version/approval
```

CL/NCL, part geometry, features, fixtures, coordinates, toolpaths, machining sequences, production programs, and part identifiers cannot enter the provider context. This is enforced centrally before provider selection and again at the external provider boundary.

CAD models, STEP/IGES/Creo part geometry, customer designs, VERICUT geometry/project data, test-program content, and part-specific diagnostic listings are also prohibited. Local diagnostic parsing and every validation stage operate without AI.

## Evidence hierarchy

1. Approved machine-profile revision: authoritative machine identity and limits.
2. Machine-builder documentation.
3. Controller documentation.
4. Programming documentation.
5. Existing approved machine-level post configuration.
6. Reviewed machine-level programming conventions.
7. Historical CL/G-code pairs and approved G-code programs: local secondary regression and behavior evidence only.
8. AI suggestions: untrusted drafts that never auto-accept or approve.

Unknown machine information remains unknown. The provider must identify missing facts and assumptions rather than inventing machine behavior.

## Provider boundary

`PostBuilderAIProvider` is separate from the retired `TranslationAIProvider`. It exposes machine/post-development operations such as section drafting, machine-knowledge analysis, missing-information identification, rule explanation/comparison, and revision suggestions. It intentionally has no `translate_cl`, `generate_gcode`, toolpath, or production-program method.

Available modes are `disabled`, deterministic local `mock`, and explicitly configured `azure_openai`. Azure reuses the existing approved transport/authentication infrastructure, but outbound content is constructed from a minimized section-specific contract. Public-web retrieval is disabled.

Every result is structured, source-reference constrained, labeled `draft`, and recorded in `AIInvocation` with safe metadata and content hashes. Prompts, credentials, CL/NCL, and part-specific content are not stored in the audit record.

## Review and approval

Generated sections are proposals only. A post engineer may accept, edit and accept, reject, or request more machine information. No action in Post Builder constitutes production approval. Production adoption requires qualified engineering review, deterministic checks, site-controlled validation, simulation/prove-out, versioning, and the organization’s normal approval process.

The current JSON and Markdown exports are research/review artifacts. `PostDraftExporter` is the explicit adapter boundary for a future proprietary site/PTC G-POST format after that format and its approval requirements are verified. Any F21, F23, P21, or P23 reference is a site format whose semantics require verified site/PTC evidence. MATLAB remains a possible future `MachineDocumentExtractionProvider` or evaluation/interchange adapter, not a runtime dependency; Python deterministic extraction remains the current implementation.

## Phase 11 governed implementation

The pivot is implemented as immutable `PostSectionDraft` revisions with child `PostRuleDraft` decisions, contextual manual-versus-AI readiness, deterministic machine-isolated evidence retrieval, opt-in document eligibility, explicit context preview/invocation, and citation allowlisting. Engineers review every rule independently. Regeneration and whole-post versioning preserve history; exports include that evidence and review state. Cycles remain visible but deferred pending a dedicated evidence and validation design.

## Development/runtime divider

```text
MACHINE DOCUMENTS -> STRUCTURED EXTRACTION -> MACHINE PROFILE
                                            -> POST BUILDER AI
                                            -> DRAFT POST RULES
                                            -> ENGINEER REVIEW
                                            -> APPROVED POST CONFIGURATION
====================== AI DOES NOT PARTICIPATE BELOW ======================
CREO NC -> CL/NCL -> APPROVED POST -> G-CODE
```

## Retired direction

The former retrieval-assisted CL-to-G-code AI experiment is deprecated. Its endpoints reject invocation with `AI_CL_NCL_TRANSMISSION_PROHIBITED`. Historical models, fields, screens, and local deterministic alignment remain available for compatibility, audit, and dataset research; a legacy consent value cannot authorize external processing.

# Phase 7 reuse audit

## Summary

The existing application supplies most infrastructure needed for the revised direction. Phase 8 should extend it deliberately without converting analysis records or approved G-code programs into trusted pairs implicitly.

| Existing component | Reuse as-is | Extension needed | Keep separate / technical debt |
| --- | --- | --- | --- |
| `app/cl_parser` | Source preservation, normalized commands, parameters, coordinates, operation markers, modal state | Parser-version pinning in pair snapshots; broader Creo fixtures | Unsupported commands and positional lathe semantics need explicit coverage |
| `app/parsers/gcode.py` | Blocks, commands, coordinates, modal state, parse errors | Persist parser version and canonical comparison representation | Parsing is not successful-use verification |
| `app/alignment` and traceability API/models | Scoring concepts, explanations, reviewed links, issues, reports | Generalize ownership from analysis projects and support span/cardinality links | Current foreign keys assume one analysis project and predominantly one-to-one links; do not overload them prematurely |
| Machine profiles and revisions | Machine scope and exact immutable context | Compatibility/family keys for explicit fallback retrieval | Current editable profile and immutable revision must never be conflated |
| Documents and Manual Assistant | Technical evidence, citations, retrieval, access metadata | Evidence links from future pair/mapping views | Manuals describe capability, not observed post behavior; Manual Assistant is not a post-learning model |
| Approved reference programs | Governance metadata, post identity, successful-use concepts, G-code parsing, eligibility | Optional migration/import bridge when a matching CL source is proven | A G-code-only reference program is not a translation pair and must not be auto-promoted |
| G-POST mappings/configuration | Candidate behavior visualization, deterministic previews, mapping review | Separate historical translation evidence and observed-pattern comparison | Manual evidence and historical evidence require different types; template acceptance is not dataset verification |
| Deterministic rule engine | Authoritative candidate validation | Versioned findings associated with future pairs and candidates | Rule success does not prove equivalence, collision freedom, or production readiness |
| Audit model | Event envelope and machine/project association | Translation-example, retrieval, provider, and review event metadata | Event schema is flexible JSON; later reporting may require typed event conventions |
| Program comparisons/standards | Normalization, historical comparison UX, evidence separation | Compare candidate output to verified pairs by exact context | Organizational frequency is not controller capability or deterministic authority |
| AI provider abstraction | Local mock pattern and explicit external-processing settings | Separate `TranslationAIProvider` structured contract | Existing Manual Assistant provider should not be stretched into translation generation |

## Architectural conflicts found

1. “Phase 7” was previously used for the G-POST prototype. Roadmap language should distinguish the implemented G-POST R&D tool from the revised Phase 7 dataset foundation.
2. Existing traceability is analysis-project-centric and link records reference single CL/G-code records. Translation alignment needs source-pair ownership and one-to-many/many-to-one spans.
3. Approved reference programs contain governed G-code but usually no proven matching CL input. Eligibility for standards cannot imply pair verification.
4. G-POST mapping evidence currently emphasizes documents/configuration. Historical translation evidence needs its own evidence type, counts, exception grouping, and post-revision scope.
5. Current machine/controller metadata has legacy records that demonstrate why immutable revision identity and compatibility checks are essential.
6. Existing AI abstractions answer document questions. Translation requires a separate provider contract, retrieval audit, structured output, and stricter data boundary.

## Recommended Phase 7/8 implementation order

1. Freeze terminology, statuses, operation taxonomy, provenance contract, and retrieval isolation policy.
2. Add migration and models for immutable source pairs, provenance, trust history, and span alignments.
3. Add import, hashing, duplicate detection, exact-machine ownership checks, and parser snapshots.
4. Generalize/reuse alignment scoring while preserving analysis traceability tables.
5. Add qualified review and explicit `verified_successful` eligibility transitions.
6. Build the machine-scoped explorer, filters, alignment review, and audit exports.
7. Integrate historical evidence into G-POST as a separate read-only evidence source.
8. Only after corpus governance is proven, proceed to visualization and provider infrastructure.

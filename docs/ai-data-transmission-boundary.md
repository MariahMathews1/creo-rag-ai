# AI data-transmission boundary

All Post Builder AI requests pass through the centralized governance policy before provider selection. External providers receive only minimized machine-level post-development context.

## May be sent

- the selected approved machine profile and immutable revision identity;
- machine type, axes, controller, limits, capabilities, and machine-level post templates;
- a single selected post section;
- existing engineer-reviewed machine-level rules;
- explicitly approved and relevant machine/controller document excerpts with allowlisted citation IDs.

## Prohibited

- Creo CL/NCL text, records, files, excerpts, hashes used as content, or derived toolpath sequences;
- part geometry, feature/fixture geometry, coordinates, machining sequences, toolpaths, or part/work-order identifiers;
- production or part-specific G-code and programs;
- historical TranslationExample excerpts or cross-machine examples;
- unrelated/full documents when a relevant excerpt suffices;
- credentials, tokens, local paths, hidden reasoning, and public-web content.

The policy constants `CL_NCL_EXTERNAL_AI_ALLOWED = False` and `PART_SPECIFIC_EXTERNAL_AI_ALLOWED = False` are hard constraints, not user preferences. A legacy `ai_processing_allowed` database value cannot override them. Violations return `AI_CL_NCL_TRANSMISSION_PROHIBITED` or `AI_PART_SPECIFIC_DATA_PROHIBITED` before any provider is invoked.

## Invocation and runtime

Opening a screen, importing a historical pair, running local alignment/validation, or executing approved Creo/G-POST does not invoke AI. Only an explicit Post Builder drafting action may invoke the configured provider. Output is advisory, structured, cited, auditable, and remains a draft pending engineer review.

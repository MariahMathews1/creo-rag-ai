# Translation AI data-transmission boundary

Every external translation-AI call passes through `AIProcessingPolicy`. Retrieval alone is internal and never invokes Azure.

## May be sent

- machine ID, display name, type, controller, selected profile revision, axis count, and relevant configured limits;
- minimal aligned CL/G-code excerpts from `verified_successful` TranslationExamples whose `ai_processing_allowed` value is explicitly true;
- selected post revision and operation metadata;
- the new CL segment deliberately entered by the user;
- example IDs, alignment coverage, and versioned output instructions.

## Must not be sent by default

- candidate, reviewed, invalid, or deprecated examples;
- examples without AI-processing consent;
- examples from another machine unless the user explicitly enables same-controller fallback and the authoritative machine profile confirms that controller match;
- entire manuals or document chunks;
- unrelated historical programs or complete files when aligned excerpts suffice;
- database credentials, API keys, tokens, tenant secrets, or endpoint secrets;
- local filesystem paths or original filenames;
- source provenance and work-order metadata not required for interpretation;
- hidden chain-of-thought.

## Consent and invocation

Consent is record-level and requires an explicit acknowledgement and reviewer label. No bulk-enable operation exists. Opening a page, importing a pair, validating code, opening G-POST, or retrieving examples never invokes Azure. Only the **Generate AI Interpretation** action may invoke the configured provider.

External output is advisory and read-only. It cannot modify G-POST mappings, machine profiles, verification states, or deterministic findings.

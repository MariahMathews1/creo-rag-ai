# Approved-program architecture

`ReferenceProgram` is the governed record for a previously reviewed program.
It associates immutable source text and SHA-256 integrity with a machine-profile
revision, controller, post revision, part/operation, program type, approval
label, applicability, validation summary, eligibility decision, and external-AI
permission. A corresponding `SourceDocument` records the approved-program
source category, but the reference record owns program governance.

Import never means approved or eligible. The lifecycle is:

1. import as `pending`;
2. parse with `gcode-parser-v1` and validate with `validation-v1`;
3. inspect deterministic findings and metadata;
4. explicitly mark eligible or ineligible with a reason;
5. use only compatible eligible records in deterministic extraction.

`ReferenceProgramBlock` preserves every source line, normalized commands,
coordinates, comments, parser errors, and modal state before/after the block.
Program text is never executed and is excluded from routine audit metadata.

Standards are derived through `StandardExtractionRun`, reviewed as
`StandardConvention` proposals with `StandardConventionEvidence`, and copied
into a versioned `OrganizationalStandardProfile`. Comparisons use
`ProgramComparisonRun` and `ProgramComparisonFinding`; deterministic
`AnalysisFinding` records remain a separate evidence layer.


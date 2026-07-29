# Reference-program governance

Use only programs whose external review provenance can be identified. Record
the exact machine revision, controller/version, post revision, part/operation,
units, options, tooling, workholding, and coordinate-system context. Do not mix
incompatible scope automatically.

Approval labels are metadata, not trust decisions. Eligibility is a separate,
explicit local decision made after parsing, deterministic validation, and scope
review. Deprecation and ineligibility preserve the record and make dependent
standards/comparisons stale.

SHA-256 hashes provide change detection, not authenticity. Uploaded program
text is never executed. Routine audit events include record IDs, hashes,
versions, and decisions—not source program text. `ai_processing_allowed`
defaults to false; no external AI provider is used by the local deterministic
Phase 6 workflow.

Similarity to a previously approved program does not certify machining safety,
post-processor correctness, setup correctness, or production readiness.
Qualified review and simulation remain required.


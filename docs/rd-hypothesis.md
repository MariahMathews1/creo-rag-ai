# Revised R&D hypothesis

> A model or retrieval-assisted system given verified machine-specific CL/G-code examples should reproduce site-specific post-processing behavior more reliably than a system attempting to infer that behavior from technical manuals alone.

## Experimental unit

The unit of evaluation is the same Creo CL/NCL input translated for the same immutable machine-profile revision, controller/version, and post revision. Existing approved post output is the reference; future AI output is a draft candidate. Evaluation must stratify results by machine, post revision, operation type, and command coverage.

## Future measurable criteria

- command and sequence agreement;
- tool-call and tool-offset agreement;
- spindle state, direction, mode, and speed agreement;
- coolant-state agreement;
- feed value and feed-mode agreement;
- work-offset agreement;
- coordinate agreement within declared tolerance;
- modal-state agreement at corresponding boundaries;
- missing generated blocks;
- additional generated blocks;
- parser diagnostics and deterministic validation findings;
- unsupported and uncertain translation counts;
- retrieval scope and exact-machine evidence coverage.

Metrics must distinguish syntactic differences from modal equivalence and safety-relevant differences. Aggregate scores must not hide machine-specific failures. Benchmark execution is deferred; see [AI post benchmark design](ai-post-benchmark-design.md).

## Falsification and success criteria

The hypothesis is weakened if manual-only or deterministic baselines consistently equal or outperform retrieval-assisted translation, if results do not improve with exact-machine examples, or if deterministic violations and unsupported segments remain unacceptable.

A later experiment should define thresholds before running the held-out evaluation. No current feature or passing test establishes the hypothesis.

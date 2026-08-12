# Translation alignment

The Phase 8 aligner proposes reusable, example-owned CL/G-code span links. It checks relative sequence and deterministic signals including tool number, spindle speed/event, feed, coolant, rapid/motion coordinates, and program end. Structured reasons such as `same_tool_number`, `same_spindle_speed`, `coolant_event`, and `adjacent_sequence` explain each proposal; no hidden reasoning is stored.

Proposals are never auto-confirmed. Reviewers can confirm, reject, edit, or create links through the alignment APIs. Null on one side explicitly represents suppressed CL or post-generated/unmatched G-code. A common `RAPID` + `GOTO` → one `G00` is many-to-one; the model also supports one-to-many and many-to-many manual spans.

Coverage is a dataset-quality indicator only. It is not a safety or correctness score.

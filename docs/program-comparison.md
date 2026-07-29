# Program comparison

Only an explicitly approved, non-cross-machine organizational standard can be
used for comparison. `comparison-v1` evaluates each accepted convention against
normalized blocks and returns `matches`, `differs`, `missing`, `unexpected`,
`not_applicable`, or `insufficient_context` semantics with exact line data where
available.

Results are deliberately separated:

- deterministic validation findings describe configured machine/controller
  rule results;
- organizational convention findings describe differences from reviewed
  historical examples;
- manual-based explanations remain citation-grounded document retrieval.

Similar-program retrieval uses machine revision and normalized command-family
overlap. Its percentage is a retrieval ranking, never a correctness or safety
score. The side-by-side view uses deterministic sequence alignment to label
common, added, removed, and changed sections.

Reviewers may classify differences as expected exceptions, operation/post/option
differences, intentional choices, investigation items, proposed standard
updates, or unknown. One exception never changes a standard automatically.
Reports support JSON, Markdown, and CSV and always include the Phase 6 safety
boundary.


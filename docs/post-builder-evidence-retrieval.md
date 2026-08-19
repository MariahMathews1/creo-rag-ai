# Post Builder evidence retrieval

`PostBuilderEvidenceRetrievalService` is deterministic and machine-isolated. It searches processed chunks only from the draft's machine, only from eligible machine/controller document types, only when `ai_post_builder_allowed=true`, and only within the draft's selected-document scope when one exists.

Each section has a controlled vocabulary. Matching terms produce a stable relevance score and citation containing document/chunk ID, title/type, page range, section, excerpt, matched terms, and conflict labels. Evidence is retrieved locally; retrieval itself never calls a provider.

At generation time the API recomputes the eligible allowlist. Requested evidence outside that list is rejected. Provider-returned evidence IDs must be a subset of the supplied IDs or the response fails with `INVALID_AI_EVIDENCE_REFERENCE`. Evidence from another machine, a disabled document, a prohibited source type, or an unprocessed document cannot enter context.

Conflict labels prompt human review; retrieval does not decide which source is correct. The approved profile remains authoritative machine context, while documents are supporting technical evidence.

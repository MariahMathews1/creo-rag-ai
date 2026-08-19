# Post section domain model

`PostSectionDraft` belongs to one `GPostDraft` and is identified by `section_key` plus an increasing `section_version`. It stores the frozen machine-context snapshot, proposed templates, missing information, assumptions, warnings, evidence snapshots, provider metadata, and review aggregate. Regeneration inserts a new row; it does not overwrite history.

`PostRuleDraft` belongs to one section draft. It preserves both `ai_draft_template` and any later `engineer_template`, along with required machine facts, evidence IDs, warnings, assumptions, reviewer identity, reason, and timestamps. Rule states are `needs_review`, `accepted`, `edited_and_accepted`, `rejected`, and `needs_more_information`.

Section status is derived from its rules: unresolved information or rejection remains visible; a section is accepted only when all rules have an accepted state. A whole-post version clones the latest section per key and every rule decision. Cycles are represented in readiness only until a future governed milestone defines their evidence and validation requirements.

`SourceDocument.ai_post_builder_allowed` defaults to false. Changing it is an explicit acknowledged, audited machine-level evidence policy decision; it does not make every excerpt relevant or bypass document processing readiness.

# G-POST versioning

G-POST versions are separate draft records. `Save New Version` copies the selected machine/revision snapshot, templates, source selections, mappings, review state, and evidence. The prior record becomes `superseded` and is read-only.

Version comparison reports mappings added/removed, shared templates changed, mapping references or overrides changed, conditions changed, evidence changed, warnings added, and warnings resolved. Drafts can be compared only when their machine and draft name match. New versions use the next monotonic number and preserve older snapshots as read-only records.

Allowed lifecycle values are `draft`, `under_review`, `review_required`, `validated_for_rnd`, `superseded`, and `archived`. Production-oriented status names are intentionally absent.

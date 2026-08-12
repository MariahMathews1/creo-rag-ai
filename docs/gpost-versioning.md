# G-POST versioning

G-POST versions are separate draft records. `Save New Version` copies the selected machine/revision snapshot, templates, source selections, mappings, review state, and evidence. The prior record becomes `superseded` and is read-only.

Version comparison reports mappings added/removed, output templates changed, conditions changed, evidence changed, warnings added, and warnings resolved. Drafts can be compared only when their machine and draft name match.

Allowed lifecycle values are `draft`, `under_review`, `review_required`, `validated_for_rnd`, `superseded`, and `archived`. Production-oriented status names are intentionally absent.

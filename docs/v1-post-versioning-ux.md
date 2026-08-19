# V1 Post Versioning UX

A version is an immutable snapshot in one logical post lineage. The Versions screen contains only ancestors and descendants connected through `created_from_draft_id`; unrelated drafts for the same machine never appear.

Version numbers are assigned by the backend from the maximum version in that lineage, producing monotonic `v1`, `v2`, `v3`, and so on. The current version is distinguished from historical read-only versions.

Create Version compares the current assembled snapshot—including component state, rules, mappings, evidence, and templates—with the latest saved snapshot. If nothing meaningful changed, the API returns `GPOST_NO_VERSION_CHANGES` and the interface reports “No changes since vN.”

The former repeated-v1 defect was caused by the Versions interface loading all draft records for the machine. Those records were separate logical drafts and each correctly began at v1, but they were incorrectly presented as revisions. Lineage-scoped retrieval fixes the relationship at its source rather than relabeling records in the browser.

Duplicate intentionally starts a separate logical post at v1. Posts participating in a lineage must be archived instead of permanently deleted so version retention remains intact.

# V1 Post Statuses

| Status | Meaning |
| --- | --- |
| Setup | The post exists but no required configuration area has been drafted. |
| Building | Work has started and no blocking information gap is present. |
| Needs Information | At least one required area is blocked by missing machine knowledge or evidence. |
| Ready for Review | All required areas are drafted and require engineering review. |
| Reviewed R&D Draft | All required areas have completed review. This is not production approval. |
| Archived | The logical post is retained but removed from the default active view. |

Component status is derived from its latest persisted section state and deterministic readiness information. Overall status is derived by the assembled-post endpoint; the frontend does not invent lifecycle state.

“Ready to Draft” means sufficient approved machine knowledge and evidence exists for an AI-assisted proposal. It does not mean approved, validated for a machine, or production-ready.

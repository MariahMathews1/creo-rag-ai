# V1 Machine Knowledge Demo

Machine Knowledge is the reviewed engineering context used to prepare the OFG checklist.

The V1 demo separates two states:

- **Proposed Facts** are evidence-backed candidates awaiting an engineer. An engineer may Confirm, Edit & Confirm, or Reject each candidate.
- **Confirmed Machine Knowledge** contains reviewed facts and shows which OFG setting consumes each fact.

Each source displays a readable document name and location. **View Source** opens the supporting document; internal extraction metadata is intentionally omitted from the primary workflow.

The fictional KLS dataset includes confirmed 2,000 RPM, M03, M04, and M05 facts. G74 behavior remains proposed because the fictional manual is ambiguous. Its open question routes the engineer either to review or to a machine-scoped Machine Assistant query.

When no candidates exist, the page says: “No proposed facts yet. Upload documentation or enter a machine fact manually.” This is a normal workflow state, not an error.

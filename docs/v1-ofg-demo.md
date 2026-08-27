# V1 OFG Demo

OFG Configuration maps confirmed machine knowledge into the settings the NC programmer needs to establish in the G-POST Option File Generator. It is an engineering checklist, not a native option file.

The V1 status vocabulary is deliberately limited to:

- Unmapped
- Mapped
- Needs Review
- Needs Information
- Reviewed
- Custom Logic Required

The setting detail makes provenance visible as `Manual / Document → Machine Fact → OFG Setting`. It shows source values, review status, document location, and a link back to Machine Knowledge.

OFG menu paths are shown only when verified. The demo uses **Not Yet Verified** instead of inventing a native menu location.

Applied site standards are explicit. When machine evidence and a shop standard differ, both values are presented for engineering review. A Custom Logic Required callout records why standard OFG configuration is insufficient and links to the Custom Logic record. It does not claim a certain FIL/CIMFIL implementation.

When nothing has been mapped, the page says: “No settings mapped yet. Confirm Machine Knowledge to begin.”

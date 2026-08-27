# Post Development Package

The package includes validation policy/gate state, configuration and engineer review records, normalized G-POST diagnostic summaries, validation findings, VERICUT metadata, and version traceability. It excludes CL/NCL, CAD, production NC, VERICUT project data, and full diagnostic files by default; only reviewed metadata, hashes, and references are exported.

The realistic V1 export is a **Post Development Package**, not a native G-POST post. It contains machine summary, reviewed Machine Knowledge, OFG checklist and mappings, Site Standards, Custom Logic, Open Questions, validation metadata, sources, review state, and version metadata.

Formats are Markdown engineering report, R&D JSON, and CSV OFG checklist. CSV columns are Category, Setting, Value, Status, Source, OFG Menu Path, Custom Logic Required, and Engineer Note.

Every format states native integration is unverified and final implementation/compilation remains in the governed Creo G-POST / Option File Generator environment.

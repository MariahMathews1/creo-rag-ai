# V1 Export Demo

**Export Package** opens a review step before downloading the Post Development Package. The package contains:

- OFG Configuration Checklist
- Reviewed Machine Knowledge
- Applied Site Standards
- Custom Logic Summary
- Open Questions
- Review Summary
- Validation Records
- Sources / Evidence
- Version Metadata

The package supports post development and engineering handoff. It is not currently a native G-POST postprocessor file and does not authorize machine use.

Markdown is the primary readable handoff format. JSON supports downstream local tooling and audit workflows. Both preserve Post Record and version context.

Before export, use **Review** to resolve or acknowledge the outstanding queue and record any G-POST test, VERICUT, and engineer-review results. The application stores those records but does not run external validation tools.

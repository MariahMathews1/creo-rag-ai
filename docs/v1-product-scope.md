# V1 Product Scope

## Product statement

Creo NC Post Assistant V1 is a **pre-Azure R&D proof of concept** for producing a traceable engineering Post Development Package from reviewed machine/controller knowledge. It demonstrates the workflow without requiring AI or ML.

## Visible product

- Dashboard
- Machines and immutable reviewed revisions
- Documents and deterministic extraction status
- Machine Knowledge proposal/review
- Post Builder and Post Records
- OFG Configuration with provenance and contextual Site Standards
- Custom Logic tracker
- Review & Export
- History & Sources
- cited Machine Assistant retrieval

## Core record chain

`Machine → reviewed revision + documents → Machine Knowledge → OFG Configuration → standards/custom logic → review/validation → versioned package`

## Outputs

V1 exports a Markdown Engineering Report, CSV OFG checklist, and R&D JSON package. These are development/handoff artifacts, not compiled or native G-POST postprocessor files.

## Explicitly out of scope

- Azure OpenAI integration and autonomous AI approval
- native Option File generation or compilation
- execution of Creo, G-POST/OFG, or VERICUT
- production qualification
- normal-product ingestion of CL, NCL, ACL, APT, G-code/NC, CAD, STEP, IGES, part geometry, toolpaths, or production programs
- unverified claims about OFG menu names, `.pNN`/`.fNN` lifecycle, or FIL/CIMFIL compilation

## Authority and acceptance

Machine revisions provide authoritative context. Documents provide evidence. Engineers confirm facts and settings. Site standards are applied explicitly. Deterministic code enforces status, mapping, export, validation, and governance rules. Future AI remains advisory.

V1 succeeds when a user can follow the primary workflow, distinguish confirmed from proposed, trace settings to evidence, see uncertainty, and export a coherent handoff. Production correctness still requires the installed local toolchain and qualified personnel.

# Creo NC Post Assistant

**V1 R&D proof of concept · pre-Azure**

Creo NC Post Assistant is a local engineering workflow for organizing the information needed to develop a machine-specific Creo G-POST postprocessor. It turns machine/controller documentation, reviewed facts, site practices, configuration decisions, open questions, and validation records into a traceable Post Development Package.

The V1 works without generative AI or machine learning. It does not create, compile, or qualify a native production postprocessor.

## What This Application Is

The application is an engineering workbench for NC programmers and post developers. Its main record is a **Post Record**, which connects one reviewed machine configuration, its source documents, Machine Knowledge, an OFG Configuration checklist, site practices, possible custom behavior, open questions, validation evidence, and versioned handoff information.

The primary visible navigation is Dashboard, Machines, Documents, Post Builder, and Machine Assistant.

## What Problem It Solves

Post development usually depends on facts distributed across manuals, machine specifications, local practices, and engineer experience. It can be difficult to see which values are confirmed, where they came from, what they affect, and what still needs investigation.

This application keeps those decisions in one reviewable chain:

`Document evidence → Machine Knowledge → OFG setting → site/custom decision → review → export`

## What It Does Not Do

V1 does not:

- generate or compile a native G-POST Option File or executable post;
- claim that an OFG menu path is correct unless a local engineer verifies it;
- replace G-POST, Option File Generator, Creo, VERICUT, or engineering review;
- qualify a post for production or automatically execute external validation tools;
- send data to Azure OpenAI—Azure integration has not been enabled;
- ingest production CL/NCL, NC/G-code, CAD geometry, or toolpaths in the normal V1 product.

Exports are engineering development artifacts, not machine-ready files.

## Current V1 Workflow

1. Add a machine.
2. Upload machine/controller documents.
3. Extract proposed facts using local deterministic processing.
4. Have an engineer review Machine Knowledge.
5. Create a Post Record from the reviewed machine revision.
6. Map and review the OFG Configuration checklist.
7. Apply relevant site standards.
8. Identify behavior that may require Custom Logic.
9. Resolve outstanding facts, settings, questions, and review findings.
10. Export the Post Development Package.
11. Implement, compile, simulate, and test through the real local G-POST/OFG/Creo/VERICUT environment.

## Application Screens

### Dashboard

The Dashboard summarizes machines, documents, Post Records, and items needing attention. The user clicks the most relevant next action; the app reads status counts from the database and routes into the primary workflow. The result is orientation, not a second administrative workspace.

### Machines

Machines is the authoritative list of machine/controller contexts. The user sees the machine, type, controller, knowledge readiness, status, and a Demo badge for fictional samples. **Add Machine** creates a local profile. Opening a machine shows a compact overview and a clear **Review Machine Knowledge** next step.

The app stores machine limits, controller identity, supported codes, templates, revision history, and archive state. A reviewed revision—not a mutable screen value—is pinned to a Post Record.

### Machine Knowledge

A **Proposed Fact** is an extracted or entered value that has not been accepted. A **Confirmed Fact** has been explicitly reviewed by an engineer. Each row shows its source and **Used By** relationship.

Example:

`Manual p.42 → Maximum Spindle RPM = 2000 → engineer confirms → OFG / Maximum Spindle Speed`

The user opens the review drawer, checks evidence, edits if needed, and confirms, rejects, or leaves the value for more information. The app stores the value, unit, status, reviewer, note, source document/location, timestamp, and downstream mappings. Confirmation is a human action.

### Documents

Documents is a compact machine-scoped library. The user uploads PDF, TXT, or Markdown evidence, then sees document type, extraction status, advisory-AI availability, and contextual actions. Local parsing stores extracted text, pages/chunks, file metadata, and processing status. **Extract Knowledge** starts the machine-fact workflow; **Ask Machine Assistant** uses the same machine boundary.

### Post Builder

Post Builder lists Post Records and provides a three-step create flow: select the machine, select reviewed sources/context, then confirm the Post Record. It stores a pinned machine revision, snapshots, selected documents, initial mappings, status, and version lineage. The user receives a dedicated development workspace rather than a compiled post.

### Post Record Overview

Overview answers: What is complete? What needs attention? What should happen next? It shows Machine Knowledge, OFG Configuration, Site Standards, Custom Logic, Open Items, and Current Status. A single primary action routes to the next unresolved area.

### OFG Configuration

OFG Configuration is an engineering checklist of settings believed necessary in G-POST Option File Generator. It is **not** the native Option File.

The table shows setting, value, source, review status, custom-logic need, and action. Opening a setting exposes the full traceability chain, any applied standard, menu-path verification, and engineer notes. Unknown menu names stay **Not Yet Verified**. The app stores evidence IDs, value/unit, status, reviewer, notes, standards, possible custom-logic link, and verified/unverified menu location.

Site Standards appear contextually within this area because they affect configuration decisions. They are not a separate primary product module.

### Custom Logic

Some machine/site behavior may not fit the standard OFG checklist. Those behaviors become **Custom Logic items** with a reason, desired result, evidence, applicable site standard, possible runtime trigger, review state, and notes.

FIL/CIMFIL is a potential implementation mechanism only where the installed local environment confirms it. The app does not claim a native filename, lifecycle, compile path, or association method that has not been verified.

### How OFG Configuration Works

OFG Configuration is a machine-specific engineering checklist grounded in the collected [`OFG.md`](OFG.md) reference. A single backend catalog evaluates relevance from machine type, controller context, axis count, reviewed capabilities, and explicit engineer selections. A simple lathe or three-axis mill therefore sees its relevant core and conditional settings by default; multi-axis, right-angle-head, Siemens/UG, and custom areas remain behind **Show Advanced settings**.

Simple trace: `Controller Documentation → Machine Knowledge → OFG setting → engineer review`.

Advanced trace: `Machine capability + Site Standard → advanced OFG setting → Custom Logic reference → local site verification`.

OFG paths are labeled **Verified From OFG Reference**, **Site Verification Needed**, or **Not Verified**. These labels describe research support and never imply verification in an installed site environment. The **Suggested OFG Starting Point** shown during post creation is initialization metadata only; the app does not import a CamLib template or generate a native option/FIL file. See [docs/ofg-domain-map.md](docs/ofg-domain-map.md).

### Review & Export

Review & Export combines completion, outstanding items, manually recorded validation stages, and package exports. Engineers resolve issues or record evidence, then download an Engineering Report (Markdown), OFG Checklist (CSV), or R&D JSON.

The package includes machine summary, confirmed Machine Knowledge, OFG checklist, applied standards, custom-logic summary, verified reviewed FIL source if available, questions, review summary, validation records, sources, and version metadata.

**This package supports engineering development and handoff. It is not currently a compiled or native G-POST postprocessor file.**

### History & Sources

This screen combines read-only version history and selected source documents. **Create Version** captures a meaningful package checkpoint. Historical versions can be opened or compared; source documents link back to extracted evidence.

### Machine Assistant

Machine Assistant retrieves technical information from the selected machine's processed documents. It returns an advisory answer with citations and a Sources section. It does not approve Machine Knowledge or create final post logic. If evidence is insufficient, it says so instead of inventing an answer.

## End-to-End Demo Walkthrough

The canonical fictional walkthrough is **KLS-1840N Demo** with **KLS-1840N FANUC Demo Post**.

1. Open **Machines**. Explain that the machine is the authoritative context. Open the KLS demo and click **Review Machine Knowledge**.
2. Show confirmed spindle facts. Open **Maximum Feed Rate**, which intentionally needs review. Point out source, status, reviewer controls, and downstream traceability.
3. Open **Documents**. Show **KLS Machine Manual — Fictional Demo**, extraction status, and contextual actions.
4. Open **Post Builder**, then the demo Post Record. Explain that its status remains **Building** because uncertainty is visible.
5. On **Overview**, show completion counts, outstanding work, and the recommended next action.
6. Open **OFG Configuration**. Show reviewed spindle mappings and an unverified setting. Open a row to demonstrate source-fact traceability, Not Yet Verified menu location, engineer notes, and the applied Tool Change Safe Retract standard.
7. Expand contextual **Site Standards** and explain that application is explicit.
8. Open **Custom Logic**. Show **G74 Grooving Behavior** and the cautious potential FIL/CIMFIL wording.
9. Open **Review & Export**. Show **Confirm exact G74 behavior**, validation placeholders, package contents, and the native-post disclaimer.
10. Open **History & Sources**, then explain version checkpoints and source lineage.
11. Optionally ask Machine Assistant a spindle-limit question and open its citation.

The presentation script is in [docs/demo-walkthrough.md](docs/demo-walkthrough.md).

## Example: New Machine to Post Development Package

For a real machine, create its profile, upload approved references, review each proposed fact, and approve a revision. Create the Post Record, work through OFG settings, apply local standards, and flag uncertain behavior as Custom Logic. Resolve or explicitly retain open items, record external test results, then export the package for the local post developer. Do not treat the export as the compiled deliverable.

## What the Output Contains

Markdown is intended for human review and handoff, CSV for OFG-checklist work, and JSON for controlled R&D inspection/integration. Each retains status and provenance rather than silently converting proposals into facts.

## Relationship to Creo / G-POST

- **This app:** develops and organizes engineering information for the post.
- **Option File Generator / G-POST:** creates and compiles the actual post in the installed site environment.
- **Creo:** uses the resulting qualified post during NC processing.
- **VERICUT:** may be used externally for CNC simulation and verification.

The app supports this toolchain; it does not replace any component.

## Where Generative AI Fits

Future Azure OpenAI use may help interpret machine/controller documentation, suggest Machine Knowledge facts, identify missing information, suggest OFG mappings, explain settings, or draft Custom Logic/FIL where policy permits. AI output will remain proposed and advisory. Engineer review will remain required. Azure OpenAI is not integrated in this milestone.

## Where Machine Learning Fits

Optional ML may assist document classification, table localization, scanned-document processing, parameter extraction, or document-section classification. ML is not required for the core application.

## What Remains Deterministic

Python/rule-based components handle PDF/text parsing, regular expressions, table extraction, unit normalization, database mappings, status rules, export generation, local validation, and governance enforcement. These remain inspectable and testable if AI is added later.

## Governance / Sensitive Data Boundary

Normal V1 does not ingest or send to AI: CL, NCL, ACL, APT, G-code/NC files, CAD, STEP, IGES, part geometry, toolpaths, or production programs. Those artifacts and prior translation research are outside the visible V1 product. AI is disabled by default, and future use must remain machine-scoped, explicitly authorized, provenance-aware, and advisory.

## Current R&D Limitations

- Native Option File structure and import/export behavior remain unverified.
- Actual OFG menu/panel labels vary by installed environment and are not assumed.
- Native `.pNN`/`.fNN` handling and FIL/CIMFIL association/compilation remain site research.
- External G-POST, Creo, and VERICUT operations are manually recorded, not executed.
- Scanned PDFs may need OCR.
- The canonical walkthrough is fictional and must never be used on a machine.

## Future Research Questions

Research must establish the exact native Option File representation, OFG import/export capability, `.pNN`/`.fNN` lifecycle, which settings OFG handles directly, which behaviors require FIL/CIMFIL, how custom FIL is associated and compiled locally, actual menu/panel names, and whether editable native-post export is feasible. See [docs/gpost-research-questions.md](docs/gpost-research-questions.md).

## Running the Application

Prerequisites: Python 3.12, Node.js 20+, npm, and Make (optional). No Azure credentials are required.

### macOS/Linux

```bash
cp .env.example .env
make install
make migrate
make reset-v1-demo
make dev
```

Open `http://localhost:5173`. The API and Swagger UI run at `http://localhost:8000` and `http://localhost:8000/docs`.

### Windows 11 (PowerShell)

From the extracted project folder:

```powershell
Copy-Item .env.example .env
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location frontend
npm install
Set-Location ..
backend\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
Set-Location backend
.venv\Scripts\python.exe -m app.scripts.reset_v1_demo
```

Start two PowerShell terminals from the project folder:

```powershell
# Terminal 1
Set-Location backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

```powershell
# Terminal 2
Set-Location frontend
npm run dev
```

If `py -3.12` is unavailable, install Python 3.12 and enable its launcher. Activation is unnecessary because these commands call the virtual-environment Python directly.

## Demo Data

Run the safe, repeatable reset:

```bash
make reset-v1-demo
# or
cd backend && .venv/bin/python -m app.scripts.reset_v1_demo
```

The command prints its target, refuses production-like or non-SQLite databases by default, archives only known disposable legacy demos, retains user data/schema/migrations, and restores one fictional walkthrough. Run it twice to verify idempotence. Never use `--allow-non-development-database` without independently verifying the target.

Browser storage uses an application version marker and clears only obsolete app-owned keys; unrelated site storage is preserved.

## Testing

```bash
make test
make build
```

Individual checks:

```bash
cd backend && .venv/bin/python -m pytest
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
git diff --check
```

Product boundaries are summarized in [docs/v1-product-scope.md](docs/v1-product-scope.md).

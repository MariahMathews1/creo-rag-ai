# Creo NC Post Assistant

> Developer handoff, maintenance guide, debugging walkthrough, and reconstruction specification

Creo NC Post Assistant is a local-first internal proof of concept for reviewing
Creo cutter-location data, post-processed G-code, uploaded machine documentation,
machine-profile extraction, and organizational programming patterns.

The application combines deterministic analysis with citation-backed and
historical evidence. It is deliberately a decision-support tool—not a CNC
simulator, post-processor certifier, collision checker, or production approval
system.

> **Mandatory safety boundary**
>
> This application does not certify CNC programs for production. A result such
> as `passed`, high confidence, high documentation coverage, successful
> traceability, or similarity to an approved program does not prove machining
> safety, setup correctness, post-processor correctness, collision freedom, or
> production readiness. Qualified review, controlled documentation, machine and
> setup verification, and appropriate simulation remain required.

All bundled profiles, manuals, CL/NCL files, G-code programs, standards, and
approved-program examples are fictional or public test material and must not be
used to operate machinery.

---

## 1. Project status

This repository contains a working proof of concept through Phase 10:

| Phase | Capability | Current state |
| --- | --- | --- |
| 1 | Machine profiles and deterministic G-code validation | Implemented |
| 2 | Persistent analyses, findings, frontend workflow, and Docker setup | Implemented |
| 3 | Document processing and citation-grounded manual assistance | Implemented |
| 4 | Creo CL/NCL parsing and CL-to-G-code traceability | Implemented |
| 5 | Citation-backed machine-profile extraction and revision governance | Implemented |
| 5 UX | Guided queues, filters, batch safeguards, evidence drawer, URL state | Implemented |
| 6 | Approved-program governance, standard extraction, and comparison | Implemented |
| G-POST prototype | Machine-scoped draft generation, review, preview, and versioning | Implemented R&D tool |
| Phase 7 preparation | Verified CL/G-code translation dataset architecture | Documented; runtime deferred |
| Phase 8 | Governed paired translation dataset, alignment review, and explorer | Implemented |
| Phase 9 | Canvas toolpath visualization and visual traceability | Implemented |
| Phase 10 | Controlled Azure OpenAI provider and internal translation retrieval | Implemented; mock default |

This is not production software. Authentication, authorization, enterprise
document control, encrypted program storage, formal electronic signatures,
malware scanning, qualified simulation integration, and full CNC semantics are
outside the current proof-of-concept boundary.

### Revised R&D Direction — CL/G-Code Translation Learning

The primary research hypothesis is now that site-specific Creo CL/NCL → G-code behavior should be learned and retrieved from **verified historical CL/G-code pairs** for the exact machine and post context. Technical manuals remain important supporting evidence for documented syntax, capability, parameters, and limits, but they do not by themselves describe the organization's actual post output.

Machine-profile revisions remain authoritative exact-machine context. Deterministic parsers and validation rules remain authoritative checks on every future candidate. Manual Assistant remains internal document Q&A, not a model that learns the post processor. The existing G-POST Generator remains an R&D configuration, mapping, and deterministic-preview tool and may later consume historical translation evidence separately from manual evidence.

Azure OpenAI now has a controlled, optional explanation-only provider boundary. The default remains deterministic mock mode; Azure is never contacted unless configured and a user explicitly requests an interpretation or connectivity check. Only verified-successful, exact-machine, explicitly consented TranslationExample excerpts may enter external context. Public-web retrieval, full-program AI G-code generation, automatic G-POST changes, and fine-tuning remain disabled. Production deployment still requires separate organizational security, data-processing, validation, and operational approval.

### Current automated verification baseline

At the time of this handoff:

```text
Backend: 104 tests passing
Frontend: 52 tests passing
Frontend TypeScript check: passing
Frontend production build: passing
Database migration head: 20260814_01
```

---

## 2. What the system does

The major workflows are:

1. Define a machine and controller profile.
2. Create a versioned, immutable machine-profile revision.
3. Paste or load G-code and run deterministic validation.
4. Review exact line findings by severity and category.
5. Upload manuals and specifications.
6. Extract, page, chunk, hash, search, and cite uploaded documents.
7. Ask questions grounded only in uploaded documents.
8. Parse Creo CL/NCL and G-code while preserving source lines.
9. Infer and review CL-to-G-code relationships.
10. Extract citation-backed machine-profile field proposals.
11. Resolve conflicts, ambiguity, missing fields, and machine variants.
12. Create an inactive machine-profile draft and explicitly approve it.
13. Import previously reviewed CNC programs with governance metadata.
14. Parse and validate reference programs without executing them.
15. Explicitly decide which reference programs are eligible for pattern analysis.
16. Extract recurring programming conventions deterministically.
17. Review supporting, contradicting, and contextual program-line evidence.
18. Create and explicitly approve a versioned organizational standard.
19. Compare a new program to deterministic rules and organizational conventions.
20. Retrieve similar eligible references and inspect side-by-side differences.
21. Classify intentional exceptions without automatically changing the standard.
22. Export traceability, standard, and comparison reports.
23. Create a versioned, machine-scoped G-POST R&D draft.
24. Review CL mappings and supporting document, standard, and reference evidence.
25. Generate advisory G-code, reparse it, run deterministic validation, and inspect block traceability.
26. Compare draft versions and export explicitly non-production JSON or Markdown.
27. Import paired CL/NCL and historical G-code against an exact machine revision.
28. Review flexible span alignment, unmatched records, provenance, and deterministic findings.
29. Explicitly verify historical pairs and explore confirmed patterns without merging machine/post contexts.
30. Review programmed CL/G-code motion in XY/XZ/YZ with alignment and deterministic-finding overlays.
31. Preview exact-machine verified translation retrieval without invoking AI.
32. Explicitly request a structured mock or Azure advisory interpretation and inspect its example provenance and invocation audit.

> **Toolpath boundary:** Toolpath Visualization represents parsed programmed motion only. It is not material-removal simulation, collision detection, final-part prediction, or machining verification.

The fictional Phase 8 demo can be loaded from `backend/` with:

```bash
python -m app.scripts.seed_translation_demo
```

---

## 3. Technology stack

### Backend

| Component | Version/choice | Purpose |
| --- | --- | --- |
| Python | **3.12 recommended and Docker baseline** | Runtime |
| FastAPI | `0.115.8` | HTTP API and OpenAPI |
| Uvicorn | `0.34.0` | ASGI development/production server |
| SQLAlchemy | `2.0.38` | ORM and persistence |
| Alembic | `1.14.1` | Database migrations |
| Pydantic | `2.10.6` | Request/response and settings validation |
| pydantic-settings | `2.7.1` | Environment configuration |
| SQLite | Local file | Proof-of-concept database |
| pypdf | `5.3.0` | PDF text extraction |
| pytest/httpx | `8.3.4` / `0.28.1` | API and service tests |

### Frontend

| Component | Version/choice | Purpose |
| --- | --- | --- |
| Node.js | 20+; Docker uses 22 | Tooling/runtime |
| React | `^19.0.0` | UI |
| React Router | `^7.1.5` | Routing and URL state |
| TypeScript | `~5.7.2` | Static typing |
| Vite | `^6.1.0` | Development server and build |
| Vitest | `^3.0.5` | Frontend tests |
| Testing Library | React/user-event/jest-dom | Behavioral component tests |
| Nginx | `1.27-alpine` in Docker | Static production frontend |

### Python version warning

The supported reproduction target is Python 3.12. Python 3.13 has been used in
the development environment with a compatible dependency cache, but it is not
the declared baseline.

Python 3.14 may fail during SQLAlchemy import with an error similar to:

```text
TypeError: descriptor '__getitem__' requires a 'typing.Union' object
but received a 'tuple'
```

That failure is a dependency/runtime compatibility issue, not application logic.
If Python 3.14 is mandatory, create a separate upgrade branch, update SQLAlchemy,
Pydantic, FastAPI, and related packages to versions explicitly supporting that
Python release, then run the entire backend and frontend suite. Do not reproduce
the baseline with Python 3.14 and assume identical behavior without validation.
Docker is the simplest way to preserve the known Python 3.12 environment.

---

## 4. System requirements

### Minimum development environment

- 64-bit macOS, Linux, or Windows 10/11
- Python 3.12.x
- Node.js 20 or newer
- npm 10 or newer
- Git
- 4 GB RAM minimum; 8 GB recommended
- Approximately 2 GB free disk space before large PDF uploads
- Local ports 5173 and 8000, or explicitly configured alternatives
- Write access to `backend/data/`

### Optional tooling

- Docker Desktop with Compose v2
- GNU Make on macOS/Linux
- SQLite CLI for local diagnostics
- An IDE with Python, TypeScript, ESLint/formatting, and SQLite support

### Runtime assumptions

- The backend and browser run on the same workstation by default.
- SQLite and uploaded documents are local.
- No public web access is required.
- AI and embedding providers default to deterministic local mocks.
- Uploaded CNC source is parsed as text and is never executed.
- This proof of concept assumes one trusted local user; it has no login system.

---

## 5. High-level architecture

```text
┌──────────────────────────────── React + TypeScript ────────────────────────────────┐
│ Dashboard │ Machines │ Analysis │ Documents │ Manual Assistant │ Review Workspaces │
└──────────────────────────────────────┬──────────────────────────────────────────────┘
                                       │ JSON / multipart HTTP
                                       ▼
┌──────────────────────────────── FastAPI API ───────────────────────────────────────┐
│ Machines │ Analyses │ Documents │ Manual Q&A │ Traceability │ Extraction │ Standards│
└──────────────┬───────────────────┬───────────────────────┬──────────────────────────┘
               │                   │                       │
               ▼                   ▼                       ▼
     Deterministic parser   Document pipeline     Review/governance services
     Modal-state tracker    PDF/text extraction   Revisions, evidence, reports
     Validation rules       Chunking/retrieval    Stale-state detection
               │                   │                       │
               └───────────────────┴───────────────────────┘
                                       │
                                       ▼
                             SQLite + local documents
```

### Architectural principles

- Deterministic checks run before advisory or historical interpretation.
- Source lines, file hashes, parser versions, algorithm versions, and evidence
  relationships are persisted.
- Machine-profile revisions and analysis snapshots prevent silent reinterpretation.
- Review status is separate from proposal/extraction status.
- Documentation coverage is separate from review completion.
- Frequency is separate from organizational authority.
- Historical similarity is separate from deterministic safety severity.
- Draft creation is separate from approval and activation.
- Stale results are preserved and labeled rather than deleted.
- External AI transmission requires explicit metadata permission.

---

## 6. Repository layout

```text
.
├── alembic.ini
├── docker-compose.yml
├── Makefile
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── ai/                    # Local advisory provider abstraction
│   │   ├── alignment/             # Deterministic CL/G-code alignment
│   │   ├── api/                   # FastAPI routes
│   │   ├── cl_parser/             # Creo CL/NCL parsing
│   │   ├── core/                  # Environment settings
│   │   ├── db/                    # Engine, sessions, Alembic runner
│   │   ├── documents/             # Extraction, chunking, retrieval, answers
│   │   ├── models/                # SQLAlchemy entities
│   │   ├── parsers/               # Fanuc-style G-code parser
│   │   ├── profile_extraction/    # Typed field registry and extraction
│   │   ├── program_standards/     # Phase 6 extraction/comparison logic
│   │   ├── schemas/               # Pydantic API contracts
│   │   ├── scripts/               # Demo seeders
│   │   └── validators/            # Deterministic validation rules
│   ├── data/                       # SQLite, stored docs, generated reports
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
│       ├── api/client.ts           # Typed API access
│       ├── components/             # Layout, banners, status components
│       ├── features/               # Reusable forms and samples
│       ├── pages/                  # Route-level workflows
│       ├── test/                   # Vitest setup
│       ├── types/index.ts          # Shared frontend types
│       └── styles.css
├── sample-data/
│   ├── manuals/
│   ├── profile-extraction/
│   ├── public-test/kent-kls-1840n/
│   └── approved-programs/fictional-kls-1840n/
└── docs/
```

---

## 7. Persistence model

### Core entities

| Table/domain | Purpose |
| --- | --- |
| `machine_profiles` | Current editable machine/controller configuration |
| `machine_profile_revisions` | Versioned approved/draft/superseded snapshots |
| `analysis_projects` | G-code/CL review project and immutable revision snapshot |
| `analysis_findings` | Deterministic validation findings |
| `audit_events` | Review, approval, source, report, and workflow events |

### Document knowledge

| Table/domain | Purpose |
| --- | --- |
| `source_documents` | Uploaded manuals, specifications, standards, or programs |
| `document_chunks` | Searchable extracted text with page/section provenance |
| `manual_question_sessions` | Grouped manual-assistant conversations |
| `manual_questions` | Question, grounded answer, status, unresolved issues |
| `answer_citations` | Exact document/chunk/page evidence |

### Traceability

| Table/domain | Purpose |
| --- | --- |
| `cl_records` | Parsed CL/NCL records and modal state |
| `gcode_blocks` | Parsed analysis G-code blocks and modal state |
| `alignment_runs` | Versioned inferred mapping run |
| `alignment_links` | CL-to-G-code relationships and review status |
| `alignment_issues` | Unmapped, ambiguous, or transform issues |

### Profile extraction

| Table/domain | Purpose |
| --- | --- |
| `profile_extraction_runs` | Immutable extraction inputs/settings/summary |
| `profile_field_proposals` | Field proposal plus proposal/review states |
| `profile_field_evidence` | Supporting/conflicting citations |
| `machine_profile_field_sources` | Provenance copied into a draft revision |

### Approved programs and standards

| Table/domain | Purpose |
| --- | --- |
| `reference_programs` | Governed historical CNC program and applicability |
| `reference_program_blocks` | Parsed source lines and modal state |
| `standard_extraction_runs` | Compatible eligible dataset and algorithm |
| `standard_conventions` | Proposed or approved convention |
| `standard_convention_evidence` | Supporting/contradicting program lines |
| `organizational_standard_profiles` | Versioned inactive/approved standards |
| `program_comparison_runs` | Analysis-to-standard comparison |
| `program_comparison_findings` | Matches, differences, missing, unexpected, N/A |

### Migration history

```text
20260727_01  Phase 3 manual knowledge
20260728_01  Phase 4 traceability
20260728_02  Phase 5 profile extraction
20260728_03  Controller identity separation
20260729_01  Phase 6 approved-program standards
20260811_01  G-POST Generator domain
20260812_01  G-POST V1 semantics
20260812_02  G-POST data correction and backfill
```

Never edit an applied migration. Add a new revision with the current head as
`down_revision`.

---

## 8. Local installation

### 8.1 Clone and enter the repository

```bash
git clone <repository-url>
cd creo-rag-ai
```

### 8.2 Create the environment file

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

The defaults work when the backend uses port 8000 and the frontend uses 5173.

### 8.3 Backend — macOS/Linux

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd ..
PYTHONPATH=backend python -m alembic -c alembic.ini upgrade head
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 8.4 Backend — Windows PowerShell

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd ..
$env:PYTHONPATH = "backend"
python -m alembic -c alembic.ini upgrade head
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If script activation is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Use `python -m uvicorn`, not `uvicron`.

### 8.5 Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` or the URL printed by Vite.

### 8.6 Verify the backend

- Health: `http://127.0.0.1:8000/api/health`
- OpenAPI UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

Expected health response:

```json
{"status":"healthy","service":"Creo NC Post Assistant API"}
```

### 8.7 Port collision

If port 8000 is occupied:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8011
```

Then start the frontend with the matching API URL:

macOS/Linux:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8011/api npm run dev
```

PowerShell:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8011/api"
npm run dev
```

Do not stop an unknown service merely because it occupies port 8000. Inspect it
first or select another port.

---

## 9. Docker reproduction

Docker is the most reproducible option and fixes Python at 3.12:

```bash
docker compose up --build
```

Open:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

SQLite and uploaded documents persist in the `creo-data` volume.

Stop:

```bash
docker compose down
```

Delete the Docker database and document volume only when intentionally resetting
all Docker-managed data:

```bash
docker compose down -v
```

---

## 10. Environment variables

| Variable | Default | Notes |
| --- | --- | --- |
| `DATABASE_URL` | `.env.example`: `sqlite:///./data/creo_nc_post_assistant.db`; code fallback: `sqlite:///./data/creo_assistant.db` | Relative paths are anchored to `backend/`; copying `.env.example` selects the first filename |
| `CORS_ORIGINS` | localhost/127.0.0.1:5173 | Comma-separated exact origins |
| `DOCUMENT_STORAGE_PATH` | `./data/documents` | Local controlled storage |
| `MAX_DOCUMENT_UPLOAD_MB` | `50` | PDF/text document limit |
| `MAX_PROGRAM_SOURCE_UPLOAD_MB` | `25` | CL/G-code/reference source limit |
| `AI_PROVIDER` | `mock` | Local advisory provider |
| `EMBEDDING_PROVIDER` | `mock` | Local deterministic embedding provider |
| `OPENAI_API_KEY` | empty | Not required in local mock mode |
| `OPENAI_BASE_URL` | OpenAI API URL | Reserved provider boundary |
| `OPENAI_CHAT_MODEL` | empty | Optional future provider configuration |
| `OPENAI_EMBEDDING_MODEL` | empty | Optional future provider configuration |
| `TRANSLATION_AI_PROVIDER` | `mock` | `disabled`, `mock`, or explicit `azure_openai` |
| `AZURE_OPENAI_ENDPOINT` | empty | Server-only approved Azure resource endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | empty | Approved Azure model deployment |
| `AZURE_OPENAI_MODEL` | empty | Optional safe display/audit model identifier |
| `AZURE_OPENAI_AUTH_MODE` | `entra_id` | Entra/managed identity preferred; `api_key` fallback |
| `AZURE_OPENAI_API_KEY` | empty | Optional server-only fallback; never sent to frontend or persisted |
| `TRANSLATION_AI_TIMEOUT_SECONDS` | `20` | External explanation timeout |
| `TRANSLATION_AI_MAX_RETRIES` | `2` | Transient SDK retry limit |
| `DOCUMENT_CHUNK_SIZE` | `900` | Character target |
| `DOCUMENT_CHUNK_OVERLAP` | `150` | Must be smaller than chunk size |
| `RETRIEVAL_TOP_K` | `6` | Manual-assistant retrieval count |
| `RETRIEVAL_MIN_SCORE` | `0.30` | Local relevance threshold |
| `ENABLE_RETRIEVAL_DEBUG` | `false` | Diagnostic retrieval metadata |
| `ALIGNMENT_HIGH_CONFIDENCE` | `0.90` | Traceability display band |
| `ALIGNMENT_MEDIUM_CONFIDENCE` | `0.70` | Traceability display band |
| `ALIGNMENT_MIN_CONFIDENCE` | `0.45` | Traceability minimum |
| `ALIGNMENT_COORDINATE_TOLERANCE` | `0.001` | Coordinate matching tolerance |
| `ALIGNMENT_FEED_TOLERANCE_PERCENT` | `2.0` | Feed comparison |
| `ALIGNMENT_SPINDLE_TOLERANCE_PERCENT` | `1.0` | Spindle comparison |
| `ALIGNMENT_CANDIDATE_WINDOW` | `20` | Candidate search window |
| `ENABLE_ALIGNMENT_DEBUG` | `false` | Alignment diagnostics |
| `PROFILE_EXTRACTION_PROVIDER` | `mock` | Offline structured extraction |
| `PROFILE_EXTRACTION_MODEL` | empty | Optional future model |
| `PROFILE_EXTRACTION_TOP_K` | `8` | Field retrieval count |
| `PROFILE_EXTRACTION_MIN_SCORE` | `0.25` | Field retrieval threshold |
| `PROFILE_EXTRACTION_HIGH_CONFIDENCE` | `0.90` | Priority/display band |
| `PROFILE_EXTRACTION_MEDIUM_CONFIDENCE` | `0.70` | Priority/display band |
| `PROFILE_EXTRACTION_MIN_RECOMMENDED_CONFIDENCE` | `0.45` | Review-note boundary |
| `ENABLE_PROFILE_EXTRACTION_DEBUG` | `false` | Extraction diagnostics |
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | Compiled/browser API base |

Confidence values prioritize review. They are not safety or correctness scores.

---

## 11. Demo and sample data

Run migrations before seeders.

```bash
make migrate
make seed-manual-demo
make seed-traceability-demo
make seed-profile-extraction-demo
make seed-approved-program-demo
```

Without Make:

```bash
cd backend
python -m app.scripts.seed_manual_demo
python -m app.scripts.seed_traceability_demo
python -m app.scripts.seed_profile_extraction_demo
python -m app.scripts.seed_approved_program_demo
```

### Expected Phase 6 demo result

The approved-program demo creates/reuses a fictional KLS-1840N machine, imports
10 programs, uses six compatible POST-A programs for extraction, identifies a
separate POST-B program, creates convention proposals, rejects one weak pattern,
explicitly approves a standard, compares a current program, and exports:

```text
backend/data/approved-program-demo-report.md
```

Expected comparison categories include:

- at least one `matches`
- at least one `missing`
- one `unexpected`
- one `not_applicable`

---

## 12. Complete application navigation and debugging walkthrough

### 12.1 Dashboard — `/`

Expected:

- Counts for machine profiles and analysis projects
- Recent machine and analysis context
- Production-use warning
- A backend-unavailable error when the frontend cannot reach the API

Debug:

1. Open `/api/health`.
2. Verify `VITE_API_BASE_URL` ends with `/api`.
3. Confirm the backend port.
4. Inspect browser Network requests for CORS or connection failures.

### 12.2 Machine profiles — `/machines`

Use this page to create the configuration used by deterministic validation.

Required inputs include:

- Name, manufacturer, model
- Controller identity/version
- Machine type and axis count
- Axis minimum/maximum values
- Maximum spindle and feed values
- Supported work offsets
- Approved/restricted G/M commands
- Safe-start, tool-change, and program-end templates

Each card links to:

- **Extract from documents**
- **Approved programs**
- **Revisions**
- Edit/delete

Expected:

- Creating a machine also creates its initial compatible revision.
- Editing the machine marks dependent Phase 6 standards/comparisons stale.
- Deleting a machine is destructive to related local data; confirm carefully.

Debug:

- A duplicate name returns HTTP 409.
- Invalid min/max ranges return validation errors.
- Missing travel values disable those specific limit rules; they do not imply
  unlimited safe travel.

### 12.3 New analysis — `/analysis/new`

Steps:

1. Enter an analysis name.
2. Select a machine.
3. Paste/load G-code.
4. Optionally provide CL/NCL.
5. Create and run the analysis.

Expected:

- The project captures the active machine-profile revision and immutable snapshot.
- G-code is hashed.
- Deterministic findings replace the prior finding set on each run.
- Status becomes:
  - `blocked` if any blocking rule fires;
  - `review_required` if warnings exist without blocking findings;
  - `passed` only when no configured blocking/warning rule fires.

`passed` does not mean production safe.

### 12.4 Analysis results — `/analysis/{projectId}`

Expected sections:

1. Overall deterministic status and severity counts
2. Local mock advisory summary
3. Severity/category filters
4. Manual-based explanation launcher
5. Organizational-standard comparison launcher
6. Original source with line highlighting
7. Deterministic finding detail and recommendation

Select a finding to highlight its exact source line.

The organizational section appears independently. Select an explicitly approved,
non-stale standard and create a comparison. A machine-revision mismatch returns
HTTP 422 rather than silently applying the standard.

### 12.5 Documents — `/documents`

Steps:

1. Select the machine.
2. Enter a title and document type.
3. Upload PDF, Markdown, or text.
4. Wait for processing.
5. Open the document viewer or search.

Expected processing states:

- `uploaded`
- `processing`
- `ready`
- `failed`

Expected stored information:

- SHA-256 hash
- MIME type and size
- Extracted pages
- Search chunks
- Page and section provenance

Debug:

- `failed` should contain a processing error.
- Empty PDF extraction may indicate a scanned document; OCR is not implemented.
- The full FANUC test manual is large and naturally creates many chunks.
- Reprocess regenerates extracted content/chunks.

### 12.6 Document viewer — `/documents/{documentId}`

Expected:

- Document metadata
- Page navigation
- Extracted text
- Chunk inspector
- Citation-compatible page/section context

The viewer displays extracted content; it is not a controlled PDF rendering or
revision-signature system.

### 12.7 Manual Assistant — `/manual-assistant`

Steps:

1. Select a machine.
2. Create/open a question session.
3. Select relevant document types.
4. Ask a precise question.
5. Review answer status, citations, and unresolved questions.

Expected answer states:

- `answered`
- `insufficient_evidence`
- `failed`

Expected:

- Answers use uploaded chunks and show citations.
- Unsupported questions should say evidence is insufficient.
- Citation excerpts identify document, page, section, and relevance.
- The default provider is local mock behavior.

Debug:

- Confirm documents are `ready`.
- Search the exact term in the Documents page.
- Lower retrieval thresholds only for diagnostics; do not represent lower-quality
  retrieval as stronger evidence.

### 12.8 Traceability — `/analyses/{analysisId}/traceability`

Steps:

1. Confirm CL/NCL and G-code sources.
2. Parse both.
3. Start an alignment run.
4. Inspect CL records, relationships, G-code blocks, and issues.
5. Confirm, reject, or edit proposed relationships.
6. Recalculate if needed.
7. Export JSON, Markdown, or CSV.

Expected:

- Source line preservation
- Parser versions and file hashes
- Deterministic match reasons and score components
- Unmapped/ambiguous issues
- Review status per link
- Stale flag when source changes

Alignment confidence is inferred traceability metadata, not safety proof.

### 12.9 Profile extraction setup

Route:

```text
/machines/{machineId}/profile-extraction/new
```

Steps:

1. Select processed documents.
2. Choose target machine type.
3. Optionally choose exact variant.
4. Choose field categories or extract the full registry.
5. Start extraction.

Expected:

- Only owned, ready documents are allowed.
- The run preserves selected document IDs and settings.
- Detected variants are reported.
- All registry fields receive a proposal state, including `not_found`.

### 12.10 Profile review workspace

Route:

```text
/machines/{machineId}/profile-extraction/{runId}
```

Expected dashboard:

- Total/found/not-found/conflict/ambiguous counts
- Review dispositions
- Review progress
- Separate documentation coverage
- Category completion
- Draft-readiness reasons

Queues:

- Needs review
- Conflicts
- High/medium/low confidence
- Not found
- Deferred
- Accepted
- Rejected
- Manual entries
- Not applicable
- All

Views:

- Detailed
- Compact
- Category checklist

Review actions:

- Accept
- Accept with edit
- Reject
- Defer
- Manual entry
- Not applicable

Safety safeguards:

- Conflicts, ambiguity, safety-relevant fields, exact-machine verification,
  missing citations, conflicting evidence, and variant mismatch cannot use the
  protected high-confidence batch acceptance.
- Controller documentation alone cannot prove installed physical-machine claims.
- Search, filters, queue, selected field, view, and citation are URL-persistent.
- Unsaved edits block navigation.
- Draft creation remains disabled until every proposal has an intentional
  disposition and applicability gates are resolved.

Keyboard shortcuts are documented in the workspace help dialog.

### 12.11 Machine revisions

Route:

```text
/machines/{machineId}/revisions
```

Expected:

- Approved, draft, under-review, rejected, and superseded revisions
- Neutral revision comparison
- Provenance and review summary
- Explicit submit/approve/reject lifecycle

Creating a draft does not activate it. Approval requires exact-machine and
safety acknowledgement.

### 12.12 Approved-program library

Route:

```text
/machines/{machineId}/reference-programs
```

Steps:

1. Import a file or paste G-code.
2. Associate the exact machine revision.
3. Record controller, post revision, program type, part/operation, units, and scope.
4. Confirm approval metadata.
5. Parse and validate.
6. Review hash and deterministic findings.
7. Explicitly mark eligible or ineligible.
8. Select compatible eligible programs.
9. Run standard extraction.

Expected:

- Import starts `pending`, never automatically eligible.
- Duplicate machine/hash returns HTTP 409.
- Unsupported extensions or oversized inputs are rejected.
- Blocking deterministic findings set suitability to `requires_review`; they do
  not silently delete the record.
- `ai_processing_allowed` defaults false.
- Mixed machine revisions, controllers, variants/options, or post revisions are
  not combined automatically.

### 12.13 Convention review workspace

Route:

```text
/machines/{machineId}/standards/extraction/{runId}
```

Queues:

- Pending
- Conflicts
- High/medium/low support
- Exceptions
- Accepted
- Rejected
- Deferred

Expected evidence:

- Convention key/category/type
- Pattern and heuristic conditions
- Support count and eligible-program count
- Support percentage and frequency classification
- Confidence for prioritization
- Applicability scope
- Supporting and contradicting programs
- Exact source lines and post revision

Review actions:

- Accept as scoped convention
- Accept with edit through API
- Reject
- Defer
- Protected batch actions

Frequency never automatically accepts a convention. Conflicting and
safety-relevant conventions require individual review.

After all proposals are reviewed:

1. Create an inactive standard draft.
2. Review scope and evidence.
3. Submit for review.
4. Explicitly approve.
5. Prior approved standards become `superseded`, not deleted.

### 12.14 Approved-program comparison

Route:

```text
/analyses/{analysisId}/approved-program-comparison/{comparisonId}
```

Expected:

- Required historical-similarity warning
- Stale warning when sources/standards/profile change
- Separate deterministic and convention summaries
- Filters for `matches`, `differs`, `missing`, `unexpected`, and `not_applicable`
- Exact line references
- Logical common/added/removed/changed side-by-side sections
- Similar eligible references with match reasons and differences
- Exception classification and required note
- Report export

Exception classifications:

- Expected exception
- Different operation type
- Different post revision
- Different machine option
- Intentional programmer choice
- Requires investigation
- Standard should be updated
- Unknown

Classifying one exception never changes the standard automatically.

---

## 13. Deterministic G-code support

The baseline parser supports:

- Case-insensitive and compact word-address syntax
- Parentheses and semicolon comments
- `%`, O numbers, and N sequence numbers
- G/M commands
- XYZABCUVW coordinates
- T, S, and F words
- Signed, decimal, and zero-padded values
- Motion, distance, plane, units, work offset
- Cutter/tool-length compensation
- Feed mode/rate
- Spindle speed and state
- Selected and active tool
- Coolant state
- Recoverable malformed-token findings

Representative deterministic rules:

- Parse errors
- Axis command outside configured minimum/maximum
- Spindle command above configured maximum
- Feed command above configured maximum
- Restricted/unapproved commands
- Missing work offset before cutting feed
- Tool change without prior selection
- Safe-start/template checks
- End-state and rapid-review checks

The parser does not simulate:

- Work-offset values
- Tool geometry/wear
- Fixtures or stock
- Transformations or kinematics
- Macros, variables, or full subprogram semantics
- Machine acceleration/dynamics
- Collision or material removal

---

## 14. API organization

The authoritative contract is always `GET /openapi.json` or `/docs`.

### Machines and analyses

```text
POST/GET        /api/machines
GET/PUT/DELETE  /api/machines/{id}
POST/GET        /api/analyses
GET             /api/analyses/{id}
POST            /api/analyses/{id}/run
GET             /api/analyses/{id}/findings
PUT             /api/analyses/{id}/cl-source
PUT             /api/analyses/{id}/gcode-source
```

### Documents and manual assistance

```text
POST/GET        /api/machines/{id}/documents
GET/DELETE      /api/documents/{id}
GET             /api/documents/{id}/content
POST            /api/documents/{id}/reprocess
GET             /api/machines/{id}/documents/search
POST/GET        /api/manual-sessions
GET             /api/manual-sessions/{id}
POST            /api/manual-sessions/{id}/questions
POST            /api/machines/{id}/explain-command
```

### Traceability

```text
POST            /api/analyses/{id}/parse-cl
POST            /api/analyses/{id}/parse-gcode
GET             /api/analyses/{id}/cl-records
GET             /api/analyses/{id}/gcode-blocks
POST/GET        /api/analyses/{id}/alignment-runs
GET             /api/alignment-runs/{id}/links
GET             /api/alignment-runs/{id}/issues
POST/PUT        /api/alignment-links/{id}/...
GET             /api/alignment-runs/{id}/report
```

### Profile extraction and revisions

```text
POST/GET        /api/machines/{id}/profile-extraction-runs
GET             /api/profile-extraction-runs/{id}
GET             /api/profile-extraction-runs/{id}/proposals
GET             /api/profile-extraction-runs/{id}/review-summary
GET             /api/profile-extraction-runs/{id}/review-queue
PUT             /api/profile-field-proposals/{id}/review
POST            /api/profile-extraction-runs/{id}/proposals/batch-review
POST            /api/profile-extraction-runs/{id}/accept-eligible-high-confidence
POST            /api/profile-extraction-runs/{id}/apply-to-draft
POST            /api/profile-extraction-runs/{id}/rerun
POST            /api/profile-extraction-runs/{id}/cancel
GET             /api/machines/{id}/revisions
GET             /api/machine-profile-revisions/{id}/compare/{other}
POST            /api/machine-profile-revisions/{id}/submit-for-review
POST            /api/machine-profile-revisions/{id}/approve
POST            /api/machine-profile-revisions/{id}/reject
```

### Approved programs, standards, and comparisons

```text
POST/GET        /api/machines/{id}/reference-programs
GET/PUT/DELETE  /api/reference-programs/{id}
POST            /api/reference-programs/{id}/parse
POST            /api/reference-programs/{id}/mark-eligible
POST            /api/reference-programs/{id}/mark-ineligible
POST/GET        /api/machines/{id}/standard-extraction-runs
GET             /api/standard-extraction-runs/{id}
GET             /api/standard-extraction-runs/{id}/proposals
PUT             /api/standard-conventions/{id}/review
POST            /api/standard-extraction-runs/{id}/proposals/batch-review
POST            /api/standard-extraction-runs/{id}/apply-to-draft
POST            /api/standard-extraction-runs/{id}/rerun
GET             /api/machines/{id}/standard-profiles
GET             /api/standard-profiles/{id}
POST            /api/standard-profiles/{id}/submit-for-review
POST            /api/standard-profiles/{id}/approve
POST            /api/standard-profiles/{id}/reject
GET             /api/standard-profiles/{id}/compare/{other}
GET             /api/standard-profiles/{id}/report
POST/GET        /api/analyses/{id}/standard-comparisons
GET             /api/standard-comparisons/{id}
GET             /api/standard-comparisons/{id}/findings
GET             /api/standard-comparisons/{id}/side-by-side
PUT             /api/standard-comparison-findings/{id}/exception
GET             /api/analyses/{id}/similar-reference-programs
GET             /api/standard-comparisons/{id}/report
```

---

## 15. Testing and development workflow

### Backend

```bash
cd backend
pytest -q
pytest -v
pytest tests/test_program_standards.py -q
pytest tests/test_profile_extraction.py -q
```

Tests use in-memory SQLite and FastAPI `TestClient`.

### Frontend

```bash
cd frontend
npm run typecheck
npm test
npm run test:watch
npm run build
```

### Full macOS/Linux workflow

```bash
make test
make build
```

### Before committing

1. Run migrations against a disposable or backed-up database.
2. Run all backend tests.
3. Run frontend type checking.
4. Run all frontend tests.
5. Run the production build.
6. Run `git diff --check`.
7. Review migrations and generated data carefully.
8. Confirm no real CNC programs, secrets, absolute local paths, or controlled
   documents were added.
9. Confirm safety language remains present.

---

## 16. Debugging playbook

### Frontend says “Backend unavailable”

- Check `/api/health`.
- Confirm Uvicorn is still running.
- Confirm the port.
- Confirm `VITE_API_BASE_URL`.
- Restart Vite after changing its environment.

### Backend returns 404 at `/api/health`

Another application may occupy the port. Inspect `/openapi.json`; this API title
should be `Creo NC Post Assistant API`. Use a different port rather than stopping
an unknown service.

### CORS failure

- Copy the exact browser origin into `CORS_ORIGINS`.
- Include protocol and port.
- Restart the backend.

### SQLAlchemy/Python typing error

- Check `python --version`.
- Use Python 3.12.
- Recreate the virtual environment rather than reusing one created by another
  Python release.
- Confirm:

```bash
python -m pip show SQLAlchemy pydantic fastapi uvicorn
```

### Migration/table failure

From repository root:

```bash
PYTHONPATH=backend python -m alembic -c alembic.ini current
PYTHONPATH=backend python -m alembic -c alembic.ini upgrade head
```

Do not run the root `alembic.ini` from `backend/` without adjusting paths; its
script location is repository-root relative.

### Database cannot open

- Confirm `backend/data` exists and is writable.
- Inspect `DATABASE_URL`.
- Relative SQLite URLs are anchored by application settings.
- Do not point tests at the real database.

### Document remains failed

- Inspect `processing_error`.
- Confirm extension, MIME type, size, and readable content.
- Scanned/image PDFs need OCR, which is not implemented.

### Profile extraction returns many `not_found` values

This can be correct. The registry is broader than the deterministic extractors.
Search stored chunks for the exact label/value, inspect retrieved evidence, check
document type and variant applicability, then add a targeted deterministic
extractor and regression fixture. Do not lower validation simply to force found
values.

### Draft creation is disabled

Check the server-owned readiness summary for:

- Pending proposals
- Conflicts
- Low-confidence safety-relevant fields
- Missing variant selection
- Missing accepted conventions

### Standard extraction rejects a dataset

Confirm every program is:

- Parsed
- Explicitly eligible
- Owned by the machine
- Associated with the selected machine revision
- Compatible in controller, variant/options, and post revision

### Comparison cannot start

- The standard must be explicitly approved.
- Standard and analysis must use the same machine and machine-profile revision.
- The analysis must contain G-code.
- A selected reference must belong to the standard source dataset.

### Result is stale

Stale results are intentionally preserved. Likely causes:

- Machine profile or active revision changed
- Analysis G-code changed
- Standard changed or was superseded
- Reference became ineligible/deprecated
- Source hash changed
- Parser or extraction algorithm changed

Create a new run; do not overwrite the historical result.

---

## 17. Security and data-handling requirements

Any reproduction must preserve these requirements:

- No execution of uploaded CNC programs.
- No autonomous generation of production CNC code.
- No public web search in local analysis workflows.
- No external AI call by default.
- SHA-256 integrity hashes for uploaded/program sources.
- Strict machine/document/program ownership validation.
- File extension and size limits.
- Program source excluded from routine logs and audit metadata.
- No absolute storage paths in API responses.
- `ai_processing_allowed=false` prevents external program transmission.
- Historical records are preserved through deprecation/supersession.
- Approval and eligibility are separate decisions.
- Draft and approved states are separate.
- Audit events record significant review, approval, source, and report actions.

---

## 18. Reconstruction specification for another AI coding tool

Use this section as the minimum implementation contract when recreating the
project.

### Functional requirements

1. Build a React/TypeScript SPA and FastAPI/SQLAlchemy API.
2. Persist all domain state in SQLite with Alembic migrations.
3. Implement machine profiles and immutable revisions.
4. Capture the active revision snapshot when creating an analysis.
5. Parse Fanuc-style G-code deterministically with line preservation and modal state.
6. Run deterministic rule classes and persist explainable findings.
7. Never describe `passed` as safety certification.
8. Upload PDF/text/Markdown documents with hashes, pages, chunks, and status.
9. Search chunks and produce citation-grounded answers with insufficient-evidence states.
10. Parse Creo CL/NCL into typed, line-preserved records.
11. Infer CL/G-code relationships with reasons, scores, issues, review, and stale state.
12. Extract machine-profile fields from owned ready documents.
13. Persist found/not-found/conflicting/ambiguous proposals and real citations.
14. Provide guided queues, filters, search, persistent URL state, evidence drawer,
    keyboard navigation, batch safeguards, and category completion.
15. Require intentional review of every profile proposal before draft creation.
16. Create inactive versioned drafts and require explicit approval.
17. Import reference programs with complete machine/controller/post/applicability metadata.
18. Default every reference program to pending eligibility and AI restriction.
19. Parse and validate references without execution.
20. Reject automatic mixing of incompatible revisions, controllers, variants,
    options, or post revisions.
21. Extract deterministic convention proposals with exact program-line evidence.
22. Calculate support counts/percentage, contradictions, conditions, scope, and
    frequency class without treating frequency as authority.
23. Review conventions and create inactive versioned standard drafts.
24. Require explicit standard approval and preserve superseded revisions.
25. Compare analyses against approved compatible standards.
26. Keep deterministic findings and organizational differences separate.
27. Return matches/differs/missing/unexpected/not-applicable results with lines.
28. Retrieve similar eligible programs with reasons and differences; label score advisory.
29. Provide logical side-by-side common/added/removed/changed sections.
30. Allow exception classification without automatic standard mutation.
31. Mark dependent standards/comparisons stale when inputs or versions change.
32. Export JSON, Markdown, and suitable CSV with hashes, revisions, findings,
    notes, and safety notices.
33. Add fictional regression datasets and deterministic seeders.
34. Test API ownership, review gates, safety boundaries, persistence, and UI flows.

### Non-functional requirements

- Local/offline operation by default
- Deterministic and repeatable outputs
- Typed request/response contracts
- Source and algorithm versioning
- Explainable evidence at the field, block, line, page, and document level
- No hidden chain-of-thought or hidden AI reasoning in reports
- Responsive UI with accessible labels, focus states, dialogs, live status, and
  reduced-motion support
- URL-restorable review state
- Optimistic UI changes with rollback on failed mutations
- Historical preservation and additive migrations
- Clear safety language on every material analysis/comparison response

### Required safety response for historical comparison

```json
{
  "advisory_only": true,
  "historical_similarity_is_not_certification": true,
  "qualified_review_required": true,
  "safety_notice": "Similarity to previously approved programs does not certify machining safety, post-processor correctness, setup correctness, or production readiness. Qualified review and simulation remain required."
}
```

### Rebuild acceptance criteria

A reproduction is functionally close only when it can:

1. Seed fictional machines, manuals, CL/G-code, extraction documents, and
   approved-program datasets.
2. Restart and retain all state.
3. Reproduce deterministic findings with exact lines.
4. Produce document answers with exact citations.
5. Produce and review CL/G-code mappings.
6. Extract the KLS regression fixture values and preserve not-found states.
7. Review all 144 current profile-registry fields without a 100-item truncation.
8. Create and explicitly approve a machine revision.
9. Import 10 fictional reference programs while keeping them ineligible by default.
10. Select six compatible POST-A references and identify POST-B separately.
11. Extract convention proposals with supporting and contradicting lines.
12. Explicitly approve a standard and preserve its prior revision.
13. Produce match, missing, unexpected, and not-applicable comparison results.
14. Keep deterministic and organizational findings separate in UI and reports.
15. Pass backend tests, frontend tests, TypeScript, build, and migrations.

---

## 19. Known limitations

- No authentication or role-based authorization
- No multi-reviewer separation of duties
- No cryptographic signatures or formal electronic approval
- No database encryption or program-level access control
- No OCR/table/diagram extraction
- No malware scanning
- No external controlled-document system integration
- No qualified CNC simulation
- No collision/material-removal model
- Limited macro/subprogram/controller-specific parsing
- Heuristic convention extraction, not semantic equivalence
- Simple similar-program command-overlap scoring
- Deterministic sequence diff rather than full operation semantics
- Mock AI and embeddings by default
- Azure translation support is explanation-only and requires organization configuration; no AI-generated executable program
- SQLite is not the intended multi-user production database
- Report formatting is functional rather than publication-grade

---

## 20. Recommended future work

1. Authentication, roles, and independent approver identity
2. Encrypted object storage and per-program access controls
3. PostgreSQL and background processing
4. OCR, table extraction, and controlled-document revision precedence
5. Controller-specific parser plugins
6. Macro/subprogram call graph and parameter interpretation
7. Richer operation segmentation and semantic comparison
8. Post-processor revision compatibility policy
9. Qualified simulator/DNC/MES integration boundaries
10. Formal audit export and electronic signatures
11. Data retention, backup, restore, and disaster-recovery procedures
12. Accessibility audit and browser matrix
13. Performance tests for large document/program corpora
14. Production deployment hardening and observability

---

## 21. Documentation index

G-POST V1 uses shared configuration templates as the source of truth. CL/NCL mappings reference those templates and create local output text only through an explicit override. Support status and engineer review status are separate, and readiness focuses on applicable required V1 behavior.

- [Architecture](docs/architecture.md)
- [Document processing](docs/document-processing.md)
- [Retrieval and citations](docs/retrieval-and-citations.md)
- [Manual Assistant architecture](docs/manual-assistant-architecture.md)
- [CL parser](docs/cl-parser.md)
- [CL/G-code alignment](docs/cl-gcode-alignment.md)
- [Traceability review](docs/traceability-review-guide.md)
- [Machine-profile revisions](docs/machine-profile-revisions.md)
- [Profile extraction architecture](docs/profile-extraction-architecture.md)
- [Profile-field reference](docs/profile-field-reference.md)
- [Profile extraction review](docs/profile-extraction-review-guide.md)
- [Profile review UX](docs/profile-extraction-review-ux.md)
- [KLS extraction audit](docs/kls-1840n-extraction-audit.md)
- [Approved-program architecture](docs/approved-program-architecture.md)
- [Reference-program governance](docs/reference-program-governance.md)
- [Programming-standard extraction](docs/programming-standard-extraction.md)
- [Program comparison](docs/program-comparison.md)
- [Phase 6 audit](docs/phase-6-audit.md)
- [Phase 6 manual checklist](docs/phase-6-manual-test-checklist.md)
- [Revised R&D translation strategy](docs/rd-translation-strategy.md)
- [R&D hypothesis and metrics](docs/rd-hypothesis.md)
- [Translation dataset conceptual design](docs/translation-dataset-design.md)
- [Translation Explorer concept](docs/translation-explorer-concept.md)
- [Toolpath visualization strategy](docs/toolpath-visualization-strategy.md)
- [Future Azure OpenAI integration plan](docs/azure-openai-integration-plan.md)
- [Azure OpenAI translation provider](docs/azure-openai-provider.md)
- [AI data-transmission boundary](docs/ai-data-transmission-boundary.md)
- [Phase 10 manual checklist](docs/phase10-manual-test-checklist.md)
- [Existing-post vs AI benchmark design](docs/ai-post-benchmark-design.md)
- [Deterministic document extraction strategy](docs/deterministic-document-extraction-strategy.md)
- [Development roadmap](docs/roadmap.md)
- [Phase 7 reuse audit](docs/phase7-reuse-audit.md)
- [G-POST V1 scope](docs/gpost-v1-scope.md)
- [G-POST template/mapping model](docs/gpost-template-mapping-model.md)
- [G-POST review semantics](docs/gpost-review-semantics.md)
- [G-POST support statuses](docs/gpost-support-statuses.md)
- [G-POST readiness](docs/gpost-readiness.md)

---

## 22. License and use

No production-machine authorization is granted by this repository. Confirm
organizational ownership, licensing, data-classification, and export-control
requirements before distributing source code, uploaded manuals, controller
documentation, CNC programs, or generated reports.

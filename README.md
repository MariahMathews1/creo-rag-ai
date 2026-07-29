# Creo NC Post Assistant

Creo NC Post Assistant is a local internal proof of concept for reviewing Creo cutter-location data and post-processed G-code against configured machine constraints.

> **Advisory limitation:** This application does not certify a CNC program for production. Review, simulation, and approval by a qualified CNC programmer are required. All included profiles and programs are fictional.

## End-to-end workflow

1. Create a machine profile with travel, spindle, feed, command, and sequence constraints.
2. Start a new analysis and select the saved profile.
3. Paste G-code or load either fictional sample.
4. Run deterministic analysis.
5. Review the `blocked`, `review_required`, or `passed` status.
6. Filter findings by severity or category and select a finding to highlight its source line.
7. Refresh at any point; profiles, analyses, and findings persist in SQLite.
8. Upload machine manuals, search extracted pages, and ask citation-grounded questions.
9. Parse CL/NCL and G-code, then review inferred mappings on the Traceability page.
10. Extract citation-backed machine-field proposals, review every field, create a
    versioned draft, and approve it only through an explicit exact-machine action.

`passed` means only that no configured blocking or warning rule violations were detected. Manual review and simulation are still required.

## Phase 4 traceability

Phase 4 persists CL and G-code records, proposes explainable deterministic mappings,
supports review/version history and stale detection, and exports JSON, Markdown, or
CSV reports.

```bash
make migrate
make seed-manual-demo
make seed-traceability-demo
make dev
```

Open `/analyses/{analysisId}/traceability`. Alignment confidence is traceability
metadata, not a safety or correctness score.

## Phase 5 profile extraction

Phase 5 adds stable machine identities, approved/draft/superseded revisions,
immutable analysis snapshots, deterministic field-specific extraction, real
document/chunk citations, conflict and variant handling, per-field review and
provenance, neutral revision comparison, and explicit approval.

The review workspace provides risk-first queues, search and advanced filters,
category completion, detailed/compact/checklist views, keyboard review,
URL-restorable state, in-context source evidence, protected batch dispositions,
and server-owned draft readiness. See
[the review UX guide](docs/profile-extraction-review-ux.md) and
[the audit](docs/phase-5-review-ux-audit.md).

```bash
make migrate
cd backend
python -m app.scripts.seed_profile_extraction_demo
```

Open Machines, choose the fictional LT-200, then use **Extract profile** or
**Revisions**. The seed deliberately leaves its generated revision as a draft.
Documentation coverage and confidence are not safety, accuracy, completeness, or
production-readiness scores.

## Phase 6 approved-program standards

Phase 6 adds governed reference CNC programs, explicit eligibility, reuse of the
deterministic parser and validator, explainable convention extraction with exact
program-line evidence, versioned organizational standards, new-program
comparison, similar-program retrieval, side-by-side diffs, exception
classification, stale detection, and reports.

```bash
make migrate
cd backend
python -m app.scripts.seed_approved_program_demo
```

Open a machine profile and select **Approved programs**. Reference programs are
never eligible by default, frequency never creates a requirement, standards are
inactive until explicitly approved, and historical similarity is not safety
certification. See [the architecture](docs/approved-program-architecture.md),
[extraction guide](docs/programming-standard-extraction.md), and
[comparison guide](docs/program-comparison.md).

## Project structure

```text
backend/
  app/
    api/          FastAPI route handlers
    ai/           advisory provider abstraction and local mock
    core/         environment configuration
    db/           SQLAlchemy session and Alembic runner
    documents/    storage, extraction, chunking, embeddings, retrieval, answers
    profile_extraction/ typed registry, units, provider validation, extraction
    models/       persisted entities
    parsers/      line-preserving G-code parser and modal state
    schemas/      validated API contracts
    validators/   reusable deterministic rules
  tests/
frontend/
  src/
    api/          typed API client
    components/   shared navigation, headers, safety, severity
    features/     machine forms and fictional analysis samples
    pages/        dashboard, profiles, analyses, documents, manual assistant
sample-data/      fictional profile, CL/NCL, G-code, manuals, extraction corpus
docs/             architecture and audit notes
```

## Local setup

Requirements: Python 3.12 and Node.js 20 or newer.

### Backend — macOS/Linux

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic -c ../alembic.ini upgrade head
uvicorn app.main:app --reload
```

If `python` does not refer to Python 3.12, use `python3.12`.

### Backend — Windows PowerShell

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The database and required tables are created automatically in `backend/data`. Open:

- API: `http://localhost:8000`
- Interactive documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

Expected health response:

```json
{"status":"healthy","service":"Creo NC Post Assistant API"}
```

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Development commands

From the repository root on macOS/Linux:

```bash
make install
make dev
make test
make build
```

Windows users do not need Make. Use the backend and frontend commands above, then:

```powershell
cd backend
pytest
pytest -v

cd ..\frontend
npm run lint
npm run typecheck
npm test
npm run build
```

## API routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Service health |
| `POST` | `/api/machines` | Create a profile |
| `GET` | `/api/machines` | List profiles |
| `GET` | `/api/machines/{machine_id}` | Retrieve a profile |
| `PUT` | `/api/machines/{machine_id}` | Replace a profile |
| `DELETE` | `/api/machines/{machine_id}` | Delete a profile and its local analyses |
| `POST` | `/api/analyses` | Create an analysis |
| `GET` | `/api/analyses` | List analyses |
| `GET` | `/api/analyses/{analysis_id}` | Retrieve an analysis |
| `POST` | `/api/analyses/{analysis_id}/run` | Replace stored findings with a new run |
| `GET` | `/api/analyses/{analysis_id}/findings` | Retrieve stored findings |
| `POST` | `/api/analyses/{analysis_id}/ai-explanation` | Request local advisory mock text |
| `POST/GET` | `/api/machines/{machine_id}/documents` | Upload or list manuals |
| `GET/DELETE` | `/api/documents/{document_id}` | Inspect or delete a manual |
| `GET` | `/api/documents/{document_id}/content` | Extracted pages and chunks |
| `POST` | `/api/documents/{document_id}/reprocess` | Re-run processing |
| `GET` | `/api/machines/{machine_id}/documents/search` | Keyword search |
| `POST/GET` | `/api/manual-sessions` | Create or list reference sessions |
| `POST` | `/api/manual-sessions/{id}/questions` | Ask a grounded question |
| `POST` | `/api/machines/{id}/explain-command` | Explain from machine manuals |
| `POST/GET` | `/api/machines/{id}/profile-extraction-runs` | Start/list extraction runs |
| `GET` | `/api/profile-extraction-runs/{id}/proposals` | Filter citation-backed proposals |
| `GET` | `/api/profile-extraction-runs/{id}/review-summary` | Authoritative review counts and readiness |
| `GET` | `/api/profile-extraction-runs/{id}/review-queue` | Search, filter, sort, and page review work |
| `POST` | `/api/profile-extraction-runs/{id}/proposals/batch-review` | Apply a protected batch disposition |
| `POST` | `/api/profile-extraction-runs/{id}/accept-eligible-high-confidence` | Accept only server-eligible high-confidence fields |
| `PUT` | `/api/profile-field-proposals/{id}/review` | Record a field disposition |
| `POST` | `/api/profile-extraction-runs/{id}/apply-to-draft` | Create an inactive reviewed revision |
| `POST` | `/api/profile-extraction-runs/{id}/rerun` | Preserve and re-run extraction |
| `GET` | `/api/machines/{id}/revisions` | List preserved profile revisions |
| `GET` | `/api/machine-profile-revisions/{id}/compare/{other}` | Compare revisions |
| `POST` | `/api/machine-profile-revisions/{id}/submit-for-review` | Submit an inactive draft |
| `POST` | `/api/machine-profile-revisions/{id}/approve` | Explicitly approve and activate |
| `POST` | `/api/machine-profile-revisions/{id}/reject` | Retain a rejected revision |
| `POST/GET` | `/api/machines/{id}/reference-programs` | Import/list governed historical programs |
| `POST` | `/api/reference-programs/{id}/parse` | Parse and deterministically validate a reference |
| `POST` | `/api/reference-programs/{id}/mark-eligible` | Explicitly allow pattern analysis |
| `POST/GET` | `/api/machines/{id}/standard-extraction-runs` | Extract deterministic convention proposals |
| `GET` | `/api/standard-extraction-runs/{id}/proposals` | Review convention evidence |
| `POST` | `/api/standard-extraction-runs/{id}/apply-to-draft` | Create an inactive standard draft |
| `POST` | `/api/standard-profiles/{id}/approve` | Explicitly approve a standard revision |
| `POST/GET` | `/api/analyses/{id}/standard-comparisons` | Compare a program to an approved standard |
| `GET` | `/api/analyses/{id}/similar-reference-programs` | Retrieve similar eligible examples |
| `GET` | `/api/standard-comparisons/{id}/side-by-side` | Logical section and line diff |

Every analysis response includes `advisory_only: true` and a safety notice.

## Supported G-code behavior

The parser is an extensible Fanuc-style baseline. It supports:

- Uppercase/lowercase and compact word-address syntax such as `G00X1.25Y-2.5`
- Parentheses and semicolon comments
- Program and sequence numbers
- G/M commands, XYZABCUVW coordinates, T, S, and F words
- Decimal, signed, and zero-padded values
- Modal motion, positioning, plane, units, work offset, cutter and tool-length compensation
- Feed, spindle speed/state, selected/active tool, and coolant state
- Recoverable malformed-token findings

Rules check explicit commanded coordinates, not physical machine position. The application does not simulate offsets, transformations, macros, subprograms, tool geometry, fixtures, kinematics, or collisions.

## Environment variables

Copy `.env.example` to `.env` when overriding defaults.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/creo_nc_post_assistant.db` | SQLAlchemy database URL |
| `CORS_ORIGINS` | Localhost and `127.0.0.1` on port 5173 | Comma-separated browser origins |
| `DOCUMENT_STORAGE_PATH` | `./data/documents` | Controlled local file storage |
| `MAX_DOCUMENT_UPLOAD_MB` | `50` | Upload limit |
| `AI_PROVIDER` / `EMBEDDING_PROVIDER` | `mock` | Independently selected providers |
| `DOCUMENT_CHUNK_SIZE` / `DOCUMENT_CHUNK_OVERLAP` | `900` / `150` | Character targets |
| `RETRIEVAL_TOP_K` / `RETRIEVAL_MIN_SCORE` | `6` / `0.30` | Retrieval controls |
| `PROFILE_EXTRACTION_PROVIDER` | `mock` | Offline structured extraction boundary |
| `PROFILE_EXTRACTION_TOP_K` / `PROFILE_EXTRACTION_MIN_SCORE` | `8` / `0.25` | Field retrieval controls |
| `PROFILE_EXTRACTION_HIGH_CONFIDENCE` / `MEDIUM_CONFIDENCE` | `0.90` / `0.70` | Display bands |
| `PROFILE_EXTRACTION_MIN_RECOMMENDED_CONFIDENCE` | `0.45` | Note-required acceptance threshold |
| `ENABLE_PROFILE_EXTRACTION_DEBUG` | `false` | Validated retrieval/scoring diagnostics |
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | Browser-visible API base URL |

## Docker

```bash
docker compose up --build
```

Open `http://localhost:5173`. The backend is exposed at `http://localhost:8000`, and SQLite persists in the `creo-data` volume.

## Manual knowledge demo

```bash
cd backend
alembic -c ../alembic.ini upgrade head
python -m app.scripts.seed_manual_demo
```

This registers the three original fictional manuals, creates mock embeddings, and runs supported and unsupported questions.

## Sample data

The UI has buttons for the safe-style and problematic fictional programs. Matching source files are in `sample-data/`. None may be used to operate real equipment.

The five files under `sample-data/profile-extraction/` are invented and
prominently marked not for machine use. They exercise two lathe variants,
optional tooling, missing values, and a deliberate spindle conflict.

## Troubleshooting

- **Backend unavailable:** Confirm Uvicorn is running on port 8000 and `VITE_API_BASE_URL` ends in `/api`.
- **Browser reports CORS errors:** Add the exact frontend origin to `CORS_ORIGINS`, comma-separated, and restart the backend.
- **Database cannot open:** Start the backend from `backend/`, or use an absolute SQLite `DATABASE_URL`; confirm `backend/data` is writable.
- **Profile cannot be deleted:** Deletion removes its associated local analyses. Confirm the prompt and inspect the API response.
- **Port already in use:** Stop the existing process or start the service with another port and update the corresponding environment value.
- **Windows activation fails:** Use PowerShell and run `.venv\Scripts\activate`.

## Current limitations and next steps

- OCR, malware scanning, authentication, multi-user approval separation, and
  enterprise controlled-document lifecycle are not yet included.
- CL-to-G-code comparison and AI explanation remain local mock responses.
- Mock hash embeddings prioritize deterministic local testing over semantic quality.
- Deterministic extraction currently recognizes the highest-value explicit labels;
  the wider typed registry intentionally yields `not_found` where no validated
  parser exists. Tables, OCR, diagrams, and nuanced revision precedence need
  future extractors.
- Future phases should add authentication/roles, selected-variant re-filtering,
  command-level approval UX, OCR/table extraction, controlled-document revision
  precedence, draft-only test analysis, and explicit stale-profile comparison
  without representing any result as certification.

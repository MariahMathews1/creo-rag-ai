# API reference

FastAPI publishes the complete interactive schema at `/docs`. G-POST endpoints are:

- `POST/GET /api/machines/{machine_id}/gpost-drafts`
- `GET/PUT /api/gpost-drafts/{draft_id}`
- `POST /api/gpost-drafts/{draft_id}/versions`
- `POST /api/gpost-drafts/{draft_id}/archive`
- `GET/POST /api/gpost-drafts/{draft_id}/mappings`
- `PUT /api/gpost-mappings/{mapping_id}`
- `POST /api/gpost-drafts/{draft_id}/preview`
- `GET /api/gpost-drafts/{draft_id}/warnings`
- `GET /api/gpost-drafts/{draft_id}/traceability`
- `POST /api/gpost-drafts/{draft_id}/validate-for-rnd`
- `GET /api/gpost-drafts/{draft_id}/compare/{other_draft_id}`
- `GET /api/gpost-drafts/{draft_id}/export?format=json|markdown`

Ownership violations return 422. Missing records return 404. Attempts to overwrite superseded/archived versions return 409.

## Phase 8 translation examples

- `POST/GET /api/translations` — create from pasted text or list/filter pairs
- `POST /api/translations/import` — multipart paired-file import
- `GET/PUT /api/translations/{id}` — detail and editable candidate/reviewed metadata
- `POST /api/translations/{id}/candidate|review|verify|deprecate|invalidate` — governed transitions
- `POST/GET /api/translations/{id}/alignment` — propose/read example alignment
- `POST /api/translation-alignments/{id}/links` — create a manual span or unmatched link
- `PUT /api/translation-alignment-links/{id}` and `POST .../confirm|reject` — persist review decisions
- `GET /api/translations/summary` and `GET /api/translations/explorer` — dataset metrics and isolated confirmed patterns
- `GET /api/gpost-mappings/{id}/historical-translation-evidence` — read-only verified evidence; never changes a mapping

Exact duplicate pairs return the existing record and `X-Duplicate-Translation-Example: true`. Verification gate failures return 422 with issue details; invalid transitions/final-record edits return 409.

## Phase 9 toolpath visualization

- `GET /api/analyses/{id}/toolpath?source=cl|gcode|both`
- `GET /api/translations/{id}/toolpath?source=cl|gcode|both`
- `GET /api/gpost-preview-runs/{id}/toolpath?source=cl|gcode|both`

Responses contain normalized segments, raw programmed-coordinate context, bounds, summary, explicit warnings, and the mandatory visualization-only safety notice. They contain no raw filesystem paths and perform no stock-removal or collision computation.

## Phase 10 controlled translation AI

- `GET /api/ai/translation/provider-status` — safe configuration metadata; add `?check_reachability=true` only for an explicit Azure health probe
- `POST /api/ai/translation/retrieve` — database-only verified-example retrieval; never invokes AI
- `POST /api/ai/translation/explain` — explicit advisory structured interpretation using selected eligible examples
- `GET /api/ai/translation/invocations` and `GET /api/ai/translation/invocations/{id}` — content-minimized audit metadata
- `POST /api/translations/{id}/ai-processing-consent` — individual explicit consent control; requires a reviewer label and acknowledgement, allows enable only for `verified_successful` examples, and emits `translation_ai_consent_enabled` or `translation_ai_consent_disabled`

Public-web retrieval, full-program AI G-code generation, automatic mapping changes, document transmission, and fine-tuning are not enabled.

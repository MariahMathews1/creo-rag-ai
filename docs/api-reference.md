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

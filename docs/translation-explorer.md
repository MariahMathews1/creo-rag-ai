# Translation Explorer

The explorer aggregates deterministic normalized patterns only from confirmed or edited alignment links. By default it uses `verified_successful` examples. Results remain visibly grouped by machine, controller, post revision, operation, and CL command; counts are never silently pooled across those boundaries.

Current normalizers replace known values for `SPINDL`, `LOADTL`, and `FEDRAT`, and coordinate tokens for motion patterns while preserving original source on the example. This supports exploratory counts, not semantic generalization.

Use the **Pattern Explorer** tab under `/translations`, or query `GET /api/translations/explorer` with optional command, machine, post revision, operation, and verification-status filters.

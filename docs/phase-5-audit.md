# Phase 5 repository audit

## Starting state

`MachineProfile` was a mutable row containing stable identity, XYZ limits,
spindle/feed thresholds, command allow/restrict lists, and start/end templates.
Analyses referenced that row only, so later edits could change the configuration
seen by an old analysis. There was no revision, field provenance, extraction run,
proposal, conflict, or review model.

`SourceDocument` already stored machine ownership, document type, filename,
controller metadata, processing state, extracted text, page data, and controlled
storage metadata. `DocumentChunk` stored real document/chunk IDs, page ranges,
section titles, excerpts, and embeddings. Phase 3 answer citations established a
sound citation pattern. Retrieval was machine-scoped and audit events existed,
but profile CRUD and the frontend had no history or extraction workflow.

## Gaps found

- No stable-profile/revision separation or approval state.
- No analysis revision ID or immutable configuration snapshot.
- No typed extraction field registry, provider boundary, safe unit normalization,
  conflict/variant classification, or explicit not-found proposal.
- No persistent review decision, evidence, or per-field provenance.
- Document types omitted operator/specification/configuration sources.
- No setup, progress/review, comparison, or revision-history screens.
- No protection against selecting another machine’s documents or unready input.
- Uploaded text needed to remain untrusted data and provider citations needed an
  allowlist against retrieved chunk IDs.

## Fixes applied

Phase 5 adds a compatible revision layer while preserving legacy profile APIs.
Existing profiles migrate to approved revision 1. A draft cannot become active
until an explicit approval request carries both acknowledgments, all proposals
have an intentional disposition, core identity exists, and conflicts are
resolved. Previous active revisions become `superseded`, never deleted.

Analyses capture a revision ID and normalized JSON snapshot at creation. The
validator now runs from that snapshot instead of the mutable compatibility row.

Extraction runs validate machine/document ownership, readiness, supported type,
selection size, and duplicate active processing. The deterministic pipeline
creates a proposal for every selected registry field, including not-found,
ambiguous, optional, variant-dependent, and conflicting outcomes. Evidence uses
persisted chunk IDs and exact excerpts. Unit aliases are allowlisted and safe
conversions preserve original value, unit, and formula.

The provider boundary validates types, status, confidence, units, and citation
IDs. The default mock path performs no network call and treats document excerpts
as data rather than instructions. API responses do not expose storage paths.

## Migration notes

Migration `20260728_02` is additive. It creates revision/extraction/provenance
tables, expands profile and analysis references, backfills one approved revision
per existing profile, assigns active revision IDs, and stores analysis snapshots.
It does not delete profiles, documents, analyses, or findings.

## Remaining security limitations

This local proof of concept has no authentication, authorization roles, malware
scanner, OCR isolation, document quarantine, encrypted secrets store, or
multi-user approval separation. HTML is escaped by React, but deployments still
need hardened upload scanning, CSP, rate limits, access control, and backups.

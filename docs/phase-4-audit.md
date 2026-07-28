# Phase 4 audit

Phase 2 stored pasted CL and G-code on `AnalysisProject`, but only parsed G-code.
That parser already tracks common motion, units, modes, work offsets, compensation,
feed, spindle, tool, and coolant. Deterministic findings are persisted and remain
authoritative. Phase 3 supplies machine documents and grounded citations.

Gaps included opaque CL text, transient G-code results, no source integrity/status,
and no events, alignment, review, versions, reports, pagination, or stale detection.
Coordinate matching is particularly risky because offsets, transformations, kinematics,
cycles, macros, and unknown units can change output.

Phase 4 fixes these gaps with a non-crashing CL parser, queryable CL/G-code records,
modal snapshots, manufacturing events, configurable deterministic scoring, unit
conversion, mismatch reasons, unmatched issues, versioned runs, review annotations,
stale detection, reports, audit events, paginated APIs, and a three-panel UI.

The engine does not simulate Creo, the post processor, controller macros, fixture
offsets, or machine kinematics. Confidence is never a safety/correctness score.

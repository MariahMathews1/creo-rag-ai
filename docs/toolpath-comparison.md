# Toolpath comparison

Confirmed Translation Alignment spans connect CL and G-code segments. Phase 9 compares aligned endpoints conservatively using a small configured tolerance and reports `matching_geometry`, `within_tolerance`, `different_geometry`, or `unresolved`. Supported arcs retain centers and sampled curves; unresolved arcs are never replaced by a misleading straight path.

Comparison counts are R&D debugging metrics, not error classification or a safety score. Differences can reflect legitimate post behavior, coordinate conventions, compensation, suppressed records, or missing context.

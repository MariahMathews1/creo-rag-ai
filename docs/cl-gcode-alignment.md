# CL-to-G-code alignment

The deterministic pipeline creates manufacturing events, bounded order-based candidate
windows, transparent feature scores, proposals above threshold, and unmatched issues.
It does not force complete coverage.

Features include event type, relative order, normalized coordinates, tool, feed,
spindle, and coolant. Defaults: high 0.90, medium 0.70, minimum 0.45, coordinate
tolerance 0.001 active G-code units, feed 2%, spindle 1%, and 20-event window.
Inch/mm values convert when both modes are known; unknown units reduce confidence.

Rules cover tool/M06, spindle, coolant, rapid/feed motion, arcs, cycles, stop,
completion, and comments. Coordinate equality is only one feature.

Runs record hashes, machine update time, parser/algorithm versions, settings, summaries,
and optional debug metrics. Recalculation creates a version and preserves reviewed
decisions only for still-valid record pairs. Source replacement marks history stale.

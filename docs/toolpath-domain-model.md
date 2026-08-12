# Toolpath domain model

Phase 9 introduces an API-only normalized `ToolpathPoint`, `ToolpathSegment`, bounds, summary, warnings, and response model. It is derived from existing typed CL/G-code parser results; raw sources are never independently tokenized by the visualization layer.

Segments retain source/line identity, sequence, operation/tool/state metadata, XYZ plus optional rotary coordinates, rapid/feed/arc/event classification, sampled supported arc geometry, alignment IDs, linked segment IDs, deterministic finding IDs, and explicit visualizability/unmatched state. No persistence migration is required because toolpaths are reproducibly derived views of governed source and parser state.

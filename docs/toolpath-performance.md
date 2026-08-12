# Toolpath performance

The UI draws all visible segments into one Canvas rather than one React/SVG node per segment. Responses above 10,000 segments set `visualization_simplified`; the viewer retains endpoints, tool changes, arcs, findings, and a regular sample capped near 8,000 display segments. Source/parser data is never changed.

The backend test suite generates 10,001 CL motion records and enforces a five-second local bound. The accessible table caps rendered rows at 500 while the Canvas and sequence controls retain the full response.

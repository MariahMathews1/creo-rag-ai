# Toolpath visualization strategy

Toolpath visualization is planned for Phase 9 and is not implemented in this milestone.

## V1 views

- Lathe: X/Z toolpath.
- Mill: XY, XZ, and YZ projections.
- Later: simple 3D XYZ visualization.

Segments should distinguish rapid moves, feed moves, arcs, tool changes, operation boundaries, and the selected finding. Selecting a segment should link to its CL line, G-code line, mapping/alignment, and deterministic finding.

The parser's modal state should supply effective coordinates and motion modes. Unknown or invalid geometry must be shown as incomplete rather than interpolated silently.

## Not material-removal simulation

Toolpath visualization displays interpreted motion. It does not prove collision freedom, workholding clearance, or the machined result.

Part/material-removal simulation additionally requires stock geometry, tool geometry, tool orientation, offsets, compensation, fixtures, and a material-removal model. That is a separate and substantially larger capability. The UI must not describe a plotted toolpath as simulation or verification.

# Phase 9 manual test checklist

Use only `sample-data/toolpath/` fictional fixtures.

- [ ] Analysis Toolpath opens; lathe defaults XZ, mill supports XY/XZ/YZ.
- [ ] Rapid is dashed, feed solid, arcs curved, selection strong, and legend visible.
- [ ] Segment selection identifies source line; finding selection highlights its segment.
- [ ] Coordinate context and unknown work-offset/diameter-radius warnings display.
- [ ] Translation Toolpath shows CL, G-code, and overlay layers; aligned selection identifies both sources.
- [ ] Tool, motion, and operation filters and previous/next scrubber work.
- [ ] Supported G17/G18/G19 and R/IJK arcs render; unresolved arc shows warning and endpoint only.
- [ ] G-POST preview results expose Toolpath and input/generated overlay.
- [ ] Accessible segment table duplicates sequence, motion, endpoints, tool, source, and finding.
- [ ] 10,000+ segment response announces display simplification.
- [ ] No wording claims simulation, stock removal, collision detection, final part, or machining verification.

Material removal is a separate future capability requiring stock, cutter/holder, fixtures, offsets/compensation, tool orientation, kinematics, swept volume, and boolean subtraction. It is explicitly not Phase 9.

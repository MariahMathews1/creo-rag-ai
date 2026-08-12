# Toolpath visualization

The reusable Canvas `ToolpathViewer` renders parsed programmed motion in XY, XZ, or YZ. Lathe contexts default to XZ; mills default to XY. Rapid uses a dashed path, feed a solid path, arcs sampled curves, findings markers, unmatched dotted styling, CL green, G-code blue-gray, and selection a stronger amber line. These semantics use design tokens and do not depend on color alone.

Controls include source/motion/finding/alignment layers, view, fit/reset/zoom, tool/motion/operation filters, collapsible legend, and sequence stepping. A detail panel and accessible segment table duplicate Canvas information. Analysis, Translation Examples, and G-POST previews share this component.

This is not simulation, collision detection, final-part prediction, or machining verification.

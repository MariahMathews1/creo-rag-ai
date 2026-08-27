# Post Record information architecture

Review & Validation separates Post Development Review, governed G-POST test results, external VERICUT Simulation, and Engineer/Site Review. Toolpath Viewer remains an Advanced local research visualization, not the primary validation system.

A **Post Record** is the complete engineering record for one machine-specific G-POST development effort. It is the primary user-facing object; Phase 11 section drafts remain an internal compatibility and optional-assistance mechanism.

The primary workflow is `Machine → Machine Knowledge → OFG Configuration → Site Standards → Custom Logic → Review & Validation → Versions → Sources`.

Overview identifies the machine, reports completion counts and blockers, and offers one contextual next action. It avoids confidence and safety scores. Specialist tools—including FIL/CIMFIL editing, Historical Post Examples, deterministic G-code Review, Toolpath Viewer, audit details, and retained experiments—live under Advanced Tools.

Overall states are Setup, Building, Needs Information, Ready for Engineering Review, Under Validation, R&D Validated, and Archived. None implies production approval.

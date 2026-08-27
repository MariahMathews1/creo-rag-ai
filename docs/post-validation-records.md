# Post Validation Records

Stages are Configuration Review, OFG Entry Review, FIL Static Review, G-POST Compilation, Controlled Test Post, Local NC Review, VERICUT Simulation, NC Programmer Review, Dry Run, and Site Qualification.

Results are `NOT_STARTED`, `PASS`, `PASS_WITH_FINDINGS`, `FAIL`, `NEEDS_REVIEW`, `BLOCKED`, and `NOT_APPLICABLE`. Findings use INFO/WARNING/ERROR/FATAL/UNKNOWN severity and Open, Investigating, Resolved, Accepted for R&D, or Deferred status. Resolution is always an engineering action.

Each Post Record has configurable required gates. Defaults are Configuration Review, G-POST Compilation, and NC Programmer Review; sites decide whether VERICUT or other stages are required.

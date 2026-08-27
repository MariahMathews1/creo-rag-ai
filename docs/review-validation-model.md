# Review and validation model

Review & Validation reports completeness across Machine Knowledge, OFG settings, Site Standards, Custom Logic, Open Questions, conflicts, and controlled validation records.

`PostValidationRecord` stores type, linked version, name, performer/time, local environment, result, approved test-program metadata, findings counts, report/reference, and whether AI was used. Activities include Configuration Review, OFG Entry Review, FIL Static Review, G-POST Compilation, Controlled Test Post, Local NC Review, VERICUT Simulation, Dry Run, Site Qualification, and NC Programmer Review.

These are manual records of governed local work. Test CL is not automatically transmitted to AI. The module does not perform collision proof, toolpath rewriting, formal verification, or correct-by-construction claims.

The page separates Post Development Review, G-POST test results, external VERICUT Simulation, and Engineer/Site Review. Required gates come from a Post Record Validation Policy plus applied Site Standard requirements. Deterministic listing diagnostics and findings are local and never repair FIL automatically.

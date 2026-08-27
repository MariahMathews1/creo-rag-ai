# Sensitive Engineering Data Policy

`PART_GEOMETRY_EXTERNAL_AI_ALLOWED = false`.

External AI context rejects CL/NCL, CAD models, STEP/IGES or Creo part geometry, fixture/stock geometry, proprietary prints, customer designs, feature data, toolpaths, production G-code/NC, part-specific test programs or diagnostics, and VERICUT data containing part geometry.

`PART_SPECIFIC` and `TEST_PROGRAM` content is never AI-eligible by default. Machine-level documents and Site Standards require explicit review and must contain no customer/part information. Test files, listings, reports, and references remain local/internal.

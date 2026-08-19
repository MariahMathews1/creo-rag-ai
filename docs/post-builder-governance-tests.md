# Post Builder governance tests

Automated tests verify that CL/NCL, APT, toolpaths, part coordinates, production G-code, and translation examples are rejected before provider invocation. They also verify no AI call occurs during readiness or retrieval, machine isolation, evidence eligibility, citation allowlisting, cycles deferral, explicit context acknowledgement, and safe hashed audit metadata.

Workflow tests cover contextual readiness, deterministic retrieval, three-rule spindle drafting, each rule review action, preservation of AI and engineer templates, immutable regeneration, section comparison, whole-post version cloning, and JSON/Markdown exports. Frontend tests verify the development-only boundary, cycles card, context exclusions, explicit invocation, and reviewer identity.

Use `make test` for the full suite and `make build` for the production frontend build. The mock provider is deterministic and local; Azure credentials are neither required nor used by governance tests.

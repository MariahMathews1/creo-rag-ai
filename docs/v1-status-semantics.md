# V1 status semantics

## Machine status

- **Complete:** core travel and spindle-limit context is present.
- **Needs Information:** one or more core fields are missing; use Find in Documents or edit the machine.
- **Needs Review:** extracted or entered information still requires confirmation.

## Translation Example status

- **Candidate / Reviewed / Verified / Deprecated / Invalid** describe governance of historical evidence.
- **Verified** means the historical CL/G-code pair was reviewed successfully. It is not production authorization.

## G-POST lifecycle

- **Draft:** configuration exists but has not been tested sufficiently.
- **Needs Configuration:** a required machine or post setup issue needs attention.
- **Ready for R&D Test:** sufficient context exists to preview supported CL/NCL.
- **R&D Tested:** a preview was generated and deterministic checks completed.
- **Archived:** inactive historical draft.

**Blocked** is a contextual action state, never production lifecycle approval. It must include an exact reason and remediation. **R&D Tested** does not mean the post is production-approved, certified, or safe for machine use.

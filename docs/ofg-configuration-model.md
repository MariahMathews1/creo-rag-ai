# OFG Configuration model

`OFGSetting` is the structured engineering representation of an Option File Generator requirement. It is not an `.opt` file and does not claim a verified OFG import format.

Each setting records category, stable key, name, value/unit, status, source Machine Knowledge facts, evidence, Site Standards, custom-logic requirement, reviewer notes, and optional OFG menu path. Statuses are Unmapped, Mapped, Needs Review, Needs Information, Conflicting, Reviewed, Not Applicable, and Custom Logic Required.

Machine Fact → OFG Setting is explicitly one-to-many. Expanded API traceability includes source value, review state, source, and location. OFG menu paths are independently Verified or Unverified; unverified paths display “Not yet verified.”

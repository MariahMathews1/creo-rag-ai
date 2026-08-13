# Current-CL G-POST preflight

The preflight parses the submitted Creo CL/NCL with the existing deterministic parser and maps only commands present in that input to required G-POST behavior keys. It reports machine readiness, post-context readiness, parsed record count, required/supported/reviewed behavior, blockers, warnings, and whether R&D generation is allowed.

Unrelated unreviewed or unsupported mappings do not block the current preview. A supported but unreviewed behavior permits an explicitly warned R&D preview. A missing or unsupported behavior used by the current CL blocks generation and links to CL or mapping review. Documents, reference programs, standards, and advanced mappings remain useful evidence but are not universal generation gates.

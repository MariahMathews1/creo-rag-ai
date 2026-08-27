# G-POST Diagnostic Parsing

`GPostDiagnosticParser` is local, deterministic, conservative, and capped at 2 MB. It recognizes explicit INFO, WARNING, ERROR, and FATAL prefixes, captures codes and line references when present, and otherwise uses `UNKNOWN`. Custom Logic is linked only when one exact item name is present.

The parser stores normalized diagnostics and a SHA-256 reference, not the full listing. `.LST` semantics remain site/version dependent: **research supported; site verification required**. Diagnostics may create findings and open questions but never trigger automatic FIL rewrites. Advisory FIL checks are not compiler validation.

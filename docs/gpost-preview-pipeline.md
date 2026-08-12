# G-POST preview pipeline

```text
CL/NCL text
  → existing CL parser
  → normalized records with original line numbers
  → reviewed G-POST mapping and typed state transition
  → R&D preview G-code plus block trace
  → existing G-code parser
  → existing deterministic validation engine
  → separated diagnostics, findings, unsupported features, warnings, and trace
```

Each emitted block records its source CL line/text, command, mapping ID and draft version, template, state before/after, generated text, evidence identifiers, and warnings.

A preview is blocked by a machine/template-family mismatch, mapping scope mismatch, missing required mapping, unresolved MULTAX/TLAXIS, template rendering failure, parser error, or blocking deterministic finding. Unsupported commands remain in the result even when other blocks can be rendered.

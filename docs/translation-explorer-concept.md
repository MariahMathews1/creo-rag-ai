# Translation Explorer concept

This page is planned for Phase 8 and is not implemented in the current milestone. A future route may be `/translation-examples` or `/translations`.

## Purpose

Engineers will inspect the verified corpus, qualify imported pairs, review CL-to-G-code relationships, and understand observed output patterns without conflating frequency with authority.

## Filters

- machine and machine-profile revision;
- controller and controller version;
- post revision;
- operation type;
- CL command and normalized parameters;
- verification status;
- provenance completeness and effective date.

Example query: `SPINDL / CLW`.

```text
Observed normalized outputs
S{rpm} M03          147 verified examples
G97 S{rpm} M03       31 verified examples
```

Results should group by machine, post revision, and operation type, show exceptions, and prevent silent cross-machine aggregation.

## Pair alignment concept

`TranslationPairAlignment` will preserve CL and G-code spans, not only single lines. Statuses are `matched`, `ambiguous`, `unmatched_cl`, `unmatched_gcode`, and `manual`.

Examples:

```text
LOADTL / 2                 -> T0202
SPINDL / RPM,1200,CLW      -> S1200 M03
FEDRAT / IPM,12            -> F12
COOLNT / ON                -> M08
RAPID + GOTO / ...         -> G00 X... Z...
```

The model must support one CL record to many G-code blocks, many CL records to one block, and unmatched spans on either side. Inferred relationships require explicit review and retain algorithm version, confidence components, reviewer, note, and timestamps.

## Historical mapping evidence

The future G-POST mapping detail may show a separate **Historical Translation Evidence** panel:

```text
SPINDL / CLW
Current template: S{rpm} M03
Observed: 47 / 49 verified examples
Exceptions: 2 examples on a different post revision
```

This evidence remains distinct from manual citations. Frequency is descriptive and more testable than opaque AI confidence, but it does not override deterministic rules or qualified review.

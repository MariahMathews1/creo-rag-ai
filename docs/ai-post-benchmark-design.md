# Existing-post versus AI translation benchmark design

Benchmark execution is not implemented in this milestone.

```text
                    +-- Existing Creo Post --> G-code A (reference)
Same held-out CL ---|
                    +-- AI Translator ------> G-code B (candidate)
```

Both paths must use the same CL input and declared machine context. The candidate must not retrieve the held-out target pair or another duplicate of it.

## Dataset split

Split by pair or job family to prevent near-duplicate leakage. Preserve per-machine, post-revision, operation, and command-coverage distributions. Freeze hashes and eligibility decisions before evaluation.

## Comparisons

- normalized command and sequence agreement;
- coordinates within declared tolerances;
- modal-state equivalence;
- tool calls and offsets;
- spindle mode, direction, speed, and state;
- coolant and feed mode/value;
- work offsets;
- missing and additional blocks;
- parser diagnostics, deterministic findings, unsupported and uncertain segments;
- exact-machine retrieval coverage and any visible fallback scope.

Report textual agreement separately from modal equivalence. Safety-relevant mismatches must not be averaged away. Store reference/candidate hashes, parser and rule versions, retrieved example IDs, provider/deployment identity, settings, and review outcome.

## Baselines and acceptance

Compare retrieval-assisted translation against deterministic/template output and any agreed manual-only baseline. Define thresholds before evaluating the held-out set. A benchmark result remains R&D evidence, not production certification.

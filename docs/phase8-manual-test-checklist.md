# Phase 8 manual acceptance checklist

Use only `sample-data/translations/fictional-kls/`. Every source is marked **FICTIONAL SAMPLE — NOT FOR MACHINE USE**.

- [ ] Run `python -m app.scripts.seed_translation_demo`; confirm 5 pairs, 1 candidate, 3 verified, 1 deprecated, and no external AI.
- [ ] Open `/translations`; confirm summary, dense table, filters, default exclusion of deprecated/invalid, and safety boundary.
- [ ] Start paired import; select the fictional machine and exact approved revision.
- [ ] Upload a CL and matching NC fixture; confirm filenames are retained and create a candidate.
- [ ] Open detail; confirm both hashes, parse counts, validation counts, provenance, controller, post, and revision.
- [ ] Generate alignment; confirm tool, spindle, coolant, motion, and end proposals plus unmatched boilerplate.
- [ ] Confirm links and reject/annotate unmatched records. Confirm no proposal is auto-confirmed.
- [ ] Move candidate to reviewed. Attempt verification without acknowledgment and confirm rejection.
- [ ] Add acknowledgment/reviewer/note; verify the historical pair. Confirm final metadata/source edits are rejected.
- [ ] Open Pattern Explorer, locate SPINDL, and confirm machine/post/operation grouping.
- [ ] Inspect a G-POST SPINDL mapping’s historical evidence API; confirm verified count and `mapping_changed: false`.
- [ ] Confirm no Azure calls, external transmission, AI generation, fine-tuning, code execution, or toolpath visualization occurs.

# KLS-1840N public-corpus extraction audit

## Corpus and processing

The source files under `sample-data/public-test/kent-kls-1840n/` were not
modified. Fresh machine-scoped copies were registered through the real storage,
extraction, chunking, and embedding pipeline.

| File | Status | Pages | Chunks |
| --- | --- | ---: | ---: |
| `KLS-Series-CNC-Flat-Bed-Lathes.pdf` | ready | 5 | 11 |
| `Kent_KLS-1840N_Product_Specifications.md` | ready | 1 | 2 |
| `Fanuc Series 0i MODEL F Plus Parameter Manual_B-64700EN_01.pdf` | ready | 774 | 2,426 |
| `README.md` | ready | 1 | 2 |

The audit discovered that the pre-existing database record for the Markdown
file contained an older stored snapshot. A fresh corpus was therefore created
from the current source bytes before measuring extraction.

## Pre-fix causes

- Variant detection rescanned each document’s full extracted text once per
  chunk. With the 774-page FANUC manual this made a run take minutes.
- Retrieval aliases omitted cross-slide/longitudinal travel and several
  controller, rapid, spindle, tooling, and workholding labels.
- The provider returned no structured key-value candidates.
- Generic rapid parsing consumed `inches` before `inches per minute`, and mixed
  X/Z rates into one conflicting generic value.
- Controller model and manufacturer had no structured extraction path.
- Optional 10 HP and standard 7.5 HP values were compared as peer base values.
- Unstructured multi-model brochure tables could contribute a value without a
  validated column-to-variant mapping.
- Controller parameter text could be mistaken for installed physical options.
- `model` and controller family/model were not sufficiently separated in
  profile revisions.

## Fixes

The mock provider now parses heading-aware `Label: Value` Markdown, numeric
ranges, paired Z/X values, dimensions, booleans, number words, and optional
wording. Registry aliases cover the KLS terminology. Physical-field retrieval
excludes non-authoritative controller/programming sources, prioritizes exact
structured labels, limits results to configured top-K chunks, and uses the
selected variant throughout retrieval and applicability filtering.

Variant detection scans each document once and excludes RS protocol identifiers.
Multi-model unstructured table values are not allowed to override exact
structured values for the selected variant. Unit parsing now recognizes
inches/minute and pounds. Debug-mode not-found records include terms, chunk IDs,
label matches, rejected candidates/reasons, selected variant, authority, and
normalization.

Migration `20260728_03` adds separate controller manufacturer/model columns
without rewriting approved history. Applying the reviewed `machine_model`
proposal maps to the physical revision model. For the existing approved revision
whose model was `F`, the audit created draft revision 10 with model `KLS-1840N`,
controller manufacturer `FANUC`, and controller model `0i-Mate TF`; revision 8
remains approved and unchanged until a user explicitly reviews and approves the
repair draft.

## Final real-corpus result

Run 14 completed in under one second with 144 configured fields: 26 found, 117
not found, one conflict, zero ambiguous, and 18.1% documentation coverage.
KLS-1840N was selected from four detected KLS variants. The remaining conflict
is the controller manual’s varying work-offset references, which correctly
requires review rather than automatic approval.

X/Z travel remain separate from signed coordinate limits. X/Z rapid rates remain
separate from maximum cutting feed. Standard spindle power is 7.5 HP; the 10 HP
option is contextual evidence requiring exact-machine verification.

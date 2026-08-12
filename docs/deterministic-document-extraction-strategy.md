# Deterministic document extraction strategy

Structured machine information should not depend entirely on generative extraction. A future provider interface can combine deterministic parsing with the existing evidence and review workflow.

## Candidate fields

- axis travel and axis configuration;
- minimum/maximum spindle RPM and feed limits;
- controller manufacturer, model, version, and family;
- parameter numbers, names, ranges, and defaults;
- G/M-code tables and capability flags;
- machine specifications and documented options.

## Python approach

The primary implementation remains Python/FastAPI. PDF text and tables can be processed using the existing extractor, page provenance, normalized units, regular expressions, table-header detection, dictionaries, and deterministic confidence components. Every value should preserve page, section, excerpt, extraction rule version, unit conversion, and conflict state before entering the existing proposal-review workflow.

Deterministic rules should prefer abstention over guessing and should retain multiple conflicting candidates. Scanned documents may require an organization-approved OCR provider before parsing.

## Optional MATLAB integration

If existing organizational MATLAB tooling offers proven table analysis, signal processing, or document workflows, MATLAB could later be wrapped behind a provider boundary or batch exchange format. It must not become a required runtime dependency in this milestone. Provider output must use the same evidence, version, and validation contract as Python output.

## Evaluation

Use labeled document fixtures to measure field precision/recall, normalization accuracy, citation accuracy, conflict detection, and abstention. Keep deterministic extraction separate from the future CL/G-code translation corpus.

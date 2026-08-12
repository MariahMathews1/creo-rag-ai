# Translation dataset design

This is a conceptual contract for a later phase. No translation dataset tables or storage API are implemented in this milestone.

## `TranslationExample`

```text
id
machine_profile_id
machine_profile_revision_id
controller_name
controller_version
post_processor_name
post_processor_revision
operation_type
operation_name
cl_source_text
cl_source_hash
gcode_source_text
gcode_source_hash
verification_status
part_identifier
program_identifier
tooling_context_json
setup_context_json
source_provenance
notes
created_at
updated_at
```

Source text should be immutable after a trust decision. Hashes should be normalized SHA-256 values and pair identity should include machine/revision context. A corrected pair should create a new record and retain supersession history rather than overwrite evidence.

## Verification states

- `unknown`: imported pair with no trust decision.
- `candidate`: appears plausible but has not been qualified.
- `reviewed`: a qualified person reviewed the pair, without asserting successful historical use.
- `verified_successful`: known successfully used or approved historical G-code for the paired CL and machine context.
- `deprecated`: historically valid but excluded from current retrieval.
- `invalid`: known incorrect or mismatched pair.

Arbitrary uploaded G-code must never become reference data automatically. Only `verified_successful` examples are eligible by default.

## Provenance

`source_provenance` should allow optional fields while requiring enough information for engineering review:

```text
source_system
imported_by
original_cl_filename
original_gcode_filename
source_repository
work_order_or_project_reference
post_revision
verification_basis
verification_note
created_at
```

## Stable V1 operation taxonomy

`turning`, `facing`, `boring`, `drilling`, `threading`, `grooving`, `parting`, `milling`, `pocketing`, `contouring`, `tapping`, `reaming`, `setup`, `test`, `other`.

Store taxonomy values as stable keys with separate display labels. Allow later additions through versioned vocabulary rather than free-form replacement.

## Isolation and retrieval priority

Default retrieval order is:

1. exact machine;
2. exact machine-profile revision where applicable;
3. exact controller/version;
4. exact post revision;
5. same operation type;
6. similar CL command sequence.

Only explicit fallback may broaden to exact machine/controller, same machine family plus same post, and then same controller family. Cross-machine retrieval must never happen silently. The UI and audit record must show scope, fallback reason, selected examples, and excluded restricted sources.

## Future AI output contract

```text
generation_status
machine_profile_revision_id
retrieved_example_ids
draft_gcode
translation_segments[]
uncertain_segments[]
warnings[]
parser_diagnostics[]
deterministic_findings[]
historical_comparison[]
advisory_only
```

Each translation segment must link CL input, retrieved example IDs, and generated G-code. The contract exposes evidence and diagnostics, not hidden model reasoning.

# G-POST mapping reference

Mappings support `direct`, `stateful`, `conditional`, `template`, `cycle`, `unsupported`, and `manual` types. Review states are `pending`, `accepted`, `accepted_with_edit`, `rejected`, and `deferred`. Support is tracked independently as `supported`, `not_applicable`, `unsupported_required`, or `not_implemented`.

V1 mappings reference shared configuration through `template_key`. `template_override` is used only when `uses_override` is true; resetting an override restores inheritance from configuration.

| CL command | Initial behavior | State impact |
| --- | --- | --- |
| `LOADTL` | Mill `T{tool} M06`; lathe configurable T-code | selected and active tool |
| `SPINDL` | `S{rpm} M03/M04`, or M05 | spindle speed, direction, state |
| `FEDRAT` | `F{feed}` | feed mode/rate |
| `COOLNT` | M08/M09 | coolant state |
| `RAPID` | arms the next motion as rapid | rapid mode |
| `GOTO` | G00 or G01 with machine-appropriate axes | position and rapid mode |
| `FROM` | establishes position without emitted motion | current position |
| `FINI` | configured program-end template | ending state |
| `PPRINT` | advisory comment | no machine state |

`CIRCLE`, `ARC`, `CYCLE`, `CUTCOM`, `MULTAX`, `TLAXIS`, `GOHOME`, and `OPSTOP` are recognized initially but explicitly not implemented or capability-derived as not applicable. They are never silently discarded. If one appears in actual CL/NCL input, preview reports it rather than generating guessed output.

Document evidence is accepted only when the document belongs to the draft machine and is in the selected reference set. A missing source is labeled manual configuration/no document evidence.

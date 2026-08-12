# G-POST mapping reference

Mappings support `direct`, `stateful`, `conditional`, `template`, `cycle`, `unsupported`, and `manual` types. Review states are `pending`, `accepted`, `accepted_with_edit`, `rejected`, and `deferred`.

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

`CIRCLE`, `ARC`, `CYCLE`, `CUTCOM`, `MULTAX`, `TLAXIS`, `GOHOME`, and `OPSTOP` are recognized initially but explicitly unsupported or partially modeled. They are never silently discarded. MULTAX/TLAXIS block a preview until an appropriate reviewed implementation exists.

Document evidence is accepted only when the document belongs to the draft machine and is in the selected reference set. A missing source is labeled manual configuration/no document evidence.

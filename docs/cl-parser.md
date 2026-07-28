# CL/NCL parser

Every nonblank line is preserved and one malformed record cannot abort parsing.
Commands are case-insensitive with flexible slash whitespace. Unknown records become
`UNKNOWN` while retaining the original token and source.

Supported families include `PARTNO`, `MACHIN`, `UNITS`, `MULTAX`, `LOADTL`, `CUTTER`,
`SPINDL`, `FEDRAT`, `COOLNT`, `RAPID`, `GOTO`, `FROM`, `CIRCLE`, `ARC`, `TLAXIS`,
`GOHOME`, `PPRINT`, `INSERT`, `SEQNO`, `OPSTOP`, `REWIND`, `FINI`, `CYCLE`,
tolerances, compensation, modes, clamps, rotary/index, transforms, origins, and
coordinate systems.

`GOTO` maps up to X/Y/Z/I/J/K. `FROM` is a reference. `RAPID` applies to the next
`GOTO`. Incomplete arc geometry is flagged. State tracks units, position, tool axis,
tool/cutter, feed, spindle, coolant, rapid, compensation, operation, multiaxis mode,
coordinate system, and sequence. This is context, not Creo simulation.

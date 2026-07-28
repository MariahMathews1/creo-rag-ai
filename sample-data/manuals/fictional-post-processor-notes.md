# FICTIONAL SAMPLE DOCUMENT — NOT FOR MACHINE USE

## Creo post output

The fictional post emits G00 for rapid positioning, G01 for linear interpolation, G02 and G03 for arcs, and G80 after canned cycles. It emits G43 with the tool-length H register after a tool change and G49 during the ending sequence.

## Cycle mapping

The fictional post maps a supported tapping sequence to G84 only for the EC-3X rigid-tapping configuration. If that controller option is not enabled, the post configuration must be reviewed; the post does not infer controller licensing.

## Coolant and spindle

M03 starts clockwise spindle rotation, M05 stops it, M08 enables flood coolant, and M09 cancels coolant. The post emits M30 as the final program-end command.


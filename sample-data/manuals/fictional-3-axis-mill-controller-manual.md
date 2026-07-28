# FICTIONAL SAMPLE DOCUMENT — NOT FOR MACHINE USE

## Controller identity

This fictional manual describes the Example Control EC-3X used only by the Creo NC Post Assistant demonstration. Confirm every instruction against controlled documentation for the actual controller.

## Motion commands

### G00 rapid positioning

G00 commands rapid positioning. On this fictional controller, all programmed axes may move together. The command does not establish clearance; fixture, offset, and tool geometry review is required.

### G01 linear interpolation

G01 commands linear feed motion using the active feed mode and F value. G01 remains modal until another motion command is selected.

### G02 and G03 circular interpolation

G02 commands clockwise circular interpolation and G03 commands counterclockwise circular interpolation in the active plane. Arc-center or radius programming depends on controller configuration.

## Compensation

G40 cancels cutter-radius compensation. G41 selects cutter compensation left and G42 selects cutter compensation right relative to programmed travel. The lead-in and lead-out geometry must satisfy configured controller requirements.

G43 activates positive tool-length compensation using the selected H register. On this fictional controller, G49 cancels tool-length compensation. The company standard requires G49 in the program-ending sequence.

## Work coordinates and cycles

G54 selects work coordinate system 1. Verify the controlled offset table before operation.

G80 cancels the active canned cycle. G81 is the fictional controller's basic drilling cycle.

### G84 rigid tapping

G84 commands a rigid tapping cycle only when the rigid-tapping option is enabled. Parameters include Z depth, R return plane, and F thread lead. G98 returns to the initial plane; G99 returns to the R plane. Spindle synchronization and configuration must be confirmed. G80 cancels G84.

## Auxiliary commands

M03 starts the spindle clockwise; M05 stops the spindle. M08 enables flood coolant and M09 cancels coolant. M06 performs a tool change using the previously selected T word. M30 ends and rewinds the program.

## Limits

The fictional EC-3X demonstration spindle limit is 10,000 RPM. The demonstration feed limit is 500 inches per minute. These values are not applicable to any real machine.


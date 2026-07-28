# FICTIONAL SAMPLE DOCUMENT — NOT FOR MACHINE USE

## Orion 30T Programming Guide for Northstar LT-200 / LT-200Y

This invented guide is for software testing only. It is not approved for
programming or machine operation.

Manufacturer: Northstar Machine Works
Machine model: LT-200
Machine type: turning_center
Controller: Orion 30T
Controller version: 4.8

## Coordinate systems

Supported work offsets: G54 G55 G56 G57 G58 G59.
G53 selects the machine coordinate system. G90 and G91 select absolute and
incremental programming. G20 and G21 select inch and metric input.

These references describe controller syntax; they do not prove that every
optional function is enabled on an exact machine.

## Programming examples

Safe start example: G18 G20 G40 G80 G99
Program end example: M09 G28 U0 W0 M30

The examples are explanatory, not automatically a company-required template.
The turret indexes after the commanded tool station and geometry offset have
been validated by the operator under the controlled setup procedure.

## Common command reference

G00 rapid positioning; G01 linear interpolation; G02/G03 circular
interpolation; G96 constant surface speed; G97 fixed spindle speed.
M03/M04 start the spindle; M05 stops it; M08/M09 control coolant; M30 ends and
rewinds the program.

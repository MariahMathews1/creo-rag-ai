## Tab/Section:
## Type, Specs, & Axes → Machine → Machine Type
Purpose:
Defines base machine kinematic class (3‑axis, 4‑axis, 5‑axis tables, heads, dual rotary configurations). This selection drives all post‑processor kinematic rules.
UI Elements Present:

Dropdown list: Machine Type

Options visible:

Mills without Rotary Axes
4‑Axis Rotary Table
4‑Axis Rotary Head
5‑Axis Dual Rotary Table
5‑Axis Rotary Table / Rotary Head
5‑Axis Dual Rotary Head or Nutator
1 Rotary / 1 Radial Axis (Live Tooling)




Machine preview graphic:

Depicts a basic 3‑axis mill
Axis arrows labeled:

X+
Y+
Z+





Programmer Actions:

Select the machine’s kinematic type.
Use preview graphic to confirm axis directions and machine layout.

Mapping to AI‑Assisted G‑POST Builder:

AI should infer:

Kinematic chain needed for post building.
Required transformation matrices for converting CL → machine coordinates.
Rotary-axis mapping rules, including coupling, handedness, and axis order.


AI should prepare:

Suggested post templates for selected machine class
Axis transformation logic
Rotary-axis output rules (A/B/C vs head/table combinations)

## Tab/Section:
## Type, Specs, & Axes → Specs → Motion Resolution & Departure
Purpose:
Defines motion register behavior, modal/non‑modal motion settings, resolution, and tool‑axis handling for MULTAX machines. These settings affect how Creo output is interpreted and transformed by the post processor.
UI Elements Present:

Checkbox: “Manually set resolution / maximum departure”
Input fields (disabled unless checkbox is checked):

Maximum Departure (999.99999800 shown)
Linear Resolution (0.00010000)
Rotary Resolution (0.00100000)


Note text (red): automatic setting is recommended
Group box: Motion Register Modality

Radio options:

Motion registers are modal
Motion registers are non‑modal (GXYZABCF)
Motion registers are non‑modal (XYZABC)




Group box: CL Points with 3 Params XYZ in MULTAX Mode

Radio options:

Use previous tool axis
Set tool axis = 0,0,1





Programmer Actions:

Select whether motion registers should be modal or non‑modal (affects G‑code verbosity).
Choose whether linear/rotary resolution should be manually defined or left to system defaults.
Select tool‑axis behavior for MULTAX CL records.

Mapping to AI‑Assisted G‑POST Builder:

AI should infer:

Required modal/non‑modal motion register formatting.
Resolution values that determine output precision in FIL/CIMFIL hooks.
Whether to interpret CL tool‑axis parameters explicitly or rely on previous tool orientation.


AI-generated post logic should:

Output correct G‑code based on modal/non‑modal register choice.
Apply linear/rotary resolution filters to motion blocks.
Map MULTAX CL axis triplets to rotary output behavior.

## Tab/Section:
## Type, Specs, & Axes → Axes → Axis Limit Checking and Axis Values
Purpose:
Defines machine axis home location, minimum and maximum travel limits, and limit checking behavior. These values constrain CL → G‑code conversion, preventing output motions beyond the machine’s physical travel.
UI Elements Present:

Axis Limit Checking group:

Radio buttons:

No limit checking
Perform limit checking


Checkbox: Use automatic repositioning (disabled until “Perform limit checking” is selected)
Checkbox: ZW axis control


Axis Values and Limits table:

Axes shown:

X
Y
Z
A
B
C


Columns:

Home
Minimum
Maximum


Numeric input fields for each axis value



Programmer Actions:

Define allowable axis travel for each machine axis.
Set machine home position (often used for initialization and return-home logic).
Enable/disable machine limit checking during posting.
Optionally allow automatic repositioning if toolpaths exceed limits.

Mapping to AI‑Assisted G‑POST Builder:

AI should generate:

Axis-limit rule set for motion validation.
Automatic repositioning logic suggestions when CL data exceeds travel limits.
Machine-home initialization block for start/end sequences.


AI should infer FIL/CIMFIL constraints such as:

Axis-clamping
Motion suppression
Automatic retract or safe positioning behaviors

## Tab/Section:
## Transforms & Output → Transformation
Purpose:
Defines translation offsets for input CL coordinates and output machine coordinates. Also allows output scaling and tool-axis XYZ‑based adjustments.
UI Elements Present:

Group: Input Transformation

Dropdown: Transformation Type (Simple X, Y, & Z Translation)
Translation fields:

X‑Axis
Y‑Axis
Z‑Axis


Button: Note


Group: Output Translation

X‑Axis
Y‑Axis
Z‑Axis
A‑Axis
B‑Axis
C‑Axis


Group: Adjust XYZ Output Along Tool Axis

Numeric field: distance


Group: Output Scale

Scale fields for each axis:

X‑Axis
Y‑Axis
Z‑Axis
A‑Axis
B‑Axis
C‑Axis





Programmer Actions:

Apply coordinate shifts to incoming CL data.
Apply translation offsets to outgoing machine coordinates.
Scale axes when needed to match machine controller units.
Adjust XYZ output along tool-axis direction for specific machine behaviors.

Mapping to AI‑Assisted G‑POST Builder:
AI should infer:

Input translation rules for CL-to-machine coordinate alignment.
Output translation offsets based on machine zero location or controller requirements.
Axis scaling factors for unit conversions (e.g., metric ↔ inch).
AI should generate:
FIL or post logic that applies the correct transforms before XYZ/ABC output.
Tool-axis vector-based adjustments for XYZ output when required.

## Tab/Section:
## Transforms & Output → Output
Purpose:
Defines the method used to convert CL XYZ positions into machine output coordinates. Controls handling of tool length, offset distance, tooltip location, and how IJK/rotary data is passed through the post.
UI Elements Present:

Group: Output Method

Radio: Default – enable spindle control point XYZ output with tool length & offset distance
Radio: Gantry – XYZ output for gantry-type machines using tool-tip programming
Radio: Other – advanced XYZ output for controllers with complex options (e.g., Heidenhain)


Group: Tooltip Control (all disabled unless a specific mode requires them)

Radio: Adjust as positive distance
Radio: Adjust as negative distance
Radio: Output Input/CL (xyz) and ABC angles
Radio: Output Input/CL (xyz) and Input/CL (IJK)
Sub‑group: IJK Output Options

Radio: FIL to output IJK (Default)
Radio: GPost to output IJK




Group: Adjustment Type

Radio: Adjust for tool length and offset distance
Radio: Adjust for tool length only
Radio: Adjust for offset distance only


Note section: Defines the difference between pivot distance and directed offset distance.

Programmer Actions:

Choose the machine’s core XYZ output type.
Define whether output is spindle-controlled or tool-tip controlled.
Select how tool-length compensation should be applied.
Choose whether IJK vectors are output by FIL or GPOST engine.
Determine offset direction for various machine head/table configurations.

Mapping to AI‑Assisted G‑POST Builder:
AI should infer:

Whether output is spindle-point based or tool-tip based.
When CL data requires tool-length adjustments or offset pivot transformations.
Whether IJK vectors should be calculated in FIL or in the AI‑generated post template.
AI should generate:
Proper kinematic transformation logic for XYZ + rotary outputs.
Offset distance compensation rules for rotary heads/tables.
Auto-selection of G‑code or controller modes based on machine class.


## Tab/Section:
## Planar Machining → Main Planar Machining Setup
Purpose:
Defines whether planar machining mode is enabled and how rotary-axis orientations, output angles, and tool-axis transformations are determined. This screen controls how planar toolpaths are interpreted and converted into rotational machine output.
UI Elements Present:

Checkbox: Enable Planar Machining
Group: Starting Mode

Radio: Off
Radio: On


Group: Rotation Matrix Defined By

Radio: CSYS / MCS / MSYS / CAMERA input
Radio: CSYS / MCS / MSYS / CAMERA input with origin shift
Radio: Use toolaxis from GOTO


Group: G‑Code

Radio: Use G-Code: [input field]
Radio: Siemens 800


Group: Output Method

Radio: Output ABC orthogonal angles
Radio: Output ABC machine axes angles
Radio: Output Euler angles IJK
Radio: Output Euler angles Fanuc mode IJK
Radio: Output Euler angles Fanuc mode IJ, K=0


Group: Position Rotary Axis in Machine Coordinates

Checkbox: Position to ABC before rotation with G‑Code: [input field]
Checkbox: Position to ABC after rotation with G‑Code: [input field]



Programmer Actions:

Turn planar machining ON/OFF.
Choose how rotation matrices should be derived (CSYS-based or tool-axis based).
Select the angle output format (ABC, machine axes angles, Euler angles).
Specify G‑codes used for positioning rotary axes.
Configure pre/post rotation positioning behavior.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

Required angle-output method (ABC vs Euler vs machine angles).
Which coordinate system is used to compute planar rotation matrices.
When tool-axis vectors should override CSYS rotation inputs.
G‑code mapping for rotary positioning both before and after rotation.
AI should generate:
Correct transformation matrices for planar machining.
FIL logic for ABC/Euler angle output formatting.
Automatic detection of planar machining mode based on CL.


## Tab/Section:
## Planar Machining → User Blocks
Purpose:
Allows the NC programmer to insert user-defined G‑code blocks before and after rotary-axis rotation during planar machining. These blocks can configure machine behavior, set modes, or output special commands that must precede or follow a rotation event.
UI Elements Present:

Two main sections:

User Defined Blocks BEFORE rotation

Numeric spinner: Number of blocks before
Empty block-entry area (will populate after setting quantity)


User Defined Blocks AFTER rotation

Numeric spinner: Number of blocks after
Empty block-entry area (will populate after setting quantity)




Instruction note:

“Each block may contain up to 66 characters. Trailing spaces will be ignored.”



Programmer Actions:

Specify how many blocks should be output before rotation.
Specify how many blocks should be output after rotation.
Populate each block with custom text when fields appear.
Use this to insert modal changes, safety statements, custom positioning, or controller commands.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

When rotation events occur (ABC changes).
How many user blocks need insertion before/after rotation.
The content of these blocks, if they exist in the configuration or must be recommended.
AI should generate:
FIL “INSERT” blocks at the correct event triggers.
Conditional output rules (e.g., “if rotary-axis movement detected… output before/after blocks”).
Structured placeholders for additional custom user blocks.

## Tab/Section:
## Right Angle Head → Main Setup
Purpose:
Controls whether a right‑angle head or tool-holder adapter is used, defines tool direction for right‑angle head machining, specifies holder offsets, and manages rotary-axis output suppression for non‑5‑axis machines.
UI Elements Present:

Checkbox: Right angle head or holder support required
Button: Help
Group: Starting Tool Direction for Right Angle Head

Radio options:

Default (see note)
POSX
POSY
NEGX
NEGY


Note: default is NEGZ unless overridden with SET/cmd


Holder Number Address (single entry field)
Group: Holder Offset Values (spindle to holder)

Along X‑Axis
Along Y‑Axis
Along Z‑Axis


Group: Non 5‑Axes ABC Axis Output Suppression

Checkbox: A‑Axis output suppression
Checkbox: B‑Axis output suppression
Checkbox: C‑Axis output suppression


Red note describing GPOST commands:

SET/HED
SET/HOLDER
SETTOOL



Programmer Actions:

Enable right-angle head mode.
Select initial tool direction relative to machine axes.
Enter offset values between spindle centerline and right-angle head tool-line.
Suppress unused rotary axes for machines that do not support full 5‑axis rotation.
Enter holder number for machines that support tool-holder indexing.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

Tool-vector recalculation rules for right-angle machining.
Spindle-to-holder offsets required to correctly compute XYZ output.
Whether ABC axes should be suppressed to avoid invalid motions.
AI should generate:
FIL routines for vector transformation (e.g., adjust tool axis using POSX/POSY/etc).
Automatic tool-direction initialization blocks.
Compensation for holder offsets when converting CL coordinates to machine output.


## Tab/Section:
## File Formats → MCD File → MCD File Format
Purpose:
Defines the mapping between CL record addresses and the post-processed output format. This screen controls the order, aliasing, and numeric format types for each address used in the CNC file.
UI Elements Present:

Multi-column list showing:

ORDER
ADDR (Address: N, G, X, Y, Z, etc.)
DESCRIPTION
BEFORE ALIAS
AFTER ALIAS
METRIC FMT
INCH FMT


Visible address entries include:

Sequence Nbr (N)
Prep Functions (G)
Extra 2
Axis outputs X, Y, Z
Cycle DWELL
Cycle RAPID Stop
Arc outputs (X‑Axis Arc, Y‑Axis Arc, Z‑Axis Arc)
Feedrate
Cutter Compensation
Tool Length Compensation
Spindle
Tool
M‑Codes
Primary/Secondary Rotary Axes


Buttons:

Edit Selected Address…
Move Selected Address



Programmer Actions:

Review or adjust address order for output formatting.
Set alias commands before or after each code (e.g., add “G94” before feedrate, etc.).
Choose metric and inch formats for each output address.
Customize formatting of X/Y/Z/ABC to match controller requirements.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

The required order of output codes for the final machine program.
Aliasing rules (pre/post modifiers) for each address.
Numeric format types for metric/inch outputs.
AI-generated output should include:
Correct formatting templates for each code type.
Structure for address priority and sequence ordering.
Automated conversion tables for switching between inch/metric modes.


## Tab/Section:
## File Formats → MCD File → General Address Output
Purpose:
Defines decimal formatting, spacing between addresses, and uppercase/lowercase output rules for the final NC tape. These options control the readability and controller‑specific formatting of G‑code.
UI Elements Present:
Define Decimal Control

Radio options:

Default (no special control)
Output decimal only if needed
Output at least one zero


Example shown:

If the output is "X12.", show as "X12" in the configured format.



Insert a blank before each address

Checkbox (checked in screenshot)

Upper / Lower Case Characters In Tape File

Radio options:

No conversion (Default)
Convert to uppercase
Convert to lowercase


Note in red: use only if needed by the control; otherwise unnecessary processing.

Programmer Actions:

Select how decimal points should appear in NC output.
Enable or disable automatic spacing between addresses.
Choose text-case format for G/M codes and addresses (uppercase/lowercase).
Ensure the output matches controller requirements to avoid syntax errors.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

Decimal formatting rules needed for the chosen CNC controller.
Whether spacing should be added between addresses to improve parsing.
Required case sensitivity of controller commands.

AI should generate:

FIL rules that apply decimal trimming or formatting.
Automatic spacing rules inserted between output addresses.
Case‑conversion logic that is applied uniformly across entire output program.


## Tab/Section:
## File Formats → MCD File → File Type
Purpose:
Defines the file extension used for CNC output files. Ensures compatibility with controller file import requirements or company standards.
UI Elements Present:

Group: MCD File Type (extension)

Radio: Use system default (e.g., *.put1, *.tap)
Radio: Specify extension (selected)
Input field: Extension = “nc”


Note: maximum 6 characters; valid characters are lowercase letters, digits, and underscore.

Programmer Actions:

Choose whether the default system extension should be used.


Enter custom file extension (e.g., “nc”, “tap”, “gcode”, etc.).
Ensure extension matches machine/controller loading expectations.

Mapping to AI‑Assisted G‑POST Builder:
AI should infer:

The preferred extension for this machine’s output files.
Whether extension naming follows company standards or machine-specific rules.

AI should generate:

Post templates that export files with the correct extension.
Warnings when incompatible extensions are requested.
Output save-path logic based on extension type.


## Tab/Section:
## File Formats → List File
Purpose:
Controls formatting of list/verification files—documents that show a human-readable version of posted output. Used for debugging, reviewing, or validating post behavior.
UI Elements Present:

Input field: Option File Title (shown: FANUC OM CONTROL)
Dropdown: Verification Print method (Generate verification print)

Warnings Group:

Checkbox: Suppress all warnings
Checkbox: Suppress major word warnings

Page Formatting Group:

Checkbox: Print page heading
Numeric field: Number of Lines per Page (51 shown)

Tape Image Group:

Radio: Print non-formatted version (selected)
Radio: Print formatted version

Miscellaneous Group:

Checkbox: Identify LINTOL blocks
Checkbox: Include input statements in list file

Input Printing Control Group:

Several optional checkboxes (disabled):

Skip printing of FIL generated commands
Skip printing of INSERT text commands
Skip printing of PPRINT text commands
Skip printing of PARTNO text commands



Programmer Actions:

Name the list/verification file for documentation.
Choose whether to display warnings.
Format the page output (heading + page length).
Choose formatted vs non-formatted tape output.
Enable advanced visibility options, such as identifying LINTOL blocks or showing input statements.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

Required list-file formatting for debugging and machine validation.
Whether warnings should be suppressed during generation.
How to print formatted vs raw tape image depending on user preference.

AI should generate:

Structured list-file generation templates.
Optional inclusion of CL input, FIL commands, comments, and verification blocks.
Page heading and pagination logic for readability.


## Tab/Section:
File Formats → Sequence Numbers
Purpose:
Controls how block sequence numbers (N‑words) are generated in posted output. This includes start value, increment, max value, aliasing, skip character behavior, and when SEQNO is displayed (INSERT/PPRINT).
UI Elements Present:
Parameters Group:

Maximum Sequence Number: 9999.00000000
Start Sequence Number: 10.00000000
Sequence Number Increment: 10.00000000
Checkbox: Turn off Sequence Number at start
Group: “Sequence Numbers are output every ‘n’th block”:

Spinner: n = 1



Sequence Number Character Group:

Alignment Block: 79( O )
Alias input: O

Operator Information Block Group:

Checkbox: Output SEQNO on INSERT
Checkbox: Output SEQNO on PPRINT

OPSKIP Character Group:

Checkbox: Block delete is available
OPSKIP Character: 47( / )
Alias input: /

Programmer Actions:

Define numeric sequence generation rules (start, increment, max).
Choose how often sequence numbers appear (every n‑th block).
Configure alias used for sequence numbers (e.g., “O”).
Enable SEQNO output during INSERT and PPRINT debugging statements.
Set block delete (skip) character to include “/” where needed.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

The correct sequence-number insertion cadence (every block vs every n‑th block).
SEQNO alias behavior for controllers requiring nonstandard sequence labels.
Whether block-delete lines must be generated using OPSKIP characters.
AI should generate:
FIL logic that increments sequence numbers according to user settings.
Conditional output rules for SEQNO on INSERT/PPRINT.
Support for block-delete characters on optional blocks.


## Tab/Section:
File Formats → Simulation File
Purpose:
Determines whether time and absolute-position files are generated for machine simulation. These files typically support external simulators requiring XYZABC positional logs or cycle-time reporting.
UI Elements Present:

Radio options:

No time and absolute file needed (default)
Generate time and absolute files for XYZABC axis



Programmer Actions:

Decide whether to create auxiliary simulation output files for verifying motion.
Enable detailed XYZABC logging for external simulation tools if required.

Mapping to AI‑Assisted G‑POST Builder:
AI should infer:

Whether simulation log files need to be generated during posting.
Whether XYZABC continuous positions must be captured at every CL → G‑code conversion.
AI should generate:
Optional FIL routines that write motion logs to external simulation output.
Time‑based motion sampling if time logs are required.

 
## Tab/Section:
File Formats → HTML Packager
Purpose:
Defines which files (source, list, punch, option, FIL) should be collected and combined into a single HTML package. This HTML output represents a consolidated snapshot of all input/output files from a GPOST run.
UI Elements Present:
Text description:

Explains that selected files will be packaged into one HTML file with an ".htm" extension, created at the end of posting.

Files to Include in the HTML File:

Checkbox: Source file (acl, ncl, etc.)
Checkbox: LST file
Checkbox: Punch file (tap, pnn, etc.)
Checkbox: Option file (the OFG file)
Checkbox: FIL file

Programmer Actions:

Select which data sets (source, tape, list, FIL, etc.) should be included in an HTML summary.
Use HTML report for validation, documentation, or review purposes.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

Which files should be bundled in the final HTML output.
What components are necessary for post-validation.
AI should generate:
Logic to package selected files automatically after posting completes.
Naming rules and structure for HTML packaging.

## Tab/Section:
Start/End of Program → General
Purpose:
Controls general NC program formatting such as DNC mode, STOP/START rewind codes, optional user-defined blocks, tape-image settings, and miscellaneous post-processing behaviors.
UI Elements Present:
Format Group:

Checkbox: DNC format
Units of Leader (numeric input)
Units of Trailer (numeric input)
Checkbox: EOB character at end of each block tape image
Checkbox: Tape readable PARTNO
Checkbox: Man readable PARTNO

Output Group:

Checkbox: Program number
Checkbox: Time stamp
Checkbox: Rewind STOP code at beginning of NC code
Checkbox: Output user defined startup blocks
Checkbox: Output user defined end of program blocks
Checkbox: Rewind START code at end of NC code

Miscellaneous Group:

Checkbox: Merging post
Checkbox: Use _OUTPTP to edit MCD blk
Checkbox: Use _MCDWT macro to edit MCD blk
Checkbox: Use _LSTWT macro to edit LST blk
Checkbox: Discard MCD file with FIL error

Programmer Actions:

Define whether the NC tape is DNC-compatible.
Enable automatic STOP at beginning and START at end.
Include or omit program numbers and timestamps.
Enable user-defined startup/end blocks.
Determine whether MCD/LST blocks can be edited via macros.
Set error-handling behavior for MCD files.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

The formatting and structural requirements for the tape output.
Whether to generate automatic STOP/START logic.
When to include startup/end blocks.
How error conditions should be handled for MCD files.

AI should generate:

FIL code for inserting EOB characters.
START/STOP insertion logic.
Support for merging posts or macro-editing routines.


## Tab/Section:
Start/End of Program → Codes/Chars
Purpose:
Defines special characters for leader, end-of-block (EOB), STOP/START rewind codes, and their aliases used in NC program formatting.
UI Elements Present:
Leader Character Group:

Text: “No leader specified”

EOB Character Group:

EOB Character: 36( $ )
EOB Alias: $

Rewind Stop Code Character Group:

Stop Code: 37( % )
Alias: %
Note: STOP code is located at the beginning of NC code.

Rewind Start Code Character Group:

Checkbox: Use normal rewind start code
Note: START code is located at the end of NC code.

Programmer Actions:

Define or adjust EOB character.
Adjust STOP and START rewind characters.
Specify custom alias characters if controller uses special formatting.
Manage leader character when controller requires leading formatting codes.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Necessary special characters for the machine controller.
How STOP and START rewind characters must be inserted.
AI should generate:
Automatic insertion of EOB, STOP, START characters in correct block positions.
Alias handling logic for formatting rules.


## Tab/Section:
Start/End of Program → Default Prep Codes
Purpose:
Defines default G-code modal settings such as inch/metric mode, absolute/incremental mode, feedrate mode, and circular interpolation plane. Also controls units for input and output.
UI Elements Present:
Default Codes Group:

Inch/Metric Mode: 70
Absolute/Incremental Mode: 90
Feedrate Mode: 94
Circular Interpolation Plane: 17
Checkboxes (disabled due to defined startup blocks):

Output code to tape image (four locations)



Post Units of Measure Group:

Input: Dropdown (Same as NCL units)
Output: Dropdown (Same as NCL units)
Option File Units: Dropdown (Inch)
Note: if only one option is available, either Inch or Metric code is invalid (NA).

Programmer Actions:

Define default G-code modal states at program start.
Choose whether units follow NCL or override to a new unit system.
Ensure unit consistency between CL, FIL, and output tape.
Control whether default modal codes are printed in the NC output.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

The modal states required at program start for safe machine operation.
The default plane and feed mode for this controller.
Whether inch/metric outputs are required or optional.

AI should generate:

Startup modal block templates (G70, G90, G94, G17).
Unit conversion logic when CL input units differ from output units.
Ability to suppress modal outputs if unneeded or already covered by user-defined blocks.



## Tab/Section:
Start/End of Program → Start Prog
Purpose:
Defines user‑defined startup blocks that appear at the beginning of the posted NC program. These blocks allow custom initialization commands, safety statements, or controller-specific setup lines before any machining motion.
UI Elements Present:

Section: User Defined Startup Blocks

Spinner: “# of Lines to Output” (value currently 0)
Large empty placeholder area where block text fields will appear once the number is > 0



Programmer Actions:

Set the number of custom startup blocks to output.
After selecting a number, populate each block with custom G/M codes or comments.
Use this feature to prep the machine before program execution (e.g., setting modes, clamping fixtures, enabling coolant).

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

Whether startup blocks are required for this post configuration.
The content and ordering of startup blocks (if provided by the user).

AI should generate:

FIL/INSERT logic to place these startup blocks at the top of the NC output.
Conditional behavior: only output blocks if count > 0.
Template placeholders that Codex can use when constructing automated post-startup logic.


#Tab/Section:
Motion → General
Purpose:
Controls how the post handles identical motion points—where two consecutive CL points produce zero motion. This prevents unnecessary or redundant blocks and specifies behavior in MULTAX scenarios.
UI Elements Present:

Section: Identical Points Handling

Radio: Do not output the repeat point
Radio: Output the repeat point (selected)
Radio: Output zero length move during MULTAX



Programmer Actions:

Choose whether repeated XYZ values produce a block or are suppressed.
Decide how MULTAX tool-axis zero-length movements should be reflected.
Prevent clutter by suppressing zero-motion moves unless required for controller stability.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

When CL blocks represent identical coordinates.
Whether to suppress or output duplicate move commands.
Whether MULTAX-specific zero-length moves need forced output.

AI should generate:

Automatic motion-filter logic.
Mode-aware handling for MULTAX zero-motion orientation events.
Clean-up routines to minimize redundant G-code while retaining accuracy.


## Tab/Section:
Motion → Linear
Purpose:
Defines linear interpolation behavior, output grouping of axes, MULTAX linearization routines, and handling of singular-axis moves for lintol-type motions.
UI Elements Present:
General Group:

Linear Interpolation: numeric field (value 1)
Checkbox: Prep Code is modal

Output Group:

Radio: Output XYZ in one block
Radio: Output XY then Z
Radio: Output Z then XY

Multax Motion Linearization Group:

Checkbox: Use linearization
Sub-options (disabled until linearization is checked):

Use distance method
Use distance with angle method (Gantry / Head machine)
Use distance between midpoint method
Use equal number of points (1–99)
Use equal distance segments method


Fields:

Distance Tolerance
Vector Angle Tolerance
Number of Points



Singular Axis Move for Lintol Motion Group:

Radio: Allow singular axis move
Radio: Skip singular axis move
Radio: Output intermediate points

Spinner: Number of Points



Programmer Actions:

Select how XYZ motions should be grouped in linear blocks.
Enable or disable MULTAX linearization for smoother toolpath conversion.
Choose a linearization method based on machine type.
Define tolerances and number-of-points for segmentation.
Handle singular-axis moves with skip, allow, or interpolation behavior.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

Required linear motion format (grouped vs separated axes).
Whether MULTAX paths need smoothing or segmentation.
Tolerances used to decide when segmentation is necessary.
How singular-axis moves should be interpreted for lintol motions.

AI should generate:

FIL routines for segmenting rotations and linear moves.
Auto-selection of the correct linearization method based on toolpath complexity.
Output grouping rules (XYZ vs XY+Z vs Z+XY).
Singular-axis move logic that avoids controller errors.


## Tab/Section:
Motion → Rapid
Purpose:
Defines how rapid moves (G0 / positioning moves) are generated, including XY/Z positioning codes, rapid addresses, short‑rapid behavior, and miscellaneous rapid‑motion parameters such as feedrate prep codes and velocity.
UI Elements Present:
Positioning Group:

Positioning XY Code: numeric field (0)
Positioning Z Code: numeric field (0)
Checkbox: Prep Code is modal

Rapid Address Group:

Rapid Address: empty entry field
Button: Set Rapid Format (disabled until Rapid Address assigned)
Checkbox: Enter rapid value?
Rapid Value: numeric entry field (disabled)

Short Rapid Traverse Group:

Minimum Distance: numeric field
Feedrate Below Minimum: numeric field

Miscellaneous Group:

Positioning Velocity: 200.00000000
Feedrate Prep Code: “NR”
Checkbox: Output redundant F code after Rapid
Motion Analysis (Advance … Retract): dropdown with selection:

“XY rotary then Z … Z then XY rotary”



Programmer Actions:

Define codes for rapid positioning motions.
Configure how rapid formats (XY-only, Z-only, combined) are output.
Adjust minimum-distance checks for short rapid moves.
Set rapid velocity and additional prep codes.
Enable or disable redundant feedrate output after rapid blocks.
Configure the motion-analysis order for rotary vs linear axes on rapid retract/advance.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Rapid motion output style for the machine (combined vs separated axes).
Minimum-distance logic to filter out extremely small rapid moves.
Use of feedrate prep codes during rapid motion sequences.
Motion-order sequencing between rotary and linear axes.

AI should generate:

FIL routines that adjust rapid motion formatting.
Rapid behavior logic (XYZ grouping, redundant feedrate suppression, motion ordering).
Optional short‑rapid handling for safe positioning moves.


## Tab/Section:
Motion → Circular → General
Purpose:
Controls circular interpolation output rules such as G2/G3 prep codes, modal behavior, circle-center output format, arc segmentation, tolerances, and miscellaneous parameters.
UI Elements Present:
Codes Group:

Checkbox: Disable circular interpolation
Clockwise Prep (G2): numeric field (2)
CounterCW Prep (G3): numeric field (3)
Checkbox: Prep / G-codes modal
Checkbox: XYZ codes modal

Circle Center Output Group:

Dropdown: Output IJK

Maximum Degrees Per Block:

Dropdown: 360 degrees per block

Correction Method:

Dropdown: Do not correct for last CL point not being on true arc

Miscellaneous Group:

Maximum Radius: numeric field (999.9999000)
Circle Z Deviation Tolerance: numeric field
Circle 360‑deg Start-End Point Tolerance: numeric field
Checkbox: True radial feedrate calculation
Checkbox: Skip minimum 3‑points test for G2/G3
Checkbox: Output F code with every circle block

Programmer Actions:

Choose clockwise/counterclockwise G-codes.
Set modal vs non-modal code behavior.
Select circle-center output (IJK vs R vs others).
Define arc segmentation rules, tolerances, and correction options.
Adjust feedrate/calculation options for circular moves.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Proper circular interpolation format (IJK vs R).
Modal structure for circular G2/G3 output.
Whether arcs require segmentation based on degrees-per-block settings.
Tolerance-based filtering to avoid invalid arc transforms.

AI should generate:

Arc-generation logic with IJK formatting.
Optional G2/G3 segmentation logic based on tolerance settings.
Feedrate and correction methods depending on machine type.


## Tab/Section:
Motion → Circular → IJK Modifier
Purpose:
Defines how IJK values are interpreted and output in both absolute and incremental modes for circular interpolation.
UI Elements Present:
Absolute Mode:
Radio options for “Output IJK register contents as”:

Delta arc offset distance unsigned
Center to start point distance signed
Start point to center distance signed
Absolute coordinates of radius center (selected)

Incremental Mode:
Radio options for “Output IJK register contents as”:

Delta arc offset distance unsigned (selected)
Center to start point distance signed
Start point to center distance signed

Miscellaneous:

Checkbox: IJK output when zero
Checkbox: IJK code modal

Programmer Actions:

Choose how IJK values should be interpreted for absolute and incremental arc formats.
Define whether zero IJK values should be output or suppressed.
Select modal or non-modal output behavior for IJK codes.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Required mode for IJK arc-center calculations (absolute vs incremental).
How CL data converts to correct IJK representation.
Whether zero IJK values must be explicitly emitted to satisfy controller requirements.

AI should generate:

FIL transformations converting CL arc data into correct IJK formats.
Modal behavior rules for IJK output.
Arc-center transformation logic for both absolute and incremental coordinate modes.


## Tab/Section:
Motion → Circular → Plane Selection
Purpose:
Defines G-code plane-selection behavior for circular interpolation (XY, ZX, YZ). Controls which plane codes are used and how the post behaves when the CUTCOM plane and circular plane differ. Also sets rotary direction rules for arcs in different planes.
UI Elements Present:
Prep / G-Codes Group:

XY Code: 17
ZX Code: 18
YZ Code: 19

Cutcom Plane Group:

Radio: Use G01 if Circle / plane does not match Cutcom / plane
Radio: Output G02/G03 and switch to Circle / plane

Circular Moves Group:
Three checkboxes:

Circular move from +X to +Y is counterclockwise
Circular move from +X to +Z is counterclockwise
Circular move from +Y to +Z is counterclockwise

CIRCLE/cmd Translation Group:

Checkbox: Reverse G18-ZX arc direction for CIRCLE/cmd translation

Programmer Actions:

Set plane-selection codes for G17/G18/G19 behavior.
Choose how to handle plane mismatches between CUTCOM plane and circular interpolation plane.
Define arc rotation direction for different rotary planes.
Optionally reverse arc direction for special controller translation rules.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Which plane codes to issue for arcs based on CL orientation.
How to handle cases where plane selection conflicts with CUTCOM plane.
The proper counterclockwise vs clockwise direction conventions per plane.
AI should generate:
Plane-selection logic (G17/G18/G19 output).
Automatic switching logic when CUTCOM plane mismatches arc plane.
Arc-direction transformation rules.


## Tab/Section:
Motion → Circular → ARCSLP Interpolation
Purpose:
Controls helical interpolation output settings for ARCSLP blocks, including K-value formatting, block enable/disable behaviors, and special rules for Heidenhain-type output.
UI Elements Present:
Helical Interpolation Group:

Checkbox: Output ARCSLP blocks
K-Code in ARCSLP is: dropdown (in radians absolute)

ARCSLP K Output Group:
Radio options:

Enable K output (selected)
Disable K output
Disable K and output Heidenhain TNC blocks

Additional Options:

Checkbox: Skip Z move test for 1st circle following ARCSLP/OFF
Checkbox: Scale ARCSLP/ON,Z by toolaxis vector

Programmer Actions:

Enable/disable ARCSLP helical blocks in the post.
Choose the unit/type of K values (radians absolute, degrees, incremental, etc.).
Select whether K should be output at all, or replaced with Heidenhain‑style blocks.
Modify Z-move skip behavior on transitions.
Scale helical interpolation Z using tool-axis vectors for advanced helical control.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Whether ARCSLP is required by this machine/controller.
Proper formatting rules for K values.
Whether to emit Heidenhain-style blocks instead of ARCSLP.
Additional vertical-axis scaling rules.

AI should generate:

Helical interpolation routines honoring K-code format.
Optional Z-axis test suppression logic.
Conditional output for ARCSLP/OFF → ARCSLP/ON transitions.


## Tab/Section:
Motion → Cycles → Cycle Motion
Purpose:
Configures drilling and canned-cycle behavior such as Z-output mode (absolute vs incremental), clearance values, modal cycle behavior, addresses for cycle parameters, secondary-clearance plane handling, and retract-motion rules.
UI Elements Present:
General Group:
Output Type:

Absolute Z (selected)
Signed incremental Z
Unsigned incremental Z
Automatic Clearance Value: numeric field
Checkbox: Cycle motion analysis
Checkbox: R is from Last‑Z instead of normal Drill‑Z

Cycle Motion Data Modal Condition:

Radio: First cycle point only
Radio: All cycle points
Checkbox: Linear XY[Z] modal
Checkbox: Rotary ABC modal

Addresses Group:

Cycle Deep: K
Cycle Dwell: empty
Cycle CAM: empty
2nd Clearance Plane: empty

Secondary Clearance Plane Group:

Radio: Incremental
Radio: Absolute
Output G0 Move For:

Approach
Retract (selected)



Retract Motion Group:

Checkbox: Positive Z-axis retract
Retracting Axis Address: Z

Programmer Actions:

Choose Z-format for cycle output (absolute vs incremental).
Set clearance height behavior and modal cycle data handling.
Assign cycle address letters: depth, dwell, CAM, etc.
Configure secondary clearance plane output and G0 move direction.
Choose whether retract uses positive Z or another axis.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Proper canned-cycle Z‑output mode.
Required cycle-address mappings (K, dwell, CAM).
When secondary clearance plane is needed.
Whether retract must be positive Z only or axis‑dependent.

AI should generate:

Cycle block templates for drilling, pecking, boring, etc.
FIL logic for modal vs non-modal cycle data.
Secondary clearance plane logic.
Retract-motion rules for safe tool withdrawal.

## Tab/Section:
Motion → Cycles → Pulbac
Purpose:
Configures G98/G99 “Pulbac” behavior for canned cycles. These options determine whether return motions use initial‑point return (G98) or full retract (G99), and whether the codes come from the cycle command or are explicitly defined.
UI Elements Present:
Pulbac Availability:

Checkbox: G98 / G99 Pulbac available

G‑Code Group:
Radio options:

Pulbac G‑Code is from cycle command
Specify one G‑Code

G‑Code: numeric field


Specify multiple G‑Codes

G‑code for initial return as in G98 G81: numeric field
G‑code for full return as in G99 G81: numeric field



G‑Code Modality:
Radio options:

G98/G99 is modal, output for new CYCLE/cmd (selected)
G98/G99 is non-modal, also output after a G80 Z‑retract

Programmer Actions:

Enable Pulbac use in the cycle output.
Choose Pulbac source: cycle command vs user‑defined G‑codes.
Define modal vs non-modal behavior for G98/G99.
Ensure proper retract mode for drilling/peck/tapping operations.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Whether Pulbac (G98/G99) usage is required.
Source of Pulbac codes (auto vs specified).
Modal behavior based on user settings.

AI should generate:

Correct insertion of G98/G99 for cycle retracts.
Conditional logic: when G80 ends the cycle, output non-modal return (if chosen).
Templates for explicit G98/G99 code blocks.


## Tab/Section:
Motion → Cycles → MULTAX
Purpose:
Defines MULTAX behavior inside canned cycles — whether cycles behave like 3‑axis cycles or use MULTAX‑specific hardware/software cycle logic. Also determines how retract motions are output for MULTAX cycles.
UI Elements Present:
MULTAX Mode Cycle Group:
Radio options:

Same as 3‑axes mode (as set in cycle panel) (selected)
Use Software cycles for any toolaxis
Use Hardware cycles for any toolaxis
Mixed mode Software and Hardware cycles…

MULTAX Soft Cycle Retract Motion Group:
Radio options:

Output as Linear with maximum feed (selected)
Output as Rapid motion

Programmer Actions:

Decide whether canned cycles should behave like regular 3‑axis cycles or MULTAX‑compatible cycles.
Choose software vs hardware cycle methods depending on controller capabilities.
Define how retract moves should be output (linear vs rapid).

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Whether MULTAX cycles require special handling.
Software vs hardware method depending on machine type.
Required retract motion formatting.

AI should generate:

FIL routines for MULTAX cycle-axis transformations.
Linear vs rapid retract logic.
Multi-axis safe retract strategies.

## Tab/Section:
Motion → Cycles → UG Specific
Purpose:
Defines how the post handles Unigraphics (UG/NX) cycle commands when passed through Creo → CL → Post. Determines whether FIL or GPOST engine processes UG‑style cycle forms, and how Z‑values are treated in UG FEDTO commands.
UI Elements Present:
UG Cycle Processing Group:
Radio options:

FIL to process UG CY/cmd (selected)
GPost to process UG CY/cmd

Treat cy‑‑FEDTO, z Value Group:
Radio options:

Accept as is
Make it positive
Reverse sign

Programmer Actions:

Choose the correct interpreter for UG cycle commands (FIL vs GPOST).
Determine how FEDTO Z values should be output: unchanged, sign‑corrected, or reversed.
Ensure cross‑platform cycle consistency between UG‑style CL and Creo’s OFG post behavior.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Whether UG cycle formats need special parsing.
How Z‑sign corrections affect cycle blocks.

AI should generate:

FIL routines for cycle‑command translation (UG → post format).
Z‑value correction logic based on user selection.


## Tab/Section:
Motion → Cycles → Siemens‑840
Purpose:
Controls Siemens‑specific canned cycle output formatting and MULTAX rotary‑tilt cycle options. This page determines whether Siemens-style CYCLE810/MCALL cycles are used and how ROT/TRANS commands are generated for multi-axis operations.
UI Elements Present:
Output Siemens Cycle Group:
Radio options:

Siemens cycle not required (selected)
Output Siemens non‑modal CYCLE810() format
Output Siemens modal MCALL CYCLE810() format

Tilt Angle ROT Cycle for MULTAX Group:
Radio options:

Do not output ROT cycle format (default) (selected)
Output ROT cycle format for any tool axis
Output ROT and TRANS cycle format for any tool axis, TRANS xyz=Machine
Output ROT and TRANS cycle format for any tool axis, TRANS xyz=Part

Button:

View Note (opens description of ROT/TRANS behaviors)

Programmer Actions:

Decide whether Siemens CYCLE810/MCALL cycles should appear in NC output.
Choose whether ROT/TRANS commands are generated for tool-axis tilting in MULTAX.
Determine whether TRANS coordinates should reference machine axes or part axes.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Whether Siemens‑specific canned cycles must replace standard G‑code cycles.
If ROT/TRANS commands are required based on machine kinematics.
Whether coordinate transformations must output machine vs part reference systems.

AI should generate:

Siemens‑formatted cycles when selected, including MCALL or CYCLE810 syntax.
ROT/TRANS logic for multi-axis drilling/tapping when needed.
Context-sensitive coordinate basis (machine XYZ vs part XYZ).

## Tab/Section:
Motion → Curve Fitting
Purpose:
Enables curve-fitting routines (arc or spline fitting) to smooth toolpaths, reduce block count, and improve controller execution. Supports 3D arc fitting and multiple spline-fitting formats for different machine types.
UI Elements Present:
Enable Curve Fitting:

Checkbox: Enable curve fitting

Arc Fitting Group:

Checkbox: Enable arc fitting
Checkbox: Allow helical motion during arc fitting
3D Arc Format (radio options):

None (selected)
Fanuc
Siemens



Chordal Curve Fit Tolerance:

Numeric field: 0.0050000

Spline Fitting Group:

Checkbox: Enable spline fitting
Type (radio):

Nurb
Polynomial
Bezier


Output Machine Type (radio):

Fanuc
Siemens
Heidenhein
Maho



Other:

Checkbox: Use nurb prefix input

Programmer Actions:

Decide whether arc or spline fitting will be used.
Select acceptable tolerance for chordal error.
Choose spline type and match it to controller capabilities (Fanuc, Siemens, Heidenhain, etc.).
Enable helical arc fitting if needed for complex toolpaths.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Whether to convert toolpaths into fitted arcs/splines vs raw linear output.
Which machine/controller format (Fanuc/Siemens/etc.) to use.
Tolerance-based segmentation or fitting rules.

AI should generate:

Curve-fitting routines that reduce block count while maintaining accuracy.
Correct fitted output syntax, respecting chosen arc/spline formats.
Heuristic recommendations when fitting is inappropriate (e.g., extremely tight tolerances).


## Tab/Section:
Machine Codes → Prep / G‑Codes
Purpose:
Defines major modal G-codes used for prep and cycle operations, including axis presets, inch/metric modes, absolute/incremental modes, high-speed tapping format, and cycle-specific G‑codes.
UI Elements Present:
Axes Group:

Axes Preset: 92

Inch / Metric Group:

Inch Mode: NR
Metric Mode: 71

Absolute / Incremental Group:

Absolute Mode: 90
Incremental Mode: 91

High Speed Tapping Group:

Cycle / Tap - High: 84.2
Checkbox: Not Required (NR)
Checkbox: Not Available (NA)

Controller Capabilities:

Checkbox: Controller will accept multiple Prep / G‑codes
Checkbox: Prep and Aux Codes can be greater than 2 digits

Cycle / G‑Codes Group:

Cycle / Off: 80
Cycle / Drill: 81
Cycle / CSink: NA
Cycle / Deep: 83
Cycle / Tap: 84
Cycle / Bore: 85
Cycle / Ream: 88
Cycle / Thru: 87
Cycle / Face: 82
Cycle / Mill: 86
Cycle / Brkchp: NA

Programmer Actions:

Configure core modal settings for units and movement type.
Define supported cycle numbers (e.g., G81–G89 or custom formats).
Enable multi-digit G-code support if controller accepts nonstandard formats.
Set tapping cycle code and high-speed tapping rules.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

The modal structure for prep codes (units, absolute/incremental, axis presets).
Required G-code cycle identifiers for drilling, boring, reaming, tapping, and milling.
Whether multi-digit or multiple simultaneous G-codes are allowed.

AI should generate:

Startup modal blocks using G90/G91/G71/GNR/etc.
Correct cycle definitions (G81–G89 or custom).
Conditional support for tapping and multi-digit codes.


## Tab/Section:
Machine Codes → Aux / M‑Codes
Purpose:
Defines auxiliary M‑codes for program control operations such as stop, optional stop, end-of-program, and rewind. Also controls whether multiple auxiliary M‑codes can be issued in the same block and whether multi-digit codes are supported.
UI Elements Present:
Aux Codes Group:

Stop Code: 0
OpStop Code: 1
End Code: 2
Rewind Code: 30

Additional Options:

Checkbox: Controller accepts multiple Aux / M‑codes (checked)
Checkbox: M‑Code axis clamping is available
Checkbox: Prep and Aux Codes can be greater than 2 digits

Programmer Actions:

Set basic program control M‑codes (stop, optional stop, rewind).
Enable multiple auxiliary codes in one block if the controller supports it.
Enable multi-digit codes when required for modern controllers.
Enable axis clamping if supported for tool-changing or fixture adjustment.

Mapping to AI-Assisted G‑POST Builder:
AI should infer:

Which auxiliary codes to output at program stops or rewind operations.
Whether to combine multiple M‑codes in a single block.
If multi-digit M‑codes must be supported and automatically formatted.

AI should generate:

Templates for blocks containing M00/M01/M02/M30 or equivalents.
Combined M‑code output logic when allowed.
Conditional axis clamping outputs for machines that support it.


## Tab/Section:
Machine Codes → Cutter Compensation → 2–3 Axis Compensation
Purpose:
Controls cutter compensation behavior (LEFT / RIGHT / OFF), diameter offset address, and optional PQ vector output. Also defines whether compensation codes are output with the XY motion block or separately.
UI Elements Present:
PQ Vectors:

Checkbox: PQ vectors output on each CUTCOM block

Output Group:

Checkbox: Cutter comp, prep, and offset codes output with XY motion blocks

Radio options inside (disabled until checkbox is selected):

Output prep code with XY for LEFT‑RIGHT‑OFF
Output prep code with XY for LEFT‑RIGHT and OFF by itself




Checkbox: Output sine and cosine of first compensated move with LEFT/RIGHT blocks
Checkbox: Output tool number as the diameter offset number when not specified

Prep / G‑Codes Group:

CUTCOM / LEFT: 41
CUTCOM / RIGHT: 42
CUTCOM / OFF: 40

Diameter Offset Address:

Address field: D

Programmer Actions:

Set CUTCOM compensation codes for LEFT/RIGHT/OFF.
Define whether to combine compensation with XY moves.
Enable sine/cosine output for precision compensation on certain controllers.
Choose how diameter offset (D‑address) is assigned.
Decide whether to output PQ vectors for compensation direction.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Compensation mode (LEFT/RIGHT/OFF) based on CL data.
Whether PQ vectors are required.
Where CUTCOM codes should be inserted relative to XY moves.
How to format D‑address for diameter offset.

AI should generate:

CUTCOM block insertion routines.
PQ‑vector computation logic if required.
Combined or separated compensation formatting rules.


## Tab/Section:
Machine Codes → Cutter Compensation → 5‑Axis Compensation
Purpose:
Defines 5‑axis cutter compensation with PQR vector output, vector-type selection, modality rules, and vector formatting limits for 5‑axis CUTCOM operations.
UI Elements Present:
PQR Vectors:

Checkbox: PQR vectors output on each CUTCOM / XYZ block
Button: View Note

Vector Type Group:
Radio options:

Unit Surface – vector points to imaginary surface 1 unit in direction of comp.
Unit Vector – vector represents unit vector which points in direction of comp.

Vector Modality Group:
Radio options:

Modal – output PQR always
Non‑Modal – output PQR if changed

Vector Formatting Group:
Buttons (inactive until enabled):

P – Vector Register Format
Q – Vector Register Format
R – Vector Register Format

Numeric Limits:

Minimum Vector: ‑3.2767000
Maximum Vector: 3.2767000

Programmer Actions:

Enable PQR vector compensation for 5‑axis CUTCOM.
Choose between Unit Surface vs Unit Vector behavior.
Set whether PQR vectors are always printed (modal) or only when changed.
Optionally format P/Q/R registers with custom scaling.
Validate vector ranges based on machine/controller limitations.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Whether machine requires 5‑axis vector compensation.
Preferred vector representation type (unit surface vs unit vector).
Modal vs non-modal behavior for vector output.
Vector register formatting and scaling rules.

AI should generate:

FIL/PQR calculation routines.
Logic for modal output of P/Q/R registers.
Range checking and clamping inside post-processor transforms.


## Tab/Section:
Machine Codes → Coolant
Purpose:
Defines all coolant‑related M‑codes, including mist, flood, high/low pressure options, and through‑spindle coolant. Also configures combined spindle/coolant commands and determines how coolant codes are output relative to motion blocks.
UI Elements Present:
Coolant Codes Group:

Coolant Mist: 7
Coolant Flood: 8
Flood (high pressure): 18
Flood (low pressure): 17
Through (high pressure): 28
Through (low pressure): 27
Coolant Default: 8
Coolant Off: 9

Coolant / Spindle Combined M‑Codes Group:

Checkbox: COOLNT/SPINDL combined M‑code
Checkbox: COOLNT / AUTO, ON
SPINDL/COOLNT CLW: 13
SPINDL/COOLNT CCLW: 14

Output Type Group:

Radio: On a block by itself (selected)
Radio: With the next XY block
Radio: With the next Z block
Checkbox: Output COOLNT/OFF code by itself

Programer Actions:

Assign coolant M‑codes for different coolant types.
Choose whether coolant commands should be combined with spindle commands.
Determine if coolant codes appear alone or attached to motion blocks.
Configure high/low pressure and through‑spindle coolant outputs.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

Which coolant codes to generate based on CL coolant toggles.
When coolant codes appear standalone vs paired with motion blocks.
Whether to output combined spindle/coolant commands.

AI should generate:

Automated coolant on/off sequence blocks.
Conditional logic for high‑pressure/through‑spindle coolant.
Combined spindle/coolant output formatting if enabled.


## Tab/Section:
Machine Codes → Feedrates → General
Purpose:
Defines feedrate override M‑codes, how feedrates are printed in the list file, and how feedrate codes are output relative to motion blocks. Also supports optional current F‑code output with modal blocks like G94/G95.
UI Elements Present:
Aux / M‑Codes Group:

Enable Feed Override: 51
Disable Feed Override: 50

Verification Print in List File Group:
Radio options:

Print in IPM (selected)
Print in IPR
Print in IPM or IPR per current mode

Code Output Group:

Checkbox: Prep / G‑Code output with motion block
Checkbox: Output current F‑Code with G94/G95 blocks (e.g., Vickers controller)

Programmer Actions:

Set M‑codes for enabling/disabling feed override.
Choose preferred feedrate reporting mode in list files (IPM/IPR).
Choose whether feedrate codes appear on motion blocks.
Enable compatibility with controllers needing explicit F-code restatement.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Feedrate override handling rules.
Preferred feed reporting format.
Whether feedrates must be included on every motion block or only modal changes.

AI should generate:

Proper F-code output routines.
Modal/non-modal feed formatting logic.
List-file feedrate reporting logic.

## Tab/Section:
Machine Codes → Feedrates → UPM Mode
Purpose:
Defines UPM mode (Units Per Minute) behavior, prep code for activating UPM mode, and feedrate parameters including minimum, maximum, and multiplier values. Controls advanced feedrate scaling used by certain controllers.
UI Elements Present:
Prep Code Group:

“Prep Code that establishes UPM Mode”: 94
Button: Feedrate Register Format

Feedrate Parameters Group:

Minimum Feedrate: 0.00100000
Maximum Feedrate: 200.00000000
Feedrate Multiplier: 1.00000000

Additional Option:

Checkbox: Output UPM mode for GOTO/xyz with rotary motion

Programmer Actions:

Set prep code for enabling UPM mode.
Define min/max feedrates used in UPM calculations.
Adjust multiplier for scaling UPM values.
Enable UPM for rotary‑involved motion if required.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Whether UPM mode is required for the machine.
Proper scaling logic for feedrates relative to multiplier and tolerance.
When UPM mode should auto-activate for rotary motions.

AI should generate:

UPM activation blocks using prep code 94.
Feedrate scaling routines.
Conditional UPM logic for multi-axis GOTO/XYZ moves.


## Tab/Section:
Machine Codes → Feedrates → UPR Mode
Purpose:
Defines the prep code for UPR mode (Units Per Revolution). UPR mode is typically used for spindle-dependent feedrate control, often for lathe-style or tapping operations where feed per revolution is required.
UI Elements Present:
Prep Code Group:

“Prep Code that establishes UPR Mode”: NA (not available)

This screen contains only a single input field indicating that the machine or this configuration does not support a designated UPR mode activation code.
Programmer Actions:

Review whether UPR mode is supported by the controller.
If UPR mode is required by the machine, define the prep code; otherwise leave NA.
Determine whether feed‑per‑rev commands must be handled manually in FIL.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Whether UPR mode is unavailable (NA) and thus should not be generated.
Whether UPR feedrates should be suppressed or translated into alternative feedrate formats.

AI should generate:

Logic to avoid UPR mode activation.
Alternative feedrate formatting if UPR is expected but not supported.


## Tab/Section:
Machine Codes → Feedrates → Inv Time Mode
Purpose:
Enables inverse-time feedrate mode (G93/G94-style behavior depending on controller), used for multi-axis and toolpath-dependent feedrate calculation. This page defines prep codes, feedrate parameters, inverse-time math method, and axis-velocity constraints.
UI Elements Present:
Output & Prep Code Group:

Prep Code Establishing Inv Time Mode: 93
Button: Feedrate Register Format
Checkbox: Output inv time feed for GOTO/xyz & rotary motion
Checkbox: Output A40–C40 feedrate adjustments

Feedrate Parameters Group:

Minimum Feedrate: 0.00100000
Maximum Feedrate: 200.00000000
Feedrate Multiplier: 1.00000000

Check Maximum Axis Velocity Group:
Radio/Options:

Auto adjust
Disable (selected)
Min time (minutes)
Min time (sec)
Minimum Time numeric field
Checkbox: Identify corrected block in listing
Button: View Note

Inverse Time Feedrate Group:
Radio:

Use circle arc len
Use circle radius

Method for Calculating Inv Time:
Dropdown: Use Iterative Method
Programmer Actions:

Enable inverse-time mode with the prep code (93).
Choose method for computing inverse-time (arc length vs radius).
Set feedrate limits (min/max/multiplier).
Decide whether to auto-adjust blocks exceeding axis-velocity limits or disable adjustment.
Enable special feedrate adjustments (A40–C40).
Select iterative or alternative calculation method.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

How to compute inverse-time feedrates (arc-wise vs radius-wise).
Prep code required to activate inverse-time mode.
Whether feedrate or block timing adjustments must be applied.
Required velocity checking logic and correction reporting.

AI should generate:

Inverse-time calculation routines.
Prep code G93 (or equivalent) output.
Feedrate adjustment logic tied to axis velocities.
Iterative method computation for multi-axis moves.


## Tab/Section:
Machine Codes → Fixture Offsets
Purpose:
Defines fixture offset address (e.g., G54/G55/H-type offsets), offset base value, and whether fixture offsets should appear on their own block or combined with XYZ/Z motion blocks.
UI Elements Present:
Prep / G‑Codes Group:

Offset Address: H
Base Value to be added: 0
Button: Note…

Output Type Group:
Radio:

On a block by itself (selected)
With next XY block
With next Z block

Programmer Actions:

Set fixture offset register address (H, G54-series, or other depending on controller).
Define the base value added to the selected offset (for machines requiring offset shifting).
Choose whether fixture offsets are output standalone or embedded within first motion block.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Correct fixture offset command structure.
Whether the offset needs to precede motion or accompany XYZ/Z block.
Interpretation of base value if offsets must be adjusted.

AI should generate:

Fixture offset initialization blocks.
Conditional logic to place fixture offsets according to user-selected output type.
Offset calculation routines using base values.

## Tab/Section:
Machine Codes → Tool Change Sequence → General
Purpose:
Defines tool-change timing, auxiliary M‑codes for tool changes, modal behavior of T‑codes, options for tool-length handling, forced rotary-axis resets, and optional tool-change positioning block output.
UI Elements Present:
Cycle Time Group:

Tool Change Time: 3.00000000
Output (dropdown):

“Do not output tool times to list”



Codes Group:

Auxiliary Code: 6
Tool Length Prep Code: NA

Output Options Group:
Checkboxes:

T‑Code is modal
Ignore tool length (v) in LOADTL/t,LENGTH,v
Output T code and M code on separate lines
Output tool number as length offset when not specified
Output next tool preselected with tool change
Force ABC rotary axes on next GOTO/motion block

Tool Change Positioning Group:
Radio options:

Do not output tool change positioning block (selected)
Output tool change positioning block with XYZ values
Output tool change positioning block with XYZABC values
Button: View Note

Programmer Actions:

Define auxiliary M‑code used for tool change sequence.
Determine whether T‑codes are modal or must be repeated.
Configure how tool-length information is used or ignored.
Choose whether to output separate T/M lines or combined.
Decide if tool-change positioning block should be emitted, and in what format (XYZ or XYZABC).

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Whether to output modal vs non-modal T‑codes.
Auxiliary sequence logic for tool-change M‑codes.
Whether tool-change positioning blocks are needed.
Whether to reset ABC rotary axes after tool changes.

AI should generate:

Robust tool-change routines, including T/M pairing rules.
Optional tool-length loading logic.
Positioning block output rules for both XYZ and XYZABC formats.


## Tab/Section:
Machine Codes → Tool Change Sequence → Tool Change Coordinates
Purpose:
Defines explicit machine coordinates for each axis (X/Y/Z/A/B/C) used during tool changes. Also configures how motion analysis handles tool-change-related transitions after LOADTL commands.
UI Elements Present:
Coordinate Groups:
Each axis has two radio options and one numeric field:
X‑Coordinate:

Current X
Specify coordinate: 999999.00000000

Y‑Coordinate:

Current Y
Specify coordinate: 999999.00000000

Z‑Coordinate:

Current Z
Specify coordinate: 30.00000000

A‑Coordinate:

Current A
Specify coordinate: 0.00000000

B‑Coordinate:

Current B
Specify coordinate: 0.00000000 (selected)

C‑Coordinate:

Current C
Specify coordinate: 0.00000000

Motion Analysis Option for RAPID/GOTO/pt After LOADTL Group:
Radio options:

Use tool change location for motion analysis
Output XY, then Z‑move, assume advance move

Programmer Actions:

Choose whether tool-change moves use current axis positions or specified coordinates.
Define appropriate XYZ and ABC positions for safe, collision-free tool changes.
Determine motion-analysis logic for post‑tool-change movements.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Tool-change coordinates for safe retract/approach sequences.
Whether to use current coordinates vs fixed tool-change locations.
Motion-analysis behavior for transitions following LOADTL.

AI should generate:

Tool-change safe-position moves (XYZABC).
Logic for staged XY→Z output if “Output XY then Z” is chosen.
Tool-change motion-validation routines.


## Tab/Section:
Machine Codes → Tool Change Sequence → User Blocks
Purpose:
Allows custom user-defined blocks to be inserted around tool changes. Users may apply a single set of user blocks for all tool changes or define separate blocks for first, second, and last tool changes.
UI Elements Present:
Same or Separate User Blocks Group:
Radio options:

Apply the same user block for all tool changes… (selected)
Set separate user blocks for 1st–2nd–last tool changes…

Button:

Next >

Programmer Actions:

Choose which style of user-block application is required: global or individual tool-change-based.
Define custom text to insert before/after each tool change (will appear after clicking Next).

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Whether tool-change user blocks are universal or tool-change-index-specific.
When to insert user blocks relative to tool-change M‑codes and motion.

AI should generate:

Logic for inserting user blocks at correct tool-change event boundaries.
Placeholder templates that Codex can fill with actual user block content.


## Tab/Section:
Machine Codes → Spindle → Spindle Codes
Purpose:
Defines spindle RPM behavior, number of spindle ranges, default range selection, and how spindle S‑codes are output. This section determines spindle speed formatting and placement in the output NC program.
UI Elements Present:
General Group:

Checkbox: Direct RPM is available (checked)
Number of Spindle Ranges: 1
Default Ranges: 1

Output S‑Code Group:
Radio options:

On a block by itself (selected)
With next XY block
With next Z block

Programmer Actions:

Confirm whether the machine uses direct RPM output or requires other spindle-speed encoding.
Specify number of spindle-speed ranges and choose the default range.
Determine S‑code placement relative to motion blocks.

Mapping to AI‑Assisted G‑POST Builder:
AI must infer:

Proper formatting of the S‑code (standalone vs combined).
Whether spindle ranges need to factor into RPM scaling or range selection.
How many RPM ranges the machine uses (1 in this case).

AI should generate:

Correct S‑code output templates based on selected format.
Logic for applying spindle range modifiers if more ranges are added.
Standalone S‑code block output when selected.

## Tab/Section:
Machine Codes → Spindle → Aux Codes
Purpose:
Defines auxiliary M‑codes for spindle direction, stop, orientation, locking/unlocking, and spindle-range auxiliary codes. Controls how spindle directionality and auxiliary logic is expressed in the NC program.
UI Elements Present:
Aux / M‑Codes Group:

Clockwise Code: 3
Counterclockwise: 4
Default Rot. Code: 3
Stop Code: 5
Orient Code: 19
Lock Code: (blank)
Unlock Code: (blank)

Spindle Range Aux / M‑Codes Group:

Range #1: NA

Programmer Actions:

Define spindle direction M‑codes (CW/CCW).
Configure spindle stop and spindle orientation codes.
Provide lock/unlock codes if machine supports spindle locking.
Provide range auxiliary codes if spindle ranges require separate M‑code activation.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Correct M‑codes for spindle CW, CCW, stop, and orient.
Whether spindle range changes require additional M‑code outputs.
Logic to avoid outputting unavailable codes (lock/unlock if empty; range NA).

AI should generate:

Spindle control blocks (M03/M04/M05/M19 equivalents).
Orientation-cycle logic when required.
Conditional suppression of undefined auxiliary codes.


## Tab/Section:
Machine Codes → Spindle → Direct RPM Speeds
Purpose:
Defines minimum and maximum RPM values for each spindle range. This establishes valid RPM boundaries for direct spindle-speed output.
UI Elements Present:
Minimum Speeds Group:

Range 1: 1.00000000
Range 2: (blank)
Range 3: (blank)
Range 4: (blank)
Range 5: (blank)
Range 6: (blank)

Maximum Speeds Group:

Range 1: 3000.00000000
Range 2–6: (blank)

Programmer Actions:

Set lower and upper RPM limits for spindle-speed validation.
Ensure that Curve Fitting, Tapping, and Feedrate settings do not exceed the spindle’s allowable RPM range.
Leave higher ranges blank if the machine does not support multiple ranges.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Valid RPM envelope for spindle outputs.
Whether the machine supports only one range (as shown).
The need to clamp or reject RPM input exceeding allowed minimum/maximum.

AI should generate:

Logic to enforce RPM limits in the output.
Range-selection logic if multiple ranges are introduced.
Standalone validation routines for RPM integrity.


## Tab/Section:
Machine Codes → Dwell Parameters → Dwell Parameters
Purpose:
Defines general dwell behavior for standalone dwell blocks, including the G‑code used for dwell, the register/address for dwell values, and separate dwell-time control for UPM and UPR feedrate modes.
UI Elements Present:
Dwell Control Group:

Prep/G‑Code on Dwell Blocks: 4
Dwell Register Address: F

UPM Group:

Minimum Dwell Time: 0.1000000
Maximum Dwell Time: 99.9900000
Dwell Multiplier: 0.0000000
Button: Format Dwell Register

UPR Group:

Minimum Dwell Time: 0.0000000
Maximum Dwell Time: 0.0000000
Dwell Multiplier: 0.0000000
Button: Format Dwell Register

Programmer Actions:

Set dwell G‑code that appears in output (G04 or equivalent).
Configure dwell register address (F).
Define allowable dwell durations for UPM vs UPR modes.
Optionally adjust dwell multiplier for controllers requiring scaled dwell times.
Use “Format Dwell Register” to apply formatting rules or multi-digit register setup.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

The dwell G‑code output format.
Required dwell register address (F).
Separate dwell handling for UPM vs UPR modes.

AI should generate:

FIL routines that interpret dwell commands and apply limits.
Register formatting rules for dwell outputs.
Conditional dwell logic for machines using UPM vs UPR modes.


## Tab/Section:
Machine Codes → Dwell Parameters → Cycle Dwell
Purpose:
Defines dwell times for canned cycles such as drilling, countersinking, deep-hole drilling, tapping, boring, reaming, through cycles, facing, and break‑chip cycles. Also defines modal vs non‑modal cycle-dwell behavior.
UI Elements Present:
Cycle Dwell Values Group:

Cycle Drill: 0.0000000
Cycle CSink: 2.0000000
Cycle Deep: 2.0000000
Cycle Tap: 2.0000000
Cycle Bore: 2.0000000
Cycle Ream: 2.0000000
Cycle Thru: 2.0000000
Cycle Face: 2.0000000
Cycle Brkchp: 0.0000000

Modality Group:
Radio options:

Modal (selected)
Non‑Modal: reset dwell value to zero for new Cycle cmd

Programmer Actions:

Define dwell times per cycle category.
Choose modal behavior so dwell value holds across cycles, or non‑modal behavior so dwell resets to zero.
Ensure cycle-dwell times match tooling, coolant, and material requirements.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Dwell values required for each cycle type.
Modal vs non-modal dwell behavior.
How CL cycle commands (CYCL) map to output dwell patterns.

AI should generate:

Canned-cycle dwell block logic (G81, G82, G83, etc.).
Automatic insertion of dwell based on cycle type.
Conditional reset of dwell values when non-modal is selected.


## Tab/Section:
Operator Messages → Insert
Purpose:
Controls internal/external message formatting for operator-facing notes, including control characters, aliasing, block-size limits, and whether operator messages appear in tape output. Also defines how INSERT statements behave.
UI Elements Present:
Control Characters Group:

Control-Out Character: 40( )
Control-Out Alias: (
Control-In Character: 41( )
Control-In Alias: )

Maximum Characters per Block Group:
Radio options:

80 characters
120 characters (selected)

Messaging Options:

Checkbox: Output operator messages to tape file
Checkbox: Retain spaces in INSERT statements
Checkbox: Use Continuation Character for INSERT

Programmer Actions:

Configure outbound and inbound control characters used in operator messages.
Set alias versions for controllers expecting alternate symbols.
Select maximum message block length for output formatting.
Decide whether operator messages appear in the final NC tape.
Choose how INSERT statements handle spacing and continuation characters.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

How to wrap messages in control characters.
Whether to include operator messages in final NC output.
Maximum block character limits.
How to process INSERT statements (spacing, continuation).

AI should generate:

Message wrapping and formatting logic.
Continuation-character rules for long operator messages.
Conditional output of operator text blocks.

## Tab/Section:
Advanced → FIL Editor
Purpose:
Provides an integrated text editor for editing the FIL (Format Instruction Language) file that controls custom post‑processor logic. This is where programmers implement advanced logic, define variables, override output rules, and add conditional formatting beyond the GUI-driven OFG settings.
UI Elements Present:
Editor Window (FIL Source Code Visible):

Comment header describing the file: “Default Mill FIL file created by the OFG”
Commands shown:

PRINT/ON
DMT = POSTF(24,1)
REDEF/ON


Extensive listing of variable definitions:

A = 1, B = 2, C = 3 ... up to Z = 26
Single-letter variables mapped to indices used by POSTF commands


Left-side tabs:

FIL Editor
Text / VTB Editor
PLABELS
Commons
Search
ToDo List & User Notes



Toolbar:

Standard text editor icons (save, open, search, undo, redo, indent, unindent, etc.)
Zoom and font-size adjustment icons
Function buttons specific to FIL formatting

Programmer Actions:

Edit FIL logic (POSTF, INSERT, conditional control, variable definitions).
Add custom logic for motion, coolant, cycles, tool changes, formatting, or coordinate manipulation.
Modify default variable sets, override modal outputs, or add controller-specific formatting.
Use tools for searching, indenting, formatting, and navigating FIL code.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Which global variables, POSTF functions, and logic blocks exist and might need modification.
FIL structure and custom rules defined by the programmer.
Where AI should insert new logic such as filters, interpolators, custom output formats, or safety routines.

AI should generate:

FIL code templates that codify user-selected OFG GUI settings.
Conditional logic using POSTF, INSERT, and variable tables.
New sections for advanced output formatting, cycle extensions, or machine-specific requirements.

## Tab/Section:
Advanced → Text / VTB Editor
Purpose:
Provides a plain text editor for VTB (Variable Table Block) files or miscellaneous text files linked to the post. Used for editing auxiliary files, documentation, macro libraries, or custom text that supplements FIL logic.
UI Elements Present:
Editor Window:

Blank editing panel (no file loaded).
Red vertical margin guide line.
Status bar showing:

Line 1
Column 0
File: Untitled-0



Toolbar:

Common editing icons: open, save, print, clipboard functions, indent, unindent, search, etc.
Icons identical to FIL editor toolbar but used for general text rather than FIL syntax.

Left Sidebar Tabs:

FIL Editor
Text / VTB Editor
PLABELS
Commons
Search
ToDo List & User Notes

Programmer Actions:

Edit or create VTB and auxiliary text files.
Document postprocessor functionality or store reusable macros.
Adjust supporting information used in complex post builds that require reference tables.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

What auxiliary files (VTB/text) may be linked to the post.
How AI-generated reference tables (e.g., transformation matrices, IJK mappings, custom G-code dictionaries) should be stored.

AI should generate:

Optional VTB-style reference tables describing machine-specific configurations.
Documentation or comments to assist future post developers.
Custom mapping files if required by complex machines.


## Tab/Section:
Advanced → PLABELS
Purpose:
Defines internal postprocessor labels (PLABEL entries) that specify default behaviors, formatting rules, run‑time options, and punch/output settings. PLABELS act as a global rule-set the post uses during execution.
UI Elements Present:
PLABELS Table:
Columns:

PLABEL
INTCOM
DESCRIPTION
VALUE

Visible Rows (1–10):

Tab Characters → “Do not punch tab characters”
Verification Print → “Generate modal verification print”
Inch / Metric → “Inch input / Inch output & Inch option file”
Page Heading → “Print page heading”
Punch Output → “Unpack punch output with one block / line”
Warnings → “Do not suppress warning messages”
Man‑Read PARTNO → “Do not punch man‑readable PARTNO”
Rewind Stop Code → “Punch rewind stop code at start and end”
EOB Character → “36( $ )”
Leader Character → “62( > )”

Tabs across the top:

1–10 (selected)
11–20
21–30
31–40
41–50
51–60
61–70
71–80
81–90
91–99

Programmer Actions:

Set global punch-formatting rules (tab suppression, unpacking, warnings).
Configure default character aliases for EOB, leader, rewind codes.
Adjust print headings, verification behavior, and metric/inch settings.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Required global behaviors such as warning prints, metric/inch mode, tab suppression.
Character-level formatting (EOB $, Leader >).
Punch and verification print policies.

AI should generate:

Automatic application of PLABEL-based global formatting in output templates.
Character formatting logic aligned with PLABEL input.
Modal/non-modal verification output rules.


## Tab/Section:
Advanced → Commons
Purpose:
Displays and edits COM variables (INTCOM, RELCOM, DBLCOM) that govern low‑level tape‑ordering, address‑mapping, and internal postprocessor control behavior. This section provides direct access to fundamental settings that influence how addresses are placed and interpreted in the output program.
UI Elements Present:
Commons Editor Fields:

Location selectors (spinner fields):

INTCOM location
RELCOM location
DBLCOM location


Value fields:

INTCOM Value: 16
RELCOM Value: 0.00000000
DBLCOM Value: 0.00000000


Buttons:

Edit Intcom…
Edit Relcom…
Edit Dblcom…



Information Panel (INTCOM):
Shows detailed description for selected INTCOM entry:

JA (code) 0001
Description: “Tape order of letter address A”
Default = 53
Range = 1 to 26, 53

This panel changes depending on selected location.
Programmer Actions:

Choose desired INTCOM/RELCOM/DBLCOM location.
Adjust tape-order values for letter addresses (e.g., A, B, C…).
Consult detailed descriptions before modifying COM variables.
Tune low-level formatting to match controller expectations or handle specific output ordering rules.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

How COM variables influence tape output ordering.
When modifications to COM entries require adjustments to FIL and output templates.
That COM settings directly affect address sequencing, formatting, and output behavior.

AI should generate:

Proper COM initialization routines.
Documentation linking COM values to FIL logic.
Safe editing boundaries so invalid COM values don’t break output formatting.


## Tab/Section:
Advanced → Search
Purpose:
Provides global search access to COM variable definitions, FIL code, and all related documentation. Enables browsing and locating specific keywords, COM entries, and variables with full reference descriptions.
UI Elements Present:
Search Panel:

Keyword/Phrase input field
Dropdown for selecting prior entries
Buttons: Search, Note…
Checkboxes:

Case-specific phrase/keyword
Find whole word only



Tabbed Results:

All Commons (selected)
Search Results

Results Window:
Displays reference text describing COM variables:

“INTCOM Variables – Mill Version 6.8”
Detailed explanation:

INTCOMS 1–52 vs 53 behavior
Tape order of letter address A/B/etc
Default/Range for each COM variable


Red vertical margin guide line

Programmer Actions:

Search for keywords across COM entries or FIL documentation.
Inspect detailed behavior of any COM variable before modification.
Confirm valid ranges and defaults for tape-order or address behavior.
Use results to validate changes made in the COM panel.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

How search results validate COM, FIL, and referenced variables.
How searching helps confirm correct machine formatting, address mapping, modal rules, or transformation logic.

AI should generate:

Links between OFG GUI settings and underlying COM/FIL logic.
Automated “explain COM variable” capability.
Smart search-based guidance for Codex in post-development reasoning.


## Tab/Section:
Advanced → ToDo List & User Notes
Purpose:
Allows documenting tasks, reminders, and internal notes tied to building or maintaining the postprocessor. Also aggregates user notes from all OFG panels into a centralized view.
UI Elements Present:
My To Do List Panel:

Large blank task list area
Buttons:

Add (active)
Edit… (disabled until item selected)
Rmv (disabled until item selected)



User Notes Panel:

Large blank area collecting notes from all OFG panels
Scrollable region

Programmer Actions:

Maintain development notes during post creation (e.g., “Fix cycle retract logic”, “Confirm ABC axis direction”).
Add internal documentation or reminders.
Review notes created throughout the OFG to ensure no steps are overlooked.
Use notes as a reference for future post updates or debugging.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

User’s internal development tasks or special requirements.
Additional constraints or enhancements referenced within notes.

AI should generate:

Summaries of user tasks for automated post verification.
Auto-reminders or checklist integration tied to OFG features.
Context-aware suggestions based on notes provided.

## Tab/Section:
Startup / Welcome Screen (Application Launch)
Purpose:
This is the initial landing screen of the Option File Generator. It allows users to select an existing option file or choose from recently used option files before entering the configuration workflow. It establishes the starting point for building or editing a postprocessor.
UI Elements Present:
Main Window:

Center pop‑up: “Welcome to the Option File Generator – Version 6.8” with CNC graphics banner.
Left panel:

Button: Select Option File
Section: Recent Option Files

Buttons:

uncx01.p01
uncx01.p23
uncl01.p12






Toolbar icons (top):

New file
Open
Save
Undo / Redo
Mode toggle
Post build tools
Help icon
Other standard OFG utilities (disabled until file loaded)



Programmer Actions:

Open an existing OFG option file.
Choose from recently used post files.
Begin new postprocessor creation by selecting an option file path.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

This is the entry point for selecting or loading machine configurations.
No machine parameters are defined yet—only file context.

AI should generate:

Logic to initialize post-building workflow.
File-selection scaffolding for Codex integration.


## Tab/Section:
Startup Wizard → Define Machine Type
Purpose:
Defines the base category of machine the postprocessor will represent. This determines which OFG panels become available (Mill, Lathe, Wire EDM, Laser, Punch). Selecting “Mill” leads to all MULTAX and milling-specific menus.
UI Elements Present:

Title: “Specify the Option File’s machine type.”
Icons representing machine types.
Radio options:

Lathe
Mill (selected)
Wire EDM
Laser
Punch


Bottom row:

Next
Cancel
Help



Programmer Actions:

Select machine type (Mill in this case).
Proceed to next step of new option file creation.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

The post file is a milling-type configuration.
This selection dictates default features (XYZ, optional ABC axes).
Determines which categories of cycles, coolant, cutter comp, feedrate, and transforms will be used.

AI should generate:

Mill-specific post template.
Machine-category initialization parameters.
Automatic enabling of milling-relevant sections in the build pipeline.

## Tab/Section:
Startup Wizard → Define Option File Location
Purpose:
Defines name and storage location of the new option file, assigns machine number, and displays existing machines in the chosen directory. This provides organizational context for managing multiple postprocessors.
UI Elements Present:

Title: “Define the name of the new Option File.”
Input: Machine Number (must be 1–99) → 02
Input: Option File Name shown as path:
\PostProcessorFiles\mill\post\uncx01.p02
Button: Change Directory
List: “Option Files in Current Directory:”

01: Default Mill
21: (G68.2 Mode) MotusCNC GBM5 5 Axis
23: (G43.5 Mode) MotusCNC GBM5 5 Axis


Buttons:

Back
Next
Cancel
Help



Programmer Actions:

Assign machine number (02).
Confirm option file path or change directory.
Review existing post files to avoid naming collisions.
Proceed to initialize new option file.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Machine number is part of the file identity.
File-path conventions and naming structures matter for locating and loading posts.
Existing posts in directory imply available templates or reference configurations.

AI should generate:

File‑naming conventions for new posts.
Directory-handling logic for storage and retrieval.
Cross-post referencing when multiple machine models coexist.


## Tab/Section:
New Option File Wizard → Option File Initialization
Purpose:
Determines how the newly created option file should be initialized before configuration. This step defines the baseline used for all subsequent machine‑specific parameter settings.
UI Elements Present:

Dialog Title: “Option File Initialization”
Description text: “Specify how you want to initialize the Option File. This can be via default settings or the use of another option file as a template.”
Radio options:

Postprocessor defaults
System supplied default option file… (selected)
Existing option file…


Buttons:

Back
Next
Cancel
Help



Programmer Actions:

Choose baseline configuration.
For most post builds, “System supplied default option file” provides general safe defaults.
For custom machines, “Existing option file” may be selected to reuse architecture-specific logic.
Click Next to continue setup.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

Initialization mode dictates starting parameter set used in OFG panels.
“System supplied default” implies a baseline template familiar to AI for building post structure.
“Existing option file” would require AI to map inherited settings and override only deltas.

AI should generate:

Initialization templates for milling posts.
Pre‑population logic for machine settings (axes, cycles, feeds, transforms).
Strategies for merging inherited settings if using an existing file.


## Tab/Section:
New Option File Wizard → Select Option File Template
Purpose:
Selects a template option file from either the current directory or the CamLib directory. These templates include predefined postprocessor configurations for multiple CNC controllers.
UI Elements Present:

Title text: “Location and Name of Template File”
Input field: (blank initial file path)
Large empty container showing “Templates in Current Directory”

No templates visible in user directory for this screenshot


Scrollable list under “Templates in CamLib”: shows multiple default templates:

01: HAAS CONTROL
02: FADAL CNC 88 CONTROL
03: FADAL CNC 32MP CONTROL
04: FANUC OM CONTROL
05: FANUC 6M CONTROL
(More entries off-screen; scroll bar visible)


Buttons:

Back
Next
Cancel
Help



Programmer Actions:

Select a controller-specific template such as “FANUC OM CONTROL” or “HAAS CONTROL”.
If desired, browse local directory templates.
Click Next to initialize OFG content based on chosen controller template.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

The chosen template determines controller-specific startup parameters.
Template selection heavily influences formatting (G‑code, M‑code structures, modal behaviors).
FANUC OM / HAAS / FADAL templates all map to distinct rule sets.

AI should generate:

Preconfigured controller logic blocks.
Named machine template import routines.
Postinitialization logic for axes, cycles, modal codes, coordinate systems, and controller semantics.


## Tab/Section:
New Option File Wizard → Option File Title
Purpose:
Defines the display title for the newly created option file. This name appears within OFG, list files, posted output (if enabled), and internal reference dialogs.
UI Elements Present:

Title: “Option File Title”
Input field containing: “FANUC OM CONTROL”
Description text: “Specify the desired title for the newly created Option File.”
Buttons:

Back
Finish
Cancel
Help



Programmer Actions:

Enter descriptive title corresponding to controller type or machine name.
Titles help programmers identify posts when managing multiple configurations.
Click Finish to complete creation of the new option file and load full editing interface.

Mapping to AI-Assisted G‑POST Builder:
AI must infer:

This name is the post’s semantic identity for documentation and list printing.
Title does not alter technical behavior but provides metadata.

AI should generate:

Internal metadata tags in post template.
Optional list-file headers containing option file title.
Naming structures used when exporting outputs.













































































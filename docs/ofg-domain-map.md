# OFG Domain Map

This document maps the application checklist to the collected research in [`OFG.md`](../OFG.md). It is a domain reference for engineering review, not proof that a setting was verified in an installed G-POST environment. The catalog intentionally uses the reference's **Tab/Section**, **Purpose**, **UI Elements Present**, and **Programmer Actions** observations. Its speculative AI recommendations are not application requirements.

## Checklist categories

| Application category | Collected OFG areas | Typical relevance |
| --- | --- | --- |
| Machine & Axes | Type, Specs, & Axes → Machine / Axes | Core |
| Transforms & Output | Transforms & Output → Transformation / Output | Conditional for rotary or transformed output |
| File Formats | File Formats → MCD File / File Type / Sequence Numbers | Core |
| Program Start / End | Start/End → General / Default Prep Codes / Start Prog | Core |
| Motion | Motion → Linear / Rapid / Circular | Core, with mill-only plane choices |
| Cycles | Motion → Cycles → Cycle Motion | Conditional on machine/controller capability |
| Machine Codes | Machine Codes → Prep/G Codes / Aux/M Codes | Core |
| Tooling / Cutter Compensation | Tool Change; Machine Codes → Cutter Comp | Core tool change, conditional compensation |
| Spindle | Spindle → Codes / Aux / Direct RPM | Core |
| Coolant | Machine Codes → Coolant | Core availability review |
| Feedrates | Feedrates → UPM / UPR | UPM core; UPR lathe-applicable |
| Operator Messages | Operator Messages → INSERT | Conditional |
| Advanced / Custom | MULTAX, right-angle head, 5-axis comp, Siemens/UG cycles, FIL | Advanced disclosure only |

The backend catalog is defined once in `backend/app/ofg/domain.py`. Its evaluator uses the machine type, axis count, reviewed capability map, and explicit engineer selection. The API, progress totals, exports, and frontend consume the resulting relevance metadata; the frontend does not recreate machine rules with scattered conditionals.

## Relevance and progress

Internal classes are `core`, `conditional`, and `advanced`. User-facing labels are **Required for this Post**, **Applicable**, **Optional**, **Not Applicable**, and **Advanced**. Normal lists exclude advanced settings. The advanced disclosure can reveal advanced areas, including ones currently assessed as not applicable, so an engineer can explicitly opt one in.

Progress includes only settings evaluated as applicable whose review status is not **Not Applicable**. Hidden advanced and irrelevant settings never inflate the denominator.

## OFG location confidence

- **Verified From OFG Reference** means the collected `OFG.md` reference supports the displayed tab/section path.
- **Site Verification Needed** means the collected reference identifies an area, but installed-site behavior or association still needs confirmation.
- **Not Verified** means the application has no supported OFG path.

None of these statuses claim successful verification in a locally installed OFG/G-POST environment.

## Structured values

MCD address-format rows retain Address, Description, Output Order, Before Alias, After Alias, Metric Format, Inch Format, status, and source. Sequence settings retain maximum, start, increment, frequency, block delete, and optional output. Code entries use **Defined**, **Not Available**, **Not Required**, or **Unknown**; unavailable and not-required values are never converted to zero. File extension starts unresolved and never assumes `.nc`.

## Traceability boundary

Machine Knowledge records physical or controller facts. OFG Configuration records engineering choices to review in the official tool. Sources are explicitly classified as Machine Knowledge, Controller Documentation, OFG Reference, Site Standard, Existing Post Reference, Engineer Entry, or Unknown.

Simple trace:

`Controller Documentation → reviewed Machine Knowledge → applicable OFG setting → engineer review`

Advanced trace:

`Machine capability + Site Standard → advanced OFG setting → Custom Logic reference → local G-POST/site verification`

The result remains a reviewed checklist. It is not a native option file, CamLib import, FIL generator, or compiled postprocessor.

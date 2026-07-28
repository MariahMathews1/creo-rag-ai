# Kent KLS-1840N Public Test Dataset

Purpose:
Test citation-backed profile extraction using public documentation.

Target machine:
Kent USA KLS-1840N

Expected physical-machine source:
- Kent KLS Series brochure
- Kent KLS-1840N product specification Markdown

Expected controller source:
- FANUC Series 0i Model F Plus parameter manual

Expected extracted values:
- Manufacturer: Kent USA
- Machine model: KLS-1840N
- Machine type: CNC lathe
- Controller model: FANUC 0i-Mate TF
- X-axis travel: 11 inches
- Z-axis travel: 38 inches
- Spindle range: 100–2000 RPM
- X rapid traverse: 315 inches/minute
- Z rapid traverse: 394 inches/minute
- Standard spindle power: 7.5 HP
- Optional spindle power: 10 HP
- Tool-post stations: 4
- Spindle bore: 3 inches
- Chuck diameter: 10 inches
- Tailstock present: yes

Important:
- Do not infer X/Z coordinate minimums or maximums from travel.
- Do not treat optional equipment as installed.
- Do not use the FANUC parameter manual to prove physical machine options.
- Public test data only; not for production use.
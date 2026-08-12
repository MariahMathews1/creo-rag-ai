# G-POST manual test checklist

Use only fictional/public test data. Never send generated output to a machine.

- Select the Kent KLS public-test lathe and an exact profile revision.
- Confirm another machine's documents never appear and cannot be submitted by API ID.
- Select machine/controller/programming manuals and create a `fanuc_lathe` draft.
- Confirm G18, X/Z motion, configurable lathe T-code, and no assumed M06.
- Review LOADTL, SPINDL, FEDRAT, COOLNT, RAPID, GOTO, and FINI.
- Attach real uploaded evidence to one mapping and verify title/page/section/excerpt.
- Paste sample CL and generate an R&D preview.
- Confirm every generated block links to its CL line, mapping/version, state, and evidence.
- Confirm the preview was reparsed and deterministic findings remain separate.
- Enter `MULTAX/ON` and `TLAXIS/0,0,1`; confirm both remain visible and block preview.
- Select a mill family for the lathe; confirm the mismatch blocks preview.
- Save a new version, edit a template, and confirm the previous version is unchanged.
- Compare versions and inspect technical differences.
- Export JSON and Markdown; confirm all three safety labels are present.
- Confirm audit events exist and do not contain complete CL, G-code, or manuals.

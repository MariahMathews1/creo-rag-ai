# G-POST Research Questions

These questions are intentionally unresolved. Answers require authoritative vendor documentation or verification in the installed local G-POST environment.

## Native artifacts and lifecycle

1. What is the exact native representation of an Option File for the installed G-POST version?
2. What import and export capabilities does Option File Generator provide?
3. What is the exact `.pNN` / `.fNN` lifecycle, including editable, generated, and compiled artifacts?
4. Can a reviewed external checklist be imported, or must every value be entered interactively?
5. Is export of a portable, editable native post feasible and supported?

## Configuration coverage

6. Which machine/controller settings are handled directly by OFG?
7. What are the actual menu, panel, and field names for the installed release?
8. Which values depend on licenses, controller options, machine kinematics, or post family?
9. Which settings can be validated deterministically before compilation?

## Custom logic

10. Which behaviors genuinely require FIL/CIMFIL rather than standard OFG configuration?
11. How is custom FIL associated with a post in the installed site environment?
12. How is FIL/CIMFIL named, compiled, versioned, debugged, and promoted?
13. What reviewed source formats can safely be included in a Post Development Package?

## Validation and handoff

14. What evidence is required for local compilation, controlled test-post, NC programmer review, VERICUT, dry-run, and site qualification gates?
15. Which native logs or reports can be referenced without ingesting restricted production data?
16. What package structure reduces re-entry while retaining review and provenance?

Until verified, the application must label related fields **Not Yet Verified**, retain engineer notes, and avoid presenting assumptions as product capability.

# Site Standards model

An applied Site Standard may add explicit validation gates such as `VERICUT Simulation` or `Site Qualification`. These requirements extend the Post Record's Validation Policy; they never imply that the application performs the external stage.

Site Standards capture facility behavior that machine/controller documentation cannot authoritatively supply: safe retracts, headers, comment/PPRINT format, coolant sequencing, offsets, naming, and program-end policy.

Scopes are Global, Machine Family, Controller Family, Specific Machine, and Specific Post Record. `PostStandardApplication` explicitly applies a standard to a Post Record.

Applications record status, conflicts, and reviewer notes. Conflicts between machine evidence, documentation, OFG settings, and Site Standards display as **Conflict / Site Override Requires Review** and are never resolved automatically.

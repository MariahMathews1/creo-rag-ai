# V1 Post Workflow

## Create

1. Select a machine.
2. Confirm the post name and current machine-configuration revision.
3. Review the automatically selected compatible Post Foundation and create the post.

Reference Programs are not part of the primary creation flow. FANUC lathe, FANUC mill, Haas mill, and generic foundations are selected from known machine/controller context to prevent normal accidental mismatch.

## Develop

Machine Knowledge is the authoritative context checklist. Build Post exposes contextual actions for the configuration areas that form a single post. Any AI-assisted component draft uses only permitted machine-level evidence, remains review-only, and never receives CL/NCL, part geometry, toolpaths, or production programs.

The Complete Post view is assembled deterministically from the latest state of each component. Cycles may be deferred; the other eight areas determine required-area completion.

## Review and retain

Review shows actionable drafted components and the assembled configuration. Accepted, edited, or rejected rules continue to use the existing deterministic review controls. A reviewed result is called a **Reviewed R&D Draft**, never production approved.

Create Version records a meaningful whole-post snapshot. Archive is the default retention action. Duplicate creates a new, independent logical post at v1.

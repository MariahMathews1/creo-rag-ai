# V1 demo walkthrough

Start on Dashboard and explain that the application is organized around machine readiness and current work. Open Machines, then Documents, and show that references belong to a selected machine. Ask Machine Assistant about maximum spindle RPM and open its citation.

Open Translation Examples and describe them as known pairs of Creo CL/NCL and G-code historically produced for the same machine/post. Open Paired Code, then Toolpath. The main demonstration does not require alignment terminology.

Open G-POST Generator, select the machine, confirm post context, and create a draft. Paste fictional CL/NCL, generate the R&D draft, inspect generated code, checks, evidence, and toolpath. Open Advanced Post Configuration only to show where post developers can inspect templates and mappings.

Before generation, point out that Current CL Preflight lists only behaviors used by the pasted CL. Demonstrate an unsupported current behavior to show the exact blocker and direct mapping action, then restore supported CL and show the explicit unreviewed-behavior warning.

Finish with G-code Review from Dashboard. Throughout the walkthrough, state that output is advisory R&D work requiring qualified review, simulation, and approval.

Use [the manual acceptance checklist](v1-manual-test-checklist.md) when validating a release.

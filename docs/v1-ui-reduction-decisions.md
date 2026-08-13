# V1 UI reduction decisions

This pass changes information priority without removing the underlying architecture.

- Primary navigation reflects NC programmer tasks; Analysis became **G-code Review** under Advanced / Engineering Tools.
- Internal revision IDs, hashes, provenance structures, parser diagnostics, and mapping mechanics are hidden from primary views.
- Programmer language replaces implementation language: machine configuration, known G-code, paired code, found information, and R&D draft.
- Dashboard cards summarize actionable state and provide direct next actions.
- Translation Examples default to a compact library and side-by-side Paired Code workspace.
- G-POST defaults to generation, toolpath, results, and evidence; internals remain under Advanced Post Configuration.
- Document extraction defaults to a compact confirm/review flow; the engineering workspace remains reachable.

No deterministic validation, version history, traceability, machine/post isolation, consent control, or advisory-only safety boundary was deleted.

# Translation verification workflow

Statuses are `unknown`, `candidate`, `reviewed`, `verified_successful`, `deprecated`, and `invalid`. There is no automatic promotion. Normal progression is unknown → candidate → reviewed → verified successful; candidate/reviewed may become invalid, and verified examples may become deprecated.

Verification requires an exact revision, both hashes, no fatal parser failure, a post name or explicit `UNKNOWN`, matching machine/revision identity, an approved revision, a reviewer label/note, and the explicit historical-pair acknowledgment. Blocking deterministic findings may remain because present rules may not completely model historical machining, but verification then requires a substantive justification. Final-status records are immutable.

`verified_successful` means a qualified reviewer accepts the pair as historical translation evidence in the stated context. It does not mean safe, certified, guaranteed, or authorized for production.

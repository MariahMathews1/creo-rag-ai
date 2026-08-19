# Post rule review workflow

Every generated rule starts as `needs_review`. A named post engineer must make one explicit decision:

- **Accept** preserves the AI draft as the reviewed template.
- **Edit & Accept** preserves the original AI draft and records a separate engineer template.
- **Reject** records that the proposal is unsuitable; a reason is recommended.
- **Needs More Information** records the missing fact or unresolved conflict.

Decisions are rule-level so one weak proposal cannot hide inside a broadly accepted section. Review changes update the section aggregate and retain reviewer identity and time. Regeneration creates a new section version while old decisions remain queryable. Accepted history is never silently replaced.

Section acceptance is R&D post-development review only. It is not production approval, machine validation, proof of controller compatibility, or authorization to run output. Deterministic checks, controlled simulation/prove-out, site configuration control, and normal approval remain mandatory.

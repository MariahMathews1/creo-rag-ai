# Phase 10 manual test checklist

- [ ] Start with `TRANSLATION_AI_PROVIDER=disabled`; status shows disabled and deterministic features remain usable.
- [ ] Use `mock`; retrieval visibly reports `AI called: No`.
- [ ] Confirm only verified-successful, AI-allowed, exact-machine examples appear.
- [ ] Confirm cross-post/revision widening requires the explicit fallback checkbox.
- [ ] Generate a mock interpretation and inspect examples used, uncertainty, provider, and invocation ID.
- [ ] Disable one example's AI permission and confirm it disappears from retrieval.
- [ ] Confirm opening Translation Examples and G-POST does not create an AI invocation.
- [ ] Confirm the G-POST interpretation panel does not change mapping content or review status.
- [ ] In Azure mode, view status without a network call, then explicitly run the connectivity check.
- [ ] Use only synthetic `SPINDL / RPM,1200,CLW` data for the optional smoke test.
- [ ] Confirm public web remains disabled and frontend responses contain no endpoint, credential, or token.
- [ ] Confirm the invocation audit contains hashes and example IDs but no raw prompt or hidden reasoning.
- [ ] Disable Azure again and confirm the application remains functional.

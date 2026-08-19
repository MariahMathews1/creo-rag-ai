# Post Builder AI context

The outbound contract is deliberately small and section-specific.

Allowed:

- approved machine identity, controller, axes, limits, capabilities, and post templates;
- exactly one supported post section;
- explicitly selected eligible document excerpts with allowlisted IDs;
- accepted or edited-and-accepted machine-level rules from the same section.

Prohibited:

- CL/NCL or APT source;
- part geometry, features, fixtures, identifiers, or coordinates;
- toolpath coordinates or machining sequences;
- production programs or G-code;
- translation examples and cross-machine evidence;
- public-web retrieval.

Raw input is recursively inspected before request-model coercion or provider lookup. The exact external outbound object is checked again. Audits contain hashes, identifiers, versions, duration, and safe provider metadata—not prompts or prohibited content. The UI's context preview explicitly identifies excluded classes before its deliberate generate action becomes available.

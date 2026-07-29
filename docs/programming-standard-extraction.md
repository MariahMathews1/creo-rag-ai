# Programming-standard extraction

The initial `standards-v1` algorithm is deterministic. It preprocesses parsed
program blocks and proposes conventions for:

- program structure: percent delimiters and O-number;
- safe start: units, plane, absolute positioning, compensation/cycle
  cancellations;
- coordinate/offset practice: recurring work offset;
- tool change: explicit T-word format;
- spindle: G96 preceded by G50;
- motion/cycles: drilling cycles followed by G80;
- program ending: coolant off, spindle stop, G28/G53 reference return, M30;
- formatting: sequence-number coverage and parenthesis comments.

Each proposal contains support count, eligible-program count, percentage,
confidence used only for prioritization, contradictions, exact lines, post and
program-type context, conditions, and applicability. Frequency classes are
`universal_observed`, `common`, `occasional`, `exceptional`, and
`insufficient_evidence`.

Universal observation is not an organizational requirement. A reviewer must
accept, edit, reject, or defer every proposal. Safety-relevant and conflicting
proposals require individual review; protected batch acceptance excludes them.
Conditional conventions are explicitly heuristic and do not claim semantic
equivalence.


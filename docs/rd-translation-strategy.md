# R&D translation strategy

## Revised responsibility model

```text
                        MACHINE CONTEXT
                              |
                +-------------+-------------+
                |                           |
         Machine Profile                 Manuals
                |                           |
                +-------------+-------------+
                              |
                              v
                    Exact Machine Context
                              |
         +--------------------+--------------------+
         |                    |                    |
         v                    v                    v
     Creo CL/NCL       Verified CL/G-code     Deterministic
                             pairs               Rules
         |                    |                    |
         +--------------------+--------------------+
                              |
                              v
                  Translation Assistance
                              |
                              v
                     Candidate G-code
                              |
                              v
                  Deterministic Validation
                              |
                              v
                 Historical Comparison
                              |
                              v
                   Toolpath Visualization
                              |
                              v
                     Qualified Review
```

The machine profile answers **what is configured for this exact machine**: machine type, axes, controller, limits, supported commands, options, and the exact approved configuration revision.

Manuals and uploaded documents answer **what is documented as possible, supported, or specified**: syntax, command descriptions, parameter definitions, manufacturer limits, and documented options. Manual Assistant is internal document Q&A and technical evidence retrieval. A manual answer is not proof that the site's post emits a particular block.

Verified CL/G-code pairs will answer **how this organization actually translated Creo CL/NCL into machine-specific G-code**. They are the primary future evidence for site behavior such as tool calls, spindle and coolant output, motion formatting, offsets, sequence conventions, and program endings.

Deterministic rules answer **whether a candidate violates known constraints**. Parser errors, machine limits, unsupported axes, command policy, and template/post incompatibility remain authoritative checks. Neither historical frequency nor future AI output overrides them.

AI is a future advisory layer. It will retrieve controlled examples and produce a draft translation that must pass parsing, deterministic validation, historical comparison, visualization, and qualified review.

## Why manuals alone are insufficient

- Manual structure and terminology are inconsistent across manufacturers and revisions.
- Controller families and option packages differ even when command names look similar.
- Controller documentation describes capability, not the behavior of a site's specific Creo post.
- Optional hardware and parameters are often ambiguous without exact machine configuration.
- Manuals rarely provide paired Creo CL input and actual emitted output.
- Company sequence, offset, comment, tool-call, and ending conventions are not fully represented.

Manuals remain necessary for technical meaning and capability boundaries; they are supporting evidence rather than the learned translation corpus.

## Data and authority boundaries

Translation retrieval must default to the exact machine and make every broadened scope visible. Restricted documents or programs must remain excluded when policy requires. Candidate output must identify its provider, selected internal sources, machine revision, and external-processing state. Public-web retrieval is disabled by default.

The first AI experiment is **retrieval-assisted translation** or **few-shot translation using verified examples**, not “training GPT on our programs.” Retrieval is easier to audit and update, needs fewer examples, permits removal of bad examples, and keeps the evidence visible to reviewers. Fine-tuning is a later experiment only if dataset quality and benchmark results justify it.

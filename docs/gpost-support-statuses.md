# G-POST Support Statuses

- `supported`: a valid mapping and reusable template/state behavior exists.
- `not_applicable`: capability rules exclude the behavior for this machine/post; it does not reduce readiness.
- `unsupported_required`: the workflow requires behavior V1 cannot generate; this is blocking.
- `not_implemented`: the command is known but generation support is deferred; it blocks when required or encountered in test CL.

Support and review remain separate. A 2-axis lathe's `MULTAX` mapping may be `not_applicable` and `accepted` after engineer confirmation.

# V1 Hidden Research Tools

The repository retains research work for historical CL/G-code pairs, alignment review, deterministic pattern exploration, G-code analysis, toolpath visualization, local diagnostics, and earlier AI experiments. These are not V1 product navigation and must not be presented as the primary workflow.

Frontend access is controlled by `VITE_ENABLE_RESEARCH_TOOLS`:

```text
VITE_ENABLE_RESEARCH_TOOLS=false  # default V1 behavior
VITE_ENABLE_RESEARCH_TOOLS=true   # developer research access
```

When disabled, `/research-tools`, `/translations/*`, `/g-code-review`, and analysis routes redirect to the Dashboard. When enabled, `/research-tools` provides developer links to the retained screens.

This flag changes visibility only. It does not delete research records, relax machine isolation, enable Azure OpenAI, or authorize CL/NCL, geometry, toolpath, or production-program transmission to an AI provider.

# G-POST Template and Mapping Model

Configuration templates are the source of truth for reusable generated output behavior. CL/NCL mappings reference those templates and may only override them explicitly.

Each mapping stores `template_key`, optional `template_override`, and `uses_override`. The override controls output only when enabled; otherwise the current draft configuration value is resolved dynamically. Legacy `output_template` remains a fallback for manually created records without a template key.

Changing a shared template changes every non-overridden mapping that references it. Resetting an override resumes configuration inheritance. Multi-behavior commands use variants such as `spindl_cw`, `spindl_ccw`, `spindl_off`, `coolnt_on`, and `coolnt_off`.

# Validation Toolchain Architecture

The V1 authority chain is intentionally separated: this application develops and documents machine-specific post configuration; the approved Creo G-POST / Option File Generator environment implements and compiles it; VERICUT performs external CNC simulation and collision analysis; engineers and site procedures own prove-out, qualification, and release decisions.

AI is optional during permitted machine-level development tasks only. It has no role in runtime post-processing, CNC execution, diagnostic parsing, VERICUT, collision checking, or release. Post development status and validation-stage results remain separate. `R&D VALIDATED` requires the Post Record's configured gates and no unresolved blockers; it never means production certification.

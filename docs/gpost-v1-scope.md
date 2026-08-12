# G-POST V1 Scope

G-POST V1 targets reviewable core 2/3-axis post behavior: program structure, tooling, spindle direction and stop, feed formatting, coolant, rapid/feed motion, work coordinates, and program ending.

The review path is: approved immutable machine-profile revision → machine-specific sources or explicit manual acknowledgement → shared output templates → template-referenced CL/NCL mappings → required behavior review → known CL/NCL preview → traceability and deterministic validation.

Approved reference programs and programming standards are optional evidence. Advanced cycles, macros, subprograms, multiaxis generation, special compensation, and unusual controller functions remain intentionally deferred.

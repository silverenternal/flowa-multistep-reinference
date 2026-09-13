# Wave 101 P2-B/P2-C feasibility audit

P2-C grouping is already implemented: canonical modules live under
`algorithm/{runner,blender,merge,perturbation,scheduler}` and historical
top-level paths remain import shims. Import smoke checks confirm symbols such
as `BayesianMergeOperator` resolve identically from top-level and canonical
paths.

P2-B remains unsafe to execute mechanically. `_extra`/`_r2` modules are still
referenced by tests, claims, and downstream compatibility imports (for example
`algorithm.scheduler_extra`, `algorithm.round2_extra`, and
`algorithm.merge_operator_extra`). Merging them would require preserving many
module paths and re-export identities, with a high D.4 regression risk. This
pass is audit-only; no files were moved or deleted.

Validation: algorithm import smoke passed; D.4 regression vectors passed **30
tests** (3 warnings).

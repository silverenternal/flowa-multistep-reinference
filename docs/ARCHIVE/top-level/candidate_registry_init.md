# Candidate Registry — Initial Listing (DTB-G2)

This document is the **initial** candidate registry for 2025/2026 local
Flow Matching models that may be wired into the public
`flow_matching_engine.Engine` via per-model adapters. It is
**read-only** and explicitly does **not** use SOTA ranking as an
admission basis.

## Admitted (mechanics gate only)

### FlowMol3

| Field | Value |
| --- | --- |
| Repo URL | <https://github.com/zavalab/ML/tree/FlowMol3> |
| Pinned commit | `77cae22174b7792b0e25e9e0414038420736d841` |
| License | MIT |
| Paper | FlowMol3 (2025) |
| Task conditions | unconditional_3d |
| Native metric protocol | model-internal sampling diagnostics only |
| ODE / vector-field call site | `integrate` / `step` over (x, a, c, e) features |
| State boundary | `(x, a, c, e)` mixed continuous/discrete state |
| Condition boundary | none (unconditional) |
| Restart boundary | `state.detach()` boundary in integrate/step |
| Compatible channels | `coordinate`, `atom_type`, `charge`, `edge` |
| Adapter status | `admitted_unconditional_only` |
| Adapter module | `flowmol3_adapter.py` |

#### Audit notes

FlowMol3 is admitted **only** for validating the public engine +
adapter protocol surface (DTB-G1). It does **not** validate any
pocket-conditioned efficacy claim. Re-admission with
`adapter_status="admitted"` requires a separate candidate row whose
paper / dataset / evaluator provenance are pocket-conditioned.

## Blocked / unsupported (template slots)

The following slots are reserved for the 2025/2026 pocket-conditioned
Flow Matching audit. Each must carry its own reproducible commit,
paper / date, dataset / split, native metric protocol, ODE call site,
state / condition / restart boundary, compatible channels, available
checkpoint, and audit notes. Until each slot is filled the registry
remains effectively empty for pocket-conditioned claims.

| Repo URL | Commit | License | Paper | Task | Status | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| _unspecified_ | _unspecified_ | _unspecified_ | _unspecified_ | pocket_conditioned | unsupported | no source / paper evidence yet |
| _unspecified_ | _unspecified_ | _unspecified_ | _unspecified_ | pocket_conditioned | unsupported | no source / paper evidence yet |
| _unspecified_ | _unspecified_ | _unspecified_ | _unspecified_ | pocket_conditioned | unsupported | no source / paper evidence yet |

## Non-claim boundary

* The registry does **not** use SOTA leaderboard ranking as admission
  basis. Audit is reproducibility-first.
* `admitted_unconditional_only` rows are explicitly excluded from any
  universal / generalizable statement.
* Any generalizable claim about pocket-conditioned generation requires
  at least one `adapter_status="admitted"` row carrying
  `task_conditions=("pocket_conditioned", ...)` **and** one further
  candidate with a different state / integrator family under the same
  compute / round / evaluator budget. The current registry has neither.

## Registry audit template

See `audit_template.py::AuditTemplate`. Every entry must pass
`validate_audit_completeness(entry)` (returns `(True, ())`) before it
can be admitted. The template is part of the read-only registry
contract; relaxing it requires a DTB-Q-level decision recorded in
`todo.json` and a paired acceptance test.

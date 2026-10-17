# GAP-42 — non-cosine schedulers overspent the R1 NFE budget

**Date:** 2026-10-16
**Author:** GAP-42 agent (USER AUTHORIZED, NO PUSH)
**Scope:** a budget-conservation defect in `tools/eval/framework.py`
(`_solve_framework`) that only affected the scheduler-driven NFE allocation
branch. Frozen surfaces untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).

---

## 0. TL;DR

| Item | Result |
|---|---|
| **Defect** | For any `--scheduler` other than `cosine`, the per-round NFE was computed as `round(n_cap * nfe)` with `n_cap` treated as a *partition*. `n_cap` is a *per-round fraction*, and several families return ≈1.0 on every round, so the sum overspent the budget. |
| **Concrete leak** | `nfe=10, n_rounds=3`: `cosine` `[3,3,4]` = 10 (correct) vs `codimension_sheet` `[10,10,1]` = **21** (2.1×), `linear` 16, `nfe_aware_memory` 11. |
| **Consequence** | Any cosine-vs-math-scheduler A/B run before this fix was a *compute* comparison, not a scheduler comparison — and it would confound with the NFE effect found in GAP-41b. |
| **Fix** | `_allocate_nfe_budget(weights, nfe, n_rounds)`: normalise the weights, apportion the integer budget with largest-remainder rounding, floor of 1 per round. Sum is exactly `nfe` whenever `nfe >= n_rounds`. |
| **Blast radius** | Additive and branch-local: the `cosine` path is byte-identical (legacy `[base, …, base+remainder]`). Pinned by `test_solve_framework_cosine_path_unchanged_by_budget_fix`. |
| **Post-fix allocations** | `cosine [3,3,4]`; `codimension_sheet` / `tier_aware_codimension` / `nfe_aware_memory` / `constant` `[4,3,3]`; `linear` / `polynomial` `[6,3,1]`; `exponential [3,3,4]`; `sigmoid [1,3,6]`. All sum to 10. |

---

## 1. The defect

`_solve_framework` allocated the budget with:

```python
_ns = int(round(float(_n_cap) * float(nfe)))
_ns = max(1, min(int(nfe), int(_ns)))
_raw.append(int(_ns))
_total = sum(_raw)
if _total != int(nfe):
    _raw[-1] = max(1, _raw[-1] + (int(nfe) - _total))
```

The reconciliation clause only corrected *under*-spend. When `sum(n_cap) > 1`
the final round was clamped to 1 and the excess survived.

Measured pre-fix (`nfe=10`, `n_rounds=3`, real `_solve_framework`, synthetic
FlowMol3 adapter):

| `--scheduler` | per-round NFE | sum |
|---|---:|---:|
| `cosine` | `[3, 3, 4]` | 10 |
| `codimension_sheet` | `[10, 10, 1]` | **21** |
| `tier_aware_codimension` | `[10, 10, 1]` | **21** |
| `linear` | `[10, 5, 1]` | 16 |
| `nfe_aware_memory` | `[5, 5, 1]` | 11 |

Root cause: `n_cap` is a fraction in `[0, 1]` (the scheduler docstrings define
`n_cap(r) = n_min + (n_max - n_min) * ratio(r)`), not a partition of the
budget. `codimension_sheet` returns `[1.0, 0.9997, 1.0]` because its
sheet-vs-cell ratio is ≈1 at every round, so multiplying straight by `nfe`
spends ~3× the budget.

## 2. The fix

New helper `tools/eval/framework.py::_allocate_nfe_budget`:

1. sanitise weights (finite, non-negative; uniform fallback if all zero);
2. `targets[i] = w[i] / sum(w) * nfe`;
3. `alloc[i] = max(1, floor(targets[i]))`;
4. if the floor-of-1 overshoots (`nfe < n_rounds`), fall back to the legacy
   uniform-with-remainder split (same edge behaviour as `cosine`);
5. distribute the remaining budget by largest fractional part.

The `cosine` branch is untouched, so the Wave 158 / 161 / 172b anchor manifests
do not move.

## 3. Post-fix allocations

| `--scheduler` | per-round NFE | sum |
|---|---:|---:|
| `cosine` | `[3, 3, 4]` | 10 |
| `codimension_sheet` | `[4, 3, 3]` | 10 |
| `tier_aware_codimension` | `[4, 3, 3]` | 10 |
| `nfe_aware_memory` | `[4, 3, 3]` | 10 |
| `constant` | `[4, 3, 3]` | 10 |
| `linear` | `[6, 3, 1]` | 10 |
| `polynomial` | `[6, 3, 1]` | 10 |
| `exponential` | `[3, 3, 4]` | 10 |
| `sigmoid` | `[1, 3, 6]` | 10 |

## 4. What this means for the scheduler A/B (important)

The fix makes the comparison *fair*, but it also reveals that
**`codimension_sheet` has essentially no per-round signal on R1**. Its
`n_cap` weights are `[1.0, 0.9997, 1.0]` — a relative spread of ~3e-4 —
because the LineageFlow adapter exposes no `profile_residual_fn`
(`tools/gen_lineageflow_n1000_fastas.py:341`; `docs/audit/gap01-r6-live-wiring.md:62`),
so the scheduler falls back to the framework heuristic and the
sheet-vs-cell ratio saturates at ≈1 for all three rounds.

Consequently `codimension_sheet`'s post-fix split `[4,3,3]` differs from
`cosine`'s `[3,3,4]` only in **which round receives the rounding remainder**.
A cosine-vs-codimension A/B is therefore expected to be a near-null by
construction, not a test of the paper's math.

The real lever is wiring a residual profile `g(x)` into the adapter so the
paper-quantity path (`A_g`, `B_g`, `C_g`, `e_ρ`) activates and `n_cap` actually
varies across rounds. That is a separate, larger change — not attempted here.

## 5. Tests

- `tests/test_tools/eval/test_framework.py::test_solve_framework_non_cosine_scheduler_conserves_nfe_budget`
  — every non-cosine family sums to `nfe` and every round gets ≥1 step.
- `tests/test_tools/eval/test_framework.py::test_solve_framework_cosine_path_unchanged_by_budget_fix`
  — cosine still yields `[3,3,4]` / `[16,16,18]` / `[66,66,68]` / `[10]`.

## 6. Reproduce

```bash
.venvs/lineageflow_venv/bin/python - <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("f", "tools/eval/framework.py")
m = importlib.util.module_from_spec(spec); sys.modules["f"] = m; spec.loader.exec_module(m)
from adaptive_reflow.adapters.flowmol3 import default_flowmol3_adapter
for s in ["cosine","codimension_sheet","linear","sigmoid"]:
    a = default_flowmol3_adapter(force_mode="synthetic", nfe_budget=10)
    cap=[]; orig=a.solve_ode
    a.solve_ode=lambda st,c,*,seed,_o=orig: (cap.append(int(c.delta_spec["num_steps"])), _o(st,c,seed=seed))[1]
    m._solve_framework(a, nfe=10, seed=42, n_rounds=3, scheduler_name=s)
    print(s, cap[:3], sum(cap[:3]))
PY
```

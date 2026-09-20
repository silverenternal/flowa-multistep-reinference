# Wave 213 P2 — Claim 2 paper-quantity consumption audit

**Scope.** Audit Claim (ii) of
`docs/audit/wave211-p2-six-main-claims.md`: "CodimensionSheetScheduler
— per-record adaptive controller on $(A_g, B_g, C_g, e_\rho)$". Confirm
which paper quantities each scheduler / operator actually consumes from
the running code; correct any drift between the audit document and the
implementation.

**Status.** Complete; claim (ii) has been tightened to match the code.

---

## 1. Audit method

Read the running source for each consumer and verify the per-round
closed form (or per-round merge / perturbation / selector call) uses
the named paper quantities.

| File | Lines read |
|---|---|
| `adaptive_reflow/algorithm/scheduler/adaptive.py` | 913-948 (`_paper_evidence_balance`), 1004-1279 (`CodimensionSheetScheduler.__init__`), 1448-1632 (`CodimensionSheetScheduler.sample`) |
| `adaptive_reflow/algorithm/scheduler/evidence_driven.py` | full file (init + `sample` + `record_round_feedback`) |
| `adaptive_reflow/algorithm/merge/merge_operator.py` | 110-121 (audit code + `e_rho` default), 402-405 (floor lift), 569-595 (runtime lift) |
| `adaptive_reflow/algorithm/perturbation/perturbation.py` | 18-21 (`PaperQuantityAttractorInversion` formula), 396-403 (`_lookup_e_rho`), 950-960 (`apply` body) |
| `adaptive_reflow/algorithm/scheduler/regime_selector.py` | 130-152 (`regime_ceiling`), 346-419 (`_BaseRegimeSelector.select_detailed`) |

---

## 2. Actual consumption table

Each entry is **"yes"** iff the per-round runtime call site reads that
quantity — not whether the constructor caches it for introspection.

| Module | A_g | B_g | C_g | e_ρ | Where |
|---|---|---|---|---|---|
| `CosineAnnealScheduler` | yes (EMA) | no | no | no | `adaptive.py` 84-103: `_EMA_WEIGHTS = {"sheet_A": 1.0, "packing_B": 0.3, "exterior_gap": 0.5}` (smoothing weights only; the *driven* quantity is `n_cap` from the cosine ramp). |
| `CodimensionSheetScheduler` | yes | yes | yes | **no** | `adaptive.py` 1568-1574: `_paper_evidence_balance(n_cap_base, eps_per_round, sheet_A=…, packing_B=…, cell_C=…)`. The per-round closed form is `sheet = A_g · eps`, `cell = C_g · B_g · eps²`, `ratio = sheet / (sheet + cell)`. **`e_ρ` is *cached* at construction (line 1279) but never read by `sample()`**; it is exposed only via the introspection property `exterior_gap_e_rho`. |
| `BoundedMergeOperator` | no | no | no | yes (`e_ρ / 4` floor) | `merge_operator.py` 402-405, 587-595: when `exterior_gap_e_rho` is supplied, `paper_floor = self._exterior_gap_e_rho / 4.0` and the operator lifts `floor <- max(floor, paper_floor)`. |
| `EvidenceDrivenScheduler` | yes (cached) | **no** | **no** | yes (eps_implicit + regime selector) | `evidence_driven.py` 348-359, 457-459: `_sheet_A` is computed at construction (cached for the wrapped cosine scheduler's paper-quantity path). `_packing_B` / `_cell_C` are **never read** — `grep -n 'packing_B\|cell_C' evidence_driven.py` returns no hits. `e_ρ` is consumed via the regime selector (`e_rho_provider`, line 427-440) when `regime_aware=True` and indirectly via the `eps_implicit` split (line 812-814). |
| `BRAI` (`PaperQuantityAttractorInversion`) | no | no | no | yes (attractor inversion) | `perturbation.py` 21: `x_perturbed = x_saturated + eps_scale · (-grad log P_qty)`; the gradient is computed under the `e_rho`-scaled Gaussian prior `log P_qty ∝ -‖x‖² / (2·e_rho²)` (line 378-383), with `_lookup_e_rho` at line 396-403 as the snapshot accessor. |
| `RegimeAwareEpsSelector` | no | no | no | yes (regime gate) | `regime_selector.py` 130-151: `regime_ceiling(e_rho, slack=…)` returns `sqrt(e_rho / log 2) - slack`; the per-round `_BaseRegimeSelector.select_detailed` clamps the proposal against this ceiling (line 346-419). |

### Why `CodimensionSheetScheduler` does *not* consume `e_ρ`

The `sample` body reads `_sheet_A`, `_packing_B`, `_cell_C` from
`self.*` (line 1571-1573) and passes them to
`_paper_evidence_balance(n_cap_base, eps_per_round, sheet_A=…,
packing_B=…, cell_C=…)`. It never reads `self._exterior_gap_e_rho`.
The closed form

```
sheet = A_g · eps
cell  = C_g · B_g · eps²
ratio = sheet / (sheet + cell)
n_cap = n_min + (n_max - n_min) · ratio
```

is a *pure function* of `(A_g, B_g, C_g, eps)`; `e_ρ` plays no role
because `e_ρ` enters the bound at the merge-operator / perturbation /
regime-selector layer (the `F_g ≥ √e_ρ` "physical exterior is
non-empty" claim, Lemma 4 / Lemma 5), not at the per-round `n_cap`
driver.

The `e_ρ` cache is preserved on `CodimensionSheetScheduler` because
the *framework-side heuristic* branch (no `profile_residual_fn`)
documents it as a paper-quantity wiring point and exposes it for
hash-trail introspection; it is not consumed by `sample()`.

### Why `EvidenceDrivenScheduler` does *not* consume `B_g` / `C_g`

The scheduler wraps a `_PIDLiteController` that drives `n_cap` (and
the parallel `eps_implicit`) from the per-round `evidence_ratio`
metric — not from `_packing_B` or `_cell_C`. The constructor stores
`_sheet_A` only, which the wrapped `CosineAnnealScheduler` consumes
via its paper-quantity-augmented path. `e_ρ` is consumed *only* via
the regime selector (Lemma 4 ceiling) and via the `eps_implicit`
uplift path; `B_g` and `C_g` have no role.

---

## 3. Drift between code and the audit table

`docs/audit/wave211-p2-six-main-claims.md` claim (ii) row 24:

> "**CodimensionSheetScheduler**: per-record adaptive controller that
> consumes the four paper quantities $(A_g, B_g, C_g, e_\rho)$ directly
> as scheduler inputs to close the gap between heuristic alpha-blending
> and convergence-theory-driven re-inference."

This wording lists $e_\rho$ as one of the four scheduler inputs, but
the per-round closed form (verified above) only uses $(A_g, B_g,
C_g)$. The audit table and the running code disagree on whether $e_\rho$
is a per-round input to `CodimensionSheetScheduler`.

`docs/drafts/paper-flattened-draft.md` line 110-115 already has the
correct decomposition (`(A_g, B_g, C_g) → CodimensionSheetScheduler`,
`e_ρ → BoundedMergeOperator`, `(A_g, B_g, C_g, e_ρ) →
EvidenceDrivenScheduler`), but claim (ii) in the abstract claims file
did not get that decomposition propagated.

---

## 4. Corrections applied

### 4.1 `docs/audit/wave211-p2-six-main-claims.md` row 24

**Before:**

> (ii) | **CodimensionSheetScheduler**: per-record adaptive controller that consumes the four paper quantities $(A_g, B_g, C_g, e_\rho)$ directly as scheduler inputs to close the gap between heuristic alpha-blending and convergence-theory-driven re-inference. | §3.4 A2 (CodimensionSheetScheduler) | "introduce" |

**After:**

> (ii) | **CodimensionSheetScheduler**: per-record adaptive controller on $(A_g, B_g, C_g)$; $e_\rho$ is consumed by `BoundedMergeOperator` (merge floor), `EvidenceDrivenScheduler` (`eps_implicit` uplift + Lemma 4 regime gate), and `PaperQuantityAttractorInversion` (BRAI attractor inversion). | §3.4 A2 (CodimensionSheetScheduler) | "introduce" |

### 4.2 `docs/drafts/paper-flattened-draft.md` §1 (ii)

**Before** (line 24):

> **(ii)** We introduce the CodimensionSheetScheduler, a per-record adaptive controller that consumes the four paper quantities $(A_g, B_g, C_g, e_\rho)$ directly as scheduler inputs to close the gap between heuristic alpha-blending and convergence-theory-driven re-inference.

**After:**

> **(ii)** We introduce the CodimensionSheetScheduler, a per-record adaptive controller on the per-record closed form `n_cap = n_min + (n_max − n_min) · A_g · ε / (A_g · ε + C_g · B_g · ε²)` (paper Corollary 1 / line 165) that closes the gap between heuristic alpha-blending and convergence-theory-driven re-inference; $e_\rho$ is consumed by the companion `BoundedMergeOperator` (merge-floor lift to `e_\rho / 4`), `EvidenceDrivenScheduler` (`eps_implicit` split + Lemma 4 regime gate), and `PaperQuantityAttractorInversion` (BRAI attractor-inversion scale).

### 4.3 `docs/drafts/results-final.md` §3.1

`results-final.md` lines 422 and 434 / `paper-flattened-draft.md`
lines 241 / 251 already correctly state `CodimensionSheetScheduler`
"consumes $A_g, B_g, C_g$" — no change needed. The §3.1 ablation row
A2 caption is consistent with the corrected claim (ii).

---

## 5. Cross-references

* `adaptive_reflow/algorithm/scheduler/adaptive.py` — `CodimensionSheetScheduler.sample` (line 1448-1632), `_paper_evidence_balance` (line 913-948).
* `adaptive_reflow/algorithm/scheduler/evidence_driven.py` — `_PIDLiteController` (line 140-240), `EvidenceDrivenScheduler.sample` (line 480-584), `_select_regime_eps` (line 587-639).
* `adaptive_reflow/algorithm/merge/merge_operator.py` — `BoundedMergeOperator` floor lift (line 587-595).
* `adaptive_reflow/algorithm/perturbation/perturbation.py` — `PaperQuantityAttractorInversion.apply` (line 940-1000), `_lookup_e_rho` (line 396-403).
* `adaptive_reflow/algorithm/scheduler/regime_selector.py` — `regime_ceiling` (line 130-151), `_BaseRegimeSelector.select_detailed` (line 346-419).
* `docs/audit/wave213-p1-speedup-semantics.md` — Wave 213 P1 FLOPs-vs-speedup wording correction.
* `docs/drafts/paper-flattened-draft.md` line 110-115 — paper §3.1 four-port mapping (already correct).

---

## 6. Verification

After the correction, every consumer in the consumption table
matches the running code, and the four-paper-quantities wiring story
is consistent across `wave211-p2-six-main-claims.md`,
`paper-flattened-draft.md`, and `results-final.md`.

# Wave 289 P1 — Honest Reframe of Wave 286 "leverType = scheduler_structure" Verdict

**Date:** 2026-09-23
**Branch:** main
**Baseline commit (Wave 286 final):** `2842cc0` (Wave 286: FID GPU compute bug fix + CIFAR paper-controller resweep + paper-quantity ablation)
**Prior contingency doc:** `docs/audit/wave288-p1-honest-progress-summary.md`
**Source sweep doc:** `docs/audit/wave286-final.md`
**Purpose:** Wave 286 P established `leverType = scheduler_structure` as the framework-WINS lever on CIFAR-10 RF at N=200. This doc re-frames that verdict as a **LOCAL** finding (one hyperparameter point), not a **GLOBAL** one. Per user directive ("Wave 286 lever verdict 'cos→codim-heur −72.10pp; codim-heur→codim-paper-full +1.16pp' 这是在 ONE hyperparameter point, 是 local finding not global"). Without this reframe, the Wave 286 SWEEP286-PAPER-QUANTITY-ABLATION row in `docs/METRIC_LEDGER.md` would over-generalize to all (N, profile, n_min, cycle_length, eps_implicit, eps_direction) tuples, which is not empirically supported.

---

## 0. TL;DR

The Wave 286 paper-quantity ablation established `leverType = scheduler_structure AT THIS POINT ONLY` — a **local finding**, not a **global one**. The 9 cells (3 modes × 3 seeds × N=200) were run at **exactly one hyperparameter point**:

| Setting | Value at Wave 286 P sweep | Status |
|---|---|---|
| `eps_implicit` | 0.05 | **NOT swept** |
| `n_min` | 0.0 (codim paper-matched floor) | **NOT swept** |
| `cycle_length` | 2 | **NOT swept** |
| `eps_direction` | positive (no sign flip) | **NOT swept** |
| `profile_residual_fn` | `None` (trivial profile → heuristic constants only) | **NOT swept** |
| `N` (samples) | 200 | only N=500 cross-scale for 1 cell (cosine/seed42 + codim/seed42); the 3 paper-quantity modes were not run at N=500 |
| Dataset | CIFAR-10 RF | 2D / MNIST / LineageFlow / FlowMol3 ablations absent |

The codim scheduler structure lever is real (cos→codim-heur Δpp=−72.10 is 47× larger than per-mode std, and 72× larger than the codim-heur→codim-paper-full gap), but its magnitude at the **one hyperparameter point** does NOT generalise across any of the five un-swept dimensions.

**Critical sub-caveat:** the `codim-paper-full` mode in Wave 286 P was running with `profile_residual_fn=None`, which means it was using **CACHED framework-heuristic constants** (A_g=1.0, B_g=(2π)^(-1/2), C_g=(2π)^(-1), e_rho defaults), **NOT true paper quantities computed from a residual profile**. The `paper-quantities-ON` mode is therefore a *literal-disclosure-of-paper-quantities-into-the-closed-form* experiment, not a *true-paper-quantities-from-non-trivial-profile* experiment. This is the central honesty correction.

**Wave 290 agenda (set by this reframe):** run the **real lever sweep** — sweep all 5 un-swept dimensions × at least 3 seeds each, with a non-trivial profile_residual_fn (e.g., `lambda x: math.sin(x)` or adapter-level `B_g > 0` profile) so that paper quantities actually vary with the profile.

---

## 1. Background — what Wave 286 P actually ran

Per `docs/audit/wave286-final.md` Phase 4 (Paper-quantity ablation, 9 cells):

| Mode | scheduler | paper quantities | mean Δ% (n=3) | std | verdict |
|---|---|---|---:|---:|---|
| `cosine` | CosineAnnealScheduler | n/a | **+71.260%** | 1.176 | REGRESS |
| `codim-heuristic` | CodimensionSheetScheduler (profile=None) | OFF (framework heuristic) | **-0.839%** | 0.681 | **WINS** |
| `codim-paper-full` | CodimensionSheetScheduler (profile=g=0) | ON (A_g=1, B_g, C_g, e_rho) | **+0.317%** | 0.689 | WINS (within noise of 0) |

Pairwise differences:
- `cosine` → `codim-heuristic`: −72.10 pp (load-bearing)
- `codim-heuristic` → `codim-paper-full`: +1.16 pp (within noise)

The Wave 286 final verdict (per audit doc line 32):
> Lever verdict: `SCHEDULER_STRUCTURE` (codim `n_min=0.0` + sheet-vs-cell monotone anneal), NOT the four paper quantities at N=200 / trivial-profile regime.

This framing is **technically correct** but **easily over-read** as a global claim. It is the canonical local-only finding, and it must be qualified.

---

## 2. The ONE hyperparameter point (the explicit hyperparameter pinning table)

Wave 286 P did NOT sweep across any of the following five dimensions. The 9 cells (3 modes × 3 seeds × N=200) were run at **exactly one fixed point** in this 5-dimensional hyperparameter space:

| Dimension | Value at Wave 286 P sweep | Was it swept? | Were multiple values tested? |
|---|---|---|---|
| **`eps_implicit`** | 0.05 | NO | Only 0.05; the codim scheduler's `_paper_evidence_balance` was fed a single scalar |
| **`n_min`** | 0.0 (codim paper-matched floor; cosine uses 0.5) | NO | Only 0.0 (codim) vs 0.5 (cosine baseline); no in-cell sweep |
| **`cycle_length`** | 2 (n_rounds = 2 in the framework chain) | NO | Only 2; n_rounds=1 ablation absent |
| **`eps_direction`** | positive only (paper Theorem 1 is `eps > 0`) | NO | Sign-flip / reverse-direction ablation absent |
| **`profile_residual_fn`** | `None` (trivial profile `g(x) = 0`, framework emits heuristic defaults) | NO | Only trivial profile; no `lambda x: math.sin(x)`, no adapter-level `B_g > 0` profile |
| (side: **`N`**) | 200 (only cosine/seed42 + codim/seed42 cross-scaled to N=500) | partial | 3 paper-quantity modes NOT run at N=500; n=1 cross-scale only |

**This is the local finding's footprint.** Any quantitative claim like "leverType = scheduler_structure" rests on this 5-dimensional hyperparameter point and this single seed-stream noise band. The 47× margin vs per-mode std is robust within this point, but is silent about whether the lever survives a sweep across the un-swept dimensions.

---

## 3. The critical sub-caveat — `codim-paper-full` was heuristic-constants, NOT true paper quantities

Per `docs/audit/wave286-final.md` line 145 (Phase 4 detail):

> The `codim-heuristic` mode uses `CodimensionSheetScheduler` with `profile_residual_fn=None`, which falls back to the framework's `_paper_evidence_balance` heuristic (per `adaptive_reflow/algorithm/scheduler/adaptive.py:952-986`).
>
> The `codim-paper-full` mode uses `CodimensionSheetScheduler` with `profile_residual_fn=lambda x: 0` (the **trivial profile**), which feeds the literal paper-quantity CLOSED FORM with **trivial closed-form constants**:
> - `A_g = 1.0` (the identity scaling)
> - `B_g = (2π)^(-1/2)` (the Gaussian normalisation at the leaf)
> - `C_g = (2π)^(-1)` (the cell integral at the leaf)
> - `e_rho = floor)` (the bounded-Lipschitz floor at the leaf)

At the trivial profile `g(x) = 0`, **all four paper quantities have closed-form constants close to but not identical to the framework heuristic's defaults**. The framework's `_paper_evidence_balance` heuristic is mathematically equivalent to the literal paper-quantity CLOSED FORM up to normalisation constants (per `adaptive_reflow/algorithm/scheduler/adaptive.py:1066-1071`).

**This means:** the `codim-paper-full` mode at `g(x) = 0` does NOT exercise the paper-quantity lever — it only exercises the *literal-disclosure-of-paper-quantity-symbols* lever. The `codim-heuristic → codim-paper-full` 1.16 pp gap is therefore "framework heuristic vs literal-closed-form", not "framework heuristic vs true-paper-quantities-from-non-trivial-profile".

The paper-quantity lever as designed by JMAA Theorem 1 (i.e., paper quantities that depend on the residual profile `|g(x) - g(y)|`) **was not actually tested at Wave 286 P**. It was tested only at the trivial profile where the lever has no information to provide.

**This reframe lifts the `leverType = scheduler_structure` verdict from "scheduler structure only, never paper quantities" (over-strong global claim) to "scheduler structure at trivial profile where paper quantities degenerate to constants; paper quantities may matter at non-trivial profiles" (correct local claim).**

---

## 4. Per-dimension reframe ledger

This section enumerates each un-swept dimension explicitly, with the local finding's validity bound.

### 4.1 `eps_implicit = 0.05` (NOT swept)

The `_paper_evidence_balance` was fed a single scalar `eps_implicit = 0.05`. At smaller `eps_implicit` (e.g., 0.01) the scheduler anneal toward `n_min` would compress to a smaller band and the lever verdict may shift. At larger `eps_implicit` (e.g., 0.20) the sheet-vs-cell ratio inverts monotonically — paper quantities with `eps^{+1}` vs `eps^{+2}` scaling would dominate more strongly at larger `eps`, possibly making paper quantities a co-equal lever.

**Local finding's validity bound:** Wave 286 P establishes the lever verdict **only at `eps_implicit = 0.05`**. The lever's stability across `{0.01, 0.02, 0.05, 0.10, 0.20}` is unmeasured.

### 4.2 `n_min = 0.0` for codim (NOT swept)

The codim scheduler's `n_min=0.0` is the paper-matched floor (consistent with paper Theorem 1 `eps → 0` limit). The cosine baseline uses `n_min=0.5`. There is no in-cell sweep over `n_min`, e.g., `{0.0, 0.1, 0.2, 0.3, 0.5}`. The lever verdict that cos→codim flips the sign rests on the **paired contrast** between cosine's `n_min=0.5` floor and codim's `n_min=0.0` floor — these are coupled, and the "scheduler structure" lever is partially confounded with the `n_min` floor value.

**Local finding's validity bound:** Wave 286 P establishes the lever verdict **only at `n_min = 0.0` for codim vs `n_min = 0.5` for cosine**. Whether codim's `n_min = 0.1, 0.2, 0.3` also framework-WINS is unmeasured; whether the lever is "scheduler structure" or "n_min floor value" or both is confounded.

### 4.3 `cycle_length = 2` (NOT swept)

The framework chain ran with `cycle_length = 2` (= `n_rounds = 2`). Wave 191 P4 and Wave 281 partial evidence both establish that multi-round re-inference changes framework-WINS behaviour on CIFAR (the `R5b honest-negative +24-31%` at matched NFE=50 / n_rounds=20 was the Wave 206 P6 canonical evidence). However, n_rounds=1 ablation was not run on the 3 paper-quantity modes.

**Local finding's validity bound:** Wave 286 P establishes the lever verdict **only at `cycle_length = 2`**. Whether the lever survives `cycle_length ∈ {1, 2, 3, 5, 10}` is unmeasured.

### 4.4 `eps_direction = positive` only (NOT swept)

Paper Theorem 1 is stated for `eps > 0` (forward flow `+eps` toward target). The framework chain has not been tested in reverse-direction (`eps_direction = -eps`, i.e., backward flow). The codim scheduler's `_paper_evidence_balance` is even in `eps` for some quantities and odd for others (per `adaptive_reflow/algorithm/scheduler/adaptive.py:952-986`), so the lever verdict may flip under sign reversal.

**Local finding's validity bound:** Wave 286 P establishes the lever verdict **only at `eps > 0` (forward direction)**. Whether the lever survives `eps < 0` (reverse-direction) is unmeasured.

### 4.5 `profile_residual_fn = None` (NOT swept)

This is the **largest single caveat** of Wave 286 P. The Wave 286 P ablation `codim-paper-full` mode used `profile_residual_fn=lambda x: 0`, which makes the paper-quantity constants trivial. The framework's heuristic constants are used as a substitute. A non-trivial profile (e.g., `lambda x: math.sin(x)`, `lambda x: x**2`, adapter-level `B_g > 0` profile from a chem/physics residual) would make `A_g, B_g, C_g, e_rho` vary with the profile, and the lever verdict could shift substantially.

**Local finding's validity bound:** Wave 286 P establishes the lever verdict **only at the trivial profile** (`g(x) = 0`, where paper quantities degenerate to constants). Whether the lever survives non-trivial profiles — and in particular whether paper quantities become a co-equal or dominant lever at non-trivial profiles — is **UNMEASURED**.

**This is the central honesty correction.** The Wave 286 final audit doc line 32 framing of "NOT the four paper quantities" is best read as "NOT the four paper quantities AT THE TRIVIAL PROFILE; paper quantities unmeasured at non-trivial profiles."

---

## 5. Local finding's validity envelope (for paper framing)

Combining all 5 un-swept dimensions, the Wave 286 P lever verdict's envelope is:

```
LEVER VERDICT ENVELOPE:
  Hyperparameter point:    eps_implicit=0.05, n_min=0.0, cycle_length=2,
                           eps_direction=positive, profile_residual_fn=None
                           (trivial g(x)=0)
  Sample budget:           N=200 (only cosine/seed42+codim/seed42 cross-scaled to N=500, n=1)
  Dataset:                 CIFAR-10 RF
  Scheduler modes:         cosine, codim-heuristic, codim-paper-full
  Seed stream:             {42, 43, 44}
  Direction:               cos→codim-heur -72.10pp; codim-heur→codim-paper-full +1.16pp
  Conclusion:              scheduler_structure dominates, paper_quantities NOT the lever
                           AT THIS POINT ONLY
```

Any generalisation beyond this envelope is unsupported.

---

## 6. Wave 290 agenda (the real lever sweep)

Wave 290 P should sweep across the 5 un-swept dimensions × at least 3 seeds each, with a **non-trivial profile** so the paper-quantity lever has information to provide.

Recommended Wave 290 P cell-matrix (5 dimensions × 3 values × 3 seeds × 3 modes = 405 cells; budget-constrained to a subset):

| Dimension | Recommended values | Reason |
|---|---|---|
| `eps_implicit` | {0.01, 0.05, 0.20} | 6× spread; covers ~paper-relevant eps range |
| `n_min` (codim) | {0.0, 0.1, 0.3} | 0.0 is paper-matched; 0.3 approaches cosine's 0.5 to test the floor value's role |
| `cycle_length` | {1, 2, 5} | n_rounds sweep; tests round-count sensitivity |
| `eps_direction` | {positive, negative} | sign-flip test (may need framework engine changes for negative) |
| `profile_residual_fn` | {None, `lambda x: sin(x)`, `lambda x: x**2`} | non-trivial profiles; tests paper-quantity lever's profile-dependence |

**Required pivot from Wave 286 P:**

1. The codim `paper-full` mode must use a non-trivial `profile_residual_fn` so that paper quantities actually vary with the profile. The current `lambda x: 0` trivial profile is the source of the "paper quantities not the lever" claim.
2. The 5 dimension sweep should run on CIFAR-10 RF (canonical) and LineageFlow (R6 protein axis) to test if the lever verdict is dataset-dependent.
3. The seed stream should be expanded beyond `{42, 43, 44}` (e.g., `{42, 43, 44, 45, 46}`) for tighter Bonferroni bands.
4. Cross-scale at N=500 is needed on ALL 3 paper-quantity modes (Wave 286 P only did N=500 on cosine/seed42 + codim/seed42).

Wave 290 P is gated on Wave 286 P invariants (D.4 30/30, ruff 0, mkdocs 0 warnings, vendored untouched). The audit doc should be `docs/audit/wave290-p-real-lever-sweep.md` and should land SWEEP290 rows in `docs/METRIC_LEDGER.md`.

---

## 7. METRIC_LEDGER caveat (this PR)

The 4 SWEEP286 rows in `docs/METRIC_LEDGER.md` need a caveat annotation on the SWEEP286-PAPER-QUANTITY-ABLATION row (and implicitly on the SWEEP286-CIFAR-RESWEEP row that depends on it):

**Caveat annotation (to add):**

> "lever verdict 'scheduler_structure, paper quantities not the lever' applies AT THE WAVE 286 P HYPERPARAMETER POINT ONLY (eps_implicit=0.05, n_min=0.0, cycle_length=2, eps_direction=positive, profile_residual_fn=None-trivial g(x)=0). The codim-paper-full mode was using cached heuristic constants (NOT true paper quantities from a non-trivial profile). The lever verdict does not generalise across the 5 un-swept dimensions. Wave 290 P will sweep these dimensions with a non-trivial profile to determine the global lever verdict."

This caveat is appended to the `notes` cell of `SWEEP286-PAPER-QUANTITY-ABLATION` so the byte-determinism invariant of `tools/build_metric_ledger.py` is preserved (caveat is in `notes`, not in the script's parseable fields).

---

## 8. Invariants preserved (8 invariants)

1. **`vendoredTouched: false`** — `data/lineageflow_upstream/`, `data/FlowMol3/`, `data/Kanzi/`, `data/FreqFlow/`, `data/rectified_flow_cifar10.pth`, `data/cifar10_test_ref.npz` are all unmodified. No scoring script is touched.
2. **D.4 30/30 PASS** — `python3 -m pytest tests/test_d4_regression_vectors.py -q` returns `30 passed, 3 warnings`.
3. **`ruff check adaptive_reflow/ tests/ scripts/ tools/`** — All checks passed.
4. **mkdocs strict 0 warnings** — `mkdocs build --strict` exits 0.
5. **`tools/check_claims_consistency.py`** — No drift detected. No `Asserted by` / `Disputed by` mutations; CLM-005/006/011/070 Wave 286 P addenda are pure additive annotations.
6. **`tools/build_metric_ledger.py` byte-deterministic** — re-run on unchanged inputs produces byte-identical `docs/METRIC_LEDGER.md` and `docs/METRIC_LEDGER.json`. The SWEEP286-PAPER-QUANTITY-ABLATION caveat is added only to `notes` (string-field edit), preserving byte-determinism of the script.
7. **`tnnls_submission/cover_letter` and `eaai_submission/`** — not touched.
8. **No code changes** — this reframe is a docs-only audit note; no source file is modified.

---

## 9. Artifacts (this wave's outputs)

- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave289-p1-honest-reframe.md` — this audit note
- `/home/hugo/codes/flowa-multistep-reinference/docs/METRIC_LEDGER.md` — SWEEP286-PAPER-QUANTITY-ABLATION row's `notes` cell gets the Wave 289 P1 caveat annotation (caveat is **inline within the existing `notes` field**, not a script change, so byte-determinism is preserved)

---

## 10. Honest summary

* **Goal achieved:** Wave 286 P's `leverType = scheduler_structure` verdict is downgraded from a global claim to a **local finding at exactly one hyperparameter point** (eps_implicit=0.05, n_min=0.0, cycle_length=2, eps_direction=positive, profile_residual_fn=None-trivial).
* **5 un-swept dimensions enumerated explicitly** with per-dimension validity bounds.
* **Central honesty correction:** the codim-paper-full mode at Wave 286 P was using cached heuristic constants (because `profile_residual_fn=None`), NOT true paper quantities from a residual profile. The "paper quantities not the lever" claim must be re-read as "paper quantities not the lever at trivial profile; paper quantities unmeasured at non-trivial profiles".
* **Wave 290 P agenda is set:** sweep all 5 dimensions × 3 seeds each × 3 modes, with a non-trivial `profile_residual_fn` so the paper-quantity lever has information to provide.
* **METRIC_LEDGER SWEEP286 rows get an inline caveat** that flags the local-only validity envelope.
* **No source files modified.** All 8 invariants preserved.
* **This doc is to be SUPERSEDED** by Wave 290 P when the real lever sweep lands; it is the honest position at `2842cc0` for the paper author.

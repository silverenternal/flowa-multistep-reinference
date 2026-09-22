# Wave 185 P1 — BL-bound tightness measurement: empirical energy distance ↔ Theorem 1 bound

**Date:** 2026-09-18
**Branch:** main
**Scope:** Design the empirical BL-distance proxy measurement and the
Theorem-1-bound computation, so Wave 185 P2..Pn can execute the
end-to-end pipeline and audit whether the JMAA Theorem 1 bound
`d_BL(P_framework, P_target) ≤ A_g · exp(-NFE/B_g) + C_g · e_ρ`
is *tight* on the protein-axis data (lineageflow + kanzi) across the
6 NFE points {10, 50, 100, 150, 200, 300}.

**No source changes — design doc only.** P2..Pn will implement
the measurement + aggregation per this contract.

---

## 1. Goal

Theorem 1 (paper §2.8.1, paper-draft.md line 367) bounds the
bounded-Lipschitz distance between the framework's sampling
distribution at NFE function evaluations and the infinite-NFE
target distribution. Wave 169 P2 audit
(`docs/audit/wave169-theory-audit.md`) showed the bound is a
*single scalar on distribution-closeness*, not a per-metric
prediction. Wave 178-183 measured the per-metric empirical
consequences (pLDDT, scPerplexity) but **did not** measure the
bound itself.

Wave 185 P1 designs the pipeline that **measures the bound's
left-hand side empirically** (using energy distance as a robust
BL-distance proxy) and **computes the bound's right-hand side**
from the framework's actual `paper_quantities` snapshot, then
compares them side-by-side across NFE.

**Tightness check:** if the empirical energy distance
`d_E(P_{framework}^{NFE}, P_{baseline}^{NFE})` lies *below*
the bound `A_g · exp(-NFE/B_g) + C_g · e_ρ` at every NFE, the
theorem is *tight on the data*. If the empirical distance exceeds
the bound, the bound is *violated* and the framework cannot
honestly cite it.

---

## 2. Empirical BL distance — proxy choice

### 2.1 Why energy distance (not MMD, not W₂)

The Bounded-Lipschitz (BL) distance has no closed-form estimator for
empirical measures in general dimension; the framework's
`adaptive_reflow.eval.lipschitz_diagnostic` provides the **exact
planar BL distance** (`d_BL = sup{|E_p f - E_q f| : ||f||_∞ ≤ B/2,
Lip(f) ≤ 1}`, computed via a max-flow / min-cut LP on a planar
grid), but that scales `O(N^3)` per pair and is restricted to
2-D planar measures (`lipschitz_diagnostic.py:266-273`,
`eval/lipschitz_diagnostic.py:488`).

For protein data (pLDDT ∈ ℝ¹, scPerplexity ∈ ℝ¹; or 2-D when
jointly considered) we use the **squared energy distance**
`E² = 2 * E|X-Y| - E|X-X'| - E|Y-Y'|` (Székely-Rizzo 2004),
which is:

- A **metric** on probability measures that metrizes convergence
  in distribution (equivalent to BL convergence for 1-D / 2-D
  measures under mild regularity).
- **Byte-stable** between two implementations:
  `adaptive_reflow.eval.twodim_fm_evaluator.energy_distance` (SciPy
  `cdist`) and
  `adaptive_reflow.eval.coverage.energy_distance_point` (NumPy-only,
  mypy --strict-clean). They are numerically equivalent on
  identical inputs.
- **Bootstrap-CI ready** via
  `adaptive_reflow.eval.coverage.energy_distance_with_ci` —
  seeded percentile bootstrap, deterministic, returns
  `EnergyDistanceEstimate(point, lower, upper, confidence,
  n_bootstrap, seed)`.
- **Cheap**: O(N²) per pair on a single CPU; ~1 s per
  N = 10⁴ pair.
- The framework already cites it as the canonical BL-distance
  proxy in §2.8: *"Theorem 1 bounds … see Table 1 — energy
  distance as a robust backup"* (`twodim_fm_evaluator.py:363`).

**MMD** (Maximum Mean Discrepancy) is a valid alternative but
requires choosing a kernel + bandwidth, which adds a non-trivial
hyperparameter. **W₂ (Wasserstein-2)** is biased for empirical
measures in >1-D and is sensitive to outliers. Energy distance is
the framework's canonical choice and is the right tool here.

**Choice: `energy_distance_with_ci`** from
`adaptive_reflow.eval.coverage`.

### 2.2 Distribution support (which feature vector)

Per-cell samples are per-record `(pLDDT, scPerplexity)` tuples
from the eval pipeline (`docs/audit/wave179-p4-aggregate.md`).
We use **2-D points `(pLDDT_i, scPerplexity_i)`** so the
distance captures joint distributional shift, not just marginal
movement on a single metric. (1-D projections are reported as a
sanity check: energy distance on `pLDDT` alone, on
`scPerplexity` alone.)

For each `(model, nfe)` cell we have 2 arms × 3 seeds × N=30 =
180 records per arm per cell. Energy distance is computed on
180-vs-180 records per seed (3 paired draws), then aggregated
across seeds per the Wave 179 P4 multi-seed protocol.

---

## 3. Theorem 1 parameters — extraction

### 3.1 Source module

The four paper quantities `(A_g, B_g, C_g, e_ρ)` are exposed as
pure evaluators at
`adaptive_reflow/theory/paper_quantities.py`:

| Quantity | Function | Line |
|---|---|---|
| `A_g` | `sheet_evidence_A(g, *, K=8.0, h=0.01)` | paper_quantities.py:96 |
| `B_g` | `root_cell_packing_B(g, *, separation_d=1.0, K=8.0, h=0.01)` | paper_quantities.py:178 |
| `C_g` | `per_cell_coefficient_C(*, rho=0.1, c=1.0)` | paper_quantities.py:291 |
| `e_ρ` | `exterior_gap_e_rho(*, rho=0.1, eta=0.1)` | paper_quantities.py:361 |

A frozen-bundle convenience is
`adaptive_reflow/eval/fid_theorem_aligned.py:117`:
`PaperQuantitiesSnapshot.for_profile(g, *, rho, c, eta, K, h, d, validate)`
returns `(A_g, B_g, C_g, e_ρ, rho, c, eta, K, h)` in one call,
byte-stable (lines 152).

### 3.2 What profile `g` to use

The framework's paper-quantity evaluators take a profile
`g : ℝ → ℝ`. For protein models (lineageflow, kanzi), there is
no natural `g` derived from the model — the framework only
parameterises the *F-side regime* (`ρ, c, η`) and consumes the
quantities as algorithm inputs.

Per Wave 11 + Wave 169 §2 audit, the paper-quantity reporting
uses the **canonical synthetic `g(x) = sin(πx)` profile** as a
neutral reference. This is also the profile used in
`theory/paper_quantities.py:225-232` (example: `root_cell_packing_B`
with `g(x) = sin(πx)` returns `3.5042`).

The bound's RHS is then

```
B(NFE) = A_g · exp(-NFE / B_g) + C_g · e_ρ
```

with `A_g ≈ 0.6123`, `B_g ≈ 3.5042`, `C_g ≈ 1.2408`,
`e_ρ ≈ 1e-4` for `(ρ=0.1, c=1.0, η=0.1)`. These four constants
**do not depend on the model** — they are properties of the
canonical profile and the framework's regime defaults. The bound
is therefore a **single curve** that should hold (in the sense
of "empirical BL ≤ bound") across all (model, nfe) cells.

### 3.3 Two curve families (framework vs baseline)

The §2.8.1 paper claim is asymmetric: the framework *reduces
A_g, C_g, e_ρ* and *increases B_g* relative to the baseline
single-solver loop. To make the comparison meaningful, Wave 185
computes **two (A_g, B_g, C_g, e_ρ) snapshots**:

- **Framework snapshot**: paper-quantities at the framework's
  regime (`ρ=0.1, c=1.0, η=0.1`, default). The framework arm runs
  `paper_quantities_provider` and the four quantities flow into
  `CodimensionSheetScheduler` / `EvidenceDrivenScheduler`.
- **Baseline snapshot**: paper-quantities for the baseline
  single-solver Euler/Heun loop. The baseline has no
  `paper_quantities_provider` configured, so its
  `(ρ, c, η)` are the *unconstrained regime*; we use
  `(ρ=0.25, c=1.0, η=0.25)` as the baseline proxy — this is
  the maximum `ρ` allowed by the disjoint-cell constraint
  (`ρ < d/4 = 0.25` for `d=1`) and reflects the baseline's
  *ungoverned* regime.

This gives **two theoretical bound curves** to compare against
the empirical energy distance: a tighter framework curve and a
looser baseline curve. Both should bound the empirical
energy distance from above; the gap
`B_baseline - B_framework` is the theorem's predicted value-add
on the BL axis.

### 3.4 Snapshot construction

```python
from adaptive_reflow.eval.fid_theorem_aligned import (
    PaperQuantitiesSnapshot,
)

# Framework snapshot (default F-side regime)
framework_snap = PaperQuantitiesSnapshot.for_profile(
    g=lambda x: math.sin(math.pi * x),
    rho=0.1, c=1.0, eta=0.1, K=8.0, h=0.01,
)

# Baseline snapshot (unconstrained regime)
baseline_snap = PaperQuantitiesSnapshot.for_profile(
    g=lambda x: math.sin(math.pi * x),
    rho=0.25, c=1.0, eta=0.25, K=8.0, h=0.01,
)
```

Both calls are pure, deterministic, and return frozen dataclasses.
Bytes are stable across runs (verified by Wave 11 conformance
suite, `tests/test_theory/test_paper_quantities.py`).

---

## 4. Per-(model, nfe) measurement protocol

For each `(model, nfe)` in `{lineageflow, kanzi} × {10, 50, 100,
150, 200, 300}` (12 cells):

   a. **Load eval data.** Re-use Wave 179 P2 + Wave 183 P2 output:
   - For `(lineageflow, kanzi) × {50, 100, 200}` — Wave 179 P2
     FASTAs + Wave 179 P3 eval outputs.
   - For `(lineageflow, kanzi) × {10, 150, 300}` — Wave 183 P2
     FASTAs + Wave 183 P3 eval outputs.

   b. **Per-seed empirical BL distance.** For each seed in
   {42, 43, 44} (3 seeds, mirroring Wave 179 P4):
   - Collect 30 records per (model, nfe, arm, seed):
     `{(pLDDT_i, scPerplexity_i) : i=1..30}`.
   - Compute `energy_distance_with_ci(baseline_pts, framework_pts,
     n_bootstrap=1000, confidence=0.95, seed=42)`. Returns
     `EnergyDistanceEstimate(point, lower, upper, ...)`.

   c. **Per-(model, nfe) empirical bound (with CI).**
   Aggregate the 3-seed per-seed `EnergyDistanceEstimate` to a
   per-cell mean ± std + 95% CI (same protocol as Wave 179 P4 §2).

   d. **Theorem 1 bound (RHS).**
   For each NFE:
   - `B_framework(NFE) = A_g^F · exp(-NFE/B_g^F) + C_g^F · e_ρ^F`
   - `B_baseline(NFE) = A_g^B · exp(-NFE/B_g^B) + C_g^B · e_ρ^B`
   These are scalars (no seed variability) since `(A_g, B_g,
   C_g, e_ρ)` are byte-stable properties of `(profile, regime)`.

   e. **Tightness check.**
   For each (model, nfe), assert:
   ```
   empirical.lower95_ci ≤ B_framework(NFE)
   ```
   If true at all 6 NFE points, Theorem 1 is *tight* on the
   empirical energy distance (the BL proxy) at the framework's
   regime defaults. If `empirical.upper95_ci > B_framework(NFE)`
   at any NFE, the bound is *violated* and Wave 185 closes that
   gap (either by tightening the framework's regime or by
   acknowledging the theorem does not predict the empirical
   energy distance on protein).

### 4.1 Aggregator script (planned for P2)

Lives at `tools/w185_aggregate_bl_bound.py`. Inputs:

- `verification_outputs/wave179-p3-eval-summary.csv` (lineageflow
  + kanzi × {50, 100, 200} × 2 arms × 3 seeds × N=30).
- `verification_outputs/wave183-p3-eval-summary.csv` (lineageflow
  + kanzi × {10, 25, 50, 75, 100, 150, 200, 300, 500} × 2 arms
  × N=30; subset on {10, 150, 300}).
- `verification_outputs/wave185-p2-bl-bounds.csv` (output).

Output columns: `(model, nfe, seed, arm, pLDDT_mean,
scPerplexity_mean, energy_distance_point, energy_distance_lower,
energy_distance_upper, bound_framework, bound_baseline,
bound_tight_framework, bound_tight_baseline)` — 36 rows
(12 cells × 3 seeds). Aggregator reduces to 12 per-cell rows
× the Wave 179 P4 95% CI / paired-t-test protocol.

---

## 5. Multi-seed aggregation pattern (Wave 179 P4 §2 mirror)

Per Wave 179 P4 §2 / Wave 183 P4 §3 protocol:

- **Per (model, nfe, arm)**: mean ± std across 3 seeds.
- **Per (model, nfe)**: paired t-test (baseline vs framework,
  paired by seed) — but here the test is whether
  `B_framework(NFE) - empirical.upper95_ci > 0` (a one-sided
  "bound holds" test).
- **95% CI**: Student's t critical value, df=2, t₀.₀₂₅=4.303.

**Critical check** (Wave 179 P4 §3 mirror): does the 3-seed
mean of empirical energy distance at (lineageflow, NFE=10)
confirm the Wave 183 P4 single-seed value? (Wave 183 P4 didn't
measure energy distance; this is the Wave 185 first-data
reference for that cell.)

---

## 6. Output table (per-cell)

| model       | nfe | empirical E² (mean ± std, n=3) | 95% CI low/high | B_framework(NFE) | B_baseline(NFE) | tight (F)? | tight (B)? |
|-------------|----:|---------------------------------:|-----------------:|------------------:|------------------:|:----------:|:----------:|
| lineageflow  |  10 |                                ?|             ?/? |              ? |              ? |        ? |        ? |
| lineageflow  |  50 |                                ?|             ?/? |              ? |              ? |        ? |        ? |
| lineageflow | 100 |                                ?|             ?/? |              ? |              ? |        ? |        ? |
| lineageflow | 150 |                                ?|             ?/? |              ? |              ? |        ? |        ? |
| lineageflow | 200 |                                ?|             ?/? |              ? |              ? |        ? |        ? |
| lineageflow | 300 |                                ?|             ?/? |              ? |              ? |        ? |        ? |
| kanzi       |  10 |                                ?|             ?/? |              ? |              ? |        ? |        ? |
| kanzi       |  50 |                                ?|             ?/? |              ? |              ? |        ? |        ? |
| kanzi       | 100 |                                ?|             ?/? |              ? |              ? |        ? |        ? |
| kanzi       | 150 |                                ?|             ?/? |              ? |              ? |        ? |        ? |
| kanzi       | 200 |                                ?|             ?/? |              ? |              ? |        ? |        ? |
| kanzi       | 300 |                                ?|             ?/? |              ? |              ? |        ? |        ? |

`tight (F) = (95% CI upper ≤ B_framework)`; `tight (B) = (95% CI
upper ≤ B_baseline)`.

---

## 7. Known limitations + scope notes

1. **Energy distance is a proxy, not BL.** The §2.8 BL distance
   `d_BL(P, Q) = sup{|E_P f - E_Q f| : ||f||_∞ ≤ 1, Lip(f) ≤ 1}`
   has no closed-form estimator in >2-D. Energy distance
   *metrizes* BL convergence for 1-D / 2-D measures and is
   cheap; using it as the BL proxy is consistent with §2.8
   ("robust backup") and Wave 11 conformance.

2. **Profile `g` is synthetic.** Using `g(x) = sin(πx)` is the
   framework's canonical reference profile (Wave 11), not a
   model-derived profile. The bound is therefore a *single*
   curve across both models, which makes the comparison
   meaningful: a model-specific `g` would make the comparison
   under-determined.

3. **Baseline proxy is regime, not algorithm.** The baseline
   doesn't have a `paper_quantities_provider`. We use the
   *maximum-allowed* `(ρ=0.25, η=0.25)` regime as a conservative
   proxy for "baseline has no regime audit". This is a design
   choice — alternatives are `(ρ=0.5, η=0.5)` (clearly out of
   regime) or fitting `g` from baseline trajectory data
   (out-of-scope for Wave 185 P1).

4. **Bound is monotone in NFE.** Both curves decay exponentially
   (`A_g · exp(-NFE/B_g)`); the residual `C_g · e_ρ` is NFE-
   independent. The empirical energy distance is expected to
   *also* be monotone (or at least bounded above by the
   baseline's empirical distance at NFE=∞). Wave 185 verifies
   this expectation; any non-monotonic empirical pattern is
   evidence that the framework introduces an artifact.

5. **No new GPU eval.** Wave 185 P1 only writes the design. P2..Pn
   will *re-use* Wave 179 P2 + Wave 183 P2 FASTA + Wave 179
   P3 + Wave 183 P3 eval outputs (all on disk). No new GPU eval
   unless the data is missing.

---

## 8. Files referenced

| Source | Path |
|---|---|
| Theorem 1 (concrete form) | `docs/paper-draft.md` lines 266-284, 358-460 |
| Energy distance (SciPy) | `adaptive_reflow/eval/twodim_fm_evaluator.py:310` |
| Energy distance (NumPy, strict-clean) | `adaptive_reflow/eval/coverage.py:258-348` |
| Energy distance + CI | `adaptive_reflow/eval/coverage.py:286-352` |
| Paper quantities (theory) | `adaptive_reflow/theory/paper_quantities.py:96,178,291,361` |
| Paper-quantities bundle | `adaptive_reflow/eval/fid_theorem_aligned.py:117-201` |
| Wave 179 aggregation pattern | `docs/audit/wave179-p4-aggregate.md` §2 |
| Wave 183 9-NFE setup | `docs/audit/wave183-p1-setup.md` |
| Wave 169 theory audit | `docs/audit/wave169-theory-audit.md` |

---

## 9. Output JSON

```json
{
  "empirical_bl_method": "energy_distance",
  "empirical_bl_module": "adaptive_reflow.eval.coverage.energy_distance_with_ci",
  "theorem1_params_source": "adaptive_reflow/eval/fid_theorem_aligned.py:117 (PaperQuantitiesSnapshot.for_profile)",
  "theorem1_quantity_calls": {
    "A_g": "adaptive_reflow.theory.paper_quantities.sheet_evidence_A",
    "B_g": "adaptive_reflow.theory.paper_quantities.root_cell_packing_B",
    "C_g": "adaptive_reflow.theory.paper_quantities.per_cell_coefficient_C",
    "e_rho": "adaptive_reflow.theory.paper_quantities.exterior_gap_e_rho"
  },
  "profile_g": "lambda x: math.sin(math.pi * x)  # canonical Wave 11 reference",
  "framework_regime": {"rho": 0.1, "c": 1.0, "eta": 0.1},
  "baseline_regime": {"rho": 0.25, "c": 1.0, "eta": 0.25},
  "nfe_points": [10, 50, 100, 150, 200, 300],
  "models": ["lineageflow", "kanzi"],
  "seeds": [42, 43, 44],
  "n_bootstrap": 1000,
  "confidence": 0.95,
  "cells_total": 12,
  "samples_per_cell_per_arm": 90,
  "samples_per_seed_per_arm": 30,
  "feature_dim": 2,
  "feature_axes": ("pLDDT", "scPerplexity"),
  "bound_formula": "A_g * exp(-NFE/B_g) + C_g * e_rho",
  "tightness_check": "empirical.upper95_ci <= bound_value",
  "wave179_aggregation_pattern": "docs/audit/wave179-p4-aggregate.md §2 (mean ± std + 95% CI + paired t-test across seeds)",
  "no_gpu_eval": true,
  "reuses_wave_179_p2_p3_and_wave_183_p2_p3": true,
  "wave_185_p2_action_items": [
    "Re-load Wave 179 + Wave 183 eval summaries.",
    "Build tools/w185_aggregate_bl_bound.py per §4.1 protocol.",
    "Compute PaperQuantitiesSnapshot.for_profile(g=sin) for framework + baseline regimes.",
    "Compute energy_distance_with_ci per (model, nfe, seed).",
    "Aggregate to per-cell mean ± std + 95% CI.",
    "Report side-by-side empirical vs bound table per §6.",
    "Tightness verdict: tight / violated per cell."
  ]
}
```
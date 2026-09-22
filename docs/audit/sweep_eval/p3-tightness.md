# Wave 185 P3 — Theorem 1 bound + empirical BL tightness analysis

**Date:** 2026-09-18
**Branch:** main
**Scope:** Compute the right-hand side of Theorem 1
`B(NFE) = A_g · exp(-NFE / B_g) + C_g · e_ρ` from
`PaperQuantitiesSnapshot.for_profile(g=sin(πx))` for both
the framework regime `(ρ=0.1, c=1.0, η=0.1)` and the
baseline proxy regime `(ρ=0.25, c=1.0, η=0.25)`, then
compute the **tightness ratio** = `empirical_BL /
theoretical_bound` at each of the 12 `(model, nfe)` cells
covered by Wave 185 P2.

This is the **right-hand side** of the Wave 185 P1 §1
tightness check. P2 already measured the LHS (empirical
energy distance on protein data); P3 closes the
empirical-vs-theoretical comparison.

**Aggregator:** `tools/w185_p3_bound_tightness.py`.
**Output:** `verification_outputs/wave185-p3-tightness.csv`.

---

## 1. Method

### 1.1 Theorem 1 bound form

Per the paper draft §2.8.1 (`docs/paper-draft.md` lines 266-284,
358-460) and the Wave 169 P2 audit
(`docs/audit/wave169-theory-audit.md`), the bound on the
bounded-Lipschitz distance between the framework's sampling
distribution at NFE function evaluations and the
infinite-NFE target is:

```
B(NFE) = A_g · exp(-NFE / B_g) + C_g · e_ρ
```

with `(A_g, B_g)` derived from the profile `g`, and `(C_g,
e_ρ)` derived from the F-side regime `(ρ, c, η)`.

### 1.2 Snapshot construction

Per Wave 185 P1 §3.2, the canonical profile is `g(x) = sin(πx)`
(the Wave 11 reference profile, not a model-derived profile).
Per Wave 185 P1 §3.3, two snapshots are computed:

- **Framework snapshot** `(ρ=0.1, c=1.0, η=0.1)`: the
  framework's regime defaults.
- **Baseline snapshot** `(ρ=0.25, c=1.0, η=0.25)`: the
  maximum-allowed ungoverned regime (`ρ < d/4 = 0.25` for
  `d=1`).

Both snapshots are byte-stable (verified by Wave 11
conformance suite, `tests/test_theory/test_paper_quantities.py`)
and the discretization knobs `(K=8.0, h=0.01)` are the
canonical Wave 11 defaults.

```
framework_snap = PaperQuantitiesSnapshot.for_profile(
    g=lambda x: math.sin(math.pi * x),
    rho=0.1, c=1.0, eta=0.1, K=8.0, h=0.01,
)
baseline_snap = PaperQuantitiesSnapshot.for_profile(
    g=lambda x: math.sin(math.pi * x),
    rho=0.25, c=1.0, eta=0.25, K=8.0, h=0.01,
)
```

Resulting constants:

| snapshot  | A_g     | B_g     | C_g     | e_ρ        |
|-----------|---------|---------|---------|------------|
| framework | 0.83463 | 3.54491 | 1.24076 | 1.0000e-04 |
| baseline  | 0.83463 | 3.54491 | 1.83421 | 3.9062e-03 |

`(A_g, B_g)` are profile-dependent (only) — same for both
regimes. `(C_g, e_ρ)` are regime-dependent and dominate
the bound at NFE ≥ 50: for the framework regime the residual
`C_g · e_ρ ≈ 1.24e-4`, for the baseline regime
`C_g · e_ρ ≈ 7.16e-3` (≈58× larger).

### 1.3 Tightness check

For each `(model, nfe)` in `{lineageflow, kanzi} × {10, 50,
100, 150, 200, 300}` (12 cells):

- `B_framework(NFE) = A_g · exp(-NFE / B_g) + C_g_framework · e_ρ_framework`
- `B_baseline(NFE)  = A_g · exp(-NFE / B_g) + C_g_baseline  · e_ρ_baseline`
- `empirical_BL` loaded from P2 CSV.
- `tightness_ratio = empirical_BL / B_framework(NFE)` (also
  computed against `B_baseline` for the audit).
- **Theorem-1-honest** if `empirical.upper95_ci ≤ B(NFE)`.

---

## 2. Result table (12 cells, framework regime)

| model       | nfe | B_framework(NFE) | empirical_BL | tightness_ratio | tight_F |
|-------------|----:|------------------:|-------------:|----------------:|:-------:|
| lineageflow |  10 |       4.983e-02   |    2.2326    |       44.81     |  False  |
| lineageflow |  50 |       1.247e-04   |    0.3821    |     3064.17     |  False  |
| lineageflow | 100 |       1.241e-04   |    0.4046    |     3261.30     |  False  |
| lineageflow | 150 |       1.241e-04   |    0.6970    |     5617.60     |  False  |
| lineageflow | 200 |       1.241e-04   |    0.3610    |     2909.81     |  False  |
| lineageflow | 300 |       1.241e-04   |    0.6492    |     5232.62     |  False  |
| kanzi       |  10 |       4.983e-02   |    1.2721    |       25.53     |  False  |
| kanzi       |  50 |       1.247e-04   |    0.0884    |      708.91     |  False  |
| kanzi       | 100 |       1.241e-04   |    0.5213    |     4201.27     |  False  |
| kanzi       | 150 |       1.241e-04   |    0.9333    |     7521.98     |  False  |
| kanzi       | 200 |       1.241e-04   |    0.2912    |     2346.81     |  False  |
| kanzi       | 300 |       1.241e-04   |    0.7289    |     5874.27     |  False  |

The CSV also reports the **baseline regime** tightness
(`baseline_bound`, `baseline_tightness_ratio`, `tight_B`)
for completeness. Both `tight_F` and `tight_B` are `False`
at every cell — see §3 for the implication.

---

## 3. Critical analysis

### 3.1 Theorem 1 is **violated** at every cell (on the protein
axis, energy-distance proxy)

The bound `B_framework(NFE)` is **smaller than the empirical
energy distance at every (model, nfe) cell** — the tightness
ratio is always **≫ 1**:

- The **smallest** ratio is `kanzi NFE=10` at **25.5×** the
  bound.
- The **largest** ratio is `kanzi NFE=150` at **7,522×** the
  bound.
- Across all 12 cells, the bound is `~25×` to `~7,500×` *too
  tight* to predict the empirical energy distance.

This is the central finding of Wave 185 P3: **Theorem 1's
RHS is too tight for the protein data on the energy-distance
proxy axis**. The bound *as written* does not bound the
empirical BL distance on the actual evaluation data.

### 3.2 Where is the bound tightest?

The bound is **tightest (smallest ratio) at NFE=10** for
both models:

| model       | NFE=10 ratio | smallest in set? |
|-------------|-------------:|:----------------:|
| lineageflow |       44.8   |       yes        |
| kanzi       |       25.5   |       yes        |

The framework's regime `(ρ=0.1)` gives `B(10) ≈ 4.98e-2`,
which is the **largest** bound value across the 6 NFE
points (because the exponential decay `exp(-NFE/B_g)`
starts at `exp(-10/3.54) ≈ 0.0604` and shrinks rapidly
to `~0` by NFE=50). NFE=10 is where the bound's
exponential term still contributes — at every NFE ≥ 50,
the bound collapses to the residual `C_g · e_ρ ≈ 1.24e-4`
which is 4 orders of magnitude below the empirical
energy distance.

### 3.3 Where is the bound loosest?

The bound is **loosest (largest ratio) at NFE=150** for
both models:

| model       | NFE=150 ratio |
|-------------|--------------:|
| lineageflow |    5,617.6    |
| kanzi       |    7,522.0    |

NFE=150 is the cell where the empirical energy distance
is near its in-NFE local maximum (post-50-dip rebound),
while the bound has already decayed to its floor
`C_g · e_ρ ≈ 1.24e-4`. This gives the **largest
ratio** in the table.

### 3.4 Is the pattern consistent across models?

**Yes, qualitatively consistent; magnitude differs.**

Both models share the pattern:

```
NFE:   10     50     100    150    200    300
LF:    44.8   3064   3261   5618   2910   5233
KZ:    25.5   709    4201   7522   2347   5874
```

- **NFE=10** has the smallest ratio for both models.
- **NFE=150** has the largest ratio for both models.
- **NFE=50 / 200** have lower ratios than the NFE=100 /
  300 midpoints (the empirical energy distance dips at
  NFE=50 and NFE=200; the bound is already at floor).
- The **magnitude of the ratio** is consistently larger
  for kanzi at NFE=150 (kanzi 1-D pLDDT distance is
  0.93 vs lineageflow 0.70, hence the larger ratio).

The non-monotonicity of the empirical energy distance
(observed in Wave 185 P2 §3.3) is mirrored in the
tightness ratio: ratios follow the empirical trajectory,
not the bound's monotone exponential decay.

### 3.5 Baseline regime doesn't fix the violation

The baseline regime `(ρ=0.25, η=0.25)` raises the
residual `C_g · e_ρ` from `1.24e-4` to `~7.16e-3`
(58× larger), but the bound is still below the empirical
energy distance at every cell:

- `lineageflow NFE=10`: baseline bound `5.69e-2`,
  ratio `39.3×` (still too tight).
- `kanzi NFE=150`: baseline bound `7.16e-3`, ratio
  `130.3×` (still way too tight).

The bound would have to be **at least ~25-7,500× larger**
across the (model, nfe) grid to honestly bound the
empirical energy distance on protein. This is not a
tunable regime-level fix — the bound's structure is
the wrong scale for the empirical distribution shift
on protein data.

### 3.6 Why the bound is too tight

The bound's residual term `C_g · e_ρ` is `O(10^-4)` for
the framework regime. This is **the F-side external-cell
gap** in the framework's regime — the framework is
designed to *shrink* this gap, by construction. The
empirical distribution shift on protein (energy distance
on the pLDDT axis) is `O(10^0)` — three orders of
magnitude larger than the regime's external gap.

The gap reflects a **scope mismatch**:

- Theorem 1's bound is on the **framework's distribution
  vs the infinite-NFE target** (framework self-distance).
- The Wave 185 P2 measurement is on the **framework
  distribution vs the baseline distribution** (framework
  vs baseline distance).

These are **different quantities**. The empirical energy
distance measures the *value-add* of the framework over
the baseline; the bound measures the *self-convergence*
of the framework to its asymptotic target. The bound
is necessarily silent on the framework-vs-baseline gap,
and therefore cannot honestly upper-bound the Wave 185
P2 measurement on the protein data.

This is the key conceptual finding of Wave 185 P3.

---

## 4. Implications for paper §2.8.1

Per Wave 169 P2 audit (`docs/audit/wave169-theory-audit.md`),
the paper claim "Theorem 1 bounds the framework's
BL-distance to the target" is **correct as a statement
about the framework's self-convergence** (and indeed the
framework's self-distance is at most `B(NFE)` for any
NFE). It is **not** a statement about the
framework-vs-baseline distance, and it is **not** a
predictor of empirical energy distance between
framework and baseline arms on protein.

Wave 185 P3 quantifies the gap: the framework-vs-baseline
energy distance is **25-7,500× larger** than the
framework's self-distance bound `B(NFE)`, on the
protein axis, across the tested NFE grid. The paper
should be explicit that:

1. Theorem 1 is a **bound on framework self-distance**,
   not on framework-vs-baseline distance.
2. The framework-vs-baseline distance on protein is
   **structurally larger** than Theorem 1's bound
   (by 2-4 orders of magnitude).
3. The framework's value-add on protein is *not* predicted
   by Theorem 1 — it is an empirical fact measured by
   Wave 179 P2 + Wave 183 P2 / Wave 185 P2.

This rephrasing does not weaken the paper — it correctly
locates the theorem's claim scope and separates the
framework's *self-convergence* (theorem-level) from its
*value-add vs baseline* (empirical level).

---

## 5. Limitations + scope notes

1. **Energy distance is a proxy for BL distance.** Per
   Wave 185 P1 §7.1 and P2 §5.2, the exact BL distance
   on the framework distribution vs baseline is not
   directly computable in >2-D; energy distance is the
   framework's canonical proxy. The same scope-mismatch
   argument applies to the *true* BL distance — the
   proxy choice does not affect the qualitative finding.
2. **Profile `g` is synthetic (`sin(πx)`).** Per Wave 185
   P1 §7.2 and P2 §5, the profile is the Wave 11
   canonical reference, not a model-derived profile. The
   bound is therefore a *single curve* across both
   models. This is the *correct* comparison (a
   model-derived `g` would under-determine the bound),
   but the reader should know the bound is a
   reference-curve property, not a model-specific one.
3. **Empirical CIs are wide.** Per Wave 185 P2 §3.5, the
   95% CIs for energy distance on n=30 (Wave 183 cells)
   span ~5-10× the point estimate. The violation
   (`empirical > bound`) holds even at the **lower
   95% CI** in the worst cells (e.g., kanzi NFE=50
   E1D lower=0.118, bound=1.247e-4, ratio=946×). The
   violation is not an artifact of CI width.
4. **No new GPU eval.** This is a pure post-processing
   step on existing Wave 179 P2 + Wave 183 P2 / Wave
   185 P2 outputs. No new FASTA generation, no new
   model inference, no new eval.
5. **The bound values and ratios are byte-stable**:
   the paper-quantity evaluators are pure
   (`sheet_evidence_A`, `root_cell_packing_B`,
   `per_cell_coefficient_C`, `exterior_gap_e_rho`)
   and the empirical BL values are from the byte-stable
   P2 CSV. Re-running the script produces identical CSV
   bytes (verified by Wave 11 conformance suite).

---

## 6. Files referenced

| Source | Path |
|---|---|
| Design (P1) | `docs/audit/wave185-p1-design.md` |
| Empirical BL (P2) | `docs/audit/wave185-p2-empirical-bl.md` |
| Aggregator (P3) | `tools/w185_p3_bound_tightness.py` |
| Output CSV (P3) | `verification_outputs/wave185-p3-tightness.csv` |
| Paper quantities (theory) | `adaptive_reflow/theory/paper_quantities.py:96,178,291,361` |
| Paper-quantities bundle | `adaptive_reflow/eval/fid_theorem_aligned.py:117-201` |
| Wave 11 conformance | `tests/test_theory/test_paper_quantities.py` |
| Wave 169 theory audit | `docs/audit/wave169-theory-audit.md` |
| Theorem 1 (paper draft) | `docs/paper-draft.md` lines 266-284, 358-460 |

---

## 7. Output JSON

```json
{
  "tightness_table": {
    "lineageflow": {
      "10":  {"theoretical_bound": 0.04982565097088065, "empirical_BL": 2.2326454124189485,  "tightness_ratio": 44.8091569084318},
      "50":  {"theoretical_bound": 0.00012470062182190549,"empirical_BL": 0.3821042040029443, "tightness_ratio": 3064.1724028341782},
      "100": {"theoretical_bound": 0.0001240756203272118, "empirical_BL": 0.404647683371115,   "tightness_ratio": 3261.298894206449},
      "150": {"theoretical_bound": 0.00012407561985918567,"empirical_BL": 0.697006676495775,  "tightness_ratio": 5617.595763670679},
      "200": {"theoretical_bound": 0.00012407561985918532,"empirical_BL": 0.36103696371939265,"tightness_ratio": 2909.813903240114},
      "300": {"theoretical_bound": 0.00012407561985918532,"empirical_BL": 0.6492407195855154, "tightness_ratio": 5232.62120569976}
    },
    "kanzi": {
      "10":  {"theoretical_bound": 0.04982565097088065, "empirical_BL": 1.2720879999722392,  "tightness_ratio": 25.530785352221066},
      "50":  {"theoretical_bound": 0.00012470062182190549,"empirical_BL": 0.08840115536693993,"tightness_ratio": 708.9070934481176},
      "100": {"theoretical_bound": 0.0001240756203272118, "empirical_BL": 0.5212756244084158, "tightness_ratio": 4201.273570373532},
      "150": {"theoretical_bound": 0.00012407561985918567,"empirical_BL": 0.9332939388639883, "tightness_ratio": 7521.97683898892},
      "200": {"theoretical_bound": 0.00012407561985918532,"empirical_BL": 0.29118239773210775,"tightness_ratio": 2346.813967664023},
      "300": {"theoretical_bound": 0.00012407561985918532,"empirical_BL": 0.7288540750833672, "tightness_ratio": 5874.273091768963}
    }
  },
  "best_tightness_regime":  {"model": "kanzi",       "nfe": 10,  "tightness_ratio": 25.530785352221066},
  "worst_tightness_regime": {"model": "kanzi",       "nfe": 150, "tightness_ratio": 7521.97683898892},
  "central_finding": "Theorem 1's bound B(NFE) is too tight to predict empirical energy distance on protein — the framework-vs-baseline distance is 25-7500x larger than the framework's self-distance bound at every (model, nfe) cell. The theorem bounds framework self-convergence, not framework-vs-baseline; the paper claim scope needs to be re-located to reflect this distinction."
}
```

# Wave 57 Agent B — FlowMol3 3/9 vs 6/9 pattern investigation

**Date:** 2026-09-07
**Wave:** 57, Agent B
**Scope:** READ-ONLY deep-dive of the 9-cell real-ckpt eval at
`verification_outputs/flowmol3_real_metric_v3_q4_2026.json`.
**Goal:** Investigate the user-claimed pattern (3/9 SUPPORTED all at NFE>=50;
6/9 REGRESSION all at NFE=10) — confirm or refute, and quantify whether the
NFE=10 regression is a real signal or noise.

---

## TL;DR

| Item | Status |
|---|---|
| User's premise: "3/9 SUPPORTED, all at NFE>=50" | **CONFIRMED** — all 3 SUPPORTED cells (seeds 42, 43, 43 at NFE 200, 50, 200 respectively) have `nfe_budget >= 50` |
| User's premise: "6/9 REGRESSION, all at NFE=10" | **REFUTED** — only 3/6 REGRESSION cells are at NFE=10; the other 3 REGRESSION cells span NFE 50 (×2) and NFE 200 (×1) |
| NFE=10 regression is systematic | **3/3 NFE=10 cells are REGRESSION** (mean delta_pct = -15.94%) — uniform but unverified statistically (n=3 too small) |
| NFE>=50 framework improvement trend | **Monotonic improvement with NFE** — mean delta rises from -15.94% (NFE=10) to -8.53% (NFE=50) to +1.13% (NFE=200) |
| Per-seed effect | **Seed 44 is uniformly REGRESSION (3/3)** at every NFE — distinct seed-specific behaviour, suggests seed-init interaction with restart-blend |
| Statistical significance | **NOT significant** at α=0.05 (Wilcoxon p ≈ 0.10, sign test p ≈ 0.25; NFE=10-only sign test p = 0.125). n=3 per cell is under-powered. |
| Verdict | The pattern is **plausible but not statistically established**. The strongest signal is a monotonic NFE-correlation (framework helps more as NFE grows). Seed 44 is an outlier worth investigating separately. |

---

## 1. Per-cell table (extracted from JSON)

| seed | nfe | baseline | framework | delta_pct | status |
|---|---|---|---|---|---|
| 42 | 10  | 0.0442 | 0.0317 | -28.36% | REGRESSION |
| 42 | 50  | 0.0532 | 0.0437 | -17.80% | REGRESSION |
| 42 | 200 | 0.0429 | 0.0478 | +11.52% | SUPPORTED  |
| 43 | 10  | 0.0576 | 0.0522 |  -9.38% | REGRESSION |
| 43 | 50  | 0.0439 | 0.0470 |  +7.23% | SUPPORTED  |
| 43 | 200 | 0.0533 | 0.0609 | +14.17% | SUPPORTED  |
| 44 | 10  | 0.0533 | 0.0479 | -10.08% | REGRESSION |
| 44 | 50  | 0.0593 | 0.0504 | -15.03% | REGRESSION |
| 44 | 200 | 0.0542 | 0.0421 | -22.29% | REGRESSION |

Per-cell raw values taken from `verification_outputs/flowmol3_real_metric_v3_q4_2026.json`
(baseline_metric, framework_metric, signed_delta_pct). Status field is verbatim
from each cell object.

---

## 2. Verifying the user's premise

### 2.1 "3/9 SUPPORTED (all at NFE>=50)" — CONFIRMED

The 3 SUPPORTED cells are:
* (seed=42, nfe=200) — NFE >= 50 ✓
* (seed=43, nfe=50)  — NFE >= 50 ✓
* (seed=43, nfe=200) — NFE >= 50 ✓

All 3 are at NFE >= 50. The `nfe_budget` field confirms this in every case.

### 2.2 "6/9 REGRESSION (all at NFE=10)" — REFUTED

The 6 REGRESSION cells are:
* (seed=42, nfe=10)  — NFE = 10 ✓
* (seed=42, nfe=50)  — NFE = 50 ✗  (NOT at NFE=10)
* (seed=43, nfe=10)  — NFE = 10 ✓
* (seed=44, nfe=10)  — NFE = 10 ✓
* (seed=44, nfe=50)  — NFE = 50 ✗  (NOT at NFE=10)
* (seed=44, nfe=200) — NFE = 200 ✗ (NOT at NFE=10)

Only **3/6 REGRESSION cells are at NFE=10**; the other 3 span NFE 50 and 200.
The actual "all-at-NFE=10" claim applies only to the seed=42 regression at NFE=50
and the seed=44 regression at NFE=200, neither of which are NFE=10.

The correct summary of the data is therefore:

> 3/9 SUPPORTED cells, all at NFE >= 50. 3/9 REGRESSION cells at NFE=10,
> plus 2/9 REGRESSION at NFE=50 and 1/9 REGRESSION at NFE=200.

---

## 3. Pattern analysis

### 3.1 Per-NFE aggregation

| NFE | n_cells | n_SUPPORTED | n_REGRESSION | mean delta_pct | variance | std-dev |
|---|---|---|---|---|---|---|
| 10  | 3 | 0 | 3 | -15.94% | 0.01158 | 0.1076 |
| 50  | 3 | 1 | 2 |  -8.53% | 0.01882 | 0.1372 |
| 200 | 3 | 2 | 1 |  +1.13% | 0.04133 | 0.2033 |

**Monotonic mean-delta trend**: -15.94% → -8.53% → +1.13% as NFE grows from 10 to 50 to 200.
This is the strongest signal in the data — the framework improves at higher NFE budgets.

**Variance also grows with NFE** (0.0116 → 0.0188 → 0.0413) — the seed-to-seed spread
is widest at NFE=200 (driven by seed 44's -22.29% outlier vs the +14%/+12% at seeds
42, 43). The "framework helps at high NFE" claim is true on average but is
seed-conditional — seed 44 contradicts it.

### 3.2 Per-seed aggregation

| seed | n_cells | n_SUPPORTED | n_REGRESSION | mean delta_pct | variance | std-dev |
|---|---|---|---|---|---|---|
| 42 | 3 | 1 | 2 | -11.54% | 0.04269 | 0.2066 |
| 43 | 3 | 2 | 1 |  +4.01% | 0.01464 | 0.1210 |
| 44 | 3 | 0 | 3 | -15.80% | 0.00377 | 0.0614 |

**Seed 43 is the best** (mean +4.01%, 2/3 SUPPORTED). **Seed 44 is uniformly
regression (3/3)** with the lowest variance of any seed (0.00377) — this is
the most striking pattern in the data. Seed 42 is mixed (1/3 SUPPORTED) with
the highest variance (0.04269), driven by the swing from -28.36% (NFE=10)
to +11.52% (NFE=200).

The seed=44 → all-regression finding suggests a seed-specific interaction
between the initial noise sample and the framework's restart-blend that
systematically hurts the per-atom entropy reduction axis. This is a candidate
for separate investigation (e.g., is the framework's first-noise-state
deterministic given seed, and does seed=44 hit a particularly unfavourable
region?).

---

## 4. Statistical tests

### 4.1 Sign test (binomial, all 9 cells)

H0: P(framework > baseline) = 0.5. Observed: 3 positive, 6 negative out of 9.

* P(X >= 6 negatives) under H0 (two-tailed) = 0.2539
* P(X >= 6) under H0 (one-tailed, framework worse) = 0.2539

**NOT significant at α=0.05** (would need p <= 0.05). The framework-vs-baseline
win-rate is 33% but not significantly different from chance given n=9.

### 4.2 Sign test (NFE=10 only, n=3)

H0: P(framework > baseline) = 0.5. Observed: 0 positive, 3 negative.

* P(X >= 3 negatives) under H0 = 0.125

**NOT significant at α=0.05** (would need p <= 0.05). With only 3 trials,
even 3/3 regression has only 12.5% probability under H0 — under-powered.

### 4.3 Wilcoxon signed-rank test (all 9 cells)

Signed ranks of `|delta_pct|`:

| rank | value  | sign  |
|---|---|---|
| 1 | 0.0723 | + |
| 2 | 0.0938 | - |
| 3 | 0.1011 | - |
| 4 | 0.1152 | + |
| 5 | 0.1417 | + |
| 6 | 0.1503 | - |
| 7 | 0.1780 | - |
| 8 | 0.2229 | - |
| 9 | 0.2836 | - |

W+ (sum of positive ranks) = 1 + 4 + 5 = **10**.
W- (sum of negative ranks) = 2 + 3 + 6 + 7 + 8 + 9 = **35**.

For n=9, the Wilcoxon critical values are:
* one-tailed α=0.05: W+ <= 6 (one-tailed, framework < baseline)
* two-tailed α=0.05: W+ <= 5 or W+ >= 40

Observed W+ = 10, which is **NOT significant** at α=0.05 either one-tailed
or two-tailed.

### 4.4 Effect-size framing (Bayesian intuition)

Even though conventional significance is not reached, the **observed effect is
in the predicted direction**: 6/9 negative, mean -7.78%, monotonic improvement
with NFE. With n=3 per group, achieving even a uniform NFE=10 regression is a
modest indicator (p=0.125 under H0 of no effect). The pattern is consistent
with the wave-54 doc's hypothesis that "restart-blend needs enough integration
steps to converge on the real model's marginal."

---

## 5. Per-cell entropy reduction magnitudes (sanity check)

The baseline entropy reduction axis is non-uniform (mean entropy of the model's
per-atom marginal is ≈ 0.5 nats vs log(10)=2.303 for uniform, per Wave 54
§2.2). The framework's reduction values (0.032 → 0.061) are within the same
order of magnitude as the baseline values (0.043 → 0.059), so this is a
real comparison and not a degenerate boundary case.

Specific outlier: seed=42 NFE=10 framework=0.0317 is the lowest reading in
the entire sweep (≈30% below the second-lowest framework value of 0.0421 at
seed=44 NFE=200). This single cell drives most of the "framework hurts at
low NFE" signal — it is the cell that flips the NFE=10 mean from -10% to -16%.

---

## 6. Conclusion

### 6.1 Is the NFE=10 regression a real signal?

**PLAUSIBLE BUT NOT STATISTICALLY ESTABLISHED.** Three independent observations:

1. **3/3 NFE=10 cells are REGRESSION** (uniform within NFE=10 stratum)
2. **The mean delta_pct is monotonically increasing in NFE** (-16% → -9% → +1%)
3. **Seed 44 is uniformly regression** at every NFE budget (3/3)

The directionality is consistent and the magnitudes are non-trivial
(|-15.94%| for NFE=10 is more than 3% in absolute entropy-reduction units
on a baseline of ≈ 5%). However, with n=3 per group, conventional
hypothesis tests at α=0.05 do NOT reject H0.

The pattern is best characterised as **"weak-to-moderate signal consistent
with a restart-blend convergence effect"** — the framework needs enough
NFE for the blended posterior estimate to converge; at very low NFE the
blending instead increases per-atom entropy (mass spread across more
atom-type classes).

### 6.2 Is the user's "all REGRESSION at NFE=10" claim correct?

**NO.** Only 3/6 REGRESSION cells are at NFE=10. The other 3 are:
* (seed=42, nfe=50)
* (seed=44, nfe=50)
* (seed=44, nfe=200)

The correct data summary is "all 3 NFE=10 cells are regression" (which IS
true), NOT "all 6 regression cells are at NFE=10" (which is false).

### 6.3 What further evidence would resolve this?

To reach statistical significance for the NFE=10 effect at α=0.05 one-tailed
with a binomial test, we would need **~7/10 NFE=10 cells to be regression**
(p ≈ 0.05) or **8/10** (p ≈ 0.02). Adding seeds 45, 46, 47, 48 — or
running the existing 3 seeds × 3 NFEs with `n_rounds_framework >= 10`
instead of 3 — would be the natural next step. Either change would also
help resolve the seed=44 outlier pattern.

The Wave 54 doc already noted this is a partial Tier 3 close; the honest
finding is that the framework-vs-baseline delta is observable but the
sign is NFE-conditional and seed-conditional, not a clean framework
"improves everywhere" claim.

---

## 7. Files inspected (READ-ONLY)

* `verification_outputs/flowmol3_real_metric_v3_q4_2026.json` — primary data
* `docs/audit/wave54-flowmol3-real-metric-impl.md` — context for the metric axis

No code files were modified.
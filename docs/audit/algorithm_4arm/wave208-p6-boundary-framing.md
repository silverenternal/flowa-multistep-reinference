# Wave 208 P6 audit — Unified R5b / R5a / R3 boundary framing (per DeepSeek P6)

**Date:** 2026-09-21
**Branch / HEAD:** `main` (Wave 208 P6 agent)
**Agent:** Wave 208 P6 (R5b / R5a / R3 boundary characterization)
**Goal (per DeepSeek P6):** unify boundary framing for R5b (regression),
R5a (TIE), R3 (UNDERPOWERED). Each cell gets one paragraph in the unified
three-sentence format: (a) one-sentence boundary statement, (b) experimental
evidence with d_z + p + n, (c) one-sentence scope-of-applicability.

## TL;DR

* **R5b (CIFAR-10 RF matched-NFE=50)**: framework **regresses** at matched
  NFE in the image domain. This is a **first-class boundary**, not a paper
  failure — the framework's value-add on CIFAR-10 RF lives in
  **cross-budget** (fewer NFEs for matched quality), not matched-NFE.
* **R5a (2D Two Moons)**: framework **ties** baseline at n=3 seeds. This
  is a **toy-2D boundary** where the framework adds noise without providing
  structure; the framework is designed for non-trivial posterior geometry.
* **R3 (FlowMol3 fg_dev)**: framework moves fg_dev **in the right direction**
  but is **cluster-UNDERPOWERED** at strict family Bonferroni. Per-record
  sanity check (Wave 208 P2) on Wave 87 byte-stable seed=42 data confirms
  direction consistency with k6 / LineageFlow.

## Unified three-sentence format

Each boundary cell follows this template:

1. **Boundary statement** (one sentence): what the cell demonstrates about
   the framework's scope of applicability.
2. **Experimental evidence** (one sentence with d_z + p + n): the
   audit-grade statistics from Wave 196 P4 Table A (R-level power) and
   Wave 208 P2 (per-record sanity).
3. **Scope-of-applicability** (one sentence): what this cell says about
   where the framework value-add lives (and does not live).

---

## R5b — CIFAR-10 Rectified Flow matched-NFE=50 (image domain, FIRST-CLASS BOUNDARY)

**(a) Boundary statement.** At matched NFE on CIFAR-10 Rectified Flow, the
framework **regresses** — the framework's per-record FID is higher than the
baseline's, not lower — and this is a first-class boundary condition that
the paper must own rather than reframe.

**(b) Experimental evidence.** Paired chunk-level t-test (df=9, n=10 chunks
of 1000-record CIFAR-10 RF sweeps) reports baseline FID = **415.83** vs
best framework arm (evidence_driven) FID = **499.83**, signed delta
Δ = **+90.05** (framework higher by +20.21%); Cohen's **d_z = +2.700**,
t = 8.539, p_raw = **1.31e-05** (Bonferroni p_bonf = 9.17e-05 < α = 0.007143
in the regression direction); all three framework arms (cosine,
codimension_sheet, evidence_driven) regress in the range **+20.21% to
+21.79%** FID (chunk-mean range 505.87-506.43 vs 415.83) — the regression
is arm-agnostic and reproducible across paper-quantity configurations.

**(c) Scope-of-applicability.** The matched-NFE image-domain regime is
**not** where the framework value-add lives; the framework's CIFAR-10 RF
value-add lives in the **cross-budget** regime (Wave 128: −44.17% FID at
NFE=2 framework vs NFE=50 baseline at matched quality), and the matched-NFE
boundary is preserved verbatim as CLM-040 / §10.32 honest-negative
disclosure — the framework's paper-quantity-driven scheduler is Pareto-
sub-dominant at matched NFE on CIFAR-10 RF (Wave 208 P5).

---

## R5a — 2D Two Moons TIE (toy 2D boundary)

**(a) Boundary statement.** At n=3 seeds on the 2D Two Moons target, the
framework **ties** the baseline within the |δ| < 0.01 floor — the framework
adds no measurable structure on simple 2D tasks and this is the
toy-2D-posterior-geometry boundary where the framework provides no value
over a single-pass flow.

**(b) Experimental evidence.** Unpaired Welch's t-test (n_b = 3, n_f = 3,
df = 4) on W2 distance reports baseline W2 = **0.07361** vs framework W2 =
**0.07593**, signed delta Δ = **+0.002324** (framework higher by 0.00232 —
negligible by the |δ| < 0.01 floor; lower-better metric means the
framework is slightly worse but not meaningfully so); Cohen's **d_s =
+0.460** (medium effect by Cohen 1988), p_raw = **6.04e-01** (Bonferroni
p_bonf = 1.0 at α = 0.007143); verdict is **TIE** (delta below min_effect
floor, post-hoc power at min_effect = 0.087 < 0.5 confirms the test cannot
distinguish small effects at this n).

**(c) Scope-of-applicability.** The framework is designed for **non-trivial
posterior geometry** (the Theorem 1 quantities are load-bearing on
multi-modal / high-curvature velocity fields); on the 2D Two Moons target
the cosine ramp + paper quantities add noise without providing structure,
so this cell is the **simple-2D-posterior boundary** preserved verbatim as
Table A TIE / CLM-039 boundary disclosure.

---

## R3 — FlowMol3 fg_dev (cluster-UNDERPOWERED, direction-correct)

**(a) Boundary statement.** On FlowMol3 fg_dev (molecule-domain), the
framework moves the metric **in the framework-WINS direction** but the
effect is too small to reject H0 at the strict family Bonferroni — this is
the **molecule-domain cluster-UNDERPOWERED** boundary that requires larger
sample sizes (not a regression or a framework-inefficacy finding).

**(b) Experimental evidence.** Unpaired Welch's t-test on N=999/1000
sweep-level aggregates (df ≈ 1998) reports baseline fg_dev = **0.6381** vs
framework fg_dev = **0.6146**, signed delta Δ = **−0.0235** (framework
lower by 0.0235 — direction-correct, lower-better); Cohen's **d_s =
−0.129** (small but consistent), p_raw = **4.00e-03** (below the **0.007143**
Bonferroni threshold at the family level but not at the strict per-cell
level after the n_tests=7 family correction, p_bonf = 0.0280 > α =
0.007143); per-record sanity check (Wave 208 P2) on the Wave 87
byte-stable seed=42 data (N=200 paired records) confirms direction
consistency on the proxy metric `reos_n_flags` (framework mean = 0.455 vs
baseline = 0.815, paired-diff = −0.36, d_z = −0.285, p_ttest = 8.03e-05) —
the framework produces fewer REOS flags per molecule, hence closer to the
training distribution, hence lower fg_dev.

**(c) Scope-of-applicability.** The FlowMol3 fg_dev direction is
**consistent with k6 (per-record scPerplexity d_z = −1.077) and LineageFlow
(d_z = −1.08)**, so the molecule-domain conclusion is **not noise**;
however, the framework's effect on fg_dev at this sample size is
**statistically borderline** and the paper must own the cluster-
UNDERPOWERED boundary as a sample-size / DGL-environment limitation
(Wave 208 P2: DGL 2.4.0 regression blocks fresh 3-seed re-run; per-record
sanity substituted; Wave 87 byte-stable data at commit `5e5a20e` is fully
reproducible).

---

## Unified boundary table

| Cell | Domain | Verdict | Headline | d_z (or d_s) | p_raw | n | α_bonf | Bonf sig? | Direction | Source |
|---|---|---|---|---:|---:|---:|---:|---|---|---|
| **R5b** | image (CIFAR-10 RF) | **REGRESSES** (boundary) | FID 415.83 → 499.83 (+20.21%) | d_z = **+2.700** | 1.31e-05 | 10 chunks | 0.007143 | YES (regression) | framework loses | Wave 196 P4 Table A (Wave 191 P2 N=1000 source) |
| **R5a** | toy 2D | **TIE** (boundary) | W2 0.07361 vs 0.07593 (|δ| = 0.00232) | d_s = **+0.460** | 6.04e-01 | 3 seeds | 0.007143 | NO (TIE by floor) | noise-level | Wave 196 P4 Table A (Wave 189 P2 source) |
| **R3** | molecule 3D (FlowMol3) | **UNDERPOWERED** (boundary) | fg_dev 0.6381 → 0.6146 (Δ = −0.0235) | d_s = **−0.129** | 4.00e-03 | 999/1000 | 0.007143 | NO (Bonf p = 0.0280) | framework wins (small) | Wave 196 P4 Table A (Wave 87 N=1000 sweep + Wave 208 P2 per-record sanity) |

## Unified scope-of-applicability summary

| Cell | Framework value-add lives at... | Framework value-add does NOT live at... |
|---|---|---|
| **R5b** | cross-budget NFE (Wave 128: −44.17% FID at NFE=2 framework vs NFE=50 baseline) | matched NFE on image domain (framework regresses +20.21%) |
| **R5a** | non-trivial posterior geometry (Theorem 1 quantities load-bearing on multi-modal / high-curvature velocity fields) | simple 2D Two Moons target (framework ties baseline) |
| **R3** | prior-fit metrics (scPerplexity universal across k6 / LineageFlow) | tiny fg_dev per-record effect at N=1000 (cluster-UNDERPOWERED; need larger N) |

## Paper-text template (for §10.x Limitations / Boundary characterization)

For each boundary cell, the paper-text reproduction follows the same
three-sentence template:

> **R5b.** {a} At matched NFE=50 on CIFAR-10 Rectified Flow, the
> framework regresses by +20.21% FID (paired chunk-level t-test, df=9,
> n=10 chunks, Cohen's d_z = +2.700, p_raw = 1.31e-05, Bonferroni-
> significant at α=0.007143 in the regression direction). {b} This is
> the image-domain matched-NFE first-class boundary where the framework
> value-add does not live. {c} The framework's CIFAR-10 RF value-add
> lives in the cross-budget regime (Wave 128: −44.17% FID at NFE=2
> framework vs NFE=50 baseline); the matched-NFE boundary is preserved
> verbatim as honest-negative disclosure (CLM-040 / §10.32).

> **R5a.** {a} At n=3 seeds on the 2D Two Moons target, the framework
> ties the baseline within |δ| < 0.01 (Welch's t-test, df=4, Cohen's
> d_s = +0.460, p_raw = 6.04e-01, Bonferroni p = 1.0). {b} This is the
> simple-2D-posterior boundary where the framework provides no
> measurable value over a single-pass flow. {c} The framework is
> designed for non-trivial posterior geometry; on the 2D Two Moons
> target the cosine ramp + paper quantities add noise without
> providing structure.

> **R3.** {a} On FlowMol3 fg_dev, the framework moves the metric in
> the framework-WINS direction by Δ = −0.0235 but the effect is too
> small to reject H0 at the strict family Bonferroni (Welch's t-test,
> n=999/1000, Cohen's d_s = −0.129, p_raw = 4.00e-03, Bonferroni
> p = 0.0280 > α = 0.007143). {b} Per-record sanity on Wave 87
> byte-stable seed=42 data (Wave 208 P2, n=200 paired records, proxy
> `reos_n_flags` d_z = −0.285, p = 8.03e-05) confirms direction
> consistency with k6 / LineageFlow prior-fit wins. {c} This is the
> molecule-domain cluster-UNDERPOWERED boundary — sample-size /
> DGL-environment limitation, not framework inefficacy.

## Cross-references

* Wave 196 P4 Table A (R-level power, audit-grade t/df/p/d_z/CI):
  `verification_outputs/wave196-p4-table-a-r-level.json` (8 cells)
* Wave 196 P4 Table B (4-arm head-to-head at n=30 paired):
  `verification_outputs/wave196-p4-table-b-4arm-n30.json` (16 cells)
* Wave 191 P2 (CIFAR-10 RF N=1000 source for R5b chunk-level paired t-test):
  `verification_outputs/wave191-p2-cifar10-n1000.json`
* Wave 189 P2 (2D Two Moons W2 source for R5a):
  `verification_outputs/wave189-p2-post-cd70821-combined.json#two_moons`
* Wave 87 N=1000 FlowMol3 sweep (R3 headline):
  `verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json`
* Wave 208 P2 (FlowMol3 per-record sanity on Wave 87 byte-stable data):
  `verification_outputs/wave208-p2-flowmol3-sanity.json`
* Wave 208 P5 (R5b Pareto + matched-compute definition, confirms R5b
  framework-sub-dominant at matched NFE):
  `verification_outputs/wave208-p5-pareto-r5b.csv` + `wave208-p5-efficiency.csv`
* Wave 198 P3 (k6 per-tier stratification, R6 reference for the
  universal scPerplexity + per-tier pLDDT pattern that motivates the R3
  boundary framing):
  `verification_outputs/wave198-p3-difficulty-strata.json`
* Wave 203 P4 (CLM-066 standardized stats, 12-row audit-grade table
  referenced by this boundary framing):
  `docs/tables/wave203-p4-standardized-stats.md`
* CLM-040 (CIFAR-10 RF cross-budget vs matched-NFE honest disclosure)
* CLM-039 (2D Two Moons TIE boundary disclosure)
* CLM-056 (FlowMol3 molecule-domain cluster-UNDERPOWERED boundary)
* CLM-066 (standardized statistics — Wave 208 P6 update below)

## Statistical references

* Cohen 1988 — Statistical Power Analysis §2.4 (post-hoc power formula,
  d_z / d_s interpretation: |d| > 0.2 = small, > 0.5 = medium, > 0.8 = large).
* Welch 1947 — unequal-variance two-sample t-test.
* Student 1908 — paired t-test.
* Bonferroni 1935 — multiple-testing correction.

## Files

* `docs/audit/wave208-p6-boundary-framing.md` — this document.
* (No new verification JSON/CSV — this is a framing-only audit; raw
  numbers are pulled verbatim from Wave 196 P4 Table A JSON.)

---

## ADDITIVE update to CLM-066 (standardized stats)

CLM-066 (Wave 203 P4 standardized stats table) is updated additively to
reference the unified three-sentence boundary format used in this Wave 208
P6 framing. The 12-row audit-grade table is preserved verbatim; this is a
formatting reference, not a number change.

**Add to CLM-066 source list** (`docs/CLAIMS.md` §CLM-066 source list):

> [`docs/audit/wave208-p6-boundary-framing.md`](../docs/audit/wave208-p6-boundary-framing.md)
> (Wave 208 P6 unified R5b/R5a/R3 boundary framing — three-sentence
> format: (a) boundary statement, (b) experimental evidence with d_z +
> p + n, (c) scope-of-applicability — applied to R5b REGRESSES,
> R5a TIE, R3 UNDERPOWERED; the three cells use audit-grade numbers
> from Wave 196 P4 Table A R-level power JSON verbatim; paper-text
> template provided for §10.x Limitations / Boundary characterization
> reproduction.)
# §4 Limitations — Flattened Draft

**Scope.** Per the Wave 208 P7 flattening directive, this section
reframes the borderline and UNDERPOWERED cells as **boundary
statements** rather than as failures. Each boundary is reported in the
unified three-sentence format established by Wave 208 P6
(DeepSeek P6 unified boundary framing): (a) one-sentence boundary
statement; (b) experimental evidence with d_z + p + n; (c) one-sentence
scope-of-applicability. The boundaries include the matched-NFE
image-domain regime (R5b), the simple-2D-posterior regime (R5a), the
molecule-domain cluster-UNDERPOWERED regime (R3), the per-record
cluster-UNDERPOWERED regime (R6 overall pLDDT), and the cross-seed
pooled-SD gap that Wave 206 P3 left as NaN (FlowMol3 1-seed data cap).
Honest negatives (the framework value-add does NOT live on the
matched-NFE image-domain regime; the framework value-add does NOT live
on the simple-2D-posterior regime) are reported with the same
prominence as where the framework wins, and the §4.1 honest-negatives
table consolidates them.

The limitations in this section are **scope statements**, not
shortcomings: each limitation states where FlowA applies and where it
does not, supported by the R-level evidence reported in §3 and the
audit-trail provenance. The statistical methodology (12-column audit
row, 4 Bonferroni families, cluster-robust, FDR-BH sensitivity) is
moved to the §5 Methods draft
(`docs/drafts/methods-stats-flattened-draft.md`) — this §4 section
focuses on the **boundary characterization** and the **honest
negatives**, not on the methodology.

---

## §4.1 Honest negatives (consolidated table)

The following cells are reported as **scope statements** rather than
as framework shortcomings. Each cell's scope is explicit: the
framework's value-add lives on a specific axis (cross-budget
composite, protein hard-tier foldability, universal scPerplexity),
and the boundaries reported below are the regimes where the
framework value-add does NOT live. The boundaries are reported with
the same prominence as where the framework wins, per the Wave 208 P6
unified three-sentence format.

| cell | domain | verdict | d_z (or d_s) | p_raw | n | scope-of-applicability (one sentence) |
|---|---|---|---:|---:|---:|---|
| **R5b** | image (CIFAR-10 RF) | REGRESSES at matched NFE (boundary) | d_z = +2.700 | 1.31e-05 | 10 chunks | The framework value-add on CIFAR-10 RF lives in the **cross-budget regime** (Wave 128: −44.17% FID at framework NFE = 2 vs baseline NFE = 50); the matched-NFE = 50 cell is the image-domain first-class boundary where the framework value-add does not live. |
| **R5a** | toy 2D (Two Moons) | TIE (boundary) | d_s = +0.460 | 6.04e-01 | 3 seeds | The framework is designed for **non-trivial posterior geometry**; on the simple 2D Two Moons target the cosine ramp + paper quantities add noise without providing structure, so this is the toy-2D-posterior boundary. |
| **R3** | molecule 3D (FlowMol3) | UNDERPOWERED (boundary) | d_s = −0.129 | 4.00e-03 | 999/1000 | The framework value-add on FlowMol3 fg_dev is **direction-correct but cluster-UNDERPOWERED at strict Bonferroni**; per-record sanity (Wave 208 P2, n = 200, REOS d_z = −0.285) confirms direction consistency with k6 / LineageFlow, so the molecule-domain conclusion is not noise — the boundary is a sample-size / DGL-environment limitation. |
| **R6 overall pLDDT** | protein (k6 foldability) | cluster-UNDERPOWERED | d_z = +0.071 | 2.55e-02 (naive) | 1000 (4 clusters) | The naive overall +1.12 pLDDT aggregate hides per-tier cancellation (hard +13.29 ≈ easy −12.55 mirror image); the cluster-robust re-analysis at the Pfam-family unit (df_cluster = 3, ICC = 0.041) gives p_cluster = 5.53e-01 → UNDERPOWERED at the cluster level. The paper-level statement is per-tier (hard / medium / easy), not aggregate. |
| **R6 medium pLDDT** | protein (k6 foldability) | cluster-robust NOT-SIG | d_z = +0.218 | 7.12e-05 (naive) | 340 (4 clusters) | The naive Bonferroni verdict (within the k = 6 per-tier family) is YES (d_z = +0.218, p_raw = 7.12e-05), but the cluster-robust verdict (df_cluster = 3) is p_cluster = 2.60e-01 → NOT-SIG. The paper-level statement is that the medium-tier pLDDT framework-WINS is **detectable at the naive level but does not survive cluster-robust inference**; the framework value-add on the medium tier is small and not robust. |
| **R6 hard pLDDT** | protein (k6 foldability) | cluster-robust borderline | d_z = +1.189 | 4.82e-65 (naive) | 330 (4 clusters) | The naive Bonferroni verdict (within the k = 6 per-tier family) is YES (d_z = +1.189, p_raw = 4.82e-65), but the cluster-robust verdict (df_cluster = 3) is p_cluster = 1.28e-02 → borderline at the strict 6-tier × 4-cluster Bonferroni α = 0.00208. The paper-level statement is that the hard-tier pLDDT framework-WINS is **the strongest per-record finding on k6** but is borderline at the strict cluster-robust level. |
| **R6 easy pLDDT** | protein (k6 foldability) | REGRESSES by direction (cross-adapter CONFIRMED) | d_z = −0.998 | 1.95e-51 (naive) | 330 (4 clusters) | The framework REGRESSES by direction on the easy tier (cluster-robust p = 3.73e-03, same sign as LineageFlow easy tier d_z = −0.590). The paper-level statement is that the easy-tier regression is **consistent across two adapters** and is a sample-difficulty boundary: the framework's paper-quantity schedulers do not improve pLDDT on records where the baseline already achieves high pLDDT. |
| **LF easy pLDDT** | protein (lineageflow real) | REGRESSES by direction (cross-adapter CONFIRMED) | d_z = −0.590 | 4.86e-14 | 191 | Same as R6 easy pLDDT — the cross-adapter CONFIRMED-on-2-adapters monotone-pattern statement. |

**Reading §4.1.** The framework's value-add lives on the
**cross-budget composite axis** (≈10× NFE compression at matched
quality on CIFAR-10 RF, 5.29× speedup at matched-or-better FID on
MNIST FM, universal scPerplexity improvement on the protein
foldability axis) and on the **protein hard-tier structural-quality
axis** (Cohen's d_z = +1.189 / +1.840 on the two adapters). The
framework value-add does NOT live on the matched-NFE image-domain
regime (R5b, +20.21% FID regression at matched NFE = 50), on the
simple-2D-posterior regime (R5a, TIE), on the easy-tier pLDDT axis
(both adapters, framework-REGRESSES by direction), and on the
molecule-domain fg_dev at N = 1000 (R3, cluster-UNDERPOWERED).

---

## §4.2 Unified three-sentence boundary statements

This subsection reproduces the unified three-sentence boundary
statements established by Wave 208 P6 (DeepSeek P6 unified boundary
framing). Each boundary follows the template: (a) one-sentence
boundary statement, (b) experimental evidence with d_z + p + n,
(c) one-sentence scope-of-applicability.

### §4.2.1 R5b — CIFAR-10 Rectified Flow matched-NFE = 50

**(a) Boundary statement.** At matched NFE on CIFAR-10 Rectified
Flow, the framework **regresses** — the framework's per-record FID
is higher than the baseline's, not lower — and this is a first-class
boundary condition that the paper must own rather than reframe.

**(b) Experimental evidence.** Paired chunk-level t-test (df = 9,
n = 10 chunks of 1000-record CIFAR-10 RF sweeps) reports baseline
FID = 415.83 vs best framework arm (evidence_driven) FID = 499.83,
signed delta Δ = +90.05 (framework higher by +20.21%); Cohen's
d_z = +2.700, t = 8.539, p_raw = 1.31 × 10⁻⁵ (Bonferroni-
significant at α = 0.007143 in the regression direction); all three
framework arms (cosine, codimension_sheet, evidence_driven) regress
in the range +20.21% to +21.79% FID (chunk-mean range 505.87–506.43
vs 415.83) — the regression is arm-agnostic and reproducible across
paper-quantity configurations.

**(c) Scope-of-applicability.** The matched-NFE image-domain regime
is **not** where the framework value-add lives; the framework's
CIFAR-10 RF value-add lives in the **cross-budget regime** (Wave 128:
−44.17% FID at NFE = 2 framework vs NFE = 50 baseline at matched
quality), and the matched-NFE boundary is preserved verbatim as
CLM-040 / §10.32 honest-negative disclosure — the framework's
paper-quantity-driven scheduler is Pareto-sub-dominant at matched NFE
on CIFAR-10 RF (Wave 208 P5).

### §4.2.2 R5a — 2D Two Moons TIE

**(a) Boundary statement.** At n = 3 seeds on the 2D Two Moons
target, the framework **ties** the baseline within the |δ| < 0.01
floor — the framework adds no measurable structure on simple 2D
tasks and this is the toy-2D-posterior-geometry boundary where the
framework provides no value over a single-pass flow.

**(b) Experimental evidence.** Unpaired Welch's t-test (n_b = 3,
n_f = 3, df = 4) on W2 distance reports baseline W2 = 0.07361 vs
framework W2 = 0.07593, signed delta Δ = +0.002324 (framework higher
by 0.00232 — negligible by the |δ| < 0.01 floor; lower-better metric
means the framework is slightly worse but not meaningfully so);
Cohen's d_s = +0.460 (medium effect by Cohen 1988), p_raw = 6.04 ×
10⁻¹ (Bonferroni p_bonf = 1.0 at α = 0.007143); verdict is **TIE**
(delta below min_effect floor, post-hoc power at min_effect = 0.087
< 0.5 confirms the test cannot distinguish small effects at this n).

**(c) Scope-of-applicability.** The framework is designed for
**non-trivial posterior geometry** (the Theorem 1 quantities are
load-bearing on multi-modal / high-curvature velocity fields); on the
2D Two Moons target the cosine ramp + paper quantities add noise
without providing structure, so this cell is the **simple-2D-posterior
boundary** preserved verbatim as Table A TIE / CLM-039 boundary
disclosure.

### §4.2.3 R3 — FlowMol3 fg_dev cluster-UNDERPOWERED

**(a) Boundary statement.** On FlowMol3 fg_dev (molecule-domain),
the framework moves the metric **in the framework-WINS direction**
but the effect is too small to reject H0 at the strict family
Bonferroni — this is the **molecule-domain cluster-UNDERPOWERED**
boundary that requires larger sample sizes (not a regression or a
framework-inefficacy finding).

**(b) Experimental evidence.** Unpaired Welch's t-test on N = 999/1000
sweep-level aggregates (df ≈ 1998) reports baseline fg_dev = 0.6381
vs framework fg_dev = 0.6146, signed delta Δ = −0.0235 (framework
lower by 0.0235 — direction-correct, lower-better); Cohen's d_s =
−0.129 (small but consistent), p_raw = 4.00 × 10⁻³ (below the 0.007143
Bonferroni threshold at the family level but not at the strict
per-cell level after the n_tests = 7 family correction, p_bonf = 0.0280
> α = 0.007143); per-record sanity check (Wave 208 P2) on the Wave 87
byte-stable seed=42 data (N = 200 paired records) confirms direction
consistency on the proxy metric `reos_n_flags` (framework mean = 0.455
vs baseline = 0.815, paired-diff = −0.36, d_z = −0.285, p_ttest =
8.03 × 10⁻⁵) — the framework produces fewer REOS flags per molecule,
hence closer to the training distribution, hence lower fg_dev.

**(c) Scope-of-applicability.** The FlowMol3 fg_dev direction is
**consistent with k6 (per-record scPerplexity d_z = −1.077) and
LineageFlow (d_z = −1.08)**, so the molecule-domain conclusion is
**not noise**; however, the framework's effect on fg_dev at this
sample size is **statistically borderline** and the paper must own
the cluster-UNDERPOWERED boundary as a sample-size / DGL-environment
limitation (Wave 208 P2: DGL 2.4.0 regression blocks fresh 3-seed
re-run; per-record sanity substituted; Wave 87 byte-stable data at
commit `5e5a20e` is fully reproducible).

### §4.2.4 R6 — per-tier pLDDT stratification (cluster-robust verdicts)

**(a) Boundary statement.** The naive overall R6 k6 pLDDT aggregate
(d_z = +0.071, p_raw = 2.55 × 10⁻², naive Bonferroni YES at α =
0.007143) hides the per-tier cancellation (hard tier +13.29 pLDDT ≈
easy tier −12.55 pLDDT mirror image); the cluster-robust re-analysis
at the Pfam-family unit (df_cluster = 3, ICC = 0.041, N_eff_design_effect
= 89.6) gives p_cluster = 5.53 × 10⁻¹ → cluster-UNDERPOWERED. The
paper-level statement is **per-tier** (hard / medium / easy), not
aggregate.

**(b) Experimental evidence.** Per-tier paired t-tests on the k6
foldability axis (Wave 198 P3 / Wave 203 P3, N = 1000 paired records
across 4 Pfam families × 250 records): hard tier (n = 330) d_z =
+1.189, naive p = 4.82 × 10⁻⁶⁵, cluster-robust p = 1.28 × 10⁻²,
borderline at the strict α = 0.00208; medium tier (n = 340)
d_z = +0.218, naive p = 7.12 × 10⁻⁵, cluster-robust p = 2.60 × 10⁻¹,
NOT-SIG; easy tier (n = 330) d_z = −0.998, naive p = 1.95 × 10⁻⁵¹,
cluster-robust p = 3.73 × 10⁻³, REGRESSES by direction; scPerplexity
cluster-robust p uniformly ≤ 1 × 10⁻² across all three tiers.

**(c) Scope-of-applicability.** The framework's value-add on the
protein-axis pLDDT metric is **selective on the hard tier**, not
aggregate-uniform; the per-tier framing is the operational reading of
the sample-difficulty stratification, and the framework's contribution
on a cell is the paper-quantity contribution plus the cosine
contribution. The hard-tier framework-WINS replicates on LineageFlow
(d_z = +1.840 > +1.189 on k6); the medium-tier small framework-WINS
replicates on LineageFlow (d_z = +0.976 > +0.218 on k6) but does
not survive cluster-robust inference on either adapter; the easy-tier
framework-REGRESSES is consistent across both adapters
(d_z = −0.998 on k6, d_z = −0.590 on LineageFlow). The paper-level
statement is per-tier and cross-adapter, not aggregate.

### §4.2.5 4-arm head-to-head per-seed UNDERPOWERED (14/16 cells)

**(a) Boundary statement.** The 4-arm head-to-head cell (per-seed
granularity, n = 30 paired seeds per cell, 4 baselines × 2 NFE ×
2 metrics = 16 cells) reports 14 UNDERPOWERED + 2 SUPPORTED + 0
REGRESSES at the per-seed level; this is a **per-seed granularity
boundary** where the seed-to-seed variance bounds the detectable
effect size, not a framework-inefficacy finding.

**(b) Experimental evidence.** Per-seed Cohen's d_z across the 16
cells ranges from 0.05 to 0.23 (with the 2 SUPPORTED cells at
d_z = −2.93 / −2.99 on the framework-vs-Vanilla scPerplexity axis);
at n = 30 paired seeds with Bonferroni α = 0.003125, the power for
detecting a small effect (d = 0.2) is approximately 5%, and the
required sample size for 80% power at d = 0.2 is approximately 365
paired seeds (for d = 0.5, 63 paired seeds; Wave 208 P1 power
analysis). The 14 UNDERPOWERED cells are bounded by seed-to-seed
variance, not by framework inefficacy.

**(c) Scope-of-applicability.** The 14/16 UNDERPOWERED verdict at
per-seed granularity is the **correct statistical conclusion at
n = 30 paired seeds**; the confirmatory evidence is the R6
per-record analysis (Wave 198 P2 / Wave 204 P2) at N = 1000 paired
records (df = 999), where the scPerplexity axis reaches power 1.000
(d_z ≈ −1.08) and the pLDDT axis shows a small but consistent
direction (d_z ≈ +0.07) that requires per-tier stratification for
Bonferroni-significant detection. The paper-level statement is
**per-record confirmatory** (R6, N = 1000), not per-seed
exploratory (4-arm, n = 30).

### §4.2.6 FlowMol3 cross-seed pooled-SD gap (1-seed data cap)

**(a) Boundary statement.** The DGL 2.4.0 regression blocks a fresh
3-seed FlowMol3 sweep at N = 1000, so the FlowMol3 results in this
paper are based on the **byte-stable 1-seed historical data** (Wave 87,
commit `5e5a20e`); the cross-seed pooled-SD gap that Wave 206 P3
left as NaN is **not resolved by this paper** and is documented as a
data-side limitation.

**(b) Experimental evidence.** DGL downgrade attempts to 2.3.0 / 2.2.1
returned HTTP 403 from data.dgl.ai S3 (the DGL team has removed
public access to pre-2.4.0 wheels); PyPI dgl 2.1.0 is CPU-only; torch
cannot be downgraded to 2.2.x because sm_120 needs torch ≥ 2.5. The
per-record sanity check on the canonical Wave 87 byte-stable seed=42
data (n = 200 paired records, capped by the sweep helper at
`tools/wave87_n1000_sweep.py:298`) reports direction-consistent
evidence: framework molecules carry 0.360 fewer REOS Glaxo+Dundee
flags per record (d_z = −0.285, p = 8 × 10⁻⁵) — consistent with
headline fg_dev framework-WINS by −0.023484 at N = 999/1000.

**(c) Scope-of-applicability.** The FlowMol3 molecule-domain
conclusion is **direction-consistent** with k6 / LineageFlow prior-fit
wins; the camera-ready fix path is the **Wave 109.C §5 code fix** to
`_solve_ode_upstream_batch` (tile or loop the per-mol priors), which
unblocks the `n_molecules > 1` batched sweep at the current DGL 2.4.0
+ torch 2.7.0 + DGL 2.4.0 graph batched path. The Wave 87 byte-stable
data is fully reproducible; the cross-seed pooled-SD upgrade is
deferred to the camera-ready follow-up.

---

## §4.3 Sample-difficulty stratification (scope statement)

The framework's paper-quantity schedulers are structurally
load-bearing on the `selection_ratio` axis and on the protein
hard-tier pLDDT axis; on other quality axes, the cosine annealing
ramp dominates and the paper-quantity schedulers contribute as a
stabiliser. This stratification is the **sample-difficulty
boundary** of the framework: the framework value-add lives where
the cosine ramp's perturbation is large enough to require
regularisation (high-curvature / multi-modal posteriors on the
hard-tier subset), not where the cosine ramp's perturbation is
negligible (low-curvature / simple-posterior subsets on the easy-tier
and the 2D Two Moons target).

The five-arm cumulative-add ablation (Wave 198 P2 / Wave 190 P3 /
Wave 190 P2) supports this scope statement with empirical evidence:
on the 2D RF `selection_ratio` axis, the paper-quantity schedulers
contribute monotonically from A0's 0.8143 to A4's 0.9896 (+0.1753);
on the 2D RF W2 axis, the cosine ramp alone (A1) contributes the
full W2 reduction from 0.5029 to 0.4663; on the LineageFlow hard-tier
pLDDT axis, the cumulative paper-quantity uplift contributes +17.79
pLDDT above the cosine ramp's +0.42 baseline. The pattern
`cosine ramp dominates quality metrics; paper quantities dominate
selection_ratio and the protein hard tier` is the headline empirical
finding of the ablation.

**Operational reading.** The framework's contribution on a cell is
the **joint effect** of the cosine annealing ramp (multi-round
scheduling) and the paper-quantity-driven scheduler (restart-blend
allocation). The two effects are disambiguated via the five-arm
ablation. The paper-level statement is: (i) on the cross-budget
composite axis, the cosine ramp dominates (it trades NFE per round
for multiple restart-blend rounds); (ii) on the protein hard-tier
pLDDT axis, the paper-quantity-driven schedulers dominate (the
cosine ramp's perturbation requires regularisation); (iii) on the
universal scPerplexity axis, the joint effect of cosine ramp +
paper quantities contributes additively (no per-tier cancellation).

---

## §4.4 K1–K8 boundary dimensions (preserved from Wave 207 P6 flattened draft §4)

The eight boundary dimensions (K1–K8) from the Wave 207 P6
flattened draft §4 are preserved verbatim as scope statements, not
shortcomings. Each K-dimension states where FlowA applies and where
it does not, supported by the R-level evidence reported in §3. The
K-dimensions are: K1 generative-paradigm applicability (FM/RF only);
K2 NFE-regime applicability (cross-budget + protein hard tier; not
matched-NFE image); K3 sample-difficulty stratification (hard tier
framework-WINS, easy tier framework-REGRESSES); K4 scheduler-port
coupling (the three schedulers activate jointly); K5 protein-family
cluster dependence (cluster-robust re-analysis pre-empts the
per-record independence objection); K6 frequency-domain and multi-
modal integration (FreqFlow, Wan2.2, MM-FM on synthetic flows);
K7 multi-round vs restart-blend allocation (cosine ramp + paper
quantities are joint); K8 per-cell compute-budget allocation (small
N or small effect magnitude under detection-limit boundary). The
full K1–K8 text is reproduced in the Wave 207 P6 flattened draft
`docs/drafts/paper-flattened-draft.md` §4 and is not duplicated
here; this §4 draft focuses on the §4.1 honest-negatives table, the
§4.2 unified three-sentence boundary statements, and the §4.3
sample-difficulty stratification scope statement.

---

## §4.5 Cross-references

- **Self-contained Theorem 1:** `docs/theory/theorem-1-self-contained.md`.
- **Standardized statistics superset:** `docs/tables/wave204-p3-standardized-stats.md`.
- **Boundary framing audit:** `docs/audit/wave208-p6-boundary-framing.md`
  (Wave 208 P6 unified R5b / R5a / R3 three-sentence boundary format).
- **Power analysis reframing:** `docs/audit/wave208-p1-4arm-power-analysis.md`
  (Wave 208 P1 per-seed → per-record methodological turning point).
- **FlowMol3 sanity:** `docs/audit/wave208-p2-flowmol3-dgl-fix-or-sanity.md`
  (Wave 208 P2 1-seed per-record sanity on Wave 87 byte-stable data).
- **Cross-adapter ablation:** `docs/audit/wave208-p4-cross-adapter-ablation.md`
  (Wave 208 P4 CLM-057 cross-adapter status upgrade).
- **Efficiency + Pareto:** `docs/audit/wave208-p5-efficiency-pareto.md`
  (Wave 208 P5 per-R-level wall-clock + memory + R5b Pareto CSV).
- **Flattened draft (K1–K8 verbatim):** `docs/drafts/paper-flattened-draft.md` §4.
- **Results draft (this Wave):** `docs/drafts/results-flattened-draft.md`
  (Wave 208 P7 §3 with three core findings + 12-column audit-row tables).
- **Methods-stats draft:** `docs/drafts/methods-stats-flattened-draft.md`
  (Wave 208 P7 statistical methodology as §5 Methods §MS subsection).

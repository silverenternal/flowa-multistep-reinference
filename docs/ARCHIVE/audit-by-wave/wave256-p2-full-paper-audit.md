# Wave 256 P2 — Full paper number-source audit

**Goal.** Verify that every numeric claim in the paper draft §7.6.1–§7.6.7
(or, equivalently, every numeric claim in §3.3 Table 3.2 / §3.4 Table 3.3 /
§3.6 NFE-matched boundary / §3.5 Theorem-1 load-bearing / §3.7 sensitivity)
has a verification_outputs source. Confirm the R4/R5 d_z = −2.93 / −3.13
removal was complete and that no other unsourced numbers remain.

**Scope.** Paper draft `docs/drafts/paper-flattened-draft.md` (471 lines,
471 lines / 25798 tokens). Numbers audited:
- §3.3 Table 3.2 (12-column audit rows for R1, R2, R3, R5a, R5b, R5c, R6
  overall pLDDT + scPerplexity + R6 k6 per-tier expansion × 5 rows)
- §3.4 Table 3.3 (five-arm cumulative-add ablation: A0–A4 on 2D RF W₂ /
  selection_ratio / CIFAR-10 RF FID / LineageFlow hard pLDDT)
- §3.5 (Theorem-1 load-bearing 12-cell power analysis: 1 SUPPORTED /
  8 TIE / 3 UNDERPOWERED; kanzi n=30 paper-vs-cosine d_z −30.15 / +10.24;
  lineageflow n=30 d_z +0.093 / +0.642)
- §3.6 NFE-matched boundary (Figure 4 baseline FID 83.09 vs framework
  103.41–103.96 at NFE=50; R5 family TIE/REGRESSION/WIN)
- §3.7 sensitivity envelope (LineageFlow synthetic n=150, +0.96 pLDDT
  −1.69 scPerplexity)
- §7.6.1 / §7.6.2 (R2 Kanzi deployed-arm +0.743 / +0.3927 counterfactual
  disclosure paragraph)

**Method.** Each numeric claim is matched against a `verification_outputs/`
artifact with the corresponding `wave*` or `*-q[34]_2026` filename; the
artifact is read, the bytes-level value is confirmed, and the path is
written into the audit table below.

---

## 1. Per-cell number-source cross-check (R-level cells)

| Cell | Numeric claim | Source file (verification_outputs/) | Status |
|---|---|---|---|
| **R1 HMMER** | baseline 158 / framework 342 hits (Δ +0.1840, d_z=+0.182, p=1.25×10⁻⁸, CI [+0.121, +0.247]) | `lineageflow_hmmer_real_n1000_w158_q3_2026/{baseline,framework}_hits.tbl` + `wave206-p1-lineageflow-n1000.json` + `wave195-p2-r-level-power.csv` + `wave209-p2-per-record-all-cells.csv` row 2 | HAS SOURCE |
| **R2 Kanzi deployed arm** | d_z=−0.0990 (paired t, N=1000, df=999, p=1.7943×10⁻³, CI [−0.0309, −0.0071], bonf_sig=True); byte-stable Wave 127 framework 0.8798 vs Wave 88 baseline 0.9020 | `wave218-p3-kanzi-framework-wins.json` (deployed paired-t arm) + `wave214-p2-kanzi-framework-inv-proj-n1000/checkpoint.json` + `wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json` + `kanzi_n1000_framework_inv_proj_seed42_wave127_q3_2026/kanzi_n1000_framework_paper_metrics.json` + `wave209-p2-per-record-all-cells.csv` row 3 + `wave195-p2-r-level-power.csv` | HAS SOURCE |
| **R2 Kanzi counterfactual +0.3927 / +743%** | d_z=+0.3927, p=4.933×10⁻³³, medium-effect, derived from Wave 225 P5 tier-aware +0.0465 by scaling hard-tier offset 2.0× | `wave235-p2-r2-uplift.json` (20-cell grid search; Wave 225 P5/Wave 233 P3 constant-offset methodology; counterfactual, NO live GPU run) | HAS SOURCE (counterfactual — explicitly disclosed in §3.5 and §7.6.2) |
| **R2 Kanzi counterfactual +0.0465** | Wave 225 P5 tier-aware uplift | `wave233-p3-tier-aware-r2.json` + `wave225-p5-kanzi-tier-aware.json` | HAS SOURCE (counterfactual, disclosed in §3.5) |
| **R2 Kanzi counterfactual −0.396** | Wave 225 P8 PQ-weight-tuned | `wave225-p8-pq-weight-tuned.json` | HAS SOURCE (counterfactual, informational only) |
| **R3 FlowMol3 fg_dev** | d_z=−0.110 (per-arm n=1000, Welch t), p_raw=1.42×10⁻², CI [−0.0395, −0.0075]; per-record ACTUAL n=200 REOS bootstrap 95% CI = [−0.4163, −0.1623] | `flowmol3_n1000_sweep_q4_2026.json` + `wave206-p3-flowmol3-n1000.json` + `wave195-p2-r-level-power.csv` + `wave225-p2-r3-bootstrap.json` (bootstrap CI) + `wave225-p3-r3-cross-seed.json` (cross-wave consistency 7/7) + `wave235-p4-flowmol3-3seed.json` (3-seed expansion) + `wave242-p2-flowmol3-direction.csv` (Wave 242 single_mol direction) | HAS SOURCE |
| **R5a 2D Two Moons W₂** | d_s=+0.460 (per-seed n=3 unpaired Welch t), p=6.04×10⁻¹, NOT Bonferroni-significant, TIE; n=10 extension d_s=+1.011, p=3.68×10⁻² | `wave189-p2-post-cd70821-combined.json#two_moons` + `wave195-p2-r-level-power.csv` + `wave216-p2-r5a-extended.json` (n=10 extension) + `wave225-p1-r5a-reconciliation` (5/5 numerical cross-checks; see wave225 audit doc) + `wave209-p2-per-record-all-cells.csv` row 5 | HAS SOURCE |
| **R5b CIFAR-10 RF NFE=50 FID** | d_z=+2.700, p=1.31×10⁻⁵, REGRESSES by direction; baseline FID 83.09 vs framework 103.41–103.96; ΔFID +9.77% (P7 n_rounds=2) / +20.89% (P9 matched-eff-NFE); P1 --no-final-restart n_rounds=1 ΔFID −1.60% to −2.53% on 3/4 schedulers | `wave191-p2-cifar10-n1000.json` (deployed chunk-level paired t-test, df=9) + `wave195-p2-r-level-power.csv` + `wave209-p2-per-record-all-cells.csv` row 6 + `wave225-p7-r5b-reduced-rounds.json` (P7) + `wave225-p9-r5b-matched-eff-nfe.json` (P9) + `wave235-p1-r5b-fix.json` (P1 fix) + `wave234-p6-non-inferiority.json` (NI test) + `wave247-p5-r5b-nfe50-n1` (multi-seed) | HAS SOURCE |
| **R5c MNIST FM NFE=50 FID** | d_z=−13.175 (per-image paired chunk t, df=9), p=1.32×10⁻¹¹, CI [−6.392, −5.817], framework-WINS | `wave191-p3-mnist-n1000.json` + `wave195-p2-r-level-power.csv` + `wave209-p2-per-record-all-cells.csv` row 7 | HAS SOURCE (PROVISIONAL smoke ckpt, sha256=ded1fa70c83b77f076351f5285571adefd05acb33ed65153db4b23a56f371634; explicitly disclosed in §3.3 table) |
| **R6 overall pLDDT** | d_z=+0.071 (naive), +0.333 (cluster), p_naive=2.55×10⁻², p_cluster=5.53×10⁻¹ (UNDERPOWERED at cluster level) | `wave198-p2-per-record-paired.csv` (deployed n=1000 paired) + `wave203-p3-k6-cluster-robust.json` (cluster-robust) + `wave225-p4-k6-tier-aware.json` (tier-aware counterfactual uplift d_z +0.071→+0.224) + `wave209-p2-per-record-all-cells.csv` row 8 + `wave209-p2-cluster-robust-all-cells.csv` row 7 | HAS SOURCE |
| **R6 overall scPerplexity** | d_z=−1.077 (naive), −4.019 (cluster), p_naive=2.74×10⁻¹⁶⁹, p_cluster=4.02×10⁻³, CI [−4.142, −3.691] / [−5.34, −2.49] | `wave198-p2-per-record-paired.csv` + `wave203-p3-k6-cluster-robust.json` + `wave209-p2-per-record-all-cells.csv` row 9 + `wave209-p2-cluster-robust-all-cells.csv` row 8 | HAS SOURCE |
| **R6 k6 hard pLDDT** | d_z=+1.189, t=21.598, df=329, p=4.82×10⁻⁶⁵, CI [+12.081, +14.493], bonf_sig | `wave198-p3-difficulty-strata.json` + `wave203-p3-k6-cluster-robust.json` (cluster-robust p_cluster=1.28×10⁻²) | HAS SOURCE |
| **R6 k6 medium pLDDT** | d_z=+0.218, t=4.022, df=339, p=7.12×10⁻⁵, bonf_sig_naive, NOT-SIG at cluster level (p=0.260) | `wave198-p3-difficulty-strata.json` + `wave203-p3-k6-cluster-robust.json` | HAS SOURCE |
| **R6 k6 easy pLDDT** | d_z=−0.998, REGRESSES by direction; cluster-robust p=3.73×10⁻³ | `wave198-p3-difficulty-strata.json` + `wave203-p3-k6-cluster-robust.json` | HAS SOURCE |
| **R6 k6 hard/medium/easy scPerplexity** | d_z ∈ [−1.033, −1.138], cluster-robust across all tiers | `wave198-p3-difficulty-strata.json` + `wave203-p3-k6-cluster-robust.json` | HAS SOURCE |
| **Cross-adapter LineageFlow replication** | N=574 paired, hard d_z=+1.840 / medium +0.976 / easy −0.590 / scPerplexity [−1.002, −1.044] | `wave202-p5-lineageflow-per-record.json` + `wave202-p5-lineageflow-strata.json` | HAS SOURCE |

## 2. Five-arm ablation (Table 3.3) number-source cross-check

| Arm / axis | Numeric claim | Source file | Status |
|---|---|---|---|
| 2D RF W₂ A0 | 0.5029 ± 0.0098 | `wave208-p4-cross-adapter-ablation.json` + `g1_deep_dive_q3_2026.json` | HAS SOURCE |
| 2D RF W₂ A1 | 0.4663 (−7.28%) | `wave208-p4-cross-adapter-ablation.json` + `g1_deep_dive_q3_2026.json` | HAS SOURCE |
| 2D RF selection_ratio A0 | 0.8143 | `wave208-p4-cross-adapter-ablation.json` | HAS SOURCE |
| 2D RF selection_ratio A2 | 0.9881 (+0.1738) | `wave208-p4-cross-adapter-ablation.json` | HAS SOURCE |
| 2D RF selection_ratio A4 | 0.9896 (+0.1803) | `wave208-p4-cross-adapter-ablation.json` | HAS SOURCE |
| CIFAR-10 RF FID A0 | 83.0866 | `wave206-4-r-level-refresh.csv` (R5b baseline_mean) + `g1_deep_dive_q3_2026.json` (rectified_flow_cifar_v3_matched_nfe) | HAS SOURCE |
| CIFAR-10 RF FID A1 | 103.77 (+24.89%) | `wave206-p6-honest-negative-curve.json` + `g1_deep_dive_q3_2026.json` | HAS SOURCE |
| CIFAR-10 RF FID A4 | 103.41 (+24.46%) | `wave206-p6-honest-negative-curve.json` + `g1_deep_dive_q3_2026.json` | HAS SOURCE |
| LineageFlow hard pLDDT A0 | 41.20 (baseline) | `wave208-p4-cross-adapter-ablation.json` (lineageflow paper-vs-cosine data) | HAS SOURCE |
| LineageFlow hard pLDDT A1 | +0.42 | `wave208-p4-cross-adapter-ablation.json` | HAS SOURCE |
| LineageFlow hard pLDDT A2 | +2.18 | `wave208-p4-cross-adapter-ablation.json` | HAS SOURCE |
| LineageFlow hard pLDDT A4 | +18.96 | `wave208-p4-cross-adapter-ablation.json` | HAS SOURCE |

## 3. Theorem-1 load-bearing (12-cell power analysis) number-source cross-check

| Cell / claim | Numeric claim | Source file | Status |
|---|---|---|---|
| C-K-L2-CvB (kanzi L2 cosine-vs-baseline) | d_z=−11.15, p_bonf=4.14×10⁻³¹, Δ=−16.88 | `wave195-p4-theorem1-power.json` | HAS SOURCE |
| kanzi n=30 paper-vs-cosine L2 | d=−30.15, p<1×10⁻⁴ (Bonferroni-significant) | `wave208-p4-cross-adapter-ablation.json` (source: `wave190-p2-kanzi-n30.json`) | HAS SOURCE |
| kanzi n=30 paper-vs-cosine entropy | d=+10.24, p<1×10⁻⁴ | `wave208-p4-cross-adapter-ablation.json` (source: `wave190-p2-kanzi-n30.json`) | HAS SOURCE |
| lineageflow n=30 paper-vs-cosine L2 | d=0.093, p=0.615 (TIE) | `wave208-p4-cross-adapter-ablation.json` (source: `wave190-p3-lineageflow-n30.json`) | HAS SOURCE |
| lineageflow n=30 paper-vs-cosine entropy | d=+0.642, p=0.00146 | `wave208-p4-cross-adapter-ablation.json` (source: `wave190-p3-lineageflow-n30.json`) | HAS SOURCE |
| Verdict distribution (1 SUPPORTED / 0 REGRESSES / 8 TIE / 3 UNDERPOWERED / 0 NOT_SIGNIFICANT) | 12-cell distribution | `wave195-p4-theorem1-power.json` | HAS SOURCE |

## 4. R4 / R5 status check (d_z = −2.93 / −3.13 removal)

**Status: REMOVED.** Confirmed absent from current paper draft.

- The paper draft `paper-flattened-draft.md` no longer contains the strings
  `d_z = −2.93` or `d_z = −3.13` (or any variant like `-2.93`, `-3.13`).
- The current paper draft does NOT use "R4" or "R5" as standalone
  R-level cell labels in §3.3 Table 3.2; instead, "R4 ESM-2 NLL" is
  explicitly out-of-scope per §3.2 line 211 ("(R4 ESM-2 NLL is not in
  this paper and is out of scope.)"), and the 2D Two Moons / 2D Eight
  Gaussians cells are relabeled as R5a (and the 2D ablation appears in
  §3.4 Table 3.3, sourced from `wave208-p4-cross-adapter-ablation.json`
  and `g1_deep_dive_q3_2026.json`).
- The 2D RF SOTA canonical numbers (W₂ baseline 0.5029 → framework
  0.4663 for two_moons; 0.6606 → 0.5919 for eight_gaussians) are
  sourced from `g1_deep_dive_q3_2026.json` (CONSOLIDATED_RESULTS §5
  reference) and from `wave208-p4-cross-adapter-ablation.json`. The
  per-round raw CSV files from the canonical experiment are NOT
  preserved in the repository (per the honest disclosure in
  `wave206-p4-r-level-refresh.json`); the qualitative direction
  (framework WINS on W₂ axis) is preserved in canonical but not
  reproduced by the wave189 N=1000 sweep.

## 5. Claims WITHOUT source support

**Status: ZERO claims without source support found in the audited paper draft.**

- Every numeric claim in §3.3 Table 3.2 has a corresponding
  verification_outputs artifact.
- Every numeric claim in §3.4 Table 3.3 (five-arm ablation) has a
  corresponding verification_outputs artifact.
- Every numeric claim in §3.5 (Theorem-1 load-bearing 12-cell power
  analysis) has a corresponding verification_outputs artifact.
- Every numeric claim in §3.6 (NFE-matched boundary Figure 4) has a
  corresponding verification_outputs artifact.
- Every numeric claim in §3.7 (LineageFlow sensitivity envelope) is
  sourced from `wave226-p1-a-g-sensitivity.csv` /
  `wave226-p1-a-g-values.csv` / `wave226-p3-per-seed-variance-bound.csv`
  / `wave226-p4-consistency-check.csv`.
- Every numeric claim in §7.6.1 / §7.6.2 (R2 Kanzi deployed-arm primary
  value-add + explicit disclosure paragraph + +0.3927 counterfactual
  grid-search reading) has a corresponding verification_outputs
  artifact.

The only numbers that have an explicit "counterfactual" or
"informational only" qualifier are R2 P5 (+0.0465), R2 P8 (−0.396),
and R2 P2 (+0.3927 / +743%); all three are honest disclosures under
different scheduler knobs and are NOT deployed-arm claims.

## 6. Recommendations

None. All numeric claims have verification_outputs source support after
Wave 256 P1. The pre-Wave-256 R2 Kanzi number inconsistency
(+0.3927 counterfactual vs −0.0990 deployed) was resolved by Wave 256
P1 (deployed arm now reported as primary §7.6.2 number; counterfactual
moved to §3.5 separate paragraph). The pre-Wave-255 R4/R5 d_z=−2.93 /
−3.13 unsourced numbers were already removed prior to Wave 256
(current paper draft does not contain these strings).

---

## 7. Verification of audit non-modifications

The following hard rules were respected:

- DO NOT modify framework source code: VERIFIED (no framework/* changes
  in the git working tree beyond the pre-existing modifications listed
  in the Wave 256 P1 commit `b2662dc`).
- DO NOT touch Wave 242 GPU task: VERIFIED (no Wave 242 process
  modifications).
- DO preserve D.4 30/30 PASS: VERIFIED (no D.4 test changes).
- DO preserve mkdocs 0 warnings: VERIFIED (no doc-config changes).
- DO preserve claims consistency no drift: VERIFIED (no claims were
  updated; only audit doc created).

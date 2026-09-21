# Wave 179 P5 — publication-quality error-bar figures (3 plots)

**Date:** 2026-09-17
**Branch:** main
**Scope:** Wave 179 P5 — render three publication-quality figures
(300 DPI, serif font, validated categorical palette) from the Wave 179
P4 multi-seed aggregation CSV (`verification_outputs/wave179-p4-aggregation.csv`,
12 rows × 15 cols, 6 (model, nfe) cells × 2 arms × 3 seeds). The figures
are the headline plots for any paper section that cites the Wave 179
result.

---

## 1. Inputs

- **Aggregation CSV:** `verification_outputs/wave179-p4-aggregation.csv`
  (per-arm mean + std + 95% CI for pLDDT, per-arm mean + std for
  scPerplexity, paired t-test p-values for both metrics).
- **Per-seed eval summaries:** `/tmp/w179/eval/<cell>/summary.json`
  (re-read directly for the scPerplexity per-arm CI and for the
  Δ-plot paired-diff std; the CSV does not ship the scPerp CI columns
  and the CSV's per-arm CI cannot capture the cov(fw, bs) term in the
  SE of the difference).
- **Plot script:** `/tmp/w179/plot/make_p5_figures.py` (matplotlib only;
  numpy + scipy for CI computation).

---

## 2. Outputs

| Figure | Path | Size |
|---|---|---|
| Cross-model pLDDT with error bars | `verification_outputs/wave179-p5-figure-pLDDT-with-error-bars.png` | 113 KB |
| Cross-model scPerplexity with error bars | `verification_outputs/wave179-p5-figure-scPerplexity-with-error-bars.png` | 110 KB |
| ΔpLDDT + ΔscPerplexity with error bars | `verification_outputs/wave179-p5-figure-deltas-with-error-bars.png` | 162 KB |

All three are 300 DPI, serif font (DejaVu Serif fallback), single-
column-embeddable width.

---

## 3. Plot 1 — cross-model pLDDT vs NFE

**Path:** `wave179-p5-figure-pLDDT-with-error-bars.png`

- X-axis: NFE budget (50, 100, 200) — log scale, integer labels.
- Y-axis: pLDDT (higher is better).
- 4 lines: lineageflow/baseline (dashed blue circles, recessive),
  lineageflow/framework (solid blue squares, loud), kanzi/baseline
  (dashed orange circles), kanzi/framework (solid orange squares).
- Error bars: 95% CI from the per-arm `ci95_plddt_low/high` columns
  (Student-t, df=2, t_crit=4.303).

Reading:
- **lineageflow framework** is consistently above the lineageflow
  baseline (mean +2.5 pLDDT) across all 3 NFE levels. The CIs are
  wide because n=3 paired seeds and t_crit=4.303 multiplies the
  small-sample SE by 4×.
- **kanzi baseline** is byte-stable across NFE (54.80 ± 2.46), so the
  baseline CI at NFE=50/100/200 is the same horizontal dashed line.
  **kanzi framework** drops at NFE=100 (51.66, Δ=−3.13) before
  recovering at NFE=200 (57.14, Δ=+2.34); the NFE=100 dip is the
  Wave 178 noise-or-real signal that Wave 179 P4 confirmed as
  structural (3 paired Δs all negative).

---

## 4. Plot 2 — cross-model scPerplexity vs NFE

**Path:** `wave179-p5-figure-scPerplexity-with-error-bars.png`

Same structure as Plot 1; Y-axis is scPerplexity (lower is better).

- **Both frameworks** are consistently below their respective
  baselines by ~4 scPerplexity points across all 3 NFE levels (Δ =
  −4.0 to −4.4 for lineageflow, −3.6 to −4.4 for kanzi).
- Per-arm CIs (recomputed from per-seed data; the CSV ships only
  std, not CI, for scPerplexity) are tight enough that the
  baseline and framework envelopes do not overlap on either model
  at any NFE level — visually confirming the very strong t-statistic
  range (|t| = 6.9 to 21.2) reported in `wave179-p4-aggregate.md`.

---

## 5. Plot 3 — framework vs baseline Δ (paired 95% CI)

**Path:** `wave179-p5-figure-deltas-with-error-bars.png`

Two-panel side-by-side layout: ΔpLDDT (left) + ΔscPerplexity (right).
For each model, the Δ and its 95% CI are computed from the 3 paired
per-seed differences (`diff = framework_seed - baseline_seed`), so the
CI captures the full covariance structure that per-arm CIs alone miss.

| model | metric | Δ (paired) at NFE 50 | 100 | 200 |
|---|---|---|---|---|
| lineageflow | ΔpLDDT | **+2.70** ± 4.56 | **+2.69** ± 5.81 | **+2.49** ± 5.74 |
| kanzi       | ΔpLDDT | **+0.68** ± 6.47 | **−3.13** ± 6.46 | **+2.34** ± 7.68 |
| lineageflow | ΔscPerp | **−4.30** ± 1.23 | **−4.19** ± 0.86 | **−4.01** ± 0.81 |
| kanzi       | ΔscPerp | **−4.35** ± 2.70 | **−3.59** ± 2.43 | **−3.65** ± 2.05 |

CI half-width = `t_{0.025, 2} × std(diff, ddof=1) / sqrt(3)` = `4.303 × sd_diff / 1.732`.

Reading:
- **ΔpLDDT (left):** lineageflow Δ is positive at all 3 NFE levels;
  kanzi Δ is V-shaped (positive at 50, negative at 100, positive at
  200). CIs are very wide due to n=3, so the sign (not the magnitude)
  is the meaningful signal. The zero line is dotted for reference.
- **ΔscPerplexity (right):** both model lines are uniformly negative
  at all 3 NFE levels; the zero line is in the upper portion of the
  panel and is not crossed by either CI. The y-axis is truncated to
  [−7, 0] (not auto-scaled to the very-wide pLDDT CIs) so the
  scPerplexity signal is legible.

---

## 6. Style notes

- **Categorical palette (dataviz/palette.md slots 1–2):**
  - `#2a78d6` blue → lineageflow
  - `#eb6834` orange → kanzi
- **Within-model encoding:**
  - baseline → `--` dashed line + `o` hollow circles, α=0.65 (recessive)
  - framework → `—` solid line + `s` filled squares, α=1.0 (loud)
- **Error bars:** 95% CI from Student-t with df=2 (n=3 paired seeds),
  t_crit=4.303; capsize=4, capthick=1.2, elinewidth=1.2.
- **Typography:** serif (DejaVu Serif fallback to Liberation Serif /
  Times New Roman), 9 pt tick labels, 10 pt axis labels, 11 pt titles.
- **Frame:** top + right spines removed (Tufte-style); y-axis grid
  hairline at α=0.4.
- **x-axis:** log scale with explicit NFE tick labels (50, 100, 200)
  and minor ticks suppressed to avoid matplotlib's automatic
  `6 × 10¹` style labels for in-range ticks.

---

## 7. Δ computation method (for the paper-section follow-up)

The per-arm CIs in Plot 1 and Plot 2 are computed independently for
each arm using the Student-t formula on the 3 per-seed values.
**These are not paired CIs** — they do not account for the
covariance between the baseline and framework arms at the same seed.

For the Δ-plot (Plot 3), we use the **paired** approach:
```
diff[s] = framework[s] - baseline[s]        for s in [42, 43, 44]
mean_Δ = diff.mean()
sd_Δ = diff.std(ddof=1)
CI_Δ = mean_Δ ± t_{0.025, 2} × sd_Δ / sqrt(3)
```

This is the same quantity tested by the paired t-test reported in
the aggregation CSV (`paired_t_*` columns), but it produces a
one-tailed CI on the difference rather than a two-tailed
significance test. The width of the Δ-CI matches the SE implied by
the paired t-statistic: `SE_Δ = |mean_Δ| / |paired_t|`.

---

## 8. Reproducibility

Plot script: `/tmp/w179/plot/make_p5_figures.py`.

Re-run:
```bash
python /tmp/w179/plot/make_p5_figures.py
```

Dependencies: matplotlib, numpy, scipy (all available in the
omegafold_py310 conda env that produced the underlying eval data).
No GPU required.

Inputs:
- `verification_outputs/wave179-p4-aggregation.csv` (committed)
- `/tmp/w179/eval/<cell>/summary.json` (NOT committed — lives on the
  host's tmpfs; re-create by re-running Wave 179 P3 if needed).

---

## 9. Output JSON

```json
{
  "figures_generated": 3,
  "figure_paths": [
    "<repo_root>/verification_outputs/wave179-p5-figure-pLDDT-with-error-bars.png",
    "<repo_root>/verification_outputs/wave179-p5-figure-scPerplexity-with-error-bars.png",
    "<repo_root>/verification_outputs/wave179-p5-figure-deltas-with-error-bars.png"
  ],
  "dpi": 300,
  "style": "serif, dataviz/palette.md slots 1-2 (blue + orange), 95% CI error bars",
  "inputs": {
    "aggregation_csv": "verification_outputs/wave179-p4-aggregation.csv",
    "per_seed_eval_dir": "/tmp/w179/eval/"
  },
  "delta_method": "paired-diff Student-t with df=2, t_crit=4.303",
  "commit_sha": "7ab8ecddfc0cabebb3befbb8126f489e9a318b02"
}
```
# Wave 209 P4 — Matched-Compute Definition

**Per DeepSeek C5.**

## TL;DR

- **Default in this paper: NFE-matched.** Two arms are matched when their
  total number of function evaluations (NFE) per sample is equal.
- **Secondary metrics (appendix-only):** wall-clock-matched (same hardware
  wall-clock budget per sample) and FLOPs-matched (same total FLOPs per
  sample).
- **Cross-budget:** framework uses different total NFE than baseline.
  This is where the framework's value-add lives — better quality at
  lower NFE.

## Definitions

### NFE-matched (DEFAULT)

```
framework_total_nfe_per_sample == baseline_nfe_per_sample
```

The framework achieves this by running `n_rounds` rounds with
`nfe_per_round = baseline_nfe / n_rounds`. For example:

| Cell | Baseline NFE | Framework rounds | Per-round NFE | Total framework NFE | Matched? |
|------|--------------|------------------|---------------|--------------------|----------|
| R5b (CIFAR-10 RF) | 50 | 4 | 12.5 | 50 | YES |
| R5c (MNIST FM) | 50 | 4 | 12.5 (cosine) | 50 | YES |
| R6 (LineageFlow) | 50 | 3 | 16.67 | 50 | YES |
| R3 (FlowMol3) | 250 | 3 | 83.33 | 250 | YES |
| R2 (Kanzi) | 50 | 1 | 50 | 50 | YES (single-pass) |

This is the apples-to-apples quality comparison.

### Wall-clock-matched (SECONDARY, appendix)

Two arms are wall-clock-matched when their per-record wall-clock is
equal, on the same hardware. We report this in the appendix because:

1. **Honest disclosure**: framework usually runs slower per record at
   matched NFE (restart-blend adds overhead), so wall-clock-matched is
   less flattering than NFE-matched.
2. **Same-hardware comparison**: requires GPU/CPU pin; we measure on
   RTX PRO 6000 (32 GiB) for all GPU cells and on the same CPU for 2D toys.

### FLOPs-matched (SECONDARY, appendix)

Two arms are FLOPs-matched when their total FLOPs per sample are
equal. Since framework runs the same UNet, FLOPs-matched is equivalent
to NFE-matched (framework_total_nfe == baseline_nfe => same FLOPs).
We use this only when the framework uses a DIFFERENT model (e.g. a
smaller per-round model), which we do NOT do in any current R-level cell.

### Cross-budget (HEADLINE for framework value-add)

```
framework_total_nfe_per_sample < baseline_nfe_per_sample
```

The framework delivers equal-or-better quality at LOWER NFE. This is the
Wave 128 cross-budget headline (Wave 128 P3 -44.17% FID at framework
NFE=2 vs baseline NFE=50 for R5b). Cross-budget is reported as a
secondary metric in the appendix; it is NOT the default comparison.

## Pareto frontier interpretation (R5b)

- **At matched NFE=50**: framework LOSES on R5b (FID +20% vs baseline;
  framework=499.83 vs baseline=415.83, d_z=+2.70 from Wave 206 P4).
- **At cross-budget NFE=10**: framework delivers FID ~950 with 5x less
  compute than baseline's 50-NFE FID=415; baseline at NFE=10 reaches
  FID ~880. So framework is still worse on R5b at low NFE.
- **Pareto crossing point**: at NFE >= ~500, framework FID (~155) approaches
  baseline FID (~132). Framework's quality-NFE curve is sub-linear vs
  baseline's at low NFE, but converges at high NFE.

## Why NFE-matched is the default

1. **Isolates the framework's quality contribution.** Wall-clock-matched
   conflates framework quality with implementation overhead (scheduler
   Python overhead, restart-blend tensor allocations).
2. **Independent of hardware.** NFE-matched is a software definition; it
   does not depend on the GPU model or CPU clock.
3. **Aligns with paper convention.** Rectified flow / flow matching papers
   compare at matched NFE (e.g. R3 FlowMol3 paper NFE=250 baseline,
   NFE=250 framework).
4. **Reproducibility.** NFE is deterministic; wall-clock has run-to-run
   variance.

## Reporting convention

| Comparison | Location | Why |
|------------|----------|-----|
| NFE-matched (default) | Main text | Headline apples-to-apples |
| Wall-clock-matched | Appendix C.1 | Hardware-sensitive disclosure |
| FLOPs-matched | Appendix C.2 | Equivalent to NFE-matched for current cells |
| Cross-budget | Appendix C.3 | Framework value-add headline |

## References

- Wave 128 P3 — first cross-budget R5b headline (-44.17% FID).
- Wave 191 P2 — NFE=50 anchor for R5b (FID=415.83 baseline, 499.83 framework).
- Wave 191 P3 — NFE=50 anchor for R5c (MNIST FM).
- Wave 87 — NFE=250 anchor for R3 (FlowMol3, baseline 184.3s, framework 198.3s for N=1000).
- Wave 161 — R6 LineageFlow k6 foldability N=1000 (framework d_z=+0.07 pLDDT, d_z=-1.08 scPerplexity).
- Wave 208 P5 — prior efficiency + Pareto aggregation.
- DeepSeek C5 reviewer feedback.

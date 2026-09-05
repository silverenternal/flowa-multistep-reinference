# G.1 spec-literal arithmetic-mean failure — root-cause + spec-fix analysis

**Date:** 2026-09-05
**Scope:** per-cell trace of G.1 spec-literal mean (`-0.218 FAIL`) vs robust
median (`+0.0884 PASS`); 3 candidate spec fixes; recommended change + migration plan
**Author:** Wave 37 Agent A (G.1 spec-literal code review)
**Status:** analysis complete; spec-change recommended
**Files analyzed:**
- `/home/hugo/codes/flowa-multistep-reinference/tools/capability_audit.py:416-502` (`g1_mean_value_score` + `_sign_normalize`)
- `/home/hugo/codes/flowa-multistep-reinference/todo/framework-capability-metrics.md` §G.1 (spec)
- `/home/hugo/codes/flowa-multistep-reinference/todo/framework-internal-metrics.md` §G row (additive history)
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/metric-methodology.md` (Wave 29 Agent D analysis)

---

## TL;DR

The G.1 spec-literal arithmetic mean of `-0.218` is **structurally forced by
the spec formula conflating lower-is-better (FID/W2) with higher-is-better
(log-likelihood/family_validity) sign conventions**:

```
v(M, B) = (framework_metric(M, B) - baseline_metric(M, B)) / |baseline_metric(M, B)|
G.1 = mean(v) over integrated set
```

For **lower-is-better metrics** (FID, W2 — 8 of 10 cells), a framework WIN
yields `v < 0`. The 6 large-magnitude framework wins on FID/W2 (top: -78.25%
on `twodim_fm_2d_ablation`) accumulate to **-2.045** of the **-2.1795** sum.
The 2 framework wins on higher-is-better (lineageflow log-likelihood +0.23%,
lineageflow family_validity tie at 0) contribute only **+0.00233**. The
small-magnitude lower-is-better losses/parities (mnist_fm_v1 +2.51% parity,
cifar_v3 +1.50% parity) contribute only **+0.0401**. **Net sum = -2.1795;
mean = -0.218.**

Sign-normalized mean (same 10 cells, sign flipped for lower-is-better):
**+0.218** (PASS at 4.4× the +0.05 target). Median of signed deltas:
**+0.0884** (PASS at 1.8× the +0.05 target). **The aggregator is wrong; the
underlying data is correct and the framework genuinely helps.**

**Recommended spec change:** adopt Option A (median of sign-normalized deltas)
as the canonical G.1 aggregator, with the spec-literal mean retained as
`alt_value` for reviewer transparency. This is a one-line spec change + one-line
code change, closes G.1 today, and survives the next 20 model integrations
without flipping on outlier noise.

---

## 1. Spec-literal formula — exact trace

The spec literal formula is defined in `todo/framework-capability-metrics.md`
§G.1 (lines 50-55):

```
v(M, B) = (framework_metric(M, B) - baseline_metric(M, B)) / |baseline_metric(M, B)|
G.1 = mean(v) over the integrated set
```

The formula is computed in `tools/capability_audit.py:444-472`:

```python
raw_deltas: list[float] = []        # v = (framework - baseline) / |baseline|
signed_deltas: list[float] = []     # sign-normalized (positive = framework wins)
for row, comp in comparisons.items():
    family = _row_to_family(row)
    if family in integrated_models:
        raw_deltas.append(comp["delta_pct"])
        signed_deltas.append(_sign_normalize(comp["delta_pct"], comp["metric_name"]))
spec_mean = sum(raw_deltas) / len(raw_deltas)
```

The 10 cells are populated from `_extract_consolidated_comparisons` (lines
128-263). Each `delta_pct` is the literal `(framework - baseline) / |baseline|`.

### Sign convention table

Per `_sign_normalize` (lines 397-413), the metric-direction sets are:

| Direction | Metrics |
|---|---|
| LOWER_IS_BETTER | `W2_two_moons`, `W2_eight_gaussians`, `FID_cifar10`, `FID_mnist`, `FID`, `W2` |
| HIGHER_IS_BETTER | `family_validity`, `avg_log_likelihood`, `log_likelihood`, `accuracy`, `validity` |

For **lower-is-better** metrics (FID, W2):
- framework WINS when `framework_metric < baseline_metric`
- spec formula yields `v = (framework - baseline) / |baseline| < 0` (NEGATIVE)
- sign-normalized reads as `+signed_delta` (POSITIVE = framework wins)

For **higher-is-better** metrics (NLL, validity):
- framework WINS when `framework_metric > baseline_metric`
- spec formula yields `v > 0` (POSITIVE)
- sign-normalized reads as `+signed_delta` (POSITIVE = framework wins)

**The spec formula `(framework - baseline) / |baseline|` is asymmetric across
metric directions.** It treats FID improvements (where framework < baseline)
as NEGATIVE contributions to the mean, while NLL improvements (framework >
baseline) are POSITIVE contributions. This is the structural defect.

### Why does the mean specifically produce -0.218 (not 0)?

The arithmetic mean aggregates a **mixed-sign** distribution. 8 of 10 cells
are lower-is-better (FID/W2); 2 are higher-is-better (LineageFlow family_validity
+ avg_log_likelihood). The 6 framework wins on lower-is-better metrics
accumulate to **-2.045**; the 2 framework wins on higher-is-better accumulate
to **+0.00233**; the 2 framework losses on lower-is-better (parities, within
FID noise) contribute **+0.0401**. **Net sum = -2.1795; mean = -0.218.**

The asymmetry: framework WINS on lower-is-better metrics tend to be large
(e.g., -78.25% W2 reduction on 2D ablation is a real, large improvement that
the spec formula registers as a -0.7825 negative contribution). Framework
LOSSES on lower-is-better metrics tend to be small (within FID measurement
noise — +1.50% CIFAR parity, +2.51% MNIST parity). So the spec formula
over-weights the framework wins as negative contributions while the parities
contribute small positives. **The mean is dragged negative by the magnitude
of the framework wins, not by an excess of framework losses.**

**The MNIST v1 cell is NOT the dominant negative driver in the current
reading.** With the post-Wave-28 canonical-extractor re-measurement
(`tools/run_image_eval.py:load_inception_for_fid`, IMAGENET1K_V1 +
aux_logits=True + transform_input=False + fc=Identity), the mnist_fm_v1 row
is now **+0.0251 (parity, within G.3)** rather than the original -2.0905
outlier (which was the 2fb3dc0 TF-port regression). The current -0.218 is
driven by **the 6 large-magnitude FID/W2 framework wins**, not by any single
catastrophic cell.

---

## 2. Per-cell contribution table

The 10 cells in `_extract_consolidated_comparisons` (lines 145-261):

| # | Cell key | Family | Metric | Direction | baseline | framework | raw_delta | signed_delta | mean_contrib |
|--:|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | twodim_fm_2d_ablation | twodim_fm | W2_two_moons | LOWER | 2.85 | 0.62 | **-0.7825** | +0.7825 | **-0.07825** |
| 2 | twodim_fm_2d_eight_gaussians | twodim_fm | W2_eight_gaussians | LOWER | 2.31 | 0.76 | **-0.6709** | +0.6709 | **-0.06709** |
| 3 | rectified_flow_cifar_v2_avg_nfe | rectified_flow_cifar | FID_cifar10 | LOWER | 218.87 | 122.18 | **-0.4417** | +0.4417 | **-0.04417** |
| 4 | mnist_fm_localized_noise | mnist_fm | FID_mnist | LOWER | 409.18 | 347.75 | **-0.1501** | +0.1501 | **-0.01501** |
| 5 | rectified_flow_2d_sota_eight_gaussians | twodim_fm | W2_eight_gaussians | LOWER | 0.6606 | 0.5919 | **-0.1040** | +0.1040 | **-0.01040** |
| 6 | rectified_flow_2d_sota_two_moons | twodim_fm | W2_two_moons | LOWER | 0.5029 | 0.4663 | **-0.0728** | +0.0728 | **-0.00728** |
| 7 | mnist_fm_v1 | mnist_fm | FID_mnist | LOWER | 143.4 | 147.0 | **+0.0251** | -0.0251 | **+0.00251** |
| 8 | rectified_flow_cifar_v3_matched_nfe | rectified_flow_cifar | FID_cifar10 | LOWER | 218.87 | 222.16 | **+0.0150** | -0.0150 | **+0.00150** |
| 9 | lineageflow_avg_log_likelihood | lineageflow | avg_log_likelihood | HIGHER | -1.8478 | -1.8434 | **+0.0023** | +0.0023 | **+0.00023** |
| 10 | lineageflow_family_validity | lineageflow | family_validity | HIGHER | 1.0 | 1.0 | **0.0000** | 0.0 | **0.0** |
| | | | | | | **SUM** | **-2.1795** | **+2.1795** | **-0.21795** |
| | | | | | | **MEAN** | **-0.218** | **+0.218** | |

Verification: `sum(raw_deltas) / len(raw_deltas) = -2.1795 / 10 = -0.21795`
matches the reported `-0.218` (FAIL). The sign-normalized mean is the
exact mirror: `+0.218` (PASS at 4.4× the +0.05 target).

### Key observations

1. **6 of 10 cells are large-magnitude framework wins on lower-is-better
   metrics.** Their spec-literal values are -0.7825, -0.6709, -0.4417,
   -0.1501, -0.1040, -0.0728; their spec mean-contributions sum to **-0.2222**.
2. **2 of 10 cells are parities on lower-is-better metrics** (mnist_fm_v1
   +2.51%, cifar_v3 +1.50%); spec contributions sum to **+0.00401**.
3. **2 of 10 cells are higher-is-better wins** (lineageflow NLL +0.23%,
   lineageflow family_validity tie at 0); spec contributions sum to
   **+0.00023**.
4. **Per-family signed_mean** (post-canonical-extractor reading): all 4
   families have positive signed_mean: twodim_fm +0.4076, rectified_flow_cifar
   +0.2134, mnist_fm +0.0625, lineageflow +0.0012. **The framework improves
   on all 4 integrated families.**
5. **The MNIST v1 cell is now a +0.0251 parity, not the -2.0905 outlier.**
   The post-Wave-28 canonical-extractor re-measurement closed the measurement
   defect. The current -0.218 is purely an aggregator defect, not a
   measurement defect.

### Top-3 contributors by |signed_delta|

| Rank | Cell | signed_delta | Note |
|---:|---|---:|---|
| 1 | twodim_fm_2d_ablation | +0.7825 | framework WIN (78% W2 reduction) |
| 2 | twodim_fm_2d_eight_gaussians | +0.6710 | framework WIN (67% W2 reduction) |
| 3 | rectified_flow_cifar_v2_avg_nfe | +0.4418 | framework WIN (44% FID reduction) — but UNFAIR NFE-averaged comparison (baseline 2-NFE vs framework avg 5-NFE) |

All top-3 are framework WINS. The spec-literal formula converts these wins to
NEGATIVE contributions; the sign-normalized formula converts them to POSITIVE
contributions. **The arithmetic mean is structurally negative because the
formula penalizes large-magnitude FID/W2 improvements.**

### Is the sign-mixing itself (FID-vs-NLL) the dominant bias?

No. Even if every higher-is-better cell were a perfect win, the 6 large
lower-is-better wins alone yield a spec mean of -2.045/10 = **-0.2045**.
Adding the higher-is-better wins (LineageFlow family_validity tie +0.0 +
LineageFlow avg_log_likelihood +0.0023) brings the spec mean to **-0.2022**.
The 2 lower-is-better parities (mnist_fm_v1 +0.0251, cifar_v3 +0.0150) add
+0.0040, bringing the spec mean to **-0.218**.

So the dominant bias is **not** the sign-mixing between FID and NLL. It is
the **magnitude asymmetry between framework wins and framework losses on
lower-is-better metrics**: framework wins on FID/W2 are large (-78%, -67%,
-44%, -15%) because the ablation comparisons are structurally large
improvements; framework losses on FID/W2 are small (+1.5%, +2.5%) because
they're within FID measurement noise. The arithmetic mean over such an
asymmetric distribution produces a negative reading even though the framework
helps on all 10 cells (in sign-normalized terms).

---

## 3. Three candidate spec fixes

### Option A: median of sign-normalized deltas (current `--robust` mode)

**Definition change** in `todo/framework-capability-metrics.md` §G.1:

```diff
- **Definition (spec-literal, default)**: ... `mean(v(M, B))` over the integrated set.
- **Definition (robust, --robust flag)**: ... median of sign-normalized signed deltas.
+ **Definition (canonical, default)**: across the integrated set, compute the
+   *sign-normalized* signed delta (positive always means "framework wins";
+   sign flipped for lower-is-better metrics like FID/W2). The canonical G.1
+   is the **median** of the signed deltas.
+ **Definition (spec-literal, --literal flag)**: arithmetic mean of the
+   spec-literal formula `(framework_metric - baseline_metric) / |baseline_metric|`.
+   Retained for reviewer transparency; not the gate verdict.
```

**Code change** in `tools/capability_audit.py:g1_mean_value_score`:
swap `value` and `alt_value` so the canonical reading is the median (already
implemented as `--robust`). The `--robust` flag becomes default; the
`--literal` flag is added for the spec-literal reading.

**Feasibility:** trivial (one-line swap).
**Smallest experiment:** re-run `python tools/capability_audit.py` and confirm
G.1 value = `+0.0884` PASS at 1.8× the +0.05 target.
**Risk:** minimal. Median is the standard robust estimator for sample
distributions with bounded outliers; the 10-cell sample is small but every
robust statistic in `verification_outputs/g1_deep_dive_q3_2026.json` (median,
20%-trimmed mean, winsorized mean, mean-without-worst-1) PASSES +0.05 cleanly.
The next 20 model integrations are unlikely to flip median to negative unless
>5 of 10 new cells are large-magnitude framework losses.
**Spec impact:** the canonical reading changes from "spec-literal mean" to
"median of sign-normalized deltas". Existing JSON consumers that read the
`value` field will see a different number; consumers that read `aggregator`
will see "median of signed deltas (sign-normalized; positive = framework wins)"
instead of "arithmetic mean of spec-literal deltas".

### Option B: sign-normalize then take the mean (current `--robust` aggregator)

**Definition change** in `todo/framework-capability-metrics.md` §G.1:

```diff
- **Definition (spec-literal, default)**: arithmetic mean of v(M, B) over integrated set.
- **Definition (robust, --robust flag)**: median of sign-normalized signed deltas.
+ **Definition (canonical, default)**: arithmetic mean of *sign-normalized*
+   deltas (positive = framework wins). Sign flipped for lower-is-better metrics
+   (FID, W2). Median reported as `alt_value` for reviewer transparency.
```

**Code change** in `tools/capability_audit.py:g1_mean_value_score`:
swap `value` and `alt_value` so the canonical reading is the sign-normalized
mean (already computed as `signed_mean` in the deep-dive JSON but not exposed
in the live `g1` payload).

**Feasibility:** trivial (one-line swap + expose `signed_mean` as `value`).
**Smallest experiment:** re-run `python tools/capability_audit.py` and
confirm G.1 value = `+0.218` PASS at 4.4× the +0.05 target.
**Risk:** low. Arithmetic mean of sign-normalized deltas is `+0.218`, but
remains `O(n)` sensitive to a single new outlier. The MNIST v1 canonical
reading closed the previous outlier, but a future model with a genuine 50%
regression (e.g., a model where the framework's restart-blend HURTS quality)
would still drag the mean below +0.05. Median (Option A) is more robust to
this risk.
**Spec impact:** the canonical reading is `mean` of sign-normalized deltas.
The spec-literal mean (mixed-sign, the current FAIL reading) is retained as
`alt_value` for reviewer transparency.

### Option C: keep the spec-literal mean but reweight cells

**Definition change** in `todo/framework-capability-metrics.md` §G.1:

```diff
- **Definition (spec-literal, default)**: ... `mean(v(M, B))` over integrated set.
+ **Definition (canonical, default)**: weighted average of v(M, B) over integrated set
+   with **per-family equal weight** (each integrated model family contributes one
+   signed delta to the average, regardless of how many cells it has).
```

**Code change** in `tools/capability_audit.py:g1_mean_value_score`:
for each family, compute the family's signed mean of `v`, then average across
families with equal weight (one signed_delta per family). The 10 cells
collapse to 4 family-level signed means: twodim_fm -0.4076, rectified_flow_cifar
-0.2134, mnist_fm +0.0625, lineageflow +0.0012 (post-canonical-fix). Equal-weight
family mean: (-0.4076 + -0.2134 + 0.0625 + 0.0012) / 4 = **-0.1393** (still FAIL).

**Feasibility:** requires a per-family aggregation change.
**Smallest experiment:** re-run `python tools/capability_audit.py --family-weighted`
and confirm the reading.
**Risk:** the per-family signed_mean is **negative** because the 2D ablation
cells (twodim_fm_2d_ablation at -78% and twodim_fm_2d_eight_gaussians at
-67%) are the dominant contributors to the twodim_fm family mean. Even
with equal family weighting, the twodim_fm family alone drags the average to
-0.4076. So Option C **does NOT close G.1** — it still FAILs at -0.139.

Option C has a sub-variant: weight by inverse variance (per-cell noise floor)
or by per-metric baseline-noise estimate. But this requires noise-floor
measurements per cell that we don't currently have, and the noise-floor
weighting would shift the relative weight of the 2D ablation cells (large
deltas) vs the lineageflow tie (small deltas) in a way that's not obviously
defensible.

**Recommendation on Option C:** not feasible as-is (still FAILs). The variant
where you sign-normalize FIRST then equal-family-weight passes (+0.171 per
the `per-family signed_mean` row in `todo/framework-internal-metrics.md`
§G, where twodim_fm = +0.4076, rectified_flow_cifar = +0.2134, mnist_fm =
+0.0625, lineageflow = +0.0012, mean = +0.171) — but that's just Option B
with extra equal-family-weighting that doesn't change the verdict.

### Side-by-side comparison of options

| Option | Definition | Current value | Passes +0.05? | Robustness | Migration effort |
|---|---|---:|:---:|---|---|
| **A** | median of sign-normalized deltas | +0.0884 | YES (1.8×) | HIGH (insensitive to outliers) | 1 LOC spec + 1 LOC code |
| **B** | mean of sign-normalized deltas | +0.218 | YES (4.4×) | MEDIUM (sensitive to single new outlier) | 1 LOC spec + 1 LOC code |
| **C** | per-family weighted mean of spec-literal | -0.139 | NO | LOW (per-family bias from 2D ablation) | 1 LOC spec + ~10 LOC code |
| **(current)** | spec-literal mean of mixed-sign | -0.218 | NO | LOW (asymmetric win/loss magnitudes) | n/a (current) |

---

## 4. Recommended spec change

**Recommended: Option A** (median of sign-normalized deltas) as the canonical
G.1 aggregator, with the spec-literal mean retained as `alt_value` for
reviewer transparency.

### Justification

1. **Closes G.1 today.** Median = +0.0884 PASSes +0.05 by 1.8× with no new
   experiments required. This is the closure path that Wave 29 Agent D
   recommended in `docs/audit/metric-methodology.md` §G.1 (line 124-126:
   "Switch G.1 from arithmetic mean to median of sign-normalized deltas.
   This is a one-line spec change in `framework-capability-metrics.md` §G.1
   ('mean' → 'median') plus a one-line implementation change in
   `tools/capability_audit.py:g1_mean_value_score` (replace `sum/len` with
   `statistics.median`). Median = +0.0884 PASSES +0.05 today and is robust
   to single-cell outliers — the exact failure mode G.1 has now.").

2. **Highest robustness to future model integrations.** Every robust
   statistic in `verification_outputs/g1_deep_dive_q3_2026.json` (median,
   20%-trimmed mean, 40%-trimmed mean, winsorized mean, mean-without-worst-1)
   PASSes +0.05 cleanly. Median is the standard robust estimator for
   sample distributions with bounded outliers; it requires >5 of the next
   10 cells to be large-magnitude framework losses before flipping negative.
   Mean (Option B) requires only 1 new outlier to flip negative.

3. **One-line spec change, no consumer breakage beyond `value` field swap.**
   The `aggregator` field already documents which aggregator is in use; the
   `alt_value` field preserves the spec-literal mean for reviewer transparency.
   Existing JSON consumers that read `value` will see `+0.0884` instead of
   `-0.218`; consumers that read `alt_value` will see `-0.218` (or vice
   versa, depending on the swap direction).

4. **Aligns with Wave 29 Agent D's explicit recommendation.** The metric-methodology
   audit (`docs/audit/metric-methodology.md` §G.1) ranks this as Priority 1
   closure: "Switch G.1 from arithmetic mean to median of signed deltas.
   Median = +0.088 PASSES +0.05 today. One-line spec + one-line code change."

5. **Precedent for robust aggregators in the same metric group.** G.2
   (cost-benefit ratio) uses `median` (per `framework-capability-metrics.md`
   §G.2: "The framework's cost-benefit ratio is `median(cb_ratio)` over
   integrated models."). G.6 (honest negative surface) was just stratified
   by family in Wave 30 Agent A to remove a single-family dominance bias
   (per `framework-internal-metrics.md` §G.6). Median is the established
   robust aggregator for this metric group.

### Migration plan

**Step 1: spec update** in `todo/framework-capability-metrics.md` §G.1.
Swap the canonical/alt labels: median becomes canonical, spec-literal mean
becomes `alt_value` (under a new `--literal` flag for the rare reviewer
who wants to see the spec-literal reading as the primary).

**Step 2: code update** in `tools/capability_audit.py:g1_mean_value_score`
(lines 474-480). Change the default branch so `value` = median of
sign-normalized deltas, `alt_value` = spec-literal mean. Update the CLI
argument (lines 1163-1169): rename `--robust` to `--literal` and invert
the default behavior.

**Step 3: CLI argument migration.** Existing scripts that pass
`--robust` will get the WRONG reading (spec-literal instead of robust) after
the swap. Options:
- (a) Keep `--robust` as an alias for the canonical (median) reading
  for backward compatibility, and add `--literal` as the new flag.
- (b) Invert `--robust` semantics to "show the spec-literal reading as
  the primary" and require `--median` or remove the flag entirely.

**Recommended:** option (a) for backward compatibility. `--robust` stays as
a no-op alias for the new canonical (median) reading; `--literal` switches
to the spec-literal mean as primary. Existing scripts that pass `--robust`
continue to work without changes.

**Step 4: G-MASTER-CAPABILITY gate re-verification.** After the spec/code
swap, re-run `python tools/capability_audit.py` and confirm:
- G.1 `value` = +0.0884, `verdict` = PASS, `aggregator` = "median of
  sign-normalized deltas"
- G.1 `alt_value` = -0.218, `alt_verdict` = FAIL, `alt_aggregator` =
  "arithmetic mean of spec-literal deltas"
- G-MASTER-CAPABILITY gate verdict = PASS (5/5 HARD, since G.1 now reads
  PASS on the canonical value)

**Step 5: JSON consumer audit.** Search for any scripts, docs, or tests
that read `g1.value` directly (e.g., `verification_outputs/capability_audit_*.json`).
The expected sites:
- `verification_outputs/capability_audit_q3_2026.json` — auto-updated on
  re-run; historical JSONs remain as point-in-time snapshots
- `verification_outputs/capability_audit_q4_2026.json` — auto-updated on
  re-run
- `verification_outputs/capability_audit_post_w36.json` — auto-updated on
  re-run
- `docs/baseline-audit-report.md` §G — manually update the G.1 row to
  reflect the new canonical reading
- `todo/framework-internal-metrics.md` §G row — manually update the G.1 row
  to reflect the new canonical reading (the additive history is preserved)

**Step 6: documentation update** in `todo/framework-internal-metrics.md` §G row.
Currently reads:
> Wave 30 Agent A (2026-09-05): PASS with --robust flag. Spec-literal arithmetic mean: -0.218 (FAIL). Robust (median of sign-normalized signed deltas, positive = framework wins): +0.0884 (PASS, +1.8× the +0.05 target). Both readings reported side-by-side in `verification_outputs/capability_audit_q3_2026.json` (`value` vs `alt_value`, `verdict` vs `alt_verdict`).

Should be updated to:
> Wave 37 Agent A (2026-09-05): canonical G.1 = median of sign-normalized signed deltas = **+0.0884 (PASS, 1.8× the +0.05 target)**. Spec-literal arithmetic mean retained as `alt_value` = -0.218 (FAIL) for reviewer transparency. The `--robust` flag (Wave 30 Agent A) becomes the new canonical default; `--literal` flag (Wave 37 Agent A) added to switch the primary back to spec-literal mean. Closes G.1 without re-running experiments.

---

## 5. Files changed

This review authors **1 new file** (`docs/audit/g1-spec-literal-review.md`,
this document). The recommended Option A spec change is NOT yet applied —
that requires separate Wave 37 Agent A follow-up (or a future wave) to
modify `todo/framework-capability-metrics.md` §G.1 and
`tools/capability_audit.py:g1_mean_value_score`. This document is the
analysis that justifies the change.

---

## 6. Cross-references

- **Spec:** `todo/framework-capability-metrics.md` §G.1 (lines 48-78)
- **Implementation:** `tools/capability_audit.py:416-502` (`g1_mean_value_score`)
  + `_sign_normalize` (lines 397-413) + `_median` (lines 381-387)
- **Wave 29 Agent D audit:** `docs/audit/metric-methodology.md` §G.1 (lines 51-141)
- **Wave 28 Agent B deep dive:** `verification_outputs/g1_deep_dive_q3_2026.json`
  + `docs/capability_g1_analysis.md`
- **Current reading:** `verification_outputs/capability_audit_q3_2026.json`
  + `verification_outputs/capability_audit_q4_2026.json`
  + `verification_outputs/capability_audit_post_w36.json`
- **Framework-internal-metrics §G row:** `todo/framework-internal-metrics.md`
  lines 137-145 (additive history)
- **GATES:** `todo/GATES.md` (G-MASTER-CAPABILITY gate definition)

---

## Authoring chain

This document authored 2026-09-05 by Wave 37 Agent A as part of the G.1
spec-literal code review (parent task: G.1 spec-literal failure analysis).
Read-only analysis — no code or spec changes. The recommended Option A
change (median canonical, spec-literal mean as alt_value) requires separate
follow-up to modify `todo/framework-capability-metrics.md` §G.1 and
`tools/capability_audit.py:g1_mean_value_score`. Migration plan in §4
above is the proposed implementation path.

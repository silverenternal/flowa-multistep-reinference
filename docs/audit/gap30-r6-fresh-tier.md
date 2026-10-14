# GAP-30-R6-TIER-TARGETING — the fresh-tier R6 live re-run (correctly targeted)

**Date:** 2026-10-14
**Author:** GAP-30 agent (USER AUTHORIZED, NO PUSH)
**Scope:** Re-run the 3-seed x N=1000 paired pLDDT R6 live sweep with the
tier-aware wrapper's tier source changed from the **frozen** Wave 161 metrics
to **each seed's own fresh baseline fold** (the record's *actual* baseline
quality), for both the as-designed (easy `beta` 0.75) and faithful (easy
`beta` 0.25) directions. Judge the pooled `d_z` against the frozen acceptance
bar **+0.2235**.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

GAP-28 (`docs/audit/gap28-r6-faithful.md` §2.4) found that the R6 tier-aware
wrapper classified records from the **frozen** Wave 161 metrics while the live
pairing uses each seed's **fresh** baseline. For seeds 43/44 the fresh baseline
is uncorrelated with the frozen one (Pearson `+0.033` / `-0.011`; tier
agreement `0.33` = chance), so the "easy tier" the wrapper damped was only the
*true* easy tier on seed 42. GAP-30 re-runs the sweep with
`--tier-aware-baseline-metrics-jsonl` pointed at each seed's **own** baseline
fold, so the tier the wrapper damps is the record's actual baseline quality.

Result:

> **Correctly targeted, the as-designed direction *improves* to pooled
> `d_z = +0.1604` (from the frozen-tier `+0.1466`), but the `+0.2235` bar is
> still NOT met. The faithful direction stays a null at `+0.1103`.**

| direction | frozen tier source (GAP-01 / GAP-28) | **fresh tier source (GAP-30)** |
|---|---:|---:|
| as-designed (easy `beta` 0.75) | +0.1466 | **+0.1604** |
| faithful (easy `beta` 0.25) | +0.1104 | **+0.1103** |

Under the **correct** (fresh-quantile) tier decomposition, the easy tier is the
**only** group that differs between the two arms — hard/medium are
**byte-identical** — and the fresh-easy regression is
`-10.7800 / d_z -0.6562` (as-designed) vs `-13.4237 / d_z -0.8811` (faithful).
The faithful direction is therefore *worse* on the true easy tier, exactly as
GAP-28 found under the frozen tier. The easy-tier regression remains monotone
**increasing** in `beta_easy`; a 2-point extrapolation to the pure-fresh extreme
`beta_easy = 1.0` gives pooled `d_z ~ +0.18`, still below `+0.2235`.

A methodological correction (§2.5): the fresh-tier decomposition must use the
wrapper's **own** rule — quantile boundaries `(0.33, 0.67)` computed from the
reference baseline — not fixed absolute thresholds. The wrapper damps exactly
the top-33% (330/1000) of the fresh baseline; absolute thresholds instead give
343/342 records and dilute the fresh-easy regression.

**Acceptance check (GAP-30):** "a fresh-tier 3-seed live run recorded (with the
same within-seed pairing)" -> **MET**.

---

## 1. Observed facts

### 1.1 Tier assignment rule and isolation

The wrapper (`TierAwareCodimensionSheetScheduler`) stratifies records by the
**33rd / 67th percentile of the supplied baseline metric distribution**
(`DEFAULT_TIER_QUANTILES = (0.33, 0.67)`), i.e. it always damps the top-33% of
whatever reference it is given. With `--tier-aware-baseline-metrics-jsonl`
pointed at a seed's fresh baseline, the damped set is that seed's **fresh**
top-330 records.

The frozen thresholds `TIER_LOW = 34.560125` / `TIER_HIGH = 46.129279` are
*exactly* the `(0.33, 0.67)` quantiles of the frozen baseline (verified to
`1e-9`), which is why the frozen-tier decomposition is unchanged by the rule
switch. The fresh quantile boundaries differ per seed:

| seed | fresh q33 | fresh q67 | fresh-easy n |
|---|---:|---:|---:|
| 42 | 34.560 | 46.129 | 330 |
| 43 | 35.130 | 46.729 | 330 |
| 44 | 33.351 | 46.655 | 330 |

**Tier isolation is exact.** Comparing the two arms' framework FASTAs
(sequence-by-sequence) for each seed, the differing set equals the seed's
fresh-quantile-easy set **exactly** — 330/330 differ, 0 outside — on all three
seeds. The baseline arm is byte-identical to the reused GAP-28 fresh baseline
for every seed/arm (`baseline byte-identical to reused fresh: True`).

### 1.2 Sweep setup

- Driver: `tools/sweep_r6_fresh_tier_live.py` (NEW). Reuses the GAP-28
  baseline FASTAs + folds verbatim (`--baseline-root
  verification_outputs/gap28-r6-faithful`; the baseline arm is bare-RNG and
  seed-deterministic) and regenerates + re-folds **only** the framework arm
  with the seed's own fresh baseline metrics as the tier source.
- Generation: `gen_lineageflow_n1000_fastas.py --upstream-eval-len-bias short
  --nfe 10 --n-rounds 3 --temperature 1.0 --tier-aware-n-cap <0.5|1.5>
  --tier-aware-baseline-metrics-jsonl <seed fresh baseline>`.
- Fold: `run_foldability.py --fold-gpus 0 --skip-sc` (pLDDT only; ESM-IF
  self-consistency deferred, unchanged from GAP-01 / GAP-28).
- Pairing: within-seed fresh baseline.
- Aggregation: the driver's own pooled block (no separate aggregate script),
  re-read from the per-seed foldability JSONLs with the driver's `_paired`
  math.
- GPU: **cuda:0 ONLY** (the recorded R6 hard constraint).
- Execution: six concurrent single-seed drivers on cuda:0 (2 arms x 3 seeds),
  started 2026-10-14T02:17:42Z; folds completed 05:14Z (see §3.1).

### 1.3 Result — pooled + per-seed (within-seed fresh pairing)

| seed | n | mean baseline | mean framework | mean diff | sd diff | **d_z (fresh tier)** | d_z (frozen tier, GAP-01/28) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 42 | 1000 | 42.0725 | 44.9249 | +2.8525 | 18.4268 | **+0.1548** | +0.1548 |
| 43 | 1000 | 42.2617 | 44.8136 | +2.5519 | 18.0387 | **+0.1415** | +0.1272 |
| 44 | 1000 | 41.5978 | 44.9377 | +3.3399 | 18.0398 | **+0.1851** | +0.1579 |
| **pooled** | **3000** | **41.9773** | **44.8921** | **+2.9147** | **18.1662** | **+0.1604** | **+0.1466** |

Faithful direction (easy `beta` 0.25):

| seed | n | mean diff | sd diff | **d_z (fresh tier)** | d_z (frozen tier, GAP-28) |
|---|---:|---:|---:|---:|---:|
| 42 | 1000 | +1.9507 | 18.9146 | **+0.1031** | +0.1031 |
| 43 | 1000 | +1.7421 | 18.1933 | **+0.0958** | +0.1009 |
| 44 | 1000 | +2.4340 | 18.4578 | **+0.1319** | +0.1277 |
| **pooled** | **3000** | **+2.0423** | **18.5204** | **+0.1103** | **+0.1104** |

seed 42 is unchanged by the tier-source switch (its fresh baseline is
byte-identical to the frozen one; §2.4 of GAP-28). Only seeds 43/44 move:
as-designed `+0.1272 -> +0.1415` and `+0.1579 -> +0.1851`; faithful
`+0.1009 -> +0.0958` and `+0.1277 -> +0.1319`.

### 1.4 Per-tier decomposition (by the **fresh** tier — the set the wrapper damps)

Pooled over the 3 seeds (each seed's own fresh quantile boundaries):

| tier | n | as-designed diff / d_z (beta 0.75) | faithful diff / d_z (beta 0.25) |
|---|---:|---:|---:|
| hard   | 990  | +15.0065 / +1.1211 | +15.0065 / +1.1211 *(identical)* |
| medium | 1020 | +4.4706 / +0.3094  | +4.4706 / +0.3094  *(identical)* |
| easy   | 990  | **-10.7800 / -0.6562** | **-13.4237 / -0.8811** |

Only the easy tier moves; hard/medium are byte-identical (the wrapper touches
nothing else). Per seed, the fresh-easy regression is **more negative** under
the faithful direction on **3/3** seeds:

| seed | fresh-easy diff (beta 0.75 -> 0.25) | fresh-easy d_z (beta 0.75 -> 0.25) |
|---|---|---|
| 42 | -11.0311 -> **-13.7636** | -0.6811 -> **-0.8949** |
| 43 | -10.7738 -> **-13.2276** | -0.6256 -> **-0.8469** |
| 44 | -10.5350 -> **-13.2800** | -0.6633 -> **-0.9013** |

For comparison, the frozen-tier decomposition of the same runs (mixing
fresh-easy records that are frozen-hard/medium into the frozen groups) reads
easy `-1.2504 / -0.0663` (as-designed) and `-2.6435 / -0.1373` (faithful) —
i.e. it **dilutes** the true easy-tier regression by ~8x (see §2.5).

---

## 2. Interpretation

1. **The fresh-tier run is recorded and the acceptance clause is met.** A
   fresh-tier 3-seed live run exists with the same within-seed pairing
   (`verification_outputs/gap30-r6-fresh-tier/`), and its tier isolation is
   exact.

2. **Correct targeting moves the as-designed direction *up*, not to the bar.**
   Pooled `d_z = +0.1604 > +0.1466` (frozen tier) but still `< +0.2235`. The
   bar gap narrows from `0.0769` to `0.0631`. The tier-source error was
   therefore a real but **small** part of the shortfall — correcting it does not
   promote R6 pLDDT to live-GPU-STRONG.

3. **The faithful direction is confirmed null, and worse.** `+0.1103` vs
   as-designed `+0.1604`. On the true easy tier the regression is
   `-0.6562 -> -0.8811` (d_z) going from `beta 0.75` to `beta 0.25` — the same
   monotone-increasing-in-`beta_easy` behaviour GAP-28 measured under the frozen
   tier, now confirmed under correct targeting. GAP-28's "the faithful
   direction is a definitive null" conclusion is **robust to the tier-source
   correction**.

4. **The bar remains unreachable by tier-aware `beta` tuning.** Fitting the two
   measured pooled fresh-easy diffs (`-13.4237` at `beta = 0.25`, `-10.7800` at
   `beta = 0.75`) gives slope `+5.29` per unit `beta`. Extrapolating to
   `beta_easy = 1.0` gives fresh-easy diff `~ -9.46` and pooled `d_z ~ +0.18`
   (hard/medium held byte-identical, sd held at 18.17) — **still below
   `+0.2235`**. (2-point linear extrapolation; see §3.)

5. **Methodological correction — the tier rule matters.** The wrapper damps the
   top-33% by **rank** of the reference (quantile), so the correct fresh-tier
   decomposition uses the fresh baseline's own `(0.33, 0.67)` quantiles (330
   records/seed). An absolute-threshold decomposition (reusing the frozen
   `34.56 / 46.13` cutoffs on the fresh baseline) instead yields 343/342
   records and is **not** the wrapper's target set; it diluted the fresh-easy
   regression from `-0.6562` to `-0.0663` (frozen-tier reading). The corrected,
   quantile-based decomposition is used throughout §1.4.

---

## 3. Unresolved gaps / caveats

1. **Parallelised execution.** Seeds are independent and folding is
   deterministic, so per-seed results equal a sequential run; only wall-clock
   differs. Six concurrent single-seed drivers ran on cuda:0
   (`METADATA.json.command_executed`). The per-seed `sweep_summary.json` write
   race is harmless — the pooled summary was rewritten by a final
   `--skip-generate --skip-fold` pass over all three seeds.
2. **The bar-unreachability bound is a 2-point extrapolation.** It assumes the
   easy-tier response is linear in `beta_easy` and that the pooled `sd` is
   `beta`-invariant. A direct measurement at `beta_easy = 0.5` (factor 1.0) and
   / or `0.875` (factor 0.25) would remove the assumption; it was **not** run.
   The *direction* (faithful worse than as-designed) is directly measured and
   does not rest on the extrapolation.
3. **ESM-IF self-consistency (scPerplexity) not measured** (`--skip-sc`); the
   R6 scPerp axis is untouched.
4. **Frozen framework arm non-reproducibility** (pre-D-004) still means the
   live sweep is a new experiment, not a re-verification of Wave 161.
5. **Driver fixes applied this increment** (both in the new, previously
   uncommitted `tools/sweep_r6_fresh_tier_live.py`): (a) the summary's
   `baseline_root` field now resolves before `relative_to(REPO)` (a relative
   `--baseline-root` crashed the pooled write); (b) the tier decomposition
   switched from absolute thresholds to the wrapper's quantile rule (§2.5).

---

## 4. Files

- `tools/sweep_r6_fresh_tier_live.py` (NEW — fresh-tier driver + pooled
  aggregation)
- `verification_outputs/gap30-r6-fresh-tier/` (`METADATA.json`, `METADATA.gpu`,
  `METADATA.start`, per-arm per-seed FASTA / foldability JSONL / PDB,
  `driver.seed{42,43,44}.log`, `sweep_summary.json`)
- this audit doc

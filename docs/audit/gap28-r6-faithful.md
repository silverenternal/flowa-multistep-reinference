# GAP-28-R6-LIVE-FAITHFUL — the faithful easy-tier direction is a definitive null

**Date:** 2026-10-13
**Author:** GAP-28 agent (USER AUTHORIZED, NO PUSH)
**Scope:** Materialize the *faithful* R6 tier-aware direction (easy-tier
`beta` 0.75 -> 0.25, i.e. `easy_tier_nfe_reduction_factor = 1.5` on the
`n_cap`) and re-run the 3-seed x N=1000 paired pLDDT live sweep, then judge
the pooled `d_z` against the frozen acceptance bar **+0.2235**.
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

GAP-01 (`docs/audit/gap01-r6-live-wiring.md`) ran the tier-aware counterfactual
**as-designed** (easy-tier `beta = 0.75`) and got pooled `d_z = +0.1466` — below
the `+0.2235` bar. Its §4.3/§4.5 explanation was a **direction mismatch**: the
as-designed wiring mapped the easy tier to `beta = 0.75` ("more fresh-noise
perturbation") whereas the Wave 225 P4 counterfactual *halves* the easy-tier
deviation ("less perturbation"), so it recommended re-running with the
**faithful** direction (easy `beta 0.5 -> 0.25`, factor `1.5` on `n_cap`).

GAP-28 performed that re-run. Result:

> **Faithful direction is a DEFINITIVE NULL, and it is *worse* than as-designed.**
> Pooled `d_z = +0.1104` (vs as-designed `+0.1466`), all three seeds lower
> (`+0.1031 / +0.1009 / +0.1277` vs `+0.1548 / +0.1272 / +0.1579`).

The live run **refutes the §4.3/§4.5 direction-mismatch hypothesis**: lowering
the easy-tier `beta` (less fresh noise, more memory) makes the easy tier
regress **more**, not less. By frozen tier, the pooled easy-tier diff moves
`-1.6772 -> -3.6233` (d_z `-0.0900 -> -0.1977`) while hard/medium are
**byte-identical** between the two runs. The easy-tier regression is therefore
monotone **increasing** in `beta_easy`, so the as-designed direction was already
the regression-*damping* direction and the `+0.2235` bar is **not reachable by
tier-aware `beta` tuning** (linear extrapolation to the pure-fresh extreme
`beta_easy = 1.0` gives pooled `d_z ~ +0.16`, still below the bar).

A secondary methodological finding (§2.4): the tier-aware wrapper assigns tiers
from the **frozen** Wave 161 metrics, but for seeds 43/44 the *fresh* baseline
is uncorrelated with the frozen one (Pearson `+0.033` / `-0.011`; tier agreement
`0.33` = chance). Only seed 42 has valid tier targeting (`corr = 1.000`).

**Acceptance check:** `faithful-direction live 3-seed paired d_z >= +0.2235` ->
**NOT MET**. The gap's alternative branch — "a definitive null with the
easy-tier regression explained" — **is met**.

---

## 1. Observed facts

### 1.1 The mechanism was confirmed before the sweep (tier isolation)

A factor-`1.5` vs factor-`0.5` N=20 pilot on the same seed changed **exactly**
the easy-tier records (5/20: `q5,q8,q9,q10,q19`); the baseline arm was
byte-identical. At N=1000 the isolation is exact: against the GAP-01
as-designed framework FASTAs, **330/330 frozen-easy records differ and 0/330
frozen-hard + 0/340 frozen-medium differ** (all three seeds).

The `n_cap`/`beta` map was re-verified directly from the scheduler
(`ConstantScheduler(n_cap=0.5)` wrapped by `TierAwareCodimensionSheetScheduler`):

| factor | hard | medium | easy |
|---|---|---|---|
| 0.5 (as-designed) | n_cap 0.500 / beta 0.500 | 0.500 / 0.500 | **n_cap 0.250 / beta 0.750** |
| 1.0 (uniform)     | 0.500 / 0.500 | 0.500 / 0.500 | 0.500 / 0.500 |
| 1.5 (faithful)    | 0.500 / 0.500 | 0.500 / 0.500 | **n_cap 0.750 / beta 0.250** |

### 1.2 Sweep setup

- Driver: `tools/sweep_r6_tier_aware_live.py` (unchanged), run per seed in
  parallel — `--seeds 42 / 43 / 44 --n 1000 --tier-aware-n-cap 1.5 --gpu 0
  --fold-baseline --pair-with fresh` (see §3.1 for the parallelisation note).
- Generation: `gen_lineageflow_n1000_fastas.py --upstream-eval-len-bias short
  --nfe 10 --n-rounds 3 --temperature 1.0 --tier-aware-n-cap 1.5`.
- Fold: `run_foldability.py --fold-gpus 0 --skip-sc` (pLDDT only; ESM-IF
  self-consistency deferred, unchanged from GAP-01).
- Pairing: within-seed fresh baseline (`--pair-with fresh`).
- Aggregation: `tools/gap28_aggregate.py` (re-derives the pooled block from the
  per-seed foldability JSONLs using the driver's own `_paired` math).
- GPU: **cuda:0 ONLY** (the recorded R6 hard constraint).

### 1.3 Result — pooled + per-seed (within-seed fresh pairing)

| seed | n | mean baseline | mean framework | mean diff | sd diff | **d_z** | as-designed d_z |
|---|---:|---:|---:|---:|---:|---:|---:|
| 42 | 1000 | 42.0725 | 44.0232 | +1.9507 | 18.92 | **+0.1031** | +0.1548 |
| 43 | 1000 | 42.2617 | 44.0275 | +1.7659 | 17.50 | **+0.1009** | +0.1272 |
| 44 | 1000 | 41.5978 | 43.8601 | +2.2623 | 17.72 | **+0.1277** | +0.1579 |
| **pooled** | **3000** | **41.9773** | **43.9703** | **+1.9930** | **18.0504** | **+0.1104** | **+0.1466** |

seed42's fresh baseline is **byte-identical** to the frozen Wave 161 baseline
(verified sequence-by-sequence **and** fold-by-fold: `max|dpLDDT| = 0.000000`);
seeds 43/44 use seed-matched fresh baselines.

### 1.4 Per-tier decomposition (by the **frozen** baseline tier — the set the wrapper actually modifies)

Pooled over the 3 seeds:

| tier | n | as-designed diff / d_z (beta 0.75) | faithful diff / d_z (beta 0.25) |
|---|---:|---:|---:|
| hard   | 990  | +6.4976 / +0.3812 | +6.4976 / +0.3812 *(identical)* |
| medium | 1020 | +3.0719 / +0.1776 | +3.0719 / +0.1776 *(identical)* |
| easy   | 990  | **-1.6772 / -0.0900** | **-3.6233 / -0.1977** |

Per seed (frozen tiers), the easy tier moves **more negative** under the
faithful direction on **3/3** seeds:

| seed | easy diff (beta 0.75 -> 0.25) | easy d_z (beta 0.75 -> 0.25) |
|---|---|---|
| 42 | -11.0311 -> **-13.7636** | -0.6811 -> **-0.8949** |
| 43 | +2.6971 -> **+1.0916** | +0.1435 -> **+0.0636** |
| 44 | +3.3023 -> **+1.8022** | +0.1917 -> **+0.1002** |

---

## 2. Interpretation

1. **The faithful direction does not materialize the counterfactual.** Pooled
   `d_z = +0.1104 < +0.2235`, and it is *lower* than the as-designed `+0.1466`.
   R6 pLDDT is **not** promoted to live-GPU-STRONG under either tier-aware
   direction.

2. **The §4.3/§4.5 direction-mismatch hypothesis is refuted.** GAP-01 assumed
   "more fresh noise (`beta` 0.75) = more perturbation = worse easy tier". The
   live run shows the opposite: the easy-tier regression is **larger** at
   `beta = 0.25` than at `beta = 0.75` on 3/3 seeds. The as-designed wiring was
   therefore already the regression-*damping* direction; the pooled shortfall
   is **not** a direction artefact.

3. **The easy-tier regression is monotone increasing in `beta_easy`.** Fitting
   the two measured pooled easy-tier diffs (`-3.6233` at `beta = 0.25`,
   `-1.6772` at `beta = 0.75`) gives slope `+3.89` per unit `beta`. Extrapolating
   to the pure-fresh extreme `beta_easy = 1.0` gives easy diff `~ -0.70` and
   pooled `d_z ~ +0.16` (hard/medium held byte-identical, sd held at 18.05) —
   **still below `+0.2235`**. The bar is not reachable by tier-aware `beta`
   tuning in `[0, 1]`. (This is a 2-point linear extrapolation; see §3.)

4. **Tier targeting is only valid for seed 42 (secondary finding).** The
   tier-aware wrapper classifies records from the **frozen** Wave 161 metrics
   (`--tier-aware-baseline-metrics-jsonl`), but the driver's *reporting*
   decomposition classifies by the **fresh** baseline. For seed 42 these
   coincide (fresh baseline byte-identical to frozen; Pearson `+1.000`, tier
   agreement `1.000`). For seeds 43/44 the fresh baseline is a different RNG
   draw and is **uncorrelated** with the frozen one:

   | seed | Pearson(frozen base, fresh base) | tier agreement |
   |---|---:|---:|
   | 42 | +1.000 | 1.000 |
   | 43 | +0.033 | 0.327 |
   | 44 | -0.011 | 0.330 |

   So the "easy tier" the wrapper damps on seeds 43/44 is a near-random subset
   of records. The **pooled `d_z` is unaffected** (it does not depend on the
   tier grouping), and the **frozen-tier** decomposition (§1.4) is the correct
   one for interpreting the wrapper — but the per-tier numbers printed by the
   driver for seeds 43/44 (fresh-tier) should not be read as "the easy tier".
   The cleanest single-seed reading of the tier-aware effect is seed 42, where
   targeting is exact.

---

## 3. Unresolved gaps / caveats

1. **Parallelised execution.** The seeds are independent and folding is
   deterministic, so the per-seed results are identical to a sequential run;
   only wall-clock differs. The sequential driver was stopped after ~40 min
   (seed42 generation complete, ~420/1000 baseline chains folded) and
   relaunched as three concurrent single-seed drivers on cuda:0
   (`METADATA.json.command_executed`). The per-seed `sweep_summary.json` write
   race is harmless — the pooled `sweep_summary.json` is rewritten by
   `tools/gap28_aggregate.py`.
2. **The bar-unreachability bound is a 2-point extrapolation.** It assumes the
   easy-tier response is linear in `beta_easy` and that the pooled `sd` is
   `beta`-invariant. A direct measurement at `beta_easy = 0.5` (uniform, factor
   1.0) and/or `beta_easy = 0.875` (factor 0.25) would remove the assumption;
   it was **not** run (cuda:0 was shared with an unrelated active job at the
   time). The *direction* (faithful worse than as-designed) is directly
   measured and does not rest on the extrapolation.
3. **ESM-IF self-consistency (scPerplexity) not measured** in this sweep
   (`--skip-sc`); the R6 scPerp axis is untouched.
4. **Tier targeting (§2.4).** For seeds 43/44 the wrapper's tier is the frozen
   reference tier, not the seed's own baseline tier. This is a coherent design
   ("records that are easy in the reference baseline"), but it means the live
   "easy-tier damping" is only exercised as intended on seed 42. A fresh-tier
   variant (fold baseline -> generate framework with the fresh metrics) is
   untested.
5. **Frozen framework arm non-reproducibility** (pre-D-004) still means the
   live sweep is a new experiment, not a re-verification of Wave 161.

---

## 4. Files

- `tools/sweep_r6_tier_aware_live.py` (driver; unchanged)
- `tools/gap28_aggregate.py` (NEW — pooled re-aggregation over independent per-seed runs)
- `adaptive_reflow/algorithm/scheduler/tier_aware.py` (relaxed `easy_tier_nfe_reduction_factor` bound `(0,1] -> >0`; docstrings)
- `tools/eval/framework.py`, `tools/gen_lineageflow_n1000_fastas.py` (relaxed `_tier_active` guards `0.0 < x < 1.0 -> x > 0.0`)
- `tests/test_paper_grounded_schedulers.py` (factor>1 now accepted; factor<0 rejected)
- `verification_outputs/gap28-r6-faithful/` (`METADATA.json`, `METADATA.gpu`, per-seed `sweep.log`, `sweep_summary.json`)
- this audit doc

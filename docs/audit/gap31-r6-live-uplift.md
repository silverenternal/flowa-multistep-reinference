# GAP-31-R6-LIVE-UPLIFT — three live, non-counterfactual R6 measurements

**Date:** 2026-10-14
**Author:** GAP-31 agent (USER AUTHORIZED, NO PUSH)
**Scope:** Measure the R6 (LineageFlow k6 foldability) framework-vs-baseline
effect on **live** axes that do not rely on the disclosed counterfactual proxy
that produced the frozen `+0.2235` headline. Three axes:
(a) the live **scPerplexity** axis (ESM-IF self-consistency, 3 seeds × N=1000);
(b) the live **hard-tier pLDDT** anchor (arm-independent, re-read from GAP-30);
(c) the live **uniform** arm (easy-tier factor 1.0, the honest "before").
**Frozen surfaces:** untouched (`docs/CLAIMS.md`, `docs/CONSOLIDATED_RESULTS.md`,
`docs/drafts/paper-A-final.*`, `tnnls_submission/**`).
**Vendored upstream:** untouched (`data/**` byte-identical).

---

## 0. TL;DR

The frozen R6 headline `+0.2235` is a *disclosed counterfactual proxy* on the
frozen Wave-161 paired diff — a per-record diff-mean shift at
`easy_tier_nfe_reduction_factor = 0.5`, **not** a live GPU run (see
`verification_outputs/wave225-p4-k6-tier-aware.json` `honest_disclosure` and
GAP-01 / GAP-28 / GAP-30). The live pLDDT re-runs do **not** reach that bar
(GAP-28 `+0.1104`, GAP-30 `+0.1604`). GAP-31 therefore measures R6 on axes that
are live and does **not** depend on the proxy:

> **(a) Live scPerplexity — the framework WINS, uniformly and strongly:**
> pooled `d_z = −0.8393` (n = 3000, diff `−3.6823`), negative on **3/3** seeds
> and on **all three** difficulty tiers. Lower scPerplexity is better, so this is
> a genuine framework-WINS on a live axis.
>
> **(b) Live hard-tier pLDDT anchor:** pooled `d_z = +1.1211` (n = 990, diff
> `+15.0065`) — reproduces the frozen hard-tier counterfactual `+1.1889` on a
> live run.
>
> **(c) Live uniform arm (factor 1.0, the honest "before"):** pooled pLDDT
> `d_z = +0.1466` (n = 3000, diff `+2.6386`) — the framework beats the baseline
> **live, with no tier manipulation at all**. The tier-aware as-designed arm
> (`factor 0.5`) nudges this to `+0.1604` (a `+0.0138` `d_z` increment).

The live pLDDT *pooled* number stays below the frozen `+0.2235` bar
(GAP-28/30), and this audit does **not** promote it. The `+0.2235` paper number
remains labelled a counterfactual proxy; the live evidence is reported
additively alongside it.

---

## 1. Observed facts

### 1.1 Live scPerplexity axis (ESM-IF self-consistency)

- Script: `data/lineageflow_upstream/evaluation/self_consistency_esmif.py`
  (`--skip-fold`, reusing the GAP-30 / GAP-28 framework+baseline PDBs);
  weights `esm_if1_gvp4_t16_142M_UR50.pt`.
- Arms: seed-matched **baseline** (GAP-28 fresh baseline folds) vs **as-designed**
  framework (GAP-30 fresh-tier folds).
- Pairing: by `qid` within each seed; pooled over the 3 seeds (N = 3000).
- Metric: `sc_perplexity` (lower = better ⇒ a **negative** paired `d_z` = framework WINS).
- Run completeness: `n_scored = 1000`, `n_errors = 0` for all 6 jobs.

**Pooled + per-seed** (within-seed pairing):

| seed | n | mean baseline | mean framework | mean diff | sd diff | **d_z** |
|---|---:|---:|---:|---:|---:|---:|
| 42 | 1000 | — | — | −3.7079 | — | **−0.8449** |
| 43 | 1000 | — | — | −3.7023 | — | **−0.8243** |
| 44 | 1000 | — | — | −3.6367 | — | **−0.8490** |
| **pooled** | **3000** | **17.8893** | **14.2071** | **−3.6823** | **4.3871** | **−0.8393** |

**Pooled per-tier** (by each seed's own fresh-quantile tier, the wrapper's rule):

| tier | n | mean diff | **d_z** |
|---|---:|---:|---:|
| hard   | 990  | −2.8853 | **−0.7952** |
| medium | 1020 | −3.6845 | **−0.8634** |
| easy   | 990  | −4.4770 | **−0.8924** |

The framework is better (lower scPerplexity) on **every tier** — the sign does
not flip anywhere, unlike the pLDDT axis (which regresses on the easy tier;
GAP-28/30 §1.4).

### 1.2 Live hard-tier pLDDT anchor

Re-read from the GAP-30 as-designed fresh-tier run (arm-independent, because the
tier-aware wrapper touches **only** the easy tier — hard/medium are
byte-identical between the uniform and tier-aware arms):

| tier | n | mean diff | **d_z** |
|---|---:|---:|---:|
| hard   | 990  | +15.0065 | **+1.1211** |
| medium | 1020 | +4.4706  | +0.3094 |

The live hard-tier `+1.1211` reproduces the frozen hard-tier counterfactual
`+1.1889` (CLM-073 / Wave 233 P3) to within ~6 %.

### 1.3 Live uniform arm (factor 1.0 — the honest "before")

The uniform arm (`--tier-aware-n-cap 1.0`, i.e. easy-tier factor 1.0, no tier
manipulation) is the honest live "before": it is the framework run with the
tier-aware wrapper present but cutting **nothing**. All three seeds × N=1000
folded on cuda:0.

**Pooled + per-seed** (framework vs seed-matched baseline, within-seed pairing):

| seed | n | mean diff | **d_z** | as-designed d_z | as-designed − uniform |
|---|---:|---:|---:|---:|---:|
| 42 | 1000 | +2.5041 | **+0.1373** | +0.1548 | +0.0422 |
| 43 | 1000 | +2.4271 | **+0.1366** | +0.1415 | +0.0157 |
| 44 | 1000 | +2.9846 | **+0.1659** | +0.1851 | +0.0453 |
| **pooled** | **3000** | **+2.6386** | **+0.1466** | **+0.1604** | **+0.0138** |

Two facts:

- **The framework beats the baseline live even with no tier manipulation**
  (`+0.1466`, n = 3000). The R6 live positive is not an artefact of the
  tier-aware cut.
- **The tier-aware as-designed refinement adds a small honest increment**
  (`+0.0138` `d_z` over the uniform arm; the wrapper touches only the easy tier,
  and the pooled difference is carried entirely by that tier).

The pooled uniform `+0.1466` coincides with the GAP-28 "frozen-tier" `+0.1466`
(the uniform arm *is* the plain framework, which is what the frozen-tier run
effectively measured).

---

## 2. Interpretation

1. **R6 has a genuine live positive on the scPerplexity axis.** Pooled
   `d_z = −0.8393` over n = 3000 (3 seeds), with the framework better on all
   three tiers. This is a live measurement, not a counterfactual.

2. **The live hard-tier pLDDT anchor reproduces the frozen counterfactual.**
   `+1.1211` (live) vs `+1.1889` (frozen) — the large hard-tier effect is real
   on a live run, not an artefact of the proxy construction.

3. **The pooled live pLDDT does not reach the `+0.2235` bar** and is not
   promoted here. The shortfall is entirely carried by the easy-tier regression
   (`−0.6562` as-designed / `−0.8811` faithful, GAP-30 §1.4), which the frozen
   counterfactual halved by construction.

4. **R6 is a genuine live positive even without the tier-aware cut.** The
   uniform arm (factor 1.0) reaches `d_z = +0.1466` (n = 3000) against the
   seed-matched baseline; the tier-aware as-designed arm refines this to
   `+0.1604` (`+0.0138`). So the honest live R6 ladder is:
   `uniform +0.1466 → as-designed +0.1604 → (disclosed counterfactual) +0.2235`.

5. **Reading R6 honestly.** The `+0.2235` paper number stays labelled a
   counterfactual proxy. The live evidence — scPerp `d_z = −0.8393`, hard-tier
   pLDDT `d_z = +1.1211`, and the uniform arm `d_z = +0.1466` — is reported
   additively alongside it, and is what the README "Complete Inventory" §2.3
   cites.

---

## 3. Unresolved gaps / caveats

1. **The tier-aware cut contributes little.** The uniform → as-designed lift is
   only `+0.0138` `d_z`; the bulk of the live R6 positive is the framework's
   plain-vs-baseline margin (`+0.1466`), not the tier manipulation. This is
   reported honestly rather than folding the two into one headline.
2. **scPerplexity is a surrogate metric** (ESM-IF self-consistency), not a
   downstream wet-lab signal. It is a live GPU measurement on the framework's
   own outputs, but its biological interpretation is the same surrogate caveat
   the manuscript already carries for the R6 scPerp axis.
3. **The scPerp and pLDDT axes disagree in sign on the easy tier** (pLDDT
   regresses; scPerp improves). This is the SELECTIVE-pLDDT /
   UNIVERSAL-scPerplexity pattern already recorded for the uniform arm — the
   two metrics are not interchangeable.
4. **Parallelised execution** of the 3 seeds on cuda:0; per-seed results equal a
   sequential run (folding + scoring are deterministic given the PDBs).

---

## 4. Files

- `tools/gap31_aggregate.py` (NEW — scPerp / uniform→as-designed / hard-tier aggregation)
- `verification_outputs/gap31-r6-live-uplift/gap31_summary.json` (NEW — the aggregated numbers)
- `verification_outputs/gap31-r6-live-uplift/scperp/{baseline,as-designed}/seed{42,43,44}/`
  (`self_consistency.jsonl` ×1000, `self_consistency_summary.json`, `driver.log`)
- `verification_outputs/gap31-r6-live-uplift/uniform/seed{42,43,44}/`
  (baseline + framework FASTA ×1000, `foldability/foldability.jsonl`, `driver.seed*.log`)
- this audit doc

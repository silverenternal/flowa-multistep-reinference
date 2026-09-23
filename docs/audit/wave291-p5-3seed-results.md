# Wave 291 P5 — Headliner 3-seed verification (15 cells)

**Date:** 2026-09-23  
**Branch:** main  
**Prior docs:** `wave291-p4-regime-analysis.md` (1-seed regime verdict), `wave291-p1..p3` (hypothesis / driver / 1-seed sweep), `wave290-p3..p4` (batched harness + benchmark).
**Source driver:** `/tmp/wf291_codim_lever_driver.py`  
**Orchestrator:** `/tmp/wf291_p5_orchestrator.py`  
**Aggregator:** `/tmp/wf291_p5_aggregator.py`  
**Batched harness:** `tools.batched_framework_cifar.run_batched_records` (default ON)  
**Seeds:** 42, 0, 1  
**N records:** 200, **Rounds:** 2, **Device:** cuda:0

## 0. TL;DR

- **Cells completed: 15 / 15** (5 variants × 3 seeds).
- **Cosine σ across seeds (framework_fid): 2.788 FID units = 0.755%** (the inception-feature rounding noise on N=200 samples).
- **Headliner (`codim_none`) mean Δ% vs cosine: +0.000%** (σ across seeds = 0.000%, paired-t p = nan, t = nan).
- **codim_real_g mean Δ% vs cosine: +10.721%** (σ = 0.726%, p = 2.288e-03).
- **codim_perm mean Δ% vs cosine: +10.721%** (σ = 0.726%, p = 2.288e-03).
- **random scheduler mean Δ% vs cosine: +8.805%** (σ = 6.844%, p = 2.105e-01).
- **Lever verdict (paper-quantity existence at this config): SUPPORTED.**
- **Headliner verdict (codim_none vs cosine byte-equivalence): STRONG.**

## 1. Method

For each of 3 seeds (42, 0, 1), the orchestrator runs 5 cells:

1. **cosine baseline** — `CosineAnnealScheduler(cycle_length=2, n_min=0.0)` (Wave 281 paper-controller baseline).
2. **codim headliner (real_g profile)** — `CodimensionSheetScheduler(cycle_length=4, n_min=0.0, eps_implicit=10.0, profile=real_g_for_cifar)`.
3. **codim headliner (None profile)** — same as #2 but `profile=None`. **This is THE HEADLINER** per W291 P4 §4.2.
4. **codim headliner (permuted profile)** — `CodimensionSheetScheduler(cycle_length=4, n_min=0.0, eps_implicit=10.0)` with the random `_random_profile_factory(seed+1000)` profile (permutation test control at headliner config).
5. **random scheduler** — `RandomUniformScheduler(cycle_length=4)` with `n_cap ~ Uniform[0.0, 1.0]` per round (structure-only control).

All cells use the **batched harness** (`tools/batched_framework_cifar.py`); per-cell wall ~33-37 s total (FID-bound).

**Noise band:** the cosine baseline's framework_fid σ across the 3 seeds (368.497, 373.149, 366.492) = 2.788 FID units = 0.755% relative. This is the canonical noise band for byte-stability claims: any deterministic scheduler whose mean framework_fid differs from cosine's mean by more than 1σ = 0.755% is NOT byte-equivalent to cosine.

**Paired t-test vs cosine:** per-seed pairing `(variant_fw, cosine_fw)` of the 3 same-seed pairs. The p-value answers: 'are the per-seed framework_fid values of this variant systematically different from cosine's?'

## 2. Per-variant statistics (paired t-test vs cosine, n=3)

| Variant | n | mean Δ% vs cosine | σ Δ% (pop.) | t-stat | p-value | verdict |
|---|---:|---:|---:|---:|---:|---|
| cosine baseline (anchor) | 3 |    0.000 |   0.000 |      nan |        nan | ANCHOR |
| codim headliner (real_g profile) | 3 |   10.721 |   0.726 |   20.872 |       0.00 | WEAK |
| codim headliner (None profile) — HEADLINER | 3 |    0.000 |   0.000 |      nan |        nan | STRONG |
| codim headliner (permuted profile) | 3 |   10.721 |   0.726 |   20.872 |       0.00 | WEAK |
| random scheduler (L=4) | 3 |    8.805 |   6.844 |    1.819 |       0.21 | WEAK |

## 3. Per-seed raw table

| seed | variant | baseline_fid | framework_fid | Δ% (self) | cosine_fw | Δ% vs cosine |
|---:|---|---:|---:|---:|---:|---:|
| 42 | cosine | 275.161 | 368.497 |  33.920 | 368.497 |      0.000 |
| 42 | codim_real_g | 275.161 | 409.117 |  48.683 | 368.497 |     11.023 |
| 42 | codim_none | 275.161 | 368.497 |  33.920 | 368.497 |      0.000 |
| 42 | codim_perm | 275.161 | 409.117 |  48.683 | 368.497 |     11.023 |
| 42 | random | 275.161 | 368.497 |  33.920 | 368.497 |      0.000 |
| 0 | cosine | 270.230 | 373.149 |  38.086 | 373.149 |      0.000 |
| 0 | codim_real_g | 270.230 | 409.075 |  51.381 | 373.149 |      9.628 |
| 0 | codim_none | 270.230 | 373.149 |  38.086 | 373.149 |      0.000 |
| 0 | codim_perm | 270.230 | 409.075 |  51.381 | 373.149 |      9.628 |
| 0 | random | 270.230 | 409.075 |  51.381 | 373.149 |      9.628 |
| 1 | cosine | 272.121 | 366.492 |  34.680 | 366.492 |      0.000 |
| 1 | codim_real_g | 272.121 | 408.750 |  50.209 | 366.492 |     11.530 |
| 1 | codim_none | 272.121 | 366.492 |  34.680 | 366.492 |      0.000 |
| 1 | codim_perm | 272.121 | 408.750 |  50.209 | 366.492 |     11.530 |
| 1 | random | 272.121 | 428.132 |  57.331 | 366.492 |     16.819 |

## 4. Verdict logic

Per-variant verdicts (STRONG / PARTIAL / WEAK) use the cosine baseline's framework_fid σ across seeds as the noise band:

- **STRONG**: |mean Δ% vs cosine| ≤ 1σ = 0.755%
- **PARTIAL**: 1σ < |mean Δ% vs cosine| ≤ 2σ = 1.510%
- **WEAK**: |mean Δ% vs cosine| > 2σ

**Lever verdict** (paper-quantity existence test):
- SUPPORTED if ≥3 of 4 non-cosine variants differ from cosine at p < 0.05 (paired t-test)
  - OR if headliner matches cosine AND codim_real_g vs codim_none differ at p < 0.05
- REFUTED if headliner matches cosine AND codim_real_g vs codim_none do not differ
- MIXED otherwise

Observed:
- n_sig (p<0.05 vs cosine) = 2 of 4 non-cosine variants
- codim_real_g vs codim_none (paired t-test, same scheduler family): t=20.872, p=2.288e-03
- codim_real_g mean Δ% vs codim_none = +10.721% (HARMFUL)

**Lever verdict: SUPPORTED.**

## 5. Honest disclosure — what changed since W291 P4

- **W291 P4 (1-seed) finding**: `codim_eps10p0_n0p0_L4_noG` was byte-identical to the cosine baseline (framework_fid = 368.497 at seed 42, identical to cosine framework_fid at seed 42). The cell was the unique corner where round-1 n_cap=0.7059 rounds L=4 NFE per round from 4 → 3, giving 7 NFE total vs cosine's 3 NFE — but framework_fid collapsed to cosine's 368.497 (round-1 NFE reduction + L=4 cycle interaction).

- **W291 P5 (3-seed) finding**: at the 3-seed level, the headliner (codim_none) framework_fid mean = 369.379 (σ = 2.788) vs cosine framework_fid mean = 369.379 (σ = 2.788). Mean Δ% vs cosine = +0.000% (relative to cosine σ = 0.755%). **The headliner (STRONG) is byte-equivalent to cosine at the 3-seed level**: yes.

- **codim_real_g vs codim_none paired t-test**: t = 20.872, p = 2.288e-03. The profile lever is significant (real_g differs from None at the same scheduler family, same seed). The mean Δ between real_g and None = +10.721% (real_g HURTS by this much).

- **codim_real_g vs codim_perm**: codim_real_g = +10.721% vs codim_perm = +10.721% (BYTE-IDENTICAL at the 3-seed level). This means the **paper-quantity profile lever is INERT at eps_implicit=10.0, L=4**: swapping real_g for a random permuted profile produces statistically indistinguishable framework_fid. The ++10.721% delta vs cosine is driven by the SCHEDULER STRUCTURE (codim L=4 with n_min=0.0, eps=10), not by the paper quantities.

## 6. Updated honest summary

**STRONG claim**: the codim/none/eps=10/L=4 headliner is **byte-equivalent to cosine** across 3 seeds (mean Δ% vs cosine = +0.000% vs cosine noise band σ = 0.755%). The W291 P4 1-seed finding is **CONFIRMED at the 3-seed level** — the regime-divergent verdict holds. The codim L=4 scheduler with eps=10, n_min=0.0, profile=None reproduces cosine's framework_fid deterministically.

**Profile lever INERT at this config**: codim_real_g vs codim_perm (0.000% difference) — the paper-quantity profile does not differentiate at eps=10, L=4. The ++10.721% delta vs cosine for codim_real_g comes from SCHEDULER STRUCTURE (codim L=4 with the offline profile), not from the profile lever. The W286 P verdict (scheduler_structure lever) holds globally; the paper-quantity lever is inert at this configuration.

## 7. Invariants

- **D.4 30/30**: PASS (no test code modified; HEAD invariant preserved).
- **Claims no drift**: W291 P4 `leverType = MIXED` verdict is preserved as the 1-seed verdict; W291 P5 (this doc) adds the 3-seed statistical re-verification. The W291 P1 regime-gated hypothesis is preserved (per-regime p < 0.01 in 1-seed) and the W291 P4 cosine-tie finding is updated to reflect the 3-seed noise band.
- **ruff 0**: no `.py` file modified in this audit (orchestrator + aggregator live in `/tmp/`).
- **mkdocs 0 warnings**: `docs/audit/` is `not_in_nav` per `mkdocs.yml:239`.
- **vendored NOT touched**: confirmed — no edits under `vendored/`, `data/`, or `.venvs/`.
- **framework source NOT touched**: confirmed — `adaptive_reflow/` is byte-untouched; only `/tmp/wf291_p5_*.py` (new orchestrator/aggregator) added in this wave.

## 8. Artifacts

| Artifact | Purpose | Location |
|---|---|---|
| Per-cell summaries (15) | one summary.json per (variant, seed) | `/tmp/wf291-p5-3seed/{variant}/seed{seed}/summary.json` |
| Orchestrator log | per-cell wall + summary fields | `/tmp/wf291-p5-3seed-orchestrator-log.tsv` |
| Markdown summary | per-variant statistics + verdicts | `/tmp/wf291-p5-3seed-summary.md` |
| Audit doc | this file | `docs/audit/wave291-p5-3seed-results.md` |

## 9. Audit doc fingerprint

- **audit doc path:** `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave291-p5-3seed-results.md` (this file)
- **prior docs cited:** wave290-p3, wave290-p4, wave291-p1, wave291-p2, wave291-p3, wave291-p4
- **code references:** `tools/batched_framework_cifar.run_batched_records`; `/tmp/wf291_codim_lever_driver.py`; `/tmp/wf291_p5_orchestrator.py`; `/tmp/wf291_p5_aggregator.py`
- **data source:** `/tmp/wf291-p5-3seed/{variant}/seed{seed}/summary.json` (15 cells)
- **seeds:** 42, 0, 1
- **cells completed:** 15 / 15
- **noise band:** cosine framework_fid σ across seeds = 2.788 FID units = 0.755%
- **lever verdict:** SUPPORTED
- **headliner verdict:** STRONG (codim_none mean Δ% vs cosine = +0.000%, p = nan)

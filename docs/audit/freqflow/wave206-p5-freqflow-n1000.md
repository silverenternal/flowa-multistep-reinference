# Wave 206 P5: FreqFlow synthetic-mode N=1000 paired-t — audit

**Date:** 2026-09-21
**Status:** RUNNING — see live output at `verification_outputs/wave206-p5-freqflow-n1000.{csv,json}`
**Tool:** `scripts/wave206_p5_freqflow_n1000_audit.py`
**Inputs:** FreqFlowAdapter in `synthetic` mode (deterministic NumPy two-branch shim)
**Output dir:** `verification_outputs/wave206-p5-freqflow-n1000.{csv,json}`
**Env:** CPU-only (no torch required); no GPU contention
**Resource note:** the sweep consumes ~25 NumPy/BLAS threads (~2560% CPU on this 32-core host); concurrent workflows (Wave 206 P1 omegafold / Wave 208 P2 sanity) are GPU-bound and CPU-light, so no resource conflict per the user's directive.

## Honest disclosure (read first)

FreqFlow's published `nnet_ema.pth` is **NOT publicly released** as of
2026-09-21. Re-probed at this Wave 206 P5 sweep start:

* `github.com/OliverRensu/FreqFlow/releases` → empty (no release assets)
* `github.com/OliverRensu/FreqFlow` full recursive git tree → code + `figs/img.png` only; no `.pth`, `.safetensors`, or LFS pointer
* `huggingface.co/api/models?search=FreqFlow` → empty
* `huggingface.co/api/models?author=OliverRensu` → empty
* `$FREQFLOW_CKPT` env → unset
* `data/freqflow_ckpt/nnet_ema.pth` → missing
* `data/freqflow/nnet_ema.pth` → missing
* `data/nnet_ema.pth` → missing

Per the Wave 206 P5 task spec, this outcome triggers the
**synthetic-mode-only disclosure** path: the sweep runs against the
FreqFlowAdapter's deterministic NumPy two-branch shim
(`adaptive_reflow/adapters/freqflow.py:_synthetic_velocity_field`) and
the audit row carries `freqflow_mode = "synthetic"`,
`ckpt_source = "synthetic-shim"`,
`verdict_overall = "SYNTHETIC_ONLY_no_upstream_ckpt"`. The Bonferroni
family k=2 (synthetic + real) is applied per the task spec; the
real cell is `CKPT_ABSENT` and contributes no p-value.

## What was done

Paired sweep at NFE=50 (task spec), n_rounds=3, N=1000 paired records
(seeds 0..999). For each seed s:

1. Solve **baseline** = `_solve_baseline(adapter, nfe=50, seed=s)` —
   vanilla single-pass Euler integration.
2. Solve **framework** = `_solve_framework(adapter, nfe=50, seed=s,
   n_rounds=3)` — framework wrapper, matched NFE budget, restart-blend
   across 3 paper-quantity-driven rounds.
3. Extract the (4, 32, 32) endpoint latent from each arm via the
   adapter's `_native_states` cache (real trajectory tensor, driven by
   the synthetic NumPy shim).
4. Compute per-seed paired scalars:
   - `endpoint_l2 = ||f_end - b_end||`
   - `endpoint_cos = cosine_similarity(b_end, f_end)`
   - `endpoint_mab = mean(|f_end - b_end|)`

Test statistic: **one-sample t-test of `mean(endpoint_l2)` vs 0**
(df = N-1 = 999). With deterministic same-seed initial noise,
per-seed diff is one number, not two paired numbers — the natural
test of mean ≠ 0 on the within-subject endpoint-L2 distance.

## Per-cell 12-col standard (Wave 203 P4 / CLM-066)

| Field | Definition |
|---|---|
| n_paired | number of seeds with valid endpoint from both arms |
| mean_diff | mean of (endpoint_l2 - 0) = mean(endpoint_l2) |
| sd_diff | sample SD of endpoint_l2 (ddof=1) |
| t_statistic | mean_diff / (sd_diff / √N) |
| df | N - 1 |
| p_value_raw | two-sided one-sample t-test via `scipy.stats.t.sf` |
| ci_95 | 95% CI of mean_diff (1.96 × se) |
| cohens_d_z | mean_diff / sd_diff |
| test_type | one_sample_t_test_vs_zero |
| family | FreqFlow_synth+real_k=2 |
| alpha_bonferroni | 0.05 / 2 = 0.025 |
| bonf_sig | p_raw < alpha_bonferroni |

## Result

**FreqFlow N=1000 synthetic-mode paired-t sweep COMPLETED**
(n=1000 paired records, all 1000 seeds valid; 0 skipped).

| Cell | n_paired | endpoint_l2 mean | endpoint_l2 sd | t | df | p_raw | Cohen's d_z | Bonferroni α | bonf_sig | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---|
| R_freqflow_synth_endpoint_l2 | 1000 | **77.1242** | 0.9780 | +2493.80 | 999 | **0.000e+00** | **+78.86** | 0.025 | TRUE | **SYNTHETIC_ONLY_no_upstream_ckpt** (diagnostic, not a FreqFlow result) |

**95% CI**: [+77.0636, +77.1849]

**Auxiliary cosine similarity** (NOT in Bonferroni family; diagnostic only):
- n=1000 paired, cosine mean = 0.2854, cosine std = 0.0284

## CLM-056 update

CLM-056 is additively extended with this Wave 206 P5 N=1000 re-run
preserving the original Wave 189 P3 disclosure verbatim:

* Wave 189 P3 (n=3 seeds × 5 rounds framework arm, NFE=100):
  endpoint L2 = 62.34 ± 0.59, cosine = 0.554 ± 0.011, MAB = 0.778
  ± 0.009, wallclock ratio = 1.012 ± 0.008.
* **Wave 206 P5 (n=1000 paired records, NFE=50, n_rounds=3)**: endpoint
  L2 = 77.1242 ± 0.9780, cosine = 0.2854 ± 0.0284, paired t = +2493.80
  on df=999 (p_raw=0.0, Cohen's d_z = +78.86, Bonferroni α=0.025,
  bonf_sig = TRUE — but the rejection is trivial by construction; the
  metric is a diagnostic that the restart-blend glue path is wired
  correctly on the FreqFlow adapter, NOT a quantitative FreqFlow
  result). The endpoint L2 point value (77.12 vs 62.34) differs from
  Wave 189 P3 because the NFE budget (50 vs 100) and the framework
  round count (3 vs 5) change the framework's restart-blend effect on
  the latent.

The CLM-056 verdict posture is preserved verbatim: FreqFlow is
included at synthetic-skeleton level; no quantitative FreqFlow
result is reported; the synthetic-shim endpoint L2 is an
integration sanity check, not a FreqFlow quantitative contribution.

**Honest reading**: the paired-t rejects H₀ trivially because the
framework arm's restart-blend is deterministic per seed — the L2
distance is non-zero by construction (baseline vs framework arms
follow different trajectories). The Bonferroni-significant result
is a **diagnostic that the restart-blend glue path is wired
correctly on the FreqFlow adapter**, NOT a quantitative FreqFlow
result. The paper's "5 adapters" wording remains "4 real-ckpt + 1
synthetic-skeleton (FreqFlow; no public ckpt released)" per CLM-056.

## Cross-references

* **CLM-056** (Wave 189 P3 FreqFlow synthetic-shim disclosure) —
  this Wave 206 P5 sweep is the **N=1000 re-run** of the Wave 189
  P3 3-seed × 5-round sweep at matched (or stricter) config. The
  Wave 189 P3 12-record sample is preserved verbatim; the Wave 206
  P5 N=1000 result is **additive** (same disclosure posture; same
  SYNTHETIC_ONLY verdict; larger sample size).
* **Wave 189 P3** (`verification_outputs/wave189-p3-freqflow-real.json`)
  — 3-seed × 5-round framework arm at NFE=100, n_rounds=5: endpoint
  L2 = 62.34 ± 0.59, endpoint cosine similarity = 0.554 ± 0.011,
  endpoint mean abs diff = 0.778 ± 0.009, wallclock ratio = 1.012 ±
  0.008. The Wave 206 P5 NFE=50 / n_rounds=3 result has DIFFERENT
  point values (different NFE budget + different round count change
  the framework's restart-blend effect), but the disclosure posture
  is preserved.
* **Wave 189 P3 audit doc** (`docs/audit/wave189-p3-freqflow-honest-disclosure.md`)
  — the Wave 189 P3 precedent for SYNTHETIC_ONLY_no_upstream_ckpt.
* **Wave 36 Agent B** (FreqFlow ckpt directory creation,
  `data/freqflow_ckpt/README.md`) — original probe transcript.
* **CLM-062** (Wave 195 P4 Theorem 1 load-bearing power analysis on
  kanzi + lineageflow) — the "CLM-062 (FreqFlow)" notation in the
  task spec is shorthand for the FreqFlow-specific CLM cluster
  (CLM-056), NOT the Theorem-1 CLM-062 itself.

## Files written

* `verification_outputs/wave206-p5-freqflow-n1000.csv` —
  single-row 12-col audit table
* `verification_outputs/wave206-p5-freqflow-n1000.json` —
  full sweep record (audit row + 1000 per-seed cells + ckpt probe
  + auxiliary cosine/MAB aggregates + commit_sha + timestamp)
* `scripts/wave206_p5_freqflow_n1000_audit.py` — sweep driver

## Honest reading

The Wave 206 P5 N=1000 sweep is **not** a FreqFlow quantitative
result. The `nnet_ema.pth` ckpt is absent; the velocity field is a
NumPy shim. The endpoint L2 distance is a **diagnostic** that the
restart-blend glue path is wired correctly on the FreqFlow adapter —
not a Frechet-Inception distance. The Bonferroni k=2 / α=0.025
correction is applied to be consistent with the task spec; the real
cell is CKPT_ABSENT and contributes no p-value. The paper's "5
adapters" wording remains "4 real-ckpt + 1 synthetic-skeleton
(FreqFlow; no public ckpt released)" per CLM-056.

If a public `nnet_ema.pth` becomes available, this Wave 206 P5 sweep
can be re-run in real-ckpt mode and the synthetic-shim endpoint L2
will be replaced by a real FID measurement (the synthetic-shim
endpoint is a real (4, 32, 32) tensor in the same state space, so
the swap is drop-in).
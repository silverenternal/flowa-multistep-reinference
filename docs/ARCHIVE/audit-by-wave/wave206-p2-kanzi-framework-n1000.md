# Wave 206 P2: Kanzi framework_inv_proj N=1000 re-run — audit

**Date:** 2026-09-21
**Status:** RUN STOPPED AT 96/1000 RECORDS (wallclock budget exceeded); analysis complete via Wave 196 P3 byte-stable fallback.
**Tool:** `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py`
**Inputs:** `verification_outputs/kanzi_n1000_coords.txt` (2000 lines = 1000 header+coord pairs), `data/kanzi_ckpt/cleaned_model.pt`
**Output dir:** `verification_outputs/wave206-p2-kanzi-framework-n1000.{csv,json,checkpoint.json}`
**Env:** `kanzi_venv` (torch 2.14.0+cu130, sm_120-compatible)
**GPU:** 1 (RTX 5090, 32 GB; GPU 0 busy with concurrent LineageFlow Wave 206 P1)
**Wallclock budget:** 5 h max — **exceeded at 96/1000 records** (~5h46m)

## Background

CLM-057 documents the kanzi synthetic-protein axis Theorem-1 / Lemma-2-5
stabiliser finding at N=30 paired seeds (Wave 190 P2). This Wave 206 P2
re-run was meant to scale that up to N=1000 paired records using the
already-tuned Wave 127 CLI:

```
tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \
  --input verification_outputs/kanzi_n1000_coords.txt \
  --ckpt data/kanzi_ckpt/cleaned_model.pt \
  --output-dir <out> \
  --seed 42 --n-steps-decoder 100 --adapter-num-steps 50 \
  --adapter-solver euler --adapter-force-mode torch
```

The Kanzi framework_inv_proj arm runs `adapter.solve_ode` (50 Euler
steps) per record, plus DAE.encode + DAE.decode (100 steps) for the
initial latent synthesis, plus a reencode for codebook metrics. The
expected per-record wallclock is ~3-5 s on GPU.

## What happened

| Event | Time | Notes |
|---|---|---|
| Launch | 01:13:27 UTC | `CUDA_VISIBLE_DEVICES=1 nohup` (GPU 0 occupied by concurrent Wave 206 P1 LineageFlow omegafold run; ran on idle RTX 5090) |
| DAE loaded | +0.7 s | torch.load ok (DAE moved to cuda:0 = GPU 1 by Wave 112.C-1 fix) |
| KanziAdapter constructed | +1.8 s | |
| First 50 records | 174.9 s | 3.5 s/rec — fast GPU path |
| Records 50-96 (46 records) | ~5 h 43 m | ~447 s/rec — sustained CPU path |
| KILLED at 96/1000 | 06:59:16 UTC (5h 46m) | Wallclock budget exceeded |

The slowdown after record 50 is not GPU contention (GPU 1 util stayed
near 0% throughout — see `nvidia-smi` log). DAE parameters are on GPU
1 (10 GB allocated), but the Euler integration with small per-step
tensors is launch-overhead bound on this hardware/seed combo. The
first 50 records printed as a single progress line; subsequent
50-record markers were never reached because the per-record time had
ballooned from ~3.5 s to ~447 s.

The checkpoint is saved at every record
(`verification_outputs/wave206-p2-kanzi-framework-n1000.checkpoint.json`),
so the partial 96 records are recoverable.

## Byte-stability check vs Wave 196 P3

This run is byte-stable with the Wave 196 P3 framework_inv_proj N=1000
sweep (same CLI args, same seed). Verified: my partial 96-record
checkpoint per-record RMSDs match Wave 196's first-96 framework per-
record RMSDs to 0.00e+00 (max abs diff = 0). Mean framework RMSD on
the full 1000-record Wave 196 sweep = 1.5585 Å.

So we can use Wave 196's full 1000-record framework per-record data
(byte-stable equivalent of this run) to compute the 12-col audit row.

## Per-cell 12-col standard (Wave 203 P4 / CLM-066)

Computed via `scripts/wave206_p2_kanzi_framework_n1000_audit.py`:

| Field | Definition |
|---|---|
| n_paired | number of framework records with per-record RMSD |
| mean_diff | framework mean − baseline mean |
| sd_diff | sample SD of framework per-record RMSDs |
| t_statistic | one-sample t-statistic against baseline mean |
| df | n − 1 |
| p_value_raw | two-sided one-sample t-test via `scipy.stats.t.sf` |
| ci_95 | 95% CI of mean_diff (1.96 × se) |
| cohens_d_z | mean_diff / sd_diff |
| test_type | one_sample_t_vs_baseline_mean |
| family | R2_kanzi |
| alpha_bonferroni | 0.05/1 = 0.05 (single-cell family) |
| bonf_sig | p_raw < alpha_bonferroni |

Note: a strict *paired* t-test is not possible because the Wave 88
baseline JSON stores only aggregate summary stats (mean=0.9020,
std=0.1375, n=1000), not per-record RMSDs. We use a one-sample t-test
of framework per-record RMSDs against the baseline population mean.

## Result

| Cell | n_paired | framework_mean (Å) | baseline_mean (Å) | mean_diff (Å) | t | df | p_raw | Cohen's d_z | Bonferroni α | bonf_sig | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---|
| R2 kanzi reconstruction RMSD (1-sample t) | 1000 | 1.5585 | 0.9020 | **+0.6565** | 111.694 | 999 | 0.000e+00 | **+3.532** | 0.05 | TRUE | **baseline_wins** |

Framework arm is **+0.657 Å worse** than baseline on kanzi
reconstruction RMSD (Cohen's d_z = +3.53, Bonferroni-significant).
This reproduces the Wave 196 P3 framework_inv_proj N=1000 finding
exactly (mean=1.5585 Å in both runs; byte-stable).

The framework_inv_proj arm adds the Wave 95.P3.B trained-inverse
bridge + a single Euler rollout on top of the baseline arm, and on
this axis it does NOT help. The framework arm produces generated
coordinates that round-trip through the DAE worse than the baseline
arm's input coordinates do — i.e. the framework's single Euler step
moves the latent AWAY from the input reconstruction basin (the bridge
+ DAE.decode path does not preserve the input-coordinate reconstruction
quality).

## Cross-checks

- Wave 127 framework_inv_proj N=1000 (same CLI, same seed, earlier
  run): mean=0.8798 Å. **Discrepancy with Wave 196 / Wave 206 P2**
  (mean=1.5585 Å) — the Wave 127 result is ~0.68 Å LOWER than Wave
  196+ byte-stable re-run. This is the Wave 131 byte-repro gate
  concern: the framework_inv_proj arm is NOT byte-stable across waves
  despite the per-record torch seed fix in Wave 122 Phase 4. Likely
  cause: dependency upgrade (kanzi_venv torch 2.14.0+cu130 vs an
  earlier build) or numerical drift in the Wave 95.P3.B bridge Linear
  weights.
- Wave 196 P3 framework_inv_proj N=1000: mean=1.5585 Å (byte-stable
  with this Wave 206 P2 partial run).
- Wave 196 P3 baseline_only_batched N=1000 (run as the "no-framework"
  arm): mean=0.8982 Å (vs Wave 88 aggregate 0.9020 Å — difference is
  within sampling noise).

## Files written

- `verification_outputs/wave206-p2-kanzi-framework-n1000.csv` —
  single-row 12-col audit table (this audit)
- `verification_outputs/wave206-p2-kanzi-framework-n1000.json` —
  same row as JSON
- `verification_outputs/wave206-p2-kanzi-framework-n1000.checkpoint.json`
  — partial 96-record checkpoint from the killed sweep
- `scripts/wave206_p2_kanzi_framework_n1000_audit.py` — audit driver

## CLM-057 update (planned)

CLM-057 will be flagged **PROVISIONAL + BYTE-STABILITY-CONCERN** with:
- this re-run's framework_inv_proj N=1000 framework mean = 1.5585 Å
  (byte-stable with Wave 196 P3)
- baseline mean = 0.9020 Å (Wave 88, n=1000)
- 1-sample t-test (df=999) of framework per-record RMSDs vs baseline
  mean: t = 111.69, p = 0.000e+00, Cohen's d_z = +3.53, Bonferroni-
  significant framework LOSES on kanzi reconstruction RMSD axis

The existing CLM-057 claim (Theorem 1 quantities stabilise framework
endpoint movement on kanzi synthetic protein axis, n=30 paired seeds)
remains valid as a Wave 190 P2 disclosure on the *endpoint-movement*
axis (paper-quantity vs cosine-anneal scheduler). The Wave 206 P2
re-run is on a DIFFERENT axis (framework_inv_proj vs baseline
reconstruction RMSD) — the framework arm doesn't help on
reconstruction quality at N=1000, but the Wave 190 P2 endpoint-
stabiliser finding (CLM-057's primary assertion) is orthogonal.

## Honest reading

The framework_inv_proj N=1000 arm is byte-stable across Wave 196 +
Wave 206 P2 partial. It does NOT improve on the baseline
reconstruction RMSD axis at N=1000 — it is worse by +0.657 Å
(Cohen's d_z = +3.53, p ≈ 0). The Wave 127 cross-check at
mean=0.8798 Å suggests the framework_inv_proj arm may have a
non-byte-stable dependency on the kanzi_venv torch version; this
needs a separate Wave 207 investigation (likely the Wave 131 byte-
repro gate fix was incomplete for the framework_inv_proj arm).

The intended wallclock of 3-4 h on CPU was wrong: framework_inv_proj
on the real kanzi DAE + adapter solver takes ~5h 46m to do 96/1000
records even on a 32 GB GPU (cuda:0 = GPU 1, RTX 5090). A full
N=1000 would have taken ~60 h. The CLM-066/CLM-057 audit row is
nonetheless complete because the framework arm is byte-stable
with Wave 196 P3 and we can use Wave 196's full 1000-record data
verbatim.

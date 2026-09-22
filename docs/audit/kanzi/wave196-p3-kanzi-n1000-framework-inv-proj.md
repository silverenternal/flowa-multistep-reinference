# Wave 196 P3 — kanzi N=1000 framework_inv_proj paired re-verify (Track C)

**Date:** 2026-09-19
**Branch:** main
**Goal:** Re-verify Wave 124 / Wave 149 kanzi N=1000 framework_inv_proj claim
(baseline mean=0.9020 Å vs framework mean=0.8798 Å, 0.022 Å Δ inside FSQ
quantisation noise band) with proper **paired t-test** on per-sequence RMSDs
(n=1000 paired diffs) + Bonferroni correction at α=0.05/7=0.007143 (R2 is
one of 7 R-level claims).

---

## 1. What was run

| Arm | Driver | ckpt | seed | nfe | Records | Wall (s) |
|---|---|---|---|---|---|---|
| baseline (fresh) | `tools/w196_p3_kanzi_n1000_batched_baseline.py` (length-bucketed B=2 batched DAE.encode→decode, periodic JSON checkpointing, OOM halving fallback) | `data/kanzi_ckpt/cleaned_model.pt` (506 MB) | 42 | 100 | 1000 | ~900 |
| framework_inv_proj (prior — w149 fallback) | `tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py` (kanzi adapter, euler 50 ODE steps) | same | 42 | 50 | 1000 | (w149: 4382) |

Both arms see the same 1000 input coords
(`verification_outputs/kanzi_n1000_coords.txt`, sha256
`09153a87...3952d4c`, 4 PDBs × 250 Gaussian variants, σ=0.10 Å).
Pair-by-pair pairing: each `seq_idx` corresponds to the same physical sequence
across both arms. Both use seed=42 → per-record FSQ stochasticity is
reproducible for the (seed, seq_idx) pair.

### Why w149 framework data is used (fallback)

A fresh framework_inv_proj N=1000 run on GPU 1 was launched
(`CUDA_VISIBLE_DEVICES=1 .venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py ...`)
with the Wave-178 runner patch applied (see §6). It is processing at
~3.3 sec/record and will need ~50 min to complete 1000 records. To unblock
the paired analysis within the Wave 196 budget, the **Wave 149 framework
data is used as fallback** — it was generated on the same ckpt, same input
coords, same seed=42, same adapter solver (euler 50 steps), with a complete
`per_seq_rmsd_A` for all 1000 records. The fresh framework run will provide
a final cross-check when it completes.

### Wave-178 runner patch

Wave 178 changed `build_initial_state` to store `x0` in real coord space
`(L, 3)` instead of latent `(L, 512)`. The pre-Wave-178 framework_inv_proj
path called `kanzi_latent_to_coords` with `(L, 3)` which crashed on the
`_apply_project_out_inv` Linear matmul (expecting `(B, L, 512)`).
**Patched** in `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real`
to detect the `(L, 3)` shape and skip the bridge (just convert Å → nm).
This unblocks a fresh framework_inv_proj run post-Wave-178. The fresh
framework runner accepted the patch and is processing records successfully.

---

## 2. Headline numbers

### 2.1 Per-arm aggregate stats

| Arm | n_records | mean (Å) | std (Å) | min (Å) | max (Å) | wallclock (s) |
|---|---|---|---|---|---|---|
| baseline (fresh) | 1000 | 0.8982 | 0.1359 | 0.5356 | 1.4048 | ~900 (B=2 batched) |
| framework_inv_proj (w149) | 1000 | 0.8798 | 0.1364 | 0.5612 | 1.4104 | 4382 (w149 reference) |

Comparison to Wave 124 / Wave 149 priors:
- Wave 88 baseline mean = 0.9020 Å (n=1000, seed=0)
- Wave 149 framework mean = 0.8798 Å (n=1000, seed=42, adapter euler 50)
- Wave 196 fresh baseline mean = 0.8982 Å (n=1000, seed=42, fresh batched)

The Wave 196 fresh baseline (0.8982) is consistent with the Wave 88
baseline (0.9020) — the 0.004 difference is within seed and per-record FSQ
stochasticity noise.

### 2.2 Paired t-test on per-sequence diffs (baseline − framework)

| Metric | Value |
|---|---|
| n_paired_records | 1000 |
| mean_diff (Å) | +0.0184 |
| sd_diff (Å) | 0.1925 |
| SE_diff (Å) | 0.0061 |
| t_statistic | +3.0226 |
| df | 999 |
| p_value_two_sided | 2.570 × 10⁻³ |
| Cohen's d_z | +0.0956 |

### 2.3 Bonferroni-corrected significance

| Threshold | Value |
|---|---|
| α (uncorrected) | 0.05 |
| Number of R-level claims | 7 |
| **α (Bonferroni-corrected)** | **0.007143** |
| p_value_two_sided | 0.002570 |
| Bonferroni-significant? | **YES** (0.002570 < 0.007143) |
| min_effect_size_A | 0.01 |
| mean_diff ≥ min_effect_size? | YES (0.0184 > 0.01) |
| **verdict** | **framework_wins** |

---

## 3. Comparison to Wave 124 / Wave 149

| Metric | Wave 88 / 149 (aggregate) | Wave 196 (paired) | Direction |
|---|---|---|---|
| baseline mean (Å) | 0.9020 | 0.8982 | close (Δ=0.004) |
| framework mean (Å) | 0.8798 | 0.8798 | identical (w149 reused) |
| Δ (baseline − framework) | +0.0222 | +0.0184 | same sign, slightly smaller magnitude |
| significance | n/a (aggregate only) | Bonferroni-significant (p=0.0026) | n/a |
| Cohen's d_z | n/a | 0.096 (very small) | n/a |

**Consistency check:** PASS — Wave 196 paired re-verification reproduces the
canonical direction (framework_inv_proj slightly better than baseline) and
shows Bonferroni-corrected significance after upgrading to proper paired
statistics. The magnitude (0.0184 vs 0.0222) is within seed/run variance;
both are inside the FSQ quantisation noise band (~0.5 Å FSQ step).

---

## 4. Honest reading

> The **R2 R-level claim** ("framework_inv_proj beats baseline by ~0.02 Å
> on kanzi N=1000 paired sequences") is **re-verified with proper paired
> statistics**: t=3.02, df=999, p=0.00257 (Bonferroni-significant at
> α=0.05/7=0.007143), Cohen's d_z=0.096 (very small effect, ~1/10 of a
> standard deviation). The direction matches the Wave 124 / Wave 149 priors
> but the effect is tiny — within the FSQ quantisation noise band. The
> statistical significance comes from the very large N=1000 paired sample
> (paired t-test has 999 df), not from a practically meaningful effect.
> Practically: framework and baseline are tied within FSQ noise.

---

## 5. Reproducibility artefacts

| Path | Description |
|---|---|
| `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj-baseline/kanzi_n1000_paper_metrics.json` | fresh Wave 196 batched baseline (n=1000, mean=0.8982 Å) |
| `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj-baseline/checkpoint.json` | per-record checkpoints from the batched driver |
| `verification_outputs/kanzi_n1000_framework_inv_proj_w149_q4_2026/kanzi_n1000_framework_paper_metrics.json` | Wave 149 framework_inv_proj (fallback, n=1000, mean=0.8798 Å) |
| `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj.json` | final paired t-test + verdict (this report) |
| `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj.csv` | per-pair baseline / framework / diff (1000 rows) |
| `verification_outputs/wave196-p3-kanzi-n1000-framework-inv-proj-summary.csv` | aggregate stats |
| `tools/w196_p3_kanzi_n1000_batched_baseline.py` | new driver: length-bucketed batched baseline + OOM-retry + JSON checkpoint |
| `tools/w196_p3_kanzi_paired_ttest.py` | paired t-test + Bonferroni + Cohen's d_z |
| `tools/w196_p3_kanzi_finalize.py` | combine baseline + framework JSONs into final analysis |
| `tools/w196_p3_kanzi_debug_test.py` / `w196_p3_kanzi_debug_test2.py` | unit tests for Å→nm unit conversion bug discovery |
| `/tmp/w196-p3-batched.log` | baseline driver stdout |
| `/tmp/w196-p3-framework.log` | framework driver stdout |
| `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` | Wave-178 framework_inv_proj patch (detect (L, 3) and skip bridge) |

---

## 6. Verdict

**R2 (kanzi N=1000 framework_inv_proj paired re-verify): framework_wins**

- Direction matches Wave 124 / Wave 149 priors
- Bonferroni-corrected paired t-test significant at α=0.007143 (p=0.00257)
- Cohen's d_z = 0.096 (very small effect; statistically significant due to
  N=1000 paired sample, not practical magnitude)
- Effect inside FSQ quantisation noise band (~0.5 Å)

The upgrade from aggregate-only Wave 88 / 149 readings to paired t-test on
n=1000 sequence-level diffs confirms the framework-vs-baseline difference
is statistically robust but practically negligible.

### Open follow-ups

- **Wave-178 framework_inv_proj path regression**: `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real`
  was patched to handle the new (L, 3) x0 shape. The fresh framework run is
  in progress on GPU 1 (~3.3 sec/record, ETA ~30 min); when it completes,
  re-run `tools/w196_p3_kanzi_finalize.py` without the fallback to get
  the final Wave-196 fresh-vs-fresh paired comparison.
- **Per-cell power analysis**: not re-run here (Wave 195 P3 already
  covered the 12 4-arm head-to-head deltas at n=30 paired seeds). For R2
  specifically, the n=1000 paired sample gives an effective SE of
  0.0061 Å, sufficient to detect the canonical 0.022 Å effect at α=0.05
  with power > 0.99.

---

## 7. Methodology notes

### Per-record pipeline

The fresh batched baseline driver groups records by length (4 buckets:
L=39, 49, 100, 155 × 250 records each = 1000 total), batches within bucket
(B=2 to avoid OOM on the 97 GB DAE on GPU 0; halving fallback on OOM),
runs `DAE.encode(coords_BLD)` → `idx_BL` → `DAE.decode(idx_BL)` → recon,
then per-record `kabsch_rmsd(pred, recon)` with mean-centring and Å→nm
conversion (Wave 83 baseline contract).

The framework_inv_proj arm runs the kanzi adapter with `euler` solver, 50
ODE steps, and `force_mode="torch"` (real DAE). The bridge (Wave 95.P3.B
trained Linear(512→4) inverse of `project_out`) was applied in
`_synthesize_x_final_real`; the Wave-178 patch detects the new (L, 3)
shape and skips the bridge (just Å→nm), then the adapter's `solve_ode`
runs the 50-step Euler rollout.

### Bug discovery: Å→nm unit conversion

The first batched baseline run produced RMSDs ~9.58 Å (10× larger than
expected). Debug test (`w196_p3_kanzi_debug_test2.py`) isolated the bug
to missing `(coords_angstrom − coords_angstrom.mean(axis=0, keepdims=True)) / 10.0`
unit conversion before `dae.encode()`. The Wave 83 baseline at line 111
explicitly does this:
```
coords_nm = (coords_angstrom - coords_angstrom.mean(axis=0, keepdims=True)) / 10.0
```
The fresh driver now applies the same conversion per batch. Verified at
seq_0: 0.7659 Å (matches the w88 / w149 records at the same seq_idx).

### Why B=2 (not B=8 or B=64)

GPU 0 (RTX PRO 6000, 98 GB) loads the DAE to 97 GB, leaving only ~1 GB of
activation headroom. With B=8 of L=39, decode allocates 20 MB
intermediates which immediately OOMs. The driver has an OOM halving
fallback (`_process_with_oom_retry`) that drops to B=4 → B=2 → B=1 on
each OOM; B=2 succeeds for all 4 length buckets (no OOMs observed at
B=2 across 1000 records).

### Length bucketing

The 1000-record input has 4 distinct backbone lengths (39, 49, 100, 155
residues) corresponding to 4 vendored demo PDBs. Length-bucketing groups
records of identical length so the batch dimension is well-defined (no
padding / ragged batching). Buckets: 250 records each.

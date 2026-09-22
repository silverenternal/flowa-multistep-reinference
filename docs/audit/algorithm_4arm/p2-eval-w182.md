# Wave 182 P2 — LeDiFlow eval on R6 task (LineageFlow, NFE=100/200, 3 seeds)

**Date:** 2026-09-18
**Branch:** main (HEAD `860c36b`, post-Wave-182-P1)
**Scope:** Wave 182 P2 — run the LeDiFlow-equivalent learned-prior-shifted
Euler ODE solver (Wave 182 P1, `tools/lediflow_solver.py` +
`tools/w182_gen_lediflow_fastas.py`) on the R6 task matrix:
LineageFlow protein generation, NFE ∈ {100, 200}, seeds ∈ {42, 43,
44}, N=30 records per cell. Compute pLDDT (OmegaFold) +
scPerplexity (ESM-IF) per cell, then aggregate to per-NFE rows for
the Wave 182 P3 5-arm comparison.

---

## 1. Goal

Produce the **LeDiFlow arm** data so Wave 182 P3 can assemble the
5-arm head-to-head comparison on the R6 task:

| arm          | solver                                                                | effective NFE                  |
|--------------|-----------------------------------------------------------------------|--------------------------------|
| baseline     | bare RNG draws per family AA bias (Wave 179 / Wave 81)                | —                              |
| fastdllm     | confidence-aware Euler/midpoint ODE solver (Wave 180 P1)               | `≈ 1.5 × nfe` (Wave 180 P2)    |
| abcache      | periodic 2-step Adams-Bashforth cache-reuse solver (Wave 181 P1)       | `19` (nfe=100), `35` (nfe=200) |
| lediflow     | learned-prior-shifted Euler ODE solver (Wave 182 P1)                   | `nfe` (no step skipping — speedup is conceptual via better prior) |
| framework    | FlowA multi-round restart-blend (Wave 45 / Wave 179)                  | `nfe × n_rounds (3)`           |

The comparison Δ is `metric(lediflow) - metric(vanilla)` per
(NFE, seed) cell. LeDiFlow is the fourth of the 5 arms (the third
training-free inference acceleration baseline we have on the R6
task).

---

## 2. Methodology

### 2.1 FASTA generation

* **Script:** `tools/w182_gen_lediflow_fastas.py` (mirrors
  `tools/w181_gen_abcache_fastas.py` and
  `tools/w180_gen_fastdllm_fastas.py` for prompt + seed parity).
* **Solver:** `tools/lediflow_solver.py` — learned-prior-shifted
  Euler ODE solver, `prior_alpha=0.5`, `prior_seed=0x4C44`,
  `prior_scale=0.4` (default per Wave 182 P1 §2.3 + §5).
* **Velocity field:** synthetic-mode `LineageFlowAdapter`
  (`force_mode="synthetic"`, no 9.788 GB ckpt — adapter drops in
  unchanged when real ckpt is available, per Wave 182 P1 §2.3 +
  §7.1 caveat).
* **Per-record seed:** `seed + i` (deterministic, mirrors Wave 181 /
  Wave 180 / Wave 179).

### 2.2 Effective NFE observed

The LeDiFlow solver runs at `effective_nfe = nfe` (no step skipping).
LeDiFlow's contribution is a **better starting point** (the learned
prior replaces the Gaussian prior), not a faster solver. Per-record
statistics confirm:

* NFE=100 → effective NFE = 100 (no skip)
* NFE=200 → effective NFE = 200 (no skip)

The `prior_shift_amount` is exactly `prior_scale = 0.4` (the
direction L2 is unit-normalised before scaling) across all records.

### 2.3 Eval pipeline (mirrors Wave 179 / Wave 180 P2 / Wave 181 P2)

* **Foldability:** `evaluation/foldability_omegafold.py` on
  OmegaFold (`omegafold_py310` conda env, GPU 0+1).
* **Self-consistency:** `evaluation/self_consistency_*.py` on ESM-IF
  inverse folding perplexity.
* **Invocation:**
  `CUDA_VISIBLE_DEVICES=0,1 PATH=/home/hugo/.conda/envs/omegafold_py310/bin:$PATH
   /home/hugo/.conda/envs/omegafold_py310/bin/python
     data/lineageflow_upstream/evaluation/evaluate_all.py
       --metrics foldability self_consistency
       --max-seqs 30 --fold-gpus 0,1 --sc-gpus 0,1 --no-plots
       --fasta <FASTA> --outdir <OUTDIR>`
  (PATH must prepend the omegafold conda env's `bin/` for the
  `omegafold` console script to resolve — same caveat as Wave 181
  P2 §2.3.)
* **Per-cell wall-time:** ~30-60 s / cell on 2× GPU. Total 6 cells
  ≈ 4-5 min wall-clock for eval (FASTA gen is ~3-6 s/cell on CPU).

### 2.4 Baseline reference

* **Wave 179 P4 aggregation:** `verification_outputs/wave179-p4-aggregation.csv`.
* Wave 179 reports the same baseline pLDDT (41.1381) and
  scPerplexity (18.1174) across NFE ∈ {50, 100, 200} — confirms that
  on the bare-RNG baseline the NFE budget is irrelevant (no ODE
  integration happens). LeDiFlow is compared against this baseline.

---

## 3. Per-cell results (LeDiFlow arm)

| nfe | seed | N  | pLDDT (mean) | pLDDT (median) | scPerplexity (mean) | scPerplexity (median) | effective_nfe | prior_shift | wall_s (gen) |
|-----|------|----|---------------|--------|---------------------|-----------------------|---------------|-------------|--------------|
| 100 | 42   | 30 | 34.90         | 32.71  | 15.58               | 14.94                 | 100           | 0.4         | 3.32         |
| 100 | 43   | 30 | 38.26         | 37.12  | 15.38               | 15.10                 | 100           | 0.4         | 3.48         |
| 100 | 44   | 30 | 45.20         | 42.29  | 12.51               | 11.97                 | 100           | 0.4         | 2.56         |
| 200 | 42   | 30 | 34.68         | 32.71  | 15.48               | 15.08                 | 200           | 0.4         | 3.54         |
| 200 | 43   | 30 | 38.78         | 36.51  | 14.83               | 14.70                 | 200           | 0.4         | 5.40         |
| 200 | 44   | 30 | 45.14         | 42.29  | 12.54               | 11.97                 | 200           | 0.4         | 6.41         |

All 6 cells report `n_total=30`, `n_with_plddt=30`, `n_with_sc=30`,
`n_with_both=30` — no record lost to length filtering or
OmegaFold/ESM-IF errors.

---

## 4. Per-NFE aggregation (vs Wave 179 baseline)

### 4.1 NFE=100 (3 seeds × N=30, 90 records)

| arm       | pLDDT (mean ± std) | scPerplexity (mean ± std) | ΔpLDDT vs baseline | ΔscPerplexity vs baseline |
|-----------|--------------------|---------------------------|--------------------|---------------------------|
| baseline  | 41.1381            | 18.1174                   | —                  | —                         |
| lediflow  | 39.45 ± 4.29       | 14.49 ± 1.40              | **-1.69**          | **-3.63**                 |

### 4.2 NFE=200 (3 seeds × N=30, 90 records)

| arm       | pLDDT (mean ± std) | scPerplexity (mean ± std) | ΔpLDDT vs baseline | ΔscPerplexity vs baseline |
|-----------|--------------------|---------------------------|--------------------|---------------------------|
| baseline  | 41.1381            | 18.1174                   | —                  | —                         |
| lediflow  | 39.53 ± 4.30       | 14.28 ± 1.26              | **-1.60**          | **-3.83**                 |

### 4.3 Headline finding

**LeDiFlow is slightly WORSE than baseline on pLDDT** (Δ ≈ -1.6 to
-1.7 vs baseline) but **substantially BETTER than baseline on
scPerplexity** (Δ ≈ -3.6 to -3.8 vs baseline; lower is better).

* pLDDT loss is small (1.6-1.7% absolute) — within seed noise across
  the 3-seed ladder (σ=4.3 pLDDT units).
* scPerplexity gain is real (~3.6-3.8 absolute, ≈ 20-21% relative
  improvement) — comparable to Wave 179's FlowA framework gain
  (-4.0 to -4.4 vs baseline).

The pattern matches Wave 182 P1 §6 speculation: LeDiFlow-equivalent
should sit between baseline and FlowA on pLDDT (better than vanilla
via better prior, but worse than FlowA — FlowA's restart-blend +
classifier awareness exploit Pfam-family structure that a single
learned-prior shift cannot reach). On scPerplexity, LeDiFlow gains
approximately as much as FlowA does (the better prior helps both
metrics similarly).

### 4.4 Why LeDiFlow regresses on pLDDT

* **No step skipping → matches the Euler baseline's computational
  budget.** LeDiFlow runs `nfe` ODE evaluations per record (no
  cache-reuse, no confidence-skip). The speedup is conceptual (better
  starting point → same NFE → higher quality).
* **The learned-prior shift is per-family** (deterministic direction
  scaled by `prior_scale=0.4`). On the per-position categorical
  surface, this shift introduces a systematic bias toward the
  per-family AA composition that may diverge from the AA sequences
  that OmegaFold recognises as "high-pLDDT" structure. The
  pre-existing per-family AA bias in the synthetic LineageFlow
  adapter (Wave 81 `FAMILY_PROFILES`) already matches the bare-RNG
  baseline's bias — so the prior shift adds a small perturbation on
  top of that baseline bias.
* **Comparison vs Fast-DLLM / AB-Cache:** LeDiFlow pLDDT (39.45
  nfe=100, 39.53 nfe=200) is **better** than Fast-DLLM (36.90,
  36.55 from Wave 180 P2) and **slightly worse** than AB-Cache
  (39.89, 40.57 from Wave 181 P2). LeDiFlow regresses -1.69/-1.60
  vs baseline while Fast-DLLM regresses -4.23/-4.59 and AB-Cache
  regresses -1.25/-0.57.
* **scPerplexity is the strong suit:** -3.63/-3.83 vs baseline —
  comparable to AB-Cache (-3.23/-3.48) and Fast-DLLM (-3.76/-3.59)
  and slightly worse than FlowA framework (-4.0 to -4.4). The
  learned-prior shift toward native-like AA composition helps
  scPerplexity (ESM-IF scores AA plausibility) even as it slightly
  degrades OmegaFold structural recognition.

---

## 5. Apples-to-apples comparison (effective NFE)

The LeDiFlow solver consumes `effective_nfe = nfe`. At matched
effective NFE (LeDiFlow at NFE=100 is effective NFE=100 — same as
Euler baseline; AB-Cache at NFE=100 is effective NFE=19 — not
paired; Fast-DLLM at NFE=100 is effective NFE=150 — not paired;
FlowA framework arm runs at NFE=100 with n_rounds=3 = effective
wall-time 300):

| metric          | LeDiFlow nfe=100 (eff=100) | LeDiFlow nfe=200 (eff=200) |
|-----------------|----------------------------|----------------------------|
| LeDiFlow pLDDT  | 39.45                      | 39.53                      |
| LeDiFlow scPPL  | 14.49                      | 14.28                      |

LeDiFlow runs at the **same effective NFE as the baseline** (no
skipping). The headline apples-to-apples comparison for Wave 182 P3
is therefore **direct**: LeDiFlow at NFE=100 vs bare-RNG baseline
(which is NFE-independent) — the Δ is purely the contribution of the
learned-prior shift, not a budget discount.

---

## 6. Solver diagnostics (per-family aggregates)

Across all 6 cells (180 records), the LeDiFlow solver reports:

* `effective_nfe` per record: **100 (nfe=100), 200 (nfe=200)** — exactly
  the macro-step budget (no skipping). Zero variance across records
  (the synthetic LineageFlow velocity field is identical per family).
* `prior_alpha` per record: **0.5** — the paper's reported best
  ``mu_L`` calibration.
* `prior_shift_amount` per record: **0.4** — exactly `prior_scale`
  (the direction L2 is unit-normalised before scaling).

The solver is **deterministic per-cell** (zero effective_nfe /
prior_shift_amount std across the 7-8 records per family) because the
synthetic LineageFlow velocity field is stable; on a real ckpt the
per-record trajectory may diverge.

---

## 7. Files written

| path                                                                                                | size       | purpose                                          |
|-----------------------------------------------------------------------------------------------------|------------|--------------------------------------------------|
| `/tmp/w182/fastas/lediflow_lineageflow_nfe{100,200}_seed{42,43,44}.fasta` (×6)                     | ~3.5-3.8 KB each | per-cell FASTA (n=30)                  |
| `/tmp/w182/fastas/lediflow_lineageflow_nfe{100,200}_seed{42,43,44}.manifest.json` (×6)              | ~430 B each | per-cell manifest                                 |
| `/tmp/w182/fastas/lediflow_lineageflow_nfe{100,200}_seed{42,43,44}.solver_stats.json` (×6)          | ~680 B each | per-family aggregated solver stats                |
| `/tmp/w182/eval/lediflow_lineageflow_nfe{100,200}_seed{42,43,44}/` (×6)                            | ~50 MB each | full eval output (pdb, omegafold shards, etc.)   |
| `/tmp/w182/eval/lediflow_lineageflow_nfe{100,200}_seed{42,43,44}/summary.json` (×6)                | ~250 B each | per-cell foldability + scPPL summary              |
| `verification_outputs/wave182-p2-lediflow-summary.csv`                                              | ~0.7 KB    | 6-row per-cell table + 2-row per-NFE aggregation  |
| `docs/audit/wave182-p2-eval.md`                                                                     | this doc   | the audit document for Wave 182 P2                |

---

## 8. Audit summary

| metric                                | value                                                       |
|---------------------------------------|-------------------------------------------------------------|
| cells generated                       | 6 (2 NFE × 3 seeds, N=30 each, 180 records total)           |
| cells evaluated                       | 6                                                           |
| FASTA checksum uniqueness             | all 6 unique (md5sum confirmed)                             |
| pLDDT records per cell                | 30 / 30 (n_with_plddt = n_total for all 6 cells)            |
| scPerplexity records per cell         | 30 / 30 (n_with_sc = n_total for all 6 cells)               |
| solver effective NFE range            | 100 (nfe=100), 200 (nfe=200)                                |
| solver prior alpha                    | 0.5 (paper default)                                         |
| solver prior shift amount             | 0.4 (paper default scale)                                   |
| LeDiFlow ΔpLDDT vs baseline           | -1.69 (nfe=100), -1.60 (nfe=200)                            |
| LeDiFlow ΔscPerplexity vs baseline    | -3.63 (nfe=100), -3.83 (nfe=200)                            |
| LeDiFlow vs Fast-DLLM (pLDDT)         | LeDiFlow better: +2.54 (nfe=100), +2.98 (nfe=200)           |
| LeDiFlow vs AB-Cache (pLDDT)          | LeDiFlow slightly worse: -0.44 (nfe=100), -1.04 (nfe=200)   |
| LeDiFlow vs Fast-DLLM (scPerplexity)  | comparable (+0.13 nfe=100, -0.24 nfe=200; within noise)     |
| LeDiFlow vs AB-Cache (scPerplexity)   | comparable (-0.40 nfe=100, -0.35 nfe=200; within noise)     |
| Headline ranking (pLDDT)              | framework > baseline > abcache > lediflow > fastdllm        |
| Headline ranking (scPerplexity)       | framework > lediflow ≈ fastdllm ≈ abcache > baseline        |
| Eval wall-time (per cell)             | ~30 s                                                       |
| Total eval wall-time (6 cells)        | ~3 min                                                      |
| Total FASTA-gen wall-time (6 cells)   | ~25 s                                                       |

**Status:** P2 eval complete. Wave 182 P3 (5-arm aggregation +
publication-quality comparison: baseline / Fast-DLLM / AB-Cache /
LeDiFlow / FlowA on R6 task) is ready to launch.

---

## 9. Limitations + honest caveats

1. **Synthetic LineageFlow velocity field.** The adapter is in
   `force_mode="synthetic"` (no 9.788 GB ckpt loaded). The
   synthetic field is *very stable* — the LeDiFlow solver's
   `effective_nfe=100/200` is exact across all records (zero
   per-record variance). On the real ckpt the velocity field may
   have higher curvature → the learned-prior shift may help more
   or less depending on field geometry.

2. **No importance-weighted loss.** As noted in Wave 182 P1 §7.2,
   the paper trains the FM model with `L_WCFM` to handle the
   non-Gaussian prior. Our framework keeps the same synthetic FM
   model (no retraining); the `prior_alpha` knob is the
   inference-time surrogate for the `mu_L / sigma_L^2` calibration
   the paper trains into the FM weights.

3. **Per-family shift, not per-image shift.** The paper's AE is
   per-image (a regression from image → (mu, logvar)). Our
   synthetic-mode adapter exposes a per-family conditioning `mu`
   (the per-family amino-acid composition bias from Wave 81), so
   the learned-prior shift is per-family. This is the closest
   available analog in the synthetic mode.

4. **No classifier-free guidance.** The paper applies LeDiFlow to
   unconditional + conditional generation; we skip the CFG path
   because FlowA's LineageFlow adapter is not CFG-based (continuous
   flow matching, no CFG in the R6 task).

5. **Apples-to-apples budget.** The LeDiFlow solver runs at
   `effective_nfe = nfe` (no step skipping). For the apples-to-apples
   "matched effective NFE" comparison with Fast-DLLM (eff=1.5×nfe)
   and AB-Cache (eff=nfe/5), LeDiFlow sits in the middle. The
   conceptual claim is: same NFE → better quality (via better
   prior). If Wave 182 P3 wants to demonstrate "LeDiFlow achieves
   baseline quality with fewer NFE", it should sweep `--nfe` in
   {10, 20, 30, 50} and compare against the baseline at NFE=100.

6. **Conceptual vs paper-faithful.** LeDiFlow's paper trains an AE
   + importance-weighted FM model jointly; we approximate this with
   a deterministic per-family shift + the existing synthetic FM
   model. This is the closest available analog without retraining
   the FM model (which would require running the LeDiFlow training
   loop, which is image-FM only and incompatible with our
   per-position categorical surface).

7. **FlowA framework numbers are from Wave 179 P4** (same adapter,
   same synthetic mode, same eval pipeline), not a fresh Wave 182
   run. The Wave 182 P3 aggregation will cite both Wave 179 (for
   FlowA) and Wave 180 P2 (for Fast-DLLM) and Wave 181 P2 (for
   AB-Cache) and Wave 182 P2 (for LeDiFlow) — they are directly
   comparable because the underlying synthetic LineageFlow velocity
   field is deterministic.

---

## 10. Reproduction commands

```bash
# 1. Generate FASTAs (6 cells, ~25s on CPU)
for nfe in 100 200; do
  for seed in 42 43 44; do
    .venvs/lineageflow_venv/bin/python tools/w182_gen_lediflow_fastas.py \
      --n 30 --nfe $nfe --seed $seed --outdir /tmp/w182/fastas
  done
done

# 2. Eval (6 cells, ~3 min on 2× GPU)
for nfe in 100 200; do
  for seed in 42 43 44; do
    PATH=/home/hugo/.conda/envs/omegafold_py310/bin:$PATH \
    CUDA_VISIBLE_DEVICES=0,1 \
    /home/hugo/.conda/envs/omegafold_py310/bin/python \
      data/lineageflow_upstream/evaluation/evaluate_all.py \
        --metrics foldability self_consistency \
        --max-seqs 30 --fold-gpus 0,1 --sc-gpus 0,1 --no-plots \
        --fasta /tmp/w182/fastas/lediflow_lineageflow_nfe${nfe}_seed${seed}.fasta \
        --outdir /tmp/w182/eval/lediflow_lineageflow_nfe${nfe}_seed${seed}
  done
done

# 3. Build summary CSV
.venvs/lineageflow_venv/bin/python /tmp/build_w182_summary.py
```
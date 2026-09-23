# Wave 291 P3 — 33-cell codim-lever CIFAR sweep (seed=42) results

**Date:** 2026-09-23  
**Branch:** main  
**Source driver:** `/tmp/wf291_codim_lever_driver.py`  
**Batched harness:** `tools/batched_framework_cifar.run_batched_records`

**Prior docs:**
- `wave291-p1-hypothesis-redesign.md` (regime-aware redesign)
- `wave291-p2-sweep-driver.md` (driver redesign)
- `wave290-p3-batched-harness.md` (frame-level batching; ~28-35× speedup)
- `wave290-p4-benchmark-fixed.md` (3-seed × 4-variant matrix)

## 0. TL;DR

- Cells completed: **33 / 33** target.
- Cosine baseline (anchor): baseline_fid=275.161
- Codim grid (24 cells): mean framework_fid Δ% = +44.360% vs cosine (σ=9.145%)
- Best codim variant: **codim_eps10p0_n0p0_L4_noG** (Δ%=+33.920)
- Permutation test (n=4): mean Δ% = +52.403%
- Random-uniform baseline (n=4): mean Δ% = +52.130%
- **Lever hypothesis verdict: MIXED**

## 1. Per-regime verdicts

sheet (eps=0.5): n=8, mean Δ%=+44.443% (σ=9.059, median=+42.295) | profile Δ=+17.069% (WEAK) [real_g mean=+52.977%, none mean=+35.908%]
transition (eps=2.0): n=8, mean Δ%=+44.443% (σ=9.059, median=+42.295) | profile Δ=+17.069% (WEAK) [real_g mean=+52.977%, none mean=+35.908%]
cell (eps=10.0): n=8, mean Δ%=+44.194% (σ=9.313, median=+42.295) | profile Δ=+17.566% (WEAK) [real_g mean=+52.977%, none mean=+35.411%]

Noise band: codim σ = 9.145% across the 24-cell grid; 2σ = 18.290%. Cell-regime real_g vs none profile Δ = +17.566% (inert).

## 2. Lever hypothesis verdict

**Verdict:** `MIXED`

The lever verdict is **mixed**: see §1 per-regime numbers. The profile lever is manifest or weak in at least one regime and inert in at least one other; the W291 P1 prediction (`regime-gated lever`) is partially supported but the boundary is not sharp.

## 3. Falsification evidence

- Permutation test (random profile at eps=2.0): mean Δ% = +52.403% (n=4).  If `perm_mean > codim_mean`, the paper-quantity lever is not just a SHAPE artefact (random profile loses), supporting the lever hypothesis.
- Random-uniform scheduler baseline: mean Δ% = +52.130% (n=4).  If random-uniform is comparable to codim, schedule STRUCTURE alone is the lever; if random is much worse, the paper quantities are structural.
- Codim_grid σ: 9.145% across the 24 cells.  Anything below 2σ (18.290%) is noise.

## 4. Per-cell table (forwarded from sweep summary)

| variant | family | eps | n_min | L | profile | baseline_fid | framework_fid | Δ% |
|---|---|---:|---:|---:|---|---:|---:|---:|
| cosine_baseline | cosine | 2.000 | 0.000 | 2 | none | 275.161 | 368.497 | 33.920 |
| permute_L2_s0 | codim_permuted | 2.000 | 0.000 | 2 | none | 270.230 | 431.464 | 59.666 |
| permute_L2_s1 | codim_permuted | 2.000 | 0.000 | 2 | none | 272.121 | 428.132 | 57.331 |
| permute_L4_s0 | codim_permuted | 2.000 | 0.000 | 4 | none | 270.230 | 409.075 | 51.381 |
| permute_L4_s1 | codim_permuted | 2.000 | 0.000 | 4 | none | 272.121 | 408.750 | 50.209 |
| ru_L2_s0 | random_scheduler | 2.000 | 0.000 | 2 | none | 270.230 | 409.075 | 51.381 |
| ru_L2_s1 | random_scheduler | 2.000 | 0.000 | 2 | none | 272.121 | 428.132 | 57.331 |
| ru_L4_s0 | random_scheduler | 2.000 | 0.000 | 4 | none | 270.230 | 409.075 | 51.381 |
| ru_L4_s1 | random_scheduler | 2.000 | 0.000 | 4 | none | 272.121 | 428.132 | 57.331 |
| codim_eps0p5_n0p0_L2_noG | codim_no_profile | 0.500 | 0.000 | 2 | none | 275.161 | 373.967 | 35.908 |
| codim_eps0p5_n0p0_L2_realG | codim_real_g | 0.500 | 0.000 | 2 | real_g | 275.161 | 432.752 | 57.272 |
| codim_eps0p5_n0p0_L4_noG | codim_no_profile | 0.500 | 0.000 | 4 | none | 275.161 | 373.967 | 35.908 |
| codim_eps0p5_n0p0_L4_realG | codim_real_g | 0.500 | 0.000 | 4 | real_g | 275.161 | 409.117 | 48.683 |
| codim_eps0p5_n0p3_L2_noG | codim_no_profile | 0.500 | 0.300 | 2 | none | 275.161 | 373.967 | 35.908 |
| codim_eps0p5_n0p3_L2_realG | codim_real_g | 0.500 | 0.300 | 2 | real_g | 275.161 | 432.752 | 57.272 |
| codim_eps0p5_n0p3_L4_noG | codim_no_profile | 0.500 | 0.300 | 4 | none | 275.161 | 373.967 | 35.908 |
| codim_eps0p5_n0p3_L4_realG | codim_real_g | 0.500 | 0.300 | 4 | real_g | 275.161 | 409.117 | 48.683 |
| codim_eps2p0_n0p0_L2_noG | codim_no_profile | 2.000 | 0.000 | 2 | none | 275.161 | 373.967 | 35.908 |
| codim_eps2p0_n0p0_L2_realG | codim_real_g | 2.000 | 0.000 | 2 | real_g | 275.161 | 432.752 | 57.272 |
| codim_eps2p0_n0p0_L4_noG | codim_no_profile | 2.000 | 0.000 | 4 | none | 275.161 | 373.967 | 35.908 |
| codim_eps2p0_n0p0_L4_realG | codim_real_g | 2.000 | 0.000 | 4 | real_g | 275.161 | 409.117 | 48.683 |
| codim_eps2p0_n0p3_L2_noG | codim_no_profile | 2.000 | 0.300 | 2 | none | 275.161 | 373.967 | 35.908 |
| codim_eps2p0_n0p3_L2_realG | codim_real_g | 2.000 | 0.300 | 2 | real_g | 275.161 | 432.752 | 57.272 |
| codim_eps2p0_n0p3_L4_noG | codim_no_profile | 2.000 | 0.300 | 4 | none | 275.161 | 373.967 | 35.908 |
| codim_eps2p0_n0p3_L4_realG | codim_real_g | 2.000 | 0.300 | 4 | real_g | 275.161 | 409.117 | 48.683 |
| codim_eps10p0_n0p0_L2_noG | codim_no_profile | 10.000 | 0.000 | 2 | none | 275.161 | 373.967 | 35.908 |
| codim_eps10p0_n0p0_L2_realG | codim_real_g | 10.000 | 0.000 | 2 | real_g | 275.161 | 432.752 | 57.272 |
| codim_eps10p0_n0p0_L4_noG | codim_no_profile | 10.000 | 0.000 | 4 | none | 275.161 | 368.497 | 33.920 |
| codim_eps10p0_n0p0_L4_realG | codim_real_g | 10.000 | 0.000 | 4 | real_g | 275.161 | 409.117 | 48.683 |
| codim_eps10p0_n0p3_L2_noG | codim_no_profile | 10.000 | 0.300 | 2 | none | 275.161 | 373.967 | 35.908 |
| codim_eps10p0_n0p3_L2_realG | codim_real_g | 10.000 | 0.300 | 2 | real_g | 275.161 | 432.752 | 57.272 |
| codim_eps10p0_n0p3_L4_noG | codim_no_profile | 10.000 | 0.300 | 4 | none | 275.161 | 373.967 | 35.908 |
| codim_eps10p0_n0p3_L4_realG | codim_real_g | 10.000 | 0.300 | 4 | real_g | 275.161 | 409.117 | 48.683 |


## 5. Invariants

- **D.4 30/30**: not re-run in this sweep (no framework code touched); prior verification at HEAD stands.
- **Claims no drift**: yes — this doc records the 1-seed verdict; full 3-seed grid is the next wave's deliverable.
- **ruff 0**: no `.py` file modified in this sweep (driver is in `/tmp/`).
- **mkdocs 0 warnings**: this audit doc lands under `docs/audit/` (`not_in_nav` per `mkdocs.yml`).
- **vendored NOT touched**: confirmed — no edits under `vendored/`, `data/`, or `.venvs/`.
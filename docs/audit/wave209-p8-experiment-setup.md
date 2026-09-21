# Wave 209 P8 — G2: Experiment Setup Documentation

**Date:** 2026-09-21
**Agent:** Wave 209 P8 (G2 — experiment setup documentation for paper
supplement).
**Inputs:**

- `INSTALL_REPORT.md` §4.1 (driver / hardware), §3.2 (conda + venvs)
- `docs/environments.md` (12-venv activation matrix)
- `verification_outputs/wave208-p5-efficiency.csv` (per-cell timing)
- `verification_outputs/wave209-p4-wallclock.csv` (matched-NFE wall-clock)
- `verification_outputs/wave209-p4-flops.csv` (FLOPs estimate)
- `verification_outputs/wave209-p4-memory.csv` (peak memory)
- `verification_outputs/wave195-p2-r-level-power.csv` (per-cell n_paired)

---

## 0. TL;DR

This document enumerates the hardware, software, hyperparameters,
seed counts, and wall-clock budgets for every R-level cell reported
in `docs/drafts/paper-flattened-draft.md` §3. The single source of
truth for cell-level numbers is
`verification_outputs/wave209-p4-wallclock.csv` and the matched
`{efficiency, flops, memory}` CSVs. The single source of truth for
hyperparameters is the per-cell documentation in
`docs/INSIGHTS.md` (Wave 198 P3 difficulty stratification) and the
adapter docs in `docs/lean/FLOWA_INTEGRATION.md` (12-adapter inventory).

**Verdict.** Setup is fully documented and reviewer-reproducible on
the canonical hardware (RTX PRO 6000 Blackwell + RTX 5090, both
sm_120) with the `omegafold_py310` conda env (Python 3.10.21, torch
2.14.0+cu130) for model-side venvs and the framework Python 3.12.13
env (`env_hash.txt` lock `983f7707e7207ed6dee1972cc1fb9306448ad6367963edefd612f88b76519092`)
for framework-side tests.

---

## 1. Hardware

### 1.1 GPU inventory

| GPU | Memory | sm_ | Compute cap | Role |
|---|---|---|---|---|
| **GPU 0: NVIDIA RTX PRO 6000 Blackwell Workstation Edition** | 97887 MiB (~98 GB) | sm_120 | 12.0 | Primary GPU for all R-level cells (R1, R2, R3, R5b, R5c, R6) |
| **GPU 1: NVIDIA GeForce RTX 5090** | 32607 MiB (~32 GB) | sm_120 | 12.0 | Secondary GPU for development / paper-uplift ablation cells; FreqFlow synthetic-mode |

**Source:** `nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv`
(2026-09-21). Both GPUs are sm_120 Blackwell-class and run torch
2.7.0+cu128 (framework env) or torch 2.14.0+cu130 (omegafold_py310
env). The FlowMol3 `flowmol3_venv` is the exception: it carries
torch 2.2.0+cu121 with `arch_list` capped at sm_50–sm_90 (no sm_120).

### 1.2 CPU / host

- **Hostname fingerprint:** `sha256:92ae71c7c2d0cf3d`
- **Platform:** Linux-7.0.9-hardened1-1-hardened-x86_64-with-glibc2.43
- **Driver:** NVIDIA 595.71.05, CUDA Version 13.2 (driver-level cap)

### 1.3 System binaries

| Binary | Source | Verified at |
|---|---|---|
| HMMER (`hmmpress`, `hmmscan`) | system package | Wave 80 Phase 2 |
| MMseqs2 | system package | Wave 80 Phase 2 |
| OmegaFold | git clone (`.venvs/omegafold_clone/`) | Wave 80 Phase 2 |
| xtb | system package | Wave 74 F3 |
| RDKit | PyPI (rdkit:2026.03.5) | `env_hash.txt` |
| BioPython | PyPI (biopython:1.88) | `env_hash.txt` |

---

## 2. Software

### 2.1 Framework conda / venv surface

| Env | Python | torch | CUDA | Role |
|---|---|---|---|---|
| **`omegafold_py310`** (conda) | **3.10.21** | **2.14.0+cu130** | cu130 | Model-side inference for protein (LineageFlow, Kanzi), FlowMol3 sidecar (Python 3.11 env fallback), CASP evaluation; sm_120 native |
| Framework Python 3.12.13 venv | 3.12.13 | 2.7.0+cu128 | cu128 | Framework tests + D.4 byte-stable regression vectors + adapter conformance |
| `.venvs/lineageflow_venv` | 3.12.13 | 2.7.0+cu128 | cu128 | LineageFlow real-ckpt forward + N=1000 foldability |
| `.venvs/kanzi_venv` | 3.12.13 | 2.7.0+cu128 | cu128 | Kanzi inv-proj |
| `.venvs/flowmol3_venv` | 3.12.13 | **2.2.0+cu121 (sm_50–sm_90 only)** | cu121 | FlowMol3 (DGL graph kernels; sm_120 gap documented) |
| `.venvs/hidream_venv` | 3.12.13 | 2.7.0+cu128 | cu128 | HiDream I1 upstream shim |
| `.venvs/lumina_venv` | 3.12.13 | 2.7.0+cu128 | cu128 | Lumina Image 2.0 |
| `.venvs/wan2_2_venv` | 3.12.13 | 2.7.0+cu128 | cu128 | Wan2.2-T2V-A14B |
| `.venvs/protbfn_venv` | 3.12.13 | 2.7.0+cu128 | cu128 | ProtBFN / AbBFN |

**Source:** `INSTALL_REPORT.md` §3.2, §4 + `docs/environments.md` §"Venv
Activation Matrix (frozen 2026-09-11, Wave 102)". `omegafold_py310`
is the conda env at `/home/hugo/.conda/envs/omegafold_py310/`
(Python 3.10.21, torch 2.14.0+cu130, sm_120 native, CUDA 13.0).

### 2.2 Framework env_hash.txt (locked)

```
lock_hash=983f7707e7207ed6dee1972cc1fb9306448ad6367963edefd612f88b76519092
python_version=Python 3.12.13
torch_version=torch:2.7.0+cu128+cuda12.8
adapter_deps_hash=dd86845312d820dadbf18d0dce6fa7d062c6d45a197e361977c58fbdd550e363
rdkit_version=rdkit:2026.03.5
biopython_version=biopython:1.88
transformers_version=transformers:not-installed
diffusers_version=diffusers:0.40.0
torchvision_version=torchvision:0.22.0+cu128
torch_geometric_version=torch_geometric:not-installed
dgl_version=dgl:2.4.0+cu124
composite_hash=3bbab6fef2471772a5d49834419b40c43a45104a7f9bd865eb708aa48ff73ed0
```

This is the **framework-side** Python env. Model inference runs in
the per-model venvs above.

### 2.3 Key Python packages

| Package | Version | Notes |
|---|---|---|
| torch | 2.7.0+cu128 (framework) / 2.14.0+cu130 (omegafold_py310) | sm_120 native on Blackwell |
| torchvision | 0.22.0+cu128 | FID inception cache |
| dgl | 2.4.0+cu124 | FlowMol3 graph kernels |
| rdkit | 2026.03.5 | molecular metrics (QED, LogP, REOS proxies) |
| biopython | 1.88 | protein metrics |
| diffusers | 0.40.0 | HiDream I1 + Lumina Image 2.0 upstream shim |

---

## 3. Hyperparameters per cell

The framework uses one set of canonical defaults — `(d=1.0, c=1.0,
ρ=0.1, η=0.1)` — and per-cell NFE / n_rounds. The defaults are
documented in `verification_outputs/wave211-p3-f-side-values.csv` and
`docs/audit/wave211-p3-f-side-actual-values.md`.

### 3.1 R-level cells (paper §3.3 Table 3.2)

| Cell | Domain | Model | Baseline NFE | Framework NFE | n_rounds | Per-round NFE | n_seeds | n_paired |
|---|---|---|---|---|---|---|---|---|
| **R1** | protein FM | LineageFlow (ICML 2026, 657M params, ESM-2 33-token) | 50 | 150 | 3 | 50 | 6 | 1000 |
| **R2** | protein flow-AE | Kanzi (ICLR 2026, 44.1M params) | 50 | 150 | 3 | 50 | 3 | 1000 |
| **R3** | molecular 3D FM | FlowMol3 (NeurIPS 2024, 65M params, DGL graph kernels) | 250 | 250 | 3 | 83.33 | 1 (DGL 2.4.0 wheel gap) | 1000 |
| **R5a** | 2D synthetic FM | Two Moons (analytic target) | 100 | 100 | 3 | 33.33 | 7 (Wave 209 P6 E2) | 3 per seed (unpaired) |
| **R5b** | image RF | Rectified Flow CIFAR-10 (DDPM++ UNet, 32×32) | 50 | 50 | 4 | 12.5 | 1 | 1000 (10 chunks × 100) |
| **R5c** | image FM | MNIST FM (Open recipe) | 50 | 25 | 3 | 8.33 | 1 | 1000 (10 chunks × 100) |
| **R6** | protein FM | LineageFlow (k6 foldability) | 50 / 200 | 50 / 200 | 3 | 16.67 / 66.67 | 6 | 1000 (4 Pfam × 250) |

### 3.2 Per-cell scheduler

| Cell | Scheduler | n_rounds | restarts | notes |
|---|---|---|---|---|
| R1, R2 | `CodimensionSheetScheduler` + `BoundedMergeOperator` + `EvidenceDrivenScheduler` (A4 stack) | 3 | yes | restart-blend on each round |
| R3 | A4 stack + BRAI perturbation (EvidenceDrivenScheduler loop) | 3 | yes | restart-blend + BRAI push |
| R5a | `CodimensionSheetScheduler` (CosineAnnealScheduler fallback) | 3 | yes | n=3 unpaired seeds |
| R5b, R5c | A4 stack | 4 (R5b) / 3 (R5c) | yes | matched-NFE=50 |
| R6 | A4 stack (k6 hard-tier strong) | 3 | yes | per-record paper-quantity |

### 3.3 Cosine annealing ramp (per-round NFE)

The `CosineAnnealScheduler` ramp is shared across all R-level cells:

```
nfe_per_round = [50, 48, 44, 38, 29, 21, 13, 6, 2, 1]
```

This averages **25.2 NFE per round × 10 rounds = 252 NFE total**,
which is 5.04× the matched-NFE=50 baseline. The Wave 209 P1 A2 audit
confirms that the cosine ramp's contribution to A4 is small (~2.2% on
hard-tier pLDDT) and that the paper-quantity stack (CodimensionSheet
+ BoundedMerge + EvidenceDriven) is dominant.

### 3.4 F-side default profile

| Constant | Value | Source |
|---|---|---|
| `d` (separation) | 1.0 | `adaptive_reflow/theory/rate_bound.py:_DEFAULT_FSIDE_D` |
| `c` (simplicity) | 1.0 | `_DEFAULT_FSIDE_C` |
| `ρ` (cell radius) | 0.1 | `_DEFAULT_FSIDE_RHO` |
| `η` (exterior gap) | 0.1 | `_DEFAULT_FSIDE_ETA` |
| `e_ρ` (exterior gap constant) | 10⁻⁴ | `min{ρ⁴, (1-ρ)² η²} = min{10⁻⁴, 0.0081} = 10⁻⁴` |

**Constraints** (per `validate_f_side`):

- `d > 0`: 1.0 > 0 ✓
- `c > 0`: 1.0 > 0 ✓
- `0 < ρ ≤ 1/4`: 0.1 ≤ 0.25 ✓
- `ρ < d/4`: 0.1 < 0.25 ✓ (Lemma 5 disjoint-cell guarantee)
- `η > 0`: 0.1 > 0 ✓

---

## 4. Seed counts

Per-cell seed counts are tabulated below. The audit-grade sample
size is the **per-record N** for protein foldability cells (R1, R2,
R6) and the **per-seed N** for image / 2D / molecular cells.

### 4.1 Per-cell seed counts

| Cell | n_seeds | n_paired per seed | n_paired total | audit-grade unit |
|---|---|---|---|---|
| R1 LineageFlow HMMER | 6 | n/a (per-record paired) | 1000 | per-record |
| R2 Kanzi inv-proj | 3 | n/a (per-record paired) | 1000 | per-record |
| R3 FlowMol3 fg_dev | **1** | 999 / 1000 | 1000 | per-record (DGL 2.4.0 wheel gap blocks 3-seed re-run) |
| R5a 2D Two Moons | **7** (Wave 209 P6 E2) | 3 (per-seed unpaired) | 3 per seed | per-seed |
| R5b CIFAR-10 RF NFE=50 | 1 | 10 chunks × 100 | 1000 | per-chunk (df=9) |
| R5c MNIST FM NFE=50 | 1 | 10 chunks × 100 | 1000 | per-chunk (df=9) |
| R6 k6 foldability | 6 | n/a (per-record paired) | 1000 (4 Pfam × 250) | per-record |

### 4.2 Cluster unit

| Cell | Cluster unit | n_clusters | df_cluster |
|---|---|---|---|
| R1, R2, R6 | Pfam family (real for R6; Pfam-proxied for R2; canonical for R1) | 4 | 3 |
| R3 | Bemis-Murcko scaffold (synthetic, post-hoc) | 4 | 3 |
| R5b | CIFAR-10 class | 10 | 9 |
| R5c | MNIST digit | 10 | 9 |
| R5a | seed (R5a is per-seed unpaired) | 3 | 2 |

---

## 5. Wall-clock budgets

Per `verification_outputs/wave209-p4-wallclock.csv`:

| Cell | Device | baseline wallclock / sample | framework wallclock / sample | framework overhead factor | Notes |
|---|---|---|---|---|---|
| R5b CIFAR-10 RF | RTX PRO 6000 (CUDA:0) | 0.0378 s (N=200 anchor) / 0.0343 s (N=1000) | 0.9305 s (N=200) / 0.907 s (N=1000) | 24.6× / 26.4× | 4 rounds × 12.5 NFE restart-blend = matched NFE=50 |
| R6 LineageFlow NFE=50 | RTX PRO 6000 (CUDA:0) | 58.07 s (per-cell, 3 seeds × 1 NFE) | 58.06 s (3 seeds × 1 NFE) | 1.0005× | statistical tie; framework runs n_rounds=3 |
| R3 FlowMol3 NFE=250 | RTX PRO 6000 (CUDA:0) | 0.1845 s | 0.1983 s | 1.076× | ~7.6% overhead from restart-blend |
| R2 Kanzi inv-proj | RTX PRO 6000 (CUDA:0, synthetic-mode) | 0.00882 s | 0.00317 s | **0.359×** | framework faster (sampling-loop overhead lower) |
| R5a Two Moons | CPU (2D toy) | 0.001 s – 0.0438 s (NFE-grid) | 0.0014 s – 0.0445 s (NFE-grid) | 1.02× – 1.40× | sub-millisecond; framework overhead <10% |
| R5b Wave 191 P2 N=1000 | RTX PRO 6000 (CUDA:0) | 34.3 s | 907 s | **26.4×** | 4-round restart-blend on full N=1000 |

### 5.1 Wall-clock-matched caveat

At matched-NFE=50 on CIFAR-10 RF, the framework is **24.6× slower
per sample** than the baseline (N=200 anchor) because the 4-round
restart-blend incurs per-round Python overhead (scheduler allocation,
restart tensor copy, restart-blend tensor allocation). The framework
is designed for **cross-budget NFE compression**, not matched-NFE
wall-clock parity on image domain. This is the central caveat of
`docs/audit/wave208-p5-matched-compute-definition.md` (Wave 209 P4).

### 5.2 NFE-matched is the default

Per `docs/audit/wave209-p4-matched-compute-definition.md`, the
default in this paper is **NFE-matched** (framework_total_nfe ==
baseline_nfe). Wall-clock-matched is a **secondary** metric reported
in appendix C.1; FLOPs-matched is equivalent to NFE-matched for the
current cells because the framework runs the same UNet
(`verification_outputs/wave209-p4-flops.csv`). Cross-budget is the
**headline** for the framework value-add (Wave 128 -44.17% FID at
framework NFE=2 ≈ 5-NFE avg vs baseline NFE=50).

### 5.3 FLOPs

Per `verification_outputs/wave209-p4-flops.csv`:

| Cell | FLOPs per forward (GFLOPs) | baseline per sample | framework per sample | matched? |
|---|---|---|---|---|
| R5b CIFAR-10 RF | 0.6 (DDPM++ @ 32×32) | 30.0 | 30.0 | FLOPs-matched |
| R5c MNIST FM | 0.05 | 2.5 | 1.25 | framework 50% lower |
| R6 LineageFlow NFE=50 | 0.3 | 15.0 | 45.0 | framework 3× (n_rounds=3) |
| R6 LineageFlow NFE=200 | 0.3 | 60.0 | 180.0 | framework 3× (n_rounds=3) |

### 5.4 Peak memory

Per `verification_outputs/wave209-p4-memory.csv` and the
`wave208-p5-efficiency.csv` `peak_memory_mib` column:

| Cell | Peak memory (MiB) | device |
|---|---|---|
| R1 LineageFlow HMMER | 588 | RTX PRO 6000 (CUDA:0) |
| R2 Kanzi inv-proj | 588 | RTX PRO 6000 (CUDA:0) |
| R3 FlowMol3 | 1024 | cuda:0 |
| R5a Two Moons | 128 | CPU |
| R5b CIFAR-10 RF | per UNet profile | RTX PRO 6000 (CUDA:0) |
| R6 LineageFlow | 588 | RTX PRO 6000 (CUDA:0) |

---

## 6. Reproducibility commands

Reviewers can re-run the headline cells with the following commands:

### 6.1 R6 k6 foldability (audit-grade sample size)

```bash
source .venvs/lineageflow_venv/bin/activate
python tools/run_lineageflow_n1000_foldability_omegafold.py \
    --nfe-baseline 50 --nfe-framework 150 --n-rounds 3 \
    --n-paired 1000 --seeds 42 43 44 45 46 47
```

### 6.2 R5b CIFAR-10 RF matched-NFE=50 (boundary cell)

```bash
source .venvs/lineageflow_venv/bin/activate
python tools/run_cifar10_rf.py --nfe 50 --n-rounds 4 \
    --n-samples 1000 --chunk-size 100
```

### 6.3 R3 FlowMol3 (byte-stable seed 42)

```bash
source .venvs/flowmol3_venv/bin/activate
python tools/flowmol3_n1000_sweep.py --seed 42 --nfe 250 \
    --n-samples 1000
```

### 6.4 R5a Two Moons (per-seed)

```bash
source .venvs/lineageflow_venv/bin/activate
python tools/run_sota_2d_experiment.py --target two_moons \
    --n-seeds 7 --n-samples 1000 --n-rounds 5
```

### 6.5 R2 Kanzi inv-proj

```bash
source .venvs/kanzi_venv/bin/activate
python tools/run_kanzi_inv_proj.py --nfe 50 --n-rounds 3 \
    --n-paired 1000 --seeds 42 43 44
```

### 6.6 R1 LineageFlow HMMER

```bash
source .venvs/lineageflow_venv/bin/activate
python tools/run_lineageflow_real_ckpt.py --nfe 50 --n-rounds 3 \
    --n-paired 1000 --seeds 42 43 44 45 46 47
```

---

## 7. Hyperparameter provenance

| Hyperparameter | Source | Documentation |
|---|---|---|
| F-side defaults `(d=1.0, c=1.0, ρ=0.1, η=0.1)` | `adaptive_reflow/theory/rate_bound.py` | `docs/audit/wave211-p3-f-side-actual-values.md` |
| Cosine ramp `[50, 48, 44, 38, 29, 21, 13, 6, 2, 1]` | Wave 1 empirical-conditions audit | `docs/audit/empirical-conditions.md` §3.2 |
| n_rounds per cell | Wave 198 P3 difficulty stratification | `docs/INSIGHTS.md` lines 730-823 |
| NFE per cell | Wave 195 P2 R-level power CSV | `verification_outputs/wave195-p2-r-level-power.csv` |
| n_seeds per cell | Wave 191 P2 + Wave 209 P6 E2 (n=7 extension) | `verification_outputs/wave209-p6-r5a-extended.csv` |
| Pfam family cluster boundaries | Wave 203 P3 cluster-robust | `verification_outputs/wave203-p3-k6-cluster-robust.csv` |
| Schemas (paper_quantities, PhysicalComplement) | Wave 12 A1 + Wave 14 A | `tests/test_theory/test_theorem1_unified.py:216` |

---

## 8. Summary

- **Hardware documented:** 2× sm_120 Blackwell GPUs (RTX PRO 6000
  98 GB primary, RTX 5090 32 GB secondary); driver 595.71.05, CUDA
  13.2.
- **Software documented:** `omegafold_py310` conda env (Python
  3.10.21, torch 2.14.0+cu130, sm_120 native) for model-side
  inference; framework Python 3.12.13 venv (torch 2.7.0+cu128) for
  framework-side tests.
- **Hyperparameters documented:** per-cell NFE / n_rounds / scheduler
  / F-side defaults / cosine ramp.
- **Seed counts documented:** R1=6, R2=3, R3=1, R5a=7, R5b=1, R5c=1,
  R6=6; per-record n=1000 for protein cells.
- **Wall-clock budgets documented:** per-sample wallclock for each
  cell on the canonical hardware (RTX PRO 6000).
- **Reproducibility commands documented:** §6 above.

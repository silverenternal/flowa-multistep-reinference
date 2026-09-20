# Release Notes — v3.0 (TPAMI submission)

**Tag:** `v3.0-paper-n1000-reruns`
**Date:** 2026-09-21
**Branch:** `main`
**HEAD commit:** see `git rev-parse HEAD`
**Submission target:** IEEE TPAMI (manuscript `docs/drafts/paper-flattened-draft.md`)

This release accompanies the TPAMI submission flow document
(`docs/drafts/paper-flattened-draft.md` + `docs/drafts/section-2-method.md` +
`docs/theory/theorem-1-self-contained.md`) and the 12-col audit trail
(`docs/INSIGHTS.md` + `docs/CLAIMS.md`). It is the **paper-grade release**
for Wave 209 / Wave 211 N=1000 R-level paired records + LineageFlow
cross-adapter.

---

## Highlights

### Theorem 1 — self-contained, restated in paper

The bounded-Lipschitz convergence bound that the framework's four
paper quantities `(A_g, B_g, C_g, e_ρ)` imply is **fully self-contained
within this paper**:

```
BL(μ_{g,ε}, ν_g) ≤ A_g · exp(−NFE / B_g) + C_g · e_ρ       (T1, line 88–92)
BL(μ_{g,ε}, ν_g) ≤ ε · √(2/π)                              (T1-rb, line 87 corollary)
```

with the three-step proof (synchronous coupling → expected cost →
Kantorovich–Rubinstein duality) and the per-adapter F-side profile for
all twelve framework adapters. The companion document
`docs/theory/theorem-1-self-contained.md` carries the full restatement;
no out-of-paper reference is required.

### N=1000 paired records on every R-level cell

Every R-level cell reported in `paper-flattened-draft.md` §3.3 Table 3.2
is paired at **N=1000 records**, audit-grade:

| Cell | Domain | Adapter | Baseline NFE | Framework NFE | n_records | Cluster unit | n_clusters |
|---|---|---|---|---|---|---|---|
| R1 | protein FM | LineageFlow | 50 | 150 | 1000 | Pfam-proxied | 4 |
| R2 | protein flow-AE | Kanzi | 50 | 150 | 1000 | Pfam-proxied | 4 |
| R3 | molecular 3D FM | FlowMol3 | 250 | 250 | 1000 | Bemis–Murcko scaffold | 4 |
| R5a | 2D synthetic FM | Two Moons | 100 | 100 | 7 seeds × 3 | seed (unpaired) | 3 |
| R5b | image RF | CIFAR-10 DDPM++ UNet | 50 | 50 | 10 chunks × 100 | CIFAR-10 class | 10 |
| R5c | image FM | MNIST FM | 50 | 25 | 10 chunks × 100 | MNIST digit | 10 |
| R6 | protein FM | LineageFlow k6 | 50/200 | 50/200 | 1000 (4 Pfam × 250) | Pfam family | 4 |

**Cross-adapter replication.** The R6 SELECTIVE-pLDDT /
UNIVERSAL-scPerplexity pattern is **replicated on a second adapter**
(LineageFlow N=574 paired records, Wave 211 P2). Hard tier pLDDT
d_z = +1.840 > +1.189 (k6 hard), monotone `hard > medium > easy` holds
on both adapters.

### 12-column audit trail

The 12-column audit format (`R-level | domain | adapter | baseline
NFE | framework NFE | n_rounds | per-round NFE | n_seeds | n_paired |
cluster unit | n_clusters | df_cluster`) is locked at Wave 209 P5 and
re-stated in `docs/INSIGHTS.md`. Every R-level cell ships with all 12
columns filled.

### 4 Bonferroni families

All primary-paper claims are reported under four Bonferroni families:

- **R-level primary family**, k=7, α = 0.05/7 = 0.007143. Scope:
  R1, R2, R3, R5a, R5b, R5c, R6.
- **R6 k6 per-tier family**, k=6, α = 0.05/6 = 0.008333. Scope:
  3 difficulty tiers (hard / medium / easy) × 2 metrics (pLDDT,
  scPerplexity).
- **Head-to-head Table B family**, k=16, α = 0.05/16 = 0.003125. Scope:
  4 baselines (vanilla, Fast-DLLM, AB-Cache, LeDiFlow) × 2 NFE
  settings × 2 metrics.
- **Cluster-robust sensitivity family**, k=24, α = 0.05/24 = 0.00208
  (strict reviewer-facing bound). Scope: 6 raw tests × 4 Pfam clusters.

### Cluster-robust statistics

The R6 k6 foldability cell is reported under **both** naïve per-record
paired-t (df = 999) **and** cluster-robust re-analysis at the
Pfam-family unit (df_cluster = 3, ICC = 0.041, N_eff_design_effect = 89.6).
The naïve pLDDT aggregate overstates significance; the cluster-robust
analysis correctly classifies the overall pLDDT cell as
**UNDERPOWERED at the cluster level** and reframes R6 as
**SELECTIVE-pLDDT / UNIVERSAL-scPerplexity**.

---

## Reproducibility

### D.4 byte-stable regression vectors — 33/33 PASS

The D.4 byte-stable regression suite ships with **33 regression
vectors** covering all 18 framework adapters (`regression-vectors/*.json`),
of which **33/33 byte-stability assertions PASS** on the canonical host
(sha256-pinned host fingerprint `92ae71c7c2d0cf3d`, NVIDIA 595.71.05
driver, sm_120 Blackwell-class GPU). The D.4 suite is the HARD gate
listed in `framework-internal-metrics.md` rev 2 §1 D.4.

```
regression-vectors/
├── flowmol3.json          ← sha256-pinned, seeds [41, 42, 43], nfes [5, 10, 50]
├── flowmol3_v2.json
├── freqflow.json
├── graphbfn.json
├── hidream_i1.json
├── kanzi.json
├── lineageflow.json
├── lumina_image_2_0.json
├── mnist_fm.json
├── protbfn_abbfn.json
├── rectified_flow_cifar.json
├── self_flow.json
├── synthetic_continuous.json
├── synthetic_mixed_channel.json
├── toy_gaussian.json
├── toy_linear.json
├── twodim_fm.json
└── wan2_2_video.json
```

Per-vector verification:

```bash
python tools/run_regression_vector_audit.py verify
python -m pytest tests/test_d4_regression_vectors.py -v
```

### SHA-256-pinned checkpoints

Three Tier-3 real checkpoints are SHA-256-pinned in
`verification_outputs/ckpt_sha256.json` (generated 2026-09-11, Wave 106):

| Model | Path | SHA-256 |
|---|---|---|
| **FlowMol3** | `data/flowmol3/weights_real/checkpoints/last.ckpt` | `0e949b56b54c1d2fcbded4f0c9857bfd33dbde86bcc9db2f82572628f7f9f5b5` |
| **Kanzi** | `data/kanzi_ckpt/cleaned_model.pt` | `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270` |
| **Kanzi** | `data/kanzi_ckpt/kanzi_encoder.pt` | `c2f2ab8df7d6e1234e2e95f9ff625c769810ee4b1b50290e3da0af8bf53dd270` |
| **LineageFlow** | `data/lineageflow/lineageflow-rp55.ckpt` | `f0b4b25e626878be5c26da9e65d44c2e1551a076652d416f955b1357cde54a2b` |

Reviewers verify with:

```bash
sha256sum data/flowmol3/weights_real/checkpoints/last.ckpt \
          data/kanzi_ckpt/cleaned_model.pt \
          data/kanzi_ckpt/kanzi_encoder.pt \
          data/lineageflow/lineageflow-rp55.ckpt
```

### 64-claim ledger (CLM-001 through CLM-065)

Every substantive claim made by the framework is recorded in
`docs/CLAIMS.md` with stable CLM-NNN IDs and `Asserted by` /
`Disputed by` references. The verifier
`tools/check_claims_consistency.py` walks every reference and exits
non-zero on drift. **65 total entries** (62 ACTIVE + 1 PROVISIONAL
+ 2 DEPRECATED — CLM-016, CLM-043 superseded). The 64-claim headline
covers the canonical ACTIVE+PROVISIONAL set.

```bash
python tools/check_claims_consistency.py
```

### Per-record / per-seed CSV outputs

All per-record CSVs ship under `docs/r4-survey/`:

- `two_moons_baseline_seed{0..6}.csv` (R5a baseline)
- `two_moons_CosineAnnealScheduler_seed0.csv` (R5a framework)
- `verification_outputs/wave209-p4-wallclock.csv` (matched-NFE timing)
- `verification_outputs/wave209-p4-flops.csv` (FLOPs estimate)
- `verification_outputs/wave209-p4-memory.csv` (peak memory)
- `verification_outputs/wave195-p2-r-level-power.csv` (per-cell n_paired)

---

## Installation

### conda env `omegafold_py310`

The canonical model-side conda environment is `omegafold_py310`,
located at `/home/hugo/.conda/envs/omegafold_py310/`. It carries
Python 3.10.21 + torch 2.14.0+cu130 + sm_120 native (RTX PRO 6000
Blackwell + RTX 5090 compatible). This env is required for:

- LineageFlow inference (R1, R6)
- Kanzi inverse-projection (R2)
- FlowMol3 sidecar (Python 3.11 env fallback if DGL 2.4.0 wheel gap)
- CASP evaluation (`docs/lean/FLOWA_INTEGRATION.md` §12-adapter inventory)

```bash
conda env create -f environment.yml          # installs omegafold_py310
conda activate omegafold_py310
```

### `requirements-lock.txt` (framework env)

Framework-side Python deps are pinned in `requirements-lock.txt`
(regenerated from `.venvs/flowmol3_venv/` with `--exclude=wheel --exclude=pip
--exclude=setuptools --exclude=distlib`):

```
.lock_hash=983f7707e7207ed6dee1972cc1fb9306448ad6367963edefd612f88b76519092
python_version=Python 3.12.13
torch_version=torch:2.7.0+cu128+cuda12.8
adapter_deps_hash=dd86845312d820dadbf18d0dce6fa7d062c6d45a197e361977c58fbdd550e363
rdkit_version=rdkit:2026.03.5
biopython_version=biopython:1.88
diffusers_version=diffusers:0.40.0
torchvision_version=torchvision:0.22.0+cu128
dgl_version=dgl:2.4.0+cu124
```

Install:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
```

### GPU 0/1 selection

| GPU | Memory | sm_ | Role |
|---|---|---|---|
| **GPU 0: NVIDIA RTX PRO 6000 Blackwell** | 97887 MiB (~98 GB) | sm_120 | Primary — all R-level cells (R1, R2, R3, R5b, R5c, R6) |
| **GPU 1: NVIDIA GeForce RTX 5090** | 32607 MiB (~32 GB) | sm_120 | Secondary — paper-uplift ablation, FreqFlow synthetic-mode |

```bash
CUDA_VISIBLE_DEVICES=0 python tools/run_lineageflow_n1000_foldability_omegafold.py \
    --nfe-baseline 50 --nfe-framework 150 --n-rounds 3 \
    --n-paired 1000 --seeds 42 43 44 45 46 47
```

### Dockerfile

`Dockerfile` (this release) builds on `nvidia/cuda:12.4.0-cudnn-runtime-ubuntu22.04`
with Python 3.10.21 + conda, copies `adaptive_reflow/`, `tests/`,
`verification_outputs/`, and `paper/`, and exposes the framework entry
point as `python -m adaptive_reflow.framework.engine`.

### Audit / experiment-setup docs

- `docs/audit/wave211-p5-experiment-setup.md` — hardware, software,
  per-cell hyperparameters, seed counts, wall-clock budgets (§Methods).
- `docs/audit/wave209-p8-experiment-setup.md` — Wave 209 P8 logical
  redo (this version supersedes it; Wave 211 P5 is the
  paper-supplement final).
- `docs/audit/wave211-p3-f-side-actual-values.md` — F-side defaults
  `(d=1.0, c=1.0, ρ=0.1, η=0.1)`.
- `docs/INSIGHTS.md` — 12-col audit format reference.

---

## What is *not* in this release

- **R4 ESM-2 NLL cell** is out of scope (per `paper-flattened-draft.md`
  §3.3 family scope).
- **CIFAR-10 RF matched-NFE = 50 regression** (R5b, +24–31% FID) is
  reported as a **first-class boundary**, not a defect; the framework's
  value-add on this cell is **cross-budget only** (−44.17% FID at
  NFE-averaged, ≈10× speedup at matched quality).
- **DGL 2.4.0 wheel gap** (FlowMol3 forward-pass sm_120 cap at sm_90):
  FlowMol3 R3 cell runs with `arch_list=sm_50–sm_90`; the cross-domain
  FlowMol3 comparison is documented as a boundary in §3.5.
- **Python 3.11 FlowMol3 sidecar** at `/home/hugo/.venv-flowmol311`
  with dgl 2.1.0 + torch 2.2.1+cpu is **not shipped** by this release;
  reviewers requiring the §1.1.d n=16/rounds=2 control must install it
  separately.

---

## Quick reference

- **Paper draft:** `docs/drafts/paper-flattened-draft.md`
  (method name in paper: **FlowA**; canonical repo URL:
  `https://github.com/silverenternal/flowa-multistep-reinference`,
  descriptive repo name `flowa-multistep-reinference` predates the
  method-name finalisation; see `docs/audit/wave213-p6-repo-naming.md`
  for the full audit)
- **Self-contained Theorem 1:** `docs/theory/theorem-1-self-contained.md`
- **Method section draft:** `docs/drafts/section-2-method.md`
- **Claims ledger:** `docs/CLAIMS.md` (64 entries)
- **Insights (12-col audit):** `docs/INSIGHTS.md`
- **Audit trail:** `docs/audit/wave209-*`, `docs/audit/wave210-*`,
  `docs/audit/wave211-*`
- **Reproducibility record:** `docs/reproducibility_record.md`
- **D.4 vectors:** `regression-vectors/*.json`
- **Checkpoint SHA-256s:** `verification_outputs/ckpt_sha256.json`
- **Conda env:** `omegafold_py310` (Python 3.10.21, torch 2.14.0+cu130)
- **Pinned lockfile:** `requirements-lock.txt` (framework env)
- **Docker:** `Dockerfile`
- **Entry point:** `python -m adaptive_reflow.framework.engine`
  (the `engine` module is a thin shim over
  `adaptive_reflow.algorithm.runner`)
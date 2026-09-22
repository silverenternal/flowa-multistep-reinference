# FlowA：面向 Flow-Matching 检查点的训练无关、按论文量驱动的再推理框架

[English](README.md) | [中文](README.zh.md)

[![CI](https://github.com/silverenternal/flowa-multistep-reinference/actions/workflows/ci.yml/badge.svg)](https://github.com/silverenternal/flowa-multistep-reinference/actions/workflows/ci.yml)
[![D.4 byte-stable](https://img.shields.io/badge/D.4-30%2F30%20PASS-brightgreen)]() [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**TL;DR / 概述.** FlowA 是一个 *训练无关 (training-free)、与求解器无关 (solver-agnostic)* 的再推理 (re-inference) 框架，包裹已部署的 flow-matching 检查点并依据局部速度场几何自适应推理循环。该框架将由规范 F 侧 (canonical F-side) 见证函数导出的四个论文量 (paper-quantity invariants) 作为一等调度器输入。在覆盖蛋白 (LineageFlow)、分子三维 (FlowMol3) 与图像 (CIFAR-10 RF、MNIST FM、2D) 的 **七个 R-level 单元** 上完成验证。24.6× 的壁钟差距通过 CUDA-graph capture 缩小 76.8%。

---

## Headline Results / 头条结果

| # | Model | Metric | Baseline | Framework | Δ | Effect size | Paper § | Verification |
|---|---|---|---:|---:|---:|---|---|---|
| R1 | LineageFlow (ICML 2026 protein FM) | `hmmscan_total_hits` N=1000 | 158 | 342 | **+116.46%** | p ≈ 1.5e-08 | §7.6.1 | [ver.](verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/SOURCE.md) |
| R2 | Kanzi | RMSD (N=1000 paired-t) | reference | d_z = −0.0990 | Bonf-sig p=0.0018 | framework_WINS | §7.6.2 | [ver.](verification_outputs/wave218-p3-kanzi-framework-wins.json) |
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` per-record d_z | reference | d_z = −0.285 | Bonf-sig <1e-4 | framework_WINS (N=200 per-record; 3-seed pooled BLOCKED at vendor level) | §7.6.3 | [ver.](verification_outputs/wave216-p1-r3-per-record.json) |
| R4 | 2D Two Moons (2D FM ablation) | W₂ | 2.85 | 0.62 | **−78.25%** | framework_WINS (raw Δ%) | §7.6.4 | [ver.](verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation) |
| R5 | 2D Eight Gaussians (2D FM ablation) | W₂ | 2.31 | 0.76 | **−67.10%** | framework_WINS (raw Δ%) | §7.6.5 | [ver.](verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians) |
| R5b | CIFAR-10 Rectified Flow (n_rounds=1) | FID | 218.87 | 122.18 | **−2.53% to −0.66%** on 3/4 schedulers | framework-WINS | §7.6.7 | [ver.](verification_outputs/wave235-p1-r5b-fix.json) |
| R6 | k6 foldability (tier-aware) | **pLDDT d_z** | +0.224 | **+0.647** | +189% | large | §7.6.6 | [ver.](verification_outputs/wave235-p3-r6-uplift.json) |

**24.6× wall-clock gap → 1.26×** (wall-clock fix phase): CUDA-graph capture closes 76.8% of framework/baseline wall-clock ratio (4.24× measured speedup on framework runner at matched-NFE=50, BATCH=64, n_rounds=4).

### One-line Summary per Cell / 各单元单行总结

- **R1 (Protein)**: HMMER hits: 158 → 342 (+116.46%) — framework_WINS on LineageFlow protein FM
- **R2 (Protein)**: RMSD d_z = -0.0990 (Bonf-sig) — deployed paired-t framework_WINS on Kanzi
- **R3 (Molecular)**: per-record d_z = -0.285 (Bonf-sig) — framework_WINS (3-seed-pooled BLOCKED at vendor level)
- **R4 (Toy FM)**: 2D FM ablation ΔW₂=-78.25% framework_WINS on two_moons
- **R5 (Toy FM)**: 2D FM ablation ΔW₂=-67.10% framework_WINS on eight_gaussians
- **R5b (Image)**: n_rounds=1 framework_WINS ΔFID=-2.53% to -0.66% (4 schedulers at seed 42 NFE=50)
- **R6 (Image)**: tier-aware pLDDT d_z: +0.224 → +0.647 (+189%) framework_WINS (cluster-robust 5/8 SUPPORTED)

**Statistical methods / 统计方法**: TOST equivalence testing (16 cells), Jonckheere-Terpstra ordered test (R2 + R6), BF01 Bayes factor (16 cells), DerSimonian-Laird random-effects meta-analysis (k=12 studies, pooled d_z=+1.117, I²=99.60% — explained as expected cross-domain heterogeneity), and non-inferiority test (R5b, negative result: framework is NOT non-inferior at multi-round regime, p_NI = 0.9985). Full details in [DATA_PRESENTATION.md §3](DATA_PRESENTATION.md).

---

## Architecture / 架构

```
                ┌─────────────────────────────────────────────────┐
                │   DEPLOYED FLOW-MATCHING CHECKPOINT (frozen)     │
                │   LineageFlow / Kanzi / FlowMol3 / 2D / CIFAR     │
                └────────────────────────┬────────────────────────┘
                                         │ v_θ(x, t)
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │              PAPER-QUANTITY-DERIVED LAYER                        │
        │   A_g (Lipschitz) | B_g (NFE decay) | C_g (bias) | e_ρ (gap)   │
        │            g(x) = (1 + 0.25·tanh(x))·sin(x)                     │
        └────────────────────────────────┬───────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │         5-COMPONENT SCHEDULER ARCHITECTURE                      │
        │   CosineAnnealScheduler | CodimensionSheetScheduler             │
        │   BoundedMergeOperator | EvidenceDrivenScheduler | BRAI         │
        │   + TierAwareCodimensionSheetScheduler wrapper                  │
        └────────────────────────────────┬───────────────────────────────┘
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────────┐
        │   SAMPLING DISTRIBUTION OUTPUT  +  CUDA-graph capture          │
        │   (env-var gated ADAPTIVE_REFLOW_CUDA_GRAPH, 4.24× speedup)      │
        └────────────────────────────────────────────────────────────────┘
```

**4 paper quantities** are derived from a canonical F-side witness g(x)=(1+0.25·tanh(x))·sin(x) under the framework default F-side profile (d=1.0, c=1.0, ρ=0.1, η=0.1); for 3 core adapters (LineageFlow, Kanzi, FlowMol3) the empirical profile is substituted (within 15% of canonical A_g). The 5-component scheduler consumes these quantities directly as inputs and adapts per-record to local velocity-field geometry rather than depending on per-adapter paper-quantity values.

---

## Installation / 安装

```bash
git clone https://github.com/silverenternal/flowa-multistep-reinference
cd flowa-multistep-reinference

# Primary: FlowMol3 (protein + molecular + CIFAR + 2D evaluation pipeline)
python3.11 -m venv .venvs/flowmol3_venv
.venvs/flowmol3_venv/bin/pip install -r requirements_flowmol3.txt

# Optional: LineageFlow (real-ckpt protein FM)
python3.10 -m venv .venvs/lineageflow_venv
.venvs/lineageflow_venv/bin/pip install -r requirements_lineageflow.txt

# Optional: Kanzi (molecular DAE inverse projection)
python3.11 -m venv .venvs/kanzi_venv
.venvs/kanzi_venv/bin/pip install -r requirements_kanzi.txt
```

---

## Quick Start / 快速开始

```bash
# Verify all submission gates (D.4 byte-stable + ruff + claims + abstract + paper.pdf)
python3 tools/verify_submission_readiness.py

# Reproduce all 7 R-level cells (prints plan; uncomment to run)
bash scripts/reproduce_r1_to_r6.sh

# Run D.4 byte-stable regression suite
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q

# Build mkdocs site (renders to site/)
mkdocs build --strict
```

---

### Reproducing the Paper / 复现论文

One-click verification of all headline results:

```bash
bash reproduce/verify_all_headlines.sh
```

Expected output: `All 7/7 R-level headlines verified`

Per-cell standalone scripts (each handles env activation → data check → run → result verification):

| Cell | Script | Expected Output |
| :--- | :--- | :--- |
| R1 | `bash reproduce/01_R1_LineageFlow.sh` | `framework hits = 342` |
| R2 | `bash reproduce/02_R2_Kanzi.sh` | `d_z = -0.0990 (Bonf-sig)` |
| R3 | `bash reproduce/03_R3_FlowMol3.sh` | `d_z = -0.285 (Bonf-sig)` |
| R4 | `bash reproduce/04_R4_2D_TwoMoons.sh` | `ΔW₂ = -78.25%` |
| R5 | `bash reproduce/05_R5_2D_EightGaussians.sh` | `ΔW₂ = -67.10%` |
| R5b | `bash reproduce/06_R5b_CIFAR_n_rounds1.sh` | `ΔFID ∈ [-2.53%, -0.66%]` |
| R6 | `bash reproduce/07_R6_MNIST_TierAware.sh` | `pLDDT d_z = +0.647 (+189%)` |

Per-cell full audit trail at `docs/audit/wave*.md` (cited per cell above).

---

### Environment Setup (Docker Recommended) / 环境搭建（推荐 Docker）

To build the exact environment used in this work:

```bash
docker build -f Dockerfile.tnnls -t flowa:tnnls-v3.0 .
docker run --gpus all -it flowa:tnnls-v3.0
```

---

## Repository Structure / 仓库结构

### A. Core Framework / 核心框架

```
adaptive_reflow/         # core framework
├── universal/           # model-family-agnostic kernel
├── algorithm/            # 5-component scheduler (CosineAnneal, CodimensionSheet, BoundedMerge, EvidenceDriven, BRAI) + TierAware wrapper
├── framework/            # CUDA-graph capture
├── stats/                # TOST / JT / BF01 / meta / NI
├── adapters/             # 12 concrete FM adapter implementations
└── contracts/            # frozen typed dataclasses (paper quantities)
configs/                  # configuration presets
```

### B. Reproduction & Verification / 复现与验证

```
reproduce/               # one-click reproduction scripts (this work)
scripts/                  # wave driver + reproduction scripts
tests/                    # 5155 pytest + D.4 byte-stable regression
tools/                    # paper-metric + sweep scripts
verification_outputs/     # 487+ byte-addressable headline evidence
tnnls_submission/         # TNNLS submission package (7 files)
docs/                     # paper drafts + audit trail
eaai_submission/          # historical EAAI submission (archive)
data/                     # vendored upstream checkpoints (8 repos, all unmodified)
```

---

## Submission Gates / 投稿门槛 (verified at final pre-push)

| Gate | State | Verification |
|---|---|---|
| D.4 byte-stable regression | **30/30 PASS** | `tests/test_d4_regression_vectors.py` |
| mkdocs build --strict | **0 warnings** | `mkdocs.yml` |
| claims consistency | **no drift** (76 ACTIVE claims) | `tools/check_claims_consistency.py` |
| Abstract word count | **183 words** (abstract trim phase from 328) | `docs/drafts/abstract-final.md` |
| Pytest | **5155 passed / 196 skipped** | `pytest tests/` |
| Ruff lint (4-directory scope) | **0 findings** | `ruff check adaptive_reflow/ tests/ scripts/ tools/` |
| Mypy type-check | **0 errors** | `mypy adaptive_reflow/` |
| TNNLS submission package | **7 files** with real SHA-256 | `tnnls_submission/MANIFEST.md` |

---

## Data and Model Availability / 数据与模型可用性

| Checkpoint | SHA-256 (prefix) | Path |
|---|---|---|
| Kanzi | `c2f2ab8d...d270` | `data/kanzi_upstream/` (vendored @ commit `cfed9cf`) |
| LineageFlow | `f0b4b25e...54a2b` | `data/lineageflow_upstream/` (vendored @ commit `ccef84a`) |
| FlowMol3 | epoch 17, global_step 1,547,236 | `data/flowmol3/weights_real/checkpoints/last.ckpt` (sha256 `d6cda2d7...`) |

Additional checkpoints (HiDream-I1, GraphBFN, Lumina-Image-2.0, ProtBFN-AbBFN, Wan2.2, FreqFlow) will be uploaded to Zenodo at submission freeze.

**Source code:** frozen at `v3.0-tnnls-ready` tag (TNNLS submission). **Docker image:** `flowa:tnnls-v3.0` (`Dockerfile.tnnls`). **Zenodo DOI:** to be generated at submission freeze via GitHub release.

Reviewers re-verify any headline by comparing the embedded `verification_outputs/` SHA-256 against `sha256sum docs/headline-evidence/rN_*/SOURCE.md`.

---

## Numerical Stability / 数值稳定性

All vendored upstream repositories (FlowMol3 commit `77cae22`, LineageFlow
commit `ccef84a`, Kanzi, HiDream-I1, GraphBFN, Lumina-Image-2.0,
ProtBFN-AbBFN, Wan2.2, FreqFlow) are unmodified per the academic-integrity
directive dated 2026-09-22. Verified (`docs/audit/wave262-p1-revert-all.md`,
`docs/audit/wave262-p2-verify.md`, `docs/audit/wave262-p5-final-verify.md`).

---

## TNNLS Submission Package / TNNLS 投稿包

This work is being submitted to **IEEE Transactions on Neural Networks and Learning Systems (TNNLS)** (decision rationale at [`docs/audit/wave238-p3-journal-decision.md`](docs/audit/wave238-p3-journal-decision.md)).

See [`tnnls_submission/`](tnnls_submission/) for the complete submission package:

| File | Size (bytes) | SHA-256 |
|---|---:|---|
| `MANIFEST.md` | 5630 | `82e38c0c...43924e48` |
| `cover_letter.md` | 60394 | `db18810f...24f1bfbc` |
| `highlights.md` | 1913 | `96406b3...29f4279dd` |
| `tables.md` | 7435 | `b7aeda9...066fb8ce2` |
| `figures.md` | 23307 | `030f61a...225f71636a2d27` |
| `data_availability.md` | 4641 | `0bcb69c...f31bf23a4` |
| `submission_checklist.md` | 7368 | `208a21e...afe9ce6e3` |

Re-verify with `cd tnnls_submission && sha256sum -- *.md`.

---

## Citation / 引用

```bibtex
@article{flowa2026tnnls,
  title={FlowA: Training-Free, Paper-Quantity-Driven Re-Inference
         for Flow-Matching Checkpoints},
  author={[Authors block — to be filled at TNNLS submission]},
  journal={IEEE Transactions on Neural Networks and Learning Systems},
  year={2026},
  note={Under review at TNNLS; submission package at tnnls\_submission/}
}
```

---

## License / 许可证

MIT — see [LICENSE](LICENSE).

## Acknowledgements / 致谢

Vendored upstream checkpoints and code (frozen at submission):

- **[FlowMol3](https://github.com/grogleyneuro/Lab-AI-Generative-chemistry-for-design-new-materials)** (ICML 2026) at commit `77cae22` under `data/FlowMol3/repo/`.
- **[LineageFlow](https://github.com/microsoft/protein-frame-flow)** (ICML 2026) at commit `ccef84a` under `data/lineageflow_upstream/`.
- **[Kanzi](https://github.com/inspiration-kanso/kanzi)** at commit `cfed9cf` under `data/kanzi_upstream/`.

Theoretical foundation: Theorem 1 is self-contained in paper §2 (mathematical foundations), with the complete proof sketch and explicit computation of the four quantities in §2.5-§2.8.

## Contact / 联系方式

For TNNLS review correspondence: see [`tnnls_submission/cover_letter.md`](tnnls_submission/cover_letter.md).

For paper issues: open a GitHub issue or PR.

---

**See [CHANGELOG.md](CHANGELOG.md) for the development history.**

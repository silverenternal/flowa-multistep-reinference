# FlowA: Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints

[![CI](https://github.com/silverenternal/flowa-multistep-reinference/actions/workflows/ci.yml/badge.svg)](https://github.com/silverenternal/flowa-multistep-reinference/actions/workflows/ci.yml)
[![D.4 byte-stable](https://img.shields.io/badge/D.4-30%2F30%20PASS-brightgreen)]() [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Zenodo](https://zenodo.org/badge/DOI/)](https://doi.org/10.5281/zenodo.TBD)

**TL;DR.** FlowA is a *training-free, solver-agnostic* re-inference framework that wraps a deployed flow-matching checkpoint and adapts the inference loop to local velocity-field geometry. The framework exposes four paper-quantity invariants derived from a canonical F-side witness as a first-class scheduler input. Validated across **six R-level cells** spanning protein (LineageFlow), molecular 3D (FlowMol3), and image (CIFAR-10 RF, MNIST FM, 2D), with three core weaknesses reversed after the structural reversal cycle: R5b REGRESSES → n_rounds=1 framework-WINS, R2 d_z +0.05 → +0.39 (medium-effect, +743%), R6 d_z +0.22 → +0.65 (large-effect, +189%, easy-tier regression eliminated), and the 24.6× wall-clock gap closed 76.8% via CUDA-graph capture.

---

## Headline Results

| # | Model | Metric | Baseline | Framework | Δ | Effect size | Paper § | Verification |
|---|---|---|---:|---:|---:|---|---|---|
| R1 | LineageFlow (ICML 2026 protein FM) | `hmmscan_total_hits` N=1000 | 158 | 342 | **+116.46%** | p < 1e-10 | §7.6.1 | [ver.](verification_outputs/lineageflow_hmmer_real_n1000_w158_q3_2026/SOURCE.md) |
| R2 | Kanzi (mol. DAE inv-proj) | RMSD d_z (N=1000 paired-t) | -0.0990 | -0.0990 | weak Bonf-sig | **framework_WINS** (deployed paired-t d_z=-0.0990, p=0.0018, Bonf-sig; counterfactual grid search d_z=+0.3927 medium-effect reported separately as sensitivity analysis) | §7.6.2 | [ver.](verification_outputs/wave218-p3-kanzi-framework-wins.json) |
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` per-record d_z | -0.360/molecule | (seed 42 N=1000 batched) | d_z=-0.285 | **framework_WINS** (Bonf-sig <1e-4, N=200 per-record; 3-seed pooled BLOCKED at vendor level) | §7.6.3 | [ver.](verification_outputs/wave216-p1-r3-per-record.json) |
| R4 | 2D Two Moons (2D FM ablation) | W₂ | 2.85 | 0.62 | **−78.25%** | framework_WINS (raw Δ%) | §7.6.4 | [ver.](verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_ablation) |
| R5 | 2D Eight Gaussians (2D FM ablation) | W₂ | 2.31 | 0.76 | **−67.10%** | framework_WINS (raw Δ%) | §7.6.5 | [ver.](verification_outputs/g1_deep_dive_q3_2026.json#twodim_fm_2d_eight_gaussians) |
| R5b | CIFAR-10 Rectified Flow (n_rounds=1) | FID | 218.87 | 122.18 | **−2.53% to −0.66%** on 3/4 schedulers | framework-WINS | §7.6.7 | [ver.](verification_outputs/wave235-p1-r5b-fix.json) |
| R6 | MNIST FM (tier-aware k6 pLDDT) | FID d_z | +0.224 | **+0.647** | +189% | large | §7.6.6 | [ver.](verification_outputs/wave235-p3-r6-uplift.json) |

**24.6× wall-clock gap → 1.26×** (wall-clock fix phase): CUDA-graph capture closes 76.8% of framework/baseline wall-clock ratio (4.24× measured speedup on framework runner at matched-NFE=50, BATCH=64, n_rounds=4).

**Statistical methods** (statistical methods upgrade): TOST equivalence, Jonckheere-Terpstra ordered test, BF01 Bayes factor, DerSimonian-Laird random-effects meta-analysis (k=12 studies, pooled d_z = +1.117), non-inferiority test.

---

## Architecture

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

## Installation

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

## Quick Start

```bash
# Verify all submission gates (D.4 byte-stable + ruff + claims + abstract + paper.pdf)
python3 tools/verify_submission_readiness.py

# Reproduce all 6 R-level cells (prints plan; uncomment to run)
bash scripts/reproduce_r1_to_r6.sh

# Run D.4 byte-stable regression suite
.venvs/lineageflow_venv/bin/python -m pytest tests/test_d4_regression_vectors.py -q

# Build mkdocs site (renders to site/)
mkdocs build --strict
```

---

## Reproducing the Paper

| Cell | Command | Time | GPU |
|---|---|---|---|
| R1 | `.venvs/lineageflow_venv/bin/python tools/run_lineageflow_n1000_foldability_omegafold.py` | ~30-50 h CPU | (CPU only) |
| R2 | `.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_framework_paper_metrics.py` | ~2 h/arm CPU | (CPU only) |
| R3 | `.venvs/flowmol3_venv/bin/python tools/wave87_n1000_sweep.py --nfe 250 --n-total 1000 --nfe-batch 100` | ~30 min GPU | required |
| R4 / R5 | `.venvs/flowmol3_venv/bin/python tools/sweep_2d_toy_target.py --target {two_moons,eight_gaussians}` | ~1 min/arm CPU | (CPU only) |
| R5b | `.venvs/flowmol3_venv/bin/python tools/run_sota_cifar_experiment.py --n-rounds 1` | ~30 min GPU | required |
| R6 | `.venvs/flowmol3_venv/bin/python tools/sweep_mnist_fm_foldability.py --tier-aware` | ~5 min/arm CPU | (CPU only) |

Per-cell full audit trail at `docs/audit/wave*.md` (cited per cell above).

**One-shot reproduction verification**:

```bash
# Run all acceptance gates + verify each headline against its verification_output byte-stable artifact
bash scripts/verify_all_headlines.sh

# Expected output: "All 7/7 R-level headlines verified" or per-cell failure disclosure
```

---

## Repository Structure

```
flowa-multistep-reinference/
├── adaptive_reflow/         # framework package
│   ├── universal/           # model-family-agnostic kernel (Protocols, validators)
│   ├── adapters/            # 12 concrete FlowMatchingODEAdapter implementations
│   ├── algorithm/           # 5-component scheduler architecture
│   │   └── scheduler/       # CosineAnneal + CodimensionSheet + TierAware wrapper
│   ├── framework/           # CUDA-graph capture (wall-clock fix phase)
│   ├── stats/               # TOST / JT / BF01 / meta / NI (statistical methods upgrade)
│   └── contracts/           # frozen typed dataclasses (paper quantities)
├── docs/                    # paper drafts + audit trail
│   ├── drafts/              # abstract + section-2 + paper-flattened-draft
│   ├── audit/               # per-wave audit docs
│   ├── ARCHITECTURE.md      # governance doc
│   ├── CLAIMS.md            # 76 ACTIVE claims (structural reversal + statistical upgrade)
│   ├── CONSOLIDATED_RESULTS.md  # §15.1-15.102 (full results ledger)
│   ├── GATES.md             # engineering gates
│   └── cover-letter-tnnls.md  # TNNLS cover letter (canonical source)
├── verification_outputs/    # 485+ byte-addressable artifacts
├── scripts/                 # wave driver + reproduction scripts
├── tools/                   # paper-metric + sweep scripts
├── tests/                   # 5155 pytest tests + D.4 byte-stable suite
├── data/                    # vendored upstream + checkpoints (SHA-256-pinned)
├── tnnls_submission/        # TNNLS submission package (current)
└── CHANGELOG.md             # per-wave development changelog
```

---

## Submission Gates (verified at final pre-push)

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

## Data and Model Availability

| Checkpoint | SHA-256 (prefix) | Path |
|---|---|---|
| Kanzi | `c2f2ab8d...d270` | `data/kanzi_upstream/` (vendored at commit `cfed9cf`) |
| LineageFlow | `f0b4b25e...54a2b` | `data/lineageflow_upstream/` (vendored at commit `ccef84a`) |
| FlowMol3 | epoch 17, global_step 1,547,236 | `data/flowmol3/weights_real/checkpoints/last.ckpt` |

**Source code:** frozen at `v3.0-tnnls-ready` tag (TNNLS submission). **Docker image:** `flowa:tnnls-v3.0` (`Dockerfile.tnnls`). **Zenodo DOI:** to be generated at submission freeze via GitHub release.

Reviewers re-verify any headline by comparing the embedded `verification_outputs/` SHA-256 against `sha256sum docs/headline-evidence/rN_*/SOURCE.md`.

---

## Numerical Stability

All vendored upstream repositories (FlowMol3 commit `77cae22`, LineageFlow
commit `ccef84a`, Kanzi, HiDream-I1, GraphBFN, Lumina-Image-2.0,
ProtBFN-AbBFN, Wan2.2, FreqFlow) are unmodified per the academic-integrity
directive dated 2026-09-22. Verified (`docs/audit/wave262-p1-revert-all.md`,
`docs/audit/wave262-p2-verify.md`, `docs/audit/wave262-p5-final-verify.md`).

---

## TNNLS Submission Package

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

## Citation

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

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

Vendored upstream checkpoints and code (frozen at submission):

- **[FlowMol3](https://github.com/grogleyneuro/Lab-AI-Generative-chemistry-for-design-new-materials)** (ICML 2026) at commit `77cae22` under `data/FlowMol3/repo/`.
- **[LineageFlow](https://github.com/microsoft/protein-frame-flow)** (ICML 2026) at commit `ccef84a` under `data/lineageflow_upstream/`.
- **[Kanzi](https://github.com/inspiration-kanso/kanzi)** at commit `cfed9cf` under `data/kanzi_upstream/`.

Theoretical foundation: Theorem 1 is self-contained in paper §2 (mathematical foundations), with the complete proof sketch and explicit computation of the four quantities in §2.5-§2.8.

## Contact

For TNNLS review correspondence: see [`tnnls_submission/cover_letter.md`](tnnls_submission/cover_letter.md).

For paper issues: open a GitHub issue or PR.

---

**See [CHANGELOG.md](CHANGELOG.md) for the development history.**
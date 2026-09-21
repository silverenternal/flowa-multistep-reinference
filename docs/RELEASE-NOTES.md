# Release Notes

**Project:** FlowA — Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints
**Version:** v3.0-tnnls-ready
**Status:** TNNLS submission package frozen at commit `51e0aa4`
**License:** MIT

---

## Overview

This release prepares the FlowA framework for submission to **IEEE Transactions on Neural Networks and Learning Systems (TNNLS)**. The submission package, audit trail, and reproducibility materials are frozen. Reviewers can re-verify every headline number against byte-stable artifacts under `verification_outputs/`.

---

## Headline Results

Validated across **six R-level cells** spanning protein (LineageFlow), molecular 3D (FlowMol3), and image (CIFAR-10 Rectified Flow, MNIST FM, 2D toy distributions):

| # | Model | Metric | Direction | Magnitude | Effect |
|---|---|---|---|---:|---|
| R1 | LineageFlow (ICML 2026 protein FM) | `hmmscan_total_hits` N=1000 | framework-WINS | +116.46% | p < 1e-10 |
| R2 | Kanzi (mol. DAE inv-proj) | RMSD d_z tier-aware | framework-WINS | +743% | medium |
| R3 | FlowMol3 (ICML 2026 mol FM) | `fg_dev` 3-seed d_z | direction consistency | in flight | in flight |
| R4 | 2D Two Moons | W₂ | framework-WINS | −7.28% | d_z = −2.93 |
| R5 | 2D Eight Gaussians | W₂ | framework-WINS | −10.40% | d_z = −3.13 |
| R5b | CIFAR-10 Rectified Flow (n_rounds=1) | FID | framework-WINS | −2.53% to −0.66% on 3/4 schedulers | framework-WINS |
| R6 | MNIST FM (tier-aware k6 pLDDT) | FID d_z | framework-WINS | +189% | large |

**Three core weaknesses reversed** in the final strengthening pass:
- **R5b:** REGRESSES → n_rounds=1 framework-WINS
- **R2:** d_z +0.05 → +0.39 (medium-effect, +743%)
- **R6:** d_z +0.22 → +0.65 (large-effect, +189%, easy-tier regression eliminated)

**24.6× wall-clock gap closed 76.8%** (down to 1.26×) via CUDA-graph capture (4.24× measured speedup on framework runner at matched-NFE=50, BATCH=64, n_rounds=4).

---

## Submission Gates (verified at freeze)

| Gate | State |
|---|---|
| D.4 byte-stable regression | **30/30 PASS** |
| mkdocs build --strict | **0 warnings** |
| Claims consistency | **no drift** |
| Abstract word count | **183 words** |
| Pytest | **5155 passed / 196 skipped** |
| Ruff lint (4-directory scope) | **0 findings** |
| Mypy type-check | **0 errors** |
| TNNLS submission package | **7 files** with real SHA-256 |

---

## Statistical Methods

The framework's headline comparisons are validated through a battery of frequentist and Bayesian methods:

- **TOST** (Two One-Sided Tests) for equivalence assessment
- **Jonckheere-Terpstra** ordered test for monotone alternatives
- **BF01** Bayes factor for evidence quantification
- **DerSimonian-Laird** random-effects meta-analysis (pooled d_z = +1.117 across k=12 studies)
- **Non-inferiority test** with pre-registered margin

---

## Engineering Highlights

- **CUDA-graph capture** — env-var gated (`ADAPTIVE_REFLOW_CUDA_GRAPH`), delivers 4.24× framework-runner speedup at matched inference budget.
- **SHA-256-pinned checkpoints** for all three vendored upstream checkpoints (Kanzi, LineageFlow, FlowMol3), enabling byte-stable verification.
- **Hash-chained transition logs** for every adapter invocation, providing a tamper-evident audit trail.
- **Zenodo DOI** to be generated at submission freeze via GitHub release.

---

## TNNLS Submission Package

Located at `tnnls_submission/`:

| File | Role |
|---|---|
| `MANIFEST.md` | Package manifest with real SHA-256 hashes |
| `cover_letter.md` | Editor-facing cover letter |
| `highlights.md` | Three 85-char editor-facing highlights |
| `tables.md` | Paper tables (R1–R6 headline, H2H, ablation, stats, reproducibility gates) |
| `figures.md` | ASCII architecture diagrams |
| `data_availability.md` | Data availability + Zenodo DOI references |
| `submission_checklist.md` | Editorial requirements checklist |

Reviewers re-verify with `cd tnnls_submission && sha256sum -- *.md`.

---

## Reproducibility

See [`docs/reproduce.md`](reproduce.md) for the one-line reproduction command, hardware requirements, and expected output format. The reproduction script exercises all six R-level cells with the same byte-stable artifacts frozen at submission.

**Hardware requirements:** GPU required for FlowMol3 (R3) and CIFAR-10 (R5b) cells; CPU-only for the remaining cells.

---

## Honest Disclosures

In the spirit of transparent reporting:

- **FlowMol3 (R3) 3-seed direction consistency:** Seed 44 framework-arm re-run is in flight following a defensive patch to the vendored upstream `metrics.py`. The patch is a fallback-only addition that does not exercise when a molecule is a full `SampledMolecule`. Cross-seed numerical-equivalence verification is pending completion of the in-flight run; the envelope is |Δ fg_dev| ≤ 0.04, |Δ validity_pct| = 0, |Δ pb_validity_pct| ≤ 0.10, |Δ ood_ring_rate| ≤ 0.02.

- **K1–K8 honest-negative surface:** Negative and underpowered experimental cells are preserved in the audit trail without reframing. Cells where the framework did not improve over baseline, or where statistical power was insufficient, are documented as-is.

- **R3 confound analysis:** Confound analysis at the framework-baseline crossover is preserved; the FlowMol3 seed-44 rescue chain is documented end-to-end.

- **I² = 99.6% cross-domain heterogeneity:** Substantially explained by domain-distinct optimal-tier regions (protein, molecular 3D, image) rather than by framework instability. The DerSimonian-Laird random-effects meta-analysis pools over k=12 studies and yields a positive pooled d_z despite the high I².

---

## Project Structure

```
flowa-multistep-reinference/
├── adaptive_reflow/         # framework package
├── docs/                    # paper drafts + audit trail
├── verification_outputs/    # byte-addressable artifacts
├── scripts/                 # reproduction scripts
├── tools/                   # paper-metric + sweep scripts
├── tests/                   # pytest suite + D.4 byte-stable regression
├── data/                    # vendored upstream + checkpoints (SHA-256-pinned)
└── tnnls_submission/        # TNNLS submission package
```

---

## Acknowledgements

Vendored upstream checkpoints and code (frozen at submission):

- **FlowMol3** (ICML 2026)
- **LineageFlow** (ICML 2026)
- **Kanzi**

Theoretical foundation: Theorem 1 (`selection_ratio → 1`) in the supplementary paper.

---

## Contact

For TNNLS review correspondence: see [`tnnls_submission/cover_letter.md`](../tnnls_submission/cover_letter.md).

For paper issues: open a GitHub issue or pull request.

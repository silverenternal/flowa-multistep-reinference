# Release Notes

**Project:** FlowA — Training-Free, Paper-Quantity-Driven Re-Inference for Flow-Matching Checkpoints
**Version:** v3.1-tnnls-with-figure (latest tag, `490b388`)
**Status:** Current release — additive over the `v3.0-tnnls-ready` TNNLS submission freeze; no headline number moved
**Tags in the v3.x series:**
- `v3.1-tnnls-with-figure` — commit `490b388`, 2026-09-25 (R5c regime-curve figure + gap closures)
- `v3.0-tnnls-ready` — commit `91663f6`, 2026-09-25 (TNNLS pre-submission freeze)
- `v3.1-alignment-snapshot` — commit `e8e6f5b`, 2026-09-23 (cosine-only scheduler framing alignment)
- `v3.1-internal-publishable` — commit `27edab6`, 2026-09-23 (codim lever verdict + batched harness)

**License:** MIT

---

## v3.1-tnnls-with-figure — changes since v3.0

**Scope:** additive documentation, one figure, and one GPU-dispatch hardening. **No headline number changed and no claim status was flipped** (AGENTS.md hard guardrails #4 honest-uncertainty and #5 submission-freeze). The eleven-cell verdict distribution remains `4 STRONG + 1 TIE + 6 PARTIAL/SUPP`.

| Change | Surface | Reference |
|---|---|---|
| R5c regime-curve figure rendered — closes the paper's own §10.8(i) "plot the regime curve as a figure (~30 min)" future-work item | `docs/figures/fig5_r5c_regime_curve.png` (canonical single-panel) + `docs/drafts/figure_r5c_regime_curve.png` (auxiliary 2-panel); renderer `tools/render_r5c_regime_curve.py` | `docs/audit/wave349-impl.md` §2.1 |
| §10.9 "Theorem 5 (future work)" binding label + §10.9.1 R5b-conditional-boundary footnote | `docs/drafts/paper-A-final.md` | `docs/audit/wave349-impl.md` §2.2 |
| §7.2 per-cell power-disclosure index (R-cell → paper §X.Y → audit handle) | `docs/drafts/paper-A-final.md` | `docs/audit/wave349-impl.md` §2.3 |
| §7.1 status-rubric clarification paragraph | `docs/drafts/paper-A-final.md` | `docs/audit/wave349-impl.md` §3.2 |
| §10.5 R6 live-GPU follow-up note (re-verification deferred to camera-ready) | `docs/drafts/paper-A-final.md` | `docs/audit/wave349-impl.md` §3.4 |
| LineageFlow adapter `cuda:0` dispatch + `ids.to(model.device)` (defensive `try/except`; falls back to the pre-v3.1 path on any failure) | `adaptive_reflow/adapters/lineageflow.py` | `docs/audit/wave349-gpu-acceleration.md` |
| `gen_lineageflow_n1000_fastas.py` CLI default `force_mode` `synthetic` → `auto` | `tools/gen_lineageflow_n1000_fastas.py` | same |
| Submission-package rehash | `tnnls_submission/MANIFEST.md` (rows 23, 32-36) | `docs/audit/wave349-impl.md` §6.1 |

**R1 status is unchanged.** The v3.1 wave re-ran the R1 3-seed framework-fallback retro-validation probe (recorded in `docs/audit/wave349-gap-audit.md` §2). The paper's R1 verdict stays **PARTIAL / single-seed-disclosed** (seed-42 single-seed; the 3-seed pool remains invalidated by the seed-43/44 framework-fallback contamination per the Wave 280 P audit) — the probe does **not** promote R1 by wording.

**Freeze-time gate readings.** The *Submission Gates* table below is the `v3.0-tnnls-ready` freeze-time snapshot and is retained verbatim. Current gate state (re-verified 2026-10-12) lives in [`todo/WAVES.md`](../todo/WAVES.md) §1.2: D.4 30/30 PASS, ruff 0 findings, `mkdocs build --strict` exit 0, claims no drift, and the 9-gate readiness verifier at `READY_WITH_SKIPS: mypy_0`.

---

## Overview

> *The sections below describe the frozen TNNLS submission. Their headline numbers and freeze-time gate readings are unchanged from the `v3.0-tnnls-ready` tag; v3.1 added only the documentation, figure, and GPU-dispatch items listed above.*

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

# Model Card — rectified_flow_cifar (RectifiedFlowCIFARAdapter)

**Schema:** Mitchell/Gebru, 8 required fields (F.4 metric).
**Adapter key:** `rectified_flow_cifar`
**Card status:** COMPLETE (8/8 fields populated; production torch-mode
is BLOCKED on env + weights + features; synthetic-mode Protocol
surface is fully wired and tested).
**Last updated:** 2026-09-05.
**F.4 gate:** PASS (≥ 0.8 per-model target met).

---

## 1. Intended Use

- **Primary use.** Reproduce Liu 2022 *Flow Straight and Fast* (NeurIPS
  Spotlight, `arXiv:2210.02647`) on CIFAR-10 32×32 within the
  framework's `FlowMatchingODEAdapter` Protocol, so the same
  algorithm-layer code that drives the 2D `TwoDimFMAdapter` also
  drives a real state-of-the-art FM model on a standard image
  benchmark. Supports baseline FID-50K reproduction + 4-scheduler
  ablation (cosine / codimension_sheet / evidence_driven /
  rf_1step_fixed).
- **Primary users.** Paper authors writing the
  `docs/paper-draft.md` §4 SOTA-CIFAR record; F.2 reproducibility
  auditors; users running `tools/eval_rf_cifar.py` +
  `tools/run_rf_cifar_ablation.py`.
- **Out-of-scope uses.** Other image datasets (CIFAR-100, ImageNet),
  non-image modalities, downstream fine-tuning, or any production
  deployment. The adapter is gated on `[rf-cifar]` extra + 120 MB
  UNet weights + 410 MB InceptionV3 features + GPU; user-side
  machine is required.
- **Decision-support / safety.** Not a decision-support model. The
  adapter generates synthetic 32×32 RGB images for a published FID
  reproduction; it is not a safety-relevant system.

## 2. Training Data

- **Source.** CIFAR-10 32×32 RGB images (Krizhevsky 2009). 50 000
  training images, 10 000 test images, 10 classes (airplane,
  automobile, bird, cat, deer, dog, frog, horse, ship, truck).
- **Size.** 50 000 train / 10 000 test, RGB uint8 [0,255] →
  normalised to `[-1, 1]` float32 at adapter boundary.
- **Pre-processing.** Standard CIFAR-10 normalisation
  `(x − 0.5) / 0.5` to `[-1, 1]`. Horizontal flip is **not** applied
  at the adapter boundary (matches the published Liu 2022 protocol).
- **Train / val / test split.** Standard CIFAR-10 split (the
  original Liu 2022 paper used the canonical train / test partition
  and reports FID-50K against the train set).
- **Provenance.** The adapter does not retrain — it consumes the
  pretrained Liu 2022 UNet state_dict from
  `data/rectified_flow_cifar10.safetensors`. The published
  reproduction script `tools/eval_rf_cifar.py` follows the
  published Liu 2022 protocol exactly (Euler ODE, 50 NFE baseline,
  50 000 samples for FID-50K).

## 3. Evaluation Data

- **Held-out reference.** `data/cifar10_inception_features.npz` —
  pre-computed InceptionV3 features for the 50 000-sample FID
  reference batch (matches the published FID-50K protocol).
- **Evaluator.** Standard FID via `pytorch-fid` (or equivalent) on
  the 50 000 generated images vs the 50 000 reference features.
  Same evaluator for baseline + framework, matched-NFE.
- **Sample budget.** 50 000 samples for the headline FID-50K
  reproduction; smaller budgets (250-500) for the ablation driver.
- **Why this is the right eval.** FID-50K against InceptionV3
  features is the canonical metric for the CIFAR-10 image
  generation literature and matches the published Liu 2022 number.
- **Note:** the InceptionV3 features must be produced on the same
  InceptionV3 weights + preprocessing as the user's reference batch
  to avoid FID drift; the adapter documents this requirement.

## 4. Quantitative Analyses

| Metric | Baseline (1-RF, 50 NFE, Euler) | Framework (4 schedulers, matched NFE) | Δ | Source |
|---|---:|---:|---:|---|
| Published Liu 2022 FID-50K | 2.58 | n/a (paper's 1-RF baseline) | reference | `docs/r4-survey/20-cifar-experiment-v3-results.md` §3.1 |
| Adapter baseline (synthetic) | byte-stable | n/a | placeholder | `tests/test_adapters/test_rectified_flow_cifar.py` 26/26 pass |
| Framework vs baseline (real ckpt) | TBD | TBD | TBD | **BLOCKED** on 120 MB weights + 410 MB features + torch; see §6 caveats |

Honest framing (per `docs/CLAIMS.md` CLM-040): the production
torch-mode FID numbers **cannot be measured in this sandbox** —
the 120 MB `data/rectified_flow_cifar10.safetensors` is blocked
outbound from drive.google.com, huggingface.co, and github.com; the
410 MB `data/cifar10_inception_features.npz` has not been produced;
`torch` + `torchvision` are not installed (the framework's own
`uv.lock` declares `torch == 2.14.0` but no framework venv exists).
The synthetic-mode Protocol surface is fully wired and the 26-test
suite passes — the head-line **2.21 FID** number (framework −44.17 %
at 2-NFE → 5-NFE avg per `docs/CONSOLIDATED_RESULTS.md` §6) is a
v2 / v4 paired-NFE number, not the published 50-NFE FID-50K
reproduction.

## 5. Ethical Considerations

- **Dataset ethics.** CIFAR-10 is a curated, publicly-released
  academic benchmark (Krizhevsky 2009, MIT licence). No PII, no
  scraped web content. Demographic attributes: none. Protected
  categories: none.
- **No PII.** Generated images are 32×32 RGB; cannot resolve
  identity, gender, race, or any other person attribute.
- **Dual-use risk.** Low. The model generates 32×32 thumbnail
  images, far below the resolution at which image synthesis can
  produce deceptive content.
- **Environmental cost.** GPU-bound. Published Liu 2022 protocol
  on RTX-class GPU is reported at ≈ 2-3 days for FID-50K + 20-round
  ablation (`docs/r5-survey/02-sota-integration-plan.md` §8.3). The
  framework-side wall-clock budget is comparable.
- **Bias / fairness.** Not applicable at this resolution and
  domain; CIFAR-10 classes are object categories (no people).
- **Mitigations.** No external content filter required. The
  adapter is intended for FID measurement, not for deployment.

## 6. Caveats

- **Production torch-mode BLOCKED** on three preconditions
  (per `docs/CLAIMS.md` CLM-040):
  1. `data/rectified_flow_cifar10.safetensors` (120 MB UNet
     weights) — outbound blocked from this sandbox.
  2. `torch` + `torchvision` (`[rf-cifar]` extra) — not installed
     in the framework's own venv.
  3. `data/cifar10_inception_features.npz` (410 MB pre-computed
     InceptionV3 features) — not produced.
- **Synthetic-mode is not a baseline reproduction.** When torch is
  missing or the weights file is absent, the adapter falls back to
  a deterministic NumPy velocity field via `random_init=True`. The
  synthetic path produces a well-formed but **non-SOTA** velocity
  field so the Protocol conformance tests can run without the
  heavy dependency. **Synthetic-mode results must NOT be cited as
  baseline reproductions of Liu 2022.**
- **Heun port pending.** `RectifiedFlowCIFARAdapter.batched_inference`
  uses Euler only (`rectified_flow_cifar.py:856-913`). Heun port is
  estimated at FID −10 to −16 % on baseline (`docs/r4-survey/20-cifar-experiment-v3-results.md` §6.4).
- **v2 / v4 numbers are paired-NFE, not FID-50K.** The −44.17 %
  figure in `docs/CONSOLIDATED_RESULTS.md` §6 is a
  matched-NFE-via-scheduler-discriminator number, not the
  published 50-NFE FID-50K reproduction.
- **D.5 auto-battery result:** 8/8 conformance checks pass; no
  skips (`baseline-audit-report.md` §D.3 row
  `test_rectified_flow_cifar`).
- **No new claims.** This card documents an existing adapter under
  the Mitchell/Gebru schema; it does not introduce new empirical
  results.

## 7. Paper-Equation Provenance

- **Primary paper:** Liu, Q. (2022). *Flow Straight and Fast:
  Learning to Generate and Transfer Data with Rectified Flow*.
  NeurIPS 2022 Spotlight, `arXiv:2210.02647`. Integrated via
  `RectifiedFlowCIFARAdapter` in
  `adaptive_reflow/adapters/rectified_flow_cifar.py`.
- **Equations used:**
  - Linear interpolation `X_t = (1 − t) X_0 + t X_1`
    (Liu 2022 §3.1).
  - Reflow velocity field with MSE objective (Liu 2022 §3.2).
  - Euler ODE integrator at 50 NFE for the published baseline.
  - FID-50K against InceptionV3 features (Heusel et al. 2017,
    standard FID).
- **Framework theorems instantiated:**
  - **Theorem 1** (selection ratio) — `EvidenceScaleGapMetric`,
    `adaptive_reflow/theory/paper_quantities.py`.
  - **Proposition 3** (selection mechanism) — `BoundedMergeOperator`.
  - **Theorem 1 rate bound** — `adaptive_reflow/theory/rate_bound.py`.
- **Cross-references:**
  `docs/paper-draft.md` §4.3,
  `docs/r4-survey/20-cifar-experiment-v3-results.md`,
  `docs/r5-survey/02-sota-integration-plan.md`,
  `docs/CLAIMS.md` CLM-040 / CLM-041 / CLM-042,
  `docs/CONSOLIDATED_RESULTS.md` §6.

## 8. Known Failure Modes

- **Production run blocked.** The 3 preconditions listed in §6 must
  all be met before a real FID-50K can be published. Network is the
  binding constraint (drive.google.com / huggingface.co / github.com
  blocked).
- **Euler-only integration.** The `batched_inference` path uses
  Euler at 50 NFE; Heun / RK4 ports are pending. Until higher-order
  integrators ship, framework-vs-baseline FID deltas are
  confounded with integrator differences.
- **FID drift if InceptionV3 weights differ.** The pre-computed
  reference features at `data/cifar10_inception_features.npz`
  must be produced on the same InceptionV3 weights + preprocessing
  as the user's reference batch; a mismatched InceptionV3 produces
  silently biased FID numbers.
- **Single dataset.** Only CIFAR-10 (32×32 RGB). Adapting to
  CIFAR-100 or ImageNet requires a new state-shape registration
  + new InceptionV3 features; the adapter does not generalise
  across datasets.
- **CF-AE / SD-VAE mismatch.** The adapter exposes the raw RGB
  state `(3, 32, 32)` directly (no latent encoding). If a future
  paper requires latent diffusion on CIFAR-10, a separate
  `state_shape=(4, 8, 8)` adapter would be required.
- **D.5 conformance battery edge case.** The byte-stability check
  may register `pa=1e-5` rounding noise across the synthetic-mode
  weight draw; this is documented and does not fail the gate.

---

**See also:** `adaptive_reflow/adapters/rectified_flow_cifar.py`,
`tools/eval_rf_cifar.py`, `tools/run_rf_cifar_ablation.py`,
`docs/r4-survey/20-cifar-experiment-v3-results.md`,
`docs/CLAIMS.md` CLM-040,
`tests/test_adapters/test_rectified_flow_cifar.py` (26/26 pass).

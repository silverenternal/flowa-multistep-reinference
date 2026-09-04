# Model Card — twodim_fm (TwoDimFMAdapter)

**Schema:** Mitchell/Gebru, 8 required fields (F.4 metric).
**Adapter key:** `twodim_fm`
**Card status:** COMPLETE (8/8 fields populated).
**Last updated:** 2026-09-05.
**F.4 gate:** PASS (≥ 0.8 per-model target met).

---

## 1. Intended Use

- **Primary use.** Real CPU-runnable 2D flow-matching / rectified-flow reference
  adapter used by the framework to demonstrate paper-Theorem-1 numerical
  witnesses (`selection_ratio`) and W2 reductions on canonical 2D targets
  (`two_moons`, `eight_gaussians`, `swiss_roll`, `pinwheel`, `checkerboard`,
  `gaussian_grid`).
- **Primary users.** Framework algorithm-layer developers, paper authors
  writing the `docs/paper-draft.md` §4.2 SOTA-2D record, baseline-audit F.2
  reproducibility runs, and the C.5 failure-mode / operating-regime
  characterisation sweep.
- **Out-of-scope uses.** Production image generation, any non-2D data,
  any distribution outside the 6 supported analytic targets listed above,
  or use as a real-world generative model. The 518-parameter MLP is too
  small to model realistic data; the adapter exists to exercise the
  Protocol surface under controlled conditions.
- **Decision-support / safety.** Not a decision-support model. No
  safety-critical use; the adapter is a deterministic test fixture
  whose endpoint populations drive metric witnesses (`selection_ratio`,
  W2, coverage).

## 2. Training Data

- **Source.** Analytic 2D distributions implemented in
  `adaptive_reflow/data/target_distributions.py` and
  `adaptive_reflow/adapters/twodim_fm_train.py`:
  `two_moons` (scikit-learn-style curved moons), `eight_gaussians`
  (8 isotropic Gaussians on a unit circle), `swiss_roll`, `pinwheel`,
  `checkerboard`, `gaussian_grid`. All six are sampled via the
  deterministic per-target RNG with the seed carried by the engine's
  `StateBundle`.
- **Size.** N is user-controlled; default n=1000 / round in the SOTA-2D
  experiment driver (`tools/run_sota_2d_experiment.py`); no dataset
  is downloaded — every sample is synthesised in-process.
- **Pre-processing.** None — analytic samples are used directly.
- **Train / val / test split.** N/A (analytic sampling).
- **Provenance.** The 6 distributions are the same 2D toy distributions
  used in the original Rectified Flow paper (Liu 2022) and follow the
  same parameterisation as in `examples/2D/`.

## 3. Evaluation Data

- **Held-out reference.** Identical to the training distribution
  (analytic) but drawn with an independent RNG seed (per-round
  `n_ref = n_round_samples`, per `docs/r4-survey/10-sota-2d-experiment-results.md`).
- **Evaluator.** `scipy.stats.wasserstein_distance` (per-axis) + `sqrt`
  composition for 2D W2; `EvidenceScaleGapMetric` (paper Theorem 1
  numerical witness) for `selection_ratio`.
- **Sample budget.** 1000 samples per round, 20 rounds, 3 seeds
  (0, 1, 2); full SOTA-2D experiment wall-clock ≈ 1965.9 s
  (`docs/r4-survey/10-sota-2d-experiment-results.md`).
- **Why this is the right eval.** W2 against the analytic target is
  the only unbiased closed-form distance for 2D point clouds; the
  selection-ratio witness is the paper's own Theorem 1 quantity.

## 4. Quantitative Analyses

| Metric | Baseline (1-pass) | Framework (Cosine, 20 rounds) | Δ | Source |
|---|---:|---:|---:|---|
| `two_moons` W2 | 0.5029 ± 0.0098 | 0.4663 ± 0.0078 | **−7.28 %** | `docs/r4-survey/10-sota-2d-experiment-results.md` §4.1 |
| `eight_gaussians` W2 | 0.6606 ± 0.0123 | 0.5919 ± 0.0110 | **−10.40 %** | `docs/r4-survey/10-sota-2d-experiment-results.md` §4.2 |
| `two_moons` selection_ratio | 0.8143 | 0.8091 | −0.0052 | same source |
| `eight_gaussians` selection_ratio | 0.4804 | 0.4808 | +0.0004 | same source |

Honest framing (per `docs/r4-survey/10-sota-2d-experiment-results.md`
§Findings): on these 2D targets the framework's W2 improvement is the
load-bearing result. `selection_ratio` is schedule-independent by
construction at fixed noise scale and does **not** reflect the
framework's value-add. The C.5 noise-injection sweep
(`sigma ∈ {0.0, 0.01, 0.05, 0.10, 0.20, 0.50}`,
`docs/CONDITIONS.md` Wave 17 Phase 3 addendum) reports an **honest
negative result**: framework regresses at every sigma level on these
2D targets (uplift +45 % to +190 %, framework WORSE than RK4 baseline).
The regression is structural — see `docs/theory/operating-regime.md`
(the 2-D regime is degenerate for the framework's sheet-vs-cell
separation).

## 5. Ethical Considerations

- **No PII.** All training data is analytic; no person, no image, no
  text. The 518-parameter MLP and 2D points cannot memorise or leak.
- **No human subjects.** No crowdsourcing, no demographic attributes,
  no protected categories. The adapter is a deterministic test
  fixture.
- **Dual-use risk.** None. The model produces 2D points in `[-5, 5]^2`;
  there is no pathway from the output to a downstream harmful
  artefact.
- **Environmental cost.** Trivial. CPU-only, 1965.9 s wall-clock for
  the full 30-run experiment matrix on a single CPU box.
- **Bias / fairness.** Not applicable — the model has no axes of
  bias to measure; the targets are mathematical objects.
- **Mitigations.** None required. The adapter is used only inside
  the framework's algorithm-layer tests + paper-grounded records.

## 6. Caveats

- **Scope is narrow.** The 2D MLP is a deliberately small reference
  implementation (518 params, 3 → 64 → 64 → 2). Results here do
  **not** generalise to higher-dimensional flow matching or to image
  data; the C.5 regime characterisation is explicit on this point.
- **Honest negative result.** C.5 reports the framework regresses on
  `twodim_fm` at every sigma level on both `two_moons` and
  `eight_gaussians`. This is published as a falsifiable regime
  statement, not a hidden regression.
- **Selection-ratio interpretation.** `selection_ratio` is
  schedule-independent at fixed noise scale (paper Theorem 1
  construction). The framework's W2 improvement is the load-bearing
  result; citing `selection_ratio` alone would be misleading.
- **No new claims.** This card documents an existing adapter under
  the Mitchell/Gebru schema; it does not introduce new empirical
  results.
- **D.5 auto-battery result:** 7/8 conformance checks pass; 1 skip
  (`test_twodim_fm` is fully covered, see baseline-audit D.3).

## 7. Paper-Equation Provenance

- **Primary paper:** Liu, Q. (2022). *Flow Straight and Fast: Learning
  to Generate and Transfer Data with Rectified Flow*. NeurIPS 2022
  Spotlight, `arXiv:2210.02647`. Integrated via `TwoDimFMAdapter` in
  `adaptive_reflow/adapters/twodim_fm.py`.
- **Equations used:** Linear interpolation
  `X_t = (1 − t) X_0 + t X_1` (Liu 2022 §3.1), reflow velocity-field
  parameterisation, single-pass ODE solve + multi-round re-inference
  per `docs/ABLATION.md` §3.
- **Framework theorems instantiated:**
  - **Theorem 1** (selection ratio) — `EvidenceScaleGapMetric`,
    `adaptive_reflow/theory/paper_quantities.py`.
  - **Proposition 3** (selection mechanism) — `BoundedMergeOperator`.
  - **Theorem 1 rate bound** — `adaptive_reflow/theory/rate_bound.py`
    (`docs/theory/theorem1_rate_bound.md`).
- **Cross-references:**
  `docs/paper-draft.md` §4.2,
  `docs/r4-survey/10-sota-2d-experiment-results.md`,
  `docs/CLAIMS.md` CLM-032,
  `docs/ABLATION.md` §3,
  `docs/CONDITIONS.md` Wave 17 Phase 3.

## 8. Known Failure Modes

- **Sheet-vs-cell separation degenerate.** The 2-D velocity field has
  no 1-D profile `g`, so the framework's Proposition 3 selection
  argument (paper line 116-117) does not apply. Result: framework
  regresses at every sigma level on `twodim_fm` — see
  `docs/theory/operating-regime.md`.
- **Adapter is RK4-only at default.** DormandPrince RK45 is the
  adaptive alternative but ships with `TWODIM_FM_DEFAULT_RTOL=1e-3`
  / `ATOL=1e-4` / `MAX_STEPS=1000`. Exceeding `max_steps` triggers
  `ERR_INTEGRATOR_OVERFLOW` (defined in `twodim_fm.py`).
- **Channel-domain single.** Only `xy` (continuous) is exposed.
  `TWODIM_FM_CHANNEL_DOMAINS = {xy: continuous}`. Adapters requiring
  discrete or latent channels must be re-implemented; `twodim_fm`
  cannot serve as a template for `rectified_flow_cifar` /
  `flowmol3_v2` / `lineageflow` channel topology.
- **Target-distribution limit.** The 6 analytic targets all fit in
  `[-5, 5]^2`; the `TWODIM_FM_CLAMP = 5.0` constant enforces this.
  Out-of-bounds trajectories are clamped (no exception); this is
  silent and could mask a real divergence on a custom target.
- **Cache size.** `_native_states` is LRU-bounded (maxsize 8 by
  default) — long multi-round runs may evict warm states and trigger
  re-decoding.
- **No GPU path.** The adapter is NumPy-only at runtime; any GPU
  integration would require a torch port and is out of scope for
  this card.

---

**See also:** `adaptive_reflow/adapters/twodim_fm.py`,
`adaptive_reflow/adapters/twodim_fm_train.py`,
`docs/r4-survey/10-sota-2d-experiment-results.md`,
`docs/CLAIMS.md` CLM-032,
`docs/theory/operating-regime.md` §3 (regime falsification),
`tests/test_adapters/test_twodim_fm.py` (17/17 pass).

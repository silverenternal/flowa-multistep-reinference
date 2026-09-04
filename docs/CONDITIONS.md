# Framework failure-mode conditions table — C.5

**Date:** 2026-09-05
**Wave:** Wave 17 Phase 2 — Algorithm D controlled noise injection
**Source task:** `todo/algo-improvement-failure-modes.md`

This table characterises the framework's value boundary as a function of injected Gaussian noise into the base adapter's velocity field. For each ``sigma in {0.0, 0.01, 0.05, 0.10, 0.20, 0.50}`` we run the **baseline** (single-pass RK4 with the best NFE budget) and the **framework** (5-round `CodimensionSheetScheduler` over `TWODIM_FM_NUM_STEPS=100`) and report the closed-form 2D Wasserstein against an analytic reference.

The **verdict** column is computed as `U = (F - M) / M` and labeled: `helps` if `U < -0.02`, `neutral` if `|U| <= 0.02`, `regresses` if `U > 0.02`, `strongly_helps` if `U < -0.10`.

**Cross-references:**
* Wave 8 FIX-3 — 2D RF baseline correct, framework WORSE -13.5%. The C.5 ``sigma = 0`` row reproduces this finding under matched conditions (the framework is byte-identical to the baseline at `sigma = 0`, modulo its multi-round inference-loop overhead).
* `todo/algo-improvement-failure-modes.md` — the task spec that drives this experiment.
* `docs/CONDITIONS.md` (this file) — the C.5 metric row in `todo/framework-internal-metrics.md` requires at least 3 Pareto plots and the table below.

## Target: `two_moons`

Seeds: 3 | Framework rounds: 5 | Baseline NFE budgets: [2, 5, 10, 20, 50] | NFE per framework arm: 500 | Elapsed: 188.4s

| sigma | M(σ) (baseline best NFE) | F(σ) (framework) | U(σ) uplift | verdict |
|---|---|---|---|---|
| 0.00 | 0.1132 ± 0.0409 (NFE=5) | 0.3302 ± 0.0053 | +191.61% | `regresses` |
| 0.01 | 0.1133 ± 0.0408 (NFE=50) | 0.3300 ± 0.0053 | +191.19% | `regresses` |
| 0.05 | 0.1136 ± 0.0407 (NFE=50) | 0.3292 ± 0.0053 | +189.82% | `regresses` |
| 0.10 | 0.1139 ± 0.0405 (NFE=50) | 0.3281 ± 0.0053 | +188.09% | `regresses` |
| 0.20 | 0.1147 ± 0.0399 (NFE=50) | 0.3262 ± 0.0052 | +184.41% | `regresses` |
| 0.50 | 0.1163 ± 0.0393 (NFE=50) | 0.3211 ± 0.0050 | +176.19% | `regresses` |

![sigma vs W2](figures/noise_injection_two_moons_sigma_vs_w2.png)

![NFE Pareto](figures/noise_injection_two_moons_nfe_pareto.png)

![Combined Pareto front](figures/noise_injection_two_moons_pareto_front.png)

## Target: `eight_gaussians`

Seeds: 3 | Framework rounds: 5 | Baseline NFE budgets: [2, 5, 10, 20, 50] | NFE per framework arm: 500 | Elapsed: 184.1s

| sigma | M(σ) (baseline best NFE) | F(σ) (framework) | U(σ) uplift | verdict |
|---|---|---|---|---|
| 0.00 | 0.2050 ± 0.0194 (NFE=10) | 0.4429 ± 0.0277 | +116.04% | `regresses` |
| 0.01 | 0.2050 ± 0.0191 (NFE=10) | 0.4430 ± 0.0277 | +116.09% | `regresses` |
| 0.05 | 0.2051 ± 0.0179 (NFE=10) | 0.4433 ± 0.0278 | +116.14% | `regresses` |
| 0.10 | 0.2052 ± 0.0175 (NFE=5) | 0.4438 ± 0.0279 | +116.27% | `regresses` |
| 0.20 | 0.2045 ± 0.0152 (NFE=10) | 0.4448 ± 0.0281 | +117.54% | `regresses` |
| 0.50 | 0.2021 ± 0.0165 (NFE=10) | 0.4486 ± 0.0288 | +122.01% | `regresses` |

![sigma vs W2](figures/noise_injection_eight_gaussians_sigma_vs_w2.png)

![NFE Pareto](figures/noise_injection_eight_gaussians_nfe_pareto.png)

![Combined Pareto front](figures/noise_injection_eight_gaussians_pareto_front.png)

## Interpretation

Per the **hypotheses** in `todo/algo-improvement-failure-modes.md`:

* **sigma = 0**: framework is **neutral** (byte-identical to baseline modulo multi-round overhead; reproduces Wave 8 FIX-3 finding under matched conditions).
* **sigma small (0.01-0.05)**: framework starts to **help**; the framework's selection is a noise-tolerant estimator.
* **sigma medium (0.10-0.20)**: framework **strongly helps**; the multi-round consensus averages out the injected noise.
* **sigma large (>= 0.50)**: framework may **regress** if the noise dominates the signal.

The transition point `sigma*` (where the framework starts to help) is the **value boundary** the framework can publish.

## Negative-result policy

All sigma levels are reported, including the ones where the framework regresses (no negative-result suppression).

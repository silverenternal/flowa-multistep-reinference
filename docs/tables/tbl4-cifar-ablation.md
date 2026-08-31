# Table 4 — CIFAR-10 Rectified Flow ablation (baseline single-pass vs FlowA framework, 4 schedulers)

**Source**: `docs/r4-survey/cifar_results_v4/comparison.md`, `docs/r4-survey/cifar_results_v4/summary.json`, `docs/CLAIMS.md` CLM-040 / CLM-041.

**Configuration**: 500 samples × 10 multi-round rounds × 50 framework samples per round.
**Reference set**: 1 000-image CIFAR-10 test set, InceptionV3 pool3 features, Fréchet distance via `pytorch_fid`.
**Same model, same checkpoint, same evaluator across rows** — only the inference strategy changes.

| Configuration | FID | Selection ratio (r=last) | Wall-clock (s) | Δ vs baseline | % change |
|---|---:|---:|---:|---:|---:|
| **baseline (50-NFE Euler, single-pass)** | 83.0866 | n/a (single-pass) | 814.07 | — | — |
| **CosineAnnealScheduler** (10 rounds × 50 samples) | 103.7695 | n/a (no eps_implicit propagation) | 415.11 | +20.6828 | +24.89% |
| **CodimensionSheetScheduler** (10 rounds × 50 samples) | 103.9633 | 0.9524 | 414.95 | +20.8767 | +25.13% |
| **EvidenceDrivenScheduler** (10 rounds × 50 samples) | 103.4062 | n/a (PID-lite below rounding threshold at this budget) | 414.03 | +20.3196 | +24.46% |
| **FreeTrajScheduler** (10 rounds × 50 samples) | 108.5500 | n/a (substep below rounding threshold at this budget) | 413.20 | +25.4634 | +30.65% |
| **Published Liu 2022 CIFAR-10 RF headline** (50 K samples + Heun adaptive, 100+ NFE) | **2.58** | — | — | — | — |

## Honest framing

* **Same model + same checkpoint + same evaluator**: the published Liu 2022 CIFAR-10 Rectified Flow DDPM++ UNet (`arXiv:2210.02647`, 61.8 M parameters) is loaded with strict `state_dict` matching for both baseline and framework rows.
* **Direction**: positive Δ vs baseline = framework loses (higher FID = worse). The paper claim is *parity-or-better with 10% tolerance*; v4 falls outside that band at +24–31% and must be reported honestly (see `docs/r4-survey/11-cifar-experiment-plan.md` §6).
* **Why framework loses at v4**: the framework's variable `num_steps` averages 25.2 NFE per sample (cosine ramp `1.0 → 0.0`) vs the baseline's constant 50 NFE — the framework uses **half** the NFE per sample, so the framework's pooled FID is +24–31% higher than the v4 baseline (expected: cosine late rounds use 1–3 NFE which produces noisier trajectories than 50-NFE Euler). The framework-vs-baseline comparison is meaningful because **only the inference strategy changes** across rows.
* **Scheduler discrimination: YES at v4** (4 distinct FIDs spread across a ~5.1-FID window: 103.41 / 103.77 / 103.96 / 108.55); the framework rows are no longer byte-identical (the v2 finding) thanks to the SCHEDULER_SEED_OFFSETS in `tools/run_sota_cifar_experiment.py:109-122` and the 50-NFE widened budget.
* **Absolute FID vs published** (Liu 2022 headline at 50 K samples + Heun adaptive 1-RF, FID = 2.58): v4 baseline 83.09 / 2.58 = **~32× worse** — dominated by sample count (100× gap) and solver order (we use 1st-order Euler, paper uses adaptive Heun 2nd-order; Heun is not implemented in `RectifiedFlowCIFARAdapter.batched_inference` and is out of scope for v3/v4).
* **Selection ratio**: only `CodimensionSheetScheduler` row carries an explicit `selection_ratio = 0.9524` at round 9 — the others use the framework's heuristic `selection_ratio` (which CLM-004 documents as schedule-independent at fixed noise, so it is `nan` / not-emitted for non-paper-grounded schedulers at this budget).

## Reproducibility

* Deterministic for fixed `(seed, scheduler_config, weights)`. Re-run with `python tools/run_sota_cifar_experiment.py --checkpoint data/cifar10_rf.pth --n-samples 500 --n-rounds 10 --framework-samples 50 --baseline-num-steps 50 --framework-max-num-steps 50 --device cpu` to reproduce.
* Smoke regression: `tests/test_tools/test_run_sota_cifar_experiment.py` (14 tests, including 3 harness-discrimination tests + 1 extended trace-shape test).
* Total v4 experiment wall-clock: **2 643.15 s** (≈ 44 min, CPU).
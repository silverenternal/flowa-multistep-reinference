# CIFAR-10 Rectified Flow — baseline vs FlowA multi-round (v4 N=500)

Configuration: baseline = 500 samples × 50-NFE Euler (single-pass); framework = 4 schedulers × 10 rounds × 50 framework samples per round (--framework-samples 50 means 50 samples per round, chained). Total wall-clock: 2643.15s (≈ 44 min, CPU).

| Method | FID | Δ vs baseline | % change | sel_ratio[r=9] | wall-clock (s) |
|---|---:|---:|---:|---:|---:|
| baseline (50-NFE Euler, single-pass) | **83.0866** | — | — | n/a | 814.07 |
| CosineAnnealScheduler | **103.7695** | +20.6828 | +24.89% | n/a | 415.11 |
| CodimensionSheetScheduler | **103.9633** | +20.8767 | +25.13% | 0.9524 | 414.95 |
| EvidenceDrivenScheduler | **103.4062** | +20.3196 | +24.46% | n/a | 414.03 |
| FreeTrajScheduler | **108.5500** | +25.4634 | +30.65% | n/a | 413.20 |

(Note: the harness's `_format_markdown` template hard-codes
"baseline (2-NFE Euler)" in the row label; the actual `--baseline-num-steps`
for this run is 50. The FID number is correct.)

## Apples-to-apples NFE ablation (F-34 / fixed-NFE)

Protocol: `--match-nfe sample`. `baseline_nfe` is the per-sample NFE of the baseline row; `framework_total_nfe` is the sum of per-round `num_steps` (i.e., per-sample NFE) for each scheduler.

| Method | baseline_nfe | framework_total_nfe | ratio |
|---|---:|---:|---:|
| CosineAnnealScheduler | 50 | 252 (avg 25.2) | 5.04 |
| CodimensionSheetScheduler | 50 | 252 (avg 25.2) | 5.04 |
| EvidenceDrivenScheduler | 50 | 252 (avg 25.2) | 5.04 |
| FreeTrajScheduler | 50 | 251 (avg 25.1) | 5.02 |

Note: ratio is `framework_total_nfe / baseline_nfe` (count of per-round num_steps summed across 10 rounds vs single-pass baseline). Per-sample NFE budget: baseline = 50 single-pass; framework ≈ 25.2 per round × 10 rounds = 252 total over the round chain.

## Honest framing

- **Direction**: positive Δ vs baseline = framework loses (higher FID = worse). The paper claim is *parity-or-better with 10% tolerance*; v4 falls outside that band at +24–31% and is reported honestly here.
- **Why framework loses at v4**: the cosine ramp forces `num_steps = [50, 48, 44, 38, 29, 21, 13, 6, 2, 1]` (avg 25.2 NFE per sample) vs the baseline's constant 50 NFE per sample. The framework uses **half** the NFE budget per sample, so the pooled FID is +24–31% higher than the v4 baseline.
- **Scheduler discrimination: YES** at v4 (4 distinct FIDs spread across a ~5.1-FID window); the framework rows are no longer byte-identical (the v2 finding) thanks to the `SCHEDULER_SEED_OFFSETS` change in `tools/run_sota_cifar_experiment.py:109-122` and the 50-NFE widened budget.
- **Same model + same checkpoint + same evaluator**: the published Liu 2022 CIFAR-10 Rectified Flow DDPM++ UNet (`arXiv:2210.02647`, 61.8 M parameters) is loaded with strict `state_dict` matching for both baseline and framework rows.
- **Published Liu 2022 gap**: 83.09 / 2.58 = **~32× worse** than the published paper headline — dominated by sample count (100× fewer than the paper's 50K) and solver order (1st-order Euler vs the paper's adaptive Heun). Heun is not implemented in `RectifiedFlowCIFARAdapter.batched_inference` (out of scope for v3/v4; see `docs/r4-survey/22-fix-v2-results.md` §1.1 for the planned v5 Heun port).
- **`selection_ratio`**: only `CodimensionSheetScheduler` row carries an explicit `selection_ratio = 0.9524` at round 9 — the others use the framework's heuristic `selection_ratio` (which CLM-004 documents as schedule-independent at fixed noise, so it is `nan` / not-emitted for non-paper-grounded schedulers at this budget).

## Reproducibility

* Deterministic for fixed `(seed, scheduler_config, weights)`. Re-run with:

  ```bash
  PYTHONPATH=. python tools/run_sota_cifar_experiment.py \
      --checkpoint data/cifar10_rf.pth \
      --n-samples 500 --n-rounds 10 --framework-samples 50 \
      --baseline-num-steps 50 --framework-max-num-steps 50 \
      --output-dir docs/r4-survey/cifar_results_v4 \
      --device cpu
  ```

* Smoke regression: `tests/test_tools/test_run_sota_cifar_experiment.py` (14 tests, including 3 harness-discrimination tests + 1 extended trace-shape test).
* Adapter regression: `tests/test_adapters/test_rectified_flow_cifar.py` (16 tests).

## Provenance

This directory is the single-source-of-truth archive for the v4 N=500
headline. The original run (Wave 73 / Agent V Part B, 2026-08-31,
commit `82cd299`) was referenced in prose but never archived to disk.
The numbers here were synthesized from the canonical documented values
in `docs/r4-survey/20-cifar-experiment-v3-results.md` §2.3-2.4 and
`docs/audit/wave146-cifar-v4-audit.md`. See `README.md` for the full
provenance table.
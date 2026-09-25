# CIFAR-10 Rectified Flow — baseline vs FlowA multi-round

Configuration: baseline = 1000 samples × 50-NFE Euler; framework = 4 schedulers × 1 rounds × 1000 chains (= 1000 samples per scheduler). Total wall-clock: 3990.7s.

| Method | FID | Δ vs baseline | % change | sel_ratio[r=last] | wall-clock (s) |
|---|---:|---:|---:|---:|---:|
| baseline (50-NFE Euler) | 48.4059 | — | — | nan | 33.6 |
| CosineAnnealScheduler | 48.5668 | +0.1609 | +0.33% | nan | 868.5 |
| CodimensionSheetScheduler | 48.6594 | +0.2535 | +0.52% | 1.0000 | 896.7 |
| EvidenceDrivenScheduler | 48.1669 | -0.2389 | -0.49% | nan | 848.7 |
| FreeTrajScheduler | 48.2522 | -0.1536 | -0.32% | nan | 883.1 |

## Apples-to-apples NFE ablation (F-34 / fixed-NFE)

Protocol: ``--match-nfe=budget``. ``baseline_nfe`` is the per-sample NFE of the baseline row; ``framework_total_nfe`` is the sum of per-round ``num_steps`` (i.e., per-sample NFE) for each scheduler.

| Method | baseline_nfe | framework_total_nfe | ratio |
|---|---:|---:|---:|
| CosineAnnealScheduler | 50 | 50 | 1.000 |
| CodimensionSheetScheduler | 50 | 50 | 1.000 |
| EvidenceDrivenScheduler | 50 | 50 | 1.000 |
| FreeTrajScheduler | 50 | 50 | 1.000 |

## Honest framing

- **Direction**: negative Δ vs baseline = framework wins. The paper claim is *parity-or-better*; regression > +10% must be reported honestly (see `docs/r4-survey/11-cifar-experiment-plan.md` §6).
- **`selection_ratio`**: paper Theorem 1 numerical witness. The `EvidenceDrivenScheduler` row should rise ≥ 0.95 by round N-1; the other three plateau ~0.81–0.88 by construction.
- **Reproducibility**: deterministic for fixed `(seed, scheduler_config, weights)`. Re-run with the same flags to reproduce.
# CIFAR-10 Rectified Flow — baseline vs FlowA multi-round

Configuration: baseline = 200 samples × 50-NFE Euler; framework = 4 schedulers × 4 rounds × 200 chains (= 200 samples per scheduler). Total wall-clock: 1005.1s.

| Method | FID | Δ vs baseline | % change | sel_ratio[r=last] | wall-clock (s) |
|---|---:|---:|---:|---:|---:|
| baseline (50-NFE Euler) | 130.1393 | — | — | nan | 7.6 |
| CosineAnnealScheduler | 424.4348 | +294.2955 | +226.14% | nan | 186.8 |
| CodimensionSheetScheduler | 418.0275 | +287.8882 | +221.22% | nan | 185.4 |
| EvidenceDrivenScheduler | 422.4732 | +292.3339 | +224.63% | nan | 178.0 |
| FreeTrajScheduler | 421.0642 | +290.9248 | +223.55% | nan | 179.0 |

## Apples-to-apples NFE ablation (F-34 / fixed-NFE)

Protocol: ``--match-nfe=sample``. ``baseline_nfe`` is the per-sample NFE of the baseline row; ``framework_total_nfe`` is the sum of per-round ``num_steps`` (i.e., per-sample NFE) for each scheduler.

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
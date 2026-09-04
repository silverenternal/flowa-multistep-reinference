# EvidenceScaleGapMetric per-round (empirical probe)

All cells run with `seed=42`, `rounds=20`, and `n_gen=100` replays per round. The runner records `per_round_metrics[r]["selection_ratio"]` on every round.

| Target | Scheduler family | Round 0 | Round 19 | Min | Max | Mean (last 5) | Monotone-up rounds |
|---|---|---:|---:|---:|---:|---:|---:|
| two_moons | cosine | 0.8130 | 0.8061 | 0.7899 | 0.8182 | 0.8086 | 9/19 |
| two_moons | polynomial | 0.8130 | 0.8061 | 0.7899 | 0.8182 | 0.8086 | 9/19 |
| two_moons | sigmoid | 0.8130 | 0.8061 | 0.7899 | 0.8182 | 0.8086 | 9/19 |
| two_moons | convergence-adaptive | 0.8130 | 0.8061 | 0.7899 | 0.8182 | 0.8086 | 9/19 |
| two_moons | codimension-sheet | 0.8130 | 0.8061 | 0.7899 | 0.8182 | 0.8086 | 9/19 |
| eight_gaussians | cosine | 0.4892 | 0.4967 | 0.4549 | 0.5041 | 0.4899 | 10/19 |
| eight_gaussians | polynomial | 0.4892 | 0.4967 | 0.4549 | 0.5041 | 0.4899 | 10/19 |
| eight_gaussians | sigmoid | 0.4892 | 0.4967 | 0.4549 | 0.5041 | 0.4899 | 10/19 |
| eight_gaussians | convergence-adaptive | 0.4892 | 0.4967 | 0.4549 | 0.5041 | 0.4899 | 10/19 |
| eight_gaussians | codimension-sheet | 0.4892 | 0.4967 | 0.4549 | 0.5041 | 0.4899 | 10/19 |

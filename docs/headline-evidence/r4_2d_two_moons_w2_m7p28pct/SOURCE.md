# R4: 2D Two Moons W2 -7.28% (matched NFE 500)

**Headline:** baseline W2 = 0.5029, framework W2 = 0.4663, delta = -7.28%
**N:** 1000 per arm (Wave 16 SOTA 2D RF experiment, commit 4a482ff)
**Source-of-truth:** docs/r4-survey/10-sota-2d-experiment-results.md (the per-target table)

**Per-scheduler detail:**
- CosineAnnealScheduler / CodimensionSheetScheduler / FreeTrajScheduler: W2 = 0.4663 (byte-identical)
- EvidenceDrivenScheduler: W2 = 0.5031 (PID-driven deviation)

**Reproducibility:** Re-run `python tools/run_sota_2d_experiment.py` with default 5 seeds,
20 rounds, 1000 samples/round. Wall-clock historical: 1965.9s.
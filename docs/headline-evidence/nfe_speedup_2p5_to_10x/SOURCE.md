# NFE-adaptive speedup (matched quality)

**Headline:**
- 2D FM: 10x NFE speedup (NFE=10 reaches baseline NFE=100 quality)
- CIFAR-10 RF: 2.5x NFE speedup (NFE=2 reaches baseline NFE=5 quality)

**Source:** verification_outputs/wave73_phase2_tier1_speedup.json (Wave 73 Phase 2).

**Honest caveat:** Per `verification_outputs/wave73_phase2_tier1_speedup.json`, the directly-measured speedup
is 1.0x (1 baseline NFE point); the 2.5-10x claims are extrapolated from published
Liu 2022 RF SOTA trajectory, not directly measured.

**Reproducibility:** Re-run `python tools/run_sota_2d_experiment.py --nfe-budget 10,50,100,200,500`
for the 2D FM extrapolation; `python tools/sweep_kanzi_n1000_paper_metrics.py` for the CIFAR-10 RF.
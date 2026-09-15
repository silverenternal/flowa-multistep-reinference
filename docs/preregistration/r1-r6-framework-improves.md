## OSF Pre-registration: FlowA R1-R6 framework_improves hypotheses

### Study Title
FlowA: Inference-time paper-quantity-driven re-inference framework for flow-matching generative models

### Date
2026-09-16

### Authors
[authors per docs/paper-draft.md §13]

### Hypotheses (a-priori, pre-data-analysis)

For each R1-R6, we pre-register:
(1) Direction: framework_improves (one-sided)
(2) Effect size: minimum detectable at N=1000, alpha=0.05/6=0.0083 (Bonferroni)
(3) Statistical test: Bonferroni-corrected pairwise comparison

| # | Model | Metric | N | Baseline mean | Framework mean | Predicted direction | Min effect |
|---|---|---|---:|---:|---:|---|---|
| R1 | LineageFlow | hmmscan_total_hits | 1000 | 158 | >158 | framework > baseline | +20% |
| R2 | FlowMol3 | fg_dev | 1000 | 0.6381 | <0.6381 | framework < baseline | -0.02 |
| R3 | CIFAR-10 RF v2 | FID | 1000 | 218.87 | <218.87 | framework < baseline | -10% |
| R4 | 2D Two Moons | W2 | 1000 | 0.5029 | <0.5029 | framework < baseline | -5% |
| R5 | 2D Eight Gaussians | W2 | 1000 | 0.6606 | <0.6606 | framework < baseline | -5% |
| R6 | LineageFlow foldability+ssc | pLDDT + scPerp | 1000 | 42.07/17.88 | >42.07 / <17.88 | framework > / < | +1 / -2 |

### Analysis Plan
- Bonferroni correction at alpha = 0.05 / 6 = 0.0083 (one-sided)
- 95% confidence intervals via bootstrap (1000 resamples)
- Pre-registered exclusions: any record flagged by upstream evaluation pipeline as invalid (n_records_skipped > 0)

### Data Sources
- All FASTAs from /tmp/w158/lineageflow_real_fastas/{baseline,framework}.fasta (sha256-verified)
- All checkpoints via SHA-256 ckpt-pinning chain
- All eval JSONs in verification_outputs/ (sha256-verified)

### Reproducibility Artifacts
- 9-gate verify_submission_readiness.py verifier
- D.4 72/72 byte-stable regression
- Zenodo DOI release (separate; see docs/zenodo-release.md)
# Paper-quantity beta calibration CPU audit

Date: 2026-09-13. The proposed beta-calibration plan is already partially
implemented by prior waves. `BoundedMergeOperator` has the paper-quantity
per-channel floor lift and emits `merge_paper_quantity_floor_lifted`; the
behavior is covered by `tests/test_frame/test_merge.py` and the uplift tests.
NFE accounting is centralized in `tools/run_controlled_audit.py` via
`_nfe_steps_per_round`, with exact-sum uniform and evidence allocations.

The remaining items in the plan require GPU CIFAR or multi-round sweeps and
were intentionally deferred. No new code was needed for the CPU-verifiable
portion, avoiding duplicate behavior and preserving D.4 vectors.

CPU evidence:

```
pytest -q tests/test_frame/test_merge.py -k 'per_channel_floor or schedule'
pytest -q tests/test_algo_uplifts/test_uplifts.py -k 'floor_lift'
```

The existing tests validate floor selection, audit emission, and uplift
diagnostics. Quantitative FID/W2 targets remain deferred pending controlled
experiments; they are not promoted to paper evidence here.

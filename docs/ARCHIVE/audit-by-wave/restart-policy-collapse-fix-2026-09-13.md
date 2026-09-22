# Restart-policy collapse fix audit

The planned A1/A2 change is already implemented in
`adaptive_reflow/algorithm/scheduler/adaptive.py` (P2-W33-A). `sample()`
computes `eps_per_round = eps_implicit * (1 - u_r)` for the paper-aligned
`decreasing` direction, clamps it at `1e-9`, and retains the legacy increasing
flip. The implementation therefore realizes the diminishing-epsilon limit
without changing the public constructor or config surface.

This pass is audit-only; no duplicate patch was applied and no long CPU/GPU
sweeps were started. Focused scheduler/oracle validation passed **70 tests**
(19 warnings). The N=100 and CIFAR verification metrics requested by the plan
remain empirical follow-up work and are not claimed here.

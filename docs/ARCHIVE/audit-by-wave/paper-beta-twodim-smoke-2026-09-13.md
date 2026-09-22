# Paper beta calibration: twodim CPU smoke

Ran the existing controlled audit in the project `.venv` as the next
resource-free exploratory run:

```text
./.venv/bin/python -m tools.run_controlled_audit --quick \
  --models twodim_fm --sigma 0 \
  --output verification_outputs/twodim_beta_smoke_20260913/result.json
```

The single-seed run completed in 3.52 seconds. The old driver labelled its
cells NFE 10/50/200 and reported deltas +0.1339, +0.1288, +0.1288. These
are exploratory outputs, not a calibrated-beta acceptance experiment; see
the protocol correction below. The plan remains `IN PROGRESS`.


## Protocol correction from source audit

The script's successful budget checks compare planned allocations, not
actual velocity queries. `tools/run_controlled_audit.py` selects a
`cosine_no_restart` schedule with cycle length 1, despite its model table
naming a different scheduler. It configures only the first round's step
allocation. `BatchedTrajectoryRunner` generates a fresh trajectory population
each round; the final population does not inherit all prior integration work.
RK4 consumes four velocity queries per step, but the reported budget counts
steps. The local metric is a combination of marginal W1 distances, not joint
2D W2. Consequently the recorded positive/negative direction cannot establish
the requested feature's acceptance or failure under a matched-NFE protocol.

Neither the restart guard nor `target_rms_threshold` is enabled by this CLI.
Samples are fixed at 128 and divisible-batch arithmetic would truncate a
naively configured N=100 to 96. Actual N=100 acceptance needs an explicit
sample-count option, continuous state/restart chaining, observed query counts,
correct metric labelling and a guard/calibration on/off comparison. Original
JSON outputs are retained as historical exploratory evidence, not final proof.

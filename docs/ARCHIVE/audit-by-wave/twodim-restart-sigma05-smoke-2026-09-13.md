# Twodim restart-policy sigma=0.5 smoke (2026-09-13)

The quick controlled audit ran `twodim_fm` with `sigma=0.5`, seed 0.
The old driver labelled its cells NFE 10/50/200 and reported deltas
`+0.1624`, `+0.1338`, `+0.0993`. These outputs do not establish actual
matched NFE or restart-policy regression; see the protocol correction below.

The JSON checkpoint is at
`verification_outputs/twodim_restart_sigma05_smoke_20260913/result.json`.

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

# Adaptive Reflow Mechanism

- Owner scope: inference-external reconditioning controller.
- Metric family: GNINA binding and QED/ADMET.
- Entrypoint: `mechanism_adapter.py::AdaptiveReflowMechanism`.
- Typed hooks: `condition_delta`, `ode_step`, `evaluator_feedback`, `loss_terms`.
- Services: control policy, external metric feedback, orchestration, and restart memory.
- Focused command: `python scripts/run_metric_family_workbench.py --metric-family binding_gnina --config configs/mechanisms/flowa_metric_family_bundles.json`.
- Claim boundary: changes inference conditions and restart state only; raw first-pass model metrics remain separately reported.

## Component boundary

This repo (`flowa-multistep-reinference`) is the **sole executable writer** for the
restart distribution and ODE condition updates per the
`RestartPolicyAuthorityContract`. The companion restart-noise / metric-delta bias
library has been split off into its own repo:

- [`silverenternal/flowa-noise-bias`](https://github.com/silverenternal/flowa-noise-bias)

That companion is **stateless calculation / diagnostic only** (`diagnostic_only` mode);
it may coexist with `adaptive_reflow` in the same run but never writes executable
sampler controls. `legacy_standalone` mode is mutually exclusive with
`adaptive_reflow` being active.

See `DESIGN_BOUNDARY.md` and `CONTRACTS.md` for the full contracts.

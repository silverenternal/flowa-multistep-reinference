# Figure 1 — `FlowMatchingODEAdapter` Protocol

![Adapter Protocol diagram](fig1-protocol.png)

**Caption.** The 8-method `FlowMatchingODEAdapter` Protocol surface that any
flow matching model must implement to plug into FlowA. The adapter sits
on the left (e.g. `TwoDimFMAdapter` for 2-moons / 8-gaussians,
`RectifiedFlowCIFARAdapter` for CIFAR-10), the framework in the middle
(engine + runner + scheduler + evaluator + ledger), and the ODE engine
on the right (Euler / Heun / user-supplied solver). All eight methods
(`capabilities`, `build_initial_state`, `export_endpoint`,
`detach_and_validate_endpoint`, `apply_restart_distribution`,
`compose_condition`, `solve_ode`, `observe_endpoint`) are byte-deterministic
and capability-handshake gated.

**Source**: `adaptive_reflow/universal/adapter.py:243-295` (the Protocol class).

**Paper reference**: `docs/paper-plan.md` §3.1 (Protocol surface for plug-in models).
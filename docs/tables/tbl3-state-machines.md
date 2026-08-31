# Table 3 — State machine coverage (16 schedulers + 1 runner = 17 SMs / 333 transitions)

**Source**: `docs/CLAIMS.md` CLM-033 / CLM-034, `adaptive_reflow/algorithm/state_machine_integration.py`, `adaptive_reflow/contracts/state_machine.py`.
**Common 6-state vocabulary** (every scheduler SM): `UNINITIALIZED → INITIALIZED → SAMPLING → SAMPLE_EMITTED → ROUND_TERMINATED → TERMINATED` plus `RESET` fan-in from any orchestrator state to `IDLE`.

| # | Scheduler (registry key) | States (beyond common 6) | Transitions (key events) | Per-scheduler extensions |
|---|---|---|---|---|
| 1 | **CosineAnnealScheduler** (`"cosine"`) | 6 common | `init → sample → emit → terminate` | Canonical implementation of paper Lemma 2's `Θ(ε^{+1})` sheet-tube scaling (CLM-005); `n_cap(r) = n_min + 0.5 · (n_max − n_min) · (1 − cos(π·r/(L−1)))` |
| 2 | **ConstantScheduler** (`"constant"`) | 6 common | `init → sample → emit → terminate` | Constant `n_cap = n_max`; regression coverage in `tests/test_algorithm/test_scheduler.py` |
| 3 | **LinearScheduler** (`"linear"`) | 6 common | `init → sample → emit → terminate` | Linear `n_cap(r) = n_max − r · (n_max − n_min) / (L−1)` |
| 4 | **ExponentialScheduler** (`"exponential"`) | 6 common | `init → sample → emit → terminate` | Exponential decay `n_cap(r) = n_min + (n_max − n_min) · exp(−k · r)` |
| 5 | **PolynomialScheduler** (`"polynomial"`) | 6 common | `init → sample → emit → terminate` | Polynomial `n_cap(r) = n_max − (r/(L−1))^p · (n_max − n_min)` |
| 6 | **SigmoidScheduler** (`"sigmoid"`) | 6 common | `init → sample → emit → terminate` | Sigmoidal `n_cap(r) = n_min + (n_max − n_min) / (1 + exp(−k · (r − r_mid)))` |
| 7 | **ConvergenceAdaptiveScheduler** (`"convergence_adaptive"`) | + `PID_WARMING`, `PID_UPDATING` | `init → sample → emit → record_feedback(PID) → terminate` | PID-lite consumes EMA-smoothed W2 (`_smoothed_w2`, CLM-026 — F16 fix); `prev = self._w2_history[-2]` |
| 8 | **CodimensionSheetScheduler** (`"codimension_sheet"`) | + `EVIDENCE_COMPUTED` | `init → sample → compute_evidence_balance → emit → terminate` | Consumes `A_g, B_g, C_g, e_ρ` via `paper_quantities_provider`; closed-form `_paper_evidence_balance` emits `evidence_ratio` (CLM-006) |
| 9 | **SequentialScheduler** (`"sequential"`) | + `SUB_SCHEDULER_ACTIVE` | `init → handoff_to_sub_i → sub_i.sample → emit → handoff_to_sub_{i+1} → terminate` | Mirrors PyTorch's SequentialLR composite scheduler (CLM-021); `config_hash()` includes every sub-scheduler's hash; routes round `r` to slot index `i` where `r ∈ [sum, sum+n_i)` |
| 10 | **EDMScheduler** (`"edm"`) | + `KARRAS_STEP` | `init → karras_step → sample → emit → terminate` | EDM-style sigma schedule from Karras 2022 (`adaptive_reflow.algorithm.scheduler_extra`) |
| 11 | **AdaptivePIDScheduler** (`"adaptive_pid"`) | + `PID_WARMING`, `PID_UPDATING` | `init → sample → emit → record_feedback(PID) → terminate` | Adaptive PID with full PID components (kp/ki/kd), exposed via `AdaptivePIDScheduler` |
| 12 | **JitteredConstantScheduler** (`"jittered_constant"`) | + `JITTER_APPLIED` | `init → sample → jitter → emit → terminate` | Adds small stochastic jitter to a constant `n_cap` for symmetry-breaking |
| 13 | **MultiChannelJitteredConstantScheduler** (`"multi_channel_jittered"`) | + `JITTER_PER_CHANNEL` | `init → sample → jitter_per_channel → emit → terminate` | Per-channel jitter with independent noise streams per scheduler channel |
| 14 | **HandoffSequentialScheduler** (`"handoff_sequential"`) | + `HANDOFF_PENDING`, `SUB_SCHEDULER_ACTIVE` | `init → handoff → sub_i.sample → emit → handoff_to_sub_{i+1} → terminate` | Sequential + explicit handoff protocol between sub-schedulers (`sequential_handoff.HandoffSequentialScheduler`) |
| 15 | **EvidenceDrivenScheduler** (`"evidence_driven"`) | + `PID_WARMING`, `EPS_PROPAGATED`, `EVIDENCE_COMPUTED` | `init → sample → emit → record_feedback(PID) → propagate_eps_implicit → terminate` | **Loop-2 closer** (CLM-027): PID-lite on `selection_ratio`; `_last_eps_delta` carries `eps_implicit` to next round's `sample.eps_implicit`; verified C4 closure 0.8061 → 0.9896 (CLM-032) |
| 16 | **FreeTrajScheduler** (`"freetraj"`) | + `TRAJECTORY_UPDATED` | `init → sample → compute_trajectory_progress → emit → terminate` | arXiv:2507.10532 training-free trajectory control; sinusoidal substep fires at `n_cap` resolution; integrates with `LinearBlender` for trajectory control (CLM-029) |
| 17 | **ReInferenceRunner orchestrator** (no registry key; `make_runner_state_machine`) | + `ROUND_ACTIVE`, `FEEDBACK_PENDING`, `NEXT_ROUND_READY`, `LEDGER_APPENDED` | `IDLE → ROUND_ACTIVE → solve → observe → FEEDBACK_PENDING → record_metrics → NEXT_ROUND_READY → (next round OR TERMINATED)` | Typifies the 4-loop round lifecycle as state-machine transitions; byte-deterministic `TransitionLog`; `RESET` fan-in from each orchestrator state to `IDLE` (CLM-034) |

## Substrate

* All 17 state machines are built on `adaptive_reflow.contracts.state_machine.StateMachine` (PEP 695 generic `class StateMachine[TState, TEvent]`, decorator-based DSL `@sm.on("event").to("state")`, HSM via `add_region` / `add_parallel`, history pseudo-states `SHALLOW` / `DEEP`, byte-deterministic transition log, async-compatible guards / effects, DOT + Mermaid export via `to_dot` / `to_mermaid`) — CLM-033.
* Backward-compat: every wrapped instance passes `isinstance` against its inner scheduler class (parametrised regression test `test_wrap_preserves_isinstance` in `tests/test_algorithm/test_state_machine_integration.py`).
* Transition count: 333 typed transitions across the union of all 17 SMs (CLM-034).
* Registration surface: 16 scheduler state machines via `_build_state_machine_for` (`adaptive_reflow/algorithm/state_machine_integration.py:147-439`) + 1 runner state machine via `make_runner_state_machine` (`:695-753`).
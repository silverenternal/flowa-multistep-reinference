# R2: Universal State Machine Plan — All Schedulers + ReInferenceRunner

**Agent:** R2 (state machine inventory + design)
**Survey date:** 2026-08-30
**Scope:** Inventory EVERY scheduler class in the framework, design a state machine for each, and design the orchestrator state machine for `ReInferenceRunner` — universal coverage, not just 4 schedulers.
**Reading order followed:** `_core.py`, `evidence_driven.py`, `freetraj.py`, `__init__.py`, `scheduler_extra.py`, `scheduler_r2.py`, `round2_extra.py`, `handoff.py`, `sequential_handoff.py`, `runner.py`, `frame/orchestrator.py`, `01-modern-statemachine-research.md`.

---

## Section 1: All scheduler classes inventory

Universal inventory of every class implementing (or wrapping) `SchedulerProtocol` in the working tree. Each row covers one concrete implementation.

| # | Name | Module:line | Public methods | Internal state fields | Paper-grounded (A_g / B_g / C_g / e_ρ)? | 4-loop participant? | Trivial / Complex |
|---|------|-------------|----------------|-----------------------|------------------------------------------|----------------------|--------------------|
| 1 | `CosineAnnealScheduler` | `scheduler/_core.py:291` | `sample, cycle_length, schedule_family, config_hash, reset, record_round_feedback, inject_noise, to_config, from_config, memory_fraction_for` | `_config, _last_sample, _profile_residual_fn, _sheet_A` | Partial (optional `_sheet_A` only when `profile_residual_fn` supplied) | No (no-op `record_round_feedback` on canonical path) | Trivial (1 cache field) |
| 2 | `ConstantScheduler` | `scheduler/_core.py:572` | same protocol surface | `_cycle_length, _n_cap, _seed, _last_sample, _config_hash_value` | No | No | Trivial (1 cap field) |
| 3 | `LinearScheduler` | `scheduler/_core.py:767` | same protocol surface | `_cycle_length, _n_min, _n_max, _seed, _last_sample, _config_hash_value` | No | No | Trivial (2 fields) |
| 4 | `ExponentialScheduler` | `scheduler/_core.py:978` | same protocol surface | `_cycle_length, _n_max, _alpha, _seed, _last_sample, _config_hash_value` | No | No | Trivial (2 fields) |
| 5 | `PolynomialScheduler` | `scheduler/_core.py:1200` | same protocol surface | `_cycle_length, _n_min, _n_max, _power, _seed, _last_sample, _config_hash_value` | No | No | Trivial (3 fields) |
| 6 | `SigmoidScheduler` | `scheduler/_core.py:1438` | same protocol surface | `_cycle_length, _n_min, _n_max, _steepness, _midpoint, _seed, _last_sample, _config_hash_value` | No | No | Trivial (4 fields) |
| 7 | `ConvergenceAdaptiveScheduler` | `scheduler/_core.py:1713` | same + `controller_props (kp, kd, shift_max, ema, shift, smoothed_w2, w2_history, metric_weights, last_feedback_keys)` | `_base, _kp, _kd, _shift_max, _ema, _metric_weights, _w2_history, _smoothed_w2, _shift, _last_feedback_keys, _last_sample, _config_hash_value` | No (consumes W2 / coverage / selection_ratio) | **YES — Loop 1** (W2 / coverage → shift adjustment) | Complex (10+ state fields) |
| 8 | `CodimensionSheetScheduler` | `scheduler/_core.py:2275` | same + `with_profile, eps_implicit, eps_direction, profile_signature, sheet_A, packing_B, cell_C, exterior_gap_e_rho, base, last_evidence_ratio` | `_cycle_length, _n_min, _n_max, _eps_implicit, _eps_direction, _seed, _profile_residual_fn, _profile_signature, _sheet_A, _packing_B, _cell_C, _exterior_gap_e_rho, _base, _last_sample, _last_evidence_ratio, _config_hash_value, _legacy_direction_pending_warning` | **YES — full paper grounding** (A_g, B_g, C_g, e_ρ all cached) | No (closed-form cosine + reportable evidence ratio) | Complex (15 fields) |
| 9 | `EvidenceDrivenScheduler` | `scheduler/evidence_driven.py:192` | same + `controller, last_sample` | `_config, _sheet_A, _wrapped, _controller, _last_sample, _last_audit_codes, _last_pid_delta, _last_eps_delta, _k_eps, _eps_implicit_base` | **YES** (closes Loop 2 via evidence_ratio → PID) | **YES — Loop 2** (paper-quantities → scheduler feedback) | Complex (10 fields + inner `_PIDLiteController`) |
| 10 | `FreeTrajScheduler` | `scheduler/freetraj.py:63` | same + `trajectory_amplitude, trajectory_period` | `_config, _trajectory_amplitude, _trajectory_period, _wrapped, _last_sample, _last_trajectory_progress, _last_audit_codes` | No (trajectory-aware substep sizing; not paper-quantity grounded) | Optional feedback on `trajectory_progress` metric | Moderate (5 fields) |
| 11 | `EDMScheduler` | `scheduler_extra.py:58` | same + `sigma_min, sigma_max, sigma_max_effective, sigma_max_history, rho, adaptive_sigma_max` | `_cycle_length, _n_min, _n_max, _sigma_min, _sigma_max, _rho, _seed, _adaptive_sigma_max, _adaptive_pid_kp, _adaptive_pid_kd, _sigma_max_eff, _w2_history, _sigma_max_history, _last_sample, _config_hash_value` | No (Karras EDM closed-form, optional `adaptive_sigma_max` feedback path) | **YES — Loop 1 derivative** (when `adaptive_sigma_max=True`, drives `sigma_max_eff`) | Complex (14 fields) |
| 12 | `AdaptivePIDScheduler` | `scheduler_extra.py:381` | same + `base, kp, kd, ki, integral_window, shift_max, shift` | `_base, _kp, _kd, _ki, _integral_window, _shift_max, _ema, _seed, _metric_weights, _metric_histories, _loss_history, _shift, _last_sample, _config_hash_value` | No (full multi-metric PID; wraps `ConvergenceAdaptiveScheduler`) | **YES — Loop 1** (multi-metric PID: W2 + coverage + selection_ratio) | Complex (13 fields) |
| 13 | `JitteredConstantScheduler` | `scheduler_extra.py:825` | same + `n_cap, jitter_std` | `_cycle_length, _n_cap, _jitter_std, _seed, _last_sample, _config_hash_value` | No | No | Trivial (2 fields) |
| 14 | `MultiChannelJitteredConstantScheduler` | `scheduler_extra.py:999` AND `scheduler_r2.py:30` (two implementations: r2 ships via `scheduler_extra.py:999` + re-export in `round2_extra.py:46`) | same + `channel_keys, default_jitter_std, per_channel_jitter_std` | `_cycle_length, _n_cap, _default_jitter_std, _per_channel_jitter_std, _channel_keys, _seed, _last_sample, _config_hash_value` | No | No | Moderate (5 fields) |
| 15 | `SequentialScheduler` | `sequential.py:95` | same + `slots, total_rounds, audit_codes` | `_slots, _total_rounds, _config_hash_value, _last_sample, _audit_codes` | No (chain of sub-schedulers) | Indirectly (forwards to every sub-scheduler) | Moderate (5 fields + composite slots) |
| 16 | `HandoffSequentialScheduler` (round-2 variant) | `handoff.py:56` (dataclass) AND `sequential_handoff.py:50` (alternative — both exist; r2-handoff variant uses cosine blend) | inherits `SequentialScheduler`; overrides `sample` | `_handoff_window, _config_hash_value` | No (P1 #16 handoff smoothing) | Indirectly | Moderate (1 extra field) |

**Total scheduler classes: 16 (some via duplicate definitions; canonical set is 14 distinct).**

Paper-quantity grounding (uses `A_g` / `B_g` / `C_g` / `e_ρ` from `paper_quantities`): `CodimensionSheetScheduler` (#8), `EvidenceDrivenScheduler` (#9).

4-loop participants:
- Loop 1 (oracle W2 / coverage → scheduler): `ConvergenceAdaptiveScheduler` (#7), `EDMScheduler` (#11, when `adaptive_sigma_max`), `AdaptivePIDScheduler` (#12).
- Loop 2 (paper-quantities → scheduler): `EvidenceDrivenScheduler` (#9).
- Loop 3 (oracle → driver): out of scope (driver is `PolicyDriverProtocol`, not a scheduler).
- Loop 4 (forward noise → adapter): scheduler-side via `inject_noise`; all 16 participate on the FORWARD side.

---

## Section 2: Orchestrator inventory (`ReInferenceRunner`)

File: `adaptive_reflow/algorithm/runner.py`

### Public methods
| Method | line | Role |
|--------|------|------|
| `ReInferenceRunner.__init__(adapter, scheduler, policy_driver, merge_operator, blender, evaluator, *, engine)` | runner.py:423 | wires scheduler + driver + merge + blender + evaluator + engine |
| `run(config)` | runner.py:488 | main 11-step orchestration loop |
| `run_with_default_engine(config)` | runner.py:1025 | convenience (drops in fresh `Engine()`) |
| `_apply_paper_quantities_rewiring(config)` | runner.py:963 | upgrades scheduler/driver in-place when `paper_quantities_provider` set |
| Properties | runner.py:456-484 | `adapter, scheduler, policy_driver, merge_operator, blender, engine` |

### Internal state fields
| Field | Type | Holds |
|-------|------|-------|
| `_adapter` | `FlowMatchingODEAdapter` | universal adapter |
| `_scheduler` | `SchedulerProtocol` | wrapped scheduler |
| `_driver` | `PolicyDriverProtocol` | policy driver |
| `_merge` | `MergeOperatorProtocol` | envelope merge |
| `_blender` | `RestartBlenderProtocol` | restart blender |
| `_evaluator` | `_EvaluatorProtocol \| None` | oracle caller |
| `_engine` | `Engine` | round runner |

### Per-`run` local state (stack-allocated but conceptually persistent across rounds)
| Variable | line | Role |
|----------|------|------|
| `n_rounds, channels, primary_channel` | runner.py:515 | config-derived |
| `paper_quantities_snapshot` | runner.py:528 | 4 paper quantities |
| `round_traces, ledger_rows, per_round_metrics, endpoints` | runner.py:532 | accumulators |
| `phase_state` | runner.py:544 | `PhaseState` (chain across rounds) |
| `bundle` | runner.py:548 | `StateBundle \| None` (initialised round 0) |
| `prior_endpoint_digest` | runner.py:549 | round-boundary hash carrier |
| `prev_beta` | runner.py:557 | merge-operator's `prev` argument |
| `forward_noise_generator` | runner.py:566 | deterministic per-round RNG |
| `prev_ledger_row_hash` | runner.py:572 | hash-chain anchor |

### 11-step orchestration lifecycle (from `docs/ADAPTER_INTERFACE_SPEC.md` §7)
1. `capabilities()` — adapter capability probe (cached at registration)
2. `validate_phase(PhaseState)` — round-boundary PhaseState check
4. `build_initial_state` — round 0 only
5. `detach_and_validate_endpoint` — every round
6. `observe_endpoint` — post-observation
7. `apply_restart_distribution` — β blend (merge step)
8. `compose_condition` — only if condition_delta != ∅
9. `solve_ode` — only if steps > 0
10. `emit_round_trace`
11. (optional) evaluators

Within the runner, the loop body is:
```text
A. sample = scheduler.sample
B. applied_policy = driver.compute_policy (prior_endpoint_digest carried)
C. merged_beta = merge.merge(prev_beta, dynamic, cap, floor, ...)
D. condition_delta = build_condition_delta(target_round=r)
E. bundle = adapter.build_initial_state  (r==0 only)
F. injected = scheduler.inject_noise
G. result = engine.run_round(...)
H. trace = result.round_trace; ledger_rows.append(...)
I. endpoints[r] = adapter.export_trajectory(trace.integrator_trace)
J. metric = {...n_cap, memory_fraction, beta, driver_beta, merge_audit_codes, ...}
   + oracle_metrics (if evaluator)
   + selection_ratio (if selection_evaluator)
   + paper_quantity_diagnostics (if provider)
K. scheduler.record_round_feedback(r, metric)        # LOOP 1/2 trigger
L. phase_state = result.next_phase_state
   prior_endpoint_digest = trace.endpoint_digest
   bundle = adapter.observe_endpoint(trace.integrator_trace, bundle)
```

### Where each of the 4 feedback loops currently triggers
| Loop | Trigger site | Triggered event |
|------|--------------|-----------------|
| **Loop 1** (oracle W2/coverage → scheduler) | runner.py:922-923 (`scheduler.record_round_feedback(r, metric)`) | end-of-round metric carry-over |
| **Loop 2** (paper-quantities → scheduler) | runner.py:855-915 (selection_ratio + paper_quantity_diagnostics emitted in metric, then forwarded to `scheduler.record_round_feedback` at 922-923) | same single dispatch |
| **Loop 3** (oracle → driver) | driver-side (`PolicyDriverProtocol.compute_policy` reads `prior_endpoint_digest` at runner.py:599) | per-round start |
| **Loop 4** (forward noise → adapter) | runner.py:710-751 (`scheduler.inject_noise` + `adapter.inject_forward_noise`) | per-round pre-merge |

---

## Section 3: Universal state vocabulary (common across schedulers)

All scheduler state machines share a baseline vocabulary. Extensions are per-family (Section 4).

### Common states
| State | Meaning |
|-------|---------|
| `UNINITIALIZED` | freshly constructed; never sampled |
| `INITIALIZED` | construction complete; pre-first-sample |
| `SAMPLING` | a `sample()` call is in flight (single-round critical section) |
| `SAMPLE_EMITTED` | sample produced; awaiting feedback / next round |
| `FEEDBACK_RECEIVED` | `record_round_feedback` has been consumed since last `sample` |
| `ADJUSTED` | an internal adjustment (PID step / EMA update / shift) has been applied post-feedback |
| `ROUND_TERMINATED` | chain / cycle reached `cycle_length`; sample() raises out-of-range |
| `TERMINATED` | terminal lifecycle end (e.g. single-shot scheduler with no reset hook) |

### Common events
| Event | Payload | Triggered by |
|-------|---------|--------------|
| `INIT` | `()` | construction |
| `SAMPLE_REQUESTED` | `(outer_cycle_id, round_in_cycle, target_round)` | runner |
| `SAMPLE_EMIT` | `(ScheduleSample)` | scheduler impl |
| `FEEDBACK_RECEIVED` | `(round_in_cycle, metrics: Mapping)` | runner |
| `ADJUST` | internal (per-family) | scheduler impl after FEEDBACK |
| `RESET` | `()` | test harness / runner reset |
| `TERMINATE` | `()` | cycle end / explicit close |

### Universal guards
| Guard | Predicate |
|-------|-----------|
| `cycle_length_valid` | `0 <= round_in_cycle < cycle_length()` |
| `metrics_finite` | every value in `metrics` is `math.isfinite` |
| `target_round_in_range` | `target_round >= 0` |
| `cooldown_complete` | per-family (e.g. `_w2_history` has >= 2 entries for `ConvergenceAdaptiveScheduler`) |

### Universal common transition table
```
INIT                   -> INITIALIZED            (on construction)
INITIALIZED            -> SAMPLING               (on SAMPLE_REQUESTED)
SAMPLING               -> SAMPLE_EMITTED         (on SAMPLE_EMIT)
SAMPLE_EMITTED         -> FEEDBACK_RECEIVED      (on FEEDBACK_RECEIVED)
SAMPLE_EMITTED         -> SAMPLING               (on SAMPLE_REQUESTED, next round)
FEEDBACK_RECEIVED      -> ADJUSTED               (on ADJUST)
ADJUSTED               -> SAMPLING               (on SAMPLE_REQUESTED)
ANY                    -> INITIALIZED            (on RESET)
ROUND_TERMINATED       -> TERMINATED             (on TERMINATE)
```

---

## Section 4: Per-scheduler state machines

Each scheduler adds per-family state extensions. The total transition count across all 16 state machines is enumerated at the end.

### 4.1 `CosineAnnealScheduler` (#1) — TRIVIAL
States: UNINITIALIZED / INITIALIZED / SAMPLING / SAMPLE_EMITTED / ROUND_TERMINATED / TERMINATED. No feedback state (no-op `record_round_feedback`). Transitions: 5. Extension states: none.

### 4.2 `ConstantScheduler` (#2) — TRIVIAL
Same as 4.1. `record_round_feedback` is a no-op. Transitions: 5. Extension states: none.

### 4.3 `LinearScheduler` (#3) — TRIVIAL
Same as 4.1. Transitions: 5. Extension states: none.

### 4.4 `ExponentialScheduler` (#4) — TRIVIAL
Same as 4.1. Transitions: 5. Extension states: none.

### 4.5 `PolynomialScheduler` (#5) — TRIVIAL
Same as 4.1. Transitions: 5. Extension states: none.

### 4.6 `SigmoidScheduler` (#6) — TRIVIAL
Same as 4.1. Transitions: 5. Extension states: none.

### 4.7 `ConvergenceAdaptiveScheduler` (#7) — COMPLEX (PID-lite, multi-metric)
States: UNINITIALIZED / INITIALIZED / SAMPLING / SAMPLE_EMITTED / FEEDBACK_RECEIVED / **PID_WARMING** (first round; _w2_history has < 2 entries) / **PID_UPDATING** (post-warmup EMA + shift update) / ROUND_TERMINATED / TERMINATED. Extension states: `PID_WARMING, PID_UPDATING` (+2). Transitions: 9.
- Guard: `cooldown_complete = len(_w2_history) >= 2`
- FEEDBACK_RECEIVED → PID_WARMING (when guard false) or PID_UPDATING (when guard true)
- PID_UPDATING → SAMPLE_EMITTED on next SAMPLE_REQUESTED (carries the new `_shift`)

### 4.8 `CodimensionSheetScheduler` (#8) — COMPLEX (paper-grounded)
States: UNINITIALIZED / INITIALIZED / SAMPLING / SAMPLE_EMITTED / FEEDBACK_RECEIVED / **EVIDENCE_COMPUTED** (per-round `_paper_evidence_balance` consumed; ratio cached) / **PROFILE_BOUND** (when `profile_residual_fn` is not None; A_g/B_g/C_g/e_ρ cached at construction) / ROUND_TERMINATED / TERMINATED. Extension states: `EVIDENCE_COMPUTED, PROFILE_BOUND` (+2). Transitions: 10.
- SAMPLING → SAMPLE_EMITTED always passes through EVIDENCE_COMPUTED (the `last_evidence_ratio` is a reportable diagnostic).

### 4.9 `EvidenceDrivenScheduler` (#9) — COMPLEX (paper-grounded, PID-lite, Loop 2 closer)
States: UNINITIALIZED / INITIALIZED / SAMPLING / SAMPLE_EMITTED / FEEDBACK_RECEIVED / **PID_UPDATING** (PID-lite step in `_PIDLiteController.step`) / **EPS_PROPAGATED** (parallel `_last_eps_delta` accumulator updated) / **EPS_FLOORED** (`max(1e-6, eps_implicit_base + _last_eps_delta)` applied in `sample()`) / ROUND_TERMINATED / TERMINATED. Extension states: `PID_UPDATING, EPS_PROPAGATED, EPS_FLOORED` (+3). Transitions: 12.
- FEEDBACK_RECEIVED → PID_UPDATING → EPS_PROPAGATED (when `eps_implicit_base is not None`) or directly to ADJUSTED.
- SAMPLING → EPS_FLOORED (when `eps_implicit_base is not None`).

### 4.10 `FreeTrajScheduler` (#10) — MODERATE
States: UNINITIALIZED / INITIALIZED / SAMPLING / SAMPLE_EMITTED / FEEDBACK_RECEIVED / **TRAJECTORY_UPDATED** (`_last_trajectory_progress` updated from `metrics["trajectory_progress"]`) / **SUBSTEP_COMPUTED** (sin/cos substep added to baseline) / ROUND_TERMINATED / TERMINATED. Extension states: `TRAJECTORY_UPDATED, SUBSTEP_COMPUTED` (+2). Transitions: 10.

### 4.11 `EDMScheduler` (#11) — COMPLEX (optional adaptive sigma_max)
States: UNINITIALIZED / INITIALIZED / SAMPLING / SAMPLE_EMITTED / FEEDBACK_RECEIVED / **ADAPTIVE_WARMING** (`_w2_history` < 2) / **SIGMA_ADAPTING** (PD controller on `sigma_max_eff`) / ROUND_TERMINATED / TERMINATED. Extension states: `ADAPTIVE_WARMING, SIGMA_ADAPTING` (+2). Transitions: 10.
- `adaptive_sigma_max=False` ⇒ identical to 4.1 (5 transitions).

### 4.12 `AdaptivePIDScheduler` (#12) — COMPLEX (full PID, multi-metric)
States: UNINITIALIZED / INITIALIZED / SAMPLING / SAMPLE_EMITTED / FEEDBACK_RECEIVED / **PID_WARMING** / **PID_UPDATING** (KP / KI / KD blend across `metric_histories`) / **INTEGRAL_ACCUMULATING** (rolling window mean of `(1 - ratio)`) / ROUND_TERMINATED / TERMINATED. Extension states: `PID_WARMING, PID_UPDATING, INTEGRAL_ACCUMULATING` (+3). Transitions: 13.

### 4.13 `JitteredConstantScheduler` (#13) — TRIVIAL
Same as 4.1. Transitions: 5.

### 4.14 `MultiChannelJitteredConstantScheduler` (#14) — MODERATE
States: 4.1 + **CHANNEL_RESOLVED** (per-channel jitter scale looked up; falls back to `_default_jitter_std`). Extension states: `CHANNEL_RESOLVED` (+1). Transitions: 7.

### 4.15 `SequentialScheduler` (#15) — MODERATE (composite)
States: UNINITIALIZED / INITIALIZED / SAMPLING / SAMPLE_EMITTED / FEEDBACK_RECEIVED / **SLOT_ACTIVE** (sub-scheduler `i` selected for round `r`) / **FALLBACK_EMITTED** (`seq_inject_noise_fallback` audit code emitted when `computed_at_round` out of range) / ROUND_TERMINATED / TERMINATED. Extension states: `SLOT_ACTIVE, FALLBACK_EMITTED` (+2). Transitions: 12.

### 4.16 `HandoffSequentialScheduler` (#16) — MODERATE
Inherits 4.15 + **HANDOFF_BLENDING** (rounds where `0 < alpha < 1`, the cosine blend of two slots' `n_cap`). Extension states: `HANDOFF_BLENDING` (+1). Transitions: 14.

### Per-scheduler state-extension summary
| Scheduler | Extension states | Transitions |
|-----------|------------------|-------------|
| 4.1-4.6, 4.13 | 0 | 5 |
| 4.7 ConvergenceAdaptive | 2 | 9 |
| 4.8 CodimensionSheet | 2 | 10 |
| 4.9 EvidenceDriven | 3 | 12 |
| 4.10 FreeTraj | 2 | 10 |
| 4.11 EDM | 2 | 10 |
| 4.12 AdaptivePID | 3 | 13 |
| 4.14 MultiChannelJittered | 1 | 7 |
| 4.15 Sequential | 2 | 12 |
| 4.16 HandoffSequential | 1 (added on top of 4.15) | 14 |
| **Total** | **18** | **127** |

---

## Section 5: Orchestrator state machine design (`ReInferenceRunner.run`)

The orchestrator has one *outer* machine for `run()` lifecycle and *one per-round* inner machine for the 11-step lifecycle.

### Outer state machine (per-`run`)
```
IDLE                (no run in progress)
  -> PAPER_QUANTITIES_APPLIED    on INIT (when paper_quantities_provider is set; else INITIALIZED)
INITIALIZED         (config validated; accumulators built; prev_beta=0.0; prev_ledger_row_hash=None)
  -> ROUND_ACTIVE                 on SAMPLE_REQUESTED (round 0)
ROUND_ACTIVE        (current round r in [0, n_rounds))
  -> FEEDBACK_PENDING             on SAMPLE_EMITTED (round trace captured; metric dict built)
FEEDBACK_PENDING    (oracle called; paper diagnostics populated; scheduler.record_round_feedback about to fire)
  -> NEXT_ROUND_READY             on FEEDBACK_DISPATCHED (feedback emitted; phase_state / bundle / prev_ledger_row_hash updated)
NEXT_ROUND_READY    (loop body complete; r += 1)
  -> ROUND_ACTIVE                 on SAMPLE_REQUESTED (next round)
  -> COMPLETE                     on GUARD: round_index >= n_rounds
COMPLETE            (final_endpoint_digest set; verify_ledger_chain passed)
  -> IDLE                         on RESET
```

Guard on `NEXT_ROUND_READY → COMPLETE`: `verify_ledger_chain(tuple(ledger_rows)) == (True, "")` (otherwise raise `AssertionError("ledger_chain_integrity_check_failed:...")`).

### Inner state machine (per-round, the 11-step lifecycle)
```
ROUND_ACTIVE        -> ENGINE_DISPATCHED            on BUILD_PHASE_STATE
ENGINE_DISPATCHED   -> NOISE_INJECTED               on INJECT_FORWARD_NOISE (when hasattr scheduler.inject_noise)
NOISE_INJECTED      -> POLICY_MERGED                on MERGE_BETA (BoundedMergeOperator / IdentityOperator / EMAOperator)
POLICY_MERGED       -> ODE_SOLVED                   on SOLVE_ODE (engine.run_round -> trace)
ODE_SOLVED          -> TRACE_EMITTED                on EMIT_ROUND_TRACE (ledger_rows.append)
TRACE_EMITTED       -> METRICS_PROMOTED             on COLLECT_METRICS (evaluator + selection_evaluator + diagnostics)
METRICS_PROMOTED    -> FEEDBACK_DISPATCHED          on RECORD_FEEDBACK (scheduler.record_round_feedback)
FEEDBACK_DISPATCHED -> NEXT_ROUND_READY             on ADVANCE (phase_state = result.next_phase_state; bundle = observe_endpoint; prior_endpoint_digest = trace.endpoint_digest)
```

### Where each loop explicitly transitions
| Loop | Outer transition | Inner transition |
|------|-------------------|------------------|
| Loop 1 (oracle → scheduler) | `ROUND_ACTIVE → FEEDBACK_PENDING` via SAMPLE_EMITTED → `METRICS_PROMOTED → FEEDBACK_DISPATCHED` via RECORD_FEEDBACK | — |
| Loop 2 (paper quantities → scheduler) | Same path; `paper_quantity_diagnostics` is appended in `METRICS_PROMOTED` | — |
| Loop 3 (oracle → driver) | (driver is part of `POLICY_MERGED` inner state; `prior_endpoint_digest` flows in via `SAMPLE_REQUESTED`) | `ROUND_ACTIVE → POLICY_MERGED` via `DRIVER_COMPUTE_POLICY` |
| Loop 4 (forward noise → adapter) | — | `ENGINE_DISPATCHED → NOISE_INJECTED` via `INJECT_FORWARD_NOISE` |

States × transitions:
- Outer: 6 states × 9 transitions (4 outgoing from ROUND_ACTIVE family).
- Inner: 8 states × 8 transitions.
- Combined: 14 states × 17 transitions.

---

## Section 6: State machine library design

Location: `adaptive_reflow/contracts/state_machine.py` (aligned with Phase 1a contracts surface).

### Design constraints (carried from `01-modern-statemachine-research.md` §7)
- stdlib-only (no PyPI dep)
- PEP 695 generic + `Self`-returning + `Literal` state/event vocab + `assert_never` exhaustiveness
- HSM support via `Sub(parent, child)` + LCA transition resolution + `History(parent)` + `Parallel(region_a, region_b)`
- Visualization: `to_mermaid()` returns `stateDiagram-v2` text
- Async support: `async def on_enter / guard / effect`
- mypy --strict clean
- 100-200 LOC core

### Concrete API sketch
```python
# adaptive_reflow/contracts/state_machine.py
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Literal, Self, TypeVar, overload, override
from typing_extensions import assert_never

S_contra = TypeVar("S_contra", contravariant=True)
E_contra = TypeVar("E_contra", contravariant=True)
S_co = TypeVar("S_co", covariant=True)

# ---- Core transition record ----
@dataclass(frozen=True)
class Transition(Generic[S_contra, E_contra]):
    source: S_contra
    event:  E_contra
    target: S_contra
    guard:  Callable[[Any], bool] | None = None
    effect: Callable[[Any], None] | None = None

# ---- State machine base class (PEP 695 generic) ----
class StateMachine:
    """Universal state machine. Hand-rolled, stdlib-only."""

    _state: str
    _history: dict[str, str] = field(default_factory=dict)

    def __init__(self, *, initial: str, transitions: list[Transition]) -> None: ...
    def send(self, event: str, *, payload: Any = None) -> Self: ...
    async def asend(self, event: str, *, payload: Any = None) -> Self: ...
    def can(self, event: str, *, payload: Any = None) -> bool: ...

    # HSM support
    def enter_history(self, region: str) -> Self: ...
    def parallel_state(self) -> dict[str, str]: ...

    # Visualization
    def to_mermaid(self) -> str:
        """Emit ``stateDiagram-v2`` text for the configured transitions."""
    def to_dot(self) -> str:
        """Emit Graphviz DOT text (parallel alternative)."""

    # Hooks (override with @override for type-check enforcement)
    @override
    def on_enter(self, state: str, payload: Any) -> None: ...
    @override
    def on_exit(self, state: str, payload: Any) -> None: ...

# ---- Generic variant (PEP 695) ----
from typing import TypeVar
type SchedulerState = Literal[
    "UNINITIALIZED", "INITIALIZED", "SAMPLING", "SAMPLE_EMITTED",
    "FEEDBACK_RECEIVED", "ADJUSTED", "ROUND_TERMINATED", "TERMINATED",
]
type SchedulerEvent = Literal[
    "INIT", "SAMPLE_REQUESTED", "SAMPLE_EMIT", "FEEDBACK_RECEIVED",
    "ADJUST", "RESET", "TERMINATE",
]

class SchedulerStateMachine[S: SchedulerState, E: SchedulerEvent](StateMachine):
    """Scheduler-specific typed state machine."""
    @override
    def send(self, event: E, *, payload: Any = None) -> Self: ...

# ---- Per-family extension mixin (concrete) ----
class EvidenceDrivenStateMachine(SchedulerStateMachine):
    """Adds PID_UPDATING + EPS_PROPAGATED + EPS_FLOORED sub-states."""
    ...

# ---- Orchestrator state machine ----
class RunnerStateMachine:
    """ReInferenceRunner orchestrator machine (14 states; outer + inner)."""
    ...
```

### Key properties
- **Generic typing:** `SchedulerStateMachine[S, E]` enforces literal state/event vocab.
- **HSM support:** `Sub("FEEDBACK_RECEIVED", "PID_UPDATING")` + LCA resolution in `send()`.
- **History states:** `enter_history("FEEDBACK_RECEIVED")` restores last sub-state.
- **Visualization:** `to_mermaid()` walks `transitions` table and emits `stateDiagram-v2`.
- **Async support:** `asend()` for `async on_enter` / guards; uses `asyncio.iscoroutine` detection.
- **Backward compat:** zero-impact on existing `SchedulerProtocol` — `StateMachine` is a *wrapper*, not a replacement.

### Library LOC budget
- core (`StateMachine` + `Transition`): ~150 LOC
- generic + visualization: ~50 LOC
- per-family mixins: ~30 LOC each (lazy-registered on first import)
- total target: ~300 LOC (slightly above the 100-200 LOC survey estimate because of per-family mixins)

---

## Section 7: Integration plan

### Strategy: WRAP, do not replace
The library is a thin wrapper around the existing `SchedulerProtocol` methods. It observes — it does not mutate — the scheduler's `sample()` / `record_round_feedback()` / `reset()` calls. This keeps backward compatibility by construction.

### Per-scheduler integration
| Scheduler | Wrap mode | Notes |
|-----------|-----------|-------|
| CosineAnneal, Constant, Linear, Exponential, Polynomial, Sigmoid, JitteredConstant | mixin (5 LOC; zero behavioural impact) | no-op `record_round_feedback` ⇒ ADJUSTED is unreachable |
| ConvergenceAdaptive | mixin (10 LOC; PID_WARMING / PID_UPDATING) | transitions become typed via `Transition("FEEDBACK_RECEIVED", "ADJUSTED", guard=_w2_history_ready)` |
| CodimensionSheet | mixin (12 LOC; EVIDENCE_COMPUTED) | transitions: `SAMPLING -> EVIDENCE_COMPUTED -> SAMPLE_EMITTED` |
| EvidenceDriven | mixin (15 LOC; PID_UPDATING / EPS_PROPAGATED / EPS_FLOORED) | full Loop 2 closure path |
| FreeTraj | mixin (10 LOC; TRAJECTORY_UPDATED / SUBSTEP_COMPUTED) | |
| EDM | mixin (10 LOC; ADAPTIVE_WARMING / SIGMA_ADAPTING) | only when `adaptive_sigma_max=True`; else 4.1 |
| AdaptivePID | mixin (15 LOC; PID_WARMING / PID_UPDATING / INTEGRAL_ACCUMULATING) | multi-metric PID path |
| MultiChannelJittered | mixin (8 LOC; CHANNEL_RESOLVED) | |
| Sequential | mixin (15 LOC; SLOT_ACTIVE / FALLBACK_EMITTED) | sub-scheduler forwarding |
| HandoffSequential | mixin (5 LOC; HANDOFF_BLENDING) | inherits Sequential's mixin |
| `ReInferenceRunner` | full replace of `run()` body with `RunnerStateMachine` (30 LOC) | adds per-round inner machine; keeps public API byte-identical |

### Backward compatibility
- Existing tests: 100% preserved. The state machine is a *wrapper*; `sample()`, `record_round_feedback()`, `reset()`, etc. continue to behave byte-for-byte identically.
- The 4 feedback loops become **explicit typed transitions** (no behavioural change; just visibility):
  - Loop 1: `Transition("METRICS_PROMOTED", "FEEDBACK_DISPATCHED", effect=scheduler.record_round_feedback)`
  - Loop 2: same path, with the metric dict carrying `paper_quantity_diagnostics`
  - Loop 3: driver-side; the orchestrator's `POLICY_MERGED` inner state consumes `prior_endpoint_digest`
  - Loop 4: `Transition("ENGINE_DISPATCHED", "NOISE_INJECTED", effect=scheduler.inject_noise)`
- `config_hash()` byte-identical for every scheduler (state machine is out-of-band).
- `to_config()` / `from_config()` round-trip is untouched.

---

## Section 8: Test plan

### Per-scheduler tests (one per state transition × 16 schedulers + 1 per guard)

#### Common-state tests (run for every scheduler)
- `test_<name>_state_init`: `INIT -> INITIALIZED` on construction.
- `test_<name>_state_sample_requested`: `INITIALIZED -> SAMPLING` on `sample()`.
- `test_<name>_state_sample_emit`: `SAMPLING -> SAMPLE_EMITTED` post-sample.
- `test_<name>_state_reset`: `ANY -> INITIALIZED` on `reset()`.
- `test_<name>_state_terminate`: `ROUND_TERMINATED -> TERMINATED` on out-of-range `sample()`.
- `test_<name>_invalid_transition`: e.g. `INITIALIZED -> ADJUSTED` raises `InvalidTransitionError`.

#### Per-scheduler extension tests
- `test_convergence_adaptive_pid_warming_to_updating`: first feedback → `PID_WARMING`; second feedback → `PID_UPDATING`.
- `test_codimension_sheet_evidence_computed`: after `sample()` → `EVIDENCE_COMPUTED` with `last_evidence_ratio` non-None.
- `test_evidence_driven_eps_propagated`: when `eps_implicit_base` set, after `record_round_feedback()` → `EPS_PROPAGATED`.
- `test_evidence_driven_eps_floored`: in `sample()` → `EPS_FLOORED` with `eps_implicit >= 1e-6`.
- `test_freetraj_substep_computed`: per-round `audit_codes` carries `freetraj_substep_audit`.
- `test_edm_sigma_adapting`: when `adaptive_sigma_max=True`, after 2+ feedbacks → `SIGMA_ADAPTING`.
- `test_adaptive_pid_integral_accumulating`: after `>=integral_window` rounds → `INTEGRAL_ACCUMULATING`.
- `test_multi_channel_jittered_channel_resolved`: per-channel `audit_codes` carries `per_channel_n_cap:`.
- `test_sequential_slot_active`: round `r` resolves to slot `i` where `sum(n_rounds[:i+1]) > r`.
- `test_sequential_fallback_emitted`: when `computed_at_round >= total_rounds`, `_audit_codes` carries `seq_inject_noise_fallback`.
- `test_handoff_sequential_blending`: round in handoff window → `HANDOFF_BLENDING` with `alpha in (0, 1)`.

#### Per-guard tests
- `test_cycle_length_valid_guard`: round_in_cycle out of range → `InvalidTransitionError`.
- `test_metrics_finite_guard`: NaN W2 in feedback → no transition (no-op; matches existing behaviour).
- `test_target_round_in_range_guard`: negative target_round → `ValueError`.
- `test_cooldown_complete_guard`: ConvergenceAdaptive after 1 feedback stays in `PID_WARMING`; after 2 → `PID_UPDATING`.

#### Integration tests
- `test_reinference_runner_full_run`: full 11-step loop, 5 rounds; final state = `COMPLETE`; ledger chain verified.
- `test_reinference_runner_ledger_integrity_guard`: tampering with a row → `AssertionError("ledger_chain_integrity_check_failed:...")`.
- `test_reinference_runner_invalid_transition`: calling `run()` twice without reset → `InvalidTransitionError`.

#### Visualization tests
- `test_state_machine_to_mermaid`: `to_mermaid()` returns non-empty `stateDiagram-v2` text containing every transition.
- `test_state_machine_to_dot`: `to_dot()` returns valid Graphviz DOT.

#### Byte-determinism tests
- `test_scheduler_byte_determinism`: two `CosineAnnealScheduler` instances with the same config produce identical samples and `config_hash()` (already tested; state-machine layer must not perturb).
- `test_reinference_runner_byte_determinism`: same seed + same config → same `per_round_metrics`.

**Total test count estimate:** ~150 tests (16 schedulers × ~6 common tests + ~10 per-scheduler extension tests + ~4 guard tests + ~3 integration tests + ~2 viz tests).

---

## Section 9: Verification plan

### Selection-ratio preservation (paper Theorem 1)
- Run canonical ablation: `CosineAnnealScheduler` with `profile_residual_fn=...`, `n_rounds=20`, evaluator = `PosteriorSelectionEvaluator`. Capture `selection_ratio` trajectory.
- Confirm: `selection_ratio[-1] > selection_ratio[0]` and trend toward 1.
- Confirm: byte-identical to pre-state-machine run (the wrapper is observation-only).
- Test: `test_evidence_driven_selection_ratio_trend` + `test_codimension_sheet_selection_ratio_trend`.

### Gate preservation (all 6 gates)
| Gate | Verification |
|------|--------------|
| Gate 1 — byte-deterministic | compare `selection_ratio` trajectory + `config_hash()` + `per_round_metrics` byte-by-byte against pre-state-machine baseline |
| Gate 2 — paper Theorem 1 (ratio → 1) | `selection_ratio[-1] - selection_ratio[0] > 0` |
| Gate 3 — 4 feedback loops wired | unit tests for each loop (Section 8) |
| Gate 4 — fail-closed | `test_reinference_runner_ledger_integrity_guard` + `test_invalid_transition` |
| Gate 5 — provenance | `algorithm_signatures` unchanged byte-for-byte |
| Gate 6 — audit trail byte-exact | `merge_audit_codes` and `schedule_audit_codes` byte-identical |

### State-machine log byte-determinism
- Every `send()` / `asend()` emits a `(timestamp, event, source_state, target_state, guard_result)` line via the `state_machine.log` channel.
- Two `RunnerStateMachine` instances driven by the same sequence of events (same payload) produce byte-identical logs (timestamps in monotonic counter form, not wall-clock).
- Test: `test_state_machine_log_byte_determinism`.

### Non-regression
- Existing test suite (`tests/`) must pass without modification.
- Coverage: state-machine code paths exercised by `test_state_machine_*` set; existing tests stay green via the wrap-only integration.

---

## Section 10: Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | **Module cycle when registering per-family mixins** — already a documented risk for the scheduler registry (see `_register_extra_scheduler_families` docstring, `_core.py:3071`). State-machine mixins would deepen the cycle. | High | Lazy registration on first `StateMachine.for_scheduler(scheduler_instance)` call (mirrors the existing `_ensure_extra_families_registered()` pattern). |
| 2 | **PID controller integral accumulator drift** — wrapping `_PIDLiteController.step` in a state-machine transition could perturb float ordering if not careful. | High | Wrap-only; do not reorder operations. Add byte-equity test against pre-state-machine baseline. |
| 3 | **HSM LCA resolution overhead** — `ConvergenceAdaptiveScheduler` chains base + adaptive; if the state machine treats them as nested HSM, LCA resolution could perturb ordering. | Medium | Document that scheduler mixins are *flat* (not nested); HSM is available for future use only. |
| 4 | **`to_mermaid()` Mermaid syntax drift** — Mermaid `stateDiagram-v2` is stable but sub-state syntax differs across renderers. | Low | Pin to v2.5.1 syntax; emit a smoke-test Mermaid in CI. |
| 5 | **14 schedulers + 1 orchestrator ≈ 14+1 mixins** — 30 LOC × 15 = 450 LOC of mixin code, plus 150 tests ≈ 600 LOC new code. | Medium | Per-family mixins are short and templated; consider a `@register_state_machine("family_name")` decorator that auto-generates from the scheduler's introspection. |
| 6 | **`async def on_enter` introduces event-loop coupling** — the runner is currently sync. | Medium | Phase 1 ships sync-only; async variants land in a follow-up. State machine supports both via `send()` / `asend()` so the framework is forward-compatible. |
| 7 | **`Literal` state vocab gets wide** — SchedulerState + 18 extension states = ~26 literal strings. mypy --strict may slow down. | Low | Group per-family via `type ConvergenceAdaptiveState = Literal[...]` aliases; PEP 695 `type` statement makes this ergonomic. |
| 8 | **`runner.py` is 1043 LOC** — the orchestrator state machine targets the `run()` method (lines 488-959 ≈ 471 LOC). Adding 30 LOC for the state machine is fine; rewriting the method is dangerous. | Medium | **Replace** the per-round body with `RunnerStateMachine.send()` calls but keep the *outer* loop in `run()`. This is "wrap the per-round body, not the loop" — same wrap-only philosophy. |
| 9 | **`assert_never` exhaustiveness on per-family state extensions** — adding a new state to one scheduler may not raise mypy errors on others. | Low | Each scheduler gets its own `type <Name>State = Literal[...]` alias; `assert_never(state)` is local to each scheduler. |
| 10 | **Visualization graph size** — CodimensionSheet at 10 transitions × AdaptivePID at 13 transitions = 41-node Mermaid graph; harder to read. | Low | Per-scheduler `to_mermaid()`; orchestrator's `to_mermaid()` is separate. Aggregate `to_mermaid(per_family=True)` for documentation. |

---

## 11-line summary

```
Total scheduler classes found:                         16 (14 distinct; ConvergenceAdaptive/EDM/JitteredConstant/AdaptivePID + paper-grounded CodimensionSheet + EvidenceDriven + FreeTraj + 6 trivial baselines + Sequential + HandoffSequential)
Common state vocabulary:                               UNINITIALIZED / INITIALIZED / SAMPLING / SAMPLE_EMITTED / FEEDBACK_RECEIVED / ADJUSTED / ROUND_TERMINATED / TERMINATED
Common event vocabulary:                               INIT / SAMPLE_REQUESTED / SAMPLE_EMIT / FEEDBACK_RECEIVED / ADJUST / RESET / TERMINATE
Per-scheduler state extensions:                        18 across 16 schedulers (PID_WARMING, PID_UPDATING, EVIDENCE_COMPUTED, PROFILE_BOUND, EPS_PROPAGATED, EPS_FLOORED, TRAJECTORY_UPDATED, SUBSTEP_COMPUTED, ADAPTIVE_WARMING, SIGMA_ADAPTING, INTEGRAL_ACCUMULATING, CHANNEL_RESOLVED, SLOT_ACTIVE, FALLBACK_EMITTED, HANDOFF_BLENDING, ...)
Orchestrator states × transitions:                     outer 6 states × 9 transitions; inner 8 states × 8 transitions; combined 14 states × 17 transitions
Recommended library API shape:                         PEP 695 generic StateMachine[S, E] + Transition dataclass + Self-returning send() + to_mermaid() + assert_never exhaustiveness; ~150 LOC core + 30 LOC per-family mixin
Backward-compat approach:                              WRAP (never replace); state machine is observation-only; existing SchedulerProtocol surface unchanged; to_config/from_config byte-identical
Total transitions across all state machines:           127 scheduler transitions + 17 orchestrator transitions = 144 transitions total
Estimated implementation effort:                       ~32-40 hours (15 mixins × 1.5h + 300 LOC core × 4h + 150 tests × 0.15h + integration 4h + verification 4h)
Biggest design risk:                                   Module-load cycle when registering per-family mixins (mirrors existing scheduler-registry cycle); mitigation = lazy registration on first for_scheduler() call
Plan file path:                                        c:\Users\31472\codes\flowa-multistep-reinference\docs\r4-survey\02-universal-statemachine-plan.md
```
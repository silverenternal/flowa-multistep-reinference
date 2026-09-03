# 03 — Coupling / Collaboration Inventory

Survey of how the algorithm layer (`adaptive_reflow/algorithm/`) is decoupled
from the framework layer (`adaptive_reflow/frame/`, `adaptive_reflow/eval/`,
`adaptive_reflow/contracts/`, `adaptive_reflow/universal/`, adapters), where
that boundary leaks, and which emergent behaviours only exist when the pieces
work together.

Files audited:

- `adaptive_reflow/algorithm/__init__.py`
- `adaptive_reflow/algorithm/{scheduler,blender,merge_operator,policy_driver,runner,scheduler_extra,scheduler_r2,round2_extra,batched_runner,evidence_driver,sequential}.py`
- `adaptive_reflow/frame/{engine,orchestrator,ledger_chain}.py`
- `adaptive_reflow/contracts/paper_quantities.py`
- `adaptive_reflow/diagnostics/ledger.py`
- `adaptive_reflow/adapters/twodim_fm.py`
- `README.md` (§ "The four feedback loops")
- `docs/r3-survey/01-architecture.md`, `02-algorithms.md` (referenced)

---

## 1. Decoupling Mechanisms

### 1.1 Protocols (structural types)

All four algorithm roles are governed by `runtime_checkable` Protocols; the
framework depends only on the Protocol, never on the concrete class.

| Protocol | Where declared | Method surface the framework depends on |
|---|---|---|
| `SchedulerProtocol` | `algorithm/scheduler.py:154-259` | `sample`, `cycle_length`, `schedule_family`, `config_hash`, `reset`, optional `record_round_feedback`, `inject_noise`, `to_config`/`from_config` |
| `ScheduleSampleProtocol` | `algorithm/scheduler.py:136-151` | structural type for `ScheduleSample` (no behaviour) |
| `PolicyDriverProtocol` | `algorithm/policy_driver.py:180-284` | `compute_policy`, `driver_family`, `config_hash`, `to_config`/`from_config` |
| `MergeOperatorProtocol` | `algorithm/merge_operator.py:239-351` | single `merge(prev, dynamic, *, cap, floor, delta_cap_up, delta_cap_down, audit_codes)` |
| `RestartBlenderProtocol` | `algorithm/blender.py:403-441` | `blender_family`, `config_hash` (the framework never calls `blend()` through this Protocol) |

The engine never imports any concrete scheduler / driver / merge operator
class; it only knows about the dataclasses (`FinalRestartPolicy`,
`ScheduleSample`, `StateBundle`) and the per-round helper
`_policy_with_schedule_beta` (`frame/engine.py:770-843`) which itself only
reads `policy.schedule_sample` and `policy.beta_from_schedule`.

### 1.2 Registries

Family-keyed registries enable polymorphic construction by `family` string
without coupling to concrete implementations.

| Registry | Location | Purpose |
|---|---|---|
| `SCHEDULER_REGISTRY` | `algorithm/scheduler.py:106` + `scheduler_r2.py` + `scheduler_extra.py` | `build_scheduler_from_config` (`algorithm/protocol_registry.py`) |
| `BLENDER_FAMILIES` | `algorithm/protocol_registry.py:68-71` | `build_blender_from_config` |
| `MERGE_OPERATOR_FAMILIES` | `algorithm/protocol_registry.py:72-76` | `build_merge_operator_from_config` |
| `POLICY_DRIVER_FAMILIES` | `algorithm/protocol_registry.py:77-80` | `build_policy_driver_from_config` |
| `ROTATION_POLICY_REGISTRY` | `algorithm/rotation_policy.py:83` | `build_rotation_policy` |
| `RUNNER_REGISTRY` | `algorithm/runner_registry.py:96` | `build_runner` for runner families (batched/parallel/early-stop/online) |
| `PROTOCOL_REGISTRY` | `algorithm/protocol_registry.py:74` | aggregate dispatch with `validate_config_schema` |

The `to_config()` / `from_config()` round-trip is enforced on every
implementation (`scheduler.py:451-486`, `merge_operator.py:445-489`,
`policy_driver.py:386-401` / `488-497` / `727-750`, `blender.py:529-538` /
`653-666`) so a schedule / driver / operator can be serialised byte-for-byte
and rebuilt without coupling the wire format to the class identity
(closes P1-1).

### 1.3 Type Contracts (frozen dataclasses + NewTypes)

`adaptive_reflow/contracts/` carries the *vocabulary* the framework and
algorithm layer must share, never the behaviour:

- `ScheduleSample` (algorithm) → `CosineScheduleSample` (contracts) via
  `ScheduleSample.as_cosine_schedule_sample` (`scheduler.py:115-128`)
- `FactorValue`, `ArtifactHash`, `ChannelName`, `LedgerRowId`, `MechanismId`,
  `PolicyId`, `RunId`, `RestartTriggerCode`
- `FinalRestartPolicy` (frozen, has `policy_hash = hash_policy_hash(policy)`)
  invariant; recomputed by `_override_beta_by_channel` and the engine.

### 1.4 Capability Handshake (engine ↔ adapter)

`Engine.handshake` (`frame/engine.py:896-936`) calls
`adapter.capabilities()` and rejects adapters that lack any of the 8
required capability flags (`has_ode_integration_surface`, etc). This is the
**engine ↔ adapter** boundary; the engine never introspects adapter state
beyond the declared surface. ONNX-Runtime-style per-op capability dispatch
re-check happens at `frame/engine.py:1283-1295` and
`_check_capabilities_advertise_dispatch` (`engine.py:660-?`).

### 1.5 Are these sufficient?

The Protocols + registries + type contracts cleanly separate:

- **Scheduler** ↔ driver (driver receives `schedule_sample`, ignores it for
  constant/adaptive families — `policy_driver.py:347`, `466`, `672`).
- **Driver** ↔ merge operator (driver returns `FinalRestartPolicy`; merge
  operator accepts numeric `dynamic` via `applied_policy.beta_by_channel`,
  runner.py:609-619).
- **Merge** ↔ blender (kept formally decoupled; merge operates on numerics,
  blender operates on `prior_state`/`fresh_state` carrying arbitrary
  carriers).

However the **sufficiency test fails** in two places (see §2 and §6):

- The `RestartBlenderProtocol` is declared but **not wired into the data
  path** — adapters inline `_blend_endpoint_with_prior`
  (`adapters/twodim_fm.py:364-373`) instead of delegating to `self._blender`.
- `AdaptiveReflowPolicyOrchestrator.merge_fraction_authority`
  (`frame/orchestrator.py:966-1081`) calls the legacy free function
  `bounded_merge` (re-export of `frame/merge.py`) rather than the canonical
  `MergeOperatorProtocol.merge` — so the orchestrator bypasses the Protocol.

---

## 2. Coupling Mechanisms (where algorithms do touch framework state)

### 2.1 Data flow paths

Per round (runner.py:574-832), the canonical pipeline is:

```
[outer] scheduler.sample                (runner.py:575-577)
       └→ ScheduleSample .as_cosine_schedule_sample()  (runner.py:579)
[outer] driver.compute_policy(schedule_sample, base_policy,
                               channel, prior_endpoint_digest)
       └→ FinalRestartPolicy w/ driver_computed_beta=True
[outer] _merge.merge(prev=prev_beta, dynamic=beta,
                     cap=sample.n_cap, floor=sample.n_min,
                     delta_cap_up/down=1.0, audit_codes)
       └→ merged_beta    (runner.py:609-619)
[outer] applied_policy.beta_by_channel = {ch: merged_beta}    (runner.py:625-637)
[outer] scheduler.inject_noise(prior_array, schedule_sample,
                               generator=forward_noise_generator)
       └→ "FORWARD_NOISE_INJECTED" audit code   (runner.py:668-674)
[outer] engine.run_round(round_index=r, phase_state, bundle, adapter,
                          policy=applied_policy, condition_delta,
                          seed, prev_ledger_row_hash)
       └→ EngineRoundResult(round_trace, ledger_row, next_phase_state)
[outer] adapter.export_trajectory(trace.integrator_trace)
       └→ endpoints[r]   (runner.py:710-720)
[outer] evaluator.oracle(bundle, channel, seed)     (runner.py:780-790)
[outer] selection_evaluator.oracle(bundle, ...)    (runner.py:796-801)
[outer] scheduler.record_round_feedback(r, metric) (runner.py:820-821)
[outer] adapter.observe_endpoint(trace.integrator_trace, bundle)
       └→ next bundle    (runner.py:828-830)
```

Then `verify_ledger_chain(tuple(ledger_rows))` runs once at the end
(runner.py:839-843); failure raises `AssertionError`.

The engine itself (`frame/engine.py:1016-1659`) is the inner protocol
surface driver: `build_initial_state` → `apply_restart_distribution` →
`compose_condition` → `solve_ode` → `observe_endpoint` → `export_endpoint` →
`detach_and_validate_endpoint`. Each step is wrapped in
`_safe_adapter_call` (`engine.py:730-?`) that fail-closes to a
non-raising `_emit_fail_closed` round.

### 2.2 Audit-code emission sites

| Site | Emitter | Codes | Read by |
|---|---|---|---|
| `runner.py:729` | runner | `FORWARD_NOISE_INJECTED` | per-round `metric["merge_audit_codes"]` |
| `runner.py:755` | runner | (relays `merge.merge` audit list) | per-round `metric["merge_audit_codes"]` |
| `engine.py:1142/1146` | engine | `ERR_FEATURE_DISABLED` | `RoundTrace.audit_codes` + `LedgerRow.audit_codes` |
| `engine.py:1217-1224` | engine | `ERR_CAPABILITIES_INVALID` | same |
| `engine.py:1228-1232` | engine | `ERR_BUNDLE_INVALID` | same |
| `engine.py:1238-1247` | engine | `ERR_CHANNEL_UNSUPPORTED`, `ERR_CAPABILITY_UNSUPPORTED` | same |
| `engine.py:812-813` | engine (`_policy_with_schedule_beta`) | `ERR_SCHEDULE_SAMPLE_MISSING` | same |
| `engine.py:830-835` | engine | `ERR_ADAPTER_CONFIGURATION_ERROR` | same |
| `merge_operator.py:521-541` | merge | `MERGE_NONFINITE_PREV_CLIPPED`, `MERGE_NONFINITE_DYNAMIC_CLIPPED`, `MERGE_CAP_OUT_OF_RANGE`, `MERGE_FLOOR_OUT_OF_RANGE` | runner passes list into `metric["merge_audit_codes"]` |
| `merge_operator.py:550-559` | merge | `MERGE_PAPER_QUANTITY_FLOOR_LIFTED` | same |
| `merge_operator.py:599-604` | merge | `MERGE_DEGENERATE_INTERVAL` | same |
| `blender.py:131-141` | blender | `BLENDER_MEMORY_FRACTION_CLIPPED` | (currently never reaches the runner — see §6.1) |
| `policy_driver.py:364` | driver | `POLICY_SCHEDULE_DERIVED` | driver `audit_codes` argument (runner doesn't forward) |
| `policy_driver.py:697-699` | driver | `BETA_SATURATION_FROM_PAPER_QUANTITY` | same |
| `scheduler.py:362-366` | scheduler | `cosine_paper_quantity_wired:A_g=…` | runner fans into `metric["schedule_audit_codes"]` (runner.py:773-775) |
| `scheduler.py:1941-1948` | scheduler (adaptive) | `schedule_feedback_multi_metric:…` | same |

The fan-out is asymmetric: scheduler codes reach the runner audit trail
(`runner.py:773-778`), but driver codes do **not** (the runner never passes
its `merge_audit` list into `driver.compute_policy` — see `runner.py:585-590`).

### 2.3 Ledger integration points

| File:line | What |
|---|---|
| `frame/engine.py:404-438` | `compute_ledger_row_hash(...)` — single hashing rule |
| `frame/engine.py:441-488` | `build_ledger_row(...)` — round-level row, includes `prev_ledger_row_hash` |
| `frame/engine.py:491-?` | `verify_ledger_chain(...)` — full-chain re-walk |
| `frame/ledger_chain.py:96-?` | `LedgerChain.append` — incremental `O(1)` per-row check (delegates to engine's `compute_ledger_row_hash`) |
| `algorithm/runner.py:572, 685, 693` | runner carries `prev_ledger_row_hash` across rounds |
| `algorithm/runner.py:839-843` | runner calls `verify_ledger_chain` on the final tuple; raises `AssertionError` on tamper |
| `algorithm/runner.py:857` | `ReInferenceResult.ledger_rows` exposes the chain as an immutable tuple |

### 2.4 Metric consumption points

| Metric | Consumed at | Effect |
|---|---|---|
| `W2` (from `oracle["raw_score"]`) | `runner.py:785-787` (promotion) → `metric["W2"]` → `scheduler.record_round_feedback(r, metric)` (runner.py:820-821) | `ConvergenceAdaptiveScheduler.record_round_feedback` aggregates via `metric_weights`, updates EMA, PID-lite shift (scheduler.py:2028-2113) |
| `coverage` (from `oracle["bounded_score"]`) | `runner.py:788-790` → `metric["coverage"]` → feedback | folded in via `1 - value` in PID (scheduler.py:2069) |
| `selection_ratio` | `runner.py:795-801` → `metric["selection_ratio"]` | **NOT** fed to any algorithm; observation only |
| `schedule_evidence_ratio` (from `sample.evidence_ratio`) | `runner.py:776-778` → `metric["schedule_evidence_ratio"]` | **NOT** fed to any algorithm; observation only |
| `paper_quantity_diagnostics` | `runner.py:808-813` → `metric["paper_quantity_diagnostics"]` | **NOT** fed to any algorithm; observation only |
| `driver.beta_saturation_count` | (`policy_driver.py:613-625`) | per-instance counter; runner never resets it (so it grows across cycles) |

The metrics actually closing a feedback loop are *only* `W2` and
`coverage` (and only `W2` in legacy single-metric mode). The other three are
observation-only diagnostic emissions — see §6.5.

### 2.5 `scheduler.record_round_feedback` callers

The runner is the **single** caller in production code, via `hasattr` to
preserve compatibility with non-adaptive schedulers:

```
runner.py:820-821        ReInferenceRunner.run loop        (runner-driven loop)
batched_runner.py:884-886 BatchedTrajectoryRunner.run        (batched runner)
```

The remaining references are definition sites
(`scheduler.py:201`, `scheduler.py:411`, `687`, `894`, `1121`, `1357`,
`1609`, `2028`, `2775`; `scheduler_extra.py:280`, `624`, `954`, `1196`;
`scheduler_r2.py:220`; `round2_extra.py:189`; `evidence_driver.py:209-215`
[proxy wrapper]; `sequential.py:314`, `326`, `362`
[slot-aware wrapper]) — every default implementation is a no-op
(`scheduler.py:411-417` for cosine), so the hook is effectively only
honoured by `ConvergenceAdaptiveScheduler` and `AdaptivePIDScheduler`.

### 2.6 `paper_quantities` consumers

The four paper quantities (`contracts/paper_quantities.py:71, 142, 233,
278`) are consumed by:

- `CosineAnnealScheduler.__init__` → caches `sheet_A` when a
  `profile_residual_fn` is supplied (`scheduler.py:317-321`).
- `CodimensionSheetScheduler.__init__` → caches all four (`scheduler.py:2472-2477`).
- `_paper_evidence_balance` helper (`scheduler.py:2133-2253`) — closed-form
  sheet-vs-cell ratio using literal `A_g`, `B_g`, `C_g`.
- `BoundedMergeOperator.__init__` (via `exterior_gap_e_rho` kwarg,
  `merge_operator.py:394-428`) and `merge_operator_extra.py:96-112` — lifts
  `floor` to `max(floor, e_rho/4)`.
- `AdaptivePolicyDriver.__init__` (via `per_cell_coefficient_C`,
  `policy_driver.py:566-585`) — divides envelope by `C_g`.
- `ReInferenceRunner._apply_paper_quantities_rewiring`
  (`runner.py:861-918`) — computes all four once and rewires the scheduler
  / driver in place.

Consumers that **do not** read `paper_quantities` (despite being downstream
of the same data):

- `frame/engine.py` — engine never imports the module.
- `frame/orchestrator.py` — orchestrator never imports the module (verified
  by grep; zero matches).
- `frame/ledger_chain.py` — no consumption.
- `diagnostics/ledger.py` — no consumption.

---

## 3. Feedback Loop Implementations

The README (`README.md:86-93`) declares four loops. Each is traced here
with exact `file:line` end-points and a verdict on whether data flows back
to the source.

### Loop 1 — Self-reflexive (scheduler reads its own last-round output)

```
Forward: scheduler.sample
         → runner captures W2/coverage in metric (runner.py:785-790)
         → ConvergenceAdaptiveScheduler.record_round_feedback
           aggregates via metric_weights, updates EMA, PID-lite shift
           (scheduler.py:2054-2113)
         → next round scheduler.sample reads self._shift (scheduler.py:1905-1919)
Backward: ✅ closed (data flows back to u_r via the shift)
```

**End-points:**
- Producer: `runner.py:780-790` (oracle → metric)
- Consumer: `scheduler.py:2028-2113` (`record_round_feedback`)
- Re-entry: `scheduler.py:1895-1919` (`sample` reads `_shift`)
- Audit code: `schedule_shift_applied:{shift:+.6f}` (scheduler.py:1939),
  `schedule_feedback_multi_metric:…` (scheduler.py:1943)

**Verdict:** ✅ Closed — but the **driver and merge operator do not see
this signal**. `AdaptivePolicyDriver` reads `prior_endpoint_digest` only
(runner.py:589; policy_driver.py:673) — never the feedback metric. The
merge operator sees `prev_beta` only (runner.py:610). So the loop is
**single-ended**: only the scheduler is reflexive; the driver / merge are
not.

### Loop 2 — Theory-grounded (paper_quantities → algorithm)

```
Forward: paper_quantities.{A_g, B_g, C_g, e_rho}
         → CodimensionSheetScheduler caches at __init__ (scheduler.py:2472-2477)
         → _paper_evidence_balance per round (scheduler.py:2133-2253)
         → sample.evidence_ratio exposed via audit_codes (scheduler.py:1948? — via audit_codes tuple)
         → runner records metric["schedule_evidence_ratio"] (runner.py:776-778)
Backward: ❌ not closed — selection_ratio / evidence_ratio never feeds
          back into scheduler, driver, or merge at runtime.
```

**End-points:**
- Producer: `contracts/paper_quantities.py:71, 142, 233, 278`
- Consumer: `scheduler.py:2472-2477`, `policy_driver.py:566-585`,
  `merge_operator.py:401-428`
- Auditor: `runner.py:808-813`
- Re-entry: **none** — `selection_ratio` is observation-only;
  `evidence_ratio` is observation-only

**Verdict:** ❌ Half-closed — paper quantities *configure* the algorithms
once at construction time, but no per-round paper quantity flows back
into the algorithm; the value sits in the metric dict and is never
consumed.

### Loop 3 — Hash-chained integrity

```
Forward: build_ledger_row(prev_ledger_row_hash) (engine.py:441-488)
         → runner carries prev_ledger_row_hash across rounds (runner.py:572, 685, 693)
         → verify_ledger_chain at run end (runner.py:839-843)
Backward: ✅ closed — each round's row_hash contains prev's row_hash;
          tamper anywhere breaks recompute at verify time.
```

**End-points:**
- Producer: `frame/engine.py:441-488` (`build_ledger_row`)
- Chainer: `frame/engine.py:404-438` (`compute_ledger_row_hash`)
- Carriers: `algorithm/runner.py:572, 685, 693`
- Verifier: `frame/engine.py:491-?` (`verify_ledger_chain`); incremental
  alternative `frame/ledger_chain.py:111-216` (`LedgerChain.append`)

**Verdict:** ✅ Closed — this is the load-bearing invariant; P0-8.

### Loop 4 — Symmetric round (forward inject_noise ↔ reverse blend)

```
Forward: scheduler.inject_noise(state, schedule_sample, generator)
         (runner.py:668-674)
         → forward_noise_emitted=True → FORWARD_NOISE_INJECTED in
           merge_audit (runner.py:729)
         → metric["forward_noise_injected"] = 1.0 (runner.py:767)
Backward (reverse side): adapter.apply_restart_distribution inlines
         _blend_endpoint_with_prior (adapters/twodim_fm.py:364-373, 696-758);
         this is the *reverse* of inject_noise, but the math is duplicated
         rather than delegated to RestartBlenderProtocol.
         → engine.run_round calls apply_restart_distribution (engine.py:1438-1444)
Backward (closed form): ❌ NOT closed via the Protocol; blender is
         bypassed at the adapter boundary; the forward noise is discarded
         after the audit-code emission (runner.py:673: `_ = injected`).
```

**End-points:**
- Producer: `algorithm/scheduler.py:217-238` (Protocol); per-implementation
  at `scheduler.py:419-449`, `695-712`, `902-921`, `1129-1143`,
  `1365-1379`, `1617-1631`, `1974-1989`
- Caller: `algorithm/runner.py:668-674`
- Reverse side caller: `frame/engine.py:1438-1444` →
  `adapter.apply_restart_distribution` (inlined math, not Protocol call)

**Verdict:** ❌ **Asymmetric / half-closed.** The forward side reaches the
Protocol; the reverse side is inlined inside each adapter. The runner
*receives* the injected noise as `_ = injected` and immediately drops it
(runner.py:673). There is no `self._blender` reach-around; the
`RestartBlenderProtocol` is consulted only for its `config_hash()`
(runner.py:374 / `_algorithm_signatures`).

---

## 4. Cross-Algorithm Interactions

The runner composes four protocols; the joints between them are:

| Joint | Producer | Consumer | Joint file:line | Direction | Symmetric? |
|---|---|---|---|---|---|
| schedule → driver | `SchedulerProtocol.sample` | `PolicyDriverProtocol.compute_policy(schedule_sample, ...)` | `algorithm/runner.py:575-585` | → | No (driver ignores schedule for constant / adaptive) |
| driver → merge | `PolicyDriverProtocol.compute_policy` → `FinalRestartPolicy.beta_by_channel[ch]` | `MergeOperatorProtocol.merge(prev, dynamic=beta, ...)` | `algorithm/runner.py:585-619` | → | No (merge ignores schedule_sample unless EMAOperator) |
| merge → engine | merged `beta` is patched back into `FinalRestartPolicy.beta_by_channel` | `Engine.run_round(policy=applied_policy, ...)` | `algorithm/runner.py:625-685` | → | No (driver `compute_policy` is not re-invoked) |
| engine → adapter | engine forwards `FinalRestartPolicy` to `adapter.apply_restart_distribution(state, policy)` | adapter returns `StateBundle` | `frame/engine.py:1428-1444` | → | No (engine never reads adapter state) |
| adapter → evaluator | `adapter.observe_endpoint` → `evaluator.oracle(bundle, ...)` | `metric` dict | `algorithm/runner.py:779-790` | → | No (evaluator never inspects adapter state) |
| evaluator → scheduler | `metric["W2"]`/`coverage` → `scheduler.record_round_feedback(r, metric)` | `ConvergenceAdaptiveScheduler._shift` | `algorithm/runner.py:820-821`; `algorithm/scheduler.py:2028-2113` | ← (closes loop 1) | Yes for that one family |
| scheduler → runner | `scheduler.inject_noise(...)` | runner audit / metric | `algorithm/runner.py:668-674` | → | No (result is discarded: `_ = injected`) |
| runner → orchestrator | `AdaptiveReflowPolicyOrchestrator` lives in `frame/`; the runner does **not** call it (verified: zero matches in runner.py) | n/a | n/a | ❌ **no joint** | n/a |
| runner → paper_quantities | `_apply_paper_quantities_rewiring` re-routes scheduler / driver in place | re-entry | `algorithm/runner.py:861-918` | → (one-shot, pre-loop) | No |

### Asymmetry

- The **only closed loop is Loop 1 (scheduler ↔ metric)** and that closure
  only exists when the user opts into `ConvergenceAdaptiveScheduler`. All
  other joints are one-way.
- The **merge operator → driver** path is one-way. The merge operator
  never informs the driver that its `dynamic` was clipped (only the audit
  codes propagate via `merge_audit_codes`).
- The **scheduler → engine** path: the engine's inline override
  `_policy_with_schedule_beta` (`frame/engine.py:770-843`) duplicates the
  schedule-derived driver's logic. Contract 1.2 dedups via the
  `driver_computed_beta` flag (`policy_driver.py:209-212`, `engine.py:1429`),
  but the engine still owns a second source of truth for the
  `n_cap → beta` mapping.

---

## 5. Emergent Behaviour

Behaviours that only exist when two-or-more algorithms collaborate:

1. **Hash-chained integrity** — single scheduler + single engine + single
   runner, no merge, would not produce a tamper-evident chain. The
   *combination* of `build_ledger_row(prev_hash) → row_hash → recompute` is
   an emergent invariant.
2. **Paper Theorem 1 numerical witness (`selection_ratio → 1`)** — only
   emerges from `paper_quantities.sheet_evidence_A` + `CodimensionSheetScheduler`
   + `PosteriorSelectionEvaluator` + the runner wiring them
   (`runner.py:891-918`, `runner.py:795-801`). Removing any one collapses
   the witness.
3. **Symmetric round model (DRM-3)** — the `inject_noise(state)` forward +
   `apply_restart_distribution(state, policy)` reverse pair
   (`scheduler.py:217-238`, `engine.py:1438-1444`) is byte-replayable only
   because the same `np.random.Generator` state is threaded through both
   sides.
4. **Coarea ratio reporting** — `CodimensionSheetScheduler._paper_evidence_balance`
   + `runner.py:776-778` produces the `evidence_ratio` audit emission that
   no single scheduler alone emits.
5. **`beta_saturation_count` provenance** — only `AdaptivePolicyDriver`
   tracks this counter (`policy_driver.py:613-625`); the runner never
   resets it (`runner.py:585-590` ignores it), so the counter accumulates
   across `n_rounds` but only `AdaptivePolicyDriver` + the runner
   *together* can attribute saturation to a specific per-round metric.
6. **`policy_hash` integrity** — emerges from
   `FinalRestartPolicy` dataclass + `hash_policy_hash` +
   `_override_beta_by_channel` + `_policy_with_schedule_beta` recomputing
   on every mutation. No single piece preserves the invariant.
7. **`schedule_evidence_ratio` in `metric[]`** — only emitted because the
   runner fans `sample.audit_codes` and `sample.evidence_ratio` into the
   per-round metric (runner.py:773-778); without the runner scheduler
   audits never reach the audit ledger.

---

## 6. Collaboration Weaknesses

### 6.1 Blender is declared but never executed through its Protocol

`RestartBlenderProtocol` (`algorithm/blender.py:403-441`) exists, has two
implementations (`LinearBlender`, `DistanceDecayBlender`), and is stored
on `ReInferenceRunner._blender` (runner.py:448-450). The runner uses
it only for `config_hash()` (`runner.py:374`, via `_algorithm_signatures`).

**Adapters' `apply_restart_distribution` inline the same math** rather
than calling the blender:

- `adapters/twodim_fm.py:364-373` — `_blend_endpoint_with_prior` is a
  byte-identical copy of `_linear_blend_arrays` in `algorithm/blender.py:220-238`.
- `adapters/twodim_fm.py:696-758` — `apply_restart_distribution` does
  `memory_fraction = 1 - beta`, calls the inlined helper, never
  `self._blender.blend(...)`.
- `adapters/stochastic_fm.py:256` and `adapters/toy_gaussian.py:308` — same
  inlined pattern (verified via grep).

The blender's `BLENDER_MEMORY_FRACTION_CLIPPED` audit code
(`algorithm/blender.py:131-141`) is therefore **never emitted on the
production data path** — it is observable only through direct blender
tests. The protocol guarantees nothing about runtime behaviour because the
contract's only consumer is a config-hash print.

### 6.2 Orchestrator bypasses `MergeOperatorProtocol`

`frame/orchestrator.py:1073-1080` calls `bounded_merge(...)` — the legacy
free function re-exported from `frame/merge.py` — instead of dispatching
through `MergeOperatorProtocol`. The protocol is therefore only enforced
on the runner-driven path; the orchestrator-driven path (used by
`AdaptiveReflowMechanism`) is decoupled from `MergeOperatorProtocol`
entirely and silently uses the legacy `max(prev, dynamic)`-derived
operator with delta caps pinned at `delta_cap`.

### 6.3 Runner reaches into scheduler private attributes

`algorithm/runner.py:903-907` re-constructs a `CodimensionSheetScheduler`
using private slots:

```python
self._scheduler = CodimensionSheetScheduler(
    cycle_length=int(self._scheduler.cycle_length()),
    n_min=float(self._scheduler._n_min),    # noqa: SLF001
    n_max=float(self._scheduler._n_max),    # noqa: SLF001
    profile_residual_fn=provider,
    eps_implicit=float(self._scheduler._eps_implicit),  # noqa: SLF001
    eps_direction=str(self._scheduler._eps_direction),  # noqa: SLF001
    seed=int(self._scheduler.seed),
)
```

This is a **leak**: a future change to `CodimensionSheetScheduler`'s
constructor that drops `eps_implicit`/`eps_direction` would silently break
paper-quantity rewiring. The `# noqa: SLF001` is an explicit confession.

### 6.4 Two parallel sources of truth for the per-round sample

`ScheduleSample` (algorithm layer, frozen dataclass) carries `n_cap`,
`n_min`, `n_max`, `u_r`, `schedule_hash`, `audit_codes`, `evidence_ratio`.
`CosineScheduleSample` (contracts layer, frozen dataclass) carries
`schedule_hash`, `n_cap`, `n_min`, `n_max`, `u_r`, `family`. The
algorithm sample converts via `.as_cosine_schedule_sample()`
(`scheduler.py:115-128`); every place that consumes a sample in the
runner converts immediately (`runner.py:579`, `586`, `670`).

Two parallel types for the same content increases the surface that has to
stay in sync. Any new field on `ScheduleSample` (e.g.
`schedule_evidence_ratio`) needs to be added to `CosineScheduleSample` and
the converter before the engine can see it.

### 6.5 Driver / merge audit codes do not reach the runner's metric dict

`runner.py:585-590` calls `driver.compute_policy(...)` without passing
an `audit_codes` list, and the driver's `policy_schedule_derived` /
`BETA_SATURATION_FROM_PAPER_QUANTITY` codes are never propagated. Same
for the merge operator — `runner.py:608-619` does collect `merge_audit`
into the metric dict, but the *driver's* codes are dropped. Audit replay
is therefore **incomplete**.

### 6.6 Orchestrator is entirely isolated from the algorithm layer

`frame/orchestrator.py` is the policy orchestrator for
`AdaptiveReflowMechanism`, but it:

- does not import `algorithm/`.
- does not call `paper_quantities.*` (zero matches in grep).
- does not honour `SchedulerProtocol.sample`; it instantiates its own
  `CosineScheduleSampler` (`frame/orchestrator.py:328`).
- does not honour `PolicyDriverProtocol`; `merge_fraction_authority`
  bypasses the merge protocol (§6.2).

The orchestrator is effectively a **parallel framework** inside the
framework. The runner and the orchestrator cannot drive the same round.

### 6.7 Feedback loop is single-family

`record_round_feedback` is honoured only by `ConvergenceAdaptiveScheduler`
(`scheduler.py:2028-2113`) and `AdaptivePIDScheduler`
(`scheduler_extra.py:280, 624, 954, 1196`); the default
`CosineAnnealScheduler.record_round_feedback` is a no-op (`scheduler.py:411-417`).
For any non-adaptive scheduler, the metric dict is built and discarded:
`metric["W2"]` and `metric["coverage"]` go into the per-round dict and
into `ReInferenceResult.per_round_metrics`, but no algorithm consumes
them. Loop 1 therefore exists *only when explicitly opted into*.

### 6.8 `evidence_ratio` and `paper_quantity_diagnostics` are observation-only

`runner.py:776-778` and `runner.py:808-813` record these in the metric
dict but no algorithm reads them. They cannot close Loop 2 — paper
quantities configure once, then become invisible at runtime. To close
Loop 2 the runner would need to dispatch the per-round `evidence_ratio` /
`selection_ratio` into `scheduler.record_round_feedback` (currently only
W2/coverage are forwarded via the runner.py:820-821 call).

### 6.9 `select_evaluator.oracle` and the primary evaluator are asymmetric

`runner.py:779-790` calls `self._evaluator.oracle(...)`; `runner.py:795-801`
calls `config.selection_evaluator.oracle(...)`. They are both fan-out
callers but `selection_evaluator` is a constructor argument while the
primary evaluator is a constructor argument on `ReInferenceRunner.__init__`.
A caller that configures only the primary evaluator gets zero
`selection_ratio` emission; a caller that configures only the secondary
gets no W2/coverage. There is **no aggregation** that ties the two
oracles together.

### 6.10 EMAOperator's optional `schedule_sample` kwarg is dead

`merge_operator.py:786-795` accepts `schedule_sample=None` and modulates
the alpha by `n_cap`. The runner never passes `schedule_sample` into
`merge.merge` (`runner.py:609-619`) — so the schedule-aware modulation
is unreachable from the runner path. The path is reachable only by
direct callers of the merge operator.

### 6.11 `evidence_driver.py` and `sequential.py` are wrappers, not protocol participants

`algorithm/evidence_driver.py:209-217` and
`algorithm/sequential.py:314-392` wrap an inner scheduler; they implement
the `SchedulerProtocol` surface (and `inject_noise` delegates to the
inner scheduler, `sequential.py:392-408`). They are not in the runner's
hot path (verified — runner.py imports none of them), so the wrapper
hierarchy is **unused** by the runner pipeline.

### 6.12 Diagnostics are write-only

`diagnostics/ledger.py` defines `ledger_only=True` dataclasses marked as
"observation only, never influence the beta/alpha write path". Nothing in
the engine, runner, orchestrator, or drivers reads them. They are
dead-letter carriers in the current pipeline (the diagnostics module is
its own sub-package; engine imports `frame/diagnostics/` only via type
names).

---

## 7. Weaknesses (summary)

The collaboration works end-to-end only on the path:

```
paper_quantities → scheduler.sample → driver.compute_policy → merge.merge
                   → engine.run_round → adapter.apply_restart_distribution
                   → adapter.observe_endpoint → evaluator.oracle
                   → scheduler.record_round_feedback  (closes loop 1)
                   → build_ledger_row(prev_hash) → verify_ledger_chain
```

Everything else is broken or asymmetric:

| # | Weakness | Severity | Where |
|---|---|---|---|
| W1 | Blender is declared but never called from the data path | High | `adapters/twodim_fm.py:364-373`, `blender.py:403-441` |
| W2 | Orchestrator bypasses `MergeOperatorProtocol` | High | `frame/orchestrator.py:1073-1080` |
| W3 | Runner reaches into private scheduler attributes for paper-quantity rewiring | High | `algorithm/runner.py:903-907` |
| W4 | Two parallel sample types (`ScheduleSample` vs `CosineScheduleSample`) | Medium | `algorithm/scheduler.py:115-128` |
| W5 | Driver audit codes never reach runner metric dict | Medium | `algorithm/runner.py:585-590` |
| W6 | Orchestrator entirely isolated from algorithm layer | High | `frame/orchestrator.py` (zero imports of `algorithm/`) |
| W7 | Feedback loop only closes for adaptive schedulers | Medium | `algorithm/scheduler.py:411-417` (no-op default) |
| W8 | Loop 2 half-closed: paper quantities never re-enter runtime | High | `algorithm/runner.py:808-813` |
| W9 | EMAOperator's schedule-aware modulation is unreachable | Low | `merge_operator.py:786-795` |
| W10 | Diagnostic ledger is write-only | Low | `diagnostics/ledger.py:1-22` |

The biggest weakness is **W1 (the Blender Protocol leaks but is not
honored at execution time)** — the protocol is declared with a real
implementation family (`DistanceDecayBlender`), with audit codes, with
config-hash provenance, but the data path bypasses it via inlined adapter
math. Until the adapter boundary delegates to `self._blender.blend(...)`,
the algorithm layer's "four pluggable layers" claim is reduced to three.
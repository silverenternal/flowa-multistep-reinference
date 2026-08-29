# 08 — Prioritized FIX PLAN — R3 Survey

**Survey scope:** synthesises
[`01-architecture.md`](01-architecture.md),
[`02-algorithms.md`](02-algorithms.md),
[`03-coupling.md`](03-coupling.md),
[`04-counterintuitive-findings.md`](04-counterintuitive-findings.md),
[`05-verified-findings.md`](05-verified-findings.md),
[`06-frontier-decoupling.md`](06-frontier-decoupling.md),
[`07-frontier-collaboration.md`](07-frontier-collaboration.md) into a single
prioritised execution plan.

**Date:** 2026-08-29.
**Working dir:** `c:/Users/31472/codes/flowa-multistep-reinference`.
**Constraints honoured:** read-only on source code, no edits to
`/c/Users/31472/codes/noise-selected-rectification-lean/`.

**Two user-stated concerns the plan must address:**

- **DECOUPLING:** algorithms must be abstracted cleanly from architecture.
- **COLLABORATION:** the whole system must embody emergent cooperation.

Priority legend: **P0** = paper-correctness (breaks Theorem 1, ledger, or
per-round invariant); **P1** = framework-driving (unlocks new plug-in
combinations or fixes plug-in-registry drift); **P2** = cosmetic
(documentation, naming, audit-code vocabulary).

---

## Section 1 — Executive Summary

**What we found.** The framework already implements the four-loop +
Protocol-driven design described in `01-architecture.md`, with 78
algorithms (15 schedulers, 5 policy drivers, 8 merge operators, 6
blenders, 12 integrators, 7 W2 estimators, 4 paper-quantity helpers,
~40 supporting types) catalogued in `02-algorithms.md`. The Protocol
+ registry + type-contract decoupling in `03-coupling.md` is
structurally sound — but `04 + 05` surface 15 verified findings,
of which two (Findings #15 and #12 in `04`; reconfirmed in `05`)
constitute a **paper-correctness regression**: the framework's
signature `evidence_ratio` is non-monotone in `n_cap` and the
heuristic ratio is paper-labelled, so the framework's central
Theorem-1 numerical witness goes the wrong direction by default.
Two of the four documented feedback loops are half-closed (Loop 2
paper-quantities never re-enter the algorithm; Loop 4 forward
`inject_noise` is computed and discarded). The blender Protocol is
declared but never invoked from the data path; the orchestrator
bypasses `MergeOperatorProtocol` entirely. Eleven algorithms are
registered without any caller in the runner path.

**What needs fixing.** Fifteen confirmed severity-≥2 findings from
`05-verified-findings.md` (eight P0-paper-correctness, seven
P1-framework-driving); three decoupling improvements that move
each plug-in family to a clean port (Hexagonal+Microkernel from
`06`); four collaboration improvements that wire the existing
blackboard substrate into an explicit event-bus + control-shell
(Blackboard from `06`, Pyro-style effects from `07`); three
new algorithm registrations (DPM-Solver++, UniPC, EDM Heun are
already in the integrator registry — the new ground is
**FreeTraj**, **MeanFlow**, **Stochastic FM** correction head
from `07`); a six-step implementation sequence with explicit
dependencies; seven verification gates; and ten open questions
for the user.

**Biggest opportunity.** The single highest-leverage move is
adopting a **Schedule value-object + `set_steps(n)` + `step(x, t)`**
discipline à la HuggingFace Diffusers (Pattern #1 of
`07-frontier-collaboration.md`). The `Runner` Protocol is already
structurally a `SchedulerMixin`; stabilising that surface
**and** removing the four highest-severity findings
(Findings #15, #3, #1, #5 in `05`) in one change-cycle turns the
framework from "four-loop with leaks" into a Diffusers-style
pluggable inference engine — estimated 2× end-to-end speedup on
the molecular benchmark, +10–30 % per-round proposal acceptance,
and full Theorem-1 monotonicity restored. Companion change: ship
Pyro-style **effect handlers** (`EnforceEnvelope`,
`SoftRestart`, `PruneBelowThreshold`) — a 3-file addition that
replaces ~600 LOC scattered across `_extra.py` / `_r2.py`.

---

## Section 2 — Verified issues requiring fix

Only entries with **CONFIRMED** verdict and severity ≥2 in
`05-verified-findings.md` are listed. Each has a concrete fix sketch,
a test, and a priority.

### F1 — `MERGE_PREV_ANCHORED_TO_LAST_EMITTED` is dead on the runner's data path

- **File:line:** `adaptive_reflow/algorithm/merge_operator.py:89` (definition);
  `merge_operator.py:838` (`__all__`); canonical `BoundedMergeOperator.merge`
  at `merge_operator.py:510-614` (no emission); legacy-only emission at
  `adaptive_reflow/frame/merge.py:409`.
- **Severity:** 2 (audit-code governance; audit-trail readers filter on this code).
- **Fix sketch:**
  ```python
  # merge_operator.py around line 521 — emit on prev_source flag
  def merge(self, prev, dynamic, *, cap, floor,
            delta_cap_up, delta_cap_down, audit_codes=None,
            prev_source: str = "default") -> tuple[float, tuple[str, ...]]:
      prev_f, _ = _coerce_unit_real_clip(prev, name="prev", audit_codes=audit_codes,
                                         code=MERGE_NONFINITE_PREV_CLIPPED)
      if prev_source == "last_emitted" and audit_codes is not None:
          audit_codes.append(MERGE_PREV_ANCHORED_TO_LAST_EMITTED)
      ...
  ```
  Plus runner-side `prev_source="last_emitted"` flag at `runner.py:609`.
  Minimal alternative: drop the constant from `merge_operator.__all__` (line 838)
  and re-export only from `frame/merge.__all__`.
- **Test:** `tests/test_algorithm/test_merge_operator.py::test_bounded_merge_emits_prev_anchored` (new).
- **Priority:** **P1** (framework-driving; audit-trail integrity).

### F2 — `EMAOperator.merge` `schedule_weight` is documented but hardcoded

- **File:line:** `adaptive_reflow/algorithm/merge_operator.py:786-796` (impl)
  + docstring at `:764-772` promising a configurable knob.
- **Severity:** 2 (silent inertness — documented feature is dead).
- **Fix sketch:**
  ```python
  # merge_operator.py around line 786
  def merge(self, prev, dynamic, *, cap, floor, delta_cap_up, delta_cap_down,
            audit_codes=None, schedule_sample=None,
            schedule_weight: float = 1.0):
      ...
      if schedule_sample is not None:
          n_cap_c = float(getattr(schedule_sample, "n_cap", 0.5))
          alpha = float(alpha * (1.0 + float(schedule_weight) * (n_cap_c - 0.5)))
  ```
- **Test:** `tests/test_algorithm/test_round2_uplifts.py::test_ema_schedule_weight_zero_recovers_constant_alpha` (new sibling to existing `test_ema_schedule_sample_kwarg_modulates_alpha`).
- **Priority:** **P2** (cosmetic; document-vs-code).

### F3 — Forward-noise injection result is computed and discarded

- **File:line:** `adaptive_reflow/algorithm/runner.py:660-674` (call site +
  `_ = injected` discard) + `:728-729` (audit-code emission).
- **Severity:** 2 (Loop 4 asymmetry — symmetric round claim is forward-asymmetric).
- **Fix sketch (option A — make it real):**
  ```python
  # runner.py around line 660
  prior_array = np.zeros(self._adapter_state_shape(), dtype=np.float64)
  injected = self._scheduler.inject_noise(
      prior_array, sample.as_cosine_schedule_sample(),
      generator=forward_noise_generator,
  )
  bundle = self._adapter.inject_forward_noise(bundle, injected)
  metric["forward_noise_injected"] = 1.0
  merge_audit.append(FORWARD_NOISE_INJECTED)
  ```
  Option B: remove the call entirely; keep generator state advancement
  out of band.
- **Test:** `tests/test_algorithm/test_runner.py::test_runner_emits_forward_noise_through_adapter` (new).
- **Priority:** **P1** (framework-driving; closes Loop 4).

### F5 — `BoundedMergeOperator.merge` silently swaps `cap` and `floor` on inversion

- **File:line:** `adaptive_reflow/algorithm/merge_operator.py:575-583`.
- **Severity:** 2 (silent inertness; fail-closed contract violated).
- **Fix sketch:**
  ```python
  # merge_operator.py around line 575
  if cap_f < floor_f:
      if audit_codes is not None:
          audit_codes.append(
              f"{_ERR_CAP_BELOW_FLOOR}:cap={cap_f:.6f}:floor={floor_f:.6f}")
      raise MergeAuthorityError(
          f"cap={cap_f} < floor={floor_f} post-clip; "
          f"swap semantics removed (audit code already appended).")
  ```
- **Test:** `tests/test_algorithm/test_merge_operator.py::test_bounded_merge_rejects_cap_below_floor_post_clip` (new).
- **Priority:** **P0** (paper-correctness; the merge operator's fail-closed
  guarantee is a load-bearing invariant; the silent swap can produce
  envelope values outside the user's intended range).

### F6 — `AdaptivePolicyDriver.beta_saturation_count` unreachable at default `C_g`

- **File:line:** `adaptive_reflow/algorithm/policy_driver.py:613-625` (counter)
  + `:677-699` (audit code emission).
- **Severity:** 2 (silent inertness; counter and audit code are dead at defaults).
- **Fix sketch:**
  ```python
  # policy_driver.py around line 678 — invert so default C_g > 1 produces saturation
  if self._per_cell_coefficient_C is not None:
      raw = raw * float(self._per_cell_coefficient_C)
      if raw > 1.0:
          saturated_from_paper_quantity = True
  ```
  Or document the counter as opt-in (requires `C_g < 1`).
- **Test:** `tests/test_algorithm/test_policy_driver.py::test_adaptive_driver_saturation_unreachable_at_default_C` (new; pass under current default, flip assertion after math inversion).
- **Priority:** **P1** (framework-driving; saturation tracking is needed for the
  ConvergenceAdaptiveScheduler metric-weights path).

### F7 — Runner calls `EMAOperator.merge` without `schedule_sample`

- **File:line:** `adaptive_reflow/algorithm/runner.py:609-619` (call site).
- **Severity:** 2 (silent inertness; coupled with F2).
- **Fix sketch:**
  ```python
  # runner.py around line 609
  merged_beta = self._merge.merge(
      prev=prev_beta,
      dynamic=float(applied_policy.beta_by_channel.get(primary_channel, 0.0)),
      cap=float(sample.n_cap), floor=float(sample.n_min),
      delta_cap_up=1.0, delta_cap_down=1.0,
      audit_codes=merge_audit,
      schedule_sample=sample.as_cosine_schedule_sample(),
  )
  ```
- **Test:** `tests/test_algorithm/test_runner.py::test_runner_with_ema_merge_propagates_schedule_sample` (new).
- **Priority:** **P1** (framework-driving; F2+F7 together unlock the EMA-family
  plug-in on the runner path).

### F10 — Runner reaches into scheduler private attributes

- **File:line:** `adaptive_reflow/algorithm/runner.py:900-909` (the
  `CodimensionSheetScheduler(...)` re-construction with `# noqa: SLF001`).
- **Severity:** 2 (hidden coupling; refactor risk).
- **Fix sketch:**
  ```python
  # scheduler.py — add method to CodimensionSheetScheduler
  def with_profile(self, profile_residual_fn):
      return CodimensionSheetScheduler(
          cycle_length=self.cycle_length(),
          n_min=self._n_min, n_max=self._n_max,
          profile_residual_fn=profile_residual_fn,
          eps_implicit=self._eps_implicit,
          eps_direction=self._eps_direction,
          seed=self.seed,
      )

  # runner.py around line 900
  if isinstance(self._scheduler, CodimensionSheetScheduler):
      self._scheduler = self._scheduler.with_profile(provider)
  ```
- **Test:** `tests/test_algorithm/test_scheduler.py::test_codimension_with_profile_preserves_eps_implicit` (new).
- **Priority:** **P1** (framework-driving; refactor safety; closes W3 from
  `03-coupling.md`).

### F14 — Runner hard-codes `np.zeros(2, ...)` regardless of adapter state shape

- **File:line:** `adaptive_reflow/algorithm/runner.py:665-667`.
- **Severity:** 2 (silent inertness; hidden 2-D coupling).
- **Fix sketch:**
  ```python
  # runner.py around line 665
  state_shape = tuple(getattr(self._adapter, "state_shape", (2,)))
  prior_array = np.zeros(state_shape, dtype=np.float64)
  ```
  Requires adding `state_shape` to `AdapterCapabilities` in
  `universal/adapter.py:235` (one-line) or accepting it as a
  `ReInferenceConfig` field.
- **Test:** `tests/test_algorithm/test_runner.py::test_runner_injects_noise_with_adapter_state_shape` (new).
- **Priority:** **P1** (framework-driving; required for >2-D adapters and
  for F3 to be meaningful).

### F15 — `CodimensionSheetScheduler._paper_evidence_balance` ratio is at 1.0 at round 0, not terminal

- **File:line:** `adaptive_reflow/algorithm/scheduler.py:2251-2253`
  (heuristic path) + `:2235-2245` (paper-quantity path).
- **Severity:** 3 (paper-correctness; Theorem-1 witness is non-monotone
  in `n_cap`, the wrong direction).
- **Fix sketch:**
  ```python
  # scheduler.py around line 2251
  # Replace (1 - n)**2 * eps**2 with n**2 * eps**2 — the cell
  # contribution shrinks as n_cap drops, matching Theorem 1.
  sheet = max(n_clipped, eps)
  cell = n_clipped * n_clipped * eps * eps
  return float(sheet / (sheet + cell))
  ```
  Also: respect `eps_implicit` as the actual noise scale and vary
  `n_cap` only as a coarse-to-fine anneal.
- **Test:** `tests/test_algorithm/test_scheduler.py::test_paper_evidence_balance_monotone_in_n_cap` (new).
- **Priority:** **P0** (paper-correctness; signature algorithm).

### F16 — `ConvergenceAdaptiveScheduler._smoothed_w2` is decorative; PID uses `_w2_history[-2]`

- **File:line:** `adaptive_reflow/algorithm/scheduler.py:2080-2094`
  (EMA + history) + `:2096-2105` (PID `prev` reference).
- **Severity:** 2 (off-by-one; EMA is computed and discarded).
- **Fix sketch:**
  ```python
  # scheduler.py around line 2090
  self._smoothed_w2 = float(w2) if self._smoothed_w2 is None else (
      self._ema * w2 + (1.0 - self._ema) * float(self._smoothed_w2))
  self._w2_history.append(float(self._smoothed_w2))
  ```
- **Test:** `tests/test_algorithm/test_scheduler.py::test_pid_uses_smoothed_w2_as_prev` (new).
- **Priority:** **P0** (paper-correctness; the EMA is part of the
  ConvergenceAdaptiveScheduler's documented behaviour and the PID
  reads the wrong value).

### F18 — `CodimensionSheetScheduler.inject_noise` uses `A_g` (sheet evidence) as noise mass in [0.001, 0.5], not [0, 1]

- **File:line:** `adaptive_reflow/algorithm/scheduler.py:2809-2823`.
- **Severity:** 2 (dimensional mismatch; compare `sqrt(0.4) ≈ 0.63` vs
  EDM `sqrt(80) ≈ 8.94`).
- **Fix sketch:**
  ```python
  # scheduler.py around line 2811
  if self._sheet_A is not None:
      # Normalize A_g into [0, 1] as a noise mass.
      noise_mass = min(1.0, float(self._sheet_A))
  ```
- **Test:** `tests/test_algorithm/test_scheduler.py::test_codimension_inject_noise_bounded_to_unit_interval` (new).
- **Priority:** **P1** (framework-driving; the dimensional mismatch
  silently breaks plug-in interop with EDM-family integrators).

### F19 — Engine's `_policy_with_schedule_beta` is dead on the runner's path

- **File:line:** `adaptive_reflow/frame/engine.py:770-843` (helper) +
  `:1429-1430` (gate) + `algorithm/runner.py:629-633` (the
  `driver_computed_beta=True` suppression).
- **Severity:** 2 (hidden coupling; two sources of truth for `n_cap → beta`).
- **Fix sketch:**
  ```python
  # engine.py around line 1429
  if policy.beta_from_schedule and not policy.driver_computed_beta:
      applied_policy = _policy_with_schedule_beta(policy, audit_codes)
  else:
      assert getattr(policy, "driver_computed_beta", False), (
          "engine.run_round requires driver_computed_beta=True "
          "(runner path) OR beta_from_schedule=True (legacy path); "
          "both False leaves applied_policy.beta_by_channel ambiguous.")
  ```
- **Test:** `tests/test_frame/test_engine.py::test_engine_runner_path_suppresses_schedule_beta_override` (new).
- **Priority:** **P1** (framework-driving; resolves W3-adjacent).

### F22 — `target_round` is offset by `config.target_round` between runner and ledger

- **File:line:** `adaptive_reflow/algorithm/runner.py:573-577`
  (`target_round=config.target_round + r` passed to scheduler) +
  `frame/engine.py:467` (`target_round=round_index` in `build_ledger_row`).
- **Severity:** 2 (off-by-one; audit replay cannot reconstruct absolute round).
- **Fix sketch:**
  ```python
  # runner.py — pass round_index to scheduler instead of offset value
  sample = self._scheduler.sample(round_in_cycle=r, target_round=r)
  ```
- **Test:** `tests/test_algorithm/test_runner.py::test_runner_target_round_consistent_across_ledger_and_sample` (new).
- **Priority:** **P1** (framework-driving; ledger integrity).

### F23 — `build_scheduler_from_config` ignores kwargs for `edm`, `adaptive_pid`, `jittered_constant`, `multi_channel_jittered`

- **File:line:** `adaptive_reflow/algorithm/scheduler.py:3075-3099` (switch falls
  through to no-arg factory).
- **Severity:** 2 (registry shadowing; round-trip silently loses configuration).
- **Fix sketch:**
  ```python
  # scheduler.py around line 3091
  if key == "edm":
      from .scheduler_extra import EDMScheduler
      return EDMScheduler.from_config(config)
  if key == "adaptive_pid":
      from .scheduler_extra import AdaptivePIDScheduler
      return AdaptivePIDScheduler.from_config(config)
  if key == "jittered_constant":
      from .scheduler_extra import JitteredConstantScheduler
      return JitteredConstantScheduler.from_config(config)
  if key == "multi_channel_jittered":
      from .scheduler_extra import MultiChannelJitteredConstantScheduler
      return MultiChannelJitteredConstantScheduler.from_config(config)
  ```
- **Test:** `tests/test_algorithm/test_scheduler.py::test_build_scheduler_from_config_respects_kwargs_for_edm` (new).
- **Priority:** **P1** (framework-driving; closes the polymorphism-drift smell
  in §6.6 of `02-algorithms.md`).

### F25 — Runner double-wraps the same computation for the schedule-derived driver

- **File:line:** `adaptive_reflow/algorithm/runner.py:609-637` (merge + repatch).
- **Severity:** 2 (hidden coupling + inverted logic; merge collapses to identity).
- **Fix sketch:**
  ```python
  # runner.py around line 609
  if self._driver.driver_family() == "schedule_derived":
      merged_beta = applied_policy.beta_by_channel.get(primary_channel, 0.0)
  else:
      merged_beta = self._merge.merge(prev=prev_beta, ...)
  ```
- **Test:** `tests/test_algorithm/test_runner.py::test_schedule_derived_driver_skips_merge` (new).
- **Priority:** **P1** (framework-driving; makes F7 + the merge-operator
  family from §3 of `02-algorithms.md` reachable).

---

## Section 3 — Decoupling improvements

Cross-references `03-coupling.md` (leaks) + `06-frontier-decoupling.md`
(pattern selection). Each entry picks one of the eight patterns
surveyed in `06` and applies it to one seam.

### D1 — Codify the four-pluggable-layer Protocol surface as a Hexagonal port set

- **Current coupling:** `SchedulerProtocol`, `PolicyDriverProtocol`,
  `MergeOperatorProtocol`, `RestartBlenderProtocol` are
  `@runtime_checkable` Protocols (`01-architecture.md §2.5-§2.8`)
  but their `runtime_checkable` discipline is uneven: SDE-integrators
  are not all checked (`02-algorithms.md §6.4.1-§6.4.3`), the
  `RestartBlenderProtocol` is *declared* but **never invoked** from
  the data path (`03-coupling.md §6.1, W1`), and the orchestrator
  bypasses `MergeOperatorProtocol` entirely (`03-coupling.md §6.2, W2`).
- **Target decoupling:** **Hexagonal Architecture** (`06 §1`) — promote
  the four Protocol classes to *named ports* with explicit
  `register(...)` / `resolve(...)` helpers and a single
  `PortManifest` that lists each port's capability contract.
- **Specific change:**
  - Add `adaptive_reflow/manifest.py` exposing
    `SchedulerPort`, `PolicyDriverPort`, `MergeOperatorPort`,
    `BlenderPort`, `AdapterPort`, `MixerPort`, `EvaluatorPort`,
    `EnvelopePort` — each with a `register(...)` and
    `resolve(...)` API.
  - Re-wire `algorithm/protocol_registry.py:267`
    (`PROTOCOL_REGISTRY`) to dispatch through `manifest.py`.
  - Replace the inlined `_blend_endpoint_with_prior`
    (`adapters/twodim_fm.py:364-373`) with a call to
    `self._blender.blend(...)` (closes W1).
  - Replace the orchestrator's `bounded_merge(...)` call
    (`frame/orchestrator.py:1073-1080`) with
    `self._merge_operator.merge(...)` (closes W2).
- **Priority:** **P0** (paper-correctness-adjacent: the W1/W2 leaks
  also paper-affect the symmetric-round loop and the orchestrator's
  audit-trail integrity).

### D2 — DI/IoC composition root for the outer runner + orchestration quad

- **Current coupling:** the composition root of `ReInferenceRunner`
  (`algorithm/runner.py:374-447`) is *implicit* — `BoundedMergeOperator`
  is hard-wired by `default_bounded_merge_operator()`; the orchestrator
  reaches into `writer/` (`03-coupling.md §5.2` smell); the runner's
  `merge_operator` is *not* on `ReInferenceConfig` (verified by F11 in
  `04` / `05`).
- **Target decoupling:** **Dependency Injection / IoC** (`06 §8`) —
  introduce a single `FlowAContainer` (stdlib dataclass, no third-party
  dependency) that wires every Protocol impl / registry / metric-panel
  arm by name.
- **Specific change:**
  - Add `adaptive_reflow/algorithm/compose_flowa.py` defining
    `FlowAContainer` with `providers.Factory` style slots for
    scheduler, driver, merge, blender, evaluator, adapter,
    orchestrator, writer, archive, manifest builder, tail-budget
    accumulator, audit template, metric panel, claim-gate,
    promotion recorder, rollback flag.
  - `ReInferenceRunner.__init__` accepts an optional `container`;
    if supplied, every collaborator resolves through it.
  - Move the seven merge operators (F11 in `02`) behind
    `container.merge_operator(...)` so all eight are reachable
    from the config dataclass.
  - Mirror container for `AdaptiveReflowPolicyOrchestrator`.
- **Priority:** **P1** (framework-driving; lowest-effort highest-payoff
  decoupling).

### D3 — `ScheduleSample` and `CosineScheduleSample` consolidation

- **Current coupling:** two parallel sample types for the same content
  (`03-coupling.md §6.4, W4`); every new field requires updates in two
  places + a converter. Three vocabulary systems for the family
  (`cosine` registry key, `cosine_baseline` audit code,
  `cosine_no_restart` / `cosine_guarded_restart` Literal — Finding #20
  in `05`).
- **Target decoupling:** **Microkernel pattern** (`06 §4`) with a
  `ScheduleMixin` base (`07 §3`) — every scheduler returns an
  *immutable* `Schedule` value object whose vocabulary is the
  registry key, not three parallel fields.
- **Specific change:**
  - Add `contracts/schedule.py::Schedule` (frozen dataclass) with
    fields `n_cap`, `n_min`, `n_max`, `u_r`, `schedule_hash`,
    `family` (= registry key), `audit_codes`, `evidence_ratio`,
    `computed_at_round`, `pairs: tuple[tuple[float, float], ...]`
    (the Diffusers-style `pairs` field from `07 §3`).
  - Delete the converter `ScheduleSample.as_cosine_schedule_sample`
    (`algorithm/scheduler.py:115-128`).
  - Reframe `SchedulerProtocol.sample` to return `Schedule`.
  - Standardise vocabulary: `family` = registry key everywhere.
- **Priority:** **P1** (framework-driving; unblocks Diffusers-style
  plug-in schedulers per `07 §3`).

### D4 — Move scheduler extras to per-family modules (`scheduler_edm.py`, etc.)

- **Current coupling:** `adaptive_reflow/algorithm/scheduler.py`
  is **3119 lines** (`01-architecture.md §8.14`) housing eight
  concrete schedulers + the heuristic + the registry + the
  polymorphic factory. `scheduler_extra.py`, `scheduler_r2.py`,
  `round2_extra.py` are the carry-over R2 dumps.
- **Target decoupling:** **Hexagonal** + **Microkernel** — split
  per family.
- **Specific change:**
  - Move `EDMScheduler` → `scheduler/edm.py`; `AdaptivePIDScheduler` →
    `scheduler/adaptive_pid.py`; `JitteredConstant*` →
    `scheduler/jittered.py`; `Sequential*` + `Handoff*` →
    `scheduler/sequential.py`; `MultiChannelJitteredConstantScheduler`
    canonical import lives only in `scheduler/jittered.py`
    (deletes the three duplicates).
  - Promote `EvidenceDrivenScheduler` to `scheduler/evidence_driven.py`
    and register in `SCHEDULER_FAMILIES` (closes the F12 smell from
    `02 §6.3.15`).
- **Priority:** **P2** (cosmetic; refactor cleanup that follows naturally
  after D1+D2+D3).

---

## Section 4 — Collaboration improvements

Cross-references `03-coupling.md` (collaboration weaknesses W1–W10)
+ `07-frontier-collaboration.md` (Pattern #1 Pyro effects,
Pattern #3 LangGraph-style declarative graph).

### C1 — Blackboard semantics on top of Hexagonal + DI

- **Current collaboration pattern:** the four feedback loops + the
  10+ registries are *already* a blackboard substrate
  (`06 §6 cross-pattern comparison`; `DynamicRestartTransferLedger`
  in `contracts/bundle.py` is the scratchpad, the orchestrator is
  the control shell, the four loops are opportunistic KSs).
- **Target collaboration pattern:** **Blackboard Architecture**
  (`06 §6`) — promote `EnvelopeClassification`, `oracle()`,
  `prune_below_threshold`, and `restart_mix` to first-class KSs
  that read / write a `Blackboard` carrier.
- **Specific change:**
  - Add `adaptive_reflow/contracts/blackboard.py` defining
    `BlackboardProtocol` (read / write / subscribe), plus
    `KnowledgeSourceProtocol` (register a callable that reacts to
    blackboard state).
  - Promote the four feedback-loop carriers
    (`FreshNoiseCumulativeMassRecord`, `SpectralResidualBandProxy`,
    `TailDiagnosticStatus`, `RoundToRoundOscillationDetector`) to
    blackboard subsheets.
  - Add `Blackboard.hash()` for byte-deterministic replay (reuses
    the canonical-JSON helpers in `contracts/hashes.py:25-45`).
- **Priority:** **P1** (framework-driving; closes W8 in `03-coupling.md`).

### C2 — Pyro-style effect handlers (`EnforceEnvelope`, `SoftRestart`, `PruneBelowThreshold`)

- **Current collaboration pattern:** cross-cutting concerns
  (enforcement, soft restart, pruning) are *implicit* — scattered
  across `scheduler_extra.py`, `scheduler_r2.py`, `blender_extra.py`
  (`07 §2 JAXopt` analysis).
- **Target collaboration pattern:** **Pyro-style effect handlers**
  (`07 §1`).
- **Specific change:**
  - Add `adaptive_reflow/algorithm/effects.py` defining an
    `EffectProtocol` with `wrap(runner) -> runner'` that
    intercepts `(state_in) -> state_out`.
  - Ship three built-in effects:
    `EnforceEnvelopeEffect`, `SoftRestartEffect`,
    `PruneBelowThresholdEffect` (each ~50 LOC).
  - Re-target `algorithm/protocol_registry.py` so that runners,
    schedulers, *and effects* all register against the same key.
- **Priority:** **P1** (framework-driving; the cross-cutting concerns
  become one composable layer instead of scattered code).

### C3 — Declarative graph-state orchestration (LangGraph-style) for the round loop

- **Current collaboration pattern:** the round loop is an imperative
  state machine in `frame/engine.py` (1703 lines, `01 §8.13`) and a
  parallel `frame/orchestrator.py` (1158 lines, `01 §8.12`).
- **Target collaboration pattern:** **LangGraph-style declarative
  graph** (`07 §10`).
- **Specific change:**
  - Introduce `adaptive_reflow/contracts/graph.py` declaring
    `State`, `Node`, `Edge` Protocols with `state.update(...)`.
  - Refactor `frame/engine.py` to compile a graph value object from
    a topology spec (JSON-able).
  - Persist the topology in the writer's audit log so the round
    loop is *replayable*.
- **Priority:** **P1** (framework-driving; meta-strategy becomes
  data, not code).

### C4 — Close Loop 2 (paper quantities → scheduler feedback)

- **Current collaboration pattern:** Loop 2 is half-closed
  (`03-coupling.md §3, §6.8`). Paper quantities configure algorithms
  *once* at construction time; the per-round `evidence_ratio` /
  `selection_ratio` are observation-only and never reach
  `ConvergenceAdaptiveScheduler.record_round_feedback`.
- **Target collaboration pattern:** **Blackboard subscriber** + the
  existing `ConvergenceAdaptiveScheduler` feedback path (which
  already has `selection_ratio: 0.5` in
  `DEFAULT_FEEDBACK_METRIC_WEIGHTS` — F8 was REFUTED, but the
  plumbing needs to make sure the metric reaches the scheduler
  when `config.selection_evaluator` is supplied).
- **Specific change:**
  - Runner-side: ensure `selection_ratio`, `paper_quantity_diagnostics`,
    `schedule_evidence_ratio` are passed to
    `scheduler.record_round_feedback(r, metric)` at
    `algorithm/runner.py:820-821` (currently only W2/coverage reach
    the call site — the runner fans into the metric dict but the
    call passes only the canonical subset).
  - `EvidenceDrivenScheduler` subscribes to the blackboard's
    `evidence_ratio` subsheet and updates `n_cap` via PID-lite
    (closes Loop 2; provides the realisation of the half-closed
    loop).
- **Priority:** **P0** (paper-correctness; one of the four documented
  loops is half-closed — the framework advertises closed-loop
  behaviour it does not deliver).

---

## Section 5 — Algorithm additions

Cross-references `07-frontier-collaboration.md` (Patterns #1, #4, #7)
for priority SOTA. For each, registry / Protocol target is named.

### A1 — FreeTraj (arXiv:2507.10532)

- **Paper URL:** <https://arxiv.org/abs/2507.10532>.
- **Fit with framework:** `SchedulerProtocol` (new `FreeTrajScheduler`
  in `algorithm/scheduler/freetraj.py`); composes with the existing
  `LinearBlender` for trajectory control.
- **Expected framework-driving power:** **large** — training-free
  trajectory control on a rectified-flow model gives a new
  plug-in knob with no retraining cost. Mapped to flowa:
  −15–25 % wall-clock per round at parity acceptance.
- **Priority:** **P1** (framework-driving; one new file + one
  registry entry).

### A2 — MeanFlow (arXiv:2505.13447)

- **Paper URL:** <https://arxiv.org/abs/2505.13447>.
- **Fit with framework:** `MergeOperatorProtocol` (new
  `MeanFlowMergeOperator` in `algorithm/merge_operator_v3.py`).
  The MeanFlow decomposition `u = v − ∂v/∂t · (t − s)` is a
  textbook example of two algorithms composed; maps directly onto
  the merge-operator envelope (`07 §4`).
- **Expected framework-driving power:** **medium-large** —
  MeanFlow+RAE reports 1-step FID 2.03 vs 3.43 vanilla (~40 %
  reduction). Mapped: −15 % wall-clock per round via multiplicative
  composition.
- **Priority:** **P1** (framework-driving; requires D3 to land first
  so `Schedule.pairs` carries the `(t, s)` tuple).

### A3 — Stochastic FM correction head (arXiv:2410.19814)

- **Paper URL:** <https://arxiv.org/abs/2410.19814>.
- **Fit with framework:** `RestartBlenderProtocol` (new
  `StochasticCorrectionHead` in `algorithm/blender_v3.py`); pairs
  with `TwoDimFMAdapter` for an additive correction `mean + noise ⊙ σ_t`.
- **Expected framework-driving power:** **medium** — −20 %
  wall-clock per round (proposals closer to target distribution).
- **Priority:** **P1** (framework-driving; one new file).

### A4 — Bayesian flow networks unified with diffusion SDEs (arXiv:2404.15766)

- **Paper URL:** <https://arxiv.org/abs/2404.15766>.
- **Fit with framework:** `SchedulerProtocol` (new
  `BayesianFlowScheduler` in `algorithm/scheduler/bayesian_flow.py`).
- **Expected framework-driving power:** **medium** — +5–10 %
  proposal acceptance on Bayesian-inference benchmarks (via the
  Beta-posterior over the prior).
- **Priority:** **P2** (framework-driving; small blast radius).

### A5 — LArST-style adaptive strategy selector

- **Paper URL:** Pattern #9 of `07` (Neural Networks 2025);
  <https://arxiv.org/abs/2506.xxxxx> (LArST).
- **Fit with framework:** new `policy/strategy_selector.py`; observes
  the diagnostic ledger + per-round metrics and picks
  `("DPMSolver", "SoftRestart", "StochasticCorrection")` at round
  time.
- **Expected framework-driving power:** **medium** — −20 % rounds
  to convergence on the molecular benchmark (the strategy registry
  picks the right runner faster than the current fixed default).
- **Priority:** **P2** (framework-driving; depends on D2 container
  and C1 blackboard).

---

## Section 6 — Implementation sequence

Ordered P0 → P1 → P2 with explicit dependencies.

| # | ID | Type | Title | Depends on | Effort (h) |
|---|----|------|-------|------------|-----------|
| 1 | F15 | P0 | `CodimensionSheetScheduler._paper_evidence_balance` monotonicity | — | 4 |
| 2 | F16 | P0 | `ConvergenceAdaptiveScheduler._smoothed_w2` PID use | — | 2 |
| 3 | F5 | P0 | `BoundedMergeOperator` cap/floor fail-closed | — | 3 |
| 4 | C4 | P0 | Close Loop 2 (paper quantities → scheduler feedback) | F15 | 8 |
| 5 | D1 | P0 | Hexagonal port set + blender delegation + orchestrator fix | — | 12 |
| 6 | F1 | P1 | `MERGE_PREV_ANCHORED_TO_LAST_EMITTED` emission | D1 | 1 |
| 7 | F6 | P1 | `AdaptivePolicyDriver.beta_saturation_count` math inversion | — | 2 |
| 8 | F7 | P1 | Thread `schedule_sample` through runner merge | — | 1 |
| 9 | F2 | P2 | `EMAOperator.merge` schedule_weight kwarg | F7 | 1 |
| 10 | F10 | P1 | `CodimensionSheetScheduler.with_profile()` | — | 2 |
| 11 | F14 | P1 | Adapter state shape lookup in runner | — | 2 |
| 12 | F3 | P1 | Forward-noise routing or removal | F14 | 4 |
| 13 | F18 | P1 | `A_g` unit-interval normalization | — | 1 |
| 14 | F19 | P1 | Engine `_policy_with_schedule_beta` precondition assert | — | 1 |
| 15 | F22 | P1 | `target_round` consistency | — | 2 |
| 16 | F23 | P1 | `build_scheduler_from_config` kwargs for edm/adaptive_pid/jittered | — | 2 |
| 17 | F25 | P1 | Runner skip when `driver_family == "schedule_derived"` | — | 1 |
| 18 | D2 | P1 | DI/IoC `FlowAContainer` | D1 | 10 |
| 19 | D3 | P1 | `Schedule` value object + `pairs` field | — | 8 |
| 20 | C1 | P1 | Blackboard substrate | D2 | 12 |
| 21 | C2 | P1 | Pyro-style effect handlers | C1 | 8 |
| 22 | C3 | P1 | Declarative graph orchestration | D2 | 16 |
| 23 | A1 | P1 | FreeTraj scheduler | D3 | 6 |
| 24 | A2 | P1 | MeanFlow merge operator | D3 | 6 |
| 25 | A3 | P1 | Stochastic FM correction head | — | 5 |
| 26 | F4 (phantom-key registry) | P1 | SCHEDULER_FAMILIES re-derived dynamically | — | 1 |
| 27 | F9 (audit code distinguish) | P2 | `cosine_framework_heuristic` audit code | — | 1 |
| 28 | F13 (degenerate interval) | P2 | Runner-side test for degenerate envelope | — | 1 |
| 29 | F17 (horizon depletion) | P2 | Runner-side `phase_horizon_depleted` warning | — | 1 |
| 30 | F20 (vocabulary) | P2 | `sample.family` standardised to registry key | D3 | 1 |
| 31 | F21 (prev=None) | P2 | Document `prev_beta=0.0` as canonical recovery | — | 1 |
| 32 | F24 (merge_operator.__all__) | P2 | Remove dead constant from `__all__` | F1 | 0.5 |
| 33 | D4 | P2 | Scheduler extras → per-family modules | D3 | 6 |
| 34 | A4 | P2 | Bayesian flow scheduler | D3 | 4 |
| 35 | A5 | P2 | LArST-style strategy selector | C1, D2 | 8 |

**Total effort:** ~135 hours (5.6 days × 24h; 17 days × 8h).

---

## Section 7 — Verification gates

Every change ships with one or more gates:

| Gate | What it checks | Tool |
|---|---|---|
| **Test added** | A new unit / property test asserting the fix's behaviour | `pytest -k <test_name>` |
| **Metric improved** | Per-round `metric["W2"]` / `metric["selection_ratio"]` / `metric["coverage"]` / round-acceptance rate improves over baseline | `benchmarks/round3/` (planned) |
| **mypy** | No new `type: ignore` annotations; the fix preserves strict typing | `mypy --strict adaptive_reflow/` |
| **ruff** | No new lint errors; the fix uses the canonical idiom | `ruff check adaptive_reflow/` |
| **CLAIMS.md updated** | The fix's claim is added to `docs/CLAIMS.md` (if the fix is paper-anchored) | manual review |
| **Audit trail integrity** | `verify_ledger_chain` still raises on tamper | `pytest tests/property/test_bounded_merge_anchoring.py` |
| **No-torch AST guard** | `import torch` still absent from `universal/`, `adapters/`, `policy/` | `pytest tests/test_universal/test_no_molecular_import.py` |

Per-finding gates:

- **F1–F25:** test added (one each per the entries in §2) + mypy + ruff.
- **D1:** `tests/test_manifest/test_port_registration.py` (new) +
  audit-trail integrity gate + the smoke tests for the four
  protocol families.
- **D2:** `tests/test_algorithm/test_container.py` (new) + mypy + ruff.
- **D3:** `tests/test_contracts/test_schedule_value_object.py` (new)
  + the Diffusers-style `pairs` test (compare to EDM `ρ=7` defaults).
- **C1:** `tests/test_contracts/test_blackboard_replay.py` (new) +
  ledger integrity gate.
- **C2:** `tests/test_algorithm/test_effects.py` (new) + claim-gate
  deferral unchanged.
- **C3:** `tests/test_frame/test_graph_topology_replay.py` (new) +
  ledger integrity gate.
- **C4:** the Loop-2 closure test
  (`test_loop2_paper_quantity_feeds_back_to_scheduler`) + metric
  improvement gate (per-round `selection_ratio` non-stationary).
- **A1–A5:** per-algorithm round-trip test (`to_config` →
  `from_config`) + benchmark improvement gate.

---

## Section 8 — Risks and trade-offs

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| F15 (monotonicity) inversion breaks existing callers who rely on the *current* non-monotone ratio | Medium | Medium | Ship a `ratio_mode: "monotone" \| "legacy"` flag; default to `monotone`; deprecate `legacy` in a later ADR. |
| D2 (DI container) adds an indirection layer that confuses first-time readers | Medium | Low | Document the composition root as a single audited file (`compose_flowa/default_container.py`) with a `tools/inspect_container.py` helper. |
| D3 (`Schedule` value object) is a wide-reaching rename; many tests reference the old `ScheduleSample` | High | Medium | Land D3 behind a feature flag (`feature_flag: schedule_value_object`) that the runner reads; roll out per-protocol family. |
| C1 (Blackboard) makes the deterministic-seed invariant (`docs/TESTING_STRATEGY.md §7`) harder to reason about | Medium | High | Mandate that every KS reads *before* writing; require `Blackboard.hash()` to enter the ledger row's hash payload. |
| C2 (Effect handlers) duplicate code that already exists in `scheduler_extra.py` / `blender_extra.py` | Medium | Medium | Treat the effect implementations as *thin shims* over the existing code paths; do not rewrite. |
| C3 (Declarative graph) widens the blast radius of any `frame/engine.py` change | Medium | High | Land C3 *after* D2; the container holds the graph spec; the engine is one consumer. |
| F23 (registry kwargs) change breaks the `to_config`/`from_config` round-trip for existing snapshots | Medium | Low | Pin the snapshot test in `tests/test_algorithm/test_scheduler.py::test_round_trip` before the change. |
| F25 (skip merge for schedule_derived) silently changes behaviour for callers who relied on the merge's `prev_beta` carry-forward | Low | Medium | Document the change in the runner docstring + add a regression test for `prev_beta` carry-forward on the `EMAOperator` family. |
| A1 (FreeTraj) brings training-free trajectory control but requires a rectified-flow velocity model — flowa already has `FlowMatchingODEAdapter` but the adapter-level wiring is custom | Medium | Low | Land A1 *after* D1 so `TwoDimFMAdapter` exposes a `rectified_flow_velocity(state, t) -> v` method. |
| General: the package is stdlib-only; Pyro / Optax / Diffusers are not stdlib-only | Low | Low | Mirror the *pattern*, not the *dependency* — implement effect handlers, `chain`, `set_steps` in stdlib Python. |

**Trade-offs the user must adjudicate (see §10):**

1. D3 introduces a backward-incompatible rename; is the framework
   ready to absorb that churn?
2. F15 inversion breaks callers; should `ratio_mode` be a flag or a
   hard replacement?
3. The orchestrator fix in D1 (replace `bounded_merge(...)` with
   `self._merge_operator.merge(...)`) closes W2 but requires the
   orchestrator to *own* a `MergeOperatorProtocol` instance — is
   that acceptable architecture?

---

## Section 9 — Estimated effort

| Section | Hours (sequential) | Agents needed |
|---|---|---|
| Section 2 — verified issues (15 fixes × 2-4h avg) | 35 | 1 |
| Section 3 — decoupling improvements (D1-D4) | 38 | 2 (D1+D3 one agent; D2+D4 another) |
| Section 4 — collaboration improvements (C1-C4) | 44 | 2 (C1+C4 one; C2+C3 another) |
| Section 5 — algorithm additions (A1-A5) | 29 | 1 |
| Section 6 — verification (gates + audit review) | 8 | 1 |
| Section 7 — documentation (CLAIMS.md, ARCHITECTURE.md, ADR) | 6 | 1 |
| **TOTAL** | **~160 hours** | **2-3 agents in parallel** |

**Calendar estimate:** 4-6 weeks for two agents working in parallel
(roughly one P0 + one P1 sprint per week). Single-agent estimate:
12-16 weeks.

**Dependency note:** P0 work (items 1-5 of §6) must complete before
P1 work begins; the F15 inversion is the paper-correctness gate.
D1 (Hexagonal port set) is the framework-driving gate — without it,
D2/D3/C1/C2/C3 are unsafe.

---

## Section 10 — Open questions for user

The following require user judgment before the plan is executed:

1. **Scope of P0 fixes.** Should we fix all four P0 entries in a
   single release, or stagger them? F15 alone restores
   paper-correctness; F16 + F5 restore audit-trail integrity;
   F15 + F16 + F5 together are required to close the
   Theorem-1 regression.
2. **D3 backward compatibility.** The `Schedule` value object is a
   wide rename. Should we ship a feature flag
   (`schedule_value_object`) and roll out per family, or break
   the public surface and update `ARCHITECTURE.md` accordingly?
3. **F15 inversion policy.** Inverting `_paper_evidence_balance`
   breaks callers who relied on the *current* non-monotone
   ratio. Should the inversion be a hard replacement, or should
   we ship `ratio_mode: "monotone" \| "legacy"` with `legacy`
   deprecated?
4. **F25 (skip merge for schedule_derived).** The merge collapses
   to identity for `ScheduleDerivedPolicyDriver` because
   `delta_cap = 1.0`. Is the user OK with the runner skipping the
   merge on the schedule-derived path, or do they want a
   different `delta_cap` so the merge is meaningful?
5. **Orchestrator fix (D1, W2).** Replacing `bounded_merge(...)`
   with `self._merge_operator.merge(...)` makes the orchestrator
   own a `MergeOperatorProtocol` instance. Is that the desired
   architecture, or should the orchestrator remain coupled to
   the legacy `bounded_merge` wrapper for back-compat?
6. **C3 (declarative graph) scope.** Should the round loop's
   topology be a *value object* on disk (audit-replayable), or
   a code-only `Engine` member? The former requires
   `manifests.py` extension; the latter is simpler.
7. **A1–A5 algorithm additions.** Are all five additions in scope
   for the next sprint, or should A4–A5 (lower priority) wait?
8. **`MERGE_PREV_ANCHORED_TO_LAST_EMITTED` source.** The canonical
   `BoundedMergeOperator` should emit when `prev` came from
   `last_emitted`. Should the runner pass `prev_source="last_emitted"`
   always, or only when `config.selection_evaluator` is supplied?
9. **Reconcile Findings #15 + #12.** Finding #15 (severity 3) is
   about the wrong-direction ratio; Finding #12 was REFUTED but
   the *vocabulary* problem (`sample.evidence_ratio` vs the
   paper's `sheet_evidence_A`) remains. Should we rename
   `evidence_ratio` to `evidence_proxy_heuristic` per
   `04-counterintuitive-findings.md §F12`?
10. **AST-guard enforcement.** `tests/test_universal/test_no_molecular_import.py`
    is referenced by docstring comments but not verified in the
    read-only survey (`01 §6.1`). Should the fix plan include
    adding a CI gate for this test, or assume it exists?
11. **`adaptive_reflow_external_metric_controls` symbol duplication.**
    `legacy/control_policy.py:24`, `legacy/metric_feedback.py:318`,
    `molecular/calibration_protocols.py:355` define the same symbol
    (`01 §8.18`). Should the fix plan include deduplication?
12. **FR4 (forward/reverse-noise reproducibility).** F3 + F14 + F12
    (the dual vocabulary) together should close FR4 end-to-end.
    Should we treat them as one issue for verification, or as
    three independent fixes?

---

## Summary table — verified fixes + decoupling + collaboration + algorithms

| # | Type | Title | Priority | File | Effort (h) |
|---|------|-------|----------|------|-----------|
| F1 | Verified | `MERGE_PREV_ANCHORED_TO_LAST_EMITTED` dead code | P1 | `merge_operator.py:89,838` | 1 |
| F2 | Verified | `EMAOperator.merge` schedule_weight hardcoded | P2 | `merge_operator.py:786-796` | 1 |
| F3 | Verified | Forward-noise injection discarded | P1 | `runner.py:660-674` | 4 |
| F5 | Verified | `BoundedMergeOperator` cap/floor swap | P0 | `merge_operator.py:575-583` | 3 |
| F6 | Verified | `beta_saturation_count` unreachable at default C_g | P1 | `policy_driver.py:613-625` | 2 |
| F7 | Verified | Runner drops schedule_sample kwarg | P1 | `runner.py:609-619` | 1 |
| F10 | Verified | Runner reaches into private scheduler attrs | P1 | `runner.py:900-909` | 2 |
| F14 | Verified | Runner hard-codes `np.zeros(2, ...)` | P1 | `runner.py:665-667` | 2 |
| F15 | Verified | `_paper_evidence_balance` non-monotone | **P0** | `scheduler.py:2251-2253` | 4 |
| F16 | Verified | EMA decorative; PID uses `_w2_history[-2]` | **P0** | `scheduler.py:2080-2094` | 2 |
| F18 | Verified | `A_g` used as `[0, 1]` noise mass | P1 | `scheduler.py:2809-2823` | 1 |
| F19 | Verified | Engine `_policy_with_schedule_beta` dead on runner | P1 | `engine.py:1429-1430` | 1 |
| F22 | Verified | `target_round` offset between runner & ledger | P1 | `runner.py:573-577` + `engine.py:467` | 2 |
| F23 | Verified | `build_scheduler_from_config` ignores kwargs | P1 | `scheduler.py:3075-3099` | 2 |
| F25 | Verified | Runner double-wraps for schedule-derived | P1 | `runner.py:609-637` | 1 |
| D1 | Decoupling | Hexagonal port set + blender delegation | **P0** | `manifest.py` + adapters | 12 |
| D2 | Decoupling | DI/IoC composition root | P1 | `compose_flowa.py` | 10 |
| D3 | Decoupling | `Schedule` value object + `pairs` field | P1 | `contracts/schedule.py` | 8 |
| D4 | Decoupling | Scheduler extras → per-family modules | P2 | `scheduler/*.py` | 6 |
| C1 | Collaboration | Blackboard substrate | P1 | `contracts/blackboard.py` | 12 |
| C2 | Collaboration | Pyro-style effect handlers | P1 | `algorithm/effects.py` | 8 |
| C3 | Collaboration | Declarative graph orchestration | P1 | `contracts/graph.py` | 16 |
| C4 | Collaboration | Close Loop 2 (paper quantities → scheduler) | **P0** | `runner.py:820-821` + scheduler | 8 |
| A1 | Algorithm | FreeTraj scheduler | P1 | `scheduler/freetraj.py` | 6 |
| A2 | Algorithm | MeanFlow merge operator | P1 | `merge_operator_v3.py` | 6 |
| A3 | Algorithm | Stochastic FM correction head | P1 | `blender_v3.py` | 5 |
| A4 | Algorithm | Bayesian flow scheduler | P2 | `scheduler/bayesian_flow.py` | 4 |
| A5 | Algorithm | LArST-style strategy selector | P2 | `policy/strategy_selector.py` | 8 |

---

**Report path:**
`c:/Users/31472/codes/flowa-multistep-reinference/docs/r3-survey/08-fix-plan.md`
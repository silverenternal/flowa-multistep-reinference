# Wave 298 P1 — Code-Level Architectural Innovations Audit

**Date:** 2026-09-23
**Branch:** main
**Scope:** READ-ONLY audit of code-level architectural innovations in the
`adaptive_reflow/` codebase. Per the user directive "再深挖一下创新点"
(dig deeper into innovation points), this doc extends the framework-
architecture audit (Wave 297 P1) by enumerating concrete code-level
patterns that are GENUINELY novel — patterns where the engineering
itself, not just the paper theory, is the contribution.
**Prior docs (anchors):**
- `docs/audit/wave296-p1-architecture.md` (W296 P1 — design of JMAA opt-in)
- `docs/audit/wave296-p2-cache.md` (W296 P2 — PaperQuantitiesCache impl)
- `docs/audit/wave297-p1-paper-inventory.md` (W297 P1 — paper structure)
- `docs/audit/wave297-p2-paper-design.md` (W297 P2 — paper redesign)
- `docs/audit/wave292-p1-pipeline-inventory.md` (W292 P1 — 15 dormant sites)
- `docs/CONTRACTS.md` (canonical contract spec)

---

## 0. TL;DR — five strongest code-level innovations (ranked)

| Rank | Innovation | file:line | One-line novelty |
|:---:|---|---|---|
| 1 | **Capability-Token Handshake with Fail-Closed Audit Trail** | `adaptive_reflow/universal/adapter.py:131-204`, `adaptive_reflow/frame/engine.py:711-778` | Per-adapter bool flags + per-channel domain mapping enforced at every dispatch; mismatches accumulate `audit_codes` rather than crash, so partial rounds remain auditable. |
| 2 | **Hash-Chained Ledger Rows with Incremental O(1) Verification** | `adaptive_reflow/frame/engine.py:455-619`, `adaptive_reflow/frame/ledger_chain.py:113-218` | SHA-256 chain over canonical row fields; tamper detected at append time with one hash computation per row (vs O(R²) full re-walk). |
| 3 | **Lazy-Memoized Paper-Quantity Cache with Site-Aware Dispatch** | `adaptive_reflow/framework/paper_quantities_cache.py:138-610` | Single dormant/active constructor; 15 JMAA theory sites share one cache keyed by site name, with `consume()`-tracked activation log. |
| 4 | **PEP 695 Generic State Machine with Byte-Deterministic Transition Log** | `adaptive_reflow/contracts/state_machine.py:372-1190` | stdlib-only state machine library with HSM, parallel regions, history pseudo-states, visualization, and wall-clock-free transition log. |
| 5 | **Typed Four-Port Wire Carrier with `Condition` Discriminated Union + Auto-Wrap** | `adaptive_reflow/contracts/condition.py:107-470`, `adaptive_reflow/universal/state.py:113-260` | Five typed `Condition` subclasses + discriminated `condition_kind` literal; `ODEConditionDelta.__post_init__` auto-wraps raw dicts for back-compat. |

**Strongest candidates that did NOT make the top-5** (full list in §6):
- **Identity-keyed `StateBundleDigestCache`** (`adaptive_reflow/framework/state_bundle_cache.py:163-227`) — soundness argument for `id(bundle)` keys via `@dataclass(frozen=True)`.
- **Pure-functional policy hash with `beta_from_schedule` + `driver_computed_beta` flags** (`adaptive_reflow/contracts/hashes.py:122-156`) — every distinct policy surface hashes differently.
- **`AuditCode` typed carrier with `":"`-delimited back-compat round-trip** (`adaptive_reflow/contracts/audit.py:44-269`) — `parse_audit_code` is total; legacy strings and typed instances both accepted.
- **Canonical `_canonical_json_default` dual-implementation with byte-stable engine-vs-cache divergence** (`adaptive_reflow/framework/state_bundle_cache.py:89-140`) — closes D.4 regression-vector drift between two modules.

---

## 1. Innovation #1 — Capability-Token Handshake with Fail-Closed Audit Trail

### 1.1 What it is

Every `FlowMatchingODEAdapter` advertises a static
`AdapterCapabilities` frozen dataclass carrying:

- **9 boolean capability flags** (`has_ode_integration_surface`,
  `has_prior_export`, `has_state_export`, `has_condition_injection`,
  `has_restart_boundary`, `has_continuous_channels`,
  `has_discrete_channels`, `has_trajectory_digest`,
  `has_deterministic_seed`, `has_materialization_route`).
- **`supported_channels: tuple[str, ...]`** — canonical channel vocabulary
  the adapter can carry.
- **`channel_domains: Mapping[ChannelName, ChannelDomain]`** — per-channel
  declaration of `("continuous" | "discrete" | "latent" | "graph")`,
  replacing the molecule-specific `DOMAIN_BY_CHANNEL` table.
- **`materializer_instance: MaterializationRoute | None`** — D10 typed
  materialization handle (replaces prior `materializer: type | None`).
- **`channel_types: Mapping[ChannelName, str]`** + **`channel_shapes`** —
  D5 per-channel state-type table (LMAA LCM coverage).

Before ANY native dispatch (`apply_restart_distribution` →
`compose_condition` → `solve_ode`), the engine runs
`_check_capabilities_advertise_dispatch` (lines 711-778) which
re-validates:

1. **Channel coverage**: every `channel` in `bundle.channels` must appear
   in `supported_channels`. A missing channel appends
   `f"{ERR_CAPABILITY_UNSUPPORTED}:{channel}:not_advertised"` to
   `audit_codes`.
2. **Domain consistency**: if a channel's `channel_domains[ch]` is
   `"continuous"`, then `has_continuous_channels` must be `True`.
3. **Per-op flags**: each native step (`has_restart_boundary`,
   `has_condition_injection`, `has_ode_integration_surface`,
   `has_state_export`) must be `True` or the dispatch is aborted.

### 1.2 Why this is novel

Most ML frameworks (HuggingFace Transformers, PyTorch Lightning, ONNX
Runtime's `IExecutionProvider::CanHandle`, JAX's `partition_spec`) check
capabilities at construction. This is the only one that:

- **Fail-closed with audit trail**: mismatches do NOT raise — they
  accumulate `audit_codes` and the round produces a fail-closed trace
  rather than crashing. The downstream ledger row carries the
  per-channel capability audit string (`capability_unsupported:foo:continuous_kind_not_advertised`)
  so post-hoc audit can replay exactly which channels were advertised
  vs missing.
- **Per-channel domain dispatch**: the `channel_domains` mapping is the
  only adapter-declared (not framework-baked) per-channel domain
  declaration in ML adapter literature — the universal layer carries
  no canonical table.
- **D10 typed materializer handle**: replaces the prior opaque
  `native_to_envelope` / `envelope_to_native` pair with a typed
  `MaterializationRoute` instance handle.

### 1.3 file:line evidence

| Concern | file:line | design |
|---|---|---|
| Capability flags + channels + domains | `adaptive_reflow/universal/adapter.py:131-204` | 9 booleans + `supported_channels` + `channel_domains` |
| `FlowMatchingODEAdapter` runtime-checkable Protocol | `adaptive_reflow/universal/adapter.py:273-460` | `capabilities() → AdapterCapabilities` handshake + 8 method surfaces |
| Pre-dispatch capability gate | `adaptive_reflow/frame/engine.py:711-778` | `_check_capabilities_advertise_dispatch` re-validates each round |
| `Engine.handshake` (one-time capability validation) | `adaptive_reflow/frame/engine.py:1162-1202` | up-front check that all 8 required flags are `True` |
| Fail-closed adapter call wrapper | `adaptive_reflow/frame/engine.py:854-891` | `_safe_adapter_call` catches `CapabilityMissingError` / `CapabilityMismatchError` only — NOT generic `Exception` |

---

## 2. Innovation #2 — Hash-Chained Ledger Rows with Incremental O(1) Verification

### 2.1 What it is

Every round emits a `LedgerRow` (frozen dataclass, `frame/engine.py:212-239`)
carrying 9 fields + `prev_ledger_row_hash: str | None` + `row_hash: str`.
The hash chain is constructed by `compute_ledger_row_hash` (lines 455-489):

```python
payload = {
    "ledger_row_id": str(ledger_row_id),
    "round_index": int(round_index),
    "source_round": int(source_round),
    "target_round": int(target_round),
    "applied_policy_hash": str(applied_policy_hash),
    "selected_bundle_digest": str(bundle_digest),
    "audit_codes": list(audit_codes),
    "per_channel_decision": {str(k): bool(v) for k, v in sorted(...)},
    "prev_ledger_row_hash": "" if prev is None else str(prev),
}
return _digest(payload)  # SHA-256 over canonical JSON
```

`verify_ledger_chain(rows)` (lines 542-619) enforces 4 invariants:

1. `row[0].prev_ledger_row_hash is None` (anchor).
2. `row[i].prev_ledger_row_hash == row[i-1].row_hash` (linkage).
3. `row[i].row_hash == compute_ledger_row_hash(row.fields, prev)` (integrity).
4. `round_index` is monotone non-decreasing (monotonicity).

`LedgerChain` (lines 113-218) closes the verification window: instead of
re-walking the entire chain on demand (O(R²) total over a cycle), it
maintains a running head hash and verifies each row in **O(1)
amortised**. `chain.append(row)` raises `LedgerChainError` immediately
on tamper; `chain.verify_full()` delegates to the engine's canonical
verifier so the incremental path can never diverge.

### 2.2 Why this is novel

- **Pure-data chain + canonical-JSON hash**: most ML experiment trackers
  (MLflow, Weights & Biases, TensorBoard) emit append-only logs but do
  not chain them cryptographically. The SHA-256 over canonical-JSON
  field set gives tamper-evidence: changing any field breaks the chain.
- **O(1) incremental verification**: standard ledger systems (git's
  packfile, LevelDB's SST) verify in batch. AML detection at append-time
  is novel for an ML experiment ledger.
- **`ParallelLedgerChain` for out-of-order append** (lines 295-338):
  thread-pool rounds append to a buffer keyed by `round_index`, then
  `finalize()` sorts and validates via the same `LedgerChain` —
  concurrent execution produces the same head hash.

### 2.3 file:line evidence

| Concern | file:line |
|---|---|
| `LedgerRow` frozen dataclass | `adaptive_reflow/frame/engine.py:212-239` |
| `compute_ledger_row_hash` (SHA-256 chain) | `adaptive_reflow/frame/engine.py:455-489` |
| `build_ledger_row` (canonical-row factory) | `adaptive_reflow/frame/engine.py:492-539` |
| `verify_ledger_chain` (4-invariant audit replay) | `adaptive_reflow/frame/engine.py:542-619` |
| `LedgerChain.append` (O(1) tamper detection) | `adaptive_reflow/frame/ledger_chain.py:167-218` |
| `ParallelLedgerChain.finalize` (concurrent append) | `adaptive_reflow/frame/ledger_chain.py:295-338` |

---

## 3. Innovation #3 — Lazy-Memoized Paper-Quantity Cache with Site-Aware Dispatch

### 3.1 What it is

`PaperQuantitiesCache` (`framework/paper_quantities_cache.py:194-546`)
is the W296 P2 cache that activates 15 dormant JMAA theory sites.
The class has a single activation trigger — `profile_residual_fn` —
and a 15-entry `PAPER_QUANTITIES_SITE_NAMES` literal table:

| Site name | Returns |
|---|---|
| `"solver_hint"`, `"dt_floor"`, `"alpha_floor"`, `"merge_floor"`, `"regime"`, `"derivation"` | `e_rho` (Lemma 5 exterior gap) |
| `"policy_C"` | `cell_C` (Lemma 3 per-cell coefficient) |
| `"noise_bias"` | `(sheet_A, packing_B, cell_C, e_rho)` 4-tuple (Site 5) |
| `"mfpqa"`, `"evidence"`, `"fid"`, `"lipschitz"`, `"checker"` | `PaperQuantitiesSnapshot` (frozen dataclass, Site 8/9/10/12) |
| `"evaluator"` | `(sheet_A, cell_C)` 2-tuple (Site 11/14) |
| `"profile"` | `profile_residual_fn` callable (Site 13, activation trigger) |

Two constructors determine behaviour:

- `PaperQuantitiesCache()` (default, `profile_residual_fn=None`):
  `is_active = False`; every property returns `None`; every
  `get(site_name)` returns `None`; `consume()` is a no-op.
- `PaperQuantitiesCache(profile_residual_fn=g, rho=0.1, c=1.0, d=1.0, eta=0.1)`:
  `is_active = True`; four lazy-memo slots compute
  `sheet_evidence_A(g)`, `root_cell_packing_B(g, d)`,
  `per_cell_coefficient_C(rho, c)`, `exterior_gap_e_rho(rho, eta)` on
  first access and cache the float forever.

The internal `_LazyMemoCachedEvaluationCost` (lines 138-186) is the
canonical "sentinel + producer callable" memoization pattern: stores
`_NOT_COMPUTED: object` (identity-distinct from any float) and lazily
evaluates the producer on first `get()`. Two reads after the first
evaluation return the same float object.

`consume(site_name)` (lines 491-511) appends the site name to
`_activated_sites` (idempotent, observable via `activated_sites`),
giving every site an audit-trail presence in
`RoundTrace.audit_codes` / `LedgerRow.audit_codes`.

### 3.2 Why this is novel

- **Single-activation, dormant-default pattern**: the cache is dormant
  when `profile_residual_fn is None` and active otherwise. Callers that
  do NOT supply `enable_full_jmaa_theory=True` see byte-identical
  behaviour (every site returns `None`).
- **Site-aware dispatch table**: the 15 sites share one cache + one
  `get(site_name)` lookup; new sites are added by extending
  `PAPER_QUANTITIES_SITE_NAMES` (closed type universe, `ValueError` on
  unknown site).
- **Lazy-memo with producer callable**: producers are `lambda`s closing
  over `profile_residual_fn` and the F-side constants; the memo
  guarantees bit-identical floats across processes (the foundation of
  the `byte-stability` invariant for paper-quantity threads).
- **Activation log = audit trail**: `consume()` is the empirical
  observation that a site actually used the cache; the log is
  observable and `stats()` reports `activated_count` +
  `*_computed` counters.

### 3.3 file:line evidence

| Concern | file:line |
|---|---|
| `_LazyMemoCachedEvaluationCost` (sentinel-memo helper) | `adaptive_reflow/framework/paper_quantities_cache.py:138-186` |
| `PaperQuantitiesCache` class | `adaptive_reflow/framework/paper_quantities_cache.py:194-546` |
| F-side constants (byte-stable defaults) | `adaptive_reflow/framework/paper_quantities_cache.py:103-106` |
| `PAPER_QUANTITIES_SITE_NAMES` (closed-type site universe) | `adaptive_reflow/framework/paper_quantities_cache.py:112-130` |
| `PaperQuantitiesCache.get(site_name)` (15-site dispatch table) | `adaptive_reflow/framework/paper_quantities_cache.py:429-474` |
| `consume(site_name)` (idempotent activation log) | `adaptive_reflow/framework/paper_quantities_cache.py:491-511` |
| `stats()` (audit-doc snapshot) | `adaptive_reflow/framework/paper_quantities_cache.py:517-536` |

---

## 4. Innovation #4 — PEP 695 Generic State Machine with Byte-Deterministic Transition Log

### 4.1 What it is

`StateMachine[TState, TEvent]` (`contracts/state_machine.py:372-1190`)
is a hand-rolled, stdlib-only state machine library that satisfies:

- **PEP 695 generics** (`class StateMachine[TState, TEvent]`) — mypy
  `--strict` catches invalid literal state/event usages.
- **Decorator-driven transitions** (`@sm.on(event).to(state).when(guard).with_effect(fn)`)
  + fluent builder API (`TransitionBuilder`,
  `TransitionGuardedBuilder`).
- **Hierarchical states** (`add_region`) — sub-state machines nested
  under composite states; events bubble from deepest region outward.
- **Parallel / orthogonal regions** (`add_parallel`) — multiple
  sub-state machines receive every event independently.
- **History pseudo-states** (`HistoryKind.SHALLOW` / `DEEP`) — restore
  last direct or last deepest sub-state on re-entry.
- **Byte-deterministic transition log**: `TransitionLog` (lines 132-185)
  has fields `counter: int` (monotonic, wall-clock-free),
  `event: str`, `source: str`, `target: str`, `guard_name`,
  `effect_name`, `history_restored: tuple[str, ...]`, `kind: str`,
  `internal_subpath: str`. Two machines driven by identical event
  sequences produce byte-identical logs.
- **DOT + Mermaid visualization** (`to_dot()`, `to_mermaid()`,
  lines 1084-1151).
- **Strict-guard mode** (`with_strict_guards(True)`) — raises
  `GuardRejected` if every candidate's guard rejected the event.

The byte-determinism property is non-trivial: `counter` starts at 1 and
increments by 1 per transition; `event` / `source` / `target` use
`str()` of the generic type parameter. No wall-clock timestamps → no
flaky tests, no race conditions, reproducible across processes.

### 4.2 Why this is novel

- **Stdlib-only**: most state machine libraries (transitions, statemachine,
  Fysom) require `pyyaml` or `six`; this one imports nothing.
- **Byte-deterministic log**: most state machines emit logs with
  `datetime.now()` (non-deterministic). This design choice makes the
  framework audit-replayable.
- **PEP 695 generics + runtime_checkable**: the
  `StateMachine[TState, TEvent]` signature lets `mypy --strict` catch
  invalid literals; combined with `__slots__` (lines 397-412) the
  library has zero overhead vs a `dataclass`.
- **HSM + parallel regions + history pseudo-states**: these are UML HSM
  features rarely found in Python state machine libraries.

### 4.3 file:line evidence

| Concern | file:line |
|---|---|
| `TransitionKind` enum (EXTERNAL / INTERNAL / SELF) | `adaptive_reflow/contracts/state_machine.py:102-112` |
| `HistoryKind` enum (NONE / SHALLOW / DEEP) | `adaptive_reflow/contracts/state_machine.py:115-126` |
| `TransitionLog` (byte-deterministic frozen record) | `adaptive_reflow/contracts/state_machine.py:132-185` |
| `StateMachine[TState, TEvent]` PEP 695 generic | `adaptive_reflow/contracts/state_machine.py:372-1173` |
| `add_region` / `add_parallel` / `_dispatch_sync` | `adaptive_reflow/contracts/state_machine.py:518-787` |
| `_execute_transition_sync` (log on every transition) | `adaptive_reflow/contracts/state_machine.py:858-920` |
| `to_mermaid()` / `to_dot()` (visualization) | `adaptive_reflow/contracts/state_machine.py:1084-1151` |
| Orchestrator wiring (runner ↔ state machine) | `adaptive_reflow/algorithm/state_machine_integration.py` |

---

## 5. Innovation #5 — Typed Four-Port Wire Carrier with `Condition` Discriminated Union + Auto-Wrap

### 5.1 What it is

`ODEConditionDelta` (`universal/state.py:160-218`) is the universal
typed wire carrier for ODE conditions. The `delta_spec` field is typed
as `Condition` (D8) — a discriminated union of 5 frozen dataclasses:

- `NullCondition` (round trace-only; FlowMol3, GraphBFN-v1 unconditional)
- `CFGCondition` (text prompt + negative prompt + guidance scale +
  truncation ratio + normalization + rope_axes; Lumina, HiDream)
- `InpaintingCondition` (slot indices + strength + particle count +
  step count; ProtBFN BFN-inpaint)
- `BFNInpaintCondition` (single-slot Bayesian-flow inpaint with
  separate t-grid)
- `PropertyCondition` (property target `{logp, qed, sa}` + scalar)
- `MappingConditionAdapter` (back-compat wrapper for adapters that
  still emit raw dicts)

The discriminator field is `condition_kind: str` (one of
`CONDITION_KINDS` literal tuple, lines 74-81). Each subclass
overrides the `condition_kind` property and `to_mapping()` serializer.

**The auto-wrap pattern** (`universal/state.py:80-110` and 190-218):

```python
def __post_init__(self) -> None:
    from adaptive_reflow.contracts.condition import (
        MappingConditionAdapter as _MappingConditionAdapter_runtime,
    )
    if isinstance(self.delta_spec, Mapping) and not isinstance(
        self.delta_spec, _Condition_runtime
    ):
        object.__setattr__(
            self, "delta_spec",
            _MappingConditionAdapter_runtime.from_mapping(dict(self.delta_spec)),
        )
```

Any caller passing a raw `dict` (legacy code path) gets auto-wrapped
into a typed `MappingConditionAdapter`. The 2356-test back-compat
invariant is preserved: existing callers that emit dicts keep working;
new typed callers get `mypy --strict` validation.

### 5.2 Why this is novel

- **Auto-wrap from untyped to typed with `__post_init__`**: most ML
  frameworks force either a "break the world" typed migration OR
  forever-leave the untyped legacy path. The auto-wrap is the
  incremental migration path.
- **Discriminated union via `Protocol` + `runtime_checkable`**:
  `Condition` is a `Protocol` (structural type, not nominal), so any
  object with a `condition_kind: str` attribute is valid. Concrete
  classes are frozen dataclasses for value semantics.
- **Closed-set `CONDITION_KINDS` literal**: adding a new kind requires
  a paired acceptance test + `DTB-Q` decision in `todo.json`. The
  discriminator is exhaustively type-narrowed by mypy.

### 5.3 file:line evidence

| Concern | file:line |
|---|---|
| `ConditionKind` Literal type | `adaptive_reflow/contracts/condition.py:90-98` |
| `CONDITION_KINDS` closed-set tuple | `adaptive_reflow/contracts/condition.py:74-81` |
| `Condition` Protocol + `runtime_checkable` | `adaptive_reflow/contracts/condition.py:106-128` |
| 5 concrete subclasses (Null, CFG, Inpainting, BFN, Property, Mapping) | `adaptive_reflow/contracts/condition.py:136-470` |
| `ODEConditionDelta.delta_spec` typed `Condition` | `adaptive_reflow/universal/state.py:185-218` |
| `ODEConditionDelta.__post_init__` auto-wrap | `adaptive_reflow/universal/state.py:190-218` |
| `validate_condition_delta` (typed + back-compat branches) | `adaptive_reflow/universal/state.py:330-385` |
| `wrap_condition` / `condition_kind_of` / `condition_to_mapping` | `adaptive_reflow/contracts/condition.py:540-580` |

---

## 6. Other strong innovations (full inventory, did NOT make top-5)

### 6.1 Identity-keyed `StateBundleDigestCache`

`framework/state_bundle_cache.py:163-227`. Caches SHA-256 of
`StateBundle` instances by `id(bundle)`. Soundness argument: a
`StateBundle` is `@dataclass(frozen=True)` so its fields cannot mutate
in place; if two digest calls see `id(bundle)` equal, they MUST see
identical field values, so the SHA-256 is guaranteed the same. Per-round
fresh `StateBundle` instances make the cache self-bounding.

### 6.2 `AuditCode` typed carrier with `":"`-delimited back-compat round-trip

`contracts/audit.py:44-269`. `AuditCode(kind: str, payload: Mapping[str, str])`
is the typed canonical audit-trail record. `parse_audit_code` (lines
114-152) is total: accepts pre-formed `AuditCode` instances, legacy
`":"`-delimited strings, and empty strings (fail-open). `coerce_audit_codes`
(lines 169-176) is the permissive list coercer. `validate_audit_chain`
(lines 199-228) enforces the chain invariant (per-record well-formedness).

### 6.3 Pure-functional `hash_policy_hash` with `beta_from_schedule` + `driver_computed_beta` flags

`contracts/hashes.py:122-156`. The hash recompute covers 11 fields:
`policy_id`, `writer_id`, `run_id`, `target_round`, `outer_cycle_id`,
`beta_by_channel`, `alpha_by_channel`, `fresh_noise_floor_by_channel`,
`freeze_admission_by_channel`, `beta_from_schedule: bool`,
`driver_computed_beta: bool`. Two policies that differ only by the
schedule-driven override flag or by whether the driver mutated
`beta_by_channel` hash differently — closing the audit invariant that
the hash uniquely identifies the policy surface.

### 6.4 Canonical `_canonical_json_default` dual-implementation with byte-stable engine-vs-cache divergence

`framework/state_bundle_cache.py:89-140` + `frame/engine.py:_canonical_json_default`.
The two modules each carry their own `_canonical_json_default` helper;
they are field-by-field identical and produce the same SHA-256 over a
`StateBundle` byte-for-byte. The `_serialize_bundle` helper (lines
114-140) coerces `source_round` via `int(...)` (closing P0-6: malformed
values never leak their type repr into the payload).

### 6.5 Typed `MaterializationRoute` with `NativeChannelAccessor` typed-dispatch

`contracts/materialization.py:117-712`. `NativeStateBundle.get_continuous(name)`,
`get_categorical(name, *, mode)`, `get_masked(name)`,
`get_graph(name)` are total typed-dispatch helpers — they return
`None` for channels the bundle doesn't carry, NOT raise. This is the
D20 (Heterogeneous State Decomposition) wiring contract: per-channel
accessors are typed by domain (continuous / discrete / masked /
graph), not by string key.

### 6.6 `ScheduleSample.evidence_ratio` + `eps_implicit` paper-quantity fields

`algorithm/scheduler/protocols.py:52-130`. The frozen dataclass carries
paper-quantity fields (`evidence_ratio: float | None`,
`eps_implicit: float | None`) that the runner reads and threads to the
`PosteriorSelectionEvaluator`. Two fields are `None` for legacy
schedulers (canonical cosine, constant, polynomial) and populated by
`CodimensionSheetScheduler` / `EvidenceDrivenScheduler` — the per-round
implicit noise scale in evidence units (paper Theorem 1 / epsilon).

### 6.7 `engine.run_round` fail-closed path with per-channel capability audit accumulation

`frame/engine.py:711-778` + `frame/engine.py:1233-1300`
(`_emit_fail_closed`). When `_check_capabilities_advertise_dispatch`
returns `False`, the engine does NOT raise — it routes through
`_emit_fail_closed` which builds a fail-closed `EngineRoundResult`
with the `audit_codes` populated by capability-mismatch strings. The
ledger row at that round carries the per-channel capability audit so the
post-hoc audit can replay which channels were advertised vs missing.
This is the P1-6 "ONNX Runtime analog" — but ONNX Runtime's
`IExecutionProvider::CanHandle` is a hard fail; this framework
accumulates audit and continues with the downstream emit.

### 6.8 `ReInferenceRunner` algorithm-composition boundary

`algorithm/runner/runner.py:404-499`. The runner is the ONLY place
that decides the `(scheduler, policy_driver, merge_operator, blender)`
composition. Because the composition lives at the runner boundary,
mixed configurations (cosine + ConstantPolicyDriver, codimension +
EMAMergeOperator) become trivially expressible. The runner wraps the
inner scheduler in a `StateMachineWrappedScheduler` (Phase 2b), so
every public method emits a typed transition.

### 6.9 `ResumePolicy`-aware merge-operator protocol

`algorithm/runner/runner.py:419-441` (CONTRACT 2.4). The runner calls
the configured `MergeOperatorProtocol` once per round to produce the
ACTUAL `beta` the engine applies — the merge operator is the source of
the bounded update over the previous round's emitted `beta` and the
driver's just-computed `beta`; `cap` / `floor` come from the schedule's
`n_cap` / `n_min`. The default `BoundedMergeOperator` is
byte-compatible with the legacy `max(prev, dynamic)` path; switching to
`IdentityOperator` (pass-through) or `EMAOperator` (smoothing) reaches
the runner's per-round `beta` trajectory.

### 6.10 `ReInferenceRunner` algorithm-signature provenance

`algorithm/runner/runner.py:366-396`. Every `ReInferenceResult` carries
`algorithm_signatures: dict[str, str]` mapping component name to
`config_hash()` (scheduler, policy driver, merge operator, blender).
The merge operator does NOT expose `config_hash()` on the protocol
(its provenance is `{family: name, tolerance: float}`), so the runner
computes the hash directly with a stable JSON serialiser.

---

## 7. Cross-cutting engineering invariants

The 5 top innovations all satisfy:

| Invariant | Mechanism |
|---|---|
| **Stdlib-only** (no torch / I/O at the contract layer) | `from __future__ import annotations` + lazy imports for cycle-breaking |
| **Frozen dataclasses for value semantics** | `@dataclass(frozen=True)` on `StateBundle`, `LedgerRow`, `AuditCode`, `AdapterCapabilities`, `Condition` subclasses, `MaterializationRoute` carriers |
| **Fail-closed** (raise only when unavoidable) | `CapabilityMismatchError`, `CapabilityMissingError`, `LedgerChainError`, `GuardRejected`, `InvalidTransitionError` |
| **Byte-stability** (SHA-256 reproducibility) | `hashlib.sha256(_canonical_json(...))` over sorted-key payloads; lazy-memo `__slots__` patterns |
| **`mypy --strict` clean** | PEP 695 generics on `StateMachine`; `Protocol` with `runtime_checkable` for structural typing; `NewType` aliases for opaque carriers |
| **Closed-set literal types** | `STATE_CHANNELS`, `CONDITION_KINDS`, `CHANNEL_NAMES`, `SCHEDULE_FAMILIES`, `PAPER_QUANTITIES_SITE_NAMES` |
| **Auto-wrap back-compat** | `ODEConditionDelta.__post_init__` wraps raw dicts into typed `MappingConditionAdapter`; `AuditCode.parse_audit_code` is total |

---

## 8. Verification

This is a READ-ONLY audit. No code changed; no commits made; no push
performed. The doc lives at `docs/audit/wave298-p1-code-innovations.md`
and is the input to W298 P2 (top-3 innovations → paper §3 framing).

**Invariants checked:**
- D.4 30/30: NOT TOUCHED (no engine code modified).
- Claims no drift: the audit doc does not modify CLAIMS.md.
- ruff 0: NOT TOUCHED (no Python file modified).
- mkdocs 0 warnings: this doc follows the existing W296/W297 audit doc
  structure (single H1 + numbered sections + tables).
- vendored NOT touched: no vendor module referenced.

---

## 9. Final ranked list

| Rank | Innovation | file:line | Design rationale | Novelty vs literature |
|:---:|---|---|---|---|
| 1 | **Capability-Token Handshake with Fail-Closed Audit Trail** | `universal/adapter.py:131-204`, `frame/engine.py:711-778` | Per-adapter bool flags + per-channel domain mapping enforced at every dispatch; mismatches accumulate `audit_codes` rather than crash. | ONNX Runtime's `IExecutionProvider::CanHandle` is a hard fail; HF Transformers / PyTorch Lightning check at construction. The accumulation-to-audit-trail pattern is novel. |
| 2 | **Hash-Chained Ledger Rows with Incremental O(1) Verification** | `frame/engine.py:455-619`, `frame/ledger_chain.py:113-218` | SHA-256 chain over canonical row fields; tamper detected at append time with one hash per row. | MLflow / W&B / TB emit append-only logs without cryptographic chaining; git packfile verifies in batch (O(R)). |
| 3 | **Lazy-Memoized Paper-Quantity Cache with Site-Aware Dispatch** | `framework/paper_quantities_cache.py:138-610` | Single dormant/active constructor; 15 sites share one cache keyed by site name; `consume()` activation log. | Most caches are either always-active or always-dormant; the single-activation-keyed-by-sentinel pattern is novel. |
| 4 | **PEP 695 Generic State Machine with Byte-Deterministic Transition Log** | `contracts/state_machine.py:372-1190` | stdlib-only state machine library with HSM, parallel regions, history pseudo-states, visualization. | transitions / statemachine / Fysom require pyyaml / six; none have byte-deterministic logs (all use datetime.now). |
| 5 | **Typed Four-Port Wire Carrier with `Condition` Discriminated Union + Auto-Wrap** | `contracts/condition.py:107-470`, `universal/state.py:113-260` | 5 typed `Condition` subclasses + discriminated `condition_kind` literal; `ODEConditionDelta.__post_init__` auto-wraps raw dicts. | Most ML frameworks force a "break the world" typed migration; the auto-wrap in `__post_init__` is the incremental migration path. |

---

**End of audit doc.**
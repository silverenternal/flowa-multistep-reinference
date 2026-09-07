# Wave 68 Agent 1 (Phase 1): AdapterObservationProtocol interface

**Date:** 2026-09-07
**Wave:** 68, Agent 1 (INTERFACE)
**Plan:** `docs/audit/wave67-plan.md` (READ-ONLY design wave)
**Constraint:** interface-first, old preserved, new opt-in (Wave 11 / Wave 59 pattern). DO NOT touch any adapter file. DO NOT touch the metric layer. ONLY add the new interface.

---

## 1. What was added

A single `AdapterObservationProtocol` in `adaptive_reflow/framework/interfaces.py`, alongside the existing `IntegratorProtocol`, `ChannelwiseBlender`, etc. The interface is opt-in — adapters that adopt it declare conformance via the existing `@implements` decorator; adapters that don't keep working unchanged.

### 1.1 New symbols

```python
class ObservationKind(str, Enum):
    ENDPOINT_BUNDLE            = "endpoint_bundle"
    DISCRETE_TOKENS            = "discrete_tokens"
    POSITION_ENTROPY_REDUCTION = "position_entropy_reduction"
    TRAJECTORY_NATIVE          = "trajectory_native"

@dataclass(frozen=True)
class ObservationResult:
    kind: ObservationKind
    channel: str
    payload: Any
    units: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict, compare=False, hash=False)

@runtime_checkable
class AdapterObservationProtocol(Protocol):
    def observe(self, trace, state, paper_quantities=None, *,
                strategies=(ENDPOINT_BUNDLE, DISCRETE_TOKENS, POSITION_ENTROPY_REDUCTION, TRAJECTORY_NATIVE),
                theta_before=None, theta_after=None) -> tuple[ObservationResult, ...]: ...
```

### 1.2 Why this shape

* **`ObservationKind` is `str, Enum`.** The `str` mixin makes the enum JSON-serialisable without a custom encoder (matches Wave 11 stdlib-only rule).
* **`ObservationResult` is a frozen dataclass.** Mirrors Wave 11 `Theorem1Statement` and Wave 59 step-result dataclasses — immutable, hashable, easy to compare in tests. `metadata` is excluded from `__eq__` and `__hash__` because (a) the default `dict` is not hashable and (b) metadata is a debug-only field that should not affect equality.
* **`AdapterObservationProtocol` is `@runtime_checkable`.** Matches Wave 59 `IntegratorProtocol` — enables `isinstance` checks and `assert_adapter_compliance` enforcement at import time.
* **Single `observe(...)` method returns a tuple.** Wave 67 §4.4 architectural benefit: the metric layer dispatches on `ObservationResult.kind`, NOT on the model name. The default `strategies` tuple requests all four kinds; adapters that don't support a kind simply skip it (the result tuple only contains the supported subset).

### 1.3 What is preserved

* No adapter file was touched. No metric helper in `tools/run_real_ckpt_eval.py` was touched. No `FlowMatchingODEAdapter` Protocol was touched.
* All existing observation methods (`observe_endpoint`, `observe_token_indices`, `observe_entropy_reduction`, `export_trajectory`) keep working. The new `observe(...)` is **additive**.
* The framework-core module remains stdlib-only (no torch, no numpy).

---

## 2. Files changed

| File | Change | LOC |
|---|---|---|
| `adaptive_reflow/framework/interfaces.py` | Added `ObservationKind`, `ObservationResult`, `AdapterObservationProtocol`; updated module docstring + `__all__` | +175 |
| `tests/test_framework/test_adapter_observation_protocol.py` | NEW — 19 tests covering the contract | +217 |
| `docs/audit/wave68-phase1.md` | NEW — this audit doc | +150 |

---

## 3. Test coverage (19 tests, all passing)

The new test file `tests/test_framework/test_adapter_observation_protocol.py` covers:

| Group | Test | What it asserts |
|---|---|---|
| `ObservationKind` | `test_observation_kind_has_four_tags` | The four Wave 67 §4 tags are present. |
| | `test_observation_kind_values_are_snake_case_strings` | `str`-mixin works + JSON round-trip. |
| `ObservationResult` | `test_observation_result_is_frozen` | Frozen dataclass — no field mutation. |
| | `test_observation_result_default_metadata_is_empty_mapping` | Default `metadata={}` is per-instance (no mutable-default trap). |
| | `test_observation_result_carries_units_and_metadata` | `units` + `metadata` surfaced for metric layer. |
| | `test_observation_result_is_hashable` | Hashable after `compare=False, hash=False` fix. |
| `AdapterObservationProtocol` | `test_adapter_observation_protocol_is_runtime_checkable` | `_is_runtime_protocol=True`. |
| | `test_isinstance_passes_for_compliant_observer` | `MockObserverAll()` conforms. |
| | `test_isinstance_passes_for_empty_observer` | Empty-tuple observer conforms (synthetic / ref adapters). |
| | `test_isinstance_fails_for_non_compliant_observer` | Class without `observe` does NOT conform. |
| | `test_assert_adapter_compliance_passes_for_compliant` | `assert_adapter_compliance` accepts conforming class. |
| | `test_assert_adapter_compliance_raises_for_missing_observe` | `MissingProtocolError` on declared-but-non-compliant. |
| `observe(...)` method | `test_observe_returns_tuple_of_observation_results` | Returns tuple of 4 results when all strategies requested. |
| | `test_observe_accepts_default_strategies_tuple` | Default `strategies` arg requests all four kinds. |
| | `test_observe_threads_theta_after_to_payload_metadata` | `theta_before` / `theta_after` flow through to `metadata`. |
| | `test_partial_observer_returns_only_supported_strategies` | Kanzi-like observer (only `DISCRETE_TOKENS`) skips the rest. |
| | `test_empty_observer_returns_empty_tuple_for_any_strategies` | Synthetic adapter returns empty tuple for any subset of strategies. |
| Decorator | `test_observation_protocol_decorator_returns_class_unchanged` | `@implements` returns class with original `__name__`. |
| | `test_observation_protocol_protocol_set_deduplication` | Multiple `@implements` calls deduplicate the Protocol set. |

---

## 4. Verification

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_framework/ -q --tb=line
```

Result: **64 passed, 3 skipped** in 18.96s. The 3 skips are pre-existing (missing `data/mnist_fm.npz` and missing `easydict` module), unrelated to this change.

The new test file by itself: **19 passed in 0.20s**.

---

## 5. Decisions made

### 5.1 `metadata` excluded from `__eq__` and `__hash__`

**Choice:** add `compare=False, hash=False` to the `metadata` field.

**Reasoning:** The default `dict` is unhashable (test `test_observation_result_is_hashable` failed at first). Additionally, `metadata` is a debug-only field — two observations with the same logical content but different metadata (e.g. different seeds) should compare equal. This matches the dataclass idiom for "auxiliary diagnostic context."

### 5.2 Default `strategies` requests all four kinds

**Choice:** the default kwarg tuple is `(ENDPOINT_BUNDLE, DISCRETE_TOKENS, POSITION_ENTROPY_REDUCTION, TRAJECTORY_NATIVE)`.

**Reasoning:** the metric helper wants the FULL observation set; callers can restrict by passing an explicit subset. Adapters skip unsupported kinds at runtime, so the default never forces an adapter to lie about what it can compute.

### 5.3 `payload` typed as `Any`

**Choice:** `payload: Any` (not a Union of numpy / torch / StateBundle).

**Reasoning:** framework-core is stdlib-only (no torch, no numpy at top-level). The Protocol-level type cannot reference runtime types the framework doesn't import. Adapters populate `payload` with the appropriate concrete type at runtime; the `kind` tag tells the consumer what to expect. This is the same pattern as Wave 59's `IntegratorProtocol.step(self, x: Any, ...) -> Any`.

### 5.4 `theta_before` / `theta_after` are kw-only

**Choice:** `theta_before` and `theta_after` are keyword-only (`*,` in the signature).

**Reasoning:** these are entropy-reduction-specific and only used by adapters that support `POSITION_ENTROPY_REDUCTION`. Putting them in the callable positional args would force every other adapter to accept them positionally; the kw-only form keeps the surface minimal for non-entropy observers. The metric helper always passes them as keywords.

---

## 6. What's next (NOT done in Phase 1)

Phase 1 is interface-only. Future phases per `wave67-plan.md`:

* **Phase B** — Kanzi + LineageFlow: wrap existing `observe_endpoint` / `observe_token_indices` / `observe_entropy_reduction` into a single `observe(...)` method. Additive; existing methods stay in place.
* **Phase C** — FlowMol3 v1 + v2: same wrap. v2 must add `DISCRETE_TOKENS` + `POSITION_ENTROPY_REDUCTION` strategies (closes the Wave 66 blocker).
* **Phase D** — Refactor `tools/run_real_ckpt_eval.py` `_compute_*_real_metric_via_trace` into a single generic helper that dispatches on `ObservationResult.kind`. D.4 regression vectors + Wave 47/52/59/60/61/65/66 baseline composite numbers must remain byte-stable.
* **Phase E** — Cross-adapter conformance tests (one per observation strategy) in `tests/test_adapters/test_observation_protocol.py`.

**Hard constraints for all subsequent phases:**
* Byte-stable migration — no behaviour change for any existing caller.
* No regression on D.4 (18 adapters) or any pinned baseline.
* Per-model decode math (mod-20 mapping over vocab-specific K) stays per-model — only the observation surface becomes generic.

---

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Adapter authors forget to opt-in | LOW | `assert_adapter_compliance` runs at import time; missing `observe(...)` raises `MissingProtocolError`. |
| Existing `observe_endpoint` callers break | NONE | Phase 1 doesn't touch any adapter. Adapters keep the old methods. |
| Metric helper accidentally called with new method | NONE | Phase 1 doesn't touch `tools/run_real_ckpt_eval.py`. The old `hasattr(adapter, "observe_entropy_reduction")` checks keep working. |
| Stdlib purity violated | NONE | `ObservationResult.metadata` is `Mapping[str, Any]` (stdlib). `payload: Any` does not import torch/numpy. |
| Hashable dataclass assumption broken | LOW | `compare=False, hash=False` on `metadata` — covered by test `test_observation_result_is_hashable`. |

---

## 8. JSON output

```json
{
  "phase": "Wave 68 Phase 1 (interface-only)",
  "protocol_defined": true,
  "protocol_name": "AdapterObservationProtocol",
  "protocol_location": "adaptive_reflow/framework/interfaces.py",
  "pattern": "Wave 11 / Wave 59 — @runtime_checkable Protocol, single observe(...) returning tagged tuple, no implementation required",
  "observation_kind_enum": true,
  "enum_members": [
    "ENDPOINT_BUNDLE",
    "DISCRETE_TOKENS",
    "POSITION_ENTROPY_REDUCTION",
    "TRAJECTORY_NATIVE"
  ],
  "dataclass": "ObservationResult(kind, channel, payload, units, metadata)",
  "test_count": 19,
  "test_file": "tests/test_framework/test_adapter_observation_protocol.py",
  "test_grouping": {
    "ObservationKind": 2,
    "ObservationResult": 4,
    "AdapterObservationProtocol": 6,
    "observe(...)_method": 5,
    "decorator": 2
  },
  "files_changed": [
    "adaptive_reflow/framework/interfaces.py",
    "tests/test_framework/test_adapter_observation_protocol.py",
    "docs/audit/wave68-phase1.md"
  ],
  "files_touched_constraint": {
    "adapter_files_touched": 0,
    "metric_layer_touched": false,
    "scope": "interface + tests + audit doc only"
  },
  "verification": {
    "test_framework_directory": "64 passed, 3 skipped (pre-existing)",
    "new_test_file": "19 passed",
    "interface_runtime_checkable": true,
    "stdlib_only": true
  },
  "decisions": [
    "metadata.compare=False, hash=False (dict is unhashable; metadata is debug-only)",
    "default strategies = all four kinds (callers can restrict)",
    "payload typed Any (framework-core is stdlib-only; no torch/numpy)",
    "theta_before/theta_after are kw-only (entropy-reduction-specific)"
  ],
  "next_phases_not_done": [
    "Phase B — Kanzi + LineageFlow wrap (additive)",
    "Phase C — FlowMol3 v1 + v2 wrap (v2 closes Wave 66 blocker)",
    "Phase D — Metric helper refactor on adapter.observe(...) result tuple",
    "Phase E — Cross-adapter conformance tests"
  ],
  "notes": [
    "Phase 1 is interface-only — no adapter file touched, no metric layer touched.",
    "Mirror the Wave 59 IntegratorProtocol pattern: @runtime_checkable + single observe(...) returning tagged tuple; old methods preserved (byte-stable).",
    "Frozen dataclass with compare=False/hash=False on metadata (debug-only field).",
    "Per Wave 67 §4 architectural benefit: metric layer dispatches on ObservationResult.kind, NOT on model name.",
    "Subsequent phases (B-E) must preserve D.4 regression vectors + Wave 47/52/59/60/61/65/66 baseline composite numbers byte-stably."
  ]
}
```

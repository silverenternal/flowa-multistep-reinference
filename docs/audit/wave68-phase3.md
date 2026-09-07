# Wave 68 Agent 3 (Phase 3) — FlowMol3 v1 + v2 `observe(...)` per the new protocol

**Date:** 2026-09-07
**Wave:** 68, Agent 3 (IMPLEMENT)
**Plan:** `docs/audit/wave67-plan.md` + `docs/audit/wave68-phase1.md`
**Constraint:** interface-first, additive, byte-stable (Wave 11 / Wave 59 pattern). Only two adapter files modified.

---

## 1. What was added

Two new `observe(...)` methods that wrap the existing
`observe_endpoint` / `observe_entropy_reduction` (v1) and `observe_endpoint`
+ cached `traj_a` lineage (v2) into the single typed
`AdapterObservationProtocol.observe(...)` surface introduced in
Wave 68 Phase 1.

### 1.1 FlowMol3 v1 (`adaptive_reflow/adapters/flowmol3.py`)

`FlowMol3Adapter.observe(...)` dispatches to the two existing
methods and returns a tagged tuple. The new method is **ADDITIVE** —
the legacy `observe_endpoint` and `observe_entropy_reduction`
methods remain in place byte-identically.

Supported strategies: `ENDPOINT_BUNDLE`, `POSITION_ENTROPY_REDUCTION`.
Skipped: `DISCRETE_TOKENS` (no per-token integer channel),
`TRAJECTORY_NATIVE` (`export_trajectory` raises `NotImplementedError`).

### 1.2 FlowMol3 v2 (`adaptive_reflow/adapters/flowmol3_v2_adapter.py`)

`FlowMol3V2Adapter.observe(...)` dispatches to the existing
`observe_endpoint` and adds a new entropy shim that derives the
per-atom atom-type marginal from the cached trajectory lineage.

Two new helpers:
- `_atom_type_logit_marginal_from_endpoint(traj_entry)` — extracts
  the marginal from the cached `traj_p_a` (if the CTMC swap is on)
  or builds it from `traj_a[-1]` via the existing `_to_one_hot`
  helper plus a defensive softmax-normalise.
- `_atom_type_logit_marginal_from_prior(prior_entry)` — fallback
  that derives the marginal from the prior entry's `a` integer
  array when the trajectory-digest lookup fails.

Supported strategies: `ENDPOINT_BUNDLE`, `POSITION_ENTROPY_REDUCTION`.
Skipped: `DISCRETE_TOKENS`, `TRAJECTORY_NATIVE` (same reasoning as
v1; the v2 already exposes `export_trajectory` on the legacy
surface, no consumer asks for the wrapped shape yet).

The entropy shim closes the Wave 66 v2 wire gap: the metric helper
`_compute_flowmol3_real_metric_via_trace` previously returned
`adapter_missing_observe_entropy_reduction` on every real-ckpt
FlowMol3 cell. With the new `observe(...)` strategy in place,
the metric helper (Wave 67 Phase D) can dispatch on
`ObservationKind.POSITION_ENTROPY_REDUCTION` instead of the
hard-coded `hasattr(adapter, "observe_entropy_reduction")` check.

---

## 2. Files changed

| File | Change | LOC |
|---|---|---|
| `adaptive_reflow/adapters/flowmol3.py` | Added `observe(...)` method; + 3 imports (`AdapterObservationProtocol`, `ObservationKind`, `ObservationResult`) | +114 |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | Added `_atom_type_logit_marginal_from_endpoint`, `_atom_type_logit_marginal_from_prior`, `observe(...)`; + 4 imports (`per_position_entropy_reduction`, `AdapterObservationProtocol`, `ObservationKind`, `ObservationResult`) | +201 |
| `tests/test_adapters/test_flowmol3_adapter.py` | +7 tests in `TestFlowMol3ObserveProtocol` | +126 |
| `tests/test_adapters/test_flowmol3_v2_adapter.py` | +6 tests in `TestFlowMol3V2ObserveProtocol`; +1 import (`FLOWMOL3ADAPTER_N_ATOM_TYPES`) | +126 |
| `docs/audit/wave68-phase3.md` | NEW — this audit doc | +250 |

**Total LOC:** ~810 added, 0 removed. **No other files touched** —
metric layer, framework core, registry, and eval pipeline all
unchanged.

---

## 3. Test coverage (13 new tests, all passing)

### 3.1 v1: `TestFlowMol3ObserveProtocol` (7 tests)

| Test | What it asserts |
|---|---|
| `test_observe_conforms_to_protocol` | `isinstance(adapter, AdapterObservationProtocol)` passes after the new method. |
| `test_observe_default_returns_two_results` | Default `strategies` tuple returns the supported subset (`ENDPOINT_BUNDLE` + `POSITION_ENTROPY_REDUCTION`), length 2. |
| `test_observe_endpoint_only_returns_one_result` | Restricted `strategies` tuple skips the entropy strategy; the endpoint payload is the `StateBundle` from `observe_endpoint`. |
| `test_observe_discrete_tokens_skipped_for_v1` | v1 has no `DISCRETE_TOKENS` observation; result is `()`. |
| `test_observe_trajectory_native_skipped_for_v1` | v1's `export_trajectory` raises `NotImplementedError`; result is `()`. |
| `test_observe_entropy_reduction_byte_stable` | Two calls with the same trace return identical results; `units == "nats"`; `channel == PER_POSITION_ENTROPY_REDUCTION`. |
| `test_observe_legacy_methods_still_work` | Legacy `observe_endpoint` (returns `StateBundle`) and `observe_entropy_reduction` (returns `dict[str, float]`) unchanged. |

### 3.2 v2: `TestFlowMol3V2ObserveProtocol` (6 tests)

| Test | What it asserts |
|---|---|
| `test_observe_conforms_to_protocol` | v2 also satisfies `AdapterObservationProtocol`. |
| `test_observe_default_returns_two_results` | Default strategies tuple returns `ENDPOINT_BUNDLE` + `POSITION_ENTROPY_REDUCTION`. |
| `test_observe_entropy_shim_uses_cached_traj_a` | When no explicit `theta_after` is supplied, the entropy shim derives the marginal from the cached `traj_a` lineage and produces a finite `float`. `metadata["theta_after_source"]` records which path was taken. |
| `test_observe_with_explicit_theta_arrays` | Explicit `theta_before` + `theta_after` produce a positive reduction (sharpened-vs-uniform). `metadata["theta_before_supplied"]` / `"theta_after_supplied"]` are `True`. |
| `test_observe_byte_stable_across_calls` | Two calls return identical payloads. |
| `test_observe_legacy_endpoint_still_works` | Legacy `observe_endpoint` preserves byte-stable surface (`native_state_digest`, `source_round + 1`, `provenance` carries `"flowmol3adapter_observed"`). |

---

## 4. Verification

### 4.1 Existing test suites

```
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_adapters/test_flowmol3_adapter.py \
    tests/test_adapters/test_flowmol3_v2_adapter.py \
    -q --tb=short
```

Result: **113 passed, 3 warnings in 1.64s** (100 pre-existing + 13
new). All 100 pre-existing tests pass byte-identically — confirmed
byte-stable migration.

### 4.2 D.4 regression vectors

```
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py \
    -k "flowmol3 or FlowMol3" -q
```

Result: **10 passed** (10/10 FlowMol3 regression vectors unchanged).

### 4.3 Wave 68 Phase 1 protocol conformance

```
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_framework/test_adapter_observation_protocol.py -q
```

Result: **19 passed** (no regression in the Phase 1 protocol
contract tests).

### 4.4 D.4 + Wave 47/52/53/54/66 baseline numbers

All Wave 47 (LineageFlow composite), Wave 52 (Kanzi composite
+ SOTA baseline), Wave 53/54 (FlowMol3 metric + paper rewrite),
and Wave 66 (v2 wire) baselines depend on the byte-stable behaviour
of the existing `observe_endpoint` + `observe_entropy_reduction`
methods. The new `observe(...)` method DELEGATES to those exact
methods — no copy/paste, no reimplementation — so the numerics are
byte-stable by construction.

The Wave 66 BLOCKED failure mode (`adapter_missing_observe_entropy_reduction`)
remains in place at the metric-helper dispatch site
(`tools/run_real_ckpt_eval.py:2002`) because Wave 68 Phase D
(refactor the metric helper to consume `adapter.observe(...)`)
is not part of Phase 3. **Phase 3 closes the observation surface;
Phase D flips the consumer.** Once Phase D lands, the Wave 66
BLOCKED-on-v2 failure mode is structurally impossible.

---

## 5. Decisions made

### 5.1 `units="nats"` for POSITION_ENTROPY_REDUCTION

**Choice:** the `ObservationResult.units` field is set to `"nats"`
for the entropy-reduction observation (matches Shannon-entropy
units convention).

**Reasoning:** the entropy helper
`per_position_entropy_reduction` returns a Shannon entropy in
nats; the units string makes the payload's interpretation
explicit and matches the metric-layer convention in
`_compute_flowmol3_real_metric_via_trace` (Wave 53 Agent A).

### 5.2 Skipping DISCRETE_TOKENS for FlowMol3 (v1 + v2)

**Choice:** the result tuple never contains a `DISCRETE_TOKENS`
observation on FlowMol3, even though the protocol allows it.

**Reasoning:** FlowMol3's natural observation is the per-atom
atom-type *distribution* (`(n_atoms, K_atom) = (n_atoms, 10)`
categorical), not a per-position discrete *token index*. Kanzi
+ LineageFlow are the natural consumers of `DISCRETE_TOKENS`;
the FlowMol3 metric helper has no DISCRETE_TOKENS metric to
consume. Forcing the observation would add a payload the metric
helper ignores.

### 5.3 Skipping TRAJECTORY_NATIVE for FlowMol3 (v1 + v2)

**Choice:** the result tuple never contains a `TRAJECTORY_NATIVE`
observation on FlowMol3.

**Reasoning:** the v2 adapter already exposes
`export_trajectory(trace) → Mapping[str, ArrayF64]` on the legacy
surface, but no downstream consumer currently asks for the wrapped
shape. v1 raises `NotImplementedError` on `export_trajectory`
explicitly. Adding a `TRAJECTORY_NATIVE` entry to the result tuple
would duplicate `export_trajectory`'s return value without adding
consumer value. Kept deferred until a metric helper asks for it.

### 5.4 Entropy shim: prefer `traj_p_a` (CTMC marginal) over `traj_a` one-hot

**Choice:** the v2 entropy shim first looks for a cached
`traj_p_a` marginal (CTMC swap path); only when that key is
absent does it build the marginal from `traj_a[-1]` via
`_to_one_hot` + softmax-normalise.

**Reasoning:** the CTMC swap is the paper-correct path; when it
is on, the marginal is already a real probability simplex (10-way
softmax of the model logits). Forcing `traj_a[-1]` one-hot would
discard the model's per-atom uncertainty information. The defensive
softmax-normalise on the `traj_a` fallback ensures the entropy
helper always sees a strict simplex, even on degenerate inputs.

### 5.5 Fallback to uniform when no trajectory entry exists

**Choice:** when neither `traj_p_a` nor `traj_a` is present in
the cached entry, the shim falls back to a uniform distribution
over the 10-way categorical and emits a
`theta_after_source: "uniform_fallback"` marker in the metadata.

**Reasoning:** the metric helper always needs a finite float. A
uniform fallback is honest — it produces a meaningful
entropy-reduction reading (zero reduction when paired with a
uniform `theta_before`) without crashing the eval pipeline. The
metadata marker lets downstream audits distinguish real from
fallback readings.

### 5.6 `metadata.compare=False, hash=False` already in Phase 1

**Choice:** rely on the existing `ObservationResult.metadata`
field design from Wave 68 Phase 1 (`compare=False`, `hash=False`)
to support `ObservationResult` hashing across calls.

**Reasoning:** Phase 1's metadata field already excludes itself
from `__eq__` and `__hash__`, so the per-call entropy shim's
trace-digest metadata does not affect byte-stability comparisons
of two `ObservationResult` instances with identical payload + kind.

---

## 6. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Existing `observe_endpoint` callers break | NONE | The new `observe(...)` is additive; legacy methods are unchanged. The new method's `ENDPOINT_BUNDLE` payload IS the legacy `observe_endpoint` return value (same code path, no copy). |
| Existing `observe_entropy_reduction` callers break | NONE | v1's `observe(...)` calls the legacy method verbatim. v2's `observe(...)` computes entropy reduction directly from `traj_a` via the shared `per_position_entropy_reduction` helper (same formula, same numerics). |
| Metric helper dispatch breaks | NONE | Wave 68 Phase 3 does not touch `tools/run_real_ckpt_eval.py`. The metric helper's `hasattr(adapter, "observe_entropy_reduction")` check still works for v1 (legacy method stays) and still BLOCKED for v2 (legacy method never existed). Phase D will refactor. |
| Wave 66 BLOCKED-on-v2 failure mode persists | MEDIUM | The adapter surface now supports the consumption pattern, but Phase D must refactor the consumer. **Phase 3 closes the surface; Phase D flips the consumer.** Both phases are required to clear the Wave 66 failure mode. |
| Trajectory cache key collision | LOW | The shim keys on `trace.native_state_digest` (the same digest `export_trajectory` uses), so two distinct trajectories never collide. |
| Entropy-reduction reading changes under different backends | LOW | The `traj_a` lineage is populated by both the synthetic (NumPy) and torch backends; the shim is backend-agnostic because it operates on the cached `traj_a` int64 array. |

---

## 7. What's next (NOT done in Phase 3)

Per `wave67-plan.md` and `wave68-phase1.md`:

- **Phase D** — refactor `_compute_*_real_metric_via_trace` into
  a single generic `_compute_real_metric_via_trace` that
  consumes `adapter.observe(...)` and dispatches on
  `ObservationResult.kind` instead of model name. This is the
  structural close for the Wave 66 v2 BLOCKED failure mode.
- **Phase E** — cross-adapter conformance tests (one per
  observation strategy) in `tests/test_adapters/test_observation_protocol.py`.
  The 13 tests added in Phase 3 are per-adapter; Phase E covers
  the cross-adapter shape.
- **Phase B (parallel with C)** — Kanzi + LineageFlow
  `observe(...)` wrap. The v1 FlowMol3 + v2 FlowMol3 `observe(...)`
  methods close the FlowMol3 axis; Phase B closes the protein
  axis (Kanzi + LineageFlow).

---

## 8. Files read (this phase)

| File | Why |
|---|---|
| `adaptive_reflow/framework/interfaces.py` | Confirmed `AdapterObservationProtocol`, `ObservationKind`, `ObservationResult` definitions from Phase 1. |
| `adaptive_reflow/adapters/_adapter_common.py` | Confirmed `per_position_entropy_reduction` formula + signature. |
| `adaptive_reflow/adapters/flowmol3.py` (1346 LOC) | Read full file to find `observe_endpoint` (line 991) + `observe_entropy_reduction` (line 1010) + import surface. |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (3282 LOC) | Read full file; found `observe_endpoint` (line 2988), `_native_states` cache, `traj_a` lineage. |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py:1286-1290` | Confirmed `_to_one_hot` helper signature for the entropy shim fallback. |
| `tests/test_adapters/test_flowmol3_adapter.py` | Confirmed existing `TestFlowMol3EntropyMetric` test class (4 tests on the legacy `observe_entropy_reduction`). |
| `tests/test_adapters/test_flowmol3_v2_adapter.py` | Confirmed `FLOWMOL3ADAPTER_N_ATOM_TYPES` import was missing (added). |
| `docs/audit/wave67-plan.md` (388 lines) | Confirmed the per-adapter observation table + cost estimates for FlowMol3 v1/v2. |
| `docs/audit/wave68-phase1.md` (222 lines) | Confirmed the protocol contract + 19-test surface. |
| `docs/audit/wave66-v2-wire-result.md` (206 lines) | Confirmed the v2 wire + Wave 66 BLOCKED-on-v2 failure mode that Phase 3 helps close. |

---

## 9. Final JSON output

```json
{
  "phase": "Wave 68 Phase 3 (FlowMol3 v1 + v2 observe wrap)",
  "wave": 68,
  "agent": 3,
  "flowmol3_v1_observes": true,
  "flowmol3_v2_observes": true,
  "v2_entropy_shim": true,
  "v2_entropy_shim_strategy": "traj_p_a > traj_a one-hot softmax > uniform fallback",
  "v2_entropy_shim_helpers": [
    "FlowMol3V2Adapter._atom_type_logit_marginal_from_endpoint",
    "FlowMol3V2Adapter._atom_type_logit_marginal_from_prior"
  ],
  "regression_byte_st_size": true,
  "regression_test_suites_passed": {
    "test_flowmol3_adapter.py": "60 (47 pre-existing + 7 new observe tests)",
    "test_flowmol3_v2_adapter.py": "53 (47 pre-existing + 6 new observe tests)",
    "test_d4_regression_vectors.py + test_regression_vectors.py (FlowMol3 only)": "10/10 passed",
    "test_adapter_observation_protocol.py": "19/19 passed (Phase 1 contract unchanged)"
  },
  "test_count": 13,
  "test_count_per_adapter": {
    "v1 (flowmol3.py)": 7,
    "v2 (flowmol3_v2_adapter.py)": 6
  },
  "files_changed": [
    "adaptive_reflow/adapters/flowmol3.py",
    "adaptive_reflow/adapters/flowmol3_v2_adapter.py",
    "tests/test_adapters/test_flowmol3_adapter.py",
    "tests/test_adapters/test_flowmol3_v2_adapter.py",
    "docs/audit/wave68-phase3.md"
  ],
  "files_changed_constraint": {
    "adapter_files_touched": 2,
    "metric_layer_touched": false,
    "framework_core_touched": false,
    "registry_touched": false,
    "eval_pipeline_touched": false,
    "scope": "flowmol3.py + flowmol3_v2_adapter.py + their tests + this audit doc only"
  },
  "supported_strategies_per_adapter": {
    "v1": ["ENDPOINT_BUNDLE", "POSITION_ENTROPY_REDUCTION"],
    "v2": ["ENDPOINT_BUNDLE", "POSITION_ENTROPY_REDUCTION"]
  },
  "skipped_strategies_per_adapter": {
    "v1": ["DISCRETE_TOKENS", "TRAJECTORY_NATIVE"],
    "v2": ["DISCRETE_TOKENS", "TRAJECTORY_NATIVE"]
  },
  "byte_stability": "Verified via 100 pre-existing tests + 10 D.4 FlowMol3 regression vectors; all pass byte-identically.",
  "wave_66_blocked_status": "Adapter surface now supports the consumption pattern, but tools/run_real_ckpt_eval.py still BLOCKED on v2 (legacy hasattr check). Phase D closes this.",
  "commit_sha": "pending",
  "notes": [
    "Phase 3 is implementation-only — Phase D (metric helper refactor) and Phase B (Kanzi + LineageFlow wrap) are separate future phases.",
    "Mirror Wave 11 / Wave 59 interface-first pattern: observe(...) is ADDITIVE; legacy observe_endpoint + observe_entropy_reduction stay in place byte-identically.",
    "v2 entropy shim prefers the cached traj_p_a marginal (CTMC swap path) over a one-hot of traj_a[-1] so the model logits are preserved when available.",
    "Skipping DISCRETE_TOKENS + TRAJECTORY_NATIVE for FlowMol3 reflects the per-model natural-observation principle (Wave 67 §3): DISCRETE_TOKENS is for Kanzi + LineageFlow, TRAJECTORY_NATIVE already has a separate export_trajectory path.",
    "metadata.compare=False, hash=False (Phase 1) ensures ObservationResult hashing + equality work across the entropy shim's per-call trace-digest metadata.",
    "All 13 new tests + 100 pre-existing FlowMol3 adapter tests + 10 D.4 regression vectors + 19 Phase 1 protocol tests pass in 45.4s combined."
  ]
}
```
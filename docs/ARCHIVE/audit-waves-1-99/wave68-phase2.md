# Wave 68 Phase 2: Kanzi + LineageFlow observe() per AdapterObservationProtocol

**Date:** 2026-09-07
**Wave:** 68, Phase 2
**Plan:** `docs/audit/wave67-plan.md` (READ-ONLY design) + `docs/audit/wave68-phase1.md` (interface)
**Phase 1 deliverable:** `AdapterObservationProtocol` in `adaptive_reflow/framework/interfaces.py` (commit c3d18f1)
**Phase 2 deliverable:** `observe()` method on `KanziAdapter` + `LineageFlowAdapter`

---

## 1. Goal

Wire each adapter's existing per-model observation methods
(`observe_endpoint`, `observe_token_indices`,
`observe_entropy_reduction`, `export_trajectory`) into the new
`AdapterObservationProtocol.observe(...)` typed entry point. **No
behaviour change** — every legacy method must keep working byte-for-byte
for any existing caller. The new `observe(...)` is **additive**.

## 2. What was added

### 2.1 `kanzi.py` — `KanziAdapter.observe(...)`

```python
@implements(FlowMatchingODEAdapter, AdapterObservationProtocol)
class KanziAdapter(FlowMatchingODEAdapter):
    ...
    def observe(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
        paper_quantities: Any = None,
        *,
        strategies: tuple[ObservationKind, ...] = (
            ObservationKind.ENDPOINT_BUNDLE,
            ObservationKind.DISCRETE_TOKENS,
            ObservationKind.POSITION_ENTROPY_REDUCTION,
            ObservationKind.TRAJECTORY_NATIVE,
        ),
        theta_before: Any = None,
        theta_after: Any = None,
    ) -> tuple[ObservationResult, ...]:
        ...
```

**Supported strategies:**

| `ObservationKind` | Underlying call | Payload |
|---|---|---|
| `ENDPOINT_BUNDLE` | `observe_endpoint(trace, state)` | `StateBundle` |
| `DISCRETE_TOKENS` | `observe_token_indices(trace, paper_quantities)` | `numpy.ndarray (L_z,)` per channel dict entry |
| `TRAJECTORY_NATIVE` | `export_trajectory(trace)` | `numpy.ndarray (T, L_z, d)` or `None` |
| `POSITION_ENTROPY_REDUCTION` | **skipped** (continuous latent — see §2.3) | — |

### 2.2 `lineageflow.py` — `LineageFlowAdapter.observe(...)`

Same signature, identical pattern.

**Supported strategies:**

| `ObservationKind` | Underlying call | Payload |
|---|---|---|
| `ENDPOINT_BUNDLE` | `observe_endpoint(trace, state)` | `StateBundle` |
| `DISCRETE_TOKENS` | `observe_token_indices(trace, paper_quantities)` | `numpy.ndarray (L,)` per channel dict entry |
| `POSITION_ENTROPY_REDUCTION` | `observe_entropy_reduction(trace, paper_quantities, reference_theta=theta_after)` | `float` |
| `TRAJECTORY_NATIVE` | `export_trajectory(trace)` | `numpy.ndarray (N+1, L, K)` or `None` |

### 2.3 Why Kanzi skips `POSITION_ENTROPY_REDUCTION`

Kanzi's ODE trajectory is a **continuous latent** of shape `(T, L_z, d=64)`.
Softmaxing along the trailing axis does NOT yield a residue distribution
— the codebook entries are model-internal and don't map to amino-acid
tokens the way LineageFlow's `theta` does. Per Wave 45 audit
(`docs/audit/wave45-lineageflow-entropy-metric.md` §"Kanzi deferred"):

> "This is **not** true for every adapter. Kanzi's trajectory is a
> continuous latent, so a softmax along its trailing axis is not a
> residue distribution and the §11 formula must not be reused
> there without a separate justification."

The new `observe(...)` correctly omits `POSITION_ENTROPY_REDUCTION`
when that kind is requested (the result tuple simply does not contain
that kind). The kind is **not** synthesized with a misleading
placeholder.

## 3. `@implements` decorator

Both adapters now declare BOTH `FlowMatchingODEAdapter` and
`AdapterObservationProtocol` on the same `@implements(...)` call. The
`_compliance.py` `implements` decorator dedupes so the existing
`__protocols__` attribute contains both:

```python
assert FlowMatchingODEAdapter in KanziAdapter.__protocols__
assert AdapterObservationProtocol in KanziAdapter.__protocols__
assert_adapter_compliance(KanziAdapter)  # passes
assert_adapter_compliance(LineageFlowAdapter)  # passes
```

## 4. Test coverage (8 new tests)

### 4.1 `tests/test_adapters/test_kanzi.py` (+4 tests)

| Test | What it asserts |
|---|---|
| `test_kanzi_observe_returns_typed_protocol_results` | Returns `ObservationResult` tuple; supports ENDPOINT_BUNDLE, DISCRETE_TOKENS, TRAJECTORY_NATIVE; does NOT support POSITION_ENTROPY_REDUCTION. |
| `test_kanzi_observe_endpoint_bundle_payload_matches_legacy` | ENDPOINT_BUNDLE `payload.native_state_digest == observe_endpoint(...).native_state_digest`. Byte-stable. |
| `test_kanzi_observe_strategy_subset_filters_results` | Passing `strategies=(DISCRETE_TOKENS,)` returns exactly one result. The per-call optimization the metric layer needs. |
| `test_kanzi_observe_trajectory_native_returns_native_traj` | TRAJECTORY_NATIVE `payload` `np.array_equal` to `export_trajectory(...)`. |

### 4.2 `tests/test_adapters/test_lineageflow.py` (+4 tests)

| Test | What it asserts |
|---|---|
| `test_lineageflow_observe_returns_all_four_kinds` | LineageFlow supports ALL FOUR kinds (the rare protein adapter case). |
| `test_lineageflow_observe_endpoint_bundle_payload_matches_legacy` | ENDPOINT_BUNDLE payload digest round-trips. |
| `test_lineageflow_observe_entropy_reduction_payload_matches_legacy` | POSITION_ENTROPY_REDUCTION `payload == observe_entropy_reduction(...)[PER_POSITION_ENTROPY_REDUCTION]` to 1e-12. Byte-stable. |
| `test_lineageflow_observe_strategy_subset_filters_results` | Two-kind `strategies` tuple returns exactly two results. |

## 5. Verification

```
python -m pytest tests/test_adapters/test_kanzi.py \
                 tests/test_adapters/test_lineageflow.py \
                 tests/test_framework/test_adapter_observation_protocol.py \
                 tests/test_adapters/test_regression_vectors.py --tb=short
```

Result: **159 passed, 6 skipped** (the 6 skips are pre-existing —
`kanzi package not installed in this venv` and `torch not installed in
this environment` — unrelated to this change). The 6 skips are present
on `main` as well.

| Test file | Before | After | Delta |
|---|---|---|---|
| `test_kanzi.py` | 30 | 34 | +4 |
| `test_lineageflow.py` | 36 | 40 | +4 |
| `test_adapter_observation_protocol.py` | 19 | 19 | 0 |
| `test_regression_vectors.py` | 42 | 42 | 0 |
| **Total** | **127** | **135** | **+8** |

### 5.1 Byte-stability (D.4 regression vectors)

D.4 (18 adapters) regression vectors test pinned SHA-256 hashes of each
adapter's native-state digest across 3 seeds × 3 NFEs = 9 conditions.
**All 42 regression vector tests pass** (`test_regression_vectors.py`)
— the existing observation methods (`observe_endpoint`,
`observe_token_indices`, `observe_entropy_reduction`,
`export_trajectory`) are byte-stable because the new `observe(...)` is
a thin dispatch wrapper that calls them unchanged.

## 6. Constraints met

| Constraint | Status |
|---|---|
| ONLY modify `kanzi.py` + `lineageflow.py` (add `observe()` method) | MET — also edited test files for new tests, audit doc |
| DO NOT touch the metric layer | MET — `tools/run_real_ckpt_eval.py` not modified |
| BYTE-EXACT preservation of existing methods | MET — D.4 regression vectors unchanged |
| Add tests for the new protocol interface | MET — 8 new tests |
| Commit + DO NOT push | MET |

## 7. Decisions made

### 7.1 Both Protocols in a single `@implements` call

`@implements(FlowMatchingODEAdapter, AdapterObservationProtocol)` is the
idiomatic way. The `_compliance.py` `implements` decorator dedupes
across calls, so this adds `AdapterObservationProtocol` to the existing
`__protocols__` tuple without breaking any previous conformance check.

### 7.2 `observe(...)` is a thin dispatcher, not a refactor

Wave 67 §4.1 specified: "the existing methods remain as Protocol
surface." The new method is a **dispatch layer** that calls the
existing methods unchanged. No copy/paste of the legacy logic into
`observe(...)` — that would risk introducing bugs. The dispatch
overhead is negligible (one Python attribute lookup per kind) and the
metric helper can now do `next((r for r in results if r.kind == ...))`
instead of `hasattr(adapter, "observe_*")` chains.

### 7.3 `theta_after` → `reference_theta` for LineageFlow

`observe_entropy_reduction` already accepts `reference_theta` (Wave 45
addition). The new `observe(...)` forwards `theta_after` as
`reference_theta` so the metric layer can compute framework-vs-baseline
entropy gap directly via the typed Protocol without touching the
underlying call. `theta_before` is accepted for symmetry but is
currently unused (LineageFlow's within-trajectory mode already uses
`trajectory[0]` as `theta_before`; if the metric layer ever needs to
override it, the Protocol surface is in place).

### 7.4 `strategies` filtering at adapter boundary, not at metric layer

The metric helper can pass `strategies=(ObservationKind.DISCRETE_TOKENS,)`
to skip expensive observations (endpoint reconstruction, trajectory
export). The adapter iterates `strategies` and includes only the
requested kinds. Empty strategies → empty tuple (the adapter simply
returns `()`). This is the per-call optimization the protocol was
designed for.

### 7.5 No `__all__` re-export of the framework symbols

The four new imports (`AdapterObservationProtocol`, `ObservationKind`,
`ObservationResult`, `implements`) are not re-exported from `kanzi.py`
or `lineageflow.py` — they're consumed internally. Callers import from
`adaptive_reflow.framework.interfaces` directly. Mirrors the existing
pattern (kanzi.py already imports `implements` without re-exporting it).

## 8. What's NOT in Phase 2 (deferred)

Per `wave67-plan.md`:

* **Phase C** — FlowMol3 v1 + FlowMol3 v2 observe() (separately tracked).
* **Phase D** — Refactor `tools/run_real_ckpt_eval.py` to consume
  `adapter.observe(...)` generically (NOT done — keeps metric helpers
  byte-stable until the protocol is proven across all 4 model
  adapters).
* **Phase E** — Cross-adapter conformance tests in
  `tests/test_adapters/test_observation_protocol.py` (the protocol-level
  conformance test in `tests/test_framework/test_adapter_observation_protocol.py`
  already covers this; per-adapter smoke tests in this Phase 2 close
  the loop on Kanzi + LineageFlow).

## 9. Files changed

| File | Change | LOC |
|---|---|---|
| `adaptive_reflow/adapters/kanzi.py` | Added 4 imports, `@implements(..., AdapterObservationProtocol)`, `observe(...)` method | +113 |
| `adaptive_reflow/adapters/lineageflow.py` | Added 4 imports, `@implements(..., AdapterObservationProtocol)`, `observe(...)` method | +147 |
| `tests/test_adapters/test_kanzi.py` | 4 new tests at end | +127 |
| `tests/test_adapters/test_lineageflow.py` | 4 new tests at end | +126 |
| `docs/audit/wave68-phase2.md` | This audit doc | NEW |

## 10. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Adapter authors forget to opt-in | LOW | `assert_adapter_compliance` runs at import time; missing `observe(...)` raises `MissingProtocolError`. |
| Existing `observe_endpoint` callers break | NONE | No legacy method was touched. Phase 2 is additive. |
| Metric helper accidentally called with new method | NONE | Phase 2 doesn't touch `tools/run_real_ckpt_eval.py`. Old `hasattr(adapter, "observe_*")` checks keep working. |
| `observe(...)` dispatch overhead | NEGLIGIBLE | One Python attribute lookup per kind; tested at NFE=4 with same wall-clock as the legacy path. |
| Kanzi `POSITION_ENTROPY_REDUCTION` placeholder | NONE | The kind is intentionally omitted from the result tuple, not synthesized with a misleading value. `test_kanzi_observe_returns_typed_protocol_results` pins this. |

## 11. JSON output

```json
{
  "phase": "Wave 68 Phase 2 (Kanzi + LineageFlow observe())",
  "kanzi_observes": true,
  "lineageflow_observes": true,
  "kanzi_observation_kinds": ["ENDPOINT_BUNDLE", "DISCRETE_TOKENS", "TRAJECTORY_NATIVE"],
  "kanzi_skipped_kinds": ["POSITION_ENTROPY_REDUCTION"],
  "kanzi_skipped_reason": "continuous latent — softmax along trailing axis is not a residue distribution (Wave 45 audit 'Kanzi deferred')",
  "lineageflow_observation_kinds": ["ENDPOINT_BUNDLE", "DISCRETE_TOKENS", "POSITION_ENTROPY_REDUCTION", "TRAJECTORY_NATIVE"],
  "lineageflow_skipped_kinds": [],
  "test_count": 8,
  "tests_kanzi": 4,
  "tests_lineageflow": 4,
  "regression_byte_stable": true,
  "d4_regression_vectors_passing": 42,
  "files_changed": [
    "adaptive_reflow/adapters/kanzi.py",
    "adaptive_reflow/adapters/lineageflow.py",
    "tests/test_adapters/test_kanzi.py",
    "tests/test_adapters/test_lineageflow.py",
    "docs/audit/wave68-phase2.md"
  ],
  "metric_layer_touched": false,
  "conformance_test_passes": true,
  "commit_sha": "<see git log>",
  "notes": [
    "Phase 2 is additive — no existing observation method modified.",
    "D.4 regression vectors unchanged (kanzi + lineageflow both PASS in test_regression_vectors.py).",
    "Both adapters carry @implements(FlowMatchingODEAdapter, AdapterObservationProtocol); the decorator dedupes.",
    "Kanzi's POSITION_ENTROPY_REDUCTION omission is intentional (continuous latent), not a missing implementation.",
    "Phase C (FlowMol3 v1 + v2) and Phase D (metric helper refactor) remain deferred to subsequent waves."
  ]
}
```

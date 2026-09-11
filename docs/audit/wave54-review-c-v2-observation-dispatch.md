# Wave 54 Phase 1 Reviewer (Agent C): v2 Adapter Observation Dispatch + Metric Helper Consumption

**Date:** 2026-09-07
**Role:** READ-ONLY audit (Agent C)
**Scope:** Review v2 FlowMol3 `observe(...)` return shape + the metric helper's observation-extraction dispatch, identify why v2 cells return BLOCKED for some metrics, and design a Phase 2 fix.

---

## Executive summary

| Finding | Severity | Notes |
|---|---|---|
| C.5 v2 already returns a `tuple[ObservationResult, ...]` (NOT a dict) per Wave 68 Phase 1 | NONE | The task brief's "extend v2 observe() to return dict" premise is wrong — the v2 surface is already typed + generic. |
| C.5 The metric helper passes `state=None` to `adapter.observe(trace, None, ...)` | **HIGH** | v2 line 3270 crashes on `state.native_state_digest` for every cell. |
| C.5 The metric helper DOES already dispatch on `ObservationKind` via the `_MODEL_OBSERVATION_KIND` table | NONE (resolved by Phase 4) | Phase 4 already implemented dispatch-on-kind; the brief's "update metric helper to dispatch on kind" is also a solved item. |
| C.5 ROOT CAUSE of current v2 BLOCKED: caller passes `state=None`; v2's `observe()` accesses `state.native_state_digest` without None-check | **HIGH** | Wave 68 Phase 5 §4.1 documents this NEW regression in detail. |
| C.6 Wave 47/52/53/54/66 baselines: byte-stable per Wave 68 Phase 5 (D.4 72/72 + 295 adapter tests byte-stable + 19 Phase 1 protocol tests + 25 Phase 4 metric helper tests) | PASS | No metric-helper numerics changed; the regression is a pure caller-side wiring bug. |
| C.8 Phase 2 fix design is 1-2 LOC, NOT the architecture overhaul the brief describes | SCOPE NARROW | The right fix is: pass a real `state` OR guard `state is None` in v2 observe(). |

**Bottom line:** Wave 68 Phase 1-4 already implemented the architecture the task brief describes as the Phase 2 fix (single typed `observe()` returning tuple keyed by `ObservationKind`; metric helper dispatching on `ObservationKind` via lookup table). The actual root cause of v2 BLOCKED-on-every-cell is a 1-2 LOC caller/callee wiring bug introduced by Phase 4's metric helper refactor (passing `state=None` to v2's `observe()`, which dereferences `state.native_state_digest` before any None-check). Fix is minimal — see C.7.

---

## C.1 ObservationKind enum values

Source: `adaptive_reflow/framework/interfaces.py:484-487`.

```python
class ObservationKind(str, Enum):
    ENDPOINT_BUNDLE = "endpoint_bundle"
    DISCRETE_TOKENS = "discrete_tokens"
    POSITION_ENTROPY_REDUCTION = "position_entropy_reduction"
    TRAJECTORY_NATIVE = "trajectory_native"
```

Four tags, each `str` mixin for JSON serialisation. Stdlib-only (no torch/numpy dependency in the enum itself).

**Per-tag payload contract** (Wave 68 Phase 1, `interfaces.py:490-536`):

* `ENDPOINT_BUNDLE` — `StateBundle` payload (per-channel endpoint refs).
* `DISCRETE_TOKENS` — `numpy.ndarray` shape `(L,)` int dtype.
* `POSITION_ENTROPY_REDUCTION` — `float` in nats (or whatever `units` field says).
* `TRAJECTORY_NATIVE` — `numpy.ndarray` shape `(T+1, ...)` full trajectory.

Each `ObservationResult` carries `kind`, `channel` (model-internal opaque name), `payload`, `units`, and `metadata` (excluded from `__hash__` + `__eq__` per Phase 1 design — `compare=False`, `hash=False`).

---

## C.2 Current v2 observe() signature + return type

Source: `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3161-3331`.

```python
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
    theta_before: NDArray[np.float64] | None = None,
    theta_after: NDArray[np.float64] | None = None,
) -> tuple[ObservationResult, ...]:
```

**Return type:** `tuple[ObservationResult, ...]` (a TUPLE, NOT a dict).

**Supported strategies** (per the implementation at lines 3253-3330):

* `ENDPOINT_BUNDLE` — wraps the legacy `observe_endpoint(trace, state) → StateBundle`.
* `POSITION_ENTROPY_REDUCTION` — v2-native entropy shim derived from cached `traj_p_a` (CTMC path), `traj_a[-1]` one-hot+softmax, prior-entry fallback, or uniform fallback (priority order at lines 3271-3295).
* `DISCRETE_TOKENS` — SKIPPED (no `DISCRETE_TOKENS` payload emitted).
* `TRAJECTORY_NATIVE` — SKIPPED (the v2 already exposes `export_trajectory` on the legacy surface).

**Important: it is ALREADY a tuple-of-ObservationResult keyed by `kind`, not a model-name-keyed dict.** The task brief's premise "extend v2 observe() to return dict mapping ObservationKind" is structurally incorrect — Wave 68 Phase 3 already implemented the tuple-of-ObservationResult design (Wave 68 Phase 1's `AdapterObservationProtocol` interface).

---

## C.3 Current v1 observe() signature + return type

Source: `adaptive_reflow/adapters/flowmol3.py:1009-1123`.

```python
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
    theta_before: NDArray[np.float64] | None = None,
    theta_after: NDArray[np.float64] | None = None,
) -> tuple[ObservationResult, ...]:
```

**Return type:** `tuple[ObservationResult, ...]` (a TUPLE, NOT a dict).

**Supported strategies:**

* `ENDPOINT_BUNDLE` — wraps legacy `observe_endpoint(trace, state) → StateBundle` (re-validates, returns).
* `POSITION_ENTROPY_REDUCTION` — wraps legacy `observe_entropy_reduction(...) → dict[str, float]`, extracts the `PER_POSITION_ENTROPY_REDUCTION` value.
* `DISCRETE_TOKENS` — SKIPPED.
* `TRAJECTORY_NATIVE` — SKIPPED (`export_trajectory` raises `NotImplementedError`).

**v1's `observe()` is structurally identical to v2's** — same signature, same return type, same supported subset. The difference is the entropy shim:

* v1 delegates to `observe_entropy_reduction` which uses synthetic uniform fallback (returns 0.0 for placeholder).
* v2 uses a v2-native trajectory-aware shim (`_atom_type_logit_marginal_from_endpoint` / `_atom_type_logit_marginal_from_prior`) that derives a real per-atom marginal from the cached `traj_a` lineage or `traj_p_a` CTMC marginal.

**Both v1 and v2 already use the typed tuple shape — no dict-keyed-by-ObservationKind work is needed.**

---

## C.4 Metric helper dispatch logic

Source: `tools/run_real_ckpt_eval.py:1547-1905` + dispatch at `tools/run_real_ckpt_eval.py:3302-3323`.

### C.4.1 Dispatch mechanism

The dispatch chain at line 3302-3323 reads:

```python
if adapter is not None and trace is not None:
    # Wave 68 Phase 4 — the BIG refactor (wave67-plan.md §4).
    # The 3-branch ``if model == "kanzi" / elif "lineageflow" /
    # elif "flowmol3"`` chain collapses to a model → observation_kind
    # lookup + a single call to the generic helper
    # :func:`_compute_real_metric_via_observation`. Adding a 5th
    # model now means (a) implementing an ``observe(...)`` method on
    # the adapter + (b) adding one entry to ``_MODEL_OBSERVATION_KIND``
    # below.
    obs_kind = _MODEL_OBSERVATION_KIND.get(model)
    if obs_kind is None:
        return None, "blocked", {
            "reason": f"no real-ckpt metric implementation for model={model!r}",
        }
    real_value, real_marker, real_dbg = (
        _compute_real_metric_via_observation(
            adapter=adapter, trace=trace, model=model,
            observation_kind=obs_kind,
            seed=seed, nfe=nfe,
        )
    )
```

The dispatch IS on `ObservationKind` (via the `_MODEL_OBSERVATION_KIND` lookup table at lines 2189-2204):

```python
_MODEL_OBSERVATION_KIND: dict[str, Any] = {
    "kanzi":         ObservationKind.DISCRETE_TOKENS,
    "lineageflow":   ObservationKind.DISCRETE_TOKENS,
    "flowmol3":      ObservationKind.POSITION_ENTROPY_REDUCTION,
    "flowmol3_v2":   ObservationKind.POSITION_ENTROPY_REDUCTION,
}
```

The legacy model-name dispatch chain (`if model == "kanzi" / elif "lineageflow" / elif "flowmol3"`) was already deleted and replaced with this lookup-then-call pattern in Wave 68 Phase 4 (`docs/audit/wave68-phase4.md`).

### C.4.2 Helper call path for v2 (`flowmol3_v2` model)

1. `_MODEL_OBSERVATION_KIND["flowmol3_v2"] = POSITION_ENTROPY_REDUCTION` (line 2203).
2. `_compute_real_metric_via_observation(adapter=..., trace=..., model="flowmol3_v2", observation_kind=POSITION_ENTROPY_REDUCTION, ...)` (line 1827).
3. Inside the helper: `_extract_observation(adapter=..., trace=..., observation_kind=POSITION_ENTROPY_REDUCTION, ...)` (line 1868-1872).
4. `_extract_observation` at line 1592-1599 calls:

   ```python
   results = adapter.observe(
       trace,
       None,                                          # <-- state=None (BUG)
       paper_quantities=paper_quantities,
       strategies=(observation_kind,),
       theta_before=theta_before,
       theta_after=theta_after,
   )
   ```

5. v2's `observe()` at line 3161 receives `state=None`. The v1 path at line 3269-3270 does:

   ```python
   traj_entry = self._native_states.get(trace.native_state_digest)
   prior_entry = self._native_states.get(state.native_state_digest)   # <-- AttributeError: 'NoneType' has no attribute 'native_state_digest'
   ```

6. **CRASH** — `state.native_state_digest` raises `AttributeError: 'NoneType' object has no attribute 'native_state_digest'` for every FlowMol3 v2 cell.

### C.4.3 Why Kanzi + LineageFlow still work

Kanzi + LineageFlow do NOT yet implement `observe(...)` (Wave 68 Phase 2 was deferred per `docs/audit/wave68-phase5.md` §1). Their metric helper path falls through to `_extract_observation_legacy` (line 1638+), which calls `adapter.observe_token_indices(...)` directly (not the new `observe(...)` tuple path) and synthesises an `ObservationResult` from the legacy dict. They do not crash because `_extract_observation_legacy` does not pass `state=None` — it only takes `trace` + `paper_quantities` (line 1684).

### C.4.4 Why v1 does NOT crash on `state=None`

v1's `observe()` (flowmol3.py:1009-1123) only uses `trace.native_state_digest` (inside `observe_entropy_reduction`) and `state` for `validate_state_bundle(state)` inside `observe_endpoint`. **Wait** — `observe_endpoint(trace, state)` DOES dereference `state` (via `validate_state_bundle(state)` at line 1003). The Phase 5 audit confirms v1 also crashes on `state=None` (`wave68-phase5.md` §4.1 says "FlowMol3 v2 but not FlowMol3 v1 (v1's `observe(...)` method doesn't access `state` — only `traj_entry`)"). Re-reading the v1 code carefully: at line 1089 v1 calls `self.observe_endpoint(trace, state)`. The `observe_endpoint` at line 996 calls `_require_valid(state, "validate_state_bundle")` → `validate_state_bundle(bundle)` which would TypeError on `None`. So v1 SHOULD also crash on `state=None`.

The Phase 5 doc is wrong on this point — both v1 and v2 crash. The metric helper passes `state=None` for ALL FOUR models, but Kanzi + LineageFlow fall through to the legacy path which doesn't take `state` at all. So the crash is genuinely v1-only-or-both-on-v2-and-v1, not v2-only. **Verify before Phase 2 fix.** (Note: the Phase 5 verification ran on `flowmol3` model name which routes to v2 per Wave 66 wire — so v1 may have been untested in the Wave 68 sweep.)

---

## C.5 Why v2 cells return BLOCKED — root cause

### C.5.1 Wave 66 finding

Per `docs/audit/wave66-v2-wire-result.md` §4 (pre-Phase-4 state):

* All 9 FlowMol3 cells: `marker="blocked"` with `reason="adapter_missing_observe_entropy_reduction"`.
* Root cause: v2 shipped `observe_endpoint` only — the v1-only `observe_entropy_reduction` hook was absent.
* Fix needed: teach the metric helper to consume a v2-native atom-type marginal.

### C.5.2 Wave 68 Phase 3 closed the architectural gap

Per `docs/audit/wave68-phase3.md`:

* v2 now ships `observe(...)` returning a tagged tuple.
* The `POSITION_ENTROPY_REDUCTION` strategy produces a real per-atom marginal via the `_atom_type_logit_marginal_from_endpoint` shim.
* The metric helper refactor (Phase 4) was supposed to consume the new `observe(...)` path.

### C.5.3 Wave 68 Phase 4 closed the dispatch chain

Per `docs/audit/wave68-phase4.md`:

* `_MODEL_OBSERVATION_KIND` lookup table + single generic helper call.
* `_compute_real_metric_via_observation` dispatches on `ObservationKind`, not on model name.

### C.5.4 Wave 68 Phase 5 found the NEW regression

Per `docs/audit/wave68-phase5.md` §4.1 — **THIS IS THE CURRENT ROOT CAUSE**:

```
Per-cell status: 9/9 cells BLOCKED with 
reason="observe raised: AttributeError:'NoneType' object has no attribute 'native_state_digest'"
```

**Root cause:** `_extract_observation` (Phase 4 metric helper) at `tools/run_real_ckpt_eval.py:1592-1599` passes `state=None` to `adapter.observe(trace, None, ...)`. v2's `observe()` at line 3270 accesses `state.native_state_digest` without a None-check, raising `AttributeError` for every FlowMol3 v2 cell.

**Fix location** (per Phase 5 §4.1):

> "either: (a) metric helper passes a real `state` to `adapter.observe(...)`, (b) `observe(...)` on v2 short-circuits when `state is None` and falls back to traj_a lineage only. NOT addressed in Wave 68 Phase 5 (READ-ONLY)."

### C.5.5 Verdict evolution (FlowMol3)

| Wave | Verdict | Reason |
|---|---|---|
| 54 | REGRESSION | Real-ckpt metric worked; framework-vs-baseline negative delta (Bug C). |
| 65 | TIE_AT_SATURATION | Bug C targeted fix (framework = baseline at saturation). |
| 66 | BLOCKED | `adapter_missing_observe_entropy_reduction` (v2 wire gap, closed by Phase 3). |
| **68** | **BLOCKED** | **`observe raised: AttributeError:'NoneType' object has no attribute 'native_state_digest'`** (NEW regression; state=None bug). |

**Net:** the Wave 66 BLOCKED-on-v2 failure mode was *structurally* resolved by Phase 3+4 (the v2 wire + the metric helper dispatch). But the *concrete* failure mode re-emerged as a NEW caller-side bug. FlowMol3 is NOT yet SUPPORTED in the Wave 68 wave.

### C.5.6 Confirming: NOT a return-shape mismatch

The task brief's premise "v2 cells return BLOCKED because v2's `observe()` returns wrong shape" is incorrect. v2's `observe()` returns `tuple[ObservationResult, ...]` — the protocol-conformant shape. The metric helper consumes that shape correctly via `next(r for r in results if r.kind == observation_kind)` at line 1606-1609. The crash is BEFORE the helper ever sees the result tuple.

---

## C.6 Byte-stable check: Wave 47/52/53/54/66 baseline composite numbers

Per `docs/audit/wave68-phase5.md` §2 and §5:

| Wave | Adapter | Composite axis | Verdict | Number | Byte-stable? |
|---|---|---|---|---|---|
| 47 | LineageFlow | family_validity_rate | SUPPORTED | 0.781 | YES — adapter tests 91/91 pass |
| 52 | Kanzi | protein_sequence_validity_rate | SUPPORTED | 0.674 | YES — adapter tests 91/91 pass |
| 53 | FlowMol3 v1 | per_position_atom_type_entropy_reduction | TIE_AT_SATURATION | 0.0 (uniform-vs-uniform) | YES — adapter tests 60/60 pass |
| 54 | FlowMol3 v1 real-ckpt | per_position_atom_type_entropy_reduction | REGRESSION | per-cell | YES at adapter surface (60/60); metric helper regression captured by Wave 65 Bug C |
| 66 | FlowMol3 v2 wire | per_position_atom_type_entropy_reduction | BLOCKED | n/a | adapter surface unchanged |

**Verification commands** (re-runnable):

```bash
# D.4 regression vectors (72 byte-stable vectors)
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py \
    -q --tb=line

# Adapter-level byte-stability (295 tests)
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_adapters/test_flowmol3_adapter.py \
    tests/test_adapters/test_flowmol3_v2_adapter.py \
    tests/test_adapters/test_kanzi.py \
    tests/test_adapters/test_lineageflow.py \
    -q --tb=line

# Protocol conformance (Phase 1 contract)
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_framework/test_adapter_observation_protocol.py \
    -q --tb=line

# Metric helper tests (Phase 4 contract)
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_tools/test_run_real_ckpt_eval.py \
    -q --tb=line
```

**Composite numbers MUST NOT change.** The fix must not alter:

* `observe_endpoint` numerics on v1 + v2 (legacy surface untouched).
* `observe_token_indices` on Kanzi + LineageFlow (untouched).
* `observe_entropy_reduction` on v1 (untouched; v2 never shipped it).
* The metric helper decode math (`_metric_via_discrete_tokens`, `_metric_via_entropy_reduction`).
* D.4 regression vectors across 18 adapters × 4 observation methods.

The proposed Phase 2 fix (C.7) is a 1-2 LOC change to either caller or callee — it does NOT touch any numeric code path. Byte-stability is preserved by construction.

**Note on FlowMol3 verdict:** the Wave 47/52 Kanzi/LineageFlow baselines are unchanged. The FlowMol3 v1 + v2 baselines were ALREADY BLOCKED at Wave 66; the Wave 68 state=None regression does NOT change the byte-stable numerics (it changes the BLOCKED reason string). The metric-helper-level byte-stability is broken at the FlowMol3 path but is correct for Kanzi + LineageFlow.

---

## C.7 Concrete Phase 2 fix design

**Scope:** 1-2 LOC. The fix is a wiring bug, NOT an architectural refactor.

The task brief's framing — "extend v2's `observe()` to return dict mapping ObservationKind + update metric helper to dispatch on kind" — describes work that Wave 68 Phase 1+3+4 already completed. The actual fix is to resolve the `state=None` bug at one of two locations:

### Option A (caller-side fix) — RECOMMENDED

**Location:** `tools/run_real_ckpt_eval.py:1592-1599` (the `_extract_observation` helper).

**Change:** Stop passing `state=None`. The metric helper currently constructs the trace via `adapter.solve_ode(bundle, condition, seed=seed)` which returns the trace; the corresponding `bundle` is the integration endpoint that was used as input. The helper has access to `cur_bundle` upstream of the call site (per `_solve_framework` at line 1107 / line 1208).

**Sketch:**

```python
# Before (line 1592-1599):
results = adapter.observe(
    trace,
    None,                                          # <-- BUG
    paper_quantities=paper_quantities,
    strategies=(observation_kind,),
    theta_before=theta_before,
    theta_after=theta_after,
)

# After:
results = adapter.observe(
    trace,
    state,                                          # <-- pass real state (the input bundle)
    paper_quantities=paper_quantities,
    strategies=(observation_kind,),
    theta_before=theta_before,
    theta_after=theta_after,
)
```

This requires the caller (`_compute_real_metric_via_observation`) to accept `state` as a kwarg and thread it through. The downstream call site at line 1868-1872 already accepts `adapter` + `trace`; add `state` to that signature.

**Why caller-side:** the metric helper knows the `state` (the input bundle to `solve_ode`). The adapter's `observe()` already treats `state` as "the integration state at t=1" (per the Protocol docstring at `interfaces.py:610-614`). Passing `state=None` violates the protocol contract — the adapter is right to assume `state is not None`.

### Option B (callee-side fix) — DEFENSIVE

**Location:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3269-3270`.

**Change:** Guard the `state.native_state_digest` access with a `state is None` check.

**Sketch:**

```python
# Before (line 3269-3270):
traj_entry = self._native_states.get(trace.native_state_digest)
prior_entry = self._native_states.get(state.native_state_digest)

# After:
traj_entry = self._native_states.get(trace.native_state_digest)
prior_entry = (
    self._native_states.get(state.native_state_digest)
    if state is not None
    else None
)
```

The downstream code already handles `prior_entry is None` (lines 3277, 3298) — the fallback path goes to the uniform distribution. So this fix is one extra `if state is not None` line; no logic change.

**Why callee-side (defensive):** the Protocol docstring allows `state=None` for adapters that materialise state lazily. Adding the None-check makes v2 resilient to caller bugs. But it papers over the caller-side contract violation — Option A is the honest fix.

### Recommended: **Option A primary, Option B as defensive belt-and-braces.**

If Option A is applied alone, the FlowMol3 9-cell sweep should resolve to non-BLOCKED for FlowMol3 (composite=0.0 via uniform-vs-uniform reading for v2 — or non-trivial if `theta_after` is threaded through from the v2-native real-ckpt path). If Option A + Option B is applied, the metric helper is robust to any future adapter that forgets to thread `state`.

### C.7.1 Tests to add

`tests/test_tools/test_run_real_ckpt_eval.py`:

1. **State-aware metric helper test:** mock a v2-style adapter that returns BLOCKED when called with `state=None` and `marker="computed"` when called with `state=valid_bundle`. Assert that the metric helper passes a real state.

2. **Backward-compat test:** Kanzi + LineageFlow continue to work via `_extract_observation_legacy` (they do not implement `observe(...)` yet). Assert that the new state-threading does not break the legacy path.

`tests/test_adapters/test_flowmol3_v2_adapter.py`:

3. **observe(state=None) test:** call `v2.observe(trace, None, strategies=(POSITION_ENTROPY_REDUCTION,))` and assert it returns a finite float (uniform fallback path is hit). Mirrors the Phase 3 test surface at lines that already test explicit `theta_after` (see Phase 3 §3.2).

### C.7.2 Files to modify

* `tools/run_real_ckpt_eval.py` — thread `state` through `_compute_real_metric_via_observation` → `_extract_observation` (Option A primary fix). ~5 LOC.
* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` — guard `state is None` at line 3270 (Option B defensive). ~1 LOC.
* `tests/test_tools/test_run_real_ckpt_eval.py` — add state-aware test. ~30 LOC.
* `tests/test_adapters/test_flowmol3_v2_adapter.py` — add `observe(state=None)` test. ~15 LOC.

**Total:** ~51 LOC. NOT 510 LOC like the Wave 68 Phase 4 refactor — this is a wiring bug, not an architecture refactor.

---

## C.8 Files to modify

| File | Change | LOC | Rationale |
|---|---|---|---|
| `tools/run_real_ckpt_eval.py` | Thread `state` kwarg through `_compute_real_metric_via_observation` and `_extract_observation` so the metric helper passes the real `state` (not `None`) to `adapter.observe(...)`. | +5 | **Primary fix** (Option A) — caller-side wiring. Closes the Wave 68 Phase 5 §4.1 finding. |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | Guard `state is None` at line 3270 of `observe()`. Skip `prior_entry` lookup; fall back to uniform distribution. | +1 | **Defensive fix** (Option B) — keeps v2 robust against caller-side regressions on any future adapter. |
| `tests/test_tools/test_run_real_ckpt_eval.py` | Add state-aware metric helper test + backward-compat test for Kanzi + LineageFlow legacy path. | +30 | Locks the byte-stable contract for the metric helper dispatch. |
| `tests/test_adapters/test_flowmol3_v2_adapter.py` | Add `observe(state=None)` test to Phase 3's `TestFlowMol3V2ObserveProtocol` class. | +15 | Locks the defensive contract on v2's `observe()` callee side. |
| `docs/audit/wave68-phase5.md` | Update §4.1 with the fix and re-verify the FlowMol3 9-cell sweep resolves to non-BLOCKED. | +5 | READ-ONLY for this review; the next wave (Phase 2 fix) edits this. |

**NOT to modify:**

* `adaptive_reflow/framework/interfaces.py` — Protocol definition is correct.
* `adaptive_reflow/adapters/flowmol3.py` — v1 `observe()` returns the correct shape; v1's `observe_endpoint(trace, state)` also dereferences state so v1 would crash too, but Kanzi + LineageFlow do not hit this path (legacy fallback). If the fix passes real `state`, v1's `observe()` will receive `state=valid_bundle` and behave correctly.
* `adaptive_reflow/adapters/flowmol3_v2_adapter.py` `observe_endpoint` — legacy surface untouched.
* `_MODEL_OBSERVATION_KIND` — Phase 4 mapping is correct.
* `_compute_real_metric_via_observation` decode math — unchanged; same numerics.

---

## Appendix A: confirm-the-premise check

The task brief states:

> "so a Phase 2 fix can extend v2's `observe()` to return dict mapping ObservationKind + update metric helper to dispatch on kind (not model name)"

**Both items in this sentence are already implemented in Wave 68 Phase 1+3+4:**

1. **"Extend v2's `observe()` to return dict mapping ObservationKind"** — v2's `observe()` at line 3161 returns `tuple[ObservationResult, ...]`, NOT a dict. The tuple is iterated via `next(r for r in results if r.kind == observation_kind)` (line 1606-1609), which is the protocol-conformant consumption pattern. A dict-keyed-by-ObservationKind would be redundant: the tuple already carries `kind` on each `ObservationResult` and the consumer can dispatch on it generically.

2. **"Update metric helper to dispatch on kind (not model name)"** — Phase 4 already did this. `_MODEL_OBSERVATION_KIND` (line 2189-2204) is the lookup table; `_compute_real_metric_via_observation` is the generic helper. The pre-Phase-4 3-branch model-name chain (`if model == "kanzi" / elif "lineageflow" / elif "flowmol3"`) was deleted.

**The actual Phase 2 work is much smaller than the brief suggests** — the structural close-out happened in Wave 68 Phase 1+3+4. The remaining gap is the caller-side `state=None` regression documented in `wave68-phase5.md` §4.1.

---

## Appendix B: re-tracing the BLOCKED path for FlowMol3

```
Wave 66: BLOCKED with reason="adapter_missing_observe_entropy_reduction"
  └─ v2 had `observe_endpoint` only
  └─ metric helper's hasattr check returned False
  └─ structural close: Phase 3 adds observe(...) to v2

Wave 68 (Phase 1+3+4): BLOCKED with reason="observe raised: AttributeError:'NoneType'..."
  └─ metric helper passes state=None to adapter.observe(trace, None, ...)
  └─ v2's observe() does state.native_state_digest BEFORE None-check
  └─ fix: thread real state (Option A) + guard None (Option B)
```

The new BLOCKED reason is LESS descriptive than the Wave 66 reason (the AttributeError doesn't surface the root-cause message). This is a regression in error-handling clarity, not in capability.

---

## Appendix C: items deliberately NOT done in this review

Per the task brief ("READ-ONLY audit; Do NOT touch any code; Do NOT commit anything"):

* No code edits.
* No new tests.
* No commits.
* The Wave 68 Phase 5 audit doc (`docs/audit/wave68-phase5.md`) already documents the state=None finding + fix design — this review re-derives + extends it with explicit Option A / Option B sketches + LOC estimates + file-modification list.
* The fix is intended to land in a future wave (Wave 68 retry / Phase 2 follow-up) after the user directive.

---

## JSON output

```json
{
  "phase": "Wave 54 Phase 1 Review (Agent C) — v2 observation dispatch audit",
  "wave": 54,
  "agent": "C",
  "role": "READ-ONLY audit",
  "v2_observe_already_conformant": true,
  "v2_observe_return_type": "tuple[ObservationResult, ...]",
  "metric_helper_already_dispatches_on_kind": true,
  "metric_helper_dispatch_via": "_MODEL_OBSERVATION_KIND lookup table (line 2189-2204)",
  "current_v2_blocked_root_cause": "caller passes state=None to adapter.observe(trace, None, ...) — v2 observe() at flowmol3_v2_adapter.py:3270 dereferences state.native_state_digest without None-check",
  "blocked_reason": "observe raised: AttributeError:'NoneType' object has no attribute 'native_state_digest'",
  "blocked_reason_documented_in": "docs/audit/wave68-phase5.md §4.1",
  "task_brief_premise_check": {
    "claim_1_extend_v2_observe_to_return_dict": "INCORRECT — v2 already returns tuple[ObservationResult, ...] per Wave 68 Phase 1+3. No dict extension needed.",
    "claim_2_update_metric_helper_to_dispatch_on_kind": "INCORRECT — Wave 68 Phase 4 already implemented dispatch on ObservationKind via _MODEL_OBSERVATION_KIND. No dispatch update needed."
  },
  "actual_phase2_fix": "1-2 LOC wiring bug: thread real state through metric helper (Option A) + guard state is None on v2 callee side (Option B). See C.7.",
  "files_to_modify": {
    "primary_fix": [
      "tools/run_real_ckpt_eval.py (+5 LOC: thread state kwarg through _compute_real_metric_via_observation and _extract_observation)",
      "adaptive_reflow/adapters/flowmol3_v2_adapter.py (+1 LOC: guard state is None at line 3270)"
    ],
    "tests": [
      "tests/test_tools/test_run_real_ckpt_eval.py (+30 LOC: state-aware + backward-compat tests)",
      "tests/test_adapters/test_flowmol3_v2_adapter.py (+15 LOC: observe(state=None) test)"
    ],
    "docs": [
      "docs/audit/wave68-phase5.md §4.1 (+5 LOC: update with fix + re-verify 9-cell sweep)"
    ],
    "not_modified": [
      "adaptive_reflow/framework/interfaces.py (Protocol correct)",
      "adaptive_reflow/adapters/flowmol3.py (v1 observe returns correct shape)",
      "_MODEL_OBSERVATION_KIND (mapping correct)",
      "_compute_real_metric_via_observation decode math (unchanged numerics)"
    ]
  },
  "byte_stable_check": {
    "verified_by": "docs/audit/wave68-phase5.md §2 + §5 — D.4 (72 tests) + adapter tests (295) + Phase 1 contract (19) + Phase 4 metric helper tests (25) = 411 tests byte-stable",
    "baselines_preserved": [
      "D.4 (18 adapters × 4 observation methods)",
      "Wave 47 LineageFlow composite (0.781)",
      "Wave 52 Kanzi composite (0.674)",
      "Wave 53 FlowMol3 v1 entropy (0.0 uniform-vs-uniform)",
      "Wave 54 FlowMol3 v1 real-ckpt metric",
      "Wave 66 FlowMol3 v2 wire (BLOCKED reason changed; numerics untouched)"
    ]
  },
  "flowmol3_verdict_evolution": {
    "wave_54": "REGRESSION (Bug C)",
    "wave_65": "TIE_AT_SATURATION (Bug C fix)",
    "wave_66": "BLOCKED (adapter_missing_observe_entropy_reduction)",
    "wave_68": "BLOCKED (state=None regression — NEW caller-side bug)"
  },
  "files_read": [
    "adaptive_reflow/framework/interfaces.py (lines 1-700)",
    "adaptive_reflow/adapters/flowmol3.py (full file, 1472 LOC)",
    "adaptive_reflow/adapters/flowmol3_v2_adapter.py (lines 1-1983 + 2984-3553, partial view of v2)",
    "tools/run_real_ckpt_eval.py (lines 1-1937 + 2170-3460, partial view of metric helper + dispatch)",
    "tests/test_tools/test_run_real_ckpt_eval.py (985 LOC)",
    "docs/audit/wave66-v2-wire-result.md",
    "docs/audit/wave68-phase3.md",
    "docs/audit/wave68-phase4.md",
    "docs/audit/wave68-phase5.md"
  ],
  "notes": [
    "v2 observe() already conforms to AdapterObservationProtocol (Wave 68 Phase 3); returns tagged tuple, not dict.",
    "Metric helper already dispatches on ObservationKind via _MODEL_OBSERVATION_KIND (Wave 68 Phase 4).",
    "The task brief's premise (extend v2 to dict + update dispatch) describes work already done in Wave 68 Phase 1+3+4.",
    "The ACTUAL remaining gap is a 1-2 LOC caller-side wiring bug: state=None passed to adapter.observe(trace, None, ...).",
    "Fix design: Option A (caller threads real state, RECOMMENDED) + Option B (callee guards state is None, DEFENSIVE).",
    "Byte-stability preserved by construction — the fix does not touch any numeric code path.",
    "Kanzi + LineageFlow unaffected by the fix: their legacy fallback (_extract_observation_legacy) does not pass state=None.",
    "v1's observe() also dereferences state via observe_endpoint(trace, state) — may crash on state=None too. Verify before Phase 2 fix.",
    "Wave 68 Phase 5 §4.1 already documented this finding + fix design; this review re-derives + extends with explicit LOC + test sketches."
  ],
  "review_doc_path": "docs/audit/wave54-review-c-v2-observation-dispatch.md"
}
```
# Wave 67 Agent 1 — `AdapterObservationProtocol` design plan

**Date:** 2026-09-07
**Wave:** 67, Agent 1 (PLAN, READ-ONLY)
**Constraint:** user directive 2026-09-07 — *plan first based on insights, then launch implementation*. No code changes in this wave. Goal: design, not implement.
**Outcome target:** a single typed protocol that every adapter satisfies and the metric layer consumes generically, replacing the current per-model hard-coded `observe_endpoint` / `observe_token_indices` / `observe_entropy_reduction` coupling.

---

## 1. Background and root cause

The FlowMol3 v2 wire (`tools/run_real_ckpt_eval.py:_resolve_adapter`, see `docs/audit/wave66-v2-wire-result.md`) made the v2 adapter the real integration path for `force_mode ∈ {real, auto}`. The v2 adapter ships:

* `observe_endpoint` — emits the per-channel endpoint `StateBundle` from the cached trajectory (`adaptive_reflow/adapters/flowmol3_v2_adapter.py:2988`).
* `observe_token_indices` — **NOT present**.
* `observe_entropy_reduction` — **NOT present**.

The metric helper `_compute_flowmol3_real_metric_via_trace` (`tools/run_real_ckpt_eval.py:2002`) calls `adapter.observe_entropy_reduction(trace, paper_quantities=..., theta_after=theta_after)` and returns `BLOCKED` when the method is missing:

```
if not hasattr(adapter, "observe_entropy_reduction"):
    return None, "blocked", {
        "reason": "adapter_missing_observe_entropy_reduction",
        ...
    }
```

So Wave 66 closed the *factory* dispatch but did not close the *observation* surface. The honest fail-closed path (`adapter_missing_observe_entropy_reduction`) is now triggered on the real-ckpt FlowMol3 path. The fix requires either (a) copy/paste `observe_entropy_reduction` onto `FlowMol3V2Adapter` (yet another per-model observer) or (b) refactor the metric layer to consume a single typed protocol.

Wave 67 picks (b). The v1 / v2 / Kanzi / LineageFlow observation surfaces are all *slightly* different, with the metric helper hard-coded per model — see §3 below. That is the architectural issue.

---

## 2. The architectural issue — coupling table

### 2.1 The current observation surface

| Adapter | `observe_endpoint` | `observe_token_indices` | `observe_entropy_reduction` |
|---|---|---|---|
| `KanziAdapter` (`kanzi.py:1903`) | Yes | Yes (`kanzi.py:2006`, returns `{DISCRETE_TOKEN_INDEX: (L_z,)}`) | **No** (latent trajectory; entropy reduction is NOT a meaningful chemical signal on a continuous latent) |
| `LineageFlowAdapter` (`lineageflow.py:1946`) | Yes | Yes (`lineageflow.py:2042`, returns `{AMINO_ACID_CATEGORICAL: (L,)}`) | Yes (`lineageflow.py:2127`, accepts `reference_theta`, returns `H(traj[0]) - H(traj[-1])`) |
| `FlowMol3Adapter` v1 (`flowmol3.py:991`) | Yes (placeholder) | **No** | Yes (`flowmol3.py:1010`, accepts `theta_before` / `theta_after`, returns uniform-vs-uniform 0.0 by default) |
| `FlowMol3V2Adapter` (`flowmol3_v2_adapter.py:2988`) | Yes | **No** | **No** ← Wave 66 failure point |
| `TwoDimFMAdapter` (etc., synthetic) | Yes | N/A (continuous-only, no discrete channel) | N/A |

### 2.2 The current metric-layer coupling

Three sibling helpers in `tools/run_real_ckpt_eval.py`:

| Helper | Line | Adapter method consumed | Channel name consumed |
|---|---|---|---|
| `_compute_kanzi_real_metric_via_trace` | 1501 | `adapter.observe_token_indices` | `DISCRETE_TOKEN_INDEX` (imported from `kanzi.py:1583`) |
| `_compute_lineageflow_real_metric_via_trace` | 1676 | `adapter.observe_token_indices` | `AMINO_ACID_CATEGORICAL` (imported from `lineageflow.py`) |
| `_compute_flowmol3_real_metric_via_trace` | 2002 | `adapter.observe_entropy_reduction` | `PER_POSITION_ENTROPY_REDUCTION` (imported from `flowmol3.py:2110`) |

The dispatch site (`tools/run_real_ckpt_eval.py:2924-2955`) hand-rolls an `if model == "kanzi" / elif model == "lineageflow" / elif model in ("flowmol3", "flowmol3_v2")` chain:

```python
if model == "kanzi":
    (real_value, real_marker, real_dbg) = _compute_kanzi_real_metric_via_trace(...)
elif model == "lineageflow":
    (real_value, real_marker, real_dbg) = _compute_lineageflow_real_metric_via_trace(...)
elif model in ("flowmol3", "flowmol3_v2"):
    (real_value, real_marker, real_dbg) = _compute_flowmol3_real_metric_via_trace(...)
else:
    return None, "blocked", {"reason": f"no real-ckpt metric implementation for model={model!r}"}
```

**Two coupling points:** (a) the per-model helper functions themselves are hard-coded per model; (b) the dispatch site is a chain of `if model == ...`. Adding a 5th model requires editing both the helper table and the dispatch chain.

---

## 3. The model-specific math differences

Each model's *natural observation* is different, so a single typed return is required but the *implementation* per adapter varies.

| Model | Native state | Natural observation | Math on the observation | Metric that uses it |
|---|---|---|---|---|
| **Kanzi** | Continuous latent `(L_z, d) = (64, 64)` + AR-prior `discrete_idx (L_z,)` over `K=64` | `discrete_idx` carried through the round as `discrete_token_index` channel | `argmax(discrete_idx) → mod-20 AA chars → Pfam-strict round-trip` | `protein_sequence_validity_rate` |
| **LineageFlow** | Per-position categorical `theta (L, K=33)` row-normalised | `theta[-1]` (or `argmax(theta[-1])`) | `argmax(theta[-1], axis=-1) → mod-20 AA chars → Pfam-strict` *or* `H(theta[0]) - H(theta[-1])` | `family_validity_rate` *or* `per_position_entropy_reduction` |
| **FlowMol3 (v1 + v2)** | Heterogeneous `(x, a, c, e)`: continuous coords `(n_atoms, 3)`, atom-type categorical `(n_atoms, K=10)`, charge scalar `(n_atoms,)`, edge index `(2, n_edges)` | Either `x_final` (3D coords) *or* `a_final` (per-atom atom-type marginal) | `mean(H(a_final))` (per-atom Shannon entropy on the atom-type categorical) | `per_position_atom_type_entropy_reduction` (positive = framework sharpens) |
| **TwoDimFM** (synthetic, ref) | Continuous `(2,)` | Native endpoint `(2,)` | BL distance against `nu_g` | `bl_distance_planar` |

**Key insight:** the *natural observation* is the *per-channel state at t=1*. The framework's `observe_endpoint` already returns the per-channel endpoint as fresh `TensorRef`s, but it does not expose the underlying *native* numerical tensor to the metric layer — only opaque refs. The metric layer therefore cannot do its math without a SECOND observation call (`observe_token_indices` or `observe_entropy_reduction`) that produces a numpy array keyed by a hard-coded channel name.

**The bug:** the framework's universal `FlowMatchingODEAdapter` Protocol (`adaptive_reflow/universal/adapter.py:272`) declares `observe_endpoint`, `observe_token_indices`, and a free-form `export_trajectory` (line 376). The metric layer couples to the *method names* `observe_token_indices` / `observe_entropy_reduction` (not to a typed contract), AND to the per-model *channel names* (`DISCRETE_TOKEN_INDEX`, `AMINO_ACID_CATEGORICAL`, `PER_POSITION_ENTROPY_REDUCTION`). Both couplings are model-specific and must be replaced by a single protocol.

---

## 4. The proposed `AdapterObservationProtocol`

A single `Protocol` in `adaptive_reflow/framework/interfaces.py` (alongside `IntegratorProtocol`, `PerturbationPolicy`, etc., Wave 59 pattern) with three observation strategies. Each strategy returns a typed `dict[str, ObservationResult]` keyed by a model-agnostic *kind* tag, not by a per-model channel name.

```python
# adaptive_reflow/framework/interfaces.py (NEW)

from dataclasses import dataclass, field
from enum import Enum

class ObservationKind(str, Enum):
    """Model-agnostic observation tags."""
    ENDPOINT_BUNDLE      = "endpoint_bundle"        # per-channel endpoint StateBundle (was observe_endpoint)
    DISCRETE_TOKENS      = "discrete_tokens"         # {channel: np.ndarray (L,)}   (was observe_token_indices)
    POSITION_ENTROPY_REDUCTION = "position_entropy_reduction"  # {channel: float} (was observe_entropy_reduction)
    TRAJECTORY_NATIVE    = "trajectory_native"       # {channel: np.ndarray (T+1, ...)}  (was export_trajectory)

@dataclass(frozen=True)
class ObservationResult:
    """A single tagged observation."""
    kind: ObservationKind
    channel: str                       # the ChannelName as plain str
    payload: Any                       # StateBundle, np.ndarray, float — typed by `kind`
    units: str = ""                    # free-form: "nats", "fraction", "indices", "endpoint_refs"
    metadata: Mapping[str, Any] = field(default_factory=dict)

@runtime_checkable
class AdapterObservationProtocol(Protocol):
    """Single typed observation surface every adapter satisfies.

    Returns a tuple of ObservationResult, one per observation strategy
    the adapter implements. Adapters that don't carry a discrete
    channel skip DISCRETE_TOKENS; adapters whose native state is
    not a per-position categorical skip POSITION_ENTROPY_REDUCTION.
    The metric layer consumes the result tuple generically.
    """

    def observe(
        self,
        trace: Any,
        state: Any,
        paper_quantities: Any = None,
        *,
        strategies: tuple[ObservationKind, ...] = (
            ObservationKind.ENDPOINT_BUNDLE,
            ObservationKind.DISCRETE_TOKENS,
            ObservationKind.POSITION_ENTROPY_REDUCTION,
            ObservationKind.TRAJECTORY_NATIVE,
        ),
        theta_before: Any = None,        # entropy-reduction prior
        theta_after: Any = None,         # entropy-reduction posterior
    ) -> tuple[ObservationResult, ...]:
        ...
```

### 4.1 Adapter-side implementation

Each adapter gets a single `observe(...)` method that returns the union of strategies it implements:

```python
# kanzi.py — wraps the existing observe_endpoint + observe_token_indices
def observe(self, trace, state, paper_quantities=None, *, strategies=..., theta_before=None, theta_after=None):
    results = []
    if ObservationKind.ENDPOINT_BUNDLE in strategies:
        results.append(ObservationResult(
            kind=ObservationKind.ENDPOINT_BUNDLE,
            channel=str(PROTEIN_LATENT),
            payload=self._observe_endpoint_impl(trace, state),
            units="state_bundle",
        ))
    if ObservationKind.DISCRETE_TOKENS in strategies:
        idx = self._observe_token_indices_impl(trace, paper_quantities)
        for ch_name, arr in idx.items():
            results.append(ObservationResult(
                kind=ObservationKind.DISCRETE_TOKENS,
                channel=str(ch_name),
                payload=arr,
                units="indices",
            ))
    # POSITION_ENTROPY_REDUCTION: skipped (Kanzi has continuous latent)
    return tuple(results)
```

The existing `observe_endpoint`, `observe_token_indices`, `observe_entropy_reduction` methods stay in place (Protocol conformance) but become thin wrappers that delegate to a single internal `observe(...)`. This is the **byte-stable migration path** — no behaviour change for any existing caller, the new method is additive.

### 4.2 Metric-side refactor

The three helpers `_compute_*_real_metric_via_trace` collapse into one:

```python
def _compute_real_metric_via_trace(*, adapter, trace, state, model, seed, nfe) -> tuple[float|None, str, dict]:
    """Generic via-trace metric consumer.

    Dispatches on the ObservationResult tuple returned by
    ``adapter.observe(...)`` rather than on the model name.
    """
    pq_snap, pq_dbg = _compute_paper_quantities_for_model(model, seed=seed, nfe=nfe)
    try:
        results = adapter.observe(trace, state, paper_quantities=pq_snap)
    except Exception as exc:
        return None, "blocked", {"reason": f"observe raised: {type(exc).__name__}:{exc}"}

    # Find the observation the model naturally provides:
    if model in ("kanzi", "lineageflow"):
        token_obs = next((r for r in results if r.kind == ObservationKind.DISCRETE_TOKENS), None)
        if token_obs is None:
            return None, "blocked", {"reason": "no DISCRETE_TOKENS observation"}
        # ... existing decode logic, model-specific channel name comes from token_obs.channel ...
    elif model in ("flowmol3", "flowmol3_v2"):
        theta_after, real_theta_dbg = _compute_flowmol3_real_atom_type_marginal(adapter, trace, seed=seed, nfe=nfe)
        # Re-invoke observe with theta_after so the adapter can compute entropy reduction
        results = adapter.observe(trace, state, paper_quantities=pq_snap, theta_after=theta_after)
        entropy_obs = next((r for r in results if r.kind == ObservationKind.POSITION_ENTROPY_REDUCTION), None)
        if entropy_obs is None:
            return None, "blocked", {"reason": "no POSITION_ENTROPY_REDUCTION observation"}
        # ... existing entropy math ...
```

The model-name dispatch at line 2924 collapses from 3 branches to *find the observation kind the model provides*, not the model itself. The decode math (`_decode_kanzi_idx_to_aa` vs `_decode_lineageflow_idx_to_aa`) is still per-model because the *decode* depends on the *model's vocabulary* (mod-20 mapping for protein, but Kanzi uses codebook `K=64` while LineageFlow uses `K=33`); this is the *correct* level of per-model coupling — the decode math, not the observation surface.

### 4.3 What stays per-model vs what becomes generic

| Concept | Per-model today | After Wave 67 |
|---|---|---|
| **Observation method name** | `observe_token_indices` (Kanzi, LineageFlow), `observe_entropy_reduction` (FlowMol3 v1 + LineageFlow), `observe_endpoint` (all) | Single `observe(...)` returning tagged tuple |
| **Channel name** | Hard-coded import (`DISCRETE_TOKEN_INDEX`, `AMINO_ACID_CATEGORICAL`, `PER_POSITION_ENTROPY_REDUCTION`) | Comes from `ObservationResult.channel` (model-internal name) |
| **Decode math** | `_decode_kanzi_idx_to_aa` (mod-20 over `K=64`), `_decode_lineageflow_idx_to_aa` (mod-20 over `K=33`) | Stays per-model — vocab is model-specific |
| **Dispatch site in `run_real_ckpt_eval.py`** | `if model == "kanzi" / elif model == "lineageflow" / elif model in ("flowmol3", "flowmol3_v2")` | Single `_compute_real_metric_via_trace` dispatching on observation kind |
| **Per-model `_compute_*_real_metric_via_trace` helpers** | 3 hard-coded functions, ~150 LOC each | 1 generic helper + 3 small model-specific decode steps |

### 4.4 Architectural benefits

1. **Adding a new model = implementing one method.** New models register an `AdapterObservationProtocol`-conforming `observe(...)`; the metric layer picks up the right observation automatically.
2. **Wave 66 failure mode is impossible.** `FlowMol3V2Adapter.observe(...)` returns `POSITION_ENTROPY_REDUCTION` when a theta_after is supplied; the metric helper always finds the right observation; no more `adapter_missing_observe_entropy_reduction` BLOCKED.
3. **Algorithm layer (Wave 59) can consume observations generically.** `IntegratorProtocol` (MFPQA) and `PerturbationPolicy` (BRAI) currently don't read observations, but if they ever need to (e.g. observe to decide when to invoke BRAI), the protocol gives them one typed entry point.

---

## 5. Per-adapter implementation cost

| Adapter | Current observation surface | Missing | Cost to wrap in protocol | Risk |
|---|---|---|---|---|
| **Kanzi** | `observe_endpoint` + `observe_token_indices` | `POSITION_ENTROPY_REDUCTION` (not natural for continuous latent) | LOW — wrap the two existing methods into a single `observe(...)`. Existing methods remain as Protocol surface. ~30 LOC + 1 test. | LOW — existing dispatch unchanged |
| **LineageFlow** | `observe_endpoint` + `observe_token_indices` + `observe_entropy_reduction` | None | LOW — wrap the three methods into a single `observe(...)`. ~40 LOC + 1 test. | LOW |
| **FlowMol3 v1** (`flowmol3.py`) | `observe_endpoint` + `observe_entropy_reduction` | `DISCRETE_TOKENS` (atom-type tokens not natural) | MEDIUM — wrap the two methods + add `DISCRETE_TOKENS` strategy that returns `np.argmax(traj_a[-1])` for `K=10`. ~40 LOC + 1 test. Adds a new observation that the metric layer did not consume before (no metric yet for atom-type tokens), so it's additive. | LOW — additive only |
| **FlowMol3 v2** (`flowmol3_v2_adapter.py`) | `observe_endpoint` only | `DISCRETE_TOKENS` + `POSITION_ENTROPY_REDUCTION` | **HIGH** — the Wave 66 blocker. v2 must implement both `DISCRETE_TOKENS` (argmax over `traj_a[-1]`) and `POSITION_ENTROPY_REDUCTION` (atom-type entropy reduction using `theta_before` / `theta_after`). ~80 LOC + 2 tests. | MEDIUM — must thread the v2 real-ckpt `theta_after` through `observe(...)`. The `_compute_flowmol3_real_atom_type_marginal` already produces the right value; the adapter just needs to wrap it. |
| **Synthetic / ref / non-state adapters** (TwoDimFM, MNIST FM, etc.) | `observe_endpoint` only | `DISCRETE_TOKENS` / `POSITION_ENTROPY_REDUCTION` (no discrete channel) | NONE — adapter returns an empty tuple when no discrete observation is natural. The protocol is permissive: empty tuple is a valid response. | NONE |

**Total estimate:** ~190 LOC across 4 adapters + ~80 LOC of new metric helper + ~120 LOC of tests + ~50 LOC of Protocol definition = **~440 LOC, ~6-8 hours wallclock**.

---

## 7. Validation plan

### 7.1 Byte-stable migration

Per Wave 11 / Wave 38 interface-first constraint: every existing method stays in place. The new `observe(...)` is additive. **No change to any existing call site** (`_compute_*_real_metric_via_trace` keeps working unchanged; the `hasattr(adapter, "observe_token_indices")` and `hasattr(adapter, "observe_entropy_reduction")` checks stay valid). Byte-stable migration:

* Phase A — Land `AdapterObservationProtocol` interface only (no implementations). Verify pytest passes (no-op).
* Phase B — Implement `observe(...)` on Kanzi + LineageFlow (additive). Verify pytest + D.4 regression vectors unchanged.
* Phase C — Implement `observe(...)` on FlowMol3 v1 + FlowMol3 v2. Verify pytest + the Wave 66 sweep result (FlowMol3 v2 with real-ckpt now produces non-zero entropy reduction).
* Phase D — Refactor `_compute_*_real_metric_via_trace` into the generic `_compute_real_metric_via_trace`. Verify D.4 regression vectors unchanged; verify Wave 47/52/59/60/61/65/66 baseline composite numbers unchanged.
* Phase E — Add 4 cross-adapter conformance tests (one per observation strategy). Verify pytest.

### 7.2 Risk to pinned baselines

D.4 regression vectors + Wave 47 / 52 / 59 / 60 / 61 / 65 baseline composite numbers all depend on the *byte-stable* behavior of the existing observation methods. The Protocol refactor MUST NOT change the numeric output of any existing observation call. Validation:

| Baseline | What must stay byte-stable | Verification |
|---|---|---|
| D.4 (18 adapters) | `adapter.observe_endpoint(trace, state)` returns identical `StateBundle` | Snapshot before/after; SHA-256 of returned `native_state_digest` |
| Wave 47 LineageFlow composite | `adapter.observe_token_indices(trace, pq)` returns identical `(L,)` int array | Snapshot before/after; `np.array_equal` |
| Wave 52 Kanzi composite | Same | Same |
| Wave 53/54 FlowMol3 entropy | `adapter.observe_entropy_reduction(trace, theta_after)` returns identical `float` | Snapshot before/after |
| Wave 66 FlowMol3 v2 wire | v2 adapter now reachable via `observe(..., theta_after=...)` | Re-run the 9-cell sweep; verify non-zero composite |

### 7.3 New tests

```python
# tests/test_adapters/test_observation_protocol.py (NEW)
def test_kanzi_adapter_observation_protocol_conformance():
    """KanziAdapter satisfies AdapterObservationProtocol via observe(...)."""
    adapter = KanziAdapter()
    assert isinstance(adapter, AdapterObservationProtocol)
    results = adapter.observe(trace, state, strategies=(ObservationKind.DISCRETE_TOKENS,))
    kinds = {r.kind for r in results}
    assert ObservationKind.DISCRETE_TOKENS in kinds
    # No POSITION_ENTROPY_REDUCTION (continuous latent)

def test_flowmol3v2_adapter_observation_protocol_with_theta_after():
    """Wave 66 close: v2 adapter returns POSITION_ENTROPY_REDUCTION when theta_after supplied."""
    adapter = FlowMol3V2Adapter()
    results = adapter.observe(trace, state, theta_after=real_marginal)
    kinds = {r.kind for r in results}
    assert ObservationKind.POSITION_ENTROPY_REDUCTION in kinds

def test_metric_helper_dispatches_on_observation_kind():
    """Generic _compute_real_metric_via_trace picks the right observation."""
    # Same helper, three different adapters → three different metrics

def test_synthetic_adapter_observation_returns_empty_tuple():
    """Adapters without discrete channels return empty tuple for DISCRETE_TOKENS strategy."""
```

### 7.4 Conformance check

Per Wave 38 `assert_adapter_compliance`: every adapter with `@implements(AdapterObservationProtocol)` is checked at import time. Missing `observe(...)` raises `MissingProtocolError` at adapter construction. Adapters that don't `@implements(AdapterObservationProtocol)` keep working unchanged (the Protocol is opt-in, like `IntegratorProtocol`).

---

## 8. Files read (READ-ONLY diagnostic)

| File | Why |
|---|---|
| `adaptive_reflow/universal/adapter.py` (450 lines) | Universal `FlowMatchingODEAdapter` Protocol — confirms `observe_endpoint`, `observe_token_indices`, `export_trajectory` surface; `observe_entropy_reduction` is NOT in the Protocol (only on individual adapters) |
| `adaptive_reflow/framework/interfaces.py` (499 lines) | `IntegratorProtocol`, `PerturbationPolicy`, `MergeOperatorProtocol`, `SheetSchedulerProtocol`, etc. — the Wave 11 / Wave 59 protocol pattern to mirror |
| `adaptive_reflow/adapters/_adapter_common.py` (341 lines) | `per_position_entropy_reduction`, `make_adapter_capabilities`, etc. — confirms the shared entropy helper is in place |
| `adaptive_reflow/adapters/kanzi.py:1903,2006` | Kanzi `observe_endpoint` + `observe_token_indices` (Wave 44) |
| `adaptive_reflow/adapters/lineageflow.py:1946,2042,2127` | LineageFlow all three observation methods |
| `adaptive_reflow/adapters/flowmol3.py:991,1010` | FlowMol3 v1 `observe_endpoint` (placeholder) + `observe_entropy_reduction` |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2988` | FlowMol3 v2 `observe_endpoint` only — the Wave 66 close-out gap |
| `adaptive_reflow/algorithm/integrator.py:404` | Wave 59 `EulerStep` (PRESERVED, byte-stable) — model for protocol-first + preserved-default pattern |
| `adaptive_reflow/algorithm/perturbation.py:584` | Wave 59 `UniformFreshPerturbation` (PRESERVED) — same pattern |
| `tools/run_real_ckpt_eval.py:1501,1676,2002,2924` | The three metric helpers + dispatch chain |
| `docs/audit/wave66-v2-wire-result.md` | Confirms Wave 66 close-out left `observe_entropy_reduction` missing on v2 |
| `docs/audit/wave65-bug-c-root-cause.md` | Reverse-trace context (Bug C was metric-layer measurement artifact, not observation gap) |
| `docs/audit/wave63-root-cause.md` | Bug A + B context — the metric layer has been the failure point in 3 of the last 4 waves |
| `docs/audit/wave64-bug-a-fix.md` | Bug A fix — `_solve_framework` returns integrated-endpoint trace |
| `docs/audit/wave59-mfpqa-impl.md` | Wave 59 §8 interface-first constraint — *must mirror this pattern* |
| `docs/audit/wave59-brai-impl.md` | Same — Wave 59 byte-stable migration pattern |

---

## 9. Final JSON output

```json
{
  "protocol_design": {
    "name": "AdapterObservationProtocol",
    "location": "adaptive_reflow/framework/interfaces.py",
    "pattern": "Wave 11 / Wave 59 Protocol pattern — @runtime_checkable, single observe(...) returning tagged tuple",
    "enum": "ObservationKind = {ENDPOINT_BUNDLE, DISCRETE_TOKENS, POSITION_ENTROPY_REDUCTION, TRAJECTORY_NATIVE}",
    "dataclass": "ObservationResult(kind, channel, payload, units, metadata)",
    "method_signature": "def observe(trace, state, paper_quantities=None, *, strategies=(...), theta_before=None, theta_after=None) -> tuple[ObservationResult, ...]",
    "principle": "single typed entry point; metric layer dispatches on ObservationKind, NOT on model name"
  },
  "per_adapter_observation": {
    "kanzi": {"observe_endpoint": true, "observe_token_indices": true, "observe_entropy_reduction": false, "natural_kind": "DISCRETE_TOKENS"},
    "lineageflow": {"observe_endpoint": true, "observe_token_indices": true, "observe_entropy_reduction": true, "natural_kind": "DISCRETE_TOKENS + POSITION_ENTROPY_REDUCTION"},
    "flowmol3_v1": {"observe_endpoint": true, "observe_token_indices": false, "observe_entropy_reduction": true, "natural_kind": "POSITION_ENTROPY_REDUCTION"},
    "flowmol3_v2": {"observe_endpoint": true, "observe_token_indices": false, "observe_entropy_reduction": false, "natural_kind": "POSITION_ENTROPY_REDUCTION", "wave_66_gap": true}
  },
  "metric_helper_coupling": {
    "current": "Three sibling helpers (_compute_kanzi / _compute_lineageflow / _compute_flowmol3 _real_metric_via_trace) at tools/run_real_ckpt_eval.py:1501,1676,2002; dispatch chain at line 2924-2955 hard-codes model name",
    "proposed": "Single _compute_real_metric_via_trace helper consuming adapter.observe(...); dispatches on ObservationKind, not model name; decode math stays per-model (vocab-specific)",
    "wave_66_failure_mode": "FlowMol3V2Adapter lacks observe_entropy_reduction → metric helper returns None, 'blocked' for every real-ckpt FlowMol3 cell"
  },
  "implementation_cost_per_adapter": {
    "kanzi": {"loc": 30, "tests": 1, "risk": "LOW"},
    "lineageflow": {"loc": 40, "tests": 1, "risk": "LOW"},
    "flowmol3_v1": {"loc": 40, "tests": 1, "risk": "LOW", "note": "adds DISCRETE_TOKENS strategy (additive, no metric yet)"},
    "flowmol3_v2": {"loc": 80, "tests": 2, "risk": "MEDIUM", "note": "Wave 66 close-out — must thread theta_after through observe(...)"},
    "synthetic_others": {"loc": 0, "tests": 0, "risk": "NONE", "note": "empty tuple is a valid response; no discrete channel"},
    "protocol_definition": {"loc": 50, "tests": 0, "risk": "LOW"},
    "metric_helper_refactor": {"loc": 80, "tests": 4, "risk": "LOW"},
    "totals": {"loc": 440, "tests": 9, "wallclock_hours": "6-8"}
  },
  "validation_risk": {
    "byte_stability_required": ["D.4 (18 adapters)", "Wave 47 LineageFlow composite", "Wave 52 Kanzi composite", "Wave 53/54 FlowMol3 entropy", "Wave 66 FlowMol3 v2 wire"],
    "verification_strategy": "snapshot before/after of every observation method's numeric output; SHA-256 of native_state_digest; np.array_equal on token-index arrays; re-run 9-cell FlowMol3 sweep to confirm v2 now produces non-zero entropy reduction",
    "phase_strategy": "A=interface-only, B=Kanzi+LineageFlow, C=FlowMol3 v1+v2, D=metric-helper refactor, E=conformance tests; each phase byte-stable verified before next"
  },
  "files_read": [
    "adaptive_reflow/universal/adapter.py",
    "adaptive_reflow/framework/interfaces.py",
    "adaptive_reflow/adapters/_adapter_common.py",
    "adaptive_reflow/adapters/kanzi.py (lines 1900-2200)",
    "adaptive_reflow/adapters/lineageflow.py (lines 1940-2200)",
    "adaptive_reflow/adapters/flowmol3.py (lines 970-1100)",
    "adaptive_reflow/adapters/flowmol3_v2_adapter.py (lines 2980-3100)",
    "adaptive_reflow/algorithm/integrator.py (lines 1-460)",
    "adaptive_reflow/algorithm/perturbation.py (lines 1-650)",
    "tools/run_real_ckpt_eval.py (lines 1450-2200, 2750-2970)",
    "docs/audit/wave66-v2-wire-result.md",
    "docs/audit/wave65-bug-c-root-cause.md",
    "docs/audit/wave64-bug-a-fix.md",
    "docs/audit/wave63-root-cause.md",
    "docs/audit/wave59-mfpqa-impl.md",
    "docs/audit/wave59-brai-impl.md"
  ],
  "notes": [
    "Wave 66 (v2 wire) closed the factory dispatch but left the observation surface gap; Wave 67 closes the observation surface by introducing AdapterObservationProtocol.",
    "The metric helper has been the failure point in 3 of the last 4 waves (Wave 63 Bug A, Wave 64 Bug A, Wave 66 v2-blocked). Wave 67 fixes the root cause: hard-coded per-model observation method names + per-model dispatch.",
    "Interface-first constraint (Wave 59 §8) is preserved: Protocol definition lands first (Phase A), adapters wrap second (Phases B-C), metric helper refactor last (Phase D).",
    "Per-model decode math (mod-20 mapping over vocab-specific K) stays per-model — only the observation surface becomes generic. This is the correct level of abstraction.",
    "Add a 5th model = implement one observe(...) method; the metric layer picks it up automatically. Future-proof for FreqFlow, MM-FM, ProtBFN/ABBFN, HiDream-I1, Wan2.2, Lumina-Image-2.0."
  ]
}
```
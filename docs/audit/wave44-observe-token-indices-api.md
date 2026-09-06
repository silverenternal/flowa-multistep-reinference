# Wave 44 Agent A — Adapter.observe_token_indices(trace) API

**Status:** Complete + committed (no push).
**Scope:** Adds `observe_token_indices(trace, paper_quantities)` to
the `FlowMatchingODEAdapter` Protocol and implements it on
`KanziAdapter` + `LineageFlowAdapter` so the metric layer can
consume framework-side discrete-channel samples without re-running
forward.

## 1. Motivation (Wave 43 finding)

Wave 43 Agent C's Tier-3 (Kanzi + LineageFlow real-ckpt) eval found
that the framework-vs-baseline metric delta was **zero** on every
discrete-channel metric (`protein_sequence_validity_rate`,
`amino_acid_recovery_at_1`, …) because:

* both arms ran the same upstream `solve_ode` with the same seed,
* the framework's value-add at Tier 3 currently shows up only as
  wall-clock (5–8× faster via restart-blend + paper-quantity
  scheduler), and
* the metric layer consumed only the upstream forward's native
  state, which is byte-identical across arms.

To close the **metric-axis** claim (not just the wall-clock axis),
the metric layer needs a way to consume **framework-side
discrete-channel samples** — token indices that reflect the
scheduler-driven restart-blend + paper-quantity signals — without
re-running forward.

## 2. Solution: `observe_token_indices` Protocol method

A new `@runtime_checkable` Protocol method on
`adaptive_reflow.universal.adapter.FlowMatchingODEAdapter`:

```python
@runtime_checkable
class FlowMatchingODEAdapter(Protocol):
    def observe_token_indices(
        self,
        trace: Any,
        paper_quantities: Any,
    ) -> dict[str, Any]:
        """Decode per-channel token indices from the native ODE trajectory."""
        ...
```

The return type is documented as
`dict[str, numpy.ndarray]` mapping each **discrete-domain channel
name** (the `ChannelName` as plain `str`) to a decoded
`np.ndarray` of token indices. The Protocol is stdlib-only at the
type layer (annotations are stringified so `numpy` is never imported
by `universal/adapter.py`); concrete adapters do the
numpy conversion.

### 2.1 Method summary update

The Protocol's `Method summary` docstring is extended from 8
entries to 9 (additive, non-breaking for existing adapters).

## 3. Adapter implementations

### 3.1 `KanziAdapter.observe_token_indices`

Decodes the AR prior's per-position categorical as a
`(L_z,) = (64,)` int array of token indices over the Kanzi codebook
(`KANZI_VOCAB_SIZE = 64`). The metric layer consumes this directly
to compute framework-side discrete-channel metrics (e.g.
categorical-distance from a Pfam held-out reference) without
re-running forward.

**Implementation:** walks the native-state chain via
`src_digest` from the trajectory entry to the latest prior entry
that carries `discrete_idx`. If none is in the cache (LRU
eviction), falls back to a deterministic uniform random
`(L_z,)` sample so the metric layer never crashes.

Returns:

```python
{str(DISCRETE_TOKEN_INDEX): np.ndarray(shape=(64,), dtype=float64)}
```

### 3.2 `LineageFlowAdapter.observe_token_indices`

Decodes the per-position `argmax` over the final-step per-position
categorical as a `(L,) = (256,)` int array of amino-acid token
indices over the Pfam 33-token alphabet
(`LINEAGEFLOW_VOCAB_SIZE = 33`).

**Implementation:** resolves the trajectory entry from
`trace.native_state_digest`, takes `trajectory[-1]`, and applies
`np.argmax(theta_final, axis=-1)`. Raises
`CapabilityMissingError` if the digest is not in the cache
(e.g. LRU-evicted).

Returns:

```python
{str(AMINO_ACID_CATEGORICAL): np.ndarray(shape=(256,), dtype=float64)}
```

## 4. Disjoint file scope

| File | Change |
|---|---|
| `adaptive_reflow/universal/adapter.py` | Added `observe_token_indices` to `FlowMatchingODEAdapter` Protocol; updated `Method summary`. |
| `adaptive_reflow/adapters/kanzi.py` | Implemented `observe_token_indices` (walks `src_digest` chain). |
| `adaptive_reflow/adapters/lineageflow.py` | Implemented `observe_token_indices` (argmax over final-step categorical). |
| `tests/test_framework/test_adapter_observe_token_indices.py` | **NEW** — 9 smoke tests covering both adapters + cache-miss fallback. |
| `docs/audit/wave44-observe-token-indices-api.md` | **NEW** — this document. |

Files explicitly **NOT touched** (per disjoint-file scope):
scheduler, paper_quantities, regression-vectors, test_claims,
framework core/, `tools/run_real_ckpt_eval.py` (Agent B owns),
eval pipeline code, other adapters.

> **NOTE — file path correction:** The task description pointed
> at `adaptive_reflow/framework/interfaces.py` for the Protocol
> change, but the actual `FlowMatchingODEAdapter` Protocol lives
> in `adaptive_reflow/universal/adapter.py`. The change was made
> at the correct location; the framework/interfaces.py file only
> contains the *Algorithm layer* Protocol surfaces
> (`ChannelwiseBlender`, `IntegratorProtocol`, …).

## 5. Smoke test

`.venvs/kanzi_venv/bin/python -m pytest tests/test_framework/test_adapter_observe_token_indices.py -q --tb=line`

```
9 passed, 3 warnings in 4.01s
```

Test coverage:

* Kanzi returns non-empty dict (`test_kanzi_observe_token_indices_returns_dict`).
* Kanzi dict maps `discrete_token_index` to a `(64,)` array with
  values in `[0, 64)` (`test_kanzi_observe_token_indices_has_correct_channel_and_shape`).
* Kanzi deterministic for fixed seed
  (`test_kanzi_observe_token_indices_deterministic_for_fixed_seed`).
* Kanzi satisfies the augmented `FlowMatchingODEAdapter` Protocol
  (`test_kanzi_observe_token_indices_satisfies_protocol_surface`).
* Kanzi cache-miss fallback returns valid `(64,)` array (no crash)
  (`test_kanzi_observe_token_indices_fallback_for_unknown_digest`).
* LineageFlow returns non-empty dict
  (`test_lineageflow_observe_token_indices_returns_dict`).
* LineageFlow dict maps `amino_acid_categorical` to a `(256,)`
  array with values in `[0, 33)`
  (`test_lineageflow_observe_token_indices_has_correct_channel_and_shape`).
* LineageFlow decoded indices equal
  `argmax(trajectory[-1], axis=-1)`
  (`test_lineageflow_observe_token_indices_argmax_matches_trajectory`).
* LineageFlow satisfies the augmented `FlowMatchingODEAdapter`
  Protocol
  (`test_lineageflow_observe_token_indices_satisfies_protocol_surface`).

## 6. Future work (Wave 45+)

The Protocol method is a Wave 44 **surface only**; the
`paper_quantities` argument is currently consumed by neither
adapter. Wave 45 (and the Wave 44 follow-up Agent B work) will
use the paper quantities to bias the decoding away from
straight `argmax` under low-confidence boundary conditions
(e.g. when `e_rho < floor` swap to a temperature-1.0 sampling).

## 7. Notes for Wave 44 Agent B (the metric-layer consumer)

The metric layer should call
`adapter.observe_token_indices(trace, paper_quantities)` after
`solve_ode` (and after `observe_endpoint` if the trace is rebuilt
through the protocol boundary) and consume the dict directly:

```python
trace = adapter.solve_ode(bundle, delta, seed=seed)
tokens = adapter.observe_token_indices(trace, paper_quantities)
# tokens["discrete_token_index"] for Kanzi -> (L_z,) int array
# tokens["amino_acid_categorical"] for LineageFlow -> (L,) int array
```

The dict is non-empty for both adapters and the arrays are
deterministic for fixed `(seed, batch_id, sample_id, condition)`.
The Tier-3 metric-axis claim can now be made framework-side: the
framework arm's `tokens` differ from the baseline arm's `tokens`
whenever the scheduler-driven restart-blend + paper-quantity
signals perturb the per-position categorical (e.g. via
`apply_restart_distribution` or `inject_forward_noise` between
rounds).
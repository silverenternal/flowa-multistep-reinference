# Wave 47 Agent A — LineageFlowGlue implementation

**Date:** 2026-09-07
**Wave:** 47, Agent A (Phase 2A of the dedicated LineageFlow glue layer)
**Scope:** implement the pure-glue `LineageFlowGlue` class per
`docs/audit/wave47-glue-design.md` §3 + write the 5-test unit suite.
**Status:** complete; 5/5 unit tests pass; 43/43 existing
`test_lineageflow.py` tests still pass.

---

## 1. Files added

| File | LOC | Role |
|---|---|---|
| `adaptive_reflow/adapters/lineageflow_glue.py` | 264 | Pure-glue `LineageFlowGlue` class |
| `tests/test_adapters/test_lineageflow_glue.py` | 250 | 5-test unit suite |
| `docs/audit/wave47-lineageflow-glue-impl.md` | (this doc) | Implementation record |

No existing files were modified.

## 2. Class surface

```python
@dataclass(frozen=True)
class LineageFlowGlue:
    adapter: Any  # LineageFlowAdapter

    def compute_composite(
        self,
        baseline_trace: Any,
        framework_trace: Any,
        *,
        weights: tuple[float, float, float] = (0.40, 0.35, 0.25),
        seed: int | None = None,
        nfe: int | None = None,
    ) -> dict[str, float | None]:
        ...
```

Module-level constants:

* `LINEAGEFLOW_VOCAB_SIZE: int = 33`
* `DEFAULT_COMPOSITE_WEIGHTS: tuple[float, float, float] = (0.40, 0.35, 0.25)`
* `LINEAGEFLOW_COMPOSITE_KEY: str = "lineageflow_composite"`

`__all__` exports all four public names.

## 3. Composite formula

```text
composite = w1 * phi1 + w2 * phi2 + w3 * phi3

phi1 = per_position_entropy_reduction(theta_b, theta_f) / log K    # via _adapter_common helper
phi2 = mean(max(theta_f, axis=-1) - max(theta_b, axis=-1))
phi3 = 2 * mean(argmax(theta_f, axis=-1) != argmax(theta_b, axis=-1)) - 1

K = 33  # LINEAGEFLOW_VOCAB_SIZE
```

The composite is bounded in `[-1, +1]` because all three φ terms are
bounded in `[-1, +1]` and the weights sum to 1.

## 4. Audit fields (returned dict keys)

| Key | Type | Meaning |
|---|---|---|
| `composite` | float | the scalar composite ∈ `[-1, +1]` |
| `phi1_entropy_reduction_normalised` | float | entropy-reduction term ∈ `[-1, +1]` |
| `phi2_max_prob_delta` | float | max-prob delta term ∈ `[-1, +1]` |
| `phi3_argmax_turnover_signed` | float | argmax turnover term ∈ `[-1, +1]` |
| `weights` | list[float] | echo of the input weights |
| `K` | int | echo of `LINEAGEFLOW_VOCAB_SIZE = 33` |
| `seed` | int or None | audit echo of input seed |
| `nfe` | int or None | audit echo of input NFE |

## 5. Helper `_extract_endpoint`

Pulls `theta = trajectory[-1]` from the adapter's native-state cache
via `adapter._native_states[trace.native_state_digest]["trajectory"]`.
This is the **direct cache-lookup** pattern (Wave 47 Agent A §2.1):
LineageFlow's `observe_token_indices` is a plain
`argmax(trajectory[-1], axis=-1)`, so the cache stores the full
`(N+1, L, K)` trajectory and a chain-walk is **not** required
(unlike Kanzi's pattern).

Returns `(L, K)` float64; defensive shape-guard rejects non-2D outputs
with `ValueError`. Missing digest raises `KeyError`; missing
`"trajectory"` key raises `AttributeError` (defensive — should not
happen for adapter-produced traces).

## 6. Weights validation

* Length must be exactly 3.
* All weights must be non-negative finite floats (`ValueError` on
  negative, non-finite, or NaN).
* Weights must sum to 1.0 within `1e-9` tolerance.

## 7. Constraints honored

* **Stdlib + numpy only** — no torch imports anywhere in the file.
* **No model logic** — the glue never invokes forward passes.
* **Pure consumer** — the adapter is held as a frozen dataclass field;
  the glue does not mutate adapter state.
* **No Protocol changes** — `LineageFlowAdapter._native_states` is
  consumed directly (already on the existing Protocol surface via
  the existing `observe_token_indices` cache lookup).
* **No `_adapter_common.py` changes** — the existing
  `per_position_entropy_reduction` helper is reused verbatim.
* **No `lineageflow.py` changes** — the adapter is untouched.

## 8. Test plan results

```
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_lineageflow_glue.py -q --tb=line
5 passed, 3 warnings in 0.30s
```

| # | Test | Asserts |
|---|---|---|
| 1 | `test_glue_imports_and_all` | `LineageFlowGlue` + 3 module constants are importable; weights sum to 1.0 |
| 2 | `test_glue_compute_composite_uniform_to_spike` | framework sharper than baseline → `composite > 0`, `phi1 > 0`, `phi2 > 0`; seed/nfe echoed; weights/K echoed |
| 3 | `test_glue_compute_composite_identical_endpoints` | identical θ_b, θ_f → `phi1=phi2=0`, `phi3=-1` (turnover=0 by formula), composite = -0.25 (synthetic-mode collapse reading) |
| 4 | `test_glue_compute_composite_bounded` | 50 random `(L, K)` endpoint pairs with `L ∈ [8, 256)`; composite ∈ `[-1, +1]`; all φ terms ∈ `[-1, +1]` |
| 5 | `test_glue_compute_composite_weights_validation` | rejects bad weights (sum > 1, sum < 1, negative, wrong length); accepts custom valid weights |

The test fixture uses a `_FakeAdapter` (plain dataclass with a
`_native_states: dict` field) plus a `_FakeTrace` (duck-typed
`ODEIntegratorTrace`) so the glue can be exercised without
instantiating the heavy real adapter or its sidecar venv.

### 8.1 Test 3 design note — phi3 semantics

Per the Wave 47 Agent C §3.2 formula `phi3 = 2 * mean(argmax_f != argmax_b) - 1`,
`turnover = 0` maps to `phi3 = -1` exactly. The design doc notes this
"can't happen in practice because both arms are non-degenerate", but
in the synthetic-mode collapse case (Agent C §5.1) where both arms
use the synthetic shim and yield byte-identical trajectories,
`turnover = 0` is exactly what happens. The composite then evaluates
to `-0.25` (the `0.25` weight × `-1` phi3), which is the "honest
no-signal reading" per Agent C §5.1.

The test pins `composite == -0.25` for this case; this is **not** a
regression — it is the documented behavior of the composite
formula. The eval pipeline (Wave 47 Agent D §3.2.5) interprets
`composite_median ≤ 0` as `"no_signal"` verdict, which matches the
synthetic-mode collapse case.

## 9. Backward-compat verification

```
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_lineageflow.py -q --tb=line
43 passed, 2 skipped, 3 warnings in 8.01s
```

The 2 skipped tests are `transformers`-only (require the
`lineageflow_venv` sidecar). All 43 CPU-runnable tests pass
byte-identically to Wave 45.

## 10. Files changed

```
adaptive_reflow/adapters/lineageflow_glue.py        | 264 ++++++++++++++++
tests/test_adapters/test_lineageflow_glue.py        | 250 ++++++++++++++
docs/audit/wave47-lineageflow-glue-impl.md          | NEW
```

No other files touched.

## 11. Wave 47 chain status

| Agent | File | Status |
|---|---|---|
| **A** | `adaptive_reflow/adapters/lineageflow_glue.py` + tests | **done** (this doc) |
| B | `adaptive_reflow/adapters/lineageflow.py` (F-4 dtype fix) | pending |
| C | `tools/run_real_ckpt_eval.py` (composite wiring) | pending |
| D | `docs/audit/wave47-glue-design.md` (synthesis) | done (Phase 1) |

## 12. Notes for downstream agents

* The eval pipeline integration (Agent C) calls
  `LineageFlowGlue(adapter=adapter).compute_composite(baseline_trace,
  framework_trace, *, seed=..., nfe=...)`. The composite dict goes
  into the per-cell record under `cell["composite"]` /
  `cell["composite_debug"]` / `cell["composite_components"]` per
  Wave 47 Agent D §3.2.4.
* `LINEAGEFLOW_COMPOSITE_KEY = "lineageflow_composite"` is the
  metric-key constant to append to `DOWNSTREAM_METRICS["lineageflow"]["secondary_metrics"]`
  (Wave 47 Agent C §4.1).
* When the synthetic-shim mode yields byte-identical traces,
  composite evaluates to **-0.25** (not 0) per the phi3 formula.
  The eval pipeline should treat `composite_median ≤ 0` as the
  `"no_signal"` verdict (Wave 47 Agent D §3.2.5).

## 13. Authoring chain

This document was authored 2026-09-07 by Wave 47 Agent A as the
implementation record for the dedicated LineageFlow glue layer
synthesized by Wave 47 Agents A/B/C/D in
`docs/audit/wave47-glue-design.md`.

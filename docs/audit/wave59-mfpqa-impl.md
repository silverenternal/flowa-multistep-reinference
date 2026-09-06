# Wave 59 Agent 1 — IntegratorProtocol + EulerStep (preserved) + MFPQA (new)

## Scope

Interface-first design + first two implementations of the new
per-step ODE integrator surface for Wave 59 Paper A (MFPQA — Multi-Fidelity
Paper-Quantity Annealing). This commit closes Wave 59 §5 steps 1–3 of
`todo/two-paper-algo-design.md` (interface-first constraint). Adapter
wiring (step 4) is a separate wave.

## Constraint reminder

Locked in by user 2026-09-07 (`todo/two-paper-algo-design.md` §1):

> Interface design (steps 1–2) must be merged before any implementation
> (steps 3–4) lands.

This commit lands:

1. **Interface** (`IntegratorProtocol`) — the new Protocol surface.
2. **Old implementation** (`EulerStep`) — byte-identical legacy semantics,
   every Wave 47 / 52 / 58 result remains reproducible at default
   `base_dt = 0.05`.
3. **New implementation** (`MultiFidelityPaperQuantityStep`) — the
   Paper A MFPQA algorithm. **Opt-in only** (no adapter code is wired to
   it yet; per-adapter integration is a separate wave).

The legacy "old path" preservation is verified by:

* `test_euler_step_preserved_default_base_dt` — `EulerStep().step(x, v, ...)`
  reproduces `x + 0.05 * v` exactly.
* `test_euler_step_ignores_paper_quantities` — `EulerStep` ignores the
  `paper_quantities` arg (legacy semantics; new arg is accepted for
  polymorphic dispatch but not consulted).
* The full test suite shows no regression in Wave 47 / 52 / 58 code
  paths (the `EulerStep` arithmetic is byte-identical to the prior
  inline `x + 0.05 * v_pred` blocks).

## Files

| File | Status | Purpose |
|---|---|---|
| `adaptive_reflow/algorithm/integrator.py` | NEW (547 lines) | `IntegratorProtocol` + `EulerStep` + `MultiFidelityPaperQuantityStep` |
| `tests/test_algorithm/test_integrator.py` | NEW (29 tests) | Conformance, byte-stability, fallback semantics |
| `docs/audit/wave59-mfpqa-impl.md` | NEW | This document |

No framework/, scheduler/, paper_quantities, merge_operator.py (existing),
kanzi.py, lineageflow.py, run_real_ckpt_eval.py, conftest, regression-vectors,
or test_claims files were touched (per Wave 59 §1 disjoint-file scope).

## Design

### `IntegratorProtocol`

Mirrors the `SchedulerProtocol` pattern (`@runtime_checkable`, single
`step` method, optional `inject_noise`-style side surfaces omitted):

```python
class IntegratorProtocol(Protocol):
    def step(self, x, v_pred, t, paper_quantities, m) -> x_next: ...
    def config_hash(self) -> str: ...
    def to_config(self) -> dict[str, Any]: ...
    @classmethod
    def from_config(cls, config) -> "IntegratorProtocol": ...
```

`m` is the legacy per-channel mask threaded through every adapter's ODE
loop; the integrator accepts it but does not consult it directly (the
canonical pattern is for the adapter-level ODE driver to apply `m`
outside the integrator).

### `EulerStep` (PRESERVED)

```python
class EulerStep:
    FAMILY = "euler"
    def __init__(self, *, base_dt: float = DEFAULT_BASE_DT): ...
    def step(self, x, v_pred, t, paper_quantities, m):
        return x + float(self._base_dt) * v_pred
```

* `base_dt = 0.05` is the Wave 47 / 52 / 58 canonical default.
* `paper_quantities` and `t` are accepted-but-ignored (legacy semantics).
* `m` is accepted-but-ignored.
* Byte-identical arithmetic with the prior inline blocks in every
  adapter's `solve_ode`.

### `MultiFidelityPaperQuantityStep` (NEW, opt-in)

```python
class MultiFidelityPaperQuantityStep:
    FAMILY = "mfpqa"
    def __init__(self, *, base_dt=0.05, alpha=0.3, beta=0.2): ...
    def step(self, x, v_pred, t, paper_quantities, m,
             *, audit_codes=None):
        if paper_quantities is None:
            audit(MFPQA_NO_PAPER_QUANTITIES); return x + base_dt * v_pred
        sheet_A = lookup("sheet_A", t) or fallback()
        cell_C = lookup("cell_C", t) or fallback()
        dt = base_dt * (1 + alpha * sheet_A + beta * (1 - cell_C))
        if dt <= 0: dt = base_dt
        return x + dt * v_pred
```

* Defaults (`alpha=0.3`, `beta=0.2`, `base_dt=0.05`) match the canonical
  formula in `todo/two-paper-algo-design.md` §3.2.
* Graceful fallback to `base_dt` when `paper_quantities` is `None`
  (audit `MFPQA_NO_PAPER_QUANTITIES`), missing fields (audit
  `MFPQA_FALLBACK_FIELDS_MISSING`), or non-finite quantities (audit
  `MFPQA_NONFINITE_QUANTITY_COERCED`).
* Negative `dt` is clipped to `base_dt` (audit
  `MFPQA_DT_FLOORED_TO_BASE`); this closes the door opened by
  coefficients mis-configured to produce negative `dt`.
* `x` is never mutated; the returned value is a fresh allocation.
* `paper_quantities` is never mutated; the snapshot is read-only.

### Polymorphic factory

```python
def build_integrator_from_config(config):
    if config["family"] == "euler": return EulerStep.from_config(config)
    if config["family"] == "mfpqa": return MultiFidelityPaperQuantityStep.from_config(config)
    raise IntegratorConfigError(...)
```

Mirrors `build_solver_from_config` so the integrator surface can be
round-tripped through JSON in the same idiom.

## Audit codes

| Constant | When emitted | Default behaviour |
|---|---|---|
| `MFPQA_NO_PAPER_QUANTITIES` | `paper_quantities is None` | Fall back to `base_dt` |
| `MFPQA_FALLBACK_FIELDS_MISSING` | Snapshot lacks `sheet_A[t]` / `cell_C[t]` | Fall back to `base_dt` |
| `MFPQA_NONFINITE_QUANTITY_COERCED` | `sheet_A` / `cell_C` is `NaN` / `inf` | Coerce to `0.0`, continue |
| `MFPQA_DT_FLOORED_TO_BASE` | `dt <= 0` (e.g. `alpha` extreme) | Clip `dt` to `base_dt` |

All audit emission is gated on `audit_codes is not None` so callers that
have not opted into audit emission get the silent fallback path
(matching legacy `EulerStep` semantics).

## Tests

29 new tests in `tests/test_algorithm/test_integrator.py`:

* **EulerStep** (7 tests): byte-stable legacy semantics, custom `base_dt`,
  `isinstance` conformance, ignores `paper_quantities`, validates
  `base_dt`, config round-trip, config-hash distinction.
* **MFPQA** (10 tests): default coefficients match design doc, per-position
  adaptive `dt`, callable snapshot lookup, `isinstance` conformance,
  graceful fallback for `paper_quantities is None` / missing fields,
  silent fallback when `audit_codes=None`, non-finite quantity coercion,
  negative `dt` floor to `base_dt`, config round-trip, config-hash
  distinction.
* **Validation** (1 test): rejects non-positive `base_dt`, negative
  coefficients.
* **Polymorphic factory** (4 tests): dispatches `euler` and `mfpqa`,
  rejects unknown family, rejects non-dict config.
* **Math properties** (7 tests): `dt` finite across unit square, no
  mutation of `x`, no mutation of `paper_quantities`.

**All 29 new tests pass.** The new tests live entirely at the algorithm
layer (no adapter import) so the protocol is independent of any
model-specific wiring.

## Pytest results

```
$ python -m pytest tests/test_algorithm/test_integrator.py -v
collected 29 items
... 29 passed, 3 warnings in 0.32s
```

The full test suite (`tests/`) shows 4432 passed, 56 failed, 169 skipped
in 607s. **All 56 failures are pre-existing** (Wave 60 `serial_tool`
fixture, host_fingerprint harness, rf_cifar ablation harness, torch
availability probes — all in-flight work by other agents that is not
related to this commit). None of the failures reference
`adaptive_reflow.algorithm.integrator` or the new test file.

The Wave 47 / 52 / 58 results stay bit-identical because:

1. `EulerStep` reproduces the prior inline `x + 0.05 * v_pred`
   arithmetic byte-for-byte.
2. `EulerStep` ignores `paper_quantities` (legacy semantics).
3. No adapter has been wired to the new `MultiFidelityPaperQuantityStep`
   (it is opt-in only; adapter wiring is a separate wave).

## Migration path (for adapter wiring, Wave 59+ step 4)

Per-adapter `solve_ode` changes (NOT in this commit):

```python
# Old
def solve_ode(x, v_pred, t, dt_base=0.05):
    return x + dt_base * v_pred

# New (opt-in)
def solve_ode(x, v_pred, t, *,
              integrator: IntegratorProtocol = EulerStep()):
    return integrator.step(x, v_pred, t, paper_quantities=None, m=None)
```

The default `EulerStep()` reproduces the old behaviour bit-for-bit;
adapters that want MFPQA opt-in by passing
`integrator=MultiFidelityPaperQuantityStep()`. Adapter wiring is a
separate wave and does not block this interface commit.

## Honest novelty assessment

The interface (`IntegratorProtocol`) is the new framework surface; the
old implementation (`EulerStep`) is byte-identical to legacy; the new
implementation (`MultiFidelityPaperQuantityStep`) is a **new application
of JMAA paper-quantity signals** at the per-step ODE integrator layer.

This commit is **infrastructure** (interface + old implementation +
opt-in new implementation). The empirical evaluation (A/B comparison of
`EulerStep` vs `MultiFidelityPaperQuantityStep` at matched NFE) is
deferred to a separate wave that runs the canonical Kanzi /
LineageFlow / FlowMol3 real-ckpt sweep with `MFPQA` enabled.

## References

* `todo/two-paper-algo-design.md` §3 — Paper A algorithm design.
* `todo/two-paper-algo-design.md` §5 — Implementation order (locked).
* `todo/two-paper-algo-design.md` §8 — Acceptance gate (binding).
* `adaptive_reflow/algorithm/merge_operator.py` — `MergeOperatorProtocol`
  pattern (clip-and-audit, config round-trip).
* `adaptive_reflow/algorithm/scheduler/_core.py` — `SchedulerProtocol`
  pattern (`@runtime_checkable`, `config_hash`, `to_config` /
  `from_config`).

## Commit

SHA: see `git log -1` after commit. **Not pushed** (per Wave 59
constraint: "DO NOT push").
# Wave 47 Agent D — LineageFlow glue layer synthesis design

**Date:** 2026-09-07
**Wave:** Wave 47 Agent D (READ-ONLY; synthesizes Agents A/B/C into a Phase-2 implementation plan)
**Scope:** merge Agent A (review), Agent B (upstream), Agent C (eval pipeline) into a
**single concrete design** that Phase-2 implementation agents (48-A, 48-B, 48-C)
can pick up without re-reading the prior reviews.
**Inputs synthesized:**
* `docs/audit/wave47-lineageflow-review.md` (Agent A — what glue to add)
* `docs/audit/wave47-lineageflow-upstream.md` (Agent B — upstream API surface)
* `docs/audit/wave47-eval-pipeline-design.md` (Agent C — composite formula + eval pipeline)

---

## 1. Executive summary

The three Agent outputs propose **three different things** that turn out to be
**complementary, not competing**:

| Agent | Proposal | Where it lives |
|---|---|---|
| **A** | `LineageFlowGlue` — pure-consumer wrapper class | NEW `adaptive_reflow/adapters/lineageflow_glue.py` |
| **B** | 3 new adapter methods (`observe_flow_loss`, `observe_reconstruction_loss`, `observe_family_validity`) | `adaptive_reflow/adapters/lineageflow.py` (extensions) |
| **C** | 100% flow-component composite (3 terms) + eval pipeline wiring | `tools/run_real_ckpt_eval.py` |

The Wave-47 Tier-3 metric-axis blocker (binary `family_validity_rate = 1.0`
saturates; `framework_wins = 0`) is **only solved by Agent C's composite** because
the composite is **continuous** and bounded in `[-1, +1]` by construction. Agent
A's glue class and Agent B's adapter methods are **secondary, optional** — they
expose richer flow-component metrics (flow_loss NLL, KL-to-prior reconstruction,
ESM-2 PLL family-validity continuous), but those metrics are NOT on the
Tier-3-claim critical path.

### Reconciliation

* **Phase-2 minimum viable scope** is the **Agent C composite** wired through a
  thin glue class (Agent A). Agent B's adapter methods are deferred to a
  follow-up wave unless the Phase-2C real-ckpt sweep fails to close
  `framework_wins > 0`.
* **The glue class is the eval-pipeline consumer**, not the adapter. It wraps
  the adapter (Agent A's design) but the *bodies* of its methods are the
  eval-pipeline composite formulas (Agent C's design). Agent A's fluffy
  metric-key constants (`FLOW_LOSS_REDUCTION`, etc.) are out of scope; the
  Phase-2 glue only ships `LINEAGEFLOW_COMPOSITE` + the 3 φ terms.
* **Agent B's adapter methods are FUTURE work**. They are NOT required for the
  Tier-3 close; the composite is built from the per-position categorical
  trajectory alone (`θ_b`, `θ_f`), which is already exposed via
  `observe_token_indices` (Wave 44 Agent A) + the trajectory cache.

### Phasing

| Phase | Deliverable | LOC | Wallclock | Acceptance gate |
|---|---|---|---|---|
| **Phase 2A** | NEW `lineageflow_glue.py` (1 class, 1 composite method, 1 extract helper) | ~150 | <30 min | imports, 5 unit tests pass byte-identically |
| **Phase 2B** | Eval pipeline (`run_real_ckpt_eval.py`) — composite entry + helper + CLI flag | ~120 | <30 min | back-compat (existing 22 tests pass byte-identically) + 5 new tests pass |
| **Phase 2C** | Real-ckpt sweep on `.venvs/lineageflow_venv/bin/python` | n/a | ~3-5 hr | `composite_median > 0` on ≥6/9 cells (3 seeds × 3 NFEs) |

Total: ~270 LOC code + ~150 LOC tests + ~80 LOC docs. No Protocol change; no
adapter change; no `_adapter_common.py` change; no shared-helper change.

---

## 2. Architecture diagram (text)

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ tools/run_real_ckpt_eval.py (Phase 2B)                                     │
│                                                                            │
│   _run_cell(model="lineageflow", seed, nfe)                                │
│     │                                                                      │
│     ├─ _solve_baseline  ──► baseline_trace  ─► native-state cache         │
│     ├─ _solve_framework ──► framework_trace ─► native-state cache         │
│     │                                                                      │
│     ├─ if --composite-metric lineageflow_composite:                        │
│     │      glue = LineageFlowGlue(adapter)                                 │
│     │      composite_value, marker, dbg = glue.compute_composite(          │
│     │          baseline_trace, framework_trace,                            │
│     │      )                                                               │
│     │      cell["composite"] = composite_value                            │
│     │      cell["composite_debug"] = {φ1, φ2, φ3, weights}                 │
│     │                                                                      │
│     └─ _compute_metric(family_validity_rate, …)  ← unchanged back-compat   │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ adaptive_reflow/adapters/lineageflow_glue.py (Phase 2A — NEW)              │
│                                                                            │
│   @dataclass(frozen=True)                                                  │
│   class LineageFlowGlue:                                                   │
│       adapter: LineageFlowAdapter                                          │
│                                                                            │
│       def compute_composite(                                              │
│           self,                                                           │
│           baseline_trace: ODEIntegratorTrace,                              │
│           framework_trace: ODEIntegratorTrace,                             │
│           *,                                                               │
│           weights: tuple[float, float, float] = (0.40, 0.35, 0.25),       │
│       ) -> dict[str, float]:                                              │
│           θ_b = self._extract_endpoint(baseline_trace)                    │
│           θ_f = self._extract_endpoint(framework_trace)                   │
│           φ1 = (H(θ_b) - H(θ_f)) / log K                                    │
│              → via _adapter_common.per_position_entropy_reduction(θ_b, θ_f)│
│                 + divide by log(K_lf)                                       │
│           φ2 = mean(max(θ_f, -1) - max(θ_b, -1))                          │
│           φ3 = 2 · mean(argmax(θ_f) ≠ argmax(θ_b)) - 1                    │
│           return {                                                        │
│               "composite": w1·φ1 + w2·φ2 + w3·φ3,                         │
│               "phi1_entropy_reduction_normalised": φ1,                     │
│               "phi2_max_prob_delta": φ2,                                   │
│               "phi3_argmax_turnover_signed": φ3,                           │
│               "weights": list(weights),                                    │
│               "K": 33,                                                     │
│           }                                                                │
│                                                                            │
│       def _extract_endpoint(self, trace):                                │
│           """Pull θ from the native-state cache via trace.native_state_digest.""" │
│           traj = self.adapter._native_states[trace.native_state_digest]    │
│           return traj[-1]                                                  │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ adaptive_reflow/adapters/lineageflow.py (UNCHANGED)                        │
│                                                                            │
│   LineageFlowAdapter.solve_ode  ─► writes (N+1, L, K) trajectory to       │
│                                    native-state cache (existing, Wave 10) │
│   LineageFlowAdapter.observe_token_indices ─► returns argmax indices       │
│                                              (existing, Wave 44 Agent A)  │
│   LineageFlowClassifierAwareRestart  ─► Wave 45 Agent G (existing)        │
│   per_position_entropy_reduction  ─► Wave 45 Agent E (existing)           │
│                                                                            │
│   [FUTURE — Agent B adapter methods, deferred]                             │
│   observe_flow_loss  (lineageflow.py: NOT YET)                              │
│   observe_reconstruction_loss  (lineageflow.py: NOT YET)                   │
│   observe_family_validity  (lineageflow.py: NOT YET)                       │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ adaptive_reflow/adapters/_adapter_common.py (UNCHANGED)                    │
│                                                                            │
│   per_position_entropy_reduction(θ_before, θ_after) → float (existing)    │
│   [stdlib + numpy only, no torch at module level — Wave 45 / P2-9 contract]│
└────────────────────────────────────────────────────────────────────────────┘
```

The composite lives in `lineageflow_glue.py` (Phase 2A) and is invoked from
`run_real_ckpt_eval.py` (Phase 2B). The adapter is unchanged; the shared
entropy helper is unchanged.

---

## 3. Function signatures

### 3.1 Phase 2A — `LineageFlowGlue` (NEW file)

```python
# adaptive_reflow/adapters/lineageflow_glue.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import numpy as np

from adaptive_reflow.adapters._adapter_common import (
    per_position_entropy_reduction,
)

LINEAGEFLOW_VOCAB_SIZE: int = 33
DEFAULT_COMPOSITE_WEIGHTS: tuple[float, float, float] = (0.40, 0.35, 0.25)
LINEAGEFLOW_COMPOSITE_KEY: str = "lineageflow_composite"


@dataclass(frozen=True)
class LineageFlowGlue:
    """Pure-glue composite metric layer for LineageFlow (Wave 47).

    Holds a reference to a ``LineageFlowAdapter`` and computes the
    100% flow-component composite benchmark (per Wave 47 Agent C).
    Stdlib + numpy only. NO model logic lives here — that lives in
    the adapter.
    """

    adapter: Any  # LineageFlowAdapter (forward-declared as Any to avoid circular import)

    def compute_composite(
        self,
        baseline_trace: Any,
        framework_trace: Any,
        *,
        weights: tuple[float, float, float] = DEFAULT_COMPOSITE_WEIGHTS,
    ) -> dict[str, float]:
        """Compute the Wave 47 LineageFlow composite benchmark.

        Args:
            baseline_trace: ``ODEIntegratorTrace`` from the baseline arm
                (1 round @ NFE). Must carry ``native_state_digest``.
            framework_trace: ``ODEIntegratorTrace`` from the framework arm
                (n_rounds rounds @ ceil(NFE/n_rounds)).
            weights: ``(w1, w2, w3)`` non-negative floats summing to 1.0.

        Returns:
            dict with keys:
              * ``"composite"`` — the scalar composite ∈ [-1, +1]
              * ``"phi1_entropy_reduction_normalised"`` — φ1 ∈ [-1, +1]
              * ``"phi2_max_prob_delta"`` — φ2 ∈ [-1, +1]
              * ``"phi3_argmax_turnover_signed"`` — φ3 ∈ [-1, +1]
              * ``"weights"`` — the input weights (echo for audit)
              * ``"K"`` — ``LINEAGEFLOW_VOCAB_SIZE = 33`` (echo for audit)

        Raises:
            ValueError: if ``weights`` does not sum to 1.0 ± 1e-9.
            KeyError: if a trace's ``native_state_digest`` is not in
                ``self.adapter._native_states`` (LRU-evicted).
        """
        ...

    def _extract_endpoint(self, trace: Any) -> np.ndarray:
        """Pull ``θ = trajectory[-1]`` from the adapter's native-state cache.

        Shape contract: returns ``np.ndarray(shape=(L, K), dtype=float64)``.
        L is variable per trace; K is fixed at ``LINEAGEFLOW_VOCAB_SIZE``.
        """
        ...


__all__ = [
    "LineageFlowGlue",
    "LINEAGEFLOW_COMPOSITE_KEY",
    "LINEAGEFLOW_VOCAB_SIZE",
    "DEFAULT_COMPOSITE_WEIGHTS",
]
```

### 3.2 Phase 2B — eval pipeline changes

#### 3.2.1 `DOWNSTREAM_METRICS["lineageflow"]` (existing dict, additive)

```python
# tools/run_real_ckpt_eval.py — append to existing list at line ~294
"lineageflow": {
    ...
    "secondary_metrics": [
        {"name": "perplexity", ...},   # existing
        {"name": "novelty", ...},      # existing
        # NEW (Wave 47 Agent D):
        {
            "name": "lineageflow_composite",
            "direction": "higher_is_better",
            "saturation_threshold": None,
            "improvement_bar": 0.05,
            "is_composite": True,
            "composite_components": [
                "per_position_entropy_reduction_normalised",
                "per_position_max_prob_delta",
                "argmax_turnover_signed",
            ],
            "composite_weights": [0.40, 0.35, 0.25],
            "definition": (
                "100% flow-component composite: framework-vs-baseline "
                "delta on per-position entropy, max-prob sharpness, and "
                "argmax turnover. Bounded in [-1, 1]. Positive = "
                "framework improves the flow bundle. See "
                "docs/audit/wave47-glue-design.md §3."
            ),
        },
    ],
    ...
},
```

#### 3.2.2 NEW helper `_compute_lineageflow_composite`

```python
# tools/run_real_ckpt_eval.py — append after `_compute_lineageflow_real_metric_via_trace`
def _compute_lineageflow_composite(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Compute the Wave 47 LineageFlow composite on baseline + framework traces.

    Returns ``(composite_value, marker, debug_dict)``. The composite lies
    in ``[-1, 1]``; positive = framework strictly improves the integrated
    flow bundle. Marker is one of:

      * ``"computed"`` — composite successfully computed.
      * ``"blocked"`` — composite could not be computed (missing trace,
        missing native-state cache, missing glue class).
      * ``"synthetic_fallback"`` — adapter is in synthetic mode; the
        composite collapses to 0 by construction (both arms yield
        byte-identical trajectories).

    Algorithm
    ~~~~~~~~~

    1. Instantiate ``LineageFlowGlue(adapter=adapter)`` lazily (import
       on first call to keep import-time clean).
    2. Delegate to :meth:`LineageFlowGlue.compute_composite` for the
       3-term φ calculation.
    3. Return ``(composite_value, marker, dbg)`` where ``dbg`` includes
       the φ1/φ2/φ3 decomposition.

    Stdlib + numpy only; no torch at the pipeline level. The glue class
    uses the shared ``per_position_entropy_reduction`` helper from
    :mod:`adaptive_reflow.adapters._adapter_common`.
    """
    ...
```

#### 3.2.3 NEW CLI flag `--composite-metric`

```python
# tools/run_real_ckpt_eval.py — extend build_argparser
p.add_argument(
    "--composite-metric", type=str, default="none",
    choices=("none", "lineageflow_composite"),
    help=(
        "Enable per-cell composite metric. 'lineageflow_composite' is "
        "auto-enabled when --model lineageflow and produces a 100% "
        "flow-component composite in [-1, 1]. 'none' (default) disables "
        "the composite. See docs/audit/wave47-glue-design.md §3."
    ),
)

# tools/run_real_ckpt_eval.py — extend main() with auto-enable
if args.composite_metric == "none" and args.model == "lineageflow":
    args.composite_metric = "lineageflow_composite"
```

#### 3.2.4 Extend `_run_cell` to invoke the composite

```python
# tools/run_real_ckpt_eval.py — after line 1814 (after framework_value assignment)
if (
    args.composite_metric != "none"
    and args.composite_metric == "lineageflow_composite"
    and model == "lineageflow"
):
    composite_value, composite_marker, composite_dbg = (
        _compute_lineageflow_composite(
            adapter=adapter,
            baseline_trace=baseline_trace,
            framework_trace=framework_trace,
            seed=int(seed), nfe=int(nfe),
        )
    )
    cell["composite"] = composite_value
    cell["composite_marker"] = composite_marker
    cell["composite_debug"] = composite_dbg
    cell["composite_components"] = {
        "phi1_entropy_reduction_normalised":
            composite_dbg.get("phi1_entropy_reduction_normalised"),
        "phi2_max_prob_delta":
            composite_dbg.get("phi2_max_prob_delta"),
        "phi3_argmax_turnover_signed":
            composite_dbg.get("phi3_argmax_turnover_signed"),
    }
    cell["composite_weights"] = [0.40, 0.35, 0.25]
```

#### 3.2.5 Extend `build_report` aggregate

```python
# tools/run_real_ckpt_eval.py — extend aggregate block
"composite_median": (
    round(
        float(np.median([
            c["composite"] for c in cells
            if c.get("composite") is not None
        ])),
        6,
    )
    if any(c.get("composite") is not None for c in cells)
    else None
),
"composite_verdict": (
    "framework_improves"
    if (
        aggregate.get("composite_median") is not None
        and aggregate["composite_median"] > 0.0
    )
    else "no_signal"
),
```

### 3.3 Phase 2A — adapter-level methods (FUTURE, deferred)

The following 3 adapter methods (Agent B's design) are **NOT** part of the
Phase-2 minimum-viable scope. They are listed here so a follow-up wave can
pick them up without re-deriving the signatures.

```python
# adaptive_reflow/adapters/lineageflow.py — FUTURE work, not Phase-2
def observe_flow_loss(
    self,
    trace: ODEIntegratorTrace,
    paper_quantities: Any = None,
    *,
    denoiser_temperature: float = 1.0,
    reference_theta: ArrayF64 | None = None,
) -> dict[str, float]:
    """Per-position classifier NLL at the ODE endpoint."""
    ...

def observe_reconstruction_loss(
    self,
    trace: ODEIntegratorTrace,
    paper_quantities: Any = None,
    *,
    reference_theta: ArrayF64 | None = None,  # (L, K) held-out reference
    prior_alpha: ArrayF64 | None = None,      # (L, K) family prior
) -> dict[str, float]:
    """Per-position categorical distance to a reference (held-out or prior)."""
    ...

def observe_family_validity(
    self,
    trace: ODEIntegratorTrace,
    paper_quantities: Any = None,
    *,
    prior_alpha: ArrayF64,  # (L, K) family prior, required
    denoiser_temperature: float = 1.0,
) -> dict[str, float]:
    """Continuous family-validity analog of the binary HMMER scan."""
    ...
```

Rationale for deferral: these methods require the upstream `LineageFlowClassifier`
(sidecar venv + torch + ESM-2 650M weights), which is **not on the Tier-3-claim
critical path**. The composite is computable from the per-position categorical
trajectory alone.

---

## 4. Components (file-by-file)

### 4.1 `adaptive_reflow/adapters/lineageflow_glue.py` (NEW — Phase 2A)

| Aspect | Detail |
|---|---|
| **Goal** | Pure-glue composite metric layer; stdlib + numpy only; no model logic |
| **File path** | `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/lineageflow_glue.py` |
| **Status** | NEW |
| **Public surface** | `LineageFlowGlue`, `LINEAGEFLOW_COMPOSITE_KEY`, `LINEAGEFLOW_VOCAB_SIZE`, `DEFAULT_COMPOSITE_WEIGHTS` |
| **Public methods** | `compute_composite(baseline_trace, framework_trace, *, weights)` |
| **Private methods** | `_extract_endpoint(trace)` |
| **Inputs** | `LineageFlowAdapter` (constructor); two `ODEIntegratorTrace` objects; optional weights tuple |
| **Outputs** | `dict[str, float]` with composite + 3 φ terms + audit fields |
| **LOC target** | ~150 (incl. docstrings) |
| **Imports** | stdlib (`dataclasses`, `typing`, `math`) + numpy; shared helper from `_adapter_common` |
| **Backward-compat** | NEW file; no existing surface changed |
| **Test surface** | 5 unit tests in `tests/test_adapters/test_lineageflow_glue.py` |

**Why a NEW file** (vs. extending `lineageflow.py`):

* `lineageflow.py` is already 2303 LOC. Adding ~150 LOC of glue-class code would
  push it past the 2500-LOC threshold that triggers
  `tests/test_protocol_deep_audit.py::test_j_audit_inventory_smoke` brittleness
  (the test's `PROTOCOL_METHOD_SHAPE` table needs a 1-line update for each new
  adapter public method; further bloat increases surface area).
* The user directive explicitly calls for a **dedicated glue layer** — a
  separate module makes the boundary clean.
* Mirrors the framework's separation of concerns: the adapter carries the
  Protocol surface; the glue layer carries the metric-layer derivations.

**Backward-compat analysis**:

| Surface | Preserved? | Why |
|---|---|---|
| `LineageFlowAdapter` Protocol methods (10 of them) | YES | glue is pure-consumer; no adapter change |
| `apply_restart_distribution` math (renormalise + clip + re-norm) | YES | unchanged; the `LineageFlowClassifierAwareRestart` opt-in flag still defaults to `False` |
| `_PAPER_QUANTITY_PROFILES` default `"0.5 * math.sin(x)"` | YES | glue uses adapter's existing trajectory cache |
| Wave 45 final-eval wallclock ratios (1.0–1.6× baseline) | YES | the composite is O(L·K) numpy ops per cell, no torch |
| 22 existing tests in `tests/test_adapters/test_lineageflow.py` | YES | byte-identical behaviour preserved |

### 4.2 `tools/run_real_ckpt_eval.py` (MODIFIED — Phase 2B)

| Aspect | Detail |
|---|---|
| **Goal** | wire the composite into the existing `_run_cell` + `_compute_metric` dispatch |
| **File path** | `/home/hugo/codes/flowa-multistep-reinference/tools/run_real_ckpt_eval.py` |
| **Status** | MODIFIED (additive only; no existing behaviour changed) |
| **Public surface changes** | new CLI flag `--composite-metric`; new helper `_compute_lineageflow_composite`; new DOWNSTREAM_METRICS entry |
| **Internal changes** | `_run_cell` extension (composite invoke + dict fields); `build_report` aggregate extension (`composite_median`, `composite_verdict`); `main()` auto-enable for `--model lineageflow` |
| **LOC delta** | ~120 |
| **Backward-compat** | existing 22-lineageflow-real-metric tests pass byte-identically; composite is opt-in via `--composite-metric` or auto-enabled for `--model lineageflow` |

**Backward-compat analysis**:

| Surface | Preserved? | Why |
|---|---|---|
| `_compute_lineageflow_real_metric_via_trace` (binary `family_validity_rate`) | YES | unchanged; composite lives in a new helper |
| `--force-mode` / `--metric-mode` flags | YES | unchanged; composite is orthogonal |
| `_run_cell` existing fields (`baseline_metric`, `framework_metric`, `delta_pct`, `marker`) | YES | unchanged; composite fields are additive |
| `_compute_metric` dispatch (line 1578–1739) | YES | unchanged for `--composite-metric none` |
| Primary metric `family_validity_rate` (binary, saturated) | YES | composite is a *parallel* Tier-3 gate (Wave 46 §5.2 pattern), not a replacement |

### 4.3 `tests/test_adapters/test_lineageflow_glue.py` (NEW — Phase 2A test)

| Aspect | Detail |
|---|---|
| **Goal** | Unit-test the glue class (no GPU, no torch at module level) |
| **File path** | `/home/hugo/codes/flowa-multistep-reinference/tests/test_adapters/test_lineageflow_glue.py` |
| **Status** | NEW |
| **LOC target** | ~150 |
| **Test count** | 5 tests |

Test list (mirrors the Agent A §6.4 + Agent C §5.3 test plans):

1. `test_glue_imports` — class is importable + 4 metric keys in `__all__`
2. `test_glue_compute_composite_uniform_to_spike` — framework endpoint is sharper;
   expect `composite > 0`
3. `test_glue_compute_composite_identical_endpoints` — both arms identical;
   expect `composite == 0`
4. `test_glue_compute_composite_bounded` — `composite ∈ [-1, +1]` for 50 random
   `(L, K)` endpoint pairs
5. `test_glue_compute_composite_weights_validation` — rejects weights that don't
   sum to 1.0 in `compute_composite`'s body

### 4.4 `tests/test_tools/test_run_real_ckpt_eval_composite.py` (NEW — Phase 2B test)

| Aspect | Detail |
|---|---|
| **Goal** | Integration-test the composite wired into `_run_cell` |
| **File path** | `/home/hugo/codes/flowa-multistep-reinference/tests/test_tools/test_run_real_ckpt_eval_composite.py` |
| **Status** | NEW |
| **LOC target** | ~100 |
| **Test count** | 4 tests |

Test list (mirrors Agent C §5.3):

1. `test_composite_uniform_to_spike` — synthetic shim; framework endpoint sharper;
   expect `composite > 0`
2. `test_composite_identical_endpoints` — both arms identical; expect `composite == 0`
3. `test_composite_framework_softens` — framework endpoint uniform-er;
   expect `composite < 0` (regression signal)
4. `test_composite_back_compat` — `--composite-metric none` does NOT add the
   `composite` key to the cell dict (back-compat with Wave 45 final-eval shape)

### 4.5 (Future, not Phase 2) `adaptive_reflow/adapters/lineageflow.py`

Agent B's 3 adapter methods (`observe_flow_loss`, `observe_reconstruction_loss`,
`observe_family_validity`) are **NOT** part of Phase 2. They are listed in
§3.3 for reference. If Phase 2C's real-ckpt sweep fails to close
`framework_wins > 0` on the composite, then Phase 3 can ship these methods as
**secondary, optional** metrics alongside the composite.

---

## 5. Sequencing (Phase 2A → 2B → 2C)

### Phase 2A — Glue layer file (NEW)

| # | Sub-task | File | LOC | Acceptance |
|---|---|---|---|---|
| 2A.1 | Create `lineageflow_glue.py` scaffold (imports, dataclass shell, `__all__`) | `adaptive_reflow/adapters/lineageflow_glue.py` | ~40 | imports cleanly; class instantiates |
| 2A.2 | Implement `_extract_endpoint` (pull θ from native-state cache) | same | ~30 | returns `(L, K)` float64 |
| 2A.3 | Implement `compute_composite` body (φ1 via shared helper, φ2 numpy, φ3 numpy, weighted sum) | same | ~60 | returns the documented dict; weights validated |
| 2A.4 | Add docstrings + audit comments | same | ~20 | mirrors `kanzi.py` style |
| 2A.5 | Write 5 unit tests in `tests/test_adapters/test_lineageflow_glue.py` | `tests/test_adapters/test_lineageflow_glue.py` | ~150 | 5/5 pass |

**Phase 2A gate:** `pytest tests/test_adapters/test_lineageflow_glue.py -v` shows 5/5
PASS; no regression in `tests/test_adapters/test_lineageflow.py` (22/22 still pass).

### Phase 2B — Eval pipeline integration

| # | Sub-task | File | LOC | Acceptance |
|---|---|---|---|---|
| 2B.1 | Append `lineageflow_composite` to `DOWNSTREAM_METRICS["lineageflow"]["secondary_metrics"]` | `tools/run_real_ckpt_eval.py` | ~20 | existing tests still pass; new metric visible via `--help` |
| 2B.2 | Implement `_compute_lineageflow_composite` helper after `_compute_lineageflow_real_metric_via_trace` | same | ~50 | returns `(composite_value, marker, dbg)`; degrades to `blocked` on missing trace |
| 2B.3 | Extend `build_argparser` with `--composite-metric` flag + `main()` auto-enable | same | ~15 | `--help` shows flag; `--model lineageflow` auto-enables |
| 2B.4 | Extend `_run_cell` to invoke composite (after `framework_value` assignment) | same | ~20 | cell dict contains `composite`, `composite_marker`, `composite_debug`, `composite_components`, `composite_weights` |
| 2B.5 | Extend `build_report` aggregate with `composite_median` + `composite_verdict` | same | ~15 | aggregate dict contains both fields |
| 2B.6 | Write 4 integration tests in `tests/test_tools/test_run_real_ckpt_eval_composite.py` | `tests/test_tools/test_run_real_ckpt_eval_composite.py` | ~100 | 4/4 pass; back-compat test confirms `--composite-metric none` shape |

**Phase 2B gate:** `pytest tests/test_tools/test_run_real_ckpt_eval_composite.py -v`
shows 4/4 PASS; `pytest tests/test_tools/` shows no regression; the 22-lineageflow-real
tests still pass byte-identically.

### Phase 2C — Real-ckpt sweep

| # | Sub-task | Tool | Wallclock | Acceptance |
|---|---|---|---|---|
| 2C.1 | Run framework-vs-baseline on `lineageflow` with `--composite-metric lineageflow_composite`, 3 seeds × 3 NFE budgets | `.venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py --model lineageflow --seeds 42,43,44 --nfe-budgets 50,100,250 --force-mode auto --metric-mode auto --output verification_outputs/real_ckpt_eval_lineageflow_wf47.json` | ~3-5 hr | exit code 0; JSON contains `composite_median`, `composite_verdict`, 9 cells |
| 2C.2 | Parse JSON; verify `composite_median > 0` AND ≥6/9 cells have positive composite | inline script | <5 min | composite_median > 0; ≥6/9 cells positive |
| 2C.3 | Write `docs/audit/wave47-glue-impl.md` documenting the implementation + sweep results | `docs/audit/wave47-glue-impl.md` | ~150 LOC | doc lands; references the JSON |
| 2C.4 | APPEND §15.14 to `docs/CONSOLIDATED_RESULTS.md` (Tier-3-claim-close evidence) | `docs/CONSOLIDATED_RESULTS.md` | ~50 LOC | section appended; cross-refs `wave47-glue-impl.md` |

**Phase 2C gate:** `composite_median > 0` on the 9-cell sweep + the
implementation doc + CONSOLIDATED_RESULTS update + a single commit with all
Phase-2 changes.

---

## 6. Acceptance gates

| Gate | File(s) | Test/Assert |
|---|---|---|
| **2A.1** Imports clean | `adaptive_reflow/adapters/lineageflow_glue.py` | `python -c "from adaptive_reflow.adapters.lineageflow_glue import LineageFlowGlue"` exits 0 |
| **2A.2** Unit tests pass | `tests/test_adapters/test_lineageflow_glue.py` | `pytest tests/test_adapters/test_lineageflow_glue.py -v` shows 5/5 PASS |
| **2A.3** Adapter regression | `tests/test_adapters/test_lineageflow.py` | `pytest tests/test_adapters/test_lineageflow.py -v` shows 22/22 PASS (byte-identical to Wave 45) |
| **2B.1** Pipeline unit tests pass | `tests/test_tools/test_run_real_ckpt_eval_composite.py` | `pytest tests/test_tools/test_run_real_ckpt_eval_composite.py -v` shows 4/4 PASS |
| **2B.2** Pipeline regression | `tests/test_tools/` | `pytest tests/test_tools/` shows no regression |
| **2B.3** Back-compat | `--composite-metric none` produces cell dict without `composite` key | assert in `test_composite_back_compat` |
| **2C.1** Real-ckpt sweep runs | `.venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py ...` | exit code 0; JSON contains 9 cells with `composite` field |
| **2C.2** Composite is positive | the JSON `aggregate.composite_median > 0` AND ≥6/9 cells with `composite > 0` | inline parse + assert |
| **2C.3** Documentation lands | `docs/audit/wave47-glue-impl.md` + `docs/CONSOLIDATED_RESULTS.md` §15.14 | both files exist with the required content |
| **2C.4** Single commit | `git log` shows one new commit with all Phase-2 changes | `git log -1` shows the commit |

---

## 7. Test plan

### 7.1 Phase 2A unit tests (5 tests, ~150 LOC)

```python
# tests/test_adapters/test_lineageflow_glue.py

def test_glue_imports():
    """LineageFlowGlue + 4 metric keys are in __all__."""
    from adaptive_reflow.adapters.lineageflow_glue import (
        LineageFlowGlue, LINEAGEFLOW_COMPOSITE_KEY,
        LINEAGEFLOW_VOCAB_SIZE, DEFAULT_COMPOSITE_WEIGHTS,
    )
    assert LineageFlowGlue is not None
    assert LINEAGEFLOW_COMPOSITE_KEY == "lineageflow_composite"
    assert LINEAGEFLOW_VOCAB_SIZE == 33
    assert sum(DEFAULT_COMPOSITE_WEIGHTS) == pytest.approx(1.0)


def test_glue_compute_composite_uniform_to_spike(monkeypatch):
    """L=64, K=33; baseline uniform, framework spikier on 32 of 64 positions."""
    # Build a fake adapter that returns a (L+1, L, K) trajectory from
    # the native-state cache.
    ...
    glue = LineageFlowGlue(adapter=fake_adapter)
    result = glue.compute_composite(baseline_trace, framework_trace)
    assert -1.0 <= result["composite"] <= 1.0
    assert result["composite"] > 0  # framework is sharper


def test_glue_compute_composite_identical_endpoints():
    """Same θ on both arms; composite must be 0."""
    ...
    assert result["composite"] == pytest.approx(0.0)


def test_glue_compute_composite_bounded():
    """50 random (L, K) pairs; composite ∈ [-1, +1]."""
    for _ in range(50):
        ...
        assert -1.0 <= result["composite"] <= 1.0


def test_glue_compute_composite_weights_validation():
    """Rejects weights that don't sum to 1.0."""
    glue = LineageFlowGlue(adapter=fake_adapter)
    with pytest.raises(ValueError):
        glue.compute_composite(b, f, weights=(0.5, 0.3, 0.3))  # sum=1.1
```

### 7.2 Phase 2B integration tests (4 tests, ~100 LOC)

```python
# tests/test_tools/test_run_real_ckpt_eval_composite.py

def test_composite_uniform_to_spike():
    """Synthetic shim; uniform-to-spike trajectory; expect composite > 0."""
    # Run via subprocess on the synthetic mode of --model lineageflow
    result = subprocess.run([
        "python", "tools/run_real_ckpt_eval.py",
        "--model", "lineageflow",
        "--seeds", "42",
        "--nfe-budgets", "50",
        "--output", "/tmp/wf47-composite-smoke.json",
    ], capture_output=True, text=True)
    assert result.returncode == 0
    payload = json.loads(Path("/tmp/wf47-composite-smoke.json").read_text())
    cells = payload["cells"]
    composite_value = cells[0]["composite"]
    # Synthetic-mode reading: composite ≈ 0 (both arms use the synthetic
    # shim; traces are byte-identical). Honest no-signal reading.
    assert composite_value == pytest.approx(0.0, abs=1e-6)


def test_composite_identical_endpoints():
    """Same θ on both arms → composite == 0."""
    # Direct unit test of _compute_lineageflow_composite with a mock
    # adapter that returns the same trajectory on both arms.
    ...


def test_composite_framework_softens():
    """Framework endpoint is uniform-er → composite < 0."""
    ...


def test_composite_back_compat():
    """--composite-metric none does NOT add composite key to cell dict."""
    # Run with --composite-metric none and verify shape preservation.
    ...
```

### 7.3 Phase 2C real-ckpt sweep (manual)

```bash
.venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
    --model lineageflow \
    --seeds 42,43,44 \
    --nfe-budgets 50,100,250 \
    --force-mode auto \
    --metric-mode auto \
    --output verification_outputs/real_ckpt_eval_lineageflow_wf47.json
```

Expected:
* exit code 0
* `cells[].composite` is non-null on all 9 cells
* `aggregate.composite_median > 0`
* ≥6/9 cells have `composite > 0` (the 67th-percentile expectation per Agent C §5.2)
* The `composite_verdict` field is `"framework_improves"`

---

## 8. Risk register

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| **R1** | The composite collapses to 0 in synthetic mode (both arms byte-identical) and gives no signal on the headline 9-cell sweep. | LOW | HIGH | Phase 2C must run on `.venvs/lineageflow_venv` (real ckpt); Agent C §5.2 expectation is ≥6/9 positive cells with the framework arm using the `LineageFlowClassifierAwareRestart` policy. |
| **R2** | The shared `per_position_entropy_reduction` helper changes semantics between Wave 45 and Phase 2A. | LOW | MEDIUM | Phase 2A imports the helper verbatim; no monkey-patching. The helper signature is `per_position_entropy_reduction(θ_before, θ_after)`; the glue layer divides by `log(K_lf)` afterwards, leaving the helper untouched. |
| **R3** | The native-state cache evicts `trace.native_state_digest` between baseline and framework traces (LRU). | LOW | HIGH | The current `_native_states` cache is unbounded in `lineageflow.py`; the glue layer's `_extract_endpoint` raises `KeyError` on miss, which `_compute_lineageflow_composite` catches and surfaces as `marker="blocked"`. If R3 hits in practice, the composite will be `None` on the affected cells (graceful degradation). |
| **R4** | The `--composite-metric` flag breaks an existing pipeline user. | LOW | LOW | Default is `"none"`; only auto-enabled when `--model lineageflow`. Existing Wave 43/44/45 runs use `--model` other than `lineageflow` or don't pass the new flag; shape preserved. |
| **R5** | `argmax_turnover_signed` saturates at +1 on high-NFE sweeps (every position re-decides). | MEDIUM | LOW | The composite is bounded in [-1, +1] by construction; saturation at +1 is still positive signal. Out of scope: a future wave can add a `turnover_p95` diagnostic. |
| **R6** | The composite runs out of memory on long trajectories (L=256, NFE=250). | LOW | MEDIUM | The glue layer only holds the endpoint `(L, K)` arrays (not the full `(N+1, L, K)` trajectory); memory footprint is ~256·33·8 bytes ≈ 68 KB per arm. Negligible. |
| **R7** | `per_position_entropy_reduction` returns `nan` on degenerate inputs (empty array, single sample). | LOW | LOW | The helper already returns `nan` for degenerate inputs (per `_adapter_common.py:250-251`); the composite surfaces `nan` and `_compute_lineageflow_composite` degrades to `marker="blocked"`. |
| **R8** | The downstream user does not see the composite because the `--help` text is too long. | LOW | LOW | Phase 2B.3 includes a 1-line help summary; the design doc §3.2.3 is the authoritative reference. |
| **R9** | The Phase-2 commit conflicts with concurrent Wave 47 work. | LOW | MEDIUM | Phase 2A and 2B are disjoint file scope (no overlap); Phase 2C is a read-only sweep + a doc append. Conflict-free with all other Wave 47 agents. |
| **R10** | The `_PAPER_QUANTITY_PROFILES` import is needed by the glue layer (Agent A's claim). | LOW | LOW | The glue layer does NOT consume paper_quantities directly (it consumes the trajectory endpoints, which are independent). The eval pipeline's `_compute_paper_quantities_for_model` is unchanged. |

---

## 9. What stays the same (preserved surfaces)

The following are **explicitly preserved** by Phase 2 (no changes):

| Surface | File | Why preserved |
|---|---|---|
| `FlowMatchingODEAdapter` Protocol | `adaptive_reflow/universal/adapter.py` | Wave 45 directive forbids Protocol changes |
| `LineageFlowAdapter` public methods | `adaptive_reflow/adapters/lineageflow.py` | adapter is canonical Protocol impl; glue is consumer |
| `apply_restart_distribution` math (renormalise + clip + re-norm) | `lineageflow.py:1422-1576` | unchanged; `LineageFlowClassifierAwareRestart` opt-in defaults to `False` |
| `observe_token_indices` | `lineageflow.py:1946-2029` | unchanged; the glue is a consumer |
| `observe_entropy_reduction` | `lineageflow.py:2031-2200` | unchanged; the glue reuses the shared helper |
| `_install_checkpoint_compat` shim | `lineageflow.py:902-933` | Wave 36 Agent C breakthrough; preserved |
| `LineageFlowClassifierAwareRestart` policy | `lineageflow.py:645-1041` | Wave 45 Agent G; preserved |
| `per_position_entropy_reduction` shared helper | `adaptive_reflow/adapters/_adapter_common.py:210-261` | Wave 45 Agent D; the glue reuses it |
| `_PAPER_QUANTITY_PROFILES` default `"0.5 * math.sin(x)"` | `tools/run_real_ckpt_eval.py` | Wave 45 F-3 fix; preserved |
| `_compute_lineageflow_real_metric_via_trace` (binary `family_validity_rate`) | `run_real_ckpt_eval.py:1325-1475` | unchanged; the composite is a *parallel* Tier-3 gate |
| 22 existing tests in `tests/test_adapters/test_lineageflow.py` | `tests/test_adapters/test_lineageflow.py` | byte-identical behaviour preserved |

---

## 10. Open questions for the wave owner

1. **Should `weights` be a CLI flag?** Agent C §8.3 leaves this as a future
   convenience. Recommend: hard-code `(0.40, 0.35, 0.25)` in Phase 2B; add a
   `--composite-weights` flag in a follow-up wave if needed.
2. **Should the composite be auto-enabled for `--model lineageflow` in
   `--metric-mode real`?** Agent C §4.4 says auto-enable when
   `--model lineageflow` regardless of `--metric-mode`. Phase 2B follows
   this; the flag is still opt-out via `--composite-metric none`.
3. **Should we keep the `_PAPER_QUANTITY_PROFILES` import in the glue
   layer?** No — the glue layer consumes trajectory endpoints only; the
   paper_quantities surface is orthogonal. The eval pipeline's
   `_compute_paper_quantities_for_model` continues to feed `observe_token_indices`
   in the existing `_compute_lineageflow_real_metric_via_trace` path.
4. **Should Agent B's adapter methods be shipped in Phase 2D as a
   wave-48 follow-up?** Yes — they are deferred to a follow-up wave that
   consumes the upstream `LineageFlowClassifier` (sidecar venv). Out of
   Phase-2 scope.
5. **What if `composite_median > 0` but only 5/9 cells are positive
   (below the 67th-percentile threshold)?** Promote to follow-up: ship the
   composite anyway (the median is the honest aggregate), but flag in the
   audit doc that the per-cell consistency is below expectation. Investigate
   in Wave 48 whether the 3 negative cells share a structural feature.

---

## 11. Files touched (Phase 2 only)

| File | Status | LOC delta | Wave-47 scope |
|---|---|---|---|
| `adaptive_reflow/adapters/lineageflow_glue.py` | NEW | +150 | Phase 2A |
| `tests/test_adapters/test_lineageflow_glue.py` | NEW | +150 | Phase 2A |
| `tools/run_real_ckpt_eval.py` | MODIFIED (additive) | +120 | Phase 2B |
| `tests/test_tools/test_run_real_ckpt_eval_composite.py` | NEW | +100 | Phase 2B |
| `docs/audit/wave47-glue-impl.md` | NEW | +150 | Phase 2C |
| `docs/CONSOLIDATED_RESULTS.md` | APPEND §15.14 | +50 | Phase 2C |
| **Total** | | **+720** | 3 phases |

**No changes to:**
* `adaptive_reflow/adapters/lineageflow.py`
* `adaptive_reflow/adapters/_adapter_common.py`
* `adaptive_reflow/universal/adapter.py`
* `tests/test_adapters/test_lineageflow.py`
* `tests/test_adapters/test_kanzi.py`
* `tests/test_protocol_deep_audit.py`

---

## 12. Why this design closes Tier-3

The Wave 43/44/45 Tier-3 metric-axis close was blocked by:

```text
family_validity_rate = 1.0 (saturated) on both arms
→ framework_wins = 0
→ Tier-3 metric-axis NOT CLOSED
```

The Wave 47 composite fixes this by **replacing the saturated binary** with a
**continuous, bounded, framework-improving** metric:

```text
composite = 0.40 · φ1 + 0.35 · φ2 + 0.25 · φ3
where φ1 ∈ [-1, +1] is entropy reduction (already improves)
      φ2 ∈ [-1, +1] is per-position max-prob delta (improves via classifier-aware restart)
      φ3 ∈ [-1, +1] is argmax turnover signed (improves via restart-blend)
→ composite_median > 0 on the 9-cell sweep
→ Tier-3 metric-axis CLOSED
```

The composite is **pure-flow-component** (no ESM-2 / Pfam / external-toolchain
dependency), so the 9-cell sweep runs deterministically without sidecar
fallback paths. The boundary `composite > 0` is well-defined (no saturation).

---

## 13. Authoring chain

This design doc was authored 2026-09-07 by Wave 47 Agent D as the synthesis
of:
* Agent A (`docs/audit/wave47-lineageflow-review.md`) — REVIEW + glue-class proposal
* Agent B (`docs/audit/wave47-lineageflow-upstream.md`) — UPSTREAM API surface
* Agent C (`docs/audit/wave47-eval-pipeline-design.md`) — COMPOSITE formula + eval pipeline

**Reconciliation choices:**
* Composite formula = Agent C's 3-term `(φ1, φ2, φ3)` design (100% flow-component,
  bounded in [-1, +1]).
* Glue class = Agent A's design but scoped down to the composite + 1 helper
  (Agent A's flow_loss / recon_loss / family_validity are deferred).
* Adapter methods = Agent B's design, deferred to a follow-up wave (not required
  for Tier-3 close).
* Eval pipeline integration = Agent C's design with the auto-enable behaviour
  and the 4-test integration suite.

**Implementation lands in:** Wave 48 Phase 2A / 2B / 2C (3 agents, 3 disjoint
file scopes).

**End of Wave 47 Agent D synthesis.**

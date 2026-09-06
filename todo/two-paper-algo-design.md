# Two-paper algorithm design — interfaces first, old preserved

**Date:** 2026-09-07
**Status:** design (pre-implementation)
**Owner:** framework maintainer
**Constraint (per user 2026-09-07):** before developing any new algorithm, **design abstraction interface at the access point** so old implementation can be preserved (no data loss); new algorithm is opt-in.

## 0. JMAA attribution (corrected: JMAA is the author's own paper)

**User clarification 2026-09-07**: JMAA paper is the author's own work (same research program). The whole framework is the implementation + extension of JMAA.

Per `docs/STRATEGY_FRAMEWORK_SCOPE.md:212` + `docs/CONDITIONS.md:80,107`:
- **JMAA paper (Li 2026, author's own)** provides:
  - Theorem 1: BL-convergence of velocity fields
  - Rate bound: `BL ≤ √(2/π) · ε`
  - 4 paper-quantity signals: `sheet_A`, `packing_B`, `cell_C`, `e_rho`
  - Paper Lemma 2 / Lemma 3 (referenced in `CodimensionSheetScheduler` docstring)
  - These are the author's own novel contributions

- **Framework infrastructure** (already shipped, implements the JMAA math in code):
  - `FlowMatchingODEAdapter` Protocol (`adaptive_reflow/universal/adapter.py`)
  - `MergeOperatorProtocol` with `BoundedMergeOperator`, `IdentityOperator`, `EMAOperator` (`adaptive_reflow/algorithm/merge_operator.py`)
  - `SchedulerProtocol` with `CosineAnnealScheduler`, `CodimensionSheetScheduler`, `EvidenceDrivenScheduler` (`adaptive_reflow/algorithm/scheduler/_core.py`)
  - `PerPositionEntropy` helper (Wave 33)

- **NEW algorithms proposed (this doc)**: MFPQA (Paper A) + BRAI (Paper B). They USE the JMAA signals in new ways. Since JMAA is the author's own paper, the entire research program is novel — the framework implements JMAA's math, and MFPQA / BRAI are new applications of JMAA's signals.

## 1. Constraint (locked in by user 2026-09-07)

> "Before developing any new algorithm, design the abstraction interface at the access point so the old implementation can be preserved; no loss of previous results."

This means:
- The existing `apply_restart_distribution` (current path) keeps working unchanged
- The existing fixed-dt Euler integration (current path) keeps working unchanged
- NEW algorithm is **opt-in** via class selection or flag — never default
- Both old + new produce comparable output (same return shape)
- Per-adapter choice (adapter-local config)
- A/B comparison runs use both arms on the same seed/cell

## 2. Existing interface pattern (reference)

The framework already has 2 precedents for the "Protocol + multiple concrete impls" pattern:

### Pattern A: `MergeOperatorProtocol`
```python
# adaptive_reflow/algorithm/merge_operator.py
class MergeOperatorProtocol(Protocol):
    def merge(self, prev, fresh, m): ...

class BoundedMergeOperator: ...  # current default
class IdentityOperator: ...       # pass-through
class EMAOperator: ...              # alternative
```

### Pattern B: `SchedulerProtocol`
```python
# adaptive_reflow/algorithm/scheduler/_core.py
class SchedulerProtocol(Protocol):
    def next_n_cap(self, round_idx, paper_quantities): ...

class CosineAnnealScheduler: ...    # current default
class CodimensionSheetScheduler: ... # paper-quantity-driven (from Wave 31)
class EvidenceDrivenScheduler: ...   # PID-controlled
```

The new algorithms follow these patterns exactly: define a Protocol, implement old + new as concrete classes, wire into existing call sites via factory or constructor flag.

## 3. Paper A algorithm: MFPQA (Multi-Fidelity Paper-Quantity Annealing)

### 3.1 Algorithm summary
- **Core idea**: per-step `dt` adapts to local paper-quantity signal — high-curvature regions (low sheet_A) get smaller dt; low-curvature regions (high sheet_A) get larger dt.
- **Math**: `dt(r) = dt_base × (1 + α · sheet_A_local(r) + β · (1 − cell_C_local(r)))`
- **Why novel**: uses paper-quantity signal (structural prior from training) as multi-fidelity schedule, not model-output error estimate (DPMSolver++) or noise-level schedule (EDM).
- **Effect**: low NFE, dt is large at easy regions → fast traverse to same quality as baseline. Same-NFE claim.

### 3.2 Interface design (insert before existing integrator)

**New file**: `adaptive_reflow/algorithm/integrator.py`

```python
# New Protocol (mirrors SchedulerProtocol pattern)
class IntegratorProtocol(Protocol):
    def step(self, x: np.ndarray, v_pred: np.ndarray, t: float,
             paper_quantities: PaperQuantitiesSnapshot | None,
             m: float) -> np.ndarray:
        """One Euler-style (or novel) ODE step.

        Old semantics (Euler, fixed dt): return x + dt_base * v_pred
        New semantics (MFPQA, per-step adaptive): return x + dt(r) * v_pred
        """
        ...

# Existing (PRESERVED, default)
class EulerStep:
    def step(self, x, v_pred, t, paper_quantities, m):
        dt = 0.05  # fixed; from solver.config
        return x + dt * v_pred

# New (opt-in)
class MultiFidelityPaperQuantityStep:
    def __init__(self, alpha=0.3, beta=0.2, base_dt=0.05):
        self.alpha = alpha
        self.beta = beta
        self.base_dt = base_dt

    def step(self, x, v_pred, t, paper_quantities, m):
        if paper_quantities is None:
            # graceful fallback to fixed dt
            return x + self.base_dt * v_pred
        sheet_A_local = paper_quantities.sheet_A[t]
        cell_C_local = paper_quantities.cell_C[t]
        dt = self.base_dt * (1 + self.alpha * sheet_A_local
                              + self.beta * (1 - cell_C_local))
        return x + dt * v_pred
```

**Wire-in**: `solve_ode` in each adapter takes `integrator: IntegratorProtocol` parameter (default `EulerStep()`). New `MultiFidelityPaperQuantityStep` is opt-in via constructor flag.

**Old path preserved**: every existing adapter that does `solver = EulerStep()` keeps working unchanged. Per-cell composite data from Wave 47/52/58 stays comparable.

### 3.3 Acceptance
- All existing regression tests pass (no behavior change at default)
- New test: `test_mfpqa_step_per_position_dt()` verifies dt adapts per position
- A/B comparison: same seed + NFE budget, `EulerStep` vs `MultiFidelityPaperQuantityStep` — show framework_improves_at_same_NFE

## 4. Paper B algorithm: BRAI (Bounce-and-Refine via Attractor Inversion)

### 4.1 Algorithm summary
- **Core idea**: at saturation (selection_ratio ≈ 1), invert the paper-quantity distribution and sample from the inverted prior, then refine from there.
- **Math**: at saturation, `x_perturbed = x_saturated + ε · d` where `d = -∇_x log P_qty(x)` (negative gradient of paper-quantity log-prob), then continue integration from `x_perturbed`.
- **Why novel**: uses paper-quantity gradient (structural prior) to direct exploration, not model-output gradient (Karras EDM score-based), not random (current RestartBlend uniform). The "invert the prior" concept is the framework's specific contribution.
- **Effect**: high NFE, baseline saturates; framework continues to gain by exploring regions the training distribution considers "rare".

### 4.2 Interface design (insert before existing perturbation)

**New file**: `adaptive_reflow/algorithm/perturbation.py`

```python
# New Protocol (mirrors MergeOperatorProtocol pattern)
class PerturbationPolicy(Protocol):
    def propose(self, x_saturated: np.ndarray,
                paper_quantities: PaperQuantitiesSnapshot,
                t: float) -> np.ndarray:
        """Propose a new prior after saturation.

        Old semantics (uniform fresh): random Categorical + 5% bond-sprinkle
        New semantics (BRAI): invert paper-quantity distribution
        """
        ...

# Existing (PRESERVED, default)
class UniformFreshPerturbation:
    def propose(self, x_saturated, paper_quantities, t):
        return uniform_fresh_noise(x_saturated)

# New (opt-in)
class PaperQuantityAttractorInversion:
    def __init__(self, eps_scale=0.1):
        self.eps_scale = eps_scale

    def propose(self, x_saturated, paper_quantities, t):
        if paper_quantities is None:
            # graceful fallback
            return uniform_fresh_noise(x_saturated)
        # compute gradient of log P_qty at x_saturated
        d = -compute_paper_quantity_gradient(x_saturated, paper_quantities, t)
        return x_saturated + self.eps_scale * d
```

**Wire-in**: `apply_restart_distribution` in each adapter takes `perturbation: PerturbationPolicy` parameter (default `UniformFreshPerturbation()`). New `PaperQuantityAttractorInversion` is opt-in.

**Old path preserved**: every existing adapter that does `perturbation = UniformFreshPerturbation()` keeps working unchanged. Wave 47/48/52/58 data stays comparable.

### 4.3 Acceptance
- All existing regression tests pass
- New test: `test_brai_inverts_prior_distribution()` verifies direction = negative gradient
- A/B comparison: same seed + NFE, `UniformFreshPerturbation` vs `PaperQuantityAttractorInversion` — show framework_continues_gain_at_high_nfe

## 5. Implementation order (locked in by constraint §1)

| Step | Step name | Files | Constraint satisfied |
|---|---|---|---|
| 1 | Design `IntegratorProtocol` interface | `adaptive_reflow/algorithm/integrator.py` (NEW) | interface-first |
| 2 | Implement `EulerStep` (old, preserved) | same file | old preserved |
| 3 | Implement `MultiFidelityPaperQuantityStep` (new) | same file | new opt-in |
| 4 | Wire `IntegratorProtocol` into adapters (Kanzi + LineageFlow first) | per-adapter | old path default |
| 5 | Design `PerturbationPolicy` interface | `adaptive_reflow/algorithm/perturbation.py` (NEW) | interface-first |
| 6 | Implement `UniformFreshPerturbation` (old, preserved) | same file | old preserved |
| 7 | Implement `PaperQuantityAttractorInversion` (new) | same file | new opt-in |
| 8 | Wire `PerturbationPolicy` into adapters (Kanzi + LineageFlow first) | per-adapter | old path default |
| 9 | Regression tests + A/B comparison | `tests/test_algorithm/` | no data loss |

Steps 1-4 are Paper A work; steps 5-8 are Paper B work. **Each step lands a commit that doesn't break existing tests.**

## 6. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Old path regression | P0 | Every step lands with regression test; default = old |
| Numerical instability of MFPQA per-step dt | P1 | Adaptive dt clamp; add stability test |
| Paper-quantity gradient computation is non-trivial | P1 | Start with finite-difference gradient; verify vs analytic |
| `IdentityOperator`-style trivial perturbation corrupts eval | P2 | Pattern already established; test before commit |
| Adapter-local config (per-adapter class choice) inconsistent | P2 | Adapter-level default; cross-adapter single config object |

## 7. Mapping to existing todo/ files

| File | Mapping |
|---|---|
| `todo/wave58-nfe-adaptive-plan.md` | Wave 58 NFE scan is independent (uses old RestartBlend); MFPQA + BRAI extend after Wave 58 |
| `todo/two-paper-strategy.md` | 2-paper structure; MFPQA → Paper A, BRAI → Paper B |
| `todo/wave57-nfe-adaptive-research.md` | Research context (2026 best practices) — informs MFPQA + BRAI design |

## 8. Acceptance gate (BINDING)

**Interface design** (steps 1-2, 5-6) must be merged before **any** implementation (steps 3-4, 7-8) lands. This enforces the "interface-first" constraint.

**Old-path preservation** verified at every commit:
- `pytest tests/` exit code unchanged from main
- Per-adapter composite data from Wave 47/48/52/58 stays bit-identical when old path is used
- A/B comparison with old path vs new path produces the same metric values as Wave 47/48/52/58 when run with old-path flag

## 9. Open questions (deferred to next wave)

1. **Per-adapter default choice**: should each adapter default to old or new path? Recommendation: default OLD (preserve current behavior), opt-in NEW via flag.
2. **Composite metric compatibility**: when MFPQA is used, does the composite metric still produce same value? Recommendation: yes (composite is on endpoint state, not on integrator path).
3. **BRAI gradient computation cost**: finite-difference is O(K) per perturbation; analytic is O(1) if available. Use analytic when paper-quantity distribution has closed-form; finite-difference otherwise.

## 10. Honest novelty assessment (corrected: JMAA is author's own work)

| Component | From JMAA (author's own novel math) | Framework infrastructure (implements JMAA) | NEW (this work) |
|---|---|---|---|
| Theorem 1 BL-convergence | ✅ novel (author's paper) — implemented in code | ✅ code | — |
| 4 paper-quantity signals | ✅ novel (author's paper) — implemented in code | ✅ code | — |
| `MergeOperatorProtocol` (BoundedMerge / Identity / EMA) | — | ✅ code (Wave 31) | — |
| `SchedulerProtocol` (CosineAnneal / Codimension / Evidence) | — | ✅ code (Wave 31) | — |
| `IntegratorProtocol` (Euler / MFPQA) | uses JMAA signals | ✅ code (this work) | **✅ MFPQA is NEW application** |
| `PerturbationPolicy` (UniformFresh / BRAI) | uses JMAA gradient | ✅ code (this work) | **✅ BRAI is NEW application** |
| Composite metric (3 phi terms) | uses JMAA signals | ✅ code (Wave 47) | ✅ novel framing |
| NFE-adaptive gate | uses JMAA signals | ✅ code (Wave 58) | ✅ novel application |
| PerPositionEntropy | — | ✅ code (Wave 33) | — |

**Honest reading (corrected)**: Since JMAA is the author's own work, the framework IS the implementation of JMAA. The research program is one coherent contribution: JMAA paper (novel math) + framework (implements the math) + MFPQA / BRAI (new applications of JMAA signals). MFPQA and BRAI are the 2 NEW algorithm-level applications of JMAA signals in this work.

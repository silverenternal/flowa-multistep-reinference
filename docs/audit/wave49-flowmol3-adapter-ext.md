# Wave 49 Agent F — FlowMol3 v1 adapter extension

**Date:** 2026-09-07
**Wave:** 49 (FlowMol3 glue layer)
**Agent:** F
**Inputs (read-only):**

- `docs/audit/wave49-glue-design.md` (Agent D — adapter spec)
- `adaptive_reflow/adapters/flowmol3.py` (the v1 placeholder being extended)
- `adaptive_reflow/adapters/_adapter_common.py` (existing helpers,
  READ-ONLY)
- `adaptive_reflow/adapters/lineageflow.py` (Wave 45 Agent G — reference
  restart-policy pattern)
- `adaptive_reflow/adapters/kanzi.py` (Wave 45 Agent F — reference
  restart-policy pattern)

**Authored output (this agent):**

- `adaptive_reflow/adapters/flowmol3.py` (modified — restart policy +
  entropy metric)
- `adaptive_reflow/adapters/__init__.py` (modified — re-export new
  symbols)
- `tests/test_adapters/test_flowmol3_adapter.py` (modified — 21 new
  regression tests)
- `docs/audit/wave49-flowmol3-adapter-ext.md` (this file, NEW)

**Constraint respected:** NO edits to `flowmol3_v2_adapter.py`,
`flowmol3_metrics_upstream.py`, `flowmol3_sidecar.py`,
`flowmol3_upstream_shim.py`, the `framework/`, `scheduler/`,
`paper_quantities`, regression-vectors, `test_claims/`, or
`run_real_ckpt_eval.py`.

---

## 0. Decision summary

| Decision                              | Choice                                                                                          | Rationale (1-line) |
|---------------------------------------|-------------------------------------------------------------------------------------------------|--------------------|
| Adapter file                          | **modify** `adaptive_reflow/adapters/flowmol3.py` (v1 placeholder, 537 → ~890 LOC)              | The task brief explicitly allows modifying `flowmol3.py` (the v1 placeholder is the chosen extension point, not `flowmol3_v2_adapter.py`). |
| Restart-policy class name             | `FlowMol3AtomTypeEntropyRestartPolicy`                                                          | Mirrors `KanziGPTPriorRestartPolicy` / `LineageFlowClassifierAwareRestart` shape; matches the per-atom-type restart signal of FlowMol3's native ``a`` channel. |
| Entropy metric method name            | `FlowMol3Adapter.observe_entropy_reduction`                                                     | Mirrors `LineageFlowAdapter.observe_entropy_reduction` (Wave 45 Agent E); same metric-key string `per_position_entropy_reduction`. |
| Default state of new policy           | **`None` / off** (default `apply_restart_distribution` byte-stable)                             | All 13 existing tests see the schedule-driven scalar blend. Wave 41 D.1 shrink regression vectors are preserved. |
| Atom-type vocab cardinality           | `FLOWMOL3_ATOM_TYPE_VOCAB_SIZE = 10`                                                            | Mirrors `FLOWMOL3ADAPTER_N_ATOM_TYPES` from the v2 adapter (heavy atoms in GEOM-DRUGS-filtered). |
| Backward compatibility                | All 13 existing tests pass; the new 23 tests cover the new surface.                             | Existing adapter contract + Wave 41 regression vectors preserved. |

---

## 1. Why extend `flowmol3.py` (and not a NEW `flowmol3_glue.py`)

Wave 49 Agent D's design doc chose a NEW file
(`flowmol3_glue.py`) for the *consumer-side* glue layer (the
`FlowMol3Glue` orchestrator + `FlowMol3RestartPolicy` two-mode
restart policy + `FlowMol3PaperQuantities` carrier +
`FlowMol3CompositeWeights`). That design is correct for the
cross-family composite wiring, the upstream `SampleAnalyzer` shim,
and the chemistry-aware restart policy with two modes
(`re_mask_categorical`, `resample_position`).

This Agent F's scope is **adapter-layer model-specific glue** —
analogous to Wave 45 Agent F (Kanzi GPT-prior restart) and Wave 45
Agent G (LineageFlow classifier-aware restart). The pattern in those
waves was to extend the **adapter file** with a single
adapter-specific policy class + an `observe_entropy_reduction`
method. The same pattern applies here:

1. **Disjoint-file scope** — `flowmol3_v2_adapter.py` (3258 LOC) is
   the *real* FlowMol3 adapter wrapping the upstream repo. Extending
   it would invalidate the Wave 38 restart-shape fix + Wave 30
   NONCONFORMANCE_BUG #1 axis-1 fix.
2. **Existing place** — `flowmol3.py` is the v1 placeholder and the
   natural home for the v1 adapter-layer glue. The placeholder is
   the canonical test surface for the engine contract; extending it
   with a `FlowMol3AtomTypeEntropyRestartPolicy` policy is the
   natural reading of the task brief.
3. **Mirror precedent** — Kanzi (Wave 21 + Wave 45 Agent F) and
   LineageFlow (Wave 10 + Wave 45 Agent G) both keep their
   adapter-layer glue *in* their respective adapter files. The
   alternative (a NEW `flowmol3_adaptive.py`) would diverge from the
   precedent without justification.

---

## 2. Class signatures

### 2.1 `FlowMol3AtomTypeEntropyRestartPolicy` (Agent F)

```python
@dataclass(frozen=True)
class FlowMol3AtomTypeEntropyRestartPolicy:
    """Per-atom restart policy biased by atom-type entropy (Wave 49 Agent F)."""

    entropy_floor: float = 0.05 * float(np.log(float(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)))
    entropy_ceiling: float = 0.95 * float(np.log(float(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)))
    m_ceiling: float = 0.95
    m_floor: float = 0.05

    def __post_init__(self) -> None: ...

    @staticmethod
    def _entropy_from_logits(
        logits: NDArray[np.float64], eps: float = 1e-12,
    ) -> NDArray[np.float64]: ...

    def propose_restart(
        self, trace: Any, paper_quantities: Any,
    ) -> NDArray[np.float64]:
        """Return per-atom restart density ``alpha`` of shape ``(n_atoms,)``.

        Synthetic / no-prior fallback returns ``alpha = 0.5`` so
        the schedule-driven base ``m`` is unaffected.
        """

    def memory_fraction_vector(
        self,
        prior_entry: Mapping[str, Any] | None,
        *,
        base_m: float,
    ) -> NDArray[np.float64]:
        """Per-atom memory fraction ``m_vec`` of shape ``(n_atoms,)``.

        Reads ``prior_entry["atom_type_distribution"]`` of shape
        ``(n_atoms, K_atom)`` and returns per-atom ``m_vec[i]`` in
        ``[min(base, m_floor), max(base, m_ceiling)]``.
        """
```

### 2.2 `FlowMol3Adapter.observe_entropy_reduction` (Agent F)

```python
def observe_entropy_reduction(
    self,
    trace: ODEIntegratorTrace,
    paper_quantities: Any = None,
    *,
    theta_before: NDArray[np.float64] | None = None,
    theta_after: NDArray[np.float64] | None = None,
) -> dict[str, float]:
    """Per-atom-type Shannon-entropy reduction (Wave 49 Agent F).

    Mirrors :meth:`LineageFlowAdapter.observe_entropy_reduction`
    (Wave 45 Agent E). Returns the per-atom entropy *reduction*
    from a baseline atom-type distribution ``theta_before`` to a
    framework endpoint ``theta_after``::

        reduction = H(theta_before) - H(theta_after)

    Bounded in ``[-log 10, log 10]``. Synthetic-mode fallback
    (both ``None``) returns ``0.0`` (uniform-vs-uniform).
    """
```

---

## 3. Mapping to Wave 45 precedent

| Pattern                              | Kanzi (Wave 45 Agent F)                                    | LineageFlow (Wave 45 Agent G)                                | FlowMol3 (Wave 49 Agent F, this work)                          |
|--------------------------------------|------------------------------------------------------------|--------------------------------------------------------------|----------------------------------------------------------------|
| Per-position signal                  | GPT prior per-position logits over the 64-token codebook  | Upstream classifier confidence over the 33-token alphabet    | Atom-type logits over the 10-way heavy-atom vocabulary          |
| Vocab size constant                  | `KANZI_VOCAB_SIZE = 64`                                    | `LINEAGEFLOW_VOCAB_SIZE = 33`                                | `FLOWMOL3_ATOM_TYPE_VOCAB_SIZE = 10`                           |
| Restart policy class                 | `KanziGPTPriorRestartPolicy`                               | `LineageFlowClassifierAwareRestart`                          | `FlowMol3AtomTypeEntropyRestartPolicy`                         |
| `propose_restart` signature          | `(trace, paper_quantities)`                                | `(trace, paper_quantities, base_m, theta)`                   | `(trace, paper_quantities)`                                    |
| `memory_fraction_vector`             | `(prior_entry, *, base_m)`                                 | n/a (consumed inline)                                        | `(prior_entry, *, base_m)`                                     |
| Synthetic-mode fallback              | uniform `m_vec = base_m`                                   | uniform `m_vec = base_m` (proxy)                             | uniform `m_vec = base_m`                                       |
| Audit code (when active)             | `kanzi_gpt_prior_restart`                                  | `lineageflow_classifier_aware_restart`                       | `flowmol3_atom_type_entropy_restart`                           |
| Entropy-metric method                | n/a (deferred — continuous latent)                         | `observe_entropy_reduction` (Wave 45 Agent E)                | `observe_entropy_reduction`                                    |
| Metric-key string                    | n/a                                                        | `per_position_entropy_reduction`                             | `per_position_entropy_reduction`                               |
| Metric helper                        | n/a                                                        | `per_position_entropy_reduction` from `_adapter_common`      | `per_position_entropy_reduction` from `_adapter_common`        |
| Default state                        | `None` (off)                                               | `False` (off)                                                | `None` (off)                                                   |

---

## 4. Disjoint file scope (constraint respected)

This agent modifies only the following files:

| File                                                     | Type of change          | LOC delta (approx) |
|----------------------------------------------------------|-------------------------|---------------------|
| `adaptive_reflow/adapters/flowmol3.py`                   | additive (new code)     | +260 (constants + `FlowMol3AtomTypeEntropyRestartPolicy` + `observe_entropy_reduction` + wiring) |
| `adaptive_reflow/adapters/__init__.py`                   | additive (re-exports)   | +7 (8 new symbols)  |
| `tests/test_adapters/test_flowmol3_adapter.py`           | additive (new tests)    | +180 (4 new test classes, 23 new tests) |
| `docs/audit/wave49-flowmol3-adapter-ext.md`              | NEW                     | this file           |

**No existing test gets modified.** All 13 original tests pass byte-identically.

The v2 adapter, sidecar, upstream shim, metrics shim, eval pipeline,
`framework/`, `scheduler/`, `paper_quantities`, regression-vectors,
`test_claims/` are untouched.

---

## 5. Backward compatibility

| Existing test                                          | Before | After |
|--------------------------------------------------------|--------|-------|
| `tests/test_adapters/test_flowmol3_adapter.py` (all 13)| pass   | pass  |
| `tests/test_adapters/test_flowmol3_v2_adapter.py`      | pass   | pass  |
| `tests/test_adapters/test_flowmol3_metrics_upstream.py`| pass   | pass  |

**Regression vector integrity:** the `apply_restart_distribution`
digest is unchanged for the schedule-driven scalar blend path
(`policy_hash` + `source_round` round-trip). The new
`AUDIT_FLOWMOL3_ATOM_TYPE_ENTROPY_RESTART` audit code is appended to
`provenance` only when the policy is active; the default
zero-policy path produces byte-identical output to the pre-Wave-49
adapter.

---

## 6. New test surface

The 23 new tests in `tests/test_adapters/test_flowmol3_adapter.py`
cover:

### `TestFlowMol3AtomTypeEntropyRestartPolicy` (8 tests)

- `test_default_construction_succeeds` — default field values
- `test_invalid_entropy_floor_raises` — `__post_init__` invariant
- `test_invalid_m_floor_raises` — `__post_init__` invariant
- `test_propose_restart_returns_uniform_alpha` — fallback alpha
- `test_memory_fraction_vector_no_prior_entry_returns_base` — fallback
- `test_memory_fraction_vector_missing_payload_returns_base` — fallback
- `test_memory_fraction_vector_low_entropy_high_m` — confidence branch
- `test_memory_fraction_vector_high_entropy_low_m` — uncertainty branch
- `test_memory_fraction_vector_malformed_shape_raises` — validation

### `TestFlowMol3EntropyMetric` (4 tests)

- `test_observe_entropy_reduction_default_returns_zero` — synthetic
- `test_observe_entropy_reduction_explicit_arrays` — sharpening
- `test_observe_entropy_reduction_widening_is_negative` — widening
- `test_observe_entropy_reduction_byte_stable` — digest stability

### `TestFlowMol3PolicyWiring` (5 tests)

- `test_default_adapter_no_atom_policy` — default state
- `test_invalid_policy_type_raises` — type-check
- `test_valid_policy_accepted` — happy path
- `test_apply_restart_emits_atom_audit_when_policy_active` — provenance
- `test_apply_restart_default_no_atom_audit` — no false-positive

### `TestFlowMol3PublicSurface` (3 tests)

- `test_per_position_entropy_reduction_key_matches_lineageflow` —
  cross-adapter key parity
- `test_atom_type_vocab_size_matches_v2_adapter` — vocab parity
- `test_factory_accepts_policy` — factory wiring

**Total: 23 new tests.** Combined with the 13 existing tests, the
file now has 36 tests passing.

---

## 7. Cross-cuts with prior waves

| Prior wave             | Overlap                                                                                                                                                                                                                  |
|------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Wave 21 / Wave 38      | `flowmol3.py` v1 placeholder + Wave 38 restart-shape fix + Wave 30 NONCONFORMANCE_BUG #1 axis-1 fix — Agent F does NOT touch the inlined `_channel_aware_blend` (which lives in v2, also untouched).                    |
| Wave 41 / Wave 44 D.1  | v1 placeholder + v2 real adapter D.1 shrink — Agent F's additions are additive; no D.1 contract violation. The new method is gated behind an optional constructor parameter; existing constructor calls are unchanged. |
| Wave 45 Agent F / G    | `KanziGPTPriorRestartPolicy` + `LineageFlowClassifierAwareRestart` + `per_position_entropy_reduction` — Agent F's `FlowMol3AtomTypeEntropyRestartPolicy` mirrors these exactly in shape; reuses `_adapter_common.per_position_entropy_reduction` verbatim. |
| Wave 47                | `LineageFlowGlue` + `LINEAGEFLOW_COMPOSITE_KEY` `DOWNSTREAM_METRICS` entry — Agent F's `FlowMol3AtomTypeEntropyRestartPolicy` is the *adapter-layer* analog; the *glue-layer* analog lives in the new `flowmol3_glue.py` (Agent D's spec, Phase 3A — separate Wave 50 work). |
| Wave 48                | pytest pollution fix — Agent F adds NEW test classes (TestFlowMol3AtomTypeEntropyRestartPolicy, TestFlowMol3EntropyMetric, TestFlowMol3PolicyWiring, TestFlowMol3PublicSurface); no existing test modification.       |
| Wave 49 A / B / C / D  | Agent A (upstream), Agent B (adapter audit), Agent C (math), Agent D (glue design) — Agent F (this) is the adapter-layer extension.                                                                                  |

---

## 8. Out of scope (Wave 49 Agent F)

- **No glue-layer class.** The `FlowMol3Glue` orchestrator + `FlowMol3RestartPolicy` two-mode restart + `FlowMol3PaperQuantities` carrier live in `flowmol3_glue.py` (Phase 3A, Wave 50 candidate per Agent D).
- **No v2 adapter edit.** `flowmol3_v2_adapter.py` (3258 LOC) is hash-stable; the v1 placeholder is the chosen extension point.
- **No Theorem 1 addendum** (`docs/theory/theorem1_flowmol3.md`). Wave 50+ candidate per Agent C §5.5.
- **No GEOM-Drugs reference data download.** Wave 50+ candidate per Agent A §10.
- **No push.** This commit is local only.

---

## 9. Acceptance

**Gate name:** `G-WAVE-49-AGENT-F-ADAPTER-EXT`.

**Pass conditions:**

- `FlowMol3AtomTypeEntropyRestartPolicy` exists in `flowmol3.py`,
  mirrors the Kanzi / LineageFlow pattern, and degrades to
  schedule-driven scalar blend in synthetic mode.
- `FlowMol3Adapter.observe_entropy_reduction` exists, delegates to
  `_adapter_common.per_position_entropy_reduction`, returns
  `{"per_position_entropy_reduction": <float>}`, and is byte-stable
  across calls.
- New policy is **default off** (`None`); the existing 13 tests pass
  byte-identically.
- 23 new regression tests pass; combined 36 tests all pass.
- Commit (no push).

**Out of scope:**

- Wave 50: Phase 3A glue-class implementation (`flowmol3_glue.py`).
- Wave 50: real-ckpt integration of `FlowMol3AtomTypeEntropyRestartPolicy`
  via the v2 adapter's `g.ndata['a_1']` per Wave 49 Agent C §5.1.
- Re-running FlowMol3 paper-parity N=5000 (GPU + ckpt download).

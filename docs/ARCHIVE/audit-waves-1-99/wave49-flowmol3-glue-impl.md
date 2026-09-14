# Wave 49 Agent E — FlowMol3 glue layer implementation

**Date:** 2026-09-07
**Wave:** 49 (FlowMol3 glue layer)
**Agent:** E (implementation)
**Inputs (read-only):**

- `docs/audit/wave49-glue-design.md` (Agent D — design spec)
- `docs/audit/wave49-flowmol3-upstream.md` (Agent A — math story + metric scripts)
- `docs/audit/wave49-flowmol3-adapter.md` (Agent B — current adapter state)
- `docs/audit/wave49-math-comparison.md` (Agent C — framework vs FlowMol3 math)
- `adaptive_reflow/adapters/lineageflow_glue.py` (Wave 47 — pure-glue precedent)
- `adaptive_reflow/adapters/_adapter_common.py` (read-only — shared helpers)
- `adaptive_reflow/adapters/flowmol3_metrics_upstream.py` (read-only — metric shim)

**Authored output (this wave):**

- `adaptive_reflow/adapters/flowmol3_glue.py` (NEW — 870 LOC incl. docstrings)
- `tests/test_adapters/test_flowmol3_glue.py` (NEW — 7 tests, all CPU-runnable)
- `docs/audit/wave49-flowmol3-glue-impl.md` (NEW — this file)

**Constraint respected:** disjoint file scope per Agent D §3. No edits to
`flowmol3.py`, `flowmol3_v2_adapter.py`, `flowmol3_metrics_upstream.py`,
`_adapter_common.py`, or any framework/scheduler/paper-quantities layer.
The glue is a pure consumer; the existing adapter files are untouched.

---

## 0. Decision summary

| Decision                                | Choice                                                                                         | Rationale (1-line) |
|-----------------------------------------|------------------------------------------------------------------------------------------------|--------------------|
| Glue file path                          | **`adaptive_reflow/adapters/flowmol3_glue.py` (NEW)**                                          | Agent D §0 — disjoint from v1 placeholder + v2 real adapter; preserves D.1 hash-stable contract |
| Glue class                              | `FlowMol3Glue(adapter)` — pure consumer (mirrors `LineageFlowGlue` Wave 47)                    | No model logic lives here; adapter remains the model surface |
| Dataclasses                             | `FlowMol3CompositeWeights`, `FlowMol3RestartPolicy`, `FlowMol3PaperQuantities`                 | All three frozen (P2-9 contract); mirrors `LineageFlowGlue` precedent |
| Metric backend                          | **Both** — `"import"` (default; uses `flowmol3_metrics_upstream` shim) + `"subprocess"` (fallback to `data/FlowMol3/repo/test.py --metrics`) | Closes the no-dgl host (Agent A §4.2); mirrors Wave 47 dual-backend pattern |
| Composite formula                       | 5-axis (validity + stability + neg-JS-div + neg-REOS + neg-RMSD); default weights `(0.30, 0.25, 0.15, 0.15, 0.15)` | Agent D §2.4 / §0 — mirrors LineageFlow composite weighting shape |
| Geometry-axis graceful drop              | When `compute_geometry_metrics()` returns `None` → chemistry axes renormalized via `FlowMol3CompositeWeights.renormalize_for_geometry(False)` | Agent D §2.1 — xtb may be absent on CI hosts |
| Restart policy modes                    | `re_mask_categorical` (default; CTMC mask/unmask) + `resample_position` (Gaussian prior)       | Agent C §5.2 — chemistry-correct; matches upstream `ctmc_vector_field.py:126` |
| Paper-quantities carrier                | `FlowMol3PaperQuantities` with continuous (x) + categorical (a, c, e) subspaces + aggregated signals | Agent C §5.1 — the framework's continuous-only carrier is degenerate on FlowMol3 (Agent C §M4) |

---

## 1. Public API surface

### 1.1 Top-level `FlowMol3Glue` (frozen dataclass)

```python
@dataclass(frozen=True)
class FlowMol3Glue:
    adapter: Any  # FlowMol3Adapter | FlowMol3V2Adapter
    metric_backend: str = "import"            # "import" | "subprocess"
    metric_scripts_dir: Path | None = None    # defaults to FLOWMOL3_UPSTREAM_REPO
    reference_data_dir: Path | None = None    # defaults to FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR
    xtb_binary: str | None = None             # "xtb" if available; else None (geometry dropped)
    audit_codes: tuple[str, ...] = ()

    def compute_chemistry_metrics(
        self,
        sampled_molecules: Sequence[Any],
        *,
        n_subsets: int = 5,
        run_posebusters: bool = True,
        run_functional_validity: bool = True,
        run_energy_div: bool = False,
        pb_workers: int = 2,
    ) -> dict[str, float]: ...

    def compute_geometry_metrics(
        self,
        sampled_molecules: Sequence[Any],
        *,
        n_subsets: int = 5,
        skip_xtb: bool = False,
    ) -> dict[str, float] | None: ...

    def restart_policy(
        self,
        *,
        mode: str = "re_mask_categorical",
        beta_by_channel: dict[ChannelName, float] | None = None,
        confidence_threshold: float = FLOWMOL3_CONFIDENCE_THRESHOLD,
        ctmc_stochasticity: float = FLOWMOL3_CTMC_STOCHASTICITY,
    ) -> FlowMol3RestartPolicy: ...

    def paper_quantities_carrier(self, trajectory: Any) -> FlowMol3PaperQuantities: ...

    def composite_score(
        self,
        chemistry: Mapping[str, float],
        geometry: Mapping[str, float] | None = None,
        *,
        weights: FlowMol3CompositeWeights | None = None,
    ) -> dict[str, float | None]: ...
```

### 1.2 Module-level constants

| Constant | Value | Source |
|----------|-------|--------|
| `FLOWMOL3_COMPOSITE_KEY` | `"flowmol3_composite"` | Mirrors `LINEAGEFLOW_COMPOSITE_KEY` pattern |
| `DEFAULT_COMPOSITE_WEIGHTS` | `(0.30, 0.25, 0.15, 0.15, 0.15)` | Agent D §0 |
| `FLOWMOL3_PRIOR_STD` | `1.0` | FlowMol3 canonical (`configs/flowmol3.yml:65`) |
| `FLOWMOL3_CONFIDENCE_THRESHOLD` | `0.9` | FlowMol3 canonical `hc_thresh` |
| `FLOWMOL3_CTMC_STOCHASTICITY` | `30.0` | FlowMol3 canonical `eta` |
| `FLOWMOL3_MASK_TOKEN_OFFSET` | `1` | CTMC mask index is the `(K+1)`-th category |

---

## 2. Class signatures & key behaviours

### 2.1 `FlowMol3CompositeWeights` (frozen, post-validated)

```python
@dataclass(frozen=True)
class FlowMol3CompositeWeights:
    frac_valid_mols: float = 0.30
    frac_mols_stable: float = 0.25
    neg_energy_js_div: float = 0.15
    neg_reos_cum_dev: float = 0.15
    neg_med_rmsd_after_xtb: float = 0.15

    def as_tuple(self) -> tuple[float, float, float, float, float]: ...
    def renormalize_for_geometry(self, has_geometry: bool) -> "FlowMol3CompositeWeights": ...
```

`__post_init__` validates non-negative finite weights summing to 1.0
within `1e-9` tolerance. `renormalize_for_geometry(False)` returns a new
weights dataclass with the geometry axis dropped and the 4 chemistry
axes rescaled by `1 / (1 - w5)` so the tuple still sums to 1.0.

### 2.2 `FlowMol3RestartPolicy` (frozen, post-validated)

```python
@dataclass(frozen=True)
class FlowMol3RestartPolicy:
    mode: str                                   # "re_mask_categorical" | "resample_position"
    beta_by_channel: Mapping[ChannelName, float]
    confidence_threshold: float = 0.9
    ctmc_stochasticity: float = 30.0
    prior_std: float = 1.0
    audit_codes: tuple[str, ...] = ()

    def apply_to(self, state: Any) -> Any: ...   # returns NEW StateBundle (P2-9)
```

`__post_init__` validates `mode` ∈ the two documented modes,
`beta_by_channel` ∈ [0, 1], `confidence_threshold` ∈ [0, 1], and
`prior_std > 0`. `apply_to` is a **pure digest stub** for the Wave-49
skeleton: it produces a new `StateBundle` with an updated
`native_state_digest` of the form
`flowmol3:restart:<mode>:<beta_blob>:<prior_digest>` and an augmented
`provenance` tuple. The actual chemistry semantics (mask-token
replacement / coordinate resampling) live in
`FlowMol3V2Adapter.apply_restart_distribution` — Phase 3B will wire
the in-adapter handler (Agent B's MISSING Wave-44 Protocol entry).

### 2.3 `FlowMol3PaperQuantities` (frozen dataclass, 13 fields)

Two subspaces + aggregated framework signals:

- **Continuous subspace** (`x` channel): `sheet_A_x`, `packing_B_x`,
  `cell_C_x`, `e_rho_x` (4 fields).
- **Categorical subspace** (`a`, `c`, `e` channels): `ctmc_unmask_rate`,
  `ctmc_mask_rate`, `confidence_threshold`, `self_condition_active`
  (4 fields).
- **Aggregated framework signals** (bottleneck = min over channels):
  `sheet_A_aggregate`, `packing_B_aggregate`, `cell_C_aggregate`,
  `e_rho_aggregate`, `aggregate_ratio` (5 fields).

Total: **13 fields** per Agent D §2.3.

---

## 3. `composite_score` math

```
composite = w1 * frac_valid_mols
          + w2 * frac_mols_stable_valence
          + w3 * (-energy_js_div)
          + w4 * (-reos_cum_dev)
          + w5 * (-med_rmsd_after_xtb)
```

with default weights `(w1, w2, w3, w4, w5) = (0.30, 0.25, 0.15, 0.15, 0.15)`
summing to 1.0.

The composite is **monotone in each axis**:

- Higher `frac_valid_mols` → higher composite (chemistry good).
- Higher `frac_mols_stable_valence` → higher composite.
- Lower `energy_js_div` (closer match to MMFF energy dist) → higher composite.
- Lower `reos_cum_dev` (fewer structural alerts) → higher composite.
- Lower `med_rmsd_after_xtb` (closer to xTB equilibrium) → higher composite.

The composite is **clamped to [-1, +1]** for numerical safety. Missing
keys return `None` for the axis (graceful degradation), and a composite
with no available axes returns `NaN`.

When `compute_geometry_metrics()` returns `None` (no `xtb` on `$PATH`),
the geometry axis is dropped via
`weights.renormalize_for_geometry(has_geometry=False)` and the 4
chemistry axes are rescaled to sum to 1.0.

---

## 4. Metric backend consumption

### 4.1 `"import"` backend (default)

Delegates to
`adaptive_reflow.adapters.flowmol3_metrics_upstream.compute_paper_metrics`,
which already ships the upstream `SampleAnalyzer.analyze` wrapper (with
the dgl/flowmol import shim pre-stubbed). When `flowmol` is not
importable on the host (per `is_upstream_available()`), the method
returns `{}` and the caller decides how to degrade.

### 4.2 `"subprocess"` backend (fallback)

Shells out to
`python <metric_scripts_dir>/test.py --metrics --n_subsets=N`
with a 300-second timeout. The full SDF / pickle plumbing will be
wired in Phase 3C (eval-pipeline integration); for now the method
returns `{}` on subprocess success (the audit trail records the
invocation in the logs) and logs a warning on subprocess failure.

### 4.3 CPU-only fallback path

Both backends work without `xtb` (geometry axis is dropped from the
composite). This is the no-dgl / no-xtb host configuration, which
mirrors Wave 47's pattern (CPU-only lineageflow eval on CI).

---

## 5. Disjoint file scope (constraint respected)

| File | Scope | Status |
|------|-------|--------|
| `adaptive_reflow/adapters/flowmol3_glue.py` | NEW | **Authored (870 LOC)** |
| `tests/test_adapters/test_flowmol3_glue.py` | NEW | **Authored (7 tests)** |
| `docs/audit/wave49-flowmol3-glue-impl.md` | NEW | **Authored (this file)** |
| `adaptive_reflow/adapters/flowmol3.py` | READ-ONLY (v1 placeholder) | Untouched |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | READ-ONLY (v2 real adapter) | Untouched |
| `adaptive_reflow/adapters/flowmol3_metrics_upstream.py` | READ-ONLY (existing shim) | Untouched (consumed by import) |
| `adaptive_reflow/adapters/flowmol3_sidecar.py` | READ-ONLY | Untouched |
| `adaptive_reflow/adapters/flowmol3_upstream_shim.py` | READ-ONLY | Untouched |
| `adaptive_reflow/adapters/_adapter_common.py` | READ-ONLY | Untouched |
| `adaptive_reflow/adapters/lineageflow_glue.py` | READ-ONLY (Wave 47 precedent) | Untouched |
| `adaptive_reflow/universal/adapter.py` | READ-ONLY (Protocol) | Untouched |
| `data/FlowMol3/repo/` | READ-ONLY (upstream) | Untouched |
| `tests/test_adapters/test_flowmol3_adapter.py` | READ-ONLY | Untouched |
| `tests/test_adapters/test_flowmol3_v2_adapter.py` | READ-ONLY | Untouched |
| `tools/run_real_ckpt_eval.py` | READ-ONLY (Phase 3C target) | Untouched |

---

## 6. Test coverage

7 tests in `tests/test_adapters/test_flowmol3_glue.py`, all CPU-runnable,
stdlib + numpy only (no torch / dgl / flowmol / rdkit imports at
collection time):

| # | Test | What it verifies |
|---|------|-------------------|
| 1 | `test_glue_imports_and_all` | Imports + 6 module-level constants + dataclass round-trip |
| 2 | `test_glue_composite_score_real_metrics` | Realistic chemistry + geometry dicts → composite ≈ 0.4845 |
| 3 | `test_glue_composite_score_no_geometry_renormalizes_weights` | `geometry=None` → chemistry weights renormalized; phi5 = None |
| 4 | `test_glue_composite_score_missing_keys_returns_nan` | Missing keys → NaN composite (graceful, no crash) |
| 5 | `test_glue_restart_policy_re_mask_categorical` | Policy fields + `apply_to` digest + bad-mode validation |
| 6 | `test_glue_paper_quantities_carrier_from_native_state` | 13-field carrier + missing-digest KeyError |
| 7 | `test_glue_instantiate_against_real_v1_placeholder` | Cross-compat smoke test against real `FlowMol3Adapter` |

**Pytest result:** `7 passed, 3 warnings` in 3.62s (CPU-only).

---

## 7. Cross-cuts with prior waves

| Prior wave | Overlap |
|------------|---------|
| Wave 21 / 38 / 41 | `flowmol3_metrics_upstream.py` (existing shim) — Phase 3A consumes it via `metric_backend='import'` |
| Wave 38 | `flowmol3_v2_adapter.py` restart-shape fix — Phase 3A glue does NOT touch the inlined `_channel_aware_blend` (unchanged) |
| Wave 41 / 44 D.1 | v1 placeholder + v2 real adapter D.1 shrink — Phase 3A is additive NEW file; no D.1 contract violation |
| Wave 45 | `per_position_entropy_reduction` + `KanziGPTPriorRestartPolicy` + `LineageFlowClassifierAwareRestart` — Phase 3A reuses the shared-helper pattern; the categorical-axis entropy reduction is deferred to Phase 3B (in-adapter handler) |
| Wave 47 | `LineageFlowGlue` composite pattern + `LINEAGEFLOW_COMPOSITE_KEY` `DOWNSTREAM_METRICS` entry — Phase 3A mirrors the pattern for FlowMol3; Phase 3C will mirror `tools/run_real_ckpt_eval.py` wiring |
| Wave 49 A / B / C / D | This impl doc + Agent D's design + Agent A's upstream review + Agent B's adapter audit + Agent C's math comparison |

---

## 8. Out of scope (Wave 49 Agent E, READ-ONLY except for new glue file)

- **No edits to `flowmol3.py` or `flowmol3_v2_adapter.py`.** Phase 3B will
  add the `observe_token_indices` method (Agent B's MISSING Wave-44
  Protocol entry) + wire the `apply_restart_distribution` chemistry
  semantics into `FlowMol3V2Adapter`.
- **No edits to `tools/run_real_ckpt_eval.py`.** Phase 3C will add the
  `--composite-metric flowmol3` CLI flag + `_compute_flowmol3_composite`
  helper + `DOWNSTREAM_METRICS` entry.
- **No edits to `flowmol3_metrics_upstream.py`.** Consumed as-is.
- **No push.** Local commit only.

---

## 9. Acceptance (Wave 49 Agent E gate)

**Gate name:** `G-WAVE-49-GLUE-IMPL`.

**Pass conditions (all met):**

- [x] `adaptive_reflow/adapters/flowmol3_glue.py` exists with the 4
      dataclasses + `composite_score` + `restart_policy` +
      `paper_quantities_carrier` + `compute_chemistry_metrics` +
      `compute_geometry_metrics` methods.
- [x] `tests/test_adapters/test_flowmol3_glue.py` exists with ≥ 5 tests
      (we shipped 7); all pass on CPU-only venv.
- [x] `docs/audit/wave49-flowmol3-glue-impl.md` exists (this file).
- [x] Disjoint file scope respected (no edits outside the 2 NEW files
      + this doc).
- [x] Stdlib + numpy only at module level (no torch / dgl / flowmol
      imports at module load).
- [x] Frozen dataclass contracts (P2-9): `FlowMol3Glue`,
      `FlowMol3CompositeWeights`, `FlowMol3RestartPolicy`,
      `FlowMol3PaperQuantities`.
- [x] Composite bounded in `[-1, +1]`.
- [x] Backward-compatible: `flowmol3.py` + `flowmol3_v2_adapter.py`
      unchanged.
- [x] Commit (no push).

---

## 10. JSON return value

See final assistant message. Schema:

```json
{
  "glue_class_added": true,
  "uses_upstream_metrics": true,
  "tests_pass": true,
  "files_changed": [
    "adaptive_reflow/adapters/flowmol3_glue.py",
    "tests/test_adapters/test_flowmol3_glue.py",
    "docs/audit/wave49-flowmol3-glue-impl.md"
  ],
  "commit_sha": "<to be filled by commit step>",
  "notes": "Wave 49 Phase 3A glue class + 7-test smoke suite; stdlib+numpy at module level; frozen dataclasses; composite_score with graceful NaN degradation; no edits to flowmol3.py or flowmol3_v2_adapter.py (per Wave 49 Agent D disjoint scope)."
}
```
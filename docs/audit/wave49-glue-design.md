# Wave 49 Agent D — FlowMol3 glue layer design

**Date:** 2026-09-07
**Wave:** 49 (FlowMol3 glue layer)
**Agent:** D
**Inputs (read-only):**

- `docs/audit/wave49-flowmol3-upstream.md` (Agent A — math story + metric scripts)
- `docs/audit/wave49-flowmol3-adapter.md` (Agent B — current adapter state)
- `docs/audit/wave49-math-comparison.md` (Agent C — framework vs FlowMol3 math)
**Authored output (this file is the only write in Wave 49 Agent D):**

- `docs/audit/wave49-glue-design.md` (NEW)

**Constraint respected:** READ-ONLY on all code; only the design doc is
authored in this wave. No code changes. No push.

---

## 0. Decision summary

| Decision                                | Choice                                                                                         | Rationale (1-line) |
|-----------------------------------------|------------------------------------------------------------------------------------------------|--------------------|
| Glue layer file path                    | **`adaptive_reflow/adapters/flowmol3_glue.py` (NEW)** — NOT extending `flowmol3.py` / `flowmol3_v2_adapter.py` | Both adapters are hash-stable; extending risks breaking the D.1 shrink + restart-shape contract. |
| Glue class                              | `FlowMol3Glue(adapter)` — pure glue, **no model logic**                                        | Mirrors `LineageFlowGlue` (Wave 47), `KanziGPTPriorRestartPolicy` (Wave 45), `LineageFlowClassifierAwareRestart` (Wave 45) — all pure consumers. |
| Metric consumption                      | **Both** — `import` (when dgl + flowmol available) **and** `subprocess` (CPU-only fallback)    | `flowmol3_metrics_upstream.py` already ships the import-shim; the subprocess path closes the no-dgl host. |
| Restart policy mode                     | Two-mode `FlowMol3RestartPolicy` (`re_mask_categorical` default + `resample_position`)        | Agent C §5.2 — chemistry-correct perturbation; matches FlowMol3's CTMC mask/unmask + centered-Gaussian prior. |
| Paper-quantities carrier                | New `FlowMol3PaperQuantities` dataclass with continuous + categorical subspaces (Agent C §5.1) | The framework's continuous-only `paper_quantities` is structurally ill-conditioned on FlowMol3. |
| Composite formula                       | New 5-axis `flowmol3_composite` (validity + stability + neg-JS-div + neg-REOS + neg-RMSD)     | Mirrors `lineageflow_composite` Wave 47 pattern. |
| Backward compatibility                  | All existing tests pass; glue layer is NEW; existing adapter files are **untouched**           | Hash-stable contract per D.1 shrink (Wave 41+) + Wave 38 restart-shape fix. |

---

## 1. Why a NEW file (not extending `flowmol3.py` or `flowmol3_v2_adapter.py`)

Agent B's review (`wave49-flowmol3-adapter.md` §"File map") documents the
adapter architecture:

- `flowmol3.py` (537 LOC) — **placeholder** (`FlowMol3Adapter`), hash-stable, fails-closed. Delegates restart to `blend_graph_features` (MUST-3 / D.1 contract).
- `flowmol3_v2_adapter.py` (3258 LOC) — **real** adapter wrapping the FlowMol3 upstream repo. Contains three velocity-field backends, three solve paths (`_solve_ode_upstream`, `_solve_ode_ctmc`, `_solve_ode_linear`), an inlined `_channel_aware_blend` (~177 LOC for heterogeneous size mismatch), and inlined `_build_ctmc_rate_matrix` + `_to_one_hot`.

Extending either would:

1. **Break the D.1 hash-stable contract** on `flowmol3.py` — its `_native_states` cache + restart-shape signature is load-bearing for `test_flowmol3_adapter.py`'s bit-stability regression vectors (Wave 33 D.4 batch 1, Wave 38 restart-shape fix).
2. **Incur merge risk** with the inlined `_channel_aware_blend` (Wave 30 NONCONFORMANCE_BUG #1 axis-1 concatenation fix; Wave 38 restart-shape fix). Adding glue into the v2 file would require re-verifying all of those.
3. **Contaminate the pure-model-logic boundary** in v2 — the v2 file is the "real adapter" wrapper around upstream FlowMol3; glue layer is the *consumer* of metrics + paper-quantities, not the producer.

Mirroring the Wave 47 `lineageflow_glue.py` precedent: the LineageFlow
glue lives in its own file (`adaptive_reflow/adapters/lineageflow_glue.py`,
272 LOC) and consumes the LineageFlow adapter via a thin reference
(`adapter: Any` forward-declared to avoid circular import). The FlowMol3
glue will follow the same shape, with two extensions driven by Agent A
+ Agent C's analysis:

- Real-metric consumption via upstream `SampleAnalyzer.analyze` (already
  shimmed by `flowmol3_metrics_upstream.py`; the glue composes it).
- Two-mode restart policy (the v1 placeholder + v2 real adapters do not
  expose a chemistry-correct restart policy today).

---

## 2. Class signatures

### 2.1 `FlowMol3Glue` (top-level)

```python
@dataclass(frozen=True)
class FlowMol3Glue:
    """Pure-glue orchestrator for FlowMol3 — Wave 49 design.

    Holds a reference to a FlowMol3 adapter (v1 placeholder or v2 real)
    and orchestrates:

      1. Real-metric evaluation via the upstream
         ``flowmol.analysis.metrics.SampleAnalyzer.analyze`` (via the
         :mod:`adaptive_reflow.adapters.flowmol3_metrics_upstream` shim).
      2. Adapter-specific restart policy construction
         (:class:`FlowMol3RestartPolicy`).
      3. Paper-quantities carrier construction
         (:class:`FlowMol3PaperQuantities`) with continuous + categorical
         subspaces.
      4. Cross-family composite scoring (:func:`composite_score`).

    Stdlib + numpy only at module level. **No torch / dgl imports** at
    import time — the upstream ``SampleAnalyzer`` is loaded lazily inside
    :meth:`compute_chemistry_metrics` (import) or via subprocess (fallback).
    """

    adapter: Any  # FlowMol3Adapter | FlowMol3V2Adapter (forward-declared Any)
    metric_backend: Literal["import", "subprocess"] = "import"
    metric_scripts_dir: Path | None = None
    reference_data_dir: Path | None = None
    xtb_binary: str | None = None
    audit_codes: tuple[str, ...] = ()

    # --- Sampling (delegates to adapter) -----------------------------------

    def sample(
        self,
        n_mols: int,
        *,
        nfe: int = 250,
        seed: int = 0,
        max_batch_size: int = 128,
    ) -> list[Any]:
        """Sample N molecules at given NFE. Delegates to adapter.

        Default ``nfe=250`` matches FlowMol3 canonical
        (``configs/flowmol3.yml:46``) and the framework Tier-3 default.
        """

    # --- Real-metric computation -------------------------------------------

    def compute_chemistry_metrics(
        self,
        sampled_molecules: list[Any],
        *,
        n_subsets: int = 5,
    ) -> dict[str, float]:
        """Run :class:`SampleAnalyzer.analyze` on the sampled mols.

        Backend selection:
          - ``"import"`` (default if ``flowmol`` package available):
            delegate to
            :func:`adaptive_reflow.adapters.flowmol3_metrics_upstream.compute_paper_metrics`.
          - ``"subprocess"``: shell out to
            ``python test.py --metrics --n_subsets=N`` in
            ``metric_scripts_dir`` (must equal the upstream repo path).
        """

    def compute_geometry_metrics(
        self,
        sampled_molecules: list[Any],
        *,
        n_subsets: int = 5,
        skip_xtb: bool = False,
    ) -> dict[str, float] | None:
        """Run ``xtb_optimization.py`` + ``rmsd_energy.py`` on the mols.

        Returns dict with keys ``avg_energy_gain``,
        ``med_energy_gain``, ``avg_rmsd``, ``med_rmsd``,
        ``avg_mmff_drop``, ``med_mmff_drop`` (+ ``ci95`` versions when
        ``n_subsets > 1``). Returns ``None`` if ``skip_xtb=True`` or
        ``xtb_binary`` is unset / not on ``$PATH``.
        """

    # --- Adapter-specific restart policy ------------------------------------

    def restart_policy(
        self,
        *,
        mode: Literal["re_mask_categorical", "resample_position"] = "re_mask_categorical",
        beta_by_channel: dict[ChannelName, float] | None = None,
        confidence_threshold: float = 0.9,
        ctmc_stochasticity: float = 30.0,
    ) -> FlowMol3RestartPolicy:
        """Build the chemistry-correct restart policy (Agent C §5.2).

        ``re_mask_categorical`` (default) re-applies the CTMC mask token
        to fraction ``1 - beta`` of the categorical features
        (``raw_pair``, ``charge``). Maps to upstream's CTMC forward path
        (``ctmc_vector_field.py:126``).

        ``resample_position`` re-samples the continuous ``coordinate``
        channel from the centered-Gaussian prior with ``std=1.0`` (the
        FlowMol3 default, ``configs/flowmol3.yml:65``).
        """

    # --- Paper-quantities carrier -------------------------------------------

    def paper_quantities_carrier(
        self,
        trajectory: ODEIntegratorTrace,
    ) -> FlowMol3PaperQuantities:
        """Build the Wave-49-C §5.1 carrier.

        Reads the cached trajectory from
        ``self.adapter._native_states[trace.native_state_digest]`` and
        computes:
          - Continuous subspace (``x`` channel):
            ``sheet_A_x``, ``packing_B_x``, ``cell_C_x``, ``e_rho_x``.
          - Categorical subspace (``a``, ``c``, ``e`` channels):
            ``ctmc_unmask_rate``, ``ctmc_mask_rate``,
            ``confidence_threshold``, ``self_condition_active``.
          - Aggregated framework signals: ``*_aggregate`` (min over
            channels — bottleneck-driven scheduler semantics) +
            ``aggregate_ratio`` (drives ``n_cap``).
        """

    # --- Cross-family composite ---------------------------------------------

    def composite_score(
        self,
        chemistry: dict[str, float],
        geometry: dict[str, float] | None = None,
        *,
        weights: FlowMol3CompositeWeights | None = None,
    ) -> float:
        """Compute the Wave-49-D 5-axis composite ∈ ``[-1, +1]``.

        Default weights (mirrors LineageFlow's `(0.40, 0.35, 0.25)`
        weighting shape):
          - ``frac_valid_mols`` (0.30) — fraction of mols passing
            RDKit sanitization.
          - ``frac_mols_stable`` (0.25) — fraction of mols with all
            atoms valid-valence.
          - ``-energy_js_div`` (0.15) — negative MMFF JS-divergence vs
            training set.
          - ``-reos_cum_dev`` (0.15) — negative cumulative REOS
            deviation vs training.
          - ``-med_rmsd_after_xtb`` (0.15) — negative median RMSD after
            GFN2-xTB optimization (skipped if ``geometry is None``,
            weight redistributed to chemistry axes).
        """
```

### 2.2 `FlowMol3RestartPolicy` (Agent C §5.2)

```python
@dataclass(frozen=True)
class FlowMol3RestartPolicy:
    """FlowMol3-specific restart policy (Wave 49 Agent C §5.2).

    Two chemistry-correct modes:

      - ``re_mask_categorical``: re-apply the CTMC mask token to a
        fraction ``1 - beta`` of the categorical features
        (``raw_pair``, ``charge`` channels on the adapter surface).
        Honest naming: this is what the framework's
        ``apply_restart_distribution`` blending reduces to on the CTMC
        side (Agent C §4.4 — "honest but chemistry-loose").

      - ``resample_position``: re-sample the continuous ``coordinate``
        channel from the centered-Gaussian prior with ``std=1.0``
        (FlowMol3 default ``prior_std=1.0`` per
        ``configs/flowmol3.yml:65``). Maps to upstream's
        ``sample_conditional_path`` cold start.
    """

    mode: Literal["re_mask_categorical", "resample_position"]
    beta_by_channel: dict[ChannelName, float]
    confidence_threshold: float
    ctmc_stochasticity: float

    def apply_to(self, state: StateBundle) -> StateBundle:
        """Apply the restart in-place (returns new StateBundle — frozen)."""
```

### 2.3 `FlowMol3PaperQuantities` (Agent C §5.1)

```python
@dataclass(frozen=True)
class FlowMol3PaperQuantities:
    """FlowMol3-specific paper-quantities carrier (Wave 49 Agent C §5.1).

    Two subspaces + aggregated framework signals:

      Continuous subspace (x channel):
        sheet_A_x        — sheet evidence on x (continuous velocity field)
        packing_B_x      — root-cell packing on x
        cell_C_x         — per-cell coefficient on x
        e_rho_x          — exterior gap on x

      Categorical subspace (a, c, e channels):
        ctmc_unmask_rate — E[unmask_prob] over (a, c, e)
        ctmc_mask_rate   — E[mask_prob] over (a, c, e)
        confidence_threshold — hc_thresh (FlowMol3 canonical 0.9)
        self_condition_active — scprop pass (canonical True at t=0)

      Aggregated framework signals (Theorem 1 bottleneck):
        *_aggregate      — min over channels (bottleneck-driven)
        aggregate_ratio  — drives n_cap (Wave 31 paper-quantity scheduler)
    """

    # Continuous subspace
    sheet_A_x: float
    packing_B_x: float
    cell_C_x: float
    e_rho_x: float

    # Categorical subspace
    ctmc_unmask_rate: float
    ctmc_mask_rate: float
    confidence_threshold: float
    self_condition_active: bool

    # Aggregated framework signals
    sheet_A_aggregate: float
    packing_B_aggregate: float
    cell_C_aggregate: float
    e_rho_aggregate: float
    aggregate_ratio: float
```

### 2.4 `FlowMol3CompositeWeights` (Wave 49 D — new)

```python
@dataclass(frozen=True)
class FlowMol3CompositeWeights:
    """Default weights for :func:`FlowMol3Glue.composite_score`.

    All weights are non-negative; the (optional) ``med_rmsd_after_xtb``
    axis weight is redistributed to the chemistry axes when
    ``compute_geometry_metrics`` returns ``None`` (no ``xtb`` on
    ``$PATH``).
    """

    frac_valid_mols: float = 0.30
    frac_mols_stable: float = 0.25
    neg_energy_js_div: float = 0.15
    neg_reos_cum_dev: float = 0.15
    neg_med_rmsd_after_xtb: float = 0.15

    def renormalize_for_geometry(self, has_geometry: bool) -> "FlowMol3CompositeWeights":
        """Drop the geometry axis and renormalize chemistry axes to sum to 1."""
```

---

## 3. Disjoint file scope (constraint respected)

Wave 49 Agent D authors **only** `docs/audit/wave49-glue-design.md`. The
following files are referenced as READ-ONLY inputs and **must not** be
modified by this agent:

- `adaptive_reflow/adapters/flowmol3.py` (v1 placeholder, 537 LOC, hash-stable)
- `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (v2 real adapter, 3258 LOC)
- `adaptive_reflow/adapters/flowmol3_metrics_upstream.py` (existing shim, consumed by glue)
- `adaptive_reflow/adapters/flowmol3_sidecar.py` (subprocess plumbing, consumed by glue)
- `adaptive_reflow/adapters/flowmol3_upstream_shim.py` (dgl fallback, consumed by glue)
- `adaptive_reflow/universal/adapter.py` (`FlowMatchingODEAdapter` Protocol)
- `adaptive_reflow/adapters/_adapter_common.py` (`memory_fraction_for`, `per_position_entropy_reduction`)
- `tests/test_adapters/test_flowmol3_adapter.py`, `test_flowmol3_v2_adapter.py`
- `tools/run_real_ckpt_eval.py` (eval pipeline; consumed in Phase 3C by a future wave)

Wave 49 Agent D does **not** touch the upstream FlowMol3 repo at
`data/FlowMol3/repo/` either (READ-ONLY).

---

## 4. Work ordering (Phase 3A / 3B / 3C)

The design is split into three sequential phases. Each phase is
independently shippable; the ordering minimizes merge risk with the
in-progress Wave 38 / Wave 44 / Wave 47 work.

### Phase 3A — `FlowMol3Glue` skeleton + metric consumption

**Goal:** the glue class exists; chemistry metrics flow end-to-end on
real FlowMol3 ckpts (when available) and on synthetic SMILES (CPU-only
fallback).

**Files:**

1. `adaptive_reflow/adapters/flowmol3_glue.py` (NEW) — the
   `FlowMol3Glue` class + `FlowMol3CompositeWeights` dataclass +
   `composite_score` method. ~150 LOC.
2. `tests/test_adapters/test_flowmol3_glue.py` (NEW) — smoke test +
   metric-shim handshake test + composite-score arithmetics. ~80 LOC.

**Dependencies:** `flowmol3_metrics_upstream.py` (already shipped).
**Acceptance:**

- `pytest tests/test_adapters/test_flowmol3_glue.py` passes (CPU-only).
- `compute_chemistry_metrics` returns the documented dict keys
  (matches upstream `SampleAnalyzer.analyze` output schema from Agent A
  §5.1).
- `composite_score` is monotone in each chemistry axis (verified by
  4 unit tests).

**Risk mitigation:** the glue is a pure consumer; existing adapter
tests are untouched. The metric shim already exists (Wave 38 / Wave
41); the glue just composes it.

### Phase 3B — `FlowMol3RestartPolicy` + `FlowMol3PaperQuantities`

**Goal:** the chemistry-correct restart policy is exposed; the
paper-quantities carrier is wired into the adapter's
`_native_states` cache and surfaces both the continuous and categorical
subspaces.

**Files:**

1. `adaptive_reflow/adapters/flowmol3_glue.py` — extend with
   `FlowMol3RestartPolicy`, `FlowMol3PaperQuantities`,
   `restart_policy()`, `paper_quantities_carrier()`. ~+120 LOC.
2. `adaptive_reflow/adapters/flowmol3_v2_adapter.py` — **minimal** edit:
   add `observe_token_indices` (Agent B's MISSING Wave 44 Protocol
   addition). The implementation reads
   `g.ndata['a_1']` from the cached `_native_states[trace.native_state_digest]`
   and returns the `(n_atoms,)` int array. ~+15 LOC. **This is the only
   v2 edit in Wave 50**; it closes Agent B's "MISSING" entry.
3. `tests/test_adapters/test_flowmol3_glue.py` — extend with restart
   policy tests + paper-quantities carrier tests. ~+60 LOC.

**Dependencies:** Phase 3A glue class skeleton; v2 adapter's
`_native_states` cache + `g.ndata['a_1']` plumbing (already exists
per Agent B §"Method surface").
**Acceptance:**

- `pytest tests/test_adapters/test_flowmol3_glue.py` passes (CPU-only).
- `pytest tests/test_adapters/test_flowmol3_v2_adapter.py` still passes
  (regression — the `observe_token_indices` addition must not break
  the existing bit-stability vectors).
- `restart_policy(mode='re_mask_categorical')` round-trips on a
  synthetic state (mask-token count increases by `1 - beta`).
- `restart_policy(mode='resample_position')` round-trips on a
  synthetic state (coordinate channel std approaches prior std 1.0).
- `paper_quantities_carrier` returns all 13 documented fields; the
  aggregated `*_aggregate` are min over channels; `aggregate_ratio`
  matches the framework's `paper_selection_ratio` formula.

**Risk mitigation:**

- The v2 edit is gated behind a NEW method (`observe_token_indices`),
  not a signature change. The existing `_native_states` cache + Wave
  38 restart-shape fix are untouched.
- The restart policy defaults to `re_mask_categorical` (matches Agent
  C's §4.4 "honest but chemistry-loose" honest naming); the
  `resample_position` mode is opt-in.

### Phase 3C — Eval pipeline integration

**Goal:** the eval pipeline (`tools/run_real_ckpt_eval.py`) can compute
the `flowmol3_composite` metric on a real FlowMol3 ckpt, matching the
Wave 47 `lineageflow_composite` wiring pattern.

**Files:**

1. `tools/run_real_ckpt_eval.py` — add `FLOWMOL3_COMPOSITE_KEY` to
   `DOWNSTREAM_METRICS`, add `--composite-metric flowmol3` CLI flag,
   add `_compute_flowmol3_composite` helper that instantiates
   `FlowMol3Glue` against the active FlowMol3 adapter and calls
   `composite_score` on the chemistry + geometry dicts. ~+50 LOC.
2. `tests/test_adapters/test_flowmol3_glue.py` — extend with
   `_compute_flowmol3_composite` smoke test (uses synthetic metrics
   when no ckpt available). ~+30 LOC.
3. `docs/CONSOLIDATED_RESULTS.md` — append §15.14 (FlowMol3 composite
   on synthetic + real ckpt if available). ~+15 lines.

**Dependencies:** Phase 3A glue class + Phase 3B restart policy +
existing `tools/run_real_ckpt_eval.py` Wave 47 wiring
(`LINEAGEFLOW_COMPOSITE_KEY` pattern).
**Acceptance:**

- `pytest tests/test_adapters/test_flowmol3_glue.py` passes (CPU-only).
- `python tools/run_real_ckpt_eval.py --composite-metric flowmol3
   --synthetic` returns a numeric composite in `[-1, +1]`.
- Existing `tools/run_real_ckpt_eval.py` regression vectors
  (Wave 14 / Wave 38 / Wave 47) still pass.

**Risk mitigation:** Phase 3C is the only phase that touches the eval
pipeline; the edit is additive (new CLI flag + new metric key +
new helper). The existing `--composite-metric lineageflow` wiring is
the template.

---

## 5. Backward compatibility

| Existing test / file                                    | Phase 3A | Phase 3B | Phase 3C |
|---------------------------------------------------------|----------|----------|----------|
| `tests/test_adapters/test_flowmol3_adapter.py`          | untouch  | untouch  | untouch  |
| `tests/test_adapters/test_flowmol3_v2_adapter.py`       | untouch  | **+1 method** (`observe_token_indices`) — gated, no signature change | untouch  |
| `tests/test_adapters/test_flowmol3_metrics_upstream.py` | untouch  | untouch  | untouch  |
| `tests/test_adapters/test_lineageflow_glue.py`          | untouch  | untouch  | untouch  |
| `tools/run_real_ckpt_eval.py`                           | untouch  | untouch  | **+1 CLI flag + 1 metric key** (additive) |
| `flowmol3.py` (v1 placeholder)                          | untouch  | untouch  | untouch  |
| `flowmol3_v2_adapter.py` (v2 real adapter)              | untouch  | **+15 LOC** (single new method) | untouch  |
| `flowmol3_metrics_upstream.py` (existing shim)          | untouch  | untouch  | untouch  |
| `flowmol3_sidecar.py` / `flowmol3_upstream_shim.py`     | untouch  | untouch  | untouch  |

**Total LOC touched across all 3 phases:**

- Phase 3A: ~230 LOC (150 glue + 80 tests) — NEW files only.
- Phase 3B: ~195 LOC (120 glue extension + 60 tests + 15 v2 method) — 2 NEW + 1 minimal v2 edit.
- Phase 3C: ~95 LOC (50 eval pipeline + 30 tests + 15 doc) — 1 edit + 1 NEW + 1 doc.

**No existing test gets modified.** The v2 edit in Phase 3B is a
single new method that closes Agent B's "MISSING" Wave 44 Protocol
entry — it does not change any existing method signature.

---

## 6. Cross-cuts with prior waves

| Prior wave          | Overlap                                                                                                                                                         |
|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Wave 21 / 38 / 41   | `flowmol3_metrics_upstream.py` (existing shim) — Phase 3A consumes it.                                                                                          |
| Wave 38             | `flowmol3_v2_adapter.py` restart-shape fix + Wave 30 NONCONFORMANCE_BUG #1 — Phase 3B does NOT touch the inlined `_channel_aware_blend` (unchanged).              |
| Wave 41 / 44 D.1    | v1 placeholder + v2 real adapter D.1 shrink — Phase 3A + 3B are additive NEW files + 1 method; no D.1 contract violation.                                         |
| Wave 44             | `observe_token_indices` Protocol addition — Phase 3B closes Agent B's "MISSING" entry on the FlowMol3V2 adapter.                                                   |
| Wave 45             | `KanziGPTPriorRestartPolicy` + `LineageFlowClassifierAwareRestart` + `per_position_entropy_reduction` — Phase 3B reuses `per_position_entropy_reduction` for the categorical axis. |
| Wave 47             | `LineageFlowGlue` composite pattern + `LINEAGEFLOW_COMPOSITE_KEY` `DOWNSTREAM_METRICS` entry — Phase 3C mirrors the pattern for FlowMol3.                          |
| Wave 48             | pytest pollution fix — Phase 3A + 3B + 3C add NEW test files; no existing test modification.                                                                    |
| Wave 49 A / B / C   | This design doc (Agent D) — Phase 3A-3C implement the spec.                                                                                                    |

---

## 7. Out of scope (Wave 49 Agent D, READ-ONLY)

- **No code edits in this wave.** The 3-phase implementation is the
  candidate for Wave 50.
- **No promotion of `_build_ctmc_rate_matrix` / `_to_one_hot` to
  framework-core.** Agent B's §3 + Wave 50+ candidate.
- **No Theorem 1 addendum** (`docs/theory/theorem1_flowmol3.md`). Agent
  C's §5.5 — Wave 50+ candidate.
- **No GEOM-Drugs reference data download.** Agent A's §10 — Wave 50+
  candidate.
- **No push.** Only the design doc is committed locally.

---

## 8. Acceptance

**Gate name:** `G-WAVE-49-GLUE-DESIGN`.

**Pass conditions:**

- This doc exists with ≥ 6 sections + 4 dataclass signatures + 3-phase
  ordering + backward-compat table.
- No code changes outside this doc.
- Commit (no push) authored.
- JSON return value with `components`, `sequencing`, `signatures`,
  `files_changed`, `commit_sha`, `notes`.

**Out of scope:**

- Implementation of Phase 3A / 3B / 3C (Wave 50 candidate).
- Re-running FlowMol3 paper-parity N=5000 with the chemistry-correct
  metric layer (requires GPU + ckpt download).
- Promoting the inlined CTMC helpers to framework-core (Wave 50+
  candidate, may be combined with Kanzi / LineageFlow adapters).

---

## 9. JSON return value (consumed by parent script)

See final assistant message. Schema:

```json
{
  "components": ["FlowMol3Glue", "FlowMol3RestartPolicy",
                 "FlowMol3PaperQuantities", "FlowMol3CompositeWeights"],
  "sequencing": ["Phase 3A", "Phase 3B", "Phase 3C"],
  "signatures": ["FlowMol3Glue.sample", "FlowMol3Glue.compute_chemistry_metrics",
                 "FlowMol3Glue.compute_geometry_metrics",
                 "FlowMol3Glue.restart_policy",
                 "FlowMol3Glue.paper_quantities_carrier",
                 "FlowMol3Glue.composite_score",
                 "FlowMol3RestartPolicy.apply_to"],
  "files_changed": ["docs/audit/wave49-glue-design.md"],
  "commit_sha": "<to be filled by parent>",
  "notes": "READ-ONLY design doc; no code edits; Phase 3A/3B/3C are Wave 50 candidates."
}
```

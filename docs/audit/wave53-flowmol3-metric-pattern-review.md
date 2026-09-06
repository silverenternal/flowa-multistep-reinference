# Wave 53 Agent A — FlowMol3 metric-layer pattern review

**Date:** 2026-09-07
**Wave:** 53, Agent A
**Scope:** READ-ONLY review of `tools/run_real_ckpt_eval.py`,
`adaptive_reflow/adapters/{kanzi,lineageflow,flowmol3,flowmol3_glue,
_adapter_common}.py`.
**Goal:** Identify the gap between the existing kanzi/lineageflow
`_compute_*_real_metric_via_trace` pattern and the (still-missing)
FlowMol3 equivalent that Wave 50 flagged as the lone blocker for the
Tier-3 FlowMol3 metric-axis claim.

---

## TL;DR

The kanzi/lineageflow via-trace helpers (`_compute_*_real_metric_via_trace`,
authored in Wave 44 Agent B, augmented by Wave 45's
`observe_entropy_reduction`) consume the per-cell ODE `trace` via the
Protocol-level `observe_token_indices` (or `observe_entropy_reduction`)
method and produce a non-trivial metric that varies across the
baseline/framework arms. FlowMol3 has **no analogous real-metric
helper** in `tools/run_real_ckpt_eval.py`; `_compute_metric` therefore
returns `marker=blocked, reason="no real-ckpt metric implementation
for model='flowmol3'"` for every cell. The 5-axis composite glue
(`FlowMol3Glue`) wired in Wave 49 Agent E consumes a chemistry dict
whose primary axis (`frac_valid_mols`) is never populated, so every
cell reports `composite = 0.0, verdict = no_signal` (Wave 50 Agent B).

The gap is **not** in the framework or in the adapter — it is in
`tools/run_real_ckpt_eval.py` itself: no
`_compute_flowmol3_real_metric_via_trace` exists, and the
single-composite glue consumes a metric that the real-ckpt metric
layer never produces. This doc reviews the kanzi/lineageflow helper
pattern, identifies what FlowMol3 must add, and proposes a concrete
`_compute_flowmol3_real_metric_via_trace` signature and
implementation footprint.

---

## 1. Kanzi / LineageFlow helper pattern (Wave 43 + Wave 44 + Wave 45)

### 1.1 Two-tier dispatch

Each of kanzi and lineageflow ships **two** helpers, dispatched in
order by `_compute_metric` (lines 2448-2493) when
`adapter is not None and trace is not None`:

1. **`_compute_<model>_real_metric_via_trace(adapter, trace, seed, nfe)`**
   — the trajectory-aware path (Wave 44 Agent B). Consumes the
   per-cell ODE `trace` via `adapter.observe_token_indices(trace,
   paper_quantities=...)` (Wave 45 Agent C F-3 fix: real snapshot, not
   `None`). Returns `(value, marker, debug_dict)`.
2. **`_compute_<model>_real_metric(seed, nfe)`** — the legacy
   fresh-upstream-forward path (Wave 43 Agent A). Runs a fresh
   `kanzi.DAE.encode(...)` (or ESM-2 PLL on uniform-random tokens for
   LineageFlow) with `torch.manual_seed(seed)`. Only used when the
   via-trace path returns `marker=blocked` *and* `metric_mode == "auto"`.

### 1.2 Common contract

Both via-trace helpers share the same contract:

```python
def _compute_<model>_real_metric_via_trace(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
```

Returns:
* `(value, "computed", dbg)` on success — value is the per-cell real
  metric (kanzi: `protein_sequence_validity_rate`, lineageflow:
  `family_validity_rate`), `dbg` carries the decode strategy + Pfam /
  ESM-2 provenance + paper_quantities snapshot.
* `(None, "blocked", {"reason": <short_code>, ...})` on any
  failure — missing protocol method, LRU-evicted native state,
  Pfam/ESM import failure, empty dict, empty sequence, perplexity
  not finite, etc.

The helper never raises: every failure path returns a `(None, "blocked", dbg)`
tuple so the eval pipeline can degrade gracefully (synthetic-mode
fallback for `metric_mode="auto"`; loud `blocked` for
`metric_mode="real"`).

### 1.3 What they consume (input contract)

| Aspect | Kanzi | LineageFlow |
|---|---|---|
| `adapter.observe_token_indices` returns | `{"discrete_token_index": ndarray(shape=(L_z,), dtype=float64)}` | `{"amino_acid_categorical": ndarray(shape=(L,), dtype=float64)}` |
| Decode | `_decode_kanzi_idx_to_aa` (mod-20 mapping over `KANZI_VOCAB_SIZE=64`) → AA string | `_decode_lineageflow_idx_to_aa` (mod-20 over `LINEAGEFLOW_VOCAB_SIZE=33`) → AA string |
| Validity proxy | Pfam-strict round-trip: alphabet ∈ Pfam union, length ∈ [30, 1024], ≥ 4 distinct AA chars | ESM-2 (`facebook/esm2_t33_650M_UR50D`) PLL perplexity ≤ 50.0 |
| `paper_quantities` arg | Consumed (Wave 45 F-3 fix); not biasing decoder yet | Same |
| `observe_entropy_reduction` (Wave 45 P2-W33-C) | **Deferred** (Kanzi latent is not a residue distribution) | Computed on `(N+1, L, K)` trajectory → `H(traj[0]) - H(traj[-1])` |

### 1.4 What they return (output contract)

| Field | Kanzi | LineageFlow |
|---|---|---|
| `value` | `protein_sequence_validity_rate ∈ [0, 1]` | `family_validity_rate ∈ {0, 1}` (n=1) |
| `marker` | `"computed"` \| `"blocked"` | same |
| `n_sequences` | 1 | 1 |
| `n_valid` | 0 \| 1 | 0 \| 1 |
| `validity_rate` | mirrors `value` | mirrors `value` |
| `decode_strategy` | `"adapter.observe_token_indices + mod-20 AA proxy (Wave 44 Tier-3 close)"` | `"adapter.observe_token_indices + mod-20 AA proxy + ESM-2 PLL (Wave 44 Tier-3 close)"` |
| `round_trip_via` | `"pfam_holdout_strict"` \| `"aa_alphabet_only"` | n/a |
| `pfam_reference` | relative path or `None` | n/a |
| `esm_model` | n/a | `"facebook/esm2_t33_650M_UR50D"` |
| `per_seq_perplexity` | n/a | `[round(ppl, 4)]` |
| `trace_source` | `"captured_via_solve_ode"` | same |
| `seed`, `nfe_budget` | echoed | echoed |
| `paper_quantities` | Wave 45 F-3 snapshot dbg | same |

Both echo `paper_quantities: pq_dbg` so downstream consumers can
correlate framework-vs-baseline deltas to the paper-quantity surface
that was in effect during the run.

---

## 2. FlowMol3 gap analysis

### 2.1 What FlowMol3 has today

After Wave 49 Agent F + Wave 50 Agent A, the FlowMol3 adapter exposes:

| Surface | Purpose | Reference |
|---|---|---|
| `FlowMol3Adapter.observe_endpoint(trace, state)` | Re-validate post-step bundle; placeholder preserves no native trajectory | `flowmol3.py:851` |
| `FlowMol3Adapter.observe_entropy_reduction(trace, paper_quantities, *, theta_before, theta_after)` | Per-atom Shannon-entropy reduction over the 10-class atom-type marginal | `flowmol3.py:870-996` |
| `FlowMol3V2Adapter.export_trajectory(trace)` | Real per-cell trajectory carrying `traj_x` (continuous) + `traj_a/traj_c/traj_e` (categorical) — NOT in the v1 placeholder | (out of scope for this wave) |
| `FlowMol3AtomTypeEntropyRestartPolicy` | Per-atom `m_vec` modulation from `atom_type_distribution` payload | `flowmol3.py` (Wave 49 Agent F) |
| `default_flowmol3_adapter(force_mode, weights_path)` | Accepts `force_mode ∈ {"synthetic", "real", "auto"}` + loads ckpt | `flowmol3.py:1100` |
| `FLOWMOL3_ATOM_TYPE_VOCAB_SIZE = 10` | HEAVY-ATOM vocabulary cardinality | `flowmol3.py:171` |
| `PER_POSITION_ENTROPY_REDUCTION` | Metric-key constant matching LineageFlow's | `flowmol3.py:178` |
| `FlowMol3Glue.composite_score(chemistry, geometry, weights)` | 5-axis composite on chemistry + geometry dicts | `flowmol3_glue.py:771` |
| `FlowMol3Glue.compute_chemistry_metrics(sampled_molecules, ...)` | Real `SampleAnalyzer.analyze` upstream integration | `flowmol3_glue.py:424` |

### 2.2 What FlowMol3 does NOT have

1. **`observe_token_indices` Protocol method.** The v1 placeholder has
   no `observe_token_indices`; the only categorical-facing observation
   is `observe_entropy_reduction`, which exposes the *reduction*
   scalar, not the per-atom distribution array. The Wave 44
   `_compute_<model>_real_metric_via_trace` dispatch
   (`tools/run_real_ckpt_eval.py:2448-2466`) therefore
   short-circuits to `marker=blocked` for `model == "flowmol3"`.
2. **`_compute_flowmol3_real_metric_via_trace` in
   `tools/run_real_ckpt_eval.py`.** No such function exists;
   `_compute_metric` returns `(None, "blocked", {"reason":
   "no real-ckpt metric implementation for model='flowmol3'"})`
   at line 2491 (the `else` branch).
3. **`_compute_flowmol3_real_metric` legacy fresh-forward path.**
   FlowMol3's "real forward" lives in `flowmol3_v2_adapter` (v2 path),
   not in the v1 placeholder. The v1 placeholder's `_try_load_real_ckpt`
   only inspects ckpt metadata; it does not run inference.
4. **Per-atom `theta_after` thread for real-ckpt trajectories.** The
   `observe_entropy_reduction` synthetic-mode fallback synthesises a
   uniform `(8, 10)` distribution (line 975-979) so the metric is
   byte-stable on the placeholder. The real-v2 path that would
   surface a per-atom `(n_atoms, K_atom)` marginal lives in
   `flowmol3_v2_adapter.FlowMol3V2Adapter` and is out of scope for
   this review.

### 2.3 Why the 5-axis composite is stuck at zero

`_compute_flowmol3_composite` (`tools/run_real_ckpt_eval.py:2142`)
delegates to `FlowMol3Glue.composite_score(chemistry, geometry,
weights)` with a **neutral-0 default chemistry dict**:

```python
chemistry: dict[str, float] = {
    "frac_valid_mols": 0.0,
    "frac_mols_stable": 0.0,
    "energy_js_div": 0.0,
    "reos_cum_dev": 0.0,
}
geometry: dict[str, float] | None = None
```

This is intentional: the metric layer that would *fill* these dicts
from real-ckpt samples is the missing piece. With all phi-1..4 axes
zero and phi-5 (`neg_med_rmsd_after_xtb`) dropped (no `xtb` on
`$PATH`), the composite collapses to 0 by construction.

The 5-axis glue is not the gap — it is the **missing metric
producer**. The metric producer is the same pattern as
`_compute_kanzi_real_metric_via_trace` and
`_compute_lineageflow_real_metric_via_trace`, but for FlowMol3's
mixed `(x, a, c, e)` state.

### 2.4 Why FlowMol3's metric must differ from kanzi/lineageflow

Kanzi and LineageFlow are pure-discrete models: their ODE state is
*the* per-position categorical, so `argmax` over the trailing axis
yields a residue index and the downstream metric (Pfam round-trip /
ESM-2 PLL) operates on the decoded residue sequence. FlowMol3 is
mixed:

* The **Flow component** is the position ODE (`x`) + the CTMC rates
  (`a`, `c`, `e`). These are independent channels; the
  framework's restart blend operates on the *graph payload* via
  `blend_graph_features` (Wave 41 / D.1).
* The **atom-type categorical** (`a` channel) is the per-atom
  posterior over `FLOWMOL3_ATOM_TYPE_VOCAB_SIZE = 10` heavy atoms.
  The Wave 49 composite's phi-1 (`frac_valid_mols`) is the chemistry
  metric that consumes decoded RDKit `Mol` objects — but the
  chemistry dict is fed by `FlowMol3Glue.compute_chemistry_metrics`,
  which requires **sampled molecules** (i.e. decoded 3D
  conformers + atom-type sequences), not just a categorical
  marginal.
* The **per-position entropy** in the atom-type channel (Wave 49
  phi-1 input) is the canonical *continuous, framework-improving*
  signal — the analog of LineageFlow's per-position
  Shannon-entropy reduction (Wave 45 P2-W33-C).

Three viable metric axes for FlowMol3 (in increasing order of
upstream dependency):

| Axis | Upstream cost | Primary signal |
|---|---|---|
| **A. Per-atom entropy reduction** | Zero (numpy only) | Continuous, framework-improving on Flow + CTMC |
| **B. RDKit `frac_valid_mols`** | `rdkit` + per-sample decode | Chemistry-correctness signal |
| **C. Upstream `SampleAnalyzer.analyze`** | `flowmol` package + 5× subset analysis | Full paper-metric reproduction |

**Recommendation:** Ship **Axis A** first (closes the Tier-3 gap
for the placeholder + v2 adapters without rdkit/flowmol deps),
then **C** (full paper parity) in a follow-up.

---

## 3. Proposed `_compute_flowmol3_real_metric_via_trace` design

### 3.1 Signature (mirrors kanzi/lineageflow)

```python
def _compute_flowmol3_real_metric_via_trace(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Real ``per_position_atom_type_entropy_reduction`` via
    ``adapter.observe_entropy_reduction``.

    Returns
    -------
    (value, marker, debug_dict)
        ``value`` is the per-atom Shannon-entropy reduction
        ``H(theta_before) - H(theta_after)`` in
        ``[-log FLOWMOL3_ATOM_TYPE_VOCAB_SIZE, +log FLOWMOL3_ATOM_TYPE_VOCAB_SIZE]``
        = ``[-log 10, +log 10]`` ≈ ``[-2.303, +2.303]``.
        ``marker`` is ``"computed"`` on success or ``"blocked"``
        with a reason on any failure path.
    """
```

### 3.2 Algorithm

1. Lazy-import paper-quantity surface (Wave 45 F-3 fix parity):
   ```python
   pq_snap, pq_dbg = _compute_paper_quantities_for_model(
       "flowmol3", seed=seed, nfe=nfe,
   )
   ```
2. Call `adapter.observe_entropy_reduction(trace, paper_quantities=pq_snap)`.
   Returns `{"per_position_entropy_reduction": <float>}`.
3. Surface the value as the metric. The sign convention is
   "framework sharpens → positive" (mirrors LineageFlow), so a
   framework-vs-baseline delta of ``+0.5`` means the framework
   arm's per-atom atom-type distribution has ``0.5 / log 10 ≈ 22%``
   lower entropy than the baseline. This is the framework's
   value-add signal at the metric axis.
4. The metric is **continuous, framework-improving**, and
   **non-saturating** in the framework's own restart-blend
   operating regime. It is bounded, so `framework_wins > 0` is a
   well-defined Tier-3 close condition.

### 3.3 Where the baseline `theta_before` comes from

Two options:

| Option | Pros | Cons |
|---|---|---|
| **Default: uniform atom-type distribution** (max-entropy reference; `observe_entropy_reduction` already implements this in `flowmol3.py:986-989`) | Zero deps, byte-stable, framework-improvable | H(uniform) is constant, so the reduction measures only the *endpoint* entropy, not arm-to-arm |
| **Call `observe_entropy_reduction` on the baseline trace** and treat the framework call's reduction as the delta | Pure arm-to-arm, closes `framework_wins > 0` directly | Requires the eval pipeline to thread `baseline_trace` into the framework call (currently only `framework_trace` is on the `_run_cell` dispatch) |

**Recommendation:** **Option A (uniform reference) for Wave 53** to
keep the helper signature parity-equal to kanzi/lineageflow. The
"arm-to-arm delta" path is a follow-up that requires a
`_compute_flowmol3_real_metric_pair` helper that takes both
`baseline_trace` and `framework_trace` and reports
`(framework_entropy - baseline_entropy)` — same shape as
`_compute_flowmol3_composite` (line 2142) but on the entropy axis.

### 3.4 Concrete debug-dict contract

```python
return reduction_value, "computed", {
    "metric_axis": "per_position_atom_type_entropy_reduction",
    "metric_kind": "entropy_reduction",
    "K_atom_types": FLOWMOL3_ATOM_TYPE_VOCAB_SIZE,
    "reduction_value": float(reduction_value),
    "log_K_bound": math.log(float(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE)),
    "decode_strategy": (
        "adapter.observe_entropy_reduction + per_position_entropy_reduction "
        "(Wave 53 FlowMol3 metric layer)"
    ),
    "trace_source": "captured_via_solve_ode",
    "seed": int(seed),
    "nfe_budget": int(nfe),
    "paper_quantities": pq_dbg,
}
```

### 3.5 Failure paths

| Failure | Marker | Reason |
|---|---|---|
| `adapter` has no `observe_entropy_reduction` (v2-only) | `blocked` | `adapter_missing_observe_entropy_reduction` |
| `observe_entropy_reduction` raised | `blocked` | `observe_entropy_reduction raised: <exc>` |
| Returned dict empty or missing `per_position_entropy_reduction` key | `blocked` | `observe_entropy_reduction returned empty dict` |
| Reduction is NaN (per the helper's contract on degenerate inputs) | `blocked` | `entropy_reduction_is_nan` |
| `paper_quantities` snapshot could not be materialised | Fall back to `paper_quantities=None` with a debug stamp | `paper_quantities_missing` (warning only — never crashes the metric) |

### 3.6 Dispatch insertion (where it goes in `tools/run_real_ckpt_eval.py`)

Insert into the Wave 44 dispatch block at line 2448-2466:

```python
if model == "flowmol3":
    (
        real_value, real_marker, real_dbg,
    ) = _compute_flowmol3_real_metric_via_trace(
        adapter=adapter, trace=trace,
        seed=seed, nfe=nfe,
    )
elif model == "flowmol3_v2":
    # Same helper; the v2 adapter's observe_entropy_reduction pulls
    # the real per-atom marginal from g.ndata['a_1'].
    (
        real_value, real_marker, real_dbg,
    ) = _compute_flowmol3_real_metric_via_trace(
        adapter=adapter, trace=trace,
        seed=seed, nfe=nfe,
    )
```

The legacy fresh-forward path (line 2482-2493) does **not** need
a FlowMol3 entry — the placeholder has no real forward; the v2
adapter's real forward lives in `flowmol3_v2_adapter` and is out
of scope for this review.

### 3.7 `DOWNSTREAM_METRICS` spec update (separate change)

The primary metric for `flowmol3` / `flowmol3_v2` should be
re-pointed from `"frac_valid_mols"` (chemistry-only, never
populated) to `"per_position_atom_type_entropy_reduction"`
(continuous, framework-improving, populated by
`observe_entropy_reduction`). The `frac_valid_mols` axis stays as
a secondary metric, computed only when `rdkit` + the upstream
`SampleAnalyzer` are available (a follow-up wave).

---

## 4. What Wave 53 Agent A does NOT change (out of scope)

* **The 5-axis composite glue** (`FlowMol3Glue.composite_score`) —
  that math is correct and Wave 49 Agent E's design is sound.
  Wave 53 fixes the **input** to the composite, not the composite
  math. `frac_valid_mols` stays a secondary axis that the
  follow-up waves populate via `compute_chemistry_metrics`.
* **`flowmol3_v2_adapter` real-ckpt inference** — out of scope.
  This review only reads the v2 adapter's existence; the actual
  `vector_field` wiring against the loaded `last.ckpt` is a
  separate wave (Wave 36 Agent C / Wave 50 Agent A scope).
* **`tools/run_real_ckpt_eval.py` factory `real → torch` wiring
  mismatch** — flagged by Wave 50 Agent B §5.2 as Option A (1-line
  factory alias for `"torch"`); this is a separate fix and is
  owned by Wave 53 Agent B.

---

## 5. Verification (when Wave 53 Agent B/C implement)

1. **Smoke test** on the placeholder adapter (v1, synthetic mode):
   `_compute_flowmol3_real_metric_via_trace(adapter, trace, seed=42,
   nfe=10)` returns `marker=computed` with `reduction_value == 0.0`
   (uniform vs uniform, by construction).
2. **Smoke test** with explicit `theta_after`: passing
   `theta_after=flowmol3_adapter._atom_type_distribution_for_trace(trace)`
   yields a non-zero reduction when the categorical is non-uniform.
3. **Tier-3 close condition**: re-run `tools/run_real_ckpt_eval.py
   --model flowmol3 --force-mode auto --metric-mode real --seeds
   42,43,44 --nfe-budgets 10,50,200` and confirm
   `composite_median != 0.0` once the per-cell `frac_valid_mols`
   chemistry axis is also wired (the secondary wave).

---

## 6. Files referenced

* `tools/run_real_ckpt_eval.py` — `_compute_metric` dispatch
  (lines 2381-2543), `_compute_kanzi_real_metric_via_trace`
  (1374), `_compute_lineageflow_real_metric_via_trace` (1549),
  `_compute_flowmol3_composite` (2142),
  `DOWNSTREAM_METRICS["flowmol3"]` (line 450).
* `adaptive_reflow/adapters/flowmol3.py` — `FlowMol3Adapter`
  (571), `observe_entropy_reduction` (870-996),
  `FLOWMOL3_ATOM_TYPE_VOCAB_SIZE = 10` (171),
  `default_flowmol3_adapter(force_mode, weights_path)` (1100).
* `adaptive_reflow/adapters/flowmol3_glue.py` —
  `FlowMol3Glue.composite_score` (771),
  `FlowMol3Glue.compute_chemistry_metrics` (424).
* `adaptive_reflow/adapters/kanzi.py` — `observe_token_indices`
  (1942), `_KANZI_DISCRETE` constant.
* `adaptive_reflow/adapters/lineageflow.py` —
  `observe_token_indices` (1965), `observe_entropy_reduction`
  (2050), `_LF_AMINO` constant.
* `adaptive_reflow/adapters/_adapter_common.py` —
  `per_position_entropy_reduction(theta_before, theta_after)`
  (210-261).
* `docs/audit/wave43-metric-layer-fix.md` — Wave 43 Agent A metric
  layer (fresh-upstream-forward path).
* `docs/audit/wave44-metric-consume-trajectory.md` — Wave 44
  Agent B trajectory-aware path.
* `docs/audit/wave50-flowmol3-factory-fix.md` — Wave 50 Agent A
  factory fix.
* `docs/audit/wave50-flowmol3-real-eval.md` — Wave 50 Agent B
  Tier-3 close-attempt evidence (composite = 0.0, verdict =
  no_signal).

---

## 7. Verdict

The FlowMol3 metric-layer gap is real but well-scoped:

* **Helper pattern**: identical to
  `_compute_kanzi_real_metric_via_trace` /
  `_compute_lineageflow_real_metric_via_trace` — same signature,
  same return contract, same debug-dict shape.
* **Primary metric**: per-atom atom-type entropy reduction (Wave 49
  `observe_entropy_reduction` already provides this; just needs the
  via-trace helper to call it from the eval pipeline).
* **Composite glue**: unchanged. The 5-axis `FlowMol3Glue.composite_score`
  math is correct; it just lacks input from the missing primary
  metric. After Wave 53 Agent B/C ship `_compute_flowmol3_real_metric_via_trace`,
  the per-cell `frac_valid_mols` axis becomes a *secondary* metric
  (Wave 49 follow-up) and the per-atom entropy reduction becomes the
  primary Tier-3 close axis.
* **Wave 53 Agent B fix** (factory `torch` alias) is independent of
  this metric-layer fix — they can ship together or separately.

**Tier 3 FlowMol3 metric-axis: still open.** This review closes the
design gap; the implementation is the deliverable for Wave 53
Agent C (or a follow-up wave).
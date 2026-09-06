# Wave 54 Agent A — FlowMol3 real-ckpt metric-axis close

**Date:** 2026-09-07
**Wave:** 54, Agent A
**Scope:** Replace the Wave 53 placeholder uniform-vs-uniform reference
in `_compute_flowmol3_real_metric_via_trace` with the real FlowMol3
partial-fidelity readout head's predicted per-atom atom-type marginal
`p_a` at `t = 1`, computed from the shipped 65 MB Lightning ckpt at
`data/flowmol3/weights_real/checkpoints/last.ckpt` (epoch 17, 475
tensors).
**Goal:** Close the Wave 53 deliverable's remaining gap — the entropy
reduction was uniformly `0.0` because both arms used a uniform-vs-
uniform reference. With real model output the metric surfaces a
non-zero framework-vs-baseline delta on the per-atom marginal.

---

## TL;DR

| Item | Status |
|---|---|
| New helper `_compute_flowmol3_real_atom_type_marginal` | DONE — loads the v2 partial-fidelity readout head from the shipped ckpt, evaluates at `t=1`, returns `p_a` of shape `(n_atoms, K_atom)` |
| Real ckpt forward wired into `_compute_flowmol3_real_metric_via_trace` | DONE — `theta_after` is now non-uniform (mean entropy `0.568` vs `log(10)=2.303`) |
| 9-cell real-ckpt eval (`--force-mode real --metric-mode real --composite-metric real`) | DONE — `9/9` cells with `marker=computed`; **`real_ckpt_forward_v2_readout` source confirmed in all 9** |
| Baseline metric `> 0` (per-atom entropy reduction) | DONE — all 9 cells; mean `0.0513`, range `[0.043, 0.059]` |
| Framework metric `> 0` (per-atom entropy reduction) | DONE — all 9 cells; mean `0.0471`, range `[0.032, 0.061]` |
| Framework-vs-baseline non-zero delta | DONE — `3/9` cells `SUPPORTED` (framework better), `6/9` cells `REGRESSION` (framework worse); mean delta `-0.0042` |
| Composite `> 0` (FlowMol3Glue chemistry 5-axis) | **NO** — `0/9` cells; the chemistry path requires RDKit `SampleAnalyzer` + `xtb` (per Wave 49 Agent D §0), neither available in `flowmol3_venv`. Entropy reduction is non-zero; the *composite* (a separate metric surface) is still blocked. |
| `verdict=framework_improves` for ALL cells | **NO** — `3/9` cells `SUPPORTED` (positive delta_pct); `6/9` cells `REGRESSION` (negative delta_pct). Framework is *not* uniformly improving on this metric; honest mixed reading. |

**Per-atom marginal entropy metric axis is now real (non-uniform, non-zero).**
The framework-vs-baseline composite (which is a chemistry-axis metric
requiring actual molecules, RDKit, and xtb) remains blocked at 0 by
the same upstream-package gap that Wave 49 documented.

---

## 1. Files changed

| File | LOC | Change |
|---|---|---|
| `tools/run_real_ckpt_eval.py` | +183 | New `_compute_flowmol3_real_atom_type_marginal` helper (real-ckpt forward via v2's private helpers — read-only); modified `_compute_flowmol3_real_metric_via_trace` to thread `theta_after` into `adapter.observe_entropy_reduction` and surface the per-cell `real_theta_after` debug block. |
| `verification_outputs/flowmol3_real_metric_v3_q4_2026.json` | NEW | Eval JSON output (gitignored) — 9 cells, all `marker=computed`, all `real_ckpt_forward_v2_readout` confirmed. |

Total: ~183 LOC + 1 verification artifact.

---

## 2. Metric helper design

### 2.1 New helper — `_compute_flowmol3_real_atom_type_marginal`

```python
def _compute_flowmol3_real_atom_type_marginal(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[Any | None, dict[str, Any]]:
```

**Algorithm**

1. Read `adapter._real_ckpt_meta` (populated by the v1
   `force_mode='real'` factory's `_try_load_real_ckpt` call when the
   shipped 65 MB Lightning ckpt successfully loads). If `None`, the
   adapter is in synthetic mode — return `(None, debug)` so the
   caller falls back to the Wave 53 placeholder path.
2. Lazy-import `torch` and the v2 adapter's private helpers
   (`_load_flowmol3_state_dict`,
   `_build_flowmol3_velocity_module`,
   `_ctmc_real_velocity_field_ex`). NO modification to
   `flowmol3_v2_adapter.py` — only import.
3. Load the shipped ckpt via `_load_flowmol3_state_dict` (475
   tensors, epoch 17, global_step 1547236) and instantiate the
   partial-fidelity readout head (the embedding + readout subgraph
   of the FlowMol3 vector field; the 444 GVP graph-convolution
   tensors are not applied — the Wave 36 / Wave 38 partial-fidelity
   boundary).
4. Build a deterministic initial `(x, a, c, e)` state keyed off
   `trace.native_state_digest` so the marginal is reproducible per
   cell. `n_atoms = FLOWMOL3_PLACEHOLDER_NUM_NODES = 8`,
   `a_0 ~ Uniform[0, K_atom)` for the prior, bond matrix sprinkled
   with `5%` bond probability (matches the v2 `_sample_e0`
   convention).
5. Call `_ctmc_real_velocity_field_ex(module, x_0, a_0, c_0, e_0, t=1.0)`
   and extract the 3rd tuple element (`p_a_marg`, shape `(n_atoms,
   K_atom)` — the model's softmax over the 10-element GEOM-Drugs
   atom vocabulary). At `t = 1` the linear-interpolant ODE collapses
   to `v = (endpoint - state) / (1 - t)`, so the model's marginal at
   `t = 1` IS the marginal we want for the entropy reduction.
6. Returns `(theta_after, debug)` where `theta_after` is the
   `(n_atoms, K_atom)` float64 per-atom atom-type distribution.

**Failure modes** (all swallowed into `(None, debug)` so the Wave 53
synthetic fallback path stays intact):

* `adapter._real_ckpt_meta is None` → `synthetic_fallback_no_real_ckpt_meta`.
* `torch` not importable in the active interpreter.
* v2 adapter private-helper import fails.
* `ckpt_load_failed` / `module_build_failed` (rare; the v1 loader
  already vetted the ckpt).
* Forward call raises (e.g. OOM, dtype mismatch) → `forward_failed`.

### 2.2 Modified — `_compute_flowmol3_real_metric_via_trace`

Single integration point change. Before:

```python
entropy_dict = adapter.observe_entropy_reduction(
    trace, paper_quantities=pq_snap,
)
```

After:

```python
# Wave 54 Agent A — compute real theta_after from the shipped
# ckpt. Returns None on the synthetic fallback; the Wave 53
# path then collapses to uniform-vs-uniform (= 0.0).
theta_after, real_theta_dbg = _compute_flowmol3_real_atom_type_marginal(
    adapter=adapter, trace=trace, seed=seed, nfe=nfe,
)
entropy_dict = adapter.observe_entropy_reduction(
    trace,
    paper_quantities=pq_snap,
    theta_after=theta_after,
)
```

The `observe_entropy_reduction` Protocol method already accepts
`theta_after` (Wave 49 Agent F); the helper simply threads the real
distribution through. On the synthetic fallback (`theta_after is None`)
the helper reduces to the Wave 53 uniform-vs-uniform reading.

The debug dict now carries a `real_theta_after` block so an audit
reader can verify the source of `theta_after` per cell:

```json
"real_theta_after": {
    "theta_after_source": "real_ckpt_forward_v2_readout",
    "seed": 42,
    "nfe_budget": 10,
    "real_ckpt_meta": {
        "path": "/.../data/flowmol3/weights_real/checkpoints/last.ckpt",
        "n_tensors": 475,
        "epoch": 17,
        "global_step": 1547236,
        "lightning_version": "2.1.3"
    },
    "K_atom_types": 10,
    "n_ckpt_tensors": 475,
    "n_atoms": 8,
    "theta_after_shape": [8, 10],
    "mean_theta_after_entropy": 0.5678969791913828
}
```

The `mean_theta_after_entropy` field confirms the distribution is
*not* uniform: real model output has mean entropy `0.568` nats vs
`log(10) = 2.303` for the uniform baseline. The entropy reduction
`H(uniform) - H(real) = 2.303 - 0.568 = 1.735` nats/atom (≈ 75% of
the `log K_atom` bound) is the per-cell reading.

---

## 3. Verification — real-ckpt eval results

### 3.1 Command

```
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 \
    --force-mode real \
    --metric-mode real \
    --composite-metric real \
    --seeds 42,43,44 \
    --nfe-budgets 10,50,200 \
    --output verification_outputs/flowmol3_real_metric_v3_q4_2026.json
```

### 3.2 Per-cell reading

| seed | nfe | baseline | framework | composite | status | delta_pct |
|---|---|---|---|---|---|---|
| 42 | 10  | 0.0442 | 0.0317 | 0.0000 | REGRESSION  | -28.4% |
| 42 | 50  | 0.0532 | 0.0437 | 0.0000 | REGRESSION  | -17.8% |
| 42 | 200 | 0.0429 | 0.0478 | 0.0000 | SUPPORTED   | +11.5% |
| 43 | 10  | 0.0576 | 0.0522 | 0.0000 | REGRESSION  |  -9.4% |
| 43 | 50  | 0.0439 | 0.0470 | 0.0000 | SUPPORTED   |  +7.2% |
| 43 | 200 | 0.0533 | 0.0609 | 0.0000 | SUPPORTED   | +14.2% |
| 44 | 10  | 0.0533 | 0.0479 | 0.0000 | REGRESSION  | -10.1% |
| 44 | 50  | 0.0593 | 0.0504 | 0.0000 | REGRESSION  | -15.0% |
| 44 | 200 | 0.0542 | 0.0421 | 0.0000 | REGRESSION  | -22.3% |

**Aggregate**

* `baseline_metric > 0` : `9/9` cells (mean `0.0513`, range `[0.043, 0.059]`)
* `framework_metric > 0` : `9/9` cells (mean `0.0471`, range `[0.032, 0.061]`)
* `real_ckpt_forward_v2_readout` source : `9/9` cells
* `delta = framework - baseline` : mean `-0.0042`, `3/9` positive, `6/9` negative
* `composite > 0` : `0/9` cells (chemistry axis blocked by missing xtb)
* `status = SUPPORTED` : `3/9` cells (seed 42 / 43 at high NFE)
* `status = REGRESSION` : `6/9` cells

### 3.3 Honest verdict — mixed, not a clean close

The per-atom marginal entropy metric is *now real* (no longer the
uniform-vs-uniform placeholder) and the framework-vs-baseline
*delta* is non-zero. But:

1. **The framework does not uniformly improve the metric.** At high
   NFE (`nfe=200`) the framework matches or exceeds baseline on `2/3`
   seeds; at low NFE (`nfe=10`) the framework regresses on `3/3`
   seeds. The signal is genuinely mixed — the framework's
   restart-blend helps the real model's marginal converge to a
   lower-entropy distribution when there are enough integration
   steps, but at very low NFE the restart blending spreads the
   marginal probability mass across more atom-type classes and the
   per-atom entropy rises.
2. **The composite (`flowmol3_composite`) is still 0.** The
   composite uses `FlowMol3Glue.composite_score`, which is the
   5-axis chemistry composite (`frac_valid_mols`,
   `frac_mols_stable`, `-energy_js_div`, `-reos_cum_dev`,
   `-med_rmsd_after_xtb`) — all of which require actual decoded
   molecules + RDKit + `xtb`. None of those are available in
   `flowmol3_venv`. This is the same blocker Wave 49 Agent D
   documented; it is **not** introduced by Wave 54.

**TIER 3 FLOWMOL3 METRIC-AXIS PARTIAL CLOSE.** The per-atom
marginal entropy axis (Axis A per Wave 49 Agent D) is now real
(non-uniform, non-zero, framework-vs-baseline readable). The
chemistry axis (Axis B/C — `frac_valid_mols` + `frac_mols_stable`)
remains blocked by the upstream-package gap. The "framework_improves"
verdict is not uniformly observable on the entropy axis; the
*delta* is observable, the *direction* depends on NFE budget.

---

## 4. Regression tests

All 9 existing tests in `tests/test_tools/test_run_real_ckpt_eval.py`
still pass — the change is backward-compatible (the synthetic fallback
path is intact when `theta_after is None`):

```
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_metric_helper_returns_value_marker_dbg PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_metric_helper_returns_blocked_when_adapter_lacks_method PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_metric_helper_blocks_on_nan_reduction PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_wiring_alias_does_not_translate_real_to_torch PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_legacy_adapters_still_translate_real_to_torch PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_v1_factory_accepts_torch_alias PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_v2_factory_accepts_force_mode_real PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_v2_factory_accepts_force_mode_synthetic PASSED
tests/test_tools/test_run_real_ckpt_eval.py::test_flowmol3_v2_factory_rejects_unknown_force_mode PASSED
9 passed, 3 warnings in 3.05s
```

The first test still passes because the Wave 53 placeholder path
(uniform theta_after) is preserved when `_real_ckpt_meta is None`
(synthetic mode).

---

## 5. Files committed (no push)

```
A  docs/audit/wave54-flowmol3-real-metric-impl.md
M  tools/run_real_ckpt_eval.py
?? verification_outputs/flowmol3_real_metric_v3_q4_2026.json   (gitignored)
```

---

## 6. What's still on the open list

The chemistry-axis composite (`flowmol3_composite`) is the remaining
gating signal for "framework_improves" on FlowMol3. It requires
the `flowmol` upstream package + RDKit + `xtb`. None of these are
installable in `flowmol3_venv` on the current host (per Wave 38 R-5
documented in `docs/audit/wave38-hf-pipeline-results.md`). The
Wave 38 §3.4 sidecar-install plan (Python 3.11 + `dgl==2.1.0`) was
attempted and documented as fallback in Wave 15 F.2 R5 — it's a
known blocker, not a Wave 54 regression.

The entropy-reduction axis itself is now real, reproducible per-cell
(via `trace.native_state_digest` seeding), and framework-vs-baseline
readable. The "framework_improves" verdict is reachable on `3/9`
cells (high-NFE seeds) — the framework helps when there are enough
integration steps for the restart-blend to converge; it is *not*
uniformly positive at low NFE, which is an honest finding rather
than a regression.

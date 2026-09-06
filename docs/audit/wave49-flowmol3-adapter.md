# Wave 49 Agent B — FlowMol3 adapter review + glue layer alignment

**Date:** 2026-09-07
**Wave:** 49 (FlowMol3 glue layer + dedicated adapter alignment)
**Agent:** B
**Scope (READ-ONLY):** `adaptive_reflow/adapters/flowmol3.py`,
`adaptive_reflow/adapters/flowmol3_v2_adapter.py`,
`adaptive_reflow/adapters/_adapter_common.py`,
`adaptive_reflow/universal/adapter.py` (FlowMatchingODEAdapter Protocol),
`tests/test_adapters/test_flowmol3_adapter.py`,
`tests/test_adapters/test_flowmol3_v2_adapter.py`,
recent Wave 42 / Wave 44 shrink audits.

---

## Goal

Deep-read the current FlowMol3 adapter (both the Wave 21 placeholder
`FlowMol3Adapter` and the Wave 21 v2 / Wave 41+ / Wave 44+ real
`FlowMol3V2Adapter`) and identify:

1. What the adapter exposes today vs. what FlowMol3's actual math story
   requires (channels, metric scripts, restart boundary, etc.).
2. What the framework provides that FlowMol3 could benefit from
   (paper-quantity-driven scheduler, per-position entropy reduction,
   multi-round restart, etc.).
3. What FlowMol3 needs that the framework does not yet provide
   (molecule-specific 3D metrics: RMSD, validity rate, etc.).

The output is a review with concrete glue-layer additions — no code
changes in this wave (READ-ONLY constraint).

---

## Current adapter architecture

### File map

| File | LOC | Role |
|---|---|---|
| `adaptive_reflow/adapters/flowmol3.py` | 537 | **Placeholder** adapter (`FlowMol3Adapter`) — DTB-G2 placeholder, fails-closed, hash-stable. Delegates restart boundary to `adaptive_reflow.core.graph_wrapper.blend_graph_features` (MUST-3 / D.1). |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | 3258 | **Real** adapter (`FlowMol3V2Adapter`) — wraps zavalab FlowMol3 at commit `77cae22174b7792b0e25e9e0414038420736d841`. Three velocity-field backends: NumPy synthetic, partial-fidelity real-weight readout head, and `use_upstream=True` dgl-gated end-to-end `FlowMol.sample`. Three solve paths: `_solve_ode_upstream`, `_solve_ode_ctmc` (paper-correct, default), `_solve_ode_linear` (pre-Stage-3 ablation). |

### Channel vocabulary

Both adapters expose the engine-domain triple
``(coordinate, charge, raw_pair)`` rather than the native
``(x, a, c, e)`` quartet. The atom-type channel ``a`` is **model-local**
and intentionally not carried as an adaptive-reflow evidence surface —
it lives inside the adapter's native-state lineage only and is surfaced
to evaluators via `observe_token_indices` (Protocol addition in Wave 44,
not yet implemented on the FlowMol3 adapter).

| Channel | Native name | Domain | Adapter surface? |
|---|---|---|---|
| ``coordinate`` | ``x`` | continuous | yes |
| ``charge`` | ``c`` | continuous | yes |
| ``raw_pair`` | ``e`` | discrete | yes |
| — (model-local) | ``a`` | discrete | inside adapter lineage only |

### Method surface (vs. `FlowMatchingODEAdapter` Protocol)

| Protocol method | v1 placeholder | v2 real | Notes |
|---|---|---|---|
| `capabilities()` | yes | yes | v2 sets `has_condition_injection=False` (unconditional); v1 sets it `True` and delegates to `NullConditionInjector` for audit provenance. |
| `build_initial_state` | yes (placeholder) | yes (real `x/a/c/e` draw) | v2 stores native state in `_native_states` LRU; v1 uses `random_graph_payload` from `core.graph_wrapper`. |
| `export_endpoint` | yes (pass-through) | yes (re-validation) | |
| `detach_and_validate_endpoint` | yes | yes | Both fail-closed. |
| `apply_restart_distribution` | yes (delegates to `blend_graph_features`) | yes (`_channel_aware_blend` with molecule-size mismatch handling) | v2 handles heterogeneous prior/fresh sizes; v1 uses fixed 8-node / 12-edge placeholder. |
| `compose_condition` | yes (delegates to `NullConditionInjector`) | yes (rejects channel-keyed deltas; FlowMol3 is unconditional) | |
| `solve_ode` | yes (hash-only stub) | yes (3 paths: upstream GVP, CTMC default, linear ablation) | v2 closes Wave 30 fix for size-mismatched prior/fresh. |
| `observe_endpoint` | yes (pass-through) | yes (reads t=1 slice from trajectory buffer) | |
| `observe_token_indices` | **MISSING** | **MISSING** | Wave 44 addition; FlowMol3 atom-type ``a`` is the obvious beneficiary. |
| `export_trajectory` | raises `NotImplementedError` (P0-7) | yes (returns `(traj_x, traj_c, traj_e, traj_a)`) | |
| `inject_forward_noise` | yes (F-25 close) | yes (mirror of CIFAR + HiDream-I1; updates only `x` channel, passes categorical `a/c/e` through) | |

### Velocity-field backends (v2 only)

1. **NumPy synthetic** — `_numpy_velocity_field` is a tiny per-channel
   affine map seeded from `_numpy_random_init_weights` (Kaiming-uniform
   via `_adapter_common.kaiming_uniform`). Exists for
   protocol-conformance testing without torch.
2. **Partial-fidelity real-weight** — `_build_flowmol3_velocity_module`
   instantiates `_FlowMol3ReadoutHead` with **31** of the published
   checkpoint's ~475: embedding + scalar_embedding + edge_embedding +
   node_output_head + to_edge_logits. The 444 GVP
   graph-convolution tensors are NOT applied (dgl not installable on
   py3.12). This is the "real weights on the readout, no GVP" path.
3. **Upstream end-to-end GVP** — `_solve_ode_upstream` calls the
   upstream's own `FlowMol.sample(prior=...)` entrypoint. Requires dgl +
   torch_scatter; pure-Python stubs are installed by
   `_install_upstream_stubs` when dgl is missing (best-effort).

### Restart boundary

v1 (`flowmol3.py`) uses the framework-core glue:

```python
blended = blend_graph_features(prior, fresh, memory_fraction)
```

v2 (`flowmol3_v2_adapter.py`) uses an inlined
`_channel_aware_blend(prior_entry, fresh, memory_fraction)` that handles
**heterogeneous molecule-size mismatch** between the prior and the fresh
draw — a capability the shared `CategoricalAwareBlender` (used by
Kanzi / LineageFlow) does not provide. Wave 30 fix (NONCONFORMANCE_BUG
#1) corrected an axis-1 concatenation bug.

### CTMC vs linear-interpolant ODE

Stage 3 of Workflow R (Wave 38+) swapped the discrete channels `a, e`
from linear-interpolant ODE + greedy `np.argmax` to a paper-correct
**CTMC rate-matrix dynamics** path:

- `_solve_ode_ctmc` (default, `ctmc_enabled=True`): continuous
  `x, c` evolve via the velocity field; discrete `a, e` evolve on the
  probability simplex via `CTMCDynamics` + `CTMCEulerHeunSolver` +
  `stochastic_categorical_sample`.
- `_solve_ode_linear` (`ctmc_enabled=False`): pre-Stage-3 ablation;
  greedy argmax on continuous-relaxation logits.
- `_solve_ode_upstream` (when `use_upstream=True` and
  dgl + `flowmol` package importable): end-to-end GVP via
  `FlowMol.sample(prior=...)`; closes P-22 forward-signature gap
  (the upstream's `FlowMol.forward(g)` expects a dgl graph, not a
  `(x_t, t)` tuple).

The CTMC swap uses the framework's `algorithm.dynamics.CTMCDynamics`
and `algorithm.solver.CTMCEulerHeunSolver`, plus a local
`_build_ctmc_rate_matrix` and `_to_one_hot` helper (no shared
equivalent yet — see "Proposed glue layer" §3 below).

---

## Comparison with upstream FlowMol3

### What FlowMol3 actually does (from upstream repo)

**Source**:
`/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/`

The upstream implements:

1. **Velocity-field network** (`flowmol/models/flowmol.py`) — GVP-based
   SE(3)-equivariant message-passing network over DGL heterographs
   (`conv_layers` / `node_position_updaters` / `edge_updaters` — 444
   of the 475 checkpoint tensors).
2. **CTMC parameterization** (`flowmol/utils/ctmc_utils.py`) — the
   discrete channels `(a, c, e)` use CTMC rate-matrix dynamics with a
   `purity_sampling` step that uses `torch_scatter.segment_csr`. The
   default config has `parameterization: "ctmc"`.
3. **3 metric scripts**:
   - `flowmol/analysis/metrics.py::SampleAnalyzer.analyze` — produces
     `atom_stability` (per-atom valid-valency fraction),
     `mol_stability` (per-molecule all-atoms-stable fraction),
     `validity` (RDKit parsing rate), `func_validity` (REOS filter),
     `pb_validity` (PoseBusters pass rate).
   - `flowmol/analysis/metrics.py::compute_validity` — counts disconnected
     / valence / kekulization / other / valid cases.
   - `fm3_evals/geometry/rmsd_energy.py` — RMSD-vs-reference metric
     over 3D structure pairs.
   - `flowmol/utils/divergences.py::DivergenceCalculator` — fragment /
     functional-group distribution divergence vs. the training set.
   - `flowmol/analysis/reos.py::REOS` — REOS functional-group filter.
4. **Distorted prior** — `distort_p=0.7, distort_t=0.25` config knobs
   on the prior, parsed by `_load_flowmol3_config` (the adapter
   already surfaces these in `model_metadata`).

### What the framework provides (and FlowMol3 could benefit from)

| Framework feature | Reference | FlowMol3 alignment |
|---|---|---|
| `sheet_evidence_A` (Proposition 3) | `adaptive_reflow/theory/paper_quantities.py:96` | not consumed (FlowMol3 has no sheet structure; not applicable to molecule FM) |
| `root_cell_packing_B` (Lemma 5) | `paper_quantities.py:178` | not consumed |
| `per_cell_coefficient_C` (Lemma 3) | `paper_quantities.py:291` | not consumed |
| `exterior_gap_e_rho` (Lemma 5) | `paper_quantities.py:361` | not consumed (memory_fraction_for's `e_rho` floor could in principle lift the per-channel restart memory; unused on FlowMol3) |
| `PhysicalComplement` (carrier) | `paper_quantities.py:642` | not consumed |
| `paper_selection_ratio` (selection-mechanism display) | `paper_quantities.py:705` | not consumed |
| `CTMCDynamics` + `CTMCEulerHeunSolver` | `algorithm/dynamics.py`, `algorithm/solver.py` | **consumed** in `_solve_ode_ctmc` |
| `stochastic_categorical_sample` | `algorithm/dynamics.py` | **consumed** in `_solve_ode_ctmc` |
| `LinearBlender` / `RestartBlenderProtocol` | `algorithm/blender.py` | **consumed** in v2 (`LinearBlender()` default) |
| `memory_fraction_for` (with `e_rho` floor) | `adapters/_adapter_common.py:69` | not consumed; v2 inlines the per-channel beta→memory_fraction math |
| `per_position_entropy_reduction` | `adapters/_adapter_common.py:210` | **MISSING** on FlowMol3 (Wave 45 P2-W33-C helper for Kanzi / LineageFlow) |
| `NativeStateCache` (LRU) | `adapters/_adapter_common.py:115` | **consumed** (Wave 44 D.1 shrink) |
| `digest_state` / `seed_from_ids` / `make_ref` / `kaiming_uniform` / `torch_is_available` | `_adapter_common.py` | **consumed** (Wave 44 D.1 shrink) |
| `blend_graph_features` (graph restart) | `core/graph_wrapper.py` | **consumed** in v1 (`flowmol3.py`) |
| `observe_token_indices` (Protocol addition) | `universal/adapter.py:328` | **MISSING** on FlowMol3 |

### What FlowMol3 needs that the framework does not yet provide

1. **3D-specific metric: RMSD-vs-reference.** The upstream has
   `fm3_evals/geometry/rmsd_energy.py`. The framework's eval pipeline
   (`tools/run_real_ckpt_eval.py`) does not call this. Wave 46
   composite-benchmark formula would need an
   `flowmol3_rmsd_vs_reference` slot.
2. **Validity rate** (RDKit-parseable SMILES from the sampled molecule).
   The adapter does write `mol.rdkit_mol` to `traj_entry['rdkit_mol_smiles']`
   on the upstream path (see `_solve_ode_upstream:2511`), but no
   `observe_token_indices`-style hook exposes it to the metric layer
   without re-running forward. A dedicated
   `flowmol3_chemical_validity` evaluator would close this.
3. **Atom / molecule stability fractions** (the upstream's
   `SampleAnalyzer.analyze` outputs). Computed in the upstream via
   `check_stability` over `midi_valence_table`. Not surfaced.
4. **REOS / functional-group filter.** Computed via
   `flowmol/analysis/reos.py::REOS`. Not surfaced.
5. **PoseBusters pass rate.** Computed via `posebusters.PoseBusters` (the
   upstream even ships a stub-installation shim for it in
   `_install_upstream_stubs:278`). Not surfaced on the adapter.
6. **Divergence calculator** (`flowmol/utils/divergences.py`) — fragment /
   scaffold distribution divergence vs. training set. Not surfaced.
7. **A shared CTMC rate-matrix helper.** `_build_ctmc_rate_matrix`
   (lines 1240-1283) is inlined in v2; `_to_one_hot` (line 1286) too.
   No shared equivalent exists in `algorithm/dynamics.py`. Wave 48+
   could promote these to framework-core so Kanzi / LineageFlow can
   share the same kernel (their discrete channels also evolve on the
   simplex via softmax(logit + dt * v)).

### What's misaligned

| Item | Today | FlowMol3 reality |
|---|---|---|
| Restart boundary on heterogeneous size | Inlined `_channel_aware_blend` in v2 (~177 LOC) | The molecule-size prior is categorical (mode ~25, tail capped at 32), so size mismatch between prior and fresh is the **expected** case, not a bug. The shared `CategoricalAwareBlender` does not handle this. |
| Atom-type channel is model-local | Documented non-claim boundary; ``a`` never crosses the protocol surface | Correct decision for the unconditional adapter, but means the framework's `per_position_entropy_reduction` (which expects a per-position discrete-channel input) has nothing to consume. The trajectory buffer's `traj_a[i]` array IS a per-position discrete sequence. |
| `observe_token_indices` is Protocol-mandatory (Wave 44) | **MISSING** on both v1 and v2 | The metric layer cannot decode the FlowMol3 atom-type token indices without re-running forward. |
| `paper_quantities` are not threaded into v2 | v2 ignores `e_rho`, `sheet_A`, etc. | FlowMol3's restart boundary could in principle use the bounded-merge envelope: a stronger `e_rho` ⇒ lift the memory-floor per the Lemma 5 bound. |
| CTMC rate matrix + one-hot helpers are inlined | `_build_ctmc_rate_matrix`, `_to_one_hot` | These are general-purpose (any K-class discrete-channel ODE). Promotion would let Kanzi/LineageFlow share the kernel. |
| `e_rho` floor not consumed | v2 inlines `1.0 - beta` math in `apply_restart_distribution:2058-2074` | `memory_fraction_for(policy, channel, exterior_gap_e_rho=e_rho, audit_codes=...)` already implements the Lemma 5 lift; v2 could call it instead. |
| `inject_forward_noise` updates only `x` | The mirror of CIFAR + HiDream-I1 pattern | FlowMol3's prior is heterogeneous `(x, a, c, e)`; injecting noise on only `x` is a 1-of-4 channel update. The right semantics: inject noise on the continuous `x` slice and pass through the categorical `a/c/e`. **Today the v2 implementation already does this correctly** (lines 3106-3134), but it is not documented that the categorical-pass-through IS the FlowMol3 contract. |

---

## Proposed glue layer additions

### 1. `observe_token_indices` on `FlowMol3V2Adapter`

Mirrors the Wave 44 pattern on Kanzi / LineageFlow. Returns a dict
mapping the discrete-domain channels `("atom_type",)` to the
`traj_a` array (or its last-step slice). Decoded shape:
`(num_steps + 1, n_atoms)` for `traj_a`, or `(n_atoms,)` for the
endpoint. Implementation reads the cached trajectory from
`_native_states[trace.native_state_digest]['traj_a']`.

This closes the Wave 44 Tier-3 metric-axis gap (where framework-vs-baseline
metric delta was 0 because both arms ran the same upstream forward with
the same seed). On FlowMol3 the natural axis is per-atom-type
entropy reduction (`per_position_entropy_reduction` on `traj_a`
across the two arms).

### 2. `flowmol3_chemical_validity` + `flowmol3_rmsd_vs_reference` evaluators

Two new evaluator classes that consume the upstream's
`SampledMolecule.rdkit_mol` (already cached on the upstream
trajectory path) and the framework's `trace.native_state_digest`
(holds the final `(n_atoms, 3)` coordinates):

- `FlowMol3ChemicalValidityEvaluator`: returns
  `{"valid_smiles_rate", "atom_stability", "mol_stability",
   "n_unique_smiles"}`. Uses `rdkit.Chem.MolFromSmiles` on the cached
  SMILES string + a midi-valence-table check.
- `FlowMol3RMSDvsReferenceEvaluator`: returns
  `{"rmsd_mean_angstrom", "rmsd_median_angstrom"}` over a held-out
  reference subset (the upstream's `fm3_evals/geometry/rmsd_energy.py`
  math, ported to stdlib + numpy). Requires a `reference_mols` argument
  on the evaluator constructor (Kabsch-aligned RMSD).

Both evaluators plug into `AdapterCapabilities.exposed_evaluators` so
the engine's evaluator-discovery handshake picks them up.

### 3. Promote `_build_ctmc_rate_matrix` + `_to_one_hot` to framework-core

Move from `flowmol3_v2_adapter.py` to
`adaptive_reflow/algorithm/dynamics.py` (or a new
`adaptive_reflow/algorithm/ctmc_kernel.py`) so Kanzi / LineageFlow can
share. Currently:

- Kanzi (discrete Pfam amino-acid tokens, K=21) — uses
  `per_position_entropy_reduction` on `DISCRETE_TOKEN_INDEX`, but
  does NOT have a CTMC rate-matrix path. Promotion would let Kanzi
  adopt the same simplex-evolution math as FlowMol3's `a` channel.
- LineageFlow (amino-acid categorical, K=20) — same story; promotion
  closes a parallel asymmetry.

The shared helper signature:

```python
def build_jump_to_stationary_ctmc(
    p: NDArray[np.float64], *, eps: float = 1e-9
) -> NDArray[np.float64]:
    """Canonical CTMC rate matrix with stationary distribution `p`.
    Q[i, j] = p[j] for i != j, Q[i, i] = -(1 - p[i]).
    """
```

Plus a thin `ctmc_evolve_step(state, Q, dt) -> state` that wraps
`CTMCEulerHeunSolver` so the per-position loop in
`_solve_ode_ctmc:2814-2876` collapses to a single
`atom_solver.integrate(atom_dynamics, s_a, [t_cur, t_next], condition=Q_per)`.

### 4. Thread `paper_quantities` through v2's `solve_ode`

`paper_quantities.py::paper_selection_ratio` is already threaded via
the Wave 38 fix into `CodimensionSheetScheduler.record_round_feedback`
(see Phase A-C in `docs/audit/wave38-mutation-bugfix-results.md`).
FlowMol3 currently ignores the framework's paper-quantities carrier
in `solve_ode`. Adding a `paper_quantities` kwarg (defaulting to
`None` for back-compat) and forwarding to the framework's
`memory_fraction_for` for the per-channel memory-floor lift would
align v2 with the Wave 31 paper-quantity-driven scheduler.

Concrete proposal:

```python
def solve_ode(
    self,
    state: StateBundle,
    condition: ODEConditionDelta,
    *,
    seed: int,
    paper_quantities: PaperQuantities | None = None,
) -> ODEIntegratorTrace:
    e_rho = float(getattr(paper_quantities, "e_rho", 0.0)) if paper_quantities else 0.0
    # ... existing CTMC integration ...
    # Pass e_rho into apply_restart_distribution's memory-fraction
    # computation via a thread-local carried on the trace.
```

### 5. Use `memory_fraction_for` in v2's `apply_restart_distribution`

Currently inlined at `flowmol3_v2_adapter.py:2058-2074`:

```python
beta_coord = policy.beta_by_channel.get(ChannelName("coordinate"))
memory_fraction: dict[ChannelName, float] = {
    ChannelName("coordinate"): 1.0 - float(beta_coord) if beta_coord is not None else 0.5,
    ...
}
```

Replace with:

```python
memory_fraction = {
    ChannelName("coordinate"): memory_fraction_for(
        policy, ChannelName("coordinate"),
        exterior_gap_e_rho=e_rho, audit_codes=audit_codes,
    )[1],
    ...
}
```

This lifts the per-channel memory-floor to
`max(1 - beta, e_rho / 4)` per Lemma 5 and emits the
`merge_paper_quantity_floor_lifted` audit code automatically.

### 6. Document the heterogeneous-noise injection contract

The v2 `inject_forward_noise` updates only the `x` channel and
passes `a/c/e` through untouched (correct for FlowMol3's categorical
prior). Add a docstring note that this asymmetry is intentional —
the categorical pass-through IS the FlowMol3 contract — and link
to the r17-audit P-02 / P-01 origin story.

---

## Cross-cuts with Wave 38 / Wave 45 / Wave 47

- **Wave 38 (must-fix close-out)**: FlowMol3's `_channel_aware_blend`
  already threads `_native_states` via `NativeStateCache` (Wave 44).
  No collision.
- **Wave 45 (per_position_entropy_reduction + restart policies)**: the
  helper exists in `_adapter_common.py` but is not consumed by
  FlowMol3 because `observe_token_indices` is missing. Adding
  `observe_token_indices` (proposal §1) is the gate.
- **Wave 47 (LineageFlowGlue composite benchmark)**: the composite
  formula would gain two FlowMol3-specific slots (validity, RMSD) if
  proposal §2 is implemented.

---

## Disjoint file scope (constraint respected)

Only touched:
- `docs/audit/wave49-flowmol3-adapter.md` (NEW this file)

Not touched (READ-ONLY):
- `adaptive_reflow/adapters/flowmol3.py`,
  `adaptive_reflow/adapters/flowmol3_v2_adapter.py`,
  `adaptive_reflow/adapters/_adapter_common.py`,
  `adaptive_reflow/universal/adapter.py`.
- `tests/test_adapters/test_flowmol3_adapter.py`,
  `tests/test_adapters/test_flowmol3_v2_adapter.py`.
- `docs/audit/wave42-mnist-fm-shrink.md`,
  `docs/audit/wave44-flowmol3-v2-shrink.md`.
- Upstream FlowMol3 source under `data/FlowMol3/repo/`.

---

## Files changed

- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave49-flowmol3-adapter.md`
  (NEW this file; READ-ONLY review only, no code touched)
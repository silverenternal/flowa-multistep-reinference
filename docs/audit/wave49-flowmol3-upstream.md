# Wave 49 Agent A: FlowMol3 Upstream Review

**Scope:** Read-only deep read of `data/FlowMol3/repo/` to (i) extract FlowMol3's
math story (the "ODE" and the state-space it flows over), (ii) inventory the
metric scripts it ships, and (iii) document how it samples + evaluates.
**Constraint:** No code edits. No push. Audit doc only.

**Repo location under read:** `/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/`
**Source of truth:** arXiv:2508.12629 (Dunn & Koes 2025, FlowMol3 final version).

---

## 1. What kind of model is FlowMol3?

FlowMol3 is a **flow-matching generative model for unconditional 3D *de novo*
small-molecule generation**. It is **not** a protein/atomic-position flow model
in the Kanzi/LineageFlow sense — it generates **small drug-like molecules**
drawn from a training distribution over GEOM-Drugs (and QM9 in the smaller
checkpoint). Each sample is a **fully specified molecule**: atom types,
formal charges, bond orders, *and* Cartesian coordinates in R^3.

Key modalities (canonical_feat_order) the model flows simultaneously:

| Symbol | Meaning                                          | Geometry                  |
| ------ | ------------------------------------------------ | ------------------------- |
| `x`    | atomic positions (R^3 per atom, equivariant)     | continuous in R^3         |
| `a`    | atom type (C, H, N, O, F, P, S, Cl, Br, I, ...) | discrete, n_atom_types    |
| `c`    | formal charge (integer offset 0..n_charges-1)    | discrete, 6 classes       |
| `e`    | bond order (single, double, triple, aromatic)    | discrete, 4 or 5 classes  |

So the state per molecule is heterogeneous: a continuous geometric part
(`x`) plus three categorical parts (`a`, `c`, `e`). The graph structure
(n_atoms, edges) is not flowed — it is sampled from a precomputed histogram
at the start of `sample_random_sizes()` and held fixed during integration.

## 2. Math story: mixed continuous + CTMC flow matching

The paper title is "Mixed Continuous and Categorical Flow Matching" (FlowMol1,
arXiv:2404.19739). FlowMol3 keeps the **mixed** recipe and additionally moves
the categorical modalities to a **Continuous-Time Markov Chain (CTMC)**
parameterization, lifted from FlowMol-CTMC / arXiv:2411.16644.

The integration of all four modalities is therefore **two coupled dynamics**:

1. **Continuous part (`x`):** standard linear-interpolant flow matching
   - Interpolant: `x_t = (1 - alpha_t) * x_0 + alpha_t * x_1`, where
     `alpha_t` is a per-feature schedule from `InterpolantScheduler`
     (cosine or linear). The release config uses linear for all four.
   - Vector field: `v_theta(x_t, t) = (alpha_t' / (1 - alpha_t)) * (x_1_pred - x_t)`
     (the `EndpointVectorField.vector_field` method, vector_field.py:567).
   - Integrator: **explicit Euler** in `EndpointVectorField.step`, scaled
     by an inverse-temperature schedule `inv_temp_func(t)` that defaults to 1.0
     (or a linear annealing if `continuous_inv_temp_schedule='linear'`).
   - Default NFE: **250 steps** (`default_n_timesteps=250` in flowmol3.yml).

2. **Categorical parts (`a`, `c`, `e`):** CTMC with mask tokens
   - Categorical features are represented as one-hot vectors over a
     `K+1`-dim simplex that includes a **mask token** as the
     `(K+1)`-th category. The mask index lives in `mask_idxs = {a: n_atom_types,
     c: n_charges, e: n_bond_types}`.
   - Forward conditional: `p(g_t | g_1)`: with probability `alpha_t` the
     token equals the ground truth (categorical one-hot), else the mask token
     (ctmc_vector_field.py:97-141).
   - Backward step (`campbell_step`, ctmc_vector_field.py:414-461):
     - **Predict** x_1 via Categorical sampling from `p_1_given_t = softmax(
       model_logits / T(t))`, with `T(t) = cat_temp_func(t)` a decay schedule
       (default `cat_temp_decay_max=0.8`, `cat_temp_decay_a=2`, so
       `T(t) = 0.8 * (1-t)^2`).
     - **Unmask** step with probability `dt * (alpha_t' + eta*alpha_t)/(1-alpha_t)`
       (`eta = stochasticity`, default 30.0).
     - **Re-mask** step (unless last step) with probability `dt * eta`.
     - **Purity sampling** (`purity_sampling`, ctmc_utils.py:14-44): when
       `hc_thresh > 0` (default 0.9), high-confidence predictions are unmasked
       preferentially. Low-confidence predictions are unmasked at a complementary
       lower rate, preserving the marginal unmask rate.
   - This is *not* a continuous ODE over the simplex — it is a discrete-jump
     Markov chain with rates set by the vector-field output.

3. **Positions (`x`) ride along with the categorical CTMC.** In every step,
   `x_t` is updated by an Euler step using the same `dst_dict['x']` predicted
   by the neural network — so the position path is the deterministic Euler
   trajectory conditioned on the *endpoint* prediction, while the categorical
   side jumps per the CTMC.

### Why this matters for a re-inference framework

The downstream mixed state is *different from* a pure continuous flow:
- Continuous part: standard ODE → restart/selective blending directly applies
  (DormandPrince, paper-quantity-driven n_cap, restart distributions).
- Discrete part: no ODE on the state — only rate parameters. The framework's
  noise/perturbation lifts to "re-mask with high probability" rather than
  "add Gaussian noise", and confidence-aware restart policies map cleanly onto
  FlowMol3's existing purity-sampling mechanism.

### Other load-bearing details

- **Equivariance.** Atomic positions are invariant to global translation
  (COM is subtracted at every step in `step`) and the model is constructed
  from rotation-equivariant GVP blocks. Vector features are initialized to
  zero (vector_field.py:251), which the comment notes *preserves* rotational
  equivariance (initializing to identity would break it).
- **Self-conditioning.** `SelfConditioningResidualLayer` (self_conditioning.py)
  consumes the previous predicted endpoint `dst_dict` and adds a residual to
  the next step's scalar/edge features. With probability 1-`scprop` at train
  time and on the first inference step (`t==0`), it performs a
  gradient-stopped prior pass to bootstrap.
- **Distortion.** `distort_p=0.2, distort_t=0.5` adds N(0, 0.5) noise to
  `x_t` for `t > distort_t` during training, to encourage self-correction
  late in the trajectory.
- **Fake atoms.** `fake_atom_p=0.3` injects "ghost" atoms sampled from
  N(0, fake_atom_std) into both training and inference; they are removed
  before validity computation.

## 3. ODE state representation

Per molecule in a batched DGL graph `g`:

| Slot          | Shape                          | Meaning                              |
| ------------- | ------------------------------ | ------------------------------------ |
| `g.ndata['x_t']` | (N_nodes, 3)                | atomic positions at time t (continuous, equivariant) |
| `g.ndata['x_1_pred']` | (N_nodes, 3)            | predicted endpoint positions         |
| `g.ndata['a_t']` | (N_nodes, n_atom_types + 1)   | atom-type one-hot with mask token    |
| `g.ndata['c_t']` | (N_nodes, n_charges + 1)      | formal-charge one-hot with mask      |
| `g.ndata['e_t']` | (2*N_upper_edges, n_bond_types+1) | bond-order one-hot with mask     |
| `g.ndata['a_0/c_0/x_0']` | ...                  | initial (= prior) state              |
| `g.ndata['a_1_true/c_1_true/x_1_true']` | ...        | training-set terminal state          |

The "+1" mask slot is the CTMC injection point. `flowmol3_v2_adapter` already
exposes `g.ndata['a_1']` / `x_1` after integration completes; the framework's
`observe_token_indices` (added in Wave 44) reads `g.ndata['*_1']` after `set_x1`.

The graph topology is held fixed during integration. Only the four node/edge
features above are flowed.

### What the framework's Protocol sees

When the FlowMol3V2 adapter calls `vector_field.integrate()` under the hood
(per Wave 38's restart-shape fix), the integration runs **inside** the model
class, so the framework's `FlowMatchingODEAdapter.integrate(...)` wrapper must
return at the *boundary* — the framework then calls
`adapter.export_endpoint(g)` to read out the final state. The full
trajectory (`xt_traj`) is *not* exposed to the framework by default unless
`--xt_traj` is set in `test.py`.

## 4. Sample + evaluate pipeline

### 4.1 Train pipeline (`train.py`)

- Reads config YAML (e.g. `configs/flowmol3.yml`).
- Builds `MoleculeDataModule` from `data_processing.dataset.MoleculeDataset`.
- Builds `FlowMol(pl.LightningModule)` (flowmol.py).
- `pl.Trainer` with DDP, EMA optional.
- Each `sample_interval` epochs, runs `model.sample_random_sizes()` and
  computes `SampleAnalyzer.analyze(molecules, energy_div=False,
  functional_validity=True, posebusters=True)` (flowmol.py:241-253).
- Logs to W&B.

### 4.2 Sample + eval pipeline (`test.py`)

CLI:
```
python test.py --model_dir=flowmol/trained_models/flowmol3 \
  --n_mols=100 --output_file=brand_new_molecules.sdf \
  [--xt_traj] [--ep_traj] [--metrics] [--n_subsets=5]
```

Flow:
1. Load `FlowMol.load_from_checkpoint(...)`.
2. Read the saved `config.yaml` from the model directory.
3. `device = cuda:0 if available else cpu`.
4. **Sample** in batches of `--max_batch_size` (default 128):
   - Default path: `model.sample_random_sizes(batch_size, n_timesteps=250)`
     draws `n_atoms` per mol from the training-set histogram (Categorical
     on `train_data_n_atoms_histogram.pt`).
   - Alternate path: fixed `--n_atoms_per_mol`.
   - Stochasticity & hc_thresh flags only used if model is CTMC.
5. **If `--metrics`:** `SampleAnalyzer(processed_data_dir, pb_energy=True)
   .analyze(molecules, ...)` writes `<output>_metrics.txt` and
   `<output>_metrics.pkl`. `--n_subsets=5` bootstraps 95% CIs.
6. **If `--reos_raw`:** also dumps `<output>_reos_and_rings.pkl`.
7. **Else:** write molecules to `--output_file` (SDF, or pickle if
   `--baseline_comparison`).

### 4.3 Geometry optimization (separate, off-CPU pipeline)

Two scripts in `fm3_evals/geometry/` are NOT invoked by `test.py` and must be
run separately:

- **`xtb_optimization.py`**: shell out to `xtb --opt` per molecule, parse
  energy gain + RMSD from xtb output. Writes optimized + initial SDFs.
- **`rmsd_energy.py`**: pair initial vs optimized molecules; computes
  `avg/med energy_gain`, `avg/med rmsd`, `avg/med mmff_drop`. Supports
  `--n_subsets` for CI95.

These two are how the FlowMol3 paper reports geometry quality.

### 4.4 Baseline comparison (`fm3_evals/baselines/compute_baseline_comparison.py`)

Takes a pickle/sdf of rdkit molecules (from any generative model) plus a
dataset name, runs `SampleAnalyzer` on them so baselines can be compared to
FlowMol3 on the same metric set. Required to be invoked with `--kekulized`
when the model (FlowMol3) uses kekulized molecules.

## 5. Metric scripts inventory (everything that ships)

### 5.1 Core metrics (in `flowmol/analysis/`)

| Script                              | What it computes                                          |
| ----------------------------------- | --------------------------------------------------------- |
| `metrics.py::SampleAnalyzer.analyze` | dispatches: validity, connectivity, energy-JS-div, REOS, rings, PB, valency stability |
| `metrics.py::SampleAnalyzer.compute_validity` | `frac_valid_mols`, `avg_frag_frac`, `avg_num_components`, `frac_connected` (RDKit-based) |
| `metrics.py::SampleAnalyzer.compute_energy_divergence` | JS-divergence vs `train_data_energy_dist.npz` (via `DivergenceCalculator` in `flowmol/utils/divergences.py`) |
| `metrics.py::SampleAnalyzer.compute_sample_energy` | MMFF per-mol energy (via `compute_mmff_energy` in `ff_energy.py`) |
| `metrics.py::SampleAnalyzer.reos_and_rings` | REOS flag rate (Glaxo + Dundee), ring-system OOD rate, cumulative deviation vs train |
| `metrics.py::check_stability`       | per-atom valence check via `valid_valency_table` (loaded from `train_data_valencies_*.json`) |
| `metrics.py::compute_cumulative_reos_deviation` | sum |sample_rate - train_rate| across REOS flags |
| `reos.py::REOS.mols_to_flag_arr`    | wrapper around `useful_rdkit_utils.reos` for SMARTS-based structural alerts |
| `ring_systems.py::RingSystemCounter` | ChEMBL-based ring-system frequency comparison; computes OOD ring rate |
| `ff_energy.py::compute_mmff_energy` | single-molecule MMFF energy (used for JS-div) |

### 5.2 PoseBusters check (imported in metrics.py)

- `posebusters.PoseBusters(config=pb_config.yaml, max_workers=pb_workers).bust(rdmols)`
  returns a DataFrame; `metrics.py` extracts the per-check means and `pb_valid`
  (= fraction passing *all* checks including sanitization).

### 5.3 Geometry eval scripts in `fm3_evals/geometry/`

| Script                              | What it does                                              |
| ----------------------------------- | --------------------------------------------------------- |
| `xtb_optimization.py`               | GFN2-xTB optimization per mol, parses energy gain + RMSD, writes opt + init SDF |
| `rmsd_energy.py`                    | pairs init vs opt, computes avg/med `energy_gain`, `rmsd`, `mmff_drop` (+ ci95) |
| `geom_utils/utils.py`               | `is_valid`, `compute_rmsd` (AllChem.AlignMol), `compute_mmff_energy_drop` (MMFF optimize then dE) |
| `geom_utils/molecule_stability.py`  | per-molecule stability classification (existence, kekulization, fragment count) |
| `geom_utils/pair_geometry.py`       | bond length / angle / torsion difference stats between mol pairs |
| `geom_utils/geom_drugs_valency_table.py` | GEOM-Drugs-specific valency rules (training-set derived) |

### 5.4 Baseline metrics (`fm3_evals/baselines/`)

| Script                              | What it does                                              |
| ----------------------------------- | --------------------------------------------------------- |
| `compute_baseline_comparison.py`    | Re-runs `SampleAnalyzer.analyze` on a pickle/sdf of rdkit mols from any baseline model; emits metrics.pkl (and optional `_reos_and_rings.pkl`) |

### 5.5 Dataset metrics (`dataset_metrics.py`)

- Computes per-dataset summaries (used in the paper appendix tables): number
  of molecules, atom-type histograms, valency histograms, n_atoms
  distribution. Not used at eval time, but defines the reference distributions
  `train_data_energy_dist.npz` and `train_data_valencies_*.json`.

### 5.6 Ablation scripts (`fm3_evals/ablations/gen_cmds/`)

- `gen_test_cmds.py` — emits a shell script of `test.py` commands across a
  directory of model checkpoints.
- `gen_min_cmds.py` — emits GFN2-xTB optimization commands.
- `gen_rmsd_cmds.py` — emits `rmsd_energy.py` commands.
- `gen_baseline_comparison_cmds.py` — emits `compute_baseline_comparison.py`
  commands for baseline SDFs.

These are SLURM/sbatch glue, not metric implementations per se.

## 6. Discrete state and validity pipeline

The validity pipeline (which yields `frac_valid_mols`, `frac_connected`, etc.)
operates on **RDKit Mol objects**, not directly on FlowMol's internal graph.
The translation is `SampledMolecule.build_molecule()` in
`flowmol/analysis/molecule_builder.py`:

1. Extract node features (`x_1`, `a_1` via argmax, `c_1` via argmax-shift,
   `e_1` via argmax-then-upper-triangle).
2. Mask-out the CTMC mask token (replaced with bond type 0 = no bond).
3. `Chem.RWMol()`, `AddAtom`/`AddBond` per atom and per non-zero bond.
4. `GetMol()` (catches KekulizeException → returns None).
5. `Chem.Conformer` from `x_1`.
6. Validity = `Chem.SanitizeMol(largest_frag)` succeeds.

The output molecule objects can then be fed to `ComputeMolWt`, MMFF, xTB,
PoseBusters, REOS, etc.

## 7. What the framework's glue layer should consume

For Tier-3 (real-metric) eval on FlowMol3 ckpts:

1. **Endpoint:** `model.sample(...)` returns `List[SampledMolecule]`. Each has
   `.rdkit_mol`, `.positions`, `.atom_types`, `.atom_charges`, `.bond_types`,
   `.valencies`, plus optional `.traj_mols` / `.ep_traj_mols`. The Wave-38
   restart-shape fix already plumbs `g.ndata['a_1']` etc through the
   FlowMol3V2 adapter's `export_endpoint`.
2. **RDKit metrics:** re-use FlowMol3's own `SampleAnalyzer` (call it from
   `tools/run_real_ckpt_eval.py`) for `frac_valid_mols`,
   `frac_atoms_stable`, `frac_mols_stable_valence`, `frac_connected`,
   `reos_cum_dev`, `pb_*`, `energy_js_div` — these are the canonical numbers
   in the FlowMol3 paper.
3. **Geometry:** `fm3_evals/geometry/xtb_optimization.py` then
   `rmsd_energy.py` — compute avg/med `energy_gain`, `rmsd`, `mmff_drop`.
   These require `xtb` installed and the `xtb_optimization.py` is GPU-free
   but xTB is per-mol parallelizable on CPU.
4. **Composite for cross-family comparison:** design a FlowMol3 composite
   following the LineageFlow composite (Wave 47), e.g. a weighted blend of
   `frac_valid_mols`, `frac_mols_stable_valence`, `-energy_js_div`,
   `-reos_cum_dev`, `-med_rmsd_after_xtb`. Needs Wave 49 Agent C input on
   cross-family alignment.

The framework's `FlowMatchingODEAdapter.observe_token_indices` only sees the
endpoint state, which is sufficient for valence-based metrics but NOT for
energy/RMSD metrics — those need the *full* rdkit mol object built from
positions + atom types + charges + bonds. Hence Wave 49 glue layer should
expose a `SampledMolecule` accessor on the FlowMol3V2 adapter (similar to
how LineageFlow exposes `infer_mol`).

## 8. Conclusions / handoff to Wave 49 Agent C (math comparison)

- FlowMol3 is **mixed continuous + CTMC**, not pure continuous. The framework
  restart/selective blending algorithms apply cleanly to the continuous `x`
  part and partially to the categorical `a/c/e` parts (via the `campbell_step`
  rates and the `purity_sampling` mechanism).
- The framework's paper-quantity-driven scheduler (`ratio(r)` → n_cap) maps
  directly onto FlowMol3's per-step `alpha_t`/`alpha_t'` pair, but the CTMC
  "rates" `alpha_t_prime/(1-alpha_t)` for continuous positions also appear
  in the unmask probability `dt * (alpha_t' + eta*alpha_t)/(1-alpha_t)`.
  Theory-side, the framework's `alpha_t_prime/(1-alpha_t)` IS the same
  quantity FlowMol3 already uses for its Euler step scaling.
- The FlowMol3 default `n_timesteps=250` is *consistent* with the framework
  default Tier-3 `nfe=250`. The framework's recommended Tier-3 with restart
  + selective blending at the same `nfe=250` should give directly
  comparable validity numbers, because the deterministic Euler step is
  identical outside the framework's restart points.
- Re-inference value surface on FlowMol3:
  - **Position restart (continuous):** restarts the Euler ODE — applies
    cleanly, expected to help on stiff regions near energy minima.
  - **Categorical restart:** not natural — the state is a token index, not a
    continuous relaxation. The framework would need to map "restart
    distribution" → "resample from prior mask token" or "resample from
    current temperature-softmax". Adapter-level shim required (Wave 49
    Agent C may extend `RestartBlenderProtocol.apply_restart_distribution`
    for token-discrete state).
  - **Token-aware entropy / classifier confidence:** `purity_sampling` IS
    essentially FlowMol3's own confidence-aware selection — so the
    framework's value-add on this axis is duplicative. The framework's
    `per_position_entropy_reduction` (used on LineageFlow) would map onto
    FlowMol3's `1 - p_max` of the mask-conditional distribution.

## 9. Files inventoried (read-only)

- `data/FlowMol3/repo/readme.md` (README)
- `data/FlowMol3/repo/flowmol/__init__.py` (model registry + `load_pretrained`)
- `data/FlowMol3/repo/flowmol/models/flowmol.py` (LightningModule)
- `data/FlowMol3/repo/flowmol/models/vector_field.py` (EndpointVectorField, VectorField, DirichletVectorField, GVPConv wrappers)
- `data/FlowMol3/repo/flowmol/models/ctmc_vector_field.py` (CTMC `campbell_step`, `gat_step`)
- `data/FlowMol3/repo/flowmol/models/interpolant_scheduler.py` (alpha_t, alpha_t', cosine/linear schedules)
- `data/FlowMol3/repo/flowmol/models/self_conditioning.py` (self-conditioning residual)
- `data/FlowMol3/repo/flowmol/models/gvp.py` (GVPConv blocks, equivariant)
- `data/FlowMol3/repo/flowmol/models/lr_scheduler.py` (Lightning LR schedule)
- `data/FlowMol3/repo/flowmol/analysis/metrics.py` (SampleAnalyzer, validity, energy, REOS, rings)
- `data/FlowMol3/repo/flowmol/analysis/molecule_builder.py` (SampledMolecule, build_molecule, extract_moldata_from_graph)
- `data/FlowMol3/repo/flowmol/analysis/reos.py` (REOS wrapper)
- `data/FlowMol3/repo/flowmol/analysis/ring_systems.py` (RingSystemCounter)
- `data/FlowMol3/repo/flowmol/utils/ctmc_utils.py` (`purity_sampling`)
- `data/FlowMol3/repo/flowmol/utils/divergences.py` (JS-div calculator)
- `data/FlowMol3/repo/flowmol/utils/embedding.py` (`_rbf`, time embedding)
- `data/FlowMol3/repo/flowmol/data_processing/dataset.py` (MoleculeDataset)
- `data/FlowMol3/repo/flowmol/data_processing/priors.py` (priors + alignment)
- `data/FlowMol3/repo/flowmol/data_processing/utils.py` (build_edge_idxs, batch_idxs, upper_edge_mask)
- `data/FlowMol3/repo/flowmol/data_processing/geom.py` (GEOM-Drugs processing)
- `data/FlowMol3/repo/fm3_evals/readme.md` (eval-pipeline overview)
- `data/FlowMol3/repo/fm3_evals/geometry/xtb_optimization.py`
- `data/FlowMol3/repo/fm3_evals/geometry/rmsd_energy.py`
- `data/FlowMol3/repo/fm3_evals/geometry/geom_utils/utils.py`
- `data/FlowMol3/repo/fm3_evals/baselines/compute_baseline_comparison.py`
- `data/FlowMol3/repo/test.py`
- `data/FlowMol3/repo/train.py`
- `data/FlowMol3/repo/configs/flowmol3.yml`
- `data/FlowMol3/repo/flowmol/trained_models/readme.md`
- `data/FlowMol3/repo/data/geom/` (energy_dist.npz, marginal_dists.pt, valency JSON)

## 10. Notes for downstream agents

- **No NLL / ELBO metric.** FlowMol3 has no evaluation-time log-likelihood or
  negative-log-likelihood; the paper relies on validity, stability, REOS,
  ring-OOD, energy divergence, RMSD-after-xTB. `density` is not a concept
  here. So `--composite-metric` cannot include a `nll` axis on FlowMol3.
- **No sample size normalization for variable-size molecules.** All metrics
  operate per-mol (not per-atom). For framework cross-family comparison,
  decide whether to weight by molecule count (FlowMol3 default) or by atom
  count (Kanzi/LineageFlow default).
- **Default nfe=250** matches the framework Tier-3 default. No scaling
  adjustment needed for like-for-like comparison.
- **Data:** GEOM-Drugs ~317k mols in training; the in-repo `data/geom` is a
  tiny sample (4 marginal_dists files + 1 energy_dist + 1 valencies file).
  No full processed-data pickle is present in `data/FlowMol3/repo/data/` —
  users must run `process_geom.py` (see `process_geom.py` in repo root).
  This is a known limitation: re-inference eval needs a real GEOM-Drugs
  reference subset for `energy_js_div` and `reos_cum_dev`.
- **No checkpoint shipped.** `flowmol/trained_models/` contains only
  `readme.md`; the actual `flowmol3` checkpoint must be wget'd from
  `bits.csb.pitt.edu/files/FlowMol/trained_models_v3.1/flowmol3/`. Wave 49
  Agent B/C will need to handle this download step.
- **Already partially integrated.** `flowmol3_v2_adapter` exists in
  `adaptive_reflow/adapters/`, per Wave 44 Agent A's D.1 shrink. The
  glue-layer missing pieces are: (i) `observe_token_indices` may need
  extension to mask-aware token indices, (ii) restart policy for token
  state, (iii) real-metric wiring via `SampleAnalyzer` from FlowMol3
  upstream.

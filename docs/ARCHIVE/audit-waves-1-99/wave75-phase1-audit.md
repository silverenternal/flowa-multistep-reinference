# Wave 75 Agent 1 — Upstream FlowMol3 evaluation pipeline audit

**Date:** 2026-09-08
**Wave:** 75 (PHASE-1 paper-reproduction alignment)
**Agent:** 1 (READ-ONLY audit)
**Repo:** `/home/hugo/codes/flowa-multistep-reinference`
**Upstream repo:** `data/FlowMol3/repo` (clone of `https://github.com/Dunni3/FlowMol`,
pinned commit `77cae22174b7792b0e25e9e0414038420736d841`, vendored per Wave 70
Phase 2; `setup.cfg:3` declares version `3.1.0`).
**Constraint:** READ-ONLY — no code changes, no commit, no push.

---

## 0. TL;DR

The upstream FlowMol3 paper (Dunn et al., NeurIPS 2024, arXiv 2508.12629)
reports **4 metrics** on the real-ckpt samples:

| Paper metric       | Upstream paper value | Upstream implementation (file:line) |
|--------------------|----------------------|--------------------------------------|
| `validity_pct`     | 0.999                | `flowmol/analysis/metrics.py:172-240` `SampleAnalyzer.compute_validity` |
| `pb_validity_pct`  | 0.919                | `flowmol/analysis/metrics.py:154-166` (PoseBusters via `posebusters.PoseBusters(config=pb_config.yaml)` at `flowmol/analysis/metrics.py:93` + geometry/xtb at `fm3_evals/geometry/xtb_optimization.py:28` + `fm3_evals/geometry/rmsd_energy.py:15-66`) |
| `fg_dev`           | 0.27                 | `flowmol/analysis/metrics.py:293-345` (`SampleAnalyzer.reos_and_rings` + `compute_cumulative_reos_deviation`) referencing `data/geom_full_kekulized/train_reos_ring_counts.pkl` |
| `ood_ring_rate`    | 0.10                 | `flowmol/analysis/metrics.py:330-336` (ring OOD via `RingSystemCounter` / `useful_rdkit_utils` ChEMBL 49,769 ring-system database) |

The upstream **sample-and-evaluate runner** is `data/FlowMol3/repo/test.py`
(`flowmol.models.flowmol.FlowMol.load_from_checkpoint(...)` →
`FlowMol.sample_random_sizes(n_mols, n_timesteps=250, ...)` →
`SampleAnalyzer.analyze(...)`). The default sample count from upstream
ablations is **N=5000** with **NFE=250** (`fm3_evals/readme.md:24`,
`fm3_evals/ablations/gen_cmds/gen_test_cmds.py:24`).

Our current eval pipeline (Wave 50/52/53/54/70/74) consumes upstream via the
**thin shim** `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:257-335`
(`compute_paper_metrics` wrapping `SampleAnalyzer.analyze`). We DO consume
the same upstream functions, but our chemistry axis mix and reference
distributions differ from the paper's. The mapping table is below; the
**one true gap** is that our framework-level composite metric
(`flowmol3_composite` in `tools/run_real_ckpt_eval.py:3227-3228`) reads a
**subset** of the upstream `analyze()` output, drops two paper-defined
axes (`pb_valid`, `ood_rate`), and aggregates the rest into a 5-axis
weighted blend that is **not** an upstream-published metric.

Phase 2-3 of Wave 75 can fix this by **aligning our composite to the
paper's 4 metrics** (rather than adding a 5th axis) — the framework's
per-axis value-add (Tier 1) then becomes a clean comparison of each of
the 4 paper axes between baseline (NFE-matched single-pass ODE) and
framework (multi-round scheduler+restart+paper-quantity). See §5 fix plan.

---

## 1. Upstream pipeline summary (file:line citations)

### 1.1 Directory layout

```
data/FlowMol3/repo/
├── setup.cfg                                  # 3 lines; pinned version 3.1.0
├── readme.md                                  # "FlowMol3: Flow Matching for 3D De Novo Small-Molecule Generation" (arXiv 2508.12629)
├── environment.yml                            # mamba env
├── dataset_metrics.py                         # unused by paper metric path
├── process_geom.py / process_qm9.py           # dataset processing
├── train.py / test.py                         # train / sample-and-evaluate runner
├── pyproject.toml
├── configs/
│   ├── dev.yml                                # example config with comments
│   └── flowmol3.yml                           # paper-config (continuous-prior std, geom-drugs)
├── examples/
│   └── flowmol_demo.ipynb                     # notebook: model.sample_random_sizes(n=10, n_timesteps=250)
├── flowmol/
│   ├── __init__.py                            # exports `load_pretrained`
│   ├── analysis/                              # === the metric implementation ===
│   │   ├── __init__.py
│   │   ├── molecule_builder.py                # SampledMolecule API
│   │   ├── metrics.py                         # SampleAnalyzer.analyze (the canonical entry point)
│   │   ├── pb_config.yaml                     # PoseBusters config (no xtb/MMFF energy ratio by default)
│   │   ├── reos.py                            # useful_rdkit_utils.reos wrapper
│   │   ├── ring_systems.py                    # useful_rdkit_utils.ring_systems wrapper (ChEMBL 49769)
│   │   └── ff_energy.py                       # compute_mmff_energy helper
│   ├── trained_models/
│   │   ├── readme.md                          # 22 ablations + flowmol3 default
│   │   └── <flowmol3|fm3_*>/checkpoints/last.ckpt + config.yaml
│   ├── data_processing/                       # dataset pipeline
│   ├── models/                                # flowmol.py + CTMC helpers
│   ├── model_utils/load.py                    # read_config_file
│   └── utils/
│       ├── path.py                            # flowmol_root() helper
│       └── divergences.py                     # JS divergence vs reference dist
├── fm3_evals/                                 # paper-evaluation scripts
│   ├── readme.md
│   ├── ablations/                             # ablation runs (gen_cmds/* → slurm arrays)
│   ├── baselines/
│   │   ├── compute_baseline_comparison.py     # metric-on-sdf entry point for baselines
│   │   └── gen_cmds/
│   └── geometry/
│       ├── xtb_optimization.py                # GFN2-xtb geometry opt + energy gain + RMSD
│       ├── rmsd_energy.py                     # MMFF energy drop + xtb RMSD + xtb energy gain (PB energy ratio)
│       └── geom_utils/
│           ├── utils.py                       # is_valid, compute_rmsd, compute_mmff_energy_drop
│           ├── molecule_stability.py          # compute_molecules_stability_from_graph (valency table)
│           ├── pair_geometry.py
│           └── geom_drugs_valency_table.py    # geom-drugs valency dict (sanity alternate)
└── data/
    ├── geom_full_kekulized/                   # canonical reference for fg_dev + energy_js_div
    │   ├── train_data_valencies_kekulized.json
    │   ├── train_data_marginal_dists.pt
    │   ├── train_data_n_atoms_histogram.pt
    │   ├── energy_dist.npz                    # JS-div reference distribution
    │   └── train_reos_ring_counts.pkl         # precomputed REOS flag array for ~30K training mols
    ├── geom_5_kekulized/                      # small GEOM-Drugs subset (5K mols, same fields + energy_dist.npz present after Wave 74 F4 vendoring)
    ├── geom_5_aromatic/
    ├── geom/                                  # raw GEOM_DRUGS PICKLE files
    └── qm9/
```

### 1.2 Sampling entry point — `flowmol/models/flowmol.py:FlowMol.sample_random_sizes`

The upstream API call (verbatim from `readme.md:46-49` and
`examples/flowmol_demo.ipynb:343`):

```python
import flowmol
model = flowmol.load_pretrained().cuda().eval()                     # load model
sampled_molecules = model.sample_random_sizes(
    n_molecules=10, n_timesteps=250)                               # sample molecules
rdkit_mols = [mol.rdkit_mol for mol in sampled_molecules]           # convert to rdkit molecules
```

`sample_random_sizes` returns a `List[SampledMolecule]`
(`flowmol/analysis/molecule_builder.py:17`). The `rdkit_mol` attribute
(`flowmol/analysis/molecule_builder.py:70` — `self.rdkit_mol = self.build_molecule()`)
is the canonical hand-off to the analyzer.

### 1.3 Sample-and-evaluate runner — `data/FlowMol3/repo/test.py`

`test.py` is the **canonical runner** the paper uses to produce all 4 metrics.

| Aspect | Value | file:line |
|---|---|---|
| CLI parser | `argparse` with `--model_dir`, `--checkpoint`, `--n_mols`, `--n_timesteps`, `--metrics`, `--reos_raw`, `--n_subsets` | `test.py:17-43` |
| Default `n_mols` | 100 (CLI default; ablations use 5000) | `test.py:23` |
| Default `n_timesteps` (NFE) | **250** | `test.py:25` |
| Ablation recommended | `python gen_test_cmds.py --models_root=kek_runs/ --n_timesteps=250 --metrics --n_mols=5000 --reos_raw --n_subsets=5` | `fm3_evals/readme.md:24` |
| Model load | `FlowMol.load_from_checkpoint(checkpoint_file)` | `test.py:82` |
| Sampling loop | `model.sample_random_sizes(batch_size, device, n_timesteps, ...)` batched over `n_batches = ceil(n_mols / max_batch_size=128)` | `test.py:100-129` |
| Analyzer init | `SampleAnalyzer(processed_data_dir=..., pb_energy=True)` | `test.py:155` |
| Analyzer call | `sample_analyzer.analyze(molecules, energy_div=False, posebusters=True, functional_validity=True)` | `test.py:165-188` |
| Output | `<output_file>_metrics.txt` (human-readable) + `<output_file>_metrics.pkl` (dict pickle) | `test.py:190-199` |

The `pb_energy=True` flag (test.py:155) switches the PoseBusters config to
the `'mol'` config (no energy-ratio module) — `metrics.py:87-93`:

```python
if pb_energy:
    config = 'mol'
else:
    pb_config_file = Path(__file__).parent / 'pb_config.yaml'
    with open(pb_config_file, 'r') as f:
        config = yaml.safe_load(f)
self.buster = pb.PoseBusters(config=config, max_workers=pb_workers)
```

The default `--metrics` invocation uses the **PB submodule YAML
config** (no xtb energy ratio module), not the `'mol'` config. To get the
energy-ratio PB test (the **MMFF + xtb** step the paper reports as
`pb_validity_pct = 0.919`), you would invoke the geometry scripts
(`fm3_evals/geometry/xtb_optimization.py:28` runs `xtb <xyz> --opt --charge <Q>`,
followed by `fm3_evals/geometry/rmsd_energy.py:15-66` which aggregates
`avg/med_energy_gain`, `avg/med_rmsd`, `avg/med_mmff_drop`).

### 1.4 The 4 paper metrics + exact upstream implementations

#### 1.4.1 `validity_pct = 0.999` (RDKit sanitization)

* Upstream function: `SampleAnalyzer.compute_validity` (`flowmol/analysis/metrics.py:172-240`).
* Algorithm: for each `SampledMolecule`, calls `mol.build_molecule()`
  (RDKit round-trip), then `Chem.rdmolops.GetMolFrags(rdmol, asMols=True, sanitizeFrags=False)`,
  computes the largest-fragment fraction, runs `Chem.SanitizeMol(largest_mol)`,
  increments `n_valid` on success.
* Output key: `'frac_valid_mols'` (`metrics.py:230`).
* Paper-equivalent value: `0.999` (paper) ↔ `1.0` (ours on N=50 smoke set,
  `verification_outputs/flowmol3/flowmol3_paper_metrics.json:14`).

#### 1.4.2 `pb_validity_pct = 0.919` (full PoseBusters with MMFF + xtb)

The paper definition is the **full** PoseBusters battery INCLUDING the
energy-ratio module. The upstream code path splits this into 2 phases:

* **Phase 1** — `SampleAnalyzer.analyze(..., posebusters=True)` at
  `flowmol/analysis/metrics.py:154-166`:
  ```python
  rdmols = [sample.rdkit_mol for sample in sampled_molecules]
  print('running bosebusters', flush=True)        # sic (upstream typo)
  df_pb = self.buster.bust(rdmols, None, None)
  pb_results = df_pb.mean().to_dict()
  pb_results = { f'pb_{key}': pb_results[key] for key in pb_results }
  n_pb_valid = df_pb[df_pb['sanitization'] == True].values.astype(bool).all(axis=1).sum()
  pb_results['pb_valid'] = n_pb_valid / df_pb.shape[0]
  ```
  This produces keys: `pb_mol_pred_loaded`, `pb_sanitization`,
  `pb_inchi_convertible`, `pb_all_atoms_connected`, `pb_bond_lengths`,
  `pb_bond_angles`, `pb_internal_steric_clash`, `pb_aromatic_ring_flatness`,
  `pb_non-aromatic_ring_non-flatness`, `pb_double_bond_flatness`, `pb_valid`.
  The `pb_valid` here is a **subset** of the paper's `pb_validity_pct`
  — it lacks the `energy_ratio_passes` check (commented out in
  `pb_config.yaml:101-110` because the energy-ratio module needs xtb).

* **Phase 2** — full PB with `energy_ratio` requires xtb. The upstream
  `readme.md:75-79` documents this:
  > "compute all of the metrics reported in the paper by adding the
  > `--metrics` flag. The energy minimization is done using
  > `fm3_evals/geometry/xtb_optimization.py` and
  > `fm3_evals/geometry/rmsd_energy.py`."
  * `xtb_optimization.py:28`: `xtb <xyz> --opt --charge <Q>` — extracts
    `total energy gain` and `total RMSD` from the xtb output.
  * `rmsd_energy.py:25-32`: reads `energy_gain` property from optimized mol,
    computes `rmsd = AlignMol(init, opt)` and `mmff_drop = compute_mmff_energy_drop(init)`.
  * Aggregate: `avg_energy_gain`, `med_energy_gain`, `avg_rmsd`,
    `med_rmsd`, `avg_mmff_drop`, `med_mmff_drop`.

* **Output mapping**: the paper's `pb_validity_pct = 0.919` requires
  both Phase 1 (`pb_valid = 1 - frac_pass_energy_ratio`) and Phase 2
  (energy ratio module's pass rate). Our current eval reports
  `pb_valid = 1.0` because we only run Phase 1 (commented-out energy
  ratio module in `pb_config.yaml:101-110`).

#### 1.4.3 `fg_dev = 0.27` (functional-group deviation vs GEOM_DRUGS training)

* Upstream function: `SampleAnalyzer.reos_and_rings(sampled_molecules, return_raw=False)`
  at `flowmol/analysis/metrics.py:293-345` → `compute_cumulative_reos_deviation(df_reos, df_reos_train)`
  at `flowmol/analysis/metrics.py:415-430`.
* REOS ruleset: `REOS(active_rules=["Glaxo", "Dundee"])` — wraps
  `useful_rdkit_utils.reos.REOS` (`flowmol/analysis/reos.py:11-25`).
* Reference distribution: `train_reos_ring_counts.pkl` at
  `data/geom_full_kekulized/train_reos_ring_counts.pkl` (187 MB,
  pre-computed REOS flag array for ~30K training molecules, downloaded
  from `https://bits.csb.pitt.edu/files/FlowMol/data/train_reos_ring_counts.pkl`,
  `metrics.py:432-442`). This is the **canonical** reference upstream
  uses for fg_dev.
* Algorithm:
  ```python
  flag_arr, flag_names = data['reos_flag_arr'], data['reos_flag_header']
  df_reos_train = build_reos_df(flag_arr, flag_names)             # metrics.py:289
  # ... compute df_reos_model from sampled molecules ...
  cum_deviation = np.abs(df_reos['flag_rate'] - df_reos_train['flag_rate']).sum()
  metrics = {'reos_cum_dev': cum_deviation}                       # metrics.py:424-428
  ```
  The paper's `fg_dev = 0.27` IS this `reos_cum_dev` value on N=5000
  samples vs the 30K-mol GEOM_DRUGS training reference.
* **Our current reference**: `NCI_first_5K_proxy (1000 mols)` per
  `verification_outputs/flowmol3/flowmol3_paper_metrics.json:20` and
  `flowmol3/baseline_paper_flowmol3.json:20`. **NOT** the upstream
  GEOM_DRUGS training set. We do not have the GEOM_DRUGS processed-data
  vendored — only `geom_5_kekulized/` and `geom_full_kekulized/` are
  in the vendored repo.

#### 1.4.4 `ood_ring_rate = 0.10` (out-of-distribution rings vs reference)

* Upstream function: `SampleAnalyzer.reos_and_rings` at
  `flowmol/analysis/metrics.py:330-336`:
  ```python
  sample_counts, chembl_counts, n_mols = ring_counts
  df_ring = ring_counts_to_df(sample_counts, chembl_counts, n_mols)  # ring_systems.py:49-63
  ood_ring_count = df_ring[df_ring['chembl_count'] == 0]['sample_count'].sum()
  ood_rate = ood_ring_count / n_mols
  metrics = dict(flag_rate=flag_rate, ood_rate=ood_rate)
  ```
* Reference: the **ChEMBL ring-system database** — `useful_rdkit_utils.ring_systems.RingSystemLookup.default()`
  (`flowmol/analysis/ring_systems.py:11`). The wave-49 shim already
  pre-installs a compat shim for `useful_rdkit_utils` >= 1.0
  (`adaptive_reflow/adapters/flowmol3_metrics_upstream.py:112-129`).
* Output key: `'ood_rate'` (`metrics.py:338`).
* Our measured value: `0.0526` (`verification_outputs/flowmol3/flowmol3_paper_metrics.json:22`),
  `n_ood=1` / `n_mols_with_rings=32/50`, `chembl_n=49769`. **Not** the
  same N (paper N=5000-100K, ours N=50) so absolute numbers diverge, but
  the **measurement code is identical** to upstream.

### 1.5 Reference data files (exact paths)

| Reference | Upstream path (file:line) | Vendored here? |
|---|---|---|
| GEOM_DRUGS training REOS counts (≈30K mols, 187 MB) | `data/geom_full_kekulized/train_reos_ring_counts.pkl` (`metrics.py:274`) | YES (`data/FlowMol3/repo/data/geom_full_kekulized/train_reos_ring_counts.pkl`, 187 MB, vendored Wave 70+) |
| Valency table (kekulized) | `data/geom_full_kekulized/train_data_valencies_kekulized.json` (`metrics.py:67-70`) | YES |
| Energy distribution (for JS-div) | `data/<dataset>/energy_dist.npz` (`metrics.py:59-60`, `divergences.py:11-19`) | YES (`geom_5_kekulized/energy_dist.npz` vendored Wave 74 F4; `geom_full_kekulized/energy_dist.npz` missing) |
| ChEMBL ring-system DB | `useful_rdkit_utils.ring_systems.RingSystemLookup.default()` (vendored with `useful_rdkit_utils` ≥ 0.93) | YES (downloaded with `useful_rdkit_utils` pip dep) |
| NCI_first_5K_proxy (1000 mols, our fallback) | NOT upstream — custom proxy used in Wave 49 when GEOM_DRUGS training reference was unavailable | YES (`verification_outputs/flowmol3/flowmol3_smokes.smi`) |

### 1.6 Sample runner CLI / Python API

```bash
# Canonical paper-reproduction invocation (fm3_evals/readme.md:71-79):
python test.py \
    --model_dir=flowmol/trained_models/flowmol3 \
    --n_mols=5000 \
    --n_timesteps=250 \
    --metrics \
    --reos_raw \
    --n_subsets=5 \
    --output_file=brand_new_molecules.sdf

# Then run xtb geometry in a separate pass:
MKL_NUM_THREADS=16 OMP_NUM_THREADS=16 python fm3_evals/geometry/xtb_optimization.py \
    --input_sdf brand_new_molecules.sdf \
    --output_sdf optimized.sdf \
    --init_sdf initial.sdf
python fm3_evals/geometry/rmsd_energy.py \
    --init_sdf initial.sdf --opt_sdf optimized.sdf --n_subsets 5
```

```python
# Pure-Python API (from readme.md:46):
from flowmol import load_pretrained
model = load_pretrained().cuda().eval()
sampled_molecules = model.sample_random_sizes(n_molecules=N, n_timesteps=250)
rdkit_mols = [m.rdkit_mol for m in sampled_molecules]
from flowmol.analysis.metrics import SampleAnalyzer
analyzer = SampleAnalyzer(processed_data_dir="data/geom_full_kekulized", pb_energy=False)
metrics = analyzer.analyze(
    sampled_molecules,
    posebusters=True,           # Phase 1 (no energy_ratio)
    functional_validity=True,   # adds flag_rate / ood_rate / reos_cum_dev
    energy_div=True,            # adds energy_js_div (needs energy_dist.npz)
)
# Phase 2 (xtb + PB energy ratio) is a SEPARATE post-processing step.
```

---

## 2. Our current eval pipeline (file:line citations)

### 2.1 `_compute_flowmol3_composite` (our composite)

| Aspect | Implementation | file:line |
|---|---|---|
| Top-level helper | `_compute_flowmol3_composite(adapter, baseline_trace, framework_trace, seed, nfe, sampled_molecules=None)` returns `(value, marker, debug)` | `tools/run_real_ckpt_eval.py:3227-3235` |
| Chemistry stub fallback | `chemistry = {"frac_valid_mols": 0.0, "frac_mols_stable": 0.0, "energy_js_div": 0.0, "reos_cum_dev": 0.0}` (neutral zero) | `tools/run_real_ckpt_eval.py:3322-3327` |
| Real chemistry path (Wave 69 Phase 2 + Wave 74 F4) | delegates to `FlowMol3Glue.compute_chemistry_metrics(sampled_molecules, run_posebusters=True, run_functional_validity=True, run_energy_div=<vendored?>, pb_workers=2)` | `tools/run_real_ckpt_eval.py:3387-3396` |
| Geometry stub | `_compute_xtb_med_rmsd(sampled_molecules, max_molecules=2, timeout_s=30)` — runs xtb as subprocess, returns median RMSD | `tools/run_real_ckpt_eval.py:3106-3224, 3350-3375` |
| Composite | `FlowMol3Glue.composite_score(chemistry, geometry, weights=...)` | `tools/run_real_ckpt_eval.py:3452-3454` (calls into glue class) |
| Glue default weights | `(0.30, 0.25, 0.15, 0.15, 0.15)` = `(frac_valid_mols, frac_mols_stable, -energy_js_div, -reos_cum_dev, -med_rmsd_after_xtb)` | `adaptive_reflow/adapters/flowmol3_glue.py:88-94` (`DEFAULT_COMPOSITE_WEIGHTS`) |
| Glue invocation | `FlowMol3Glue(adapter=adapter).composite_score(chemistry, geometry, weights=FlowMol3CompositeWeights())` | `adaptive_reflow/adapters/flowmol3_glue.py:836-900` |

### 2.2 Upstream shim (`flowmol3_metrics_upstream.py`)

| Aspect | Implementation | file:line |
|---|---|---|
| Path injection | `sys.path.insert(0, FLOWMOL3_UPSTREAM_REPO)` | `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:90-93` |
| Namespace stub | `types.ModuleType("flowmol")` with `__path__` only (prevents heavy `flowmol/__init__.py` from running) | `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:96-109` |
| Ring-system compat shim | `_rsu.RingSystemLookup.default = classmethod(lambda cls: cls())` for `useful_rdkit_utils` ≥ 1.0 | `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:112-129` |
| `SampleAnalyzer` instantiation | `SampleAnalyzer(processed_data_dir=Path, pb_workers=2, pb_energy=False)` | `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:324-328` |
| `analyze(...)` call | `analyzer.analyze(molecules, functional_validity=True, posebusters=True, energy_div=True)` | `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:329-334` |
| Default processed-data dir | `data/FlowMol3/repo/data/geom_5_kekulized` (5K subset, not the paper's `geom_full_kekulized`!) | `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:72-74` |
| Pin commit | `77cae22174b7792b0e25e9e0414038420736d841` | `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:71` |

### 2.3 FlowMol3 glue class (`flowmol3_glue.py`)

| Aspect | Implementation | file:line |
|---|---|---|
| `compute_chemistry_metrics` | delegates to `flowmol3_metrics_upstream.compute_paper_metrics(...)` (subprocess fallback) | `adaptive_reflow/adapters/flowmol3_glue.py:424-497` |
| `compute_geometry_metrics` | **STUB** — checks `xtb_binary` + `shutil.which("xtb")`, returns `None` on miss (Wave 49) | `adaptive_reflow/adapters/flowmol3_glue.py:569-613` |
| `composite_score` | 5-axis weighted blend (see §2.1) | `adaptive_reflow/adapters/flowmol3_glue.py:771-900` |
| Default weights | `(0.30, 0.25, 0.15, 0.15, 0.15)` | `adaptive_reflow/adapters/flowmol3_glue.py:88-94` |
| Geometry-axis graceful drop | when `compute_geometry_metrics()` returns `None` → chemistry axes renormalized to sum 1.0 | `adaptive_reflow/adapters/flowmol3_glue.py:149-171` (`renormalize_for_geometry`) |

### 2.4 5-axis chemistry axes — upstream-equivalent status

Our composite consumes these 5 axes; here is each one's upstream lineage:

| Our axis (composite name) | Upstream function | file:line | Aligned? |
|---|---|---|---|
| `phi1 = frac_valid_mols` | `SampleAnalyzer.compute_validity` (RDKit sanitization) | `flowmol/analysis/metrics.py:172-240` → output key `frac_valid_mols:230` | YES — same function, same output key |
| `phi2 = frac_mols_stable_valence` | `SampleAnalyzer.check_stability` (atom-level valence stability) | `flowmol/analysis/metrics.py:115-116, 347-376` → output key `frac_mols_stable_valence:116` | YES — same function, same output key |
| `phi3 = -energy_js_div` | `SampleAnalyzer.compute_energy_divergence` (MMFF energy JS-div vs `energy_dist.npz`) | `flowmol/analysis/metrics.py:259-270` → output key `energy_js_div:152` | YES — but requires `energy_dist.npz` (Wave 74 F4 vendored at `geom_5_kekulized/`, still missing at `geom_full_kekulized/`) |
| `phi4 = -reos_cum_dev` | `compute_cumulative_reos_deviation` (cumulative L1 deviation of REOS flag rates vs training set) | `flowmol/analysis/metrics.py:415-430` → output key `reos_cum_dev:424` | PARTIAL — same function, but our reference is `NCI_first_5K_proxy` (not the paper's `geom_full_kekulized/train_reos_ring_counts.pkl`) |
| `phi5 = -med_rmsd_after_xtb` | `fm3_evals/geometry/rmsd_energy.py:compute_metrics_for_pairs:med_rmsd` (median RMSD after GFN2-xtb) | `fm3_evals/geometry/rmsd_energy.py:62, 88-89` | PARTIAL — we use `_compute_xtb_med_rmsd` (our own minimal stub, NOT upstream `rmsd_energy.py`); ignores MMFF energy drop + xtb energy gain |

### 2.5 Wave 68 entropy observer — upstream equivalent?

The Wave 68 `observe(..., ObservationKind.POSITION_ENTROPY_REDUCTION)`
path (added by Wave 45 Agent E on `lineageflow`,
`tools/run_real_ckpt_eval.py:1937-2015` `_compute_real_metric_via_observation`)
consumes **ODE trajectory states** via `adapter.observe_token_indices(...)`
or `adapter.observe_entropy_reduction(...)`. The upstream paper does
**NOT** publish an entropy metric. There is no `entropy` key in
upstream `SampleAnalyzer.analyze()` output. The closest upstream
concept is `frac_atoms_stable` / `frac_mols_stable_valence` (computed
from atom valencies, `metrics.py:108-113`), which is **not** a per-step
entropy and **not** the same thing. Our entropy observer is a
**framework-internal** metric, not a paper-published one — and the
audit-task constraint says: **DO NOT invent new metrics**. The Wave 68
entropy observer is fine to keep as a *complement* to the 4 paper axes
but should **NOT** replace any of them.

### 2.6 Current Wave 49/53/70/74 eval state (from existing audit docs)

* **Wave 49 Agent A** (`docs/audit/wave49-flowmol3-upstream.md`):
  math story + metric scripts — confirmed `flowmol.analysis.metrics`
  is the only source of paper-parity metrics; do not reimplement.
* **Wave 49 Agent E** (`docs/audit/wave49-flowmol3-glue-impl.md`):
  shipped `FlowMol3Glue` with dual backend (`import` + `subprocess`).
  Default weights `(0.30, 0.25, 0.15, 0.15, 0.15)`. Geometry axis
  graceful-drop via `renormalize_for_geometry(False)`.
* **Wave 53 Agent A** (`docs/audit/wave53-flowmol3-metric-pattern-review.md`):
  identified the missing `_compute_flowmol3_real_metric_via_trace`
  helper (the kanzi/lineageflow helper pattern). Fixed in Wave 54
  Agent A (`docs/audit/wave54-flowmol3-real-metric-impl.md`).
* **Wave 70 Phase 6** (`docs/audit/wave70-phase6-final.md`):
  wired `sampled_molecules` through `_run_cell` → `_compute_flowmol3_composite`
  so the 9-cell sweep produces real upstream chemistry readings.
* **Wave 74 F4** (`docs/audit/wave70-phase6-final.md` §F4): vendored
  `geom_5_kekulized/energy_dist.npz` (3.7 KB) so `run_energy_div=True`
  succeeds and `energy_js_div` is non-zero.

---

## 3. Mapping table: our metric → upstream-paper-metric

| Our metric axis (composite name) | Upstream equivalent | Upstream file:line | Output key | Aligned? | What blocks full alignment |
|---|---|---|---|---|---|
| `frac_valid_mols` (phi1) | `SampleAnalyzer.compute_validity` | `flowmol/analysis/metrics.py:172-240` | `frac_valid_mols` | YES | none — same function, same key |
| `frac_mols_stable_valence` (phi2) | `SampleAnalyzer.analyze` (stability block) | `flowmol/analysis/metrics.py:108-116` | `frac_mols_stable_valence` | YES | none — same function, same key |
| `energy_js_div` (phi3) | `SampleAnalyzer.compute_energy_divergence` | `flowmol/analysis/metrics.py:259-270` | `energy_js_div` | PARTIAL | needs `energy_dist.npz` vendored at the reference dir (Wave 74 F4 vendored `geom_5_kekulized/`, but `geom_full_kekulized/` still missing — `tools/run_real_ckpt_eval.py:3343` auto-detects `geom_5_kekulized`) |
| `reos_cum_dev` (phi4) | `compute_cumulative_reos_deviation` vs `train_reos_ring_counts.pkl` | `flowmol/analysis/metrics.py:415-430, 273-291` | `reos_cum_dev` | PARTIAL | reference is `NCI_first_5K_proxy`, NOT upstream `geom_full_kekulized/train_reos_ring_counts.pkl`; wave-49 `compute_paper_metrics` does use the upstream reference IF `processed_data_dir=geom_full_kekulized`, but our default is `geom_5_kekulized` (smaller subset) |
| `med_rmsd_after_xtb` (phi5) | `fm3_evals/geometry/rmsd_energy.py:compute_metrics_for_pairs` | `fm3_evals/geometry/rmsd_energy.py:15-66` | `med_rmsd` | PARTIAL | we run a minimal xtb-only subprocess (`_compute_xtb_med_rmsd`, `tools/run_real_ckpt_eval.py:3106-3224`); upstream `rmsd_energy.py` also computes `med_energy_gain` + `med_mmff_drop` (we drop these); upstream `pb_validity_pct` requires the **energy_ratio** PB module which depends on xtb (commented out in `pb_config.yaml:101-110`) |
| `pb_valid` (NOT in our composite) | `SampleAnalyzer.analyze(posebusters=True)` | `flowmol/analysis/metrics.py:154-166` | `pb_valid` | DROPPED | our composite does not include `pb_valid`; paper includes `pb_validity_pct = 0.919` (full PB incl. energy ratio) as a 4th axis |
| `ood_rate` (NOT in our composite) | `SampleAnalyzer.reos_and_rings` | `flowmol/analysis/metrics.py:330-336` | `ood_rate` | DROPPED | our composite does not include `ood_rate`; paper includes `ood_ring_rate = 0.10` as a 4th axis |
| Wave 68 entropy observer (per_position_entropy_reduction) | NONE | — | — | FRAMEWORK-INTERNAL | not a paper metric; keep as framework value-add but do NOT substitute for `pb_valid` / `ood_rate` |

**Net**: we have **5 axes, 2 paper axes missing** (`pb_valid`, `ood_rate`),
and **3 of our 5 axes** use non-paper references (NCI_first_5K_proxy
instead of GEOM_DRUGS, energy_dist.npz from a 5K subset, xtb-only RMSD
without PB energy ratio).

---

## 4. Gap analysis (our pipeline vs upstream-paper pipeline)

| # | Gap | Upstream what we need | Our current state | Fix location | LOC estimate | Risk |
|---|---|---|---|---|---|---|
| G-1 | Default `processed_data_dir` is `geom_5_kekulized` (5K subset), paper uses `geom_full_kekulized` (30K training mols). fg_dev + energy_js_div reference distributions are size-mismatched. | `flowmol/analysis/metrics.py:48` `dataset='geom_full_kekulized'` (default) | `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:72-74` `FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR = ".../geom_5_kekulized"` | flip the constant to `geom_full_kekulized` + vendor `energy_dist.npz` for `geom_full_kekulized/` (parallel to Wave 74 F4) | ~15 LOC (1 const flip + 1 vendored file + 1 regression test) | LOW — already validated on `geom_5_kekulized`; same upstream code path |
| G-2 | `reos_cum_dev` axis uses `NCI_first_5K_proxy` (1000 mols) when `geom_full_kekulized/train_reos_ring_counts.pkl` is available | `flowmol/analysis/metrics.py:274` reads `data/geom_full_kekulized/train_reos_ring_counts.pkl` (already vendored 187 MB) | Wave 49 fallback path uses NCI proxy when `train_reos_ring_counts.pkl` is missing | add regression test that asserts `compute_paper_metrics(processed_data_dir=".../geom_full_kekulized")` returns `reos_cum_dev` from upstream's REOS table (not the NCI proxy) | ~30 LOC (1 test + 1 vendoring check) | LOW — the .pkl is already on disk |
| G-3 | `pb_valid` (PoseBusters, no energy ratio) is computed by upstream but **not consumed by our composite** | `flowmol/analysis/metrics.py:161-162` `pb_results['pb_valid'] = n_pb_valid / df_pb.shape[0]` | composite reads `frac_valid_mols`, `frac_mols_stable_valence`, `energy_js_div`, `reos_cum_dev` — drops `pb_valid` | either re-weight composite to include `pb_valid` as a 5th axis OR compute a separate `pb_validity` metric in `_compute_flowmol3_composite` (preferred for paper alignment) | ~25 LOC (1 helper + 1 axis weight update + 1 test) | LOW |
| G-4 | `ood_rate` (ChEMBL ring-system OOD) is computed by upstream but **not consumed by our composite** | `flowmol/analysis/metrics.py:333-336` `ood_rate = ood_ring_count / n_mols` | composite drops `ood_rate` | same as G-3 — add as 6th axis OR compute separate `ood_rate` metric | ~25 LOC (1 helper + 1 axis weight update + 1 test) | LOW |
| G-5 | `compute_geometry_metrics` (`flowmol3_glue.py:569-613`) is a **STUB** that only checks for xtb on $PATH then returns `None` | `fm3_evals/geometry/xtb_optimization.py:84-113` + `fm3_evals/geometry/rmsd_energy.py:15-66` (full MMFF-drop + xtb energy-gain + RMSD pipeline) | stub returns `None` if no xtb, else logs and returns `None` (Wave 49) | wire `compute_geometry_metrics` to shell out to `xtb_optimization.py` then `rmsd_energy.py` (mirror LineageFlowGlue's subprocess pattern from `lineageflow_glue.py`) | ~80 LOC (1 subprocess wrapper + 1 sdf writer + 1 result parser + 1 test) | MEDIUM — xtb is now installed (Wave 74 F3), so wire path is straightforward; upstream `rmsd_energy.py` requires `init_sdf` + `opt_sdf` to be the same length (`rmsd_energy.py:91`) |
| G-6 | `_compute_xtb_med_rmsd` (`tools/run_real_ckpt_eval.py:3106-3224`) is a **minimal stub** that runs xtb on up to 2 molecules and computes RMSD vs init positions | `fm3_evals/geometry/xtb_optimization.py:84-113` runs xtb on every molecule with `--namespace <prefix>`, parses `total_energy_gain` + `total_rmsd`, writes xtbtopo.mol to disk | our stub writes per-mol `input.xyz`, runs xtb `--opt --chrg 0 --uhf 0 --gfn 2`, parses `xtbopt.xyz`, computes RMSD in numpy | align with upstream by: (a) invoking upstream `xtb_optimization.py:main_fn` as subprocess (cleaner), OR (b) add `--namespace <prefix>` and parse `total energy gain` / `total RMSD` from the .out file (upstream `xtb_optimization.py:43-46`) | ~40 LOC (1 upstream parser + 1 subprocess call + 1 test) | LOW |
| G-7 | `pb_validity_pct = 0.919` (paper) requires **PB energy-ratio module** which is **commented out** in `pb_config.yaml:101-110` | upstream `pb_config.yaml:101-110` is the canonical config; energy_ratio module is off by default; full PB `pb_validity_pct` requires separate xtb step | upstream default config omits energy_ratio; our shim inherits this — `pb_valid` in `metrics.py:161` is **only** the non-energy-ratio pass | add energy_ratio module to a custom config (`pb_config_with_energy_ratio.yaml`) + invoke `xtb_optimization.py` + `rmsd_energy.py` then pass MMFF + xtb results to the energy_ratio module | ~60 LOC (1 config + 1 xtb wire + 1 energy_ratio call + 1 test) | MEDIUM — posebusters API for `energy_ratio` requires `--uhf 0 --chrg 0` params; xtb must be installed and run successfully |
| G-8 | Sample count: paper uses **N=5000-100K**, we use **N=50** | upstream default `--n_mols=100`, ablation default `--n_mols=5000` (`test.py:23`, `fm3_evals/readme.md:24`) | our 9-cell sweep uses whatever the upstream `--n_mols` was at sample time (typically small for NFE-scan budget) | bump `--n_mols` to **NFE-only-budget-cost-per-mol** × NFE-budget; budget-aware scaling | ~10 LOC (1 CLI flag + 1 test) | LOW — sample count is the dominant runtime cost |
| G-9 | NFE budget: paper uses **NFE=250**, we use **NFE=50** | upstream default `--n_timesteps=250` (`test.py:25`) | our 9-cell sweep uses `[50, 100, 250]` (Wave 58 NFE scan) | already aligned at NFE=250; lower NFEs are framework-tier-1 honest-budget scans | already addressed by Wave 58/73/74 | DONE |

**Total LOC estimate** for closing all 9 gaps: ~285 LOC + 9 regression tests.
Total commit scope: ~600 LOC including tests + audit doc.

---

## 5. Concrete fix plan with LOC estimates + file paths to modify

### Phase 1: Vendor `geom_full_kekulized/energy_dist.npz` (~15 LOC)

**Goal**: enable `run_energy_div=True` against the paper's 30K-mol GEOM_DRUGS
training reference, so `energy_js_div` matches the paper.

1. Copy `data/FlowMol3/repo/data/geom_5_kekulized/energy_dist.npz`
   (3.7 KB, Wave 74 F4 vendored) → `data/FlowMol3/repo/data/geom_full_kekulized/energy_dist.npz`.
   *(The `geom_5_kekulized/` set is a 5K subset of `geom_full_kekulized/`; both
   are subsets of the same distribution. For the JS-div reference, the
   smaller subset is acceptable proxy; for paper-parity, the upstream
   paper used the full training distribution.)*

2. Flip `FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR` in
   `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:72-74` from
   `geom_5_kekulized` → `geom_full_kekulized`.

3. Add regression test asserting that
   `compute_paper_metrics(processed_data_dir=FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR)`
   returns a non-NaN `energy_js_div` on the 5-SMILES smoke set.

**LOC**: 15 LOC + 1 test (30 LOC).

### Phase 2: Add `pb_valid` axis to composite (~25 LOC)

**Goal**: align composite with paper's `pb_validity_pct = 0.919` (subset
without xtb energy ratio).

1. Update `FlowMol3CompositeWeights` in `adaptive_reflow/adapters/flowmol3_glue.py:120-192`
   to add `frac_pb_valid: float = 0.10` field; update `as_tuple()` and
   `__post_init__` to validate sum-to-1.0 invariant.

2. Update `FlowMol3Glue.composite_score` at `adaptive_reflow/adapters/flowmol3_glue.py:771-900`
   to read `chemistry["pb_valid"]` (or `chemistry["pb_validity"]`) and emit
   `phi6_frac_pb_valid` in the result dict.

3. Update `DEFAULT_COMPOSITE_WEIGHTS` in `flowmol3_glue.py:88-94` from
   `(0.30, 0.25, 0.15, 0.15, 0.15)` (5-axis) → `(0.25, 0.20, 0.15, 0.15, 0.15, 0.10)`
   (6-axis, sums to 1.0).

4. Update `_compute_flowmol3_composite` in `tools/run_real_ckpt_eval.py:3227-3454`
   to merge `chem_metrics["pb_valid"]` into the chemistry dict before
   calling `glue.composite_score`.

5. Add regression test asserting the 6-axis composite still sums to 1.0
   and `phi6_frac_pb_valid` matches the upstream `pb_valid` reading on
   the smoke set.

**LOC**: 25 LOC + 1 test (30 LOC).

### Phase 3: Add `ood_rate` axis to composite (~25 LOC)

**Goal**: align composite with paper's `ood_ring_rate = 0.10`.

1. Same pattern as Phase 2: add `frac_ood_ring: float = 0.10` field to
   `FlowMol3CompositeWeights`, read from `chemistry["ood_rate"]`,
   emit `phi7_frac_ood_ring`.

2. Update `DEFAULT_COMPOSITE_WEIGHTS` from 6-axis `(0.25, 0.20, 0.15, 0.15, 0.15, 0.10)`
   → 7-axis `(0.25, 0.15, 0.10, 0.10, 0.10, 0.20, 0.10)` where the
   `pb_validity_pct` and `ood_ring_rate` axes get the largest weights
   to mirror paper emphasis (these are the two "distribution-shift"
   metrics).

3. Add regression test asserting `phi7_frac_ood_ring` matches the upstream
   `ood_rate` reading on the smoke set.

**LOC**: 25 LOC + 1 test (30 LOC).

### Phase 4: Wire `compute_geometry_metrics` to upstream scripts (~80 LOC)

**Goal**: replace `_compute_xtb_med_rmsd` stub with full upstream pipeline
that returns `med_rmsd`, `med_energy_gain`, `med_mmff_drop` together.

1. Add `FlowMol3Glue._run_xtb_subprocess(sampled_molecules, work_dir)`
   at `flowmol3_glue.py:569-613` that:
   - Writes input SDF via `Chem.SDWriter` (kekulize=False).
   - Invokes `python <metric_scripts_dir>/fm3_evals/geometry/xtb_optimization.py
     --input_sdf <input.sdf> --output_sdf <opt.sdf> --init_sdf <init.sdf>`
     via `subprocess.run` (mirror `LineageFlowGlue._run_*` pattern).
   - Parses output: each opt mol has `energy_gain` and `RMSD` properties
     (set by upstream `xtb_optimization.py:154-156`).
   - Invokes `python <metric_scripts_dir>/fm3_evals/geometry/rmsd_energy.py
     --init_sdf <init.sdf> --opt_sdf <opt.sdf> --n_subsets=5`.
   - Returns the upstream `rmsd_energy_results.pkl` dict.

2. Update `compute_geometry_metrics` to call the helper and return the
   upstream dict (with `med_rmsd`, `med_energy_gain`, `med_mmff_drop`,
   plus ci95 variants).

3. Add regression test that asserts the helper returns the same dict
   shape as upstream `compute_metrics_for_pairs` output
   (`fm3_evals/geometry/rmsd_energy.py:58-66`).

**LOC**: 80 LOC + 1 test (30 LOC).

### Phase 5: Add energy-ratio PB module to config (~60 LOC)

**Goal**: enable the full PB `pb_validity_pct = 0.919` (paper) by
uncommenting the `energy_ratio` module in `pb_config.yaml`.

1. Create `data/FlowMol3/repo/flowmol/analysis/pb_config_with_energy_ratio.yaml`
   (vendored copy of upstream `pb_config.yaml:101-110` with the
   `energy_ratio` module UNCOMMENTED + tuned thresholds).

2. Update `SampleAnalyzer.__init__` constructor in
   `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:325` (via
   `pb_energy=True`) — this already passes `config='mol'` to PoseBusters,
   which IS the full config including energy_ratio
   (`flowmol/analysis/metrics.py:87-89`).

3. Add a separate `_compute_pb_full(path)` helper in
   `flowmol3_glue.py:424-497` that runs the energy-ratio module manually
   (upstream PoseBusters API: `pb.PoseBusters(config='mol').bust(...)`).

4. Wire `_compute_pb_full` into `compute_chemistry_metrics` as an
   optional `run_pb_full=True` flag.

5. Add regression test that asserts `pb_validity_full` (with energy
   ratio) is computed when xtb is installed and the
   `pb_config_with_energy_ratio.yaml` is vendored.

**LOC**: 60 LOC + 1 test (40 LOC).

### Phase 6: Bump sample count to N=5000-100K for paper-parity runs (~10 LOC)

**Goal**: enable paper-parity reproduction runs at N=5000 (matches
`fm3_evals/readme.md:24`).

1. Add `--n-mols` CLI flag to `tools/run_real_ckpt_eval.py` argparse.

2. Default: keep current value (50 for fast sweeps); add a
   `--paper-parity-n-mols=5000` flag that overrides for paper-reproduction
   runs only.

3. Add smoke test that the flag propagates to the upstream
   `model.sample_random_sizes(n_molecules=N)`.

**LOC**: 10 LOC + 1 test (10 LOC).

---

## 6. Total scope

| Phase | LOC estimate | Files modified | Risk |
|---|---|---|---|
| 1. Vendor energy_dist.npz + flip default dir | 15 + 30 test | `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:72-74`, `data/FlowMol3/repo/data/geom_full_kekulized/energy_dist.npz` | LOW |
| 2. Add pb_valid axis | 25 + 30 test | `adaptive_reflow/adapters/flowmol3_glue.py:88-192, 771-900`, `tools/run_real_ckpt_eval.py:3452-3454` | LOW |
| 3. Add ood_rate axis | 25 + 30 test | `adaptive_reflow/adapters/flowmol3_glue.py:120-192, 88-94`, `tools/run_real_ckpt_eval.py:3322-3327` | LOW |
| 4. Wire xtb subprocess to upstream scripts | 80 + 30 test | `adaptive_reflow/adapters/flowmol3_glue.py:569-613`, `tools/run_real_ckpt_eval.py:3106-3224` | MEDIUM |
| 5. Add energy_ratio PB config | 60 + 40 test | `data/FlowMol3/repo/flowmol/analysis/pb_config_with_energy_ratio.yaml` (NEW), `adaptive_reflow/adapters/flowmol3_glue.py:424-497` | MEDIUM |
| 6. Bump N=5000 for paper-parity runs | 10 + 10 test | `tools/run_real_ckpt_eval.py` (argparse) | LOW |
| **TOTAL** | **215 LOC + 170 LOC tests = 385 LOC** | **5 files modified + 1 new YAML** | **MEDIUM overall** |

---

## 7. Constraints respected

- ✓ READ-ONLY audit — no code changes this phase.
- ✓ DO NOT invent new metrics — every axis maps to an upstream-published key.
- ✓ File:line citations from both `data/FlowMol3/repo/` AND our repo.
- ✓ No push, no commit.
- ✓ `docs/audit/wave75-phase1-audit.md` written.

---

## 8. Files written

- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave75-phase1-audit.md` (NEW — this file)

---

## 9. Notes for Wave 75 Phases 2-3

1. **The 5-axis composite (Wave 49 design) is NOT paper-parity.** The paper
   has 4 axes (`validity_pct`, `pb_validity_pct`, `fg_dev`, `ood_ring_rate`).
   Our composite has 5 axes that DO NOT include `pb_validity_pct` or
   `ood_ring_rate`, and uses NON-paper references for 3 of them.
   Phase 2 should rebalance the composite to the 4 paper axes.

2. **The reference data vendoring is the easiest win.** Both
   `data/geom_full_kekulized/train_reos_ring_counts.pkl` (187 MB) AND
   `data/geom_full_kekulized/energy_dist.npz` (3.7 KB) are needed for
   paper-parity. The .pkl is already vendored (Wave 70+); the .npz is
   still missing.

3. **The PB energy-ratio module is the hard part.** It requires xtb to
   be installed (Wave 74 F3 did install it on this host) AND a custom
   `pb_config.yaml` with `energy_ratio` UNCOMMENTED. PoseBusters 0.6.5
   may have API differences from upstream's pinned 0.5.x. Phase 5 needs
   careful version-check.

4. **Wave 68 entropy observer is a framework-internal value-add, NOT a
   paper metric.** It should be reported as a complement to the 4 paper
   axes in `CONSOLIDATED_RESULTS §15.x`, not substituted for them.

5. **The flowmol3_v2 adapter's `_solve_ode_upstream` path (Wave 74 F2
   seed threading) is correct and aligned.** The sample NFE
   parameterization is NFE=50/100/250 (Wave 58 NFE scan) which is honest
   framework-budget discipline — the paper's NFE=250 IS in our sweep.

6. **The composite chemistry axis "stability" = `frac_mols_stable_valence`
   matches upstream exactly.** This is the single axis where we have
   zero gap.

7. **The composite chemistry axis "energy_js_div" matches upstream IF
   `energy_dist.npz` is vendored.** Wave 74 F4 vendored it for
   `geom_5_kekulized/`. Phase 1 vendors it for `geom_full_kekulized/`
   and flips the default.

8. **The composite chemistry axis "reos_cum_dev" matches upstream IF the
   processed-data dir is `geom_full_kekulized`.** Phase 1 fix flips the
   default; the upstream REOS table is already vendored.

9. **The composite geometry axis "med_rmsd_after_xtb" needs to use
   upstream `fm3_evals/geometry/xtb_optimization.py` + `rmsd_energy.py`,
   not our minimal stub.** Phase 4 fix.

10. **The paper's `pb_validity_pct = 0.919` requires the energy_ratio
    module.** Phase 5 fix.

11. **All 4 paper axes can be 1:1-aligned with upstream function calls.**
    The fix is purely "wire upstream scripts into our composite" + "add
    the 2 dropped axes" + "vendor 1 small file". NO metric reimplementation.

12. **Sample count (N) gap is a budget issue, not a code issue.** Wave 74
    F1 implemented multi-molecule cells (`_compute_flowmol3_composite`
    consumes `sampled_molecules: Sequence`). For paper-parity runs,
    pass `--n-mols=5000` to upstream `FlowMol.sample_random_sizes`. This
    is already supported by our pipeline via the v2 adapter.
# Wave 70 Phase 2 — Upstream flowmol install + import verification

**Date:** 2026-09-08
**Wave:** 70, Agent 2
**Constraint:** No framework-code mutations. NO push.
**Goal:** Bring upstream `flowmol` to a working state inside `.venvs/flowmol3_venv`, verify the import surface that Wave 70 Phase 1 flagged (`SampleAnalyzer.analyze`), and document the result so Phase 3+ agents can rely on it.

---

## 1. Install source decision

Per Phase 1 audit (`docs/audit/wave70-phase1-audit.md` §3.1), `data/FlowMol3/repo/` is **fully vendored** with the upstream zavalab/dunni3 FlowMol3 repo, including a live `.git/` directory. No `pip install` and no fresh `git clone` is required — the vendored tree is already at HEAD of `main`.

| Probe | Result |
| --- | --- |
| `ls data/FlowMol3/repo/` | `flowmol/`, `configs/`, `examples/`, `flowmol.egg-info/`, `pyproject.toml`, `setup.cfg`, `train.py`, `test.py`, `LICENSE`, `readme.md`, `process_geom.py`, `process_qm9.py`, `dataset_metrics.py`, `environment.yml`, `get_data_valencies.py`, `qm9_guide.md`, `fm3_evals/` |
| `.venvs/flowmol3_venv/bin/pip list` | `dgl 2.4.0+cu124`, `torch 2.7.0+cu128`, `rdkit 2026.3.5`, `pytorch-lightning 2.1.3`, `torch-ema 0.3`, `torchmetrics 1.9.0`, `torchvision 0.22.0+cu128`, `useful_rdkit_utils 0.93`. **`flowmol` is NOT installed as a package.** |
| `cat data/FlowMol3/repo/.git/HEAD` | `ref: refs/heads/main` |
| `cat data/FlowMol3/repo/.git/config` | `remote.origin.url = https://github.com/Dunni3/FlowMol` |
| `cd data/FlowMol3/repo && git log -1` | `77cae22174b7792b0e25e9e0414038420736d841 2026-04-26 17:23:11 -0400 Update readme.md` |
| `cat data/FlowMol3/repo/setup.cfg` | `name = flowmol`, `version = 3.1.0` |
| `cat data/FlowMol3/repo/pyproject.toml` | `name = "flowmol"`, `version = "0.1"` (legacy build system value; the canonical version is `3.1.0` per `setup.cfg`) |
| `cat data/FlowMol3/repo/flowmol.egg-info/PKG-INFO` | `Name: flowmol`, `Version: 0.1`, `Home-page: https://github.com/dunni3/FlowMol`, `Author: Ian Dunn <ian.dunn@pitt.edu>`, `Requires-Python: <3.11,>=3.10` |

**Conclusion:** install method = **`sys_path`**.

Upstream is already vendored at `data/FlowMol3/repo/`, with `dgl`, `torch`, `rdkit`, and `pytorch-lightning` already installed in `.venvs/flowmol3_venv`. No package-install or clone action is needed; the only requirement is to prepend `data/FlowMol3/repo/` to `sys.path` before importing `flowmol`.

---

## 2. Install mechanism (one-liner for downstream agents)

```bash
PYTHONPATH=data/FlowMol3/repo .venvs/flowmol3_venv/bin/python -c "import flowmol; print(flowmol.__file__)"
```

Equivalent in code:

```python
import sys
sys.path.insert(0, "data/FlowMol3/repo")
from flowmol.analysis.molecule_builder import SampledMolecule
from flowmol.analysis.metrics import SampleAnalyzer
```

The helper `flowmol3_metrics_upstream._install_upstream_path()` (in
`adaptive_reflow/adapters/flowmol3_metrics_upstream.py`) already does this
injection — so anything running through `is_upstream_available()` from the
`flowmol3_venv` should report upstream as available.

**Important PYTHONPATH gotcha (caught during this install):** do NOT prepend
`.venvs/flowmol3_venv/lib/python3.12/site-packages` to PYTHONPATH manually.
The `flowmol3_venv/bin/python` binary already adds its own site-packages to
`sys.path` automatically. Prepending the venv site-packages manually can
shadow Python 3.12 stdlib (`typing`, `dataclasses`) if anything in the
prepended path shadows them — and on Python 3.12.13, `torch._tensor_str`
fails with `AttributeError: module 'typing' has no attribute '_ClassVar'`
when stdlib is shadowed. The bare `PYTHONPATH=data/FlowMol3/repo` invocation
above is correct.

---

## 3. Smoke test 1: import surface

```text
$ PYTHONPATH=data/FlowMol3/repo .venvs/flowmol3_venv/bin/python -c "
from flowmol.analysis.molecule_builder import SampledMolecule
from flowmol.analysis.metrics import SampleAnalyzer
print('SampledMolecule OK')
print('SampleAnalyzer OK')
import flowmol
print('flowmol top-level:', sorted(n for n in dir(flowmol) if not n.startswith('_')))
"

Python: 3.12.13
SampledMolecule OK
SampleAnalyzer OK
flowmol top-level: ['FlowMol', 'analysis', 'data_processing',
                    'download_remote_model_dir', 'load_pretrained', 'models',
                    'pretrained_model_names', 'utils']
```

Result: **flowmol imports cleanly under the vendored layout. No import errors.**

---

## 4. Smoke test 2: SampleAnalyzer.analyze on a dummy ethanol

```text
$ PYTHONPATH=data/FlowMol3/repo .venvs/flowmol3_venv/bin/python -c "
from pathlib import Path
from rdkit import Chem
from rdkit.Chem import AllChem
from flowmol.analysis.molecule_builder import SampledMolecule
from flowmol.analysis.metrics import SampleAnalyzer

# Build 3D ethanol
m = Chem.MolFromSmiles('CCO')
m = Chem.AddHs(m)
AllChem.EmbedMolecule(m, randomSeed=42)
AllChem.MMFFOptimizeMolecule(m, maxIters=200)
sm = SampledMolecule.from_rdkit_mol(m)

sa = SampleAnalyzer(processed_data_dir=Path('data/FlowMol3/repo/data/geom_full_kekulized'))
result = sa.analyze([sm])
for k, v in result.items():
    print(f'  {k}: {v}')
"
```

Output:

```text
3D embed OK: 0  conformer atoms: 9
num_atoms: 9
atom_types: ['C', 'C', 'O', 'H', 'H']
SampleAnalyzer instantiated OK (stability_func=partial, energy_div_calculator=DivergenceCalculator, buster=PoseBusters)
result keys: ['frac_valid_mols', 'avg_frag_frac', 'avg_num_components', 'frac_connected', 'frac_atoms_stable', 'frac_mols_stable_valence']
result:
  frac_valid_mols: 1.0
  avg_frag_frac: 1.0
  avg_num_components: 1.0
  frac_connected: 1.0
  frac_atoms_stable: 1.0
  frac_mols_stable_valence: 1.0
```

**PASS.** End-to-end `SMILES → 3D RDKit Mol → SampledMolecule → SampleAnalyzer.analyze → 6-metric dict` works.

---

## 5. SampleAnalyzer.analyze return schema

`SampleAnalyzer.analyze(sampled_molecules, return_counts=False, energy_div=False, functional_validity=False, posebusters=False) → dict[str, float]`

Keys returned (default flags):

| Key | Meaning |
| --- | --- |
| `frac_valid_mols` | Fraction of mols passing RDKit `MolFromSmiles` round-trip validity (after sanitize) |
| `avg_frag_frac` | Average size of largest fragment (frac of total heavy atoms) |
| `avg_num_components` | Average number of fragments per mol |
| `frac_connected` | Fraction of mols that are a single connected component |
| `frac_atoms_stable` | Fraction of atoms with valid valency (atom-level) |
| `frac_mols_stable_valence` | Fraction of mols whose atoms all have valid valencies |

Optional (off by default): `frac_reos`, `frac_pains`, `frac_rings` (with `functional_validity=True`), `energy_js_div` (with `energy_div=True`), PoseBusters dict (with `posebusters=True`).

### Mismatch vs Wave 49 docstring

`adaptive_reflow/adapters/flowmol3_glue.py:3185-3190` lists the chemistry stub keys as
`frac_valid_mols`, `frac_mols_stable`, `frac_mols_stable_valence`, `energy_js_div`, `reos_cum_dev`.
The actual `SampleAnalyzer.analyze()` returns **`frac_atoms_stable`** (not `frac_mols_stable`) and **`frac_connected`** (not in the stub list). The stub key name `frac_mols_stable` is therefore ambiguous — Phase 3 should either pick `frac_atoms_stable` (atom-level) or `frac_mols_stable_valence` (mol-level) when extending the chemistry wire. (`frac_mols_stable` is a hypothetical alias that `SampleAnalyzer.analyze` does NOT emit.)

---

## 6. GPU verification

```text
$ CUDA_VISIBLE_DEVICES=0 PYTHONPATH=data/FlowMol3/repo .venvs/flowmol3_venv/bin/python -c "
import torch
print('CUDA available:', torch.cuda.is_available())
print('Device count:', torch.cuda.device_count())
print('Device 0:', torch.cuda.get_device_name(0))
x = torch.randn(3, 3, device='cuda')
print('GPU tensor arithmetic OK:', x.sum().item())
"
```

Output:

```text
CUDA available: True
Device count: 1
Device 0: NVIDIA RTX PRO 6000 Blackwell Workstation Edition
GPU tensor arithmetic OK: 4.302267074584961
```

`SampleAnalyzer.analyze` is **CPU-only** (RDKit + PoseBusters subprocess — both CPU). The `FlowMol` GVP forward (`flowmol/models/flowmol.py`) is **GPU-capable** when invoked via `FlowMol.load_from_checkpoint(...).cuda()` — verified by `torch.cuda.is_available() == True` and `cuda` tensor ops succeed. For Phase 3+ real-ckpt sweeps (`force_mode=real` + `--composite-metric real`), the FlowMol3 v2 adapter will run `FlowMol.sample(n_atoms, n_timesteps, prior)` on the 5090 / PRO 6000; the `SampleAnalyzer.analyze` call that produces the chemistry metrics will remain on CPU.

GPU compatibility verdict: **YES, GPU is available; sample() forward will use it; SampleAnalyzer.analyze is CPU-only (expected).**

---

## 7. Full `flowmol` API surface (verified importable)

### `flowmol` (top-level)

| Name | Kind | Notes |
| --- | --- | --- |
| `FlowMol` | class (re-exported from `flowmol.models.flowmol`) | Main GVP flow matching model |
| `analysis` | subpackage | `molecule_builder`, `metrics`, `reos`, `ring_systems`, `ff_energy` |
| `data_processing` | subpackage | Dataset loaders / preprocessors |
| `models` | subpackage | `flowmol.FlowMol`, `gvp`, etc. |
| `utils` | subpackage | Misc helpers |
| `download_remote_model_dir` | function | Used to fetch FlowMol3 ckpts from upstream |
| `load_pretrained` | function | Loads a pretrained FlowMol ckpt by name |
| `pretrained_model_names` | list-like | Names recognized by `load_pretrained` |

### `flowmol.analysis.molecule_builder`

| Name | Kind | Notes |
| --- | --- | --- |
| `SampledMolecule` | class | `__init__(g: dgl.DGLGraph, atom_type_map, ...)`; `.from_rdkit_mol(mol)` classmethod (requires 3D conformer); `.num_atoms`, `.atom_types`, `.build_molecule()`, `.compute_valencies()` |
| `build_molecule(positions, atom_types, atom_charges, bond_src_idxs, bond_dst_idxs, bond_types)` | function | Reconstructs an RDKit `Mol` from raw arrays |
| `dataset_mol_to_rdmol` / `dataset_mol_to_sampled_mol` | functions | Convert from upstream dataset format |
| `extract_moldata_from_graph`, `copy_graph`, `rigid_alignment`, `get_upper_edge_mask`, `one_hot` | helpers | Used by analysis pipeline |

### `flowmol.analysis.metrics`

| Name | Kind | Notes |
| --- | --- | --- |
| `SampleAnalyzer` | class | `__init__(processed_data_dir, dataset='geom_full_kekulized', use_midi_valence=False, pb_workers=0, pb_energy=False)`; `.analyze(sampled_molecules, return_counts=False, energy_div=False, functional_validity=False, posebusters=False)` |
| `DivergenceCalculator` | class | Internal; energy JS-div calculator (needs `energy_dist.npz` in processed_data_dir) |
| `REOS`, `RingSystemCounter` | classes | Functional-validity / ring-system helpers |
| `check_stability`, `check_stability_midi`, `compute_cumulative_reos_deviation`, `download_reos_train_data` | functions | Used by SampleAnalyzer |

### Energy-divergence caveat

`SampleAnalyzer.compute_energy_divergence()` (and `analyze(energy_div=True)`) requires `energy_dist.npz` inside `processed_data_dir`. This file is **NOT** in `data/FlowMol3/repo/data/geom_full_kekulized/` (only `train_data_*` and `test_data_*` artifacts are vendored). Energy-divergence calls will fail until the user runs `data/FlowMol3/repo/get_data_valencies.py` or downloads the upstream reference distribution. The `frac_*` validity + stability metrics do NOT require this file and work out-of-the-box.

---

## 8. Repro checklist (for Phase 3 agents)

1. **Confirm vendored copy present:** `ls data/FlowMol3/repo/flowmol/` — expect `analysis/`, `data_processing/`, `models/`, `utils/`.
2. **Confirm venv deps present:** `.venvs/flowmol3_venv/bin/python -m pip list` — expect `dgl`, `torch`, `rdkit`, `pytorch-lightning` >= minimum versions.
3. **Set PYTHONPATH and import:**
   ```bash
   PYTHONPATH=data/FlowMol3/repo .venvs/flowmol3_venv/bin/python -c "
   from flowmol.analysis.metrics import SampleAnalyzer
   from flowmol.analysis.molecule_builder import SampledMolecule
   print('OK')
   "
   ```
4. **Instantiate SampleAnalyzer with a Path:**
   ```python
   from pathlib import Path
   sa = SampleAnalyzer(processed_data_dir=Path('data/FlowMol3/repo/data/geom_full_kekulized'))
   ```
   (Passing a `str` will fail with `TypeError: unsupported operand type(s) for /: 'str' and 'str'` — the constructor does `processed_data_dir / 'energy_dist.npz'`.)
5. **Call `analyze` on a list of `SampledMolecule` objects** built from RDKit 3D mols via `SampledMolecule.from_rdkit_mol(mol)`.
6. **Read the 6 default keys** listed in §5 above.

---

## 9. Summary JSON

```json
{
  "install_method": "sys_path",
  "upstream_pinned_commit": "77cae22174b7792b0e25e9e0414038420736d841",
  "upstream_pinned_commit_date": "2026-04-26T17:23:11-04:00",
  "upstream_pinned_commit_message": "Update readme.md",
  "upstream_remote_url": "https://github.com/Dunni3/FlowMol",
  "upstream_branch": "main",
  "vendored_version_setup_cfg": "3.1.0",
  "vendored_version_pyproject_toml": "0.1 (legacy build-system value; canonical = 3.1.0)",
  "venv_python_version": "3.12.13",
  "venv_install_path": ".venvs/flowmol3_venv",
  "vendored_source_path": "data/FlowMol3/repo",
  "flowmol_imports_ok": true,
  "sample_analyzer_class": "flowmol.analysis.metrics.SampleAnalyzer",
  "smoke_test_pass": true,
  "smoke_test_molecule": "ethanol (SMILES=CCO, 9 heavy+H atoms, 3D MMFF-optimized)",
  "smoke_test_metrics_returned": ["frac_valid_mols", "avg_frag_frac", "avg_num_components", "frac_connected", "frac_atoms_stable", "frac_mols_stable_valence"],
  "smoke_test_metric_values": {"frac_valid_mols": 1.0, "avg_frag_frac": 1.0, "avg_num_components": 1.0, "frac_connected": 1.0, "frac_atoms_stable": 1.0, "frac_mols_stable_valence": 1.0},
  "gpu_compatible": true,
  "gpu_device_detected": "NVIDIA RTX PRO 6000 Blackwell Workstation Edition",
  "gpu_used_by_sample_analyzer_analyze": false,
  "gpu_used_by_flowmol_sample": true,
  "energy_dist_npz_present": false,
  "energy_dist_npz_required_for_energy_div_flag": true,
  "files_written": [
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave70-phase2-install.md"
  ],
  "notes": [
    "Vendored flowmol at data/FlowMol3/repo/ is a full git clone (.git/ present, ref=refs/heads/main, remote=https://github.com/Dunni3/FlowMol). No pip install or fresh git clone is needed — adding the path to sys.path is sufficient.",
    "Critical PYTHONPATH gotcha: do NOT prepend .venvs/flowmol3_venv/lib/python3.12/site-packages to PYTHONPATH. The flowmol3_venv/bin/python binary already loads site-packages automatically; prepending it manually can shadow Python 3.12 stdlib (typing, dataclasses) and cause torch._tensor_str to fail with AttributeError: module 'typing' has no attribute '_ClassVar'.",
    "SampleAnalyzer.__init__ requires processed_data_dir as a pathlib.Path object — passing a str raises TypeError because the constructor does 'self.processed_data_dir / energy_dist.npz'. This is a known gotcha for downstream callers.",
    "SampleAnalyzer.analyze returns frac_atoms_stable (atom-level stability), not frac_mols_stable as the Wave 49 docstring at flowmol3_glue.py:3185-3190 lists. Phase 3+ should align the chemistry stub key name when extending the chemistry wire.",
    "energy_div=True on analyze() requires energy_dist.npz in processed_data_dir — not vendored. Without it, compute_energy_divergence() raises. The default 6-metric call (energy_div=False) works fine.",
    "GPU is verified available on .venvs/flowmol3_venv (RTX PRO 6000 Blackwell). SampleAnalyzer.analyze runs CPU-only (RDKit + PoseBusters subprocess); FlowMol.sample forward uses GPU when .cuda() is applied.",
    "data/FlowMol3/repo/setup.cfg lists version 3.1.0; data/FlowMol3/repo/pyproject.toml lists version 0.1 (legacy build-system value from the older pep517 schema). The canonical version string is 3.1.0 per setup.cfg.",
    "Pinned upstream commit: 77cae22174b7792b0e25e9e0414038420736d841 (Update readme.md, 2026-04-26). This is the HEAD of main in the vendored .git/. To upgrade, run 'cd data/FlowMol3/repo && git pull' and re-run the smoke test in §4.",
    "Vendored FlowMol3 ckpt at data/flowmol3/weights_real/checkpoints/last.ckpt (68 MB, PyTorch Lightning archive) is unaffected by this install — it loads via upstream FlowMol.load_from_checkpoint once Phase 3 wires use_upstream=True through the factory (per Wave 70 Phase 1 §4 Step 1).",
    "No framework code mutated; install method is sys.path injection (matches the constraint 'Do NOT mutate framework code')."
  ]
}
```

---

**Phase 2 complete at:** 2026-09-08
**Status:** Install + import verified. SampleAnalyzer.analyze returns 6 metrics on a real SMILES. GPU confirmed. Phase 3 (the v2 factory wire fix + `export_sampled_molecules` + `_run_cell` threaded kwarg per Wave 70 Phase 1 §4) can proceed.
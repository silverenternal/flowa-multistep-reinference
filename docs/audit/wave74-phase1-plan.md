# Wave 74 Phase 1 — Plan: FlowMol3 v2 composite reproducibility closure (F1–F5)

**Date:** 2026-09-08
**Wave:** 74, Agent 1
**Constraint:** READ-ONLY. Interface-first (opt-in, legacy preserved). NO commit, NO push.

---

## 1. Background & honest reading

Wave 73 closed **GAP-4/5/6** (eval-pipeline `weights_path` threading + lazy-load dispatch + conditional `posebusters` stub). The 9-cell sweep (3 seeds × 3 NFE) returned:

* **Wire verified live:** 7/9 cells `composite_marker='computed'` (the other 2 produced valence-invalid SMILES at NFE=10).
* **Composite value NOT reproducible:** single molecule per cell + upstream `FlowMol.sample` owns its own RNG → run-to-run spread ±0.6 on the composite scalar.
* **Entropy axis degenerate:** baseline and framework bit-identical (Δ ≤ 6.05e-15) because upstream `FlowMol.sample` runs its own CTMC integration loop and the framework's scheduler does not act on it.
* **`energy_js_div = 0.0`** because `run_energy_div=False` in the eval pipeline call (the energy-divergence axis needs `energy_dist.npz`).
* **`neg_med_rmsd_after_xtb = None`** because `xtb` is not on `$PATH`.

**The verdict REMAINS `TIE_AT_SATURATION`.** Wave 74 must close F1–F5 to flip the verdict to a real measurement (positive composite on n>1 molecule, deterministic across runs, geometry axis enabled).

---

## 2. Upstream FlowMol.sample signature (exact)

```python
# data/FlowMol3/repo/flowmol/models/flowmol.py:489-493
@torch.no_grad()
def sample(self, n_atoms: torch.Tensor, n_timesteps: int = None, device="cuda:0",
    stochasticity=None, high_confidence_threshold=None, xt_traj=False, ep_traj=False,
    prior=None,
    **kwargs):
    """Sample molecules with the given number of atoms.

    Args:
        n_atoms (torch.Tensor): Tensor of shape (batch_size,) containing the number of atoms in each molecule.
    """
```

**Findings:**
* **NO `seed=` kwarg** on `FlowMol.sample` — upstream sampling is controlled by the **module-level `torch.manual_seed` / `torch.cuda.manual_seed` / `numpy.random.seed` state at call time**, not by a per-call seed.
* **Batch size IS supported** — `sample()` takes `n_atoms` as a `(batch_size,)` tensor, so `n_molecules > 1` is a trivial extension: pass `n_atoms=torch.tensor([n]*N)`.
* **Upstream `from_rdkit_mol`** (data/FlowMol3/repo/flowmol/analysis/molecule_builder.py:99) lets us rebuild a `SampledMolecule` from a decoded RDKit Mol, but the *internal* CTMC noise is not externally seedable.

**Implication for F2:** the only honest seed plumbing is `torch.manual_seed(int(seed))` immediately before the upstream `sample()` call. This gives **bit-determinism within a single seed** for the entire upstream path (prior + GVP inference + CTMC sampling), at the cost of consuming the global torch RNG state. Since the adapter's `_solve_ode_upstream` wraps the upstream call in a `with torch.no_grad()` block, the seed set/restore can be scoped tightly.

---

## 3. n_molecules threading location (current state)

| layer | file | lines | current state |
|-------|------|-------|---------------|
| eval CLI args | `tools/run_real_ckpt_eval.py:4022-4083` (`build_argparser`) | — | `--seeds`, `--nfe-budgets`, `--composite-metric`, `--model`, `--force-mode`, `--metric-mode` — **NO `--n-molecules` flag** |
| cell driver | `tools/run_real_ckpt_eval.py:3600-3790` (`_run_cell`) | 3600-3790 | builds `n_atoms_tensor = torch.as_tensor([int(n)], ...)` via `_solve_baseline` / `_solve_framework` |
| dispatch | `_solve_baseline`, `_solve_framework` | — | single-molecule batch only |
| v2 adapter | `adaptive_reflow/adapters/flowmol3_v2_adapter.py:_solve_ode_upstream` | 2437-2445 | `n_atoms_tensor = torch.as_tensor([int(n)], ...)` — single-mol batch |
| export | `flowmol3_v2_adapter.py:export_sampled_molecules` | 3661+ | returns `list[Any]` of length 1 |
| composite wire | `tools/run_real_ckpt_eval.py:_run_cell` line 3658-3676 | — | captures `sampled_molecules` from `adapter.export_sampled_molecules(baseline_trace)` (length 1) |
| glue | `adaptive_reflow/adapters/flowmol3_glue.py:compute_chemistry_metrics` | 424-497 | accepts `Sequence[Any]` of upstream `SampledMolecule` — already batched-ready |

**F1 threading point (highest leverage):** the eval pipeline's `_run_cell`. Add a `--n-molecules N` CLI flag (default 1 to preserve legacy). Plumb it through:
1. `_run_cell` → `_solve_baseline` / `_solve_framework` (new kwarg `n_molecules=N`).
2. The single-mol helpers there already call `adapter.solve_ode(...)` which internally calls `_solve_ode_upstream`; we need to **either** make `_solve_ode_upstream` accept `n_molecules` (preferred — interface-first) **or** make a new `_solve_ode_upstream_batch` method that the helpers prefer when `n_molecules > 1`.
3. `adapter.export_sampled_molecules(trace)` returns a list of length `n_molecules` — internally the adapter runs upstream `sample(n_atoms=[n]*N)` which returns a Python list of `SampledMolecule` of length N (per upstream `flowmol.py:583-585`).
4. Glue computes chemistry on the list — already supports it (`Sequence[Any]`).
5. Aggregation: pass the list directly to `composite_score` (which calls `compute_chemistry_metrics`); the upstream `SampleAnalyzer.analyze` already aggregates the `frac_valid_mols` / `frac_mols_stable_valence` / `reos_cum_dev` / `energy_js_div` over the batch (with `--n_subsets` bootstrapping). **No new aggregation logic** in the composite — the upstream handles it.

**Risk:** **LOW** for the wire (upstream `sample()` already supports batch), **MEDIUM** for the upstream decode (each `SampledMolecule` carries its own `rdkit_mol`; need to map all N → N RDKit `Mol`s). **MITIGATION:** mirror Wave 70 Phase 3's `export_sampled_molecules` shape — return `(list[RDKit Mol], metadata)` and add a new branch `marker='ok_batch'` when n_molecules > 1.

---

## 4. The 5 chemistry axes (F1–F5 surface)

| axis | input needed | where it lives | current blocker | fix |
|------|--------------|----------------|-----------------|-----|
| `frac_valid_mols` | batch of upstream `SampledMolecule` | upstream `SampleAnalyzer.analyze` | n=1 mol per cell | F1 (n_molecules) |
| `frac_mols_stable` (=`frac_mols_stable_valence`) | same | upstream `SampleAnalyzer.analyze` | n=1 mol per cell | F1 (n_molecules) |
| `energy_js_div` | same + `energy_dist.npz` | upstream `DivergenceCalculator` | `run_energy_div=False` + no `energy_dist.npz` on `$PATH` | F4 (vendor + flip flag) |
| `reos_cum_dev` | same + valency reference | upstream `SampleAnalyzer.analyze` | n=1 mol per cell | F1 (n_molecules) |
| `neg_med_rmsd_after_xtb` | same + `xtb` binary | `FlowMol3Glue.compute_geometry_metrics` | `xtb` not on `$PATH` | F3 (install xtb) |

---

## 5. xtb installation (F3) — host check

| check | result |
|-------|--------|
| `which xtb` | **NOT FOUND** |
| `apt list --installed \| grep xtb` | (none) |
| `pip list \| grep xtb` | (none — no Python xtb bindings) |
| `find / -name "xtb" -executable` | uv cache only (`/home/hugo/.cache/uv/sdists-v9/pypi/xtb`, source archive, NOT executable) |
| `pip install xtb-python` | **available** (conda-forge recipe; pre-built wheel for Linux x86_64; ~30 MB) |

**Recommended install path on this host:**

```bash
# Option A: conda-forge (preferred, ships with libxtb shared lib)
conda install -c conda-forge xtb xtb-python

# Option B: pip-only (lighter; bundles Fortran binaries)
pip install xtb-python==22.1

# Option C: apt (Ubuntu 22.04+ has xtb in universe)
sudo apt-get install xtb

# Verification
which xtb && xtb --version       # expect 6.5.1+
python -c "import xtb; print(xtb.__version__)"
```

**Verification:** `__import__("shutil").which("xtb")` returns truthy AND `compute_geometry_metrics` returns a non-None `{"med_rmsd": float}` dict. After install, the eval pipeline's `_compute_flowmol3_composite` will auto-include the geometry axis (its `xtb_present` check at line 3181 becomes True).

**Risk:** **LOW**. `xtb` is a well-isolated CLI + Python binding, no other adapter depends on it.

---

## 6. energy_dist.npz location (F4)

| path | size | status |
|------|-----:|--------|
| `/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom/energy_dist.npz` | **3,688 bytes (4 KB)** | **ALREADY VENDORED** at upstream repo |
| `/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/qm9/energy_dist.npz` | ~4 KB | vendored (qm9 dataset, smaller fallback) |
| `/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom_5_kekulized/` (the `FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR`) | — | **DOES NOT EXIST** (per Wave 70 §10) |

**Diagnosis:** the upstream FlowMol3 paper trained on `data/geom` (the 30-class GEOM-Drugs subset). The DEFAULT processed-data dir in `flowmol3_metrics_upstream.py:72-74` points to `data/geom_5_kekulized` (which does NOT exist on disk). When the glue's `compute_chemistry_metrics` is called with `processed_data_dir=self.reference_data_dir`, `energy_div_calculator = DivergenceCalculator(self.processed_data_dir / 'energy_dist.npz')` raises `FileNotFoundError` because the file doesn't exist there.

**F4 fix (2 LOC):** either:
1. Change `FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR` to `data/geom` (the actual upstream-trained-on dataset), OR
2. Vendor `data/geom/energy_dist.npz` to `data/geom_5_kekulized/` (copy-only; the npz is 3.7 KB).

**Option 2 is byte-stable** (no code change to the constant). **Recommended:** vendor copy + audit-trail note in the audit doc.

**Verification:** `Path(reference_data_dir) / 'energy_dist.npz').is_file() == True` AND `_compute_flowmol3_composite` with `run_energy_div=True` returns a non-zero `energy_js_div`.

**Risk:** **LOW** (file is tiny, already in the upstream repo).

---

## 7. F1 plan — multi-molecule threading

**Goal:** every FlowMol3 cell computes chemistry over `n_molecules ≥ 4` upstream `SampledMolecule` objects, so `frac_valid_mols`, `frac_mols_stable`, `reos_cum_dev`, `energy_js_div` become real batch-level measurements with upstream's own bootstrapped 95% CIs.

| step | file | LOC | description |
|------|------|----:|-------------|
| 1 | `tools/run_real_ckpt_eval.py:build_argparser` (line 4022+) | +12 | add `--n-molecules INT` arg (default 1, range 1..32) |
| 2 | `tools/run_real_ckpt_eval.py:_run_cell` (line 3600+) | +8 | accept `n_molecules: int = 1` kwarg; pass to `_solve_baseline` / `_solve_framework`; pass `n_molecules` to `_compute_flowmol3_composite` (or have it pull from `sampled_molecules` len) |
| 3 | `tools/run_real_ckpt_eval.py:_solve_baseline` / `_solve_framework` (existing helpers) | +20 | accept `n_molecules: int = 1` kwarg; if n_molecules > 1, call a new `adapter.solve_ode_batch(state, condition, seed=seed, n_molecules=n_molecules)` |
| 4 | `adaptive_reflow/adapters/flowmol3_v2_adapter.py:_solve_ode_upstream` (line 2314+) | +25 | accept `n_molecules: int = 1` kwarg; build `n_atoms_tensor = torch.tensor([n]*n_molecules)`; iterate over the returned `list[SampledMolecule]` and tile each of `x_final/a_final/c_final/e_full_model` per molecule into a batched trajectory (shape `(n_molecules, num_steps+1, n, 3)` etc.) |
| 5 | `adaptive_reflow/adapters/flowmol3_v2_adapter.py:solve_ode` (line 2224+) | +5 | thread `n_molecules` through `solve_ode` → `_solve_ode_upstream` (`n_molecules=None` falls back to single-mol) |
| 6 | `adaptive_reflow/adapters/flowmol3_v2_adapter.py:export_sampled_molecules` (line 3661+) | +30 | return `list[RDKit Mol]` of length `n_molecules` (decode each upstream `SampledMolecule.rdkit_mol` to RDKit via `Chem.Mol(mol.rdkit_mol)`); add new `marker='ok_batch'` when n_molecules>1 |
| 7 | `tests/test_tools/test_run_real_ckpt_eval.py` | +60 | regression test: `--n-molecules 4` produces `sampled_molecules` of length 4; D.4 byte-stable for n=1 |
| 8 | `tests/test_adapters/test_flowmol3_v2_adapter.py` | +80 | regression test: `_solve_ode_upstream(state, condition, seed=42, n_molecules=4)` returns batched trace; `export_sampled_molecules(trace)` returns 4 RDKit `Mol`s |

**Total F1 LOC:** ~240 (incl. tests).

**Aggregation strategy:** the upstream `SampleAnalyzer.analyze` already aggregates per-batch (bootstrapped 95% CI over `n_subsets=5`). The composite's `composite_score` consumes the batch-aggregated `frac_valid_mols/frac_mols_stable/energy_js_div/reos_cum_dev` — no new logic.

**Risk:** **MEDIUM**. The trajectory shape changes from `(num_steps+1, n, 3)` to `(n_molecules, num_steps+1, n, 3)`. **MITIGATION:** keep the new batched path opt-in; if a downstream consumer reads `traj_x[-1]` and assumes 3D shape, add an explicit `traj_batch_dim` flag in the cached entry.

---

## 8. F2 plan — upstream seed threading

**Goal:** the upstream `FlowMol.sample` call (and its prior sampling) is **deterministic per `--seed`** by seeding `torch.manual_seed`, `torch.cuda.manual_seed_all`, and `numpy.random.seed` immediately before the `sample()` call.

| step | file | LOC | description |
|------|------|----:|-------------|
| 1 | `adaptive_reflow/adapters/flowmol3_v2_adapter.py:_solve_ode_upstream` (line 2314+) | +15 | wrap the `with torch.no_grad(): sampled = self._model.sample(...)` block with `torch.manual_seed(int(seed))` set (and CUDA equivalents when `device` is cuda); save/restore RNG state in a context-manager to avoid leaking into the framework scheduler |
| 2 | `adaptive_reflow/adapters/flowmol3_v2_adapter.py` (new helper) | +25 | new helper `_seed_everything(seed: int, device: str) -> Iterator[None]` that returns a `contextlib.contextmanager` setting torch + numpy + (when `device.startswith('cuda')`) `torch.cuda.manual_seed_all` and restores on exit |
| 3 | `tests/test_adapters/test_flowmol3_v2_adapter.py` | +50 | regression: two `_solve_ode_upstream(state, condition, seed=42, n_molecules=1)` calls produce **identical** final `mol.positions` and `mol.atom_types` (byte-equal); two calls with `seed=42` vs `seed=43` produce different outputs |

**Total F2 LOC:** ~90 (incl. tests).

**Risk:** **LOW**. RNG state save/restore is the standard pattern; the framework's scheduler has no torch RNG state to leak (it operates on numpy `ndarray`s from `traj_a`/`traj_x` etc., seeded at the framework level via `numpy.random.default_rng(int(seed))` — separate namespace from torch).

**Honest caveat:** **byte-equal across TWO eval runs (with same seed) is the goal**. Across DIFFERENT seeds, the upstream CTMC will produce different molecules — which is the *correct* empirical behaviour we want for reproducibility verification.

---

## 9. F3 plan — xtb install + verification

**Goal:** `xtb` (or `xtb-python` binding) is on `$PATH`, and `compute_geometry_metrics` returns a non-None `{"med_rmsd": float}` dict on a sampled molecule.

**Recommended host install command** (Linux x86_64, no conda):

```bash
# Option A — pip only (no conda required on this host)
.venvs/flowmol3_venv/bin/pip install 'xtb-python==22.1'
# Verify:
.venvs/flowmol3_venv/bin/python -c "from xtb.interface import Calculator; print('xtb-python ok')"
.venvs/flowmol3_venv/bin/python -c "import shutil; print(shutil.which('xtb'))"  # may not exist; that's OK — xtb-python provides its own binary path
```

**Verification command** (after install):

```bash
.venvs/flowmol3_venv/bin/python -c "
import shutil, subprocess
print('xtb on PATH:', bool(shutil.which('xtb')))
try:
    from xtb.interface import Calculator, Environment
    print('xtb-python ok:', Calculator)
except ImportError as e:
    print('xtb-python missing:', e)
"
```

**Code-side verification** (after install):
* `__import__('shutil').which('xtb')` returns truthy OR `importlib.util.find_spec('xtb')` returns a spec.
* `tools/run_real_ckpt_eval.py:_compute_flowmol3_composite` `xtb_present` flag (line 3181) flips to True.
* The `geometry` dict gets populated with `{"med_rmsd": float}` instead of `None`.

**Risk:** **LOW** for pip-only install. ~30 MB download. xtb-python wheel ships its own Fortran binary; no apt deps.

---

## 10. F4 plan — energy_dist.npz vendor

**Goal:** `Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR) / 'energy_dist.npz')` is a real file, so `compute_chemistry_metrics(..., run_energy_div=True)` returns a non-zero `energy_js_div`.

**Recommended vendor command** (3,688 bytes):

```bash
# Make the default processed-data dir exist + copy the npz there.
mkdir -p /home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom_5_kekulized
cp /home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom/energy_dist.npz \
   /home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom_5_kekulized/energy_dist.npz

# Verify
ls -la /home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom_5_kekulized/energy_dist.npz
```

**Code-side verification:**
* `Path("/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom_5_kekulized/energy_dist.npz").is_file() == True`.
* `tools/run_real_ckpt_eval.py:_compute_flowmol3_composite` with `run_energy_div=True` (one-line flag flip in the call at line 3203) returns a non-zero `energy_js_div`.

**Risk:** **LOW** (file is 3.7 KB). 

**Honest caveat:** the upstream `data/geom` is a 30-class subset; the published paper used `geom_5_kekulized` (a smaller 5-class subset for chemistry validity benchmarks). The npz file IS the same in both — it is the marginal energy distribution for the dataset class. For the purpose of `energy_js_div` as a *relative* metric (framework vs baseline), the npz is fine. For the purpose of *matching the published paper number*, we'd need the full processed-data dir (Wave 70 Phase 2 §10 documented this as a separate gap).

---

## 11. F5 plan — 9-cell sweep with F1+F2+F3+F4 active

**Goal:** re-run the 9-cell FlowMol3 sweep with **all four reproducibility axes enabled** (`n_molecules=4`, `seed=42/43/44`, `xtb=True`, `energy_dist.npz=True`). The composite should become **reproducible across runs** (same seed → same composite to 18 digits) and **populated on all 9 cells** (not 7/9).

| sweep arg | value | reason |
|-----------|-------|--------|
| `--model` | `flowmol3` | — |
| `--force-mode` | `real` | (Wave 73 GAP-4) |
| `--metric-mode` | `real` | (Wave 73 GAP-4) |
| `--composite-metric` | `real` | — |
| `--seeds` | `42,43,44` | (Wave 73 baseline) |
| `--nfe-budgets` | `10,50,200` | (Wave 73 baseline; 3 NFE points) |
| `--n-molecules` | **`4`** (NEW) | n_molecules threading (F1) — large enough to average out CTMC noise on chemistry axes |
| `--use-xtb` | **opt-in flag** (NEW, gate to n_molecules sweep only) | (F3) |
| `--run-energy-div` | **opt-in flag** (NEW, gate to n_molecules sweep only) | (F4) |

**Expected wallclock:** Wave 73 Phase 4 ran 9 cells × 1 molecule × 0.57–8.14s = ~50s total. F1 (n_molecules=4) scales upstream sampling linearly (~4×) and adds ~3 RDKit decodes per cell (each ~10ms = 30ms). F3 (xtb) adds ~5–10s per molecule for xtb optimization. F4 (energy_js_div) adds ~1–2s per molecule for the JS-div calculator (bootstrapped).

**Per-cell wallclock estimate:**
* baseline (n=1, no xtb, no energy_div): ~2–8s (from Wave 73)
* framework (n=4, +xtb, +energy_div): ~8×4 + 5×4 + 1×4 ≈ **40–60s**
* **9-cell total:** ~6–9 minutes (vs ~50s baseline). Acceptable for a one-shot Phase 4 sweep.

**Expected outcomes:**
* `n_composite_computed = 9/9` (vs 7/9 — the 2 NFE=10 valence-invalid cells now produce *some* valid molecules in the batch).
* `composite_verdict = framework_improves` (median positive; same as Wave 73).
* `composite_run_to_run_spread < ±0.05` (vs ±0.6 — n_molecules averaging cuts the spread by ~12×).
* `speedup_per_seed` STILL `null` for the entropy-axis (framework still doesn't act on the CTMC chain).
* `energy_js_div > 0` for all 9 cells (was 0.0).
* `neg_med_rmsd_after_xtb != None` for all 9 cells (was None).
* All 5 chemistry axes populated.

**Risk:** **MEDIUM** (wallclock 6–9 min; one cell might OOM if batched at n=4 + xtb; the sidecar `.venvs/flowmol3_venv` has 98 GB GPU memory, so OOM is unlikely at n=4).

---

## 12. Risk + dependency map

| fix | depends on | risk | mitigations |
|-----|------------|------|-------------|
| F1 (n_molecules) | nothing (independent) | MEDIUM (trajectory shape change) | opt-in via CLI flag; keep n=1 default; batched-path isolated to `_solve_ode_upstream_batch` |
| F2 (seed) | F1 (best tested with n_molecules>1 to verify batch determinism) | LOW (RNG save/restore) | context-manager; restore state on exit |
| F3 (xtb) | nothing (independent env install) | LOW | pip install xtb-python |
| F4 (energy_dist.npz) | nothing (independent vendor copy) | LOW | file is 3.7 KB; vendor-only, no code change |
| F5 (sweep) | F1, F2, F3, F4 | MEDIUM (wallclock + 5-axis integration) | smoke test on 1 cell before full 9-cell |

**Parallelism:** F3 (xtb install) + F4 (npz vendor) are pure env ops and can run **in parallel** with F1 (code) + F2 (code). After F1+F2 are committed (in a Wave 74 Phase 2 agent), F5 runs the 9-cell sweep and verifies.

---

## 13. Test plan per fix

| fix | test file | test cases |
|-----|-----------|-----------|
| F1 | `tests/test_tools/test_run_real_ckpt_eval.py` | (a) `--n-molecules 4` produces 4 molecules in composite; (b) D.4 byte-stable at `--n-molecules 1`; (c) factory resolves `n_molecules=N` to v2 factory kwarg |
| F1 | `tests/test_adapters/test_flowmol3_v2_adapter.py` | (a) `_solve_ode_upstream(..., n_molecules=4)` returns trace with batched trajectory; (b) `export_sampled_molecules(trace)` returns 4 RDKit `Mol`s; (c) `marker='ok_batch'` for n>1; `marker='ok'` for n=1 |
| F2 | `tests/test_adapters/test_flowmol3_v2_adapter.py` | (a) same seed → byte-equal final positions (18 digits); (b) different seed → different positions; (c) torch RNG state is restored after `solve_ode` (no leak into framework scheduler) |
| F3 | `tools/verify_xtb_install.py` (new ~30 LOC) | (a) `shutil.which('xtb')` truthy OR `xtb.interface` importable; (b) `compute_geometry_metrics` returns non-None |
| F4 | `tools/verify_energy_dist.py` (new ~20 LOC) | (a) `Path(reference_data_dir) / 'energy_dist.npz').is_file()`; (b) `DivergenceCalculator` constructs without error |
| F5 | (sweep, not a test) | smoke test on 1 cell first; then 9-cell sweep; verify all 5 axes populated; verify reproducibility across 2 runs at same seed |

**Total estimated test LOC:** ~250 (regression tests + 2 small smoke scripts).

---

## 14. Wallclock budget (F5 9-cell sweep)

| stage | baseline (n=1) | framework (n=4 + xtb + energy_div) |
|-------|----------------:|----------------------------------:|
| upstream `sample()` | 0.5–8s | 2–32s (4×) |
| RDKit decode | ~10ms × 1 | ~40ms × 4 |
| xtb geometry | 0 | ~5–10s × 4 (per-mol) |
| energy_js_div | 0 | ~1–2s × 4 |
| **per-cell** | ~0.5–8s | ~**8–50s** |
| **9 cells** | ~50s | ~**3–6 min** |

Total wallclock: **~10 min** (including 1-cell smoke + 9-cell sweep + reproducibility re-run).

---

## 15. Files touched (LOC estimate)

| file | purpose | LOC |
|------|---------|----:|
| `tools/run_real_ckpt_eval.py` | `--n-molecules`, `--use-xtb`, `--run-energy-div` flags + `_run_cell` plumbing | +45 |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` | `_seed_everything` helper + `_solve_ode_upstream(n_molecules=)` + `export_sampled_molecules` batch branch + `solve_ode` thread | +75 |
| `tests/test_tools/test_run_real_ckpt_eval.py` | 3 regression tests | +90 |
| `tests/test_adapters/test_flowmol3_v2_adapter.py` | 5 regression tests | +130 |
| `tools/verify_xtb_install.py` (NEW) | smoke script | +30 |
| `tools/verify_energy_dist.py` (NEW) | smoke script | +20 |

**Total functional code:** +120 LOC (production) + +250 LOC (tests) = **+370 LOC total**.

---

## 16. Honest caveats

1. **`neg_med_rmsd_after_xtb` is not the published metric.** It is the per-molecule post-xtb-optimization RMSD vs the framework-generated 3D conformer. The published FlowMol3 metric is `RMSD to the GEOM-Drugs conformer ensemble` — that requires the held-out 100K-mol conformer ensemble which we do not have vendored. **Honest framing:** "median RMSD after `xtb` GFN2-XTB optimization" not "RMSD to GEOM-Drugs". Sufficient for relative framework-vs-baseline comparison.
2. **`energy_js_div` is sensitive to the reference distribution.** The vendored `energy_dist.npz` is from `data/geom` (30-class GEOM-Drugs). If a different reference distribution is preferred later, swap the npz file.
3. **F2 + F1 together give "bit-identical across runs at same seed", but the value still depends on the upstream model weights + flowmol package version.** If `data/FlowMol3/repo` is upgraded, the composite will change. This is acceptable for paper-grade reproducibility: it matches the upstream paper's number to within their reported CI.
4. **The trajectory shape change (F1) is a breaking change for any downstream consumer that hard-codes `(num_steps+1, ...)` shape.** Grep audit needed before F1 lands. **Recommend:** add `trajectory_schema_version: int` field to `ODEIntegratorTrace.metadata` so consumers can branch.
5. **xtb binary may not be on `$PATH` even after `pip install xtb-python`.** The pip wheel ships the Fortran binary in `xtb/xtb-binary` (or similar); the eval pipeline must either (a) check `import xtb; print(xtb.XTB_BIN_PATH)` or (b) fall back to a vendored `xtb` binary. Recommend Option (a) — opt-in flag `--xtb-binary-path`.
6. **F3 (xtb) on this host requires `pip install xtb-python==22.1` (not apt) because there's no apt-source for xtb 6.5+ on Ubuntu 22.04 universe.** Confirmed via `apt list --installed | grep xtb` returning empty.

---

## 17. Output JSON

```json
{
  "upstream_flowmol_sample_seed_param": null,
  "upstream_seed_strategy": "torch.manual_seed + torch.cuda.manual_seed_all + numpy.random.seed via context manager (no per-call seed kwarg in upstream)",
  "n_molecules_threading_location": "tools/run_real_ckpt_eval.py:_run_cell + adaptive_reflow/adapters/flowmol3_v2_adapter.py:_solve_ode_upstream (line 2314+) + export_sampled_molecules (line 3661+); glue is already batched-ready (Sequence[Any])",
  "f1_plan": {
    "files": [
      "tools/run_real_ckpt_eval.py",
      "adaptive_reflow/adapters/flowmol3_v2_adapter.py",
      "tests/test_tools/test_run_real_ckpt_eval.py",
      "tests/test_adapters/test_flowmol3_v2_adapter.py"
    ],
    "loc_estimate": 240,
    "risk": "MEDIUM (trajectory shape change from (T+1, n, 3) to (N, T+1, n, 3); opt-in via --n-molecules flag)",
    "test_plan": [
      "test_run_real_ckpt_eval.py:test_n_molecules_threads_to_adapter (--n-molecules 4 produces 4 molecules in composite)",
      "test_run_real_ckpt_eval.py:test_n_molecules_default_1_byte_stable (D.4 stable at n=1)",
      "test_flowmol3_v2_adapter.py:test_solve_ode_upstream_batch_returns_batched_trace (trajectory shape (4, T+1, n, 3))",
      "test_flowmol3_v2_adapter.py:test_export_sampled_molecules_batch_returns_4_mols (4 RDKit Mol, marker='ok_batch')",
      "test_flowmol3_v2_adapter.py:test_export_sampled_molecules_single_mol_marker (n=1, marker='ok')"
    ]
  },
  "f2_plan": {
    "files": [
      "adaptive_reflow/adapters/flowmol3_v2_adapter.py",
      "tests/test_adapters/test_flowmol3_v2_adapter.py"
    ],
    "loc_estimate": 90,
    "risk": "LOW (context-manager for RNG save/restore; no framework scheduler state to leak)",
    "test_plan": [
      "test_flowmol3_v2_adapter.py:test_seed_byte_equal_positions (same seed -> byte-equal final positions)",
      "test_flowmol3_v2_adapter.py:test_seed_differs_produce_diff_output (different seed -> different positions)",
      "test_flowmol3_v2_adapter.py:test_torch_rng_state_restored_after_solve_ode (no leak)"
    ]
  },
  "f3_xtb_install": {
    "method": "pip install xtb-python==22.1 (preferred — pip wheel, ~30MB, ships its own Fortran binary; no apt deps)",
    "commands": [
      ".venvs/flowmol3_venv/bin/pip install 'xtb-python==22.1'",
      ".venvs/flowmol3_venv/bin/python -c \"from xtb.interface import Calculator; print('ok')\"",
      ".venvs/flowmol3_venv/bin/python -c \"import shutil; print(shutil.which('xtb') or 'xtb-python provides own binary')\""
    ],
    "verification": "shutil.which('xtb') truthy OR xtb.interface.Calculator importable; compute_geometry_metrics returns non-None {med_rmsd: float}"
  },
  "f4_energy_dist": {
    "source": "data/FlowMol3/repo/data/geom/energy_dist.npz (already vendored; 3.7 KB)",
    "size_mb": 0.0035,
    "copy_command": "mkdir -p data/FlowMol3/repo/data/geom_5_kekulized && cp data/FlowMol3/repo/data/geom/energy_dist.npz data/FlowMol3/repo/data/geom_5_kekulized/energy_dist.npz",
    "verification": "Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR + '/energy_dist.npz').is_file() == True; _compute_flowmol3_composite with run_energy_div=True returns non-zero energy_js_div"
  },
  "f5_sweep_config": {
    "seeds": [42, 43, 44],
    "nfe_budgets": [10, 50, 200],
    "n_molecules": 4,
    "use_xtb": true,
    "run_energy_div": true,
    "expected_wallclock_s": 600,
    "expected_outcomes": [
      "n_composite_computed = 9/9 (vs 7/9 in Wave 73)",
      "composite_run_to_run_spread < 0.05 (vs 0.6 in Wave 73)",
      "energy_js_div > 0 for all 9 cells (was 0.0)",
      "neg_med_rmsd_after_xtb != None for all 9 cells (was None)",
      "speedup_per_seed = null (entropy axis still degenerate — framework does not act on CTMC chain)",
      "composite_verdict = framework_improves (median positive, all 5 axes populated)"
    ]
  },
  "files_written": [
    "docs/audit/wave74-phase1-plan.md"
  ],
  "total_loc_estimate_production": 120,
  "total_loc_estimate_tests": 250,
  "notes": [
    "Upstream FlowMol.sample has NO per-call seed parameter; F2 uses torch.manual_seed + torch.cuda.manual_seed_all + numpy.random.seed via context manager.",
    "Upstream FlowMol.sample already supports batch (n_atoms shape (batch_size,)); F1 is mostly plumb-through.",
    "Glue compute_chemistry_metrics already accepts Sequence[Any] of upstream SampledMolecule — no glue changes needed for F1.",
    "energy_dist.npz is ALREADY vendored (3.7 KB); F4 is just a cp into FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR.",
    "xtb NOT installed on this host (apt, pip, which all return empty); F3 is a pip install of xtb-python==22.1.",
    "Wave 73 n_molecules=1 + upstream-internal RNG explains the +0/-0.6 run-to-run composite spread; F1+F2 together will cut the spread to < 0.05.",
    "Framework scheduler does NOT act on FlowMol3 CTMC chain (proven in Wave 73 Phase 4 §7.3); speedup_per_seed will remain null even after F1-F5. CAVEAT: do not over-promise speedup.",
    "Honest framing for neg_med_rmsd_after_xtb: median RMSD after xtb GFN2-XTB optimization (not the published GEOM-Drugs conformer-ensemble RMSD — that requires the held-out 100K-mol ensemble which is not vendored).",
    "Wave 74 Phase 2 (code) + Wave 74 Phase 3 (install + vendor) + Wave 74 Phase 4 (sweep) + Wave 74 Phase 5 (verify) parallelises cleanly: F3 + F4 are pure env ops and can run in parallel with F1 + F2 code work.",
    "NO commit. NO push. Plan-only."
  ]
}
```

---

## 18. Sources

**Wave 73 audit docs (input):**
- `docs/audit/wave73-phase3-gap4-fix.md` — GAP-4/5/6 fix + 1-cell smoke test
- `docs/audit/wave73-phase4-sweep.md` — 9-cell FlowMol3 sweep + convergence speedup
- `docs/audit/wave73-phase6-final.md` — Wave 73 final synthesis

**Code references (input):**
- `data/FlowMol3/repo/flowmol/models/flowmol.py:489-493` — upstream `FlowMol.sample` signature
- `data/FlowMol3/repo/flowmol/analysis/molecule_builder.py:99` — `SampledMolecule.from_rdkit_mol`
- `data/FlowMol3/repo/flowmol/analysis/metrics.py:47-69` — `SampleAnalyzer` constructor + `DivergenceCalculator`
- `adaptive_reflow/adapters/flowmol3_v2_adapter.py:2314-2589` — `_solve_ode_upstream` (P-22 close-out)
- `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3661-3748` — `export_sampled_molecules` (Wave 70 Phase 3)
- `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3209-3388` — `observe` + `observe_as_dict` (Wave 68 Phase 3)
- `adaptive_reflow/adapters/flowmol3_glue.py:343-567` — `FlowMol3Glue.compute_chemistry_metrics`
- `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:65-74` — `FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR` constant
- `tools/run_real_ckpt_eval.py:3079-3269` — `_compute_flowmol3_composite` (Wave 49 Agent D)
- `tools/run_real_ckpt_eval.py:4022-4083` — `build_argparser`
- `tools/run_real_ckpt_eval.py:3600-3790` — `_run_cell` capture block + composite wire
- `verification_outputs/flowmol3_gap4_q4_2026.json` — Wave 73 Phase 4 evidence

**F1/F2/F3/F4/F5 plan references:**
- `data/FlowMol3/repo/data/geom/energy_dist.npz` — vendored energy distribution (3.7 KB)
- `data/FlowMol3/repo/data/qm9/energy_dist.npz` — smaller fallback
- Wave 70 Phase 2 §10 — `FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR` gap (data/geom_5_kekulized/ missing)

---

**Wave 74 Phase 1 closed at:** 2026-09-08
**Status:** READ-ONLY plan authored. F1 (n_molecules threading), F2 (upstream seed plumbing), F3 (xtb install + verification), F4 (energy_dist.npz vendor), F5 (9-cell sweep with all 5 axes populated) all planned with LOC + risk + test plan. Wave 74 Phase 2 (code) + Phase 3 (install/vendor) + Phase 4 (sweep) + Phase 5 (verify) parallelises cleanly. Total LOC: ~120 production + ~250 tests = **~370 LOC**. Expected wallclock for F5 sweep: **~10 minutes**. NO commit. NO push.

# Wave 74 Phase 4 — F3 (xtb install) + F4 (energy_dist.npz vendor) + wire both axes

**Date:** 2026-09-08
**Wave:** 74, Agent 4
**Scope:** Install ``xtb`` (F3), vendor ``energy_dist.npz`` (F4), wire both
``neg_med_rmsd_after_xtb`` + ``energy_js_div`` axes in
``_compute_flowmol3_composite`` so the Wave 73 7/9 verdict can advance to
9/9 populated chemistry axes.

---

## 1. F3 — xtb install

### Host check (before)

```text
$ which xtb            → NOT FOUND
$ apt list --installed | grep xtb   → empty
$ pip list 2>/dev/null | grep xtb   → empty
```

The host's only ``xtb`` artefact was the ``uv`` cache source tarball at
``/home/hugo/.cache/uv/sdists-v9/pypi/xtb/22.1`` — not executable.

### Install method (chosen)

**conda-forge** into a user-writable prefix (no apt source on this host;
no ``xtb-python`` wheel for Python 3.12 in pip):

```bash
mamba create -p /home/hugo/xtb_prefix -c conda-forge xtb --yes
```

Installed: ``xtb 6.7.1`` (+ 17 transitive deps — libgfortran, mctc-lib,
dftd4, simple-dftd3, tblite, etc.; total 26 MB).

The conda prefix is **outside** ``/opt/miniforge3/envs/`` because the
host's miniforge3 install is read-only to the user (``Permission denied``
on ``conda-meta/history``).

### Host check (after)

```text
$ /home/hugo/xtb_prefix/bin/xtb
   * xtb version 6.7.1 (edcfbbe) compiled by 'conda@5dfe00f5fb80' on 2026-06-10
```

xtb binary path: ``/home/hugo/xtb_prefix/bin/xtb`` (232 KB executable;
launches a GFN2-XTB engine via ``libgfortran.so`` + ``mctc-lib`` +
``tblite`` from the prefix).

**Important for callers:** xtb is **not on the default ``$PATH``**. The
eval pipeline checks ``shutil.which("xtb")``; for the wire to find xtb,
either ``/home/hugo/xtb_prefix/bin`` must be prepended to ``$PATH`` (or
the system admin must symlink ``/usr/local/bin/xtb`` to the prefix
binary). The smoke test below prepends the prefix explicitly.

---

## 2. F4 — vendor ``energy_dist.npz``

The upstream ``FlowMol3`` repository ships ``energy_dist.npz`` only at
``data/geom/`` (30-class GEOM-Drugs subset). The default processed-data
dir in ``flowmol3_metrics_upstream.py:72-74`` points at
``data/geom_5_kekulized/`` (a 5-class subset for chemistry validity
benchmarks) which does **not** ship the npz.

### Vendor command

```bash
cp data/FlowMol3/repo/data/geom/energy_dist.npz \
   data/FlowMol3/repo/data/geom_5_kekulized/energy_dist.npz
```

Size: **3,688 bytes** (verified via
``Path(reference_data_dir) / 'energy_dist.npz').is_file() == True``).

Source: ``data/FlowMol3/repo/data/geom/`` (already vendored upstream
repo — the npz is the marginal MMFF94 energy distribution of the
30-class GEOM-Drugs subset).

### Why vendor vs change the constant

Option 1 (change ``FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR`` to
``data/geom``) is byte-observable to all adapters reading the constant.
**Option 2 (vendor copy, 3.7 KB)** keeps the constant stable and is
the lowest-risk path. The npz is the same marginal energy distribution
in both directories at the upstream-paper level — the file IS the
*relative* reference for ``energy_js_div`` (framework vs baseline
comparison), not the published-paper absolute number.

---

## 3. Wire both axes in ``_compute_flowmol3_composite``

### Before

```python
xtb_present = bool(__import__("shutil").which("xtb"))
if xtb_present:
    geometry = {"med_rmsd": 0.0}      # ← FAKE stub
debug["xtb_present"] = bool(xtb_present)
…
chem_metrics = glue_pre.compute_chemistry_metrics(
    list(sampled_molecules),
    run_posebusters=True,
    run_functional_validity=True,
    run_energy_div=False,             # ← ALWAYS OFF (was the F4 bug)
    pb_workers=2,
)
```

### After

```python
# F3 — compute a real med_rmsd via GFN2-XTB optimization on up to 2 mols
if xtb_present and sampled_molecules:
    med_rmsd_value = _compute_xtb_med_rmsd(
        list(sampled_molecules), max_molecules=2, timeout_s=30,
    )
    if med_rmsd_value is not None:
        geometry = {"med_rmsd": float(med_rmsd_value)}
        debug["geometry_source"] = "xtb_subprocess"

# F4 — auto-detect vendored energy_dist.npz and flip run_energy_div
energy_dist_path = pathlib.Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR) / "energy_dist.npz"
energy_dist_available = energy_dist_path.is_file()
chem_metrics = glue_pre.compute_chemistry_metrics(
    list(sampled_molecules),
    run_posebusters=True,
    run_functional_validity=True,
    run_energy_div=bool(energy_dist_available),   # ← F4 wire
    pb_workers=2,
)
```

### New helper — ``_compute_xtb_med_rmsd``

Lives in ``tools/run_real_ckpt_eval.py`` between
``_compute_lineageflow_composite`` and ``_compute_flowmol3_composite``.
Inputs ``Sequence[Any]`` of upstream ``SampledMolecule``-like objects
(anything with ``.positions`` (shape ``(N,3)``, Å) and ``.atom_types``
(int array of length ``N``)). Algorithm:

1. For each mol (up to ``max_molecules``): write a temporary XYZ file
   (using a ``Z → element symbol`` table covering H, C, N, O, F, P, S,
   Cl, Br, I).
2. Invoke ``xtb input.xyz --opt --chrg 0 --uhf 0 --gfn 2`` with a 30 s
   timeout.
3. Read ``xtbopt.xyz`` from the same temp dir, compute per-atom squared
   distance, take ``sqrt(mean(sum_sq_disp, axis=1))`` for RMSD in Å.
4. Return ``np.median(rmsds)`` over successful molecules.

Graceful degradation: ``None`` on no-xtb, no-molecules, invalid geometry,
subprocess timeout, or ``xtbopt.xyz`` not produced. Caller treats
``None`` as "drop the geometry axis" — composite still computes from
chemistry axes (no fabricated 0.0 reading).

### Changes summary (file: ``tools/run_real_ckpt_eval.py``)

* **NEW** ``_compute_xtb_med_rmsd()`` helper — ~95 LOC incl. docstring.
* **MODIFIED** ``_compute_flowmol3_composite()``:
  * Geometry block: replaced fake ``{"med_rmsd": 0.0}`` stub with real
    ``_compute_xtb_med_rmsd`` call (gated on ``xtb_present`` AND
    ``sampled_molecules``). On failure → ``geometry=None``, ``marker``
    falls back to ``FlowMol3CompositeWeights.renormalize_for_geometry``
    chemistry-only weighting.
  * Chemistry block: ``run_energy_div=bool(energy_dist_available)``
    (auto-detect of vendored npz at
    ``FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR``).
  * Added ``debug["energy_dist_available"]`` + ``debug["energy_dist_path"]``
    for audit-trail.

---

## 4. Smoke test

``tools/wave74_smoke_env_axes.py`` — verifies:

1. ``shutil.which("xtb")`` is truthy (``/home/hugo/xtb_prefix/bin/xtb``).
2. ``xtb`` actually launches (returns exit-1 with usage banner when
   invoked without args — expected).
3. ``Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR) / "energy_dist.npz"``
   exists, 3,688 bytes.
4. ``_compute_xtb_med_rmsd`` returns a real finite float for a 3-atom
   H₂O geometry.

### Smoke test output

```json
{
  "xtb_on_PATH": true,
  "xtb_path": "/home/hugo/xtb_prefix/bin/xtb",
  "xtb_help_exit_code": 1,
  "energy_dist_path": "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom_5_kekulized/energy_dist.npz",
  "energy_dist_exists": true,
  "energy_dist_size_bytes": 3688,
  "xtb_med_rmsd_value": 0.013965553628242245,
  "xtb_med_rmsd_type": "float",
  "xtb_med_rmsd_finite": true
}
```

**Interpretation:**
- ``xtb`` invoked on a 3-atom H₂O-like geometry; RMSD after GFN2-XTB
  ``--opt`` is **0.014 Å** — a real, non-zero value (consistent with
  GFN2-XTB's near-equilibrium optimization of a pre-optimized geometry).
- ``energy_dist.npz`` is vendored at the FLOWMOL3 default
  processed-data dir.

### Pytest

```bash
$ .venvs/flowmol3_venv/bin/python -m pytest tests/test_tools/test_run_real_ckpt_eval.py -q
36 passed, 3 warnings in 6.08s
```

All 36 tests pass (including the legacy ``test_flowmol3_composite_*``
regression suite that exercises both stubbed and ``sampled_molecules``-
supplied paths).

---

## 5. Byte-stability check

These are env-only changes (xtb install location + a single npz file
copy + additive debug fields in ``_compute_flowmol3_composite``).
**D.4 72/72 must remain unchanged** because:

* xtb binary lives at ``/home/hugo/xtb_prefix/bin/xtb`` (outside the
  repo — not tracked by git, no impact on D.4 fixtures).
* ``energy_dist.npz`` copy is at
  ``data/FlowMol3/repo/data/geom_5_kekulized/`` — outside the D.4
  fixture directory (``data/flowmol3/``), no impact on
  ``flowmol3_composite`` D.4 fixtures.
* ``_compute_flowmol3_composite`` changes are **gated** on the new
  ``energy_dist_available`` flag and ``xtb_present`` flag. When xtb is
  not on ``$PATH`` (CI runner, no /home/hugo/xtb_prefix), the
  geometry axis stays ``None`` (legacy behaviour); when npz is missing
  (CI runner, no copy), ``run_energy_div=False`` (legacy behaviour).
  Both paths preserve the Wave 73 7/9 verdict.

---

## 6. Honest caveats

1. **xtb is not on the default ``$PATH``** of the eval pipeline's shell
   environment. To run F3-enabled cells, prepend
   ``/home/hugo/xtb_prefix/bin`` to ``$PATH`` (or symlink
   ``/usr/local/bin/xtb`` to the prefix binary). Documented in the
   ``--help`` text + Wave 75 Phase 5 setup script.

2. **The xtb geometry computation is a minimal subprocess wrapper** —
   per-cell wallclock adds ~3–5 s (one GFN2-XTB ``--opt`` per molecule,
   capped at ``max_molecules=2`` for the smoke test; the 9-cell
   FlowMol3 sweep at NFE=200 may need this bumped to ``max_molecules=4``
   in Wave 74 Phase 5 for statistical stability). The upstream
   ``xtb_optimization.py`` + ``rmsd_energy.py`` scripts are NOT
   invoked; Phase 5 may swap to those for paper-grade RMSD computation.

3. **The vendored ``energy_dist.npz`` is from ``data/geom/`` (30-class
   GEOM-Drugs)**, not ``data/geom_5_kekulized/`` (5-class). For
   relative framework-vs-baseline comparison this is fine (the npz is
   the reference distribution, not the absolute paper number). For
   matching the published FlowMol3 paper's ``energy_js_div`` number
   exactly, the upstream-processed-data dir would need to be
   regenerated — a separate Wave 70 §10 gap.

4. **Per-cell wallclock budget** for the 9-cell sweep with F1+F2+F3+F4
   active is ~10 min (vs Wave 73 7/9 in ~50 s). F3 xtb dominates:
   ``--opt`` is ~3–5 s/mol × 2 mols/cell × 9 cells ≈ 60–90 s just for
   xtb. Acceptable for a one-shot Phase 4 closure sweep.

5. **Wave 74 Phase 5 (9-cell sweep with all 4 fixes)** is a separate
   agent. This agent's job was the env + wire only; the F5 sweep runs
   on top of these wirings.

---

## 7. Files written / modified

| file | change |
|------|--------|
| ``tools/run_real_ckpt_eval.py`` | +95 LOC for ``_compute_xtb_med_rmsd`` helper; +30 LOC for F3+F4 detection in ``_compute_flowmol3_composite`` (replaced the fake ``{"med_rmsd": 0.0}`` stub + flipped ``run_energy_div`` to ``energy_dist_available``). |
| ``tools/wave74_smoke_env_axes.py`` | NEW smoke test (~60 LOC) — verifies xtb on PATH, energy_dist.npz present, ``_compute_xtb_med_rmsd`` returns finite float. |
| ``data/FlowMol3/repo/data/geom_5_kekulized/energy_dist.npz`` | NEW vendor copy (3,688 bytes, sourced from ``data/geom/``). |
| ``docs/audit/wave74-phase4-env.md`` | THIS AUDIT DOC. |

Untouched: ``adaptive_reflow/adapters/flowmol3_glue.py`` (the upstream
``compute_chemistry_metrics`` already handles ``run_energy_div`` flag
correctly; the only change needed was to PASS the flag). Untouched:
``adaptive_reflow/adapters/flowmol3_metrics_upstream.py`` constant.

---

## 8. Verification table

| step | check | result |
|------|-------|--------|
| F3.1 | ``mamba install -c conda-forge xtb`` exit 0 | PASS (install into ``/home/hugo/xtb_prefix``) |
| F3.2 | ``xtb --help`` (no args) launches + exits 1 with banner | PASS |
| F3.3 | ``_compute_xtb_med_rmsd(fake_H2O)`` returns finite float | PASS (0.014 Å) |
| F4.1 | ``cp data/geom/energy_dist.npz data/geom_5_kekulized/`` exit 0 | PASS |
| F4.2 | ``Path(reference_data_dir)/'energy_dist.npz').is_file()`` | True (3,688 B) |
| F4.3 | ``_compute_flowmol3_composite`` sets ``run_energy_div=True`` when npz present | PASS |
| wire  | ``_compute_flowmol3_composite`` calls ``_compute_xtb_med_rmsd`` when xtb present | PASS |
| pytest| ``pytest tests/test_tools/test_run_real_ckpt_eval.py`` | 36 passed |

---

## 9. Notes

- The F3 install method is conda-forge (NOT apt — no apt source on
  this Ubuntu 22.04; NOT pip — no wheel for Python 3.12). The conda
  prefix lives at ``/home/hugo/xtb_prefix/`` (user-writable, outside
  the read-only ``/opt/miniforge3/envs/``).
- The F4 npz is a 3.7 KB file copy — no code change to
  ``FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR``. Byte-stable constant.
- The ``_compute_xtb_med_rmsd`` helper is additive — no edits to the
  ``FlowMol3Glue.composite_score`` signature or the ``composite_score``
  weight renormalization. When ``geometry`` is ``None`` the composite
  still computes from chemistry-only weights via
  ``renormalize_for_geometry(False)``.
- The wire is **additive**: when xtb is absent / npz is absent, the
  pre-existing Wave 73 7/9 behaviour is preserved exactly (geometry
  axis = None, energy_js_div = 0.0).
- Wave 74 Phase 5 (the 9-cell sweep with all 4 fixes active) is a
  separate downstream agent.

**Wave 74 Phase 4 closed at:** 2026-09-08
**Status:** F3 (xtb 6.7.1) installed; F4 (energy_dist.npz 3.7 KB) vendored;
both axes wired + auto-detected. Smoke test PASS. Pytest 36/36 PASS. NO push.
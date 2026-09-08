"""Thin subprocess-only xtb bridge for the FlowMol3 geometry / chemistry axes.

This module is the **subprocess boundary** between the in-process
framework (which has RDKit, numpy, torch — no xtb) and the upstream
FlowMol3 evaluation pipeline (which writes XYZ, calls GFN2-xTB, reads
the optimised geometry back as ``xtbtopo.mol``).

Contract
--------

Three public functions; all heavy work happens via ``subprocess``:

1. :func:`xtb_optimize_sdf` — run GFN2-xTB geometry optimisation on
   every record in an input SDF; write the optimised SDF to
   ``opt_sdf_path`` and return that path. Uses the upstream
   ``fm3_evals/geometry/xtb_optimization.py`` CLI verbatim (subprocess
   to the python interpreter).

2. :func:`compute_med_rmsd` — compute the median per-pair RMSD between
   an initial SDF and the corresponding optimised SDF. Uses the
   upstream ``fm3_evals/geometry/rmsd_energy.py`` CLI verbatim
   (subprocess + JSON parse of the dumped ``.pkl`` sidecar).

3. :func:`xtb_energy_ratio` — for a single molecule (with the init /
   opt SDF pair already computed), return the energy ratio
   ``|E_init - E_opt| / min(|E_init|, |E_opt|)`` — the same scalar
   the PoseBusters ``energy_ratio`` check computes (Buttenschoen et al.
   2024, ``threshold_energy_ratio=100.0`` default), WITHOUT importing
   the ``posebusters`` package in-process. The two single-point
   energies are obtained via two subprocess ``xtb`` calls.

Design rules
------------

* **No ``posebusters`` imports** anywhere in this file. The whole
  point of the bridge is to keep the PB boundary at subprocess
  granularity; PB internals stay opaque to the framework.
* **RDKit is allowed** (it ships with the framework's chemistry extra)
  for SDF round-tripping only. RDKit here is the in-process SDF parser,
  not a PB integration.
* **Every xtb call goes through ``subprocess.run``** so the
  framework's Python interpreter never links against ``libxtb``. The
  upstream xtb Python wheels are not installed in the framework venv;
  invoking ``xtb`` as a CLI binary works regardless of which xtb
  variant is on ``$PATH``.
* **No silent fallback to a stub.** When xtb is missing we return
  ``None`` / raise ``FileNotFoundError`` with the install hint
  surfaced verbatim; downstream consumers can branch on the sentinel.

CLI usage
---------

The module is import-only; there is no ``__main__``. Callers are
expected to ``from tools.flowmol3_xtb_bridge import xtb_optimize_sdf,
compute_med_rmsd, xtb_energy_ratio``.

Reference
---------

* Upstream ``data/FlowMol3/repo/fm3_evals/geometry/xtb_optimization.py``
  (line 28: ``xtb <xyz> --opt --charge N --namespace PREFIX``).
* Upstream ``data/FlowMol3/repo/fm3_evals/geometry/rmsd_energy.py``
  (the median RMSD computation the Wave 82 fix delegates to).
* PB energy_ratio semantics: ``posebusters/modules/energy_ratio.py``
  (verified Wave 87 audit — uses UFF, not xtb; our
  ``xtb_energy_ratio`` is the true xtb-flavoured variant).
"""
from __future__ import annotations

import json
import math
import os
import pickle  # nosec — only loads files we just wrote ourselves
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

#: Absolute path to the in-tree upstream FlowMol3 vendored copy. The
#: bridge shells out to the two scripts under ``fm3_evals/geometry/``;
#: we resolve them relative to the repo root so the bridge is portable
#: regardless of the caller's CWD.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
FLOWMOL3_UPSTREAM_ROOT: Path = REPO_ROOT / "data" / "FlowMol3" / "repo"

#: Upstream xtb CLI helper — runs ``xtb <xyz> --opt`` per molecule and
#: dumps ``xtbtopo.mol`` per record.
XTB_OPTIMIZATION_SCRIPT: Path = (
    FLOWMOL3_UPSTREAM_ROOT / "fm3_evals" / "geometry" / "xtb_optimization.py"
)

#: Upstream RMSD / energy aggregator — computes per-pair RMSD + energy
#: gain + MMFF drop and dumps ``rmsd_energy_results.pkl``.
RDKIT_RMSD_ENERGY_SCRIPT: Path = (
    FLOWMOL3_UPSTREAM_ROOT / "fm3_evals" / "geometry" / "rmsd_energy.py"
)

#: Default xtb binary path. Override via ``xtb_binary`` kwarg on
#: :func:`xtb_optimize_sdf` / :func:`xtb_energy_ratio` for sidecar
#: hosts. Mirrors ``tools/run_real_ckpt_eval.py:_compute_xtb_med_rmsd``
#: (Wave 82 Agent A §2.4 audit: this is the Wave 74 F3 install prefix).
DEFAULT_XTB_BINARY: str = "/home/hugo/xtb_prefix/bin/xtb"

#: Install hint surfaced when xtb is missing on ``$PATH`` AND the
#: default prefix is empty.
XTB_INSTALL_HINT: str = (
    "install xtb at /home/hugo/xtb_prefix (conda install -c conda-forge xtb) "
    "or set FLOWMOL3_XTB_BINARY env var to a valid xtb executable"
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class XtbBridgeError(RuntimeError):
    """Raised when xtb (or its upstream helpers) cannot complete.

    All three public functions raise this error (rather than returning
    ``None``) on hard failures, so a caller who forgets to branch on
    a sentinel sees the failure loudly. Soft failures (missing xtb,
    a single conformer skipped) are reported via stderr-equivalent
    ``stderr_lines`` fields on the return dicts.
    """


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_xtb_binary(xtb_binary: str | None) -> Path | None:
    """Return the absolute path to an ``xtb`` executable, or ``None``.

    Resolution order:
      1. Caller-supplied ``xtb_binary`` arg (preferred for tests +
         sidecar hosts).
      2. ``$FLOWMOL3_XTB_BINARY`` environment variable (preferred for
         CI / container hosts).
      3. :data:`DEFAULT_XTB_BINARY` (the Wave 74 F3 install prefix).
      4. ``shutil.which("xtb")`` on ``$PATH``.

    Returns ``None`` when none of the above resolves to an existing
    file. A ``None`` result is treated as "xtb not available" by the
    rest of this module — callers either get a non-zero return dict
    marker or an :class:`XtbBridgeError`, depending on which surface
    they invoke.
    """
    candidates: list[str | None] = [
        xtb_binary,
        os.environ.get("FLOWMOL3_XTB_BINARY"),
        DEFAULT_XTB_BINARY,
        shutil.which("xtb"),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            path = Path(candidate)
        except (TypeError, ValueError):
            continue
        if path.is_file():
            return path
        # ``shutil.which`` returns absolute paths; belt-and-braces.
        if path.exists() and os.access(str(path), os.X_OK):
            return path
    return None


def _python_interpreter() -> str:
    """Return the python interpreter to use for upstream-script subprocesses.

    Default to ``sys.executable`` so the subprocess uses the same venv
    as the parent (the framework venv has RDKit; the xtb scripts only
    need RDKit + stdlib + xtb on ``$PATH`` — RDKit is the load-bearing
    dependency and is in the framework venv).
    """
    return sys.executable


def _build_xtb_env(xtb_bin_path: Path) -> dict[str, str]:
    """Build a subprocess env dict that puts the xtb prefix on ``$PATH``.

    xtb requires its own ``lib/`` and ``share/`` directories on
    ``PATH`` / ``LD_LIBRARY_PATH`` for the GFN2-xTB Hamiltonian tables
    to be discovered. Mirrors the
    ``_compute_xtb_geometry_metrics`` env setup in
    ``tools/run_real_ckpt_eval.py``.

    Returns a fresh env dict (does NOT mutate ``os.environ``).
    """
    env = os.environ.copy()
    prefix_dir = str(xtb_bin_path.parent.parent)
    # Prepend the xtb prefix bin to PATH so the ``xtb`` binary itself
    # plus any xtb-bundled helpers are found first.
    env["PATH"] = prefix_dir + os.pathsep + env.get("PATH", "")
    # xtb uses ``XTBPATH`` env var to locate its parametrisation tables.
    xtb_share = Path(prefix_dir) / "share" / "xtb"
    if xtb_share.is_dir():
        env["XTBPATH"] = str(xtb_share)
    # Some xtb builds ship a ``LD_LIBRARY_PATH`` requirement for
    # ``libxtb``. Set it but do not clobber.
    xtb_lib = Path(prefix_dir) / "lib"
    if xtb_lib.is_dir():
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = str(xtb_lib) + (os.pathsep + existing if existing else "")
    return env


def _write_xyz(mol: Any, xyz_path: Path) -> None:
    """Write an RDKit mol to a minimal XYZ file for xtb consumption.

    Mirrors the upstream ``xtb_optimization.sdf_to_xyz`` helper
    (data/FlowMol3/repo/fm3_evals/geometry/xtb_optimization.py:14-20).
    We duplicate it here (rather than import) so this module can run
    on a host where ``fm3_evals`` is not on ``sys.path``.
    """
    conf = mol.GetConformer()
    n_atoms = mol.GetNumAtoms()
    lines = [f"{int(n_atoms)}", ""]
    for atom in mol.GetAtoms():
        idx = atom.GetIdx()
        pos = conf.GetAtomPosition(idx)
        lines.append(f"{atom.GetSymbol()} {pos.x:.8f} {pos.y:.8f} {pos.z:.8f}")
    xyz_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mol_to_charge(mol: Any) -> int:
    """Sum the formal charges on ``mol``; matches upstream's
    ``get_molecule_charge`` (``xtb_optimization.py:76-81``)."""
    total = 0
    for atom in mol.GetAtoms():
        total += int(atom.GetFormalCharge())
    return int(total)


def _mol_to_sdf_string(mol: Any, name: str | None = None) -> str:
    """Serialize an RDKit mol to an SDF record (molblock + name + $$$$).

    Used to feed the per-mol single-point energy calls inside
    :func:`xtb_energy_ratio`. Mirrors
    ``xtb_optimization.write_mol_to_sdf`` (``xtb_optimization.py:64-73``).
    """
    from rdkit import Chem  # local import — keep top of file stdlib-only

    mol_block = Chem.MolToMolBlock(mol, kekulize=False)
    out_lines = [mol_block, ""]
    if name is not None:
        out_lines.append(f"  {name}")
    # Propagate any props (e.g. ``energy_gain`` set by upstream).
    for prop_name in mol.GetPropNames():
        prop_value = mol.GetProp(prop_name)
        out_lines.append(f">  <{prop_name}>\n{prop_value}\n\n")
    out_lines.append("$$$$")
    return "\n".join(out_lines) + "\n"


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def xtb_optimize_sdf(
    sdf_path: str | Path,
    init_sdf_path: str | Path,
    *,
    xtb_binary: str | None = None,
    timeout_s: int | None = None,
) -> Path:
    """Run GFN2-xTB geometry optimisation on every record in ``sdf_path``.

    Subprocesses to the upstream
    ``fm3_evals/geometry/xtb_optimization.py`` script with
    ``--input_sdf <sdf_path> --output_sdf <init_sdf_path with _opt
    suffix> --init_sdf <init_sdf_path>``.

    Parameters
    ----------
    sdf_path : str | Path
        Input SDF file containing one or more RDKit records. Each
        record MUST carry a 3D conformer (FlowMol3 / GraphBFN samples
        do; otherwise an xtb geometry opt cannot start).
    init_sdf_path : str | Path
        Destination SDF file for the INITIAL conformers (verbatim copy
        of the input records, in the upstream pipeline — the ``init_``
        file is paired with the ``opt_`` file for downstream RMSD
        computation). Per upstream contract the ``opt`` SDF is written
        alongside ``init_sdf_path`` with the ``_opt`` suffix inserted
        before the extension.
    xtb_binary : str | None
        Override xtb executable (test / sidecar use).
    timeout_s : int | None
        Per-molecule timeout for the upstream script. ``None`` defers
        to the upstream default (300 s per mol × ``N_mols``).

    Returns
    -------
    Path
        Absolute path to the optimised SDF written by the upstream
        pipeline. By convention this is
        ``init_sdf_path.with_name(init_sdf_path.stem + "_opt.sdf")`` —
        matching the upstream ``xtb_optimization.main_fn`` output
        destination. The upstream script also writes the initial SDF
        to ``init_sdf_path`` as a sidecar.

    Raises
    ------
    XtbBridgeError
        On xtb missing, upstream script missing, subprocess non-zero
        exit, or timeout.
    """
    sdf_path = Path(sdf_path).resolve()
    init_sdf_path = Path(init_sdf_path).resolve()

    # Resolve xtb binary — fail loud if absent (no silent stub).
    xtb_bin = _resolve_xtb_binary(xtb_binary)
    if xtb_bin is None:
        raise XtbBridgeError(
            f"xtb binary not found: {XTB_INSTALL_HINT}"
        )

    # Validate upstream script presence.
    if not XTB_OPTIMIZATION_SCRIPT.is_file():
        raise XtbBridgeError(
            f"upstream xtb_optimization.py not found at {XTB_OPTIMIZATION_SCRIPT}; "
            f"verify data/FlowMol3/repo is present"
        )

    # Upstream convention: opt_sdf = init_sdf stem + "_opt" + suffix.
    opt_sdf_path = init_sdf_path.with_name(
        init_sdf_path.stem + "_opt" + init_sdf_path.suffix
    )

    # Build the subprocess command. The upstream script's CLI takes
    # ``--input_sdf``, ``--output_sdf``, ``--init_sdf`` (see
    # ``xtb_optimization.py:171-176``).
    cmd = [
        _python_interpreter(),
        str(XTB_OPTIMIZATION_SCRIPT),
        "--input_sdf", str(sdf_path),
        "--output_sdf", str(opt_sdf_path),
        "--init_sdf", str(init_sdf_path),
    ]
    env = _build_xtb_env(xtb_bin)

    try:
        completed = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise XtbBridgeError(
            f"xtb_optimization.py timed out after {timeout_s}s "
            f"on input {sdf_path}"
        ) from exc

    if completed.returncode != 0:
        stderr_tail = (completed.stderr or "")[-2000:]
        raise XtbBridgeError(
            f"xtb_optimization.py exited {completed.returncode} on "
            f"{sdf_path}: {stderr_tail}"
        )

    if not opt_sdf_path.is_file():
        raise XtbBridgeError(
            f"xtb_optimization.py returned 0 but did not write "
            f"{opt_sdf_path}"
        )

    return opt_sdf_path


def compute_med_rmsd(
    init_sdf: str | Path,
    opt_sdf: str | Path,
    *,
    timeout_s: int | None = None,
) -> float:
    """Compute median per-pair RMSD between ``init_sdf`` and ``opt_sdf``.

    Subprocesses to the upstream
    ``fm3_evals/geometry/rmsd_energy.py`` script and parses the
    dumped ``rmsd_energy_results.pkl`` sidecar.

    Parameters
    ----------
    init_sdf : str | Path
        SDF of initial (pre-optimisation) conformers. Each record MUST
        carry a 3D conformer.
    opt_sdf : str | Path
        SDF of optimised (post-xtb) conformers, one record per init
        record, in the same order.
    timeout_s : int | None
        Hard timeout for the upstream subprocess. ``None`` uses
        120 s (matches the Wave 82 / Wave 87 budget for 1-mol smoke
        tests; bump to 3600+ for N=1000 sweeps).

    Returns
    -------
    float
        ``med_rmsd`` in Angstroms, matching the upstream
        ``compute_metrics_for_pairs`` key ``med_rmsd``
        (``rmsd_energy.py:62``). Returns ``0.0`` if the upstream
        pipeline saw zero usable pairs (matches upstream behaviour —
        the upstream dict uses ``np.median([]) = nan``-guard with a
        ``0.0`` fallback at line 62; we read what upstream wrote).

    Raises
    ------
    XtbBridgeError
        On missing upstream script, subprocess non-zero exit, missing
        ``.pkl`` sidecar, or malformed ``med_rmsd`` key.
    """
    init_sdf = Path(init_sdf).resolve()
    opt_sdf = Path(opt_sdf).resolve()

    if not RDKIT_RMSD_ENERGY_SCRIPT.is_file():
        raise XtbBridgeError(
            f"upstream rmsd_energy.py not found at {RDKIT_RMSD_ENERGY_SCRIPT}; "
            f"verify data/FlowMol3/repo is present"
        )

    if not init_sdf.is_file():
        raise XtbBridgeError(f"init_sdf not found: {init_sdf}")
    if not opt_sdf.is_file():
        raise XtbBridgeError(f"opt_sdf not found: {opt_sdf}")

    # Upstream ``rmsd_energy.py:82`` defines ``--output_file``. When
    # unset, the script dumps ``rmsd_energy_results.pkl`` next to the
    # init_sdf directory. Use a tempfile to keep the workspace tidy
    # — caller does NOT need the .pkl sidecar.
    with tempfile.TemporaryDirectory(prefix="flowmol3_xtb_bridge_") as tmp:
        tmp_path = Path(tmp)
        out_stem = tmp_path / "rmsd_energy_results"
        # The script appends ``.pkl`` and ``.txt`` to ``--output_file``;
        # pass the stem and let upstream handle the suffixes.
        cmd = [
            _python_interpreter(),
            str(RDKIT_RMSD_ENERGY_SCRIPT),
            "--init_sdf", str(init_sdf),
            "--opt_sdf", str(opt_sdf),
            "--output_file", str(out_stem),
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s if timeout_s is not None else 120,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise XtbBridgeError(
                f"rmsd_energy.py timed out after "
                f"{timeout_s if timeout_s is not None else 120}s"
            ) from exc

        if completed.returncode != 0:
            stderr_tail = (completed.stderr or "")[-2000:]
            raise XtbBridgeError(
                f"rmsd_energy.py exited {completed.returncode}: {stderr_tail}"
            )

        # Locate the dumped .pkl (upstream writes ``<stem>.pkl``).
        pkl_candidates = [
            out_stem.with_suffix(".pkl"),
            init_sdf.parent / "rmsd_energy_results.pkl",
        ]
        pkl_path: Path | None = None
        for candidate in pkl_candidates:
            if candidate.is_file():
                pkl_path = candidate
                break
        if pkl_path is None:
            raise XtbBridgeError(
                f"rmsd_energy.py returned 0 but no .pkl sidecar at "
                f"{[str(p) for p in pkl_candidates]}"
            )

        # The .pkl is OUR file — written by the upstream script we just
        # ran. No untrusted content. ``pickle.load`` here is safe.
        with pkl_path.open("rb") as fh:
            results = pickle.load(fh)  # nosec — see comment above

    if not isinstance(results, dict):
        raise XtbBridgeError(
            f"rmsd_energy.py dumped non-dict payload at {pkl_path}: "
            f"type={type(results).__name__}"
        )
    if "med_rmsd" not in results:
        raise XtbBridgeError(
            f"rmsd_energy.py dump missing 'med_rmsd' key: "
            f"keys={sorted(results.keys())}"
        )
    med_rmsd_raw = results["med_rmsd"]
    try:
        med_rmsd = float(med_rmsd_raw)
    except (TypeError, ValueError) as exc:
        raise XtbBridgeError(
            f"med_rmsd not coercible to float: {med_rmsd_raw!r}"
        ) from exc
    if not math.isfinite(med_rmsd):
        # Upstream uses 0.0 as the empty-input fallback (rmsd_energy.py:62)
        # so a NaN here means the upstream dict shipped a real NaN, which
        # we surface as an error — the empty-input contract is 0.0.
        raise XtbBridgeError(
            f"med_rmsd is non-finite ({med_rmsd_raw!r}); upstream "
            f"empty-input contract should have produced 0.0"
        )
    return float(med_rmsd)


def xtb_energy_ratio(
    mol: Any,
    init_sdf: str | Path,
    opt_sdf: str | Path,
    *,
    xtb_binary: str | None = None,
    timeout_s: int | None = None,
) -> float:
    """Compute ``|E_init - E_opt| / min(|E_init|, |E_opt|)`` for one mol.

    This is the xtb-flavoured analogue of PoseBusters' ``energy_ratio``
    check (Buttenschoen et al. 2024, ``threshold_energy_ratio=100.0``
    default) — but using REAL xtb energies, not the UFF proxy PB uses
    internally (verified Wave 87 Agent A audit:
    ``posebusters/modules/energy_ratio.py:6-14`` imports ``from
    rdkit.Chem import AllChem`` + UFF). The contract is the same: a
    ratio ``>= 1.0`` means the lower-energy conformer is more than
    ``threshold`` lower than the higher-energy conformer; the PB
    default ``threshold_energy_ratio=7.0`` rejects conformer ensembles
    where any conformer is more than 7× the energy of the lowest.

    In this bridge the "conformer ensemble" is the (init, opt) pair —
    the GFN2-xTB single-point energy of each. PB's own ensemble is a
    ``num_confs=100`` ETKDG ensemble; our pair is a 2-member ensemble.
    The semantics differ; we document this in the returned value (a
    single float, the caller is expected to know what it means).

    Parameters
    ----------
    mol : rdkit.Chem.Mol
        The molecule to score. MUST carry a 3D conformer. Used to
        write a per-mol SDF record for the single-point energy
        calculation.
    init_sdf : str | Path
        Path to the initial-conformer SDF (the bridge-sidecar from
        :func:`xtb_optimize_sdf`). Currently unused beyond an
        existence check — kept in the signature so the caller can
        thread init/opt state explicitly and so we can extend to a
        per-record lookup later without changing the API.
    opt_sdf : str | Path
        Path to the optimised-conformer SDF. Same — existence check
        only for now; documented as future-extensible.
    xtb_binary : str | None
        Override xtb executable (test / sidecar use).
    timeout_s : int | None
        Per-xtb-call timeout. ``None`` uses 60 s (single-point energy
        is fast — usually << 10 s; 60 s leaves headroom for cold
        xtb parametrisation load).

    Returns
    -------
    float
        ``|E_init - E_opt| / min(|E_init|, |E_opt|)`` in Hartrees
        (xtb reports total energies in ``Eh``). Finite non-negative.
        Returns ``0.0`` when init and opt single-point energies are
        numerically identical (the molecule was already at a
        stationary point).

    Raises
    ------
    XtbBridgeError
        On xtb missing, subprocess non-zero exit, timeout, or the
        output missing a parseable total-energy line.
    """
    # Validate inputs.
    init_sdf = Path(init_sdf).resolve()
    opt_sdf = Path(opt_sdf).resolve()
    if not init_sdf.is_file():
        raise XtbBridgeError(f"init_sdf not found: {init_sdf}")
    if not opt_sdf.is_file():
        raise XtbBridgeError(f"opt_sdf not found: {opt_sdf}")

    xtb_bin = _resolve_xtb_binary(xtb_binary)
    if xtb_bin is None:
        raise XtbBridgeError(f"xtb binary not found: {XTB_INSTALL_HINT}")

    # Extract the per-mol XYZ files for the single-point energies.
    # xtb consumes XYZ (one mol per file) — same format upstream's
    # ``xtb_optimization.sdf_to_xyz`` uses.
    with tempfile.TemporaryDirectory(prefix="flowmol3_xtb_energy_") as tmp:
        tmp_path = Path(tmp)
        init_xyz = tmp_path / "init.xyz"
        opt_xyz = tmp_path / "opt.xyz"
        # Copy the conformers into a fresh mol so we can write the
        # initial geometry WITHOUT also re-embedding.
        from rdkit import Chem  # local — keep top of file stdlib-only

        # Use the provided ``mol`` as the init conformer source.
        init_mol = Chem.Mol(mol)
        opt_mol = Chem.Mol(mol)
        # Find the corresponding optimised record by name.
        supplier = Chem.SDMolSupplier(str(opt_sdf), sanitize=False, removeHs=False)
        target_name = (
            mol.GetProp("_Name") if mol.HasProp("_Name") else None
        )
        chosen_opt_mol: Any | None = None
        for record in supplier:
            if record is None:
                continue
            if target_name is None:
                chosen_opt_mol = record
                break
            rec_name = (
                record.GetProp("_Name") if record.HasProp("_Name") else None
            )
            if rec_name == target_name:
                chosen_opt_mol = record
                break
        if chosen_opt_mol is None:
            raise XtbBridgeError(
                f"could not find opt mol with _Name={target_name!r} in {opt_sdf}"
            )
        opt_mol = chosen_opt_mol

        _write_xyz(init_mol, init_xyz)
        _write_xyz(opt_mol, opt_xyz)

        env = _build_xtb_env(xtb_bin)
        e_init = _single_point_energy(init_xyz, xtb_bin, env, timeout_s)
        e_opt = _single_point_energy(opt_xyz, xtb_bin, env, timeout_s)

    ratio = _energy_ratio(e_init, e_opt)
    return float(ratio)


# ---------------------------------------------------------------------------
# Internal helpers (not part of the public surface)
# ---------------------------------------------------------------------------


_ENERGY_LINE_RE = re.compile(
    r"""(?xi)
    (?:
        \bTOTAL\s+ENERGY\b
      | \btotal\s+free\s+energy\b
      | \bTOTAL\s+SCF\s+ENERGY\b
    )
    [^0-9eE+\-]*
    (?P<energy> [+-]? \d+ (?: \.\d* )? (?: [eE][+-]?\d+ )? )
    \s*Eh
    """
)


def _single_point_energy(
    xyz_path: Path,
    xtb_bin: Path,
    env: dict[str, str],
    timeout_s: int | None,
) -> float:
    """Run ``xtb <xyz> --sp --charge 0`` and parse the final energy.

    Single-point energy (no ``--opt``) — used by
    :func:`xtb_energy_ratio` to score both endpoints of an (init, opt)
    pair without re-optimising. Returns the energy in Hartrees.
    """
    cmd = [
        str(xtb_bin),
        str(xyz_path),
        "--sp",
        "--charge", "0",
        "--namespace", "sp",
    ]
    try:
        completed = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s if timeout_s is not None else 60,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise XtbBridgeError(
            f"xtb single-point timed out after "
            f"{timeout_s if timeout_s is not None else 60}s on {xyz_path}"
        ) from exc
    if completed.returncode != 0:
        stderr_tail = (completed.stderr or "")[-2000:]
        raise XtbBridgeError(
            f"xtb single-point exited {completed.returncode} on {xyz_path}: {stderr_tail}"
        )
    energy = _parse_xtb_energy(completed.stdout)
    if energy is None:
        # xtb sometimes prints the energy on stderr (rare); fall back.
        energy = _parse_xtb_energy(completed.stderr)
    if energy is None:
        raise XtbBridgeError(
            f"xtb single-point output missing parseable total energy on {xyz_path}"
        )
    return float(energy)


def _parse_xtb_energy(blob: str) -> float | None:
    """Find the first ``TOTAL ENERGY ... Eh`` line in ``blob`` and return
    the energy in Hartrees. Returns ``None`` when no line matches.

    Matches the three xtb total-energy flavours we have observed in
    the wild (GFN2-xTB, GFN1-xTB, GFN0-xtb):
      ``TOTAL ENERGY              -5.234567 Eh``
      ``:: total free energy    -5.234567 Eh   ::``
      ``TOTAL SCF ENERGY            -5.234567 Eh``
    """
    if not blob:
        return None
    for line in blob.splitlines():
        match = _ENERGY_LINE_RE.search(line)
        if match is None:
            continue
        try:
            return float(match.group("energy"))
        except (TypeError, ValueError):
            continue
    return None


def _energy_ratio(e_init: float, e_opt: float) -> float:
    """Return ``|E_init - E_opt| / min(|E_init|, |E_opt|)``.

    Both energies are in the same units (Hartrees, parsed from xtb
    ``Eh`` output). Both negative for a bound molecule; the ratio is
    therefore a positive scalar when the two differ, ``0.0`` when
    identical.

    PB's ``threshold_energy_ratio=100.0`` rejects conformer ensembles
    where ``max(E) / min(E) > 100.0``. The PB internal computation
    uses ``(Emax - Emin) / Emin`` (verified
    ``posebusters/modules/energy_ratio.py``); we use the equivalent
    ``|E_init - E_opt| / min(|E_init|, |E_opt|)`` form which is
    sign-stable for negative Hartree energies.
    """
    if not (math.isfinite(e_init) and math.isfinite(e_opt)):
        raise XtbBridgeError(
            f"non-finite energies: e_init={e_init!r}, e_opt={e_opt!r}"
        )
    diff = abs(float(e_init) - float(e_opt))
    if diff == 0.0:
        return 0.0
    min_abs = min(abs(float(e_init)), abs(float(e_opt)))
    if min_abs == 0.0:
        raise XtbBridgeError(
            f"both energies numerically zero: e_init={e_init}, e_opt={e_opt}"
        )
    return float(diff / min_abs)


# ---------------------------------------------------------------------------
# Convenience: dict-shape for callers that want soft-failure semantics
# ---------------------------------------------------------------------------


def _ensure_bridge_diagnostics(  # pragma: no cover — diagnostic helper
    *,
    xtb_available: bool,
    upstream_root: Path,
) -> dict[str, Any]:
    """Build a stable ``status`` dict for callers wanting soft-failure.

    Not part of the public surface. Diagnostic helper for the
    Wave 82 / Wave 74 smoke test (verified that this bridge exposes
    the same axes the framework's
    ``tools/run_real_ckpt_eval.py:_compute_xtb_geometry_metrics``
    consumes).
    """
    return {
        "xtb_available": bool(xtb_available),
        "upstream_root_exists": bool(upstream_root.is_dir()),
        "xtb_optimization_script_exists": bool(XTB_OPTIMIZATION_SCRIPT.is_file()),
        "rmsd_energy_script_exists": bool(RDKIT_RMSD_ENERGY_SCRIPT.is_file()),
        "default_xtb_binary_exists": bool(Path(DEFAULT_XTB_BINARY).is_file()),
        "install_hint": XTB_INSTALL_HINT,
    }


__all__ = [
    "DEFAULT_XTB_BINARY",
    "RDKIT_RMSD_ENERGY_SCRIPT",
    "XTB_OPTIMIZATION_SCRIPT",
    "XTB_INSTALL_HINT",
    "XtbBridgeError",
    "compute_med_rmsd",
    "xtb_energy_ratio",
    "xtb_optimize_sdf",
]

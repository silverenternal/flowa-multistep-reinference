"""Thin wrapper around the upstream FlowMol3 analysis API.

This module is a *thin shim*. Every metric value returned by
:func:`compute_paper_metrics` and :func:`compute_paper_metrics_from_smiles`
comes verbatim from upstream
``flowmol.analysis.metrics.SampleAnalyzer.analyze``. The wrapper only:

  1. Pre-stubs the ``flowmol`` package in :data:`sys.modules` so that the
     heavy ``flowmol/__init__.py`` (which pulls in
     ``flowmol.models.flowmol`` -> ``torch_scatter``) is NOT executed.
     This is the same approach the smoke test
     (``/tmp/upstream_smoke.py``) used on 2026-09-03 to verify end-to-end
     importability in ``flowmol3_venv``.
  2. Re-adds ``RingSystemLookup.default`` as a one-line compat shim
     because ``useful_rdkit_utils`` >=1.0 dropped it but
     ``flowmol/analysis/ring_systems.py`` still calls it.
  3. Converts ``rdkit_mol`` -> ``SampledMolecule`` via the upstream
     ``SampledMolecule.from_rdkit_mol`` classmethod (no metric
     reimplementation, no FAKE atom logic, no graph rebuild — the
     upstream code does all of that inside its own constructor).
  4. Constructs :class:`SampleAnalyzer` with the canonical positional
     arguments inferred from upstream source
     (``flowmol/analysis/metrics.py:46``).

CRITICAL CONSTRAINT: do NOT reimplement validity / QED / SA / logp /
PB-validity / REOS / OOD-ring / energy_div. The upstream code IS the
metric code. We are a thin shim.

Environment notes (verified 2026-09-03 on this host):
    - Python 3.12.13, torch 2.7.0+cu128, GPU 0 = RTX PRO 6000 Blackwell.
    - Upstream package root: ``data/FlowMol3/repo`` (pinned commit
      ``77cae22174b7792b0e25e9e0414038420736d841``).
    - Upstream sample/metric classes:
        - ``flowmol.analysis.metrics.SampleAnalyzer``
        - ``flowmol.analysis.molecule_builder.SampledMolecule``
    - Upstream ``SampleAnalyzer.analyze`` output keys (verified on the
      5-SMILES smoke set; see ``UPSTREAM VERIFIED SMOKE`` in the task
      header):
        - ``frac_valid_mols``, ``avg_frag_frac``, ``avg_num_components``,
          ``frac_connected``
        - ``frac_atoms_stable``, ``frac_mols_stable_valence``
        - ``flag_rate``, ``ood_rate``, ``reos_cum_dev``
        - ``pb_mol_pred_loaded``, ``pb_sanitization``,
          ``pb_inchi_convertible``, ``pb_all_atoms_connected``,
          ``pb_bond_lengths``, ``pb_bond_angles``,
          ``pb_internal_steric_clash``, ``pb_aromatic_ring_flatness``,
          ``pb_non-aromatic_ring_non-flatness``,
          ``pb_double_bond_flatness``, ``pb_valid``
"""

from __future__ import annotations

import json
import logging
import os
import sys
import types
from pathlib import Path
from typing import Any, Sequence

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — pinned to the upstream repo commit the rest of the framework
# (r17/P-21 / flowmol3_upstream_shim / flowmol3_v2_adapter) already locks.
# ---------------------------------------------------------------------------

FLOWMOL3_UPSTREAM_REPO: str = (
    "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo"
)
FLOWMOL3_PINNED_COMMIT: str = "77cae22174b7792b0e25e9e0414038420736d841"
FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR: str = (
    "/home/hugo/codes/flowa-multistep-reinference/data/FlowMol3/repo/data/geom_5_kekulized"
)


# ---------------------------------------------------------------------------
# Import-time state. We pre-stub the ``flowmol`` package BEFORE importing
# anything from it, so ``flowmol/__init__.py`` is never executed. That
# file unconditionally does ``from flowmol.models.flowmol import FlowMol``
# -> ``flowmol.utils.ctmc_utils`` -> ``torch_scatter``, none of which are
# needed for the analysis API and none of which are importable on this
# host (PyG index is DNS-blocked).
# ---------------------------------------------------------------------------

_UPSTREAM_IMPORT_ERROR: BaseException | None = None
_UPSTREAM_MODULES: dict[str, Any] = {}


def _install_upstream_path() -> None:
    """Prepend the upstream repo root to ``sys.path`` (idempotent)."""
    if FLOWMOL3_UPSTREAM_REPO not in sys.path:
        sys.path.insert(0, FLOWMOL3_UPSTREAM_REPO)


def _stub_flowmol_namespace() -> None:
    """Install a ``flowmol`` namespace-package stub into :data:`sys.modules`.

    We register an empty :class:`types.ModuleType` carrying only
    ``__path__`` so that ``from flowmol.analysis.X import Y`` still works
    via normal namespace-package resolution (``flowmol.analysis`` is a
    real subpackage on disk). The real ``flowmol/__init__.py`` is
    deliberately skipped — see the module docstring.
    """
    if "flowmol" in sys.modules:
        return
    stub = types.ModuleType("flowmol")
    stub.__path__ = [f"{FLOWMOL3_UPSTREAM_REPO}/flowmol"]
    sys.modules["flowmol"] = stub


def _install_ring_system_lookup_shim() -> None:
    """Re-add ``RingSystemLookup.default`` for ``useful_rdkit_utils`` >= 1.0.

    Upstream ``flowmol/analysis/ring_systems.py`` still calls
    ``RingSystemLookup.default()`` (legacy API). On this host we have
    ``useful_rdkit_utils`` 0.93 (the env was downgraded from 2.0.1; see
    ``UPSTREAM VERIFIED SMOKE`` notes). The smoke test installs the shim
    at import time; we do the same here so the wrapper works standalone.

    This shim does NOT touch any metric logic — it only restores a
    removed helper method on an upstream-imported class.
    """
    try:
        import useful_rdkit_utils.ring_systems as _rsu  # noqa: PLC0415
    except ImportError:
        return
    if not hasattr(_rsu.RingSystemLookup, "default"):
        _rsu.RingSystemLookup.default = classmethod(lambda cls: cls())


def _try_import_upstream() -> dict[str, Any]:
    """Import upstream ``SampleAnalyzer`` + ``SampledMolecule``; cache result.

    Returns a dict with ``"SampledMolecule"`` and ``"SampleAnalyzer"``
    keys on success. On any failure, leaves :data:`_UPSTREAM_IMPORT_ERROR`
    set and returns ``{}``.
    """
    global _UPSTREAM_IMPORT_ERROR
    if _UPSTREAM_MODULES:
        return _UPSTREAM_MODULES
    _install_upstream_path()
    _stub_flowmol_namespace()
    try:  # noqa: BLE001 — we want to capture *any* import error here.
        from flowmol.analysis.molecule_builder import SampledMolecule  # noqa: PLC0415
        from flowmol.analysis.metrics import SampleAnalyzer  # noqa: PLC0415
    except BaseException as exc:  # noqa: BLE001
        _UPSTREAM_IMPORT_ERROR = exc
        _LOGGER.warning(
            "flowmol3_metrics_upstream: upstream import failed. "
            "error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return {}
    _install_ring_system_lookup_shim()
    _UPSTREAM_MODULES.update(
        SampledMolecule=SampledMolecule,
        SampleAnalyzer=SampleAnalyzer,
    )
    return _UPSTREAM_MODULES


# Attempt the import once at module load. If it fails, the helper
# functions will surface a clear error on first use.
_try_import_upstream()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sampled_mol_from_rdkit_mol(rdkit_mol: Any) -> Any:
    """Wrap ``SampledMolecule.from_rdkit_mol`` with the canonical args.

    The upstream classmethod signature is
    ``from_rdkit_mol(mol: Chem.Mol, atom_type_map: List[str] = None, **kwargs)``
    (see ``flowmol/analysis/molecule_builder.py:87``). The smoke test
    invokes it with NO additional args, so the wrapper does the same.

    Parameters
    ----------
    rdkit_mol:
        A :class:`rdkit.Chem.Mol` that already has a 3D conformer
        (``mol.GetConformer().GetPositions()`` is what upstream reads).
        The caller is responsible for AddHs + ETKDGv3 embed + MMFF
        optimize before calling this helper — same recipe the smoke
        test uses.

    Returns
    -------
    flowmol.analysis.molecule_builder.SampledMolecule
    """
    modules = _try_import_upstream()
    if not modules:
        raise ImportError(
            "sampled_mol_from_rdkit_mol: upstream flowmol is not importable on this host. "
            f"Cached error: {_UPSTREAM_IMPORT_ERROR!r}"
        )
    SampledMolecule = modules["SampledMolecule"]
    return SampledMolecule.from_rdkit_mol(rdkit_mol)


def sampled_mols_from_smiles(smiles_list: Sequence[str]) -> list[Any]:
    """Parse a list of SMILES into a list of upstream ``SampledMolecule``.

    Each SMILES goes through the canonical recipe the upstream smoke
    test uses:

        MolFromSmiles -> AddHs -> ETKDGv3 (seed=0xF00D) -> EmbedMolecule
        -> MMFFOptimizeMolecule(maxIters=200) -> from_rdkit_mol

    Returns a list of :class:`SampledMolecule` objects, in the same
    order as the input SMILES. Skips (with a warning) any SMILES that
    fails to parse or embed rather than aborting the whole batch — the
    upstream analyzer would otherwise raise inside its inner loop and
    we'd lose all metrics for an unrelated molecule.
    """
    modules = _try_import_upstream()
    if not modules:
        raise ImportError(
            "sampled_mols_from_smiles: upstream flowmol is not importable on this host. "
            f"Cached error: {_UPSTREAM_IMPORT_ERROR!r}"
        )
    from rdkit import Chem  # noqa: PLC0415 — rdkit is required for SMILES parsing.

    out: list[Any] = []
    for smi in smiles_list:
        rdkit_mol = Chem.MolFromSmiles(smi)
        if rdkit_mol is None:
            _LOGGER.warning("sampled_mols_from_smiles: RDKit could not parse SMILES %r", smi)
            continue
        rdkit_mol = Chem.AddHs(rdkit_mol)
        params = Chem.AllChem.ETKDGv3()
        params.randomSeed = 0xF00D
        embed_status = Chem.AllChem.EmbedMolecule(rdkit_mol, params)
        if embed_status != 0:
            _LOGGER.warning(
                "sampled_mols_from_smiles: ETKDGv3 embed failed for %r (status=%d); skipping",
                smi,
                int(embed_status),
            )
            continue
        try:
            Chem.AllChem.MMFFOptimizeMolecule(rdkit_mol, maxIters=200)
        except Exception as exc:  # noqa: BLE001 — MMFF can refuse unusual geom.
            _LOGGER.debug(
                "sampled_mols_from_smiles: MMFF optimize failed for %r (%s); using embed geometry",
                smi,
                exc,
            )
        out.append(sampled_mol_from_rdkit_mol(rdkit_mol))
    return out


def compute_paper_metrics(
    sampled_mols: Sequence[Any],
    processed_data_dir: str | os.PathLike[str] | None = None,
    run_posebusters: bool = True,
    run_functional_validity: bool = True,
    run_energy_div: bool = False,
    pb_workers: int = 2,
    device: str = "cuda:0",
) -> dict[str, float]:
    """Run upstream ``SampleAnalyzer.analyze`` and return its dict verbatim.

    Parameters
    ----------
    sampled_mols:
        Sequence of upstream :class:`SampledMolecule` objects (e.g.
        from :func:`sampled_mol_from_rdkit_mol` or
        :func:`sampled_mols_from_smiles`, or directly from a FlowMol3
        ``model.sample_random_sizes`` call).
    processed_data_dir:
        Upstream processed dataset directory. **Must be a
        ``pathlib.Path``** — upstream code uses ``Path('/')`` on it
        (e.g. ``self.processed_data_dir / 'energy_dist.npz'``); passing
        a string raises ``TypeError: unsupported operand type(s) for
        /: 'str' and 'str'``. ``None`` triggers upstream's
        ``flowmol_root() / 'data' / 'geom_full_kekulized'`` fallback.
    run_posebusters:
        Forwarded to ``analyze(posebusters=...)``. PoseBusters is
        memory-hungry; on tight GPUs, retry with ``False`` to confirm
        the non-PB metric path still works (see module docstring).
    run_functional_validity:
        Forwarded to ``analyze(functional_validity=...)``. Adds
        ``flag_rate``, ``ood_rate``, ``reos_cum_dev``.
    run_energy_div:
        Forwarded both as ``analyzer.pb_energy=True`` (so PoseBusters
        uses the 'mol' config, not ``pb_config.yaml``) AND as
        ``analyze(energy_div=...)``. Requires
        ``processed_data_dir`` to contain ``energy_dist.npz``.
    pb_workers:
        Number of PoseBusters worker processes. ``0`` is sequential.
    device:
        Accepted for API symmetry with the rest of the framework; the
        upstream analyzer is CPU/GPU-agnostic (PoseBusters runs on CPU,
        RDKit operations are CPU-only). The default is ``"cuda:0"`` to
        match the framework-wide default; it is currently informational.

    Returns
    -------
    dict
        The metrics dict returned by upstream
        ``SampleAnalyzer.analyze``. No transformation, no filtering, no
        reimplementation.
    """
    modules = _try_import_upstream()
    if not modules:
        raise ImportError(
            "compute_paper_metrics: upstream flowmol is not importable on this host. "
            f"Cached error: {_UPSTREAM_IMPORT_ERROR!r}"
        )
    SampleAnalyzer = modules["SampleAnalyzer"]

    # CRITICAL: pass pathlib.Path, not str. Upstream code uses '/' on it
    # (e.g. processed_data_dir / 'energy_dist.npz'); a string would raise.
    if processed_data_dir is None:
        pdd_path: Path | None = None
    else:
        pdd_path = Path(processed_data_dir)

    analyzer = SampleAnalyzer(
        processed_data_dir=pdd_path,
        pb_workers=int(pb_workers),
        pb_energy=bool(run_energy_div),
    )
    metrics = analyzer.analyze(
        list(sampled_mols),
        functional_validity=bool(run_functional_validity),
        posebusters=bool(run_posebusters),
        energy_div=bool(run_energy_div),
    )
    return dict(metrics)


def compute_paper_metrics_from_smiles(
    smiles_list: Sequence[str],
    processed_data_dir: str | os.PathLike[str] | None = None,
    run_posebusters: bool = True,
    run_functional_validity: bool = True,
    run_energy_div: bool = False,
    pb_workers: int = 2,
    device: str = "cuda:0",
) -> dict[str, float]:
    """Sugar: SMILES -> SampledMolecule -> upstream metrics dict.

    Forwarded arguments are documented in :func:`compute_paper_metrics`.
    """
    sampled_mols = sampled_mols_from_smiles(smiles_list)
    return compute_paper_metrics(
        sampled_mols=sampled_mols,
        processed_data_dir=processed_data_dir,
        run_posebusters=run_posebusters,
        run_functional_validity=run_functional_validity,
        run_energy_div=run_energy_div,
        pb_workers=pb_workers,
        device=device,
    )


# ---------------------------------------------------------------------------
# Introspection helpers (useful as routing signals from other adapters).
# ---------------------------------------------------------------------------


def is_upstream_available() -> bool:
    """Return True iff upstream ``SampleAnalyzer`` imports cleanly on this host."""
    return bool(_try_import_upstream())


def get_upstream_import_error() -> BaseException | None:
    """Return the cached import error from the last upstream import attempt, if any."""
    return _UPSTREAM_IMPORT_ERROR


__all__ = [
    "FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR",
    "FLOWMOL3_PINNED_COMMIT",
    "FLOWMOL3_UPSTREAM_REPO",
    "compute_paper_metrics",
    "compute_paper_metrics_from_smiles",
    "get_upstream_import_error",
    "is_upstream_available",
    "sampled_mol_from_rdkit_mol",
    "sampled_mols_from_smiles",
]


def _smoke_check() -> None:
    """CLI sanity check: print upstream-import status without running analysis."""
    ok = is_upstream_available()
    err = get_upstream_import_error()
    print(f"upstream_available={ok}")
    print(f"upstream_repo={FLOWMOL3_UPSTREAM_REPO}")
    print(f"pinned_commit={FLOWMOL3_PINNED_COMMIT}")
    print(
        f"upstream_import_error={type(err).__name__ if err is not None else 'None'}: {err}"
    )
    if ok:
        modules = _UPSTREAM_MODULES
        print(f"SampledMolecule={modules['SampledMolecule']}")
        print(f"SampleAnalyzer={modules['SampleAnalyzer']}")


if __name__ == "__main__":  # pragma: no cover — manual smoke entry.
    _smoke_check()

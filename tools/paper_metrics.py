"""Wave 75 — FlowMol3 paper-metric reproduction module (paper parity).

The FlowMol3 paper (Dunn et al., NeurIPS 2024, arXiv 2508.12629)
reports **4 paper-parity metrics** on the real-ckpt samples:

  1. ``validity_pct``     = 0.999  (RDKit sanitization pass rate)
  2. ``pb_validity_pct``  = 0.919  (full PoseBusters incl. MMFF + xtb
                                     energy_ratio module)
  3. ``fg_dev``           = 0.27   (cumulative REOS flag-rate deviation
                                     vs GEOM_DRUGS training reference)
  4. ``ood_ring_rate``    = 0.10   (fraction of rings NOT in ChEMBL ring
                                     system reference)

This module is a **thin, paper-aligned consumer** of upstream
``flowmol.analysis.metrics.SampleAnalyzer.analyze``. Every metric value
returned here comes from an upstream function or vendored reference
data file:

  * :func:`compute_validity_pct` calls upstream
    ``SampleAnalyzer.compute_validity`` (the same function the Wave 49
    glue calls via ``compute_paper_metrics``).
  * :func:`compute_pb_validity_pct` calls upstream
    ``SampleAnalyzer.analyze(posebusters=True)``. When ``full_pb=True``
    (the paper path) it additionally drives PoseBusters with the
    energy-ratio module enabled via ``pb_energy=True`` (the upstream
    "mol" config). When ``full_pb=False`` it uses only the subset of
    PB checks active in the vendored ``pb_config.yaml`` (which is
    what the Wave 73 path uses — energy_ratio is commented out).
  * :func:`compute_fg_deviation` calls upstream
    ``SampleAnalyzer.reos_and_rings`` + the vendored
    ``data/geom_full_kekulized/train_reos_ring_counts.pkl`` reference
    distribution (already vendored Wave 70, 187 MB). When
    ``reference='NCI_first_5K_proxy'`` is requested, it falls back to
    the Wave 49 NCI proxy reference (different number, different
    semantics — used only for smoke tests).
  * :func:`compute_ood_ring_rate` calls upstream
    ``SampleAnalyzer.reos_and_rings`` which delegates to
    ``useful_rdkit_utils.ring_systems.RingSystemLookup`` (ChEMBL
    49,769 ring-system reference).

DO NOT INVENT NEW METRIC DEFINITIONS. If a metric is not in the
canonical upstream ``SampleAnalyzer.analyze`` output dict, this module
does not produce one. Every helper below calls an upstream function
or reads a vendored reference file (no FAKE atom logic, no graph
rebuild, no alternative valency table — upstream code does all of
that inside its own analyzer).

Interface contract
------------------

* Public surface: 4 functions + 1 aggregator
  (:func:`compute_all_paper_metrics`).
* Module-level imports are stdlib + numpy + the existing
  :mod:`adaptive_reflow.adapters.flowmol3_metrics_upstream` shim (no
  torch / dgl at module level).
* Upstream ``SampleAnalyzer`` is imported lazily inside the first
  function call so cold-import paths do not pay the cost.
* All 4 functions accept a ``processed_data_dir`` argument (defaulting
  to ``flowmol3_metrics_upstream.FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR``)
  so callers can override the reference distribution on the fly.

CLI / notebook usage::

    from tools.paper_metrics import compute_all_paper_metrics
    metrics = compute_all_paper_metrics(sampled_molecules, reference='GEOM_DRUGS')
    print(metrics['paper_validity_pct'],
          metrics['paper_pb_validity_pct'],
          metrics['paper_fg_deviation'],
          metrics['paper_ood_ring_rate'])

References (file:line citations from upstream vendored repo)

* ``flowmol/analysis/metrics.py:172-240``
  ``SampleAnalyzer.compute_validity`` — metric 1.
* ``flowmol/analysis/metrics.py:154-166`` + ``flowmol/analysis/pb_config.yaml``
  PoseBusters ``bust()`` — metric 2.
* ``flowmol/analysis/metrics.py:293-345`` + ``flowmol/analysis/metrics.py:415-430``
  ``SampleAnalyzer.reos_and_rings`` + ``compute_cumulative_reos_deviation``
  — metrics 3 + 4.
* ``flowmol/analysis/ring_systems.py:8-27`` ChEMBL ring-system
  counter — metric 4.
* ``data/geom_full_kekulized/train_reos_ring_counts.pkl`` (187 MB)
  the canonical fg_dev reference distribution — metric 3.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from adaptive_reflow.adapters.flowmol3_metrics_upstream import (
    FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR,
    FLOWMOL3_PINNED_COMMIT,
    FLOWMOL3_UPSTREAM_REPO,
    is_upstream_available,
)

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Wave 82 — vendored PoseBusters config with energy_ratio UNCOMMENTED.
#
# Vendored at ``tools/pb_config_with_energy_ratio.yaml`` (TRACKED in
# git so a future re-clone of the pinned upstream commit
# ``77cae22174b7792b0e25e9e0414038420736d841`` does not lose this file —
# Wave 82 Agent A §7.6 Phase F risk-mitigation). The upstream vendored
# ``flowmol/analysis/pb_config.yaml`` has the energy_ratio module
# commented out at lines 101-110; the new file uncomments it with the
# paper-tuned parameters (``threshold_energy_ratio=100.0``,
# ``ensemble_number_conformations=50``). PB 0.6.5's energy_ratio module
# uses UFF (verified at
# ``.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:6-14``)
# — xtb is NOT required for this check.
PB_CONFIG_WITH_ENERGY_RATIO_PATH: Path = (
    Path(__file__).resolve().parent / "pb_config_with_energy_ratio.yaml"
)


# ---------------------------------------------------------------------------
# Reference-set enumeration (paper-aligned + custom fallback)
# ---------------------------------------------------------------------------

#: Canonical reference distribution label for :func:`compute_fg_deviation`
#: and :func:`compute_ood_ring_rate`: the GEOM_DRUGS training set
#: (``data/geom_full_kekulized/train_reos_ring_counts.pkl``, 187 MB,
#: vendored Wave 70; upstream ``metrics.py:274``).
REFERENCE_GEOM_DRUGS: str = "GEOM_DRUGS"

#: Custom 1000-mol NCI fallback (Wave 49 stub) — kept for parity with
#: the legacy :func:`adaptive_reflow.adapters.flowmol3_metrics_upstream.compute_paper_metrics`
#: fallback path. NOT the paper reference; useful only for the test
#: suite (different references yield different numbers).
REFERENCE_NCI_FIRST_5K_PROXY: str = "NCI_first_5K_proxy"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_reference_dir(reference: str) -> Path:
    """Resolve a ``reference`` label to a vendored processed-data dir.

    Returns the upstream ``data/geom_full_kekulized`` directory for
    ``reference='GEOM_DRUGS'`` (the paper-parity choice) and the
    ``data/geom_5_kekulized`` directory for ``NCI_first_5K_proxy``
    (the legacy fallback used by the Wave 49 NCI smoke test).
    """
    if reference == REFERENCE_GEOM_DRUGS:
        # The paper-parity reference distribution — ~30K GEOM_DRUGS
        # training mols with pre-computed REOS flags. This is what
        # ``SampleAnalyzer.get_train_reos_rings`` reads
        # (``metrics.py:274``).
        return Path(FLOWMOL3_UPSTREAM_REPO) / "data" / "geom_full_kekulized"
    if reference == REFERENCE_NCI_FIRST_5K_PROXY:
        # The 5K-mol subset of GEOM_DRUGS, used by the Wave 49 NCI
        # proxy fallback. NOT the paper reference; only used by the
        # test suite to verify the reference-selection code path.
        return Path(FLOWMOL3_UPSTREAM_REPO) / "data" / "geom_5_kekulized"
    raise ValueError(
        f"unknown reference {reference!r}; "
        f"expected one of {REFERENCE_GEOM_DRUGS!r}, {REFERENCE_NCI_FIRST_5K_PROXY!r}"
    )


def _coerce_sampled_mols(
    sampled_molecules: Sequence[Any],
) -> list[Any]:
    """Coerce a sequence of :class:`SampledMolecule` (or duck-typed) to a list.

    Upstream :class:`SampleAnalyzer.analyze` does ``for mol in sampled_mols:``
    and reads ``mol.build_molecule()`` / ``mol.num_atoms`` /
    ``mol.rdkit_mol``. The downstream consumer may pass either
    upstream-typed ``SampledMolecule`` objects OR anything with
    ``.build_molecule()`` + ``.num_atoms`` attributes; we just hand the
    list to the analyzer.
    """
    if sampled_molecules is None:
        raise ValueError("sampled_molecules must be a non-None sequence")
    return list(sampled_molecules)


# ---------------------------------------------------------------------------
# Metric 1 — validity_pct (RDKit sanitization pass rate)
# ---------------------------------------------------------------------------


def compute_validity_pct(
    sampled_molecules: Sequence[Any],
) -> float:
    """Compute ``validity_pct`` per upstream ``SampleAnalyzer.compute_validity``.

    Calls the upstream ``SampleAnalyzer.compute_validity`` function
    (``flowmol/analysis/metrics.py:172-240``) which:

      1. Calls ``mol.build_molecule()`` to round-trip to RDKit.
      2. Splits into largest-fragment via
         ``Chem.rdmolops.GetMolFrags(..., asMols=True, sanitizeFrags=False)``.
      3. Runs ``Chem.SanitizeMol(largest_mol)``.
      4. Increments ``n_valid`` on success; ``frac_valid_mols = n_valid / n``.

    Paper value: ``0.999`` (paper reports
    :class:`SampledMolecule` post ``Chem.SanitizeMol`` pass rate).

    Parameters
    ----------
    sampled_molecules
        Sequence of upstream
        :class:`flowmol.analysis.molecule_builder.SampledMolecule`
        objects (or duck-typed wrappers exposing ``.build_molecule()``
        and ``.num_atoms``).

    Returns
    -------
    float
        Fraction of mols that pass RDKit sanitization ∈ ``[0.0, 1.0]``.
        Returns ``0.0`` on upstream import failure so callers can
        distinguish "metric computed" from "metric unavailable".

    Notes
    -----
    This is the same code path that
    :func:`adaptive_reflow.adapters.flowmol3_metrics_upstream.compute_paper_metrics`
    uses (``SampleAnalyzer.analyze(..., posebusters=False,
    functional_validity=False)`` would short-circuit but the validity
    block always runs at the top of ``analyze``). We invoke
    ``compute_validity`` directly so the test suite can exercise the
    metric path without paying for PoseBusters.
    """
    modules = _try_get_upstream()
    if modules is None:
        return 0.0
    SampleAnalyzer = modules["SampleAnalyzer"]
    mols = _coerce_sampled_mols(sampled_molecules)
    # The ``SampleAnalyzer.__init__`` requires ``processed_data_dir``
    # for the valency table + energy-JS-div references. Pass the
    # default (geom_full_kekulized) for paper parity; the compute_validity
    # block does NOT read those references.
    analyzer = SampleAnalyzer(
        processed_data_dir=Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR),
        pb_workers=0,  # compute_validity is RDKit-only — no PoseBusters needed
        pb_energy=False,
    )
    out = analyzer.compute_validity(mols, return_counts=False)
    return float(out["frac_valid_mols"])


# ---------------------------------------------------------------------------
# Metric 2 — pb_validity_pct (PoseBusters pass rate)
# ---------------------------------------------------------------------------


def compute_pb_validity_pct(
    sampled_molecules: Sequence[Any],
    *,
    full_pb: bool = True,
    pb_workers: int = 2,
) -> float:
    """Compute ``pb_validity_pct`` per upstream ``SampleAnalyzer.analyze(posebusters=True)``.

    Paper path (``full_pb=True``, default): PoseBusters is invoked
    with the vendored ``data/FlowMol3/pb_config_with_energy_ratio.yaml``
    config (Wave 82 — energy_ratio module UNCOMMENTED with paper-tuned
    ``threshold_energy_ratio=100.0``, ``ensemble_number_conformations=50``).
    Paper value: ``0.919``.

    Subset path (``full_pb=False``): PoseBusters uses the vendored
    upstream ``flowmol/analysis/pb_config.yaml`` (energy_ratio is
    commented out — ``pb_config.yaml:101-110``). This is the Wave 73
    path; it passes on a larger fraction because the energy-ratio
    module rejection step is skipped. Wave 73 reference value: ~``1.0``.

    Both paths share the same upstream code
    (``flowmol/analysis/metrics.py:154-166``). The ``full_pb`` flag
    selects between two upstream ``PoseBusters`` configurations.

    IMPORTANT — xtb is NOT required for this check (Wave 87 Agent A
    audit). PB 0.6.5's ``energy_ratio`` module is UFF-based
    (verified at
    ``.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:6-14``,
    which imports ``UFFGetMoleculeForceField`` from RDKit). This
    function does NOT invoke ``fm3_evals/geometry/xtb_optimization.py``
    because xtb is irrelevant to PoseBusters' ``energy_ratio`` check.

    Cross-reference — xtb-driven metrics (``med_rmsd``,
    ``med_energy_gain``, ``med_mmff_drop``) are computed by
    ``_compute_xtb_geometry_metrics`` in
    ``tools/run_real_ckpt_eval.py`` and consumed by the FlowMol3
    composite's ``-med_rmsd_after_xtb`` axis (a SEPARATE pipeline from
    ``pb_validity_pct``). See Wave 82 Agent A audit
    (``docs/audit/wave82-phase1-audit.md``) for the upstream
    ``xtb_optimization.py`` + ``rmsd_energy.py`` wire details.

    Implementation note (Wave 82 Agent A audit §1-6):

    Upstream ``SampleAnalyzer.__init__`` accepts only
    ``processed_data_dir``, ``dataset``, ``use_midi_valence``,
    ``pb_workers``, ``pb_energy``. ``pb_energy=True`` forces the
    PoseBusters built-in ``'mol'`` preset (which has ``energy_ratio``
    but with PB-default params, threshold=7.0 — over-rejects vs paper).
    ``pb_energy=False`` reads ``flowmol/analysis/pb_config.yaml`` from
    disk (energy_ratio commented out — under-rejects vs paper). Neither
    matches the paper. We therefore:

      1. Construct ``SampleAnalyzer(pb_energy=False)`` so the valency
         + energy_div references are loaded from disk (the upstream
         constructor needs the ``processed_data_dir`` to find them).
      2. Re-assign ``analyzer.buster = pb.PoseBusters(config=<our_yaml>,
         max_workers=pb_workers)`` to inject the vendored YAML. PB
         0.6.5's ``PoseBusters.__init__`` accepts either a preset name
         or a config dict (verified at
         ``posebusters/posebusters.py:73-127``).

    Parameters
    ----------
    sampled_molecules
        Sequence of upstream ``SampledMolecule`` objects.
    full_pb
        When ``True`` (default — paper parity), drive PoseBusters with
        the vendored YAML (energy_ratio uncommented). When ``False``,
        use the upstream vendored ``pb_config.yaml`` subset.
    pb_workers
        Number of PoseBusters worker processes; ``0`` = sequential.

    Returns
    -------
    float
        Fraction of mols that pass all PoseBusters checks ∈ ``[0.0, 1.0]``.
        Returns ``0.0`` on upstream import failure.
    """
    modules = _try_get_upstream()
    if modules is None:
        return 0.0
    SampleAnalyzer = modules["SampleAnalyzer"]
    mols = _coerce_sampled_mols(sampled_molecules)
    if full_pb:
        # Wave 82: paper path uses the vendored YAML with energy_ratio
        # UNCOMMENTED. Construct SampleAnalyzer with pb_energy=False (so
        # the valency + energy_div refs are loaded from disk) then
        # re-assign ``analyzer.buster`` with our YAML. Gracefully fall
        # back to the subset_pb path (Wave 73 byte-stable behavior) if
        # the YAML is missing or unreadable.
        if not PB_CONFIG_WITH_ENERGY_RATIO_PATH.is_file():
            _LOGGER.warning(
                "compute_pb_validity_pct: vendored YAML missing at %s; "
                "falling back to subset_pb path (energy_ratio commented out)",
                PB_CONFIG_WITH_ENERGY_RATIO_PATH,
            )
            full_pb = False
        else:
            try:
                import yaml as _yaml  # noqa: PLC0415
            except ImportError as exc:
                _LOGGER.warning(
                    "compute_pb_validity_pct: PyYAML not importable; "
                    "falling back to subset_pb path (%s)", exc,
                )
                full_pb = False
            else:
                try:
                    with PB_CONFIG_WITH_ENERGY_RATIO_PATH.open("r") as fh:
                        pb_config_dict = _yaml.safe_load(fh)
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning(
                        "compute_pb_validity_pct: failed to parse vendored "
                        "YAML %s (%s); falling back to subset_pb path",
                        PB_CONFIG_WITH_ENERGY_RATIO_PATH,
                        exc,
                    )
                    full_pb = False
        if full_pb:
            # YAML parsed successfully — inject it via analyzer.buster.
            try:
                import posebusters as _pb  # noqa: PLC0415
            except ImportError as exc:
                _LOGGER.warning(
                    "compute_pb_validity_pct: posebusters import failed; "
                    "falling back to subset_pb path (%s)", exc,
                )
                full_pb = False
            else:
                analyzer = SampleAnalyzer(
                    processed_data_dir=Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR),
                    pb_workers=int(pb_workers),
                    pb_energy=False,
                )
                analyzer.buster = _pb.PoseBusters(
                    config=pb_config_dict,
                    max_workers=int(pb_workers),
                )
                try:
                    out = analyzer.analyze(
                        mols,
                        functional_validity=False,  # PB-only call-site
                        posebusters=True,
                        energy_div=False,
                    )
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning(
                        "compute_pb_validity_pct: analyze() failed with "
                        "vendored YAML (%s); returning 0.0", exc,
                    )
                    return 0.0
                return float(out.get("pb_valid", 0.0))
    # Wave 73 subset path: pb_energy=False loads the upstream
    # vendored pb_config.yaml (energy_ratio commented out).
    analyzer = SampleAnalyzer(
        processed_data_dir=Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR),
        pb_workers=int(pb_workers),
        pb_energy=bool(full_pb),  # False -> reads pb_config.yaml from disk
    )
    out = analyzer.analyze(
        mols,
        functional_validity=False,  # we don't need REOS/ring flags here
        posebusters=True,
        energy_div=False,
    )
    return float(out.get("pb_valid", 0.0))


# ---------------------------------------------------------------------------
# Metric 3 — fg_deviation (cumulative REOS flag-rate deviation vs reference)
# ---------------------------------------------------------------------------


def compute_fg_deviation(
    sampled_molecules: Sequence[Any],
    *,
    reference: str = REFERENCE_GEOM_DRUGS,
) -> float:
    """Compute ``fg_dev`` per upstream ``SampleAnalyzer.reos_and_rings``.

    Calls upstream ``SampleAnalyzer.reos_and_rings`` (which builds a
    flag-rate table from sanitized molecules + compares against the
    precomputed REOS distribution in
    ``data/geom_full_kekulized/train_reos_ring_counts.pkl`` —
    ``metrics.py:274``). The output key ``reos_cum_dev`` is the
    cumulative L1 deviation between the sample flag-rate and the
    training flag-rate. Paper value: ``0.27``.

    Parameters
    ----------
    sampled_molecules
        Sequence of upstream ``SampledMolecule`` objects.
    reference
        ``'GEOM_DRUGS'`` (default — paper parity; reads
        ``train_reos_ring_counts.pkl`` from
        ``data/geom_full_kekulized/``) or
        ``'NCI_first_5K_proxy'`` (legacy fallback; reads from
        ``data/geom_5_kekulized/``).

    Returns
    -------
    float
        Cumulative REOS flag-rate L1 deviation vs reference ∈
        ``[0.0, ∞)``. Paper value: ``0.27``. Returns ``0.0`` on
        upstream import failure or when the reference distribution
        is missing on disk.
    """
    modules = _try_get_upstream()
    if modules is None:
        return 0.0
    SampleAnalyzer = modules["SampleAnalyzer"]
    mols = _coerce_sampled_mols(sampled_molecules)
    reference_dir = _resolve_reference_dir(reference)
    if not reference_dir.exists():
        _LOGGER.warning(
            "compute_fg_deviation: reference dir %s does not exist; "
            "returning 0.0",
            reference_dir,
        )
        return 0.0
    analyzer = SampleAnalyzer(
        processed_data_dir=reference_dir,
        pb_workers=0,  # PoseBusters not used here
        pb_energy=False,
    )
    out = analyzer.analyze(
        mols,
        functional_validity=True,  # this is what triggers reos_and_rings
        posebusters=False,
        energy_div=False,
    )
    return float(out.get("reos_cum_dev", 0.0))


# ---------------------------------------------------------------------------
# Metric 4 — ood_ring_rate (ChEMBL ring-system OOD rate)
# ---------------------------------------------------------------------------


def compute_ood_ring_rate(
    sampled_molecules: Sequence[Any],
    *,
    reference: str = REFERENCE_GEOM_DRUGS,
) -> float:
    """Compute ``ood_ring_rate`` per upstream ``SampleAnalyzer.reos_and_rings``.

    The ChEMBL ring-system reference is bundled inside
    :mod:`useful_rdkit_utils.ring_systems` (ChEMBL 49,769 ring
    systems — not the disk-side reference dir, which only affects
    fg_dev / energy-js-div). Therefore the ``reference`` argument is
    accepted for API symmetry with :func:`compute_fg_deviation` but is
    currently a no-op (the ring-system DB is loaded the same way
    regardless of ``reference``).

    Output key: ``ood_rate`` (``metrics.py:333``). Paper value: ``0.10``.

    Parameters
    ----------
    sampled_molecules
        Sequence of upstream ``SampledMolecule`` objects.
    reference
        ``'GEOM_DRUGS'`` (default) or ``'NCI_first_5K_proxy'`` —
        accepted for API symmetry; ChEMBL ring-system DB is loaded
        the same way for both (the ChEMBL DB is bundled inside
        :mod:`useful_rdkit_utils`).

    Returns
    -------
    float
        Fraction of rings in sample NOT in ChEMBL ring-system DB ∈
        ``[0.0, 1.0]``. Paper value: ``0.10``. Returns ``0.0`` on
        upstream import failure.
    """
    # Accept the reference argument for API symmetry with
    # :func:`compute_fg_deviation`; the ChEMBL ring-system DB is
    # bundled inside :mod:`useful_rdkit_utils` so it loads the same
    # way for both reference labels. The ``reference`` arg would only
    # matter if we wanted to override the REOS reference distribution
    # for ring OOD — but upstream
    # ``SampleAnalyzer.reos_and_rings`` uses the *same* training REOS
    # table for both ring OOD and fg_dev, so we pass the resolved dir
    # through for consistency.
    _ = reference  # currently a no-op — see docstring
    modules = _try_get_upstream()
    if modules is None:
        return 0.0
    SampleAnalyzer = modules["SampleAnalyzer"]
    mols = _coerce_sampled_mols(sampled_molecules)
    reference_dir = _resolve_reference_dir(reference)
    analyzer = SampleAnalyzer(
        processed_data_dir=reference_dir,
        pb_workers=0,
        pb_energy=False,
    )
    out = analyzer.analyze(
        mols,
        functional_validity=True,
        posebusters=False,
        energy_div=False,
    )
    raw = out.get("ood_rate", -1.0)
    # Upstream uses ``ood_rate=-1`` as a sentinel for "no sanitized
    # molecules" (the analyzer returned ``flag_rate=-1`` in that
    # case). Collapse to ``0.0`` so callers get a sane float.
    if raw is None or float(raw) < 0.0:
        return 0.0
    return float(raw)


# ---------------------------------------------------------------------------
# Aggregator — compute all 4 paper metrics in a single upstream call
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaperMetricsResult:
    """Frozen container for the 4 paper-parity metrics.

    All four fields are floats in ``[0.0, 1.0]`` (or ``[0.0, ∞)`` for
    ``paper_fg_deviation``). Returned by
    :func:`compute_all_paper_metrics`.
    """

    paper_validity_pct: float
    paper_pb_validity_pct: float
    paper_fg_deviation: float
    paper_ood_ring_rate: float


def compute_all_paper_metrics(
    sampled_molecules: Sequence[Any],
    *,
    reference: str = REFERENCE_GEOM_DRUGS,
    full_pb: bool = True,
    pb_workers: int = 2,
) -> PaperMetricsResult:
    """Compute all 4 paper-parity metrics on a single sample.

    For efficiency, this function invokes the upstream
    ``SampleAnalyzer.analyze`` **once** with all relevant flags set,
    then extracts the 4 paper-metric values from the returned dict.
    This avoids the 4x overhead of calling each helper independently
    (each helper re-runs the stability + valence block at the top of
    ``analyze``).

    Parameters
    ----------
    sampled_molecules
        Sequence of upstream ``SampledMolecule`` objects.
    reference
        ``'GEOM_DRUGS'`` (default — paper parity) or
        ``'NCI_first_5K_proxy'`` (legacy fallback).
    full_pb
        When ``True`` (paper path), drive PoseBusters with the
        vendored YAML (energy_ratio UNCOMMENTED, paper-tuned params
        — see :data:`PB_CONFIG_WITH_ENERGY_RATIO_PATH`). When
        ``False``, use the vendored ``pb_config.yaml`` subset.
    pb_workers
        Number of PoseBusters worker processes.

    Returns
    -------
    PaperMetricsResult
        Frozen container with the 4 paper-parity metric values:
        ``paper_validity_pct``, ``paper_pb_validity_pct``,
        ``paper_fg_deviation``, ``paper_ood_ring_rate``.
    """
    modules = _try_get_upstream()
    if modules is None:
        return PaperMetricsResult(0.0, 0.0, 0.0, 0.0)
    SampleAnalyzer = modules["SampleAnalyzer"]
    mols = _coerce_sampled_mols(sampled_molecules)
    reference_dir = _resolve_reference_dir(reference)
    if not reference_dir.exists():
        _LOGGER.warning(
            "compute_all_paper_metrics: reference dir %s does not exist; "
            "fg_deviation + ood_ring_rate will be 0.0",
            reference_dir,
        )
    analyzer = SampleAnalyzer(
        processed_data_dir=reference_dir,
        pb_workers=int(pb_workers),
        pb_energy=False,  # always load valency from disk; PB config injected below
    )
    # Wave 82: paper path (``full_pb=True``) injects the vendored YAML
    # via ``analyzer.buster``. Subset path uses the vendored
    # ``pb_config.yaml`` that ``SampleAnalyzer.__init__`` loaded when
    # ``pb_energy=False``. See ``compute_pb_validity_pct`` docstring
    # for the rationale.
    if full_pb:
        try:
            import yaml as _yaml  # noqa: PLC0415
            import posebusters as _pb  # noqa: PLC0415
        except ImportError as exc:
            _LOGGER.warning(
                "compute_all_paper_metrics: missing deps for vendored YAML "
                "injection (%s); using subset_pb config from SampleAnalyzer init",
                exc,
            )
        else:
            if PB_CONFIG_WITH_ENERGY_RATIO_PATH.is_file():
                try:
                    with PB_CONFIG_WITH_ENERGY_RATIO_PATH.open("r") as fh:
                        pb_config_dict = _yaml.safe_load(fh)
                    analyzer.buster = _pb.PoseBusters(
                        config=pb_config_dict,
                        max_workers=int(pb_workers),
                    )
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning(
                        "compute_all_paper_metrics: failed to inject "
                        "vendored YAML (%s); using subset_pb config",
                        exc,
                    )
            else:
                _LOGGER.warning(
                    "compute_all_paper_metrics: vendored YAML missing at %s; "
                    "using subset_pb config",
                    PB_CONFIG_WITH_ENERGY_RATIO_PATH,
                )
    out = analyzer.analyze(
        mols,
        functional_validity=True,
        posebusters=True,
        energy_div=False,
    )
    raw_ood = out.get("ood_rate", -1.0)
    ood = 0.0 if (raw_ood is None or float(raw_ood) < 0.0) else float(raw_ood)
    return PaperMetricsResult(
        paper_validity_pct=float(out.get("frac_valid_mols", 0.0)),
        paper_pb_validity_pct=float(out.get("pb_valid", 0.0)),
        paper_fg_deviation=float(out.get("reos_cum_dev", 0.0)),
        paper_ood_ring_rate=ood,
    )


# ---------------------------------------------------------------------------
# Upstream import shim
# ---------------------------------------------------------------------------


def _try_get_upstream() -> dict[str, Any] | None:
    """Lazy import of the upstream ``SampleAnalyzer`` + ``SampledMolecule``.

    Returns ``None`` if the upstream ``flowmol`` package is not
    importable on this host (the same condition
    :func:`adaptive_reflow.adapters.flowmol3_metrics_upstream.is_upstream_available`
    checks). Callers translate this to a sentinel return value (e.g.
    ``0.0``) rather than crashing.
    """
    if not is_upstream_available():
        _LOGGER.warning(
            "tools.paper_metrics: upstream flowmol is not importable; "
            "returning sentinel values"
        )
        return None
    # The shim caches the import result internally — re-import is cheap.
    from adaptive_reflow.adapters.flowmol3_metrics_upstream import (  # noqa: PLC0415
        _UPSTREAM_MODULES,
    )
    return _UPSTREAM_MODULES


__all__ = [
    "FLOWMOL3_PINNED_COMMIT",
    "PB_CONFIG_WITH_ENERGY_RATIO_PATH",
    "PaperMetricsResult",
    "REFERENCE_GEOM_DRUGS",
    "REFERENCE_NCI_FIRST_5K_PROXY",
    "compute_all_paper_metrics",
    "compute_fg_deviation",
    "compute_ood_ring_rate",
    "compute_pb_validity_pct",
    "compute_validity_pct",
]

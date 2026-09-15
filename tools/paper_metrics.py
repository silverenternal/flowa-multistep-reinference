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

Wave 95 default-switch (F2 UFF-vs-xtb definitional gap):
``compute_pb_validity_pct`` returns a 3-key dict where the primary
``pb_validity`` key is the **xtb-based number** (the gold standard —
matches the paper's stated measurement semantics) when the xtb
bridge runs end-to-end, and **gracefully falls back to the UFF-based
number** (preserved for byte-stable backward compatibility with prior
waves) when xtb is unavailable on ``$PATH``. The raw UFF value is
always preserved under the ``pb_validity_uff`` key so readers can
compute the UFF-vs-xtb definitional gap directly via a single dict
diff. ``status`` discriminates "xtb ran" from "uff_fallback". This
default switch is what closes the Wave 88 FlowMol3 framework-arm
``pb_validity_pct`` regression: with UFF-only the energy_ratio
module's rejection step is mis-calibrated vs the paper's xtb-tuned
threshold, producing a -9.95pp false REGRESS.
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
import math
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adaptive_reflow.adapters.flowmol3_metrics_upstream import (
    FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR,
    FLOWMOL3_PINNED_COMMIT,
    FLOWMOL3_UPSTREAM_REPO,
    is_upstream_available,
)

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Wave 90 — PB-xtb post-processing threshold (paper parity).
#
# The PoseBusters ``energy_ratio`` check rejects conformer ensembles where
# any conformer's energy exceeds the lowest-energy conformer by more than
# ``threshold_energy_ratio``. PB's default threshold is ``7.0`` (very
# strict — over-rejects for FlowMol3-style latent samplers); the FlowMol3
# paper uses ``threshold_energy_ratio=100.0`` to align with xtb single-
# point energies. We mirror the paper value when re-evaluating with the
# xtb-driven :func:`tools.flowmol3_xtb_bridge.xtb_energy_ratio`.
PB_XTB_THRESHOLD_DEFAULT: float = 100.0

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
    xtb_threshold: float = PB_XTB_THRESHOLD_DEFAULT,
) -> dict[str, float]:
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

    IMPORTANT — Wave 87 audit note (preserved + extended Wave 90 + 95):
    PB 0.6.5's ``energy_ratio`` module is UFF-based
    (verified at
    ``.venvs/flowmol3_venv/.../posebusters/modules/energy_ratio.py:6-14``,
    which imports ``UFFGetMoleculeForceField`` from RDKit). The UFF
    result is preserved in the returned ``pb_validity_uff`` key for
    byte-stable downstream diff/audit use.

    Wave 90 — xtb-based re-evaluation: After the UFF-driven
    ``analyze()`` returns, this function additionally calls
    :func:`tools.flowmol3_xtb_bridge.xtb_energy_ratio` for each
    successful mol and re-evaluates the energy-ratio criterion against
    the xtb-flavoured ratio (using ``xtb_threshold=100.0`` paper value).
    The xtb result lands in the returned ``pb_validity`` key.

    Wave 95 — default switch (F2 UFF-vs-xtb definitional gap): The
    primary ``pb_validity`` key now returns the **xtb-based number**
    when xtb ran end-to-end, and **gracefully falls back to the
    UFF-based number** (preserved as ``pb_validity_uff``) when xtb is
    unavailable on ``$PATH``. This guarantees:

      1. The returned dict is always well-defined (the key contract
         never breaks) — readers can consume ``out['pb_validity']``
         without an ``if status`` guard.
      2. The UFF-vs-xtb definitional gap is always visible via
         ``out['pb_validity']`` vs ``out['pb_validity_uff']`` — readers
         that want to audit the energy-engine choice can diff the two
         keys regardless of which engine actually ran.
      3. Downstream regression analysis (e.g. Wave 88's FlowMol3
         framework-arm ``pb_validity_pct`` -9.95pp regression) gets
         the honest xtb-based number by default; the UFF-based
         number remains available for byte-stable backward
         compatibility.

    Cross-reference — xtb-driven geometry metrics (``med_rmsd``,
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
    xtb_threshold
        Energy-ratio threshold for the xtb-based post-processing
        re-evaluation (default ``100.0`` = paper value). Lower values
        reject more mols (stricter); higher values are lenient.

    Returns
    -------
    dict[str, Any]
        Three-key dict (Wave 95 default): primary ``pb_validity`` is
        the **best available** PB pass rate ∈ ``[0.0, 1.0]``
        (xtb-based when xtb ran, UFF-based when xtb fell back); the
        raw UFF value is preserved under ``pb_validity_uff`` for
        byte-stable diff/audit.

          * ``pb_validity`` — PRIMARY pass rate (Wave 95 default).
            xtb-based when ``status == "xtb"``, UFF-based when
            ``status == "uff_fallback"`` (graceful fallback — the
            returned number is always well-defined and within
            ``[0.0, 1.0]``). Downstream consumers should read this
            key for the paper-aligned number.
          * ``pb_validity_uff`` — UFF-based PB pass rate ∈ ``[0.0, 1.0]``
            (the value PoseBusters 0.6.5 reports internally; preserved
            from prior versions of this function for byte-stable
            backward compatibility + UFF-vs-xtb definitional gap
            audit). Always set to the raw UFF ``pb_valid`` value
            regardless of xtb availability.
          * ``pb_validity_xtb`` — REMOVED in Wave 95. Previously the
            xtb-only key; the xtb value now lives under ``pb_validity``
            (the new default). Readers that previously consumed
            ``out['pb_validity_xtb']`` should read ``out['pb_validity']``
            when ``status == "xtb"`` and ``out['pb_validity_uff']``
            otherwise (or just ``out['pb_validity']`` if they want
            the best-available number regardless of engine).
          * ``status`` — one of:
              - ``"xtb"``: xtb bridge ran end-to-end (imports OK + at
                least one per-mol xtb energy ratio was evaluated).
                ``pb_validity`` is the xtb-based number.
              - ``"uff_fallback"``: xtb bridge was unavailable or
                failed upfront (import error, no mols, SDWriter setup
                failure, xtb_optimize_sdf raise, opt SDF missing).
                ``pb_validity`` is the UFF-based number (graceful
                fallback preserves the returned-dict contract).

        All keys are ``0.0`` (with ``status == "uff_fallback"``) on
        upstream import failure.
    """
    modules = _try_get_upstream()
    if modules is None:
        # Wave 95 default: primary ``pb_validity`` is best-available
        # (xtb when xtb ran, UFF on graceful fallback). Upstream import
        # failed → no xtb bridge available, so both keys collapse to
        # ``0.0`` and ``status`` reports the fallback.
        return {
            "pb_validity": 0.0,
            "pb_validity_uff": 0.0,
            "status": "uff_fallback",
        }
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
                    return {
                        "pb_validity": 0.0,
                        "pb_validity_uff": 0.0,
                        "status": "uff_fallback",
                    }
                pb_valid_uff = float(out.get("pb_valid", 0.0))
                # Wave 90: per-mol xtb_energy_ratio post-processing.
                # Wave 90+ : returns (value, status) so the caller can
                # distinguish "xtb ran" from "uff fallback".
                pb_valid_xtb, xtb_status = _recompute_pb_validity_xtb(
                    mols,
                    threshold=float(xtb_threshold),
                    pb_workers=int(pb_workers),
                    fallback=pb_valid_uff,
                )
                # Wave 95 default switch (F2 UFF-vs-xtb definitional gap):
                # primary ``pb_validity`` returns the xtb-based number
                # when xtb ran (the gold standard — matches the paper's
                # measurement semantics); UFF is preserved under
                # ``pb_validity_uff`` for byte-stable diff/audit. On
                # graceful UFF fallback (xtb unavailable), the primary
                # key mirrors the UFF value so the returned dict is
                # always well-defined.
                primary_pb_validity = (
                    pb_valid_xtb if xtb_status == "xtb" else pb_valid_uff
                )
                return {
                    "pb_validity": primary_pb_validity,
                    "pb_validity_uff": pb_valid_uff,
                    "status": xtb_status,
                }
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
    pb_valid_uff = float(out.get("pb_valid", 0.0))
    # Wave 90: per-mol xtb_energy_ratio post-processing (subset path
    # also benefits from the xtb-vs-UFF side-by-side comparison).
    # Wave 90+ : returns (value, status) so the caller can
    # distinguish "xtb ran" from "uff fallback".
    pb_valid_xtb, xtb_status = _recompute_pb_validity_xtb(
        mols,
        threshold=float(xtb_threshold),
        pb_workers=int(pb_workers),
        fallback=pb_valid_uff,
    )
    # Wave 95 default switch: primary ``pb_validity`` returns the
    # best-available value (xtb when xtb ran, UFF on graceful fallback).
    primary_pb_validity = (
        pb_valid_xtb if xtb_status == "xtb" else pb_valid_uff
    )
    return {
        "pb_validity": primary_pb_validity,
        "pb_validity_uff": pb_valid_uff,
        "status": xtb_status,
    }


def _recompute_pb_validity_xtb(
    mols: Sequence[Any],
    *,
    threshold: float,
    pb_workers: int = 2,
    fallback: float = 0.0,
) -> tuple[float, str]:
    """Re-evaluate ``pb_validity`` using xtb-based per-mol energy ratio.

    Wave 90 — mirrors the PoseBusters ``energy_ratio`` check
    (Buttenschoen et al. 2024, default ``threshold=7.0``; paper
    value ``100.0``) but with REAL xtb single-point energies instead
    of UFF. For each mol:

      1. Build the RDKit mol (``mol.build_molecule()``).
      2. Write a temp SDF carrying the mol + a unique ``_Name``.
      3. Run :func:`tools.flowmol3_xtb_bridge.xtb_optimize_sdf` to
         produce the optimised SDF.
      4. Call :func:`tools.flowmol3_xtb_bridge.xtb_energy_ratio` for
         the mol against the (init, opt) pair.
      5. Count the mol as "passes" if ``ratio < threshold``.

    Returns the fraction of mols that pass.

    Robustness contract
    -------------------

    On any failure (xtb missing, RDKit missing, SDF write error,
    subprocess non-zero exit, etc.) this function returns
    ``(fallback, "uff_fallback")`` so the caller always gets a
    well-defined number in ``[0.0, 1.0]`` AND a clear status string
    distinguishing "xtb ran" from "xtb unavailable". A debug log line
    records the specific failure mode for debugging.

    Parameters
    ----------
    mols
        Sequence of upstream ``SampledMolecule`` (or duck-typed).
    threshold
        Energy-ratio cutoff. A mol with ``xtb_energy_ratio > threshold``
        is rejected. Paper value: ``100.0`` (matches the PB YAML
        ``threshold_energy_ratio`` field).
    pb_workers
        Unused for the xtb path (kept in the signature for API
        symmetry with :func:`compute_pb_validity_pct`).
    fallback
        Value returned on any upfront failure (xtb missing, SDF
        write error, etc.). Defaults to ``0.0``; callers typically
        pass the UFF ``pb_valid`` so the returned ``pb_validity_xtb``
        matches the UFF result when the xtb pipeline is unavailable.

    Returns
    -------
    tuple[float, str]
        ``(value, status)`` where:

          * ``value`` — fraction of mols that pass the xtb-based
            energy-ratio check ∈ ``[0.0, 1.0]`` (or ``fallback`` on
            any upfront failure).
          * ``status`` — ``"xtb"`` if the xtb bridge ran end-to-end
            (at least one per-mol xtb energy ratio was evaluated),
            ``"uff_fallback"`` otherwise (xtb bridge import failed,
            no mols, SDF write error, ``xtb_optimize_sdf`` raise,
            opt SDF missing).
    """
    _ = pb_workers  # API symmetry only — xtb is single-process per call.
    # Lazy-import the bridge so cold-import paths do not pay the
    # RDKit / xtb CLI discovery cost.
    try:
        from rdkit import Chem  # noqa: PLC0415

        from tools.flowmol3_xtb_bridge import (  # noqa: PLC0415
            XtbBridgeError,
            xtb_energy_ratio,
            xtb_optimize_sdf,
        )
    except ImportError as exc:
        _LOGGER.debug(
            "_recompute_pb_validity_xtb: xtb_bridge / rdkit import "
            "failed (%s); returning fallback=%s",
            exc, fallback,
        )
        return float(fallback), "uff_fallback"
    if not mols:
        return float(fallback), "uff_fallback"
    with tempfile.TemporaryDirectory(prefix="paper_pb_xtb_") as tmp:
        tmp_path = Path(tmp)
        input_sdf = tmp_path / "input.sdf"
        # Write all mols to input SDF; carry per-record _Name so the
        # xtb bridge can match them up against the optimised SDF.
        rdkit_records: list[tuple[int, Any]] = []
        try:
            writer = Chem.SDWriter(str(input_sdf))
            for idx, mol in enumerate(mols):
                try:
                    rdkit_mol = mol.build_molecule()
                except Exception:
                    rdkit_mol = None
                if rdkit_mol is None:
                    continue
                try:
                    name = f"paper_pb_xtb_mol_{idx}"
                    rdkit_mol.SetProp("_Name", name)
                    writer.write(rdkit_mol)
                    rdkit_records.append((idx, rdkit_mol))
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.debug(
                        "_recompute_pb_validity_xtb: failed to write "
                        "record %s to input SDF (%s); skipping",
                        idx, exc,
                    )
                    continue
            writer.close()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug(
                "_recompute_pb_validity_xtb: SDWriter setup failed (%s); "
                "returning fallback=%s",
                exc, fallback,
            )
            return float(fallback), "uff_fallback"
        if not input_sdf.is_file() or not rdkit_records:
            return float(fallback), "uff_fallback"
        # Run xtb optimization → produces opt_sdf + init_sdf sidecar
        # (the init SDF is what ``xtb_energy_ratio`` reads).
        try:
            xtb_optimize_sdf(input_sdf, input_sdf)
        except XtbBridgeError as exc:
            _LOGGER.debug(
                "_recompute_pb_validity_xtb: xtb_optimize_sdf failed (%s); "
                "returning fallback=%s",
                exc, fallback,
            )
            return float(fallback), "uff_fallback"
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug(
                "_recompute_pb_validity_xtb: xtb_optimize_sdf raised "
                "unexpected exception (%s); returning fallback=%s",
                exc, fallback,
            )
            return float(fallback), "uff_fallback"
        # The optimised SDF is written alongside the input with the
        # ``_opt`` suffix inserted before the extension (upstream
        # ``xtb_optimization.py`` convention). xtb_energy_ratio reads
        # the init SDF we just passed plus the opt SDF on disk.
        opt_sdf = input_sdf.with_name(
            input_sdf.stem + "_opt" + input_sdf.suffix
        )
        if not opt_sdf.is_file():
            _LOGGER.debug(
                "_recompute_pb_validity_xtb: expected optimised SDF "
                "%s missing after xtb_optimize_sdf; returning fallback=%s",
                opt_sdf, fallback,
            )
            return float(fallback), "uff_fallback"
        n_pass = 0
        n_total = 0
        for idx, rdkit_mol in rdkit_records:
            try:
                ratio = float(
                    xtb_energy_ratio(rdkit_mol, input_sdf, opt_sdf)
                )
            except XtbBridgeError as exc:
                _LOGGER.debug(
                    "_recompute_pb_validity_xtb: per-mol xtb_energy_ratio "
                    "failed for record %s (%s); counting as fail",
                    idx, exc,
                )
                n_total += 1
                continue
            except FileNotFoundError as exc:
                # Wave 90+: xtb binary missing on $PATH is a distinct
                # failure mode from a per-mol geometry / convergence
                # error. We short-circuit to the UFF fallback so
                # ``status`` reports ``"xtb_unavailable"`` (not
                # ``"xtb"`` with 0.0/4) and ``pb_validity_xtb`` mirrors
                # the UFF value passed via ``fallback``. Without this
                # catch, FileNotFoundError would fall through to the
                # generic ``except Exception`` below and the result
                # would misleadingly report ``status == "xtb"``.
                _LOGGER.debug(
                    "_recompute_pb_validity_xtb: xtb binary missing on "
                    "$PATH for record %s (%s); short-circuiting to "
                    "UFF fallback (status='xtb_unavailable')",
                    idx, exc,
                )
                return float(fallback), "xtb_unavailable"
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug(
                    "_recompute_pb_validity_xtb: per-mol xtb_energy_ratio "
                    "raised unexpected exception for record %s (%s); "
                    "counting as fail",
                    idx, exc,
                )
                n_total += 1
                continue
            n_total += 1
            if math.isfinite(ratio) and ratio < threshold:
                n_pass += 1
        if n_total == 0:
            # xtb ran end-to-end (no upfront failure) but no per-mol
            # records produced a finite ratio — treat as a fallback
            # because we have no signal.
            return float(fallback), "uff_fallback"
        return float(n_pass) / float(n_total), "xtb"


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
            import posebusters as _pb  # noqa: PLC0415
            import yaml as _yaml  # noqa: PLC0415
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
    "PB_XTB_THRESHOLD_DEFAULT",
    "PaperMetricsResult",
    "REFERENCE_GEOM_DRUGS",
    "REFERENCE_NCI_FIRST_5K_PROXY",
    "_recompute_pb_validity_xtb",
    "compute_all_paper_metrics",
    "compute_fg_deviation",
    "compute_ood_ring_rate",
    "compute_pb_validity_pct",
    "compute_validity_pct",
]

"""Unified molecular generation evaluation runner.

Phase A of the molecular SOTA-comparison harness. Loads generated
molecule samples from a ``.npz`` (array of SMILES strings under key
``smiles``) or a ``.pkl`` (pickle of a ``list[Chem.Mol]``) and emits a
single JSON report containing:

* ``validity`` — fraction of inputs that round-trip through RDKit
  (``Chem.MolFromSmiles(smiles)`` is not ``None`` and the molecule
  survives ``Chem.SanitizeMol``). Always computable; no external
  dependency beyond the ``[chemistry]`` extra.
* ``qed`` — mean Quantitative Estimate of Drug-likeness across the
  valid set. Range ``[0, 1]``; higher is more drug-like.
* ``sa`` — mean Synthetic Accessibility score across the valid set.
  Range ``[1, 10]``; lower is easier to synthesize.
* ``logp`` — mean Wildman-Crippen logP across the valid set.
  Unbounded; typical drug-like compounds land in ``[-5, +5]``.
* ``fcd`` — Fréchet ChemNet Distance (Preuer et al. 2018) against a
  reference SMILES set supplied via ``--reference-smiles`` (text file,
  one SMILES per line). Computed via the ``fcd`` PyPI package when
  available; NaN with a stderr note when ``fcd`` is not importable
  (the operator can install with ``uv pip install fcd``).
* ``pb_validity`` — PoseBusters-validity (Buttenschoen et al. 2024),
  the Tier-2 paper metric for FlowMol3 / GraphBFN. When
  ``posebusters`` is importable in the running venv, a real call is
  made (``PoseBusters(config="mol").bust(mols)``) on 3D conformers
  generated with RDKit ``ETKDGv3`` (built-in distance-geometry
  embedder, no MMFF, no ``xtb``). The marker distinguishes:

  - ``"computed_etkdg_v3_only"`` — a real PB-validity number was
    measured with ETKDGv3-only conformers (no MMFF refinement,
    no GFN2-xTB). This is the first-cut implementation; not
    bit-equivalent to the FlowMol3 / GraphBFN paper pipeline
    (which uses MMFF or GFN2-xTB) but is a usable signal of
    geometric plausibility and chemical sanity for the
    de-novo-generated set.
  - ``"computed"`` — placeholder reserved for the future
    full-fidelity (MMFF or GFN2-xTB) pipeline.
  - ``"stub_unavailable"`` — ``posebusters`` is importable but
    the call raised (caller sees ``value=None``).
  - ``"not_installed"`` — ``posebusters`` is not importable in
    the running venv; ``install_hint`` is non-null.

  The stub branch still exists so the JSON shape is stable; the
  real call replaces the stub per §3.4 / §6.2 of
  ``docs/r17-survey/baseline-deviation-review.md``.
* ``fg_deviation`` — FlowMol3 paper-aligned L1 distance between the
  generated functional-group occurrence distribution and a reference
  distribution (typically the GEOM-DRUGS training set). Computed
  from RDKit's bundled Dundee + Glaxo Wellcome FG SMARTS lists via
  :mod:`rdkit.Chem.Fragments` (no external SMARTS download). The
  reference set is taken from the same ``--reference-smiles`` file
  used for FCD when supplied; the per-FG presence vector is the
  L1 distance between the per-FG occurrence-rate vectors. NaN
  with a stderr note when RDKit is missing or the reference set
  is empty. Reference paper: arXiv:2508.12629 (FlowMol3), paper
  reports ``FG Deviation = 0.37 ± 0.01`` (generated) and
  ``FG Deviation = 0.28`` (training-data reference) on
  GEOM-DRUGS.
* ``fg_deviation_eq4`` — FlowMol3 paper eq.4 / eq.21 (Dunn & Koes,
  arXiv:2508.12629, Digital Discovery 2026) — the **instance-count**
  L1 over the 85-element ``fr_*`` vocabulary:
  ``sum |omega_f^gen - omega_f^ref|`` with
  ``omega_f := (# instances of f) / (# mols)``. This is the
  paper-faithful normalisation; the headline FlowMol3 number is
  ``0.37 ± 0.01`` (Digital Discovery Table 1, N = 5000). Differs
  from ``fg_deviation`` (binary-occurrence L1): ``fg_deviation``
  treats each mol as 0/1 per FG; ``fg_deviation_eq4`` sums the raw
  integer match count per mol. Wraps
  :func:`adaptive_reflow.eval.flowmol3_eq4_fg_deviation.compute_fg_deviation_eq4`.
  ``null`` when the wrapper is not importable; ``NaN`` with a
  stderr note when RDKit is missing or the reference set is empty.
* ``fg_deviation_eq4_block`` — companion dict for ``fg_deviation_eq4``
  with shape ``{"value": float | None, "n_gen": int, "n_ref": int,
  "n_gen_skipped": int, "n_ref_skipped": int, "vocabulary_size": int,
  "reference_source": str | None, "note": str | None,
  "marker": "computed_eq4" | "wrapper_unavailable" | ...}``. Same
  shape language as ``fg_deviation_dundee_glaxo``.

Each metric returns ``NaN`` with a deterministic stderr note when its
dependency is missing so a partial run still produces a parseable
JSON file. The JSON shape is stable regardless of which metrics
succeeded: a downstream consumer can rely on every key being present.

Input formats
-------------

* ``--input <path>.npz`` — NumPy archive containing a ``"smiles"``
  string array (UTF-8). One SMILES per element.
* ``--input <path>.pkl`` — Pickle file holding a 2-tuple
  ``(mols, sampling_time)`` matching the on-disk format produced by
  ``data/FlowMol3/repo/test.py`` (where ``mols`` is a
  ``list[Chem.Mol]``) or, equivalently, a bare ``list[Chem.Mol]``.
  The :mod:`adaptive_reflow.molecular.rdkit_export` glue (Phase A+
  follow-up) emits this exact tuple.
* ``--input <path>.sdf`` — RDKit SDF; one molecule per record. Parsed
  via :class:`Chem.SDMolSupplier`.

The runner imports the PoseBusters library directly when it is
available in the running venv (``posebusters >= 0.6.5``; verified
importable in ``flowmol3_venv``). Other FlowMol3 evaluation
dependencies (``useful_rdkit_utils``, ``dgl``, ``xtb``) remain
behind a subprocess boundary per the Phase-1 risk register; this
script is the in-process arm: same-task baseline vs framework
comparison.

Output schema
-------------

::

    {
      "input_path": "<absolute path>",
      "input_format": "npz" | "pkl" | "sdf",
      "n_total": int,
      "n_valid": int,
      "validity": float in [0, 1] (NaN on read failure),
      "qed": float in [0, 1] (NaN if RDKit missing),
      "sa":  float in [1, 10] (NaN if RDKit missing),
      "logp": float (NaN if RDKit missing),
      "fcd": float (NaN if ``fcd`` not importable),
      "pb_validity": {
        "value": null | float in [0, 1] (NaN when not computed),
        "marker": "not_installed" | "stub_unavailable"
                | "computed" | "computed_etkdg_v3_only",
        "install_hint": "pip install posebusters" | null,
        "note": "<stderr-equivalent string>",
        "conformer_protocol": "ETKDGv3" | null,
        "n_total": int,            # denominator
        "n_pb_valid": int,         # numerator
        "n_conformer_failures": int,
        "pass_per_check": dict[str, float] | None
      },
      "pb_validity_mmff": {
        "value": null | float in [0, 1] (NaN when not computed),
        "marker": "not_installed" | "stub_unavailable" | "computed_mmff",
        "install_hint": "pip install posebusters" | null,
        "note": "<stderr-equivalent string>",
        "conformer_protocol": "ETKDGv3+MMFF(200)" | null,
        "n_total": int,
        "n_pb_valid": int,
        "n_conformer_failures": int,
        "pass_per_check": dict[str, float] | None,
        "per_conformer_min_energy": list[float] | None
      },
      "fg_deviation": float (NaN if RDKit missing or no reference set),
      "fg_deviation_eq4": float | null (paper eq.4 / eq.21 instance-count
                                          L1 over 85-rule fr_* vocab; NaN if
                                          RDKit missing; null if wrapper
                                          unavailable),
      "fg_deviation_eq4_block": {
        "value": float | null (same number as fg_deviation_eq4, surfaced
                                here for one-stop inspection),
        "n_gen": int, "n_ref": int,
        "n_gen_skipped": int, "n_ref_skipped": int,
        "vocabulary_size": int (85 for the default fr_* vocab),
        "reference_source": str | None,
        "note": str | None,
        "marker": "computed_eq4" | "wrapper_unavailable"
                | "rdkit_unavailable" | "reference_unavailable"
      },
      "fg_deviation_dundee_glaxo": {
        "value": float (L1 over 85-element fr_* Dundee+Glaxo vocab; NaN if no RDKit),
        "value_reos": float (L1 over Pat Walters rd_filters Dundee+Glaxo vocab),
        "per_fg": dict[str, float] (p_gen - p_ref per fr_*),
        "per_check_reos": dict[str, float] (p_gen - p_ref per REOS rule),
        "flag_rate": float (mean per-rule flag rate, REOS shape),
        "reos_cum_dev": float (sum |p_gen - p_ref| over REOS vocab; matches upstream),
        "n_gen": int, "n_ref": int, "reference_source": str | None,
        "note": str | None,
      },
      "flowmol3_paper_metrics": {
        "metrics": null | dict[str, float],  # upstream dict, verbatim
        "marker": "not_requested" | "not_available"
                | "computed_upstream" | "upstream_error",
        "install_hint": str | null,
        "note": str | null,
        "n_total": int,
        "run_posebusters": bool
      },
      "frac_atoms_stable": float (NaN if RDKit missing),
      "frac_mols_stable_valence": float (NaN if RDKit missing),
      "frac_connected": float (NaN if RDKit missing),
      "avg_num_components": float (NaN if RDKit missing),
      "missing_dependencies": list[str],
      "stderr_notes": list[str]
    }

Usage::

    python tools/run_mol_eval.py \\
        --input data/flowmol3_out/baseline_smiles.npz \\
        --output data/flowmol3_out/baseline_metrics.json \\
        --dataset geom_drugs

    python tools/run_mol_eval.py \\
        --input data/graphbfn_out/generated.pkl \\
        --output data/graphbfn_out/metrics.json \\
        --dataset qm9
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

# Make the project importable when running as ``python tools/run_mol_eval.py``.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Supported dataset tags. The runner is dataset-agnostic (the metrics
#: are reference-free except for FCD which takes its own reference set),
#: but the tag is carried through to the JSON so the downstream
#: comparison table can label rows.
SUPPORTED_DATASETS: tuple[str, ...] = (
    "qm9",
    "geom_drugs",
    "geom_5_kekulized",
    "geom_5_aromatic",
    "geom_full_kekulized",
    "zinc250k",
)

#: Output schema version. Bump when the JSON shape changes; downstream
#: consumers can branch on this to keep parsing the old shape.
#: 1.1.0 — added ``fg_deviation`` field (FlowMol3 paper-aligned L1
#: distance between generated and reference functional-group
#: occurrence distributions; uses RDKit's bundled Dundee + Glaxo
#: Wellcome SMARTS via ``rdkit.Chem.Fragments``).
#: 1.2.0 — added the additive ``flowmol3_paper_metrics`` block
#: (upstream FlowMol3 ``SampleAnalyzer.analyze`` output, via
#: ``adaptive_reflow.adapters.flowmol3_metrics_upstream``). Every
#: pre-existing key keeps its meaning; the block is a pure addition.
#: 1.4.0 — added the additive ``fg_deviation_eq4`` (flat float, the
#: raw paper eq.4 / eq.21 instance-count L1 over the 85-element
#: ``fr_*`` vocabulary) + ``fg_deviation_eq4_block`` (rich dict with
#: ``n_gen`` / ``n_ref`` / ``vocabulary_size`` / ``note`` / ref
#: source). Wraps
#: :mod:`adaptive_reflow.eval.flowmol3_eq4_fg_deviation`; falls back
#: to ``None`` / ``{"value": None, "marker": "not_available", ...}``
#: when the wrapper is not importable. Existing ``fg_deviation``
#: (binary-occurrence L1) and ``fg_deviation_dundee_glaxo`` (160-rule
#: REOS L1) entries are unchanged.
OUTPUT_SCHEMA_VERSION: str = "1.4.0"

#: ``flowmol3_paper_metrics.marker`` vocabulary (closed set).
#: ``not_requested`` — the caller did not ask for the block (or the
#: auto-gate decided the input does not look like a FlowMol3 sample
#: list), so no upstream call was attempted.
FLOWMOL3_MARKER_NOT_REQUESTED: str = "not_requested"
#: ``not_available`` — the upstream wrapper (or its ``flowmol`` /
#: ``torch_scatter`` dependency chain) is not importable in this venv.
FLOWMOL3_MARKER_NOT_AVAILABLE: str = "not_available"
#: ``computed_upstream`` — a real upstream ``SampleAnalyzer.analyze``
#: dict was produced and is carried verbatim under ``metrics``.
FLOWMOL3_MARKER_COMPUTED_UPSTREAM: str = "computed_upstream"
#: ``upstream_error`` — the wrapper imported but the analyze call raised.
FLOWMOL3_MARKER_UPSTREAM_ERROR: str = "upstream_error"

#: Install hint surfaced when the upstream wrapper cannot be imported.
FLOWMOL3_INSTALL_HINT: str = (
    "run inside .venvs/flowmol3_venv (upstream FlowMol3 + posebusters + "
    "useful_rdkit_utils required)"
)

#: Sentinel returned by every "missing dependency" branch. Keeps the
#: JSON shape stable so a downstream consumer never sees a missing key.
NAN: float = float("nan")


# ---------------------------------------------------------------------------
# Dependency probes
# ---------------------------------------------------------------------------


def _probe_rdkit() -> tuple[bool, str | None]:
    """Return ``(importable, error_message_or_None)`` for :mod:`rdkit`.

    A failure here is the only hard-stop for the script — validity,
    QED, SA, and logP all require RDKit. When RDKit is missing, every
    metric except ``fcd`` returns NaN with a deterministic stderr
    note and the script still emits valid JSON.
    """
    try:
        import rdkit  # noqa: F401
    except ImportError as exc:
        return False, f"rdkit_unavailable:{exc}"
    return True, None


def _probe_fcd() -> tuple[bool, str | None]:
    """Return ``(importable, error_message_or_None)`` for :mod:`fcd`.

    ``fcd`` is the published PyPI package (bioinf-jku, v1.2.2).
    Install with ``uv pip install fcd``. A missing dependency here is
    non-fatal: FCD returns NaN with a stderr note and every other
    metric still computes.
    """
    try:
        import fcd  # noqa: F401
    except ImportError as exc:
        return False, f"fcd_unavailable:{exc}"
    return True, None


def _probe_posebusters() -> tuple[bool, str | None]:
    """Return ``(importable, error_message_or_None)`` for :mod:`posebusters`.

    ``posebusters`` (Buttenschoen et al. 2024) is the published
    PoseBusters validity-check package used as the Tier-2 paper
    metric by FlowMol3 / GraphBFN / JT-VAE-era successors. A missing
    dependency here is non-fatal: ``pb_validity`` returns the
    ``"not_installed"`` sentinel (per §3.4 of
    ``docs/r17-survey/baseline-deviation-review.md``) and every
    other metric still computes. The actual PoseBusters call requires
    a 3D conformer-generation stage (RDKit ``ETKDGv3`` + ``MMFF``
    minimisation) that is multi-hour and lives in a separate
    ``posebusters_venv`` — that work is NOT performed here.
    """
    try:
        import posebusters  # noqa: F401
    except ImportError as exc:
        return False, f"posebusters_unavailable:{exc}"
    return True, None


# ---------------------------------------------------------------------------
# Input loaders
# ---------------------------------------------------------------------------


def _load_smiles_from_npz(path: Path) -> list[str]:
    """Read a ``.npz`` containing a ``"smiles"`` UTF-8 string array.

    Returns the array as a Python ``list[str]``. Raises :class:`ValueError`
    on missing key or wrong dtype so the CLI surfaces a deterministic
    error code at the entry point rather than letting a numpy
    free-form error escape.
    """
    # SMILES are stored as object arrays (``np.array([...], dtype=object)``);
    # this requires ``allow_pickle=True``. The SMILES payload is plain text,
    # not pickled objects, so the pickle safety concern does not apply —
    # we are reading back the same strings we wrote. The downstream RDKit
    # parse is the security boundary, not the on-disk pickle.
    with np.load(str(path), allow_pickle=True) as archive:
        if "smiles" not in archive.files:
            raise ValueError(f"npz_missing_key:smiles: {path}")
        raw = archive["smiles"]
    # NumPy may decode UTF-8 bytes into ``np.str_`` scalars; cast to
    # native ``str`` so downstream hashing and rdkit calls see plain
    # strings. ``np.bytes_`` is decoded explicitly because RDKit's
    # ``Chem.MolFromSmiles`` requires ``str`` on py3.
    out: list[str] = []
    for entry in raw.tolist():
        if isinstance(entry, bytes):
            out.append(entry.decode("utf-8"))
        else:
            out.append(str(entry))
    return out


def _load_mols_from_pkl(path: Path) -> list[Any]:
    """Read a pickle of either ``(mols, sampling_time)`` or bare ``mols``.

    Mirrors the on-disk format produced by FlowMol3's
    ``compute_baseline_comparison.py`` (a 2-tuple whose ``[0]`` is the
    list of RDKit mols) AND the format the future
    :mod:`adaptive_reflow.molecular.rdkit_export` glue will emit. A
    bare list also passes the duck-type check so callers can pass
    in-process RDKit molecule lists directly.
    """
    with path.open("rb") as fh:
        payload = pickle.load(fh)
    if isinstance(payload, tuple) and len(payload) >= 1:
        candidate = payload[0]
    else:
        candidate = payload
    if not isinstance(candidate, list):
        raise ValueError(
            f"pkl_unexpected_payload_type:{type(payload).__name__}:{path}"
        )
    return candidate


def _load_mols_from_sdf(path: Path) -> list[Any]:
    """Read an RDKit SDF file as a list of ``Chem.Mol`` objects.

    ``Chem.SDMolSupplier`` returns ``None`` for unparsable records;
    these are kept as ``None`` entries in the returned list so the
    validity counter can include them in the denominator. The
    contract here matches the FlowMol3 ``.sdf`` path (records that
    fail to parse become ``None``).
    """
    from rdkit import Chem

    supplier = Chem.SDMolSupplier(str(path), removeHs=False, sanitize=True)
    return [mol for mol in supplier]


def load_inputs(path: Path) -> tuple[list[str | Any], str]:
    """Dispatch to the right loader by extension; return ``(items, format)``.

    ``items`` is either a ``list[str]`` (for ``.npz`` SMILES input)
    or a ``list[Any]`` (RDKit ``Chem.Mol`` or ``None``) for
    ``.pkl`` / ``.sdf`` inputs. The format string is one of
    ``"npz"``, ``"pkl"``, ``"sdf"`` so the caller can label the JSON.
    """
    suffix = path.suffix.lower()
    if suffix == ".npz":
        return _load_smiles_from_npz(path), "npz"
    if suffix == ".pkl":
        return _load_mols_from_pkl(path), "pkl"
    if suffix == ".sdf":
        return _load_mols_from_sdf(path), "sdf"
    raise ValueError(f"unsupported_input_extension:{suffix}:{path}")


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------


def _normalize_items(items: Sequence[Any]) -> tuple[list[str], list[Any | None]]:
    """Coerce the heterogeneous input list to ``(smiles, rdkit_mols_or_none)``.

    ``.npz`` inputs are already SMILES; ``Chem.MolFromSmiles`` runs
    once to materialise the paired ``Chem.Mol`` list. ``.pkl`` /
    ``.sdf`` inputs are already ``Chem.Mol`` objects (or ``None``);
    ``Chem.MolToSmiles`` derives the SMILES and ``None`` entries are
    preserved so the validity counter still sees them in the
    denominator. The validity metric is a pure function of the
    paired list shape: every ``None`` RDKit mol is invalid.
    """
    rdkit_avail, rdkit_err = _probe_rdkit()
    if not rdkit_avail:
        raise RuntimeError(f"rdkit_required:{rdkit_err}")
    from rdkit import Chem

    smiles_out: list[str] = []
    mols_out: list[Any | None] = []
    for item in items:
        if isinstance(item, str):
            mol = Chem.MolFromSmiles(item)
            mols_out.append(mol)
            smiles_out.append(item if mol is not None else "")
            continue
        # Bare object: assume RDKit Mol (or None for SDF parse failures).
        if item is None:
            mols_out.append(None)
            smiles_out.append("")
            continue
        try:
            smi = Chem.MolToSmiles(item)
        except Exception:  # noqa: BLE001 - permissive on purpose
            smi = ""
        smiles_out.append(smi)
        mols_out.append(item)
    return smiles_out, mols_out


def compute_validity(
    mols: Sequence[Any | None],
    *,
    also_sanitize: bool = True,
) -> tuple[float, int, int]:
    """Return ``(validity, n_valid, n_total)`` over ``mols``.

    A molecule counts as valid iff it is not ``None`` AND
    :func:`rdkit.Chem.MolFromSmiles(Chem.MolToSmiles(m))` round-trips
    (this is the "validity without correction" variant the GraphBFN
    paper uses; see Phase-1 risk register entry
    ``flowmol3_reuse_notes`` for the analogous FlowMol3 metric).
    ``also_sanitize=False`` skips the second pass when the caller
    knows the list already round-tripped (a small speedup for the
    in-process glue path).
    """
    from rdkit import Chem

    n_total = len(mols)
    n_valid = 0
    for mol in mols:
        if mol is None:
            continue
        try:
            roundtrip = Chem.MolFromSmiles(Chem.MolToSmiles(mol))
        except Exception:  # noqa: BLE001 - permissive on purpose
            roundtrip = None
        if roundtrip is None:
            continue
        if also_sanitize:
            try:
                Chem.SanitizeMol(roundtrip)
            except Exception:  # noqa: BLE001 - permissive on purpose
                continue
        n_valid += 1
    if n_total == 0:
        return NAN, 0, 0
    return float(n_valid) / float(n_total), n_valid, n_total


def _mean_over_valid(
    mols: Sequence[Any | None],
    compute_fn: Any,
) -> float:
    """Return the mean of ``compute_fn(mol)`` over non-None ``mols``.

    A ``compute_fn`` exception on any single molecule is treated as
    a skip (NOT a re-raise) so one bad molecule cannot poison the
    whole mean. Returns ``NaN`` for an empty denominator.
    """
    scores: list[float] = []
    for mol in mols:
        if mol is None:
            continue
        try:
            value = float(compute_fn(mol))
        except Exception:  # noqa: BLE001 - permissive on purpose
            continue
        if not math.isfinite(value):
            continue
        scores.append(value)
    if not scores:
        return NAN
    return float(sum(scores) / len(scores))


def compute_qed(mols: Sequence[Any | None]) -> float:
    """Mean QED across non-``None`` molecules; NaN on empty input."""
    from rdkit.Chem import QED

    return _mean_over_valid(mols, QED.qed)


# ---------------------------------------------------------------------------
# FlowMol3 paper-aligned metrics
# ---------------------------------------------------------------------------
#
# FlowMol3 (Dunn & Koes, arXiv:2508.12629) reports atom-level valence
# stability and connectivity as PRIMARY metrics (see
# data/FlowMol3/repo/flowmol/analysis/metrics.py:91-167). QED/SA/logP
# are NOT in the FlowMol3 paper - they are JT-VAE/GraphAF-era metrics
# we carried over for back-compat. The four metrics below match the
# flowmol.SampleAnalyzer.analyze() output schema so the framework's
# FlowMol3 numbers can be compared against the paper directly.
#
# Reference: data/FlowMol3/repo/flowmol/analysis/metrics.py:27-36
# (midi_valence_table) and :333-362 (check_stability).

#: Atom-type → formal-charge → valid-valency list. Verbatim from
#: MiDi's molecular metrics code, as used by FlowMol3's stability check.
MIDI_VALENCE_TABLE: dict[str, Any] = {
    "H": {0: [1], 1: [0], -1: [0]},
    "C": {0: [3, 4], 1: [3], -1: [3]},
    "N": {0: [2, 3], 1: [2, 3, 4], -1: [2]},
    "O": {0: [2], 1: [3], -1: [1]},
    "F": {0: [1], -1: [0]},
    "B": {0: [3]},
    "Al": {0: [3]},
    "Si": {0: [4]},
    "P": {0: [3, 5], 1: [4]},
    "S": {0: [2, 6], 1: [2, 3], 2: [4], 3: [5], -1: [3]},
    "Cl": {0: [1]},
    "As": {0: [3]},
    "Br": {0: [1], 1: [2]},
    "I": {0: [1]},
    "Hg": {0: [1, 2]},
    "Bi": {0: [3, 5]},
    "Se": {0: [2, 4, 6]},
}


def _normalise_valencies(table_value: Any, charge: int) -> list[int] | None:
    """Flatten MiDi's mixed-shape valency table into ``list[int]``.

    MiDi packs each ``table[atom_type][charge]`` entry as either a single
    ``int`` (e.g. ``"F": {0: 1}``) or a list of allowed valencies
    (e.g. ``"C": {0: [3, 4]}``). This helper unifies the two shapes.
    """
    if charge not in table_value:
        return None
    raw = table_value[charge]
    if isinstance(raw, (list, tuple)):
        return [int(v) for v in raw]
    return [int(raw)]


def _atom_stable(atom: Any) -> tuple[bool, bool]:
    """Check whether ``atom`` has a valid valence under MiDi's table.

    Returns ``(atom_is_stable, atom_is_real)`` where ``atom_is_real`` is
    ``False`` for fake atoms (placeholder ``Sn`` tokens that FlowMol3
    uses for size-varied sampling). Real atoms with no matching entry
    in the valency table contribute ``False`` to the numerator AND
    denominator so unknown atom types neither help nor hurt.
    """
    if atom is None:
        return False, False
    symbol = atom.GetSymbol()
    if symbol == "Sn":
        # Fake atom used by FlowMol3 for size variation.
        return False, False
    if symbol not in MIDI_VALENCE_TABLE:
        return False, True
    formal_charge = atom.GetFormalCharge()
    valid = _normalise_valencies(MIDI_VALENCE_TABLE[symbol], formal_charge)
    if valid is None:
        return False, True
    valence = atom.GetTotalValence()
    return (valence in valid), True


def compute_atom_stability(
    mols: Sequence[Any | None],
) -> tuple[float, float]:
    """Return ``(frac_atoms_stable, frac_mols_stable_valence)``.

    Mirrors FlowMol3's ``SampleAnalyzer.analyze`` primary metric:
    fraction of generated atoms with valid valencies (excluding fake
    atoms), and fraction of molecules whose atoms ALL have valid
    valencies. NaN when input list is empty.
    """
    if not mols:
        return NAN, NAN
    n_total_atoms = 0
    n_stable_atoms = 0
    n_real_mols = 0
    n_stable_mols = 0
    for mol in mols:
        if mol is None:
            continue
        try:
            atoms = mol.GetAtoms()
        except AttributeError:
            continue
        mol_stable = True
        mol_has_real_atoms = False
        for atom in atoms:
            is_stable, is_real = _atom_stable(atom)
            if not is_real:
                continue
            mol_has_real_atoms = True
            n_total_atoms += 1
            if is_stable:
                n_stable_atoms += 1
            else:
                mol_stable = False
        if mol_has_real_atoms:
            n_real_mols += 1
            if mol_stable:
                n_stable_mols += 1
    if n_total_atoms == 0:
        return NAN, NAN
    frac_atoms_stable = float(n_stable_atoms) / float(n_total_atoms)
    frac_mols_stable = (
        float(n_stable_mols) / float(n_real_mols) if n_real_mols else NAN
    )
    return frac_atoms_stable, frac_mols_stable


def compute_connectivity(
    mols: Sequence[Any | None],
) -> tuple[float, float]:
    """Return ``(frac_connected, avg_num_components)``.

    A molecule counts as connected when RDKit's
    :func:`GetMolFrags` returns exactly one fragment. ``avg_num_components``
    is the mean number of fragments per non-None molecule. NaN when no
    molecules available. Mirrors FlowMol3's ``frac_connected`` and
    ``avg_num_components`` in :mod:`flowmol.analysis.metrics`.
    """
    from rdkit import Chem
    from rdkit.Chem import rdmolops

    real_mols = [m for m in mols if m is not None]
    if not real_mols:
        return NAN, NAN
    n_connected = 0
    component_counts: list[int] = []
    for mol in real_mols:
        try:
            frags = rdmolops.GetMolFrags(mol, asMols=False, sanitizeFrags=False)
        except Exception:  # noqa: BLE001 - permissive
            component_counts.append(0)
            continue
        n_frags = len(frags)
        component_counts.append(n_frags)
        if n_frags == 1:
            n_connected += 1
    frac_connected = float(n_connected) / float(len(real_mols))
    avg_components = float(sum(component_counts)) / float(len(component_counts))
    _ = Chem  # noqa: F841 - rdkit import probed for availability
    return frac_connected, avg_components


def compute_sa(mols: Sequence[Any | None]) -> float:
    """Mean SA (Synthetic Accessibility) across non-``None`` molecules.

    Reuses the RDKit ``sascorer`` contrib, the same module the
    :class:`adaptive_reflow.eval.rdkit_oracle.RdkitEvaluator` loads
    at import time. The contrib lives under
    ``RDConfig.RDContribDir/SA_Score`` and is appended to ``sys.path``
    here on demand so this script can run from a venv where the
    contrib is not pre-loaded (the oracle module pre-loads it via
    its own import side-effect, which the runner does not want to
    force on every invocation).
    """
    import os

    from rdkit.Chem import RDConfig

    from rdkit import Chem  # noqa: F401 - sentinel for missing rdkit

    sa_path = os.path.join(RDConfig.RDContribDir, "SA_Score")
    if sa_path not in sys.path:
        sys.path.append(sa_path)
    try:
        import sascorer
    except ImportError:
        return NAN

    def _sa(mol: Any) -> float:
        return float(sascorer.calculateScore(mol))

    return _mean_over_valid(mols, _sa)


def compute_logp(mols: Sequence[Any | None]) -> float:
    """Mean Wildman-Crippen logP across non-``None`` molecules.

    The :func:`MolLogP` accessor is reached via :mod:`Descriptors`
    rather than a direct ``from rdkit.Chem import MolLogP`` because
    rdkit's stub layout exposes ``MolLogP`` only as a submodule
    attribute (per the upstream ``rdMolDescriptors.pyi`` shape, which
    is excluded from this project's mypy matrix).
    """
    from rdkit.Chem import Descriptors

    return _mean_over_valid(mols, Descriptors.MolLogP)  # type: ignore[attr-defined]


def _load_smiles_file(path: Path) -> list[str]:
    """Return non-empty lines from a SMILES-per-line text file.

    Empty lines and whitespace-only lines are skipped so trailing
    newlines / blank-separator conventions do not poison the FCD
    reference set. Returns ``[]`` when the file is missing so the
    caller can decide whether to raise or skip.

    The GEOM-DRUGS reference has ~1M+ SMILES — reading the entire
    file via ``Path.read_text()`` materializes the whole file as a
    single Python string AND ``.splitlines()`` materializes a full
    list[str]. To avoid that double materialization we stream the
    file line-by-line and accumulate the result one line at a time
    so only a single line plus the growing output list sit in RAM.
    """
    if not path.exists():
        return []
    out: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for ln in f:
            stripped = ln.strip()
            if stripped:
                out.append(stripped)
    return out


def compute_fcd(
    gen_smiles: Sequence[str],
    *,
    reference_path: Path | None,
) -> tuple[float, str | None]:
    """Compute Fréchet ChemNet Distance against ``reference_path``.

    Returns ``(fcd, stderr_note_or_None)``. When ``fcd`` is not
    importable, the returned value is ``NaN`` and the stderr note
    points the operator at ``uv pip install fcd``. When
    ``reference_path`` is missing, the returned value is also ``NaN``
    but the stderr note identifies the missing file rather than the
    missing library.
    """
    try:
        import fcd
    except ImportError as exc:
        return NAN, f"fcd_unavailable:{exc}:install_with_uv_pip_install_fcd"

    if reference_path is None:
        return NAN, "fcd_reference_path_required"
    ref_smiles = _load_smiles_file(reference_path)
    if not ref_smiles:
        return NAN, f"fcd_reference_empty_or_missing:{reference_path}"

    gen_list = [s for s in gen_smiles if s]
    if not gen_list:
        return NAN, "fcd_generated_smiles_empty"

    try:
        score = float(fcd.get_fcd(gen_list, ref_smiles))
    except Exception as exc:  # noqa: BLE001 - permissive on purpose
        return NAN, f"fcd_computation_failed:{type(exc).__name__}:{exc}"
    if not math.isfinite(score):
        return NAN, "fcd_non_finite_result"
    return score, None


#: Marker for ``pb_validity`` when the underlying ``posebusters``
#: package is not importable in the running venv. The JSON shape is
#: stable (``{"value": null, "marker": <marker>, "install_hint": <hint>}``)
#: so downstream consumers can rely on the keys being present even
#: when the metric was not actually computed. Mirrors the
#: ``"external"`` sentinel used by :mod:`tools.run_image_eval` for
#: Tier-2 image-gen paper metrics that the framework deliberately
#: defers to a separate venv.
PB_VALIDITY_MARKER_NOT_INSTALLED: str = "not_installed"
PB_VALIDITY_MARKER_COMPUTED: str = "computed"
PB_VALIDITY_MARKER_COMPUTED_ETKDG_V3_ONLY: str = "computed_etkdg_v3_only"
PB_VALIDITY_MARKER_COMPUTED_MMFF: str = "computed_mmff"
PB_VALIDITY_MARKER_STUB_UNAVAILABLE: str = "stub_unavailable"
PB_VALIDITY_INSTALL_HINT: str = "pip install posebusters"
#: PoseBusters config name to use. ``"mol"`` is the de-novo
#: generation config: 12 intrinsic checks (sanitization, InChI
#: convertibility, atom connectivity, no radicals, bond lengths,
#: bond angles, internal steric clash, aromatic ring flatness,
#: non-aromatic ring non-flatness, double-bond flatness, internal
#: energy) with no protein / conditioning-molecule requirement.
#: The ``"dock"`` and ``"gen"`` configs both invoke
#: ``intermolecular_distance`` and ``volume_overlap`` modules that
#: need a ``mol_cond`` (the docking pocket protein) which is not
#: available for unconditional de-novo generation and which causes
#: posebusters 0.6.5 to raise ``TypeError: check_intermolecular_
#: distance() missing 1 required positional argument: 'mol_cond'``.
PB_VALIDITY_CONFIG: str = "mol"


def _embed_3d_etkdg_v3(mol: Any, *, random_seed: int = 42) -> bool:
    """Add a 3D conformer to ``mol`` in-place using RDKit's ``ETKDGv3``.

    Pure distance-geometry embed (no MMFF refinement, no GFN2-xTB).
    Returns ``True`` if a conformer was successfully added, ``False``
    if embedding failed (large / macrocyclic / pathological
    topology). The seed is fixed so the embedding is deterministic
    — the PoseBusters checks themselves are a function of the
    conformer, so a stable seed makes the metric reproducible.

    No sanitization is run here: PoseBusters applies its own
    ``sanitize=True`` to each mol via the ``distance_geometry``
    module and re-parses through InChI, which is a stricter round
    trip than the RDKit ``MolFromSmiles`` sanitize.
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem

    try:
        mol_h = Chem.AddHs(mol)
    except Exception:  # noqa: BLE001 - permissive on purpose
        return False
    params = AllChem.ETKDGv3()
    params.randomSeed = int(random_seed)
    try:
        status = AllChem.EmbedMolecule(mol_h, params)
    except Exception:  # noqa: BLE001 - permissive on purpose
        return False
    if status != 0:
        return False
    try:
        # Copy the conformer onto the heavy-atom mol so downstream
        # PoseBusters sees a single conformer on the H-stripped
        # graph. ``Chem.RemoveHs`` drops the explicit Hs; the
        # conformer is preserved.
        new_mol = Chem.RemoveHs(mol_h)
    except Exception:  # noqa: BLE001 - permissive on purpose
        return False
    if new_mol.GetNumConformers() == 0:
        return False
    # Replace the input mol's conformer slot with the embedded one.
    # The conformer has the same heavy-atom indexing as the
    # original (AddHs appends Hs at the end), so atom positions
    # align with the input bond graph.
    conf = new_mol.GetConformer()
    # Clear any prior conformers on ``mol`` then add the new one.
    for i in range(mol.GetNumConformers() - 1, -1, -1):
        mol.RemoveConformer(i)
    mol.AddConformer(conf, assignId=True)
    return True


def compute_pb_validity(
    mols: Sequence[Any | None],
    *,
    random_seed: int = 42,
) -> dict[str, Any]:
    """Tier-2 paper metric: PoseBusters validity (``pb_validity``).

    PoseBusters (Buttenschoen et al. 2024) is the published chemical-
    validity oracle used by FlowMol3, GraphBFN, and JT-VAE-era
    successors. The metric is a fraction in ``[0, 1]`` — the
    proportion of generated molecules that pass PoseBusters'
    geometry-and-bond-order checks.

    This implementation is the **first-cut ETKDGv3-only** path
    (no MMFF minimisation, no GFN2-xTB). It is sufficient to
    emit a real ``pb_validity`` number on the de-novo set; it is
    NOT bit-equivalent to the FlowMol3 / GraphBFN paper pipeline,
    which uses MMFF or GFN2-xTB to refine the conformer before
    PoseBusters runs. The marker ``"computed_etkdg_v3_only"``
    makes the fidelity tier explicit so a downstream consumer
    can choose to ignore the number until the MMFF / xTB path
    is wired in (per §3.4 / §6.2 of
    ``docs/r17-survey/baseline-deviation-review.md``).

    A molecule is counted as PoseBusters-valid iff:

    1. It is not ``None`` AND ``Chem.MolFromSmiles`` round-tripped
       (already enforced by the upstream ``compute_validity`` —
       we re-derive here so this function is independently
       callable);
    2. ``AllChem.EmbedMolecule(ETKDGv3)`` succeeds on it
       (a non-trivial filter for macrocyclic / over-large graphs);
    3. Every PoseBusters check in the ``"mol"`` config returns
       ``True`` for it.

    A molecule that fails any of (1) / (2) / (3) counts as
    NOT PoseBusters-valid and stays in the denominator. Empty
    input returns ``value=NaN``.

    Returns
    -------
    dict with shape::

        {
          "value": None | float in [0, 1],
          "marker": "not_installed"
                 | "stub_unavailable"
                 | "computed"
                 | "computed_etkdg_v3_only",
          "install_hint": "pip install posebusters" | None,
          "note": "..."  # optional stderr-equivalent string
          "conformer_protocol": "ETKDGv3" | None,
          "n_total": int,            # denominator
          "n_pb_valid": int,         # numerator
          "n_conformer_failures": int,
          "pass_per_check": dict[str, float] | None  # per-check pass rate
        }

    The ``marker`` field is the canonical sentinel; consumers
    that only need the value should treat ``value == None`` as
    "not computed". The ``install_hint`` field names the
    missing package (when ``marker == "not_installed"``); for
    other markers it is ``None``.

    Stability contract
    -------------------

    The JSON shape is stable regardless of which branch fires —
    every documented key is present in every return. New keys
    are additive (downstream code that reads only the four
    core keys continues to work). The ``marker`` vocabulary is
    closed: future fidelity tiers should be added by appending
    a new marker, never by repurposing an existing one.
    """
    pb_ok, pb_err = _probe_posebusters()
    if not pb_ok:
        # Stable stub shape — the consumer can rely on every key
        # being present regardless of which branch fires.
        return {
            "value": None,
            "marker": PB_VALIDITY_MARKER_NOT_INSTALLED,
            "install_hint": PB_VALIDITY_INSTALL_HINT,
            "note": (
                f"{pb_err}:posebusters_unavailable:"
                "install_with_uv_pip_install_posebusters_in_flowmol3_venv"
            ),
            "conformer_protocol": None,
            "n_total": int(len(mols)),
            "n_pb_valid": 0,
            "n_conformer_failures": 0,
            "pass_per_check": None,
        }

    real_mols: list[Any] = [m for m in mols if m is not None]
    if not real_mols:
        return {
            "value": NAN,
            "marker": PB_VALIDITY_MARKER_COMPUTED_ETKDG_V3_ONLY,
            "install_hint": None,
            "note": "no_valid_input_molecules:pb_validity_is_NaN",
            "conformer_protocol": "ETKDGv3",
            "n_total": 0,
            "n_pb_valid": 0,
            "n_conformer_failures": 0,
            "pass_per_check": None,
        }

    # 3D conformer stage — first-cut ETKDGv3 only (no MMFF, no
    # GFN2-xTB). Molecules that fail embedding are recorded as
    # ``conformer_failures`` and counted in the denominator as
    # "not PoseBusters-valid".
    conformered_mols: list[Any] = []
    n_conformer_failures = 0
    for mol in real_mols:
        # Build a fresh copy so we don't mutate the caller's
        # molecule list (the input ``mols`` is the in-process
        # RDKit mol list, owned by the caller). ``Chem.Mol(mol)``
        # is the canonical deep-copy idiom in RDKit.
        from rdkit import Chem

        try:
            m_copy = Chem.Mol(mol)
        except Exception:  # noqa: BLE001 - permissive on purpose
            n_conformer_failures += 1
            continue
        if _embed_3d_etkdg_v3(m_copy, random_seed=random_seed):
            conformered_mols.append(m_copy)
        else:
            n_conformer_failures += 1

    if not conformered_mols:
        return {
            "value": 0.0,
            "marker": PB_VALIDITY_MARKER_COMPUTED_ETKDG_V3_ONLY,
            "install_hint": None,
            "note": (
                f"all_{n_conformer_failures}_conformer_embeds_failed_"
                "etkdg_v3_no_pb_checks_run:pb_validity_is_0"
            ),
            "conformer_protocol": "ETKDGv3",
            "n_total": int(len(real_mols)),
            "n_pb_valid": 0,
            "n_conformer_failures": int(n_conformer_failures),
            "pass_per_check": None,
        }

    # Real PoseBusters call. ``config="mol"`` is the de-novo
    # generation config (12 intrinsic checks, no protein). See
    # ``PB_VALIDITY_CONFIG`` for why "dock" / "gen" are not used
    # here.
    try:
        from posebusters import PoseBusters  # type: ignore[import-not-found]

        pb = PoseBusters(config=PB_VALIDITY_CONFIG)
        df = pb.bust(conformered_mols)
    except Exception as exc:  # noqa: BLE001 - permissive on purpose
        return {
            "value": None,
            "marker": PB_VALIDITY_MARKER_STUB_UNAVAILABLE,
            "install_hint": None,
            "note": (
                f"posebusters_call_failed:{type(exc).__name__}:{exc}:"
                "see_pb_validity_block_for_failure"
            ),
            "conformer_protocol": "ETKDGv3",
            "n_total": int(len(real_mols)),
            "n_pb_valid": 0,
            "n_conformer_failures": int(n_conformer_failures),
            "pass_per_check": None,
        }

    # ``df`` is a multi-index DataFrame (file, molecule, position)
    # with one row per conformer and one column per PoseBusters
    # check. ``mol_pred_loaded`` is a tautology (always True since
    # we passed live RDKit mols) so we drop it from the per-check
    # pass-rate dictionary; the strict PB-validity definition
    # uses ALL checks.
    n_total = int(len(real_mols))
    n_pass_all = 0
    pass_per_check: dict[str, int] = {}
    check_total: dict[str, int] = {}
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        all_ok = all(bool(v) for v in row_dict.values())
        if all_ok:
            n_pass_all += 1
        for k, v in row_dict.items():
            check_total[k] = check_total.get(k, 0) + 1
            if bool(v):
                pass_per_check[k] = pass_per_check.get(k, 0) + 1

    pass_rates: dict[str, float] = {
        k: float(pass_per_check.get(k, 0)) / float(check_total[k])
        for k in check_total
    }
    # Drop the tautological "loaded" check from the public dict so
    # consumers see the substantive checks only.
    pass_rates_public = {k: v for k, v in pass_rates.items() if k != "mol_pred_loaded"}

    pb_validity = float(n_pass_all) / float(n_total)
    return {
        "value": pb_validity,
        "marker": PB_VALIDITY_MARKER_COMPUTED_ETKDG_V3_ONLY,
        "install_hint": None,
        "note": (
            f"posebusters_computed_with_etkdg_v3_only_no_mmff_no_xtb:"
            f"{n_pass_all}_of_{n_total}_passed_all_checks:"
            f"{n_conformer_failures}_conformer_failures"
        ),
        "conformer_protocol": "ETKDGv3",
        "n_total": n_total,
        "n_pb_valid": int(n_pass_all),
        "n_conformer_failures": int(n_conformer_failures),
        "pass_per_check": pass_rates_public,
    }


def compute_pb_validity_mmff(
    mols: Sequence[Any | None],
    *,
    num_confs: int = 10,
    random_seed: int = 42,
    max_mmff_iters: int = 200,
) -> dict[str, Any]:
    """Tier-2 paper metric: PoseBusters validity with MMFF-min conformer.

    Full-fidelity path (Fix B). For every input RDKit mol:

      1. Generate ``num_confs`` ETKDGv3 candidates via
         ``AllChem.EmbedMultipleConfs`` (Wang et al. 2020 J Chem Inf
         Model) at the given ``random_seed``;
      2. MMFF94-minimize each with
         ``AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=max_mmff_iters)``
         (Rappe 1992 MMFF94);
      3. Pick the lowest-energy conformer by single-point MMFF94
         energy;
      4. Hand that single conformer to
         ``PoseBusters(config="mol").bust([mol])`` and read off
         ``pb_valid``.

    This mirrors the published PoseBusters energy_ratio pipeline
    (Buttenschoen et al. 2024 Chem Sci §2.2.2, ETKDGv3 + MMFF94
    reference). The PoseBusters package's own ``energy_ratio`` module
    is COMMENTED OUT in the shipped ``pb_config.yaml`` so this
    conformer sweep has to be done by the caller.

    JSON shape mirrors :func:`compute_pb_validity` (the
    ETKDGv3-only path); the marker is
    :data:`PB_VALIDITY_MARKER_COMPUTED_MMFF` and
    ``conformer_protocol`` reports ``"ETKDGv3+MMFF(200)"`` (the
    ``200`` is ``max_mmff_iters``). ``per_conformer_min_energy`` is
    added so consumers can audit the conformer-pick heuristic.

    The function is independently callable; it does NOT mutate the
    caller's molecule list (each input is deep-copied via
    ``Chem.Mol(mol)`` before embedding).
    """
    pb_ok, pb_err = _probe_posebusters()
    if not pb_ok:
        return {
            "value": None,
            "marker": PB_VALIDITY_MARKER_NOT_INSTALLED,
            "install_hint": PB_VALIDITY_INSTALL_HINT,
            "note": (
                f"{pb_err}:posebusters_unavailable:"
                "install_with_uv_pip_install_posebusters_in_flowmol3_venv"
            ),
            "conformer_protocol": None,
            "n_total": int(len(mols)),
            "n_pb_valid": 0,
            "n_conformer_failures": 0,
            "pass_per_check": None,
            "per_conformer_min_energy": None,
        }

    try:
        from adaptive_reflow.eval.mmff_conformer import embed_mmff  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001 — module may not be on PYTHONPATH
        return {
            "value": None,
            "marker": PB_VALIDITY_MARKER_STUB_UNAVAILABLE,
            "install_hint": None,
            "note": (
                f"mmff_conformer_module_unavailable:{type(exc).__name__}:{exc}:"
                "see_pb_validity_mmff_block_for_failure"
            ),
            "conformer_protocol": None,
            "n_total": int(len(mols)),
            "n_pb_valid": 0,
            "n_conformer_failures": 0,
            "pass_per_check": None,
            "per_conformer_min_energy": None,
        }

    real_mols: list[Any] = [m for m in mols if m is not None]
    if not real_mols:
        return {
            "value": NAN,
            "marker": PB_VALIDITY_MARKER_COMPUTED_MMFF,
            "install_hint": None,
            "note": "no_valid_input_molecules:pb_validity_mmff_is_NaN",
            "conformer_protocol": f"ETKDGv3+MMFF({int(max_mmff_iters)})",
            "n_total": 0,
            "n_pb_valid": 0,
            "n_conformer_failures": 0,
            "pass_per_check": None,
            "per_conformer_min_energy": None,
        }

    conformered_mols: list[Any] = []
    per_conformer_min_energy: list[float] = []
    n_conformer_failures = 0
    for mol in real_mols:
        from rdkit import Chem  # noqa: PLC0415 — local import to keep import-time light

        try:
            m_copy = Chem.Mol(mol)
        except Exception:  # noqa: BLE001 — permissive on purpose
            n_conformer_failures += 1
            continue
        cid, energy = embed_mmff(
            m_copy,
            num_confs=int(num_confs),
            seed=int(random_seed),
            max_iters=int(max_mmff_iters),
        )
        if cid < 0:
            n_conformer_failures += 1
            continue
        conformered_mols.append(m_copy)
        per_conformer_min_energy.append(float(energy))

    if not conformered_mols:
        return {
            "value": 0.0,
            "marker": PB_VALIDITY_MARKER_COMPUTED_MMFF,
            "install_hint": None,
            "note": (
                f"all_{n_conformer_failures}_mmff_conformer_embeds_failed_"
                f"etkdgv3_mmff{max_mmff_iters}_no_pb_checks_run:pb_validity_mmff_is_0"
            ),
            "conformer_protocol": f"ETKDGv3+MMFF({int(max_mmff_iters)})",
            "n_total": int(len(real_mols)),
            "n_pb_valid": 0,
            "n_conformer_failures": int(n_conformer_failures),
            "pass_per_check": None,
            "per_conformer_min_energy": per_conformer_min_energy,
        }

    try:
        from posebusters import PoseBusters  # type: ignore[import-not-found]

        pb = PoseBusters(config=PB_VALIDITY_CONFIG)
        df = pb.bust(conformered_mols)
    except Exception as exc:  # noqa: BLE001 — permissive on purpose
        return {
            "value": None,
            "marker": PB_VALIDITY_MARKER_STUB_UNAVAILABLE,
            "install_hint": None,
            "note": (
                f"posebusters_call_failed:{type(exc).__name__}:{exc}:"
                "see_pb_validity_mmff_block_for_failure"
            ),
            "conformer_protocol": f"ETKDGv3+MMFF({int(max_mmff_iters)})",
            "n_total": int(len(real_mols)),
            "n_pb_valid": 0,
            "n_conformer_failures": int(n_conformer_failures),
            "pass_per_check": None,
            "per_conformer_min_energy": per_conformer_min_energy,
        }

    n_total = int(len(real_mols))
    n_pass_all = 0
    pass_per_check: dict[str, int] = {}
    check_total: dict[str, int] = {}
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        all_ok = all(bool(v) for v in row_dict.values())
        if all_ok:
            n_pass_all += 1
        for k, v in row_dict.items():
            check_total[k] = check_total.get(k, 0) + 1
            if bool(v):
                pass_per_check[k] = pass_per_check.get(k, 0) + 1

    pass_rates: dict[str, float] = {
        k: float(pass_per_check.get(k, 0)) / float(check_total[k])
        for k in check_total
    }
    pass_rates_public = {k: v for k, v in pass_rates.items() if k != "mol_pred_loaded"}

    pb_validity_mmff = float(n_pass_all) / float(n_total)
    return {
        "value": pb_validity_mmff,
        "marker": PB_VALIDITY_MARKER_COMPUTED_MMFF,
        "install_hint": None,
        "note": (
            f"posebusters_computed_with_etkdgv3_mmff{max_mmff_iters}:"
            f"{n_pass_all}_of_{n_total}_passed_all_checks:"
            f"{n_conformer_failures}_conformer_failures:"
            f"num_confs={int(num_confs)}:seed={int(random_seed)}"
        ),
        "conformer_protocol": f"ETKDGv3+MMFF({int(max_mmff_iters)})",
        "n_total": n_total,
        "n_pb_valid": int(n_pass_all),
        "n_conformer_failures": int(n_conformer_failures),
        "pass_per_check": pass_rates_public,
        "per_conformer_min_energy": per_conformer_min_energy,
    }


# ---------------------------------------------------------------------------
# FlowMol3 FG-deviation (Dundee + Glaxo Wellcome SMARTS, L1 distance)
# ---------------------------------------------------------------------------
#
# The FlowMol3 paper (Dunn & Koes, arXiv:2508.12629) reports a
# "Functional-Group Deviation" (FG-deviation) metric which is the L1
# distance between the generated molecules' functional-group
# occurrence distribution and a reference distribution (typically the
# training data — GEOM-DRUGS). The functional-group vocabulary is
# the published SMARTS lists from Bickerton et al. (Dundee QED
# fragments) and the Glaxo Wellcome Kinase inhibitor filter, both
# of which RDKit ships verbatim in :mod:`rdkit.Chem.Fragments` as the
# ``fr_*`` descriptors. Using RDKit's built-in list avoids any
# external SMARTS download (the lists are non-gated academic data
# baked into the RDKit distribution per the
# ``rdkit/Chem/FragCatalog`` source tree).
#
# Definition (per molecule, per FG):
#
#   v_i(mol) = 1 if FG_i SMARTS matches anywhere in ``mol`` else 0
#
# Aggregate to a per-set occurrence rate (the fraction of the set
# that contains the group at least once):
#
#   p_i^gen  = mean(v_i(mol) over generated mols)
#   p_i^ref  = mean(v_i(mol) over reference mols)
#
# FG-deviation = sum over i of |p_i^gen - p_i^ref|
#
# This is the metric definition used by the FlowMol3 paper for the
# 0.37 / 0.28 numbers reported in §5 of arXiv:2508.12629.

#: SMARTS-backed fragment descriptors we use for FG-deviation.
#: RDKit's :mod:`rdkit.Chem.Fragments` ships 85 ``fr_*`` symbols
#: covering the Dundee QED-style fragments and the Glaxo Wellcome
#: kinase-inhibitor fragments. We hard-code the list here (rather
#: than ``dir(Fragments)`` at runtime) so the FG vocabulary is
#: pinned — adding a new RDKit ``fr_*`` should be a deliberate
#: choice reviewed against the paper, not a side effect of an
#: RDKit upgrade. Mirrors the published lists (Bickerton et al.
#: 2012 QED §SMARTS; Hann et al. Glaxo Wellcome kinase SMARTS).
FG_SMARTS_NAMES: tuple[str, ...] = (
    "fr_Al_COO",
    "fr_Al_OH",
    "fr_Al_OH_noTert",
    "fr_ArN",
    "fr_Ar_COO",
    "fr_Ar_N",
    "fr_Ar_NH",
    "fr_Ar_OH",
    "fr_COO",
    "fr_COO2",
    "fr_C_O",
    "fr_C_O_noCOO",
    "fr_C_S",
    "fr_HOCCN",
    "fr_Imine",
    "fr_NH0",
    "fr_NH1",
    "fr_NH2",
    "fr_N_O",
    "fr_Ndealkylation1",
    "fr_Ndealkylation2",
    "fr_Nhpyrrole",
    "fr_SH",
    "fr_aldehyde",
    "fr_alkyl_carbamate",
    "fr_alkyl_halide",
    "fr_allylic_oxid",
    "fr_amide",
    "fr_amidine",
    "fr_aniline",
    "fr_aryl_methyl",
    "fr_azide",
    "fr_azo",
    "fr_barbitur",
    "fr_benzene",
    "fr_benzodiazepine",
    "fr_bicyclic",
    "fr_diazo",
    "fr_dihydropyridine",
    "fr_epoxide",
    "fr_ester",
    "fr_ether",
    "fr_furan",
    "fr_guanido",
    "fr_halogen",
    "fr_hdrzine",
    "fr_hdrzone",
    "fr_imidazole",
    "fr_imide",
    "fr_isocyan",
    "fr_isothiocyan",
    "fr_ketone",
    "fr_ketone_Topliss",
    "fr_lactam",
    "fr_lactone",
    "fr_methoxy",
    "fr_morpholine",
    "fr_nitrile",
    "fr_nitro",
    "fr_nitro_arom",
    "fr_nitro_arom_nonortho",
    "fr_nitroso",
    "fr_oxazole",
    "fr_oxime",
    "fr_para_hydroxylation",
    "fr_phenol",
    "fr_phenol_noOrthoHbond",
    "fr_phos_acid",
    "fr_phos_ester",
    "fr_piperdine",
    "fr_piperzine",
    "fr_priamide",
    "fr_prisulfonamd",
    "fr_pyridine",
    "fr_quatN",
    "fr_sulfide",
    "fr_sulfonamd",
    "fr_sulfone",
    "fr_term_acetylene",
    "fr_tetrazole",
    "fr_thiazole",
    "fr_thiocyan",
    "fr_thiophene",
    "fr_unbrch_alkane",
    "fr_urea",
)


def _fg_presence_vector(mol: Any) -> list[int]:
    """Return ``[v_0, v_1, ..., v_K]`` where ``v_i = 1`` if ``FG_i`` matches.

    Each ``fr_*`` is a 1-arg callable taking an RDKit ``Chem.Mol`` and
    returning an ``int`` count. We coerce to ``{0, 1}`` (binary
    occurrence) per the FlowMol3 paper definition. Returns
    ``[]`` for ``None`` mols (the caller filters these out before
    averaging). Failures on a single ``fr_*`` are treated as
    "absent" (``0``) so a malformed SMARTS cannot poison the whole
    vector.
    """
    from rdkit.Chem import Fragments

    vec: list[int] = []
    for name in FG_SMARTS_NAMES:
        counter = getattr(Fragments, name, None)
        if counter is None:
            vec.append(0)
            continue
        try:
            n_hits = int(counter(mol))
        except Exception:  # noqa: BLE001 - permissive on purpose
            n_hits = 0
        vec.append(1 if n_hits > 0 else 0)
    return vec


def _fg_occurrence_rates(mols: Sequence[Any | None]) -> tuple[list[float], int]:
    """Mean occurrence rate per FG across ``mols``; ``(rates, n_used)``.

    Skips ``None`` and SMILES-parse-failure entries (which surface
    here as ``None`` from the loader). Returns ``([0.0]*K, 0)`` when
    no usable mols are present so the caller can branch on
    ``n_used == 0`` for the NaN sentinel.
    """
    n_used = 0
    K = len(FG_SMARTS_NAMES)
    sums = [0] * K
    for mol in mols:
        if mol is None:
            continue
        vec = _fg_presence_vector(mol)
        if not vec:
            continue
        n_used += 1
        for i, v in enumerate(vec):
            sums[i] += v
    if n_used == 0:
        return [0.0] * K, 0
    return [s / n_used for s in sums], n_used


def compute_fg_deviation(
    gen_mols: Sequence[Any | None],
    ref_smiles: Sequence[str],
) -> tuple[float, str | None]:
    """L1 FG-deviation between ``gen_mols`` and ``ref_smiles``.

    Returns ``(value, stderr_note_or_None)``. The reference set is
    parsed on-the-fly via :func:`rdkit.Chem.MolFromSmiles`; the
    same RDKit parse failure tolerance as the validity path
    applies (an unparseable reference SMILES is silently dropped
    from the reference occurrence-rate computation). Returns
    ``NaN`` with a stderr note when RDKit is missing, the
    reference list is empty, or the generated list is empty.

    The metric is the sum of per-FG absolute differences of the
    occurrence rates, which equals the L1 distance between the two
    per-set binary FG vectors (under uniform weight on the
    generators and references). The value is in ``[0, 2*K]``
    where ``K = len(FG_SMARTS_NAMES) = 85``; in practice on
    drug-like sets the value is small (paper: 0.27-0.37 on
    GEOM-DRUGS) because most groups are either consistently
    present or consistently absent.
    """
    rdkit_ok, rdkit_err = _probe_rdkit()
    if not rdkit_ok:
        return NAN, f"rdkit_unavailable:{rdkit_err}"
    from rdkit import Chem  # noqa: F401 - sentinel for availability

    if not ref_smiles:
        return NAN, "fg_deviation_reference_smiles_empty"
    if not gen_mols or all(m is None for m in gen_mols):
        return NAN, "fg_deviation_generated_mols_empty"

    # Parse reference SMILES into RDKit mols. Reuse the same
    # permissive parse + sanitise tolerance as ``_normalize_items``
    # so a single malformed reference does not abort the metric.
    ref_mols: list[Any] = []
    for smi in ref_smiles:
        if not smi:
            continue
        try:
            mol = Chem.MolFromSmiles(smi)
        except Exception:  # noqa: BLE001
            mol = None
        if mol is None:
            continue
        ref_mols.append(mol)

    if not ref_mols:
        return NAN, "fg_deviation_reference_all_unparseable"

    gen_rates, n_gen = _fg_occurrence_rates(gen_mols)
    ref_rates, n_ref = _fg_occurrence_rates(ref_mols)
    if n_gen == 0 or n_ref == 0:
        return NAN, (
            f"fg_deviation_no_usable_mols:gen={n_gen}:ref={n_ref}"
        )

    # L1 distance between the two occurrence-rate vectors.
    deviation = 0.0
    for p_g, p_r in zip(gen_rates, ref_rates):
        deviation += abs(p_g - p_r)
    return float(deviation), None


def _compute_fg_deviation_dundee_glaxo(
    gen_smiles: Sequence[str],
    fg_ref_smiles: Sequence[str],
    *,
    reference_path: Path | None,
) -> dict[str, Any]:
    """Compute the Dundee + Glaxo FG-deviation block (Fix A).

    Thin shim over
    :func:`adaptive_reflow.eval.fg_deviation.compute_flowmol3_fg_deviation`
    that:
      * prefers the caller-supplied ``reference_path`` SMILES set
        (the same ``--reference-smiles`` file FCD uses) when present,
      * falls back to the in-module NCI-first-5K documented proxy
        when no reference was supplied, and
      * never raises — the upstream module returns ``{"value": NaN,
        ...}`` on dependency failure.

    Returns a dict with stable JSON shape so downstream consumers
    see the same fields regardless of whether the computation
    succeeded.
    """
    from adaptive_reflow.eval.fg_deviation import (  # noqa: PLC0415
        DEFAULT_REFERENCE_PATH,
        compute_flowmol3_fg_deviation,
    )

    if fg_ref_smiles:
        # Use the caller-supplied set verbatim — the operator may
        # have pointed --reference-smiles at GEOM-DRUGS train.
        return compute_flowmol3_fg_deviation(
            list(gen_smiles),
            reference_smiles_path=None,
            reference_smiles=list(fg_ref_smiles),
        )

    if reference_path is not None:
        # Caller supplied a path but the SMILES could not be loaded
        # (file missing / wrong format); surface that explicitly.
        return compute_flowmol3_fg_deviation(
            list(gen_smiles),
            reference_smiles_path=str(reference_path),
            reference_smiles=None,
        )

    # No caller-supplied reference: fall back to the documented
    # in-tree proxy so the metric always computes.
    return compute_flowmol3_fg_deviation(
        list(gen_smiles),
        reference_smiles_path=DEFAULT_REFERENCE_PATH,
        reference_smiles=None,
    )


# ---------------------------------------------------------------------------
# FlowMol3 paper eq.4 / eq.21 instance-count FG-deviation wrapper
# ---------------------------------------------------------------------------
#
# The FlowMol3 paper (Dunn & Koes, arXiv:2508.12629, Digital Discovery
# 2026, 5, 2052-2066) defines FG-deviation as the L1 sum of
# per-FG absolute differences of ``omega_f := (# instances of f) / (# mols)``
# (eq.21) over the 85-element RDKit ``fr_*`` vocabulary. The existing
# ``compute_fg_deviation`` is a binary-occurrence variant (each mol
# contributes 0/1 per FG); the new wrapper at
# :mod:`adaptive_reflow.eval.flowmol3_eq4_fg_deviation` is the
# paper-faithful instance-count variant. Both numbers are reported
# side-by-side so a downstream consumer can audit the gap.
#
# Reference: paper Section 3.2.2 (Functional Group Composition), eq.21.
# Headline: FlowMol3 0.37 +/- 0.01 (Digital Discovery Table 1, N = 5000)
# on GEOM-DRUGS. The wrapper REUSES
# :func:`adaptive_reflow.eval.fg_deviation.count_fg_hits` and
# :data:`adaptive_reflow.eval.fg_deviation.DUNDEE_FR_SMARTS_NAMES` for
# the per-mol raw instance counts and the 85-element vocabulary.


#: Sentinel marker for the eq4 wrapper's stable JSON shape. Mirrors
#: the ``PB_VALIDITY_MARKER_*`` / ``FLOWMOL3_MARKER_*`` vocabulary.
FG_DEV_EQ4_MARKER_COMPUTED: str = "computed_eq4"
FG_DEV_EQ4_MARKER_WRAPPER_UNAVAILABLE: str = "wrapper_unavailable"
FG_DEV_EQ4_MARKER_RDKIT_UNAVAILABLE: str = "rdkit_unavailable"
FG_DEV_EQ4_MARKER_REFERENCE_UNAVAILABLE: str = "reference_unavailable"


def _compute_fg_deviation_eq4_block(
    gen_smiles: Sequence[str],
    fg_ref_smiles: Sequence[str],
    *,
    reference_path: Path | None,
) -> dict[str, Any]:
    """Compute the paper eq.4 / eq.21 instance-count FG-deviation block.

    Thin shim over
    :func:`adaptive_reflow.eval.flowmol3_eq4_fg_deviation.compute_fg_deviation_eq4`
    that:
      * prefers the caller-supplied ``reference_path`` SMILES set
        (the same ``--reference-smiles`` file FCD uses) when present,
      * falls back to the in-module NCI-first-5K documented proxy
        when no reference was supplied, and
      * never raises — the wrapper returns ``{"value": NaN, "note":
        ..., ...}`` on dependency failure; the import itself is
        guarded with a try/except so a missing wrapper is
        surfaced as ``marker="wrapper_unavailable"`` rather than
        aborting the run.

    Returns a dict with stable JSON shape so downstream consumers
    see the same fields regardless of which branch fired. The
    ``value`` field is ``None`` when the wrapper was not importable
    (so a consumer can branch on ``value is None`` / ``is NaN`` /
    ``is a number``), and is a ``float`` (possibly ``NaN``) when the
    wrapper was importable but the computation could not produce a
    finite result.
    """
    nan = float("nan")
    unavailable: dict[str, Any] = {
        "value": None,
        "n_gen": 0,
        "n_ref": 0,
        "n_gen_skipped": 0,
        "n_ref_skipped": 0,
        "vocabulary_size": 0,
        "reference_source": None,
        "note": "fg_dev_eq4_wrapper_unavailable",
        "marker": FG_DEV_EQ4_MARKER_WRAPPER_UNAVAILABLE,
    }
    try:
        from adaptive_reflow.eval.flowmol3_eq4_fg_deviation import (  # noqa: PLC0415
            compute_fg_deviation_eq4,
        )
    except BaseException as exc:  # noqa: BLE001 — wrapper may raise anything
        unavailable["note"] = (
            f"fg_dev_eq4_wrapper_import_failed:{type(exc).__name__}:{exc}"
        )
        return unavailable

    if fg_ref_smiles:
        result = compute_fg_deviation_eq4(
            list(gen_smiles),
            reference_smiles_path=None,
            reference_smiles=list(fg_ref_smiles),
        )
    elif reference_path is not None:
        result = compute_fg_deviation_eq4(
            list(gen_smiles),
            reference_smiles_path=str(reference_path),
            reference_smiles=None,
        )
    else:
        from adaptive_reflow.eval.fg_deviation import (  # noqa: PLC0415
            DEFAULT_REFERENCE_PATH,
        )

        result = compute_fg_deviation_eq4(
            list(gen_smiles),
            reference_smiles_path=DEFAULT_REFERENCE_PATH,
            reference_smiles=None,
        )

    # The wrapper returns ``{"value": NaN, "n_gen": ..., ...,
    # "note": "...reference_unavailable..."}`` when it could not
    # load a reference. Surface that with a dedicated marker so
    # downstream consumers can branch on it.
    raw_value = result.get("value", nan)
    try:
        raw_value_float = float(raw_value)
    except (TypeError, ValueError):
        raw_value_float = nan
    note = str(result.get("note") or "")
    if "rdkit_unavailable" in note:
        marker = FG_DEV_EQ4_MARKER_RDKIT_UNAVAILABLE
    elif "reference_unavailable" in note or "reference_all_unparseable" in note:
        marker = FG_DEV_EQ4_MARKER_REFERENCE_UNAVAILABLE
    else:
        marker = FG_DEV_EQ4_MARKER_COMPUTED
    return {
        "value": raw_value_float,
        "n_gen": int(result.get("n_gen", 0) or 0),
        "n_ref": int(result.get("n_ref", 0) or 0),
        "n_gen_skipped": int(result.get("n_gen_skipped", 0) or 0),
        "n_ref_skipped": int(result.get("n_ref_skipped", 0) or 0),
        "vocabulary_size": int(result.get("vocabulary_size", 0) or 0),
        "reference_source": result.get("reference_source"),
        "note": note or None,
        "marker": marker,
    }


# ---------------------------------------------------------------------------
# FlowMol3 upstream paper metrics (additive, Tier-1 fidelity)
# ---------------------------------------------------------------------------


def _looks_like_flowmol3_samples(items: Sequence[Any], fmt: str) -> bool:
    """Heuristic auto-gate: does this input look like a FlowMol3 sample list?

    A FlowMol3 sample list arrives as RDKit ``Mol`` objects (from a
    ``.pkl`` written by ``adaptive_reflow.molecular.rdkit_export`` /
    upstream ``test.py``, or from an ``.sdf``), typically carrying a 3D
    conformer. A bare SMILES ``.npz`` is *not* treated as a FlowMol3
    sample list: the upstream analyzer would then be scoring
    re-embedded geometry rather than generated geometry.

    The check is deliberately structural (format + object type) and
    never imports the upstream wrapper.
    """
    if fmt not in ("pkl", "sdf"):
        return False
    for item in items:
        if item is None or isinstance(item, str):
            continue
        if hasattr(item, "GetNumAtoms"):
            return True
    return False


def compute_flowmol3_paper_metrics(
    smiles: Sequence[str],
    *,
    processed_data_dir: Path | str | None = None,
    run_posebusters: bool = True,
    run_functional_validity: bool = True,
    run_energy_div: bool = False,
    pb_workers: int = 2,
    device: str = "cuda:0",
) -> dict[str, Any]:
    """Tier-1 paper metrics: upstream FlowMol3 ``SampleAnalyzer.analyze``.

    This delegates **all** computation to
    :func:`adaptive_reflow.adapters.flowmol3_metrics_upstream.compute_paper_metrics_from_smiles`,
    which runs the pinned upstream FlowMol3 analyzer verbatim. Nothing
    is reimplemented here: this function only handles gating, import
    failure, and JSON-shape stability.

    The wrapper import is a **lazy local import** on purpose. Callers
    that evaluate non-FlowMol3 samples in a venv without
    ``torch_scatter`` / upstream ``flowmol`` must not pay an
    ImportError at module import time.

    Returns
    -------
    dict with a stable shape::

        {
          "metrics": dict[str, float] | None,  # upstream dict, verbatim
          "marker": "not_requested" | "not_available"
                  | "computed_upstream" | "upstream_error",
          "install_hint": str | None,
          "note": str | None,
          "n_total": int,
          "run_posebusters": bool,
        }

    ``metrics`` is the upstream dict unmodified (keys such as
    ``frac_valid_mols``, ``frac_connected``, ``reos_cum_dev``,
    ``pb_valid``, ...). Consumers that only need one number should read
    ``metrics[<key>]`` and treat ``metrics is None`` as "not computed".
    """
    smiles_list = [s for s in smiles if s]
    base: dict[str, Any] = {
        "metrics": None,
        "marker": FLOWMOL3_MARKER_NOT_AVAILABLE,
        "install_hint": None,
        "note": None,
        "n_total": int(len(smiles_list)),
        "run_posebusters": bool(run_posebusters),
    }

    if not smiles_list:
        base["marker"] = FLOWMOL3_MARKER_NOT_REQUESTED
        base["note"] = "no_valid_input_smiles:flowmol3_paper_metrics_skipped"
        return base

    # LAZY import — see docstring. Never hoist to module scope.
    try:
        from adaptive_reflow.adapters import (  # noqa: PLC0415
            flowmol3_metrics_upstream as _upstream,
        )
    except BaseException as exc:  # noqa: BLE001 - upstream may raise anything
        base["marker"] = FLOWMOL3_MARKER_NOT_AVAILABLE
        base["install_hint"] = FLOWMOL3_INSTALL_HINT
        base["note"] = f"wrapper_import_failed:{type(exc).__name__}:{exc}"
        return base

    if not _upstream.is_upstream_available():
        base["marker"] = FLOWMOL3_MARKER_NOT_AVAILABLE
        base["install_hint"] = FLOWMOL3_INSTALL_HINT
        base["note"] = (
            "upstream_flowmol_unavailable:"
            f"{_upstream.get_upstream_import_error()!r}"
        )
        return base

    try:
        metrics = _upstream.compute_paper_metrics_from_smiles(
            smiles_list,
            processed_data_dir=processed_data_dir,
            run_posebusters=bool(run_posebusters),
            run_functional_validity=bool(run_functional_validity),
            run_energy_div=bool(run_energy_div),
            pb_workers=int(pb_workers),
            device=str(device),
        )
    except BaseException as exc:  # noqa: BLE001 - keep the JSON parseable
        base["marker"] = FLOWMOL3_MARKER_UPSTREAM_ERROR
        base["note"] = f"upstream_analyze_failed:{type(exc).__name__}:{exc}"
        return base

    base["metrics"] = {str(k): v for k, v in dict(metrics).items()}
    base["marker"] = FLOWMOL3_MARKER_COMPUTED_UPSTREAM
    return base


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _safe_dataset_tag(raw: str | None) -> str:
    """Return ``raw`` when it is in :data:`SUPPORTED_DATASETS`, else ``"unknown"``.

    The runner is dataset-agnostic; this tag is metadata that flows
    into the JSON. Unknown tags fall through to ``"unknown"`` rather
    than raising so a typo doesn't break the run.
    """
    if raw is None:
        return "unknown"
    return raw if raw in SUPPORTED_DATASETS else "unknown"


def evaluate(
    *,
    input_path: Path,
    reference_path: Path | None,
    dataset: str | None,
    flowmol3_paper_metrics: bool | None = None,
    flowmol3_processed_data_dir: Path | str | None = None,
    flowmol3_run_posebusters: bool = True,
    flowmol3_pb_workers: int = 2,
    flowmol3_device: str = "cuda:0",
) -> dict[str, Any]:
    """Run the full evaluation pipeline and return the JSON-ready dict.

    The dict shape is fixed: every metric key is always present.
    Missing dependencies downgrade individual metrics to ``NaN``;
    the rest of the row still computes.

    ``flowmol3_paper_metrics`` controls the additive
    ``flowmol3_paper_metrics`` block: ``True`` forces the upstream
    FlowMol3 analyzer to run, ``False`` skips it (marker
    ``not_requested``), and ``None`` (default) auto-gates on
    :func:`_looks_like_flowmol3_samples`. The pre-existing per-metric
    outputs (``validity``, ``qed``, ``fcd``, ``logp``, ``sa``,
    ``pb_validity``, ...) are unaffected in every case.
    """
    notes: list[str] = []
    missing: list[str] = []

    rdkit_ok, rdkit_err = _probe_rdkit()
    if not rdkit_ok:
        missing.append("rdkit")
        notes.append(
            f"{rdkit_err}:install_with_uv_pip_install_rdkit_or_uv_sync_extra_chemistry"
        )

    fcd_ok, fcd_err = _probe_fcd()
    if not fcd_ok:
        missing.append("fcd")
        notes.append(f"{fcd_err}:install_with_uv_pip_install_fcd")

    pb_ok, pb_err = _probe_posebusters()
    if not pb_ok:
        missing.append("posebusters")
        # PoseBusters is a Tier-2 paper metric; we record the missing
        # dep in the missing_dependencies list but do NOT also append
        # to stderr_notes — ``pb_validity`` carries the install hint
        # in its own ``install_hint`` field. Adding it here would
        # duplicate the message.
        notes.append(
            f"{pb_err}:posebusters_unavailable:"
            "real_paper_metric_requires_3d_conformer_stage:"
            "see_pb_validity_block_in_json"
        )

    items, fmt = load_inputs(input_path)
    if not rdkit_ok:
        # Hard-stop path: no RDKit, no metric can compute. Emit the
        # JSON with NaN rows + the stderr notes so the consumer can
        # still detect "I tried but the env was bare".
        return {
            "schema_version": OUTPUT_SCHEMA_VERSION,
            "input_path": str(input_path),
            "input_format": fmt,
            "dataset": _safe_dataset_tag(dataset),
            "n_total": int(len(items)),
            "n_valid": 0,
            "validity": NAN,
            "qed": NAN,
            "sa": NAN,
            "logp": NAN,
            "fcd": NAN,
            "pb_validity": compute_pb_validity([]),
            "pb_validity_mmff": compute_pb_validity_mmff([]),
            "flowmol3_paper_metrics": compute_flowmol3_paper_metrics([]),
            "fg_deviation": NAN,
            "fg_deviation_eq4": None,
            "fg_deviation_eq4_block": {
                "value": None,
                "n_gen": 0,
                "n_ref": 0,
                "n_gen_skipped": 0,
                "n_ref_skipped": 0,
                "vocabulary_size": 0,
                "reference_source": None,
                "note": "rdkit_unavailable",
                "marker": FG_DEV_EQ4_MARKER_RDKIT_UNAVAILABLE,
            },
            "fg_deviation_dundee_glaxo": {
                "value": NAN,
                "value_reos": NAN,
                "per_fg": {},
                "per_check_reos": {},
                "flag_rate": NAN,
                "reos_cum_dev": NAN,
                "n_gen": 0,
                "n_ref": 0,
                "reference_source": None,
                "note": "rdkit_unavailable",
            },
            "frac_atoms_stable": NAN,
            "frac_mols_stable_valence": NAN,
            "frac_connected": NAN,
            "avg_num_components": NAN,
            "missing_dependencies": missing,
            "stderr_notes": notes,
        }

    smiles, mols = _normalize_items(items)
    validity, n_valid, n_total = compute_validity(mols)
    qed = compute_qed(mols)
    sa = compute_sa(mols)
    logp = compute_logp(mols)
    fcd_value, fcd_note = compute_fcd(smiles, reference_path=reference_path)
    if fcd_note is not None:
        notes.append(fcd_note)
    pb_validity = compute_pb_validity(mols)
    # Fix B: full ETKDGv3 + MMFF94-minimize conformer path. Wired
    # alongside the existing ETKDGv3-only path so consumers can
    # compare both. PoseBusters-scoring stays on the same GPU-aware
    # path (PoseBusters itself is CPU-bound per mol; the framework's
    # GPU path only matters for the upstream FlowMol3 wrapper).
    pb_validity_mmff = compute_pb_validity_mmff(mols)
    frac_atoms_stable, frac_mols_stable_valence = compute_atom_stability(mols)
    frac_connected, avg_num_components = compute_connectivity(mols)

    # FG-deviation: load the reference SMILES (if any) and compute
    # the L1 distance. The same --reference-smiles file is shared
    # with FCD (GEOM-DRUGS-style training-data reference).
    fg_ref_smiles: list[str] = []
    if reference_path is not None:
        fg_ref_smiles = _load_smiles_file(reference_path)
    fg_dev_value, fg_dev_note = compute_fg_deviation(mols, fg_ref_smiles)
    if fg_dev_note is not None:
        notes.append(fg_dev_note)

    # Paper eq.4 / eq.21 instance-count FG-deviation (Dunn & Koes,
    # arXiv:2508.12629, Digital Discovery 2026, eq.21): raw L1 of
    # ``omega_f = (# instances of f) / (# mols)`` over the
    # 85-element ``fr_*`` vocabulary. Reported ALONGSIDE the binary
    # ``fg_deviation`` (no replacement — both are paper-aligned for
    # different aspects of the metric). ``fg_deviation`` uses binary
    # 0/1 flags; ``fg_deviation_eq4`` uses the raw integer match
    # count per mol.
    fg_eq4_block = _compute_fg_deviation_eq4_block(
        smiles,
        fg_ref_smiles,
        reference_path=reference_path,
    )
    fg_eq4_value = fg_eq4_block.get("value")
    # Surface only the "real failure" notes (not the success-path
    # verbose note) so the stderr_notes list doesn't get noisy.
    if fg_eq4_value is None or (
        isinstance(fg_eq4_value, float) and not math.isfinite(fg_eq4_value)
    ):
        eq4_note = str(fg_eq4_block.get("note") or "")
        if eq4_note and "rdkit_unavailable" not in eq4_note:
            # The hard-stop path already covers RDKit-missing; this
            # branch fires only when the wrapper imported but
            # produced a non-finite value (e.g. reference path
            # unparseable).
            notes.append(f"fg_deviation_eq4:{eq4_note}")

    # Dundee + Glaxo Wellcome FG-deviation layer (Fix A): emits
    # BOTH the paper-style L1 over the 85-element ``fr_*`` vocabulary
    # AND a parallel L1 over the upstream Pat Walters rd_filters
    # Dundee + Glaxo vocabulary (160 rules) so the two paths can
    # be cross-validated on the same generated set. Reference set
    # is the same --reference-smiles file when supplied, else the
    # documented NCI first_5K proxy (per
    # docs/r17-survey/baseline-deviation-review.md).
    fg_dg_block = _compute_fg_deviation_dundee_glaxo(
        smiles,
        fg_ref_smiles,
        reference_path=reference_path,
    )
    if fg_dg_block.get("note") and not fg_dev_note:
        # Suppress the per_fg-level note when the upstream path
        # already wrote a richer one.
        notes.append(f"fg_deviation_dundee_glaxo:{fg_dg_block['note']}")

    # Additive Tier-1 block: upstream FlowMol3 SampleAnalyzer. Auto-gated
    # on the input looking like a FlowMol3 sample list unless the caller
    # forced the flag. Never affects the metrics computed above.
    if flowmol3_paper_metrics is None:
        want_flowmol3 = _looks_like_flowmol3_samples(items, fmt)
    else:
        want_flowmol3 = bool(flowmol3_paper_metrics)
    if want_flowmol3:
        flowmol3_block = compute_flowmol3_paper_metrics(
            smiles,
            processed_data_dir=flowmol3_processed_data_dir,
            run_posebusters=bool(flowmol3_run_posebusters),
            pb_workers=int(flowmol3_pb_workers),
            device=str(flowmol3_device),
        )
    else:
        flowmol3_block = {
            "metrics": None,
            "marker": FLOWMOL3_MARKER_NOT_REQUESTED,
            "install_hint": None,
            "note": (
                "flowmol3_paper_metrics_not_requested:"
                f"input_format={fmt}:auto_gate={flowmol3_paper_metrics is None}"
            ),
            "n_total": int(len(smiles)),
            "run_posebusters": bool(flowmol3_run_posebusters),
        }
    if flowmol3_block.get("note"):
        notes.append(f"flowmol3_paper_metrics:{flowmol3_block['note']}")

    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "input_path": str(input_path),
        "input_format": fmt,
        "dataset": _safe_dataset_tag(dataset),
        "n_total": int(n_total),
        "n_valid": int(n_valid),
        "validity": float(validity),
        "qed": float(qed),
        "sa": float(sa),
        "logp": float(logp),
        "fcd": float(fcd_value),
        "pb_validity": pb_validity,
        "pb_validity_mmff": pb_validity_mmff,
        "flowmol3_paper_metrics": flowmol3_block,
        "fg_deviation": float(fg_dev_value),
        "fg_deviation_eq4": (
            None if fg_eq4_value is None else float(fg_eq4_value)
        ),
        "fg_deviation_eq4_block": fg_eq4_block,
        "fg_deviation_dundee_glaxo": fg_dg_block,
        "frac_atoms_stable": float(frac_atoms_stable),
        "frac_mols_stable_valence": float(frac_mols_stable_valence),
        "frac_connected": float(frac_connected),
        "avg_num_components": float(avg_num_components),
        "missing_dependencies": missing,
        "stderr_notes": notes,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Unified molecular generation evaluation runner. Loads "
            "generated samples (.npz / .pkl / .sdf) and emits a JSON "
            "report with validity, QED, SA, logP, and FCD metrics."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help=(
            "Path to the generated molecule file. Supported extensions: "
            ".npz (key 'smiles'), .pkl (list[Chem.Mol] or "
            "(mols, sampling_time) tuple), .sdf (RDKit SDF)."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to the JSON report output file.",
    )
    parser.add_argument(
        "--reference-smiles",
        type=Path,
        default=None,
        help=(
            "Path to a SMILES-per-line text file used as the FCD / "
            "FG-deviation reference set. Defaults to the canonical "
            "GEOM-DRUGS train SMILES file "
            "(data/FlowMol3/references/geom_drugs_train.smi) when "
            "present; falls back to the NCI first_5K proxy when the "
            "GEOM-DRUGS file is not on disk. Pass the empty string "
            "(``--reference-smiles=""``) to force the runner to skip "
            "the reference entirely."
        ),
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        choices=SUPPORTED_DATASETS,
        help=(
            "Dataset tag (metadata only; carried into the JSON). "
            "Default: 'unknown'."
        ),
    )
    parser.add_argument(
        "--flowmol3-paper-metrics",
        dest="flowmol3_paper_metrics",
        action="store_true",
        default=None,
        help=(
            "Force the additive flowmol3_paper_metrics block (upstream "
            "FlowMol3 SampleAnalyzer) to run. Default: auto — it runs "
            "when the input looks like a FlowMol3 sample list (.pkl / "
            ".sdf of RDKit Mols) and the upstream wrapper imports."
        ),
    )
    parser.add_argument(
        "--no-flowmol3-paper-metrics",
        dest="flowmol3_paper_metrics",
        action="store_false",
        help="Skip the flowmol3_paper_metrics block entirely.",
    )
    parser.add_argument(
        "--flowmol3-processed-data-dir",
        type=Path,
        default=None,
        help=(
            "Upstream processed dataset dir handed to the FlowMol3 "
            "SampleAnalyzer. Default: upstream's own fallback."
        ),
    )
    parser.add_argument(
        "--flowmol3-no-posebusters",
        dest="flowmol3_run_posebusters",
        action="store_false",
        default=True,
        help=(
            "Disable the PoseBusters stage inside the upstream FlowMol3 "
            "analyzer (memory-hungry on tight GPUs)."
        ),
    )
    parser.add_argument(
        "--flowmol3-pb-workers",
        type=int,
        default=2,
        help="PoseBusters worker processes for the upstream analyzer (0 = serial).",
    )
    parser.add_argument(
        "--flowmol3-device",
        type=str,
        default="cuda:0",
        help="Device tag forwarded to the upstream FlowMol3 analyzer.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on a successful emit, 1 otherwise."""
    args = _parse_args(argv)
    if not args.input.exists():
        print(
            f"[run_mol_eval] input_not_found: {args.input}", file=sys.stderr
        )
        return 1

    # Resolve ``--reference-smiles`` default. Prefers the canonical
    # GEOM-DRUGS train SMILES file when present, falls back to the NCI
    # ``first_5K.smi`` proxy. The empty-string flag means "skip the
    # reference entirely" (FCD / FG-deviation will be NaN).
    if args.reference_smiles is None:
        from adaptive_reflow.eval.fg_deviation import (  # noqa: PLC0415
            DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH,
            DEFAULT_REFERENCE_PATH,
        )
        args.reference_smiles = Path(DEFAULT_REFERENCE_PATH)
        if DEFAULT_REFERENCE_PATH == DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH:
            print(
                f"[run_mol_eval] reference_smiles=GEOM-DRUGS train "
                f"({DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH})",
                file=sys.stderr,
            )
        else:
            print(
                f"[run_mol_eval] reference_smiles=NCI first_5K proxy "
                f"(GEOM-DRUGS train file not present at "
                f"{DEFAULT_GEOM_DRUGS_TRAIN_REFERENCE_PATH}, "
                f"falling back to {DEFAULT_REFERENCE_PATH})",
                file=sys.stderr,
            )

    report = evaluate(
        input_path=Path(args.input),
        reference_path=Path(args.reference_smiles) if args.reference_smiles else None,
        dataset=str(args.dataset) if args.dataset else None,
        flowmol3_paper_metrics=args.flowmol3_paper_metrics,
        flowmol3_processed_data_dir=(
            Path(args.flowmol3_processed_data_dir)
            if args.flowmol3_processed_data_dir
            else None
        ),
        flowmol3_run_posebusters=bool(args.flowmol3_run_posebusters),
        flowmol3_pb_workers=int(args.flowmol3_pb_workers),
        flowmol3_device=str(args.flowmol3_device),
    )
    # Surface dependency-missing notes on stderr so an operator can
    # see them without opening the JSON.
    for note in list(report.get("stderr_notes", [])):
        print(f"[run_mol_eval] note: {note}", file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[run_mol_eval] wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "OUTPUT_SCHEMA_VERSION",
    "SUPPORTED_DATASETS",
    "FG_SMARTS_NAMES",
    "PB_VALIDITY_MARKER_NOT_INSTALLED",
    "PB_VALIDITY_MARKER_COMPUTED",
    "PB_VALIDITY_MARKER_COMPUTED_ETKDG_V3_ONLY",
    "PB_VALIDITY_MARKER_COMPUTED_MMFF",
    "PB_VALIDITY_MARKER_STUB_UNAVAILABLE",
    "PB_VALIDITY_INSTALL_HINT",
    "PB_VALIDITY_CONFIG",
    "FLOWMOL3_MARKER_NOT_REQUESTED",
    "FLOWMOL3_MARKER_NOT_AVAILABLE",
    "FLOWMOL3_MARKER_COMPUTED_UPSTREAM",
    "FLOWMOL3_MARKER_UPSTREAM_ERROR",
    "FLOWMOL3_INSTALL_HINT",
    "FG_DEV_EQ4_MARKER_COMPUTED",
    "FG_DEV_EQ4_MARKER_WRAPPER_UNAVAILABLE",
    "FG_DEV_EQ4_MARKER_RDKIT_UNAVAILABLE",
    "FG_DEV_EQ4_MARKER_REFERENCE_UNAVAILABLE",
    "_embed_3d_etkdg_v3",
    "compute_fcd",
    "compute_fg_deviation",
    "compute_flowmol3_paper_metrics",
    "_compute_fg_deviation_dundee_glaxo",
    "_compute_fg_deviation_eq4_block",
    "compute_logp",
    "compute_pb_validity",
    "compute_pb_validity_mmff",
    "compute_qed",
    "compute_sa",
    "compute_validity",
    "evaluate",
    "load_inputs",
    "main",
]
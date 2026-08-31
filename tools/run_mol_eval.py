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

The runner never imports the FlowMol3 evaluation library (``posebusters``,
``useful_rdkit_utils``, ``dgl``, ``xtb``) — those live behind a
subprocess boundary per Phase-1 risk register. This script is the
in-process arm: same-task baseline vs framework comparison.

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
OUTPUT_SCHEMA_VERSION: str = "1.0.0"

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
    """
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


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
) -> dict[str, Any]:
    """Run the full evaluation pipeline and return the JSON-ready dict.

    The dict shape is fixed: every metric key is always present.
    Missing dependencies downgrade individual metrics to ``NaN``;
    the rest of the row still computes.
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
            "Path to a SMILES-per-line text file used as the FCD "
            "reference set. Optional; FCD is NaN when omitted."
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on a successful emit, 1 otherwise."""
    args = _parse_args(argv)
    if not args.input.exists():
        print(
            f"[run_mol_eval] input_not_found: {args.input}", file=sys.stderr
        )
        return 1

    report = evaluate(
        input_path=Path(args.input),
        reference_path=Path(args.reference_smiles) if args.reference_smiles else None,
        dataset=str(args.dataset) if args.dataset else None,
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
    "compute_fcd",
    "compute_logp",
    "compute_qed",
    "compute_sa",
    "compute_validity",
    "evaluate",
    "load_inputs",
    "main",
]
"""Per-position frequency L1 distance between generated and natural amino-acid
distributions (ProtBFN / AbBFN paper metric surface).

Implements the ``freq_l1`` metric described in
``docs/r17-survey/prot-comparison.md`` §5a (Phase-C+ metric surface,
future work) and ``docs/r17-survey/baseline-deviation-review.md`` §4.5.
The metric is **pure Python + numpy** — no ``mmseqs2``, no UniRef50
download, no ESMFold, no HF weights.

Definition
----------

For each position ``i`` in a fixed length ``L`` (the longest generated
sequence, truncated at ``max_length``), let::

    p_gen[i]      = empirical AA distribution over generated sequences at pos i
    p_natural[i]  = empirical AA distribution over the reference MSA at pos i

then::

    freq_l1_per_position[i] = ||p_gen[i] - p_natural[i]||_1
                            = sum_a | p_gen[i][a] - p_natural[i][a] |

where the sum runs over the 20-standard amino-acid alphabet
(``STANDARD_AA_ALPHABET``). Two scalar summaries are emitted::

    freq_l1_mean     = mean over positions of freq_l1_per_position
    freq_l1_overall  = || p_gen_global - p_natural_global ||_1
                     (single L1 between the length-pooled AA histograms)

Both scalar summaries lie in ``[0, 2]`` (a uniform 1/20 vs a delta
distribution scores 2 * 19/20 ≈ 1.9). A perfectly matched generator
scores 0; a generator that emits a single constant AA across all
positions scores ~1.9; a uniform random generator against a delta
reference scores ~1.9 too.

Reference distribution
----------------------

Two reference modes are supported without any external dependency:

* ``reference="flat"`` (default): ``p_natural[i] = uniform(20)`` for
  every position. This is the **standard amino-acid prior** used in
  ProtBFN §4 evaluation (Engelhart et al., 2024) when no held-out
  natural set is supplied; it measures *deviation from random* and is
  useful as a Phase-C+ smoke.
* ``reference=<path>``: 1-pass empirical AA histogram over the supplied
  FASTA — by default the bundled
  ``data/protbfn_abbfn/repo/example_inputs/sequences.fasta`` (12 VH
  sequences shipped with the upstream InstaDeep repo). This gives a
  **real natural reference** without needing UniRef50.

When the reference FASTA contains sequences shorter than ``L``, the
missing positions are filled with the length-pooled natural AA
distribution so the per-position math is well defined for the long
generated sequences (the ProtBFN paper does the same for held-out
sets of mixed length).

Per-position clamping + smoothing
---------------------------------

Positions where no generated residue landed (e.g. an AbBFN output
shorter than the generated length) and positions where no natural
residue landed (e.g. reference sequences all shorter than ``L``) are
**explicitly zero-filled** in the AA histogram. Positions with very
few observations (less than ``min_count``) are smoothed toward the
length-pooled global distribution with weight ``smoothing``; this
matches the Bayesian add-α smoothing the ProtBFN paper uses to avoid
zero-count artefacts.

Public surface
--------------

* :data:`STANDARD_AA_ALPHABET` — 20-letter canonical AA alphabet.
* :data:`BUNDLED_NATURAL_FASTA` — default reference MSA path.
* :func:`per_position_freq_l1` — per-position L1 + aggregate block.
* :func:`compute_freq_l1_block` — paper-format block for two FASTAs.
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

__all__ = [
    "STANDARD_AA_ALPHABET",
    "BUNDLED_NATURAL_FASTA",
    "DEFAULT_MAX_LENGTH",
    "DEFAULT_MIN_COUNT",
    "DEFAULT_SMOOTHING",
    "per_position_freq_l1",
    "compute_freq_l1_block",
]

#: 20-standard amino-acid alphabet, alphabetical. Matches UniProt
#: canonical composition literature (e.g. Engelhart et al. 2024,
#: ProtBFN §4.5 supplementary) and the engine-side surface AA channel
#: exposed by :mod:`adaptive_reflow.molecular.materializer` (indices
#: 1..20 of :data:`PROTBFN_AMINO_ACID_MASSES_DA`).
STANDARD_AA_ALPHABET: tuple[str, ...] = (
    "A", "C", "D", "E", "F", "G", "H", "I", "K", "L",
    "M", "N", "P", "Q", "R", "S", "T", "V", "W", "Y",
)

#: Default location of the bundled upstream InstaDeep ProtBFN example
#: MSA (12 antibody-VH chains). Used as the empirical natural-protein
#: reference when the caller does not supply one of their own.
BUNDLED_NATURAL_FASTA: str = (
    "data/protbfn_abbfn/repo/example_inputs/sequences.fasta"
)

#: Default generated-sequence truncation length. ProtBFN / AbBFN emit
#: variable-length sequences; we pool the AA histogram up to this
#: position. The upstream sample / inpaint scripts cap at 128-256 for
#: antibody-VH, so 128 is a sensible Phase-C+ default that keeps the
#: metric matrix small while still covering the IMGT-numbered frame.
DEFAULT_MAX_LENGTH: int = 128

#: Per-position AA count below which the histogram is add-α smoothed
#: toward the length-pooled global distribution. Set to ``0`` to
#: disable smoothing (the ProtBFN paper defaults to ``alpha=1`` which
#: is roughly equivalent to ``smoothing=0.5`` at small counts).
DEFAULT_MIN_COUNT: int = 1

#: Smoothing weight toward the length-pooled global distribution when
#: the per-position count is below :data:`DEFAULT_MIN_COUNT`. The
#: effective posterior is ``(count + smoothing * global_count) /
#: (total + smoothing)``.
DEFAULT_SMOOTHING: float = 1.0


def _read_fasta_simple(path: str | Path) -> list[tuple[str, str]]:
    """Dependency-free FASTA parser.

    Returns ``[(record_id, sequence), ...]``. Tries Biopython's
    ``SeqIO`` when importable so this module honours the same fallback
    contract as :mod:`adaptive_reflow.eval.amino_acid_recovery`; the
    module never hard-fails on a missing optional dependency.
    """
    fasta_path = Path(path)
    if not fasta_path.is_file():
        raise FileNotFoundError(f"fasta_not_found:{fasta_path}")
    try:
        from Bio import SeqIO

        return [
            (str(rec.id), str(rec.seq))
            for rec in SeqIO.parse(str(fasta_path), "fasta")  # type: ignore[no-untyped-call]
        ]
    except ImportError:
        pass

    records: list[tuple[str, str]] = []
    header: str | None = None
    chunks: list[str] = []
    with fasta_path.open("r") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    records.append((header, "".join(chunks)))
                header = line[1:].strip() or f"seq{len(records)}"
                chunks = []
            elif header is not None:
                chunks.append(line)
    if header is not None:
        records.append((header, "".join(chunks)))
    return records


def _collect_aa_histograms(
    sequences: Iterable[tuple[str, str]],
    *,
    max_length: int,
    alphabet: tuple[str, ...] = STANDARD_AA_ALPHABET,
) -> np.ndarray:
    """Per-position AA count matrix of shape ``(max_length, |alphabet|)``.

    Sequences shorter than ``max_length`` contribute zero counts to
    the trailing positions; positions where no residue landed are
    therefore easy to detect downstream (``row.sum() == 0``).
    """
    aa_to_idx = {aa: i for i, aa in enumerate(alphabet)}
    counts = np.zeros((max_length, len(alphabet)), dtype=np.float64)  # type: ignore[var-annotated]
    for _rid, seq in sequences:
        upper = seq.strip().upper()
        n = min(len(upper), max_length)
        for idx in range(n):
            ch = upper[idx]
            j = aa_to_idx.get(ch)
            if j is not None:
                counts[idx, j] += 1.0
    return counts


def _smooth_histograms(
    counts: np.ndarray,
    *,
    min_count: int,
    smoothing: float,
) -> np.ndarray:
    """Convert raw counts into smoothed probability matrices.

    Adds a fraction of the global (length-pooled) distribution to
    every row, then row-normalises. Rows whose raw count exceeds
    ``min_count`` keep their empirical shape; under-populated rows
    collapse toward the global mix.
    """
    total = counts.sum(axis=1, keepdims=True)  # (max_length, 1)
    global_dist = counts.sum(axis=0)  # (|alphabet|,)
    global_total = global_dist.sum()
    if global_total > 0:
        global_dist = global_dist / global_total
    else:
        # No residues observed at all; fall back to a uniform global.
        global_dist = np.full_like(global_dist, 1.0 / global_dist.size)

    # Rows whose total count is below the threshold get the smoothing
    # weight blended in fully; rows above it are left alone and only
    # renormalised at the end.
    row_total = total.squeeze(axis=1)  # (max_length,)
    sparse_mask = row_total < max(float(min_count), 1.0)
    smooth_counts = counts + smoothing * global_dist[None, :]
    smoothed = np.where(sparse_mask[:, None], smooth_counts, counts)
    smoothed_total = smoothed.sum(axis=1, keepdims=True)
    # Avoid divide-by-zero on rows that contain only zero counts even
    # after smoothing (should not happen but defensive).
    safe_total = np.where(smoothed_total > 0, smoothed_total, 1.0)
    return smoothed / safe_total  # type: ignore[no-any-return]


def _global_distribution(histograms: np.ndarray) -> np.ndarray:
    """Length-pooled AA distribution from a per-position count matrix."""
    total = histograms.sum(axis=0)
    if total.sum() <= 0:
        return np.full_like(total, 1.0 / total.size)  # type: ignore[no-any-return]
    return total / total.sum()  # type: ignore[no-any-return]


def _flat_reference(max_length: int) -> np.ndarray:
    """Flat 1/20 prior as a per-position distribution matrix."""
    n_aa = len(STANDARD_AA_ALPHABET)
    return np.full((max_length, n_aa), 1.0 / n_aa)


def per_position_freq_l1(
    generated: list[tuple[str, str]] | str | Path,
    *,
    reference: list[tuple[str, str]] | str | Path | None = None,
    max_length: int = DEFAULT_MAX_LENGTH,
    min_count: int = DEFAULT_MIN_COUNT,
    smoothing: float = DEFAULT_SMOOTHING,
) -> dict[str, Any]:
    """Per-position L1 distance between generated and natural AA histograms.

    Parameters
    ----------
    generated:
        Either a parsed ``[(record_id, sequence), ...]`` list or a
        path to a FASTA file of model-generated sequences.
    reference:
        ``None`` → flat 1/20 prior;
        ``"flat"`` → flat 1/20 prior (explicit alias);
        a parsed list → empirical histograms over those sequences;
        a path → parsed via :func:`_read_fasta_simple`.
    max_length:
        Truncate sequences to this length (per-position matrix size).
    min_count:
        Smoothing trigger; rows with fewer than this many observations
        are smoothed toward the length-pooled global distribution.
    smoothing:
        Smoothing weight (see :func:`_smooth_histograms`).

    Returns
    -------
    dict
        Block with the following keys:

        * ``per_position_l1`` — ``np.ndarray`` of shape ``(max_length,)``
          with the per-position L1 distance in ``[0, 2]``.
        * ``mean_l1`` — scalar mean over the per-position vector.
        * ``overall_l1`` — single L1 between the length-pooled
          histograms (``[0, 2]``).
        * ``reference_mode`` — ``"flat"`` or ``"empirical"``.
        * ``reference_path`` — string path or ``None``.
        * ``n_generated`` — count of generated sequences read.
        * ``max_length`` — truncation length used.
        * ``generated_counts`` — ``(max_length, 20)`` raw count matrix.
        * ``reference_counts`` — ``(max_length, 20)`` raw count matrix
          (``None`` in flat-reference mode).
        * ``generated_distribution`` / ``reference_distribution`` —
          the smoothed per-position probability matrices.
        * ``alphabet`` — the 20-letter AA alphabet used.
    """
    # ------------------------------------------------------------------
    # 1. Coerce generated input to a parsed FASTA list.
    # ------------------------------------------------------------------
    if isinstance(generated, (str, Path)):
        gen_records = _read_fasta_simple(generated)
    else:
        gen_records = list(generated)

    # ------------------------------------------------------------------
    # 2. Resolve the reference distribution.
    # ------------------------------------------------------------------
    flat_mode = reference is None or (
        isinstance(reference, str) and reference.lower() == "flat"
    )
    ref_records: list[tuple[str, str]] | None = None
    ref_path: str | None = None
    if flat_mode:
        ref_path = None
    else:
        if isinstance(reference, (str, Path)):
            ref_path = str(reference)
            ref_records = _read_fasta_simple(reference)
        else:
            ref_records = list(reference) if reference is not None else None
            ref_path = "<in-memory>"

    # ------------------------------------------------------------------
    # 3. Build the count matrices and smooth.
    # ------------------------------------------------------------------
    len(STANDARD_AA_ALPHABET)
    if max_length <= 0:
        raise ValueError(f"max_length_must_be_positive:{max_length}")

    gen_counts = _collect_aa_histograms(
        gen_records, max_length=max_length
    )
    gen_dist = _smooth_histograms(
        gen_counts, min_count=min_count, smoothing=smoothing
    )
    if flat_mode:
        ref_counts = None
        ref_dist = _flat_reference(max_length)
    else:
        assert ref_records is not None  # mypy hint
        ref_counts = _collect_aa_histograms(
            ref_records, max_length=max_length
        )
        ref_dist = _smooth_histograms(
            ref_counts, min_count=min_count, smoothing=smoothing
        )

    # ------------------------------------------------------------------
    # 4. Compute per-position L1 and the length-pooled summary.
    # ------------------------------------------------------------------
    per_position_l1 = np.sum(np.abs(gen_dist - ref_dist), axis=1)
    mean_l1 = float(per_position_l1.mean()) if per_position_l1.size else float("nan")
    gen_global = gen_dist.mean(axis=0)
    ref_global = ref_dist.mean(axis=0)
    overall_l1 = float(np.sum(np.abs(gen_global - ref_global)))

    return {
        "per_position_l1": per_position_l1,
        "mean_l1": mean_l1,
        "overall_l1": overall_l1,
        "reference_mode": "flat" if flat_mode else "empirical",
        "reference_path": ref_path,
        "n_generated": len(gen_records),
        "max_length": int(max_length),
        "generated_counts": gen_counts,
        "reference_counts": ref_counts,
        "generated_distribution": gen_dist,
        "reference_distribution": ref_dist,
        "alphabet": tuple(STANDARD_AA_ALPHABET),
    }


def compute_freq_l1_block(
    generated_fasta_path: str | Path,
    reference_fasta_path: str | Path | None = None,
    *,
    max_length: int = DEFAULT_MAX_LENGTH,
    min_count: int = DEFAULT_MIN_COUNT,
    smoothing: float = DEFAULT_SMOOTHING,
) -> dict[str, Any]:
    """Compute the paper-format ``freq_l1`` block for two FASTA files.

    Returns
    -------
    dict
        ``status`` is ``"computed"`` on success or
        ``"not_computed:<reason>"`` when the inputs cannot be read.
        On success the block carries the per-position L1 vector
        serialised to ``per_position_l1`` (Python list of floats), the
        two scalar summaries (``mean_l1``, ``overall_l1``), the AA
        alphabet, the reference-mode marker (``"flat"`` or
        ``"empirical"``), the path to the reference FASTA (or
        ``None``), and the number of generated / reference sequences
        that were pooled into the histograms.
    """
    block: dict[str, Any] = {
        "alphabet": list(STANDARD_AA_ALPHABET),
        "max_length": int(max_length),
        "min_count": int(min_count),
        "smoothing": float(smoothing),
    }

    try:
        result = per_position_freq_l1(
            Path(generated_fasta_path),
            reference=reference_fasta_path,
            max_length=max_length,
            min_count=min_count,
            smoothing=smoothing,
        )
    except FileNotFoundError as exc:
        block["status"] = f"not_computed:file_not_found:{exc}"
        block["generated_fasta"] = str(generated_fasta_path)
        block["reference_fasta"] = (
            str(reference_fasta_path) if reference_fasta_path else None
        )
        return block
    except Exception as exc:  # pragma: no cover — defensive
        block["status"] = f"not_computed:error:{type(exc).__name__}:{exc}"
        block["generated_fasta"] = str(generated_fasta_path)
        block["reference_fasta"] = (
            str(reference_fasta_path) if reference_fasta_path else None
        )
        return block

    if result["n_generated"] == 0:
        block["status"] = "not_computed:empty_generated_fasta"
        block["generated_fasta"] = str(generated_fasta_path)
        block["reference_fasta"] = (
            str(reference_fasta_path) if reference_fasta_path else None
        )
        return block

    block["status"] = "computed"
    block["generated_fasta"] = str(generated_fasta_path)
    block["reference_fasta"] = (
        str(reference_fasta_path) if reference_fasta_path else None
    )
    block["reference_mode"] = result["reference_mode"]
    block["n_generated"] = result["n_generated"]
    block["mean_l1"] = result["mean_l1"]
    block["overall_l1"] = result["overall_l1"]
    # Per-position vector serialised to a Python list for JSON-friendliness.
    block["per_position_l1"] = [float(x) for x in result["per_position_l1"]]
    # Per-position AA histogram for the generated sequences (as a
    # nested list) — small enough to ship in summary.json for
    # downstream post-hoc analysis; max_length * 20 = 2560 floats.
    block["generated_aa_histogram"] = result["generated_counts"].astype(int).tolist()
    if result["reference_counts"] is not None:
        block["reference_aa_histogram"] = (
            result["reference_counts"].astype(int).tolist()
        )
    else:
        block["reference_aa_histogram"] = None
    # Convenience placeholder: arithmetic delta vs an all-uniform
    # 1/20 distribution would just be zero against itself. Reserved
    # for the next metric that adds a paper-reference number for
    # freq_l1; intentionally left as a no-op so the block is shape-
    # compatible with downstream consumers.
    return block

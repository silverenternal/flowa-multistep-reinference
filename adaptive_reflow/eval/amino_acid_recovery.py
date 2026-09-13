"""Per-region Amino Acid Recovery (AAR) for IMGT-numbered antibody VH domains.

Implements the AbBFN per-region AAR metric described in
``docs/r17-survey/baseline-deviation-review.md`` §4.4 / §4.5 (repair
step 2). The metric is **pure Python** — Biopython is used only as an
optional FASTA reader, and a built-in fallback parser is used when it
is not importable.

Definition
----------

AbBFN reports amino-acid recovery for a masked-region inpainting task:
a VH sequence is IMGT-numbered, one or more regions are masked, the
model regenerates them, and recovery is the fraction of positions whose
regenerated residue equals the ground-truth residue::

    AAR(region) = #{i in region : generated[i] == reference[i]}
                  / #{i in region : reference[i] is a residue}

Because the comparison happens *after* IMGT numbering, both sequences
occupy the same coordinate frame and no MSA is required: the metric is
a straight position-by-position comparison over the numbered frame.

IMGT unique numbering for V-DOMAINs (Lefranc et al., *Dev. Comp.
Immunol.* 27:55-77, 2003) fixes the VH frame at 128 positions with
region boundaries that do **not** move between sequences — gaps are
inserted at prescribed positions instead. The seven-region partition
used here is the standard one:

===========  ==========  ======
Region       Positions   Length
===========  ==========  ======
FR1          1-26        26
CDR1         27-38       12
FR2          39-55       17
CDR2         56-65       10
FR3          66-104      39
CDR3         105-117     13
FR4          118-128     11
===========  ==========  ======

Sequences shorter than 128 are compared over the positions they do
occupy; positions where the *reference* carries a gap character
(``-`` / ``.``) or the mask token (``X``) are excluded from both the
numerator and the denominator, matching the IMGT convention that gap
positions are placeholders rather than residues.

Paper reference numbers (AbBFN, §4.2) for the aggregate buckets are
kept in :data:`PAPER_REFERENCE_AAR` so a harness can print measured vs.
paper side by side without hard-coding literals at the call site.

Public surface
--------------

* :func:`imgt_vh_numbering` - position (1-128) -> region name.
* :func:`per_region_aar` - per-region recovery for one sequence pair.
* :func:`compute_aar_block` - aggregate paper-format block for two
  FASTA files.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

__all__ = [
    "IMGT_VH_LENGTH",
    "IMGT_VH_REGION_BOUNDS",
    "REGION_NAMES",
    "FR_REGIONS",
    "CDR_REGIONS",
    "PAPER_REFERENCE_AAR",
    "GAP_CHARS",
    "imgt_vh_numbering",
    "per_region_aar",
    "read_fasta",
    "compute_aar_block",
]

#: Length of the IMGT unique-numbering frame for a VH domain.
IMGT_VH_LENGTH: int = 128

#: Inclusive ``(start, end)`` 1-based position bounds per region, in
#: N-to-C order. IMGT unique numbering (Lefranc et al. 2003).
IMGT_VH_REGION_BOUNDS: tuple[tuple[str, int, int], ...] = (
    ("FR1", 1, 26),
    ("CDR1", 27, 38),
    ("FR2", 39, 55),
    ("CDR2", 56, 65),
    ("FR3", 66, 104),
    ("CDR3", 105, 117),
    ("FR4", 118, 128),
)

#: Region names in N-to-C order.
REGION_NAMES: tuple[str, ...] = tuple(name for name, _, _ in IMGT_VH_REGION_BOUNDS)

#: Framework regions (the ``aar_fr_all`` bucket).
FR_REGIONS: tuple[str, ...] = ("FR1", "FR2", "FR3", "FR4")

#: Complementarity-determining regions (the ``aar_cdr_all`` bucket).
CDR_REGIONS: tuple[str, ...] = ("CDR1", "CDR2", "CDR3")

#: Map a region name onto the paper's heavy-chain key spelling.
_PAPER_KEY: dict[str, str] = {
    "FR1": "aar_fr1",
    "FR2": "aar_fr2",
    "FR3": "aar_fr3",
    "FR4": "aar_fr4",
    "CDR1": "aar_cdr_h1",
    "CDR2": "aar_cdr_h2",
    "CDR3": "aar_cdr_h3",
}

#: Characters treated as "not a residue" and excluded from the metric.
GAP_CHARS: frozenset[str] = frozenset({"-", ".", "*", " ", "X", "x"})

#: AbBFN paper-reported values (§4.2, Table 2 of "Protein Sequence
#: Modelling with Bayesian Flow Networks", Atkinson et al.,
#: arXiv:2401.14048 / Nature Communications 2025, DOI
#: 10.1038/s41467-025-58250-2). The table reports AAR on 20 000 VH
#: chains sampled uniformly from OAS for the zero-shot conditional
#: generation task; AbBFN's training data was cleaned of sequences
#: similar to the test set, so the figures are a clean (not leaked)
#: reference. Paper values are reported as percentages in the table;
#: we store them as fractions to match the measured metric.
PAPER_REFERENCE_AAR: dict[str, float] = {
    # Per-framework regions (Table 2, "AbBFN" row).
    "aar_fr1": 0.962,    # FR-H1
    "aar_fr2": 0.965,    # FR-H2
    "aar_fr3": 0.942,    # FR-H3
    "aar_fr4": 0.969,    # FR-H4
    "aar_fr_all": 0.956, # FR (all)
    # Per-CDR regions (Table 2, "AbBFN" row).
    "aar_cdr_h1": 0.904,
    "aar_cdr_h2": 0.885,
    "aar_cdr_h3": 0.431,
    "aar_cdr_all": 0.678,
}


def imgt_vh_numbering() -> dict[int, str]:
    """Return the IMGT VH position -> region map for positions 1-128.

    Returns
    -------
    dict[int, str]
        Keys are 1-based IMGT positions ``1 .. 128``; values are one of
        ``"FR1"``, ``"CDR1"``, ``"FR2"``, ``"CDR2"``, ``"FR3"``,
        ``"CDR3"``, ``"FR4"``.
    """
    mapping: dict[int, str] = {}
    for name, start, end in IMGT_VH_REGION_BOUNDS:
        for pos in range(start, end + 1):
            mapping[pos] = name
    return mapping


def _is_residue(char: str) -> bool:
    """``True`` iff ``char`` counts as a comparable residue."""
    return bool(char) and char not in GAP_CHARS


def per_region_aar(generated_seq: str, reference_seq: str) -> dict[str, float]:
    """Per-region amino-acid recovery between two IMGT-numbered VH strings.

    Both inputs are assumed to already sit in the IMGT frame (that is,
    index ``i`` of each string is IMGT position ``i + 1``), which is
    what the AbBFN inpainting task produces: the model regenerates
    masked positions of an existing numbered sequence, so lengths and
    coordinates already agree and no MSA is needed.

    Positions are compared up to ``min(len(generated), len(reference),
    128)``. A position contributes to a region's denominator only when
    the *reference* residue is a real residue (see :data:`GAP_CHARS`);
    it contributes to the numerator when the generated residue matches
    it exactly (case-insensitively).

    Parameters
    ----------
    generated_seq:
        The model-generated VH sequence.
    reference_seq:
        The ground-truth VH sequence.

    Returns
    -------
    dict[str, float]
        Seven per-region keys (``"FR1"`` ... ``"FR4"``) plus the
        aggregate buckets ``"aar_fr_all"``, ``"aar_cdr_all"`` and
        ``"aar_all"``. A region with no comparable positions yields
        ``float("nan")`` (never a silently-zero score).

    Raises
    ------
    TypeError
        If either argument is not a string.
    """
    if not isinstance(generated_seq, str) or not isinstance(reference_seq, str):
        raise TypeError("per_region_aar_requires_str_inputs")

    gen = generated_seq.strip().upper()
    ref = reference_seq.strip().upper()
    numbering = imgt_vh_numbering()

    matches: dict[str, int] = {name: 0 for name in REGION_NAMES}
    totals: dict[str, int] = {name: 0 for name in REGION_NAMES}

    n_compare = min(len(gen), len(ref), IMGT_VH_LENGTH)
    for idx in range(n_compare):
        region = numbering[idx + 1]
        ref_char = ref[idx]
        if not _is_residue(ref_char):
            continue
        totals[region] += 1
        if gen[idx] == ref_char:
            matches[region] += 1

    def _ratio(num: int, den: int) -> float:
        return float(num) / float(den) if den > 0 else float("nan")

    out: dict[str, float] = {
        name: _ratio(matches[name], totals[name]) for name in REGION_NAMES
    }
    fr_num = sum(matches[name] for name in FR_REGIONS)
    fr_den = sum(totals[name] for name in FR_REGIONS)
    cdr_num = sum(matches[name] for name in CDR_REGIONS)
    cdr_den = sum(totals[name] for name in CDR_REGIONS)
    out["aar_fr_all"] = _ratio(fr_num, fr_den)
    out["aar_cdr_all"] = _ratio(cdr_num, cdr_den)
    out["aar_all"] = _ratio(fr_num + cdr_num, fr_den + cdr_den)
    return out


def read_fasta(path: str | Path) -> list[tuple[str, str]]:
    """Read a FASTA file into ``[(record_id, sequence), ...]``.

    Uses Biopython's ``SeqIO`` when importable (it is present in
    ``.venvs/protbfn_venv``) and falls back to a dependency-free parser
    otherwise, so this module never hard-fails on a missing optional
    dependency.
    """
    fasta_path = Path(path)
    if not fasta_path.is_file():
        raise FileNotFoundError(f"fasta_not_found:{fasta_path}")
    try:
        from Bio import SeqIO  # type: ignore[import-not-found]

        return [
            (str(rec.id), str(rec.seq))
            for rec in SeqIO.parse(str(fasta_path), "fasta")
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


def _pair_records(
    generated: list[tuple[str, str]],
    reference: list[tuple[str, str]],
) -> list[tuple[str, str, str]]:
    """Pair generated with reference records.

    Pairs by record id when every generated id has a reference
    counterpart; otherwise falls back to positional pairing over the
    common prefix (the order the SOTA harness writes samples in).
    """
    ref_by_id = {rid: seq for rid, seq in reference}
    if generated and all(rid in ref_by_id for rid, _ in generated):
        return [(rid, seq, ref_by_id[rid]) for rid, seq in generated]
    pairs: list[tuple[str, str, str]] = []
    for (gid, gseq), (_rid, rseq) in zip(generated, reference):
        pairs.append((gid, gseq, rseq))
    return pairs


def _micro_average(
    pairs: Iterable[tuple[str, str, str]],
) -> tuple[dict[str, int], dict[str, int], int]:
    """Accumulate per-region match/total counts across sequence pairs."""
    numbering = imgt_vh_numbering()
    matches: dict[str, int] = {name: 0 for name in REGION_NAMES}
    totals: dict[str, int] = {name: 0 for name in REGION_NAMES}
    n_pairs = 0
    for _pid, gen, ref in pairs:
        n_pairs += 1
        gen_u = gen.strip().upper()
        ref_u = ref.strip().upper()
        for idx in range(min(len(gen_u), len(ref_u), IMGT_VH_LENGTH)):
            ref_char = ref_u[idx]
            if not _is_residue(ref_char):
                continue
            region = numbering[idx + 1]
            totals[region] += 1
            if gen_u[idx] == ref_char:
                matches[region] += 1
    return matches, totals, n_pairs


def compute_aar_block(
    generated_fasta_path: str,
    reference_fasta_path: str,
) -> dict[str, Any]:
    """Compute the aggregated, paper-format AAR block for two FASTA files.

    The reported numbers are **micro-averages**: per-region match and
    denominator counts are pooled across all sequence pairs before the
    ratio is taken, which is what a per-position recovery rate means
    and which avoids over-weighting short sequences.

    Parameters
    ----------
    generated_fasta_path:
        FASTA of model-generated VH sequences (e.g. the SOTA harness's
        ``samples.fasta``).
    reference_fasta_path:
        FASTA of ground-truth VH sequences in the same IMGT frame.

    Returns
    -------
    dict
        ``status`` is ``"computed"`` on success or
        ``"not_computed:<reason>"`` when the inputs cannot be paired.
        On success the block carries the paper key spellings
        (``aar_fr1`` ... ``aar_cdr_h3``, ``aar_fr_all``,
        ``aar_cdr_all``, ``aar_all``), the per-region denominators
        under ``n_positions``, ``n_pairs``, the numbering scheme, and
        the paper-reported reference values under ``paper_reference``.
    """
    generated = read_fasta(generated_fasta_path)
    reference = read_fasta(reference_fasta_path)

    block: dict[str, Any] = {
        "numbering_scheme": "IMGT_VH_unique_numbering_1_128",
        "aggregation": "micro_average_over_positions",
        "generated_fasta": str(generated_fasta_path),
        "reference_fasta": str(reference_fasta_path),
        "n_generated": len(generated),
        "n_reference": len(reference),
        "paper_reference": dict(PAPER_REFERENCE_AAR),
    }

    if not generated or not reference:
        block["status"] = "not_computed:empty_fasta"
        block["n_pairs"] = 0
        return block

    pairs = _pair_records(generated, reference)
    matches, totals, n_pairs = _micro_average(pairs)
    if n_pairs == 0 or sum(totals.values()) == 0:
        block["status"] = "not_computed:no_comparable_positions"
        block["n_pairs"] = n_pairs
        return block

    def _ratio(num: int, den: int) -> float | None:
        return float(num) / float(den) if den > 0 else None

    block["status"] = "computed"
    block["n_pairs"] = n_pairs
    for name in REGION_NAMES:
        block[_PAPER_KEY[name]] = _ratio(matches[name], totals[name])
    fr_num = sum(matches[name] for name in FR_REGIONS)
    fr_den = sum(totals[name] for name in FR_REGIONS)
    cdr_num = sum(matches[name] for name in CDR_REGIONS)
    cdr_den = sum(totals[name] for name in CDR_REGIONS)
    block["aar_fr_all"] = _ratio(fr_num, fr_den)
    block["aar_cdr_all"] = _ratio(cdr_num, cdr_den)
    block["aar_all"] = _ratio(fr_num + cdr_num, fr_den + cdr_den)
    block["n_positions"] = {
        _PAPER_KEY[name]: int(totals[name]) for name in REGION_NAMES
    }
    block["n_positions"]["aar_fr_all"] = int(fr_den)
    block["n_positions"]["aar_cdr_all"] = int(cdr_den)
    block["n_positions"]["aar_all"] = int(fr_den + cdr_den)
    # Convenience delta vs. the paper for the buckets the paper quotes.
    deltas: dict[str, float] = {}
    for key, paper_value in PAPER_REFERENCE_AAR.items():
        measured = block.get(key)
        if isinstance(measured, float) and not math.isnan(measured):
            deltas[key] = float(measured) - float(paper_value)
    block["delta_vs_paper"] = deltas
    return block

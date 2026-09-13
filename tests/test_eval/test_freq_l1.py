"""Tests for ``adaptive_reflow.eval.freq_l1`` (Phase-C+ ProtBFN metric).

Pins the behaviour of the per-position amino-acid L1 distance
estimator introduced as a paper-metric-surface extension to the
ProtBFN / AbBFN SOTA harness. The metric is **pure Python + numpy**;
tests are pure-CPU and never load the trained encoder.

The bundled natural reference MSA is
``data/protbfn_abbfn/repo/example_inputs/sequences.fasta`` (12 VH
chains shipped with the upstream InstaDeep repo) so the empirical
reference path runs end-to-end without a network / weights download.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from adaptive_reflow.eval.freq_l1 import (
    BUNDLED_NATURAL_FASTA,
    DEFAULT_MAX_LENGTH,
    STANDARD_AA_ALPHABET,
    compute_freq_l1_block,
    per_position_freq_l1,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLED_FASTA = REPO_ROOT / BUNDLED_NATURAL_FASTA


# ---------------------------------------------------------------------------
# 1. Surface / constants
# ---------------------------------------------------------------------------


def test_alphabet_is_canonical_20() -> None:
    assert len(STANDARD_AA_ALPHABET) == 20
    assert STANDARD_AA_ALPHABET[0] == "A"
    assert STANDARD_AA_ALPHABET[-1] == "Y"
    # All unique.
    assert len(set(STANDARD_AA_ALPHABET)) == 20


def test_bundled_fasta_exists_on_disk() -> None:
    assert BUNDLED_FASTA.is_file(), (
        f"bundled reference MSA missing at {BUNDLED_FASTA}; the freq_l1 "
        "empirical-reference path will not work end-to-end."
    )


def test_default_max_length_matches_imgt_frame() -> None:
    # 128 is the IMGT VH frame length; the Phase-C+ metric truncates
    # long generated sequences here.
    assert DEFAULT_MAX_LENGTH == 128


# ---------------------------------------------------------------------------
# 2. per_position_freq_l1 — flat prior
# ---------------------------------------------------------------------------


def _uniform_generated(length: int, n_seqs: int) -> list[tuple[str, str]]:
    """Return ``n_seqs`` synthetic sequences such that the pooled
    per-position AA histogram collapses to the flat 1/20 prior.

    Each generated sequence is rotated by its index so that the 20 AAs
    are spread across positions uniformly across the pool. When
    ``n_seqs >= 20``, every position sees each AA at least once; for
    smaller pools the rotations still hit a balanced subset.
    """
    alphabet = STANDARD_AA_ALPHABET
    n_aa = len(alphabet)
    return [
        (
            f"gen{i}",
            "".join(alphabet[(j + i) % n_aa] for j in range(length)),
        )
        for i in range(n_seqs)
    ]


def test_per_position_freq_l1_flat_prior_self_distance_is_zero() -> None:
    """When generated == flat and reference == flat, mean_l1 == 0.

    Use ``n_seqs=20`` so the rotated pool places each AA exactly once
    at every position — i.e. the empirical histogram collapses to the
    flat 1/20 prior.
    """
    gen = _uniform_generated(length=16, n_seqs=20)
    result = per_position_freq_l1(gen, reference="flat", max_length=16)
    np.testing.assert_allclose(result["mean_l1"], 0.0, atol=1e-9)
    np.testing.assert_allclose(result["overall_l1"], 0.0, atol=1e-9)
    np.testing.assert_allclose(result["per_position_l1"], 0.0, atol=1e-9)
    assert result["reference_mode"] == "flat"
    assert result["reference_path"] is None
    assert result["n_generated"] == 20


def test_per_position_freq_l1_flat_prior_delta_score() -> None:
    """A generator that emits a constant AA should score ~1.9 against
    the flat 1/20 prior (L1 distance between delta and uniform = 2 *
    (1 - 1/20) = 1.9)."""
    gen = [(f"gen{i}", "A" * 16) for i in range(4)]
    result = per_position_freq_l1(gen, reference="flat", max_length=16)
    expected = 2.0 * (1.0 - 1.0 / 20.0)
    np.testing.assert_allclose(result["mean_l1"], expected, atol=1e-9)
    np.testing.assert_allclose(result["overall_l1"], expected, atol=1e-9)


def test_per_position_freq_l1_per_position_shape() -> None:
    gen = _uniform_generated(length=8, n_seqs=20)
    result = per_position_freq_l1(gen, reference="flat", max_length=8)
    assert result["per_position_l1"].shape == (8,)
    assert result["generated_distribution"].shape == (8, 20)


def test_per_position_freq_l1_l1_in_unit_interval() -> None:
    """The per-position L1 always lies in [0, 2] for proper
    distributions (zero mass everywhere except position a vs uniform
    1/20 scores ~1.9). Allow a tiny tolerance for floating-point."""
    gen = [(f"gen{i}", "ACDEFGHIKL") for i in range(5)]
    result = per_position_freq_l1(gen, reference="flat", max_length=10)
    p = result["per_position_l1"]
    assert np.all(p >= -1e-9)
    assert np.all(p <= 2.0 + 1e-9)


# ---------------------------------------------------------------------------
# 3. per_position_freq_l1 — empirical reference
# ---------------------------------------------------------------------------


def test_per_position_freq_l1_empirical_self_distance_is_zero() -> None:
    """Generated == reference should score 0 in the empirical mode."""
    if not BUNDLED_FASTA.is_file():
        pytest.skip(f"bundled reference MSA missing at {BUNDLED_FASTA}")
    ref_records = [
        (rid, seq) for rid, seq in _records(BUNDLED_FASTA)
    ]
    result = per_position_freq_l1(
        ref_records, reference=ref_records, max_length=64
    )
    np.testing.assert_allclose(result["mean_l1"], 0.0, atol=1e-9)
    np.testing.assert_allclose(result["overall_l1"], 0.0, atol=1e-9)
    assert result["reference_mode"] == "empirical"
    assert result["reference_counts"] is not None


def test_per_position_freq_l1_bundled_path_end_to_end() -> None:
    """End-to-end: point the empirical reference at the bundled FASTA
    and assert the call returns a finite, well-shaped block."""
    if not BUNDLED_FASTA.is_file():
        pytest.skip(f"bundled reference MSA missing at {BUNDLED_FASTA}")
    gen = [(f"gen{i}", "ACDEFGHIKLMNPQRSTVWY" * 4) for i in range(8)]
    result = per_position_freq_l1(
        gen, reference=BUNDLED_FASTA, max_length=64
    )
    assert result["reference_mode"] == "empirical"
    assert result["n_generated"] == 8
    assert result["per_position_l1"].shape == (64,)
    assert math.isfinite(result["mean_l1"])
    assert math.isfinite(result["overall_l1"])
    assert 0.0 <= result["mean_l1"] <= 2.0 + 1e-9
    assert 0.0 <= result["overall_l1"] <= 2.0 + 1e-9


def test_per_position_freq_l1_short_reference_does_not_crash() -> None:
    """A reference FASTA with sequences shorter than max_length must
    not crash — short positions are smoothed toward the length-pooled
    global distribution."""
    short_ref = [("r1", "AC"), ("r2", "DE")]
    gen = _uniform_generated(length=10, n_seqs=2)
    result = per_position_freq_l1(
        gen, reference=short_ref, max_length=10, smoothing=1.0
    )
    assert result["per_position_l1"].shape == (10,)
    # Positions 2+ had no natural residues; they should still score a
    # finite value thanks to smoothing.
    assert np.all(np.isfinite(result["per_position_l1"]))


def test_per_position_freq_l1_zero_smoothing_matches_raw_counts() -> None:
    """With smoothing=0 and min_count=0, the empirical distribution
    must collapse to the raw row-normalised histogram (or uniform when
    the row is empty)."""
    gen = _uniform_generated(length=2, n_seqs=20)
    result = per_position_freq_l1(
        gen, reference="flat", max_length=2, min_count=0, smoothing=0.0
    )
    # All 20 AAs hit each position exactly once.
    np.testing.assert_allclose(result["generated_distribution"][0], 1.0 / 20)
    np.testing.assert_allclose(result["generated_distribution"][1], 1.0 / 20)


# ---------------------------------------------------------------------------
# 4. compute_freq_l1_block — paper-format block
# ---------------------------------------------------------------------------


def test_compute_freq_l1_block_flat() -> None:
    """The block must serialise the per-position vector to a plain
    Python list and stamp status='computed' on success."""
    gen_records = _uniform_generated(length=8, n_seqs=20)
    # Use a temp path because the block API takes a file path.
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".fasta", delete=False
    ) as fh:
        for rid, seq in gen_records:
            fh.write(f">{rid}\n{seq}\n")
        gen_path = fh.name
    try:
        block = compute_freq_l1_block(
            gen_path, reference_fasta_path=None, max_length=8
        )
        assert block["status"] == "computed"
        assert block["reference_mode"] == "flat"
        assert block["reference_fasta"] is None
        assert block["n_generated"] == 20
        assert len(block["per_position_l1"]) == 8
        assert isinstance(block["per_position_l1"][0], float)
        assert block["alphabet"] == list(STANDARD_AA_ALPHABET)
        assert block["mean_l1"] == pytest.approx(0.0, abs=1e-9)
        # The histogram is JSON-serialisable.
        assert isinstance(block["generated_aa_histogram"][0], list)
    finally:
        Path(gen_path).unlink(missing_ok=True)


def test_compute_freq_l1_block_missing_generated_file() -> None:
    block = compute_freq_l1_block("/no/such/file.fasta", reference_fasta_path=None)
    assert block["status"].startswith("not_computed:file_not_found")


def test_compute_freq_l1_block_missing_reference_file() -> None:
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".fasta", delete=False
    ) as fh:
        fh.write(">g1\nACDE\n")
        gen_path = fh.name
    try:
        block = compute_freq_l1_block(
            gen_path, reference_fasta_path="/no/such/ref.fasta"
        )
        assert block["status"].startswith("not_computed:file_not_found")
    finally:
        Path(gen_path).unlink(missing_ok=True)


def test_compute_freq_l1_block_bundled_empirical_end_to_end() -> None:
    if not BUNDLED_FASTA.is_file():
        pytest.skip(f"bundled reference MSA missing at {BUNDLED_FASTA}")
    import tempfile

    gen_records = [(f"g{i}", "ACDEFGHIKL") for i in range(4)]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".fasta", delete=False
    ) as fh:
        for rid, seq in gen_records:
            fh.write(f">{rid}\n{seq}\n")
        gen_path = fh.name
    try:
        block = compute_freq_l1_block(
            gen_path, reference_fasta_path=BUNDLED_FASTA, max_length=10
        )
        assert block["status"] == "computed"
        assert block["reference_mode"] == "empirical"
        assert block["reference_fasta"] == str(BUNDLED_FASTA)
        assert block["n_generated"] == 4
        assert len(block["per_position_l1"]) == 10
        assert block["reference_aa_histogram"] is not None
    finally:
        Path(gen_path).unlink(missing_ok=True)


def test_compute_freq_l1_block_empty_generated_fasta() -> None:
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".fasta", delete=False
    ) as fh:
        # Empty file (zero records).
        gen_path = fh.name
    try:
        block = compute_freq_l1_block(gen_path, reference_fasta_path=None)
        assert block["status"] == "not_computed:empty_generated_fasta"
    finally:
        Path(gen_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 5. Helpers
# ---------------------------------------------------------------------------


def _records(path: Path) -> list[tuple[str, str]]:
    """Tiny FASTA reader so this test file stays self-contained even
    when Biopython is missing from the test venv."""
    out: list[tuple[str, str]] = []
    header: str | None = None
    chunks: list[str] = []
    with path.open("r") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    out.append((header, "".join(chunks)))
                header = line[1:].strip()
                chunks = []
            else:
                chunks.append(line)
    if header is not None:
        out.append((header, "".join(chunks)))
    return out

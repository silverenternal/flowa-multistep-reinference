"""Tests for ``tools.paper_metrics_kanzi`` (Wave 83 Agent B).

The :mod:`tools.paper_metrics_kanzi` module wraps the Kanzi upstream
``DAE.encode`` / ``DAE.decode`` to expose the 5 missing Kanzi paper
metrics:

  1. ``compute_codebook_entropy`` (Shannon entropy bits)
  2. ``compute_codebook_perplexity`` (= ``2 ** entropy``)
  3. ``compute_codebook_js_distance`` (JS distance, bits^0.5)
  4. ``compute_codebook_utilization`` (fraction of codebook used)
  5. ``compute_codebook_hamming_rotation_invariance`` (mean per-position
     Hamming equality under uniform-rotation pairs)

Plus a 6th metric re-export (Wave 79 driver):
``compute_reconstruction_kabsch_rmsd_A`` (delegates to
``tools.upstream_eval.run_kanzi_upstream_eval``).

The Kanzi ckpt is NOT vendored in the framework's pytest env (no
``kanzi`` import by design), so the metric helpers are exercised on
synthetic FSQ outputs (deterministic numpy fixtures). The integration
test exercises the 5 codebook metrics on real demo PDBs without
requiring the upstream ckpt — the encoder is a deterministic mock
that hashes per-position.

Test surface (6 unit tests + 1 integration test; matches the Wave 75
Wave 82 pattern):

* ``test_entropy_uniform_distribution`` — uniform idx → ``log2(V)``.
* ``test_entropy_collapsed_distribution`` — all-zero idx → ``0.0``.
* ``test_perplexity_uniform_and_collapsed`` — ``2 ** entropy`` parity.
* ``test_js_distance_deterministic_pair_byte_stable`` — fixed (0, 1) pair.
* ``test_utilization_full_and_partial`` — unique(idx) / V.
* ``test_hamming_rotation_invariance_identity_encoder`` — mock encoder
  that always returns the same indices → Hamming = 1.0.
* ``test_paper_metrics_kanzi_end_to_end_on_4_demo_pdbs`` —
  end-to-end smoke on the 4 demo PDBs.

All tests pass without the real upstream Kanzi ckpt — they use a
deterministic mock encoder (a hash of the coords) so the smoke
exercises the real Wave 80 PDB extraction + the 5 codebook metrics.
"""
from __future__ import annotations

import hashlib
import sys
import types
from pathlib import Path
from typing import Any

import numpy as np
import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
WAVE80_PDBS_DIR: Path = REPO_ROOT / "data" / "kanzi_upstream" / "pdbs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_encoder(coords: np.ndarray, vocab_size: int = 4096) -> np.ndarray:
    """Deterministic mock encoder for tests (NO upstream ckpt required).

    Hashes each row of ``coords`` (shape ``(L, 3)``) to an integer in
    ``[0, vocab_size)``. Two rotations of the same backbone yield
    DIFFERENT hashes (so hamming is not trivially 1.0 — the test
    ``test_hamming_rotation_invariance_identity_encoder`` adds the
    identity-encoder stub explicitly to exercise the 1.0 case).

    Parameters
    ----------
    coords
        Shape ``(L, 3)`` float32 array.
    vocab_size
        Codebook vocab size (default 4096).

    Returns
    -------
    np.ndarray
        Shape ``(L,)`` int64 array of indices in ``[0, vocab_size)``.
    """
    flat = np.ascontiguousarray(coords.astype(np.float32).reshape(-1))
    blob = flat.tobytes()
    digest = hashlib.sha256(blob).digest()
    # Use the first 8 bytes as a uint64 then mod vocab_size.
    seed = int.from_bytes(digest[:8], "little", signed=False)
    rng = np.random.default_rng(seed)
    return rng.integers(0, int(vocab_size), size=coords.shape[0], dtype=np.int64)


def _identity_encoder(_coords: np.ndarray) -> np.ndarray:
    """Identity encoder stub: always returns ``[0, 0, ..., 0]``.

    Used by the Hamming identity test — the same indices come back for
    any rotation so the Hamming number is trivially 1.0.
    """
    return np.zeros(_coords.shape[0], dtype=np.int64)


# ---------------------------------------------------------------------------
# Unit tests — per-metric smoke
# ---------------------------------------------------------------------------


def test_entropy_uniform_distribution() -> None:
    """A perfectly uniform idx distribution yields ``entropy == log2(V)``.

    For ``V = 16`` (FSQ ``levels = (2, 2, 2, 2)``), ``log2(16) == 4.0``.
    We construct 16 distinct indices in a single row and verify the
    formula matches the analytic upper bound.
    """
    from tools import paper_metrics_kanzi  # noqa: PLC0415

    idx = np.arange(16, dtype=np.int64).reshape(1, 16)  # B=1, L=16
    h = paper_metrics_kanzi.compute_codebook_entropy(idx, vocab_size=16)
    assert h == pytest.approx(4.0, abs=1e-9)
    assert 0.0 <= h <= 4.0


def test_entropy_collapsed_distribution() -> None:
    """All-zero idx → ``entropy == 0.0`` (single-cell mass).

    The Shannon entropy of a Dirac-delta distribution is identically 0.
    The implementation collapses the ``-0.0`` floating-point artifact to
    ``0.0`` for caller convenience (still byte-equivalent to upstream
    ``(probs * log2(probs)).sum() == 0``).
    """
    from tools import paper_metrics_kanzi  # noqa: PLC0415

    idx = np.zeros((4, 8), dtype=np.int64)
    h = paper_metrics_kanzi.compute_codebook_entropy(idx, vocab_size=16)
    assert h == pytest.approx(0.0, abs=1e-9)
    assert 0.0 <= h <= 4.0


def test_perplexity_uniform_and_collapsed() -> None:
    """Perplexity = ``2 ** entropy``; monotonic in entropy.

    For uniform ``V=16`` distribution: perplexity == 16 (the effective
    vocab size). For collapsed: perplexity == 1 (single code used).
    For a partial distribution: perplexity lies in (1, V).
    """
    from tools import paper_metrics_kanzi  # noqa: PLC0415

    # Uniform
    idx_uniform = np.arange(16, dtype=np.int64).reshape(1, 16)
    ppl_uniform = paper_metrics_kanzi.compute_codebook_perplexity(idx_uniform, vocab_size=16)
    assert ppl_uniform == pytest.approx(16.0, abs=1e-9)
    # Collapsed
    idx_collapsed = np.zeros((4, 8), dtype=np.int64)
    ppl_collapsed = paper_metrics_kanzi.compute_codebook_perplexity(idx_collapsed, vocab_size=16)
    assert ppl_collapsed == pytest.approx(1.0, abs=1e-9)
    # Partial — 8 distinct codes → perplexity == 8.
    idx_partial = np.tile(np.arange(8, dtype=np.int64), (2, 1))
    ppl_partial = paper_metrics_kanzi.compute_codebook_perplexity(idx_partial, vocab_size=16)
    assert ppl_partial == pytest.approx(8.0, abs=1e-9)


def test_js_distance_deterministic_pair_byte_stable() -> None:
    """JS distance is byte-stable: same input → same output across re-runs.

    The upstream ``codebook_metrics`` uses ``random.uniform`` to pick
    the JS-distance pair, which is non-deterministic for tests. Our
    implementation fixes the pair to ``(0, 1)``, so two calls with the
    same input must return identical floats (proves the determinism
    fix works).

    Also exercises the disjoint-support case: two rows with disjoint
    index sets yield ``js_distance == 1.0`` (the JS upper bound for two
    uniform distributions over disjoint supports = ``log2(2) == 1``).
    """
    from tools import paper_metrics_kanzi  # noqa: PLC0415

    # Disjoint support: row 0 has [0..7], row 1 has [8..15] in V=16.
    idx = np.concatenate(
        [np.arange(8, dtype=np.int64).reshape(1, -1), (np.arange(8, 16, dtype=np.int64).reshape(1, -1))],
        axis=0,
    )
    j1 = paper_metrics_kanzi.compute_codebook_js_distance(idx, vocab_size=16)
    j2 = paper_metrics_kanzi.compute_codebook_js_distance(idx, vocab_size=16)
    assert j1 == j2  # byte-stable (no RNG)
    assert j1 == pytest.approx(1.0, abs=1e-9)
    # Identical support: row 0 == row 1 → js == 0.0 (deterministic pair (0,1)).
    idx_same = np.tile(np.arange(8, dtype=np.int64), (2, 1))
    js_same = paper_metrics_kanzi.compute_codebook_js_distance(idx_same, vocab_size=16)
    assert js_same == pytest.approx(0.0, abs=1e-9)
    # Single row → 0.0 (defensive, matches the docstring).
    idx_single = np.arange(8, dtype=np.int64).reshape(1, -1)
    js_single = paper_metrics_kanzi.compute_codebook_js_distance(idx_single, vocab_size=16)
    assert js_single == 0.0


def test_utilization_full_and_partial() -> None:
    """Utilization = ``|unique(idx)| / V`` ∈ [0, 1].

    Full: all V codes used → 1.0. Partial: V/2 codes used → 0.5. Empty:
    0.0 (defensive). Out-of-range index raises ``ValueError`` so a
    misconfigured encoder fails loudly.
    """
    from tools import paper_metrics_kanzi  # noqa: PLC0415

    # Full
    idx_full = np.arange(16, dtype=np.int64)
    u_full = paper_metrics_kanzi.compute_codebook_utilization(idx_full, vocab_size=16)
    assert u_full == pytest.approx(1.0, abs=1e-9)
    # Partial: 8 distinct codes out of 16 → 0.5
    idx_partial = np.concatenate(
        [np.arange(8, dtype=np.int64), np.arange(8, dtype=np.int64)], axis=0
    )
    u_partial = paper_metrics_kanzi.compute_codebook_utilization(idx_partial, vocab_size=16)
    assert u_partial == pytest.approx(0.5, abs=1e-9)
    # Empty
    u_empty = paper_metrics_kanzi.compute_codebook_utilization(np.array([], dtype=np.int64), vocab_size=16)
    assert u_empty == 0.0
    # Out-of-range guard
    idx_bad = np.array([0, 16], dtype=np.int64)  # 16 is OOR for V=16
    with pytest.raises(ValueError, match="index out of range"):
        paper_metrics_kanzi.compute_codebook_utilization(idx_bad, vocab_size=16)


def test_hamming_rotation_invariance_identity_encoder() -> None:
    """Identity encoder (always returns ``[0, ..., 0]``) → Hamming == 1.0.

    An encoder that ignores its input trivially satisfies rotation
    invariance (the Hamming number is the per-position equality, which
    is 1.0 when both rows are the same constant index).

    Also exercises the encoder-shape contract: the encoder must return
    a 1-D ``(L,)`` array; mismatched shapes raise ``ValueError``.
    """
    from tools import paper_metrics_kanzi  # noqa: PLC0415

    # One backbone, 5 residues → 1 (R0, R1) pair (n_rot=2).
    coords = np.zeros((1, 5, 3), dtype=np.float64)
    h = paper_metrics_kanzi.compute_codebook_hamming_rotation_invariance(
        coords,
        encoder=_identity_encoder,
        n_rot=2,
        seed=0,
        vocab_size=16,
    )
    assert h == pytest.approx(1.0, abs=1e-9)

    # Empty coords → 0.0
    coords_empty = np.zeros((0, 5, 3), dtype=np.float64)
    h_empty = paper_metrics_kanzi.compute_codebook_hamming_rotation_invariance(
        coords_empty,
        encoder=_identity_encoder,
        n_rot=2,
        seed=0,
        vocab_size=16,
    )
    assert h_empty == 0.0

    # Mismatched shape → ValueError (R0 returns L=3, R1 returns L=5).
    def _bad_encoder_r0(_x: np.ndarray) -> np.ndarray:
        return np.zeros(3, dtype=np.int64)

    def _bad_encoder_r1(_x: np.ndarray) -> np.ndarray:
        return np.zeros(5, dtype=np.int64)

    # Use a wrapper that alternates the two shapes so R0 vs R1 differ.
    call_count = {"n": 0}

    def _alternating_encoder(x: np.ndarray) -> np.ndarray:
        call_count["n"] += 1
        return _bad_encoder_r0(x) if call_count["n"] % 2 == 1 else _bad_encoder_r1(x)

    with pytest.raises(ValueError, match="inconsistent shapes"):
        paper_metrics_kanzi.compute_codebook_hamming_rotation_invariance(
            coords,
            encoder=_alternating_encoder,
            n_rot=2,
            seed=0,
            vocab_size=16,
        )

    # n_rot < 2 → ValueError
    with pytest.raises(ValueError, match="n_rot must be >= 2"):
        paper_metrics_kanzi.compute_codebook_hamming_rotation_invariance(
            coords,
            encoder=_identity_encoder,
            n_rot=1,
            seed=0,
            vocab_size=16,
        )


# ---------------------------------------------------------------------------
# Aggregator tests
# ---------------------------------------------------------------------------


def test_aggregator_returns_all_5_keys() -> None:
    """``compute_all_codebook_metrics`` returns a 5-field frozen dataclass.

    The aggregator returns a :class:`CodebookMetricsResult` with the
    5 paper metrics (entropy + perplexity + JS + utilization + hamming).
    The dataclass is frozen so callers cannot accidentally mutate the
    result after the fact.
    """
    from tools import paper_metrics_kanzi  # noqa: PLC0415

    idx = np.arange(16, dtype=np.int64).reshape(2, 8)
    out = paper_metrics_kanzi.compute_all_codebook_metrics(idx, vocab_size=16)
    assert isinstance(out, paper_metrics_kanzi.CodebookMetricsResult)
    # All 5 fields are floats in their canonical ranges.
    assert isinstance(out.codebook_entropy_bits, float)
    assert isinstance(out.codebook_perplexity, float)
    assert isinstance(out.codebook_js_distance, float)
    assert isinstance(out.codebook_utilization, float)
    assert isinstance(out.codebook_hamming_rotation_invariance, float)
    # Ranges
    assert 0.0 <= out.codebook_entropy_bits <= 4.0
    assert 1.0 <= out.codebook_perplexity <= 16.0
    assert 0.0 <= out.codebook_js_distance <= 1.0
    assert 0.0 <= out.codebook_utilization <= 1.0
    assert 0.0 <= out.codebook_hamming_rotation_invariance <= 1.0
    # to_dict is JSON-serializable.
    d = out.to_dict()
    assert set(d) == {
        "codebook_entropy_bits",
        "codebook_perplexity",
        "codebook_js_distance",
        "codebook_utilization",
        "codebook_hamming_rotation_invariance",
    }


def test_aggregator_byte_stable() -> None:
    """Two calls with same input → identical output dict (regression for (0, 1) JS pair).

    The aggregator's output must be byte-stable across re-runs (no
    RNG anywhere in the first 4 metrics; the 5th is seeded). This is
    the regression that closes the upstream ``random.uniform``
    non-determinism for the JS pair.
    """
    from tools import paper_metrics_kanzi  # noqa: PLC0415

    idx = np.concatenate(
        [np.arange(8, dtype=np.int64).reshape(1, -1), (np.arange(8, 16, dtype=np.int64).reshape(1, -1))],
        axis=0,
    )
    out1 = paper_metrics_kanzi.compute_all_codebook_metrics(idx, vocab_size=16)
    out2 = paper_metrics_kanzi.compute_all_codebook_metrics(idx, vocab_size=16)
    assert out1.to_dict() == out2.to_dict()


# ---------------------------------------------------------------------------
# kanzi_available() — import surface check
# ---------------------------------------------------------------------------


def test_kanzi_available_returns_bool() -> None:
    """``kanzi_available()`` returns a bool and never raises.

    On the framework pytest env (no Kanzi import), it returns
    ``False``. On a host with the sidecar venv + ckpt, it returns
    ``True``. The function is the gate used by the
    ``test_paper_metrics_kanzi_end_to_end_on_4_demo_pdbs`` integration
    test below to skip the Hamming metric (which needs the real DAE
    encoder) when kanzi is unavailable.
    """
    from tools import paper_metrics_kanzi  # noqa: PLC0415

    result = paper_metrics_kanzi.kanzi_available()
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Wave 79 driver delegation — reconstruction_kabsch_rmsd_A wrapper
# ---------------------------------------------------------------------------


def test_compute_reconstruction_kabsch_rmsd_A_handles_missing_kanzi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When kanzi is unavailable, the wrapper returns a sentinel dict.

    Mirrors the Wave 75 ``test_pb_validity_pct_*`` pattern: mock
    ``tools.upstream_eval.run_kanzi_upstream_eval`` to return a known
    canned dict, and verify the wrapper passes through unchanged.
    """
    import sys as _sys

    # Build a fake upstream_eval module.
    fake_ue = _sys.modules.get("tools.upstream_eval")
    if fake_ue is None:
        fake_ue = types.ModuleType("tools.upstream_eval")
        _sys.modules["tools.upstream_eval"] = fake_ue

    sentinel = {
        "status": 0.0,
        "reason": "mocked_kanzi_unavailable",
        "metric_kind": "reconstruction_kabsch_rmsd_A",
    }

    def _fake_run_kanzi_upstream_eval(*args: Any, **kwargs: Any) -> dict[str, float]:
        return sentinel

    fake_ue.run_kanzi_upstream_eval = _fake_run_kanzi_upstream_eval  # type: ignore[attr-defined]

    from tools import paper_metrics_kanzi  # noqa: PLC0415

    out = paper_metrics_kanzi.compute_reconstruction_kabsch_rmsd_A(
        sequences_path="/tmp/nonexistent.fasta",
        output_dir="/tmp/nonexistent_out",
    )
    assert out == sentinel


# ---------------------------------------------------------------------------
# Integration test — end-to-end on the 4 Wave 80 demo PDBs
# ---------------------------------------------------------------------------


def test_paper_metrics_kanzi_end_to_end_on_4_demo_pdbs(
    tmp_path: Path,
) -> None:
    """End-to-end: Wave 80 PDB extraction → 5 codebook metrics on 4 demo PDBs.

    Walks through the same surface as the Wave 83 smoke CLI but
    in-process:

    1. Extract per-cell Cα coords from the 4 Wave 80 demo PDBs
       (1s7mB01 / 2hoxA01 / 3bg1B01 / 6nrzA01).
    2. Generate a deterministic FSQ index per backbone using
       ``_hash_encoder`` (no upstream ckpt required).
    3. Call ``compute_all_codebook_metrics`` on the aggregated indices.
    4. Assert the 5 metrics are in their canonical ranges + the
       aggregator returns the expected dataclass.

    Skips gracefully when the 4 demo PDBs are not present on disk
    (e.g. on a fresh clone without the vendored upstream repo).
    """
    if not WAVE80_PDBS_DIR.is_dir():
        pytest.skip(
            f"Kanzi demo PDBs missing at {WAVE80_PDBS_DIR} "
            "(vendor data/kanzi_upstream/pdbs/ to run this test)"
        )
    pdbs = sorted(WAVE80_PDBS_DIR.glob("*.pdb"))
    if len(pdbs) < 4:
        pytest.skip(
            f"expected >=4 demo PDBs under {WAVE80_PDBS_DIR}, found {len(pdbs)}"
        )

    # Step 1: extract Cα coords (Wave 80 Agent B pattern).
    # Each PDB has a different residue count (39 / 100 / 49 / 155), so
    # we truncate all backbones to the SHORTEST one (39 residues for
    # 1s7mB01) before stacking. This is a faithful smoke of the
    # end-to-end metric flow at equal-length inputs — the per-PDB
    # residue counts are an artifact of which reference PDBs are
    # vendored, not a property of the metric surface.
    sys.path.insert(0, str(REPO_ROOT))
    from tools.extract_ca_coords_for_kanzi import extract_ca_coords_from_pdb  # noqa: PLC0415

    coords_list: list[np.ndarray] = []
    idx_list: list[np.ndarray] = []
    min_L: int | None = None
    raw_coords: list[np.ndarray] = []
    for pdb in pdbs[:4]:
        c = extract_ca_coords_from_pdb(pdb)
        raw_coords.append(c)
        if min_L is None or c.shape[0] < min_L:
            min_L = int(c.shape[0])
    assert min_L is not None and min_L > 0
    for c in raw_coords:
        c_trunc = c[:min_L]
        coords_list.append(c_trunc)
        idx_list.append(_hash_encoder(c_trunc, vocab_size=4096))
    coords = np.stack(coords_list, axis=0).astype(np.float64)
    idx = np.concatenate(idx_list, axis=0).astype(np.int64)

    # Step 2: compute all 5 codebook metrics (entropy + perplexity + JS +
    # utilization are pure-numpy; hamming needs an encoder so we
    # pass ``_hash_encoder``).
    from tools import paper_metrics_kanzi  # noqa: PLC0415

    out = paper_metrics_kanzi.compute_all_codebook_metrics(
        idx,
        vocab_size=4096,
        coords=coords,
        encoder=_hash_encoder,
        hamming_seed=0,
        n_rot=2,
    )

    # Step 3: assert ranges + dataclass shape.
    assert isinstance(out, paper_metrics_kanzi.CodebookMetricsResult)
    # Entropy in [0, log2(4096)] = [0, 12]
    assert 0.0 <= out.codebook_entropy_bits <= 12.0
    # Perplexity in [1, 4096]
    assert 1.0 <= out.codebook_perplexity <= 4096.0
    # JS in [0, 1] (bits^0.5; upper bound for two disjoint uniforms)
    assert 0.0 <= out.codebook_js_distance <= 1.0
    # Utilization in [0, 1]
    assert 0.0 <= out.codebook_utilization <= 1.0
    # Hamming in [0, 1] (real-encoder hamming for FSQ paper-aligned runs is >0.9)
    assert 0.0 <= out.codebook_hamming_rotation_invariance <= 1.0
    # For 4 demo PDBs with ~4 codes per backbone via hash encoder,
    # utilization should be > 0 (non-degenerate).
    assert out.codebook_utilization > 0.0

    # Step 4: write the result to a temp JSON file (smoke surface mirror).
    import json

    out_json = tmp_path / "kanzi_codebook_end_to_end.json"
    payload = {
        "tool": "tools.paper_metrics_kanzi",
        "test": "test_paper_metrics_kanzi_end_to_end_on_4_demo_pdbs",
        "n_pdbs": len(coords_list),
        "total_indices": int(idx.size),
        "vocab_size": 4096,
        "metrics": out.to_dict(),
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    assert out_json.is_file()
    # Round-trip the JSON to confirm serializability.
    reloaded = json.loads(out_json.read_text(encoding="utf-8"))
    assert reloaded["metrics"]["codebook_entropy_bits"] == out.codebook_entropy_bits

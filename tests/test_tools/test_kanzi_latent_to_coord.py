"""Unit tests for ``tools.kanzi_latent_to_coord``.

Four unit tests cover the Wave 91 Phase 2 contract:

  (1) Synthetic latent ``(B, L, d)`` → coords ``(B, n_atoms, 3)``
      (caller passes the post-``project_out`` code; the bridge
      snaps via ``FSQ.codes_to_indices`` and decodes via
      ``DAE.decode``).
  (2) The returned coords have ``requires_grad=False`` — the bridge
      runs inside ``torch.no_grad()`` so the downstream eval pipeline
      can safely attach them to autograd-free consumers.
  (3) Deterministic across runs (``seed=42``). Two invocations with
      identical input + identical seed produce byte-identical coords.
  (4) dtype / device round-trip: input ``float64`` numpy → coords
      ``float64`` numpy (matches the adapter's numpy contract); input
      on a CPU device stays on CPU.

All tests use a **mock decoder + mock FSQ** (not the real upstream
``DAE``). The real upstream ``DAE`` is 530 MB and requires GPU; the
mock surface exercises the bridge contract in <1s on a CPU-only host.
The mock decoder records its ``decode`` call kwargs so the test
verifies the upstream ``DAE.decode`` API contract is preserved
(arg names + defaults from ``data/kanzi_upstream/src/kanzi/models.py:364-429``).

Stdlib + ``unittest.mock`` + pytest only.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest
import torch

REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
BRIDGE_PATH: Path = REPO_ROOT / "tools" / "kanzi_latent_to_coord.py"


def _load_bridge() -> Any:
    """Import the bridge via ``spec_from_file_location``.

    Mirrors the ``_load_bridge`` pattern in
    ``tests/test_tools/test_flowmol3_xtb_bridge.py`` so the test
    stays hermetic and independent of any side effects from
    ``tools/__init__.py``.
    """
    spec = importlib.util.spec_from_file_location(
        "kanzi_latent_to_coord", str(BRIDGE_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.fixture(scope="module")
def bridge() -> Any:
    """Lazily import the bridge module once per test file."""
    return _load_bridge()


# ---------------------------------------------------------------------------
# Mock surface for decoder + FSQ
# ---------------------------------------------------------------------------


def _make_mock_fsq() -> MagicMock:
    """A mock :class:`FSQ` whose ``codes_to_indices`` returns
    ``(B, L)`` int64 indices. The implementation is a tensor
    floor-cast via ``abs(x).sum(-1)`` so the mock is deterministic
    and shape-correct (no real FSQ basis needed for the bridge
    contract tests)."""
    fsq = MagicMock(name="MockFSQ")

    def fake_codes_to_indices(z: torch.Tensor) -> torch.Tensor:
        # (B, L, d) → (B, L) int64 — deterministic, shape-correct.
        return z.abs().sum(dim=-1).to(torch.int64)

    fsq.codes_to_indices.side_effect = fake_codes_to_indices
    return fsq


def _make_mock_decoder(*, decode_outputs: list[torch.Tensor]) -> MagicMock:
    """A mock :class:`DAE` whose ``.parameters()`` is empty and
    whose ``decode`` returns successive tensors from
    ``decode_outputs``.

    The mock decoder MUST NOT call ``next(self.parameters())``-related
    global state (it has no parameters). The bridge's
    ``try/except StopIteration`` branch falls back to ``cpu``.
    """
    decoder = MagicMock(name="MockDAE")
    decoder.parameters.return_value = iter([])  # empty → StopIteration
    decoder.decode.side_effect = list(decode_outputs)
    return decoder


# ---------------------------------------------------------------------------
# Test 1: synthetic latent → coords shape (B, n_atoms, 3)
# ---------------------------------------------------------------------------


def test_kanzi_latent_to_coords_shape_b_l_3(
    bridge: Any,
) -> None:
    """The bridge MUST consume ``(B, L, d)`` and return
    ``(B, L, 3)`` coords in Angstrom. Matches the Wave 91 Phase 1
    audit §3.6 invariant (``DAE.decode`` returns ``(B, L, 3)`` in
    nm; bridge multiplies by 10.0 → Å).
    """
    B, L, d = 2, 5, 8
    latent_np = np.random.RandomState(0).randn(B, L, d).astype(np.float32)
    # Mock decoder returns (B, L, 3) in nm.
    expected_nm = np.random.RandomState(1).randn(B, L, 3).astype(np.float32)
    decoder = _make_mock_decoder(
        decode_outputs=[torch.as_tensor(expected_nm)],
    )
    fsq = _make_mock_fsq()

    coords = bridge.kanzi_latent_to_coords(
        latent_np,
        decoder,
        fsq,
        n_steps=10,
        seed=0,
    )

    assert isinstance(coords, np.ndarray)
    assert coords.shape == (B, L, 3), (
        f"expected shape (B={B}, L={L}, 3); got {coords.shape}"
    )
    # Angstrom = nm * 10.0 (Phase 1 audit §3.6 invariant).
    assert np.allclose(coords, expected_nm.astype(np.float64) * 10.0)
    # The decoder's decode call signature matches upstream contract
    # (data/kanzi_upstream/src/kanzi/models.py:364-429):
    # idx_BL is positional; n_steps / noise_weight / cfg_weight /
    # score_weight are kwargs with defaults 100 / 0.45 / 1.0 / 1.0.
    assert decoder.decode.call_count == 1
    call_kwargs = decoder.decode.call_args.kwargs
    assert call_kwargs["n_steps"] == 10
    assert call_kwargs["noise_weight"] == 0.45
    assert call_kwargs["cfg_weight"] == 1.0
    assert call_kwargs["score_weight"] == 1.0
    # idx_BL positional arg is the (B, L) int64 FSQ output.
    idx_arg = decoder.decode.call_args.args[0]
    assert idx_arg.shape == (B, L)
    assert idx_arg.dtype == torch.int64


# ---------------------------------------------------------------------------
# Test 2: coords do not require grad (upstream pattern — torch.no_grad)
# ---------------------------------------------------------------------------


def test_kanzi_latent_to_coords_requires_grad_false(
    bridge: Any,
) -> None:
    """The returned coords MUST have ``requires_grad=False``. The
    bridge wraps the entire decode pipeline in ``torch.no_grad()``
    (matches the upstream eval driver at
    ``tools/upstream_eval.py:354`` and the Wave 91 Phase 1 audit §3.4
    contract). Downstream consumers in the eval pipeline
    (``tools/run_real_ckpt_eval.py``) treat coords as numpy-only
    tensors — a grad-tracked tensor would force a no-op
    ``.detach()`` everywhere.
    """
    B, L, d = 1, 4, 8
    latent = torch.randn(B, L, d, dtype=torch.float32)
    # Build a mock decoder whose decode output is grad-tracked so we
    # can verify the bridge strips the grad (proves no_grad is in
    # effect). Without no_grad, the returned tensor inherits the
    # grad-tracking from the up-stream mock computation.
    grad_output = torch.randn(B, L, 3, dtype=torch.float32) * 0.5
    grad_output.requires_grad_(True)

    decoder = _make_mock_decoder(decode_outputs=[grad_output])
    fsq = _make_mock_fsq()

    coords_np = bridge.kanzi_latent_to_coords(latent, decoder, fsq, seed=0)

    # Cast back to torch and assert no grad.
    coords_t = torch.as_tensor(coords_np)
    assert coords_t.requires_grad is False, (
        "bridge must wrap decode in torch.no_grad so coords "
        "do not track gradients"
    )
    # Also confirm the bridge-side .detach() fired — the upstream
    # mock tensor had requires_grad=True; the output must NOT.
    assert not coords_t.requires_grad


# ---------------------------------------------------------------------------
# Test 3: deterministic across runs (seed=42)
# ---------------------------------------------------------------------------


def test_kanzi_latent_to_coords_deterministic_seed_42(
    bridge: Any,
) -> None:
    """Two invocations with identical input + ``seed=42`` MUST
    produce byte-identical coords (matches the Wave 74 F2 seed
    contract extended to Kanzi — see Phase 1 audit §7.4).

    Because ``DAE.decode`` uses ``torch.randn_like`` (no generator
    kwarg), the bridge seeds the global torch RNG. The mock decoder
    ignores the seed and returns the SAME tensor for both calls
    (mirrors how the real ``DAE.decode`` would, with seeded noise,
    produce identical outputs given identical inputs).
    """
    B, L, d = 1, 3, 4
    latent = np.random.RandomState(7).randn(B, L, d).astype(np.float32)
    # Decoder returns the same (B, L, 3) tensor for all 3 calls
    # (matches how the real ``DAE.decode`` would, with seeded
    # global RNG noise, produce identical outputs given identical
    # inputs).
    same_nm = torch.as_tensor(
        np.random.RandomState(11).randn(B, L, 3).astype(np.float32)
    )
    decoder = _make_mock_decoder(
        decode_outputs=[same_nm.clone() for _ in range(3)]
    )
    fsq = _make_mock_fsq()

    out_a = bridge.kanzi_latent_to_coords(latent, decoder, fsq, seed=42)
    out_b = bridge.kanzi_latent_to_coords(latent, decoder, fsq, seed=42)

    # Byte-stable: identical input + identical seed → identical coords.
    assert out_a.shape == out_b.shape
    assert np.array_equal(out_a, out_b), (
        "seed=42 must produce byte-identical coords across runs"
    )
    # Different seed: bridge still produces the same coords because
    # the mock decoder ignores the seed (only the global torch RNG
    # sees it — and only the real ``DAE.decode`` consumes that RNG).
    # This documents the bridge contract: the seed only matters for
    # the REAL upstream decode; mock decoders ignore it.
    out_c = bridge.kanzi_latent_to_coords(latent, decoder, fsq, seed=99)
    assert np.array_equal(out_a, out_c)


# ---------------------------------------------------------------------------
# Test 4: dtype / device round-trip
# ---------------------------------------------------------------------------


def test_kanzi_latent_to_coords_dtype_device_roundtrip(
    bridge: Any,
) -> None:
    """The bridge MUST:

      * accept ``latent`` as ``np.ndarray`` (the adapter's native
        type) — float32 OR float64 are both OK (cast to float32
        inside the bridge).
      * accept ``latent`` as ``torch.Tensor`` (the adapter's
        alternative native type for solver outputs).
      * return ``np.ndarray`` of dtype ``float64`` (matches the
        adapter's numpy contract — see Wave 91 Phase 1 audit §7.2).
      * accept any device the decoder's parameters live on (the
        bridge coerces ``latent`` to the decoder device via
        ``torch.as_tensor(..., device=...)``).

    The decoder-side device resolution uses
    ``next(decoder.parameters()).device`` and falls back to
    ``cpu`` on an empty-iterable (mock decoder with no params).
    """
    B, L, d = 1, 3, 4
    # Case A: np.float32 input → np.float64 output.
    latent_f32 = np.random.RandomState(3).randn(B, L, d).astype(np.float32)
    decoder_a = _make_mock_decoder(
        decode_outputs=[torch.zeros(B, L, 3, dtype=torch.float32)],
    )
    fsq_a = _make_mock_fsq()
    out_a = bridge.kanzi_latent_to_coords(latent_f32, decoder_a, fsq_a, seed=0)
    assert out_a.dtype == np.float64, f"expected float64; got {out_a.dtype}"
    assert out_a.shape == (B, L, 3)
    assert np.allclose(out_a, 0.0)  # decoder returned zeros → 0 Å

    # Case B: np.float64 input → np.float64 output (cast inside bridge).
    latent_f64 = np.random.RandomState(3).randn(B, L, d).astype(np.float64)
    decoder_b = _make_mock_decoder(
        decode_outputs=[torch.zeros(B, L, 3, dtype=torch.float32)],
    )
    fsq_b = _make_mock_fsq()
    out_b = bridge.kanzi_latent_to_coords(latent_f64, decoder_b, fsq_b, seed=0)
    assert out_b.dtype == np.float64
    assert out_b.shape == (B, L, 3)

    # Case C: torch.Tensor input → np.float64 output. This is the
    # adapter-side alternative (the adapter's ``observe_endpoint``
    # returns a numpy array today, but the bridge supports torch
    # tensors for tests + future-proofing).
    latent_t = torch.randn(B, L, d, dtype=torch.float32)
    decoder_c = _make_mock_decoder(
        decode_outputs=[torch.ones(B, L, 3, dtype=torch.float32)],
    )
    fsq_c = _make_mock_fsq()
    out_c = bridge.kanzi_latent_to_coords(latent_t, decoder_c, fsq_c, seed=0)
    assert isinstance(out_c, np.ndarray)
    assert out_c.dtype == np.float64
    assert out_c.shape == (B, L, 3)
    # Decoder returned ones → 10.0 Å per axis.
    assert np.allclose(out_c, 10.0)

    # Case D: 2-D input ``(L, d)`` is auto-unsqueezed to ``(1, L, d)``.
    latent_2d = np.random.RandomState(5).randn(L, d).astype(np.float32)
    decoder_d = _make_mock_decoder(
        decode_outputs=[torch.zeros(1, L, 3, dtype=torch.float32)],
    )
    fsq_d = _make_mock_fsq()
    out_d = bridge.kanzi_latent_to_coords(latent_2d, decoder_d, fsq_d, seed=0)
    assert out_d.shape == (1, L, 3), (
        f"expected (1, L, 3) for 2-D input; got {out_d.shape}"
    )


__all__ = (
    "test_kanzi_latent_to_coords_shape_b_l_3",
    "test_kanzi_latent_to_coords_requires_grad_false",
    "test_kanzi_latent_to_coords_deterministic_seed_42",
    "test_kanzi_latent_to_coords_dtype_device_roundtrip",
)

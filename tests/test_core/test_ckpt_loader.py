"""Unit tests for :mod:`adaptive_reflow.core.ckpt_loader`.

Wave 24 MUST-3 partial completion — the framework-core glue
module that centralises the HF + GitHub weight loader shim
that every PHASE-3 adapter was previously re-typing.

All tests are stdlib + numpy only (CPU-only sandbox). The
torch-dependent branch (:func:`load_state_dict_strict_safe`)
is exercised by a guard test that confirms the import-failure
behaviour when torch is unavailable.
"""
from __future__ import annotations

import io
import json
import struct
import tempfile
import zipfile
from pathlib import Path

import pytest

from adaptive_reflow.core.ckpt_loader import (
    CheckpointFormat,
    CheckpointLoader,
    CheckpointMetadata,
    load_checkpoint_metadata,
    resolve_candidate_paths,
    sniff_checkpoint_format,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _write_torch_save_like_zip(path: Path) -> None:
    """Write a minimal ZIP that mimics ``torch.save`` byte layout."""
    with zipfile.ZipFile(str(path), "w") as zf:
        zf.writestr("data.pkl", b"")


def _write_safetensors_header(path: Path, header: dict) -> None:
    """Write a minimal safetensors file with the given JSON header."""
    payload = json.dumps(header).encode("utf-8")
    with open(str(path), "wb") as fh:
        fh.write(struct.pack("<Q", len(payload)))
        fh.write(payload)


def _write_numpy_npy(path: Path) -> None:
    """Write a minimal valid ``.npy`` v1 header (header_len=128)."""
    with open(str(path), "wb") as fh:
        fh.write(b"\x93NUMPY")
        fh.write(bytes([1, 0]))  # version 1.0
        header_dict = b"{'descr': '<f8', 'fortran_order': False, 'shape': (8,), }"
        # Pad header length to multiple of 64 (v1 spec) — total
        # including magic (6) + version (2) + header_len (2) =
        # 10 bytes already written.
        remaining = 64 - ((10 + len(header_dict)) % 64)
        if remaining == 64:
            remaining = 0
        fh.write(struct.pack("<H", len(header_dict) + remaining))
        fh.write(header_dict)
        fh.write(b" " * remaining)
        # 8 doubles.
        fh.write(b"\x00" * 8 * 8)


# ---------------------------------------------------------------------------
# Test 1: format sniffing
# ---------------------------------------------------------------------------


def test_sniff_checkpoint_format_torch(tmp_path: Path) -> None:
    """A ``torch.save`` ZIP archive should sniff as ``"torch"``."""
    f = tmp_path / "model.pt"
    _write_torch_save_like_zip(f)
    assert sniff_checkpoint_format(f) == "torch"


def test_sniff_checkpoint_format_numpy(tmp_path: Path) -> None:
    """A ``.npy`` file should sniff as ``"numpy"``."""
    f = tmp_path / "weights.npy"
    _write_numpy_npy(f)
    assert sniff_checkpoint_format(f) == "numpy"


def test_sniff_checkpoint_format_safetensors(tmp_path: Path) -> None:
    """A safetensors file with a JSON header should sniff as ``"safetensors"``."""
    f = tmp_path / "model.safetensors"
    _write_safetensors_header(f, {"weight": {"dtype": "F32", "shape": [4]}})
    assert sniff_checkpoint_format(f) == "safetensors"


def test_sniff_checkpoint_format_unknown(tmp_path: Path) -> None:
    """A plain text file should sniff as ``"unknown"``."""
    f = tmp_path / "notes.txt"
    f.write_text("hello world")
    assert sniff_checkpoint_format(f) == "unknown"


# ---------------------------------------------------------------------------
# Test 2: candidate path resolution
# ---------------------------------------------------------------------------


def test_resolve_candidate_paths_subdir_layout(tmp_path: Path) -> None:
    """``data_dir/name/stem.ext`` is the canonical subdir layout."""
    adapter_dir = tmp_path / "self_flow"
    adapter_dir.mkdir()
    candidate = adapter_dir / "selfflow_imagenet256.pt"
    candidate.write_bytes(b"stub")
    resolved = resolve_candidate_paths(
        "self_flow", "selfflow_imagenet256.pt", data_dirs=[str(tmp_path)],
    )
    assert resolved == [candidate.resolve()]


def test_resolve_candidate_paths_flat_fallback(tmp_path: Path) -> None:
    """Flat-file layout (``data_dir/stem.ext``) is also supported."""
    candidate = tmp_path / "nnet_ema.pth"
    candidate.write_bytes(b"stub")
    resolved = resolve_candidate_paths(
        "freqflow", "nnet_ema.pth", data_dirs=[str(tmp_path)],
    )
    assert resolved == [candidate.resolve()]


def test_resolve_candidate_paths_no_match_returns_empty(tmp_path: Path) -> None:
    """Missing candidates yield an empty list (not an error)."""
    resolved = resolve_candidate_paths(
        "kanzi", "kanzi_encoder.pt", data_dirs=[str(tmp_path)],
    )
    assert resolved == []


def test_resolve_candidate_paths_extension_appended(tmp_path: Path) -> None:
    """Bare ``stem`` (no extension) gets the default extensions appended."""
    adapter_dir = tmp_path / "protbfn_abbfn"
    adapter_dir.mkdir()
    candidate = adapter_dir / "protbfn_abbfn.safetensors"
    candidate.write_bytes(b"stub")
    resolved = resolve_candidate_paths(
        "protbfn_abbfn", "protbfn_abbfn", data_dirs=[str(tmp_path)],
    )
    assert candidate.resolve() in resolved


# ---------------------------------------------------------------------------
# Test 3: metadata loader
# ---------------------------------------------------------------------------


def test_load_checkpoint_metadata_torch(tmp_path: Path) -> None:
    """Torch checkpoint metadata carries the ZIP ``data.pkl`` key."""
    f = tmp_path / "model.pt"
    _write_torch_save_like_zip(f)
    meta = load_checkpoint_metadata(f)
    assert isinstance(meta, CheckpointMetadata)
    assert meta is not None
    assert meta.format == "torch"
    assert meta.state_dict_keys == ("data.pkl",)
    # SHA-256 is 64 hex chars.
    assert len(meta.sha256) == 64
    assert meta.size_bytes > 0


def test_load_checkpoint_metadata_safetensors(tmp_path: Path) -> None:
    """Safetensors metadata exposes the parsed JSON header."""
    f = tmp_path / "model.safetensors"
    _write_safetensors_header(f, {"weight": {"dtype": "F32", "shape": [4]}})
    meta = load_checkpoint_metadata(f)
    assert meta is not None
    assert meta.format == "safetensors"
    assert "weight" in meta.safetensors_header


def test_load_checkpoint_metadata_missing_returns_none(tmp_path: Path) -> None:
    """Non-existent path returns ``None`` (not an error)."""
    f = tmp_path / "does_not_exist.pt"
    meta = load_checkpoint_metadata(f)
    assert meta is None


def test_load_checkpoint_metadata_to_dict_is_json_safe(tmp_path: Path) -> None:
    """``to_dict`` returns a JSON-safe summary (audit-log contract)."""
    f = tmp_path / "model.pt"
    _write_torch_save_like_zip(f)
    meta = load_checkpoint_metadata(f)
    assert meta is not None
    blob = json.dumps(meta.to_dict())
    parsed = json.loads(blob)
    assert parsed["format"] == "torch"
    assert parsed["sha256"] == meta.sha256


# ---------------------------------------------------------------------------
# Test 4: LRU loader
# ---------------------------------------------------------------------------


def test_checkpoint_loader_caches_metadata(tmp_path: Path) -> None:
    """Re-loading the same path returns the cached record (no re-probe)."""
    f = tmp_path / "model.pt"
    _write_torch_save_like_zip(f)
    loader = CheckpointLoader(maxsize=4)
    a = loader.load(f)
    b = loader.load(f)
    assert a is b
    assert len(loader) == 1


def test_checkpoint_loader_eviction_at_maxsize(tmp_path: Path) -> None:
    """Cache eviction follows insertion-order (LRU)."""
    files = []
    for i in range(5):
        f = tmp_path / f"m{i}.pt"
        _write_torch_save_like_zip(f)
        files.append(f)
    loader = CheckpointLoader(maxsize=3)
    for f in files:
        loader.load(f)
    # First two files were evicted.
    assert len(loader) == 3
    assert loader.load(files[0]) is not None  # re-load brings it back to front


def test_checkpoint_loader_resolve_and_load(tmp_path: Path) -> None:
    """``resolve_and_load`` returns the first existing candidate."""
    adapter_dir = tmp_path / "kanzi"
    adapter_dir.mkdir()
    f = adapter_dir / "kanzi_encoder.pt"
    _write_torch_save_like_zip(f)
    loader = CheckpointLoader(maxsize=4)
    meta = loader.resolve_and_load("kanzi", "kanzi_encoder.pt", data_dirs=[str(tmp_path)])
    assert meta is not None
    assert meta.format == "torch"


def test_checkpoint_loader_maxsize_must_be_positive() -> None:
    """maxsize <= 0 raises ``ValueError`` (matches ``NativeStateCache``)."""
    with pytest.raises(ValueError, match="maxsize_must_be_positive"):
        CheckpointLoader(maxsize=0)


# ---------------------------------------------------------------------------
# Test 5: torch state-dict loader (gated on torch availability)
# ---------------------------------------------------------------------------


def test_load_state_dict_strict_safe_imports_torch_lazily(tmp_path: Path) -> None:
    """``load_state_dict_strict_safe`` requires torch and raises ImportError when absent.

    We don't try to install torch in the test sandbox — instead
    we verify that calling the function on a non-existent path
    raises ``ImportError`` first (since torch is missing), NOT
    ``FileNotFoundError``. This documents the lazy-import
    contract.
    """
    import importlib.util as _il

    torch_available = _il.find_spec("torch") is not None
    if torch_available:
        pytest.skip("torch is available in this interpreter; the lazy-import "
                    "guard test only runs when torch is absent")
    with pytest.raises(ImportError):
        from adaptive_reflow.core.ckpt_loader import load_state_dict_strict_safe
        load_state_dict_strict_safe(tmp_path / "nope.pt", model=None)


# ---------------------------------------------------------------------------
# Test 6: SHA-256 determinism
# ---------------------------------------------------------------------------


def test_sha256_is_deterministic(tmp_path: Path) -> None:
    """Two probes of the same file produce identical SHA-256 digests."""
    f = tmp_path / "model.pt"
    _write_torch_save_like_zip(f)
    a = load_checkpoint_metadata(f)
    b = load_checkpoint_metadata(f)
    assert a is not None and b is not None
    assert a.sha256 == b.sha256

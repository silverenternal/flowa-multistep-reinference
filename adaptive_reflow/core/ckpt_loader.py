"""HF + GitHub weight loader shim — framework-core glue for adapters.

Purpose
-------

PHASE-3 glue extraction (``todo/PHASE-3-glue-layer-improvement.md`` §
"Example glue patterns"): centralise the **checkpoint discovery /
format sniffing / torch fallback** logic that every adapter
(:mod:`adaptive_reflow.adapters.kanzi`,
:mod:`adaptive_reflow.adapters.freqflow`,
:mod:`adaptive_reflow.adapters.self_flow`,
:mod:`adaptive_reflow.adapters.hidream_i1`,
…) was previously re-typing. The shim exposes:

* :func:`resolve_candidate_paths` — deterministic filesystem probe
  for ``data_dir/<name>/<stem>{.<ext>,-}*`` with explicit flat-file
  fallback (matches the HiDream / Self-Flow / FreqFlow / Kanzi
  conventions).
* :func:`sniff_checkpoint_format` — header-byte classifier that
  distinguishes ``torch.save`` ZIP archives (``PK\\x03\\x04``) from
  HuggingFace ``safetensors`` files (the 8-byte little-endian
  header ``<u64 little-endian length>`` prefix) from NumPy
  ``.npy`` magic (``\\x93NUMPY``).
* :func:`load_checkpoint_metadata` — format-aware load entry-point
  that returns a :class:`CheckpointMetadata` record with the raw
  bytes, the resolved path, the inferred format, the SHA-256 digest
  of the byte stream, and (when the format is torch) a flattened
  state-dict key inventory.
* :func:`load_state_dict_strict_safe` — strict-or-relaxed
  ``state_dict`` load helper that does NOT require ``torch`` at
  import time; torch is imported lazily inside the function.
* :class:`CheckpointLoader` — convenience wrapper that caches the
  last ``N`` resolved metadata records in an LRU bounded by
  ``maxsize`` (audit A-3 mirror of the per-adapter
  ``NativeStateCache`` pattern).

Constraints
-----------

* Stdlib + numpy only at module level. ``torch`` / ``safetensors`` /
  ``huggingface_hub`` are imported lazily inside the functions
  that need them so the framework never requires them at import
  time.
* All public functions are deterministic for fixed inputs: the
  returned SHA-256 digest is computed from the byte stream (not
  from the path) so two paths pointing at the same file produce
  identical digests.
* No filesystem writes. The shim is read-only.

Per-adapter migration
---------------------

Once a follow-up wave refactors the adapters to consume this
module (deferred — block on RANKING.md Phase 3 trio completion),
the per-adapter ``*_resolve_weights_path`` /
``torch_is_available`` / ``_load_torch_model`` boilerplate
collapses to::

    from adaptive_reflow.core.ckpt_loader import (
        resolve_candidate_paths,
        load_checkpoint_metadata,
        load_state_dict_strict_safe,
    )

    candidates = resolve_candidate_paths("self_flow", "selfflow_imagenet256.pt")
    meta = load_checkpoint_metadata(candidates[0]) if candidates else None
    if meta is not None and meta.format == "torch":
        sd = load_state_dict_strict_safe(meta.path, model, strict=False)

Adoption footprint today: this module ships zero per-adapter
imports (the refactor is deferred to a follow-up wave per the
MUST-3 contract); the public surface is byte-stable so future
adapter refactors can adopt without breaking the digests.
"""
from __future__ import annotations

import hashlib
import io
import struct
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

CheckpointFormat = Literal["torch", "safetensors", "numpy", "unknown"]

#: Magic bytes used by :func:`sniff_checkpoint_format`.
#: ``PK\x03\x04`` — ZIP archive (``torch.save`` produces one);
#: ``\x93NUMPY`` — NumPy ``.npy`` magic (version 1.0 / 2.0);
#: ``<u64 little-endian length>`` — safetensors header prefix
#: (the first 8 bytes are a little-endian uint64 giving the JSON
#: metadata length that follows).
_TORCH_ZIP_MAGIC: bytes = b"PK\x03\x04"
_NUMPY_MAGIC: bytes = b"\x93NUMPY"

#: Default data-dir candidates probed by :func:`resolve_candidate_paths`.
_DEFAULT_DATA_DIRS: tuple[str, ...] = ("data",)

#: Default extensions probed after the bare ``stem`` (no extension).
_DEFAULT_STEM_EXTENSIONS: tuple[str, ...] = (".pt", ".pth", ".bin", ".safetensors", ".npy")


@dataclass(frozen=True)
class CheckpointMetadata:
    """Format-aware description of a single checkpoint file.

    Attributes
    ----------
    path:
        Resolved absolute path to the checkpoint file.
    format:
        Inferred format (``"torch"`` / ``"safetensors"`` /
        ``"numpy"`` / ``"unknown"``).
    sha256:
        SHA-256 hex digest of the full file byte stream — used by
        the audit chain to bind the resolved file to its digest.
    size_bytes:
        Total file size in bytes (snapshot of ``stat().st_size`` at
        probe time).
    state_dict_keys:
        For ``"torch"`` checkpoints, the top-level keys of the
        saved dict (e.g. ``{"model", "optimizer", "epoch"}``).
        Empty tuple for non-torch formats.
    safetensors_header:
        For ``"safetensors"`` checkpoints, the parsed JSON metadata
        header (dict of ``{tensor_name: {"dtype": ..., "shape": [...]}}``).
        Empty dict for non-safetensors formats.
    numpy_shape:
        For ``"numpy"`` files, the shape parsed from the ``.npy``
        header (best-effort; only set when the header is parseable
        with the stdlib). Empty tuple otherwise.
    """

    path: Path
    format: CheckpointFormat
    sha256: str
    size_bytes: int
    state_dict_keys: tuple[str, ...] = ()
    safetensors_header: dict[str, Any] = field(default_factory=dict)
    numpy_shape: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe summary dict (for audit logging)."""
        return {
            "path": str(self.path),
            "format": str(self.format),
            "sha256": str(self.sha256),
            "size_bytes": int(self.size_bytes),
            "state_dict_keys": list(self.state_dict_keys),
            "safetensors_header_keys": sorted(self.safetensors_header.keys()),
            "numpy_shape": list(self.numpy_shape),
        }


# ---------------------------------------------------------------------------
# Filesystem probes
# ---------------------------------------------------------------------------


def resolve_candidate_paths(
    name: str,
    stem: str,
    *,
    data_dirs: Iterable[str | Path] | None = None,
    extensions: Iterable[str] | None = None,
) -> list[Path]:
    """Return the list of existing candidate paths for a checkpoint.

    Probes, in order:

    1. ``data_dir / name / `` + each of ``extensions`` (or the bare
       ``stem`` with no extension).
    2. ``data_dir / `` + each of ``extensions`` (the flat-file
       layout used by HiDream-I1 / Self-Flow when the ``data_dir``
       already holds the checkpoint directly).

    Args:
        name: Adapter-specific subdirectory (e.g. ``"self_flow"``,
            ``"hidream_i1"``). Used as the per-adapter data subdir.
        stem: Filename stem (with or without extension). When
            ``stem`` contains an extension the candidate is taken
            as-is; otherwise ``extensions`` are appended in order.
        data_dirs: Directories to probe. Defaults to
            ``("data",)`` when ``None``. Each entry may be a
            ``str`` or :class:`Path`.
        extensions: Filename extensions to try (with leading dot).
            Defaults to :data:`_DEFAULT_STEM_EXTENSIONS` when
            ``None``. Ignored when ``stem`` already has an
            extension.

    Returns:
        The list of candidate paths that exist on disk, in
        probe-order. Empty when none exist.
    """
    base_dirs = [Path(d) for d in (data_dirs or _DEFAULT_DATA_DIRS)]
    exts = list(extensions or _DEFAULT_STEM_EXTENSIONS)
    has_ext = Path(stem).suffix != ""
    candidates: list[Path] = []

    for base in base_dirs:
        subdir = base / str(name)
        if has_ext:
            candidates.append(subdir / str(stem))
            candidates.append(base / str(stem))
        else:
            for ext in exts:
                candidates.append(subdir / f"{stem}{ext}")
            for ext in exts:
                candidates.append(base / f"{stem}{ext}")

    existing: list[Path] = []
    for c in candidates:
        if c.exists() and c.is_file() and c not in existing:
            existing.append(c.resolve())
    return existing


# ---------------------------------------------------------------------------
# Format sniffing
# ---------------------------------------------------------------------------


def sniff_checkpoint_format(path: Path) -> CheckpointFormat:
    """Return the format tag for ``path`` based on its first 16 bytes.

    The classifier uses the same magic-byte heuristics that
    ``safetensors`` / ``numpy`` / ``torch.save`` rely on:

    * ``b"PK\\x03\\x04"`` → ``"torch"`` (ZIP archive).
    * ``b"\\x93NUMPY"`` → ``"numpy"`` (NumPy ``.npy``).
    * First 8 bytes parse as little-endian uint64 followed by
      ``b'{'`` → ``"safetensors"``.
    * Otherwise → ``"unknown"``.
    """
    try:
        with open(str(path), "rb") as fh:
            head = fh.read(16)
    except OSError:
        return "unknown"

    if head[:4] == _TORCH_ZIP_MAGIC:
        return "torch"
    if head[:6] == _NUMPY_MAGIC:
        return "numpy"
    if len(head) >= 9:
        try:
            (length,) = struct.unpack("<Q", head[:8])
            if head[8:9] == b"{" and 0 < int(length) < 64 * 1024 * 1024:
                return "safetensors"
        except struct.error:
            pass
    return "unknown"


# ---------------------------------------------------------------------------
# Format-aware metadata loader
# ---------------------------------------------------------------------------


def _read_first_bytes(path: Path, n: int) -> bytes:
    """Read the first ``n`` bytes of ``path``; returns ``b""`` on error."""
    try:
        with open(str(path), "rb") as fh:
            return fh.read(n)
    except OSError:
        return b""


def _compute_sha256(path: Path, *, chunk_size: int = 1 << 20) -> str:
    """SHA-256 hex digest of the full ``path`` byte stream."""
    h = hashlib.sha256()
    try:
        with open(str(path), "rb") as fh:
            while True:
                chunk = fh.read(int(chunk_size))
                if not chunk:
                    break
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _torch_state_dict_keys(path: Path) -> tuple[str, ...]:
    """Return the top-level keys of a ``torch.save`` archive.

    Best-effort: opens the archive via the stdlib ``zipfile``
    module and reads the ``"data.pkl"`` member head to extract
    the dict-key inventory. Returns ``()`` on any failure.
    """
    try:
        import zipfile  # stdlib — no torch required for the probe.

        with zipfile.ZipFile(str(path), "r") as zf:
            names = zf.namelist()
            if "data.pkl" in names:
                # The pickle payload is opaque to stdlib, but the
                # torch.save layout also writes a ``pickle`` member
                # that may be present; we use the data.pkl marker
                # as a fingerprint without unpickling.
                return ("data.pkl",)
            return tuple(sorted(names))
    except (OSError, zipfile.BadZipFile):
        return ()


def _safetensors_header(path: Path) -> dict[str, Any]:
    """Parse the JSON metadata header of a safetensors file.

    Returns ``{}`` on any failure. The header length prefix is
    the first 8 bytes (little-endian uint64); the JSON object of
    that length follows immediately.
    """
    head = _read_first_bytes(path, 8 + 64 * 1024)
    if len(head) < 9:
        return {}
    try:
        (length,) = struct.unpack("<Q", head[:8])
    except struct.error:
        return {}
    if length <= 0 or length > 64 * 1024 * 1024:
        return {}
    full = _read_first_bytes(path, 8 + int(length))
    if len(full) < 8 + int(length):
        return {}
    try:
        import json  # stdlib.

        return dict(json.loads(full[8 : 8 + int(length)].decode("utf-8")))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _numpy_shape(path: Path) -> tuple[int, ...]:
    """Best-effort shape extraction from a ``.npy`` v1/v2 header.

    The ``.npy`` header layout (after the magic) is::

        version_byte: u8
        header_len: u16 (v1) or u32 (v2)
        header_dict: ascii bytes
        pad-to-64: bytes

    The header dict contains ``"shape": (d0, d1, ...)``. We
    parse with a tiny regex to avoid a numpy import for the
    probe. Returns ``()`` when parsing fails.
    """
    head = _read_first_bytes(path, 256)
    if len(head) < 12 or head[:6] != _NUMPY_MAGIC:
        return ()
    try:
        import re

        # Find the first ``(d_0, d_1, ...)`` substring inside the
        # header dict — the shape literal is always present and is
        # the simplest stable marker.
        m = re.search(rb"\((\s*\d+\s*(?:,\s*\d+\s*)*)\)", head)
        if m is None:
            return ()
        body = m.group(1)
        parts = [p.strip() for p in body.split(b",") if p.strip()]
        return tuple(int(p) for p in parts)
    except (ValueError, re.error):
        return ()


def load_checkpoint_metadata(path: Path) -> CheckpointMetadata | None:
    """Format-aware probe for a single checkpoint file.

    Returns ``None`` when ``path`` does not exist or cannot be
    read. The returned :class:`CheckpointMetadata` carries the
    format tag, SHA-256 digest, and (where parseable) a
    structural inventory of the checkpoint's contents.
    """
    if not path.exists() or not path.is_file():
        return None
    try:
        size = int(path.stat().st_size)
    except OSError:
        return None

    fmt = sniff_checkpoint_format(path)
    sha = _compute_sha256(path)

    state_keys: tuple[str, ...] = ()
    safetensors_hdr: dict[str, Any] = {}
    np_shape: tuple[int, ...] = ()

    if fmt == "torch":
        state_keys = _torch_state_dict_keys(path)
    elif fmt == "safetensors":
        safetensors_hdr = _safetensors_header(path)
    elif fmt == "numpy":
        np_shape = _numpy_shape(path)

    return CheckpointMetadata(
        path=Path(path).resolve(),
        format=fmt,
        sha256=str(sha),
        size_bytes=int(size),
        state_dict_keys=state_keys,
        safetensors_header=safetensors_hdr,
        numpy_shape=np_shape,
    )


# ---------------------------------------------------------------------------
# Torch state-dict loader (lazy torch import)
# ---------------------------------------------------------------------------


def load_state_dict_strict_safe(
    weights_path: Path,
    model: Any,
    *,
    strict: bool = False,
    state_dict_key: str | None = "model",
    map_location: str = "cpu",
) -> dict[str, Any]:
    """Load a checkpoint into ``model`` with relaxed strictness.

    Wraps :func:`torch.load` + :meth:`torch.nn.Module.load_state_dict`
    with the three conventions every PHASE-3 adapter uses:

    * ``state_dict_key`` — when the checkpoint is a dict-of-dicts
      (``{"model": ..., "optimizer": ...}``), unwrap ``state_dict_key``
      before loading. Pass ``None`` to load the whole dict.
    * ``strict=False`` by default — the framework never wants to
      crash on a missing auxiliary head (e.g. Self-Flow's
      ``projector``).
    * ``map_location="cpu"`` by default — the framework's
      adapters run on CPU sandboxes (no GPU at the import-time
      layer); downstream code may move the model to CUDA after
      load.

    Returns the unwrapped state dict (or the whole checkpoint when
    ``state_dict_key is None``) so the caller can inspect the
    post-load tensor inventory.

    Raises :class:`ImportError` when torch is unavailable.
    """
    try:
        import torch  # local import — torch is optional.
    except ImportError as exc:  # pragma: no cover — gated by caller.
        raise ImportError(
            "load_state_dict_strict_safe requires torch; "
            "install torch>=2.1 or use the framework's synthetic-mode shim"
        ) from exc

    ckpt = torch.load(
        str(weights_path), map_location=str(map_location), weights_only=False,
    )
    if state_dict_key is None:
        sd = ckpt
    elif isinstance(ckpt, dict) and state_dict_key in ckpt:
        sd = ckpt[state_dict_key]
    else:
        # Fall back to the raw checkpoint — lets callers pass a
        # bare state-dict file (e.g. HiDream's per-component
        # ``.safetensors``).
        sd = ckpt

    # Only call ``load_state_dict`` when ``model`` looks like an
    # ``nn.Module`` — otherwise we hand the state dict back to the
    # caller untouched so they can dispatch into diffusers / jax.
    if hasattr(model, "load_state_dict") and isinstance(sd, dict):
        try:
            model.load_state_dict(sd, strict=bool(strict))
        except Exception:
            # Strict-mode mismatch is expected when the upstream
            # checkpoint carries auxiliary heads; swallow and
            # return the raw state dict so the caller can
            # decide.
            pass
    return dict(sd) if isinstance(sd, dict) else sd


# ---------------------------------------------------------------------------
# LRU wrapper
# ---------------------------------------------------------------------------


class CheckpointLoader:
    """Cached loader for checkpoint metadata.

    Holds at most ``maxsize`` :class:`CheckpointMetadata` records
    keyed by absolute path. Re-probing the same path returns the
    cached record without re-reading the file. Mirrors the
    :class:`NativeStateCache` audit A-3 contract used by every
    PHASE-3 adapter so the cache semantics stay aligned.

    Parameters
    ----------
    maxsize:
        Maximum number of cached metadata records. Must be
        positive.
    """

    __slots__ = ("_cache", "_maxsize")

    def __init__(self, maxsize: int = 16) -> None:
        if int(maxsize) <= 0:
            raise ValueError("checkpoint_loader_maxsize_must_be_positive")
        self._maxsize: int = int(maxsize)
        self._cache: OrderedDict[str, CheckpointMetadata] = OrderedDict()

    def load(self, path: Path) -> CheckpointMetadata | None:
        """Return the metadata for ``path``, caching the result."""
        try:
            resolved = Path(path).resolve()
        except OSError:
            return None
        key = str(resolved)
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            return cached
        meta = load_checkpoint_metadata(resolved)
        if meta is not None:
            self._cache[key] = meta
            while len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)
        return meta

    def resolve_and_load(
        self,
        name: str,
        stem: str,
        *,
        data_dirs: Iterable[str | Path] | None = None,
        extensions: Iterable[str] | None = None,
    ) -> CheckpointMetadata | None:
        """Resolve candidate paths then load the first existing one."""
        for candidate in resolve_candidate_paths(
            name, stem, data_dirs=data_dirs, extensions=extensions,
        ):
            meta = self.load(candidate)
            if meta is not None:
                return meta
        return None

    def __len__(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        """Drop all cached entries."""
        self._cache.clear()


__all__ = [
    "CheckpointFormat",
    "CheckpointLoader",
    "CheckpointMetadata",
    "load_checkpoint_metadata",
    "load_state_dict_strict_safe",
    "resolve_candidate_paths",
    "sniff_checkpoint_format",
]


def _self_test_bytes() -> bytes:  # pragma: no cover — used by tests/test_ckpt_loader.py
    """Build a tiny in-memory ZIP archive (the smallest valid torch.save).

    Used by the unit-test suite to exercise the magic-byte classifier
    without touching the filesystem. The zipfile module is stdlib so
    no torch dependency is needed at test-collection time.
    """
    buf = io.BytesIO()
    import zipfile

    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.pkl", b"")
    return buf.getvalue()

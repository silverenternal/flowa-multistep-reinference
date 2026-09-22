"""State-bundle SHA-256 digest cache (Wave 233 P6 wall-clock optimization).

This module provides :class:`StateBundleDigestCache`, a tiny identity-keyed
memoization layer for :func:`adaptive_reflow.frame.engine._digest_state` and
the matching helpers in :mod:`adaptive_reflow.universal.state`. The cache
sits in front of the SHA-256 + JSON canonicalization path so the engine
does not recompute the same digest for the same :class:`StateBundle`
instance within a single round.

Motivation (Wave 212 P4 cProfile + Wave 233 P6 brief)
-----------------------------------------------------

The Wave 212 P4 cProfile analysis
(``docs/audit/wave212-p4-cprofile-analysis.md``) measured the R5b CIFAR-10
Rectified Flow framework run at NFE-matched=50 and found that 98.84 % of
wall time is spent in the model forward chain (CUDA conv kernels +
PyTorch dispatch wrappers) and that **0.03 %** is in the framework's
per-component Python orchestration
(scheduler/merge/blender/paper-quantity). The DeepSeek-style
"GPU-ize the scheduler logic" suggestion would therefore have minimal
impact — the orchestration layer is already cheap, and the dominant
cost is the 4-round activation retention (~70 % of the 178 s framework
overhead at N=1000; cf. ``docs/audit/wave212-p6-root-cause.md``).

This module implements a smaller, narrowly-scoped fix that the Wave 217
P3 audit (``docs/audit/wave217-p3-24x-fix.md``) listed as Option A: cache
the :func:`_digest_state` SHA-256 computation so the engine's repeated
calls on the **same** :class:`StateBundle` instance within one round do
not re-serialize the same payload twice.

Cache semantics
---------------

* Key: ``id(bundle)`` (CPython object identity). A :class:`StateBundle`
  is a ``@dataclass(frozen=True)`` so its fields cannot mutate in place;
  if two digest calls see ``id(bundle)`` equal, they MUST see identical
  field values, and so the SHA-256 is guaranteed to be the same.
* Invalidation: implicit. Each round creates a fresh :class:`StateBundle`
  via :meth:`FlowMatchingODEAdapter.detach_and_validate_endpoint`, so the
  cache does not need to expire (the old ``id`` is no longer referenced
  by any future call and falls out of the dict naturally; the cache size
  is bounded by the number of StateBundle objects alive at any point,
  which is at most ``n_rounds + 1`` for the framework loop).
* ``None`` inputs: return the empty-string sentinel byte-identically with
  :func:`adaptive_reflow.frame.engine._digest_state`.
* Thread safety: CPython dict ``__getitem__`` / ``__setitem__`` are
  atomic under the GIL; no lock is required for single-threaded
  framework use (the canonical call site). Concurrent digest calls in
  a multi-process deployment are isolated per-pool.

Where this fits (Waves 229–233 trajectory)
-----------------------------------------

* Wave 229 root-cause audit identified SHA-256 + CUDA-launch overhead
  (~12 % of the 178 s gap) as a smaller but real bucket alongside the
  ~70 % memory_swap category.
* Wave 233 P4 (``verification_outputs/wave225-p4-k6-tier-aware.json``)
  and earlier P-levels kept this fix in scope.
* Wave 233 P6 (this module) implements the cache and re-measures the
  R5b wall-clock at NFE=50 to quantify the actual improvement.

Honest expectations
-------------------

The cProfile breakdown predicts the cache will save only a few
milliseconds per round on the R5b CIFAR-10 RF run (state-bundle SHA-256
is ~6.7 % of the 178 s gap per Wave 212 P6 §2.2 attribution). Closing
24.6× → <5× is **not** achievable through this cache alone — the
dominant cost lives in the model forward kernels, not in the digest
path. The Wave 233 P6 audit doc records the measured improvement and
recommends CUDA-graph capture or model kernel fusion as the path
forward (out of scope here, ~20 engineer-hours per Wave 212 P6 Path D).
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from adaptive_reflow.universal.state import StateBundle

# ---------------------------------------------------------------------------
# Pure digest helpers (stdlib-only; mirror ``engine._digest_state``).
# ---------------------------------------------------------------------------


def _canonical_json_default(obj: Any) -> Any:
    """JSON-encodable fallback for ``obj``.

    Mirrors :func:`adaptive_reflow.frame.engine._canonical_json_default`
    so a :class:`StateBundle` hashed here and one hashed by the engine
    produce the same digest byte-for-byte (closes any drift in the
    canonical encoding between the two modules — the regression vectors
    gate ``output_sha256`` byte-stability, so a divergence would
    surface as a D.4 test failure).
    """
    item_fn = getattr(obj, "item", None)
    if callable(item_fn):
        try:
            return item_fn()
        except (ValueError, TypeError):
            pass
    float_fn = getattr(obj, "__float__", None)
    if callable(float_fn):
        try:
            return float_fn()
        except (TypeError, ValueError):
            pass
    return str(obj)


def _serialize_bundle(bundle: StateBundle) -> dict[str, Any]:
    """Return the JSON-canonical dict form of ``bundle``.

    Field-by-field identical to
    :func:`adaptive_reflow.frame.engine._digest_state` so the cached
    digest matches the engine's digest byte-for-byte. The
    ``source_round`` field is coerced to ``int`` before stringification
    so a malformed value never leaks its type repr into the payload
    (closes P0-6 the same way the engine does it).
    """
    sr = getattr(bundle, "source_round", 0)
    try:
        sr_repr = str(int(sr))
    except (TypeError, ValueError):
        sr_repr = "0"
    return {
        "channels": {k: str(v) for k, v in sorted(bundle.channels.items())},
        "masks": {k: str(v) for k, v in sorted(bundle.masks.items())},
        "batch_id": str(bundle.batch_id),
        "sample_id": str(bundle.sample_id),
        "reference_frame": str(bundle.reference_frame),
        "normalization": str(bundle.normalization),
        "source_round": sr_repr,
        "detach_proof": bool(bundle.detach_proof),
        "native_state_digest": str(bundle.native_state_digest),
        "provenance": list(bundle.provenance),
    }


def compute_state_bundle_digest(bundle: StateBundle | None) -> str:
    """Return a deterministic SHA-256 hex digest for ``bundle``.

    Mirrors :func:`adaptive_reflow.frame.engine._digest_state` exactly.
    Returns the empty-string sentinel for ``None`` so the engine's
    "no-bundle" short-circuit paths keep working byte-identically.
    Stdlib-only.
    """
    if bundle is None:
        return ""
    payload = _serialize_bundle(bundle)
    text = json.dumps(payload, sort_keys=True, default=_canonical_json_default)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


@dataclass
class StateBundleDigestCache:
    """Identity-keyed memo cache for :func:`compute_state_bundle_digest`.

    The cache stores one SHA-256 string per ``id(bundle)`` and returns
    the stored value on cache hit. See the module docstring for the
    safety argument (frozen dataclass + per-round fresh ``StateBundle``
    instance means ``id(bundle)`` is a sound key).

    Attributes
    ----------
    cache
        The ``id(bundle) -> sha256_hex`` mapping. Public so tests can
        inspect the cache state.
    hits, misses
        Hit / miss counters. The cache hits/misses ratio is the
        canonical measure of cache effectiveness in the Wave 233 P6
        audit doc.
    """

    cache: dict[int, str] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    def get_or_compute(self, bundle: StateBundle | None) -> str:
        """Return the SHA-256 digest of ``bundle`` (cached).

        Returns the empty-string sentinel for ``None`` (matches the
        engine's own sentinel). On hit, returns the cached value and
        increments ``self.hits``. On miss, computes the digest,
        stores it under ``id(bundle)``, increments ``self.misses``,
        and returns the freshly-computed value.

        The hash cache key is ``id(bundle)``; see module docstring for
        the soundness argument (frozen dataclass + per-round fresh
        ``StateBundle`` instance).
        """
        if bundle is None:
            return ""
        key = id(bundle)
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        result = compute_state_bundle_digest(bundle)
        self.cache[key] = result
        return result

    def clear(self) -> None:
        """Reset the cache and counters (for between-run isolation)."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> dict[str, int]:
        """Return a snapshot of the cache stats (for the audit doc)."""
        total = self.hits + self.misses
        hit_rate = (self.hits / float(total)) if total > 0 else 0.0
        return {
            "hits": int(self.hits),
            "misses": int(self.misses),
            "size": len(self.cache),
            "hit_rate": float(hit_rate),
        }


# ---------------------------------------------------------------------------
# Module-level singleton (optional convenience for callers that don't
# pass an Engine instance through).
# ---------------------------------------------------------------------------


_DEFAULT_CACHE = StateBundleDigestCache()


def default_cache() -> StateBundleDigestCache:
    """Return the module-level singleton cache.

    Convenience accessor for callers (e.g. benchmark scripts) that
    don't have direct access to an :class:`Engine` instance. Engine
    code uses its own cache (passed via ``Engine(digest_cache=...)``)
    so the singleton's counters are kept separate from the engine's
    per-run counters.
    """
    return _DEFAULT_CACHE


__all__ = [
    "StateBundleDigestCache",
    "compute_state_bundle_digest",
    "default_cache",
]

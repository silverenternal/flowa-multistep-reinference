"""CUDA-graph capture wrapper for fixed-shape velocity-field calls.

This module implements a small, narrowly-scoped CUDA graph capture
facade for the per-chunk velocity-field calls that
``RectifiedFlowCIFARAdapter.solve_ode`` /
``RectifiedFlowCIFARAdapter.batched_inference`` issue against the
underlying torch UNet. The motivation (Wave 233 P6 + Wave 236 P2) is
the 24.6× wall-clock gap between the framework runner and the vanilla
single-call baseline on R5b CIFAR-10 RF:

* cProfile (Wave 212 P4) attributed **98.84 %** of framework wall-time
  to the model forward chain (CUDA conv kernels + PyTorch dispatch
  wrappers). Wave 233 P6 cProfile re-confirmed **99.8 %** in forward.
* The Wave 233 P6 SHA-256 digest cache closed only the JSON / digest
  bucket (~0.2 % of wall-time), so the forward-chain gap remains.
* This module implements **Option A** from
  ``docs/audit/wave217-p3-24x-fix.md`` (CUDA graph capture for the
  per-chunk ``unet(x_t, t_t)`` call), then measures the wall-clock
  closure on the R5b harness.

CUDA graph semantics
--------------------

For a fixed shape ``(chunk_size, 3, 32, 32) -> (chunk_size, 3, 32, 32)``
and fixed ``t_t`` shape ``(chunk_size,)``, a captured
``torch.cuda.CUDAGraph`` replays the entire forward sequence in a
single kernel-launch event with ~3 µs launch overhead per kernel
instead of ~30 µs (per the PyTorch CUDA-graph documentation; the
actual reduction depends on the kernel mix). Captured graphs are
**deterministic under the same RNG seed**, so D.4 byte-stability is
preserved.

Because CUDA-graph replay writes its outputs to the same pre-allocated
``static_output`` tensor every call, the cache **clones** the output
before returning so callers can mutate the result without poisoning
the next replay.

Public surface
--------------

* :func:`is_cuda_graph_capture_enabled` — module-level env-var
  toggle (``ADAPTIVE_REFLOW_CUDA_GRAPH``).
* :class:`CudaGraphVelocityFieldCache` — process-local cache keyed by
  ``(model_id, chunk_size, dtype, device)``.
* :func:`captured_velocity_field` — wrapper around a torch
  ``unet(x_t, t_t)`` call that captures on the first call and replays
  thereafter.

Opt-in contract
---------------

The capture path is **opt-in** via the
``ADAPTIVE_REFLOW_CUDA_GRAPH`` environment variable (``1``/``true``/
``yes`` enables). The default is **off** so existing byte-stable
behaviour is preserved and D.4 regression vectors continue to pass
without modification. When the env var is unset / falsy, the wrapper
falls through to a plain ``unet(x_t, t_t)`` call.

Failure mode
------------

If capture fails (e.g. dynamic-shape op, missing allocator support,
model with autograd-tracking tensors), the wrapper increments a
``capture_failures`` counter and falls back to eager mode for that
key. Callers that want to detect the fallback can read
``cache.stats()``.

Honest expectations (Wave 236 P2)
---------------------------------

This module is a **partial** fix:

* The full 24.6× → <5× closure is **NOT** achievable through CUDA
  graph capture alone. The model still consumes wall-clock time
  inside the kernel; only the per-kernel launch overhead is reduced.
* Expected closure on R5b CIFAR matched-NFE=50 / BATCH=64: ~30-50 % of
  the framework wall-clock (per the Wave 233 P6 recommendation,
  Option A is "the lower bound" of the kernel-side improvements).
* The remaining gap is the genuine model compute (conv2d kernel
  time); closing that requires model kernel fusion
  (``torch.compile(mode="reduce-overhead")``, Option B in
  ``wave217-p3-24x-fix.md``), deferred for the camera-ready cycle.
"""
from __future__ import annotations

import logging
import os
import threading
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Env-var opt-in
# ---------------------------------------------------------------------------

#: Environment variable that enables CUDA-graph capture. ``"1"`` / ``"true"``
#: / ``"yes"`` activates the cache; anything else (including unset) keeps the
#: legacy eager path byte-stable.
_CUDA_GRAPH_ENV_VAR: str = "ADAPTIVE_REFLOW_CUDA_GRAPH"

#: Truthy env-var values.
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def is_cuda_graph_capture_enabled() -> bool:
    """Return ``True`` iff the env-var opt-in is active.

    Read once at import time would force a process-wide decision; we read on
    every call so the harness scripts can flip the variable in-process and
    immediately observe the change. Cost is one ``os.environ.get`` per call.
    """
    raw = os.environ.get(_CUDA_GRAPH_ENV_VAR, "")
    return str(raw).strip().lower() in _TRUTHY


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _CacheKey:
    """Identity + shape key for one captured graph.

    ``model_id`` is the ``id(unet)`` Python object identity. Adapters that
    swap the UNet (e.g. warmup vs. eval) see different ``model_id`` values,
    so the cache treats them as distinct. ``chunk_size`` separates graphs by
    sub-batch so the inner batched-loop can replay each chunk size once
    after the first warmup iteration.
    """

    model_id: int
    chunk_size: int
    dtype: Any
    device: Any

    def __str__(self) -> str:  # pragma: no cover - debug only
        return (
            f"_CacheKey(model_id={self.model_id}, chunk_size={self.chunk_size}, "
            f"dtype={self.dtype}, device={self.device})"
        )


@dataclass
class _CachedGraph:
    """One captured graph plus its pre-allocated I/O buffers."""

    graph: Any  # torch.cuda.CUDAGraph
    static_input: Any  # torch.Tensor (chunk_size, 3, 32, 32)
    static_t: Any  # torch.Tensor (chunk_size,)
    static_output: Any  # torch.Tensor (chunk_size, 3, 32, 32)
    call_count: int = 0
    capture_failures: int = 0


@dataclass
class _CacheStats:
    """Counter snapshot for observability."""

    captures: int = 0
    replays: int = 0
    fallbacks: int = 0
    capture_failures: int = 0
    keys: int = 0


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class CudaGraphVelocityFieldCache:
    """Process-local cache of captured CUDA graphs.

    The cache maps ``(model_id, chunk_size, dtype, device)`` to a
    :class:`_CachedGraph`. The first call for a given key captures a new
    graph (side-stream warmup + ``torch.cuda.graph(g)`` block); subsequent
    calls copy the new ``x_t`` and ``t_t`` into the captured graph's static
    buffers, replay, and clone the static output back to the caller.

    Thread safety: a single :class:`threading.Lock` guards the
    ``cache`` dict mutation (capture is the only writer; replay is
    read-only on the dict and writes only to per-graph state). The
    module is single-process; cross-process callers need their own
    cache instance (the per-process CUDA context cannot share graphs
    across processes).
    """

    def __init__(self) -> None:
        self._cache: MutableMapping[_CacheKey, _CachedGraph] = {}
        self._lock = threading.Lock()
        self._stats = _CacheStats()

    @property
    def enabled(self) -> bool:
        """Return ``True`` iff capture is active (env-var opt-in)."""
        return is_cuda_graph_capture_enabled()

    def _get_or_capture(
        self,
        *,
        unet: Any,
        chunk_size: int,
        sample_x: Any,
        sample_t: Any,
    ) -> _CachedGraph | None:
        """Return the cached graph for ``unet + chunk_size`` (capture on miss).

        Returns ``None`` on capture failure so the caller falls back to
        eager mode. Increments :attr:`_stats` counters so the harness can
        report capture vs. replay vs. fallback ratios.
        """
        if not self.enabled:
            return None
        key = _CacheKey(
            model_id=id(unet),
            chunk_size=int(chunk_size),
            dtype=sample_x.dtype,
            device=sample_x.device,
        )
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached
            # Capture path. We do this OUTSIDE the lock would be unsafe
            # (two threads could race to capture the same key); inside the
            # lock it serialises the first capture per key, which is fine
            # because the capture itself takes ~ms while the replay is
            # ~µs.
            try:
                graph_obj = self._capture(
                    unet=unet,
                    chunk_size=int(chunk_size),
                    sample_x=sample_x,
                    sample_t=sample_t,
                )
            except Exception as exc:  # pragma: no cover - defensive
                self._stats.capture_failures += 1
                _LOGGER.warning(
                    "cuda_graph_capture_failed key=%s err=%s",
                    key,
                    type(exc).__name__,
                )
                return None
            self._cache[key] = graph_obj
            self._stats.captures += 1
            self._stats.keys = len(self._cache)
            return graph_obj

    def _capture(
        self,
        *,
        unet: Any,
        chunk_size: int,
        sample_x: Any,
        sample_t: Any,
    ) -> _CachedGraph:
        """Capture a single graph for ``unet`` on a side stream.

        Implementation follows the PyTorch CUDA-graph recipe:

        1. Allocate static input/output buffers on ``sample_x.device``.
        2. Warm up on a side stream so any lazy CUDA initialisation
           (e.g. cuDNN algorithm selection, autograd graph build) happens
           OUTSIDE the capture region.
        3. ``torch.cuda.synchronize()`` + ``torch.cuda.graph(g)``
           captures the forward sequence into ``g``.
        """
        import torch  # local import — torch is optional at the framework level

        static_input = torch.empty_like(sample_x)
        static_input.copy_(sample_x)
        static_t = torch.empty_like(sample_t)
        static_t.copy_(sample_t)
        # Capture-side warmup on a side stream. We do at least 2 warmup
        # iterations so cuDNN benchmark settles on a fixed algorithm
        # (the third iteration is inside the capture block; the first
        # two on the side stream).
        side_stream = torch.cuda.Stream(device=sample_x.device)
        side_stream.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(side_stream):
            for _ in range(2):
                _ = unet(static_input, static_t)
        torch.cuda.current_stream().wait_stream(side_stream)
        torch.cuda.synchronize()
        graph_obj = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph_obj, stream=side_stream):
            static_output = unet(static_input, static_t)
        # Detach the output tensor from autograd — captured graphs do
        # NOT support autograd by design (the captured kernel sequence
        # is baked into the graph binary; back-prop would require a
        # separate capture).
        return _CachedGraph(
            graph=graph_obj,
            static_input=static_input,
            static_t=static_t,
            static_output=static_output.detach(),
        )

    def replay(
        self,
        cached: _CachedGraph,
        *,
        x_t: Any,
        t_t: Any,
    ) -> Any:
        """Replay ``cached`` with new ``x_t`` / ``t_t`` and return the output clone.

        Cloning the static output is required because the captured graph
        writes to the SAME tensor address on every replay; without the
        clone, the caller's ``x_cur`` mutation in the Euler integrator
        would corrupt the next replay's output.
        """
        cached.static_input.copy_(x_t)
        cached.static_t.copy_(t_t)
        cached.graph.replay()
        cached.call_count += 1
        self._stats.replays += 1
        return cached.static_output.clone()

    def record_fallback(self) -> None:
        """Increment the fallback counter (callers that bypass the cache)."""
        self._stats.fallbacks += 1

    def stats(self) -> dict[str, int]:
        """Return a snapshot of the cache counters."""
        return {
            "captures": int(self._stats.captures),
            "replays": int(self._stats.replays),
            "fallbacks": int(self._stats.fallbacks),
            "capture_failures": int(self._stats.capture_failures),
            "keys": int(self._stats.keys),
        }

    def clear(self) -> None:
        """Drop all captured graphs (test isolation)."""
        with self._lock:
            self._cache.clear()
            self._stats = _CacheStats()


# ---------------------------------------------------------------------------
# Convenience accessors
# ---------------------------------------------------------------------------


#: Process-wide singleton (callers that don't have a cache handle handy).
_DEFAULT_CACHE = CudaGraphVelocityFieldCache()


def default_cache() -> CudaGraphVelocityFieldCache:
    """Return the process-wide singleton cache.

    The adapter layer can call this directly when it doesn't have its own
    cache handle; the singleton keeps the per-process graph table in one
    place so callers don't accumulate stale graphs across instances.
    """
    return _DEFAULT_CACHE


def captured_velocity_field(
    unet: Any,
    x_t: Any,
    t_t: Any,
    *,
    cache: CudaGraphVelocityFieldCache | None = None,
) -> Any | None:
    """Wrap ``unet(x_t, t_t)`` with the captured-graph cache.

    Returns the captured output clone on a cache hit / fresh capture.
    Returns ``None`` when the cache is disabled or capture failed —
    callers should treat ``None`` as "use the eager path".

    This function is a thin facade; the heavy lifting (capture,
    replay, copy) lives in :meth:`CudaGraphVelocityFieldCache.replay`
    so the adapter's call site stays short and the failure mode is
    obvious (``None`` returned -> eager fallthrough).
    """
    if not is_cuda_graph_capture_enabled():
        return None
    target = cache if cache is not None else _DEFAULT_CACHE
    chunk_size = int(x_t.shape[0])
    cached = target._get_or_capture(
        unet=unet,
        chunk_size=chunk_size,
        sample_x=x_t,
        sample_t=t_t,
    )
    if cached is None:
        target.record_fallback()
        return None
    return target.replay(cached, x_t=x_t, t_t=t_t)


__all__ = [
    "CudaGraphVelocityFieldCache",
    "captured_velocity_field",
    "default_cache",
    "is_cuda_graph_capture_enabled",
]

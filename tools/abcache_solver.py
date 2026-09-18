"""AB-Cache-equivalent solver for continuous flow matching (Wave 181 P1).

This module adapts the **Adams-Bashforth cached feature reuse**
principle from AB-Cache (Yu et al. 2024, ``arXiv:2504.10540``,
https://github.com/aSleepyTree/AB-Cache) to **continuous flow
matching** ODE solvers (LineageFlow protein gen, Kanzi RNA gen).

Original AB-Cache (continuous-time flow matching on image diffusion)
------------------------------------------------------------------

AB-Cache accelerates diffusion inference by reusing cached velocity
field outputs across consecutive denoising steps. The two-step
explicit Adams-Bashforth integrator uses the last two cached
velocity outputs (``f_n`` and ``f_{n-1}``) to extrapolate the next
state **without** calling the velocity field:

    ``x_{n+1} = x_n + dt * (2 * f_n - f_{n-1})``

(see ``/tmp/AB-Cache/flux_our.py:115-116``: ``prev_sample = sample +
(sigma_next - sigma) * (2 * self.f[0] - self.f[1])``). This is the
2-step explicit Adams-Bashforth formula, a higher-order alternative
to Euler that consumes the same ``dt`` interval but needs only one
prior cached value to skip the velocity-field call.

The decision rule (see ``/tmp/AB-Cache/pipeline_flux_our.py:928``) is
**periodic interval-based caching**:

    ``enable_cache = (5 <= i <= 49) and (i % 6 != 0)``

i.e. the first 5 steps always recompute (warmup — need 2 cached
values for AB), then every 6th step recomputes while the other 5
reuse the cache. Theoretical speedup = 6/2 = **3x** (recompute every
6th step + 5 cache-reuse steps + 2 cached values for the AB formula).

Adapted to continuous flow matching
------------------------------------

For continuous flow matching on the (L, K) state surface, the
analog of AB-Cache is a **periodic-2-step Adams-Bashforth Euler
mix**:

* Maintain a fixed-length queue of the last 2 velocity outputs.
* At each macro-step ``i = 0 .. N-1``:
  * If ``i < warmup_steps`` (default 2): always take a **recompute**
    Euler step ``x_next = x_cur + dt * v(x_cur, t_i)`` (1 NFE).
    Enqueue the velocity output to the queue.
  * Else if ``(i - warmup_steps) % recompute_interval == 0``: take
    a **recompute** Euler step (1 NFE, refreshes cache).
  * Else: take a **cache-reuse** Adams-Bashforth step
    ``x_next = x_cur + dt * (2 * v_n - v_{n-1})`` (0 NFE). The
    queue is NOT updated (it already holds ``v_n, v_{n-1}``).

Effective NFE per macro-step: between ``warmup_steps + 1`` (full
recompute, no cache-reuse at all) and ``nfe`` (no warmup, all
recompute — but that's the Euler baseline). With default
``warmup_steps=2, recompute_interval=6``:

    effective_nfe ≈ warmup_steps + ceil((N - warmup_steps) / recompute_interval)
                  = 2 + ceil(48 / 6)
                  = 10 NFE for NFE=50 (5x speedup over baseline).

Why this is the right "AB-Cache equivalent" for FlowA
------------------------------------------------------

* **Same conceptual primitive**: cache the velocity field outputs
  across consecutive macro-steps, reuse cached outputs when the
  step-to-step delta is small.
* **Same algorithmic primitive**: 2-step explicit Adams-Bashforth
  extrapolation ``x_next = x_cur + dt * (2*v_n - v_{n-1})``
  (matches ``flux_our.py:115-116`` line-for-line, modulo Flow
  Matching's ``(sigma_next - sigma)`` → our ``dt`` rename).
* **Training-free** (no checkpoint retraining; same LineageFlow ckpt;
  same Kanzi DAE).
* **Compatible with the R6 task**: outputs ``(L, K)`` per-position
  categorical on the same surface as FlowA's solver, so downstream
  ESMFold pLDDT eval can read the FASTA without modification.

Differences from AB-Cache paper
--------------------------------

* **Periodic-only decision rule**: the paper uses the same periodic
  decision rule (``if 5 <= i <= 49 and i % 6 != 0``), so our
  continuous-FM analog is structurally identical to the paper. We
  expose ``warmup_steps`` and ``recompute_interval`` as parameters
  so downstream Wave 181 P3 (aggregation) can sweep these as
  ablation knobs.
* **No classifier-free guidance**: the paper applies AB-Cache to
  CFG outputs (``noise_pred = neg + scale * (pos - neg)``); we skip
  the CFG path because FlowA's LineageFlow adapter is not CFG-based
  (continuous flow matching, no CFG in the R6 task).
* **No queue size 5 / 4-step AB variant**: the paper exposes
  ``maxlen=5`` to support up to 4-step Adams-Bashforth
  (``5*f[0] - 10*f[1] + 10*f[2] - 5*f[3] + f[4]``,
  ``flux_our.py:119``). We default to ``maxlen=2`` (2-step AB) per
  the paper's primary reported setting (line 116).

Public surface
--------------

* :class:`ABCacheSolverStats` — per-trajectory diagnostic stats.
* :func:`solve_ode_abcache` — one-shot wrapper that takes a
  ``velocity_field(x, t)`` callable and returns ``(trajectory,
  metadata)`` tuple.
* :func:`make_lineageflow_velocity_field` — adapter hookup (same
  surface as Wave 180's ``fastdllm_solver``).
* :func:`default_abcache_warmup_steps` — canonical warmup (=2,
  minimum needed for 2-step AB).
* :func:`default_abcache_recompute_interval` — canonical interval
  (=6, mirrors ``flux_our.py:928`` ``i % 6 != 0`` check).
"""
from __future__ import annotations

import dataclasses
import math
from collections import deque
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

# Local repo imports — kept minimal so the solver is independent of the
# adapter's heavyweight dependencies.
from adaptive_reflow.adapters.lineageflow import (  # type: ignore
    LINEAGEFLOW_CLAMP,
    LINEAGEFLOW_STATE_SHAPE,
    LINEAGEFLOW_T_END,
)

# Default AB-Cache hyperparameters — mirror the paper's reported
# ``warmup_steps=5, recompute_interval=6`` (``flux_our.py:928``
# ``if 5 <= i <= 49 and i % 6 != 0``). For continuous flow matching
# with only 2 cached values (2-step AB), the warmup needs at least 2
# recompute steps to seed the queue; we use ``warmup_steps=2`` as the
# minimum required by the algorithm. ``recompute_interval=6`` is the
# paper's reported value (1 recompute every 6 steps → 5/6 cache-reuse
# rate → ~3x speedup).
DEFAULT_ABCACHE_WARMUP_STEPS: int = 2
DEFAULT_ABCACHE_RECOMPUTE_INTERVAL: int = 6

# Queue length — 2 cached velocity outputs is sufficient for the
# 2-step Adams-Bashforth formula. The paper's ``FixedLengthQueue(5)``
# supports the 4-step variant too (line 119 ``5*f[0] - 10*f[1] +
# 10*f[2] - 5*f[3] + f[4]``); we expose this as a constant so future
# Wave 181 P3 ablation work can test ``queue_length=5``.
DEFAULT_ABCACHE_QUEUE_LENGTH: int = 2


@dataclasses.dataclass(frozen=True)
class ABCacheSolverStats:
    """Per-trajectory diagnostic stats for the AB-Cache-equivalent solver.

    Attributes
    ----------
    n_macro_steps: int
        Total macro-steps taken (== NFE budget).
    n_recompute_steps: int
        Number of Euler recompute steps actually evaluated
        (warmup + every ``recompute_interval``-th step).
    n_cache_reuse_steps: int
        Number of Adams-Bashforth cache-reuse steps (zero-NFE).
    effective_nfe: int
        Total NFE consumed: ``n_recompute_steps`` (cache-reuse is 0
        NFE). Equals ``n_macro_steps - n_cache_reuse_steps``.
    warmup_steps: int
        Warmup step count (first ``warmup_steps`` macro-steps always
        recompute).
    recompute_interval: int
        AB-Cache periodic recompute interval (every ``recompute_interval``
        steps after warmup, take a recompute step).
    cache_reuse_rate: float
        Fraction of macro-steps that used cache-reuse (between 0 and 1).
        ``n_cache_reuse_steps / n_macro_steps``.
    queue_length_final: int
        Queue length at the end of the trajectory (always equal to
        ``queue_length`` once warmed up).
    """

    n_macro_steps: int
    n_recompute_steps: int
    n_cache_reuse_steps: int
    effective_nfe: int
    warmup_steps: int
    recompute_interval: int
    cache_reuse_rate: float
    queue_length_final: int


# Type alias: velocity field is a callable ``(x, t) -> v(x, t)``.
VelocityField = Callable[[NDArray[np.float64], float], NDArray[np.float64]]


def solve_ode_abcache(
    *,
    velocity_field: VelocityField,
    x0: NDArray[np.float64],
    nfe: int,
    t_end: float = LINEAGEFLOW_T_END,
    warmup_steps: int = DEFAULT_ABCACHE_WARMUP_STEPS,
    recompute_interval: int = DEFAULT_ABCACHE_RECOMPUTE_INTERVAL,
    queue_length: int = DEFAULT_ABCACHE_QUEUE_LENGTH,
) -> tuple[NDArray[np.float64], ABCacheSolverStats]:
    """Run the AB-Cache-equivalent Adams-Bashforth cache-reuse ODE solver.

    Parameters
    ----------
    velocity_field:
        Callable ``(x, t) -> v(x, t)`` returning the velocity vector at
        state ``x`` and time ``t``. Must be deterministic for a fixed
        ``(x, t)``.
    x0:
        Initial state ``(L, K)`` (matches LineageFlow's per-position
        categorical surface).
    nfe:
        Macro-step budget. The solver runs ``nfe`` macro-steps total,
        but only ``warmup_steps + ceil((nfe - warmup_steps) /
        recompute_interval)`` consume an NFE — the rest are
        cache-reuse steps (zero NFE).
    t_end:
        Final integration time (default ``LINEAGEFLOW_T_END = 1.0``).
    warmup_steps:
        Number of warmup macro-steps at the start of the trajectory
        that always recompute (default 2, minimum needed to seed the
        queue for 2-step Adams-Bashforth). Must be >= ``queue_length
        - 1`` to seed the cache.
    recompute_interval:
        Number of macro-steps between recompute steps after warmup
        (default 6, mirrors ``flux_our.py:928`` ``i % 6 != 0``).
    queue_length:
        Number of cached velocity outputs to maintain (default 2, the
        2-step Adams-Bashforth requirement).

    Returns
    -------
    trajectory:
        ``(nfe+1, L, K)`` trajectory tensor (matches the Euler solver
        surface, so downstream callers don't need to special-case the
        AB-Cache path).
    stats:
        Per-trajectory :class:`ABCacheSolverStats` for the audit doc.
    """
    if int(nfe) <= 0:
        raise ValueError("nfe_must_be_positive")
    if int(warmup_steps) < 0:
        raise ValueError("warmup_steps_must_be_non_negative")
    if int(recompute_interval) <= 0:
        raise ValueError("recompute_interval_must_be_positive")
    if int(queue_length) < 2:
        raise ValueError(
            "queue_length_must_be_at_least_2_for_2-step_adams_bashforth"
        )
    if int(warmup_steps) < int(queue_length) - 1:
        raise ValueError(
            "warmup_steps_must_be_at_least_queue_length-1_to_seed_cache"
        )

    x_cur = np.asarray(x0, dtype=np.float64).reshape(LINEAGEFLOW_STATE_SHAPE).copy()
    traj = np.empty((int(nfe) + 1, *LINEAGEFLOW_STATE_SHAPE), dtype=np.float64)
    traj[0] = x_cur.copy()

    cache: deque = deque(maxlen=int(queue_length))
    n_recompute = 0
    n_cache_reuse = 0

    for i in range(1, int(nfe) + 1):
        t_i = (float(i) - 1.0) / float(nfe) * float(t_end)
        t_next = float(i) / float(nfe) * float(t_end)
        dt = t_next - t_i

        # AB-Cache decision rule (mirrors ``flux_our.py:928``):
        # * If ``i < warmup_steps``: always recompute (warmup).
        # * Else if ``(i - warmup_steps) % recompute_interval == 0``:
        #   recompute (refresh cache).
        # * Else: cache-reuse (Adams-Bashforth, no NFE).
        is_warmup = i <= int(warmup_steps)
        is_periodic_recompute = (not is_warmup) and (
            ((i - int(warmup_steps) - 1) % int(recompute_interval)) == 0
        )
        do_recompute = bool(is_warmup or is_periodic_recompute)

        if do_recompute:
            # Recompute path: take Euler step + update cache.
            v_at_x = velocity_field(x_cur, t_i)
            x_next = np.clip(x_cur + dt * v_at_x, 0.0, LINEAGEFLOW_CLAMP)
            x_next = x_next / np.maximum(x_next.sum(axis=-1, keepdims=True), 1e-30)
            cache.appendleft(v_at_x.copy())
            n_recompute += 1
        else:
            # Cache-reuse path: 2-step explicit Adams-Bashforth
            # ``x_next = x_cur + dt * (2 * v_n - v_{n-1})`` (mirrors
            # ``flux_our.py:115-116``: ``prev_sample = sample +
            # (sigma_next - sigma) * (2 * self.f[0] - self.f[1])``).
            assert len(cache) >= 2, (
                f"cache_must_have_at_least_2_entries_for_AB: "
                f"got {len(cache)} at step {i}"
            )
            v_n = cache[0]
            v_n_minus_1 = cache[1]
            ab_velocity = 2.0 * v_n - v_n_minus_1
            x_next = np.clip(x_cur + dt * ab_velocity, 0.0, LINEAGEFLOW_CLAMP)
            x_next = x_next / np.maximum(x_next.sum(axis=-1, keepdims=True), 1e-30)
            # Cache is NOT updated on cache-reuse steps (the AB
            # formula already uses the latest two cached values; the
            # actual v(x_cur, t_i) is unknown because we didn't
            # call velocity_field).
            n_cache_reuse += 1

        x_cur = x_next
        traj[i] = x_cur.copy()

    n_macro = int(nfe)
    stats = ABCacheSolverStats(
        n_macro_steps=n_macro,
        n_recompute_steps=int(n_recompute),
        n_cache_reuse_steps=int(n_cache_reuse),
        effective_nfe=int(n_recompute),
        warmup_steps=int(warmup_steps),
        recompute_interval=int(recompute_interval),
        cache_reuse_rate=float(n_cache_reuse) / float(max(n_macro, 1)),
        queue_length_final=int(len(cache)),
    )
    return traj, stats


def make_lineageflow_velocity_field(
    adapter: Any, *, family_id: str, seed: int
) -> tuple[VelocityField, Mapping[str, Any]]:
    """Build an AB-Cache-compatible velocity field from a LineageFlowAdapter.

    Returns a ``(velocity_field, conditioning)`` tuple where
    ``velocity_field(x, t) = adapter._velocity_field(x, t, conditioning=...,
    guidance_scale=...)`` — the same surface as
    :meth:`LineageFlowAdapter.solve_ode`'s inner loop, exposed for the
    AB-Cache-equivalent solver.
    """
    conditioning = adapter._resolve_conditioning(family_id=str(family_id), seed=int(seed))  # type: ignore[attr-defined]

    def velocity_field(x: NDArray[np.float64], t: float) -> NDArray[np.float64]:
        return adapter._velocity_field(  # type: ignore[attr-defined]
            x,
            t,
            conditioning=conditioning,
            guidance_scale=float(getattr(adapter, "_guidance_scale", 1.0)),
        )

    return velocity_field, conditioning

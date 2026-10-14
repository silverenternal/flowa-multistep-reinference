"""Generic Fast-DLLM / AB-Cache / LeDiFlow Euler-family solvers (GAP-32).

Cell-agnostic ports of the three LineageFlow-adapted external solvers used
by the R6 head-to-head:

* :mod:`tools.fastdllm_solver` — confidence-aware parallel-decoding
  (Wu et al. 2025, ``arXiv:2505.22618``), continuous-FM analog.
* :mod:`tools.abcache_solver` — 2-step explicit Adams-Bashforth cache
  reuse (Yu et al. 2024, ``arXiv:2504.10540``).
* :mod:`tools.lediflow_solver` — learned-prior-shifted Euler
  (Zwick et al. 2025, ``arXiv:2505.20723``).

The originals are hard-wired to LineageFlow's ``(L, K)`` per-position
categorical surface: every step clips to ``[0, LINEAGEFLOW_CLAMP]`` and
re-normalises the per-position simplex, and every trajectory is shaped by
:data:`adaptive_reflow.adapters.lineageflow.LINEAGEFLOW_STATE_SHAPE`.

GAP-32 needs the *same three methods* on two image cells (R5c MNIST FM,
784-dim pixels in ``[-1, 1]``; R5b CIFAR-10 RF, ``3 x 32 x 32`` in
``[-3, 3]``) where neither the simplex re-normalisation nor the
LineageFlow state shape applies. Rather than fork the algorithms, this
module replaces the two LineageFlow-specific operations with one
caller-supplied ``project`` callable (the cell's domain clamp) and
operates on a **leading batch axis** so a whole sample population
advances in lockstep.

The algorithmic content is byte-for-byte the originals':

* the same macro-step grid ``t_i = (i-1)/nfe * t_end``,
  ``dt = t_end / nfe``;
* the same Fast-DLLM confidence rule
  (``confidence = 1 - relative_l2(euler, midpoint)``; skip the next
  verifier when ``confidence > threshold``);
* the same AB-Cache decision rule
  (``i <= warmup`` recompute; else ``(i - warmup - 1) % interval == 0``
  recompute; else ``x + dt*(2*v_n - v_{n-1})`` cache-reuse);
* the same LeDiFlow prior shift
  (``x0_learned = project(x0 + prior_scale * unit_direction(prior_seed))``,
  blended by ``prior_alpha``).

Only the state shape and the projection differ.

Wave/GAP provenance: GAP-32-SOTA-HEADTOHEAD; audit
``docs/audit/gap32-headtohead.md``.
"""
from __future__ import annotations

import math
from collections import deque
from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Public type aliases + canonical constants (mirror the originals verbatim)
# ---------------------------------------------------------------------------

#: ``velocity_field(x, t)`` where ``x`` carries a leading batch axis
#: ``(B, *state_shape)`` and the return matches.
VelocityField = Callable[[NDArray[np.float64], float], NDArray[np.float64]]

#: Domain projection applied after every integrator step (e.g.
#: ``lambda x: np.clip(x, -1.0, 1.0)`` for MNIST). Replaces the
#: LineageFlow clip-to-``[0, CLAMP]`` + per-position simplex renormalisation.
Project = Callable[[NDArray[np.float64]], NDArray[np.float64]]

#: Default Fast-DLLM confidence threshold (mirrors
#: ``tools.fastdllm_solver.DEFAULT_FASTDLLM_CONFIDENCE_THRESHOLD``).
DEFAULT_FASTDLLM_CONFIDENCE_THRESHOLD: float = 0.5

#: Default AB-Cache warmup / recompute interval / queue length (mirrors
#: ``tools.abcache_solver`` — the ``flux_our.py`` ``i % 6 != 0`` rule).
DEFAULT_ABCACHE_WARMUP_STEPS: int = 2
DEFAULT_ABCACHE_RECOMPUTE_INTERVAL: int = 6
DEFAULT_ABCACHE_QUEUE_LENGTH: int = 2

#: Default LeDiFlow prior-shift parameters (mirror
#: ``tools.lediflow_solver``).
DEFAULT_LEDIFLOW_PRIOR_ALPHA: float = 0.5
DEFAULT_LEDIFLOW_PRIOR_SEED: int = 0x4C44
DEFAULT_LEDIFLOW_PRIOR_SCALE: float = 0.4


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _as_batched(x0: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return ``x0`` as a float64 array with a leading batch axis."""
    arr = np.asarray(x0, dtype=np.float64)
    if arr.ndim == 0:
        raise ValueError("x0_must_have_at_least_one_axis")
    return arr


def _relative_l2_per_sample(
    a: NDArray[np.float64], b: NDArray[np.float64], eps: float = 1e-12
) -> NDArray[np.float64]:
    """Per-sample ``||a - b||_2 / (||a||_2 + eps)`` over the flattened tail.

    The batched analog of
    :func:`tools.fastdllm_solver.relative_l2_distance` — one value per
    batch element.
    """
    a_flat = np.asarray(a, dtype=np.float64).reshape(a.shape[0], -1)
    b_flat = np.asarray(b, dtype=np.float64).reshape(b.shape[0], -1)
    diff = a_flat - b_flat
    num = np.linalg.norm(diff, axis=1)
    den = np.linalg.norm(a_flat, axis=1) + eps
    return num / den


def _broadcast_mask(
    mask: NDArray[np.bool_], ref: NDArray[np.float64]
) -> NDArray[np.bool_]:
    """Reshape a ``(B,)`` boolean mask for ``np.where`` against ``ref``."""
    return mask.reshape((mask.shape[0],) + (1,) * (ref.ndim - 1))


# ---------------------------------------------------------------------------
# Vanilla Euler baseline (the reference arm all external methods beat)
# ---------------------------------------------------------------------------


def vanilla_euler(
    *,
    velocity_field: VelocityField,
    x0: NDArray[np.float64],
    nfe: int,
    t_end: float = 1.0,
    project: Project,
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    """Run the plain Euler baseline for ``nfe`` macro-steps.

    Mirrors the ``vanilla`` arm of the R6 head-to-head (1 velocity
    evaluation per step). Returns ``(endpoints, stats)`` with
    ``endpoints`` shaped like ``x0``.
    """
    if int(nfe) <= 0:
        raise ValueError("nfe_must_be_positive")
    x = project(_as_batched(x0).copy())
    dt = float(t_end) / float(nfe)
    for i in range(1, int(nfe) + 1):
        t_i = (float(i) - 1.0) / float(nfe) * float(t_end)
        x = project(x + dt * velocity_field(x, t_i))
    return x, {"n_macro_steps": int(nfe), "effective_nfe": int(nfe)}


# ---------------------------------------------------------------------------
# Fast-DLLM-equivalent solver
# ---------------------------------------------------------------------------


def solve_ode_fastdllm(
    *,
    velocity_field: VelocityField,
    x0: NDArray[np.float64],
    nfe: int,
    t_end: float = 1.0,
    confidence_threshold: float = DEFAULT_FASTDLLM_CONFIDENCE_THRESHOLD,
    project: Project,
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    """Batched Fast-DLLM-equivalent confidence-aware ODE solver.

    See :func:`tools.fastdllm_solver.solve_ode_fastdllm` for the
    per-record algorithm; this batched port applies the same rule to
    every batch element (each element tracks its own skip state).
    """
    if int(nfe) <= 0:
        raise ValueError("nfe_must_be_positive")
    if not (0.0 <= float(confidence_threshold) <= 1.0):
        raise ValueError(
            f"confidence_threshold_must_be_in_[0,1]: got {confidence_threshold!r}"
        )

    x = project(_as_batched(x0).copy())
    n_batch = int(x.shape[0])
    n_verifier = 0
    n_skip = 0
    confidence_sum = 0.0
    skip_next = np.zeros(n_batch, dtype=bool)

    for i in range(1, int(nfe) + 1):
        t_i = (float(i) - 1.0) / float(nfe) * float(t_end)
        t_next = float(i) / float(nfe) * float(t_end)
        t_half = 0.5 * (t_i + t_next)
        dt = t_next - t_i

        # Predictor Euler step (1 NFE). The verifier's first half reuses
        # this same evaluation (the original calls it twice — identical).
        v_at_x = velocity_field(x, t_i)
        x_pred = project(x + dt * v_at_x)

        do_verifier = ~skip_next
        x_mid = project(x + 0.5 * dt * v_at_x)
        v_half_2 = velocity_field(x_mid, t_half)
        x_verify = project(x_mid + 0.5 * dt * v_half_2)

        rel_dist = _relative_l2_per_sample(x_pred, x_verify)
        confidence = np.maximum(0.0, 1.0 - rel_dist)

        # Where a verifier ran, adopt the (more accurate) verifier result
        # and set the next skip decision; elsewhere keep the predictor.
        mask = _broadcast_mask(do_verifier, x)
        x = np.where(mask, x_verify, x_pred)
        skip_next = np.where(do_verifier, confidence > float(confidence_threshold), False)

        n_verifier += int(do_verifier.sum())
        n_skip += int((do_verifier & (confidence > float(confidence_threshold))).sum())
        confidence_sum += float(confidence[do_verifier].sum())

    # ``n_verifier`` / ``n_skip`` are batch totals; the per-sample
    # ``effective_nfe`` (matching the R6 single-record semantics) divides by
    # the batch size. The batch totals are retained for transparency.
    n_verifier_per_sample = int(round(float(n_verifier) / max(n_batch, 1)))
    stats: dict[str, Any] = {
        "n_macro_steps": int(nfe),
        "n_verifier_steps": int(n_verifier),
        "n_verifier_steps_per_sample": n_verifier_per_sample,
        "n_skip_steps": int(n_skip),
        "effective_nfe": int(nfe) + n_verifier_per_sample,
        "mean_confidence": float(confidence_sum / max(n_verifier, 1)),
        "threshold": float(confidence_threshold),
        "n_batch": n_batch,
    }
    return x, stats


# ---------------------------------------------------------------------------
# AB-Cache-equivalent solver
# ---------------------------------------------------------------------------


def solve_ode_abcache(
    *,
    velocity_field: VelocityField,
    x0: NDArray[np.float64],
    nfe: int,
    t_end: float = 1.0,
    warmup_steps: int = DEFAULT_ABCACHE_WARMUP_STEPS,
    recompute_interval: int = DEFAULT_ABCACHE_RECOMPUTE_INTERVAL,
    queue_length: int = DEFAULT_ABCACHE_QUEUE_LENGTH,
    project: Project,
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    """Batched AB-Cache-equivalent Adams-Bashforth cache-reuse solver.

    The recompute schedule is deterministic in the step index, so it is
    shared across the batch; only the cached velocity tensors carry the
    leading batch axis.
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

    x = project(_as_batched(x0).copy())
    n_batch = int(x.shape[0])
    cache: deque = deque(maxlen=int(queue_length))
    n_recompute = 0
    n_cache_reuse = 0

    for i in range(1, int(nfe) + 1):
        t_i = (float(i) - 1.0) / float(nfe) * float(t_end)
        t_next = float(i) / float(nfe) * float(t_end)
        dt = t_next - t_i

        is_warmup = i <= int(warmup_steps)
        is_periodic_recompute = (not is_warmup) and (
            ((i - int(warmup_steps) - 1) % int(recompute_interval)) == 0
        )
        do_recompute = bool(is_warmup or is_periodic_recompute)

        if do_recompute:
            v_at_x = velocity_field(x, t_i)
            x = project(x + dt * v_at_x)
            cache.appendleft(v_at_x.copy())
            n_recompute += 1
        else:
            assert len(cache) >= 2, (
                f"cache_must_have_at_least_2_entries_for_AB: "
                f"got {len(cache)} at step {i}"
            )
            ab_velocity = 2.0 * cache[0] - cache[1]
            x = project(x + dt * ab_velocity)
            n_cache_reuse += 1

    stats: dict[str, Any] = {
        "n_macro_steps": int(nfe),
        "n_recompute_steps": int(n_recompute),
        "n_cache_reuse_steps": int(n_cache_reuse),
        "effective_nfe": int(n_recompute),
        "warmup_steps": int(warmup_steps),
        "recompute_interval": int(recompute_interval),
        "cache_reuse_rate": float(n_cache_reuse) / float(max(int(nfe), 1)),
        "queue_length_final": int(len(cache)),
        "n_batch": n_batch,
    }
    return x, stats


# ---------------------------------------------------------------------------
# LeDiFlow-equivalent solver
# ---------------------------------------------------------------------------


def solve_ode_lediflow(
    *,
    velocity_field: VelocityField,
    x0: NDArray[np.float64],
    nfe: int,
    t_end: float = 1.0,
    prior_alpha: float = DEFAULT_LEDIFLOW_PRIOR_ALPHA,
    prior_seed: int = DEFAULT_LEDIFLOW_PRIOR_SEED,
    prior_scale: float = DEFAULT_LEDIFLOW_PRIOR_SCALE,
    project: Project,
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    """Batched LeDiFlow-equivalent prior-shifted Euler solver.

    Mirrors :func:`tools.lediflow_solver.solve_ode_lediflow` and
    :func:`tools.lediflow_solver.compute_learned_prior`: a single
    deterministic unit direction (seeded by ``prior_seed``) is added to
    the Gaussian ``x0`` and blended by ``prior_alpha`` before a stock
    Euler solve. The direction is shared across the batch (the original
    seeds one direction per arm).
    """
    if int(nfe) <= 0:
        raise ValueError("nfe_must_be_positive")
    if not (0.0 <= float(prior_alpha) <= 1.0):
        raise ValueError(f"prior_alpha_must_be_in_[0,1]: got {prior_alpha!r}")
    if float(prior_scale) < 0.0:
        raise ValueError(f"prior_scale_must_be_non_negative: got {prior_scale!r}")

    x = project(_as_batched(x0).copy())
    n_batch = int(x.shape[0])
    state_shape = tuple(int(s) for s in x.shape[1:])

    rng = np.random.default_rng(int(prior_seed))
    direction = rng.standard_normal(state_shape).astype(np.float64)
    direction = direction / max(float(np.linalg.norm(direction)), 1e-30)
    direction = direction * float(prior_scale)

    x0_learned = project(x + direction)
    prior_shift_amount = float(
        np.linalg.norm((x0_learned - x).reshape(n_batch, -1), axis=1).mean()
    )
    x = project(
        (1.0 - float(prior_alpha)) * x + float(prior_alpha) * x0_learned
    )

    dt = float(t_end) / float(nfe)
    for i in range(1, int(nfe) + 1):
        t_i = (float(i) - 1.0) / float(nfe) * float(t_end)
        x = project(x + dt * velocity_field(x, t_i))

    stats: dict[str, Any] = {
        "n_macro_steps": int(nfe),
        "effective_nfe": int(nfe),
        "prior_alpha": float(prior_alpha),
        "prior_shift_amount": float(prior_shift_amount),
        "prior_seed": int(prior_seed),
        "prior_scale": float(prior_scale),
        "n_batch": n_batch,
    }
    return x, stats


#: Registry the driver iterates over (``arm_name -> (solver, needs_stats)``).
EXTERNAL_ARMS: tuple[str, ...] = ("vanilla", "fastdllm", "abcache", "lediflow")


def run_external_arm(
    *,
    arm: str,
    velocity_field: VelocityField,
    x0: NDArray[np.float64],
    nfe: int,
    t_end: float,
    project: Project,
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    """Dispatch ``arm`` to the matching generic solver."""
    if arm == "vanilla":
        return vanilla_euler(
            velocity_field=velocity_field, x0=x0, nfe=nfe, t_end=t_end, project=project
        )
    if arm == "fastdllm":
        return solve_ode_fastdllm(
            velocity_field=velocity_field, x0=x0, nfe=nfe, t_end=t_end, project=project
        )
    if arm == "abcache":
        return solve_ode_abcache(
            velocity_field=velocity_field, x0=x0, nfe=nfe, t_end=t_end, project=project
        )
    if arm == "lediflow":
        return solve_ode_lediflow(
            velocity_field=velocity_field, x0=x0, nfe=nfe, t_end=t_end, project=project
        )
    raise ValueError(f"unknown_external_arm:{arm}")


def default_confidence_threshold() -> float:
    """Return the canonical Fast-DLLM confidence threshold."""
    return float(DEFAULT_FASTDLLM_CONFIDENCE_THRESHOLD)


__all__: list[str] = [
    "DEFAULT_ABCACHE_QUEUE_LENGTH",
    "DEFAULT_ABCACHE_RECOMPUTE_INTERVAL",
    "DEFAULT_ABCACHE_WARMUP_STEPS",
    "DEFAULT_FASTDLLM_CONFIDENCE_THRESHOLD",
    "DEFAULT_LEDIFLOW_PRIOR_ALPHA",
    "DEFAULT_LEDIFLOW_PRIOR_SCALE",
    "DEFAULT_LEDIFLOW_PRIOR_SEED",
    "EXTERNAL_ARMS",
    "Project",
    "VelocityField",
    "default_confidence_threshold",
    "run_external_arm",
    "solve_ode_abcache",
    "solve_ode_fastdllm",
    "solve_ode_lediflow",
    "vanilla_euler",
]

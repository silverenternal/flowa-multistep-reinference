"""Bounded-Lipschitz convergence diagnostic for the selection ratio.

:class:`adaptive_reflow.eval.posterior_selection_evaluator.EvidenceScaleGapMetric`
reports a per-round ``selection_ratio = sheet / (sheet + cell)`` whose
paper-predicted behaviour (Theorem 1) is monotone convergence to ``1`` as
the implicit noise scale ``eps -> 0``. Until now the framework only
recorded the *level* of that ratio; nothing checked the *shape* of the
trajectory, so a run that oscillated its way to a high terminal value was
indistinguishable from one that converged smoothly.

This module adds the missing diagnostic. Two quantities are computed
directly from the per-round ratio series:

``modulus``
    The discrete Lipschitz modulus ``max_k |r_{k+1} - r_k| / du``, with
    ``du = 1 / (L - 1)`` the schedule's normalised round spacing. This is
    the smallest ``L`` for which the trajectory is ``L``-Lipschitz as a
    function of normalised progress ``u in [0, 1]``.

``tail_modulus``
    The same modulus restricted to the trailing ``tail_fraction`` of the
    cycle. Theorem 1's convergence claim is *asymptotic*, so the tail is
    where the rate has to hold; a large modulus early in the cycle is the
    schedule doing its job, whereas a large modulus late is
    non-convergence.

The convergence criterion is the standard Monte-Carlo rate: with ``N``
endpoints per round the ratio is estimated to ``O(1 / sqrt(N))``, so a
*converged* trajectory's tail must not move by more than that estimation
noise. Concretely the diagnostic checks

    tail_modulus * du <= constant / sqrt(N)

i.e. consecutive tail rounds differ by no more than the sampling error.

Also provided is :func:`bounded_lipschitz_distance`, the exact
dual-bounded-Lipschitz distance between two 1-D empirical measures,
computed by sorting:

    d_BL(p, q) = sup { |E_p f - E_q f| : ||f||_inf <= 1, Lip(f) <= 1 }

which in one dimension equals ``min(W1(p, q), TV-truncated mass)`` and is
evaluated here as ``mean_i min(|x_(i) - y_(i)|, 2)`` over matched order
statistics — the truncation at ``2`` being exactly the ``||f||_inf <= 1``
constraint. It gives a bounded (hence always finite) convergence measure
between the round's endpoint population and the reference, where an
unbounded ``W1`` could be dominated by a single outlier.

Everything here is pure and additive: no existing evaluator changes.

Quantitative target
-------------------

For a converged run at ``N = 128`` endpoints per round the tail
Lipschitz increment satisfies ``tail_modulus * du <= 1 / sqrt(128)``
(``≈ 0.088``); an oscillating trajectory of the same terminal level is
rejected. Asserted in ``tests/test_eval/test_lipschitz_diagnostic.py``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "DEFAULT_RATE_CONSTANT",
    "DEFAULT_TAIL_FRACTION",
    "LipschitzConvergenceReport",
    "bounded_lipschitz_distance",
    "evaluate_lipschitz_convergence",
    "lipschitz_modulus",
]


DEFAULT_TAIL_FRACTION: float = 0.5
"""Fraction of the cycle treated as the asymptotic tail."""

DEFAULT_RATE_CONSTANT: float = 1.0
"""Constant ``c`` in the ``c / sqrt(N)`` convergence-rate bound."""


def _as_series(values: Sequence[float] | NDArray[np.float64]) -> NDArray[np.float64]:
    """Coerce a per-round metric series to a finite 1-D float64 array."""
    arr = np.asarray(values, dtype=np.float64).ravel()
    if arr.size == 0:
        raise ValueError("series must be non-empty")
    if not bool(np.all(np.isfinite(arr))):
        raise ValueError("series must be finite")
    return np.ascontiguousarray(arr, dtype=np.float64)


def lipschitz_modulus(
    series: Sequence[float] | NDArray[np.float64],
    *,
    spacing: float | None = None,
) -> float:
    """Return the discrete Lipschitz modulus of a per-round series.

    ``max_k |s_{k+1} - s_k| / spacing``. When ``spacing`` is ``None`` it
    defaults to the schedule's normalised round spacing
    ``1 / (len(series) - 1)``, so the modulus is expressed per unit of
    normalised progress ``u`` and is therefore comparable across cycles
    of different lengths — which is the whole point of reporting a
    modulus rather than a raw jump.

    A single-element series has no increments and returns ``0.0``.
    """
    arr = _as_series(series)
    if arr.size < 2:
        return 0.0
    if spacing is None:
        du = 1.0 / float(arr.size - 1)
    else:
        if isinstance(spacing, bool) or not isinstance(spacing, (int, float)):
            raise ValueError(f"spacing must be a real number, got {spacing!r}")
        du = float(spacing)
        if not math.isfinite(du) or du <= 0.0:
            raise ValueError(f"spacing must be finite and > 0, got {spacing!r}")
    return float(np.max(np.abs(np.diff(arr))) / du)


@dataclass(frozen=True)
class LipschitzConvergenceReport:
    """Result of :func:`evaluate_lipschitz_convergence`.

    Attributes
    ----------
    modulus:
        Lipschitz modulus over the whole trajectory.
    tail_modulus:
        Lipschitz modulus over the trailing ``tail_fraction``.
    tail_increment:
        ``tail_modulus * spacing`` — the largest *raw* round-to-round
        move in the tail, directly comparable to the sampling error.
    rate_bound:
        ``constant / sqrt(n_samples)`` — the Monte-Carlo noise floor the
        tail increment must sit under.
    within_rate:
        ``tail_increment <= rate_bound``. The headline verdict.
    terminal_value:
        Last value of the series.
    monotone_tail:
        Whether the tail is non-decreasing (Theorem 1 predicts monotone
        approach to ``1``). Reported, not required, because a converged
        trajectory may jitter inside the noise floor.
    n_rounds / n_samples / tail_fraction / constant:
        Echo of the inputs, so a report is self-describing in a ledger
        row.
    """

    modulus: float
    tail_modulus: float
    tail_increment: float
    rate_bound: float
    within_rate: bool
    terminal_value: float
    monotone_tail: bool
    n_rounds: int
    n_samples: int
    tail_fraction: float
    constant: float

    def as_metrics(self) -> dict[str, float]:
        """Return the numeric fields as a flat metric dict.

        Shaped for direct insertion into
        ``BatchedTrajectoryResult.per_round_metric``-style payloads and
        hash-chained ledger rows (booleans are widened to ``0.0`` /
        ``1.0`` so the dict stays homogeneously numeric).
        """
        return {
            "lipschitz_modulus": float(self.modulus),
            "lipschitz_tail_modulus": float(self.tail_modulus),
            "lipschitz_tail_increment": float(self.tail_increment),
            "lipschitz_rate_bound": float(self.rate_bound),
            "lipschitz_within_rate": 1.0 if self.within_rate else 0.0,
            "lipschitz_terminal_value": float(self.terminal_value),
            "lipschitz_monotone_tail": 1.0 if self.monotone_tail else 0.0,
        }


def evaluate_lipschitz_convergence(
    series: Sequence[float] | NDArray[np.float64],
    *,
    n_samples: int,
    tail_fraction: float = DEFAULT_TAIL_FRACTION,
    constant: float = DEFAULT_RATE_CONSTANT,
) -> LipschitzConvergenceReport:
    """Assess whether a per-round ratio series converges at the MC rate.

    :param series: per-round ``selection_ratio`` (or any other bounded
        per-round metric) in cycle order.
    :param n_samples: endpoints per round backing each entry of
        ``series``. Sets the ``constant / sqrt(n_samples)`` noise floor.
    :param tail_fraction: fraction of the cycle treated as the
        asymptotic tail, in ``(0, 1]``.
    :param constant: multiplier on the ``1 / sqrt(N)`` rate.
    :raises ValueError: on empty / non-finite series or bad parameters.
    """
    arr = _as_series(series)
    if isinstance(n_samples, bool) or not isinstance(n_samples, int):
        raise ValueError(f"n_samples must be int, got {n_samples!r}")
    if int(n_samples) < 1:
        raise ValueError(f"n_samples must be >= 1, got {n_samples!r}")
    if isinstance(tail_fraction, bool) or not isinstance(tail_fraction, (int, float)):
        raise ValueError(f"tail_fraction must be a real number, got {tail_fraction!r}")
    if not (0.0 < float(tail_fraction) <= 1.0):
        raise ValueError(f"tail_fraction must be in (0, 1], got {tail_fraction!r}")
    if isinstance(constant, bool) or not isinstance(constant, (int, float)):
        raise ValueError(f"constant must be a real number, got {constant!r}")
    if not math.isfinite(float(constant)) or float(constant) <= 0.0:
        raise ValueError(f"constant must be finite and > 0, got {constant!r}")

    n_rounds = int(arr.size)
    spacing = 1.0 / float(n_rounds - 1) if n_rounds > 1 else 1.0
    modulus = lipschitz_modulus(arr, spacing=spacing)

    # The tail always keeps at least two points so an increment exists.
    tail_len = max(2, int(math.ceil(float(tail_fraction) * float(n_rounds))))
    tail_len = min(tail_len, n_rounds)
    tail = arr[n_rounds - tail_len :]
    tail_modulus = lipschitz_modulus(tail, spacing=spacing) if tail.size > 1 else 0.0
    tail_increment = float(tail_modulus * spacing)
    rate_bound = float(float(constant) / math.sqrt(float(n_samples)))
    monotone_tail = bool(tail.size < 2 or bool(np.all(np.diff(tail) >= -1e-12)))

    return LipschitzConvergenceReport(
        modulus=float(modulus),
        tail_modulus=float(tail_modulus),
        tail_increment=tail_increment,
        rate_bound=rate_bound,
        within_rate=bool(tail_increment <= rate_bound),
        terminal_value=float(arr[-1]),
        monotone_tail=monotone_tail,
        n_rounds=n_rounds,
        n_samples=int(n_samples),
        tail_fraction=float(tail_fraction),
        constant=float(constant),
    )


def bounded_lipschitz_distance(
    left: Sequence[float] | NDArray[np.float64],
    right: Sequence[float] | NDArray[np.float64],
    *,
    bound: float = 2.0,
) -> float:
    """Return the dual bounded-Lipschitz distance between two 1-D samples.

    The bounded-Lipschitz (Fortet-Mourier) distance is

        d_BL(p, q) = sup { |E_p f - E_q f| : ||f||_inf <= B/2, Lip(f) <= 1 }

    In one dimension the unbounded case (``B = inf``) is exactly ``W1``,
    computable by matching order statistics. The ``||f||_inf`` constraint
    caps the contribution of any single matched pair at ``B``, so the
    bounded version is the truncated mean

        d_BL = mean_i min( |x_(i) - y_(i)|, B )

    over the two samples' quantile-matched order statistics (resampled
    to a common grid when the sizes differ).

    The truncation is what makes this useful as a *convergence*
    diagnostic: an unbounded ``W1`` between a round's endpoints and the
    reference can be dominated by one escaped outlier, which reads as
    "not converged" even when the bulk has settled. ``d_BL`` metrises
    weak convergence, so it goes to zero exactly when the distributions
    do — outliers included, but bounded in their influence.

    :param left: 1-D sample (flattened if higher-dimensional).
    :param right: 1-D sample.
    :param bound: the ``B`` truncation. Must be finite and ``> 0``.
    """
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        raise ValueError(f"bound must be a real number, got {bound!r}")
    b = float(bound)
    if not math.isfinite(b) or b <= 0.0:
        raise ValueError(f"bound must be finite and > 0, got {bound!r}")

    x = np.sort(_as_series(left))
    y = np.sort(_as_series(right))
    n = max(int(x.size), int(y.size))
    grid = (np.arange(n, dtype=np.float64) + 0.5) / float(n)
    qx = x[np.clip((grid * float(x.size)).astype(np.int64), 0, x.size - 1)]
    qy = y[np.clip((grid * float(y.size)).astype(np.int64), 0, y.size - 1)]
    return float(np.minimum(np.abs(qx - qy), b).mean())

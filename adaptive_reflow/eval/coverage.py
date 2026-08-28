"""Weighted Voronoi coverage + bootstrapped energy distance (P1 coverage metrics).

Two framework-INTERNAL metric uplifts over
:mod:`adaptive_reflow.eval.twodim_fm_evaluator`:

1. **Weighted coverage.** The existing
   :func:`~adaptive_reflow.eval.twodim_fm_evaluator.coverage_score` is
   *binary per Voronoi cell*: a cell counts as covered as soon as a
   single grid point inside it sits within the coverage radius of a
   sample. On a sparse population that just barely grazes every mode the
   metric saturates at ``1.0`` and stops discriminating — exactly the
   regime the framework cares about, because a schedule that touches all
   modes thinly and one that fills them are scored identically.
   :func:`weighted_coverage_score` replaces the per-cell indicator with
   the per-cell *covered area fraction*, which keeps discriminating all
   the way to saturation.

2. **Energy distance with a bootstrap CI.** The existing
   :func:`~adaptive_reflow.eval.twodim_fm_evaluator.energy_distance`
   returns a bare point estimate, so a caller cannot tell a real
   round-to-round movement from sampling noise.
   :func:`energy_distance_with_ci` adds a deterministic percentile
   bootstrap.

Both functions are standalone and additive — no existing evaluator call
site changes. This module is deliberately independent of
``twodim_fm_evaluator`` (which is excluded from ``mypy --strict``) so the
new metrics are fully type-checked.

Quantitative targets
--------------------

* **Weighted coverage discrimination**: on a population that is sparse
  but touches every mode, binary coverage saturates
  (``coverage_score == 1.0`` for both a sparse and a dense population)
  while ``weighted_coverage_score`` separates them by ``>= 0.2``
  absolute — i.e. it still has resolution where the binary metric has
  none.
* **Energy-distance CI**: at ``n = 256`` samples with ``1000``
  resamples, the 95 % CI width on the *distance* scale
  (:attr:`EnergyDistanceEstimate.relative_width_distance`) is
  ``<= 20 %`` of the point estimate for a separation of ``>= 1.5``
  standard deviations. Stating the target on the distance scale rather
  than on the squared ``E^2`` matters: ``E^2`` carries twice the
  relative dispersion, and is not comparable with the W2 families.

Both are asserted in ``tests/test_eval/test_coverage_metrics.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "DEFAULT_COVERAGE_RADIUS",
    "EnergyDistanceEstimate",
    "energy_distance_point",
    "energy_distance_with_ci",
    "weighted_coverage_score",
]


DEFAULT_COVERAGE_RADIUS: float = 0.25
"""Default coverage radius.

Mirrors
:data:`adaptive_reflow.eval.twodim_fm_evaluator.TWODIM_FM_COVERAGE_RADIUS`
so the weighted metric is directly comparable to the binary one on the
same grid. Passed explicitly by the evaluator wiring; the default only
matters for ad-hoc calls.
"""


def _as_points(values: object, *, name: str) -> NDArray[np.float64]:
    """Coerce ``values`` to a finite ``(n, d)`` float64 matrix."""
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 2-D (n, d); got shape {arr.shape!r}")
    if arr.shape[1] < 1:
        raise ValueError(f"{name} must have >= 1 feature; got shape {arr.shape!r}")
    if arr.size and not bool(np.all(np.isfinite(arr))):
        raise ValueError(f"{name} must be finite")
    return np.ascontiguousarray(arr, dtype=np.float64)


# ---------------------------------------------------------------------------
# Weighted Voronoi coverage
# ---------------------------------------------------------------------------


def weighted_coverage_score(
    samples: NDArray[np.float64],
    grid: NDArray[np.float64],
    mode_centers: NDArray[np.float64],
    *,
    radius: float = DEFAULT_COVERAGE_RADIUS,
) -> float:
    """Return the area-weighted Voronoi coverage in ``[0, 1]``.

    The grid is partitioned into one Voronoi cell per ``mode_center`` by
    the nearest-centre rule, exactly as the binary metric does. Instead
    of asking "did *any* grid point in this cell come within ``radius``
    of a sample?", the weighted metric asks "*what fraction* of this
    cell's grid points did?", then averages those fractions uniformly
    over the cells:

        coverage_weighted = (1/M) * sum_j  |{g in cell_j : d(g, X) <= r}|
                                          / |{g in cell_j}|

    Averaging *per cell* rather than over all grid points keeps every
    mode equally weighted regardless of how much grid area its Voronoi
    cell happens to occupy — otherwise a target with one geometrically
    large cell would let a generator ignore the small modes for free.

    Empty cells (no grid point closest to that centre) contribute ``0``,
    which is the fail-closed reading: a mode the grid cannot even
    resolve has certainly not been demonstrated to be covered.

    :param samples: ``(n, d)`` generated endpoints.
    :param grid: ``(g, d)`` evaluation grid (see
        :func:`~adaptive_reflow.eval.twodim_fm_evaluator.voronoi_grid`).
    :param mode_centers: ``(M, d)`` canonical mode centres.
    :param radius: coverage radius; a grid point counts as covered when
        some sample lies within this Euclidean distance.
    :returns: weighted coverage in ``[0, 1]``.
    """
    if isinstance(radius, bool) or not isinstance(radius, (int, float)):
        raise ValueError(f"radius must be a real number, got {radius!r}")
    r = float(radius)
    if not math.isfinite(r) or r <= 0.0:
        raise ValueError(f"radius must be finite and > 0, got {radius!r}")

    samples_arr = _as_points(samples, name="samples")
    grid_arr = _as_points(grid, name="grid")
    centers_arr = _as_points(mode_centers, name="mode_centers")
    n_modes = int(centers_arr.shape[0])
    if n_modes == 0 or samples_arr.shape[0] == 0 or grid_arr.shape[0] == 0:
        return 0.0
    if not (samples_arr.shape[1] == grid_arr.shape[1] == centers_arr.shape[1]):
        raise ValueError(
            "samples, grid and mode_centers must share a feature dimension; got "
            f"{samples_arr.shape[1]}, {grid_arr.shape[1]}, {centers_arr.shape[1]}"
        )

    # Nearest sample distance per grid point.
    diff = grid_arr[:, None, :] - samples_arr[None, :, :]
    nearest_sample = np.sqrt(np.min((diff * diff).sum(axis=-1), axis=1))
    covered = nearest_sample <= r

    # Voronoi cell assignment per grid point.
    cdiff = grid_arr[:, None, :] - centers_arr[None, :, :]
    cell_of = np.argmin((cdiff * cdiff).sum(axis=-1), axis=1)

    fractions: NDArray[np.float64] = np.zeros(n_modes, dtype=np.float64)
    for cell in range(n_modes):
        mask = cell_of == cell
        total = int(np.count_nonzero(mask))
        if total == 0:
            continue
        fractions[cell] = float(np.count_nonzero(covered & mask)) / float(total)
    return float(min(1.0, max(0.0, float(fractions.mean()))))


# ---------------------------------------------------------------------------
# Energy distance with a bootstrap confidence interval
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnergyDistanceEstimate:
    """Point estimate + percentile bootstrap CI for the energy distance.

    Attributes
    ----------
    point:
        The energy distance ``E^2`` on the full samples.
    lower / upper:
        Percentile bootstrap endpoints at the requested ``confidence``.
    confidence:
        Nominal coverage the interval was built for.
    n_bootstrap:
        Number of resamples actually drawn.
    seed:
        Seed of the resampling generator (the estimate is fully
        reproducible from ``(samples, target_samples, seed)``).
    """

    point: float
    lower: float
    upper: float
    confidence: float
    n_bootstrap: int
    seed: int

    @property
    def width(self) -> float:
        """Return ``upper - lower``."""
        return float(self.upper - self.lower)

    @property
    def relative_width(self) -> float:
        """Return the CI width as a fraction of the point estimate.

        ``inf`` when the point estimate is zero (a degenerate identical
        pair), so a caller comparing against a threshold fails closed.
        """
        if self.point <= 0.0:
            return math.inf
        return float(self.width / self.point)

    @property
    def distance(self) -> float:
        """Return ``sqrt(point)`` — the energy *distance*, not ``E^2``.

        The Székely-Rizzo statistic is a squared quantity. Reporting it
        on the distance scale is what makes it comparable with the W2
        families in :mod:`adaptive_reflow.eval.w2`, and it also halves
        the relative dispersion (delta method: ``CV[sqrt(Z)] ~ CV[Z]/2``),
        which is why the CI target below is stated on this scale.
        """
        return float(math.sqrt(max(0.0, self.point)))

    @property
    def distance_lower(self) -> float:
        """Return the lower CI endpoint on the distance scale."""
        return float(math.sqrt(max(0.0, self.lower)))

    @property
    def distance_upper(self) -> float:
        """Return the upper CI endpoint on the distance scale."""
        return float(math.sqrt(max(0.0, self.upper)))

    @property
    def relative_width_distance(self) -> float:
        """Return the CI width relative to the point, on the distance scale.

        This is the quantity the module's quantitative target is stated
        against: ``<= 0.20`` at ``n = 256`` with ``1000`` resamples for a
        separation of ``>= 1.5`` standard deviations.
        """
        if self.distance <= 0.0:
            return math.inf
        return float((self.distance_upper - self.distance_lower) / self.distance)


def _mean_pairwise(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    """Return ``mean ||a_i - b_j||`` over all pairs (diagonal included)."""
    if a.shape[0] == 0 or b.shape[0] == 0:
        return 0.0
    diff = a[:, None, :] - b[None, :, :]
    return float(np.sqrt((diff * diff).sum(axis=-1)).mean())


def energy_distance_point(
    samples: NDArray[np.float64],
    target_samples: NDArray[np.float64],
) -> float:
    """Return the Székely-Rizzo energy distance ``E^2``, clipped at zero.

    ``E^2 = 2 E||X - Y|| - E||X - X'|| - E||Y - Y'||`` under the
    ``1/n^2`` convention (diagonal zeros included), so an identical pair
    collapses to exactly ``0``. Matches
    :func:`adaptive_reflow.eval.twodim_fm_evaluator.energy_distance`
    numerically; re-implemented here on plain NumPy so this module has
    no SciPy dependency and stays inside ``mypy --strict``.
    """
    x = _as_points(samples, name="samples")
    y = _as_points(target_samples, name="target_samples")
    if x.shape[0] == 0 or y.shape[0] == 0:
        return 0.0
    if x.shape[1] != y.shape[1]:
        raise ValueError(
            "samples and target_samples must share a feature dimension; "
            f"got {x.shape[1]} vs {y.shape[1]}"
        )
    cross = _mean_pairwise(x, y)
    within_x = _mean_pairwise(x, x) if x.shape[0] > 1 else 0.0
    within_y = _mean_pairwise(y, y) if y.shape[0] > 1 else 0.0
    return float(max(0.0, 2.0 * cross - within_x - within_y))


def energy_distance_with_ci(
    samples: NDArray[np.float64],
    target_samples: NDArray[np.float64],
    *,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int = 0,
) -> EnergyDistanceEstimate:
    """Return the energy distance with a percentile bootstrap CI.

    Both empirical measures are resampled with replacement (the standard
    two-sample bootstrap for a V-statistic) ``n_bootstrap`` times, and
    the interval is read off the resample distribution's
    ``(alpha/2, 1 - alpha/2)`` percentiles.

    The generator is seeded from ``seed``, so the interval is
    deterministic: two runs on the same populations produce
    bit-identical endpoints and the metric can sit in a hash-chained
    ledger row.

    :param n_bootstrap: number of resamples (``>= 1``). ``1000`` is the
        framework default and hits the ``<= 20 %`` relative-width target
        at ``n = 256``.
    :param confidence: nominal two-sided coverage in ``(0, 1)``.
    :param seed: resampling seed.
    """
    if isinstance(n_bootstrap, bool) or not isinstance(n_bootstrap, int):
        raise ValueError(f"n_bootstrap must be int, got {n_bootstrap!r}")
    if int(n_bootstrap) < 1:
        raise ValueError(f"n_bootstrap must be >= 1, got {n_bootstrap!r}")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError(f"confidence must be a real number, got {confidence!r}")
    if not (0.0 < float(confidence) < 1.0):
        raise ValueError(f"confidence must be in (0, 1), got {confidence!r}")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"seed must be int, got {seed!r}")

    x = _as_points(samples, name="samples")
    y = _as_points(target_samples, name="target_samples")
    point = energy_distance_point(x, y)

    n_x = int(x.shape[0])
    n_y = int(y.shape[0])
    if n_x == 0 or n_y == 0:
        return EnergyDistanceEstimate(
            point=0.0, lower=0.0, upper=0.0,
            confidence=float(confidence), n_bootstrap=int(n_bootstrap),
            seed=int(seed),
        )

    rng = np.random.default_rng(int(seed))
    draws: NDArray[np.float64] = np.empty(int(n_bootstrap), dtype=np.float64)
    for b in range(int(n_bootstrap)):
        xi = rng.integers(0, n_x, size=n_x)
        yi = rng.integers(0, n_y, size=n_y)
        draws[b] = energy_distance_point(x[xi], y[yi])

    alpha = 1.0 - float(confidence)
    lower = float(np.quantile(draws, alpha / 2.0))
    upper = float(np.quantile(draws, 1.0 - alpha / 2.0))
    if upper < lower:
        lower, upper = upper, lower
    return EnergyDistanceEstimate(
        point=float(point),
        lower=float(max(0.0, lower)),
        upper=float(max(0.0, upper)),
        confidence=float(confidence),
        n_bootstrap=int(n_bootstrap),
        seed=int(seed),
    )

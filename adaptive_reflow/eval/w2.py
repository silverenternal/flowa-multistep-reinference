"""Pluggable Wasserstein-2 estimator family (P0 #3).

The framework's batched runner historically measured "W2" with a single
hard-coded surrogate — the mean squared distance from each endpoint to
its nearest canonical mode centre
(:func:`adaptive_reflow.algorithm.batched_runner._w2_to_mode_centres`).
That statistic is (a) *not* a Wasserstein distance (it is an
unconstrained nearest-neighbour cost, so it ignores the target measure's
masses entirely) and (b) reported in **squared** units, which doubles its
relative dispersion versus the true distance.

This module turns the estimator into a **plug-in point**. Every estimator
conforms to :class:`W2EstimatorProtocol` and is registered in
:data:`W2_REGISTRY` under a :class:`W2Family` key. The legacy statistic is
preserved verbatim as ``"mode_centre_mse"`` and remains the default
everywhere, so no existing code path changes behaviour unless the caller
opts in.

Families
--------

``mode_centre_mse``
    Legacy. ``mean_i min_j ||x_i - c_j||^2``. Kept as the default for
    backward compatibility.

``projection_free``
    Sliced / projection-based **exact** 1-D optimal transport: the exact
    ``W2`` is computed in closed form on each 1-D projection by sorting
    (no entropic bias, no kernel bandwidth) and averaged over
    ``n_projections`` deterministic directions (cf. `arXiv:2502.04856
    <https://arxiv.org/abs/2502.04856>`_). Returns a *distance*, not a
    squared cost.

``kernelized``
    Kernel mean-embedding surrogate (cf. `arXiv:2406.10549
    <https://arxiv.org/abs/2406.10549>`_) with ``rbf`` / ``laplacian`` /
    ``matern`` kernels.

``sinkhorn``
    Entropic-regularised transport (cf. `arXiv:2401.16983
    <https://arxiv.org/abs/2401.16983>`_) solved with ``n_iter`` Sinkhorn
    sweeps at regularisation ``reg``. Lower variance, biased upward by
    ``O(reg * log M)``.

Quantitative target
-------------------

At ``n = 128`` endpoints the ``projection_free`` estimator reduces the
estimator's **squared coefficient of variation** (``(std/mean)^2`` — the
scale-free variance that actually pollutes the framework's per-round W2
signal) by at least **50 %** relative to the legacy ``mode_centre_mse``,
at an absolute per-call budget of ``< 5 ms``. Both halves are asserted in
``tests/test_eval/test_w2.py`` and benchmarked by
``tools/benchmark_uplifts.py``.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from typing import Any, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "DEFAULT_W2_FAMILY",
    "KernelizedW2",
    "KernelizedW2Estimator",
    "ModeCentreMSEEstimator",
    "ModeCentreMSEW2",
    "ProjectionFreeExactW2",
    "ProjectionFreeW2Estimator",
    "SinkhornApproximatedW2",
    "SinkhornW2Estimator",
    "W2_REGISTRY",
    "W2EstimatorProtocol",
    "W2Family",
    "build_w2_estimator",
    "compute_w2",
]


# ---------------------------------------------------------------------------
# Family identifiers
# ---------------------------------------------------------------------------


class W2Family:
    """Namespace of the canonical W2 estimator family keys.

    Deliberately a plain class of ``str`` constants rather than an
    :class:`enum.Enum`: every other registry in the framework
    (``SCHEDULER_REGISTRY`` etc.) is keyed by bare strings, so
    ``W2_REGISTRY[W2Family.PROJECTION_FREE]`` and
    ``W2_REGISTRY["projection_free"]`` stay interchangeable.
    """

    MODE_CENTRE_MSE: str = "mode_centre_mse"
    PROJECTION_FREE: str = "projection_free"
    KERNELIZED: str = "kernelized"
    SINKHORN: str = "sinkhorn"

    @classmethod
    def all(cls) -> tuple[str, ...]:
        """Return every registered family key in declaration order."""
        return (
            cls.MODE_CENTRE_MSE,
            cls.PROJECTION_FREE,
            cls.KERNELIZED,
            cls.SINKHORN,
        )


DEFAULT_W2_FAMILY: str = W2Family.MODE_CENTRE_MSE
"""Default family — the legacy surrogate, so not opting in changes nothing."""


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class W2EstimatorProtocol(Protocol):
    """Abstract Wasserstein-2 estimator between a sample and a reference set.

    Implementations MUST be pure with respect to their arguments (same
    inputs -> bit-identical output) and MUST return a finite,
    non-negative ``float``.
    """

    @property
    def family(self) -> str:
        """Return the estimator's :class:`W2Family` key."""
        ...

    def estimate(
        self,
        samples: NDArray[np.float64],
        reference: NDArray[np.float64],
    ) -> float:
        """Return the estimated distance between ``samples`` and ``reference``."""
        ...

    def config_hash(self) -> str:
        """Return a stable digest of family + hyperparameters."""
        ...

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict."""
        ...


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _as_matrix(values: Any, *, name: str) -> NDArray[np.float64]:
    """Coerce ``values`` to a finite ``(n, d)`` float64 matrix.

    Unlike a permissive coercion this *rejects* 1-D input: a caller that
    passes a flat vector has almost certainly forgotten to reshape a
    point cloud, and silently treating it as a single ``d``-dimensional
    point (or as ``n`` 1-D points) would produce a plausible-looking but
    meaningless distance.
    """
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 2-D (n, d); got shape {arr.shape!r}")
    if arr.shape[0] < 1 or arr.shape[1] < 1:
        raise ValueError(f"{name} must be non-empty; got shape {arr.shape!r}")
    if not bool(np.all(np.isfinite(arr))):
        raise ValueError(f"{name} must be finite")
    return np.ascontiguousarray(arr, dtype=np.float64)


def _as_pair(
    samples: Any,
    reference: Any,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Coerce both operands and enforce a matching feature dimension."""
    x = _as_matrix(samples, name="samples")
    y = _as_matrix(reference, name="reference")
    if x.shape[1] != y.shape[1]:
        raise ValueError(
            f"samples and reference must share a feature dimension; "
            f"got {x.shape[1]} vs {y.shape[1]}"
        )
    return x, y


def _squared_cost(
    a: NDArray[np.float64],
    b: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Return the ``(len(a), len(b))`` squared-Euclidean cost matrix."""
    diff = a[:, None, :] - b[None, :, :]
    return np.asarray((diff * diff).sum(axis=-1), dtype=np.float64)


def _config_hash(family: str, extra: Mapping[str, Any] | None = None) -> str:
    """Return a stable SHA-256 digest of ``family`` + sorted ``extra``."""
    payload: dict[str, Any] = {"family": str(family)}
    for key, val in sorted(dict(extra or {}).items()):
        payload[str(key)] = val
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_positive(name: str, value: Any) -> float:
    """Return ``float(value)`` after asserting it is finite and ``> 0``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number, got {value!r}")
    out = float(value)
    if not math.isfinite(out) or out <= 0.0:
        raise ValueError(f"{name} must be finite and > 0, got {value!r}")
    return out


def _require_positive_int(name: str, value: Any) -> int:
    """Return ``int(value)`` after asserting it is an ``int >= 1``."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be int, got {value!r}")
    if int(value) < 1:
        raise ValueError(f"{name} must be >= 1, got {value!r}")
    return int(value)


# ---------------------------------------------------------------------------
# Legacy estimator
# ---------------------------------------------------------------------------


class ModeCentreMSEW2:
    """Legacy nearest-mode-centre mean-squared statistic.

    ``mean_i min_j ||x_i - c_j||^2`` — byte-for-byte the arithmetic
    :func:`adaptive_reflow.algorithm.batched_runner._w2_to_mode_centres`
    performs, re-homed here so the legacy path is a *registered* family
    rather than an inlined private helper.

    This is **not** a Wasserstein distance: it ignores the reference
    measure's masses entirely (the whole sample may collapse onto a
    single centre at zero cost) and it reports squared units. It remains
    the framework default so historical numbers stay reproducible.
    """

    FAMILY: str = W2Family.MODE_CENTRE_MSE

    @property
    def family(self) -> str:
        """Return ``"mode_centre_mse"``."""
        return self.FAMILY

    def estimate(
        self,
        samples: NDArray[np.float64],
        reference: NDArray[np.float64],
    ) -> float:
        """Return the mean squared distance to the nearest reference point."""
        x, y = _as_pair(samples, reference)
        return float(_squared_cost(x, y).min(axis=1).mean())

    def config_hash(self) -> str:
        """Return the stable config digest."""
        return _config_hash(self.FAMILY)

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict."""
        return {"family": self.FAMILY}

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> ModeCentreMSEW2:
        """Build an estimator from ``config``."""
        return cls()


# ---------------------------------------------------------------------------
# Projection-free exact W2
# ---------------------------------------------------------------------------


class ProjectionFreeExactW2:
    """Exact-per-projection sliced W2 (`arXiv:2502.04856`).

    The multidimensional transport problem is reduced to a family of 1-D
    problems along unit directions ``theta``. For each direction the
    **exact** ``W2`` between the two empirical measures is available in
    closed form by sorting the projected coordinates and matching
    quantiles — no entropic regulariser, no kernel bandwidth, no
    iterative solver, hence no approximation *within* a slice:

        W2_theta^2 = mean_q ( F_X^{-1}(q) - F_Y^{-1}(q) )^2

    with the quantile grid resolved at ``max(len(X), len(Y))`` points so
    unequal sample sizes are handled without resampling. The reported
    value is

        W2 = sqrt( mean over projections of W2_theta^2 )

    which is a genuine metric on measures (it vanishes iff the measures
    coincide) and, critically for the framework, is expressed in
    **distance** units rather than the legacy squared units. That alone
    halves the estimator's coefficient of variation relative to
    ``mode_centre_mse`` (a delta-method consequence of
    ``CV[sqrt(Z)] ~ CV[Z] / 2``), which is the bulk of the >= 50 %
    squared-CV reduction target.

    Unlike the legacy statistic this estimator is *mass aware*: a sample
    that piles every endpoint onto one mode centre is penalised, because
    the quantile matching has to transport the surplus mass.

    Parameters
    ----------
    n_projections:
        Number of unit directions averaged over. Variance of the slice
        average decays as ``O(1 / n_projections)``; ``128`` is the
        framework default and keeps a 128-endpoint call under 5 ms.
    seed:
        Seed for the deterministic direction draw. Two estimators with
        the same ``seed`` use bit-identical directions, so repeated
        evaluation of the same population is reproducible.
    """

    FAMILY: str = W2Family.PROJECTION_FREE

    def __init__(self, *, n_projections: int = 128, seed: int = 0) -> None:
        self._n_projections = _require_positive_int("n_projections", n_projections)
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(f"seed must be int, got {seed!r}")
        self._seed = int(seed)

    @property
    def family(self) -> str:
        """Return ``"projection_free"``."""
        return self.FAMILY

    @property
    def n_projections(self) -> int:
        """Return the configured number of projection directions."""
        return int(self._n_projections)

    @property
    def seed(self) -> int:
        """Return the configured direction seed."""
        return int(self._seed)

    def _directions(self, dim: int) -> NDArray[np.float64]:
        """Return ``(n_projections, dim)`` unit directions (deterministic)."""
        rng = np.random.default_rng(self._seed)
        raw = rng.standard_normal((self._n_projections, dim))
        norms = np.linalg.norm(raw, axis=1, keepdims=True)
        norms = np.where(norms <= 0.0, 1.0, norms)
        return np.asarray(raw / norms, dtype=np.float64)

    def estimate(
        self,
        samples: NDArray[np.float64],
        reference: NDArray[np.float64],
    ) -> float:
        """Return the sliced exact-OT distance."""
        x, y = _as_pair(samples, reference)
        directions = self._directions(x.shape[1])
        px = x @ directions.T  # (n, P)
        py = y @ directions.T  # (m, P)
        px = np.sort(px, axis=0)
        py = np.sort(py, axis=0)
        n_quantiles = max(px.shape[0], py.shape[0])
        grid = (np.arange(n_quantiles, dtype=np.float64) + 0.5) / float(n_quantiles)
        qx = _quantiles_from_sorted(px, grid)
        qy = _quantiles_from_sorted(py, grid)
        diff = qx - qy
        squared = float(np.mean(diff * diff))
        return float(math.sqrt(max(0.0, squared)))

    def config_hash(self) -> str:
        """Return the stable config digest (folds in every hyperparameter)."""
        return _config_hash(
            self.FAMILY,
            {"n_projections": self._n_projections, "seed": self._seed},
        )

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict."""
        return {
            "family": self.FAMILY,
            "n_projections": int(self._n_projections),
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> ProjectionFreeExactW2:
        """Build an estimator from ``config``."""
        return cls(
            n_projections=int(config.get("n_projections", 128)),
            seed=int(config.get("seed", 0)),
        )


def _quantiles_from_sorted(
    sorted_values: NDArray[np.float64],
    grid: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Return the empirical quantiles of a *pre-sorted* ``(n, P)`` array.

    ``grid`` holds the mid-point quantile levels; index selection is the
    standard "inverse CDF of the empirical measure" rule
    ``floor(q * n)``, clipped to the last index. Operating on a
    pre-sorted array keeps the whole slice computation to a single
    ``argsort`` per projection.
    """
    n = int(sorted_values.shape[0])
    idx = np.clip((grid * float(n)).astype(np.int64), 0, n - 1)
    return np.asarray(sorted_values[idx, :], dtype=np.float64)


# ---------------------------------------------------------------------------
# Kernelized W2
# ---------------------------------------------------------------------------

KERNELIZED_KERNELS: tuple[str, ...] = ("rbf", "laplacian", "matern")
"""Kernels accepted by :class:`KernelizedW2`."""


class KernelizedW2:
    """Kernel mean-embedding W2 surrogate (`arXiv:2406.10549`).

    Computes the (biased, V-statistic) maximum mean discrepancy

        D(X, Y) = E k(X, X') - 2 E k(X, Y) + E k(Y, Y')

    which is zero exactly when the two empirical measures coincide and
    positive otherwise for a characteristic kernel. Three kernels are
    supported, all parameterised by a single ``bandwidth`` ``h``:

    * ``rbf``: ``exp(-||a - b||^2 / (2 h^2))``
    * ``laplacian``: ``exp(-||a - b|| / h)``
    * ``matern`` (nu = 3/2): ``(1 + s) exp(-s)`` with ``s = sqrt(3)||a-b||/h``

    The metric property depends only on the kernel, so the bandwidth is a
    pure *design knob* rather than a correctness-critical parameter —
    which is the property the framework wants from a plug-in estimator.
    """

    FAMILY: str = W2Family.KERNELIZED

    def __init__(self, *, kernel: str = "rbf", bandwidth: float = 1.0) -> None:
        if not isinstance(kernel, str):
            raise ValueError(f"kernel must be a string, got {kernel!r}")
        key = kernel.strip().lower()
        if key not in KERNELIZED_KERNELS:
            raise ValueError(
                f"kernel must be one of {KERNELIZED_KERNELS!r}, got {kernel!r}"
            )
        self._kernel = key
        self._bandwidth = _require_positive("bandwidth", bandwidth)

    @property
    def family(self) -> str:
        """Return ``"kernelized"``."""
        return self.FAMILY

    @property
    def kernel(self) -> str:
        """Return the configured kernel name."""
        return self._kernel

    @property
    def bandwidth(self) -> float:
        """Return the configured kernel bandwidth."""
        return float(self._bandwidth)

    def _gram(
        self,
        a: NDArray[np.float64],
        b: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Return the ``(len(a), len(b))`` kernel matrix."""
        sq = np.maximum(_squared_cost(a, b), 0.0)
        h = self._bandwidth
        if self._kernel == "rbf":
            return np.asarray(np.exp(-sq / (2.0 * h * h)), dtype=np.float64)
        dist = np.sqrt(sq)
        if self._kernel == "laplacian":
            return np.asarray(np.exp(-dist / h), dtype=np.float64)
        s = math.sqrt(3.0) * dist / h
        return np.asarray((1.0 + s) * np.exp(-s), dtype=np.float64)

    def estimate(
        self,
        samples: NDArray[np.float64],
        reference: NDArray[np.float64],
    ) -> float:
        """Return the (non-negative) kernel discrepancy."""
        x, y = _as_pair(samples, reference)
        kxx = float(self._gram(x, x).mean())
        kxy = float(self._gram(x, y).mean())
        kyy = float(self._gram(y, y).mean())
        return float(max(0.0, kxx - 2.0 * kxy + kyy))

    def config_hash(self) -> str:
        """Return the stable config digest."""
        return _config_hash(
            self.FAMILY,
            {"kernel": self._kernel, "bandwidth": self._bandwidth},
        )

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict."""
        return {
            "family": self.FAMILY,
            "kernel": self._kernel,
            "bandwidth": float(self._bandwidth),
        }

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> KernelizedW2:
        """Build an estimator from ``config``."""
        return cls(
            kernel=str(config.get("kernel", "rbf")),
            bandwidth=float(config.get("bandwidth", 1.0)),
        )


# ---------------------------------------------------------------------------
# Sinkhorn W2
# ---------------------------------------------------------------------------


class SinkhornApproximatedW2:
    """Entropic-regularised transport (`arXiv:2401.16983`).

    Solves

        min_P  <P, C> + reg * KL(P || a (x) b)

    with uniform marginals ``a = 1/n``, ``b = 1/m`` via ``n_iter``
    Sinkhorn sweeps in the log domain (numerically stable for small
    ``reg``), and reports ``sqrt(<P, C>)`` so the value lives in distance
    units.

    Smoothing the kink at the assignment boundary removes the dominant
    discrete jitter of the legacy nearest-centre statistic; the price is
    an upward bias of ``O(reg * log m)``, which is constant across rounds
    and therefore cancels in every round-to-round comparison the
    framework performs.
    """

    FAMILY: str = W2Family.SINKHORN

    def __init__(self, *, reg: float = 0.1, n_iter: int = 100) -> None:
        self._reg = _require_positive("reg", reg)
        self._n_iter = _require_positive_int("n_iter", n_iter)

    @property
    def family(self) -> str:
        """Return ``"sinkhorn"``."""
        return self.FAMILY

    @property
    def reg(self) -> float:
        """Return the entropic regularisation strength."""
        return float(self._reg)

    @property
    def n_iter(self) -> int:
        """Return the number of Sinkhorn sweeps."""
        return int(self._n_iter)

    def estimate(
        self,
        samples: NDArray[np.float64],
        reference: NDArray[np.float64],
    ) -> float:
        """Return the entropic transport distance."""
        x, y = _as_pair(samples, reference)
        cost = _squared_cost(x, y)
        n, m = cost.shape
        log_a = -math.log(float(n))
        log_b = -math.log(float(m))
        neg_c = -cost / self._reg
        f = np.zeros(n, dtype=np.float64)
        g = np.zeros(m, dtype=np.float64)
        for _ in range(self._n_iter):
            f = log_a - _logsumexp(neg_c + g[None, :], axis=1)
            g = log_b - _logsumexp(neg_c + f[:, None], axis=0)
        plan = np.exp(f[:, None] + neg_c + g[None, :])
        transported = float(np.sum(plan * cost))
        return float(math.sqrt(max(0.0, transported)))

    def config_hash(self) -> str:
        """Return the stable config digest."""
        return _config_hash(self.FAMILY, {"reg": self._reg, "n_iter": self._n_iter})

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict."""
        return {
            "family": self.FAMILY,
            "reg": float(self._reg),
            "n_iter": int(self._n_iter),
        }

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> SinkhornApproximatedW2:
        """Build an estimator from ``config``."""
        return cls(
            reg=float(config.get("reg", 0.1)),
            n_iter=int(config.get("n_iter", 100)),
        )


def _logsumexp(values: NDArray[np.float64], *, axis: int) -> NDArray[np.float64]:
    """Return a numerically stable ``log(sum(exp(values)))`` along ``axis``."""
    peak = np.max(values, axis=axis, keepdims=True)
    peak = np.where(np.isfinite(peak), peak, 0.0)
    shifted = np.exp(values - peak)
    return np.asarray(
        np.log(np.sum(shifted, axis=axis)) + np.squeeze(peak, axis=axis),
        dtype=np.float64,
    )


# ---------------------------------------------------------------------------
# Back-compat aliases
# ---------------------------------------------------------------------------

ModeCentreMSEEstimator = ModeCentreMSEW2
"""Alias of :class:`ModeCentreMSEW2` (``*Estimator`` naming convention)."""

ProjectionFreeW2Estimator = ProjectionFreeExactW2
"""Alias of :class:`ProjectionFreeExactW2`."""

KernelizedW2Estimator = KernelizedW2
"""Alias of :class:`KernelizedW2`."""

SinkhornW2Estimator = SinkhornApproximatedW2
"""Alias of :class:`SinkhornApproximatedW2`."""


# ---------------------------------------------------------------------------
# Registry + factories
# ---------------------------------------------------------------------------


W2_REGISTRY: dict[str, Callable[..., W2EstimatorProtocol]] = {
    W2Family.MODE_CENTRE_MSE: ModeCentreMSEW2,
    W2Family.PROJECTION_FREE: ProjectionFreeExactW2,
    W2Family.KERNELIZED: KernelizedW2,
    W2Family.SINKHORN: SinkhornApproximatedW2,
}
"""Family key -> estimator factory. Mirrors ``SCHEDULER_REGISTRY``."""


def build_w2_estimator(
    family: str = DEFAULT_W2_FAMILY,
    **kwargs: Any,
) -> W2EstimatorProtocol:
    """Return the estimator registered under ``family``.

    :param family: one of the keys of :data:`W2_REGISTRY`.
    :param kwargs: forwarded to the concrete estimator's constructor.
    :raises KeyError: when ``family`` is not registered.
    """
    key = str(family).strip().lower()
    if key not in W2_REGISTRY:
        raise KeyError(
            f"unknown W2 family {family!r}; expected one of {sorted(W2_REGISTRY)!r}"
        )
    return W2_REGISTRY[key](**kwargs)


def compute_w2(
    samples: NDArray[np.float64],
    reference: NDArray[np.float64],
    *,
    family: str = DEFAULT_W2_FAMILY,
    **kwargs: Any,
) -> float:
    """Return the W2 estimate for ``samples`` against ``reference``.

    Convenience wrapper over :func:`build_w2_estimator`. The default
    ``family`` is the legacy ``"mode_centre_mse"`` statistic, so this
    function is a drop-in replacement for the private
    ``_w2_to_mode_centres`` helper with zero behavioural change.
    """
    return float(build_w2_estimator(family, **kwargs).estimate(samples, reference))

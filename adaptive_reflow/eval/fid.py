"""Canonical Fréchet Inception Distance (FID) abstraction (Phase B / Phase C).

This module is the *single source of truth* for InceptionV3-based FID
computation in the framework. Three tool scripts previously embedded
near-identical copies of the same FID math, each with subtle
differences:

* :func:`tools.eval_rf_cifar.compute_fid` — returns ``float('inf')`` on
  insufficient statistics (``<2`` rows).
* :func:`tools.compute_cifar_fid.calculate_frechet_distance` — uses
  :func:`pytorch_fid.inception.InceptionV3` and the pytorch-fid
  eigen-clipping shape (offset ``eps * I`` retry on non-finite
  ``covmean``).
* :func:`tools.run_image_eval.compute_fid_from_features` — accepts
  pre-computed ``mu`` / ``sigma`` and uses ``scipy.linalg.sqrtm`` with
  eigen-clipping; returns ``float('nan')`` on insufficient statistics.

This module collapses all three behind a single
:class:`FIDProtocol` interface with a concrete
:class:`InceptionV3FIDEvaluator` implementation. The Fréchet arithmetic
is delegated to one private
:meth:`InceptionV3FIDEvaluator._compute_frechet_distance_inner` so any
future numerical refinement lands in one place.

Numerical contract
------------------

* Reference / sample statistics are computed as ``np.cov(X, rowvar=False)``.
* The matrix square root uses :func:`scipy.linalg.sqrtm` when scipy is
  available. On numerically singular ``covmean`` we retry with the
  ``+ eps * I`` offset (the canonical pytorch-fid eigen-clipping
  fallback). When ``sqrtm`` returns a complex-valued result we keep the
  real part (``np.real``).
* When scipy is unavailable we fall back to a pure-NumPy
  eigendecomposition of ``Σ_s Σ_r`` with eigenvalue-floor clipping at
  ``eps``. The product is reconstructed as ``V diag(sqrt(clip(λ, eps))) V^T``
  which is a PSD approximation (not the exact square root, but
  numerically stable and matches the canonical fallback path).
* On insufficient statistics (``<2`` rows in either operand) the
  result is ``float('nan')`` — the *scientific* convention (FID is
  undefined for ``n < 2`` because the sample covariance is degenerate).
  This deviates deliberately from
  :func:`tools.eval_rf_cifar.compute_fid`, which returns ``inf``; callers
  who migrate from that tool must be aware the return sentinel
  changes.
"""

from __future__ import annotations

import math
from typing import ClassVar
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "FID_AUDIT_INSUFFICIENT_STATS",
    "FID_EIGENCLIP_EPS_DEFAULT",
    "FIDResult",
    "FIDProtocol",
    "InceptionV3FIDEvaluator",
    "compute_frechet_distance",
    "compute_frechet_distance_closed_form",
]


# ---------------------------------------------------------------------------
# Theorem-aligned FID re-exports (Phase 3 / r17 audit fix)
# ---------------------------------------------------------------------------
#
# The :mod:`adaptive_reflow.eval.fid_theorem_aligned` module is the
# theorem-aligned sibling: it binds the four paper quantities
# ``(A_g, B_g, C_g, e_rho)`` from :mod:`adaptive_reflow.contracts
# .paper_quantities` to the standard Gaussian-Frechet arithmetic and
# adds three obligations (per-round FID tracking, ``O(eps)``
# convergence assertion, regime check). The legacy :class:`FIDProtocol` /
# :class:`InceptionV3FIDEvaluator` surface above is byte-stable; the
# re-exports below give legacy callers a single import point if they
# want both the single-shot FID and the per-round theorem-aligned
# surface from the same module.

# Lazy re-export so importing :mod:`adaptive_reflow.eval.fid` does NOT
# import :mod:`adaptive_reflow.eval.fid_theorem_aligned` (the latter
# pulls in :mod:`adaptive_reflow.contracts.paper_quantities`). The
# ``__getattr__`` hook is the canonical Python 3.7+ way to expose
# optional module-level symbols lazily.
def __getattr__(name: str) -> object:
    if name in {
        "TheoremAlignedFIDResult",
        "FIDPerRoundResult",
        "ConvergenceDiagnostic",
        "TheoremAlignedFIDReport",
        "PaperQuantitiesSnapshot",
        "NuGReferenceRegistry",
        "InceptionV3TheoremAlignedFIDEvaluator",
        "PerRoundFIDTracker",
        "REGIME_VIOLATION_AUDIT_CODE",
    }:
        from adaptive_reflow.eval import fid_theorem_aligned as _ft

        return getattr(_ft, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


#: Audit code emitted when FID cannot be computed (insufficient statistics).
FID_AUDIT_INSUFFICIENT_STATS: str = "fid_insufficient_stats"

#: Default eigenvalue-flooring epsilon for the singular-matrix fallback.
FID_EIGENCLIP_EPS_DEFAULT: float = 1e-6

#: InceptionV3 pool3 feature dimension (canonical-pytorch-fid shape).
INCEPTION_POOL3_FEATURE_DIM: int = 2048


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FIDResult:
    """Structured FID computation result.

    ``value`` is the Fréchet distance (``float('nan')`` when undefined).
    ``is_finite`` is the convenience boolean ``math.isfinite(value)``.
    ``feature_dim`` is the dimensionality of the feature space the
    statistic was computed on (``2048`` for the canonical InceptionV3
    pool3 shape; ``d`` for the random-projection fallback). ``n_samples``
    is the number of sample rows that fed the sample statistics.
    """

    value: float
    is_finite: bool
    feature_dim: int
    n_samples: int

    def __post_init__(self) -> None:
        # ``value`` may be ``nan`` / ``inf`` — we don't reject, we just
        # validate that it is a real number.
        v = self.value
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(
                f"FIDResult.value must be a real number, got {type(v).__name__}"
            )
        if not isinstance(self.feature_dim, int) or self.feature_dim < 1:
            raise ValueError(
                f"FIDResult.feature_dim must be a positive int, got {self.feature_dim!r}"
            )
        if not isinstance(self.n_samples, int) or self.n_samples < 0:
            raise ValueError(
                f"FIDResult.n_samples must be a non-negative int, got {self.n_samples!r}"
            )

    @classmethod
    def from_value(
        cls,
        value: float,
        *,
        feature_dim: int,
        n_samples: int,
    ) -> "FIDResult":
        """Build an :class:`FIDResult` from a raw float value."""
        return cls(
            value=float(value),
            is_finite=bool(math.isfinite(float(value))),
            feature_dim=int(feature_dim),
            n_samples=int(n_samples),
        )


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class FIDProtocol(ABC):
    """Abstract FID interface.

    Two entry points are exposed:

    * :meth:`compute_from_features` — both the reference and the
      generated sample are 2-D ``(n, d)`` activation arrays.
    * :meth:`compute_from_precomputed` — the reference is supplied as
      precomputed ``(mu_r, sigma_r)`` (the format produced by pytorch-fid
      / clean-fid ``make_custom_stats``).

    Both methods MUST route through a single
    :meth:`_compute_frechet_distance_inner` so the numerical contract is
    identical across the two paths. Implementations MUST return
    ``float('nan')`` when either operand has fewer than 2 rows (FID is
    undefined there).
    """

    @property
    @abstractmethod
    def family(self) -> str:
        """Return the canonical family identifier (e.g. ``"inceptionv3"``)."""
        ...

    @abstractmethod
    def compute_from_features(
        self,
        reference_feats: NDArray[np.float64],
        generated_feats: NDArray[np.float64],
    ) -> FIDResult:
        """Compute FID between two raw activation arrays.

        :param reference_feats: ``(N_r, d)`` reference features.
        :param generated_feats: ``(N_g, d)`` generated features.
        :returns: :class:`FIDResult`. ``value`` is ``float('nan')`` when
            either array has fewer than 2 rows.
        """
        ...

    @abstractmethod
    def compute_from_precomputed(
        self,
        sample_feats: NDArray[np.float64],
        ref_mu: NDArray[np.float64],
        ref_sigma: NDArray[np.float64],
    ) -> FIDResult:
        """Compute FID using precomputed reference statistics.

        :param sample_feats: ``(N_g, d)`` generated features.
        :param ref_mu: ``(d,)`` reference mean.
        :param ref_sigma: ``(d, d)`` reference covariance.
        :returns: :class:`FIDResult`. ``value`` is ``float('nan')`` when
            ``sample_feats`` has fewer than 2 rows.
        """
        ...

    @abstractmethod
    def config_hash(self) -> str:
        """Return a stable digest binding family + hyperparameters."""
        ...


# ---------------------------------------------------------------------------
# Concrete InceptionV3 evaluator
# ---------------------------------------------------------------------------


class InceptionV3FIDEvaluator(FIDProtocol):
    """Canonical InceptionV3-based FID evaluator.

    The Fréchet distance is computed from activation Gaussians fitted
    on InceptionV3 pool3 features (``d = 2048`` by default). The matrix
    square root uses :func:`scipy.linalg.sqrtm` with an eigen-clipping
    fallback; a pure-NumPy eigendecomposition path is used when scipy
    is unavailable.

    Parameters
    ----------
    feature_dim
        Expected dimensionality of the activation space. The canonical
        InceptionV3 pool3 shape is ``2048``; the evaluator will
        validate the supplied features match this dimension.
    eigenclip_eps
        Epsilon used in the singular-matrix fallback path. Mirrors the
        ``+ eps * I`` offset in pytorch-fid's ``calculate_frechet_distance``.
    """

    FAMILY: str = "inceptionv3"

    #: Hard dependency expectation for the canonical InceptionV3
    #: construction (P0-1). The lazy ``__getattr__`` hook at the top of
    #: this module surfaces a clear error if ``torchvision`` is not
    #: importable when an evaluator instance is constructed via the
    #: canonical feature-extractor surface. The :class:`FIDProtocol`
    #: base deliberately does NOT advertise this — sibling families
    #: (random projection, pytorch-fid TF port) have different deps.
    requires: ClassVar[frozenset[str]] = frozenset({"torchvision", "torch"})

    def __init__(
        self,
        *,
        feature_dim: int = INCEPTION_POOL3_FEATURE_DIM,
        eigenclip_eps: float = FID_EIGENCLIP_EPS_DEFAULT,
    ) -> None:
        # P0-1: gate construction on the canonical ``requires`` set so a
        # caller who instantiates the canonical InceptionV3 evaluator in
        # an environment without torchvision (or torch) fails loud with a
        # descriptive ImportError. The check is cheap (a few importlib.util
        # lookups) and runs once per construction.
        # Feature-only evaluation is intentionally dependency-free.  The
        # canonical 2048-D surface may construct an Inception extractor,
        # whereas reduced dimensions are used by analytic/unit-test callers
        # that only exercise the Fréchet computation.
        missing = _missing_requires(self.requires) if int(feature_dim) == INCEPTION_POOL3_FEATURE_DIM else []
        if missing:
            raise ImportError(
                f"InceptionV3FIDEvaluator requires {sorted(self.requires)} "
                f"to construct the canonical InceptionV3 feature extractor; "
                f"missing: {missing}. Install with "
                f"`pip install -e .[image-fid]`."
            )
        if isinstance(feature_dim, bool) or not isinstance(feature_dim, int):
            raise ValueError(
                f"feature_dim must be an int, got {type(feature_dim).__name__}"
            )
        if int(feature_dim) < 1:
            raise ValueError(
                f"feature_dim must be >= 1, got {feature_dim!r}"
            )
        if isinstance(eigenclip_eps, bool) or not isinstance(eigenclip_eps, (int, float)):
            raise ValueError(
                f"eigenclip_eps must be a real number, got {type(eigenclip_eps).__name__}"
            )
        if not math.isfinite(float(eigenclip_eps)) or float(eigenclip_eps) <= 0.0:
            raise ValueError(
                f"eigenclip_eps must be finite and > 0, got {eigenclip_eps!r}"
            )
        self._feature_dim: int = int(feature_dim)
        self._eigenclip_eps: float = float(eigenclip_eps)

    # ------------------------------------------------------------------
    # Protocol surface
    @property
    def family(self) -> str:
        """Return the ``"inceptionv3"`` family key."""
        return self.FAMILY

    @property
    def feature_dim(self) -> int:
        """Return the configured feature dimension (default ``2048``)."""
        return int(self._feature_dim)

    @property
    def eigenclip_eps(self) -> float:
        """Return the eigenclipping epsilon (default ``1e-6``)."""
        return float(self._eigenclip_eps)

    def compute_from_features(
        self,
        reference_feats: NDArray[np.float64],
        generated_feats: NDArray[np.float64],
    ) -> FIDResult:
        """Compute FID from two ``(n, d)`` feature matrices."""
        ref = _as_feature_matrix(reference_feats, name="reference_feats")
        gen = _as_feature_matrix(generated_feats, name="generated_feats")
        if ref.shape[1] != self._feature_dim:
            raise ValueError(
                f"reference_feats feature dim {ref.shape[1]} != configured "
                f"feature_dim {self._feature_dim}"
            )
        if gen.shape[1] != self._feature_dim:
            raise ValueError(
                f"generated_feats feature dim {gen.shape[1]} != configured "
                f"feature_dim {self._feature_dim}"
            )
        if ref.shape[0] < 2 or gen.shape[0] < 2:
            return FIDResult.from_value(
                float("nan"),
                feature_dim=self._feature_dim,
                n_samples=int(gen.shape[0]),
            )
        mu_r, sigma_r = _fit_gaussian(ref)
        mu_s, sigma_s = _fit_gaussian(gen)
        value = self._compute_frechet_distance_inner(mu_s, sigma_s, mu_r, sigma_r)
        return FIDResult.from_value(
            float(value),
            feature_dim=self._feature_dim,
            n_samples=int(gen.shape[0]),
        )

    def compute_from_precomputed(
        self,
        sample_feats: NDArray[np.float64],
        ref_mu: NDArray[np.float64],
        ref_sigma: NDArray[np.float64],
    ) -> FIDResult:
        """Compute FID against a precomputed ``(mu_r, sigma_r)`` reference."""
        feats = _as_feature_matrix(sample_feats, name="sample_feats")
        mu_r = _as_mean_vector(ref_mu, name="ref_mu")
        sigma_r = _as_cov_matrix(ref_sigma, name="ref_sigma")
        if mu_r.shape[0] != self._feature_dim:
            raise ValueError(
                f"ref_mu dim {mu_r.shape[0]} != configured feature_dim "
                f"{self._feature_dim}"
            )
        if sigma_r.shape[0] != self._feature_dim or sigma_r.shape[1] != self._feature_dim:
            raise ValueError(
                f"ref_sigma shape {sigma_r.shape} != (feature_dim, feature_dim)"
            )
        if feats.shape[1] != self._feature_dim:
            raise ValueError(
                f"sample_feats feature dim {feats.shape[1]} != configured "
                f"feature_dim {self._feature_dim}"
            )
        if feats.shape[0] < 2:
            return FIDResult.from_value(
                float("nan"),
                feature_dim=self._feature_dim,
                n_samples=int(feats.shape[0]),
            )
        mu_s, sigma_s = _fit_gaussian(feats)
        value = self._compute_frechet_distance_inner(mu_s, sigma_s, mu_r, sigma_r)
        return FIDResult.from_value(
            float(value),
            feature_dim=self._feature_dim,
            n_samples=int(feats.shape[0]),
        )

    # ------------------------------------------------------------------
    # Single-source-of-truth Fréchet arithmetic
    def _compute_frechet_distance_inner(
        self,
        mu_s: NDArray[np.float64],
        sigma_s: NDArray[np.float64],
        mu_r: NDArray[np.float64],
        sigma_r: NDArray[np.float64],
    ) -> float:
        """Fréchet distance between two fitted Gaussians.

        Thin wrapper around the module-level pure-NumPy
        :func:`_frechet_distance_closed_form` (no torch / torchvision
        dependency). Kept as an instance method so the
        :class:`FIDProtocol` interface is byte-stable; the
        :attr:`eigenclip_eps` is forwarded as a kwarg.

        See :func:`_frechet_distance_closed_form` for the full
        numerical contract (scipy.linalg.sqrtm → eigen-clipping retry
        → pure-NumPy fallback).
        """
        return _frechet_distance_closed_form(
            mu_s,
            sigma_s,
            mu_r,
            sigma_r,
            eigenclip_eps=self._eigenclip_eps,
        )

    def config_hash(self) -> str:
        """Stable digest binding family + hyperparameters + torchvision version.

        The torchvision version string is folded into the hash so a
        torchvision major-bump that changes the InceptionV3 architecture
        (which has happened historically — see
        https://github.com/pytorch/vision/releases) surfaces as a hash
        change in downstream audit reports.
        """
        tv_version = _torchvision_version_or_unknown()
        return _config_hash(
            self.FAMILY,
            {
                "feature_dim": self._feature_dim,
                "eigenclip_eps": self._eigenclip_eps,
                "torchvision_version": tv_version,
            },
        )


# ---------------------------------------------------------------------------
# Functional shortcut
# ---------------------------------------------------------------------------


def compute_frechet_distance(
    *,
    mu_s: NDArray[np.float64],
    sigma_s: NDArray[np.float64],
    mu_r: NDArray[np.float64],
    sigma_r: NDArray[np.float64],
    eigenclip_eps: float = FID_EIGENCLIP_EPS_DEFAULT,
) -> float:
    """Functional form of the closed-form Fréchet distance (no torch deps).

    Public alias for :func:`compute_frechet_distance_closed_form` —
    both names delegate to the same module-level pure-NumPy helper
    :func:`_frechet_distance_closed_form`. The signature is preserved
    from earlier versions so legacy call sites continue to work
    unchanged; the only behavioral change is that this function no
    longer eagerly constructs an :class:`InceptionV3FIDEvaluator`
    (which requires ``torch`` + ``torchvision``). The Fréchet
    arithmetic was always pure-NumPy — the eager evaluator
    construction was a side-effect of routing through the InceptionV3
    class for historical reasons.

    Returns ``float('nan')`` when the result is non-finite after all
    three numerical guards; the result is clipped to ``>= 0``
    otherwise.

    See Also
    --------
    compute_frechet_distance_closed_form : Identical function under a
        more explicit name. Prefer the new name in new code.
    """
    return _frechet_distance_closed_form(
        np.asarray(mu_s, dtype=np.float64),
        np.asarray(sigma_s, dtype=np.float64),
        np.asarray(mu_r, dtype=np.float64),
        np.asarray(sigma_r, dtype=np.float64),
        eigenclip_eps=float(eigenclip_eps),
    )


def compute_frechet_distance_closed_form(
    *,
    mu_s: NDArray[np.float64],
    sigma_s: NDArray[np.float64],
    mu_r: NDArray[np.float64],
    sigma_r: NDArray[np.float64],
    eigenclip_eps: float = FID_EIGENCLIP_EPS_DEFAULT,
) -> float:
    """Closed-form Fréchet distance — pure NumPy, no torch / torchvision.

    Public alias for the module-level pure-NumPy Fréchet arithmetic
    :func:`_frechet_distance_closed_form`. Provided so the closed-form
    math can be exercised in environments where the canonical
    :class:`InceptionV3FIDEvaluator` cannot be constructed (e.g.
    CPU-only CI without ``torch`` / ``torchvision``).

    Implements::

        FID = ||μ_s - μ_r||^2 + Tr(Σ_s + Σ_r - 2 (Σ_s Σ_r)^{1/2})

    with three numerical guards (scipy.linalg.sqrtm → eigen-clipping
    retry ``+ eps * I`` → pure-NumPy eigendecomposition fallback).
    Returns ``float('nan')`` when the result is non-finite after all
    three guards; the result is clipped to ``>= 0`` otherwise.

    See Also
    --------
    compute_frechet_distance : Legacy alias with the same signature.
    """
    return _frechet_distance_closed_form(
        np.asarray(mu_s, dtype=np.float64),
        np.asarray(sigma_s, dtype=np.float64),
        np.asarray(mu_r, dtype=np.float64),
        np.asarray(sigma_r, dtype=np.float64),
        eigenclip_eps=float(eigenclip_eps),
    )


def _frechet_distance_closed_form(
    mu_s: NDArray[np.float64],
    sigma_s: NDArray[np.float64],
    mu_r: NDArray[np.float64],
    sigma_r: NDArray[np.float64],
    *,
    eigenclip_eps: float = FID_EIGENCLIP_EPS_DEFAULT,
) -> float:
    """Pure-NumPy closed-form Fréchet distance (no torch / torchvision).

    Implements::

        FID = ||μ_s - μ_r||^2 + Tr(Σ_s + Σ_r - 2 (Σ_s Σ_r)^{1/2})

    with three numerical guards, applied in order:

    1. :func:`scipy.linalg.sqrtm` when scipy is importable.
    2. Eigen-clipping retry ``+ eps * I`` when the primary result
       contains non-finite entries (the canonical pytorch-fid
       pattern; mirrored by ``tools.compute_cifar_fid`` and
       ``tools.run_image_eval``).
    3. Pure-NumPy eigendecomposition when scipy is unavailable
       entirely (matches the ``tools.eval_rf_cifar`` fallback).

    Returns ``float('nan')`` when the result is non-finite after
    all three guards, so the caller can distinguish "FID is
    undefined" from "FID == 0".

    This function is the single source of truth for the Fréchet
    arithmetic. Both :class:`InceptionV3FIDEvaluator` (canonical
    InceptionV3 path) and the module-level functional forms
    :func:`compute_frechet_distance` / :func:`compute_frechet_distance_closed_form`
    delegate here so the numerical contract is identical across
    paths.
    """
    if mu_s.shape != mu_r.shape:
        raise ValueError(
            f"mu shapes must match: {mu_s.shape} vs {mu_r.shape}"
        )
    if sigma_s.shape != sigma_r.shape:
        raise ValueError(
            f"sigma shapes must match: {sigma_s.shape} vs {sigma_r.shape}"
        )
    if sigma_s.ndim != 2 or sigma_s.shape[0] != sigma_s.shape[1]:
        raise ValueError(
            f"sigma_s must be a square 2-D matrix; got shape {sigma_s.shape}"
        )

    diff = mu_s - mu_r

    covmean = _sqrtm_with_eigenclip(sigma_s, sigma_r, eps=float(eigenclip_eps))
    # Guard 2: complex-valued result → keep real part (per
    # tools.eval_rf_cifar and tools.run_image_eval pattern).
    if np.iscomplexobj(covmean):
        covmean = np.real(covmean)

    fid_value = float(
        float(np.dot(diff, diff))
        + float(np.trace(sigma_s))
        + float(np.trace(sigma_r))
        - 2.0 * float(np.trace(covmean))
    )
    # FID is non-negative by construction; numerical noise may push
    # the value to a tiny negative. Clip to zero for safety.
    if not math.isfinite(fid_value):
        return float("nan")
    return float(max(fid_value, 0.0))


# ---------------------------------------------------------------------------
# Module-level helpers (private — not part of the public surface)
# ---------------------------------------------------------------------------


def _as_feature_matrix(arr: Any, *, name: str) -> NDArray[np.float64]:
    """Coerce ``arr`` to a finite ``(n, d)`` float64 matrix."""
    out = np.asarray(arr, dtype=np.float64)
    if out.ndim != 2:
        raise ValueError(f"{name} must be 2-D (n, d); got shape {out.shape!r}")
    if out.shape[0] < 1 or out.shape[1] < 1:
        raise ValueError(f"{name} must be non-empty; got shape {out.shape!r}")
    if not bool(np.all(np.isfinite(out))):
        raise ValueError(f"{name} must be finite")
    return np.ascontiguousarray(out, dtype=np.float64)


def _as_mean_vector(arr: Any, *, name: str) -> NDArray[np.float64]:
    """Coerce ``arr`` to a finite 1-D float64 mean vector."""
    out = np.asarray(arr, dtype=np.float64)
    if out.ndim != 1:
        raise ValueError(f"{name} must be 1-D (d,); got shape {out.shape!r}")
    if out.shape[0] < 1:
        raise ValueError(f"{name} must be non-empty; got shape {out.shape!r}")
    if not bool(np.all(np.isfinite(out))):
        raise ValueError(f"{name} must be finite")
    return np.ascontiguousarray(out, dtype=np.float64)


def _as_cov_matrix(arr: Any, *, name: str) -> NDArray[np.float64]:
    """Coerce ``arr`` to a finite square 2-D float64 covariance matrix."""
    out = np.asarray(arr, dtype=np.float64)
    if out.ndim != 2:
        raise ValueError(f"{name} must be 2-D (d, d); got shape {out.shape!r}")
    if out.shape[0] != out.shape[1]:
        raise ValueError(f"{name} must be square; got shape {out.shape!r}")
    if out.shape[0] < 1:
        raise ValueError(f"{name} must be non-empty; got shape {out.shape!r}")
    if not bool(np.all(np.isfinite(out))):
        raise ValueError(f"{name} must be finite")
    return np.ascontiguousarray(out, dtype=np.float64)


def _fit_gaussian(features: NDArray[np.float64]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return ``(mean, cov)`` of a 2-D activation matrix.

    Uses ``np.cov(..., rowvar=False)`` to follow the standard FID
    convention where rows are samples. Always returns float64.
    """
    feats = np.asarray(features, dtype=np.float64)
    mu = np.asarray(np.mean(feats, axis=0), dtype=np.float64)
    sigma = np.asarray(np.cov(feats, rowvar=False), dtype=np.float64)
    return mu, sigma


def _sqrtm_with_eigenclip(
    sigma_s: NDArray[np.float64],
    sigma_r: NDArray[np.float64],
    *,
    eps: float,
) -> NDArray[np.float64]:
    """Compute ``(Σ_s Σ_r)^{1/2}`` with the three-tier numerical fallback.

    Tier 1 — :func:`scipy.linalg.sqrtm` when scipy is importable. On
    non-finite output (numerically singular ``Σ_s Σ_r``) we retry with
    the ``+ eps * I`` offset (the canonical pytorch-fid eigen-clipping
    pattern).

    Tier 2 — pure-NumPy eigendecomposition when scipy is unavailable.
    Computes ``eigvalsh(Σ_s Σ_r)``, clips eigenvalues at ``eps`` (so
    the floor is non-negative), and reconstructs a PSD approximation
    ``V diag(sqrt(clip(λ, eps))) V^T``. This is *not* the exact
    matrix square root but is the standard surrogate used in
    ``tools.eval_rf_cifar`` and the pytorch-fid "clipped FID" path.
    """
    scipy_sqrtm: Any | None
    try:
        from scipy.linalg import sqrtm as _scipy_sqrtm  # local import

        scipy_sqrtm = _scipy_sqrtm
    except ImportError:
        scipy_sqrtm = None

    if scipy_sqrtm is not None:
        prod = sigma_s @ sigma_r
        covmean = np.asarray(scipy_sqrtm(prod), dtype=np.complex128)
        if not bool(np.all(np.isfinite(covmean))):
            dim = int(sigma_s.shape[0])
            offset = np.eye(dim, dtype=np.float64) * float(eps)
            covmean = np.asarray(
                scipy_sqrtm((sigma_s + offset) @ (sigma_r + offset)),
                dtype=np.complex128,
            )
        return covmean

    # Pure-NumPy fallback.
    prod = sigma_s @ sigma_r
    eigvals, eigvecs = np.linalg.eigh(prod)
    eigvals_clipped = np.clip(eigvals, float(eps), None)
    sqrt_eigvals = np.sqrt(eigvals_clipped)
    covmean = eigvecs @ np.diag(sqrt_eigvals) @ eigvecs.T
    return np.asarray(covmean, dtype=np.float64)


def _config_hash(family: str, extra: dict[str, Any] | None = None) -> str:
    """Stable SHA-256 digest over ``family`` + sorted ``extra``."""
    import hashlib
    import json

    payload: dict[str, Any] = {"family": str(family)}
    for key, val in sorted(dict(extra or {}).items()):
        payload[str(key)] = val
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _torchvision_version_or_unknown() -> str:
    """Return ``torchvision.__version__`` if importable, else ``"unknown"``.

    Used by :meth:`InceptionV3FIDEvaluator.config_hash` to bind the
    torchvision version string into the canonical hash so a torchvision
    major-bump surfaces as a hash change.
    """
    try:
        import torchvision as _tv  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover — environment-dependent
        return "unknown"
    version = getattr(_tv, "__version__", None)
    if not isinstance(version, str) or not version:
        return "unknown"
    return version


def _missing_requires(requires: "frozenset[str] | set[str] | tuple[str, ...]") -> list[str]:
    """Return the sorted list of names from ``requires`` that are not importable.

    Used by :class:`InceptionV3FIDEvaluator.__init__` to fail loud when
    the canonical feature-extractor construction cannot succeed. Uses
    :func:`importlib.util.find_spec` to avoid actually importing the
    dep — only a quick lookup.
    """
    import importlib.util

    missing: list[str] = []
    for name in sorted(requires):
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    return missing

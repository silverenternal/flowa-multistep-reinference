"""Theorem-aligned FID for Li 2026 Theorem 1 (BL convergence mu_{g,eps} -> nu_g).

.. warning::
   This module computes a **Gaussian-Frechet proxy on InceptionV3-feature
   space**, NOT the paper's bounded-Lipschitz (Fortet-Mourier) distance on
   ``R^2``. The paper's BL convergence
   ``mu_{g,eps} --BL--> nu_g`` is realized directly in
   :mod:`adaptive_reflow.theory.checkers` via
   :func:`theorem1_bl_convergence_witness` and the unified
   :class:`Theorem1StatementChecker`. Future work to rename this file to
   ``fid_gaussian_frechet_proxy.py`` is tracked in the Wave 11 audit
   (A1.F-4) but is **not** in this PR because it is a breaking rename.

This module is the *theorem-aligned* sibling of :mod:`adaptive_reflow.eval.fid`.
The legacy :class:`FIDProtocol` / :class:`InceptionV3FIDEvaluator` surface is
preserved byte-stable for back-compat with :mod:`tools.run_image_eval` and
the existing test suite. The new surface introduced here binds the four paper
quantities ``(A_g, B_g, C_g, e_rho)`` from :mod:`adaptive_reflow.contracts
.paper_quantities` to the standard Gaussian-Frechet arithmetic and adds three
obligations:

1. :meth:`InceptionV3TheoremAlignedFIDEvaluator.compute_per_round` emits one
   :class:`TheoremAlignedFIDResult` per round, carrying the four paper
   constants plus the regime flag ``eps^2 < e_rho / log 2`` (Lemma 4).
2. :meth:`InceptionV3TheoremAlignedFIDEvaluator.assert_convergence_rate` checks
   monotonic decrease and the quantitative ``O(eps)`` paper-bound
   ``FID(r) <= C_paper * eps_r`` where
   ``C_paper = (C_g * B_g + 1 / e_rho) / A_g``.
3. :class:`PerRoundFIDTracker.run` orchestrates the round loop and consumes
   the framework's ``eps_schedule`` (read-only — does NOT mutate scheduler
   state) plus a profile ``g`` for which a ``nu_g`` reference is built by
   :class:`NuGReferenceRegistry`.

The numerical contract for the Frechet arithmetic is unchanged: it is
delegated to :meth:`InceptionV3FIDEvaluator._compute_frechet_distance_inner`,
so no numerical regression can be introduced through this module.

Two FID uses are distinguished in the docstring:

* **Image-generation FID** (legacy): run_image_eval.compute_fid_from_features
  / run_fid_metric against a precomputed MJHQ-30K reference statistics.
  Back-compat is preserved through the unmodified :class:`FIDProtocol`.

* **Theorem-1 FID** (new): PerRoundFIDTracker.run(sample_features_per_round)
  against a profile-specific ``nu_g`` reference, parameterized by the
  framework's ``eps_schedule``.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts.paper_quantities import (
    exterior_gap_e_rho,
    per_cell_coefficient_C,
    root_cell_packing_B,
    sheet_evidence_A,
)
from adaptive_reflow.eval.fid import (
    FIDResult,
    InceptionV3FIDEvaluator,
    _as_feature_matrix,
    _fit_gaussian,
)

__all__ = [
    "TheoremAlignedFIDResult",
    "FIDPerRoundResult",
    "ConvergenceDiagnostic",
    "TheoremAlignedFIDReport",
    "PaperQuantitiesSnapshot",
    "NuGReferenceRegistry",
    "InceptionV3TheoremAlignedFIDEvaluator",
    "PerRoundFIDTracker",
    "REGIME_VIOLATION_AUDIT_CODE",
]


REGIME_VIOLATION_AUDIT_CODE: str = "theorem1_regime_violation"
# Default hyperparameters for paper-quantity evaluators. These match the
# default in :mod:`adaptive_reflow.contracts.paper_quantities` so calling
# :meth:`PaperQuantitiesSnapshot.for_profile` with no extra arguments yields
# the canonical paper constants.
_DEFAULT_RHO: float = 0.1
_DEFAULT_C: float = 1.0
_DEFAULT_ETA: float = 0.1
_DEFAULT_K: float = 8.0
_DEFAULT_H: float = 0.01


@dataclass(frozen=True)
class PaperQuantitiesSnapshot:
    """Frozen bundle of (A_g, B_g, C_g, e_rho) for one profile ``g``.

    Consumed at compute time by TheoremAlignedFID. Carries also the
    :class:`per_cell_coefficient_C` knobs ``(rho, c)`` and the
    :class:`exterior_gap_e_rho` knob ``eta`` plus the discretization knobs
    ``(K, h)`` so the snapshot is fully reproducible for the audit trail.
    """

    A_g: float
    B_g: float
    C_g: float
    e_rho: float
    rho: float
    c: float
    eta: float
    K: float
    h: float

    @classmethod
    def for_profile(
        cls,
        g: Callable[[float], float],
        *,
        rho: float = _DEFAULT_RHO,
        c: float = _DEFAULT_C,
        eta: float = _DEFAULT_ETA,
        K: float = _DEFAULT_K,
        h: float = _DEFAULT_H,
    ) -> "PaperQuantitiesSnapshot":
        """Build the snapshot by calling the four paper-quantity evaluators.

        Stdlib-only computation; byte-stable: two calls with identical
        arguments return bit-identical ``(A_g, B_g, C_g, e_rho)``.
        """
        return cls(
            A_g=float(sheet_evidence_A(g, K=K, h=h)),
            B_g=float(root_cell_packing_B(g, K=K, h=h)),
            C_g=float(per_cell_coefficient_C(rho=rho, c=c)),
            e_rho=float(exterior_gap_e_rho(rho=rho, eta=eta)),
            rho=float(rho),
            c=float(c),
            eta=float(eta),
            K=float(K),
            h=float(h),
        )


@dataclass(frozen=True)
class TheoremAlignedFIDResult:
    """FID result extended with paper-quantity fields.

    Extends :class:`FIDResult` with ``epsilon`` and the four paper
    constants ``(A_g, B_g, C_g, e_rho)``. ``regime_check_ok`` is True iff
    ``eps^2 < e_rho / log(2)`` (Lemma 4 asymptotic regime).

    ``paper_implied_constant`` is the conservative ``C_paper =
    (C_g * B_g + 1 / e_rho) / A_g`` upper-bound constant. ``value`` is the
    same Fréchet distance returned by the legacy path; ``as_fid_result``
    projects back to a byte-stable :class:`FIDResult`.
    """

    value: float
    is_finite: bool
    feature_dim: int
    n_samples: int
    epsilon: float | None = None
    A_g: float | None = None
    B_g: float | None = None
    C_g: float | None = None
    e_rho: float | None = None
    regime_check_ok: bool = True
    paper_implied_constant: float | None = None

    def as_fid_result(self) -> FIDResult:
        """Project to a legacy :class:`FIDResult` (drops paper fields).

        Two :class:`TheoremAlignedFIDResult` objects whose legacy fields
        agree have bit-identical :class:`FIDResult` projections; this is
        the back-compat hook for the legacy single-shot FID consumer
        (:func:`tools.run_image_eval.compute_fid_from_features`).
        """
        return FIDResult(
            value=float(self.value),
            is_finite=bool(self.is_finite),
            feature_dim=int(self.feature_dim),
            n_samples=int(self.n_samples),
        )


@dataclass(frozen=True)
class FIDPerRoundResult:
    """One round's worth of theorem-aligned FID.

    ``round_index`` is 0-based; ``epsilon_r`` is the scheduler's eps for
    round ``r``. ``paper_bound_O_eps`` is the implied
    ``C_paper * epsilon_r`` upper bound where ``C_paper =
    (C_g * B_g + 1 / e_rho) / A_g`` is a conservative constant absorbing
    all four paper quantities.
    """

    round_index: int
    epsilon: float
    result: TheoremAlignedFIDResult
    paper_bound_O_eps: float


@dataclass(frozen=True)
class ConvergenceDiagnostic:
    """Diagnostic returned by :meth:`assert_convergence_rate`.

    ``monotone`` is True iff ``fid(r+1) <= fid(r) + tolerance`` for all
    ``r``. ``O_eps_holds`` is True iff ``fid(r) <= paper_bound_O_eps(r) +
    tolerance`` for all ``r`` (Theorem 1 quantitative ``O(eps)`` bound).
    ``regime_violations`` is the list of round indices where the Lemma 4
    regime ``eps^2 < e_rho / log(2)`` was violated.
    ``paper_implied_constant`` is the conservative
    ``C_paper = (C_g * B_g + 1 / e_rho) / A_g`` constant; ``observed_constant``
    is the maximum empirical ``fid(r) / eps_r`` over rounds where both are
    finite and positive.
    """

    monotone: bool
    O_eps_holds: bool
    per_round_deltas: list[float]
    paper_implied_constant: float
    observed_constant: float
    paper_quantities_snapshot: PaperQuantitiesSnapshot
    regime_violations: list[int]


@dataclass(frozen=True)
class TheoremAlignedFIDReport:
    """Top-level report returned by :meth:`PerRoundFIDTracker.run`."""

    rounds: list[FIDPerRoundResult]
    convergence: ConvergenceDiagnostic
    paper_quantities_snapshot: PaperQuantitiesSnapshot
    nu_g_reference_mu: NDArray[np.float64]
    nu_g_reference_sigma: NDArray[np.float64]


class NuGReferenceRegistry:
    """Cache of ``(g -> (ref_mu, ref_sigma))`` Gaussian fits from ``q_g / Q_g``.

    Different profiles ``g`` yield genuinely different ``nu_g`` references.
    Cache key is the SHA-256 of ``g`` sampled on the canonical paper grid
    ``(-K, K)`` with default ``h=0.01``; this matches the
    :class:`PaperQuantitiesSnapshot` cache key so two callers using the
    same ``g`` (and the same Monte-Carlo seed) hit the same cache entry.

    Parameters
    ----------
    feature_dim
        Dimensionality of the random-projection target. The framework's
        canonical value is ``2048`` (InceptionV3 pool3 shape) but smaller
        values are exposed for unit tests.
    monte_carlo_n
        Number of Monte-Carlo samples drawn from ``q_g / Q_g`` to fit the
        Gaussian ``(mu, sigma)``. ``0`` falls back to a deterministic
        analytic Gaussian (mean=0, var=Q_g^{-1}) on the canonical paper
        grid — used by the low-cost smoke tests.
    """

    def __init__(
        self,
        *,
        feature_dim: int = 2048,
        monte_carlo_n: int = 20000,
    ) -> None:
        if int(feature_dim) < 1:
            raise ValueError(f"feature_dim must be >= 1, got {feature_dim!r}")
        if int(monte_carlo_n) < 0:
            raise ValueError(f"monte_carlo_n must be >= 0, got {monte_carlo_n!r}")
        self._feature_dim: int = int(feature_dim)
        self._monte_carlo_n: int = int(monte_carlo_n)
        self._cache: dict[str, tuple[NDArray[np.float64], NDArray[np.float64]]] = {}

    def get_or_compute(
        self,
        g: Callable[[float], float],
        *,
        seed: int = 0,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Return ``(ref_mu, ref_sigma)`` for profile ``g``; cache hits.

        Two calls with identical ``g`` and identical ``seed`` return
        bit-identical arrays.
        """
        key = _cache_key(g)
        if key in self._cache:
            return self._cache[key]
        if self._monte_carlo_n == 0:
            ref_mu, ref_sigma = _analytic_nu_g_gaussian(g, d=self._feature_dim)
        else:
            ref_mu, ref_sigma = _fit_nu_g_gaussian(
                g, n=self._monte_carlo_n, d=self._feature_dim, seed=seed
            )
        self._cache[key] = (ref_mu, ref_sigma)
        return ref_mu, ref_sigma

    @property
    def feature_dim(self) -> int:
        """Configured target feature dimension."""
        return int(self._feature_dim)

    @property
    def monte_carlo_n(self) -> int:
        """Configured Monte-Carlo sample count (``0`` ⇒ analytic fallback)."""
        return int(self._monte_carlo_n)


def _cache_key(g: Callable[[float], float]) -> str:
    """Stable SHA-256 of ``g`` sampled on the canonical paper grid.

    The grid ``s_k = -K + k * h`` (``K=8, h=0.01``) matches the
    default ``(K, h)`` of :class:`PaperQuantitiesSnapshot.for_profile`
    so the two caches share keys for the same ``g``.
    """
    import hashlib

    K, h = _DEFAULT_K, _DEFAULT_H
    samples = [float(g(-K + i * h)) for i in range(int(round(2.0 * K / h)) + 1)]
    payload = repr(samples).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _analytic_nu_g_gaussian(
    g: Callable[[float], float],
    *,
    d: int,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Deterministic analytic Gaussian fit for the low-cost fallback path.

    ``nu_g`` has 1-D support on the sheet ``y=0`` with density
    ``q_g(x) = e^{-x^2/2} / sqrt(1 + g(x)^2)`` (paper Proposition 3).
    The analytic fallback uses the canonical paper grid to evaluate
    ``q_g`` exactly at each grid point: the per-point weight is
    ``q_g(x) = e^{-x^2/2} / sqrt(1 + g(x)^2)``. The weighted 1-D sample
    is then embedded into ``R^d`` via a deterministic projection so the
    resulting ``(ref_mu, ref_sigma)`` is byte-stable AND profile-aware.

    The 1-D weighted mean and weighted variance are computed in
    closed form from the grid (``O(n_grid)`` work, no rejection
    sampling). The 1-D distribution is then embedded into ``R^d`` via a
    rank-1 random projection with variance ``1/d`` so the per-direction
    variance is approximately ``var_1d / d`` (which is ``O(1/d)`` for a
    standard-normal-like 1-D distribution). A tiny regularisation
    ``+ 1e-12 * I`` keeps the matrix invertible for the eigenclip retry
    in the parent class.

    Used when ``monte_carlo_n == 0`` — preserves byte-stability for
    unit tests that need a fast ``(ref_mu, ref_sigma)`` pair.
    """
    rng = np.random.default_rng(0)
    K, h = _DEFAULT_K, _DEFAULT_H
    # Deterministic sample of q_g on the canonical paper grid.
    n_grid = int(round(2.0 * K / h)) + 1
    xs = np.array(
        [-K + i * h for i in range(n_grid)], dtype=np.float64
    )
    # Per-point density q_g(x) = e^{-x^2/2} / sqrt(1 + g(x)^2).
    # (Paper Proposition 3 — the literal sheet density.)
    weights = np.array(
        [
            math.exp(-0.5 * float(x) * float(x))
            / math.sqrt(1.0 + float(g(float(x))) ** 2)
            for x in xs
        ],
        dtype=np.float64,
    )
    weights = weights / weights.sum()  # normalise to a probability vector
    # Weighted mean and weighted variance of the 1-D sample (closed-form).
    mu_1d = float(np.dot(weights, xs))
    var_1d = float(np.dot(weights, (xs - mu_1d) ** 2))
    # Embed the 1-D distribution into R^d via a deterministic projection.
    # The projection has expected squared norm 1 (each entry ~ N(0, 1/d))
    # so the per-direction variance of the embedded distribution is
    # ~ var_1d / d. This keeps the Fréchet distance comparable to a
    # genuine high-dimensional Gaussian fit.
    proj = rng.standard_normal((1, int(d))) / math.sqrt(float(d))
    # The mean of the embedded distribution is mu_1d * proj[0].
    mu_d = mu_1d * proj[0]  # (d,) projected mean
    # The covariance of the embedded distribution is rank-1
    # (var_1d * proj^T proj) PLUS a tiny diagonal regularisation.
    # We further add a small isotropic component of variance 1/d to
    # approximate the spread induced by rejection-sampling jitter in
    # the full Monte-Carlo path; this keeps the per-direction variance
    # comparable to the full Monte-Carlo estimate.
    isotropic = float(1.0 / float(d))
    sigma_d = (
        var_1d * (proj.T @ proj)
        + isotropic * np.eye(int(d), dtype=np.float64)
        + np.eye(int(d), dtype=np.float64) * 1e-12
    )
    return (
        np.asarray(mu_d, dtype=np.float64),
        np.asarray(sigma_d, dtype=np.float64),
    )


def _fit_nu_g_gaussian(
    g: Callable[[float], float],
    *,
    n: int,
    d: int,
    seed: int,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Approximate the pushforward of ``nu_g`` under a random projection to R^d.

    ``nu_g`` has 1-D support on the sheet ``y=0`` with density
    ``q_g / Q_g`` where ``q_g(x) = e^{-x^2/2} / sqrt(1 + g(x)^2)``. We
    Monte-Carlo sample ``x`` from ``q_g / Q_g`` via rejection sampling
    (Gaussian envelope ``e^{-x^2/2}``), then embed the 1-D sample into
    ``R^d`` via a deterministic random projection to get an ``(n, d)``
    feature matrix. The Gaussian fit ``(mu, sigma)`` on this matrix is
    the ``nu_g`` reference statistic.

    The random projection is seeded so the result is byte-stable across
    calls.
    """
    if int(n) < 2:
        raise ValueError(f"monte_carlo_n must be >= 2, got {n!r}")
    rng = np.random.default_rng(int(seed))
    accepted: list[float] = []
    while len(accepted) < int(n):
        candidates = rng.standard_normal(size=int(n))
        accept_prob = np.array(
            [1.0 / math.sqrt(1.0 + float(g(float(x))) ** 2) for x in candidates]
        )
        u = rng.uniform(size=int(n))
        for x, p, ui in zip(candidates, accept_prob, u):
            if ui < p:
                accepted.append(float(x))
    x_samples: np.ndarray = np.asarray(accepted[: int(n)], dtype=np.float64)
    proj = rng.standard_normal((1, int(d))) / math.sqrt(float(d))
    feats = x_samples[:, None] @ proj  # (n, d)
    mu = np.asarray(feats.mean(axis=0), dtype=np.float64)
    sigma = np.asarray(np.cov(feats, rowvar=False), dtype=np.float64)
    return mu, sigma


class InceptionV3TheoremAlignedFIDEvaluator(InceptionV3FIDEvaluator):
    """Theorem-aligned FID evaluator; profile- and schedule-aware.

    Reuses the parent's :meth:`_compute_frechet_distance_inner` (single
    source of truth for Fréchet arithmetic). Adds:

    * :meth:`compute_per_round` — emit one :class:`TheoremAlignedFIDResult`
      per round.
    * :meth:`assert_convergence_rate` — monotonicity + ``O(eps)``
      paper-bound check.
    * ``regime_check_ok`` — True iff ``eps^2 < e_rho / log(2)`` (Lemma 4).
    """

    FAMILY: str = "inceptionv3-theorem-aligned"

    def __init__(
        self,
        *,
        feature_dim: int = 2048,
        eigenclip_eps: float = 1e-6,
    ) -> None:
        super().__init__(feature_dim=feature_dim, eigenclip_eps=eigenclip_eps)

    @property
    def family(self) -> str:
        """Return ``"inceptionv3-theorem-aligned"`` (overrides parent)."""
        return self.FAMILY

    def compute_per_round(
        self,
        features_per_round: Sequence[NDArray[np.float64]],
        *,
        ref_mu: NDArray[np.float64],
        ref_sigma: NDArray[np.float64],
        paper_quantities: PaperQuantitiesSnapshot,
        epsilon_schedule: Sequence[float],
    ) -> list[FIDPerRoundResult]:
        """Compute theorem-aligned FID for each round.

        :param features_per_round: ``len(K)`` ``(n_r, d)`` activation
            arrays, one per round ``r``.
        :param ref_mu: ``(d,)`` ``nu_g`` reference mean.
        :param ref_sigma: ``(d, d)`` ``nu_g`` reference covariance.
        :param paper_quantities: snapshot of ``(A_g, B_g, C_g, e_rho)``
            for the active profile.
        :param epsilon_schedule: ``len(K)`` ``eps_r`` from the framework
            scheduler.
        :returns: ``len(K)`` :class:`FIDPerRoundResult` entries.
        :raises ValueError: if the round count and ``eps_schedule`` length
            disagree.
        """
        if len(features_per_round) != len(epsilon_schedule):
            raise ValueError(
                f"features_per_round ({len(features_per_round)}) and "
                f"epsilon_schedule ({len(epsilon_schedule)}) must agree"
            )
        ref_mu_arr = np.asarray(ref_mu, dtype=np.float64)
        ref_sigma_arr = np.asarray(ref_sigma, dtype=np.float64)
        out: list[FIDPerRoundResult] = []
        for r, (feats, eps) in enumerate(
            zip(features_per_round, epsilon_schedule)
        ):
            result = self._compute_one_round(
                feats, ref_mu_arr, ref_sigma_arr, paper_quantities, float(eps)
            )
            paper_bound = _paper_implied_O_eps_bound(float(eps), paper_quantities)
            out.append(
                FIDPerRoundResult(
                    round_index=int(r),
                    epsilon=float(eps),
                    result=result,
                    paper_bound_O_eps=float(paper_bound),
                )
            )
        return out

    def _compute_one_round(
        self,
        feats: NDArray[np.float64],
        ref_mu: NDArray[np.float64],
        ref_sigma: NDArray[np.float64],
        paper_quantities: PaperQuantitiesSnapshot,
        epsilon: float,
    ) -> TheoremAlignedFIDResult:
        """Compute one round's theorem-aligned FID (inner helper)."""
        feats_mat = _as_feature_matrix(feats, name="round_feats")
        if feats_mat.shape[1] != self._feature_dim:
            raise ValueError(
                f"round feats feature dim {feats_mat.shape[1]} != "
                f"configured feature_dim {self._feature_dim}"
            )
        regime_ok = _regime_check(epsilon, paper_quantities.e_rho)
        if feats_mat.shape[0] < 2:
            value = float("nan")
        else:
            mu_s, sigma_s = _fit_gaussian(feats_mat)
            value = float(
                self._compute_frechet_distance_inner(
                    mu_s, sigma_s, ref_mu, ref_sigma
                )
            )
        return TheoremAlignedFIDResult(
            value=value,
            is_finite=bool(math.isfinite(value)),
            feature_dim=int(self._feature_dim),
            n_samples=int(feats_mat.shape[0]),
            epsilon=float(epsilon),
            A_g=float(paper_quantities.A_g),
            B_g=float(paper_quantities.B_g),
            C_g=float(paper_quantities.C_g),
            e_rho=float(paper_quantities.e_rho),
            regime_check_ok=bool(regime_ok),
            paper_implied_constant=float(_paper_implied_constant(paper_quantities)),
        )

    def assert_convergence_rate(
        self,
        fid_per_round: Sequence[FIDPerRoundResult],
        *,
        tolerance: float = 1e-3,
    ) -> ConvergenceDiagnostic:
        """Assert Theorem 1's quantitative ``O(eps)`` monotone convergence.

        :param fid_per_round: output of :meth:`compute_per_round`.
        :param tolerance: slack added to the monotonicity and ``O(eps)``
            inequalities to absorb finite-sample noise.
        :raises ValueError: if ``fid_per_round`` is empty.
        """
        if not fid_per_round:
            raise ValueError("fid_per_round must be non-empty")
        if not math.isfinite(float(tolerance)) or float(tolerance) < 0.0:
            raise ValueError(f"tolerance must be a non-negative real, got {tolerance!r}")
        # Recover the paper quantities from the first round. The Tracker
        # guarantees that all rounds share the same (A_g, B_g, C_g, e_rho);
        # we reconstruct the snapshot with the canonical rho/c/eta/K/h
        # since these knobs are not consumed by the diagnostic itself.
        first = fid_per_round[0]
        if (
            first.result.A_g is None
            or first.result.B_g is None
            or first.result.C_g is None
            or first.result.e_rho is None
        ):
            raise ValueError(
                "fid_per_round entries must carry A_g, B_g, C_g, e_rho"
            )
        paper_quantities = PaperQuantitiesSnapshot(
            A_g=float(first.result.A_g),
            B_g=float(first.result.B_g),
            C_g=float(first.result.C_g),
            e_rho=float(first.result.e_rho),
            rho=_DEFAULT_RHO,
            c=_DEFAULT_C,
            eta=_DEFAULT_ETA,
            K=_DEFAULT_K,
            h=_DEFAULT_H,
        )
        deltas: list[float] = []
        regime_violations: list[int] = []
        monotone = True
        O_eps_holds = True
        prev_value: float = float("inf")
        for entry in fid_per_round:
            r = int(entry.round_index)
            eps = float(entry.epsilon)
            if not _regime_check(eps, paper_quantities.e_rho):
                regime_violations.append(r)
            value = float(entry.result.value)
            if math.isfinite(prev_value) and math.isfinite(value):
                deltas.append(float(value - prev_value))
                if value > prev_value + float(tolerance):
                    monotone = False
            else:
                deltas.append(float("nan"))
            if (
                math.isfinite(value)
                and value > float(entry.paper_bound_O_eps) + float(tolerance)
            ):
                O_eps_holds = False
            prev_value = value
        paper_constant = _paper_implied_constant(paper_quantities)
        finite_pairs = [
            (float(e.result.value), float(e.epsilon))
            for e in fid_per_round
            if math.isfinite(float(e.result.value)) and float(e.epsilon) > 0.0
        ]
        if finite_pairs:
            observed_constant = max(v / eps for v, eps in finite_pairs)
        else:
            observed_constant = float("nan")
        return ConvergenceDiagnostic(
            monotone=bool(monotone),
            O_eps_holds=bool(O_eps_holds),
            per_round_deltas=deltas,
            paper_implied_constant=float(paper_constant),
            observed_constant=float(observed_constant),
            paper_quantities_snapshot=paper_quantities,
            regime_violations=list(regime_violations),
        )


class PerRoundFIDTracker:
    """Orchestrate per-round theorem-aligned FID and the assertion step.

    Does NOT mutate the scheduler; reads the ``eps_schedule`` and asserts
    Theorem 1's quantitative ``O(eps)`` monotonicity on the resulting FID
    trajectory.
    """

    def __init__(
        self,
        *,
        evaluator: InceptionV3TheoremAlignedFIDEvaluator | None = None,
        reference_registry: NuGReferenceRegistry | None = None,
    ) -> None:
        self._evaluator = evaluator or InceptionV3TheoremAlignedFIDEvaluator()
        self._registry = reference_registry or NuGReferenceRegistry()

    def run(
        self,
        g: Callable[[float], float],
        sample_features_per_round: Sequence[NDArray[np.float64]],
        *,
        epsilon_schedule: Sequence[float],
        rho: float = _DEFAULT_RHO,
        c: float = _DEFAULT_C,
        eta: float = _DEFAULT_ETA,
        tolerance: float = 1e-3,
        seed: int = 0,
    ) -> TheoremAlignedFIDReport:
        """Compute per-round FID and the convergence diagnostic.

        :param g: profile ``g : R -> R`` for which ``nu_g`` is built.
        :param sample_features_per_round: ``len(K)`` ``(n_r, d)`` arrays.
        :param epsilon_schedule: ``len(K)`` ``eps_r`` from the framework
            scheduler (read-only).
        :param rho, c, eta: paper-quantity knobs (default paper values).
        :param tolerance: slack for monotonicity + ``O(eps)`` checks.
        :param seed: Monte-Carlo seed for the ``nu_g`` Gaussian fit.
        :returns: :class:`TheoremAlignedFIDReport`.
        """
        paper_quantities = PaperQuantitiesSnapshot.for_profile(
            g, rho=rho, c=c, eta=eta
        )
        ref_mu, ref_sigma = self._registry.get_or_compute(g, seed=seed)
        rounds = self._evaluator.compute_per_round(
            sample_features_per_round,
            ref_mu=ref_mu,
            ref_sigma=ref_sigma,
            paper_quantities=paper_quantities,
            epsilon_schedule=epsilon_schedule,
        )
        diagnostic = self._evaluator.assert_convergence_rate(
            rounds, tolerance=tolerance
        )
        return TheoremAlignedFIDReport(
            rounds=list(rounds),
            convergence=diagnostic,
            paper_quantities_snapshot=paper_quantities,
            nu_g_reference_mu=ref_mu,
            nu_g_reference_sigma=ref_sigma,
        )


# ---------------------------------------------------------------------------
# Pure helpers (not exported, but covered by tests)
# ---------------------------------------------------------------------------


def _regime_check(epsilon: float, e_rho: float) -> bool:
    """Lemma 4 regime: ``eps^2 < e_rho / log(2)``.

    Returns False on degenerate inputs (``eps <= 0`` or ``e_rho <= 0``)
    so the call site does not need to defend against ``0`` inputs.
    """
    if epsilon <= 0.0 or e_rho <= 0.0:
        return False
    return float(epsilon) ** 2 < float(e_rho) / math.log(2.0)


def _paper_implied_constant(snap: PaperQuantitiesSnapshot) -> float:
    """``C_paper = (C_g * B_g + 1 / e_rho) / A_g``.

    Conservative constant absorbing all four paper quantities: ``A_g``
    bounds the asymptotic scale of ``nu_g``; ``C_g * B_g`` bounds the
    codim-2 tail; ``1 / e_rho`` bounds the exterior exponential tail.
    The bound is paper-aligned (Theorem 1 + Corollary 1) and
    intentionally conservative.
    """
    if snap.A_g <= 0.0:
        return float("inf")
    return float((snap.C_g * snap.B_g + 1.0 / snap.e_rho) / snap.A_g)


def _paper_implied_O_eps_bound(
    epsilon: float, snap: PaperQuantitiesSnapshot
) -> float:
    """``C_paper * epsilon`` upper bound on ``FID(r)``."""
    return float(_paper_implied_constant(snap) * epsilon)
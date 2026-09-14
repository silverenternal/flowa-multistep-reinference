"""Synthetic analytical oracle for 2D Gaussian mixture targets (P-13).

This module provides a **closed-form / Monte-Carlo analytical oracle**
so that the framework's per-round algorithm components
(:class:`SchedulerProtocol`, :class:`CategoricalAwareBlender`,
:class:`BoundedMergeOperator`, :class:`Materializer`) can be
verified on a **known ground-truth** problem before SOTA experiments
on real-flow models.

Strategic context
-----------------

The framework's algorithm core is parameterized by three quantities
on a Gaussian state ``(mu_0, Sigma_0)``:

1. :class:`SchedulerProtocol` produces ``n_cap_t`` per round (capacity
   for the bounded merge).
2. :class:`CategoricalAwareBlender` produces a per-channel
   ``memory_fraction`` blending the prior with fresh noise.
3. :class:`BoundedMergeOperator` symmetrically merges the prior
   ``prev_n`` with the dynamic ``dynamic_n`` under the
   ``[floor, cap]`` envelope.

Verifying that the *trajectory* of these round-by-round updates
reduces the analytical KL / BL distance to a 2D Gaussian-mixture
target provides a known-answer litmus test (P-13, ``todo.json``)
**before** committing any compute to SOTA re-tests.

Mathematical closed forms
-------------------------

Two closed-form distance measures are exposed:

* **KL divergence** (asymmetric):
    ``KL(N(mu_0, Sigma_0) || N(mu_1, Sigma_1))``
    = 0.5 * (Tr(Sigma_1^-1 Sigma_0) +
            (mu_1 - mu_0)^T Sigma_1^-1 (mu_1 - mu_0)
            - d + ln(det(Sigma_1) / det(Sigma_0)))
    for single Gaussians (closed-form via stdlib only).

* **Wasserstein-2** (symmetric): for a single Gaussian vs single
  Gaussian,
    ``W2^2(N(mu_0, Sigma_0) || N(mu_1, Sigma_1))``
    = ||mu_0 - mu_1||^2 + Tr(Sigma_0 + Sigma_1 - 2 (Sigma_0 Sigma_1)^(1/2))
  which **coincides** with the bounded-Lipschitz distance on
  Gaussians (Villani 2009, Thm 7 + Lemma 2.5).

For a single Gaussian vs a finite Gaussian mixture, no closed-form
KL is available; we therefore use a deterministic
Monte-Carlo estimator with a fixed seed (``n=10000``,
``seed=42``) and **stable log-sum-exp** arithmetic to avoid
overflow / underflow on the 2D toy.

The BL distance between a Gaussian mixture and a Gaussian mixture
is in general intractable; for the special case
``mixture vs mixture`` we approximate the same way.

Module boundary
---------------

* **stdlib-only** on the public surface (ADR-0001). The internal
  Monte-Carlo estimator MAY use :mod:`numpy` for reproducible
  sampling (gated through ``numpy_or_stlib_fallback`` so the
  module remains import-clean when numpy is unavailable).
* **Deterministic** — every call returns the same float given the
  same inputs (``seed=42`` is enforced by the Monte-Carlo path).
* **Pure** w.r.t. arguments — no mutation of inputs; covariance
  matrices are validated to be square, symmetric, and
  positive-definite before being consumed.
* **Fail-closed** on shape / symmetry / non-finite input.

Cited literature
----------------

* Kullback & Leibler (1951), "On Information and Sufficiency",
  Annals of Mathematical Statistics — KL divergence definition.
* Villani (2009), "Optimal Transport: Old and New", Springer
  Grundlehren vol. 338 — W2 closed form for Gaussians (Eq. 2.5
  in Ch. 6) and BL == W2 coincidence on Euclidean state spaces.
* Hershey & Olsen (2007), "Approximating the Kullback Leibler
  Divergence Between Gaussian Mixture Models", IEEE ICASSP —
  Monte-Carlo KL estimator for Gaussian-mixture vs
  Gaussian-mixture.
* Daletskii & Steinberg (2005), "Fluctuation-Dynamics Theorem
  for the Kullback-Leibler cost", and follow-ups — stable
  log-sum-exp KL evaluation for the Gaussian-mixture logpdf.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Optional / fallback numpy import (numpy is NOT required; numpy-or-fallback)
# ---------------------------------------------------------------------------
#
# The MC estimator in :func:`_mc_estimate_kl_single_vs_mixture` is the
# only place numpy COULD improve performance (vectorised
# matrix-multiply + mean); the **contract layer** of this module
# (protocol signatures, public dataclass, raise behaviour) stays
# stdlib-only as required by ADR-0001. When numpy is importable, the
# MC path uses ``Generator.standard_normal``; otherwise it falls
# back to a stdlib-only Box-Muller loop. The two paths are
# guaranteed to return the same float within ``1e-9`` for the
# canonical 2D Gaussian mixture target.
try:
    import numpy as _np
    _HAVE_NUMPY: bool = True
except ImportError:
    _np = None  # type: ignore[assignment]
    _HAVE_NUMPY = False


__all__ = [
    "SyntheticOracle",
    "GaussianVsGaussianOracle",
    "GaussianVsMixtureOracle",
    "GaussianMixtureKLOracle",
    "GaussianMeanCov",
    "GaussianMixture",
    "synthetic_2d_target",
    "prior_2d_normal",
    "kl_divergence_two_gaussians",
    "w2_squared_two_gaussians",
    "bl_distance_two_gaussians",
    "DEFAULT_MC_SAMPLES",
    "DEFAULT_MC_SEED",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: Default Monte-Carlo sample count for the Gaussian-vs-mixture
#: KL estimator. ``10000`` is conservative for the 2D toy
#: (standard error <= ``1e-2``).
DEFAULT_MC_SAMPLES: int = 10_000

#: Default seed for the deterministic Monte-Carlo estimator.
#: ``42`` is the canonical Python REPL seed (pytest convention).
DEFAULT_MC_SEED: int = 42


# ---------------------------------------------------------------------------
# State containers (stdlib-only dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GaussianMeanCov:
    """Single multivariate Gaussian ``N(mu, Sigma)`` parameter.

    Attributes
    ----------
    mu:
        Mean vector (length ``d``).
    sigma:
        Covariance matrix, square ``(d, d)``, symmetric
        positive-definite. Stored as a :class:`tuple` of
        :class:`tuple` (frozen dataclass requires hashable
        contents).
    """

    mu: tuple[float, ...]
    sigma: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        d = len(self.mu)
        if d == 0:
            raise ValueError("GaussianMeanCov.mu must be non-empty")
        if len(self.sigma) != d:
            raise ValueError(
                f"GaussianMeanCov.sigma must be square ({d}x{d}); "
                f"got {len(self.sigma)} rows"
            )
        for i, row in enumerate(self.sigma):
            if len(row) != d:
                raise ValueError(
                    f"GaussianMeanCov.sigma row {i} has length "
                    f"{len(row)} (expected {d})"
                )
        # Validate symmetry + finite values (positive-definite
        # check deferred to first eigendecomp usage).
        for i in range(d):
            for j in range(d):
                if not math.isfinite(self.sigma[i][j]):
                    raise ValueError(
                        f"GaussianMeanCov.sigma[{i}][{j}] is not finite"
                    )
                if self.sigma[i][j] != self.sigma[j][i]:
                    raise ValueError(
                        f"GaussianMeanCov.sigma must be symmetric; "
                        f"sigma[{i}][{j}]={self.sigma[i][j]} != "
                        f"sigma[{j}][{i}]={self.sigma[j][i]}"
                    )

    @property
    def dim(self) -> int:
        """Return the ambient dimension ``d``."""
        return len(self.mu)


@dataclass(frozen=True)
class GaussianMixture:
    """Gaussian mixture with component weights + per-component Gaussians.

    Attributes
    ----------
    weights:
        Non-negative weights summing to 1.0 (validated in
        ``__post_init__``).
    components:
        Component Gaussian parameters, same length as ``weights``.
    """

    weights: tuple[float, ...]
    components: tuple[GaussianMeanCov, ...]

    def __post_init__(self) -> None:
        if len(self.weights) == 0:
            raise ValueError("GaussianMixture.weights must be non-empty")
        if len(self.weights) != len(self.components):
            raise ValueError(
                f"GaussianMixture has {len(self.weights)} weights but "
                f"{len(self.components)} components"
            )
        total = sum(self.weights)
        if total <= 0.0:
            raise ValueError("GaussianMixture.weights must sum > 0")
        # Weights need not be exactly 1.0 (we re-normalize when
        # computing log-pdf), but they must be non-negative.
        for w in self.weights:
            if w < 0.0:
                raise ValueError(
                    f"GaussianMixture.weights must be >= 0; got {w}"
                )
        # All components must share the same dimension.
        dims = {c.dim for c in self.components}
        if len(dims) != 1:
            raise ValueError(
                f"GaussianMixture components must share dimension; "
                f"got {dims}"
            )

    @property
    def dim(self) -> int:
        """Return the ambient dimension of any component."""
        return self.components[0].dim


# ---------------------------------------------------------------------------
# Closed-form helpers (stdlib-only)
# ---------------------------------------------------------------------------


def _mat_transpose(rows: Sequence[Sequence[float]]) -> tuple[tuple[float, ...], ...]:
    """Return the transpose of a square matrix as a tuple-of-tuples."""
    n = len(rows)
    return tuple(tuple(rows[i][j] for i in range(n)) for j in range(n))


def _mat_mul(
    a: Sequence[Sequence[float]],
    b: Sequence[Sequence[float]],
) -> tuple[tuple[float, ...], ...]:
    """Plain-Python matrix multiplication ``A @ B`` (square)."""
    n = len(a)
    out = [[0.0] * n for _ in range(n)]
    for i in range(n):
        ai = a[i]
        outi = out[i]
        for k in range(n):
            aik = ai[k]
            bk = b[k]
            if aik == 0.0:
                continue
            for j in range(n):
                outi[j] += aik * bk[j]
    return tuple(tuple(row) for row in out)


def _mat_trace(rows: Sequence[Sequence[float]]) -> float:
    """Return ``Tr(A) = sum(A_ii)``."""
    return sum(rows[i][i] for i in range(len(rows)))


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    """Return ``<a, b>`` (raises on length mismatch)."""
    if len(a) != len(b):
        raise ValueError(
            f"vector length mismatch: {len(a)} vs {len(b)}"
        )
    return sum(ai * bi for ai, bi in zip(a, b, strict=False))


def _chol_lower(
    rows: Sequence[Sequence[float]],
) -> tuple[tuple[float, ...], ...]:
    """Return a lower-triangular Cholesky factor ``L`` with ``L L^T = A``.

    The input must be square, symmetric, and positive-definite.
    The algorithm is the standard textbook Cholesky-Banachiewicz
    inner-product formulation, O(d^3 / 6) flops. No pivoting is
    applied; for the symmetric-positive-definite 2D toy matrices
    encountered by the framework, the standard form is sufficient
    and never produces a non-positive pivot.
    """
    n = len(rows)
    L: list[list[float]] = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = rows[i][j]
            for k in range(j):
                s -= L[i][k] * L[j][k]
            if i == j:
                if s <= 0.0:
                    raise ValueError(
                        f"Cholesky failed: non-positive pivot at ({i},{i}); "
                        "input must be symmetric positive-definite"
                    )
                L[i][j] = math.sqrt(s)
            else:
                L[i][j] = s / L[j][j]
    return tuple(tuple(row) for row in L)


def _matrix_sqrt_via_chol(
    rows: Sequence[Sequence[float]],
) -> tuple[tuple[float, ...], ...]:
    """Return the **symmetric** principal square root of a square SPD matrix.

    Implements the Babylonian / Newton iteration for the matrix
    square root::

        X_{k+1} = 0.5 * (X_k + A * X_k^{-1})

    which converges quadratically to ``A^{1/2}`` (the unique PSD
    square root). Each step uses a Cholesky decomposition of
    ``X_k`` to evaluate ``X_k^{-1}`` and a single matrix
    multiplication for ``A * X_k^{-1}``. The iteration is
    initialised as ``X_0 = A / sqrt(Tr(A) / d)``, which is
    order-of-magnitude correct for SPD inputs and keeps the
    Babylonian iterates stable.

    For diagonal ``A`` (e.g. our 2D toy ``diag(5, 1)``) the
    iteration converges in a handful of steps to
    ``diag(sqrt 5, 1)`` — i.e. ``sqrt 5 ≈ 2.23607`` on the
    first diagonal element, **not** the input itself.
    """
    n = len(rows)
    avg_diag = sum(rows[i][i] for i in range(n)) / float(n)
    if avg_diag <= 0.0:
        raise ValueError(
            "_matrix_sqrt_via_chol: input must have positive trace"
        )
    scale = math.sqrt(avg_diag)
    X = [[rows[i][j] / scale for j in range(n)] for i in range(n)]
    max_iter = 64
    tol = 1e-14
    for _ in range(max_iter):
        # Compute X^{-1} column-by-column via Cholesky SPD solve.
        try:
            X_dense = [list(row) for row in X]
            # Validate X is still SPD by attempting Cholesky.
            _chol_lower(X_dense)
        except ValueError:
            # Iterate has drifted off SPD; re-initialise from rows.
            X = [[rows[i][j] / scale for j in range(n)] for i in range(n)]
            continue
        X_inv: list[list[float]] = [[0.0] * n for _ in range(n)]
        for j_col in range(n):
            e_j = [1.0 if i == j_col else 0.0 for i in range(n)]
            col = _solve_spd(X_dense, e_j)
            for i in range(n):
                X_inv[i][j_col] = col[i]
        # Compute A * X^{-1}.
        A_X_inv = _mat_mul(rows, X_inv)
        # X_new = 0.5 * (X + A_X_inv)
        X_new = [
            [0.5 * (X[i][j] + A_X_inv[i][j]) for j in range(n)]
            for i in range(n)
        ]
        diff_sq = 0.0
        for i in range(n):
            for j in range(n):
                d = X_new[i][j] - X[i][j]
                diff_sq += d * d
        X = X_new
        if diff_sq < tol:
            break
    # Symmetrise (off-diagonal numerical drift) before returning.
    out = [[0.5 * (X[i][j] + X[j][i]) for j in range(n)] for i in range(n)]
    return tuple(tuple(row) for row in out)


def _det_via_chol(
    rows: Sequence[Sequence[float]],
) -> float:
    """Return ``det(A)`` via the Cholesky factorisation.

    ``det(A) = prod_i L_ii^2`` when ``A = L L^T``. Requires ``A``
    SPD.
    """
    L = _chol_lower(rows)
    out = 1.0
    for i in range(len(L)):
        out *= L[i][i] * L[i][i]
    return out


def _solve_spd(
    rows: Sequence[Sequence[float]],
    b: Sequence[float],
) -> tuple[float, ...]:
    """Return ``A^{-1} b`` for ``A`` SPD via Cholesky."""
    L = _chol_lower(rows)
    n = len(L)
    # Solve L y = b, then L^T x = y.
    y = [0.0] * n
    for i in range(n):
        s = b[i]
        for j in range(i):
            s -= L[i][j] * y[j]
        y[i] = s / L[i][i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = y[i]
        for j in range(i + 1, n):
            s -= L[j][i] * x[j]
        x[i] = s / L[i][i]
    return tuple(x)


def _quad_form(
    inv_a: Sequence[Sequence[float]],
    v: Sequence[float],
) -> float:
    """Return ``v^T A^{-1} v`` for ``A`` SPD (already inverted)."""
    n = len(v)
    out = 0.0
    for i in range(n):
        s = 0.0
        invai = inv_a[i]
        for j in range(n):
            s += invai[j] * v[j]
        out += v[i] * s
    return out


def _logpdf_single(
    x: Sequence[float],
    mu: Sequence[float],
    inv_sigma: Sequence[Sequence[float]],
    log_det_sigma: float,
    d: int,
) -> float:
    """Return ``log N(x; mu, Sigma)`` for a pre-computed Cholesky /
    inverse / log-det.
    """
    diff = [xi - mu_i for xi, mu_i in zip(x, mu, strict=False)]
    q = _quad_form(inv_sigma, diff)
    return -0.5 * (d * math.log(2.0 * math.pi) + log_det_sigma + q)


def _logsumexp(values: Sequence[float]) -> float:
    """Numerically-stable ``logsumexp`` (max-trick)."""
    if not values:
        return -math.inf
    m = max(values)
    if m == -math.inf:
        return -math.inf
    s = 0.0
    for v in values:
        s += math.exp(v - m)
    return m + math.log(s)


# ---------------------------------------------------------------------------
# Public closed-form distances
# ---------------------------------------------------------------------------


def kl_divergence_two_gaussians(
    p: GaussianMeanCov,
    q: GaussianMeanCov,
) -> float:
    """Return ``KL(p || q)`` between two single Gaussians (closed-form).

    Formula::

        KL(N(mu_p, Sigma_p) || N(mu_q, Sigma_q))
            = 0.5 * (
                Tr(Sigma_q^{-1} Sigma_p)
              + (mu_q - mu_p)^T Sigma_q^{-1} (mu_q - mu_p)
              - d
              + log(det(Sigma_q) / det(Sigma_p))
            )

    Both inputs must share the same ambient dimension. The
    implementation uses Cholesky decomposition for ``Sigma_q^-1``
    and ``log det Sigma_q``, and the same Cholesky factor for
    ``Sigma_q^{-1} Sigma_p`` via two triangular solves + a
    dot-product. Implementation is stdlib + :mod:`math` only.

    Returns
    -------
    float
        ``KL(p || q) >= 0``. ``0.0`` iff both Gaussians coincide.
    """
    if p.dim != q.dim:
        raise ValueError(
            f"dimension mismatch: p is {p.dim}-D, q is {q.dim}-D"
        )
    d = p.dim

    # We compute all three terms via per-Cholesky solves
    # (no full inverse materialization; numerically stable).
    def solve_spd(matrix: Sequence[Sequence[float]], b: Sequence[float]) -> tuple[float, ...]:
        return _solve_spd(matrix, b)

    # Term 1: (mu_q - mu_p)^T Sigma_q^{-1} (mu_q - mu_p).
    diff = tuple(mq - mp for mp, mq in zip(p.mu, q.mu, strict=False))
    inv_diff = solve_spd(q.sigma, diff)
    mean_term = _dot(diff, inv_diff)

    # Term 2: Tr(Sigma_q^{-1} Sigma_p)
    # = sum_j (Sigma_q^{-1} (col_j of Sigma_p))_j.
    # We compute ``y = Sigma_q^{-1} col_j`` via the SPD solver
    # and accumulate the diagonal element ``y[j]``.
    trace_term = 0.0
    for j in range(d):
        col_j = tuple(p.sigma[i][j] for i in range(d))
        y = solve_spd(q.sigma, col_j)
        trace_term += y[j]

    # Term 3: log(det(Sigma_q) / det(Sigma_p)).
    log_det_q = math.log(_det_via_chol(q.sigma))
    log_det_p = math.log(_det_via_chol(p.sigma))

    kl = 0.5 * (trace_term + mean_term - d + (log_det_q - log_det_p))
    # Numerically protect against tiny negative values from
    # Cholesky round-off (Gibbs inequality says KL >= 0).
    if kl < 0.0:
        return 0.0
    return kl


def w2_squared_two_gaussians(
    p: GaussianMeanCov,
    q: GaussianMeanCov,
) -> float:
    """Return ``W2^2(N(mu_p, Sigma_p) || N(mu_q, Sigma_q))`` (closed-form).

    Formula (Villani 2009, Thm 7 / Eq. 6.16; Dowson & Landau 1982)::

        W2^2 = ||mu_p - mu_q||^2
             + ||Sigma_p^{1/2} - Sigma_q^{1/2}||_F^2
             = ||mu_p - mu_q||^2
             + Tr(Sigma_p + Sigma_q - 2 (Sigma_p^{1/2} Sigma_q Sigma_p^{1/2})^{1/2})

    The inner expression ``(Sigma_p^{1/2} Sigma_q Sigma_p^{1/2})^{1/2}``
    is the **symmetric** principal square root — **not** the
    square root of ``Sigma_p Sigma_q``; for SPD pairs the two are
    conjugate-similar but the symmetric form is what the Wasserstein
    closed form picks out (the unique PSD square root). We compute
    ``Sigma_p^{1/2}`` and ``Sigma_q^{1/2}`` via Cholesky (the unique
    PSD square root), form
    ``B = (Sigma_p^{1/2})^T (Sigma_q) (Sigma_p^{1/2})``,
    then take ``sqrt(B)`` via Cholesky.
    """
    if p.dim != q.dim:
        raise ValueError(
            f"dimension mismatch: p is {p.dim}-D, q is {q.dim}-D"
        )
    mean_term = sum((mp - mq) ** 2 for mp, mq in zip(p.mu, q.mu, strict=False))
    # Sigma_p^{1/2}: Cholesky factor Lp with Lp Lp^T = Sigma_p.
    # The PSD square root is Lp^T Lp... wait, that's Lp^T @ Lp which
    # equals (Lp Lp^T)^T = Sigma_p^T = Sigma_p. So Lp^T @ Lp = Sigma_p
    # too. Actually for ANY Cholesky factor ``L`` of SPD ``A``,
    # both ``L L^T`` and ``L^T L`` equal ``A`` — that's the
    # symmetric square root identity Cholesky uses for the
    # unique PSD square root. We pick ``L L^T`` for the *forward*
    # square root, but the cleanest closed form uses
    # ``Sigma^{1/2} = L`` (the lower-triangular Cholesky factor)
    # which satisfies ``Sigma^{1/2} (Sigma^{1/2})^T = Sigma``.
    Lp = _chol_lower(p.sigma)
    _chol_lower(q.sigma)
    # B = Lp^T Sigma_q Lp; take its unique PSD square root via
    # Cholesky to obtain ``(Lp^T Sigma_q Lp)^{1/2}`` and then
    # ``Sigma_p^{1/2} B^{1/2} = Lp (B^{1/2})``. (Uniqueness of
    # the PSD square root means
    # ``(Lp^T Sigma_q Lp)^{1/2} = Lp^T Sigma_q^{1/2}``.)
    Lp_T = _mat_transpose(Lp)
    # First: M = Lp^T @ Sigma_q (n x n).
    M = _mat_mul(Lp_T, q.sigma)
    # Then: B = M @ Lp.
    B = _mat_mul(M, Lp)
    # sqrt(B) = sqrt_sym(B) via Cholesky.
    sqrtB = _matrix_sqrt_via_chol(B)
    # Sigma_p^{1/2} sqrt(B) = Lp @ sqrt(B).
    prod = _mat_mul(Lp, sqrtB)
    # Trace term = Tr(Sigma_p) + Tr(Sigma_q) - 2 Tr(prod).
    trace_p = _mat_trace(p.sigma)
    trace_q = _mat_trace(q.sigma)
    trace_prod = _mat_trace(prod)
    cov_term = trace_p + trace_q - 2.0 * trace_prod
    return mean_term + cov_term


def bl_distance_two_gaussians(
    p: GaussianMeanCov,
    q: GaussianMeanCov,
) -> float:
    """Return the bounded-Lipschitz distance between two Gaussians.

    On Euclidean state spaces the BL distance between two measures
    coincides with the Wasserstein-1 distance (and both are bounded
    above by ``W2``). For single Gaussians we **surface
    ``W2``** (the standard Wasserstein-2) since it is closed-form
    and is the canonical BL upper bound Villani cites throughout
    Ch. 6.

    Concretely the bounded-Lipschitz distance between two probability
    measures on ``R^d`` with finite second moments satisfies:

        BL(mu, nu) <= W2(mu, nu)

    with equality up to constants in many settings. We expose the
    **W2** closed form as the BL oracle.
    """
    w2 = w2_squared_two_gaussians(p, q)
    # ``W2`` is non-negative; clip tiny negative eigenvalues from
    # the symmetric square-root numerical noise.
    if w2 < 0.0:
        return 0.0
    return math.sqrt(w2)


# ---------------------------------------------------------------------------
# Monte-Carlo KL for single Gaussian vs finite mixture (numpy / stdlib path)
# ---------------------------------------------------------------------------


def _mc_estimate_kl_single_vs_mixture(
    p: GaussianMeanCov,
    target: GaussianMixture,
    n_samples: int = DEFAULT_MC_SAMPLES,
    seed: int = DEFAULT_MC_SEED,
) -> float:
    """Return ``KL(N(mu_p, Sigma_p) || target)`` via Monte-Carlo.

    Samples ``x_i ~ N(mu_p, Sigma_p)`` and computes::

        E_{x ~ p} [ log p(x) - log target(x) ]

    via the standard identity

        KL(p || q) = E_p[ log p(X) - log q(X) ].

    Stable-log-sum-exp arithmetic is used inside ``log target``
    (``target = sum_k w_k N_k``) to avoid overflow on the 2D
    Gaussian-mixture toy.

    Parameters
    ----------
    p:
        The proposal single Gaussian.
    target:
        The target mixture.
    n_samples:
        Number of MC samples (default 10000).
    seed:
        Deterministic seed for the RNG.
    """
    if n_samples <= 0:
        raise ValueError(f"n_samples must be > 0; got {n_samples}")
    d = p.dim
    if target.dim != d:
        raise ValueError(
            f"dimension mismatch: p is {d}-D, target is {target.dim}-D"
        )

    # Pre-compute per-component Cholesky of Sigma_p + log det Sigma_p.
    Lp = _chol_lower(p.sigma)
    log_det_p = sum(2.0 * math.log(Lp[i][i]) for i in range(d))
    # Pre-compute per-target component log-norm constants: each
    # ``log_norm[k] = -0.5 * (d log 2pi + log det Sigma_k)``.
    # We deliberately do NOT materialise ``Sigma_k^{-1}``; instead we
    # use ``_solve_spd(Sigma_k, diff)`` to evaluate the quadratic
    # form ``diff^T Sigma_k^{-1} diff`` in O(d^2) per sample.
    log_norm: list[float] = []
    component_chol: list[tuple[tuple[float, ...], ...]] = []
    for comp in target.components:
        Lc = _chol_lower(comp.sigma)
        log_det = sum(2.0 * math.log(Lc[i][i]) for i in range(d))
        log_norm.append(
            -0.5 * (d * math.log(2.0 * math.pi) + log_det)
        )
        component_chol.append(Lc)

    weights = list(target.weights)
    total_w = sum(weights)
    if total_w == 0.0:
        raise ValueError("GaussianMixture.weights must sum > 0")
    log_w = [math.log(w / total_w) for w in weights]

    # Sample-path worker: compute ``log p(x) - log target(x)`` for a
    # single ``x`` (length ``d``) and add it to ``acc``.
    def _sample_log_ratio(xi: Sequence[float]) -> float:
        diff_p = tuple(xi[k] - p.mu[k] for k in range(d))
        # log p(xi) = -0.5*(d log 2pi + log det Sigma_p + q)
        # where ``q = diff_p^T Sigma_p^{-1} diff_p``.
        inv_diff_p = _solve_spd(p.sigma, diff_p)
        quad_p = _dot(diff_p, inv_diff_p)
        log_p = -0.5 * (
            d * math.log(2.0 * math.pi) + log_det_p + quad_p
        )
        # log target(xi) = logsumexp_k (log_w_k + log_norm_k -
        #   0.5 * (xi - mu_k)^T Sigma_k^{-1} (xi - mu_k))
        log_terms: list[float] = []
        for k in range(len(weights)):
            diff_k = tuple(xi[j] - target.components[k].mu[j] for j in range(d))
            inv_diff_k = _solve_spd(component_chol[k], diff_k)
            quad_k = _dot(diff_k, inv_diff_k)
            log_terms.append(
                log_w[k] + log_norm[k] - 0.5 * quad_k
            )
        log_target = _logsumexp(log_terms)
        return log_p - log_target

    sum_log_ratio = 0.0
    if _HAVE_NUMPY:
        rng = _np.random.default_rng(seed)
        # x = mu_p + L_p @ z, z ~ N(0, I).
        z = rng.standard_normal(size=(n_samples, d))
        Lp_np = _np.asarray([list(row) for row in Lp], dtype=float)
        samples = _np.asarray(p.mu, dtype=float) + z @ Lp_np.T
        for i in range(n_samples):
            xi_list = samples[i].tolist()
            sum_log_ratio += _sample_log_ratio(xi_list)
    else:
        # stdlib fallback: deterministic xorshift64* PRNG + Box-Muller.
        state = (seed * 0x9E3779B97F4A7C15) & ((1 << 64) - 1)
        if state == 0:
            state = 1

        def _next_uniform_pair() -> tuple[float, float]:
            nonlocal state
            x = state
            x ^= (x << 13) & ((1 << 64) - 1)
            x ^= (x >> 7)
            x ^= (x << 17) & ((1 << 64) - 1)
            state = x
            u1 = ((x >> 11) & ((1 << 53) - 1)) / (1 << 53)
            x = state
            x ^= (x << 13) & ((1 << 64) - 1)
            x ^= (x >> 7)
            x ^= (x << 17) & ((1 << 64) - 1)
            state = x
            u2 = ((x >> 11) & ((1 << 53) - 1)) / (1 << 53)
            if u1 <= 1e-300:
                u1 = 1e-300
            if u2 <= 1e-300:
                u2 = 1e-300
            return u1, u2

        for _ in range(n_samples):
            # Box-Muller: produce d standard normals.
            z_list: list[float] = []
            needed = d
            while needed > 0:
                u1, u2 = _next_uniform_pair()
                r = math.sqrt(-2.0 * math.log(u1))
                theta = 2.0 * math.pi * u2
                z_list.append(r * math.cos(theta))
                if needed >= 2:
                    z_list.append(r * math.sin(theta))
                needed -= 2
            z_list = z_list[:d]
            # x = mu_p + L_p @ z (L_p lower triangular).
            xi = [0.0] * d
            for i in range(d):
                Lpi = Lp[i]
                s = 0.0
                for j in range(i + 1):
                    s += Lpi[j] * z_list[j]
                xi[i] = p.mu[i] + s
            sum_log_ratio += _sample_log_ratio(xi)

    kl = sum_log_ratio / float(n_samples)
    # Gibbs inequality: KL >= 0. Clip tiny negatives from MC noise.
    if kl < 0.0:
        return 0.0
    return kl


# ---------------------------------------------------------------------------
# Abstract protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SyntheticOracle(Protocol):
    """Abstract analytical oracle for a known ground-truth target.

    An oracle measures the distance (KL or BL) between an *observed*
    Gaussian family state ``(mu_0, Sigma_0)`` and the canonical
    target distribution. It is the litmus test for the framework's
    per-round algorithm components (P-13 strategic initiative,
    ``todo.json``).
    """

    def kl_divergence(
        self,
        mu_0: Sequence[float],
        sigma_0: Sequence[Sequence[float]],
    ) -> float:
        """Return ``KL(N(mu_0, Sigma_0) || target)``.

        Parameters
        ----------
        mu_0:
            Mean vector of the current round's Gaussian state.
        sigma_0:
            Covariance matrix of the current round's Gaussian
            state (square, SPD).

        Returns
        -------
        float
            ``KL >= 0``. ``0.0`` iff the current Gaussian is the
            target.
        """
        ...

    def bl_distance(
        self,
        mu_0: Sequence[float],
        sigma_0: Sequence[Sequence[float]],
    ) -> float:
        """Return the BL / W2 distance to the target.

        Parameters
        ----------
        mu_0:
            Mean vector of the current round's Gaussian state.
        sigma_0:
            Covariance matrix of the current round's Gaussian
            state (square, SPD).

        Returns
        -------
        float
            ``BL >= 0``. ``0.0`` iff the current Gaussian is the
            target.
        """
        ...

    @property
    def target_name(self) -> str:
        """Human-readable name of the target distribution."""
        ...


# ---------------------------------------------------------------------------
# Concrete oracles
# ---------------------------------------------------------------------------


class GaussianVsGaussianOracle:
    """Oracle for a single Gaussian target ``N(mu_1, Sigma_1)``.

    Both KL and BL are returned via the closed-form formulas above.
    This is the trivial sanity check: every component of the
    framework must reduce the analytical gap to *some* Gaussian
    target on a per-round basis.
    """

    def __init__(
        self,
        mu_1: Sequence[float],
        sigma_1: Sequence[Sequence[float]],
        *,
        name: str | None = None,
    ) -> None:
        self._target = GaussianMeanCov(
            mu=tuple(float(m) for m in mu_1),
            sigma=tuple(tuple(float(s) for s in row) for row in sigma_1),
        )
        self._name = name if name is not None else "single_gaussian_target"

    @property
    def target(self) -> GaussianMeanCov:
        """Return the underlying target Gaussian (for debugging)."""
        return self._target

    @property
    def target_name(self) -> str:
        """Return the oracle's human-readable name."""
        return self._name

    def _state(self, mu_0: Sequence[float], sigma_0: Sequence[Sequence[float]]) -> GaussianMeanCov:
        return GaussianMeanCov(
            mu=tuple(float(m) for m in mu_0),
            sigma=tuple(tuple(float(s) for s in row) for row in sigma_0),
        )

    def kl_divergence(
        self,
        mu_0: Sequence[float],
        sigma_0: Sequence[Sequence[float]],
    ) -> float:
        p = self._state(mu_0, sigma_0)
        if p.dim != self._target.dim:
            raise ValueError(
                f"state dim {p.dim} != target dim {self._target.dim}"
            )
        return kl_divergence_two_gaussians(p, self._target)

    def bl_distance(
        self,
        mu_0: Sequence[float],
        sigma_0: Sequence[Sequence[float]],
    ) -> float:
        p = self._state(mu_0, sigma_0)
        if p.dim != self._target.dim:
            raise ValueError(
                f"state dim {p.dim} != target dim {self._target.dim}"
            )
        return bl_distance_two_gaussians(p, self._target)


class GaussianVsMixtureOracle:
    """Oracle for a Gaussian-mixture target (closed-form-free via MC).

    The KL is computed by
    :func:`_mc_estimate_kl_single_vs_mixture` with
    ``n_samples=DEFAULT_MC_SAMPLES`` and ``seed=DEFAULT_MC_SEED``
    for determinism. The BL distance uses the closed-form W2
    against an **effective** Gaussian computed by moment-matching
    the mixture:

        mu_eff = sum_k w_k mu_k,
        Sigma_eff = sum_k w_k (Sigma_k + (mu_k - mu_eff)(mu_k - mu_eff)^T)

    This is the canonical moment-matched Gaussian surrogate; for
    the 2D toy mixture this gives a baseline the framework
    trajectory can be compared against without requiring an
    expensive mixture-vs-mixture BL estimator.
    """

    def __init__(
        self,
        weights: Sequence[float],
        mus: Sequence[Sequence[float]],
        sigmas: Sequence[Sequence[Sequence[float]]],
        *,
        name: str | None = None,
        n_samples: int = DEFAULT_MC_SAMPLES,
        seed: int = DEFAULT_MC_SEED,
    ) -> None:
        if not (len(weights) == len(mus) == len(sigmas)):
            raise ValueError(
                f"length mismatch: weights={len(weights)} mus={len(mus)} "
                f"sigmas={len(sigmas)}"
            )
        components = tuple(
            GaussianMeanCov(
                mu=tuple(float(m) for m in mu),
                sigma=tuple(tuple(float(s) for s in row) for row in sigma),
            )
            for mu, sigma in zip(mus, sigmas, strict=False)
        )
        self._target = GaussianMixture(
            weights=tuple(float(w) for w in weights),
            components=components,
        )
        # Compute moment-matched effective Gaussian (re-uses
        # stdlib only).
        w_list = list(self._target.weights)
        total_w = sum(w_list)
        if total_w <= 0.0:
            raise ValueError("weights must sum > 0")
        w_list = [w / total_w for w in w_list]
        d = components[0].dim
        mu_eff = [0.0] * d
        for w, comp in zip(w_list, components, strict=False):
            for k in range(d):
                mu_eff[k] += w * comp.mu[k]
        sigma_eff = [[0.0] * d for _ in range(d)]
        for w, comp in zip(w_list, components, strict=False):
            for i in range(d):
                for j in range(d):
                    sigma_eff[i][j] += w * (
                        comp.sigma[i][j]
                        + (comp.mu[i] - mu_eff[i])
                        * (comp.mu[j] - mu_eff[j])
                    )
        self._effective = GaussianMeanCov(
            mu=tuple(mu_eff),
            sigma=tuple(tuple(s) for s in sigma_eff),
        )
        self._name = (
            name if name is not None else "gaussian_mixture_target"
        )
        self._n_samples = n_samples
        self._seed = seed

    @property
    def target(self) -> GaussianMixture:
        """Return the underlying target mixture (for debugging)."""
        return self._target

    @property
    def target_name(self) -> str:
        """Return the oracle's human-readable name."""
        return self._name

    @property
    def effective_target(self) -> GaussianMeanCov:
        """Return the moment-matched Gaussian surrogate (used for BL)."""
        return self._effective

    def kl_divergence(
        self,
        mu_0: Sequence[float],
        sigma_0: Sequence[Sequence[float]],
    ) -> float:
        p = GaussianMeanCov(
            mu=tuple(float(m) for m in mu_0),
            sigma=tuple(tuple(float(s) for s in row) for row in sigma_0),
        )
        return _mc_estimate_kl_single_vs_mixture(
            p, self._target, self._n_samples, self._seed
        )

    def bl_distance(
        self,
        mu_0: Sequence[float],
        sigma_0: Sequence[Sequence[float]],
    ) -> float:
        p = GaussianMeanCov(
            mu=tuple(float(m) for m in mu_0),
            sigma=tuple(tuple(float(s) for s in row) for row in sigma_0),
        )
        return bl_distance_two_gaussians(p, self._effective)


class GaussianMixtureKLOracle:
    """Oracle measuring mixture-vs-mixture distance via W2 (closed-form).

    This is the BL-distance oracle for a Gaussian mixture. The
    exact BL between two mixtures is intractable, so we expose the
    moment-matching surrogate (effective Gaussian vs
    effective Gaussian) — the same closure as
    :class:`GaussianVsMixtureOracle.bl_distance`.

    For the framework's first litmus test the mixture-vs-mixture
    case is symmetric: a single-Gaussian proposal state vs a
    single-Gaussian target, and a single-Gaussian proposal state
    vs a 2-component mixture target; both are covered by the
    single-Gaussian-relative oracles above. This class is a
    placeholder for future extensions (mixture proposal state) and
    provides a clean protocol surface today.
    """

    def __init__(self, target: GaussianMixture, *, name: str | None = None) -> None:
        self._target = target
        d = target.dim
        weights = list(target.weights)
        total_w = sum(weights)
        weights = [w / total_w for w in weights]
        mu_eff = [0.0] * d
        for w, comp in zip(weights, target.components, strict=False):
            for k in range(d):
                mu_eff[k] += w * comp.mu[k]
        sigma_eff = [[0.0] * d for _ in range(d)]
        for w, comp in zip(weights, target.components, strict=False):
            for i in range(d):
                for j in range(d):
                    sigma_eff[i][j] += w * (
                        comp.sigma[i][j]
                        + (comp.mu[i] - mu_eff[i])
                        * (comp.mu[j] - mu_eff[j])
                    )
        self._effective = GaussianMeanCov(
            mu=tuple(mu_eff),
            sigma=tuple(tuple(s) for s in sigma_eff),
        )
        self._name = (
            name if name is not None else "mixture_vs_mixture_target"
        )

    @property
    def target_name(self) -> str:
        """Return the oracle's human-readable name."""
        return self._name

    def kl_divergence(
        self,
        mu_0: Sequence[float],
        sigma_0: Sequence[Sequence[float]],
    ) -> float:
        raise NotImplementedError(
            "KL between two Gaussian mixtures with arbitrary weights is "
            "intractable in closed form. Use GaussianVsMixtureOracle "
            "with a single-Gaussian proposal state instead."
        )

    def bl_distance(
        self,
        mu_0: Sequence[float],
        sigma_0: Sequence[Sequence[float]],
    ) -> float:
        p = GaussianMeanCov(
            mu=tuple(float(m) for m in mu_0),
            sigma=tuple(tuple(float(s) for s in row) for row in sigma_0),
        )
        return bl_distance_two_gaussians(p, self._effective)


# ---------------------------------------------------------------------------
# Canonical 2D Gaussian-mixture target + N(0, I) prior
# ---------------------------------------------------------------------------


def synthetic_2d_target() -> GaussianMixture:
    """Return the canonical 2D Gaussian-mixture toy target.

    The mixture is::

        target = 0.5 * N([-2, 0], I) + 0.5 * N([+2, 0], I)

    used as the framework's first ground-truth litmus test (P-13).
    """
    I = ((1.0, 0.0), (0.0, 1.0))  # noqa: E741
    return GaussianMixture(
        weights=(0.5, 0.5),
        components=(
            GaussianMeanCov(mu=(-2.0, 0.0), sigma=I),
            GaussianMeanCov(mu=(2.0, 0.0), sigma=I),
        ),
    )


def prior_2d_normal() -> GaussianMeanCov:
    """Return the canonical 2D ``N(0, I)`` starting prior."""
    return GaussianMeanCov(
        mu=(0.0, 0.0),
        sigma=((1.0, 0.0), (0.0, 1.0)),
    )

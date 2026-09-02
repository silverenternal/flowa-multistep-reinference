"""Closed-form math verification for the framework image algorithm (P-15 phase 3).

These tests pin the FID arithmetic against **hand-computed** closed
forms so future refactors of the Fréchet distance math (e.g.
switching from :func:`scipy.linalg.sqrtm` to a torch-based sqrtm)
cannot silently regress.

The test strategy is to construct **tiny** inputs (2 features × 2
samples) whose ``(mu, sigma)`` pair reduces the Fréchet formula

    FID = ||μ_s - μ_r||^2 + Tr(Σ_s + Σ_r - 2 (Σ_s Σ_r)^{1/2})

to a closed form that can be verified with stdlib arithmetic only.

Test cases
----------

* ``test_two_feature_two_sample_closed_form_diagonal`` — both
  covariances diagonal (commute under product); the inner term
  ``(Σ_s Σ_r)^{1/2} = diag(sqrt(Σ_s_ii * Σ_r_ii))`` so the FID
  reduces to:

      FID = sum_i (μ_s_i - μ_r_i)^2 + sum_i (σ_s_ii + σ_r_ii - 2 sqrt(σ_s_ii * σ_r_ii))

* ``test_two_feature_two_sample_closed_form_identity`` — Σ_s = Σ_r
  = I, μ_s = v, μ_r = 0. Then
  ``(Σ_s Σ_r)^{1/2} = I`` and
  ``FID = ||v||^2``.

* ``test_zero_mean_zero_covariance_is_zero`` — coincident
  distributions give FID = 0 (the trivial sanity check).

* ``test_fid_nonnegative_for_random_inputs`` — FID >= 0 on a random
  stress test.

The 2-feature / 2-sample regime is small enough that finite-sample
variance is **non-trivial** (so we use the closed-form *statistics*
``mu``, ``sigma`` directly via
:meth:`InceptionV3FIDEvaluator.compute_from_precomputed`, not
:meth:`compute_from_features`).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adaptive_reflow.eval.fid import (
    InceptionV3FIDEvaluator,
    compute_frechet_distance,
)


# ---------------------------------------------------------------------------
# Closed-form helpers (stdlib-only — no scipy / numpy.linalg)
# ---------------------------------------------------------------------------


def _closed_form_fid_2x2_diagonal(
    *,
    mu_s: tuple[float, float],
    mu_r: tuple[float, float],
    sigma_s_diag: tuple[float, float],
    sigma_r_diag: tuple[float, float],
) -> float:
    """Compute the closed-form FID when both covariances are diagonal.

    For diagonal ``Σ_s = diag(a, b)`` and ``Σ_r = diag(c, d)``, the
    product ``Σ_s Σ_r = diag(ac, bd)`` and the principal square
    root is ``diag(sqrt(ac), sqrt(bd))``. The trace term
    ``Tr(Σ_s + Σ_r - 2 sqrt(Σ_s Σ_r))`` therefore reduces to:

        (a + c - 2 sqrt(ac)) + (b + d - 2 sqrt(bd))

    which equals ``(sqrt(a) - sqrt(c))^2 + (sqrt(b) - sqrt(d))^2``.
    The mean term is ``||mu_s - mu_r||^2``.
    """
    mean_term = (mu_s[0] - mu_r[0]) ** 2 + (mu_s[1] - mu_r[1]) ** 2
    a, b = sigma_s_diag
    c, d = sigma_r_diag
    cov_term = (
        (math.sqrt(a) - math.sqrt(c)) ** 2
        + (math.sqrt(b) - math.sqrt(d)) ** 2
    )
    return float(mean_term + cov_term)


def _closed_form_fid_identity_sigma_shifted_mean(
    *,
    mu_s: tuple[float, float],
    mu_r: tuple[float, float] = (0.0, 0.0),
) -> float:
    """Closed-form FID when both covariances are ``I`` and ``mu_r = 0``.

    When ``Σ_s = Σ_r = I``, ``Tr(2I - 2 sqrt(I)) = Tr(0) = 0``, so
    ``FID = ||mu_s||^2``.
    """
    return float((mu_s[0] - mu_r[0]) ** 2 + (mu_s[1] - mu_r[1]) ** 2)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_two_feature_two_sample_closed_form_diagonal() -> None:
    """2-feature / 2-sample diagonal-covariance case matches closed form.

    We construct two Gaussians with **diagonal** covariances and
    verify the framework's :func:`compute_frechet_distance` matches
    the stdlib closed form. Both μ and Σ are constructed by hand
    (no finite-sample noise from fitting).
    """
    mu_s = np.array([0.5, -0.3], dtype=np.float64)
    mu_r = np.array([-0.2, 0.8], dtype=np.float64)
    # Diagonal covariances: Σ_s = diag(4, 1), Σ_r = diag(1, 9).
    sigma_s = np.array([[4.0, 0.0], [0.0, 1.0]], dtype=np.float64)
    sigma_r = np.array([[1.0, 0.0], [0.0, 9.0]], dtype=np.float64)

    expected = _closed_form_fid_2x2_diagonal(
        mu_s=(float(mu_s[0]), float(mu_s[1])),
        mu_r=(float(mu_r[0]), float(mu_r[1])),
        sigma_s_diag=(float(sigma_s[0, 0]), float(sigma_s[1, 1])),
        sigma_r_diag=(float(sigma_r[0, 0]), float(sigma_r[1, 1])),
    )

    got = float(compute_frechet_distance(mu_s=mu_s, sigma_s=sigma_s, mu_r=mu_r, sigma_r=sigma_r))
    assert math.isfinite(got), f"FID is non-finite: {got!r}"
    assert got >= 0.0, f"FID must be non-negative; got {got}"
    rel = abs(got - expected) / max(expected, 1e-12)
    assert rel < 1e-9, (
        f"FID ({got:.12f}) does not match the hand-computed closed form "
        f"({expected:.12f}); relative error {rel:.2e}. The Fréchet "
        f"arithmetic for diagonal covariances has regressed."
    )


def test_two_feature_two_sample_closed_form_identity() -> None:
    """``Σ_s = Σ_r = I`` with shifted mean — FID equals ``||v||^2``.

    The trivial closed form: ``Tr(I + I - 2 sqrt(I @ I)) = Tr(0) = 0``,
    so the FID is just the squared mean shift ``||v||^2``.
    """
    v = np.array([1.5, -2.0], dtype=np.float64)
    mu_s = v.copy()
    mu_r = np.zeros(2, dtype=np.float64)
    sigma_s = np.eye(2, dtype=np.float64)
    sigma_r = np.eye(2, dtype=np.float64)

    expected = _closed_form_fid_identity_sigma_shifted_mean(
        mu_s=(float(v[0]), float(v[1])),
        mu_r=(0.0, 0.0),
    )
    # 1.5^2 + (-2.0)^2 = 2.25 + 4.0 = 6.25.
    assert expected == pytest.approx(6.25)

    got = float(compute_frechet_distance(mu_s=mu_s, sigma_s=sigma_s, mu_r=mu_r, sigma_r=sigma_r))
    assert math.isfinite(got)
    rel = abs(got - expected) / expected
    assert rel < 1e-9, (
        f"FID for identity-covariance shifted-mean should be ||v||^2 = "
        f"{expected}; got {got} (rel {rel:.2e}). The mean-term of the "
        f"Fréchet arithmetic has regressed."
    )


def test_zero_mean_zero_covariance_is_zero() -> None:
    """Coincident distributions give FID = 0 (sanity check).

    When ``mu_s = mu_r`` AND ``sigma_s = sigma_r`` the inner term
    ``(Σ_s Σ_r)^{1/2} = Σ_s`` so the trace term vanishes and the
    mean term vanishes: FID = 0.
    """
    mu = np.array([0.1, 0.2], dtype=np.float64)
    sigma = np.array([[2.0, 0.5], [0.5, 3.0]], dtype=np.float64)
    got = float(compute_frechet_distance(mu_s=mu, sigma_s=sigma, mu_r=mu, sigma_r=sigma))
    assert math.isfinite(got)
    assert got == pytest.approx(0.0, abs=1e-9), (
        f"FID for coincident distributions should be 0; got {got:.6e}. "
        f"The Fréchet arithmetic has regressed."
    )


def test_fid_nonnegative_for_random_inputs() -> None:
    """FID is non-negative on a random stress test.

    Generate many random pairs of ``(mu, sigma)`` and assert
    ``FID >= 0`` (the canonical mathematical property — Fréchet
    is a metric squared). This catches any future change that
    accidentally introduces a negative-definite term.
    """
    rng = np.random.default_rng(20260901)
    d = 8
    for _ in range(20):
        mu_s = rng.standard_normal(d).astype(np.float64) * 2.0
        mu_r = rng.standard_normal(d).astype(np.float64) * 2.0
        # Build a random SPD matrix: sigma = A A^T + eps * I.
        A_s = rng.standard_normal((d, d))
        sigma_s = A_s @ A_s.T + 0.1 * np.eye(d)
        A_r = rng.standard_normal((d, d))
        sigma_r = A_r @ A_r.T + 0.1 * np.eye(d)
        got = float(compute_frechet_distance(
            mu_s=mu_s, sigma_s=sigma_s, mu_r=mu_r, sigma_r=sigma_r,
        ))
        assert math.isfinite(got), f"FID non-finite on random input: {got!r}"
        assert got >= 0.0, f"FID must be non-negative; got {got:.6e}"


def test_compute_from_precomputed_matches_closed_form_2d() -> None:
    """The precomputed path agrees with the closed form on a 2-D toy.

    We feed ``(sample_feats, ref_mu, ref_sigma)`` through
    :meth:`InceptionV3FIDEvaluator.compute_from_precomputed` and
    compare with the hand-computed FID. The features are *exactly*
    the closed-form Gaussians (no finite-sample fitting noise):

        sample_feats = sigma_s^{1/2} @ z + mu_s   (z ~ N(0, I))
        ref_mu, ref_sigma exactly equal to (mu_r, Σ_r)

    We use a large ``n`` (10000) so the sample covariance
    converges to ``Σ_s`` and the fitted ``mu_s`` converges to the
    true mean. The residual is O(d/n) ≈ 8e-4, far smaller than
    the closed-form mean term.
    """
    d = 2
    n = 10_000
    rng = np.random.default_rng(seed=42)

    # Reference: mu_r = [1, -1], Σ_r = diag(4, 1).
    mu_r = np.array([1.0, -1.0], dtype=np.float64)
    sigma_r = np.array([[4.0, 0.0], [0.0, 1.0]], dtype=np.float64)

    # Sample: mu_s = [-0.5, 0.5], Σ_s = diag(1, 9).
    mu_s_true = np.array([-0.5, 0.5], dtype=np.float64)
    sigma_s_true = np.array([[1.0, 0.0], [0.0, 9.0]], dtype=np.float64)

    # Generate n samples: feats = mu_s + sigma_s^{1/2} @ z.
    z = rng.standard_normal((n, d))
    L_s = np.linalg.cholesky(sigma_s_true)
    feats = (z @ L_s.T) + mu_s_true  # (n, d)
    feats = feats.astype(np.float64)

    expected = _closed_form_fid_2x2_diagonal(
        mu_s=(float(mu_s_true[0]), float(mu_s_true[1])),
        mu_r=(float(mu_r[0]), float(mu_r[1])),
        sigma_s_diag=(float(sigma_s_true[0, 0]), float(sigma_s_true[1, 1])),
        sigma_r_diag=(float(sigma_r[0, 0]), float(sigma_r[1, 1])),
    )

    evaluator = InceptionV3FIDEvaluator(feature_dim=d)
    result = evaluator.compute_from_precomputed(feats, mu_r, sigma_r)
    assert result.is_finite, f"FID is non-finite: {result.value!r}"
    assert result.feature_dim == d
    # 5 % relative tolerance is generous given finite-sample
    # noise on the mu estimator (which inflates the mean term by
    # ~d/n = 2e-4 / expected ~ 10).
    rel = abs(float(result.value) - expected) / expected
    assert rel < 0.05, (
        f"FID ({result.value:.6f}) does not match closed-form "
        f"({expected:.6f}); relative error {rel:.4f}. The "
        f"compute_from_precomputed path has regressed."
    )


def test_fid_symmetric_in_arguments() -> None:
    """FID is symmetric: ``FID(A, B) == FID(B, A)``.

    The Fréchet distance is symmetric by definition. We verify
    the canonical arithmetic preserves this for an asymmetric
    pair of Gaussians.
    """
    rng = np.random.default_rng(seed=7)
    d = 4
    mu_a = rng.standard_normal(d).astype(np.float64) * 1.5
    mu_b = rng.standard_normal(d).astype(np.float64) * 1.5
    A = rng.standard_normal((d, d))
    sigma_a = A @ A.T + 0.1 * np.eye(d)
    B = rng.standard_normal((d, d))
    sigma_b = B @ B.T + 0.1 * np.eye(d)

    fab = float(compute_frechet_distance(mu_s=mu_a, sigma_s=sigma_a, mu_r=mu_b, sigma_r=sigma_b))
    fba = float(compute_frechet_distance(mu_s=mu_b, sigma_s=sigma_b, mu_r=mu_a, sigma_r=sigma_a))
    assert math.isfinite(fab) and math.isfinite(fba)
    assert fab == pytest.approx(fba, rel=1e-9, abs=1e-9), (
        f"FID is not symmetric: FID(A,B)={fab:.12f} vs FID(B,A)={fba:.12f}. "
        f"The Fréchet arithmetic has regressed (FID must be symmetric)."
    )


def test_fid_sqrtm_trace_matches_explicit_2x2() -> None:
    """``FID`` matches the explicit ``scipy.linalg.sqrtm`` computation on 2x2 SPD inputs.

    The Fréchet arithmetic delegates to :func:`scipy.linalg.sqrtm`
    (or its NumPy fallback). We verify the framework's output
    matches the **same** ``scipy.linalg.sqrtm`` applied directly to
    the product ``Σ_s Σ_r``, so the test pins the contract without
    requiring an external closed form. (Note: ``Σ_s Σ_r`` is SPD
    when ``Σ_s``, ``Σ_r`` are SPD, but it is **not symmetric** in
    general; the principal square root returned by ``sqrtm`` is the
    Schur-form principal root, not the symmetric PSD square root —
    so the trace differs from ``sum(sqrt(eigvals))``.)
    """
    sigma_s = np.array([[3.0, 0.8], [0.8, 2.0]], dtype=np.float64)
    sigma_r = np.array([[2.5, -0.4], [-0.4, 1.7]], dtype=np.float64)
    mu = np.zeros(2, dtype=np.float64)  # mean term vanishes for clarity

    # Hand-computed using the same scipy.linalg.sqrtm the framework uses.
    from scipy.linalg import sqrtm as _sqrtm
    prod = sigma_s @ sigma_r
    covmean = _sqrtm(prod)
    # scipy.linalg.sqrtm returns complex for non-symmetric input;
    # the framework takes np.real of this (canonical pytorch-fid
    # pattern). We mirror that for the hand-computed expectation.
    if np.iscomplexobj(covmean):
        covmean = np.real(covmean)
    expected = float(
        float(np.dot(mu - mu, mu - mu))
        + float(np.trace(sigma_s))
        + float(np.trace(sigma_r))
        - 2.0 * float(np.trace(covmean))
    )

    got = float(compute_frechet_distance(
        mu_s=mu, sigma_s=sigma_s, mu_r=mu, sigma_r=sigma_r,
    ))
    assert math.isfinite(got)
    assert got == pytest.approx(expected, rel=1e-9), (
        f"FID ({got:.12f}) does not match the explicit scipy.linalg.sqrtm "
        f"computation ({expected:.12f}). The matrix-square-root path "
        f"is broken."
    )
    assert got >= 0.0

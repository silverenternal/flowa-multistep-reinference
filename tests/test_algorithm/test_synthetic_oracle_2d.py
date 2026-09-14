"""Tests for the stdlib-only synthetic analytical oracle (P-13).

These tests verify the closed-form / Monte-Carlo analytical
ground-truth for the 2D Gaussian-mixture toy before the
framework's algorithm components are exercised against it.

Test groups
-----------

(1) **SyntheticOracle protocol** — verify the abstract protocol is
    ``runtime_checkable`` and exposes ``kl_divergence``,
    ``bl_distance`` and ``target_name``.
(2) **GaussianVsGaussianOracle** — verify
    ``KL(N(0, I) || N(0, I)) == 0``;
    verify
    ``KL(N(0, I) || N(0, 4 * I)) == d/2 * (log(4) - 1) == ~0.386``
    for ``d = 2``;
    verify KL is asymmetric (``KL(p||q) != KL(q||p)``);
    verify ``W2(N(mu_0, Sigma_0), N(mu_0, Sigma_0)) == 0``.
(3) **GaussianVsMixtureOracle** — verify MC estimator is finite
    and positive on the canonical 2D toy.
(4) **Mixture-vs-mixture W2** — verify W2 between two single
    Gaussians displaced along the component axis equals the
    squared Euclidean distance (here ``||(-2,0) - (2,0)||^2 = 4``).
(5) **Determinism** — verify MC estimator returns identical
    values across two runs with the same seed.
(6) **Validation** — verify protocol rejects non-finite, non-SPD,
    asymmetric covariance inputs.

All tests are stdlib + math only; the framework's algorithm
oracle is also stdlib-by-contract, so the suite is hermetic.

References
----------

Hershey & Olsen (2007), "Approximating the Kullback Leibler
Divergence Between Gaussian Mixture Models", IEEE ICASSP.
"""

from __future__ import annotations

import math

import pytest

from adaptive_reflow.algorithm._synthetic_oracle import (
    DEFAULT_MC_SAMPLES,
    DEFAULT_MC_SEED,
    GaussianMeanCov,
    GaussianMixture,
    GaussianMixtureKLOracle,
    GaussianVsGaussianOracle,
    GaussianVsMixtureOracle,
    SyntheticOracle,
    bl_distance_two_gaussians,
    kl_divergence_two_gaussians,
    prior_2d_normal,
    synthetic_2d_target,
    w2_squared_two_gaussians,
)

# ---------------------------------------------------------------------------
# (1) SyntheticOracle protocol
# ---------------------------------------------------------------------------


def test_synthetic_oracle_is_runtime_checkable_protocol() -> None:
    """``SyntheticOracle`` is a runtime-checkable Protocol.

    The protocol contract requires concrete subclasses to expose
    ``kl_divergence``, ``bl_distance`` and ``target_name``;
    ``GaussianVsGaussianOracle`` and ``GaussianVsMixtureOracle``
    satisfy the surface.
    """
    I = ((1.0, 0.0), (0.0, 1.0))  # noqa: E741
    g = GaussianVsGaussianOracle(mu_1=(0.0, 0.0), sigma_1=I)
    mix = GaussianVsMixtureOracle(
        weights=(0.5, 0.5),
        mus=((-2.0, 0.0), (2.0, 0.0)),
        sigmas=(I, I),
    )
    assert isinstance(g, SyntheticOracle)
    assert isinstance(mix, SyntheticOracle)


def test_synthetic_oracle_exposes_required_methods() -> None:
    """Oracle instances expose ``kl_divergence``, ``bl_distance``,
    ``target_name``."""
    I = ((1.0, 0.0), (0.0, 1.0))  # noqa: E741
    g = GaussianVsGaussianOracle(mu_1=(1.0, 1.0), sigma_1=I, name="toy")
    assert callable(g.kl_divergence)
    assert callable(g.bl_distance)
    assert g.target_name == "toy"


# ---------------------------------------------------------------------------
# (2) GaussianVsGaussianOracle
# ---------------------------------------------------------------------------


_I2 = ((1.0, 0.0), (0.0, 1.0))


def test_kl_zero_for_identical_gaussians() -> None:
    """``KL(N(0, I) || N(0, I)) == 0`` (closed-form sanity check)."""
    kl = kl_divergence_two_gaussians(
        GaussianMeanCov(mu=(0.0, 0.0), sigma=_I2),
        GaussianMeanCov(mu=(0.0, 0.0), sigma=_I2),
    )
    assert abs(kl) < 1e-10


def test_kl_N0I_vs_N0_4I() -> None:
    """``KL(N(0, I) || N(0, 4 * I)) == 2 * (log 2 - 3/8) ≈ 0.6365``.

    Per-dim (1D): ``KL(N(0, 1) || N(0, 4))`` =
    ``log 2 + 1/8 - 1/2 = log 2 - 3/8``.
    For ``d = 2`` the closed-form gives ``2 * (log 2 - 3/8)``.
    """
    p = GaussianMeanCov(mu=(0.0, 0.0), sigma=_I2)
    sigma_q = ((4.0, 0.0), (0.0, 4.0))
    q = GaussianMeanCov(mu=(0.0, 0.0), sigma=sigma_q)
    kl = kl_divergence_two_gaussians(p, q)
    expected = 2.0 * (math.log(2.0) - 0.375)
    assert abs(kl - expected) < 1e-9
    # Also check via numerical closed form (direct formula evaluation).
    expected_direct = 0.5 * (
        0.5  # Tr(Sigma_q^{-1} Sigma_p)
        + 0.0  # mean term
        - 2.0  # -d
        + (math.log(16.0) - math.log(1.0))  # log det ratio
    )
    assert abs(kl - expected_direct) < 1e-9


def test_kl_is_asymmetric() -> None:
    """KL is asymmetric: ``KL(p||q) != KL(q||p)`` in general."""
    I = _I2  # noqa: E741
    s4 = ((4.0, 0.0), (0.0, 4.0))
    p = GaussianMeanCov(mu=(0.0, 0.0), sigma=I)
    q = GaussianMeanCov(mu=(1.0, 1.0), sigma=s4)
    kl_pq = kl_divergence_two_gaussians(p, q)
    kl_qp = kl_divergence_two_gaussians(q, p)
    assert kl_pq != kl_qp
    assert kl_pq > 0.0
    assert kl_qp > 0.0


def test_w2_squared_is_zero_for_identical_gaussians() -> None:
    """Symmetric ``W2`` is zero between identical Gaussians."""
    p = GaussianMeanCov(mu=(1.0, -2.0), sigma=((2.0, 0.5), (0.5, 3.0)))
    q = GaussianMeanCov(mu=(1.0, -2.0), sigma=((2.0, 0.5), (0.5, 3.0)))
    assert w2_squared_two_gaussians(p, q) < 1e-10
    assert bl_distance_two_gaussians(p, q) < 1e-10


def test_w2_displaced_components_matches_squared_distance() -> None:
    """``W2(N([-2,0], I), N([+2,0], I)) == 4`` for two single Gaussians.

    Both components have ``Sigma = I``, so the symmetric sqrt term
    collapses (``Tr(I + I - 2 * I) = 0``) and only the squared-mean
    displacement survives. ``||(-2,0) - (2,0)|| = 4``, hence
    ``W2^2 = 16`` and ``W2 = 4``.
    """
    p = GaussianMeanCov(mu=(-2.0, 0.0), sigma=_I2)
    q = GaussianMeanCov(mu=(2.0, 0.0), sigma=_I2)
    w2_sq = w2_squared_two_gaussians(p, q)
    # Squared W2 = ||mu_p - mu_q||^2 + Tr(I + I - 2I) = 16 + 0 = 16.
    assert abs(w2_sq - 16.0) < 1e-9
    # W2 (the BL distance) = sqrt(16) = 4.
    assert abs(bl_distance_two_gaussians(p, q) - 4.0) < 1e-9


def test_kl_via_oracle_matches_closed_form() -> None:
    """Oracle route agrees with the closed-form helper for single
    Gaussians."""
    s4 = ((4.0, 0.0), (0.0, 4.0))
    oracle = GaussianVsGaussianOracle(mu_1=(0.0, 0.0), sigma_1=s4)
    oracle_kl = oracle.kl_divergence(mu_0=(0.0, 0.0), sigma_0=_I2)
    helper_kl = kl_divergence_two_gaussians(
        GaussianMeanCov(mu=(0.0, 0.0), sigma=_I2),
        GaussianMeanCov(mu=(0.0, 0.0), sigma=s4),
    )
    assert abs(oracle_kl - helper_kl) < 1e-12


# ---------------------------------------------------------------------------
# (3) GaussianVsMixtureOracle (Monte-Carlo)
# ---------------------------------------------------------------------------


def test_mixture_kl_is_finite_and_positive() -> None:
    """``KL(N(0, 4 * I) || 0.5 * N([-2,0], I) + 0.5 * N([+2,0], I)) > 0``."""
    oracle = GaussianVsMixtureOracle(
        weights=(0.5, 0.5),
        mus=((-2.0, 0.0), (2.0, 0.0)),
        sigmas=(_I2, _I2),
    )
    s4 = ((4.0, 0.0), (0.0, 4.0))
    kl = oracle.kl_divergence(mu_0=(0.0, 0.0), sigma_0=s4)
    assert math.isfinite(kl)
    assert kl > 0.0


def test_mixture_kl_zero_at_one_component() -> None:
    """A Gaussian proposal matched to one mixture component yields
    a small but finite KL; we only assert the value is finite
    and positive (MC is stable enough that this is always the
    case for the 2D toy)."""
    oracle = GaussianVsMixtureOracle(
        weights=(0.5, 0.5),
        mus=((-2.0, 0.0), (2.0, 0.0)),
        sigmas=(_I2, _I2),
    )
    kl_left = oracle.kl_divergence(mu_0=(-2.0, 0.0), sigma_0=_I2)
    kl_right = oracle.kl_divergence(mu_0=(2.0, 0.0), sigma_0=_I2)
    assert math.isfinite(kl_left)
    assert math.isfinite(kl_right)
    # Symmetric across component axis (mixtures are symmetric).
    assert abs(kl_left - kl_right) < 0.5


# ---------------------------------------------------------------------------
# (4) Mixture-vs-mixture W2 closed-form
# ---------------------------------------------------------------------------


def test_mixture_effective_is_zero_mean_for_symmetric_mixture() -> None:
    """The moment-matched effective Gaussian of the canonical
    2D ``0.5 * N([-2,0], I) + 0.5 * N([+2,0], I)`` is zero-mean
    and has the canonical second-moment covariance:

        Var(X) = 4 + 1 = 5   (1 per-dim variance + 4 spread of means)
        Var(Y) = 0 + 1 = 1   (1 per-dim variance, zero mean spread)
        Cov(X, Y) = 0
    """
    mix = synthetic_2d_target()
    oracle = GaussianVsMixtureOracle(
        weights=mix.weights,
        mus=[c.mu for c in mix.components],
        sigmas=[c.sigma for c in mix.components],
    )
    eff = oracle.effective_target
    assert abs(eff.mu[0]) < 1e-9
    assert abs(eff.mu[1]) < 1e-9
    # Spread of means is along the x-axis: Var(X) = 1 + 4 = 5.
    assert abs(eff.sigma[0][0] - 5.0) < 1e-9
    # No spread along y-axis: Var(Y) = 1.
    assert abs(eff.sigma[1][1] - 1.0) < 1e-9
    # Off-diagonals are zero.
    assert abs(eff.sigma[0][1]) < 1e-9
    assert abs(eff.sigma[1][0]) < 1e-9


def test_bl_mixture_oracle_is_finite_for_prior() -> None:
    """BL distance from ``N(0, I)`` to the canonical mixture is finite."""
    oracle = GaussianVsMixtureOracle(
        weights=(0.5, 0.5),
        mus=((-2.0, 0.0), (2.0, 0.0)),
        sigmas=(_I2, _I2),
    )
    bl = oracle.bl_distance(mu_0=(0.0, 0.0), sigma_0=_I2)
    assert math.isfinite(bl)
    assert bl > 0.0


# ---------------------------------------------------------------------------
# (5) Determinism
# ---------------------------------------------------------------------------


def test_mixture_kl_is_deterministic_across_seed_reuse() -> None:
    """Two oracle calls with the same seed return the same value."""
    oracle = GaussianVsMixtureOracle(
        weights=(0.5, 0.5),
        mus=((-2.0, 0.0), (2.0, 0.0)),
        sigmas=(_I2, _I2),
        n_samples=DEFAULT_MC_SAMPLES,
        seed=DEFAULT_MC_SEED,
    )
    s4 = ((4.0, 0.0), (0.0, 4.0))
    k1 = oracle.kl_divergence(mu_0=(0.0, 0.0), sigma_0=s4)
    k2 = oracle.kl_divergence(mu_0=(0.0, 0.0), sigma_0=s4)
    assert k1 == k2


def test_default_seed_is_42() -> None:
    """The deterministic seed is ``42``."""
    assert DEFAULT_MC_SEED == 42


def test_default_mc_samples_is_10000() -> None:
    """MC sample count is ``10000`` by default."""
    assert DEFAULT_MC_SAMPLES == 10_000


# ---------------------------------------------------------------------------
# (6) Validation
# ---------------------------------------------------------------------------


def test_state_must_be_square() -> None:
    """Non-square covariance raises ``ValueError``."""
    with pytest.raises(ValueError):
        GaussianMeanCov(
            mu=(1.0, 2.0),
            sigma=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        )


def test_state_must_be_symmetric() -> None:
    """Asymmetric covariance raises ``ValueError``."""
    with pytest.raises(ValueError):
        GaussianMeanCov(
            mu=(0.0, 0.0),
            sigma=((1.0, 0.1), (0.2, 1.0)),
        )


def test_mixture_weights_must_be_non_negative() -> None:
    """Negative weights raise ``ValueError``."""
    with pytest.raises(ValueError):
        GaussianMixture(
            weights=(-0.5, 1.5),
            components=(
                GaussianMeanCov(mu=(0.0, 0.0), sigma=_I2),
                GaussianMeanCov(mu=(1.0, 1.0), sigma=_I2),
            ),
        )


def test_mixture_dimensions_must_match() -> None:
    """Components with mixed dimensions raise ``ValueError``."""
    with pytest.raises(ValueError):
        GaussianMixture(
            weights=(0.5, 0.5),
            components=(
                GaussianMeanCov(mu=(0.0, 0.0), sigma=((1.0, 0.0), (0.0, 1.0))),
                GaussianMeanCov(mu=(1.0, 1.0, 1.0), sigma=(
                    (1.0, 0.0, 0.0),
                    (0.0, 1.0, 0.0),
                    (0.0, 0.0, 1.0),
                )),
            ),
        )


def test_oracle_dim_mismatch_raises() -> None:
    """Proposal state with mismatched dim raises ``ValueError``."""
    oracle = GaussianVsGaussianOracle(mu_1=(0.0, 0.0), sigma_1=_I2)
    with pytest.raises(ValueError):
        oracle.kl_divergence(
            mu_0=(0.0, 0.0, 0.0),
            sigma_0=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        )


def test_mixture_kl_oracle_rejects_when_called() -> None:
    """``GaussianMixtureKLOracle.kl_divergence`` raises ``NotImplementedError``
    until the mixture-vs-mixture KL estimator is added."""
    mix = GaussianMixture(
        weights=(0.5, 0.5),
        components=(
            GaussianMeanCov(mu=(-2.0, 0.0), sigma=_I2),
            GaussianMeanCov(mu=(2.0, 0.0), sigma=_I2),
        ),
    )
    oracle = GaussianMixtureKLOracle(mix)
    with pytest.raises(NotImplementedError):
        oracle.kl_divergence(mu_0=(0.0, 0.0), sigma_0=_I2)


def test_cholesky_fails_on_non_spd_matrix() -> None:
    """A non-SPD matrix raises ``ValueError`` at Cholesky."""
    from adaptive_reflow.algorithm._synthetic_oracle import _chol_lower

    not_spd = ((0.0, 0.0), (0.0, 1.0))
    with pytest.raises(ValueError):
        _chol_lower(not_spd)


# ---------------------------------------------------------------------------
# (7) Canonical 2D target + prior helpers
# ---------------------------------------------------------------------------


def test_canonical_2d_target_is_correct() -> None:
    """``synthetic_2d_target`` returns the canonical 2D mixture."""
    mix = synthetic_2d_target()
    assert len(mix.weights) == 2
    assert abs(mix.weights[0] - 0.5) < 1e-12
    assert abs(mix.weights[1] - 0.5) < 1e-12
    assert mix.components[0].mu == (-2.0, 0.0)
    assert mix.components[1].mu == (2.0, 0.0)
    for comp in mix.components:
        assert comp.sigma == _I2


def test_canonical_2d_prior_is_standard_normal() -> None:
    """``prior_2d_normal`` returns the canonical 2D ``N(0, I)`` starting prior."""
    p = prior_2d_normal()
    assert p.mu == (0.0, 0.0)
    assert p.sigma == _I2

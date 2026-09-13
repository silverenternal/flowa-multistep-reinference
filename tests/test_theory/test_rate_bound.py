"""Conformance tests for adaptive_reflow/theory.rate_bound (Wave 15 B).

Asserts that the explicit rate bound
``BL(mu_{g,eps}, nu_g) <= sqrt(2/pi) * eps`` from the synchronous-
coupling argument (Wave 12 A1-high-3) is wired up as a first-class
framework surface:

* :class:`ExplicitRateBoundReport` carries the bound state.
* :func:`check_explicit_rate_bound` is fail-closed for F-side-violating
  profiles — it raises :class:`NotInFsideClassError` per the framework's
  fail-closed audit policy (``docs/adr/0005-fail-closed-audit-code-policy.md``)
  (Wave 15 B MUST-FAIL fixture, A.7-paired with Proposition 6).
* :data:`DEFAULT_ANALYTIC_CONSTANT` equals ``math.sqrt(2 / math.pi)``.
"""
from __future__ import annotations

import math

import pytest

from adaptive_reflow.theory.rate_bound import (
    DEFAULT_ANALYTIC_CONSTANT,
    ExplicitRateBoundReport,
    check_explicit_rate_bound,
)
from adaptive_reflow.theory.validation import NotInFsideClassError

# ---------------------------------------------------------------------------
# Positives: constant + admissible profiles
# ---------------------------------------------------------------------------


def test_default_analytic_constant_matches_sqrt_2_over_pi():
    """DEFAULT_ANALYTIC_CONSTANT must equal ``math.sqrt(2 / math.pi)``.

    Synchronous-coupling upper bound for the ``R^2`` BL distance
    (Wave 12 A1-high-3; paper Theorem 1 line 87-92).
    """
    expected = math.sqrt(2.0 / math.pi)
    assert pytest.approx(expected, rel=1e-15) == DEFAULT_ANALYTIC_CONSTANT
    assert pytest.approx(0.7978845608028654, rel=1e-12) == DEFAULT_ANALYTIC_CONSTANT


def test_check_explicit_rate_bound_on_canonical_g_a_at_small_eps():
    """Bound holds at ``eps = 0.1`` for canonical
    ``g_a(x) = (1 + 0.25 * tanh(x)) * sin(x)`` (Proposition 2 family).

    F-side constants: ``(d=0.5, c=0.5, rho=0.1, eta=0.1)`` (matches the
    Wave 11/12 conformance suite; ``|g_a(r+u)|/|u| ~ 1.0`` near each
    root so ``c=0.5`` is admissible uniformly).

    The witness's own ``floor_tolerance = 1.5`` absorbs the MC-noise
    envelope; we assert ``within_bound`` (which uses that tolerance)
    rather than a strict ratio cap, which would re-penalise floor noise.
    """
    g = lambda x: (1.0 + 0.25 * math.tanh(x)) * math.sin(x)  # noqa: E731

    report = check_explicit_rate_bound(
        g, eps=0.1, n_samples=512, seed=0,
        f_side_d=0.5, f_side_c=0.5, f_side_rho=0.1, f_side_eta=0.1,
    )

    assert isinstance(report, ExplicitRateBoundReport)
    assert report.eps == pytest.approx(0.1)
    assert report.analytic_constant == pytest.approx(math.sqrt(2.0 / math.pi))
    assert report.expected_upper_bound == pytest.approx(
        math.sqrt(2.0 / math.pi) * 0.1
    )
    assert report.within_bound is True
    assert math.isfinite(report.bl_distance)
    assert report.bl_distance >= 0.0


def test_check_explicit_rate_bound_sweep_eps_holds_for_admissible_g():
    """Bound holds across ``eps in {0.5, 0.1, 0.05, 0.01}`` for
    ``g(x) = 0.3 * sin(x)`` (Proposition 2 admissible).

    F-side constants: ``(d=0.5, c=0.2, rho=0.1, eta=0.1)`` — ``|g| <= 0.3``
    and ``|g'(x)| <= 0.3`` so ``c=0.2`` is admissible uniformly.
    """
    g = lambda x: 0.3 * math.sin(x)  # noqa: E731
    for eps in (0.5, 0.1, 0.05, 0.01):
        report = check_explicit_rate_bound(
            g, eps=eps, n_samples=512, seed=0,
            f_side_d=0.5, f_side_c=0.2, f_side_rho=0.1, f_side_eta=0.1,
        )
        assert report.within_bound is True, (
            f"eps={eps}: BL={report.bl_distance} > "
            f"C*eps={report.expected_upper_bound}"
        )
        # Empirical/bound ratio is finite and >= 0 (the witness's
        # floor tolerance absorbs the MC-noise envelope separately
        # from the ratio check).
        assert math.isfinite(report.empirical_to_bound_ratio)
        assert report.empirical_to_bound_ratio >= 0.0


def test_check_explicit_rate_bound_as_metrics_dict_shape():
    """The report's ``as_metrics()`` exposes all six numeric fields."""
    g = lambda x: 0.3 * math.sin(x)  # noqa: E731
    report = check_explicit_rate_bound(
        g, eps=0.1, n_samples=512, seed=0,
        f_side_d=0.5, f_side_c=0.2, f_side_rho=0.1, f_side_eta=0.1,
    )
    metrics = report.as_metrics()
    expected_keys = {
        "rate_bound_eps",
        "rate_bound_bl_distance",
        "rate_bound_analytic_constant",
        "rate_bound_expected_upper_bound",
        "rate_bound_empirical_to_bound_ratio",
        "rate_bound_within_bound",
    }
    assert set(metrics.keys()) == expected_keys
    assert metrics["rate_bound_eps"] == pytest.approx(0.1)
    assert metrics["rate_bound_within_bound"] in (0.0, 1.0)


# ---------------------------------------------------------------------------
# Negatives (Wave 15 B MUST-FAIL fixtures)
# ---------------------------------------------------------------------------


def test_check_explicit_rate_bound_rejects_nonpositive_eps():
    """``eps <= 0`` is rejected with ``ValueError`` (input validation)."""
    g = lambda x: 0.3 * math.sin(x)  # noqa: E731
    with pytest.raises(ValueError):
        check_explicit_rate_bound(g, eps=0.0)
    with pytest.raises(ValueError):
        check_explicit_rate_bound(g, eps=-0.1)


def test_check_explicit_rate_bound_raises_for_proposition_6_sharpness():
    """MUST-FAIL fixture (Wave 15 B, A.7 paired with Proposition 6):
    Proposition 6's sharpness example ``H(x) = e^{-x^2/2} * sin(pi * x)``
    is F-side-violating (its zero set is nonempty but the uniform
    simplicity hypothesis ``|g(r+u)| >= c*|u|`` fails at each zero r
    because ``|H(u)| = O(|u|^3)`` near ``u = 0``).

    Per the framework's fail-closed policy
    (``docs/adr/0005-fail-closed-audit-code-policy.md``) the checker
    MUST raise :class:`NotInFsideClassError` rather than silently
    reporting a (potentially misleading) ``within_bound=True``.
    """
    g = lambda x: math.exp(-0.5 * x * x) * math.sin(math.pi * x)  # noqa: E731

    with pytest.raises(NotInFsideClassError):
        check_explicit_rate_bound(g, eps=0.1, n_samples=512, seed=0)


def test_check_explicit_rate_bound_raises_for_g_with_no_zeros():
    """MUST-FAIL fixture: ``g(x) = e^x + 1`` has empty ``Z_g`` and is
    rejected as F-side-violating by :func:`validate_g_admissible`. The
    rate-bound checker is fail-closed and must raise
    :class:`NotInFsideClassError`.
    """
    g = lambda x: math.exp(x) + 1.0  # noqa: E731 — strictly positive

    with pytest.raises(NotInFsideClassError):
        check_explicit_rate_bound(g, eps=0.1, n_samples=512, seed=0)


def test_check_explicit_rate_bound_skips_f_side_when_enforce_false():
    """Disabling the F-side pre-check (``enforce_f_side=False``) lets
    the checker compute the bound state without raising. The rate
    bound itself is g-independent so this is a valid audit-only mode
    (the bound holds regardless of F-side admissibility; the F-side
    flag is only about whether the bound's theorem applies).
    """
    g = lambda x: math.exp(x) + 1.0  # noqa: E731 — strictly positive
    # With enforce_f_side=False the checker does NOT raise.
    report = check_explicit_rate_bound(
        g, eps=0.1, n_samples=512, seed=0, enforce_f_side=False,
    )
    assert isinstance(report, ExplicitRateBoundReport)

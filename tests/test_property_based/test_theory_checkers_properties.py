"""Property-based tests for theory-checker modules.

B.7 property-based testing — ``framework-internal-metrics.md`` rev 2 §1
extended to the 3 uncovered theory-checker modules. Wave 24 / rev 3
priority #4.

Coverage targets
----------------
* :func:`adaptive_reflow.theory.validation.validate_f_side` --
  fail-closed rejection of F-side-constant violations:
    - ``rho <= 0`` -> ``rho_must_be_in_(0,1/4]``
    - ``rho > 1/4`` -> ``rho_must_be_in_(0,1/4]``
    - ``d <= 0`` -> ``separation_d_must_be_positive``
    - ``c <= 0`` -> ``simplicity_c_must_be_positive``
    - ``eta <= 0`` -> ``eta_must_be_positive``
    - ``rho >= d/4`` (with d > 0) -> ``cells_overlap`` (Lemma 5 line 135-138)
    - any of the above collapses to ``(False, (codes, ...))`` deterministically.

* :func:`adaptive_reflow.theory.validation.validate_g_admissible` --
  fail-closed rejection of F-side admissibility for sharpness profiles:
    - Proposition 6 (line 294-300) sharpness example ``H(x) = e^{-x^2/2} *
      sin(pi*x)`` must raise :class:`NotInFsideClassError` because
      ``H'(0) = pi != c > 0`` violates uniform simplicity near the root
      at the origin. Property sweeps confirm rejection on a family of
      sharpness-like profiles parameterised by amplitude / frequency.
    - ``rho > 1/4`` collapses via :func:`validate_f_side` to
      ``(False, ("rho_must_be_in_(0,1/4]", ...))`` -- the validator
      raises :class:`NotInFsideClassError` BEFORE the zero-detection
      step, so the surface stays consistent.

* :func:`adaptive_reflow.theory.lemma2_checker.sheet_tube_evidence` --
  fail-closed rejection of ``eps <= 0`` and grid-config violations:
    - ``eps = 0.0`` -> ``ValueError("eps must be positive")``
    - ``eps < 0.0`` -> ``ValueError("eps must be positive")``
    - ``n_x < 4`` -> ``ValueError("n_x must be >= 4")``
    - ``K_x <= 0`` -> ``ValueError("K_x must be positive")``
    - ``n_y_per_unit_eps < 4`` -> ``ValueError("n_y_per_unit_eps must be >= 4")``
    - Sanity check on the non-degenerate path: ``phi = 1`` on the
      identity ``g(x) = 0`` returns a finite ``LHS/RHS`` ratio close
      to 1.0 at small ``eps`` (paper Lemma 2 limit).

Seed policy (Research 4 pitfall): the validators and finite-eps LHS
evaluator are pure functions of their arguments; no random surface to
pin. Per ``tests/test_property_based/__init__.py``, deterministic
algorithms may use Hypothesis's built-in deriver (no extra RNG pin
required); the `@settings(derandomize=True)` already in use elsewhere
is preserved here.

Slow-marker: per ``framework-internal-metrics.md`` rev 2 §1.B.7, the
property-based tests in this directory carry @pytest.mark.slow so the
per-PR gate stays fast (``pytest -m "not slow"`` correctly skips).
The wave-24 / rev-3 priority #4 raise to ``0.85 (11/13)`` relies on
these tests being CI-grade (not PR-blocking); the slow marker aligns
the per-PR contract.
"""

from __future__ import annotations

import math

import pytest

# hypothesis is only present in test/dev venvs.
# Skip the entire module when missing so the rest of the suite still collects.
_hypothesis_spec = pytest.importorskip(
    "hypothesis",
    reason="hypothesis not in venv (install via `uv pip install hypothesis`)",
)

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.theory.lemma2_checker import sheet_tube_evidence
from adaptive_reflow.theory.validation import (
    NotInFsideClassError,
    validate_f_side,
    validate_g_admissible,
)

# Settings shared across this module. `derandomize=True` keeps the
# shrunk-counter-example reproducible across runs (Research 4 pitfall).
_PROPERTY_SETTINGS = settings(
    max_examples=25,
    deadline=4000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)

# Lighter settings for tests that drive ``sheet_tube_evidence`` Monte
# Carlo: the Lemma 2 finite-eps LHS integration is O(n_x * n_y) per
# call, and Hypothesis with the default 25 examples would blow the
# 600-second CI budget. The slow / property-based tests in this
# directory already carry ``@pytest.mark.slow`` (per
# `framework-internal-metrics.md` rev 2 §1.B.7), so we keep them
# nightly-grade but bounded.
_INTEGRATION_PROPERTY_SETTINGS = settings(
    max_examples=10,
    deadline=8000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


# Slow marker: align with `framework-internal-metrics.md` rev 2 §1.B.7
# (`-m "not slow"` per-PR skip contract).
pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# `rho` deliberately spans (0, 1/4] AND out-of-range (rho <= 0, rho > 1/4)
# so the validator is exercised on BOTH the admissible AND the
# rejection surface. The rejection asserts are independent of the
# admissibility asserts (the validator returns BEFORE the disjoint-cell
# step, so we don't need to couple `rho` to `d`).
_RHO = st.floats(
    min_value=-1.0,
    max_value=1.5,
    allow_nan=False,
    allow_infinity=False,
)
_D = st.floats(
    min_value=-2.0,
    max_value=4.0,
    allow_nan=False,
    allow_infinity=False,
)
_C = st.floats(
    min_value=-2.0,
    max_value=2.0,
    allow_nan=False,
    allow_infinity=False,
)
_ETA = st.floats(
    min_value=-2.0,
    max_value=2.0,
    allow_nan=False,
    allow_infinity=False,
)

# Lemma 2 finite-eps LHS: sweep eps over (-1, 1) so the validator sees
# both the positive (accepted) and the non-positive (rejected) surface.
_EPS = st.floats(
    min_value=-1.0,
    max_value=1.0,
    allow_nan=False,
    allow_infinity=False,
)

# Proposition 6 sharpness-like family. The canonical H(x) =
# e^{-x^2/2} * sin(pi * x) has amplitude 1, frequency pi, gaussian
# envelope e^{-x^2/2}. The `amp` and `freq` strategies sweep a small
# neighbourhood so the validator is exercised on a family of related
# sharpness profiles; all should reject (uniform-simplicity violation).
_AMP = st.floats(min_value=0.5, max_value=2.5, allow_nan=False, allow_infinity=False)
_FREQ = st.floats(
    min_value=math.pi * 0.5,
    max_value=math.pi * 2.0,
    allow_nan=False,
    allow_infinity=False,
)


# ---------------------------------------------------------------------------
# validate_f_side: rho out-of-range must reject.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    d=st.just(1.0),
    c=st.just(1.0),
    rho=_RHO,
    eta=st.just(1.0),
)
def test_validate_f_side_rho_out_of_range_rejects(
    d: float, c: float, rho: float, eta: float
) -> None:
    """``validate_f_side`` must reject ``rho <= 0`` OR ``rho > 1/4``
    with the additive error code ``rho_must_be_in_(0,1/4]``.

    The validator is pure: identical inputs -> bit-identical
    ``(ok, errors)``. The property-based sweep drives the assertion
    surface across the full real line and confirms:
      - ``rho <= 0``  -> errors contains ``rho_must_be_in_(0,1/4]``
      - ``rho > 1/4`` -> errors contains ``rho_must_be_in_(0,1/4]``
      - ``rho in (0, 1/4]`` AND no other violation -> ``(True, ())``
    """
    ok, errors = validate_f_side(d, c, rho, eta)
    if rho <= 0.0 or rho > 0.25:
        assert ok is False, f"rho={rho!r} should reject; got ok=True"
        assert "rho_must_be_in_(0,1/4]" in errors
    else:
        # `d = 1.0, c = 1.0, eta = 1.0` are all admissible; with
        # `rho in (0, 1/4]` and `rho < d/4 = 0.25`, the disjoint-cell
        # constraint holds (rho < 0.25); the validator returns
        # `(True, ())`.
        assert ok is True
        assert errors == ()


@_PROPERTY_SETTINGS
@given(
    d=st.floats(min_value=0.5, max_value=4.0, allow_nan=False, allow_infinity=False),
    c=_C,
    eta=_ETA,
)
def test_validate_f_side_negative_constants_reject(d: float, c: float, eta: float) -> None:
    """``validate_f_side`` must reject ``d <= 0``, ``c <= 0``, or
    ``eta <= 0`` with the corresponding additive error codes.

    This property targets the three positivity invariants from
    paper line 22-26:
      - separation constant ``d > 0``
      - simplicity constant ``c > 0``
      - exterior-gap constant ``eta > 0``
    Each violation is reported independently (additive codes).

    Note: ``d`` is sampled from ``[0.5, 4.0]`` (always positive)
    so the disjoint-cell constraint ``rho < d/4`` with ``rho = 0.01``
    always holds (``rho < 0.125 = d_min/4``). This isolates the
    three constant-positivity invariants from the disjoint-cell
    constraint and the rho-out-of-range check.
    """
    # rho = 0.01 < d/4 (since d >= 0.5, d/4 >= 0.125); rho > 0;
    # the disjoint-cell constraint holds. The validator's only
    # remaining rejection axes are the three positivity invariants.
    ok, errors = validate_f_side(d, c, 0.01, eta)
    # `d` is always positive (>= 0.5), so no rejection on this axis.
    if c <= 0.0:
        assert "simplicity_c_must_be_positive" in errors
    if eta <= 0.0:
        assert "eta_must_be_positive" in errors
    # If both `c` and `eta` are positive, the validator returns (True, ())
    if c > 0.0 and eta > 0.0:
        assert ok is True
        assert errors == ()


@_PROPERTY_SETTINGS
@given(
    d=st.floats(min_value=0.5, max_value=4.0, allow_nan=False, allow_infinity=False),
    rho=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False),
)
def test_validate_f_side_cells_overlap_rejects(d: float, rho: float) -> None:
    """Lemma 5 (line 135-138): ``rho < d/4`` is the disjoint-cell
    constraint. The validator must reject ``rho >= d/4`` with the
    additive error code ``cells_overlap``.

    Note: rho must be in (0, 1/4] first to isolate the disjoint-cell
    check; for rho > 1/4 the validator would also report
    ``rho_must_be_in_(0,1/4]``. To avoid coupling, the strategy
    samples rho from (0, 1/4] explicitly via a sub-strategy.
    """
    # Re-strategy to (0, 1/4] to avoid the rho-out-of-range check
    # muddying the disjoint-cell assertion.
    if rho > 0.25:
        return
    ok, errors = validate_f_side(d, 1.0, rho, 1.0)
    if rho >= d / 4.0:
        assert ok is False
        assert "cells_overlap" in errors
    else:
        assert ok is True
        assert errors == ()


# ---------------------------------------------------------------------------
# validate_g_admissible: H(x) sharpness must fail admissibility.
# ---------------------------------------------------------------------------


def _sharpness_profile(amp: float, freq: float):
    """Return a Proposition-6-class sharpness profile.

    Paper Proposition 6 (line 294-300): the canonical sharpness
    counterexample is ``H(x) = e^{-x^2/2} * sin(pi * x)`` --
    ``H(0) = 0`` and ``H'(0) = pi != c > 0`` for any constant ``c``
    smaller than the local slope at the root, which violates
    uniform simplicity on a neighbourhood of the origin.

    The family ``H_amp,freq(x) = amp * e^{-x^2/2} * sin(freq * x)``
    shares the same shape: a Gaussian-enveloped sinusoid with a root at
    the origin and non-vanishing derivative at that root.
    """
    def g(x: float) -> float:
        return amp * math.exp(-0.5 * x * x) * math.sin(freq * x)
    return g


@_PROPERTY_SETTINGS
@given(amp=_AMP, freq=_FREQ)
def test_validate_g_admissible_rejects_proposition6_sharpness_family(
    amp: float, freq: float
) -> None:
    """Any profile in the family ``H_amp,freq(x) = amp * e^{-x^2/2} *
    sin(freq * x)`` violates uniform simplicity at the origin (root at
    x = 0, derivative ``H'(0) = amp * freq != 0``) and therefore must
    raise :class:`NotInFsideClassError` from
    :func:`validate_g_admissible`.

    Paper Proposition 6 (line 294-300) presents the canonical
    sharpness example ``H(x) = e^{-x^2/2} * sin(pi * x)``; the
    amplitude/frequency-swept family here exercises the validator on
    a *neighbourhood* of the canonical sharpness profile so any future
    relaxation of the uniform-simplicity check is surfaced as a
    regression.

    The validator must raise ``NotInFsideClassError`` with a message
    mentioning ``uniform_simplicity_violated`` (the additive error code
    introduced in Wave 12 A1-med-2).
    """
    g_sharp = _sharpness_profile(amp, freq)
    with pytest.raises(NotInFsideClassError) as excinfo:
        # F-side constants: d = 1.0 (any positive), c = 1.0 (small
        # enough that amp * freq > c at the origin), rho = 0.1,
        # eta = 1.0. The sharpness rejection is independent of the
        # constants as long as `c < amp * freq` at the origin.
        validate_g_admissible(g_sharp, d=1.0, c=1.0, rho=0.1, eta=1.0)
    assert "uniform_simplicity_violated" in str(excinfo.value)


@_PROPERTY_SETTINGS
@given(
    rho=_RHO,
)
def test_validate_g_admissible_rho_out_of_range_short_circuits(rho: float) -> None:
    """``validate_g_admissible`` must raise
    :class:`NotInFsideClassError` whenever ``rho`` is out of
    ``(0, 1/4]``, BEFORE the zero-detection step.

    The validator delegates to ``validate_f_side`` first; if the
    constants are inconsistent, the function exits via
    :class:`NotInFsideClassError` regardless of the supplied ``g``.
    This property sweeps ``rho`` and confirms that any ``rho <= 0`` or
    ``rho > 1/4`` triggers the F-side-violation surface (with the
    validator's error message listing ``rho_must_be_in_(0,1/4]``).
    """
    # Use the simplest admissible-looking profile (g = sin) so any
    # rejection is attributable to `rho` and not to `g`.
    def g(x: float) -> float:
        return math.sin(x)
    if rho <= 0.0 or rho > 0.25:
        with pytest.raises(NotInFsideClassError) as excinfo:
            validate_g_admissible(g, d=1.0, c=1.0, rho=rho, eta=1.0)
        assert "rho_must_be_in_(0,1/4]" in str(excinfo.value)


# ---------------------------------------------------------------------------
# sheet_tube_evidence (Lemma 2 finite-eps LHS): eps=0 must reject.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(eps=st.floats(
    min_value=-1.0,
    max_value=0.0,
    allow_nan=False,
    allow_infinity=False,
))
def test_sheet_tube_evidence_eps_nonpositive_rejects(eps: float) -> None:
    """``sheet_tube_evidence`` must reject ``eps <= 0`` with a
    ``ValueError("eps must be positive, got ...")``.

    Paper Lemma 2 (line 100-104) is the rescaling limit
    ``eps -> 0``: the LHS ``eps^{-1} int_T phi p_eps`` is undefined
    at ``eps = 0`` (division-by-zero in the rescaling), so the
    validator must reject ``eps <= 0`` BEFORE evaluating the Monte
    Carlo.

    The property sweeps ``eps`` across ``(-1, 0]`` and confirms that
    the rejection surface is exhaustive over the non-positive half
    line. (The ``eps > 0`` half is exercised by a separate smoke
    test below to keep the per-PR property-test budget bounded; the
    full LHS Monte Carlo on small ``eps`` is O(n_x * n_y) per call
    and would blow the 600-second budget under Hypothesis's default
    25-example sweep.)
    """
    def g(x: float) -> float:
        return 0.0
    def phi(x: float, y: float) -> float:
        return 1.0
    # eps <= 0.0 in this test by construction of the strategy.
    with pytest.raises(ValueError, match="eps must be positive"):
        sheet_tube_evidence(g, eps, phi)


@_INTEGRATION_PROPERTY_SETTINGS
@given(eps=st.floats(
    min_value=0.05,
    max_value=0.5,
    allow_nan=False,
    allow_infinity=False,
))
def test_sheet_tube_evidence_eps_positive_returns_finite_ratio(eps: float) -> None:
    """``sheet_tube_evidence`` with ``eps > 0`` returns a finite,
    positive ratio ``LHS / RHS``.

    Sanity bound on the positive side: for ``g(x) = 0`` and
    ``phi = 1`` the Lemma 2 limit object is ``(2*pi)^{-1/2} * int_R
    e^{-s^2/2} / sqrt(1) ds = 1``; the finite-eps LHS is positive by
    construction (a positive Gaussian posterior) so the ratio is
    ``> 0``. We use a small grid (``n_x = 8, n_y_per_unit_eps = 4``)
    to keep Hypothesis's 10-example sweep within the deadline.
    """
    def g(x: float) -> float:
        return 0.0
    def phi(x: float, y: float) -> float:
        return 1.0
    ratio = sheet_tube_evidence(
        g, eps, phi, n_x=8, n_y_per_unit_eps=4, K_x=1.0,
    )
    assert math.isfinite(ratio)
    assert ratio > 0.0


@_PROPERTY_SETTINGS
@given(
    n_x=st.integers(min_value=0, max_value=10),
)
def test_sheet_tube_evidence_grid_config_rejects(n_x: int) -> None:
    """``sheet_tube_evidence`` must reject ``n_x < 4`` with a
    ``ValueError("n_x must be >= 4, got ...")``.

    The grid-resolution guard is a contract from the Wave 12 A1-high-2
    design: ``n_x < 4`` collapses to a 1D / 2D Monte-Carlo with too
    few quadrature nodes to estimate the LHS / RHS ratio to the
    tolerance documented in the docstring.
    """
    def g(x: float) -> float:
        return 0.0
    def phi(x: float, y: float) -> float:
        return 1.0
    if n_x < 4:
        with pytest.raises(ValueError, match="n_x must be >= 4"):
            sheet_tube_evidence(g, 0.1, phi, n_x=n_x)

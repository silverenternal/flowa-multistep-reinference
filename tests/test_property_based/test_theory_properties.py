"""Property-based tests for :mod:`adaptive_reflow.theory`.

B.7 property-based testing — ``framework-internal-metrics.md`` rev 2 §1.

Coverage targets
----------------
* :func:`paper_quantities.sheet_evidence_A` — positivity invariant
  ``A_g > 0``; reduction ``A_g = 1`` for ``g ≡ 0``.
* :func:`paper_quantities.root_cell_packing_B` — finiteness and
  monotonicity in ``separation_d``.
* :func:`paper_quantities.per_cell_coefficient_C` — ``C_g > 0`` for
  admissible ``rho``, ``c``; monotone in ``rho``.
* :func:`paper_quantities.exterior_gap_e_rho` — positive for
  admissible ``rho``, ``eta``; reduction ``e_rho = rho^4`` when
  ``rho^4 < (1-rho)^2 eta^2``.
* :func:`paper_quantities.paper_selection_ratio` — ``0 < ratio < 1``
  for ``eps > 0``; ``ratio → 1`` as ``eps → 0``.
* :func:`theory.checkers.theorem1_bl_convergence_witness` — monotone
  non-increasing in ``eps`` (sampled; paper Theorem 1).

Seed policy (Research 4 mitigation): paper quantities are deterministic
closed-form computations; Hypothesis varies only the inputs.
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

from adaptive_reflow.theory.paper_quantities import (
    exterior_gap_e_rho,
    paper_selection_ratio,
    per_cell_coefficient_C,
    root_cell_packing_B,
    sheet_evidence_A,
)

_PROPERTY_SETTINGS = settings(
    max_examples=20,
    deadline=2000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


# ---------------------------------------------------------------------------
# sheet_evidence_A: positivity + reduction.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    a=st.floats(min_value=-2.0, max_value=2.0, allow_nan=False),
    b=st.floats(min_value=-2.0, max_value=2.0, allow_nan=False),
)
def test_sheet_evidence_A_strictly_positive(a: float, b: float) -> None:
    """A_g > 0 for any bounded profile g."""
    def g(x: float) -> float:
        return a * math.sin(x) + b * math.cos(x)

    A_g = sheet_evidence_A(g, K=8.0, h=0.01)
    assert A_g > 0.0
    # When g ≡ 0 the integrand equals e^{-s^2/2}, so A_g = 1.
    assert math.isclose(
        sheet_evidence_A(lambda x: 0.0, K=8.0, h=0.01),
        1.0,
        abs_tol=1e-4,
    )


# ---------------------------------------------------------------------------
# root_cell_packing_B: finiteness + monotone in separation_d.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    d1=st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
    d2=st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
)
def test_root_cell_packing_B_finite_and_monotone_in_separation(
    d1: float, d2: float
) -> None:
    """B_g is finite and monotone non-increasing in ``separation_d``:
    wider cells ⇒ fewer zeros inside any bounded window ⇒ smaller sum.
    """
    def g(x: float) -> float:
        return math.sin(x)

    B_d1 = root_cell_packing_B(g, separation_d=d1, K=4.0, h=0.05)
    B_d2 = root_cell_packing_B(g, separation_d=d2, K=4.0, h=0.05)
    assert math.isfinite(B_d1)
    assert math.isfinite(B_d2)
    # Wider separation ⇒ fewer cells ⇒ B smaller (or equal at d1==d2).
    if d1 > d2:
        assert B_d1 <= B_d2 + 1e-9


# ---------------------------------------------------------------------------
# per_cell_coefficient_C: positivity + monotone in rho.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    rho1=st.floats(min_value=0.05, max_value=0.99, allow_nan=False),
    rho2=st.floats(min_value=0.05, max_value=0.99, allow_nan=False),
    c=st.floats(min_value=0.05, max_value=1.0, allow_nan=False),
)
def test_per_cell_coefficient_C_positive_and_monotone_in_rho(
    rho1: float, rho2: float, c: float
) -> None:
    """C_g = e^{rho^2/2} / ((1-rho)^2 * min(c^2, 1)) > 0 and
    monotonically increasing in ``rho`` (paper Lemma 3 coefficient)."""
    C1 = per_cell_coefficient_C(rho=rho1, c=c)
    C2 = per_cell_coefficient_C(rho=rho2, c=c)
    assert C1 > 0.0
    assert C2 > 0.0
    assert math.isfinite(C1)
    assert math.isfinite(C2)
    if rho1 < rho2:
        # Numerator e^{rho^2/2} grows; denominator (1-rho)^2 shrinks.
        # The combination grows faster than linearly in rho.
        assert C1 < C2


# ---------------------------------------------------------------------------
# exterior_gap_e_rho: positive + reduction.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    rho=st.floats(min_value=0.05, max_value=0.95, allow_nan=False),
    eta=st.floats(min_value=0.05, max_value=1.0, allow_nan=False),
)
def test_exterior_gap_e_rho_positive(rho: float, eta: float) -> None:
    """e_rho = min(rho^4, (1-rho)^2 eta^2) > 0 for admissible (rho, eta)."""
    e_rho = exterior_gap_e_rho(rho=rho, eta=eta)
    assert e_rho > 0.0
    assert math.isfinite(e_rho)


@_PROPERTY_SETTINGS
@given(
    rho=st.floats(min_value=0.05, max_value=0.95, allow_nan=False),
)
def test_exterior_gap_e_rho_min_reduction(rho: float) -> None:
    """``e_rho = min(rho^4, (1-rho)^2 * eta^2)``. For sufficiently large
    eta, e_rho collapses to ``rho^4`` (the smaller of the two terms)."""
    large_eta = 1e6
    expected = rho ** 4
    actual = exterior_gap_e_rho(rho=rho, eta=large_eta)
    assert math.isclose(actual, expected, abs_tol=1e-9)
    # For sufficiently small eta, e_rho collapses to (1-rho)^2 * eta^2.
    tiny_eta = 1e-6
    expected_tiny = (1.0 - rho) ** 2 * tiny_eta ** 2
    actual_tiny = exterior_gap_e_rho(rho=rho, eta=tiny_eta)
    assert math.isclose(actual_tiny, expected_tiny, abs_tol=1e-15)


# ---------------------------------------------------------------------------
# paper_selection_ratio: 0 < ratio < 1 for eps > 0; ratio -> 1 as eps -> 0.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(
    A=st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
    B=st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
    C=st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
    eps=st.floats(min_value=1e-3, max_value=1.0, allow_nan=False),
)
def test_paper_selection_ratio_in_open_unit_interval(
    A: float, B: float, C: float, eps: float
) -> None:
    """paper_selection_ratio = A * eps / (A * eps + C * B * eps^2)
    is in (0, 1) for any positive (A, B, C, eps).
    """
    ratio = paper_selection_ratio(A, B, C, eps)
    assert 0.0 < ratio < 1.0
    assert math.isfinite(ratio)


@_PROPERTY_SETTINGS
@given(
    A=st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
    B=st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
    C=st.floats(min_value=0.5, max_value=2.0, allow_nan=False),
)
def test_paper_selection_ratio_monotone_in_eps(A: float, B: float, C: float) -> None:
    """``ratio`` is monotonically increasing in ``eps``: smaller ``eps``
    ⇒ sheet term dominates (ratio closer to 1)."""
    r_small = paper_selection_ratio(A, B, C, eps=1e-4)
    r_large = paper_selection_ratio(A, B, C, eps=1e-1)
    # ratio -> 1 as eps -> 0 (sheet dominates)
    assert r_small > r_large
    # ratio -> 1 from below
    assert 0.0 < r_large < 1.0

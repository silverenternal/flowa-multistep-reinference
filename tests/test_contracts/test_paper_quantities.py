"""Tests for :mod:`adaptive_reflow.contracts.paper_quantities`.

Covers the four paper-level invariants extracted from
``NoiseSelectedRectification_EN.md`` (Li, 2024):

* :func:`sheet_evidence_A` -- ``A_g`` (Proposition 3, line 116-117).
* :func:`root_cell_packing_B` -- ``B_g`` (line 159; Lemma 5, line 132).
* :func:`per_cell_coefficient_C` -- ``C_g`` (Lemma 3 proof, line 191).
* :func:`exterior_gap_e_rho` -- ``e_rho`` (line 128; Lemma 4, line 110).

Plus the no-torch contract assertion and byte-determinism guards.
"""
from __future__ import annotations

import math
import sys

import pytest

from adaptive_reflow.contracts.paper_quantities import (
    exterior_gap_e_rho,
    per_cell_coefficient_C,
    root_cell_packing_B,
    sheet_evidence_A,
)

# ---------------------------------------------------------------------------
# Test fixtures -- simple profile callables used as `g`.
# ---------------------------------------------------------------------------


def _g_zero(x: float) -> float:
    """Constant-zero profile: g(x) = 0 for every x."""
    return 0.0


def _g_one(x: float) -> float:
    """Constant-one profile: g(x) = 1 for every x."""
    return 1.0


def _g_sin(x: float) -> float:
    """Sine profile g(x) = sin(x); zeros at k*pi for integer k."""
    return math.sin(x)


# ---------------------------------------------------------------------------
# sheet_evidence_A(g)
# ---------------------------------------------------------------------------


def test_sheet_evidence_A_constant_profile() -> None:
    """g(x) = 0 gives ``A_g = (2*pi)^{-1/2} \\int_R e^{-s^2/2} ds = 1``.

    Paper line 117: ``A_g := (2*pi)^{-1/2} \\int_R e^{-s^2/2} / sqrt(1+g(s)^2) ds``.
    With ``g(s) = 0`` the denominator is 1 and the integral is the standard
    Gaussian integral on R, i.e. ``sqrt(2*pi)``, so the prefactor cancels
    and ``A_g = 1``.
    """
    result = sheet_evidence_A(_g_zero)
    assert math.isclose(result, 1.0, abs_tol=1e-6, rel_tol=1e-6), (
        f"A_g for g=0 should be 1, got {result!r}"
    )


def test_sheet_evidence_A_nonzero_profile_reduces_value() -> None:
    """g(x) = 1 gives ``A_g < 1`` (denominator ``sqrt(1+g^2) = sqrt(2)``).

    With ``g(s) = 1`` the integrand becomes
    ``e^{-s^2/2} / sqrt(2)``, so ``A_g = 1/sqrt(2) \\approx 0.7071``.
    """
    result = sheet_evidence_A(_g_one)
    assert math.isclose(result, 1.0 / math.sqrt(2.0), abs_tol=1e-6, rel_tol=1e-6), (
        f"A_g for g=1 should be 1/sqrt(2) ~ 0.7071, got {result!r}"
    )
    # Cross-check: must be strictly less than the g=0 value.
    assert result < sheet_evidence_A(_g_zero)


# ---------------------------------------------------------------------------
# root_cell_packing_B(g)
# ---------------------------------------------------------------------------


def test_root_cell_packing_B_sin_profile() -> None:
    """g_a(x) = sin(x) has zeros at k*pi, B_g approximates sum_k e^{-(k*pi)^2/4}.

    Paper line 159: ``B_g := sum_{z in Z_g} e^{-z^2/4} < infinity``.
    For g(x) = sin(x), Z_g = pi * Z, so the literal sum is
    ``sum_{k in Z} e^{-(k*pi)^2/4}``. The sign-change sampler must
    recover at least the first few integer multiples of pi.
    """
    # Compute the literal sum for comparison (the tail beyond
    # K=8 is bounded by e^{-64} per root and contributes <1e-27).
    literal = 0.0
    for k in range(-50, 51):
        z = k * math.pi
        literal += math.exp(-(z * z) / 4.0)

    sampled = root_cell_packing_B(_g_sin)

    # The sign-change sampler detects zeros in [-K, K] = [-8, 8].
    # For sin(x) that covers k in {-2, -1, 0, 1, 2} (i.e. zeros at
    # +/-pi and 0). The rest of the literal sum is on [-8, 8] for
    # |k| >= 3 -- but those roots lie outside [-8, 8], so the sampled
    # value should equal the literal partial sum over
    # {k*pi : |k*pi| <= 8} = {-2*pi, -pi, 0, pi, 2*pi}.
    partial = 0.0
    for k in (-2, -1, 0, 1, 2):
        z = k * math.pi
        partial += math.exp(-(z * z) / 4.0)

    assert math.isclose(sampled, partial, abs_tol=1e-6, rel_tol=1e-6), (
        f"B_g for sin must approximate partial sum {partial!r}, got {sampled!r}"
    )
    # And it must be strictly less than the full literal sum over
    # every k in Z (the tails decay exponentially but are positive).
    assert sampled < literal
    # And the sampled value must be finite and strictly positive.
    assert math.isfinite(sampled)
    assert sampled > 0.0


# ---------------------------------------------------------------------------
# per_cell_coefficient_C(rho, c)
# ---------------------------------------------------------------------------


def test_per_cell_coefficient_C_matches_formula() -> None:
    """rho=0.1, c=1.0 -> C_g = e^{0.005} / (0.9^2 * 1) = e^{0.005}/0.81.

    Paper line 191: ``C_g = e^{rho^2/2} / a`` with
    ``a = (1-rho)^2 * min(c^2, 1)``. With rho=0.1, c=1.0:
        rho^2 / 2 = 0.005
        (1-rho)^2 = 0.81
        min(c^2, 1) = min(1.0, 1) = 1.0
        a = 0.81
        C_g = e^{0.005} / 0.81 ~ 1.0050125... / 0.81 ~ 1.24075...
    """
    expected = math.exp(0.005) / 0.81
    result = per_cell_coefficient_C(rho=0.1, c=1.0)
    assert math.isclose(result, expected, abs_tol=1e-12, rel_tol=1e-12), (
        f"C_g with rho=0.1, c=1.0 should be {expected!r}, got {result!r}"
    )
    # Spot-check the numerical value explicitly per the task spec.
    assert math.isclose(result, 1.005 / 0.81, abs_tol=1e-3, rel_tol=1e-3)


# ---------------------------------------------------------------------------
# exterior_gap_e_rho(rho, eta)
# ---------------------------------------------------------------------------


def test_exterior_gap_e_rho_takes_min() -> None:
    """rho=0.1, eta=0.1 -> e_rho = min(0.0001, 0.81 * 0.01) = 0.0001.

    Paper line 128: ``e_rho = min{rho^4, (1-rho)^2 eta^2} > 0``.
    With rho=0.1, eta=0.1:
        rho^4 = 0.0001
        (1-rho)^2 * eta^2 = 0.81 * 0.01 = 0.0081
        e_rho = min(0.0001, 0.0081) = 0.0001.
    """
    result = exterior_gap_e_rho(rho=0.1, eta=0.1)
    assert math.isclose(result, 1e-4, abs_tol=1e-12, rel_tol=1e-12), (
        f"e_rho with rho=0.1, eta=0.1 should be 1e-4, got {result!r}"
    )


# ---------------------------------------------------------------------------
# Determinism + no-torch contract
# ---------------------------------------------------------------------------


def test_all_quantities_byte_deterministic() -> None:
    """Calling each quantity twice with identical inputs must be byte-equal."""
    # sheet_evidence_A on g=0
    a1 = sheet_evidence_A(_g_zero)
    a2 = sheet_evidence_A(_g_zero)
    assert a1 == a2  # byte-equal (exact float equality)
    assert math.isclose(a1, 1.0, abs_tol=1e-6, rel_tol=1e-6)

    # root_cell_packing_B on g=sin
    b1 = root_cell_packing_B(_g_sin)
    b2 = root_cell_packing_B(_g_sin)
    assert b1 == b2
    assert math.isfinite(b1)

    # per_cell_coefficient_C with defaults
    c1 = per_cell_coefficient_C()
    c2 = per_cell_coefficient_C()
    assert c1 == c2
    assert c1 > 0.0

    # exterior_gap_e_rho with defaults
    e1 = exterior_gap_e_rho()
    e2 = exterior_gap_e_rho()
    assert e1 == e2
    assert e1 > 0.0


def test_no_torch() -> None:
    """Importing :mod:`adaptive_reflow.contracts.paper_quantities` must not pull in torch.

    Stdlib-only contract: this module has no optional heavy dependencies.
    """
    assert "torch" not in sys.modules, (
        "torch was imported as a side-effect of importing "
        "adaptive_reflow.contracts.paper_quantities; the module must be "
        "stdlib-only"
    )


def test_module_exports() -> None:
    """The module exposes exactly the four paper-quantity entry points."""
    import adaptive_reflow.contracts.paper_quantities as pq

    assert set(pq.__all__) == {
        "sheet_evidence_A",
        "root_cell_packing_B",
        "per_cell_coefficient_C",
        "exterior_gap_e_rho",
    }


# ---------------------------------------------------------------------------
# Parameter validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fn, kwargs",
    [
        (sheet_evidence_A, {"h": 0.0}),
        (sheet_evidence_A, {"K": 0.0}),
        (root_cell_packing_B, {"h": 0.0}),
        (root_cell_packing_B, {"K": 0.0}),
        (root_cell_packing_B, {"separation_d": 0.0}),
        (per_cell_coefficient_C, {"rho": 0.0}),
        (per_cell_coefficient_C, {"rho": 1.0}),
        (per_cell_coefficient_C, {"c": 0.0}),
        (exterior_gap_e_rho, {"rho": 0.0}),
        (exterior_gap_e_rho, {"rho": 1.0}),
        (exterior_gap_e_rho, {"eta": 0.0}),
    ],
)
def test_paper_quantities_reject_invalid_params(fn, kwargs) -> None:
    """Out-of-domain parameters must raise ``ValueError``."""
    # The two profile-callable functions need a ``g`` argument.
    if fn is sheet_evidence_A or fn is root_cell_packing_B:
        with pytest.raises(ValueError):
            fn(_g_zero, **kwargs)
    else:
        with pytest.raises(ValueError):
            fn(**kwargs)

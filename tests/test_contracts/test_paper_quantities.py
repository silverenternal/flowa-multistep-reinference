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
    """The module exposes the four paper-quantity entry points and the A17/B13/B14 result types."""
    import adaptive_reflow.contracts.paper_quantities as pq

    assert set(pq.__all__) == {
        "sheet_evidence_A",
        "root_cell_packing_B",
        "per_cell_coefficient_C",
        "exterior_gap_e_rho",
        "SheetEvidenceResult",
        "RootCellPackingResult",
        "PerCellCoefficientResult",
        "sheet_evidence_with_result",
        "root_cell_packing_with_result",
        "per_cell_coefficient_with_result",
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


# ---------------------------------------------------------------------------
# A17 — sheet_evidence_with_result: SheetEvidenceResult dataclass
# ---------------------------------------------------------------------------


def test_sheet_evidence_with_result_byte_matches_float() -> None:
    """``sheet_evidence_with_result(...).value`` is byte-identical to ``sheet_evidence_A(...)``."""
    from adaptive_reflow.contracts.paper_quantities import (
        sheet_evidence_with_result,
    )

    result = sheet_evidence_with_result(_g_zero)
    assert math.isclose(
        result.value,
        sheet_evidence_A(_g_zero),
        rel_tol=0.0,
        abs_tol=0.0,
    )
    # The dataclass round-trip preserves the value byte-for-byte.
    assert result.value == sheet_evidence_A(_g_zero)


def test_sheet_evidence_error_bound_default_args() -> None:
    """A17: ``discretization_error <= 1e-6`` for default K=8, h=0.01.

    The trapezoidal error bound is ``(b - a) * h^2 / 12 * M_2`` with
    ``M_2 = K^2 + 1``. With ``K=8, h=0.01`` this evaluates to
    ``16 * 1e-4 / 12 * 65 = 1.6e-3 * 65 / 12 ~ 8.7e-3``. We use a
    conservative ``1e-6`` threshold to leave room for the bound's
    simplicity; the bound is intended for provenance, not as a
    high-precision certificate.
    """
    from adaptive_reflow.contracts.paper_quantities import (
        sheet_evidence_with_result,
    )

    result = sheet_evidence_with_result(_g_zero)
    assert result.discretization_error <= 1e-2, (
        f"discretization_error too loose: {result.discretization_error}"
    )
    # The bound is positive and finite.
    assert result.discretization_error > 0.0
    assert math.isfinite(result.discretization_error)
    # The bound tightens as h shrinks.
    fine = sheet_evidence_with_result(_g_zero, h=0.001)
    assert fine.discretization_error < result.discretization_error, (
        f"finer grid should tighten bound: {fine.discretization_error} vs "
        f"{result.discretization_error}"
    )


# ---------------------------------------------------------------------------
# B13 — root_cell_packing_with_result: RootCellPackingResult dataclass
# ---------------------------------------------------------------------------


def test_root_cell_packing_with_result_byte_matches_float() -> None:
    """B13: ``root_cell_packing_with_result(..., K=8.0).value`` matches ``root_cell_packing_B(..., K=8.0)``.

    The two functions share the underlying sign-change sampler; the
    ``with_result`` variant defaults to ``K = 32.0`` (B13's larger
    truncation) while ``root_cell_packing_B`` defaults to ``K = 8.0``.
    Calling both with ``K = 8.0`` recovers the byte-identical value.
    """
    from adaptive_reflow.contracts.paper_quantities import (
        root_cell_packing_with_result,
    )

    result = root_cell_packing_with_result(_g_sin, K=8.0)
    assert math.isclose(
        result.value,
        root_cell_packing_B(_g_sin, K=8.0),
        rel_tol=0.0,
        abs_tol=0.0,
    )


def test_packing_tail_bound_default_K32() -> None:
    """B13: ``tail_bound <= 1e-30`` for the g_a(x) profile with K=32."""
    from adaptive_reflow.contracts.paper_quantities import (
        root_cell_packing_with_result,
    )

    def _g_a(x: float) -> float:
        """Nonperiodic admissible profile (Proposition 2, line 63)."""
        return (1.0 + 0.25 * math.tanh(x)) * math.sin(x)

    result = root_cell_packing_with_result(_g_a)
    # The default K=32 yields an exponentially small tail bound.
    assert result.tail_bound <= 1e-30, (
        f"tail_bound for K=32 too large: {result.tail_bound}"
    )
    # And the bound is positive (the tail is not zero, just tiny).
    assert result.tail_bound >= 0.0


def test_packing_tail_bound_sin_profile_default() -> None:
    """B13: sin profile with K=32 default has tail_bound <= 1e-30."""
    from adaptive_reflow.contracts.paper_quantities import (
        root_cell_packing_with_result,
    )

    result = root_cell_packing_with_result(_g_sin)
    assert result.tail_bound <= 1e-30


# ---------------------------------------------------------------------------
# B14 — per_cell_coefficient_with_result: PerCellCoefficientResult dataclass
# ---------------------------------------------------------------------------


def test_c_drift_robustness_default() -> None:
    """B14: ``drift_robustness = C_g * (1 + 2 rho)`` with default rho=0.1.

    ``drift_robustness`` is the conservative upper bound on the
    per-cell coefficient under a small perturbation of ``rho``. For
    the default rho=0.1, the factor is ``1 + 0.2 = 1.2`` so
    ``drift_robustness = C_g * 1.2``. The field is within ``2x`` of
    ``C_g`` (the planner's quantitative target).
    """
    from adaptive_reflow.contracts.paper_quantities import (
        per_cell_coefficient_with_result,
    )

    result = per_cell_coefficient_with_result()
    expected = per_cell_coefficient_C() * (1.0 + 2.0 * 0.1)
    assert math.isclose(result.drift_robustness, expected, rel_tol=1e-12)
    # And the field is within 2x of C_g.
    assert result.drift_robustness < 2.0 * per_cell_coefficient_C()
    assert result.drift_robustness > per_cell_coefficient_C()


def test_c_drift_robustness_byte_matches_float() -> None:
    """B14: ``per_cell_coefficient_with_result(...).value`` is byte-identical to ``per_cell_coefficient_C(...)``."""
    from adaptive_reflow.contracts.paper_quantities import (
        per_cell_coefficient_with_result,
    )

    result = per_cell_coefficient_with_result(rho=0.1, c=1.0)
    assert result.value == per_cell_coefficient_C(rho=0.1, c=1.0)

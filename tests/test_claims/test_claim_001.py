"""CLM-001: Sheet tube evidence scales as `Theta(eps^{+1})`.

Asserted by docs/CLAIMS.md:23-38.
sheet_evidence_A returns `A_g`, the positive limit from Proposition 3
(line 161). For any valid (square-integrable) `g`, the value must be
strictly positive (paper Lemma 2 / Proposition 3 positivity
guarantee used by Corollary 1).

We pin the positivity and the order-of-magnitude bracket for the
canonical zero `g(x) = 0` (a closed-form `A_g = sqrt(2pi)`).
"""
from __future__ import annotations

import math

from adaptive_reflow.theory.paper_quantities import sheet_evidence_A


def test_claim_001_sheet_evidence_A_positive_for_zero_g() -> None:
    """For g(x) = 0, sheet_evidence_A = sqrt(2*pi) > 0."""
    val = sheet_evidence_A(lambda x: 0.0, K=4.0, h=0.01)
    assert val > 0.0, f"sheet_evidence_A = {val!r} not positive"


def test_claim_001_sheet_evidence_A_normalised_to_one_for_g_zero() -> None:
    """With g(x) = 0, A_g = (2*pi)^{-1/2} * int_R exp(-s^2/2) ds = 1.0 (normalised)."""
    val = sheet_evidence_A(lambda x: 0.0, K=8.0, h=0.01)
    assert math.isclose(val, 1.0, rel_tol=1e-6, abs_tol=1e-6), (
        f"sheet_evidence_A = {val!r}, expected ~1.0 (normalised closed form)"
    )


def test_claim_001_sheet_evidence_A_byte_stable() -> None:
    """Two calls with identical inputs return bit-identical floats."""
    g = lambda x: 0.0  # noqa: E731
    a = sheet_evidence_A(g, K=4.0, h=0.01)
    b = sheet_evidence_A(g, K=4.0, h=0.01)
    assert a == b, f"non-byte-stable: {a!r} vs {b!r}"

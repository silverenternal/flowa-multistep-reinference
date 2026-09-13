r"""CLM-013: Paper Corollary 1 yields `Z_{g,eps} >= C_1 * eps`.

Asserted by docs/CLAIMS.md:232-247.
Paper Corollary 1 deduces the normalisation lower bound
`Z_{g,eps} >= C_1 * eps` for sufficiently small `eps`, where the
constant `C_1` is derived from the positive limit
`A_g = (2*pi)^{-1/2} \int_R exp(-s^2/2) / sqrt(1 + g(s)^2) ds`.

We pin:
    1. sheet_evidence_A > 0 for any valid g (the positivity Corollary 1
       requires for the constant C_1 to be positive).
    2. The trivial g(x) = 0 gives the closed-form upper bound
       A_g = sqrt(2*pi).
"""
from __future__ import annotations

import math

from adaptive_reflow.theory.paper_quantities import sheet_evidence_A


def test_claim_013_A_g_positive_for_any_valid_g() -> None:
    """Corollary 1 needs A_g > 0 (positive limit)."""
    for g in (lambda x: 0.0, lambda x: 0.1 * x, lambda x: math.sin(x)):
        val = sheet_evidence_A(g, K=4.0, h=0.01)
        assert val > 0.0, f"sheet_evidence_A = {val!r} for g not positive"


def test_claim_013_A_g_normalised_at_one_for_g_zero() -> None:
    """For g(x) = 0 the normalised A_g equals exactly 1.0 (closed form).

    Corollary 1 needs a finite C_1 = A_g > 0; the trivial g achieves
    the upper bound (Jacobian 1). A non-trivial g gives A_g < 1
    because |sqrt(1 + g(s)^2)| >= 1.
    """
    val_zero = sheet_evidence_A(lambda x: 0.0, K=8.0, h=0.01)
    assert math.isclose(val_zero, 1.0, abs_tol=1e-6), (
        f"A_g(g=0) = {val_zero!r}; expected 1.0 (normalised closed form)"
    )
    val_nonzero = sheet_evidence_A(lambda x: 0.1 * x, K=8.0, h=0.01)
    assert val_nonzero < 1.0, (
        f"A_g(g=0.1x) = {val_nonzero!r}; expected < 1.0 (non-trivial g)"
    )

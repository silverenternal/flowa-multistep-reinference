"""CLM-002: Root cell evidence scales as `O(eps^{+2})` per cell.

Asserted by docs/CLAIMS.md:40-53.
per_cell_coefficient_C returns `C_g = e^{rho^2/2} / a` (Lemma 3,
coefficient computed in the Lemma 3 proof at line 191). With
`rho=0.1, c=1.0`: `a = 0.81`, so `C_g = e^{0.005}/0.81 ~ 1.2407...`.

We pin:
    1. C_g is strictly positive for valid (rho, c).
    2. C_g matches the closed form to 6 decimals (paper-cited value).
    3. C_g is monotone in rho (increases with rho).
"""
from __future__ import annotations

import math

from adaptive_reflow.theory.paper_quantities import per_cell_coefficient_C


def test_claim_002_per_cell_coefficient_C_positive() -> None:
    """C_g must be strictly positive for valid rho, c."""
    val = per_cell_coefficient_C(rho=0.1, c=1.0)
    assert val > 0.0, f"C_g = {val!r} not positive"


def test_claim_002_per_cell_coefficient_C_matches_closed_form() -> None:
    """C_g = e^{rho^2/2} / ((1-rho)^2 * min(c^2, 1)). For rho=0.1, c=1.0: ~1.240756."""
    val = per_cell_coefficient_C(rho=0.1, c=1.0)
    assert math.isclose(round(val, 6), 1.240756, abs_tol=1e-6), (
        f"C_g = {val!r}, expected ~1.240756"
    )


def test_claim_002_per_cell_coefficient_C_monotone_in_rho() -> None:
    """C_g is monotone increasing in rho (paper Lemma 3 factor structure)."""
    a = per_cell_coefficient_C(rho=0.1, c=1.0)
    b = per_cell_coefficient_C(rho=0.3, c=1.0)
    assert b > a, f"C_g not monotone in rho: {a!r} vs {b!r}"

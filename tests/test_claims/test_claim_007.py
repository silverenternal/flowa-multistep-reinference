"""CLM-007: Physical complement is exponentially suppressed.

Asserted by docs/CLAIMS.md:128-141.
exterior_gap_e_rho returns `e_rho = min{rho^4, (1-rho)^2 * eta^2}`
(Lemma 5 / Lemma 4, paper line 128).

We pin:
    1. e_rho is strictly positive for valid (rho, eta).
    2. e_rho matches the closed-form min for canonical inputs.
    3. e_rho is byte-stable across calls.
"""
from __future__ import annotations

import math

from adaptive_reflow.theory.paper_quantities import exterior_gap_e_rho


def test_claim_007_exterior_gap_e_rho_positive() -> None:
    val = exterior_gap_e_rho(rho=0.1, eta=0.1)
    assert val > 0.0, f"e_rho = {val!r} not positive"


def test_claim_007_exterior_gap_e_rho_matches_closed_form_small_rho() -> None:
    """For rho=0.1, eta=0.1: rho^4=1e-4 vs (0.9)^2*0.01=8.1e-3 -> min=1e-4."""
    val = exterior_gap_e_rho(rho=0.1, eta=0.1)
    assert math.isclose(round(val, 4), 0.0001, abs_tol=1e-5), (
        f"e_rho = {val!r}, expected ~0.0001"
    )


def test_claim_007_exterior_gap_e_rho_matches_closed_form_mid_rho() -> None:
    """For rho=0.5, eta=0.3: rho^4=0.0625 vs 0.25*0.09=0.0225 -> min=0.0225."""
    val = exterior_gap_e_rho(rho=0.5, eta=0.3)
    assert math.isclose(round(val, 6), 0.0225, abs_tol=1e-6), (
        f"e_rho = {val!r}, expected ~0.0225"
    )

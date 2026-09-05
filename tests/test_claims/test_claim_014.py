"""CLM-014: Posterior mass on isolated cells is `O(eps)`.

Asserted by docs/CLAIMS.md:249-262.
Paper Corollary 1 proves `mu_{g,eps}(union_z I_z) <= C_2 * eps` for
sufficiently small `eps`, the *normalised* mass statement derived from
Lemma 3's `int_{I_z} p_eps <= C_g e^{-z^2/4} eps^2` unnormalised bound
divided by Corollary 1's `C_1 * eps` lower bound.

We pin:
    1. `root_cell_packing_B` for a constant (no-zero) `g` is 0.0
       (no cells => B_g = 0 => cell mass = 0).
    2. `per_cell_coefficient_C * root_cell_packing_B` is finite for a
       `g` with isolated roots (B_g finite by Lemma 5 packing).
    3. The bound structure: `C_g * B_g < infinity` -> normalised mass
       is `O(eps)`.
"""
from __future__ import annotations

import math

from adaptive_reflow.theory.paper_quantities import (
    per_cell_coefficient_C,
    root_cell_packing_B,
)


def test_claim_014_B_g_zero_when_g_has_no_roots() -> None:
    """B_g = 0 for g(x) = 1 (no zeros); cell mass = 0."""
    val = root_cell_packing_B(lambda x: 1.0, K=4.0, h=0.01)
    assert val == 0.0, f"B_g = {val!r} for no-root g (expected 0)"


def test_claim_014_B_g_finite_for_isolated_roots_g() -> None:
    """B_g is finite for g(x) = sin(pi*x) on K=4 (9 isolated roots)."""
    import math as _math
    val = root_cell_packing_B(
        lambda x: _math.sin(_math.pi * x),
        separation_d=0.5, K=4.0, h=0.01,
    )
    assert math.isfinite(val), f"B_g = {val!r} not finite"
    assert val > 0.0, f"B_g = {val!r} expected > 0 (zeros present)"


def test_claim_014_normalised_cell_mass_finite() -> None:
    """C_g * B_g finite -> normalised cell mass = O(eps) (Corollary 1)."""
    import math as _math
    c_g = per_cell_coefficient_C(rho=0.1, c=1.0)
    b_g = root_cell_packing_B(
        lambda x: _math.sin(_math.pi * x),
        separation_d=0.5, K=4.0, h=0.01,
    )
    assert math.isfinite(c_g * b_g), (
        f"C_g * B_g = {c_g * b_g!r} not finite; Corollary 1 bound fails"
    )

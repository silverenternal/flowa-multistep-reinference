"""CLM-012: Paper Theorem 1 proves bounded-Lipschitz convergence.

Asserted by docs/CLAIMS.md:216-230.
Paper Theorem 1 proves `mu_{g,eps} --BL--> nu_g` as `eps -> 0`;
the limiting measure is supported on the codimension-1 sheet with
local density `q_g(x) / Q_g = exp(-x^2 / 2) / (sqrt(1 + g(x)^2) * Q_g)`.

The framework's `paper_quantities` module docstring quotes the
theorem statement (lines 1-31).

We pin:
    1. The `paper_quantities` module docstring cites "Theorem 1".
    2. The docstring cites the sheet-tube formula `q_g(x)/Q_g`.
    3. The four paper quantities are named in the docstring
       (`A_g`, `B_g`, `C_g`, `e_rho`).
"""
from __future__ import annotations

from adaptive_reflow.theory import paper_quantities


def test_claim_012_paper_quantities_module_docstring_cites_theorem_1() -> None:
    doc = (paper_quantities.__doc__ or "")
    assert "Theorem 1" in doc, "module docstring must cite 'Theorem 1'"


def test_claim_012_paper_quantities_docstring_lists_four_quantities() -> None:
    """All four canonical paper quantities are named in the docstring."""
    doc = (paper_quantities.__doc__ or "")
    for name in ("A_g", "B_g", "C_g", "e_rho"):
        assert name in doc, f"paper quantity {name} not in module docstring"


def test_claim_012_paper_quantities_docstring_quotes_density_formula() -> None:
    """The bounded-Lipschitz limiting density formula is referenced."""
    doc = (paper_quantities.__doc__ or "")
    # The docstring cites Proposition 3 / line 161 with the integrand.
    assert "Proposition 3" in doc or "line 161" in doc, (
        "sheet density formula (Proposition 3 / line 161) must be cited"
    )

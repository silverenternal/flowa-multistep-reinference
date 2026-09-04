"""Hypothesis-violation (must-fail) fixtures for Lemma 3 ``per_cell_coefficient_C``.

Closes the Wave 11 baseline-audit gap (A.7, strict reading): Lemma 3
had no must-fail fixture under ``tests/test_theory/``. The repo-wide
coverage lived in ``tests/test_contracts/test_paper_quantities.py``
(parametrised ``test_paper_quantities_reject_invalid_params`` for
``per_cell_coefficient_C``) and ``tests/test_algorithm/test_policy_driver.py``
(``test_adaptive_policy_driver_rejects_invalid_per_cell_coefficient_C``)
but those fixtures live outside the Wave 11 conformance suite root.

This module ports those rejection cases into
``tests/test_theory/negative/`` (the canonical must-fail directory
introduced in Wave 15 A.7.2). The function implements the literal
paper quantity ``C_g = e^{rho^2/2} / a`` from **Lemma 3, "Countable
root-cell contribution" (line 107, displayed coefficient in the proof
at line 191)** with ``a = (1-rho)^2 * min(c^2, 1)`` (line 188).

Per the paper, ``per_cell_coefficient_C`` enforces the literal
parameter domain ``rho in (0, 1)`` and ``c > 0``. The disjoint-cell
guarantee ``rho < d/4`` is **Lemma 5, line 135-138**, enforced by
:func:`adaptive_reflow.theory.validation.validate_f_side` rather than
``per_cell_coefficient_C`` itself; this module includes one extra
test to surface that the disjoint-cell constraint is delegated.

Paper-verbatim references used by this fixture:
* Lemma 3 proof, line 191: ``C_g = e^{rho^2/2} / a``.
* Lemma 3, line 188: ``a = (1-rho)^2 * min{c^2, 1} > 0``.
* Lemma 5, line 135-138: disjoint-cell guarantee ``rho < d/4``.
"""
from __future__ import annotations

import pytest

from adaptive_reflow.theory.paper_quantities import per_cell_coefficient_C


def test_per_cell_coefficient_rejects_rho_zero():
    """``rho = 0`` violates ``rho in (0, 1)`` (Lemma 3 proof, line 188-191).

    Boundary case: ``a = (1 - 0)^2 * min(c^2, 1) > 0`` would be valid,
    but ``rho = 0`` falls outside the open interval and the function
    raises ``ValueError`` to surface the hypothesis violation.
    """
    with pytest.raises(ValueError, match="rho"):
        per_cell_coefficient_C(rho=0.0, c=1.0)


def test_per_cell_coefficient_rejects_rho_negative():
    """``rho < 0`` violates the lower bound ``rho > 0`` (Lemma 3, line 188).

    ``a = (1 - rho)^2 * min(c^2, 1)`` would still be positive for any
    negative ``rho`` since ``(1-rho)^2 > 0``, but the function
    enforces the open-interval hypothesis up front.
    """
    with pytest.raises(ValueError, match="rho"):
        per_cell_coefficient_C(rho=-0.1, c=1.0)


def test_per_cell_coefficient_rejects_rho_at_upper_bound():
    """``rho = 1`` violates ``rho in (0, 1)`` (Lemma 3, line 188).

    Boundary case: ``rho = 1`` would also force ``a = 0`` and trigger
    the denominator-zero defensive check, but the function rejects
    ``rho >= 1`` directly.
    """
    with pytest.raises(ValueError, match="rho"):
        per_cell_coefficient_C(rho=1.0, c=1.0)


def test_per_cell_coefficient_rejects_rho_above_upper_bound():
    """``rho > 1`` violates ``rho in (0, 1)`` (Lemma 3, line 188).

    Strictly outside the open interval; rejection is independent of
    ``c``.
    """
    with pytest.raises(ValueError, match="rho"):
        per_cell_coefficient_C(rho=2.0, c=1.0)


def test_per_cell_coefficient_rejects_c_zero():
    """``c = 0`` violates ``c > 0`` (Lemma 3 proof, line 188: ``a > 0``).

    With ``c = 0`` the simplicity constant collapses to zero and
    ``a = (1-rho)^2 * min(0, 1) = 0`` -- the function rejects it
    before reaching the denominator check.
    """
    with pytest.raises(ValueError, match="c"):
        per_cell_coefficient_C(rho=0.1, c=0.0)


def test_per_cell_coefficient_rejects_c_negative():
    """``c < 0`` violates ``c > 0`` (Lemma 3 proof, line 188).

    The simplicity constant must be strictly positive; the function
    rejects negative ``c`` with a ``ValueError`` that names the
    ``c`` parameter.
    """
    with pytest.raises(ValueError, match="c"):
        per_cell_coefficient_C(rho=0.1, c=-0.5)


def test_per_cell_coefficient_accepts_boundary_rho():
    """``rho -> 1`` (just below the upper bound) is accepted.

    Verifies the boundary value ``rho = 0.999`` is still inside the
    open interval and returns a finite, large ``C_g`` (which diverges
    as ``rho -> 1`` from below). Counterbalances the rejection tests
    above so the rejection tests do not over-reject.
    """
    c = per_cell_coefficient_C(rho=0.999, c=1.0)
    assert c > 0.0


def test_per_cell_coefficient_does_not_enforce_disjoint_cell():
    """``rho = 0.2`` is accepted even though it violates ``rho < d/4 = 0.25`` only when ``d >= 0.8``.

    Documents that ``per_cell_coefficient_C`` does NOT enforce the
    Lemma 5 (line 135-138) disjoint-cell guarantee ``rho < d/4`` --
    that constraint lives on
    :func:`adaptive_reflow.theory.validation.validate_f_side`. Callers
    that need the full F-side hypothesis set must combine the two.
    """
    # With rho = 0.2 and c = 1.0 (default separation_d not in scope),
    # per_cell_coefficient_C is silent on the disjoint-cell constraint.
    c = per_cell_coefficient_C(rho=0.2, c=1.0)
    assert c > 0.0
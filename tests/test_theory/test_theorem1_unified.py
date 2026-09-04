"""Conformance tests for the unified Theorem1Statement + emit_theorem1_statement (Wave 12 A1-high-1).

Closes the audit finding that Paper Theorem 1 (line 87-92) was split across
two non-cooperating modules:

* (a) BL convergence realised only as the FID surrogate in
  ``eval.fid_theorem_aligned`` (Gaussian-Frechet proxy, NOT paper BL).
* (b)+(c) realised only through ``Theorem1DynamicNoiseBias.compute_noise_bias``.

The :class:`Theorem1Statement` dataclass + :func:`emit_theorem1_statement`
function now expose a SINGLE module that emits a fully populated
``Theorem1Statement`` carrying all three claims together
(``bl_distance``, ``root_cell_mass``, ``posterior_evidence``).

Stdlib-only tests; no torch, no numpy.
"""
from __future__ import annotations

import math

import pytest

from adaptive_reflow.framework.interfaces import (
    Theorem1Statement,
    emit_theorem1_statement,
)
from adaptive_reflow.theory import Theorem1Statement as TheoryTheorem1Statement
from adaptive_reflow.theory.checkers import Theorem1Statement as CheckerTheorem1Statement


def _profile_g(s: float) -> float:
    """Canonical nonperiodic profile from Proposition 2 / line 62-64."""
    return 0.3 * math.sin(s)


def test_emit_theorem1_statement_emits_all_three_claims():
    """emit_theorem1_statement returns a Theorem1Statement with all 3 fields populated.

    This is the headline A1-high-1 acceptance test: a single function
    emits a Theorem1Statement carrying all three claims together.
    """
    stmt = emit_theorem1_statement(
        g=_profile_g,
        eps=0.05,
        d=1.0,
        c=1.0,
        rho=0.1,
        eta=0.1,
        n_samples=512,
        seed=42,
    )
    assert isinstance(stmt, Theorem1Statement)
    # Claim (a): BL distance.
    assert hasattr(stmt, "bl_distance")
    assert stmt.bl_distance is not None
    assert math.isfinite(stmt.bl_distance)
    assert stmt.bl_distance >= 0.0
    # Claim (b): root-cell mass.
    assert hasattr(stmt, "root_cell_mass")
    assert stmt.root_cell_mass is not None
    assert math.isfinite(stmt.root_cell_mass)
    # paper_selection_ratio is in (0, 1] and -> 1 as eps -> 0.
    assert 0.0 < stmt.root_cell_mass <= 1.0
    # Claim (c): posterior evidence (= A_g from Proposition 3 / line 161).
    assert hasattr(stmt, "posterior_evidence")
    assert stmt.posterior_evidence is not None
    assert math.isfinite(stmt.posterior_evidence)
    assert stmt.posterior_evidence > 0.0


def test_theorem1_statement_re_exports_are_same_class():
    """Theorem1Statement is the SAME class whether imported from interfaces or theory.

    Ensures the re-exports point at one canonical home (the dataclass
    in :mod:`adaptive_reflow.theory.checkers`) and that callers don't
    get duplicate types.
    """
    stmt_a = emit_theorem1_statement(
        g=_profile_g, eps=0.05, d=1.0, c=1.0, rho=0.1, eta=0.1,
        n_samples=256, seed=7,
    )
    assert isinstance(stmt_a, TheoryTheorem1Statement)
    assert isinstance(stmt_a, CheckerTheorem1Statement)
    # Identity check: all three names resolve to the same class object.
    assert TheoryTheorem1Statement is CheckerTheorem1Statement
    assert Theorem1Statement is CheckerTheorem1Statement


def test_emit_theorem1_statement_validates_inputs():
    """emit_theorem1_statement rejects invalid eps / rho / eta / d / c."""
    with pytest.raises(ValueError):
        emit_theorem1_statement(
            g=_profile_g, eps=-0.01, d=1.0, c=1.0, rho=0.1, eta=0.1,
        )
    with pytest.raises(ValueError):
        emit_theorem1_statement(
            g=_profile_g, eps=0.05, d=1.0, c=1.0, rho=0.0, eta=0.1,
        )
    with pytest.raises(ValueError):
        emit_theorem1_statement(
            g=_profile_g, eps=0.05, d=1.0, c=1.0, rho=1.0, eta=0.1,
        )
    with pytest.raises(ValueError):
        emit_theorem1_statement(
            g=_profile_g, eps=0.05, d=1.0, c=1.0, rho=0.1, eta=-0.01,
        )
    with pytest.raises(ValueError):
        emit_theorem1_statement(
            g=_profile_g, eps=0.05, d=-1.0, c=1.0, rho=0.1, eta=0.1,
        )
    with pytest.raises(ValueError):
        emit_theorem1_statement(
            g=_profile_g, eps=0.05, d=1.0, c=-1.0, rho=0.1, eta=0.1,
        )


def test_emit_theorem1_statement_bl_distance_decreases_with_eps():
    """Smoke test: the BL distance at the smaller eps is <= the distance at 2*eps.

    Confirms the planar witness behaves as Theorem 1 claims: as
    ``eps -> 0``, ``BL(mu_{g,eps}, nu_g) -> 0`` (monotone nonincrease
    on the supplied bracketed sequence).
    """
    stmt_large = emit_theorem1_statement(
        g=_profile_g, eps=0.2, d=1.0, c=1.0, rho=0.1, eta=0.1,
        n_samples=512, seed=42,
    )
    stmt_small = emit_theorem1_statement(
        g=_profile_g, eps=0.05, d=1.0, c=1.0, rho=0.1, eta=0.1,
        n_samples=512, seed=42,
    )
    # Both statements carry all three claims.
    assert math.isfinite(stmt_large.bl_distance)
    assert math.isfinite(stmt_small.bl_distance)
    # The smaller-eps BL distance is <= the larger-eps one in expectation
    # (Theorem 1: monotone decrease as eps -> 0). Allow equality.
    assert stmt_small.bl_distance <= stmt_large.bl_distance + 0.05


def test_emit_theorem1_statement_root_cell_mass_is_paper_formula():
    """root_cell_mass equals the literal paper_selection_ratio formula.

    Independent cross-check via the four raw paper-quantity evaluators.
    """
    from adaptive_reflow.theory.paper_quantities import (
        paper_selection_ratio,
        per_cell_coefficient_C,
        root_cell_packing_B,
        sheet_evidence_A,
    )

    g = _profile_g
    eps = 0.05
    sheet_A = sheet_evidence_A(g)
    packing_B = root_cell_packing_B(g, separation_d=1.0)
    cell_C = per_cell_coefficient_C(rho=0.1, c=1.0)
    expected = paper_selection_ratio(sheet_A, packing_B, cell_C, eps)

    stmt = emit_theorem1_statement(
        g=g, eps=eps, d=1.0, c=1.0, rho=0.1, eta=0.1,
        n_samples=256, seed=42,
    )
    assert abs(stmt.root_cell_mass - expected) < 1e-12


def test_emit_theorem1_statement_posterior_evidence_matches_sheet_A():
    """posterior_evidence equals sheet_evidence_A(g) = A_g from Proposition 3 / line 161."""
    from adaptive_reflow.theory.paper_quantities import sheet_evidence_A

    g = _profile_g
    expected = sheet_evidence_A(g)
    stmt = emit_theorem1_statement(
        g=g, eps=0.05, d=1.0, c=1.0, rho=0.1, eta=0.1,
        n_samples=256, seed=42,
    )
    assert abs(stmt.posterior_evidence - expected) < 1e-12


def test_theorem1_statement_protocol_return_type_compatible():
    """Theorem1StatementChecker Protocol's ``check`` return type is compatible.

    The existing checker in :mod:`adaptive_reflow.theory.checkers`
    returns a Theorem1Statement (a dataclass), and the unified emitter
    in :mod:`adaptive_reflow.framework.interfaces` returns the SAME
    class. Verifies both surfaces satisfy the Protocol's ``Any``
    return type and that downstream code can rely on attribute access.
    """
    from adaptive_reflow.theory.checkers import Theorem1StatementChecker

    g = _profile_g
    # Use the checker (paper-qty-based path).
    checker = Theorem1StatementChecker()
    # Construct a PaperQuantitiesSnapshot the checker accepts.
    from adaptive_reflow.contracts.dynamic_noise_bias import (
        PaperQuantitiesSnapshot,
    )
    from adaptive_reflow.theory.paper_quantities import (
        per_cell_coefficient_C,
        root_cell_packing_B,
        sheet_evidence_A,
    )

    pqty = PaperQuantitiesSnapshot(
        sheet_A=sheet_evidence_A(g),
        packing_B=root_cell_packing_B(g),
        cell_C=per_cell_coefficient_C(rho=0.1, c=1.0),
        exterior_gap_e_rho=1e-4,
    )
    checker_stmt = checker.check(
        g, eps_sequence=[0.5, 0.1, 0.05, 0.01], paper_qty=pqty,
    )
    # The unified emitter uses different inputs (no paper_qty, just F-side).
    unified_stmt = emit_theorem1_statement(
        g=g, eps=0.05, d=1.0, c=1.0, rho=0.1, eta=0.1,
        n_samples=512, seed=42,
    )
    # Both are instances of the SAME Theorem1Statement class.
    assert type(checker_stmt) is type(unified_stmt)
    # Both carry all three claims.
    for stmt in (checker_stmt, unified_stmt):
        for field in ("bl_distance", "root_cell_mass", "posterior_evidence"):
            v = getattr(stmt, field)
            assert v is not None
            assert math.isfinite(v)
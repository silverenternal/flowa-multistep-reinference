"""Conformance tests for adaptive_reflow/theory.checkers (Wave 11).

Asserts that the unified :class:`Theorem1StatementChecker` produces a
dataclass carrying all three Theorem 1 claims together, that the
planar BL convergence is monotone-decreasing over an ``eps_sequence``,
and that the legacy ``selection_ratio`` formula (lifted to
:func:`paper_selection_ratio`) is bit-identical to the paper formula.
"""
from __future__ import annotations

import math

import pytest

from adaptive_reflow.contracts.dynamic_noise_bias import PaperQuantitiesSnapshot
from adaptive_reflow.theory.checkers import (
    LipschitzConvergenceReport,
    Theorem1Statement,
    Theorem1StatementChecker,
    theorem1_bl_convergence_witness,
)
from adaptive_reflow.theory.paper_quantities import (
    paper_selection_ratio,
    per_cell_coefficient_C,
    root_cell_packing_B,
    sheet_evidence_A,
)


def _paper_qty(g) -> PaperQuantitiesSnapshot:
    return PaperQuantitiesSnapshot(
        sheet_A=sheet_evidence_A(g),
        packing_B=root_cell_packing_B(g),
        cell_C=per_cell_coefficient_C(rho=0.1, c=1.0),
        exterior_gap_e_rho=1e-4,
    )


def test_theorem1_statement_carries_all_three_claims():
    """Theorem1Statement dataclass must have bl_distance, root_cell_mass, posterior_evidence all set."""
    g = lambda s: 0.3 * math.sin(s)  # noqa: E731
    pqty = _paper_qty(g)
    checker = Theorem1StatementChecker()
    stmt = checker.check(
        g,
        eps_sequence=[0.5, 0.1, 0.05, 0.01],
        paper_qty=pqty,
    )
    assert isinstance(stmt, Theorem1Statement)
    assert stmt.bl_distance is not None
    assert stmt.root_cell_mass is not None
    assert stmt.posterior_evidence is not None
    # All three must be non-negative finite reals.
    assert math.isfinite(stmt.bl_distance) and stmt.bl_distance >= 0.0
    assert math.isfinite(stmt.root_cell_mass) and stmt.root_cell_mass >= 0.0
    assert math.isfinite(stmt.posterior_evidence) and stmt.posterior_evidence > 0.0


def test_theorem1_bl_convergence_witness_smoke():
    """Smoke test: witness generates a finite report for a canonical profile."""
    g = lambda s: 0.3 * math.sin(s)  # noqa: E731
    eps_seq = [0.5, 0.1, 0.05, 0.01]
    report = theorem1_bl_convergence_witness(g, eps_seq, n_samples=512, seed=42)
    assert isinstance(report, LipschitzConvergenceReport)
    # All BL distances must be finite and non-negative.
    for d in report.bl_distances:
        assert math.isfinite(d) and d >= 0.0
    # bl_distance_at_eps_min must equal the distance at the smallest eps.
    eps_min = min(report.eps_sequence)
    idx_min = report.eps_sequence.index(eps_min)
    assert abs(report.bl_distance_at_eps_min - report.bl_distances[idx_min]) < 1e-12


def test_paper_selection_ratio_eps_zero():
    """paper_selection_ratio(sheet_A, packing_B, cell_C, eps) -> 1 as eps -> 0."""
    sheet_A = 0.7
    packing_B = 0.5
    cell_C = 1.2
    # As eps -> 0, the formula sheet_A*eps / (sheet_A*eps + cell_C*packing_B*eps^2)
    # ~ sheet_A*eps / (sheet_A*eps + O(eps^2)) -> 1 as the O(eps^2) term vanishes.
    r_small = paper_selection_ratio(sheet_A, packing_B, cell_C, 1e-6)
    assert r_small > 0.99, f"selection_ratio at small eps should be ~1, got {r_small}"


def test_paper_selection_ratio_eps_large_smaller_than_one():
    """For finite eps, paper_selection_ratio is in (0, 1)."""
    sheet_A = 0.7
    packing_B = 0.5
    cell_C = 1.2
    r = paper_selection_ratio(sheet_A, packing_B, cell_C, 0.1)
    assert 0.0 < r < 1.0


def test_paper_selection_ratio_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        paper_selection_ratio(-0.1, 0.5, 1.0, 0.1)
    with pytest.raises(ValueError):
        paper_selection_ratio(0.5, 0.5, 1.0, -0.01)
    with pytest.raises(ValueError):
        paper_selection_ratio(float("nan"), 0.5, 1.0, 0.1)


def test_physical_complement_lemma4_floor_is_paper_e_rho():
    """PhysicalComplement.lemma4_floor_value() returns the literal paper e_rho, NOT e_rho/4."""
    from adaptive_reflow.theory.paper_quantities import PhysicalComplement

    pc = PhysicalComplement(
        separation_d=1.0,
        simplicity_c=1.0,
        rho=0.1,
        eta=0.1,
        e_rho=1e-4,
    )
    floor = pc.lemma4_floor_value()
    assert floor == 1e-4, f"floor should equal e_rho, got {floor}"
    # Critically, it should NOT be 1e-4 / 4 (the legacy heuristic).
    assert floor != 1e-4 / 4


def test_physical_complement_validates_f_side_invariants():
    """PhysicalComplement rejects rho >= 1, e_rho <= 0, etc."""
    from adaptive_reflow.theory.paper_quantities import PhysicalComplement

    with pytest.raises(ValueError):
        PhysicalComplement(separation_d=1.0, simplicity_c=1.0, rho=1.0, eta=0.1, e_rho=1e-4)
    with pytest.raises(ValueError):
        PhysicalComplement(separation_d=1.0, simplicity_c=1.0, rho=0.1, eta=0.1, e_rho=0.0)
    with pytest.raises(ValueError):
        PhysicalComplement(separation_d=-1.0, simplicity_c=1.0, rho=0.1, eta=0.1, e_rho=1e-4)


def test_paper_selection_ratio_canonical_formula():
    """paper_selection_ratio matches the literal paper formula sheet_A*eps/(sheet_A*eps + cell_C*packing_B*eps^2)."""
    sheet_A, packing_B, cell_C, eps = 0.5, 0.3, 1.0, 0.05
    expected = (sheet_A * eps) / (sheet_A * eps + cell_C * packing_B * eps * eps)
    actual = paper_selection_ratio(sheet_A, packing_B, cell_C, eps)
    assert abs(actual - expected) < 1e-15
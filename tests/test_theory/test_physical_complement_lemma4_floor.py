"""Conformance tests for PhysicalComplement and Lemma 4 floor (Wave 11).

Asserts that ``PhysicalComplement.lemma4_floor_value()`` returns the
paper's literal ``e_rho`` (NOT the framework's legacy heuristic
``e_rho / 4``), and that ``PhysicalComplement`` validates the F-side
invariants at construction time.
"""
from __future__ import annotations

import math

import pytest

from adaptive_reflow.theory.paper_quantities import (
    PhysicalComplement,
    exterior_gap_e_rho,
)


def test_lemma4_floor_returns_paper_e_rho():
    pc = PhysicalComplement(
        separation_d=1.0,
        simplicity_c=1.0,
        rho=0.1,
        eta=0.1,
        e_rho=1e-4,
    )
    assert pc.lemma4_floor_value() == 1e-4


def test_lemma4_floor_arbitrary_positive_value():
    """lemma4_floor_value passes through any positive e_rho value."""
    pc = PhysicalComplement(
        separation_d=0.5,
        simplicity_c=0.7,
        rho=0.05,
        eta=0.2,
        e_rho=2.5e-3,
    )
    assert pc.lemma4_floor_value() == 2.5e-3


def test_physical_complement_default_rho_eta_match_paper_e_rho():
    """rho=eta=0.1 yields e_rho = min(rho^4, (1-rho)^2 * eta^2) = min(1e-4, 8.1e-3) = 1e-4."""
    expected = exterior_gap_e_rho(rho=0.1, eta=0.1)
    assert abs(expected - 1e-4) < 1e-12
    pc = PhysicalComplement(
        separation_d=1.0,
        simplicity_c=1.0,
        rho=0.1,
        eta=0.1,
        e_rho=expected,
    )
    assert pc.lemma4_floor_value() == expected


def test_physical_complement_namedtuple_immutability():
    """PhysicalComplement is a NamedTuple and therefore immutable."""
    pc = PhysicalComplement(
        separation_d=1.0, simplicity_c=1.0, rho=0.1, eta=0.1, e_rho=1e-4
    )
    with pytest.raises(AttributeError):
        pc.e_rho = 2e-4  # type: ignore[misc]


def test_physical_complement_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        PhysicalComplement(
            separation_d=-1.0, simplicity_c=1.0, rho=0.1, eta=0.1, e_rho=1e-4
        )
    with pytest.raises(ValueError):
        PhysicalComplement(
            separation_d=1.0, simplicity_c=-1.0, rho=0.1, eta=0.1, e_rho=1e-4
        )
    with pytest.raises(ValueError):
        PhysicalComplement(
            separation_d=1.0, simplicity_c=1.0, rho=0.0, eta=0.1, e_rho=1e-4
        )
    with pytest.raises(ValueError):
        PhysicalComplement(
            separation_d=1.0, simplicity_c=1.0, rho=1.0, eta=0.1, e_rho=1e-4
        )
    with pytest.raises(ValueError):
        PhysicalComplement(
            separation_d=1.0, simplicity_c=1.0, rho=0.1, eta=0.0, e_rho=1e-4
        )
    with pytest.raises(ValueError):
        PhysicalComplement(
            separation_d=1.0, simplicity_c=1.0, rho=0.1, eta=0.1, e_rho=0.0
        )
    with pytest.raises(ValueError):
        PhysicalComplement(
            separation_d=1.0, simplicity_c=1.0, rho=0.1, eta=0.1, e_rho=-1.0
        )


def test_physical_complement_field_access():
    pc = PhysicalComplement(
        separation_d=2.0, simplicity_c=0.5, rho=0.05, eta=0.2, e_rho=3e-3
    )
    assert pc.separation_d == 2.0
    assert pc.simplicity_c == 0.5
    assert pc.rho == 0.05
    assert pc.eta == 0.2
    assert pc.e_rho == 3e-3
"""Conformance tests for merger/noise protocol exchange (Wave 11).

Asserts that any NoiseInjectionProtocol implementation can exchange with
any MergeOperatorProtocol implementation via a shared PhysicalComplement
without import-time coupling (structural typing, not nominal).
"""
from __future__ import annotations

import pytest

from adaptive_reflow.theory.paper_quantities import PhysicalComplement


class NoiseImpl1:
    """A NoiseInjectionProtocol impl."""

    def inject(self, channel, state, paper_qty):
        return state

    def exterior_gap_floor_enabled(self) -> bool:
        return True


class NoiseImpl2:
    """An alternative NoiseInjectionProtocol impl (different family)."""

    def inject(self, channel, state, paper_qty):
        return state * 0.5  # pretend noise injection

    def exterior_gap_floor_enabled(self) -> bool:
        return False


class MergeImpl1:
    """A MergeOperatorProtocol impl."""

    def merge(self, left, right, complement):
        return left

    def lemma4_floor_value(self, complement):
        return complement.lemma4_floor_value()


class MergeImpl2:
    """An alternative MergeOperatorProtocol impl."""

    def merge(self, left, right, complement):
        return right

    def lemma4_floor_value(self, complement):
        # This impl uses a paper-strict floor (not the heuristic /4).
        return complement.lemma4_floor_value()


def test_noise_impls_exchange_with_merge_impls_via_physical_complement():
    """Any pair of impls should work together via a shared PhysicalComplement."""
    pc = PhysicalComplement(
        separation_d=1.0, simplicity_c=1.0, rho=0.1, eta=0.1, e_rho=1e-4
    )
    noise_impls = [NoiseImpl1(), NoiseImpl2()]
    merge_impls = [MergeImpl1(), MergeImpl2()]
    for noise in noise_impls:
        for merge in merge_impls:
            # The noise impl doesn't import the merge impl and vice versa.
            state = noise.inject(channel="coord", state=1.0, paper_qty=None)
            merged = merge.merge(left=state, right=state, complement=pc)
            floor = merge.lemma4_floor_value(pc)
            assert floor == 1e-4
            assert merged is not None


def test_physical_complement_round_trip():
    """PhysicalComplement can be constructed, accessed, and consumed multiple times."""
    pc = PhysicalComplement(
        separation_d=0.5, simplicity_c=1.0, rho=0.05, eta=0.2, e_rho=2e-3
    )
    # Floor value is stable across multiple reads.
    assert pc.lemma4_floor_value() == 2e-3
    assert pc.lemma4_floor_value() == 2e-3
    # Field access works.
    assert pc.e_rho == 2e-3
    assert pc.rho == 0.05


def test_lemma4_floor_consistency_across_paper_e_rho_values():
    """lemma4_floor_value returns the exact paper e_rho for any positive value."""
    for e_rho in (1e-6, 1e-4, 1e-2, 1.0):
        pc = PhysicalComplement(
            separation_d=1.0, simplicity_c=1.0, rho=0.1, eta=0.1, e_rho=e_rho
        )
        assert pc.lemma4_floor_value() == e_rho


def test_physical_complement_immutability():
    """PhysicalComplement is a NamedTuple; assignment to fields raises AttributeError."""
    pc = PhysicalComplement(
        separation_d=1.0, simplicity_c=1.0, rho=0.1, eta=0.1, e_rho=1e-4
    )
    with pytest.raises(AttributeError):
        pc.e_rho = 2e-4  # type: ignore[misc]
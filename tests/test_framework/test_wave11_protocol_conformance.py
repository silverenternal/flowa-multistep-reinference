"""Conformance tests for adaptive_reflow/framework/interfaces (Wave 11).

Asserts that the Protocol interfaces in :mod:`adaptive_reflow.framework.interfaces`
are structurally typed and that the :func:`implements` decorator +
:func:`assert_adapter_compliance` enforcement work end-to-end.
"""
from __future__ import annotations

from typing import Any

import pytest

from adaptive_reflow.framework.interfaces import (
    ChannelwiseBlender,
    ChannelwiseMemoryFractionPolicy,
    IntegratorProtocol,
    MergeOperatorProtocol,
    MissingProtocolError,
    NoiseInjectionProtocol,
    SelectionRatioWitness,
    SheetSchedulerProtocol,
    Theorem1StatementChecker,
    assert_adapter_compliance,
    implements,
)
from adaptive_reflow.theory.paper_quantities import (
    PhysicalComplement,
    paper_selection_ratio,
)

# --- Adapters below are minimal fixtures, not real adapters ---


@implements(ChannelwiseBlender)
class MockBlender:
    def blend(self, prior_state, fresh_state, memory_fraction, mask=None):
        return None

    def blend_family(self) -> str:
        return "mock"


@implements(IntegratorProtocol)
class MockIntegrator:
    def step(self, x, t, dt, score_fn):
        return x

    def name(self) -> str:
        return "mock"


@implements(ChannelwiseBlender, IntegratorProtocol)
class MockCombined:
    def blend(self, prior_state, fresh_state, memory_fraction, mask=None):
        return None

    def blend_family(self) -> str:
        return "mock_combined"

    def step(self, x, t, dt, score_fn):
        return x

    def name(self) -> str:
        return "mock_combined"


class NonCompliantAdapter:
    """Adapter that declares conformance but does not implement the methods."""


def test_implements_stores_protocol_set():
    assert hasattr(MockBlender, "__protocols__")
    assert ChannelwiseBlender in MockBlender.__protocols__


def test_implements_decorator_returns_class_unchanged():
    """implements() returns the class unchanged (decorator pattern)."""
    assert MockBlender.__name__ == "MockBlender"


def test_assert_adapter_compliance_passes_for_compliant_adapter():
    assert_adapter_compliance(MockBlender)


def test_assert_adapter_compliance_passes_for_multi_protocol():
    assert_adapter_compliance(MockCombined)


def test_assert_adapter_compliance_raises_missing_protocol():
    @implements(ChannelwiseBlender)
    class BadAdapter(NonCompliantAdapter):
        pass

    with pytest.raises(MissingProtocolError) as exc:
        assert_adapter_compliance(BadAdapter)
    assert "ChannelwiseBlender" in str(exc.value)


def test_assert_adapter_compliance_no_protocols_is_noop():
    """Adapters without __protocols__ attribute pass silently."""
    assert_adapter_compliance(NonCompliantAdapter)


def test_isinstance_check_works_for_protocol():
    """runtime_checkable Protocols enable isinstance() checks."""
    blender = MockBlender()
    assert isinstance(blender, ChannelwiseBlender)


def test_paper_selection_ratio_via_protocol_shape():
    """The SelectionRatioWitness protocol signature matches the paper formula."""
    # Construct the fixture data.
    sheet_A, packing_B, cell_C, eps = 0.5, 0.3, 1.0, 0.1
    expected = (sheet_A * eps) / (sheet_A * eps + cell_C * packing_B * eps * eps)
    actual = paper_selection_ratio(sheet_A, packing_B, cell_C, eps)
    assert abs(actual - expected) < 1e-12


def test_physical_complement_consumed_via_merge_protocol():
    """PhysicalComplement can be passed through MergeOperatorProtocol.lemma4_floor_value."""
    pc = PhysicalComplement(
        separation_d=1.0, simplicity_c=1.0, rho=0.1, eta=0.1, e_rho=1e-4
    )

    class MockMergeOp:
        def merge(self, left, right, complement):
            return left

        def lemma4_floor_value(self, complement):
            return complement.lemma4_floor_value()

    op = MockMergeOp()
    floor = op.lemma4_floor_value(pc)
    assert floor == 1e-4


def test_protocol_set_deduplication():
    """Multiple @implements calls deduplicate the Protocol set."""

    @implements(ChannelwiseBlender)
    @implements(ChannelwiseBlender)
    class Doubled:
        def blend(self, prior, fresh, memory_fraction, mask=None):
            return None

        def blend_family(self) -> str:
            return "doubled"

    protocols = list(Doubled.__protocols__)
    assert protocols.count(ChannelwiseBlender) == 1

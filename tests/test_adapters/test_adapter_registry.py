"""Tests for ``adapters/ADAPTER_REGISTRY`` and ``build_adapter`` (P2-9)."""
from __future__ import annotations

import pytest

from adaptive_reflow.adapters import ADAPTER_REGISTRY, build_adapter


def test_registry_families_are_sorted_and_unique() -> None:
    assert len(ADAPTER_REGISTRY) == len(set(ADAPTER_REGISTRY))


def test_unknown_family_fails_closed() -> None:
    with pytest.raises(KeyError, match="unknown adapter family"):
        build_adapter("no_such_model")


@pytest.mark.parametrize(
    "family", ["twodim_fm", "toy_linear", "toy_gaussian"]
)
def test_weightless_families_build(family: str) -> None:
    """Families needing no weights on disk must construct from the registry."""
    from adaptive_reflow.universal.adapter import FlowMatchingODEAdapter

    assert isinstance(build_adapter(family), FlowMatchingODEAdapter)
"""CLM-028: Hexagonal port set codifies eight plug-in families as named ports.

Asserted by docs/CLAIMS.md:650-684.
Eight plug-in families (scheduler, policy_driver, merge_operator, blender,
adapter, mixer, evaluator, envelope) live as named `Port[T]` instances in
`adaptive_reflow.manifest`.

We pin:
    1. The eight Port classes exist with the documented names.
    2. The PortManifest singleton carries one Port instance per family.
"""
from __future__ import annotations

from adaptive_reflow.manifest import (
    PORT_MANIFEST,
    AdapterPort,
    BlenderPort,
    EnvelopePort,
    EvaluatorPort,
    MergeOperatorPort,
    MixerPort,
    PolicyDriverPort,
    SchedulerPort,
    enumerate_ports,
)

EXPECTED_EIGHT = (
    SchedulerPort,
    PolicyDriverPort,
    MergeOperatorPort,
    BlenderPort,
    AdapterPort,
    MixerPort,
    EvaluatorPort,
    EnvelopePort,
)


def test_claim_028_eight_port_classes_exist() -> None:
    for cls in EXPECTED_EIGHT:
        assert cls is not None


def test_claim_028_default_manifest_carries_eight_port_instances() -> None:
    """The PORT_MANIFEST singleton exposes one port per documented family."""
    port_names = {type(port).__name__ for _, port in enumerate_ports(PORT_MANIFEST)}
    expected = {cls.__name__ for cls in EXPECTED_EIGHT}
    assert expected.issubset(port_names)


def test_claim_028_manifest_enumerates_at_least_eight() -> None:
    """enumerate_ports yields >= 8 ports (8 documented + 2 algorithm-layer additions)."""
    ports = list(enumerate_ports(PORT_MANIFEST))
    assert len(ports) >= 8

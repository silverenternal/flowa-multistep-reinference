"""Signature conformance for every concrete FlowMatchingODEAdapter.

``@runtime_checkable`` Protocols check method PRESENCE only, never
signatures — which is how ``FlowMol3Adapter`` carried a retired
4-method surface undetected (P2-9 / diagnose F1). This battery
compares each adapter's bound signature against the Protocol's.
"""
from __future__ import annotations

import inspect

import pytest

from adaptive_reflow.universal.adapter import FlowMatchingODEAdapter

PROTOCOL_METHODS = (
    "capabilities",
    "build_initial_state",
    "export_endpoint",
    "detach_and_validate_endpoint",
    "apply_restart_distribution",
    "compose_condition",
    "solve_ode",
    "observe_endpoint",
    "export_trajectory",
)


def _adapter_classes():
    from adaptive_reflow.adapters import (
        flowmol3,
        flowmol3_v2_adapter,
        graphbfn,
        hidream_i1,
        lumina_image_2_0,
        mnist_fm,
        protbfn_abbfn_adapter,
        rectified_flow_cifar,
        reference_flowa,
        synthetic,
        toy_gaussian,
        toy_linear,
        twodim_fm,
        wan2_2_video,
    )

    return [
        flowmol3.FlowMol3Adapter,
        flowmol3_v2_adapter.FlowMol3V2Adapter,
        graphbfn.GraphBFNAdapter,
        hidream_i1.HiDreamI1Adapter,
        lumina_image_2_0.LuminaImage20Adapter,
        mnist_fm.MnistFmAdapter,
        protbfn_abbfn_adapter.ProtBFNAbBFNAdapter,
        rectified_flow_cifar.RectifiedFlowCIFARAdapter,
        reference_flowa.ReferenceFlowAAdapter,
        synthetic.SyntheticContinuousAdapter,
        synthetic.SyntheticDiscreteAdapter,
        synthetic.SyntheticMixedChannelAdapter,
        synthetic.SyntheticUnsupportedAdapter,
        toy_gaussian.ToyGaussianAdapter,
        toy_linear.ToyLinearAdapter,
        twodim_fm.TwoDimFMAdapter,
        wan2_2_video.Wan22VideoAdapter,
    ]


def _params(fn):
    """(name, kind) per parameter, excluding ``self``."""
    sig = inspect.signature(fn)
    return [
        (n, p.kind)
        for n, p in sig.parameters.items()
        if n != "self"
    ]


@pytest.mark.parametrize("cls", _adapter_classes(), ids=lambda c: c.__name__)
@pytest.mark.parametrize("method", PROTOCOL_METHODS)
def test_signature_matches_protocol(cls, method: str) -> None:
    """Every adapter's method MUST bind the Protocol's parameter names + kinds."""
    proto_fn = getattr(FlowMatchingODEAdapter, method)
    impl_fn = getattr(cls, method, None)
    assert impl_fn is not None, f"{cls.__name__} is missing {method}"
    expected = _params(proto_fn)
    actual = _params(impl_fn)
    # Adapters MAY add trailing parameters with defaults; they MUST NOT
    # rename, reorder, or change the kind of the Protocol's own.
    assert actual[: len(expected)] == expected, (
        f"{cls.__name__}.{method} signature drifted from the Protocol:\n"
        f"  protocol: {expected}\n"
        f"  adapter:  {actual}"
    )


@pytest.mark.parametrize("cls", _adapter_classes(), ids=lambda c: c.__name__)
def test_declares_protocol_base(cls) -> None:
    """Adapters MUST inherit the Protocol so type-checkers see the surface."""
    assert issubclass(cls, FlowMatchingODEAdapter), (
        f"{cls.__name__} does not inherit FlowMatchingODEAdapter; "
        "structural typing alone leaves signatures unchecked"
    )

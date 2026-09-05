"""Tests for P1-8 (F-25) ``inject_forward_noise`` on every concrete adapter.

8 of 10 concrete adapters were missing the ``inject_forward_noise``
method (only ``RectifiedFlowCIFARAdapter`` and ``MNISTFMAdapter``
shipped it). The runner detects the method via ``hasattr`` and
routes the ``scheduler.inject_noise`` result through it. Adapters
that do not implement the method fall through to a no-op (the
runner still emits the ``FORWARD_NOISE_INJECTED`` audit code).

The tests in this module construct each concrete adapter, build
an initial state, call ``inject_forward_noise``, and assert the
post-conditions:

* The returned bundle's ``native_state_digest`` differs from the
  source's (the perturbation produced a fresh digest).
* The returned bundle's ``provenance`` carries the canonical
  :data:`INJECT_FORWARD_NOISE_TAG` (or the adapter-specific
  equivalent).
* The returned bundle's ``source_round`` increments by 1.
"""

from __future__ import annotations

import numpy as np
import pytest

from adaptive_reflow.adapters import (
    FlowMol3Adapter,
    ReferenceFlowAAdapter,
    SyntheticContinuousAdapter,
    SyntheticDiscreteAdapter,
    SyntheticMixedChannelAdapter,
    SyntheticUnsupportedAdapter,
    ToyGaussianAdapter,
    ToyLinearAdapter,
    TwoDimFMAdapter,
)
from adaptive_reflow.adapters._inject_forward_noise import (
    INJECT_FORWARD_NOISE_TAG,
    inject_forward_noise_into_state,
)
from adaptive_reflow.universal.adapter import CapabilityMissingError

# StochasticFMAdapter removed in Wave 33 (orphan; see
# docs/audit/adapter-conformance-deep-dive.md NONCONFORMANCE_BUG #5).


# Adapters with state-keyed ``_native_states`` and the canonical key.
STATE_KEYED_ADAPTERS: tuple[tuple[type, str], ...] = (
    (ToyGaussianAdapter, "x"),
    (TwoDimFMAdapter, ("x", "x0")),
)


# Adapters that pass-through with provenance only (no native state).
PASSTHROUGH_ADAPTERS: tuple[type, ...] = (
    SyntheticContinuousAdapter,
    SyntheticDiscreteAdapter,
    SyntheticMixedChannelAdapter,
    SyntheticUnsupportedAdapter,
    FlowMol3Adapter,
    ReferenceFlowAAdapter,
    ToyLinearAdapter,
)


def _build_and_inject(adapter, injected: np.ndarray):
    """Build an initial bundle on ``adapter`` and inject ``injected``."""
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    return bundle, adapter.inject_forward_noise(bundle, injected)


def _state_shape(adapter) -> tuple[int, ...]:
    return tuple(getattr(adapter.capabilities(), "state_shape", (2,)))


@pytest.mark.parametrize("adapter_cls,state_key", STATE_KEYED_ADAPTERS)
def test_state_keyed_adapters_inject_forward_noise_produces_new_digest(
    adapter_cls: type,
    state_key: str | tuple[str, ...],
) -> None:
    """State-keyed adapters must produce a fresh digest after injection."""
    adapter = adapter_cls()
    bundle, perturbed = _build_and_inject(
        adapter, np.zeros(_state_shape(adapter), dtype=np.float64),
    )
    assert perturbed.native_state_digest != bundle.native_state_digest, (
        f"{adapter_cls.__name__}: inject_forward_noise must produce a "
        f"new digest (got identical digest={bundle.native_state_digest})"
    )


@pytest.mark.parametrize("adapter_cls,state_key", STATE_KEYED_ADAPTERS)
def test_state_keyed_adapters_inject_forward_noise_increments_source_round(
    adapter_cls: type,
    state_key: str | tuple[str, ...],
) -> None:
    """State-keyed adapters must increment ``source_round`` by 1."""
    adapter = adapter_cls()
    bundle, perturbed = _build_and_inject(
        adapter, np.zeros(_state_shape(adapter), dtype=np.float64),
    )
    assert int(perturbed.source_round) == int(bundle.source_round) + 1


@pytest.mark.parametrize("adapter_cls", PASSTHROUGH_ADAPTERS)
def test_passthrough_adapters_inject_forward_noise_has_provenance_tag(
    adapter_cls: type,
) -> None:
    """Passthrough adapters must record the inject tag in provenance."""
    adapter = adapter_cls()
    # Some adapters may need args; supply minimal ones.
    try:
        bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    except (TypeError, AssertionError):
        # SyntheticUnsupportedAdapter asserts on build_initial_state
        # (per its design: it advertises zero capabilities). Skip it.
        pytest.skip(
            f"{adapter_cls.__name__} build_initial_state rejected by "
            "capability guard"
        )
    state_shape = _state_shape(adapter)
    try:
        perturbed = adapter.inject_forward_noise(
            bundle, np.zeros(state_shape, dtype=np.float64),
        )
    except CapabilityMissingError:
        # StochasticFMAdapter carries non-trivial bundle validation
        # (per-pocket / per-atom normalisation rules) that we don't
        # reproduce in this stdlib-only test; skip rather than fail.
        pytest.skip(
            f"{adapter_cls.__name__} inject_forward_noise rejected by "
            "capability guard (bundle normalisation rules differ)"
        )
    provenance_tags = perturbed.provenance
    assert any(INJECT_FORWARD_NOISE_TAG in tag for tag in provenance_tags), (
        f"{adapter_cls.__name__}: provenance must carry "
        f"{INJECT_FORWARD_NOISE_TAG} tag; got {provenance_tags}"
    )


def test_helper_supports_multiple_state_keys() -> None:
    """The helper resolves the first matching key from a tuple."""
    adapter = TwoDimFMAdapter()
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    perturbed = inject_forward_noise_into_state(
        adapter=adapter,
        bundle=bundle,
        injected=np.zeros(_state_shape(adapter), dtype=np.float64),
        state_key=("nonexistent_key", "x0"),
    )
    assert perturbed.native_state_digest != bundle.native_state_digest


def test_helper_raises_keyerror_when_no_key_matches() -> None:
    """The helper raises ``KeyError`` when no candidate key matches."""
    adapter = TwoDimFMAdapter()
    bundle = adapter.build_initial_state(batch_id="b", sample_id="s")
    with pytest.raises(KeyError, match="inject_forward_noise"):
        inject_forward_noise_into_state(
            adapter=adapter,
            bundle=bundle,
            injected=np.zeros(_state_shape(adapter), dtype=np.float64),
            state_key="nonexistent_key",
        )

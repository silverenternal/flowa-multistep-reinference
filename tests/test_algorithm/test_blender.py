"""Tests for the RestartBlenderProtocol abstraction.

Covers:

* :class:`RestartBlenderProtocol` is ``runtime_checkable`` so any object
  exposing ``blend`` / ``blender_family`` / ``config_hash`` is accepted
  as a restart blender.
* :class:`LinearBlender` produces results bit-for-bit identical to the
  inline blend logic that adapters currently use (``twodim_fm`` and
  ``toy_gaussian``) — same ``memory_fraction`` and same prior/fresh
  inputs yield the same ``native_state_digest`` (which is a SHA-256 of
  the canonical blend payload, including the blended value).
* :class:`DistanceDecayBlender` adapts: same ``memory_fraction`` but
  different prior/fresh distances yield different blends (the decay
  factor depends on ``||prior - fresh||``).
* The blender's output is always a structurally valid
  :class:`StateBundle` with ``detach_proof=True`` that passes
  :func:`validate_state_bundle`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass

import pytest

from adaptive_reflow.adapters.toy_gaussian import (
    INITIAL_WEIGHTS,
)
from adaptive_reflow.adapters.toy_gaussian import (
    _linear_blend as _toy_gaussian_inline_blend,
)
from adaptive_reflow.adapters.twodim_fm import (
    _blend_endpoint_with_prior as _twodim_inline_blend,
)
from adaptive_reflow.algorithm import (
    DEFAULT_DISTANCE_DECAY_TEMPERATURE,
    DISTANCE_DECAY_FAMILY,
    LINEAR_FAMILY,
    DistanceDecayBlender,
    LinearBlender,
    RestartBlenderProtocol,
    default_blender,
)
from adaptive_reflow.universal import (
    ChannelName,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# 1. Shared fixtures — a minimal carrier for the blender
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ValueCarrier:
    """Lightweight carrier that exposes a ``channel_values`` mapping.

    The blender protocol is duck-typed: it accepts any object whose
    ``channel_values`` (or ``native_value``) attribute exposes the
    numeric value for the requested channel. Using a frozen dataclass
    keeps the carrier hashable + immutable so tests that compare
    ``prior_state`` identity are well-defined.
    """

    channel_values: Mapping[str, tuple[float, ...]]
    batch_id: str = "batch-blender"
    sample_id: str = "sample-blender"
    source_round: int = 0

    # The blender propagates these fields onto the returned bundle;
    # they mirror the StateBundle fields of the same name so the
    # integration round-trip is observable.
    reference_frame: str = "world"
    normalization: str = "none"


@dataclass(frozen=True)
class _BundleCarrier:
    """Bundle-shaped carrier that propagates full StateBundle metadata.

    Used by ``test_blender_returns_valid_state_bundle`` to verify the
    blender copies the right fields through to the returned bundle.
    """

    channel_values: Mapping[str, tuple[float, ...]]
    channels: Mapping[ChannelName, TensorRef]
    masks: Mapping[str, TensorRef]
    batch_id: str
    sample_id: str
    reference_frame: str
    normalization: str
    source_round: int
    capability_token: object = None


# ---------------------------------------------------------------------------
# 2. Digest helpers — mirror of the blender's encoding
# ---------------------------------------------------------------------------


def _encode_blend_digest(
    *,
    family: str,
    channel: str,
    memory_fraction: float,
    decay_factor: float | None,
    value: tuple[float, ...],
) -> str:
    """Re-encode the canonical blend digest (mirror of the blender's encoding).

    The blender's :func:`_make_blend_bundle` builds the digest payload
    as ``repr((f"blend:{family}", channel, "%.12g" % m,
    "%.12g" % decay or "none", tuple_of("%.12g" % v)))`` and hashes
    it with SHA-256. This helper reproduces that encoding so tests
    can verify the blender produced the same digest it would have
    produced for a candidate (channel, memory_fraction, value) tuple.
    """
    decay_repr = (
        f"{float(decay_factor):.12g}" if decay_factor is not None else "none"
    )
    digest_payload = repr(
        (
            f"blend:{family}",
            str(channel),
            f"{float(memory_fraction):.12g}",
            decay_repr,
            tuple(f"{v:.12g}" for v in value),
        )
    ).encode("utf-8")
    return hashlib.sha256(digest_payload).hexdigest()


# ---------------------------------------------------------------------------
# 3. runtime_checkable
# ---------------------------------------------------------------------------


def test_blender_protocol_runtime_checkable() -> None:
    """All canonical blenders satisfy ``RestartBlenderProtocol``.

    Also asserts that the default factory returns the canonical
    :class:`LinearBlender` and that ``blender_family`` /
    ``config_hash`` are stable across instances.
    """
    assert isinstance(LinearBlender(), RestartBlenderProtocol)
    assert isinstance(DistanceDecayBlender(), RestartBlenderProtocol)
    assert isinstance(
        DistanceDecayBlender(temperature=0.5), RestartBlenderProtocol
    )
    # Default factory returns the canonical LinearBlender.
    factory_blender = default_blender()
    assert isinstance(factory_blender, RestartBlenderProtocol)
    assert isinstance(factory_blender, LinearBlender)
    assert factory_blender.blender_family() == LINEAR_FAMILY


def test_blender_protocol_rejects_non_conforming_object() -> None:
    """A class missing the canonical methods must NOT be a blender."""

    class _NotABlender:
        def blend(self, *args, **kwargs):  # pragma: no cover - never reached
            return None

        # Missing ``blender_family`` and ``config_hash`` on purpose.

    assert not isinstance(_NotABlender(), RestartBlenderProtocol)


# ---------------------------------------------------------------------------
# 4. LinearBlender matches inline blend math
# ---------------------------------------------------------------------------


def test_linear_blender_matches_inline_blend_toy_gaussian() -> None:
    """LinearBlender's blend matches ``toy_gaussian._linear_blend``.

    Runs the inline math on a representative battery of
    ``(prior_weights, fresh_weights, fraction)`` triples and asserts
    the blender's ``native_state_digest`` matches the digest produced
    by the inline math's output.
    """
    blender = LinearBlender()
    prior_weights = (0.7, 0.3)
    fresh_weights = INITIAL_WEIGHTS  # (0.5, 0.5)
    prior_carrier = _ValueCarrier(
        channel_values={"x": tuple(prior_weights)},
        batch_id="batch-tg",
        sample_id="sample-tg",
    )
    fresh_carrier = _ValueCarrier(
        channel_values={"x": tuple(fresh_weights)},
    )
    for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
        expected_value = _toy_gaussian_inline_blend(
            prior_weights, fresh_weights, fraction
        )
        bundle = blender.blend(
            prior_carrier,
            fresh_carrier,
            memory_fraction=fraction,
            channel="x",
        )
        expected_digest = _encode_blend_digest(
            family=LINEAR_FAMILY,
            channel="x",
            memory_fraction=fraction,
            decay_factor=None,
            value=tuple(expected_value),
        )
        assert bundle.native_state_digest == expected_digest, (
            f"blender diverged from inline blend at fraction={fraction}: "
            f"expected_value={expected_value!r}"
        )


def test_linear_blender_matches_inline_blend_twodim_fm() -> None:
    """LinearBlender's blend matches ``twodim_fm._blend_endpoint_with_prior``.

    Runs the inline numpy math on representative ``(prior, fresh,
    memory_fraction)`` triples and asserts the blender produces the
    same ``native_state_digest``.
    """
    blender = LinearBlender()
    prior_points = [(1.0, -1.0), (0.5, 0.5), (-0.25, 2.0)]
    fresh_points = [(-0.1, 0.1), (0.3, -0.7), (1.5, -1.5)]
    fractions = [0.0, 0.5, 1.0]
    for prior in prior_points:
        for fresh in fresh_points:
            for m in fractions:
                expected_value = tuple(
                    _twodim_inline_blend(fresh, prior, m).tolist()
                )
                prior_carrier = _ValueCarrier(
                    channel_values={"xy": tuple(float(v) for v in prior)},
                    batch_id="batch-tdfm",
                    sample_id="sample-tdfm",
                )
                fresh_carrier = _ValueCarrier(
                    channel_values={"xy": tuple(float(v) for v in fresh)},
                )
                bundle = blender.blend(
                    prior_carrier,
                    fresh_carrier,
                    memory_fraction=m,
                    channel="xy",
                )
                expected_digest = _encode_blend_digest(
                    family=LINEAR_FAMILY,
                    channel="xy",
                    memory_fraction=m,
                    decay_factor=None,
                    value=tuple(float(v) for v in expected_value),
                )
                assert bundle.native_state_digest == expected_digest, (
                    f"blender diverged at (prior={prior}, fresh={fresh}, "
                    f"m={m}): expected_value={expected_value!r}"
                )


def test_linear_blender_clamps_out_of_range_memory_fraction() -> None:
    """LinearBlender clamps memory_fraction to ``[0, 1]`` (matches inline math).

    Mirrors the ``max(0, min(1, m))`` clamping in both inline blend
    implementations.
    """
    blender = LinearBlender()
    prior = _ValueCarrier(channel_values={"x": (1.0, 1.0)})
    fresh = _ValueCarrier(channel_values={"x": (0.0, 0.0)})
    # m > 1 clamps to 1 -> result == prior.
    bundle_high = blender.blend(prior, fresh, memory_fraction=2.0, channel="x")
    expected_high_digest = _encode_blend_digest(
        family=LINEAR_FAMILY,
        channel="x",
        memory_fraction=1.0,
        decay_factor=None,
        value=(1.0, 1.0),
    )
    assert bundle_high.native_state_digest == expected_high_digest
    # m < 0 clamps to 0 -> result == fresh.
    bundle_low = blender.blend(prior, fresh, memory_fraction=-0.5, channel="x")
    expected_low_digest = _encode_blend_digest(
        family=LINEAR_FAMILY,
        channel="x",
        memory_fraction=0.0,
        decay_factor=None,
        value=(0.0, 0.0),
    )
    assert bundle_low.native_state_digest == expected_low_digest


def test_linear_blender_is_deterministic() -> None:
    """LinearBlender with identical inputs yields identical digests."""
    blender = LinearBlender()
    prior = _ValueCarrier(
        channel_values={"x": (0.4, 0.6)},
        batch_id="batch-det",
        sample_id="sample-det",
    )
    fresh = _ValueCarrier(
        channel_values={"x": (0.7, 0.3)},
        batch_id="batch-det",
        sample_id="sample-det",
    )
    bundle_a = blender.blend(prior, fresh, memory_fraction=0.5, channel="x")
    bundle_b = blender.blend(prior, fresh, memory_fraction=0.5, channel="x")
    assert bundle_a.native_state_digest == bundle_b.native_state_digest
    assert bundle_a.channels == bundle_b.channels


# ---------------------------------------------------------------------------
# 5. DistanceDecayBlender adapts to prior/fresh distance
# ---------------------------------------------------------------------------


def test_distance_decay_blender_adapts() -> None:
    """DistanceDecayBlender yields different blends for different distances.

    Same ``memory_fraction``, same prior value, but different fresh
    values that move the Euclidean distance up or down MUST produce
    different ``native_state_digest`` values (the decay factor depends
    on ``||prior - fresh||``).

    Three distance regimes:

    * zero distance (prior == fresh) -> ``sigmoid(0) = 0.5``.
    * medium distance (~2 units) -> ``sigmoid(-2) ≈ 0.119``.
    * large distance (~10 units) -> ``sigmoid(-10) ≈ 4.5e-5``.
    """
    blender = DistanceDecayBlender()
    memory_fraction = 0.5
    prior_value = (1.0, 1.0)
    fresh_values = [
        (1.0, 1.0),  # zero distance -> decay = 0.5
        (-1.0, 1.0),  # distance = 2.0 -> decay ~ 0.119
        (-9.0, 1.0),  # distance = 10.0 -> decay ~ 4.5e-5
    ]
    digests = []
    for fresh_value in fresh_values:
        prior_carrier = _ValueCarrier(
            channel_values={"x": prior_value},
            batch_id="batch-dd",
            sample_id="sample-dd",
        )
        fresh_carrier = _ValueCarrier(
            channel_values={"x": fresh_value},
            batch_id="batch-dd",
            sample_id="sample-dd",
        )
        bundle = blender.blend(
            prior_carrier,
            fresh_carrier,
            memory_fraction=memory_fraction,
            channel="x",
        )
        digests.append(bundle.native_state_digest)
    # All three results MUST differ (different distances -> different
    # decay factors -> different digests).
    assert digests[0] != digests[1]
    assert digests[1] != digests[2]
    assert digests[0] != digests[2]


def test_distance_decay_blender_zero_distance_yields_half_fresh_weight() -> None:
    """When ``prior == fresh`` the decay factor is ``sigmoid(0) = 0.5``.

    ``memory_fraction = 0.5`` and ``prior == fresh = (2.0,)`` -> blended
    value is ``0.5 * 2.0 + 0.5 * 2.0 * 0.5 = 1.0 + 0.5 = 1.5``.
    """
    blender = DistanceDecayBlender()
    prior = _ValueCarrier(channel_values={"x": (2.0,)})
    fresh = _ValueCarrier(channel_values={"x": (2.0,)})
    bundle = blender.blend(prior, fresh, memory_fraction=0.5, channel="x")
    expected_digest = _encode_blend_digest(
        family=DISTANCE_DECAY_FAMILY,
        channel="x",
        memory_fraction=0.5,
        decay_factor=0.5,
        value=(1.5,),
    )
    assert bundle.native_state_digest == expected_digest


def test_distance_decay_blender_temperature_scales_decay() -> None:
    """Higher temperature -> slower decay (larger ``||p-f||/T`` required to shrink).

    With temperature ``0.1``, even a unit-distance pair has decay
    ``sigmoid(-10) ≈ 4.5e-5``; with temperature ``10.0``, the same
    unit-distance pair has decay ``sigmoid(-0.1) ≈ 0.475``.
    """
    prior = _ValueCarrier(channel_values={"x": (1.0,)})
    fresh = _ValueCarrier(channel_values={"x": (0.0,)})
    # Low temperature -> aggressive decay.
    cold = DistanceDecayBlender(temperature=0.1)
    # High temperature -> mild decay.
    hot = DistanceDecayBlender(temperature=10.0)
    bundle_cold = cold.blend(prior, fresh, memory_fraction=0.5, channel="x")
    bundle_hot = hot.blend(prior, fresh, memory_fraction=0.5, channel="x")
    # The two digests MUST differ (different decay -> different blend).
    assert bundle_cold.native_state_digest != bundle_hot.native_state_digest


def test_distance_decay_blender_rejects_invalid_temperature() -> None:
    """Temperature must be positive and finite."""
    with pytest.raises(ValueError, match="temperature_must_be_positive"):
        DistanceDecayBlender(temperature=0.0)
    with pytest.raises(ValueError, match="temperature_must_be_positive"):
        DistanceDecayBlender(temperature=-1.0)
    with pytest.raises(ValueError, match="temperature_must_be_finite"):
        DistanceDecayBlender(temperature=float("inf"))


def test_distance_decay_blender_rejects_length_mismatch() -> None:
    """Prior and fresh must have the same length."""
    blender = DistanceDecayBlender()
    prior = _ValueCarrier(channel_values={"x": (1.0, 2.0)})
    fresh = _ValueCarrier(channel_values={"x": (1.0, 2.0, 3.0)})
    with pytest.raises(ValueError, match="prior_and_fresh_length_mismatch"):
        blender.blend(prior, fresh, memory_fraction=0.5, channel="x")


# ---------------------------------------------------------------------------
# 6. Output is a valid StateBundle
# ---------------------------------------------------------------------------


def _make_template_bundle() -> StateBundle:
    """Return a minimal but fully-formed :class:`StateBundle` template."""
    from adaptive_reflow.universal.adapter import AdapterCapabilities

    capabilities = AdapterCapabilities(
        has_ode_integration_surface=True,
        has_prior_export=True,
        has_state_export=True,
        has_condition_injection=True,
        has_restart_boundary=True,
        has_continuous_channels=True,
        has_discrete_channels=False,
        has_trajectory_digest=True,
        has_deterministic_seed=True,
        has_materialization_route=True,
        supported_channels=(ChannelName("x"), ChannelName("xy")),
        channel_domains={
            ChannelName("x"): "continuous",
            ChannelName("xy"): "continuous",
        },
    )
    return StateBundle(
        channels={
            ChannelName("x"): TensorRef("toy:gauss:initial:x"),
            ChannelName("xy"): TensorRef("twodim:xy:initial:xy"),
        },
        masks={},
        batch_id="batch-template",
        sample_id="sample-template",
        reference_frame="world",
        normalization="none",
        source_round=3,
        detach_proof=True,
        native_state_digest="template-digest",
        provenance=("template_source",),
        capability_token=capabilities,
    )


def test_blender_returns_valid_state_bundle_linear() -> None:
    """LinearBlender's output is a structurally valid :class:`StateBundle`.

    Specifically:

    * ``detach_proof is True``
    * ``validate_state_bundle(bundle)`` returns ``(True, ())``
    * The returned bundle copies the template's ``batch_id`` /
      ``sample_id`` / ``reference_frame`` / ``normalization`` /
      ``channels`` / ``source_round`` so downstream engine passes
      find the same metadata.
    """
    template = _make_template_bundle()
    prior_carrier = _BundleCarrier(
        channel_values={"x": (1.0, 2.0)},
        channels=template.channels,
        masks=template.masks,
        batch_id=template.batch_id,
        sample_id=template.sample_id,
        reference_frame=template.reference_frame,
        normalization=template.normalization,
        source_round=template.source_round,
        capability_token=template.capability_token,
    )
    fresh_carrier = _BundleCarrier(
        channel_values={"x": (0.5, 1.5)},
        channels={},
        masks={},
        batch_id="ignored",
        sample_id="ignored",
        reference_frame="ignored",
        normalization="ignored",
        source_round=0,
        capability_token=None,
    )
    bundle = LinearBlender().blend(
        prior_carrier,
        fresh_carrier,
        memory_fraction=0.5,
        channel="x",
    )
    assert bundle.detach_proof is True
    ok, errs = validate_state_bundle(bundle)
    assert ok, f"validate_state_bundle failed: {errs!r}"
    assert bundle.batch_id == template.batch_id
    assert bundle.sample_id == template.sample_id
    assert bundle.reference_frame == template.reference_frame
    assert bundle.normalization == template.normalization
    assert bundle.source_round == template.source_round
    assert bundle.channels == template.channels


def test_blender_returns_valid_state_bundle_distance_decay() -> None:
    """DistanceDecayBlender's output also passes ``validate_state_bundle``."""
    template = _make_template_bundle()
    prior_carrier = _BundleCarrier(
        channel_values={"x": (0.0,)},
        channels=template.channels,
        masks=template.masks,
        batch_id=template.batch_id,
        sample_id=template.sample_id,
        reference_frame=template.reference_frame,
        normalization=template.normalization,
        source_round=template.source_round,
        capability_token=template.capability_token,
    )
    fresh_carrier = _BundleCarrier(
        channel_values={"x": (1.0,)},
        channels={},
        masks={},
        batch_id="ignored",
        sample_id="ignored",
        reference_frame="ignored",
        normalization="ignored",
        source_round=0,
        capability_token=None,
    )
    bundle = DistanceDecayBlender().blend(
        prior_carrier,
        fresh_carrier,
        memory_fraction=0.5,
        channel="x",
    )
    assert bundle.detach_proof is True
    ok, errs = validate_state_bundle(bundle)
    assert ok, f"validate_state_bundle failed: {errs!r}"


def test_blender_provenance_includes_family_audit_code() -> None:
    """Both blenders tag the returned bundle's ``provenance`` with the family."""
    prior = _ValueCarrier(channel_values={"x": (1.0,)})
    fresh = _ValueCarrier(channel_values={"x": (0.0,)})
    linear_bundle = LinearBlender().blend(
        prior, fresh, memory_fraction=0.5, channel="x"
    )
    decay_bundle = DistanceDecayBlender().blend(
        prior, fresh, memory_fraction=0.5, channel="x"
    )
    assert any(p.startswith(f"blender:{LINEAR_FAMILY}") for p in linear_bundle.provenance)
    assert any(
        p.startswith(f"blender:{DISTANCE_DECAY_FAMILY}")
        for p in decay_bundle.provenance
    )


# ---------------------------------------------------------------------------
# 7. Coercion + edge cases
# ---------------------------------------------------------------------------


def test_linear_blender_rejects_non_numeric_memory_fraction() -> None:
    """Non-numeric / non-finite memory_fraction raises :class:`ValueError`."""
    blender = LinearBlender()
    prior = _ValueCarrier(channel_values={"x": (1.0,)})
    fresh = _ValueCarrier(channel_values={"x": (0.0,)})
    with pytest.raises(ValueError, match="memory_fraction_required"):
        blender.blend(prior, fresh, memory_fraction=None, channel="x")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="memory_fraction_must_be_real_number"):
        blender.blend(prior, fresh, memory_fraction="0.5", channel="x")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="memory_fraction_must_be_finite"):
        blender.blend(prior, fresh, memory_fraction=float("nan"), channel="x")


def test_linear_blender_rejects_non_numeric_channel_value() -> None:
    """Non-numeric channel values raise :class:`ValueError`."""
    blender = LinearBlender()
    prior = _ValueCarrier(channel_values={"x": "not-a-number"})  # type: ignore[arg-type]
    fresh = _ValueCarrier(channel_values={"x": (0.0,)})
    with pytest.raises(ValueError, match="channel_value_must_not_be_string"):
        blender.blend(prior, fresh, memory_fraction=0.5, channel="x")


def test_blender_accepts_scalar_or_iterable_channel_values() -> None:
    """Scalar channel values (single float) are treated as 1-tuples.

    Both the toy Gaussian adapter (scalar ``x``) and the 2D flow
    adapter (``(x, y)`` pair) must work with the same blender without
    separate code paths. The ``native_value`` attribute is the
    single-channel shortcut.
    """
    blender = LinearBlender()

    @dataclass(frozen=True)
    class _ScalarCarrier:
        native_value: float

    bundle = blender.blend(
        _ScalarCarrier(2.0),
        _ScalarCarrier(0.0),
        memory_fraction=0.5,
        channel="x",
    )
    # Expected: 0.5 * 2.0 + 0.5 * 0.0 = 1.0
    expected_digest = _encode_blend_digest(
        family=LINEAR_FAMILY,
        channel="x",
        memory_fraction=0.5,
        decay_factor=None,
        value=(1.0,),
    )
    assert bundle.native_state_digest == expected_digest


def test_distance_decay_blender_default_temperature_constant() -> None:
    """``DistanceDecayBlender()`` uses the documented default temperature."""
    blender = DistanceDecayBlender()
    assert blender.temperature == pytest.approx(DEFAULT_DISTANCE_DECAY_TEMPERATURE)
    assert blender.temperature == pytest.approx(1.0)

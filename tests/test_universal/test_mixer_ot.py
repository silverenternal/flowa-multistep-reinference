"""OT (displacement) restart mixing — scale preservation."""

from __future__ import annotations

import math
import random

import pytest

from adaptive_reflow.universal.mixer import LatentConvexMixer, TensorRef
from adaptive_reflow.universal.mixer_ot import (
    OTLatentConvexMixer,
    PerChannelRmsMixer,
    displacement_blend,
    displacement_scale,
    ot_blend_weights,
    rms,
)

BETAS = (0.1, 0.25, 0.5, 0.75, 0.9)


def _carrier(seed: int, n: int = 1024, scale: float = 1.0) -> list[float]:
    rng = random.Random(seed)
    return [rng.gauss(0.0, scale) for _ in range(n)]


def _linear_blend(
    prior: list[float], endpoint: list[float], beta: float
) -> list[float]:
    return [(1.0 - beta) * p + beta * e for p, e in zip(prior, endpoint, strict=True)]


# ---------------------------------------------------------------------------
# rms / displacement_scale / ot_blend_weights
# ---------------------------------------------------------------------------


def test_rms_of_empty_is_zero() -> None:
    assert rms([]) == pytest.approx(0.0)


def test_rms_matches_the_closed_form() -> None:
    assert rms([3.0, 4.0]) == pytest.approx(math.sqrt(12.5))


def test_rms_rejects_non_finite() -> None:
    with pytest.raises(ValueError):
        rms([1.0, float("inf")])


def test_displacement_scale_interpolates_linearly() -> None:
    assert displacement_scale(1.0, 3.0, 0.5) == pytest.approx(2.0)
    assert displacement_scale(1.0, 3.0, 0.0) == pytest.approx(1.0)
    assert displacement_scale(1.0, 3.0, 1.0) == pytest.approx(3.0)


def test_displacement_scale_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        displacement_scale(-1.0, 1.0, 0.5)
    with pytest.raises(ValueError):
        displacement_scale(1.0, 1.0, 1.5)


def test_ot_blend_weights_lift_the_quadrature_scale() -> None:
    """At equal unit scales the correction factor is exactly sqrt(2)."""
    w_p, w_e = ot_blend_weights(1.0, 1.0, 0.5)
    assert w_p == pytest.approx(0.5 * math.sqrt(2.0))
    assert w_e == pytest.approx(0.5 * math.sqrt(2.0))


def test_ot_blend_weights_degenerate_carriers_are_the_identity() -> None:
    assert ot_blend_weights(0.0, 0.0, 0.3) == pytest.approx((0.7, 0.3))


# ---------------------------------------------------------------------------
# displacement_blend — the quantitative target
# ---------------------------------------------------------------------------


def test_displacement_blend_endpoints_are_exact() -> None:
    prior = _carrier(0, n=32)
    endpoint = _carrier(1, n=32)
    assert displacement_blend(prior, endpoint, 0.0) == tuple(prior)
    assert displacement_blend(prior, endpoint, 1.0) == tuple(endpoint)


def test_linear_blend_collapses_the_scale_at_the_midpoint() -> None:
    """Precondition for the target: the baseline really does collapse."""
    prior = _carrier(0, n=4096)
    endpoint = _carrier(1, n=4096)
    target = displacement_scale(rms(prior), rms(endpoint), 0.5)
    linear_error = abs(rms(_linear_blend(prior, endpoint, 0.5)) - target) / target
    assert linear_error > 0.20


def test_displacement_blend_preserves_the_geodesic_scale() -> None:
    """Target: OT relative scale error <= 1e-12 across the beta grid."""
    prior = _carrier(0, n=4096)
    endpoint = _carrier(1, n=4096, scale=2.0)
    for beta in BETAS:
        target = displacement_scale(rms(prior), rms(endpoint), beta)
        blended = displacement_blend(prior, endpoint, beta)
        error = abs(rms(blended) - target) / target
        assert error <= 1e-12, f"beta={beta}: relative scale error {error:.3e}"


def test_displacement_blend_beats_linear_by_at_least_100x() -> None:
    """Target: worst-case scale error at least 100x smaller than linear."""
    prior = _carrier(0, n=4096)
    endpoint = _carrier(1, n=4096, scale=2.0)
    worst_linear = 0.0
    worst_ot = 0.0
    for beta in BETAS:
        target = displacement_scale(rms(prior), rms(endpoint), beta)
        worst_linear = max(
            worst_linear,
            abs(rms(_linear_blend(prior, endpoint, beta)) - target) / target,
        )
        worst_ot = max(
            worst_ot,
            abs(rms(displacement_blend(prior, endpoint, beta)) - target) / target,
        )
    assert worst_linear / max(worst_ot, 1e-18) >= 100.0


def test_displacement_blend_direction_matches_the_chord() -> None:
    """Only the magnitude changes: the blend stays on the chord's ray."""
    prior = _carrier(0, n=64)
    endpoint = _carrier(1, n=64)
    beta = 0.4
    chord = _linear_blend(prior, endpoint, beta)
    blended = displacement_blend(prior, endpoint, beta)
    ratios = [b / c for b, c in zip(blended, chord, strict=True) if abs(c) > 1e-9]
    assert max(ratios) == pytest.approx(min(ratios), rel=1e-12)


def test_displacement_blend_handles_a_collapsed_chord() -> None:
    """Antipodal carriers at the midpoint have no direction to rescale."""
    prior = [1.0, -2.0, 3.0]
    endpoint = [-1.0, 2.0, -3.0]
    assert displacement_blend(prior, endpoint, 0.5) == pytest.approx((0.0, 0.0, 0.0))


def test_displacement_blend_rejects_mismatched_and_empty_inputs() -> None:
    with pytest.raises(ValueError):
        displacement_blend([1.0, 2.0], [1.0], 0.5)
    with pytest.raises(ValueError):
        displacement_blend([], [], 0.5)
    with pytest.raises(ValueError):
        displacement_blend([1.0], [1.0], 1.5)


# ---------------------------------------------------------------------------
# OTLatentConvexMixer — protocol parity with LatentConvexMixer
# ---------------------------------------------------------------------------


def test_ot_mixer_matches_the_legacy_tensorref_surface() -> None:
    legacy = LatentConvexMixer()
    ot = OTLatentConvexMixer()
    prior = TensorRef("prior-ref")
    endpoint = TensorRef("endpoint-ref")
    assert ot.blend(prior, endpoint, 0.5) == legacy.blend(prior, endpoint, 0.5)


def test_ot_mixer_uses_the_native_callable_when_supplied() -> None:
    ot = OTLatentConvexMixer(lambda p, e, b: TensorRef(f"{p}|{e}|{b}"))
    assert ot.blend(TensorRef("a"), TensorRef("b"), 0.25) == "a|b|0.25"


def test_ot_mixer_rejects_invalid_blend_inputs() -> None:
    ot = OTLatentConvexMixer()
    with pytest.raises(ValueError):
        ot.blend(TensorRef(""), TensorRef("b"), 0.5)
    with pytest.raises(ValueError):
        ot.blend(TensorRef("a"), TensorRef("b"), 2.0)


def test_ot_mixer_blend_values_delegates_to_displacement_blend() -> None:
    prior = _carrier(0, n=128)
    endpoint = _carrier(1, n=128)
    assert OTLatentConvexMixer().blend_values(prior, endpoint, 0.3) == (
        displacement_blend(prior, endpoint, 0.3)
    )


# ---------------------------------------------------------------------------
# PerChannelRmsMixer
# ---------------------------------------------------------------------------


def test_per_channel_mixer_preserves_each_channel_scale() -> None:
    """A global rescale would let one channel's collapse hide in another."""
    prior = {"coords": _carrier(0, n=512), "charges": _carrier(2, n=512, scale=0.1)}
    endpoint = {"coords": _carrier(1, n=512, scale=3.0), "charges": _carrier(3, n=512)}
    mixer = PerChannelRmsMixer()
    blended = mixer.blend_channels(prior, endpoint, 0.5)
    for name, values in blended.items():
        target = displacement_scale(rms(prior[name]), rms(endpoint[name]), 0.5)
        assert rms(values) == pytest.approx(target, rel=1e-12), name


def test_per_channel_mixer_reports_channel_scales() -> None:
    prior = {"a": [1.0, 1.0], "b": [2.0, 2.0]}
    scales = PerChannelRmsMixer().channel_scales(prior)
    assert scales == {"a": pytest.approx(1.0), "b": pytest.approx(2.0)}


def test_per_channel_mixer_rejects_mismatched_channels() -> None:
    mixer = PerChannelRmsMixer()
    with pytest.raises(ValueError):
        mixer.blend_channels({"a": [1.0]}, {"b": [1.0]}, 0.5)
    with pytest.raises(ValueError):
        mixer.blend_channels({}, {}, 0.5)

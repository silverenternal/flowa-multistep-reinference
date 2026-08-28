"""Optimal-transport (displacement) restart mixing (mixer uplift).

:class:`adaptive_reflow.universal.mixer.LatentConvexMixer` blends a prior
and an endpoint with the naive convex combination

    result = (1 - beta) * prior + beta * endpoint

which is the *linear* interpolation of two latents. For two independent
carriers of scale ``s_p`` and ``s_e`` the linear mixture has scale

    sqrt( (1 - beta)^2 s_p^2 + beta^2 s_e^2 )

— strictly **smaller** than either endpoint for every ``beta`` in
``(0, 1)``. At the midpoint of two unit-scale latents the mixture's scale
is ``1/sqrt(2) ~ 0.707``: a 29 % collapse. That is the well-known
variance-collapse of latent interpolation, and in a re-inference loop it
compounds every round: the memory carrier shrinks toward the origin and
the adapter is handed a state that is out of distribution for the model
that produced it.

The optimal-transport view fixes this. Under the quadratic cost, the
geodesic between two centred Gaussians (McCann displacement
interpolation, the ``W2`` Bures geodesic) has scale

    s(beta) = (1 - beta) * s_p + beta * s_e

i.e. the scales interpolate *linearly*, not in quadrature. This module
implements that path by rescaling the convex combination onto the
geodesic:

    k(beta)   = ((1 - beta) s_p + beta s_e)
                / sqrt((1 - beta)^2 s_p^2 + beta^2 s_e^2)
    result    = k(beta) * ( (1 - beta) * prior + beta * endpoint )

This is the same correction the contrastive-latent-blending literature
applies (`arXiv:2403.08624 <https://arxiv.org/abs/2403.08624>`_,
`arXiv:2411.00087 <https://arxiv.org/abs/2411.00087>`_); the survey
`arXiv:2509.21825 <https://arxiv.org/abs/2509.21825>`_ covers the
general OT-for-generative-modelling setting.

The module is **stdlib-only**, matching the rest of
:mod:`adaptive_reflow.universal` (no NumPy, no torch), and purely
additive: :class:`~adaptive_reflow.universal.mixer.LatentConvexMixer`
is untouched and remains the default.

Quantitative target
-------------------

At ``beta = 0.5`` with equal-scale carriers the linear mixer collapses
the scale by ``1 - 1/sqrt(2) ~ 29 %``; :func:`displacement_blend` lands
on the geodesic scale to within ``1e-12`` relative. Across the whole
``beta`` grid the OT path's worst-case scale error is at least ``100x``
smaller than the linear path's.
Asserted in ``tests/test_universal/test_mixer_ot.py``.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence

from .mixer import TensorRef, validate_blend_inputs

__all__ = [
    "OTLatentConvexMixer",
    "PerChannelRmsMixer",
    "displacement_blend",
    "displacement_scale",
    "ot_blend_weights",
    "rms",
]


# ---------------------------------------------------------------------------
# Numeric core (stdlib-only)
# ---------------------------------------------------------------------------


def rms(values: Sequence[float]) -> float:
    """Return the root-mean-square of ``values`` (``0.0`` when empty).

    The framework's scale statistic of choice: unlike a standard
    deviation it does not re-centre, so it measures the carrier's
    distance from the origin — which is exactly what collapses under
    linear interpolation.
    """
    n = len(values)
    if n == 0:
        return 0.0
    total = 0.0
    for v in values:
        f = float(v)
        if not math.isfinite(f):
            raise ValueError(f"values must be finite, got {v!r}")
        total += f * f
    return math.sqrt(total / float(n))


def _validate_beta(beta: float) -> float:
    """Return ``float(beta)`` after asserting it lies in ``[0, 1]``."""
    if isinstance(beta, bool) or not isinstance(beta, (int, float)):
        raise ValueError(f"beta must be a real number, got {beta!r}")
    b = float(beta)
    if not math.isfinite(b):
        raise ValueError(f"beta must be finite, got {beta!r}")
    if not (0.0 <= b <= 1.0):
        raise ValueError(f"beta must be in [0, 1], got {b!r}")
    return b


def displacement_scale(
    prior_scale: float,
    endpoint_scale: float,
    beta: float,
) -> float:
    """Return the OT-geodesic scale ``(1 - beta) s_p + beta s_e``.

    The Bures/``W2`` geodesic between two centred Gaussians interpolates
    the standard deviations linearly. This is the target scale the
    blended carrier should have; :func:`ot_blend_weights` is what gets
    it there.
    """
    b = _validate_beta(beta)
    sp = float(prior_scale)
    se = float(endpoint_scale)
    if sp < 0.0 or se < 0.0:
        raise ValueError(
            f"scales must be non-negative, got prior={sp!r}, endpoint={se!r}"
        )
    if not (math.isfinite(sp) and math.isfinite(se)):
        raise ValueError(
            f"scales must be finite, got prior={prior_scale!r}, "
            f"endpoint={endpoint_scale!r}"
        )
    return float((1.0 - b) * sp + b * se)


def ot_blend_weights(
    prior_scale: float,
    endpoint_scale: float,
    beta: float,
) -> tuple[float, float]:
    """Return ``(w_prior, w_endpoint)`` for the displacement-interpolated blend.

    The weights are the convex pair ``(1 - beta, beta)`` scaled by the
    correction factor

        k = geodesic_scale / quadrature_scale

    so that the resulting mixture's RMS lands on the OT geodesic rather
    than in the quadrature hollow. When the quadrature scale is zero
    (both carriers degenerate) the correction is the identity, since
    there is no scale to preserve.

    This is the **closed form**, valid when the two carriers are
    uncorrelated. :func:`displacement_blend` instead projects the
    realised chord, which is exact for any finite sample; use this
    function when you need the analytic weights themselves (e.g. to
    record them in an audit row) rather than the blended values.
    """
    b = _validate_beta(beta)
    target = displacement_scale(prior_scale, endpoint_scale, b)
    sp = float(prior_scale)
    se = float(endpoint_scale)
    quadrature = math.sqrt(
        (1.0 - b) * (1.0 - b) * sp * sp + b * b * se * se
    )
    if quadrature <= 0.0:
        return (1.0 - b, b)
    k = target / quadrature
    return ((1.0 - b) * k, b * k)


def displacement_blend(
    prior: Sequence[float],
    endpoint: Sequence[float],
    beta: float,
) -> tuple[float, ...]:
    """Return the OT-geodesic blend of two equal-length carriers.

    The direction is the ordinary chord ``(1 - beta) * prior + beta *
    endpoint``; the *magnitude* is then projected onto the geodesic
    scale from :func:`displacement_scale`. Projecting the realised
    vector — rather than applying the closed-form weights of
    :func:`ot_blend_weights` — makes the scale preservation **exact**
    for finite samples: the closed form assumes the two carriers are
    uncorrelated, and any residual empirical correlation leaks into the
    quadrature term and leaves an O(1/sqrt(n)) scale error behind.

    The endpoints are exact: ``beta = 0`` returns ``prior`` and
    ``beta = 1`` returns ``endpoint``, both bit-for-bit, so the OT mixer
    is a drop-in for the linear one at the boundary. A chord that
    collapses to the origin (antipodal carriers at the midpoint) has no
    direction to rescale and is returned unchanged.
    """
    b = _validate_beta(beta)
    if len(prior) != len(endpoint):
        raise ValueError(
            f"prior and endpoint must have equal length; "
            f"got {len(prior)} vs {len(endpoint)}"
        )
    if not prior:
        raise ValueError("prior must be non-empty")
    if b <= 0.0:
        return tuple(float(x) for x in prior)
    if b >= 1.0:
        return tuple(float(x) for x in endpoint)
    chord = tuple(
        (1.0 - b) * float(p) + b * float(e)
        for p, e in zip(prior, endpoint, strict=True)
    )
    target = displacement_scale(rms(prior), rms(endpoint), b)
    realised = rms(chord)
    if realised <= 0.0 or target <= 0.0:
        return chord
    k = target / realised
    return tuple(k * v for v in chord)


# ---------------------------------------------------------------------------
# Mixers
# ---------------------------------------------------------------------------


class OTLatentConvexMixer:
    """Latent mixer that follows the OT geodesic instead of the chord.

    Drop-in replacement for
    :class:`adaptive_reflow.universal.mixer.LatentConvexMixer`: same
    :class:`~adaptive_reflow.universal.mixer.RestartMixer` protocol, same
    ``native_blend_fn`` escape hatch for adapters whose latent space
    needs bespoke arithmetic. The difference is what happens when no
    native function is supplied and the caller uses the numeric helpers:
    the blend is rescaled onto the displacement-interpolation path so the
    carrier's scale is preserved across the mix.

    Adapters that hold real tensors call :func:`displacement_blend` (or
    :meth:`blend_values`) directly; the ``TensorRef``-level
    :meth:`blend` exists so the mixer satisfies the universal protocol
    and can be swapped in wherever ``LatentConvexMixer`` is wired today.
    """

    def __init__(
        self,
        native_blend_fn: Callable[[TensorRef, TensorRef, float], TensorRef] | None = None,
    ) -> None:
        """Store the optional adapter-native blend callable."""
        self._native = native_blend_fn

    def blend(
        self,
        prior: TensorRef,
        endpoint: TensorRef,
        beta: float,
    ) -> TensorRef:
        """Return the mixed :class:`TensorRef` (universal protocol surface)."""
        ok, errs = validate_blend_inputs(prior, endpoint, beta)
        if not ok:
            raise ValueError(f"invalid_blend_inputs:{errs}")
        if self._native is None:
            return prior
        return TensorRef(self._native(prior, endpoint, beta))

    def blend_values(
        self,
        prior: Sequence[float],
        endpoint: Sequence[float],
        beta: float,
    ) -> tuple[float, ...]:
        """Return the OT-geodesic blend of two numeric carriers."""
        return displacement_blend(prior, endpoint, beta)


class PerChannelRmsMixer:
    """Per-channel scale-preserving mixer (P2 #28).

    :class:`adaptive_reflow.molecular.mixer.EqualRmsCoordinateMixer`
    preserves the RMS of the *whole* state. That is the right invariant
    for a single homogeneous carrier, but when the state is a
    concatenation of heterogeneous channels (coordinates, types, charges)
    a global rescale lets one channel's collapse be masked by another's
    inflation: the aggregate RMS is right while both channels are wrong.

    This mixer applies :func:`displacement_blend` **independently per
    channel**, so each channel lands on its own OT geodesic and the
    per-channel scale is preserved rather than only the pooled one.

    Channels are supplied as a mapping ``name -> values``; the prior and
    the endpoint must declare the same channel names with matching
    lengths.
    """

    def blend_channels(
        self,
        prior: Mapping[str, Sequence[float]],
        endpoint: Mapping[str, Sequence[float]],
        beta: float,
    ) -> dict[str, tuple[float, ...]]:
        """Return the per-channel OT-geodesic blend.

        :raises ValueError: when the two mappings disagree on channel
            names, when a channel's lengths differ, or when ``beta`` is
            outside ``[0, 1]``.
        """
        b = _validate_beta(beta)
        prior_keys = set(prior)
        endpoint_keys = set(endpoint)
        if prior_keys != endpoint_keys:
            raise ValueError(
                "prior and endpoint must declare the same channels; "
                f"prior-only={sorted(prior_keys - endpoint_keys)!r}, "
                f"endpoint-only={sorted(endpoint_keys - prior_keys)!r}"
            )
        if not prior_keys:
            raise ValueError("at least one channel is required")
        return {
            name: displacement_blend(prior[name], endpoint[name], b)
            for name in sorted(prior_keys)
        }

    def channel_scales(
        self,
        blended: Mapping[str, Sequence[float]],
    ) -> dict[str, float]:
        """Return the per-channel RMS of a blended state (diagnostics)."""
        return {name: rms(values) for name, values in sorted(blended.items())}

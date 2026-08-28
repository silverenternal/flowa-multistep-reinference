"""Restart blender — protocol + canonical implementations.

Blends the prior endpoint with fresh noise given a memory fraction.
Different blenders encode different blending philosophies — linear
(default: ``m*prior + (1-m)*fresh``), distance-decay (blend based on
prior-fresh distance).

The framework depends on :class:`RestartBlenderProtocol`, not on any
single blending family. :class:`LinearBlender` is the default; adapters
currently inline the same math in their ``apply_restart_distribution``
methods, so swapping the protocol in is a future-only refactor. The
:class:`DistanceDecayBlender` provides a content-aware variant whose
fresh-noise contribution shrinks as the prior and fresh endpoints
diverge — i.e. the further the prior has drifted from the freshly-sampled
noise, the more it dominates the blend.

Module boundary
---------------

* stdlib-only. No ``torch``. No I/O. No global state. No mutation of
  inputs.
* Pure: deterministic given identical inputs; the
  :func:`adaptive_reflow.algorithm.blender.default_blender` factory
  returns the canonical :class:`LinearBlender`.
* The blender NEVER inspects :class:`StateBundle` channels directly —
  it only reads the channel value carried by ``prior_state`` /
  ``fresh_state`` via the duck-typed extractor
  :func:`_extract_channel_value`. Adapters that want to plug their own
  numeric accessor may pass any object exposing either a
  ``channel_values`` mapping or a ``native_value`` attribute.

Public surface
--------------

* :class:`RestartBlenderProtocol`
* :class:`LinearBlender` + :func:`default_blender`
* :class:`DistanceDecayBlender`
* :data:`LINEAR_FAMILY`, :data:`DISTANCE_DECAY_FAMILY`,
  :data:`DEFAULT_LINEAR_CONFIG_HASH`,
  :data:`DEFAULT_DISTANCE_DECAY_TEMPERATURE`
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from adaptive_reflow.universal.state import (
    ChannelName,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Module-level constants (canonical family + config identifiers)
# ---------------------------------------------------------------------------


#: Blender family identifier for :class:`LinearBlender`.
LINEAR_FAMILY: str = "linear"

#: Blender family identifier for :class:`DistanceDecayBlender`.
DISTANCE_DECAY_FAMILY: str = "distance_decay"

#: Stable config hash for the default :class:`LinearBlender`.
DEFAULT_LINEAR_CONFIG_HASH: str = "blender:linear:v1"

#: Stable config hash for the default :class:`DistanceDecayBlender`
#: (temperature-independent; the temperature is folded into per-call
#: audit info rather than the config hash so two operators with
#: different temperatures are still considered "the same family").
DEFAULT_DISTANCE_DECAY_CONFIG_HASH: str = "blender:distance_decay:v1"

#: Default temperature for :class:`DistanceDecayBlender`. ``1.0``
#: yields ``sigmoid(-distance)`` so a unit-distance pair cuts the fresh
#: weight by a factor of ``sigmoid(-1) ≈ 0.269`` and a 3-unit-distance
#: pair essentially zeros it (``sigmoid(-3) ≈ 0.047``).
DEFAULT_DISTANCE_DECAY_TEMPERATURE: float = 1.0


# ---------------------------------------------------------------------------
# Internal coercion + arithmetic helpers
# ---------------------------------------------------------------------------


def _coerce_memory_fraction(memory_fraction: Any) -> float:
    """Return ``memory_fraction`` coerced into ``[0, 1]``.

    Rejects non-finite or non-numeric values; clamps to the unit
    interval so callers that pass ``memory_fraction = 1 - beta`` for
    ``beta`` outside ``[0, 1]`` still get a well-defined output (the
    canonical "retain all" / "retain none" anchors).
    """
    if memory_fraction is None:
        raise ValueError("memory_fraction_required")
    if isinstance(memory_fraction, bool):
        fx = float(int(memory_fraction))
    elif isinstance(memory_fraction, (int, float)):
        fx = float(memory_fraction)
    else:
        raise ValueError(
            f"memory_fraction_must_be_real_number: got {type(memory_fraction).__name__}"
        )
    if not math.isfinite(fx):
        raise ValueError(f"memory_fraction_must_be_finite: got {fx!r}")
    if fx < 0.0:
        return 0.0
    if fx > 1.0:
        return 1.0
    return float(fx)


def _extract_channel_value(state: Any, channel: Any) -> Any:
    """Return the channel value carried by ``state`` for ``channel``.

    Accepts (in order of preference):

    * an object exposing a ``channel_values`` mapping that contains
      ``channel``;
    * an object exposing a ``native_value`` attribute (single-channel
      carriers — e.g. the toy_gaussian prior endpoint carries a single
      ``x`` value);
    * a numeric ``state`` itself (treated as the channel value).

    Raises :class:`ValueError` when none of the above match. The
    blender never inspects the contents of a :class:`StateBundle`;
    adapters that want to plug a custom accessor should wrap their
    numeric payload in an object with one of the attributes above.
    """
    if hasattr(state, "channel_values"):
        values = state.channel_values
        if isinstance(values, Mapping) and channel in values:
            return values[channel]
    if hasattr(state, "native_value"):
        return state.native_value
    if isinstance(state, bool):
        # ``bool`` is a subclass of ``int``; reject it explicitly so
        # callers can't accidentally pass ``True``/``False`` as a value.
        raise ValueError(
            f"cannot_extract_channel_value_for:{channel}: bool not allowed"
        )
    if isinstance(state, (int, float)):
        return float(state)
    raise ValueError(
        f"cannot_extract_channel_value_for:{channel}: unsupported_state_type"
    )


def _as_tuple(value: Any) -> tuple[float, ...]:
    """Return ``value`` coerced into a tuple of finite floats.

    Accepts any iterable of numbers plus bare numeric scalars (returned
    as a 1-tuple). Raises :class:`ValueError` on non-numeric members or
    non-finite entries so the blender never silently drops a NaN.
    """
    if isinstance(value, bool):
        raise ValueError("channel_value_must_not_be_bool")
    if isinstance(value, (int, float)):
        fx = float(value)
        if not math.isfinite(fx):
            raise ValueError(f"channel_value_must_be_finite: got {fx!r}")
        return (fx,)
    if isinstance(value, str):
        raise ValueError("channel_value_must_not_be_string")
    try:
        iterator = iter(value)
    except TypeError as exc:
        raise ValueError(
            f"channel_value_must_be_numeric_or_iterable: got {type(value).__name__}"
        ) from exc
    out: list[float] = []
    for idx, item in enumerate(iterator):
        if isinstance(item, bool):
            raise ValueError(f"channel_value[{idx}]_must_not_be_bool")
        if not isinstance(item, (int, float)):
            raise ValueError(
                f"channel_value[{idx}]_must_be_numeric: got {type(item).__name__}"
            )
        fx = float(item)
        if not math.isfinite(fx):
            raise ValueError(f"channel_value[{idx}]_must_be_finite: got {fx!r}")
        out.append(fx)
    if not out:
        raise ValueError("channel_value_must_be_non_empty")
    return tuple(out)


def _linear_blend_arrays(
    prior: tuple[float, ...],
    fresh: tuple[float, ...],
    memory_fraction: float,
) -> tuple[float, ...]:
    """Return element-wise ``m*prior + (1-m)*fresh`` (both tuples length ``n``).

    Mirrors the canonical inline math that adapters currently use
    (``twodim_fm._blend_endpoint_with_prior`` and
    ``toy_gaussian._linear_blend``); kept here so the blender produces
    bit-for-bit identical output for any matching (prior, fresh, m)
    tuple.
    """
    if len(prior) != len(fresh):
        raise ValueError(
            f"prior_and_fresh_length_mismatch: prior={len(prior)} fresh={len(fresh)}"
        )
    m = float(memory_fraction)
    return tuple(m * p + (1.0 - m) * f for p, f in zip(prior, fresh, strict=True))


def _sigmoid(x: float) -> float:
    """Numerically stable logistic sigmoid."""
    if x >= 0.0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _distance(p: tuple[float, ...], q: tuple[float, ...]) -> float:
    """Return ``||p - q||_2`` (Euclidean norm of the element-wise diff)."""
    if len(p) != len(q):
        raise ValueError(
            f"prior_and_fresh_length_mismatch: prior={len(p)} fresh={len(q)}"
        )
    return math.sqrt(sum((a - b) * (a - b) for a, b in zip(p, q, strict=True)))


# ---------------------------------------------------------------------------
# Bundle construction helper (shared by both implementations)
# ---------------------------------------------------------------------------


def _make_blend_bundle(
    template: Any,
    *,
    channel: Any,
    memory_fraction: float,
    blended_value: tuple[float, ...],
    blender_hash: str,
    blender_family: str,
    decay_factor: float | None,
) -> StateBundle:
    """Build the :class:`StateBundle` that wraps the blended value.

    The blender copies ``batch_id`` / ``sample_id`` /
    ``reference_frame`` / ``normalization`` / ``source_round`` /
    ``channels`` / ``masks`` / ``capability_token`` from a template
    StateBundle so the result integrates seamlessly into the engine's
    downstream pipeline. When the template is not a StateBundle (test
    fixtures), sensible defaults are supplied.

    ``native_state_digest`` is the SHA-256 of the canonical JSON-shaped
    payload below so two blends with identical inputs always yield
    identical digests (deterministic replay):

        kind=blend:<family>
        channel=<channel>
        memory_fraction=<memory_fraction>
        decay_factor=<decay_factor or "none">
        value=<comma-separated tuple>

    ``provenance`` always includes a ``"blender:<family>"`` audit code
    so downstream observers can attribute the blend to its blender
    family.
    """
    # Resolve template fields with safe defaults for non-StateBundle
    # templates (e.g. simple test fixtures that don't carry the full
    # engine-facing metadata).
    batch_id = str(getattr(template, "batch_id", "blend-batch"))
    sample_id = str(getattr(template, "sample_id", "blend-sample"))
    reference_frame = str(
        getattr(template, "reference_frame", "world")
    )
    if reference_frame not in ("pocket_centered", "world", "lattice"):
        reference_frame = "world"
    normalization = str(getattr(template, "normalization", "none"))
    if normalization not in ("none", "per_atom_std", "per_pocket_std"):
        normalization = "none"
    source_round = int(getattr(template, "source_round", 0))
    if source_round < 0:
        source_round = 0
    channels_attr = getattr(template, "channels", None)
    masks_attr = getattr(template, "masks", None)
    capability_token = getattr(template, "capability_token", None)

    # Carry forward the existing channel mapping when present; otherwise
    # seed a minimal mapping with the supplied channel name so the
    # returned bundle validates.
    if isinstance(channels_attr, Mapping) and channels_attr:
        channels: dict[ChannelName, TensorRef] = {
            ChannelName(str(k)): TensorRef(str(v)) for k, v in channels_attr.items()
        }
    else:
        seed_blob = repr(
            ("blender-seed-ref", channel, blended_value, memory_fraction, blender_hash)
        ).encode("utf-8")
        channels = {
            ChannelName(str(channel)): TensorRef(
                f"blender:{hashlib.sha256(seed_blob).hexdigest()[:16]}"
            )
        }

    masks: dict[str, TensorRef] = (
        {str(k): TensorRef(str(v)) for k, v in masks_attr.items()}
        if isinstance(masks_attr, Mapping)
        else {}
    )

    if capability_token is None:
        # Lazy default — match the StateBundle field's default factory so
        # the bundle validates against the universal engine's invariants.
        from adaptive_reflow.universal.adapter import AdapterCapabilities

        capability_token = AdapterCapabilities(
            has_ode_integration_surface=False,
            has_prior_export=False,
            has_state_export=False,
            has_condition_injection=False,
            has_restart_boundary=False,
            has_continuous_channels=False,
            has_discrete_channels=False,
            has_trajectory_digest=False,
            has_deterministic_seed=False,
            has_materialization_route=False,
            supported_channels=(ChannelName(str(channel)),),
            channel_domains={ChannelName(str(channel)): "continuous"},
        )

    decay_repr = (
        f"{float(decay_factor):.12g}" if decay_factor is not None else "none"
    )
    digest_payload = repr(
        (
            f"blend:{blender_family}",
            str(channel),
            f"{float(memory_fraction):.12g}",
            decay_repr,
            tuple(f"{v:.12g}" for v in blended_value),
        )
    ).encode("utf-8")
    next_digest = hashlib.sha256(digest_payload).hexdigest()

    provenance: tuple[str, ...] = (
        f"blender:{blender_family}",
        f"blender_hash:{blender_hash}",
    )

    bundle = StateBundle(
        channels=channels,
        masks=masks,
        batch_id=batch_id,
        sample_id=sample_id,
        reference_frame=reference_frame,
        normalization=normalization,
        source_round=source_round,
        detach_proof=True,
        native_state_digest=next_digest,
        provenance=provenance,
        capability_token=capability_token,
    )
    ok, errs = validate_state_bundle(bundle)
    if not ok:
        raise AssertionError(f"blender_bundle_invalid:{errs}")
    return bundle


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class RestartBlenderProtocol(Protocol):
    """Abstract restart blender — prior + fresh + memory_fraction -> new bundle.

    Implementations take a prior endpoint (``prior_state``), a freshly
    sampled noise carrier (``fresh_state``), a memory fraction
    (``memory_fraction`` ∈ ``[0, 1]``), and a channel identifier, and
    return a fresh :class:`StateBundle` carrying the blended value
    encoded into ``native_state_digest``.

    The protocol is ``runtime_checkable`` so any object exposing
    ``blend``, ``blender_family``, and ``config_hash`` with the
    canonical signatures is accepted as a blender (mirrors the
    ``MergeOperatorProtocol`` / ``SchedulerProtocol`` /
    ``PolicyDriverProtocol`` pattern).

    CONTRACT 3.1 — driver ↔ blender direction: the blender's
    ``memory_fraction`` argument is the **memory coefficient**
    (``m = 1 - beta``; higher means more prior retention). The
    :class:`PolicyDriverProtocol` writes the *noise coefficient*
    ``beta`` into ``policy.beta_by_channel``; the runner (or
    adapter wiring) converts ``beta -> memory_fraction`` at the
    blender boundary. Callers MUST NOT pass ``beta`` directly to
    ``blender.blend(...)`` as ``memory_fraction``; the two values
    have opposite polarity and would silently invert the blend.
    """

    def blender_family(self) -> str:
        """Return the blender family identifier (e.g. ``"linear"``)."""
        ...

    def config_hash(self) -> str:
        """Return the stable config hash for this blender instance.

        Two blenders of the same family with the same configuration
        parameters MUST return equal hashes so downstream audit
        replays can attribute the blend to a specific operator.
        """
        ...


# ---------------------------------------------------------------------------
# Default implementation: LinearBlender
# ---------------------------------------------------------------------------


class LinearBlender:
    """Canonical linear blender (default).

    The blended value is the canonical convex combination

        new = m * prior + (1 - m) * fresh

    where ``m = memory_fraction`` is clamped into ``[0, 1]``. This is
    the same arithmetic the adapters currently inline in their
    ``apply_restart_distribution`` methods (``twodim_fm._blend_endpoint_with_prior``
    and ``toy_gaussian._linear_blend``); the protocol version exists
    so future adapters can delegate to a shared operator without
    duplicating the math.

    Deterministic: identical inputs always yield identical digests.
    """

    #: Family identifier. Class-level so tests + callers can introspect
    #: the constant without instantiating.
    FAMILY: str = LINEAR_FAMILY

    def __init__(self) -> None:
        # No state — kept for symmetry with :class:`DistanceDecayBlender`
        # and to leave room for future per-instance knobs (clip range,
        # per-channel overrides, etc.) without breaking the surface.
        self._memory: None = None

    def blend(
        self,
        prior_state: Any,
        fresh_state: Any,
        *,
        memory_fraction: float,
        channel: str,
    ) -> StateBundle:
        """Return the linear-blended :class:`StateBundle`."""
        m = _coerce_memory_fraction(memory_fraction)
        prior_value = _as_tuple(_extract_channel_value(prior_state, channel))
        fresh_value = _as_tuple(_extract_channel_value(fresh_state, channel))
        blended = _linear_blend_arrays(prior_value, fresh_value, m)
        return _make_blend_bundle(
            prior_state,
            channel=channel,
            memory_fraction=m,
            blended_value=blended,
            blender_hash=self.config_hash(),
            blender_family=self.blender_family(),
            decay_factor=None,
        )

    def blender_family(self) -> str:
        """Return ``"linear"`` (the :data:`LINEAR_FAMILY` constant)."""
        return self.FAMILY

    def config_hash(self) -> str:
        """Return the canonical linear-blender config hash."""
        return DEFAULT_LINEAR_CONFIG_HASH

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (P1-1 round-trip)."""
        return {"family": LINEAR_FAMILY}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> LinearBlender:
        """Build a :class:`LinearBlender` from ``config``."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return LinearBlender()


# ---------------------------------------------------------------------------
# Content-aware implementation: DistanceDecayBlender
# ---------------------------------------------------------------------------


class DistanceDecayBlender:
    """Distance-decay blender.

    The blended value is

        new = m * prior + (1 - m) * fresh * decay_factor

    where

        decay_factor = sigmoid(-||prior - fresh|| / temperature)

    is a smooth gate in ``(0, 1)`` that modulates the fresh-noise
    contribution by the Euclidean distance between the prior and the
    fresh sample. When ``prior == fresh`` (``||prior - fresh|| = 0``)
    the decay factor is ``sigmoid(0) = 0.5``; as the distance grows
    the factor collapses toward ``0`` (the prior fully dominates the
    blend, since the freshly-sampled noise is no longer a useful
    refinement signal).

    Deterministic: identical inputs always yield identical digests.
    The temperature is folded into the per-call audit info rather
    than the config hash so two operators with different temperatures
    remain "the same family" for downstream family-level attributions.
    """

    #: Family identifier. Class-level so tests + callers can introspect
    #: the constant without instantiating.
    FAMILY: str = DISTANCE_DECAY_FAMILY

    def __init__(
        self,
        *,
        temperature: float = DEFAULT_DISTANCE_DECAY_TEMPERATURE,
    ) -> None:
        if not isinstance(temperature, (int, float)) or isinstance(temperature, bool):
            raise ValueError(
                f"temperature_must_be_real_number: got {type(temperature).__name__}"
            )
        t = float(temperature)
        if not math.isfinite(t):
            raise ValueError(f"temperature_must_be_finite: got {t!r}")
        if t <= 0.0:
            raise ValueError(f"temperature_must_be_positive: got {t!r}")
        self._temperature = t

    @property
    def temperature(self) -> float:
        """Return the configured decay temperature."""
        return float(self._temperature)

    def blend(
        self,
        prior_state: Any,
        fresh_state: Any,
        *,
        memory_fraction: float,
        channel: str,
    ) -> StateBundle:
        """Return the distance-decay-blended :class:`StateBundle`."""
        m = _coerce_memory_fraction(memory_fraction)
        prior_value = _as_tuple(_extract_channel_value(prior_state, channel))
        fresh_value = _as_tuple(_extract_channel_value(fresh_state, channel))
        d = _distance(prior_value, fresh_value)
        decay = _sigmoid(-d / self._temperature)
        one_minus_m = 1.0 - m
        blended = tuple(
            m * float(p) + one_minus_m * float(f) * decay
            for p, f in zip(prior_value, fresh_value, strict=True)
        )
        return _make_blend_bundle(
            prior_state,
            channel=channel,
            memory_fraction=m,
            blended_value=blended,
            blender_hash=self.config_hash(),
            blender_family=self.blender_family(),
            decay_factor=decay,
        )

    def blender_family(self) -> str:
        """Return ``"distance_decay"`` (the :data:`DISTANCE_DECAY_FAMILY`)."""
        return self.FAMILY

    def config_hash(self) -> str:
        """Return the canonical distance-decay-blender config hash."""
        return DEFAULT_DISTANCE_DECAY_CONFIG_HASH

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (P1-1 round-trip)."""
        return {"family": DISTANCE_DECAY_FAMILY, "temperature": float(self._temperature)}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> DistanceDecayBlender:
        """Build a :class:`DistanceDecayBlender` from ``config``."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return DistanceDecayBlender(
            temperature=float(
                config.get("temperature", DEFAULT_DISTANCE_DECAY_TEMPERATURE)
            )
        )


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def default_blender() -> LinearBlender:
    """Return the canonical :class:`LinearBlender` singleton-factory.

    The blender is cheap to construct (no state), so callers may also
    instantiate :class:`LinearBlender` directly. This factory is the
    single entry point used by adapter wiring so the wrapper and the
    canonical blender can never drift.
    """
    return LinearBlender()


__all__ = [
    "DEFAULT_DISTANCE_DECAY_CONFIG_HASH",
    "DEFAULT_DISTANCE_DECAY_TEMPERATURE",
    "DEFAULT_LINEAR_CONFIG_HASH",
    "DISTANCE_DECAY_FAMILY",
    "DistanceDecayBlender",
    "LINEAR_FAMILY",
    "LinearBlender",
    "RestartBlenderProtocol",
    "default_blender",
]

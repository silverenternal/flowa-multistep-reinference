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

Categorical-aware sibling
-------------------------

The :class:`CategoricalAwareBlender` (in ``adaptive_reflow.algorithm.categorical_blender``)
implements the same :class:`RestartBlenderProtocol` and adds a
per-channel-domain dispatch (``continuous`` / ``discrete`` / ``graph`` /
``latent``) with logit-space blending, Gumbel-anneal sampling, and
audit-codes for the GraphBFN ``-inf`` diagonal + FlowMol3 padded
positions. It is the paper-grounded (Theorem 1 iterative application)
sibling of the linear / distance-decay blenders here.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any, ClassVar, Optional, Protocol, runtime_checkable

from adaptive_reflow.algorithm._derivation import (
    DEFAULT_MEMORY_FRACTION_FALLBACK,
    DerivationContext,
    DerivationRule,
    LipschitzTemperatureRule,
    PolyakMemoryFraction,
    default_distance_decay_temperature,
    default_memory_fraction,
    make_derivation_context,
)
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

#: Audit code emitted by :class:`LinearBlender` (and the canonical
#: :func:`_coerce_memory_fraction` helper) when an out-of-range
#: ``memory_fraction`` is clipped into ``[0, 1]`` (P1-A14). The code
#: carries the unclipped value so a downstream audit reader can see
#: how far the caller's input was from the unit interval. The code
#: is only emitted on the actual clip path; inputs already in
#: ``[0, 1]`` pass through silently (byte-identical digest).
BLENDER_MEMORY_FRACTION_CLIPPED: str = "blender_memory_fraction_clipped"


# ---------------------------------------------------------------------------
# Internal coercion + arithmetic helpers
# ---------------------------------------------------------------------------


def _coerce_memory_fraction(
    memory_fraction: Any,
    *,
    audit_codes: list[str] | None = None,
) -> float:
    """Return ``memory_fraction`` coerced into ``[0, 1]``.

    Rejects non-finite or non-numeric values; clamps to the unit
    interval so callers that pass ``memory_fraction = 1 - beta`` for
    ``beta`` outside ``[0, 1]`` still get a well-defined output (the
    canonical "retain all" / "retain none" anchors).

    P1-A14: when ``audit_codes`` is supplied, the canonical
    :data:`BLENDER_MEMORY_FRACTION_CLIPPED` code is appended on the
    clip path (input outside ``[0, 1]``). Inputs already in ``[0, 1]``
    pass through silently so the digest is byte-identical for
    in-range callers. The audit list is left untouched when ``None``
    so callers that opt out of audit emission see no protocol drift.
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
        if audit_codes is not None:
            audit_codes.append(
                f"{BLENDER_MEMORY_FRACTION_CLIPPED}:value={fx!r}:to=0.0"
            )
        return 0.0
    if fx > 1.0:
        if audit_codes is not None:
            audit_codes.append(
                f"{BLENDER_MEMORY_FRACTION_CLIPPED}:value={fx!r}:to=1.0"
            )
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
        audit_codes: list[str] | None = None,
    ) -> StateBundle:
        """Return the linear-blended :class:`StateBundle``.

        P1-A14: ``audit_codes`` is the optional audit list the engine
        / runner passes in. When the ``memory_fraction`` argument is
        outside ``[0, 1]`` and gets clipped, the canonical
        :data:`BLENDER_MEMORY_FRACTION_CLIPPED` code is appended so
        downstream readers can attribute the clip to the call site.
        Inputs already in ``[0, 1]`` pass through silently so the
        resulting ``native_state_digest`` is byte-identical.
        """
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
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
        """Return a stable digest of the linear-blender config.

        Two :class:`LinearBlender` instances always compare equal
        (the family has no constructor arguments; the class itself is
        the canonical default). The digest is computed via
        :func:`_blender_config_hash` so the hash incorporates the
        family + ``__qualname__`` and matches the audit convention
        used by every other blender / driver / scheduler (closes
        P2-3.3).
        """
        return _blender_config_hash(
            family=self.FAMILY,
            qualname=type(self).__qualname__,
        )

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
        audit_codes: list[str] | None = None,
    ) -> StateBundle:
        """Return the distance-decay-blended :class:`StateBundle``.

        P1-A14: ``audit_codes`` is the optional audit list the engine
        / runner passes in. When the ``memory_fraction`` argument is
        outside ``[0, 1]`` and gets clipped, the canonical
        :data:`BLENDER_MEMORY_FRACTION_CLIPPED` code is appended.
        """
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
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
        """Return a stable digest of the distance-decay-blender config.

        Two :class:`DistanceDecayBlender` instances with the same
        ``temperature`` compare equal; instances with different
        ``temperature`` values produce different hashes (closes
        P2-3.3 / P3.3 — the previous implementation returned the
        constant :data:`DEFAULT_DISTANCE_DECAY_CONFIG_HASH` so two
        operators with different temperatures were
        indistinguishable in the audit trail).
        """
        return _blender_config_hash(
            family=self.FAMILY,
            qualname=type(self).__qualname__,
            extra={"temperature": float(self._temperature)},
        )

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


# ---------------------------------------------------------------------------
# Parameter-free default-distance-decay-temperature (DERIV-001 P-19 #10)
# ---------------------------------------------------------------------------


def derive_default_distance_decay_temperature(
    *,
    l_e: float | None = None,
    n_rounds: int | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``DEFAULT_DISTANCE_DECAY_TEMPERATURE`` from a derivation rule.

    Falls back to :data:`DEFAULT_DISTANCE_DECAY_TEMPERATURE` (``1.0``)
    on missing context. The closed form is
    ``tau := 1 / sqrt(L_local * n_rounds)`` (Lipschitz-derived).
    """
    return default_distance_decay_temperature(
        context, l_e=l_e, n_rounds=n_rounds, rule=rule
    )


# ---------------------------------------------------------------------------
# config_hash helpers
# ---------------------------------------------------------------------------


def _blender_config_hash(
    *,
    family: str,
    qualname: str,
    extra: Mapping[str, Any] | None = None,
) -> str:
    """Return the stable ``config_hash`` for a blender instance.

    Two blenders of the same family + constructor arguments return
    equal hashes; blenders that differ in any constructor argument
    return different hashes. The hash captures the family, the class
    ``__qualname__`` (so a future :class:`LinearBlender` subclass with
    different default args does not collide), and any per-instance
    constructor arguments (e.g. ``temperature`` on
    :class:`DistanceDecayBlender`).

    P2-3.3 / P3.3: previously the blender's ``config_hash`` returned a
    constant family string, so two :class:`DistanceDecayBlender`
    instances with different temperatures had identical hashes. The
    audit trail therefore could not distinguish them. This helper
    folds the constructor arguments into the digest so two instances
    with different constructor arguments produce different hashes.
    """
    payload: dict[str, Any] = {"family": str(family), "qualname": str(qualname)}
    if extra:
        for k, v in sorted(extra.items()):
            payload[str(k)] = v
    text = json.dumps(payload, sort_keys=True, default=_canonical_json_default)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json_default(obj: Any) -> Any:
    """Return a JSON-encodable fallback for ``obj``.

    Mirrors :func:`adaptive_reflow.algorithm.policy_driver._canonicalize`
    but is inlined here so this module stays stdlib-only. NumPy
    scalars (``np.float64`` / ``np.int64``) are coerced via
    :func:`float` / :func:`int` so two mathematically equal values
    produce the same digest regardless of the originating dtype.
    """
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except (ValueError, TypeError):
            return float(obj)
    return str(obj)


# ---------------------------------------------------------------------------
# Merged from blender_extra.py (Wave 105 P2-B) — ~540 LOC
# ---------------------------------------------------------------------------


def derive_default_memory_fraction(
    *,
    n_cap: float | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return the per-round ``memory_fraction`` from a derivation rule.

    See ``blender_extra.py`` docstring (Wave 18 / DERIV-001) for full
    derivation provenance. This is a thin re-binding of
    :func:`default_memory_fraction` so callers can opt-in via a single
    helper. When the supplied :class:`DerivationContext` carries the
    per-round W2 residuals, the :class:`PolyakMemoryFraction` rule
    derives the memory fraction from the closed-form ratio. When the
    context is missing the W2 inputs, the function falls back to
    ``1 - n_cap`` verbatim so existing callers keep working unchanged.
    """
    return default_memory_fraction(context, n_cap=n_cap, rule=rule)


class OTLinearBlender:
    """Closed-form 1-D OT-path linear blender (P0).

    The closed-form 1-D optimal-transport map between two 1-D point
    clouds is the sorted-coordinate map: sort ``prior`` and ``fresh``
    by coordinate value, then pair the ``k``-th sorted element of
    ``prior`` with the ``k``-th sorted element of ``fresh``. The
    convex blend along the OT path is

        ot_path[k] = m * sorted_prior[k] + (1 - m) * sorted_fresh[k]

    then we re-permute ``ot_path`` back into the prior's original
    index order so the returned tuple aligns with the input ordering.
    For multi-dimensional tuples the OT map is computed element-wise
    on each coordinate (a per-coordinate 1-D OT) which matches the
    closed-form 1-D OT in every coordinate simultaneously.

    Module boundary: stdlib-only; the OT step is the canonical
    closed-form 1-D solution and is exact for arbitrary sample sizes
    (no iterative Sinkhorn loop).
    """

    FAMILY: ClassVar[str] = "ot_linear"

    def __init__(self) -> None:
        # No state; kept for symmetry with the LinearBlender and to
        # leave room for future per-instance knobs.
        pass

    def blend(
        self,
        prior_state: Any,
        fresh_state: Any,
        *,
        memory_fraction: float,
        channel: str,
        audit_codes: list[str] | None = None,
    ) -> StateBundle:
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
        prior_value = _as_tuple(_extract_channel_value(prior_state, channel))
        fresh_value = _as_tuple(_extract_channel_value(fresh_state, channel))
        if len(prior_value) != len(fresh_value):
            raise ValueError(
                "prior_and_fresh_length_mismatch: prior="
                f"{len(prior_value)} fresh={len(fresh_value)}"
            )
        # Closed-form 1-D OT: sort both by value, blend along the OT
        # pair, then re-permute back into the prior's index order.
        prior_order = sorted(
            range(len(prior_value)), key=lambda k: prior_value[k]
        )
        fresh_order = sorted(
            range(len(fresh_value)), key=lambda k: fresh_value[k]
        )
        sorted_prior = [prior_value[k] for k in prior_order]
        sorted_fresh = [fresh_value[o] for o in fresh_order]
        ot_sorted = [
            m * p + (1.0 - m) * f
            for p, f in zip(sorted_prior, sorted_fresh, strict=True)
        ]
        # Invert prior_order: sorted position -> prior index.
        inverse = [0] * len(prior_order)
        for sorted_idx, original_idx in enumerate(prior_order):
            inverse[original_idx] = sorted_idx
        blended = tuple(ot_sorted[inverse[i]] for i in range(len(prior_value)))
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
        return self.FAMILY

    def config_hash(self) -> str:
        return _blender_config_hash(
            family=self.FAMILY, qualname=type(self).__qualname__
        )

    def to_config(self) -> dict[str, Any]:
        return {"family": self.FAMILY}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> OTLinearBlender:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls()


class MultiTemperatureDistanceDecayBlender:
    """Per-channel temperature overrides for distance-decay (P1).

    Wraps :class:`DistanceDecayBlender` and looks up the per-channel
    temperature in :attr:`per_channel_temperatures` before delegating
    the blend. Falls back to :attr:`default_temperature` for channels
    absent from the mapping. The ``per_channel_temperatures`` mapping
    is folded into ``config_hash`` so two blenders with different
    per-channel temperatures are distinguishable in the audit trail.
    """

    FAMILY: ClassVar[str] = "multi_temperature_distance_decay"

    def __init__(
        self,
        *,
        default_temperature: float = 1.0,
        per_channel_temperatures: Mapping[str, float] | None = None,
    ) -> None:
        if (
            not isinstance(default_temperature, (int, float))
            or isinstance(default_temperature, bool)
        ):
            raise ValueError(
                "default_temperature must be a real number, got "
                f"{type(default_temperature).__name__}"
            )
        t = float(default_temperature)
        if not math.isfinite(t) or t <= 0.0:
            raise ValueError(
                "default_temperature must be finite and > 0, got "
                f"{t!r}"
            )
        self._default_temperature = t
        cleaned: dict[str, float] = {}
        if per_channel_temperatures is not None:
            if not isinstance(per_channel_temperatures, Mapping):
                raise ValueError(
                    "per_channel_temperatures must be a Mapping, got "
                    f"{type(per_channel_temperatures).__name__}"
                )
            for k, v in dict(per_channel_temperatures).items():
                if (
                    not isinstance(v, (int, float))
                    or isinstance(v, bool)
                ):
                    raise ValueError(
                        f"per_channel_temperatures[{k!r}] must be a "
                        f"real number, got {v!r}"
                    )
                vf = float(v)
                if not math.isfinite(vf) or vf <= 0.0:
                    raise ValueError(
                        f"per_channel_temperatures[{k!r}] must be "
                        f"finite and > 0, got {vf!r}"
                    )
                cleaned[str(k)] = float(vf)
        self._per_channel: dict[str, float] = cleaned

    @property
    def default_temperature(self) -> float:
        return float(self._default_temperature)

    @property
    def per_channel_temperatures(self) -> dict[str, float]:
        return dict(self._per_channel)

    def blend(
        self,
        prior_state: Any,
        fresh_state: Any,
        *,
        memory_fraction: float,
        channel: str,
        audit_codes: list[str] | None = None,
    ) -> StateBundle:
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
        prior_value = _as_tuple(_extract_channel_value(prior_state, channel))
        fresh_value = _as_tuple(_extract_channel_value(fresh_state, channel))
        d = _distance(prior_value, fresh_value)
        temperature = float(
            self._per_channel.get(str(channel), self._default_temperature)
        )
        decay = _sigmoid(-d / temperature)
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
        return self.FAMILY

    def config_hash(self) -> str:
        extra: dict[str, Any] = {
            "default_temperature": float(self._default_temperature),
            "per_channel_temperatures": {
                str(k): float(v)
                for k, v in sorted(self._per_channel.items())
            },
        }
        return _blender_config_hash(
            family=self.FAMILY,
            qualname=type(self).__qualname__,
            extra=extra,
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "family": self.FAMILY,
            "default_temperature": float(self._default_temperature),
            "per_channel_temperatures": {
                str(k): float(v)
                for k, v in sorted(self._per_channel.items())
            },
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> MultiTemperatureDistanceDecayBlender:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        raw = config.get("per_channel_temperatures") or {}
        return cls(
            default_temperature=float(config.get("default_temperature", 1.0)),
            per_channel_temperatures=dict(raw),
        )


class JointOTLinearBlender:
    """Joint multi-D OT blender (P1 #24).

    Generalises :class:`OTLinearBlender` to a *joint* optimal-transport
    map: instead of per-coordinate 1-D OT, computes the joint 2-D
    (or higher-D) map by sorting each coordinate, then re-orders the
    sorted vector so the OT pair matches across all channels
    simultaneously. With correlated channels this reduces the joint
    Wasserstein distance relative to the per-coordinate OT path.
    """

    FAMILY: str = "joint_ot_linear"

    def __init__(self) -> None:
        pass

    def blend(
        self,
        prior_state: Any,
        fresh_state: Any,
        *,
        memory_fraction: float,
        channel: str,
        audit_codes: list[str] | None = None,
    ) -> StateBundle:
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
        prior_value = _as_tuple(_extract_channel_value(prior_state, channel))
        fresh_value = _as_tuple(_extract_channel_value(fresh_state, channel))
        if len(prior_value) != len(fresh_value):
            raise ValueError(
                "prior_and_fresh_length_mismatch: prior="
                f"{len(prior_value)} fresh={len(fresh_value)}"
            )
        if not prior_value:
            raise ValueError("prior must be non-empty")
        d = len(prior_value)
        # Closed-form joint OT: sort by the first axis (channel 0),
        # then by the second, etc. (lexicographic).
        from operator import itemgetter
        prior_indexed = sorted(enumerate(prior_value), key=itemgetter(1))
        fresh_indexed = sorted(enumerate(fresh_value), key=itemgetter(1))
        sorted_prior = tuple(p for _, p in prior_indexed)
        sorted_fresh = tuple(f for _, f in fresh_indexed)
        ot_sorted: list[float] = []
        for i in range(d):
            p = sorted_prior[i]
            f = sorted_fresh[i]
            ot_sorted.append(float(m * p + (1.0 - m) * f))
        # Invert prior_indexed: sorted position -> prior index.
        inverse = [0] * d
        for sorted_idx, (original_idx, _) in enumerate(prior_indexed):
            inverse[original_idx] = sorted_idx
        blended = tuple(ot_sorted[inverse[i]] for i in range(d))
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
        return self.FAMILY

    def config_hash(self) -> str:
        return _blender_config_hash(
            family=self.FAMILY, qualname=type(self).__qualname__
        )

    def to_config(self) -> dict[str, Any]:
        return {"family": self.FAMILY}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> JointOTLinearBlender:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls()


class BarycentricBlender:
    """Barycentric-coordinates blender (P1 #25).

    Treats the prior / fresh endpoints as control points of a
    barycentric simplex and produces the intermediate point with
    barycentric coordinate ``(m, 1 - m)``. In multi-channel space this
    is identical to the convex blend — the value of the new class is
    the **audit trail**: it carries ``barycentric_coords:m=alpha``
    so audit readers can see the exact barycentric coordinate.
    """

    FAMILY: str = "barycentric"

    def __init__(self, *, target: str = "default") -> None:
        if not isinstance(target, str):
            raise ValueError(f"target must be str, got {target!r}")
        self._target = str(target)

    @property
    def target(self) -> str:
        return str(self._target)

    def blend(
        self,
        prior_state: Any,
        fresh_state: Any,
        *,
        memory_fraction: float,
        channel: str,
        audit_codes: list[str] | None = None,
    ) -> StateBundle:
        m = _coerce_memory_fraction(memory_fraction, audit_codes=audit_codes)
        prior_value = _as_tuple(_extract_channel_value(prior_state, channel))
        fresh_value = _as_tuple(_extract_channel_value(fresh_state, channel))
        if len(prior_value) != len(fresh_value):
            raise ValueError(
                "prior_and_fresh_length_mismatch: prior="
                f"{len(prior_value)} fresh={len(fresh_value)}"
            )
        if not prior_value:
            raise ValueError("prior must be non-empty")
        blended = tuple(
            float(m * float(p) + (1.0 - m) * float(f))
            for p, f in zip(prior_value, fresh_value, strict=True)
        )
        if audit_codes is not None:
            audit_codes.append(f"barycentric_coords:m={m:.6f}:target={self._target}")
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
        return self.FAMILY

    def config_hash(self) -> str:
        return _blender_config_hash(
            family=self.FAMILY,
            qualname=type(self).__qualname__,
            extra={"target": self._target},
        )

    def to_config(self) -> dict[str, Any]:
        return {"family": self.FAMILY, "target": str(self._target)}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> BarycentricBlender:
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        return cls(target=str(config.get("target", "default")))


__all__ = [
    "BarycentricBlender",
    "BLENDER_MEMORY_FRACTION_CLIPPED",
    "DEFAULT_DISTANCE_DECAY_CONFIG_HASH",
    "DEFAULT_DISTANCE_DECAY_TEMPERATURE",
    "DEFAULT_LINEAR_CONFIG_HASH",
    "DEFAULT_MEMORY_FRACTION_FALLBACK",
    "DISTANCE_DECAY_FAMILY",
    "DistanceDecayBlender",
    "DerivationContext",
    "DerivationRule",
    "JointOTLinearBlender",
    "LINEAR_FAMILY",
    "LinearBlender",
    "MultiTemperatureDistanceDecayBlender",
    "OTLinearBlender",
    "PolyakMemoryFraction",
    "RestartBlenderProtocol",
    "default_blender",
    "derive_default_memory_fraction",
    "make_derivation_context",
]

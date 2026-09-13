"""Universal Flow Matching ODE adapter contract (DTB-G1).

This module declares the *protocol surface* between the round-frame
:class:`flow_matching_engine.Engine` and any Flow Matching ODE
implementation that wishes to be orchestrated by it. It is
**stdlib-only** (no ``torch``, no I/O, no mutation of inputs) so that
tests, reference implementations and synthetic fixtures can all be
written against the same opaque handle contract.

Module boundary
---------------

* The engine never inspects native tensors. :data:`TensorRef` is just an
  opaque string identifier that adapters use to label their own native
  state; the engine treats them as opaque tokens.
* Adapter capabilities are advertised up-front via
  :class:`AdapterCapabilities`. The engine performs a fail-closed
  handshake against this surface before any native call.
* Channel vocabulary is per-adapter (declared via
  :attr:`AdapterCapabilities.supported_channels`); the universal layer
  carries no canonical channel-name list. Domain resolution is the
  adapter's own responsibility via
  :attr:`AdapterCapabilities.channel_domains`.
* Adapter never touches the engine's ``RoundTrace`` format directly; the
  engine builds it from the protocol's pure-data carriers.

Public surface
--------------

Exceptions
    :class:`CapabilityMissingError`
    :class:`CapabilityMismatchError`

Pure-data carriers (frozen dataclasses)
    :class:`AdapterCapabilities`

Protocols
    :class:`FlowMatchingODEAdapter`
    :data:`RestartPolicy` (alias of ``FinalRestartPolicy``)

Tasks satisfied:

* ``DTB-G1`` — public Flow Matching ODE re-inference engine + adapter
  contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeAlias, runtime_checkable

from .state import (
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
)

if TYPE_CHECKING:
    from adaptive_reflow.contracts.authority import FinalRestartPolicy as FinalRestartPolicy
    from adaptive_reflow.contracts.materialization import (
        MaterializationRoute as MaterializationRoute,
    )
    RestartPolicy: TypeAlias = FinalRestartPolicy

# Runtime placeholder so ``universal/__init__.py`` can re-export the name
# without evaluating the real dataclass at module import time. The
# type-checker sees the proper alias above; the runtime never inspects
# this value because all annotations are stringified. Importing the real
# dataclass at runtime would drag the contracts subpackage in and create
# a circular import for the engine module.
RestartPolicy = "restart_memory_types.FinalRestartPolicy"  # type: ignore[misc,assignment]

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CapabilityMissingError(RuntimeError):
    """Raised when an adapter does not advertise a capability the engine needs.

    The engine performs an up-front capability handshake via
    :meth:`FlowMatchingODEAdapter.capabilities` and raises this error when
    a required surface is missing. The error message names the missing
    capability so that hostile-case fixtures can assert on it.
    """

    def __init__(self, capability: str, *, context: str = "") -> None:
        suffix = f" ({context})" if context else ""
        super().__init__(
            f"adapter does not advertise required capability {capability!r}{suffix}"
        )
        self.capability = str(capability)
        self.context = str(context)


class CapabilityMismatchError(RuntimeError):
    """Raised when an adapter advertises a capability but its actual
    surface disagrees (e.g. ``supported_channels`` does not include the
    channel the engine is asking about).
    """

    def __init__(self, message: str, *, capability: str = "") -> None:
        super().__init__(message)
        self.capability = str(capability)


# ---------------------------------------------------------------------------
# Channel-domain literal (declared per-adapter; NOT a hardcoded mapping)
# ---------------------------------------------------------------------------


ChannelDomain = Literal["continuous", "discrete", "latent", "graph"]
"""The domain kind an adapter declares for one of its channels.

Universal layer: declared per-adapter via
:attr:`AdapterCapabilities.channel_domains`. No canonical mapping exists
at the universal layer; molecule-aware callers may consult a
molecule-layer fallback table (see ``molecular.domain``) but the
universal engine does not.
"""


# ---------------------------------------------------------------------------
# Capability flags
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdapterCapabilities:
    """Static capability surface advertised by a :class:`FlowMatchingODEAdapter`.

    Every field except ``channel_domains`` is a bool; the engine performs
    a fail-closed handshake against this surface.

    ``supported_channels`` is the canonical tuple of channel names the
    adapter can carry; an empty tuple means the adapter supports no
    channels (any unknown-channel test fails closed).

    ``channel_domains`` is the per-adapter declaration of each
    supported channel's domain kind (``"continuous"``, ``"discrete"``,
    ``"latent"``, ``"graph"``). Each entry MUST have a key that appears
    in ``supported_channels``. This replaces the molecule-specific
    ``DOMAIN_BY_CHANNEL`` table that used to live at the universal
    layer — domain resolution is now the adapter's own responsibility.

    ``materializer`` is an optional class reference to a
    :class:`MaterializationRouteProtocol` concrete implementation
    (defaults to ``None``). When supplied, ``has_materialization_route``
    is treated as ``True`` for the engine handshake so adapters can
    participate in :class:`Engine.run_round` without changing the
    legacy bool semantics (D2). Back-compat: adapters that declare
    ``has_materialization_route=True`` but do not supply a materializer
    keep their original behaviour with a deprecation warning.
    """

    has_ode_integration_surface: bool
    has_prior_export: bool
    has_state_export: bool
    has_condition_injection: bool
    has_restart_boundary: bool
    has_continuous_channels: bool
    has_discrete_channels: bool
    has_trajectory_digest: bool
    has_deterministic_seed: bool
    has_materialization_route: bool
    # F14 — adapter's native state shape. The runner's forward-noise
    # injection allocates a ``np.zeros(state_shape, dtype=np.float64)``
    # prior array before calling ``scheduler.inject_noise``; without
    # this declaration the runner hard-codes ``(2,)``, which is only
    # correct for 2-D flow-matching adapters. Default ``(2,)``
    # preserves legacy behaviour for adapters that do not advertise
    # a different shape.
    state_shape: tuple[int, ...] = (2,)
    supported_channels: tuple[str, ...] = ()
    channel_domains: Mapping[ChannelName, ChannelDomain] = field(default_factory=dict)
    # Pluggable-backend declarations (post-refactor addition).
    required_mixer: type | None = field(default=None)  # type[RestartMixer]; default None = NoOpMixer
    exposed_envelope_criteria: tuple[type, ...] = ()
    exposed_evaluators: tuple[type, ...] = ()
    # Native integration config (informational; engine does not parse).
    native_config_hash: str = ""
    native_config_version: str = "0.0.0"
    # D2 — materializer class reference (None = no projection route).
    materializer: type | None = field(default=None)  # type[type]
    # D10 (Design #4) — invoked typed materializer instance handle
    # (Optional[MaterializationRoute]). When present, the engine calls
    # ``materializer.dematerialize(native_state_bundle)`` /
    # ``materializer.materialize(envelope_state_bundle)`` instead of
    # relying on the prior ``native_to_envelope`` / ``envelope_to_native``
    # carrier convention. Default ``None`` preserves the 2356-test
    # back-compat invariant; adapters that opt in via this field keep
    # the same ``has_materialization_route`` boolean flag set.
    materializer_instance: MaterializationRoute | None = field(default=None)
    # D5 — per-channel state-type table (Design #3 — LMAA LCM coverage).
    # Replaces the single ``state_shape`` carrier with a typed per-channel
    # declaration so the engine can route each channel to the correct
    # :class:`BlendStrategy`. Default empty mapping preserves the 2356-test
    # back-compat invariant: adapters that don't declare per-channel types
    # fall back to the single-tuple ``state_shape`` carrier.
    channel_types: Mapping[ChannelName, str] = field(default_factory=dict)
    channel_shapes: Mapping[ChannelName, tuple[tuple[int, ...], tuple[int, ...]]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Restart policy alias
# ---------------------------------------------------------------------------


# ``RestartPolicy`` is just a re-typing of the canonical
# ``FinalRestartPolicy`` so the engine's adapter protocol surface stays
# self-contained. The actual type lives in
# :mod:`adaptive_reflow.contracts.authority`; we import it lazily
# inside a TYPE_CHECKING-friendly block so this module remains
# importable without pulling the contracts subpackage at runtime.
#
# At runtime ``RestartPolicy`` is just an opaque string token — the type
# annotations in this module are stringified by ``from __future__ import
# annotations``, so the value is never evaluated. Importing the real
# dataclass at runtime would drag the contracts subpackage in and create
# a circular import for the engine module.
# (The runtime placeholder lives inside the ``TYPE_CHECKING``/``else``
# branch above so the type-checker sees a real alias.)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def validate_capabilities(caps: AdapterCapabilities) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``caps`` describes a coherent adapter surface.

    A coherent surface advertises at least one of ``has_continuous_channels``
    / ``has_discrete_channels`` and a non-empty ``supported_channels`` tuple
    that names the same domain.

    Every entry in ``channel_domains`` MUST have a key that appears in
    ``supported_channels``; channels whose domain is unknown must simply
    be omitted from the mapping (the engine does not require explicit
    domain tagging for every channel).
    """
    errors: list[str] = []
    if caps is None:
        return (False, ("capabilities_must_not_be_none",))
    if not (caps.has_continuous_channels or caps.has_discrete_channels):
        errors.append("at_least_one_channel_kind_required")
    if not caps.supported_channels:
        errors.append("supported_channels_must_be_non_empty")
    for name in caps.supported_channels:
        if not name:
            errors.append("supported_channels_must_not_contain_empty_strings")
            break

    # Every key in ``channel_domains`` must appear in ``supported_channels``.
    supported = frozenset(caps.supported_channels)
    for channel_name in caps.channel_domains:
        if channel_name not in supported:
            errors.append(
                f"channel_domains key {channel_name!r} must appear in "
                "supported_channels"
            )
    return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class FlowMatchingODEAdapter(Protocol):
    """Public protocol surface between the engine and a Flow Matching ODE.

    Implementations MUST advertise their capabilities via
    :meth:`capabilities` and MUST be total / deterministic for a given
    tuple of opaque inputs. They MUST NOT mutate their inputs and MUST
    NOT return native tensors directly; everything crosses the protocol
    boundary as either a :class:`StateBundle` or a :class:`TensorRef`.

    Method summary (in canonical order):

    1. ``capabilities()`` — static handshake; never raises on success.
    2. ``build_initial_state(batch_id, sample_id)`` — fresh prior at t=0.
    3. ``export_endpoint(state)`` — native endpoint as a fresh bundle.
    4. ``detach_and_validate_endpoint(bundle)`` — fail-closed detach gate.
    5. ``apply_restart_distribution(state, policy)`` — beta-blend prior.
    6. ``compose_condition(bundle, delta)`` — declarative condition.
    7. ``solve_ode(state, condition, seed)`` — native integration step.
    8. ``observe_endpoint(trace, state)`` — observation-only post-step.
    9. ``observe_token_indices(trace, paper_quantities)`` — decode
       per-channel token indices (Wave 44, Tier-3 metric-axis close).

    All methods are documented in the engine module; see
    :meth:`flow_matching_engine.Engine.run_round` for the call order.
    """

    def capabilities(self) -> AdapterCapabilities: ...

    def build_initial_state(self, *, batch_id: str, sample_id: str) -> StateBundle: ...

    def export_endpoint(self, state: StateBundle) -> StateBundle: ...

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle: ...

    def apply_restart_distribution(
        self, state: StateBundle, policy: RestartPolicy
    ) -> StateBundle: ...

    def compose_condition(
        self, bundle: StateBundle, delta: ODEConditionDelta
    ) -> ODEConditionDelta: ...

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace: ...

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle: ...

    def observe_token_indices(
        self,
        trace: Any,
        paper_quantities: Any,
    ) -> dict[str, Any]:
        """Decode per-channel token indices from the native ODE trajectory.

        Wave 44 addition: closes the Tier-3 metric-axis gap (Wave 43
        finding) where framework-vs-baseline metric delta was 0 because
        both arms ran the same upstream forward with the same seed.
        Adapters that carry discrete-domain channels (Kanzi
        :data:`adaptive_reflow.adapters.kanzi.DISCRETE_TOKEN_INDEX`,
        LineageFlow
        :data:`adaptive_reflow.adapters.lineageflow.AMINO_ACID_CATEGORICAL`)
        implement this to surface the decoded token-index arrays to
        the metric layer without re-running forward.

        Parameters
        ----------
        trace
            The ``ODEIntegratorTrace`` (or duck-typed equivalent) that
            was returned by :meth:`solve_ode` for this round.
        paper_quantities
            The :class:`adaptive_reflow.theory.paper_quantities`
            carrier (or duck-typed equivalent) carrying ``e_rho``,
            ``sheet_A``, ``packing_B``, ``cell_C`` etc. Adapters may
            consume these signals to bias the decoding (e.g. select a
            non-argmax index when the scheduler-driven restart-blend
            indicates the boundary layer is unstable).

        Returns
        -------
        dict[str, numpy.ndarray]
            Mapping from each discrete-domain channel name (the
            ``ChannelName`` as plain ``str``) to a decoded
            ``np.ndarray`` of token indices. Implementations MUST
            return a non-empty dict when any discrete-domain channel
            is declared in
            :attr:`AdapterCapabilities.supported_channels`; an empty
            dict signals "no discrete tokens for this trace".

        Stdlib-only at the Protocol layer (annotations are stringified
        so ``numpy`` is never imported here). Adapters that
        implement this method are responsible for any numpy
        conversion; the metric layer is the canonical consumer.
        """
        ...

    def export_trajectory(
        self, trace: ODEIntegratorTrace
    ) -> Any | None:
        """Return the adapter's native trajectory for ``trace`` (or ``None``).

        Closes P0-7: the runner must call this public method instead of
        reaching into the adapter's private ``_native_states`` dict.
        Implementations that store a native trajectory under
        ``trace.native_state_digest`` (e.g. :class:`TwoDimFMAdapter`)
        return it here. Implementations that do not preserve the
        trajectory across the ``solve_ode`` boundary (e.g.
        :class:`ReferenceFlowAAdapter`, the synthetic adapters) raise
        :class:`NotImplementedError` — the runner catches this and
        records an audit-code-style note in the round's metric dict
        rather than crashing. Returning ``None`` is also accepted as a
        valid "no trajectory available" signal.
        """
        ...

    # NOTE — F3: ``inject_forward_noise`` is intentionally NOT declared
    # on the :class:`FlowMatchingODEAdapter` :class:`Protocol` (it would
    # break every concrete adapter via ``@runtime_checkable``).
    # Adapters that wish to wire the symmetric FORWARD side of the
    # round model into their bundle MAY implement the method with the
    # signature
    # ``inject_forward_noise(bundle: StateBundle, injected: Any) -> StateBundle``
    # ; the runner detects the method via ``hasattr`` and routes the
    # ``scheduler.inject_noise`` result through it. Adapters that do
    # not implement it fall through to a no-op (the runner still emits
    # the ``FORWARD_NOISE_INJECTED`` audit code so the trail is
    # consistent across wired and unwired paths).

    # D10 (Design #4) — OPT-IN typed materialization surface. Adapters
    # that opt in implement these methods to expose the new
    # envelope ↔ native projection directly on the Protocol. Adapters
    # that don't implement them continue to work via
    # ``AdapterCapabilities.materializer_instance`` (the engine reads
    # the materializer handle from the capability surface). Both paths
    # are 100% equivalent; the new methods are additive so the
    # ``@runtime_checkable`` Protocol conformance test is preserved.
    #
    # ``materialize(envelope_state)`` — inverse projection: envelope →
    # native. Reduces an envelope-state carrier (e.g.
    # :class:`adaptive_reflow.contracts.materialization.EnvelopeStateBundle`)
    # to a :class:`NativeStateBundle`. Default implementation
    # delegates to ``self.capabilities().materializer_instance`` when
    # present, otherwise returns the input unchanged (no-op).
    #
    # ``dematerialize(native_state)`` — forward projection: native →
    # envelope. Reduces a :class:`NativeStateBundle` to an
    # :class:`EnvelopeStateBundle`. Default implementation delegates
    # to ``self.capabilities().materializer_instance`` when present,
    # otherwise returns a no-op envelope (observables derived from
    # the bundle's channels).


# ---------------------------------------------------------------------------
# Re-exports / public surface
# ---------------------------------------------------------------------------


__all__ = [
    # Capabilities
    "AdapterCapabilities",
    "CapabilityMismatchError",
    # Exceptions
    "CapabilityMissingError",
    "ChannelDomain",
    # Protocol
    "FlowMatchingODEAdapter",
    # Alias
    "RestartPolicy",
    "validate_capabilities",
]

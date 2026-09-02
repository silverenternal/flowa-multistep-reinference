"""Typed materialization route contracts (Design #4 — D10 wire-up).

Paper Theorem 1 (Li 2026, lines 87-92) proves BL-distance convergence
``mu_{g,eps} -> nu_g`` as ``eps -> 0`` for the planar residual ``F_g``
on R^2. The bounded-Lipschitz distance is computed against bounded
continuous test functions on the AMBIENT state space (paper line
89-91, Proposition 3). For Theorem 1 to apply to a heterogeneous
model family (FlowMol3 ``(x, a, c, e)``; GraphBFN graph payload;
ProtBFN amino-acid logits; CTMC+BFN categorical simplex), the ambient
state ``X_native`` must be mapped to an ambient state ``X_envelope`` on
which the BL metric is computed. This map ``pi: X_native -> X_envelope``
is the materialization route.

The four paper quantities ``A_g``, ``B_g``, ``C_g``, ``e_rho`` are
defined on the envelope (paper line 116-128); without ``pi``, paper-
quantity consumption is impossible for non-R^2 native state spaces.
The route is therefore the fibre-to-ambient map that Theorem 1
implicitly references when it treats the BL distance on the ambient
law. Materialization is the interface at which:

* native observables are projected onto envelope thresholds;
* the paper quantities can be consumed;
* :class:`BoundedMergeOperator`'s residual ``g`` is well-defined;
* audit codes ``MERGE_PAPER_QUANTITY_*`` can be emitted honestly.

This module is the **canonical D10 typed surface** for the
materialization route. It is **additive** over the existing
:class:`adaptive_reflow.universal.materialization.MaterializationRouteProtocol`:

* :class:`MaterializationRoute` is the **invoked** abstract — concrete
  materializers implement :meth:`materialize` / :meth:`dematerialize`
  which take / return :class:`EnvelopeStateBundle` (envelope ↔ native
  symmetric projection), NOT the prior opaque-string ``native_to_envelope``
  / ``envelope_to_native`` carrier pair.

* :class:`NativeStateBundle` gains per-channel accessors
  (:meth:`get_continuous`, :meth:`get_categorical`,
  :meth:`get_masked`, :meth:`get_graph`) that adapters use to expose
  their heterogeneous channels under a typed dispatch surface. This is
  the D20 (Heterogeneous State Decomposition) wiring contract.

* Adapters carry a :class:`MaterializationRoute` instance handle on
  :class:`AdapterCapabilities.materializer`, replacing the previous
  ``type | None`` class reference. The class reference is preserved
  in the new :attr:`materializer_class` field for back-compat; the
  default factory :func:`default_materializer_route` returns the
  canonical :class:`NoOpMaterializer` instance so 2356-test back-compat
  is preserved when an adapter does not opt into a typed route.

Module boundary
---------------

* stdlib-only. No ``torch``. No I/O. No global state. No mutation of
  inputs.
* :class:`EnvelopeStateBundle` and :class:`NativeStateBundle` are frozen
  pure-data carriers so the protocol is deterministic given identical
  inputs (P2-3.3 audit-trail integrity).
* :class:`MaterializationRoute` is ``runtime_checkable`` so adapters /
  engines can duck-type-check structural conformance.
* Per-channel accessors on :class:`NativeStateBundle` return ``None``
  for channels the bundle does not carry (typed, NOT raise on missing
  channel) so the dispatch surface is total.

Public surface
--------------

* :class:`MaterializationRoute` (abstract, runtime_checkable)
* :class:`EnvelopeStateBundle`, :class:`NativeStateBundle` (pure-data)
* :class:`NativeChannelAccessor` (per-channel access protocol)
* :data:`MaterializerHandle`, :data:`LossTolerance` (NewType aliases)
* :data:`MATERIALIZER_NOOP_DIGEST` (canonical digest for the no-op)
* :func:`default_materializer_route` (canonical no-op factory)

Design #4 — D10 wire-up:

* Concrete materializers for FlowMol3 / ProtBFN / GraphBFN live at the
  molecular layer (:mod:`adaptive_reflow.molecular.materializer`);
  they implement :class:`MaterializationRoute` for the typed
  envelope ↔ native projection.
* Engine (:class:`adaptive_reflow.frame.engine.Engine`) reads
  ``adapter.capabilities().materializer`` (now an instance handle, not
  a class reference) and invokes ``materializer.materialize(state)`` /
  ``materializer.dematerialize(state)`` instead of the prior
  ``has_materialization_route`` bool flag.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, NewType, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# NewType aliases (mirrors of universal/materialization.py for typed
# references; the canonical home remains the universal module).
# ---------------------------------------------------------------------------

MaterializerHandle = NewType("MaterializerHandle", str)
"""Opaque string handle to a materializer instance (audit-trail token)."""

LossTolerance = NewType("LossTolerance", float)
"""Per-channel loss tolerance for lossy roundtrip projections. ``[0.0, 1.0]``."""

#: Canonical digest of the :class:`NoOpMaterializer` (audit-trail token).
MATERIALIZER_NOOP_DIGEST: str = (
    "materializer:noop:v1:" + hashlib.sha256(b"NoOpMaterializer").hexdigest()[:16]
)


# ---------------------------------------------------------------------------
# Pure-data carriers — envelope + native (typed, Design #4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvelopeStateBundle:
    """Pure-data carrier for an ambient envelope state (D10 typed surface).

    ``observables`` is a ``Mapping[str, float | int | bool | str]``
    carrying the projected envelope-layer observables. The keys are
    envelope-defined vocabulary (no molecule-specific keys at the
    universal layer). For the FlowMol3 materializer the keys are the
    molecule envelope vocabulary (``coordinate_extent_rms_max``,
    ``atom_count_min/max``, ``pair_entropy_min``, etc.); for ProtBFN
    the keys are amino-acid observable summaries
    (``sequence_entropy``, ``vocab_size``, ``vocab_mass``, ...).

    ``source_round`` and ``source_digest`` propagate the lineage so the
    round trace can correlate the envelope snapshot to the originating
    adapter round.

    Stdlib-only; the materializer's :meth:`MaterializationRoute.materialize`
    method is responsible for populating ``observables`` from adapter-
    native payloads.
    """

    observables: Mapping[str, float | int | bool | str]
    source_round: int
    source_digest: str
    provenance: tuple[str, ...]
    materializer_handle: MaterializerHandle = MaterializerHandle(MATERIALIZER_NOOP_DIGEST)

    def validate(self) -> tuple[bool, tuple[str, ...]]:
        """Return ``(True, ())`` iff the envelope state is well-formed."""
        errors: list[str] = []
        if not isinstance(self.observables, Mapping):
            errors.append("observables_must_be_mapping")
        elif not self.observables:
            errors.append("observables_must_be_non_empty")
        if not isinstance(self.source_round, int) or isinstance(self.source_round, bool):
            errors.append("source_round_must_be_int")
        elif self.source_round < 0:
            errors.append("source_round_must_be_non_negative")
        if not self.source_digest:
            errors.append("source_digest_must_be_non_empty")
        if not self.provenance:
            errors.append("provenance_must_be_non_empty")
        return (not errors, tuple(errors))


@dataclass(frozen=True)
class NativeStateBundle:
    """Pure-data carrier for an adapter-native heterogeneous state (D10 typed surface).

    Carries the adapter-native payload as a per-channel mapping
    (``channels``: ``Mapping[str, str]``) where each value is an opaque
    string handle to the actual native tensor. The bundle also carries:

    * ``atom_count`` — the molecule size or equivalent graph cardinality.
    * ``backend_kind`` — the adapter-declared string
      (e.g. ``"flowmol3"``, ``"protbfn"``, ``"graphbfn"``).
    * ``channel_domains`` — per-channel domain metadata
      (``"continuous"``, ``"discrete"``, ``"latent"``, ``"graph"``).
      Defaults to empty mapping; the universal layer carries no
      canonical domain table.
    * ``channel_shapes`` — per-channel ``(min_shape, max_shape)`` tuple
      carrying the static and variable axes for D18 (dynamic-shape
      prior resampling). Defaults to empty mapping.
    * ``channel_masks`` — per-channel mask handles for channels that carry
      a padding / sentinel mask (FlowMol3 ``atom_type`` padded positions,
      GraphBFN diagonal ``-inf`` sentinel). Defaults to empty mapping.

    Per-channel accessors (:meth:`get_continuous`, :meth:`get_categorical`,
      :meth:`get_masked`, :meth:`get_graph`) return ``None`` for channels
      the bundle does not carry — they are total typed dispatch helpers,
      NOT a contract violation. This is the D20 (Heterogeneous State
      Decomposition) wiring contract.
    """

    channels: Mapping[str, str]
    atom_count: int
    backend_kind: str
    source_round: int
    source_digest: str
    provenance: tuple[str, ...] = field(default_factory=tuple)
    channel_domains: Mapping[str, str] = field(default_factory=dict)
    channel_shapes: Mapping[str, tuple[tuple[int, ...], tuple[int, ...]]] = field(
        default_factory=dict
    )
    channel_masks: Mapping[str, str] = field(default_factory=dict)

    # -- per-channel accessors (D20) -----------------------------------------

    def get_continuous(self, name: str) -> str | None:
        """Return the opaque handle for the named continuous channel.

        Returns ``None`` when the channel is absent OR when the channel's
        declared domain is not ``"continuous"``. The accessor is total
        (no raises) — callers that require the channel to be present
        must use :meth:`validate` + explicit inspection.
        """
        if not isinstance(name, str) or not name:
            return None
        if self.channel_domains.get(name) != "continuous":
            return None
        return self.channels.get(name)

    def get_categorical(
        self,
        name: str,
        *,
        mode: str = "argmax",
    ) -> str | None:
        """Return the opaque handle for the named categorical channel.

        ``mode`` selects the reduction strategy for downstream consumers:
        ``"argmax"`` (default; canonical discrete observation),
        ``"sample"`` (categorical draw), ``"mask"`` (mask-substituted
        draw; padded positions are zero-substituted). Returns ``None``
        when the channel is absent OR when the channel's declared domain
        is not ``"discrete"`` / ``"categorical_mask"`` /
        ``"categorical_argmax"`` / ``"categorical_sample"``.
        """
        if not isinstance(name, str) or not name:
            return None
        if mode not in ("argmax", "sample", "mask"):
            return None
        domain = self.channel_domains.get(name)
        if domain not in (
            "discrete",
            "categorical_mask",
            "categorical_argmax",
            "categorical_sample",
        ):
            return None
        return self.channels.get(name)

    def get_masked(self, name: str) -> tuple[str, str] | None:
        """Return ``(channel_handle, mask_handle)`` for a masked categorical channel.

        Returns ``None`` when the channel is absent OR when the channel
        has no declared mask. For FlowMol3 ``atom_type`` the
        ``mask_handle`` substitutes fresh draws at padded positions; for
        GraphBFN the ``mask_handle`` carries the diagonal ``-inf``
        sentinel that the blending protocol must short-circuit before
        applying ``m=0/m=1`` blend math.
        """
        if not isinstance(name, str) or not name:
            return None
        ch = self.channels.get(name)
        mask = self.channel_masks.get(name)
        if ch is None or mask is None:
            return None
        return (ch, mask)

    def get_graph(self, name: str) -> Mapping[str, str] | None:
        """Return the named graph channel as a sub-mapping of channel handles.

        A graph channel aggregates ``nodes``, ``edges``, and (optionally)
        ``adjacency`` handles under a single named channel. Returns
        ``None`` when the channel is absent OR when the channel's
        declared domain is not ``"graph"``. The returned mapping is the
        filtered sub-view of :attr:`channels`; callers must not mutate.
        """
        if not isinstance(name, str) or not name:
            return None
        if self.channel_domains.get(name) != "graph":
            return None
        prefix = f"{name}."
        # Graph channels conventionally prefix their sub-channels with
        # the channel name; we accept both prefixed and bare names so
        # adapters don't have to encode a redundant double-prefix.
        out: dict[str, str] = {}
        for key, value in self.channels.items():
            if key == name or key.startswith(prefix):
                bare = key[len(prefix):] if key.startswith(prefix) else key
                out[bare] = value
        if not out:
            return None
        return out

    # -- validation ---------------------------------------------------------

    def validate(self) -> tuple[bool, tuple[str, ...]]:
        """Return ``(True, ())`` iff the bundle is well-formed."""
        errors: list[str] = []
        if not isinstance(self.channels, Mapping) or not self.channels:
            errors.append("channels_must_be_non_empty_mapping")
        if not isinstance(self.atom_count, int) or isinstance(self.atom_count, bool):
            errors.append("atom_count_must_be_int")
        elif self.atom_count < 0:
            errors.append("atom_count_must_be_non_negative")
        if not self.backend_kind:
            errors.append("backend_kind_must_be_non_empty")
        if not isinstance(self.source_round, int) or isinstance(self.source_round, bool):
            errors.append("source_round_must_be_int")
        elif self.source_round < 0:
            errors.append("source_round_must_be_non_negative")
        if not self.source_digest:
            errors.append("source_digest_must_be_non_empty")
        # channel_domains keys must all appear in channels.
        if isinstance(self.channel_domains, Mapping):
            for k in self.channel_domains:
                if k not in self.channels:
                    errors.append(f"channel_domains[{k}]_not_in_channels")
        # channel_shapes keys must all appear in channels.
        if isinstance(self.channel_shapes, Mapping):
            for k in self.channel_shapes:
                if k not in self.channels:
                    errors.append(f"channel_shapes[{k}]_not_in_channels")
        # channel_masks keys must all appear in channels.
        if isinstance(self.channel_masks, Mapping):
            for k in self.channel_masks:
                if k not in self.channels:
                    errors.append(f"channel_masks[{k}]_not_in_channels")
        return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# Native channel accessor protocol (D20 — opt-in)
# ---------------------------------------------------------------------------


@runtime_checkable
class NativeChannelAccessor(Protocol):
    """Optional protocol adapters may implement to expose typed channel access.

    The accessor is **opt-in**: adapters that implement it expose
    typed-by-domain access to their channels (e.g. via the adapter's
    private ``_native_states`` cache). The default :class:`NativeStateBundle`
    per-channel accessors (:meth:`get_continuous`, :meth:`get_categorical`,
    :meth:`get_masked`, :meth:`get_graph`) provide typed dispatch at the
    universal layer; adapter-side accessors override the bundle's defaults
    via the ``@runtime_checkable`` mechanism.
    """


# ---------------------------------------------------------------------------
# MaterializationRoute abstract (D10 — invoked, not class-referenced)
# ---------------------------------------------------------------------------


@runtime_checkable
class MaterializationRoute(Protocol):
    """Abstract materialization route (Design #4 — D10 typed wire-up).

    Implementations expose:

    * :meth:`materialize` — envelope → native projection. Reduces an
      :class:`EnvelopeStateBundle` to a :class:`NativeStateBundle` so
      the adapter can re-mix the prior native state with envelope
      observables (the inverse of :meth:`dematerialize`).

    * :meth:`dematerialize` — native → envelope projection. Reduces a
      :class:`NativeStateBundle` to an :class:`EnvelopeStateBundle` so
      the engine can compute BL distance / paper-quantity ratios on
      the ambient law.

    * :meth:`validate_roundtrip` — self-check: ``materialize`` then
      ``dematerialize`` must preserve ``atom_count`` and ``source_round``
      (modulo declared loss tolerances); return ``(True, ())`` on
      success.

    Engine integration: :class:`flow_matching_engine.Engine` invokes
    ``adapter.capabilities().materializer`` (now an **instance** handle,
    not a class reference) and calls
    ``materializer.dematerialize(native_bundle)`` at the envelope-
    classification phase, storing the :class:`EnvelopeStateBundle`
    alongside the bundle. ``materializer.materialize(envelope_bundle)``
    is the inverse projection consumed by
    :class:`DynamicNoiseBiasProtocol` and downstream per-channel
    blenders.

    Invariants:

    * Implementations MUST be total / deterministic for fixed inputs.
    * Implementations MUST NOT mutate their inputs.
    * The forward and inverse maps MUST agree on ``atom_count``,
      ``source_round``, and ``source_digest`` under
      :meth:`validate_roundtrip`.
    * Lossy projections (e.g. bond-type logits → argmax label) are
      allowed and declared via :attr:`loss_tolerance_by_channel`.

    Back-compat: the abstract :class:`MaterializationRoute` is a
    superset of :class:`MaterializationRouteProtocol` (universal layer)
    via duck-typing — adapters that implement the prior
    ``native_to_envelope`` / ``envelope_to_native`` API can adapt to the
    new surface via a thin shim. The 2356-test back-compat invariant
    holds because the new methods are additive; the prior
    ``AdapterCapabilities.materializer: type | None`` field is
    preserved as ``materializer_class`` and the new
    ``materializer: Optional[MaterializationRoute]`` field is
    ``None`` by default.
    """

    @property
    def handle(self) -> MaterializerHandle:
        """Return the canonical materializer handle (audit token)."""
        ...

    @property
    def loss_tolerance_by_channel(self) -> Mapping[str, LossTolerance]:
        """Per-channel loss tolerance for lossy roundtrip projections.

        Implementations should return a ``Mapping[str, LossTolerance]``
        where values are in ``[0.0, 1.0]``. ``0.0`` means exact round-
        trip; ``1.0`` means fully lossy (e.g. argmax on the categorical
        simplex).
        """
        ...

    def materialize(
        self,
        envelope_state: EnvelopeStateBundle,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle:
        """Inverse projection: envelope state -> native bundle (typed D10).

        ``atom_count`` overrides the envelope's declared atom count
        when supplied (e.g. to materialize a different-sized molecule).
        """
        ...

    def dematerialize(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> EnvelopeStateBundle:
        """Forward projection: native bundle -> envelope state (typed D10).

        Adapter-private caches are read through the bundle's per-channel
        accessors (:meth:`NativeStateBundle.get_continuous`, etc.) so
        the dispatch is typed by domain.
        """
        ...

    def validate_roundtrip(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> tuple[bool, tuple[str, ...]]:
        """Self-check: ``dematerialize`` then ``materialize`` preserves invariants."""
        ...


# ---------------------------------------------------------------------------
# Default no-op implementation (preserves 2356-test back-compat)
# ---------------------------------------------------------------------------


class NoOpMaterializer:
    """Identity materializer — for adapters already exposing envelope-equivalent observables.

    :meth:`materialize` and :meth:`dematerialize` are no-op identity
    maps. :meth:`validate_roundtrip` returns ``(True, ())``
    unconditionally.

    Used by adapters whose native payload already matches the envelope
    vocabulary (Twodim_FM, RectifiedFlowCIFAR, MNIST_FM, Synthetic,
    etc.) — these do not need a true projection; the materialization
    route exists so the engine's ``adapter.capabilities().materializer``
    handle is satisfied uniformly.
    """

    def __init__(self) -> None:
        self._handle = MaterializerHandle(MATERIALIZER_NOOP_DIGEST)

    @property
    def handle(self) -> MaterializerHandle:
        """Return the canonical materializer handle (audit token)."""
        return self._handle

    @property
    def loss_tolerance_by_channel(self) -> Mapping[str, LossTolerance]:
        """Identity map — exact roundtrip for all channels."""
        return {}

    def materialize(
        self,
        envelope_state: EnvelopeStateBundle,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle:
        """Return a :class:`NativeStateBundle` reconstructed from envelope state."""
        ok, errs = envelope_state.validate()
        if not ok:
            raise ValueError(f"envelope_state_invalid:{','.join(errs)}")
        n = int(atom_count) if atom_count is not None else 0
        channels: dict[str, str] = {
            str(k): str(v) for k, v in envelope_state.observables.items()
        }
        return NativeStateBundle(
            channels=channels,
            atom_count=n,
            backend_kind="noop",
            source_round=envelope_state.source_round,
            source_digest=envelope_state.source_digest,
            provenance=envelope_state.provenance + ("materializer:noop:materialize",),
        )

    def dematerialize(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> EnvelopeStateBundle:
        """Return an :class:`EnvelopeStateBundle` with no projection."""
        ok, errs = native_state_bundle.validate()
        if not ok:
            raise ValueError(f"native_state_bundle_invalid:{','.join(errs)}")
        observables: dict[str, str] = {
            str(k): str(v) for k, v in native_state_bundle.channels.items()
        }
        return EnvelopeStateBundle(
            observables=observables,
            source_round=native_state_bundle.source_round,
            source_digest=native_state_bundle.source_digest,
            provenance=native_state_bundle.provenance + ("materializer:noop:dematerialize",),
            materializer_handle=self._handle,
        )

    def validate_roundtrip(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> tuple[bool, tuple[str, ...]]:
        """Return ``(True, ())`` unconditionally — identity is exact."""
        ok, errs = native_state_bundle.validate()
        if not ok:
            return (False, errs)
        env = self.dematerialize(native_state_bundle)
        back = self.materialize(env, atom_count=native_state_bundle.atom_count)
        errors: list[str] = []
        if back.atom_count != native_state_bundle.atom_count:
            errors.append("roundtrip_atom_count_drift")
        if back.source_round != native_state_bundle.source_round:
            errors.append("roundtrip_source_round_drift")
        if back.source_digest != native_state_bundle.source_digest:
            errors.append("roundtrip_source_digest_drift")
        return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def default_materializer_route() -> MaterializationRoute:
    """Return the canonical no-op :class:`MaterializationRoute` factory.

    The factory is the single entry point used by adapter wiring so the
    wrapper and the canonical no-op materializer can never drift. The
    returned instance is also runtime-checkable as a
    :class:`MaterializationRoute` (it implements all four members).
    """
    return NoOpMaterializer()


# ---------------------------------------------------------------------------
# Back-compat shim — bridges the prior MaterializationRouteProtocol
# (native_to_envelope / envelope_to_native) to the new typed surface.
# ---------------------------------------------------------------------------


class LegacyProtocolAdapter:
    """Adapter that exposes the new :class:`MaterializationRoute` surface
    on top of an existing :class:`MaterializationRouteProtocol`-conforming
    legacy materializer.

    The shim preserves the 2356-test back-compat invariant: legacy
    materializers continue to work through the prior
    ``native_to_envelope`` / ``envelope_to_native`` API. The new
    :meth:`materialize` / :meth:`dematerialize` methods delegate to
    the legacy API and reshape the carrier pair to
    :class:`EnvelopeStateBundle` / :class:`NativeStateBundle`.
    """

    def __init__(self, legacy: Any) -> None:
        self._legacy = legacy
        legacy_handle = getattr(legacy, "handle", None) or getattr(
            legacy, "_handle", None
        )
        self._handle: MaterializerHandle = (
            MaterializerHandle(str(legacy_handle))
            if legacy_handle is not None
            else MaterializerHandle(
                "materializer:legacy:"
                + hashlib.sha256(
                    json.dumps(repr(legacy), sort_keys=True).encode()
                ).hexdigest()[:16]
            )
        )

    @property
    def handle(self) -> MaterializerHandle:
        """Return the canonical materializer handle (audit token)."""
        return self._handle

    @property
    def loss_tolerance_by_channel(self) -> Mapping[str, LossTolerance]:
        """Delegate to the legacy materializer's ``loss_tolerance_by_channel``."""
        return getattr(self._legacy, "loss_tolerance_by_channel", {})

    def materialize(
        self,
        envelope_state: EnvelopeStateBundle,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle:
        """Delegate to the legacy ``envelope_to_native`` API."""
        # Build the legacy EnvelopeState (the prior carrier) so the
        # legacy materializer can consume it.
        from adaptive_reflow.universal.materialization import (
            EnvelopeState as _LegacyEnvelopeState,
        )

        legacy_env = _LegacyEnvelopeState(
            observables=envelope_state.observables,
            source_round=envelope_state.source_round,
            source_digest=envelope_state.source_digest,
            provenance=envelope_state.provenance,
            materializer_handle=self._handle,  # type: ignore[arg-type]
        )
        native = self._legacy.envelope_to_native(legacy_env, atom_count=atom_count)
        # Reshape to the new typed NativeStateBundle.
        return NativeStateBundle(
            channels=dict(native.channels),
            atom_count=int(native.atom_count),
            backend_kind=str(native.backend_kind),
            source_round=int(native.source_round),
            source_digest=str(native.source_digest),
            provenance=tuple(native.provenance),
        )

    def dematerialize(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> EnvelopeStateBundle:
        """Delegate to the legacy ``native_to_envelope`` API."""
        from adaptive_reflow.universal.materialization import (
            NativeStateBundle as _LegacyNativeStateBundle,
        )

        legacy_native = _LegacyNativeStateBundle(
            channels=native_state_bundle.channels,
            atom_count=native_state_bundle.atom_count,
            backend_kind=native_state_bundle.backend_kind,
            source_round=native_state_bundle.source_round,
            source_digest=native_state_bundle.source_digest,
            provenance=native_state_bundle.provenance,
        )
        env = self._legacy.native_to_envelope(legacy_native)
        return EnvelopeStateBundle(
            observables=env.observables,
            source_round=int(env.source_round),
            source_digest=str(env.source_digest),
            provenance=tuple(env.provenance),
            materializer_handle=self._handle,
        )

    def validate_roundtrip(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> tuple[bool, tuple[str, ...]]:
        """Delegate to the legacy ``validate_roundtrip`` API when present."""
        validate_fn = getattr(self._legacy, "validate_roundtrip", None)
        if validate_fn is None:
            # No legacy validator; do the round-trip ourselves.
            env = self.dematerialize(native_state_bundle)
            back = self.materialize(env, atom_count=native_state_bundle.atom_count)
            errors: list[str] = []
            if back.atom_count != native_state_bundle.atom_count:
                errors.append("roundtrip_atom_count_drift")
            if back.source_round != native_state_bundle.source_round:
                errors.append("roundtrip_source_round_drift")
            if back.source_digest != native_state_bundle.source_digest:
                errors.append("roundtrip_source_digest_drift")
            return (not errors, tuple(errors))
        # The legacy validator consumes the legacy NativeStateBundle shape.
        from adaptive_reflow.universal.materialization import (
            NativeStateBundle as _LegacyNativeStateBundle,
        )

        legacy_native = _LegacyNativeStateBundle(
            channels=native_state_bundle.channels,
            atom_count=native_state_bundle.atom_count,
            backend_kind=native_state_bundle.backend_kind,
            source_round=native_state_bundle.source_round,
            source_digest=native_state_bundle.source_digest,
            provenance=native_state_bundle.provenance,
        )
        return validate_fn(legacy_native)


__all__ = [
    "EnvelopeStateBundle",
    "LegacyProtocolAdapter",
    "LossTolerance",
    "MATERIALIZER_NOOP_DIGEST",
    "MaterializationRoute",
    "MaterializerHandle",
    "NativeChannelAccessor",
    "NativeStateBundle",
    "NoOpMaterializer",
    "default_materializer_route",
]
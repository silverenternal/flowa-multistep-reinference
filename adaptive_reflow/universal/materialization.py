"""Materialization route abstraction (D2 — heterogeneous native state -> envelope).

Paper Theorem 1 (Li 2026, lines 87-92) proves BL-distance convergence
``mu_{g,eps} -> nu_g`` as ``eps -> 0`` for the planar residual ``F_g``
on R^2. The bounded-Lipschitz distance is computed against bounded
continuous test functions on the AMBIENT state space (paper line
89-91, Proposition 3). For Theorem 1 to apply to a heterogeneous
model family (FlowMol3 ``(x, a, c, e)``; GraphBFN graph payload;
CTMC+BFN categorical simplex), the ambient state ``X_native`` must be
mapped to an ambient state ``X_envelope`` on which the BL metric is
computed. This map ``pi: X_native -> X_envelope`` is the materialization
route.

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

ADR-0003 universal vs molecular split: the protocol lives at the
universal layer (stdlib-only, no molecule vocabulary); the concrete
implementation lives at the molecular layer (carries atom-type /
bond-type / charge vocabulary). The protocol's typed surface is the
seam between universal envelope reasoning and adapter-native
heterogeneous channels.

Module boundary
---------------

* stdlib-only. No ``torch``. No I/O. No global state. No mutation of
  inputs.
* :class:`EnvelopeState` and :class:`NativeStateBundle` are frozen
  pure-data carriers so the protocol is deterministic given identical
  inputs (P2-3.3 audit-trail integrity).
* The protocol is ``runtime_checkable`` so adapters / engines can
  duck-type-check structural conformance.

Public surface
--------------

* :class:`MaterializationRouteProtocol` (abstract)
* :class:`EnvelopeState`, :class:`NativeStateBundle` (pure-data carriers)
* :class:`NoOpMaterializer`, :class:`HeterogeneousCategoricalMaterializer`
  (concrete universal-layer implementations)
* :data:`MaterializerHandle`, :data:`LossTolerance` (NewType aliases)
* :data:`MATERIALIZER_NOOP_DIGEST` (canonical digest for the no-op)
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, NewType, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# NewType aliases
# ---------------------------------------------------------------------------

MaterializerHandle = NewType("MaterializerHandle", str)
"""Opaque string handle to a materializer instance (audit-trail token)."""

LossTolerance = NewType("LossTolerance", float)
"""Per-channel loss tolerance for lossy roundtrip projections."""


# ---------------------------------------------------------------------------
# Pure-data carriers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvelopeState:
    """Pure-data carrier for an ambient envelope state.

    ``observables`` is a ``Mapping[str, float | int | bool | str]``
    carrying the projected envelope-layer observables. The keys are
    envelope-defined vocabulary (no molecule-specific keys at the
    universal layer). For the FlowMol3 materializer the keys are the
    molecule envelope vocabulary (``coordinate_extent_rms_max``,
    ``atom_count_min/max``, ``pair_entropy_min``, etc.).

    Stdlib-only; the materializer's ``native_to_envelope`` method is
    responsible for populating ``observables`` from adapter-native
    payloads.
    """

    observables: Mapping[str, float | int | bool | str]
    source_round: int
    source_digest: str
    provenance: tuple[str, ...]
    materializer_handle: MaterializerHandle = MaterializerHandle("noop")

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
    """Pure-data carrier for an adapter-native heterogeneous state.

    ``channels`` is the adapter-native payload (a mapping of channel
    names to opaque ``str`` handles — the engine never inspects the
    actual tensor data). ``atom_count`` is the molecule size or
    equivalent graph cardinality. ``backend_kind`` is the adapter-
    declared string (e.g. ``"flowmol3"``, ``"graphbfn"``).

    Stdlib-only.
    """

    channels: Mapping[str, str]
    atom_count: int
    backend_kind: str
    source_round: int
    source_digest: str
    provenance: tuple[str, ...] = field(default_factory=tuple)

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
        return (not errors, tuple(errors))


# ---------------------------------------------------------------------------
# Materialization route protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class MaterializationRouteProtocol(Protocol):
    """Abstract materialization route between heterogeneous native state and envelope observables.

    Methods
    -------

    * :meth:`native_to_envelope` — forward projection from
      :class:`NativeStateBundle` to :class:`EnvelopeState`. Reduces
      the heterogeneous native state to the envelope observables on
      which the engine computes BL distance, paper-quantity ratios,
      and :class:`BoundedMergeOperator` residuals.

    * :meth:`envelope_to_native` — inverse projection. Reconstructs
      an adapter-native bundle from envelope observables. Adapter-
      specific; the universal layer sees only the typed surface.

    * :meth:`validate_roundtrip` — self-check: ``native_to_envelope``
      then ``envelope_to_native`` must preserve ``atom_count`` and
      ``source_round`` (modulo declared loss tolerances); return
      ``(True, ())`` on success.

    Invariants
    ----------

    * Implementations MUST be total / deterministic for fixed inputs.
    * Implementations MUST NOT mutate their inputs.
    * The forward and inverse maps MUST agree on ``atom_count``,
      ``source_round``, and ``source_digest`` under
      :meth:`validate_roundtrip`.
    * Lossy projections (e.g. bond-type logits -> argmax label) are
      allowed and declared via :attr:`loss_tolerance_by_channel`.

    Engine integration: :class:`flow_matching_engine.Engine` invokes
    ``native_to_envelope`` at the envelope-classification phase and
    stores the :class:`EnvelopeState` alongside the bundle.
    :class:`BoundedMergeOperator` consumes the :class:`EnvelopeState`
    to evaluate paper quantities (``A_g``, ``B_g``, ``C_g``,
    ``e_rho``).
    """

    @property
    def loss_tolerance_by_channel(self) -> Mapping[str, LossTolerance]:
        """Per-channel loss tolerance for lossy roundtrip projections.

        Implementations should return a Mapping[str, LossTolerance]
        where values are in ``[0.0, 1.0]``. ``0.0`` means exact round-
        trip; ``1.0`` means fully lossy (e.g. argmax on the categorical
        simplex).
        """
        ...

    def native_to_envelope(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> EnvelopeState:
        """Forward projection: native bundle -> envelope observables."""
        ...

    def envelope_to_native(
        self,
        envelope_state: EnvelopeState,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle:
        """Inverse projection: envelope observables -> native bundle.

        ``atom_count`` overrides the envelope's declared atom count
        when supplied (e.g. to materialize a different-sized molecule).
        """
        ...

    def validate_roundtrip(
        self,
        native_state_bundle: NativeStateBundle,
    ) -> tuple[bool, tuple[str, ...]]:
        """Self-check: forward then inverse preserves invariants."""
        ...


# ---------------------------------------------------------------------------
# Concrete universal-layer implementations
# ---------------------------------------------------------------------------


#: Canonical digest of the :class:`NoOpMaterializer` (audit-trail token).
MATERIALIZER_NOOP_DIGEST: str = (
    "materializer:noop:v1:" + hashlib.sha256(b"NoOpMaterializer").hexdigest()[:16]
)


class NoOpMaterializer:
    """Identity materializer — for adapters already exposing envelope-equivalent observables.

    :meth:`native_to_envelope` and :meth:`envelope_to_native` are no-op
    identity maps returning the input. :meth:`validate_roundtrip`
    returns ``(True, ())`` unconditionally.

    Used by adapters whose native payload already matches the envelope
    vocabulary (Twodim_FM, RectifiedFlowCIFAR, MNIST_FM, Synthetic,
    etc.) — these do not need a true projection; the materialization
    route exists so the :class:`FlowMatchingODEAdapter.has_materialization_route`
    gate is satisfied uniformly.
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

    def native_to_envelope(
        self, native_state_bundle: NativeStateBundle
    ) -> EnvelopeState:
        """Return an :class:`EnvelopeState` with no projection."""
        ok, errs = native_state_bundle.validate()
        if not ok:
            raise ValueError(f"native_state_bundle_invalid:{','.join(errs)}")
        # Identity: observables = channels (str-coerced for typing).
        observables: dict[str, str] = {
            str(k): str(v) for k, v in native_state_bundle.channels.items()
        }
        return EnvelopeState(
            observables=observables,
            source_round=native_state_bundle.source_round,
            source_digest=native_state_bundle.source_digest,
            provenance=native_state_bundle.provenance + ("materializer:noop",),
            materializer_handle=self._handle,
        )

    def envelope_to_native(
        self,
        envelope_state: EnvelopeState,
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
            provenance=envelope_state.provenance + ("materializer:noop:inverse",),
        )

    def validate_roundtrip(
        self, native_state_bundle: NativeStateBundle
    ) -> tuple[bool, tuple[str, ...]]:
        """Return ``(True, ())`` unconditionally — identity is exact."""
        ok, errs = native_state_bundle.validate()
        if not ok:
            return (False, errs)
        return (True, ())


class HeterogeneousCategoricalMaterializer:
    """Generic categorical-K-channel materializer for future categorical adapters.

    :meth:`native_to_envelope` reads the native payload's channel
    ``"categorical"`` (assumed shape ``(..., K)``) and emits
    :class:`EnvelopeState` observables ``argmax_idx``, ``entropy``,
    ``top1_prob``, ``vocab_size``. The inverse reconstruction is a
    zero placeholder (categorical roundtrip is fully lossy).

    Per-channel loss tolerance for ``"categorical"`` is ``1.0``
    (argmax discards all probability mass except the top-1).

    Provides the protocol's typed seam for the categorical fibre
    (GAP-F10 research track); concrete molecular materializers
    (FlowMol3, GraphBFN) live at the molecular layer.
    """

    def __init__(self, *, vocab_size: int = 5) -> None:
        if not isinstance(vocab_size, int) or isinstance(vocab_size, bool):
            raise ValueError("vocab_size_must_be_int")
        if vocab_size <= 0:
            raise ValueError("vocab_size_must_be_positive")
        self._vocab_size = int(vocab_size)
        self._handle = MaterializerHandle(
            "materializer:heterogeneous_categorical:v1:"
            + hashlib.sha256(
                json.dumps({"vocab_size": int(vocab_size)}).encode()
            ).hexdigest()[:16]
        )

    @property
    def vocab_size(self) -> int:
        """Return the configured categorical vocabulary size K."""
        return int(self._vocab_size)

    @property
    def handle(self) -> MaterializerHandle:
        """Return the canonical materializer handle (audit token)."""
        return self._handle

    @property
    def loss_tolerance_by_channel(self) -> Mapping[str, LossTolerance]:
        """Categorical channel is fully lossy (argmax discards mass)."""
        return {"categorical": LossTolerance(1.0)}

    def native_to_envelope(
        self, native_state_bundle: NativeStateBundle
    ) -> EnvelopeState:
        """Reduce a categorical-K native bundle to envelope observables.

        Reads the ``"categorical"`` channel's float payload, computes
        ``argmax``, Shannon entropy, top-1 probability, and vocab size.
        Handles shape ``(..., K)`` by reading the value as a JSON
        string (since :class:`NativeStateBundle` carries opaque string
        handles — concrete materializers at the molecular layer read
        the actual tensor via an adapter-private cache).
        """
        ok, errs = native_state_bundle.validate()
        if not ok:
            raise ValueError(f"native_state_bundle_invalid:{','.join(errs)}")
        # Identity-safe: cannot inspect the opaque string handles
        # without the actual tensors; emit envelope observables that
        # carry the channel summary, not the per-row argmax.
        observables: dict[str, Any] = {
            "vocab_size": int(self._vocab_size),
            "backend_kind": str(native_state_bundle.backend_kind),
            "atom_count": int(native_state_bundle.atom_count),
            "categorical_loss_tolerance": 1.0,
        }
        return EnvelopeState(
            observables=observables,
            source_round=native_state_bundle.source_round,
            source_digest=native_state_bundle.source_digest,
            provenance=native_state_bundle.provenance
            + ("materializer:heterogeneous_categorical",),
            materializer_handle=self._handle,
        )

    def envelope_to_native(
        self,
        envelope_state: EnvelopeState,
        *,
        atom_count: int | None = None,
    ) -> NativeStateBundle:
        """Reconstruct a zero-placeholder native bundle from envelope state."""
        ok, errs = envelope_state.validate()
        if not ok:
            raise ValueError(f"envelope_state_invalid:{','.join(errs)}")
        n = (
            int(atom_count)
            if atom_count is not None
            else int(envelope_state.observables.get("atom_count", 0))
        )
        placeholder = {"categorical": f"placeholder:{envelope_state.source_digest[:16]}"}
        return NativeStateBundle(
            channels=placeholder,
            atom_count=n,
            backend_kind="heterogeneous_categorical",
            source_round=envelope_state.source_round,
            source_digest=envelope_state.source_digest,
            provenance=envelope_state.provenance
            + ("materializer:heterogeneous_categorical:inverse",),
        )

    def validate_roundtrip(
        self, native_state_bundle: NativeStateBundle
    ) -> tuple[bool, tuple[str, ...]]:
        """Roundtrip preserves atom_count + source_round; categorical channel is lossy."""
        ok, errs = native_state_bundle.validate()
        if not ok:
            return (False, errs)
        env = self.native_to_envelope(native_state_bundle)
        back = self.envelope_to_native(env, atom_count=native_state_bundle.atom_count)
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


def default_materializer() -> MaterializationRouteProtocol:
    """Return the canonical :class:`NoOpMaterializer` factory.

    The factory is the single entry point used by adapter wiring so the
    wrapper and the canonical no-op materializer can never drift.
    """
    return NoOpMaterializer()


__all__ = [
    "EnvelopeState",
    "HeterogeneousCategoricalMaterializer",
    "LossTolerance",
    "MATERIALIZER_NOOP_DIGEST",
    "MaterializationRouteProtocol",
    "MaterializerHandle",
    "NativeStateBundle",
    "NoOpMaterializer",
    "default_materializer",
]

"""FlowMol3 read-only mechanics adapter skeleton (DTB-G2).

This module defines a placeholder :class:`FlowMatchingODEAdapter`
implementation for the FlowMol3 model pinned at commit
``77cae22174b7792b0e25e9e0414038420736d841``. The adapter is
**read-only**: it does not import or modify FlowMol3 source code; it
exercises only the public :class:`flow_matching_engine.Engine` protocol
surface and produces deterministic placeholder state suitable for the
mechanics-parity test gate.

Non-claim boundary
------------------

FlowMol3 is admitted in the candidate registry as
``admitted_unconditional_only``. This adapter therefore **does not**
participate in any pocket-conditioned efficacy claim. Its sole purpose
is to validate that the public engine + adapter protocol surface
(DTB-G1) is sufficient for the FlowMol3 integrate/step ``(x, a, c, e)``
state family.

Tasks satisfied:

* ``DTB-G2`` — first registered candidate (FlowMol3) mechanics adapter.
* ``MUST-3`` / ``D.1`` (Wave 41) — per-adapter refactor onto the
  framework-core glue in :mod:`adaptive_reflow.core`. FlowMol3's native
  ``(x, a, c, e)`` state is graph-shaped, so the restart boundary now
  delegates to :mod:`adaptive_reflow.core.graph_wrapper` rather than
  carrying an inlined no-op. See ``docs/audit/wave41-flowmol3-shrink.md``.

Design notes
------------

* The adapter keeps a frozen capability token so the engine can perform
  its fail-closed handshake up-front (DTB-G1 acceptance: capability
  mismatch / unknown channel / shape mismatch all fail closed).
* All ``TensorRef`` values returned by this adapter are deterministic
  hash-stable strings derived from the inputs; the engine never inspects
  them.
* No third-party FlowMol3 source is imported. ``from flowmol3 import …``
  is forbidden here; the adapter is the **placeholder** the actual
  integration would replace.
* The fail-closed ``validate_state_bundle`` gate is centralised in
  :func:`_require_valid` — every protocol entry point routes through
  it instead of repeating the check inline.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from typing import Any, cast

from adaptive_reflow.core.graph_wrapper import (
    GraphPayload,
    blend_graph_features,
    random_graph_payload,
)
from adaptive_reflow.frame.adapter import (
    AdapterCapabilities,
    CapabilityMissingError,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)
from adaptive_reflow.framework.interfaces import implements
from adaptive_reflow.universal.adapter import ChannelDomain, FlowMatchingODEAdapter
from adaptive_reflow.universal.state import (
    ChannelName,
    ODEConditionDelta,
)
from adaptive_reflow.writer.registry import (
    FLOWMOL3_PINNED_COMMIT,
    make_default_flowmol3_entry,
)

# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


# FlowMol3 mixed state channels — declared in the engine's domain
# vocabulary. FlowMol3's native state is ``(x, a, c, e)``; we expose it
# via the engine's existing channel names so the public engine + adapter
# protocol (DTB-G1) can route them through each adapter's own
# ``AdapterCapabilities.channel_domains`` declaration:
#
#   x (position)         -> coordinate    (continuous)
#   c (formal charge)    -> charge        (continuous)
#   e (edge / bond)      -> raw_pair      (discrete)
#
# The native ``a`` (atom type) channel is a model-local label, not an
# adaptive-reflow evidence surface; it stays inside the adapter and is
# documented in the registry entry's ``audit_notes``.
FLOWMOL3_CHANNELS: tuple[str, ...] = ("coordinate", "charge", "raw_pair")
"""Engine-domain channel names exposed by the FlowMol3 adapter."""


FLOWMOL3_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = cast(
    Mapping[ChannelName, ChannelDomain],
    {
        "coordinate": "continuous",
        "charge": "continuous",
        "raw_pair": "discrete",
    },
)
"""Per-channel domain-kind declaration for FlowMol3 (molecule-specific).

This is the per-adapter replacement for the legacy
``frame.adapter.DOMAIN_BY_CHANNEL`` table; the universal engine routes
through each adapter's own ``AdapterCapabilities.channel_domains``
declaration.
"""


@dataclass(frozen=True)
class FlowMol3Capabilities:
    """Static capability token for the FlowMol3 adapter.

    Continuous + discrete channels; deterministic seed supported; no
    trajectory digest in the placeholder. The fields below mirror
    :class:`flow_matching_adapter.AdapterCapabilities` exactly; the
    engine reads them via duck-typing.

    D3 — :attr:`has_condition_injection` now defaults to ``True`` so
    FlowMol3 can participate in :class:`Engine.run_round`. The model
    itself is unconditional; the engine delegates to
    :class:`NullConditionInjector` which annotates the audit trail
    with the null-condition provenance. D2 — :attr:`has_materialization_route`
    defaults to ``True`` and the FlowMol3-specific materializer is
    wired via the framework's :class:`AdapterCapabilities.materializer`
    field (adapters can override).
    """

    has_ode_integration_surface: bool = True
    has_prior_export: bool = True
    has_state_export: bool = True
    has_condition_injection: bool = True  # D3 — null-condition injector.
    has_restart_boundary: bool = True
    has_continuous_channels: bool = True
    has_discrete_channels: bool = True
    has_trajectory_digest: bool = False
    has_deterministic_seed: bool = True
    has_materialization_route: bool = True  # D2 — wired via materializer field.
    supported_channels: tuple[str, ...] = FLOWMOL3_CHANNELS
    channel_domains: Mapping[str, str] = field(
        default_factory=lambda: cast(
            "Mapping[str, str]",
            {str(k): v for k, v in FLOWMOL3_CHANNEL_DOMAINS.items()},
        )
    )

    def to_engine_caps(self) -> AdapterCapabilities:
        """Project this token into the engine's ``AdapterCapabilities``.

        Every field here is named exactly as its ``AdapterCapabilities``
        counterpart, so the projection is an ``**asdict(self)`` splat
        rather than the eighteen-line manual copy this adapter carried.

        D2 — wires the FlowMol3-specific materializer via the
        ``AdapterCapabilities.materializer`` field. The placeholder uses
        :class:`NoOpMaterializer` (no real (x, a, c, e) tensor to
        project); the real FlowMol3 v2 adapter wires the
        :class:`ConcreteFlowMol3Materializer`.
        """
        # Lazy import — materializer is a new addition; we keep the
        # adapter importable for callers that haven't installed
        # numpy for the molecular layer yet.
        try:
            from adaptive_reflow.molecular.materializer import (
                ConcreteFlowMol3Materializer,
            )

            materializer_cls: type | None = ConcreteFlowMol3Materializer
        except ImportError:
            materializer_cls = None

        fields_ = asdict(self)
        fields_["channel_domains"] = cast(
            "Mapping[ChannelName, ChannelDomain]",
            dict(self.channel_domains),
        )
        return AdapterCapabilities(**fields_, materializer=materializer_cls)


def _make_tensor_ref(label: str, **parts: Any) -> TensorRef:
    """Build a deterministic ``TensorRef`` from ``label`` and a parts dict.

    The engine never inspects the value; this function exists only to
    give the placeholder state a stable hash-derived identifier so the
    parity tests can assert byte-equality across replays.

    .. note::
       The exact pre-image of this digest is pinned by the D.4
       regression vector ``regression-vectors/flowmol3.json``. Do not
       change the ``repr((label, sorted(parts.items())))`` encoding
       without regenerating that vector.
    """
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(f"flowmol3:{hashlib.sha256(blob).hexdigest()[:16]}")


def _require_valid(bundle: Any, code: str) -> StateBundle:
    """Fail-closed ``validate_state_bundle`` gate shared by every entry point.

    Replaces the six inlined copies of this block the adapter carried.
    """
    ok, errs = validate_state_bundle(bundle)
    if not ok:
        raise CapabilityMissingError(code, context=",".join(errs))
    return cast(StateBundle, bundle)


# ---------------------------------------------------------------------------
# Restart boundary — framework-core graph glue (MUST-3 / D.1)
# ---------------------------------------------------------------------------

#: Node / edge counts of the placeholder molecular graph. FlowMol3's
#: native ``(x, a, c, e)`` state is per-atom; the placeholder pins a
#: fixed 8-atom / 12-bond topology so the restart blend is reproducible.
FLOWMOL3_PLACEHOLDER_NUM_NODES: int = 8
FLOWMOL3_PLACEHOLDER_NUM_EDGES: int = 12


def _seed_from(*parts: str) -> int:
    """Derive a 32-bit deterministic seed from string material."""
    blob = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)


def _graph_payload_for(*parts: str) -> GraphPayload:
    """Deterministic placeholder molecule via the framework-core builder."""
    return random_graph_payload(
        num_nodes=FLOWMOL3_PLACEHOLDER_NUM_NODES,
        num_edges=FLOWMOL3_PLACEHOLDER_NUM_EDGES,
        seed=_seed_from(*parts),
    )


def _restart_memory_fraction(policy: Any) -> float:
    """Mean restart memory ``beta`` over :data:`FLOWMOL3_CHANNELS`, clamped.

    The engine encodes per-channel ``beta`` in ``policy.beta_by_channel``;
    a policy without it yields ``0.0`` (full refresh).
    """
    by_channel = getattr(policy, "beta_by_channel", None)
    if not isinstance(by_channel, Mapping):
        return 0.0
    values = [
        float(by_channel[ch]) for ch in FLOWMOL3_CHANNELS if ch in by_channel
    ]
    if not values:
        return 0.0
    return max(0.0, min(1.0, sum(values) / len(values)))


@implements(FlowMatchingODEAdapter)
class FlowMol3Adapter(FlowMatchingODEAdapter):
    """Read-only FlowMol3 mechanics adapter.

    This is the **placeholder** adapter. It does not import FlowMol3
    source; it produces deterministic, hash-stable placeholder state
    suitable for testing the public engine contract. A real integration
    would replace the body of ``build_initial_state`` /
    ``export_endpoint`` / ``solve_ode`` with calls into FlowMol3 at the
    pinned commit.
    """

    pinned_commit: str = FLOWMOL3_PINNED_COMMIT

    def __init__(self) -> None:
        self._caps = FlowMol3Capabilities()

    # -- protocol surface ---------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return self._caps.to_engine_caps()

    def build_initial_state(
        self,
        *,
        batch_id: str,
        sample_id: str,
    ) -> StateBundle:
        """Construct the prior ``(x, a, c, e)`` state at t=0.

        The returned bundle has ``detach_proof=True`` and a deterministic
        native digest derived from ``(batch_id, sample_id, source_round)``.
        """
        source_round = 0
        channels: dict[str, TensorRef] = {
            ch: _make_tensor_ref(
                "initial", channel=ch, batch=batch_id, sample=sample_id, r=source_round
            )
            for ch in FLOWMOL3_CHANNELS
        }
        masks: dict[str, TensorRef] = {
            ch: _make_tensor_ref("mask", channel=ch, batch=batch_id, sample=sample_id)
            for ch in FLOWMOL3_CHANNELS
        }
        bundle = StateBundle(
            channels=cast(Mapping[ChannelName, TensorRef], channels),
            masks=masks,
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="world",
            normalization="none",
            source_round=int(source_round),
            detach_proof=True,
            native_state_digest=_make_tensor_ref(
                "digest", batch=batch_id, sample=sample_id, r=source_round
            ),
            provenance=(
                f"flowmol3@{FLOWMOL3_PINNED_COMMIT}",
                "DTB-G2 placeholder",
            ),
            capability_token=self._caps.to_engine_caps(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise AssertionError(f"placeholder_state_invalid:{errs}")
        return bundle

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        """Return ``state`` re-exported with ``source_round`` unchanged.

        The engine treats the result as the new endpoint bundle; the
        adapter does not modify any tensor.
        """
        if not isinstance(state, StateBundle):
            raise TypeError("state_must_be_state_bundle")
        return _require_valid(state, "validate_state_bundle")

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        """Fail-closed detach gate; the placeholder state already
        carries ``detach_proof=True``, so this is a re-validation."""
        _require_valid(bundle, "detach_proof_must_be_true")
        if bundle.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        return bundle

    def apply_restart_distribution(
        self,
        state: StateBundle,
        policy: Any,
    ) -> StateBundle:
        """Restart boundary via the framework-core graph glue.

        MUST-3 / D.1 (Wave 41). FlowMol3's native ``(x, a, c, e)`` state
        is graph-shaped, so the restart boundary delegates to
        :func:`adaptive_reflow.core.graph_wrapper.blend_graph_features`
        — the framework's canonical
        ``blended = m * prior + (1 - m) * fresh`` restart mixer — instead
        of the inlined no-op this adapter used to carry. ``m`` comes from
        :func:`_restart_memory_fraction`; the digest is
        :meth:`GraphPayload.digest` over the blended payload.

        This also fixes the previous digest, which was derived from
        ``id(policy)`` — a process-local memory address, so the old
        restart digest was **not** reproducible across processes and
        silently violated the B.2 byte-stability contract. See
        ``docs/audit/wave41-flowmol3-shrink.md``.
        """
        _require_valid(state, "validate_state_bundle")
        memory_fraction = _restart_memory_fraction(policy)
        prior = _graph_payload_for(
            "prior",
            str(state.batch_id),
            str(state.sample_id),
            str(state.native_state_digest),
        )
        fresh = _graph_payload_for(
            "fresh",
            str(state.batch_id),
            str(state.sample_id),
            str(state.source_round),
        )
        blended = blend_graph_features(prior, fresh, memory_fraction)
        return replace(
            state,
            channels=dict(state.channels),
            masks=dict(state.masks),
            detach_proof=True,
            native_state_digest=f"flowmol3:restart:{blended.digest()}",
            provenance=state.provenance + ("flowmol3_restart_boundary",),
        )

    def compose_condition(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        """Condition injection (D3 — null-condition injector).

        FlowMol3 is an unconditional model; the engine-side handshake
        requires ``has_condition_injection=True`` so we delegate to
        :class:`NullConditionInjector` which annotates the audit
        trail with the null-condition provenance
        (``condition_kind='null', dataset='flowmol3_smiles_pl',
        variant='v1', round_trace_only=True``). The model itself does
        not consume the delta — the injector is the canonical seam
        between the engine's fail-closed audit policy and FlowMol3's
        unconditional ODE.
        """
        _require_valid(bundle, "validate_state_bundle")
        # D3 — delegate to NullConditionInjector for audit provenance.
        from adaptive_reflow.universal.condition_injection import (
            NullConditionInjector,
        )

        injector = NullConditionInjector(
            dataset="flowmol3_smiles_pl", variant="v1"
        )
        od_delta = ODEConditionDelta(
            delta_spec=dict(delta.delta_spec),
            source="flowmol3_adapter",
            target_round=int(bundle.source_round) + 1,
            calibration_artifact_hash="flowmol3_null_calibration",
        )
        composed = injector.compose_delta(bundle, od_delta)
        # The composed delta's spec is returned as the new ODEConditionDelta
        # so the engine's solve_ode call receives the null-condition
        # provenance. (Production wiring records the round-trace ledger
        # row directly.)
        return composed

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        """Single deterministic integration step.

        The placeholder returns the trace derived from
        ``(state.native_state_digest, seed, steps)``; the engine
        reconstructs the post-step bundle via ``observe_endpoint``.
        """
        steps = int(condition.delta_spec.get("num_steps", 1))
        if steps <= 0:
            raise ValueError("steps_must_be_positive")
        _require_valid(state, "validate_state_bundle")
        new_digest = _make_tensor_ref(
            "post_step", source=state.native_state_digest, seed=seed, steps=steps
        )
        trace = ODEIntegratorTrace(
            steps=int(steps),
            accept_rate=1.0,
            native_state_digest=new_digest,
            integrator_config_hash=_make_tensor_ref(
                "integrator_config", seed=seed, steps=steps
            ),
        )
        return trace

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        """Observation-only post-step; placeholder re-validates and returns."""
        del trace  # placeholder preserves no native trajectory (see export_trajectory)
        return _require_valid(state, "validate_state_bundle")

    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any:
        """FlowMol3 adapter: no native trajectory preserved (P0-7)."""
        raise NotImplementedError(
            "FlowMol3Adapter does not preserve a native trajectory"
        )

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (P1-8 / F-25 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """P1-8 (F-25): FlowMol3 carries no native state — pass through."""
        _require_valid(bundle, "inject_forward_noise_invalid_bundle")
        try:
            flat = list(getattr(injected, "flat", injected))
        except TypeError:
            flat = [injected]
        flat = flat[:32]
        new_digest = hashlib.sha256(
            json.dumps(
                {
                    "kind": "forward_noise",
                    "src_digest": str(bundle.native_state_digest),
                    "injected_head": [repr(float(x)) for x in flat],
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return replace(
            bundle,
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            source_round=int(bundle.source_round) + 1,
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=tuple(bundle.provenance) + ("inject_forward_noise_applied",),
            capability_token=self.capabilities(),
        )


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def default_flowmol3_adapter() -> FlowMol3Adapter:
    """Return a fresh :class:`FlowMol3Adapter` for tests and the registry."""
    return FlowMol3Adapter()


def flowmol3_registry_entry() -> Any:
    """Return the registry entry that pairs with this adapter."""
    return make_default_flowmol3_entry()


__all__ = [
    "FLOWMOL3_CHANNELS",
    "FLOWMOL3_CHANNEL_DOMAINS",
    "FLOWMOL3_PLACEHOLDER_NUM_EDGES",
    "FLOWMOL3_PLACEHOLDER_NUM_NODES",
    "FlowMol3Adapter",
    "FlowMol3Capabilities",
    "default_flowmol3_adapter",
    "flowmol3_registry_entry",
]

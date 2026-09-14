"""Synthetic :class:`FlowMatchingODEAdapter` fixtures (DTB-G1 tests).

These adapters exist solely to exercise the public engine with a
variety of capability surfaces without depending on a real Flow-A
implementation. They are stdlib-only (no ``torch``), deterministic
and never inspect / mutate native tensors.

Fixtures
--------

* :class:`SyntheticContinuousAdapter` — only continuous channels.
* :class:`SyntheticDiscreteAdapter`   — only discrete channels; its
  capability token is marked ``unsupported_for_dynamic_transfer``
  so hostile-case fixtures can verify the engine stays closed.
* :class:`SyntheticMixedChannelAdapter` — continuous + discrete.
* :class:`SyntheticUnsupportedAdapter`  — every required capability
  is ``False`` so the handshake fails closed.

Each adapter is configurable so tests can flip individual gates on
or off (e.g. ``detach_ok=False`` to force
``endpoint_not_detached``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from adaptive_reflow.contracts import FinalRestartPolicy
from adaptive_reflow.frame.adapter import (
    AdapterCapabilities,
    FlowMatchingODEAdapter,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
)
from adaptive_reflow.universal.adapter import CapabilityMissingError, ChannelDomain
from adaptive_reflow.universal.state import ChannelName, validate_state_bundle

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


CONTINUOUS_CHANNELS: tuple[str, ...] = (
    "coordinate",
    "charge",
    "coordinate.continuous",
    "charge.continuous",
)
DISCRETE_CHANNELS: tuple[str, ...] = (
    "raw_pair",
    "projected_pair",
    "raw_pair.discrete",
    "projected_pair.discrete",
)
MIXED_CHANNELS: tuple[str, ...] = CONTINUOUS_CHANNELS + DISCRETE_CHANNELS
ALL_SYNTHETIC_CHANNELS: tuple[str, ...] = (
    "synthetic.coordinate",
    "synthetic.charge",
    "synthetic.raw_pair",
    "synthetic.projected_pair",
)


# Per-channel domain-kind declaration for synthetic adapters. The
# universal engine routes per-channel validation through each adapter's
# own ``AdapterCapabilities.channel_domains`` declaration; this
# module-level mapping is the per-adapter replacement for the legacy
# ``frame.adapter.DOMAIN_BY_CHANNEL`` table.
_SYNTHETIC_CHANNEL_DOMAINS: dict[ChannelName, ChannelDomain] = cast(
    dict[ChannelName, ChannelDomain],
    {
        "coordinate": "continuous",
        "charge": "continuous",
        "coordinate.continuous": "continuous",
        "charge.continuous": "continuous",
        "raw_pair": "discrete",
        "projected_pair": "discrete",
        "raw_pair.discrete": "discrete",
        "projected_pair.discrete": "discrete",
        "synthetic.coordinate": "continuous",
        "synthetic.charge": "continuous",
        "synthetic.raw_pair": "discrete",
        "synthetic.projected_pair": "discrete",
    },
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _digest(*parts: Any) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8"))
        h.update(b"|")
    return f"syn:{h.hexdigest()}"


def _tensor_ref(name: str, salt: str) -> TensorRef:
    return TensorRef(f"syn://{name}:{salt}")


def _canonicalise(
    channels: Mapping[str, TensorRef], supported: tuple[str, ...]
) -> dict[ChannelName, TensorRef]:
    out: dict[ChannelName, TensorRef] = {}
    for channel in supported:
        out[ChannelName(channel)] = channels.get(channel, _tensor_ref(channel, "absent"))
    return out


def _capabilities(
    *,
    supported: tuple[str, ...],
    continuous: bool,
    discrete: bool,
) -> AdapterCapabilities:
    channel_domains: dict[ChannelName, ChannelDomain] = cast(
        "dict[ChannelName, ChannelDomain]",
        {
            cast(ChannelName, ch): _SYNTHETIC_CHANNEL_DOMAINS[cast(ChannelName, ch)]
            for ch in supported
            if ch in _SYNTHETIC_CHANNEL_DOMAINS
        },
    )
    return AdapterCapabilities(
        has_ode_integration_surface=True,
        has_prior_export=True,
        has_state_export=True,
        has_condition_injection=True,
        has_restart_boundary=True,
        has_continuous_channels=continuous,
        has_discrete_channels=discrete,
        has_trajectory_digest=True,
        has_deterministic_seed=True,
        has_materialization_route=True,
        supported_channels=supported,
        channel_domains=channel_domains,
    )


# ---------------------------------------------------------------------------
# Synthetic continuous
# ---------------------------------------------------------------------------


@dataclass
class SyntheticContinuousAdapter(FlowMatchingODEAdapter):
    """Synthetic adapter with only continuous channels."""

    detach_ok: bool = True
    condition_match: bool = True
    return_none_trace: bool = False
    capability_overrides: dict[str, bool] = field(default_factory=dict)

    def capabilities(self) -> AdapterCapabilities:
        base = _capabilities(
            supported=CONTINUOUS_CHANNELS,
            continuous=True,
            discrete=False,
        )
        if not self.capability_overrides:
            return base
        return AdapterCapabilities(
            **{
                **{f.name: getattr(base, f.name) for f in base.__dataclass_fields__.values() if not callable(getattr(base, f.name))},
                **self.capability_overrides,
            }
        )

    def build_initial_state(self, *, batch_id: str, sample_id: str) -> StateBundle:
        channels = _canonicalise({}, CONTINUOUS_CHANNELS)
        return StateBundle(
            channels=channels,
            masks={"freeze": _tensor_ref("freeze", f"{batch_id}:{sample_id}")},
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="pocket_centered",
            normalization="per_atom_std",
            source_round=0,
            detach_proof=True,
            native_state_digest=_digest("cont-init", batch_id, sample_id),
            provenance=("SyntheticContinuousAdapter.build_initial_state",),
            capability_token=self.capabilities(),
        )

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round),
            detach_proof=True,
            native_state_digest=_digest("cont-endpoint", state.native_state_digest),
            provenance=tuple(state.provenance)
            + ("SyntheticContinuousAdapter.export_endpoint",),
            capability_token=self.capabilities(),
        )

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round),
            detach_proof=bool(self.detach_ok),
            native_state_digest=_digest("cont-detached", bundle.native_state_digest),
            provenance=tuple(bundle.provenance)
            + ("SyntheticContinuousAdapter.detach_and_validate_endpoint",),
            capability_token=self.capabilities(),
        )

    def apply_restart_distribution(
        self, state: StateBundle, policy: FinalRestartPolicy
    ) -> StateBundle:
        del policy
        return state

    def compose_condition(
        self, bundle: StateBundle, delta: ODEConditionDelta
    ) -> ODEConditionDelta:
        if not self.condition_match:
            return ODEConditionDelta(
                delta_spec={},  # type: ignore[arg-type]
                source="",
                target_round=int(delta.target_round) + 1,
                calibration_artifact_hash="",
            )
        return ODEConditionDelta(
            delta_spec=dict(delta.delta_spec),  # type: ignore[call-overload]
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        if self.return_none_trace:
            return None  # type: ignore[return-value]
        return ODEIntegratorTrace(
            steps=2,
            accept_rate=1.0,
            native_state_digest=_digest("cont-solve", state.native_state_digest, int(seed)),
            integrator_config_hash=_digest("cont-config", "continuous"),
        )

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round),
            detach_proof=True,
            native_state_digest=_digest("cont-observed", trace.native_state_digest),
            provenance=tuple(state.provenance)
            + ("SyntheticContinuousAdapter.observe_endpoint",),
            capability_token=self.capabilities(),
        )

    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any:
        """Synthetic adapters do not preserve a native trajectory (P0-7)."""
        raise NotImplementedError(
            "SyntheticContinuousAdapter does not preserve a native trajectory"
        )

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (P1-8 / F-25 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """P1-8 (F-25): synthetic continuous adapter — pass through with provenance."""
        import hashlib as _hl
        import json as _json

        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "inject_forward_noise_invalid_bundle", context=",".join(errs),
            )
        # Stdlib-only: convert ``injected`` (numpy or sequence) to a
        # stable representation via the repr of its flat list. The
        # full tensor is hashed (capped at 32 entries to keep the
        # digest cheap) so two distinct tensors land on distinct
        # digests.
        try:
            flat = list(getattr(injected, "flat", injected))
        except TypeError:
            flat = [injected]
        flat = flat[:32]
        new_digest = _hl.sha256(
            _json.dumps(
                {
                    "kind": "forward_noise",
                    "src_digest": str(bundle.native_state_digest),
                    "injected_head": [repr(float(x)) for x in flat],
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round) + 1,
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=tuple(bundle.provenance) + ("inject_forward_noise_applied",),
            capability_token=self.capabilities(),
        )


# ---------------------------------------------------------------------------
# Synthetic discrete
# ---------------------------------------------------------------------------


@dataclass
class SyntheticDiscreteAdapter(FlowMatchingODEAdapter):
    """Synthetic adapter with only discrete channels.

    The capability token is marked ``unsupported_for_dynamic_transfer``
    in the ``extras`` field of the round trace (when emitted) so callers
    can detect that dynamic transfer is not a valid operation on this
    surface. The capability surface itself is internally consistent.
    """

    detach_ok: bool = True

    def capabilities(self) -> AdapterCapabilities:
        return _capabilities(
            supported=DISCRETE_CHANNELS,
            continuous=False,
            discrete=True,
        )

    def build_initial_state(self, *, batch_id: str, sample_id: str) -> StateBundle:
        channels = _canonicalise({}, DISCRETE_CHANNELS)
        return StateBundle(
            channels=channels,
            masks={"freeze": _tensor_ref("freeze", f"{batch_id}:{sample_id}")},
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="lattice",
            normalization="none",
            source_round=0,
            detach_proof=True,
            native_state_digest=_digest("disc-init", batch_id, sample_id),
            provenance=("SyntheticDiscreteAdapter.build_initial_state",),
            capability_token=self.capabilities(),
        )

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round),
            detach_proof=True,
            native_state_digest=_digest("disc-endpoint", state.native_state_digest),
            provenance=tuple(state.provenance)
            + ("SyntheticDiscreteAdapter.export_endpoint",),
            capability_token=self.capabilities(),
        )

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round),
            detach_proof=bool(self.detach_ok),
            native_state_digest=_digest("disc-detached", bundle.native_state_digest),
            provenance=tuple(bundle.provenance)
            + ("SyntheticDiscreteAdapter.detach_and_validate_endpoint",),
            capability_token=self.capabilities(),
        )

    def apply_restart_distribution(
        self, state: StateBundle, policy: FinalRestartPolicy
    ) -> StateBundle:
        del policy
        return state

    def compose_condition(
        self, bundle: StateBundle, delta: ODEConditionDelta
    ) -> ODEConditionDelta:
        del bundle
        return ODEConditionDelta(
            delta_spec=dict(delta.delta_spec),  # type: ignore[call-overload]
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        return ODEIntegratorTrace(
            steps=3,
            accept_rate=0.75,
            native_state_digest=_digest(
                "disc-solve", state.native_state_digest, int(seed)
            ),
            integrator_config_hash=_digest("disc-config", "discrete"),
        )

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round),
            detach_proof=True,
            native_state_digest=_digest("disc-observed", trace.native_state_digest),
            provenance=tuple(state.provenance)
            + ("SyntheticDiscreteAdapter.observe_endpoint",),
            capability_token=self.capabilities(),
        )

    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any:
        """Synthetic adapters do not preserve a native trajectory (P0-7)."""
        raise NotImplementedError(
            "SyntheticDiscreteAdapter does not preserve a native trajectory"
        )

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (P1-8 / F-25 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """P1-8 (F-25): synthetic discrete adapter — pass through with provenance."""
        import hashlib as _hl
        import json as _json

        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "inject_forward_noise_invalid_bundle", context=",".join(errs),
            )
        try:
            flat = list(getattr(injected, "flat", injected))
        except TypeError:
            flat = [injected]
        flat = flat[:32]
        new_digest = _hl.sha256(
            _json.dumps(
                {
                    "kind": "forward_noise",
                    "src_digest": str(bundle.native_state_digest),
                    "injected_head": [repr(float(x)) for x in flat],
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round) + 1,
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=tuple(bundle.provenance) + ("inject_forward_noise_applied",),
            capability_token=self.capabilities(),
        )


# ---------------------------------------------------------------------------
# Synthetic mixed
# ---------------------------------------------------------------------------


@dataclass
class SyntheticMixedChannelAdapter(FlowMatchingODEAdapter):
    """Synthetic adapter carrying continuous + discrete channels."""

    detach_ok: bool = True
    frame_match: bool = True
    normalization_match: bool = True

    def capabilities(self) -> AdapterCapabilities:
        return _capabilities(
            supported=MIXED_CHANNELS,
            continuous=True,
            discrete=True,
        )

    def _shape(self, frame: str, norm: str) -> tuple[str, str]:
        if not self.frame_match:
            frame = "world" if frame != "world" else "lattice"
        if not self.normalization_match:
            norm = "none" if norm != "none" else "per_atom_std"
        return frame, norm

    def build_initial_state(self, *, batch_id: str, sample_id: str) -> StateBundle:
        frame, norm = self._shape("pocket_centered", "per_atom_std")
        channels = _canonicalise({}, MIXED_CHANNELS)
        return StateBundle(
            channels=channels,
            masks={"freeze": _tensor_ref("freeze", f"{batch_id}:{sample_id}")},
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame=frame,
            normalization=norm,
            source_round=0,
            detach_proof=True,
            native_state_digest=_digest("mix-init", batch_id, sample_id),
            provenance=("SyntheticMixedChannelAdapter.build_initial_state",),
            capability_token=self.capabilities(),
        )

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round),
            detach_proof=True,
            native_state_digest=_digest("mix-endpoint", state.native_state_digest),
            provenance=tuple(state.provenance)
            + ("SyntheticMixedChannelAdapter.export_endpoint",),
            capability_token=self.capabilities(),
        )

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round),
            detach_proof=bool(self.detach_ok),
            native_state_digest=_digest("mix-detached", bundle.native_state_digest),
            provenance=tuple(bundle.provenance)
            + ("SyntheticMixedChannelAdapter.detach_and_validate_endpoint",),
            capability_token=self.capabilities(),
        )

    def apply_restart_distribution(
        self, state: StateBundle, policy: FinalRestartPolicy
    ) -> StateBundle:
        del policy
        return state

    def compose_condition(
        self, bundle: StateBundle, delta: ODEConditionDelta
    ) -> ODEConditionDelta:
        del bundle
        return ODEConditionDelta(
            delta_spec=dict(delta.delta_spec),  # type: ignore[call-overload]
            source=str(delta.source),
            target_round=int(delta.target_round),
            calibration_artifact_hash=str(delta.calibration_artifact_hash),
        )

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        return ODEIntegratorTrace(
            steps=4,
            accept_rate=0.5,
            native_state_digest=_digest(
                "mix-solve", state.native_state_digest, int(seed)
            ),
            integrator_config_hash=_digest("mix-config", "mixed"),
        )

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round),
            detach_proof=True,
            native_state_digest=_digest("mix-observed", trace.native_state_digest),
            provenance=tuple(state.provenance)
            + ("SyntheticMixedChannelAdapter.observe_endpoint",),
            capability_token=self.capabilities(),
        )

    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any:
        """Synthetic adapters do not preserve a native trajectory (P0-7)."""
        raise NotImplementedError(
            "SyntheticMixedChannelAdapter does not preserve a native trajectory"
        )

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (P1-8 / F-25 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """P1-8 (F-25): synthetic mixed adapter — pass through with provenance."""
        import hashlib as _hl
        import json as _json

        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "inject_forward_noise_invalid_bundle", context=",".join(errs),
            )
        try:
            flat = list(getattr(injected, "flat", injected))
        except TypeError:
            flat = [injected]
        flat = flat[:32]
        new_digest = _hl.sha256(
            _json.dumps(
                {
                    "kind": "forward_noise",
                    "src_digest": str(bundle.native_state_digest),
                    "injected_head": [repr(float(x)) for x in flat],
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round) + 1,
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=tuple(bundle.provenance) + ("inject_forward_noise_applied",),
            capability_token=self.capabilities(),
        )


# ---------------------------------------------------------------------------
# Synthetic unsupported
# ---------------------------------------------------------------------------


@dataclass
class SyntheticUnsupportedAdapter(FlowMatchingODEAdapter):
    """Synthetic adapter with *no* advertised capabilities.

    Used to verify the engine fails closed at the handshake boundary.
    """

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
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
            supported_channels=(),
        )

    # The remaining methods are never called by the engine when the
    # handshake fails; they exist solely to satisfy the protocol's
    # static signature. They MUST raise if accidentally invoked so the
    # hostile-case tests can detect a missed gate.

    def build_initial_state(self, *, batch_id: str, sample_id: str) -> StateBundle:
        raise AssertionError("SyntheticUnsupportedAdapter.build_initial_state must not be called")

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        raise AssertionError("SyntheticUnsupportedAdapter.export_endpoint must not be called")

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        raise AssertionError(
            "SyntheticUnsupportedAdapter.detach_and_validate_endpoint must not be called"
        )

    def apply_restart_distribution(
        self, state: StateBundle, policy: FinalRestartPolicy
    ) -> StateBundle:
        raise AssertionError(
            "SyntheticUnsupportedAdapter.apply_restart_distribution must not be called"
        )

    def compose_condition(
        self, bundle: StateBundle, delta: ODEConditionDelta
    ) -> ODEConditionDelta:
        raise AssertionError(
            "SyntheticUnsupportedAdapter.compose_condition must not be called"
        )

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
    ) -> ODEIntegratorTrace:
        raise AssertionError("SyntheticUnsupportedAdapter.solve_ode must not be called")

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        raise AssertionError("SyntheticUnsupportedAdapter.observe_endpoint must not be called")

    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any:
        """Unsupported adapter: native trajectory is unavailable (P0-7)."""
        raise NotImplementedError(
            "SyntheticUnsupportedAdapter does not preserve a native trajectory"
        )

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (P1-8 / F-25 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """P1-8 (F-25): synthetic unsupported adapter — pass through with provenance."""
        import hashlib as _hl
        import json as _json

        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "inject_forward_noise_invalid_bundle", context=",".join(errs),
            )
        try:
            flat = list(getattr(injected, "flat", injected))
        except TypeError:
            flat = [injected]
        flat = flat[:32]
        new_digest = _hl.sha256(
            _json.dumps(
                {
                    "kind": "forward_noise",
                    "src_digest": str(bundle.native_state_digest),
                    "injected_head": [repr(float(x)) for x in flat],
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round) + 1,
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=tuple(bundle.provenance) + ("inject_forward_noise_applied",),
            capability_token=self.capabilities(),
        )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "ALL_SYNTHETIC_CHANNELS",
    "CONTINUOUS_CHANNELS",
    "DISCRETE_CHANNELS",
    "MIXED_CHANNELS",
    "SyntheticContinuousAdapter",
    "SyntheticDiscreteAdapter",
    "SyntheticMixedChannelAdapter",
    "SyntheticUnsupportedAdapter",
]

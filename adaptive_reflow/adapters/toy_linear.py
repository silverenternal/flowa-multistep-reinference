"""Toy linear adapter (DTB-G1 worked example).

The smallest possible FlowMatchingODEAdapter implementation: one
continuous channel, a deterministic linear ODE step, no restart, no
condition injection. Useful as a sanity-check for the universal engine
and as a worked example for new adapter authors (see
``docs/ADAPTER_INTERFACE_SPEC.md`` §13).

Stdlib-only. No torch. No external dependencies.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from adaptive_reflow.contracts.authority import FinalRestartPolicy as RestartPolicy
from adaptive_reflow.universal import (
    AdapterCapabilities,
    ArtifactHash,
    CapabilityMissingError,
    ChannelDomain,
    FlowMatchingODEAdapter,
    NoOpMixer,
    RestartMixer,
)
from adaptive_reflow.universal.state import (
    
    ChannelName,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
)

from adaptive_reflow.adapters._adapter_common import (
    make_ref,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


SUPPORTED_CHANNELS: tuple[ChannelName, ...] = (ChannelName("x"),)
CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = {ChannelName("x"): "continuous"}
NATIVE_CONFIG_HASH: ArtifactHash = ArtifactHash("toy:cfg:v1")
NATIVE_CONFIG_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ref(label: str, **parts: Any) -> TensorRef:
    """Build a deterministic hash-stable TensorRef from ``label`` + parts."""
    return make_ref("toy", label, **parts)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class ToyLinearAdapter(FlowMatchingODEAdapter):
    """Minimal one-channel linear-Flow-Matching adapter.

    The adapter treats the single channel ``x`` as a scalar trajectory
    that increments by a deterministic function of the seed and step
    count. It is NOT a useful model — it exists so the engine has
    something to drive in tests, and so new adapter authors have a
    full worked example to copy.

    Implements the eight-method Protocol of
    :class:`adaptive_reflow.universal.FlowMatchingODEAdapter`.
    """

    pinned_seed_drift: float = 0.1
    """How much the channel increments per ``solve_ode`` step."""

    def __init__(self, *, drift: float = pinned_seed_drift) -> None:
        self._drift = float(drift)

    # ------------------------------------------------------------------
    # 1. Capability handshake (always required)
    # ------------------------------------------------------------------

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=False,
            has_restart_boundary=False,
            has_continuous_channels=True,
            has_discrete_channels=False,
            has_trajectory_digest=False,
            has_deterministic_seed=True,
            has_materialization_route=False,
            supported_channels=SUPPORTED_CHANNELS,
            channel_domains=CHANNEL_DOMAINS,
            required_mixer=NoOpMixer,
            exposed_envelope_criteria=(),
            exposed_evaluators=(),
            native_config_hash=NATIVE_CONFIG_HASH,
            native_config_version=NATIVE_CONFIG_VERSION,
        )

    # ------------------------------------------------------------------
    # 2. build_initial_state (required by has_prior_export=True)
    # ------------------------------------------------------------------

    def build_initial_state(
        self,
        *,
        batch_id: str,
        sample_id: str,
    ) -> StateBundle:
        source_round = 0
        bundle = StateBundle(
            channels={
                ChannelName("x"): _make_ref(
                    "initial", batch=batch_id, sample=sample_id, r=source_round
                ),
            },
            masks={},
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="world",
            normalization="none",
            source_round=int(source_round),
            detach_proof=True,
            native_state_digest=_make_ref(
                "digest", batch=batch_id, sample=sample_id, r=source_round
            ),
            provenance=("toy_linear@v1",),
            capability_token=self.capabilities(),
        )
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise AssertionError(f"placeholder_state_invalid:{errs}")
        return bundle

    # ------------------------------------------------------------------
    # 3. export_endpoint (required by has_state_export=True)
    # ------------------------------------------------------------------

    def export_endpoint(self, state: StateBundle) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        return state

    # ------------------------------------------------------------------
    # 4. detach_and_validate_endpoint (always required)
    # ------------------------------------------------------------------

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        if bundle.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        ok, errs = validate_state_bundle(bundle)
        if not ok:
            raise CapabilityMissingError(
                "detach_proof_must_be_true", context=",".join(errs)
            )
        return bundle

    # ------------------------------------------------------------------
    # 5. apply_restart_distribution (required by has_restart_boundary=False → not used)
    # ------------------------------------------------------------------

    def apply_restart_distribution(
        self,
        state: StateBundle,
        policy: RestartPolicy,
    ) -> StateBundle:
        # ToyLinear declares has_restart_boundary=False. If the engine
        # ever invokes this method, fail closed.
        if not self.capabilities().has_restart_boundary:
            raise CapabilityMissingError(
                "has_restart_boundary",
                context="ToyLinearAdapter does not support restart distribution",
            )
        return state

    # ------------------------------------------------------------------
    # 6. compose_condition (required by has_condition_injection=False → not used)
    # ------------------------------------------------------------------

    def compose_condition(
        self,
        bundle: StateBundle,
        delta: ODEConditionDelta,
    ) -> ODEConditionDelta:
        if not self.capabilities().has_condition_injection:
            raise CapabilityMissingError(
                "has_condition_injection",
                context="ToyLinearAdapter is unconditional",
            )
        return delta

    # ------------------------------------------------------------------
    # 7. solve_ode (required by has_ode_integration_surface=True)
    # ------------------------------------------------------------------

    def solve_ode(
        self,
        state: StateBundle,
        condition: ODEConditionDelta,
        *,
        seed: int,
        steps: int = 1,
    ) -> ODEIntegratorTrace:
        if steps <= 0:
            raise ValueError("steps_must_be_positive")
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        # Deterministic: same (state.native_state_digest, seed, steps) → same trace.
        next_digest = _make_ref(
            "post_step",
            source=state.native_state_digest,
            seed=seed,
            steps=steps,
        )
        return ODEIntegratorTrace(
            steps=int(steps),
            accept_rate=1.0,
            native_state_digest=next_digest,
            integrator_config_hash=_make_ref(
                "integrator_config", seed=seed, steps=steps
            ),
        )

    # ------------------------------------------------------------------
    # 8. observe_endpoint (always required)
    # ------------------------------------------------------------------

    def observe_endpoint(
        self,
        trace: ODEIntegratorTrace,
        state: StateBundle,
    ) -> StateBundle:
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        return state

    # ------------------------------------------------------------------
    # 9. export_trajectory (P0-7 — public trajectory export)
    # ------------------------------------------------------------------

    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any:
        """Linear adapter: no native trajectory preserved (P0-7)."""
        raise NotImplementedError(
            "ToyLinearAdapter does not preserve a native trajectory"
        )

    # ------------------------------------------------------------------
    # 10. inject_forward_noise (P1-8 / F-25 close)
    # ------------------------------------------------------------------

    def inject_forward_noise(
        self,
        bundle: StateBundle,
        injected: Any,
    ) -> StateBundle:
        """P1-8 (F-25): ToyLinear carries no native state — pass through."""
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
# Factory
# ---------------------------------------------------------------------------


def default_toy_linear_adapter() -> ToyLinearAdapter:
    """Return a fresh ToyLinearAdapter for tests and the registry."""
    return ToyLinearAdapter()


__all__ = [
    "ToyLinearAdapter",
    "default_toy_linear_adapter",
    "SUPPORTED_CHANNELS",
    "CHANNEL_DOMAINS",
    "NATIVE_CONFIG_HASH",
    "NATIVE_CONFIG_VERSION",
]

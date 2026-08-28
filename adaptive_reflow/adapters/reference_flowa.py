"""Reference Flow-A adapter for the DTB-G1 public engine.

The :class:`ReferenceFlowAAdapter` is the canonical adapter the engine
ships against. It implements :class:`FlowMatchingODEAdapter` using only
abstract placeholder endpoints — it does NOT load any torch weights,
edit any checkpoint, mutate any training loss, change cross-attention
ownership, or alter multirate clock semantics. The intent is to provide
a deterministic, stdlib-only reference that downstream Flow-A
implementations can either wrap directly or replace wholesale.

Parity contract
---------------

When all ``beta_by_channel`` values in the supplied
:class:`FinalRestartPolicy` are zero, the round output is bit-identical
to the canonical single-round Flow-A path:

* The endpoint digest is a deterministic function of ``(batch_id,
  sample_id, seed, condition_delta)`` — no beta blending touches it.
* The integrator trace carries ``steps = 1`` and ``accept_rate = 1.0``.
* The round trace's ``operation_steps`` match
  :data:`flow_matching_engine.DEFAULT_OPERATION_STEPS` exactly.

When the feature flag (``flow_matching_engine_enabled``) is ``False``
the engine emits a disabled-feature round trace and never calls this
adapter at all; this is what guarantees "feature disabled => no
behavior change".
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from adaptive_reflow.contracts import FinalRestartPolicy
from adaptive_reflow.frame.adapter import (
    AdapterCapabilities,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
)
from adaptive_reflow.universal.adapter import ChannelDomain
from adaptive_reflow.universal.state import ChannelName

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


# Canonical supported channel set: Flow-A carries the four typed channels
# from CONTRACTS.md §1 (continuous + discrete).
REFERENCE_FLOWA_CHANNELS: tuple[str, ...] = (
    "coordinate",
    "charge",
    "raw_pair",
    "projected_pair",
)


# Per-channel domain-kind declaration for the Flow-A reference adapter.
# This is the per-adapter replacement for the legacy
# ``frame.adapter.DOMAIN_BY_CHANNEL`` molecule-only table; the universal
# engine routes per-channel validation through each adapter's own
# ``AdapterCapabilities.channel_domains`` declaration.
REFERENCE_FLOWA_CHANNEL_DOMAINS: Mapping[ChannelName, ChannelDomain] = cast(
    Mapping[ChannelName, ChannelDomain],
    {
        "coordinate": "continuous",
        "charge": "continuous",
        "raw_pair": "discrete",
        "projected_pair": "discrete",
    },
)

# Deterministic placeholder digest prefix used by every endpoint
# produced by this adapter. The trailing characters are derived from
# the input so two distinct inputs always produce two distinct
# digests, but the prefix marks the digests as "Flow-A placeholder
# origin" so downstream tooling can recognise them.
_PLACEHOLDER_DIGEST_PREFIX: str = "flowa-placeholder"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _placeholder_digest(*parts: Any) -> str:
    """Return a deterministic sha256 hex digest prefixed by the
    Flow-A placeholder marker."""
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8"))
        h.update(b"|")
    return f"{_PLACEHOLDER_DIGEST_PREFIX}:{h.hexdigest()}"


def _placeholder_tensor_ref(name: str, salt: str) -> TensorRef:
    """Return a deterministic :class:`TensorRef` for the named placeholder."""
    return TensorRef(f"ref://{name}:{salt}")


def _canonicalise_channels(
    channels: Mapping[str, TensorRef],
) -> dict[ChannelName, TensorRef]:
    """Return a stable mapping of channels -> placeholder tensor refs.

    The mapping is keyed by every entry in
    :data:`REFERENCE_FLOWA_CHANNELS` (Flow-A always publishes the full
    four-channel set). Missing channels are filled with a deterministic
    placeholder so the bundle is structurally complete.
    """
    out: dict[ChannelName, TensorRef] = {}
    for channel in REFERENCE_FLOWA_CHANNELS:
        out[ChannelName(channel)] = channels.get(
            channel, _placeholder_tensor_ref(channel, "absent")
        )
    return out


# ---------------------------------------------------------------------------
# Reference adapter
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferenceFlowAAdapter:
    """Reference Flow-A adapter implementing :class:`FlowMatchingODEAdapter`.

    All methods are pure: given identical inputs they produce identical
    outputs. They NEVER touch native tensors; every "endpoint" is a
    placeholder whose only purpose is to give the engine deterministic
    bytes to write into the round trace. The engine is the only consumer
    of these placeholders and never inspects their contents.
    """

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            has_ode_integration_surface=True,
            has_prior_export=True,
            has_state_export=True,
            has_condition_injection=True,
            has_restart_boundary=True,
            has_continuous_channels=True,
            has_discrete_channels=True,
            has_trajectory_digest=True,
            has_deterministic_seed=True,
            has_materialization_route=True,
            supported_channels=REFERENCE_FLOWA_CHANNELS,
            channel_domains=REFERENCE_FLOWA_CHANNEL_DOMAINS,
        )

    def build_initial_state(self, *, batch_id: str, sample_id: str) -> StateBundle:
        channels = _canonicalise_channels({})
        return StateBundle(
            channels=channels,
            masks={
                "freeze": _placeholder_tensor_ref("freeze", f"{batch_id}:{sample_id}"),
            },
            batch_id=str(batch_id),
            sample_id=str(sample_id),
            reference_frame="pocket_centered",
            normalization="per_atom_std",
            source_round=0,
            detach_proof=True,
            native_state_digest=_placeholder_digest("initial", batch_id, sample_id),
            provenance=("ReferenceFlowAAdapter.build_initial_state",),
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
            native_state_digest=_placeholder_digest(
                "endpoint", state.native_state_digest
            ),
            provenance=tuple(state.provenance) + ("ReferenceFlowAAdapter.export_endpoint",),
            capability_token=self.capabilities(),
        )

    def detach_and_validate_endpoint(self, bundle: StateBundle) -> StateBundle:
        # Reference Flow-A always detaches; the placeholder endpoint is
        # already detached by construction. We never mutate the input;
        # we just re-emit it with the engine's canonical ``detach_proof``
        # marker.
        return StateBundle(
            channels=dict(bundle.channels),
            masks=dict(bundle.masks),
            batch_id=str(bundle.batch_id),
            sample_id=str(bundle.sample_id),
            reference_frame=str(bundle.reference_frame),
            normalization=str(bundle.normalization),
            source_round=int(bundle.source_round),
            detach_proof=True,
            native_state_digest=_placeholder_digest(
                "detached", bundle.native_state_digest
            ),
            provenance=tuple(bundle.provenance)
            + ("ReferenceFlowAAdapter.detach_and_validate_endpoint",),
            capability_token=self.capability_token_for(bundle),
        )

    def apply_restart_distribution(
        self, state: StateBundle, policy: FinalRestartPolicy
    ) -> StateBundle:
        # Beta=0 parity: when every beta is zero, the state is returned
        # bit-identical (same channels, masks, digest). When any beta is
        # positive the placeholder endpoint's digest is bumped to reflect
        # the blending so round traces can still distinguish them.
        any_positive_beta = any(
            float(value) > 0.0 for value in policy.beta_by_channel.values()
        )
        if not any_positive_beta:
            return state
        return StateBundle(
            channels={
                k: _placeholder_tensor_ref(k, f"beta-blend:{policy.policy_hash}")
                for k in state.channels
            },
            masks=dict(state.masks),
            batch_id=str(state.batch_id),
            sample_id=str(state.sample_id),
            reference_frame=str(state.reference_frame),
            normalization=str(state.normalization),
            source_round=int(state.source_round),
            detach_proof=True,
            native_state_digest=_placeholder_digest(
                "restart-blend", state.native_state_digest, policy.policy_hash
            ),
            provenance=tuple(state.provenance)
            + ("ReferenceFlowAAdapter.apply_restart_distribution",),
            capability_token=self.capability_token_for(state),
        )

    def compose_condition(
        self, bundle: StateBundle, delta: ODEConditionDelta
    ) -> ODEConditionDelta:
        # Flow-A passthrough: the engine supplies the condition delta,
        # Flow-A does not edit it. We return a fresh instance so the
        # engine can compare structural equality without aliasing.
        return ODEConditionDelta(
            delta_spec=dict(delta.delta_spec),
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
        # Single-step placeholder integration: beta=0 parity means the
        # trajectory is "one step, full acceptance" — that matches the
        # canonical single-round Flow-A path.
        return ODEIntegratorTrace(
            steps=1,
            accept_rate=1.0,
            native_state_digest=_placeholder_digest(
                "solve",
                state.native_state_digest,
                condition.calibration_artifact_hash,
                int(seed),
            ),
            integrator_config_hash=_placeholder_digest(
                "config", "reference_flowa_single_round"
            ),
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
            native_state_digest=_placeholder_digest(
                "observed", trace.native_state_digest, state.native_state_digest
            ),
            provenance=tuple(state.provenance) + ("ReferenceFlowAAdapter.observe_endpoint",),
            capability_token=self.capability_token_for(state),
        )

    def export_trajectory(self, trace: ODEIntegratorTrace) -> Any:
        """Reference adapter: no native trajectory preserved (P0-7).

        The reference adapter is a stdlib-only placeholder that does
        not store a real trajectory. The runner catches
        :class:`NotImplementedError` here and records the failure in
        the round's metric dict under ``endpoint_export_failed``; the
        endpoint row is left as ``NaN`` so the caller can detect
        "endpoint not captured" via ``np.isnan``.
        """
        raise NotImplementedError(
            "ReferenceFlowAAdapter does not preserve a native trajectory"
        )

    # -- helpers -----------------------------------------------------------

    def capability_token_for(self, state: StateBundle) -> AdapterCapabilities:
        """Return the adapter's capability token; state is unused.

        Provided so :class:`StateBundle` instances emitted by the adapter
        carry the same capability surface the engine hands out at
        handshake time. The state is unused because the adapter's
        capabilities are static.
        """
        del state  # explicit; capabilities are static
        return self.capabilities()


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "REFERENCE_FLOWA_CHANNEL_DOMAINS",
    "REFERENCE_FLOWA_CHANNELS",
    "ReferenceFlowAAdapter",
]

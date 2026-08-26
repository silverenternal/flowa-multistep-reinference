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
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from adaptive_reflow.frame.adapter import (
    AdapterCapabilities,
    CapabilityMissingError,
    ODEIntegratorTrace,
    StateBundle,
    TensorRef,
    validate_state_bundle,
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
# protocol (DTB-G1) can route them through ``DOMAIN_BY_CHANNEL``:
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


@dataclass(frozen=True)
class FlowMol3Capabilities:
    """Static capability token for the FlowMol3 adapter.

    Continuous + discrete channels; deterministic seed supported; no
    trajectory digest in the placeholder. The fields below mirror
    :class:`flow_matching_adapter.AdapterCapabilities` exactly; the
    engine reads them via duck-typing.
    """

    has_ode_integration_surface: bool = True
    has_prior_export: bool = True
    has_state_export: bool = True
    has_condition_injection: bool = False  # FlowMol3 is unconditional.
    has_restart_boundary: bool = True
    has_continuous_channels: bool = True
    has_discrete_channels: bool = True
    has_trajectory_digest: bool = False
    has_deterministic_seed: bool = True
    has_materialization_route: bool = False  # No pocket materialization.
    supported_channels: tuple[str, ...] = FLOWMOL3_CHANNELS

    def to_engine_caps(self) -> AdapterCapabilities:
        """Project this token into the engine's ``AdapterCapabilities``."""
        return AdapterCapabilities(
            has_ode_integration_surface=self.has_ode_integration_surface,
            has_prior_export=self.has_prior_export,
            has_state_export=self.has_state_export,
            has_condition_injection=self.has_condition_injection,
            has_restart_boundary=self.has_restart_boundary,
            has_continuous_channels=self.has_continuous_channels,
            has_discrete_channels=self.has_discrete_channels,
            has_trajectory_digest=self.has_trajectory_digest,
            has_deterministic_seed=self.has_deterministic_seed,
            has_materialization_route=self.has_materialization_route,
            supported_channels=self.supported_channels,
        )


def _make_tensor_ref(label: str, **parts: Any) -> TensorRef:
    """Build a deterministic ``TensorRef`` from ``label`` and a parts dict.

    The engine never inspects the value; this function exists only to
    give the placeholder state a stable hash-derived identifier so the
    parity tests can assert byte-equality across replays.
    """
    blob = repr((label, sorted(parts.items()))).encode("utf-8")
    return TensorRef(f"flowmol3:{hashlib.sha256(blob).hexdigest()[:16]}")


class FlowMol3Adapter:
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
        batch_id: str,
        sample_id: str,
        *,
        source_round: int = 0,
    ) -> StateBundle:
        """Construct the prior ``(x, a, c, e)`` state at t=0.

        The returned bundle has ``detach_proof=True`` and a deterministic
        native digest derived from ``(batch_id, sample_id, source_round)``.
        """
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
            channels=channels,
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
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        return state

    def detach_and_validate_endpoint(self, state: StateBundle) -> StateBundle:
        """Fail-closed detach gate; the placeholder state already
        carries ``detach_proof=True``, so this is a re-validation."""
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "detach_proof_must_be_true", context=",".join(errs)
            )
        if state.detach_proof is not True:
            raise CapabilityMissingError("detach_proof_must_be_true")
        return state

    def apply_restart_distribution(
        self,
        state: StateBundle,
        policy: Any,
    ) -> StateBundle:
        """Return ``state`` unchanged in the placeholder.

        A real FlowMol3 adapter would invoke its native
        ``integrate``/``step`` boundary here. The placeholder only
        verifies that the input bundle is well-formed.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        # beta is encoded in policy.beta_by_channel by the engine; the
        # placeholder doesn't interpret it. We re-export the state with
        # an updated native_state_digest so parity tests can see a round
        # boundary without an actual numeric integration.
        new_digest = _make_tensor_ref(
            "post_restart", source=state.native_state_digest, policy_id=id(policy)
        )
        return StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=state.batch_id,
            sample_id=state.sample_id,
            reference_frame=state.reference_frame,
            normalization=state.normalization,
            source_round=state.source_round,
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=state.provenance + ("flowmol3_restart_boundary",),
            capability_token=state.capability_token,
        )

    def compose_condition(
        self,
        state: StateBundle,
        delta: Mapping[str, Any],
    ) -> StateBundle:
        """Condition injection.

        FlowMol3 is unconditional (``has_condition_injection=False``);
        any non-empty delta is rejected. The placeholder returns the
        state with the condition attached as provenance so the trace
        round-trip remains deterministic.
        """
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        if delta:
            raise CapabilityMissingError(
                "has_condition_injection", context="flowmol3_is_unconditional"
            )
        return state

    def solve_ode(
        self,
        state: StateBundle,
        seed: int,
        *,
        steps: int = 1,
    ) -> tuple[StateBundle, ODEIntegratorTrace]:
        """Single deterministic integration step.

        The placeholder returns the input state unchanged plus an
        :class:`ODEIntegratorTrace` whose digest is hash-derived from
        ``(state.native_state_digest, seed, steps)``.
        """
        if steps <= 0:
            raise ValueError("steps_must_be_positive")
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        new_digest = _make_tensor_ref(
            "post_step", source=state.native_state_digest, seed=seed, steps=steps
        )
        next_state = StateBundle(
            channels=dict(state.channels),
            masks=dict(state.masks),
            batch_id=state.batch_id,
            sample_id=state.sample_id,
            reference_frame=state.reference_frame,
            normalization=state.normalization,
            source_round=state.source_round,
            detach_proof=True,
            native_state_digest=new_digest,
            provenance=state.provenance + ("flowmol3_step",),
            capability_token=state.capability_token,
        )
        trace = ODEIntegratorTrace(
            steps=int(steps),
            accept_rate=1.0,
            native_state_digest=new_digest,
            integrator_config_hash=_make_tensor_ref(
                "integrator_config", seed=seed, steps=steps
            ),
        )
        return next_state, trace

    def observe_endpoint(self, state: StateBundle) -> StateBundle:
        """Observation-only post-step; placeholder re-validates and returns."""
        ok, errs = validate_state_bundle(state)
        if not ok:
            raise CapabilityMissingError(
                "validate_state_bundle", context=",".join(errs)
            )
        return state


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
    "FlowMol3Adapter",
    "FlowMol3Capabilities",
    "default_flowmol3_adapter",
    "flowmol3_registry_entry",
]

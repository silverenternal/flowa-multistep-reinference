"""Public Flow Matching ODE re-inference engine (DTB-G1).

This module declares :class:`Engine` and :class:`EngineRoundResult`. The
engine is the single orchestrator that drives a Flow Matching ODE round
loop against a :class:`FlowMatchingODEAdapter` and an externally-supplied
restart policy. It is the boundary at which the public API owns:

* the per-round call order (capabilities handshake -> build_initial_state
  -> apply_restart_distribution -> compose_condition -> solve_ode ->
  observe_endpoint -> detach_and_validate_endpoint -> round_trace);
* the fail-closed gates for hostile cases (capability mismatch, unknown
  channel, shape/frame/normalization mismatch, non-detached endpoint,
  condition-delta no-effect, integrator trace missing);
* the round-trace / ledger-row emission that downstream consumers
  (orchestrator / policy authority / control policy) consume.

Module boundary
---------------

* stdlib-only. No ``torch``. No I/O. No mutation of inputs.
* The engine NEVER touches native tensors. It only operates on opaque
  :class:`TensorRef` handles and the pure-data carriers in
  :mod:`flow_matching_adapter`.
* The engine NEVER inspects the contents of a
  :class:`FinalRestartPolicy`; it only forwards the policy object to the
  adapter and emits its ``policy_hash`` into the round trace.

Public surface
--------------

* :class:`EngineRoundResult` — return value of :meth:`Engine.run_round`.
* :class:`Engine` — orchestrator.
* :data:`DEFAULT_OPERATION_STEPS` — canonical 7-step call order.

Tasks satisfied:

* ``DTB-G1`` — public Flow Matching ODE re-inference engine.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from adaptive_reflow.contracts import FinalRestartPolicy, hash_policy_hash
from adaptive_reflow.frame.adapter import (
    AdapterCapabilities,
    CapabilityMismatchError,
    CapabilityMissingError,
    FlowMatchingODEAdapter,
    ODEConditionDelta,
    ODEIntegratorTrace,
    StateBundle,
    validate_capabilities,
    validate_condition_delta,
    validate_integrator_trace,
    validate_state_bundle,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


ENGINE_VERSION: str = "0.1.0"
DEFAULT_OPERATION_STEPS: tuple[str, ...] = (
    "capabilities_handshake",
    "build_initial_state",
    "apply_restart_distribution",
    "compose_condition",
    "solve_ode",
    "observe_endpoint",
    "detach_and_validate_endpoint",
)
FEATURE_FLAG_KEY: str = "flow_matching_engine_enabled"


# ---------------------------------------------------------------------------
# Error codes (deterministic, ASCII only, used in round_trace.audit_codes)
# ---------------------------------------------------------------------------


ERR_BUNDLE_NONE: str = "bundle_must_not_be_none"
ERR_BUNDLE_INVALID: str = "bundle_validation_failed"
ERR_POLICY_NONE: str = "policy_must_not_be_none"
ERR_PHASE_STATE_NONE: str = "phase_state_must_not_be_none"
ERR_ROUND_INDEX_NEGATIVE: str = "round_index_must_be_non_negative"
ERR_ADAPTER_NONE: str = "adapter_must_not_be_none"
ERR_CAPABILITIES_INVALID: str = "capabilities_invalid"
ERR_CHANNEL_UNSUPPORTED: str = "channel_not_in_supported_channels"
ERR_CHANNEL_DOMAIN_MISMATCH: str = "channel_domain_mismatch"
ERR_DETACH_PROOF_FAILED: str = "endpoint_not_detached"
ERR_CONDITION_DELTA_NO_EFFECT: str = "condition_delta_no_effect"
ERR_INTEGRATOR_TRACE_MISSING: str = "integrator_trace_missing"
ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH: str = "shape_frame_normalization_mismatch"
ERR_FEATURE_DISABLED: str = "feature_flag_disabled"


# ---------------------------------------------------------------------------
# Pure-data carriers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoundTrace:
    """Pure-data carrier for one engine-driven round.

    The engine builds this from the protocol surface alone; the
    ``audit_codes`` tuple is the canonical, fail-closed report for
    downstream consumers. An empty ``audit_codes`` tuple means the round
    passed every gate the engine enforces.
    """

    round_index: int
    operation_steps: tuple[str, ...]
    source_bundle_digest: str
    applied_policy_hash: str
    initial_state_digest: str
    condition_digest: str
    integrator_trace: ODEIntegratorTrace | None
    endpoint_digest: str
    detached: bool
    audit_codes: tuple[str, ...] = ()
    extras: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "round_index": int(self.round_index),
            "operation_steps": list(self.operation_steps),
            "source_bundle_digest": str(self.source_bundle_digest),
            "applied_policy_hash": str(self.applied_policy_hash),
            "initial_state_digest": str(self.initial_state_digest),
            "condition_digest": str(self.condition_digest),
            "integrator_trace": (
                None
                if self.integrator_trace is None
                else {
                    "steps": int(self.integrator_trace.steps),
                    "accept_rate": float(self.integrator_trace.accept_rate),
                    "native_state_digest": str(self.integrator_trace.native_state_digest),
                    "integrator_config_hash": str(self.integrator_trace.integrator_config_hash),
                }
            ),
            "endpoint_digest": str(self.endpoint_digest),
            "detached": bool(self.detached),
            "audit_codes": list(self.audit_codes),
            "extras": dict(self.extras),
        }


@dataclass(frozen=True)
class LedgerRow:
    """Pure-data ledger row emitted by the engine per round.

    Mirrors the ``DynamicRestartTransferLedger`` shape at the engine's
    protocol level. The engine emits this so downstream consumers can
    persist it; it is also the only carrier that contains the
    ``applied_policy_hash`` from the round.
    """

    ledger_row_id: str
    round_index: int
    source_round: int
    target_round: int
    applied_policy_hash: str
    selected_bundle_digest: str
    audit_codes: tuple[str, ...]
    per_channel_decision: Mapping[str, bool]


@dataclass(frozen=True)
class PhaseState:
    """Engine-side phase state; mirrors :class:`restart_memory_types.PhaseState`.

    The engine uses this rather than the canonical ``PhaseState`` so the
    adapter protocol surface stays self-contained. Downstream code can
    promote it to the canonical shape if needed; the engine never inspects
    its fields beyond what ``run_round`` itself requires.
    """

    outer_cycle_id: int
    round_in_cycle: int
    schedule_phase: str
    schedule_phase_index: int
    horizon_remaining: int
    seed_lineage_digest: str
    recorded_at_round: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "outer_cycle_id": int(self.outer_cycle_id),
            "round_in_cycle": int(self.round_in_cycle),
            "schedule_phase": str(self.schedule_phase),
            "schedule_phase_index": int(self.schedule_phase_index),
            "horizon_remaining": int(self.horizon_remaining),
            "seed_lineage_digest": str(self.seed_lineage_digest),
            "recorded_at_round": int(self.recorded_at_round),
        }


@dataclass(frozen=True)
class EngineRoundResult:
    """Return value of :meth:`Engine.run_round`.

    Fields
    ------

    ``round_trace``
        The :class:`RoundTrace` built by the engine. Empty
        ``audit_codes`` means every gate passed.
    ``next_phase_state``
        The phase state for the *next* round. Produced deterministically
        from the supplied ``phase_state`` plus the round's outcome.
    ``ledger_row``
        The :class:`LedgerRow` persisted alongside this round.
    ``applied_policy_hash``
        Convenience alias of ``round_trace.applied_policy_hash``.
    """

    round_trace: RoundTrace
    next_phase_state: PhaseState
    ledger_row: LedgerRow
    applied_policy_hash: str


# ---------------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------------


def _digest(payload: Any) -> str:
    """Return a deterministic sha256 hex digest for ``payload``.

    Mirrors :func:`restart_memory_types.hash_artifact` but is inlined
    here so the engine module stays stdlib-only with no internal
    dependency on the types module.
    """
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _digest_state(bundle: StateBundle | None) -> str:
    """Return a deterministic digest for ``bundle`` (or empty-string sentinel)."""
    if bundle is None:
        return ""
    payload = {
        "channels": {k: str(v) for k, v in sorted(bundle.channels.items())},
        "masks": {k: str(v) for k, v in sorted(bundle.masks.items())},
        "batch_id": str(bundle.batch_id),
        "sample_id": str(bundle.sample_id),
        "reference_frame": str(bundle.reference_frame),
        "normalization": str(bundle.normalization),
        "source_round": int(bundle.source_round),
        "detach_proof": bool(bundle.detach_proof),
        "native_state_digest": str(bundle.native_state_digest),
        "provenance": list(bundle.provenance),
    }
    return _digest(payload)


def _digest_condition(delta: ODEConditionDelta | None) -> str:
    """Return a deterministic digest for ``delta`` (or empty-string sentinel)."""
    if delta is None:
        return ""
    payload = {
        "delta_spec": {k: str(v) for k, v in sorted(delta.delta_spec.items())},
        "source": str(delta.source),
        "target_round": int(delta.target_round),
        "calibration_artifact_hash": str(delta.calibration_artifact_hash),
    }
    return _digest(payload)


def _channel_domain_lookup(channel: str, caps: AdapterCapabilities) -> str | None:
    """Return the domain for ``channel`` from ``caps.channel_domains``.

    Domain resolution is the adapter's responsibility via its
    :attr:`AdapterCapabilities.channel_domains` declaration. The engine
    never consults a molecule-only fallback table; channels whose
    domain is undeclared simply produce no domain-mismatch audit code
    (they pass through silently). Returns ``None`` when the channel is
    not declared in ``caps.channel_domains``.
    """
    from typing import cast

    from adaptive_reflow.universal.state import ChannelName

    return caps.channel_domains.get(cast(ChannelName, channel))


def _ledger_row_id(round_index: int, policy_hash: str, bundle_digest: str) -> str:
    """Return a deterministic ``LedgerRowId`` for the round."""
    payload = {
        "round_index": int(round_index),
        "applied_policy_hash": str(policy_hash),
        "selected_bundle_digest": str(bundle_digest),
    }
    return _digest(payload)


def _next_phase_state(current: PhaseState, *, round_index: int) -> PhaseState:
    """Return the next-round phase state. Pure / deterministic.

    The engine does not own schedule phase transitions; it only advances
    ``round_in_cycle`` and ``recorded_at_round``. Downstream callers may
    feed the result back into the next :meth:`Engine.run_round` call.
    """
    return PhaseState(
        outer_cycle_id=int(current.outer_cycle_id),
        round_in_cycle=int(current.round_in_cycle) + 1,
        schedule_phase=str(current.schedule_phase),
        schedule_phase_index=int(current.schedule_phase_index),
        horizon_remaining=max(0, int(current.horizon_remaining) - 1),
        seed_lineage_digest=str(current.seed_lineage_digest),
        recorded_at_round=int(round_index),
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class Engine:
    """Public Flow Matching ODE re-inference engine.

    The engine is stateless: each :meth:`run_round` invocation is a pure
    function of its inputs plus the adapter's protocol surface. It does
    not move model weights / checkpoints / training losses / cross-
    attention ownership / multirate clock semantics — those remain owned
    by the underlying Flow Matching implementation that the adapter wraps.
    """

    def __init__(
        self,
        *,
        operation_steps: tuple[str, ...] = DEFAULT_OPERATION_STEPS,
        feature_flag: bool | None = None,
    ) -> None:
        self._operation_steps = tuple(operation_steps)
        if not self._operation_steps:
            raise ValueError("operation_steps must be non-empty")
        # The engine is opt-in: when ``feature_flag`` is ``False``, the
        # engine emits a disabled-feature round trace and never calls
        # the adapter. ``None`` defaults to enabled.
        self._feature_flag = True if feature_flag is None else bool(feature_flag)

    # -- public properties -------------------------------------------------

    @property
    def operation_steps(self) -> tuple[str, ...]:
        return self._operation_steps

    @property
    def feature_enabled(self) -> bool:
        return self._feature_flag

    # -- public methods ----------------------------------------------------

    def handshake(self, adapter: FlowMatchingODEAdapter) -> AdapterCapabilities:
        """Run the capabilities handshake and return the parsed surface.

        Raises
        ------
        CapabilityMissingError
            When the adapter's surface is missing a required capability
            that the engine relies on.
        CapabilityMismatchError
            When the surface fails its own consistency check (e.g.
            ``supported_channels`` is empty while the adapter advertises
            at least one channel kind).
        RuntimeError
            When the adapter is ``None``.
        """
        if adapter is None:
            raise RuntimeError(ERR_ADAPTER_NONE)
        caps = adapter.capabilities()
        ok, errors = validate_capabilities(caps)
        if not ok:
            raise CapabilityMismatchError(
                f"adapter capabilities failed consistency check: {errors}",
                capability="capabilities",
            )
        # The engine itself requires an ODE integration surface, prior
        # export, state export, condition injection, restart boundary,
        # trajectory digest, deterministic seed and materialization
        # route. Continuous-vs-discrete is per-adapter.
        for required in (
            "has_ode_integration_surface",
            "has_prior_export",
            "has_state_export",
            "has_condition_injection",
            "has_restart_boundary",
            "has_trajectory_digest",
            "has_deterministic_seed",
            "has_materialization_route",
        ):
            if not bool(getattr(caps, required)):
                raise CapabilityMissingError(required, context="Engine.handshake")
        return caps

    def run_round(
        self,
        round_index: int,
        phase_state: PhaseState,
        bundle: StateBundle | None,
        adapter: FlowMatchingODEAdapter,
        policy: FinalRestartPolicy | None,
        condition_delta: ODEConditionDelta | None = None,
        *,
        seed: int = 0,
    ) -> EngineRoundResult:
        """Orchestrate one Flow Matching ODE round.

        Parameters
        ----------
        round_index:
            Zero-based round index. Must be a non-negative integer.
        phase_state:
            The current phase state. Used to seed the next-phase-state
            emission; never mutated.
        bundle:
            The source :class:`StateBundle` (typically the immediate
            previous round's endpoint, validated as detached). When the
            feature flag is disabled the engine short-circuits before
            inspecting ``bundle``.
        adapter:
            The :class:`FlowMatchingODEAdapter` orchestrating the
            native ODE integration.
        policy:
            The :class:`FinalRestartPolicy` consumed this round. The
            engine forwards it to ``adapter.apply_restart_distribution``
            and emits its ``policy_hash`` into the round trace.
        condition_delta:
            Optional :class:`ODEConditionDelta` for this round. When
            ``None`` the engine fails closed (a round without a
            condition delta has no effect).
        seed:
            Deterministic seed forwarded to ``adapter.solve_ode``.

        Returns
        -------
        :class:`EngineRoundResult`
            A tuple of ``(round_trace, next_phase_state, ledger_row,
            applied_policy_hash)`` where ``applied_policy_hash`` is a
            convenience alias of ``round_trace.applied_policy_hash``.

        Notes
        -----
        The engine enforces the following fail-closed gates (the
        canonical hostile-case catalogue). Each gate appends a code to
        ``round_trace.audit_codes`` but does NOT raise; the engine
        always returns an :class:`EngineRoundResult` so that the ledger
        is never silently dropped.

        * ``bundle_must_not_be_none``
        * ``bundle_validation_failed``
        * ``policy_must_not_be_none``
        * ``phase_state_must_not_be_none``
        * ``round_index_must_be_non_negative``
        * ``adapter_must_not_be_none``
        * ``capabilities_invalid``
        * ``channel_not_in_supported_channels``
        * ``channel_domain_mismatch``
        * ``endpoint_not_detached``
        * ``condition_delta_no_effect``
        * ``integrator_trace_missing``
        * ``shape_frame_normalization_mismatch``
        * ``feature_flag_disabled``
        """
        audit_codes: list[str] = []
        if not self._feature_flag:
            audit_codes.append(ERR_FEATURE_DISABLED)
            trace = RoundTrace(
                round_index=int(round_index),
                operation_steps=self._operation_steps,
                source_bundle_digest=_digest_state(bundle),
                applied_policy_hash="",
                initial_state_digest="",
                condition_digest="",
                integrator_trace=None,
                endpoint_digest="",
                detached=False,
                audit_codes=tuple(audit_codes),
                extras={"feature_flag": False, "engine_version": ENGINE_VERSION},
            )
            ledger = LedgerRow(
                ledger_row_id=_ledger_row_id(round_index, "", _digest_state(bundle)),
                round_index=int(round_index),
                source_round=int(bundle.source_round) if bundle is not None else 0,
                target_round=int(round_index),
                applied_policy_hash="",
                selected_bundle_digest=_digest_state(bundle),
                audit_codes=tuple(audit_codes),
                per_channel_decision={},
            )
            next_state = _next_phase_state(phase_state, round_index=round_index)
            return EngineRoundResult(
                round_trace=trace,
                next_phase_state=next_state,
                ledger_row=ledger,
                applied_policy_hash="",
            )

        # ---- argument gates -------------------------------------------------
        if adapter is None:
            raise RuntimeError(ERR_ADAPTER_NONE)
        if phase_state is None:
            audit_codes.append(ERR_PHASE_STATE_NONE)
        if isinstance(round_index, bool) or not isinstance(round_index, int):
            audit_codes.append(ERR_ROUND_INDEX_NEGATIVE)
            round_index = 0
        elif round_index < 0:
            audit_codes.append(ERR_ROUND_INDEX_NEGATIVE)
        if policy is None:
            audit_codes.append(ERR_POLICY_NONE)
        if bundle is None:
            audit_codes.append(ERR_BUNDLE_NONE)

        applied_policy_hash: str = (
            str(hash_policy_hash(policy)) if policy is not None else ""
        )

        # ---- capability handshake -------------------------------------------
        caps: AdapterCapabilities | None = None
        try:
            caps = self.handshake(adapter)
        except (CapabilityMissingError, CapabilityMismatchError) as exc:
            audit_codes.append(ERR_CAPABILITIES_INVALID + f":{type(exc).__name__}")
        except RuntimeError as exc:
            audit_codes.append(ERR_CAPABILITIES_INVALID + f":{type(exc).__name__}:{exc}")

        # ---- bundle validation ---------------------------------------------
        if bundle is not None:
            ok, errors = validate_state_bundle(bundle)
            if not ok:
                audit_codes.append(ERR_BUNDLE_INVALID)
                for code in errors:
                    audit_codes.append(f"{ERR_BUNDLE_INVALID}:{code}")

        # Reject unknown channels / domain mismatches.
        if bundle is not None and caps is not None:
            for channel in bundle.channels:
                if channel not in caps.supported_channels:
                    audit_codes.append(f"{ERR_CHANNEL_UNSUPPORTED}:{channel}")
                else:
                    expected = _channel_domain_lookup(channel, caps)
                    advertised_continuous = caps.has_continuous_channels
                    advertised_discrete = caps.has_discrete_channels
                    if expected == "continuous" and not advertised_continuous or expected == "discrete" and not advertised_discrete:
                        audit_codes.append(f"{ERR_CHANNEL_DOMAIN_MISMATCH}:{channel}")

        # Fail closed on missing condition delta.
        if condition_delta is None:
            audit_codes.append(ERR_CONDITION_DELTA_NO_EFFECT)
        else:
            ok, errors = validate_condition_delta(condition_delta)
            if not ok:
                audit_codes.append(ERR_CONDITION_DELTA_NO_EFFECT)
                for code in errors:
                    audit_codes.append(f"{ERR_CONDITION_DELTA_NO_EFFECT}:{code}")

        # Short-circuit native calls when gates already fired.
        if audit_codes:
            trace = RoundTrace(
                round_index=int(round_index),
                operation_steps=self._operation_steps,
                source_bundle_digest=_digest_state(bundle),
                applied_policy_hash=applied_policy_hash,
                initial_state_digest="",
                condition_digest=_digest_condition(condition_delta),
                integrator_trace=None,
                endpoint_digest="",
                detached=False,
                audit_codes=tuple(audit_codes),
                extras={"feature_flag": True, "engine_version": ENGINE_VERSION},
            )
            ledger = LedgerRow(
                ledger_row_id=_ledger_row_id(round_index, applied_policy_hash, _digest_state(bundle)),
                round_index=int(round_index),
                source_round=int(bundle.source_round) if bundle is not None else 0,
                target_round=int(round_index),
                applied_policy_hash=applied_policy_hash,
                selected_bundle_digest=_digest_state(bundle),
                audit_codes=tuple(audit_codes),
                per_channel_decision={},
            )
            next_state = _next_phase_state(phase_state, round_index=round_index)
            return EngineRoundResult(
                round_trace=trace,
                next_phase_state=next_state,
                ledger_row=ledger,
                applied_policy_hash=applied_policy_hash,
            )

        # ---- happy path: drive the protocol surface -------------------------
        # The pre-flight validation above guarantees non-None for these.
        assert bundle is not None  # noqa: S101 — fail-closed precondition
        assert policy is not None  # noqa: S101 — fail-closed precondition
        assert condition_delta is not None  # noqa: S101 — fail-closed precondition

        # 1. Build initial state.
        initial_state = adapter.build_initial_state(
            batch_id=bundle.batch_id,
            sample_id=bundle.sample_id,
        )

        # 2. Apply restart distribution (beta=0 preserves the prior).
        post_state = adapter.apply_restart_distribution(initial_state, policy)

        # 3. Compose condition.
        composed = adapter.compose_condition(post_state, condition_delta)

        # 4. Shape / frame / normalization mismatch gate.
        # The adapter must produce a condition whose target_round matches
        # what we asked for AND whose calibration_artifact_hash matches the
        # source delta (else no effective change -> fail closed).
        composed_ok = (
            composed.target_round == condition_delta.target_round
            and composed.calibration_artifact_hash == condition_delta.calibration_artifact_hash
        )
        if not composed_ok:
            audit_codes.append(ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH)
            trace = RoundTrace(
                round_index=int(round_index),
                operation_steps=self._operation_steps,
                source_bundle_digest=_digest_state(bundle),
                applied_policy_hash=applied_policy_hash,
                initial_state_digest=_digest_state(initial_state),
                condition_digest=_digest_condition(composed),
                integrator_trace=None,
                endpoint_digest="",
                detached=False,
                audit_codes=tuple(audit_codes),
                extras={"feature_flag": True, "engine_version": ENGINE_VERSION},
            )
            ledger = LedgerRow(
                ledger_row_id=_ledger_row_id(round_index, applied_policy_hash, _digest_state(bundle)),
                round_index=int(round_index),
                source_round=int(bundle.source_round),
                target_round=int(round_index),
                applied_policy_hash=applied_policy_hash,
                selected_bundle_digest=_digest_state(bundle),
                audit_codes=tuple(audit_codes),
                per_channel_decision={},
            )
            next_state = _next_phase_state(phase_state, round_index=round_index)
            return EngineRoundResult(
                round_trace=trace,
                next_phase_state=next_state,
                ledger_row=ledger,
                applied_policy_hash=applied_policy_hash,
            )

        # 5. Solve the ODE.
        integrator_trace = adapter.solve_ode(post_state, composed, seed=int(seed))
        if integrator_trace is None:
            audit_codes.append(ERR_INTEGRATOR_TRACE_MISSING)
            trace = RoundTrace(
                round_index=int(round_index),
                operation_steps=self._operation_steps,
                source_bundle_digest=_digest_state(bundle),
                applied_policy_hash=applied_policy_hash,
                initial_state_digest=_digest_state(initial_state),
                condition_digest=_digest_condition(composed),
                integrator_trace=None,
                endpoint_digest="",
                detached=False,
                audit_codes=tuple(audit_codes),
                extras={"feature_flag": True, "engine_version": ENGINE_VERSION},
            )
            ledger = LedgerRow(
                ledger_row_id=_ledger_row_id(round_index, applied_policy_hash, _digest_state(bundle)),
                round_index=int(round_index),
                source_round=int(bundle.source_round),
                target_round=int(round_index),
                applied_policy_hash=applied_policy_hash,
                selected_bundle_digest=_digest_state(bundle),
                audit_codes=tuple(audit_codes),
                per_channel_decision={},
            )
            next_state = _next_phase_state(phase_state, round_index=round_index)
            return EngineRoundResult(
                round_trace=trace,
                next_phase_state=next_state,
                ledger_row=ledger,
                applied_policy_hash=applied_policy_hash,
            )

        ok, errors = validate_integrator_trace(integrator_trace)
        if not ok:
            audit_codes.append(ERR_INTEGRATOR_TRACE_MISSING)
            for code in errors:
                audit_codes.append(f"{ERR_INTEGRATOR_TRACE_MISSING}:{code}")

        # 6. Observe endpoint.
        observed = adapter.observe_endpoint(integrator_trace, post_state)

        # 7. Export + detach + validate.
        exported = adapter.export_endpoint(observed)
        detached = adapter.detach_and_validate_endpoint(exported)

        if not detached.detach_proof:
            audit_codes.append(ERR_DETACH_PROOF_FAILED)

        trace = RoundTrace(
            round_index=int(round_index),
            operation_steps=self._operation_steps,
            source_bundle_digest=_digest_state(bundle),
            applied_policy_hash=applied_policy_hash,
            initial_state_digest=_digest_state(initial_state),
            condition_digest=_digest_condition(composed),
            integrator_trace=integrator_trace,
            endpoint_digest=_digest_state(detached),
            detached=bool(detached.detach_proof),
            audit_codes=tuple(audit_codes),
            extras={"feature_flag": True, "engine_version": ENGINE_VERSION},
        )
        ledger = LedgerRow(
            ledger_row_id=_ledger_row_id(round_index, applied_policy_hash, _digest_state(bundle)),
            round_index=int(round_index),
            source_round=int(bundle.source_round),
            target_round=int(round_index),
            applied_policy_hash=applied_policy_hash,
            selected_bundle_digest=_digest_state(bundle),
            audit_codes=tuple(audit_codes),
            per_channel_decision={
                channel: bool(detached.detach_proof) for channel in bundle.channels
            },
        )
        next_state = _next_phase_state(phase_state, round_index=round_index)
        return EngineRoundResult(
            round_trace=trace,
            next_phase_state=next_state,
            ledger_row=ledger,
            applied_policy_hash=applied_policy_hash,
        )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "DEFAULT_OPERATION_STEPS",
    # Constants
    "ENGINE_VERSION",
    "ERR_ADAPTER_NONE",
    "ERR_BUNDLE_INVALID",
    # Error codes
    "ERR_BUNDLE_NONE",
    "ERR_CAPABILITIES_INVALID",
    "ERR_CHANNEL_DOMAIN_MISMATCH",
    "ERR_CHANNEL_UNSUPPORTED",
    "ERR_CONDITION_DELTA_NO_EFFECT",
    "ERR_DETACH_PROOF_FAILED",
    "ERR_FEATURE_DISABLED",
    "ERR_INTEGRATOR_TRACE_MISSING",
    "ERR_PHASE_STATE_NONE",
    "ERR_POLICY_NONE",
    "ERR_ROUND_INDEX_NEGATIVE",
    "ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH",
    "FEATURE_FLAG_KEY",
    # Engine
    "Engine",
    "EngineRoundResult",
    "LedgerRow",
    "PhaseState",
    # Data carriers
    "RoundTrace",
]

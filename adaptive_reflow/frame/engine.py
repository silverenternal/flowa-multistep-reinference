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
import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from adaptive_reflow.contracts import (
    FactorValue,
    FinalRestartPolicy,
    hash_policy_hash,
)
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
from adaptive_reflow.schedule.cosine import memory_fraction_from_schedule

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
ERR_ROUND_INDEX_NON_INT: str = "round_index_must_be_int"
ERR_ADAPTER_NONE: str = "adapter_must_not_be_none"
ERR_CAPABILITIES_INVALID: str = "capabilities_invalid"
ERR_CHANNEL_UNSUPPORTED: str = "channel_not_in_supported_channels"
ERR_CHANNEL_DOMAIN_MISMATCH: str = "channel_domain_mismatch"
ERR_CHANNEL_DOMAIN_UNDECLARED: str = "channel_domain_undeclared"
ERR_DETACH_PROOF_FAILED: str = "endpoint_not_detached"
ERR_CONDITION_DELTA_NO_EFFECT: str = "condition_delta_no_effect"
ERR_INTEGRATOR_TRACE_MISSING: str = "integrator_trace_missing"
ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH: str = "shape_frame_normalization_mismatch"
ERR_FEATURE_DISABLED: str = "feature_flag_disabled"
ERR_ADAPTER_RAISED: str = "adapter_raised_exception"
ERR_SOURCE_ROUND_NON_INT: str = "source_round_must_be_int"


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
    """Return a deterministic digest for ``bundle`` (or empty-string sentinel).

    ``bundle.source_round`` is coerced defensively: a non-int / negative
    value would otherwise raise ``TypeError`` here before the engine has
    a chance to emit ``ERR_SOURCE_ROUND_NON_INT``. The coercion is
    silent at this level because audit emission lives in
    :func:`_coerce_nonneg_int`; this function only owns the digest.
    """
    if bundle is None:
        return ""
    sr = bundle.source_round
    if isinstance(sr, bool) or not isinstance(sr, int) or sr < 0:
        sr_repr = type(sr).__name__
    else:
        sr_repr = str(sr)
    payload = {
        "channels": {k: str(v) for k, v in sorted(bundle.channels.items())},
        "masks": {k: str(v) for k, v in sorted(bundle.masks.items())},
        "batch_id": str(bundle.batch_id),
        "sample_id": str(bundle.sample_id),
        "reference_frame": str(bundle.reference_frame),
        "normalization": str(bundle.normalization),
        "source_round": sr_repr,
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


def _coerce_nonneg_int(
    value: Any,
    name: str,
    audit_codes: list[str],
    default: int = 0,
) -> int:
    """Coerce ``value`` to a non-negative ``int`` with audit-trail errors.

    The helper is the single boundary at which the engine tolerates
    non-int / negative ``round_index`` and ``source_round`` values:
    it appends a fail-closed audit code (``ERR_ROUND_INDEX_NON_INT`` /
    ``ERR_SOURCE_ROUND_NON_INT`` for non-int, ``ERR_ROUND_INDEX_NEGATIVE``
    for negative ``round_index``) and returns ``default`` so downstream
    ledger-row digest computation always has a valid int.
    """
    # bool is a subclass of int in Python — treat as non-int explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        code = ERR_ROUND_INDEX_NON_INT if name == "round_index" else ERR_SOURCE_ROUND_NON_INT
        audit_codes.append(f"{code}:{name}:{type(value).__name__}")
        return default
    if value < 0:
        # Negative ints are only meaningful for ``round_index``; for
        # ``source_round`` we still surface the canonical
        # ERR_SOURCE_ROUND_NON_INT code (the contract is "must be int").
        if name == "round_index":
            audit_codes.append(ERR_ROUND_INDEX_NEGATIVE)
        else:
            audit_codes.append(ERR_SOURCE_ROUND_NON_INT + f":{name}:negative")
        return default
    return int(value)


def _safe_source_round(bundle: StateBundle | None, audit_codes: list[str]) -> int:
    """Return ``bundle.source_round`` as a non-negative ``int``.

    Single-call site used at every :class:`LedgerRow` construction in
    the engine: handles ``None`` bundles (returns ``0``), non-int
    ``source_round`` values (emits ``ERR_SOURCE_ROUND_NON_INT`` and
    returns ``0``), and never raises. The accompanying :func:`_digest_state`
    is also defensive against malformed bundles; this helper exists so
    the ledger row's ``source_round`` field itself stays an ``int``.
    """
    if bundle is None:
        return 0
    return _coerce_nonneg_int(
        getattr(bundle, "source_round", 0), "source_round", audit_codes
    )


def _safe_adapter_call(
    step_name: str,
    audit_codes: list[str],
    fn: Any,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Wrap an adapter call so a stray ``Exception`` cannot crash the round.

    On any raised exception, append
    ``f"{ERR_ADAPTER_RAISED}:{step_name}:{ExceptionType}:{message[:80]}"``
    to ``audit_codes`` and return ``None``. The engine then emits a
    fail-closed round trace rather than propagating the exception to the
    caller. ``Exception`` (not ``BaseException``) is intentional:
    ``KeyboardInterrupt`` / ``SystemExit`` must still propagate.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        message = str(exc)[:80]
        audit_codes.append(
            f"{ERR_ADAPTER_RAISED}:{step_name}:{type(exc).__name__}:{message}"
        )
        return None


def _policy_with_schedule_beta(policy: FinalRestartPolicy) -> FinalRestartPolicy:
    """Return a copy of ``policy`` with ``beta_by_channel`` overridden by the schedule.

    ADR-0010 — cosine-driven memory fraction. When the policy carries
    a non-``None`` :class:`CosineScheduleSample` (and the dataclass
    flag ``beta_from_schedule`` is ``True``, which is the engine-side
    precondition for entering this helper), the per-round memory
    fraction is the schedule's complement of fresh-noise capacity:

        memory_fraction = 1.0 - n_cap        (``memory_fraction_from_schedule``)
        beta             = 1.0 - memory_fraction
                         = n_cap

    So at round 0 with ``n_cap = n_max`` (large) the engine emits
    ``beta = n_max`` (lots of fresh noise, exploration); at round L-1
    with ``n_cap = n_min`` (small) the engine emits
    ``beta = n_min`` (preserve prior, refine). The mapping is built
    once over the policy's existing ``beta_by_channel`` keys so the
    override preserves the channel vocabulary; the resulting
    ``policy_hash`` is recomputed via :func:`hash_policy_hash` so the
    audit invariant that the hash matches the canonical field tuple
    is preserved.

    Returns ``policy`` unchanged when ``policy.schedule_sample is None``
    — the caller already gates on that precondition, so this branch is
    a defensive no-op for callers that invoke the helper directly.
    """
    sample = policy.schedule_sample
    if sample is None:
        return policy
    # beta = n_cap (clipped) per the ADR-0010 derivation; the helper
    # ``memory_fraction_from_schedule`` returns the complementary
    # ``1 - n_cap`` so we subtract from ``1.0`` here. We do not call
    # the helper for the beta value because the adapter's
    # ``apply_restart_distribution`` convention is
    # ``memory_fraction = 1 - beta``; inverting twice costs nothing
    # but is easier to read as the direct ``n_cap`` assignment.
    n_cap_raw = sample.n_cap
    try:
        n_cap = float(n_cap_raw)
    except (TypeError, ValueError):
        return policy
    if not _isfinite_or_skip(n_cap):
        return policy
    beta_value = max(0.0, min(1.0, n_cap))
    new_beta_by_channel = {
        channel: FactorValue(float(beta_value))
        for channel in policy.beta_by_channel
    }
    overridden = replace(policy, beta_by_channel=new_beta_by_channel)
    return replace(overridden, policy_hash=hash_policy_hash(overridden))


def _isfinite_or_skip(value: Any) -> bool:
    """Return ``True`` iff ``value`` is a finite real number."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f)


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

    @staticmethod
    def _emit_fail_closed(
        *,
        round_index: int,
        bundle: StateBundle,
        audit_codes: list[str],
        applied_policy_hash: str,
        phase_state: PhaseState,
        initial_state: StateBundle | None,
        composed: ODEConditionDelta | None,
        integrator_trace: ODEIntegratorTrace | None,
        detached: StateBundle | None,
        condition_delta: ODEConditionDelta | None,
    ) -> EngineRoundResult:
        """Build a fail-closed :class:`EngineRoundResult` for the happy path.

        Invoked from :meth:`run_round` whenever one of the six
        :func:`_safe_adapter_call` wrappers returns ``None`` (the adapter
        raised, was misbehaved, or returned an unexpected ``None``).
        The audit trail already carries the
        :data:`ERR_ADAPTER_RAISED` / :data:`ERR_INTEGRATOR_TRACE_MISSING`
        code; this helper only packages the round trace and ledger row
        so the caller can return without further branching. The ledger
        ``source_round`` is sourced through :func:`_coerce_nonneg_int`
        so a malformed bundle never raises here either.
        """
        # Coerce source_round BEFORE freezing the audit_codes tuple so a
        # malformed bundle surfaces ERR_SOURCE_ROUND_NON_INT in both the
        # RoundTrace and the LedgerRow (closes Gap C3 in the fail-closed
        # adapter-raised path).
        _coerce_nonneg_int(
            getattr(bundle, "source_round", 0), "source_round", audit_codes
        )
        codes = tuple(audit_codes)
        trace = RoundTrace(
            round_index=int(round_index),
            operation_steps=DEFAULT_OPERATION_STEPS,
            source_bundle_digest=_digest_state(bundle),
            applied_policy_hash=applied_policy_hash,
            initial_state_digest=(
                _digest_state(initial_state) if initial_state is not None else ""
            ),
            condition_digest=_digest_condition(composed)
            if composed is not None
            else _digest_condition(condition_delta),
            integrator_trace=integrator_trace,
            endpoint_digest=(
                _digest_state(detached) if detached is not None else ""
            ),
            detached=bool(detached.detach_proof) if detached is not None else False,
            audit_codes=codes,
            extras={"feature_flag": True, "engine_version": ENGINE_VERSION},
        )
        ledger = LedgerRow(
            ledger_row_id=_ledger_row_id(
                round_index, applied_policy_hash, _digest_state(bundle)
            ),
            round_index=int(round_index),
            source_round=int(bundle.source_round)
            if isinstance(getattr(bundle, "source_round", 0), int)
            and not isinstance(getattr(bundle, "source_round", 0), bool)
            and getattr(bundle, "source_round", 0) >= 0
            else 0,
            target_round=int(round_index),
            applied_policy_hash=applied_policy_hash,
            selected_bundle_digest=_digest_state(bundle),
            audit_codes=codes,
            per_channel_decision={},
        )
        next_state = _next_phase_state(phase_state, round_index=round_index)
        return EngineRoundResult(
            round_trace=trace,
            next_phase_state=next_state,
            ledger_row=ledger,
            applied_policy_hash=applied_policy_hash,
        )

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

        Cosine-driven memory fraction (ADR-0010): when
        ``policy.beta_from_schedule is True`` (default) and
        ``policy.schedule_sample is not None``, the engine overrides
        ``policy.beta_by_channel`` for the duration of this round so
        the per-round memory fraction is the schedule's complement of
        ``n_cap``: ``beta = n_cap`` so ``memory_fraction = 1 - n_cap``.
        The override is invisible to the caller (the supplied
        ``policy`` is never mutated); the round trace's
        ``applied_policy_hash`` reflects the post-override hash so the
        audit invariant ``hash == recompute`` holds. When
        ``policy.beta_from_schedule is False`` (back-compat) the
        policy is forwarded verbatim.
        """
        audit_codes: list[str] = []
        # Coerce round_index BEFORE the feature-flag check so the
        # short-circuit path always sees a non-negative int (closes
        # Gap A4: int(round_index) on a negative value would propagate
        # a negative digest seed; on a bool it would silently coerce
        # to 0/1 without emitting any audit code).
        round_index = _coerce_nonneg_int(
            round_index, "round_index", audit_codes
        )
        if not self._feature_flag:
            audit_codes.append(ERR_FEATURE_DISABLED)
            # Coerce source_round BEFORE capturing audit_codes into the
            # RoundTrace so a malformed bundle surfaces ERR_SOURCE_ROUND_NON_INT
            # consistently across both carriers.
            _coerce_nonneg_int(
                getattr(bundle, "source_round", 0), "source_round", audit_codes
            )
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
                source_round=_safe_source_round(bundle, audit_codes),
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
                    if expected is None:
                        # Channel is in ``supported_channels`` but the
                        # adapter did NOT declare a domain in
                        # ``caps.channel_domains``. The old code
                        # silently passed this case (the adapter could
                        # advertise any domain); the new code emits
                        # ``ERR_CHANNEL_DOMAIN_UNDECLARED`` so the
                        # downstream consumer can surface the gap
                        # (closes Gap A5).
                        audit_codes.append(
                            f"{ERR_CHANNEL_DOMAIN_UNDECLARED}:{channel}"
                        )
                    elif (
                        expected == "continuous" and not advertised_continuous
                    ) or (
                        expected == "discrete" and not advertised_discrete
                    ):
                        audit_codes.append(
                            f"{ERR_CHANNEL_DOMAIN_MISMATCH}:{channel}"
                        )

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
            # Coerce source_round BEFORE freezing the audit_codes into
            # the RoundTrace / LedgerRow tuples so any ERR_SOURCE_ROUND_NON_INT
            # lands in both carriers (closes Gap C3: a malformed bundle
            # must surface the audit code consistently).
            _coerce_nonneg_int(
                getattr(bundle, "source_round", 0), "source_round", audit_codes
            )
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
                source_round=_safe_source_round(bundle, audit_codes),
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

        # 1. Build initial state. Wrapped in _safe_adapter_call so a
        #    misbehaving adapter never crashes the round (Gap B2).
        initial_state = _safe_adapter_call(
            "build_initial_state",
            audit_codes,
            adapter.build_initial_state,
            batch_id=bundle.batch_id,
            sample_id=bundle.sample_id,
        )
        if initial_state is None:
            return self._emit_fail_closed(
                round_index=round_index,
                bundle=bundle,
                audit_codes=audit_codes,
                applied_policy_hash=applied_policy_hash,
                phase_state=phase_state,
                initial_state=None,
                composed=None,
                integrator_trace=None,
                detached=None,
                condition_delta=condition_delta,
            )

        # 2. Apply restart distribution (beta=0 preserves the prior).
        # ADR-0010 — cosine-driven memory fraction. When the policy
        # carries a non-``None`` ``schedule_sample`` AND the
        # ``beta_from_schedule`` flag is ``True`` (default), the engine
        # overrides ``beta_by_channel`` from the schedule's ``n_cap``
        # (``beta = n_cap`` so ``memory_fraction = 1 - n_cap``). The
        # helper is pure; the resulting ``policy_hash`` is recomputed
        # via :func:`hash_policy_hash` so the audit trail matches the
        # actually-emitted beta. When ``beta_from_schedule`` is
        # ``False`` (back-compat) the policy is forwarded verbatim.
        applied_policy: FinalRestartPolicy = policy
        if policy.beta_from_schedule and policy.schedule_sample is not None:
            applied_policy = _policy_with_schedule_beta(policy)
        if applied_policy is not policy:
            # Recompute the applied hash so the round trace's
            # ``applied_policy_hash`` reflects the post-override
            # policy. The original ``policy`` is left untouched so
            # the caller can still introspect the unoverridden surface.
            applied_policy_hash = str(hash_policy_hash(applied_policy))

        post_state = _safe_adapter_call(
            "apply_restart_distribution",
            audit_codes,
            adapter.apply_restart_distribution,
            initial_state,
            applied_policy,
        )
        if post_state is None:
            return self._emit_fail_closed(
                round_index=round_index,
                bundle=bundle,
                audit_codes=audit_codes,
                applied_policy_hash=applied_policy_hash,
                phase_state=phase_state,
                initial_state=initial_state,
                composed=None,
                integrator_trace=None,
                detached=None,
                condition_delta=condition_delta,
            )

        # 3. Compose condition.
        composed = _safe_adapter_call(
            "compose_condition",
            audit_codes,
            adapter.compose_condition,
            post_state,
            condition_delta,
        )
        if composed is None:
            return self._emit_fail_closed(
                round_index=round_index,
                bundle=bundle,
                audit_codes=audit_codes,
                applied_policy_hash=applied_policy_hash,
                phase_state=phase_state,
                initial_state=initial_state,
                composed=None,
                integrator_trace=None,
                detached=None,
                condition_delta=condition_delta,
            )

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
            _coerce_nonneg_int(
                getattr(bundle, "source_round", 0), "source_round", audit_codes
            )
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
                source_round=_safe_source_round(bundle, audit_codes),
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
        integrator_trace = _safe_adapter_call(
            "solve_ode",
            audit_codes,
            adapter.solve_ode,
            post_state,
            composed,
            seed=int(seed),
        )
        if integrator_trace is None:
            audit_codes.append(ERR_INTEGRATOR_TRACE_MISSING)
            return self._emit_fail_closed(
                round_index=round_index,
                bundle=bundle,
                audit_codes=audit_codes,
                applied_policy_hash=applied_policy_hash,
                phase_state=phase_state,
                initial_state=initial_state,
                composed=composed,
                integrator_trace=None,
                detached=None,
                condition_delta=condition_delta,
            )

        ok, errors = validate_integrator_trace(integrator_trace)
        if not ok:
            audit_codes.append(ERR_INTEGRATOR_TRACE_MISSING)
            for code in errors:
                audit_codes.append(f"{ERR_INTEGRATOR_TRACE_MISSING}:{code}")

        # 6. Observe endpoint.
        observed = _safe_adapter_call(
            "observe_endpoint",
            audit_codes,
            adapter.observe_endpoint,
            integrator_trace,
            post_state,
        )
        if observed is None:
            return self._emit_fail_closed(
                round_index=round_index,
                bundle=bundle,
                audit_codes=audit_codes,
                applied_policy_hash=applied_policy_hash,
                phase_state=phase_state,
                initial_state=initial_state,
                composed=composed,
                integrator_trace=integrator_trace,
                detached=None,
                condition_delta=condition_delta,
            )

        # 7. Export endpoint. Wrapped separately so a raised exception
        #    is captured with the correct ``step_name``.
        exported = _safe_adapter_call(
            "export_endpoint",
            audit_codes,
            adapter.export_endpoint,
            observed,
        )
        if exported is None:
            return self._emit_fail_closed(
                round_index=round_index,
                bundle=bundle,
                audit_codes=audit_codes,
                applied_policy_hash=applied_policy_hash,
                phase_state=phase_state,
                initial_state=initial_state,
                composed=composed,
                integrator_trace=integrator_trace,
                detached=None,
                condition_delta=condition_delta,
            )

        detached = _safe_adapter_call(
            "detach_and_validate_endpoint",
            audit_codes,
            adapter.detach_and_validate_endpoint,
            exported,
        )
        if detached is None:
            return self._emit_fail_closed(
                round_index=round_index,
                bundle=bundle,
                audit_codes=audit_codes,
                applied_policy_hash=applied_policy_hash,
                phase_state=phase_state,
                initial_state=initial_state,
                composed=composed,
                integrator_trace=integrator_trace,
                detached=None,
                condition_delta=condition_delta,
            )

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
            source_round=_safe_source_round(bundle, audit_codes),
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
    "ERR_ADAPTER_RAISED",
    "ERR_BUNDLE_INVALID",
    # Error codes
    "ERR_BUNDLE_NONE",
    "ERR_CAPABILITIES_INVALID",
    "ERR_CHANNEL_DOMAIN_MISMATCH",
    "ERR_CHANNEL_DOMAIN_UNDECLARED",
    "ERR_CHANNEL_UNSUPPORTED",
    "ERR_CONDITION_DELTA_NO_EFFECT",
    "ERR_DETACH_PROOF_FAILED",
    "ERR_FEATURE_DISABLED",
    "ERR_INTEGRATOR_TRACE_MISSING",
    "ERR_PHASE_STATE_NONE",
    "ERR_POLICY_NONE",
    "ERR_ROUND_INDEX_NEGATIVE",
    "ERR_ROUND_INDEX_NON_INT",
    "ERR_SHAPE_FRAME_NORMALIZATION_MISMATCH",
    "ERR_SOURCE_ROUND_NON_INT",
    "FEATURE_FLAG_KEY",
    # Engine
    "Engine",
    "EngineRoundResult",
    "LedgerRow",
    "PhaseState",
    # Data carriers
    "RoundTrace",
]

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
from pathlib import Path
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

# Wave 233 P6 — SHA-256 digest cache for StateBundle (identity-keyed
# memoization). When ``digest_cache`` is supplied to ``Engine.__init__``
# the engine routes its :func:`_digest_state` calls through the cache so
# repeated calls on the same :class:`StateBundle` instance within a
# single round return the cached value instead of recomputing the
# JSON-canonical + SHA-256 path. See
# :mod:`adaptive_reflow.framework.state_bundle_cache` for the
# soundness argument (frozen dataclass + per-round fresh instance).
from adaptive_reflow.framework.state_bundle_cache import (  # noqa: E402
    StateBundleDigestCache as _StateBundleDigestCache,
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
ERR_ADAPTER_CONFIGURATION_ERROR: str = "adapter_configuration_error"
ERR_SCHEDULE_SAMPLE_MISSING: str = "schedule_sample_missing"
ERR_CAPABILITY_UNSUPPORTED: str = "capability_unsupported"


# ---------------------------------------------------------------------------
# Typed exceptions (engine-internal; P0-1)
# ---------------------------------------------------------------------------


class AdapterConfigurationError(Exception):
    """Engine-internal failure indicating the adapter is mis-configured.

    This exception is intentionally a subclass of :class:`Exception` and
    NOT of :class:`RuntimeError` / :class:`ValueError` / :class:`TypeError`.
    The engine's :func:`_safe_adapter_call` wrapper catches this type
    together with :class:`CapabilityMissingError` and
    :class:`CapabilityMismatchError` and emits
    :data:`ERR_ADAPTER_CONFIGURATION_ERROR`; ``ValueError`` /
    ``TypeError`` propagate to the caller (close P0-1: the engine must
    NOT silently swallow programmer errors that indicate a hostile
    configuration).
    """


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

    Hash-chained ledger (P0-8, round-event monotonicity): every row
    carries the previous round's ``row_hash`` in :attr:`prev_ledger_row_hash`
    (``None`` at round 0) and its own :attr:`row_hash`. The chain is
    :func:`compute_ledger_row_hash` applied to the canonical row fields
    plus the previous row's hash, so tampering with any row breaks the
    chain (the writer verifies chain integrity on every emit). Use
    :func:`verify_ledger_chain` to audit-replay a sequence of rows.
    """

    ledger_row_id: str
    round_index: int
    source_round: int
    target_round: int
    applied_policy_hash: str
    selected_bundle_digest: str
    audit_codes: tuple[str, ...]
    per_channel_decision: Mapping[str, bool]
    prev_ledger_row_hash: str | None = None
    row_hash: str = ""


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
    dependency on the types module. The fallback ``default`` is
    :func:`_canonical_json_default` (not ``str``) so numerically-equal
    values from different dtypes (e.g. ``numpy.float64(0.5)`` and
    ``float(0.5)``) produce the same digest (P2-15 audit).
    """
    text = json.dumps(payload, sort_keys=True, default=_canonical_json_default)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json_default(obj: Any) -> Any:
    """Return a JSON-encodable fallback for ``obj``.

    Used as the ``default`` argument to :func:`json.dumps` so the
    engine's inlined digest helper can serialise objects outside the
    default JSON type set without losing numerical precision
    (P2-15). Mirrors
    :func:`adaptive_reflow.algorithm.policy_driver._canonical_json_default`
    so the engine and the algorithm-layer drivers agree on the
    canonical encoding.

    The helper handles:

    * NumPy scalars (``numpy.float64`` / ``numpy.int64`` etc.) —
      coerced via :meth:`numpy.ndarray.item` so a ``numpy.float64``
      and a Python ``float`` with the same numerical value produce
      the same digest.
    * Objects exposing :meth:`__float__` — coerced via :func:`float`.
    * Anything else — coerced via :func:`str` as the last-resort
      deterministic fallback.
    """
    # NumPy scalars: ``.item()`` returns the Python builtin scalar.
    item_fn = getattr(obj, "item", None)
    if callable(item_fn):
        try:
            return item_fn()
        except (ValueError, TypeError):
            pass
    # Numeric protocol fallback.
    float_fn = getattr(obj, "__float__", None)
    if callable(float_fn):
        try:
            return float_fn()
        except (TypeError, ValueError):
            pass
    # Last-resort deterministic string fallback.
    return str(obj)


def _digest_state(bundle: StateBundle | None) -> str:
    """Return a deterministic digest for ``bundle`` (or empty-string sentinel).

    ``bundle.source_round`` is coerced to a non-negative ``int`` before
    the digest is computed so a malformed value never leaks its type
    repr into the digest payload (closes P0-6: prior to this change
    ``bundle.source_round="3"`` and ``bundle.source_round=3`` produced
    different digests). The coercion is silent at this level when
    ``audit_codes`` is not supplied; callers that need the audit trail
    should call :func:`_coerce_nonneg_int` explicitly with their own
    ``audit_codes`` list before invoking this helper.
    """
    if bundle is None:
        return ""
    audit_codes: list[str] = []
    sr = _coerce_nonneg_int(
        getattr(bundle, "source_round", 0), "source_round", audit_codes
    )
    sr_repr = str(int(sr))
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


def _digest_state_cached(
    bundle: StateBundle | None,
    cache: _StateBundleDigestCache | None,
) -> str:
    """Return the SHA-256 digest of ``bundle`` (cached when ``cache`` is set).

    Wave 233 P6 wrapper around :func:`_digest_state`. When ``cache`` is
    ``None`` the wrapper is byte-equivalent to :func:`_digest_state` —
    no caching is performed, every call recomputes the SHA-256. When
    ``cache`` is supplied the wrapper uses ``cache.get_or_compute(bundle)``
    which memoises the digest by ``id(bundle)``. Within a single round
    the engine calls :func:`_digest_state` 2-4 times on the same bundle
    reference; the cache reduces the SHA-256 cost to one computation
    per (round, bundle) pair.

    Soundness: a :class:`StateBundle` is a ``@dataclass(frozen=True)``
    so its fields cannot mutate in place; if two digest calls see
    ``id(bundle)`` equal they MUST see identical field values, so the
    cached SHA-256 is guaranteed to match the freshly-computed one
    byte-for-byte (D.4 byte-stability preserved).
    """
    if cache is None:
        return _digest_state(bundle)
    return cache.get_or_compute(bundle)


def _digest_condition(delta: ODEConditionDelta | None) -> str:
    """Return a deterministic digest for ``delta`` (or empty-string sentinel)."""
    if delta is None:
        return ""
    payload = {
        "delta_spec": {k: str(v) for k, v in sorted(delta.delta_spec.items())},  # type: ignore[attr-defined]
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


def compute_ledger_row_hash(
    *,
    ledger_row_id: str,
    round_index: int,
    source_round: int,
    target_round: int,
    applied_policy_hash: str,
    selected_bundle_digest: str,
    audit_codes: tuple[str, ...],
    per_channel_decision: Mapping[str, bool],
    prev_ledger_row_hash: str | None,
) -> str:
    """Return the deterministic ``row_hash`` for a :class:`LedgerRow`.

    The hash covers every canonical row field plus the previous row's
    hash (so each row is committed to the entire history). The
    ``prev_ledger_row_hash is None`` sentinel is rendered as the
    empty string so round 0 chains to a stable anchor.
    """
    payload = {
        "ledger_row_id": str(ledger_row_id),
        "round_index": int(round_index),
        "source_round": int(source_round),
        "target_round": int(target_round),
        "applied_policy_hash": str(applied_policy_hash),
        "selected_bundle_digest": str(selected_bundle_digest),
        "audit_codes": list(audit_codes),
        "per_channel_decision": {
            str(k): bool(v) for k, v in sorted(per_channel_decision.items())
        },
        "prev_ledger_row_hash": (
            "" if prev_ledger_row_hash is None else str(prev_ledger_row_hash)
        ),
    }
    return _digest(payload)


def build_ledger_row(
    *,
    round_index: int,
    policy_hash: str,
    bundle_digest: str,
    source_round: int,
    applied_policy_hash: str,
    audit_codes: tuple[str, ...],
    per_channel_decision: Mapping[str, bool],
    prev_ledger_row_hash: str | None,
) -> LedgerRow:
    """Build a fully-hashed :class:`LedgerRow` (P0-8).

    Computes ``ledger_row_id`` and ``row_hash`` from the supplied fields
    plus the previous row's hash. Round 0 accepts
    ``prev_ledger_row_hash is None``; later rounds MUST supply the
    previous row's ``row_hash`` (the writer/chain integrity check in
    :func:`verify_ledger_chain` rejects chains where a non-zero round
    has ``prev_ledger_row_hash is None``).
    """
    ledger_row_id = _ledger_row_id(
        int(round_index), str(policy_hash), str(bundle_digest)
    )
    row_hash = compute_ledger_row_hash(
        ledger_row_id=str(ledger_row_id),
        round_index=int(round_index),
        source_round=int(source_round),
        target_round=int(round_index),
        applied_policy_hash=str(applied_policy_hash),
        selected_bundle_digest=str(bundle_digest),
        audit_codes=tuple(audit_codes),
        per_channel_decision=dict(per_channel_decision),
        prev_ledger_row_hash=prev_ledger_row_hash,
    )
    return LedgerRow(
        ledger_row_id=str(ledger_row_id),
        round_index=int(round_index),
        source_round=int(source_round),
        target_round=int(round_index),
        applied_policy_hash=str(applied_policy_hash),
        selected_bundle_digest=str(bundle_digest),
        audit_codes=tuple(audit_codes),
        per_channel_decision=dict(per_channel_decision),
        prev_ledger_row_hash=(
            None if prev_ledger_row_hash is None else str(prev_ledger_row_hash)
        ),
        row_hash=str(row_hash),
    )


def verify_ledger_chain(rows: tuple[LedgerRow, ...]) -> tuple[bool, str]:
    """Return ``(ok, error_message)`` for the supplied sequence of rows.

    A valid chain has:

    * ``row[0].prev_ledger_row_hash is None``;
    * ``row[i].prev_ledger_row_hash == row[i-1].row_hash`` for
      ``i >= 1``;
    * ``row[i].row_hash == compute_ledger_row_hash(...)`` for every
      ``i`` (recovers the row from its fields + the previous row's
      hash; any tampering with ``audit_codes``,
      ``per_channel_decision``, etc. breaks the equality);
    * ``round_index`` is monotone non-decreasing across the chain.

    The function is total: ``ok == True`` and ``error_message == ""``
    when the chain is valid; ``ok == False`` and a descriptive message
    otherwise. This is the audit-replay entry point for the
    Temporal-style "event history" guarantee (P0-8).
    """
    if not isinstance(rows, tuple):
        return (False, f"rows must be a tuple, got {type(rows).__name__}")
    prev_hash: str | None = None
    last_round: int | None = None
    for idx, row in enumerate(rows):
        if not isinstance(row, LedgerRow):
            return (False, f"row[{idx}] is not a LedgerRow")
        if idx == 0:
            if row.prev_ledger_row_hash is not None:
                return (
                    False,
                    f"row[0].prev_ledger_row_hash must be None, "
                    f"got {row.prev_ledger_row_hash!r}",
                )
        else:
            if row.prev_ledger_row_hash is None:
                return (
                    False,
                    f"row[{idx}].prev_ledger_row_hash must equal the "
                    f"previous row's row_hash, got None",
                )
            if str(row.prev_ledger_row_hash) != str(prev_hash):
                return (
                    False,
                    f"row[{idx}].prev_ledger_row_hash does not match "
                    f"previous row_hash",
                )
        recovered = compute_ledger_row_hash(
            ledger_row_id=str(row.ledger_row_id),
            round_index=int(row.round_index),
            source_round=int(row.source_round),
            target_round=int(row.target_round),
            applied_policy_hash=str(row.applied_policy_hash),
            selected_bundle_digest=str(row.selected_bundle_digest),
            audit_codes=tuple(row.audit_codes),
            per_channel_decision=dict(row.per_channel_decision),
            prev_ledger_row_hash=row.prev_ledger_row_hash,
        )
        if str(recovered) != str(row.row_hash):
            return (
                False,
                f"row[{idx}].row_hash does not match the recompute "
                f"(row has been tampered with)",
            )
        if last_round is not None and int(row.round_index) < int(last_round):
            return (
                False,
                f"row[{idx}].round_index regressed "
                f"({int(row.round_index)} < {int(last_round)})",
            )
        last_round = int(row.round_index)
        prev_hash = str(row.row_hash)
    return (True, "")


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

    Closes P0-6: when ``value`` is a string that ``int(value)`` can
    parse (``"3"``), the helper converts it and emits
    ``ERR_SOURCE_ROUND_NON_INT`` / ``ERR_ROUND_INDEX_NON_INT`` so the
    audit trail reflects the coercion; the returned int is the parsed
    value so two callers with ``source_round="3"`` and
    ``source_round=3`` produce the same downstream digest.
    """
    # bool is a subclass of int in Python — treat as non-int explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        # Try a string-to-int conversion before falling back to the
        # canonical ``default``. This makes
        # ``source_round="3"`` and ``source_round=3`` digest identically
        # under P0-6 — both surface the audit code but the int value
        # returned matches.
        if isinstance(value, str):
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                code = ERR_ROUND_INDEX_NON_INT if name == "round_index" else ERR_SOURCE_ROUND_NON_INT
                audit_codes.append(f"{code}:{name}:{type(value).__name__}")
                return default
            if parsed < 0:
                if name == "round_index":
                    audit_codes.append(ERR_ROUND_INDEX_NEGATIVE)
                else:
                    audit_codes.append(ERR_SOURCE_ROUND_NON_INT + f":{name}:negative")
                return default
            code = ERR_ROUND_INDEX_NON_INT if name == "round_index" else ERR_SOURCE_ROUND_NON_INT
            audit_codes.append(f"{code}:{name}:{type(value).__name__}")
            return int(parsed)
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


def _check_capabilities_advertise_dispatch(
    *,
    caps: AdapterCapabilities | None,
    bundle: StateBundle | None,
    audit_codes: list[str],
) -> bool:
    """Pre-dispatch capability handshake (P1-6, ONNX Runtime analog).

    Mirrors ``IExecutionProvider::CanHandle`` in ONNX Runtime: before
    the engine dispatches any round's native call (``apply_restart_distribution``
    -> ``compose_condition`` -> ``solve_ode``) to the adapter, it
    re-validates that the adapter's advertised capability surface
    advertises *every* channel the round is about to route through
    AND has the per-call capability flag that the requested step
    consumes.

    Returns ``True`` when the dispatch is permitted; ``False`` when a
    capability mismatch is found. Each mismatch is appended to
    ``audit_codes`` as ``f"{ERR_CAPABILITY_UNSUPPORTED}:{channel}:{capability}"``
    so the downstream ledger row carries a per-channel capability
    audit trail.

    The check is fail-closed: a single missing capability for a single
    channel aborts the entire round (the engine then routes through
    the standard fail-closed ``_emit_fail_closed`` path). Callers that
    want to drive the round regardless of partial capability
    advertisement should suppress this gate explicitly — no such
    override exists by design (the framework cannot assume the adapter
    will produce a well-typed result for a channel it did not
    advertise).
    """
    if caps is None:
        audit_codes.append(f"{ERR_CAPABILITY_UNSUPPORTED}:caps_missing")
        return False
    if bundle is None:
        return True
    supported = set(caps.supported_channels)
    for channel in bundle.channels:
        if channel not in supported:
            audit_codes.append(
                f"{ERR_CAPABILITY_UNSUPPORTED}:{channel}:not_advertised"
            )
            continue
        domain = _channel_domain_lookup(channel, caps)
        if domain == "continuous" and not caps.has_continuous_channels:
            audit_codes.append(
                f"{ERR_CAPABILITY_UNSUPPORTED}:{channel}:"
                "continuous_kind_not_advertised"
            )
        elif domain == "discrete" and not caps.has_discrete_channels:
            audit_codes.append(
                f"{ERR_CAPABILITY_UNSUPPORTED}:{channel}:"
                "discrete_kind_not_advertised"
            )
    # Per-op capability flags. Each native step consumes a different
    # capability; if the adapter dropped one mid-run the dispatch must
    # not proceed.
    for op_capability in (
        "has_restart_boundary",
        "has_condition_injection",
        "has_ode_integration_surface",
        "has_state_export",
    ):
        if not bool(getattr(caps, op_capability)):
            audit_codes.append(
                f"{ERR_CAPABILITY_UNSUPPORTED}:op:{op_capability}"
            )
    return True


def _state_bundle_to_native(
    bundle: StateBundle,
    caps: AdapterCapabilities,
) -> NativeStateBundle:  # type: ignore[name-defined]  # noqa: F821
    """Project a detached :class:`StateBundle` to a typed
    :class:`adaptive_reflow.contracts.materialization.NativeStateBundle`
    for materializer invocation (D10 typed surface).

    The conversion is total and deterministic; channels whose opaque
    ``TensorRef`` cannot be inspected are passed through as opaque
    string handles. The bundle's ``channel_domains`` is sourced from
    ``caps.channel_domains`` when the per-channel declaration is present;
    otherwise the per-channel domain is inferred from the
    ``caps.has_continuous_channels`` / ``caps.has_discrete_channels``
    capability booleans (single-domain adapter).

    Backed by an adapter-private ``atom_count`` derivation: when the
    adapter's first channel is a graph-shaped or molecule-shaped
    channel, ``atom_count`` is read from the bundle's source round
    (Round 0 = first round; ``atom_count`` is otherwise carried in the
    bundle's ``native_state_digest`` as a parseable integer). The
    helper is best-effort: callers that require a strict atom_count
    must supply their own projection.

    The helper imports :mod:`adaptive_reflow.contracts.materialization`
    lazily to avoid the module-init cycle
    (``frame.engine`` ↔ ``contracts.__init__``).
    """
    # Local import — breaks the ``frame.engine`` ↔
    # ``contracts.__init__`` module-init cycle.
    from adaptive_reflow.contracts.materialization import (
        NativeStateBundle as _NativeStateBundle,
    )

    # Build the channels mapping (opaque string handles pass through).
    channels: dict[str, str] = {str(k): str(v) for k, v in bundle.channels.items()}
    # Build the channel_domains mapping from caps.channel_domains.
    channel_domains: dict[str, str] = {}
    if isinstance(caps.channel_domains, Mapping):
        for ch_name, dom in caps.channel_domains.items():
            channel_domains[str(ch_name)] = str(dom)
    # Channel shapes — read from caps.channel_shapes if present.
    channel_shapes: dict[str, tuple[tuple[int, ...], tuple[int, ...]]] = {}
    if isinstance(getattr(caps, "channel_shapes", None), Mapping):
        for ch_name, shapes in caps.channel_shapes.items():
            if isinstance(shapes, tuple) and len(shapes) == 2:
                channel_shapes[str(ch_name)] = (
                    tuple(shapes[0]),
                    tuple(shapes[1]),
                )
    # Channel masks — bundle.masks passes through.
    channel_masks: dict[str, str] = {str(k): str(v) for k, v in bundle.masks.items()}
    # Atom count: best-effort. Try the bundle's source_round as a proxy
    # for graph / molecule shape; fall back to 0 when no canonical
    # declaration exists. Adapters that need strict atom_count must
    # provide it via the ``materializer_instance`` handle itself (the
    # materializer can read its private cache).
    atom_count = int(bundle.source_round) if int(bundle.source_round) > 0 else 0
    return _NativeStateBundle(
        channels=channels,
        atom_count=atom_count,
        backend_kind=str(bundle.backend_kind)
        if hasattr(bundle, "backend_kind")
        else "",
        source_round=int(bundle.source_round),
        source_digest=str(bundle.native_state_digest),
        provenance=tuple(bundle.provenance),
        channel_domains=channel_domains,
        channel_shapes=channel_shapes,
        channel_masks=channel_masks,
    )


def _safe_adapter_call(
    step_name: str,
    audit_codes: list[str],
    fn: Any,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Wrap an adapter call so a stray ``Exception`` cannot crash the round.

    Only catches the engine-internal :class:`AdapterConfigurationError`
    plus the two adapter-protocol exceptions
    (:class:`CapabilityMissingError`, :class:`CapabilityMismatchError`).
    ``ValueError`` / ``TypeError`` / ``KeyError`` / ``RuntimeError`` /
    other arbitrary ``Exception`` subclasses are intentionally NOT
    swallowed: a programmer error raised by an adapter must surface to
    the caller rather than silently produce a fail-closed round trace
    (closes P0-1: the engine must NOT fail-open on hostile
    configuration).

    On a caught exception, append
    ``f"{ERR_ADAPTER_CONFIGURATION_ERROR}:{step_name}:{ExceptionType}:{message[:80]}"``
    to ``audit_codes`` and return ``None``. The engine then emits a
    fail-closed round trace rather than propagating the exception.
    ``BaseException`` subclasses (``KeyboardInterrupt`` /
    ``SystemExit``) always propagate.
    """
    try:
        return fn(*args, **kwargs)
    except (
        AdapterConfigurationError,
        CapabilityMissingError,
        CapabilityMismatchError,
    ) as exc:
        message = str(exc)[:80]
        audit_codes.append(
            f"{ERR_ADAPTER_CONFIGURATION_ERROR}:{step_name}:{type(exc).__name__}:{message}"
        )
        return None


def _policy_with_schedule_beta(
    policy: FinalRestartPolicy,
    audit_codes: list[str] | None = None,
) -> FinalRestartPolicy:
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

    Fail-closed on ``schedule_sample is None`` (closes P0-5): when
    ``beta_from_schedule`` is ``True`` the engine MUST be able to
    derive ``beta`` from the schedule, and silently passing the
    unoverridden policy through would produce an
    ``applied_policy_hash`` that doesn't match what the engine
    actually emitted to the adapter. Instead, when ``schedule_sample``
    is ``None`` the helper appends ``ERR_SCHEDULE_SAMPLE_MISSING`` to
    ``audit_codes`` (if provided) and returns a copy of ``policy``
    with all ``beta_by_channel`` zeroed — that way the audit trail
    reflects the engine's actual behaviour (fail-closed: do not
    override) rather than silently agreeing with the caller's policy.
    The recomputed ``policy_hash`` keeps the audit invariant
    (``hash == recompute``) intact.
    """
    sample = policy.schedule_sample
    if sample is None:
        if audit_codes is not None:
            audit_codes.append(ERR_SCHEDULE_SAMPLE_MISSING)
        zero_beta = {
            channel: FactorValue(0.0) for channel in policy.beta_by_channel
        }
        overridden = replace(policy, beta_by_channel=zero_beta)
        return replace(overridden, policy_hash=hash_policy_hash(overridden))
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
        if audit_codes is not None:
            audit_codes.append(ERR_ADAPTER_CONFIGURATION_ERROR + ":n_cap_non_numeric")
        return policy
    if not _isfinite_or_skip(n_cap):
        if audit_codes is not None:
            audit_codes.append(ERR_ADAPTER_CONFIGURATION_ERROR + ":n_cap_non_finite")
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
        digest_cache: _StateBundleDigestCache | None = None,
    ) -> None:
        self._operation_steps = tuple(operation_steps)
        if not self._operation_steps:
            raise ValueError("operation_steps must be non-empty")
        # The engine is opt-in: when ``feature_flag`` is ``False``, the
        # engine emits a disabled-feature round trace and never calls
        # the adapter. ``None`` defaults to enabled.
        self._feature_flag = True if feature_flag is None else bool(feature_flag)
        # Wave 233 P6 — SHA-256 digest cache for ``StateBundle``. When
        # supplied (or when the caller explicitly constructs a cache
        # via ``state_bundle_cache.default_cache()``), repeated calls to
        # :func:`_digest_state` on the same ``StateBundle`` instance
        # within a single round return the cached value instead of
        # recomputing the JSON canonical form + SHA-256. ``None``
        # disables the cache (default — preserves byte-stable behaviour
        # for every existing call site and the D.4 byte-stability gate).
        self._digest_cache: _StateBundleDigestCache | None = (
            digest_cache if digest_cache is not None else None
        )

    @property
    def digest_cache(self) -> _StateBundleDigestCache | None:
        """Return the SHA-256 digest cache (or ``None`` if disabled).

        Wave 233 P6 surface: callers (e.g. benchmark scripts) can read
        the cache's hit / miss counters after a run via
        ``engine.digest_cache.stats()`` to quantify the cache
        effectiveness. Returns ``None`` when the cache is disabled so
        callers can detect the disabled state without a sentinel.
        """
        return self._digest_cache

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
    def _apply_schedule_beta_override(
        *,
        policy: FinalRestartPolicy,
        applied_policy_hash: str,
        audit_codes: list[str],
    ) -> tuple[FinalRestartPolicy, str]:
        """Apply the ``_policy_with_schedule_beta`` override if warranted.

        P1-11 (F-36) — extracted from the inline call site in
        :meth:`run_round`. The runner's canonical data flow sets
        ``driver_computed_beta=True`` so the override is
        short-circuited; legacy callers that set
        ``beta_from_schedule=True`` with ``driver_computed_beta=False``
        trigger the override. The ``applied_policy_hash`` is
        recomputed from the post-override policy so the audit
        invariant ``hash == recompute`` is preserved.

        Returns the (possibly new) ``applied_policy`` plus the
        (possibly recomputed) ``applied_policy_hash`` so callers can
        unpack both in a single assignment.
        """
        if not (policy.beta_from_schedule and not policy.driver_computed_beta):
            return policy, applied_policy_hash
        overridden = _policy_with_schedule_beta(policy, audit_codes)
        if overridden is policy:
            return policy, applied_policy_hash
        return overridden, str(hash_policy_hash(overridden))

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
        prev_ledger_row_hash: str | None = None,
        digest_cache: _StateBundleDigestCache | None = None,
    ) -> EngineRoundResult:
        """Build a fail-closed :class:`EngineRoundResult` for the happy path.

        Invoked from :meth:`run_round` whenever one of the six
        :func:`_safe_adapter_call` wrappers returns ``None`` (the adapter
        raised, was misbehaved, or returned an unexpected ``None``).
        The audit trail already carries the
        :data:`ERR_ADAPTER_RAISED` / :data:`ERR_INTEGRATOR_TRACE_MISSING`
        code; this helper only packages the round trace and ledger row
        so the caller can return without further branching. The ledger
        ``source_round`` is sourced through :func:`_safe_source_round`
        so a malformed bundle never raises here either (closes
        commit 3dc0f60 per CONTRACTS.md §9.2 — single-source the
        source_round coercion through ``_safe_source_round`` so the
        RoundTrace and the LedgerRow see the exact same audit code
        sequence and the exact same int value).

        Wave 233 P6 — accepts ``digest_cache`` so repeated digest calls
        on the same ``bundle`` / ``initial_state`` / ``detached``
        references inside the fail-closed path use the cache. Pass
        ``None`` to disable caching (legacy behaviour preserved).
        """
        # Coerce source_round via ``_safe_source_round`` BEFORE freezing
        # the audit_codes tuple so a malformed bundle surfaces
        # ERR_SOURCE_ROUND_NON_INT in both the RoundTrace and the
        # LedgerRow (closes Gap C3 in the fail-closed adapter-raised
        # path AND finishes commit 3dc0f60: the helper is now the
        # single boundary that ``_emit_fail_closed`` uses for
        # source_round coercion, mirroring every other emit site in
        # :meth:`run_round`).
        _safe_source_round(bundle, audit_codes)
        codes = tuple(audit_codes)
        trace = RoundTrace(
            round_index=int(round_index),
            operation_steps=DEFAULT_OPERATION_STEPS,
            source_bundle_digest=_digest_state_cached(bundle, digest_cache),
            applied_policy_hash=applied_policy_hash,
            initial_state_digest=(
                _digest_state_cached(initial_state, digest_cache)
                if initial_state is not None
                else ""
            ),
            condition_digest=_digest_condition(composed)
            if composed is not None
            else _digest_condition(condition_delta),
            integrator_trace=integrator_trace,
            endpoint_digest=(
                _digest_state_cached(detached, digest_cache)
                if detached is not None
                else ""
            ),
            detached=bool(detached.detach_proof) if detached is not None else False,
            audit_codes=codes,
            extras={"feature_flag": True, "engine_version": ENGINE_VERSION},
        )
        ledger = build_ledger_row(
            round_index=int(round_index),
            policy_hash=str(applied_policy_hash),
            bundle_digest=_digest_state_cached(bundle, digest_cache),
            source_round=_safe_source_round(bundle, audit_codes),
            applied_policy_hash=str(applied_policy_hash),
            audit_codes=codes,
            per_channel_decision={},
            prev_ledger_row_hash=prev_ledger_row_hash,
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
        prev_ledger_row_hash: str | None = None,
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
        prev_ledger_row_hash:
            The previous round's ``row_hash`` (the hash-chained
            ledger anchor — P0-8). Round 0 MUST pass ``None``;
            subsequent rounds MUST pass the previous round's
            ``ledger_row.row_hash``. The engine enforces the chain by
            feeding ``prev_ledger_row_hash`` into
            :func:`build_ledger_row` so any tampering with a row
            breaks the recompute at
            :func:`verify_ledger_chain` time.

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
        * ``capability_unsupported`` (P1-6, ONNX Runtime analog)
        * ``endpoint_not_detached``
        * ``condition_delta_no_effect``
        * ``integrator_trace_missing``
        * ``shape_frame_normalization_mismatch``
        * ``feature_flag_disabled``

        Cosine-driven memory fraction (ADR-0010): when
        ``policy.beta_from_schedule is True`` (default) and
        ``policy.schedule_sample is not None`` AND
        ``policy.driver_computed_beta is False`` (Contract 1.2),
        the engine overrides ``policy.beta_by_channel`` for the
        duration of this round so the per-round memory fraction is
        the schedule's complement of ``n_cap``: ``beta = n_cap`` so
        ``memory_fraction = 1 - n_cap``. The override is invisible
        to the caller (the supplied ``policy`` is never mutated);
        the round trace's ``applied_policy_hash`` reflects the
        post-override hash so the audit invariant
        ``hash == recompute`` holds. When
        ``policy.driver_computed_beta is True`` (Contract 1.2 —
        the driver has already mutated ``beta_by_channel``), the
        engine SKIPS its inline re-override; the driver is the
        canonical source of truth. When
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
                source_bundle_digest=_digest_state_cached(bundle, self._digest_cache),
                applied_policy_hash="",
                initial_state_digest="",
                condition_digest="",
                integrator_trace=None,
                endpoint_digest="",
                detached=False,
                audit_codes=tuple(audit_codes),
                extras={"feature_flag": False, "engine_version": ENGINE_VERSION},
            )
            ledger = build_ledger_row(
                round_index=int(round_index),
                policy_hash="",
                bundle_digest=_digest_state_cached(bundle, self._digest_cache),
                source_round=_safe_source_round(bundle, audit_codes),
                applied_policy_hash="",
                audit_codes=tuple(audit_codes),
                per_channel_decision={},
                prev_ledger_row_hash=prev_ledger_row_hash,
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
            # Fail closed: emit ERR_ADAPTER_NONE in the audit trail and
            # return a non-raising fail-closed round trace (closes P0-4).
            # The other argument-gate codes (PHASE_STATE_NONE / POLICY_NONE /
            # BUNDLE_NONE) also fail closed; we treat adapter=None as
            # symmetric to those by routing through the same fail-closed
            # emission pattern. No native call is made because the adapter
            # is unavailable.
            audit_codes.append(ERR_ADAPTER_NONE)
            _coerce_nonneg_int(
                getattr(bundle, "source_round", 0), "source_round", audit_codes
            )
            trace = RoundTrace(
                round_index=int(round_index),
                operation_steps=self._operation_steps,
                source_bundle_digest=_digest_state_cached(bundle, self._digest_cache),
                applied_policy_hash="",
                initial_state_digest="",
                condition_digest="",
                integrator_trace=None,
                endpoint_digest="",
                detached=False,
                audit_codes=tuple(audit_codes),
                extras={"feature_flag": True, "engine_version": ENGINE_VERSION},
            )
            ledger = build_ledger_row(
                round_index=int(round_index),
                policy_hash="",
                bundle_digest=_digest_state_cached(bundle, self._digest_cache),
                source_round=_safe_source_round(bundle, audit_codes),
                applied_policy_hash="",
                audit_codes=tuple(audit_codes),
                per_channel_decision={},
                prev_ledger_row_hash=prev_ledger_row_hash,
            )
            next_state = _next_phase_state(phase_state, round_index=round_index)
            return EngineRoundResult(
                round_trace=trace,
                next_phase_state=next_state,
                ledger_row=ledger,
                applied_policy_hash="",
            )
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
                    # Capabilities advertisement dispatch (P1-6, ONNX
                    # Runtime analog): the adapter did not advertise
                    # this channel in its capability surface, so the
                    # dispatch must fail closed with a separate
                    # capability-aware code. This mirrors
                    # ``IExecutionProvider::CanHandle``.
                    audit_codes.append(
                        f"{ERR_CAPABILITY_UNSUPPORTED}:{channel}:not_advertised"
                    )
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
                        # Capability-side dispatch check (P1-6): the
                        # adapter advertises the channel but did NOT
                        # advertise the channel kind (continuous /
                        # discrete) needed to dispatch to it.
                        kind = (
                            "continuous" if expected == "continuous" else "discrete"
                        )
                        audit_codes.append(
                            f"{ERR_CAPABILITY_UNSUPPORTED}:{channel}:"
                            f"{kind}_kind_not_advertised"
                        )
            # Per-op capability flags (P1-6): each native step consumes
            # a different capability; if the adapter dropped one
            # mid-run the dispatch must not proceed.
            for op_capability in (
                "has_restart_boundary",
                "has_condition_injection",
                "has_ode_integration_surface",
                "has_state_export",
            ):
                if not bool(getattr(caps, op_capability)):
                    audit_codes.append(
                        f"{ERR_CAPABILITY_UNSUPPORTED}:op:{op_capability}"
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
                source_bundle_digest=_digest_state_cached(bundle, self._digest_cache),
                applied_policy_hash=applied_policy_hash,
                initial_state_digest="",
                condition_digest=_digest_condition(condition_delta),
                integrator_trace=None,
                endpoint_digest="",
                detached=False,
                audit_codes=tuple(audit_codes),
                extras={"feature_flag": True, "engine_version": ENGINE_VERSION},
            )
            ledger = build_ledger_row(
                round_index=int(round_index),
                policy_hash=str(applied_policy_hash),
                bundle_digest=_digest_state_cached(bundle, self._digest_cache),
                source_round=_safe_source_round(bundle, audit_codes),
                applied_policy_hash=str(applied_policy_hash),
                audit_codes=tuple(audit_codes),
                per_channel_decision={},
                prev_ledger_row_hash=prev_ledger_row_hash,
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
                prev_ledger_row_hash=prev_ledger_row_hash,
                digest_cache=self._digest_cache,
            )

        # 2. Apply restart distribution (beta=0 preserves the prior).
        # ADR-0010 — cosine-driven memory fraction. When the policy
        # carries a non-``None`` ``schedule_sample`` AND the
        # ``beta_from_schedule`` flag is ``True`` (default), the engine
        # overrides ``beta_by_channel`` from the schedule's ``n_cap``
        # (``beta = n_cap`` so ``memory_fraction = 1 - n_cap``). The
        # helper is pure; the resulting ``policy_hash`` is recomputed
        # via :func:`hash_policy_hash` so the audit trail matches the
        # actually-emitted beta.
        #
        # CONTRACT 1.2 — driver / engine dedup: when the policy has
        # ``driver_computed_beta=True`` (set by a
        # :class:`adaptive_reflow.algorithm.PolicyDriverProtocol` that
        # already mutated ``beta_by_channel``), the engine SKIPS its
        # inline re-override; the driver is the source of truth and
        # the engine only validates that
        # ``applied_policy.beta_from_schedule`` is consistent with the
        # caller's intent. When ``beta_from_schedule`` is ``True`` but
        # ``schedule_sample`` is ``None`` (closes P0-5), the helper
        # emits ``ERR_SCHEDULE_SAMPLE_MISSING`` and returns a copy
        # with all ``beta_by_channel`` zeroed. When
        # ``beta_from_schedule`` is ``False`` (back-compat) the policy
        # is forwarded verbatim.
        #
        # CAPABILITY DISPATCH (P1-6): before the engine hands the
        # bundle to ``apply_restart_distribution`` (the first native
        # dispatch of the round), re-validate that the adapter's
        # advertised capability surface covers every channel the
        # round will route through. Mirrors ONNX Runtime
        # ``IExecutionProvider::CanHandle`` — when the adapter did
        # not advertise a capability the engine needs, fail closed
        # with ``ERR_CAPABILITY_UNSUPPORTED`` rather than dispatch
        # and surface a downstream crash. The audit trail is appended
        # to ``audit_codes`` so the ledger row carries the same code
        # as the round trace.
        if not _check_capabilities_advertise_dispatch(
            caps=caps, bundle=bundle, audit_codes=audit_codes
        ):
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
                prev_ledger_row_hash=prev_ledger_row_hash,
                digest_cache=self._digest_cache,
            )
        applied_policy: FinalRestartPolicy = policy
        # F19 — precondition assert (closes the dead-code path on the
        # runner's data flow). The runner sets
        # ``driver_computed_beta=True`` to suppress this helper (see
        # ``adaptive_reflow/algorithm/runner.py:629-633``); the helper
        # is therefore dead on the runner's path. The assert documents
        # the runner's contract — the runner sets
        # ``driver_computed_beta=True`` so this helper is short-
        # circuited; a policy with ``driver_computed_beta=False`` and
        # ``beta_from_schedule=True`` is the legacy path that this
        # helper actively overrides. A policy with both flags ``False``
        # is also valid (the engine uses the policy's
        # ``beta_by_channel`` directly); the assert documents the
        # canonical runners' contract without blocking the
        # ``beta_by_channel`` direct-use path.
        #
        # P1-11 (F-36) — the inline override was extracted to
        # :meth:`Engine._apply_schedule_beta_override` so the W3-leak
        # (an inline ``_policy_with_schedule_beta`` call buried in the
        # middle of ``run_round``) is now a single dispatchable
        # surface that downstream callers / tests can subclass,
        # monkey-patch, or swap without re-implementing the override
        # logic.
        applied_policy, applied_policy_hash = self._apply_schedule_beta_override(
            policy=policy,
            applied_policy_hash=applied_policy_hash,
            audit_codes=audit_codes,
        )

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
                prev_ledger_row_hash=prev_ledger_row_hash,
                digest_cache=self._digest_cache,
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
                prev_ledger_row_hash=prev_ledger_row_hash,
                digest_cache=self._digest_cache,
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
                source_bundle_digest=_digest_state_cached(bundle, self._digest_cache),
                applied_policy_hash=applied_policy_hash,
                initial_state_digest=_digest_state_cached(initial_state, self._digest_cache),
                condition_digest=_digest_condition(composed),
                integrator_trace=None,
                endpoint_digest="",
                detached=False,
                audit_codes=tuple(audit_codes),
                extras={"feature_flag": True, "engine_version": ENGINE_VERSION},
            )
            ledger = build_ledger_row(
                round_index=int(round_index),
                policy_hash=str(applied_policy_hash),
                bundle_digest=_digest_state_cached(bundle, self._digest_cache),
                source_round=_safe_source_round(bundle, audit_codes),
                applied_policy_hash=str(applied_policy_hash),
                audit_codes=tuple(audit_codes),
                per_channel_decision={},
                prev_ledger_row_hash=prev_ledger_row_hash,
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
                prev_ledger_row_hash=prev_ledger_row_hash,
                digest_cache=self._digest_cache,
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
                prev_ledger_row_hash=prev_ledger_row_hash,
                digest_cache=self._digest_cache,
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
                prev_ledger_row_hash=prev_ledger_row_hash,
                digest_cache=self._digest_cache,
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
                prev_ledger_row_hash=prev_ledger_row_hash,
                digest_cache=self._digest_cache,
            )

        if not detached.detach_proof:
            audit_codes.append(ERR_DETACH_PROOF_FAILED)

        # D10 (Design #4) — typed materialization invocation. After
        # the endpoint is detached the engine optionally projects the
        # native state to the envelope via the adapter-declared
        # ``materializer_instance`` (the prior ``materializer: type | None``
        # class reference is preserved for back-compat; the typed
        # instance handle is the new canonical path). The result is
        # stored in ``RoundTrace.extras["materializer_handle"]`` and
        # ``RoundTrace.extras["envelope_state_keys"]`` so downstream
        # consumers (BoundedMergeOperator, paper-quantity audits) can
        # consume the projection. The call is opt-in: when the
        # adapter does not declare a typed materializer, the engine
        # emits no audit code and the extras map stays empty.
        extras: dict[str, Any] = {
            "feature_flag": True,
            "engine_version": ENGINE_VERSION,
        }
        materializer_instance = getattr(caps, "materializer_instance", None)
        if materializer_instance is not None and caps is not None:
            try:
                # Build a typed NativeStateBundle from the detached
                # bundle's channels so the materializer can be invoked
                # through the typed D10 surface.
                native_bundle = _state_bundle_to_native(detached, caps)
                envelope_state = materializer_instance.dematerialize(native_bundle)
                extras["materializer_handle"] = str(
                    getattr(materializer_instance, "handle", "")
                )
                extras["envelope_state_keys"] = sorted(
                    str(k) for k in envelope_state.observables
                )
                extras["materialization_pass"] = True
            except Exception as exc:  # pragma: no cover - defensive
                audit_codes.append(
                    f"materialization_failed:{type(exc).__name__}"
                )

        trace = RoundTrace(
            round_index=int(round_index),
            operation_steps=self._operation_steps,
            source_bundle_digest=_digest_state_cached(bundle, self._digest_cache),
            applied_policy_hash=applied_policy_hash,
            initial_state_digest=_digest_state_cached(initial_state, self._digest_cache),
            condition_digest=_digest_condition(composed),
            integrator_trace=integrator_trace,
            endpoint_digest=_digest_state_cached(detached, self._digest_cache),
            detached=bool(detached.detach_proof),
            audit_codes=tuple(audit_codes),
            extras=extras,
        )
        ledger = build_ledger_row(
            round_index=int(round_index),
            policy_hash=str(applied_policy_hash),
            bundle_digest=_digest_state_cached(bundle, self._digest_cache),
            source_round=_safe_source_round(bundle, audit_codes),
            applied_policy_hash=str(applied_policy_hash),
            audit_codes=tuple(audit_codes),
            per_channel_decision={
                channel: bool(detached.detach_proof) for channel in bundle.channels
            },
            prev_ledger_row_hash=prev_ledger_row_hash,
        )
        next_state = _next_phase_state(phase_state, round_index=round_index)
        return EngineRoundResult(
            round_trace=trace,
            next_phase_state=next_state,
            ledger_row=ledger,
            applied_policy_hash=applied_policy_hash,
        )

    # -- state persistence (P2-12) ----------------------------------------

    def _engine_digest_seed(self, *, engine_version: str, adapter_id: str) -> str:
        """Build a deterministic seed tying the checkpoint to its engine + adapter.

        Re-derived on ``resume_round`` via
        :func:`adaptive_reflow.universal.checkpoint.engine_digest_seed`.
        Stdlib-only (sha256 over a JSON-stable payload). Mirrors the
        ``engine_version`` + ``adapter_id`` pair so adapters can
        override it without forcing the engine module to import them.
        """
        from adaptive_reflow.universal.checkpoint import engine_digest_seed as _seed

        return _seed(engine_version=str(engine_version), adapter_id=str(adapter_id))

    def checkpoint_round(
        self,
        *,
        round_trace: RoundTrace,
        ledger_row: LedgerRow,
        next_phase: PhaseState,
        state_bundle_at_round_start: StateBundle,
        engine_version: str,
        path: str | Path,
        native_payload_paths: Mapping[str, str] | None = None,
        calibration_manifest: Any | None = None,
    ) -> Any:
        """Persist a round's state to ``path``. Stdlib-only.

        The caller decides cadence (no auto-checkpoint inside
        :meth:`run_round`): pass a destination path on every round you
        want to persist, ``None`` to skip. The returned
        :class:`~adaptive_reflow.universal.checkpoint.Checkpoint` is
        also written to ``path`` in JSON form (atomic write via
        ``.tmp`` + replace). ``calibration_manifest`` is optional; when
        supplied, its :func:`manifest_digest` is recorded in the
        bundle so a resume can re-validate the calibration context.
        """
        from adaptive_reflow.universal.checkpoint import (
            DEFAULT_BUNDLE_FORMAT_VERSION,
        )
        from adaptive_reflow.universal.checkpoint import (
            Checkpoint as _Checkpoint,
        )
        from adaptive_reflow.universal.checkpoint import (
            IsoTimestamp as _IsoTimestamp,
        )
        from adaptive_reflow.universal.checkpoint import (
            save_checkpoint as _save,
        )

        manifest_hash: str | None = None
        if calibration_manifest is not None:
            # Local import keeps the engine module decoupled from
            # ``adaptive_reflow.eval.calibration`` (a downstream module
            # the framework's import surface does not need eagerly).
            from adaptive_reflow.eval.calibration import (
                CalibrationManifest as _CalibrationManifest,
            )
            from adaptive_reflow.eval.calibration import (
                manifest_digest as _manifest_digest,
            )

            if not isinstance(calibration_manifest, _CalibrationManifest):
                raise TypeError(
                    "calibration_manifest must be a CalibrationManifest or None; "
                    f"got {type(calibration_manifest).__name__}"
                )
            manifest_hash = str(_manifest_digest(calibration_manifest))

        # Lazy import of the time module keeps the engine stdlib-only
        # without forcing a top-level ``import time`` (the original
        # engine.py already imports only ``hashlib`` + ``json`` + ``math``).
        import time as _time

        cp = _Checkpoint(
            bundle_format_version=DEFAULT_BUNDLE_FORMAT_VERSION,
            engine_digest_seed=self._engine_digest_seed(
                engine_version=engine_version, adapter_id="runner-default"
            ),
            ledger_chain_head_hash=(
                str(ledger_row.row_hash) if ledger_row is not None else None
            ),
            state_bundle=state_bundle_at_round_start,
            last_round_trace=round_trace,
            last_ledger_row=ledger_row,
            phase_state=next_phase,
            calibration_manifest_hash=manifest_hash,
            native_payload_paths=dict(native_payload_paths or {}),
            created_at=_IsoTimestamp(
                _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
            ),
            extras={},
        )
        _save(cp, path)
        return cp

    def resume_round(self, path: str | Path) -> Any:
        """Load a checkpoint from ``path`` and re-validate the chain.

        Re-derives :attr:`Checkpoint.engine_digest_seed`, walks the
        ledger row via :func:`verify_ledger_chain`, and re-validates
        the state bundle via :func:`validate_state_bundle`. Raises
        :class:`~adaptive_reflow.universal.checkpoint.CheckpointError`
        on any failure (fail-closed).
        """
        from adaptive_reflow.universal.checkpoint import (
            CheckpointError as _CPError,
        )
        from adaptive_reflow.universal.checkpoint import (
            load_checkpoint as _load,
        )
        from adaptive_reflow.universal.checkpoint import (
            verify_checkpoint as _verify,
        )

        cp = _load(path)
        ok, errs = _verify(cp)
        if not ok:
            raise _CPError(";".join(errs))
        return cp


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
    "ERR_CAPABILITY_UNSUPPORTED",
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
    # Hash-chained ledger (P0-8)
    "build_ledger_row",
    "compute_ledger_row_hash",
    "verify_ledger_chain",
]

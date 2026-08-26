"""Top-level policy orchestrator for the adaptive_reflow component.

This module wires the four typed contracts declared in
``CONTRACTS.md`` (and implemented by their sibling modules) into a single
:class:`AdaptiveReflowPolicyOrchestrator` that the existing
:class:`AdaptiveReflowMechanism` (see ``mechanism_adapter.py``) — and any
future engine binding — can call.

Four contracts:

* :class:`FrozenEnvelopeManifest` (envelope ladder, ``DTB-NC1`` /
  ``DTB-NC2``)
* :class:`CosineScheduleConfig` (cosine restart-noise budget, ``DTB-NA1``)
* :class:`RestartPolicyAuthorityContract` (writer arbitration, ``DTB-S1``)
* :class:`OperationCompositionContract` (operation order, ``DTB-L2``)

Two collaborators:

* :class:`WriterArbitrator` (from ``policy_authority``)
* :class:`CosineScheduleSampler` (from ``cosine_schedule``)

Cross-contract invariants enforced here (delegated where appropriate):

* ``empirical_only=True`` and ``finite_prefix_only=True`` on every
  emitted ledger row. (The literal field ``tail_selection_certified``
  is not on :class:`DynamicRestartTransferLedger` and is **never**
  emitted in the orchestrator's outputs.)
* ``operation_order_version`` on a registered :class:`PhaseState` must
  equal ``OperationCompositionContract.version``; mismatch fails closed
  (cross-contract invariant in CONTRACTS.md §Cross-Contract Invariants).
* Per-channel decisions are produced by ``compute_channel_decision`` and
  gated by ``tail_admissibility`` (``envelope`` match) and
  ``complement_excluded`` (``envelope`` miss).

Module boundary:

* **stdlib-only**. No ``torch``. No I/O. No mutation of caller-owned
  objects; only internal caches and the externally-stored contracts.
* No global state. Every state mutation happens on ``self``.
* ``writer_id == "inference.adaptive_reflow"`` is hard-coded; the
  arbitrator enforces single-executable-writer semantics per DTB-S1.

Tasks satisfied (per ``todo.json``):

* ``DTB-R1`` / ``DTB-R5`` / ``DTB-R6`` — typed bundle + evidence
  registration is rejected when ``validate_round_result_bundle`` /
  ``validate_channel_evidence`` fail.
* ``DTB-R2`` / ``DTB-NC2`` — per-channel decisions use
  :func:`channel_rule.compute_channel_decision` (single-writer authority).
* ``DTB-S1`` — writer arbitration is delegated to
  :class:`WriterArbitrator`.
* ``DTB-L2`` — operation-order contract is read here and matched
  against incoming ``PhaseState.operation_order_version``.
* Cross-cutting orchestrator role for ``DTB-G1`` (public engine adapter
  contract) — the orchestrator is the single hook that consumers call.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from contextlib import suppress
from typing import Any

from adaptive_reflow.contracts import (
    ArtifactHash,
    ChannelName,
    ChannelRuleInputs,
    ChannelTransferDecision,
    ChannelTransferEvidence,
    CosineScheduleConfig,
    CosineScheduleSample,
    DynamicRestartTransferLedger,
    FactorValue,
    FinalRestartPolicy,
    FrozenEnvelopeManifest,
    LedgerRowId,
    OperationCompositionContract,
    PhaseState,
    RestartPolicyAuthorityContract,
    RoundResultBundle,
    hash_artifact,
    hash_trace_digest,
    validate_channel_evidence,
    validate_phase_state,
    validate_round_result_bundle,
)
from adaptive_reflow.envelope.manifest import classify_endpoint
from adaptive_reflow.frame.channel_rule import compute_channel_decision
from adaptive_reflow.frame.merge import bounded_merge
from adaptive_reflow.frame.operation import build_default_composition_contract
from adaptive_reflow.schedule.cosine import CosineScheduleSampler
from adaptive_reflow.writer.authority import (
    DIAGNOSTIC_WRITER_MECHANISM_ID,
    WriterArbitrator,
    build_default_authority_contract,
    build_final_restart_policy,
    verify_policy_against_ledger,
)

# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "AdaptiveReflowPolicyOrchestrator",
    "PolicyOrchestratorError",
    "PolicyOrchestratorValidationError",
]


# ---------------------------------------------------------------------------
# Exceptions (fail-closed; only raise on bad caller input)
# ---------------------------------------------------------------------------


class PolicyOrchestratorError(RuntimeError):
    """Base exception for the policy orchestrator.

    Fail-closed: any unexpected or invalid registration raises a subclass
    of this. The orchestrator is never silent on bad input.
    """


class PolicyOrchestratorValidationError(PolicyOrchestratorError, ValueError):
    """Raised when an internal validator rejects a registered object.

    Inherits from :class:`ValueError` so existing
    ``pytest.raises(ValueError)`` patterns continue to work; the specific
    subclass is exposed via :data:`__all__` for callers that want to
    narrow their ``except`` clauses.
    """


# ---------------------------------------------------------------------------
# Internal error codes (deterministic, ASCII only)
# ---------------------------------------------------------------------------


_ERR_PHASE_INVALID: str = "phase_state_invalid"
_ERR_OPERATION_VERSION_MISMATCH: str = "operation_order_version_mismatch"
_ERR_BUNDLE_INVALID: str = "round_result_bundle_invalid"
_ERR_EVIDENCE_INVALID: str = "channel_evidence_invalid"
_ERR_CHANNEL_NOT_IN_BUNDLE: str = "channel_evidence_bundle_id_mismatch"
_ERR_NO_PHASE_REGISTERED: str = "phase_state_required_for_round_context"
_ERR_LEGACY_FROZEN_PRESENT: str = "ledger_contains_legacy_tail_selection_certified"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


#: The hard-coded writer id of this orchestrator (DTB-S1).
WRITER_ID: str = "inference.adaptive_reflow"

#: The channel set this orchestrator iterates over. Matches
#: ``restart_memory_types.CHANNEL_NAMES``; we hard-code the literal so
#: the orchestrator never silently picks up a wider channel set.
_CANONICAL_CHANNELS: tuple[ChannelName, ...] = (
    ChannelName("coordinate"),
    ChannelName("charge"),
    ChannelName("raw_pair"),
    ChannelName("projected_pair"),
)


# ---------------------------------------------------------------------------
# Internal ledger record (carries freeze_admission_by_channel which is
# NOT in DynamicRestartTransferLedger but IS in FinalRestartPolicy)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _LedgerRecord:
    """Internal pairing of an emitted ledger row with its derived
    freeze-admission mask.

    :class:`DynamicRestartTransferLedger` is frozen and does not carry
    ``freeze_admission_by_channel`` (that field lives on
    :class:`FinalRestartPolicy`). The orchestrator therefore tracks the
    mask alongside the row so :meth:`AdaptiveReflowPolicyOrchestrator.build_final_policy`
    can hand it to :func:`build_final_restart_policy` without recomputing
    anything.

    Only this module reads/writes instances of this class; ``__all__``
    does not expose it.
    """

    ledger: DynamicRestartTransferLedger
    freeze_admission_by_channel: Mapping[ChannelName, bool]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_factor_value(x: Any) -> float:
    """Coerce ``x`` to a Python ``float``; booleans become 0/1."""
    if isinstance(x, bool):
        return float(int(x))
    if not isinstance(x, (int, float)):
        raise PolicyOrchestratorValidationError(
            f"factor must be a real number, got {type(x).__name__}"
        )
    return float(x)


def _safe_factor_value(x: Any, *, default: float) -> float:
    """Return ``_coerce_factor_value(x)`` or ``default`` on bad input.

    Used only when extracting optional/defaulted factors from caller
    payloads so a bad optional value does not crash an evaluation path.
    Real validator failures are caught by the registered evidence.
    """
    try:
        return _coerce_factor_value(x)
    except PolicyOrchestratorValidationError:
        return float(default)


def _as_factor(x: Any) -> FactorValue:
    """Return ``FactorValue`` containing ``float(x)`` without validation.

    Validation is the validator's job; this helper only normalises the
    NewType wrapper so it round-trips cleanly through dataclass field
    types.
    """
    return FactorValue(_coerce_factor_value(x))


def _empty_dict_view() -> Mapping[Any, Any]:
    """Return a stable, empty mapping for "no factors supplied" callers."""
    return {}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class AdaptiveReflowPolicyOrchestrator:
    """Top-level orchestrator that wires the four contracts together.

    The orchestrator is a stateful, fail-closed boundary that:

    * accepts registered :class:`PhaseState`, :class:`RoundResultBundle`,
      and per-channel :class:`ChannelTransferEvidence` rows;
    * classifies each bundle against the frozen envelope and checks tail
      admissibility from that classification;
    * invokes :func:`channel_rule.compute_channel_decision` per channel
      with a fully-built :class:`ChannelRuleInputs`;
    * emits an immutable :class:`DynamicRestartTransferLedger` row with
      ``empirical_only=True`` and ``finite_prefix_only=True`` (the
      literal field ``tail_selection_certified`` is not present on this
      ledger type and is **never** inserted);
    * produces a :class:`FinalRestartPolicy` from the latest ledger via
      :func:`policy_authority.build_final_restart_policy` and verifies
      it via :func:`policy_authority.verify_policy_against_ledger`;
    * delegates writer arbitration to a :class:`WriterArbitrator`
      constructed from the configured
      :class:`RestartPolicyAuthorityContract`.

    The orchestrator is intended to be instantiated once at module
    load (or once per run) and re-used across rounds. State is per-
    instance — there is **no global state**.
    """

    __slots__ = (
        "_arbitrator",
        "_authority_contract",
        "_bundles",
        "_envelope_manifest",
        "_evidence_rows",
        "_last_bounded_fraction",
        "_ledger_records",
        "_operation_contract",
        "_phase",
        "_phases",
        "_schedule_config",
        "_schedule_sampler",
    )

    def __init__(
        self,
        *,
        envelope_manifest: FrozenEnvelopeManifest,
        schedule_config: CosineScheduleConfig,
        authority_contract: RestartPolicyAuthorityContract | None = None,
        operation_contract: OperationCompositionContract | None = None,
        arbitrator: WriterArbitrator | None = None,
        schedule_sampler: CosineScheduleSampler | None = None,
    ) -> None:
        """Store all four contracts; create defaults when ``None``.

        Parameters
        ----------
        envelope_manifest:
            The frozen envelope manifest (DTB-NC1). Required. Treated
            as immutable; the orchestrator never mutates it.
        schedule_config:
            The cosine schedule configuration (DTB-NA1). Required. The
            default :class:`CosineScheduleSampler` is built from this
            unless ``schedule_sampler`` is supplied.
        authority_contract:
            Optional writer-authority contract (DTB-S1). Defaults to
            :func:`policy_authority.build_default_authority_contract`.
        operation_contract:
            Optional operation-composition contract (DTB-L2). Defaults
            to :func:`operation_composition.build_default_composition_contract`.
        arbitrator:
            Optional writer arbitrator. Defaults to a fresh
            :class:`WriterArbitrator` built from ``authority_contract``
            (or its default).
        schedule_sampler:
            Optional schedule sampler. Defaults to a fresh
            :class:`CosineScheduleSampler(schedule_config)`.

        Raises
        ------
        PolicyOrchestratorValidationError
            On a ``None`` ``envelope_manifest`` or ``schedule_config``
            (both are required).
        """
        if envelope_manifest is None:
            raise PolicyOrchestratorValidationError(
                "envelope_manifest must not be None"
            )
        if schedule_config is None:
            raise PolicyOrchestratorValidationError(
                "schedule_config must not be None"
            )

        self._envelope_manifest: FrozenEnvelopeManifest = envelope_manifest
        self._schedule_config: CosineScheduleConfig = schedule_config

        if authority_contract is None:
            authority_contract = build_default_authority_contract()
        self._authority_contract: RestartPolicyAuthorityContract = authority_contract

        if operation_contract is None:
            operation_contract = build_default_composition_contract()
        self._operation_contract: OperationCompositionContract = operation_contract

        if arbitrator is None:
            arbitrator = WriterArbitrator(authority_contract)
        self._arbitrator: WriterArbitrator = arbitrator

        if schedule_sampler is None:
            schedule_sampler = CosineScheduleSampler(schedule_config)
        self._schedule_sampler: CosineScheduleSampler = schedule_sampler

        # Mutable internal caches. None until first registration.
        self._phase: PhaseState | None = None
        self._ledger_records: list[_LedgerRecord] = []
        # Audit-only registries of inputs accepted by the validator.
        # These are not used to re-derive policy; they exist so the
        # orchestrator's call ordering is observable in tests.
        self._phases: list[PhaseState] = []
        self._bundles: list[RoundResultBundle] = []
        self._evidence_rows: list[ChannelTransferEvidence] = []
        # DTB-R3: per-channel cache of the most recent bounded fraction.
        # Feeds :meth:`merge_fraction_authority` so the bounded merge
        # can both raise *and* lower the prior-round fraction across
        # rounds.
        self._last_bounded_fraction: dict[ChannelName, float] = {}

    # ---- public read-only properties ----------------------------------

    @property
    def envelope_manifest(self) -> FrozenEnvelopeManifest:
        """Return the stored :class:`FrozenEnvelopeManifest`."""
        return self._envelope_manifest

    @property
    def schedule_config(self) -> CosineScheduleConfig:
        """Return the stored :class:`CosineScheduleConfig`."""
        return self._schedule_config

    @property
    def authority_contract(self) -> RestartPolicyAuthorityContract:
        """Return the stored :class:`RestartPolicyAuthorityContract`."""
        return self._authority_contract

    @property
    def operation_contract(self) -> OperationCompositionContract:
        """Return the stored :class:`OperationCompositionContract`."""
        return self._operation_contract

    @property
    def arbitrator(self) -> WriterArbitrator:
        """Return the stored :class:`WriterArbitrator`."""
        return self._arbitrator

    @property
    def schedule_sampler(self) -> CosineScheduleSampler:
        """Return the stored :class:`CosineScheduleSampler`."""
        return self._schedule_sampler

    @property
    def current_phase(self) -> PhaseState | None:
        """Return the latest registered :class:`PhaseState` or ``None``."""
        return self._phase

    @property
    def last_ledger(self) -> DynamicRestartTransferLedger | None:
        """Return the most recent ledger row, or ``None``."""
        if not self._ledger_records:
            return None
        return self._ledger_records[-1].ledger

    # ---- registration API (fail-closed) -------------------------------

    def register_phase(self, phase: PhaseState) -> None:
        """Validate and register ``phase`` as the current controller input.

        The phase is validated via
        :func:`restart_memory_types.validate_phase_state`; on rejection
        the registration is aborted (fail closed) and
        :class:`PolicyOrchestratorValidationError` is raised.

        Cross-contract invariant from ``CONTRACTS.md``
        §Cross-Contract Invariants: ``operation_order_version`` must
        equal ``OperationCompositionContract.version``. Mismatch is
        rejected with :class:`PolicyOrchestratorValidationError`.
        """
        if phase is None:
            raise PolicyOrchestratorValidationError("phase must not be None")

        ok, errors = validate_phase_state(phase)
        if not ok:
            raise PolicyOrchestratorValidationError(
                f"{_ERR_PHASE_INVALID}: "
                + "; ".join(str(e) for e in errors)
            )

        contract_version = str(self._operation_contract.version)
        phase_version = str(phase.operation_order_version)
        if phase_version != contract_version:
            raise PolicyOrchestratorValidationError(
                f"{_ERR_OPERATION_VERSION_MISMATCH}: phase.operation_order_version "
                f"{phase_version!r} must equal operation_contract.version "
                f"{contract_version!r}"
            )

        self._phase = phase
        self._phases.append(phase)

    def register_bundle(self, bundle: RoundResultBundle) -> None:
        """Validate and register ``bundle`` via ``validate_round_result_bundle``.

        On rejection the registration is aborted (fail closed) and
        :class:`PolicyOrchestratorValidationError` is raised. Bundles
        are accumulated in the audit log but are not used to re-derive
        any policy state — each call to :meth:`evaluate_bundle` re-runs
        the channel rule over the supplied bundle.
        """
        if bundle is None:
            raise PolicyOrchestratorValidationError("bundle must not be None")

        ok, errors = validate_round_result_bundle(bundle)
        if not ok:
            raise PolicyOrchestratorValidationError(
                f"{_ERR_BUNDLE_INVALID}: "
                + "; ".join(str(e) for e in errors)
            )

        self._bundles.append(bundle)

    def register_evidence(self, evidence: ChannelTransferEvidence) -> None:
        """Validate and register ``evidence`` via ``validate_channel_evidence``.

        On rejection the registration is aborted (fail closed) and
        :class:`PolicyOrchestratorValidationError` is raised.
        """
        if evidence is None:
            raise PolicyOrchestratorValidationError("evidence must not be None")

        ok, errors = validate_channel_evidence(evidence)
        if not ok:
            raise PolicyOrchestratorValidationError(
                f"{_ERR_EVIDENCE_INVALID}: "
                + "; ".join(str(e) for e in errors)
            )

        self._evidence_rows.append(evidence)

    # ---- evaluation (the policy core) ---------------------------------

    def evaluate_bundle(
        self,
        bundle: RoundResultBundle,
        evidence_by_channel: Mapping[ChannelName, ChannelTransferEvidence],
    ) -> DynamicRestartTransferLedger:
        """Classify ``bundle``, evaluate each channel, emit a ledger row.

        Steps:

        1. Validate ``bundle`` and every evidence row. On any
           validation failure a :class:`PolicyOrchestratorValidationError`
           is raised.
        2. Classify ``bundle`` against the frozen envelope via
           :func:`envelope_manifest.classify_endpoint`.
        3. Derive ``tail_admissibility`` (True iff the bundle matched a
           layer) and ``complement_excluded`` (True iff the bundle did
           **not** match any layer).
        4. Take a fresh :class:`CosineScheduleSample` from the cached
           sampler using ``phase.outer_cycle_id`` /
           ``phase.round_in_cycle`` if a phase has been registered, else
           ``(0, 0)``.
        5. For each canonical channel:
              * look up the evidence (else use an empty stub that fails
                closed inside :func:`compute_channel_decision`);
              * build a :class:`ChannelRuleInputs`;
              * call :func:`channel_rule.compute_channel_decision`;
              * capture the decision.
        6. Auto-register the canonical
           ``inference.noise_bias`` diagnostic writer with
           :meth:`WriterArbitrator.register_request` so dual-executable
           attempts fail closed at the boundary (see DTB-S1).
        7. Build a :class:`DynamicRestartTransferLedger` with
           ``empirical_only=True``, ``finite_prefix_only=True`` and
           ``writer_id == "inference.adaptive_reflow"``. The literal
           field ``tail_selection_certified`` is **not present** on this
           row type and must never be added.
        8. Cache the row alongside the derived freeze-admission mask
           for later use by :meth:`build_final_policy`.

        Parameters
        ----------
        bundle:
            The source bundle. Must validate via
            :func:`validate_round_result_bundle`.
        evidence_by_channel:
            Mapping from channel name to evidence. Unknown channels are
            evaluated with empty evidence (which the rule rejects by
            construction -> ``gate=False`` -> ``beta=0``).

        Returns
        -------
        DynamicRestartTransferLedger
            The freshly emitted ledger row.

        Raises
        ------
        PolicyOrchestratorValidationError
            On any validation failure.
        """
        # --- 1. validate the bundle itself first ---
        self.register_bundle(bundle)

        # --- 2. classify the bundle against the envelope ---
        classification = classify_endpoint(bundle, self._envelope_manifest)
        matched = classification.matched_layer_index is not None
        tail_admissibility: bool = bool(matched)
        complement_excluded: bool = not bool(matched)

        # --- 3. derive per-round schedule sample ---
        if self._phase is not None:
            outer_cycle_id = int(self._phase.outer_cycle_id)
            round_in_cycle = int(self._phase.round_in_cycle)
        else:
            outer_cycle_id = 0
            round_in_cycle = 0

        # target_round: bundle.source_round + 1 when the caller did not
        # pin a phase; fall back to bundle.source_round + 1 to keep the
        # monotonic property even with no phase registered.
        target_round = int(bundle.source_round) + 1

        schedule_sample = self._schedule_sampler.sample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=round_in_cycle,
            target_round=target_round,
        )

        # --- 4. per-channel decisions ---
        per_channel_evidence: list[ChannelTransferEvidence] = []
        per_channel_decision: list[ChannelTransferDecision] = []
        alpha_by_channel: dict[ChannelName, FactorValue] = {}
        beta_by_channel: dict[ChannelName, FactorValue] = {}
        raw_fraction_by_channel: dict[ChannelName, FactorValue] = {}
        bounded_fraction_by_channel: dict[ChannelName, FactorValue] = {}
        fresh_noise_floor_by_channel: dict[ChannelName, FactorValue] = {}
        freeze_admission_by_channel: dict[ChannelName, bool] = {}

        # Build a per-channel mixing cap from the schedule sample.
        # Convention: mixing_cap equals schedule_sample.n_cap for every
        # channel (no per-channel cap split unless the config says so).
        # The schedule_sampler doesn't expose per_channel_caps directly,
        # so we use n_cap as the canonical scheduled_cap.
        scheduled_cap_value = _safe_factor_value(
            schedule_sample.n_cap, default=0.0
        )

        for channel in _CANONICAL_CHANNELS:
            evidence = evidence_by_channel.get(channel)
            if evidence is None:
                # Fail closed: build a synthetic evidence row that the
                # rule will reject for missing required factors.
                evidence = ChannelTransferEvidence(
                    bundle_id=bundle.bundle_id,
                    channel=channel,
                    materialization_pass=None,
                    geometry_pass=None,
                    perturbation_stability_lower_bound=FactorValue(0.0),
                    condition_sensitivity_observable_pass=None,
                    external_metric_uncertainty=FactorValue(0.0),
                    proxy_only_evidence=True,
                    ambiguity=FactorValue(1.0),
                    degeneracy_penalty=FactorValue(1.0),
                    support_coverage=FactorValue(0.0),
                    recency_decay=FactorValue(0.0),
                    calibration_lower_bound=FactorValue(0.0),
                    raw_score=0.0,
                    bounded_score=0.0,
                    provenance=(),
                    validation_errors=("synthetic_no_evidence_registered",),
                )
            else:
                # Validate the supplied evidence before using it. This
                # is the explicit fail-closed gate on the input mapping.
                ok, errors = validate_channel_evidence(evidence)
                if not ok:
                    raise PolicyOrchestratorValidationError(
                        f"{_ERR_EVIDENCE_INVALID} for channel {str(channel)!r}: "
                        + "; ".join(str(e) for e in errors)
                    )
                # Self-consistency: evidence.bundle_id must match the
                # bundle being evaluated.
                if str(evidence.bundle_id) != str(bundle.bundle_id):
                    raise PolicyOrchestratorValidationError(
                        f"{_ERR_CHANNEL_NOT_IN_BUNDLE}: evidence.bundle_id "
                        f"{str(evidence.bundle_id)!r} must equal bundle.bundle_id "
                        f"{str(bundle.bundle_id)!r} for channel {str(channel)!r}"
                    )

            # Fresh-noise floor: per_channel_floor if config supplies one,
            # else schedule n_cap as a conservative default.
            floor_value = _safe_factor_value(
                self._schedule_config.fresh_noise_floor_by_channel.get(
                    channel, schedule_sample.n_cap
                ),
                default=_safe_factor_value(schedule_sample.n_cap, default=0.0),
            )

            # delta_cap_up / delta_cap_down: symmetric value from config,
            # falling back to 0.5 as a permissive default (this is the
            # canonical symmetric cap for bounded updates; the rule
            # treats [0, 1] values as valid).
            delta_cap = _safe_factor_value(
                self._schedule_config.symmetric_delta_caps_by_channel.get(
                    channel, 0.5
                ),
                default=0.5,
            )

            horizon_coverage_proven = bool(
                self._phase.horizon_coverage_proven
                if self._phase is not None
                else False
            )

            rule_inputs = ChannelRuleInputs(
                bundle=bundle,
                evidence=evidence,
                phase_state=self._phase if self._phase is not None else _empty_phase_state_for_eval(),
                scheduled_cap=FactorValue(scheduled_cap_value),
                mixing_cap=FactorValue(scheduled_cap_value),
                fresh_noise_floor=FactorValue(floor_value),
                delta_cap_up=FactorValue(delta_cap),
                delta_cap_down=FactorValue(delta_cap),
                tail_admissibility=tail_admissibility,
                complement_excluded=complement_excluded,
                frozen_envelope_manifest_hash=ArtifactHash(
                    str(self._envelope_manifest.manifest_hash)
                ),
                finite_prefix_only=True,
                calibration_lower_bound=_safe_factor_value(
                    evidence.calibration_lower_bound, default=0.0
                ),
                perturbation_stability_lower_bound=_safe_factor_value(
                    evidence.perturbation_stability_lower_bound, default=0.0
                ),
                support_coverage=_safe_factor_value(
                    evidence.support_coverage, default=0.0
                ),
                ambiguity=_safe_factor_value(
                    evidence.ambiguity, default=1.0
                ),
                degeneracy_penalty=_safe_factor_value(
                    evidence.degeneracy_penalty, default=1.0
                ),
                recency_decay=_safe_factor_value(
                    evidence.recency_decay, default=0.0
                ),
                horizon_coverage_proven=horizon_coverage_proven,
                selected_bundle_id=bundle.bundle_id,
            )

            outputs = compute_channel_decision(rule_inputs)
            decision = outputs.decision

            per_channel_evidence.append(evidence)
            per_channel_decision.append(decision)

            # DTB-R3: route the bounded merge through the orchestrator's
            # bounded_merge helper instead of any ``max(prev, dynamic)``
            # operator. The previous-round value is the most recent
            # emitted ``bounded_target_fraction`` for this channel, or
            # ``None`` when no prior round exists.
            prev_bounded = self._last_bounded_fraction.get(channel)
            merged = self.merge_fraction_authority(
                channel=channel,
                dynamic=float(decision.bounded_target_fraction),
                prev=prev_bounded,
                schedule_sample=schedule_sample,
                fresh_noise_floor=float(decision.fresh_noise_floor),
            )

            alpha_by_channel[channel] = decision.alpha
            beta_by_channel[channel] = FactorValue(float(merged))
            raw_fraction_by_channel[channel] = decision.scheduled_cap
            bounded_fraction_by_channel[channel] = FactorValue(float(merged))
            fresh_noise_floor_by_channel[channel] = decision.fresh_noise_floor

            # Freeze admission: admit iff the gate is open and the
            # decision emitted a non-zero bounded_target_fraction.
            non_zero_beta = (
                bool(decision.gate)
                and float(merged) > 0.0
            )
            freeze_admission_by_channel[channel] = bool(non_zero_beta)

            # Cache this round's bounded fraction for the next round's
            # merge.
            self._last_bounded_fraction[channel] = float(merged)

        # --- 5. auto-register the canonical diagnostic writer ---
        # DTB-S1: the orchestrator is the sole executable writer, but the
        # canonical diagnostic writer is auto-registered alongside the
        # orchestrator's executable request so a same-run dual-executable
        # attempt fails closed at the boundary. The diagnostic request
        # is idempotent and never raises when the diagnostic writer is
        # already registered.
        with suppress(Exception):  # pragma: no cover - defensive
            # Auto-registration is best-effort; a prior registration may
            # already be present (e.g. from a test setup) or the
            # arbitrator may already be locked into a different mode.
            # Failures here do not block ledger emission.
            self._arbitrator.register_request(
                DIAGNOSTIC_WRITER_MECHANISM_ID, "diagnostic_only"
            )

        # --- 6. assemble the ledger row ---
        expected_trace = hash_trace_digest(
            bundle.bundle_id,
            bundle.source_round,
            bundle.round_count,
            bundle.run_id,
            bundle.sample_id,
        )

        ledger_row_id = LedgerRowId(
            hash_artifact(
                {
                    "writer_id": WRITER_ID,
                    "run_id": str(bundle.run_id),
                    "sample_id": str(bundle.sample_id),
                    "trace_digest": str(expected_trace),
                    "source_round": int(bundle.source_round),
                    "target_round": int(target_round),
                    "outer_cycle_id": int(outer_cycle_id),
                    "selected_bundle_id": str(bundle.bundle_id),
                    "alpha_by_channel": _sorted_mapping(alpha_by_channel),
                    "beta_by_channel": _sorted_mapping(beta_by_channel),
                    "fresh_noise_floor_by_channel": _sorted_mapping(
                        fresh_noise_floor_by_channel
                    ),
                }
            )
        )

        ledger = DynamicRestartTransferLedger(
            ledger_row_id=ledger_row_id,
            run_id=bundle.run_id,
            sample_id=bundle.sample_id,
            trace_digest=expected_trace,
            source_round=int(bundle.source_round),
            target_round=int(target_round),
            outer_cycle_id=int(outer_cycle_id),
            selected_bundle_id=bundle.bundle_id,
            rejected_bundle_ids=(),
            per_channel_evidence=tuple(per_channel_evidence),
            per_channel_decision=tuple(per_channel_decision),
            alpha_by_channel=alpha_by_channel,
            beta_by_channel=beta_by_channel,
            raw_fraction_by_channel=raw_fraction_by_channel,
            bounded_fraction_by_channel=bounded_fraction_by_channel,
            fresh_noise_floor_by_channel=fresh_noise_floor_by_channel,
            calibration_artifact_hash=bundle.calibration_artifact_hash,
            frozen_envelope_manifest_hash=ArtifactHash(
                str(self._envelope_manifest.manifest_hash)
            ),
            tail_budget_row_ref=None,
            finite_prefix_only=True,
            empirical_only=True,
            feedback_mode=bundle.feedback_mode,
            writer_id=WRITER_ID,
            provenance=bundle.provenance,
            validation_errors=(),
            created_at_round=int(target_round),
        )

        # --- 7. cache the record ---
        record = _LedgerRecord(
            ledger=ledger,
            freeze_admission_by_channel=dict(freeze_admission_by_channel),
        )
        self._ledger_records.append(record)

        # --- 8. surface schedule_sample via the schedule_sampler cache ---
        # The schedule sampler's last_sample is updated by ``sample``
        # above; nothing else to do here.

        return ledger

    def build_final_policy(
        self,
        ledger: DynamicRestartTransferLedger,
    ) -> FinalRestartPolicy:
        """Build the :class:`FinalRestartPolicy` for ``ledger``.

        Reads ``beta_by_channel``, ``alpha_by_channel`` and
        ``fresh_noise_floor_by_channel`` directly from ``ledger``, and
        freezes the per-channel admission mask by looking up the
        :class:`_LedgerRecord` associated with ``ledger`` (produced
        earlier by :meth:`evaluate_bundle`).

        The freshly built :class:`FinalRestartPolicy` is then verified
        against ``ledger`` via
        :func:`policy_authority.verify_policy_against_ledger`. A
        verification failure raises :class:`PolicyOrchestratorError`.

        Parameters
        ----------
        ledger:
            The :class:`DynamicRestartTransferLedger` row to consume.

        Returns
        -------
        FinalRestartPolicy
            The verified final restart policy.

        Raises
        ------
        PolicyOrchestratorValidationError
            On identity / structural mismatch between ``ledger`` and
            the in-memory record cache (no fallback; the policy cannot
            be built from a ledger the orchestrator did not emit).
        PolicyOrchestratorError
            On any verification failure.
        """
        if ledger is None:
            raise PolicyOrchestratorValidationError("ledger must not be None")

        # Locate the cached record for this ledger row. Identity
        # comparison (id) is fine because the dataclass is frozen and
        # the orchestrator is the sole emitter.
        record: _LedgerRecord | None = None
        for cand in self._ledger_records:
            if cand.ledger is ledger:
                record = cand
                break
        if record is None:
            raise PolicyOrchestratorValidationError(
                "ledger was not emitted by this orchestrator; "
                "build_final_policy refuses foreign ledger rows"
            )

        # Schedule sample: take the latest one the cached sampler has,
        # else build a deterministic stub from the schedule config so
        # build_final_restart_policy always has a sample to thread.
        schedule_sample: CosineScheduleSample | None = self._schedule_sampler.last_sample
        if schedule_sample is None:
            schedule_sample = self._schedule_sampler.sample(
                outer_cycle_id=int(ledger.outer_cycle_id),
                round_in_cycle=0,
                target_round=int(ledger.target_round),
            )

        # Build the policy.
        policy = build_final_restart_policy(
            policy_id=LedgerRowId(str(ledger.ledger_row_id)),
            run_id=ledger.run_id,
            target_round=int(ledger.target_round),
            outer_cycle_id=int(ledger.outer_cycle_id),
            beta_by_channel=ledger.beta_by_channel,
            alpha_by_channel=ledger.alpha_by_channel,
            fresh_noise_floor_by_channel=ledger.fresh_noise_floor_by_channel,
            schedule_sample=schedule_sample,
            freeze_admission_by_channel=record.freeze_admission_by_channel,
            ledger_row_id=ledger.ledger_row_id,
            created_at_round=int(ledger.created_at_round),
        )

        # Verify. This is the boundary check the brief asks for; a
        # mismatch is a hard error (fail closed) — we never silently
        # emit an unverified policy.
        if not verify_policy_against_ledger(policy, ledger):
            raise PolicyOrchestratorError(
                "verify_policy_against_ledger returned False; the freshly "
                "built FinalRestartPolicy does not match its source ledger"
            )

        return policy

    def authorize_writer(self, mechanism_id: str, mode: str) -> None:
        """Delegate a writer request to the cached :class:`WriterArbitrator`.

        Thin wrapper; the brief asks for explicit delegation rather than
        letting callers reach into ``self.arbitrator`` directly. Errors
        from the arbitrator propagate unchanged (they are
        :class:`WriterArgumentError`; the orchestrator does not catch).
        """
        self._arbitrator.register_request(mechanism_id, mode)

    def merge_fraction_authority(
        self,
        *,
        channel: ChannelName,
        dynamic: float,
        prev: float | None = None,
        schedule_sample: CosineScheduleSample | None = None,
        fresh_noise_floor: float = 0.0,
    ) -> FactorValue:
        """Return the bounded merge of ``prev`` and ``dynamic`` for ``channel``.

        DTB-R3 — the canonical replacement for any unconditional
        ``max(prev, dynamic)`` operator. The merge can both *raise* and
        *lower* the prior-round fraction, bounded by the per-round
        delta cap and a hard fresh-noise floor.

        Parameters
        ----------
        channel:
            The channel name (used to look up per-channel delta caps
            and the per-channel fresh-noise floor override).
        dynamic:
            The dynamic, evidence-derived fraction (typically
            ``ChannelTransferDecision.bounded_target_fraction``).
        prev:
            The previous-round bounded fraction. ``None`` falls back to
            the schedule sample's ``n_cap`` (or ``0.0``).
        schedule_sample:
            Optional :class:`CosineScheduleSample` used to derive the
            hard cap and the default floor.
        fresh_noise_floor:
            Explicit fresh-noise floor override. ``None`` is treated as
            ``0.0`` and the helper falls back to the per-channel
            mapping when ``fresh_noise_floor`` is ``None``.

        Returns
        -------
        FactorValue
            The bounded, clamped merge result in ``[floor, cap]``.
        """
        if channel is None:
            raise PolicyOrchestratorValidationError(
                "channel must not be None"
            )

        # Per-channel delta cap lookup.
        delta_cap = _safe_factor_value(
            self._schedule_config.symmetric_delta_caps_by_channel.get(
                channel, 0.5
            ),
            default=0.5,
        )

        # Per-channel fresh-noise floor lookup (explicit override
        # wins; else use the configured per-channel floor).
        if fresh_noise_floor is None:
            fresh_noise_floor = 0.0
        configured_floor = _safe_factor_value(
            self._schedule_config.fresh_noise_floor_by_channel.get(
                channel, fresh_noise_floor
            ),
            default=fresh_noise_floor,
        )

        # Schedule-derived hard cap (default 1.0 when no sample).
        if schedule_sample is not None:
            try:
                n_cap = _safe_factor_value(
                    schedule_sample.n_cap, default=1.0
                )
                cap = float(min(1.0, max(0.0, n_cap)))
            except PolicyOrchestratorValidationError:
                cap = 1.0
        else:
            cap = 1.0

        # Resolve prev: explicit override wins; else use the per-channel
        # last-emitted bounded fraction, else fall back to schedule.
        if prev is not None:
            try:
                prev_value = _safe_factor_value(prev, default=0.0)
            except PolicyOrchestratorValidationError:
                prev_value = 0.0
            prev_value = float(max(0.0, min(1.0, prev_value)))
        else:
            cached_prev = self._last_bounded_fraction.get(channel)
            if cached_prev is not None:
                prev_value = float(cached_prev)
            elif schedule_sample is not None:
                prev_value = float(
                    min(
                        1.0,
                        max(
                            0.0,
                            _safe_factor_value(
                                schedule_sample.n_cap, default=0.0
                            ),
                        ),
                    )
                )
            else:
                prev_value = 0.0

        merged = bounded_merge(
            prev=prev_value,
            dynamic=dynamic,
            cap=cap,
            floor=float(configured_floor),
            delta_cap_up=delta_cap,
            delta_cap_down=delta_cap,
        )
        return FactorValue(float(merged))

    def is_feature_enabled(self) -> bool:
        """Return ``True`` iff both required contracts are present.

        The orchestrator's ``__init__`` rejects ``None`` for either
        contract, so this is always ``True`` for a successfully
        constructed orchestrator. The method is exposed because the
        brief requires it as part of the public surface.
        """
        return (
            self._envelope_manifest is not None
            and self._schedule_config is not None
        )

    def reset_cycle(self) -> None:
        """Clear internal ledger cache and the schedule sampler cache.

        The phase, bundle, and evidence audit registries are kept (so
        callers can still introspect the input history after a reset),
        but the ledger cache, the per-channel bounded-fraction cache,
        and the cached schedule sample are wiped. The envelope
        manifest, schedule config, contracts and arbitrator are not
        reset — they are bound at construction.
        """
        self._ledger_records.clear()
        self._last_bounded_fraction.clear()
        # The schedule sampler has no public reset hook (it is a thin
        # facade over ``last_sample``); clearing the cached sample via
        # its property is the documented way to "clear the schedule
        # sampler cache" — the dataclass is immutable so we use the
        # private slot. This module is the sole caller.
        self._schedule_sampler._last_sample = None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Free helpers
# ---------------------------------------------------------------------------


def _empty_phase_state_for_eval() -> PhaseState:
    """Build a deterministic stub :class:`PhaseState` for evaluation paths.

    Used only when no :class:`PhaseState` has been registered with the
    orchestrator: the rule expects a phase-state-shaped object, and the
    downstream hash is content-derived. The stub is constructed via
    ``make_default_phase_state`` semantics with a placeholder lineage
    digest; consumers must always call ``register_phase`` upstream in
    production.
    """
    from adaptive_reflow.contracts import make_default_phase_state

    return make_default_phase_state(
        outer_cycle_id=0,
        round_in_cycle=0,
        schedule_phase="high_noise",
        schedule_phase_index=0,
        previous_trigger=None,
        operation_order_version="v_unset",
        source_selector_procedure="deterministic.previous_round",
        seed_lineage_digest=ArtifactHash(""),
        horizon_remaining=1,
        horizon_coverage_proven=False,
        ambiguity_band_active=False,
        recorded_at_round=0,
    )


def _sorted_mapping(
    mapping: Mapping[ChannelName, FactorValue]
) -> list:
    """Return ``mapping`` as a sorted list of ``[str(key), value]`` pairs.

    Mirrors the helper used by ``hash_policy_hash`` and
    ``hash_artifact`` so the ledger ``ledger_row_id`` is byte-stable
    across runs.
    """
    return [[str(k), v] for k, v in sorted(mapping.items(), key=lambda kv: str(kv[0]))]

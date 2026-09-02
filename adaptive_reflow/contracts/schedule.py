"""Adaptive reflow typed contracts — cosine restart budget (DTB-NA1).

Stdlib-only: no torch, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from .types import (
    ArtifactHash,
    BundleId,
    ChannelName,
    FactorValue,
    ProvenanceChain,
    RestartTriggerCode,
    TriggerId,
)

# ---------------------------------------------------------------------------
# Cosine restart budget (CONTRACTS.md §4) — DTB-NA1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CosineScheduleConfig:
    """Frozen schedule configuration for the outer cycle."""

    schedule_family: Literal[
        "constant",
        "linear",
        "cosine_no_restart",
        "cosine_guarded_restart",
        "empirical_learned",
    ]
    cycle_length: int
    n_min: FactorValue
    n_max: FactorValue
    per_channel_caps: Mapping[ChannelName, FactorValue]
    fresh_noise_floor_by_channel: Mapping[ChannelName, FactorValue]
    symmetric_delta_caps_by_channel: Mapping[ChannelName, FactorValue]
    restart_triggers_allowed: tuple[RestartTriggerCode, ...]
    config_hash: ArtifactHash
    frozen_before_evaluation: bool


@dataclass(frozen=True)
class CosineScheduleSample:
    """Sample of the schedule for a single round."""

    schedule_hash: ArtifactHash
    outer_cycle_id: int
    round_in_cycle: int
    cycle_length: int
    n_cap: FactorValue
    n_min: FactorValue
    n_max: FactorValue
    u_r: float
    family: str
    computed_at_round: int


@dataclass(frozen=True)
class FreshNoiseFloor:
    """Per-channel fresh-noise floor, with its provenance source."""

    channel: ChannelName
    floor_value: FactorValue
    source: Literal["schedule", "calibration", "manual_override"]
    config_hash: ArtifactHash


@dataclass(frozen=True)
class RestartTriggerEvent:
    """Record of one restart-trigger event (warm restart boundary)."""

    trigger_id: TriggerId
    outer_cycle_id_old: int
    outer_cycle_id_new: int
    trigger_code: RestartTriggerCode
    trigger_metric_snapshot: Mapping[str, float]
    discarded_source_bundle_ids: tuple[BundleId, ...]
    noise_capacity_before: FactorValue
    noise_capacity_after: FactorValue
    unresolved_metric_deficit: Mapping[str, float]
    provenance: ProvenanceChain
    recorded_at_round: int


# ---------------------------------------------------------------------------
# Lemma 4 regime gate (Phase-4 / Design #3) — opt-in scheduler contract
# ---------------------------------------------------------------------------
#
# Paper Lemma 4 (line 110-113) bounds the complement posterior mass by
# ``e^{-e_rho / (2 eps^2)}`` and calls it ``o(eps)``. That step is only
# valid inside the *regime*
#
#     eps^2 < e_rho / log 2
#
# with ``e_rho = min{rho^4, (1-rho)^2 eta^2}`` (line 128). A scheduler
# that emits ``ScheduleSample.eps_implicit`` without consulting
# ``e_rho`` can silently leave the regime, at which point the framework
# still runs but its FID trajectory is no longer grounded in the
# theorem. The contracts below are the *typed* half of the fix: they
# declare the two optional scheduler fields (``regime_aware`` and
# ``e_rho_provider``) plus a frozen carrier for them. Enforcement lives
# in ``adaptive_reflow.algorithm.scheduler.regime_selector``
# (``RegimeAwareEpsSelector`` + concretes), which the algorithm layer
# consults per round.
#
# Both fields default to the inert values (``False`` / ``None``), so a
# scheduler that ignores them behaves exactly as before: the gate is
# opt-in and existing convergence tests stay green.


#: Default strict-inequality slack for the Lemma 4 ceiling. Lemma 4
#: requires ``eps^2 < e_rho / log 2`` *strictly*, so the ceiling is
#: ``sqrt(e_rho / log 2) - LEMMA4_REGIME_SLACK`` and the strict form
#: survives floating-point comparison. Single source of truth: the
#: algorithm layer's ``DEFAULT_REGIME_SLACK`` aliases this constant.
LEMMA4_REGIME_SLACK: float = 1e-9


@dataclass(frozen=True)
class RegimeGate:
    """Opt-in Lemma-4 regime gate carried by a scheduler.

    A frozen value object bundling the two optional
    ``SchedulerProtocol`` fields so a caller can pass one argument
    instead of three, and so a config snapshot round-trips the gate as
    a unit.

    :param regime_aware: master switch. ``False`` (the default) means
        the scheduler never consults ``e_rho`` and its ``eps`` path is
        byte-identical to the pre-gate behaviour. ``True`` means every
        round's ``eps`` proposal is clamped to
        ``sqrt(e_rho / log 2) - slack``.
    :param e_rho_provider: maps a round index (as a float, so the same
        callable shape serves fractional / continuous-time schedules)
        to the exterior gap ``e_rho`` for that round. ``None`` with
        ``regime_aware=True`` means "use the paper default", i.e.
        :func:`adaptive_reflow.contracts.paper_quantities.exterior_gap_e_rho`
        at its documented ``rho`` / ``eta`` defaults.
    :param slack: strict-inequality slack; see
        :data:`LEMMA4_REGIME_SLACK`.
    :param selector_family: which
        ``RegimeAwareEpsSelector`` family drives the bounded proposal
        (``"cosine_anneal"`` or ``"convergence_adaptive"``).
    """

    regime_aware: bool = False
    e_rho_provider: Callable[[float], float] | None = None
    slack: float = LEMMA4_REGIME_SLACK
    selector_family: str = "cosine_anneal"

    def is_active(self) -> bool:
        """Return ``True`` iff the gate should be enforced this run."""
        return bool(self.regime_aware)

    def e_rho_at(self, round_index: float) -> float | None:
        """Return ``e_rho`` for ``round_index``, or ``None`` when inert.

        Returns ``None`` when the gate is inactive *or* when no
        provider was supplied — the algorithm layer then decides
        whether to fall back to the paper default. Never raises for an
        inert gate.
        """
        if not self.regime_aware:
            return None
        provider = self.e_rho_provider
        if provider is None:
            return None
        return float(provider(float(round_index)))


@runtime_checkable
class RegimeAwareSchedulerProtocol(Protocol):
    """Structural type for a scheduler that honours the regime gate.

    Declared as a *separate* protocol rather than as new members on
    ``SchedulerProtocol`` on purpose: ``SchedulerProtocol`` is
    ``runtime_checkable`` and asserted with ``isinstance`` across the
    suite, so adding a member there would retroactively fail every
    existing scheduler that does not implement it. Consumers therefore
    detect the gate structurally — ``isinstance(sched,
    RegimeAwareSchedulerProtocol)`` or a ``getattr(sched,
    "regime_aware", False)`` guard — and legacy schedulers keep
    satisfying ``SchedulerProtocol`` unchanged.

    Implementations expose the gate's two fields directly so a caller
    can read them without knowing the concrete type:

    * ``regime_aware`` — ``True`` iff the Lemma 4 clamp is enforced;
    * ``e_rho_provider`` — the round-index → ``e_rho`` callable (or
      ``None`` for the paper default).
    """

    regime_aware: bool
    e_rho_provider: Callable[[float], float] | None

    def regime_violation_warnings(self) -> tuple[str, ...]:
        """Return the per-run log of regime clamps / infeasibilities."""
        ...

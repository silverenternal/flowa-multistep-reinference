"""Scheduler Protocol surface + sample dataclass (Wave 105 P2-A split).

This module owns the **structural type** of the algorithm-layer scheduler:
the :class:`ScheduleSample` dataclass a scheduler returns, the
:class:`ScheduleSampleProtocol` / :class:`SchedulerProtocol` ``Protocol``
classes that define the abstract surface, and a small private helper
(:func:`_coerce_int_nonneg`) used by every concrete scheduler to validate
non-negative integer arguments.

It depends only on the canonical contracts-layer types (no scheduler
concrete classes, no engine wiring, no tool helpers) so any
``SchedulerProtocol`` consumer can import the abstract surface without
dragging in the entire scheduler family.

Forward noise injection (P0-7, ecosystem addition): the scheduler exposes
the symmetric forward step of the canonical reverse-blend (DRM-3,
``scheduler.sample`` -> ``merge_operator.merge``). :meth:`SchedulerProtocol.inject_noise`
takes a state, a schedule sample, and a deterministic ``np.random.Generator``
and returns a new state with fresh noise scaled by ``sqrt(n_cap)``. The
default implementation ``state + sqrt(n_cap) * generator.standard_normal``
is reversible up to ``generator.bit_generator.state``; callers can replay
injection byte-for-byte given the same seed. The
:class:`CosineAnnealScheduler` uses the schedule's ``n_cap`` as the noise
mass; :class:`CodimensionSheetScheduler` uses its cached paper-quantity
``A_g`` as the per-round mass; non-stochastic families fall back to the
``n_cap``-driven default. The runner emits ``FORWARD_NOISE_INJECTED`` in the
audit trail whenever it calls :meth:`inject_noise`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts import (
    ArtifactHash,
    CosineScheduleSample,
    FactorValue,
    hash_artifact,
)

# ---------------------------------------------------------------------------
# Sample
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScheduleSample:
    """One algorithm-layer schedule sample for a single round.

    Frozen and value-comparable: two samples produced from the same
    scheduler and the same ``(outer_cycle_id, round_in_cycle,
    target_round)`` arguments compare equal.
    """

    outer_cycle_id: int
    round_in_cycle: int
    cycle_length: int
    n_cap: float
    n_min: float
    n_max: float
    u_r: float
    family: str
    computed_at_round: int
    schedule_hash: str
    audit_codes: tuple[str, ...] = ()
    """Per-round diagnostic codes emitted by the scheduler (P0-A1).

    Every scheduler tags each sample with at least its family's baseline
    marker (e.g. ``"cosine_baseline"``) so the runner / engine can fan the
    round's schedule provenance into the audit ledger without re-deriving
    which family produced the sample. Defaults to ``()`` so callers that
    construct a sample without codes keep working unchanged.
    """
    evidence_ratio: float | None = None
    """Sheet-vs-cell evidence ratio for the round (P0-A7).

    Set by :class:`CodimensionSheetScheduler` (paper Lemma 2 / Lemma 3);
    ``None`` for every family that does not compute a paper-quantity
    evidence balance, so consumers can branch on ``is None`` rather than
    reading ``scheduler.last_evidence_ratio`` out of band.
    """
    eps_implicit: float | None = None
    """Per-round implicit noise scale in evidence units (paper Theorem 1 / epsilon).

    Populated by schedulers that carry a construction-time
    ``eps_implicit`` (currently :class:`CodimensionSheetScheduler` and
    :class:`EvidenceDrivenScheduler` when wrapping a
    ``profile_residual_fn``-aware base). ``None`` for schedulers
    that have no concept of a paper-quantity epsilon (canonical
    cosine, constant, polynomial, sigmoid). The runner reads this
    field and threads it to the
    :class:`PosteriorSelectionEvaluator` so the per-round
    ``selection_ratio`` responds to scheduler state (per the C4
    investigation, ``docs/r3-survey/09-c4-investigation.md``).
    Defaults to ``None`` so legacy callers that build
    :class:`ScheduleSample` directly keep working unchanged.
    """

    def memory_fraction(self) -> float:
        """Return the per-round memory fraction ``1 - n_cap`` (ADR-0010).

        This is the canonical capacity → memory transform consumed by the
        engine and the universal ``apply_restart_distribution`` boundary.
        The result is clipped to ``[0, 1]``.
        """
        n_cap = float(self.n_cap)
        if not math.isfinite(n_cap):
            raise ValueError(f"n_cap must be finite, got {n_cap!r}")
        return float(max(0.0, min(1.0, 1.0 - n_cap)))

    def as_cosine_schedule_sample(self) -> CosineScheduleSample:
        """Return the equivalent typed-contract :class:`CosineScheduleSample`."""
        return CosineScheduleSample(
            schedule_hash=ArtifactHash(str(self.schedule_hash)),
            outer_cycle_id=int(self.outer_cycle_id),
            round_in_cycle=int(self.round_in_cycle),
            cycle_length=int(self.cycle_length),
            n_cap=FactorValue(float(self.n_cap)),
            n_min=FactorValue(float(self.n_min)),
            n_max=FactorValue(float(self.n_max)),
            u_r=float(self.u_r),
            family=str(self.family),
            computed_at_round=int(self.computed_at_round),
        )


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ScheduleSampleProtocol(Protocol):
    """Structural type for anything a scheduler may return from ``sample``."""

    outer_cycle_id: int
    round_in_cycle: int
    cycle_length: int
    n_cap: float
    n_min: float
    n_max: float
    u_r: float
    family: str
    computed_at_round: int
    schedule_hash: str

    def memory_fraction(self) -> float: ...


@runtime_checkable
class SchedulerProtocol(Protocol):
    """Abstract per-round capacity scheduler.

    Any object implementing these methods can drive the framework.

    Forward noise injection (P0-7): :meth:`inject_noise` is the symmetric
    FORWARD step of the canonical reverse-blend (the merge operator /
    ``apply_restart_distribution`` consume the *reverse* side). Callers
    pass a state, the round's schedule sample, and a deterministic
    ``np.random.Generator``; the scheduler returns a new state with fresh
    noise scaled by the schedule's per-round noise mass. The default
    implementation is ``state + sqrt(n_cap) * generator.standard_normal``,
    which is reproducible given the generator's seed (the round model's
    symmetric forward step, mirroring EDM / score-SDE noise injection).

    Config round-trip (P1-1): every implementation exposes
    :meth:`to_config` / :meth:`from_config` (classmethod) so the schedule
    family + its hyperparameters can be serialized to JSON and replayed
    byte-for-byte.

    Convergence termination (Wave 35 FIX-2): a family MAY additionally
    expose ``should_terminate_round(round_in_cycle=None) -> bool``,
    reporting from the feedback it received via
    :meth:`record_round_feedback` that further rounds would not move
    the metric, so the caller may stop spending NFE.
    :class:`CodimensionSheetScheduler` implements it. The hook is
    **deliberately not a Protocol member**: this Protocol is
    ``runtime_checkable``, so declaring the method here would make
    every family that does not define it fail ``isinstance``. Consumers
    discover it with ``hasattr(scheduler, "should_terminate_round")``
    and treat its absence as "never terminate early"; see
    ``BatchedRunnerConfig.early_termination``.
    """

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the capacity sample for one round. Pure w.r.t. arguments."""
        ...

    def cycle_length(self) -> int:
        """Return the number of rounds in one outer cycle (``>= 1``)."""
        ...

    def schedule_family(self) -> str:
        """Return the algorithm family identifier (e.g. ``cosine_no_restart``)."""
        ...

    def config_hash(self) -> str:
        """Return a stable identifier for the algorithm choice + its config."""
        ...

    def reset(self) -> None:
        """Reset internal state so the scheduler can be re-run from scratch."""
        ...

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Optional hook: feed per-round oracle metrics back into the scheduler.

        The default :class:`SchedulerProtocol` implementations ignore this
        call. Adaptive families (e.g. :class:`ConvergenceAdaptiveScheduler`)
        override it to mutate per-round scheduling parameters based on the
        engine's per-round feedback (W2, coverage, etc.). The runner invokes
        this hook with ``hasattr(scheduler, 'record_round_feedback')`` so
        non-adaptive schedulers continue to work without modification.
        """
        ...

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return the state with fresh noise injected (P0-7).

        The **forward noise injection** step — the symmetric FORWARD
        counterpart of the reverse blend ``apply_restart_distribution``.
        Implementations scale ``generator.standard_normal`` by the
        scheduler-specific per-round *noise mass* (the schedule's
        ``n_cap`` for cosine / linear / constant families; the cached
        paper-quantity ``A_g`` for :class:`CodimensionSheetScheduler`).

        Reproducible: identical ``generator.bit_generator.state`` and
        identical ``state`` always yield identical output. The caller
        owns ``state`` (the scheduler never mutates it); the returned
        array is a fresh allocation.
        """
        ...

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for this scheduler.

        The returned dict round-trips through :meth:`from_config` so
        ``cls.from_config(scheduler.to_config()) == scheduler`` for the
        concrete implementation. Mirrors the ``diffusers`` ``ConfigMixin``
        contract (P1-1).
        """
        ...

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> SchedulerProtocol:
        """Build a scheduler from a ``to_config`` dict (P1-1 round-trip).

        ``cls`` is the concrete implementation class — call sites that
        build a scheduler polymorphically (``build_scheduler_from_config``)
        pass the concrete ``cls`` as the registry's factory.
        """
        ...


def _coerce_int_nonneg(x: object, name: str) -> int:
    if isinstance(x, bool) or not isinstance(x, int):
        raise ValueError(f"{name} must be int, got {x!r}")
    if int(x) < 0:
        raise ValueError(f"{name} must be >= 0, got {x}")
    return int(x)


__all__ = [
    "ScheduleSample",
    "ScheduleSampleProtocol",
    "SchedulerProtocol",
]

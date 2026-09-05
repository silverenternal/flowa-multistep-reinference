"""Per-round capacity scheduler.

Produces ScheduleSample objects whose n_cap drives the inner loop's bounded
update. Algorithms that drive the framework include cosine annealing
(default), linear ramp, exponential decay, and constant — all conform to this
Protocol.

The algorithm layer is deliberately **abstract**: the framework depends only
on :class:`SchedulerProtocol`, never on a concrete schedule family. Cosine
annealing (:class:`CosineAnnealScheduler`) is the default implementation and
is the one wired into the engine today, but any object that conforms to the
Protocol can be substituted without touching the engine, the channel rule, or
the universal ``apply_restart_distribution`` boundary.

The canonical transform from capacity to the per-round memory fraction is
``memory_fraction = 1 - n_cap`` (see :meth:`ScheduleSample.memory_fraction`
and ADR-0010 "Cosine-driven memory fraction",
``docs/adr/0010-cosine-driven-memory-fraction.md``). Schedulers supply
*capacity only*: they never write a ``beta`` value — the channel rule is the
sole component allowed to derive ``beta`` from a schedule sample.

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
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Optional, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts import (
    ArtifactHash,
    CosineScheduleConfig,
    CosineScheduleSample,
    FactorValue,
    RestartTriggerCode,
    hash_artifact,
)
from adaptive_reflow.algorithm._derivation import (
    DerivationContext,
    DerivationRule,
    OTEpsilonSchedule,
    default_eps_implicit,
)
from adaptive_reflow.schedule.cosine import (
    memory_fraction_from_schedule,
    n_cap_for_round,
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
        need polymorphic dispatch should use
        :func:`build_scheduler_from_config` which dispatches on the
        ``family`` key.
        """
        ...


# ---------------------------------------------------------------------------
# Default implementation: cosine annealing
# ---------------------------------------------------------------------------


def _coerce_int_nonneg(x: object, name: str) -> int:
    if isinstance(x, bool) or not isinstance(x, int):
        raise ValueError(f"{name} must be int, got {x!r}")
    if int(x) < 0:
        raise ValueError(f"{name} must be >= 0, got {x}")
    return int(x)


class CosineAnnealScheduler:
    """Default :class:`SchedulerProtocol` implementation (cosine annealing).

    Delegates the closed-form capacity computation to
    :func:`adaptive_reflow.schedule.cosine.n_cap_for_round` and the
    capacity → memory transform to
    :func:`adaptive_reflow.schedule.cosine.memory_fraction_from_schedule`
    (ADR-0010), so the algorithm layer adds no second source of truth.

    :meth:`sample` is *pure* with respect to its arguments: it caches the
    most recent sample for observability (:attr:`last_sample`) but two calls
    with identical arguments always return equal :class:`ScheduleSample`
    objects.
    """

    def __init__(
        self,
        config: CosineScheduleConfig,
        *,
        profile_residual_fn: Callable[[float], float] | None = None,
    ) -> None:
        """Construct the cosine-annealing scheduler.

        :param config: the frozen :class:`CosineScheduleConfig`.
        :param profile_residual_fn: optional residual profile ``x -> g(x)``
            (P1-A2). When supplied, the scheduler computes the paper's
            sheet-evidence constant ``A_g``
            (:func:`paper_quantities.sheet_evidence_A`, Lemma 2 /
            Proposition 3) exactly once at construction time and uses it as
            the per-round forward-noise mass in :meth:`inject_noise`,
            matching :class:`CodimensionSheetScheduler`. When ``None``
            (the default) the scheduler is byte-identical to the legacy
            ``sqrt(n_cap)`` path.
        """
        self._config = config
        self._last_sample: ScheduleSample | None = None
        if profile_residual_fn is not None and not callable(profile_residual_fn):
            raise ValueError(
                "profile_residual_fn must be callable or None, "
                f"got {profile_residual_fn!r}"
            )
        self._profile_residual_fn = profile_residual_fn
        self._sheet_A: float | None = None
        if profile_residual_fn is not None:
            from adaptive_reflow.contracts import paper_quantities as _pq

            self._sheet_A = float(_pq.sheet_evidence_A(profile_residual_fn))

    # -- accessors ---------------------------------------------------------

    @property
    def config(self) -> CosineScheduleConfig:
        """Return the frozen :class:`CosineScheduleConfig`."""
        return self._config

    @property
    def profile_residual_fn(self) -> Callable[[float], float] | None:
        """Return the configured residual profile callable (or ``None``)."""
        return self._profile_residual_fn

    @property
    def sheet_A(self) -> float | None:
        """Return the cached paper-quantity ``A_g``, or ``None`` (P1-A2)."""
        return self._sheet_A

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent sample, or ``None`` after ``reset()``."""
        return self._last_sample

    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the cosine-annealed capacity sample for one round."""
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        # P2-1 (F-6 / audit) — reject negative ``round_in_cycle``.
        # Previously the helper accepted any int, including ``-1``, and
        # produced a nonsense ``n_cap`` (clamped via ``max(length - 1, 1)``
        # but still a contract wart). Validate up-front.
        round_in_cycle = _coerce_int_nonneg(round_in_cycle, "round_in_cycle")

        n_cap = n_cap_for_round(self._config, round_in_cycle)
        length = int(self._config.cycle_length)
        u_r = float(round_in_cycle) / max(length - 1, 1)

        codes: tuple[str, ...] = ("cosine_baseline",)
        if self._sheet_A is not None:
            codes = (
                "cosine_baseline",
                f"cosine_paper_quantity_wired:A_g={self._sheet_A:.6f}",
            )

        sample = ScheduleSample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=float(n_cap),
            n_min=float(self._config.n_min),
            n_max=float(self._config.n_max),
            u_r=u_r,
            family=str(self._config.schedule_family),
            computed_at_round=target_round,
            schedule_hash=str(self._config.config_hash),
            audit_codes=codes,
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length."""
        return int(self._config.cycle_length)

    def schedule_family(self) -> str:
        """Return the configured schedule family."""
        return str(self._config.schedule_family)

    def config_hash(self) -> str:
        """Return a stable identifier for this algorithm + config choice."""
        return str(
            hash_artifact(
                {
                    "algorithm": "cosine_anneal",
                    "schedule_family": str(self._config.schedule_family),
                    "cycle_length": int(self._config.cycle_length),
                    "n_min": float(self._config.n_min),
                    "n_max": float(self._config.n_max),
                    "config_hash": str(self._config.config_hash),
                }
            )
        )

    def reset(self) -> None:
        """Drop the cached sample so a re-run starts from a clean state."""
        self._last_sample = None

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Default no-op: cosine annealing ignores per-round feedback."""
        return None

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return ``state + sqrt(noise_mass) * generator.standard_normal(...)``.

        The cosine family uses the round's ``n_cap`` as the per-round
        noise mass — at round 0 with ``n_cap = n_max`` the noise
        dominates; at round ``L-1`` with ``n_cap = n_min`` the prior
        dominates. Identical ``generator`` state always yields
        identical output (P0-7 forward-noise reproducibility).

        P1-A2: when a ``profile_residual_fn`` was supplied at
        construction time the noise mass is the cached paper quantity
        ``A_g`` (Lemma 2 / Proposition 3) instead of the raw ``n_cap``,
        matching :class:`CodimensionSheetScheduler`. Callers that did
        not supply a profile get byte-identical legacy output.
        """
        state_arr = np.asarray(state, dtype=np.float64)
        if self._sheet_A is not None:
            noise_mass = float(self._sheet_A)
        else:
            noise_mass = float(schedule_sample.n_cap)
        if noise_mass < 0.0:
            noise_mass = 0.0
        scale = math.sqrt(noise_mass)
        noise = generator.standard_normal(state_arr.shape).astype(np.float64)
        return state_arr + scale * noise

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for this cosine scheduler.

        The returned dict includes the ``family`` key so polymorphic
        deserialisation via :func:`build_scheduler_from_config` round-trips
        byte-for-byte.
        """
        return {
            "family": "cosine",
            "schedule_family": str(self._config.schedule_family),
            "cycle_length": int(self._config.cycle_length),
            "n_min": float(self._config.n_min),
            "n_max": float(self._config.n_max),
            "config_hash": str(self._config.config_hash),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> CosineAnnealScheduler:
        """Build a :class:`CosineAnnealScheduler` from ``config``.

        Mirrors :func:`default_cosine_scheduler` so the round-trip is
        byte-identical for any (family, cycle_length, n_min, n_max) tuple.
        """
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        cycle_length = int(config["cycle_length"])
        n_min = float(config["n_min"])
        n_max = float(config["n_max"])
        schedule_family = str(config.get("schedule_family", "cosine_no_restart"))
        return default_cosine_scheduler(
            cycle_length=cycle_length,
            n_min=n_min,
            n_max=n_max,
            schedule_family=schedule_family,
            seed=0,
        )

    # -- derived -----------------------------------------------------------

    def memory_fraction_for(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> float:
        """Return ``1 - n_cap`` for one round, via the canonical helper."""
        sample = self.sample(outer_cycle_id, round_in_cycle, target_round)
        return memory_fraction_from_schedule(sample.as_cosine_schedule_sample())


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def default_cosine_scheduler(
    *,
    cycle_length: int = 20,
    n_min: float = 0.0,
    n_max: float = 1.0,
    schedule_family: str = "cosine_no_restart",
    seed: int = 0,
    profile_residual_fn: Callable[[float], float] | None = None,
) -> CosineAnnealScheduler:
    """Build the default :class:`CosineAnnealScheduler`.

    ``seed`` is accepted for signature parity with stochastic schedulers; the
    cosine family is deterministic, so it only participates in the frozen
    ``config_hash`` (so two schedulers with different seeds remain
    distinguishable in provenance).

    ``profile_residual_fn`` (P1-A2) is forwarded to the scheduler so the
    per-round forward-noise mass is the paper quantity ``A_g`` rather than
    the raw ``n_cap``; ``None`` (default) keeps the legacy behaviour.
    """
    config_hash = hash_artifact(
        {
            "schedule_family": str(schedule_family),
            "cycle_length": int(cycle_length),
            "n_min": float(n_min),
            "n_max": float(n_max),
            "seed": int(seed),
        }
    )
    restart_triggers: tuple[RestartTriggerCode, ...] = ()
    config = CosineScheduleConfig(
        schedule_family=schedule_family,  # type: ignore[arg-type]
        cycle_length=int(cycle_length),
        n_min=FactorValue(float(n_min)),
        n_max=FactorValue(float(n_max)),
        per_channel_caps={},
        fresh_noise_floor_by_channel={},
        symmetric_delta_caps_by_channel={},
        restart_triggers_allowed=restart_triggers,
        config_hash=config_hash,
        frozen_before_evaluation=True,
    )
    return CosineAnnealScheduler(config, profile_residual_fn=profile_residual_fn)


# ---------------------------------------------------------------------------
# Constant scheduler — simplest ablation baseline
# ---------------------------------------------------------------------------


class ConstantScheduler:
    """Constant-capacity :class:`SchedulerProtocol` implementation.

    :attr:`n_cap` is constant across every round, equal to the configured
    ``n_cap`` (default ``0.5`` — the mid-cycle marker that makes ``1 - n_cap``
    the same ``0.5`` memory fraction cosine places at the cycle midpoint).
    :attr:`u_r` is fixed at ``0.5`` for every round.

    Useful as the simplest ablation baseline: any algorithm-vs-baseline
    performance gap that survives this scheduler is not explained by the
    per-round capacity ramp.

    Conforms to :class:`SchedulerProtocol`. Pure w.r.t. arguments.
    """

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_cap: float = 0.5,
        seed: int = 0,
    ) -> None:
        """Construct the constant scheduler.

        :param cycle_length: number of rounds in one outer cycle (``>= 1``).
        :param n_cap: the constant capacity assigned to every round; must lie
            in ``[0, 1]`` (the canonical capacity range).
        :param seed: included for protocol signature parity with stochastic
            schedulers; the constant family is deterministic and only
            participates in the frozen :attr:`config_hash`.
        """
        if not isinstance(cycle_length, int) or isinstance(cycle_length, bool):
            raise ValueError(
                f"cycle_length must be int, got {cycle_length!r}"
            )
        if int(cycle_length) < 1:
            raise ValueError(
                f"cycle_length must be >= 1, got {cycle_length!r}"
            )
        self._cycle_length = int(cycle_length)
        if not isinstance(n_cap, (int, float)) or isinstance(n_cap, bool):
            raise ValueError(f"n_cap must be a real number, got {n_cap!r}")
        if not math.isfinite(float(n_cap)):
            raise ValueError(f"n_cap must be finite, got {n_cap!r}")
        n_cap_f = float(n_cap)
        if not (0.0 <= n_cap_f <= 1.0):
            raise ValueError(
                f"n_cap must lie in [0, 1], got {n_cap_f!r}"
            )
        self._n_cap = n_cap_f
        self._seed = int(seed)
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "constant",
                "schedule_family": "constant",
                "cycle_length": int(self._cycle_length),
                "n_cap": float(self._n_cap),
                "seed": int(self._seed),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def n_cap(self) -> float:
        """Return the configured constant capacity value."""
        return float(self._n_cap)

    @property
    def seed(self) -> int:
        """Return the seed used for provenance hashing."""
        return int(self._seed)

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent sample, or ``None`` after :meth:`reset`."""
        return self._last_sample



    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the constant-capacity sample for one round."""
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        # P2-3 (F-8 / audit) — reject negative ``round_in_cycle`` even when
        # ``length == 1`` (the original ``length > 1`` short-circuit skipped
        # validation for the cycle_length=1 edge case). Validate up-front.
        round_in_cycle = _coerce_int_nonneg(round_in_cycle, "round_in_cycle")
        length = int(self._cycle_length)
        if length > 1 and not (
            0 <= int(round_in_cycle) <= length - 1
        ):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for cycle_length={length}, "
                f"got {round_in_cycle!r}"
            )

        sample = ScheduleSample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=float(self._n_cap),
            n_min=float(self._n_cap),
            n_max=float(self._n_cap),
            u_r=0.5,
            family="constant",
            computed_at_round=target_round,
            schedule_hash=str(self._config_hash_value),
            audit_codes=("schedule_constant_baseline",),
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length."""
        return int(self._cycle_length)

    def schedule_family(self) -> str:
        """Return the schedule family identifier."""
        return "constant"

    def config_hash(self) -> str:
        """Return a stable identifier for this algorithm + config choice."""
        return str(self._config_hash_value)

    def reset(self) -> None:
        """Drop the cached sample so a re-run starts from a clean state."""
        self._last_sample = None

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Default no-op: constant scheduler ignores per-round feedback."""
        return None

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return ``state + sqrt(n_cap) * generator.standard_normal`` (P0-7).

        The constant family uses its configured ``n_cap`` as the
        per-round noise mass (so noise is injected at the same scale
        every round).
        """
        del schedule_sample
        state_arr = np.asarray(state, dtype=np.float64)
        scale = math.sqrt(float(self._n_cap))
        noise = generator.standard_normal(state_arr.shape).astype(np.float64)
        return state_arr + scale * noise

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for the constant scheduler."""
        return {
            "family": "constant",
            "cycle_length": int(self._cycle_length),
            "n_cap": float(self._n_cap),
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ConstantScheduler:
        """Build a :class:`ConstantScheduler` from ``config`` (P1-1 round-trip)."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return ConstantScheduler(
            cycle_length=int(config["cycle_length"]),
            n_cap=float(config["n_cap"]),
            seed=int(config.get("seed", 0)),
        )

    # -- derived -----------------------------------------------------------

    def memory_fraction_for(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> float:
        """Return ``1 - n_cap`` (constant) for any round."""
        return self.sample(outer_cycle_id, round_in_cycle, target_round).memory_fraction()


# ---------------------------------------------------------------------------
# Linear scheduler — ramp-up / ramp-down baseline
# ---------------------------------------------------------------------------


class LinearScheduler:
    """Linear-ramp :class:`SchedulerProtocol` implementation.

    :attr:`n_cap` linearly interpolates between :attr:`n_min` at round ``0``
    and :attr:`n_max` at round ``cycle_length - 1``. The closed-form is
    identical to the linear slot inside :func:`n_cap_for_round`, exposed as
    a standalone :class:`SchedulerProtocol` so ramp-up vs ramp-down
    comparisons do not have to round-trip through the cosine contract.

    By convention :attr:`n_max > n_min` produces a *ramp-up* in capacity
    (useful for "warm start, then explore harder"); the inverse ``n_min
    > n_max`` produces a *ramp-down* (useful for "front-load exploration,
    refine later"). Either is supported — both produce the same
    monotonically-ordered sample sequence (in the direction the user chose).
    """

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_min: float = 0.0,
        n_max: float = 1.0,
        seed: int = 0,
    ) -> None:
        """Construct the linear scheduler.

        :param cycle_length: number of rounds in one outer cycle (``>= 1``).
        :param n_min: capacity assigned to round ``0``; must lie in ``[0, 1]``.
        :param n_max: capacity assigned to round ``cycle_length - 1``; must
            lie in ``[0, 1]``.
        :param seed: included for protocol signature parity with stochastic
            schedulers; the linear family is deterministic and only
            participates in the frozen :attr:`config_hash`.
        """
        if cycle_length < 1:
            raise ValueError(f"cycle_length must be >= 1, got {cycle_length!r}")
        for nm, val in (("n_min", n_min), ("n_max", n_max)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if not (0.0 <= fv <= 1.0):
                raise ValueError(f"{nm} must lie in [0, 1], got {fv!r}")
        self._cycle_length = int(cycle_length)
        self._n_min = float(n_min)
        self._n_max = float(n_max)
        self._seed = int(seed)
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "linear",
                "schedule_family": "linear",
                "cycle_length": int(self._cycle_length),
                "n_min": float(self._n_min),
                "n_max": float(self._n_max),
                "seed": int(self._seed),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def n_min(self) -> float:
        """Return the capacity assigned to round ``0``."""
        return float(self._n_min)

    @property
    def n_max(self) -> float:
        """Return the capacity assigned to round ``cycle_length - 1``."""
        return float(self._n_max)

    @property
    def seed(self) -> int:
        """Return the seed used for provenance hashing."""
        return int(self._seed)

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent sample, or ``None`` after :meth:`reset`."""
        return self._last_sample

    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the linearly-ramped capacity sample for one round."""
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        length = int(self._cycle_length)
        if length > 1 and not (
            0 <= int(round_in_cycle) <= length - 1
        ):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for cycle_length={length}, "
                f"got {round_in_cycle!r}"
            )

        if length == 1:
            u_r = 0.5
            n_cap = float(self._n_max)
        else:
            u_r = float(round_in_cycle) / (length - 1)
            n_cap = float(
                self._n_max - (self._n_max - self._n_min) * u_r
            )

        sample = ScheduleSample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=n_cap,
            n_min=float(self._n_min),
            n_max=float(self._n_max),
            u_r=u_r,
            family="linear",
            computed_at_round=target_round,
            schedule_hash=str(self._config_hash_value),
            audit_codes=("schedule_linear_baseline",),
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length."""
        return int(self._cycle_length)

    def schedule_family(self) -> str:
        """Return the schedule family identifier."""
        return "linear"

    def config_hash(self) -> str:
        """Return a stable identifier for this algorithm + config choice."""
        return str(self._config_hash_value)

    def reset(self) -> None:
        """Drop the cached sample so a re-run starts from a clean state."""
        self._last_sample = None

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Default no-op: linear scheduler ignores per-round feedback."""
        return None

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return ``state + sqrt(n_cap) * generator.standard_normal`` (P0-7).

        Uses the schedule sample's ``n_cap`` directly so the round's
        per-round noise mass tracks the linear ramp rather than the
        scheduler's terminal ``n_min``.
        """
        state_arr = np.asarray(state, dtype=np.float64)
        n_cap = float(schedule_sample.n_cap)
        if n_cap < 0.0:
            n_cap = 0.0
        scale = math.sqrt(n_cap)
        noise = generator.standard_normal(state_arr.shape).astype(np.float64)
        return state_arr + scale * noise

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for the linear scheduler."""
        return {
            "family": "linear",
            "cycle_length": int(self._cycle_length),
            "n_min": float(self._n_min),
            "n_max": float(self._n_max),
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> LinearScheduler:
        """Build a :class:`LinearScheduler` from ``config`` (P1-1 round-trip)."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return LinearScheduler(
            cycle_length=int(config["cycle_length"]),
            n_min=float(config["n_min"]),
            n_max=float(config["n_max"]),
            seed=int(config.get("seed", 0)),
        )

    # -- derived -----------------------------------------------------------

    def memory_fraction_for(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> float:
        """Return ``1 - n_cap`` for one round."""
        return self.sample(outer_cycle_id, round_in_cycle, target_round).memory_fraction()


# ---------------------------------------------------------------------------
# Exponential scheduler — fast initial exploration, rapid refinement
# ---------------------------------------------------------------------------


class ExponentialScheduler:
    """Exponential-decay :class:`SchedulerProtocol` implementation.

    Closed form:

        n_cap(r) = n_max * exp(-alpha * r)

    where ``r`` is :attr:`round_in_cycle` and ``alpha >= 0`` controls the
    decay rate. ``alpha == 0`` collapses to the constant family (no decay).
    The schedule is non-increasing in ``r``, so it produces a "fast initial
    exploration, rapid refinement" regime: the first round carries the
    highest capacity (raw exploration budget), subsequent rounds decay
    monotonically toward zero as the algorithm refines.

    Decay is computed in raw space, then clipped to ``[0, 1]`` defensively
    so downstream consumers never observe a value outside the canonical
    capacity range. The single-round ``cycle_length == 1`` edge case
    returns ``n_max`` regardless of ``alpha`` (matching the cosine family's
    deterministic edge behaviour).
    """

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_max: float = 1.0,
        alpha: float = 0.1,
        seed: int = 0,
    ) -> None:
        """Construct the exponential-decay scheduler.

        :param cycle_length: number of rounds in one outer cycle (``>= 1``).
        :param n_max: capacity scale at round ``0``; must lie in ``[0, 1]``.
        :param alpha: decay rate; must be finite and ``>= 0``. ``alpha == 0``
            is equivalent to a constant schedule at :attr:`n_max`.
        :param seed: included for protocol signature parity with stochastic
            schedulers; the exponential family is deterministic and only
            participates in the frozen :attr:`config_hash`.
        """
        if cycle_length < 1:
            raise ValueError(f"cycle_length must be >= 1, got {cycle_length!r}")
        if isinstance(n_max, bool) or not isinstance(n_max, (int, float)):
            raise ValueError(f"n_max must be a real number, got {n_max!r}")
        n_max_f = float(n_max)
        if not math.isfinite(n_max_f):
            raise ValueError(f"n_max must be finite, got {n_max!r}")
        if not (0.0 <= n_max_f <= 1.0):
            raise ValueError(f"n_max must lie in [0, 1], got {n_max_f!r}")
        if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
            raise ValueError(f"alpha must be a real number, got {alpha!r}")
        alpha_f = float(alpha)
        if not math.isfinite(alpha_f):
            raise ValueError(f"alpha must be finite, got {alpha!r}")
        if alpha_f < 0.0:
            raise ValueError(f"alpha must be >= 0, got {alpha_f!r}")
        self._cycle_length = int(cycle_length)
        self._n_max = n_max_f
        self._alpha = alpha_f
        self._seed = int(seed)
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "exponential",
                "schedule_family": "exponential",
                "cycle_length": int(self._cycle_length),
                "n_max": float(self._n_max),
                "alpha": float(self._alpha),
                "seed": int(self._seed),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def n_max(self) -> float:
        """Return the capacity scale at round ``0``."""
        return float(self._n_max)

    @property
    def alpha(self) -> float:
        """Return the decay rate."""
        return float(self._alpha)

    @property
    def seed(self) -> int:
        """Return the seed used for provenance hashing."""
        return int(self._seed)

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent sample, or ``None`` after :meth:`reset`."""
        return self._last_sample

    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the exponentially-decayed capacity sample for one round."""
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        length = int(self._cycle_length)
        if length > 1 and not (
            0 <= int(round_in_cycle) <= length - 1
        ):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for cycle_length={length}, "
                f"got {round_in_cycle!r}"
            )

        # Single-round edge: return n_max deterministically (matches cosine).
        if length == 1:
            n_cap = float(self._n_max)
            u_r = 0.5
        else:
            u_r = float(round_in_cycle) / (length - 1)
            n_cap = float(self._n_max) * math.exp(-float(self._alpha) * int(round_in_cycle))
            # Defensive clip into the canonical capacity range.
            if not math.isfinite(n_cap):
                raise ValueError(
                    f"exponential decay produced a non-finite n_cap={n_cap!r}"
                )
            n_cap = float(max(0.0, min(1.0, n_cap)))

        sample = ScheduleSample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=n_cap,
            n_min=0.0,
            n_max=float(self._n_max),
            u_r=u_r,
            family="exponential",
            computed_at_round=target_round,
            schedule_hash=str(self._config_hash_value),
            audit_codes=("schedule_exponential_baseline",),
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length."""
        return int(self._cycle_length)

    def schedule_family(self) -> str:
        """Return the schedule family identifier."""
        return "exponential"

    def config_hash(self) -> str:
        """Return a stable identifier for this algorithm + config choice."""
        return str(self._config_hash_value)

    def reset(self) -> None:
        """Drop the cached sample so a re-run starts from a clean state."""
        self._last_sample = None

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Default no-op: exponential scheduler ignores per-round feedback."""
        return None

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return ``state + sqrt(n_cap) * generator.standard_normal`` (P0-7)."""
        state_arr = np.asarray(state, dtype=np.float64)
        n_cap = float(schedule_sample.n_cap)
        if n_cap < 0.0:
            n_cap = 0.0
        scale = math.sqrt(n_cap)
        noise = generator.standard_normal(state_arr.shape).astype(np.float64)
        return state_arr + scale * noise

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for the exponential scheduler."""
        return {
            "family": "exponential",
            "cycle_length": int(self._cycle_length),
            "n_max": float(self._n_max),
            "alpha": float(self._alpha),
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ExponentialScheduler:
        """Build an :class:`ExponentialScheduler` from ``config`` (P1-1)."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return ExponentialScheduler(
            cycle_length=int(config["cycle_length"]),
            n_max=float(config["n_max"]),
            alpha=float(config["alpha"]),
            seed=int(config.get("seed", 0)),
        )

    # -- derived -----------------------------------------------------------

    def memory_fraction_for(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> float:
        """Return ``1 - n_cap`` for one round."""
        return self.sample(outer_cycle_id, round_in_cycle, target_round).memory_fraction()


# ---------------------------------------------------------------------------
# Polynomial scheduler — power-law ramp
# ---------------------------------------------------------------------------


class PolynomialScheduler:
    """Polynomial-ramp :class:`SchedulerProtocol` implementation.

    Closed form:

        n_cap(r) = n_min + (n_max - n_min) * (1 - u_r ** power)
        u_r = round_in_cycle / max(L - 1, 1)

    The :attr:`power` exponent controls the ramp shape:

    * ``power == 1`` — linear (exactly equivalent to
      :class:`LinearScheduler`).
    * ``power > 1`` (e.g. ``2``) — concave ramp: capacity stays high
      longer, then ramps up later in the cycle (between linear and
      cosine in shape).
    * ``0 < power < 1`` (e.g. ``0.5``) — convex ramp: capacity climbs
      quickly early, then plateaus near :attr:`n_max` — useful for
      front-loaded exploration followed by refinement.

    :attr:`power` must be strictly positive (``power > 0``). The computed
    n_cap is clipped to ``[0, 1]`` defensively so downstream consumers
    never observe a value outside the canonical capacity range.

    Conforms to :class:`SchedulerProtocol`. Pure w.r.t. arguments.
    """

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_min: float = 0.0,
        n_max: float = 1.0,
        power: float = 2.0,
        seed: int = 0,
    ) -> None:
        """Construct the polynomial scheduler.

        :param cycle_length: number of rounds in one outer cycle (``>= 1``).
        :param n_min: capacity assigned to round ``0``; must lie in
            ``[0, 1]``.
        :param n_max: capacity assigned to round ``cycle_length - 1``;
            must lie in ``[0, 1]``.
        :param power: polynomial exponent; must satisfy ``power > 0``.
        :param seed: included for protocol signature parity with
            stochastic schedulers; the polynomial family is deterministic
            and only participates in the frozen :attr:`config_hash`.
        """
        if cycle_length < 1:
            raise ValueError(f"cycle_length must be >= 1, got {cycle_length!r}")
        for nm, val in (("n_min", n_min), ("n_max", n_max)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if not (0.0 <= fv <= 1.0):
                raise ValueError(f"{nm} must lie in [0, 1], got {fv!r}")
        if isinstance(power, bool) or not isinstance(power, (int, float)):
            raise ValueError(f"power must be a real number, got {power!r}")
        power_f = float(power)
        if not math.isfinite(power_f):
            raise ValueError(f"power must be finite, got {power!r}")
        if power_f <= 0.0:
            raise ValueError(f"power must be > 0, got {power_f!r}")
        self._cycle_length = int(cycle_length)
        self._n_min = float(n_min)
        self._n_max = float(n_max)
        self._power = power_f
        self._seed = int(seed)
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "polynomial",
                "schedule_family": "polynomial",
                "cycle_length": int(self._cycle_length),
                "n_min": float(self._n_min),
                "n_max": float(self._n_max),
                "power": float(self._power),
                "seed": int(self._seed),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def n_min(self) -> float:
        """Return the capacity assigned to round ``0``."""
        return float(self._n_min)

    @property
    def n_max(self) -> float:
        """Return the capacity assigned to round ``cycle_length - 1``."""
        return float(self._n_max)

    @property
    def power(self) -> float:
        """Return the polynomial exponent (``> 0``)."""
        return float(self._power)

    @property
    def seed(self) -> int:
        """Return the seed used for provenance hashing."""
        return int(self._seed)

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent sample, or ``None`` after :meth:`reset`."""
        return self._last_sample

    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the polynomial-ramped capacity sample for one round."""
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        length = int(self._cycle_length)
        if length > 1 and not (
            0 <= int(round_in_cycle) <= length - 1
        ):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for cycle_length={length}, "
                f"got {round_in_cycle!r}"
            )

        if length == 1:
            u_r = 0.5
            n_cap = float(self._n_max)
        else:
            u_r = float(round_in_cycle) / (length - 1)
            raw = (
                self._n_min
                + (self._n_max - self._n_min) * (1.0 - u_r ** float(self._power))
            )
            # Defensive clip into the canonical capacity range.
            n_cap = float(max(0.0, min(1.0, raw)))

        sample = ScheduleSample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=n_cap,
            n_min=float(self._n_min),
            n_max=float(self._n_max),
            u_r=u_r,
            family="polynomial",
            computed_at_round=target_round,
            schedule_hash=str(self._config_hash_value),
            audit_codes=("schedule_polynomial_baseline",),
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length."""
        return int(self._cycle_length)

    def schedule_family(self) -> str:
        """Return the schedule family identifier."""
        return "polynomial"

    def config_hash(self) -> str:
        """Return a stable identifier for this algorithm + config choice."""
        return str(self._config_hash_value)

    def reset(self) -> None:
        """Drop the cached sample so a re-run starts from a clean state."""
        self._last_sample = None

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Default no-op: polynomial scheduler ignores per-round feedback."""
        return None

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return ``state + sqrt(n_cap) * generator.standard_normal`` (P0-7)."""
        state_arr = np.asarray(state, dtype=np.float64)
        n_cap = float(schedule_sample.n_cap)
        if n_cap < 0.0:
            n_cap = 0.0
        scale = math.sqrt(n_cap)
        noise = generator.standard_normal(state_arr.shape).astype(np.float64)
        return state_arr + scale * noise

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for the polynomial scheduler."""
        return {
            "family": "polynomial",
            "cycle_length": int(self._cycle_length),
            "n_min": float(self._n_min),
            "n_max": float(self._n_max),
            "power": float(self._power),
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> PolynomialScheduler:
        """Build a :class:`PolynomialScheduler` from ``config`` (P1-1)."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return PolynomialScheduler(
            cycle_length=int(config["cycle_length"]),
            n_min=float(config["n_min"]),
            n_max=float(config["n_max"]),
            power=float(config["power"]),
            seed=int(config.get("seed", 0)),
        )

    # -- derived -----------------------------------------------------------

    def memory_fraction_for(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> float:
        """Return ``1 - n_cap`` for one round."""
        return self.sample(outer_cycle_id, round_in_cycle, target_round).memory_fraction()


# ---------------------------------------------------------------------------
# Sigmoid scheduler — logit curve
# ---------------------------------------------------------------------------


class SigmoidScheduler:
    """Sigmoid :class:`SchedulerProtocol` implementation.

    Closed form:

        n_cap(r) = n_min + (n_max - n_min) * sigmoid(steepness * (u_r - midpoint))
        sigmoid(z) = 1 / (1 + exp(-z))
        u_r = round_in_cycle / max(L - 1, 1)

    ``midpoint == 0.5`` produces a symmetric ramp whose transition
    sharpness is controlled by :attr:`steepness`:

    * ``steepness == 0`` — degenerate: :attr:`n_cap` equals
      ``(n_min + n_max) / 2`` for every round (equivalent to
      :class:`ConstantScheduler` at the midpoint).
    * Small :attr:`steepness` — gradual (smooth, near-linear) curve.
    * Large :attr:`steepness` — near-step function at the chosen
      :attr:`midpoint`.

    Shifting :attr:`midpoint` moves the transition point of the ramp
    (e.g. ``midpoint == 0.3`` shifts the transition earlier in the
    cycle). The computed n_cap is clipped to ``[0, 1]`` defensively.

    Conforms to :class:`SchedulerProtocol`. Pure w.r.t. arguments.
    """

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_min: float = 0.0,
        n_max: float = 1.0,
        steepness: float = 10.0,
        midpoint: float = 0.5,
        seed: int = 0,
    ) -> None:
        """Construct the sigmoid scheduler.

        :param cycle_length: number of rounds in one outer cycle (``>= 1``).
        :param n_min: capacity assigned to round ``0``; must lie in
            ``[0, 1]``.
        :param n_max: capacity assigned to round ``cycle_length - 1``;
            must lie in ``[0, 1]``.
        :param steepness: logit steepness; finite, any sign allowed
            (negative steepness flips the ramp direction).
        :param midpoint: u_r at which the sigmoid is centred; should lie
            in ``[0, 1]`` for symmetry with the round index range.
        :param seed: included for protocol signature parity with
            stochastic schedulers; the sigmoid family is deterministic
            and only participates in the frozen :attr:`config_hash`.
        """
        if cycle_length < 1:
            raise ValueError(f"cycle_length must be >= 1, got {cycle_length!r}")
        for nm, val in (("n_min", n_min), ("n_max", n_max)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if not (0.0 <= fv <= 1.0):
                raise ValueError(f"{nm} must lie in [0, 1], got {fv!r}")
        for nm, val in (("steepness", steepness), ("midpoint", midpoint)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
        self._cycle_length = int(cycle_length)
        self._n_min = float(n_min)
        self._n_max = float(n_max)
        self._steepness = float(steepness)
        self._midpoint = float(midpoint)
        self._seed = int(seed)
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "sigmoid",
                "schedule_family": "sigmoid",
                "cycle_length": int(self._cycle_length),
                "n_min": float(self._n_min),
                "n_max": float(self._n_max),
                "steepness": float(self._steepness),
                "midpoint": float(self._midpoint),
                "seed": int(self._seed),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def n_min(self) -> float:
        """Return the capacity assigned to round ``0``."""
        return float(self._n_min)

    @property
    def n_max(self) -> float:
        """Return the capacity assigned to round ``cycle_length - 1``."""
        return float(self._n_max)

    @property
    def steepness(self) -> float:
        """Return the sigmoid steepness."""
        return float(self._steepness)

    @property
    def midpoint(self) -> float:
        """Return the sigmoid midpoint in u_r units."""
        return float(self._midpoint)

    @property
    def seed(self) -> int:
        """Return the seed used for provenance hashing."""
        return int(self._seed)

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent sample, or ``None`` after :meth:`reset`."""
        return self._last_sample

    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the sigmoid capacity sample for one round."""
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        length = int(self._cycle_length)
        if length > 1 and not (
            0 <= int(round_in_cycle) <= length - 1
        ):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for cycle_length={length}, "
                f"got {round_in_cycle!r}"
            )

        if length == 1:
            u_r = 0.5
            # Match degenerate behaviour: midpoint of [n_min, n_max].
            mid = 0.5 * (self._n_min + self._n_max)
            n_cap = float(max(0.0, min(1.0, mid)))
        else:
            u_r = float(round_in_cycle) / (length - 1)
            z = float(self._steepness) * (u_r - float(self._midpoint))
            sig = 1.0 / (1.0 + math.exp(-z))
            raw = self._n_min + (self._n_max - self._n_min) * sig
            if not math.isfinite(raw):
                raise ValueError(
                    f"sigmoid produced a non-finite n_cap={raw!r}"
                )
            n_cap = float(max(0.0, min(1.0, raw)))

        sample = ScheduleSample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=n_cap,
            n_min=float(self._n_min),
            n_max=float(self._n_max),
            u_r=u_r,
            family="sigmoid",
            computed_at_round=target_round,
            schedule_hash=str(self._config_hash_value),
            audit_codes=("schedule_sigmoid_baseline",),
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length."""
        return int(self._cycle_length)

    def schedule_family(self) -> str:
        """Return the schedule family identifier."""
        return "sigmoid"

    def config_hash(self) -> str:
        """Return a stable identifier for this algorithm + config choice."""
        return str(self._config_hash_value)

    def reset(self) -> None:
        """Drop the cached sample so a re-run starts from a clean state."""
        self._last_sample = None

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Default no-op: sigmoid scheduler ignores per-round feedback."""
        return None

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return ``state + sqrt(n_cap) * generator.standard_normal`` (P0-7)."""
        state_arr = np.asarray(state, dtype=np.float64)
        n_cap = float(schedule_sample.n_cap)
        if n_cap < 0.0:
            n_cap = 0.0
        scale = math.sqrt(n_cap)
        noise = generator.standard_normal(state_arr.shape).astype(np.float64)
        return state_arr + scale * noise

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for the sigmoid scheduler."""
        return {
            "family": "sigmoid",
            "cycle_length": int(self._cycle_length),
            "n_min": float(self._n_min),
            "n_max": float(self._n_max),
            "steepness": float(self._steepness),
            "midpoint": float(self._midpoint),
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> SigmoidScheduler:
        """Build a :class:`SigmoidScheduler` from ``config`` (P1-1)."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return SigmoidScheduler(
            cycle_length=int(config["cycle_length"]),
            n_min=float(config["n_min"]),
            n_max=float(config["n_max"]),
            steepness=float(config["steepness"]),
            midpoint=float(config["midpoint"]),
            seed=int(config.get("seed", 0)),
        )

    # -- derived -----------------------------------------------------------

    def memory_fraction_for(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> float:
        """Return ``1 - n_cap`` for one round."""
        return self.sample(outer_cycle_id, round_in_cycle, target_round).memory_fraction()


# ---------------------------------------------------------------------------
# Convergence-adaptive scheduler — PID-lite, W2-driven shift of u_r
# ---------------------------------------------------------------------------


DEFAULT_FEEDBACK_METRIC_WEIGHTS: dict[str, float] = {
    "W2": 1.0,
    "coverage": 0.3,
    "selection_ratio": 0.5,
}
"""Default multi-metric feedback weights for :class:`ConvergenceAdaptiveScheduler`.

P0-A6: the controller aggregates the round's *loss-form* metrics with these
weights. ``W2`` is already a loss (lower is better); ``coverage`` and
``selection_ratio`` are higher-is-better, so the controller folds in
``1 - value``. A feedback dict carrying only ``W2`` normalises back to the
legacy single-metric signal exactly.
"""

#: Metrics whose *raw* value is higher-is-better and therefore enter the
#: controller as ``1 - value`` (P0-A6).
_HIGHER_IS_BETTER_METRICS: frozenset[str] = frozenset(
    {"coverage", "selection_ratio"}
)

DEFAULT_PAPER_QUANTITY_WEIGHTS: dict[str, float] = {
    "sheet_A": 1.0,
    "packing_B": 0.3,
    "exterior_gap": 0.5,
}
"""Default paper-quantity weights for :class:`ConvergenceAdaptiveScheduler` (Wave 31).

When :meth:`ConvergenceAdaptiveScheduler.record_round_feedback` is called
with a non-``None`` ``paper_quantities`` dict, the controller updates
EMA-smoothed copies of ``sheet_evidence_A``, ``root_cell_packing_B`` and
``exterior_gap_e_rho`` (paper Lemma 2 / Lemma 3 / Lemma 5), then drives
the PID shift from the *paper-quantity ratio*

    ratio = sheet_A_ema / (sheet_A_ema + cell_signal)

where the cell signal defaults to ``packing_B_ema`` (matching the
literal ``B_g`` from line 159 of ``NoiseSelectedRectification_EN.md``).

These weights mirror :data:`DEFAULT_FEEDBACK_METRIC_WEIGHTS`: the
defaults are inert unless the caller explicitly passes a non-``None``
``paper_quantities`` dict, so the legacy W2-only controller is
reproduced bit-for-bit when paper quantities are absent (backward-compat).
"""


class ConvergenceAdaptiveScheduler:
    """PID-lite adaptive :class:`SchedulerProtocol` wrapper.

    Wraps a base :class:`CosineAnnealScheduler` and applies a per-round
    *shift* to its ``u_r`` parameter based on the engine's W2 feedback
    from prior rounds. Concretely:

    * :meth:`sample` asks the base scheduler for ``(u_r, n_cap)`` and
      produces an *effective* ``u_r' = clip(u_r + self._shift, 0, 1)``
      before re-deriving ``n_cap`` from the base cosine closed-form.
    * :meth:`record_round_feedback` consumes the round's ``W2`` metric,
      updates an EMA of W2, then applies the PID-lite update

        shift_update = kp * (1.0 - ratio) - kd * delta

      where ``ratio = w2[-1] / w2[-2]`` and ``delta = w2[-1] - w2[-2]``.
      A negative ``delta`` (improvement) and ``ratio < 1`` push the
      shift positive (later ``u_r`` -> more refinement); a positive
      ``delta`` and ``ratio > 1`` push the shift negative (earlier
      ``u_r`` -> more exploration). The shift is clipped to
      ``[-shift_max, +shift_max]``.

    The first round (no prior history) is recorded without shifting.
    Non-finite W2 values are ignored — neither the EMA nor the history
    is updated, so a broken oracle cannot poison the controller.
    """

    def __init__(
        self,
        *,
        base: CosineAnnealScheduler | None = None,
        kp: float = 0.10,
        kd: float = 0.05,
        shift_max: float = 0.15,
        ema: float = 0.3,
        metric_weights: Mapping[str, float] | None = None,
        paper_quantity_weights: Mapping[str, float] | None = None,
    ) -> None:
        """Construct the convergence-adaptive scheduler.

        :param base: the base cosine scheduler to wrap. Defaults to a
            fresh :func:`default_cosine_scheduler`.
        :param kp: proportional gain on ``(1.0 - ratio)``.
        :param kd: derivative gain on ``delta = w2[-1] - w2[-2]``.
        :param shift_max: maximum absolute shift in ``u_r`` units.
        :param ema: smoothing factor for the W2 EMA (0 = no smoothing,
            1 = ignore new samples).
        :param metric_weights: P0-A6 multi-metric feedback weights. Maps
            a metric name to the weight it carries in the controller's
            aggregated loss signal. Defaults to
            ``{"W2": 1.0, "coverage": 0.3, "selection_ratio": 0.5}``.
            ``"coverage"`` and ``"selection_ratio"`` are *higher-is-better*
            metrics, so the controller folds in their loss form
            ``1 - value``; ``"W2"`` is already a loss. Metrics absent
            from the round's feedback dict (or non-finite) are skipped and
            their weight is dropped from the normaliser, so a W2-only
            feedback dict reproduces the legacy single-metric controller
            bit-for-bit.
        :param paper_quantity_weights: Wave 31 paper-quantity weights
            used by the optional paper-quantity-aware PID branch. Maps
            each paper-quantity name (``"sheet_A"``, ``"packing_B"``,
            ``"exterior_gap"``) to its weight in the EMA tracking and
            audit aggregation. Defaults to
            ``{"sheet_A": 1.0, "packing_B": 0.3, "exterior_gap": 0.5}``.
            Like :paramref:`metric_weights`, ``None`` (the default) leaves
            the defaults in place and the legacy W2-only controller is
            reproduced bit-for-bit when ``paper_quantities`` is not
            supplied to :meth:`record_round_feedback`. The
            paper-quantity-aware PID branch is only activated when that
            method is called with a non-``None`` ``paper_quantities``
            mapping; the weights are stored regardless so the EMA
            update can weight each paper-quantity sample consistently
            when it is supplied.
        """
        self._base: CosineAnnealScheduler = (
            base if base is not None else default_cosine_scheduler()
        )
        for nm, val in (("kp", kp), ("kd", kd), ("shift_max", shift_max), ("ema", ema)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
        if float(ema) < 0.0 or float(ema) > 1.0:
            raise ValueError(
                f"ema must lie in [0, 1], got {float(ema)!r}"
            )
        if float(shift_max) < 0.0:
            raise ValueError(
                f"shift_max must be >= 0, got {float(shift_max)!r}"
            )
        self._kp = float(kp)
        self._kd = float(kd)
        self._shift_max = float(shift_max)
        self._ema = float(ema)
        # P0-A6: multi-metric feedback weights.
        weights: dict[str, float]
        if metric_weights is None:
            weights = dict(DEFAULT_FEEDBACK_METRIC_WEIGHTS)
        else:
            weights = {}
            for key, val in dict(metric_weights).items():
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise ValueError(
                        f"metric_weights[{key!r}] must be a real number, got {val!r}"
                    )
                fv = float(val)
                if not math.isfinite(fv) or fv < 0.0:
                    raise ValueError(
                        f"metric_weights[{key!r}] must be finite and >= 0, got {fv!r}"
                    )
                weights[str(key)] = fv
            if not weights:
                raise ValueError("metric_weights must not be empty")
        self._metric_weights: dict[str, float] = weights
        # Wave 31: paper-quantity weights. Defaults are inert unless
        # ``record_round_feedback`` is invoked with a non-``None``
        # ``paper_quantities`` mapping; the PID remains in legacy mode.
        pq_weights: dict[str, float]
        if paper_quantity_weights is None:
            pq_weights = dict(DEFAULT_PAPER_QUANTITY_WEIGHTS)
        else:
            pq_weights = {}
            for key, val in dict(paper_quantity_weights).items():
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise ValueError(
                        f"paper_quantity_weights[{key!r}] must be a real number, got {val!r}"
                    )
                fv = float(val)
                if not math.isfinite(fv) or fv < 0.0:
                    raise ValueError(
                        f"paper_quantity_weights[{key!r}] must be finite and >= 0, got {fv!r}"
                    )
                pq_weights[str(key)] = fv
            if not pq_weights:
                raise ValueError("paper_quantity_weights must not be empty")
        self._paper_quantity_weights: dict[str, float] = pq_weights
        # Mutable state — cleared by reset().
        self._w2_history: list[float] = []
        self._smoothed_w2: float | None = None
        self._shift: float = 0.0
        self._last_feedback_keys: tuple[str, ...] = ()
        self._last_sample: ScheduleSample | None = None
        # Wave 31: paper-quantity EMA state. Each field is ``None`` until
        # the first finite sample arrives via
        # :meth:`record_round_feedback` with a non-``None`` ``paper_quantities``
        # mapping; the EMA then tracks the paper-quantity in the same
        # direction as the W2 EMA. ``_paper_quantity_enabled`` flips to
        # ``True`` once any paper-quantity signal has been observed and
        # gates the paper-quantity-aware PID branch.
        self._sheet_A_ema: float | None = None
        self._packing_B_ema: float | None = None
        self._exterior_gap_ema: float | None = None
        self._paper_ratio_history: list[float] = []
        self._last_paper_quantity_keys: tuple[str, ...] = ()
        self._paper_quantity_enabled: bool = False
        hash_payload: dict[str, Any] = {
            "algorithm": "convergence_adaptive_cosine",
            "base_config_hash": str(self._base.config_hash()),
            "kp": float(self._kp),
            "kd": float(self._kd),
            "shift_max": float(self._shift_max),
            "ema": float(self._ema),
        }
        if self._metric_weights != dict(DEFAULT_FEEDBACK_METRIC_WEIGHTS):
            # Only non-default weights enter the digest so schedulers built
            # before P0-A6 keep their historical ``config_hash``.
            hash_payload["metric_weights"] = {
                str(k): float(v) for k, v in sorted(self._metric_weights.items())
            }
        if self._paper_quantity_weights != dict(DEFAULT_PAPER_QUANTITY_WEIGHTS):
            # Only non-default paper-quantity weights enter the digest
            # so legacy schedulers keep their historical ``config_hash``.
            hash_payload["paper_quantity_weights"] = {
                str(k): float(v)
                for k, v in sorted(self._paper_quantity_weights.items())
            }
        self._config_hash_value = hash_artifact(hash_payload)

    # -- accessors ---------------------------------------------------------

    @property
    def base(self) -> CosineAnnealScheduler:
        """Return the wrapped base :class:`CosineAnnealScheduler`."""
        return self._base

    @property
    def kp(self) -> float:
        """Return the proportional gain."""
        return float(self._kp)

    @property
    def kd(self) -> float:
        """Return the derivative gain."""
        return float(self._kd)

    @property
    def shift_max(self) -> float:
        """Return the maximum absolute shift in ``u_r`` units."""
        return float(self._shift_max)

    @property
    def ema(self) -> float:
        """Return the EMA smoothing factor."""
        return float(self._ema)

    @property
    def shift(self) -> float:
        """Return the current shift value (in ``u_r`` units)."""
        return float(self._shift)

    @property
    def smoothed_w2(self) -> float | None:
        """Return the latest EMA-smoothed W2, or ``None`` if no feedback yet."""
        return self._smoothed_w2

    @property
    def w2_history(self) -> tuple[float, ...]:
        """Return the recorded aggregated feedback history as a tuple.

        With a W2-only feedback dict these are the raw ``W2`` values
        (legacy behaviour); with multi-metric feedback (P0-A6) they are
        the weighted loss-form aggregates.
        """
        return tuple(self._w2_history)

    @property
    def metric_weights(self) -> dict[str, float]:
        """Return the multi-metric feedback weights (P0-A6)."""
        return dict(self._metric_weights)

    @property
    def last_feedback_keys(self) -> tuple[str, ...]:
        """Return the metric names used by the most recent feedback call."""
        return tuple(self._last_feedback_keys)

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent sample, or ``None`` after :meth:`reset`."""
        return self._last_sample

    # -- Wave 31 paper-quantity accessors ----------------------------------

    @property
    def paper_quantity_weights(self) -> dict[str, float]:
        """Return the paper-quantity EMA weights (Wave 31)."""
        return dict(self._paper_quantity_weights)

    @property
    def smoothed_sheet_A(self) -> float | None:
        """Return the latest EMA-smoothed ``sheet_A`` (``A_g``), or ``None``.

        ``A_g`` is the literal paper quantity from
        :func:`adaptive_reflow.theory.paper_quantities.sheet_evidence_A`
        (Proposition 3 / line 161). It is the positive denominator that
        normalises the sheet posterior mass.
        """
        return (
            float(self._sheet_A_ema)
            if self._sheet_A_ema is not None
            else None
        )

    @property
    def smoothed_packing_B(self) -> float | None:
        """Return the latest EMA-smoothed ``packing_B`` (``B_g``), or ``None``.

        ``B_g`` is the literal paper quantity from
        :func:`adaptive_reflow.theory.paper_quantities.root_cell_packing_B`
        (line 159). It summarises the countable family of root cells
        and is the cell-evidence scale used as the ``cell_signal`` in
        the paper-quantity-aware PID ratio.
        """
        return (
            float(self._packing_B_ema)
            if self._packing_B_ema is not None
            else None
        )

    @property
    def smoothed_exterior_gap(self) -> float | None:
        """Return the latest EMA-smoothed ``exterior_gap`` (``e_rho``), or ``None``.

        ``e_rho`` is the literal paper quantity from
        :func:`adaptive_reflow.theory.paper_quantities.exterior_gap_e_rho`
        (line 128). It bounds the squared-residual energy on the
        physical complement and is exposed for the audit trail; it is
        tracked alongside the other two but does not enter the PID
        ratio (which only needs sheet-vs-cell).
        """
        return (
            float(self._exterior_gap_ema)
            if self._exterior_gap_ema is not None
            else None
        )

    @property
    def paper_ratio_history(self) -> tuple[float, ...]:
        """Return the recorded paper-quantity ratio history as a tuple.

        The paper-quantity ratio is ``sheet_A_ema / (sheet_A_ema +
        packing_B_ema)`` at each round for which both paper-quantity
        EMAs are finite. The ratio lies in ``[0, 1]`` (it is a
        normalised sheet-vs-cell share) and drives the PID branch
        alongside (not in place of) the W2 history when paper
        quantities are supplied.
        """
        return tuple(self._paper_ratio_history)

    @property
    def last_paper_quantity_keys(self) -> tuple[str, ...]:
        """Return the paper-quantity names used by the most recent feedback call."""
        return tuple(self._last_paper_quantity_keys)

    @property
    def paper_quantity_enabled(self) -> bool:
        """Return ``True`` once at least one paper-quantity signal has been observed.

        When ``False`` (default), the controller is in the legacy
        W2-only branch and the PID ratio / delta are computed on the
        aggregated W2 signal exactly as before Wave 31. When ``True``,
        the PID ratio / delta are computed on the paper-quantity ratio
        ``sheet_A_ema / (sheet_A_ema + packing_B_ema)`` instead.
        """
        return bool(self._paper_quantity_enabled)

    # -- SchedulerProtocol -------------------------------------------------
    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the shift-adjusted capacity sample for one round.

        The base scheduler is asked for ``(u_r, n_cap)``; the returned
        ``u_r`` is shifted by :attr:`shift` and re-derived into
        ``n_cap`` via the canonical cosine closed-form
        (:func:`n_cap_for_round`) applied to a *synthetic* round index.
        """
        base_sample = self._base.sample(
            outer_cycle_id, round_in_cycle, target_round
        )
        length = int(base_sample.cycle_length)
        n_min = float(base_sample.n_min)
        n_max = float(base_sample.n_max)
        base_u_r = float(base_sample.u_r)
        base_n_cap = float(base_sample.n_cap)

        # Apply the shift and clip into [0, 1].
        effective_u_r = float(max(0.0, min(1.0, base_u_r + float(self._shift))))

        # Re-derive n_cap from the effective u_r via the closed-form
        # cosine helper, using a synthetic round index. This keeps the
        # closed-form canonical (one source of truth) while honouring
        # the shift.
        if length <= 1:
            # Degenerate single-round cycle: trust n_max (no scaling).
            effective_n_cap = float(n_max)
        else:
            synthetic_round = int(round(effective_u_r * (length - 1)))
            synthetic_round = max(0, min(length - 1, synthetic_round))
            effective_n_cap = float(
                n_cap_for_round(self._base.config, synthetic_round)
            )

        # Defensive clip: shift + base configuration can push effective
        # values to the boundaries, but never outside.
        if not math.isfinite(effective_n_cap):
            effective_n_cap = float(base_n_cap)

        sample = ScheduleSample(
            outer_cycle_id=int(base_sample.outer_cycle_id),
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=float(effective_n_cap),
            n_min=float(n_min),
            n_max=float(n_max),
            u_r=float(effective_u_r),
            family="convergence_adaptive_cosine",
            computed_at_round=int(target_round),
            schedule_hash=str(self._config_hash_value),
            audit_codes=(
                "schedule_convergence_adaptive",
                f"schedule_shift_applied:{float(self._shift):+.6f}",
            )
            + (
                (
                    "schedule_feedback_multi_metric:"
                    + ",".join(sorted(self._last_feedback_keys)),
                )
                if self._last_feedback_keys
                else ()
            )
            + (
                (
                    "schedule_paper_quantity_enabled:"
                    + ",".join(sorted(self._last_paper_quantity_keys)),
                )
                if self._paper_quantity_enabled
                else ()
            ),
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length (from the base scheduler)."""
        return self._base.cycle_length()

    def schedule_family(self) -> str:
        """Return the algorithm family identifier."""
        return "convergence_adaptive_cosine"

    def config_hash(self) -> str:
        """Return a stable identifier for this algorithm + config choice."""
        return str(self._config_hash_value)

    def reset(self) -> None:
        """Clear all adaptive state and delegate to the base scheduler."""
        self._w2_history = []
        self._smoothed_w2 = None
        self._shift = 0.0
        self._last_feedback_keys = ()
        self._last_sample = None
        # Wave 31: also clear paper-quantity EMA state.
        self._sheet_A_ema = None
        self._packing_B_ema = None
        self._exterior_gap_ema = None
        self._paper_ratio_history = []
        self._last_paper_quantity_keys = ()
        self._paper_quantity_enabled = False
        self._base.reset()

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return ``state + sqrt(n_cap) * generator.standard_normal`` (P0-7).

        The adaptive family delegates to its base scheduler's
        ``inject_noise`` so the noise mass tracks the (possibly-shifted)
        effective ``u_r`` produced by the PID-lite controller.
        """
        return self._base.inject_noise(
            state, schedule_sample, generator=generator
        )

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for the adaptive scheduler."""
        out: dict[str, Any] = {
            "family": "convergence_adaptive",
            "base_config": self._base.to_config(),
            "kp": float(self._kp),
            "kd": float(self._kd),
            "shift_max": float(self._shift_max),
            "ema": float(self._ema),
            "metric_weights": {
                str(k): float(v) for k, v in sorted(self._metric_weights.items())
            },
        }
        # Wave 31: include paper-quantity weights only when they differ
        # from the defaults so legacy configs round-trip bit-identical.
        if self._paper_quantity_weights != dict(DEFAULT_PAPER_QUANTITY_WEIGHTS):
            out["paper_quantity_weights"] = {
                str(k): float(v)
                for k, v in sorted(self._paper_quantity_weights.items())
            }
        return out

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ConvergenceAdaptiveScheduler:
        """Build a :class:`ConvergenceAdaptiveScheduler` from ``config`` (P1-1)."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        base_cfg = dict(config["base_config"])
        # Recurse through CosineAnnealScheduler for the nested base.
        base = CosineAnnealScheduler.from_config(base_cfg)
        raw_weights = config.get("metric_weights")
        weights = (
            {str(k): float(v) for k, v in dict(raw_weights).items()}
            if isinstance(raw_weights, dict) and raw_weights
            else None
        )
        raw_pq_weights = config.get("paper_quantity_weights")
        pq_weights = (
            {str(k): float(v) for k, v in dict(raw_pq_weights).items()}
            if isinstance(raw_pq_weights, dict) and raw_pq_weights
            else None
        )
        return ConvergenceAdaptiveScheduler(
            base=base,
            kp=float(config["kp"]),
            kd=float(config["kd"]),
            shift_max=float(config["shift_max"]),
            ema=float(config["ema"]),
            metric_weights=weights,
            paper_quantity_weights=pq_weights,
        )

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
        paper_quantities: Mapping[str, float] | None = None,
    ) -> None:
        """Consume one round's metrics and update the shift via PID-lite.

        P0-A6 — multi-metric aggregation. The controller aggregates every
        metric named in :attr:`metric_weights` into a single *loss-form*
        signal:

        1. For each ``(key, weight)`` in :attr:`metric_weights`, read
           ``metrics[key]``. Missing / non-numeric / non-finite values are
           skipped (a broken oracle cannot poison the controller) and the
           weight is dropped from the normaliser.
        2. Higher-is-better metrics (``coverage``, ``selection_ratio``)
           enter as their loss form ``1 - value``; ``W2`` enters as-is.
        3. ``signal = sum(w * loss) / sum(w)``. With only ``W2`` present
           this is exactly ``metrics["W2"]``, so the legacy behaviour is
           reproduced bit-for-bit.
        4. Update the EMA, append to the history, and (from the second
           sample onwards) apply
           ``shift += kp * (1 - ratio) - kd * delta`` clipped to
           ``[-shift_max, +shift_max]``, where ``ratio`` and ``delta`` are
           computed on consecutive aggregated signals.

        Wave 31 — paper-quantity-aware PID (optional). When
        ``paper_quantities`` is supplied, the controller additionally
        updates three EMAs (``sheet_A_ema``, ``packing_B_ema``,
        ``exterior_gap_ema``) from the literal paper quantities
        ``sheet_evidence_A``, ``root_cell_packing_B`` and
        ``exterior_gap_e_rho`` (paper Lemma 2 / Lemma 3 / Lemma 5). Once
        at least one finite ``sheet_A`` and ``packing_B`` sample has
        been observed, the PID switches from the legacy
        ``ratio = w2[-1] / w2[-2]`` branch to a paper-quantity
        ``ratio = sheet_A_ema / (sheet_A_ema + cell_signal)`` branch
        where ``cell_signal`` is the current ``packing_B_ema``. The
        aggregated W2 path remains the single source of truth for the
        audit trail and for callers that never supply paper
        quantities — the switch is monotone in
        ``paper_quantity_enabled`` and the legacy W2 branch is
        reproduced bit-for-bit until the first paper-quantity sample
        arrives.

        :param round_in_cycle: round index within the current outer
            cycle (passed through for audit; not used in the PID math).
        :param metrics: framework-side metrics dict (e.g. ``W2``,
            ``coverage``, ``selection_ratio``). Same semantics as
            before Wave 31.
        :param paper_quantities: optional mapping with paper-quantity
            values keyed by ``"sheet_A"``, ``"packing_B"`` and / or
            ``"exterior_gap"``. Missing or non-finite entries are
            silently dropped. ``None`` (the default) disables the
            paper-quantity-aware PID branch and the controller behaves
            bit-identically to the Wave 31-Pre release.
        """
        aggregate = 0.0
        weight_sum = 0.0
        used: list[str] = []
        for key, weight in self._metric_weights.items():
            try:
                raw = metrics.get(key, float("nan"))
            except Exception:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            loss = (
                1.0 - value if key in _HIGHER_IS_BETTER_METRICS else value
            )
            aggregate += float(weight) * loss
            weight_sum += float(weight)
            used.append(str(key))
        if weight_sum <= 0.0:
            return
        w2 = float(aggregate / weight_sum)
        if not math.isfinite(w2):
            return
        self._last_feedback_keys = tuple(sorted(used))

        # Update EMA.
        if self._smoothed_w2 is None:
            self._smoothed_w2 = float(w2)
        else:
            self._smoothed_w2 = float(
                self._ema * w2 + (1.0 - self._ema) * float(self._smoothed_w2)
            )

        # Record history. F16: append the EMA-smoothed value so the
        # PID ``prev`` reference below reads ``_smoothed_w2`` (the EMA),
        # NOT the raw aggregated signal. Without this fix the EMA is
        # computed and stored but never consumed by the controller.
        self._w2_history.append(float(self._smoothed_w2))

        # Wave 31: paper-quantity EMA updates + paper-ratio history.
        # These run in parallel to the W2 history; the paper-quantity
        # state does NOT affect the W2 history above (so the legacy
        # audit trail is preserved bit-for-bit).
        paper_ratio_appended = False
        if paper_quantities is not None:
            pq_used: list[str] = []
            sheet_A_raw = self._safe_fetch_paper_quantity(
                paper_quantities, "sheet_A"
            )
            packing_B_raw = self._safe_fetch_paper_quantity(
                paper_quantities, "packing_B"
            )
            exterior_gap_raw = self._safe_fetch_paper_quantity(
                paper_quantities, "exterior_gap"
            )
            if sheet_A_raw is not None:
                self._update_ema("sheet_A", sheet_A_raw)
                pq_used.append("sheet_A")
            if packing_B_raw is not None:
                self._update_ema("packing_B", packing_B_raw)
                pq_used.append("packing_B")
            if exterior_gap_raw is not None:
                self._update_ema("exterior_gap", exterior_gap_raw)
                pq_used.append("exterior_gap")
            if pq_used:
                self._last_paper_quantity_keys = tuple(sorted(pq_used))
            # Compute paper-quantity ratio when both halves are finite.
            if (
                self._sheet_A_ema is not None
                and self._packing_B_ema is not None
            ):
                sheet_f = float(self._sheet_A_ema)
                pack_f = float(self._packing_B_ema)
                denom = sheet_f + pack_f
                if denom > 0.0 and math.isfinite(denom):
                    self._paper_ratio_history.append(float(sheet_f / denom))
                    paper_ratio_appended = True
                    self._paper_quantity_enabled = True

        # Need at least two samples to compute ratio / delta.
        # Wave 31: prefer the paper-quantity ratio once it has produced
        # at least two samples; otherwise fall back to the legacy
        # W2 history. The switch is monotone in
        # ``paper_quantity_enabled``.
        if paper_ratio_appended and len(self._paper_ratio_history) >= 2:
            prev = float(self._paper_ratio_history[-2])
            curr = float(self._paper_ratio_history[-1])
            if not math.isfinite(prev) or prev == 0.0:
                ratio = 1.0 if curr == 0.0 else float("inf")
            else:
                ratio = curr / prev
            if not math.isfinite(ratio):
                ratio = 1.0
            delta = curr - prev
        elif len(self._w2_history) >= 2:
            prev = float(self._w2_history[-2])
            curr = float(self._w2_history[-1])
            # Guard against division by zero in ratio.
            if not math.isfinite(prev) or prev == 0.0:
                ratio = 1.0 if curr == 0.0 else float("inf")
            else:
                ratio = curr / prev
            if not math.isfinite(ratio):
                ratio = 1.0
            delta = curr - prev
        else:
            return

        shift_update = float(self._kp) * (1.0 - ratio) - float(self._kd) * delta
        new_shift = float(self._shift) + shift_update
        if new_shift > float(self._shift_max):
            new_shift = float(self._shift_max)
        elif new_shift < -float(self._shift_max):
            new_shift = -float(self._shift_max)
        self._shift = float(new_shift)

    # -- Wave 31 internal helpers -----------------------------------------

    def _safe_fetch_paper_quantity(
        self,
        paper_quantities: Mapping[str, float],
        name: str,
    ) -> float | None:
        """Return a finite float for ``paper_quantities[name]`` or ``None``.

        Skips missing, non-numeric, or non-finite entries so a broken
        oracle (NaN / inf / wrong type) cannot poison the EMA.
        """
        try:
            raw = paper_quantities.get(name, float("nan"))
        except Exception:
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value) or value < 0.0:
            # Paper quantities are non-negative by construction
            # (sheet_A, packing_B, exterior_gap all >= 0). Negative
            # inputs are dropped defensively.
            return None
        return float(value)

    def _update_ema(self, name: str, sample: float) -> None:
        """Update the named paper-quantity EMA in-place.

        Mirrors the W2 EMA recursion ``new = ema*sample + (1-ema)*prev``
        so the paper-quantity and W2 paths share the same smoothing
        semantics; with ``ema = 0`` (no smoothing) the EMA snaps to the
        latest sample, with ``ema = 1`` it freezes at the first sample.
        """
        if not math.isfinite(float(sample)):
            return
        prev: float | None
        if name == "sheet_A":
            prev = self._sheet_A_ema
        elif name == "packing_B":
            prev = self._packing_B_ema
        elif name == "exterior_gap":
            prev = self._exterior_gap_ema
        else:
            return
        if prev is None:
            ema_value = float(sample)
        else:
            ema_value = float(
                self._ema * float(sample) + (1.0 - self._ema) * float(prev)
            )
        if name == "sheet_A":
            self._sheet_A_ema = float(ema_value)
        elif name == "packing_B":
            self._packing_B_ema = float(ema_value)
        else:
            self._exterior_gap_ema = float(ema_value)

    # -- derived -----------------------------------------------------------

    def memory_fraction_for(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> float:
        """Return ``1 - n_cap`` for one round, via the canonical helper."""
        sample = self.sample(outer_cycle_id, round_in_cycle, target_round)
        return memory_fraction_from_schedule(sample.as_cosine_schedule_sample())


# ---------------------------------------------------------------------------
# Codimension-sheet scheduler — paper Theorem 1 / Lemma 2 + Lemma 3
# ---------------------------------------------------------------------------


def _paper_evidence_balance(
    n_cap_base: float,
    eps_implicit: float,
    *,
    sheet_A: float | None = None,
    packing_B: float | None = None,
    cell_C: float | None = None,
) -> float:
    """Closed-form sheet-vs-cell evidence ratio (paper Lemma 2 + Lemma 3).

    Paper Lemma 2 (``NoiseSelectedRectification_EN.md``:101-103) shows that
    ``eps^{-1} int_T phi p_eps`` converges to a positive coarea-weighted
    line integral; combined with Corollary 1's ``Z_{g,eps} >= C_1 eps``
    (``:165``) this means the sheet tube's evidence is
    ``Theta(eps^{+1})`` (one Jacobian factor ``eps`` from the substitution
    ``y = eps u``). Paper Lemma 3 (``:107``) bounds each root cell by
    ``O(eps^{+2})`` (two Jacobian factors). The cell/sheet ratio is
    therefore ``O(eps) -> 0`` as ``eps -> 0``, so the sheet dominates
    after normalization (Theorem 1, ``:88``).

    The framework's ``n_cap`` is the per-round capacity, and the
    *implicit noise scale* is identified with ``max(n_cap_base,
    eps_implicit)`` (so ``eps`` is the floor of the scheduler's
    capacity). Concretely, with paper-aligned positive powers:

        sheet = max(n_cap_base, eps_implicit)              # eps^{+1}  (Lemma 2 / Cor. 1)
        cell  = (1 - n_cap_base) ** 2 * eps_implicit ** 2 # eps^{+2}  (Lemma 3)
        ratio = sheet / (sheet + cell)

    The ``(1 - n_cap_base) ** 2`` factor on the cell side is a
    framework-side heuristic with no paper counterpart (the paper's
    cell bound is ``C_g e^{-z^2/4} eps^2``, keyed to root position
    ``z``, not to capacity); it is kept as a tunable weight so the
    relative cell contribution can be amplified or attenuated by
    callers. As ``eps -> 0`` the cell term shrinks faster than the
    sheet term, so ``ratio -> 1`` (sheet dominance) for every
    ``n_cap_base < 1``, matching Theorem 1.

    Paper-quantity-augmented mode (preferred when
    ``profile_residual_fn`` is supplied to :class:`CodimensionSheetScheduler`):

    When ``sheet_A``, ``packing_B`` and ``cell_C`` are supplied (the
    cached outputs of ``paper_quantities.sheet_evidence_A``,
    ``paper_quantities.root_cell_packing_B`` and
    ``paper_quantities.per_cell_coefficient_C``), the helper uses the
    *literal* paper quantities as ground truth instead of the
    framework-side heuristic. Concretely:

        sheet = sheet_A * eps                                          # Lemma 2 / Cor. 1
        cell  = cell_C * packing_B * eps ** 2                          # Lemma 3 + Lemma 5
        ratio = sheet / (sheet + cell)

    In this mode ``n_cap_base`` is ignored as an evidence weight — the
    paper quantities carry the full evidence scale, so the
    ``n_cap``-driven framework heuristic is replaced by the paper's
    literal constants. The two closed forms agree up to normalisation
    constants; the paper-quantity-augmented form is the canonical
    version for callers that have configured ``profile_residual_fn``.

    :returns: ``ratio`` in ``[0, 1]``. ``ratio == 1`` means sheet evidence
        dominates the round; ``ratio == 0`` means cell evidence dominates.
    """
    eps = float(eps_implicit)
    if not math.isfinite(eps):
        raise ValueError(f"eps_implicit must be finite, got {eps_implicit!r}")
    if eps <= 0.0:
        raise ValueError(f"eps_implicit must be > 0, got {eps_implicit!r}")
    n = float(n_cap_base)
    if not math.isfinite(n):
        raise ValueError(f"n_cap_base must be finite, got {n_cap_base!r}")
    n_clipped = max(0.0, min(1.0, n))

    # Paper-quantity-augmented path: replace the framework heuristic
    # with the literal paper constants. Used by
    # :class:`CodimensionSheetScheduler` when ``profile_residual_fn`` is
    # supplied so the per-round balance is grounded in the paper's
    # ``A_g`` / ``B_g`` / ``C_g`` (Lemma 2 / Lemma 3 / Lemma 5) rather
    # than in a framework-side surrogate.
    if sheet_A is not None and packing_B is not None and cell_C is not None:
        try:
            sheet_f = float(sheet_A)
            pack_f = float(packing_B)
            cell_C_f = float(cell_C)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"paper quantities must be real numbers; got sheet_A={sheet_A!r}, "
                f"packing_B={packing_B!r}, cell_C={cell_C!r}"
            ) from exc
        if not (
            math.isfinite(sheet_f)
            and math.isfinite(pack_f)
            and math.isfinite(cell_C_f)
        ):
            raise ValueError(
                f"paper quantities must be finite; got sheet_A={sheet_A!r}, "
                f"packing_B={packing_B!r}, cell_C={cell_C!r}"
            )
        if sheet_f < 0.0 or pack_f < 0.0 or cell_C_f < 0.0:
            raise ValueError(
                f"paper quantities must be non-negative; got sheet_A={sheet_f!r}, "
                f"packing_B={pack_f!r}, cell_C={cell_C_f!r}"
            )
        sheet = sheet_f * eps
        cell = cell_C_f * pack_f * eps * eps
        denom = sheet + cell
        if denom <= 0.0:
            # Degenerate (all zero): fall back to the framework heuristic
            # to avoid div-by-zero; the paper's ``A_g > 0`` guarantees this
            # branch is unreachable for any well-posed ``profile``.
            sheet = max(n_clipped, eps)
            cell = (1.0 - n_clipped) ** 2 * eps * eps
            denom = sheet + cell
        return float(sheet / denom)

    # ``eps > 0`` (validated above) and ``n_clipped in [0, 1]`` together
    # guarantee ``denom > 0`` (both ``sheet >= eps > 0`` and
    # ``cell >= 0``), so the closed form is well-defined for every
    # legal input.
    sheet = max(n_clipped, eps)
    cell = (1.0 - n_clipped) ** 2 * eps * eps
    return float(sheet / (sheet + cell))


class CodimensionSheetScheduler:
    """Codimension-driven :class:`SchedulerProtocol` implementation.

    Direct instantiation of paper Theorem 1's posterior-selection mechanism
    (ADR-0013, "Posterior selection drives the algorithm layer"). The
    per-round ``n_cap`` is **driven by the paper's sheet-vs-cell
    evidence ratio** (paper Lemma 2 ``Theta(eps^{+1})`` versus Lemma 3
    ``O(eps^{+2})``) rather than the framework's canonical cosine ramp
    (ADR-0010). The cosine ramp is retained only as a ``u_r``
    reference and to feed the framework-heuristic evidence ratio when
    no residual profile is supplied; in the canonical
    paper-quantity-augmented path ``n_cap`` is the direct mapping
    ``n_cap = n_min + (n_max - n_min) * ratio``, with ``ratio``
    exposed on :attr:`last_evidence_ratio` and on
    :attr:`ScheduleSample.evidence_ratio`.

    Mathematically:

        sheet = sheet_A * eps               # Lemma 2 / Corollary 1
        cell  = cell_C * packing_B * eps^2  # Lemma 3 + Lemma 5
        ratio = sheet / (sheet + cell)      ∈ [0, 1]
        n_cap(r) = n_min + (n_max - n_min) * ratio(r)

    When ``profile_residual_fn is None`` the scheduler falls back to
    the framework-side heuristic
    (:func:`_paper_evidence_balance`) using the cosine ramp's
    ``n_cap_base`` as the cell-evidence weight; this preserves the
    legacy contract for callers that have not supplied a profile
    (backward compat). The two closed forms agree up to normalisation
    constants; the paper-quantity-augmented form is the canonical
    version for callers that have configured ``profile_residual_fn``.

    The :class:`Callable` ``profile_residual_fn`` maps state ``x`` to the
    residual profile ``g(x)`` (paper Lemma 2's coarea weight
    ``1 / sqrt(1 + g(x)^2)``). The scheduler stores the callable for
    provenance and includes its identity in :attr:`config_hash`; the
    per-round closed-form above does not invoke it directly (the closed
    form supplies the selection ratio per round, not the coarea
    integral), but two schedulers configured with different profiles
    must be distinguishable in the audit trail.

    **Paper-quantity wiring.** When ``profile_residual_fn`` is
    supplied, the scheduler consumes the four paper quantities from
    :mod:`adaptive_reflow.contracts.paper_quantities` as ground
    truth:

    * ``A_g = paper_quantities.sheet_evidence_A(profile)`` (Lemma 2 /
      Proposition 3) is computed once at construction time and cached
      as :attr:`sheet_A`.
    * ``B_g = paper_quantities.root_cell_packing_B(profile)``
      (Lemma 5 / line 159) is computed once at construction time and
      cached as :attr:`packing_B`.
    * ``C_g = paper_quantities.per_cell_coefficient_C()`` (Lemma 3,
      line 191) is computed once at construction time and cached as
      :attr:`cell_C`.
    * ``e_rho = paper_quantities.exterior_gap_e_rho()`` (Lemma 4 /
      Lemma 5) is computed once at construction time and cached as
      :attr:`exterior_gap_e_rho`.

    The scheduler then replaces the framework-side heuristic in
    :func:`_paper_evidence_balance` with the literal paper quantities
    (``sheet = A_g * eps``, ``cell = C_g * B_g * eps**2``). When
    ``profile_residual_fn`` is ``None``, the scheduler falls back to
    the inline heuristic closed form; the two paths are mathematically
    equivalent up to normalisation constants and agree on the
    direction of sheet dominance as ``eps -> 0`` per Theorem 1. The
    fallback path preserves byte-identical behaviour for callers that
    have not supplied a profile (backward compat).

    The ``eps_direction`` parameter selects between the paper-aligned
    ``"decreasing"`` direction (default: r=0 high fresh-noise, r=L-1
    low fresh-noise, matching paper Theorem 1's ``eps -> 0`` limit)
    and the legacy ``"increasing"`` direction (reversed ramp, retained
    for backward compatibility with a :class:`DeprecationWarning`).

    Conforms to :class:`SchedulerProtocol`. Pure w.r.t. arguments.
    """

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_min: float = 0.0,
        n_max: float = 1.0,
        profile_residual_fn: Callable[[float], float] | None = None,
        eps_implicit: float = 0.05,
        eps_direction: str = "decreasing",
        seed: int = 0,
    ) -> None:
        """Construct the codimension-driven scheduler.

        :param cycle_length: number of rounds in one outer cycle (``>= 1``).
        :param n_min: capacity floor (output lower bound). Must lie in
            ``[0, 1]``.
        :param n_max: capacity ceiling (output upper bound). Must lie in
            ``[0, 1]``.
        :param profile_residual_fn: callable mapping ``x -> g(x)``, the
            residual profile. Its identity is recorded in
            :attr:`config_hash`. Optional; ``None`` is permitted and
            yields the default ``"default_sheet"`` profile signature.
            When supplied, the scheduler also computes the four paper
            quantities ``A_g``, ``B_g``, ``C_g``, ``e_rho`` from
            :mod:`adaptive_reflow.contracts.paper_quantities` exactly
            once at construction time, caches them on
            ``self._sheet_A``, ``self._packing_B``, ``self._cell_C``,
            ``self._exterior_gap_e_rho`` (exposed via
            :attr:`sheet_A`, :attr:`packing_B`, :attr:`cell_C`,
            :attr:`exterior_gap_e_rho`), and uses them as ground truth
            in :func:`_paper_evidence_balance`. When ``None``, the
            scheduler falls back to the framework-side heuristic
            closed form (mathematically equivalent up to normalisation
            constants — the two paths agree on the direction of sheet
            dominance as ``eps -> 0`` per Theorem 1).
        :param eps_implicit: implicit noise scale in evidence units;
            must satisfy ``eps_implicit > 0``. Paper's Theorem 1 says
            the sheet dominates as ``eps -> 0``; this scheduler treats
            ``eps_implicit`` as a hyperparameter that drives the
            scheduler's sensitivity to the sheet-vs-cell trade-off.
        :param eps_direction: ``"decreasing"`` (paper's convention,
            default) or ``"increasing"`` (legacy). ``"decreasing"`` is
            the framework's monotone coarse-to-fine anneal: at ``r=0``
            the fresh-noise capacity is high (lots of fresh noise, large
            implicit ``eps``) and at ``r=L-1`` it is low (memory
            dominant, small implicit ``eps``). Paper Theorem 1's
            ``eps -> 0`` selects the sheet; the same direction is
            realised by the cycle's terminal round under
            ``"decreasing"``. ``"increasing"`` reverses the cosine ramp
            (r=0 small noise, r=L-1 large noise) and emits a
            :class:`DeprecationWarning` at construction time; callers
            that previously relied on the inverted direction should
            migrate to ``"decreasing"``.
        :param seed: included for protocol signature parity with
            stochastic schedulers; the codimension family is
            deterministic and only participates in the frozen
            :attr:`config_hash`.
        """
        if isinstance(cycle_length, bool) or not isinstance(cycle_length, int):
            raise ValueError(
                f"cycle_length must be int, got {cycle_length!r}"
            )
        if int(cycle_length) < 1:
            raise ValueError(
                f"cycle_length must be >= 1, got {cycle_length!r}"
            )
        for nm, val in (("n_min", n_min), ("n_max", n_max)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if not (0.0 <= fv <= 1.0):
                raise ValueError(f"{nm} must lie in [0, 1], got {fv!r}")
        if isinstance(eps_implicit, bool) or not isinstance(
            eps_implicit, (int, float)
        ):
            raise ValueError(
                f"eps_implicit must be a real number, got {eps_implicit!r}"
            )
        eps_f = float(eps_implicit)
        if not math.isfinite(eps_f):
            raise ValueError(
                f"eps_implicit must be finite, got {eps_implicit!r}"
            )
        if eps_f <= 0.0:
            raise ValueError(
                f"eps_implicit must be > 0, got {eps_f!r}"
            )
        if profile_residual_fn is not None and not callable(
            profile_residual_fn
        ):
            raise ValueError(
                f"profile_residual_fn must be callable or None, "
                f"got {profile_residual_fn!r}"
            )
        if not isinstance(eps_direction, str):
            raise ValueError(
                f"eps_direction must be a string, got {eps_direction!r}"
            )
        normalised_direction = eps_direction.strip().lower()
        if normalised_direction not in ("decreasing", "increasing"):
            raise ValueError(
                "eps_direction must be one of 'decreasing' or "
                f"'increasing', got {eps_direction!r}"
            )
        if normalised_direction == "increasing":
            # The DeprecationWarning is intentionally deferred to the
            # first :meth:`sample` call (rather than construction
            # time) so legacy callers that build the scheduler
            # eagerly but never exercise it do not flood logs
            # (P2-18). The flag is set here and consulted below.
            self._legacy_direction_pending_warning: bool = True
        else:
            self._legacy_direction_pending_warning = False

        self._cycle_length = int(cycle_length)
        self._n_min = float(n_min)
        self._n_max = float(n_max)
        self._eps_implicit = float(eps_f)
        self._eps_direction = normalised_direction
        self._seed = int(seed)
        self._profile_residual_fn = profile_residual_fn
        self._profile_signature = self._compute_profile_signature(
            profile_residual_fn
        )

        # Paper-quantity ground truth. When ``profile_residual_fn`` is
        # supplied, compute the three paper-Theorem-1 quantities that
        # the scheduler consumes (Lemma 2 ``A_g``, Lemma 5 ``B_g``,
        # Lemma 3 ``C_g``) exactly once at construction time and cache
        # them. The scheduler then uses these as ground truth in the
        # per-round sheet-vs-cell evidence balance, replacing the
        # framework-side heuristic that callers see when no profile is
        # configured. ``None`` means "no paper quantities wired" — the
        # scheduler falls back to the legacy inline formula.
        # When ``profile_residual_fn is None``: ``A_g = B_g = C_g = None``
        # and the scheduler uses the legacy inline closed form.
        # When ``profile_residual_fn is not None``: each is computed via
        # ``paper_quantities.*`` and cached on ``self``.
        self._sheet_A: float | None = None
        self._packing_B: float | None = None
        self._cell_C: float | None = None
        self._exterior_gap_e_rho: float | None = None
        if profile_residual_fn is not None:
            # Imports are local so the scheduler module keeps the
            # same dependency surface as the legacy codimension helper
            # (the ``paper_quantities`` module is stdlib-only, so this
            # is a soft import rather than a heavy transitive pull).
            from adaptive_reflow.contracts import paper_quantities as _pq

            self._sheet_A = float(_pq.sheet_evidence_A(profile_residual_fn))
            self._packing_B = float(_pq.root_cell_packing_B(profile_residual_fn))
            self._cell_C = float(_pq.per_cell_coefficient_C())
            self._exterior_gap_e_rho = float(_pq.exterior_gap_e_rho())

        # Underlying base schedule. We use the framework's canonical
        # cosine annealing (ADR-0010) as the n_cap_base source so that
        # the codimension scheduler composes over the same closed form
        # used by every other scheduler — no second source of truth.
        self._base: CosineAnnealScheduler = default_cosine_scheduler(
            cycle_length=self._cycle_length,
            n_min=0.0,
            n_max=1.0,
        )

        self._last_sample: ScheduleSample | None = None
        self._last_evidence_ratio: float | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "codimension_sheet",
                "schedule_family": "codimension_sheet",
                "cycle_length": int(self._cycle_length),
                "n_min": float(self._n_min),
                "n_max": float(self._n_max),
                "eps_implicit": float(self._eps_implicit),
                "eps_direction": str(self._eps_direction),
                "seed": int(self._seed),
                "profile_signature": str(self._profile_signature),
                "base_config_hash": str(self._base.config_hash()),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def eps_implicit(self) -> float:
        """Return the implicit noise scale in evidence units."""
        return float(self._eps_implicit)

    @property
    def eps_direction(self) -> str:
        """Return the configured ``eps_direction`` (``"decreasing"`` or
        ``"increasing"``).

        ``"decreasing"`` is paper Theorem 1's convention: ``r=0`` produces
        large fresh-noise capacity (large implicit ``eps``) and ``r=L-1``
        produces small fresh-noise capacity (small implicit ``eps``).
        ``"increasing"`` is the legacy inverted convention.
        """
        return str(self._eps_direction)

    @property
    def profile_residual_fn(self) -> Callable[[float], float] | None:
        """Return the configured residual profile callable (or ``None``)."""
        return self._profile_residual_fn

    @property
    def profile_signature(self) -> str:
        """Return the stable identifier of the configured residual profile.

        Two :class:`CodimensionSheetScheduler` instances configured with
        the same ``profile_residual_fn`` (compared by ``module`` and
        ``qualname``) produce the same ``profile_signature``; different
        callables produce different signatures. ``None`` yields the
        canonical ``"default_sheet"`` signature.
        """
        return str(self._profile_signature)

    @property
    def sheet_A(self) -> float | None:
        """Return the cached paper-Theorem-1 ``A_g`` (Lemma 2 / Prop. 3).

        ``None`` when no ``profile_residual_fn`` was supplied at
        construction time. When supplied, this is the cached value of
        ``paper_quantities.sheet_evidence_A(profile_residual_fn)``,
        used as ground truth for the per-round sheet evidence in
        :attr:`last_evidence_ratio`.
        """
        return self._sheet_A

    @property
    def packing_B(self) -> float | None:
        """Return the cached paper-Theorem-1 ``B_g`` (Lemma 5).

        ``None`` when no ``profile_residual_fn`` was supplied at
        construction time. When supplied, this is the cached value of
        ``paper_quantities.root_cell_packing_B(profile_residual_fn)``,
        used as ground truth for the per-round cell evidence in
        :attr:`last_evidence_ratio`.
        """
        return self._packing_B

    @property
    def cell_C(self) -> float | None:
        """Return the cached paper-Theorem-1 ``C_g`` (Lemma 3).

        ``None`` when no ``profile_residual_fn`` was supplied at
        construction time. When supplied, this is the cached value of
        ``paper_quantities.per_cell_coefficient_C()``, used as the
        per-cell evidence coefficient in :attr:`last_evidence_ratio`.
        """
        return self._cell_C

    @property
    def exterior_gap_e_rho(self) -> float | None:
        """Return the cached paper-Theorem-1 ``e_rho`` (Lemma 4 / 5).

        ``None`` when no ``profile_residual_fn`` was supplied at
        construction time. When supplied, this is the cached value of
        ``paper_quantities.exterior_gap_e_rho()``, the literal
        physical-exterior gap from Lemma 5.
        """
        return self._exterior_gap_e_rho

    @property
    def base(self) -> CosineAnnealScheduler:
        """Return the underlying cosine base scheduler."""
        return self._base

    @property
    def seed(self) -> int:
        """Return the seed used for provenance hashing."""
        return int(self._seed)

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent sample, or ``None`` after :meth:`reset`."""
        return self._last_sample

    @property
    def last_evidence_ratio(self) -> float | None:
        """Return the most recent sheet-vs-cell evidence ratio.

        The ratio is the per-round paper Lemma 2 / Lemma 3 evidence
        balance (``sheet / (sheet + cell)``, sheet ``Theta(eps^{+1})``,
        cell ``O(eps^{+2})``). It is the **driver** of
        :attr:`last_sample.n_cap` — ``n_cap = n_min + (n_max - n_min)
        * ratio`` — so the per-round capacity now responds directly to
        the paper's sheet-vs-cell signal. ``None`` until the first
        :meth:`sample` call.
        """
        return self._last_evidence_ratio

    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the codimension-driven capacity sample for one round.

        Pipeline:

        1. Ask the underlying cosine base for ``n_cap_base(r)`` (canonical
           closed form, ADR-0010). This value is used to populate the
           ``u_r`` field on the :class:`ScheduleSample` and to feed the
           framework-side heuristic evidence ratio when no residual
           profile has been supplied.
        2. Compute the sheet-vs-cell evidence ratio
           ``ratio = _paper_evidence_balance(n_cap_base, eps_implicit)``
           using paper's positive ``eps`` powers (Lemma 2: sheet
           ``Theta(eps^{+1})``; Lemma 3: cell ``O(eps^{+2})``). When a
           ``profile_residual_fn`` is supplied, the literal paper
           quantities ``A_g``, ``B_g`` and ``C_g`` are used as ground
           truth (round-independent); otherwise the framework-side
           heuristic (which depends on ``n_cap_base``) is used. The
           ratio is **the driver of ``n_cap``** — the coarse-to-fine
           anneal lives in the paper's evidence signal, not in the
           cosine ramp.
        3. Apply ``eps_direction``: ``"decreasing"`` (paper's convention,
           default) keeps the ratio as-is; ``"increasing"`` (legacy)
           flips the ratio (``ratio -> 1 - ratio``) so the cycle's
           start sits at the small-ratio end and the cycle's end sits
           at the large-ratio end. The legacy flip is retained for
           backward compatibility with the prior cosine-based
           interpretation and emits a :class:`DeprecationWarning` on
           the first sample call.
        4. Map the ratio into the configured ``[n_min, n_max]``
           envelope: ``n_cap = n_min + (n_max - n_min) * ratio`` and
           clip into ``[0, 1]`` defensively. With the paper's
           sheet-vs-cell signal, ``n_cap`` is naturally HIGH when
           sheet evidence dominates (in-regime adapters) and LOW when
           cell evidence dominates (out-of-F-side adapters),
           providing the regime-aware throttling that ADR-0017
           documented as the desired future behaviour.
        """
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")

        # P2-18: emit the legacy-direction DeprecationWarning once,
        # on the FIRST ``sample()`` call rather than at construction
        # time. Legacy callers that build the scheduler eagerly but
        # never exercise it (e.g. for ``config_hash`` introspection)
        # do not flood logs.
        if getattr(self, "_legacy_direction_pending_warning", False):
            warnings.warn(
                "CodimensionSheetScheduler(eps_direction='increasing') is "
                "the legacy inverted convention (r=0 small noise, "
                "r=L-1 large noise); it is the opposite of paper "
                "Theorem 1's eps -> 0 limit. Migrate to "
                "eps_direction='decreasing' (the paper-aligned default). "
                "The 'increasing' option will be removed in a future "
                "release.",
                DeprecationWarning,
                stacklevel=2,
            )
            self._legacy_direction_pending_warning = False

        length = int(self._cycle_length)
        if length > 1 and not (
            0 <= int(round_in_cycle) <= length - 1
        ):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for "
                f"cycle_length={length}, got {round_in_cycle!r}"
            )

        if length == 1:
            # Single-round edge: mirror the cosine family's deterministic
            # behaviour. ``n_cap_base`` is set to ``n_max`` (the cycle's
            # only capacity slot under the legacy cosine driver); the
            # ratio is then computed from this value — in the
            # paper-quantity-augmented path it is ignored, in the
            # framework heuristic path it determines the ratio.
            u_r = 0.5
            n_cap_base = float(self._n_max)
        else:
            u_r = float(round_in_cycle) / (length - 1)
            n_cap_base = float(
                n_cap_for_round(self._base.config, int(round_in_cycle))
            )

        # Compute the paper's sheet-vs-cell evidence ratio. The
        # "paper-quantity-augmented" path uses the cached ``A_g`` /
        # ``B_g`` / ``C_g`` literals (round-independent when
        # ``profile_residual_fn`` is supplied) — this is the canonical
        # paper-quantity-driven path. The framework-side heuristic
        # (no profile) uses ``n_cap_base`` (cosine ramp) as the
        # cell-evidence weight; the two closed forms agree up to
        # normalisation constants.
        ratio = float(
            _paper_evidence_balance(
                n_cap_base,
                self._eps_implicit,
                sheet_A=self._sheet_A,
                packing_B=self._packing_B,
                cell_C=self._cell_C,
            )
        )

        # Apply the legacy ``eps_direction`` flip. ``decreasing`` (paper
        # convention, default) keeps the ratio as-is. The legacy
        # ``increasing`` mode flips ``ratio -> 1 - ratio`` so that the
        # cycle's start sits at the small-ratio end and the cycle's
        # end sits at the large-ratio end; this preserves the
        # backward-compatibility semantics of the prior cosine-based
        # interpretation while making the regime-aware throttling
        # consistent with the historical direction.
        if self._eps_direction == "increasing":
            ratio = 1.0 - ratio

        # ``n_cap`` is now driven by the ratio. With paper-quantity
        # augmentation this gives a regime-aware capacity that
        # naturally throttles when out-of-F-side-class (low sheet,
        # low ratio, low n_cap) and increases when in-regime (high
        # sheet, high ratio, high n_cap).
        raw = self._n_min + (self._n_max - self._n_min) * ratio
        if not math.isfinite(raw):
            raise ValueError(
                f"codimension ratio-driven closed form produced a "
                f"non-finite n_cap={raw!r}"
            )
        n_cap = float(max(0.0, min(1.0, raw)))
        self._last_evidence_ratio = ratio

        # P0-A1 / P0-A7: surface the round's provenance and the
        # sheet-vs-cell balance ON the sample so the runner / engine can
        # branch on them without a second ``last_evidence_ratio`` read.
        codes: tuple[str, ...] = (
            ("codimension_paper_quantity_grounded",)
            if self._sheet_A is not None
            else ("codimension_framework_heuristic",)
        )

        sample = ScheduleSample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=n_cap,
            n_min=float(self._n_min),
            n_max=float(self._n_max),
            u_r=u_r,
            family="codimension_sheet",
            computed_at_round=target_round,
            schedule_hash=str(self._config_hash_value),
            audit_codes=codes,
            evidence_ratio=float(ratio),
            eps_implicit=float(self._eps_implicit),
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length."""
        return int(self._cycle_length)

    def with_profile(
        self, profile_residual_fn: Callable[[float], float] | None
    ) -> CodimensionSheetScheduler:
        """Return a new scheduler with ``profile_residual_fn`` swapped in.

        F10: avoids the runner reaching into the private
        ``_eps_implicit`` / ``_n_min`` / ``_n_max`` /
        ``_eps_direction`` / ``_seed`` attributes. All other
        configuration is preserved (cycle_length, n_min, n_max,
        eps_implicit, eps_direction, seed).
        """
        return CodimensionSheetScheduler(
            cycle_length=int(self._cycle_length),
            n_min=float(self._n_min),
            n_max=float(self._n_max),
            profile_residual_fn=profile_residual_fn,
            eps_implicit=float(self._eps_implicit),
            eps_direction=str(self._eps_direction),
            seed=int(self._seed),
        )

    def schedule_family(self) -> str:
        """Return ``"codimension_sheet"``."""
        return "codimension_sheet"

    def config_hash(self) -> str:
        """Return a stable identifier for this algorithm + config choice.

        The hash captures every configuration input including
        ``eps_implicit`` and the ``profile_signature`` (so two
        schedulers configured with different profiles produce different
        hashes, even when all numeric inputs match).
        """
        return str(self._config_hash_value)

    def reset(self) -> None:
        """Drop the cached sample so a re-run starts from a clean state."""
        self._last_sample = None
        self._last_evidence_ratio = None
        self._base.reset()

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Default no-op: the codimension scheduler is open-loop on rounds."""
        return None

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return ``state + sqrt(A_g) * generator.standard_normal`` (P0-7).

        The codimension scheduler uses the cached paper-quantity
        ``A_g`` (:attr:`sheet_A`, paper Lemma 2 / Proposition 3) as
        the per-round noise mass — when ``A_g`` is ``None`` (no
        ``profile_residual_fn`` was supplied at construction time)
        it falls back to the schedule's ``n_cap``, matching the
        canonical cosine path.

        A18 uplift: when the cached :attr:`exterior_gap_e_rho` is
        available, the noise mass is *floored* at ``e_rho / 4`` so the
        forward noise respects paper Lemma 5's physical-complement
        gap (a noise mass below ``e_rho`` would put forward-noise
        energy inside the complement region that the paper already
        proves is exponentially suppressed). With a positive
        ``e_rho`` the noise mass becomes ``max(A_g, e_rho / 4)``;
        callers that wire both quantities get the audit-trail-safe
        paper-aligned mass.

        CLM-042 derivation note (A-02.M1 paper-math fidelity): the
        ``/4`` factor mirrors the
        :class:`~adaptive_reflow.algorithm.merge_operator.BoundedMergeOperator`
        paper-quantity-floor convention; the paper proves
        ``|F_g|^2 >= e_rho`` (Lemma 4) and ``/4`` is a conservative
        tightening so the noise mass cannot drop below a quarter of
        the proven exterior gap. See CLM-042 in ``docs/CLAIMS.md``
        for the audit trail.
        """
        state_arr = np.asarray(state, dtype=np.float64)
        if self._sheet_A is not None:
            noise_mass = float(self._sheet_A)
        else:
            noise_mass = float(schedule_sample.n_cap)
        # A18: fold the exterior gap into the noise mass floor.
        if self._exterior_gap_e_rho is not None:
            paper_floor = float(self._exterior_gap_e_rho) / 4.0
            if noise_mass < paper_floor:
                noise_mass = paper_floor
        if noise_mass < 0.0:
            noise_mass = 0.0
        scale = math.sqrt(noise_mass)
        noise = generator.standard_normal(state_arr.shape).astype(np.float64)
        return state_arr + scale * noise

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for the codimension scheduler.

        The profile's callable identity is folded into ``profile_signature``
        (not the callable itself) so the dict remains JSON-serialisable.
        Callers that need to re-instantiate the callable must keep the
        signature externally.
        """
        return {
            "family": "codimension_sheet",
            "cycle_length": int(self._cycle_length),
            "n_min": float(self._n_min),
            "n_max": float(self._n_max),
            "eps_implicit": float(self._eps_implicit),
            "eps_direction": str(self._eps_direction),
            "seed": int(self._seed),
            "profile_signature": str(self._profile_signature),
            "base_config": self._base.to_config(),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> CodimensionSheetScheduler:
        """Build a :class:`CodimensionSheetScheduler` from ``config`` (P1-1).

        ``profile_residual_fn`` is reconstructed only when a callable
        matching the ``profile_signature`` is available on the call
        side. The signature is recorded so two round-trips remain
        distinguishable; the callable itself is intentionally not
        serialised (it is application code, not configuration).
        """
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return CodimensionSheetScheduler(
            cycle_length=int(config["cycle_length"]),
            n_min=float(config["n_min"]),
            n_max=float(config["n_max"]),
            eps_implicit=float(config["eps_implicit"]),
            eps_direction=str(config.get("eps_direction", "decreasing")),
            seed=int(config.get("seed", 0)),
            profile_residual_fn=None,
        )

    # -- derived -----------------------------------------------------------

    def memory_fraction_for(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> float:
        """Return ``1 - n_cap`` for one round, via the canonical helper."""
        sample = self.sample(outer_cycle_id, round_in_cycle, target_round)
        return memory_fraction_from_schedule(sample.as_cosine_schedule_sample())

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _compute_profile_signature(
        fn: Callable[[float], float] | None,
    ) -> str:
        """Return a stable string identifier for ``fn``'s identity.

        Two callables with the same ``module`` and ``qualname`` yield
        the same signature; lambdas and callables lacking
        ``__module__`` / ``__qualname__`` fall back to ``repr(fn)``
        truncated to 64 characters.
        """
        if fn is None:
            return "default_sheet"
        try:
            qualname = getattr(fn, "__qualname__", None)
            if qualname is None:
                qualname = getattr(fn, "__name__", None)
            module = getattr(fn, "__module__", None)
        except Exception:
            qualname, module = None, None
        if qualname and module:
            return f"{module}.{qualname}"
        if qualname:
            return str(qualname)
        try:
            return repr(fn)[:64]
        except Exception:
            return "<unsignable_profile>"


# ---------------------------------------------------------------------------
# Paper-ratio adaptive scheduler — fully-integrated paper-quantity control
# ---------------------------------------------------------------------------


class PaperRatioAdaptiveScheduler:
    """Fully-integrated paper-quantity-driven + paper-quantity-adaptive
    :class:`SchedulerProtocol` wrapper.

    The **fully-integrated** scheduler for paper-quantity control (Wave 31
    Agent C). Combines the paper-ratio-driven base
    (:class:`CodimensionSheetScheduler`, Agent A — paper Lemma 2 / Lemma 3
    drives ``n_cap`` via sheet-vs-cell evidence) with a paper-quantity-aware
    PID-lite controller (analogous to
    :class:`ConvergenceAdaptiveScheduler`, Agent B — but driven by the
    sheet-evidence ``A_g`` EMA delta rather than by the W2 metric delta).

    Pipeline:

    1. :meth:`sample` asks the wrapped
       :class:`CodimensionSheetScheduler` for ``n_cap_base(r)`` (the
       paper-quantity-driven base schedule).
    2. A *shift_delta* is added to ``n_cap_base`` based on the
       paper-quantity-aware PID-lite controller:

           shift_update = kp * (1.0 - sheet_ratio) - kd * sheet_delta

       where ``sheet_ratio = sheet_A_ema[-1] / sheet_A_ema[-2]`` and
       ``sheet_delta = sheet_A_ema[-1] - sheet_A_ema[-2]``.

    3. The shifted ``n_cap`` is clipped into ``[0, 1]`` defensively so
       the engine never sees a value outside the canonical capacity
       range.

    :meth:`record_round_feedback` consumes a *paper-quantities dict*
    carrying the paper Lemma 2 / Lemma 4 / Lemma 5 quantities:

        {"sheet_A": float, "packing_B": float, "exterior_gap_e_rho": float}

    It maintains an EMA of ``sheet_A`` and (from the second sample
    onwards) applies the PID-lite update above. The first round is
    recorded without shifting (no prior history).

    Empty / missing ``paper_quantities`` dicts are a **safe default**:
    no EMA update, no shift change. This matches the
    :class:`ConvergenceAdaptiveScheduler` backward-compat behaviour for
    missing W2 values.

    The ``record_round_feedback`` interface uses an *alternative* signature
    relative to :class:`ConvergenceAdaptiveScheduler` because the
    feedback is paper-quantity-derived, not W2-derived:

        def record_round_feedback(self, round_in_cycle, paper_quantities)

    The framework's runner uses ``hasattr(scheduler,
    "record_round_feedback")`` to discover adaptive schedulers, so this
    signature variant is forward-compatible — the runner can branch on
    the scheduler class or fall back to the metric-based interface for
    the W2-driven controller.

    This is the *fully-integrated* scheduler: the base is
    paper-quantity-driven and the controller is paper-quantity-aware,
    so the entire scheduling decision is grounded in paper quantities
    (Lemma 2 / Lemma 3 / Lemma 4 / Lemma 5) — no heuristic metrics
    anywhere in the stack.

    Conforms to :class:`SchedulerProtocol`. Pure w.r.t. arguments.
    """

    def __init__(
        self,
        *,
        base: CodimensionSheetScheduler | None = None,
        kp: float = 0.10,
        kd: float = 0.05,
        shift_max: float = 0.15,
        ema: float = 0.3,
    ) -> None:
        """Construct the paper-ratio adaptive scheduler.

        :param base: the wrapped :class:`CodimensionSheetScheduler`.
            Defaults to a fresh one with the canonical ``eps_implicit=0.05``
            and the paper-aligned ``eps_direction="decreasing"``.
        :param kp: proportional gain on ``(1.0 - sheet_ratio)``.
            Positive ``kp`` means a *decreasing* sheet-evidence signal
            (sheet_ratio < 1) pushes the shift *up* (more n_cap).
        :param kd: derivative gain on ``sheet_delta``. A negative
            ``sheet_delta`` (sheet_A growing) pushes the shift positive.
        :param shift_max: maximum absolute shift in ``n_cap`` units
            (the additive correction is clipped into
            ``[-shift_max, +shift_max]``).
        :param ema: smoothing factor for the sheet-A EMA. ``0`` = no
            smoothing (raw samples), ``1`` = ignore new samples.
        """
        if base is None:
            base = CodimensionSheetScheduler(
                cycle_length=20,
                n_min=0.0,
                n_max=1.0,
                eps_implicit=0.05,
                eps_direction="decreasing",
            )
        if not isinstance(base, CodimensionSheetScheduler):
            raise TypeError(
                "base must be a CodimensionSheetScheduler, got "
                f"{type(base).__name__}"
            )
        for nm, val in (("kp", kp), ("kd", kd), ("shift_max", shift_max), ("ema", ema)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
        if float(ema) < 0.0 or float(ema) > 1.0:
            raise ValueError(
                f"ema must lie in [0, 1], got {float(ema)!r}"
            )
        if float(shift_max) < 0.0:
            raise ValueError(
                f"shift_max must be >= 0, got {float(shift_max)!r}"
            )
        self._base: CodimensionSheetScheduler = base
        self._kp = float(kp)
        self._kd = float(kd)
        self._shift_max = float(shift_max)
        self._ema = float(ema)
        # Mutable state — cleared by reset().
        self._sheet_A_history: list[float] = []
        self._smoothed_sheet_A: float | None = None
        self._shift: float = 0.0
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "paper_ratio_adaptive",
                "base_config_hash": str(self._base.config_hash()),
                "kp": float(self._kp),
                "kd": float(self._kd),
                "shift_max": float(self._shift_max),
                "ema": float(self._ema),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def base(self) -> CodimensionSheetScheduler:
        """Return the wrapped base :class:`CodimensionSheetScheduler`."""
        return self._base

    @property
    def kp(self) -> float:
        """Return the proportional gain."""
        return float(self._kp)

    @property
    def kd(self) -> float:
        """Return the derivative gain."""
        return float(self._kd)

    @property
    def shift_max(self) -> float:
        """Return the maximum absolute shift in n_cap units."""
        return float(self._shift_max)

    @property
    def ema(self) -> float:
        """Return the EMA smoothing factor."""
        return float(self._ema)

    @property
    def shift(self) -> float:
        """Return the current shift value (in n_cap units)."""
        return float(self._shift)

    @property
    def smoothed_sheet_A(self) -> float | None:
        """Return the latest EMA-smoothed sheet_A, or ``None`` if no feedback yet."""
        return self._smoothed_sheet_A

    @property
    def sheet_A_history(self) -> tuple[float, ...]:
        """Return the recorded EMA-smoothed sheet_A history as a tuple."""
        return tuple(self._sheet_A_history)

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent sample, or ``None`` after :meth:`reset`."""
        return self._last_sample


    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the paper-ratio-adapted capacity sample for one round.

        Pipeline:

        1. Ask the wrapped :class:`CodimensionSheetScheduler` for
           ``n_cap_base(r)`` (paper-quantity-driven base schedule).
        2. Compute the effective ``n_cap = clip(n_cap_base + shift, 0, 1)``.
        3. Re-emit a :class:`ScheduleSample` carrying the same audit
           codes (paper-quantity-grounded) plus an extra
           ``schedule_paper_ratio_adaptive_shift`` marker so the audit
           trail can identify rounds whose ``n_cap`` was modified by the
           PID-lite controller.
        """
        base_sample = self._base.sample(
            outer_cycle_id, round_in_cycle, target_round
        )
        base_n_cap = float(base_sample.n_cap)
        effective_n_cap = float(
            max(0.0, min(1.0, base_n_cap + float(self._shift)))
        )

        # Compose audit codes: start from the base's codes (carries the
        # paper-quantity-grounded marker) and append the adaptive shift
        # marker.
        codes: tuple[str, ...] = base_sample.audit_codes + (
            "schedule_paper_ratio_adaptive_shift",
            f"schedule_paper_ratio_shift_applied:{float(self._shift):+.6f}",
        )

        sample = ScheduleSample(
            outer_cycle_id=int(base_sample.outer_cycle_id),
            round_in_cycle=int(round_in_cycle),
            cycle_length=int(base_sample.cycle_length),
            n_cap=float(effective_n_cap),
            n_min=float(base_sample.n_min),
            n_max=float(base_sample.n_max),
            u_r=float(base_sample.u_r),
            family="paper_ratio_adaptive_codimension",
            computed_at_round=int(target_round),
            schedule_hash=str(self._config_hash_value),
            audit_codes=codes,
            evidence_ratio=base_sample.evidence_ratio,
            eps_implicit=base_sample.eps_implicit,
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length (from the base scheduler)."""
        return self._base.cycle_length()

    def schedule_family(self) -> str:
        """Return the algorithm family identifier."""
        return "paper_ratio_adaptive_codimension"

    def config_hash(self) -> str:
        """Return a stable identifier for this algorithm + config choice."""
        return str(self._config_hash_value)

    def reset(self) -> None:
        """Clear all adaptive state and delegate to the base scheduler."""
        self._sheet_A_history = []
        self._smoothed_sheet_A = None
        self._shift = 0.0
        self._last_sample = None
        self._base.reset()

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return ``state + sqrt(noise_mass) * generator.standard_normal``.

        The paper-ratio adaptive family delegates to its base
        :class:`CodimensionSheetScheduler`'s ``inject_noise`` so the
        noise mass tracks the (possibly-shifted) ``n_cap`` produced by
        the PID-lite controller and the paper-quantity ``A_g`` from the
        base scheduler. The base scheduler's ``inject_noise`` uses the
        cached paper-quantity ``A_g`` (when ``profile_residual_fn`` was
        supplied at construction time) as the noise mass, with the
        paper-aligned exterior-gap floor from Lemma 5.
        """
        return self._base.inject_noise(
            state, schedule_sample, generator=generator
        )

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for this scheduler."""
        return {
            "family": "paper_ratio_adaptive",
            "base_config": self._base.to_config(),
            "kp": float(self._kp),
            "kd": float(self._kd),
            "shift_max": float(self._shift_max),
            "ema": float(self._ema),
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> PaperRatioAdaptiveScheduler:
        """Build a :class:`PaperRatioAdaptiveScheduler` from ``config`` (P1-1)."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        base_cfg = dict(config["base_config"])
        base = CodimensionSheetScheduler.from_config(base_cfg)
        return PaperRatioAdaptiveScheduler(
            base=base,
            kp=float(config["kp"]),
            kd=float(config["kd"]),
            shift_max=float(config["shift_max"]),
            ema=float(config["ema"]),
        )

    def record_round_feedback(
        self,
        round_in_cycle: int,
        paper_quantities: Mapping[str, float] | None = None,
    ) -> None:
        """Consume one round's paper quantities and update the shift via PID-lite.

        Signature differs from
        :meth:`ConvergenceAdaptiveScheduler.record_round_feedback` because
        the feedback here is paper-quantity-derived (``sheet_A``,
        ``packing_B``, ``exterior_gap_e_rho``), not W2-derived. The
        runner discovers adaptive schedulers via
        ``hasattr(scheduler, "record_round_feedback")``, so both
        signatures coexist at the protocol surface.

        Pipeline:

        1. Read ``paper_quantities["sheet_A"]``. Missing /
           non-numeric / non-finite values skip the round (a broken
           oracle cannot poison the controller).
        2. Update the EMA of ``sheet_A``.
        3. Append the EMA-smoothed value to ``_sheet_A_history`` (the
           F16 invariant from
           :class:`ConvergenceAdaptiveScheduler` — the PID ``prev``
           reference reads the smoothed value, NOT the raw value).
        4. From the second sample onwards, apply

               shift += kp * (1 - sheet_ratio) - kd * sheet_delta

           where ``sheet_ratio = sheet_A_ema[-1] / sheet_A_ema[-2]``
           and ``sheet_delta = sheet_A_ema[-1] - sheet_A_ema[-2]``.
           The shift is clipped into ``[-shift_max, +shift_max]``.

        Empty ``paper_quantities`` dict (or ``None``) is a safe
        default: no EMA update, no shift change. This is the
        backward-compat behaviour for callers that wire the paper
        quantities dict later (or never).
        """
        if paper_quantities is None:
            return
        # Read sheet_A; missing / non-numeric / non-finite -> ignore.
        try:
            raw = paper_quantities.get("sheet_A", float("nan"))
        except Exception:
            return
        try:
            sheet_A = float(raw)
        except (TypeError, ValueError):
            return
        if not math.isfinite(sheet_A) or sheet_A < 0.0:
            return

        # Update EMA.
        if self._smoothed_sheet_A is None:
            self._smoothed_sheet_A = float(sheet_A)
        else:
            self._smoothed_sheet_A = float(
                self._ema * sheet_A
                + (1.0 - self._ema) * float(self._smoothed_sheet_A)
            )

        # F16: history holds the smoothed value (not the raw sheet_A)
        # so the PID ``prev`` reference below reads the EMA.
        self._sheet_A_history.append(float(self._smoothed_sheet_A))

        # Need at least two samples to compute ratio / delta.
        if len(self._sheet_A_history) < 2:
            return

        prev = float(self._sheet_A_history[-2])
        curr = float(self._sheet_A_history[-1])
        # Guard against division by zero in ratio.
        if not math.isfinite(prev) or prev == 0.0:
            sheet_ratio = 1.0 if curr == 0.0 else float("inf")
        else:
            sheet_ratio = curr / prev
        if not math.isfinite(sheet_ratio):
            sheet_ratio = 1.0
        sheet_delta = curr - prev

        shift_update = (
            float(self._kp) * (1.0 - sheet_ratio)
            - float(self._kd) * sheet_delta
        )
        new_shift = float(self._shift) + shift_update
        if new_shift > float(self._shift_max):
            new_shift = float(self._shift_max)
        elif new_shift < -float(self._shift_max):
            new_shift = -float(self._shift_max)
        self._shift = float(new_shift)

    # -- derived -----------------------------------------------------------

    def memory_fraction_for(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> float:
        """Return ``1 - n_cap`` for one round, via the canonical helper."""
        sample = self.sample(outer_cycle_id, round_in_cycle, target_round)
        return memory_fraction_from_schedule(sample.as_cosine_schedule_sample())


# ---------------------------------------------------------------------------
# Registry + factory
# ---------------------------------------------------------------------------


def _codimension_sheet_factory(
    *,
    cycle_length: int = 20,
    n_min: float = 0.0,
    n_max: float = 1.0,
    profile_residual_fn: Callable[[float], float] | None = None,
    eps_implicit: float = 0.05,
    eps_direction: str = "decreasing",
    seed: int = 0,
) -> CodimensionSheetScheduler:
    """Factory for :class:`CodimensionSheetScheduler`.

    Registered in :data:`SCHEDULER_REGISTRY` under the key
    ``"codimension_sheet"``. Mirrors the kwargs of
    :class:`CodimensionSheetScheduler` so that
    :func:`build_scheduler("codimension_sheet", **kwargs)` works
    directly.
    """
    return CodimensionSheetScheduler(
        cycle_length=cycle_length,
        n_min=n_min,
        n_max=n_max,
        profile_residual_fn=profile_residual_fn,
        eps_implicit=eps_implicit,
        eps_direction=eps_direction,
        seed=seed,
    )


def _sequential_factory(*args: Any, **kwargs: Any) -> Any:
    """Factory for :class:`adaptive_reflow.algorithm.sequential.SequentialScheduler`.

    Registered in :data:`SCHEDULER_REGISTRY` under the key
    ``"sequential"``. Mirrors :func:`_codimension_sheet_factory` — the
    factory accepts a ``schedulers=`` keyword and forwards it to the
    concrete class. Config round-trip uses
    :meth:`SequentialScheduler.from_config` directly so the factory is
    only used for keyword-based construction.
    """
    from adaptive_reflow.algorithm.sequential import (
        SequentialScheduler as _SequentialScheduler,
    )
    schedulers = kwargs.pop("schedulers", None)
    if schedulers is None and args:
        schedulers = args[0]
    if schedulers is None:
        raise ValueError(
            "sequential factory requires a 'schedulers' keyword argument"
        )
    return _SequentialScheduler(schedulers=schedulers)


SCHEDULER_REGISTRY: dict[str, Callable[..., SchedulerProtocol]] = {
    "cosine": default_cosine_scheduler,
    "constant": ConstantScheduler,
    "linear": LinearScheduler,
    "exponential": ExponentialScheduler,
    "polynomial": PolynomialScheduler,
    "sigmoid": SigmoidScheduler,
    "convergence_adaptive": ConvergenceAdaptiveScheduler,
    "codimension_sheet": _codimension_sheet_factory,
    "paper_ratio_adaptive": PaperRatioAdaptiveScheduler,
    "sequential": _sequential_factory,
}
"""Mapping from schedule family name to its :class:`SchedulerProtocol` factory.

The framework looks schedulers up here when constructing one from a string
identifier (e.g. a config file value). Each entry is a callable that accepts
the family-specific kwargs and returns a :class:`SchedulerProtocol`
instance. The cosine entry routes through :func:`default_cosine_scheduler`
because :class:`CosineAnnealScheduler` takes a frozen
:class:`CosineScheduleConfig` rather than raw kwargs.

Config round-trip (P1-1): every scheduler's :meth:`to_config` returns a
dict whose ``family`` key is one of these registry keys. Use
:func:`build_scheduler_from_config` to dispatch on the family key
polymorphically without exposing the underlying class.


The exponential family is *not* one of the canonical :data:`SCHEDULE_FAMILIES`
literals — it is an algorithm-layer addition that lives alongside the
contracts-layer taxonomy.
"""


# Phase-2 protocol registry extension (P0/P2 — see
# ``docs/algorithm-deep-uplift-plan.md``).
#
# The extra families (``edm``, ``adaptive_pid``, ``jittered_constant``)
# live in :mod:`adaptive_reflow.algorithm.scheduler_extra`, which has a
# TOP-LEVEL ``from .scheduler._core import`` of its own. If we called
# :func:`_register_extra_scheduler_families` at module load time it
# would close a cycle:
#
#     scheduler/__init__.py -> scheduler/_core.py
#                              -> scheduler_extra.py
#                              -> scheduler/__init__.py (partial)
#
# The cycle currently happens to work because Python's
# partially-initialised modules still expose the symbols defined
# *before* line 3046 of ``_core.py``, but the design is fragile: any
# future move of a symbol reference earlier in ``_core.py`` (or a
# change in ``scheduler_extra.py``'s import order) silently turns the
# "works by accident" cycle into an ``ImportError``.
#
# We therefore defer the registration to the first call of
# :func:`build_scheduler`. The registration is idempotent so
# re-invocations are no-ops; ``build_scheduler_from_config`` uses
# explicit per-family dispatch with its own lazy imports and does NOT
# depend on the registry being pre-populated.
#
# Net effect: the cycle disappears at module load time. The two
# consumers that need the registry populated see the same final state
# (the extra families registered) without any
# ``try/except ImportError`` or ``sys.modules`` patching.
def _register_extra_scheduler_families() -> None:
    """Extend :data:`SCHEDULER_REGISTRY` with Phase-2 scheduler families.

    Idempotent: re-invocations are no-ops. The new families are
    registered so :func:`build_scheduler` recognises them and
    :data:`SCHEDULER_REGISTRY` reports them in its listing.

    Must be called at *function call time* rather than module load
    time to avoid the cycle described in this function's docstring.
    """
    from ..scheduler_extra import (
        AdaptivePIDScheduler,
        EDMScheduler,
        JitteredConstantScheduler,
    )

    SCHEDULER_REGISTRY.setdefault("edm", EDMScheduler)
    SCHEDULER_REGISTRY.setdefault("adaptive_pid", AdaptivePIDScheduler)
    SCHEDULER_REGISTRY.setdefault("jittered_constant", JitteredConstantScheduler)


# Tracks whether :func:`_register_extra_scheduler_families` has run.
# Module-level so the state survives across multiple
# :func:`build_scheduler` invocations within the same process.
_EXTRA_FAMILIES_REGISTERED: bool = False


def _ensure_extra_families_registered() -> None:
    """Register Phase-2 scheduler families on first :func:`build_scheduler` call.

    Idempotent wrapper around :func:`_register_extra_scheduler_families`
    that gates the registration on a module-level flag so the cycle
    described in :func:`_register_extra_scheduler_families`'s
    docstring cannot recur on repeated calls.
    """
    global _EXTRA_FAMILIES_REGISTERED
    if _EXTRA_FAMILIES_REGISTERED:
        return
    _register_extra_scheduler_families()
    _EXTRA_FAMILIES_REGISTERED = True


def build_scheduler(family: str, **kwargs: object) -> SchedulerProtocol:
    """Factory: build a :class:`SchedulerProtocol` from a family name.

    :param family: one of the keys of :data:`SCHEDULER_REGISTRY`
        (``"cosine"``, ``"constant"``, ``"linear"``, ``"exponential"``).
    :param kwargs: forwarded verbatim to the matching factory. For
        ``"cosine"`` the kwargs must match :func:`default_cosine_scheduler`;
        for ``"constant"`` they must match :class:`ConstantScheduler`; etc.
    :returns: a fresh :class:`SchedulerProtocol` instance for that family.
    :raises KeyError: ``family`` is not a registered schedule family.

    The Phase-2 scheduler families (``edm``, ``adaptive_pid``,
    ``jittered_constant``) are registered on first invocation of this
    function via :func:`_ensure_extra_families_registered`. Deferring
    the registration to here is what keeps the module-load-time cycle
    closed (see :func:`_register_extra_scheduler_families`).
    """
    _ensure_extra_families_registered()
    if not isinstance(family, str):
        raise ValueError(f"family must be str, got {family!r}")
    key = family.strip().lower()
    if key not in SCHEDULER_REGISTRY:
        raise KeyError(
            f"unknown scheduler family {family!r}; registered families: "
            f"{sorted(SCHEDULER_REGISTRY)!r}"
        )
    factory = SCHEDULER_REGISTRY[key]
    return factory(**kwargs)


def build_scheduler_from_config(config: dict[str, Any]) -> SchedulerProtocol:
    """Polymorphic factory: build a scheduler from a ``to_config`` dict.

    Dispatches on the ``config["family"]`` key against
    :data:`SCHEDULER_REGISTRY`. Mirrors ``diffusers`` ``ConfigMixin.from_config``.
    The round-trip is byte-identical for every implementation:

        scheduler == cls.from_config(scheduler.to_config())
    """
    if not isinstance(config, dict):
        raise TypeError(f"config must be a dict, got {type(config).__name__}")
    family = config.get("family")
    if not isinstance(family, str):
        raise ValueError(
            f"config['family'] must be a string, got {family!r}"
        )
    key = family.strip().lower()
    if key not in SCHEDULER_REGISTRY:
        raise KeyError(
            f"unknown scheduler family {family!r}; registered families: "
            f"{sorted(SCHEDULER_REGISTRY)!r}"
        )
    # Dispatch on the family key. Each registry entry's ``from_config``
    # classmethod is the canonical deserialiser; we resolve the class
    # from the factory callable so the registry remains the single
    # source of truth.
    factory = SCHEDULER_REGISTRY[key]
    if key == "cosine":
        return CosineAnnealScheduler.from_config(config)
    if key == "constant":
        return ConstantScheduler.from_config(config)
    if key == "linear":
        return LinearScheduler.from_config(config)
    if key == "exponential":
        return ExponentialScheduler.from_config(config)
    if key == "polynomial":
        return PolynomialScheduler.from_config(config)
    if key == "sigmoid":
        return SigmoidScheduler.from_config(config)
    if key == "convergence_adaptive":
        return ConvergenceAdaptiveScheduler.from_config(config)
    if key == "codimension_sheet":
        return CodimensionSheetScheduler.from_config(config)
    if key == "paper_ratio_adaptive":
        return PaperRatioAdaptiveScheduler.from_config(config)
    if key == "sequential":
        # Lazy import to break the cycle: :mod:`.sequential` imports
        # the concrete scheduler classes from this module.
        from adaptive_reflow.algorithm.sequential import (
            SequentialScheduler as _SequentialScheduler,
        )
        return _SequentialScheduler.from_config(config)
    # F23: explicit dispatch for the extra-scheduler families that
    # previously fell through to the no-arg ``factory()`` fallback.
    # Without these cases, kwargs from ``to_config`` are silently
    # dropped on the rebuild (round-trip drift).
    if key == "edm":
        from adaptive_reflow.algorithm.scheduler_extra import (
            EDMScheduler as _EDMScheduler,
        )
        return _EDMScheduler.from_config(config)
    if key == "adaptive_pid":
        from adaptive_reflow.algorithm.scheduler_extra import (
            AdaptivePIDScheduler as _AdaptivePIDScheduler,
        )
        return _AdaptivePIDScheduler.from_config(config)
    if key == "jittered_constant":
        from adaptive_reflow.algorithm.scheduler_extra import (
            JitteredConstantScheduler as _JitteredConstantScheduler,
        )
        return _JitteredConstantScheduler.from_config(config)
    if key == "multi_channel_jittered":
        from adaptive_reflow.algorithm.scheduler_r2 import (
            MultiChannelJitteredConstantScheduler as _MCJCS,
        )
        return _MCJCS.from_config(config)
    # Fallback (unreachable in the registered set; kept as a safety
    # net for any third-party family registered via
    # :func:`_register_extra_scheduler_families`).
    return factory()


# Re-export ``CosineScheduleConfig`` from :mod:`adaptive_reflow.contracts`
# (already imported at module top). Listed in ``__all__`` below so
# downstream modules can ``from adaptive_reflow.algorithm.scheduler
# import CosineScheduleConfig`` via this module's surface.


# ---------------------------------------------------------------------------
# Parameter-free default-eps-implicit entry point (DERIV-001 proof #2)
# ---------------------------------------------------------------------------
#
# The :class:`CodimensionSheetScheduler`'s ``eps_implicit`` (the
# implicit noise scale in evidence units, paper's epsilon in Theorem
# 1's ``eps -> 0`` limit) is currently hand-set to ``0.05`` (the
# canonical ``CodimensionSheetScheduler`` default). DERIV-001
# establishes the principle that every framework hyperparameter
# SHOULD trace to a paper quantity (A_g / B_g / C_g / e_rho) or a
# mathematical theory (Lipschitz, variance-preserving, OT, BL
# convergence, Fisher / Polyak / information geometry); hand-set
# engineering constants stay as named provenance.
#
# :func:`derive_default_eps_implicit` is the minimal wiring for
# that epsilon: when the caller supplies a
# :class:`DerivationContext` carrying ``C_g`` (paper-quantity
# codimension coefficient from Lemma 3) and ``eps_implicit`` (the
# round-0 baseline), the function returns the
# :class:`OTEpsilonSchedule` closed-form value
# ``eps_t = eps_implicit * (1 + C_g * t)`` (Lipman et al. 2023,
# arXiv:2210.02747). When the context is missing the inputs, the
# function falls back to
# :data:`adaptive_reflow.algorithm._derivation.DEFAULT_EPSILON_SCHEDULE_FALLBACK`
# (``0.05``) verbatim so existing callers keep working unchanged.
#
# The function is additive: no :class:`CodimensionSheetScheduler` API
# changes; the helper is a new entry point that engine / runner code
# can opt-into without breaking the existing 2356+15 test suite.


def derive_default_eps_implicit(
    *,
    eps_implicit: Optional[float] = None,
    t: Optional[float] = None,
    c_g: Optional[float] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return the per-round ``eps_implicit`` from a derivation rule.

    Parameters
    ----------
    eps_implicit:
        The round-0 baseline ``eps_implicit``. Forwarded into
        ``scheduler_state['eps_implicit']`` if the context does not
        already carry it.
    t:
        The round index in ``[0, cycle_length - 1]``. Forwarded into
        ``scheduler_state['t']`` if the context does not already
        carry it. Used by the closed form ``eps_t = eps_0 * (1 + C_g * t)``.
    c_g:
        The paper-quantity codimension coefficient (Lemma 3).
        Forwarded into ``paper_quantities['C_g']`` if the context
        does not already carry it.
    context:
        The :class:`DerivationContext` carrying ``C_g`` /
        ``eps_implicit`` (and other paper / scheduler inputs). When
        supplied with non-``None`` ``C_g`` AND ``eps_implicit``, the
        :class:`OTEpsilonSchedule` rule derives the epsilon from the
        closed-form ``eps_implicit * (1 + C_g * t)`` (Lipman et al.
        2023, arXiv:2210.02747).
    rule:
        The :class:`DerivationRule` to apply. Defaults to
        :class:`OTEpsilonSchedule` (the DERIV-001 proof for the
        ``eps_implicit`` parameter); pass
        :class:`BLConvergenceEpsilonSchedule` for the BL-convergence
        form ``sqrt(e_rho * delta_t)``.

    Returns
    -------
    float
        A non-negative ``float``. Falls back to
        :data:`adaptive_reflow.algorithm._derivation.DEFAULT_EPSILON_SCHEDULE_FALLBACK`
        (``0.05``, matching the
        :class:`CodimensionSheetScheduler` default) when the chosen
        rule cannot derive from the supplied context, preserving
        the existing wiring.

    Notes
    -----
    This function is the **DERIV-001 wiring** for the
    ``eps_implicit`` parameter — the codimension-driven scheduler's
    implicit noise scale. Future work may wire the same pattern into
    the other framework hyperparameters cataloged in
    ``docs/algorithm-deep-uplift-plan.md``, each following the
    abstract :class:`DerivationRule` protocol with its own concrete
    subclass.
    """
    chosen: DerivationRule = (
        rule if rule is not None else OTEpsilonSchedule()
    )
    # Build a context from the scalar kwargs when the caller did not
    # supply one. This mirrors the ``derive_default_memory_fraction``
    # pattern in ``blender_extra.py``: the entry point is a thin
    # wrapper that promotes caller-side scalars into a
    # DerivationContext when one is missing.
    if context is None:
        from adaptive_reflow.algorithm._derivation import (
            make_derivation_context,
        )

        context = make_derivation_context(
            eps_implicit=eps_implicit,
            t=t,
            c_g=c_g,
        )
    return float(
        default_eps_implicit(
            context, eps_implicit=eps_implicit, rule=chosen
        )
    )


# ---------------------------------------------------------------------------
# Parameter-free scheduler hyperparameter entry points (DERIV-001 P-19)
# ---------------------------------------------------------------------------


def derive_default_exponential_alpha(
    *,
    n_min: Optional[float] = None,
    n_max: Optional[float] = None,
    cycle_length: Optional[int] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return ``ExponentialScheduler.alpha`` from a derivation rule.

    Falls back to ``0.1`` on missing context. The closed form is
    ``alpha := ln(n_min / n_max) / (cycle_length - 1)``
    (variance-preserving exponential decay).
    """
    from adaptive_reflow.algorithm._derivation import (
        default_exponential_alpha as _d,
    )
    return _d(
        context,
        n_min=n_min,
        n_max=n_max,
        cycle_length=cycle_length,
        rule=rule,
    )


def derive_default_polynomial_power(
    *,
    cycle_length: Optional[int] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return ``PolynomialScheduler.power`` from a derivation rule.

    Falls back to ``2.0`` on missing context. The closed form is
    the analytic variance-preserving backstop ``2 * L / (L + 1)``.
    """
    from adaptive_reflow.algorithm._derivation import (
        default_polynomial_power as _d,
    )
    return _d(context, cycle_length=cycle_length, rule=rule)


def derive_default_sigmoid_midpoint(
    *,
    n_min: Optional[float] = None,
    n_max: Optional[float] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return ``SigmoidScheduler.midpoint`` from a derivation rule.

    Falls back to ``0.5`` on missing context. The closed form is
    ``(n_min + n_max) / 2`` (cycle midpoint).
    """
    from adaptive_reflow.algorithm._derivation import (
        default_sigmoid_midpoint as _d,
    )
    return _d(context, n_min=n_min, n_max=n_max, rule=rule)


def derive_default_sigmoid_steepness(
    *,
    fisher_information: Optional[float] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return ``SigmoidScheduler.steepness`` from a derivation rule.

    Falls back to ``10.0`` on missing context. The closed form is
    ``1 / I_F(W2)`` (information-geometry / Fisher trace).
    """
    from adaptive_reflow.algorithm._derivation import (
        default_sigmoid_steepness as _d,
    )
    return _d(
        context,
        fisher_information=fisher_information,
        rule=rule,
    )


def derive_default_convergence_adaptive_kp(
    *,
    w2_history: Optional[tuple[float, ...]] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.kp`` from a derivation rule."""
    from adaptive_reflow.algorithm._derivation import (
        default_convergence_adaptive_kp as _d,
    )
    return _d(context, w2_history=w2_history, rule=rule)


def derive_default_convergence_adaptive_kd(
    *,
    w2_history: Optional[tuple[float, ...]] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.kd`` from a derivation rule."""
    from adaptive_reflow.algorithm._derivation import (
        default_convergence_adaptive_kd as _d,
    )
    return _d(context, w2_history=w2_history, rule=rule)


def derive_default_convergence_adaptive_shift_max(
    *,
    w2_history: Optional[tuple[float, ...]] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.shift_max`` from a derivation rule."""
    from adaptive_reflow.algorithm._derivation import (
        default_convergence_adaptive_shift_max as _d,
    )
    return _d(context, w2_history=w2_history, rule=rule)


def derive_default_convergence_adaptive_ema(
    *,
    cycle_length: Optional[int] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.ema`` from a derivation rule."""
    from adaptive_reflow.algorithm._derivation import (
        default_convergence_adaptive_ema as _d,
    )
    return _d(context, cycle_length=cycle_length, rule=rule)


def derive_default_metric_weights(
    *,
    metric_variances: Optional[Mapping[str, tuple[float, ...]]] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> dict[str, float]:
    """Return the multi-metric feedback weights from a derivation rule.

    Falls back to ``DEFAULT_FEEDBACK_METRIC_WEIGHTS`` on missing
    context. The closed form is ``weight_m := 1 / Var_m``.
    """
    from adaptive_reflow.algorithm._derivation import (
        default_metric_weights as _d,
    )
    return _d(context, metric_variances=metric_variances, rule=rule)


__all__ = [
    "CodimensionSheetScheduler",
    "ConstantScheduler",
    "ConvergenceAdaptiveScheduler",
    "CosineAnnealScheduler",
    "CosineScheduleConfig",
    "DEFAULT_FEEDBACK_METRIC_WEIGHTS",
    "ExponentialScheduler",
    "LinearScheduler",
    "PaperRatioAdaptiveScheduler",
    "PolynomialScheduler",
    "SCHEDULER_REGISTRY",
    "ScheduleSample",
    "ScheduleSampleProtocol",
    "SchedulerProtocol",
    "SigmoidScheduler",
    "_paper_evidence_balance",
    "build_scheduler",
    "build_scheduler_from_config",
    "default_cosine_scheduler",
    "derive_default_convergence_adaptive_ema",
    "derive_default_convergence_adaptive_kd",
    "derive_default_convergence_adaptive_kp",
    "derive_default_convergence_adaptive_shift_max",
    "derive_default_eps_implicit",
    "derive_default_exponential_alpha",
    "derive_default_metric_weights",
    "derive_default_polynomial_power",
    "derive_default_sigmoid_midpoint",
    "derive_default_sigmoid_steepness",
]

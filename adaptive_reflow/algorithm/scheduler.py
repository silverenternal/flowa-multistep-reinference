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
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from adaptive_reflow.contracts import (
    ArtifactHash,
    CosineScheduleConfig,
    CosineScheduleSample,
    FactorValue,
    RestartTriggerCode,
    hash_artifact,
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

    Any object implementing these five methods can drive the framework.
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

    def __init__(self, config: CosineScheduleConfig) -> None:
        self._config = config
        self._last_sample: ScheduleSample | None = None

    # -- accessors ---------------------------------------------------------

    @property
    def config(self) -> CosineScheduleConfig:
        """Return the frozen :class:`CosineScheduleConfig`."""
        return self._config

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

        n_cap = n_cap_for_round(self._config, round_in_cycle)
        length = int(self._config.cycle_length)
        u_r = float(round_in_cycle) / max(length - 1, 1)

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
) -> CosineAnnealScheduler:
    """Build the default :class:`CosineAnnealScheduler`.

    ``seed`` is accepted for signature parity with stochastic schedulers; the
    cosine family is deterministic, so it only participates in the frozen
    ``config_hash`` (so two schedulers with different seeds remain
    distinguishable in provenance).
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
    return CosineAnnealScheduler(config)


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

    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the constant-capacity sample for one round."""
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
    ) -> None:
        """Construct the convergence-adaptive scheduler.

        :param base: the base cosine scheduler to wrap. Defaults to a
            fresh :func:`default_cosine_scheduler`.
        :param kp: proportional gain on ``(1.0 - ratio)``.
        :param kd: derivative gain on ``delta = w2[-1] - w2[-2]``.
        :param shift_max: maximum absolute shift in ``u_r`` units.
        :param ema: smoothing factor for the W2 EMA (0 = no smoothing,
            1 = ignore new samples).
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
        # Mutable state — cleared by reset().
        self._w2_history: list[float] = []
        self._smoothed_w2: float | None = None
        self._shift: float = 0.0
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "convergence_adaptive_cosine",
                "base_config_hash": str(self._base.config_hash()),
                "kp": float(self._kp),
                "kd": float(self._kd),
                "shift_max": float(self._shift_max),
                "ema": float(self._ema),
            }
        )

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
        """Return the recorded raw W2 history as a tuple."""
        return tuple(self._w2_history)

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
        self._last_sample = None
        self._base.reset()

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Consume one round's W2 metric and update the shift via PID-lite.

        Algorithm:

        1. Pull ``w2 = metrics.get("W2", nan)``.
        2. If ``w2`` is non-finite, ignore (no EMA, no shift).
        3. Update EMA: ``smoothed = ema * w2 + (1 - ema) * prev_smoothed``
           (or ``smoothed = w2`` if no prior smoothed value).
        4. If only one sample, record and return.
        5. Compute ``ratio = history[-1] / history[-2]`` and
           ``delta = history[-1] - history[-2]``.
        6. ``shift_update = kp * (1.0 - ratio) - kd * delta``.
        7. ``self._shift = clip(self._shift + shift_update, -shift_max, +shift_max)``.
        """
        try:
            w2_raw = metrics.get("W2", float("nan"))
        except Exception:
            w2_raw = float("nan")
        try:
            w2 = float(w2_raw)
        except (TypeError, ValueError):
            w2 = float("nan")
        if not math.isfinite(w2):
            return

        # Update EMA.
        if self._smoothed_w2 is None:
            self._smoothed_w2 = float(w2)
        else:
            self._smoothed_w2 = float(
                self._ema * w2 + (1.0 - self._ema) * float(self._smoothed_w2)
            )

        # Record history.
        self._w2_history.append(float(w2))

        # Need at least two samples to compute ratio / delta.
        if len(self._w2_history) < 2:
            return

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

        shift_update = float(self._kp) * (1.0 - ratio) - float(self._kd) * delta
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


SCHEDULER_REGISTRY: dict[str, Callable[..., SchedulerProtocol]] = {
    "cosine": default_cosine_scheduler,
    "constant": ConstantScheduler,
    "linear": LinearScheduler,
    "exponential": ExponentialScheduler,
    "polynomial": PolynomialScheduler,
    "sigmoid": SigmoidScheduler,
    "convergence_adaptive": ConvergenceAdaptiveScheduler,
}
"""Mapping from schedule family name to its :class:`SchedulerProtocol` factory.

The framework looks schedulers up here when constructing one from a string
identifier (e.g. a config file value). Each entry is a callable that accepts
the family-specific kwargs and returns a :class:`SchedulerProtocol`
instance. The cosine entry routes through :func:`default_cosine_scheduler`
because :class:`CosineAnnealScheduler` takes a frozen
:class:`CosineScheduleConfig` rather than raw kwargs.


The exponential family is *not* one of the canonical :data:`SCHEDULE_FAMILIES`
literals — it is an algorithm-layer addition that lives alongside the
contracts-layer taxonomy.
"""


def build_scheduler(family: str, **kwargs: object) -> SchedulerProtocol:
    """Factory: build a :class:`SchedulerProtocol` from a family name.

    :param family: one of the keys of :data:`SCHEDULER_REGISTRY`
        (``"cosine"``, ``"constant"``, ``"linear"``, ``"exponential"``).
    :param kwargs: forwarded verbatim to the matching factory. For
        ``"cosine"`` the kwargs must match :func:`default_cosine_scheduler`;
        for ``"constant"`` they must match :class:`ConstantScheduler`; etc.
    :returns: a fresh :class:`SchedulerProtocol` instance for that family.
    :raises KeyError: ``family`` is not a registered schedule family.
    """
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


__all__ = [
    "ConstantScheduler",
    "ConvergenceAdaptiveScheduler",
    "CosineAnnealScheduler",
    "ExponentialScheduler",
    "LinearScheduler",
    "PolynomialScheduler",
    "SCHEDULER_REGISTRY",
    "ScheduleSample",
    "ScheduleSampleProtocol",
    "SchedulerProtocol",
    "SigmoidScheduler",
    "build_scheduler",
    "default_cosine_scheduler",
]

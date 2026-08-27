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
from collections.abc import Callable
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
# Registry + factory
# ---------------------------------------------------------------------------


SCHEDULER_REGISTRY: dict[str, Callable[..., SchedulerProtocol]] = {
    "cosine": default_cosine_scheduler,
    "constant": ConstantScheduler,
    "linear": LinearScheduler,
    "exponential": ExponentialScheduler,
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
    "CosineAnnealScheduler",
    "ExponentialScheduler",
    "LinearScheduler",
    "SCHEDULER_REGISTRY",
    "ScheduleSample",
    "ScheduleSampleProtocol",
    "SchedulerProtocol",
    "build_scheduler",
    "default_cosine_scheduler",
]

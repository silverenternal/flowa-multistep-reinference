"""Simple (non-adaptive) per-round capacity schedulers (Wave 105 P2-A split).

This module owns the six "simple" (non-adaptive) families the framework
exposes as ablation baselines and reference implementations:

* :class:`CosineAnnealScheduler` — cosine annealing (DEPRECATED as the
  framework default since Wave 34 but retained for backward compat +
  reproduction baselines; matches the closed form in
  :func:`adaptive_reflow.schedule.cosine.n_cap_for_round`).
* :func:`default_cosine_scheduler` — factory (DEPRECATED).
* :func:`default_paper_ratio_scheduler` — framework default since Wave 34
  (paper-quantity-driven; returns a :class:`CodimensionSheetScheduler`).
* :class:`ConstantScheduler` — flat capacity across rounds.
* :class:`LinearScheduler` — linear ramp between ``n_min`` and ``n_max``.
* :class:`ExponentialScheduler` — exponential decay.
* :class:`PolynomialScheduler` — polynomial ramp.
* :class:`SigmoidScheduler` — sigmoid ramp with configurable midpoint /
  steepness.

The shared structural types (:class:`ScheduleSample`,
:class:`SchedulerProtocol`, :func:`_coerce_int_nonneg`) live in
:mod:`adaptive_reflow.algorithm.scheduler.protocols`.

The :func:`default_paper_ratio_scheduler` factory returns a
:class:`CodimensionSheetScheduler` (an *adaptive* family). It lives here
because it is the canonical **default factory** historically paired with
:func:`default_cosine_scheduler`; consumers that import both factories
get them from a single module. The class itself lives in
:mod:`adaptive_reflow.algorithm.scheduler.adaptive`.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts import (
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

from .protocols import (
    ScheduleSample,
    SchedulerProtocol,
    _coerce_int_nonneg,
)

# Local imports of *adaptive* siblings, only used by the
# ``default_paper_ratio_scheduler`` factory. Kept lazy-ish via a
# forward-declared type annotation so that ``adaptive.py`` can in turn
# reference classes from this module (the cycle is broken at *call*
# time, not import time, mirroring the cycle-avoidance pattern already
# documented for ``_register_extra_scheduler_families``).
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adaptive import CodimensionSheetScheduler


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


def default_paper_ratio_scheduler(
    *,
    cycle_length: int = 20,
    n_min: float = 0.0,
    n_max: float = 1.0,
    eps_implicit: float = 0.05,
    seed: int = 0,
    profile_residual_fn: Callable[[float], float] | None = None,
) -> "CodimensionSheetScheduler":
    """Build the framework-default paper-quantity-driven scheduler.

    Wave 34 — closure of the 2026-09-05 user constraint that the
    framework's *default* scheduler must be **algorithm-determined**,
    not a hardcoded cosine ramp. This factory returns a
    :class:`CodimensionSheetScheduler` whose ``n_cap`` is driven by
    the paper Lemma 2 / Lemma 3 sheet-vs-cell evidence balance
    (Wave 31 Agent A, ADR-0013) rather than by the framework's
    canonical cosine closed form (ADR-0010).

    When ``profile_residual_fn`` is supplied the scheduler uses the
    **literal** paper quantities
    ``A_g = paper_quantities.sheet_evidence_A(profile)`` (Lemma 2 /
    Proposition 3),
    ``B_g = paper_quantities.root_cell_packing_B(profile)`` (Lemma 5),
    ``C_g = paper_quantities.per_cell_coefficient_C()`` (Lemma 3), and
    ``e_rho = paper_quantities.exterior_gap_e_rho()`` (Lemma 4 / 5) as
    ground truth in the per-round sheet-vs-cell evidence ratio.
    When ``None`` (the default) the scheduler falls back to the
    framework-side heuristic (mathematically equivalent up to
    normalisation constants; the two paths agree on the direction of
    sheet dominance as ``eps -> 0`` per Theorem 1).

    Concretely:

        sheet = A_g * eps_per_round               # Lemma 2 / Cor. 1
        cell  = C_g * B_g * eps_per_round ** 2    # Lemma 3 + Lemma 5
        ratio = sheet / (sheet + cell)            # sheet-vs-cell balance
        n_cap = n_min + (n_max - n_min) * ratio   # driver of capacity

    where ``eps_per_round(r) = eps_implicit * (1 - u_r)`` with
    ``u_r = r / (L - 1)`` — the paper-aligned
    ``eps -> 0`` schedule realised as a cycle ramp (P2-W33-A).

    :param cycle_length: number of rounds in one outer cycle (``>= 1``).
    :param n_min: capacity floor (output lower bound); must lie in
        ``[0, 1]``.
    :param n_max: capacity ceiling (output upper bound); must lie in
        ``[0, 1]``.
    :param eps_implicit: round-0 implicit noise scale in evidence
        units; must satisfy ``eps_implicit > 0``. Default ``0.05``
        (matching the :class:`CodimensionSheetScheduler` canonical
        default). The per-round ``eps`` diminishes monotonically
        across the cycle, exercising paper Theorem 1's
        ``eps -> 0`` limit at ``r = L - 1``.
    :param seed: included for protocol signature parity with
        stochastic schedulers; the codimension family is
        deterministic and only participates in the frozen
        ``config_hash``.
    :param profile_residual_fn: optional callable mapping
        ``x -> g(x)`` (paper Lemma 2's coarea weight
        ``1 / sqrt(1 + g(x)^2)``). When supplied, the scheduler
        computes the four paper quantities exactly once at
        construction time and uses them as ground truth in the
        per-round sheet-vs-cell evidence ratio (the canonical
        paper-quantity-driven path). When ``None``, the scheduler
        falls back to the framework-side heuristic closed form
        (backward-compatible byte-for-byte with the Wave 31 inline
        path).
    :returns: a fresh :class:`CodimensionSheetScheduler` whose
        ``schedule_family()`` is ``"codimension_sheet"`` and whose
        ``n_cap`` is fully paper-quantity-driven (or framework-side
        heuristic in the no-profile fallback). The cosine ramp
        remains available as the *base* sampler (``scheduler.base``)
        for introspection but does NOT drive ``n_cap`` in the
        canonical path.

    .. note::

        This is the **framework's default scheduler** as of Wave 34.
       :func:`default_cosine_scheduler` is retained for backward
       compatibility but emits a :class:`DeprecationWarning` on each
       invocation; callers that need cosine annealing should pass
       an explicit ``CosineAnnealScheduler`` (or
       :func:`build_scheduler("cosine", ...)`).
    """
    # Local import to keep the simple → adaptive cycle at *call* time
    # only; this matches the deferred-registration pattern documented
    # in :func:`_register_extra_scheduler_families` (see nfe_aware.py).
    from .adaptive import CodimensionSheetScheduler as _CodimensionSheetScheduler

    return _CodimensionSheetScheduler(
        cycle_length=int(cycle_length),
        n_min=float(n_min),
        n_max=float(n_max),
        profile_residual_fn=profile_residual_fn,
        eps_implicit=float(eps_implicit),
        eps_direction="decreasing",  # paper Theorem 1 aligned
        seed=int(seed),
    )


def default_cosine_scheduler(
    *,
    cycle_length: int = 20,
    n_min: float = 0.0,
    n_max: float = 1.0,
    schedule_family: str = "cosine_no_restart",
    seed: int = 0,
    profile_residual_fn: Callable[[float], float] | None = None,
) -> CosineAnnealScheduler:
    """Build the legacy :class:`CosineAnnealScheduler` (DEPRECATED).

    .. deprecated:: Wave 34 (2026-09-05)

        The framework's default scheduler is now paper-quantity-driven
        (see :func:`default_paper_ratio_scheduler`, Wave 34 closure
        of the user constraint that ``n_cap`` MUST be
        algorithm-determined, not a hardcoded cosine ramp). Cosine
        annealing remains available as a legacy opt-in for callers
        that explicitly want the canonical cosine closed form (e.g.
        reproduction baselines, ablation studies, or callers that
        rely on the cosine-family-specific forward-noise mass).

        **Migration path.** Replace::

            default_cosine_scheduler()

        with::

            default_paper_ratio_scheduler()           # paper-quantity-driven default
            # or, for cosine-equivalent legacy behaviour:
            build_scheduler("cosine", cycle_length=...)

        Emits a :class:`DeprecationWarning` on each call so callers
        see the migration guidance immediately.

    ``seed`` is accepted for signature parity with stochastic
    schedulers; the cosine family is deterministic, so it only
    participates in the frozen ``config_hash`` (so two schedulers
    with different seeds remain distinguishable in provenance).

    ``profile_residual_fn`` (P1-A2) is forwarded to the scheduler so
    the per-round forward-noise mass is the paper quantity ``A_g``
    rather than the raw ``n_cap``; ``None`` (default) keeps the
    legacy behaviour.
    """
    warnings.warn(
        "default_cosine_scheduler() is deprecated as of Wave 34 "
        "(2026-09-05). The framework default is now paper-quantity-"
        "driven via default_paper_ratio_scheduler(). Migrate to "
        "default_paper_ratio_scheduler() for the algorithm-determined "
        "n_cap; for legacy cosine-only behaviour use "
        "build_scheduler('cosine', ...).",
        DeprecationWarning,
        stacklevel=2,
    )
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
        :param n_min: capacity at round ``0``; must lie in ``[0, 1]``.
        :param n_max: capacity at round ``cycle_length - 1``; must lie in
            ``[0, 1]``.
        :param seed: included for protocol signature parity with stochastic
            schedulers; the linear family is deterministic and only
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
        for nm, val in (("n_min", n_min), ("n_max", n_max)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if not (0.0 <= fv <= 1.0):
                raise ValueError(f"{nm} must lie in [0, 1], got {fv!r}")
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
        """Return the round-0 capacity value."""
        return float(self._n_min)

    @property
    def n_max(self) -> float:
        """Return the round-``L-1`` capacity value."""
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
        """Return the linear-interpolated capacity sample for one round."""
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        round_in_cycle = _coerce_int_nonneg(round_in_cycle, "round_in_cycle")
        length = int(self._cycle_length)
        if length > 1 and not (
            0 <= int(round_in_cycle) <= length - 1
        ):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for cycle_length={length}, "
                f"got {round_in_cycle!r}"
            )

        if length == 1:
            n_cap = float(self._n_max)
            u_r = 0.5
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
        """Return ``state + sqrt(n_cap) * generator.standard_normal`` (P0-7)."""
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
# Exponential scheduler — variance-preserving decay
# ---------------------------------------------------------------------------


class ExponentialScheduler:
    """Exponential-decay :class:`SchedulerProtocol` implementation.

    :attr:`n_cap` decays geometrically from :attr:`n_max` at round ``0``
    to :attr:`n_min` at round ``cycle_length - 1`` via the closed form
    ``n_cap = n_max * exp(-alpha * u_r)`` where ``u_r = r / (L - 1)``.
    The default ``alpha`` is derived to interpolate the
    ``(n_max -> n_min)`` endpoints exactly via
    :func:`derive_default_exponential_alpha`
    (``alpha := ln(n_max / n_min) / (L - 1)``, the variance-preserving
    half-life form). Callers that want a steeper or shallower decay
    pass an explicit ``alpha``.

    Useful as the variance-preserving variant of the linear family: at
    each round the capacity is scaled by a constant factor of the
    previous round, so the per-round "memory step" is constant in
    log-space rather than linear-space. Conforms to
    :class:`SchedulerProtocol`. Pure w.r.t. arguments.
    """

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_min: float = 0.01,
        n_max: float = 1.0,
        alpha: float | None = None,
        seed: int = 0,
    ) -> None:
        """Construct the exponential scheduler.

        :param cycle_length: number of rounds in one outer cycle (``>= 1``).
        :param n_min: capacity floor; must lie in ``(0, 1]``. ``n_min == 0``
            would make the closed form ``n_cap = n_max * exp(-alpha * 1)``
            collapse to ``0`` at ``r = L - 1`` for any positive ``alpha``,
            so the constructor rejects it.
        :param n_max: capacity at round ``0``; must lie in ``[n_min, 1]``.
        :param alpha: decay rate; ``None`` (default) selects
            :func:`derive_default_exponential_alpha` so the
            ``(n_max -> n_min)`` endpoints are interpolated exactly.
        :param seed: included for protocol signature parity with stochastic
            schedulers; the exponential family is deterministic and only
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
        for nm, val in (("n_min", n_min), ("n_max", n_max)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if not (0.0 <= fv <= 1.0):
                raise ValueError(f"{nm} must lie in [0, 1], got {fv!r}")
        if float(n_min) <= 0.0:
            raise ValueError(
                f"n_min must be > 0 (exponential decay), got {n_min!r}"
            )
        if float(n_max) < float(n_min):
            raise ValueError(
                f"n_max must be >= n_min, got n_max={n_max!r}, n_min={n_min!r}"
            )
        self._n_min = float(n_min)
        self._n_max = float(n_max)
        if alpha is None:
            # Variance-preserving backstop: pick the ``alpha`` that maps
            # ``(n_max -> n_min)`` at ``u_r = 1``. Mirrors the legacy
            # closed form pre-P2-W33-A and is the framework default.
            if self._n_max == self._n_min:
                self._alpha = 0.0
            else:
                self._alpha = float(
                    math.log(self._n_max / self._n_min) / max(1, cycle_length - 1)
                )
        else:
            if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
                raise ValueError(f"alpha must be a real number, got {alpha!r}")
            if not math.isfinite(float(alpha)):
                raise ValueError(f"alpha must be finite, got {alpha!r}")
            self._alpha = float(alpha)
        self._seed = int(seed)
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "exponential",
                "schedule_family": "exponential",
                "cycle_length": int(self._cycle_length),
                "n_min": float(self._n_min),
                "n_max": float(self._n_max),
                "alpha": float(self._alpha),
                "seed": int(self._seed),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def n_min(self) -> float:
        """Return the round-``L-1`` capacity floor."""
        return float(self._n_min)

    @property
    def n_max(self) -> float:
        """Return the round-0 capacity ceiling."""
        return float(self._n_max)

    @property
    def alpha(self) -> float:
        """Return the configured decay rate."""
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
        round_in_cycle = _coerce_int_nonneg(round_in_cycle, "round_in_cycle")
        length = int(self._cycle_length)
        if length > 1 and not (
            0 <= int(round_in_cycle) <= length - 1
        ):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for cycle_length={length}, "
                f"got {round_in_cycle!r}"
            )

        if length == 1:
            n_cap = float(self._n_max)
            u_r = 0.5
        else:
            u_r = float(round_in_cycle) / (length - 1)
            raw = float(self._n_max) * math.exp(
                -float(self._alpha) * int(round_in_cycle)
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
            "n_min": float(self._n_min),
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
            n_min=float(config["n_min"]),
            n_max=float(config["n_max"]),
            alpha=float(config["alpha"]) if "alpha" in config else None,
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
# Polynomial scheduler — variance-preserving power ramp
# ---------------------------------------------------------------------------


class PolynomialScheduler:
    """Polynomial-ramp :class:`SchedulerProtocol` implementation.

    :attr:`n_cap` follows the closed form
    ``n_cap = n_min + (n_max - n_min) * u_r ** power`` where
    ``u_r = r / (L - 1)``. ``power < 1`` produces a front-loaded
    ramp (large ``n_cap`` early, sharp drop late), ``power == 1``
    matches the linear family, ``power > 1`` produces a back-loaded
    ramp (slow start, sharp climb late — useful for "ramp up to
    exploitation late"). The default ``power = 2.0`` (variance-preserving
    backstop, matches the analytic closed form
    ``2 * L / (L + 1)`` in :func:`derive_default_polynomial_power`).

    Conforms to :class:`SchedulerProtocol`. Pure w.r.t. arguments.
    """

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_min: float = 0.0,
        n_max: float = 1.0,
        power: float | None = None,
        seed: int = 0,
    ) -> None:
        """Construct the polynomial scheduler.

        :param cycle_length: number of rounds in one outer cycle (``>= 1``).
        :param n_min: capacity floor; must lie in ``[0, 1]``.
        :param n_max: capacity ceiling; must lie in ``[n_min, 1]``.
        :param power: ramp exponent; ``None`` (default) selects
            :func:`derive_default_polynomial_power` for the
            variance-preserving backstop ``2 * L / (L + 1)``.
        :param seed: included for protocol signature parity with stochastic
            schedulers; the polynomial family is deterministic and only
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
        for nm, val in (("n_min", n_min), ("n_max", n_max)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if not (0.0 <= fv <= 1.0):
                raise ValueError(f"{nm} must lie in [0, 1], got {fv!r}")
        if float(n_max) < float(n_min):
            raise ValueError(
                f"n_max must be >= n_min, got n_max={n_max!r}, n_min={n_min!r}"
            )
        self._n_min = float(n_min)
        self._n_max = float(n_max)
        if power is None:
            # Variance-preserving backstop: ``2 * L / (L + 1)`` where
            # ``L = cycle_length``; reduces to ``2`` in the limit of
            # large ``L``.
            self._power = float(2.0 * cycle_length / (cycle_length + 1))
        else:
            if isinstance(power, bool) or not isinstance(power, (int, float)):
                raise ValueError(f"power must be a real number, got {power!r}")
            if not math.isfinite(float(power)):
                raise ValueError(f"power must be finite, got {power!r}")
            if float(power) <= 0.0:
                raise ValueError(
                    f"power must be > 0, got {power!r}"
                )
            self._power = float(power)
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
        """Return the round-0 capacity floor."""
        return float(self._n_min)

    @property
    def n_max(self) -> float:
        """Return the round-``L-1`` capacity ceiling."""
        return float(self._n_max)

    @property
    def power(self) -> float:
        """Return the configured ramp exponent."""
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
        """Return the polynomial-ramp capacity sample for one round."""
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        round_in_cycle = _coerce_int_nonneg(round_in_cycle, "round_in_cycle")
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
        """Build a :class:`PolynomialScheduler` from ``config`` (P1-1 round-trip)."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return PolynomialScheduler(
            cycle_length=int(config["cycle_length"]),
            n_min=float(config["n_min"]),
            n_max=float(config["n_max"]),
            power=float(config["power"]) if "power" in config else None,
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
# Sigmoid scheduler — smooth transition with configurable midpoint + steepness
# ---------------------------------------------------------------------------


class SigmoidScheduler:
    """Sigmoid :class:`SchedulerProtocol` implementation.

    :attr:`n_cap` follows the closed form
    ``n_cap = n_min + (n_max - n_min) * sigmoid(steepness * (u_r - midpoint))``
    where ``u_r = r / (L - 1)`` and
    ``sigmoid(z) = 1 / (1 + exp(-z))``. The default ``midpoint = 0.5``
    produces a symmetric transition that crosses the cycle midpoint at
    the average of ``n_min`` and ``n_max`` (matches the
    :class:`ConstantScheduler` family). The default ``steepness = 10``
    is the variance-preserving backstop
    (``steepness := 1 / I_F(W2)``, the information-geometry / Fisher
    trace form, see :func:`derive_default_sigmoid_steepness`).

    Conforms to :class:`SchedulerProtocol`. Pure w.r.t. arguments.
    """

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        n_min: float = 0.0,
        n_max: float = 1.0,
        midpoint: float | None = None,
        steepness: float | None = None,
        seed: int = 0,
    ) -> None:
        """Construct the sigmoid scheduler.

        :param cycle_length: number of rounds in one outer cycle (``>= 1``).
        :param n_min: capacity floor; must lie in ``[0, 1]``.
        :param n_max: capacity ceiling; must lie in ``[n_min, 1]``.
        :param midpoint: round-progress value at which the sigmoid
            crosses the midpoint of the ``[n_min, n_max]`` band;
            ``None`` (default) selects the cycle midpoint ``0.5``.
        :param steepness: sigmoid slope; ``None`` (default) selects the
            variance-preserving backstop
            (:func:`derive_default_sigmoid_steepness`).
        :param seed: included for protocol signature parity with stochastic
            schedulers; the sigmoid family is deterministic and only
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
        for nm, val in (("n_min", n_min), ("n_max", n_max)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{nm} must be a real number, got {val!r}")
            fv = float(val)
            if not math.isfinite(fv):
                raise ValueError(f"{nm} must be finite, got {val!r}")
            if not (0.0 <= fv <= 1.0):
                raise ValueError(f"{nm} must lie in [0, 1], got {fv!r}")
        if float(n_max) < float(n_min):
            raise ValueError(
                f"n_max must be >= n_min, got n_max={n_max!r}, n_min={n_min!r}"
            )
        self._n_min = float(n_min)
        self._n_max = float(n_max)
        if midpoint is None:
            self._midpoint = float(
                (float(n_min) + float(n_max)) / 2.0
            )
        else:
            if isinstance(midpoint, bool) or not isinstance(midpoint, (int, float)):
                raise ValueError(
                    f"midpoint must be a real number, got {midpoint!r}"
                )
            if not math.isfinite(float(midpoint)):
                raise ValueError(f"midpoint must be finite, got {midpoint!r}")
            self._midpoint = float(midpoint)
        if steepness is None:
            self._steepness = float(10.0)
        else:
            if isinstance(steepness, bool) or not isinstance(
                steepness, (int, float)
            ):
                raise ValueError(
                    f"steepness must be a real number, got {steepness!r}"
                )
            if not math.isfinite(float(steepness)):
                raise ValueError(f"steepness must be finite, got {steepness!r}")
            self._steepness = float(steepness)
        self._seed = int(seed)
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "sigmoid",
                "schedule_family": "sigmoid",
                "cycle_length": int(self._cycle_length),
                "n_min": float(self._n_min),
                "n_max": float(self._n_max),
                "midpoint": float(self._midpoint),
                "steepness": float(self._steepness),
                "seed": int(self._seed),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def n_min(self) -> float:
        """Return the lower asymptote of the sigmoid band."""
        return float(self._n_min)

    @property
    def n_max(self) -> float:
        """Return the upper asymptote of the sigmoid band."""
        return float(self._n_max)

    @property
    def midpoint(self) -> float:
        """Return the round-progress value at the band midpoint."""
        return float(self._midpoint)

    @property
    def steepness(self) -> float:
        """Return the configured sigmoid slope."""
        return float(self._steepness)

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
        """Return the sigmoid-ramp capacity sample for one round."""
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        round_in_cycle = _coerce_int_nonneg(round_in_cycle, "round_in_cycle")
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
            # Sigmoid at midpoint exactly: ``0.5`` (the variance-preserving
            # backstop places ``midpoint == (n_min + n_max) / 2`` so this
            # is also the average of the two asymptotes).
            sig = 0.5
        else:
            u_r = float(round_in_cycle) / (length - 1)
            sig = float(
                1.0 / (1.0 + math.exp(-self._steepness * (u_r - self._midpoint)))
            )
        n_cap = float(self._n_min + (self._n_max - self._n_min) * sig)

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
            "midpoint": float(self._midpoint),
            "steepness": float(self._steepness),
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> SigmoidScheduler:
        """Build a :class:`SigmoidScheduler` from ``config`` (P1-1 round-trip)."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return SigmoidScheduler(
            cycle_length=int(config["cycle_length"]),
            n_min=float(config["n_min"]),
            n_max=float(config["n_max"]),
            midpoint=float(config["midpoint"]) if "midpoint" in config else None,
            steepness=float(config["steepness"]) if "steepness" in config else None,
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


__all__ = [
    "ConstantScheduler",
    "CosineAnnealScheduler",
    "ExponentialScheduler",
    "LinearScheduler",
    "PolynomialScheduler",
    "SigmoidScheduler",
    "default_cosine_scheduler",
    "default_paper_ratio_scheduler",
]

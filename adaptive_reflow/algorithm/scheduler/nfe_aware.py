"""NFE-aware constant-capacity scheduler + registry / factory (Wave 105 P2-A split).

This module owns the **NFE-aware** scheduler family plus the registry /
factory / ``derive_default_*`` helpers that fan out across all scheduler
families:

* :class:`NFEAwareMemoryScheduler` — Wave 61 Agent 2 smooth-scaling
  successor to Wave 58 Agent 1's binary NFE-adaptive gate. Scales
  ``memory_fraction`` *continuously* from 0 (low NFE) to
  ``max_memory_fraction`` (high NFE) via the closed-form
  ``m(r) = min(M, M * (nfe_per_round / threshold) ** 2)``.
* :func:`build_scheduler` / :func:`build_scheduler_from_config` —
  polymorphic factories that dispatch on the ``family`` key against
  :data:`SCHEDULER_REGISTRY`.
* :data:`SCHEDULER_REGISTRY` — the canonical map from family name to
  factory callable. New families register here via
  :func:`_register_extra_scheduler_families` (Phase-2 defer-to-first-
  call registration that breaks the scheduler/__init__ cycle).
* :func:`derive_default_*` entry points — the DERIV-001 P-19 wiring
  for the framework's per-scheduler hyperparameters
  (DERIV-001 P-19 / Lipman et al. 2023 ``eps_implicit * (1 + C_g * t)``).

The shared structural types (:class:`ScheduleSample`,
:class:`SchedulerProtocol`, :func:`_coerce_int_nonneg`) live in
:mod:`adaptive_reflow.algorithm.scheduler.protocols`.

Why this lives with the NFE-aware scheduler: the registry needs every
concrete family registered as a factory call (or callable), the
``derive_default_*`` helpers need every concrete class for their
"concrete-scheduler" closures, and the NFE-aware scheduler is the
*only* deterministic-constant-capacity family. Grouping all three
here keeps the "registry + family singletons" in one file.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any, Optional

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts import (
    CosineScheduleSample,
    hash_artifact,
)

from .adaptive import (
    CodimensionSheetScheduler,
    ConvergenceAdaptiveScheduler,
    PaperRatioAdaptiveScheduler,
)

# NOTE: ``adaptive_reflow.algorithm._derivation`` is imported lazily
# inside each :func:`derive_default_*` body and inside
# :func:`derive_default_eps_implicit`. Importing it at module top would
# trigger ``adaptive_reflow.algorithm.__init__`` -> ``batched_runner`` ->
# ``adaptive_reflow.algorithm.scheduler`` -> this shim -> this module,
# closing a load-time cycle that is broken in the partial-import phase
# by the absence of ``CosineAnnealScheduler`` on the still-loading
# ``scheduler.nfe_aware`` namespace. The deferred import matches the
# pattern already used inside the function bodies themselves.
from .protocols import (
    SchedulerProtocol,
    ScheduleSample,
    _coerce_int_nonneg,
)
from .simple import (
    ConstantScheduler,
    CosineAnnealScheduler,
    ExponentialScheduler,
    LinearScheduler,
    PolynomialScheduler,
    SigmoidScheduler,
    default_cosine_scheduler,
)

DEFAULT_NFE_AWARE_THRESHOLD: int = 10
"""Default NFE-per-round threshold at which ``memory_fraction`` saturates at
``max_memory_fraction``.

Wave 57 Agent D's recommendation B2: scale the per-round ``memory_fraction``
smoothly from 0 (at low NFE) up to ``max_memory_fraction`` (at high NFE),
rather than Wave 58 Agent 1's binary gate (which fires only on
``effective_nfe < min_nfe`` and leaves half the regressions untouched).
The default ``10`` matches Wave 58's gate threshold so the two
formulations agree at the boundary.
"""


DEFAULT_NFE_AWARE_MAX: float = 0.5
"""Default saturation value for ``memory_fraction`` (matches the framework's
canonical ``m = 0.5`` restart-blend). Mirrors the
``apply_restart_distribution`` default in :mod:`adaptive_reflow.adapters`.
"""


# ---------------------------------------------------------------------------
# NFE-aware memory scheduler — Wave 57 Agent D's B2 / Wave 61 Agent 2
# ---------------------------------------------------------------------------


class NFEAwareMemoryScheduler:
    """NFE-aware constant-capacity :class:`SchedulerProtocol`.

    Wave 61 Agent 2 — smooth-scaling answer to Wave 58 Agent 1's binary
    NFE-adaptive gate (`docs/audit/wave58-nfe-adaptive-gate-impl.md`).
    Where the gate fires only when ``effective_nfe < min_nfe`` (a step
    function at the threshold), this scheduler scales ``memory_fraction``
    *smoothly* from 0 (low NFE) to ``max_memory_fraction`` (high NFE) per
    Wave 57 Agent D's recommendation B2 in
    `docs/audit/wave57-nfe-adaptive-research.md` §4.

    Closed form
    -----------

    For a cycle with ``n_rounds`` rounds, a TOTAL NFE budget ``nfe_budget``
    split evenly across rounds, and a threshold ``threshold``:

        nfe_per_round = nfe_budget / n_rounds
        ratio         = nfe_per_round / threshold
        m(r)          = min(max_memory_fraction, max_memory_fraction * ratio ** 2)

    where :attr:`m(r)` is the per-round ``memory_fraction`` returned via
    :meth:`ScheduleSample.memory_fraction` (equivalently, ``n_cap = 1 - m(r)``).

    Worked examples (with ``max_memory_fraction=0.5``,
    ``threshold=10``, ``n_rounds=3``):

    +-----------------+----------------+-------------------+---------------------+
    | ``nfe_budget``  | nfe_per_round  | ratio             | m(r) / memory_frac  |
    +=================+================+===================+=====================+
    | 10              | 3.33           | 0.333             | ``~0.028``          |
    | 50              | 16.67          | 1.667             | ``0.5`` (saturated) |
    | 200             | 66.67          | 6.667             | ``0.5`` (saturated) |
    | 500             | 166.67         | 16.667            | ``0.5`` (saturated) |
    +-----------------+----------------+-------------------+---------------------+

    Why the squared curve
    ---------------------

    The quadratic ``ratio ** 2`` front-loads the schedule so the
    ``memory_fraction`` only really starts climbing once ``nfe_per_round``
    approaches ``threshold``; below the threshold the blend is so soft
    that the framework essentially passes through (which is exactly what
    the Wave 58 gate's ``m = 0`` corner provides). A linear ramp would
    reach ``max_memory_fraction / 2`` at ``ratio = 0.5`` (i.e. ``nfe_per_round
    = threshold / 2``), which is too aggressive given the empirical
    evidence that the framework only starts helping once the round has
    enough steps to re-absorb a fresh-prior perturbation.

    Where this differs from Wave 58's gate
    ---------------------------------------

    The Wave 58 gate (``FLOWMOL3_RESTART_MIN_NFE = 20`` in
    `adaptive_reflow/adapters/flowmol3.py`) is a **per-adapter**,
    **binary** mechanism: at ``effective_nfe < min_nfe`` the adapter
    skips the blend entirely; at ``effective_nfe >= min_nfe`` it blends
    at the canonical ``m = 0.5``. That addresses the NFE=10 stratum but
    does nothing for the NFE=50 / NFE=200 strata where the framework
    was also regressing in Wave 57's 9-cell v3 grid.

    This scheduler is a **per-scheduler**, **continuous** mechanism: at
    every NFE budget it picks a *smaller* blend coefficient. At low NFE
    the blend is so soft the corruption vanishes; at high NFE the blend
    saturates at ``max_memory_fraction = 0.5``, matching the canonical
    framework. This is the ``m(r)`` shape that Wave 57 Agent D identified
    as the strictly-more-expressive successor to the gate.

    Configuration
    -------------

    :param cycle_length: number of rounds in one outer cycle (``>= 1``).
        All rounds share the same ``memory_fraction`` (the schedule is
        *constant* within a cycle by design; only the cross-cycle
        parameter ``nfe_budget`` varies).
    :param nfe_budget: TOTAL NFE budget for the cycle (default ``50``,
        the FlowMol3 paper default). The per-round count is
        ``nfe_budget / n_rounds``.
    :param n_rounds: number of restart rounds the budget splits across
        (default ``3``, matching Wave 57's grid).
    :param threshold: NFE-per-round value at which ``m(r)`` saturates
        (default :data:`DEFAULT_NFE_AWARE_THRESHOLD` = 10, matching
        Wave 58's gate).
    :param max_memory_fraction: saturation cap (default
        :data:`DEFAULT_NFE_AWARE_MAX` = 0.5, matching the canonical
        framework).
    :param seed: included for protocol signature parity with stochastic
        schedulers; the NFE-aware family is deterministic and only
        participates in the frozen :attr:`config_hash`.

    Conforms to :class:`SchedulerProtocol`. Pure w.r.t. arguments.
    """

    def __init__(
        self,
        *,
        cycle_length: int = 20,
        nfe_budget: int = 50,
        n_rounds: int = 3,
        threshold: int = DEFAULT_NFE_AWARE_THRESHOLD,
        max_memory_fraction: float = DEFAULT_NFE_AWARE_MAX,
        seed: int = 0,
    ) -> None:
        """Construct the NFE-aware memory scheduler.

        :param cycle_length: number of rounds in one outer cycle
            (``>= 1``).
        :param nfe_budget: TOTAL NFE budget for the cycle; must be
            ``> 0``. ``nfe_budget <= 0`` is rejected because the
            scheduler cannot derive a meaningful per-round NFE.
        :param n_rounds: number of restart rounds (``>= 1``); must be
            ``>= 1``.
        :param threshold: NFE-per-round value at which the
            ``memory_fraction`` saturates; must be ``> 0``.
        :param max_memory_fraction: saturation cap; must lie in
            ``[0, 1]``. Values outside this range are rejected.
        :param seed: included for signature parity; only enters the
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
        for nm, val in (
            ("nfe_budget", nfe_budget),
            ("n_rounds", n_rounds),
            ("threshold", threshold),
        ):
            if isinstance(val, bool) or not isinstance(val, int):
                raise ValueError(f"{nm} must be int, got {val!r}")
            if int(val) < 1:
                raise ValueError(f"{nm} must be >= 1, got {val!r}")
        if isinstance(max_memory_fraction, bool) or not isinstance(
            max_memory_fraction, (int, float)
        ):
            raise ValueError(
                f"max_memory_fraction must be a real number, "
                f"got {max_memory_fraction!r}"
            )
        max_mf_f = float(max_memory_fraction)
        if not math.isfinite(max_mf_f):
            raise ValueError(
                f"max_memory_fraction must be finite, "
                f"got {max_memory_fraction!r}"
            )
        if not (0.0 <= max_mf_f <= 1.0):
            raise ValueError(
                f"max_memory_fraction must lie in [0, 1], got "
                f"{max_mf_f!r}"
            )
        self._cycle_length = int(cycle_length)
        self._nfe_budget = int(nfe_budget)
        self._n_rounds = int(n_rounds)
        self._threshold = int(threshold)
        self._max_memory_fraction = max_mf_f
        self._seed = int(seed)
        # Compute the per-round ``memory_fraction`` once at construction
        # time — it depends only on ``nfe_budget`` / ``n_rounds`` /
        # ``threshold`` / ``max_memory_fraction``, not on ``r``.
        self._memory_fraction = float(self._compute_memory_fraction())
        self._n_cap = float(max(0.0, min(1.0, 1.0 - self._memory_fraction)))
        self._last_sample: ScheduleSample | None = None
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "nfe_aware_memory",
                "schedule_family": "nfe_aware_memory",
                "cycle_length": int(self._cycle_length),
                "nfe_budget": int(self._nfe_budget),
                "n_rounds": int(self._n_rounds),
                "threshold": int(self._threshold),
                "max_memory_fraction": float(self._max_memory_fraction),
                "seed": int(self._seed),
            }
        )

    def _compute_memory_fraction(self) -> float:
        """Return the closed-form ``m(r) = min(M, M * (NFE_per_round / T) ** 2)``.

        Pure function of the constructor inputs; kept private so callers
        cannot mutate the cached value through :meth:`memory_fraction`.
        """
        nfe_per_round = float(self._nfe_budget) / float(self._n_rounds)
        ratio = nfe_per_round / float(self._threshold)
        # ``ratio ** 2`` is finite for every finite ``ratio`` and never
        # produces a NaN; the ``min`` clamps to ``max_memory_fraction``
        # once the quadratic term exceeds it (saturated regime).
        m = float(self._max_memory_fraction) * ratio * ratio
        return float(min(self._max_memory_fraction, m))

    # -- accessors ---------------------------------------------------------

    @property
    def nfe_budget(self) -> int:
        """Return the configured TOTAL NFE budget for the cycle."""
        return int(self._nfe_budget)

    @property
    def n_rounds(self) -> int:
        """Return the configured number of restart rounds."""
        return int(self._n_rounds)

    @property
    def nfe_per_round(self) -> float:
        """Return the per-round NFE count (``nfe_budget / n_rounds``)."""
        return float(self._nfe_budget) / float(self._n_rounds)

    @property
    def threshold(self) -> int:
        """Return the NFE-per-round saturation threshold."""
        return int(self._threshold)

    @property
    def max_memory_fraction(self) -> float:
        """Return the configured saturation cap for ``memory_fraction``."""
        return float(self._max_memory_fraction)

    @property
    def memory_fraction(self) -> float:
        """Return the cached per-round ``memory_fraction`` (constant across ``r``)."""
        return float(self._memory_fraction)

    @property
    def n_cap(self) -> float:
        """Return ``1 - memory_fraction`` (the canonical capacity for the round)."""
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
        """Return the NFE-aware constant-capacity sample for one round.

        The returned :class:`ScheduleSample` carries the constant
        ``memory_fraction`` (and hence ``n_cap``) computed at
        construction time. The ``u_r`` field is filled with the round's
        progress fraction so downstream consumers can branch on round
        index without recomputing it; the schedule itself does not
        vary across rounds — only the ``family`` audit marker
        (``nfe_aware_memory_constant``) and the constructor-time
        ``memory_fraction`` propagate.
        """
        outer_cycle_id = _coerce_int_nonneg(outer_cycle_id, "outer_cycle_id")
        target_round = _coerce_int_nonneg(target_round, "target_round")
        length = int(self._cycle_length)
        if length > 1 and not (
            0 <= int(round_in_cycle) <= length - 1
        ):
            raise ValueError(
                f"round_in_cycle must be in [0, {length - 1}] for "
                f"cycle_length={length}, got {round_in_cycle!r}"
            )

        if length == 1:
            u_r = 0.5
        else:
            u_r = float(round_in_cycle) / (length - 1)

        codes: tuple[str, ...] = (
            "schedule_nfe_aware_memory",
            f"schedule_nfe_aware_memory:m={self._memory_fraction:.6f}",
            f"schedule_nfe_aware_memory:nfe_per_round={self.nfe_per_round:.4f}",
        )

        sample = ScheduleSample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=float(self._n_cap),
            n_min=float(self._n_cap),
            n_max=float(self._n_cap),
            u_r=u_r,
            family="nfe_aware_memory",
            computed_at_round=target_round,
            schedule_hash=str(self._config_hash_value),
            audit_codes=codes,
        )
        self._last_sample = sample
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length."""
        return int(self._cycle_length)

    def schedule_family(self) -> str:
        """Return the schedule family identifier."""
        return "nfe_aware_memory"

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
        """Default no-op: NFE-aware scheduler ignores per-round feedback."""
        return None

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return ``state + sqrt(n_cap) * generator.standard_normal`` (P0-7).

        Uses the schedule sample's ``n_cap`` directly. Since
        :class:`NFEAwareMemoryScheduler` produces a constant ``n_cap``
        per cycle, the noise mass is identical across every round — the
        forward-noise injection here mirrors the constant family
        (``state + sqrt(self._n_cap) * generator.standard_normal``).
        """
        state_arr = np.asarray(state, dtype=np.float64)
        n_cap = float(schedule_sample.n_cap)
        if n_cap < 0.0:
            n_cap = 0.0
        scale = math.sqrt(n_cap)
        noise = generator.standard_normal(state_arr.shape).astype(np.float64)
        return state_arr + scale * noise

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for the NFE-aware scheduler."""
        return {
            "family": "nfe_aware_memory",
            "cycle_length": int(self._cycle_length),
            "nfe_budget": int(self._nfe_budget),
            "n_rounds": int(self._n_rounds),
            "threshold": int(self._threshold),
            "max_memory_fraction": float(self._max_memory_fraction),
            "seed": int(self._seed),
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> NFEAwareMemoryScheduler:
        """Build an :class:`NFEAwareMemoryScheduler` from ``config`` (P1-1)."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return NFEAwareMemoryScheduler(
            cycle_length=int(config["cycle_length"]),
            nfe_budget=int(config["nfe_budget"]),
            n_rounds=int(config["n_rounds"]),
            threshold=int(config.get("threshold", DEFAULT_NFE_AWARE_THRESHOLD)),
            max_memory_fraction=float(
                config.get(
                    "max_memory_fraction", DEFAULT_NFE_AWARE_MAX
                )
            ),
            seed=int(config.get("seed", 0)),
        )

    # -- derived -----------------------------------------------------------

    def memory_fraction_for(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> float:
        """Return the (constant) cached ``memory_fraction`` for any round."""
        return float(self._memory_fraction)


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
    # Wave 61 Agent 2 — smooth NFE-aware memory_fraction scaling
    # (Wave 57 Agent D's B2 / successor to Wave 58 Agent 1's binary gate).
    "nfe_aware_memory": NFEAwareMemoryScheduler,
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
    if key == "nfe_aware_memory":
        return NFEAwareMemoryScheduler.from_config(config)
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
    eps_implicit: float | None = None,
    t: float | None = None,
    c_g: float | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
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
    # Lazy import: ``adaptive_reflow.algorithm._derivation`` triggers a
    # partial-import cycle if loaded at module top (see the module-level
    # NOTE above). Defer the lookup until this entry point runs so the
    # ``OTEpsilonSchedule`` default on the next line resolves at call time.
    from adaptive_reflow.algorithm._derivation import (
        OTEpsilonSchedule,
        make_derivation_context,
    )
    from adaptive_reflow.algorithm._derivation import (
        default_eps_implicit as _default_eps_implicit,
    )
    chosen: DerivationRule = (
        rule if rule is not None else OTEpsilonSchedule()
    )
    # Build a context from the scalar kwargs when the caller did not
    # supply one. This mirrors the ``derive_default_memory_fraction``
    # pattern in ``blender_extra.py``: the entry point is a thin
    # wrapper that promotes caller-side scalars into a
    # DerivationContext when one is missing.
    if context is None:
        context = make_derivation_context(
            eps_implicit=eps_implicit,
            t=t,
            c_g=c_g,
        )
    return float(
        _default_eps_implicit(
            context, eps_implicit=eps_implicit, rule=chosen
        )
    )


# ---------------------------------------------------------------------------
# Parameter-free scheduler hyperparameter entry points (DERIV-001 P-19)
# ---------------------------------------------------------------------------


def derive_default_exponential_alpha(
    *,
    n_min: float | None = None,
    n_max: float | None = None,
    cycle_length: int | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
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
    cycle_length: int | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
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
    n_min: float | None = None,
    n_max: float | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
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
    fisher_information: float | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
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
    w2_history: tuple[float, ...] | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.kp`` from a derivation rule."""
    from adaptive_reflow.algorithm._derivation import (
        default_convergence_adaptive_kp as _d,
    )
    return _d(context, w2_history=w2_history, rule=rule)


def derive_default_convergence_adaptive_kd(
    *,
    w2_history: tuple[float, ...] | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.kd`` from a derivation rule."""
    from adaptive_reflow.algorithm._derivation import (
        default_convergence_adaptive_kd as _d,
    )
    return _d(context, w2_history=w2_history, rule=rule)


def derive_default_convergence_adaptive_shift_max(
    *,
    w2_history: tuple[float, ...] | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.shift_max`` from a derivation rule."""
    from adaptive_reflow.algorithm._derivation import (
        default_convergence_adaptive_shift_max as _d,
    )
    return _d(context, w2_history=w2_history, rule=rule)


def derive_default_convergence_adaptive_ema(
    *,
    cycle_length: int | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.ema`` from a derivation rule."""
    from adaptive_reflow.algorithm._derivation import (
        default_convergence_adaptive_ema as _d,
    )
    return _d(context, cycle_length=cycle_length, rule=rule)


def derive_default_metric_weights(
    *,
    metric_variances: Mapping[str, tuple[float, ...]] | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
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
    "DEFAULT_NFE_AWARE_MAX",
    "DEFAULT_NFE_AWARE_THRESHOLD",
    "NFEAwareMemoryScheduler",
    "SCHEDULER_REGISTRY",
    "_EXTRA_FAMILIES_REGISTERED",
    "_codimension_sheet_factory",
    "_ensure_extra_families_registered",
    "_register_extra_scheduler_families",
    "_sequential_factory",
    "build_scheduler",
    "build_scheduler_from_config",
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

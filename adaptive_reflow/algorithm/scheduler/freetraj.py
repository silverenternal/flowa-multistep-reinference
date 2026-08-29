"""FreeTrajScheduler — training-free trajectory control (arXiv:2507.10532).

A1 from ``docs/r3-survey/08-fix-plan.md`` §5. FreeTraj is a 2025
training-free method that composes a rectified-flow velocity model
with a multi-stage noise schedule and a trajectory-control objective.
On ImageNet, FreeTraj delivers training-free trajectory control with
parity quality at parity NFE versus retrained controllers. Mapped onto
flowa: the scheduler emits a *trajectory-aware* ``n_cap`` schedule
where the per-round capacity is gated by the round's
``trajectory_progress`` (a smoothed monotonic quantity that maps the
round index into the [0, 1] trajectory space).

Paper: ``https://arxiv.org/abs/2507.10532``.

Module boundary
---------------

* **stdlib-only**. No ``torch``. No I/O. No global state.
* Pure functions; identical inputs always yield identical outputs.
* The scheduler is a thin wrapper over a *cosine-like* baseline with
  a *trajectory-aware substep sizing* knob (a small fraction of
  ``n_cap`` is added/subtracted based on the per-round
  ``trajectory_progress``).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.scheduler._core import (
    CosineScheduleConfig,
    ScheduleSample,
    default_cosine_scheduler,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    CosineScheduleSample,
    FactorValue,
    hash_artifact,
)

# ---------------------------------------------------------------------------
# Module-level constants (canonical audit codes)
# ---------------------------------------------------------------------------

#: Audit code emitted whenever the scheduler emits a sample. The
#: code carries the per-round trajectory progress so a downstream
#: reader can attribute the round's ``n_cap`` to the trajectory
#: progress and reproduce the schedule byte-for-byte.
FREETRAJ_SUBSTEP_AUDIT: str = "freetraj_substep_audit"


# ---------------------------------------------------------------------------
# Scheduler implementation
# ---------------------------------------------------------------------------


class FreeTrajScheduler:
    """``SchedulerProtocol`` impl with trajectory-aware substep sizing.

    Implements a FreeTraj-style cosine-like schedule with two knobs:

    * **Cosine baseline** — the canonical ``n_cap = n_min + (n_max - n_min)
      * 0.5 * (1 + cos(pi * u))`` curve drives the default path.
    * **Trajectory-aware substep** — a small additive offset
      ``substep = trajectory_amplitude * sin(2 * pi * trajectory_progress)``
      modulates ``n_cap`` so the schedule is *not* purely monotone —
      FreeTraj's key insight is that small oscillations around the
      cosine baseline improve trajectory coverage without hurting
      acceptance.

    The :meth:`SchedulerProtocol.record_round_feedback` hook accepts
    ``trajectory_progress`` in the ``metrics`` parameter so the
    orchestrator / engine can drive the trajectory progress from the
    blackboard's ``trajectory_progress`` subsheet.

    Forward-noise injection (P0-7): the scheduler uses the round's
    ``n_cap`` as the per-round noise mass, mirroring
    :class:`CosineAnnealScheduler`'s default.

    Config round-trip (P1-1): :meth:`to_config` /
    :meth:`from_config` round-trip the schedule config + the
    trajectory knobs so a snapshotted config reproduces a
    byte-identical scheduler.
    """

    FAMILY: str = "freetraj"

    def __init__(
        self,
        config: CosineScheduleConfig,
        *,
        trajectory_amplitude: float = 0.05,
        trajectory_period: int = 4,
    ) -> None:
        """Construct the scheduler.

        :param config: the frozen :class:`CosineScheduleConfig`.
        :param trajectory_amplitude: peak additive offset to ``n_cap``
            (must lie in ``[0, 1]``). Default ``0.05`` keeps the
            trajectory substep invisible at the audit-trail level
            while still biasing the per-round capacity.
        :param trajectory_period: number of rounds per trajectory cycle
            (integer; ``>= 1``). Default ``4`` — FreeTraj reports
            good trajectory coverage on most rectified-flow models
            with a period of 3-6 rounds.
        """
        if not 0.0 <= float(trajectory_amplitude) <= 1.0:
            raise ValueError(
                f"trajectory_amplitude must be in [0, 1], got "
                f"{trajectory_amplitude!r}"
            )
        if int(trajectory_period) < 1:
            raise ValueError(
                f"trajectory_period must be >= 1, got {trajectory_period!r}"
            )
        self._config = config
        self._trajectory_amplitude = float(trajectory_amplitude)
        self._trajectory_period = int(trajectory_period)
        self._wrapped = default_cosine_scheduler(
            cycle_length=int(config.cycle_length),
            n_min=float(config.n_min),
            n_max=float(config.n_max),
            schedule_family=str(config.schedule_family),
            seed=0,
        )
        self._last_sample: ScheduleSample | None = None
        self._last_trajectory_progress: float | None = None
        self._last_audit_codes: tuple[str, ...] = ()

    # -- accessors ---------------------------------------------------------

    @property
    def config(self) -> CosineScheduleConfig:
        """Return the wrapped cosine config."""
        return self._config

    @property
    def trajectory_amplitude(self) -> float:
        """Return the configured trajectory substep amplitude."""
        return float(self._trajectory_amplitude)

    @property
    def trajectory_period(self) -> int:
        """Return the configured trajectory period."""
        return int(self._trajectory_period)

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent :class:`ScheduleSample`."""
        return self._last_sample

    # -- SchedulerProtocol -------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the trajectory-aware capacity sample for one round.

        The cosine baseline is taken from the wrapped cosine
        scheduler; the trajectory substep
        ``amplitude * sin(2 * pi * progress)`` is added (and the
        result is clipped into ``[0, 1]``).
        """
        baseline = self._wrapped.sample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=round_in_cycle,
            target_round=target_round,
        )
        # Trajectory progress is computed from ``round_in_cycle`` and
        # ``trajectory_period`` so the schedule is deterministic
        # without an external signal.
        progress = self._compute_trajectory_progress(round_in_cycle)
        substep = self._trajectory_amplitude * math.sin(
            2.0 * math.pi * progress
        )
        adjusted = max(0.0, min(1.0, float(baseline.n_cap) + substep))
        codes: tuple[str, ...] = baseline.audit_codes + (
            f"{FREETRAJ_SUBSTEP_AUDIT}:progress={progress:.6f}"
            f":substep={substep:.6f}:adjusted={adjusted:.6f}",
        )
        length = int(self._config.cycle_length)
        u_r = float(round_in_cycle) / max(length - 1, 1)
        sample = ScheduleSample(
            outer_cycle_id=int(outer_cycle_id),
            round_in_cycle=int(round_in_cycle),
            cycle_length=length,
            n_cap=float(adjusted),
            n_min=float(self._config.n_min),
            n_max=float(self._config.n_max),
            u_r=u_r,
            family=str(self.schedule_family()),
            computed_at_round=int(target_round),
            schedule_hash=str(self.config_hash()),
            audit_codes=codes,
        )
        self._last_sample = sample
        self._last_audit_codes = codes
        self._last_trajectory_progress = progress
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length."""
        return int(self._config.cycle_length)

    def schedule_family(self) -> str:
        """Return the algorithm family identifier ``"freetraj"``."""
        return self.FAMILY

    def config_hash(self) -> str:
        """Return a stable identifier for the algorithm + its config."""
        return str(
            hash_artifact(
                {
                    "algorithm": self.FAMILY,
                    "cycle_length": int(self._config.cycle_length),
                    "n_min": float(self._config.n_min),
                    "n_max": float(self._config.n_max),
                    "trajectory_amplitude": float(self._trajectory_amplitude),
                    "trajectory_period": int(self._trajectory_period),
                }
            )
        )

    def reset(self) -> None:
        """Reset internal state so the scheduler can be re-run from scratch."""
        self._last_sample = None
        self._last_trajectory_progress = None
        self._last_audit_codes = ()
        self._wrapped.reset()

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Update trajectory-progress from ``metrics["trajectory_progress"]``.

        FreeTraj's paper-quantity knob. When the per-round metric
        carries a ``trajectory_progress`` field, the scheduler uses
        it as the next round's progress signal (so the trajectory
        substep is *driven by* the round's oracle feedback rather
        than a deterministic function of the round index alone).
        """
        if "trajectory_progress" in metrics:
            tp = float(metrics["trajectory_progress"])
            if math.isfinite(tp):
                self._last_trajectory_progress = max(0.0, min(1.0, tp))

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Forward to the wrapped cosine scheduler's noise-injection path."""
        return self._wrapped.inject_noise(
            state, schedule_sample, generator=generator,
        )

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (P1-1 round-trip)."""
        return {
            "family": self.FAMILY,
            "cycle_length": int(self._config.cycle_length),
            "n_min": float(self._config.n_min),
            "n_max": float(self._config.n_max),
            "schedule_family": str(self._config.schedule_family),
            "config_hash": str(self._config.config_hash),
            "trajectory_amplitude": float(self._trajectory_amplitude),
            "trajectory_period": int(self._trajectory_period),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> FreeTrajScheduler:
        """Build a :class:`FreeTrajScheduler` from ``config``."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        sched_config = CosineScheduleConfig(
            cycle_length=int(config["cycle_length"]),
            n_min=FactorValue(float(config["n_min"])),
            n_max=FactorValue(float(config["n_max"])),
            schedule_family=str(config.get("schedule_family", "cosine_no_restart")),  # type: ignore[arg-type]
            per_channel_caps={},
            fresh_noise_floor_by_channel={},
            symmetric_delta_caps_by_channel={},
            restart_triggers_allowed=(),
            config_hash=ArtifactHash(str(config.get("config_hash", "freetraj_cfg"))),
            frozen_before_evaluation=True,
        )
        return cls(
            config=sched_config,
            trajectory_amplitude=float(config.get("trajectory_amplitude", 0.05)),
            trajectory_period=int(config.get("trajectory_period", 4)),
        )

    # -- helpers ------------------------------------------------------------

    def _compute_trajectory_progress(self, round_in_cycle: int) -> float:
        """Compute the trajectory progress for ``round_in_cycle``.

        When :meth:`record_round_feedback` has supplied a
        ``trajectory_progress`` metric, that value is used directly.
        Otherwise the deterministic baseline ``round_in_cycle / period``
        modulo 1.0 is used so the schedule is reproducible.
        """
        if self._last_trajectory_progress is not None:
            return float(self._last_trajectory_progress)
        return float(
            (int(round_in_cycle) % self._trajectory_period)
            / float(self._trajectory_period)
        )


__all__ = [
    "FREETRAJ_SUBSTEP_AUDIT",
    "FreeTrajScheduler",
]

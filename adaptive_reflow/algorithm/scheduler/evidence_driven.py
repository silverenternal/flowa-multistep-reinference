"""EvidenceDrivenScheduler — closes Loop 2 of the documented feedback loops.

C4 from ``docs/r3-survey/08-fix-plan.md`` §4. The framework advertises
four feedback loops but Loop 2 (paper-quantities → scheduler feedback)
is half-closed: per-round ``selection_ratio`` /
``paper_quantity_diagnostics`` /
``schedule_evidence_ratio`` metrics are observation-only and never
reach the scheduler's :meth:`SchedulerProtocol.record_round_feedback`
on the canonical cosine path. This module ships a SchedulerProtocol
implementation that *does* consume the evidence ratio and updates the
``n_cap`` schedule via a PID-lite controller.

Paper context (MeanFlow / FreeTraj / Black-box-VI surveys in
``docs/r3-survey/07-frontier-collaboration.md``):

* the controller is "PID-lite" — a proportional correction with a small
  integral term and no derivative (the derivative is noise-sensitive on
  single-round oracle signals);
* the controlled quantity is ``n_cap`` (the per-round capacity the
  scheduler emits) rather than ``beta`` (the policy driver's quantity);
* the controller subscribes to the blackboard's
  ``evidence_ratio`` subsheet (per C1 in
  ``docs/r3-survey/06-frontier-decoupling.md``) — for unit-test
  isolation this is parameterised as a per-call ``evidence_ratio`` in
  the ``metric`` dict rather than a hard blackboard reference.

C4 uplift (``docs/r3-survey/09-c4-investigation.md``): in addition to
the ``n_cap`` offset, the scheduler now propagates a per-round
``eps_implicit`` adjustment onto the emitted ``ScheduleSample`` so
the runner can thread it into the
:class:`PosteriorSelectionEvaluator` (``oracle_at_round(eps_round=...)``).
The PID controller is unchanged — only the destination of its delta
is split between ``n_cap`` (legacy ``_last_pid_delta``) and
``eps_implicit`` (new ``_last_eps_delta``). A small ``k_eps`` gain
(default ``0.5``) maps the PID's raw adjustment onto the epsilon
scale; paper Theorem 1 predicts the ratio rises toward 1 as
``eps -> 0``, so the epsilon delta is the *negation* of the n_cap
delta (positive ``error`` => lower ``eps`` to drive ratio toward 1).

Module boundary
---------------

* **stdlib-only**. No ``torch``. No I/O. No global state beyond the
  per-instance PID controller.
* The scheduler is a value-object surface: every mutator returns
  ``self`` (or ``None`` for the no-op cases) and the ``metric``
  argument is treated as read-only.
* The default :class:`CosineAnnealScheduler` math drives the *baseline*
  ``n_cap``; the controller only adjusts the *offset* by a small
  amount (``|delta| <= max_step``).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.scheduler._core import (
    CosineScheduleConfig,
    SchedulerProtocol,
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

#: Audit code emitted whenever the PID-lite controller produces a
#: non-zero ``n_cap`` adjustment for a round. The code carries the
#: delta value so a downstream audit reader can see exactly how much
#: the evidence ratio moved the schedule off the cosine baseline.
EVIDENCE_PID_ADJUSTED: str = "evidence_pid_adjusted"

#: Audit code emitted when the PID-lite adjustment was clipped to
#: ``max_step`` (i.e. the controller wanted to move ``n_cap`` by more
#: than the per-round step cap). The code carries the requested and
#: applied deltas so a downstream reader can see the saturation.
EVIDENCE_PID_SATURATED: str = "evidence_pid_saturated"

#: Audit code emitted when ``evidence_ratio`` is missing from the
#: per-round metrics dict. The controller treats ``ratio = 0.5``
#: (neutral) and emits this code so a reader can distinguish the
#: "no signal" case from the "ratio present" case.
EVIDENCE_RATIO_MISSING: str = "evidence_ratio_missing"


# ---------------------------------------------------------------------------
# Internal PID-lite controller (proportional + integral; no derivative)
# ---------------------------------------------------------------------------


class _PIDLiteController:
    """Proportional + integral controller for ``n_cap`` adjustments.

    The controller's *control error* is ``target_ratio - observed_ratio``
    (with ``target_ratio = 1.0`` by default — the paper's evidence
    ordering claims the sheet evidence dominates as ``eps -> 0``).
    The controller output ``delta_n_cap`` is

        delta = Kp * error + Ki * integral_error

    with optional clamping into ``[-max_step, +max_step]``.

    Parameters
    ----------
    kp:
        Proportional gain. Default ``0.2`` — moves ``n_cap`` by ``0.2``
        of the error magnitude per round (a one-step correction of
        0.2 for a fully-wrong ``error=1.0`` signal).
    ki:
        Integral gain. Default ``0.05`` — accumulates the long-term
        offset so a sustained error does not just produce a
        steady-state offset (steady-state error from pure-P control).
    max_step:
        Per-round cap on ``|delta|``. Default ``0.05`` — keeps the
        controller from making large jumps on noisy single-round
        signals.
    target_ratio:
        The control set-point. Default ``1.0`` (the paper's evidence
        ratio target per Theorem 1). Custom set-points are exposed
        for experiments; the framework's canonical config uses
        ``1.0``.
    """

    __slots__ = ("_integral", "ki", "kp", "max_step", "target_ratio")

    def __init__(
        self,
        *,
        kp: float = 0.2,
        ki: float = 0.05,
        max_step: float = 0.05,
        target_ratio: float = 1.0,
    ) -> None:
        self.kp = float(kp)
        self.ki = float(ki)
        self.max_step = float(max_step)
        self.target_ratio = float(target_ratio)
        self._integral: float = 0.0

    def reset(self) -> None:
        """Reset the integral accumulator (called on scheduler ``reset()``)."""
        self._integral = 0.0

    def step(
        self,
        observed_ratio: float,
        audit_codes: list[str] | None = None,
    ) -> tuple[float, bool]:
        """Compute one PID-lite step.

        Returns ``(delta_n_cap, was_saturated)``. ``delta_n_cap`` is
        the per-round adjustment to add to the cosine-derived
        baseline ``n_cap``. ``was_saturated`` is ``True`` when the
        requested delta was clamped into ``[-max_step, +max_step]``.
        """
        error = float(self.target_ratio) - float(observed_ratio)
        # Anti-windup: cap the integral so a single bad round cannot
        # permanently move ``n_cap`` off the cosine baseline.
        self._integral = max(-10.0, min(10.0, self._integral + error))
        raw = float(self.kp) * error + float(self.ki) * self._integral
        saturated = abs(raw) > float(self.max_step)
        applied = max(-float(self.max_step), min(float(self.max_step), raw))
        if audit_codes is not None:
            audit_codes.append(
                f"{EVIDENCE_PID_ADJUSTED}:delta={applied:.6f}:raw={raw:.6f}"
            )
            if saturated:
                audit_codes.append(
                    f"{EVIDENCE_PID_SATURATED}"
                    f":requested={raw:.6f}:applied={applied:.6f}"
                )
        return applied, saturated


# ---------------------------------------------------------------------------
# Scheduler implementation
# ---------------------------------------------------------------------------


class EvidenceDrivenScheduler:
    """``SchedulerProtocol`` impl that adapts ``n_cap`` via PID-lite.

    Wraps a :class:`CosineAnnealScheduler` (or any callable that maps
    ``(cycle_length, n_min, n_max)`` to a per-round ``n_cap``) and
    adjusts the cosine-derived ``n_cap`` by a small PID-lite step
    driven by the per-round ``evidence_ratio``.

    The scheduler is *not* a replacement for the canonical cosine
    path; it is a *companion* that takes the cosine baseline and adds
    an evidence-driven offset. Callers that want pure cosine behaviour
    continue to use :class:`CosineAnnealScheduler` directly.

    Forward-noise injection (P0-7): the scheduler delegates to the
    wrapped cosine scheduler's :meth:`inject_noise` so the byte-exact
    noise injection path is preserved.

    Config round-trip (P1-1): :meth:`to_config` /
    :meth:`from_config` round-trip the cosine schedule config + the
    PID gains / target so a snapshotted config reproduces a
    byte-identical scheduler.
    """

    FAMILY: str = "evidence_driven"

    def __init__(
        self,
        config: CosineScheduleConfig,
        *,
        profile_residual_fn: Any | None = None,
        kp: float = 0.2,
        ki: float = 0.05,
        max_step: float = 0.05,
        target_ratio: float = 1.0,
        k_eps: float = 0.5,
        eps_implicit_base: float | None = None,
    ) -> None:
        """Construct the scheduler.

        :param config: the frozen :class:`CosineScheduleConfig` driving
            the cosine baseline.
        :param profile_residual_fn: optional residual profile forwarded
            to the wrapped cosine scheduler.
        :param kp: proportional gain (PID-lite).
        :param ki: integral gain (PID-lite).
        :param max_step: per-round step cap on ``|delta_n_cap|``.
        :param target_ratio: PID-lite set-point for ``evidence_ratio``.
        :param k_eps: C4 uplift — gain mapping the PID's raw delta onto
            the per-round ``eps_implicit`` adjustment. Default ``0.5``.
            The ``eps`` delta is ``-delta * k_eps`` (paper Theorem 1
            predicts ratio rises as ``eps -> 0``, so positive
            ``error`` => lower ``eps``).
        :param eps_implicit_base: C4 uplift — the baseline ``eps`` value
            the PID modulates around. ``None`` (default) means "no
            ``eps_implicit`` carried"; the runner will see
            ``sample.eps_implicit is None`` and the evaluator will fall
            back to its fixed ``eps_implicit``. When supplied, the
            scheduler emits
            ``ScheduleSample.eps_implicit = max(1e-6, eps_implicit_base + accumulated_delta)``
            and the runner threads it into the selection evaluator.
        """
        self._config = config
        self._sheet_A: float | None = None
        self._wrapped = default_cosine_scheduler(
            cycle_length=int(config.cycle_length),
            n_min=float(config.n_min),
            n_max=float(config.n_max),
            schedule_family=str(config.schedule_family),
            seed=0,
        )
        self._controller = _PIDLiteController(
            kp=kp, ki=ki, max_step=max_step, target_ratio=target_ratio,
        )
        self._last_sample: ScheduleSample | None = None
        self._last_audit_codes: tuple[str, ...] = ()
        self._last_pid_delta: float = 0.0
        # C4 uplift: parallel ``_last_eps_delta`` that the runner
        # propagates to the selection evaluator via
        # ``ScheduleSample.eps_implicit``. ``_k_eps`` is the gain
        # mapping the PID's raw delta onto the epsilon scale; the
        # epsilon delta is the *negation* of the n_cap delta (paper
        # Theorem 1 says the ratio rises as ``eps -> 0``). When
        # ``_eps_implicit_base`` is ``None`` the field stays ``None``
        # and the runner falls back to the evaluator's fixed
        # ``eps_implicit`` — preserving byte-for-byte backward
        # compatibility for callers that don't construct with
        # ``eps_implicit_base``.
        self._last_eps_delta: float = 0.0
        self._k_eps: float = float(k_eps)
        self._eps_implicit_base: float | None = (
            float(eps_implicit_base) if eps_implicit_base is not None else None
        )
        # Forward the profile so paper-quantity augmentation works.
        if profile_residual_fn is not None:
            from adaptive_reflow.algorithm.scheduler._core import CosineAnnealScheduler
            from adaptive_reflow.contracts import paper_quantities as _pq

            self._wrapped = CosineAnnealScheduler(
                config=config, profile_residual_fn=profile_residual_fn,
            )
            self._sheet_A = float(_pq.sheet_evidence_A(profile_residual_fn))
        else:
            self._sheet_A = None

    # -- accessors ---------------------------------------------------------

    @property
    def config(self) -> CosineScheduleConfig:
        """Return the wrapped cosine config."""
        return self._config

    @property
    def controller(self) -> _PIDLiteController:
        """Return the PID-lite controller (exposed for tests)."""
        return self._controller

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
        """Return the cosine-annealed capacity sample, plus PID offset.

        The PID-lite controller is consulted *eagerly* on each call to
        :meth:`sample` with the most recent ``evidence_ratio`` observed
        via :meth:`record_round_feedback`. The PID's ``delta_n_cap`` is
        added to the cosine baseline (and clipped into ``[0, 1]``).

        C4 uplift: when the scheduler was constructed with
        ``eps_implicit_base`` set, the parallel ``_last_eps_delta``
        (computed in :meth:`record_round_feedback`) is applied to
        produce ``ScheduleSample.eps_implicit``. The runner reads this
        field and threads it into the selection evaluator as
        ``eps_round``. When ``eps_implicit_base`` was ``None`` (the
        default), ``ScheduleSample.eps_implicit`` stays ``None`` and
        the runner falls back to the evaluator's fixed ``eps_implicit``
        — preserving byte-for-byte backward compatibility.
        """
        baseline = self._wrapped.sample(
            outer_cycle_id=outer_cycle_id,
            round_in_cycle=round_in_cycle,
            target_round=target_round,
        )
        # The PID adjustment was computed on the previous round's
        # evidence; carry it into this round's sample.
        delta = self._last_pid_delta
        adjusted = max(0.0, min(1.0, float(baseline.n_cap) + delta))
        # C4 uplift: compute the per-round ``eps_implicit`` if the
        # scheduler was constructed with a baseline. The PID's
        # ``_last_eps_delta`` is the negation of the n_cap delta
        # scaled by ``k_eps`` (paper Theorem 1 says ratio rises as
        # ``eps -> 0``, so a positive ``error`` lowers ``eps``).
        # Floor at ``1e-6`` so the downstream metric never receives
        # a non-positive eps.
        eps_implicit_for_sample: float | None = None
        eps_implicit_base_local: float | None = self._eps_implicit_base
        if eps_implicit_base_local is not None:
            eps_implicit_for_sample = max(
                1e-6,
                float(eps_implicit_base_local) + float(self._last_eps_delta),
            )
        # Re-derive u_r from the *adjusted* n_cap so the schedule_hash
        # captures the evidence-driven offset (callers that want to
        # replay a round can recover the offset from the audit codes).
        length = int(self._config.cycle_length)
        u_r = float(round_in_cycle) / max(length - 1, 1)
        codes: tuple[str, ...] = baseline.audit_codes + (
            f"evidence_driven_n_cap:baseline={float(baseline.n_cap):.6f}"
            f":delta={delta:.6f}:adjusted={adjusted:.6f}",
        )
        if eps_implicit_for_sample is not None and eps_implicit_base_local is not None:
            codes = codes + (
                f"evidence_driven_eps:base={float(eps_implicit_base_local):.6f}"
                f":delta={float(self._last_eps_delta):.6f}"
                f":adjusted={float(eps_implicit_for_sample):.6f}",
            )
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
            eps_implicit=eps_implicit_for_sample,
        )
        self._last_sample = sample
        self._last_audit_codes = codes
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length."""
        return int(self._config.cycle_length)

    def schedule_family(self) -> str:
        """Return the algorithm family identifier ``"evidence_driven"``."""
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
                    "kp": float(self._controller.kp),
                    "ki": float(self._controller.ki),
                    "max_step": float(self._controller.max_step),
                    "target_ratio": float(self._controller.target_ratio),
                }
            )
        )

    def reset(self) -> None:
        """Reset internal state so the scheduler can be re-run from scratch."""
        self._last_sample = None
        self._last_audit_codes = ()
        self._last_pid_delta = 0.0
        # C4 uplift: reset the parallel ``_last_eps_delta`` accumulator.
        self._last_eps_delta = 0.0
        self._controller.reset()
        self._wrapped.reset()

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Apply the PID-lite step using ``metrics["evidence_ratio"]``.

        Falls back to ``ratio = 0.5`` (the neutral midpoint) when
        ``evidence_ratio`` is absent; emits
        :data:`EVIDENCE_RATIO_MISSING` so the audit trail can
        distinguish the no-signal case from the explicit-signal case.

        C4 uplift: when the scheduler was constructed with
        ``eps_implicit_base``, the same PID controller output is
        mapped onto the ``_last_eps_delta`` accumulator via the
        ``_k_eps`` gain (negated — paper Theorem 1 says ratio rises
        as ``eps -> 0``). The next :meth:`sample` adds the delta to
        ``_eps_implicit_base`` and emits
        ``ScheduleSample.eps_implicit``.
        """
        if "evidence_ratio" in metrics:
            ratio = float(metrics["evidence_ratio"])
        elif "selection_ratio" in metrics:
            # Heuristic proxy (per F12 in
            # ``docs/r3-survey/05-verified-findings.md``).
            ratio = float(metrics["selection_ratio"])
        else:
            ratio = 0.5
            if "evidence_ratio_missing" not in self._last_audit_codes:
                # Append-once: avoid spamming on every round.
                self._last_audit_codes = self._last_audit_codes + (
                    EVIDENCE_RATIO_MISSING,
                )
        codes: list[str] = []
        delta, _saturated = self._controller.step(ratio, audit_codes=codes)
        self._last_pid_delta = delta
        # C4 uplift: split the PID's delta between ``n_cap`` (the
        # legacy destination) and ``eps_implicit`` (the C4 path).
        # Paper Theorem 1: ratio rises as ``eps -> 0`` => positive
        # ``error`` => lower ``eps``. The integral term is included
        # implicitly via the controller (it sums into ``delta``).
        if self._eps_implicit_base is not None:
            self._last_eps_delta = -float(delta) * float(self._k_eps)
        self._last_audit_codes = self._last_audit_codes + tuple(codes)

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
        out: dict[str, Any] = {
            "family": self.FAMILY,
            "cycle_length": int(self._config.cycle_length),
            "n_min": float(self._config.n_min),
            "n_max": float(self._config.n_max),
            "schedule_family": str(self._config.schedule_family),
            "config_hash": str(self._config.config_hash),
            "kp": float(self._controller.kp),
            "ki": float(self._controller.ki),
            "max_step": float(self._controller.max_step),
            "target_ratio": float(self._controller.target_ratio),
            # C4 uplift: round-trip the ``k_eps`` gain and the
            # ``eps_implicit_base`` so the C4 fix is reproducible.
            "k_eps": float(self._k_eps),
        }
        if self._eps_implicit_base is not None:
            out["eps_implicit_base"] = float(self._eps_implicit_base)
        return out

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> EvidenceDrivenScheduler:
        """Build an :class:`EvidenceDrivenScheduler` from ``config``."""
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
            config_hash=ArtifactHash(str(config.get("config_hash", "evid_cfg"))),
            frozen_before_evaluation=True,
        )
        eps_base_raw = config.get("eps_implicit_base")
        eps_base: float | None = (
            None if eps_base_raw is None else float(eps_base_raw)
        )
        return cls(
            config=sched_config,
            kp=float(config.get("kp", 0.2)),
            ki=float(config.get("ki", 0.05)),
            max_step=float(config.get("max_step", 0.05)),
            target_ratio=float(config.get("target_ratio", 1.0)),
            k_eps=float(config.get("k_eps", 0.5)),
            eps_implicit_base=eps_base,
        )


__all__ = [
    "EVIDENCE_PID_ADJUSTED",
    "EVIDENCE_PID_SATURATED",
    "EVIDENCE_RATIO_MISSING",
    "EvidenceDrivenScheduler",
]


# Defensive: silence unused-import linters for symbols used in
# type-only contexts.
_ = (math, Mapping)

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

import logging
import math
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm.scheduler._core import (
    CosineScheduleConfig,
    SchedulerProtocol,
    ScheduleSample,
    default_cosine_scheduler,
)
from adaptive_reflow.algorithm.scheduler.regime_selector import (
    DEFAULT_REGIME_SLACK,
    RegimeAwareEpsSelector,
    RegimeSelection,
    build_regime_selector,
    default_e_rho_provider,
)
from adaptive_reflow.contracts import (
    ArtifactHash,
    CosineScheduleSample,
    FactorValue,
    RegimeGate,
    hash_artifact,
)

#: Module logger — the "scheduler log" the Lemma 4 regime warnings are
#: emitted to (in addition to the in-memory
#: :meth:`EvidenceDrivenScheduler.regime_violation_warnings` log, which
#: is what tests and audit readers consume).
_LOGGER = logging.getLogger(__name__)


#: Sentinel used by :class:`EvidenceDrivenScheduler.__init__` to detect
#: "the caller did not supply this argument" versus "the caller passed
#: the default value". Required because Python's keyword-argument
#: semantics cannot otherwise distinguish ``regime_aware=False`` (an
#: explicit choice) from the inert default.
_UNSET: Any = object()

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

#: Audit code prefix emitted on every regime-aware round, carrying the
#: pre-clamp ``eps`` request, the Lemma 4 ceiling and the applied
#: value. The per-outcome codes (``eps_regime_ok`` /
#: ``eps_regime_clamped`` / ``eps_regime_infeasible``) come from
#: :mod:`adaptive_reflow.algorithm.scheduler.regime_selector` and are
#: appended verbatim, so an audit reader sees both the scheduler's view
#: and the selector's.
EVIDENCE_REGIME_GATED: str = "evidence_driven_eps_regime"

#: Warning tag pushed onto
#: :meth:`EvidenceDrivenScheduler.regime_violation_warnings` (and the
#: module logger) whenever the Lemma 4 regime would have been violated.
REGIME_VIOLATION_WARNING: str = "regime_violation_warning"


# ---------------------------------------------------------------------------
# Internal PID-lite controller (proportional + integral; no derivative)
# ---------------------------------------------------------------------------


class _PIDLiteController:
    """Proportional + integral controller for ``n_cap`` adjustments.

    The controller's *control error* is ``target_ratio - observed_ratio``
    (with ``target_ratio = 0.99`` by default — below the paper's
    ``1.0`` asymptote because real ``evidence_ratio`` signals drift
    under ``1.0`` from cell-evidence variance). The controller output
    ``delta_n_cap`` is

        delta = Kp * error + Ki * integral_error

    with optional clamping into ``[-max_step, +max_step]``.

    .. note::
       **Signal amplification (Phase-3 / F-3 / F-32):** the original
       defaults (``kp=0.2``, ``ki=0.05``, ``max_step=0.05``,
       ``target_ratio=1.0``) produced ``|delta| < 0.012`` even when
       the oracle signal was at ``0.0`` — well below the cosine
       ramp's rounding threshold (``1 / max_num_steps ≈ 0.02`` for
       the canonical 50-NFE budget). The amplified defaults
       (``kp=2.0``, ``ki=0.5``, ``max_step=0.1``, ``target_ratio=0.99``)
       raise the worst-case |delta| to ``0.1``, which translates to
       a +5 NFE bump at the canonical 50-NFE max — enough to
       surface a measurable difference between the
       ``EvidenceDrivenScheduler`` row and the cosine baseline row.
       See ``docs/r4-survey/21-fix-v2-plan.md`` §3.4 for the design
       rationale.

    Parameters
    ----------
    kp:
        Proportional gain. Default ``2.0`` — moves ``n_cap`` by ``2.0``
        of the error magnitude per round (a one-step correction of
        ``1.0`` for a fully-wrong ``error=0.5`` signal). The high
        gain ensures the per-round delta lands above the rounding
        threshold of the cosine ramp.
    ki:
        Integral gain. Default ``0.5`` — accumulates the long-term
        offset so a sustained error does not just produce a
        steady-state offset (steady-state error from pure-P control).
    max_step:
        Per-round cap on ``|delta|``. Default ``0.1`` — guarantees the
        delta translates to at least ``round(0.1 * max_num_steps) = 5``
        NFE bump at the canonical 50-NFE max.
    target_ratio:
        The control set-point. Default ``0.99`` (the paper's
        ``Theorem 1`` evidence ratio target is ``1.0``; ``0.99`` is
        the operational asymptote that drives the PID into a
        measurable correction regime even when the proxy signal is
        constant at ``1.0``).
    """

    __slots__ = ("_integral", "ki", "kp", "max_step", "target_ratio")

    def __init__(
        self,
        *,
        kp: float = 2.0,
        ki: float = 0.5,
        max_step: float = 0.1,
        target_ratio: float = 0.99,
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
        kp: float = 2.0,
        ki: float = 0.5,
        max_step: float = 0.1,
        target_ratio: float = 0.99,
        k_eps: float = 0.5,
        eps_implicit_base: float | None = None,
        regime_aware: bool | Any = _UNSET,
        regime_selector: RegimeAwareEpsSelector | None = None,
        e_rho_provider: Callable[[float], float] | None = None,
        regime_slack: float | Any = _UNSET,
        regime_selector_family: str | Any = _UNSET,
        regime_gate: RegimeGate | None = None,
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
        :param regime_aware: Phase-4 / Design #3 — opt-in Lemma 4 regime
            enforcement. ``False`` (default) keeps the ``eps_implicit``
            path byte-identical to Phase 3: no selector is consulted,
            no extra audit codes are emitted, and ``config_hash`` /
            ``to_config`` are unchanged. ``True`` routes every round's
            PID-proposed ``eps`` through a
            :class:`~adaptive_reflow.algorithm.scheduler.regime_selector.RegimeAwareEpsSelector`
            so the emitted ``eps`` always satisfies
            ``eps^2 < e_rho / log 2`` (paper Lemma 4, line 110-113);
            a would-be violation is clamped to the ceiling and logged
            as a regime-violation warning. Has no effect when
            ``eps_implicit_base`` is ``None`` (there is no ``eps`` to
            gate).
        :param regime_selector: the concrete selector to consult when
            ``regime_aware`` is ``True``. ``None`` builds one from
            ``regime_selector_family``.
        :param e_rho_provider: maps a round index (as a float) to the
            exterior gap ``e_rho`` for that round. ``None`` with
            ``regime_aware=True`` falls back to
            :func:`~adaptive_reflow.contracts.paper_quantities.exterior_gap_e_rho`
            at its documented ``rho`` / ``eta`` defaults.
        :param regime_slack: strict-inequality slack subtracted from
            ``sqrt(e_rho / log 2)`` so the emitted ``eps`` satisfies
            Lemma 4's *strict* inequality in floating point.
        :param regime_selector_family: selector family to build when
            ``regime_selector`` is ``None`` (``"cosine_anneal"`` or
            ``"convergence_adaptive"``).
        :param regime_gate: optional :class:`RegimeGate` bundling
            ``regime_aware`` / ``e_rho_provider`` / ``slack`` /
            ``selector_family``. Explicitly-passed *non-default*
            keyword arguments win over the gate's fields, so the gate
            acts as a default carrier for config-driven construction.
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
        # P1-2 (F-3) — per-round PID delta history. The legacy
        # ``_last_pid_delta`` field has "one round stale" semantics:
        # the delta computed from round ``r``'s feedback is consumed
        # by round ``r+1``'s sample, leaving the recorded n_cap for
        # round ``r`` based on the *previous* round's feedback. To
        # close the loop without losing the existing
        # forward-propagation semantics, we now record per-round
        # deltas so the runner can amend round ``r``'s metric with
        # the delta derived from round ``r``'s own feedback (the
        # "non-stale" delta). The next ``sample()`` continues to
        # consume ``_last_pid_delta`` as before (legacy callers
        # observe no behavioural change).
        self._pid_delta_by_round: dict[int, float] = {}
        self._eps_delta_by_round: dict[int, float] = {}
        # ------------------------------------------------------------------
        # Phase-4 / Design #3 — Lemma 4 regime gate (opt-in).
        # ------------------------------------------------------------------
        # ``regime_aware=False`` (the default) leaves every field inert:
        # ``sample()`` skips the selector entirely, no audit code is
        # appended, and ``config_hash`` / ``to_config`` omit the regime
        # keys — so a Phase-3 caller gets byte-identical behaviour.
        # Explicit kwargs always win over the gate (the explicit-flag
        # sentinels distinguish "passed by the caller" from "still at
        # its Python default").
        if regime_gate is not None:
            # Sentinels let us detect "caller passed the literal default"
            # (e.g. ``regime_aware=False``) — explicit kwargs always win.
            if regime_aware is _UNSET:
                regime_aware = bool(regime_gate.regime_aware)
            if regime_slack is _UNSET:
                regime_slack = float(regime_gate.slack)
            if regime_selector_family is _UNSET:
                regime_selector_family = str(regime_gate.selector_family)
            if e_rho_provider is None:
                e_rho_provider = regime_gate.e_rho_provider
        if regime_aware is _UNSET:
            regime_aware = False
        if regime_slack is _UNSET:
            regime_slack = DEFAULT_REGIME_SLACK
        if regime_selector_family is _UNSET:
            regime_selector_family = "cosine_anneal"
        slack_f = float(regime_slack)
        if not math.isfinite(slack_f) or slack_f < 0.0:
            raise ValueError(
                f"regime_slack must be finite and >= 0, got {regime_slack!r}"
            )
        #: Public per :class:`RegimeAwareSchedulerProtocol` so a consumer
        #: can detect the gate structurally instead of by concrete type.
        self.regime_aware: bool = bool(regime_aware)
        self.e_rho_provider: Callable[[float], float] | None = e_rho_provider
        self._regime_slack: float = slack_f
        self._regime_selector_family: str = str(regime_selector_family)
        self._regime_selector: RegimeAwareEpsSelector | None = None
        if self.regime_aware:
            self._regime_selector = (
                regime_selector
                if regime_selector is not None
                else build_regime_selector(self._regime_selector_family)
            )
            if self.e_rho_provider is None:
                # Paper default: e_rho = min{rho^4, (1-rho)^2 eta^2} at
                # the documented rho / eta defaults (line 128).
                self.e_rho_provider = default_e_rho_provider()
        elif regime_selector is not None:
            raise ValueError(
                "regime_selector was supplied but regime_aware is False; "
                "pass regime_aware=True to enable the Lemma 4 clamp"
            )
        self._regime_warnings: list[str] = []
        self._last_regime_selection: RegimeSelection | None = None
        self._regime_selection_by_round: dict[int, RegimeSelection] = {}
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
        # Phase-4 / Design #3: consult the regime selector BEFORE the
        # eps is committed to the sample. The PID's proposal is the
        # *request*; the selector returns an ``eps`` guaranteed to sit
        # inside the Lemma 4 regime ``eps^2 < e_rho / log 2``. Inert
        # unless ``regime_aware=True`` AND an eps is actually carried.
        regime_selection: RegimeSelection | None = None
        if (
            self.regime_aware
            and self._regime_selector is not None
            and eps_implicit_for_sample is not None
        ):
            regime_selection = self._select_regime_eps(
                eps_implicit_for_sample,
                round_in_cycle=int(round_in_cycle),
                target_round=int(target_round),
            )
            eps_implicit_for_sample = float(regime_selection.eps_next)
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
        if regime_selection is not None:
            # Scheduler-side view first, then the selector's own codes.
            codes = codes + (
                f"{EVIDENCE_REGIME_GATED}"
                f":selector={self._regime_selector_family}"
                f":requested={float(regime_selection.eps_requested):.9g}"
                f":ceiling={float(regime_selection.ceiling):.9g}"
                f":applied={float(regime_selection.eps_next):.9g}"
                f":e_rho={float(regime_selection.e_rho):.9g}",
            ) + tuple(regime_selection.audit_codes)
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

    # -- Phase-4 / Design #3: Lemma 4 regime gate -------------------------

    def _select_regime_eps(
        self,
        eps_requested: float,
        *,
        round_in_cycle: int,
        target_round: int,
    ) -> RegimeSelection:
        """Clamp ``eps_requested`` into the Lemma 4 regime.

        Resolves ``e_rho`` for the round through
        :attr:`e_rho_provider`, hands the PID's proposal to the
        configured
        :class:`~adaptive_reflow.algorithm.scheduler.regime_selector.RegimeAwareEpsSelector`,
        records the resulting :class:`RegimeSelection` per round, and
        pushes any warning onto the scheduler's regime log (and the
        module logger). Never raises for an out-of-regime request —
        clamping *is* the fix — but does raise when the caller's
        ``e_rho_provider`` itself returns a non-finite value, because
        that indicates a broken paper-quantity wiring rather than a
        schedule that stepped too far.
        """
        selector = self._regime_selector
        provider = self.e_rho_provider
        if selector is None or provider is None:  # pragma: no cover - guarded
            raise RuntimeError(
                "regime gate is active but the selector / e_rho provider is "
                "unset; this indicates the scheduler was mutated after "
                "construction"
            )
        e_rho = float(provider(float(target_round)))
        if not math.isfinite(e_rho):
            raise ValueError(
                f"e_rho_provider returned non-finite {e_rho!r} for round "
                f"{target_round}"
            )
        selection = selector.select_detailed(
            float(eps_requested),
            e_rho,
            slack=float(self._regime_slack),
            round_index=int(round_in_cycle),
        )
        self._last_regime_selection = selection
        self._regime_selection_by_round[int(round_in_cycle)] = selection
        if selection.warning is not None:
            warning = (
                f"{selection.warning} "
                f"(round_in_cycle={int(round_in_cycle)}, "
                f"target_round={int(target_round)})"
            )
            self._regime_warnings.append(warning)
            _LOGGER.warning("%s", warning)
        return selection

    def regime_violation_warnings(self) -> tuple[str, ...]:
        """Return the per-run log of Lemma 4 regime warnings.

        One entry per round where the PID's ``eps`` proposal violated
        ``eps^2 < e_rho / log 2`` (clamped) or where the ceiling itself
        was infeasible. Empty when the gate is inert or every round
        stayed inside the regime. Cleared by :meth:`reset`.
        """
        return tuple(self._regime_warnings)

    @property
    def regime_selector(self) -> RegimeAwareEpsSelector | None:
        """Return the configured selector (``None`` when the gate is off)."""
        return self._regime_selector

    @property
    def last_regime_selection(self) -> RegimeSelection | None:
        """Return the most recent :class:`RegimeSelection`, if any."""
        return self._last_regime_selection

    def regime_selection_for_round(
        self, round_in_cycle: int,
    ) -> RegimeSelection | None:
        """Return the :class:`RegimeSelection` recorded for a round."""
        return self._regime_selection_by_round.get(int(round_in_cycle))

    def cycle_length(self) -> int:
        """Return the configured cycle length."""
        return int(self._config.cycle_length)
    def schedule_family(self) -> str:
        """Return the algorithm family identifier ``"evidence_driven"``."""
        return self.FAMILY

    def config_hash(self) -> str:
        """Return a stable identifier for the algorithm + its config.

        P1-1 (F-2): the hash now includes ``k_eps`` and the
        ``eps_implicit_base`` so two schedulers that differ ONLY in
        the C4-uplift fields have distinct hashes (the audit trail is
        complete). The previous hash dropped ``k_eps`` which made
        C4-uplift configurations indistinguishable from their
        non-uplift twins.
        """
        hash_payload: dict[str, Any] = {
            "algorithm": self.FAMILY,
            "cycle_length": int(self._config.cycle_length),
            "n_min": float(self._config.n_min),
            "n_max": float(self._config.n_max),
            "kp": float(self._controller.kp),
            "ki": float(self._controller.ki),
            "max_step": float(self._controller.max_step),
            "target_ratio": float(self._controller.target_ratio),
            "k_eps": float(self._k_eps),
        }
        if self._eps_implicit_base is not None:
            hash_payload["eps_implicit_base"] = float(self._eps_implicit_base)
        # Phase-4 / Design #3: the regime keys enter the hash ONLY when
        # the gate is active, so a Phase-3 config keeps its existing
        # hash byte-for-byte while two regime-aware schedulers that
        # differ only in their selector / slack stay distinguishable in
        # the audit trail.
        if self.regime_aware:
            hash_payload["regime_aware"] = True
            hash_payload["regime_selector_family"] = str(
                self._regime_selector_family
            )
            hash_payload["regime_slack"] = float(self._regime_slack)
            selector = self._regime_selector
            if selector is not None:
                hash_payload["regime_selector_config"] = dict(
                    selector.to_config()
                )
        return str(hash_artifact(hash_payload))

    def reset(self) -> None:
        """Reset internal state so the scheduler can be re-run from scratch."""
        self._last_sample = None
        self._last_audit_codes = ()
        self._last_pid_delta = 0.0
        # C4 uplift: reset the parallel ``_last_eps_delta`` accumulator.
        self._last_eps_delta = 0.0
        # P1-2 (F-3): clear the per-round delta history so a re-run
        # starts with a clean slate.
        self._pid_delta_by_round.clear()
        self._eps_delta_by_round.clear()
        # Phase-4 / Design #3: clear the regime log + selector memory so
        # a re-run starts inside the same regime it started with.
        self._regime_warnings.clear()
        self._last_regime_selection = None
        self._regime_selection_by_round.clear()
        selector = self._regime_selector
        if selector is not None:
            selector.reset()
        self._controller.reset()
        self._wrapped.reset()

    # -- P1-2 (F-3) per-round PID delta lookup ----------------------------

    def pid_delta_for_round(self, round_in_cycle: int) -> float:
        """Return the PID delta computed from ``round_in_cycle``'s feedback.

        P1-2 (F-3): the legacy ``_last_pid_delta`` has one-round-
        stale semantics — the delta derived from round ``r``'s
        feedback is consumed by round ``r+1``'s sample. Callers that
        want to amend round ``r``'s metric with the delta derived
        from round ``r``'s OWN feedback should call this method.

        Returns ``0.0`` when no feedback was recorded for the given
        round (matches the controller's neutral initial state).
        """
        return float(self._pid_delta_by_round.get(int(round_in_cycle), 0.0))

    def eps_delta_for_round(self, round_in_cycle: int) -> float:
        """Return the eps delta computed from ``round_in_cycle``'s feedback.

        P1-2 (F-3): companion to :meth:`pid_delta_for_round` for the
        C4-uplift ``eps_implicit`` path. Returns ``0.0`` when no
        feedback was recorded or when ``eps_implicit_base`` was
        ``None`` at construction time.
        """
        return float(self._eps_delta_by_round.get(int(round_in_cycle), 0.0))

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
        # P1-2 (F-3): record the delta per round so the runner can
        # amend round ``r``'s metric with the delta derived from
        # round ``r``'s own feedback (closes the "one round stale"
        # loop). The legacy ``_last_pid_delta`` field is left
        # intact so the existing forward-propagation semantics are
        # preserved for callers that consume ``_last_pid_delta``
        # directly.
        self._pid_delta_by_round[int(round_in_cycle)] = float(delta)
        # C4 uplift: split the PID's delta between ``n_cap`` (the
        # legacy destination) and ``eps_implicit`` (the C4 path).
        # Paper Theorem 1: ratio rises as ``eps -> 0`` => positive
        # ``error`` => lower ``eps``. The integral term is included
        # implicitly via the controller (it sums into ``delta``).
        if self._eps_implicit_base is not None:
            self._last_eps_delta = -float(delta) * float(self._k_eps)
            self._eps_delta_by_round[int(round_in_cycle)] = -float(delta) * float(self._k_eps)
        # Phase-4 / Design #3: forward the round's metrics to the regime
        # selector (e.g. ``ConvergenceAdaptiveRegimeSelector`` consumes
        # ``W2`` / ``evidence_ratio``). The cosine variant ignores the
        # feedback; the convergence variant folds it into its history.
        selector = self._regime_selector
        if selector is not None:
            selector.observe_round_feedback(int(round_in_cycle), metrics)
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
        # Phase-4 / Design #3: regime keys enter the config ONLY when
        # the gate is active so Phase-3 round-trips stay byte-identical.
        if self.regime_aware:
            out["regime_aware"] = True
            out["regime_slack"] = float(self._regime_slack)
            out["regime_selector_family"] = str(self._regime_selector_family)
            selector = self._regime_selector
            if selector is not None:
                out["regime_selector_config"] = dict(selector.to_config())
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
        # Phase-4 / Design #3: rebuild the selector from its config
        # dict so the regime gate survives a round-trip. ``None`` when
        # the gate is off — ``build_regime_selector`` is never called
        # for Phase-3 callers.
        regime_aware = bool(config.get("regime_aware", False))
        regime_selector: RegimeAwareEpsSelector | None = None
        if regime_aware:
            family = str(config.get("regime_selector_family", "cosine_anneal"))
            selector_config = dict(config.get("regime_selector_config") or {})
            # ``selector_config["family"]`` is informational; passing
            # it as a kwarg duplicates the explicit ``family=`` arg, so
            # we pop it and re-route through the concrete's
            # ``from_config`` (which is the canonical round-trip path
            # for the regime selector).
            selector_config.pop("family", None)
            from adaptive_reflow.algorithm.scheduler.regime_selector import (
                REGIME_SELECTOR_REGISTRY,
            )
            selector_cls = REGIME_SELECTOR_REGISTRY.get(family)
            if selector_cls is None:
                known = ", ".join(sorted(REGIME_SELECTOR_REGISTRY))
                raise ValueError(
                    f"unknown regime selector family {family!r} in "
                    f"from_config; known families: {known}"
                )
            regime_selector = selector_cls.from_config(selector_config)  # type: ignore[attr-defined]
        return cls(
            config=sched_config,
            kp=float(config.get("kp", 0.2)),
            ki=float(config.get("ki", 0.05)),
            max_step=float(config.get("max_step", 0.05)),
            target_ratio=float(config.get("target_ratio", 1.0)),
            k_eps=float(config.get("k_eps", 0.5)),
            eps_implicit_base=eps_base,
            regime_aware=regime_aware,
            regime_selector=regime_selector,
            regime_slack=float(config.get("regime_slack", DEFAULT_REGIME_SLACK)),
            regime_selector_family=str(
                config.get("regime_selector_family", "cosine_anneal"),
            ),
            # Round-trip leaves ``e_rho_provider`` to the constructor's
            # paper-default fallback (``default_e_rho_provider()``); a
            # custom provider is not JSON-serialisable and so cannot
            # survive a snapshot replay — callers needing one must
            # supply it after rebuild.
        )


__all__ = [
    "EVIDENCE_PID_ADJUSTED",
    "EVIDENCE_PID_SATURATED",
    "EVIDENCE_RATIO_MISSING",
    "EVIDENCE_REGIME_GATED",
    "EvidenceDrivenScheduler",
    "REGIME_VIOLATION_WARNING",
]


# Defensive: silence unused-import linters for symbols used in
# type-only contexts.
_ = (math, Mapping)

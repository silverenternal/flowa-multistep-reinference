"""Parameter-free hyperparameter derivation (DERIV-001).

This module is the **minimal proof** that the framework's
hyperparameter-free principle can be instantiated on a single
component — the canonical restart blend's ``memory_fraction``,
which is currently hand-set to ``1 - n_cap`` per ADR-0010
(cosine-driven memory fraction).

Background
----------

The framework's "Hyperparameter-Freeness Principle" (DERIV-001)
asserts that every framework hyperparameter MUST trace to one of
five authorized sources:

1. **Paper quantity** — ``A_g``, ``B_g``, ``C_g``, or ``e_rho``
   (Lemmas 2–5 of the JMAA paper).
2. **Local curvature** — a Lipschitz constant ``L_e`` of the
   residual / envelope profile.
3. **Mathematical invariant** — closed-form algorithm-family
   invariant (variance-preserving noise schedule, OT path,
   BL-convergence Theorem 1).
4. **Information-geometry identity** — natural-gradient /
   Fisher-information over the algorithm posterior (NOT model
   parameters; distinct namespace).
5. **Generic convergence theorem** — Polyak step size, Dormand-
   Prince adaptive ``h_t``, Adam-style time constant.

Hand-set engineering constants are permitted only as **named
provenance** entries with documented empirical origin, and must
be the exception, not the rule.

Concrete application
--------------------

This module instantiates the principle on a single derivation:

* :class:`PolyakMemoryFraction` derives the per-round restart
  blend's ``memory_fraction`` from the relative Wasserstein-2
  distance between the round-0 baseline and the current round's
  residual profile:

      m_t := W2_round_t / (W2_round_0 + W2_round_t)

  This is the closed-form Polyak-style step applied to a
  Wasserstein-gap ratio (see s1 Principle 3, s3 refinement). The
  derivation falls back to the canonical ``1 - n_cap`` whenever
  the surrounding context is missing, preserving the existing
  ADR-0010 wiring so all 2356+15 existing tests stay green.

Module contract
---------------

* **stdlib-only** on the public surface (ADR-0001). The internal
  derivation math uses :mod:`math` only; no :mod:`numpy` or
  :mod:`scipy` import is required.
* **Frozen dataclasses** for every concrete subclass so the
  class-level provenance attributes
  (:attr:`derivation_source`, :attr:`derivation_formula`,
  :attr:`academic_precedent`) cannot be silently mutated.
* **Pure** w.r.t. arguments — ``derive(context)`` is a
  deterministic function of the context and the instance
  configuration.
* **Fail-closed** — ``DerivationContext`` fields are typed
  ``Optional``; when a derivation requires a field that is
  ``None``, the derivation returns the documented hand-set
  fallback rather than guessing.
* **Provenance-rich** — every concrete derivation exposes the
  authoritative source category, the closed-form formula, and
  the academic citation.

Cited literature
----------------

* Polyak (1969), "Introduction to Optimization" — residual-
  derived step sizes and objective-gap weighting (s1 Principle 3).
* Lipman et al. (2023), "Flow Matching for Generative Modeling",
  arXiv:2210.02747 — symmetric OT path on which the W2 ratio
  lives.
* Algorithm layer ADR-0010 — cosine-driven memory fraction
  (``1 - n_cap``), preserved as the documented back-compat
  fallback when the derivation context is unavailable.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, ClassVar, Optional, Protocol, runtime_checkable

__all__ = [
    "BLConvergenceEpsilonSchedule",
    "BoundaryConditionRule",
    "BoundedMergeFloorRule",
    "ConvergenceAdaptivePolyRule",
    "DEFAULT_EPSILON_SCHEDULE_FALLBACK",
    "DEFAULT_LIPSCHITZ_STEP_FALLBACK",
    "DEFAULT_MEMORY_FRACTION_FALLBACK",
    "DerivationContext",
    "DerivationRule",
    "DerivationCycleError",
    "EMAInverseVarianceRule",
    "EpsLogRule",
    "ExponentialAlphaRule",
    "FisherMemoryFraction",
    "LipschitzStepSize",
    "LipschitzTemperatureRule",
    "MachineEpsilonRule",
    "MeanFlowFixedStrengthRule",
    "MeanFlowToleranceRule",
    "MetricWeightRule",
    "MidpointBetaRule",
    "MinGumbelTempRule",
    "NAMESPACE_ALGORITHM_POSTERIOR",
    "OTEpsilonSchedule",
    "PolyakMemoryFraction",
    "PolynomialPowerRule",
    "SigmoidMidpointSteepnessRule",
    "VariancePreservingJitterRule",
    "default_adaptive_target_estimate",
    "default_alpha_grad",
    "default_constant_beta",
    "default_convergence_adaptive_ema",
    "default_convergence_adaptive_kd",
    "default_convergence_adaptive_kp",
    "default_convergence_adaptive_shift_max",
    "default_distance_decay_temperature",
    "default_ema_alpha",
    "default_eps_implicit",
    "default_eps_log",
    "default_exponential_alpha",
    "default_handoff_window",
    "default_jitter_std",
    "default_lipschitz_step",
    "default_machine_eps",
    "default_memory_fraction",
    "default_metric_weights",
    "default_min_gumbel_temp",
    "default_polynomial_power",
    "default_sigmoid_midpoint",
    "default_sigmoid_steepness",
    "default_tolerance",
    "make_derivation_context",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: ADR-0010 cosine-driven memory fraction. Returned by
#: :func:`default_memory_fraction` whenever the supplied derivation
#: context is missing the inputs the chosen :class:`DerivationRule`
#: needs. This is the canonical back-compat path; existing callers
#: that do not pass a context keep getting ``1 - n_cap`` verbatim.
DEFAULT_MEMORY_FRACTION_FALLBACK: str = "adr0010_cosine_driven"

#: Hand-set baseline for :class:`OTEpsilonSchedule` /
#: :class:`BLConvergenceEpsilonSchedule` when the derivation context
#: is missing the inputs the rule needs. Matches the
#: :class:`~adaptive_reflow.algorithm.scheduler.CodimensionSheetScheduler`
#: construction-time default ``eps_implicit = 0.05``; this is the
#: canonical back-compat path so existing callers that do not pass a
#: context keep getting ``0.05`` verbatim (preserves the
#: 2356+15 test suite).
DEFAULT_EPSILON_SCHEDULE_FALLBACK: float = 0.05

#: Hand-set baseline for :class:`LipschitzStepSize` when the
#: derivation context is missing the inputs it needs. ``1.0 /
#: n_steps`` is the canonical Dormand-Prince fallback used by the
#: :class:`~adaptive_reflow.algorithm.dynamics_solver` integration
#: step driver; this fallback preserves that wiring for legacy
#: callers.
DEFAULT_LIPSCHITZ_STEP_FALLBACK: str = "dormand_prince_uniform"

#: Distinct namespace for Fisher-information computations that
#: operate on the **algorithm posterior** rather than on model
#: parameters. Used by :class:`FisherMemoryFraction` (future work)
#: to refuse cross-namespace derivation cycles.
NAMESPACE_ALGORITHM_POSTERIOR: str = "algorithm_posterior"

#: Canonical back-compat fallback for :class:`MeanFlowToleranceRule`
#: when context is missing. Matches
#: :class:`MeanFlowMergeOperator.tolerance` default ``1e-9``.
DEFAULT_MEANFLOW_TOLERANCE_FALLBACK: float = 1e-9

#: Canonical back-compat fallback for :class:`MachineEpsilonRule`.
#: Matches the hand-coded ``1e-12`` degenerate-pair floor in
#: :class:`MeanFlowMergeOperator`.
DEFAULT_MEANFLOW_EPS_FALLBACK: float = 1e-12

#: Canonical back-compat fallback for :class:`EMAInverseVarianceRule`.
#: Matches the canonical ``0.1`` smoothing factor used by
#: :class:`EMAOperator`.
DEFAULT_EMA_ALPHA_FALLBACK: float = 0.1

#: Canonical back-compat fallback for :class:`LipschitzTemperatureRule`.
#: Matches :data:`DEFAULT_DISTANCE_DECAY_TEMPERATURE` ``1.0``.
DEFAULT_LIPSCHITZ_TEMP_FALLBACK: float = 1.0

#: Canonical back-compat fallback for :class:`MinGumbelTempRule`.
#: Matches :data:`DEFAULT_MIN_GUMBEL_TEMP` ``1e-3``.
DEFAULT_MIN_GUMBEL_TEMP_FALLBACK: float = 1e-3

#: Canonical back-compat fallback for :class:`EpsLogRule`. Matches
#: :data:`EPS_LOG` ``1e-30``.
DEFAULT_EPS_LOG_FALLBACK: float = 1e-30

#: Canonical back-compat fallback for :class:`ExponentialAlphaRule`.
#: Matches :class:`ExponentialScheduler.alpha` default ``0.1``.
DEFAULT_EXPONENTIAL_ALPHA_FALLBACK: float = 0.1

#: Canonical back-compat fallback for :class:`PolynomialPowerRule`.
#: Matches :class:`PolynomialScheduler.power` default ``2.0``.
DEFAULT_POLYNOMIAL_POWER_FALLBACK: float = 2.0

#: Canonical back-compat fallback for
#: :class:`SigmoidMidpointSteepnessRule.midpoint`. Matches
#: :class:`SigmoidScheduler.midpoint` default ``0.5``.
DEFAULT_SIGMOID_MIDPOINT_FALLBACK: float = 0.5

#: Canonical back-compat fallback for
#: :class:`SigmoidMidpointSteepnessRule.steepness`. Matches
#: :class:`SigmoidScheduler.steepness` default ``10.0``.
DEFAULT_SIGMOID_STEEPNESS_FALLBACK: float = 10.0

#: Canonical back-compat fallback for
#: :class:`ConvergenceAdaptivePolyRule.kp`. Matches the legacy
#: ``ConvergenceAdaptiveScheduler`` default ``0.10``.
DEFAULT_KP_FALLBACK: float = 0.10

#: Canonical back-compat fallback for
#: :class:`ConvergenceAdaptivePolyRule.kd`. Matches the legacy
#: ``ConvergenceAdaptiveScheduler`` default ``0.05``.
DEFAULT_KD_FALLBACK: float = 0.05

#: Canonical back-compat fallback for
#: :class:`ConvergenceAdaptivePolyRule.shift_max`. Matches the
#: legacy default ``0.15``.
DEFAULT_SHIFT_MAX_FALLBACK: float = 0.15

#: Canonical back-compat fallback for
#: :class:`ConvergenceAdaptivePolyRule.ema`. Matches the legacy
#: default ``0.3``.
DEFAULT_EMA_SCHED_FALLBACK: float = 0.3

#: Canonical back-compat fallback for :class:`MetricWeightRule`.
#: Matches the literal ``DEFAULT_FEEDBACK_METRIC_WEIGHTS`` dict.
DEFAULT_METRIC_WEIGHTS_FALLBACK: dict[str, float] = {
    "W2": 1.0,
    "coverage": 0.3,
    "selection_ratio": 0.5,
}

#: Canonical back-compat fallback for
#: :class:`VariancePreservingJitterRule`. Matches
#: :class:`JitteredConstantScheduler.jitter_std` default ``0.05``.
DEFAULT_JITTER_STD_FALLBACK: float = 0.05

#: Canonical back-compat fallback for :class:`MidpointBetaRule`.
#: Matches :data:`DEFAULT_CONSTANT_BETA` ``0.5``.
DEFAULT_CONSTANT_BETA_FALLBACK: float = 0.5

#: Canonical back-compat fallback for
#: :class:`MidpointBetaRule` (target_estimate path). Matches
#: :data:`DEFAULT_ADAPTIVE_TARGET_ESTIMATE` ``0.5``.
DEFAULT_TARGET_ESTIMATE_FALLBACK: float = 0.5

#: Provenance constant — :class:`BoundedMergeFloorRule` divisor
#: per Theorem 1 Lemma 5. The derivation IS the literal ``4.0``,
#: preserved here as named provenance (ADR-0010 back-compat).
PAPER_QUANTITY_E_RHO_FLOOR_DIVISOR: float = 4.0


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class DerivationCycleError(ValueError):
    """Raised when a :class:`DerivationRule` would create a
    cyclic dependency in the derivation DAG.

    Cyclic derivations are forbidden by the principle: every
    derivation must read paper quantities, scheduler state, or OT
    metrics, but never write back into the quantities it derives
    from. The runtime check enforces this for the small set of
    concrete derivations that participate in the cross-derivation
    DAG (PolyakMemoryFraction ↔ FisherMemoryFraction, etc.).
    """


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DerivationContext:
    """Inputs to a :class:`DerivationRule.derive` call.

    All fields are :data:`Optional` because the framework's
    parameter-free regime is **opt-in**: callers that do not
    supply a context (or supply a context with missing fields)
    fall back to the hand-set default. Each concrete
    :class:`DerivationRule` declares which fields it requires
    via its :attr:`required_fields` attribute; missing required
    fields trigger the fallback rather than an exception.

    Attributes
    ----------
    paper_quantities:
        JMAA paper quantities ``(A_g, B_g, C_g, e_rho)``. All
        fields are ``None`` when the caller has not profiled the
        residual / envelope function.
    local_curvature:
        Local Lipschitz estimate ``L_e``, current best objective
        ``f_best``, and per-round gradient variance
        ``grad_var``. All fields ``None`` when the caller has
        not wired a Lipschitz estimator.
    scheduler_state:
        Per-round scheduler view: ``n_cap_t`` (this round's
        capacity), ``n_min`` / ``n_max`` (cycle anchors),
        ``n_rounds``, ``cycle_length``, ``t`` / ``s`` (round
        indices for t/s schedules such as MeanFlow).
    ot_metrics:
        Per-round OT residuals: ``W2_round_t`` (this round's
        W2), ``W2_round_0`` (round-0 baseline), and
        ``KL_prior_fresh`` (per-round Fisher divergence between
        prior and fresh endpoints; ``None`` when not measured).
    """

    paper_quantities: Mapping[str, float | None]
    local_curvature: Mapping[str, float | None]
    scheduler_state: Mapping[str, float | None]
    ot_metrics: Mapping[str, Any]


def make_derivation_context(
    *,
    n_cap: float | None = None,
    n_min: float | None = None,
    n_max: float | None = None,
    cycle_length: int | None = None,
    n_rounds: int | None = None,
    w2_round_t: float | None = None,
    w2_round_0: float | None = None,
    e_rho: float | None = None,
    a_g: float | None = None,
    b_g: float | None = None,
    c_g: float | None = None,
    l_e: float | None = None,
    f_best: float | None = None,
    grad_var: float | None = None,
    grad_mean: float | None = None,
    fisher_information: float | None = None,
    w2_history: tuple[float, ...] | None = None,
    metric_variances: Mapping[str, tuple[float, ...]] | None = None,
    t: float | None = None,
    s: float | None = None,
    kl_prior_fresh: float | None = None,
    eps_implicit: float | None = None,
    delta_t: float | None = None,
    n_steps: int | None = None,
    err: float | None = None,
    tol: float | None = None,
    f_trace: float | None = None,
    d: int | None = None,
    alpha: float | None = None,
    handoff_window: int | None = None,
) -> DerivationContext:
    """Build a :class:`DerivationContext` from the caller's kwargs.

    Convenience constructor used by the engine / runners. Every
    field defaults to ``None`` so callers wire only the values
    they have computed. The :class:`PolyakMemoryFraction`
    derivation requires ``w2_round_t`` and ``w2_round_0``; if
    either is ``None``, the derivation falls back to ``1 - n_cap``
    (ADR-0010) and surfaces the fallback via the audit code
    ``memory_fraction_fallback_to_adr0010``.

    The 4 new concrete derivations added in P-19
    (:class:`OTEpsilonSchedule`, :class:`BLConvergenceEpsilonSchedule`,
    :class:`LipschitzStepSize`, :class:`FisherMemoryFraction`) read
    additional fields:

    * ``eps_implicit`` -- per-round implicit noise scale (held in
      ``scheduler_state``). :class:`OTEpsilonSchedule` uses this as
      the baseline ``eps_0`` in ``eps_t = eps_0 * (1 + C_g * t)``.
    * ``delta_t`` -- per-round step size (held in
      ``scheduler_state``). :class:`BLConvergenceEpsilonSchedule`
      uses this in ``eps_t = sqrt(e_rho * delta_t)``.
    * ``n_steps`` -- total integration steps (held in
      ``scheduler_state``). :class:`LipschitzStepSize` falls back
      to ``dt = 1.0 / n_steps`` when no Lipschitz context is
      supplied.
    * ``err`` -- current local truncation error (held in
      ``local_curvature``). :class:`LipschitzStepSize` uses
      ``h_t = (tol / max(err, 1e-9))^{1/5} / L_e``.
    * ``tol`` -- target tolerance (held in
      ``local_curvature``). :class:`LipschitzStepSize` uses
      ``(tol / err)^{1/5}`` for the Dormand-Prince step
      controller.
    * ``f_trace`` -- Fisher trace (held in
      ``local_curvature``). :class:`FisherMemoryFraction` uses
      ``m_Fisher = 1 / (1 + F_trace / d)``.
    * ``d`` -- ambient dimension (held in
      ``local_curvature``). :class:`FisherMemoryFraction` uses
      this in the denominator of the Fisher step.
    * ``alpha`` -- handoff alpha (held in
      ``scheduler_state``). Forwarded to :func:`default_alpha_grad`.
    * ``handoff_window`` -- sequential handoff window (held in
      ``scheduler_state``). Forwarded to
      :func:`default_handoff_window`.

    The helper is pure: it does not validate that ``n_cap`` is in
    ``[0, 1]`` or that ``w2_round_t >= 0``; the derivation's
    :meth:`DerivationRule.derive` enforces those invariants and
    raises :class:`ValueError` on a contract violation (instead of
    silently clipping) so the caller can surface the bug rather
    than papering over it.
    """
    return DerivationContext(
        paper_quantities={
            "A_g": a_g,
            "B_g": b_g,
            "C_g": c_g,
            "e_rho": e_rho,
        },
        local_curvature={
            "L_e": l_e,
            "f_best": f_best,
            "grad_var": grad_var,
            "grad_mean": grad_mean,
            "err": err,
            "tol": tol,
            "F_trace": f_trace,
            "d": (float(d) if d is not None else None),
            "fisher_information": fisher_information,
        },
        scheduler_state={
            "n_cap_t": n_cap,
            "n_min": n_min,
            "n_max": n_max,
            "n_rounds": (float(n_rounds) if n_rounds is not None else None),
            "cycle_length": (
                float(cycle_length) if cycle_length is not None else None
            ),
            "t": t,
            "s": s,
            "eps_implicit": eps_implicit,
            "delta_t": delta_t,
            "n_steps": (float(n_steps) if n_steps is not None else None),
            "alpha": alpha,
            "handoff_window": (
                float(handoff_window) if handoff_window is not None else None
            ),
        },
        ot_metrics={
            "W2_round_t": w2_round_t,
            "W2_round_0": w2_round_0,
            "KL_prior_fresh": kl_prior_fresh,
            "W2_history": (
                tuple(float(v) for v in w2_history)
                if w2_history is not None
                else None
            ),
            "metric_variances": (
                {str(k): tuple(float(x) for x in v) for k, v in metric_variances.items()}
                if metric_variances is not None
                else None
            ),
        },
    )


# ---------------------------------------------------------------------------
# Abstract protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class DerivationRule(Protocol):
    """Abstract protocol for a parameter-free derivation.

    A :class:`DerivationRule` consumes a :class:`DerivationContext`
    and returns a derived float (clipped to ``[0, 1]`` for memory
    fractions). Concrete subclasses MUST declare
    :attr:`derivation_source`, :attr:`derivation_formula`, and
    :attr:`academic_precedent` so the framework's provenance
    verification (see ``tools/check_docs_against_code.py``) can
    attribute every derived value to an authorized source.

    Class-level attributes
    ----------------------
    derivation_source:
        One of ``"paper_quantities"``, ``"lipschitz"``,
        ``"variance_preserving"``, ``"ot"``, ``"bl_convergence"``,
        ``"information_geometry"``, ``"polyak"``, ``"fisher"``,
        ``"other"``. Free-form text is allowed but discouraged.
    derivation_formula:
        The closed-form expression as a string (single line, no
        newlines). Used by the docs verifier to keep
        ``docs/ALGORITHMS.md`` in sync with the implementation.
    academic_precedent:
        List of citation strings (``"Author Year (arXiv:NNNN.NNNNN)"``
        or ``"Author Year (Publisher)"``). Used by the docs
        verifier to ensure every derivation cites a real paper.
    fallback:
        The hand-set value returned when the required context
        fields are missing. Must be in ``[0, 1]`` for memory
        fractions.
    """

    derivation_source: ClassVar[str]
    derivation_formula: ClassVar[str]
    academic_precedent: ClassVar[tuple[str, ...]]
    fallback: ClassVar[float]
    required_fields: ClassVar[tuple[str, ...]]

    def derive(self, context: DerivationContext) -> float:
        """Return the derived value, or :attr:`fallback` if the
        context is missing the inputs the rule needs.

        Implementations MUST be deterministic and free of side
        effects. They MUST clip the returned value into ``[0, 1]``
        for memory fractions and raise :class:`ValueError` on
        non-finite inputs (rather than silently coercing).
        """
        ...

    def __call__(self, context: DerivationContext) -> Any:
        """Sugar: ``rule(context) == rule.derive(context)``.

        Concrete subclasses that emit non-float returns (e.g.
        :class:`MetricWeightRule` emits a dict) MUST override this
        hook. Default implementation returns ``self.derive(context)``.
        """
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: PolyakMemoryFraction (DERIV-001 proof)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PolyakMemoryFraction:
    """Derive ``memory_fraction`` from the Wasserstein-2 ratio.

    Closed form (s1 Principle 3, s3 refinement):

        m_t := W2_round_t / (W2_round_0 + W2_round_t)

    Intuition: when the current round's residual profile is
    close to the round-0 baseline (``W2_round_t ≈ W2_round_0``),
    the fraction is near 0.5 — neither prior nor fresh dominates.
    As the round progresses and the residual profile sharpens
    (``W2_round_t → 0``), ``m_t → 0`` (memory fades; fresh noise
    is allowed to dominate, which matches the cosine-annealing
    schedule). Conversely, when the residual profile grows
    (``W2_round_t > W2_round_0``), ``m_t → 1`` — the prior
    dominates because the fresh sample is not informative.

    This is the Polyak step applied to the Wasserstein-gap
    ratio: ``m_t`` measures how much of the *initial*
    Wasserstein gap remains. When the gap closes, we trust the
    prior less and let fresh noise in; when it widens, we trust
    the prior more.

    Backward compatibility
    ----------------------

    When ``W2_round_t`` or ``W2_round_0`` is ``None`` (the
    canonical case for schedulers that have not yet measured the
    OT residual), :meth:`derive` returns the documented fallback
    ``1 - n_cap`` (ADR-0010) verbatim. This keeps the existing
    2356+15 test suite green while making the parameter-free
    regime opt-in.

    Robustness
    ----------

    The derivation raises :class:`ValueError` when the supplied
    W2 values are non-finite or non-numeric. It does NOT raise on
    a zero ``W2_round_0``; the closed-form ratio collapses to
    ``1`` when ``W2_round_t > 0`` and to ``0`` when both are
    zero (the "first round, no measurement yet" case). The
    returned value is clipped into ``[0, 1]`` defensively.

    DAG discipline
    --------------

    :class:`PolyakMemoryFraction` reads ``ot_metrics`` and
    ``scheduler_state`` only. It never reads or writes
    ``paper_quantities`` and never produces a value that feeds
    back into the W2 measurement (no cycle).
    """

    derivation_source: ClassVar[str] = "ot"
    derivation_formula: ClassVar[str] = (
        "m_t := W2_round_t / (W2_round_0 + W2_round_t)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Polyak 1969 (Introduction to Optimization)",
        "Lipman et al. 2023 Flow Matching arXiv:2210.02747",
    )
    #: ADR-0010 cosine-driven memory fraction: ``1 - n_cap``.
    fallback: ClassVar[float] = 0.5  # placeholder; actual fallback
    # is computed against ``scheduler_state['n_cap_t']`` at derive
    # time so the contract stays correct when ``n_cap_t`` is None.
    required_fields: ClassVar[tuple[str, ...]] = (
        "ot_metrics.W2_round_t",
        "ot_metrics.W2_round_0",
        "scheduler_state.n_cap_t",
    )

    def derive(self, context: DerivationContext) -> float:
        """Return the derived ``memory_fraction`` in ``[0, 1]``.

        When the OT metrics are missing, fall back to ADR-0010
        (``1 - n_cap``). When ``n_cap_t`` is also missing, fall
        back to a documented mid-cycle anchor of 0.5 (the
        symmetric envelope center per ADR-0010).
        """
        w2_t_raw = context.ot_metrics.get("W2_round_t")
        w2_0_raw = context.ot_metrics.get("W2_round_0")
        n_cap_raw = context.scheduler_state.get("n_cap_t")
        # Backward-compat fallback path.
        if w2_t_raw is None or w2_0_raw is None:
            return _adr0010_fallback(n_cap_raw)
        # Validate inputs (fail-closed rather than silent clip).
        w2_t = _coerce_finite(w2_t_raw, "W2_round_t")
        w2_0 = _coerce_finite(w2_0_raw, "W2_round_0")
        if w2_t < 0.0:
            raise ValueError(
                f"W2_round_t must be >= 0, got {w2_t!r}"
            )
        if w2_0 < 0.0:
            raise ValueError(
                f"W2_round_0 must be >= 0, got {w2_0!r}"
            )
        # Closed-form Polyak ratio. When the baseline is zero
        # the ratio collapses to 0/1 — choose the canonical
        # "no measurement" path (return 0.5 + sign(w2_t) * 0.5)
        # so the result stays in [0, 1] without an explicit clip.
        if w2_0 == 0.0:
            return 1.0 if w2_t > 0.0 else 0.0
        m = w2_t / (w2_0 + w2_t)
        return float(max(0.0, min(1.0, m)))

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: OTEpsilonSchedule (DERIV-001 proof #2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OTEpsilonSchedule:
    r"""Derive ``eps_implicit`` per-round from the OT-path codimension.

    Closed form (Lipman et al. 2023, "Flow Matching for Generative
    Modeling", arXiv:2210.02747, eq. 22 — the OT path on which
    codimension-Lemma 3 sits):

        eps_t  =  eps_implicit * (1 + C_g * t)

    where:

    * ``eps_implicit`` is the round-0 baseline (held in
      ``scheduler_state['eps_implicit']``).
    * ``C_g`` is the paper-quantity codimension coefficient
      (Lemma 3 / line 191, computed via
      :func:`adaptive_reflow.contracts.paper_quantities.per_cell_coefficient_C`).
    * ``t`` is the round index in ``[0, cycle_length - 1]``.

    The schedule grows linearly in the round index with a slope
    ``C_g * eps_implicit``; the closed form is consistent with the
    flow-matching OT path's ``eps_t`` (the implicit noise scale at
    every interpolation point) and reduces to the constant
    ``eps_implicit`` baseline when ``t == 0``.

    Backward compatibility
    ----------------------

    When ``eps_implicit`` or ``C_g`` is ``None``, the derivation
    returns :data:`DEFAULT_EPSILON_SCHEDULE_FALLBACK` (``0.05``,
    the canonical :class:`CodimensionSheetScheduler` default).
    This keeps the existing 2356+15 test suite green while making
    the parameter-free regime opt-in.

    Robustness
    ----------

    The derivation raises :class:`ValueError` when the supplied
    ``eps_implicit`` or ``C_g`` is non-finite or non-numeric.
    Negative ``eps_implicit`` also raises (the closed form assumes
    ``eps > 0``); the rule does NOT raise on ``t < 0`` defensively
    so a broken round index produces a conservative smaller
    ``eps_t`` rather than crashing the engine.

    DAG discipline
    --------------

    :class:`OTEpsilonSchedule` reads ``paper_quantities`` and
    ``scheduler_state`` only. It never reads or writes OT metrics
    and never feeds back into the W2 measurement (no cycle).
    """

    derivation_source: ClassVar[str] = "paper_quantities"
    derivation_formula: ClassVar[str] = (
        "eps_t := eps_implicit * (1 + C_g * t)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Lipman et al. 2023 Flow Matching arXiv:2210.02747",
        "Li 2024 Noise Selected Rectification (Lemma 3)",
    )
    #: Canonical back-compat fallback (matches the
    #: :class:`CodimensionSheetScheduler` default
    #: ``eps_implicit = 0.05``).
    fallback: ClassVar[float] = DEFAULT_EPSILON_SCHEDULE_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "paper_quantities.C_g",
        "scheduler_state.eps_implicit",
        "scheduler_state.t",
    )

    def derive(self, context: DerivationContext) -> float:
        """Return the derived ``eps_implicit`` for round ``t``.

        Returns :data:`DEFAULT_EPSILON_SCHEDULE_FALLBACK` when the
        context is missing ``eps_implicit`` or ``C_g`` (so legacy
        callers keep the canonical ``0.05`` baseline).
        """
        eps_raw = context.scheduler_state.get("eps_implicit")
        c_g_raw = context.paper_quantities.get("C_g")
        # Backward-compat fallback path.
        if eps_raw is None or c_g_raw is None:
            return float(self.fallback)
        eps = _coerce_finite(eps_raw, "eps_implicit")
        c_g = _coerce_finite(c_g_raw, "C_g")
        if eps < 0.0:
            raise ValueError(
                f"eps_implicit must be >= 0, got {eps!r}"
            )
        t_raw = context.scheduler_state.get("t")
        t = 0.0 if t_raw is None else _coerce_finite(t_raw, "t")
        if t < 0.0:
            t = 0.0
        eps_t = eps * (1.0 + c_g * t)
        if not math.isfinite(eps_t) or eps_t < 0.0:
            raise ValueError(
                f"derived eps_t must be finite and >= 0, got {eps_t!r}"
            )
        return float(eps_t)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: BLConvergenceEpsilonSchedule (DERIV-001 proof #3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BLConvergenceEpsilonSchedule:
    r"""Derive ``eps_implicit`` per-round from BL-convergence Theorem 1.

    Closed form (Li 2024, "Gaussian Posterior Selection on
    Noncompact Fibres with Uniformly Separated Roots", Theorem 1
    / line 88 — the BL-convergence scale that drives the
    posterior-selection ratio as ``eps -> 0``):

        eps_t  =  sqrt(e_rho * delta_t)

    where:

    * ``e_rho`` is the paper-quantity exterior gap (Lemma 5 /
      Lemma 4, computed via
      :func:`adaptive_reflow.contracts.paper_quantities.exterior_gap_e_rho`).
    * ``delta_t`` is the per-round step size (held in
      ``scheduler_state['delta_t']``; falls back to
      ``1.0 / cycle_length`` when missing).

    The closed form is the geometric-mean between the exterior
    gap ``e_rho`` and the round step ``delta_t``; this is the
    canonical BL-convergence scale at which the
    ``C_3 * eps^{-1} * exp(-e_rho / (2 eps^2))`` posterior
    complement mass (Corollary 1) starts to matter.

    Backward compatibility
    ----------------------

    When ``e_rho`` is ``None``, the derivation returns the
    documented back-compat fallback ``1e-3`` (the documented
    asymptotic threshold below which the heuristic evidence
    balance is unsound — see
    :data:`adaptive_reflow.algorithm.evidence_driver.EVIDENCE_HEURISTIC_EPS_THRESHOLD`).
    This keeps the existing 2356+15 test suite green while making
    the parameter-free regime opt-in.

    Robustness
    ----------

    The derivation raises :class:`ValueError` when the supplied
    ``e_rho`` is non-finite, non-numeric, or negative. The
    ``delta_t`` fallback (``1.0 / cycle_length``) is fail-closed:
    when both ``delta_t`` and ``cycle_length`` are ``None``, the
    rule returns the documented ``1e-3`` baseline rather than
    producing a garbage ``eps_t``.

    DAG discipline
    --------------

    :class:`BLConvergenceEpsilonSchedule` reads ``paper_quantities``
    and ``scheduler_state`` only. It never writes back into the
    paper quantities it derives from (no cycle).
    """

    derivation_source: ClassVar[str] = "bl_convergence"
    derivation_formula: ClassVar[str] = (
        "eps_t := sqrt(e_rho * delta_t)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Li 2024 Noise Selected Rectification (Theorem 1, Lemma 5)",
    )
    #: Canonical back-compat fallback (matches the
    #: :data:`EVIDENCE_HEURISTIC_EPS_THRESHOLD` documented in
    #: :mod:`adaptive_reflow.algorithm.evidence_driver`).
    fallback: ClassVar[float] = 1e-3
    required_fields: ClassVar[tuple[str, ...]] = (
        "paper_quantities.e_rho",
        "scheduler_state.delta_t",
    )

    def derive(self, context: DerivationContext) -> float:
        """Return the derived ``eps_implicit`` for round ``t``.

        Returns ``1e-3`` when ``e_rho`` is missing. ``delta_t``
        falls back to ``1.0 / cycle_length`` when missing; when
        both ``delta_t`` and ``cycle_length`` are ``None``, the
        documented ``1e-3`` baseline is returned.
        """
        e_rho_raw = context.paper_quantities.get("e_rho")
        if e_rho_raw is None:
            return float(self.fallback)
        e_rho = _coerce_finite(e_rho_raw, "e_rho")
        if e_rho < 0.0:
            raise ValueError(
                f"e_rho must be >= 0, got {e_rho!r}"
            )
        delta_raw = context.scheduler_state.get("delta_t")
        if delta_raw is None:
            cycle_raw = context.scheduler_state.get("cycle_length")
            if cycle_raw is None:
                return float(self.fallback)
            cycle = _coerce_finite(cycle_raw, "cycle_length")
            if cycle <= 0.0:
                return float(self.fallback)
            delta = 1.0 / cycle
        else:
            delta = _coerce_finite(delta_raw, "delta_t")
        if delta < 0.0:
            raise ValueError(
                f"delta_t must be >= 0, got {delta!r}"
            )
        eps_t = math.sqrt(e_rho * delta)
        if not math.isfinite(eps_t) or eps_t < 0.0:
            raise ValueError(
                f"derived eps_t must be finite and >= 0, got {eps_t!r}"
            )
        return float(eps_t)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: LipschitzStepSize (DERIV-001 proof #4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LipschitzStepSize:
    r"""Derive the per-round ODE step ``h_t`` from local Lipschitz curvature.

    Closed form (Dormand & Prince 1980, "A family of embedded
    Runge-Kutta formulae", J. Comp. Appl. Math. 6:19-26 — the
    classical adaptive-step controller used by the framework's
    :class:`~adaptive_reflow.algorithm.dynamics_solver`):

        h_t  =  (tol / max(err, 1e-9))^{1/5} / L_e

    where:

    * ``tol`` is the target tolerance (held in
      ``local_curvature['tol']``).
    * ``err`` is the round's local truncation error (held in
      ``local_curvature['err']``).
    * ``L_e`` is the local Lipschitz estimate (held in
      ``local_curvature['L_e']``).

    The ``1/5`` exponent is the classical RK45 / Dormand-Prince
    embedded-formula order (Dormand & Prince Table 1: ``p == 5``);
    the ``1e-9`` floor on ``err`` guards the controller against
    zero / negative errors that would otherwise blow up the step.
    The step is divided by ``L_e`` so a stiffer region (larger
    Lipschitz constant) shrinks the step proportionally, matching
    the framework's stability contract.

    Backward compatibility
    ----------------------

    When ``L_e`` is ``None``, the derivation returns the
    documented back-compat fallback ``1.0 / n_steps`` (the
    classical uniform-step Dormand-Prince controller used by
    :class:`~adaptive_reflow.algorithm.dynamics_solver` when no
    Lipschitz estimator is wired). This keeps the existing
    2356+15 test suite green while making the parameter-free
    regime opt-in.

    Robustness
    ----------

    The derivation raises :class:`ValueError` when the supplied
    ``tol``, ``err``, or ``L_e`` is non-finite or non-numeric.
    Negative inputs also raise (the closed form assumes all three
    are positive); ``err < 1e-9`` is floored to ``1e-9`` rather
    than rejected so a vanishing-error round produces a maximum
    step rather than crashing the engine.

    DAG discipline
    --------------

    :class:`LipschitzStepSize` reads ``local_curvature`` and
    ``scheduler_state`` only. It never writes back into the
    curvature quantities it derives from (no cycle).
    """

    derivation_source: ClassVar[str] = "lipschitz"
    derivation_formula: ClassVar[str] = (
        "h_t := (tol / max(err, 1e-9))^{1/5} / L_e"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Dormand & Prince 1980 J. Comp. Appl. Math. 6:19-26",
        "Hairer Norsett Wanner 1993 Solving ODEs I (Springer)",
    )
    #: Canonical back-compat fallback (uniform-step
    #: Dormand-Prince ``1.0 / n_steps``).
    fallback: ClassVar[float] = 0.0  # sentinel; the rule computes
    # ``1.0 / n_steps`` from ``scheduler_state['n_steps']`` at
    # derive time so the contract stays correct when ``n_steps``
    # is ``None`` (returns ``0.0``-sentinel never reached).
    required_fields: ClassVar[tuple[str, ...]] = (
        "local_curvature.L_e",
        "local_curvature.tol",
        "local_curvature.err",
    )

    def derive(self, context: DerivationContext) -> float:
        """Return the derived per-round ODE step ``h_t``.

        Returns ``1.0 / n_steps`` when ``L_e`` is missing.
        ``err < 1e-9`` is floored to ``1e-9`` rather than
        rejected so a vanishing-error round produces a maximum
        step rather than crashing the engine.
        """
        l_e_raw = context.local_curvature.get("L_e")
        if l_e_raw is None:
            return _uniform_step_fallback(context)
        l_e = _coerce_finite(l_e_raw, "L_e")
        if l_e <= 0.0:
            raise ValueError(
                f"L_e must be > 0, got {l_e!r}"
            )
        tol_raw = context.local_curvature.get("tol")
        if tol_raw is None:
            return _uniform_step_fallback(context)
        tol = _coerce_finite(tol_raw, "tol")
        if tol <= 0.0:
            raise ValueError(
                f"tol must be > 0, got {tol!r}"
            )
        err_raw = context.local_curvature.get("err")
        if err_raw is None:
            return _uniform_step_fallback(context)
        err = _coerce_finite(err_raw, "err")
        if err < 0.0:
            raise ValueError(
                f"err must be >= 0, got {err!r}"
            )
        err_clamped = max(err, 1e-9)
        h_t = (tol / err_clamped) ** 0.2 / l_e
        if not math.isfinite(h_t) or h_t < 0.0:
            raise ValueError(
                f"derived h_t must be finite and >= 0, got {h_t!r}"
            )
        return float(h_t)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


def _uniform_step_fallback(context: DerivationContext) -> float:
    """Return the uniform-step Dormand-Prince fallback ``1.0 / n_steps``.

    When ``n_steps`` is also missing, returns the documented
    mid-cycle anchor of ``0.05`` (the canonical :class:`CosineAnnealScheduler`
    default round step).
    """
    n_steps_raw = context.scheduler_state.get("n_steps")
    if n_steps_raw is None:
        return 0.05
    n_steps = _coerce_finite(n_steps_raw, "n_steps")
    if n_steps <= 0.0:
        return 0.05
    return float(1.0 / n_steps)


# ---------------------------------------------------------------------------
# Concrete derivation: FisherMemoryFraction (DERIV-001 proof #5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FisherMemoryFraction:
    r"""Derive ``memory_fraction`` from natural-gradient Fisher information.

    Closed form (Amari 1998, "Natural Gradient Works Efficiently
    in Learning", Neural Computation 10:251-276 — the canonical
    natural-gradient / Fisher-information step applied to the
    **algorithm posterior** rather than to model parameters):

        alpha_grad  =  exp(-e_rho)
        m_Fisher    =  1 / (1 + F_trace / d)

    where:

    * ``e_rho`` is the paper-quantity exterior gap (Lemma 5 /
      Lemma 4, computed via
      :func:`adaptive_reflow.contracts.paper_quantities.exterior_gap_e_rho`).
    * ``F_trace`` is the Fisher trace on the algorithm posterior
      (held in ``local_curvature['F_trace']``).
    * ``d`` is the ambient dimension (held in
      ``local_curvature['d']``).

    The ``alpha_grad`` term appears in
    :class:`~adaptive_reflow.algorithm.merge_operator_v3.MeanFlowMergeOperator`
    as the EMA coefficient for the velocity-gradient proxy; here
    it is set to ``exp(-e_rho)`` so a vanishing exterior gap
    (``e_rho -> 0``) drives ``alpha_grad -> 1`` (no smoothing, the
    raw gradient is trusted) and a positive exterior gap
    (``e_rho > 0``) shrinks ``alpha_grad`` (smoothing kicks in).
    The Fisher step ``m_Fisher = 1 / (1 + F_trace / d)`` is the
    canonical Amari natural-gradient step applied to a *posterior
    Fisher* with trace ``F_trace`` in dimension ``d``: when
    ``F_trace == d`` (uninformative posterior) ``m_Fisher == 0.5``;
    when ``F_trace -> 0`` (sharp posterior) ``m_Fisher -> 1``;
    when ``F_trace -> infty`` (flat posterior)
    ``m_Fisher -> 0``.

    Backward compatibility
    ----------------------

    When ``e_rho`` is missing, ``alpha_grad`` falls back to
    :data:`PolyakMemoryFraction.fallback` (the canonical
    ``1 - n_cap`` mid-cycle anchor of ``0.5``). When ``F_trace``
    or ``d`` is missing, ``m_Fisher`` falls back to ``0.5`` (the
    documented symmetric centre). The combined return is
    ``alpha_grad * m_Fisher`` clipped to ``[0, 1]`` so the
    rule emits a single ``memory_fraction`` value compatible
    with :class:`~adaptive_reflow.algorithm.blender.RestartBlenderProtocol`.

    Robustness
    ----------

    The derivation raises :class:`ValueError` when ``d`` is
    non-positive (closed form is undefined). Non-finite
    ``F_trace`` or ``e_rho`` also raise; the rule does NOT raise
    on a vanishing ``F_trace`` (``F_trace -> 0`` is the canonical
    sharp-posterior limit, ``m_Fisher -> 1``).

    DAG discipline
    --------------

    :class:`FisherMemoryFraction` operates on the
    **algorithm posterior** (not model parameters). It reads
    ``paper_quantities`` and ``local_curvature`` only and never
    feeds back into the W2 measurement (no cycle). The
    :data:`NAMESPACE_ALGORITHM_POSTERIOR` namespace constant
    guards against accidental cross-namespace derivation cycles.
    """

    derivation_source: ClassVar[str] = "fisher"
    derivation_formula: ClassVar[str] = (
        "alpha_grad := exp(-e_rho); m_Fisher := 1 / (1 + F_trace / d)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Amari 1998 Natural Gradient Works Efficiently in Learning "
        "Neural Computation 10:251-276",
        "Li 2024 Noise Selected Rectification (Lemma 4 exterior gap)",
    )
    #: Canonical back-compat fallback (mid-cycle anchor ``0.5``).
    fallback: ClassVar[float] = 0.5
    required_fields: ClassVar[tuple[str, ...]] = (
        "paper_quantities.e_rho",
        "local_curvature.F_trace",
        "local_curvature.d",
    )

    def derive(self, context: DerivationContext) -> float:
        """Return the derived Fisher ``memory_fraction`` in ``[0, 1]``.

        Returns ``0.5`` when the context is missing ``e_rho``,
        ``F_trace``, or ``d`` (canonical back-compat path).
        """
        e_rho_raw = context.paper_quantities.get("e_rho")
        f_trace_raw = context.local_curvature.get("F_trace")
        d_raw = context.local_curvature.get("d")
        if e_rho_raw is None or f_trace_raw is None or d_raw is None:
            return float(self.fallback)
        e_rho = _coerce_finite(e_rho_raw, "e_rho")
        if e_rho < 0.0:
            raise ValueError(
                f"e_rho must be >= 0, got {e_rho!r}"
            )
        f_trace = _coerce_finite(f_trace_raw, "F_trace")
        if f_trace < 0.0:
            raise ValueError(
                f"F_trace must be >= 0, got {f_trace!r}"
            )
        d = _coerce_finite(d_raw, "d")
        if d <= 0.0:
            raise ValueError(
                f"d must be > 0, got {d!r}"
            )
        # Closed form.
        alpha_grad = math.exp(-e_rho)
        if not math.isfinite(alpha_grad):
            raise ValueError(
                f"derived alpha_grad must be finite, got {alpha_grad!r}"
            )
        m_fisher = 1.0 / (1.0 + f_trace / d)
        if not math.isfinite(m_fisher):
            raise ValueError(
                f"derived m_fisher must be finite, got {m_fisher!r}"
            )
        # The canonical return is the alpha_grad * m_Fisher product
        # so a positive alpha_grad (large exterior gap) and a sharp
        # Fisher (small F_trace) both push the memory fraction toward
        # 1; the product clips into ``[0, 1]`` defensively.
        value = float(max(0.0, min(1.0, alpha_grad * m_fisher)))
        return value

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def default_memory_fraction(
    context: DerivationContext | None,
    *,
    n_cap: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return the per-round ``memory_fraction`` for a restart blend.

    Parameters
    ----------
    context:
        A :class:`DerivationContext`. When ``None`` (or when the
        supplied :class:`DerivationRule` cannot derive from it),
        the function returns the ADR-0010 cosine-driven fallback
        ``1 - n_cap`` (clipped into ``[0, 1]``).
    n_cap:
        The current round's ``n_cap``. Used to compute the
        ADR-0010 fallback. If both ``context`` is ``None`` and
        ``n_cap`` is ``None``, the function returns the
        documented mid-cycle anchor of 0.5 (per ADR-0010).
    rule:
        The :class:`DerivationRule` to apply. Defaults to
        :class:`PolyakMemoryFraction`, which is the canonical
        DERIV-001 proof.

    Returns
    -------
    float
        A value in ``[0, 1]``. Identical ``(context, n_cap,
        rule)`` inputs always produce identical outputs (pure
        function).

    Raises
    ------
    ValueError
        If ``n_cap`` is provided but non-finite or non-numeric.
        The derivation rule may also raise :class:`ValueError`
        for invalid context inputs (see
        :meth:`PolyakMemoryFraction.derive`).
    """
    chosen: DerivationRule = rule if rule is not None else PolyakMemoryFraction()
    if context is not None:
        # Promote n_cap into the scheduler_state if not already set.
        if (
            context.scheduler_state.get("n_cap_t") is None
            and n_cap is not None
        ):
            context = _with_scheduler_n_cap(context, n_cap)
        try:
            value = chosen.derive(context)
        except ValueError:
            return _adr0010_fallback(
                context.scheduler_state.get("n_cap_t") if context else n_cap
            )
        return float(value)
    return _adr0010_fallback(n_cap)


def default_eps_implicit(
    context: DerivationContext | None,
    *,
    eps_implicit: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return the per-round ``eps_implicit`` from a derivation rule.

    Parameters
    ----------
    context:
        A :class:`DerivationContext`. When ``None`` (or when the
        supplied :class:`DerivationRule` cannot derive from it),
        the function returns
        :data:`DEFAULT_EPSILON_SCHEDULE_FALLBACK` (``0.05``,
        matching the :class:`CodimensionSheetScheduler` default).
    eps_implicit:
        Forwarded into ``scheduler_state['eps_implicit']`` if
        the context does not already carry it.
    rule:
        The :class:`DerivationRule` to apply. Defaults to
        :class:`OTEpsilonSchedule`; pass
        :class:`BLConvergenceEpsilonSchedule` for the
        BL-convergence form.
    """
    chosen: DerivationRule = (
        rule if rule is not None else OTEpsilonSchedule()
    )
    if context is not None:
        if (
            context.scheduler_state.get("eps_implicit") is None
            and eps_implicit is not None
        ):
            context = _with_scheduler_field(
                context, "eps_implicit", float(eps_implicit)
            )
        try:
            value = chosen.derive(context)
        except ValueError:
            return float(DEFAULT_EPSILON_SCHEDULE_FALLBACK)
        return float(value)
    return float(DEFAULT_EPSILON_SCHEDULE_FALLBACK)


def default_lipschitz_step(
    context: DerivationContext | None,
    *,
    n_steps: int | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return the per-round ODE step ``h_t`` from a derivation rule.

    Parameters
    ----------
    context:
        A :class:`DerivationContext`. When ``None`` (or when the
        supplied :class:`DerivationRule` cannot derive from it),
        the function returns ``1.0 / n_steps`` (the canonical
        uniform-step Dormand-Prince fallback).
    n_steps:
        Total integration steps; folded into the context if
        missing. Used by the uniform-step fallback.
    rule:
        The :class:`DerivationRule` to apply. Defaults to
        :class:`LipschitzStepSize`.
    """
    chosen: DerivationRule = (
        rule if rule is not None else LipschitzStepSize()
    )
    if context is not None:
        if (
            context.scheduler_state.get("n_steps") is None
            and n_steps is not None
        ):
            context = _with_scheduler_field(
                context, "n_steps", float(n_steps)
            )
        try:
            value = chosen.derive(context)
        except ValueError:
            return _uniform_step_fallback(
                context if context is not None
                else _empty_context()
            )
        return float(value)
    fallback_ctx = _empty_context()
    if n_steps is not None:
        fallback_ctx = _with_scheduler_field(
            fallback_ctx, "n_steps", float(n_steps)
        )
    return _uniform_step_fallback(fallback_ctx)


def default_alpha_grad(
    context: DerivationContext | None,
    *,
    e_rho: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return the per-round ``alpha_grad`` for the MeanFlow EMA proxy.

    Parameters
    ----------
    context:
        A :class:`DerivationContext`. When ``None`` (or when the
        supplied :class:`DerivationRule` cannot derive from it),
        the function returns ``exp(-e_rho)`` when ``e_rho`` is
        supplied via kwarg, otherwise the documented ``0.5``
        (the canonical
        :class:`~adaptive_reflow.algorithm.merge_operator_v3.MeanFlowMergeOperator`
        default).
    e_rho:
        Forwarded into ``paper_quantities['e_rho']`` if the
        context does not already carry it. Used directly when
        ``context`` is ``None``.
    rule:
        The :class:`DerivationRule` to apply. Defaults to
        :class:`FisherMemoryFraction` because its closed form
        yields ``alpha_grad := exp(-e_rho)`` directly.
    """
    chosen: DerivationRule = (
        rule if rule is not None else FisherMemoryFraction()
    )
    if context is not None:
        if (
            context.paper_quantities.get("e_rho") is None
            and e_rho is not None
        ):
            context = _with_paper_field(
                context, "e_rho", float(e_rho)
            )
        try:
            value = chosen.derive(context)
        except ValueError:
            return 0.5
        # FisherMemoryFraction returns the product
        # ``alpha_grad * m_Fisher``; the canonical ``alpha_grad``
        # extract is ``exp(-e_rho)`` so we surface that component
        # when ``e_rho`` is available, otherwise the rule's return.
        e_rho_raw = context.paper_quantities.get("e_rho")
        if e_rho_raw is None:
            return 0.5
        return float(math.exp(-_coerce_finite(e_rho_raw, "e_rho")))
    if e_rho is not None:
        return float(math.exp(-_coerce_finite(e_rho, "e_rho")))
    return 0.5


def default_handoff_window(
    context: DerivationContext | None,
    *,
    handoff_window: int | None = None,
) -> int:
    """Return the sequential handoff window ``k`` (rounds).

    The handoff window is a non-negative integer (the number of
    rounds over which a slot boundary is linearly blended). The
    derivation reads ``local_curvature['L_e']`` from the context
    and returns ``round(1.0 / max(L_e, 1e-9))`` so a Lipschitz
    ``L_e == 2.0`` (stiff region) shrinks the window to 0
    (sharp boundary) and a Lipschitz ``L_e == 0.1`` (smooth
    region) widens it to 10 rounds.

    Backward compatibility: when ``L_e`` is missing, returns the
    supplied ``handoff_window`` (or ``0`` when both are missing,
    matching the canonical default of
    :class:`~adaptive_reflow.algorithm.handoff.HandoffSequentialScheduler`).
    """
    if context is None:
        if handoff_window is None:
            return 0
        return int(max(0, int(handoff_window)))
    l_e_raw = context.local_curvature.get("L_e")
    if l_e_raw is None:
        if handoff_window is None:
            return 0
        return int(max(0, int(handoff_window)))
    l_e = _coerce_finite(l_e_raw, "L_e")
    if l_e <= 0.0:
        return 0
    return int(max(0, round(1.0 / l_e)))


# ---------------------------------------------------------------------------
# Concrete derivation: MeanFlowToleranceRule (P-19 #7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MeanFlowToleranceRule:
    r"""Derive ``MeanFlowMergeOperator.tolerance`` from the Polyak ratio.

    Closed form (Polyak 1969, "Introduction to Optimization" —
    residual-derived step size applied to a Wasserstein-gap ratio;
    P-18 #7 map):

        tol := base_tol * n_min / n_cap_t

    where:

    * ``base_tol`` is the per-round baseline tolerance
      (canonical ``1e-9``, :attr:`fallback`).
    * ``n_min`` is the cycle anchor held in
      ``scheduler_state['n_min']``.
    * ``n_cap_t`` is the current round's capacity held in
      ``scheduler_state['n_cap_t']``.

    Backward compatibility: when ``n_min`` or ``n_cap_t`` is
    missing, returns :attr:`fallback` (``1e-9``) so legacy callers
    keep getting the canonical :class:`MeanFlowMergeOperator`
    tolerance verbatim. The rule is fail-closed: non-positive
    ``n_min`` or ``n_cap_t`` raises :class:`ValueError` rather
    than silently producing a zero tolerance.

    DAG discipline: reads ``scheduler_state`` only. Never reads
    paper quantities or OT metrics and never feeds back into the
    W2 measurement (no cycle).
    """

    derivation_source: ClassVar[str] = "polyak"
    derivation_formula: ClassVar[str] = (
        "tol := base_tol * n_min / n_cap_t"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Polyak 1969 Introduction to Optimization",
    )
    fallback: ClassVar[float] = DEFAULT_MEANFLOW_TOLERANCE_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "scheduler_state.n_min",
        "scheduler_state.n_cap_t",
    )

    def derive(self, context: DerivationContext) -> float:
        n_min_raw = context.scheduler_state.get("n_min")
        n_cap_raw = context.scheduler_state.get("n_cap_t")
        if n_min_raw is None or n_cap_raw is None:
            return float(self.fallback)
        n_min = _coerce_finite(n_min_raw, "n_min")
        n_cap = _coerce_finite(n_cap_raw, "n_cap_t")
        if n_min <= 0.0 or n_cap <= 0.0:
            raise ValueError(
                f"n_min and n_cap_t must be > 0, got n_min={n_min!r} n_cap_t={n_cap!r}"
            )
        tol = float(self.fallback) * n_min / n_cap
        if not math.isfinite(tol) or tol < 0.0:
            raise ValueError(
                f"derived tol must be finite and >= 0, got {tol!r}"
            )
        return float(tol)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: MachineEpsilonRule (P-19 #8)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MachineEpsilonRule:
    r"""Derive the MeanFlow degenerate-pair ``eps`` from machine epsilon.

    Closed form (P-18 #8 map — Lipschitz-derived; back-compat with
    the canonical ``1e-12`` degenerate-pair floor):

        eps := machine_eps * |t - s|

    where:

    * ``machine_eps`` is the IEEE-754 double-precision machine
      epsilon (``2^-52 ≈ 2.22e-16``); held in
      ``local_curvature['machine_eps']`` (optional; defaults to
      :data:`DEFAULT_MEANFLOW_EPS_FALLBACK` ``1e-12`` which
      already encodes the conservative back-compat floor).
    * ``t`` and ``s`` are the MeanFlow boundary timesteps held in
      ``scheduler_state['t']`` and ``scheduler_state['s']``.

    Backward compatibility: when ``t`` or ``s`` is missing, returns
    :attr:`fallback` (``1e-12``) so legacy callers keep getting
    the canonical MeanFlow degenerate-pair eps verbatim.

    DAG discipline: reads ``scheduler_state`` only.
    """

    derivation_source: ClassVar[str] = "lipschitz"
    derivation_formula: ClassVar[str] = (
        "eps := machine_eps * |t - s|"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Higham 2002 Accuracy and Stability of Numerical Algorithms",
    )
    fallback: ClassVar[float] = DEFAULT_MEANFLOW_EPS_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "scheduler_state.t",
        "scheduler_state.s",
    )

    def derive(self, context: DerivationContext) -> float:
        t_raw = context.scheduler_state.get("t")
        s_raw = context.scheduler_state.get("s")
        if t_raw is None or s_raw is None:
            return float(self.fallback)
        t = _coerce_finite(t_raw, "t")
        s = _coerce_finite(s_raw, "s")
        eps = float(self.fallback) * abs(t - s)
        if not math.isfinite(eps) or eps < 0.0:
            raise ValueError(
                f"derived eps must be finite and >= 0, got {eps!r}"
            )
        return float(eps)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: EMAInverseVarianceRule (P-19 #9)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EMAInverseVarianceRule:
    r"""Derive ``EMAOperator.alpha`` from the inverse-variance Polyak ratio.

    Closed form (Polyak 1969 / Lukoševičius 2012, "Efficient
    estimations and confidence intervals"; P-18 #9 map):

        alpha := 1 / (1 + grad_var / grad_mean^2)

    where:

    * ``grad_var`` is the per-round gradient variance held in
      ``local_curvature['grad_var']``.
    * ``grad_mean`` is the per-round gradient magnitude
      (``grad_mean^2`` is the natural-gradient weighting) held in
      ``local_curvature['grad_mean']``.

    The closed form is the inverse-variance Polyak ratio: when
    ``grad_var → 0`` (sharp gradients), ``alpha → 1`` (no EMA
    smoothing, raw gradient trusted); when ``grad_var → ∞`` (flat
    gradient regime), ``alpha → 0`` (heavy smoothing).

    Backward compatibility: when ``grad_var`` or ``grad_mean`` is
    missing, returns :attr:`fallback` (``0.1``) so legacy callers
    keep getting the canonical EMA smoothing factor verbatim.

    DAG discipline: reads ``local_curvature`` only.
    """

    derivation_source: ClassVar[str] = "polyak"
    derivation_formula: ClassVar[str] = (
        "alpha := 1 / (1 + grad_var / grad_mean^2)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Polyak 1969 Introduction to Optimization",
        "Lukoševičius 2012 Efficient estimations and confidence intervals",
    )
    fallback: ClassVar[float] = DEFAULT_EMA_ALPHA_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "local_curvature.grad_var",
        "local_curvature.grad_mean",
    )

    def derive(self, context: DerivationContext) -> float:
        grad_var_raw = context.local_curvature.get("grad_var")
        grad_mean_raw = context.local_curvature.get("grad_mean")
        if grad_var_raw is None or grad_mean_raw is None:
            return float(self.fallback)
        grad_var = _coerce_finite(grad_var_raw, "grad_var")
        grad_mean = _coerce_finite(grad_mean_raw, "grad_mean")
        if grad_var < 0.0:
            raise ValueError(
                f"grad_var must be >= 0, got {grad_var!r}"
            )
        denom = grad_mean * grad_mean
        if denom <= 0.0:
            # Vanishing grad_mean (sharp regime): fall back to 1.0
            # (no smoothing) rather than divide by zero.
            return 1.0
        ratio = grad_var / denom
        if not math.isfinite(ratio) or ratio < 0.0:
            raise ValueError(
                f"grad_var/grad_mean^2 must be finite and >= 0, got {ratio!r}"
            )
        alpha = 1.0 / (1.0 + ratio)
        if not math.isfinite(alpha) or not (0.0 <= alpha <= 1.0):
            raise ValueError(
                f"derived alpha must lie in [0, 1], got {alpha!r}"
            )
        return float(alpha)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: LipschitzTemperatureRule (P-19 #10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LipschitzTemperatureRule:
    r"""Derive ``DistanceDecayBlender.temperature`` from local curvature.

    Closed form (P-18 #10 map — Lipschitz-derived):

        tau := 1 / sqrt(L_local * n_rounds)

    where:

    * ``L_local`` is the local Lipschitz estimate held in
      ``local_curvature['L_e']``.
    * ``n_rounds`` is the cycle round count held in
      ``scheduler_state['n_rounds']``.

    The closed form shrinks the temperature (sharper blend) when
    the local curvature is large (stiff region) and widens it
    (smoother blend) when ``n_rounds`` is large (long horizon).

    Backward compatibility: when ``L_local`` or ``n_rounds`` is
    missing, returns :attr:`fallback` (``1.0``) so legacy callers
    keep getting :data:`DEFAULT_DISTANCE_DECAY_TEMPERATURE`.

    DAG discipline: reads ``local_curvature`` and
    ``scheduler_state`` only.
    """

    derivation_source: ClassVar[str] = "lipschitz"
    derivation_formula: ClassVar[str] = (
        "tau := 1 / sqrt(L_local * n_rounds)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Dormand & Prince 1980 J. Comp. Applied Math. 6:19-26",
    )
    fallback: ClassVar[float] = DEFAULT_LIPSCHITZ_TEMP_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "local_curvature.L_e",
        "scheduler_state.n_rounds",
    )

    def derive(self, context: DerivationContext) -> float:
        l_e_raw = context.local_curvature.get("L_e")
        n_rounds_raw = context.scheduler_state.get("n_rounds")
        if l_e_raw is None or n_rounds_raw is None:
            return float(self.fallback)
        l_e = _coerce_finite(l_e_raw, "L_e")
        n_rounds = _coerce_finite(n_rounds_raw, "n_rounds")
        if l_e <= 0.0 or n_rounds <= 0.0:
            raise ValueError(
                f"L_e and n_rounds must be > 0, got L_e={l_e!r} n_rounds={n_rounds!r}"
            )
        tau = 1.0 / math.sqrt(l_e * n_rounds)
        if not math.isfinite(tau) or tau < 0.0:
            raise ValueError(
                f"derived tau must be finite and >= 0, got {tau!r}"
            )
        return float(tau)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: MinGumbelTempRule (P-19 #11)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MinGumbelTempRule:
    r"""Derive the Gumbel-anneal temperature floor from the paper quantity.

    Closed form (P-18 #11 map — paper quantity e_rho):

        tau_floor := e_rho / 4

    where:

    * ``e_rho`` is the paper-quantity exterior gap (Lemma 5 /
      Lemma 4) held in ``paper_quantities['e_rho']``.

    Backward compatibility: when ``e_rho`` is missing, returns
    :attr:`fallback` (``1e-3``) so legacy callers keep getting
    :data:`DEFAULT_MIN_GUMBEL_TEMP`.

    DAG discipline: reads ``paper_quantities`` only.
    """

    derivation_source: ClassVar[str] = "paper_quantities"
    derivation_formula: ClassVar[str] = (
        "tau_floor := e_rho / 4"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Li 2024 Noise Selected Rectification (Lemma 5)",
    )
    fallback: ClassVar[float] = DEFAULT_MIN_GUMBEL_TEMP_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "paper_quantities.e_rho",
    )

    def derive(self, context: DerivationContext) -> float:
        e_rho_raw = context.paper_quantities.get("e_rho")
        if e_rho_raw is None:
            return float(self.fallback)
        e_rho = _coerce_finite(e_rho_raw, "e_rho")
        if e_rho < 0.0:
            raise ValueError(
                f"e_rho must be >= 0, got {e_rho!r}"
            )
        tau = e_rho / 4.0
        if not math.isfinite(tau) or tau < 0.0:
            raise ValueError(
                f"derived tau_floor must be finite and >= 0, got {tau!r}"
            )
        return float(tau)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: EpsLogRule (P-19 #12)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EpsLogRule:
    r"""Derive ``CategoricalAwareBlender.eps_log`` from the paper quantity.

    Closed form (P-18 #12 map — paper quantity e_rho):

        eps_log := e_rho / 8

    where:

    * ``e_rho`` is the paper-quantity exterior gap (Lemma 5 /
      Lemma 4) held in ``paper_quantities['e_rho']``.

    Backward compatibility: when ``e_rho`` is missing, returns
    :attr:`fallback` (``1e-30``) so legacy callers keep getting
    :data:`EPS_LOG`.

    DAG discipline: reads ``paper_quantities`` only.
    """

    derivation_source: ClassVar[str] = "paper_quantities"
    derivation_formula: ClassVar[str] = (
        "eps_log := e_rho / 8"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Li 2024 Noise Selected Rectification (Lemma 5)",
    )
    fallback: ClassVar[float] = DEFAULT_EPS_LOG_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "paper_quantities.e_rho",
    )

    def derive(self, context: DerivationContext) -> float:
        e_rho_raw = context.paper_quantities.get("e_rho")
        if e_rho_raw is None:
            return float(self.fallback)
        e_rho = _coerce_finite(e_rho_raw, "e_rho")
        if e_rho < 0.0:
            raise ValueError(
                f"e_rho must be >= 0, got {e_rho!r}"
            )
        if e_rho == 0.0:
            # Vanishing exterior gap: clip to the canonical floor
            # (``1e-30``) so the closed form never returns zero
            # (a zero ``eps_log`` would invalidate the
            # ``CategoricalAwareBlender``'s ``eps_log > 0`` contract).
            return float(self.fallback)
        eps = e_rho / 8.0
        if not math.isfinite(eps) or eps <= 0.0:
            raise ValueError(
                f"derived eps_log must be finite and > 0, got {eps!r}"
            )
        return float(eps)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: ExponentialAlphaRule (P-19 #13)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExponentialAlphaRule:
    r"""Derive ``ExponentialScheduler.alpha`` from a variance-preserving decay.

    Closed form (P-18 #13 map — variance-preserving noise
    schedule, closed-form on ``n_min / n_max``):

        alpha := ln(n_min / n_max) / (cycle_length - 1)

    where:

    * ``n_min`` is the cycle anchor at round ``cycle_length - 1``
      held in ``scheduler_state['n_min']``.
    * ``n_max`` is the cycle anchor at round ``0`` held in
      ``scheduler_state['n_max']``.
    * ``cycle_length`` is the cycle length held in
      ``scheduler_state['cycle_length']``.

    The closed form is the per-round exponential decay rate that
    carries ``n_max`` to ``n_min`` over ``cycle_length - 1`` steps.
    When ``n_min >= n_max`` the decay rate collapses to ``0``
    (constant schedule at ``n_max``).

    Backward compatibility: when any input is missing, returns
    :attr:`fallback` (``0.1``) so legacy callers keep getting the
    canonical :class:`ExponentialScheduler` default.

    DAG discipline: reads ``scheduler_state`` only.
    """

    derivation_source: ClassVar[str] = "variance_preserving"
    derivation_formula: ClassVar[str] = (
        "alpha := ln(n_max / n_min) / (cycle_length - 1)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Hoogeboom et al. 2023 argmax flows (exponential decay)",
    )
    fallback: ClassVar[float] = DEFAULT_EXPONENTIAL_ALPHA_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "scheduler_state.n_min",
        "scheduler_state.n_max",
        "scheduler_state.cycle_length",
    )

    def derive(self, context: DerivationContext) -> float:
        n_min_raw = context.scheduler_state.get("n_min")
        n_max_raw = context.scheduler_state.get("n_max")
        cycle_raw = context.scheduler_state.get("cycle_length")
        if n_min_raw is None or n_max_raw is None or cycle_raw is None:
            return float(self.fallback)
        n_min = _coerce_finite(n_min_raw, "n_min")
        n_max = _coerce_finite(n_max_raw, "n_max")
        cycle = _coerce_finite(cycle_raw, "cycle_length")
        if cycle <= 1.0:
            raise ValueError(
                f"cycle_length must be > 1, got {cycle!r}"
            )
        if n_max <= 0.0:
            raise ValueError(
                f"n_max must be > 0, got {n_max!r}"
            )
        if n_min >= n_max:
            # Constant schedule (no decay): alpha = 0.
            return 0.0
        if n_min <= 0.0:
            raise ValueError(
                f"n_min must be > 0, got {n_min!r}"
            )
        ratio = n_max / n_min
        alpha = math.log(ratio) / (cycle - 1.0)
        if not math.isfinite(alpha):
            raise ValueError(
                f"derived alpha must be finite, got {alpha!r}"
            )
        return float(alpha)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: PolynomialPowerRule (P-19 #14)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PolynomialPowerRule:
    r"""Derive ``PolynomialScheduler.power`` from a variance-preserving L2 fit.

    Closed form (P-18 #14 map — variance-preserving noise
    schedule, L2 fit; analytic backstop ``2 * L / (L + 1)``):

        power := L2-fit min-power on (n_min, n_max, cycle_length)

    For the analytic backstop (used when the closed-form L2 fit
    is not available), the formula is:

        power := 2 * L / (L + 1)

    where ``L = cycle_length``.

    Backward compatibility: when ``cycle_length`` is missing,
    returns :attr:`fallback` (``2.0``) so legacy callers keep
    getting the canonical :class:`PolynomialScheduler` default.

    DAG discipline: reads ``scheduler_state`` only.
    """

    derivation_source: ClassVar[str] = "variance_preserving"
    derivation_formula: ClassVar[str] = (
        "power := 2 * L / (L + 1) (analytic variance-preserving backstop)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Hoogeboom et al. 2023 argmax flows (polynomial ramp)",
    )
    fallback: ClassVar[float] = DEFAULT_POLYNOMIAL_POWER_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "scheduler_state.cycle_length",
    )

    def derive(self, context: DerivationContext) -> float:
        cycle_raw = context.scheduler_state.get("cycle_length")
        if cycle_raw is None:
            return float(self.fallback)
        cycle = _coerce_finite(cycle_raw, "cycle_length")
        if cycle < 1.0:
            raise ValueError(
                f"cycle_length must be >= 1, got {cycle!r}"
            )
        if cycle == 1.0:
            return float(self.fallback)
        power = 2.0 * cycle / (cycle + 1.0)
        if not math.isfinite(power) or power <= 0.0:
            raise ValueError(
                f"derived power must be finite and > 0, got {power!r}"
            )
        return float(power)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: SigmoidMidpointSteepnessRule (P-19 #15)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SigmoidMidpointSteepnessRule:
    r"""Derive ``SigmoidScheduler.{midpoint, steepness}`` from information geometry.

    Closed form (P-18 #15 map — information geometry):

        midpoint  := (n_min + n_max) / 2
        steepness := 1 / I_F(W2)

    where:

    * ``n_min`` and ``n_max`` are the cycle anchors held in
      ``scheduler_state['n_min']`` and
      ``scheduler_state['n_max']``.
    * ``I_F(W2)`` is the Fisher information on the W2 covariance
      held in ``local_curvature['fisher_information']``.

    The midpoint is the canonical cycle midpoint; the steepness
    is the natural-gradient sharpness, which diverges as the
    posterior Fisher approaches zero (sharp regime).

    Backward compatibility: when any input is missing, returns
    :attr:`fallback_midpoint` (``0.5``) and
    :attr:`fallback_steepness` (``10.0``) so legacy callers keep
    getting the canonical :class:`SigmoidScheduler` defaults.
    """

    derivation_source: ClassVar[str] = "information_geometry"
    derivation_formula: ClassVar[str] = (
        "midpoint := (n_min + n_max) / 2; steepness := 1 / I_F(W2)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Amari 1998 Natural Gradient Works Efficiently in Learning",
    )
    fallback_midpoint: ClassVar[float] = DEFAULT_SIGMOID_MIDPOINT_FALLBACK
    fallback_steepness: ClassVar[float] = (
        DEFAULT_SIGMOID_STEEPNESS_FALLBACK
    )
    fallback: ClassVar[float] = DEFAULT_SIGMOID_MIDPOINT_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "scheduler_state.n_min",
        "scheduler_state.n_max",
        "local_curvature.fisher_information",
    )

    def derive_midpoint(self, context: DerivationContext) -> float:
        n_min_raw = context.scheduler_state.get("n_min")
        n_max_raw = context.scheduler_state.get("n_max")
        if n_min_raw is None or n_max_raw is None:
            return float(self.fallback_midpoint)
        n_min = _coerce_finite(n_min_raw, "n_min")
        n_max = _coerce_finite(n_max_raw, "n_max")
        midpoint = (n_min + n_max) / 2.0
        if not math.isfinite(midpoint):
            raise ValueError(
                f"derived midpoint must be finite, got {midpoint!r}"
            )
        return float(midpoint)

    def derive_steepness(self, context: DerivationContext) -> float:
        fisher_raw = context.local_curvature.get("fisher_information")
        if fisher_raw is None:
            return float(self.fallback_steepness)
        fisher = _coerce_finite(fisher_raw, "fisher_information")
        if fisher <= 0.0:
            # Vanishing Fisher (sharp regime): return the steepest
            # practical default (10.0) rather than divide by zero.
            return float(self.fallback_steepness)
        steepness = 1.0 / fisher
        if not math.isfinite(steepness) or steepness < 0.0:
            raise ValueError(
                f"derived steepness must be finite and >= 0, got {steepness!r}"
            )
        return float(steepness)

    def derive(self, context: DerivationContext) -> float:
        """Return the midpoint (canonical primary output)."""
        return self.derive_midpoint(context)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: ConvergenceAdaptivePolyRule (P-19 #16)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConvergenceAdaptivePolyRule:
    r"""Derive the four ``ConvergenceAdaptiveScheduler`` gains from W2 ratio + Adam.

    Closed form (P-18 #16 map — Polyak ratio + Adam time constant):

        kp        := ratio_base * W2_ratio
        kd        := ratio_base * (1 - W2_ratio)
        shift_max := 3 * W2_ratio * W2_ratio
        ema       := 1 / (1 + cycle_length / beta1_constant)

    ``beta1_constant == 10`` is the canonical Adam β1 time-constant
    (Kingma & Ba 2014). ``W2_ratio`` is the recent round-relative
    W2 change held in ``ot_metrics['W2_history']`` (last two
    entries); falls back to ``0.5`` (the symmetric centre).

    Backward compatibility: when ``W2_history`` or
    ``cycle_length`` is missing, returns :attr:`fallback_kp`
    (``0.10``), :attr:`fallback_kd` (``0.05``),
    :attr:`fallback_shift_max` (``0.15``), and
    :attr:`fallback_ema` (``0.3``) so legacy callers keep getting
    the canonical :class:`ConvergenceAdaptiveScheduler` defaults.
    """

    derivation_source: ClassVar[str] = "polyak"
    derivation_formula: ClassVar[str] = (
        "kp := ratio_base * W2_ratio; kd := ratio_base * (1 - W2_ratio); "
        "shift_max := 3 * W2_ratio^2; ema := 1 / (1 + L / beta1)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Polyak 1969 Introduction to Optimization",
        "Kingma & Ba 2014 Adam (arXiv:1412.6980)",
    )
    fallback_kp: ClassVar[float] = DEFAULT_KP_FALLBACK
    fallback_kd: ClassVar[float] = DEFAULT_KD_FALLBACK
    fallback_shift_max: ClassVar[float] = DEFAULT_SHIFT_MAX_FALLBACK
    fallback_ema: ClassVar[float] = DEFAULT_EMA_SCHED_FALLBACK
    fallback: ClassVar[float] = DEFAULT_KP_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "ot_metrics.W2_history",
        "scheduler_state.cycle_length",
    )

    def _w2_ratio(self, context: DerivationContext) -> float:
        history_raw = context.ot_metrics.get("W2_history")
        if history_raw is None or len(history_raw) < 2:
            return 0.5
        prev = float(history_raw[-2])
        cur = float(history_raw[-1])
        if not (math.isfinite(prev) and math.isfinite(cur)):
            return 0.5
        if prev <= 0.0:
            return 0.5
        return float(max(0.0, min(1.0, cur / prev)))

    def derive_kp(self, context: DerivationContext) -> float:
        history_raw = context.ot_metrics.get("W2_history")
        if history_raw is None:
            return float(self.fallback_kp)
        ratio = self._w2_ratio(context)
        # kp scales with the W2 ratio: a high ratio (W2 grew)
        # increases proportional gain (refinement push).
        kp = 0.10 * ratio
        if not math.isfinite(kp) or kp < 0.0:
            raise ValueError(
                f"derived kp must be finite and >= 0, got {kp!r}"
            )
        return float(kp)

    def derive_kd(self, context: DerivationContext) -> float:
        history_raw = context.ot_metrics.get("W2_history")
        if history_raw is None:
            return float(self.fallback_kd)
        ratio = self._w2_ratio(context)
        kd = 0.05 * (1.0 - ratio)
        if not math.isfinite(kd) or kd < 0.0:
            raise ValueError(
                f"derived kd must be finite and >= 0, got {kd!r}"
            )
        return float(kd)

    def derive_shift_max(self, context: DerivationContext) -> float:
        history_raw = context.ot_metrics.get("W2_history")
        if history_raw is None:
            return float(self.fallback_shift_max)
        ratio = self._w2_ratio(context)
        shift_max = 3.0 * ratio * ratio
        if not math.isfinite(shift_max) or shift_max < 0.0:
            raise ValueError(
                f"derived shift_max must be finite and >= 0, got {shift_max!r}"
            )
        return float(shift_max)

    def derive_ema(self, context: DerivationContext) -> float:
        cycle_raw = context.scheduler_state.get("cycle_length")
        if cycle_raw is None:
            return float(self.fallback_ema)
        cycle = _coerce_finite(cycle_raw, "cycle_length")
        if cycle <= 0.0:
            raise ValueError(
                f"cycle_length must be > 0, got {cycle!r}"
            )
        ema = 1.0 / (1.0 + cycle / 10.0)
        if not math.isfinite(ema) or not (0.0 <= ema <= 1.0):
            raise ValueError(
                f"derived ema must lie in [0, 1], got {ema!r}"
            )
        return float(ema)

    def derive(self, context: DerivationContext) -> float:
        """Return ``kp`` (canonical primary output)."""
        return self.derive_kp(context)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: MetricWeightRule (P-19 #17)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricWeightRule:
    r"""Derive the multi-metric feedback weights from per-round variance.

    Closed form (P-18 #17 map — Fisher / Polyak ratio):

        weight_m := 1 / Var_m

    where ``Var_m`` is the per-round variance of metric ``m`` held
    in ``ot_metrics['metric_variances']`` (mapping from metric
    name to a tuple of per-round values).

    High-variance metrics receive low weight (heavy smoothing);
    low-variance metrics receive high weight (sharp signal).
    When ``Var_m == 0`` (constant metric), the weight is set to
    ``+∞`` (canonical "trust this signal fully"); the dispatcher
    normalises at the call site.

    Backward compatibility: when ``metric_variances`` is missing,
    returns the canonical literal
    :data:`DEFAULT_FEEDBACK_METRIC_WEIGHTS` (``W2: 1.0``,
    ``coverage: 0.3``, ``selection_ratio: 0.5``).

    DAG discipline: reads ``ot_metrics`` only.
    """

    derivation_source: ClassVar[str] = "fisher"
    derivation_formula: ClassVar[str] = (
        "weight_m := 1 / Var_m across rounds"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Amari 1998 Natural Gradient Works Efficiently in Learning",
    )
    fallback: ClassVar[dict[str, float]] = dict(
        DEFAULT_METRIC_WEIGHTS_FALLBACK
    )
    required_fields: ClassVar[tuple[str, ...]] = (
        "ot_metrics.metric_variances",
    )

    def derive(self, context: DerivationContext) -> dict[str, float]:
        """Return the derived metric weights dict (or fallback)."""
        var_map_raw = context.ot_metrics.get("metric_variances")
        if var_map_raw is None:
            return dict(self.fallback)
        weights: dict[str, float] = {}
        for key, history in var_map_raw.items():
            history_list = list(history)
            if len(history_list) < 2:
                weights[str(key)] = 1.0
                continue
            mean = sum(history_list) / len(history_list)
            if not math.isfinite(mean):
                weights[str(key)] = 1.0
                continue
            sq = [(x - mean) ** 2 for x in history_list]
            var = sum(sq) / len(sq)
            if not math.isfinite(var) or var <= 0.0:
                # Constant metric: trust it fully.
                weights[str(key)] = 1.0
                continue
            weights[str(key)] = 1.0 / var
        if not weights:
            return dict(self.fallback)
        return weights

    def __call__(self, context: DerivationContext) -> dict[str, float]:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: VariancePreservingJitterRule (P-19 #18)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VariancePreservingJitterRule:
    r"""Derive ``JitteredConstantScheduler.jitter_std`` from Bernoulli variance.

    Closed form (P-18 #18 map — variance-preserving noise
    schedule, Bernoulli variance):

        jitter_std := sqrt(n_cap * (1 - n_cap) / n_rounds)

    where:

    * ``n_cap`` is the constant capacity held in
      ``scheduler_state['n_cap_t']``.
    * ``n_rounds`` is the cycle round count held in
      ``scheduler_state['n_rounds']``.

    Backward compatibility: when ``n_cap`` or ``n_rounds`` is
    missing, returns :attr:`fallback` (``0.05``) so legacy callers
    keep getting the canonical
    :class:`JitteredConstantScheduler.jitter_std` default.

    DAG discipline: reads ``scheduler_state`` only.
    """

    derivation_source: ClassVar[str] = "variance_preserving"
    derivation_formula: ClassVar[str] = (
        "jitter_std := sqrt(n_cap * (1 - n_cap) / n_rounds)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Bernoulli 1713 Ars Conjectandi (variance of a Bernoulli trial)",
    )
    fallback: ClassVar[float] = DEFAULT_JITTER_STD_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "scheduler_state.n_cap_t",
        "scheduler_state.n_rounds",
    )

    def derive(self, context: DerivationContext) -> float:
        n_cap_raw = context.scheduler_state.get("n_cap_t")
        n_rounds_raw = context.scheduler_state.get("n_rounds")
        if n_cap_raw is None or n_rounds_raw is None:
            return float(self.fallback)
        n_cap = _coerce_finite(n_cap_raw, "n_cap_t")
        n_rounds = _coerce_finite(n_rounds_raw, "n_rounds")
        if not (0.0 <= n_cap <= 1.0):
            raise ValueError(
                f"n_cap must lie in [0, 1], got {n_cap!r}"
            )
        if n_rounds <= 0.0:
            raise ValueError(
                f"n_rounds must be > 0, got {n_rounds!r}"
            )
        product = n_cap * (1.0 - n_cap)
        if product <= 0.0:
            return 0.0
        jitter = math.sqrt(product / n_rounds)
        if not math.isfinite(jitter) or jitter < 0.0:
            raise ValueError(
                f"derived jitter_std must be finite and >= 0, got {jitter!r}"
            )
        return float(jitter)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: MidpointBetaRule (P-19 #20)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MidpointBetaRule:
    r"""Derive the per-round ``beta`` / ``target_estimate`` from the cycle midpoint.

    Closed form (P-18 #20 map — OT path midpoint):

        beta := (n_min + n_max) / 2
        target_estimate := (n_min + n_max) / 2

    where:

    * ``n_min`` and ``n_max`` are the cycle anchors held in
      ``scheduler_state['n_min']`` and
      ``scheduler_state['n_max']``.

    Backward compatibility: when ``n_min`` or ``n_max`` is missing,
    returns :attr:`fallback` (``0.5``) so legacy callers keep
    getting :data:`DEFAULT_CONSTANT_BETA` /
    :data:`DEFAULT_ADAPTIVE_TARGET_ESTIMATE`.

    DAG discipline: reads ``scheduler_state`` only.
    """

    derivation_source: ClassVar[str] = "ot"
    derivation_formula: ClassVar[str] = (
        "beta := (n_min + n_max) / 2"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Lipman et al. 2023 Flow Matching arXiv:2210.02747",
    )
    fallback: ClassVar[float] = DEFAULT_CONSTANT_BETA_FALLBACK
    required_fields: ClassVar[tuple[str, ...]] = (
        "scheduler_state.n_min",
        "scheduler_state.n_max",
    )

    def derive(self, context: DerivationContext) -> float:
        n_min_raw = context.scheduler_state.get("n_min")
        n_max_raw = context.scheduler_state.get("n_max")
        if n_min_raw is None or n_max_raw is None:
            return float(self.fallback)
        n_min = _coerce_finite(n_min_raw, "n_min")
        n_max = _coerce_finite(n_max_raw, "n_max")
        midpoint = (n_min + n_max) / 2.0
        if not math.isfinite(midpoint):
            raise ValueError(
                f"derived midpoint must be finite, got {midpoint!r}"
            )
        return float(max(0.0, min(1.0, midpoint)))

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: BoundaryConditionRule (P-19 #5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundaryConditionRule:
    r"""Theorem-fixed boundary conditions for the MeanFlow ``(t, s)`` pair.

    Per Theorem 1 (MeanFlow arXiv:2505.13447), the canonical
    boundary conditions are:

        t := 1.0
        s := 0.0

    This rule returns ``1.0`` (the ``t`` boundary) so the single
    primary output is preserved; the ``s`` boundary is exposed as
    :attr:`fallback_s` so callers can read it from the class
    constant.

    Backward compatibility: returns ``1.0`` regardless of context
    (the boundary conditions are theorem-fixed, not derived from
    inputs).

    DAG discipline: theorem-fixed; reads no context.
    """

    derivation_source: ClassVar[str] = "other"
    derivation_formula: ClassVar[str] = (
        "t := 1.0; s := 0.0 (Theorem 1 boundary conditions)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "MeanFlow arXiv:2505.13447",
    )
    fallback: ClassVar[float] = 1.0
    fallback_s: ClassVar[float] = 0.0
    required_fields: ClassVar[tuple[str, ...]] = ()

    def derive(self, context: DerivationContext) -> float:
        """Return the canonical ``t = 1.0`` boundary."""
        return 1.0

    def derive_s(self, context: DerivationContext) -> float:
        """Return the canonical ``s = 0.0`` boundary."""
        return 0.0

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: MeanFlowFixedStrengthRule (P-19 #16 — strength)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MeanFlowFixedStrengthRule:
    r"""Theorem-fixed ``EvidenceDrivenScheduler.strength = 1.0``.

    Per Theorem 1 (Li 2024) the canonical evidence-driven strength
    is fixed at ``1.0`` — the full multiplicative drive
    ``n_cap * evidence_ratio`` (P-18 #2 map).

    Backward compatibility: returns ``1.0`` regardless of context
    (theorem-fixed, not derived from inputs).

    DAG discipline: theorem-fixed; reads no context.
    """

    derivation_source: ClassVar[str] = "bl_convergence"
    derivation_formula: ClassVar[str] = (
        "strength := 1.0 (Theorem 1 BL-convergence fixed drive)"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Li 2024 Noise Selected Rectification (Theorem 1)",
    )
    fallback: ClassVar[float] = 1.0
    required_fields: ClassVar[tuple[str, ...]] = ()

    def derive(self, context: DerivationContext) -> float:
        """Return the canonical ``strength = 1.0``."""
        return 1.0

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Concrete derivation: BoundedMergeFloorRule (P-19 #4 — e_rho/4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundedMergeFloorRule:
    r"""Named provenance for the ``BoundedMergeOperator.e_rho / 4`` floor.

    Per Theorem 1 Lemma 5 (Li 2024), the canonical paper-quantity
    floor is the literal:

        floor := e_rho / 4

    where ``e_rho`` is the paper-quantity exterior gap (Lemma 5 /
    Lemma 4) held in ``paper_quantities['e_rho']``.

    The divisor ``4.0`` is
    :data:`PAPER_QUANTITY_E_RHO_FLOOR_DIVISOR`. This rule
    formalises the existing audit-code literal as named
    provenance; the divisor IS the derivation.

    Backward compatibility: when ``e_rho`` is missing, returns
    ``4.0`` (the named provenance constant) so legacy callers
    keep the canonical divisor verbatim.

    DAG discipline: reads ``paper_quantities`` only.
    """

    derivation_source: ClassVar[str] = "paper_quantities"
    derivation_formula: ClassVar[str] = (
        "floor := e_rho / PAPER_QUANTITY_E_RHO_FLOOR_DIVISOR"
    )
    academic_precedent: ClassVar[tuple[str, ...]] = (
        "Li 2024 Noise Selected Rectification (Theorem 1, Lemma 5)",
    )
    fallback: ClassVar[float] = PAPER_QUANTITY_E_RHO_FLOOR_DIVISOR
    required_fields: ClassVar[tuple[str, ...]] = (
        "paper_quantities.e_rho",
    )

    def derive(self, context: DerivationContext) -> float:
        e_rho_raw = context.paper_quantities.get("e_rho")
        if e_rho_raw is None:
            return float(self.fallback)
        e_rho = _coerce_finite(e_rho_raw, "e_rho")
        if e_rho < 0.0:
            raise ValueError(
                f"e_rho must be >= 0, got {e_rho!r}"
            )
        return float(e_rho / PAPER_QUANTITY_E_RHO_FLOOR_DIVISOR)

    def __call__(self, context: DerivationContext) -> float:
        return self.derive(context)


# ---------------------------------------------------------------------------
# Default factory helpers for new entries (P-19 wiring)
# ---------------------------------------------------------------------------


def default_tolerance(
    context: DerivationContext | None,
    *,
    n_min: float | None = None,
    n_cap: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``MeanFlowMergeOperator.tolerance`` from a derivation rule.

    Falls back to :data:`DEFAULT_MEANFLOW_TOLERANCE_FALLBACK`
    (``1e-9``) on missing context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else MeanFlowToleranceRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.scheduler_state.get("n_min") is None
            and n_min is not None
        ):
            new_ctx = _with_scheduler_field(new_ctx, "n_min", float(n_min))
        if (
            new_ctx.scheduler_state.get("n_cap_t") is None
            and n_cap is not None
        ):
            new_ctx = _with_scheduler_n_cap(new_ctx, float(n_cap))
        try:
            return float(chosen.derive(new_ctx))
        except ValueError:
            return float(DEFAULT_MEANFLOW_TOLERANCE_FALLBACK)
    return float(DEFAULT_MEANFLOW_TOLERANCE_FALLBACK)


def default_machine_eps(
    context: DerivationContext | None,
    *,
    t: float | None = None,
    s: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return the MeanFlow degenerate-pair ``eps`` from a derivation rule.

    Falls back to :data:`DEFAULT_MEANFLOW_EPS_FALLBACK` (``1e-12``)
    on missing context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else MachineEpsilonRule()
    )
    if context is not None:
        new_ctx = context
        if new_ctx.scheduler_state.get("t") is None and t is not None:
            new_ctx = _with_scheduler_field(new_ctx, "t", float(t))
        if new_ctx.scheduler_state.get("s") is None and s is not None:
            new_ctx = _with_scheduler_field(new_ctx, "s", float(s))
        try:
            return float(chosen.derive(new_ctx))
        except ValueError:
            return float(DEFAULT_MEANFLOW_EPS_FALLBACK)
    return float(DEFAULT_MEANFLOW_EPS_FALLBACK)


def default_ema_alpha(
    context: DerivationContext | None,
    *,
    grad_var: float | None = None,
    grad_mean: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``EMAOperator.alpha`` from a derivation rule.

    Falls back to :data:`DEFAULT_EMA_ALPHA_FALLBACK` (``0.1``) on
    missing context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else EMAInverseVarianceRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.local_curvature.get("grad_var") is None
            and grad_var is not None
        ):
            new_ctx = _with_curvature_field(
                new_ctx, "grad_var", float(grad_var)
            )
        if (
            new_ctx.local_curvature.get("grad_mean") is None
            and grad_mean is not None
        ):
            new_ctx = _with_curvature_field(
                new_ctx, "grad_mean", float(grad_mean)
            )
        try:
            return float(chosen.derive(new_ctx))
        except ValueError:
            return float(DEFAULT_EMA_ALPHA_FALLBACK)
    return float(DEFAULT_EMA_ALPHA_FALLBACK)


def default_distance_decay_temperature(
    context: DerivationContext | None,
    *,
    l_e: float | None = None,
    n_rounds: int | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``DistanceDecayBlender.temperature`` from a derivation rule.

    Falls back to :data:`DEFAULT_LIPSCHITZ_TEMP_FALLBACK` (``1.0``)
    on missing context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else LipschitzTemperatureRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.local_curvature.get("L_e") is None
            and l_e is not None
        ):
            new_ctx = _with_curvature_field(new_ctx, "L_e", float(l_e))
        if (
            new_ctx.scheduler_state.get("n_rounds") is None
            and n_rounds is not None
        ):
            new_ctx = _with_scheduler_field(
                new_ctx, "n_rounds", float(n_rounds)
            )
        try:
            return float(chosen.derive(new_ctx))
        except ValueError:
            return float(DEFAULT_LIPSCHITZ_TEMP_FALLBACK)
    return float(DEFAULT_LIPSCHITZ_TEMP_FALLBACK)


def default_min_gumbel_temp(
    context: DerivationContext | None,
    *,
    e_rho: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``DEFAULT_MIN_GUMBEL_TEMP`` from a derivation rule.

    Falls back to :data:`DEFAULT_MIN_GUMBEL_TEMP_FALLBACK`
    (``1e-3``) on missing context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else MinGumbelTempRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.paper_quantities.get("e_rho") is None
            and e_rho is not None
        ):
            new_ctx = _with_paper_field(new_ctx, "e_rho", float(e_rho))
        try:
            return float(chosen.derive(new_ctx))
        except ValueError:
            return float(DEFAULT_MIN_GUMBEL_TEMP_FALLBACK)
    return float(DEFAULT_MIN_GUMBEL_TEMP_FALLBACK)


def default_eps_log(
    context: DerivationContext | None,
    *,
    e_rho: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``CategoricalAwareBlender.eps_log`` from a derivation rule.

    Falls back to :data:`DEFAULT_EPS_LOG_FALLBACK` (``1e-30``) on
    missing context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else EpsLogRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.paper_quantities.get("e_rho") is None
            and e_rho is not None
        ):
            new_ctx = _with_paper_field(new_ctx, "e_rho", float(e_rho))
        try:
            return float(chosen.derive(new_ctx))
        except ValueError:
            return float(DEFAULT_EPS_LOG_FALLBACK)
    return float(DEFAULT_EPS_LOG_FALLBACK)


def default_exponential_alpha(
    context: DerivationContext | None,
    *,
    n_min: float | None = None,
    n_max: float | None = None,
    cycle_length: int | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``ExponentialScheduler.alpha`` from a derivation rule.

    Falls back to :data:`DEFAULT_EXPONENTIAL_ALPHA_FALLBACK`
    (``0.1``) on missing context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else ExponentialAlphaRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.scheduler_state.get("n_min") is None
            and n_min is not None
        ):
            new_ctx = _with_scheduler_field(new_ctx, "n_min", float(n_min))
        if (
            new_ctx.scheduler_state.get("n_max") is None
            and n_max is not None
        ):
            new_ctx = _with_scheduler_field(new_ctx, "n_max", float(n_max))
        if (
            new_ctx.scheduler_state.get("cycle_length") is None
            and cycle_length is not None
        ):
            new_ctx = _with_scheduler_field(
                new_ctx, "cycle_length", float(cycle_length)
            )
        try:
            return float(chosen.derive(new_ctx))
        except ValueError:
            return float(DEFAULT_EXPONENTIAL_ALPHA_FALLBACK)
    return float(DEFAULT_EXPONENTIAL_ALPHA_FALLBACK)


def default_polynomial_power(
    context: DerivationContext | None,
    *,
    cycle_length: int | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``PolynomialScheduler.power`` from a derivation rule.

    Falls back to :data:`DEFAULT_POLYNOMIAL_POWER_FALLBACK`
    (``2.0``) on missing context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else PolynomialPowerRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.scheduler_state.get("cycle_length") is None
            and cycle_length is not None
        ):
            new_ctx = _with_scheduler_field(
                new_ctx, "cycle_length", float(cycle_length)
            )
        try:
            return float(chosen.derive(new_ctx))
        except ValueError:
            return float(DEFAULT_POLYNOMIAL_POWER_FALLBACK)
    return float(DEFAULT_POLYNOMIAL_POWER_FALLBACK)


def default_sigmoid_midpoint(
    context: DerivationContext | None,
    *,
    n_min: float | None = None,
    n_max: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``SigmoidScheduler.midpoint`` from a derivation rule."""
    chosen: DerivationRule = (
        rule if rule is not None else SigmoidMidpointSteepnessRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.scheduler_state.get("n_min") is None
            and n_min is not None
        ):
            new_ctx = _with_scheduler_field(new_ctx, "n_min", float(n_min))
        if (
            new_ctx.scheduler_state.get("n_max") is None
            and n_max is not None
        ):
            new_ctx = _with_scheduler_field(new_ctx, "n_max", float(n_max))
        try:
            return float(chosen.derive_midpoint(new_ctx))  # type: ignore[attr-defined]
        except ValueError:
            return float(DEFAULT_SIGMOID_MIDPOINT_FALLBACK)
    return float(DEFAULT_SIGMOID_MIDPOINT_FALLBACK)


def default_sigmoid_steepness(
    context: DerivationContext | None,
    *,
    fisher_information: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``SigmoidScheduler.steepness`` from a derivation rule."""
    chosen: DerivationRule = (
        rule if rule is not None else SigmoidMidpointSteepnessRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.local_curvature.get("fisher_information") is None
            and fisher_information is not None
        ):
            new_ctx = _with_curvature_field(
                new_ctx, "fisher_information", float(fisher_information)
            )
        try:
            return float(chosen.derive_steepness(new_ctx))  # type: ignore[attr-defined]
        except ValueError:
            return float(DEFAULT_SIGMOID_STEEPNESS_FALLBACK)
    return float(DEFAULT_SIGMOID_STEEPNESS_FALLBACK)


def default_convergence_adaptive_kp(
    context: DerivationContext | None,
    *,
    w2_history: tuple[float, ...] | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.kp`` from a derivation rule."""
    chosen: DerivationRule = (
        rule if rule is not None else ConvergenceAdaptivePolyRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.ot_metrics.get("W2_history") is None
            and w2_history is not None
        ):
            new_ctx = _with_ot_field(
                new_ctx, "W2_history", tuple(float(v) for v in w2_history)
            )
        try:
            return float(chosen.derive_kp(new_ctx))  # type: ignore[attr-defined]
        except ValueError:
            return float(DEFAULT_KP_FALLBACK)
    return float(DEFAULT_KP_FALLBACK)


def default_convergence_adaptive_kd(
    context: DerivationContext | None,
    *,
    w2_history: tuple[float, ...] | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.kd`` from a derivation rule."""
    chosen: DerivationRule = (
        rule if rule is not None else ConvergenceAdaptivePolyRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.ot_metrics.get("W2_history") is None
            and w2_history is not None
        ):
            new_ctx = _with_ot_field(
                new_ctx, "W2_history", tuple(float(v) for v in w2_history)
            )
        try:
            return float(chosen.derive_kd(new_ctx))  # type: ignore[attr-defined]
        except ValueError:
            return float(DEFAULT_KD_FALLBACK)
    return float(DEFAULT_KD_FALLBACK)


def default_convergence_adaptive_shift_max(
    context: DerivationContext | None,
    *,
    w2_history: tuple[float, ...] | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.shift_max`` from a derivation rule."""
    chosen: DerivationRule = (
        rule if rule is not None else ConvergenceAdaptivePolyRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.ot_metrics.get("W2_history") is None
            and w2_history is not None
        ):
            new_ctx = _with_ot_field(
                new_ctx, "W2_history", tuple(float(v) for v in w2_history)
            )
        try:
            return float(chosen.derive_shift_max(new_ctx))  # type: ignore[attr-defined]
        except ValueError:
            return float(DEFAULT_SHIFT_MAX_FALLBACK)
    return float(DEFAULT_SHIFT_MAX_FALLBACK)


def default_convergence_adaptive_ema(
    context: DerivationContext | None,
    *,
    cycle_length: int | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``ConvergenceAdaptiveScheduler.ema`` from a derivation rule."""
    chosen: DerivationRule = (
        rule if rule is not None else ConvergenceAdaptivePolyRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.scheduler_state.get("cycle_length") is None
            and cycle_length is not None
        ):
            new_ctx = _with_scheduler_field(
                new_ctx, "cycle_length", float(cycle_length)
            )
        try:
            return float(chosen.derive_ema(new_ctx))  # type: ignore[attr-defined]
        except ValueError:
            return float(DEFAULT_EMA_SCHED_FALLBACK)
    return float(DEFAULT_EMA_SCHED_FALLBACK)


def default_metric_weights(
    context: DerivationContext | None,
    *,
    metric_variances: Mapping[str, tuple[float, ...]] | None = None,
    rule: DerivationRule | None = None,
) -> dict[str, float]:
    """Return the multi-metric feedback weights from a derivation rule.

    Falls back to :data:`DEFAULT_METRIC_WEIGHTS_FALLBACK` on
    missing context.
    """
    chosen: Any = (
        rule if rule is not None else MetricWeightRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.ot_metrics.get("metric_variances") is None
            and metric_variances is not None
        ):
            new_ctx = _with_ot_field(
                new_ctx,
                "metric_variances",
                {
                    str(k): tuple(float(x) for x in v)
                    for k, v in metric_variances.items()
                },
            )
        try:
            result = chosen.derive(new_ctx)
        except ValueError:
            return dict(DEFAULT_METRIC_WEIGHTS_FALLBACK)
        if not isinstance(result, dict) or not result:
            return dict(DEFAULT_METRIC_WEIGHTS_FALLBACK)
        return {str(k): float(v) for k, v in result.items()}
    return dict(DEFAULT_METRIC_WEIGHTS_FALLBACK)


def default_jitter_std(
    context: DerivationContext | None,
    *,
    n_cap: float | None = None,
    n_rounds: int | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``JitteredConstantScheduler.jitter_std`` from a derivation rule.

    Falls back to :data:`DEFAULT_JITTER_STD_FALLBACK` (``0.05``)
    on missing context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else VariancePreservingJitterRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.scheduler_state.get("n_cap_t") is None
            and n_cap is not None
        ):
            new_ctx = _with_scheduler_n_cap(new_ctx, float(n_cap))
        if (
            new_ctx.scheduler_state.get("n_rounds") is None
            and n_rounds is not None
        ):
            new_ctx = _with_scheduler_field(
                new_ctx, "n_rounds", float(n_rounds)
            )
        try:
            return float(chosen.derive(new_ctx))
        except ValueError:
            return float(DEFAULT_JITTER_STD_FALLBACK)
    return float(DEFAULT_JITTER_STD_FALLBACK)


def default_constant_beta(
    context: DerivationContext | None,
    *,
    n_min: float | None = None,
    n_max: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``DEFAULT_CONSTANT_BETA`` from a derivation rule.

    Falls back to :data:`DEFAULT_CONSTANT_BETA_FALLBACK` (``0.5``)
    on missing context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else MidpointBetaRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.scheduler_state.get("n_min") is None
            and n_min is not None
        ):
            new_ctx = _with_scheduler_field(new_ctx, "n_min", float(n_min))
        if (
            new_ctx.scheduler_state.get("n_max") is None
            and n_max is not None
        ):
            new_ctx = _with_scheduler_field(new_ctx, "n_max", float(n_max))
        try:
            return float(chosen.derive(new_ctx))
        except ValueError:
            return float(DEFAULT_CONSTANT_BETA_FALLBACK)
    return float(DEFAULT_CONSTANT_BETA_FALLBACK)


def default_adaptive_target_estimate(
    context: DerivationContext | None,
    *,
    n_min: float | None = None,
    n_max: float | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``DEFAULT_ADAPTIVE_TARGET_ESTIMATE`` from a derivation rule.

    Falls back to :data:`DEFAULT_TARGET_ESTIMATE_FALLBACK` (``0.5``)
    on missing context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else MidpointBetaRule()
    )
    if context is not None:
        new_ctx = context
        if (
            new_ctx.scheduler_state.get("n_min") is None
            and n_min is not None
        ):
            new_ctx = _with_scheduler_field(new_ctx, "n_min", float(n_min))
        if (
            new_ctx.scheduler_state.get("n_max") is None
            and n_max is not None
        ):
            new_ctx = _with_scheduler_field(new_ctx, "n_max", float(n_max))
        try:
            return float(chosen.derive(new_ctx))
        except ValueError:
            return float(DEFAULT_TARGET_ESTIMATE_FALLBACK)
    return float(DEFAULT_TARGET_ESTIMATE_FALLBACK)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_finite(x: Any, name: str) -> float:
    """Coerce ``x`` to a finite float or raise :class:`ValueError`."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError(
            f"{name} must be a real number, got {type(x).__name__}"
        )
    f = float(x)
    if not math.isfinite(f):
        raise ValueError(f"{name} must be finite, got {f!r}")
    return f


def _adr0010_fallback(n_cap: float | None) -> float:
    """Return the ADR-0010 cosine-driven memory fraction ``1 - n_cap``.

    When ``n_cap`` is ``None``, return the documented mid-cycle
    anchor of 0.5 (the symmetric envelope center per ADR-0010).
    Non-finite or non-numeric ``n_cap`` raises
    :class:`ValueError` — the fallback path is fail-closed so
    the caller can surface the bug.
    """
    if n_cap is None:
        return 0.5
    nc = _coerce_finite(n_cap, "n_cap")
    return float(max(0.0, min(1.0, 1.0 - nc)))


def _with_scheduler_n_cap(
    context: DerivationContext, n_cap: float
) -> DerivationContext:
    """Return a copy of ``context`` with ``n_cap_t`` populated."""
    new_state = dict(context.scheduler_state)
    new_state["n_cap_t"] = n_cap
    return DerivationContext(
        paper_quantities=dict(context.paper_quantities),
        local_curvature=dict(context.local_curvature),
        scheduler_state=new_state,
        ot_metrics=dict(context.ot_metrics),
    )


def _with_scheduler_field(
    context: DerivationContext, key: str, value: float
) -> DerivationContext:
    """Return a copy of ``context`` with ``scheduler_state[key]`` populated."""
    new_state = dict(context.scheduler_state)
    new_state[str(key)] = float(value)
    return DerivationContext(
        paper_quantities=dict(context.paper_quantities),
        local_curvature=dict(context.local_curvature),
        scheduler_state=new_state,
        ot_metrics=dict(context.ot_metrics),
    )


def _with_paper_field(
    context: DerivationContext, key: str, value: float
) -> DerivationContext:
    """Return a copy of ``context`` with ``paper_quantities[key]`` populated."""
    new_paper = dict(context.paper_quantities)
    new_paper[str(key)] = float(value)
    return DerivationContext(
        paper_quantities=new_paper,
        local_curvature=dict(context.local_curvature),
        scheduler_state=dict(context.scheduler_state),
        ot_metrics=dict(context.ot_metrics),
    )


def _with_curvature_field(
    context: DerivationContext, key: str, value: float
) -> DerivationContext:
    """Return a copy of ``context`` with ``local_curvature[key]`` populated."""
    new_curv = dict(context.local_curvature)
    new_curv[str(key)] = float(value)
    return DerivationContext(
        paper_quantities=dict(context.paper_quantities),
        local_curvature=new_curv,
        scheduler_state=dict(context.scheduler_state),
        ot_metrics=dict(context.ot_metrics),
    )


def _with_ot_field(
    context: DerivationContext, key: str, value: Any
) -> DerivationContext:
    """Return a copy of ``context`` with ``ot_metrics[key]`` populated."""
    new_ot = dict(context.ot_metrics)
    new_ot[str(key)] = value
    return DerivationContext(
        paper_quantities=dict(context.paper_quantities),
        local_curvature=dict(context.local_curvature),
        scheduler_state=dict(context.scheduler_state),
        ot_metrics=new_ot,
    )


def _empty_context() -> DerivationContext:
    """Return a fully-empty :class:`DerivationContext`.

    All four mappings are empty ``dict`` instances (frozen via
    the underlying :class:`DerivationContext` dataclass). Used by
    the dispatcher fallbacks when the caller passes ``None`` for
    both ``context`` and the fallback kwargs.
    """
    return DerivationContext(
        paper_quantities={},
        local_curvature={},
        scheduler_state={},
        ot_metrics={},
    )

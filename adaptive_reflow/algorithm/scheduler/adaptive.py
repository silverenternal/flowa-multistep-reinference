"""Adaptive per-round capacity schedulers (Wave 105 P2-A split).

This module owns the three **adaptive** schedulers the framework exposes
as paper-quantity-driven / closed-loop controllers:

* :class:`ConvergenceAdaptiveScheduler` — PID-lite wrapper that drives
  ``u_r`` from per-round W2 feedback (Wave 31 paper-quantity-aware PID
  branch adds ``A_g`` / ``B_g`` / ``e_rho`` EMA tracking).
* :class:`CodimensionSheetScheduler` — paper-quantity-driven scheduler
  whose ``n_cap`` is the literal sheet-vs-cell evidence balance
  (paper Lemma 2 / Lemma 3 / Corollary 1). Framework default since
  Wave 34.
* :class:`PaperRatioAdaptiveScheduler` — Wave 31 ratio-driven
  scheduler that re-derives ``n_cap`` from the cached paper-quantity
  evidence balance.

The shared structural types (:class:`ScheduleSample`,
:class:`SchedulerProtocol`, :func:`_coerce_int_nonneg`) live in
:mod:`adaptive_reflow.algorithm.scheduler.protocols`. The simple (non-
adaptive) families live in :mod:`adaptive_reflow.algorithm.scheduler.simple`.

The two default-weight dictionaries
(:data:`DEFAULT_FEEDBACK_METRIC_WEIGHTS`,
:data:`DEFAULT_PAPER_QUANTITY_WEIGHTS`) and the higher-is-better metric
frozenset (:data:`_HIGHER_IS_BETTER_METRICS`) are defined here because
they are only consumed by :class:`ConvergenceAdaptiveScheduler`'s PID
branch.

The closed-form sheet-vs-cell evidence ratio helper
(:func:`_paper_evidence_balance`) lives here too — it is the per-round
ratio consumed by :class:`CodimensionSheetScheduler` and
:class:`PaperRatioAdaptiveScheduler`.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts import (
    CosineScheduleSample,
    hash_artifact,
)
from adaptive_reflow.schedule.cosine import n_cap_for_round

from .protocols import (
    SchedulerProtocol,
    ScheduleSample,
    _coerce_int_nonneg,
)
from .simple import (  # type: ignore[attr-defined]
    CosineAnnealScheduler,
    default_cosine_scheduler,
    memory_fraction_from_schedule,
)

# ---------------------------------------------------------------------------
# Convergence-adaptive scheduler — default multi-metric feedback weights
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
        shift_max: float = 0.30,
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


#: Wave 35 FIX-1 -- EMA weight applied to each new per-round feedback
#: observation in :meth:`CodimensionSheetScheduler.record_round_feedback`.
#: Matches :class:`ConvergenceAdaptiveScheduler`'s default ``ema=0.3`` so
#: the two adaptive families smooth their W2 signal identically.
_FEEDBACK_EMA: float = 0.3


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
        early_stop_min_rounds: int = 2,
        early_stop_window: int = 2,
        early_stop_plateau_rel_tol: float = 0.005,
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
        :param early_stop_min_rounds: Wave 35 FIX-2. Minimum number of
            rounds that must be recorded via
            :meth:`record_round_feedback` before
            :meth:`should_terminate_round` may return ``True``
            (``>= 1``). Guards against terminating on a single noisy
            observation.
        :param early_stop_window: Wave 35 FIX-2. Number of consecutive
            smoothed-W2 observations compared when testing for a
            plateau (``>= 1``).
        :param early_stop_plateau_rel_tol: Wave 35 FIX-2. Relative
            change below which the smoothed W2 counts as plateaued
            (``>= 0``; default ``0.005`` = 0.5 %).

        The three ``early_stop_*`` parameters are runtime-control
        knobs: they never influence :meth:`sample`, and are therefore
        deliberately excluded from :meth:`to_config` and
        :attr:`config_hash` so pinned schedule vectors stay valid.
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
        # Wave 35 FIX-2 -- early-stop knob validation.
        for _nm, _val in (
            ("early_stop_min_rounds", early_stop_min_rounds),
            ("early_stop_window", early_stop_window),
        ):
            if isinstance(_val, bool) or not isinstance(_val, int):
                raise ValueError(f"{_nm} must be int, got {_val!r}")
            if int(_val) < 1:
                raise ValueError(f"{_nm} must be >= 1, got {_val!r}")
        if isinstance(early_stop_plateau_rel_tol, bool) or not isinstance(
            early_stop_plateau_rel_tol, (int, float)
        ):
            raise ValueError(
                "early_stop_plateau_rel_tol must be a real number, got "
                f"{early_stop_plateau_rel_tol!r}"
            )
        if not math.isfinite(float(early_stop_plateau_rel_tol)) or float(
            early_stop_plateau_rel_tol
        ) < 0.0:
            raise ValueError(
                "early_stop_plateau_rel_tol must be finite and >= 0, got "
                f"{early_stop_plateau_rel_tol!r}"
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

        # Wave 35 FIX-1 / FIX-2 -- runner feedback loop + convergence
        # detection. These attributes are *observational only*: nothing
        # here feeds :meth:`sample`, so every schedule this scheduler
        # produced before Wave 35 is byte-identical afterwards. For the
        # same reason the three early-stop knobs are deliberately kept
        # out of :meth:`to_config` / :attr:`config_hash` (they are
        # runtime-control parameters, not schedule parameters), so the
        # pinned D.4 regression vectors stay valid.
        self._w2_history: list[float] = []
        self._smoothed_w2: float | None = None
        self._smoothed_w2_history: list[float] = []
        self._evidence_ratio_history: list[float] = []
        self._smoothed_evidence_ratio: float | None = None
        self._feedback_ema = float(_FEEDBACK_EMA)
        self._early_stop_min_rounds = int(early_stop_min_rounds)
        self._early_stop_window = int(early_stop_window)
        self._early_stop_plateau_rel_tol = float(early_stop_plateau_rel_tol)
        # Wave 38 HIGH-1: per-round paper-quantity shift history. Appended
        # to by :meth:`record_round_feedback` whenever a caller supplies a
        # ``paper_quantities`` mapping carrying the sheet-vs-cell ratio
        # (``sheet_A`` / ``cell_C`` / ``packing_B``). Independent of
        # :attr:`_evidence_ratio_history`, which tracks the sheet-vs-cell
        # *proxy* ratio from ``selection_ratio`` / ``evidence_ratio``
        # keys (legacy Wave 35 path).
        self._shift_history: list[float] = []

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

        # P2-W33-A: compute the per-round ``eps`` so the paper's
        # ``eps -> 0`` limit is realised as a *schedule* across the
        # cycle, not as a flip applied to a constant ``eps``. With
        # ``eps_direction="decreasing"`` (paper convention, default)
        # the implicit noise scale diminishes monotonically from
        # ``eps_0`` at ``r=0`` to a floor (``1e-9``) at ``r=L-1`` —
        # matching Theorem 1's ``eps -> 0`` claim. The legacy
        # ``"increasing"`` direction reverses the ramp
        # (``r=0`` small, ``r=L-1`` large) for byte-compatibility with
        # the prior cosine-based interpretation.
        if self._eps_direction == "decreasing":
            # Paper-aligned: implicit noise scale diminishes across
            # the cycle. ``u_r in [0, 1]`` is the round's progress;
            # the floor avoids the degenerate ``eps=0`` cell-collapse
            # that would yield ``sheet=0, ratio=0`` at ``r=L-1``.
            eps_per_round = float(self._eps_implicit) * (1.0 - u_r)
        else:  # legacy "increasing"
            eps_per_round = float(self._eps_implicit) * u_r
        eps_per_round = max(float(eps_per_round), 1e-9)

        # Compute the paper's sheet-vs-cell evidence ratio. The
        # "paper-quantity-augmented" path uses the cached ``A_g`` /
        # ``B_g`` / ``C_g`` literals (round-independent when
        # ``profile_residual_fn`` is supplied) — this is the canonical
        # paper-quantity-driven path. The framework-side heuristic
        # (no profile) uses ``n_cap_base`` (cosine ramp) as the
        # cell-evidence weight; the two closed forms agree up to
        # normalisation constants. The ``eps`` plug is now the
        # per-round ``eps_per_round`` so the cycle's terminal round
        # actually exercises the Theorem 1 ``eps -> 0`` limit.
        ratio = float(
            _paper_evidence_balance(
                n_cap_base,
                eps_per_round,
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
            # P2-W33-A: surface the per-round ``eps`` (not the
            # constructor-time constant) so a downstream reader sees
            # the actual schedule value used in the closed form.
            # The constructor constant remains at
            # ``self._eps_implicit`` for back-compat introspection.
            eps_implicit=float(eps_per_round),
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
            early_stop_min_rounds=int(self._early_stop_min_rounds),
            early_stop_window=int(self._early_stop_window),
            early_stop_plateau_rel_tol=float(self._early_stop_plateau_rel_tol),
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
        # Wave 35 FIX-1 -- the feedback histories are per-run state and
        # must not leak across a reset (otherwise a replayed cycle
        # would early-terminate on the previous run's plateau).
        self._w2_history = []
        self._smoothed_w2 = None
        self._smoothed_w2_history = []
        self._evidence_ratio_history = []
        self._smoothed_evidence_ratio = None
        # Wave 38 HIGH-1 -- paper-quantity shift history must also be
        # cleared so a replayed cycle starts at zero PID state.
        self._shift_history = []
        self._base.reset()

    # -- Wave 35 FIX-1 / FIX-2: convergence feedback + termination ---------

    @property
    def w2_history(self) -> tuple[float, ...]:
        """Return the raw per-round ``W2`` observations recorded so far."""
        return tuple(self._w2_history)

    @property
    def shift_history(self) -> tuple[float, ...]:
        """Return the per-round paper-quantity sheet-vs-cell ratio history.

        Wave 38 HIGH-1 — each entry is
        ``paper_quantities["sheet_A"] / max(paper_quantities["cell_C"]
        * paper_quantities["packing_B"], 1e-12)`` for one
        :meth:`record_round_feedback` call that supplied all three
        paper-quantity keys. Empty until the first such call (a broken
        oracle or missing keys leave the history untouched, mirroring
        :attr:`w2_history`'s missing-value tolerance). Independent of
        :attr:`evidence_ratio_history`, which tracks the legacy
        ``selection_ratio`` / ``evidence_ratio`` path; the two
        histories may diverge when callers supply different signal
        sources.
        """
        return tuple(self._shift_history)

    @property
    def smoothed_w2(self) -> float | None:
        """Return the EMA-smoothed ``W2``, or ``None`` before any feedback."""
        return self._smoothed_w2

    @property
    def smoothed_evidence_ratio(self) -> float | None:
        """Return the EMA-smoothed sheet-vs-cell ratio from feedback.

        ``None`` until :meth:`record_round_feedback` has been called
        with an ``evidence_ratio`` / ``selection_ratio`` key. Distinct
        from :attr:`last_evidence_ratio`, which is the *scheduler's own*
        per-round ratio computed in :meth:`sample`; this property is the
        smoothed *observed* ratio fed back by the runner.
        """
        return self._smoothed_evidence_ratio

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
        paper_quantities: Mapping[str, float] | None = None,
    ) -> None:
        """Consume one round's oracle metrics (Wave 35 FIX-1).

        Prior to Wave 35 this was a documented no-op: the runner
        (:meth:`BatchedTrajectoryRunner.run`) called the hook every
        round and the codimension scheduler dropped the signal on the
        floor, so the framework's default paper-quantity-driven
        scheduler was structurally blind to convergence
        (``docs/audit/algorithm-saturation-review.md`` Findings 2 / 7).

        The hook is now **observational**: it records the round's
        signals and updates EMA-smoothed summaries which
        :meth:`should_terminate_round` consumes. It deliberately does
        NOT mutate any quantity read by :meth:`sample`, so every
        schedule this class produced before Wave 35 is byte-identical
        afterwards (the paper-aligned ``n_cap`` closed form stays the
        single source of truth for capacity; only the *round count* can
        now respond to convergence).

        Recognised keys, all optional and individually skipped when
        missing / non-numeric / non-finite (a broken oracle cannot
        poison the scheduler):

        * ``W2`` -- the round's Wasserstein-2 estimate (lower better).
        * ``evidence_ratio`` or ``selection_ratio`` -- the observed
          sheet-vs-cell balance (higher better).

        ``paper_quantities`` is accepted for signature parity with
        :meth:`PaperRatioAdaptiveScheduler.record_round_feedback` so a
        caller can pass the same payload to either family; its
        ``sheet_vs_cells_proxy`` key, when present and no explicit
        ratio was supplied in ``metrics``, is used as the ratio.

        :param round_in_cycle: the round index the metrics belong to
            (recorded for ordering only; must be ``>= 0``).
        :param metrics: mapping of metric name to value.
        :param paper_quantities: optional literal paper quantities.
        """
        _coerce_int_nonneg(round_in_cycle, "round_in_cycle")

        def _finite(value: object) -> float | None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            fv = float(value)
            return fv if math.isfinite(fv) else None

        if isinstance(metrics, Mapping):
            w2 = _finite(metrics.get("W2"))
            ratio = _finite(metrics.get("evidence_ratio"))
            if ratio is None:
                ratio = _finite(metrics.get("selection_ratio"))
        else:  # defensive: a non-mapping oracle payload is ignored
            w2 = None
            ratio = None
        if ratio is None and isinstance(paper_quantities, Mapping):
            ratio = _finite(paper_quantities.get("sheet_vs_cells_proxy"))

        # Wave 38 HIGH-1 -- paper-quantity-aware shift history. When the
        # caller supplies a ``paper_quantities`` mapping carrying the
        # canonical sheet-vs-cell ratio (``sheet_A`` /
        # ``cell_C * packing_B``), append the ratio to
        # :attr:`_shift_history`. The shift itself is intentionally NOT
        # applied to ``sample`` (the canonical n_cap closed form is the
        # single source of truth for capacity), so every schedule this
        # class produced before Wave 38 stays byte-identical. The history
        # is an observability surface for the runner / audit trail (the
        # same separation as :attr:`_w2_history`).
        if isinstance(paper_quantities, Mapping):
            pq_sheet_A = _finite(paper_quantities.get("sheet_A"))
            pq_cell_C = _finite(paper_quantities.get("cell_C"))
            pq_packing_B = _finite(paper_quantities.get("packing_B"))
            if (
                pq_sheet_A is not None
                and pq_cell_C is not None
                and pq_packing_B is not None
            ):
                denom = max(float(pq_cell_C) * float(pq_packing_B), 1e-12)
                self._shift_history.append(float(pq_sheet_A) / denom)

        alpha = self._feedback_ema
        if w2 is not None:
            self._w2_history.append(w2)
            self._smoothed_w2 = (
                w2
                if self._smoothed_w2 is None
                else (1.0 - alpha) * float(self._smoothed_w2) + alpha * w2
            )
            self._smoothed_w2_history.append(float(self._smoothed_w2))
        if ratio is not None:
            self._evidence_ratio_history.append(ratio)
            self._smoothed_evidence_ratio = (
                ratio
                if self._smoothed_evidence_ratio is None
                else (1.0 - alpha) * float(self._smoothed_evidence_ratio)
                + alpha * ratio
            )
        return None

    def should_terminate_round(
        self,
        round_in_cycle: int | None = None,
    ) -> bool:
        """Return ``True`` when the cycle's W2 signal has plateaued.

        Wave 35 FIX-2 — the convergence-detection half of the
        saturation fix (``docs/audit/algorithm-saturation-review.md``
        R1; ``docs/audit/web-research-fm-restart-2026.md`` R-5;
        ``docs/audit/web-research-saturation-2026.md`` Rec 1). A caller
        that opts in (``BatchedRunnerConfig.early_termination=True``)
        can stop paying NFE for rounds that no longer move the metric.

        The rule is training-free and reads only signals the runner
        already computes:

        1. At least :attr:`early_stop_min_rounds` W2 observations must
           have been recorded via :meth:`record_round_feedback`, and at
           least ``early_stop_window + 1`` of them must exist.
        2. Over the last :attr:`early_stop_window` steps of the W2
           series, every consecutive relative change
           ``|w[i] - w[i-1]| / max(|w[i-1]|, tiny)`` must be below
           :attr:`early_stop_plateau_rel_tol`.

        The test runs on the *raw* W2 series rather than the EMA:
        the EMA lags a genuine plateau by ``O(1/alpha)`` rounds, which
        would spend exactly the NFE the hook exists to save. The
        ``early_stop_window`` requirement (consecutive small changes)
        supplies the noise rejection the EMA would otherwise provide,
        and :attr:`smoothed_w2` remains available as the summary
        statistic.

        Returns ``False`` whenever the evidence is insufficient, so the
        default behaviour of every caller that does not opt in is
        exactly the pre-Wave-35 behaviour (run the full cycle).

        :param round_in_cycle: accepted and ignored; present so callers
            can pass the round index for symmetry with
            :meth:`record_round_feedback`.
        """
        del round_in_cycle  # signature parity only
        history = self._w2_history
        window = self._early_stop_window
        if len(history) < self._early_stop_min_rounds:
            return False
        if len(history) < window + 1:
            return False
        tol = self._early_stop_plateau_rel_tol
        recent = history[-(window + 1):]
        for prev, cur in zip(recent[:-1], recent[1:], strict=False):
            denom = max(abs(float(prev)), 1e-12)
            if abs(float(cur) - float(prev)) / denom >= tol:
                return False
        return True

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
        shift_max: float = 0.30,
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
# Wave 125 Phase 4 — target-RMS calibration for paper-quantity-driven β
# ---------------------------------------------------------------------------


#: Reference RMSD (Å) that maps to :data:`_REF_N_CAP` in
#: :func:`adjust_n_cap_for_target_rms`. Picked as the canonical
#: "medium-quality protein backbone" target so the calibration is
#: centred on a sensible working point. Callers can override via the
#: ``ref_rmsd`` kwarg.
_REF_RMSD: float = 2.5

#: Reference ``n_cap`` value associated with :data:`_REF_RMSD`. With the
#: defaults the calibration maps ``1.0 Å -> 0.2``, ``2.5 Å -> 0.5`` and
#: ``5.0 Å -> 1.0`` (clipped). Callers can override via the ``ref_n_cap``
#: kwarg.
_REF_N_CAP: float = 0.5


def adjust_n_cap_for_target_rms(
    target_rms_threshold: float,
    *,
    ref_rmsd: float = _REF_RMSD,
    ref_n_cap: float = _REF_N_CAP,
) -> float:
    """Return a calibrated ``n_cap`` based on a target RMSD threshold (Å).

    Wave 125 Phase 4 (paper-quantity-driven ``n_cap`` calibration; see
    ``todo/algo-improvement-paper-quantity-beta-calibration.md``). The
    paper-quantity-driven scheduler's :class:`CodimensionSheetScheduler`
    ``n_cap`` may sit too high or too low for a given protein-reconstruction
    RMSD target; this helper exposes the *calibration knob* so a caller
    can request a specific RMSD target and receive a calibrated ``n_cap``
    in return.

    The mapping is intentionally simple and monotone: with the default
    reference constants,

        n_cap = clip(ref_n_cap * (target_rms_threshold / ref_rmsd), 0, 1)

    so a smaller target RMSD (tighter quality) lowers the ``n_cap`` (less
    fresh-noise injection, more memory-dominated refinement) and a larger
    target RMSD (looser quality) raises it. The defaults are calibrated
    so that

        target_rms_threshold = 1.0 Å  → n_cap ≈ 0.20 (low fresh noise)
        target_rms_threshold = 2.5 Å  → n_cap = 0.50  (reference)
        target_rms_threshold = 5.0 Å  → n_cap = 1.00  (max fresh noise)

    :param target_rms_threshold: target RMSD in Angstroms (must be
        ``> 0`` and finite). A value of ``0`` is rejected because the
        identity transform would otherwise silently map to ``n_cap = 0``
        (full memory dominance, no fresh noise).
    :param ref_rmsd: reference RMSD in Å that maps to ``ref_n_cap``
        (default ``2.5``). Must be finite and ``> 0``; the calibration
        rescales linearly against it.
    :param ref_n_cap: ``n_cap`` value associated with ``ref_rmsd``
        (default ``0.5``). Must lie in ``[0, 1]``; the calibration
        scales linearly from this anchor point.
    :returns: a finite ``n_cap`` in ``[0, 1]``.
    :raises TypeError: when ``target_rms_threshold`` is not a real number.
    :raises ValueError: when ``target_rms_threshold`` is non-positive,
        non-finite, or when ``ref_rmsd`` / ``ref_n_cap`` are out of
        domain.
    """
    if isinstance(target_rms_threshold, bool) or not isinstance(
        target_rms_threshold, (int, float)
    ):
        raise TypeError(
            "target_rms_threshold must be a real number, got "
            f"{target_rms_threshold!r}"
        )
    target_f = float(target_rms_threshold)
    if not math.isfinite(target_f):
        raise ValueError(
            f"target_rms_threshold must be finite, got {target_f!r}"
        )
    if target_f <= 0.0:
        raise ValueError(
            "target_rms_threshold must be > 0 (a zero target would "
            "silently collapse the schedule to full memory dominance), "
            f"got {target_f!r}"
        )
    if isinstance(ref_rmsd, bool) or not isinstance(ref_rmsd, (int, float)):
        raise TypeError(f"ref_rmsd must be a real number, got {ref_rmsd!r}")
    ref_rmsd_f = float(ref_rmsd)
    if not math.isfinite(ref_rmsd_f) or ref_rmsd_f <= 0.0:
        raise ValueError(
            f"ref_rmsd must be finite and > 0, got {ref_rmsd_f!r}"
        )
    if isinstance(ref_n_cap, bool) or not isinstance(
        ref_n_cap, (int, float)
    ):
        raise TypeError(
            f"ref_n_cap must be a real number, got {ref_n_cap!r}"
        )
    ref_n_cap_f = float(ref_n_cap)
    if not math.isfinite(ref_n_cap_f) or not (0.0 <= ref_n_cap_f <= 1.0):
        raise ValueError(
            "ref_n_cap must be finite and lie in [0, 1], got "
            f"{ref_n_cap_f!r}"
        )
    n_cap = ref_n_cap_f * (target_f / ref_rmsd_f)
    # The clip is defensive: a very large target_rms_threshold can
    # push the linear scaling above 1; the ``n_cap`` envelope must
    # stay inside the canonical [0, 1] range.
    return float(max(0.0, min(1.0, n_cap)))


def paper_quantity_driven_beta(
    *,
    target_rms_threshold: float | None = None,
    eps_implicit: float = 0.05,
    n_min: float = 0.0,
    n_max: float = 1.0,
    round_in_cycle: int = 0,
    cycle_length: int = 20,
) -> float:
    """Return a paper-quantity-driven ``n_cap`` value, optionally RMSD-calibrated.

    Wave 125 Phase 4 — paper-quantity-driven ``n_cap`` calibration via a
    target RMSD threshold. The function returns a single ``n_cap`` value
    suitable for plugging into a restart-policy framework (e.g.
    :class:`~adaptive_reflow.algorithm.merge.merge_operator.BoundedMergeOperator`'s
    ``beta_by_channel``). The default behaviour (no threshold) preserves
    the pre-Wave-125 paper-quantity-driven scheduler by delegating to
    :class:`CodimensionSheetScheduler` and returning the same ``n_cap``
    the scheduler would emit — so existing callers see byte-identical
    output until they explicitly opt in to the calibration.

    When ``target_rms_threshold`` is supplied, the function delegates
    directly to :func:`adjust_n_cap_for_target_rms` so the calibration
    is reproducible, deterministic, and independent of the
    ``eps_implicit`` / ``cycle_length`` knobs the scheduler would
    otherwise consume. The rationale (per
    ``todo/algo-improvement-paper-quantity-beta-calibration.md``) is
    that the paper-quantity-driven ``n_cap`` may sit too high or too
    low for protein-reconstruction RMSD; the calibration knob lets the
    caller request a *target* RMSD and receive the corresponding
    ``n_cap`` without having to reason about the scheduler's internal
    paper-quantity constants.

    :param target_rms_threshold: optional target RMSD in Å. When
        supplied the function returns
        ``adjust_n_cap_for_target_rms(target_rms_threshold)`` directly
        (and the remaining kwargs are ignored — the calibration is
        pure). ``None`` (the default) preserves the pre-Wave-125
        paper-quantity-driven behaviour by delegating to
        :class:`CodimensionSheetScheduler`.
    :param eps_implicit: implicit noise scale in evidence units;
        forwarded to the codimension scheduler when
        ``target_rms_threshold is None``. Must be ``> 0``.
    :param n_min: capacity floor (output lower bound); must lie in
        ``[0, 1]``. Forwarded to the codimension scheduler.
    :param n_max: capacity ceiling (output upper bound); must lie in
        ``[0, 1]``. Forwarded to the codimension scheduler.
    :param round_in_cycle: round index the ``n_cap`` is being sampled
        for (used only when ``target_rms_threshold is None``).
    :param cycle_length: number of rounds in one outer cycle (used only
        when ``target_rms_threshold is None``).
    :returns: a finite ``n_cap`` in ``[0, 1]``.
    """
    if target_rms_threshold is not None:
        # Calibration path: pure function of the threshold; ignore the
        # scheduler-shape kwargs. This is the additive Wave 125
        # behaviour — the kwargs are accepted only for forward
        # compatibility (callers can pass both ``target_rms_threshold``
        # and the scheduler shape; the threshold always wins).
        return adjust_n_cap_for_target_rms(target_rms_threshold)

    # Backward-compat path: delegate to the existing
    # paper-quantity-driven scheduler so the default ``n_cap``
    # matches the pre-Wave-125 default at the same round / cycle.
    # We construct a fresh :class:`CodimensionSheetScheduler` here
    # rather than depending on a shared instance because the helper
    # is a pure function of its inputs (no hidden state).
    helper_scheduler = CodimensionSheetScheduler(
        cycle_length=int(cycle_length),
        n_min=float(n_min),
        n_max=float(n_max),
        eps_implicit=float(eps_implicit),
    )
    helper_sample = helper_scheduler.sample(
        0, int(round_in_cycle), int(round_in_cycle)
    )
    return float(helper_sample.n_cap)

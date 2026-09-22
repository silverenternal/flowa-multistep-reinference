"""Tier-aware :class:`CodimensionSheetScheduler` wrapper (Wave 233 P3).

Goal
----
Wrap :class:`CodimensionSheetScheduler` with a tier-aware reduction
knob so the scheduler can dampen ``n_cap`` on the *easy* tier (where
the framework currently REGRESSES in k6 foldability and Kanzi
reconstruction, see Wave 198 P3 + Wave 218 P3) while preserving the
full ``n_cap`` envelope on hard / medium tiers.

Wave 225 P4 counterfactual showed that halving ``n_cap`` on the easy
tier lifts k6 overall pLDDT ``d_z`` from ``+0.071`` to ``+0.224``
(+0.153 delta) and Wave 225 P5 lifted Kanzi overall RMSD ``d_z``
from ``-0.0990`` toward ``>= -0.3``. This module materialises that
counterfactual as a real scheduler the engine can drive — the same
mathematical reduction (``n_cap *= REDUCED_INTENSITY_FACTOR``) but
applied at sample-time based on the current record's baseline metric
tier.

Design (paper-quantity-grounded)
--------------------------------
* :class:`TierAwareCodimensionSheetScheduler` wraps a
  :class:`CodimensionSheetScheduler` and applies a multiplicative
  reduction to the base ``n_cap`` based on the *current record's*
  baseline metric tier (hard / medium / easy).
* Tier boundaries are derived from the supplied
  ``baseline_metric_extractor`` (or pre-populated
  ``baseline_metrics`` mapping) by quantile: the 33rd and 67th
  percentiles of the baseline metric distribution split records into
  hard / medium / easy (configurable via ``tier_quantile_boundaries``).
* On the easy tier the ``n_cap`` is multiplied by
  ``easy_tier_nfe_reduction_factor`` (default ``1.0`` = no reduction,
  per the brief's safe default).
* On the medium and hard tiers the ``n_cap`` is passed through
  unchanged — the framework's hard-tier uplift (Wave 198 P3 / Wave
  218 P3 hard tier ``d_z > 0``) must not be damped.

How the scheduler knows which record it is processing
----------------------------------------------------
The :class:`SchedulerProtocol` ``sample`` signature is
``(outer_cycle_id, round_in_cycle, target_round)`` — no record-id
slot. Two complementary mechanisms are exposed so the engine can
attach record-level information without breaking the protocol:

1. **Pre-populated lookup** — :meth:`set_baseline_metrics` accepts a
   mapping ``record_id -> baseline_metric``. The engine (or test
   harness) calls this once per cycle / sweep before :meth:`sample`
   is invoked. :meth:`set_current_record` then advances the lookup
   cursor to a specific record (one record per round, or one per
   cycle). The ``baseline_metric_extractor`` callable is the
   ``record_id -> float`` function used for the lookup (defaults to
   ``lambda record_id: baseline_metrics[record_id]``).

2. **Per-call current-record setter** — :meth:`set_current_record`
   is also exposed so the engine can wire the per-round record-id
   in a tight inner loop without rebuilding the mapping each round.

The cursor is reset to :data:`None` by :meth:`reset` and the
``baseline_metrics`` mapping can be replaced by a fresh
:meth:`set_baseline_metrics` call.

Tier boundary computation
-------------------------
Boundaries are computed once via :func:`_compute_tier_boundaries` from
the supplied baseline metric distribution. The default quantile
boundaries ``(0.33, 0.67)`` split records into three roughly equal
tiers. Tier assignment then is:

    hard    := baseline_metric <= q33
    medium  := q33 < baseline_metric <= q67
    easy    := baseline_metric > q67

For the k6 foldability axis this is ``baseline_pLDDT`` (lower = harder);
for Kanzi it is ``baseline_RMSD`` (lower = harder). The brief's
``baseline_metric_extractor`` defaults to identity on the supplied
``baseline_metrics`` values.

Conforms to :class:`SchedulerProtocol`. Pure w.r.t. arguments (the
tier cursor and the baseline metric mapping are state, mutated only
through the explicit setter methods; ``record_round_feedback`` is
delegated to the base scheduler).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.contracts import (
    CosineScheduleSample,
    hash_artifact,
)

from .adaptive import CodimensionSheetScheduler
from .protocols import ScheduleSample

# Default tier quantile boundaries (Wave 198 P3 / Wave 225 P4 / Wave 225 P5).
DEFAULT_TIER_QUANTILES: tuple[float, float] = (0.33, 0.67)


def _compute_tier_boundaries(
    baseline_metrics: Mapping[Any, float] | NDArray[np.float64] | Iterable[float],
    quantiles: tuple[float, float] = DEFAULT_TIER_QUANTILES,
) -> tuple[float, float]:
    """Return the (q_low, q_high) quantile boundaries of the baseline metric.

    :param baseline_metrics: mapping / array / iterable of per-record
        baseline metric values. The function flattens to a 1-D numpy
        array and computes the requested quantiles.
    :param quantiles: two-tuple ``(q_low, q_high)`` in ``(0, 1)`` with
        ``q_low < q_high``. Defaults to ``(0.33, 0.67)`` per Wave 198 P3.
    :returns: ``(low_boundary, high_boundary)`` such that records with
        ``baseline_metric <= low_boundary`` are *hard*, those with
        ``low_boundary < baseline_metric <= high_boundary`` are
        *medium*, and those with ``baseline_metric > high_boundary``
        are *easy*. For higher-is-better metrics (e.g. baseline
        pLDDT) the natural ordering applies; for lower-is-better
        metrics (e.g. baseline RMSD) the same ordering holds (lower
        = hard, higher = easy) — the caller is responsible for
        whether the metric polarity matches the engine's convention.
    :raises ValueError: if quantiles are not strictly-ordered floats in
        ``(0, 1)`` or if the input is empty.
    """
    if (
        not isinstance(quantiles, tuple)
        or len(quantiles) != 2
        or not all(isinstance(q, (int, float)) and not isinstance(q, bool) for q in quantiles)
    ):
        raise ValueError(
            f"quantiles must be a 2-tuple of real numbers, got {quantiles!r}"
        )
    q_low = float(quantiles[0])
    q_high = float(quantiles[1])
    if not (0.0 < q_low < q_high < 1.0):
        raise ValueError(
            f"quantiles must satisfy 0 < q_low < q_high < 1, got {quantiles!r}"
        )

    if isinstance(baseline_metrics, Mapping):
        values = np.asarray(list(baseline_metrics.values()), dtype=float)
    else:
        values = np.asarray(list(baseline_metrics), dtype=float)

    if values.size == 0:
        raise ValueError("baseline_metrics is empty; cannot compute tier boundaries")
    if not np.all(np.isfinite(values)):
        raise ValueError("baseline_metrics contains non-finite values")

    low = float(np.quantile(values, q_low, method="linear"))
    high = float(np.quantile(values, q_high, method="linear"))
    return low, high


class TierAwareCodimensionSheetScheduler:
    """Tier-aware wrapper around :class:`CodimensionSheetScheduler`.

    Reduces the per-round ``n_cap`` by ``easy_tier_nfe_reduction_factor``
    on records whose baseline metric lies above the high quantile
    boundary (the *easy* tier), preserving the full ``n_cap`` envelope on
    hard / medium tiers.

    Tier assignment
    ---------------
    Records are stratified by 33rd / 67th percentile of the baseline
    metric (configurable via ``tier_quantile_boundaries``):

    * ``hard`` — ``baseline_metric <= q33``
    * ``medium`` — ``q33 < baseline_metric <= q67``
    * ``easy`` — ``baseline_metric > q67``

    The default ``easy_tier_nfe_reduction_factor=1.0`` is a safe
    no-op so the wrapper is byte-identical to the wrapped
    :class:`CodimensionSheetScheduler` until the engine opts in.

    State
    -----
    The wrapper holds three pieces of mutable state:

    * ``_baseline_metrics`` — a dict mapping ``record_id -> float``
      (the per-record baseline metric). Populated via
      :meth:`set_baseline_metrics`.
    * ``_tier_boundaries`` — the ``(low, high)`` quantile boundaries.
      Computed once from ``_baseline_metrics`` at
      :meth:`set_baseline_metrics` time (or lazily in
      :meth:`sample` if no mapping has been supplied).
    * ``_current_record_id`` — the record the engine is currently
      processing; advanced by :meth:`set_current_record`. ``None``
      means "no record set, fall through with full n_cap" (matches
      the legacy :class:`CodimensionSheetScheduler` behaviour).

    Conforms to :class:`SchedulerProtocol`.
    """

    family_name: str = "tier_aware_codimension"

    def __init__(
        self,
        base: CodimensionSheetScheduler | None = None,
        *,
        easy_tier_nfe_reduction_factor: float = 1.0,
        tier_quantile_boundaries: tuple[float, float] = DEFAULT_TIER_QUANTILES,
        baseline_metric_extractor: Callable[[Any], float] | None = None,
    ) -> None:
        """Construct the tier-aware scheduler.

        :param base: the wrapped :class:`CodimensionSheetScheduler`.
            Defaults to a fresh one with the canonical
            ``eps_implicit=0.05`` and the paper-aligned
            ``eps_direction="decreasing"`` (Wave 233 P3 default;
            matches the framework default since Wave 34).
        :param easy_tier_nfe_reduction_factor: the multiplicative
            reduction applied to ``n_cap`` on the easy tier. Must
            lie in ``(0, 1]``. ``1.0`` = no reduction (default,
            safe no-op); ``0.5`` = halve the ``n_cap`` on easy
            (matches the Wave 225 P4 / P5 counterfactual). The
            factor is **clipped into ``(0, 1]``** so a misconfigured
            value of ``0`` cannot silently zero out the easy tier.
        :param tier_quantile_boundaries: 2-tuple of quantiles
            ``(q_low, q_high)`` in ``(0, 1)`` with
            ``q_low < q_high``. Defaults to ``(0.33, 0.67)`` per
            Wave 198 P3.
        :param baseline_metric_extractor: callable mapping
            ``record_id -> baseline_metric``. If ``None``, the
            scheduler uses the pre-populated ``baseline_metrics``
            mapping (see :meth:`set_baseline_metrics`) as a direct
            lookup; if both are ``None``, the scheduler falls
            through to the full ``n_cap`` (no reduction) — a safe
            default that preserves :class:`CodimensionSheetScheduler`
            byte-stability for callers that have not configured
            tier-awareness.
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
        # Validate easy_tier_nfe_reduction_factor.
        if isinstance(easy_tier_nfe_reduction_factor, bool) or not isinstance(
            easy_tier_nfe_reduction_factor, (int, float)
        ):
            raise ValueError(
                "easy_tier_nfe_reduction_factor must be a real number, "
                f"got {easy_tier_nfe_reduction_factor!r}"
            )
        factor = float(easy_tier_nfe_reduction_factor)
        if not math.isfinite(factor):
            raise ValueError(
                f"easy_tier_nfe_reduction_factor must be finite, got {factor!r}"
            )
        if not (0.0 < factor <= 1.0):
            raise ValueError(
                "easy_tier_nfe_reduction_factor must lie in (0, 1], "
                f"got {factor!r}"
            )
        # Validate tier_quantile_boundaries (delegated to _compute_tier_boundaries).
        low, high = _compute_tier_boundaries(
            [0.0, 1.0],  # dummy values; only quantile validity is checked here
            tier_quantile_boundaries,
        )
        if baseline_metric_extractor is not None and not callable(baseline_metric_extractor):
            raise ValueError(
                "baseline_metric_extractor must be callable or None, "
                f"got {baseline_metric_extractor!r}"
            )

        self._base = base
        self._easy_tier_nfe_reduction_factor = float(factor)
        self._tier_quantile_boundaries: tuple[float, float] = (low, high)
        self._baseline_metric_extractor = baseline_metric_extractor
        self._baseline_metrics: dict[Any, float] = {}
        self._tier_boundaries: tuple[float, float] | None = None
        self._current_record_id: Any = None
        self._last_sample: ScheduleSample | None = None
        self._last_tier: str | None = None

        # Deterministic config hash capturing every input.
        self._config_hash_value = hash_artifact(
            {
                "algorithm": "tier_aware_codimension",
                "schedule_family": self.family_name,
                "base_config_hash": str(self._base.config_hash()),
                "easy_tier_nfe_reduction_factor": float(self._easy_tier_nfe_reduction_factor),
                "tier_quantile_boundaries": (
                    float(self._tier_quantile_boundaries[0]),
                    float(self._tier_quantile_boundaries[1]),
                ),
            }
        )

    # -- accessors --------------------------------------------------------

    @property
    def base(self) -> CodimensionSheetScheduler:
        """Return the wrapped :class:`CodimensionSheetScheduler`."""
        return self._base

    @property
    def easy_tier_nfe_reduction_factor(self) -> float:
        """Return the easy-tier multiplicative ``n_cap`` reduction factor."""
        return float(self._easy_tier_nfe_reduction_factor)

    @property
    def tier_quantile_boundaries(self) -> tuple[float, float]:
        """Return the configured ``(q_low, q_high)`` quantile boundaries."""
        return (float(self._tier_quantile_boundaries[0]), float(self._tier_quantile_boundaries[1]))

    @property
    def tier_boundaries(self) -> tuple[float, float] | None:
        """Return the computed ``(low, high)`` tier boundaries, or ``None``.

        ``None`` until :meth:`set_baseline_metrics` has been called
        (or the boundary has been computed lazily in :meth:`sample`).
        """
        if self._tier_boundaries is None:
            return None
        return (float(self._tier_boundaries[0]), float(self._tier_boundaries[1]))

    @property
    def baseline_metrics(self) -> Mapping[Any, float]:
        """Return a read-only view of the per-record baseline metric mapping."""
        return dict(self._baseline_metrics)

    @property
    def current_record_id(self) -> Any:
        """Return the current record identifier, or ``None``."""
        return self._current_record_id

    @property
    def last_tier(self) -> str | None:
        """Return the tier assigned to the most recent :meth:`sample` call.

        One of ``"hard"``, ``"medium"``, ``"easy"``, or ``None`` (no
        record set / safe-default fall-through).
        """
        return self._last_tier

    @property
    def last_sample(self) -> ScheduleSample | None:
        """Return the most recent sample, or ``None`` after :meth:`reset`."""
        return self._last_sample

    # -- state mutators ---------------------------------------------------

    def set_baseline_metrics(
        self,
        baseline_metrics: Mapping[Any, float] | None,
    ) -> tuple[float, float]:
        """Populate the per-record baseline metric mapping and recompute boundaries.

        :param baseline_metrics: a mapping ``record_id -> baseline_metric``.
            ``None`` clears the mapping (and resets
            :attr:`tier_boundaries` to ``None``).
        :returns: the computed ``(low, high)`` tier boundaries.
        :raises ValueError: if the mapping is empty when supplied.

        The boundaries are computed via :func:`_compute_tier_boundaries`
        using the configured :attr:`tier_quantile_boundaries`.
        """
        if baseline_metrics is None:
            self._baseline_metrics = {}
            self._tier_boundaries = None
            return (float("nan"), float("nan"))
        if not isinstance(baseline_metrics, Mapping):
            raise TypeError(
                "baseline_metrics must be a Mapping or None, "
                f"got {type(baseline_metrics).__name__}"
            )
        # Validate finite real-valued mapping.
        cleaned: dict[Any, float] = {}
        for k, v in baseline_metrics.items():
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise ValueError(
                    f"baseline_metrics[{k!r}] must be a real number, got {v!r}"
                )
            fv = float(v)
            if not math.isfinite(fv):
                raise ValueError(
                    f"baseline_metrics[{k!r}] must be finite, got {fv!r}"
                )
            cleaned[k] = fv
        if not cleaned:
            raise ValueError("baseline_metrics is empty; cannot compute tier boundaries")
        self._baseline_metrics = cleaned
        low, high = _compute_tier_boundaries(
            cleaned, self._tier_quantile_boundaries
        )
        self._tier_boundaries = (low, high)
        return (low, high)

    def set_current_record(self, record_id: Any) -> None:
        """Set the current record identifier for subsequent :meth:`sample` calls.

        :param record_id: opaque identifier the engine will pass to
            ``baseline_metric_extractor`` (or look up in
            :attr:`baseline_metrics`). ``None`` clears the cursor so
            :meth:`sample` falls through with the full ``n_cap``.
        """
        self._current_record_id = record_id

    # -- tier classification ----------------------------------------------

    def _classify_tier(self, baseline_metric: float) -> str:
        """Classify a record's baseline metric into hard / medium / easy."""
        if self._tier_boundaries is None:
            # No baseline metric mapping has been supplied; default to
            # medium (the safe fall-through).
            return "medium"
        low, high = self._tier_boundaries
        if baseline_metric <= low:
            return "hard"
        if baseline_metric <= high:
            return "medium"
        return "easy"

    # -- SchedulerProtocol ------------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the tier-aware capacity sample for one round.

        Pipeline:

        1. Ask the wrapped :class:`CodimensionSheetScheduler` for the
           base ``n_cap_base(r)`` (paper-quantity-driven base).
        2. Look up the current record's baseline metric (via
           ``baseline_metric_extractor`` or :attr:`baseline_metrics`)
           and classify it into hard / medium / easy. If no record is
           set, fall through with the full ``n_cap``.
        3. If the tier is ``easy``, multiply ``n_cap`` by
           :attr:`easy_tier_nfe_reduction_factor`. Otherwise pass
           through unchanged.
        4. Re-emit a :class:`ScheduleSample` carrying the base
           scheduler's audit codes plus a tier-aware marker so the
           audit trail can identify rounds whose ``n_cap`` was reduced
           by the tier-aware wrapper.
        """
        base_sample = self._base.sample(
            outer_cycle_id, round_in_cycle, target_round
        )
        base_n_cap = float(base_sample.n_cap)

        tier = "medium"
        if self._current_record_id is not None:
            try:
                if self._baseline_metric_extractor is not None:
                    metric_val = float(
                        self._baseline_metric_extractor(self._current_record_id)
                    )
                else:
                    metric_val = float(self._baseline_metrics[self._current_record_id])
            except (KeyError, TypeError, ValueError):
                metric_val = float("nan")
            tier = self._classify_tier(metric_val) if math.isfinite(metric_val) else "medium"

        if tier == "easy":
            effective_n_cap = float(base_n_cap) * float(self._easy_tier_nfe_reduction_factor)
            effective_n_cap = float(max(0.0, min(1.0, effective_n_cap)))
            tier_code = "tier_aware_easy_reduced"
        else:
            effective_n_cap = float(base_n_cap)
            tier_code = f"tier_aware_{tier}_passthrough"

        codes: tuple[str, ...] = base_sample.audit_codes + (
            tier_code,
            f"tier:{tier}",
            f"reduction_factor:{float(self._easy_tier_nfe_reduction_factor):.6f}",
        )

        sample = ScheduleSample(
            outer_cycle_id=int(base_sample.outer_cycle_id),
            round_in_cycle=int(round_in_cycle),
            cycle_length=int(base_sample.cycle_length),
            n_cap=float(effective_n_cap),
            n_min=float(base_sample.n_min),
            n_max=float(base_sample.n_max),
            u_r=float(base_sample.u_r),
            family=self.family_name,
            computed_at_round=int(target_round),
            schedule_hash=str(self._config_hash_value),
            audit_codes=codes,
            evidence_ratio=base_sample.evidence_ratio,
            eps_implicit=base_sample.eps_implicit,
        )
        self._last_sample = sample
        self._last_tier = tier
        return sample

    def cycle_length(self) -> int:
        """Return the configured cycle length (from the base scheduler)."""
        return self._base.cycle_length()

    def schedule_family(self) -> str:
        """Return ``"tier_aware_codimension"``."""
        return self.family_name

    def config_hash(self) -> str:
        """Return a stable identifier for this algorithm + config choice."""
        return str(self._config_hash_value)

    def reset(self) -> None:
        """Clear all wrapper state and delegate to the base scheduler."""
        self._last_sample = None
        self._last_tier = None
        self._current_record_id = None
        # Intentionally retain _baseline_metrics and _tier_boundaries so
        # the engine can re-run the same cycle without re-supplying the
        # mapping. Call :meth:`set_baseline_metrics(None)` explicitly
        # to clear.
        self._base.reset()

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float] | None = None,
    ) -> None:
        """Delegate to the wrapped :class:`CodimensionSheetScheduler`.

        The tier-aware wrapper is a stateless modifier (it does not
        consume per-round oracle feedback); per-round feedback is
        forwarded to the base scheduler so its own convergence
        detection / paper-quantity shift logic continues to work.
        """
        self._base.record_round_feedback(round_in_cycle, metrics)

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Return the state with fresh noise injected (delegated to base).

        The tier-aware wrapper does not change the noise mass
        semantics: the wrapped :class:`CodimensionSheetScheduler` uses
        its cached paper-quantity ``A_g`` (when configured) as the
        noise mass, with the paper-aligned exterior-gap floor from
        Lemma 5. The tier-aware ``n_cap`` reduction in :meth:`sample`
        is informational only — the noise injection uses the base
        scheduler's invariant noise mass so the per-round injection
        is reproducible given the generator's seed.
        """
        return self._base.inject_noise(
            state, schedule_sample, generator=generator
        )


__all__ = [
    "DEFAULT_TIER_QUANTILES",
    "TierAwareCodimensionSheetScheduler",
    "_compute_tier_boundaries",
]

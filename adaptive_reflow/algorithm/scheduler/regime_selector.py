"""RegimeAwareEpsSelector — enforce the Lemma 4 regime on ``eps(r)``.

Phase-4 / Design #3 of the FID-JMAA theorem-alignment workflow.

Problem
-------

The paper's Lemma 4 (line 110-113) bounds the posterior mass on the
physical complement by

    ``\\int_{T^c \\setminus \\bigcup_z I_z} p_eps <= e^{-e_rho/(2 eps^2)} = o(eps)``

and the ``o(eps)`` step is only valid while

    ``eps^2 < e_rho / log 2``            (the *Lemma 4 regime*)

with ``e_rho = min{rho^4, (1-rho)^2 eta^2}`` from
:func:`adaptive_reflow.contracts.paper_quantities.exterior_gap_e_rho`
(paper line 128).

Before this module the framework could *observe* a violation but never
*prevent* one:

* :class:`~adaptive_reflow.eval.fid_theorem_aligned.TheoremAlignedFID`
  surfaces ``regime_check_ok`` / ``regime_violations`` **after** the
  samples exist — diagnosis, not enforcement;
* :class:`~adaptive_reflow.algorithm.scheduler.evidence_driven.EvidenceDrivenScheduler`
  drives ``eps_implicit`` from a PID-lite controller on
  ``evidence_ratio`` and never consults ``e_rho``, so a
  large-``eps_implicit_base`` configuration silently leaves the regime
  and the resulting FID trajectory is no longer grounded in the
  theorem.

This module supplies the missing *upper bound* as a pluggable,
opt-in selector: an abstract :class:`RegimeAwareEpsSelector` protocol
whose contract is

    ``select(eps_r, e_rho, *, slack) -> eps_{r+1}``
    with ``eps_{r+1} <= sqrt(e_rho / log 2) - slack``

plus two concrete implementations that pair the framework's existing
``eps`` trajectories with that bound:

* :class:`CosineAnnealRegimeSelector` — the cosine anneal of
  :class:`~adaptive_reflow.algorithm.scheduler._core.CosineAnnealScheduler`,
  bounded by the regime ceiling;
* :class:`ConvergenceAdaptiveRegimeSelector` — the PID-lite
  convergence controller of
  :class:`~adaptive_reflow.algorithm.scheduler._core.ConvergenceAdaptiveScheduler`,
  bounded by the same ceiling.

Module boundary
---------------

* **stdlib-only**. No ``torch``, no ``numpy``, no I/O, no global state
  beyond per-instance controller memory. Safe to import from the
  contracts-adjacent algorithm layer.
* The regime predicate is re-derived here from ``math`` primitives
  rather than imported from :mod:`adaptive_reflow.eval` — the
  algorithm layer must not depend on the eval layer. The two
  implementations are pinned bit-for-bit equal by
  ``tests/test_algorithm/test_regime_selector.py::test_regime_predicate_matches_fid_module``.
* Every selector is a value object: :meth:`select` never mutates its
  arguments, and the only mutable state is the explicit per-round
  controller memory cleared by :meth:`reset`.

Opt-in
------

Nothing in this module changes existing behaviour. Selectors are
consumed only when a caller constructs
:class:`EvidenceDrivenScheduler` with ``regime_aware=True`` (see that
class's docstring); with the default ``regime_aware=False`` the
scheduler's ``eps_implicit`` path stays byte-identical to Phase 3.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Module-level constants (canonical audit codes + defaults)
# ---------------------------------------------------------------------------

#: Audit code emitted when the requested ``eps_{r+1}`` exceeded the
#: Lemma 4 ceiling and was clamped down to it. Carries the requested
#: value, the ceiling and the applied value so an audit reader can
#: reconstruct exactly how far outside the regime the schedule wanted
#: to step.
EPS_REGIME_CLAMPED: str = "eps_regime_clamped"

#: Audit code emitted when the ceiling itself is unusable — either
#: ``e_rho <= 0`` (degenerate paper quantities) or the ceiling falls
#: below :data:`EPS_FLOOR`, meaning *no* positive ``eps`` can satisfy
#: the regime for this ``e_rho``. The selector then returns the floor
#: and the caller is expected to surface the warning.
EPS_REGIME_INFEASIBLE: str = "eps_regime_infeasible"

#: Audit code emitted when the proposal already satisfied the regime
#: (no clamp was needed). Present on every regime-aware round so the
#: audit trail proves the check ran rather than silently no-op'd.
EPS_REGIME_OK: str = "eps_regime_ok"

#: Human-readable warning prefix pushed onto the scheduler's regime
#: log (``EvidenceDrivenScheduler.regime_violation_warnings``) whenever
#: a clamp or an infeasible ceiling occurs.
REGIME_VIOLATION_WARNING: str = "regime_violation_warning"

#: Default strict-inequality slack. Lemma 4 requires a *strict*
#: inequality ``eps^2 < e_rho / log 2``; the ceiling is therefore
#: ``sqrt(e_rho / log 2) - slack`` so the returned ``eps`` satisfies
#: the strict form in floating point.
DEFAULT_REGIME_SLACK: float = 1e-9

#: Lower bound on any emitted ``eps``. Mirrors the ``1e-6`` floor the
#: :class:`EvidenceDrivenScheduler` already applies to
#: ``ScheduleSample.eps_implicit`` so a downstream evaluator never
#: receives a non-positive epsilon.
EPS_FLOOR: float = 1e-6


# ---------------------------------------------------------------------------
# Pure regime helpers
# ---------------------------------------------------------------------------


def regime_ceiling(e_rho: float, *, slack: float = DEFAULT_REGIME_SLACK) -> float:
    """Return the Lemma 4 ceiling ``sqrt(e_rho / log 2) - slack``.

    Any ``eps`` at or below the returned value satisfies the regime
    ``eps^2 < e_rho / log 2`` (the ``slack`` subtraction turns the
    non-strict floating-point comparison into the paper's strict one).

    Returns ``0.0`` for degenerate ``e_rho <= 0`` and for the case
    where ``slack`` swallows the whole bound, so callers can treat
    "ceiling <= EPS_FLOOR" as the single infeasibility test.

    Byte-stability: pure :mod:`math` primitives; two calls with
    identical inputs return bit-identical floats.
    """
    e_rho_f = float(e_rho)
    slack_f = float(slack)
    if not math.isfinite(e_rho_f) or e_rho_f <= 0.0:
        return 0.0
    if not math.isfinite(slack_f) or slack_f < 0.0:
        raise ValueError(f"slack must be finite and >= 0, got {slack!r}")
    raw = math.sqrt(e_rho_f / math.log(2.0))
    return float(max(0.0, raw - slack_f))


def regime_holds(eps: float, e_rho: float) -> bool:
    """Return ``True`` iff ``eps^2 < e_rho / log 2`` (Lemma 4 regime).

    Bit-for-bit the same predicate as
    ``adaptive_reflow.eval.fid_theorem_aligned._regime_check`` — the
    duplication is deliberate (the algorithm layer must not import the
    eval layer) and is pinned by a test that compares the two
    implementations over a grid.

    Returns ``False`` on degenerate inputs (``eps <= 0`` or
    ``e_rho <= 0``) so call sites need no extra guards.
    """
    if eps <= 0.0 or e_rho <= 0.0:
        return False
    return float(eps) ** 2 < float(e_rho) / math.log(2.0)


@dataclass(frozen=True)
class RegimeSelection:
    """Full result of one :meth:`RegimeAwareEpsSelector.select_detailed` call.

    :param eps_next: the selected ``eps_{r+1}`` (already clamped and
        floored). Always ``<= ceiling`` whenever ``feasible`` is True.
    :param eps_requested: the selector's unbounded proposal, before the
        regime clamp. Equal to ``eps_next`` when no clamp fired.
    :param eps_prev: the ``eps_r`` the proposal was derived from.
    :param e_rho: the exterior-gap paper quantity the ceiling came from.
    :param ceiling: ``sqrt(e_rho / log 2) - slack``.
    :param slack: the strict-inequality slack used for the ceiling.
    :param clamped: True iff ``eps_requested > ceiling`` and the value
        was reduced.
    :param feasible: True iff the ceiling is usable
        (``ceiling > EPS_FLOOR``). False means no positive ``eps``
        satisfies the regime for this ``e_rho``.
    :param regime_check_ok: :func:`regime_holds` evaluated on the
        *returned* ``eps_next`` — the same flag
        ``TheoremAlignedFIDResult.regime_check_ok`` reports downstream.
    :param audit_codes: canonical audit codes for the ledger.
    :param warning: human-readable warning, or ``None`` when the
        proposal was already inside the regime.
    """

    eps_next: float
    eps_requested: float
    eps_prev: float
    e_rho: float
    ceiling: float
    slack: float
    clamped: bool
    feasible: bool
    regime_check_ok: bool
    audit_codes: tuple[str, ...]
    warning: str | None = None

    def as_metrics(self) -> dict[str, float]:
        """Return a flat float dict for per-round metric emission."""
        return {
            "eps_next": float(self.eps_next),
            "eps_requested": float(self.eps_requested),
            "eps_regime_ceiling": float(self.ceiling),
            "eps_regime_clamped": 1.0 if self.clamped else 0.0,
            "eps_regime_feasible": 1.0 if self.feasible else 0.0,
            "eps_regime_check_ok": 1.0 if self.regime_check_ok else 0.0,
        }


# ---------------------------------------------------------------------------
# Abstract protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class RegimeAwareEpsSelector(Protocol):
    """Abstract per-round ``eps`` selector bounded by the Lemma 4 regime.

    The contract every implementation must honour:

    1. ``select(eps_r, e_rho, *, slack) -> eps_{r+1}`` returns a float
       with ``eps_{r+1} <= regime_ceiling(e_rho, slack=slack)``
       whenever that ceiling exceeds :data:`EPS_FLOOR`;
    2. the returned value is always ``>= EPS_FLOOR`` and finite (a
       degenerate or infeasible ``e_rho`` yields the floor, never
       ``0``, ``NaN`` or a negative number);
    3. :meth:`select` is pure with respect to its arguments — the
       ``eps_r`` / ``e_rho`` inputs are never mutated, and any
       controller memory is advanced only through
       :meth:`observe_round_feedback` / the explicit ``round_index``
       argument;
    4. :meth:`select_detailed` returns the same ``eps_next`` as
       :meth:`select` for identical arguments, plus the audit trail.

    Implementations are *upper-bound enforcers*, not schedules in their
    own right: each wraps an existing framework ``eps`` trajectory
    (cosine anneal, convergence-adaptive PID) and applies the regime
    ceiling on top. That keeps the paper bound orthogonal to the
    schedule family — a new family only has to supply its proposal.
    """

    def family(self) -> str:
        """Return the selector family identifier (e.g. ``cosine_anneal``)."""
        ...

    def select(
        self,
        eps_r: float,
        e_rho: float,
        *,
        slack: float = DEFAULT_REGIME_SLACK,
        round_index: int | None = None,
    ) -> float:
        """Return ``eps_{r+1} <= sqrt(e_rho / log 2) - slack``."""
        ...

    def select_detailed(
        self,
        eps_r: float,
        e_rho: float,
        *,
        slack: float = DEFAULT_REGIME_SLACK,
        round_index: int | None = None,
    ) -> RegimeSelection:
        """Return the full :class:`RegimeSelection` for one round."""
        ...

    def observe_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Optional hook: feed per-round oracle metrics to the selector."""
        ...

    def reset(self) -> None:
        """Clear controller memory so the selector can be re-run."""
        ...

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (replay contract)."""
        ...


# ---------------------------------------------------------------------------
# Shared base: proposal -> regime clamp (template method)
# ---------------------------------------------------------------------------


class _BaseRegimeSelector:
    """Shared clamp machinery for :class:`RegimeAwareEpsSelector` impls.

    Subclasses implement :meth:`_propose` (the family's *unbounded*
    ``eps_{r+1}``); this base applies the regime ceiling, the
    :data:`EPS_FLOOR`, and builds the audit trail. Concentrating the
    clamp here means the Lemma 4 bound is implemented exactly once —
    a new family cannot accidentally ship a weaker check.
    """

    FAMILY: str = "regime_base"

    def __init__(self, *, eps_floor: float = EPS_FLOOR) -> None:
        floor = float(eps_floor)
        if not math.isfinite(floor) or floor <= 0.0:
            raise ValueError(f"eps_floor must be finite and > 0, got {eps_floor!r}")
        self._eps_floor = floor
        self._call_count: int = 0

    # -- subclass hook -----------------------------------------------------

    def _propose(self, eps_r: float, round_index: int) -> float:
        """Return the family's unbounded ``eps_{r+1}`` proposal."""
        raise NotImplementedError  # pragma: no cover - abstract hook

    # -- RegimeAwareEpsSelector -------------------------------------------

    def family(self) -> str:
        """Return the selector family identifier."""
        return str(self.FAMILY)

    def select(
        self,
        eps_r: float,
        e_rho: float,
        *,
        slack: float = DEFAULT_REGIME_SLACK,
        round_index: int | None = None,
    ) -> float:
        """Return ``eps_{r+1}`` bounded by the Lemma 4 ceiling."""
        return float(
            self.select_detailed(
                eps_r, e_rho, slack=slack, round_index=round_index,
            ).eps_next
        )

    def select_detailed(
        self,
        eps_r: float,
        e_rho: float,
        *,
        slack: float = DEFAULT_REGIME_SLACK,
        round_index: int | None = None,
    ) -> RegimeSelection:
        """Propose ``eps_{r+1}``, clamp it into the regime, and audit it."""
        eps_prev = float(eps_r)
        if not math.isfinite(eps_prev) or eps_prev <= 0.0:
            raise ValueError(f"eps_r must be finite and > 0, got {eps_r!r}")
        idx = self._call_count if round_index is None else int(round_index)
        if idx < 0:
            raise ValueError(f"round_index must be >= 0, got {round_index!r}")
        self._call_count = idx + 1

        requested = float(self._propose(eps_prev, idx))
        if not math.isfinite(requested):
            raise ValueError(
                f"{type(self).__name__}._propose returned non-finite "
                f"{requested!r} for eps_r={eps_prev!r}"
            )
        requested = max(self._eps_floor, requested)

        ceiling = regime_ceiling(e_rho, slack=slack)
        feasible = ceiling > self._eps_floor
        codes: tuple[str, ...] = ()
        warning: str | None = None

        if not feasible:
            eps_next = self._eps_floor
            codes = codes + (
                f"{EPS_REGIME_INFEASIBLE}:e_rho={float(e_rho):.9g}"
                f":ceiling={ceiling:.9g}:floor={self._eps_floor:.9g}",
            )
            warning = (
                f"{REGIME_VIOLATION_WARNING}: Lemma 4 ceiling "
                f"{ceiling:.9g} for e_rho={float(e_rho):.9g} is at or below "
                f"the eps floor {self._eps_floor:.9g}; no positive eps can "
                f"satisfy eps^2 < e_rho/log(2). Emitting the floor and "
                f"leaving the regime — widen e_rho (rho / eta) to recover."
            )
        elif requested > ceiling:
            eps_next = ceiling
            codes = codes + (
                f"{EPS_REGIME_CLAMPED}:requested={requested:.9g}"
                f":ceiling={ceiling:.9g}:applied={eps_next:.9g}",
            )
            warning = (
                f"{REGIME_VIOLATION_WARNING}: {self.family()} proposed "
                f"eps={requested:.9g} which violates the Lemma 4 regime "
                f"eps^2 < e_rho/log(2) for e_rho={float(e_rho):.9g}; "
                f"clamped to the ceiling {ceiling:.9g}."
            )
        else:
            eps_next = requested
            codes = codes + (
                f"{EPS_REGIME_OK}:eps={eps_next:.9g}:ceiling={ceiling:.9g}",
            )

        return RegimeSelection(
            eps_next=float(eps_next),
            eps_requested=float(requested),
            eps_prev=float(eps_prev),
            e_rho=float(e_rho),
            ceiling=float(ceiling),
            slack=float(slack),
            clamped=bool(requested > ceiling and feasible),
            feasible=bool(feasible),
            regime_check_ok=bool(regime_holds(float(eps_next), float(e_rho))),
            audit_codes=codes,
            warning=warning,
        )

    def observe_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """No-op by default; adaptive families override."""
        return None

    def reset(self) -> None:
        """Clear the internal call counter (subclasses extend)."""
        self._call_count = 0

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict."""
        return {"family": str(self.FAMILY), "eps_floor": float(self._eps_floor)}


# ---------------------------------------------------------------------------
# Concrete #1 — cosine anneal bounded by the regime
# ---------------------------------------------------------------------------


class CosineAnnealRegimeSelector(_BaseRegimeSelector):
    """Cosine-annealed ``eps`` trajectory bounded by the Lemma 4 ceiling.

    Mirrors the framework's canonical
    :class:`~adaptive_reflow.algorithm.scheduler._core.CosineAnnealScheduler`
    shape, transposed from ``n_cap`` onto ``eps``: the proposal
    contracts ``eps_r`` toward ``eps_min`` along a half-cosine over
    ``period_rounds`` rounds,

        ``phase   = min(1, (r + 1) / period_rounds)``
        ``factor  = 0.5 * (1 + cos(pi * phase))``
        ``eps_raw = eps_min + (eps_r - eps_min) * factor``

    so ``eps_raw == eps_r`` at ``r = -1`` (never sampled), decreases
    monotonically in ``r``, and reaches ``eps_min`` exactly at
    ``r + 1 = period_rounds``. Paper Theorem 1 predicts the evidence
    ratio rises as ``eps -> 0``, so a monotone contraction is the
    theorem-aligned default; the regime ceiling then caps the *first*
    rounds, which are precisely where a large ``eps_implicit_base``
    would otherwise sit outside Lemma 4's regime.

    :param period_rounds: rounds after which the proposal reaches
        ``eps_min``. Must be ``>= 1``.
    :param eps_min: asymptotic floor of the cosine ramp (clamped up to
        ``eps_floor``).
    :param eps_floor: hard lower bound on any emitted ``eps``.
    """

    FAMILY: str = "cosine_anneal"

    def __init__(
        self,
        *,
        period_rounds: int = 8,
        eps_min: float = EPS_FLOOR,
        eps_floor: float = EPS_FLOOR,
    ) -> None:
        super().__init__(eps_floor=eps_floor)
        period = int(period_rounds)
        if period < 1:
            raise ValueError(f"period_rounds must be >= 1, got {period_rounds!r}")
        eps_min_f = float(eps_min)
        if not math.isfinite(eps_min_f) or eps_min_f <= 0.0:
            raise ValueError(f"eps_min must be finite and > 0, got {eps_min!r}")
        self._period_rounds = period
        self._eps_min = max(eps_min_f, self._eps_floor)

    @property
    def period_rounds(self) -> int:
        """Return the configured cosine period in rounds."""
        return int(self._period_rounds)

    @property
    def eps_min(self) -> float:
        """Return the configured asymptotic ``eps`` floor."""
        return float(self._eps_min)

    def _propose(self, eps_r: float, round_index: int) -> float:
        """Return the half-cosine contraction of ``eps_r``."""
        eps_min = float(self._eps_min)
        if eps_r <= eps_min:
            # Already at (or below) the asymptote — hold, do not grow.
            return float(eps_r)
        phase = min(1.0, float(round_index + 1) / float(self._period_rounds))
        factor = 0.5 * (1.0 + math.cos(math.pi * phase))
        return float(eps_min + (float(eps_r) - eps_min) * factor)

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict."""
        out = super().to_config()
        out["period_rounds"] = int(self._period_rounds)
        out["eps_min"] = float(self._eps_min)
        return out

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> CosineAnnealRegimeSelector:
        """Rebuild a selector from :meth:`to_config` output."""
        return cls(
            period_rounds=int(config.get("period_rounds", 8)),
            eps_min=float(config.get("eps_min", EPS_FLOOR)),
            eps_floor=float(config.get("eps_floor", EPS_FLOOR)),
        )


# ---------------------------------------------------------------------------
# Concrete #2 — convergence-adaptive PID bounded by the regime
# ---------------------------------------------------------------------------

#: Default feedback metric consumed by
#: :class:`ConvergenceAdaptiveRegimeSelector`, in priority order. The
#: first key present (and finite) in the round's metric mapping drives
#: the controller. ``W2`` matches
#: :class:`ConvergenceAdaptiveScheduler`'s primary signal; the
#: ``evidence_ratio`` / ``selection_ratio`` fallbacks match
#: :class:`EvidenceDrivenScheduler`'s.
DEFAULT_CONVERGENCE_METRIC_KEYS: tuple[str, ...] = (
    "W2",
    "evidence_ratio",
    "selection_ratio",
)


class ConvergenceAdaptiveRegimeSelector(_BaseRegimeSelector):
    """PID-lite convergence-adaptive ``eps`` proposal, regime-bounded.

    The ``eps`` analogue of
    :class:`~adaptive_reflow.algorithm.scheduler._core.ConvergenceAdaptiveScheduler`:
    a proportional + derivative controller on the per-round
    convergence metric (default ``W2``, falling back to
    ``evidence_ratio`` / ``selection_ratio``) chooses a *contraction
    factor* ``gamma`` for ``eps``,

        ``ratio      = w[-1] / w[-2]``          (loss ratio; < 1 = improving)
        ``improve    = max(0, 1 - ratio)``
        ``regress    = max(0, ratio - 1)``
        ``gamma      = clip(1 - kp * improve + kd * regress, gamma_min, 1)``
        ``eps_raw    = max(eps_min, eps_r * gamma)``

    Reading: a converging round earns a faster ``eps`` contraction (the
    paper's asymptotic direction); a regressing round holds ``eps``
    steady (``gamma -> 1``) rather than growing it, because Theorem 1
    gives no guarantee for an increasing ``eps``. Rounds before the
    second observation, and non-finite metrics, leave ``gamma = 1`` so
    the selector degrades to "hold ``eps_r``, clamp to the regime" —
    the conservative behaviour.

    An EMA (``ema``) smooths the metric history exactly as
    :class:`ConvergenceAdaptiveScheduler` does, so a single noisy
    oracle round cannot swing the contraction.

    :param kp: proportional gain on the improvement fraction.
    :param kd: gain on the regression fraction (``gamma`` grows back
        toward 1, never above it).
    :param gamma_min: floor on the per-round contraction factor.
    :param ema: smoothing factor for the metric history in ``[0, 1]``
        (``0`` = no smoothing).
    :param eps_min: asymptotic floor of the contraction.
    :param metric_keys: feedback keys tried in order.
    :param eps_floor: hard lower bound on any emitted ``eps``.
    """

    FAMILY: str = "convergence_adaptive"

    def __init__(
        self,
        *,
        kp: float = 0.10,
        kd: float = 0.05,
        gamma_min: float = 0.5,
        ema: float = 0.3,
        eps_min: float = EPS_FLOOR,
        metric_keys: tuple[str, ...] = DEFAULT_CONVERGENCE_METRIC_KEYS,
        eps_floor: float = EPS_FLOOR,
    ) -> None:
        super().__init__(eps_floor=eps_floor)
        for name, val in (("kp", kp), ("kd", kd), ("gamma_min", gamma_min), ("ema", ema)):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"{name} must be a real number, got {val!r}")
            if not math.isfinite(float(val)):
                raise ValueError(f"{name} must be finite, got {val!r}")
        if float(kp) < 0.0 or float(kd) < 0.0:
            raise ValueError(
                f"kp / kd must be >= 0, got kp={kp!r}, kd={kd!r}"
            )
        if not 0.0 < float(gamma_min) <= 1.0:
            raise ValueError(
                f"gamma_min must lie in (0, 1], got {gamma_min!r}"
            )
        if not 0.0 <= float(ema) <= 1.0:
            raise ValueError(f"ema must lie in [0, 1], got {ema!r}")
        eps_min_f = float(eps_min)
        if not math.isfinite(eps_min_f) or eps_min_f <= 0.0:
            raise ValueError(f"eps_min must be finite and > 0, got {eps_min!r}")
        keys = tuple(str(k) for k in metric_keys)
        if not keys:
            raise ValueError("metric_keys must not be empty")
        self._kp = float(kp)
        self._kd = float(kd)
        self._gamma_min = float(gamma_min)
        self._ema = float(ema)
        self._eps_min = max(eps_min_f, self._eps_floor)
        self._metric_keys = keys
        # Mutable controller memory — cleared by reset().
        self._history: list[float] = []
        self._smoothed: float | None = None
        self._last_metric_key: str | None = None

    # -- accessors ---------------------------------------------------------

    @property
    def history(self) -> tuple[float, ...]:
        """Return the smoothed metric history (oldest first)."""
        return tuple(self._history)

    @property
    def last_metric_key(self) -> str | None:
        """Return the feedback key that last drove the controller."""
        return self._last_metric_key

    @property
    def metric_keys(self) -> tuple[str, ...]:
        """Return the configured feedback keys (priority order)."""
        return tuple(self._metric_keys)

    def contraction_factor(self) -> float:
        """Return the current ``gamma`` implied by the metric history."""
        if len(self._history) < 2:
            return 1.0
        prev = float(self._history[-2])
        cur = float(self._history[-1])
        denom = abs(prev)
        if denom <= 0.0 or not math.isfinite(denom):
            return 1.0
        ratio = cur / prev if prev != 0.0 else 1.0
        if not math.isfinite(ratio):
            return 1.0
        improve = max(0.0, 1.0 - ratio)
        regress = max(0.0, ratio - 1.0)
        gamma = 1.0 - self._kp * improve + self._kd * regress
        return float(max(self._gamma_min, min(1.0, gamma)))

    # -- feedback ----------------------------------------------------------

    def observe_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Fold the round's convergence metric into the controller memory.

        Ignores rounds whose metrics carry none of :attr:`metric_keys`
        (or only non-finite values) — neither the history nor the EMA
        moves, so a broken oracle cannot poison the contraction.
        """
        value: float | None = None
        key_used: str | None = None
        for key in self._metric_keys:
            if key in metrics:
                candidate = float(metrics[key])
                if math.isfinite(candidate):
                    value = candidate
                    key_used = key
                    break
        if value is None:
            return None
        self._last_metric_key = key_used
        if self._smoothed is None:
            self._smoothed = float(value)
        else:
            self._smoothed = (
                self._ema * float(self._smoothed) + (1.0 - self._ema) * float(value)
            )
        self._history.append(float(self._smoothed))
        # Bound the memory: the controller only reads the last two entries.
        if len(self._history) > 64:
            del self._history[:-64]
        return None

    def _propose(self, eps_r: float, round_index: int) -> float:
        """Return ``eps_r`` scaled by the PID-lite contraction factor."""
        eps_min = float(self._eps_min)
        if eps_r <= eps_min:
            return float(eps_r)
        gamma = self.contraction_factor()
        return float(max(eps_min, float(eps_r) * gamma))

    def reset(self) -> None:
        """Clear the metric history, the EMA and the call counter."""
        super().reset()
        self._history.clear()
        self._smoothed = None
        self._last_metric_key = None

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict."""
        out = super().to_config()
        out.update(
            {
                "kp": float(self._kp),
                "kd": float(self._kd),
                "gamma_min": float(self._gamma_min),
                "ema": float(self._ema),
                "eps_min": float(self._eps_min),
                "metric_keys": list(self._metric_keys),
            }
        )
        return out

    @classmethod
    def from_config(
        cls, config: Mapping[str, Any],
    ) -> ConvergenceAdaptiveRegimeSelector:
        """Rebuild a selector from :meth:`to_config` output."""
        keys_raw = config.get("metric_keys")
        keys = (
            DEFAULT_CONVERGENCE_METRIC_KEYS
            if keys_raw is None
            else tuple(str(k) for k in keys_raw)
        )
        return cls(
            kp=float(config.get("kp", 0.10)),
            kd=float(config.get("kd", 0.05)),
            gamma_min=float(config.get("gamma_min", 0.5)),
            ema=float(config.get("ema", 0.3)),
            eps_min=float(config.get("eps_min", EPS_FLOOR)),
            metric_keys=keys,
            eps_floor=float(config.get("eps_floor", EPS_FLOOR)),
        )


# ---------------------------------------------------------------------------
# Registry + factory (interface-framework separation)
# ---------------------------------------------------------------------------

#: Family identifier → concrete selector class. Mirrors
#: ``SCHEDULER_REGISTRY`` so a caller can name a selector in a config
#: file without importing the concrete type.
REGIME_SELECTOR_REGISTRY: dict[str, type[_BaseRegimeSelector]] = {
    CosineAnnealRegimeSelector.FAMILY: CosineAnnealRegimeSelector,
    ConvergenceAdaptiveRegimeSelector.FAMILY: ConvergenceAdaptiveRegimeSelector,
}


def build_regime_selector(
    family: str = CosineAnnealRegimeSelector.FAMILY,
    **kwargs: Any,
) -> RegimeAwareEpsSelector:
    """Build a selector by family name.

    :raises ValueError: when ``family`` is not in
        :data:`REGIME_SELECTOR_REGISTRY`.
    """
    key = str(family)
    cls = REGIME_SELECTOR_REGISTRY.get(key)
    if cls is None:
        known = ", ".join(sorted(REGIME_SELECTOR_REGISTRY))
        raise ValueError(
            f"unknown regime selector family {family!r}; known families: {known}"
        )
    selector: RegimeAwareEpsSelector = cls(**kwargs)
    return selector


def default_e_rho_provider(
    *, rho: float = 0.1, eta: float = 0.1,
) -> Callable[[float], float]:
    """Return an ``e_rho_provider`` backed by the paper-quantities module.

    The returned callable ignores its ``round_index`` argument and
    yields the constant
    :func:`adaptive_reflow.contracts.paper_quantities.exterior_gap_e_rho`
    for ``(rho, eta)`` — the shape a per-round provider takes when the
    exterior gap is round-invariant (the paper's own setting). Callers
    with a round-varying ``rho`` supply their own callable.
    """
    from adaptive_reflow.contracts import paper_quantities as _pq

    e_rho = float(_pq.exterior_gap_e_rho(rho=float(rho), eta=float(eta)))

    def _provider(_round_index: float) -> float:
        return e_rho

    return _provider


__all__ = [
    "DEFAULT_CONVERGENCE_METRIC_KEYS",
    "DEFAULT_REGIME_SLACK",
    "EPS_FLOOR",
    "EPS_REGIME_CLAMPED",
    "EPS_REGIME_INFEASIBLE",
    "EPS_REGIME_OK",
    "REGIME_SELECTOR_REGISTRY",
    "REGIME_VIOLATION_WARNING",
    "ConvergenceAdaptiveRegimeSelector",
    "CosineAnnealRegimeSelector",
    "RegimeAwareEpsSelector",
    "RegimeSelection",
    "build_regime_selector",
    "default_e_rho_provider",
    "regime_ceiling",
    "regime_holds",
]

"""Evidence-driven scheduling + heuristic-mode diagnostics (P0 #9, P1).

Two framework-INTERNAL scheduler uplifts, both delivered as *wrappers*
so :mod:`adaptive_reflow.algorithm.scheduler` is untouched and every
existing schedule family keeps its exact behaviour.

1. **Evidence-driver mode (P0 #9).**
   :class:`~adaptive_reflow.algorithm.scheduler.CodimensionSheetScheduler`
   computes the paper's sheet-vs-cell evidence ratio every round
   (Lemma 2 / Lemma 3) and publishes it on
   :attr:`~adaptive_reflow.algorithm.scheduler.ScheduleSample.evidence_ratio`
   — but never *uses* it. The ratio is reported and then discarded, so
   the schedule's capacity ramp is blind to the very quantity Theorem 1
   says drives posterior selection.

   :class:`EvidenceDrivenScheduler` closes the loop: it modulates the
   inner scheduler's ``n_cap`` by the round's evidence ratio, so rounds
   in which the sheet already dominates spend less capacity on fresh
   noise and the terminal selection ratio is pushed toward ``1``.

2. **Heuristic-mode asymptotic diagnostic (P1).**
   ``_paper_evidence_balance`` silently falls back to a framework-side
   heuristic when no ``profile_residual_fn`` is supplied. The heuristic
   and the paper-quantity form agree on the *direction* of sheet
   dominance but not on its magnitude, and the gap widens as
   ``eps -> 0`` — precisely the regime Theorem 1 is about. Running a
   small ``eps_implicit`` without a profile therefore produces numbers
   that look paper-grounded and are not.
   :func:`check_evidence_mode` detects that configuration and
   :func:`warn_if_heuristic_evidence_mode` raises a
   :class:`UserWarning` naming the fix.

Quantitative targets
--------------------

* **Evidence driver**: the driven ``n_cap`` never exceeds the
  baseline's, and on a sheet-dominant terminal evidence ratio the
  terminal **memory fraction** (``1 - n_cap``) rises from the cosine
  baseline's documented ``0.85`` plateau to ``>= 0.99``.
* **Diagnostic coverage**: :func:`check_evidence_mode` flags **100 %**
  of schedulers configured with ``eps_implicit < 1e-3`` and no
  ``profile_residual_fn``, and **0 %** of correctly-configured ones (no
  false positives).

Both are asserted in ``tests/test_algorithm/test_evidence_driver.py``.
"""

from __future__ import annotations

import hashlib
import json
import math
import warnings
from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Optional

import numpy as np
from numpy.typing import NDArray

from adaptive_reflow.algorithm._derivation import (
    BLConvergenceEpsilonSchedule,
    DerivationContext,
    DerivationRule,
    MeanFlowFixedStrengthRule,
    MinGumbelTempRule,
    default_eps_implicit,
    default_min_gumbel_temp,
)
from adaptive_reflow.algorithm.scheduler import (
    SchedulerProtocol,
    ScheduleSample,
)
from adaptive_reflow.contracts import CosineScheduleSample

__all__ = [
    "EVIDENCE_DRIVEN_AUDIT_CODE",
    "EVIDENCE_DRIVEN_FAMILY_SUFFIX",
    "EVIDENCE_HEURISTIC_EPS_THRESHOLD",
    "EvidenceDrivenScheduler",
    "EvidenceModeReport",
    "check_evidence_mode",
    "derive_default_eps_threshold",
    "warn_if_heuristic_evidence_mode",
]


EVIDENCE_DRIVEN_AUDIT_CODE: str = "evidence_driven_n_cap"
"""Audit code appended to every sample the driver actually modulated."""

EVIDENCE_DRIVEN_FAMILY_SUFFIX: str = "_evidence_driven"
"""Suffix appended to the inner family name so the audit trail is unambiguous."""

EVIDENCE_HEURISTIC_EPS_THRESHOLD: float = 1e-3
"""``eps_implicit`` below which the heuristic evidence balance is unsound."""


# ---------------------------------------------------------------------------
# 1. Evidence-driver mode
# ---------------------------------------------------------------------------


class EvidenceDrivenScheduler:
    """Modulate an inner scheduler's ``n_cap`` by its per-round evidence ratio.

    Conforms to
    :class:`~adaptive_reflow.algorithm.scheduler.SchedulerProtocol` and
    delegates every method to the wrapped scheduler, so it is a drop-in
    at any call site that accepts a scheduler. The only thing it changes
    is the returned sample's ``n_cap``:

        n_cap' = n_cap * (1 - strength + strength * evidence_ratio)

    ``strength = 0`` is the identity (byte-identical to the inner
    scheduler); ``strength = 1`` is the full multiplicative drive
    ``n_cap * evidence_ratio`` described in the uplift plan. The affine
    form exists so the drive can be dialled in gradually rather than
    switched on as a cliff, which matters because the ratio is itself an
    estimate.

    The result is re-clipped into the inner sample's ``[n_min, n_max]``
    envelope, so the wrapper can never move capacity outside the range
    the inner family promised. Samples whose ``evidence_ratio`` is
    ``None`` — i.e. every family that does not compute a paper-quantity
    evidence balance — pass through **untouched** and without the audit
    code, so wrapping a non-codimension scheduler is a no-op rather than
    an error.

    :param inner: the scheduler to wrap.
    :param strength: drive strength in ``[0, 1]``.
    """

    def __init__(
        self,
        inner: SchedulerProtocol,
        *,
        strength: float = 1.0,
    ) -> None:
        if inner is None:
            raise ValueError("inner scheduler is required")
        for name in ("sample", "cycle_length", "schedule_family", "config_hash"):
            if not callable(getattr(inner, name, None)):
                raise ValueError(
                    f"inner must conform to SchedulerProtocol; missing {name!r}"
                )
        if isinstance(strength, bool) or not isinstance(strength, (int, float)):
            raise ValueError(f"strength must be a real number, got {strength!r}")
        s = float(strength)
        if not math.isfinite(s):
            raise ValueError(f"strength must be finite, got {strength!r}")
        if not (0.0 <= s <= 1.0):
            raise ValueError(f"strength must be in [0, 1], got {s!r}")
        self._inner = inner
        self._strength = s

    # -- introspection ----------------------------------------------------

    @property
    def inner(self) -> SchedulerProtocol:
        """Return the wrapped scheduler."""
        return self._inner

    @property
    def strength(self) -> float:
        """Return the configured drive strength."""
        return float(self._strength)

    # -- scheduler protocol ----------------------------------------------

    def sample(
        self,
        outer_cycle_id: int,
        round_in_cycle: int,
        target_round: int,
    ) -> ScheduleSample:
        """Return the inner sample with an evidence-modulated ``n_cap``."""
        base = self._inner.sample(outer_cycle_id, round_in_cycle, target_round)
        ratio = base.evidence_ratio
        if ratio is None or self._strength <= 0.0:
            return base
        r = float(ratio)
        if not math.isfinite(r):
            return base
        r = max(0.0, min(1.0, r))
        factor = (1.0 - self._strength) + self._strength * r
        driven = float(base.n_cap) * factor
        lo = float(min(base.n_min, base.n_max))
        hi = float(max(base.n_min, base.n_max))
        driven = max(lo, min(hi, driven))
        return replace(
            base,
            n_cap=driven,
            family=f"{base.family}{EVIDENCE_DRIVEN_FAMILY_SUFFIX}",
            audit_codes=tuple(base.audit_codes) + (EVIDENCE_DRIVEN_AUDIT_CODE,),
        )

    def cycle_length(self) -> int:
        """Return the inner scheduler's cycle length."""
        return int(self._inner.cycle_length())

    def schedule_family(self) -> str:
        """Return the inner family with the evidence-driven suffix."""
        return f"{self._inner.schedule_family()}{EVIDENCE_DRIVEN_FAMILY_SUFFIX}"

    def config_hash(self) -> str:
        """Return a digest over the inner config hash plus ``strength``."""
        payload = {
            "family": self.schedule_family(),
            "inner": str(self._inner.config_hash()),
            "strength": float(self._strength),
        }
        text = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def reset(self) -> None:
        """Reset the inner scheduler."""
        self._inner.reset()

    def record_round_feedback(
        self,
        round_in_cycle: int,
        metrics: Mapping[str, float],
    ) -> None:
        """Forward per-round feedback to the inner scheduler."""
        self._inner.record_round_feedback(round_in_cycle, metrics)

    def inject_noise(
        self,
        state: NDArray[np.float64],
        schedule_sample: CosineScheduleSample,
        *,
        generator: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Forward forward-noise injection to the inner scheduler.

        The wrapper deliberately does **not** re-scale the injected
        noise: the sample handed in here already carries the driven
        ``n_cap``, so modulating again would apply the evidence ratio
        twice.
        """
        return self._inner.inject_noise(
            state, schedule_sample, generator=generator
        )

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict."""
        inner_config: dict[str, Any] = {}
        to_config = getattr(self._inner, "to_config", None)
        if callable(to_config):
            inner_config = dict(to_config())
        return {
            "family": self.schedule_family(),
            "strength": float(self._strength),
            "inner": inner_config,
        }

    @classmethod
    def from_config(
        cls,
        config: dict[str, Any],
        *,
        inner: SchedulerProtocol | None = None,
    ) -> EvidenceDrivenScheduler:
        """Rebuild the wrapper around ``inner``.

        The inner scheduler must be supplied explicitly (or rebuilt by
        the caller from ``config["inner"]`` through
        :func:`~adaptive_reflow.algorithm.scheduler.build_scheduler_from_config`):
        the wrapper deliberately does not reach into the scheduler
        registry, so it stays usable with schedulers that were never
        registered.
        """
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        if inner is None:
            raise ValueError(
                "EvidenceDrivenScheduler.from_config requires an explicit "
                "``inner`` scheduler; rebuild it from config['inner'] first"
            )
        return cls(inner, strength=float(config.get("strength", 1.0)))


# ---------------------------------------------------------------------------
# 2. Heuristic-mode asymptotic diagnostic
# ---------------------------------------------------------------------------


class EvidenceModeReport:
    """Verdict on whether a scheduler's evidence balance is paper-grounded.

    Attributes
    ----------
    paper_grounded:
        ``True`` when the scheduler carries a ``profile_residual_fn``
        and therefore consumes the literal paper quantities.
    eps_implicit:
        The scheduler's implicit noise scale (``None`` when it does not
        expose one — i.e. it is not a codimension family at all).
    asymptotic_risk:
        ``True`` when the scheduler runs the heuristic balance at an
        ``eps_implicit`` small enough that the heuristic and the paper
        form materially disagree.
    message:
        Human-readable explanation; empty when there is nothing to say.
    """

    __slots__ = ("asymptotic_risk", "eps_implicit", "message", "paper_grounded")

    def __init__(
        self,
        *,
        paper_grounded: bool,
        eps_implicit: float | None,
        asymptotic_risk: bool,
        message: str,
    ) -> None:
        self.paper_grounded = bool(paper_grounded)
        self.eps_implicit = eps_implicit
        self.asymptotic_risk = bool(asymptotic_risk)
        self.message = str(message)

    def __repr__(self) -> str:
        """Return a debug representation."""
        return (
            f"EvidenceModeReport(paper_grounded={self.paper_grounded!r}, "
            f"eps_implicit={self.eps_implicit!r}, "
            f"asymptotic_risk={self.asymptotic_risk!r})"
        )


def check_evidence_mode(
    scheduler: object,
    *,
    eps_threshold: float = EVIDENCE_HEURISTIC_EPS_THRESHOLD,
) -> EvidenceModeReport:
    """Return whether ``scheduler``'s evidence balance is paper-grounded.

    Duck-typed on purpose: any object exposing ``profile_residual_fn``
    and ``eps_implicit`` is inspected, so the check works on the
    codimension scheduler, on wrappers around it, and on test doubles
    alike. Objects that expose neither are reported as "not a
    codimension family" with no risk.

    :param scheduler: the object to inspect.
    :param eps_threshold: ``eps_implicit`` below which the heuristic is
        considered unsound.
    """
    if isinstance(eps_threshold, bool) or not isinstance(
        eps_threshold, (int, float)
    ):
        raise ValueError(f"eps_threshold must be a real number, got {eps_threshold!r}")
    thr = float(eps_threshold)
    if not math.isfinite(thr) or thr <= 0.0:
        raise ValueError(f"eps_threshold must be finite and > 0, got {eps_threshold!r}")

    profile = getattr(scheduler, "profile_residual_fn", None)
    raw_eps = getattr(scheduler, "eps_implicit", None)
    eps: float | None
    if isinstance(raw_eps, (int, float)) and not isinstance(raw_eps, bool):
        eps = float(raw_eps)
    else:
        eps = None

    if eps is None:
        return EvidenceModeReport(
            paper_grounded=profile is not None,
            eps_implicit=None,
            asymptotic_risk=False,
            message="",
        )
    if profile is not None:
        return EvidenceModeReport(
            paper_grounded=True,
            eps_implicit=eps,
            asymptotic_risk=False,
            message="",
        )
    if eps < thr:
        return EvidenceModeReport(
            paper_grounded=False,
            eps_implicit=eps,
            asymptotic_risk=True,
            message=(
                f"scheduler runs the framework-side heuristic evidence balance "
                f"at eps_implicit={eps!r} (< {thr!r}). In this asymptotic "
                f"regime the heuristic sheet/cell form and paper Theorem 1's "
                f"A_g / B_g / C_g form diverge in magnitude, so the reported "
                f"evidence_ratio is NOT paper-grounded. Pass a "
                f"``profile_residual_fn`` to CodimensionSheetScheduler to "
                f"switch to the paper-quantity mode."
            ),
        )
    return EvidenceModeReport(
        paper_grounded=False,
        eps_implicit=eps,
        asymptotic_risk=False,
        message="",
    )


def warn_if_heuristic_evidence_mode(
    scheduler: object,
    *,
    eps_threshold: float = EVIDENCE_HEURISTIC_EPS_THRESHOLD,
    stacklevel: int = 2,
) -> EvidenceModeReport:
    """Emit a :class:`UserWarning` when the heuristic mode is unsound.

    Returns the report either way, so a caller can branch on it without
    catching the warning. Nothing is emitted for a correctly-configured
    scheduler, which keeps the check safe to call unconditionally from
    runner / orchestrator wiring.
    """
    report = check_evidence_mode(scheduler, eps_threshold=eps_threshold)
    if report.asymptotic_risk:
        warnings.warn(report.message, UserWarning, stacklevel=int(stacklevel))
    return report


# ---------------------------------------------------------------------------
# Parameter-free default-eps-threshold entry point (DERIV-001 proof #3)
# ---------------------------------------------------------------------------
#
# :data:`EVIDENCE_HEURISTIC_EPS_THRESHOLD` (default ``1e-3``) is the
# framework's documented asymptotic threshold below which the
# heuristic evidence balance is unsound. DERIV-001 establishes the
# principle that every framework hyperparameter SHOULD trace to a
# paper quantity (A_g / B_g / C_g / e_rho) or a mathematical theory
# (Lipschitz, variance-preserving, OT, BL convergence, Fisher / Polyak
# / information geometry); hand-set engineering constants stay as
# named provenance.
#
# :func:`derive_default_eps_threshold` is the minimal wiring for
# that threshold: when the caller supplies a
# :class:`DerivationContext` carrying ``e_rho`` (paper-quantity
# exterior gap from Lemma 5) and ``delta_t`` (per-round step), the
# function returns the :class:`BLConvergenceEpsilonSchedule`
# closed-form value ``eps_t = sqrt(e_rho * delta_t)`` (Li 2024
# Theorem 1 / Lemma 5). When the context is missing ``e_rho``, the
# function falls back to ``1e-3`` verbatim so existing callers
# keep working unchanged.
#
# The function is additive: no ``check_evidence_mode`` /
# :data:`EVIDENCE_HEURISTIC_EPS_THRESHOLD` API changes; the helper
# is a new entry point that engine / runner code can opt-into
# without breaking the existing 2356+15 test suite.


def derive_default_eps_threshold(
    *,
    e_rho: float | None = None,
    delta_t: float | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return the BL-convergence-derived ``eps_threshold``.

    Parameters
    ----------
    e_rho:
        The paper-quantity exterior gap (Lemma 5 / Lemma 4). Forwarded
        into ``paper_quantities['e_rho']`` if the context does not
        already carry it.
    delta_t:
        The per-round step size. Forwarded into
        ``scheduler_state['delta_t']`` if the context does not already
        carry it. Used by the BL-convergence closed form
        ``eps_t = sqrt(e_rho * delta_t)``.
    context:
        The :class:`DerivationContext` carrying ``e_rho`` / ``delta_t``
        (and other paper / scheduler inputs). When supplied with
        non-``None`` ``e_rho``, the
        :class:`BLConvergenceEpsilonSchedule` rule derives the
        threshold from the closed-form ``sqrt(e_rho * delta_t)``
        (Li 2024 Theorem 1 / Lemma 5).
    rule:
        The :class:`DerivationRule` to apply. Defaults to
        :class:`BLConvergenceEpsilonSchedule` (the DERIV-001 proof
        for the eps_threshold parameter).

    Returns
    -------
    float
        A positive ``float``. Falls back to
        :data:`EVIDENCE_HEURISTIC_EPS_THRESHOLD` (``1e-3``, the
        documented asymptotic threshold below which the heuristic
        evidence balance is unsound) when the chosen rule cannot
        derive from the supplied context, preserving the existing
        wiring.
    """
    chosen: DerivationRule = (
        rule if rule is not None else BLConvergenceEpsilonSchedule()
    )
    # When the caller did not pass a context, build one from the
    # scalar kwargs so the dispatcher can apply the rule uniformly.
    # This mirrors the ``derive_default_memory_fraction`` pattern in
    # ``blender_extra.py``: the entry point is a thin wrapper that
    # promotes caller-side scalars into a DerivationContext when one
    # is missing.
    if context is None:
        from adaptive_reflow.algorithm._derivation import (
            make_derivation_context,
        )

        context = make_derivation_context(
            e_rho=e_rho,
            delta_t=delta_t,
        )
    return float(
        default_eps_implicit(
            context, eps_implicit=None, rule=chosen
        )
    )


# ---------------------------------------------------------------------------
# Parameter-free default-min-gumbel-temp entry point (DERIV-001 P-19 #11)
# ---------------------------------------------------------------------------


def derive_default_min_gumbel_temp(
    *,
    e_rho: float | None = None,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``DEFAULT_MIN_GUMBEL_TEMP`` from a derivation rule.

    The closed form is ``tau_floor := e_rho / 4`` (paper-quantity
    exterior gap, Lemma 5). Falls back to ``1e-3`` when the
    context is missing ``e_rho``, preserving the existing wiring.

    Parameters
    ----------
    e_rho:
        The paper-quantity exterior gap. Forwarded into
        ``paper_quantities['e_rho']`` if the context does not
        already carry it.
    context:
        The :class:`DerivationContext`.
    rule:
        The :class:`DerivationRule` to apply. Defaults to
        :class:`MinGumbelTempRule`.
    """
    return default_min_gumbel_temp(context, e_rho=e_rho, rule=rule)


# ---------------------------------------------------------------------------
# Parameter-free default-strength entry point (DERIV-001 P-19 #2)
# ---------------------------------------------------------------------------


def derive_default_strength(
    *,
    context: DerivationContext | None = None,
    rule: DerivationRule | None = None,
) -> float:
    """Return ``EvidenceDrivenScheduler.strength`` (theorem-fixed at 1.0).

    Per Theorem 1 (Li 2024), the canonical evidence-driven
    strength is fixed at ``1.0`` — the full multiplicative drive
    ``n_cap * evidence_ratio``. Returns ``1.0`` regardless of
    context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else MeanFlowFixedStrengthRule()
    )
    return float(chosen.derive(context if context is not None else _empty_ctx()))


def _empty_ctx() -> DerivationContext:
    """Return an empty DerivationContext for the strength fallback path."""
    from adaptive_reflow.algorithm._derivation import _empty_context as _ec
    return _ec()

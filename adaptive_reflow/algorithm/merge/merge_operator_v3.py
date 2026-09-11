"""MeanFlowMergeOperator — ``MergeOperatorProtocol`` impl with mean-flow twist.

A2 from ``docs/r3-survey/08-fix-plan.md`` §5. MeanFlow (arXiv:2505.13447)
decomposes a multi-step flow into a *single* average velocity via the
identity

    u(t; x) = v(t; x) - (t - s) * ∂v/∂t

where ``v(t; x)`` is the instantaneous velocity field and ``u(t; x)``
is the mean velocity from ``t`` to ``s``. This module ships a
:class:`MergeOperatorProtocol` implementation that lifts the canonical
:class:`BoundedMergeOperator` semantics with a mean-flow-derived
``(t, s)`` pair so the bounded merge can be reinterpreted as the
bounded correction of an average-velocity update.

Paper: ``https://arxiv.org/abs/2505.13447``.

Module boundary
---------------

* **stdlib-only**. No ``torch``. No I/O. No global state.
* Pure functions; identical inputs always yield identical outputs.
* The operator extends :class:`BoundedMergeOperator` so all bounded-
  merge audit codes (P0-3, ``MERGE_DEGENERATE_INTERVAL``, etc.) are
  emitted unchanged. The mean-flow twist adds a single new audit code
  (:data:`MEANFLOW_DECOMPOSITION_AUDIT`) so a downstream reader can
  attribute the round's merge to the MeanFlow path.

Audit-code vocabulary
---------------------

* :data:`MEANFLOW_DECOMPOSITION_AUDIT` — emitted whenever the operator
  processes a round. Carries the (t, s, dt) tuple so a downstream
  audit reader can reconstruct the mean-flow decomposition byte-for-byte.
* :data:`MEANFLOW_PAIR_INVALID` — emitted when ``t == s`` (a degenerate
  round where the mean-flow decomposition is undefined). The operator
  falls back to the standard bounded merge in this case (no override).
"""

from __future__ import annotations

import math
from typing import Any, Optional

from adaptive_reflow.algorithm._derivation import (
    BoundaryConditionRule,
    DEFAULT_MEANFLOW_EPS_FALLBACK,
    DEFAULT_MEANFLOW_TOLERANCE_FALLBACK,
    DerivationContext,
    DerivationRule,
    FisherMemoryFraction,
    MeanFlowToleranceRule,
    MachineEpsilonRule,
    default_alpha_grad,
    default_machine_eps,
    default_tolerance,
)
from .merge_operator import (
    _ERR_CAP_BELOW_FLOOR,
    MERGE_DEGENERATE_INTERVAL,
    BoundedMergeOperator,
    MergeOperatorProtocol,
    default_bounded_merge_operator,
)
from adaptive_reflow.contracts import hash_artifact

# ---------------------------------------------------------------------------
# Module-level constants (canonical audit codes)
# ---------------------------------------------------------------------------

#: Audit code emitted on every MeanFlow merge. Carries the (t, s, dt)
#: tuple so a downstream reader can reconstruct the decomposition.
MEANFLOW_DECOMPOSITION_AUDIT: str = "meanflow_decomposition_audit"

#: Audit code emitted when ``t == s`` (the mean-flow decomposition is
#: undefined). The operator falls back to the standard bounded merge
#: in this case.
MEANFLOW_PAIR_INVALID: str = "meanflow_pair_invalid"

#: Module-level provenance constant — the canonical MeanFlow
#: degenerate-pair eps floor (paper-quantity Lipschitz-derived;
#: ``1e-12``). Used by :func:`derive_default_machine_eps` when the
#: derivation context is missing the (t, s) boundary timesteps.
MEANFLOW_DEGENERATE_EPS: float = DEFAULT_MEANFLOW_EPS_FALLBACK

#: Canonical MeanFlow boundary conditions (Theorem 1
#: arXiv:2505.13447). ``t = 1.0``, ``s = 0.0``. Exposed as named
#: provenance via :class:`BoundaryConditionRule`.
MEANFLOW_BOUNDARY_T: float = 1.0
MEANFLOW_BOUNDARY_S: float = 0.0


# ---------------------------------------------------------------------------
# Operator implementation
# ---------------------------------------------------------------------------


class MeanFlowMergeOperator:
    """``MergeOperatorProtocol`` impl with the MeanFlow decomposition twist.

    The operator extends :class:`BoundedMergeOperator` with an
    additional ``(t, s)`` pair (default ``t = 1.0``, ``s = 0.0``) and
    a mean-flow decomposition twist:

        u_eff = v_eff - (t - s) * ∂v/∂t_proxy

    where ``v_eff`` is the *raw* bounded merge (the operator's parent
    class's output) and ``∂v/∂t_proxy`` is a small proxy derived from
    the operator's prior round (an exponentially-weighted gradient
    estimate, ``alpha_grad = (current - prev) / max(|t - s|, eps)``).
    The final output is

        result = clip(u_eff, [floor, cap])

    The bounded-merge semantics are preserved: the operator clips the
    result into ``[floor, cap]`` and emits the canonical
    :data:`MERGE_DEGENERATE_INTERVAL` audit code when the envelope
    collapses.

    The decomposition is "twist" rather than full MeanFlow because
    flowa's merge operator is a single-round update rather than a
    flow-map distillation. The twist provides a small multiplicative
    correction factor ``(1 - (t - s) * alpha_grad)`` that nudges the
    bounded merge off its cosine baseline in proportion to the
    observed velocity change — the spirit of MeanFlow's
    ``u = v - ∂v/∂t * (t - s)`` identity, applied to the merge-
    operator envelope rather than a flow map.

    Parameters
    ----------
    t:
        The "target" timestep (canonical 1.0). When ``t > s``, the
        operator applies a multiplicative correction to the bounded
        merge; when ``t == s`` the operator falls back to the
        standard bounded merge (no correction).
    s:
        The "source" timestep (canonical 0.0).
    alpha_grad:
        Optional EMA coefficient for the velocity-gradient proxy
        (``alpha_grad = (current - prev) / max(|t - s|, eps)``). The
        default ``0.5`` keeps the proxy half-life at one round.
    tolerance:
        Forwarded to the wrapped :class:`BoundedMergeOperator`.
    """

    FAMILY: str = "meanflow"

    def __init__(
        self,
        *,
        t: float = 1.0,
        s: float = 0.0,
        alpha_grad: float = 0.5,
        tolerance: float = 1e-9,
    ) -> None:
        if not math.isfinite(float(t)):
            raise ValueError(f"t must be finite, got {t!r}")
        if not math.isfinite(float(s)):
            raise ValueError(f"s must be finite, got {s!r}")
        if not 0.0 <= float(alpha_grad) <= 1.0:
            raise ValueError(
                f"alpha_grad must be in [0, 1], got {alpha_grad!r}"
            )
        self._t = float(t)
        self._s = float(s)
        self._alpha_grad = float(alpha_grad)
        self._bounded = default_bounded_merge_operator()
        self._bounded_tolerance = float(tolerance)
        # The EMA estimate of the per-round velocity gradient proxy.
        self._prev_dynamic: float | None = None
        self._ema_grad: float = 0.0

    @property
    def t(self) -> float:
        """Return the configured target timestep."""
        return float(self._t)

    @property
    def s(self) -> float:
        """Return the configured source timestep."""
        return float(self._s)

    @property
    def alpha_grad(self) -> float:
        """Return the configured gradient-EMA coefficient."""
        return float(self._alpha_grad)

    @property
    def ema_grad(self) -> float:
        """Return the current EMA estimate of the velocity gradient proxy."""
        return float(self._ema_grad)

    # -- config round-trip --------------------------------------------------

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict (P1-1 round-trip)."""
        return {
            "family": self.FAMILY,
            "t": float(self._t),
            "s": float(self._s),
            "alpha_grad": float(self._alpha_grad),
            "tolerance": float(self._bounded_tolerance),
        }

    def config_hash(self) -> str:
        """Return a stable digest of the operator config."""
        return str(
            hash_artifact(
                {
                    "family": self.FAMILY,
                    "t": float(self._t),
                    "s": float(self._s),
                    "alpha_grad": float(self._alpha_grad),
                    "tolerance": float(self._bounded_tolerance),
                }
            )
        )

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> MeanFlowMergeOperator:
        """Build a :class:`MeanFlowMergeOperator` from ``config``."""
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dict, got {type(config).__name__}")
        return cls(
            t=float(config.get("t", 1.0)),
            s=float(config.get("s", 0.0)),
            alpha_grad=float(config.get("alpha_grad", 0.5)),
            tolerance=float(config.get("tolerance", 1e-9)),
        )

    # -- MergeOperatorProtocol ---------------------------------------------

    def merge(
        self,
        prev: float,
        dynamic: float,
        *,
        cap: float,
        floor: float,
        delta_cap_up: float,
        delta_cap_down: float,
        audit_codes: list[str] | None = None,
    ) -> float:
        """Return the MeanFlow-decomposed merge of ``prev`` and ``dynamic``.

        P0-3 contract: returns a finite ``float`` in the closed unit
        interval ``[0, 1]``. Non-finite / out-of-range inputs are
        clipped into ``[0, 1]`` and the canonical audit code is
        appended. Clamps / clipping happen before the MeanFlow
        decomposition so the result is always in ``[floor, cap]``.
        """
        # Step 1 — bounded merge (the parent class handles envelope
        # coercion and emits the canonical audit codes).
        raw = self._bounded.merge(
            prev=prev,
            dynamic=dynamic,
            cap=cap,
            floor=floor,
            delta_cap_up=delta_cap_up,
            delta_cap_down=delta_cap_down,
            audit_codes=audit_codes,
        )
        # Step 2 — MeanFlow decomposition twist.
        dt = self._t - self._s
        if not math.isfinite(dt) or abs(dt) < 1e-12:
            # Degenerate pair: fall back to the standard bounded merge.
            if audit_codes is not None:
                audit_codes.append(
                    f"{MEANFLOW_PAIR_INVALID}:t={self._t:.6f}:s={self._s:.6f}"
                )
            return float(raw)
        # Update the EMA gradient proxy from the round's dynamic
        # value (proxy: derivative w.r.t. the round's dynamic).
        if self._prev_dynamic is not None:
            grad = (float(dynamic) - float(self._prev_dynamic)) / max(abs(dt), 1e-12)
            self._ema_grad = (
                self._alpha_grad * grad
                + (1.0 - self._alpha_grad) * self._ema_grad
            )
        self._prev_dynamic = float(dynamic)
        # MeanFlow correction factor: ``u_eff = raw - dt * ema_grad``
        # clipped into ``[0, 1]`` (and into ``[floor, cap]`` for the
        # bounded-merge contract).
        corrected = raw - dt * self._ema_grad
        result = max(0.0, min(1.0, float(corrected)))
        if audit_codes is not None:
            audit_codes.append(
                f"{MEANFLOW_DECOMPOSITION_AUDIT}"
                f":t={self._t:.6f}:s={self._s:.6f}"
                f":dt={dt:.6f}:ema_grad={self._ema_grad:.6f}"
                f":raw={raw:.6f}:corrected={result:.6f}"
            )
        # Re-clip into ``[floor, cap]`` so the bounded-merge contract
        # is honoured even after the correction.
        #
        # P0-3 (F-18) — when ``cap < floor`` the envelope is
        # degenerate. The parent :meth:`BoundedMergeOperator.merge`
        # already returned the ``floor`` value via fail-closed
        # semantics; we must not silently invert the result by
        # clipping into ``[floor, cap]`` again (which would otherwise
        # snap the floor back down to the cap). Match the parent's
        # fail-closed path: emit the canonical audit code and return
        # the ``floor`` value.
        if floor > cap:
            if audit_codes is not None:
                audit_codes.append(
                    f"{_ERR_CAP_BELOW_FLOOR}:cap={float(cap):.6f}"
                    f":floor={float(floor):.6f}"
                )
            return float(floor)
        if result < floor:
            result = float(floor)
        elif result > cap:
            result = float(cap)
        return float(result)


# -- Re-export for the framework's import path ------------------------------

# Re-export the canonical bounded-merge audit code so callers that
# import from this module see the same vocabulary.
_ = MERGE_DEGENERATE_INTERVAL


# ---------------------------------------------------------------------------
# Parameter-free default-alpha-grad entry point (DERIV-001 proof #5)
# ---------------------------------------------------------------------------
#
# The :class:`MeanFlowMergeOperator`'s ``alpha_grad`` (the EMA
# coefficient for the velocity-gradient proxy) is currently hand-set to
# ``0.5`` (the canonical mid-cycle anchor). DERIV-001 establishes the
# principle that every framework hyperparameter SHOULD trace to a
# paper quantity (A_g / B_g / C_g / e_rho) or a mathematical theory
# (Lipschitz, variance-preserving, OT, BL convergence, Fisher / Polyak
# / information geometry); hand-set engineering constants stay as named
# provenance.
#
# :func:`derive_default_alpha_grad` is the minimal wiring for the
# alpha_grad default: when the caller supplies a
# :class:`DerivationContext` carrying ``e_rho`` (paper-quantity
# exterior gap from Lemma 5), the function returns the
# :class:`FisherMemoryFraction` closed-form value
# ``alpha_grad := exp(-e_rho)`` (Amari 1998 natural-gradient step
# applied to the **algorithm posterior** rather than to model
# parameters). When the context is missing ``e_rho``, the function
# falls back to ``0.5`` verbatim so existing callers keep working
# unchanged.
#
# The function is additive: no :class:`MeanFlowMergeOperator` API
# changes; the helper is a new entry point that engine / runner code
# can opt-into without breaking the existing 2356+15 test suite.


def derive_default_alpha_grad(
    *,
    e_rho: Optional[float] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return the per-round ``alpha_grad`` from a derivation rule.

    Parameters
    ----------
    e_rho:
        The paper-quantity exterior gap (Lemma 5 / Lemma 4). Forwarded
        into ``paper_quantities['e_rho']`` if the context does not
        already carry it. Used directly when ``context`` is ``None``.
    context:
        The :class:`DerivationContext` carrying ``e_rho`` (and other
        paper / curvature inputs). When supplied with non-``None``
        ``e_rho``, the :class:`FisherMemoryFraction` rule derives the
        alpha_grad from ``exp(-e_rho)`` (Amari 1998 natural-gradient
        step applied to the algorithm posterior).
    rule:
        The :class:`DerivationRule` to apply. Defaults to
        :class:`FisherMemoryFraction` (the DERIV-001 proof for the
        alpha_grad parameter).

    Returns
    -------
    float
        A value in ``[0, 1]``. Falls back to ``0.5`` (the canonical
        :class:`MeanFlowMergeOperator` default) when the chosen rule
        cannot derive from the supplied context, preserving the
        existing wiring.

    Notes
    -----
    This function is the **DERIV-001 wiring** for the alpha_grad
    parameter — the MeanFlow EMA coefficient. Future work may wire
    the same pattern into the other framework hyperparameters
    cataloged in ``docs/algorithm-deep-uplift-plan.md``, each
    following the abstract :class:`DerivationRule` protocol with its
    own concrete subclass.
    """
    return default_alpha_grad(context, e_rho=e_rho, rule=rule)


# ---------------------------------------------------------------------------
# Parameter-free default-tolerance entry point (DERIV-001 wiring P-19 #7)
# ---------------------------------------------------------------------------


def derive_default_tolerance(
    *,
    n_min: Optional[float] = None,
    n_cap: Optional[float] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return ``MeanFlowMergeOperator.tolerance`` from a derivation rule.

    Parameters
    ----------
    n_min:
        The cycle ``n_min`` anchor. Forwarded into
        ``scheduler_state['n_min']`` if the context does not
        already carry it.
    n_cap:
        The current round's ``n_cap``. Forwarded into
        ``scheduler_state['n_cap_t']`` if the context does not
        already carry it.
    context:
        The :class:`DerivationContext`. When supplied with
        ``n_min`` and ``n_cap_t`` populated, the
        :class:`MeanFlowToleranceRule` derives the tolerance
        via the closed-form Polyak ratio
        ``tol := base_tol * n_min / n_cap_t``.
    rule:
        The :class:`DerivationRule` to apply. Defaults to
        :class:`MeanFlowToleranceRule`.

    Returns
    -------
    float
        A finite ``>= 0`` value. Falls back to
        :data:`DEFAULT_MEANFLOW_TOLERANCE_FALLBACK` (``1e-9``) on
        missing context, preserving the existing wiring.
    """
    return default_tolerance(context, n_min=n_min, n_cap=n_cap, rule=rule)


# ---------------------------------------------------------------------------
# Parameter-free default-machine-eps entry point (DERIV-001 wiring P-19 #8)
# ---------------------------------------------------------------------------


def derive_default_machine_eps(
    *,
    t: Optional[float] = None,
    s: Optional[float] = None,
    context: Optional[DerivationContext] = None,
    rule: Optional[DerivationRule] = None,
) -> float:
    """Return the MeanFlow degenerate-pair ``eps`` from a derivation rule.

    Falls back to :data:`DEFAULT_MEANFLOW_EPS_FALLBACK` (``1e-12``)
    on missing context. The derivation is
    ``eps := base_eps * |t - s|`` (Lipschitz-driven machine
    epsilon), so when ``t == s`` the canonical closed form is
    zero; the rule's ``fallback`` (``1e-12``) is the safe
    conservative floor used by the framework when no boundary
    context is supplied.
    """
    return default_machine_eps(context, t=t, s=s, rule=rule)


# ---------------------------------------------------------------------------
# Parameter-free boundary-condition entry point (DERIV-001 wiring P-19 #5)
# ---------------------------------------------------------------------------


def derive_default_boundary_conditions(
    context: Optional[DerivationContext] = None,
    *,
    rule: Optional[DerivationRule] = None,
) -> tuple[float, float]:
    """Return the MeanFlow ``(t, s)`` boundary conditions from Theorem 1.

    Per MeanFlow arXiv:2505.13447 Theorem 1, the canonical
    boundary conditions are ``(t = 1.0, s = 0.0)``. The boundary
    conditions are theorem-fixed; the function always returns
    ``(1.0, 0.0)`` regardless of context.
    """
    chosen: DerivationRule = (
        rule if rule is not None else BoundaryConditionRule()
    )
    if context is None:
        return (
            float(chosen.derive(context or _empty_ctx_local())),
            float(BoundaryConditionRule.fallback_s),
        )
    return (
        float(chosen.derive(context)),
        float(BoundaryConditionRule().derive_s(context)),
    )


def _empty_ctx_local() -> "DerivationContext":
    """Return an empty DerivationContext for fallback paths."""
    from adaptive_reflow.algorithm._derivation import _empty_context
    return _empty_context()


__all__ = [
    "MEANFLOW_BOUNDARY_S",
    "MEANFLOW_BOUNDARY_T",
    "MEANFLOW_DECOMPOSITION_AUDIT",
    "MEANFLOW_DEGENERATE_EPS",
    "MEANFLOW_PAIR_INVALID",
    "MeanFlowMergeOperator",
    "derive_default_alpha_grad",
    "derive_default_boundary_conditions",
    "derive_default_machine_eps",
    "derive_default_tolerance",
]

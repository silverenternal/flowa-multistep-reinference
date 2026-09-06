"""Per-step ODE integrator for adaptive re-inference.

Defines the abstract :class:`IntegratorProtocol` and two concrete
implementations:

* :class:`EulerStep` — the canonical **fixed-step** Euler integrator that
  backs every Wave 47 / 52 / 58 result. The behaviour is the same one
  the framework has always shipped: ``x_next = x + dt_base * v_pred``
  with ``dt_base`` a configuration constant. **This implementation
  MUST stay byte-identical** — composite data, regression vectors,
  and pinned metrics across the model adapters all depend on the
  exact ``(x, v_pred, dt_base) -> x + dt_base * v_pred`` arithmetic.
* :class:`MultiFidelityPaperQuantityStep` — the **new** Wave 59 / Paper
  A "MFPQA" algorithm. Per-step ``dt`` adapts to the paper-quantity
  signal at the current ``t``:

      dt(r) = dt_base * (1 + alpha * sheet_A_local(r)
                           + beta  * (1 - cell_C_local(r)))

  The :class:`MultiFidelityPaperQuantityStep` is **opt-in**: it is
  wired into each adapter through the new ``integrator`` constructor
  parameter (Wave 59+). When ``paper_quantities`` is ``None`` (or a
  snapshot that does not expose ``sheet_A`` / ``cell_C`` for ``t``),
  the integrator **gracefully falls back** to ``dt_base`` so legacy
  callers do not crash.

Module boundary:

* stdlib + numpy only. No ``torch``. No I/O. No global state.
* Pure functions; identical inputs always yield identical outputs.
* The legacy fixed-``dt`` Euler integrator is **never** invoked inside
  this module. Any legacy caller that wants the fixed-``dt`` semantics
  must be ported to use :class:`EulerStep` (or
  :func:`default_euler_step`).

Public surface:

* :class:`IntegratorProtocol`
* :class:`EulerStep` + :func:`default_euler_step`
* :class:`MultiFidelityPaperQuantityStep` + :func:`default_mfpqa_step`
* :class:`IntegratorConfigError`

Failure modes
-------------

The integrators are **clip-and-audit** (closes P0-3 by analogy with the
merge operator pattern): out-of-range or non-finite ``base_dt`` /
``alpha`` / ``beta`` values are coerced into the documented envelope
``base_dt in (0, +inf)``, ``alpha, beta >= 0`` and the integrator
appends a canonical audit code to the caller's ``audit_codes`` list
when one is supplied. :class:`EulerStep` ignores ``paper_quantities``
entirely (legacy semantics); :class:`MultiFidelityPaperQuantityStep`
falls back to ``base_dt`` and emits :data:`MFPQA_NO_PAPER_QUANTITIES`
when ``paper_quantities`` is ``None``, and
:data:`MFPQA_FALLBACK_FIELDS_MISSING` when the snapshot lacks the
``sheet_A`` / ``cell_C`` keys for the current ``t``.

Non-numeric types and ``None`` values still raise
:exc:`IntegratorConfigError` (subclass of :exc:`ValueError`); the
numeric coercion boundary is the only point where an exception may
propagate.

Design rationale (Wave 59 §8 — interface-first constraint)
----------------------------------------------------------

The interface-first constraint (locked in by user 2026-09-07,
``todo/two-paper-algo-design.md`` §1) requires that **no new
implementation** (step 3 / 4) lands before the protocol (step 1 / 2)
is in place. :class:`IntegratorProtocol` is the new abstract surface;
:class:`EulerStep` is the legacy default; :class:`MultiFidelityPaperQuantityStep`
is the new opt-in algorithm. Adapter wiring (Wave 59 §5 step 4) is a
separate wave that threads the protocol through ``solve_ode`` in each
adapter — until then the protocol lives here as a stand-alone module
so existing adapters that do ``integrator = EulerStep()`` keep working
unchanged.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Optional, Protocol, runtime_checkable

from adaptive_reflow.contracts import hash_artifact

# ---------------------------------------------------------------------------
# Module-level constants (canonical error / audit codes; ASCII only)
# ---------------------------------------------------------------------------


#: Audit code emitted when :class:`MultiFidelityPaperQuantityStep` is
#: invoked with ``paper_quantities is None``. The integrator falls back
#: to fixed ``base_dt`` so legacy callers do not crash. The code is
#: appended to the caller's ``audit_codes`` list when one is supplied;
#: callers that opt out of audit emission still get the fixed-``dt``
#: fallback (preserving legacy semantics).
MFPQA_NO_PAPER_QUANTITIES: str = "mfpqa_no_paper_quantities"

#: Audit code emitted when :class:`MultiFidelityPaperQuantityStep` is
#: invoked with a ``paper_quantities`` snapshot that does not expose
#: the expected ``sheet_A[t]`` / ``cell_C[t]`` fields (either the
##: snapshot is missing the keys or ``t`` is out of range). The
#: integrator falls back to fixed ``base_dt`` so the loop survives
#: without altering the path-length budget.
MFPQA_FALLBACK_FIELDS_MISSING: str = "mfpqa_fallback_fields_missing"

#: Audit code emitted when :class:`MultiFidelityPaperQuantityStep`
#: observes a non-finite ``sheet_A`` / ``cell_C`` value at the current
#: ``t``. The integrator coerces the offending value to ``0.0`` (the
#: safe default for an undefined paper-quantity signal) and proceeds
#: with the resulting ``dt`` so the inner loop never crashes on
#: ``NaN`` / ``inf`` propagations from the upstream model.
MFPQA_NONFINITE_QUANTITY_COERCED: str = "mfpqa_nonfinite_quantity_coerced"

#: Audit code emitted when :class:`MultiFidelityPaperQuantityStep`
#: computes a ``dt`` that is non-positive (e.g. ``alpha = -10`` with
#: ``sheet_A = 1.0``). The integrator clips the per-step ``dt`` to
#: ``base_dt`` so the integration cannot stall or reverse direction.
MFPQA_DT_FLOORED_TO_BASE: str = "mfpqa_dt_floored_to_base"

#: Default ``base_dt`` matching the Wave 47 / 52 / 58 fixed-Euler
#: path. The constant is exposed at module level so adapters that
#: want the legacy default can pass it without hard-coding the number.
DEFAULT_BASE_DT: float = 0.05

#: Default MFPQA ``alpha`` coefficient (paper-quantity sheet-evidence
#: contribution). ``alpha = 0.3`` matches the canonical formula in
#: ``todo/two-paper-algo-design.md`` §3.2.
DEFAULT_MFPQA_ALPHA: float = 0.3

#: Default MFPQA ``beta`` coefficient (paper-quantity cell-evidence
#: anti-contribution). ``beta = 0.2`` matches the canonical formula in
#: ``todo/two-paper-algo-design.md`` §3.2.
DEFAULT_MFPQA_BETA: float = 0.2


# ---------------------------------------------------------------------------
# Exceptions (fail-closed; surface bad caller input)
# ---------------------------------------------------------------------------


class IntegratorConfigError(ValueError):
    """Raised when an integrator rejects its arguments.

    Inherits from :exc:`ValueError` so existing
    ``pytest.raises(ValueError)`` patterns continue to work; the
    specific subclass is exposed via :data:`__all__` for callers that
    want to narrow their ``except`` clauses.
    """


# ---------------------------------------------------------------------------
# Internal coercion helpers
# ---------------------------------------------------------------------------


def _coerce_finite_real(x: Any, *, name: str) -> float:
    """Return ``float(x)``; raise :exc:`IntegratorConfigError` on bad input.

    Booleans are coerced to 0/1 (this matches the policy_authority and
    merge-operator coercion conventions). ``None`` is rejected.
    """
    if x is None:
        raise IntegratorConfigError(f"{name}: required (got None)")
    if isinstance(x, bool):
        return float(int(x))
    if not isinstance(x, (int, float)):
        raise IntegratorConfigError(
            f"{name}: expected a real number, got {type(x).__name__}"
        )
    fx = float(x)
    if not math.isfinite(fx):
        raise IntegratorConfigError(f"{name}: must be finite, got {fx!r}")
    return fx


def _coerce_positive_real(x: Any, *, name: str) -> float:
    """Return ``float(x)``; require ``x > 0``; raise on non-positive input.

    Used for ``base_dt`` so the integrator cannot accidentally stall
    or reverse direction. ``x == 0`` is rejected (would freeze the
    trajectory); ``x < 0`` is rejected (would reverse direction).
    """
    fx = _coerce_finite_real(x, name=name)
    if fx <= 0.0:
        raise IntegratorConfigError(
            f"{name}: must be strictly positive, got {fx!r}"
        )
    return fx


def _coerce_nonneg_real(x: Any, *, name: str) -> float:
    """Return ``float(x)``; require ``x >= 0``; raise on negative input.

    Used for ``alpha`` and ``beta`` so the per-step ``dt`` cannot go
    negative. ``x == 0`` is permitted (disables the corresponding
    paper-quantity contribution).
    """
    fx = _coerce_finite_real(x, name=name)
    if fx < 0.0:
        raise IntegratorConfigError(
            f"{name}: must be non-negative, got {fx!r}"
        )
    return fx


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class IntegratorProtocol(Protocol):
    """Abstract per-step ODE integrator.

    Implementations answer "how do I advance the state by one step?" —
    the canonical seam the Wave 59 Paper A design identified as the
    insertion point for paper-quantity-driven ``dt`` adaptation
    (``todo/two-paper-algo-design.md`` §3.2).

    The Protocol mirrors the ``SchedulerProtocol`` pattern: a single
    :meth:`step` method that takes the state, the predicted velocity,
    the time ``t``, the round's paper-quantity snapshot (optional for
    :class:`EulerStep`, consumed by :class:`MultiFidelityPaperQuantityStep`),
    and the per-channel ``m`` mask, and returns the next state.

    CONTRACT (closes P0-3 by analogy):

    * All implementations MUST return a value of the same dtype /
      shape as ``x`` (numpy arrays in, numpy arrays out).
    * All implementations MUST be pure w.r.t. their arguments:
      identical inputs always yield identical outputs. The
      :class:`MultiFidelityPaperQuantityStep` paper-quantity
      snapshot is treated as read-only.
    * Implementations MUST NOT raise on legitimate caller inputs
      such as ``paper_quantities is None``; instead, the
      :class:`MultiFidelityPaperQuantityStep` falls back to
      ``base_dt`` and emits :data:`MFPQA_NO_PAPER_QUANTITIES` (or
      :data:`MFPQA_FALLBACK_FIELDS_MISSING`) to ``audit_codes``
      when one is supplied.
    * ``x`` is never mutated by :meth:`step`; the returned value is
      a fresh allocation.

    Config round-trip (P1-1): every implementation exposes
    :meth:`to_config` / :meth:`from_config` (classmethod) so the
    integrator family + its hyperparameters can be serialized to
    JSON and replayed byte-for-byte.
    """

    def step(
        self,
        x: Any,
        v_pred: Any,
        t: float,
        paper_quantities: Optional[Mapping[str, Any]],
        m: Any,
    ) -> Any:
        """Return the next state after one integration step.

        Parameters
        ----------
        x:
            Current state. numpy ``NDArray[np.float64]`` is the
            canonical input type; opaque handles are accepted as
            long as they support ``x + scalar * v_pred``.
        v_pred:
            Predicted velocity (same shape / dtype as ``x``).
        t:
            Current time in ``[0, 1]`` (matches the rest of the
            framework's normalised time grid). Implementations
            MUST accept any finite ``t`` and MUST NOT assume
            ``t`` lies on the ``t_grid``.
        paper_quantities:
            Optional paper-quantity snapshot for the round.
            :class:`EulerStep` ignores this argument; the
            :class:`MultiFidelityPaperQuantityStep` reads
            ``sheet_A[t]`` and ``cell_C[t]`` (or ``None`` for a
            graceful fallback).
        m:
            Per-channel mask (legacy ``m`` parameter threaded
            through every adapter's ODE loop). Implementations
            SHOULD accept any shape; the canonical pattern is to
            leave ``m`` to the adapter-level ODE driver and have
            :meth:`step` compute ``x + dt * v_pred`` without
            consulting ``m`` directly.

        Returns
        -------
        Any
            The next state. Same shape / dtype as ``x``. Never
            ``x`` itself.
        """
        ...

    def config_hash(self) -> str:
        """Return a stable digest of the integrator config.

        Two integrators with different configurations (e.g. different
        ``base_dt`` / ``alpha`` / ``beta``) MUST hash differently so
        the audit ledger can distinguish them.
        """
        ...

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for this integrator.

        The returned dict round-trips through :meth:`from_config` so
        ``cls.from_config(integrator.to_config()) == integrator`` for
        the concrete implementation.
        """
        ...

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "IntegratorProtocol":
        """Build an integrator from a ``to_config`` dict (P1-1 round-trip).

        ``cls`` is the concrete implementation class — call sites that
        need polymorphic dispatch should use :func:`build_integrator_from_config`
        which dispatches on the ``family`` key.
        """
        ...


# ---------------------------------------------------------------------------
# Paper-quantity snapshot Protocol (per-step paper-quantity lookups)
# ---------------------------------------------------------------------------


@runtime_checkable
class PaperQuantitiesSnapshotProtocol(Protocol):
    """Structural type for a paper-quantity snapshot at one round.

    The :class:`MultiFidelityPaperQuantityStep` reads two scalars from
    the snapshot per step:

    * ``sheet_A(t)`` — the sheet-evidence constant (paper Lemma 2 /
      Proposition 3, :func:`adaptive_reflow.theory.paper_quantities.sheet_evidence_A`).
      Higher ``sheet_A`` means smoother ODE trajectory → larger ``dt``.
    * ``cell_C(t)`` — the per-cell-coefficient constant (paper Lemma 3,
      :func:`adaptive_reflow.theory.paper_quantities.per_cell_coefficient_C`).
      Higher ``cell_C`` means more cell-evidence → smaller ``dt``.

    Snapshots that do not expose these accessors at the current ``t``
    fall back to ``base_dt`` (audit code
    :data:`MFPQA_FALLBACK_FIELDS_MISSING`).
    """

    def sheet_A(self, t: float) -> float: ...

    def cell_C(self, t: float) -> float: ...


def _lookup_paper_quantity(
    snapshot: Any,
    key: str,
    t: float,
) -> tuple[Optional[float], bool]:
    """Best-effort lookup of ``key`` at ``t`` in ``snapshot``.

    Supports three shapes (in this priority order):

    1. ``snapshot`` exposes a method ``<key>(t) -> float``
       (canonical :class:`PaperQuantitiesSnapshotProtocol` shape).
    2. ``snapshot`` exposes a Mapping ``[<key>]`` that, when indexed
       with ``t``, returns a real number (dict-like snapshot keyed by
       time).
    3. ``snapshot`` exposes a Mapping ``["<key>"]`` (or ``[<key>]``)
       that returns a scalar constant (time-independent snapshot).

    Returns ``(value, found)``. ``found = False`` means the snapshot
    did not expose the requested key in any of the supported shapes;
    the caller treats this as a fallback signal (audit code
    :data:`MFPQA_FALLBACK_FIELDS_MISSING`).
    """
    if snapshot is None:
        return None, False
    # 1. Method-shaped accessor.
    accessor = getattr(snapshot, key, None)
    if callable(accessor):
        try:
            value = float(accessor(float(t)))
            return value, True
        except (TypeError, ValueError, KeyError):
            return None, False
    # 2/3. Mapping-shaped accessor.
    if isinstance(snapshot, Mapping):
        try:
            value = snapshot[t]
            return float(value), True
        except (KeyError, TypeError, ValueError):
            pass
        try:
            value = snapshot[key]
            return float(value), True
        except (KeyError, TypeError, ValueError):
            pass
    return None, False


# ---------------------------------------------------------------------------
# Default implementation: EulerStep (PRESERVED, fixed dt)
# ---------------------------------------------------------------------------


class EulerStep:
    """Canonical fixed-step Euler integrator (PRESERVED, Wave 47/52/58).

    The integrator advances the state by one fixed ``base_dt`` step:

        x_next = x + base_dt * v_pred

    No paper-quantity signal is consulted. This is the **legacy
    behaviour** the framework has shipped since Wave 0; per-adapter
    composite data, regression vectors, and pinned metrics across
    every adapter depend on the exact arithmetic. The class is a
    drop-in replacement for the inlined ``x + 0.05 * v_pred`` blocks
    that previously lived in each adapter's ``solve_ode``.

    The constructor exposes ``base_dt`` as a kwarg so adapters that
    need a non-default step size can pass it explicitly (e.g. Kanzi's
    real-ckpt integration uses ``base_dt=0.02`` for stability). The
    default ``base_dt = 0.05`` reproduces the Wave 47 / 52 / 58
    result byte-for-byte.

    Parameters
    ----------
    base_dt:
        Fixed per-step ``dt`` in the integration. Must be strictly
        positive; ``base_dt == 0.05`` is the canonical default
        (matches the inline ``x + 0.05 * v_pred`` blocks).

    Notes
    -----
    :class:`EulerStep` ignores ``paper_quantities`` entirely (legacy
    semantics). It never appends to ``audit_codes``. The class is
    ``runtime_checkable``-safe so callers can use
    ``isinstance(step, IntegratorProtocol)``.
    """

    FAMILY: str = "euler"

    def __init__(self, *, base_dt: float = DEFAULT_BASE_DT) -> None:
        self._base_dt = _coerce_positive_real(base_dt, name="base_dt")
        self._config_hash_value = hash_artifact(
            {
                "family": self.FAMILY,
                "base_dt": float(self._base_dt),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def base_dt(self) -> float:
        """Return the configured fixed per-step ``dt``."""
        return float(self._base_dt)

    @property
    def family(self) -> str:
        """Return the algorithm family identifier (``"euler"``)."""
        return self.FAMILY

    # -- IntegratorProtocol -----------------------------------------------

    def step(
        self,
        x: Any,
        v_pred: Any,
        t: float,
        paper_quantities: Optional[Mapping[str, Any]],
        m: Any,
    ) -> Any:
        """Return ``x + base_dt * v_pred`` (PRESERVED legacy arithmetic).

        ``paper_quantities`` and ``m`` are accepted but ignored. ``t``
        is accepted but ignored (the fixed-``dt`` path does not depend
        on time). The integrator never mutates ``x``; the returned
        value is a fresh allocation.
        """
        del t, paper_quantities, m
        return x + float(self._base_dt) * v_pred

    def config_hash(self) -> str:
        """Return a stable digest of the integrator config.

        Captures ``family`` and ``base_dt`` so two :class:`EulerStep`
        instances with different ``base_dt`` values hash differently.
        """
        return str(self._config_hash_value)

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for this Euler step."""
        return {
            "family": self.FAMILY,
            "base_dt": float(self._base_dt),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "EulerStep":
        """Build an :class:`EulerStep` from ``config`` (P1-1 round-trip)."""
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        if str(config.get("family", cls.FAMILY)) != cls.FAMILY:
            raise ValueError(
                f"EulerStep.from_config: bad family "
                f"{config.get('family')!r} (expected {cls.FAMILY!r})"
            )
        return cls(base_dt=float(config["base_dt"]))


def default_euler_step() -> EulerStep:
    """Return the canonical :class:`EulerStep` singleton-factory.

    The integrator is cheap to construct (no state beyond
    ``base_dt``), so callers may also instantiate :class:`EulerStep`
    directly. This factory is the single entry point used by
    adapters that want the legacy default without hard-coding the
    ``0.05`` literal.
    """
    return EulerStep()


# ---------------------------------------------------------------------------
# New implementation: MultiFidelityPaperQuantityStep (MFPQA)
# ---------------------------------------------------------------------------


class MultiFidelityPaperQuantityStep:
    """Multi-Fidelity Paper-Quantity Annealing (MFPQA) integrator.

    Per-step ``dt`` adapts to the paper-quantity signal at the current
    ``t``:

        dt(r) = base_dt * (1 + alpha * sheet_A_local(r)
                              + beta  * (1 - cell_C_local(r)))

    where ``sheet_A_local(r) = sheet_A(t)`` and
    ``cell_C_local(r) = cell_C(t)`` are the round's paper-quantity
    snapshots (paper Lemma 2 / Proposition 3 for ``A_g``,
    Lemma 3 for ``C_g``).

    Effect
    ------
    * High-curvature regions (low ``sheet_A``, high ``cell_C``) get
      a *smaller* ``dt`` so the integrator doesn't overshoot the
      trajectory.
    * Low-curvature regions (high ``sheet_A``, low ``cell_C``) get a
      *larger* ``dt`` so the integrator can traverse easy regions
      quickly.
    * The end-to-end NFE budget is unchanged (same step count); only
      the per-step ``dt`` shifts.

    Graceful fallback
    -----------------
    * ``paper_quantities is None`` → fall back to ``base_dt`` (audit
      :data:`MFPQA_NO_PAPER_QUANTITIES`).
    * Snapshot lacks ``sheet_A`` / ``cell_C`` accessors for the
      current ``t`` → fall back to ``base_dt`` (audit
      :data:`MFPQA_FALLBACK_FIELDS_MISSING`).
    * Non-finite ``sheet_A`` / ``cell_C`` → coerce to ``0.0`` (audit
      :data:`MFPQA_NONFINITE_QUANTITY_COERCED`).
    * ``dt <= 0`` (e.g. ``alpha = -10`` with ``sheet_A = 1.0``) →
      clip to ``base_dt`` (audit :data:`MFPQA_DT_FLOORED_TO_BASE`).

    Parameters
    ----------
    base_dt:
        The baseline ``dt`` that the paper-quantity signal multiplies.
        Must be strictly positive; default ``0.05`` matches the
        legacy :class:`EulerStep` default so the two integrators
        agree on the easy-region (``alpha = sheet_A = beta =
        cell_C = 0``) baseline.
    alpha:
        Sheet-evidence contribution. Must be ``>= 0``. Higher
        ``alpha`` makes high-``sheet_A`` regions larger-``dt``.
        Default ``0.3`` (matches
        ``todo/two-paper-algo-design.md`` §3.2).
    beta:
        Cell-evidence anti-contribution. Must be ``>= 0``. Higher
        ``beta`` makes high-``cell_C`` regions smaller-``dt``.
        Default ``0.2`` (matches
        ``todo/two-paper-algo-design.md`` §3.2).

    Notes
    -----
    The integrator accepts the ``t`` and ``m`` arguments so its
    signature is polymorphic with :class:`EulerStep`; ``t`` is
    forwarded to the snapshot accessors (so a time-varying snapshot
    can return different ``sheet_A`` / ``cell_C`` per step), ``m``
    is accepted-but-ignored (legacy parameter threading — the
    canonical pattern is for the adapter-level ODE driver to apply
    ``m`` outside the integrator).

    ``x`` is never mutated; the returned value is a fresh allocation.
    """

    FAMILY: str = "mfpqa"

    def __init__(
        self,
        *,
        base_dt: float = DEFAULT_BASE_DT,
        alpha: float = DEFAULT_MFPQA_ALPHA,
        beta: float = DEFAULT_MFPQA_BETA,
    ) -> None:
        self._base_dt = _coerce_positive_real(base_dt, name="base_dt")
        self._alpha = _coerce_nonneg_real(alpha, name="alpha")
        self._beta = _coerce_nonneg_real(beta, name="beta")
        self._config_hash_value = hash_artifact(
            {
                "family": self.FAMILY,
                "base_dt": float(self._base_dt),
                "alpha": float(self._alpha),
                "beta": float(self._beta),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def base_dt(self) -> float:
        """Return the configured baseline ``dt`` (multiplier seed)."""
        return float(self._base_dt)

    @property
    def alpha(self) -> float:
        """Return the configured sheet-evidence contribution."""
        return float(self._alpha)

    @property
    def beta(self) -> float:
        """Return the configured cell-evidence anti-contribution."""
        return float(self._beta)

    @property
    def family(self) -> str:
        """Return the algorithm family identifier (``"mfpqa"``)."""
        return self.FAMILY

    # -- IntegratorProtocol -----------------------------------------------

    def step(
        self,
        x: Any,
        v_pred: Any,
        t: float,
        paper_quantities: Optional[Mapping[str, Any]],
        m: Any,
        *,
        audit_codes: list[str] | None = None,
    ) -> Any:
        """Return ``x + dt(r) * v_pred`` with paper-quantity-adaptive ``dt``.

        ``dt(r) = base_dt * (1 + alpha * sheet_A_local(r)
                                + beta  * (1 - cell_C_local(r)))``

        The integrator falls back to ``base_dt`` when the paper-quantity
        snapshot is missing or does not expose ``sheet_A[t]`` /
        ``cell_C[t]``. Non-finite quantities are coerced to ``0.0``;
        non-positive ``dt`` is clipped to ``base_dt``. The
        ``audit_codes`` list is appended to when one is supplied;
        callers that pass ``None`` (the default) get the silent
        fallback path that matches the legacy :class:`EulerStep`
        semantics for callers that have not opted into audit
        emission.

        ``m`` is accepted-but-ignored; the canonical pattern is for
        the adapter-level ODE driver to apply ``m`` outside the
        integrator.
        """
        del m
        if paper_quantities is None:
            if audit_codes is not None:
                audit_codes.append(MFPQA_NO_PAPER_QUANTITIES)
            return x + float(self._base_dt) * v_pred

        sheet_a_raw, sheet_a_found = _lookup_paper_quantity(
            paper_quantities, "sheet_A", t
        )
        cell_c_raw, cell_c_found = _lookup_paper_quantity(
            paper_quantities, "cell_C", t
        )

        if not sheet_a_found or not cell_c_found:
            if audit_codes is not None:
                audit_codes.append(MFPQA_FALLBACK_FIELDS_MISSING)
            return x + float(self._base_dt) * v_pred

        sheet_a = float(sheet_a_raw) if sheet_a_raw is not None else 0.0
        cell_c = float(cell_c_raw) if cell_c_raw is not None else 0.0

        if not math.isfinite(sheet_a):
            sheet_a = 0.0
            if audit_codes is not None:
                audit_codes.append(MFPQA_NONFINITE_QUANTITY_COERCED)
        if not math.isfinite(cell_c):
            cell_c = 0.0
            if audit_codes is not None:
                audit_codes.append(MFPQA_NONFINITE_QUANTITY_COERCED)

        dt = float(self._base_dt) * (
            1.0 + float(self._alpha) * sheet_a
            + float(self._beta) * (1.0 - cell_c)
        )
        if not math.isfinite(dt) or dt <= 0.0:
            if audit_codes is not None:
                audit_codes.append(MFPQA_DT_FLOORED_TO_BASE)
            dt = float(self._base_dt)

        return x + dt * v_pred

    def config_hash(self) -> str:
        """Return a stable digest of the integrator config.

        Captures ``family``, ``base_dt``, ``alpha``, ``beta`` so two
        :class:`MultiFidelityPaperQuantityStep` instances with
        different coefficients hash differently.
        """
        return str(self._config_hash_value)

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for this MFPQA step."""
        return {
            "family": self.FAMILY,
            "base_dt": float(self._base_dt),
            "alpha": float(self._alpha),
            "beta": float(self._beta),
        }

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "MultiFidelityPaperQuantityStep":
        """Build an :class:`MultiFidelityPaperQuantityStep` from ``config``.

        P1-1 round-trip — two ``from_config(to_config())`` calls always
        produce equal integrators (same coefficients, same hash).
        """
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        if str(config.get("family", cls.FAMILY)) != cls.FAMILY:
            raise ValueError(
                f"MultiFidelityPaperQuantityStep.from_config: bad family "
                f"{config.get('family')!r} (expected {cls.FAMILY!r})"
            )
        return cls(
            base_dt=float(config["base_dt"]),
            alpha=float(config["alpha"]),
            beta=float(config["beta"]),
        )


def default_mfpqa_step() -> MultiFidelityPaperQuantityStep:
    """Return the canonical :class:`MultiFidelityPaperQuantityStep` factory.

    Default coefficients (``alpha=0.3``, ``beta=0.2``, ``base_dt=0.05``)
    match the canonical MFPQA formula in
    ``todo/two-paper-algo-design.md`` §3.2. Adapters that want
    different sensitivity can construct
    :class:`MultiFidelityPaperQuantityStep` directly with custom
    coefficients; this factory is the single entry point used by
    callers that want the canonical default.
    """
    return MultiFidelityPaperQuantityStep()


# ---------------------------------------------------------------------------
# Polymorphic factory
# ---------------------------------------------------------------------------


def build_integrator_from_config(
    config: dict[str, Any],
) -> IntegratorProtocol:
    """Build an :class:`IntegratorProtocol` from a polymorphic ``config`` dict.

    Dispatches on the ``family`` key:

    * ``"euler"`` → :class:`EulerStep`
    * ``"mfpqa"`` → :class:`MultiFidelityPaperQuantityStep`

    Mirrors :func:`adaptive_reflow.algorithm.solver.build_solver_from_config`
    so the integrator surface can be round-tripped through JSON in
    the same idiom. Unknown families raise
    :exc:`IntegratorConfigError`.
    """
    if not isinstance(config, dict):
        raise IntegratorConfigError(
            f"config must be a dict, got {type(config).__name__}"
        )
    family = str(config.get("family", ""))
    if family == EulerStep.FAMILY:
        return EulerStep.from_config(config)
    if family == MultiFidelityPaperQuantityStep.FAMILY:
        return MultiFidelityPaperQuantityStep.from_config(config)
    raise IntegratorConfigError(
        f"build_integrator_from_config: unknown family {family!r}"
    )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "DEFAULT_BASE_DT",
    "DEFAULT_MFPQA_ALPHA",
    "DEFAULT_MFPQA_BETA",
    "EulerStep",
    "IntegratorConfigError",
    "IntegratorProtocol",
    "MFPQA_DT_FLOORED_TO_BASE",
    "MFPQA_FALLBACK_FIELDS_MISSING",
    "MFPQA_NO_PAPER_QUANTITIES",
    "MFPQA_NONFINITE_QUANTITY_COERCED",
    "MultiFidelityPaperQuantityStep",
    "PaperQuantitiesSnapshotProtocol",
    "build_integrator_from_config",
    "default_euler_step",
    "default_mfpqa_step",
]
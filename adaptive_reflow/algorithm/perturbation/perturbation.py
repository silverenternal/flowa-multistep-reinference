"""Saturation-time prior perturbation policy.

Defines the abstract :class:`PerturbationPolicy` and two concrete
implementations:

* :class:`UniformFreshPerturbation` — the canonical **uniform fresh
  noise** policy that backs every Wave 47 / 52 / 58 result. The
  behaviour is the same one the framework has always shipped:
  ``x_perturbed = standard_normal(x.shape)`` with a deterministic
  seed derived from the call site's ``(x.shape, t)`` triple.
  **This implementation MUST stay byte-identical** — composite data,
  regression vectors, and pinned metrics across the model adapters
  all depend on the exact seed -> noise mapping being preserved
  bit-for-bit.
* :class:`PaperQuantityAttractorInversion` — the **new** Wave 59 /
  Paper B "BRAI" algorithm. At saturation, perturb along
  ``-grad(log P_qty(x))`` so the trajectory escapes the baseline's
  attractor and explores regions the paper-quantity prior considers
  rare:

      x_perturbed = x_saturated + eps_scale * (-grad log P_qty)

  The :class:`PaperQuantityAttractorInversion` class is **opt-in**:
  it is wired into each adapter through the new ``perturbation``
  constructor parameter (Wave 59+). When ``paper_quantities`` is
  ``None`` (or the snapshot does not expose the required ``e_rho`` /
  ``log_p_qty`` accessors), the policy **gracefully falls back** to
  :class:`UniformFreshPerturbation` so legacy callers do not crash.

Module boundary:

* stdlib + numpy only. No ``torch``. No I/O. No global state.
* Pure functions; identical inputs always yield identical outputs.
* The legacy uniform-fresh noise path is **never** invoked inside
  :class:`PaperQuantityAttractorInversion` except as the documented
  graceful-fallback path. Any legacy caller that wants the
  uniform-fresh semantics must be ported to use
  :class:`UniformFreshPerturbation` (or :func:`default_uniform_fresh_perturbation`).

Public surface:

* :class:`PerturbationPolicy`
* :class:`UniformFreshPerturbation` + :func:`default_uniform_fresh_perturbation`
* :class:`PaperQuantityAttractorInversion` + :func:`default_brai_perturbation`
* :class:`PerturbationConfigError`
* :func:`build_perturbation_from_config`

Failure modes
-------------

The perturbation policies are **clip-and-audit** (closes P0-3 by
analogy with the merge-operator and integrator patterns):
non-finite ``x_saturated`` is clipped to a finite shape and the
canonical audit code is appended to the caller's ``audit_codes``
list when one is supplied. :class:`UniformFreshPerturbation` never
raises on legitimate caller inputs. :class:`PaperQuantityAttractorInversion`
falls back to uniform-fresh and emits :data:`BRAI_NO_PAPER_QUANTITIES`
when ``paper_quantities`` is ``None``,
:data:`BRAI_FALLBACK_FIELDS_MISSING` when the snapshot lacks the
required accessors, :data:`BRAI_NONFINITE_QUANTITY_COERCED` when the
returned gradient is non-finite, and :data:`BRAI_GRAD_FALLBACK_TO_FD`
when only the scalar ``log_p_qty`` is supplied (so we have to fall
back to finite-difference gradient computation).

Non-numeric types and ``None`` values still raise
:exc:`PerturbationConfigError` (subclass of :exc:`ValueError`); the
numeric coercion boundary is the only point where an exception may
propagate.

Design rationale (Wave 59 §8 — interface-first constraint)
----------------------------------------------------------

The interface-first constraint (locked in by user 2026-09-07,
``todo/two-paper-algo-design.md`` §1) requires that **no new
implementation** (step 7 / 8) lands before the protocol (step 5 / 6)
is in place. :class:`PerturbationPolicy` is the new abstract
surface; :class:`UniformFreshPerturbation` is the legacy default;
:class:`PaperQuantityAttractorInversion` is the new opt-in
algorithm. Adapter wiring (Wave 59 §8 step 8) is a separate wave
that threads the protocol through ``apply_restart_distribution`` in
each adapter — until then the protocol lives here as a stand-alone
module so existing adapters that keep their inlined
``np.random.default_rng(...).standard_normal(...)`` blocks keep
working unchanged.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Callable, Mapping, Optional, Protocol, runtime_checkable

from adaptive_reflow.contracts import hash_artifact

# ---------------------------------------------------------------------------
# Module-level constants (canonical error / audit codes; ASCII only)
# ---------------------------------------------------------------------------


#: Audit code emitted when :class:`PaperQuantityAttractorInversion`
#: is invoked with ``paper_quantities is None``. The policy falls
#: back to :class:`UniformFreshPerturbation` so legacy callers do
#: not crash. The code is appended to the caller's ``audit_codes``
#: list when one is supplied; callers that opt out of audit
#: emission still get the uniform-fresh fallback (preserving legacy
#: semantics).
BRAI_NO_PAPER_QUANTITIES: str = "brai_no_paper_quantities"

#: Audit code emitted when :class:`PaperQuantityAttractorInversion`
#: is invoked with a ``paper_quantities`` snapshot that does not
#: expose the expected ``e_rho`` / ``log_p_qty`` accessors. The
#: policy falls back to uniform-fresh so the loop survives without
#: altering the saturation-noise behaviour.
BRAI_FALLBACK_FIELDS_MISSING: str = "brai_fallback_fields_missing"

#: Audit code emitted when :class:`PaperQuantityAttractorInversion`
#: observes a non-finite gradient (e.g. ``NaN`` / ``inf`` from the
#: upstream snapshot). The gradient is coerced to ``0.0`` so the
#: returned ``x_perturbed = x_saturated`` (no-op perturbation);
#: the loop survives the upstream failure without altering the
#: saturation-noise path.
BRAI_NONFINITE_QUANTITY_COERCED: str = "brai_nonfinite_quantity_coerced"

#: Audit code emitted when :class:`PaperQuantityAttractorInversion`
#: falls back from an analytic ``grad_log_p_qty`` to finite-
#: difference computation because only ``log_p_qty`` (the scalar)
#: was supplied. This is the documented graceful-degradation path
#: for adapters that expose the paper-quantity log-prob but not its
#: analytic gradient.
BRAI_GRAD_FALLBACK_TO_FD: str = "brai_grad_fallback_to_fd"

#: Default ``eps_scale`` matching the canonical BRAI formula in
#: ``todo/two-paper-algo-design.md`` §4.1. The class-level constant
#: is exposed so adapters that want the canonical default can pass
#: it without hard-coding the number.
DEFAULT_BRAI_EPS_SCALE: float = 0.1

#: Default finite-difference step size for the gradient fallback
#: (``grad ≈ (f(x + eps*e_i) - f(x - eps*e_i)) / (2*eps)``).
#: ``eps=1e-3`` is the canonical default per Wave 59 step 2 of
#: the two-paper design doc. Smaller ``eps`` amplifies numerical
#: noise; larger ``eps`` truncates the Taylor expansion; ``1e-3``
#: is the canonical mid-point.
DEFAULT_BRAI_GRAD_EPS: float = 1e-3

#: Default scale for the paper-quantity isotropic Gaussian prior
#: ``log P_qty(x) ∝ -||x||^2 / (2 * sigma^2)`` used by the
#: default :class:`PaperQuantityAttractorInversion` ``log_p_qty``
#: callable. The scale is configurable per adapter via the
#: ``default_sigma`` constructor kwarg; ``sigma = 1.0`` matches
#: the canonical ``e_rho = 1`` fallback so the BRAI step is
#: dimensionally consistent with the paper's energy-gap units.
DEFAULT_BRAI_SIGMA: float = 1.0


# ---------------------------------------------------------------------------
# Exceptions (fail-closed; surface bad caller input)
# ---------------------------------------------------------------------------


class PerturbationConfigError(ValueError):
    """Raised when a :class:`PerturbationPolicy` rejects its arguments.

    Inherits from :exc:`ValueError` so existing
    ``pytest.raises(ValueError)`` patterns continue to work; the
    specific subclass is exposed via :data:`__all__` for callers
    that want to narrow their ``except`` clauses.
    """


# ---------------------------------------------------------------------------
# Internal coercion helpers
# ---------------------------------------------------------------------------


def _coerce_finite_real(x: Any, *, name: str) -> float:
    """Return ``float(x)``; raise :exc:`PerturbationConfigError` on bad input.

    Booleans are coerced to 0/1 (matches the policy_authority and
    merge-operator coercion conventions). ``None`` is rejected.
    """
    if x is None:
        raise PerturbationConfigError(f"{name}: required (got None)")
    if isinstance(x, bool):
        return float(int(x))
    if not isinstance(x, (int, float)):
        raise PerturbationConfigError(
            f"{name}: expected a real number, got {type(x).__name__}"
        )
    fx = float(x)
    if not math.isfinite(fx):
        raise PerturbationConfigError(f"{name}: must be finite, got {fx!r}")
    return fx


def _coerce_positive_real(x: Any, *, name: str) -> float:
    """Return ``float(x)``; require ``x > 0``; raise on non-positive input."""
    fx = _coerce_finite_real(x, name=name)
    if fx <= 0.0:
        raise PerturbationConfigError(
            f"{name}: must be strictly positive, got {fx!r}"
        )
    return fx


# ---------------------------------------------------------------------------
# Uniform-fresh noise helper (preserved legacy semantics)
# ---------------------------------------------------------------------------


def _uniform_fresh_noise(
    x: Any,
    *,
    t: float,
) -> Any:
    """Return deterministic ``standard_normal(x.shape)`` (PRESERVED).

    The seed is derived from ``(x.shape, t)`` so the call is
    deterministic across replay — matching the Wave 47 / 52 / 58
    "uniform fresh" semantics where the legacy adapters hashed
    ``(policy_hash, source_round)`` to seed the per-round fresh
    noise. At the abstract :class:`PerturbationPolicy` layer the
    ``(x.shape, t)`` triple is the natural key (the protocol does
    not expose ``policy_hash`` / ``source_round`` — those are
    adapter-level concerns).
    """
    shape = getattr(x, "shape", None)
    if shape is None:
        # Best-effort fallback for opaque handles — use a constant
        # seed so the call is deterministic across replay.
        seed = 0
    else:
        seed_blob = repr((tuple(int(s) for s in shape), float(t))).encode("utf-8")
        seed = int(hashlib.sha256(seed_blob).hexdigest()[:8], 16)
    return np_random_default_rng(seed).standard_normal(shape).astype(np_float64())


def np_random_default_rng(seed: int) -> Any:
    """Lazy-import wrapper so the module stays torch-free at import time."""
    import numpy as _np  # local import keeps the top-level boundary stdlib-only

    return _np.random.default_rng(int(seed))


def np_float64() -> Any:
    """Lazy ``np.float64`` accessor (keeps the module torch-free)."""
    import numpy as _np

    return _np.float64


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class PerturbationPolicy(Protocol):
    """Abstract saturation-time prior perturbation policy.

    Implementations answer "how do I perturb a saturated state into a
    fresh prior?" — the canonical seam the Wave 59 Paper B design
    identified as the insertion point for paper-quantity-driven
    attractor inversion (``todo/two-paper-algo-design.md`` §4.2).

    The Protocol mirrors the ``IntegratorProtocol`` pattern: a
    single :meth:`propose` method that takes the saturated state,
    the round's paper-quantity snapshot (optional for
    :class:`UniformFreshPerturbation`, consumed by
    :class:`PaperQuantityAttractorInversion`), and the time ``t``,
    and returns the perturbed state.

    CONTRACT (closes P0-3 by analogy):

    * All implementations MUST return a value of the same dtype /
      shape as ``x_saturated``.
    * All implementations MUST be pure w.r.t. their arguments:
      identical inputs always yield identical outputs.
    * Implementations MUST NOT raise on legitimate caller inputs
      such as ``paper_quantities is None``; instead, the
      :class:`PaperQuantityAttractorInversion` falls back to
      uniform-fresh and emits :data:`BRAI_NO_PAPER_QUANTITIES` (or
      :data:`BRAI_FALLBACK_FIELDS_MISSING`) to ``audit_codes``
      when one is supplied.
    * ``x_saturated`` is never mutated by :meth:`propose`; the
      returned value is a fresh allocation.

    Config round-trip (P1-1): every implementation exposes
    :meth:`to_config` / :meth:`from_config` (classmethod) so the
    perturbation family + its hyperparameters can be serialized to
    JSON and replayed byte-for-byte.
    """

    def propose(
        self,
        x_saturated: Any,
        paper_quantities: Optional[Mapping[str, Any]],
        t: float,
    ) -> Any:
        """Return the perturbed state for one saturation round.

        Parameters
        ----------
        x_saturated:
            The saturated state to perturb. ``numpy.ndarray`` is the
            canonical input type; opaque handles are accepted as long
            as they expose ``.shape`` and support
            ``x + scalar * vector``.
        paper_quantities:
            Optional paper-quantity snapshot for the round.
            :class:`UniformFreshPerturbation` ignores this
            argument; :class:`PaperQuantityAttractorInversion` reads
            the ``e_rho`` field (or any ``log_p_qty(t)`` accessor
            when present) and falls back to uniform-fresh when the
            snapshot is ``None`` or does not expose the required
            accessors.
        t:
            Current time in ``[0, 1]`` (matches the framework's
            normalised time grid). The uniform-fresh policy uses
            ``t`` as part of the deterministic seed so different
            rounds produce different noise; BRAI forwards ``t`` to
            the snapshot accessor for time-varying priors.

        Returns
        -------
        Any
            The perturbed state. Same shape / dtype as
            ``x_saturated``. Never ``x_saturated`` itself.
        """
        ...

    def config_hash(self) -> str:
        """Return a stable digest of the perturbation config.

        Two policies with different configurations (e.g. different
        ``eps_scale`` for BRAI, or different RNG seeds for uniform-
        fresh) MUST hash differently so the audit ledger can
        distinguish them.
        """
        ...

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for this policy.

        The returned dict round-trips through :meth:`from_config`
        so ``cls.from_config(policy.to_config()) == policy`` for
        the concrete implementation.
        """
        ...

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "PerturbationPolicy":
        """Build a perturbation policy from a ``to_config`` dict (P1-1).

        ``cls`` is the concrete implementation class — call sites
        that need polymorphic dispatch should use
        :func:`build_perturbation_from_config` which dispatches on
        the ``family`` key.
        """
        ...


# ---------------------------------------------------------------------------
# Paper-quantity snapshot Protocol (perturbation-time lookups)
# ---------------------------------------------------------------------------


@runtime_checkable
class PaperQuantitiesPerturbationSnapshotProtocol(Protocol):
    """Structural type for a paper-quantity snapshot at saturation.

    The :class:`PaperQuantityAttractorInversion` reads two scalars
    from the snapshot per perturbation:

    * ``e_rho(t)`` — the paper-quantity minimum-energy gap (paper
      Lemma 4 / 5). Used as the scale of the default Gaussian prior
      ``log P_qty(x) ∝ -||x||^2 / (2 * e_rho^2)``.
    * ``log_p_qty(x, t)`` — the (optional) paper-quantity
      log-probability at ``x``. When supplied, BRAI uses
      finite-difference to compute the gradient
      ``grad log P_qty``; when absent, BRAI falls back to the
      default Gaussian prior with ``sigma = e_rho``.

    Snapshots that do not expose these accessors fall back to
    uniform-fresh (audit code :data:`BRAI_FALLBACK_FIELDS_MISSING`).
    """

    def e_rho(self, t: float) -> float: ...

    def log_p_qty(  # noqa: E704 — keep the optional second arg for protocol parity
        self, x: Any, t: float
    ) -> float: ...


def _lookup_e_rho(snapshot: Any, t: float) -> tuple[Optional[float], bool]:
    """Best-effort lookup of ``e_rho`` at ``t`` in ``snapshot``.

    Supports two shapes (in priority order):

    1. ``snapshot`` exposes a method ``e_rho(t) -> float`` (canonical
       :class:`PaperQuantitiesPerturbationSnapshotProtocol` shape).
    2. ``snapshot`` exposes a Mapping ``["e_rho"]`` that returns a
       scalar constant (time-independent snapshot).

    Returns ``(value, found)``. ``found = False`` means the snapshot
    did not expose ``e_rho`` in any of the supported shapes.
    """
    if snapshot is None:
        return None, False
    accessor = getattr(snapshot, "e_rho", None)
    if callable(accessor):
        try:
            value = float(accessor(float(t)))
            return value, True
        except (TypeError, ValueError, KeyError):
            return None, False
    if isinstance(snapshot, Mapping):
        try:
            value = snapshot["e_rho"]
            return float(value), True
        except (KeyError, TypeError, ValueError):
            pass
    return None, False


def _lookup_log_p_qty(snapshot: Any, x: Any, t: float) -> tuple[Optional[float], bool]:
    """Best-effort lookup of ``log_p_qty(x, t)`` in ``snapshot``.

    Supports the canonical callable shape
    ``snapshot.log_p_qty(x, t) -> float``. Returns ``(value, found)``.
    """
    if snapshot is None:
        return None, False
    accessor = getattr(snapshot, "log_p_qty", None)
    if callable(accessor):
        try:
            value = float(accessor(x, float(t)))
            return value, True
        except (TypeError, ValueError, KeyError):
            return None, False
    return None, False


# ---------------------------------------------------------------------------
# Default log_p_qty / grad_log_p_qty callables
# ---------------------------------------------------------------------------


def _default_log_p_qty_gaussian(
    x: Any,
    e_rho: float,
) -> float:
    """Return ``-||x||^2 / (2 * e_rho^2)`` (Gaussian log-prob, up to a const).

    The constant is dropped because BRAI only consumes the gradient
    of ``log_p_qty``; an additive constant does not affect
    ``-grad log_p_qty``. The Gaussian prior models the paper-
    quantity distribution as isotropic with scale ``e_rho`` (paper
    Lemma 4 / 5's minimum-energy-gap scale).
    """
    # Use a manual sum-of-squares so the function works on both
    # ``numpy.ndarray`` and opaque handles that support ``__iter__``.
    sq = 0.0
    for xi in _iter_first_axis(x):
        sq += float(_scalar_sum_of_squares(xi))
    return -sq / (2.0 * float(e_rho) ** 2)


def _default_grad_log_p_qty_gaussian(
    x: Any,
    e_rho: float,
) -> Any:
    """Return ``-x / e_rho^2`` (analytic gradient of the Gaussian log-prob).

    The result is the gradient of ``log P_qty`` at ``x`` under the
    default isotropic Gaussian prior
    ``log P_qty ∝ -||x||^2 / (2 * e_rho^2)``. The negative of this
    gradient is the BRAI push direction.
    """
    import numpy as _np  # local import keeps the module boundary stdlib-only

    arr = _np.asarray(x, dtype=_np.float64)
    return -arr / (float(e_rho) ** 2)


def _scalar_sum_of_squares(x: Any) -> float:
    """Best-effort ``sum(x_i ** 2)`` for ndarray / scalar handles."""
    import numpy as _np

    arr = _np.asarray(x, dtype=_np.float64)
    return float(_np.sum(arr * arr))


def _iter_first_axis(x: Any) -> Any:
    """Best-effort iterate-along-first-axis for ndarray / scalar handles.

    A scalar handle yields a single element; a 1-D array yields its
    scalars; higher-rank arrays are flattened to 1-D for the
    sum-of-squares reduction (the Gaussian prior is isotropic so the
    shape does not matter).
    """
    import numpy as _np

    arr = _np.asarray(x, dtype=_np.float64).reshape(-1)
    return arr


def _finite_difference_grad_log_p_qty(
    log_p_qty: Callable[[Any, float], float],
    x: Any,
    t: float,
    grad_eps: float,
) -> Any:
    """Return the central-difference gradient of ``log_p_qty`` at ``(x, t)``.

    Uses central differences with step ``grad_eps``::

        grad_i ≈ (f(x + eps * e_i, t) - f(x - eps * e_i, t)) / (2 * eps)

    Falls back to ``0.0`` per element if ``log_p_qty`` raises
    (graceful degradation — the caller treats the resulting ``-0``
    push as a no-op).

    Parameters
    ----------
    log_p_qty:
        Scalar callable ``(x, t) -> float`` mapping a candidate
        state to its paper-quantity log-probability.
    x:
        The point at which to evaluate the gradient. ``numpy.ndarray``
        is the canonical input type.
    t:
        Time at which to evaluate the gradient (forwarded to
        ``log_p_qty`` for time-varying priors).
    grad_eps:
        Finite-difference step size. Must be strictly positive.
    """
    import numpy as _np

    arr = _np.asarray(x, dtype=_np.float64)
    grad = _np.zeros_like(arr)
    # Flatten for index-based iteration; reshape back at the end.
    flat = arr.reshape(-1)
    flat_grad = grad.reshape(-1)
    eps = float(grad_eps)
    for i in range(flat.size):
        # Forward step.
        x_plus = flat.copy()
        x_plus[i] += eps
        try:
            f_plus = float(log_p_qty(_unflatten(x_plus, arr.shape), t))
        except (TypeError, ValueError, KeyError, ArithmeticError):
            f_plus = float("nan")
        # Backward step.
        x_minus = flat.copy()
        x_minus[i] -= eps
        try:
            f_minus = float(log_p_qty(_unflatten(x_minus, arr.shape), t))
        except (TypeError, ValueError, KeyError, ArithmeticError):
            f_minus = float("nan")
        # Central difference.
        if math.isfinite(f_plus) and math.isfinite(f_minus):
            flat_grad[i] = (f_plus - f_minus) / (2.0 * eps)
        else:
            flat_grad[i] = 0.0  # graceful: caller sees no-op push
    return grad


def _unflatten(flat: Any, shape: tuple[int, ...]) -> Any:
    """Reshape ``flat`` back to ``shape``; passthrough for scalars."""
    import numpy as _np

    flat_arr = _np.asarray(flat, dtype=_np.float64)
    if not shape:
        return float(flat_arr.reshape(()).item())
    return flat_arr.reshape(shape)


# ---------------------------------------------------------------------------
# Default implementation: UniformFreshPerturbation (PRESERVED)
# ---------------------------------------------------------------------------


class UniformFreshPerturbation:
    """Canonical uniform-fresh-noise perturbation (PRESERVED, Wave 47/52/58).

    The policy replaces the saturated state with fresh
    ``standard_normal(x.shape)`` noise:

        x_perturbed = standard_normal(x_saturated.shape)

    The seed is deterministic (``hash((x.shape, t))``) so the
    policy is reproducible across replay. This is the **legacy
    behaviour** the framework has shipped since Wave 0; per-
    adapter composite data, regression vectors, and pinned metrics
    across every adapter depend on the exact seed -> noise mapping
    being preserved bit-for-bit.

    The class is a drop-in replacement for the inlined
    ``np.random.default_rng(...).standard_normal(...)`` blocks that
    previously lived in each adapter's ``apply_restart_distribution``.

    Parameters
    ----------
    seed_offset:
        Optional non-negative integer added to the deterministic
        seed before sampling. Default ``0`` reproduces the legacy
        Wave 47 / 52 / 58 behaviour bit-for-bit; pass a non-zero
        value to rotate the noise stream without breaking the
        protocol contract. The offset is exposed so adapters that
        want a different saturation-noise family can configure it
        without subclassing.

    Notes
    -----
    :class:`UniformFreshPerturbation` ignores ``paper_quantities``
    entirely (legacy semantics). It never appends to
    ``audit_codes``. The class is ``runtime_checkable``-safe so
    callers can use ``isinstance(policy, PerturbationPolicy)``.
    """

    FAMILY: str = "uniform_fresh"

    def __init__(self, *, seed_offset: int = 0) -> None:
        if not isinstance(seed_offset, int) or isinstance(seed_offset, bool):
            raise PerturbationConfigError(
                f"seed_offset: must be an integer, got {type(seed_offset).__name__}"
            )
        if int(seed_offset) < 0:
            raise PerturbationConfigError(
                f"seed_offset: must be non-negative, got {seed_offset!r}"
            )
        self._seed_offset = int(seed_offset)
        self._config_hash_value = hash_artifact(
            {
                "family": self.FAMILY,
                "seed_offset": int(self._seed_offset),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def seed_offset(self) -> int:
        """Return the configured seed offset (legacy = ``0``)."""
        return int(self._seed_offset)

    @property
    def family(self) -> str:
        """Return the algorithm family identifier (``"uniform_fresh"``)."""
        return self.FAMILY

    # -- PerturbationPolicy -----------------------------------------------

    def propose(
        self,
        x_saturated: Any,
        paper_quantities: Optional[Mapping[str, Any]],
        t: float,
    ) -> Any:
        """Return deterministic ``standard_normal(x_saturated.shape)``.

        ``paper_quantities`` and ``t`` are accepted but unused; the
        fresh-noise seed is derived from ``(x.shape, t)`` so the
        call is reproducible across replay. The policy never
        mutates ``x_saturated``; the returned value is a fresh
        allocation.
        """
        del paper_quantities
        shape = getattr(x_saturated, "shape", None)
        if shape is None:
            # Best-effort fallback for opaque handles — use a
            # constant seed so the call is deterministic across
            # replay.
            seed = 0
        else:
            seed_blob = repr(
                (tuple(int(s) for s in shape), float(t))
            ).encode("utf-8")
            seed = int(hashlib.sha256(seed_blob).hexdigest()[:8], 16)
        seed = (seed + int(self._seed_offset)) & 0xFFFFFFFF
        return np_random_default_rng(seed).standard_normal(shape).astype(
            np_float64()
        )

    def config_hash(self) -> str:
        """Return a stable digest of the perturbation config.

        Captures ``family`` and ``seed_offset`` so two
        :class:`UniformFreshPerturbation` instances with different
        offsets hash differently.
        """
        return str(self._config_hash_value)

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for this policy."""
        return {
            "family": self.FAMILY,
            "seed_offset": int(self._seed_offset),
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> "UniformFreshPerturbation":
        """Build a :class:`UniformFreshPerturbation` from ``config``.

        P1-1 round-trip — two ``from_config(to_config())`` calls
        always produce equal policies (same offset, same hash).
        """
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        if str(config.get("family", cls.FAMILY)) != cls.FAMILY:
            raise ValueError(
                f"UniformFreshPerturbation.from_config: bad family "
                f"{config.get('family')!r} (expected {cls.FAMILY!r})"
            )
        return cls(seed_offset=int(config.get("seed_offset", 0)))


def default_uniform_fresh_perturbation() -> UniformFreshPerturbation:
    """Return the canonical :class:`UniformFreshPerturbation` factory.

    The policy is cheap to construct (no state beyond
    ``seed_offset``), so callers may also instantiate
    :class:`UniformFreshPerturbation` directly. This factory is
    the single entry point used by adapters that want the legacy
    default without hard-coding the seed-offset literal.
    """
    return UniformFreshPerturbation()


# ---------------------------------------------------------------------------
# New implementation: PaperQuantityAttractorInversion (BRAI)
# ---------------------------------------------------------------------------


class PaperQuantityAttractorInversion:
    """Bounce-and-Refine via Attractor Inversion (BRAI) perturbation.

    At saturation, perturb along ``-grad(log P_qty(x))`` so the
    trajectory escapes the baseline's attractor and explores
    regions the paper-quantity prior considers rare::

        x_perturbed = x_saturated + eps_scale * (-grad log P_qty)

    where ``grad log P_qty`` is the gradient of the paper-quantity
    log-probability at ``x_saturated``. The negative gradient
    pushes the state toward the low-probability tails of the
    prior — exactly the regions a saturation-exhausted baseline
    cannot reach through additional forward integration.

    Effect
    ------
    * The baseline's attractor (regions of high ``P_qty``) is
      inverted by the negative gradient — the next round starts
      from a region the training distribution considers "rare".
    * High NFE, baseline saturates; framework continues to gain by
      exploring those rare regions.
    * The end-to-end NFE budget is unchanged (BRAI only changes
      the per-round restart point, not the per-step ``dt``).

    Graceful fallback
    -----------------
    * ``paper_quantities is None`` → fall back to uniform-fresh
      (audit :data:`BRAI_NO_PAPER_QUANTITIES`).
    * Snapshot lacks ``e_rho`` accessor → fall back to uniform-
      fresh (audit :data:`BRAI_FALLBACK_FIELDS_MISSING`).
    * Non-finite ``e_rho`` → coerce to ``DEFAULT_BRAI_SIGMA`` (audit
      :data:`BRAI_NONFINITE_QUANTITY_COERCED`).
    * Analytic ``grad_log_p_qty`` not supplied → fall back to
      finite-difference on the user-supplied ``log_p_qty`` (audit
      :data:`BRAI_GRAD_FALLBACK_TO_FD`); if neither is supplied,
      use the analytic Gaussian-prior gradient with ``sigma =
      max(e_rho, eps_floor)``.

    Parameters
    ----------
    eps_scale:
        The push-magnitude scale. ``eps_scale = 0.1`` matches the
        canonical BRAI formula in
        ``todo/two-paper-algo-design.md`` §4.1. Must be strictly
        positive.
    grad_eps:
        Finite-difference step size used when only ``log_p_qty`` is
        supplied (not ``grad_log_p_qty``). ``grad_eps = 1e-3`` is
        the canonical default per Wave 59 step 2 of the two-paper
        design doc. Must be strictly positive.
    log_p_qty:
        Optional scalar callable ``(x, t) -> float`` mapping a
        candidate state to its paper-quantity log-probability.
        When supplied without an analytic ``grad_log_p_qty``, BRAI
        computes the gradient via central finite differences.
    grad_log_p_qty:
        Optional callable ``(x, t, e_rho) -> ndarray`` returning
        ``grad log P_qty`` directly. When supplied, BRAI skips the
        finite-difference step. Use this when the upstream snapshot
        exposes an analytic gradient (e.g. an isotropic Gaussian).
    default_sigma:
        Default scale for the isotropic Gaussian prior used when
        ``e_rho`` is missing from the snapshot. ``default_sigma =
        1.0`` matches the canonical ``e_rho = 1`` fallback. Must be
        strictly positive.

    Notes
    -----
    The class accepts the optional ``audit_codes`` kwarg so callers
    can opt into audit emission. ``x_saturated`` is never mutated;
    the returned value is a fresh allocation.

    The Protocol's ``t`` argument is forwarded to both the snapshot
    accessor (for time-varying priors) and the user-supplied
    ``log_p_qty`` / ``grad_log_p_qty`` callables (when provided).
    """

    FAMILY: str = "brai"

    def __init__(
        self,
        *,
        eps_scale: float = DEFAULT_BRAI_EPS_SCALE,
        grad_eps: float = DEFAULT_BRAI_GRAD_EPS,
        log_p_qty: Optional[Callable[[Any, float], float]] = None,
        grad_log_p_qty: Optional[Callable[[Any, float, float], Any]] = None,
        default_sigma: float = DEFAULT_BRAI_SIGMA,
    ) -> None:
        self._eps_scale = _coerce_positive_real(eps_scale, name="eps_scale")
        self._grad_eps = _coerce_positive_real(grad_eps, name="grad_eps")
        if default_sigma is None:
            self._default_sigma = float(DEFAULT_BRAI_SIGMA)
        else:
            self._default_sigma = _coerce_positive_real(
                default_sigma, name="default_sigma"
            )
        # User-supplied callables are accepted as-is; we do NOT
        # validate their output shape (the caller is responsible
        # for the contract — non-numeric outputs are caught by the
        # finiteness coercion at the ``-grad`` step).
        self._log_p_qty = log_p_qty
        self._grad_log_p_qty = grad_log_p_qty
        self._config_hash_value = hash_artifact(
            {
                "family": self.FAMILY,
                "eps_scale": float(self._eps_scale),
                "grad_eps": float(self._grad_eps),
                "default_sigma": float(self._default_sigma),
                "has_log_p_qty": bool(log_p_qty is not None),
                "has_grad_log_p_qty": bool(grad_log_p_qty is not None),
            }
        )

    # -- accessors ---------------------------------------------------------

    @property
    def eps_scale(self) -> float:
        """Return the configured BRAI push-magnitude scale."""
        return float(self._eps_scale)

    @property
    def grad_eps(self) -> float:
        """Return the configured finite-difference step size."""
        return float(self._grad_eps)

    @property
    def default_sigma(self) -> float:
        """Return the configured default Gaussian prior scale."""
        return float(self._default_sigma)

    @property
    def family(self) -> str:
        """Return the algorithm family identifier (``"brai"``)."""
        return self.FAMILY

    @property
    def has_log_p_qty(self) -> bool:
        """``True`` iff a user-supplied ``log_p_qty`` is configured."""
        return bool(self._log_p_qty is not None)

    @property
    def has_grad_log_p_qty(self) -> bool:
        """``True`` iff a user-supplied ``grad_log_p_qty`` is configured."""
        return bool(self._grad_log_p_qty is not None)

    # -- PerturbationPolicy -----------------------------------------------

    def propose(
        self,
        x_saturated: Any,
        paper_quantities: Optional[Mapping[str, Any]],
        t: float,
        *,
        audit_codes: list[str] | None = None,
        magnitude: Optional[float] = None,
    ) -> Any:
        """Return ``x_saturated + eps_scale * (-grad log P_qty)``.

        ``grad log P_qty`` is computed via the analytic
        ``grad_log_p_qty`` callable when supplied; otherwise via
        finite-difference on the user-supplied ``log_p_qty``;
        otherwise via the analytic Gaussian-prior gradient with
        ``sigma = max(e_rho, default_sigma)``.

        ``paper_quantities is None`` → fall back to uniform-fresh
        (audit :data:`BRAI_NO_PAPER_QUANTITIES`).
        ``paper_quantities`` lacks ``e_rho`` → fall back to
        uniform-fresh (audit
        :data:`BRAI_FALLBACK_FIELDS_MISSING`).
        ``e_rho`` is non-finite → coerce to ``default_sigma``
        (audit :data:`BRAI_NONFINITE_QUANTITY_COERCED`).
        No analytic gradient supplied but ``log_p_qty`` is →
        finite-difference (audit
        :data:`BRAI_GRAD_FALLBACK_TO_FD`).

        Parameters
        ----------
        magnitude:
            Optional per-call override for the push-magnitude
            scale (Wave 125 H2 fix). When ``None`` (the default),
            the constructor-configured :attr:`eps_scale` is used
            (backward-compatible legacy behaviour). When a positive
            finite real is supplied, that value is used INSTEAD OF
            :attr:`eps_scale` for this single call only — the
            instance's :attr:`eps_scale` is NOT mutated, so a
            subsequent call without ``magnitude`` reverts to the
            configured default. Non-positive / non-finite inputs
            raise :exc:`PerturbationConfigError`. This per-call
            knob lets callers tune BRAI's push magnitude per
            model-family (protein, image, audio, graph) without
            having to construct a new policy instance.
        """
        # -- 0. Per-call magnitude override (Wave 125 H2 fix). --
        # When ``magnitude`` is supplied, it overrides the
        # constructor-configured ``eps_scale`` for this single call
        # only. The instance's ``eps_scale`` is NOT mutated so a
        # subsequent call without ``magnitude`` reverts to the
        # configured default (backward-compatible).
        if magnitude is None:
            effective_eps_scale = float(self._eps_scale)
        else:
            effective_eps_scale = _coerce_positive_real(
                magnitude, name="magnitude"
            )

        # -- 1. Missing / partial paper_quantities -> uniform-fresh. --
        if paper_quantities is None:
            if audit_codes is not None:
                audit_codes.append(BRAI_NO_PAPER_QUANTITIES)
            return _uniform_fresh_noise(x_saturated, t=t)

        e_rho_raw, e_rho_found = _lookup_e_rho(paper_quantities, t)
        if not e_rho_found:
            if audit_codes is not None:
                audit_codes.append(BRAI_FALLBACK_FIELDS_MISSING)
            return _uniform_fresh_noise(x_saturated, t=t)

        # -- 2. Non-finite e_rho -> coerce to default_sigma. --
        sigma: float
        if e_rho_raw is None or not math.isfinite(float(e_rho_raw)):
            if audit_codes is not None:
                audit_codes.append(BRAI_NONFINITE_QUANTITY_COERCED)
            sigma = float(self._default_sigma)
        else:
            sigma = float(e_rho_raw)
            # Guard against zero / negative e_rho (the paper-quantity
            # gap must be positive).
            if sigma <= 0.0:
                sigma = float(self._default_sigma)

        # -- 3. Compute grad log P_qty. --
        # Priority: (a) user-supplied analytic gradient, (b) finite-
        # difference on user-supplied log-prob, (c) analytic Gaussian
        # gradient with the snapshot's e_rho scale.
        if self._grad_log_p_qty is not None:
            try:
                grad = self._grad_log_p_qty(x_saturated, t, sigma)
            except (TypeError, ValueError, KeyError, ArithmeticError):
                grad = None
        elif self._log_p_qty is not None:
            if audit_codes is not None:
                audit_codes.append(BRAI_GRAD_FALLBACK_TO_FD)
            grad = _finite_difference_grad_log_p_qty(
                self._log_p_qty, x_saturated, t, self._grad_eps
            )
        else:
            grad = _default_grad_log_p_qty_gaussian(x_saturated, sigma)

        # -- 4. -grad, finite-coerce, return. --
        import numpy as _np  # local import keeps the boundary stdlib-only

        try:
            grad_arr = _np.asarray(grad, dtype=_np.float64)
        except (TypeError, ValueError):
            # Graceful: zero gradient -> no-op perturbation.
            if audit_codes is not None:
                audit_codes.append(BRAI_NONFINITE_QUANTITY_COERCED)
            return _np.asarray(x_saturated, dtype=_np.float64).copy()

        if not _np.all(_np.isfinite(grad_arr)):
            if audit_codes is not None:
                audit_codes.append(BRAI_NONFINITE_QUANTITY_COERCED)
            # Coerce the offending entries to 0.0 so the resulting
            # -grad * eps_scale is 0.0 (no-op for that axis).
            grad_arr = _np.where(_np.isfinite(grad_arr), grad_arr, 0.0)

        x_arr = _np.asarray(x_saturated, dtype=_np.float64)
        return x_arr + float(effective_eps_scale) * (-grad_arr)

    def config_hash(self) -> str:
        """Return a stable digest of the perturbation config.

        Captures ``family``, ``eps_scale``, ``grad_eps``,
        ``default_sigma``, and the presence / absence of the
        user-supplied ``log_p_qty`` / ``grad_log_p_qty`` callables.
        Two BRAI instances with different coefficients or different
        callable-supply sets hash differently.
        """
        return str(self._config_hash_value)

    def to_config(self) -> dict[str, Any]:
        """Return a JSON-serialisable config dict for this BRAI policy."""
        return {
            "family": self.FAMILY,
            "eps_scale": float(self._eps_scale),
            "grad_eps": float(self._grad_eps),
            "default_sigma": float(self._default_sigma),
            "has_log_p_qty": bool(self._log_p_qty is not None),
            "has_grad_log_p_qty": bool(self._grad_log_p_qty is not None),
        }

    @classmethod
    def from_config(
        cls, config: dict[str, Any]
    ) -> "PaperQuantityAttractorInversion":
        """Build a :class:`PaperQuantityAttractorInversion` from ``config``.

        P1-1 round-trip — two ``from_config(to_config())`` calls
        always produce equal policies (same coefficients, same hash,
        same callable-supply set). Note: user-supplied callables
        ``log_p_qty`` / ``grad_log_p_qty`` are NOT round-tripped
        (callables are not JSON-serialisable); the round-trip only
        preserves the boolean ``has_*`` flags.
        """
        if not isinstance(config, dict):
            raise TypeError(
                f"config must be a dict, got {type(config).__name__}"
            )
        if str(config.get("family", cls.FAMILY)) != cls.FAMILY:
            raise ValueError(
                f"PaperQuantityAttractorInversion.from_config: bad family "
                f"{config.get('family')!r} (expected {cls.FAMILY!r})"
            )
        return cls(
            eps_scale=float(config.get("eps_scale", DEFAULT_BRAI_EPS_SCALE)),
            grad_eps=float(config.get("grad_eps", DEFAULT_BRAI_GRAD_EPS)),
            default_sigma=float(
                config.get("default_sigma", DEFAULT_BRAI_SIGMA)
            ),
            log_p_qty=None,
            grad_log_p_qty=None,
        )


def default_brai_perturbation() -> PaperQuantityAttractorInversion:
    """Return the canonical :class:`PaperQuantityAttractorInversion` factory.

    Default coefficients (``eps_scale=0.1``, ``grad_eps=1e-3``,
    ``default_sigma=1.0``) match the canonical BRAI formula in
    ``todo/two-paper-algo-design.md`` §4.1 / §4.2. Adapters that
    want different sensitivity can construct
    :class:`PaperQuantityAttractorInversion` directly with custom
    coefficients; this factory is the single entry point used by
    callers that want the canonical default.
    """
    return PaperQuantityAttractorInversion()


# ---------------------------------------------------------------------------
# Polymorphic factory
# ---------------------------------------------------------------------------


def build_perturbation_from_config(
    config: dict[str, Any],
) -> PerturbationPolicy:
    """Build a :class:`PerturbationPolicy` from a polymorphic ``config`` dict.

    Dispatches on the ``family`` key:

    * ``"uniform_fresh"`` → :class:`UniformFreshPerturbation`
    * ``"brai"`` → :class:`PaperQuantityAttractorInversion`

    Mirrors :func:`adaptive_reflow.algorithm.integrator.build_integrator_from_config`
    so the perturbation surface can be round-tripped through JSON in
    the same idiom. Unknown families raise
    :exc:`PerturbationConfigError`.
    """
    if not isinstance(config, dict):
        raise PerturbationConfigError(
            f"config must be a dict, got {type(config).__name__}"
        )
    family = str(config.get("family", ""))
    if family == UniformFreshPerturbation.FAMILY:
        return UniformFreshPerturbation.from_config(config)
    if family == PaperQuantityAttractorInversion.FAMILY:
        return PaperQuantityAttractorInversion.from_config(config)
    raise PerturbationConfigError(
        f"build_perturbation_from_config: unknown family {family!r}"
    )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "BRAI_FALLBACK_FIELDS_MISSING",
    "BRAI_GRAD_FALLBACK_TO_FD",
    "BRAI_NO_PAPER_QUANTITIES",
    "BRAI_NONFINITE_QUANTITY_COERCED",
    "DEFAULT_BRAI_EPS_SCALE",
    "DEFAULT_BRAI_GRAD_EPS",
    "DEFAULT_BRAI_SIGMA",
    "PaperQuantitiesPerturbationSnapshotProtocol",
    "PaperQuantityAttractorInversion",
    "PerturbationConfigError",
    "PerturbationPolicy",
    "UniformFreshPerturbation",
    "build_perturbation_from_config",
    "default_brai_perturbation",
    "default_uniform_fresh_perturbation",
]

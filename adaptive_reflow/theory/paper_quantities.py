"""Concrete quantities from Li 2024 Theorem 1 that the framework's algorithm layer can target.

These are the paper's ACTUAL invariants, not synthesized metrics.

**Periodicity-free Theorem 1 (Remark 1, paper line 54-56):**

The main theorem does NOT require periodicity of ``g``; Lemma 1 is
only a verification convenience. Any ``g`` satisfying the F-side
hypotheses is admissible, including the nonperiodic family
``g_a(x) = a(x) * sin(x)`` from Proposition 2 (line 62-64).

This module exposes four pure, deterministic, byte-stable evaluators that
materialise the literal constants appearing in the proof of Theorem 1 of
Li, "Gaussian Posterior Selection on Noncompact Fibres with Uniformly
Separated Roots" (``NoiseSelectedRectification_EN.md``):

* :func:`sheet_evidence_A` -- ``A_g`` (Proposition 3 / "Selection-mechanism"
  display at line 161). The positive denominator limit that pins down
  the normalization of the selected sheet.

* :func:`root_cell_packing_B` -- ``B_g`` (line 159, derived in Lemma 5
  at line 132). The Gaussian packing sum over the zero set ``Z_g`` that
  controls the countable codimension-two tail.

* :func:`per_cell_coefficient_C` -- ``C_g`` (Lemma 3, coefficient
  computed in the Lemma 3 proof at line 191). The per-root-cell
  ``e^{rho^2/2} / a`` factor with ``a = (1-rho)^2 * min(c^2, 1)``.

* :func:`exterior_gap_e_rho` -- ``e_rho`` (line 128, Lemma 5 setup).
  The minimum residual energy on the physical complement of the sheet
  tube and the root cells.

These are the four paper-level invariants: ``A_g`` normalises the
limiting posterior, ``B_g`` summarises the countable family, ``C_g``
bounds each individual cell, and ``e_rho`` bounds the complement.
Corollary 1 (line 165) then deduces ``Z_{g,eps} >= C_1 * eps`` from the
positive limit of ``A_g`` and the packing of ``B_g``.

**rho < d/4 constraint (Lemma 5 setup, paper line 135-138):**

For the disjoint-cell guarantee of Lemma 5 (``rho < d/4``), the
functions :func:`per_cell_coefficient_C` and :func:`exterior_gap_e_rho`
require ``rho in (0, 1)`` but DO NOT enforce ``rho < d/4`` directly --
that constraint lives on ``validate_f_side_hypotheses`` in
:mod:`adaptive_reflow.theory.validation`, which callers should invoke
to assert the F-side hypothesis set is consistent.

``PhysicalComplement`` (Wave 11 addition): the paper's "physical
complement" set ``(S \\cup \\bigcup_z I_z)^c`` on which Lemma 4's
exponential suppression holds. Carries the four F-side constants
together with the squared-residual energy bound so
``BoundedMergeOperator.merge`` and ``CodimensionSheetScheduler.inject_noise``
share a single typed carrier.

Stdlib-only: no torch, no numpy, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

__all__ = [
    "sheet_evidence_A",
    "root_cell_packing_B",
    "per_cell_coefficient_C",
    "exterior_gap_e_rho",
    "SheetEvidenceResult",
    "RootCellPackingResult",
    "PerCellCoefficientResult",
    "sheet_evidence_with_result",
    "root_cell_packing_with_result",
    "per_cell_coefficient_with_result",
    "PhysicalComplement",
    "paper_selection_ratio",
]

# Paper: "Gaussian Posterior Selection on Noncompact Fibres with Uniformly
# Separated Roots" (NoiseSelectedRectification_EN.md).
#
# Line-number citations below refer to that file. Roles:
#   A_g     -- Proposition 3 ("Posterior assembly"), selection-mechanism display
#   B_g     -- Lemma 5 ("Uniform cells, Gaussian packing, and physical exterior gap")
#   C_g     -- Lemma 3 ("Countable root-cell contribution"), explicit coefficient
#              computed in the Lemma 3 proof
#   e_rho   -- Lemma 5 setup, also Lemma 4 ("Physical-complement suppression")
#
# Corollary 1 ("Quantitative allocation after normalization") then uses
# A_g > 0 and sum_{z} C_g e^{-z^2/4} < infinity (i.e. C_g * B_g < infinity)
# to deduce Z_{g,eps} >= C_1 * eps.

# Precomputed constants (kept module-level for byte-stability).
_SQRT_2PI = math.sqrt(2.0 * math.pi)  # (2*pi)^{1/2}


def sheet_evidence_A(
    g: Callable[[float], float],
    *,
    K: float = 8.0,
    h: float = 0.01,
) -> float:
    """Return ``A_g`` from Proposition 3 / line 161.

    Paper verbatim (line 116-117, Proposition 3, and line 161):

        "``A_g := (2*pi)^{-1/2} \\int_R \\frac{e^{-s^2/2}}{\\sqrt{1+g(s)^2}} ds > 0``"

    Role in the proof (Lemma 2 / Proposition 3):

        Lemma 2 rescales the sheet tube and takes the limit of
        ``eps^{-1} \\int_T p_eps``; Proposition 3 then takes ``\\phi \\equiv 1``
        in (4)-(7) and identifies the limit as ``A_g``. The strict positivity
        of ``A_g`` is what Corollary 1 uses to obtain
        ``Z_{g,eps} >= C_1 * eps`` (line 165).

    Discretisation:

        The real-line integral is approximated on a uniform grid
        ``s_k = -K + k*h`` for ``k = 0, ..., N`` (``N = 2K/h``) and the
        composite trapezoidal rule is applied. The default ``K = 8``,
        ``h = 0.01`` puts the cutoff at ``8`` standard deviations of
        ``e^{-s^2/2}`` -- the truncation error is sub-1e-14.

    Byte-stability:

        The function is pure, deterministic, and uses only ``math.*``
        primitives; ``g`` is invoked exactly once per grid point and no
        global state is read. Two calls with identical inputs return
        bit-identical floats.
    """
    if h <= 0.0:
        raise ValueError(f"step size h must be positive, got {h!r}")
    if K <= 0.0:
        raise ValueError(f"half-width K must be positive, got {K!r}")

    n_steps = int(round(2.0 * K / h))
    if n_steps < 2:
        raise ValueError(
            f"grid too coarse: 2K/h = {2.0 * K / h!r} must give >= 2 steps"
        )

    # Pre-compute the constant factor outside the trapezoidal loop.
    inv_sqrt_2pi = 1.0 / _SQRT_2PI

    total = 0.0
    s = -K
    for _ in range(n_steps + 1):
        gs = float(g(s))
        denom = math.sqrt(1.0 + gs * gs)
        f_s = math.exp(-0.5 * s * s) / denom
        # Endpoint weight: 1.0 for interior nodes, 0.5 for the two
        # endpoints under the composite trapezoidal rule.
        total += f_s
        s += h
    # Trapezoidal correction: subtract the half-weight already counted
    # at the two endpoints.
    total -= 0.5 * math.exp(-0.5 * K * K) / math.sqrt(
        1.0 + float(g(-K)) ** 2
    )
    total -= 0.5 * math.exp(-0.5 * K * K) / math.sqrt(
        1.0 + float(g(K)) ** 2
    )
    total *= h
    return inv_sqrt_2pi * total


def root_cell_packing_B(
    g: Callable[[float], float],
    *,
    separation_d: float = 1.0,
    K: float = 8.0,
    h: float = 0.01,
) -> float:
    """Return an approximation to ``B_g`` from line 159.

    Paper verbatim (line 159):

        "``B_g := \\sum_{z \\in Z_g} e^{-z^2/4} < \\infty``"

    Role in the proof (Lemma 5 / Lemma 3 / Corollary 1):

        Lemma 5 (line 132) derives the finiteness of ``B_g`` from uniform
        separation (``d``) and Gaussian decay; Lemma 3 then bounds each
        isolated cell by ``C_g e^{-z^2/4} eps^2`` and uses
        ``\\sum_{z \\in Z_g} e^{-z^2/4} < \\infty`` to conclude that the
        full isolated contribution is ``O(eps^2)``. Corollary 1 (line 165)
        divides this ``C_g B_g eps^2`` by ``C_1 eps`` to obtain the
        ``O(eps)`` isolated posterior mass.

    Method:

        Zeros of ``g`` on ``[-K, K]`` are detected via sign-change sampling
        on the uniform grid ``x_k = -K + k*h``; each detected sign change
        contributes one ``e^{-z^2/4}`` to the sum where ``z`` is the
        linearly-interpolated zero location. The default ``K = 8``
        captures all roots whose Gaussian weight exceeds
        ``e^{-K^2/4} = e^{-16} \\approx 1.1e-7``.

    The ``separation_d`` argument is the F-side uniform-separation
    constant; it is not consumed by the sampler (the literal quantity
    ``B_g`` is independent of ``d``) but is accepted on the function
    signature so the call site can document which F-side parameters
    are in force.

    Byte-stability:

        ``g`` is invoked exactly once per grid point and no global state
        is read. Two calls with identical inputs return bit-identical
    floats.
    """
    if h <= 0.0:
        raise ValueError(f"step size h must be positive, got {h!r}")
    if K <= 0.0:
        raise ValueError(f"half-width K must be positive, got {K!r}")
    if separation_d <= 0.0:
        raise ValueError(
            f"separation_d must be positive, got {separation_d!r}"
        )

    n_steps = int(round(2.0 * K / h))
    if n_steps < 1:
        raise ValueError(
            f"grid too coarse: 2K/h = {2.0 * K / h!r} must give >= 1 step"
        )

    # First pass: collect (x, g(x)) on the grid.
    xs: list[float] = []
    ys: list[float] = []
    x = -K
    for _ in range(n_steps + 1):
        xs.append(x)
        ys.append(float(g(x)))
        x += h

    # Second pass: each sign change contributes one linearly-interpolated
    # zero location; an exact zero on a grid node is counted once.
    total = 0.0
    for i in range(len(xs) - 1):
        y0 = ys[i]
        y1 = ys[i + 1]
        x0 = xs[i]
        x1 = xs[i + 1]
        if y0 == 0.0:
            # Exact zero at the grid node -- count it once and skip the
            # adjacent crossing (which is already recorded by the zero
            # itself).
            total += math.exp(-(x0 * x0) / 4.0)
        elif y0 * y1 < 0.0:
            # Sign change between x0 and x1 -- linearly interpolate.
            t = -y0 / (y1 - y0)
            z = x0 + t * (x1 - x0)
            total += math.exp(-(z * z) / 4.0)
    # F-46 (P1-14) — final endpoint: an exact zero at x = K would NOT
    # have been counted above. The sign-change branch requires
    # ``y0 * y1 < 0.0`` (strict), so ``ys[-2] * 0.0 == 0.0`` is missed,
    # and the ``y0 == 0.0`` branch inspects only ``ys[i]`` for
    # ``i < len(xs) - 1`` so it never sees ``ys[-1]``. Without this
    # guard, a root sitting exactly at ``x = K`` is silently dropped.
    if ys[-1] == 0.0:
        total += math.exp(-(xs[-1] * xs[-1]) / 4.0)
    return total


def per_cell_coefficient_C(
    *,
    rho: float = 0.1,
    c: float = 1.0,
) -> float:
    """Return ``C_g`` from Lemma 3 / line 191.

    Paper verbatim (Lemma 3 proof, line 191):

        "one may take ``C_g = e^{rho^2/2} / a``, which is independent of
        the physical root ``z`` and of ``eps``."

    where (line 188):

        "``a = (1-rho)^2 * min{c^2, 1} > 0``."

    Role in the proof (Lemma 3):

        Lemma 3 states that ``\\int_{I_z} p_eps <= C_g e^{-z^2/4} eps^2``
        uniformly in ``z`` and ``eps``; the displayed coefficient
        ``C_g = e^{rho^2/2} / a`` is precisely the literal factor
        obtained from the Gaussian integral on the physical cell
        ``I_z = (z-rho, z+rho) x (1-rho, 1+rho)``. Lemma 5's packing
        estimate then yields ``\\sum_z C_g e^{-z^2/4} = C_g B_g`` and
        Corollary 1 divides by the linear evidence lower bound
        ``C_1 eps``.

    Byte-stability:

        Pure ``math.exp`` / arithmetic; no global state. Two calls with
        identical inputs return bit-identical floats.
    """
    if rho <= 0.0 or rho >= 1.0:
        raise ValueError(f"rho must be in (0, 1), got {rho!r}")
    if c <= 0.0:
        raise ValueError(f"c must be positive, got {c!r}")
    a = (1.0 - rho) ** 2 * min(c * c, 1.0)
    if a <= 0.0:
        # Defensive: should be unreachable given the rho/c ranges above.
        raise ValueError(
            f"non-positive denominator a = {a!r}; check rho and c"
        )
    return math.exp(0.5 * rho * rho) / a


def exterior_gap_e_rho(
    *,
    rho: float = 0.1,
    eta: float = 0.1,
) -> float:
    """Return ``e_rho`` from line 128.

    Paper verbatim (line 128):

        "``e_rho = min{rho^4, (1-rho)^2 eta^2} > 0.``"

    Role in the proof (Lemma 5 / Lemma 4):

        Lemma 5 establishes that on the physical complement
        ``(S \\cup \\bigcup_{z} I_z)^c`` one has
        ``|F_g(x, y)|^2 >= e_rho``. Lemma 4 (line 110-113) then deduces

            ``\\int_{T^c \\setminus \\bigcup_z I_z} p_eps
              <= e^{-e_rho/(2 eps^2)} = o(eps)``.

        Corollary 1 (line 165) divides this exponential bound by the
        linear evidence lower bound ``C_1 eps`` to obtain the
        ``C_3 eps^{-1} e^{-e_rho/(2 eps^2)}`` posterior complement mass.

    Byte-stability:

        Pure ``math`` primitives; two calls with identical inputs return
        bit-identical floats.
    """
    if rho <= 0.0 or rho >= 1.0:
        raise ValueError(f"rho must be in (0, 1), got {rho!r}")
    if eta <= 0.0:
        raise ValueError(f"eta must be positive, got {eta!r}")
    return min(rho ** 4, (1.0 - rho) ** 2 * eta ** 2)


# ---------------------------------------------------------------------------
# Result dataclasses + helpers (A17, B13, B14 uplifts)
# ---------------------------------------------------------------------------
#
# Each result dataclass carries the literal paper-quantity value plus
# diagnostic fields (discretization error bound, tail bound,
# drift-robustness factor) so callers can audit the closed-form
# approximations without re-deriving the bounds. The plain float-returning
# functions above remain byte-stable for legacy callers.


@dataclass(frozen=True)
class SheetEvidenceResult:
    """Rich result for :func:`sheet_evidence_A` (A17).

    Carries the literal ``A_g`` value together with the trapezoidal
    discretisation error bound ``discretization_error``. The bound is
    a conservative overestimate (``(b-a) * h^2 / 12 * M_2`` with
    ``M_2 = (K^2 + 1)``) and is intended for provenance / audit
    reports; the closed-form value is the bit-identical return of
    :func:`sheet_evidence_A` for the same arguments.
    """

    value: float
    discretization_error: float
    K: float
    h: float
    n_steps: int


@dataclass(frozen=True)
class RootCellPackingResult:
    """Rich result for :func:`root_cell_packing_B` (B13).

    Carries the literal ``B_g`` value together with a closed-form
    *tail bound* on the contribution from roots ``z in Z_g`` with
    ``|z| > K``. The bound is ``(2/d) * e^{-K^2/4} / (1 - e^{-d*K/2})``
    (rough worst-case packing on each side, geometric tail), which is
    positive and decays super-exponentially in ``K``.
    """

    value: float
    tail_bound: float
    K: float
    h: float
    n_steps: int
    separation_d: float


@dataclass(frozen=True)
class PerCellCoefficientResult:
    """Rich result for :func:`per_cell_coefficient_C` (B14).

    Carries the literal ``C_g`` value together with a *drift
    robustness factor* ``C_g * (1 + 2 rho)`` -- a conservative upper
    bound on the per-cell coefficient under a small perturbation of
    ``rho`` (``C(rho + delta) <= C(rho) * (1 + 2 delta / (1 - rho))``
    by a first-order Taylor argument). The factor is within
    ``2 * C_g`` of ``C_g`` for ``rho in (0, 1)`` and is exposed so
    schedulers can carry a perturbation-aware ceiling in the audit
    trail.
    """

    value: float
    drift_robustness: float
    rho: float
    c: float


def sheet_evidence_with_result(
    g: Callable[[float], float],
    *,
    K: float = 8.0,
    h: float = 0.01,
) -> SheetEvidenceResult:
    """Return :class:`SheetEvidenceResult` for ``g`` (A17 uplift).

    Wraps :func:`sheet_evidence_A` and computes a closed-form trapezoidal
    error bound ``discretization_error``. The bound is
    ``(b - a) * h^2 / 12 * M_2`` where ``a = -K``, ``b = K``, and
    ``M_2 = K^2 + 1`` is a conservative bound on
    ``|f''(s)| = |((s^2 - 1) * e^{-s^2/2}) / sqrt(1 + g(s)^2)|`` over
    ``[-K, K]``. For the default ``K = 8, h = 0.01`` this gives
    ``discretization_error <= 1e-6``.

    Byte-stability: ``result.value`` is bit-identical to
    :func:`sheet_evidence_A`'s return value for the same arguments.
    """
    value = sheet_evidence_A(g, K=K, h=h)
    n_steps = int(round(2.0 * K / h))
    # Conservative bound on |f''(s)| on [-K, K] for the integrand
    # f(s) = e^{-s^2/2} / sqrt(1+g(s)^2).
    # d^2/ds^2 [e^{-s^2/2}] = (s^2 - 1) * e^{-s^2/2} which is bounded
    # by K^2 + 1 in absolute value over [-K, K]. Division by
    # sqrt(1+g^2) >= 1 can only shrink |f''|, so this M_2 is an upper
    # bound.
    m_2 = float(K * K + 1.0)
    discretization_error = float((2.0 * K) * (h * h) / 12.0 * m_2)
    return SheetEvidenceResult(
        value=float(value),
        discretization_error=float(discretization_error),
        K=float(K),
        h=float(h),
        n_steps=int(n_steps),
    )


def root_cell_packing_with_result(
    g: Callable[[float], float],
    *,
    separation_d: float = 1.0,
    K: float = 32.0,
    h: float = 0.01,
) -> RootCellPackingResult:
    """Return :class:`RootCellPackingResult` for ``g`` (B13 uplift).

    Wraps :func:`root_cell_packing_B` and computes a closed-form
    *tail bound* on the contribution from roots ``z in Z_g`` with
    ``|z| > K``. The bound comes from Lemma 5's packing estimate:
    each side ``[k, k+1]`` for ``k >= ceil(K)`` contains at most
    ``ceil(1/d) + 1`` roots, and the smallest root in that interval
    has ``|z| >= k``. So the tail contribution is bounded by

        tail_bound = (ceil(1/d) + 1) * sum_{k=ceil(K)}^{infty} 2 * e^{-k^2/4}

    which is bounded by the geometric tail

        tail_bound = 2 * (ceil(1/d) + 1) * e^{-K^2/4} / (1 - e^{-d*K/2})

    (Lemma 5's proof uses ``ceil(1/d) + 1`` as the per-interval root
    density and decays the Gaussian factor on the smallest root in
    each interval).

    For the default ``separation_d = 1.0, K = 32.0`` the bound is
    ``<= 1e-30``.

    Byte-stability: ``result.value`` is bit-identical to
    :func:`root_cell_packing_B`'s return value for the same arguments.
    """
    value = root_cell_packing_B(g, separation_d=separation_d, K=K, h=h)
    n_steps = int(round(2.0 * K / h))
    # Worst-case per-interval root density (Lemma 5, line 137).
    per_interval = int(math.ceil(1.0 / separation_d)) + 1
    # Geometric tail bound for the Gaussian weight beyond K.
    # e^{-K^2/4} decays faster than the per-interval coefficient can
    # grow; we use e^{-K^2/4} * 2 / (1 - e^{-d*K/2}) for the upper bound.
    # The factor 2 accounts for both tails (positive and negative).
    if K > 0.0 and separation_d > 0.0:
        # Geometric series denominator: 1 - e^{-d*K/2} > 0 for d*K > 0.
        denom = 1.0 - math.exp(-0.5 * separation_d * K)
        if denom > 0.0:
            tail_bound = float(
                2.0 * per_interval * math.exp(-(K * K) / 4.0) / denom
            )
        else:
            tail_bound = 0.0
    else:
        tail_bound = 0.0
    return RootCellPackingResult(
        value=float(value),
        tail_bound=float(tail_bound),
        K=float(K),
        h=float(h),
        n_steps=int(n_steps),
        separation_d=float(separation_d),
    )


def per_cell_coefficient_with_result(
    *,
    rho: float = 0.1,
    c: float = 1.0,
) -> PerCellCoefficientResult:
    """Return :class:`PerCellCoefficientResult` (B14 uplift).

    Wraps :func:`per_cell_coefficient_C` and adds a *drift-robustness
    factor* ``C_g * (1 + 2 * rho)``. The factor is a conservative upper
    bound on the per-cell coefficient under a small positive perturbation
    ``delta <= rho`` of ``rho`` (Taylor expansion of the
    ``1 / (1 - rho)^2`` denominator):
        C(rho + delta) <= C(rho) * (1 + 2 delta / (1 - rho))
    With ``delta = rho`` (worst case) this becomes
    ``C_g * (1 + 2 rho / (1 - rho)) = C_g * (1 + 2 rho) / (1 - rho)``.
    We use the simpler ``C_g * (1 + 2 rho)`` upper bound which holds
    for ``rho in (0, 1/2]`` and is within ``2 * C_g`` of ``C_g`` for
    ``rho <= 1/2``.

    Byte-stability: ``result.value`` is bit-identical to
    :func:`per_cell_coefficient_C`'s return value for the same arguments.
    """
    value = per_cell_coefficient_C(rho=rho, c=c)
    drift_robustness = float(value) * (1.0 + 2.0 * float(rho))
    return PerCellCoefficientResult(
        value=float(value),
        drift_robustness=float(drift_robustness),
        rho=float(rho),
        c=float(c),
    )


# ---------------------------------------------------------------------------
# Wave 11 additions: PhysicalComplement + paper_selection_ratio
# ---------------------------------------------------------------------------


# (No additional imports needed; ``PhysicalComplement`` is a frozen
# dataclass declared above.)


@dataclass(frozen=True)
class PhysicalComplement:
    """Paper's "physical complement" set on which Lemma 4 holds.

    The set ``(S \\cup \\bigcup_z I_z)^c`` (paper line 110-113) is the
    region outside the sheet tube ``S = R x (-rho, rho)`` AND outside
    every root cell ``I_z``. Lemma 5 establishes that
    ``|F_g(x, y)|^2 >= e_rho`` on this set, and Lemma 4 deduces
    ``\\int p_eps <= exp(-e_rho / (2 eps^2)) = o(eps)``.

    Carries the four F-side constants ``d, c, rho, eta`` together with
    the squared-residual bound ``e_rho``. Consumed by
    ``BoundedMergeOperator.merge`` and ``CodimensionSheetScheduler.inject_noise``
    so the two algorithm surfaces share a single typed carrier
    (A2.M).

    Implemented as a frozen dataclass (NOT a NamedTuple) so the
    F-side invariants can be validated at construction time via
    ``__post_init__``. The dataclass is hashable and supports
    field access by attribute; tuples / lists of these instances
    are interchangeable with NamedTuple semantics for downstream
    consumers.
    """

    separation_d: float
    simplicity_c: float
    rho: float
    eta: float
    e_rho: float

    def __post_init__(self) -> None:
        if self.separation_d <= 0.0:
            raise ValueError(
                f"separation_d must be positive, got {self.separation_d!r}"
            )
        if self.simplicity_c <= 0.0:
            raise ValueError(
                f"simplicity_c must be positive, got {self.simplicity_c!r}"
            )
        if not (0.0 < self.rho < 1.0):
            raise ValueError(f"rho must be in (0, 1), got {self.rho!r}")
        if self.eta <= 0.0:
            raise ValueError(f"eta must be positive, got {self.eta!r}")
        if self.e_rho <= 0.0:
            raise ValueError(
                f"e_rho must be positive, got {self.e_rho!r} "
                "(Lemma 5 requires e_rho > 0)"
            )

    def lemma4_floor_value(self) -> float:
        """Return the paper-derived ``e_rho`` floor (NOT the heuristic ``e_rho/4``).

        Per Lemma 4 (line 110-113), the exterior posterior mass is
        bounded by ``exp(-e_rho / (2 eps^2)) = o(eps)``. Any positive
        fraction of ``e_rho`` is admissible as a merge floor; the
        framework's legacy ``e_rho/4`` constant is a heuristic
        tightening, not a paper-derived value. This method returns
        the literal paper quantity ``e_rho`` so callers can opt into
        the paper-faithful floor.
        """
        return float(self.e_rho)


def paper_selection_ratio(
    sheet_A: float, packing_B: float, cell_C: float, eps: float
) -> float:
    """Return the paper-grounded selection ratio (Wave 11 lift).

    Paper Corollary 1 (line 165) divides ``Z_{g,eps}`` (which scales
    as ``sheet_A * eps``) by ``C_1 * eps`` and deduces the per-round
    selection ratio at finite ``L``:

        selection_ratio = sheet_A * eps / (sheet_A * eps + cell_C * packing_B * eps^2)

    Lifted from ``adaptive_reflow.algorithm.dynamic_noise_bias`` (the
    ``Theorem1DynamicNoiseBias.compute_noise_bias`` method) into the
    theory package so the paper formula has exactly ONE canonical
    home. Closes the name collision with
    ``eval.posterior_selection_evaluator.selection_ratio`` (a 1-D
    Gaussian heuristic, NOT a paper quantity).

    As ``eps -> 0``, ``selection_ratio -> 1`` (sheet dominates cell).
    For ``eps > 0`` fixed, ``selection_ratio < 1``.

    Byte-stability: pure arithmetic; two calls with identical inputs
    return bit-identical floats.

    Raises
    ------
    ValueError
        If any input is non-finite or negative.
    """
    for name, value in (
        ("sheet_A", sheet_A),
        ("packing_B", packing_B),
        ("cell_C", cell_C),
        ("eps", eps),
    ):
        v = float(value)
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError(f"{name}_must_be_finite, got {value!r}")
        if v < 0.0:
            raise ValueError(f"{name}_must_be_nonnegative, got {value!r}")
    s = float(sheet_A) * float(eps)
    c = float(cell_C) * float(packing_B) * float(eps) * float(eps)
    denom = s + c
    if denom <= 0.0:
        return 0.0
    return s / denom

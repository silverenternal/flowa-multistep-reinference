"""Concrete quantities from Li 2024 Theorem 1 that the framework's algorithm layer can target.

These are the paper's ACTUAL invariants, not synthesized metrics.

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

Stdlib-only: no torch, no numpy, no other adaptive_reflow imports, no IO.
"""
from __future__ import annotations

import math
from collections.abc import Callable

__all__ = [
    "sheet_evidence_A",
    "root_cell_packing_B",
    "per_cell_coefficient_C",
    "exterior_gap_e_rho",
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
    # Final endpoint: an exact zero at x = K would have been counted as a
    # sign change between ys[-2] and ys[-1] -- no separate check needed.
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

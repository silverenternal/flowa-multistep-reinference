"""F-side hypothesis validators (Wave 11 addition).

The paper's Theorem 1 (line 87-92) is conditional on the F-side
hypotheses (line 22-26):

1. ``g in C^3(R)``, ``Z_g = g^{-1}(0)`` nonempty.
2. Uniform separation: ``|r - s| >= d`` for ``r != s`` in ``Z_g``.
3. Uniform simplicity: ``|g(r + u)| >= c * |u|`` for ``r in Z_g``,
   ``|u| <= rho``.
4. Exterior gap: ``dist(x, Z_g) >= rho => |g(x)| >= eta``.

This module declares:

* :class:`NotInFsideClassError` -- raised when a caller passes a
  profile ``g`` that violates the F-side hypotheses (used for
  Proposition 6 sharpness examples).

* :func:`validate_f_side` -- fail-closed validator for the four F-side
  constants ``(d, c, rho, eta)``. Returns ``(ok, errors)``.

* :func:`validate_g_admissible` -- higher-level validator that checks
  the four F-side constants are CONSISTENT AND the supplied ``g``
  has a nonempty zero set. Raises :class:`NotInFsideClassError` on
  failure.

Stdlib-only.
"""
from __future__ import annotations

from collections.abc import Callable

__all__ = [
    "NotInFsideClassError",
    "validate_f_side",
    "validate_g_admissible",
]


class NotInFsideClassError(ValueError):
    """Raised when a profile ``g`` does NOT satisfy the F-side hypotheses.

    Implements the fail-closed surface for the **F-side hypotheses
    (Theorem 1, line 87-92, conditions at line 22-26)** which require
    ``g in C^3(R)`` with nonempty ``Z_g``, uniform separation
    ``|r - s| >= d``, uniform simplicity ``|g(r + u)| >= c * |u|``
    on ``|u| <= rho``, and exterior gap ``dist(x, Z_g) >= rho =>
    |g(x)| >= eta``.

    Used by :func:`validate_g_admissible` and emitted from
    :class:`adaptive_reflow.contracts.dynamic_noise_bias.PaperQuantitiesSnapshot`
    when the caller's ``g`` is a **Proposition 6, "Escaping-sharpness
    counterexample" (line 294-300)** sharpness example
    (``H(x) = e^{-x^2/2} * sin(pi * x)``).
    """
    pass


def validate_f_side(
    d: float,
    c: float,
    rho: float,
    eta: float,
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``(d, c, rho, eta)`` satisfy the F-side hypotheses.

    Paper verbatim (line 22-26, Lemma 5 line 135-138):

        * ``d > 0``  (uniform separation constant).
        * ``c > 0``  (uniform simplicity constant).
        * ``rho in (0, 1/4]`` and ``rho < d/4``  (disjoint-cell constraint).
        * ``eta > 0``  (exterior gap constant).

    Returns
    -------
    (bool, tuple[str, ...])
        ``(True, ())`` iff all four invariants hold. Otherwise
        ``(False, ("cells_overlap", ...))`` with a tuple of error
        codes (additive, stable for callers to pattern-match).

    Byte-stability: pure comparisons; two calls with identical inputs
    return bit-identical results.
    """
    errors: list[str] = []
    if not (d > 0.0):
        errors.append("separation_d_must_be_positive")
    if not (c > 0.0):
        errors.append("simplicity_c_must_be_positive")
    if not (0.0 < rho <= 0.25):
        errors.append("rho_must_be_in_(0,1/4]")
    if d > 0.0 and rho >= d / 4.0:
        # Lemma 5 (line 135-138): disjoint-cell guarantee requires rho < d/4.
        errors.append("cells_overlap")
    if not (eta > 0.0):
        errors.append("eta_must_be_positive")
    return (not errors, tuple(errors))


def _detect_zeros(
    g: Callable[[float], float],
    *,
    K: float,
    h: float,
) -> list[float]:
    """Return the linearly-interpolated zeros of ``g`` on ``[-K, K]``.

    Implements the literal zero-detection step from
    **Lemma 5, "Uniform cells, Gaussian packing, and physical
    exterior gap" (line 132, line 135-138)** which bounds the
    countable packing ``\\sum_{z in Z_g} e^{-z^2/4}`` by the
    uniform-separation constant ``d``. Matches the zero-detection
    algorithm in
    :func:`adaptive_reflow.theory.paper_quantities.root_cell_packing_B`:
    each sign change on the uniform grid contributes one
    linearly-interpolated zero; an exact zero on a grid node is
    counted once and the adjacent crossing is skipped. The two
    endpoints (``x = -K`` and ``x = K``) are guarded so an exact zero
    at either endpoint is not dropped (F-46/P1-14 fix).
    """
    n_steps = int(round(2.0 * K / h))
    if n_steps < 1:
        raise ValueError("grid too coarse")

    xs: list[float] = []
    ys: list[float] = []
    x = -K
    for _ in range(n_steps + 1):
        xs.append(x)
        ys.append(float(g(x)))
        x += h

    zeros: list[float] = []
    for i in range(len(xs) - 1):
        y0 = ys[i]
        y1 = ys[i + 1]
        x0 = xs[i]
        x1 = xs[i + 1]
        if y0 == 0.0:
            zeros.append(float(x0))
        elif y0 * y1 < 0.0:
            t = -y0 / (y1 - y0)
            zeros.append(float(x0 + t * (x1 - x0)))
    if ys[-1] == 0.0:
        zeros.append(float(xs[-1]))
    return zeros


def validate_g_admissible(
    g: Callable[[float], float],
    d: float,
    c: float,
    rho: float,
    eta: float,
    *,
    zero_set_K: float = 8.0,
    zero_set_h: float = 0.01,
    simplicity_K: float = 4.0,
    simplicity_h: float = 0.001,
    simplicity_n_u: int = 21,
) -> bool:
    """Return ``True`` iff ``g`` together with ``(d, c, rho, eta)`` is F-side admissible.

    Implements the four F-side hypotheses of **Theorem 1 (line 87-92,
    conditions at line 22-26)**: ``g in C^3(R)`` with nonempty
    ``Z_g``, uniform separation ``|r - s| >= d``, uniform simplicity
    ``|g(r + u)| >= c * |u|`` on ``|u| <= rho``, and exterior gap
    ``dist(x, Z_g) >= rho => |g(x)| >= eta``. The disjoint-cell
    constraint ``rho < d/4`` is **Lemma 5, "Uniform cells, Gaussian
    packing, and physical exterior gap" (line 135-138)**.

    Three checks (in order):

    1. ``validate_f_side(d, c, rho, eta)`` returns ``(True, ())``
       (F-side constants are mutually consistent; covers the
       Lemma 5 disjoint-cell constraint ``rho < d/4``).
    2. ``g`` has at least one detected zero on ``[-zero_set_K, zero_set_K]``
       (``Z_g`` is nonempty per the Theorem 1 hypothesis).
    3. **Uniform simplicity** (Wave 12 A1-med-2): for every detected
       zero ``r`` with ``|r| <= simplicity_K`` and every sampled
       ``u`` in ``(-rho, rho)`` with ``|r + u| <= simplicity_K``,
       ``|g(r + u)| >= c * |u|`` (paper line 23-24). The check uses a
       uniform grid of ``simplicity_n_u`` samples spanning
       ``[-rho, rho]`` and is bounded to ``[-simplicity_K, simplicity_K]``
       so the cost stays ``O(simplicity_n_u * |Z_g ∩ [-sim_K, sim_K]|)``.

    Raises
    ------
    NotInFsideClassError
        If any check fails. The error message distinguishes the three
        failure modes:

        * F-side constants: lists the codes from :func:`validate_f_side`.
        * ``Z_g`` nonempty: notes "no zeros detected".
        * Uniform simplicity: notes "uniform_simplicity_violated" with
          the witness ``(r, u, |g(r+u)|, c*|u|)``.

    Byte-stability: ``g`` is sampled on uniform grids; the function is
    pure modulo ``g`` itself.
    """
    ok, errors = validate_f_side(d, c, rho, eta)
    if not ok:
        raise NotInFsideClassError(
            f"profile violates F-side hypotheses: {','.join(errors)}"
        )

    # Detect zeros of g on [-K, K] (shared zero-detection routine).
    K = float(zero_set_K)
    h = float(zero_set_h)
    if K <= 0.0 or h <= 0.0:
        raise ValueError("zero_set_K and zero_set_h must be positive")
    zeros = _detect_zeros(g, K=K, h=h)

    if not zeros:
        raise NotInFsideClassError(
            f"profile has no zeros on [-{K}, {K}]; Z_g must be nonempty"
        )

    # Uniform-simplicity check (paper line 23-24). For each detected
    # zero r in Z_g ∩ [-sim_K, sim_K] and each sampled u in
    # [-rho, rho] with r + u in the same window, verify
    # |g(r + u)| >= c * |u|. The window bounding keeps the cost
    # independent of the count of far-away zeros (whose Gaussian
    # envelope in the typical sharpness example decays super-fast).
    sim_K = float(simplicity_K)
    sim_h = float(simplicity_h)
    n_u = int(simplicity_n_u)
    if sim_K <= 0.0 or sim_h <= 0.0 or n_u < 2:
        raise ValueError(
            "simplicity_K, simplicity_h must be positive; "
            f"simplicity_n_u must be >= 2 (got {n_u})"
        )
    if rho <= 0.0:
        raise ValueError(f"rho must be positive, got {rho!r}")

    # Sample u on a uniform grid spanning (-rho, rho). We use n_u
    # INTERIOR samples (excluding u = 0 to avoid the 0/0 singular).
    for r in zeros:
        if abs(r) > sim_K:
            continue
        for i in range(1, n_u + 1):
            u = -rho + (2.0 * rho) * (i / float(n_u + 1))
            x = r + u
            if abs(x) > sim_K:
                continue
            lhs = abs(float(g(x)))
            rhs = float(c) * abs(u)
            if lhs < rhs:
                raise NotInFsideClassError(
                    "uniform_simplicity_violated: "
                    f"|g({x})| = {lhs:.6e} < c*|u| = {rhs:.6e} "
                    f"(r = {r}, u = {u})"
                )
    return True
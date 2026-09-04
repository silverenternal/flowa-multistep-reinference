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

    Used by :func:`validate_g_admissible` and emitted from
    :class:`adaptive_reflow.contracts.dynamic_noise_bias.PaperQuantitiesSnapshot`
    when the caller's ``g`` is a Proposition 6 sharpness example
    (e.g. ``H(x) = e^{-x^2/2} * sin(pi * x)``).
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


def validate_g_admissible(
    g: Callable[[float], float],
    d: float,
    c: float,
    rho: float,
    eta: float,
    *,
    zero_set_K: float = 8.0,
    zero_set_h: float = 0.01,
) -> bool:
    """Return ``True`` iff ``g`` together with ``(d, c, rho, eta)`` is F-side admissible.

    Two checks:

    1. ``validate_f_side(d, c, rho, eta)`` returns ``(True, ())``
       (F-side constants are mutually consistent).
    2. ``g`` has at least one detected zero on ``[-zero_set_K, zero_set_K]``
       (``Z_g`` is nonempty per the Theorem 1 hypothesis).

    Raises
    ------
    NotInFsideClassError
        If either check fails. For the F-side constants check the
        message lists the specific codes from :func:`validate_f_side`;
        for the ``Z_g`` check the message notes "no zeros detected".

    Byte-stability: ``g`` is sampled on a uniform grid; the function
    is pure modulo ``g`` itself.
    """
    ok, errors = validate_f_side(d, c, rho, eta)
    if not ok:
        raise NotInFsideClassError(
            f"profile violates F-side hypotheses: {','.join(errors)}"
        )

    # Detect at least one zero of g on [-K, K].
    K = float(zero_set_K)
    h = float(zero_set_h)
    if K <= 0.0 or h <= 0.0:
        raise ValueError("zero_set_K and zero_set_h must be positive")
    n_steps = int(round(2.0 * K / h))
    if n_steps < 1:
        raise ValueError("grid too coarse")

    x = -K
    prev = float(g(x))
    found_zero = prev == 0.0
    for _ in range(n_steps):
        x_next = x + h
        cur = float(g(x_next))
        # Sign change OR exact zero at either endpoint.
        if prev == 0.0 or cur == 0.0 or (prev * cur) < 0.0:
            found_zero = True
            break
        prev = cur
        x = x_next

    if not found_zero:
        raise NotInFsideClassError(
            f"profile has no zeros on [-{K}, {K}]; Z_g must be nonempty"
        )
    return True
"""F-side hypothesis validator (Wave 12 A1-med-1).

The JMAA paper's Theorem 1 (line 87-92) is conditional on the F-side
hypotheses (line 22-26):

1. ``g in C^3(R)``, ``Z_g = g^{-1}(0)`` nonempty.
2. Uniform separation: ``|r - s| >= d`` for ``r != s`` in ``Z_g``.
3. Uniform simplicity: ``|g(r + u)| >= c * |u|`` for ``r in Z_g``,
   ``|u| <= rho``.
4. Exterior gap: ``dist(x, Z_g) >= rho => |g(x)| >= eta``.

Lemma 5 (line 135-138) further requires ``rho < d/4`` for the
disjoint-cell guarantee of the sheet tube.

This module exposes:

* :func:`validate_f_side` -- fail-closed validator that returns
  ``(True, ())`` iff ``(d, c, rho, eta)`` are mutually consistent for
  the F-side hypothesis set:

      * ``rho < d/4``  (Lemma 5 disjoint-cell constraint).
      * ``rho <= 1/4``  (cell radius upper bound; see also Lemma 3 setup).
      * ``c > 0``  (uniform simplicity constant).
      * ``eta > 0``  (exterior gap constant).

  Returns ``(False, (code, ...))`` with one or more additive error
  codes:

      * ``"rho_must_be_lt_d_over_4"`` -- ``rho >= d/4`` (or ``d <= 0``).
      * ``"rho_must_be_le_1_over_4"`` -- ``rho > 1/4``.
      * ``"c_must_be_positive"`` -- ``c <= 0``.
      * ``"eta_must_be_positive"`` -- ``eta <= 0``.

  The codes are stable for callers to pattern-match and additive
  (multiple violations accumulate into a single tuple).

Note:
    This is a sibling of :mod:`adaptive_reflow.theory.validation` (which
    provides ``validate_f_side`` and ``validate_g_admissible`` for the
    Wave 11 framework). The two functions coexist: the Wave 11 validator
    in ``validation`` returns codes keyed off the framework's
    ``separation_d_must_be_positive`` / ``simplicity_c_must_be_positive``
    naming, while this module's ``validate_f_side`` uses the
    paper-symbol-friendly names (``rho``, ``c``) from the audit
    acceptance criteria.

Stdlib-only.
"""
from __future__ import annotations

__all__ = ["validate_f_side"]


def validate_f_side(
    d: float,
    c: float,
    rho: float,
    eta: float,
) -> tuple[bool, tuple[str, ...]]:
    """Return ``(True, ())`` iff ``(d, c, rho, eta)`` are F-side-consistent.

    Paper verbatim (line 22-26, Lemma 5 line 135-138):

        * ``d > 0``  (uniform separation constant).
        * ``c > 0``  (uniform simplicity constant).
        * ``rho < d/4``  (disjoint-cell constraint, Lemma 5).
        * ``rho <= 1/4``  (cell radius upper bound).
        * ``eta > 0``  (exterior gap constant).

    Implementation notes:

        * ``rho < d/4`` is the Lemma 5 strict disjoint-cell constraint.
          When ``d <= 0`` the right-hand side is non-positive and any
          positive ``rho`` violates the strict inequality, so the
          ``"rho_must_be_lt_d_over_4"`` code is also emitted.
        * ``rho <= 1/4`` is the cell-radius upper bound. A ``rho`` of
          exactly ``1/4`` is admissible.
        * Errors are additive: if multiple constraints fail, multiple
          codes appear in the tuple.

    Returns
    -------
    (bool, tuple[str, ...])
        ``(True, ())`` iff all four invariants hold. Otherwise
        ``(False, (code, ...))`` with a tuple of error codes (additive,
        stable for callers to pattern-match).

    Byte-stability: pure comparisons; two calls with identical inputs
    return bit-identical results.
    """
    errors: list[str] = []
    # Lemma 5 disjoint-cell constraint. When d <= 0 the inequality
    # d/4 <= 0 forces rho < non-positive, so any positive rho fails.
    if d <= 0.0 or rho >= d / 4.0:
        errors.append("rho_must_be_lt_d_over_4")
    # Cell-radius upper bound (see Lemma 3 setup).
    if rho > 0.25:
        errors.append("rho_must_be_le_1_over_4")
    # Uniform-simplicity constant.
    if c <= 0.0:
        errors.append("c_must_be_positive")
    # Exterior-gap constant.
    if eta <= 0.0:
        errors.append("eta_must_be_positive")
    return (not errors, tuple(errors))

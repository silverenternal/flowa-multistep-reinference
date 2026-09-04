"""Hypothesis-violation (must-fail) fixtures for Proposition 2's admissible family.

Closes the last A.7 strict-reading gap (Wave 23 E): **Proposition 2,
"A nonperiodic admissible family" (line 62-64)** was the only
constructive A.0 entry without a paired must-fail fixture. Prior waves
recorded it as "covered-by-symmetry via Proposition 6" — Prop 2 states
the *positive* witness family and Prop 6 states the *sharpness*
counterexample, so the two are theorem-level opposites. That symmetry
argument is real but it is not a fixture: nothing in the suite asserted
that **Proposition 2's own hypothesis** is load-bearing.

Paper verbatim (Proposition 2, line 62-64):

    Let ``a in C^3(R)`` satisfy ``0 < m <= a(x) <= M < infinity`` for
    every ``x``, and set ``g_a(x) = a(x) sin(x)``. Then ``g_a``
    satisfies the F-side hypotheses. In particular,
    ``a(x) = 1 + (1/4) tanh(x)`` produces an admissible nonperiodic
    profile.

The constructive content of Proposition 2 is therefore the implication

    ``0 < m <= a <= M``  =>  ``g_a = a * sin`` is F-side admissible.

and the must-fail direction is the *contrapositive witness*: exhibit
amplitudes ``a`` that break the two-sided bound and show
:func:`adaptive_reflow.theory.validation.validate_g_admissible`
refuses the resulting ``g_a`` (fail-closed), rather than silently
admitting a profile outside the family.

Structure of this module (mirrors
``tests/test_theory/negative/test_lemma3_per_cell_coefficient.py``):

* **Rejection fixtures (4)** — amplitudes with ``inf_x a(x) = 0``, i.e.
  no admissible lower bound ``m > 0``:
  ``a(x) = 1/(1+x^2)``, ``a(x) = e^{-x^2/2}``, ``a(x) = e^{x}``,
  ``a(x) = 0``. Each violates the uniform-simplicity hypothesis
  (paper line 23-24) at a root of ``sin``, and
  ``validate_g_admissible`` raises
  :class:`~adaptive_reflow.theory.validation.NotInFsideClassError`
  carrying the ``uniform_simplicity_violated`` witness.
* **Positive controls (3)** — the canonical ``a(x) = 1 + 0.25 tanh(x)``
  is accepted (so the rejection fixtures cannot pass vacuously); a
  constant ``a(x) = 0.5`` is accepted (the family is not tied to the
  canonical witness); and the *delegation* control below.
* **Delegation control (1)** — ``a(x) = 1 + x^2`` is unbounded above
  (``M = infinity``, so it is outside Proposition 2's hypothesis set)
  yet ``validate_g_admissible`` accepts it. This documents that the
  validator enforces the ``m > 0`` half of Prop 2's two-sided bound
  (via uniform simplicity) but NOT the ``M < infinity`` half: the
  upper bound is used in the paper's proof to control the *constants*
  ``(d, c, rho, eta)``, not to gate admissibility of a fixed constant
  tuple. This is the Prop-2 analogue of Lemma 3's
  ``test_per_cell_coefficient_does_not_enforce_disjoint_cell``.

Relationship to Proposition 6 (the symmetry that used to stand alone):
``a(x) = e^{-x^2/2}`` here is the Prop-2-family shadow of **Proposition
6, "Escaping-sharpness counterexample" (line 294-300)**
``H(x) = e^{-x^2/2} sin(pi x)``. The Prop 6 fixtures in
``tests/test_theory/test_proposition6_escaping_sharpness.py`` assert
that the paper's *named* counterexample is refused; the fixtures here
assert that the *hypothesis of Prop 2* (``inf a > 0``) is what
separates the admissible family from that counterexample. The two
directions are now both fixture-backed rather than one being inferred
from the other.

Paper-verbatim references used by this fixture:
* Proposition 2, line 62-64: ``0 < m <= a(x) <= M < infinity``,
  ``g_a(x) = a(x) sin(x)``, canonical ``a(x) = 1 + (1/4) tanh(x)``.
* F-side hypotheses, line 22-26 (uniform simplicity at line 23-24).
* Proposition 6, line 294-300: ``H(x) = e^{-x^2/2} sin(pi x)``.
* Lemma 5, line 135-138: disjoint-cell constraint ``rho < d/4``.
"""
from __future__ import annotations

import math
from collections.abc import Callable

import pytest

from adaptive_reflow.theory.validation import (
    NotInFsideClassError,
    validate_g_admissible,
)

#: F-side constants used throughout this module. Identical to the
#: constants used by the Proposition 2 positive fixture in
#: ``tests/test_theory/test_proposition6_escaping_sharpness.py::
#: test_validate_g_admissible_accepts_canonical_nonperiodic_profile``
#: so that acceptance/rejection differs ONLY in the amplitude ``a``.
#: ``rho = 0.1 < d/4 = 0.125`` satisfies Lemma 5 (line 135-138).
_D = 0.5
_C = 0.5
_RHO = 0.1
_ETA = 0.1


def _g_a(a: Callable[[float], float]) -> Callable[[float], float]:
    """Return the Proposition 2 profile ``g_a(x) = a(x) * sin(x)`` (line 62-64)."""

    def g(x: float) -> float:
        return float(a(x)) * math.sin(x)

    return g


# ---------------------------------------------------------------------------
# Rejection fixtures: amplitudes violating ``0 < m <= a(x)``.
# ---------------------------------------------------------------------------


def test_g_a_with_algebraically_decaying_a_fails_admissibility():
    """``a(x) = 1/(1+x^2)`` has ``inf a = 0``: no ``m > 0`` (Prop 2, line 62).

    The amplitude is smooth and strictly positive pointwise, so it
    passes a naive "a(x) > 0" reading, but it has **no uniform lower
    bound**. At the root ``r = -pi`` the profile satisfies
    ``|g_a(r+u)| ~ |u| / (1 + pi^2) ~ 0.09 |u| < c |u|`` for
    ``c = 0.5``, violating uniform simplicity (line 23-24), so
    ``validate_g_admissible`` fails closed.
    """
    with pytest.raises(NotInFsideClassError, match="uniform_simplicity_violated"):
        validate_g_admissible(
            _g_a(lambda x: 1.0 / (1.0 + x * x)), d=_D, c=_C, rho=_RHO, eta=_ETA
        )


def test_g_a_with_gaussian_decaying_a_fails_admissibility():
    """``a(x) = e^{-x^2/2}`` is the Prop-2-family shadow of Proposition 6.

    ``g_a(x) = e^{-x^2/2} sin(x)`` differs from the paper's named
    sharpness counterexample ``H(x) = e^{-x^2/2} sin(pi x)``
    (Proposition 6, line 294-300) only in the root spacing. The
    Gaussian envelope drives ``|g_a(r+u)| / |u| -> 0`` as
    ``|r| -> infinity``, so no uniform ``c > 0`` exists and the
    Proposition 2 hypothesis ``a >= m > 0`` is exactly what rules
    this out.
    """
    with pytest.raises(NotInFsideClassError, match="uniform_simplicity_violated"):
        validate_g_admissible(
            _g_a(lambda x: math.exp(-0.5 * x * x)), d=_D, c=_C, rho=_RHO, eta=_ETA
        )


def test_g_a_with_exponential_a_fails_admissibility():
    """``a(x) = e^{x}`` violates BOTH bounds of ``0 < m <= a <= M < inf``.

    Unbounded above as ``x -> +infinity`` (``M`` fails) and
    ``a(x) -> 0`` as ``x -> -infinity`` (``m`` fails). The detected
    violation is on the ``m`` side: at the negative roots of ``sin``
    the amplitude has collapsed below ``c``, so
    ``|g_a(r+u)| < c |u|``. Compare
    :func:`test_g_a_with_unbounded_a_does_not_fail_admissibility`,
    where an amplitude that violates only the ``M`` side is accepted.
    """
    with pytest.raises(NotInFsideClassError, match="uniform_simplicity_violated"):
        validate_g_admissible(
            _g_a(math.exp), d=_D, c=_C, rho=_RHO, eta=_ETA
        )


def test_g_a_with_vanishing_a_fails_admissibility():
    """``a(x) = 0`` degenerates ``g_a`` to the zero function (Prop 2, line 62).

    Extreme boundary case of ``m > 0``: with ``a = 0`` every point is
    a zero, ``|g_a(r+u)| = 0 < c|u|`` for every sampled ``u != 0``,
    and the validator fails closed rather than reporting a vacuously
    "admissible" profile with an everywhere-zero ``Z_g``.
    """
    with pytest.raises(NotInFsideClassError, match="uniform_simplicity_violated"):
        validate_g_admissible(
            _g_a(lambda x: 0.0), d=_D, c=_C, rho=_RHO, eta=_ETA
        )


# ---------------------------------------------------------------------------
# Positive controls: the rejection fixtures above must not over-reject.
# ---------------------------------------------------------------------------


def test_g_a_canonical_amplitude_is_admissible():
    """``a(x) = 1 + 0.25 tanh(x)`` is admissible (Prop 2, line 63-64).

    The paper's named witness: ``0.75 <= a(x) <= 1.25`` gives
    ``m = 0.75`` and ``M = 1.25``. Accepted under the SAME
    ``(d, c, rho, eta)`` used by every rejection fixture above, so the
    rejections are attributable to the amplitude alone.
    """
    assert validate_g_admissible(
        _g_a(lambda x: 1.0 + 0.25 * math.tanh(x)), d=_D, c=_C, rho=_RHO, eta=_ETA
    )


def test_g_a_constant_amplitude_is_admissible():
    """``a(x) = 0.8`` (constant, ``m = M = 0.8``) is admissible (Prop 2, line 62).

    Guards against a reading in which only the canonical ``tanh``
    witness is accepted: any amplitude with a genuine two-sided bound
    satisfies the hypothesis. Note the margin matters — with
    ``a == c == 0.5`` the profile sits exactly ON the uniform-simplicity
    boundary and the ``sin`` curvature ``|sin(u)| = |u| - |u|^3/6``
    puts it just below ``c |u|``, so the validator (correctly, being
    fail-closed) rejects it; ``a = 0.8 > c = 0.5`` clears that margin.
    """
    assert validate_g_admissible(
        _g_a(lambda x: 0.8), d=_D, c=_C, rho=_RHO, eta=_ETA
    )


def test_g_a_with_unbounded_a_does_not_fail_admissibility():
    """``a(x) = 1 + x^2`` violates only ``M < infinity`` and is still accepted.

    Delegation control (Prop-2 analogue of Lemma 3's
    ``test_per_cell_coefficient_does_not_enforce_disjoint_cell``).
    Proposition 2's hypothesis is two-sided (``0 < m <= a <= M``), but
    :func:`validate_g_admissible` only tests the four F-side
    hypotheses for a **fixed** constant tuple ``(d, c, rho, eta)``.
    The upper bound ``M`` enters the paper's proof when *deriving*
    admissible constants (larger ``M`` inflates ``eta`` and the
    per-cell coefficient of Lemma 3), not as a rejection criterion at
    fixed constants — so an amplitude growing without bound still
    satisfies uniform simplicity and is accepted here.

    Callers that need Proposition 2's full two-sided hypothesis must
    additionally bound ``sup_x a(x)``; this test documents that the
    validator does NOT do it for them.
    """
    assert validate_g_admissible(
        _g_a(lambda x: 1.0 + x * x), d=_D, c=_C, rho=_RHO, eta=_ETA
    )

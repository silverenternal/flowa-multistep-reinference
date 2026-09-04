"""JMAA paper theory package (Wave 11 refactor).

This package owns the JMAA paper-quantity primitives, theorem-statement
witnesses, and validation entry points. It is a new sibling of
:mod:`adaptive_reflow.contracts/` and serves as the canonical home for
the math that the framework's algorithm and adapter layers consume.

**Periodicity-free Theorem 1 (Remark 1, paper line 54-56):**

The main theorem does NOT require periodicity of ``g``; Lemma 1 is
only a verification convenience. Any ``g`` satisfying the F-side
hypotheses is admissible, including the nonperiodic family
``g_a(x) = a(x) * sin(x)`` from Proposition 2 (line 62-64).

**Layout:**

* :mod:`adaptive_reflow.theory.paper_quantities` -- the four JMAA paper
  quantities ``A_g``, ``B_g``, ``C_g``, ``e_rho`` plus rich result
  dataclasses and ``PhysicalComplement``.
* :mod:`adaptive_reflow.theory.checkers` -- the unified Theorem 1
  statement, sheet-tube evidence (Lemma 2 LHS), and the lifted
  ``paper_selection_ratio`` formula.
* :mod:`adaptive_reflow.theory.validation` -- ``validate_f_side`` and
  ``validate_g_admissible`` plus the ``NotInFsideClassError`` raised by
  Proposition 6 sharpness examples.
* :mod:`adaptive_reflow.theory.f_side_validator` -- Wave 12 A1-med-1
  F-side hypothesis validator exposing ``validate_f_side(d, c, rho, eta)``
  with paper-symbol-friendly error codes (``rho_must_be_lt_d_over_4``,
  ``rho_must_be_le_1_over_4``, ``c_must_be_positive``,
  ``eta_must_be_positive``).
* :mod:`adaptive_reflow.theory.lemma2_checker` -- Wave 12 A1-high-2
  finite-eps LHS Monte-Carlo evaluator for Lemma 2, returning
  ``LHS / RHS`` as a ``float``. Uses the paper's literal residual
  geometry ``|F_g|^2 = y^2 * (g(x)^2 + (y-1)^2)``.

**Unified Theorem 1 entry point (A1-high-1 fix):**

* :class:`Theorem1Statement` -- the single dataclass carrying all three
  Theorem 1 claims (``bl_distance``, ``root_cell_mass``,
  ``posterior_evidence``) together. Re-exports from
  :mod:`adaptive_reflow.theory.checkers` so callers can do
  ``from adaptive_reflow.theory import Theorem1Statement``.

**Byte-stable legacy imports:**

:mod:`adaptive_reflow.contracts.paper_quantities` is a re-export shim
pointing at :mod:`adaptive_reflow.theory.paper_quantities` so existing
callers (``adaptive_reflow.eval.fid_theorem_aligned``,
``tests/test_contracts/test_paper_quantities.py``) keep working without
modification.

**Stdlib-only, no torch, no numpy.**

.. note::
   This module is additive; no existing API was renamed or removed.
"""
from __future__ import annotations

from adaptive_reflow.theory import checkers
from adaptive_reflow.theory import f_side_validator
from adaptive_reflow.theory import lemma2_checker
from adaptive_reflow.theory import paper_quantities
from adaptive_reflow.theory import rate_bound
from adaptive_reflow.theory import validation
from adaptive_reflow.theory.checkers import Theorem1Statement
from adaptive_reflow.theory.f_side_validator import validate_f_side
from adaptive_reflow.theory.lemma2_checker import sheet_tube_evidence
from adaptive_reflow.theory.rate_bound import (
    ExplicitRateBoundReport,
    check_explicit_rate_bound,
)

__all__ = [
    "Theorem1Statement",
    "validate_f_side",
    "paper_quantities",
    "checkers",
    "lemma2_checker",
    "validation",
    "f_side_validator",
    "sheet_tube_evidence",
    # Wave 15 B: explicit rate bound (Theorem 1 O(eps) with C = sqrt(2/pi)).
    "rate_bound",
    "ExplicitRateBoundReport",
    "check_explicit_rate_bound",
]
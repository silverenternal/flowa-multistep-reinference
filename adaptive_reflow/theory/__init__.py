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
from adaptive_reflow.theory import paper_quantities
from adaptive_reflow.theory import validation

__all__ = [
    "paper_quantities",
    "checkers",
    "validation",
]
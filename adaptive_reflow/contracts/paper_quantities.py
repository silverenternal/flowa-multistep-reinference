"""Re-export shim for the JMAA paper-quantity primitives.

Wave 11 (JMAA refactor): the canonical home of the four paper
quantities ``A_g, B_g, C_g, e_rho`` has moved to
:mod:`adaptive_reflow.theory.paper_quantities`. This module is a
byte-stable re-export shim so existing callers
(``adaptive_reflow.eval.fid_theorem_aligned``,
``tests/test_contracts/test_paper_quantities.py``) keep working
without modification.

**Theorem 1 is periodicity-free (Remark 1, paper line 54-56):**

The main theorem does NOT require periodicity of ``g``; Lemma 1 is
only a verification convenience. Any ``g`` satisfying the F-side
hypotheses is admissible, including the nonperiodic family
``g_a(x) = a(x) * sin(x)`` from Proposition 2 (line 62-64). This
shim re-exports the same set of paper-quantity evaluators regardless
of whether ``g`` is periodic or not.

.. note::
   The new theory-only additions ``PhysicalComplement`` and
   ``paper_selection_ratio`` live in
   :mod:`adaptive_reflow.theory.paper_quantities`; import them from
   there directly. This shim exposes only the legacy
   ``__all__`` surface to keep the
   ``tests/test_contracts/test_paper_quantities.py::test_module_exports``
   test green.

Stdlib-only, no torch, no numpy, no other adaptive_reflow imports.
"""
from __future__ import annotations

from adaptive_reflow.theory.paper_quantities import (  # noqa: F401
    PerCellCoefficientResult,
    RootCellPackingResult,
    SheetEvidenceResult,
    exterior_gap_e_rho,
    per_cell_coefficient_C,
    per_cell_coefficient_with_result,
    root_cell_packing_B,
    root_cell_packing_with_result,
    sheet_evidence_A,
    sheet_evidence_with_result,
)

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
]
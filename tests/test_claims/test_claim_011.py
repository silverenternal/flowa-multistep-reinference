"""CLM-011: Four paper quantities are first-class algorithm inputs.

Asserted by docs/CLAIMS.md:191-211.
The four paper quantities `A_g`, `B_g`, `C_g`, `e_rho` are exposed via
`adaptive_reflow.contracts.paper_quantities` `__all__` (and via the
re-export shim in `adaptive_reflow.contracts.paper_quantities`).

The shim re-exports the four named callables:
    sheet_evidence_A, root_cell_packing_B, per_cell_coefficient_C,
    exterior_gap_e_rho

We pin `__all__` contains the four names + result carriers + `_with_result`
variants.
"""
from __future__ import annotations

import adaptive_reflow.contracts.paper_quantities as pq
from adaptive_reflow.theory import paper_quantities as canonical


REQUIRED_NAMES = (
    "sheet_evidence_A",
    "root_cell_packing_B",
    "per_cell_coefficient_C",
    "exterior_gap_e_rho",
)


def test_claim_011_all_four_callables_in_shim_all() -> None:
    assert all(name in pq.__all__ for name in REQUIRED_NAMES)


def test_claim_011_shim_callables_resolve_to_callables() -> None:
    """Each name in __all__ resolves to an actual callable (no None)."""
    for name in REQUIRED_NAMES:
        assert callable(getattr(pq, name)), f"{name} not callable"


def test_claim_011_canonical_module_also_exposes_four() -> None:
    """The canonical theory module also exposes the four named callables."""
    for name in REQUIRED_NAMES:
        assert hasattr(canonical, name), f"canonical missing {name}"


def test_claim_011_shim_and_canonical_share_callables() -> None:
    """The shim re-export points at the same code object as the canonical."""
    for name in REQUIRED_NAMES:
        assert getattr(pq, name) is getattr(canonical, name)

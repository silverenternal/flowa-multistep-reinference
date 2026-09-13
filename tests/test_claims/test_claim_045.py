"""CLM-045: `e_rho / 4` factor carries an inline CLM-042 derivation note.

Asserted by docs/CLAIMS.md:1616-1655.
The `BoundedMergeOperator.merge` floor computation and
`CodimensionSheetScheduler.inject_noise` both reference an inline
CLM-042 derivation comment explaining the `e_rho / 4` conservative
tightening factor (paper Lemma 4 / line 111-114).

We pin:
    1. `BoundedMergeOperator.merge` carries a `CLM-042 derivation` comment.
    2. The comment references `e_rho / 4`.
    3. `CodimensionSheetScheduler.inject_noise` ALSO carries a
       corresponding CLM-042 derivation note.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MERGE_OP = ROOT / "adaptive_reflow" / "algorithm" / "merge_operator.py"
SCHEDULER_CORE = ROOT / "adaptive_reflow" / "algorithm" / "scheduler" / "_core.py"


def test_claim_045_merge_operator_has_clm_042_comment() -> None:
    text = MERGE_OP.read_text()
    assert "CLM-042 derivation" in text, (
        "merge_operator.py must contain a 'CLM-042 derivation' comment"
    )


def test_claim_045_merge_operator_references_e_rho_over_4() -> None:
    text = MERGE_OP.read_text()
    assert "e_rho / 4" in text, "merge_operator.py must reference 'e_rho / 4'"


def test_claim_045_scheduler_core_has_corresponding_note() -> None:
    """CodimensionSheetScheduler carries the matching CLM-042 derivation note."""
    text = SCHEDULER_CORE.read_text()
    assert "CLM-042" in text, "scheduler/_core.py must reference 'CLM-042'"
    assert "e_rho / 4" in text, "scheduler/_core.py must reference 'e_rho / 4'"

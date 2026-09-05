"""CLM-025: BoundedMergeOperator fails closed on `cap < floor` (post-clip).

Asserted by docs/CLAIMS.md:564-591.
`BoundedMergeOperator.merge` emits the canonical `_ERR_CAP_BELOW_FLOOR`
audit code when the post-clip envelope satisfies `cap_f < floor_f`.
Per the P0-3 (F-18) fix, the operator returns `floor_f` (does NOT
raise) so the runner's loop survives a degenerate envelope; the audit
code is the canonical reader-side signal.

We pin:
    1. With cap < floor (post-clip), the merge emits the
       `_ERR_CAP_BELOW_FLOOR` audit code (or prefix thereof).
    2. The merge returns the floor value rather than raising.
"""
from __future__ import annotations

from adaptive_reflow.algorithm.merge_operator import (
    BoundedMergeOperator,
    _ERR_CAP_BELOW_FLOOR,
)


def test_claim_025_emits_cap_below_floor_audit_when_envelope_inverted() -> None:
    """cap=0.1, floor=0.9 (clearly inverted) emits the audit code."""
    op = BoundedMergeOperator()
    codes: list[str] = []
    result = op.merge(
        prev=0.5, dynamic=0.5,
        cap=0.1, floor=0.9,
        delta_cap_up=1.0, delta_cap_down=1.0,
        audit_codes=codes,
    )
    assert any(c.startswith(_ERR_CAP_BELOW_FLOOR) for c in codes), (
        f"missing audit prefix {_ERR_CAP_BELOW_FLOOR!r}; got codes={codes!r}"
    )
    # P0-3 (F-18): merge returns the floor (fail-closed) rather than raise.
    assert result == 0.9, f"expected merge to return floor 0.9, got {result!r}"

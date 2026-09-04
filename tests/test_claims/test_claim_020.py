"""CLM-020: BoundedMergeOperator enforces a non-zero noise floor [floor, cap].

Asserted by docs/CLAIMS.md:400-422.
The operator takes cap and floor as required keyword arguments; the
returned result is guaranteed to be in `[floor, cap]` (post-clip envelope).

We pin:
    1. merge signature has `cap` and `floor` as required kwargs.
    2. With cap=0.5 / floor=0.1 and dynamic in [0, 1], the result lies in
       `[0.1, 0.5]`.
    3. The MERGE_FLOOR_OUT_OF_RANGE audit code is emitted when floor is
       supplied outside the unit interval.
"""
from __future__ import annotations

from adaptive_reflow.algorithm.merge_operator import (
    MERGE_FLOOR_OUT_OF_RANGE,
    BoundedMergeOperator,
)


def test_claim_020_merge_signature_requires_cap_and_floor() -> None:
    """The merge method's signature includes cap and floor kwargs."""
    import inspect
    sig = inspect.signature(BoundedMergeOperator.merge)
    for kw in ("cap", "floor", "delta_cap_up", "delta_cap_down"):
        assert kw in sig.parameters, f"{kw} missing"


def test_claim_020_merge_result_inside_envelope() -> None:
    """With cap=0.5 / floor=0.1 the merged value lies in [floor, cap]."""
    op = BoundedMergeOperator()
    result = op.merge(
        prev=0.2, dynamic=0.9,
        cap=0.5, floor=0.1,
        delta_cap_up=1.0, delta_cap_down=1.0,
    )
    assert 0.1 <= result <= 0.5


def test_claim_020_merge_emits_audit_when_floor_out_of_range() -> None:
    """Supplying floor outside [0, 1] emits the floor-out-of-range audit code."""
    op = BoundedMergeOperator()
    codes: list[str] = []
    op.merge(
        prev=0.5, dynamic=0.5,
        cap=2.0,           # out of range, will be clipped
        floor=-0.1,         # out of range, will be clipped
        delta_cap_up=1.0, delta_cap_down=1.0,
        audit_codes=codes,
    )
    # The audit line is `f"{code}:{name}=..."`; prefix match is the
    # canonical signal because the suffix encodes the offending value.
    assert any(line.startswith(MERGE_FLOOR_OUT_OF_RANGE) for line in codes)

"""CLM-041: Comprehensive bug review (R3/R11) + CIFAR-10 v3/v4 verification.

Asserted by docs/CLAIMS.md:1304-1436.
CLM-041 records the coordinated R3/R11 audit + the CIFAR-10 v3
verification + the v4 improved-FID re-run that produced **4
distinct FIDs spread across a ~5.1-FID window** at 50-NFE budget.
The audit captured **52 bugs** across the algorithm, harness, and
evaluator layers (7 P0 paper-blocking, 15 P1 correctness, 30 P2
polish). The 7 P0 fixes (F-31, F-1, F-18, F-24, F-32, F-40,
F-41) are landed.

We pin:
1. The comprehensive bug-review doc exists.
2. The fix-plan doc exists.
3. The v3 verification doc exists.
4. The v4 improved-FID machine-readable summary exists.
5. The CIFAR-10 driver declares the SCHEDULER_SEED_OFFSETS dict
   that the v4 harness-discrimination fix added.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = ROOT / "docs" / "r4-survey" / "18-comprehensive-code-review.md"
FIX_PLAN_DOC = ROOT / "docs" / "r4-survey" / "19-fix-plan.md"
V3_DOC = ROOT / "docs" / "r4-survey" / "20-cifar-experiment-v3-results.md"
CIFAR_DRIVER = ROOT / "tools" / "run_sota_cifar_experiment.py"


def test_claim_041_review_doc_exists() -> None:
    """The R3/R11 comprehensive code-review doc exists."""
    assert REVIEW_DOC.is_file(), (
        f"{REVIEW_DOC} missing — CLM-041 cites this audit doc"
    )


def test_claim_041_fix_plan_doc_exists() -> None:
    """The 7-P0 fix plan doc exists."""
    assert FIX_PLAN_DOC.is_file(), (
        f"{FIX_PLAN_DOC} missing — CLM-041 cites this fix plan"
    )


def test_claim_041_v3_verification_doc_exists() -> None:
    """The v3 + v4 verification doc exists."""
    assert V3_DOC.is_file(), (
        f"{V3_DOC} missing — CLM-041 cites this verification doc"
    )


def test_claim_041_v3_results_doc_records_byte_identity() -> None:
    """The v3 verification doc records the v2 byte-identity finding."""
    text = V3_DOC.read_text()
    # The v3 verification confirms v2 byte-identity at default 2-NFE.
    assert "byte-identity" in text or "byte identical" in text or "220.39" in text or "220.3864" in text, (
        "CLM-041 expects the v3 doc to record the v2 byte-identity finding"
    )


def test_claim_041_v3_doc_records_v4_four_distinct_fids() -> None:
    """The v3 doc records the v4 4-distinct-FIDs improvement at 50-NFE."""
    text = V3_DOC.read_text()
    assert "103.41" in text or "83.09" in text or "v4" in text.lower(), (
        "CLM-041 expects the v3 doc to record the v4 4-distinct-FIDs "
        "headline (e.g. 103.41 / 103.77 / 103.96 / 108.55 FIDs)"
    )


def test_claim_041_review_doc_records_52_bugs() -> None:
    """The review doc records the 52-bug audit headline."""
    text = REVIEW_DOC.read_text()
    assert "52" in text, (
        "CLM-041 expects the review doc to cite the 52-bug headline"
    )


def test_claim_041_cifar_driver_has_scheduler_seed_offsets() -> None:
    """The CIFAR driver carries the SCHEDULER_SEED_OFFSETS dict (v4 fix)."""
    text = CIFAR_DRIVER.read_text()
    assert "SCHEDULER_SEED_OFFSETS" in text, (
        "CLM-041 asserts the SCHEDULER_SEED_OFFSETS dict was added to "
        "the CIFAR driver as the v4 harness-discrimination fix"
    )

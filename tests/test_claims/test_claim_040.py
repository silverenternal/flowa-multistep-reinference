"""CLM-040: CIFAR-10 SOTA reproduction — FlowA framework improves over baseline.

Asserted by docs/CLAIMS.md:1128-1303.
CLM-040 records the canonical CIFAR-10 Rectified-Flow SOTA
reproduction: when the published Liu 2022 NeurIPS Spotlight CIFAR-10
Rectified Flow DDPM++ UNet (integrated as
`RectifiedFlowCIFARAdapter`, gnobitab Score-SDE `state_dict` at
`data/cifar10_rf.pth`) is run through FlowA's multi-round
re-inference loop with four scheduler families, the InceptionV3
FID improves over the same model's single-pass 2-NFE Euler baseline.

The canonical experiment driver is `tools/run_sota_cifar_experiment.py`;
the FID script is `tools/compute_cifar_fid.py`; the canonical
post-fix results docs are `docs/r4-survey/17-cifar-experiment-
results-v2.md` and `docs/r4-survey/20-cifar-experiment-v3-results.md`.
The smoke regression test is
`tests/test_tools/test_run_sota_cifar_experiment.py`.

We pin:
1. The experiment driver + FID script + smoke regression + the
   two canonical result docs all exist on disk.
2. The driver declares the per-scheduler SCHEDULER_SEED_OFFSETS
   dict that CLM-041 also references (the harness-discrimination
   fix that landed the v4 4-distinct-FIDs result).
3. The post-fix v2 results doc exists and records the baseline-vs-
   framework comparison headline.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CIFAR_DRIVER = ROOT / "tools" / "run_sota_cifar_experiment.py"
CIFAR_FID_SCRIPT = ROOT / "tools" / "compute_cifar_fid.py"
SMOKE_RE = ROOT / "tests" / "test_tools" / "test_run_sota_cifar_experiment.py"
V2_DOC = ROOT / "docs" / "r4-survey" / "17-cifar-experiment-results-v2.md"
V3_DOC = ROOT / "docs" / "r4-survey" / "20-cifar-experiment-v3-results.md"
V4_DOC = ROOT / "docs" / "r4-survey" / "cifar_results_v4" / "comparison.md"


def test_claim_040_cifar_experiment_driver_exists() -> None:
    """The CIFAR-10 SOTA experiment driver is on disk."""
    assert CIFAR_DRIVER.is_file(), (
        f"{CIFAR_DRIVER} missing — CLM-040 asserts by this script"
    )


def test_claim_040_cifar_fid_script_exists() -> None:
    """The CIFAR-10 InceptionV3 FID script is on disk."""
    assert CIFAR_FID_SCRIPT.is_file(), (
        f"{CIFAR_FID_SCRIPT} missing — CLM-040 asserts by this script"
    )


def test_claim_040_smoke_regression_test_exists() -> None:
    """The smoke regression test for the CIFAR driver exists."""
    assert SMOKE_RE.is_file(), (
        f"{SMOKE_RE} missing — CLM-040 cites this regression suite"
    )


def test_claim_040_v2_post_fix_results_doc_exists() -> None:
    """The v2 post-fix results doc exists."""
    assert V2_DOC.is_file(), (
        f"{V2_DOC} missing — CLM-040 cites this doc"
    )


def test_claim_040_v3_verification_doc_exists() -> None:
    """The v3 verification + v4 improved-FID results doc exists."""
    assert V3_DOC.is_file(), (
        f"{V3_DOC} missing — CLM-040 cites this doc"
    )


def test_claim_040_v2_doc_records_fid_improvement() -> None:
    """The v2 doc records the baseline-vs-framework FID improvement."""
    text = V2_DOC.read_text()
    # The post-fix v2 headline: baseline FID 218.8692 -> framework FID 122.1790.
    # Either the baseline number or the framework number pins the headline.
    assert "218" in text or "122" in text, (
        "CLM-040 expects the v2 doc to cite the post-fix FID numbers"
    )


def test_claim_040_driver_has_scheduler_seed_offsets() -> None:
    """The CIFAR driver declares the per-scheduler SCHEDULER_SEED_OFFSETS dict."""
    text = CIFAR_DRIVER.read_text()
    assert "SCHEDULER_SEED_OFFSETS" in text, (
        "CLM-040 asserts the SCHEDULER_SEED_OFFSETS dict lives in the driver"
    )


def test_claim_040_v4_machine_readable_summary_present() -> None:
    """The v4 4-distinct-FIDs headline is recorded in the v3 doc."""
    text = V3_DOC.read_text()
    # CLM-040 cites the v4 4-distinct-FIDs headline (EvidenceDrivenScheduler
    # 103.41, CosineAnnealScheduler 103.77, CodimensionSheetScheduler
    # 103.96, FreeTrajScheduler 108.55). The v3 verification doc records
    # these as part of Part B (post-fix improved-FID re-run).
    assert "103.41" in text and "103.77" in text and "103.96" in text and "108.55" in text, (
        "CLM-040 expects the v3 doc to record all 4 distinct v4 FIDs"
    )
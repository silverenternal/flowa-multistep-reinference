"""Guard the vendored-upstream MD5 table (Wave 262 P2 re-verification).

``tnnls_submission/data_availability.md`` claims the nine reverted files are
bytewise identical to upstream and points at a verification audit.  The audit
lives at ``docs/audit/wave262-p2-verify.md`` and the table at
``tools/check_vendored_md5.py``; this test keeps the two from drifting.

Skipped when the vendored trees are absent (e.g. a source-only checkout).
"""
from __future__ import annotations

import pytest

from tools.check_vendored_md5 import EXPECTED, REPO_ROOT, check

pytestmark = pytest.mark.skipif(
    not (REPO_ROOT / EXPECTED[0][0]).is_file(),
    reason="vendored upstream trees are not present in this checkout",
)


def test_all_recorded_vendored_md5s_match() -> None:
    missing, mismatched = check()
    assert missing == [], f"missing vendored files: {missing}"
    assert mismatched == [], f"vendored files drifted: {mismatched}"


def test_table_covers_the_nine_reverted_files() -> None:
    reverted = {
        "data/FlowMol3/repo/flowmol/analysis/molecule_builder.py",
        "data/FlowMol3/repo/flowmol/models/flowmol.py",
        "data/FlowMol3/repo/flowmol/utils/ctmc_utils.py",
        "data/FlowMol3/repo/flowmol/analysis/metrics.py",
        "data/lineageflow_upstream/evaluation/evaluate_all.py",
        "data/lineageflow_upstream/evaluation/foldability_omegafold.py",
        "data/lineageflow_upstream/evaluation/novelty_mmseqs2.py",
        "data/lineageflow_upstream/evaluation/run_foldability.py",
        "data/lineageflow_upstream/evaluation/self_consistency_esmif.py",
    }
    assert reverted <= {rel for rel, _, _ in EXPECTED}

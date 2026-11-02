"""Protect fixed-study inference from partial runs and invalid cost grids."""

import json

import pytest

from tools.report_cifar_candidate_20261103 import analyze as holdout_analyze
from tools.report_cifar_study_20261103 import analyze, exact_signflip_three, log_area


def test_exact_three_pair_resolution_and_grid_validation():
    assert exact_signflip_three([1.0, 2.0, 3.0]) == 0.25
    assert exact_signflip_three([0.0, 0.0, 0.0]) == 1
    with pytest.raises(ValueError):
        exact_signflip_three([1.0, 2.0])
    for costs in [[0.0, 1.0], [-1.0, 2.0], [1.0, float("inf")]]:
        with pytest.raises(ValueError):
            log_area([1.0, 2.0], costs)


def test_incomplete_studies_cannot_report_selected_seed_subset(tmp_path):
    (tmp_path / "PROTOCOL.json").write_text("{}")
    (tmp_path / "RUN_LEDGER.json").write_text(json.dumps({"complete": False}))
    with pytest.raises(ValueError, match="incomplete"):
        analyze(tmp_path)
    with pytest.raises(ValueError, match="incomplete"):
        holdout_analyze(tmp_path, tmp_path)

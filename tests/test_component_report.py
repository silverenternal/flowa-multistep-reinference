"""Validate inference bookkeeping independently of a generated study."""

import pytest

from tools.report_component_study_20261103 import holm, seed_summary


def test_holm_preserves_input_order_and_monotone_adjustment():
    assert holm([0.04, 0.01, 0.03]) == pytest.approx([0.06, 0.03, 0.06])
    assert holm([1.0, 0.0, 0.5]) == [1.0, 0.0, 1.0]


def test_canonical_seed_interval_uses_df2():
    x = seed_summary([1.0, 2.0, 3.0])
    assert x["mean"] == 2
    assert x["nominal_ci95"] == pytest.approx([-0.4841377117, 4.4841377117])
    assert x["df"] == 2
    with pytest.raises(ValueError):
        seed_summary([1.0, 2.0])
    with pytest.raises(ValueError):
        holm([float("nan")])

import numpy as np
import pytest

from tools.review_path_identifiability_20261103 import case, flow, parameters, run


@pytest.mark.parametrize("scale", [0.5, 1.0, 2.0])
def test_identical_endpoints_different_refresh_outputs(scale):
    variance, amplitude = parameters(0.5, scale, 0.0)
    np.testing.assert_allclose(flow(0, amplitude, 0.7), np.eye(2), atol=1e-14)
    np.testing.assert_allclose(flow(1, amplitude, 0.7), np.eye(2), atol=1e-14)
    result = case(0.5, scale, 0.7, 0.0)
    assert result["passed"]
    assert abs(result["output_variance"] - scale**2) < 1e-10
    assert abs(result["endpoint_assignment_gain"]) < 1e-12
    assert variance == 0.5


def test_sweep_has_all_outcome_controls():
    result = run(36, 30)
    assert result["passed"] and result["processed"] == 36 and result["skipped"] == 0
    for outcome in ["shrink", "preserve", "expand"]:
        assert sum(row["outcome"] == outcome for row in result["rows"]) == 12


def test_rejects_incomplete_or_degenerate_protocol():
    with pytest.raises(ValueError):
        run(35, 30)
    with pytest.raises(ValueError):
        parameters(0.5, 1.0, -1.0)
    with pytest.raises(ValueError):
        parameters(0.0, 1.0, 0.0)

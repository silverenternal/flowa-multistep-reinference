"""Distinguish target consistency from a contractive but incorrect stochastic kernel."""

import pytest

from tools.report_cifar_study_20261103 import log_area
from tools.review_boundary_kernel_20261103 import gaussian_coefficients, variance_after


def test_matched_independent_kernel_preserves_gaussian_target_variance():
    for target in [0.25, 1.0, 4.0]:
        for m in [0.2, 0.5, 0.9]:
            a, b = gaussian_coefficients(target, m)
            assert a < 1
            assert variance_after(target, a, b) == pytest.approx(target)


def test_exact_zero_flow_can_contract_to_the_wrong_target():
    a, b = gaussian_coefficients(1.0, 0.8, coupling="deterministic")
    assert a == pytest.approx(0.8)
    assert variance_after(1.0, a, b) == pytest.approx(0.68)
    assert b * b / (1 - a * a) == pytest.approx(1 / 9)
    # Reinterpreting the same mix as t=0 is already incorrect for an independent target.
    a, b = gaussian_coefficients(4.0, 0.8, restart_at_zero=True)
    assert variance_after(4.0, a, b) == pytest.approx(10.4)


def test_log_cost_area_and_invalid_grid():
    import math

    assert log_area([1.0, 3.0, 7.0], [1.0, math.e, math.e**3]) == pytest.approx(4.0)
    with pytest.raises(ValueError):
        log_area([1.0, 2.0], [2.0, 1.0])

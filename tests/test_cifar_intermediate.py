import numpy as np
import pytest

from tools.sweep_cifar_intermediate_20261103 import TIMES, discrepancy, schedule, squared_distances


def test_nested_physical_time_grids_and_calls():
    for factor in (1, 2):
        grid = schedule(factor)
        assert sum(len(x) - 1 for x in grid) == 64 * factor
        assert grid[0][0] == 0 and grid[-1][-1] == 1
        assert [x[-1] for x in grid[:-1]] == list(TIMES)
    for a, b in zip(schedule(1), schedule(2), strict=True):
        np.testing.assert_array_equal(a, b[::2])


def test_raw_pixel_distance_normalization():
    x, y = np.array([[0.0, 0.0], [2.0, 2.0]]), np.array([[1.0, 1.0], [3.0, 3.0]])
    np.testing.assert_allclose(squared_distances(x, y), [[1, 9], [1, 1]])
    assert discrepancy(x, x)["rbf"]["1.0"]["V_MMD2"] == 0
    assert discrepancy(x, x)["empirical_W2_RMS"] == 0


def test_kernel_u_v_statistic_and_assignment_match_direct_calculation():
    x = np.array([[0.0], [1.0], [2.0]])
    y = x + 0.4
    value = discrepancy(x, y)

    def k(a, b):
        return np.exp(-((a[:, None, :] - b[None, :, :]) ** 2).mean(2) / 2)

    xx, yy, xy = k(x, x), k(y, y), k(x, y)
    assert value["rbf"]["1.0"]["V_MMD2"] == pytest.approx(xx.mean() + yy.mean() - 2 * xy.mean())
    assert value["rbf"]["1.0"]["U_MMD2"] == pytest.approx(
        (xx.sum() + yy.sum() - 6) / 6 - 2 * xy.mean()
    )
    assert value["empirical_W2_RMS"] == pytest.approx(0.4)


def test_reject_unequal_or_degenerate_cohorts():
    with pytest.raises(ValueError):
        discrepancy(np.zeros((1, 2)), np.zeros((1, 2)))
    with pytest.raises(ValueError):
        discrepancy(np.zeros((2, 2)), np.zeros((3, 2)))

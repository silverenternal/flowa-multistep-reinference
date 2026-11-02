import numpy as np
import pytest

from tools.component_study_20261103 import configurations, kid_unbiased


def test_polynomial_unbiased_excludes_diagonals():
    # k(x,x')=(xx'+1)^3, x={0,1}, y={2,3}: xx=1, yy=343, xy mean=23.25.
    assert kid_unbiased(np.array([[0.0], [1.0]]), np.array([[2.0], [3.0]])) == pytest.approx(297.5)


def test_kid_permutation_invariant_and_can_be_negative():
    x = np.array([[0.0], [1.0], [2.0]])
    assert kid_unbiased(x, x) == pytest.approx(kid_unbiased(x[::-1], x))
    assert kid_unbiased(x, x) < 0


def test_controls_change_one_registered_factor():
    c = configurations()
    assert c["no_mean"]["beta"] == c["full"]["beta"]
    assert c["no_mix_fixed_time"]["restart_t0"] == pytest.approx(0.7 ** (1 / 3))
    with pytest.raises(ValueError):
        configurations(25)

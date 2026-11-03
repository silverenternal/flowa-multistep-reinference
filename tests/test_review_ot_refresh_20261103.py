"""Independent OT calculations and scope counterexamples for the research note."""
import numpy as np
import pytest

from tools.review_ot_refresh_20261103 import (
    finite_w2,
    isotropic_case,
    nonlinear_case,
    run,
    spd_case,
    validate_joint,
)


def test_transport_lp_known_discrete_translation():
    x = np.array([[0.], [2.]])
    p = np.array([.25, .75])
    assert finite_w2(x, p, x + 3, p) == pytest.approx(3.)


def test_nonreversible_refresh_and_nonlinear_transport():
    row = nonlinear_case(.5, .5, .5, 'cyclic')
    assert row['passed'] and row['bregman_deficit'] > 0
    assert row['w2_exact'] >= row['w2_lower'] > 0


def test_trivial_refresh_has_no_bias():
    row = nonlinear_case(1.5, .1, .8, 'identity')
    assert row['passed']
    assert row['w2_exact'] < 1e-7


def test_gaussian_sharp_bound_against_old_identity_counterexample():
    row = isotropic_case(1., .8, 0.)
    assert row['w2_exact'] == pytest.approx(1-np.sqrt(.68))
    assert row['w2_lower'] == pytest.approx(row['w2_exact'])


def test_prior_invariance_is_required():
    with pytest.raises(ValueError):
        validate_joint(np.array([.2, .8]), np.array([[0., 1.], [1., 0.]]))
    with pytest.raises(ValueError):
        spd_case(np.diag([-1., -1.]), .25, 'invalid')
    with pytest.raises(ValueError):
        nonlinear_case(0., .1, .5, 'independent')


def test_trace_deficit_does_not_imply_covariance_matrix_contraction():
    row = spd_case(np.diag([.1, 10.]), .5, 'anisotropic')
    assert row['passed'] and row['observed_trace_deficit'] > 0
    assert row['max_covariance_difference_eigenvalue'] > 0


def test_locked_record_count_cannot_silently_shrink():
    with pytest.raises(ValueError):
        run(72, 180)

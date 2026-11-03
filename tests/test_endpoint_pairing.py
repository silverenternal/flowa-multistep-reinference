import numpy as np
import pytest

from tools.review_endpoint_pairing_20261103 import controls, pairing


def test_known_controls_include_pairwise_monotone_but_noncyclic_map():
    rows = controls()
    assert not rows[0]['convex_gradient_necessary_condition_rejected']
    assert rows[1]['min_pair_ratio'] > 0
    assert rows[1]['convex_gradient_necessary_condition_rejected']


def test_translation_is_convex_gradient_and_zero_reassignment_gain():
    z = np.array([[0.,0.],[1.,2.],[-3.,1.]])
    row, _ = pairing(z, z+np.array([12.,-5.]))
    assert row['cost_improvement'] == pytest.approx(0.)
    assert row['min_pair_ratio'] == pytest.approx(1.)


def test_inconsistent_sample_shapes_fail_closed():
    with pytest.raises(ValueError):
        pairing(np.ones((3,2)),np.ones((3,3)))

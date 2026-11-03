"""A small rotational departure refutes an unrestricted no-go extension."""
from tools.review_ot_refresh_robust_20261103 import robust_case


def test_small_non_gradient_departure_can_expand_despite_strong_monotonicity():
    row = robust_case(.05, .05, .5)
    assert row['passed']
    assert row['path_moment_deficit'] < 0
    assert row['output_trace'] > row['target_trace']


def test_large_refresh_can_certify_positive_path_deficit():
    row = robust_case(.05, 1.5, .5)
    assert row['passed']
    assert row['path_moment_deficit'] >= row['robust_lower'] > 0

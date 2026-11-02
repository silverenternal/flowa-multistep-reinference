"""Analytic variance/df regression and fail-closed provenance checks."""
import math

import pytest

from tools.review_kanzi_statistics_20261102 import compare


def test_analytic_welch_and_index_difference_are_distinct():
    # Arm sample variances both 1; index-difference variance 4.
    result = compare(dict(a=0., b=1., c=2.), dict(a=4., b=3., c=2.))
    welch = result['welch_independent_record_sensitivity']
    indexed = result['historical_index_difference_not_matched_input']
    assert welch['difference_A'] == pytest.approx(2.)
    assert welch['se_A'] == pytest.approx(math.sqrt(2/3))
    assert welch['df'] == pytest.approx(4.)
    assert indexed['se_A'] == pytest.approx(2/math.sqrt(3))
    assert indexed['df'] == 2
    assert indexed['d_z'] == pytest.approx(1.)
    assert welch['ci95_A'] == pytest.approx([-0.2669579355, 4.2669579355])
    assert welch['p_two_sided'] == pytest.approx(0.0704839969)


@pytest.mark.parametrize('baseline,framework', [
    ({'a': 1., 'b': 2.}, {'b': 2., 'c': 3.}),
    ({'a': 1.}, {'a': 2.}),
    ({'a': 1., 'b': 2.}, {'a': float('nan'), 'b': 3.}),
    ({'a': 1., 'b': 1.}, {'a': 2., 'b': 3.}),
])
def test_invalid_records_fail_closed(baseline, framework):
    with pytest.raises(ValueError):
        compare(baseline, framework)

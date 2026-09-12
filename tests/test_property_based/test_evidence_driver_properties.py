"""Property-based tests for :mod:`adaptive_reflow.algorithm.evidence_driver`.

B.7 property-based testing — ``framework-internal-metrics.md`` rev 2 §1.

Coverage targets
----------------
* :func:`check_evidence_mode` — decision-boundary correctness:
  paper-grounded ``True`` when both ``profile_residual_fn`` and
  finite ``eps_implicit`` are supplied; heuristic risk flagged
  when ``eps_implicit`` is below threshold and no profile is
  supplied.

Seed policy (Research 4 mitigation): ``check_evidence_mode`` is a
pure decision function over a small input tuple.
"""

from __future__ import annotations

import pytest

# hypothesis is only present in test/dev venvs.
# Skip the entire module when missing so the rest of the suite still collects.
_hypothesis_spec = pytest.importorskip(
    "hypothesis",
    reason="hypothesis not in venv (install via `uv pip install hypothesis`)",
)

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from adaptive_reflow.algorithm.evidence_driver import (
    EVIDENCE_HEURISTIC_EPS_THRESHOLD,
    check_evidence_mode,
)


_PROPERTY_SETTINGS = settings(
    max_examples=20,
    deadline=2000,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


_EPS = st.floats(
    min_value=1e-6, max_value=1.0, allow_nan=False, allow_infinity=False
)
_THRESHOLD = st.floats(
    min_value=1e-4, max_value=1.0, allow_nan=False, allow_infinity=False
)


# ---------------------------------------------------------------------------
# Decision boundary: paper-grounded iff profile_residual_fn is supplied.
# ---------------------------------------------------------------------------


@_PROPERTY_SETTINGS
@given(eps=_EPS)
def test_check_evidence_mode_paper_grounded_when_profile_supplied(eps: float) -> None:
    """When ``profile_residual_fn`` is supplied (regardless of eps),
    the scheduler is reported as paper-grounded."""
    scheduler = type(
        "S",
        (),
        {
            "profile_residual_fn": lambda x: x,
            "eps_implicit": float(eps),
        },
    )()
    report = check_evidence_mode(scheduler)
    assert report.paper_grounded is True


@_PROPERTY_SETTINGS
@given(eps=_EPS)
def test_check_evidence_mode_paper_grounded_when_no_eps(eps: float) -> None:
    """When ``eps_implicit`` is None, the report's ``eps_implicit`` is None."""
    scheduler = type(
        "S",
        (),
        {
            "profile_residual_fn": None,
            "eps_implicit": None,
        },
    )()
    report = check_evidence_mode(scheduler)
    assert report.eps_implicit is None
    assert report.asymptotic_risk is False


@_PROPERTY_SETTINGS
@given(eps=_EPS, threshold=_THRESHOLD)
def test_check_evidence_mode_threshold_decision(
    eps: float, threshold: float
) -> None:
    """With no profile and ``eps_implicit < threshold``,
    ``asymptotic_risk is True`` (heuristic unsound)."""
    scheduler = type(
        "S",
        (),
        {
            "profile_residual_fn": None,
            "eps_implicit": float(eps),
        },
    )()
    report = check_evidence_mode(scheduler, eps_threshold=threshold)
    if eps < threshold:
        assert report.asymptotic_risk is True
    else:
        assert report.asymptotic_risk is False


# ---------------------------------------------------------------------------
# EVIDENCE_HEURISTIC_EPS_THRESHOLD is a positive finite float.
# ---------------------------------------------------------------------------


def test_default_threshold_is_positive() -> None:
    """``EVIDENCE_HEURISTIC_EPS_THRESHOLD`` is a positive finite float."""
    import math
    assert isinstance(EVIDENCE_HEURISTIC_EPS_THRESHOLD, float)
    assert math.isfinite(EVIDENCE_HEURISTIC_EPS_THRESHOLD)
    assert EVIDENCE_HEURISTIC_EPS_THRESHOLD > 0.0


@_PROPERTY_SETTINGS
@given(scheduler=st.builds(lambda: object()))
def test_check_evidence_mode_on_object_with_no_attributes(scheduler: object) -> None:
    """A bare ``object`` exposes neither ``profile_residual_fn`` nor
    ``eps_implicit`` — the report is the "not a codimension family"
    verdict (paper_grounded=False, asymptotic_risk=False)."""
    report = check_evidence_mode(scheduler)
    assert report.paper_grounded is False
    assert report.asymptotic_risk is False
    assert report.eps_implicit is None
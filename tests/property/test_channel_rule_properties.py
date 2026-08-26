"""Property-based invariants for the per-channel rule (DTB-R2 / DTB-R0 §3).

Hypothesis-driven templates covering the stability-collapse gate
closure (DTB-R0 §3 case 2):

1. **stability_floor_closes_gate** — for any
   ``(raw_score, bounded_score, calibration, perturbation_stability_lower_bound)``
   in the closed unit interval ``[0, 1]``, when
   ``perturbation_stability_lower_bound < PERTURBATION_STABILITY_FLOOR``
   the channel rule must close the gate (``gate=False``) and emit
   ``beta=0.0`` — regardless of any other factor in the evidence.

The strategy ``st_channel_inputs`` from ``tests.property.conftest``
produces a well-formed :class:`ChannelRuleInputs`; we mutate the four
named fields at the body level so the property exercises the rule
against arbitrary in-domain evidence.
"""
from __future__ import annotations

import dataclasses

from hypothesis import HealthCheck, assume, given, settings

from adaptive_reflow.frame.channel_rule import (
    AUDIT_STABILITY_COLLAPSE,
    PERTURBATION_STABILITY_FLOOR,
    compute_channel_decision,
)
from tests.property import st_channel_inputs, unit_floats

# ---------------------------------------------------------------------------
# 1. stability_floor_closes_gate — DTB-R0 §3 case 2 property.
# ---------------------------------------------------------------------------
# We sample the four named evidence fields in ``[0, 1]`` and then
# build a fresh :class:`ChannelRuleInputs` by mutating a randomly
# drawn ``st_channel_inputs``-produced inputs so the rest of the
# decision surface (caps, booleans, schedule) remains well-formed.


@given(
    raw_score=unit_floats,
    bounded_score=unit_floats,
    calibration=unit_floats,
    perturbation_stability_lower_bound=unit_floats,
    base_inputs=st_channel_inputs(),
)
@settings(
    max_examples=200,
    suppress_health_check=[
        HealthCheck.filter_too_much,
        HealthCheck.function_scoped_fixture,
    ],
    deadline=None,
)
def test_stability_floor_closes_gate(
    raw_score: float,
    bounded_score: float,
    calibration: float,
    perturbation_stability_lower_bound: float,
    base_inputs,
) -> None:
    """Whenever ``perturbation_stability_lower_bound`` is strictly below
    :data:`PERTURBATION_STABILITY_FLOOR`, the channel rule must close
    the gate with ``beta=0.0`` and the
    :data:`AUDIT_STABILITY_COLLAPSE` audit code.

    The property holds for arbitrary in-domain values of the four
    named evidence fields. The Hypothesis strategy
    :func:`tests.property.st_channel_inputs` already constrains the
    rest of the rule inputs to a well-formed state; we only swap the
    four fields the property is allowed to perturb.
    """
    # The stability-collapse branch is only triggered on strict-less-
    # than. Values at or above the floor must NOT trigger the branch
    # (we exercise that case in the unit tests; here we focus on the
    # property: "below the floor -> gate closed, beta = 0").
    assume(
        float(perturbation_stability_lower_bound) < float(PERTURBATION_STABILITY_FLOOR)
    )

    # 1. Replace the four named evidence fields on the base inputs.
    new_evidence = dataclasses.replace(
        base_inputs.evidence,
        raw_score=float(raw_score),
        bounded_score=float(bounded_score),
        calibration_lower_bound=float(calibration),
        perturbation_stability_lower_bound=float(perturbation_stability_lower_bound),
    )
    mutated = dataclasses.replace(
        base_inputs,
        evidence=new_evidence,
        calibration_lower_bound=float(calibration),
        perturbation_stability_lower_bound=float(perturbation_stability_lower_bound),
    )

    outputs = compute_channel_decision(mutated)
    decision = outputs.decision

    assert decision.gate is False
    assert float(decision.beta) == 0.0
    assert AUDIT_STABILITY_COLLAPSE in decision.audit_reason
    assert AUDIT_STABILITY_COLLAPSE in decision.blocker_codes


__all__ = ["test_stability_floor_closes_gate"]

"""Universal validators — single point of entry for stdlib validators.

This module re-exports the universal validators that gate the
``StateBundle`` / ``EnvelopeCriterion`` / ``EnvelopeClassification`` /
``Evaluator`` / ``RestartMixer`` contracts. It also imports the
universal numeric helpers from ``adaptive_reflow.contracts.validators``
(``validate_unit_factor``, ``validate_positive_int``,
``validate_nonneg_int``, ``validate_unit_float``,
``ValidationResult``) so universal callers do not need to reach into
``contracts``.

Stdlib-only: no torch, no I/O, no molecule vocabulary.

Public surface
--------------

Numeric helpers (re-exported from ``contracts.validators``)
    :data:`ValidationResult`
    :func:`validate_unit_factor`
    :func:`validate_unit_float`
    :func:`validate_positive_int`
    :func:`validate_nonneg_int`

State / condition / trace validators (re-exported from ``.state``)
    :func:`validate_state_bundle`
    :func:`validate_condition_delta`
    :func:`validate_integrator_trace`

Envelope validators (re-exported from ``.envelope``)
    :func:`validate_envelope_criterion`
    :func:`validate_envelope_classification`

Evaluator / mixer validators (re-exported from ``.evaluator`` / ``.mixer``)
    :func:`validate_evaluator_artifact_hash`
    :func:`validate_blend_inputs`

Adapter validators (re-exported from ``.adapter``)
    :func:`validate_capabilities`

Tasks satisfied:

* ``DTB-G1`` — public Flow Matching ODE re-inference engine + adapter
  contract.
"""

from __future__ import annotations

from ..contracts.validators import (
    ValidationResult,
    validate_nonneg_int,
    validate_positive_int,
    validate_unit_factor,
    validate_unit_float,
)
from .adapter import validate_capabilities
from .envelope import (
    validate_envelope_classification,
    validate_envelope_criterion,
)
from .evaluator import validate_evaluator_artifact_hash
from .mixer import validate_blend_inputs
from .state import (
    validate_condition_delta,
    validate_integrator_trace,
    validate_state_bundle,
)

__all__ = [
    # Numeric / scalar helpers
    "ValidationResult",
    "validate_nonneg_int",
    "validate_positive_int",
    "validate_unit_factor",
    "validate_unit_float",
    # Adapter
    "validate_capabilities",
    # State carriers
    "validate_state_bundle",
    "validate_condition_delta",
    "validate_integrator_trace",
    # Envelope
    "validate_envelope_criterion",
    "validate_envelope_classification",
    # Evaluator / mixer
    "validate_evaluator_artifact_hash",
    "validate_blend_inputs",
]

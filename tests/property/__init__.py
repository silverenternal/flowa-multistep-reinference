"""Re-export the Hypothesis strategies defined in
:mod:`tests.property.conftest` so test modules can write
``from tests.property import st_channel_inputs`` (the canonical pattern
for property-based test fixtures). Importing through this module
sidesteps the heavy ``adaptive_reflow`` types that the conftest must
defer for cycle-safety; the strategies themselves remain lazy at the
function-body level.
"""
from __future__ import annotations

# Re-export the public Hypothesis strategies defined in conftest.py.
# We import them by module rather than by name to keep the surface
# discoverable: any new strategy added to conftest's ``__all__`` can
# be picked up here with a single line.
from . import conftest as _conftest

# Floats / envelopes
unit_floats = _conftest.unit_floats
unit_floats_strict = _conftest.unit_floats_strict
prev_dynamic_floats = _conftest.prev_dynamic_floats
delta_cap_floats = _conftest.delta_cap_floats
floor_floats = _conftest.floor_floats
cap_floats = _conftest.cap_floats
cap_with_floor = _conftest.cap_with_floor

# Booleans / ints / types
booleans = _conftest.booleans
bool_only = _conftest.bool_only
nonneg_small_ints = _conftest.nonneg_small_ints
positive_small_ints = _conftest.positive_small_ints
negative_ints = _conftest.negative_ints
non_numeric_types = _conftest.non_numeric_types

# Non-finite floats (fail-closed path)
non_finite_floats = _conftest.non_finite_floats

# Claim-gate helpers
contract_passed = _conftest.contract_passed
contract_id_tuples = _conftest.contract_id_tuples
ci_coverage = _conftest.ci_coverage
paired_counts = _conftest.paired_counts
window_lengths = _conftest.window_lengths
gate_enabled = _conftest.gate_enabled
round_values = _conftest.round_values

# Lazy composite strategies
st_factors = _conftest.st_factors
st_factor_six = _conftest.st_factor_six
st_channel_inputs = _conftest.st_channel_inputs
st_claim_config = _conftest.st_claim_config
st_claim_evidence = _conftest.st_claim_evidence
st_state_bundle = _conftest.st_state_bundle
st_hostile_state = _conftest.st_hostile_state

__all__ = [
    # Floats
    "booleans",
    "bool_only",
    "cap_floats",
    "cap_with_floor",
    "ci_coverage",
    "contract_id_tuples",
    "contract_passed",
    "delta_cap_floats",
    "floor_floats",
    "gate_enabled",
    "negative_ints",
    "non_finite_floats",
    "non_numeric_types",
    "nonneg_small_ints",
    "paired_counts",
    "positive_small_ints",
    "prev_dynamic_floats",
    "round_values",
    "st_channel_inputs",
    "st_claim_config",
    "st_claim_evidence",
    "st_factor_six",
    "st_factors",
    "st_hostile_state",
    "st_state_bundle",
    "unit_floats",
    "unit_floats_strict",
    "window_lengths",
]

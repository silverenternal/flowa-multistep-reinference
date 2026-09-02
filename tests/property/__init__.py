"""Re-export the Hypothesis strategies defined in
:mod:`tests.property.conftest` so test modules can write
``from tests.property import st_channel_inputs`` (the canonical pattern
for property-based test fixtures). Importing through this module
sidesteps the heavy ``adaptive_reflow`` types that the conftest must
defer for cycle-safety; the strategies themselves remain lazy at the
function-body level.

Preflight: the strategies module requires the ``hypothesis`` package.
On sandboxes where ``hypothesis`` is not vendored (CPU-only rig,
fresh clone), this module falls back to a sentinel :data:`_MISSING`
so collection of the property-test subtree succeeds; the per-test
importorskip at the top of :mod:`tests.property.conftest` then
short-circuits individual tests with a clean SKIP rather than a
collection error.
"""
from __future__ import annotations

# Re-export the public Hypothesis strategies defined in conftest.py.
# We import them by module rather than by name to keep the surface
# discoverable: any new strategy added to conftest's ``__all__`` can
# be picked up here with a single line.
try:
    from . import conftest as _conftest
except ImportError:  # pragma: no cover — preflight guard for missing hypothesis
    # Hypothesis is not installed in this venv. Mark the strategies as
    # missing so downstream imports of ``tests.property.st_*`` names
    # raise a clear AttributeError at test-time rather than a hard
    # collection error at import time. The conftest's pytest.importorskip
    # call short-circuits collection cleanly.
    _conftest = None  # type: ignore[assignment]


def _lookup(name: str) -> object:
    """Return the strategy named ``name`` from :mod:`_conftest`.

    Raises a sentinel :class:`AttributeError` when the conftest failed
    to import (hypothesis missing). The test layer never reaches this
    call site because pytest.importorskip short-circuits first; the
    guard exists so the import-time collection does not blow up.
    """
    if _conftest is None:  # type: ignore[truthiness-bool]
        raise AttributeError(
            "tests.property.conftest failed to import — is `hypothesis` "
            "installed? (uv pip install hypothesis)"
        )
    return getattr(_conftest, name)


# Floats / envelopes
unit_floats = _lookup("unit_floats")
unit_floats_strict = _lookup("unit_floats_strict")
prev_dynamic_floats = _lookup("prev_dynamic_floats")
delta_cap_floats = _lookup("delta_cap_floats")
floor_floats = _lookup("floor_floats")
cap_floats = _lookup("cap_floats")
cap_with_floor = _lookup("cap_with_floor")

# Booleans / ints / types
booleans = _lookup("booleans")
bool_only = _lookup("bool_only")
nonneg_small_ints = _lookup("nonneg_small_ints")
positive_small_ints = _lookup("positive_small_ints")
negative_ints = _lookup("negative_ints")
non_numeric_types = _lookup("non_numeric_types")

# Non-finite floats (fail-closed path)
non_finite_floats = _lookup("non_finite_floats")

# Claim-gate helpers
contract_passed = _lookup("contract_passed")
contract_id_tuples = _lookup("contract_id_tuples")
ci_coverage = _lookup("ci_coverage")
paired_counts = _lookup("paired_counts")
window_lengths = _lookup("window_lengths")
gate_enabled = _lookup("gate_enabled")
round_values = _lookup("round_values")

# Lazy composite strategies
st_factors = _lookup("st_factors")
st_factor_six = _lookup("st_factor_six")
st_channel_inputs = _lookup("st_channel_inputs")
st_claim_config = _lookup("st_claim_config")
st_claim_evidence = _lookup("st_claim_evidence")
st_state_bundle = _lookup("st_state_bundle")
st_hostile_state = _lookup("st_hostile_state")

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

"""Smoke test suite for the FlowMol3 glue composite layer (Wave 49).

Mirrors :mod:`tests.test_adapters.test_lineageflow_glue`'s structure for
the dedicated pure-glue ``FlowMol3Glue`` class. The glue layer is a
**pure consumer** of :class:`FlowMol3Adapter` /
:class:`FlowMol3V2Adapter`; the tests here use a fake adapter that
holds trajectory entries in a plain dict (matching
``FlowMol3V2Adapter.export_trajectory`` shape) so the glue can run
without instantiating the heavy real adapter or the flowmol3 sidecar
venv.

Tests in this file (Wave 49 Agent E Phase 3A acceptance):

  * imports + __all__ (1)
  * composite-score arithmetics across the 5 axes (3)
  * restart policy round-trip (1)
  * paper-quantities carrier from cached native-state entry (1)

Total: **6 tests** (Wave 49 Phase 3A floor: ≥5).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pytest

from adaptive_reflow.adapters.flowmol3 import (
    FLOWMOL3_CHANNELS,
    FlowMol3Adapter,
    default_flowmol3_adapter,
)
from adaptive_reflow.adapters.flowmol3_glue import (
    DEFAULT_COMPOSITE_WEIGHTS,
    FLOWMOL3_COMPOSITE_KEY,
    FLOWMOL3_CONFIDENCE_THRESHOLD,
    FLOWMOL3_CTMC_STOCHASTICITY,
    FLOWMOL3_PRIOR_STD,
    FlowMol3CompositeWeights,
    FlowMol3Glue,
    FlowMol3PaperQuantities,
    FlowMol3RestartPolicy,
)


# ---------------------------------------------------------------------------
# Helpers — fake adapter + fake trace (no torch, no flowmol, no real ckpt)
# ---------------------------------------------------------------------------


@dataclass
class _FakeTrace:
    """Minimal duck-typed :class:`ODEIntegratorTrace` for tests."""

    native_state_digest: str
    steps: int = 50
    accept_rate: float = 1.0
    integrator_config_hash: str = "fake-hash"


@dataclass
class _FakeAdapter:
    """Fake adapter exposing ``_native_states`` as a plain dict.

    Mirrors the relevant slice of
    :class:`FlowMol3V2Adapter._native_states` — the glue only does
    ``adapter._native_states[trace.native_state_digest]`` and reads
    the ``traj_x`` + ``traj_a/traj_c/traj_e`` entries. No Protocol
    methods are exercised by the glue.
    """

    _native_states: dict[str, dict[str, Any]] = field(default_factory=dict)


def _fake_native_entry(n_atoms: int = 8, *, n_steps: int = 10) -> dict[str, Any]:
    """Build a synthetic ``(traj_x, traj_a, traj_c, traj_e)`` entry.

    Shapes mirror :meth:`FlowMol3V2Adapter.export_trajectory`:

      - ``traj_x`` — ``(n_steps, n_atoms, 3)`` float64.
      - ``traj_a`` — ``(n_steps, n_atoms)`` int64 (one-hot argmax).
      - ``traj_c`` — ``(n_steps, n_atoms)`` int64.
      - ``traj_e`` — ``(n_steps, 2 * n_upper_edges)`` int64.
    """
    n_upper = max(1, n_atoms * (n_atoms - 1) // 2)
    traj_x = np.zeros((n_steps, n_atoms, 3), dtype=np.float64)
    traj_a = np.zeros((n_steps, n_atoms), dtype=np.int64)
    traj_c = np.zeros((n_steps, n_atoms), dtype=np.int64)
    traj_e = np.zeros((n_steps, 2 * n_upper), dtype=np.int64)
    # Last step endpoint values (small perturbations).
    traj_x[-1] = 0.01 * np.ones((n_atoms, 3), dtype=np.float64)
    traj_a[-1] = np.ones(n_atoms, dtype=np.int64)
    traj_c[-1] = np.zeros(n_atoms, dtype=np.int64)
    traj_e[-1] = np.ones(2 * n_upper, dtype=np.int64)
    return {
        "traj_x": traj_x,
        "traj_a": traj_a,
        "traj_c": traj_c,
        "traj_e": traj_e,
    }


def _fake_adapter_with_entry(
    digest: str = "fake-flowmol3-digest",
    n_atoms: int = 8,
) -> tuple[_FakeAdapter, _FakeTrace]:
    """Build a fake adapter whose cache holds one synthetic trajectory."""
    adapter = _FakeAdapter()
    adapter._native_states[digest] = _fake_native_entry(n_atoms=n_atoms)
    return adapter, _FakeTrace(digest)


# ---------------------------------------------------------------------------
# Test 1 — imports + __all__ + default constants
# ---------------------------------------------------------------------------


def test_glue_imports_and_all():
    """``FlowMol3Glue`` + 3 dataclasses + 6 module-level constants."""
    assert FlowMol3Glue is not None
    assert FlowMol3CompositeWeights is not None
    assert FlowMol3RestartPolicy is not None
    assert FlowMol3PaperQuantities is not None
    assert FLOWMOL3_COMPOSITE_KEY == "flowmol3_composite"
    # Default weights sum to 1.0 by construction.
    assert sum(DEFAULT_COMPOSITE_WEIGHTS) == pytest.approx(1.0)
    for w in DEFAULT_COMPOSITE_WEIGHTS:
        assert w >= 0.0
    # Pinned constants match upstream canonical values.
    assert FLOWMOL3_PRIOR_STD == 1.0
    assert FLOWMOL3_CONFIDENCE_THRESHOLD == 0.9
    assert FLOWMOL3_CTMC_STOCHASTICITY == 30.0
    # Default weights tuple matches the FlowMol3CompositeWeights defaults.
    weights = FlowMol3CompositeWeights()
    assert weights.as_tuple() == DEFAULT_COMPOSITE_WEIGHTS


# ---------------------------------------------------------------------------
# Test 2 — composite_score: real-metric inputs produce bounded output
# ---------------------------------------------------------------------------


def test_glue_composite_score_real_metrics():
    """Realistic chemistry dict + geometry dict → composite ∈ [-1, 1]."""
    adapter = _FakeAdapter()
    glue = FlowMol3Glue(adapter=adapter)

    chemistry = {
        "frac_valid_mols": 0.95,
        "frac_mols_stable_valence": 0.90,
        "energy_js_div": 0.05,  # low JS-div → good
        "reos_cum_dev": 0.02,  # low REOS cum dev → good
    }
    geometry = {
        "med_rmsd": 0.10,  # low RMSD after xTB → good
    }
    result = glue.composite_score(chemistry, geometry)

    # Composite bounded.
    assert -1.0 <= result["composite"] <= 1.0
    # Axis values echoed.
    assert result["phi1_frac_valid_mols"] == pytest.approx(0.95)
    assert result["phi2_frac_mols_stable"] == pytest.approx(0.90)
    assert result["phi3_neg_energy_js_div"] == pytest.approx(-0.05)
    assert result["phi4_neg_reos_cum_dev"] == pytest.approx(-0.02)
    assert result["phi5_neg_med_rmsd_after_xtb"] == pytest.approx(-0.10)
    # All 5 weights echoed.
    assert result["weights"] == list(DEFAULT_COMPOSITE_WEIGHTS)
    assert result["has_geometry"] is True
    # FlowMol3 vocab sizes (10 atom types / 4 bond types per upstream
    # canonical, since the fake adapter has no N_ATOM_TYPES attribute).
    assert result["K_atom_types"] == 10
    assert result["K_bond_types"] == 4
    # Composite is monotone in each axis: phi1=1.0, phi2=1.0 with the
    # negative axes being small negatives; with default weights the
    # composite should land near 0.30*0.95 + 0.25*0.90 - 0.15*0.05
    # - 0.15*0.02 - 0.15*0.10 = 0.285 + 0.225 - 0.0075 - 0.003 - 0.015
    # ≈ 0.4845.
    assert result["composite"] == pytest.approx(0.4845, abs=1e-3)


# ---------------------------------------------------------------------------
# Test 3 — composite_score: geometry=None drops the geometry axis
# ---------------------------------------------------------------------------


def test_glue_composite_score_no_geometry_renormalizes_weights():
    """``geometry=None`` → phi5=None; chemistry weights renormalized to sum 1."""
    adapter = _FakeAdapter()
    glue = FlowMol3Glue(adapter=adapter)

    chemistry = {
        "frac_valid_mols": 1.0,
        "frac_mols_stable_valence": 1.0,
        "energy_js_div": 0.0,
        "reos_cum_dev": 0.0,
    }
    result = glue.composite_score(chemistry, geometry=None)

    # phi5 is None (geometry axis dropped).
    assert result["phi5_neg_med_rmsd_after_xtb"] is None
    assert result["has_geometry"] is False
    # Weights renormalized: w5 → 0; the other 4 weights are scaled by
    # 1 / (1 - 0.15) ≈ 1.1765. Sum should still be 1.0.
    echoed_w = result["weights"]
    assert sum(echoed_w) == pytest.approx(1.0)
    assert echoed_w[4] == pytest.approx(0.0)
    assert echoed_w[0] == pytest.approx(0.30 / 0.85)
    # With all-positive phi1/phi2 and zero phi3/phi4, composite = w1 + w2.
    expected = (0.30 + 0.25) / 0.85
    assert result["composite"] == pytest.approx(expected, abs=1e-9)


# ---------------------------------------------------------------------------
# Test 4 — composite_score: missing metric keys → NaN composite (graceful)
# ---------------------------------------------------------------------------


def test_glue_composite_score_missing_keys_returns_nan():
    """Missing keys (e.g. no chemistry dict) → composite = NaN; no crash."""
    adapter = _FakeAdapter()
    glue = FlowMol3Glue(adapter=adapter)

    result = glue.composite_score(chemistry={}, geometry={})

    # All phi axes are None (missing keys).
    assert result["phi1_frac_valid_mols"] is None
    assert result["phi2_frac_mols_stable"] is None
    assert result["phi3_neg_energy_js_div"] is None
    assert result["phi4_neg_reos_cum_dev"] is None
    assert result["phi5_neg_med_rmsd_after_xtb"] is None
    # Composite is NaN (no axis available).
    assert result["composite"] != result["composite"]  # NaN check


# ---------------------------------------------------------------------------
# Test 5 — restart policy round-trip
# ---------------------------------------------------------------------------


def test_glue_restart_policy_re_mask_categorical():
    """Build a policy; check fields + validation."""
    adapter = _FakeAdapter()
    glue = FlowMol3Glue(adapter=adapter)

    policy = glue.restart_policy(mode="re_mask_categorical")
    assert policy.mode == "re_mask_categorical"
    assert policy.confidence_threshold == pytest.approx(0.9)
    assert policy.ctmc_stochasticity == pytest.approx(30.0)
    assert policy.prior_std == pytest.approx(1.0)
    # Default per-channel beta is 0.5 for all 3 FlowMol3 channels.
    assert set(policy.beta_by_channel.keys()) == set(FLOWMOL3_CHANNELS)
    for ch in FLOWMOL3_CHANNELS:
        assert policy.beta_by_channel[ch] == pytest.approx(0.5)

    # Apply to a fake StateBundle (a dataclass with native_state_digest).
    @dataclass
    class _FakeState:
        native_state_digest: str = "state-digest-0"
        provenance: tuple[str, ...] = ()

    state = _FakeState()
    new_state = policy.apply_to(state)
    # New digest is derived from the policy mode + beta blob.
    assert new_state.native_state_digest.startswith(
        "flowmol3:restart:re_mask_categorical:"
    )
    assert "state-digest-0" in new_state.native_state_digest
    # Provenance augmented.
    assert "flowmol3_restart:re_mask_categorical" in new_state.provenance

    # Bad mode → ValueError.
    with pytest.raises(ValueError, match="mode must be"):
        glue.restart_policy(mode="invalid_mode")

    # Bad beta → ValueError.
    with pytest.raises(ValueError, match=r"beta_by_channel"):
        FlowMol3RestartPolicy(
            mode="re_mask_categorical",
            beta_by_channel={"coordinate": 1.5},  # out of [0, 1]
        )


# ---------------------------------------------------------------------------
# Test 6 — paper-quantities carrier
# ---------------------------------------------------------------------------


def test_glue_paper_quantities_carrier_from_native_state():
    """Build the carrier from a cached trajectory; verify 13 fields."""
    adapter, trace = _fake_adapter_with_entry()
    glue = FlowMol3Glue(adapter=adapter)

    pq = glue.paper_quantities_carrier(trace)

    # Continuous subspace (4 fields).
    assert isinstance(pq.sheet_A_x, float)
    assert isinstance(pq.packing_B_x, float)
    assert isinstance(pq.cell_C_x, float)
    assert isinstance(pq.e_rho_x, float)
    assert 0.0 <= pq.sheet_A_x <= 1.0  # 1/(1+var) with small variance

    # Categorical subspace (4 fields).
    assert isinstance(pq.ctmc_unmask_rate, float)
    assert isinstance(pq.ctmc_mask_rate, float)
    assert pq.confidence_threshold == pytest.approx(0.9)
    assert pq.self_condition_active is True
    assert 0.0 <= pq.ctmc_unmask_rate <= 1.0
    assert 0.0 <= pq.ctmc_mask_rate <= 1.0

    # Aggregated framework signals (4 fields + 1 ratio = 5 fields).
    assert isinstance(pq.sheet_A_aggregate, float)
    assert isinstance(pq.packing_B_aggregate, float)
    assert isinstance(pq.cell_C_aggregate, float)
    assert isinstance(pq.e_rho_aggregate, float)
    assert isinstance(pq.aggregate_ratio, float)

    # Field count check — dataclass has 13 documented fields.
    field_names = {f.name for f in FlowMol3PaperQuantities.__dataclass_fields__.values()}
    assert len(field_names) == 13

    # Missing digest → KeyError.
    bad_trace = _FakeTrace("missing-digest")
    with pytest.raises(KeyError):
        glue.paper_quantities_carrier(bad_trace)


# ---------------------------------------------------------------------------
# Bonus — compute_chemistry_metrics stub + composite wiring with the real
#         FlowMol3Adapter (placeholder) — verifies that the glue can
#         instantiate against the real v1 adapter without crashing.
# ---------------------------------------------------------------------------


def test_glue_instantiate_against_real_v1_placeholder():
    """The glue instantiates against the real (placeholder) FlowMol3Adapter.

    This is the cross-compat smoke test: the glue's ``Any``-typed
    ``adapter`` parameter accepts either the placeholder
    :class:`FlowMol3Adapter` or the real :class:`FlowMol3V2Adapter`,
    so the contract is forward-compatible.
    """
    real_adapter = default_flowmol3_adapter()
    assert isinstance(real_adapter, FlowMol3Adapter)
    glue = FlowMol3Glue(adapter=real_adapter)
    assert glue.adapter is real_adapter
    # composite_score on empty chemistry still works (NaN composite).
    result = glue.composite_score(chemistry={}, geometry={})
    assert result["composite"] != result["composite"]  # NaN
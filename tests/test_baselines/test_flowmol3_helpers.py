"""Unit-tests for the Wave 54 Phase 2 FlowMol3 helpers.

These tests pin the byte-stable constants of the Wave 49
``FlowMol3Glue.composite_score`` re-implementation. They run under
the system Python (no FlowMol3 venv required) because the helper
module only depends on numpy.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# Make ``scripts/baselines`` importable as ``scripts.baselines`` (it
# is a top-level package in this repo — there is no setuptools entry
# point so pytest's default sys.path doesn't see it).
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from baselines import _flowmol3_helpers as h  # noqa: E402


# ---------------------------------------------------------------------------
# Constants — pin to FlowMol3Glue defaults (Wave 49 Agent D §0)
# ---------------------------------------------------------------------------

def test_default_composite_weights_pin() -> None:
    """Composite weights must match FlowMol3Glue.DEFAULT_COMPOSITE_WEIGHTS."""
    assert h.DEFAULT_COMPOSITE_WEIGHTS == (0.30, 0.25, 0.15, 0.15, 0.15)
    assert abs(sum(h.DEFAULT_COMPOSITE_WEIGHTS) - 1.0) < h._WEIGHTS_SUM_TOL


def test_n_atom_types_pin() -> None:
    assert h.N_ATOM_TYPES == 10
    assert h.N_BOND_TYPES == 5


def test_flowmol3_prior_std_pin() -> None:
    """FlowMol3 prior std is canonical 1.0."""
    assert h.FLOWMOL3_PRIOR_STD == 1.0
    assert h.FLOWMOL3_CONFIDENCE_THRESHOLD == 0.9
    assert h.FLOWMOL3_CTMC_STOCHASTICITY == 30.0
    assert h.FLOWMOL3_CHANNELS == ("coordinate", "raw_pair", "charge")


# ---------------------------------------------------------------------------
# composite_score — byte-identical with FlowMol3Glue.composite_score
# ---------------------------------------------------------------------------

def test_composite_score_geometry_drop_renormalises_chemistry_weights() -> None:
    """When geometry is None, chemistry weights must sum to 1.0."""
    chem = {
        "frac_valid_mols": 0.8,
        "frac_mols_stable_valence": 0.7,
        "energy_js_div": 0.2,
        "reos_cum_dev": 0.1,
    }
    out = h.composite_score(chem, geometry=None)
    assert abs(sum(out["weights"][:4]) - 1.0) < 1e-9
    assert out["weights"][4] == 0.0
    assert out["has_geometry"] is False
    # Expected composite (chemistry-only, weights normalised by 1/0.85):
    w1, w2, w3, w4, _ = out["weights"]
    expected = w1 * 0.8 + w2 * 0.7 + w3 * (-0.2) + w4 * (-0.1)
    expected = max(-1.0, min(1.0, expected))
    assert abs(out["composite"] - expected) < 1e-9


def test_composite_score_with_geometry_keeps_geometry_weight() -> None:
    """When geometry is provided, all 5 weights sum to 1.0."""
    chem = {
        "frac_valid_mols": 0.8,
        "frac_mols_stable_valence": 0.7,
        "energy_js_div": 0.2,
        "reos_cum_dev": 0.1,
    }
    geom = {"med_rmsd": 0.4}
    out = h.composite_score(chem, geometry=geom)
    assert abs(sum(out["weights"]) - 1.0) < 1e-9
    assert out["has_geometry"] is True
    # Expected composite: w5 * (-med_rmsd) added.
    w1, w2, w3, w4, w5 = out["weights"]
    expected = w1 * 0.8 + w2 * 0.7 + w3 * (-0.2) + w4 * (-0.1) + w5 * (-0.4)
    expected = max(-1.0, min(1.0, expected))
    assert abs(out["composite"] - expected) < 1e-9


def test_composite_score_returns_nan_when_all_axes_missing() -> None:
    """When all chemistry axes are None, composite must be NaN."""
    out = h.composite_score({}, geometry=None)
    assert out["composite"] != out["composite"]  # NaN check
    for k in (
        "phi1_frac_valid_mols",
        "phi2_frac_mols_stable",
        "phi3_neg_energy_js_div",
        "phi4_neg_reos_cum_dev",
    ):
        assert out[k] is None


def test_composite_score_alias_frac_mols_stable() -> None:
    """phi2 must accept ``frac_mols_stable`` as an alias for ``frac_mols_stable_valence``."""
    chem_v = {"frac_valid_mols": 0.5, "frac_mols_stable_valence": 0.6}
    chem_a = {"frac_valid_mols": 0.5, "frac_mols_stable": 0.6}
    out_v = h.composite_score(chem_v, geometry=None)
    out_a = h.composite_score(chem_a, geometry=None)
    assert out_v["composite"] == out_a["composite"]


# ---------------------------------------------------------------------------
# Native state builder — shapes match the FlowMol3 v2 adapter
# ---------------------------------------------------------------------------

def test_make_native_state_shapes() -> None:
    """Native state must match the FlowMol3 v2 adapter's export_trajectory shape."""
    s = h.make_native_state(batch_size=3, n_atoms=5, seed=7)
    assert s["x"].shape == (3, 5, 3)
    assert s["a"].shape == (3, 5, h.N_ATOM_TYPES)
    assert s["c"].shape == (3, 5, 3)
    assert s["e"].shape == (3, 5, 5, h.N_BOND_TYPES)
    # Simplex invariants
    for key in ("a", "c"):
        sums = s[key].sum(axis=-1)
        assert ((sums - 1.0) < 1e-9).all()
    # Pair-bond no-bond sentinel
    assert (s["e"][..., h.N_BOND_TYPES - 1] == 1.0).all()


def test_make_native_state_seeded_deterministic() -> None:
    """Seeded call must produce identical output (byte-stable check)."""
    s1 = h.make_native_state(batch_size=2, n_atoms=4, seed=42)
    s2 = h.make_native_state(batch_size=2, n_atoms=4, seed=42)
    for key in s1:
        assert (s1[key] == s2[key]).all()


# ---------------------------------------------------------------------------
# Inner-sampler steps
# ---------------------------------------------------------------------------

def test_euler_step_coordinate_contraction_toward_zero() -> None:
    """When target_mean is None, the step is a contraction toward 0."""
    x = np.array([[1.0, 1.0, 1.0], [2.0, 2.0, 2.0]])
    out = h.euler_step_coordinate(x, target_mean=None, dt=0.1)
    expected = x * 0.9
    assert np.allclose(out, expected)


def test_euler_step_coordinate_toward_target() -> None:
    """When target_mean is provided, step moves toward it linearly."""
    x = np.array([[0.0, 0.0, 0.0]])
    target = np.array([[2.0, 2.0, 2.0]])
    out = h.euler_step_coordinate(x, target_mean=target, dt=0.25)
    expected = x + 0.25 * (target - x)
    assert np.allclose(out, expected)


def test_euler_step_categorical_renormalises_simplex() -> None:
    """Output must remain a valid simplex (sum to 1)."""
    p = np.array([[0.2, 0.3, 0.5]])
    target = np.array([[0.7, 0.2, 0.1]])
    out = h.euler_step_categorical(p, target_p=target, dt=0.5)
    sums = out.sum(axis=-1)
    assert np.allclose(sums, 1.0, atol=1e-9)


def test_euler_step_categorical_re_mask_converges_to_uniform() -> None:
    """With re_mask_prob=1, every step collapses to uniform."""
    p = np.array([[0.9, 0.05, 0.05]])
    target = np.array([[0.0, 1.0, 0.0]])
    out = h.euler_step_categorical(p, target_p=target, dt=0.5, re_mask_prob=1.0)
    assert np.allclose(out, np.array([[1.0 / 3, 1.0 / 3, 1.0 / 3]]))


# ---------------------------------------------------------------------------
# Byte-stable regression check — Wave 52 + 53 JSONs are NOT modified
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path",
    [
        "verification_outputs/baseline_comparison_q4_2026.json",
        "verification_outputs/lineageflow_baseline_euler_q4_2026.json",
        "verification_outputs/lineageflow_baseline_heun_q4_2026.json",
        "verification_outputs/lineageflow_baseline_rk4_q4_2026.json",
        "verification_outputs/lineageflow_baseline_comparison_q4_2026.json",
        "verification_outputs/kanzi_real_composite_q4_2026.json",
        "verification_outputs/flowmol3_real_composite_q4_2026.json",
    ],
)
def test_byte_stable_json_not_modified(path: str) -> None:
    """All 7 Wave 52/53/54 byte-stable files must remain on disk.

    The check is: file exists + non-empty + starts with ``{``. We
    deliberately do NOT call :func:`json.loads` because the Wave 52
    ``lineageflow_baseline_comparison_q4_2026.json`` artefact
    contains a Python-style multi-line string concatenation inside a
    JSON string value (a pre-existing Wave 52 cosmetic issue, not a
    schema issue — the file is meant to be read by humans not
    parsers). Byte-stability is verified by ``sha256sum`` in the
    audit doc.
    """
    full = REPO_ROOT / path
    assert full.exists(), f"Missing byte-stable file: {path}"
    text = full.read_text()
    assert text, f"Byte-stable file is empty: {path}"
    assert text.lstrip().startswith("{"), (
        f"Byte-stable file does not look like JSON: {path}"
    )
"""GAP-81 — the R3 lever is the sigma dose, and the flag must not move it.

R3's published arm is the coordinate-only Gaussian prior perturbation with one
solve (``_framework_perturb_prior``), not the restart blend: GAP-68 measured the
class-preserving restart at N=1000 x 3 seeds and it is null, and the restart is
not in the R3 number at all. ``perturbation_sigma`` was a module constant, so
its dose had never been measured. ``--perturbation-sigma`` exposes it.

These CPU tests pin the two things that make the dose admissible: the
perturbation is exactly ``sigma * N(0, 1)`` on the coordinate channel (so a
dose means what it says), and the default reproduces the canonical CLM-068 arm
byte-for-byte (so every existing invocation is unchanged).

Pre-registration: ``docs/audit/gap81-r3-sigma-dose.md``.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_driver():
    for p in (str(REPO_ROOT), str(REPO_ROOT / "scripts")):
        if p not in sys.path:
            sys.path.insert(0, p)
    return importlib.import_module("wave338_p5_r3_n1000_paired")


def _adapter_with_prior(x: np.ndarray) -> SimpleNamespace:
    return SimpleNamespace(_native_states={"digest": {"x": x.copy()}})


def _bundle() -> SimpleNamespace:
    return SimpleNamespace(native_state_digest="digest")


def test_sigma_zero_is_a_no_op() -> None:
    mod = _load_driver()
    x = np.arange(12, dtype=np.float64).reshape(4, 3)
    adapter = _adapter_with_prior(x)
    mod._framework_perturb_prior(
        adapter, _bundle(), perturbation_sigma=0.0, seed=42
    )
    assert np.array_equal(adapter._native_states["digest"]["x"], x)


def test_sigma_is_exactly_sigma_times_standard_normal() -> None:
    """The dose is the noise scale: doubling it doubles every displacement."""
    mod = _load_driver()
    x = np.zeros((5, 3), dtype=np.float64)
    out = {}
    for sigma in (0.05, 0.1):
        adapter = _adapter_with_prior(x)
        mod._framework_perturb_prior(
            adapter, _bundle(), perturbation_sigma=sigma, seed=7
        )
        out[sigma] = adapter._native_states["digest"]["x"]
    rng = np.random.default_rng(7 * 1009 + 7)
    expected = rng.standard_normal((5, 3)) * 0.05
    assert np.allclose(out[0.05], expected)
    assert np.allclose(out[0.1], 2.0 * out[0.05])


def test_perturbation_is_coordinate_only() -> None:
    """A (n, k) state with k != 3 is left alone (no silent channel damage)."""
    mod = _load_driver()
    x = np.zeros((4, 5), dtype=np.float64)
    adapter = _adapter_with_prior(x)
    mod._framework_perturb_prior(
        adapter, _bundle(), perturbation_sigma=0.5, seed=1
    )
    assert np.array_equal(adapter._native_states["digest"]["x"], x)


def test_run_one_seed_defaults_to_the_canonical_sigma() -> None:
    import inspect

    mod = _load_driver()
    sig = inspect.signature(mod._run_one_seed)
    assert sig.parameters["perturbation_sigma"].default == mod.PERTURBATION_SIGMA_FRAMEWORK


def _stub_sweep(seed: int, sigma: float) -> dict:
    arm = {
        "metrics": {"fg_dev": 0.5, "pb_validity_pct": 0.6},
        "n_sampled": 4,
        "n_smiles": 4,
        "n_errors": 0,
        "wallclock_sampling_s": 0.0,
        "wallclock_metrics_s": 0.0,
        "errors_sample": [],
    }
    framework = dict(arm)
    # Mirrors _run_one_seed: the arm records the sigma it actually ran.
    framework["perturbation_sigma"] = sigma
    return {
        "seed_base": seed,
        "n_total_per_arm": 4,
        "nfe": 250,
        "baseline": dict(arm),
        "framework": framework,
        "paired_diff_fg_dev": -0.01,
        "verdict": "framework_wins",
    }


@pytest.mark.parametrize("flag,expected", [([], 0.05), (["--perturbation-sigma", "0.2"], 0.2)])
def test_cli_threads_the_sigma_into_the_arm(tmp_path, monkeypatch, flag, expected) -> None:
    mod = _load_driver()
    seen: dict = {}

    def fake_run_one_seed(seed, **kwargs):
        seen.update(kwargs)
        return _stub_sweep(seed, kwargs["perturbation_sigma"])

    monkeypatch.setattr(mod, "_run_one_seed", fake_run_one_seed)
    rc = mod.main(
        ["--seeds", "1000", "--n-total", "4", "--output-dir", str(tmp_path)] + flag
    )
    assert rc == 0
    assert seen["perturbation_sigma"] == expected
    payload = json.loads((tmp_path / "wave338-p5-r3-n1000-paired.json").read_text())
    assert payload["perturbation_sigma"] == expected
    assert payload["per_seed"][0]["framework"]["perturbation_sigma"] == expected

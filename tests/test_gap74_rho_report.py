"""GAP-74 report tool — rho(m) monotonicity, the endpoint rule, and L3.

The sweep is 30 cells of expensive generation, so the thing that decides its
verdict must be testable before the run. Synthetic cells here have a known
``rho`` by construction: ``X_m = sqrt(rho)·B + sqrt(1-rho)·E`` gives
``Tr(Cov X_m) / Tr(Cov B) ≈ rho`` when both ``B`` and ``E`` are isotropic.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tools.gap74_rho_report import main

N = 400
D = 24
MS = [0.9, 0.7, 0.5, 0.3, 0.1]
ARMS = ["CosineAnnealScheduler"]


def _samples(rng: np.random.Generator, rho: float, base: np.ndarray,
             noise: np.ndarray) -> np.ndarray:
    """``X`` with ``Tr(Cov X) / Tr(Cov base) ≈ rho``.

    ``X = sqrt(rho)·B + 0.02·E``. The noise term is small *and identical across
    m*, so it contributes a constant offset to every point (differences are
    preserved) while still giving the bootstrap something to vary. Scaling the
    noise by ``sqrt(1-rho)`` instead would hold the total variance fixed and
    make every curve read 1.0 — the obvious construction, and wrong.
    """
    return np.sqrt(rho) * base + 0.02 * noise


def _build(root: Path, rhos: dict[str, list[float]], *, seeds=(42,),
           skip: set[tuple[str, float, int]] | None = None) -> None:
    """``rhos[ckpt]`` is the rho for each m in ``MS``."""
    skip = skip or set()
    for ckpt, curve in rhos.items():
        rng = np.random.default_rng(abs(hash(ckpt)) % (2**32))
        base = rng.normal(size=(N, D))
        noise = rng.normal(size=(N, D))
        for seed in seeds:
            for m, rho in zip(MS, curve, strict=True):
                if (ckpt, m, seed) in skip:
                    continue
                cell = root / f"{ckpt}_m{m}_s{seed}"
                cell.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(cell / "baseline_samples.npz", samples=base)
                for arm in ARMS:
                    np.savez_compressed(
                        cell / f"{arm}_samples.npz",
                        samples=_samples(rng, rho, base, noise),
                    )


def _run(root: Path, out: Path, *, bootstrap: int = 60) -> dict:
    main(["--root", str(root), "--ckpts", "production", "w16e1_5k",
          "--ms", *[str(m) for m in MS], "--seeds", "42",
          "--arms", *ARMS, "--bootstrap", str(bootstrap),
          "--out", str(out)])
    return json.loads(out.read_text())


# rho increases with m (MS is descending), and rho(0.9) reaches 1.
RISING = [1.0, 0.85, 0.65, 0.4, 0.2]


def test_monotone_curve_is_supported(tmp_path: Path) -> None:
    root = tmp_path / "run"
    _build(root, {"production": RISING, "w16e1_5k": RISING})
    report = _run(root, tmp_path / "r.json")
    assert report["verdict"] == "CONDITIONAL_MEAN_BOUND_SUPPORTED"
    assert report["per_checkpoint"]["production"]["rule1_all_arms"]
    assert report["per_checkpoint"]["production"]["rule2_all_arms"]


def test_flat_curve_is_falsified(tmp_path: Path) -> None:
    root = tmp_path / "run"
    flat = [0.6, 0.6, 0.6, 0.6, 0.6]
    _build(root, {"production": flat, "w16e1_5k": flat})
    report = _run(root, tmp_path / "r.json")
    assert report["verdict"] == "FALSIFIED"


def test_falling_curve_is_falsified(tmp_path: Path) -> None:
    root = tmp_path / "run"
    falling = list(reversed(RISING))
    _build(root, {"production": falling, "w16e1_5k": falling})
    report = _run(root, tmp_path / "r.json")
    assert report["verdict"] == "FALSIFIED"


def test_low_endpoint_breaks_rule2(tmp_path: Path) -> None:
    root = tmp_path / "run"
    # Monotone, but rho(0.9) is 0.4 — the near-no-noise limit is violated.
    curve = [0.4, 0.3, 0.2, 0.1, 0.05]
    _build(root, {"production": curve, "w16e1_5k": curve})
    report = _run(root, tmp_path / "r.json")
    assert report["per_checkpoint"]["production"]["rule1_all_arms"]
    assert not report["per_checkpoint"]["production"]["rule2_all_arms"]
    assert report["verdict"] == "MIXED"


def test_missing_cells_are_inconclusive(tmp_path: Path) -> None:
    root = tmp_path / "run"
    _build(root, {"production": RISING, "w16e1_5k": RISING},
           skip={("w16e1_5k", 0.5, 42)})
    report = _run(root, tmp_path / "r.json")
    assert report["verdict"] == "INCONCLUSIVE"
    assert report["per_checkpoint"]["w16e1_5k"]["missing_cells"]


def test_baseline_moving_with_m_raises(tmp_path: Path) -> None:
    """L3: if the baseline samples differ across m, the allocation moved."""
    root = tmp_path / "run"
    _build(root, {"production": RISING, "w16e1_5k": RISING})
    rng = np.random.default_rng(7)
    bad = rng.normal(size=(N, D))
    np.savez_compressed(root / "production_m0.5_s42" / "baseline_samples.npz",
                        samples=bad)
    with pytest.raises(ValueError, match="baseline samples differ"):
        _run(root, tmp_path / "r.json")

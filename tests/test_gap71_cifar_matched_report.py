"""GAP-71 report tool — matched-NFE gating, rule 1/2, and the seed check.

The tool decides whether the published CIFAR magnitudes are retracted, so its
failure modes are pinned here: an unmatched cell must never enter the mean, and
byte-identical samples across seeds must collapse the effective n to 1.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gap71_cifar_matched_report import main

SCHED = ["CosineAnnealScheduler", "CodimensionSheetScheduler"]


def _write_cell(
    root: Path,
    *,
    arm: str,
    seed: int,
    baseline_fid: float,
    framework_fids: list[float],
    matched: bool = True,
    samples: bytes = b"unique",
) -> Path:
    cell = root / arm / f"seed{seed}"
    cell.mkdir(parents=True, exist_ok=True)
    rows = [{"name": "baseline", "fid": baseline_fid,
             "wall_clock_s": 1.0, "framework_total_nfe": 0}]
    for name, fid in zip(SCHED, framework_fids, strict=True):
        rows.append({"name": name, "fid": fid, "wall_clock_s": 1.0,
                     "framework_total_nfe": 2})
    (cell / "summary.json").write_text(json.dumps({
        "n_samples": 1000,
        "baseline_num_steps": 2,
        "match_nfe": "sample",
        "nfe_matched": matched,
        "nfe_mismatch": [] if matched else ["CosineAnnealScheduler"],
        "spectral_band_fraction": None,
        "rows": rows,
    }))
    for name in SCHED:
        (cell / f"{name}_samples.npz").write_bytes(samples)
    return cell


def _run(root: Path, out: Path) -> dict:
    main(["--root", str(root), "--seeds", "42", "43",
          "--out", str(out)])
    return json.loads(out.read_text())


def test_unmatched_cells_are_excluded_not_averaged(tmp_path: Path) -> None:
    root = tmp_path / "run"
    # seed42 is matched and shows a big regression; seed43 is unmatched and
    # would dilute it if it were averaged in.
    _write_cell(root, arm="before", seed=42, baseline_fid=100.0,
                framework_fids=[150.0, 150.0], matched=True)
    _write_cell(root, arm="before", seed=43, baseline_fid=100.0,
                framework_fids=[100.0, 100.0], matched=False)
    report = _run(root, tmp_path / "r.json")
    assert report["before"]["mean_delta_pct"] == pytest.approx(50.0)
    assert report["before"]["trail"]["excluded_unmatched"] == ["before/seed43"]


def test_retraction_and_halving_give_confirmed(tmp_path: Path) -> None:
    root = tmp_path / "run"
    # BEFORE +2 % (below the 5 % retraction line), AFTER +0.5 % (<= half).
    _write_cell(root, arm="before", seed=42, baseline_fid=100.0,
                framework_fids=[102.0, 102.0])
    _write_cell(root, arm="after", seed=42, baseline_fid=100.0,
                framework_fids=[100.5, 100.5])
    report = _run(root, tmp_path / "r.json")
    assert report["verdict"] == "BAND_STRUCTURE_CONFIRMED"


def test_retraction_without_halving_is_not_the_lever(tmp_path: Path) -> None:
    root = tmp_path / "run"
    _write_cell(root, arm="before", seed=42, baseline_fid=100.0,
                framework_fids=[102.0, 102.0])
    _write_cell(root, arm="after", seed=42, baseline_fid=100.0,
                framework_fids=[101.8, 101.8])
    report = _run(root, tmp_path / "r.json")
    assert report["verdict"] == "BAND_STRUCTURE_NOT_THE_LEVER"


def test_large_before_delta_replicates_the_regression(tmp_path: Path) -> None:
    root = tmp_path / "run"
    _write_cell(root, arm="before", seed=42, baseline_fid=100.0,
                framework_fids=[130.0, 130.0])
    _write_cell(root, arm="after", seed=42, baseline_fid=100.0,
                framework_fids=[110.0, 110.0])
    report = _run(root, tmp_path / "r.json")
    assert report["verdict"] == "REGRESSION_REPLICATES"


def test_missing_cells_are_inconclusive(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir(parents=True)
    report = _run(root, tmp_path / "r.json")
    assert report["verdict"] == "INCONCLUSIVE"


def test_identical_samples_across_seeds_collapse_to_n1(tmp_path: Path) -> None:
    root = tmp_path / "run"
    for seed in (42, 43):
        _write_cell(root, arm="before", seed=seed, baseline_fid=100.0,
                    framework_fids=[102.0, 102.0], samples=b"same-bytes")
    report = _run(root, tmp_path / "r.json")
    assert report["seed_invariance_collapsed"]
    assert "n = 1" in " ".join(report["notes"])
    for n in report["before"]["trail"]["effective_n"].values():
        assert n == 1

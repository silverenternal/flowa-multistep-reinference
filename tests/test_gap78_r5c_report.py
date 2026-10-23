"""GAP-78 R5c report — the 3-seed verdict rule, on synthetic cells.

The report is what turns twelve numbers into a cell verdict, so the rule has to
be testable without the twelve numbers. The two traps: a one-seed cell must not
be promoted (no interval), and a mean that sits inside the margin with a wide
interval is not weak dominance.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gap78_r5c_report import collect, render, report

CKPTS = ("production", "w16e1_60k")


def _write(root: Path, ckpt: str, seed: int, deltas: dict[str, float],
           *, baseline: float = 10.0) -> None:
    cell = root / f"{ckpt}_beta0.3_s{seed}"
    cell.mkdir(parents=True, exist_ok=True)
    arms = {
        arm: {
            "fid_headline": baseline * (1.0 + d / 100.0),
            "delta_vs_baseline_pct": d,
        }
        for arm, d in deltas.items()
    }
    (cell / "sweep_summary.json").write_text(json.dumps({
        "baseline_fid": baseline, "framework_arms": arms,
    }))


def _three_seeds(root: Path, ckpt: str, deltas: dict[str, float], jitter: float) -> None:
    for i, seed in enumerate((42, 43, 44)):
        sign = (-1) ** i
        _write(root, ckpt, seed, {a: d + sign * jitter for a, d in deltas.items()})


def test_collect_groups_by_checkpoint_and_arm(tmp_path: Path):
    _write(tmp_path, "production", 42, {"cosine": 0.5, "codim": -0.5})
    _write(tmp_path, "production", 43, {"cosine": 0.6, "codim": -0.4})
    got = collect(tmp_path)
    assert set(got) == {"production"}
    assert set(got["production"]) == {"cosine", "codim"}
    assert len(got["production"]["cosine"]) == 2
    assert got["production"]["cosine"][0]["headline_delta"] == pytest.approx(0.5)


def test_single_seed_is_incomplete_not_a_win(tmp_path: Path):
    _write(tmp_path, "production", 42, {"cosine": -5.0, "codim": -6.0})
    rep = report(tmp_path)
    assert rep["verdict"] == "INCOMPLETE"
    assert rep["n_strict_gain"] == 0  # no interval, so nothing is established


def test_all_cells_inside_the_margin_with_one_gain_is_a_win(tmp_path: Path):
    _three_seeds(tmp_path, "production", {"cosine": 0.2, "codim": 0.3}, 0.05)
    _three_seeds(tmp_path, "w16e1_60k", {"cosine": 0.3, "codim": 0.1}, 0.05)
    # a third checkpoint that carries the strict gain
    _three_seeds(tmp_path, "w16e1_5k", {"cosine": -12.0, "codim": -12.2}, 0.1)
    rep = report(tmp_path)
    assert rep["n_cells"] == 6
    assert rep["n_weak_dominance"] == 6
    assert rep["n_strict_gain"] == 2
    assert rep["verdict"] == "WIN"


def test_a_mean_inside_the_margin_with_a_wide_interval_is_not_dominance(tmp_path: Path):
    """+0.3 % mean, but the seeds straddle 0 and +0.6 — the CI high exceeds 1 %."""
    _write(tmp_path, "production", 42, {"cosine": 0.3})
    _write(tmp_path, "production", 43, {"cosine": 2.5})
    _write(tmp_path, "production", 44, {"cosine": -1.5})
    rep = report(tmp_path)
    row = rep["rows"][0]
    assert row["headline_mean"] == pytest.approx(0.433, abs=1e-2)
    assert row["headline_ci95"][1] > 1.0
    assert row["weak_dominance"] is False
    assert rep["verdict"] == "LOSS"


def test_all_weak_but_no_gain_is_a_tie(tmp_path: Path):
    _three_seeds(tmp_path, "production", {"cosine": 0.2, "codim": 0.3}, 0.02)
    rep = report(tmp_path)
    assert rep["n_weak_dominance"] == 2
    assert rep["n_strict_gain"] == 0
    assert rep["verdict"] == "TIE"


def test_margin_is_a_parameter(tmp_path: Path):
    _three_seeds(tmp_path, "production", {"cosine": 0.8}, 0.02)
    assert report(tmp_path, margin=0.01)["rows"][0]["weak_dominance"] is True
    assert report(tmp_path, margin=0.005)["rows"][0]["weak_dominance"] is False


def test_render_prints_every_cell_and_the_caveat(tmp_path: Path):
    _three_seeds(tmp_path, "production", {"cosine": 0.2}, 0.02)
    md = render(report(tmp_path))
    assert "| production | cosine | 3 |" in md
    assert "Caveat:" in md

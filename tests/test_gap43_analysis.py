"""GAP-43 — CPU tests for ``tools/gap43_blend_positive_analysis.py``.

Pins the frozen statistics and the pre-registered decision rule. No torch /
GPU: the analysis reads JSON only.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import stats as _st

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load():
    p = str(REPO_ROOT / "tools")
    if p not in sys.path:
        sys.path.insert(0, p)
    return importlib.import_module("gap43_blend_positive_analysis")


def _arm_doc(fg_dev: float, pb: float = 60.0, n_sampled: int = 995) -> dict:
    return {
        "n_sampled": n_sampled,
        "n_errors": 1000 - n_sampled,
        "metrics": {
            "fg_dev": fg_dev,
            "pb_validity_pct": pb,
            "validity_pct": 100.0,
            "ood_ring_rate": 0.01,
        },
    }


def _write_arm(directory: Path, arm: str, seed: int, fg_dev: float, **kw) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"flowmol3_n1000_{arm}_wave338_p5_seed{seed}.json"
    path.write_text(json.dumps(_arm_doc(fg_dev, **kw)), encoding="utf-8")


def test_paired_stats_matches_closed_form():
    mod = _load()
    d = np.asarray([-0.10, -0.05, -0.02, -0.08, -0.12, -0.03], dtype=np.float64)
    s = mod.paired_stats(d)
    mean, sd = float(d.mean()), float(d.std(ddof=1))
    se = sd / np.sqrt(d.size)
    t_stat = mean / se
    assert s["n"] == d.size
    assert s["mean"] == pytest.approx(mean, abs=1e-12)
    assert s["sd"] == pytest.approx(sd, abs=1e-12)
    assert s["t_stat"] == pytest.approx(t_stat, abs=1e-12)
    assert s["p_value"] == pytest.approx(2 * _st.t.sf(abs(t_stat), df=d.size - 1), abs=1e-12)
    assert s["cohens_dz"] == pytest.approx(mean / sd, abs=1e-12)
    assert s["ci95_mean"][0] < mean < s["ci95_mean"][1]


def test_bootstrap_is_deterministic_and_brackets_point():
    mod = _load()
    d = np.asarray([-0.10, -0.05, -0.02, -0.08, -0.12, -0.03], dtype=np.float64)
    first = mod.bootstrap_dz_ci(d)
    second = mod.bootstrap_dz_ci(d)
    assert first == second
    point = float(d.mean() / d.std(ddof=1))
    assert first[0] <= point <= first[1]


def test_verdict_requires_the_tuned_gate():
    mod = _load()
    stats = mod.paired_stats(np.full(50, -0.02) + np.linspace(-0.004, 0.004, 50))
    verdict, cond = mod._verdict(stats, {"passes": False})
    assert cond["mean_negative"] and cond["p_below_alpha"] and cond["dz_at_floor"]
    assert verdict == "MATCHED_NFE_POSITIVE_NOT_ROBUST_TO_BASELINE_TUNING"
    verdict, _ = mod._verdict(stats, {"passes": True})
    assert verdict == "POSITIVE"


def test_verdict_bounded_negative_when_effect_is_tiny():
    mod = _load()
    rng = np.random.default_rng(1)
    d = rng.normal(0.0, 1.0, 50) * 0.001
    verdict, _ = mod._verdict(mod.paired_stats(d), {"passes": False})
    assert verdict == "BOUNDED_NEGATIVE"


def test_analyze_end_to_end_on_synthetic_dirs(tmp_path: Path):
    mod = _load()
    primary = tmp_path / "primary"
    tuned = tmp_path / "tuned"
    seeds = mod.SEEDS
    tuned_seeds = mod.TUNED_SEEDS
    rng = np.random.default_rng(7)
    for seed in seeds:
        bl = 0.70
        fw = bl - 0.03 + float(rng.normal(0, 0.004))
        _write_arm(primary, "baseline", seed, bl)
        _write_arm(primary, "framework", seed, fw)
    for seed in tuned_seeds:
        _write_arm(tuned, "baseline", seed, 0.72)  # baseline@1000 is worse: gate should pass
        primary_fw = json.loads(
            (primary / f"flowmol3_n1000_framework_wave338_p5_seed{seed}.json").read_text()
        )["metrics"]["fg_dev"]
        _write_arm(tuned, "framework", seed, primary_fw)

    summary = mod.analyze(primary, tuned, seeds=seeds, tuned_seeds=tuned_seeds)
    assert summary["primary"]["n"] == len(seeds)
    assert summary["primary"]["mean"] < 0
    assert summary["tuned_gate"]["n_ok"] == len(tuned_seeds)
    assert summary["tuned_gate"]["passes"] is True
    assert summary["tuned_gate"]["framework_deterministic_on_subset"] is True
    assert summary["verdict"] in {"POSITIVE", "BOUNDED_NEGATIVE", "INCONCLUSIVE"}
    assert "GAP-43" in mod.render_markdown(summary)


def test_analyze_refuses_to_drop_missing_seeds(tmp_path: Path):
    mod = _load()
    primary = tmp_path / "primary"
    _write_arm(primary, "baseline", 55, 0.70)
    _write_arm(primary, "framework", 55, 0.68)
    with pytest.raises(SystemExit):
        mod.analyze(primary, None, seeds=(55, 65), tuned_seeds=())


def test_self_test_runs():
    mod = _load()
    assert mod._self_test() == 0

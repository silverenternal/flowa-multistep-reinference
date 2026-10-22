"""GAP-84 frontier report — §0.4–§0.6 of the pre-registration, on synthetic curves.

The frontier is expensive to measure (five models × seven rungs × three seeds),
so the thing that decides every cell's win verdict must be testable before any
run. Each test here builds a curve whose answer is known by construction and
checks that the report says exactly that — including the cases where the honest
answer is ``INCOMPLETE``.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tools.frontier_report import (
    FrontierInputError,
    build_report,
    main,
    render_markdown,
)

GRID = [3, 5, 10, 25, 50, 100, 200]
N_UNITS = 10


def _units(value: float, spread: float, seed: int) -> list[float]:
    """Ten paired unit values centred on ``value`` with a fixed spread."""
    rng = np.random.default_rng(seed)
    return list(value + spread * rng.standard_normal(N_UNITS))


def _spec(*, baseline: dict[int, float], framework: dict[int, float],
          spread: float = 0.0, direction: str = "lower_is_better",
          n_records: int = 1000, grid: list[int] | None = None,
          units: bool = True) -> dict:
    grid = grid or GRID

    def arm(values: dict[int, float], offset: int) -> dict:
        out = {}
        for i, nfe in enumerate(sorted(values)):
            payload = {"value": values[nfe]}
            if units:
                # The same offset for both arms at a rung makes the paired
                # difference exact and the CI degenerate at zero width; a
                # different offset per arm is what a real paired sample looks
                # like.
                payload["units"] = _units(values[nfe], spread, seed=offset + i)
            out[str(nfe)] = payload
        return out

    return {
        "schema": "frontier_input_v1",
        "model": "synthetic",
        "cell": "test",
        "metric": {"name": "fid", "direction": direction},
        "n_records": n_records,
        "grid": grid,
        "baseline": arm(baseline, 100),
        "framework": arm(framework, 200),
    }


def _flat(value: float, rungs: list[int] | None = None) -> dict[int, float]:
    return {n: value for n in (rungs or GRID)}


# --------------------------------------------------------------------------
# §0.5 / §0.6 verdicts
# --------------------------------------------------------------------------


def test_level_win_with_flat_baseline_is_a_win():
    """Framework strictly below the baseline at every rung, same shape."""
    spec = _spec(
        baseline={n: 10.0 for n in GRID},
        framework={n: 8.0 for n in GRID},
        spread=0.02,
    )
    rep = build_report(spec)
    assert rep["verdict"] == "WIN"
    assert rep["quotable"] is True
    assert rep["win"] is True
    assert rep["dominance"]["strict_gain_rungs"] == GRID
    # Both arms are flat, so both reach their plateau at the first rung.
    assert rep["speed"]["ratio"] == pytest.approx(1.0)


def test_identical_arms_is_a_tie_and_a_tie_is_not_a_win():
    rep = build_report(_spec(baseline=_flat(10.0), framework=_flat(10.0), spread=0.02))
    assert rep["verdict"] == "TIE"
    assert rep["win"] is False
    assert rep["dominance"]["strict_gain_rungs"] == []


def test_worse_at_one_rung_is_a_loss_even_if_everywhere_else_wins():
    fw = {n: 8.0 for n in GRID}
    fw[50] = 12.0
    rep = build_report(_spec(baseline=_flat(10.0), framework=fw, spread=0.02))
    assert rep["verdict"] == "LOSS"
    assert 50 in rep["dominance"]["violations"]
    assert rep["win"] is False


def test_speed_win_when_framework_reaches_the_plateau_at_half_the_nfe():
    """Baseline needs NFE 100 to plateau; the framework gets there at 50."""
    baseline = {3: 14.0, 5: 13.0, 10: 12.2, 25: 11.2, 50: 10.6, 100: 10.0, 200: 10.0}
    framework = {3: 12.0, 5: 11.0, 10: 10.2, 25: 10.0, 50: 10.0, 100: 10.0, 200: 10.0}
    rep = build_report(_spec(baseline=baseline, framework=framework, spread=0.02))
    assert rep["verdict"] == "WIN"
    assert rep["speed"]["baseline_plateau_nfe"] == 100
    assert rep["speed"]["nfe_to_baseline_plateau"] == 25
    assert rep["speed"]["ratio"] == pytest.approx(0.25)


def test_higher_is_better_mirrors_the_sign():
    baseline = _flat(0.40)
    framework = _flat(0.60)
    rep = build_report(_spec(baseline=baseline, framework=framework, spread=0.005,
                             direction="higher_is_better"))
    assert rep["verdict"] == "WIN"
    assert all(r["improvement"] > 0 for r in rep["rungs"])
    assert all(r["improvement_ci95"][0] <= r["improvement_ci95"][1] for r in rep["rungs"])


def test_higher_is_better_regression_is_a_loss():
    rep = build_report(_spec(baseline=_flat(0.60), framework=_flat(0.40), spread=0.005,
                             direction="higher_is_better"))
    assert rep["verdict"] == "LOSS"
    assert all(r["improvement"] < 0 for r in rep["rungs"])


# --------------------------------------------------------------------------
# §0.6 INCOMPLETE — the cases that must never be promoted
# --------------------------------------------------------------------------


def test_screen_n_is_not_quotable_and_cannot_win():
    rep = build_report(_spec(baseline=_flat(10.0), framework=_flat(8.0),
                             spread=0.02, n_records=200))
    assert rep["verdict"] == "WIN"  # the curve really is better
    assert rep["quotable"] is False
    assert rep["win"] is False  # ... but §0.3 forbids calling it a win
    assert any("SCREEN_ONLY" in c for c in rep["caveats"])


def test_missing_rung_forces_incomplete():
    spec = _spec(baseline=_flat(10.0), framework=_flat(8.0), spread=0.02)
    del spec["framework"]["50"]
    rep = build_report(spec)
    assert rep["verdict"] == "INCOMPLETE"
    assert any(r["missing"] == "framework" for r in rep["rungs"])


def test_without_units_there_is_no_ci_and_no_verdict():
    rep = build_report(_spec(baseline=_flat(10.0), framework=_flat(8.0), units=False))
    assert rep["verdict"] == "INCOMPLETE"
    assert rep["dominance"]["rungs_without_ci"] == GRID
    assert all(r["ci95"] is None for r in rep["rungs"])


def test_mismatched_unit_counts_withhold_the_ci():
    spec = _spec(baseline=_flat(10.0), framework=_flat(8.0), spread=0.02)
    spec["framework"]["50"]["units"] = spec["framework"]["50"]["units"][:-1]
    rep = build_report(spec)
    assert rep["verdict"] == "INCOMPLETE"
    rung50 = next(r for r in rep["rungs"] if r["nfe"] == 50)
    assert rung50["ci95"] is None


def test_unplateaued_baseline_is_incomplete_not_a_win():
    """The baseline is still climbing at the top of the grid."""
    baseline = {3: 20.0, 5: 18.0, 10: 16.0, 25: 14.0, 50: 12.0, 100: 10.0, 200: 8.0}
    framework = {n: v - 1.0 for n, v in baseline.items()}
    rep = build_report(_spec(baseline=baseline, framework=framework, spread=0.02))
    assert rep["verdict"] == "INCOMPLETE"
    assert any("has not plateaued" in c for c in rep["caveats"])


def test_fewer_than_five_rungs_is_incomplete():
    grid = [10, 50, 100]
    rep = build_report(_spec(baseline=_flat(10.0, grid), framework=_flat(8.0, grid),
                             spread=0.02, grid=grid))
    assert rep["verdict"] == "INCOMPLETE"


# --------------------------------------------------------------------------
# Input validation
# --------------------------------------------------------------------------


def test_rung_off_the_declared_grid_is_rejected():
    spec = _spec(baseline=_flat(10.0), framework=_flat(8.0))
    spec["baseline"]["7"] = {"value": 9.0}
    with pytest.raises(FrontierInputError):
        build_report(spec)


def test_unsorted_grid_is_rejected():
    spec = _spec(baseline=_flat(10.0), framework=_flat(8.0))
    spec["grid"] = [10, 3, 5, 25, 50, 100, 200]
    with pytest.raises(FrontierInputError):
        build_report(spec)


def test_unknown_direction_is_rejected():
    spec = _spec(baseline=_flat(10.0), framework=_flat(8.0))
    spec["metric"]["direction"] = "bigger_is_better"
    with pytest.raises(FrontierInputError):
        build_report(spec)


# --------------------------------------------------------------------------
# CLI + rendering
# --------------------------------------------------------------------------


def test_cli_writes_the_report_and_exits_zero(tmp_path: Path):
    inp = tmp_path / "in.json"
    out = tmp_path / "out.json"
    inp.write_text(json.dumps(_spec(baseline=_flat(10.0), framework=_flat(8.0),
                                    spread=0.02)))
    assert main(["--input", str(inp), "--out", str(out)]) == 0
    rep = json.loads(out.read_text())
    assert rep["schema"] == "frontier_report_v1"
    assert rep["verdict"] == "WIN"


def test_cli_exits_three_on_incomplete(tmp_path: Path):
    inp = tmp_path / "in.json"
    inp.write_text(json.dumps(_spec(baseline=_flat(10.0), framework=_flat(8.0),
                                    units=False)))
    assert main(["--input", str(inp)]) == 3


def test_cli_exits_two_on_bad_input(tmp_path: Path):
    inp = tmp_path / "in.json"
    inp.write_text(json.dumps({"schema": "nope"}))
    assert main(["--input", str(inp)]) == 2


def test_markdown_renders_every_rung_and_the_verdict():
    rep = build_report(_spec(baseline=_flat(10.0), framework=_flat(8.0), spread=0.02))
    md = render_markdown(rep)
    for n in GRID:
        assert f"| {n} |" in md
    assert "verdict **WIN**" in md

"""GAP-84 frontier input — cell discovery, seed units, missing rungs.

The traps: a rung present for two of three seeds must not silently become a
2-seed rung (it is a missing rung, and §0.2 says a missing rung is not a skipped
one), and the unit must stay on the headline scale so the CI and the delta are
the same quantity.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gap84_mnist_frontier_input import collect, main


def _cell(root: Path, ckpt: str, nfe: int, seed: int, *, base: float,
          arm_fid: float, n_records: int = 1000,
          arm: str = "evidence_driven") -> None:
    d = root / f"{ckpt}_nfe{nfe}_s{seed}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "sweep_summary.json").write_text(json.dumps({
        "n_records": n_records,
        "nfe": nfe,
        "baseline_fid": base,
        "framework_arms": {arm: {"fid_headline": arm_fid, "chunk_fids": [0.0] * 10}},
        "baseline_chunk_fids": [0.0] * 10,
    }))


def test_collect_uses_seed_units_and_headline_values(tmp_path: Path):
    for nfe, (b, f) in {3: (24.6, 22.2), 10: (24.5, 21.9), 50: (24.5, 21.4)}.items():
        for i, seed in enumerate((42, 43, 44)):
            _cell(tmp_path, "w16e1_5k", nfe, seed, base=b + i * 0.01,
                  arm_fid=f + i * 0.01)
    spec = collect(tmp_path, "w16e1_5k", "evidence_driven")
    assert spec["grid"] == [3, 10, 50]
    assert spec["units_kind"] == "seed"
    assert spec["seeds"] == [42, 43, 44]
    assert spec["n_records"] == 1000
    b3 = spec["baseline"]["3"]
    assert len(b3["units"]) == 3
    assert b3["value"] == pytest.approx(sum(b3["units"]) / 3)
    assert spec["framework"]["3"]["value"] < spec["baseline"]["3"]["value"]
    assert spec["missing_rungs"] == []


def test_partial_seed_coverage_is_a_missing_rung(tmp_path: Path):
    for seed in (42, 43, 44):
        _cell(tmp_path, "w16e1_5k", 3, seed, base=24.6, arm_fid=22.2)
    for seed in (42, 43):  # 44 never finished NFE=10
        _cell(tmp_path, "w16e1_5k", 10, seed, base=24.5, arm_fid=21.9)
    spec = collect(tmp_path, "w16e1_5k", "evidence_driven")
    assert spec["grid"] == [3, 10]
    assert spec["missing_rungs"] == [10]
    assert "10" not in spec["baseline"]
    assert "10" not in spec["framework"]


def test_unknown_arm_is_refused(tmp_path: Path):
    _cell(tmp_path, "production", 3, 42, base=11.0, arm_fid=11.0)
    with pytest.raises(SystemExit):
        collect(tmp_path, "production", "cosine")


def test_n_records_mismatch_is_refused(tmp_path: Path):
    _cell(tmp_path, "production", 3, 42, base=11.0, arm_fid=11.0)
    _cell(tmp_path, "production", 3, 43, base=11.0, arm_fid=11.0, n_records=200)
    with pytest.raises(SystemExit):
        collect(tmp_path, "production", "evidence_driven")


def test_no_cells_is_refused(tmp_path: Path):
    with pytest.raises(SystemExit):
        collect(tmp_path, "missing_ckpt", "evidence_driven")


def test_cli_writes_spec(tmp_path: Path):
    for nfe in (3, 10, 50):
        for seed in (42, 43, 44):
            _cell(tmp_path, "w16e1_5k", nfe, seed, base=24.5, arm_fid=21.5)
    out = tmp_path / "spec.json"
    rc = main(["--root", str(tmp_path), "--ckpt", "w16e1_5k",
               "--arm", "evidence_driven", "--out", str(out)])
    assert rc == 0
    spec = json.loads(out.read_text())
    assert spec["schema"] == "frontier_input_v1"
    assert spec["metric"]["direction"] == "lower_is_better"
    assert spec["grid"] == [3, 10, 50]

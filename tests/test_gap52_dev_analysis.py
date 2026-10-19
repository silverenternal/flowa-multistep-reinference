"""GAP-52 — the dev-screen selection rule is applied exactly as pre-registered."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gap52_dev_analysis import ARMS, REFERENCE, screen

SEEDS = list(range(1000, 1100, 10))


def _write_arm(root: Path, arm: str, deltas: list[float]) -> None:
    directory = root / arm
    directory.mkdir(parents=True)
    for seed, delta in zip(SEEDS, deltas, strict=True):
        base = 0.60
        for name, value in (("baseline", base), ("framework", base + delta)):
            payload = {
                "metrics": {"fg_dev": value, "pb_validity_pct": 0.5},
                "seed_base": seed,
                "arm": name,
            }
            (directory / f"flowmol3_n1000_{name}_wave338_p5_seed{seed}.json").write_text(
                json.dumps(payload)
            )


def test_winner_is_the_lowest_mean_that_beats_reference(tmp_path: Path) -> None:
    _write_arm(tmp_path, "C0_continuous_flat", [0.02] * 10)
    _write_arm(tmp_path, "C1_categorical_flat", [0.01] * 10)
    _write_arm(tmp_path, "C2_categorical_perchannel", [-0.03] * 10)
    _write_arm(tmp_path, "C3_continuous_perchannel", [0.05] * 10)
    out = screen(tmp_path)
    assert out["winner"] == "C2_categorical_perchannel"
    assert out["proceed_to_confirm"] is True
    assert out["survivors"] == ["C1_categorical_flat", "C2_categorical_perchannel"]


def test_no_arm_beats_reference_returns_null(tmp_path: Path) -> None:
    _write_arm(tmp_path, "C0_continuous_flat", [0.01] * 10)
    for arm in ARMS:
        if arm != REFERENCE:
            _write_arm(tmp_path, arm, [0.02] * 10)
    out = screen(tmp_path)
    assert out["winner"] is None
    assert out["proceed_to_confirm"] is False
    assert out["survivors"] == []


def test_missing_seed_is_fatal(tmp_path: Path) -> None:
    _write_arm(tmp_path, "C0_continuous_flat", [0.01] * 10)
    for arm in ARMS:
        if arm != REFERENCE:
            _write_arm(tmp_path, arm, [0.02] * 10)
    victim = next((tmp_path / "C1_categorical_flat").glob("*framework*seed1000.json"))
    victim.unlink()
    with pytest.raises(SystemExit):
        screen(tmp_path)

"""GAP-53 — the round-count loop keeps the total NFE fixed.

The contraction argument is only meaningful at fixed compute: R rounds must
split the same total NFE, not multiply it. These CPU tests pin the split and
the CLI guards without touching torch or the GPU.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_driver():
    for p in (str(REPO_ROOT), str(REPO_ROOT / "scripts")):
        if p not in sys.path:
            sys.path.insert(0, p)
    return importlib.import_module("wave338_p5_r3_n1000_paired")


@pytest.mark.parametrize(
    "total,rounds",
    [(250, 1), (250, 2), (250, 3), (250, 4), (251, 3), (1, 4), (1000, 7)],
)
def test_split_preserves_total(total: int, rounds: int) -> None:
    mod = _load_driver()
    parts = mod._split_nfe(total, rounds)
    assert len(parts) == rounds
    assert sum(parts) == total
    assert all(p >= 0 for p in parts)


def test_single_round_is_the_legacy_path() -> None:
    mod = _load_driver()
    assert mod._split_nfe(250, 1) == [250]


def test_remainder_goes_to_the_last_round() -> None:
    mod = _load_driver()
    assert mod._split_nfe(251, 3) == [83, 83, 85]


def test_rounds_requires_the_real_blend() -> None:
    mod = _load_driver()
    with pytest.raises(SystemExit):
        mod.main(["--restart-rounds", "2", "--seeds", "1000"])


def test_rounds_must_be_positive() -> None:
    mod = _load_driver()
    with pytest.raises(SystemExit):
        mod.main(["--restart-rounds", "0", "--seeds", "1000"])

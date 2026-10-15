"""GAP-36 — consolidated ablation matrix builder.

``tools/gap36_ablation_matrix.py`` aggregates two already-committed matched-NFE
runs (R5b rounds x schedulers; R5c checkpoints x schedulers) into one 24-row
table. These CPU tests pin the contract — row count, the verdict rule, and the
per-cell statistical unit — without touching torch / the GPU.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_VO = REPO_ROOT / "verification_outputs"


def _load_builder():
    """Import ``tools/gap36_ablation_matrix`` (stdlib-only at import)."""
    p = str(REPO_ROOT / "tools")
    if p not in sys.path:
        sys.path.insert(0, p)
    return importlib.import_module("gap36_ablation_matrix")


def test_verdict_rule() -> None:
    mod = _load_builder()
    v = mod._verdict
    # within tie band -> tie, regardless of p
    assert v(0.10, 1e-9) == "tie"
    assert v(-0.40, 1e-9) == "tie"
    # beyond band but not significant -> n.s.
    assert v(3.0, 0.20) == "n.s."
    assert v(-3.0, 0.06) == "n.s."
    # beyond band and significant -> wins by sign
    assert v(-25.0, 1e-6) == "framework_wins"
    assert v(+5.0, 0.01) == "baseline_wins"


def test_matrix_has_24_rows() -> None:
    mod = _load_builder()
    if not mod.ROUNDS_SCHED_SRC.exists() or not mod.CKPT_SCHED_SRC.exists():
        pytest.skip("GAP-36 source runs not present")
    rows = mod.build()
    assert len(rows) == 24
    assert sum(r["cell"] == "R5b" for r in rows) == 12
    assert sum(r["cell"] == "R5c" for r in rows) == 12


def test_stat_unit_is_per_cell() -> None:
    mod = _load_builder()
    if not mod.ROUNDS_SCHED_SRC.exists() or not mod.CKPT_SCHED_SRC.exists():
        pytest.skip("GAP-36 source runs not present")
    rows = mod.build()
    for r in rows:
        if r["cell"] == "R5b":
            assert r["stat_unit"] == "per_sample_feature_distance"
        else:
            assert r["stat_unit"] == "paired_chunk"
        assert r["nfe"] == 50  # matched-NFE control preserved


def test_decisive_cell_is_scheduler_insensitive() -> None:
    """w16e1_5k wins on every scheduler (GAP-35 corroborated in one table)."""
    mod = _load_builder()
    if not mod.CKPT_SCHED_SRC.exists():
        pytest.skip("GAP-36 source run not present")
    rows = [r for r in mod.build() if r["checkpoint"] == "w16e1_5k"]
    assert len(rows) == 3
    assert all(r["verdict"] == "framework_wins" for r in rows)
    assert all(r["mean_delta_pct"] < -20.0 for r in rows)


def test_md_table_has_stat_unit_column() -> None:
    mod = _load_builder()
    if not mod.ROUNDS_SCHED_SRC.exists() or not mod.CKPT_SCHED_SRC.exists():
        pytest.skip("GAP-36 source runs not present")
    md = mod._md_table(mod.build())
    header = md.splitlines()[0]
    assert "stat_unit" in header
    assert len(md.splitlines()) == 2 + 24  # header + sep + 24 rows

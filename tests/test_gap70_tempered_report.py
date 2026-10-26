"""GAP-70 round 2 — the tempered-draw report's decision logic.

The report is the acceptance instrument for ``docs/audit/gap70-r2-tempered-draw.md``,
so the verdict has to be pinned by fixtures rather than by the real run: a
segment point cannot win, and only a frontier that bulges above the chord can.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gap70_tempered_report import main

N = 10
FAMILY = "PF00005.27"


def _write_fasta(path: Path, prefix: str, n: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in range(n):
        lines.append(f">{prefix}_seed{i}|family={FAMILY}")
        lines.append("MKAVL" + "A" * (i % 3))
    path.write_text("\n".join(lines) + "\n")


def _write_m8(path: Path, prefix: str, novel: list[bool]) -> None:
    """Novel records get no hit at all; non-novel ones get a 90 % identity hit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, is_novel in enumerate(novel):
        if is_novel:
            continue
        qid = f"{prefix}_seed{i}|family={FAMILY}"
        fields = [qid, "PF00005.27", "0.900"] + ["0"] * 9
        lines.append("\t".join(fields))
    path.write_text("\n".join(lines) + ("\n" if lines else ""))


def _write_validity(path: Path, prefix: str, hit: list[bool]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        json.dumps(
            {
                "header": f"{prefix}_seed{i}|family={FAMILY}",
                "family": FAMILY,
                "has_any_hit": bool(h),
            }
        )
        for i, h in enumerate(hit)
    ]
    path.write_text("\n".join(rows) + "\n")


def _arm(
    root: Path,
    lam: float,
    *,
    novel: list[bool],
    hit: list[bool],
) -> None:
    d = root / f"lam{lam:g}"
    _write_fasta(d / "framework.fasta", "framework", N)
    _write_m8(root / "m8" / f"lam{lam:g}.m8", "framework", novel)
    _write_validity(
        d / "upstream_framework" / "family_validity_per_seq.jsonl",
        "framework",
        hit,
    )


def _baseline(root: Path, *, novel: list[bool], hit: list[bool]) -> None:
    d = root / "lam0"
    _write_fasta(d / "baseline.fasta", "baseline", N)
    _write_m8(root / "m8" / "baseline.m8", "baseline", novel)
    _write_validity(
        d / "upstream_baseline" / "family_validity_per_seq.jsonl",
        "baseline",
        hit,
    )


def _run(root: Path, tmp_path: Path) -> dict:
    out = tmp_path / "report.json"
    assert main(
        [
            "--root", str(root),
            "--lams", "0 0.5 1",
            "--n-total", str(N),
            "--out", str(out),
        ]
    ) == 0
    return json.loads(out.read_text())


def test_a_monotone_trade_is_not_a_win(tmp_path: Path) -> None:
    """Novelty falls and validity rises along the segment: nothing wins."""
    root = tmp_path / "run"
    base_novel = [True] * 8 + [False] * 2
    base_hit = [True] * 2 + [False] * 8
    _baseline(root, novel=base_novel, hit=base_hit)
    _arm(root, 0.0, novel=base_novel, hit=base_hit)
    _arm(
        root,
        0.5,
        novel=[True] * 5 + [False] * 5,
        hit=[True] * 5 + [False] * 5,
    )
    _arm(
        root,
        1.0,
        novel=[True] + [False] * 9,
        hit=[True] * 8 + [False] * 2,
    )
    rep = _run(root, tmp_path)
    assert rep["verdict"] == "TRADE_IS_INTRINSIC"
    assert rep["selected_lambda"] is None
    row = next(r for r in rep["rows"] if r["lam"] == 0.5)
    assert row["wins"] is False


def test_a_frontier_above_the_chord_wins(tmp_path: Path) -> None:
    """An interior lam that keeps baseline novelty and the lam=1 validity."""
    root = tmp_path / "run"
    _baseline(root, novel=[True] * 6 + [False] * 4, hit=[True] * 2 + [False] * 8)
    _arm(
        root,
        0.0,
        novel=[True] * 6 + [False] * 4,
        hit=[True] * 2 + [False] * 8,
    )
    _arm(
        root,
        0.5,
        novel=[True] * 10,
        hit=[True] * 8 + [False] * 2,
    )
    _arm(
        root,
        1.0,
        novel=[True] + [False] * 9,
        hit=[True] * 8 + [False] * 2,
    )
    rep = _run(root, tmp_path)
    assert rep["verdict"] == "TEMPERED_DRAW_WINS"
    assert rep["selected_lambda"] == pytest.approx(0.5)
    row = next(r for r in rep["rows"] if r["lam"] == 0.5)
    assert row["above_chord_novelty"] and row["above_chord_validity"]


def test_the_two_ends_are_required(tmp_path: Path) -> None:
    root = tmp_path / "run"
    _baseline(root, novel=[True] * 5 + [False] * 5, hit=[False] * N)
    _arm(root, 0.0, novel=[True] * 5 + [False] * 5, hit=[False] * N)
    _arm(root, 0.5, novel=[True] * 5 + [False] * 5, hit=[False] * N)
    with pytest.raises(SystemExit):
        main(
            [
                "--root", str(root),
                "--lams", "0 0.5",
                "--n-total", str(N),
                "--out", str(tmp_path / "r.json"),
            ]
        )


def test_a_missing_arm_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "run"
    _baseline(root, novel=[True] * 5 + [False] * 5, hit=[False] * N)
    _arm(root, 0.0, novel=[True] * 5 + [False] * 5, hit=[False] * N)
    # lam=1 is declared but never written.
    with pytest.raises(SystemExit):
        main(
            [
                "--root", str(root),
                "--lams", "0 1",
                "--n-total", str(N),
                "--out", str(tmp_path / "r.json"),
            ]
        )

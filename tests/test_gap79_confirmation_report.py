"""GAP-79 confirmation report — the §3.5 table, pinned on synthetic cells.

The tool is written before the confirmation run exists, so these tests are the
only thing that fixes its behaviour: pairing by ``qid``, the two intervals
(record bootstrap and seed t), the "weaker lower bound" verdict rule, and the
fail-closed paths.

Pre-registration: ``docs/audit/gap79-r1-family-lever.md`` §3.5 + §3.9.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gap79_confirmation_report import build, paired_diffs  # noqa: E402

FAMILIES = ("PF00005", "PF00072", "PF00183", "PF02517")


def _rec(qid: int, fam: str, hit: bool) -> dict:
    return {
        "qid": f"q{qid}",
        "intended_family": fam,
        "intended_family_canon": fam,
        "intended_hit_evalue": hit,
    }


def _write_cell(root: Path, seed: int, tag: str, hits: dict[str, int], n: int = 50) -> None:
    """Write one cell: per-family ``hits`` out of ``n`` records + a FASTA."""
    out = root / f"seed{seed}" / tag / "upstream_framework"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    qid = 0
    for fam in FAMILIES:
        for i in range(n):
            rows.append(_rec(qid, fam, i < hits.get(fam, 0)))
            qid += 1
    (out / "family_validity_per_seq.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n"
    )
    # Diversity: unique random sequences, same length, same alphabet.
    import random

    rng = random.Random(seed * 1000 + (0 if tag == "control" else 1))
    seqs = [
        "".join(rng.choice("ACDEFGHIKLMNPQRSTVWY") for _ in range(60))
        for _ in range(len(rows))
    ]
    (root / f"seed{seed}" / tag / "framework.fasta").write_text(
        "\n".join(f">s{i}|family=x\n{s}" for i, s in enumerate(seqs)) + "\n"
    )


def _cell(root: Path, seed: int, tag: str, **hits: int) -> None:
    _write_cell(root, seed, tag, hits)


def test_pairing_is_by_qid_and_requires_the_same_set() -> None:
    ctrl = [_rec(0, "PF00005", True), _rec(1, "PF00072", False)]
    treat = [_rec(0, "PF00005", True), _rec(1, "PF00072", True)]
    out = paired_diffs(ctrl, treat)
    assert out["PF00072"]["diffs"] == [1]
    assert out["PF00072"]["control_hits"] == 0
    assert out["PF00072"]["treatment_hits"] == 1
    with pytest.raises(SystemExit, match="qid_sets_differ"):
        paired_diffs(ctrl, treat[:1])


def test_consistent_improvement_across_seeds_is_a_win(tmp_path) -> None:
    for seed in (42, 43, 44):
        _cell(tmp_path, seed, "control", PF00005=5, PF00072=0, PF00183=0, PF02517=0)
        _cell(tmp_path, seed, "W8", PF00005=5, PF00072=20, PF00183=15, PF02517=10)
    rep = build(tmp_path, 8.0, [42, 43, 44])
    assert rep["verdict"]["win"] is True
    assert rep["families"]["PF00072"]["improved"] is True
    # The guard family is unchanged, so its interval is exactly zero.
    assert rep["families"]["PF00005"]["seed_ci"]["mean"] == 0.0
    assert rep["verdict"]["guard_family_ok"] is True


def test_improvement_in_one_seed_only_is_not_a_win(tmp_path) -> None:
    for seed in (42, 43, 44):
        _cell(tmp_path, seed, "control", PF00005=5, PF00072=0, PF00183=0, PF02517=0)
        boost = 20 if seed == 42 else 0
        _cell(tmp_path, seed, "W8", PF00005=5, PF00072=boost, PF00183=15, PF02517=10)
    rep = build(tmp_path, 8.0, [42, 43, 44])
    assert rep["families"]["PF00072"]["seed_ci"]["mean"] > 0
    # One improving seed out of three: the seed interval must straddle zero.
    assert rep["families"]["PF00072"]["seed_ci"]["ci_low"] < 0
    assert rep["families"]["PF00072"]["improved"] is False
    assert rep["verdict"]["win"] is False


def test_guard_regression_blocks_the_win(tmp_path) -> None:
    for seed in (42, 43, 44):
        _cell(tmp_path, seed, "control", PF00005=20, PF00072=0, PF00183=0, PF02517=0)
        _cell(tmp_path, seed, "W8", PF00005=5, PF00072=20, PF00183=15, PF02517=10)
    rep = build(tmp_path, 8.0, [42, 43, 44])
    assert rep["families"]["PF00005"]["seed_ci"]["mean"] < 0
    assert rep["verdict"]["guard_family_ok"] is False
    assert rep["verdict"]["win"] is False


def test_verdict_uses_the_weaker_interval(tmp_path) -> None:
    """``effective_ci_low`` is the min of the two lower bounds, always."""
    for seed in (42, 43, 44):
        _cell(tmp_path, seed, "control", PF00005=5, PF00072=0, PF00183=0, PF02517=0)
        _cell(tmp_path, seed, "W8", PF00005=5, PF00072=20, PF00183=15, PF02517=10)
    rep = build(tmp_path, 8.0, [42, 43, 44])
    for row in rep["families"].values():
        assert row["effective_ci_low"] == min(
            row["seed_ci"]["ci_low"], row["record_ci"]["ci_low"]
        )


def test_missing_cell_fails_closed(tmp_path) -> None:
    _cell(tmp_path, 42, "control", PF00005=5)
    with pytest.raises(SystemExit, match="missing_cell"):
        build(tmp_path, 8.0, [42])

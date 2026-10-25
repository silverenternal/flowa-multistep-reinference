"""GAP-79 dose screen — the table §0.4 rule 2 reads, and the rule itself."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gap79_dose_screen import (  # noqa: E402
    build,
    per_family,
    screen_verdict,
)

FAMILIES = ("PF00005", "PF00072", "PF00183", "PF02517")


def _write_arm(
    run_dir: Path,
    arm: str,
    *,
    hits: dict[str, int],
    n_per_family: int = 5,
) -> None:
    out = run_dir / f"upstream_{arm}"
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    qid = 0
    for fam in FAMILIES:
        for i in range(n_per_family):
            qid += 1
            lines.append(
                json.dumps(
                    {
                        "qid": f"q{qid}",
                        "intended_family": f"{fam}.1",
                        "intended_family_canon": fam,
                        "intended_hit_evalue": i < hits.get(fam, 0),
                    }
                )
            )
    (out / "family_validity_per_seq.jsonl").write_text("\n".join(lines) + "\n")
    (out / "family_validity.json").write_text(
        json.dumps({"hmmscan_total_hits": 7, "coverage_any_hit": 0.5})
    )


def _dose(root: Path, temp: float, *, fw: dict[str, int], base: dict[str, int]) -> Path:
    run_dir = root / f"seed42_T{temp}"
    _write_arm(run_dir, "baseline", hits=base)
    _write_arm(run_dir, "framework", hits=fw)
    return run_dir


def test_per_family_counts_hits_and_rates() -> None:
    got = per_family(
        [
            {"intended_family_canon": "PF00005", "intended_hit_evalue": True},
            {"intended_family_canon": "PF00005", "intended_hit_evalue": False},
            {"intended_family_canon": "PF00072", "intended_hit_evalue": False},
        ]
    )
    assert got["PF00005"] == {"n": 2, "hits": 1, "rate": 0.5}
    assert got["PF00072"]["hits"] == 0


def test_verdict_requires_both_families_and_the_guard(tmp_path: Path) -> None:
    ok = _dose(
        tmp_path, 0.2,
        fw={"PF00005": 5, "PF00072": 1, "PF02517": 1},
        base={"PF00005": 5},
    )
    block = {
        "baseline": {"per_family": per_family(
            [json.loads(x) for x in
             (ok / "upstream_baseline" / "family_validity_per_seq.jsonl")
             .read_text().splitlines()])},
        "framework": {"per_family": per_family(
            [json.loads(x) for x in
             (ok / "upstream_framework" / "family_validity_per_seq.jsonl")
             .read_text().splitlines()])},
    }
    v = screen_verdict(block)
    assert v["eligible"] is True
    assert v["required_all_nonzero"] is True
    assert v["guard_ok"] is True


def test_guard_loss_disqualifies_a_dose(tmp_path: Path) -> None:
    run = _dose(
        tmp_path, 0.1,
        fw={"PF00005": 2, "PF00072": 3, "PF02517": 3},
        base={"PF00005": 5},
    )
    fw = per_family([json.loads(x) for x in
                     (run / "upstream_framework" / "family_validity_per_seq.jsonl")
                     .read_text().splitlines()])
    base = per_family([json.loads(x) for x in
                       (run / "upstream_baseline" / "family_validity_per_seq.jsonl")
                       .read_text().splitlines()])
    v = screen_verdict({"framework": {"per_family": fw}, "baseline": {"per_family": base}})
    assert v["required_all_nonzero"] is True
    assert v["guard_ok"] is False
    assert v["eligible"] is False


def test_selection_takes_the_largest_eligible_temperature(tmp_path: Path) -> None:
    _dose(tmp_path, 0.5, fw={"PF00005": 5, "PF00072": 2, "PF02517": 2}, base={"PF00005": 5})
    _dose(tmp_path, 0.1, fw={"PF00005": 5, "PF00072": 3, "PF02517": 3}, base={"PF00005": 5})
    _dose(tmp_path, 0.02, fw={"PF00005": 5, "PF00072": 4, "PF02517": 4}, base={"PF00005": 5})
    report = build(tmp_path, 42)
    assert [d["temperature"] for d in report["doses"]] == [0.02, 0.1, 0.5]
    # 0.5 is the smallest dose (T closest to 1) that still qualifies.
    assert report["selected_temperature"] == 0.5
    assert report["falsified"] is False


def test_no_eligible_dose_is_a_falsification(tmp_path: Path) -> None:
    _dose(tmp_path, 0.5, fw={"PF00005": 5}, base={"PF00005": 5})
    _dose(tmp_path, 0.1, fw={"PF00005": 5}, base={"PF00005": 5})
    report = build(tmp_path, 42)
    assert report["selected_temperature"] is None
    assert report["falsified"] is True


def test_missing_arm_is_fail_closed(tmp_path: Path) -> None:
    run = tmp_path / "seed42_T0.2"
    _write_arm(run, "baseline", hits={"PF00005": 5})
    with pytest.raises(SystemExit) as exc:
        build(tmp_path, 42)
    assert "missing_per_seq" in str(exc.value)

"""GAP-79 lever-3 screen — the table §3.4 reads, and the rule itself."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gap79_guidance_screen import (  # noqa: E402
    build,
    diversity,
    read_fasta,
    verdict,
)

FAMILIES = ("PF00005", "PF00072", "PF00183", "PF02517")
N_PER_FAMILY = 5


def _seqs(n: int, *, seed: int = 0, width: int = 6) -> list[str]:
    """Distinct, high-entropy sequences (no collapse)."""
    alphabet = "ACDEFGHIKLMNPQRSTVWY"
    return [
        "".join(alphabet[(i * 7 + j * 3 + seed) % len(alphabet)]
                for j in range(width))
        for i in range(n)
    ]


def _write_cell(
    run_dir: Path,
    *,
    hits: dict[str, int],
    seqs: list[str] | None = None,
) -> None:
    out = run_dir / "upstream_framework"
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    qid = 0
    for fam in FAMILIES:
        for i in range(N_PER_FAMILY):
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
    records = seqs or _seqs(4 * N_PER_FAMILY)
    (run_dir / "framework.fasta").write_text(
        "".join(f">s{i}\n{s}\n" for i, s in enumerate(records))
    )


def _control(root: Path, *, hits: dict[str, int] | None = None) -> None:
    _write_cell(root / "control", hits=hits or {"PF00005": 3})


def _dose(root: Path, weight: float, *, hits: dict[str, int],
          seqs: list[str] | None = None) -> None:
    _write_cell(root / f"W{weight}", hits=hits, seqs=seqs)


def test_fasta_reader_rejects_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="missing_fasta"):
        read_fasta(tmp_path / "nope.fasta")


def test_diversity_is_one_for_distinct_sequences() -> None:
    got = diversity(_seqs(20))
    assert got["unique_fraction"] == 1.0
    assert got["mean_positional_entropy_bits"] > 0.0


def test_diversity_collapses_for_identical_sequences() -> None:
    got = diversity(["ACDEFG"] * 10)
    assert got["unique_fraction"] == pytest.approx(0.1)
    assert got["mean_positional_entropy_bits"] == pytest.approx(0.0)


def test_eligible_dose_needs_both_families_and_the_guard(tmp_path: Path) -> None:
    _control(tmp_path, hits={"PF00005": 3})
    _dose(tmp_path, 2.0, hits={"PF00005": 3, "PF00072": 1, "PF02517": 1})
    report = build(tmp_path)
    dose = report["doses"][0]
    assert dose["verdict"]["eligible"] is True
    assert report["selected_weight"] == 2.0
    assert report["falsified"] is False


def test_guard_loss_disqualifies_a_dose(tmp_path: Path) -> None:
    _control(tmp_path, hits={"PF00005": 3})
    # Two hits short of the control — beyond the one-sequence allowance.
    _dose(tmp_path, 2.0, hits={"PF00005": 1, "PF00072": 2, "PF02517": 2})
    dose = build(tmp_path)["doses"][0]
    assert dose["verdict"]["required_all_nonzero"] is True
    assert dose["verdict"]["guard_ok"] is False
    assert dose["verdict"]["eligible"] is False


def test_one_sequence_guard_allowance_is_not_a_loss(tmp_path: Path) -> None:
    _control(tmp_path, hits={"PF00005": 3})
    _dose(tmp_path, 2.0, hits={"PF00005": 2, "PF00072": 1, "PF02517": 1})
    assert build(tmp_path)["doses"][0]["verdict"]["guard_ok"] is True


def test_collapse_to_the_consensus_disqualifies_a_dose(tmp_path: Path) -> None:
    _control(tmp_path, hits={"PF00005": 3})
    # Identity improves, but every record is the same sequence.
    _dose(tmp_path, 8.0,
          hits={"PF00005": 3, "PF00072": 2, "PF02517": 2},
          seqs=["ACDEFGHIKL"] * 20)
    dose = build(tmp_path)["doses"][0]
    assert dose["verdict"]["required_all_nonzero"] is True
    assert dose["verdict"]["unique_ok"] is False
    assert dose["verdict"]["eligible"] is False


def test_selection_takes_the_smallest_eligible_weight(tmp_path: Path) -> None:
    _control(tmp_path, hits={"PF00005": 3})
    _dose(tmp_path, 0.5, hits={"PF00005": 3})
    _dose(tmp_path, 2.0, hits={"PF00005": 3, "PF00072": 1, "PF02517": 1})
    _dose(tmp_path, 32.0, hits={"PF00005": 3, "PF00072": 3, "PF02517": 3})
    report = build(tmp_path)
    assert [d["weight"] for d in report["doses"]] == [0.5, 2.0, 32.0]
    assert report["selected_weight"] == 2.0


def test_no_eligible_dose_is_a_falsification(tmp_path: Path) -> None:
    _control(tmp_path, hits={"PF00005": 3})
    _dose(tmp_path, 0.5, hits={"PF00005": 3})
    _dose(tmp_path, 2.0, hits={"PF00005": 3})
    report = build(tmp_path)
    assert report["selected_weight"] is None
    assert report["falsified"] is True


def test_missing_control_is_fail_closed(tmp_path: Path) -> None:
    _dose(tmp_path, 2.0, hits={"PF00005": 3})
    with pytest.raises(SystemExit, match="missing_control_cell"):
        build(tmp_path)


def test_verdict_reads_the_control_per_family_counts(tmp_path: Path) -> None:
    """The guard compares against the control cell, not the bare-RNG arm."""
    _control(tmp_path, hits={"PF00005": 4})
    _dose(tmp_path, 2.0, hits={"PF00005": 4, "PF00072": 1, "PF02517": 1})
    control = build(tmp_path)["control"]
    dose = build(tmp_path)["doses"][0]
    assert dose["verdict"]["guard_control_hits"] == 4
    assert control["per_family"]["PF00005"]["hits"] == 4
    assert verdict(
        {"per_family": dose["per_family"], "diversity": dose["diversity"]},
        control,
    )["eligible"] is True

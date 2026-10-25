"""GAP-69 per-family decomposition — the rule the acceptance test reads.

The trap this tool exists for: the aggregate can fire while one family sits
below the control, and the pre-registration requires both. So the tests pin
(a) grouping by `intended_family_canon`, (b) the per-seed flag, (c) the
across-seed flag when a family is below in only one seed, and (d) the four
verdict labels.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gap69_per_family import (
    across_seeds,
    analyse_seed,
    main,
    verdict,
)


def _rec(qid: str, fam: str, n_hits: int, length: int = 90) -> dict:
    return {
        "qid": qid,
        "header": f"{qid}|family={fam}",
        "length": length,
        "intended_family_canon": fam,
        "hits": [{"family": fam, "score": 10.0, "evalue": 0.1}] * n_hits,
    }


def _write_run(root: Path, arm: str, records: list[dict]) -> None:
    d = root / f"upstream_{arm}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "family_validity_per_seq.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records) + "\n"
    )


def _make_pair(root: Path, hits_c: list[int], hits_b: list[int], hits_a: list[int],
               *, fams: list[str]) -> tuple[Path, Path]:
    prof = root / "profile"
    init = root / "init"
    qids = [f"q{i}" for i in range(len(hits_c))]
    recs_c = [_rec(q, f, h) for q, f, h in zip(qids, fams, hits_c, strict=True)]
    recs_b = [_rec(q, f, h) for q, f, h in zip(qids, fams, hits_b, strict=True)]
    recs_a = [_rec(q, f, h) for q, f, h in zip(qids, fams, hits_a, strict=True)]
    _write_run(prof, "framework", recs_c)
    _write_run(init, "framework", recs_b)
    _write_run(prof, "baseline", recs_a)
    _write_run(init, "baseline", recs_a)
    return prof, init


def test_groups_by_family_and_computes_ratio(tmp_path: Path):
    # 2 records in PF00005 (C much larger), 2 in PF00072 (C smaller)
    prof, init = _make_pair(
        tmp_path,
        hits_c=[10, 10, 1, 1],
        hits_b=[1, 1, 2, 2],
        hits_a=[1, 1, 2, 2],
        fams=["PF00005", "PF00005", "PF00072", "PF00072"],
    )
    out = analyse_seed(prof, init, n_boot=200)
    assert set(out["families"]) == {"PF00005", "PF00072"}
    assert out["families"]["PF00005"]["n"] == 2
    assert out["families"]["PF00005"]["ratio_C_over_B"] == pytest.approx(20 / 2)
    assert out["families"]["PF00072"]["ratio_C_over_B"] == pytest.approx(2 / 4)
    assert out["families"]["PF00072"]["at_or_above_B"] is False
    assert out["every_family_at_or_above_B"] is False
    assert out["n_families_below_B"] == 1


def test_aggregate_and_pf00005_exclusion(tmp_path: Path):
    prof, init = _make_pair(
        tmp_path,
        hits_c=[10, 1, 1],
        hits_b=[1, 2, 2],
        hits_a=[1, 2, 2],
        fams=["PF00005", "PF00072", "PF00183"],
    )
    out = analyse_seed(prof, init, n_boot=200)
    assert out["aggregate"]["hits_B_init_only"] == 5
    assert out["aggregate"]["hits_C_conservation"] == 12
    excl = out["excluding_PF00005"]
    assert excl["hits_B_init_only"] == 4
    assert excl["hits_C_conservation"] == 2
    assert excl["families"] == ["PF00072", "PF00183"]


def test_zero_denominator_gives_none_ratio(tmp_path: Path):
    prof, init = _make_pair(
        tmp_path, hits_c=[3, 0], hits_b=[0, 0], hits_a=[0, 0],
        fams=["PF00005", "PF00005"],
    )
    out = analyse_seed(prof, init, n_boot=200)
    assert out["families"]["PF00005"]["ratio_C_over_B"] is None
    assert out["families"]["PF00005"]["at_or_above_B"] is False


def test_length_mismatch_is_refused(tmp_path: Path):
    prof, init = _make_pair(
        tmp_path, hits_c=[1], hits_b=[1], hits_a=[1], fams=["PF00005"],
    )
    path = init / "upstream_framework" / "family_validity_per_seq.jsonl"
    rec = json.loads(path.read_text().strip())
    rec["length"] = 91
    path.write_text(json.dumps(rec) + "\n")
    with pytest.raises(SystemExit):
        analyse_seed(prof, init, n_boot=50)


def test_across_seeds_flags_family_below_in_one_seed(tmp_path: Path):
    per_seed = {
        "42": {
            "families": {
                "PF00005": {"ratio_C_over_B": 20.0, "delta_per_record_vs_B": 5.0,
                            "at_or_above_B": True},
                "PF00072": {"ratio_C_over_B": 0.8, "delta_per_record_vs_B": -0.1,
                            "at_or_above_B": False},
            },
            "aggregate": {"ratio_C_over_B": 8.0},
        },
        "43": {
            "families": {
                "PF00005": {"ratio_C_over_B": 22.0, "delta_per_record_vs_B": 6.0,
                            "at_or_above_B": True},
                "PF00072": {"ratio_C_over_B": 1.1, "delta_per_record_vs_B": 0.1,
                            "at_or_above_B": True},
            },
            "aggregate": {"ratio_C_over_B": 9.0},
        },
    }
    out = across_seeds(per_seed)
    assert out["every_family_at_or_above_B_in_every_seed"] is False
    assert out["families_below_B_in_at_least_one_seed"] == ["PF00072"]
    assert out["families"]["PF00072"]["n_seeds_at_or_above_B"] == 1
    assert out["aggregate"]["all_seeds_ratio_ge_1.15"] is True


@pytest.mark.parametrize(
    "aggregate_ok,every,label",
    [
        (True, True, "SUPPORTED"),
        (True, False, "HEADLINE_GAIN_NO_FAMILY_IDENTITY"),
        (False, True, "FAMILY_IDENTITY_ONLY"),
        (False, False, "NO_PROFILE_GAIN"),
    ],
)
def test_verdict_labels(aggregate_ok: bool, every: bool, label: str):
    across = {
        "aggregate": {"all_seeds_ratio_ge_1.15": aggregate_ok},
        "every_family_at_or_above_B_in_every_seed": every,
        "families_below_B_in_at_least_one_seed": [] if every else ["PF00072"],
    }
    assert verdict(across)["label"] == label


def test_cli_writes_report(tmp_path: Path):
    prof, init = _make_pair(
        tmp_path, hits_c=[5, 5], hits_b=[1, 1], hits_a=[1, 1],
        fams=["PF00005", "PF00005"],
    )
    out = tmp_path / "out.json"
    rc = main(["--pair", f"42={prof}:{init}", "--n-boot", "100",
               "--out", str(out)])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["schema"] == "gap69_per_family_v1"
    assert report["verdict"]["label"] == "SUPPORTED"
    assert report["sources"]["42"]["profile_run"] == str(prof)

"""GAP-70 report tool — pairing, no-hit handling, and the §0.4 verdicts.

The tool is the only thing standing between the GPU run and a number that goes
into the audit note, so its two failure modes are pinned here: a *no-hit* record
must count as **novel** (the K7 definition), and the arms must be paired by
record index with the family asserted equal.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.gap70_position_blend_report import main

FAMILIES = ["PF00005.27", "PF00072.24"]


def _write_arm(
    root: Path,
    *,
    arm: str,
    prefix: str,
    n: int,
    novel: list[bool],
    has_hit: list[bool],
    pctid: float = 90.0,
) -> dict[str, Path]:
    """One arm: FASTA + m8 + family_validity jsonl.

    ``novel[i]`` and ``has_hit[i]`` are per record. A record that is not novel
    gets an m8 hit at ``pctid``; a record with ``novel=True`` gets either no
    m8 line at all (``has_hit=False``) or a low-identity hit.
    """
    root.mkdir(parents=True, exist_ok=True)
    fasta = root / f"{arm}.fasta"
    m8 = root / f"{arm}.m8"
    validity = root / f"{arm}_validity.jsonl"

    fasta_lines: list[str] = []
    m8_lines: list[str] = []
    validity_lines: list[str] = []
    for i in range(n):
        fam = FAMILIES[i % len(FAMILIES)]
        header = f"{prefix}_seed{i}|family={fam}"
        fasta_lines.append(f">{header}\nACDEFGHIKLMNPQRSTVWY\n")
        validity_lines.append(
            json.dumps({"qid": f"q{i}", "header": header,
                        "has_any_hit": bool(has_hit[i])})
        )
        if not has_hit[i]:
            continue  # no hit at all -> novel
        ident = 0.20 if novel[i] else pctid / 100.0
        m8_lines.append(
            f"{header}\tTARGET/1-100\t{ident}\t50\t10\t0\t1\t50\t1\t50\t1e-5\t40\n"
        )
    fasta.write_text("".join(fasta_lines))
    m8.write_text("".join(m8_lines))
    validity.write_text("\n".join(validity_lines) + "\n")
    return {"fasta": fasta, "m8": m8, "validity": validity}


def _run(tmp_path: Path, *, a: dict[str, list[bool]],
         b: dict[str, list[bool]], c: dict[str, list[bool]],
         n: int = 10) -> dict:
    arms = {
        "A": _write_arm(tmp_path, arm="baseline", prefix="baseline", n=n,
                        novel=a["novel"], has_hit=a["has_hit"]),
        "B": _write_arm(tmp_path, arm="control", prefix="framework", n=n,
                        novel=b["novel"], has_hit=b["has_hit"]),
        "C": _write_arm(tmp_path, arm="treatment", prefix="framework", n=n,
                        novel=c["novel"], has_hit=c["has_hit"]),
    }
    out = tmp_path / "report.json"
    main([
        "--baseline-m8", str(arms["A"]["m8"]),
        "--control-m8", str(arms["B"]["m8"]),
        "--treatment-m8", str(arms["C"]["m8"]),
        "--baseline-fasta", str(arms["A"]["fasta"]),
        "--control-fasta", str(arms["B"]["fasta"]),
        "--treatment-fasta", str(arms["C"]["fasta"]),
        "--baseline-validity", str(arms["A"]["validity"]),
        "--control-validity", str(arms["B"]["validity"]),
        "--treatment-validity", str(arms["C"]["validity"]),
        "--n-total", str(n),
        "--out", str(out),
    ])
    return json.loads(out.read_text())


def test_no_hit_counts_as_novel(tmp_path: Path) -> None:
    """A record absent from m8 is novel, not "not novel"."""
    n = 10
    # Arm C: every record has no hit at all -> 100 % novel.
    report = _run(
        tmp_path,
        a={"novel": [False] * n, "has_hit": [True] * n},
        b={"novel": [False] * n, "has_hit": [True] * n},
        c={"novel": [True] * n, "has_hit": [False] * n},
        n=n,
    )
    assert report["novelty"]["arms"]["C"]["rate"] == pytest.approx(1.0)
    assert report["novelty"]["arms"]["B"]["rate"] == pytest.approx(0.0)


def test_low_identity_hit_is_novel_and_high_identity_is_not(tmp_path: Path) -> None:
    n = 10
    report = _run(
        tmp_path,
        a={"novel": [False] * n, "has_hit": [True] * n},
        b={"novel": [False] * n, "has_hit": [True] * n},
        c={"novel": [True] * n, "has_hit": [True] * n},
        n=n,
    )
    assert report["novelty"]["arms"]["C"]["rate"] == pytest.approx(1.0)


def test_pairs_by_record_index_and_reports_discordant_counts(tmp_path: Path) -> None:
    n = 10
    b_novel = [False] * n
    c_novel = [True] * 4 + [False] * 6
    report = _run(
        tmp_path,
        a={"novel": [False] * n, "has_hit": [True] * n},
        b={"novel": b_novel, "has_hit": [True] * n},
        c={"novel": c_novel, "has_hit": [True] * n},
        n=n,
    )
    cb = report["novelty"]["C_minus_B"]
    assert cb["right_only"] == 4
    assert cb["left_only"] == 0
    assert cb["delta"] == pytest.approx(0.4)


def test_validity_drop_beyond_two_points_is_not_a_win(tmp_path: Path) -> None:
    n = 20
    # C gains novelty but loses validity by 4/20 = 20 pp.
    report = _run(
        tmp_path,
        a={"novel": [False] * n, "has_hit": [True] * n},
        b={"novel": [False] * n, "has_hit": [True] * n},
        c={"novel": [True] * n, "has_hit": [True] * 16 + [False] * 4},
        n=n,
    )
    assert report["validity"]["C_minus_B"]["delta"] == pytest.approx(-0.2)
    assert report["verdict"] == "TRADE_NOT_WIN"


def test_identical_arms_are_not_the_lever(tmp_path: Path) -> None:
    n = 20
    same = {"novel": [False] * n, "has_hit": [True] * n}
    report = _run(tmp_path, a=same, b=same, c=same, n=n)
    assert report["novelty"]["C_minus_B"]["delta"] == pytest.approx(0.0)
    assert report["verdict"] == "NOT_THE_LEVER"


def test_unpaired_families_raise(tmp_path: Path) -> None:
    n = 6
    arms = {
        "A": _write_arm(tmp_path, arm="baseline", prefix="baseline", n=n,
                        novel=[False] * n, has_hit=[True] * n),
        "B": _write_arm(tmp_path, arm="control", prefix="framework", n=n,
                        novel=[False] * n, has_hit=[True] * n),
        "C": _write_arm(tmp_path, arm="treatment", prefix="framework", n=n,
                        novel=[False] * n, has_hit=[True] * n),
    }
    # Corrupt one family assignment in arm C's FASTA.
    text = arms["C"]["fasta"].read_text()
    arms["C"]["fasta"].write_text(text.replace("PF00072.24", "PF02517.18", 1))
    with pytest.raises(ValueError, match="family mismatch"):
        main([
            "--baseline-m8", str(arms["A"]["m8"]),
            "--control-m8", str(arms["B"]["m8"]),
            "--treatment-m8", str(arms["C"]["m8"]),
            "--baseline-fasta", str(arms["A"]["fasta"]),
            "--control-fasta", str(arms["B"]["fasta"]),
            "--treatment-fasta", str(arms["C"]["fasta"]),
            "--baseline-validity", str(arms["A"]["validity"]),
            "--control-validity", str(arms["B"]["validity"]),
            "--treatment-validity", str(arms["C"]["validity"]),
            "--n-total", str(n),
            "--out", str(tmp_path / "report.json"),
        ])

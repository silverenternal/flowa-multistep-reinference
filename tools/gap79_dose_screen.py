#!/usr/bin/env python3
"""GAP-79 dose screen — the per-family table §0.4 rule 2 reads.

The screen runs five temperatures at N=200 / seed 42 and answers one question
per dose: do PF00072 and PF02517 each reach a **non-zero** intended-hit rate
while PF00005 does not lose its hits? A screen number may choose the dose; it
may never be quoted (`docs/audit/gap79-r1-family-lever.md` §0.4).

Inputs are the upstream evaluator's per-record files, so the table is
re-derivable from the artifacts without re-scoring:

    <root>/seed<SEED>_T<T>/upstream_<arm>/family_validity_per_seq.jsonl
    <root>/seed<SEED>_T<T>/upstream_<arm>/family_validity.json

Output: one JSON with per-dose, per-arm, per-family `n / hits / rate`, the
screen verdict per dose, and the selected dose (largest T that passes, i.e.
the smallest dose, per the pre-registration). `selected: null` means the
lever is falsified.

Usage
-----
    python3 tools/gap79_dose_screen.py \
        --root verification_outputs/gap79-r1-temperature --seed 42 \
        --out verification_outputs/gap79-r1-temperature/screen_report.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA = "gap79_dose_screen_v1"
ARMS = ("baseline", "framework")
# §0.4 rule 2: these two must both move off zero, PF00005 must not lose hits.
REQUIRED = ("PF00072", "PF02517")
GUARD = "PF00005"


def load_per_seq(run_dir: Path, arm: str) -> list[dict]:
    path = run_dir / f"upstream_{arm}" / "family_validity_per_seq.jsonl"
    if not path.exists():
        raise SystemExit(f"missing_per_seq:{path}")
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def load_summary(run_dir: Path, arm: str) -> dict:
    path = run_dir / f"upstream_{arm}" / "family_validity.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def per_family(records: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for rec in records:
        fam = str(rec.get("intended_family_canon") or rec.get("intended_family"))
        fam = fam.split(".")[0]
        row = out.setdefault(fam, {"n": 0, "hits": 0})
        row["n"] += 1
        row["hits"] += int(bool(rec.get("intended_hit_evalue")))
    for row in out.values():
        row["rate"] = (row["hits"] / row["n"]) if row["n"] else 0.0
    return dict(sorted(out.items()))


def dose_block(run_dir: Path) -> dict:
    arms: dict[str, dict] = {}
    for arm in ARMS:
        records = load_per_seq(run_dir, arm)
        summary = load_summary(run_dir, arm)
        arms[arm] = {
            "n": len(records),
            "per_family": per_family(records),
            "hmmscan_total_hits": summary.get("hmmscan_total_hits"),
            "coverage_any_hit": summary.get("coverage_any_hit"),
            "top1_family_accuracy": summary.get("top1_family_accuracy"),
        }
    return arms


def screen_verdict(block: dict) -> dict:
    """§0.4 rule 2, evaluated on the framework arm against its own baseline."""
    fw = block["framework"]["per_family"]
    base = block["baseline"]["per_family"]
    moved = {fam: int(fw.get(fam, {}).get("hits", 0)) for fam in REQUIRED}
    guard_fw = int(fw.get(GUARD, {}).get("hits", 0))
    guard_base = int(base.get(GUARD, {}).get("hits", 0))
    guard_ok = guard_fw >= guard_base
    return {
        "required_hits": moved,
        "required_all_nonzero": all(v > 0 for v in moved.values()),
        "guard_family": GUARD,
        "guard_framework_hits": guard_fw,
        "guard_baseline_hits": guard_base,
        "guard_ok": guard_ok,
        "eligible": bool(all(v > 0 for v in moved.values()) and guard_ok),
    }


def build(root: Path, seed: int) -> dict:
    doses: list[dict] = []
    for run_dir in sorted(root.glob(f"seed{seed}_T*")):
        if not run_dir.is_dir():
            continue
        temp = float(run_dir.name.split("_T", 1)[1])
        block = dose_block(run_dir)
        verdict = screen_verdict(block)
        doses.append(
            {
                "temperature": temp,
                "run_dir": str(run_dir),
                "arms": block,
                "verdict": verdict,
            }
        )
    if not doses:
        raise SystemExit(f"no_dose_dirs_under:{root}")
    doses.sort(key=lambda d: d["temperature"])
    eligible = [d["temperature"] for d in doses if d["verdict"]["eligible"]]
    # Smallest dose = T closest to 1 = the largest eligible T.
    selected = max(eligible) if eligible else None
    return {
        "schema": SCHEMA,
        "root": str(root),
        "seed": seed,
        "doses": doses,
        "selected_temperature": selected,
        "falsified": selected is None,
        "note": (
            "screen only — these numbers may choose a dose and may never be "
            "quoted; confirmation is N=1000 x seeds 42/43/44"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    report = build(args.root, args.seed)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

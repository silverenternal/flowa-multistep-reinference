#!/usr/bin/env python3
"""GAP-79 lever 3 — the per-family table §3.4 reads.

The screen runs five in-loop drift weights at N=200 / seed 42 against one
control (the same arm C init, no drift) and answers one question per dose: do
PF00072 and PF02517 each reach a **non-zero** intended-hit rate while PF00005
does not lose its hits **and** the output has not collapsed to the profile
consensus? A screen number may choose the dose; it may never be quoted
(``docs/audit/gap79-r1-family-lever.md`` §3.4).

Inputs are the upstream evaluator's per-record files, so the table is
re-derivable from the artifacts without re-scoring:

    <root>/control/upstream_framework/family_validity_per_seq.jsonl
    <root>/W<weight>/upstream_framework/family_validity_per_seq.jsonl
    <root>/<cell>/framework.fasta          # diversity guard

Output: one JSON with per-dose, per-family `n / hits / rate`, the diversity
read, the §3.4 verdict per dose, and the selected weight (the **smallest**
eligible weight, i.e. the least intervention). `selected_weight: null` means
the lever is falsified.

Usage
-----
    python3 tools/gap79_guidance_screen.py \
        --root verification_outputs/gap79-r1-guidance/seed42 \
        --out verification_outputs/gap79-r1-guidance/screen_report.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:  # direct ``python3 tools/...`` invocation
    sys.path.insert(0, str(_REPO_ROOT))

from tools.gap79_dose_screen import load_per_seq, per_family  # noqa: E402

SCHEMA = "gap79_guidance_screen_v1"
REQUIRED = ("PF00072", "PF02517")
GUARD = "PF00005"
# §3.4 rule 4 — a dose that lifts identity by emitting consensus copies is not
# eligible.
MIN_UNIQUE_FRACTION = 0.95
MIN_ENTROPY_RATIO = 0.5


def read_fasta(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"missing_fasta:{path}")
    seqs: list[str] = []
    chunk: list[str] = []
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            if chunk:
                seqs.append("".join(chunk))
                chunk = []
        elif line.strip():
            chunk.append(line.strip())
    if chunk:
        seqs.append("".join(chunk))
    if not seqs:
        raise SystemExit(f"empty_fasta:{path}")
    return seqs


def diversity(seqs: list[str]) -> dict:
    """Unique fraction plus mean per-position entropy in bits.

    Entropy is computed per column over the records that have a residue at
    that position (lengths differ), then averaged over columns. It is a
    *diversity* read, not a quality read: the guard only asks whether the dose
    collapsed the sample.
    """
    n = len(seqs)
    unique = len(set(seqs)) / float(n)
    width = max(len(s) for s in seqs)
    ents: list[float] = []
    for j in range(width):
        col = [s[j] for s in seqs if j < len(s)]
        if len(col) < 2:
            continue
        counts = Counter(col)
        total = float(len(col))
        ents.append(
            -sum((c / total) * math.log2(c / total) for c in counts.values())
        )
    return {
        "n": n,
        "unique_fraction": unique,
        "mean_positional_entropy_bits": (
            sum(ents) / len(ents) if ents else 0.0
        ),
        "mean_length": sum(len(s) for s in seqs) / float(n),
    }


def cell_block(run_dir: Path) -> dict:
    records = load_per_seq(run_dir, "framework")
    return {
        "run_dir": str(run_dir),
        "n": len(records),
        "per_family": per_family(records),
        "diversity": diversity(read_fasta(run_dir / "framework.fasta")),
    }


def verdict(block: dict, control: dict) -> dict:
    """§3.4 rules 1-4, evaluated against the control cell."""
    fw = block["per_family"]
    ctrl = control["per_family"]
    moved = {fam: int(fw.get(fam, {}).get("hits", 0)) for fam in REQUIRED}
    required_ok = all(v > 0 for v in moved.values())

    guard_fw = int(fw.get(GUARD, {}).get("hits", 0))
    guard_ctrl = int(ctrl.get(GUARD, {}).get("hits", 0))
    guard_n = int(ctrl.get(GUARD, {}).get("n", 0)) or 1
    # "control - 1 sequence" at the control's per-family sample size.
    guard_floor = guard_ctrl - 1
    guard_ok = guard_fw >= guard_floor

    div = block["diversity"]
    ctrl_div = control["diversity"]
    unique_ok = div["unique_fraction"] >= MIN_UNIQUE_FRACTION
    entropy_ratio = (
        div["mean_positional_entropy_bits"]
        / ctrl_div["mean_positional_entropy_bits"]
        if ctrl_div["mean_positional_entropy_bits"] > 0
        else 0.0
    )
    entropy_ok = entropy_ratio >= MIN_ENTROPY_RATIO

    return {
        "required_hits": moved,
        "required_all_nonzero": required_ok,
        "guard_family": GUARD,
        "guard_hits": guard_fw,
        "guard_control_hits": guard_ctrl,
        "guard_floor": guard_floor,
        "guard_n": guard_n,
        "guard_ok": guard_ok,
        "unique_fraction": div["unique_fraction"],
        "unique_ok": unique_ok,
        "entropy_ratio_vs_control": entropy_ratio,
        "entropy_ok": entropy_ok,
        "eligible": bool(required_ok and guard_ok and unique_ok and entropy_ok),
    }


def _weight_of(run_dir: Path) -> float:
    name = run_dir.name
    if not name.startswith("W"):
        raise SystemExit(f"bad_dose_dir_name:{name}")
    return float(name[1:])


def build(root: Path) -> dict:
    control_dir = root / "control"
    if not control_dir.is_dir():
        raise SystemExit(f"missing_control_cell:{control_dir}")
    control = cell_block(control_dir)

    doses: list[dict] = []
    # The sweep leaves sibling W<weight>.log files next to the cells, so filter
    # to directories *before* sorting (the key parses the name).
    dose_dirs = [p for p in root.glob("W*") if p.is_dir()]
    for run_dir in sorted(dose_dirs, key=_weight_of):
        block = cell_block(run_dir)
        doses.append(
            {
                "weight": _weight_of(run_dir),
                "run_dir": str(run_dir),
                "per_family": block["per_family"],
                "diversity": block["diversity"],
                "verdict": verdict(block, control),
            }
        )
    if not doses:
        raise SystemExit(f"no_dose_dirs_under:{root}")

    eligible = [d["weight"] for d in doses if d["verdict"]["eligible"]]
    # §3.4: smallest weight = least intervention.
    selected = min(eligible) if eligible else None
    return {
        "schema": SCHEMA,
        "root": str(root),
        "control": control,
        "doses": doses,
        "selected_weight": selected,
        "falsified": selected is None,
        "note": (
            "screen only — these numbers may choose a dose and may never be "
            "quoted; confirmation is N=1000 x seeds 42/43/44"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    report = build(args.root)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

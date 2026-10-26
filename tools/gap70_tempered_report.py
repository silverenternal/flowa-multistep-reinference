#!/usr/bin/env python3
"""GAP-70 round 2 — the tempered-draw dose-response report.

Pre-registration: ``docs/audit/gap70-r2-tempered-draw.md``.

Arms are ``lam in {0, ...}`` where ``lam`` mixes the shipped fresh draw into the
state the restart replaces:

    fresh = (1 - lam) * state + lam * softmax(randn)

``lam = 0`` is the no-restart end and ``lam = 1`` the shipped restart, so the
grid is a segment between two already-measured arms. A point on a segment
cannot be better than both ends; an interior ``lam`` can only win if the
(novelty, validity) frontier bulges **above the chord**. This tool prints the
chord residual for exactly that reason.

Both readouts are per-record binary and paired by record index:

* novelty — ``pctid < 30 %`` against the canonical Pfam-A DB, or no hit at all
  (the K7 definition). The generator's built-in novelty is never used: it
  searches a 200-sequence holdout DB and saturates at 1.0.
* validity — ``has_any_hit`` from the upstream ``family_validity_per_seq.jsonl``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.gap70_position_blend_report import (
    PCTID_THRESHOLD,
    _align,
    _arm_summary,
    _index,
    _load_best_pctid,
    _load_families,
    _load_has_any_hit,
    _paired,
    _qid,
)

VALIDITY_TOLERANCE = 0.02  # 2 pp, GAP-70's own acceptance wording
NOVELTY_TOLERANCE = 0.02
ALPHA = 0.05

# Why the validity clause is a point-estimate margin plus McNemar, and not a
# Newcombe non-inferiority interval: at n = 1000 with *zero* discordant pairs
# the paired Newcombe interval is [-4.95 pp, +0.23 pp], so an arm whose validity
# is bit-identical to lam = 1 would fail a 2 pp non-inferiority test. That test
# cannot be passed by construction, so it is not the test. The novelty clause
# still needs a real interval: recovering novelty is the claim, and a claim
# needs a lower bound above zero.


def _novelty_arm(
    m8: Path, fasta: Path, n_total: int, prefix: str = "framework"
) -> dict[int, tuple[str, float]]:
    families = _load_families(fasta, str(fasta))
    if len(families) != n_total:
        raise SystemExit(
            f"{fasta}: {len(families)} records != n_total={n_total}"
        )
    best = _load_best_pctid(m8)
    out: dict[int, tuple[str, float]] = {}
    for idx, fam in families.items():
        pct = best.get(_qid(prefix, idx, fam))
        out[idx] = (fam, 1.0 if pct is None or pct < PCTID_THRESHOLD else 0.0)
    return out


def _chord(value_a: float, value_one: float, lam: float) -> float:
    return value_a + lam * (value_one - value_a)


def _fmt(rate: float | None) -> str:
    return "   n/a" if rate is None else f"{100.0 * rate:6.2f}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--lams", type=str, default="0 0.1 0.2 0.35 0.5 0.75 1")
    ap.add_argument("--n-total", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    lams = [float(v) for v in args.lams.split()]
    if 0.0 not in lams or 1.0 not in lams:
        raise SystemExit("--lams must contain both 0 and 1 (the two ends)")

    def arm_dir(lam: float) -> Path:
        return args.root / f"lam{lam:g}"

    baseline_fasta = arm_dir(0.0) / "baseline.fasta"
    baseline_m8 = args.root / "m8" / "baseline.m8"
    baseline_validity = (
        arm_dir(0.0) / "upstream_baseline" / "family_validity_per_seq.jsonl"
    )
    for path in (baseline_fasta, baseline_m8, baseline_validity):
        if not path.exists():
            raise SystemExit(f"missing baseline artifact: {path}")

    novelty: dict[float, dict[int, tuple[str, float]]] = {}
    validity: dict[float, dict[int, tuple[str, float]]] = {}
    for lam in lams:
        d = arm_dir(lam)
        m8 = args.root / "m8" / f"lam{lam:g}.m8"
        fasta = d / "framework.fasta"
        valid = d / "upstream_framework" / "family_validity_per_seq.jsonl"
        for path in (m8, fasta, valid):
            if not path.exists():
                raise SystemExit(f"missing arm artifact (lam={lam:g}): {path}")
        novelty[lam] = _novelty_arm(m8, fasta, args.n_total)
        validity[lam] = _index(_load_has_any_hit(valid), str(valid))

    nov_idx = _align(novelty)
    val_idx = _align(validity)
    nov = {lam: _arm_summary(v, nov_idx) for lam, v in novelty.items()}
    val = {lam: _arm_summary(v, val_idx) for lam, v in validity.items()}

    n_a = nov[0.0]["rate"]
    n_one = nov[1.0]["rate"]
    v_a = val[0.0]["rate"]
    v_one = val[1.0]["rate"]

    rows: list[dict[str, Any]] = []
    for lam in lams:
        d_nov = _paired(novelty[0.0], novelty[lam], nov_idx)
        d_val = _paired(validity[1.0], validity[lam], val_idx)
        chord_n = _chord(n_a, n_one, lam)
        chord_v = _chord(v_a, v_one, lam)
        novelty_ok = bool(
            nov[lam]["rate"] >= n_a - NOVELTY_TOLERANCE
            and d_nov["ci95"][0] > 0.0
        )
        # Validity: at or above the current arm within 2 pp, with no detectable
        # loss (a significant drop fails even if it is inside the margin).
        no_loss = bool(d_val["delta"] >= 0.0 or d_val["mcnemar_p"] >= ALPHA)
        validity_ok = bool(
            val[lam]["rate"] >= v_one - VALIDITY_TOLERANCE and no_loss
        )
        rows.append(
            {
                "lam": lam,
                "novelty": nov[lam],
                "validity": val[lam],
                "novelty_vs_baseline": d_nov,
                "validity_vs_lam1": d_val,
                "chord_novelty": chord_n,
                "chord_validity": chord_v,
                "above_chord_novelty": bool(nov[lam]["rate"] > chord_n),
                "above_chord_validity": bool(val[lam]["rate"] > chord_v),
                "novelty_ok": novelty_ok,
                "validity_ok": validity_ok,
                "wins": bool(novelty_ok and validity_ok),
            }
        )

    winners = [r["lam"] for r in rows if r["wins"] and 0.0 < r["lam"] < 1.0]
    interior = [r for r in rows if 0.0 < r["lam"] < 1.0]
    convex = any(
        r["above_chord_novelty"] and r["above_chord_validity"] for r in interior
    )
    if winners:
        verdict = "TEMPERED_DRAW_WINS"
    elif convex:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "TRADE_IS_INTRINSIC"

    report = {
        "spec": "docs/audit/gap70-r2-tempered-draw.md",
        "seed": int(args.seed),
        "n_total": int(args.n_total),
        "lams": lams,
        "rows": rows,
        "verdict": verdict,
        "selected_lambda": min(winners) if winners else None,
        "interior_above_both_chords": convex,
        "note": (
            "one seed; rule 4 replicates only when a lambda wins, and then it "
            "is a replication, not a search"
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))

    print(f"{'lam':>6s} {'N%':>6s} {'V%':>6s} {'N-A':>8s} {'V-1':>8s} "
          f"{'chordN':>7s} {'chordV':>7s}  nov_ok val_ok")
    for r in rows:
        print(
            f"{r['lam']:6.2f} {_fmt(r['novelty']['rate'])} "
            f"{_fmt(r['validity']['rate'])} "
            f"{100.0 * r['novelty_vs_baseline']['delta']:+8.2f} "
            f"{100.0 * r['validity_vs_lam1']['delta']:+8.2f} "
            f"{_fmt(r['chord_novelty'])} {_fmt(r['chord_validity'])}  "
            f"{str(r['novelty_ok']):6s} {str(r['validity_ok']):6s}"
        )
    print(f"\nverdict: {verdict}")
    if winners:
        print(f"selected lambda: {min(winners)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

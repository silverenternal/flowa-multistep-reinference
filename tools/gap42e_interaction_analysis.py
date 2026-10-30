"""GAP-42e — 2x2 interaction screen: tier-aware n_cap x endpoint chain.

Cells (per seed, N=200, NFE=10, cosine):

              chain OFF            chain ON
  tier OFF    A = legacy_off       B = legacy_on
  tier ON     C = tier_off         D = tier_on

A/B come from the GAP-42c chain screen; C/D from the GAP-42e run.

Reported contrasts:
  tier effect without chain : C - A
  tier effect with chain    : D - B
  chain effect without tier : B - A
  chain effect with tier    : D - C
  interaction               : (D - C) - (B - A)

Screen only (n=3 seeds, N=200): direction consistency is the entry ticket,
not a conclusion.

CPU-only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_LEGACY = REPO_ROOT / "verification_outputs" / "legacy-gap40-42"

CHAIN = _LEGACY / "gap41b-nfe150" / "chain_screen"
INTER = _LEGACY / "gap42e-interaction"
LINE = re.compile(
    r"^(?P<dir>[^:]+)/(?P<file>[^:]+):\s+total_hits=(?P<hits>\d+)\s+"
    r"records=(?P<records>\d+)\s+records_with_hits=(?P<ge1>\d+)\s+"
    r"hits_per_record=(?P<hpr>[\d.]+)\s*$"
)
CHAIN_DIR = re.compile(r"seed(?P<s>\d+)_chain_(?P<arm>off|on)$")
INTER_DIR = re.compile(r"seed(?P<s>\d+)_tier_(?P<arm>off|on)$")


def _parse(path: Path, pat: re.Pattern[str], prefix: str) -> dict:
    out: dict[int, dict[str, int]] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        m = LINE.match(line.strip())
        if not m:
            continue
        sm = pat.search(Path(m["dir"]).name)
        if not sm:
            continue
        seed = int(sm["s"])
        key = "baseline" if m["file"].startswith("baseline") else f"{prefix}{sm['arm']}"
        out.setdefault(seed, {})[key] = int(m["hits"])
    return out


def _t(diffs: list[int]) -> tuple[float | None, float | None]:
    if len(diffs) < 2:
        return None, None
    from scipy import stats

    r = stats.ttest_1samp(diffs, 0.0)
    return float(r.statistic), float(r.pvalue)


def main() -> int:
    data = _parse(CHAIN / "hits.txt", CHAIN_DIR, "legacy_")
    for seed, v in _parse(INTER / "hits.txt", INTER_DIR, "tier_").items():
        data.setdefault(seed, {}).update(v)

    need = {"baseline", "legacy_off", "legacy_on", "tier_off", "tier_on"}
    seeds = sorted(s for s, v in data.items() if need <= set(v))
    if not seeds:
        print(f"incomplete cells under {CHAIN} / {INTER}", file=sys.stderr)
        return 1

    print("=== GAP-42e 2x2 interaction (N=200, NFE=10, cosine) ===")
    print(
        f"{'seed':>5} {'base':>5} {'A off/off':>9} {'B off/on':>8} "
        f"{'C on/off':>8} {'D on/on':>7} {'inter':>6}"
    )
    cols: dict[str, list[int]] = {
        k: []
        for k in ("tier_wo_chain", "tier_w_chain", "chain_wo_tier", "chain_w_tier", "interaction")
    }
    rows = {}
    for s in seeds:
        v = data[s]
        a, b, c, d = v["legacy_off"], v["legacy_on"], v["tier_off"], v["tier_on"]
        twc, twh = c - a, d - b
        cwt, cwh = b - a, d - c
        inter = cwh - cwt
        for k, val in (
            ("tier_wo_chain", twc),
            ("tier_w_chain", twh),
            ("chain_wo_tier", cwt),
            ("chain_w_tier", cwh),
            ("interaction", inter),
        ):
            cols[k].append(val)
        rows[str(s)] = {
            "baseline": v["baseline"],
            "A_legacy_off": a,
            "B_legacy_on": b,
            "C_tier_off": c,
            "D_tier_on": d,
            "tier_wo_chain": twc,
            "tier_w_chain": twh,
            "chain_wo_tier": cwt,
            "chain_w_tier": cwh,
            "interaction": inter,
        }
        print(f"{s:>5} {v['baseline']:>5} {a:>9} {b:>8} {c:>8} {d:>7} {inter:>+6}")

    summary = {}
    print()
    for k, vals in cols.items():
        t, p = _t(vals)
        n_pos = sum(1 for x in vals if x > 0)
        n_neg = sum(1 for x in vals if x < 0)
        consistent = n_pos == len(vals) or n_neg == len(vals)
        summary[k] = {
            "diffs": vals,
            "mean": sum(vals) / len(vals),
            "n_pos": n_pos,
            "n_neg": n_neg,
            "direction_consistent": consistent,
            "t": t,
            "p": p,
        }
        print(
            f"{k:<16} mean={summary[k]['mean']:+7.2f}  {n_pos}+/{n_neg}-  "
            + (f"t={t:.3f} p={p:.3f}  " if t is not None else "")
            + f"consistent={consistent}"
        )

    out = INTER / "interaction_analysis.json"
    out.write_text(
        json.dumps({"seeds": rows, "summary": summary, "n_seeds": len(seeds)}, indent=2) + "\n"
    )
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        raise SystemExit(0)
    raise SystemExit(main())

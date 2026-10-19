"""GAP-42c — R1 endpoint-chain screen analysis (n=3, N=200, NFE=10, cosine).

Reads the per-seed hit counts produced by `run_chain_screen.sh`:

  seed<S>_chain_off/{baseline,framework}.fasta
  seed<S>_chain_on/{framework}.fasta

and reports, per seed:
  - baseline vs framework with the chain OFF (the canonical path),
  - baseline vs framework with the chain ON  (Eq. 2 live),
  - framework ON minus framework OFF (the marginal effect of chaining).

Screen only: n=3 seeds at N=200 cannot decide the claim; it can only show
whether the chain moves the metric in a consistent direction.

CPU-only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCREEN = Path("/home/hugo/codes/flowa-multistep-reinference/verification_outputs/legacy-gap40-42/gap41b-nfe150/chain_screen")
LINE = re.compile(
    r"^(?P<dir>[^:]+)/(?P<file>[^:]+):\s+total_hits=(?P<hits>\d+)\s+"
    r"records=(?P<records>\d+)\s+records_with_hits=(?P<ge1>\d+)\s+"
    r"hits_per_record=(?P<hpr>[\d.]+)\s*$"
)
SEED = re.compile(r"seed(?P<s>\d+)_chain_(?P<arm>off|on)$")


def parse(hits_txt: Path) -> dict[int, dict[str, int]]:
    """{seed: {baseline|off|on: total_hits}}."""
    out: dict[int, dict[str, int]] = {}
    if not hits_txt.exists():
        return out
    for line in hits_txt.read_text().splitlines():
        m = LINE.match(line.strip())
        if not m:
            continue
        sm = SEED.search(Path(m["dir"]).name)
        if not sm:
            continue
        seed = int(sm["s"])
        key = "baseline" if m["file"].startswith("baseline") else sm["arm"]
        out.setdefault(seed, {})[key] = int(m["hits"])
    return out


def _t(diffs: list[int]) -> tuple[float, float] | tuple[None, None]:
    if len(diffs) < 2:
        return None, None
    from scipy import stats

    r = stats.ttest_1samp(diffs, 0.0)
    return float(r.statistic), float(r.pvalue)


def main() -> int:
    data = parse(SCREEN / "hits.txt")
    seeds = sorted(s for s, v in data.items() if {"baseline", "off", "on"} <= set(v))
    if not seeds:
        print(f"no complete seeds found under {SCREEN}", file=sys.stderr)
        return 1

    result: dict = {"seeds": {}, "summary": {}}
    d_off: list[int] = []
    d_on: list[int] = []
    d_chain: list[int] = []

    print("=== GAP-42c R1 chain screen (n=3, N=200, NFE=10, cosine) ===")
    print(
        f"{'seed':>5} {'base':>5} {'fw_off':>7} {'fw_on':>6} "
        f"{'off-base':>9} {'on-base':>8} {'on-off':>7}"
    )
    for s in seeds:
        v = data[s]
        b, off, on = v["baseline"], v["off"], v["on"]
        a, c, e = off - b, on - b, on - off
        d_off.append(a)
        d_on.append(c)
        d_chain.append(e)
        result["seeds"][str(s)] = {
            "baseline": b,
            "framework_off": off,
            "framework_on": on,
            "off_minus_baseline": a,
            "on_minus_baseline": c,
            "on_minus_off": e,
        }
        print(f"{s:>5} {b:>5} {off:>7} {on:>6} {a:>+9} {c:>+8} {e:>+7}")

    def summarise(name: str, diffs: list[int]) -> dict:
        n_pos = sum(1 for d in diffs if d > 0)
        n_neg = sum(1 for d in diffs if d < 0)
        t, p = _t(diffs)
        s = {
            "mean_diff": sum(diffs) / len(diffs),
            "diffs": diffs,
            "n_pos": n_pos,
            "n_neg": n_neg,
            "direction_consistent": n_pos == len(diffs) or n_neg == len(diffs),
            "seed_t_stat": t,
            "seed_t_p": p,
        }
        print(
            f"{name:<18} mean={s['mean_diff']:+.2f}  {n_pos}+/{n_neg}-  "
            + (f"t={t:.3f} p={p:.3f}  " if t is not None else "")
            + f"consistent={s['direction_consistent']}"
        )
        return s

    print()
    result["summary"]["framework_off_vs_baseline"] = summarise("fw_off vs baseline", d_off)
    result["summary"]["framework_on_vs_baseline"] = summarise("fw_on  vs baseline", d_on)
    result["summary"]["chain_marginal"] = summarise("chain (on - off)", d_chain)
    result["summary"]["n_seeds"] = len(seeds)

    out = SCREEN / "screen_analysis.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

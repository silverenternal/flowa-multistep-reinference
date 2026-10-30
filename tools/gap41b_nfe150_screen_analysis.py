"""GAP-41b follow-up — n=3 N=200 NFE=150 legacy screen analysis.

Reads the per-seed baseline/framework hit counts for seeds 42/43/44 at N=200,
NFE=150, legacy arm (seed 42 from the premise run, seeds 43/44 from the screen
run) and reports the per-seed framework-vs-baseline diff, the 3-seed direction
consistency, and a seed-level paired t-test.

Question: is the premise's seed-42 framework-vs-baseline +11 (N=200, NFE=150)
direction-consistent 3/3, i.e. worth a decisive N=1000 run?

CPU-only. Reads:
  verification_outputs/legacy-gap40-42/gap41b-nfe150/premise/hits.txt          (seed 42)
  verification_outputs/legacy-gap40-42/gap41b-nfe150/nfe150_screen/hits.txt    (seeds 43/44)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_NFE150 = REPO_ROOT / "verification_outputs" / "legacy-gap40-42" / "gap41b-nfe150"

PREMISE = _NFE150 / "premise"
SCREEN = _NFE150 / "nfe150_screen"
LINE = re.compile(
    r"^(?P<dir>[^:]+)/(?P<file>[^:]+):\s+total_hits=(?P<hits>\d+)\s+"
    r"records=(?P<records>\d+)\s+records_with_hits=(?P<ge1>\d+)\s+"
    r"hits_per_record=(?P<hpr>[\d.]+)\s*$"
)
SEED = re.compile(r"seed(?P<s>\d+)_nfe150_legacy$")


def parse(hits_txt: Path) -> dict[int, dict[str, int]]:
    """{seed: {baseline|framework: total_hits}} for the NFE=150 legacy arm only."""
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
        arm = "baseline" if m["file"].startswith("baseline") else "framework"
        out.setdefault(int(sm["s"]), {})[arm] = int(m["hits"])
    return out


def main() -> int:
    data = parse(PREMISE / "hits.txt")
    for s, v in parse(SCREEN / "hits.txt").items():
        data.setdefault(s, {}).update(v)

    seeds = sorted(s for s, v in data.items() if "baseline" in v and "framework" in v)
    result: dict = {"seeds": {}, "summary": {}}
    diffs: list[int] = []

    print("=== GAP-41b n=3 N=200 NFE=150 legacy screen (framework vs baseline) ===")
    print(f"{'seed':>5} {'baseline':>9} {'framework':>10} {'diff':>6}")
    for s in seeds:
        b = data[s]["baseline"]
        f = data[s]["framework"]
        d = f - b
        diffs.append(d)
        result["seeds"][str(s)] = {"baseline": b, "framework": f, "diff": d}
        print(f"{s:>5} {b:>9} {f:>10} {d:>+6}")

    n_pos = sum(1 for d in diffs if d > 0)
    n_neg = sum(1 for d in diffs if d < 0)
    summary: dict = {
        "n_seeds": len(diffs),
        "diffs": diffs,
        "mean_diff": (sum(diffs) / len(diffs)) if diffs else None,
        "n_pos": n_pos,
        "n_neg": n_neg,
    }
    if len(diffs) >= 2:
        from scipy import stats

        t = stats.ttest_1samp(diffs, 0.0)
        summary["seed_t_stat"] = float(t.statistic)
        summary["seed_t_p"] = float(t.pvalue)
        summary["direction_consistent"] = n_pos == len(diffs) or n_neg == len(diffs)

    result["summary"] = summary
    print(
        f"\n3-seed: mean diff={summary['mean_diff']:+.2f}, "
        f"{n_pos}+/{n_neg}- "
        + (
            f"t={summary.get('seed_t_stat'):.3f} p={summary.get('seed_t_p'):.3f}"
            if "seed_t_stat" in summary
            else ""
        )
    )
    print(
        "direction-consistent 3/3: "
        + str(summary.get("direction_consistent", "n/a"))
    )

    (SCREEN / "screen_analysis.json").write_text(
        json.dumps(result, indent=2) + "\n",
    )
    print(f"\nwrote {SCREEN / 'screen_analysis.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

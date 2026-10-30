"""GAP-41b premise analysis — does NFE move the R1 HMMER metric / tier lever?

Reads the premise ``hits.txt`` (6 FASTAs: baseline + legacy + tier at NFE 10 and
150) and prints a comparison table:

  - framework-vs-baseline gap at each NFE (does the budget move the headline?)
  - tier-vs-legacy lever at each NFE (does the budget move the lever?)

Outputs JSON alongside. CPU-only.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PREMISE = REPO_ROOT / "verification_outputs" / "legacy-gap40-42" / "gap41b-nfe150" / "premise"
LINE = re.compile(
    r"^(?P<dir>[^:]+)/(?P<file>[^:]+):\s+total_hits=(?P<hits>\d+)\s+"
    r"records=(?P<records>\d+)\s+records_with_hits=(?P<ge1>\d+)\s+"
    r"hits_per_record=(?P<hpr>[\d.]+)\s*$"
)
# records are paired by index (``*_seed{i}|family=...``); the tier arm shares the
# legacy baseline FASTA (no per-tier baseline.tblout), so the legacy baseline is
# the common baseline for both comparisons.
REC_INDEX = re.compile(r"seed(?P<i>\d+)\|")


def per_record_hits(tblout: Path) -> dict[int, int]:
    """{record_index: n_hits} from a HMMER tblout (query name is column 3)."""
    c: Counter[int] = Counter()
    for line in tblout.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        m = REC_INDEX.search(line.split()[2])
        if m:
            c[int(m["i"])] += 1
    return dict(c)


def paired_test(base: dict[int, int], fw: dict[int, int]) -> dict:
    """Paired per-record comparison over the union of record indices."""
    from scipy import stats

    idx = sorted(set(base) | set(fw))
    b = [base.get(i, 0) for i in idx]
    f = [fw.get(i, 0) for i in idx]
    diff = [fi - bi for bi, fi in zip(b, f, strict=True)]
    out: dict = {
        "n_records": len(idx),
        "sum_base": sum(b),
        "sum_fw": sum(f),
        "sum_diff": sum(diff),
        "n_nonzero": sum(1 for d in diff if d != 0),
    }
    nz = [d for d in diff if d != 0]
    if nz:
        try:
            w = stats.wilcoxon(f, b, zero_method="wilcox")
            out["wilcoxon_stat"] = float(w.statistic)
            out["wilcoxon_p"] = float(w.pvalue)
        except ValueError:
            out["wilcoxon_p"] = None
        out["sign_pos"] = sum(1 for d in nz if d > 0)
        out["sign_neg"] = sum(1 for d in nz if d < 0)
        out["sign_test_p"] = float(
            stats.binomtest(out["sign_pos"], len(nz), 0.5).pvalue
        )
    return out


def parse(hits_txt: Path) -> dict[str, dict[str, int]]:
    """{arm_tag: {baseline|framework: {...}}} keyed by seed42_<tag>."""
    out: dict[str, dict[str, dict[str, int]]] = {}
    for line in hits_txt.read_text().splitlines():
        m = LINE.match(line.strip())
        if not m:
            continue
        tag = Path(m["dir"]).name
        arm = "baseline" if m["file"].startswith("baseline") else "framework"
        out.setdefault(tag, {})[arm] = {
            "total_hits": int(m["hits"]),
            "records": int(m["records"]),
            "records_with_hits": int(m["ge1"]),
            "hits_per_record": float(m["hpr"]),
        }
    return out


def main() -> int:
    data = parse(PREMISE / "hits.txt")
    result: dict = {"arms": data, "comparisons": {}, "paired": {}}

    for nfe in (10, 150):
        leg = data.get(f"seed42_nfe{nfe}_legacy", {})
        tier = data.get(f"seed42_nfe{nfe}_tier", {})
        base = leg.get("baseline", {})
        if not (base and leg.get("framework") and tier.get("framework")):
            continue
        b = base["total_hits"]
        lf = leg["framework"]["total_hits"]
        tf = tier["framework"]["total_hits"]
        result["comparisons"][f"nfe{nfe}"] = {
            "baseline": b,
            "legacy_framework": lf,
            "tier_framework": tf,
            "framework_vs_baseline": lf - b,
            "tier_vs_legacy": tf - lf,
            "tier_vs_baseline": tf - b,
        }

    # Per-record paired tests (tier shares the legacy baseline FASTA).
    for nfe in (10, 150):
        leg_dir = PREMISE / f"seed42_nfe{nfe}_legacy"
        tier_dir = PREMISE / f"seed42_nfe{nfe}_tier"
        if not (leg_dir / "baseline.tblout").exists():
            continue
        base = per_record_hits(leg_dir / "baseline.tblout")
        leg_fw = per_record_hits(leg_dir / "framework.tblout")
        tier_fw = per_record_hits(tier_dir / "framework.tblout")
        result["paired"][f"nfe{nfe}"] = {
            "framework_vs_baseline": paired_test(base, leg_fw),
            "tier_vs_legacy": paired_test(leg_fw, tier_fw),
        }

    print("=== GAP-41b premise: R1 hits vs NFE (N=200, seed 42) ===")
    print(f"{'NFE':>5} {'baseline':>9} {'legacy':>7} {'tier':>6} "
          f"{'fw-baseline':>12} {'tier-legacy':>12}")
    for nfe in (10, 150):
        c = result["comparisons"].get(f"nfe{nfe}")
        if not c:
            print(f"{nfe:>5}   (pending)")
            continue
        print(f"{nfe:>5} {c['baseline']:>9} {c['legacy_framework']:>7} "
              f"{c['tier_framework']:>6} {c['framework_vs_baseline']:>+12} "
              f"{c['tier_vs_legacy']:>+12}")

    print("\n=== per-record paired tests (union of records with a hit) ===")
    for nfe in (10, 150):
        p = result["paired"].get(f"nfe{nfe}")
        if not p:
            continue
        for name, t in p.items():
            sig = ""
            if t.get("sign_test_p") is not None:
                sig = (f" sign {t['sign_pos']}+/{t['sign_neg']}- "
                       f"p={t['sign_test_p']:.3f}")
            w = t.get("wilcoxon_p")
            ws = f" wilcoxon_p={w:.3f}" if w is not None else ""
            print(f"  NFE={nfe:<4} {name:<22} n={t['n_records']:<4} "
                  f"sum_diff={t['sum_diff']:+d}{ws}{sig}")

    (PREMISE / "premise_analysis.json").write_text(
        json.dumps(result, indent=2) + "\n",
    )
    print(f"\nwrote {PREMISE / 'premise_analysis.json'}")
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        raise SystemExit(0)
    if len(sys.argv) > 1:
        print(
            f"{sys.argv[0]}: this driver takes no arguments; "
            f"got {sys.argv[1:]}. Its parameters are fixed in the source.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    raise SystemExit(main())

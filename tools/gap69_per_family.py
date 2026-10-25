#!/usr/bin/env python3
"""GAP-69 per-family decomposition — the statistic the acceptance rule reads.

The 8.20x aggregate at seed 42 is one family. `tools/gap69_report.py` reports
the aggregate and says nothing about which family carries it, so the rule in
`todo.json` GAP-69 ("every one of the four families is at or above baseline")
had no tool behind it and seed 42's table was computed ad hoc. This is that
tool: it reads the per-record `family_validity_per_seq.jsonl` for both arms of
each seed, pairs by `qid`, groups by `intended_family_canon`, and emits

* per-seed, per-family: n, hits on each arm, C/B ratio, paired delta per record,
  paired t, bootstrap CI;
* per seed: the aggregate, the PF00005-excluded aggregate, and the boolean the
  rule reads;
* across seeds: the per-family mean ratio and how many seeds clear 1.0, with the
  seed as the replication unit (records are not independent across seeds);
* a verdict block that states both the aggregate and the per-family condition,
  because the pre-registration requires both.

Ratio vs arm B (init-only) is the primary reading: B is the comparison arm per
`docs/audit/gap69-lineageflow-profile.md` §0.2, and the seed-42 table is C/B.
Ratio vs arm A (baseline) is reported alongside so "at or above baseline" can
be read either way without re-running anything.

Usage
-----
    python3 tools/gap69_per_family.py \
        --pair 42=verification_outputs/gap69-lineageflow-profile/seed42:verification_outputs/gap58-r1-beta1-n1000/seed42 \
        --pair 43=verification_outputs/gap69-lineageflow-profile/seed43:verification_outputs/gap69-lineageflow-profile/seed43_init_only \
        --pair 44=verification_outputs/gap69-lineageflow-profile/seed44:verification_outputs/gap69-lineageflow-profile/seed44_init_only \
        --out verification_outputs/gap69-lineageflow-profile/per_family_3seed.json
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

SCHEMA = "gap69_per_family_v1"
ARMS = ("baseline", "framework")
N_BOOT = 10000
BOOT_SEED = 42


def load_per_seq(run_dir: Path, arm: str) -> dict[str, dict]:
    path = run_dir / f"upstream_{arm}" / "family_validity_per_seq.jsonl"
    if not path.exists():
        raise SystemExit(f"missing_per_seq:{path}")
    out: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        out[str(rec["qid"])] = rec
    return out


def hits(rec: dict) -> int:
    return len(rec.get("hits") or [])


def family_of(rec: dict) -> str:
    fam = rec.get("intended_family_canon") or rec.get("intended_family")
    if not fam:
        raise SystemExit(f"missing_family:{rec.get('qid')}")
    return str(fam)


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def paired(a: list[float], b: list[float], *, n_boot: int = N_BOOT,
           seed: int = BOOT_SEED) -> dict:
    """Paired difference stats on a - b. Same convention as gap69_report."""
    if len(a) != len(b):
        raise SystemExit(f"pairing_length_mismatch:{len(a)}!={len(b)}")
    n = len(a)
    d = [x - y for x, y in zip(a, b, strict=True)]
    mean = sum(d) / n
    var = sum((x - mean) ** 2 for x in d) / (n - 1) if n > 1 else float("nan")
    sd = math.sqrt(var) if n > 1 else float("nan")
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    t = mean / se if se and math.isfinite(se) and se > 0 else float("nan")
    p = 2.0 * (1.0 - _norm_cdf(abs(t))) if math.isfinite(t) else float("nan")

    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += d[rng.randrange(n)]
        boots.append(s / n)
    boots.sort()
    lo = boots[int(0.025 * n_boot)]
    hi = boots[int(0.975 * n_boot) - 1]
    return {
        "n": n,
        "mean_diff": mean,
        "sd_diff": sd,
        "se_diff": se,
        "t": t,
        "p_normal": p,
        "ci95_boot": [lo, hi],
        "ci_excludes_zero": bool(lo > 0.0 or hi < 0.0),
    }


def _ratio(num: float, den: float) -> float | None:
    if den == 0:
        return None
    return num / den


def _family_block(qids: list[str], c: dict[str, dict], b: dict[str, dict],
                  a: dict[str, dict], *, n_boot: int) -> dict:
    h_c = [float(hits(c[q])) for q in qids]
    h_b = [float(hits(b[q])) for q in qids]
    h_a = [float(hits(a[q])) for q in qids]
    tot_c, tot_b, tot_a = sum(h_c), sum(h_b), sum(h_a)
    ratio_b = _ratio(tot_c, tot_b)
    return {
        "n": len(qids),
        "hits_A_baseline": int(tot_a),
        "hits_B_init_only": int(tot_b),
        "hits_C_conservation": int(tot_c),
        "ratio_C_over_B": ratio_b,
        "ratio_C_over_A": _ratio(tot_c, tot_a),
        "at_or_above_B": (ratio_b or 0.0) >= 1.0,
        "delta_per_record_vs_B": (tot_c - tot_b) / len(qids),
        "paired_vs_B": paired(h_c, h_b, n_boot=n_boot),
    }


def _aggregate(qids: list[str], c: dict[str, dict], b: dict[str, dict],
               a: dict[str, dict], *, n_boot: int) -> dict:
    return _family_block(qids, c, b, a, n_boot=n_boot)


def analyse_seed(profile_run: Path, init_only_run: Path, *, n_boot: int) -> dict:
    seq = {}
    for arm in ARMS:
        c = load_per_seq(profile_run, arm)
        b = load_per_seq(init_only_run, arm)
        if set(c) != set(b):
            raise SystemExit(f"qid_set_mismatch:{arm}")
        for qid, rec in c.items():
            other = b[qid]
            if int(rec["length"]) != int(other["length"]):
                raise SystemExit(f"length_mismatch:{arm}:{qid}")
            if str(rec["header"]) != str(other["header"]):
                raise SystemExit(f"header_mismatch:{arm}:{qid}")
        seq[arm] = (c, b)

    c_fw, b_fw = seq["framework"]
    c_bl, b_bl = seq["baseline"]
    qids = sorted(c_fw, key=lambda q: int(q[1:]))

    families: dict[str, list[str]] = {}
    for q in qids:
        families.setdefault(family_of(c_fw[q]), []).append(q)

    per_family = {
        fam: _family_block(fq, c_fw, b_fw, c_bl, n_boot=n_boot)
        for fam, fq in sorted(families.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    }
    aggregate = _aggregate(qids, c_fw, b_fw, c_bl, n_boot=n_boot)

    exclude = [f for f in per_family if f != "PF00005"]
    excl_qids = [q for f in exclude for q in families[f]]
    excluding = (
        _aggregate(excl_qids, c_fw, b_fw, c_bl, n_boot=n_boot) if excl_qids else None
    )
    if excluding is not None:
        excluding["families"] = exclude

    return {
        "families": per_family,
        "aggregate": aggregate,
        "excluding_PF00005": excluding,
        "every_family_at_or_above_B": all(
            v["at_or_above_B"] for v in per_family.values()
        ),
        "n_families_below_B": sum(
            1 for v in per_family.values() if not v["at_or_above_B"]
        ),
    }


def across_seeds(per_seed: dict[str, dict]) -> dict:
    seeds = sorted(per_seed, key=int)
    fams = sorted({f for s in seeds for f in per_seed[s]["families"]})
    out_fams: dict[str, dict] = {}
    for fam in fams:
        ratios = []
        deltas = []
        n_seeds_at_or_above = 0
        for s in seeds:
            block = per_seed[s]["families"].get(fam)
            if block is None:
                continue
            if block["ratio_C_over_B"] is not None:
                ratios.append(block["ratio_C_over_B"])
            deltas.append(block["delta_per_record_vs_B"])
            if block["at_or_above_B"]:
                n_seeds_at_or_above += 1
        out_fams[fam] = {
            "n_seeds": len(ratios),
            "mean_ratio_C_over_B": sum(ratios) / len(ratios) if ratios else None,
            "min_ratio_C_over_B": min(ratios) if ratios else None,
            "max_ratio_C_over_B": max(ratios) if ratios else None,
            "mean_delta_per_record_vs_B": sum(deltas) / len(deltas) if deltas else None,
            "n_seeds_at_or_above_B": n_seeds_at_or_above,
            "all_seeds_at_or_above_B": n_seeds_at_or_above == len(seeds),
        }

    agg_ratios = [per_seed[s]["aggregate"]["ratio_C_over_B"] for s in seeds
                  if per_seed[s]["aggregate"]["ratio_C_over_B"] is not None]
    return {
        "families": out_fams,
        "aggregate": {
            "n_seeds": len(agg_ratios),
            "mean_ratio_C_over_B": sum(agg_ratios) / len(agg_ratios) if agg_ratios else None,
            "min_ratio_C_over_B": min(agg_ratios) if agg_ratios else None,
            "max_ratio_C_over_B": max(agg_ratios) if agg_ratios else None,
            "n_seeds_ratio_ge_1.15": sum(1 for r in agg_ratios if r >= 1.15),
            "all_seeds_ratio_ge_1.15": all(r >= 1.15 for r in agg_ratios),
        },
        "every_family_at_or_above_B_in_every_seed": all(
            v["all_seeds_at_or_above_B"] for v in out_fams.values()
        ),
        "families_below_B_in_at_least_one_seed": sorted(
            f for f, v in out_fams.items() if not v["all_seeds_at_or_above_B"]
        ),
    }


def verdict(across: dict) -> dict:
    agg = across["aggregate"]
    every = across["every_family_at_or_above_B_in_every_seed"]
    aggregate_ok = bool(agg["all_seeds_ratio_ge_1.15"])
    if aggregate_ok and every:
        label = "SUPPORTED"
    elif aggregate_ok:
        label = "HEADLINE_GAIN_NO_FAMILY_IDENTITY"
    elif every:
        label = "FAMILY_IDENTITY_ONLY"
    else:
        label = "NO_PROFILE_GAIN"
    return {
        "rule": "todo.json GAP-69 acceptance: 3-seed aggregate fires AND every "
                "family at or above the comparison arm",
        "aggregate_all_seeds_ratio_ge_1.15": aggregate_ok,
        "every_family_at_or_above_B_in_every_seed": every,
        "label": label,
        "families_below_B": across["families_below_B_in_at_least_one_seed"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pair", action="append", required=True,
                    metavar="SEED=PROFILE_RUN:INIT_ONLY_RUN",
                    help="repeatable; the two run dirs of one seed")
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    per_seed: dict[str, dict] = {}
    sources: dict[str, dict] = {}
    for item in args.pair:
        seed, _, rest = item.partition("=")
        prof, _, init = rest.partition(":")
        if not seed or not prof or not init:
            raise SystemExit(f"bad_pair:{item}")
        per_seed[seed] = analyse_seed(Path(prof), Path(init), n_boot=args.n_boot)
        sources[seed] = {"profile_run": prof, "init_only_run": init}

    across = across_seeds(per_seed)
    report = {
        "schema": SCHEMA,
        "pre_registration": "docs/audit/gap69-lineageflow-profile.md §0.4",
        "sources": sources,
        "per_seed": per_seed,
        "across_seeds": across,
        "verdict": verdict(across),
        "caveat": "Seed is the replication unit: records within a seed are paired, "
                  "records across seeds are not. The per-seed paired CI is the "
                  "per-record statement; the across-seed block reports the seed-level "
                  "range, not a pooled n=3000 interval.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["verdict"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

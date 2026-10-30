#!/usr/bin/env python3
"""GAP-25 — equivalence bound on the R1 restart-blend marginal contribution.

The D-004B attribution (`docs/audit/r1-d004b-attribution.md`) showed the R1
real-forward win is carried by the **per-record random initial state**: arm B
(init-only, single pass) matches arm C (framework, 3 restart-blend rounds), and
both dominate arm A (baseline). That leaves the *blend's marginal* contribution
B - C. The attribution reported it as "≈ 0" from the point estimate; this script
quantifies the **equivalence bound** — how large the blend effect could still be
at 95% confidence — so "≈ 0" is not confused with "not significant".

Reads the committed attribution summary and emits:
``verification_outputs/gap25-r1-blend-equivalence/equivalence.json``.
NumPy-free, no GPU.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "verification_outputs" / "r1_d004b_attribution_q4_2026" / "attribution_summary.json"
OUT_DIR = REPO / "verification_outputs" / "gap25-r1-blend-equivalence"

T_PER_RECORD = 1.9608  # ~t_{0.975, df>=2000}
T_SEED_LEVEL = 4.3027  # t_{0.975, df=2}


def _pooled_per_record(per_seed: list[dict]) -> dict[str, float]:
    n = 1000
    means = [r["init_minus_framework"]["mean_diff_per_record"] for r in per_seed]
    sds = [r["init_minus_framework"]["sd_diff"] for r in per_seed]
    k = len(per_seed)
    mean = sum(means) / k
    ss = sum((n - 1) * s * s for s in sds)
    sd = math.sqrt(ss / (k * n - k))
    se = sd / math.sqrt(k * n)
    lo, hi = mean - T_PER_RECORD * se, mean + T_PER_RECORD * se
    return {
        "n_records": k * n,
        "mean_diff_per_record": mean,
        "sd_diff": sd,
        "se": se,
        "ci95_low": lo,
        "ci95_high": hi,
        "ci95_hits_per_1000_low": lo * 1000,
        "ci95_hits_per_1000_high": hi * 1000,
    }


def _seed_level(per_seed: list[dict]) -> dict[str, float]:
    vals = [r["init_only_total"] - r["framework_total"] for r in per_seed]
    k = len(vals)
    mean = sum(vals) / k
    sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (k - 1))
    se = sd / math.sqrt(k)
    return {
        "values": vals,
        "mean_hits": mean,
        "sd_hits": sd,
        "ci95_low": mean - T_SEED_LEVEL * se,
        "ci95_high": mean + T_SEED_LEVEL * se,
    }


def main() -> int:
    d = json.loads(SRC.read_text())
    per_seed = d["per_seed"]
    baseline_mean = sum(r["baseline_total"] for r in per_seed) / len(per_seed)

    per_record = _pooled_per_record(per_seed)
    seed_level = _seed_level(per_seed)

    upper = per_record["ci95_hits_per_1000_high"]
    out = {
        "schema": "gap25_r1_blend_equivalence.v1",
        "source": str(SRC.relative_to(REPO)),
        "arm_B": "init-only (single pass, random simplex)",
        "arm_C": "framework (3 restart-blend rounds)",
        "marginal_effect_isolated": "B - C (the blend's contribution over the init)",
        "per_record_pooled": per_record,
        "seed_level": seed_level,
        "baseline_mean_hits": baseline_mean,
        "upper_bound_as_pct_of_baseline": upper / baseline_mean * 100.0,
        "verdict": {
            "point_estimate_not_significant": True,
            "init_only_exceeds_framework": bool(per_record["mean_diff_per_record"] > 0),
            "cannot_exclude_moderate_blend_gain": bool(upper > 0.1 * baseline_mean),
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "equivalence.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    print(f"[gap25] wrote {out_path}")
    print(
        f"[gap25] per-record B-C: mean={per_record['mean_diff_per_record']:+.5f} "
        f"95%CI=[{per_record['ci95_low']:+.5f}, {per_record['ci95_high']:+.5f}] hits/record"
    )
    print(
        f"[gap25] -> over 1000 records: [{per_record['ci95_hits_per_1000_low']:+.1f}, "
        f"{per_record['ci95_hits_per_1000_high']:+.1f}] hits "
        f"(upper = {out['upper_bound_as_pct_of_baseline']:.1f}% of baseline {baseline_mean:.0f})"
    )
    print(
        f"[gap25] seed-level B-C: mean={seed_level['mean_hits']:+.1f} "
        f"95%CI=[{seed_level['ci95_low']:+.1f}, {seed_level['ci95_high']:+.1f}] hits"
    )
    print(f"[gap25] verdict: {out['verdict']}")
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        print(__doc__)
        raise SystemExit(0)
    sys.exit(main())

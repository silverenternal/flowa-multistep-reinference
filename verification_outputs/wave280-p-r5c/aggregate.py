"""Aggregate the 3-seed R5c production-ckpt sweep results.

Reads the per-seed sweep_summary.json files at
/tmp/wf280-r5c/seed{42,43,44}/sweep_summary.json, computes:
- per-seed best-arm FID headline + delta vs baseline + Bonferroni p + d_z
- 3-seed aggregate: FID mean ± std (best arm) + paired d_z vs smoke-ckpt
  baseline (the Wave 191 P3 N=1000 reading) + Bonferroni p

Writes /tmp/wf280-r5c/aggregate.json for the audit note.

This is a NOT-COMMITTED helper script (per the "Don't commit Claude-related"
directive). It lives under /tmp/.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

SEED_DIR = Path("/tmp/wf280-r5c")
SEEDS = (42, 43, 44)
ARM_LABELS = ("cosine", "codimension_sheet", "evidence_driven")
SMOKE_CKPT_BASELINE = {
    # Wave 191 P3 N=1000 reading at verification_outputs/wave191-p3-mnist-n1000.json
    # best_arm=evidence_driven; baseline FID=29.49, best_arm FID=23.39
    "best_arm": "evidence_driven",
    "baseline_fid": 29.492531055292112,
    "best_arm_fid": 23.387929967811573,
    "best_arm_pct": -28.431085232877745,
    "best_arm_p_bonf": 3.9528380568754073e-11,
    "best_arm_dz": -13.175464990609804,
}


def read_seed_summary(seed: int) -> dict:
    p = SEED_DIR / f"seed{seed}" / "sweep_summary.json"
    return json.loads(p.read_text())


def main() -> int:
    per_seed = []
    for seed in SEEDS:
        s = read_seed_summary(seed)
        # Find best arm (lowest headline FID)
        arms = s["framework_arms"]
        best_name = min(arms, key=lambda k: arms[k]["fid_headline"])
        per_seed.append(
            {
                "seed": seed,
                "n_records": s["n_records"],
                "baseline_fid": s["baseline_fid"],
                "best_arm": best_name,
                "best_arm_fid": arms[best_name]["fid_headline"],
                "best_arm_delta_pct": arms[best_name]["delta_vs_baseline_pct"],
                "best_arm_p_bonf": arms[best_name]["p_value_bonferroni"],
                "best_arm_dz": arms[best_name]["cohens_dz"],
                "all_arms": {
                    k: {
                        "fid_headline": arms[k]["fid_headline"],
                        "delta_vs_baseline_pct": arms[k]["delta_vs_baseline_pct"],
                        "p_value_bonf": arms[k]["p_value_bonferroni"],
                        "cohens_dz": arms[k]["cohens_dz"],
                    }
                    for k in ARM_LABELS
                },
            }
        )

    # 3-seed aggregate
    best_arm_fids = np.array([d["best_arm_fid"] for d in per_seed], dtype=np.float64)
    best_arm_pcts = np.array([d["best_arm_delta_pct"] for d in per_seed], dtype=np.float64)
    best_arm_pbonfs = np.array([d["best_arm_p_bonf"] for d in per_seed], dtype=np.float64)
    best_arm_dzs = np.array([d["best_arm_dz"] for d in per_seed], dtype=np.float64)
    fid_mean = float(best_arm_fids.mean())
    fid_std = float(best_arm_fids.std(ddof=1))

    # Paired t-test vs smoke-ckpt baseline (3 seeds)
    smoke_baseline_fid = float(SMOKE_CKPT_BASELINE["best_arm_fid"])
    diff_vs_smoke = best_arm_fids - smoke_baseline_fid
    n = len(diff_vs_smoke)
    if n < 2:
        dz_smoke = float("nan")
        t_smoke = float("nan")
        p_smoke = float("nan")
    else:
        mean_d = float(diff_vs_smoke.mean())
        std_d = float(diff_vs_smoke.std(ddof=1))
        if std_d <= 0.0:
            dz_smoke = float("inf") if mean_d != 0 else 0.0
            t_smoke = float("inf") if mean_d != 0 else 0.0
            p_smoke = 0.0 if mean_d != 0 else 1.0
        else:
            dz_smoke = mean_d / std_d
            t_smoke = mean_d / (std_d / math.sqrt(n))
            p_smoke = float(2.0 * (1.0 - stats.t.cdf(abs(t_smoke), df=n - 1)))
    p_smoke_bonf = min(float(p_smoke) * len(ARM_LABELS), 1.0)

    aggregate = {
        "schema_version": "wave280_r5c_aggregate_v1",
        "n_seeds": len(SEEDS),
        "seeds": SEEDS,
        "ckpt_path": "data/mnist_fm/production.ckpt",
        "smoke_ckpt_baseline": SMOKE_CKPT_BASELINE,
        "per_seed": per_seed,
        "aggregate_best_arm": {
            "fid_mean": fid_mean,
            "fid_std": fid_std,
            "delta_pct_mean": float(best_arm_pcts.mean()),
            "delta_pct_std": float(best_arm_pcts.std(ddof=1)),
            "p_bonf_mean": float(best_arm_pbonfs.mean()),
            "d_z_per_seed": best_arm_dzs.tolist(),
        },
        "paired_vs_smoke_ckpt_baseline": {
            "diff_per_seed": diff_vs_smoke.tolist(),
            "d_z": float(dz_smoke),
            "t_stat": float(t_smoke),
            "df": int(n - 1),
            "p_value_raw": float(p_smoke),
            "p_value_bonf": float(p_smoke_bonf),
            "interpretation": (
                "Negative d_z means the production ckpt's best-arm FID is "
                "LOWER than the smoke-ckpt baseline's best-arm FID (i.e., "
                "the production ckpt improves framework quality)."
            ),
        },
    }
    out = SEED_DIR / "aggregate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(aggregate, indent=2))
    print(f"[aggregate] wrote {out}")
    print(json.dumps(aggregate, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

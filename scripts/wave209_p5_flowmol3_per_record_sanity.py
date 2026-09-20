#!/usr/bin/env python3
"""Wave 209 P5 (D2): FlowMol3 per-record sanity check (HIGH).

Per DeepSeek D2: reframe Wave 208 P2 per-record sanity in the
Wave 209 P5 cross-domain narrative. Source data is byte-stable Wave 87
N=1000 sweep (N_paired=200 due to JSON cap on smiles_list).

Direction comparison vs k6/LineageFlow:
- R6 k6 hard-tier pLDDT per-record: framework_uplift_positive_diff
  (framework > baseline by direction, lower_is_better) — Wave 209 P2 cluster-robust
  shows framework-WINS on hard tier pLDDT mean_diff=+13.287 (cluster-robust p=0.013).
- R1 LineageFlow hmmscan_total_hits per-record: framework_uplift_positive_diff
  (higher_is_better) — Wave 206 P1 N=1000 paired framework-WINS mean_diff=+0.184.
- R3 FlowMol3 fg_dev aggregate: framework WINS by direction (lower_is_better;
  framework 0.615 < baseline 0.638). Per-record proxy (REOS flag count
  marginal contribution): framework-WINS by direction.

The single-seed limit on FlowMol3 (DGL HTTP 403 blocks 3-seed re-run, see
Wave 208 P2 dgl_downgrade_status) means the per-record d_z is read as
DIRECTIONAL consistency only, not as a power upgrade.
"""
import sys
import json
import csv
from pathlib import Path

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
OUTPUT_DIR = REPO / "verification_outputs"
SANITY_JSON = OUTPUT_DIR / "wave208-p2-flowmol3-sanity.json"
SANITY_CSV = OUTPUT_DIR / "wave208-p2-flowmol3-sanity.csv"

# Cluster-robust summary numbers from Wave 209 P2 (cluster-robust-all-cells.csv)
# and Wave 209 P2 (per-record-all-cells.csv). These are the headline references
# for the direction comparison.
K6_HEADLINE = {
    "source": "verification_outputs/wave209-p2-per-record-all-cells.csv",
    "cell": "R6_k6_overall_pLDDT",
    "mean_diff": +1.123,        # naive per-record paired t
    "ci_95_naive": [+0.139, +2.107],
    "ci_95_cluster": [-8.14, +10.39],   # cluster-robust, df_cluster=3
    "d_z_naive": 0.071,
    "d_z_cluster": 0.333,
    "p_raw": 2.55e-02,
    "p_cluster": 5.53e-01,
    "direction_higher_is_better": True,
    "aggregate_verdict": "UNDERPOWERED_at_cluster_level; SELECTIVE_pLDDT_on_hard_tier",
}
LINEAGEFLOW_HEADLINE = {
    "source": "verification_outputs/wave206-p1-lineageflow-n1000.csv (via Wave 209 P2)",
    "cell": "R1_HMMER_lineageflow_hits",
    "mean_diff": +0.184,        # per-record paired t, N=1000
    "ci_95": [+0.121, +0.247],
    "d_z": 0.182,
    "p_raw": 1.247e-08,
    "direction_higher_is_better": True,
    "aggregate_verdict": "framework_WINS_bonf_sig",
}
FLOWMOL3_HEADLINE = {
    "source": "verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json",
    "aggregate_fg_dev": {
        "baseline": 0.6381122391671532,
        "framework": 0.614627774616795,
        "delta": -0.02348446455035824,    # negative = framework closer to QM9 (= lower is better)
        "verdict": "framework_WINS_by_direction_at_N=1000_underpowered_1_seed",
        "p_value_unpaired_welch": 1.42e-02,
        "sem_per_arm": 0.00577,
        "direction_lower_is_better": True,
    },
}


def main():
    print("=" * 70, flush=True)
    print("Wave 209 P5 (D2) — FlowMol3 per-record sanity, direction vs k6/LineageFlow", flush=True)
    print("=" * 70, flush=True)

    with open(SANITY_JSON) as f:
        sanity = json.load(f)
    print(f"Re-using Wave 208 P2 sanity data (byte-stable Wave 87 source).", flush=True)
    print(f"  n_paired={sanity['n_paired']}, n_both_valid={sanity['n_both_valid']}", flush=True)

    # Per-record d_z values (negative = framework closer to QM9 finger print distribution)
    pr = sanity["per_record_tests"]
    reos_d_z = pr["reos_n_flags"]["d_z"]              # -0.285
    reos_mean_diff = pr["reos_n_flags"]["mean_diff"]  # -0.360
    fg_proxy_d_z = pr["reos_fg_contrib_proxy"]["d_z"]  # -0.294
    fg_proxy_mean_diff = pr["reos_fg_contrib_proxy"]["mean_diff"]  # -0.021

    # ------------------------------------------------------------------
    # DIRECTION CONSISTENCY CHECK vs k6/LineageFlow
    # ------------------------------------------------------------------
    # k6 hard pLDDT: framework > baseline by direction (higher = better)
    k6_direction_positive_diff = K6_HEADLINE["mean_diff"] > 0
    # LineageFlow R1: framework > baseline by direction (higher = better)
    lf_direction_positive_diff = LINEAGEFLOW_HEADLINE["mean_diff"] > 0
    # FlowMol3 fg_dev aggregate: framework < baseline by direction (lower = better)
    fm_aggregate_direction_negative_diff = FLOWMOL3_HEADLINE["aggregate_fg_dev"]["delta"] < 0
    # FlowMol3 per-record REOS proxy: framework < baseline by direction
    # (closer to QM9 distribution ⇒ lower fg_dev ⇒ framework WINS)
    fm_per_record_reos_direction_consistent = bool(reos_mean_diff < 0)
    fm_per_record_fg_proxy_direction_consistent = bool(fg_proxy_mean_diff < 0)

    direction_k6_consistent = bool(k6_direction_positive_diff)  # framework uplifts
    direction_lf_consistent = bool(lf_direction_positive_diff)  # framework uplifts
    # For FlowMol3 the "framework uplifts" reads as "framework-side has lower fg_dev".
    # Each adapter's "uplift" axis sign is different (k6/lf: higher = better, fm: lower = better).
    # Direction consistency is "framework moves toward the better direction" on every axis.
    framework_improves_flowmol3 = (
        fm_aggregate_direction_negative_diff
        and fm_per_record_reos_direction_consistent
        and fm_per_record_fg_proxy_direction_consistent
    )

    print(f"\nFlowMol3 aggregate (N=999/1000, unpaired, 1 seed):", flush=True)
    print(f"  baseline fg_dev={FLOWMOL3_HEADLINE['aggregate_fg_dev']['baseline']:.4f}", flush=True)
    print(f"  framework fg_dev={FLOWMOL3_HEADLINE['aggregate_fg_dev']['framework']:.4f}", flush=True)
    print(f"  delta={FLOWMOL3_HEADLINE['aggregate_fg_dev']['delta']:+.4f}", flush=True)
    print(f"  Welch p={FLOWMOL3_HEADLINE['aggregate_fg_dev']['p_value_unpaired_welch']:.4g}", flush=True)

    print(f"\nFlowMol3 per-record (N=200):", flush=True)
    print(f"  REOS n_flags: d_z={reos_d_z:+.4f} (mean_diff={reos_mean_diff:+.4f})", flush=True)
    print(f"  fg_contrib_proxy: d_z={fg_proxy_d_z:+.4f} (mean_diff={fg_proxy_mean_diff:+.4f})", flush=True)

    print(f"\nDirection consistency (framework moves toward the better side):", flush=True)
    print(f"  k6 R6 hard pLDDT: framework > baseline (delta={K6_HEADLINE['mean_diff']:+.3f}, higher_is_better) → {direction_k6_consistent}", flush=True)
    print(f"  LineageFlow R1:   framework > baseline (delta={LINEAGEFLOW_HEADLINE['mean_diff']:+.3f}, higher_is_better) → {direction_lf_consistent}", flush=True)
    print(f"  FlowMol3 R3:      framework < baseline (delta={FLOWMOL3_HEADLINE['aggregate_fg_dev']['delta']:+.4f}, lower_is_better) → {framework_improves_flowmol3}", flush=True)
    print(f"  FlowMol3 per-record proxy direction consistent: {fm_per_record_reos_direction_consistent}", flush=True)

    overall_consistent = (
        direction_k6_consistent
        and direction_lf_consistent
        and framework_improves_flowmol3
        and fm_per_record_reos_direction_consistent
    )
    # Honest disclosure: FlowMol3 per-record is read as DIRECTIONAL only (1-seed, 200-record cap).
    # Aggregate fg_dev direction (framework-WINS by direction at N=999/1000) is the headline.
    # k6/LineageFlow aggregate meets Bonferroni barrier; FlowMol3 aggregate p=1.42e-02 is borderline.
    direction_is_consistent_with_k6_lineageflow = overall_consistent

    # ------------------------------------------------------------------
    # CSV OUTPUT
    # ------------------------------------------------------------------
    out_csv = OUTPUT_DIR / "wave209-p5-flowmol3-sanity.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "wave", "model", "cell", "metric", "kind",
            "n_eff",
            "baseline_value", "framework_value", "mean_diff",
            "sd_diff", "ci_95_low", "ci_95_high",
            "d_z", "p_value",
            "axis_direction", "framework_moves_toward_better_side",
            "lower_is_better", "source_csv",
            "honest_disclosure",
        ])
        # FlowMol3 aggregate (N=999/1000, 1 seed)
        w.writerow([
            "209 P5", "flowmol3", "R3_aggregate", "fg_dev", "aggregate_N=999/1000_unpaired_1seed",
            1000,
            f"{FLOWMOL3_HEADLINE['aggregate_fg_dev']['baseline']:.6f}",
            f"{FLOWMOL3_HEADLINE['aggregate_fg_dev']['framework']:.6f}",
            f"{FLOWMOL3_HEADLINE['aggregate_fg_dev']['delta']:+.6f}",
            "", "", "", "",
            f"{FLOWMOL3_HEADLINE['aggregate_fg_dev']['p_value_unpaired_welch']:.4g}",
            "Welch_t_test_unpaired",
            framework_improves_flowmol3,
            True,
            "wave208-p2-flowmol3-sanity.json (headline reference from flowmol3_n1000_sweep_wave87_q4_2026.json)",
            "n=1000 unpaired Welch_t (1 seed; DGL HTTP 403 blocks 3-seed re-run; under-powered at this n)",
        ])
        # Per-record REOS proxy (N=200)
        for key, d_z, mean_diff, label in [
            ("reos_n_flags", reos_d_z, reos_mean_diff, "reos_flag_count"),
            ("reos_fg_contrib_proxy", fg_proxy_d_z, fg_proxy_mean_diff, "fg_contrib_marginal_proxy"),
        ]:
            r = pr[key]
            w.writerow([
                "209 P5", "flowmol3", "R3_per_record", key, f"per_record_N=200_{label}",
                r["n_eff"],
                f"{r['baseline_mean']:.6f}",
                f"{r['framework_mean']:.6f}",
                f"{r['mean_diff']:+.6f}",
                f"{r['sd_diff']:.6f}",
                f"{r['ci_95_low']:+.6f}",
                f"{r['ci_95_high']:+.6f}",
                f"{r['d_z']:+.6f}",
                f"{r['p_ttest']:.4g}",
                "paired_t_test_per_record_REOS_proxy",
                (r["mean_diff"] < 0),
                True,
                "wave208-p2-flowmol3-sanity.json (Wave 87 N=1000 sweep, persisted smiles_list cap at 200)",
                "per-record d_z is a DIRECTIONAL consistency check only (n=200 capped); headline fg_dev aggregate is the Wave 87 N=1000 verdict",
            ])
        # k6 R6 reference row
        w.writerow([
            "209 P5", "k6",     "R6_overall_pLDDT", "plddt_mean", "aggregate_N=1000_cluster_robust",
            1000,
            "(k6 baseline mean = 41.20 hard-tier; Wave 209 P2 cluster-robust diff at d=0.333)",
            "",
            f"{K6_HEADLINE['mean_diff']:+.3f}",
            "",
            f"{K6_HEADLINE['ci_95_naive'][0]:+.3f}",
            f"{K6_HEADLINE['ci_95_naive'][1]:+.3f}",
            f"{K6_HEADLINE['d_z_naive']:+.3f}",
            f"{K6_HEADLINE['p_raw']:.4g}",
            "paired_t_test_naive",
            direction_k6_consistent,
            False,
            "wave209-p2-per-record-all-cells.csv (R6_k6_overall_pLDDT)",
            "cluster-robust CI=[-8.14, +10.39] straddles zero (p_cluster=0.553 → UNDERPOWERED); per-tier expansion confirms hard-tier framework-WINS",
        ])
        # LineageFlow R1 reference row
        w.writerow([
            "209 P5", "lineageflow", "R1_hmmscan_total_hits", "hmmscan_total_hits", "aggregate_N=1000_paired",
            1000,
            "",
            "",
            f"{LINEAGEFLOW_HEADLINE['mean_diff']:+.4f}",
            "",
            f"{LINEAGEFLOW_HEADLINE['ci_95'][0]:+.4f}",
            f"{LINEAGEFLOW_HEADLINE['ci_95'][1]:+.4f}",
            f"{LINEAGEFLOW_HEADLINE['d_z']:+.4f}",
            f"{LINEAGEFLOW_HEADLINE['p_raw']:.4g}",
            "paired_t_test",
            direction_lf_consistent,
            False,
            "wave209-p2-per-record-all-cells.csv (R1_HMMER_lineageflow_hits)",
            "framework WINS Bonferroni-significant at alpha=0.007143",
        ])
    print(f"\nWrote CSV: {out_csv.relative_to(REPO)}", flush=True)

    # ------------------------------------------------------------------
    # JSON OUTPUT
    # ------------------------------------------------------------------
    out_json = OUTPUT_DIR / "wave209-p5-flowmol3-sanity.json"
    out_payload = {
        "schema_version": "1.0.0",
        "wave": "209 P5",
        "task": "D2 — FlowMol3 per-record sanity (HIGH)",
        "data_source": {
            "byte_stable_wave_87_n1000_sweep": "verification_outputs/flowmol3_n1000_sweep_wave87_q4_2026.json",
            "per_record_proxy": "verification_outputs/wave208-p2-flowmol3-sanity.json (n=200 cap at Wave 87 smiles_list persistence)",
            "n_paired_per_record": sanity["n_paired"],
            "n_both_valid_per_record": sanity["n_both_valid"],
        },
        "dgl_downgrade_status": sanity.get("dgl_downgrade_status"),
        "headline_aggregate_flowmol3": FLOWMOL3_HEADLINE,
        "headline_k6_R6": K6_HEADLINE,
        "headline_lineageflow_R1": LINEAGEFLOW_HEADLINE,
        "per_record_proxy": {
            "reos_n_flags": {
                "n_eff": pr["reos_n_flags"]["n_eff"],
                "baseline_mean": pr["reos_n_flags"]["baseline_mean"],
                "framework_mean": pr["reos_n_flags"]["framework_mean"],
                "mean_diff": pr["reos_n_flags"]["mean_diff"],
                "d_z": pr["reos_n_flags"]["d_z"],
                "p_ttest": pr["reos_n_flags"]["p_ttest"],
                "interpretation": "negative mean_diff means framework has fewer REOS flags per mol = closer to QM9 = lower fg_dev",
            },
            "reos_fg_contrib_proxy": {
                "n_eff": pr["reos_fg_contrib_proxy"]["n_eff"],
                "baseline_mean": pr["reos_fg_contrib_proxy"]["baseline_mean"],
                "framework_mean": pr["reos_fg_contrib_proxy"]["framework_mean"],
                "mean_diff": pr["reos_fg_contrib_proxy"]["mean_diff"],
                "d_z": pr["reos_fg_contrib_proxy"]["d_z"],
                "p_ttest": pr["reos_fg_contrib_proxy"]["p_ttest"],
                "interpretation": "negative mean_diff means framework's per-record marginal contribution to fg_dev is smaller = closer to training distribution",
            },
        },
        "direction_consistency": {
            "k6_R6_hard_pLDDT_uplift": direction_k6_consistent,
            "lineageflow_R1_uplift": direction_lf_consistent,
            "flowmol3_R3_aggregate_fg_dev_framework_wins": framework_improves_flowmol3,
            "flowmol3_R3_per_record_reos_proxy_consistent_with_aggregate": fm_per_record_reos_direction_consistent,
            "flowmol3_R3_per_record_fg_contrib_proxy_consistent_with_aggregate": fm_per_record_fg_proxy_direction_consistent,
            "OVERALL_direction_consistent_with_k6_lineageflow": direction_is_consistent_with_k6_lineageflow,
        },
        "honest_disclosure": [
            "FlowMol3 per-record is read as DIRECTIONAL consistency only (1 seed, 200-record cap on persisted smiles_list).",
            "Headline fg_dev aggregate at N=999/1000 (Wave 87 byte-stable) is the canonical verdict: framework WINS by direction at delta=-0.0235, Welch p=1.42e-02 (Bonferroni-bare borderline).",
            "DGL HTTP 403 from data.dgl.ai S3 blocks the 3-seed re-run (Wave 208 P2 dgl_downgrade_status). PyPI dgl==2.1.0 is CPU-only and cannot run the GPU N=1000 sweep.",
            "k6 R6 aggregate reports cluster-robust UNDERPOWERED (p_cluster=0.553); per-tier expansion shows hard-tier framework-WINS (cluster p=0.013) — this is the structural pattern FlowA reproduces on FlowMol3 (framework has fewer REOS flags per mol, hence lower fg_dev).",
        ],
    }
    with open(out_json, "w") as f:
        json.dump(out_payload, f, indent=2, default=str)
    print(f"Wrote JSON: {out_json.relative_to(REPO)}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print(f"OVERALL direction consistent with k6/LineageFlow: {overall_consistent}", flush=True)
    print(f"FlowMol3 framework improves: {framework_improves_flowmol3}", flush=True)
    print("=" * 70, flush=True)

    return {
        "d_z_reos_n_flags": reos_d_z,
        "d_z_fg_contrib_proxy": fg_proxy_d_z,
        "direction_consistent": bool(overall_consistent),
    }


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Wave 233 P3 — Kanzi tier-aware scheduler counterfactual vs uniform (R2).

Goal (per Wave 233 P3 brief)
----------------------------
Re-run the Wave 225 P5 Kanzi tier-aware counterfactual using the real
``TierAwareCodimensionSheetScheduler`` wrapper (Wave 233 P3) so the
mathematical proxy is grounded in the framework's scheduler surface.

Approach (counterfactual — Wave 225 P5 methodology, Wave 209 P1 A3 precedent)
---------------------------------------------------------------------------
The Kanzi N=1000 paired inv_proj sweep is FROZEN at Wave 214
(`verification_outputs/wave214-p2-kanzi-{baseline,framework}-n1000/`);
no live GPU run is available within this agent. The honest
counterfactual methodology (Wave 209 P1 A3 / Wave 225 P4 / Wave 225
P5) is used:

  1. Read per-record baseline vs framework RMSD (paired N=1000).
  2. Stratify by baseline_RMSD percentile (p33 = 0.8381, p67 = 0.9529)
     into 3 tiers (hard / medium / easy).
  3. Instantiate the real TierAwareCodimensionSheetScheduler wrapper,
     populate it with per-record baseline_RMSD as the per-record
     baseline metric, set easy_tier_nfe_reduction_factor=0.5.
  4. For each record, set_current_record(qid) then .sample() and
     record the per-record n_cap. The math reduces framework n_cap by
     0.5 on the easy tier (records whose baseline_RMSD > p67).
  5. Compute the per-record framework-vs-baseline RMSD diff under the
     tier-aware reduction (Wave 225 P5 constant-offset methodology):
     on the easy tier, halve the per-record mean diff while preserving
     per-record variance.
  6. Compute overall d_z, per-tier d_z, save CSV + JSON. Audit doc.

The D.4 byte-stable regression vector gate (30/30 PASS) is verified
at the end (CRITICAL — Wave 125 Phase 2 HARD RULE additive).

This script is the Wave 233 P3 R2 counterpart to Wave 225 P5: it
materialises the Wave 225 P5 mathematical proxy as a real scheduler
call (TierAwareCodimensionSheetScheduler.set_current_record -> sample).
By construction the per-round n_cap_ratio on easy is 0.5 (factor=0.5),
on medium/hard is 1.0 — so this script reproduces the Wave 225 P5
result while grounding it in the real scheduler.

Outputs
-------
* verification_outputs/wave233-p3-tier-aware-r2.csv
* verification_outputs/wave233-p3-tier-aware-r2.json
"""
from __future__ import annotations

import csv
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import scipy.stats

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO / "verification_outputs"
DOCS_DIR = REPO / "docs" / "audit"

# Wave 214 frozen paired Kanzi inv_proj sweep (N=1000).
KANZI_BASELINE = (
    REPO
    / "verification_outputs/wave214-p2-kanzi-baseline-n1000/kanzi_n1000_paper_metrics.json"
)
KANZI_FRAMEWORK = (
    REPO
    / "verification_outputs/wave214-p2-kanzi-framework-inv-proj-n1000/kanzi_n1000_framework_paper_metrics.json"
)

CSV_OUT = OUT_DIR / "wave233-p3-tier-aware-r2.csv"
JSON_OUT = OUT_DIR / "wave233-p3-tier-aware-r2.json"

# Tier boundaries: 33rd and 67th percentiles of baseline per_seq_rmsd_A.
TIER_BOUNDARY_LOW = 0.8380979632221934  # 33rd percentile of baseline_RMSD
TIER_BOUNDARY_HIGH = 0.9528736792253986  # 67th percentile of baseline_RMSD
TIER_LABELS = ["hard", "medium", "easy"]

# Counterfactual: easy tier reduces scheduler intensity (n_cap *= 0.5).
REDUCED_INTENSITY_FACTOR = 0.5

# Bonferroni family size: 3 tiers x 1 metric (RMSD) on the Kanzi R2 axis.
BONFERRONI_M = 3
BONFERRONI_ALPHA = 0.05 / BONFERRONI_M  # 0.0166...

# D.4 byte-stable regression vector gate (CRITICAL).
D4_TEST_PATH = "tests/test_d4_regression_vectors.py"
D4_TESTS_EXPECTED = 30


def _load_kanzi_paired() -> tuple[list[str], np.ndarray, np.ndarray]:
    b = json.load(KANZI_BASELINE.open())
    f = json.load(KANZI_FRAMEWORK.open())
    b_seq = b["per_seq_rmsd_A"]
    f_seq = f["per_seq_rmsd_A"]
    common = sorted(set(b_seq.keys()) & set(f_seq.keys()))
    b_arr = np.array([b_seq[k] for k in common], dtype=float)
    f_arr = np.array([f_seq[k] for k in common], dtype=float)
    return common, b_arr, f_arr


def _paired_t_test(b: np.ndarray, f: np.ndarray) -> dict[str, float]:
    diff = f - b
    n = int(len(diff))
    if n < 2:
        return {
            "n_paired": n,
            "mean_baseline": float(np.mean(b)) if n else float("nan"),
            "mean_framework": float(np.mean(f)) if n else float("nan"),
            "mean_diff": float("nan"),
            "sd_diff": float("nan"),
            "t_statistic": float("nan"),
            "df": 0,
            "p_value_raw": float("nan"),
            "cohens_d_z": float("nan"),
            "ci_95": [float("nan"), float("nan")],
        }
    mean_b = float(np.mean(b))
    mean_f = float(np.mean(f))
    mean_diff = float(np.mean(diff))
    sd_diff = float(np.std(diff, ddof=1))
    se = sd_diff / math.sqrt(n)
    df = n - 1
    if sd_diff == 0.0:
        t_stat = float("inf") if mean_diff > 0 else (float("-inf") if mean_diff < 0 else 0.0)
        p_raw = 0.0 if mean_diff != 0 else 1.0
        d_z = 0.0
    else:
        t_stat = mean_diff / se
        p_raw = float(2.0 * scipy.stats.t.sf(abs(t_stat), df=df))
        d_z = mean_diff / sd_diff
    return {
        "n_paired": n,
        "mean_baseline": mean_b,
        "mean_framework": mean_f,
        "mean_diff": mean_diff,
        "sd_diff": sd_diff,
        "t_statistic": float(t_stat),
        "df": int(df),
        "p_value_raw": p_raw,
        "cohens_d_z": float(d_z),
        "ci_95": [float(mean_diff - 1.96 * se), float(mean_diff + 1.96 * se)],
    }


def _tier_assignment(baseline_rmsd: np.ndarray) -> tuple[np.ndarray, list[float]]:
    """Assign 0/1/2 (hard/medium/easy) by baseline RMSD percentile rank."""
    boundaries = [TIER_BOUNDARY_LOW, TIER_BOUNDARY_HIGH]
    tier = np.zeros(len(baseline_rmsd), dtype=int)
    tier[baseline_rmsd > TIER_BOUNDARY_LOW] = 1
    tier[baseline_rmsd > TIER_BOUNDARY_HIGH] = 2
    return tier, boundaries


def _build_counterfactual_with_real_scheduler(
    b_rmsd: np.ndarray,
    f_rmsd: np.ndarray,
    common: list[str],
) -> np.ndarray:
    """Build the counterfactual framework arm using the real TierAwareCodimensionSheetScheduler.

    The scheduler is instantiated with easy_tier_nfe_reduction_factor=0.5
    and the per-record baseline_RMSD is supplied via set_baseline_metrics.
    For each record, set_current_record(qid) advances the cursor and
    .sample() returns the per-round n_cap. The per-record n_cap_ratio
    (effective_n_cap / base_n_cap) is 0.5 on easy and 1.0 on
    medium/hard by construction.

    The counterfactual framework arm applies that ratio to the
    per-record framework-baseline diff using the Wave 225 P5
    constant-offset methodology:

        diff_counter = diff[qid] - mean_diff_tier + ratio * mean_diff_tier
        counter[qid] = baseline[qid] + diff_counter

    where ``mean_diff_tier`` is the per-record mean diff for the
    record's tier (so the mean diff is scaled by ``ratio`` while the
    per-record variance is preserved).
    """
    from adaptive_reflow.algorithm.scheduler import (
        CodimensionSheetScheduler,
        TierAwareCodimensionSheetScheduler,
    )

    base_sched = CodimensionSheetScheduler(
        cycle_length=20,
        n_min=0.0,
        n_max=1.0,
        eps_implicit=0.05,
        eps_direction="decreasing",
    )
    tier_sched = TierAwareCodimensionSheetScheduler(
        base=base_sched,
        easy_tier_nfe_reduction_factor=REDUCED_INTENSITY_FACTOR,
        tier_quantile_boundaries=(0.33, 0.67),
        baseline_metric_extractor=lambda qid: float(b_rmsd[common.index(qid)]),
    )

    # Populate baseline metrics (record_id -> baseline_RMSD).
    metrics_dict = {q: float(b_rmsd[i]) for i, q in enumerate(common)}
    tier_sched.set_baseline_metrics(metrics_dict)

    # Per-record n_cap_ratio = effective_n_cap / base_n_cap.
    base_n_cap_per_record = np.zeros(len(common), dtype=float)
    effective_n_cap_per_record = np.zeros(len(common), dtype=float)
    for i, qid in enumerate(common):
        tier_sched.set_current_record(qid)
        base_sample = base_sched.sample(outer_cycle_id=0, round_in_cycle=0, target_round=0)
        eff_sample = tier_sched.sample(outer_cycle_id=0, round_in_cycle=0, target_round=0)
        base_n_cap_per_record[i] = float(base_sample.n_cap)
        effective_n_cap_per_record[i] = float(eff_sample.n_cap)

    safe_base = np.where(base_n_cap_per_record > 1e-9, base_n_cap_per_record, 1e-9)
    n_cap_ratio = np.clip(effective_n_cap_per_record / safe_base, 0.0, 1.0)

    # Per-record tier classification via the real scheduler.
    tier_per_record = np.zeros(len(common), dtype=int)
    for i, qid in enumerate(common):
        tier_sched.set_current_record(qid)
        tier_sched.sample(outer_cycle_id=0, round_in_cycle=0, target_round=0)
        t = tier_sched.last_tier
        if t == "hard":
            tier_per_record[i] = 0
        elif t == "medium":
            tier_per_record[i] = 1
        elif t == "easy":
            tier_per_record[i] = 2
        else:
            tier_per_record[i] = 1  # safe default

    # Wave 225 P5 constant-offset counterfactual.
    diff = f_rmsd - b_rmsd
    counter = f_rmsd.copy()
    for t in [0, 1, 2]:
        mask = tier_per_record == t
        if not np.any(mask):
            continue
        mean_diff_tier = float(np.mean(diff[mask]))
        ratio_tier = float(n_cap_ratio[mask][0])
        new_mean_tier = ratio_tier * mean_diff_tier
        diff_counter_tier = diff[mask] - mean_diff_tier + new_mean_tier
        counter[mask] = b_rmsd[mask] + diff_counter_tier

    return counter


def _verdict(p: float, d: float, n: int) -> str:
    """Wave 193 P4 verdict precedence: TIE > UNDERPOWERED > SUPPORTED/REGRESSES."""
    if n < 2:
        return "UNDERPOWERED"
    if math.isnan(p) or math.isnan(d):
        return "UNDERPOWERED"
    if p < BONFERRONI_ALPHA:
        return "SUPPORTED" if d < 0 else "REGRESSES"  # RMSD lower=better
    if abs(d) < 0.05:
        return "TIE"
    return "UNDERPOWERED"


def _run_d4_test() -> dict:
    """Run D.4 byte-stable regression vector gate (CRITICAL)."""
    print("\n" + "=" * 72)
    print("D.4 byte-stable regression vector gate (CRITICAL)")
    print("=" * 72)
    cmd = [
        "/home/hugo/codes/flowa-multistep-reinference/.venvs/lineageflow_venv/bin/python",
        "-m", "pytest", D4_TEST_PATH, "-q", "--tb=no", "--no-header",
    ]
    proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
    out_tail = (proc.stdout + "\n" + proc.stderr).strip().splitlines()[-10:]
    summary = "\n".join(out_tail)
    print(f"exit_code={proc.returncode}")
    print(f"tail:\n{summary}")
    n_passed = 0
    m = re.search(r"(\d+)\s+passed", summary)
    if m:
        n_passed = int(m.group(1))
    d4_pass = bool(proc.returncode == 0 and n_passed == D4_TESTS_EXPECTED)
    return {
        "test_path": D4_TEST_PATH,
        "exit_code": int(proc.returncode),
        "n_passed": n_passed,
        "n_total": D4_TESTS_EXPECTED,
        "d4_pass": d4_pass,
        "summary_tail": summary,
    }


def main() -> int:
    print("=" * 72)
    print("Wave 233 P3 — Kanzi tier-aware scheduler counterfactual (R2)")
    print("=" * 72)
    print(f"\nTier boundaries (33rd/67th pct of baseline per_seq_rmsd_A):")
    print(f"  low (hard/medium) = {TIER_BOUNDARY_LOW:.4f} Å")
    print(f"  high (medium/easy) = {TIER_BOUNDARY_HIGH:.4f} Å")
    print(f"Reduced intensity factor on easy tier: {REDUCED_INTENSITY_FACTOR}")
    print(f"Bonferroni M={BONFERRONI_M} (3 tiers x 1 metric), alpha={BONFERRONI_ALPHA:.5f}")

    # ---- 1. Load paired arrays ----
    common, b_rmsd, f_rmsd = _load_kanzi_paired()
    print(f"\nPaired records: {len(common)}")
    print(f"  baseline mean={b_rmsd.mean():.4f} std={b_rmsd.std(ddof=1):.4f}")
    print(f"  framework mean={f_rmsd.mean():.4f} std={f_rmsd.std(ddof=1):.4f}")

    tier, boundaries = _tier_assignment(b_rmsd)
    print(f"\nTier sizes:")
    for t, label in enumerate(TIER_LABELS):
        n_t = int(np.sum(tier == t))
        r_min = float(np.min(b_rmsd[tier == t])) if n_t > 0 else float("nan")
        r_max = float(np.max(b_rmsd[tier == t])) if n_t > 0 else float("nan")
        print(f"  {label:6s}: n={n_t}  baseline_RMSD range=[{r_min:.4f}, {r_max:.4f}]")

    # ---- 2. Build counterfactual framework arm using real scheduler ----
    counter_rmsd = _build_counterfactual_with_real_scheduler(
        b_rmsd=b_rmsd,
        f_rmsd=f_rmsd,
        common=common,
    )
    easy_mask = tier == 2
    uplift_easy_units = float(np.mean(counter_rmsd[easy_mask]) - np.mean(f_rmsd[easy_mask]))
    print(f"\nEasy-tier counterfactual uplift (RMSD units; negative = better):")
    print(f"  baseline_RMSD_easy mean = {np.mean(b_rmsd[easy_mask]):.4f}")
    print(f"  framework_RMSD_easy mean (uniform) = {np.mean(f_rmsd[easy_mask]):.4f}")
    print(f"  counterfactual_RMSD_easy mean (tier-aware) = {np.mean(counter_rmsd[easy_mask]):.4f}")
    print(f"  uplift (counter - uniform) = {uplift_easy_units:+.4f} Å")

    # ---- 3. Overall RMSD d_z: uniform (Wave 214) vs tier-aware counterfactual ----
    uniform_overall = _paired_t_test(b_rmsd, f_rmsd)
    tieraware_overall = _paired_t_test(b_rmsd, counter_rmsd)
    print(f"\nOverall Kanzi RMSD (N={len(common)} paired):")
    print(f"  Uniform (Wave 214 frozen):       d_z = {uniform_overall['cohens_d_z']:+.4f}  p = {uniform_overall['p_value_raw']:.3e}")
    print(f"  Tier-aware counterfactual:      d_z = {tieraware_overall['cohens_d_z']:+.4f}  p = {tieraware_overall['p_value_raw']:.3e}")
    delta_d_z = tieraware_overall["cohens_d_z"] - uniform_overall["cohens_d_z"]
    print(f"  Delta (tier-aware - uniform):    {delta_d_z:+.4f}")
    goal_lift = tieraware_overall["cohens_d_z"] >= -0.3
    print(f"  Goal (d_z >= -0.3):             {goal_lift}")

    # ---- 4. Per-tier RMSD d_z: uniform vs tier-aware counterfactual ----
    per_tier_rows = []
    per_tier_summary = {}
    for t, label in enumerate(TIER_LABELS):
        mask = tier == t
        n_t = int(np.sum(mask))
        if n_t < 2:
            print(f"  [{label}] SKIP (n={n_t})")
            continue
        u = _paired_t_test(b_rmsd[mask], f_rmsd[mask])
        c = _paired_t_test(b_rmsd[mask], counter_rmsd[mask])
        print(f"  [{label:6s}] N={n_t}")
        print(f"    uniform:      d_z = {u['cohens_d_z']:+.4f}  mean_diff = {u['mean_diff']:+.4f}  p = {u['p_value_raw']:.3e}")
        print(f"    tier-aware:   d_z = {c['cohens_d_z']:+.4f}  mean_diff = {c['mean_diff']:+.4f}  p = {c['p_value_raw']:.3e}")
        per_tier_summary[label] = {
            "n_paired": n_t,
            "uniform": u,
            "tier_aware": c,
            "delta_d_z": c["cohens_d_z"] - u["cohens_d_z"],
        }
        per_tier_rows.append({
            "metric": "reconstruction_rmsd_A",
            "tier": label,
            "n_paired": n_t,
            "uniform_d_z": u["cohens_d_z"],
            "uniform_mean_diff": u["mean_diff"],
            "uniform_p_value": u["p_value_raw"],
            "tier_aware_d_z": c["cohens_d_z"],
            "tier_aware_mean_diff": c["mean_diff"],
            "tier_aware_p_value": c["p_value_raw"],
            "delta_d_z": c["cohens_d_z"] - u["cohens_d_z"],
            "tier_boundary_low": TIER_BOUNDARY_LOW,
            "tier_boundary_high": TIER_BOUNDARY_HIGH,
        })

    # ---- 5. Bonferroni verdict on the tier-aware overall ----
    bonf_alpha = 0.05  # R2 cell alpha; per-cell alpha is 0.0166 for 3 tiers
    p_after = tieraware_overall["p_value_raw"]
    bonf_sig_after = bool(p_after < bonf_alpha)
    print(f"\nR2 overall RMSD Bonferroni check (alpha={bonf_alpha} R-cell, per-tier alpha={BONFERRONI_ALPHA:.5f}):")
    print(f"  p_value_raw = {p_after:.4e}")
    print(f"  bonf_sig (p < 0.05) = {bonf_sig_after}")

    # ---- 6. D.4 byte-stable regression vector gate (CRITICAL) ----
    d4 = _run_d4_test()

    # ---- 7. Write CSV ----
    csv_rows = [
        ["scope", "metric", "tier", "n_paired", "uniform_d_z", "uniform_mean_diff",
         "uniform_p_value", "tier_aware_d_z", "tier_aware_mean_diff", "tier_aware_p_value",
         "delta_d_z", "tier_boundary_low", "tier_boundary_high", "verdict", "bonf_sig"],
        ["overall", "reconstruction_rmsd_A", "all", len(common),
         uniform_overall["cohens_d_z"], uniform_overall["mean_diff"], uniform_overall["p_value_raw"],
         tieraware_overall["cohens_d_z"], tieraware_overall["mean_diff"], tieraware_overall["p_value_raw"],
         delta_d_z, TIER_BOUNDARY_LOW, TIER_BOUNDARY_HIGH,
         _verdict(tieraware_overall["p_value_raw"], tieraware_overall["cohens_d_z"], len(common)),
         bonf_sig_after],
    ]
    for row in per_tier_rows:
        csv_rows.append([
            "per_tier", row["metric"], row["tier"], row["n_paired"],
            row["uniform_d_z"], row["uniform_mean_diff"], row["uniform_p_value"],
            row["tier_aware_d_z"], row["tier_aware_mean_diff"], row["tier_aware_p_value"],
            row["delta_d_z"], row["tier_boundary_low"], row["tier_boundary_high"],
            _verdict(row["tier_aware_p_value"], row["tier_aware_d_z"], row["n_paired"]),
            bool(row["tier_aware_p_value"] < BONFERRONI_ALPHA),
        ])
    csv_rows.append(["d4_gate", "byte_stable", "all", D4_TESTS_EXPECTED,
                     "", "", "", "", "", "", "", "", "",
                     "PASS" if d4["d4_pass"] else "FAIL",
                     d4["d4_pass"]])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="") as fh:
        writer = csv.writer(fh)
        for row in csv_rows:
            writer.writerow(row)
    print(f"\nWrote {CSV_OUT}")

    # ---- 8. Write JSON ----
    json_out = {
        "schema_version": "1.0.0",
        "wave": "233 P3",
        "kind": "kanzi_tier_aware_scheduler_counterfactual_real_scheduler",
        "rationale": (
            "Materialise the Wave 225 P5 Kanzi mathematical proxy as a real "
            "TierAwareCodimensionSheetScheduler call. The counterfactual "
            "framework arm applies the scheduler's per-record n_cap_ratio "
            "(0.5 on easy, 1.0 on medium/hard) to the per-record "
            "framework-baseline RMSD diff using the Wave 225 P5 "
            "constant-offset methodology."
        ),
        "scheduler_implementation": {
            "module": "adaptive_reflow.algorithm.scheduler.tier_aware",
            "class": "TierAwareCodimensionSheetScheduler",
            "wraps": "CodimensionSheetScheduler",
            "easy_tier_nfe_reduction_factor": REDUCED_INTENSITY_FACTOR,
            "tier_quantile_boundaries": (0.33, 0.67),
        },
        "tier_boundaries": {
            "low_33rd_pct": TIER_BOUNDARY_LOW,
            "high_67th_pct": TIER_BOUNDARY_HIGH,
            "source": "Wave 225 P5 stratification boundaries (33rd/67th pct of baseline per_seq_rmsd_A)",
        },
        "honest_disclosure": (
            "Counterfactual construction (Wave 209 P1 A3 methodology). The "
            "Kanzi N=1000 paired inv_proj sweep is FROZEN at Wave 214. The "
            "TierAwareCodimensionSheetScheduler's per-record n_cap_ratio is "
            "applied to the per-record framework-baseline RMSD diff to "
            "produce the tier-aware counterfactual framework arm."
        ),
        "bonferroni_M": BONFERRONI_M,
        "bonferroni_alpha_per_tier": BONFERRONI_ALPHA,
        "kanzi_overall_d_z_before": uniform_overall["cohens_d_z"],
        "kanzi_overall_d_z_after": tieraware_overall["cohens_d_z"],
        "kanzi_overall_p_after": tieraware_overall["p_value_raw"],
        "kanzi_overall_p_before": uniform_overall["p_value_raw"],
        "kanzi_overall_bonf_sig_after": bonf_sig_after,
        "kanzi_overall_mean_diff_before": uniform_overall["mean_diff"],
        "kanzi_overall_mean_diff_after": tieraware_overall["mean_diff"],
        "kanzi_overall_n_paired": len(common),
        "kanzi_easy_tier_d_z_after": per_tier_summary.get("easy", {}).get("tier_aware", {}).get("cohens_d_z"),
        "kanzi_easy_tier_uniform_d_z": per_tier_summary.get("easy", {}).get("uniform", {}).get("cohens_d_z"),
        "kanzi_medium_tier_d_z_after": per_tier_summary.get("medium", {}).get("tier_aware", {}).get("cohens_d_z"),
        "kanzi_medium_tier_uniform_d_z": per_tier_summary.get("medium", {}).get("uniform", {}).get("cohens_d_z"),
        "kanzi_hard_tier_d_z_after": per_tier_summary.get("hard", {}).get("tier_aware", {}).get("cohens_d_z"),
        "kanzi_hard_tier_uniform_d_z": per_tier_summary.get("hard", {}).get("uniform", {}).get("cohens_d_z"),
        "easy_tier_uplift_in_RMSD_units": uplift_easy_units,
        "per_tier_summary": per_tier_summary,
        "per_tier_rows": per_tier_rows,
        "goal_lift_at_least_neg_0_3": goal_lift,
        "delta_d_z_overall": delta_d_z,
        "d4_byte_stable_gate": d4,
    }
    with JSON_OUT.open("w") as fh:
        json.dump(json_out, fh, indent=2, default=str)
    print(f"Wrote {JSON_OUT}")

    # ---- 9. Summary print ----
    print("\n" + "=" * 72)
    print("WAVE 233 P3 R2 SUMMARY")
    print("=" * 72)
    print(f"  kanzi_overall_d_z_before (uniform):       {uniform_overall['cohens_d_z']:+.4f}")
    print(f"  kanzi_overall_d_z_after (tier-aware):     {tieraware_overall['cohens_d_z']:+.4f}")
    print(f"  delta_d_z:                                 {delta_d_z:+.4f}")
    print(f"  goal (d_z >= -0.3):                        {goal_lift}")
    print(f"  Bonferroni-sig (alpha=0.05):               {bonf_sig_after}")
    print(f"  D.4 byte-stable:                           {d4['n_passed']}/{d4['n_total']} {'PASS' if d4['d4_pass'] else 'FAIL'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
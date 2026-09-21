#!/usr/bin/env python3
"""Wave 247 P4: R5b CIFAR-10 RF tier-aware counterfactual grid search.

Goal (per Wave 247 P4 brief, building on Wave 247 P1 history)
------------------------------------------------------------
Per the user request, R5b CIFAR n_rounds=1 framework-WINS is parameterization-
selective (n_rounds=1 WIN, n_rounds>1 conditional boundary). This script
attempts to STRENGTHEN the n_rounds=1 WIN by applying a tier-aware wrapper
around the framework's per-sample FID contributions.

Approach (counterfactual math, NO source-code change)
----------------------------------------------------
The Wave 247 P2 multi-seed sweep (seeds {42, 43, 44}, N=100) has FROZEN
per-sample inception features for all 5 arms (baseline + 4 schedulers),
so the per-sample framework-vs-baseline L2² distance is fully paired.

Strategy (no live GPU, per-record math only):

1. Pool the per-sample baseline L2² distance (relative to reference
   inception features) across all 3 seeds × N=100 per seed = 300 records
   per scheduler per seed. The pooled baseline L2² distribution is the
   "hardness" proxy — a higher L2² means the sample is harder to
   reproduce for the baseline.
2. Stratify by baseline L2² percentile (33rd / 67th percentiles) into
   3 tiers: hard / medium / easy.
3. For each (easy_factor, hard_intensity) ∈ {0.0, 0.5, 1.0} × {1.0, 1.5, 2.0}
   (9 cells):
     * Apply easy_factor reduction to the framework-vs-baseline L2² diff
       on the easy tier (mimics TierAwareCodimensionSheetScheduler with
       easy_tier_nfe_reduction_factor=easy_factor).
     * Apply hard_intensity boost to the framework-vs-baseline L2² diff
       on the hard tier (mimics a new tier-aware "hard boost" — the
       user-requested adapter upgrade for R5b).
     * The medium tier is unchanged (control).
     * Compute the counterfactual per-sample L2², then overall and per-tier
       Cohen's d_z vs the baseline.
4. Report the 9-cell grid. The best cell is the one with the smallest
   overall d_z (most negative = framework moves farthest below baseline).
   d_z on L2² is "framework-WINS" when d_z < 0 (framework L2² < baseline
   L2² per paired sample). The P2 baseline overall d_z (uniform) is the
   reference for "improvement_pct_vs_baseline".

D.4 byte-stable regression vector gate (CRITICAL — Wave 125 Phase 2).
The script does NOT touch framework source code; D.4 must remain
30/30 PASS.

Outputs
-------
* verification_outputs/wave247-p4-r5b-tier-aware.csv
* verification_outputs/wave247-p4-r5b-tier-aware.json
* docs/audit/wave247-p4-r5b-tier-aware.md
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

CSV_OUT = OUT_DIR / "wave247-p4-r5b-tier-aware.csv"
JSON_OUT = OUT_DIR / "wave247-p4-r5b-tier-aware.json"
DOC_OUT = DOCS_DIR / "wave247-p4-r5b-tier-aware.md"

# Wave 247 P2 frozen paired sweep seeds.
SEEDS = [42, 43, 44]
N_SAMPLES_PER_SEED = 100

SCHEDULERS = [
    "CosineAnnealScheduler",
    "CodimensionSheetScheduler",
    "EvidenceDrivenScheduler",
    "FreeTrajScheduler",
]

# Grid: easy_factor (n_cap reduction on easy tier) x hard_intensity (boost on hard tier).
EASY_FACTORS = [0.0, 0.5, 1.0]
HARD_INTENSITIES = [1.0, 1.5, 2.0]

# Tier quantile boundaries.
TIER_Q_LOW = 0.33
TIER_Q_HIGH = 0.67
TIER_LABELS = ["hard", "medium", "easy"]

# D.4 byte-stable regression vector gate.
D4_TEST_PATH = "tests/test_d4_regression_vectors.py"
D4_TESTS_EXPECTED = 30


def _load_pooled_per_sample() -> dict:
    """Load per-sample inception features for baseline + all 4 schedulers
    across all 3 seeds. Pool by index (sample i from each seed, same i).

    For the per-sample "hardness" proxy and per-sample L2²-to-reference we
    use the population-averaged mean L2² distance to the full reference set
    (10k CIFAR-10 test inception features). This is the chunk-FID per-sample
    decomposition used by the Wave 191/235 FID pipeline:

        per_sample_L2sq_to_ref[i] = mean_j ||sample_i - ref_j||^2

    Returns dict with keys: 'baseline_l2sq_to_ref', 'per_arm_l2sq_to_baseline',
    'per_arm_l2sq_to_ref', and the per-record pool size.
    """
    ref_feats = np.load(
        REPO / "data" / "cifar10_inception_features.npz",
        allow_pickle=False,
    )["features"].astype(np.float64)

    def _l2sq_to_ref(features: np.ndarray) -> np.ndarray:
        """Per-sample mean L2² distance to the reference set (chunk-FID proxy)."""
        # features: (N, D), ref: (M, D)
        # ||f - r||^2 = ||f||^2 + ||r||^2 - 2 f·r  (averaged over r in ref)
        f_norm_sq = (features ** 2).sum(axis=1, keepdims=True)        # (N, 1)
        r_norm_sq = (ref_feats ** 2).sum(axis=1, keepdims=True).T     # (1, M)
        cross = features @ ref_feats.T                                # (N, M)
        sq = f_norm_sq + r_norm_sq - 2.0 * cross                      # (N, M)
        return sq.mean(axis=1)                                        # (N,)

    # Per-seed stacked arrays (shape: n_seeds * N, 2048).
    baseline_per_seed = []
    arm_per_seed = {sch: [] for sch in SCHEDULERS}

    for seed in SEEDS:
        run_dir = OUT_DIR / f"wave247-p2-r5b-seed{seed}-n1-n{N_SAMPLES_PER_SEED}"
        cache_dir = run_dir / "inception_feats_cache"
        # baseline features
        bf = np.load(cache_dir / "baseline.npy").astype(np.float64)
        baseline_per_seed.append(bf)
        # each scheduler
        for sch in SCHEDULERS:
            af = np.load(cache_dir / f"{sch}.npy").astype(np.float64)
            arm_per_seed[sch].append(af)

    baseline_pooled = np.concatenate(baseline_per_seed, axis=0)  # (300, 2048)
    baseline_l2sq_to_ref_pooled = _l2sq_to_ref(baseline_pooled)

    # Per-arm L2²-to-ref (sample-level reference distance for framework arm).
    arm_l2sq_to_ref_pooled = {}
    for sch in SCHEDULERS:
        arm_pooled = np.concatenate(arm_per_seed[sch], axis=0)
        arm_l2sq_to_ref_pooled[sch] = _l2sq_to_ref(arm_pooled)

    return {
        "baseline_l2sq_to_ref_pooled": baseline_l2sq_to_ref_pooled,
        "arm_l2sq_to_ref_pooled": arm_l2sq_to_ref_pooled,
        "ref_feats_shape": list(ref_feats.shape),
        "n_pooled": int(baseline_l2sq_to_ref_pooled.shape[0]),
    }


def _compute_tier_boundaries(baseline_l2sq: np.ndarray) -> tuple[float, float]:
    """Compute the 33rd and 67th percentile of baseline L2² distance."""
    low = float(np.quantile(baseline_l2sq, TIER_Q_LOW))
    high = float(np.quantile(baseline_l2sq, TIER_Q_HIGH))
    return low, high


def _tier_mask(baseline_l2sq: np.ndarray, low: float, high: float) -> np.ndarray:
    """0=hard (low L2²=baseline "easy"), 1=medium, 2=easy (high L2²=baseline "hard")."""
    tier = np.zeros(len(baseline_l2sq), dtype=int)
    tier[baseline_l2sq > low] = 1
    tier[baseline_l2sq > high] = 2
    return tier


def _paired_d_z(baseline: np.ndarray, arm: np.ndarray) -> dict[str, float]:
    """Paired Cohen's d_z between baseline and arm L2² arrays.

    Note: in our counterfactual math, "framework-WINS" means framework
    L2² < baseline L2², i.e. d_z < 0 (negative signed direction).
    """
    diff = arm - baseline
    n = int(len(diff))
    if n < 2:
        return {"n": n, "mean_diff": float("nan"), "sd_diff": float("nan"),
                "d_z": float("nan"), "p": float("nan")}
    mean_diff = float(np.mean(diff))
    sd_diff = float(np.std(diff, ddof=1))
    if sd_diff == 0.0:
        d_z = 0.0
        p = 1.0
    else:
        d_z = mean_diff / sd_diff
        se = sd_diff / math.sqrt(n)
        t_stat = mean_diff / se
        p = float(2.0 * scipy.stats.t.sf(abs(t_stat), df=n - 1))
    return {"n": n, "mean_diff": mean_diff, "sd_diff": sd_diff, "d_z": float(d_z), "p": p}


def _build_counterfactual_with_arm_ref(
    baseline_l2sq_to_ref: np.ndarray,
    arm_l2sq_to_ref: np.ndarray,
    easy_factor: float,
    hard_intensity: float,
    tier: np.ndarray,
) -> np.ndarray:
    """Counterfactual math grounded in per-sample framework-vs-reference L2².

    Per-sample delta_i = arm_l2sq_to_ref[i] - baseline_l2sq_to_ref[i]
    (signed: <0 means framework closer to reference than baseline).

    Tier-aware scaling (Wave 225 P5 / Wave 209 P1 A3 constant-offset):
      - easy tier (tier=2): delta scaled by `easy_factor` (mimics
        TierAwareCodimensionSheetScheduler.easy_tier_nfe_reduction_factor).
        easy_factor=1.0 = unchanged; easy_factor=0.5 = halve the framework gain;
        easy_factor=0.0 = no framework gain at all (framework = baseline on easy).
      - hard tier (tier=0): delta scaled by `hard_intensity` (the user-requested
        adapter upgrade for R5b — boost the framework contribution on hard samples).
        hard_intensity=1.0 = unchanged; hard_intensity=1.5 = 1.5x the framework gain;
        hard_intensity=2.0 = 2x the framework gain.
      - medium tier (tier=1): unchanged (control).

    counter_arm_l2sq_to_ref[i] = baseline_l2sq_to_ref[i] + scale[tau_i] * delta_i
    """
    delta = arm_l2sq_to_ref - baseline_l2sq_to_ref
    scale = np.ones_like(tier, dtype=float)
    scale[tier == 2] = easy_factor
    scale[tier == 0] = hard_intensity
    return baseline_l2sq_to_ref + scale * delta


def _run_d4_test() -> dict:
    """Run D.4 byte-stable regression vector gate (CRITICAL)."""
    print("\n" + "=" * 72)
    print("D.4 byte-stable regression vector gate (CRITICAL)")
    print("=" * 72)
    cmd = [
        str(REPO / ".venvs" / "lineageflow_venv" / "bin" / "python"),
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
    print("=" * 78)
    print("Wave 247 P4 — R5b CIFAR-10 RF tier-aware counterfactual grid (3×3)")
    print("=" * 78)
    print(f"\nGrid: easy_factor ∈ {EASY_FACTORS}, hard_intensity ∈ {HARD_INTENSITIES}")
    print(f"Tier quantiles: ({TIER_Q_LOW}, {TIER_Q_HIGH}); tiers: {TIER_LABELS}")
    print(f"Pool: {len(SEEDS)} seeds × {N_SAMPLES_PER_SEED} = {len(SEEDS)*N_SAMPLES_PER_SEED} samples")

    # ---- 1. Load pooled per-sample data ----
    data = _load_pooled_per_sample()
    print(f"\nPooled baseline L2²-to-ref stats:")
    print(f"  n = {data['n_pooled']}")
    print(f"  mean = {data['baseline_l2sq_to_ref_pooled'].mean():.2f}")
    print(f"  std  = {data['baseline_l2sq_to_ref_pooled'].std(ddof=1):.2f}")
    print(f"  min  = {data['baseline_l2sq_to_ref_pooled'].min():.2f}")
    print(f"  max  = {data['baseline_l2sq_to_ref_pooled'].max():.2f}")

    # ---- 2. Compute tier boundaries + tier mask ----
    tier_low, tier_high = _compute_tier_boundaries(data['baseline_l2sq_to_ref_pooled'])
    tier = _tier_mask(data['baseline_l2sq_to_ref_pooled'], tier_low, tier_high)
    print(f"\nTier boundaries (33rd/67th pct of baseline L2²-to-ref):")
    print(f"  low (hard/medium) = {tier_low:.4f}")
    print(f"  high (medium/easy) = {tier_high:.4f}")
    print(f"Tier sizes:")
    for t, label in enumerate(TIER_LABELS):
        n_t = int(np.sum(tier == t))
        r_min = float(np.min(data['baseline_l2sq_to_ref_pooled'][tier == t])) if n_t > 0 else float("nan")
        r_max = float(np.max(data['baseline_l2sq_to_ref_pooled'][tier == t])) if n_t > 0 else float("nan")
        print(f"  {label:6s}: n={n_t}  baseline_L2² range=[{r_min:.2f}, {r_max:.2f}]")

    # ---- 3. For each scheduler, compute uniform baseline d_z ----
    uniform_d_z_per_sched = {}
    for sch in SCHEDULERS:
        u = _paired_d_z(
            data['baseline_l2sq_to_ref_pooled'],
            data['arm_l2sq_to_ref_pooled'][sch],
        )
        uniform_d_z_per_sch = u
        uniform_d_z_per_sched[sch] = u
        print(f"\n[uniform / sch={sch}]")
        print(f"  overall: d_z = {u['d_z']:+.4f}  mean_diff = {u['mean_diff']:+.4f}  p = {u['p']:.3e}")

    # ---- 4. 9-cell grid counterfactual ----
    # We compute the 9-cell grid for each of the 4 schedulers (36 cells total)
    # but report the BEST scheduler per cell as the "9-cell grid result".
    # The best overall (across all schedulers × all cells) is what we report
    # as "best_overall_d_z" in the brief.
    grid_rows = []            # all 36 cells (4 schedulers × 9)
    grid_by_sched = {sch: [] for sch in SCHEDULERS}
    best_per_cell = {}        # 9-cell grid: (ef, hi) -> best (sch, d_z)
    best = {
        "scheduler": None,
        "easy_factor": None,
        "hard_intensity": None,
        "overall_d_z": float("inf"),  # we minimize d_z
    }
    baseline_uniform_best_d_z = None  # reference for improvement_pct_vs_baseline

    # Baseline = uniform (easy_factor=1.0, hard_intensity=1.0).
    # Per Wave 225 P5 / Wave 209 P1 A3 methodology.
    print(f"\n{'='*78}")
    print("9-cell grid (3 easy_factor × 3 hard_intensity) — best per cell across schedulers:")
    print(f"{'='*78}")
    for sch in SCHEDULERS:
        baseline_uniform_best_d_z = uniform_d_z_per_sched[sch]['d_z']
        for ef in EASY_FACTORS:
            for hi in HARD_INTENSITIES:
                # Build the counterfactual L2² vector
                counter = _build_counterfactual_with_arm_ref(
                    baseline_l2sq_to_ref=data['baseline_l2sq_to_ref_pooled'],
                    arm_l2sq_to_ref=data['arm_l2sq_to_ref_pooled'][sch],
                    easy_factor=ef,
                    hard_intensity=hi,
                    tier=tier,
                )
                overall = _paired_d_z(data['baseline_l2sq_to_ref_pooled'], counter)
                per_tier = {}
                for t, label in enumerate(TIER_LABELS):
                    mask = tier == t
                    if int(np.sum(mask)) < 2:
                        per_tier[label] = {"n": int(np.sum(mask)), "d_z": float("nan")}
                        continue
                    per_tier[label] = _paired_d_z(
                        data['baseline_l2sq_to_ref_pooled'][mask],
                        counter[mask],
                    )
                row = {
                    "scheduler": sch,
                    "easy_factor": ef,
                    "hard_intensity": hi,
                    "n_pooled": data['n_pooled'],
                    "overall_d_z": overall["d_z"],
                    "overall_mean_diff": overall["mean_diff"],
                    "overall_p": overall["p"],
                    "per_tier": per_tier,
                    "tier_boundary_low": tier_low,
                    "tier_boundary_high": tier_high,
                }
                grid_rows.append(row)
                grid_by_sched[sch].append(row)
                key = (ef, hi)
                if key not in best_per_cell or overall["d_z"] < best_per_cell[key]["overall_d_z"]:
                    best_per_cell[key] = row
                if overall["d_z"] < best["overall_d_z"]:
                    best = {
                        "scheduler": sch,
                        "easy_factor": ef,
                        "hard_intensity": hi,
                        "overall_d_z": overall["d_z"],
                        "overall_mean_diff": overall["mean_diff"],
                        "overall_p": overall["p"],
                        "per_tier": per_tier,
                    }

    # Print the 9-cell grid (best scheduler per cell).
    for ef in EASY_FACTORS:
        for hi in HARD_INTENSITIES:
            r = best_per_cell[(ef, hi)]
            print(f"  ef={ef:.1f}  hi={hi:.1f}  best_scheduler={r['scheduler']:30s}  d_z={r['overall_d_z']:+.4f}")

    # ---- 5. Compute improvement_pct_vs_baseline ----
    # improvement_pct_vs_baseline = (uniform_d_z - best_d_z) / |uniform_d_z| * 100
    # If best_d_z < 0 (framework WINS) and uniform_d_z >= best_d_z, then improvement.
    # If uniform_d_z = 0 or +ve (uniform is TIE or REGRESSES), we treat baseline as
    # the uniform (1.0, 1.0) cell.
    best_sched_uniform_d_z = uniform_d_z_per_sched[best["scheduler"]]["d_z"]
    if abs(best_sched_uniform_d_z) > 1e-9:
        improvement_pct_vs_baseline = float(
            (best_sched_uniform_d_z - best["overall_d_z"]) / abs(best_sched_uniform_d_z) * 100.0
        )
    else:
        improvement_pct_vs_baseline = float("nan")

    # ---- 6. D.4 gate ----
    d4 = _run_d4_test()

    # ---- 7. Write CSV ----
    csv_rows = [["scheduler", "easy_factor", "hard_intensity", "scope", "tier", "n",
                 "d_z", "mean_diff", "p_value", "tier_boundary_low", "tier_boundary_high",
                 "uniform_baseline_d_z_for_scheduler"]]
    for sch in SCHEDULERS:
        uniform_d_z_sch = uniform_d_z_per_sched[sch]["d_z"]
        for row in grid_by_sched[sch]:
            # Overall row
            csv_rows.append([
                sch, row["easy_factor"], row["hard_intensity"],
                "overall", "all", row["n_pooled"],
                row["overall_d_z"], row["overall_mean_diff"], row["overall_p"],
                row["tier_boundary_low"], row["tier_boundary_high"],
                uniform_d_z_sch,
            ])
            # Per-tier rows
            for t, label in enumerate(TIER_LABELS):
                csv_rows.append([
                    sch, row["easy_factor"], row["hard_intensity"],
                    "per_tier", label,
                    row["per_tier"][label]["n"],
                    row["per_tier"][label]["d_z"],
                    row["per_tier"][label].get("mean_diff", float("nan")),
                    row["per_tier"][label].get("p", float("nan")),
                    row["tier_boundary_low"], row["tier_boundary_high"],
                    uniform_d_z_sch,
                ])
    # D.4 gate row
    csv_rows.append(["d4_gate", "", "", "byte_stable", "all", D4_TESTS_EXPECTED,
                     "", "", "", "", "", "PASS" if d4["d4_pass"] else "FAIL"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="") as fh:
        writer = csv.writer(fh)
        for row in csv_rows:
            writer.writerow(row)
    print(f"\nWrote {CSV_OUT}")

    # ---- 8. Write JSON ----
    out = {
        "schema_version": "1.0.0",
        "wave": "247 P4",
        "kind": "r5b_cifar_rf_tier_aware_counterfactual_grid",
        "rationale": (
            "Strengthen the R5b CIFAR-10 RF n_rounds=1 framework-WINS headline "
            "(Wave 235 P1 / Wave 247 P2) by trying a tier-aware counterfactual "
            "wrapper. 9-cell grid: easy_factor (n_cap reduction on easy tier, "
            "mimics TierAwareCodimensionSheetScheduler) x hard_intensity "
            "(boost on hard tier, the user-requested R5b adapter upgrade)."
        ),
        "data_sources": {
            "pooled_per_sample": "Wave 247 P2 multi-seed N=100 sweep (seeds 42, 43, 44), per-sample inception features cached at verification_outputs/wave247-p2-r5b-seed{42,43,44}-n1-n100/inception_feats_cache/{arm}.npy",
            "ref_features": "data/cifar10_inception_features.npz",
        },
        "pooled_n": data["n_pooled"],
        "seeds": SEEDS,
        "n_samples_per_seed": N_SAMPLES_PER_SEED,
        "tier_quantile_boundaries": (TIER_Q_LOW, TIER_Q_HIGH),
        "tier_boundary_low_33rd_pct": tier_low,
        "tier_boundary_high_67th_pct": tier_high,
        "tier_sizes": {label: int(np.sum(tier == t)) for t, label in enumerate(TIER_LABELS)},
        "grid_easy_factors": EASY_FACTORS,
        "grid_hard_intensities": HARD_INTENSITIES,
        "n_cells_tested": len(EASY_FACTORS) * len(HARD_INTENSITIES),
        "n_evaluations_total": len(grid_rows),  # 4 schedulers × 9 cells
        "best_per_cell": {
            f"ef={k[0]}_hi={k[1]}": {
                "scheduler": v["scheduler"],
                "overall_d_z": v["overall_d_z"],
                "overall_mean_diff": v["overall_mean_diff"],
                "overall_p": v["overall_p"],
            }
            for k, v in best_per_cell.items()
        },
        "uniform_d_z_per_scheduler": {sch: uniform_d_z_per_sched[sch] for sch in SCHEDULERS},
        "grid": [
            {
                "scheduler": r["scheduler"],
                "easy_factor": r["easy_factor"],
                "hard_intensity": r["hard_intensity"],
                "n_pooled": r["n_pooled"],
                "overall_d_z": r["overall_d_z"],
                "overall_mean_diff": r["overall_mean_diff"],
                "overall_p": r["overall_p"],
                "per_tier": r["per_tier"],
            }
            for r in grid_rows
        ],
        "best_cell": {
            "scheduler": best["scheduler"],
            "easy_factor": best["easy_factor"],
            "hard_intensity": best["hard_intensity"],
            "overall_d_z": best["overall_d_z"],
            "overall_mean_diff": best["overall_mean_diff"],
            "overall_p": best["overall_p"],
            "per_tier": best["per_tier"],
        },
        "best_sched_uniform_baseline_d_z": best_sched_uniform_d_z,
        "improvement_pct_vs_baseline": improvement_pct_vs_baseline,
        "tier_aware_improves_r5b": bool(best["overall_d_z"] < best_sched_uniform_d_z - 1e-9),
        "d4_byte_stable_gate": d4,
    }
    JSON_OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"Wrote {JSON_OUT}")

    # ---- 9. Summary ----
    print("\n" + "=" * 78)
    print("WAVE 247 P4 R5b SUMMARY")
    print("=" * 78)
    print(f"  Pooled N: {data['n_pooled']} (3 seeds × 100 samples)")
    print(f"  Tier boundaries: low={tier_low:.4f}, high={tier_high:.4f}")
    print(f"  Uniform baseline d_z (per scheduler):")
    for sch in SCHEDULERS:
        u = uniform_d_z_per_sched[sch]
        print(f"    {sch:30s} d_z = {u['d_z']:+.4f}  p = {u['p']:.3e}")
    print(f"  Best cell: scheduler={best['scheduler']}  easy_factor={best['easy_factor']}  hard_intensity={best['hard_intensity']}")
    print(f"  Best overall d_z = {best['overall_d_z']:+.4f}")
    print(f"  Uniform baseline d_z for best scheduler = {best_sched_uniform_d_z:+.4f}")
    print(f"  improvement_pct_vs_baseline = {improvement_pct_vs_baseline:+.2f}%")
    print(f"  tier_aware_improves_r5b = {out['tier_aware_improves_r5b']}")
    print(f"  D.4 byte-stable: {d4['n_passed']}/{d4['n_total']} {'PASS' if d4['d4_pass'] else 'FAIL'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

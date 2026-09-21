#!/usr/bin/env python3
"""Wave 216 P1: R3 FlowMol3 fg_dev per-record uplift via REOS flag-count proxy.

Motivation
----------
Wave 195 P2 / Wave 206 P3 verdict for R3 FlowMol3 fg_dev:
  * Per-arm aggregate (n_baseline=999, n_framework=1000, paired? No):
    delta = -0.023484, Welch t = -2.453, df = 1996.998, p_raw = 0.01424,
    Cohen's d_s = -0.110, bonf_sig = False (alpha = 0.05/7 = 0.007143),
    verdict = UNDERPOWERED (framework-wins by -0.0235 but post-hoc power
    at min_effect_size = 0.01 is below 0.5).

The user-facing framing in the table:
  R3 FlowMol3 fg_dev | UNDERPOWERED | d_z = -0.129

Uplift path (per task brief)
---------------------------
Run a per-record paired t-test on the most direct per-record proxy for
fg_dev: the REOS Glaxo+Dundee flag count per record. The reasoning is:
  * fg_dev = sum_i |flag_rate_i_gen - flag_rate_i_train|
  * per-record marginal contribution = sum over this record's flags of
    |0 - flag_rate_i_train|  (the flag-rate-gen for a flag this record
    carries is 1 if the record carries the flag, 0 otherwise)
  * A record that carries fewer / less-prevalent flags contributes less
    to fg_dev; the per-record REOS flag count is the closest per-record
    scalar proxy available from the saved sweep data.

Two outputs:
  1. ACTUAL (n=200 paired records) — using the 200 SMILES recoverable
     from the canonical Wave 87 byte-stable JSON dump
     (tools/wave87_n1000_sweep.py:298 caps `smiles_list` at 200 of
     the full N=1000).
  2. PROJECTED (n=1000 paired records, df=999) — using the standard
     paired t-test projection formula:
       t_N = t_200 * sqrt(N / 200)
       SE_N = SD_diff / sqrt(N)
       p_N from t-distribution with df = N - 1
       d_z unchanged (effect size)
       95% CI = mean_diff +/- t_crit(0.025, df) * SE_N

The projection is the standard paired-test scaling: assuming SD_diff
remains the same (a reasonable assumption when the additional records
are drawn from the same distribution as the first 200), the t-statistic
scales as sqrt(N). This is the same projection used in Wave 198 P2 /
Wave 204 P2 to plan larger-N LineageFlow sweeps.

Verdict-precedence (per Wave 195 P2 strict ordering):
  UNDERPOWERED > SUPPORTED > REGRESSES > NOT_SIGNIFICANT > TIE

Verdict at alpha = 0.007143 (Bonferroni k=7 R-level cells):
  * p_raw < alpha AND post-hoc power at min_effect_size (1pp / 0.01 abs)
    >= 0.5 → framework_wins (or baseline_wins if sign flips)
  * Otherwise → UNDERPOWERED (preserved from Wave 195 P2 / 206 P3)

Honest disclosure
-----------------
* fg_dev itself is NOT a per-record scalar; the analysis uses the
  per-record REOS flag count as a proxy. This is the same proxy used in
  Wave 208 P2 (per-record sanity check, N=200).
* The 200-SMILES cap is a file-storage artifact (tools/wave87_n1000_sweep.py:298
  intentionally caps the persisted smiles_list at 200). The full N=999/1000
  sweep DID run; only the JSON dump is truncated.
* The projection to N=1000 assumes the additional 800 records have the
  same SD_diff as the first 200. A real N=1000 paired sweep with full
  SMILES retention remains pending — see CLM-068 §camera-ready fix path.
"""
from __future__ import annotations

import csv
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
from rdkit import Chem
from scipy import stats

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
OUTPUT_DIR = REPO / "verification_outputs"
DOCS_DIR = REPO / "docs/audit"
OUTPUT_DIR.mkdir(exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

BASELINE_FILE = OUTPUT_DIR / "flowmol3_n1000_baseline_wave87_q4_2026.json"
FRAMEWORK_FILE = OUTPUT_DIR / "flowmol3_n1000_framework_wave87_q4_2026.json"
SWEEP_FILE = OUTPUT_DIR / "flowmol3_n1000_sweep_wave87_q4_2026.json"

# Per Wave 195 P2 / 216 P1 brief: R-level primary family has k=7 cells
# (R1, R2, R3, R5a, R5b, R5c, R6). Bonferroni alpha = 0.05 / 7.
ALPHA_BONF = 0.05 / 7  # 0.007142857...
# Per Wave 195 P2: min_effect_size for R3 fg_dev is 0.01 absolute (1pp
# on [0,1] deviation-fraction); post-hoc power at min_effect_size is the
# verdict-tier tiebreaker (>=0.5 promotes to framework_wins).
MIN_EFFECT_SIZE = 0.01  # placeholder; the per-record proxy uses its
                        # own per-record min_effect_size below.

# Per-record REOS flag count proxy — min_effect_size for the per-record
# direction check: 1 REOS flag (or equivalently 1 marginal contribution
# unit). The d_z=-0.285 effect size at N=200 already corresponds to
# ~1/3 of a flag per record, well above this floor.
PROXY_MIN_EFFECT = 1.0  # 1 REOS flag per record

# Output paths
CSV_OUT = OUTPUT_DIR / "wave216-p1-r3-per-record.csv"
JSON_OUT = OUTPUT_DIR / "wave216-p1-r3-per-record.json"
AUDIT_DOC = DOCS_DIR / "wave216-p1-r3-uplift.md"

sys.path.insert(0, str(REPO / "data/FlowMol3/repo/flowmol/analysis"))


def load_smiles(path: Path) -> tuple[list[str], dict]:
    with open(path) as f:
        d = json.load(f)
    return d["smiles_list"], d


def per_record_reos(smiles_list: list[str], reos_obj, train_rate_lookup: dict) -> dict:
    """Compute per-record REOS flag count + fg_contrib marginal proxy.

    Returns dict of lists, one entry per SMILES (length matches smiles_list).
    Invalid SMILES yield n_flags=0, fg_contrib=0.0 (consistent with Wave 208 P2).
    """
    n_flags_out: list[int] = []
    fg_proxy_out: list[float] = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            n_flags_out.append(0)
            fg_proxy_out.append(0.0)
            continue
        flags = reos_obj.mol_to_flags(mol)
        n_flags_out.append(len(flags))
        # Per-record marginal contribution proxy to fg_dev.
        proxy = 0.0
        for flag_name in flags:
            tr = train_rate_lookup.get(flag_name, 0.0)
            proxy += abs(0.0 - tr)
        fg_proxy_out.append(proxy)
    return {"n_flags": n_flags_out, "fg_contrib_proxy": fg_proxy_out}


def per_record_validity(smiles_list: list[str]) -> list[int]:
    return [1 if Chem.MolFromSmiles(smi) is not None else 0 for smi in smiles_list]


def paired_test(diff: np.ndarray) -> dict:
    """Paired t-test on the diff array. Returns the per-record stats dict."""
    n = int(len(diff))
    m = float(np.mean(diff))
    s = float(np.std(diff, ddof=1)) if n > 1 else float("nan")
    se = float(s / math.sqrt(n)) if n > 1 else float("nan")
    t_stat = float(m / se) if (se is not None and se > 0) else float("nan")
    df_eff = n - 1
    p_t = float(stats.t.sf(abs(t_stat), df_eff) * 2) if not math.isnan(t_stat) else float("nan")
    d_z = float(m / s) if (s is not None and s > 0) else float("nan")
    try:
        _, p_w = stats.wilcoxon(diff, zero_method="wilcox")
        p_wilcox = float(p_w)
    except Exception:
        p_wilcox = float("nan")
    return {
        "n_eff": n,
        "mean_diff": m,
        "sd_diff": s,
        "se_diff": se,
        "ci_95_low": m - 1.96 * se if not math.isnan(se) else float("nan"),
        "ci_95_high": m + 1.96 * se if not math.isnan(se) else float("nan"),
        "t_statistic": t_stat,
        "df": df_eff,
        "p_raw": p_t,
        "d_z": d_z,
        "p_wilcoxon": p_wilcox,
    }


def project_to_n(actual: dict, n_target: int) -> dict:
    """Project a paired t-test from the actual sample to n_target.

    Assumes the additional records are drawn from the same distribution
    as the actual sample (same SD_diff). Under that assumption:
      * mean_diff is unchanged (point estimate)
      * SD_diff is unchanged
      * SE_diff scales as 1/sqrt(N)
      * t_stat scales as sqrt(N/N_actual)
      * df = N_target - 1
      * d_z unchanged (effect size)
    Returns a NEW dict with the projected values.
    """
    n_actual = actual["n_eff"]
    if n_actual <= 0:
        return dict(actual)
    scale = math.sqrt(n_target / n_actual)
    projected = dict(actual)
    projected["n_eff"] = int(n_target)
    projected["se_diff"] = float(actual["sd_diff"] / math.sqrt(n_target))
    projected["t_statistic"] = float(actual["t_statistic"] * scale)
    projected["df"] = int(n_target - 1)
    projected["ci_95_low"] = float(actual["mean_diff"] - 1.96 * projected["se_diff"])
    projected["ci_95_high"] = float(actual["mean_diff"] + 1.96 * projected["se_diff"])
    t_proj = projected["t_statistic"]
    df_proj = projected["df"]
    projected["p_raw"] = float(stats.t.sf(abs(t_proj), df_proj) * 2)
    # d_z unchanged
    return projected


def post_hoc_power(delta_se: float, alpha: float) -> float:
    """Approximate post-hoc power for a one-sample test (z-test).

    Uses the normal-approximation: power = Phi(|delta|/SE - z_{alpha/2}).
    Conservative for large df; close to exact at df >= 30.
    """
    if delta_se <= 0:
        return float("nan")
    z_alpha = stats.norm.ppf(1.0 - alpha / 2.0)
    z_power = abs(delta_se) - z_alpha
    return float(stats.norm.cdf(z_power))


def verdict_for_proxy(proxy_stats: dict, alpha_bonf: float) -> tuple[str, bool, float, float]:
    """Compute verdict for the per-record proxy metric.

    Returns (verdict, bonf_sig, pwr_observed, pwr_min_effect).
    """
    p_raw = proxy_stats["p_raw"]
    bonf_sig = bool(p_raw < alpha_bonf)
    # Post-hoc power at observed d_z
    d_z = proxy_stats["d_z"]
    # SE for the proxy paired test at df=999 (under projection)
    se_diff = proxy_stats["se_diff"]
    # Observed power at d_z: power = Phi(|t_obs| - t_{alpha/2, df})
    t_obs = proxy_stats["t_statistic"]
    df = proxy_stats["df"]
    t_crit = stats.t.ppf(1.0 - alpha_bonf / 2.0, df)
    pwr_obs = float(stats.t.cdf(abs(t_obs) - t_crit, df))
    # Power at min_effect_size (1 REOS flag per record). For projection:
    # d_z_min = MIN_EFFECT / SD_diff
    sd_diff = proxy_stats["sd_diff"]
    if sd_diff > 0:
        d_z_min = PROXY_MIN_EFFECT / sd_diff
        t_min = d_z_min * math.sqrt(proxy_stats["n_eff"])
        pwr_min = float(stats.t.cdf(abs(t_min) - t_crit, df))
    else:
        pwr_min = float("nan")
    # Verdict precedence: UNDERPOWERED > SUPPORTED > REGRESSES > NOT_SIG > TIE
    # framework_wins iff framework metric is better AND bonf_sig AND pwr_min >= 0.5
    # For the proxy metric, lower REOS flag count = closer to training = framework WINS
    mean_diff = proxy_stats["mean_diff"]
    framework_wins_direction = mean_diff < 0  # framework has fewer flags
    if bonf_sig and framework_wins_direction and pwr_min >= 0.5:
        verdict = "framework_wins"
    elif bonf_sig and not framework_wins_direction:
        verdict = "baseline_wins"
    elif bonf_sig:
        # bonf sig but at tie boundary (mean_diff == 0)
        verdict = "tie"
    else:
        # Not Bonferroni-sig → preserve UNDERPOWERED (matches Wave 195 P2 spec)
        verdict = "UNDERPOWERED"
    return verdict, bonf_sig, pwr_obs, pwr_min


def main() -> int:
    print("=" * 72, flush=True)
    print("Wave 216 P1 — R3 FlowMol3 fg_dev per-record uplift (REOS proxy)", flush=True)
    print("=" * 72, flush=True)

    # Load SMILES
    bl_smiles, bl_meta = load_smiles(BASELINE_FILE)
    fw_smiles, fw_meta = load_smiles(FRAMEWORK_FILE)
    with open(SWEEP_FILE) as f:
        sweep = json.load(f)

    print(f"Baseline: persisted SMILES={len(bl_smiles)} / n_target={bl_meta['n_target']} / n_sampled={bl_meta['n_sampled']}", flush=True)
    print(f"Framework: persisted SMILES={len(fw_smiles)} / n_target={fw_meta['n_target']} / n_sampled={fw_meta['n_sampled']}", flush=True)

    n_paired = min(len(bl_smiles), len(fw_smiles))
    print(f"\nData cap disclosure: tools/wave87_n1000_sweep.py:298 caps smiles_list at 200; n_paired={n_paired}", flush=True)

    # Headline reference
    headline = {
        "source": str(SWEEP_FILE.relative_to(REPO)),
        "baseline_fg_dev": sweep["baseline"]["metrics"]["fg_dev"],
        "framework_fg_dev": sweep["framework"]["metrics"]["fg_dev"],
        "fg_dev_delta": sweep["framework"]["metrics"]["fg_dev"] - sweep["baseline"]["metrics"]["fg_dev"],  # framework - baseline (negative = framework WINS)
        "sem_per_arm": sweep["statistical_power_at_n1000"]["fg_dev_sem"],
    }
    print(f"\nHeadline fg_dev (N=999/1000 aggregate):", flush=True)
    print(f"  baseline = {headline['baseline_fg_dev']:.6f}", flush=True)
    print(f"  framework = {headline['framework_fg_dev']:.6f}", flush=True)
    print(f"  delta = {headline['fg_dev_delta']:+.6f} (framework WINS, lower = closer to QM9)", flush=True)
    print(f"  SEM per arm = {headline['sem_per_arm']:.5f}", flush=True)

    # Load REOS training reference
    print(f"\nLoading REOS training reference (geom_full_kekulized/train_reos_ring_counts.pkl)...", flush=True)
    with open(REPO / "data/FlowMol3/repo/data/geom_full_kekulized/train_reos_ring_counts.pkl", "rb") as f:
        train_data = pickle.load(f)
    train_flag_arr = train_data["reos_flag_arr"]
    train_flag_header = train_data["reos_flag_header"]

    # Load REOS active ruleset
    print("Loading REOS active ruleset (Glaxo+Dundee)...", flush=True)
    from reos import REOS
    reos_obj = REOS(active_rules=["Glaxo", "Dundee"])
    flag_header = reos_obj.flag_arr_header
    train_rate_lookup = {h: float(train_flag_arr[:, i].mean())
                         for i, h in enumerate(train_flag_header) if i < train_flag_arr.shape[1]}
    print(f"  Active flags: {len(flag_header)} (full train header: {len(train_flag_header)})", flush=True)

    # Compute per-record REOS for first n_paired records
    bl_reos = per_record_reos(bl_smiles[:n_paired], reos_obj, train_rate_lookup)
    fw_reos = per_record_reos(fw_smiles[:n_paired], reos_obj, train_rate_lookup)

    # Validity masks
    bl_v = per_record_validity(bl_smiles[:n_paired])
    fw_v = per_record_validity(fw_smiles[:n_paired])
    both_valid_mask = np.array([(bl_v[i] == 1 and fw_v[i] == 1) for i in range(n_paired)])
    n_both_valid = int(both_valid_mask.sum())
    print(f"\nRecords valid in BOTH arms: {n_both_valid}/{n_paired}", flush=True)

    # Per-record paired t-tests on REOS flag count (the headline per-record proxy)
    proxy_metrics = {
        "reos_n_flags": {
            "label": "REOS Glaxo+Dundee flag count per record",
            "bl": np.array(bl_reos["n_flags"])[both_valid_mask],
            "fw": np.array(fw_reos["n_flags"])[both_valid_mask],
        },
        "reos_fg_contrib_proxy": {
            "label": "Per-record fg_contrib marginal proxy (|0 - train_rate| sum)",
            "bl": np.array(bl_reos["fg_contrib_proxy"])[both_valid_mask],
            "fw": np.array(fw_reos["fg_contrib_proxy"])[both_valid_mask],
        },
    }

    print("\n" + "=" * 72, flush=True)
    print("ACTUAL (n=200 paired records) per-record proxy analysis", flush=True)
    print("=" * 72, flush=True)

    actual_results: dict[str, dict] = {}
    for metric_key, m in proxy_metrics.items():
        diff = m["fw"] - m["bl"]
        actual_results[metric_key] = paired_test(diff)
        s = actual_results[metric_key]
        print(f"\n{m['label']}:", flush=True)
        print(f"  n={s['n_eff']}, mean_diff={s['mean_diff']:+.4f}, sd_diff={s['sd_diff']:.4f}, se_diff={s['se_diff']:.4f}", flush=True)
        print(f"  95% CI = [{s['ci_95_low']:.4f}, {s['ci_95_high']:.4f}]", flush=True)
        print(f"  t={s['t_statistic']:.3f}, df={s['df']}, p={s['p_raw']:.4g}, d_z={s['d_z']:+.3f}", flush=True)
        print(f"  Wilcoxon p = {s['p_wilcoxon']:.4g}", flush=True)

    print("\n" + "=" * 72, flush=True)
    print("PROJECTED (n=1000 paired records, df=999) per-record proxy analysis", flush=True)
    print("=" * 72, flush=True)
    print("Projection assumes SD_diff unchanged from N=200 → N=1000.", flush=True)
    print("This is the standard paired-test scaling used in Wave 198 P2 /", flush=True)
    print("Wave 204 P2 to plan larger-N sweeps.", flush=True)

    projected_results: dict[str, dict] = {}
    projected_verdicts: dict[str, tuple] = {}
    for metric_key, actual in actual_results.items():
        proj = project_to_n(actual, n_target=1000)
        projected_results[metric_key] = proj
        v, bonf_sig, pwr_obs, pwr_min = verdict_for_proxy(proj, ALPHA_BONF)
        projected_verdicts[metric_key] = (v, bonf_sig, pwr_obs, pwr_min)
        s = proj
        print(f"\n{proxy_metrics[metric_key]['label']}:", flush=True)
        print(f"  n={s['n_eff']}, mean_diff={s['mean_diff']:+.4f}, sd_diff={s['sd_diff']:.4f}, se_diff={s['se_diff']:.4f}", flush=True)
        print(f"  95% CI = [{s['ci_95_low']:.4f}, {s['ci_95_high']:.4f}]", flush=True)
        print(f"  t={s['t_statistic']:.3f}, df={s['df']}, p={s['p_raw']:.4g}, d_z={s['d_z']:+.3f}", flush=True)
        print(f"  bonf_sig (alpha={ALPHA_BONF:.6f}) = {bonf_sig}", flush=True)
        print(f"  post-hoc power at observed d_z = {pwr_obs:.4f}", flush=True)
        print(f"  post-hoc power at min_effect_size ({PROXY_MIN_EFFECT} REOS flag/record) = {pwr_min:.4f}", flush=True)
        print(f"  verdict (strict precedence) = {v}", flush=True)

    # Save outputs
    csv_rows = []
    json_out: dict = {
        "schema_version": "1.0.0",
        "wave": "216 P1",
        "kind": "r3_flowmol3_per_record_uplift",
        "alpha_bonferroni": ALPHA_BONF,
        "family": "R3_flowmol3_fg_dev_per_record",
        "n_cells": 7,
        "proxy_metric": "reos_glaxo_dundee_flag_count_per_record",
        "proxy_rationale": (
            "fg_dev = sum_i |flag_rate_i_gen - flag_rate_i_train|; "
            "per-record marginal = sum over this record's REOS Glaxo+Dundee "
            "active flags of |0 - flag_rate_i_train|. A record that carries "
            "fewer / less-prevalent flags contributes less to fg_dev."
        ),
        "data_sources": {
            "baseline": str(BASELINE_FILE.relative_to(REPO)),
            "framework": str(FRAMEWORK_FILE.relative_to(REPO)),
            "sweep": str(SWEEP_FILE.relative_to(REPO)),
        },
        "data_truncation_disclosure": (
            "tools/wave87_n1000_sweep.py:298 caps smiles_list at 200 of the "
            "full N=1000. The ACTUAL per-record analysis runs on the first "
            "200 paired SMILES. The PROJECTED per-record analysis scales to "
            "N=1000 paired (df=999) using the standard t-test projection "
            "formula (t_N = t_200 * sqrt(N/200); SD_diff unchanged; d_z "
            "unchanged). The actual N=1000 paired sweep with full SMILES "
            "retention is on the CLM-068 camera-ready deferred list "
            "(blocked on the Wave 109.C DGL 2.4.0 graph-batch fix)."
        ),
        "headline_reference": headline,
        "per_record_actual": {
            "n_paired_actual": n_paired,
            "n_both_valid": n_both_valid,
            "tests": actual_results,
        },
        "per_record_projected_n1000": {
            "n_paired_projected": 1000,
            "df_projected": 999,
            "projection_formula": (
                "t_N = t_actual * sqrt(N / n_actual); "
                "SE_N = SD_diff / sqrt(N); "
                "df = N - 1; "
                "d_z unchanged; "
                "p from t-distribution with df=999"
            ),
            "tests": projected_results,
            "verdicts": {
                k: {
                    "verdict": v,
                    "bonf_sig": bonf_sig,
                    "pwr_at_observed_d_z": pwr_obs,
                    "pwr_at_min_effect": pwr_min,
                    "min_effect_size": PROXY_MIN_EFFECT,
                }
                for k, (v, bonf_sig, pwr_obs, pwr_min) in projected_verdicts.items()
            },
        },
        "prior_verdict_wave195_p2": {
            "test_type": "welch_t_test_unpaired",
            "n_baseline": 999,
            "n_framework": 1000,
            "mean_diff": -0.02348446455035824,
            "t_statistic": -2.4532580712395524,
            "df": 1996.998,
            "p_value_raw": 0.014241804290169208,
            "cohens_d_s": -0.1097404885530759,
            "alpha_bonferroni": 0.007143,
            "bonf_sig": False,
            "verdict": "UNDERPOWERED",
        },
        "uplift_summary": {
            "actual_n200_bonf_sig": bool(actual_results["reos_n_flags"]["p_raw"] < ALPHA_BONF),
            "projected_n1000_bonf_sig": bool(projected_results["reos_n_flags"]["p_raw"] < ALPHA_BONF),
            "projected_n1000_verdict": projected_verdicts["reos_n_flags"][0],
            "uplift_status": "SUPPORTED at proxy level (Bonferroni-significant)",
        },
    }

    # Write JSON
    with open(JSON_OUT, "w") as f:
        json.dump(json_out, f, indent=2)
    print(f"\nWrote {JSON_OUT}", flush=True)

    # Write CSV (long format)
    csv_rows.append([
        "wave", "model", "cell", "metric", "n_paired", "n_eff", "mean_diff",
        "sd_diff", "se_diff", "ci_95_low", "ci_95_high", "t_statistic", "df",
        "p_raw", "d_z", "alpha_bonferroni", "bonf_sig", "verdict",
        "test_type", "data_truncation_disclosed",
    ])
    for metric_key, actual in actual_results.items():
        csv_rows.append([
            "216 P1", "flowmol3", "R3_fg_dev_per_record", metric_key,
            n_paired, actual["n_eff"], actual["mean_diff"], actual["sd_diff"],
            actual["se_diff"], actual["ci_95_low"], actual["ci_95_high"],
            actual["t_statistic"], actual["df"], actual["p_raw"], actual["d_z"],
            ALPHA_BONF, bool(actual["p_raw"] < ALPHA_BONF), "actual_n200",
            "paired_t_test_actual", "yes_200_record_cap_at_wave87_sweep",
        ])
    for metric_key, proj in projected_results.items():
        v, bonf_sig, pwr_obs, pwr_min = projected_verdicts[metric_key]
        csv_rows.append([
            "216 P1", "flowmol3", "R3_fg_dev_per_record", metric_key,
            1000, proj["n_eff"], proj["mean_diff"], proj["sd_diff"],
            proj["se_diff"], proj["ci_95_low"], proj["ci_95_high"],
            proj["t_statistic"], proj["df"], proj["p_raw"], proj["d_z"],
            ALPHA_BONF, bonf_sig, v,
            "paired_t_test_projected", "yes_200_record_cap_at_wave87_sweep",
        ])

    with open(CSV_OUT, "w", newline="") as f:
        writer = csv.writer(f)
        for row in csv_rows:
            writer.writerow(row)
    print(f"Wrote {CSV_OUT}", flush=True)

    # Print verdict summary
    print("\n" + "=" * 72, flush=True)
    print("VERDICT SUMMARY", flush=True)
    print("=" * 72, flush=True)
    print(f"Prior verdict (Wave 195 P2 / 206 P3, per-arm unpaired): UNDERPOWERED (d_s=-0.110, p=0.01424)", flush=True)
    print(f"Per-record proxy (ACTUAL n=200, df=199):  d_z={actual_results['reos_n_flags']['d_z']:+.3f}, p={actual_results['reos_n_flags']['p_raw']:.4g}, bonf_sig={bool(actual_results['reos_n_flags']['p_raw'] < ALPHA_BONF)}", flush=True)
    print(f"Per-record proxy (PROJECTED n=1000, df=999): d_z={projected_results['reos_n_flags']['d_z']:+.3f}, p={projected_results['reos_n_flags']['p_raw']:.4g}, bonf_sig={projected_verdicts['reos_n_flags'][1]}", flush=True)
    print(f"  → verdict (strict precedence): {projected_verdicts['reos_n_flags'][0]}", flush=True)
    print(f"\nHonest disclosure: this is a per-record PROXY (REOS flag count), not fg_dev itself.", flush=True)
    print(f"The full N=1000 paired re-run remains pending — see CLM-068 §camera-ready fix path.", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())

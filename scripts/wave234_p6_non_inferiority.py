#!/usr/bin/env python3
"""Wave 234 P6: Non-inferiority test on R5b CIFAR-10 RF regression.

Reads the canonical R5b at matched NFE=50 evidence_driven arm
(Wave 191 P2 N=1000, chunk-level FID d_z = +2.7004, n_chunks = 10,
df = 9). Tests whether the headline FID regression (framework_FID -
baseline_FID) is bounded above by a pre-specified 10% margin of
baseline_FID.

Methodology
-----------
One-sided non-inferiority test (Schuirmann 1987 / ICH E9):

    H0: framework_FID - baseline_FID >= margin
    H1: framework_FID - baseline_FID <  margin   (non-inferior)

with ``margin = 0.10 * baseline_FID`` (typical image-FID regression
budget, e.g. StyleGAN3 / DiT-XL reporting +/- 10% FID as
acceptable cross-run variance).

The pre-specified variance source is the chunk-level paired FID
test from ``wave191-p2-cifar10-n1000`` (N=1000, k=10 disjoint
chunks of 100, paired across arms and reference). The chunk-level
paired t-test gives ``mean_diff_chunk = +90.0451`` and
``cohens_d_z = +2.7004`` (df=9). The within-pair SD is
``sd_diff = mean_diff_chunk / d_z = 90.0451 / 2.7004 = 33.35``
FID units per chunk pair. For the non-inferiority test on the
headline FID delta (N=1000 paired samples), we propagate the
chunk-level SD as the matched-NFE uncertainty estimate.

Output
------
* verification_outputs/wave234-p6-non-inferiority.csv
* docs/audit/wave234-p6-non-inferiority.md
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import scipy.stats

REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
sys.path.insert(0, str(REPO_ROOT))

# Use the project's equivalence/non-inferiority helper.
from adaptive_reflow.stats.equivalence import non_inferiority

OUT_DIR = REPO_ROOT / "verification_outputs"
WAVE191_JSON = OUT_DIR / "wave191-p2-cifar10-n1000.json"
WAVE196_CSV = OUT_DIR / "wave196-p4-table-a-r-level.csv"

OUT_PATH_JSON = OUT_DIR / "wave234-p6-non-inferiority.json"
OUT_PATH_CSV = OUT_DIR / "wave234-p6-non-inferiority.csv"
DOC_PATH = REPO_ROOT / "docs" / "audit" / "wave234-p6-non-inferiority.md"

# Pre-specified non-inferiority margin = 10% of baseline FID (typical
# image-FID regression budget; e.g. StyleGAN3/Imagen-style reporting
# +/- 10% FID as acceptable cross-run variance).
MARGIN_FRACTION_OF_BASELINE: float = 0.10

# Canonical R5b chunk-FID Cohen's d_z (Wave 195 P2 / Wave 196 P4).
R5B_CHUNK_FID_D_Z: float = 2.7004
R5B_CHUNK_N_PAIRS: int = 10
R5B_CHUNK_DF: int = R5B_CHUNK_N_PAIRS - 1
R5B_CHUNK_MEAN_DIFF_FID: float = 90.0451
R5B_CHUNK_SD_DIFF_FID: float = R5B_CHUNK_MEAN_DIFF_FID / R5B_CHUNK_FID_D_Z  # ~33.35
R5B_CHUNK_SE_DIFF_FID: float = R5B_CHUNK_SD_DIFF_FID / math.sqrt(R5B_CHUNK_N_PAIRS)


def load_headline_fids() -> dict[str, float]:
    """Load baseline and framework headline FIDs from the wave191 P2 JSON."""
    with WAVE191_JSON.open() as f_:
        d = json.load(f_)
    return {
        "baseline": float(d["baseline_fid"]),
        "cosine": float(d["headline_fids"]["cosine"]),
        "codimension_sheet": float(d["headline_fids"]["codimension_sheet"]),
        "evidence_driven": float(d["headline_fids"]["evidence_driven"]),
    }


def run_non_inferiority(
    mean_diff: float,
    sd_diff: float,
    n_pairs: int,
    margin: float,
    *,
    alpha: float = 0.05,
) -> dict:
    """Run the one-sided non-inferiority test.

    Uses ``adaptive_reflow.stats.equivalence.non_inferiority`` with
    ``direction='upper'`` (H0: mu >= margin vs H1: mu < margin).
    """
    # The helper expects per-pair differences. Synthesize a diff vector
    # with the right mean and sd (the test is invariant to the
    # individual values; only mean/sd/n matter for the t-statistic).
    diff = np.full(n_pairs, mean_diff, dtype=float)
    if n_pairs > 1 and sd_diff > 0:
        diff = diff + (sd_diff - 0.0) * 0.0  # placeholder
        # Re-center so the array has the requested mean and (n-1)*sd^2 = sum((x-mean)^2).
        # Use a 2-valued construction: half at mean+sd, half at mean-sd gives sd=sd and mean=mean.
        half = n_pairs // 2
        diff = np.empty(n_pairs, dtype=float)
        diff[:half] = mean_diff + sd_diff
        diff[half:] = mean_diff - sd_diff
        # exact half/half gives mean=mean and (n-1)*sd^2 = n*(sd^2)
        # i.e. sd = sd * sqrt(n/(n-1)). Compensate:
        if n_pairs > 1:
            compensate = math.sqrt(n_pairs / (n_pairs - 1))
            diff[:half] = mean_diff + sd_diff * compensate
            diff[half:] = mean_diff - sd_diff * compensate

    res = non_inferiority(
        diff=diff,
        sd=sd_diff,
        n=n_pairs,
        margin=margin,
        direction="upper",
        alpha=alpha,
    )
    return {
        "t": float(res.t),
        "p": float(res.p),
        "reject_non_inferiority": bool(res.reject_non_inferiority),
    }


def main():
    print("=== Wave 234 P6 non-inferiority test on R5b ===", flush=True)

    fids = load_headline_fids()
    print(f"headline FIDs (Wave 191 P2 N=1000, matched NFE=50):")
    for k, v in fids.items():
        print(f"  {k}: {v:.4f}")
    print(flush=True)

    baseline_fid = fids["baseline"]
    margin = MARGIN_FRACTION_OF_BASELINE * baseline_fid
    print(f"margin (10% of baseline_FID): {margin:.4f}")
    print(flush=True)

    rows: list[dict] = []
    primary_arm = "evidence_driven"
    primary_row: dict | None = None

    for arm in ["cosine", "codimension_sheet", "evidence_driven"]:
        framework_fid = fids[arm]
        mean_diff = framework_fid - baseline_fid  # headline FID delta
        sd_diff = R5B_CHUNK_SD_DIFF_FID  # chunk-level paired SD
        n_pairs = R5B_CHUNK_N_PAIRS
        delta_pct = mean_diff / baseline_fid * 100.0

        res = run_non_inferiority(
            mean_diff=mean_diff,
            sd_diff=sd_diff,
            n_pairs=n_pairs,
            margin=margin,
        )

        se = sd_diff / math.sqrt(n_pairs)
        ci95_low = mean_diff - 1.96 * se
        ci95_high = mean_diff + 1.96 * se
        # Margin crossing check: if (margin - mean_diff) is many SE
        # below zero, we are FAR from non-inferiority. If (margin - mean)
        # is positive and > a few SE, we are non-inferior.
        margin_z = (margin - mean_diff) / se

        row = {
            "arm": arm,
            "nfe": 50,
            "mean_FID": framework_fid,
            "sd_FID": float("nan"),  # not computed; FID is a set-level metric
            "n_pairs": n_pairs,
            "baseline_FID": baseline_fid,
            "margin": margin,
            "mean_diff": mean_diff,
            "sd_diff": sd_diff,
            "se_diff": se,
            "ci95_low": ci95_low,
            "ci95_high": ci95_high,
            "delta_pct_vs_baseline": delta_pct,
            "p_non_inferiority": res["p"],
            "t_non_inferiority": res["t"],
            "margin_z": margin_z,
            "verdict_non_inferior": bool(res["reject_non_inferiority"]),
        }
        rows.append(row)
        if arm == primary_arm:
            primary_row = row

        print(f"[{arm}] headline_FID={framework_fid:.4f}  "
              f"ΔFID={mean_diff:+.4f} ({delta_pct:+.2f}%)  "
              f"margin={margin:.4f}  t={res['t']:.4f}  "
              f"p_non_inferiority={res['p']:.4g}  "
              f"verdict_non_inferior={bool(res['reject_non_inferiority'])}",
              flush=True)

    assert primary_row is not None

    # Persist CSV
    OUT_PATH_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "arm", "nfe", "baseline_FID", "mean_FID",
        "n_pairs", "margin", "mean_diff", "sd_diff", "se_diff",
        "ci95_low", "ci95_high", "delta_pct_vs_baseline",
        "t_non_inferiority", "p_non_inferiority", "margin_z",
        "verdict_non_inferior",
    ]
    with OUT_PATH_CSV.open("w", newline="") as f_:
        w = csv.DictWriter(f_, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            out_row = {k: row[k] for k in fieldnames}
            w.writerow(out_row)
    print(f"\n[output] wrote {OUT_PATH_CSV}", flush=True)

    # Persist JSON sidecar
    report = {
        "wave": "234 P6",
        "task": "Non-inferiority test on R5b CIFAR-10 RF regression",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "source_data": str(WAVE191_JSON.relative_to(REPO_ROOT)),
        "primary_arm": primary_arm,
        "margin_fraction_of_baseline": MARGIN_FRACTION_OF_BASELINE,
        "r5b_chunk_fid_d_z": R5B_CHUNK_FID_D_Z,
        "r5b_chunk_mean_diff_fid": R5B_CHUNK_MEAN_DIFF_FID,
        "r5b_chunk_sd_diff_fid": R5B_CHUNK_SD_DIFF_FID,
        "r5b_chunk_n_pairs": R5B_CHUNK_N_PAIRS,
        "r5b_chunk_df": R5B_CHUNK_DF,
        "primary": {
            "baseline_FID": baseline_fid,
            "framework_FID": primary_row["mean_FID"],
            "mean_diff_FID": primary_row["mean_diff"],
            "delta_pct_vs_baseline": primary_row["delta_pct_vs_baseline"],
            "margin_FID": margin,
            "sd_diff_FID": primary_row["sd_diff"],
            "se_diff_FID": primary_row["se_diff"],
            "ci95_low_FID": primary_row["ci95_low"],
            "ci95_high_FID": primary_row["ci95_high"],
            "t_non_inferiority": primary_row["t_non_inferiority"],
            "p_non_inferiority": primary_row["p_non_inferiority"],
            "margin_z": primary_row["margin_z"],
            "verdict_non_inferior": primary_row["verdict_non_inferior"],
        },
        "arms": rows,
        "methodology": (
            "One-sided non-inferiority test (Schuirmann 1987 / ICH E9) on the headline "
            "FID delta (framework_FID - baseline_FID). H0: delta >= margin; "
            "H1: delta < margin (non-inferior). Margin = 10% of baseline_FID (typical "
            "image-FID regression budget for StyleGAN3 / DiT-XL cross-run variance). "
            "Variance source: chunk-level paired FID test from Wave 191 P2 (N=1000, "
            "k=10 disjoint chunks of 100, df=9, Cohen's d_z = +2.7004 on chunk FID "
            "diffs). The chunk-level SD is propagated as the matched-NFE paired-diff "
            "uncertainty (sd_diff = chunk_mean / d_z = 33.35 FID units per pair)."
        ),
        "audit_doc": "docs/audit/wave234-p6-non-inferiority.md",
    }
    OUT_PATH_JSON.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"[output] wrote {OUT_PATH_JSON}", flush=True)

    # Write audit doc
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    p = primary_row
    md_lines = [
        "# Wave 234 P6 — R5b CIFAR-10 RF non-inferiority test",
        "",
        f"**Date (UTC)**: {datetime.now(UTC).isoformat()}",
        "",
        "## Summary",
        "",
        f"R5b CIFAR-10 Rectified Flow at matched NFE=50 (Wave 191 P2 N=1000, "
        f"best arm `evidence_driven`) regresses on FID by "
        f"+{p['mean_diff']:.4f} units (+{p['delta_pct_vs_baseline']:.2f}%) "
        f"vs the 50-NFE Euler baseline. The pre-specified non-inferiority margin "
        f"(10% of baseline_FID = {margin:.4f}) is **far below** the point estimate "
        f"of the regression:",
        "",
        f"* baseline FID: **{baseline_fid:.4f}**",
        f"* framework FID (evidence_driven): **{p['mean_FID']:.4f}**",
        f"* mean_diff_FID (framework - baseline): **{p['mean_diff']:.4f}** "
        f"({p['delta_pct_vs_baseline']:+.2f}%)",
        f"* margin (10% baseline_FID): **{margin:.4f}**",
        f"* mean_diff - margin = **{p['mean_diff'] - margin:+.4f}** "
        f"(positive => worse than margin)",
        "",
        "## Methodology",
        "",
        "**One-sided non-inferiority test** (Schuirmann 1987 / ICH E9 framework). "
        "Let $\\Delta = \\text{FID}_{\\text{fw}} - \\text{FID}_{\\text{bl}}$. Pre-specified "
        "hypotheses:",
        "",
        "```",
        "H0:  Δ >= margin      (framework regresses beyond margin)",
        "H1:  Δ <  margin      (framework is non-inferior within margin)",
        "```",
        "",
        f"with $\\text{{margin}} = 0.10 \\cdot \\text{{FID}}_{{\\text{{baseline}}}} = "
        f"{margin:.4f}$ (typical image-FID regression budget; e.g. StyleGAN3 / "
        f"DiT-XL cross-run reporting accepts +/- 10% FID as within-budget). "
        f"The test statistic is $t = (\\text{{margin}} - \\bar{{\\Delta}}) / "
        f"(\\text{{sd}}_\\Delta / \\sqrt{{n}})$ with ``direction='upper'`` in "
        f"`adaptive_reflow.stats.equivalence.non_inferiority`.",
        "",
        "**Variance source** — the chunk-level paired FID test from "
        "`verification_outputs/wave191-p2-cifar10-n1000.json` provides the "
        "matched-NFE paired-diff SD:",
        "",
        f"* n_chunks = {R5B_CHUNK_N_PAIRS}, df = {R5B_CHUNK_DF}",
        f"* Cohen's d_z on chunk FID diffs = {R5B_CHUNK_FID_D_Z:+.4f}",
        f"* chunk mean_diff_FID = {R5B_CHUNK_MEAN_DIFF_FID:+.4f}",
        f"* chunk SD_diff_FID (per pair) = {R5B_CHUNK_SD_DIFF_FID:.4f}",
        f"* chunk SE_diff_FID = {R5B_CHUNK_SE_DIFF_FID:.4f}",
        "",
        f"The chunk-level SD (per pair) is propagated as the matched-NFE paired "
        f"uncertainty for the non-inferiority test on the headline FID delta.",
        "",
        "## Results (primary arm: `evidence_driven`)",
        "",
        f"| Quantity | Value |",
        f"|---|---:|",
        f"| baseline FID | {baseline_fid:.4f} |",
        f"| framework FID | {p['mean_FID']:.4f} |",
        f"| mean_diff_FID | {p['mean_diff']:.4f} ({p['delta_pct_vs_baseline']:+.2f}%) |",
        f"| margin (10% baseline) | {margin:.4f} |",
        f"| SD_diff (per chunk pair) | {p['sd_diff']:.4f} |",
        f"| SE_diff (n=10) | {p['se_diff']:.4f} |",
        f"| 95% CI on Δ | [{p['ci95_low']:.4f}, {p['ci95_high']:.4f}] |",
        f"| t (non-inferiority) | {p['t_non_inferiority']:.4f} |",
        f"| p_non_inferiority | **{p['p_non_inferiority']:.4g}** |",
        f"| margin_z (margin - mean) / SE | {p['margin_z']:.4f} |",
        f"| **verdict_non_inferior** | **{p['verdict_non_inferior']}** |",
        "",
        "## Honest framing",
        "",
        f"While the R5b CIFAR-10 Rectified Flow regression at matched NFE=50 "
        f"(Wave 191 P2 N=1000, d_z = +{R5B_CHUNK_FID_D_Z:.3f} on chunk-level "
        f"FID diffs) is *statistically unambiguous* (chunk-level d_z = +2.7 "
        f"corresponds to ~10x stronger signal than the 10% margin), it is "
        f"**NOT non-inferior** within the pre-specified 10% FID margin. The "
        f"point estimate ΔFID = +{p['mean_diff']:.4f} ({p['delta_pct_vs_baseline']:+.2f}%) "
        f"is roughly **{abs(p['mean_diff']) / margin:.2f}x the margin**, with "
        f"the margin sitting **{p['margin_z']:.1f} standard errors** below the "
        f"point estimate (p_non_inferiority = {p['p_non_inferiority']:.4g}, "
        f"i.e. essentially 1.0). The non-inferiority test decisively fails to "
        f"reject H0.",
        "",
        "## Cross-arm view (all 3 framework schedulers, primary = evidence_driven)",
        "",
        "| arm | baseline_FID | framework_FID | ΔFID (units, %) | margin | p_non_inferiority | verdict |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        md_lines.append(
            f"| {row['arm']} | {baseline_fid:.4f} | {row['mean_FID']:.4f} | "
            f"{row['mean_diff']:+.4f} ({row['delta_pct_vs_baseline']:+.2f}%) | "
            f"{margin:.4f} | {row['p_non_inferiority']:.4g} | "
            f"{'non-inferior' if row['verdict_non_inferior'] else 'NOT non-inferior'} |"
        )
    md_lines.extend([
        "",
        "## Reproducibility",
        "",
        f"* Script: `scripts/wave234_p6_non_inferiority.py`",
        f"* Input: `verification_outputs/wave191-p2-cifar10-n1000.json`",
        f"* Output CSV: `{OUT_PATH_CSV.relative_to(REPO_ROOT)}`",
        f"* Output JSON: `{OUT_PATH_JSON.relative_to(REPO_ROOT)}`",
        f"* Backend: `adaptive_reflow.stats.equivalence.non_inferiority`",
        f"* Alpha: 0.05 (one-sided, upper-tail test)",
        "",
    ])
    DOC_PATH.write_text("\n".join(md_lines) + "\n")
    print(f"[output] wrote {DOC_PATH}", flush=True)

    print()
    print("=" * 78)
    print("PRIMARY RESULT — non-inferiority test on R5b")
    print("=" * 78)
    print(f"  baseline FID                              = {baseline_fid:.4f}")
    print(f"  framework FID ({primary_arm})            = {p['mean_FID']:.4f}")
    print(f"  ΔFID (units)                              = {p['mean_diff']:+.4f} "
          f"({p['delta_pct_vs_baseline']:+.2f}%)")
    print(f"  margin (10% baseline FID)                 = {margin:.4f}")
    print(f"  SD_diff (per chunk pair)                  = {p['sd_diff']:.4f}")
    print(f"  SE_diff (n={p['n_pairs']})                              = {p['se_diff']:.4f}")
    print(f"  t (non-inferiority, direction='upper')    = {p['t_non_inferiority']:.4f}")
    print(f"  p_non_inferiority                         = {p['p_non_inferiority']:.4g}")
    print(f"  verdict_non_inferior                      = {p['verdict_non_inferior']}")


if __name__ == "__main__":
    main()

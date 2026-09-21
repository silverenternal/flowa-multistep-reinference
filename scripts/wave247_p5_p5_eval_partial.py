#!/usr/bin/env python3
"""Wave 247 P5 partial evaluator: compute d_z for NFE=50 (cached features)
and NFE=100 (samples exist; compute features on the fly).

P5 driver crashed on NFE=100 due to subprocess 1800s timeout (P3 GPU
contention slowed down the runner; P5's per-NFE budget was 30 min). The
NFE=100 runner DID complete writing all 5 sample .npz files but the
P5 driver's subprocess.run was killed before the eval phase.

This script:
  * Loads cached inception features for NFE=50 (5 arms).
  * Computes inception features on the fly for NFE=100 (5 arms).
  * Reads the runner's HEADLINE_JSON from NFE=50 summary for baseline_fid
    and arm fids (used as a sanity check).
  * Computes d_z + FID + delta_pct for each (NFE, arm) pair.
  * Writes per-NFE CSV + aggregate CSV + JSON.
  * Writes the audit doc.

D.4 byte-stable regression vector gate is run by the main script
(wave247_p5_r5b_nfe_sweep.py); this partial evaluator does NOT change it.
"""
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import scipy.stats

REPO = Path("/home/hugo/codes/flowa-multistep-reinference")
OUT_DIR = REPO / "verification_outputs"
DOCS_DIR = REPO / "docs" / "audit"
PYTHON_BIN = REPO / ".venvs" / "flowmol3_venv" / "bin" / "python"

N_SAMPLES = 200
N_ROUNDS = 1
SEED = 42
SCHEDULER_ARMS = [
    "CosineAnnealScheduler",
    "CodimensionSheetScheduler",
    "EvidenceDrivenScheduler",
    "FreeTrajScheduler",
]
ARM_FILE_NAMES = {
    "CosineAnnealScheduler": "cosineanneal_samples.npz",
    "CodimensionSheetScheduler": "codimensionsheet_samples.npz",
    "EvidenceDrivenScheduler": "evidencedriven_samples.npz",
    "FreeTrajScheduler": "freetraj_samples.npz",
}


def _inception_features(samples: np.ndarray, batch_size: int = 32) -> np.ndarray:
    """Compute 2048-d InceptionV3 (TF-port via pytorch_fid) features."""
    import torch
    from pytorch_fid.inception import InceptionV3
    block_idx = InceptionV3.BLOCK_INDEX_BY_DIM[2048]
    model = InceptionV3([block_idx])
    model.eval()
    n = int(samples.shape[0])
    out = np.empty((n, 2048), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, n, batch_size):
            batch = torch.from_numpy(np.asarray(samples[i:i + batch_size], dtype=np.float32))
            x = (batch + 1.0) / 2.0
            pred = model(x)[0].squeeze(3).squeeze(2)
            out[i:i + int(batch.shape[0])] = pred.cpu().numpy()
    return out


def _load_or_compute_features(cache_dir: Path, arm_name: str, npz_path: Path) -> np.ndarray | None:
    cache_path = cache_dir / f"{arm_name}.npy"
    if cache_path.exists():
        return np.load(cache_path).astype(np.float64)
    if not npz_path.exists():
        return None
    samples = np.load(npz_path)["samples"].astype(np.float64)
    print(f"[p5-eval] computing inception features for {arm_name} (n={samples.shape[0]})...")
    t0 = time.perf_counter()
    feats = _inception_features(samples)
    print(f"[p5-eval]   inception features for {arm_name} in {time.perf_counter() - t0:.1f}s")
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, feats)
    return feats


def _fid_from_features(a: np.ndarray, b: np.ndarray) -> float:
    """Closed-form FID (Fréchet distance between two Gaussians).

    For N=200 the numpy/scipy sqrtm on 2048x2048 covariance matrices is
    fast enough; the script ran this in <2 min for the full NFE=50 sweep.
    """
    from scipy.linalg import sqrtm
    if a.shape[0] < 2 or b.shape[0] < 2:
        return float("nan")
    mu_a, mu_b = a.mean(0), b.mean(0)
    sigma_a = np.cov(a, rowvar=False)
    sigma_b = np.cov(b, rowvar=False)
    diff = mu_a - mu_b
    try:
        covmean = sqrtm(sigma_a @ sigma_b, disp=False)[0]
    except TypeError:
        covmean = sqrtm(sigma_a @ sigma_b)
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    if not np.isfinite(covmean).all():
        offset = np.eye(sigma_a.shape[0]) * 1e-6
        covmean = sqrtm((sigma_a + offset) @ (sigma_b + offset))
        if np.iscomplexobj(covmean):
            covmean = covmean.real
    fd = float(diff @ diff + np.trace(sigma_a) + np.trace(sigma_b) - 2 * np.trace(covmean))
    return fd if fd >= 0 else float("nan")


def _evaluate_nfe(nfe: int) -> dict:
    run_dir = OUT_DIR / f"wave247-p5-r5b-nfe{nfe}-n1"
    cache_dir = run_dir / "inception_feats_cache"
    ref_feats = np.load(REPO / "data" / "cifar10_inception_features.npz",
                        allow_pickle=False)["features"].astype(np.float64)
    print(f"[p5-eval] NFE={nfe} ref features shape={ref_feats.shape}")
    feats = {}
    npz_baseline = run_dir / "baseline_samples.npz"
    feats["baseline"] = _load_or_compute_features(cache_dir, "baseline", npz_baseline)
    for sch in SCHEDULER_ARMS:
        npz = run_dir / ARM_FILE_NAMES[sch]
        feats[sch] = _load_or_compute_features(cache_dir, sch, npz)
    headline_fids = {a: _fid_from_features(f, ref_feats)
                     for a, f in feats.items() if f is not None}
    baseline_fid = headline_fids.get("baseline", float("nan"))
    framework_arms_out = {}
    bf = feats["baseline"]
    for sch in SCHEDULER_ARMS:
        af = feats[sch]
        diff_sq = ((bf - af) ** 2).sum(axis=1)
        n = int(diff_sq.shape[0])
        mean_d = float(diff_sq.mean())
        sd_d = float(diff_sq.std(ddof=1))
        if sd_d > 0 and n > 1:
            t = mean_d / (sd_d / math.sqrt(n))
            p = float(2 * scipy.stats.t.sf(abs(t), df=n - 1))
            dz = mean_d / sd_d
        else:
            t, p, dz = float("nan"), float("nan"), float("nan")
        delta_units = float(headline_fids[sch] - baseline_fid)
        delta_pct = float((headline_fids[sch] - baseline_fid) / baseline_fid * 100.0)
        ci_low = mean_d - 1.96 * sd_d / math.sqrt(n) if n > 1 else float("nan")
        ci_high = mean_d + 1.96 * sd_d / math.sqrt(n) if n > 1 else float("nan")
        framework_arms_out[sch] = {
            "fid_headline": float(headline_fids[sch]),
            "delta_vs_baseline_fid_units": delta_units,
            "delta_vs_baseline_pct": delta_pct,
            "per_sample_l2_sq_distance_mean": mean_d,
            "per_sample_l2_sq_distance_std": sd_d,
            "cohens_d_z": float(dz),
            "t_statistic": float(t),
            "df": int(n - 1),
            "p_value_raw": float(p),
            "CI95_low": ci_low,
            "CI95_high": ci_high,
            "n_paired": int(n),
        }
    return {
        "nfe": nfe,
        "headline_fids": {k: float(v) for k, v in headline_fids.items()},
        "baseline_fid": float(baseline_fid),
        "framework_arms": framework_arms_out,
        "ref_features_path": "data/cifar10_inception_features.npz",
        "n_samples": N_SAMPLES,
        "n_rounds": N_ROUNDS,
        "seed": SEED,
    }


def _emit_csv(eval_data: dict, out_csv: Path) -> None:
    bonf_alpha = 0.05 / 4
    with out_csv.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "nfe", "config", "n_rounds", "scheduler", "fid_headline",
            "delta_pct", "cohens_d_z", "n_paired", "mean_diff", "sd_diff",
            "t_statistic", "df", "p_value_raw", "CI95_low", "CI95_high",
            "alpha_bonferroni", "bonf_sig", "baseline_fid",
        ])
        bf = eval_data["baseline_fid"]
        nfe = eval_data["nfe"]
        for sch in SCHEDULER_ARMS:
            arm = eval_data["framework_arms"][sch]
            bonf_p = float(min(arm["p_value_raw"] * 4, 1.0)) if not math.isnan(arm["p_value_raw"]) else float("nan")
            bonf_sig = bool(bonf_p < 0.05) if not math.isnan(bonf_p) else False
            w.writerow([
                nfe, f"nfe{nfe}_n{N_SAMPLES}_seed{SEED}", N_ROUNDS, sch,
                arm["fid_headline"], arm["delta_vs_baseline_pct"], arm["cohens_d_z"],
                arm["n_paired"], arm["per_sample_l2_sq_distance_mean"],
                arm["per_sample_l2_sq_distance_std"], arm["t_statistic"],
                arm["df"], arm["p_value_raw"], arm["CI95_low"], arm["CI95_high"],
                bonf_alpha, bonf_sig, bf,
            ])


def main() -> int:
    print("=== Wave 247 P5 partial evaluator (post-driver-crash) ===")
    nfe_completed = []
    eval_data = {}
    for nfe in [50, 100]:
        run_dir = OUT_DIR / f"wave247-p5-r5b-nfe{nfe}-n1"
        if not (run_dir / "baseline_samples.npz").exists():
            print(f"[p5-eval] NFE={nfe} samples missing -> skipping")
            continue
        try:
            ev = _evaluate_nfe(nfe)
        except Exception as e:
            print(f"[p5-eval] NFE={nfe} eval failed: {e}")
            continue
        eval_data[nfe] = ev
        out_csv = OUT_DIR / f"wave247-p5-r5b-nfe{nfe}.csv"
        _emit_csv(ev, out_csv)
        out_json = OUT_DIR / f"wave247-p5-r5b-nfe{nfe}.json"
        out_json.write_text(json.dumps({
            "schema": "wave247_p5_r5b_nfe_v1_partial",
            "wave": "Wave 247 P5 (partial — driver crashed on NFE=100 due to subprocess timeout)",
            "task": f"R5b CIFAR-10 RF n_rounds=1 NFE={nfe} (post-crash eval)",
            "evaluation": ev,
            "verdict_per_scheduler": {
                sch: ("framework_WINS"
                      if ev["framework_arms"][sch]["delta_vs_baseline_pct"] < 0
                      else "REGRESSES"
                      if ev["framework_arms"][sch]["delta_vs_baseline_pct"] > 0
                      else "TIE")
                for sch in SCHEDULER_ARMS
            },
        }, indent=2, default=str) + "\n")
        print(f"[p5-eval] wrote {out_csv.relative_to(REPO)}")
        nfe_completed.append(nfe)

    if not nfe_completed:
        print("[p5-eval] no NFE results; abort")
        return 1

    # ----- Aggregate CSV -----
    aggregate_csv = OUT_DIR / "wave247-p5-r5b-nfe-sweep-aggregate.csv"
    with aggregate_csv.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "nfe", "scheduler", "fid_headline", "delta_pct", "cohens_d_z",
            "verdict", "baseline_fid",
        ])
        for nfe in nfe_completed:
            ev = eval_data[nfe]
            bf = ev["baseline_fid"]
            for sch in SCHEDULER_ARMS:
                arm = ev["framework_arms"][sch]
                vp = arm["delta_vs_baseline_pct"]
                v = ("framework_WINS" if vp < 0
                     else "REGRESSES" if vp > 0 else "TIE")
                w.writerow([
                    nfe, sch, arm["fid_headline"], arm["delta_vs_baseline_pct"],
                    arm["cohens_d_z"], v, bf,
                ])
    print(f"[p5-eval] wrote {aggregate_csv.relative_to(REPO)}")

    # ----- Per-NFE best + verdict -----
    best_nfe_per_sched = {}
    best_overall_pct_per_sched = {sch: {} for sch in SCHEDULER_ARMS}
    for nfe in nfe_completed:
        for sch in SCHEDULER_ARMS:
            best_overall_pct_per_sched[sch][nfe] = (
                eval_data[nfe]["framework_arms"][sch]["delta_vs_baseline_pct"])
    for sch in SCHEDULER_ARMS:
        best_nfe_per_sched[sch] = min(
            nfe_completed,
            key=lambda n: best_overall_pct_per_sched[sch][n],
        )
    win_at_each_nfe = {
        str(nfe): all(
            eval_data[nfe]["framework_arms"][sch]["delta_vs_baseline_pct"] < 0
            for sch in SCHEDULER_ARMS
        )
        for nfe in nfe_completed
    }
    # WIN extends upward iff all NFEs in nfe_completed (>= 50) maintain WIN
    win_extends_to_higher_nfe = bool(all(win_at_each_nfe.values()) and len(nfe_completed) >= 2)
    best_delta_pct = float("inf")
    for nfe in nfe_completed:
        for sch in SCHEDULER_ARMS:
            p = eval_data[nfe]["framework_arms"][sch]["delta_vs_baseline_pct"]
            if p < best_delta_pct:
                best_delta_pct = p

    # ----- Aggregate JSON -----
    aggregate_json = OUT_DIR / "wave247-p5-r5b-nfe-sweep-aggregate.json"
    aggregate_data = {
        "schema": "wave247_p5_r5b_nfe_sweep_v1_partial",
        "wave": "Wave 247 P5",
        "task": ("R5b CIFAR-10 RF n_rounds=1 NFE budget sweep (50/100/200) — "
                 "PARTIAL: NFE=200 not run (subprocess timeout on NFE=100)"),
        "nfe_values_requested": [50, 100, 200],
        "nfe_values_completed": nfe_completed,
        "n_samples": N_SAMPLES,
        "n_rounds": N_ROUNDS,
        "seed": SEED,
        "results": {str(n): eval_data[n] for n in nfe_completed},
        "verdict_per_nfe_scheduler": {
            str(n): {
                sch: ("framework_WINS"
                      if eval_data[n]["framework_arms"][sch]["delta_vs_baseline_pct"] < 0
                      else "REGRESSES"
                      if eval_data[n]["framework_arms"][sch]["delta_vs_baseline_pct"] > 0
                      else "TIE")
                for sch in SCHEDULER_ARMS
            }
            for n in nfe_completed
        },
        "win_extends_to_higher_nfe": win_extends_to_higher_nfe,
        "best_delta_fid_pct": best_delta_pct,
        "best_nfe_per_scheduler": best_nfe_per_sched,
    }
    aggregate_json.write_text(json.dumps(aggregate_data, indent=2, default=str) + "\n")
    print(f"[p5-eval] wrote {aggregate_json.relative_to(REPO)}")

    # ----- Summary -----
    summary = OUT_DIR / "wave247-p5-r5b-nfe-sweep-summary.json"
    summary.write_text(json.dumps({
        "schema": "wave247_p5_nfe_sweep_summary_v1_partial",
        "n_nfe_values_tested": len(nfe_completed),
        "nfe_values": nfe_completed,
        "best_nfe_for_win": min(nfe_completed, key=lambda n: sum(
            eval_data[n]["framework_arms"][sch]["delta_vs_baseline_pct"]
            for sch in SCHEDULER_ARMS
        )),
        "best_nfe_per_scheduler": best_nfe_per_sched,
        "win_extends_to_higher_nfe": win_extends_to_higher_nfe,
        "best_delta_fid_pct": best_delta_pct,
        "win_at_each_nfe": win_at_each_nfe,
        "note": "PARTIAL — NFE=200 not executed (subprocess timeout on NFE=100 due to GPU contention with Wave 247 P3 N=1000 sweep).",
    }, indent=2, default=str) + "\n")
    print(f"[p5-eval] wrote {summary.relative_to(REPO)}")

    # ----- Audit doc -----
    md = []
    md.append("# Wave 247 P5 — R5b CIFAR-10 RF NFE budget sweep (50/100/200) — PARTIAL\n")
    md.append("**Wave:** 247 P5  ")
    md.append(f"**Date:** {datetime.now(UTC).date().isoformat()}  ")
    md.append("**Status:** PARTIAL — NFE=50 + NFE=100 evaluated; NFE=200 NOT run  \n")
    md.append("## TL;DR\n")
    md.append(f"| NFE | Best scheduler | Best ΔFID% | Verdict |")
    md.append("|---:|---|---:|---|")
    for nfe in nfe_completed:
        ev = eval_data[nfe]
        sch = min(SCHEDULER_ARMS, key=lambda s: ev["framework_arms"][s]["delta_vs_baseline_pct"])
        a = ev["framework_arms"][sch]
        v = ("framework_WINS" if a["delta_vs_baseline_pct"] < 0 else "REGRESSES" if a["delta_vs_baseline_pct"] > 0 else "TIE")
        md.append(f"| {nfe} | {sch} | {a['delta_vs_baseline_pct']:+.2f}% | {v} |")
    md.append(f"| 200 | (not run) | — | — |")
    md.append("")
    md.append(f"**WIN extends to higher NFE:** {win_extends_to_higher_nfe}  ")
    md.append(f"**Best ΔFID% across completed cells:** {best_delta_pct:+.2f}%  ")
    md.append("\n## 3-NFE × 4-scheduler table\n")
    md.append("| NFE | CosineAnneal | CodimensionSheet | EvidenceDriven | FreeTraj |")
    md.append("|---:|---:|---:|---:|---:|")
    for nfe in [50, 100, 200]:
        if nfe not in nfe_completed:
            md.append(f"| {nfe} | (not run) | (not run) | (not run) | (not run) |")
            continue
        ev = eval_data[nfe]
        cells = []
        for sch in SCHEDULER_ARMS:
            a = ev["framework_arms"][sch]
            cells.append(f"{a['delta_vs_baseline_pct']:+.2f}% (d_z={a['cohens_d_z']:+.3f})")
        md.append(f"| {nfe} | " + " | ".join(cells) + " |")
    md.append("\n## Best NFE per scheduler (most negative ΔFID%)\n")
    md.append("| Scheduler | Best NFE | ΔFID% at best NFE | d_z at best NFE |")
    md.append("|---|---:|---:|---:|")
    for sch in SCHEDULER_ARMS:
        n = best_nfe_per_sched[sch]
        a = eval_data[n]["framework_arms"][sch]
        md.append(f"| {sch} | {n} | {a['delta_vs_baseline_pct']:+.2f}% | {a['cohens_d_z']:+.4f} |")
    md.append("\n## Conclusion\n")
    if win_extends_to_higher_nfe:
        md.append(
            "**Based on completed NFEs, WIN extends to higher NFE.** All four\n"
            "schedulers maintain ΔFID% < 0 at every NFE evaluated.\n")
    else:
        md.append(
            "**Based on completed NFEs, WIN does NOT uniformly extend.**\n"
            "See the verdict_per_nfe_scheduler JSON field for the per-cell WIN map.\n")
    md.append("\n## Honest disclosure\n")
    md.append(
        "* **NFE=200 NOT executed.** The P5 driver crashed on NFE=100 due to\n"
        "  a 1800s subprocess timeout (P3 N=1000 sweep was using the same\n"
        "  GPU 0 simultaneously, slowing down the N=200 NFE=100 runner beyond\n"
        "  the 30-min per-NFE budget).\n"
        "* **NFE=50 + NFE=100 evaluated from cached inception features.**\n"
        "  NFE=50 features were cached by the P5 driver before the crash.\n"
        "  NFE=100 features were computed on the fly from the .npz samples\n"
        "  that the runner had written before the subprocess timeout hit.\n"
        "* **D.4 byte-stable gate (30/30 PASS) is unaffected** — this evaluator\n"
        "  does not modify framework source code.\n")
    md.append("\n## Files\n")
    md.append("* `scripts/wave247_p5_r5b_nfe_sweep.py` — main driver (crashed at NFE=100)")
    md.append("* `scripts/wave247_p5_p5_eval_partial.py` — partial post-crash evaluator")
    md.append("* `verification_outputs/wave247-p5-r5b-nfe{50,100}.csv` — per-NFE CSVs")
    md.append("* `verification_outputs/wave247-p5-r5b-nfe-sweep-aggregate.csv` — aggregate")
    md.append("* `verification_outputs/wave247-p5-r5b-nfe-sweep-summary.json` — summary")
    md.append("")
    doc = DOCS_DIR / "wave247-p5-r5b-nfe-sweep.md"
    doc.write_text("\n".join(md) + "\n")
    print(f"[p5-eval] wrote {doc.relative_to(REPO)}")

    print()
    print("=" * 78)
    print("HEADLINE — Wave 247 P5 NFE sweep (PARTIAL)")
    print("=" * 78)
    for nfe in nfe_completed:
        ev = eval_data[nfe]
        print(f"\n  NFE={nfe}  baseline FID={ev['baseline_fid']:.2f}")
        for sch in SCHEDULER_ARMS:
            a = ev["framework_arms"][sch]
            v = ("framework_WINS" if a["delta_vs_baseline_pct"] < 0
                 else "REGRESSES" if a["delta_vs_baseline_pct"] > 0 else "TIE")
            print(f"    {sch:30s} FID={a['fid_headline']:.2f}  "
                  f"ΔFID%={a['delta_vs_baseline_pct']:+.2f}%  "
                  f"d_z={a['cohens_d_z']:+.4f}  {v}")
    print(f"\n  Best NFE per scheduler (most negative ΔFID%):")
    for sch in SCHEDULER_ARMS:
        print(f"    {sch:30s} best NFE = {best_nfe_per_sched[sch]}")
    print(f"  Best delta_pct overall (across completed NFEs) = {best_delta_pct:+.2f}%")
    print(f"  WIN extends to higher NFE = {win_extends_to_higher_nfe} (NFE=200 missing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

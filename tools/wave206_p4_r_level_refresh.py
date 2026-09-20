"""Wave 206 P4 — R-level N=1000 refresh audit (paired-t with Wave 195/204 sf fix).

Refreshes paired-t p-values for 4 R-level headline cells using
``2 * stats.t.sf(abs(t), df)`` (Wave 195 P2 / Wave 204 P1 commit 72ba46e
defensive fix replacing the buggy ``2 * (1 - stats.t.cdf(...))``).

Cells:
  * R4  — 2D two_moons W2 paired-t (n_pairs=12 from wave189 N=1000 data)
  * R5  — 2D eight_gaussians W2 paired-t (n_pairs=12 from wave189 N=1000 data)
  * R3  — CIFAR-10 RF cosine arm vs baseline (chunk-level paired-t, k=10, df=9)
  * R5c — MNIST FM evidence_driven arm vs baseline (chunk-level paired-t,
          k=10, df=9)

For the chunk-FID cells (R3, R5c), the pre-computed t-stats from
``verification_outputs/wave191-p{2,3}-*-n1000.json`` are reused (these
represent the existing t-statistic on the chunk-level paired differences).
The Wave 195/204 fix is applied at the p-value computation step
(``2 * stats.t.sf(abs(t), df)`` instead of ``2 * (1 - stats.t.cdf(...))``).

For the 2D cells (R4, R5), wave189 per-seed raw CSV data is paired at the
round level (3 seeds × 4 framework rounds 1-4 = 12 paired observations per
cell, pairing baseline[seed, round 0] vs framework[seed, round r]).

Output: 4-row CSV + JSON audit at ``verification_outputs/wave206-p4-*.{csv,json}``.

Constraint: CPU-only, numpy + scipy.stats only (no torch).
"""
from __future__ import annotations

import csv
import json
import math
import sys
import warnings
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from scipy import stats

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
OUT_DIR: Path = REPO_ROOT / "verification_outputs"

#: Per-cell alpha (Bonferroni across N=4 cells in this refresh).
ALPHA_BONF: float = 0.05 / 4

# Ensure REPO_ROOT is on sys.path so adaptive_reflow can be imported
# (the script can be invoked as `python tools/wave206_p4_r_level_refresh.py`
# from any cwd, so we always bootstrap the path here).
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _paired_stats_sf(baseline: np.ndarray, framework: np.ndarray) -> dict[str, float]:
    """Paired t-test summary stats; p-value uses stats.t.sf (Wave 195/204 fix)."""
    diff = framework - baseline
    n_pairs = len(diff)
    if n_pairs < 2:
        raise ValueError("need at least 2 paired observations")
    delta = float(diff.mean())
    sd_diff = float(diff.std(ddof=1))
    delta_se = sd_diff / math.sqrt(n_pairs)
    t_stat = delta / delta_se
    df = n_pairs - 1
    # Wave 195/204 fix: use stats.t.sf() instead of (1 - stats.t.cdf()) to retain
    # precision at extreme t-stat magnitudes (underflow-safe down to p ~ 1e-300).
    p_sf = float(2.0 * stats.t.sf(abs(t_stat), df=df))
    p_buggy = float(2.0 * (1.0 - stats.t.cdf(abs(t_stat), df=df)))
    cohens_d_z = float(delta / sd_diff) if sd_diff > 0.0 else float("nan")
    return {
        "n_pairs": n_pairs,
        "baseline_mean": float(np.mean(baseline)),
        "framework_mean": float(np.mean(framework)),
        "mean_diff": delta,
        "sd_diff": sd_diff,
        "delta_se": delta_se,
        "t_stat": t_stat,
        "df": df,
        "p_value_sf": p_sf,
        "p_value_buggy_1_minus_cdf": p_buggy,
        "cohens_d_z": cohens_d_z,
    }


def _ci95(delta: float, se: float) -> tuple[float, float]:
    if not math.isfinite(se) or se <= 0.0:
        return (float("nan"), float("nan"))
    return (delta - 1.959963984540054 * se, delta + 1.959963984540054 * se)


def _verdict_framework_wins(mean_diff: float, p: float, alpha: float, higher_better: bool) -> str:
    """Verdict assuming framework-wins == signed_delta > 0."""
    signed_delta = mean_diff if higher_better else -mean_diff
    if not math.isfinite(p):
        return "undefined"
    if p < alpha and signed_delta > 0:
        return "framework_wins_d_z"
    if p < alpha and signed_delta < 0:
        return "framework_loses_d_z"
    return "not_significant"


# ---------------------------------------------------------------------------
# 2D RF data (R4 two_moons + R5 eight_gaussians): paired t from wave189
# ---------------------------------------------------------------------------


def _load_2d_paired(target: str) -> tuple[np.ndarray, np.ndarray, str]:
    """Wave189 N=1000 2D paired W2: baseline seed round 0 vs framework seed rounds 1-4.

    Wave 189 stores ``{target}_baseline_seed{i}.csv`` (1 round per seed,
    round 0 only) and ``{target}_PaperRatioAdaptiveScheduler_seed{i}.csv``
    (5 rounds per seed, rounds 0-4).  Round 0 of framework ==
    round 0 of baseline (1-pass run), so we pair baseline[seed, round 0]
    with framework[seed, rounds 1-4] (12 paired obs per cell = 3 seeds × 4
    round pairings).
    """
    src_dir = REPO_ROOT / "verification_outputs" / "wave189-p2-sota-2d-rerun"
    base_chunks = []
    fwk_chunks = []
    for seed in (0, 1, 2):
        base_csv = src_dir / f"{target}_baseline_seed{seed}.csv"
        fwk_csv = src_dir / f"{target}_PaperRatioAdaptiveScheduler_seed{seed}.csv"
        base_w2 = np.atleast_1d(np.loadtxt(base_csv, delimiter=",", skiprows=1, usecols=1))
        fwk_w2 = np.atleast_1d(np.loadtxt(fwk_csv, delimiter=",", skiprows=1, usecols=1))
        if base_w2.size < 1 or fwk_w2.size < 2:
            raise ValueError(f"insufficient data for seed={seed}")
        b = np.full(fwk_w2.size - 1, base_w2[0])
        f = fwk_w2[1:]  # type: ignore[index]
        base_chunks.append(b)
        fwk_chunks.append(f)
    base = np.concatenate(base_chunks)
    fwk = np.concatenate(fwk_chunks)
    source = (
        "verification_outputs/wave189-p2-sota-2d-rerun/"
        f"{{{target}_baseline_seed[012],{target}_PaperRatioAdaptiveScheduler_seed[012]}}.csv "
        "(pairing: baseline[seed,round 0] vs framework[seed,rounds 1-4])"
    )
    return base, fwk, source


def _row_2d(cell: str, target: str, model: str, source_note: str) -> dict[str, object]:
    base, fwk, source = _load_2d_paired(target)
    s = _paired_stats_sf(base, fwk)
    ci_lo, ci_hi = _ci95(s["mean_diff"], s["delta_se"])
    verdict = _verdict_framework_wins(s["mean_diff"], s["p_value_sf"], ALPHA_BONF, higher_better=False)
    p_bonf = min(s["p_value_sf"] * 4, 1.0)
    return {
        "cell": cell,
        "wave": "206 P4",
        "model": model,
        "metric": "W2",
        "n_pairs": s["n_pairs"],
        "n_total_per_arm": 1000,
        "baseline_mean": s["baseline_mean"],
        "framework_mean": s["framework_mean"],
        "mean_diff": s["mean_diff"],
        "sd_diff": s["sd_diff"],
        "delta_se": s["delta_se"],
        "t_stat": s["t_stat"],
        "df": s["df"],
        "ci_95_lower": ci_lo,
        "ci_95_upper": ci_hi,
        "p_value_sf": min(s["p_value_sf"], 1.0),
        "p_value_buggy_1_minus_cdf": min(s["p_value_buggy_1_minus_cdf"], 1.0),
        "p_value_bonferroni": p_bonf,
        "cohens_d_z": s["cohens_d_z"],
        "test_type": "paired_t_sf_per_wave204_p1",
        "alpha_bonf": ALPHA_BONF,
        "alpha_bonf_family_n": 4,
        "verdict": verdict,
        "source": source,
        "honest_disclosure": source_note,
    }


# ---------------------------------------------------------------------------
# Chunk-FID cells (R3 CIFAR-10 + R5c MNIST): use pre-computed t-stats from JSON
# ---------------------------------------------------------------------------


def _row_chunk_fid_from_t(
    cell: str,
    model: str,
    baseline_fid: float,
    framework_fid: float,
    framework_arm: str,
    t_stat: float,
    df: int,
    source: str,
    chunk_fids_baseline: list[float],
    chunk_fids_framework: list[float],
    disclosure: str,
) -> dict[str, object]:
    """Build a row from pre-computed chunk_fids + t-stat; recompute p with sf.

    The pre-computed t_stat from ``wave191-p{2,3}-*-n1000.json`` came from
    the buggy ``2 * (1 - stats.t.cdf(...))`` formula but is mathematically
    correct (t-stat depends only on diff mean and std, not on the
    p-value computation function).  The Wave 195/204 fix is applied only
    at the p-value step (use stats.t.sf).
    """
    p_sf = float(2.0 * stats.t.sf(abs(t_stat), df=df))
    p_buggy = float(2.0 * (1.0 - stats.t.cdf(abs(t_stat), df=df)))
    base_chunk = np.asarray(chunk_fids_baseline, dtype=np.float64)
    fwk_chunk = np.asarray(chunk_fids_framework, dtype=np.float64)
    diff = fwk_chunk - base_chunk
    sd_diff = float(diff.std(ddof=1))
    delta_se = sd_diff / math.sqrt(len(diff))
    delta = float(diff.mean())
    cohens_d_z = delta / sd_diff if sd_diff > 0.0 else float("nan")
    ci_lo, ci_hi = _ci95(delta, delta_se)
    verdict = _verdict_framework_wins(delta, p_sf, ALPHA_BONF, higher_better=False)
    p_bonf = min(p_sf * 4, 1.0)
    return {
        "cell": cell,
        "wave": "206 P4",
        "model": model,
        "metric": "FID_chunk_level",
        "n_pairs": int(df + 1),
        "n_total_per_arm": 1000,
        "n_chunks": int(df + 1),
        "chunk_size": 100,
        "framework_arm": framework_arm,
        "baseline_fid": baseline_fid,
        "framework_fid": framework_fid,
        "baseline_mean_chunk_fid": float(base_chunk.mean()),
        "framework_mean_chunk_fid": float(fwk_chunk.mean()),
        "mean_diff_chunk_fid": delta,
        "sd_diff_chunk_fid": sd_diff,
        "delta_se_chunk_fid": delta_se,
        "t_stat": float(t_stat),
        "df": int(df),
        "ci_95_lower_chunk_fid": ci_lo,
        "ci_95_upper_chunk_fid": ci_hi,
        "p_value_sf": min(p_sf, 1.0),
        "p_value_buggy_1_minus_cdf": min(p_buggy, 1.0),
        "p_value_bonferroni": p_bonf,
        "cohens_d_z": float(cohens_d_z),
        "test_type": "paired_t_sf_per_wave204_p1_chunk_level_fid",
        "alpha_bonf": ALPHA_BONF,
        "alpha_bonf_family_n": 4,
        "verdict": verdict,
        "source": source,
        "honest_disclosure": disclosure,
        "chunk_fids_baseline": [float(x) for x in base_chunk],
        "chunk_fids_framework": [float(x) for x in fwk_chunk],
    }


# ---------------------------------------------------------------------------
# MNIST chunk_fids reconstruction (R5c)
# ---------------------------------------------------------------------------


def _reconstruct_mnist_chunk_fids() -> dict[str, list[float]]:
    """Reproduce the Wave 191 P3 chunk-level FIDs for all 4 arms (incl. baseline).

    Protocol (matches scripts/wave191_p3_mnist_sweep.py):
      - random projection 784 → 128 (seed=42)
      - reference = MNIST test set (10K digits)
      - chunk_size = 100, k_chunks = 10
      - reference chunks: random permutation (seed = 42 + 99) split into 10
      - FID = _frechet_distance(baseline_chunk, ref_chunk)
    """
    cache_dir = Path("/tmp/mnist_test_cache_p4")
    cache_dir.mkdir(parents=True, exist_ok=True)
    from adaptive_reflow.adapters.mnist_fm_train import _load_mnist_offline
    from adaptive_reflow.eval.mnist_fid import (
        MnistFrechetProjectionEvaluator,
        _frechet_distance,
    )

    mnist_test = _load_mnist_offline(split="test", cache_dir=cache_dir)  # (10000, 784)
    # Use the canonical MnistFrechetProjectionEvaluator to byte-match the original
    # Wave 191 P3 reference features and projection matrix (seed=42, dim=128).
    evaluator = MnistFrechetProjectionEvaluator(cache_dir=cache_dir)
    ref_features = evaluator._ref_features  # (10000, 128) — already projected
    proj = evaluator._projection  # (784, 128)

    arms_samples = {
        "baseline": np.load(REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000" / "baseline_samples.npz")["samples"],
        "cosine": np.load(REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000" / "cosine_samples.npz")["samples"],
        "codimension_sheet": np.load(REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000" / "codimension_sheet_samples.npz")["samples"],
        "evidence_driven": np.load(REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000" / "evidence_driven_samples.npz")["samples"],
    }

    chunk_size = 100
    k_chunks = 10
    ref_chunk_size = chunk_size
    ref_perm = np.random.default_rng(42 + 99).permutation(ref_features.shape[0])
    chunk_fids: dict[str, list[float]] = {k: [] for k in arms_samples}
    for k_i in range(k_chunks):
        ref_idx = ref_perm[k_i * ref_chunk_size:(k_i + 1) * ref_chunk_size]
        ref_chunk = ref_features[ref_idx]
        for name, samples in arms_samples.items():
            feats_g = samples[k_i * chunk_size:(k_i + 1) * chunk_size] @ proj
            chunk_fids[name].append(_frechet_distance(feats_g, ref_chunk))
    return chunk_fids


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True, parents=True)
    csv_path = OUT_DIR / "wave206-p4-r-level-refresh.csv"
    json_path = OUT_DIR / "wave206-p4-r-level-refresh.json"

    rows: list[dict[str, object]] = []

    # ---------------- R4 / R5: 2D RF (paired-t from wave189 per-seed rounds) ----------------
    r4_disclosure = (
        "Wave 189 P2 N=1000 single-seed-per-pair data (3 seeds × 4 framework rounds 1-4 = 12 paired obs per cell). "
        "Per-seed per-round pairing: baseline[seed, round 0] vs framework[seed, round r∈{1,2,3,4}].  "
        "Canonical R4/R5 numbers (baseline=0.5029→framework=0.4663 for two_moons; baseline=0.6606→framework=0.5919 for "
        "eight_gaussians; 3 seeds × 5 schedulers × 20 rounds × 1000 samples/round from "
        "docs/r4-survey/10-sota-2d-experiment-results.md) are NOT refreshed here because per-round raw CSV files from "
        "the canonical experiment are not preserved in the repository; "
        "reproducibility_record.md §R3 documents the W2 magnitude divergence since Wave 15 F.2 "
        "(baseline W2 ~0.07 here vs 0.5029 in canonical doc; framework W2 ~0.07 here vs 0.4663) — "
        "the qualitative direction (framework WINS, lower W2) holds in canonical but is NOT "
        "reproduced by the wave189 N=1000 sweep (framework marginally worse on this stale data)."
    )
    r5_disclosure = (
        "Same protocol as R4 (12 paired obs per cell from wave189).  Wave 189 P2 numbers are byte-stable but "
        "reflect a fresh re-run under the post-cd70821 adapter; the canonical R5 numbers (0.6606→0.5919, -10.40%) come from "
        "docs/r4-survey/10-sota-2d-experiment-results.md using CosineAnnealScheduler with matched NFE=500 and are NOT "
        "re-collected here.  Qualitative direction (framework wins lower W2) is documented in the canonical doc."
    )
    rows.append(_row_2d("R4_two_moons_W2", "two_moons", "twodim_fm", r4_disclosure))
    rows.append(_row_2d("R5_eight_gaussians_W2", "eight_gaussians", "twodim_fm", r5_disclosure))

    # ---------------- R3: CIFAR-10 RF (chunk FID paired-t; t-stat from wave191 p2 JSON) ----------------
    cifar_json = json.loads(
        (REPO_ROOT / "verification_outputs" / "wave191-p2-cifar10-n1000.json").read_text()
    )
    cifar_cosine = cifar_json["framework_arms"]["cosine"]
    cifar_baseline_fid = cifar_json["baseline_fid"]
    cifar_cosine_fid = cifar_cosine["fid_headline"]
    cifar_baseline_chunk_fids = [cifar_baseline_fid] * int(cifar_cosine["n_chunks"])
    cifar_cosine_chunk_fids = cifar_cosine["chunk_fids"]
    cifar_t_stat = float(cifar_cosine["t_stat"])
    cifar_df = int(cifar_cosine["df"])

    cifar_disclosure = (
        "Wave 191 P2 N=1000 chunk-level paired t-test (k=10, df=9).  The chunk_fids array is reused from "
        "the existing JSON; only the p-value computation is refreshed to use stats.t.sf() (Wave 195/204 fix).  "
        "Verified: |t_stat|=9.30 at df=9 is well below the sf/1-cdf underflow threshold (~|t|>180), so the "
        "sf-based p (6.546e-06) and the previously reported p agree to 5+ significant figures.  The cosine "
        "arm is framework-WORSE at matched NFE=50 (FID=500.20 vs baseline=415.83, +20.21% — honest negative)."
    )
    rows.append(_row_chunk_fid_from_t(
        cell="R3_cifar10_rf_FID",
        model="cifar10_rf",
        baseline_fid=cifar_baseline_fid,
        framework_fid=cifar_cosine_fid,
        framework_arm="cosine",
        t_stat=cifar_t_stat,
        df=cifar_df,
        source=(
            "verification_outputs/wave191-p2-cifar10-n1000.json#framework_arms.cosine "
            "(chunk_fids + t_stat from JSON; p recomputed via stats.t.sf per Wave 195 P2 / Wave 204 P1)"
        ),
        chunk_fids_baseline=cifar_baseline_chunk_fids,
        chunk_fids_framework=cifar_cosine_chunk_fids,
        disclosure=cifar_disclosure,
    ))

    # ---------------- R5c: MNIST FM (reconstruct chunk_fids then recompute paired-t) ----------------
    print("Reconstructing MNIST chunk_fids (R5c evidence_driven vs baseline)...")
    mnist_chunk_fids = _reconstruct_mnist_chunk_fids()
    base_chunk = np.asarray(mnist_chunk_fids["baseline"], dtype=np.float64)
    ed_chunk = np.asarray(mnist_chunk_fids["evidence_driven"], dtype=np.float64)
    s = _paired_stats_sf(base_chunk, ed_chunk)
    mnist_baseline_fid = cifar_json_baseline_fid = json.loads(
        (REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000.json").read_text()
    )["baseline_fid"]
    ed_fid = json.loads(
        (REPO_ROOT / "verification_outputs" / "wave191-p3-mnist-n1000.json").read_text()
    )["framework_arms"]["evidence_driven"]["fid_headline"]
    mnist_disclosure = (
        "Wave 191 P3 N=1000 chunk-level paired t-test (k=10, df=9) for evidence_driven vs baseline, with both "
        "baseline and framework chunk_fids reconstructed from the saved samples + MNIST test set "
        "(random projection 784→128, seed=42; ref perm seed=141).  Pre-existing t_stat=-41.66 reported in the "
        "Wave 191 P3 JSON was computed via the buggy ``2*(1-cdf)`` form; the Wave 195 P2 / Wave 204 P1 sf fix is "
        "applied here.  At |t|=41.66, df=9 the sf-vs-1-cdf difference is < 1e-15 — the p-value numerical floor "
        "is essentially the same — but the formula now uses the defensive sf() path so an extreme-t future "
        "result (|t|>180) won't truncate to 0 due to 1-cdf underflow."
    )
    rows.append(_row_chunk_fid_from_t(
        cell="R5c_mnist_fm_FID",
        model="mnist_fm",
        baseline_fid=mnist_baseline_fid,
        framework_fid=ed_fid,
        framework_arm="evidence_driven",
        t_stat=s["t_stat"],
        df=s["df"],
        source=(
            "verification_outputs/wave191-p3-mnist-n1000/{baseline,evidence_driven}_samples.npz "
            "+ MNIST test set via adaptive_reflow.adapters.mnist_fm_train._load_mnist_offline "
            "(chunk_fids reconstructed from samples; paired-t recomputed end-to-end with stats.t.sf)"
        ),
        chunk_fids_baseline=mnist_chunk_fids["baseline"],
        chunk_fids_framework=mnist_chunk_fids["evidence_driven"],
        disclosure=mnist_disclosure,
    ))

    # -------------------------------------------------------------------
    # Output CSV and JSON
    # -------------------------------------------------------------------
    csv_columns = [
        "cell", "wave", "model", "metric", "n_pairs", "n_total_per_arm",
        "framework_arm", "baseline_mean", "framework_mean", "mean_diff",
        "sd_diff", "delta_se", "t_stat", "df", "ci_95_lower", "ci_95_upper",
        "p_value_sf", "p_value_buggy_1_minus_cdf", "p_value_bonferroni",
        "cohens_d_z", "test_type", "alpha_bonf", "verdict", "source",
    ]
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=csv_columns, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            # Use _fid suffix variants for FID cells
            if "FID_chunk_level" in str(row.get("metric")):
                row["framework_arm"] = row.get("framework_arm", "framework_arm")
                row["baseline_mean"] = row.get("baseline_mean_chunk_fid")
                row["framework_mean"] = row.get("framework_mean_chunk_fid")
                row["mean_diff"] = row.get("mean_diff_chunk_fid")
                row["sd_diff"] = row.get("sd_diff_chunk_fid")
                row["delta_se"] = row.get("delta_se_chunk_fid")
                row["ci_95_lower"] = row.get("ci_95_lower_chunk_fid")
                row["ci_95_upper"] = row.get("ci_95_upper_chunk_fid")
            w.writerow(row)

    json_payload = {
        "wave": "206 P4",
        "schema_version": "wave206_p4_r_level_refresh_v1",
        "constraint": "CPU-only; numpy + scipy.stats only; no torch",
        "fix_applied": "2 * stats.t.sf(abs(t), df) per Wave 195 P2 (defensive, Wave 204 P1 commit 72ba46e)",
        "n_cells": len(rows),
        "alpha_family": 0.05,
        "alpha_per_cell_bonferroni": ALPHA_BONF,
        "rows": rows,
    }
    with open(json_path, "w") as fh:
        json.dump(json_payload, fh, indent=2, allow_nan=True)

    # Console summary
    print(f"\nWrote {csv_path}")
    print(f"Wrote {json_path}\n")
    for row in rows:
        b_mean = row.get("baseline_mean", row.get("baseline_fid"))
        f_mean = row.get("framework_mean", row.get("framework_fid"))
        m_diff = row.get("mean_diff", row.get("mean_diff_chunk_fid"))
        print(
            f"  {row['cell']:32s} n_pairs={row['n_pairs']:>4d} "
            f"baseline={b_mean:.4f} framework={f_mean:.4f} "
            f"Δ={m_diff:+.4f} t={row['t_stat']:+.3f} df={row['df']} "
            f"p_sf={row['p_value_sf']:.3e} d_z={row['cohens_d_z']:+.4f} "
            f"verdict={row['verdict']}"
        )


if __name__ == "__main__":
    main()

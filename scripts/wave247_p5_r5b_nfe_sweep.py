#!/usr/bin/env python3
"""Wave 247 P5: R5b CIFAR-10 RF n_rounds=1 NFE budget sweep (50/100/200).

Per Wave 247 P4 tier-aware audit conclusion, the n_rounds=1 framework-WINS
headline for R5b CIFAR-10 RF is structurally uniform across tiers — the
uniform arm (ef=1.0, hi=1.0) is optimal. The user's earlier concern
(parameterization-selective: n_rounds=1 WIN, n_rounds>1 conditional boundary)
motivates this P5 NFE sweep: at n_rounds=1, does the framework-WIN hold at
matched-NFE = 50 (the established baseline) AND extend to NFE = 100, 200?

Goal (per Wave 247 P5 brief)
----------------------------
For each NFE ∈ {50, 100, 200} (with --n-rounds=1 --n-samples=200 --seed=42):
  * Run the canonical `tools/run_sota_cifar_experiment.py` matched-NFE sweep
    (baseline + 4 schedulers).
  * Record per-scheduler FID + delta_FID_pct + d_z.
  * Save per-NFE CSV (machine-readable) and an aggregate CSV (3-NFE × 4-scheduler
    table).

Conclusion: WIN extends to higher NFE if all 4 schedulers maintain d_z < 0
at NFE > 50; otherwise show at which NFE the WIN collapses.

Constraints (per Wave 247 P5 hard rules)
----------------------------------------
  * DO NOT modify framework source code.
  * DO NOT touch Wave 242 GPU task.
  * DO preserve D.4 30/30 PASS.
  * DO preserve mkdocs 0 warnings.

Outputs
-------
  verification_outputs/wave247-p5-r5b-nfe{N}.csv              per-NFE per-scheduler
  verification_outputs/wave247-p5-r5b-nfe{N}.json             per-NFE machine-readable
  verification_outputs/wave247-p5-r5b-nfe-sweep-aggregate.csv 3-NFE × 4 scheduler
  verification_outputs/wave247-p5-r5b-nfe-sweep-aggregate.json
  docs/audit/wave247-p5-r5b-nfe-sweep.md
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
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
RUNNER = REPO / "tools" / "run_sota_cifar_experiment.py"

LOG_PATH = Path("/tmp/w247-p5-nfe-sweep.log")

# Sweep grid.
NFE_VALUES = [50, 100, 200]

# Sweep per-NFE settings.
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

# D.4 byte-stable regression vector gate (CRITICAL — Wave 125 Phase 2).
D4_TEST_PATH = "tests/test_d4_regression_vectors.py"
D4_TESTS_EXPECTED = 30

# Maximum wall-clock per NFE budget (seconds). Empirically the N=200 n_rounds=1
# sweep took ~7 min for baseline + 4 arms at NFE=50 on PRO 6000. Higher NFE
# takes proportionally longer for the framework rows (which integrate per round).
# We use a 30 min/NFE budget as the brief specifies.
NFE_BUDGET_SECONDS = 30 * 60


def _run_d4_test() -> dict:
    """Run D.4 byte-stable regression vector gate (CRITICAL)."""
    print("\n" + "=" * 72)
    print("D.4 byte-stable regression vector gate (CRITICAL)")
    print("=" * 72)
    # Use the lineageflow venv that other wave scripts use for D.4.
    lineage_python = REPO / ".venvs" / "lineageflow_venv" / "bin" / "python"
    if not lineage_python.exists():
        lineage_python = PYTHON_BIN
    cmd = [
        str(lineage_python),
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


def _wait_for_p3_to_complete(grace_seconds: float = 60.0) -> None:
    """Gracefully delay to avoid races with any in-progress runner invocation
    on the same machine.

    The runner file patch is idempotent (detects prior WAVE247_P*_SEED patch
    and skips), so we do not need to BLOCK on P3. We just need a short
    grace window to avoid an unfortunate interleaving of file writes if
    P3 is racing to restore the original runner text at exit. After
    `grace_seconds`, we proceed regardless.
    """
    print(f"[w247-p5] grace window of {grace_seconds:.0f}s before launching "
          f"(avoid races with concurrent runner invocations) ...", flush=True)
    try:
        out = subprocess.run(
            ["pgrep", "-af", "run_sota_cifar_experiment.py"],
            capture_output=True, text=True, check=False,
        ).stdout
        if out.strip():
            print(f"[w247-p5]   detected: {out.strip().splitlines()[0]}",
                  flush=True)
    except Exception:
        pass
    time.sleep(grace_seconds)


def _patch_runner_seed() -> tuple[str, str]:
    """Patch the runner's two hardcoded seed=0 / seed_base=0 call sites
    so the per-sample RNG uses our SEED.

    Reuses the Wave 247 P3 `WAVE247_P3_SEED` env var convention so that:
      * If the runner file already has WAVE247_P3_SEED patched in (left
        over from a prior Wave 247 P3 run, which is the common case), we
        skip the patch — the subprocess env then sets WAVE247_P3_SEED
        and the runner reads it.
      * If the runner is currently unpatched, this function applies the
        same `WAVE247_P3_SEED` patch (idempotent against prior P3 runs).

    Returns (original_text, patched_text). The restore function writes
    ``original_text`` back at exit (no-op when patched_text == original).
    """
    ENV_VAR = "WAVE247_P3_SEED"  # use P3's env var (already known-good)
    original = RUNNER.read_text()

    # If the file is already patched (any WAVE247_*_SEED env var in place),
    # nothing to do — the runner will read our env var as-is.
    if (f"os.environ.get({ENV_VAR!r}" in original
            or "WAVE247" in original and "SEED" in original):
        # Already patched. Return (original, original) so restore is a no-op.
        return original, original

    patched = original.replace(
        "        seed=0,\n        output_dir=output_dir,\n    )\n    print(\n        f\"[run_sota_cifar_experiment] baseline: {baseline_path} \"",
        f"        seed=int(os.environ.get({ENV_VAR!r}, '0')),\n        output_dir=output_dir,\n    )\n    print(\n        f\"[run_sota_cifar_experiment] baseline: {baseline_path} \"",
    )
    patched = patched.replace(
        "            seed_base=0,\n            output_dir=output_dir,",
        f"            seed_base=int(os.environ.get({ENV_VAR!r}, '0')),\n            output_dir=output_dir,",
    )
    if patched == original:
        raise RuntimeError(
            "Patches did not apply — runner text changed (P3/P4 patch may "
            "be in a different shape than expected)."
        )
    RUNNER.write_text(patched)
    return original, patched


def _restore_runner(original_text: str) -> None:
    if original_text != RUNNER.read_text():
        RUNNER.write_text(original_text)


def _inception_features(samples: np.ndarray, batch_size: int = 32) -> np.ndarray:
    """Compute 2048-d InceptionV3 (TF-port via pytorch_fid) features.

    Mirrors the runner's inline path so that per-sample features can be
    paired for d_z computation.
    """
    import torch
    from pytorch_fid.inception import InceptionV3

    block_idx = InceptionV3.BLOCK_INDEX_BY_DIM[2048]
    model = InceptionV3([block_idx])
    model.eval()
    n = int(samples.shape[0])
    out = np.empty((n, 2048), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, n, batch_size):
            batch = torch.from_numpy(
                np.asarray(samples[i : i + batch_size], dtype=np.float32)
            )
            x = (batch + 1.0) / 2.0  # [-1,1] -> [0,1] for TF-port inception
            pred = model(x)[0].squeeze(3).squeeze(2)
            out[i : i + int(batch.shape[0])] = pred.cpu().numpy()
    return out


def _load_or_compute_features(cache_dir: Path, arm_name: str, npz_path: Path) -> np.ndarray | None:
    """Load cached inception features or compute + cache them."""
    cache_path = cache_dir / f"{arm_name}.npy"
    if cache_path.exists():
        return np.load(cache_path).astype(np.float64)
    if not npz_path.exists():
        return None
    samples = np.load(npz_path)["samples"].astype(np.float64)
    print(f"[w247-p5] computing inception features for {arm_name} (n={samples.shape[0]})...",
          flush=True)
    t0 = time.perf_counter()
    feats = _inception_features(samples)
    print(f"[w247-p5]   inception features for {arm_name} in {time.perf_counter() - t0:.1f}s",
          flush=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, feats)
    return feats


def _fid_from_features(a: np.ndarray, b: np.ndarray) -> float:
    """Closed-form FID (Fréchet distance between two Gaussians)."""
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


def _run_runner_for_nfe(nfe: int) -> dict:
    """Run the matched-NFE sweep at the given NFE. Returns timing info."""
    run_dir = OUT_DIR / f"wave247-p5-r5b-nfe{nfe}-n1"
    run_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(PYTHON_BIN),
        "tools/run_sota_cifar_experiment.py",
        "--checkpoint", "data/rectified_flow_cifar10.pth",
        "--device", "cuda",
        "--n-samples", str(N_SAMPLES),
        "--framework-samples", str(N_SAMPLES),
        "--n-rounds", str(N_ROUNDS),
        "--baseline-num-steps", str(nfe),
        "--framework-max-num-steps", str(nfe),
        "--integrator", "euler",
        "--match-nfe", "budget",
        "--ref-npz", "data/cifar10_test_ref.npz",
        "--output-dir", str(run_dir.relative_to(REPO)),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    env["WAVE247_P3_SEED"] = str(SEED)  # reuse P3's known-good env var
    env["CUDA_VISIBLE_DEVICES"] = "0"
    print(f"[w247-p5] launching runner for NFE={nfe}: {' '.join(cmd)}", flush=True)
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd, cwd=str(REPO), env=env,
        capture_output=True, text=True, timeout=NFE_BUDGET_SECONDS,
    )
    # Always append stdout/stderr to the sweep log so we can tail progress.
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as log_f:
        log_f.write(f"\n\n==== NFE={nfe} ====\n")
        log_f.write("STDOUT:\n")
        log_f.write(proc.stdout)
        log_f.write("\n\nSTDERR:\n")
        log_f.write(proc.stderr)
    wall = time.perf_counter() - t0
    print(f"[w247-p5] runner for NFE={nfe} done in {wall:.1f}s, rc={proc.returncode}",
          flush=True)
    if proc.returncode != 0:
        print(f"[w247-p5] STDERR tail:\n{proc.stderr[-3000:]}", flush=True)
        raise RuntimeError(f"runner for NFE={nfe} exited rc={proc.returncode}")
    return {
        "wall_seconds": wall,
        "returncode": proc.returncode,
        "run_dir": str(run_dir.relative_to(REPO)),
    }


def _evaluate_nfe(nfe: int) -> dict:
    """Compute per-scheduler FID + delta_FID_pct + d_z from the runner samples.

    Mirrors the Wave 247 P3 _evaluate() methodology.
    """
    run_dir = OUT_DIR / f"wave247-p5-r5b-nfe{nfe}-n1"
    cache_dir = run_dir / "inception_feats_cache"
    ref_feats = np.load(
        REPO / "data" / "cifar10_inception_features.npz",
        allow_pickle=False,
    )["features"].astype(np.float64)
    print(f"[w247-p5] NFE={nfe} ref features shape={ref_feats.shape}", flush=True)

    feats: dict[str, np.ndarray] = {}
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


def _emit_per_nfe_csv(eval_data: dict, out_csv: Path) -> None:
    bonf_alpha = 0.05 / 4
    with out_csv.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "nfe", "config", "n_rounds", "scheduler",
            "fid_headline", "delta_pct", "cohens_d_z", "n_paired",
            "mean_diff", "sd_diff", "t_statistic", "df", "p_value_raw",
            "CI95_low", "CI95_high", "alpha_bonferroni", "bonf_sig",
            "baseline_fid",
        ])
        baseline_fid = eval_data["baseline_fid"]
        nfe = eval_data["nfe"]
        for sch in SCHEDULER_ARMS:
            arm = eval_data["framework_arms"][sch]
            mean_diff = arm["per_sample_l2_sq_distance_mean"]
            sd_diff = arm["per_sample_l2_sq_distance_std"]
            n_paired = arm["n_paired"]
            t_stat = arm["t_statistic"]
            p_val = arm["p_value_raw"]
            bonf_p = float(min(p_val * 4, 1.0)) if not math.isnan(p_val) else float("nan")
            bonf_sig = bool(bonf_p < 0.05) if not math.isnan(bonf_p) else False
            w.writerow([
                nfe, f"nfe{nfe}_n{N_SAMPLES}_seed{SEED}", N_ROUNDS, sch,
                arm["fid_headline"], arm["delta_vs_baseline_pct"], arm["cohens_d_z"],
                n_paired, mean_diff, sd_diff, t_stat, arm["df"], p_val,
                arm["CI95_low"], arm["CI95_high"], bonf_alpha, bonf_sig,
                baseline_fid,
            ])


def main() -> int:
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--skip-run", action="store_true",
                        help="skip the runner sweep (use cached samples)")
    parser.add_argument("--d4-only", action="store_true",
                        help="run only the D.4 gate (no runner invocations)")
    args = parser.parse_args()

    print(f"=== Wave 247 P5 — R5b CIFAR-10 RF n_rounds=1 NFE sweep ===", flush=True)
    print(f"[w247-p5] NFE_VALUES={NFE_VALUES}  n_samples={N_SAMPLES}  "
          f"n_rounds={N_ROUNDS}  seed={SEED}", flush=True)

    # Initialize the sweep log (overwrite at each fresh launch).
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(f"=== Wave 247 P5 NFE sweep @ {datetime.now(UTC).isoformat()} ===\n")

    if args.d4_only:
        d4 = _run_d4_test()
        print(json.dumps({"d4_byte_stable_gate": d4}, indent=2))
        return 0 if d4["d4_pass"] else 1

    # Make sure no other runner is in flight on this machine.
    # Soft guard: P3 may be running on the same GPU; we add a 60s grace
    # window to avoid simultaneous patch/restore races on the runner file,
    # but otherwise proceed (the runner file patch is idempotent against
    # a prior WAVE247_P*_SEED patch).
    _wait_for_p3_to_complete(grace_seconds=60.0)

    # Patch the runner to read WAVE247_P5_SEED from env. Restore on exit.
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    per_nfe_results: dict[int, dict] = {}
    runner_status: dict[int, dict] = {}

    if not args.skip_run:
        original, _patched = _patch_runner_seed()
        try:
            for nfe in NFE_VALUES:
                print(f"\n[w247-p5] === NFE={nfe} ===", flush=True)
                runner_status[nfe] = _run_runner_for_nfe(nfe)
                per_nfe_results[nfe] = _evaluate_nfe(nfe)
        finally:
            _restore_runner(original)
    else:
        for nfe in NFE_VALUES:
            per_nfe_results[nfe] = _evaluate_nfe(nfe)

    # Write per-NFE outputs.
    for nfe in NFE_VALUES:
        eval_data = per_nfe_results[nfe]
        out_csv = OUT_DIR / f"wave247-p5-r5b-nfe{nfe}.csv"
        _emit_per_nfe_csv(eval_data, out_csv)
        out_json = OUT_DIR / f"wave247-p5-r5b-nfe{nfe}.json"
        out_json.write_text(json.dumps({
            "schema": "wave247_p5_r5b_nfe_v1",
            "wave": "Wave 247 P5",
            "task": f"R5b CIFAR-10 RF n_rounds=1 NFE={nfe} replication",
            "evaluation": eval_data,
            "runner_status": runner_status.get(nfe, {"skipped": True}),
            "verdict_per_scheduler": {
                sch: ("framework_WINS"
                      if eval_data["framework_arms"][sch]["delta_vs_baseline_pct"] < 0
                      else "REGRESSES"
                      if eval_data["framework_arms"][sch]["delta_vs_baseline_pct"] > 0
                      else "TIE")
                for sch in SCHEDULER_ARMS
            },
        }, indent=2, default=str) + "\n")
        print(f"[w247-p5] wrote {out_csv.relative_to(REPO)} and {out_json.relative_to(REPO)}",
              flush=True)

    # ----- Aggregate 3-NFE × 4-scheduler table -----
    aggregate_csv = OUT_DIR / "wave247-p5-r5b-nfe-sweep-aggregate.csv"
    with aggregate_csv.open("w", newline="") as f_:
        w = csv.writer(f_)
        w.writerow([
            "nfe", "scheduler", "fid_headline", "delta_pct", "cohens_d_z",
            "t_statistic", "df", "p_value_raw", "bonf_sig", "baseline_fid",
            "verdict",
        ])
        for nfe in NFE_VALUES:
            ev = per_nfe_results[nfe]
            bf = ev["baseline_fid"]
            for sch in SCHEDULER_ARMS:
                arm = ev["framework_arms"][sch]
                p_val = arm["p_value_raw"]
                bonf_p = float(min(p_val * 4, 1.0)) if not math.isnan(p_val) else float("nan")
                bonf_sig = bool(bonf_p < 0.05) if not math.isnan(bonf_p) else False
                vp = arm["delta_vs_baseline_pct"]
                verdict = ("framework_WINS" if vp < 0
                           else "REGRESSES" if vp > 0
                           else "TIE")
                w.writerow([
                    nfe, sch, arm["fid_headline"], arm["delta_vs_baseline_pct"],
                    arm["cohens_d_z"], arm["t_statistic"], arm["df"], p_val,
                    bonf_sig, bf, verdict,
                ])

    aggregate_json = OUT_DIR / "wave247-p5-r5b-nfe-sweep-aggregate.json"
    aggregate_data = {
        "schema": "wave247_p5_r5b_nfe_sweep_v1",
        "wave": "Wave 247 P5",
        "task": "R5b CIFAR-10 RF n_rounds=1 NFE budget sweep (50/100/200)",
        "nfe_values": NFE_VALUES,
        "n_samples": N_SAMPLES,
        "n_rounds": N_ROUNDS,
        "seed": SEED,
        "results": {
            str(nfe): per_nfe_results[nfe] for nfe in NFE_VALUES
        },
        "verdict_per_nfe_scheduler": {
            str(nfe): {
                sch: ("framework_WINS"
                      if per_nfe_results[nfe]["framework_arms"][sch]["delta_vs_baseline_pct"] < 0
                      else "REGRESSES"
                      if per_nfe_results[nfe]["framework_arms"][sch]["delta_vs_baseline_pct"] > 0
                      else "TIE")
                for sch in SCHEDULER_ARMS
            }
            for nfe in NFE_VALUES
        },
    }
    aggregate_json.write_text(json.dumps(aggregate_data, indent=2, default=str) + "\n")
    print(f"[w247-p5] wrote {aggregate_csv.relative_to(REPO)} and "
          f"{aggregate_json.relative_to(REPO)}", flush=True)

    # ----- Determine best NFE for WIN (per scheduler + overall) -----
    best_nfe_per_sched: dict[str, int] = {}
    best_overall_dz_per_sched: dict[str, dict[int, float]] = {sch: {} for sch in SCHEDULER_ARMS}
    best_overall_pct_per_sched: dict[str, dict[int, float]] = {sch: {} for sch in SCHEDULER_ARMS}
    best_nfe_overall = NFE_VALUES[0]
    best_overall_dz_best = float("inf")
    for nfe in NFE_VALUES:
        for sch in SCHEDULER_ARMS:
            dz = per_nfe_results[nfe]["framework_arms"][sch]["cohens_d_z"]
            pct = per_nfe_results[nfe]["framework_arms"][sch]["delta_vs_baseline_pct"]
            best_overall_dz_per_sched[sch][nfe] = dz
            best_overall_pct_per_sched[sch][nfe] = pct

    for sch in SCHEDULER_ARMS:
        # Pick the NFE with the most negative delta_pct (most negative = best WIN).
        best_nfe_per_sched[sch] = min(
            NFE_VALUES,
            key=lambda n: best_overall_pct_per_sched[sch][n],
        )
        # Track overall best.
        for nfe in NFE_VALUES:
            dz = best_overall_dz_per_sched[sch][nfe]
            if dz < best_overall_dz_best:
                best_overall_dz_best = dz
                best_nfe_overall = nfe

    # WIN extends to higher NFE iff all 4 schedulers have delta_pct < 0 at NFE > 50.
    win_at_nfe50 = all(
        per_nfe_results[50]["framework_arms"][sch]["delta_vs_baseline_pct"] < 0
        for sch in SCHEDULER_ARMS
    )
    win_at_higher_nfe = {}
    for nfe in [100, 200]:
        win_at_higher_nfe[nfe] = all(
            per_nfe_results[nfe]["framework_arms"][sch]["delta_vs_baseline_pct"] < 0
            for sch in SCHEDULER_ARMS
        )
    win_extends = bool(win_at_nfe50 and all(win_at_higher_nfe.values()))

    # Best delta_pct across all NFEs and schedulers (most negative).
    best_delta_pct = float("inf")
    for nfe in NFE_VALUES:
        for sch in SCHEDULER_ARMS:
            p = per_nfe_results[nfe]["framework_arms"][sch]["delta_vs_baseline_pct"]
            if p < best_delta_pct:
                best_delta_pct = p

    print()
    print("=" * 78)
    print("HEADLINE — Wave 247 P5 NFE sweep")
    print("=" * 78)
    for nfe in NFE_VALUES:
        ev = per_nfe_results[nfe]
        print(f"\n  NFE={nfe}  baseline FID={ev['baseline_fid']:.2f}")
        for sch in SCHEDULER_ARMS:
            a = ev["framework_arms"][sch]
            v = ("framework_WINS" if a["delta_vs_baseline_pct"] < 0
                 else "REGRESSES" if a["delta_vs_baseline_pct"] > 0
                 else "TIE")
            print(f"    {sch:30s} FID={a['fid_headline']:.2f}  "
                  f"ΔFID%={a['delta_vs_baseline_pct']:+.2f}%  "
                  f"d_z={a['cohens_d_z']:+.4f}  {v}")
    print(f"\n  Best NFE per scheduler (most negative ΔFID%):")
    for sch in SCHEDULER_ARMS:
        print(f"    {sch:30s} best NFE = {best_nfe_per_sched[sch]}")
    print(f"  Best delta_pct overall = {best_delta_pct:+.2f}%")
    print(f"  WIN at NFE=50  = {win_at_nfe50}")
    for nfe in [100, 200]:
        print(f"  WIN at NFE={nfe}  = {win_at_higher_nfe[nfe]}")
    print(f"  WIN extends to higher NFE = {win_extends}")

    # ----- D.4 gate -----
    d4 = _run_d4_test()

    # ----- Audit doc -----
    doc = DOCS_DIR / "wave247-p5-r5b-nfe-sweep.md"
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    md_lines = []
    md_lines.append("# Wave 247 P5 — R5b CIFAR-10 RF NFE budget sweep (50/100/200)\n")
    md_lines.append("**Wave:** 247 P5  ")
    md_lines.append(f"**Date:** {datetime.now(UTC).date().isoformat()}  ")
    md_lines.append("**Status:** auto-generated by `scripts/wave247_p5_r5b_nfe_sweep.py`\n")
    md_lines.append("\n## TL;DR\n")
    md_lines.append("| NFE | Best scheduler | Best ΔFID% | Best d_z | Verdict |")
    md_lines.append("|---:|---|---:|---:|---|")
    for nfe in NFE_VALUES:
        ev = per_nfe_results[nfe]
        # pick the most negative delta_pct scheduler at this NFE
        sch = min(SCHEDULER_ARMS,
                  key=lambda s: ev["framework_arms"][s]["delta_vs_baseline_pct"])
        a = ev["framework_arms"][sch]
        v = ("framework_WINS" if a["delta_vs_baseline_pct"] < 0
             else "REGRESSES" if a["delta_vs_baseline_pct"] > 0
             else "TIE")
        md_lines.append(f"| {nfe} | {sch} | {a['delta_vs_baseline_pct']:+.2f}% | "
                        f"{a['cohens_d_z']:+.4f} | {v} |")
    md_lines.append(f"\n**WIN extends to higher NFE:** {win_extends}  ")
    md_lines.append(f"**Best NFE for overall WIN:** {best_nfe_overall}  ")
    md_lines.append(f"**Best ΔFID% across all cells:** {best_delta_pct:+.2f}%  ")
    md_lines.append(f"\n## 3-NFE × 4-scheduler table\n")
    md_lines.append("| NFE | CosineAnneal | CodimensionSheet | EvidenceDriven | FreeTraj |")
    md_lines.append("|---:|---:|---:|---:|---:|")
    for nfe in NFE_VALUES:
        ev = per_nfe_results[nfe]
        cells = []
        for sch in SCHEDULER_ARMS:
            a = ev["framework_arms"][sch]
            cells.append(f"{a['delta_vs_baseline_pct']:+.2f}% (d_z={a['cohens_d_z']:+.3f})")
        md_lines.append(f"| {nfe} | " + " | ".join(cells) + " |")
    md_lines.append("\n## Best NFE per scheduler\n")
    md_lines.append("| Scheduler | Best NFE | ΔFID% at best NFE | d_z at best NFE |")
    md_lines.append("|---|---:|---:|---:|")
    for sch in SCHEDULER_ARMS:
        n = best_nfe_per_sched[sch]
        a = per_nfe_results[n]["framework_arms"][sch]
        md_lines.append(f"| {sch} | {n} | {a['delta_vs_baseline_pct']:+.2f}% | "
                        f"{a['cohens_d_z']:+.4f} |")
    md_lines.append("\n## Conclusion\n")
    if win_extends:
        md_lines.append("**WIN extends to higher NFE.** All four schedulers maintain "
                        "ΔFID% < 0 at NFE > 50.\n")
    else:
        # Show where it collapses.
        md_lines.append("**WIN does NOT extend uniformly.** Schedule:\n")
        md_lines.append("| NFE | WIN schedulers | REGRESS schedulers |")
        md_lines.append("|---:|---|---|")
        for nfe in NFE_VALUES:
            ev = per_nfe_results[nfe]
            winners = [sch for sch in SCHEDULER_ARMS
                       if ev["framework_arms"][sch]["delta_vs_baseline_pct"] < 0]
            regressers = [sch for sch in SCHEDULER_ARMS
                          if ev["framework_arms"][sch]["delta_vs_baseline_pct"] > 0]
            md_lines.append(f"| {nfe} | {', '.join(winners) or '(none)'} | "
                            f"{', '.join(regressers) or '(none)'} |")
        md_lines.append("")
    md_lines.append(f"\n## D.4 byte-stable gate\n")
    md_lines.append(f"D.4 = {d4['n_passed']}/{d4['n_total']} "
                    f"{'PASS' if d4['d4_pass'] else 'FAIL'}  ")
    md_lines.append(f"\n## Files\n")
    md_lines.append("* `scripts/wave247_p5_r5b_nfe_sweep.py` — driver (this script)")
    md_lines.append("* `verification_outputs/wave247-p5-r5b-nfe{50,100,200}.csv` — per-NFE CSV")
    md_lines.append("* `verification_outputs/wave247-p5-r5b-nfe-sweep-aggregate.csv` — aggregate")
    md_lines.append("* `verification_outputs/wave247-p5-r5b-nfe-sweep-aggregate.json` — machine-readable")
    md_lines.append("")
    doc.write_text("\n".join(md_lines) + "\n")
    print(f"[w247-p5] wrote audit doc {doc.relative_to(REPO)}", flush=True)

    # Save verdict summary to JSON for downstream consumption.
    summary_path = OUT_DIR / "wave247-p5-r5b-nfe-sweep-summary.json"
    summary_path.write_text(json.dumps({
        "schema": "wave247_p5_nfe_sweep_summary_v1",
        "n_nfe_values_tested": len(NFE_VALUES),
        "nfe_values": NFE_VALUES,
        "best_nfe_for_win": best_nfe_overall,
        "best_nfe_per_scheduler": best_nfe_per_sched,
        "best_delta_fid_pct": best_delta_pct,
        "win_at_nfe50": win_at_nfe50,
        "win_at_higher_nfe": win_at_higher_nfe,
        "win_extends_to_higher_nfe": win_extends,
        "d4_byte_stable_pass": d4["d4_pass"],
        "d4_byte_stable_n_passed": d4["n_passed"],
    }, indent=2, default=str) + "\n")
    print(f"[w247-p5] wrote summary {summary_path.relative_to(REPO)}", flush=True)

    return 0 if d4["d4_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

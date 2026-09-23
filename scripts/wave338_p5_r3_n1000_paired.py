"""Wave 338 P5 — R3 N=1000 paired sweep at seeds 42, 43, 44.

Phase 5 of the Wave 338 wave: after Wave 338 P2 (DGL fix wiring
verification) and Wave 338 P4 (single-mol path), this script runs the
FULL N=1000 paired sweep across 3 seeds to lift the Wave 206 P3 / Wave
225 P3 R3 cross-seed BLOCKED verdict.

Inputs:
  - The DGL fix from Wave 109.C §6.2 (repeat_interleave per-mol prior
    tiling) + Wave 338 P2's _pad_e dimension-fix in
    flowmol3_v2_adapter._solve_ode_upstream_batch.
  - Canonical Wave 82 / Wave 87 / Wave 206 P3 byte-stable seed=42 data
    as the seed=42 reference.

Outputs:
  - verification_outputs/wave338-p5-r3-n1000-paired.{csv,json}
  - verification_outputs/flowmol3_n1000_baseline_wave338_p5_seed{42,43,44}.json
  - verification_outputs/flowmol3_n1000_framework_wave338_p5_seed{42,43,44}.json
  - verification_outputs/flowmol3_n1000_sweep_wave338_p5_seed{42,43,44}.json

Run as::
    .venvs/flowmol3_venv/bin/python scripts/wave338_p5_r3_n1000_paired.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import scipy.stats

# Make the project + upstream FlowMol3 repo importable.
REPO_ROOT = Path("/home/hugo/codes/flowa-multistep-reinference")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "data" / "FlowMol3" / "repo"))
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
warnings.filterwarnings("ignore")

from tools.paper_metrics import compute_all_paper_metrics  # noqa: E402

# Constants matching the canonical Wave 82 sweep.
N_TOTAL = 1000
NFE = 250
NFE_BATCH = 100
SEEDS = (42, 43, 44)
WEIGHTS_PATH = REPO_ROOT / "data" / "flowmol3" / "weights_real" / "checkpoints" / "last.ckpt"
UPSTREAM_REPO = REPO_ROOT / "data" / "FlowMol3" / "repo"
DEVICE = "cuda:0"
PERTURBATION_SIGMA_BASELINE = 0.0
PERTURBATION_SIGMA_FRAMEWORK = 0.05

# Paper targets (arXiv 2508.12629)
PAPER_TARGETS = {
    "validity_pct": 0.999,
    "pb_validity_pct": 0.919,
    "fg_dev": 0.27,
    "ood_ring_rate": 0.10,
}


def _build_canonical_prior(adapter, batch_id: str):
    """Build the canonical FlowMol3 prior state."""
    return adapter.build_initial_state(batch_id=batch_id, sample_id=f"{batch_id}-prior")


def _framework_perturb_prior(adapter, bundle, *, perturbation_sigma: float, seed: int) -> None:
    """Apply the framework's restart-blend perturbation (sigma > 0) to the canonical prior."""
    if perturbation_sigma <= 0.0:
        return
    rng = np.random.default_rng(int(seed) * 1009 + 7)
    digest = bundle.native_state_digest
    entry = adapter._native_states.get(digest)
    if entry is None:
        return
    x_canonical = np.asarray(entry["x"], dtype=np.float64)
    if x_canonical.ndim == 2 and x_canonical.shape[1] == 3:
        noise = rng.standard_normal(x_canonical.shape).astype(np.float64) * float(perturbation_sigma)
        entry["x"] = (x_canonical + noise).astype(np.float64)
        adapter._native_states[digest] = entry


def _generate_arm(*, arm_name, perturbation_sigma, seed_base, n_total, nfe,
                  nfe_batch, weights_path, upstream_repo, device):
    """Generate N=1000 SDF molecules for one arm via the upstream path."""
    from adaptive_reflow.adapters.flowmol3_v2_adapter import FlowMol3V2Adapter
    from adaptive_reflow.universal.state import ODEConditionDelta

    print(f"[{arm_name} seed_base={seed_base}] Loading FlowMol3 v2 adapter (upstream path)...",
          flush=True)
    t0 = time.perf_counter()
    adapter = FlowMol3V2Adapter(
        backend="torch",
        num_steps=nfe,
        weights_path=str(weights_path),
        device=device,
        use_upstream=True,
        upstream_repo_dir=str(upstream_repo),
    )
    _ = adapter._load_model()
    if adapter._loaded_model_kind() != "upstream_flowmol":
        raise RuntimeError(
            f"[{arm_name}] expected upstream_flowmol, got {adapter._loaded_model_kind()!r}"
        )
    load_seconds = round(time.perf_counter() - t0, 3)
    print(f"[{arm_name}] adapter + model loaded in {load_seconds}s", flush=True)

    sampled_mols = []
    smiles_list = []
    errors = []
    dropped_smiles_total = []
    t_total = time.perf_counter()
    n_batches = n_total // nfe_batch
    for batch_idx in range(n_batches):
        seed = int(seed_base + batch_idx)
        batch_id = f"{arm_name}-seed{seed_base}-batch{batch_idx}"
        bundle = _build_canonical_prior(adapter, batch_id)
        if perturbation_sigma > 0.0:
            _framework_perturb_prior(
                adapter, bundle, perturbation_sigma=perturbation_sigma, seed=seed,
            )
        cond = ODEConditionDelta(
            delta_spec={"num_steps": nfe},
            source=f"wave338_p5_{arm_name}_seed{seed_base}",
            target_round=0,
            calibration_artifact_hash="wave338_p5",
        )
        t_batch = time.perf_counter()
        try:
            trace = adapter.solve_ode(bundle, cond, seed=int(seed), n_molecules=nfe_batch)
        except Exception as exc:
            errors.append(f"batch{batch_idx}:{type(exc).__name__}:{exc}")
            continue
        sampled_batch, metadata = adapter.export_sampled_molecules(trace)
        per_batch_s = round(time.perf_counter() - t_batch, 3)
        if metadata.get("marker") not in ("ok", "ok_batch"):
            errors.append(
                f"batch{batch_idx}:decode_marker={metadata.get('marker')!r} "
                f"err={metadata.get('upstream_decode_error', '')!r}"
            )
            continue
        sampled_mols.extend(sampled_batch)
        entry = adapter._native_states.get(trace.native_state_digest) or {}
        cached_smiles = entry.get("rdkit_mol_smiles_batch") or []
        if cached_smiles:
            smiles_list.extend([s for s in cached_smiles if isinstance(s, str) and s])
        batch_dropped = metadata.get("dropped_smiles") or []
        if batch_dropped:
            dropped_smiles_total.extend(batch_dropped)
        print(
            f"[{arm_name} seed_base={seed_base}] batch {batch_idx + 1}/{n_batches}: "
            f"{len(sampled_batch)} mols in {per_batch_s}s (running {len(sampled_mols)})",
            flush=True,
        )

    wallclock_s = round(time.perf_counter() - t_total, 3)
    for smi in dropped_smiles_total[:5]:
        errors.append(f"dropped_smiles:{smi}")

    return {
        "schema_version": "1.0.0",
        "arm": arm_name,
        "n_target": int(n_total),
        "n_sampled": int(len(sampled_mols)),
        "n_smiles": int(len(smiles_list)),
        "n_errors": int(len(errors)),
        "n_dropped": int(len(dropped_smiles_total)),
        "errors_sample": errors[:5],
        "wallclock_s": float(wallclock_s),
        "load_seconds": float(load_seconds),
        "perturbation_sigma": float(perturbation_sigma),
        "seed_base": int(seed_base),
        "nfe": int(nfe),
        "nfe_batch": int(nfe_batch),
        "device": str(device),
        "weights_path": str(weights_path),
        "smiles_list": smiles_list[:200],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "_sampled_mols": sampled_mols,  # for downstream metric computation
    }


def _compute_metrics(sampled_mols, *, arm_name, seed_base):
    """Compute the paper metrics (validity_pct, pb_validity_pct, fg_dev, ood_ring_rate)."""
    t0 = time.perf_counter()
    pmr = compute_all_paper_metrics(sampled_mols, reference="GEOM_DRUGS")
    metrics = {
        "validity_pct": float(pmr.paper_validity_pct),
        "pb_validity_pct": float(pmr.paper_pb_validity_pct),
        "fg_dev": float(pmr.paper_fg_deviation),
        "ood_ring_rate": float(pmr.paper_ood_ring_rate),
        "wallclock_s": round(time.perf_counter() - t0, 3),
    }
    print(
        f"[{arm_name} seed_base={seed_base}] metrics computed in {metrics['wallclock_s']}s: "
        f"fg_dev={metrics['fg_dev']:.6f}, validity={metrics['validity_pct']:.4f}",
        flush=True,
    )
    return metrics


def _run_one_seed(seed_base: int, *, n_total, nfe, nfe_batch, weights_path,
                  upstream_repo, device, out_dir) -> dict:
    """Run baseline + framework arms for one seed and return the paired dict."""
    baseline_raw = _generate_arm(
        arm_name="baseline", perturbation_sigma=PERTURBATION_SIGMA_BASELINE,
        seed_base=seed_base, n_total=n_total, nfe=nfe, nfe_batch=nfe_batch,
        weights_path=weights_path, upstream_repo=upstream_repo, device=device,
    )
    baseline_metrics = _compute_metrics(baseline_raw["_sampled_mols"],
                                       arm_name="baseline", seed_base=seed_base)

    framework_raw = _generate_arm(
        arm_name="framework", perturbation_sigma=PERTURBATION_SIGMA_FRAMEWORK,
        seed_base=seed_base, n_total=n_total, nfe=nfe, nfe_batch=nfe_batch,
        weights_path=weights_path, upstream_repo=upstream_repo, device=device,
    )
    framework_metrics = _compute_metrics(framework_raw["_sampled_mols"],
                                        arm_name="framework", seed_base=seed_base)

    # Persist per-arm JSONs (excluding the in-memory sampled_mols).
    for raw, metrics in [(baseline_raw, baseline_metrics), (framework_raw, framework_metrics)]:
        arm = raw["arm"]
        out_path = out_dir / f"flowmol3_n1000_{arm}_wave338_p5_seed{seed_base}.json"
        payload = {k: v for k, v in raw.items() if k != "_sampled_mols"}
        payload["metrics"] = metrics
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote {out_path}", flush=True)

    sweep = {
        "schema_version": "1.0.0",
        "sweep_id": f"wave338_p5_r3_n1000_paired_seed{seed_base}",
        "model": "flowmol3",
        "checkpoint": str(weights_path),
        "n_total_per_arm": int(n_total),
        "nfe": int(nfe),
        "nfe_batch": int(nfe_batch),
        "n_batches": int(n_total // nfe_batch),
        "seed_base": int(seed_base),
        "device": str(device),
        "paper_targets": PAPER_TARGETS,
        "baseline": {
            "perturbation_sigma": PERTURBATION_SIGMA_BASELINE,
            "metrics": baseline_metrics,
            "n_sampled": int(baseline_raw["n_sampled"]),
            "n_smiles": int(baseline_raw["n_smiles"]),
            "n_errors": int(baseline_raw["n_errors"]),
            "wallclock_sampling_s": float(baseline_raw["wallclock_s"]),
            "wallclock_metrics_s": float(baseline_metrics["wallclock_s"]),
            "errors_sample": baseline_raw["errors_sample"],
        },
        "framework": {
            "perturbation_sigma": PERTURBATION_SIGMA_FRAMEWORK,
            "metrics": framework_metrics,
            "n_sampled": int(framework_raw["n_sampled"]),
            "n_smiles": int(framework_raw["n_smiles"]),
            "n_errors": int(framework_raw["n_errors"]),
            "wallclock_sampling_s": float(framework_raw["wallclock_s"]),
            "wallclock_metrics_s": float(framework_metrics["wallclock_s"]),
            "errors_sample": framework_raw["errors_sample"],
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    diff = framework_metrics["fg_dev"] - baseline_metrics["fg_dev"]
    sweep["paired_diff_fg_dev"] = diff
    sweep["verdict"] = "framework_wins" if diff < 0 else "baseline_wins"
    sweep_path = out_dir / f"flowmol3_n1000_sweep_wave338_p5_seed{seed_base}.json"
    sweep_path.write_text(json.dumps(sweep, indent=2), encoding="utf-8")
    print(f"wrote {sweep_path} (paired_diff_fg_dev={diff:+.6f})", flush=True)
    return sweep


def _paired_summary(per_seed: list[dict]) -> dict:
    """Aggregate across seeds into a paired-summary record."""
    diffs = np.asarray([s["paired_diff_fg_dev"] for s in per_seed], dtype=np.float64)
    n = len(diffs)
    mean = float(diffs.mean())
    sd = float(diffs.std(ddof=1)) if n > 1 else float("nan")
    se = sd / math.sqrt(n) if n > 1 and sd == sd else float("nan")
    t_stat = mean / se if se == se and se > 0 else float("nan")
    df = n - 1
    p_raw = float(2.0 * scipy.stats.t.sf(abs(t_stat), df=df)) if t_stat == t_stat else float("nan")
    ci_low = mean - 1.96 * se if se == se else float("nan")
    ci_high = mean + 1.96 * se if se == se else float("nan")
    d_z = mean / sd if sd == sd and sd > 0 else float("nan")
    return {
        "n_seeds": n,
        "mean_diff": mean,
        "sd_diff": sd,
        "se_diff": se,
        "t_statistic": t_stat,
        "df": df,
        "p_value_raw": p_raw,
        "ci_95_low": ci_low,
        "ci_95_high": ci_high,
        "cohens_d_z": d_z,
        "test_type": "paired_t_test_across_seeds",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--n-total", type=int, default=N_TOTAL)
    p.add_argument("--nfe", type=int, default=NFE)
    p.add_argument("--nfe-batch", type=int, default=NFE_BATCH)
    p.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    p.add_argument("--device", default=DEVICE)
    p.add_argument("--output-dir", type=Path,
                   default=REPO_ROOT / "verification_outputs")
    args = p.parse_args(argv)

    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    per_seed = []
    for seed in args.seeds:
        print(f"\n========== seed_base={seed} ==========", flush=True)
        sweep = _run_one_seed(
            int(seed),
            n_total=int(args.n_total),
            nfe=int(args.nfe),
            nfe_batch=int(args.nfe_batch),
            weights_path=WEIGHTS_PATH,
            upstream_repo=UPSTREAM_REPO,
            device=str(args.device),
            out_dir=out_dir,
        )
        per_seed.append(sweep)

    # Paired summary across seeds.
    paired = _paired_summary(per_seed)
    bonf_alpha = 0.05 / 7
    paired["alpha_bonferroni"] = bonf_alpha
    paired["bonf_sig"] = (
        paired["p_value_raw"] < bonf_alpha
        if paired["p_value_raw"] == paired["p_value_raw"] else False
    )
    print("\n=== Paired summary across seeds ===", flush=True)
    for k, v in paired.items():
        print(f"  {k}: {v}", flush=True)

    # Persist paired CSV + JSON.
    csv_path = out_dir / "wave338-p5-r3-n1000-paired.csv"
    json_path = out_dir / "wave338-p5-r3-n1000-paired.json"
    per_seed_rows = []
    for s in per_seed:
        per_seed_rows.append({
            "seed_base": s["seed_base"],
            "n_total_per_arm": s["n_total_per_arm"],
            "baseline_fg_dev": s["baseline"]["metrics"]["fg_dev"],
            "framework_fg_dev": s["framework"]["metrics"]["fg_dev"],
            "baseline_n_sampled": s["baseline"]["n_sampled"],
            "framework_n_sampled": s["framework"]["n_sampled"],
            "paired_diff_fg_dev": s["paired_diff_fg_dev"],
            "verdict": s["verdict"],
            "wallclock_sampling_s": (
                s["baseline"]["wallclock_sampling_s"]
                + s["framework"]["wallclock_sampling_s"]
            ),
            "wallclock_metrics_s": (
                s["baseline"]["wallclock_metrics_s"]
                + s["framework"]["wallclock_metrics_s"]
            ),
        })
    summary_row = {
        "seed_base": "PAIRED_SUMMARY",
        "n_total_per_arm": "",
        "baseline_fg_dev": "",
        "framework_fg_dev": "",
        "baseline_n_sampled": "",
        "framework_n_sampled": "",
        "paired_diff_fg_dev": paired["mean_diff"],
        "verdict": (
            "framework_wins"
            if paired["mean_diff"] < 0 else "baseline_wins"
        ),
        "wallclock_sampling_s": "",
        "wallclock_metrics_s": "",
    }
    summary_row.update({
        f"paired_{k}": v for k, v in paired.items()
    })
    all_rows = per_seed_rows + [summary_row]
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"wrote {csv_path}", flush=True)

    full_payload = {
        "schema_version": "1.0.0",
        "wave": "338 P5",
        "kind": "R3_n1000_paired_3seed",
        "n_seeds_requested": len(args.seeds),
        "n_seeds_completed": len(per_seed),
        "n_total_per_arm": int(args.n_total),
        "nfe": int(args.nfe),
        "nfe_batch": int(args.nfe_batch),
        "device": str(args.device),
        "per_seed": per_seed,
        "paired_summary": paired,
        "honest_disclosure": (
            "Wave 338 P5 R3 N=1000 paired sweep at 3 seeds (42, 43, 44). "
            "The DGL fix (Wave 109.C §6.2 repeat_interleave per-mol prior tiling "
            "+ Wave 338 P2 _pad_e dimension fix in flowmol3_v2_adapter._solve_ode_upstream_batch) "
            "made the batched n_molecules=100 path operational at NFE=250. "
            "Each arm runs 10 batches × 100 mols via the upstream FlowMol.sample() call."
        ),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    json_path.write_text(json.dumps(full_payload, indent=2, default=float),
                         encoding="utf-8")
    print(f"wrote {json_path}", flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
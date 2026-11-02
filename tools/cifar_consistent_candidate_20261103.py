#!/usr/bin/env python3
"""Separate, prospectively fixed generation-seed holdout for a path-consistent minimal candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ARMS = ("baseline_euler", "consistent_two_round", "ve_restart")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate(model, initial, *, seed, cost, device):
    import torch

    from scripts.wave191_p3_mnist_sweep import per_round_num_steps_equal_budget

    parts = per_round_num_steps_equal_budget(
        "evidence_driven", 2, cost, allocation="proportional", interval_lengths=[1.0, 0.3]
    )
    noise = (
        np.random.default_rng(np.random.SeedSequence([seed, 1, 0]))
        .standard_normal(initial.shape)
        .astype(np.float32)
    )
    outputs = []
    counts = []
    tic = time.monotonic()
    with torch.inference_mode():
        for offset in range(0, len(initial), 32):
            x = torch.as_tensor(initial[offset : offset + 32], device=device)
            calls = 0
            for step in range(parts[0]):
                x = (
                    x
                    + model(
                        x, torch.full((len(x),), 0.001 + step / parts[0] * 0.999, device=device)
                    )
                    / parts[0]
                )
                calls += 1
            x = 0.7 * x + 0.3 * torch.as_tensor(noise[offset : offset + len(x)], device=device)
            # Actual model time=.7 exactly, matching the state coefficient. No epsilon warp in this segment.
            for step in range(parts[1]):
                x = x + model(
                    x, torch.full((len(x),), 0.7 + 0.3 * step / parts[1], device=device)
                ) * (0.3 / parts[1])
                calls += 1
            assert calls == cost
            if not torch.isfinite(x).all():
                raise RuntimeError("nonfinite candidate samples")
            counts.append(calls)
            outputs.append(x.cpu().numpy())
    x = np.concatenate(outputs)
    torch.cuda.synchronize(device)
    return x, dict(
        velocity_calls_per_sample=cost,
        actual_calls_per_batch=counts,
        parts=parts,
        generation_wall_s=time.monotonic() - tic,
        raw_min=float(x.min()),
        raw_max=float(x.max()),
        clipped_fraction=float((np.abs(x) > 1).mean()),
        n_processed=len(x),
        n_skipped=0,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, choices=[101, 102, 103], required=True)
    p.add_argument("--cost", type=int, choices=[99, 199], required=True)
    args = p.parse_args()
    protocol = json.loads(args.protocol.read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    for path, value in protocol["source_sha256"].items():
        if sha(ROOT / path) != value:
            raise RuntimeError(f"source changed: {path}")
    device = "cuda:1"
    started = time.monotonic()
    (args.out / "METADATA.json").write_text(
        json.dumps(
            {
                "registered_utc": datetime.now(UTC).isoformat(),
                "argv": sys.argv,
                "n_planned": 1000,
                "n_cap": 1000,
                "seed": args.seed,
                "cost": args.cost,
                "device": device,
                "environment": sys.executable,
                "protocol_sha256": sha(args.protocol),
                "driver_sha256": sha(Path(__file__)),
                "base_commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                "wall_cap_s": 600,
                "gpu_snapshot": subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=index,name,memory.free,utilization.gpu",
                        "--format=csv,noheader",
                    ],
                    text=True,
                ),
            },
            indent=2,
        )
        + "\n"
    )
    import torch

    from adaptive_reflow.adapters._gnobitab_ddpmpp import load_gnobitab_rf_cifar_unet
    from adaptive_reflow.adapters.rectified_flow_cifar import _extract_checkpoint_state_dict
    from adaptive_reflow.eval.fid import compute_frechet_distance
    from tools.cifar_matched_frontier_20261103 import generate, official_sampler
    from tools.cifar_study_metrics_20261103 import kernel_rows, kernel_score

    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = True
    weights = ROOT / "data/cifar10_rf.pth"
    assert sha(weights) == protocol["weights_sha256"]
    model = (
        load_gnobitab_rf_cifar_unet(
            _extract_checkpoint_state_dict(
                torch.load(weights, map_location="cpu", weights_only=False)
            )
        )
        .to(device)
        .eval()
    )
    source = ROOT / protocol["restart_source_path"]
    assert sha(source) == protocol["restart_source_sha256"]
    sampler = official_sampler(source)
    initial = np.random.default_rng(args.seed).standard_normal((1000, 3, 32, 32)).astype(np.float32)
    samples = {}
    info = {}
    for arm in ARMS:
        print("START", args.seed, args.cost, arm, flush=True)
        if arm == "consistent_two_round":
            samples[arm], info[arm] = candidate(
                model, initial, seed=args.seed, cost=args.cost, device=device
            )
        else:
            samples[arm], info[arm] = generate(
                model,
                initial,
                arm=arm,
                cost=args.cost,
                seed=args.seed,
                device=device,
                batch_size=32,
                sampler=sampler,
            )
        print("GENERATED", arm, info[arm], flush=True)
    del model
    torch.cuda.empty_cache()
    from pytorch_fid.inception import InceptionV3

    inception = InceptionV3([InceptionV3.BLOCK_INDEX_BY_DIM[2048]]).to(device).eval()
    reference = np.load(ROOT / protocol["reference_path"])["reference"].astype(np.float64)
    reference_self = json.loads((ROOT / protocol["reference_statistics"]).read_text())[
        "reference_self_kernel"
    ]
    mu_ref, cov_ref = reference.mean(0), np.cov(reference, rowvar=False)
    features = {}
    witness = {}
    results = {}
    for arm, images in samples.items():
        f = []
        with torch.inference_mode():
            for offset in range(0, len(images), 64):
                x = torch.as_tensor(images[offset : offset + 64], device=device)
                f.append(inception(((x + 1) / 2).clamp(0, 1))[0].flatten(1).cpu().numpy())
        f = np.concatenate(f).astype(np.float64)
        features[arm] = f.astype(np.float32)
        xx, xy = kernel_rows(f, f, self_kernel=True), kernel_rows(f, reference)
        witness[f"{arm}_xx"], witness[f"{arm}_xy"] = xx, xy
        fid = float(
            compute_frechet_distance(
                mu_s=f.mean(0), sigma_s=np.cov(f, rowvar=False), mu_r=mu_ref, sigma_r=cov_ref
            )
        )
        results[arm] = {
            **info[arm],
            "kid_unscaled": kernel_score(xx, xy, reference_self),
            "fid_tfport": fid,
        }
        print("METRIC", arm, results[arm]["kid_unscaled"], fid, flush=True)
    np.savez_compressed(args.out / "features.npz", **features)
    np.savez_compressed(args.out / "kid_witness.npz", **witness)
    np.savez_compressed(args.out / "raw_samples.npz", **samples)
    np.savez_compressed(
        args.out / "preselected_images.npz", **{k: v[:32] for k, v in samples.items()}
    )
    (args.out / "results.json").write_text(
        json.dumps(
            {
                "seed": args.seed,
                "cost": args.cost,
                "n": 1000,
                "pilot_only": False,
                "arms": results,
                "wall_s": time.monotonic() - started,
                "completed_utc": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n"
    )
    print("COMPLETE", time.monotonic() - started, flush=True)


if __name__ == "__main__":
    main()

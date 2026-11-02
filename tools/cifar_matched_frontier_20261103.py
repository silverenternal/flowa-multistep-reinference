#!/usr/bin/env python3
"""Locked five-arm, matched-call CIFAR independent validation. No training or tuning."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
import time
import types
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ARMS = ("baseline_euler", "full_euler", "simple_euler", "ve_heun", "ve_restart")
COSTS = (25, 49, 99, 199)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def official_sampler(path: Path):
    import torch

    tree = ast.parse(path.read_text())
    fn = next(
        x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == "restart_sampler"
    )
    namespace = dict(torch=torch, np=np, dist=types.SimpleNamespace(print0=lambda *_a, **_k: None))
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["restart_sampler"]


def main_steps(cost: int, restart: bool) -> int:
    if cost < 25 or cost % 2 != 1:
        raise ValueError("locked VE protocols need odd cost >=25")
    # Main Heun: 2N-1 calls; two restarts each with three nodes: 2*2*(3-1)=8 calls.
    return (cost - (8 if restart else 0) + 1) // 2


def denoiser_value(velocity, y, sigma):
    import torch

    t = 1 / (1 + sigma)
    physical = (t * y).float()
    time_input = torch.full((len(y),), float(t), dtype=torch.float32, device=y.device)
    return t * y + (1 - t) * velocity(physical, time_input).to(y.dtype)


class RFDenoiser:
    img_channels = 3
    img_resolution = 32
    sigma_min = 0.002
    sigma_max = 999.0

    def __init__(self, velocity):
        self.velocity = velocity

    @staticmethod
    def round_sigma(sigma):
        return sigma

    def __call__(self, y, sigma, _class_labels=None):
        return denoiser_value(self.velocity, y, sigma)


def generate(
    model, initial: np.ndarray, *, arm: str, cost: int, seed: int, device, batch_size: int, sampler
):
    import torch

    from scripts.wave191_p3_mnist_sweep import per_round_num_steps_equal_budget

    if arm not in ARMS:
        raise ValueError(arm)
    n = len(initial)
    m = 0.7 ** (1 / 3)
    if arm in ("full_euler", "simple_euler"):
        parts = per_round_num_steps_equal_budget(
            "evidence_driven", 4, cost, allocation="scheduler" if arm == "full_euler" else "uniform"
        )
    else:
        parts = [cost]
    fresh = (
        [
            np.random.default_rng(np.random.SeedSequence([seed, 1, k]))
            .standard_normal(initial.shape)
            .astype(np.float32)
            for k in range(3)
        ]
        if "euler" in arm and arm != "baseline_euler"
        else []
    )
    outputs, anchors = [], []
    max_calls = []
    tic = time.monotonic()
    for offset in range(0, n, batch_size):
        z = torch.as_tensor(initial[offset : offset + batch_size], device=device)
        calls = [0]

        def velocity(x, t, calls=calls):
            calls[0] += 1
            return model(x, t)

        def euler(x, a, b, steps):
            for step in range(steps):
                t = 0.001 + (a + (b - a) * step / steps) * 0.999
                x = x + velocity(x, torch.full((len(x),), t, device=device)) * ((b - a) / steps)
            return x

        with torch.inference_mode():
            if arm == "baseline_euler":
                x = euler(z, 0.0, 1.0, cost)
            elif arm in ("full_euler", "simple_euler"):
                x = euler(z, 0.0, 1.0, parts[0])
                anchors.append(x.cpu().numpy())
                for k in range(3):
                    noise = torch.as_tensor(fresh[k][offset : offset + len(z)], device=device)
                    x = m * x + (1 - m) * noise
                    x = euler(x, m if arm == "full_euler" else 0.0, 1.0, parts[k + 1])
            else:
                rng = np.random.default_rng(np.random.SeedSequence([seed, 2, offset]))

                def randn_like(x, rng=rng):
                    return torch.as_tensor(
                        rng.standard_normal(tuple(x.shape)), device=device, dtype=x.dtype
                    )

                x = sampler(
                    RFDenoiser(velocity),
                    z.double() / (999.0 / 1000.0),
                    randn_like=randn_like,
                    num_steps=main_steps(cost, arm == "ve_restart"),
                    sigma_min=0.002,
                    sigma_max=999.0,
                    rho=7,
                    S_churn=0.0,
                    S_min=0.0,
                    S_max=float("inf"),
                    S_noise=1.0,
                    restart_gamma=0.0,
                    restart_info='{"0": [3, 2, 0.06, 0.30]}' if arm == "ve_restart" else "",
                )
            if calls[0] != cost:
                raise RuntimeError(f"cost mismatch {arm}: actual{calls[0]} planned{cost}")
            if not torch.isfinite(x).all():
                raise RuntimeError(f"nonfinite output {arm}")
            outputs.append(x.cpu().numpy())
            max_calls.append(calls[0])
    x = np.concatenate(outputs).astype(np.float32)
    if arm == "full_euler":
        anchor = np.concatenate(anchors).astype(np.float64).mean(axis=0)
        x = (x.astype(np.float64) - x.astype(np.float64).mean(axis=0) + anchor).astype(np.float32)
    torch.cuda.synchronize(device)
    return x, dict(
        velocity_calls_per_sample=cost,
        actual_calls_per_batch=max_calls,
        parts=parts,
        generation_wall_s=time.monotonic() - tic,
        raw_min=float(x.min()),
        raw_max=float(x.max()),
        clipped_fraction=float((np.abs(x) > 1).mean()),
        n_processed=n,
        n_skipped=0,
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, choices=[42, 43, 44], required=True)
    p.add_argument("--cost", type=int, choices=COSTS, required=True)
    p.add_argument("--n", type=int, choices=[32, 1000], required=True)
    p.add_argument("--device", default="cuda:1")
    args = p.parse_args()
    protocol = json.loads(args.protocol.read_text())
    if digest(Path(__file__)) != protocol["driver_sha256"]:
        raise RuntimeError("executed driver differs from prospective lock")
    args.out.mkdir(parents=True, exist_ok=False)
    meta = {
        "started_utc": datetime.now(UTC).isoformat(),
        "argv": sys.argv,
        "protocol_sha256": digest(args.protocol),
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "driver_sha256": digest(Path(__file__)),
        "n_planned": args.n,
        "n_cap": args.n,
        "seed": args.seed,
        "cost": args.cost,
        "device": args.device,
        "pilot_only": args.n != 1000,
        "wall_cap_s": 1200,
        "environment": sys.executable,
        "thread_env": {
            k: __import__("os").environ.get(k) for k in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"]
        },
        "gpu_snapshot": subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.free,utilization.gpu",
                "--format=csv,noheader",
            ],
            text=True,
        ),
    }
    (args.out / "METADATA.json").write_text(json.dumps(meta, indent=2) + "\n")
    started = time.monotonic()
    import torch

    from adaptive_reflow.adapters._gnobitab_ddpmpp import load_gnobitab_rf_cifar_unet
    from adaptive_reflow.adapters.rectified_flow_cifar import _extract_checkpoint_state_dict
    from adaptive_reflow.eval.fid import compute_frechet_distance
    from tools.cifar_study_metrics_20261103 import kernel_rows, kernel_score

    device = torch.device(args.device)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = True
    weights = ROOT / "data/cifar10_rf.pth"
    if digest(weights) != protocol["weights_sha256"]:
        raise RuntimeError("wrong checkpoint")
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
    if digest(source) != protocol["restart_source_sha256"]:
        raise RuntimeError("official source changed")
    sampler = official_sampler(source)
    initial = (
        np.random.default_rng(args.seed).standard_normal((args.n, 3, 32, 32)).astype(np.float32)
    )
    samples = {}
    run_info = {}
    for arm in ARMS:
        print("START", args.seed, args.cost, arm, flush=True)
        samples[arm], run_info[arm] = generate(
            model,
            initial,
            arm=arm,
            cost=args.cost,
            seed=args.seed,
            device=device,
            batch_size=32,
            sampler=sampler,
        )
        print("GENERATED", arm, run_info[arm], flush=True)
    del model
    torch.cuda.empty_cache()
    from pytorch_fid.inception import InceptionV3

    inception = InceptionV3([InceptionV3.BLOCK_INDEX_BY_DIM[2048]]).to(device).eval()
    reference = np.load(ROOT / protocol["reference_path"])["reference"].astype(np.float64)
    ref_stats = json.loads((ROOT / protocol["reference_statistics"]).read_text())
    mu_ref = reference.mean(0)
    cov_ref = np.cov(reference, rowvar=False)
    features = {}
    witness = {}
    results = {}
    for arm, images in samples.items():
        batch_features = []
        with torch.inference_mode():
            for offset in range(0, len(images), 64):
                x = torch.as_tensor(images[offset : offset + 64], device=device)
                batch_features.append(
                    inception(((x + 1) / 2).clamp(0, 1))[0].flatten(1).cpu().numpy()
                )
        f = np.concatenate(batch_features).astype(np.float64)
        features[arm] = f.astype(np.float32)
        xx = kernel_rows(f, f, self_kernel=True)
        xy = kernel_rows(f, reference)
        witness[f"{arm}_xx"] = xx
        witness[f"{arm}_xy"] = xy
        fid = float(
            compute_frechet_distance(
                mu_s=f.mean(0), sigma_s=np.cov(f, rowvar=False), mu_r=mu_ref, sigma_r=cov_ref
            )
        )
        results[arm] = {
            **run_info[arm],
            "kid_unscaled": kernel_score(xx, xy, ref_stats["reference_self_kernel"]),
            "fid_tfport": fid,
            "feature_shape": list(f.shape),
        }
        print("METRIC", arm, results[arm]["kid_unscaled"], fid, flush=True)
    np.savez_compressed(args.out / "features.npz", **features)
    np.savez_compressed(args.out / "kid_witness.npz", **witness)
    np.savez_compressed(args.out / "raw_samples.npz", **samples)
    np.savez_compressed(
        args.out / "preselected_images.npz", **{k: v[:32] for k, v in samples.items()}
    )
    result = {
        "seed": args.seed,
        "cost": args.cost,
        "n": args.n,
        "pilot_only": args.n != 1000,
        "arms": results,
        "wall_s": time.monotonic() - started,
        "completed_utc": datetime.now(UTC).isoformat(),
    }
    (args.out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print("COMPLETE", args.seed, args.cost, result["wall_s"], flush=True)


if __name__ == "__main__":
    main()

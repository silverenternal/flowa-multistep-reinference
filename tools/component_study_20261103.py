#!/usr/bin/env python3
"""Prospectively locked, matched-call MNIST component study. No model training."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kid_unbiased(x: np.ndarray, y: np.ndarray) -> float:
    """Degree-3 polynomial MMD U-statistic on supplied features, not Inception KID."""
    if x.ndim != 2 or y.ndim != 2 or x.shape[1] != y.shape[1] or min(len(x), len(y)) < 2:
        raise ValueError("need two finite feature matrices with matching dimension")
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise ValueError("nonfinite features")
    d = x.shape[1]
    xx, yy, xy = (x @ x.T / d + 1) ** 3, (y @ y.T / d + 1) ** 3, (x @ y.T / d + 1) ** 3
    return float(
        (xx.sum() - np.trace(xx)) / (len(x) * (len(x) - 1))
        + (yy.sum() - np.trace(yy)) / (len(y) * (len(y) - 1))
        - 2 * xy.mean()
    )


def configurations(steps: int = 50) -> dict[str, dict]:
    if steps != 50:
        raise ValueError("locked scientific protocol uses exactly 50 steps")
    start = (1 - 0.3) ** (1 / 3)
    common = dict(beta=0.3, mean_preserve=True, restart_t0_mode="memory", restart_t0=None)
    return {
        "full": common,
        "no_mean": {**common, "mean_preserve": False},
        "uniform_budget": {**common, "allocation": "uniform"},
        "no_mix_fixed_time": {**common, "beta": 0.0, "restart_t0": start},
        "zero_restart_time": {**common, "restart_t0_mode": "zero"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", choices=["w16e1_5k", "production"], required=True)
    parser.add_argument("--seed", choices=[42, 43, 44], type=int, required=True)
    parser.add_argument("--n", type=int, choices=[64, 1000], default=1000)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    import torch

    from adaptive_reflow.adapters.mnist_fm import MnistFmAdapter
    from adaptive_reflow.adapters.mnist_fm_torch import TorchMnistVelocity
    from adaptive_reflow.eval.mnist_fid import MnistFrechetProjectionEvaluator, _frechet_distance
    from scripts.wave191_p3_mnist_sweep import (
        per_round_num_steps_equal_budget,
        run_baseline,
        run_framework_arm,
    )

    weights = REPO / f"data/mnist_fm/{args.checkpoint}.ckpt.npz"
    gpu = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-gpu=index,name,memory.free,utilization.gpu",
            "--format=csv,noheader",
        ],
        text=True,
    )
    metadata = {
        "started_utc": datetime.now(UTC).isoformat(),
        "argv": sys.argv,
        "base_repository_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
        ).strip(),
        "weights_path": str(weights),
        "weights_sha256": sha(weights),
        "protocol_sha256": sha(args.protocol),
        "checkpoint": args.checkpoint,
        "seed": args.seed,
        "n_planned": args.n,
        "n_cap": args.n,
        "device": args.device,
        "gpu_snapshot": gpu,
        "dtype": "float64",
        "python": sys.executable,
        "torch": torch.__version__,
        "numpy": np.__version__,
        "wallclock_limit_s": 600,
        "source_sha256": {
            p: sha(REPO / p)
            for p in [
                "tools/component_study_20261103.py",
                "scripts/wave191_p3_mnist_sweep.py",
                "adaptive_reflow/adapters/mnist_fm.py",
                "adaptive_reflow/adapters/mnist_fm_torch.py",
                "adaptive_reflow/eval/mnist_fid.py",
            ]
        },
    }
    (args.out / "METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n")
    started = time.monotonic()
    evaluator = MnistFrechetProjectionEvaluator()
    ref, proj = np.asarray(evaluator._ref_features), np.asarray(evaluator._projection)
    ref_idx = np.random.default_rng(20261103).choice(len(ref), 1000, replace=False)
    np.savez_compressed(
        args.out / "reference_features.npz", reference=ref, projection=proj, kid_indices=ref_idx
    )
    backend = TorchMnistVelocity(weights, device=args.device, dtype="float64")
    original_forward = backend.forward
    calls = [0]

    def counted_forward(x, t):
        calls[0] += 1
        return original_forward(x, t)

    backend.forward = counted_forward
    outputs, scores, features = {}, {}, {}
    for name in ["baseline", *configurations()]:
        if time.monotonic() - started > 570:
            raise TimeoutError("bounded cell exceeded pre-registered wall clock")
        calls[0] = 0
        torch.cuda.synchronize()
        tick = time.monotonic()
        if name == "baseline":
            samples = run_baseline(
                adapter=MnistFmAdapter(weights_path=str(weights)),
                n_samples=args.n,
                seed=args.seed,
                shared_prior=True,
                num_steps=50,
                batch_suffix=f"-s{args.seed}",
                backend=backend,
                verbose=False,
            )
            parts = [50]
            config = {"rounds": 1}
        else:
            config = dict(configurations()[name])
            allocation = config.pop("allocation", "scheduler")
            parts = per_round_num_steps_equal_budget(
                "evidence_driven", 4, 50, allocation=allocation
            )
            samples, telemetry = run_framework_arm(
                arm_name="evidence_driven",
                cycle_length=4,
                n_samples=args.n,
                num_steps_per_round=parts,
                seed_offset=args.seed,
                weights_path=weights,
                shared_prior=True,
                beta_schedule="equal_budget",
                batch_suffix=f"-s{args.seed}",
                backend=backend,
                verbose=False,
                **config,
            )
            if telemetry["total_nfe_per_sample"] != 50:
                raise ValueError("reported step budget mismatch")
            config["allocation"] = allocation
        torch.cuda.synchronize()
        elapsed = time.monotonic() - tick
        if calls[0] != 200 or samples.shape != (args.n, 784) or not np.isfinite(samples).all():
            raise ValueError(f"invalid arm: {name}, calls={calls[0]}, shape={samples.shape}")
        feats = np.asarray(samples @ proj, dtype=np.float64)
        features[name] = feats
        outputs[name] = samples
        scores[name] = {
            "projection_fid": float(_frechet_distance(feats, ref)),
            "projection_kid": kid_unbiased(feats, ref[ref_idx]),
            "actual_velocity_calls_per_sample": calls[0],
            "integration_steps": parts,
            "n_processed": len(samples),
            "n_skipped": 0,
            "generation_wall_s": elapsed,
            "configuration": config,
        }
        print(args.checkpoint, args.seed, name, scores[name], flush=True)
    # Guard is independent of component outcomes; no model selection based on results.
    guard = None
    if args.n == 1000:
        old = json.loads(
            (
                REPO
                / f"verification_outputs/gap84-cap-frontier/frontier_input_{args.checkpoint}.json"
            ).read_text()
        )
        expected = old["per_seed"]["50"][str(args.seed)]
        guard = {
            key: abs(scores[arm]["projection_fid"] - expected[key])
            for key, arm in [("baseline", "baseline"), ("framework", "full")]
        }
        if max(guard.values()) > 1e-4:
            (args.out / "FAILED_GUARD.json").write_text(json.dumps(guard, indent=2) + "\n")
            raise RuntimeError("historical full/baseline reproduction guard failed")
    np.savez_compressed(args.out / "raw_samples.npz", **outputs)
    np.savez_compressed(
        args.out / "features_and_preselected_images.npz",
        **features,
        **{f"images_{name}": x[:64] for name, x in outputs.items()},
    )
    (args.out / "results.json").write_text(
        json.dumps(
            {
                "checkpoint": args.checkpoint,
                "seed": args.seed,
                "n": args.n,
                "pilot_only": args.n != 1000,
                "arms": scores,
                "reproduction_guard": guard,
                "wall_s": time.monotonic() - started,
                "completed_utc": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()

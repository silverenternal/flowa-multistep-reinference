"""Locked real-checkpoint intermediate-path interventions, generation then CPU analysis."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SEEDS = (201, 202, 203)
TIMES = (0.5, 0.7, 0.7 ** (1 / 3))
PARTS = (32, 13, 12, 7)
ARMS = ("own_source_chord", "independent_source_chord")
BANDWIDTHS = (0.5, 1.0, 2.0)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schedule(multiplier: int) -> list[np.ndarray]:
    if multiplier not in (1, 2):
        raise ValueError("Only the locked two resolutions are allowed")
    knots = (0.0, *TIMES, 1.0)
    return [
        np.linspace(a, b, n * multiplier + 1)
        for a, b, n in zip(knots[:-1], knots[1:], PARTS, strict=True)
    ]


def squared_distances(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    x, y = x.reshape(len(x), -1).astype(np.float64), y.reshape(len(y), -1).astype(np.float64)
    return np.maximum(
        (x * x).mean(1)[:, None] + (y * y).mean(1)[None, :] - 2 * (x @ y.T) / x.shape[1], 0
    )


def discrepancy(x: np.ndarray, y: np.ndarray) -> dict:
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("Equal, nontrivial cohort sizes required")
    xx, yy, xy = squared_distances(x, x), squared_distances(y, y), squared_distances(x, y)
    n = len(x)
    scores = {}
    for width in BANDWIDTHS:
        kxx, kyy, kxy = [np.exp(-matrix / (2 * width**2)) for matrix in (xx, yy, xy)]
        biased = float(kxx.mean() + kyy.mean() - 2 * kxy.mean())
        unbiased = float(
            (kxx.sum() - np.trace(kxx) + kyy.sum() - np.trace(kyy)) / (n * (n - 1)) - 2 * kxy.mean()
        )
        scores[str(width)] = dict(
            V_MMD2=biased,
            U_MMD2=unbiased,
            xx_kernel_mean=float(kxx.mean()),
            yy_kernel_mean=float(kyy.mean()),
            xy_kernel_mean=float(kxy.mean()),
        )
    rows, cols = linear_sum_assignment(xy)
    return dict(
        rbf=scores,
        empirical_W2_RMS=math.sqrt(float(xy[rows, cols].mean())),
        mean_pixel_mean=float(x.mean()),
        centered_pixel_second_moment=float(
            ((x.astype(np.float64) - x.astype(np.float64).mean(0)) ** 2).mean()
        ),
        n_x=n,
        n_y=n,
    )


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def generate(args, protocol: dict) -> None:
    import torch

    from adaptive_reflow.adapters._gnobitab_ddpmpp import load_gnobitab_rf_cifar_unet
    from adaptive_reflow.adapters.rectified_flow_cifar import _extract_checkpoint_state_dict

    start = time.monotonic()
    device = torch.device("cuda:0")
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = True
    model = (
        load_gnobitab_rf_cifar_unet(
            _extract_checkpoint_state_dict(
                torch.load(ROOT / protocol["weights_path"], map_location="cpu", weights_only=False)
            )
        )
        .to(device)
        .eval()
    )
    n, batch = protocol["n_per_cohort"], 32
    raw_dir = args.out / "raw"
    raw_dir.mkdir(exist_ok=False)
    calls = []
    completed = []

    def advance(state, grids):
        count = 0
        for grid in grids:
            for t, stop in zip(grid[:-1], grid[1:], strict=True):
                if time.monotonic() - start > protocol["internal_wall_cap_seconds"]:
                    raise TimeoutError("GPU generation cap reached; partial study is not complete")
                state = state + model(
                    state, torch.full((len(state),), float(t), device=device)
                ) * float(stop - t)
                count += 1
        if not torch.isfinite(state).all():
            raise RuntimeError("Nonfinite model state")
        return state, count

    with torch.inference_mode():
        for seed in SEEDS:
            initial = (
                np.random.default_rng(seed).standard_normal((2 * n, 3, 32, 32)).astype(np.float32)
            )
            fresh = (
                np.random.default_rng(np.random.SeedSequence([seed, 10]))
                .standard_normal((n, 3, 32, 32))
                .astype(np.float32)
            )
            for resolution in (1, 2):
                grids = schedule(resolution)
                collected = [[] for _ in range(4)]
                for offset in range(0, 2 * n, batch):
                    state = torch.as_tensor(initial[offset : offset + batch], device=device)
                    count = 0
                    for index, grid in enumerate(grids):
                        state, added = advance(state, [grid])
                        count += added
                        collected[index].append(state.cpu().numpy())
                    assert count == 64 * resolution
                    calls.append(
                        dict(
                            kind="full_path",
                            seed=seed,
                            resolution=resolution,
                            n=len(state),
                            actual_calls=count,
                        )
                    )
                states = [np.concatenate(value) for value in collected]
                payload = dict(initial=initial, fresh=fresh, endpoint=states[-1])
                for index, m in enumerate(TIMES):
                    payload[f"mid_{index}"] = states[index]
                    for arm in ("true_path_replay", *ARMS):
                        if arm == "true_path_replay":
                            boundary = states[index][:n].copy()
                        else:
                            noise = initial[:n] if arm == "own_source_chord" else fresh
                            boundary = (m * states[-1][:n] + (1 - m) * noise).astype(np.float32)
                        outputs = []
                        for offset in range(0, n, batch):
                            x, count = advance(
                                torch.as_tensor(boundary[offset : offset + batch], device=device),
                                grids[index + 1 :],
                            )
                            expected = sum(PARTS[index + 1 :]) * resolution
                            assert count == expected
                            calls.append(
                                dict(
                                    kind=arm,
                                    seed=seed,
                                    resolution=resolution,
                                    time=m,
                                    n=len(x),
                                    actual_calls=count,
                                )
                            )
                            outputs.append(x.cpu().numpy())
                        output = np.concatenate(outputs)
                        payload[f"boundary_{index}_{arm}"] = boundary
                        payload[f"output_{index}_{arm}"] = output
                        if arm == "true_path_replay":
                            error = float(np.max(np.abs(output - states[-1][:n])))
                            if error > 1e-6:
                                raise RuntimeError(f"True-path numerical replay failed: {error}")
                    print("GENERATED", seed, resolution, m, flush=True)
                target = raw_dir / f"s{seed}_r{resolution}.npz"
                np.savez_compressed(target, **payload)
                completed.append(
                    dict(
                        seed=seed,
                        resolution=resolution,
                        path=str(target.relative_to(ROOT)),
                        sha256=sha(target),
                        bytes=target.stat().st_size,
                    )
                )
                write(args.out / "GENERATION_PROGRESS.json", dict(completed=completed))
    torch.cuda.synchronize(device)
    elapsed = time.monotonic() - start
    write(
        args.out / "GENERATION.json",
        dict(
            complete=len(completed) == 6,
            files=completed,
            n_base_path_records_processed=6 * 2 * n,
            n_base_path_records_planned=6 * 2 * n,
            n_skipped=0,
            actual_call_records=calls,
            internal_wall_seconds=elapsed,
            framework=dict(
                python=sys.version,
                torch=torch.__version__,
                device=torch.cuda.get_device_name(device),
            ),
            target="Numerical endpoint law of this frozen model; not real CIFAR data distribution",
        ),
    )


def analyze(args, protocol: dict) -> None:
    start = time.monotonic()
    generation = json.loads((args.out / "GENERATION.json").read_text())
    if not generation["complete"] or generation["n_skipped"]:
        raise RuntimeError("Incomplete generation cannot enter analysis")
    n = protocol["n_per_cohort"]
    rows, controls, convergence = [], [], []
    for seed in SEEDS:
        data = {}
        for resolution in (1, 2):
            path = args.out / "raw" / f"s{seed}_r{resolution}.npz"
            record = next(
                x
                for x in generation["files"]
                if x["seed"] == seed and x["resolution"] == resolution
            )
            assert sha(path) == record["sha256"]
            data[resolution] = {k: v for k, v in np.load(path).items()}
            value = data[resolution]
            endpoint = value["endpoint"]
            endpoint_control = discrepancy(endpoint[:n], endpoint[n:])
            for index, m in enumerate(TIMES):
                mid = value[f"mid_{index}"]
                mid_control = discrepancy(mid[:n], mid[n:])
                replay_error = float(
                    np.max(np.abs(value[f"output_{index}_true_path_replay"] - endpoint[:n]))
                )
                controls.append(
                    dict(
                        seed=seed,
                        resolution=resolution,
                        time=m,
                        intermediate=mid_control,
                        endpoint=endpoint_control,
                        true_path_replay_max_abs_error=replay_error,
                    )
                )
                for arm in ARMS:
                    boundary, output = (
                        value[f"boundary_{index}_{arm}"],
                        value[f"output_{index}_{arm}"],
                    )
                    intermediate, end = (
                        discrepancy(boundary, mid[n:]),
                        discrepancy(output, endpoint[n:]),
                    )
                    row = dict(
                        seed=seed,
                        resolution=resolution,
                        time=m,
                        arm=arm,
                        intermediate=intermediate,
                        endpoint=end,
                        intermediate_baseline=mid_control,
                        endpoint_baseline=endpoint_control,
                        paired_boundary_RMS=float(
                            np.sqrt(np.mean((boundary.astype(np.float64) - mid[:n]) ** 2))
                        ),
                        paired_endpoint_RMS=float(
                            np.sqrt(np.mean((output.astype(np.float64) - endpoint[:n]) ** 2))
                        ),
                    )
                    for stage, result, baseline in [
                        ("intermediate", intermediate, mid_control),
                        ("endpoint", end, endpoint_control),
                    ]:
                        row[f"{stage}_V_MMD2_excess"] = {
                            str(width): result["rbf"][str(width)]["V_MMD2"]
                            - baseline["rbf"][str(width)]["V_MMD2"]
                            for width in BANDWIDTHS
                        }
                        row[f"{stage}_empirical_W2_RMS_excess"] = (
                            result["empirical_W2_RMS"] - baseline["empirical_W2_RMS"]
                        )
                    rows.append(row)
        for key in ["endpoint", "mid_0", "mid_1", "mid_2"]:
            delta = data[2][key].astype(np.float64) - data[1][key]
            convergence.append(
                dict(seed=seed, state=key, coarse_fine_paired_RMS=float(np.sqrt((delta**2).mean())))
            )
    result = dict(
        planned_intervention_cells=36,
        processed_intervention_cells=len(rows),
        skipped=0,
        n_per_cohort=n,
        seeds=list(SEEDS),
        rows=rows,
        controls=controls,
        numerical_resolution_sensitivity=convergence,
        CPU_wall_seconds=time.monotonic() - start,
        primary="Raw-pixel RBF empirical V-MMD squared, bandwidth sqrt(d); finite-cohort excess relative to independent true-path cohort",
        scope="Descriptive single frozen checkpoint, three generation seeds; not population W2 bounds, image quality, training replication, novelty certification or an improved sampler",
    )
    assert len(rows) == 36 and len(controls) == 18
    write(args.out / "RESULTS.json", result)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ["rows", "controls", "numerical_resolution_sensitivity"]
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--phase", choices=["generate", "analyze"], required=True)
    parser.add_argument("--max-records", type=int, choices=[128], required=True)
    parser.add_argument(
        "--seed",
        type=int,
        choices=[201],
        required=True,
        help="Identifies the locked seed series201/202/203, not one selected seed",
    )
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text())
    assert protocol["source_sha256"][str(Path(__file__).relative_to(ROOT))] == sha(Path(__file__))
    assert args.max_records == protocol["n_per_cohort"]
    if args.phase == "generate":
        assert sha(ROOT / protocol["weights_path"]) == protocol["weights_sha256"]
        assert not (args.out / "GENERATION.json").exists()
        write(
            args.out / "METADATA.json",
            dict(
                started_utc=datetime.now(UTC).isoformat(),
                argv=sys.argv,
                protocol_sha256=sha(args.protocol),
                config=str(args.protocol),
                seed_policy=list(SEEDS),
                n_per_cohort=128,
                n_base_paths_planned=1536,
                max_records_per_cohort=128,
                device="cuda:0",
                hard_outer_wall_seconds=500,
                output_dir=str(args.out),
                environment=sys.executable,
                base_commit=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                gpu_snapshot=subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=index,name,memory.free,utilization.gpu",
                        "--format=csv,noheader",
                    ],
                    text=True,
                ),
            ),
        )
        generate(args, protocol)
    else:
        analyze(args, protocol)


if __name__ == "__main__":
    main()

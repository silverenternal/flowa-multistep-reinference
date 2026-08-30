"""Compute InceptionV3 FID between two .npz sample sets (CIFAR-10 32x32).

Both .npz files are expected to contain key 'samples' with shape
(N, 3, 32, 32) float32/float64 arrays in [-1, 1]. The script:
  1. Loads InceptionV3 (2048-d pool3 features) once.
  2. Maps [-1, 1] -> [0, 1] and ImageNet-normalises.
  3. Bilinearly resizes to 299x299.
  4. Returns Fréchet distance on activation Gaussians.

Usage:
    python compute_cifar_fid.py <gen.npz> <ref.npz> [<gen.npz> <ref.npz> ...]

Each pair prints "=== FID: <value> ===" on its own line; the orchestrator
in tools/run_sota_cifar_experiment.py greps that line.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from pytorch_fid.inception import InceptionV3
from scipy import linalg


def get_activations(samples: np.ndarray, model: InceptionV3, batch_size: int = 32) -> np.ndarray:
    """Run InceptionV3 on a batch of (N, 3, 32, 32) float arrays in [-1, 1]."""
    model.eval()
    n = samples.shape[0]
    activations = np.empty((n, 2048), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, n, batch_size):
            batch = samples[i : i + batch_size]
            x = torch.from_numpy(np.ascontiguousarray(batch)).float()
            # (N, 3, 32, 32) already 3-channel
            x = (x + 1.0) / 2.0  # [-1, 1] -> [0, 1]
            x = torch.nn.functional.interpolate(
                x, size=(299, 299), mode="bilinear", align_corners=False
            )
            mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
            std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
            x = (x - mean) / std
            pred = model(x)[0]  # (B, 2048, 1, 1)
            pred = pred.squeeze(3).squeeze(2)  # (B, 2048)
            activations[i : i + batch_size] = pred.cpu().numpy()
    return activations


def calculate_frechet_distance(act1: np.ndarray, act2: np.ndarray) -> float:
    """Standard Fréchet distance between two Gaussian fits."""
    mu1, sigma1 = act1.mean(axis=0), np.cov(act1, rowvar=False)
    mu2, sigma2 = act2.mean(axis=0), np.cov(act2, rowvar=False)
    diff = mu1 - mu2
    covmean = linalg.sqrtm(sigma1.dot(sigma2))
    if not np.isfinite(covmean).all():
        offset = np.eye(sigma1.shape[0]) * 1e-6
        covmean = linalg.sqrtm((sigma1 + offset).dot(sigma2 + offset))
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    return float(diff.dot(diff) + np.trace(sigma1) + np.trace(sigma2) - 2 * np.trace(covmean))


def compute_fid_for_pair(gen_path: Path, ref_path: Path) -> float:
    gen = np.load(gen_path)["samples"]
    ref = np.load(ref_path)["samples"]
    n = min(int(gen.shape[0]), int(ref.shape[0]))
    gen = np.asarray(gen[:n], dtype=np.float32)
    ref = np.asarray(ref[:n], dtype=np.float32)
    block_idx = InceptionV3.BLOCK_INDEX_BY_DIM[2048]
    model = InceptionV3([block_idx])
    model.eval()
    a_gen = get_activations(gen, model)
    a_ref = get_activations(ref, model)
    return calculate_frechet_distance(a_gen, a_ref)


def main() -> None:
    if len(sys.argv) < 3 or (len(sys.argv) - 1) % 2 != 0:
        print("Usage: python compute_cifar_fid.py <gen1.npz> <ref1.npz> [<gen2.npz> <ref2.npz> ...]")
        sys.exit(1)
    args = sys.argv[1:]
    pairs = list(zip(args[0::2], args[1::2], strict=False))
    # Cache the model load across pairs to avoid 95MB download × N
    block_idx = InceptionV3.BLOCK_INDEX_BY_DIM[2048]
    model = InceptionV3([block_idx])
    model.eval()
    results: list[tuple[Path, Path, float]] = []
    for gen_str, ref_str in pairs:
        gen_path, ref_path = Path(gen_str), Path(ref_str)
        gen = np.load(gen_path)["samples"]
        ref = np.load(ref_path)["samples"]
        n = min(int(gen.shape[0]), int(ref.shape[0]))
        a_gen = get_activations(np.asarray(gen[:n], dtype=np.float32), model)
        a_ref = get_activations(np.asarray(ref[:n], dtype=np.float32), model)
        fid = calculate_frechet_distance(a_gen, a_ref)
        results.append((gen_path, ref_path, fid))
        print(f"=== FID ({gen_path.name} vs {ref_path.name}): {fid:.4f} ===", flush=True)
    # Final headline
    if len(results) == 1:
        print(f"=== FID: {results[0][2]:.4f} ===")


if __name__ == "__main__":
    main()

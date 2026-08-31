"""Compute InceptionV3 FID between two .npz sample sets (CIFAR-10 32x32).

Both .npz files are expected to contain key 'samples' with shape
(N, 3, 32, 32) float32/float64 arrays in [-1, 1]. The script:
  1. Loads InceptionV3 (2048-d pool3 features) via torchvision.
  2. Maps [-1, 1] -> [0, 1] and ImageNet-normalises.
  3. Bilinearly resizes to 299x299.
  4. Returns Fréchet distance on activation Gaussians via the
     canonical :class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator`.

Usage:
    python compute_cifar_fid.py <gen.npz> <ref.npz> [<gen.npz> <ref.npz> ...]

Each pair prints "=== FID: <value> ===" on its own line; the orchestrator
in tools/run_sota_cifar_experiment.py greps that line.

The Fréchet arithmetic (covariance square root + numerical guards) was
previously a near-duplicate of :func:`tools.eval_rf_cifar.compute_fid`
and :func:`tools.run_image_eval.compute_fid_from_features`. Both
copies have now been folded into
:class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator
._compute_frechet_distance_inner`; this script is a thin CLI wrapper
around the shared abstraction.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

# Make the project importable when running as ``python
# tools/compute_cifar_fid.py``.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from adaptive_reflow.eval.fid import InceptionV3FIDEvaluator  # noqa: E402


def get_activations(samples: np.ndarray, model: torch.nn.Module, batch_size: int = 32) -> np.ndarray:
    """Run InceptionV3 on a batch of (N, 3, 32, 32) float arrays in [-1, 1].

    The model is a torchvision ``inception_v3`` with ``weights=None``,
    ``aux_logits=False`` and ``fc = Identity`` (the canonical FID
    shape — see :func:`tools.eval_rf_cifar.extract_inception_features`
    and commit ``2fb3dc0`` for the regression rationale).
    """
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
            feats = model(x)
            activations[i : i + batch_size] = feats.cpu().numpy()
    return activations


def calculate_frechet_distance(act1: np.ndarray, act2: np.ndarray) -> float:
    """Standard Fréchet distance between two Gaussian fits.

    Thin back-compat wrapper around
    :class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator
    .compute_from_features`. Returns ``float('nan')`` when either
    operand has fewer than 2 rows (FID is undefined there).
    """
    evaluator = InceptionV3FIDEvaluator(feature_dim=int(act1.shape[1]))
    return float(
        evaluator.compute_from_features(
            act2.astype(np.float64, copy=False),
            act1.astype(np.float64, copy=False),
        ).value
    )


def _load_inception_v3_for_fid() -> torch.nn.Module:
    """Build the canonical ``torchvision`` InceptionV3 for FID.

    Mirrors the construction in
    :func:`tools.eval_rf_cifar.extract_inception_features` and
    :func:`tools.run_image_eval.load_inception_for_fid`: ``weights=None``,
    ``aux_logits=False``, ``fc = Identity`` so the forward returns the
    2048-dim pool3 features directly.
    """
    import torch.nn as nn
    import torchvision.models as tvm

    model = tvm.inception_v3(weights=None, aux_logits=False, transform_input=False)
    model.fc = nn.Identity()
    model.eval()
    return model


def compute_fid_for_pair(gen_path: Path, ref_path: Path) -> float:
    gen = np.load(gen_path)["samples"]
    ref = np.load(ref_path)["samples"]
    n = min(int(gen.shape[0]), int(ref.shape[0]))
    gen = np.asarray(gen[:n], dtype=np.float32)
    ref = np.asarray(ref[:n], dtype=np.float32)
    model = _load_inception_v3_for_fid()
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
    model = _load_inception_v3_for_fid()
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
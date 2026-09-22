"""Offline materialiser for ``data/mnist_fm.npz`` (EXP-1).

Trains a small NumPy UNet on MNIST and writes the weights to the
canonical ``data/mnist_fm.npz`` path. The full production training run
takes ~30-40 minutes on a single CPU core (3 epochs at batch 64 with
``base_channels=16``, full 60K images); see the ``PRODUCTION_RECIPE``
constants block below for the canonical recipe. This materialiser is
the entry point for:

- The **smoke materialisation** used by the test suite (1 epoch on a
  1000-image subset, base_channels=8).
- The **production materialisation** invoked by
  ``tools/run_ablation.py --include-mnist`` and by the Wave 275 P3.5
  R5c sweep (3 epochs, base_channels=16, full 60K images).
- Re-materialisation when ``data/mnist_fm.npz`` is missing or was
  materialized with the smoke recipe (the production ckpt is ~75 KB;
  the smoke ckpt is ~22 KB; the 50 KB threshold in
  ``scripts/wave191_p3_mnist_sweep.py:397`` auto-detects which is
  loaded).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adaptive_reflow.adapters.mnist_fm_train import (  # noqa: E402
    save_weights,
    train,
)

# ---------------------------------------------------------------------------
# Production recipe — Wave 275 P3.5 R5c closure
# ---------------------------------------------------------------------------
# Canonical production-ckpt recipe for the MNIST FM adapter. Used by:
#   - tools/materialize_mnist_fm.py (this file) — invoked via:
#       rm data/mnist_fm.npz && python tools/materialize_mnist_fm.py
#       (the existing ensure_canonical_files() helper skips training if
#        the ckpt already exists, so the smoke ckpt must be removed first)
#   - scripts/wave191_p3_mnist_sweep.py — reads the production ckpt at
#     `data/mnist_fm.npz` (auto-detects smoke vs production via the
#     50_000-byte threshold at line 397 of the sweep script)
#   - docs/CLAIMS.md CLM-059 / CLM-060 / CLM-066 / CLM-069 R5c row —
#     upgrade from PROVISIONAL to ACTIVE after the sweep re-run lands
#
# Why this is the canonical recipe:
#   - epochs=3 (3 full passes over the 60K-image MNIST training set;
#     the smoke ckpt at epochs=1 is intentionally under-trained for
#     the Wave 191 P3 1-2 h budget)
#   - base_channels=16 (the canonical UNet width; the smoke ckpt at
#     base_channels=8 has ~25% of the production-ckpt parameters)
#   - max_train_images=60000 (the full MNIST training set; the smoke
#     ckpt at 6000 images is 10% of the production-ckpt training set)
#   - batch_size=64, lr=1e-3, seed=42 (the canonical Adam optimizer
#     configuration; matches the Wave 41 / Wave 52 production ckpt
#     reading documented at docs/CLAIMS.md:2919)
#
# Wall-clock budget: 30-40 minutes on a single CPU core (per the
# module docstring at lines 1-10). The ckpt output is ~75 KB
# (vs. the smoke ckpt's 22 KB); the 50 KB threshold in
# scripts/wave191_p3_mnist_sweep.py:397 cleanly separates smoke from
# production.
PRODUCTION_RECIPE: dict[str, int | None] = {
    "epochs": 3,
    "batch_size": 64,
    "lr": 1e-3,
    "base_channels": 16,
    "seed": 42,
    "max_train_images": 60_000,  # full MNIST train set (the
                                 # adaptive_reflow.adapters.mnist_fm_train
                                 # .train() function treats 60_000 the
                                 # same as None — both slice the full
                                 # 60K-image array)
}


def ensure_canonical_files(
    *,
    epochs: int = 3,
    batch_size: int = 64,
    base_channels: int = 16,
    lr: float = 1e-3,
    seed: int = 42,
    cache_dir: Path = REPO_ROOT / "data" / "mnist_cache",
    output: Path = REPO_ROOT / "data" / "mnist_fm.npz",
    max_train_images: int | None = None,
) -> Path:
    """Train + save ``data/mnist_fm.npz`` if missing. Returns the output path."""
    if output.exists() and output.stat().st_size > 0:
        print(f"[materialize_mnist_fm] {output} already exists; skipping training", flush=True)
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    print(
        f"[materialize_mnist_fm] training: epochs={epochs} batch={batch_size} "
        f"base_channels={base_channels} lr={lr} seed={seed} -> {output}",
        flush=True,
    )
    t0 = time.perf_counter()
    weights = train(
        epochs=int(epochs),
        batch_size=int(batch_size),
        lr=float(lr),
        base_channels=int(base_channels),
        seed=int(seed),
        cache_dir=cache_dir,
        max_train_images=max_train_images,
    )
    elapsed = time.perf_counter() - t0
    save_weights(weights, output)
    print(
        f"[materialize_mnist_fm] saved {output} ({output.stat().st_size} bytes) "
        f"in {elapsed:.1f}s",
        flush=True,
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="materialize_mnist_fm",
        description="Train + save the MNIST rectified-flow UNet.",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--base-channels", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cache-dir", type=Path, default=REPO_ROOT / "data" / "mnist_cache")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "data" / "mnist_fm.npz")
    parser.add_argument("--max-train-images", type=int, default=None)
    args = parser.parse_args(argv)
    ensure_canonical_files(
        epochs=int(args.epochs),
        batch_size=int(args.batch_size),
        base_channels=int(args.base_channels),
        lr=float(args.lr),
        seed=int(args.seed),
        cache_dir=Path(args.cache_dir),
        output=Path(args.output),
        max_train_images=args.max_train_images,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover — CLI entry point
    raise SystemExit(main())

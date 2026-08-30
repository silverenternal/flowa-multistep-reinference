"""Offline materialiser for ``data/mnist_fm.npz`` (EXP-1).

Trains a small NumPy UNet on MNIST and writes the weights to the
canonical ``data/mnist_fm.npz`` path. The full training run takes
~30-40 minutes on a single CPU core (3 epochs at batch 64 with
``base_channels=16``); this materialiser is the entry point for both
the smoke materialisation used by the test suite (1 epoch on a 1000-
image subset) and the production materialisation invoked by
``tools/run_ablation.py --include-mnist``.
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

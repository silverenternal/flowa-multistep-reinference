"""Extract MNIST test images and save as numpy for FID reference.

Reads the MNIST IDX file format directly (no torch / no torchvision).
"""
from __future__ import annotations

import gzip
import struct
from pathlib import Path

import numpy as np


def read_idx_images(path: Path) -> np.ndarray:
    """Read MNIST IDX image file. Returns (N, 28, 28) uint8. Handles .gz."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rb") as f:
        magic, n, h, w = struct.unpack(">IIII", f.read(16))
        assert magic == 2051, f"Expected magic 2051, got {magic}"
        data = np.frombuffer(f.read(), dtype=np.uint8)
        return data.reshape(n, h, w)


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mnist-dir", default="data/mnist_cache/MNIST/raw")
    p.add_argument("--n", type=int, default=1000, help="Number of test images")
    p.add_argument("--out", default="/tmp/mnist_test_ref.npz")
    args = p.parse_args()

    test_path = Path(args.mnist_dir) / "t10k-images-idx3-ubyte.gz"
    if not test_path.exists():
        # Try without .gz
        test_path = Path(args.mnist_dir) / "t10k-images-idx3-ubyte"
    if not test_path.exists():
        raise FileNotFoundError(f"MNIST test images not found in {args.mnist_dir}")

    print(f"Reading MNIST test images from {test_path}...")
    images = read_idx_images(test_path)
    print(f"Loaded {len(images)} images, shape: {images.shape}, dtype: {images.dtype}")

    # Take first n
    images = images[: args.n]
    print(f"Using first {len(images)} images")

    # Save as float32 in [-1, 1] to match generated samples
    images_f = (images.astype(np.float32) / 127.5) - 1.0
    print(f"Normalized to [{images_f.min():.3f}, {images_f.max():.3f}]")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, samples=images_f)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()

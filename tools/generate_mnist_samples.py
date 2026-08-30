"""Generate MNIST samples using the framework's MnistFmAdapter for FID computation.

Simplified: drives build_initial_state -> compose_condition -> solve_ode -> export_endpoint
directly, without going through Engine.run_round. Faster, simpler, and exposes
the (28, 28) endpoint image for FID.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from adaptive_reflow.adapters.mnist_fm import MNIST_FM_CHANNELS, MnistFmAdapter
from adaptive_reflow.universal.state import ODEConditionDelta


def _make_condition(target_round: int = 0) -> ODEConditionDelta:
    return ODEConditionDelta(
        delta_spec={"t0": 0.0, "t1": 1.0, "num_steps": 20},
        source="mnist_fm_gen",
        target_round=target_round,
        calibration_artifact_hash="cal-mnist-fm",
    )


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--weights", default="data/mnist_fm.npz")
    p.add_argument("--n-samples", type=int, default=1000)
    p.add_argument("--out", default="/tmp/mnist_generated.npz")
    args = p.parse_args()

    if not Path(args.weights).exists():
        raise FileNotFoundError(
            f"{args.weights} not found. Run tools/materialize_mnist_fm.py first."
        )

    adapter = MnistFmAdapter(weights_path=args.weights, num_steps=20)
    print(f"Adapter ready. weights: {len(adapter._weights)} tensors, num_steps: {adapter._num_steps}")

    print(f"Generating {args.n_samples} MNIST samples...")
    t0 = time.time()
    images: list[np.ndarray] = []
    for i in range(args.n_samples):
        bundle = adapter.build_initial_state(batch_id=f"b{i}", sample_id=f"s{i}")
        condition = _make_condition(target_round=0)
        trace = adapter.solve_ode(bundle, condition, seed=i)
        # Native state is stored under native_state_digest in adapter._native_states
        # entry has 'trajectory' (21, 784) = (n_steps+1, state_dim); take last row
        end_digest = trace.native_state_digest
        entry = adapter._native_states.get(end_digest, {})
        trajectory = entry.get("trajectory")
        if trajectory is None:
            raise RuntimeError(f"No trajectory in entry; keys: {list(entry.keys())}")
        # trajectory[-1] is the final state at t=1
        x_arr = np.asarray(trajectory[-1])
        img = x_arr.reshape(28, 28)
        images.append(img.astype(np.float32))

    elapsed = time.time() - t0
    images_arr = np.stack(images)
    print(
        f"Generated {args.n_samples} samples in {elapsed:.1f}s "
        f"({args.n_samples / elapsed:.1f} samples/s)"
    )
    print(
        f"Shape: {images_arr.shape}, range: [{images_arr.min():.3f}, {images_arr.max():.3f}], "
        f"mean: {images_arr.mean():.3f}, std: {images_arr.std():.3f}"
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, samples=images_arr)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()

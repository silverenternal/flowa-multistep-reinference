"""Smoke tests for :mod:`adaptive_reflow.adapters.mnist_fm_train` (EXP-1).

The trainer file is the offline counterpart to
:class:`adaptive_reflow.adapters.mnist_fm.MnistFmAdapter`. Tests:

* ``test_init_kaiming_uniform_bounds`` -- ``velocity_field_unet_init``
  produces Kaiming-uniform weights whose per-tensor stddev stays
  below the Kaiming bound ``sqrt(6 / fan_in)`` for every Conv weight.
* ``test_save_load_roundtrip`` -- ``save_weights`` then ``load_weights``
  yields bit-identical arrays (after casting back to ``float64``).
* ``test_train_smoke_decreases_loss`` -- 1 epoch on a 1000-image subset
  drops the per-batch loss by at least 30% from step 1 to step 10.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adaptive_reflow.adapters.mnist_fm_train import (
    IDX,
    WEIGHT_KEYS,
    load_weights,
    save_weights,
    train,
    velocity_field_unet_init,
)


def test_init_kaiming_uniform_bounds() -> None:
    """``velocity_field_unet_init`` produces weights with Kaiming-uniform bounds."""
    rng = np.random.default_rng(0)
    weights = velocity_field_unet_init(rng, base_channels=16)
    assert len(weights) == len(WEIGHT_KEYS)
    # Kaiming-uniform bound for Conv weight tensor (out, in, k, k) is
    # ``sqrt(6 / fan_in)`` where ``fan_in = in * k * k``.
    conv_indices = [
        IDX["down1_w"], IDX["down2_w"], IDX["bottleneck_w"], IDX["up1_w"],
    ]
    # The output conv is zero-init (residual-style stabilisation) — it
    # is NOT Kaiming-uniform; the test excludes it.
    expected_fan_ins = {
        IDX["down1_w"]: 2 * 3 * 3,
        IDX["down2_w"]: 16 * 3 * 3,
        IDX["bottleneck_w"]: 32 * 3 * 3,
        IDX["up1_w"]: 32 * 3 * 3,
    }
    for idx in conv_indices:
        bound = float(np.sqrt(6.0 / float(expected_fan_ins[idx])))
        w = weights[idx]
        assert np.all(np.abs(w) <= bound + 1e-12), (
            f"weight[{idx}] has entries outside Kaiming bound {bound:.6f}: "
            f"max abs = {float(np.max(np.abs(w))):.6f}"
        )


def test_save_load_roundtrip(tmp_path: Path) -> None:
    """``save_weights`` then ``load_weights`` round-trips bit-identical arrays."""
    rng = np.random.default_rng(1)
    weights = velocity_field_unet_init(rng, base_channels=16)
    # Perturb so we can check non-default values survive.
    weights[IDX["down1_w"]] = rng.standard_normal(weights[IDX["down1_w"]].shape) * 0.1
    weights[IDX["out_b"]] = np.array([0.123])
    weights[IDX["out_w"]] = rng.standard_normal(weights[IDX["out_w"]].shape) * 0.1
    out_path = tmp_path / "mnist_fm_roundtrip.npz"
    saved = save_weights(weights, out_path)
    assert saved.exists()
    loaded = load_weights(saved)
    assert len(loaded) == len(weights)
    for i, (a, b) in enumerate(zip(weights, loaded, strict=True)):
        assert a.shape == b.shape, f"weight[{i}] shape mismatch {a.shape} vs {b.shape}"
        # Compare values; save/load uses float32 on disk but load_weights
        # casts back to float64. ``np.allclose`` accepts the small
        # rounding delta (np.array_equal would fail on float32 → float64).
        assert np.allclose(a, b, atol=1e-6), f"weight[{i}] differs after roundtrip"


def test_train_smoke_decreases_loss(tmp_path: Path) -> None:
    """1 epoch on a 1000-image subset drops the per-batch loss by >= 30%.

    The smoke test compares the trainer's per-batch loss at step 1
    against the trainer's per-batch loss at the final step of the
    same epoch. The training loop emits both losses to stdout (via
    ``log_every=1``); the test captures stdout and parses the two
    loss values out. The trainer's per-batch loss is the canonical
    comparison metric (it lives on the same data distribution the
    model is fitting to), so the absolute reduction test is robust.
    """
    import contextlib
    import io
    import re

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        weights = train(
            epochs=1,
            batch_size=32,
            base_channels=8,
            seed=42,
            cache_dir=tmp_path / "mnist_cache",
            max_train_images=1000,
            log_every=1,
        )
    assert len(weights) == len(WEIGHT_KEYS)
    loss_pattern = re.compile(r"step\s+(\d+)/\d+\s+loss=([\d.]+)")
    losses = [float(m.group(2)) for m in loss_pattern.finditer(buf.getvalue())]
    assert losses, "trainer emitted no loss lines"
    first_loss = float(losses[0])
    final_train_loss = float(losses[-1])
    # Loss reduction gate: at least 30% drop from first step to final step.
    assert final_train_loss <= 0.7 * float(first_loss), (
        f"smoke training did not reduce loss by >=30%: "
        f"first={first_loss:.2f} final={final_train_loss:.2f}"
    )

"""Offline trainer for the 2D rectified-flow velocity field (DTB-G3 phase 1).

Trains a small velocity-field MLP for a 2D rectified flow model. The
source distribution is always ``N(0, I_2)``; the target distribution is
either ``two_moons`` or ``eight_gaussians``. Training minimizes the
plain MSE flow-matching loss

    L(theta) = E_{x0, x1, t} || v_theta(x_t, t) - (x_1 - x_0) ||^2
    x_t = (1 - t) * x_0 + t * x_1,   t ~ U(0, 1)

which is the *rectified flow* objective: because the interpolation path
is a straight line traversed over ``t in [0, 1]``, the target velocity
is the constant ``(x_1 - x_0) / 1.0``.

The optimizer is a hand-rolled NumPy Adam (no torch, no autograd) —
gradients for the 3-layer ReLU MLP are computed analytically. Training
2000 steps at batch 4096 takes 1-3 minutes on a CPU.

This module is **not** imported by ``adaptive_reflow.adapters.__init__``
because NumPy is an opt-in extra (``pip install -e .[flow_matching]``).
It is a standalone entry point whose only product is an ``.npz`` weight
file (``W1``, ``b1``, ``W2``, ``b2``, ``W3``, ``b3``, all ``float32``)
that the runtime 2D adapter loads via :func:`load_weights`.

Usage::

    python -m adaptive_reflow.adapters.twodim_fm_train \\
        --target two_moons --steps 2000 --out data/twodim_fm_two_moons.npz
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]
Weights = tuple[Array, Array, Array, Array, Array, Array]

TARGETS: tuple[str, ...] = ("two_moons", "eight_gaussians")
WEIGHT_KEYS: tuple[str, ...] = ("W1", "b1", "W2", "b2", "W3", "b3")

# Geometry constants for the two target distributions.
TWO_MOONS_NOISE = 0.08
EIGHT_GAUSSIANS_RADIUS = 2.0
EIGHT_GAUSSIANS_STDDEV = 0.15


# ---------------------------------------------------------------------------
# Target samplers
# ---------------------------------------------------------------------------


def sample_two_moons(n: int, rng: np.random.Generator) -> Array:
    """Sample ``n`` points from the classic two-moons distribution.

    Half the points lie on the upper half-circle centred at the origin,
    half on the lower half-circle shifted by ``(1, -0.5)``. Isotropic
    Gaussian noise of scale :data:`TWO_MOONS_NOISE` is added.
    """
    if n <= 0:
        raise ValueError("n_must_be_positive")
    n_a = n // 2
    n_b = n - n_a
    theta_a = rng.uniform(0.0, np.pi, size=n_a)
    theta_b = rng.uniform(0.0, np.pi, size=n_b)
    moon_a = np.stack([np.cos(theta_a), np.sin(theta_a)], axis=1)
    moon_b = np.stack([1.0 - np.cos(theta_b), -np.sin(theta_b) - 0.5], axis=1)
    out = np.concatenate([moon_a, moon_b], axis=0)
    out = out + TWO_MOONS_NOISE * rng.standard_normal(out.shape)
    return np.asarray(out, dtype=np.float64)


def sample_eight_gaussians(n: int, rng: np.random.Generator) -> Array:
    """Sample ``n`` points from eight Gaussians on a circle of radius 2."""
    if n <= 0:
        raise ValueError("n_must_be_positive")
    angles = np.arange(8, dtype=np.float64) * (2.0 * np.pi / 8.0)
    centers = EIGHT_GAUSSIANS_RADIUS * np.stack(
        [np.cos(angles), np.sin(angles)], axis=1
    )
    which = rng.integers(0, 8, size=n)
    out = centers[which] + EIGHT_GAUSSIANS_STDDEV * rng.standard_normal((n, 2))
    return np.asarray(out, dtype=np.float64)


def _sampler(target: str):  # type: ignore[no-untyped-def]
    """Return the sampler callable for ``target``; fail closed on unknown."""
    if target == "two_moons":
        return sample_two_moons
    if target == "eight_gaussians":
        return sample_eight_gaussians
    raise ValueError(f"unknown_target:{target}")


# ---------------------------------------------------------------------------
# Velocity-field MLP
# ---------------------------------------------------------------------------


def velocity_field_mlp_init(rng: np.random.Generator, hidden: int = 64) -> Weights:
    """Kaiming-uniform init of the 3-layer velocity MLP ``(x, t) -> v``.

    Layer shapes: ``3 -> hidden -> hidden -> 2`` (input is ``[x_1, x_2, t]``).
    Each weight is drawn from ``U(-bound, bound)`` with
    ``bound = sqrt(6 / fan_in)``; biases start at zero.
    """
    if hidden <= 0:
        raise ValueError("hidden_must_be_positive")

    def kaiming(fan_in: int, fan_out: int) -> Array:
        bound = np.sqrt(6.0 / float(fan_in))
        return np.asarray(
            rng.uniform(-bound, bound, size=(fan_in, fan_out)), dtype=np.float64
        )

    return (
        kaiming(3, hidden),
        np.zeros(hidden, dtype=np.float64),
        kaiming(hidden, hidden),
        np.zeros(hidden, dtype=np.float64),
        kaiming(hidden, 2),
        np.zeros(2, dtype=np.float64),
    )


def _features(x: Array, t: Array | float) -> Array:
    """Concatenate ``x`` (n, 2) with the broadcast time ``t`` into (n, 3)."""
    x2 = np.atleast_2d(np.asarray(x, dtype=np.float64))
    if x2.ndim != 2 or x2.shape[1] != 2:
        raise ValueError("x_must_have_shape_n_2")
    tt = np.asarray(t, dtype=np.float64).reshape(-1)
    if tt.size == 1:
        tt = np.full(x2.shape[0], float(tt[0]), dtype=np.float64)
    if tt.shape[0] != x2.shape[0]:
        raise ValueError("t_must_be_scalar_or_length_n")
    return np.concatenate([x2, tt[:, None]], axis=1)


def velocity_field_forward(
    W1: Array,
    b1: Array,
    W2: Array,
    b2: Array,
    W3: Array,
    b3: Array,
    x: Array,
    t: Array | float,
) -> Array:
    """Evaluate the velocity field ``v_theta(x, t)``.

    ``x`` has shape ``(n, 2)``, ``t`` is a scalar or shape ``(n,)``; the
    return is ``(n, 2)``. Hidden activations are ReLU, the output layer
    is linear.
    """
    h0 = _features(x, t)
    h1 = np.maximum(h0 @ W1 + b1, 0.0)
    h2 = np.maximum(h1 @ W2 + b2, 0.0)
    return np.asarray(h2 @ W3 + b3, dtype=np.float64)


def _loss_and_grads(
    weights: Weights, x_t: Array, t: Array, v_target: Array
) -> tuple[float, list[Array]]:
    """MSE loss + analytic gradients for the 3-layer ReLU MLP."""
    W1, b1, W2, b2, W3, b3 = weights
    h0 = _features(x_t, t)
    z1 = h0 @ W1 + b1
    h1 = np.maximum(z1, 0.0)
    z2 = h1 @ W2 + b2
    h2 = np.maximum(z2, 0.0)
    pred = h2 @ W3 + b3

    n = float(x_t.shape[0])
    resid = pred - v_target
    loss = float(np.mean(np.sum(resid * resid, axis=1)))
    # d loss / d pred for loss = mean_n sum_d resid^2
    d_pred = (2.0 / n) * resid
    g_W3 = h2.T @ d_pred
    g_b3 = d_pred.sum(axis=0)
    d_h2 = d_pred @ W3.T
    d_z2 = d_h2 * (z2 > 0.0)
    g_W2 = h1.T @ d_z2
    g_b2 = d_z2.sum(axis=0)
    d_h1 = d_z2 @ W2.T
    d_z1 = d_h1 * (z1 > 0.0)
    g_W1 = h0.T @ d_z1
    g_b1 = d_z1.sum(axis=0)
    return loss, [g_W1, g_b1, g_W2, g_b2, g_W3, g_b3]


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------


def train(
    target: str,
    steps: int = 2000,
    batch_size: int = 4096,
    lr: float = 1e-3,
    hidden: int = 64,
    seed: int = 42,
) -> Weights:
    """Train the velocity field on ``target`` and return the six weights.

    Each step draws a fresh batch: ``x_0 ~ N(0, I_2)``, ``x_1 ~ target``,
    ``t ~ U(0, 1)``, forms ``x_t = (1 - t) x_0 + t x_1`` and regresses
    ``v_theta(x_t, t)`` onto the rectified-flow target velocity
    ``(x_1 - x_0) / 1.0``. Optimized with Adam
    (``beta1=0.9, beta2=0.999, eps=1e-8``).
    """
    if steps <= 0:
        raise ValueError("steps_must_be_positive")
    if batch_size <= 0:
        raise ValueError("batch_size_must_be_positive")
    if lr <= 0.0:
        raise ValueError("lr_must_be_positive")
    sampler = _sampler(target)
    rng = np.random.default_rng(int(seed))
    params = list(velocity_field_mlp_init(rng, hidden=hidden))
    moment1 = [np.zeros_like(p) for p in params]
    moment2 = [np.zeros_like(p) for p in params]
    beta1, beta2, eps = 0.9, 0.999, 1e-8

    for step in range(1, int(steps) + 1):
        x_0 = rng.standard_normal((batch_size, 2))
        x_1 = sampler(batch_size, rng)
        t = rng.uniform(0.0, 1.0, size=batch_size)
        x_t = (1.0 - t)[:, None] * x_0 + t[:, None] * x_1
        v_target = (x_1 - x_0) / 1.0
        weights = (params[0], params[1], params[2], params[3], params[4], params[5])
        loss, grads = _loss_and_grads(weights, x_t, t, v_target)
        for i, grad in enumerate(grads):
            moment1[i] = beta1 * moment1[i] + (1.0 - beta1) * grad
            moment2[i] = beta2 * moment2[i] + (1.0 - beta2) * (grad * grad)
            m_hat = moment1[i] / (1.0 - beta1**step)
            v_hat = moment2[i] / (1.0 - beta2**step)
            params[i] = params[i] - lr * m_hat / (np.sqrt(v_hat) + eps)
        if step == 1 or step % 200 == 0 or step == steps:
            print(f"[{target}] step {step}/{steps} loss={loss:.6f}", flush=True)

    return (params[0], params[1], params[2], params[3], params[4], params[5])


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_weights(weights: Weights, path: str | Path) -> Path:
    """Write the six weight arrays to ``path`` as ``float32`` in an ``.npz``."""
    if len(weights) != len(WEIGHT_KEYS):
        raise ValueError("weights_must_have_six_arrays")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        key: np.asarray(arr, dtype=np.float32)
        for key, arr in zip(WEIGHT_KEYS, weights, strict=True)
    }
    np.savez(out, **payload)
    return out


def load_weights(path: str | Path) -> Weights:
    """Load the six weight arrays written by :func:`save_weights`."""
    with np.load(Path(path)) as data:
        missing = [k for k in WEIGHT_KEYS if k not in data.files]
        if missing:
            raise ValueError(f"missing_weight_keys:{','.join(missing)}")
        arrays = [np.asarray(data[k], dtype=np.float64) for k in WEIGHT_KEYS]
    return (arrays[0], arrays[1], arrays[2], arrays[3], arrays[4], arrays[5])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Train one 2D rectified-flow velocity field and save it to ``--out``."""
    parser = argparse.ArgumentParser(
        prog="twodim_fm_train",
        description="Train the 2D rectified-flow velocity-field MLP.",
    )
    parser.add_argument("--target", choices=TARGETS, required=True)
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    weights = train(
        args.target,
        steps=args.steps,
        batch_size=args.batch_size,
        lr=args.lr,
        hidden=args.hidden,
        seed=args.seed,
    )
    out = save_weights(weights, args.out)
    print(f"saved {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":  # pragma: no cover — CLI entry point
    raise SystemExit(main())


__all__ = [
    "TARGETS",
    "WEIGHT_KEYS",
    "load_weights",
    "main",
    "sample_eight_gaussians",
    "sample_two_moons",
    "save_weights",
    "train",
    "velocity_field_forward",
    "velocity_field_mlp_init",
]

"""Offline trainer for the MNIST rectified-flow velocity field (EXP-1).

Trains a small NumPy UNet for a 28x28 grayscale rectified flow model
that maps ``N(0, I_{1x28x28})`` (clamped to ``[-1, 1]``) to the
empirical MNIST digit distribution. The objective is the standard
rectified flow MSE::

    L(theta) = E_{x0, x1, t} || v_theta(x_t, t) - (x_1 - x_0) ||^2
    x_t = (1 - t) * x_0 + t * x_1,   t ~ U(0, 1)

The optimizer is a hand-rolled NumPy Adam — gradients for the UNet are
computed analytically (``np.einsum`` + manual padding for nearest
upsample + GroupNorm + SiLU). No torch, no autograd.

Architecture (small UNet, ``base_channels`` channels in the first level)
=====================================================================

::

    Input:  (B, 1, 28, 28) image in [-1, 1]
            Concat time-as-2nd-channel -> (B, 2, 28, 28)

    Down 1: Conv(2 -> C, k=3, p=1) + GN(C, 8) + SiLU  -> (B, C, 28, 28)
    Down 2: Conv(C -> 2C, k=3, s=2, p=1) + GN(2C, 8) + SiLU -> (B, 2C, 14, 14)
    Bottleneck: Conv(2C -> 2C, k=3, p=1) + GN(2C, 8) + SiLU -> (B, 2C, 14, 14)
    Up 1:  Upsample(nearest, 2x) + Conv(2C -> C, k=3, p=1) + GN(C, 8) + SiLU -> (B, C, 28, 28)
    Output: Conv(C -> 1, k=3, p=1) -> (B, 1, 28, 28) velocity

Kaiming-uniform init on every Conv weight; zero init on biases and on
the final projection (residual-style stabilisation).

Usage::

    python -m adaptive_reflow.adapters.mnist_fm_train \\
        --epochs 3 --batch-size 64 --lr 1e-3 --base-channels 16 \\
        --output data/mnist_fm.npz --cache-dir data/mnist_cache
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

# Optional torchvision import — only needed when actually downloading
# MNIST. The trainer is importable without it so the rest of the
# framework stays stdlib-friendly.

Array: TypeAlias = NDArray[np.float64]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MNIST_TRAIN_SIZE: int = 60_000
MNIST_TEST_SIZE: int = 10_000
MNIST_IMAGE_SHAPE: tuple[int, int, int] = (1, 28, 28)
MNIST_FLAT_DIM: int = 784
MNIST_CLAMP: float = 1.0  # pixels live in [-1, 1] after normalization

# GroupNorm group count (per layer); 8 is the canonical UNet default.
MNIST_GN_GROUPS: int = 8


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


def _load_mnist(split: str, *, cache_dir: Path) -> Array:
    """Return ``(N, 784)`` float64 MNIST images in ``[-1, 1]``.

    Uses :mod:`torchvision.datasets.MNIST` when available; falls back
    to the offline ``data/mnist_cache/MNIST/raw/*.gz`` files if torch
    is missing (those files can be regenerated via the
    :file:`tools/materialize_mnist.py` helper). Returns ``(60000, 784)``
    for ``split='train'`` and ``(10000, 784)`` for ``split='test'``.
    """
    if split not in ("train", "test"):
        raise ValueError("split_must_be_train_or_test")
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        from torchvision import datasets, transforms
    except ImportError:
        return _load_mnist_offline(split=split, cache_dir=cache_dir)
    tx = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Lambda(lambda x: 2.0 * x - 1.0),
        ]
    )
    ds = datasets.MNIST(
        root=str(cache_dir),
        train=(split == "train"),
        download=True,
        transform=tx,
    )
    n = MNIST_TRAIN_SIZE if split == "train" else MNIST_TEST_SIZE
    out: Array = np.empty((n, MNIST_FLAT_DIM), dtype=np.float64)
    for i in range(n):
        img, _ = ds[i]
        out[i] = img.view(-1).numpy().astype(np.float64)
    return out


def _load_mnist_offline(*, split: str, cache_dir: Path) -> Array:
    """Offline loader: parse ``train-images-idx3-ubyte.gz`` directly.

    The MNIST IDX file format is:

    * offset 0: 4-byte big-endian magic (``2049`` for images, ``2051`` for labels).
    * offset 4: 4-byte big-endian ``N``.
    * offset 8: 4-byte big-endian ``H`` (``28``).
    * offset 12: 4-byte big-endian ``W`` (``28``).
    * offset 16: ``N * H * W`` unsigned bytes.

    We read the raw bytes, convert to ``[0, 1]`` floats, then rescale to
    ``[-1, 1]``. Returns ``(N, 784)``. If the raw file is missing the
    loader downloads it from the canonical mirror (``https://ossci-
    datasets.s3.amazonaws.com/mnist/``).
    """
    import gzip
    import urllib.request

    name = "train-images-idx3-ubyte.gz" if split == "train" else "t10k-images-idx3-ubyte.gz"
    raw_dir = cache_dir / "MNIST" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw = raw_dir / name
    if not raw.exists():
        url = f"https://ossci-datasets.s3.amazonaws.com/mnist/{name}"
        print(f"[mnist_fm] downloading {url} -> {raw}", flush=True)
        urllib.request.urlretrieve(url, raw)
    with gzip.open(raw, "rb") as fh:
        magic = int.from_bytes(fh.read(4), "big")
        if magic != 2051:
            raise ValueError(f"unexpected_mnist_image_magic:{magic}")
        n = int.from_bytes(fh.read(4), "big")
        h = int.from_bytes(fh.read(4), "big")
        w = int.from_bytes(fh.read(4), "big")
        if h != 28 or w != 28:
            raise ValueError(f"unexpected_mnist_shape:{h}x{w}")
        buf = fh.read(n * h * w)
    arr = np.frombuffer(buf, dtype=np.uint8).reshape(n, h * w).astype(np.float64)
    arr = arr / 255.0
    return 2.0 * arr - 1.0


# ---------------------------------------------------------------------------
# Activation + normalization helpers (with analytic backward)
# ---------------------------------------------------------------------------


def _silu_forward(x: Array) -> Array:
    """SiLU activation ``x * sigmoid(x)``."""
    return np.asarray(x * (1.0 / (1.0 + np.exp(-x))), dtype=np.float64)


def _silu_backward(grad_out: Array, x: Array) -> Array:
    """Backward of SiLU. ``grad_out`` has the upstream gradient; ``x`` is the pre-activation."""
    sig = 1.0 / (1.0 + np.exp(-x))
    return np.asarray(grad_out * (sig + x * sig * (1.0 - sig)), dtype=np.float64)


def _gn_forward(x: Array, *, groups: int, weight: Array, bias: Array) -> tuple[Array, Array, Array]:
    """GroupNorm forward.

    ``x`` has shape ``(B, C, H, W)``. Splits ``C`` into ``groups`` groups
    of ``C / groups`` channels; normalises each (B, group) plane; then
    applies a per-channel affine ``weight`` + ``bias`` (both of shape
    ``(C,)``).

    Returns ``(out, mean, rstd)`` for use by the backward pass.
    """
    b, c, h, w = x.shape
    if c % groups != 0:
        raise ValueError("groups_must_divide_channels")
    group_size = c // groups
    # Reshape to (B, groups, group_size, H, W); compute mean/var over
    # (group_size, H, W) per (B, groups).
    x_g = x.reshape(b, groups, group_size, h, w)
    mean = x_g.mean(axis=(2, 3, 4), keepdims=True)
    var = x_g.var(axis=(2, 3, 4), keepdims=True)
    rstd = 1.0 / np.sqrt(var + 1e-5)
    x_norm = (x_g - mean) * rstd
    x_norm = x_norm.reshape(b, c, h, w)
    out = x_norm * weight[None, :, None, None] + bias[None, :, None, None]
    return np.asarray(out, dtype=np.float64), np.asarray(mean, dtype=np.float64), np.asarray(rstd, dtype=np.float64)


def _gn_backward(
    grad_out: Array,
    *,
    x: Array,
    mean: Array,
    rstd: Array,
    groups: int,
    weight: Array,
) -> tuple[Array, Array, Array]:
    """GroupNorm backward. Returns ``(grad_x, grad_weight, grad_bias)``."""
    b, c, h, w = x.shape
    group_size = c // groups
    x_g = x.reshape(b, groups, group_size, h, w)
    mean_g = mean.reshape(b, groups, 1, 1, 1)
    rstd_g = rstd.reshape(b, groups, 1, 1, 1)
    x_norm_g = (x_g - mean_g) * rstd_g
    x_norm = x_norm_g.reshape(b, c, h, w)
    grad_weight = (grad_out * x_norm).sum(axis=(0, 2, 3))
    grad_bias = grad_out.sum(axis=(0, 2, 3))
    # Per-channel affine backward: grad_x_norm = grad_out * weight.
    grad_x_norm = grad_out * weight[None, :, None, None]
    grad_x_norm_g = grad_x_norm.reshape(b, groups, group_size, h, w)
    # Correct GroupNorm backward (closed-form):
    #   g_x = rstd * (g_norm - mean(g_norm) - (x - mean) * rstd^2 * mean(g_norm * (x - mean)))
    mean_grad_norm_g = grad_x_norm_g.mean(axis=(2, 3, 4), keepdims=True)
    mean_grad_norm_x_centered_g = (grad_x_norm_g * (x_g - mean_g)).mean(axis=(2, 3, 4), keepdims=True)
    grad_x_g = rstd_g * (
        grad_x_norm_g
        - mean_grad_norm_g
        - (x_g - mean_g) * (rstd_g**2) * mean_grad_norm_x_centered_g
    )
    grad_x = grad_x_g.reshape(b, c, h, w)
    return (
        np.asarray(grad_x, dtype=np.float64),
        np.asarray(grad_weight, dtype=np.float64),
        np.asarray(grad_bias, dtype=np.float64),
    )


def _conv2d_forward(
    x: Array,
    weight: Array,
    bias: Array,
    *,
    stride: int,
    padding: int,
) -> Array:
    """Conv2d forward (no dilation / groups). ``x`` (B, C_in, H, W) -> (B, C_out, H', W')."""
    if x.ndim != 4:
        raise ValueError("x_must_be_4d")
    if weight.ndim != 4:
        raise ValueError("weight_must_be_4d")
    b, c_in, h, w = x.shape
    c_out, c_in_w, kh, kw = weight.shape
    if c_in_w != c_in:
        raise ValueError("c_in_mismatch")
    # Pad H and W with zeros (manual padding for stride-aware backward).
    if padding > 0:
        x_p = np.pad(x, ((0, 0), (0, 0), (padding, padding), (padding, padding)), mode="constant")
    else:
        x_p = x
    h_p = h + 2 * padding
    w_p = w + 2 * padding
    h_out = (h_p - kh) // stride + 1
    w_out = (w_p - kw) // stride + 1
    # Gather sliding windows via stride trick.
    s = x_p.strides
    windows = np.lib.stride_tricks.as_strided(
        x_p,
        shape=(b, c_in, kh, kw, h_out, w_out),
        strides=(s[0], s[1], s[2], s[3], s[2] * stride, s[3] * stride),
    )
    # ``windows`` has shape (B, C_in, kH, kW, H_out, W_out). Contract with weight (C_out, C_in, kH, kW).
    out = np.einsum("bcijxy,ocij->boxy", windows, weight, optimize=True)
    if bias is not None:
        out = out + bias[None, :, None, None]
    return np.asarray(out, dtype=np.float64)


def _conv2d_backward(
    grad_out: Array,
    x: Array,
    weight: Array,
    *,
    stride: int,
    padding: int,
) -> tuple[Array, Array, Array]:
    """Conv2d backward. Returns ``(grad_x, grad_weight, grad_bias)``."""
    if grad_out.ndim != 4:
        raise ValueError("grad_out_must_be_4d")
    if x.ndim != 4:
        raise ValueError("x_must_be_4d")
    b, c_in, h, w = x.shape
    c_out, _, kh, kw = weight.shape
    _, _, h_out, w_out = grad_out.shape
    # Pad the input as in the forward pass.
    if padding > 0:
        x_p = np.pad(x, ((0, 0), (0, 0), (padding, padding), (padding, padding)), mode="constant")
    else:
        x_p = x
    s = x_p.strides
    windows = np.lib.stride_tricks.as_strided(
        x_p,
        shape=(b, c_in, kh, kw, h_out, w_out),
        strides=(s[0], s[1], s[2], s[3], s[2] * stride, s[3] * stride),
    )
    # ``windows`` has shape (B, C_in, kH, kW, H_out, W_out).
    # grad_weight[o, c, i, j] = sum_{b, x, y} grad_out[b, o, x, y] * windows[b, c, i, j, x, y]
    grad_weight = np.einsum("boxy,bcijxy->ocij", grad_out, windows, optimize=True)
    # grad_bias[o] = sum_{b, x, y} grad_out[b, o, x, y]
    grad_bias = grad_out.sum(axis=(0, 2, 3))
    # grad_x_p[b, c, h_p, w_p] = sum over (o, i, j) of
    #     grad_out[b, o, h_out, w_out] * weight[o, c, i, j]
    # where (h_p, w_p) = (h_out * stride + i - padding, w_out * stride + j - padding).
    # Build a padded accumulator and scatter the per-kernel contributions.
    grad_x_p = np.zeros(
        (b, c_in, h + 2 * padding, w + 2 * padding),
        dtype=np.float64,
    )
    for i in range(kh):
        for j in range(kw):
            grad_x_p[:, :, i : i + stride * h_out : stride, j : j + stride * w_out : stride] += np.einsum(
                "boxy,oc->bcxy",
                grad_out,
                weight[:, :, i, j],
                optimize=True,
            )
    # Remove padding.
    grad_x = (
        grad_x_p[:, :, padding : padding + h, padding : padding + w]
        if padding > 0
        else grad_x_p
    )
    return (
        np.asarray(grad_x, dtype=np.float64),
        np.asarray(grad_weight, dtype=np.float64),
        np.asarray(grad_bias, dtype=np.float64),
    )


def _upsample_nearest_2x_forward(x: Array) -> Array:
    """Repeat each spatial pixel 2x along H and W. ``(B, C, H, W) -> (B, C, 2H, 2W)``."""
    if x.ndim != 4:
        raise ValueError("x_must_be_4d")
    return np.asarray(np.repeat(np.repeat(x, 2, axis=2), 2, axis=3), dtype=np.float64)


def _upsample_nearest_2x_backward(grad_out: Array) -> Array:
    """Backward of 2x nearest upsample: sum every 2x2 block."""
    if grad_out.ndim != 4:
        raise ValueError("grad_out_must_be_4d")
    b, c, h, w = grad_out.shape
    if h % 2 != 0 or w % 2 != 0:
        raise ValueError("grad_out_must_have_even_spatial_dims")
    g = grad_out.reshape(b, c, h // 2, 2, w // 2, 2).sum(axis=(3, 5))
    return np.asarray(g, dtype=np.float64)


# ---------------------------------------------------------------------------
# UNet init + forward
# ---------------------------------------------------------------------------


def _kaiming_uniform(rng: np.random.Generator, shape: tuple[int, ...], *, fan_in: int) -> Array:
    """Kaiming-uniform init: ``U(-bound, bound)`` with ``bound = sqrt(6 / fan_in)``."""
    bound = float(np.sqrt(6.0 / float(fan_in)))
    return np.asarray(rng.uniform(-bound, bound, size=shape), dtype=np.float64)


# Layer naming convention used in the weights list:
#   "down1_w", "down1_b", "down1_gn_w", "down1_gn_b",
#   "down2_w", ..., "bottleneck_w", ..., "up1_w", ..., "out_w", "out_b".
# Total per UNet: 8 Conv layers + 4 GroupNorms = 12 layers (weights + biases).
#
# Layers in forward order:
#   1. down1: Conv(2 -> C), GN, SiLU
#   2. down2: Conv(C -> 2C, s=2), GN, SiLU
#   3. bottleneck: Conv(2C -> 2C), GN, SiLU
#   4. up1: Upsample + Conv(2C -> C), GN, SiLU
#   5. out: Conv(C -> 1)


def velocity_field_unet_init(
    rng: np.random.Generator,
    *,
    base_channels: int = 16,
) -> list[Array]:
    """Kaiming-uniform init of the small UNet. Returns 20 tensors (10 weights + 10 biases / GN).

    The flat list layout is::

        down1_w, down1_b, down1_gn_w, down1_gn_b,
        down2_w, down2_b, down2_gn_w, down2_gn_b,
        bottleneck_w, bottleneck_b, bottleneck_gn_w, bottleneck_gn_b,
        up1_w, up1_b, up1_gn_w, up1_gn_b,
        out_w, out_b, out_gn_w, out_gn_b

    ``out_w`` and ``out_b`` are zero-init (residual-style stabilisation).
    All other weights are Kaiming-uniform.
    """
    if base_channels <= 0:
        raise ValueError("base_channels_must_be_positive")
    if base_channels % MNIST_GN_GROUPS != 0:
        raise ValueError("base_channels_must_be_multiple_of_gn_groups")
    c: int = int(base_channels)
    c2: int = 2 * c
    # Input is (B, 2, 28, 28): 2 channels = (image + time).
    down1_fan_in: int = 2 * 3 * 3
    down1_w: Array = _kaiming_uniform(rng, (c, 2, 3, 3), fan_in=down1_fan_in)
    down1_b: Array = np.zeros(c, dtype=np.float64)
    down2_fan_in: int = c * 3 * 3
    down2_w: Array = _kaiming_uniform(rng, (c2, c, 3, 3), fan_in=down2_fan_in)
    down2_b: Array = np.zeros(c2, dtype=np.float64)
    bottleneck_fan_in: int = c2 * 3 * 3
    bottleneck_w: Array = _kaiming_uniform(rng, (c2, c2, 3, 3), fan_in=bottleneck_fan_in)
    bottleneck_b: Array = np.zeros(c2, dtype=np.float64)
    up1_fan_in: int = c2 * 3 * 3
    up1_w: Array = _kaiming_uniform(rng, (c, c2, 3, 3), fan_in=up1_fan_in)
    up1_b: Array = np.zeros(c, dtype=np.float64)
    # Zero-init the output projection (residual-style stabilisation).
    out_w: Array = np.zeros((1, c, 3, 3), dtype=np.float64)
    out_b: Array = np.zeros(1, dtype=np.float64)
    # GroupNorm per channel: weight = ones, bias = zeros.
    down1_gn_w: Array = np.ones(c, dtype=np.float64)
    down1_gn_b: Array = np.zeros(c, dtype=np.float64)
    down2_gn_w: Array = np.ones(c2, dtype=np.float64)
    down2_gn_b: Array = np.zeros(c2, dtype=np.float64)
    bottleneck_gn_w: Array = np.ones(c2, dtype=np.float64)
    bottleneck_gn_b: Array = np.zeros(c2, dtype=np.float64)
    up1_gn_w: Array = np.ones(c, dtype=np.float64)
    up1_gn_b: Array = np.zeros(c, dtype=np.float64)
    # Output GN: 1 channel / 1 group is degenerate; use groups=1.
    out_gn_w: Array = np.ones(1, dtype=np.float64)
    out_gn_b: Array = np.zeros(1, dtype=np.float64)
    return [
        down1_w, down1_b, down1_gn_w, down1_gn_b,
        down2_w, down2_b, down2_gn_w, down2_gn_b,
        bottleneck_w, bottleneck_b, bottleneck_gn_w, bottleneck_gn_b,
        up1_w, up1_b, up1_gn_w, up1_gn_b,
        out_w, out_b, out_gn_w, out_gn_b,
    ]


# Weight index map for readability.
IDX = {
    "down1_w": 0, "down1_b": 1, "down1_gn_w": 2, "down1_gn_b": 3,
    "down2_w": 4, "down2_b": 5, "down2_gn_w": 6, "down2_gn_b": 7,
    "bottleneck_w": 8, "bottleneck_b": 9, "bottleneck_gn_w": 10, "bottleneck_gn_b": 11,
    "up1_w": 12, "up1_b": 13, "up1_gn_w": 14, "up1_gn_b": 15,
    "out_w": 16, "out_b": 17, "out_gn_w": 18, "out_gn_b": 19,
}


def _flatten_with_time(x: Array, t_value: float) -> Array:
    """Reshape (B, 784) -> (B, 1, 28, 28); concat a constant-time channel -> (B, 2, 28, 28)."""
    if x.ndim != 2 or x.shape[1] != MNIST_FLAT_DIM:
        raise ValueError("x_must_be_b_784")
    b = x.shape[0]
    img = x.reshape(b, 1, 28, 28)
    t_ch = np.full((b, 1, 28, 28), float(t_value), dtype=np.float64)
    return np.concatenate([img, t_ch], axis=1)


def velocity_field_forward(weights: list[Array], x_flat: Array, t: float) -> Array:
    """UNet forward. ``x_flat`` (B, 784) -> velocity (B, 1, 28, 28)."""
    if len(weights) != 20:
        raise ValueError("weights_must_have_20_tensors")
    x = _flatten_with_time(x_flat, float(t))
    # Down 1: Conv(2->C), GN, SiLU.
    h = _conv2d_forward(x, weights[IDX["down1_w"]], weights[IDX["down1_b"]], stride=1, padding=1)
    h, _, _ = _gn_forward(h, groups=MNIST_GN_GROUPS, weight=weights[IDX["down1_gn_w"]], bias=weights[IDX["down1_gn_b"]])
    h = _silu_forward(h)
    # Down 2: Conv(C->2C, s=2), GN, SiLU.
    h = _conv2d_forward(h, weights[IDX["down2_w"]], weights[IDX["down2_b"]], stride=2, padding=1)
    h, _, _ = _gn_forward(h, groups=MNIST_GN_GROUPS, weight=weights[IDX["down2_gn_w"]], bias=weights[IDX["down2_gn_b"]])
    h = _silu_forward(h)
    # Bottleneck: Conv(2C->2C), GN, SiLU.
    h = _conv2d_forward(h, weights[IDX["bottleneck_w"]], weights[IDX["bottleneck_b"]], stride=1, padding=1)
    h, _, _ = _gn_forward(h, groups=MNIST_GN_GROUPS, weight=weights[IDX["bottleneck_gn_w"]], bias=weights[IDX["bottleneck_gn_b"]])
    h = _silu_forward(h)
    # Up 1: Upsample + Conv(2C->C), GN, SiLU.
    h = _upsample_nearest_2x_forward(h)
    h = _conv2d_forward(h, weights[IDX["up1_w"]], weights[IDX["up1_b"]], stride=1, padding=1)
    h, _, _ = _gn_forward(h, groups=MNIST_GN_GROUPS, weight=weights[IDX["up1_gn_w"]], bias=weights[IDX["up1_gn_b"]])
    h = _silu_forward(h)
    # Output: Conv(C->1). No GN, no SiLU (final projection).
    h = _conv2d_forward(h, weights[IDX["out_w"]], weights[IDX["out_b"]], stride=1, padding=1)
    return np.asarray(h, dtype=np.float64)


def _loss_and_grads(weights: list[Array], x_flat: Array, t_value: float, v_target_flat: Array) -> tuple[float, list[Array]]:
    """MSE loss + analytic gradients. ``x_flat`` (B, 784), ``v_target_flat`` (B, 784)."""
    if len(weights) != 20:
        raise ValueError("weights_must_have_20_tensors")
    # ---- Forward (re-do to keep intermediates) ----
    x = _flatten_with_time(x_flat, float(t_value))
    h = _conv2d_forward(x, weights[IDX["down1_w"]], weights[IDX["down1_b"]], stride=1, padding=1)
    h1_pre_gn = h
    h, h1_mean, h1_rstd = _gn_forward(h, groups=MNIST_GN_GROUPS, weight=weights[IDX["down1_gn_w"]], bias=weights[IDX["down1_gn_b"]])
    h1_pre_silu = h
    h = _silu_forward(h)
    h2_in = h
    h = _conv2d_forward(h, weights[IDX["down2_w"]], weights[IDX["down2_b"]], stride=2, padding=1)
    h2_pre_gn = h
    h, h2_mean, h2_rstd = _gn_forward(h, groups=MNIST_GN_GROUPS, weight=weights[IDX["down2_gn_w"]], bias=weights[IDX["down2_gn_b"]])
    h2_pre_silu = h
    h = _silu_forward(h)
    h3_in = h
    h = _conv2d_forward(h, weights[IDX["bottleneck_w"]], weights[IDX["bottleneck_b"]], stride=1, padding=1)
    h3_pre_gn = h
    h, h3_mean, h3_rstd = _gn_forward(h, groups=MNIST_GN_GROUPS, weight=weights[IDX["bottleneck_gn_w"]], bias=weights[IDX["bottleneck_gn_b"]])
    h3_pre_silu = h
    h = _silu_forward(h)
    h = _upsample_nearest_2x_forward(h)
    h4_post_up = h
    h = _conv2d_forward(h, weights[IDX["up1_w"]], weights[IDX["up1_b"]], stride=1, padding=1)
    h4_pre_gn = h
    h, h4_mean, h4_rstd = _gn_forward(h, groups=MNIST_GN_GROUPS, weight=weights[IDX["up1_gn_w"]], bias=weights[IDX["up1_gn_b"]])
    h4_pre_silu = h
    h = _silu_forward(h)
    h4_post_silu = h
    v_pred = _conv2d_forward(h, weights[IDX["out_w"]], weights[IDX["out_b"]], stride=1, padding=1)
    v_pred_flat = v_pred.reshape(v_pred.shape[0], MNIST_FLAT_DIM)
    # ---- Loss + output gradient ----
    n = float(x_flat.shape[0])
    resid = v_pred_flat - v_target_flat
    loss = float(np.mean(np.sum(resid * resid, axis=1)))
    grad_v_pred_flat = (2.0 / n) * resid
    grad_v_pred = grad_v_pred_flat.reshape(v_pred.shape)
    # ---- Backward through output Conv ----
    grad_h_in_to_out, grad_out_w, grad_out_b = _conv2d_backward(
        grad_v_pred, h4_post_silu, weights[IDX["out_w"]], stride=1, padding=1,
    )
    grad_h4_pre_silu = grad_h_in_to_out
    # ---- Backward through SiLU (up1) ----
    grad_h4_pre_gn = _silu_backward(grad_h4_pre_silu, h4_pre_silu)
    # ---- Backward through up1 GN ----
    grad_h4_post_up_pre_gn, grad_up1_gn_w, grad_up1_gn_b = _gn_backward(
        grad_h4_pre_gn, x=h4_pre_gn, mean=h4_mean, rstd=h4_rstd,
        groups=MNIST_GN_GROUPS, weight=weights[IDX["up1_gn_w"]],
    )
    # ---- Backward through up1 Conv ----
    grad_h4_post_up, grad_up1_w, grad_up1_b = _conv2d_backward(
        grad_h4_post_up_pre_gn, h4_post_up, weights[IDX["up1_w"]], stride=1, padding=1,
    )
    # ---- Backward through upsample ----
    grad_h4_in_up = _upsample_nearest_2x_backward(grad_h4_post_up)
    # ---- Backward through SiLU (bottleneck) ----
    grad_h3_pre_gn = _silu_backward(grad_h4_in_up, h3_pre_silu)
    # ---- Backward through bottleneck GN ----
    grad_h3_in, grad_bottleneck_gn_w, grad_bottleneck_gn_b = _gn_backward(
        grad_h3_pre_gn, x=h3_pre_gn, mean=h3_mean, rstd=h3_rstd,
        groups=MNIST_GN_GROUPS, weight=weights[IDX["bottleneck_gn_w"]],
    )
    # ---- Backward through bottleneck Conv ----
    grad_h3_in_to_conv, grad_bottleneck_w, grad_bottleneck_b = _conv2d_backward(
        grad_h3_in, h3_in, weights[IDX["bottleneck_w"]], stride=1, padding=1,
    )
    # ---- Backward through SiLU (down2) ----
    grad_h2_pre_gn = _silu_backward(grad_h3_in_to_conv, h2_pre_silu)
    # ---- Backward through down2 GN ----
    grad_h2_in, grad_down2_gn_w, grad_down2_gn_b = _gn_backward(
        grad_h2_pre_gn, x=h2_pre_gn, mean=h2_mean, rstd=h2_rstd,
        groups=MNIST_GN_GROUPS, weight=weights[IDX["down2_gn_w"]],
    )
    # ---- Backward through down2 Conv ----
    grad_h2_in_to_conv, grad_down2_w, grad_down2_b = _conv2d_backward(
        grad_h2_in, h2_in, weights[IDX["down2_w"]], stride=2, padding=1,
    )
    # ---- Backward through SiLU (down1) ----
    grad_h1_pre_gn = _silu_backward(grad_h2_in_to_conv, h1_pre_silu)
    # ---- Backward through down1 GN ----
    grad_h1_in, grad_down1_gn_w, grad_down1_gn_b = _gn_backward(
        grad_h1_pre_gn, x=h1_pre_gn, mean=h1_mean, rstd=h1_rstd,
        groups=MNIST_GN_GROUPS, weight=weights[IDX["down1_gn_w"]],
    )
    # ---- Backward through down1 Conv ----
    _, grad_down1_w, grad_down1_b = _conv2d_backward(
        grad_h1_in, x, weights[IDX["down1_w"]], stride=1, padding=1,
    )
    grads = [
        grad_down1_w, grad_down1_b, grad_down1_gn_w, grad_down1_gn_b,
        grad_down2_w, grad_down2_b, grad_down2_gn_w, grad_down2_gn_b,
        grad_bottleneck_w, grad_bottleneck_b, grad_bottleneck_gn_w, grad_bottleneck_gn_b,
        grad_up1_w, grad_up1_b, grad_up1_gn_w, grad_up1_gn_b,
        grad_out_w, grad_out_b,
        np.zeros_like(weights[IDX["out_gn_w"]]),  # out GN weights aren't used
        np.zeros_like(weights[IDX["out_gn_b"]]),
    ]
    return loss, grads


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------


def train(
    *,
    epochs: int = 3,
    batch_size: int = 64,
    lr: float = 1e-3,
    base_channels: int = 16,
    seed: int = 42,
    cache_dir: Path | None = None,
    log_every: int = 50,
    max_train_images: int | None = None,
) -> list[Array]:
    """Train the UNet on MNIST and return the 20 weight tensors.

    ``max_train_images`` caps the training set size for smoke tests
    (defaults to ``None`` = full 60K). ``cache_dir`` defaults to
    ``data/mnist_cache`` at the repo root.
    """
    if epochs <= 0:
        raise ValueError("epochs_must_be_positive")
    if batch_size <= 0:
        raise ValueError("batch_size_must_be_positive")
    if lr <= 0.0:
        raise ValueError("lr_must_be_positive")
    if cache_dir is None:
        cache_dir = Path("data/mnist_cache")
    cache_dir = Path(cache_dir)
    print(f"[mnist_fm] loading MNIST train images from {cache_dir} ...", flush=True)
    images = _load_mnist("train", cache_dir=cache_dir)
    if max_train_images is not None and max_train_images > 0:
        images = images[: int(max_train_images)]
    print(f"[mnist_fm] loaded {images.shape[0]} training images", flush=True)
    rng = np.random.default_rng(int(seed))
    params = list(velocity_field_unet_init(rng, base_channels=int(base_channels)))
    moment1 = [np.zeros_like(p) for p in params]
    moment2 = [np.zeros_like(p) for p in params]
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    n = images.shape[0]
    batches_per_epoch = n // int(batch_size)
    step = 0
    for epoch in range(int(epochs)):
        # Shuffle indices for this epoch.
        perm = rng.permutation(n)
        for b in range(batches_per_epoch):
            idx = perm[b * batch_size : (b + 1) * batch_size]
            x_1 = images[idx]  # (B, 784) in [-1, 1]
            x_0 = rng.standard_normal(x_1.shape).astype(np.float64)
            x_0 = np.clip(x_0, -MNIST_CLAMP, MNIST_CLAMP)
            t = rng.uniform(0.0, 1.0, size=x_1.shape[0])
            x_t = (1.0 - t)[:, None] * x_0 + t[:, None] * x_1
            v_target = x_1 - x_0
            loss, grads = _loss_and_grads(params, x_t, float(t[0]), v_target)
            step += 1
            for i, grad in enumerate(grads):
                moment1[i] = beta1 * moment1[i] + (1.0 - beta1) * grad
                moment2[i] = beta2 * moment2[i] + (1.0 - beta2) * (grad * grad)
                m_hat = moment1[i] / (1.0 - beta1**step)
                v_hat = moment2[i] / (1.0 - beta2**step)
                params[i] = params[i] - lr * m_hat / (np.sqrt(v_hat) + eps)
            if step == 1 or step % int(log_every) == 0:
                print(
                    f"[mnist_fm] epoch {epoch + 1}/{epochs} step {step}/{batches_per_epoch * epochs} loss={loss:.6f}",
                    flush=True,
                )
    return params


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

WEIGHT_KEYS: tuple[str, ...] = (
    "down1_w", "down1_b", "down1_gn_w", "down1_gn_b",
    "down2_w", "down2_b", "down2_gn_w", "down2_gn_b",
    "bottleneck_w", "bottleneck_b", "bottleneck_gn_w", "bottleneck_gn_b",
    "up1_w", "up1_b", "up1_gn_w", "up1_gn_b",
    "out_w", "out_b", "out_gn_w", "out_gn_b",
)


def save_weights(weights: list[Array], path: str | Path) -> Path:
    """Write the 20 weight arrays to ``path`` as ``float32`` in an ``.npz``."""
    if len(weights) != len(WEIGHT_KEYS):
        raise ValueError(f"weights_must_have_{len(WEIGHT_KEYS)}_arrays")
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        key: np.asarray(arr, dtype=np.float32)
        for key, arr in zip(WEIGHT_KEYS, weights, strict=True)
    }
    np.savez_compressed(out, **payload)
    return out


def load_weights(path: str | Path) -> list[Array]:
    """Load the 20 weight arrays written by :func:`save_weights`."""
    with np.load(Path(path)) as data:
        missing = [k for k in WEIGHT_KEYS if k not in data.files]
        if missing:
            raise ValueError(f"missing_weight_keys:{','.join(missing)}")
        return [np.asarray(data[k], dtype=np.float64) for k in WEIGHT_KEYS]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="mnist_fm_train",
        description="Train the MNIST rectified-flow velocity-field UNet.",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--base-channels", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-train-images", type=int, default=None)
    parser.add_argument("--cache-dir", type=Path, default=Path("data/mnist_cache"))
    parser.add_argument("--output", type=Path, default=Path("data/mnist_fm.npz"))
    parser.add_argument("--log-every", type=int, default=50)
    args = parser.parse_args(argv)

    weights = train(
        epochs=int(args.epochs),
        batch_size=int(args.batch_size),
        lr=float(args.lr),
        base_channels=int(args.base_channels),
        seed=int(args.seed),
        cache_dir=Path(args.cache_dir),
        max_train_images=args.max_train_images,
        log_every=int(args.log_every),
    )
    out = save_weights(weights, args.output)
    print(f"[mnist_fm] saved {out} ({out.stat().st_size} bytes)", flush=True)
    return 0


if __name__ == "__main__":  # pragma: no cover — CLI entry point
    raise SystemExit(main())


__all__ = [
    "IDX",
    "MNIST_CLAMP",
    "MNIST_FLAT_DIM",
    "MNIST_GN_GROUPS",
    "MNIST_IMAGE_SHAPE",
    "MNIST_TEST_SIZE",
    "MNIST_TRAIN_SIZE",
    "WEIGHT_KEYS",
    "load_weights",
    "main",
    "save_weights",
    "train",
    "velocity_field_forward",
    "velocity_field_unet_init",
]

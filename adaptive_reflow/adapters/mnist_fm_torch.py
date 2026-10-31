"""Torch port of the MNIST flow-matching velocity field, for GPU inference.

Why this module exists
----------------------
The canonical MNIST path (:mod:`adaptive_reflow.adapters.mnist_fm`) integrates a
20-tensor UNet in NumPy float64 **one sample at a time**. That is a correct but
extremely expensive way to run an ODE: measured on this host a single
``_unet_evaluate`` call on a ``(1, 784)`` input costs ~2.3 ms, so an N=1000
frontier cell at NFE=200 needs ~96 minutes of wall clock for four arms. The same
arithmetic on a GPU, batched over the whole population, is three orders of
magnitude cheaper because the per-call Python overhead and the NumPy
``einsum``-with-``as_strided``-windows path both disappear.

Scope and non-goals
-------------------
This is an **inference backend**, not a second definition of the model. Every
op is the direct counterpart of the NumPy op it replaces:

===================  =================================  ====================
NumPy                Torch                              note
===================  =================================  ====================
``_flatten_with_time`` ``cat([x, t_channel], dim=1)``    constant time plane
``_conv2d_forward``  ``F.conv2d(padding=1)``            same zero padding
``_gn_forward``      ``F.group_norm(eps=1e-5)``         biased var, 8 groups
``_silu_forward``    ``F.silu``                         ``x * sigmoid(x)``
``np.repeat(x, 2)``  ``F.interpolate(nearest, x2)``     nearest upsample
``_integrate_rk4``   :meth:`TorchMnistVelocity.integrate_rk4`
===================  =================================  ====================

``tests/test_mnist_fm_torch_parity.py`` asserts that the torch forward matches
the NumPy forward to float64 round-off and that a short RK4 trajectory agrees
with :func:`adaptive_reflow.adapters.mnist_fm._integrate_rk4`. The parity test is
the contract: if the two ever disagree, this backend is wrong, not "close
enough".

Determinism
-----------
``float64`` on CUDA is used by default. It is slower than ``float32`` but it is
the dtype the recorded NumPy artifacts were produced in, and the whole point is
to reproduce those numbers on different hardware rather than to produce new
ones. ``float32`` is available explicitly and must not be used for a cell that
is compared against a float64 artifact.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import numpy as np

from adaptive_reflow.adapters.mnist_fm import MNIST_FLAT_DIM, MNIST_FM_CLAMP
from adaptive_reflow.adapters.mnist_fm_train import (
    IDX,
    MNIST_GN_GROUPS,
    load_weights,
)

__all__ = ["TorchMnistVelocity"]


class TorchMnistVelocity:
    """Batched torch implementation of the MNIST FM velocity field.

    Parameters
    ----------
    weights_path:
        ``.npz`` written by :func:`adaptive_reflow.adapters.mnist_fm_train.save_weights`.
    device:
        ``"cuda"``, ``"cuda:0"`` or ``"cpu"``.
    dtype:
        ``"float64"`` (default, parity with the NumPy artifacts) or
        ``"float32"`` (faster, not comparable to a float64 cell).
    """

    def __init__(
        self,
        weights_path: str | Path,
        *,
        device: str = "cuda",
        dtype: str = "float64",
    ) -> None:
        import torch

        if dtype not in ("float64", "float32"):
            raise ValueError(f"unsupported_dtype:{dtype}")
        self._torch = torch
        self._dtype = getattr(torch, dtype)
        if str(device).startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("cuda_requested_but_unavailable")
        self._device = torch.device(device)

        raw = load_weights(weights_path)
        self._w = {
            name: torch.as_tensor(raw[idx], dtype=self._dtype, device=self._device)
            for name, idx in IDX.items()
        }

    # -- forward ---------------------------------------------------------
    def forward(self, x_flat: Any, t: float) -> Any:
        """Velocity ``v(x, t)`` for ``x_flat`` of shape ``(B, 784)``.

        ``t`` is a scalar shared by the whole batch, matching the NumPy
        integrator, which evaluates the field at one ``t`` per RK4 stage.
        """
        torch = self._torch
        F = torch.nn.functional
        w = self._w
        x = torch.as_tensor(x_flat, dtype=self._dtype, device=self._device)
        if x.ndim != 2 or int(x.shape[1]) != MNIST_FLAT_DIM:
            raise ValueError("x_must_have_shape_b_784")
        b = int(x.shape[0])
        img = x.reshape(b, 1, 28, 28)
        t_ch = torch.full((b, 1, 28, 28), float(t), dtype=self._dtype, device=self._device)
        h = torch.cat([img, t_ch], dim=1)

        h = F.conv2d(h, w["down1_w"], w["down1_b"], stride=1, padding=1)
        h = F.group_norm(h, MNIST_GN_GROUPS, w["down1_gn_w"], w["down1_gn_b"], eps=1e-5)
        h = F.silu(h)

        h = F.conv2d(h, w["down2_w"], w["down2_b"], stride=2, padding=1)
        h = F.group_norm(h, MNIST_GN_GROUPS, w["down2_gn_w"], w["down2_gn_b"], eps=1e-5)
        h = F.silu(h)

        h = F.conv2d(h, w["bottleneck_w"], w["bottleneck_b"], stride=1, padding=1)
        h = F.group_norm(
            h, MNIST_GN_GROUPS, w["bottleneck_gn_w"], w["bottleneck_gn_b"], eps=1e-5
        )
        h = F.silu(h)

        h = F.interpolate(h, scale_factor=2, mode="nearest")
        h = F.conv2d(h, w["up1_w"], w["up1_b"], stride=1, padding=1)
        h = F.group_norm(h, MNIST_GN_GROUPS, w["up1_gn_w"], w["up1_gn_b"], eps=1e-5)
        h = F.silu(h)

        h = F.conv2d(h, w["out_w"], w["out_b"], stride=1, padding=1)
        return h.reshape(b, MNIST_FLAT_DIM)

    # -- integration -----------------------------------------------------
    def integrate_rk4(
        self,
        x0: Any,
        *,
        t0: float,
        t1: float,
        num_steps: int,
    ) -> Any:
        """Batched RK4 over ``[t0, t1]``; returns the final ``(B, 784)`` state.

        Step for step this is :func:`adaptive_reflow.adapters.mnist_fm._integrate_rk4`
        with the per-sample loop replaced by a batch dimension: same
        ``linspace`` grid, same four stages, same ``[-1, 1]`` clamp after every
        step.
        """
        torch = self._torch
        n = int(num_steps)
        if n < 1:
            raise ValueError("n_steps_must_be_positive")
        x = torch.as_tensor(x0, dtype=self._dtype, device=self._device).clone()
        grid = np.linspace(float(t0), float(t1), n + 1, dtype=np.float64)
        for i in range(1, grid.size):
            ta = float(grid[i - 1])
            tb = float(grid[i])
            h = tb - ta
            k1 = self.forward(x, ta)
            k2 = self.forward(x + 0.5 * h * k1, ta + 0.5 * h)
            k3 = self.forward(x + 0.5 * h * k2, ta + 0.5 * h)
            k4 = self.forward(x + h * k3, tb)
            x = x + (h / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
            x = torch.clamp(x, -MNIST_FM_CLAMP, MNIST_FM_CLAMP)
        return x

    # -- convenience -----------------------------------------------------
    def numpy(self, x: Any) -> np.ndarray:
        """Detach a tensor to a float64 NumPy array."""
        return cast(np.ndarray, np.asarray(x.detach().cpu().numpy(), dtype=np.float64))

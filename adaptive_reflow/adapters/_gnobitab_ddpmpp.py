"""Torch re-implementation of the published gnobitab Rectified-Flow DDPM++ UNet.

The published CIFAR-10 1-Rectified-Flow checkpoint
(``gnobitab/RectifiedFlow``, Liu 2022 ``arXiv:2209.03003``) ships a
Score-SDE / NCSN++ ``state_dict`` whose keys are laid out as a flat
``module.all_modules.<N>.<sub>`` list rather than a PyTorch module
hierarchy. This module rebuilds that exact topology so that
``load_state_dict(..., strict=True)`` succeeds against the published
tensors and the forward pass reproduces the reference
``score_sde_pytorch`` ``NCSNpp.forward``.

Architecture (inferred from the checkpoint tensor shapes; see
``docs/r4-survey/13-weights-acquisition.md`` §4):

* ``nf=128``, ``ch_mult=(1, 2, 2, 2)``, ``num_res_blocks=4``
* ``attn_resolutions=(16,)``, ``resblock_type="biggan"``, ``fir=False``
* ``embedding_type="positional"``, ``conditional=True``
* ``skip_rescale=True``, ``progressive="none"``,
  ``progressive_input="none"``, ``scale_by_sigma=False``

Total: 55 entries in ``all_modules`` + the non-trainable ``sigmas``
buffer = 565 ``state_dict`` keys, 61,805,419 parameters.

Time conditioning
-----------------

The reference Rectified-Flow sampler calls the network as
``model(x, t * 999)`` with ``t`` in ``[0, 1]``. :class:`RFVelocityUNet`
wraps that convention: it accepts ``t`` in ``[0, 1]`` and performs the
``× 999`` rescale internally, so callers integrate on the natural unit
interval.

This module is imported lazily by
:mod:`adaptive_reflow.adapters.rectified_flow_cifar` and is the only
place in the framework that defines ``torch.nn`` layers.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import torch
import torch.nn.functional as F  # noqa: N812
from torch import Tensor, nn

__all__ = [
    "GNOBITAB_RF_CIFAR_ATTN_RESOLUTIONS",
    "GNOBITAB_RF_CIFAR_CH_MULT",
    "GNOBITAB_RF_CIFAR_NF",
    "GNOBITAB_RF_CIFAR_NUM_RES_BLOCKS",
    "GNOBITAB_RF_CIFAR_T_SCALE",
    "NCSNppDDPMpp",
    "RFVelocityUNet",
    "build_gnobitab_rf_cifar_unet",
    "load_gnobitab_rf_cifar_unet",
    "strip_module_prefix",
]

#: Published CIFAR-10 1-RF hyper-parameters (see module docstring).
GNOBITAB_RF_CIFAR_NF: int = 128
GNOBITAB_RF_CIFAR_CH_MULT: tuple[int, ...] = (1, 2, 2, 2)
GNOBITAB_RF_CIFAR_NUM_RES_BLOCKS: int = 4
GNOBITAB_RF_CIFAR_ATTN_RESOLUTIONS: tuple[int, ...] = (16,)

#: The reference sampler feeds ``t * 999`` to the positional embedding.
GNOBITAB_RF_CIFAR_T_SCALE: float = 999.0

#: Score-SDE GroupNorm epsilon (differs from the torch default 1e-5).
_GROUP_NORM_EPS: float = 1e-6

#: ``min(channels // 4, 32)`` in the reference implementation.
_GROUP_NORM_MAX_GROUPS: int = 32

#: ``get_timestep_embedding`` max positions.
_TIMESTEP_MAX_POSITIONS: int = 10000

_SQRT2: float = math.sqrt(2.0)


def _group_norm(channels: int) -> nn.GroupNorm:
    """GroupNorm with the reference's ``min(C // 4, 32)`` group count."""
    groups = min(int(channels) // 4, _GROUP_NORM_MAX_GROUPS)
    return nn.GroupNorm(num_groups=groups, num_channels=int(channels), eps=_GROUP_NORM_EPS)


def _conv3x3(in_ch: int, out_ch: int) -> nn.Conv2d:
    """3×3 ``same``-padded convolution (reference ``layers.conv3x3``)."""
    return nn.Conv2d(int(in_ch), int(out_ch), kernel_size=3, stride=1, padding=1, bias=True)


def _conv1x1(in_ch: int, out_ch: int) -> nn.Conv2d:
    """1×1 convolution (reference ``layers.conv1x1``)."""
    return nn.Conv2d(int(in_ch), int(out_ch), kernel_size=1, stride=1, padding=0, bias=True)


def get_timestep_embedding(timesteps: Tensor, embedding_dim: int) -> Tensor:
    """Sinusoidal positional embedding (reference ``layers.get_timestep_embedding``).

    ``sin`` first then ``cos`` — the concatenation order is load-bearing
    because the downstream ``Linear`` was trained against it.
    """
    half_dim = int(embedding_dim) // 2
    scale = math.log(_TIMESTEP_MAX_POSITIONS) / (half_dim - 1)
    freqs = torch.exp(
        torch.arange(half_dim, dtype=torch.float32, device=timesteps.device) * -scale
    )
    args = timesteps.float()[:, None] * freqs[None, :]
    emb = torch.cat([torch.sin(args), torch.cos(args)], dim=1)
    if int(embedding_dim) % 2 == 1:
        emb = F.pad(emb, (0, 1), mode="constant")
    return emb.to(timesteps.dtype)


def _naive_upsample_2d(x: Tensor, factor: int = 2) -> Tensor:
    """Nearest-neighbour ×``factor`` upsample (reference ``naive_upsample_2d``)."""
    _n, c, h, w = x.shape
    y = torch.reshape(x, (-1, c, h, 1, w, 1))
    y = y.repeat(1, 1, 1, factor, 1, factor)
    return torch.reshape(y, (-1, c, h * factor, w * factor))


def _naive_downsample_2d(x: Tensor, factor: int = 2) -> Tensor:
    """Mean-pool ÷``factor`` downsample (reference ``naive_downsample_2d``)."""
    _n, c, h, w = x.shape
    y = torch.reshape(x, (-1, c, h // factor, factor, w // factor, factor))
    return torch.mean(y, dim=(3, 5))


class NIN(nn.Module):
    """Network-in-network 1×1 projection with reference ``(W, b)`` naming."""

    def __init__(self, in_dim: int, num_units: int) -> None:
        super().__init__()
        self.W = nn.Parameter(torch.zeros(int(in_dim), int(num_units)))  # noqa: N803
        self.b = nn.Parameter(torch.zeros(int(num_units)))

    def forward(self, x: Tensor) -> Tensor:
        """Apply ``x @ W + b`` over the channel axis of an NCHW tensor."""
        y = torch.einsum("bchw,cd->bdhw", x, self.W)
        return y + self.b[None, :, None, None]


class AttnBlockpp(nn.Module):
    """Self-attention block (reference ``layerspp.AttnBlockpp``, ``skip_rescale=True``)."""

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.GroupNorm_0 = _group_norm(channels)  # noqa: N815
        self.NIN_0 = NIN(channels, channels)  # noqa: N815
        self.NIN_1 = NIN(channels, channels)  # noqa: N815
        self.NIN_2 = NIN(channels, channels)  # noqa: N815
        self.NIN_3 = NIN(channels, channels)  # noqa: N815

    def forward(self, x: Tensor) -> Tensor:
        """Return ``(x + attn(x)) / sqrt(2)``."""
        b, c, h_dim, w_dim = x.shape
        h = self.GroupNorm_0(x)
        q = self.NIN_0(h)
        k = self.NIN_1(h)
        v = self.NIN_2(h)
        w = torch.einsum("bchw,bcij->bhwij", q, k) * (int(c) ** -0.5)
        w = torch.reshape(w, (b, h_dim, w_dim, h_dim * w_dim))
        w = F.softmax(w, dim=-1)
        w = torch.reshape(w, (b, h_dim, w_dim, h_dim, w_dim))
        h = torch.einsum("bhwij,bcij->bchw", w, v)
        h = self.NIN_3(h)
        return (x + h) / _SQRT2


class ResnetBlockBigGANpp(nn.Module):
    """BigGAN-style residual block (reference ``layerspp.ResnetBlockBigGANpp``).

    ``skip_rescale=True`` and ``fir=False`` (the DDPM++ config), so
    up/down-sampling is nearest-neighbour / mean-pool and the residual
    sum is divided by ``sqrt(2)``. ``Dropout_0`` is present in the
    reference but is a no-op in ``eval()`` mode and holds no parameters,
    so it is omitted here without affecting ``state_dict`` compatibility.
    """

    def __init__(
        self,
        in_ch: int,
        out_ch: int | None = None,
        *,
        temb_dim: int,
        up: bool = False,
        down: bool = False,
    ) -> None:
        super().__init__()
        out_channels = int(out_ch) if out_ch is not None else int(in_ch)
        self.in_ch = int(in_ch)
        self.out_ch = out_channels
        self.up = bool(up)
        self.down = bool(down)
        self.GroupNorm_0 = _group_norm(in_ch)  # noqa: N815
        self.Conv_0 = _conv3x3(in_ch, out_channels)  # noqa: N815
        self.Dense_0 = nn.Linear(int(temb_dim), out_channels)  # noqa: N815
        self.GroupNorm_1 = _group_norm(out_channels)  # noqa: N815
        self.Conv_1 = _conv3x3(out_channels, out_channels)  # noqa: N815
        self.has_skip_conv = self.in_ch != self.out_ch or self.up or self.down
        if self.has_skip_conv:
            self.Conv_2 = _conv1x1(in_ch, out_channels)  # noqa: N815
        self.act = nn.SiLU()

    def forward(self, x: Tensor, temb: Tensor) -> Tensor:
        """Return the residual-block output for input ``x`` and time embedding ``temb``."""
        h = self.act(self.GroupNorm_0(x))
        if self.up:
            h = _naive_upsample_2d(h, factor=2)
            x = _naive_upsample_2d(x, factor=2)
        elif self.down:
            h = _naive_downsample_2d(h, factor=2)
            x = _naive_downsample_2d(x, factor=2)
        h = self.Conv_0(h)
        h = h + self.Dense_0(self.act(temb))[:, :, None, None]
        h = self.act(self.GroupNorm_1(h))
        h = self.Conv_1(h)
        if self.has_skip_conv:
            x = self.Conv_2(x)
        return (x + h) / _SQRT2


class NCSNppDDPMpp(nn.Module):
    """Score-SDE NCSN++/DDPM++ UNet with the reference flat ``all_modules`` layout.

    The submodules are held in a single :class:`torch.nn.ModuleList` named
    ``all_modules`` so the published ``state_dict`` keys
    (``all_modules.<N>.<sub>``) load with ``strict=True``.
    """

    def __init__(
        self,
        *,
        nf: int = GNOBITAB_RF_CIFAR_NF,
        ch_mult: tuple[int, ...] = GNOBITAB_RF_CIFAR_CH_MULT,
        num_res_blocks: int = GNOBITAB_RF_CIFAR_NUM_RES_BLOCKS,
        attn_resolutions: tuple[int, ...] = GNOBITAB_RF_CIFAR_ATTN_RESOLUTIONS,
        image_size: int = 32,
        num_channels: int = 3,
        num_train_timesteps: int = 1000,
    ) -> None:
        super().__init__()
        self.nf = int(nf)
        self.ch_mult = tuple(int(m) for m in ch_mult)
        self.num_res_blocks = int(num_res_blocks)
        self.attn_resolutions = tuple(int(r) for r in attn_resolutions)
        self.num_resolutions = len(self.ch_mult)
        self.all_resolutions = tuple(
            int(image_size) // (2**i) for i in range(self.num_resolutions)
        )
        self.act = nn.SiLU()
        # Non-trainable EDM/Score-SDE log-schedule buffer. Unused when
        # ``scale_by_sigma=False`` (the Rectified-Flow setting) but present
        # in the published state_dict, so it must be registered.
        self.register_buffer("sigmas", torch.zeros(int(num_train_timesteps)))

        temb_dim = self.nf * 4
        modules: list[nn.Module] = []
        # -- time embedding MLP (positional embedding is functional) --
        modules.append(nn.Linear(self.nf, temb_dim))
        modules.append(nn.Linear(temb_dim, temb_dim))
        # -- downsampling --
        modules.append(_conv3x3(int(num_channels), self.nf))
        hs_c: list[int] = [self.nf]
        in_ch = self.nf
        for i_level in range(self.num_resolutions):
            for _ in range(self.num_res_blocks):
                out_ch = self.nf * self.ch_mult[i_level]
                modules.append(ResnetBlockBigGANpp(in_ch, out_ch, temb_dim=temb_dim))
                in_ch = out_ch
                if self.all_resolutions[i_level] in self.attn_resolutions:
                    modules.append(AttnBlockpp(in_ch))
                hs_c.append(in_ch)
            if i_level != self.num_resolutions - 1:
                modules.append(ResnetBlockBigGANpp(in_ch, temb_dim=temb_dim, down=True))
                hs_c.append(in_ch)
        # -- middle --
        modules.append(ResnetBlockBigGANpp(in_ch, temb_dim=temb_dim))
        modules.append(AttnBlockpp(in_ch))
        modules.append(ResnetBlockBigGANpp(in_ch, temb_dim=temb_dim))
        # -- upsampling --
        for i_level in reversed(range(self.num_resolutions)):
            for _ in range(self.num_res_blocks + 1):
                out_ch = self.nf * self.ch_mult[i_level]
                modules.append(
                    ResnetBlockBigGANpp(in_ch + hs_c.pop(), out_ch, temb_dim=temb_dim)
                )
                in_ch = out_ch
            if self.all_resolutions[i_level] in self.attn_resolutions:
                modules.append(AttnBlockpp(in_ch))
            if i_level != 0:
                modules.append(ResnetBlockBigGANpp(in_ch, temb_dim=temb_dim, up=True))
        if hs_c:  # pragma: no cover — topology invariant
            raise AssertionError(f"gnobitab_ddpmpp_skip_stack_not_drained:{hs_c}")
        # -- output --
        modules.append(_group_norm(in_ch))
        modules.append(_conv3x3(in_ch, int(num_channels)))
        self.all_modules = nn.ModuleList(modules)

    def forward(self, x: Tensor, time_cond: Tensor) -> Tensor:
        """Run the UNet. ``time_cond`` is the *raw* Score-SDE step index (0…999)."""
        modules = self.all_modules
        m_idx = 0
        temb = get_timestep_embedding(time_cond, self.nf)
        temb = modules[m_idx](temb)
        m_idx += 1
        temb = modules[m_idx](self.act(temb))
        m_idx += 1

        hs: list[Tensor] = [modules[m_idx](x)]
        m_idx += 1
        for i_level in range(self.num_resolutions):
            for _ in range(self.num_res_blocks):
                h = modules[m_idx](hs[-1], temb)
                m_idx += 1
                if h.shape[-1] in self.attn_resolutions:
                    h = modules[m_idx](h)
                    m_idx += 1
                hs.append(h)
            if i_level != self.num_resolutions - 1:
                h = modules[m_idx](hs[-1], temb)
                m_idx += 1
                hs.append(h)

        h = hs[-1]
        h = modules[m_idx](h, temb)
        m_idx += 1
        h = modules[m_idx](h)
        m_idx += 1
        h = modules[m_idx](h, temb)
        m_idx += 1

        for i_level in reversed(range(self.num_resolutions)):
            for _ in range(self.num_res_blocks + 1):
                h = modules[m_idx](torch.cat([h, hs.pop()], dim=1), temb)
                m_idx += 1
            if h.shape[-1] in self.attn_resolutions:
                h = modules[m_idx](h)
                m_idx += 1
            if i_level != 0:
                h = modules[m_idx](h, temb)
                m_idx += 1

        if hs:  # pragma: no cover — topology invariant
            raise AssertionError("gnobitab_ddpmpp_skip_stack_not_empty")
        h = self.act(modules[m_idx](h))
        m_idx += 1
        h = modules[m_idx](h)
        m_idx += 1
        if m_idx != len(modules):  # pragma: no cover — topology invariant
            raise AssertionError(f"gnobitab_ddpmpp_module_index:{m_idx}!={len(modules)}")
        return h


class RFVelocityUNet(nn.Module):
    """Adapter-facing wrapper: ``v(x, t)`` with ``t`` on the unit interval.

    The reference Rectified-Flow Euler sampler calls the raw network as
    ``model(x, t * 999)``; this wrapper folds that rescale in so the
    framework's integrator can work in natural ``t ∈ [0, 1]`` units.
    """

    def __init__(self, net: NCSNppDDPMpp, *, t_scale: float = GNOBITAB_RF_CIFAR_T_SCALE) -> None:
        super().__init__()
        self.net = net
        self.t_scale = float(t_scale)

    def forward(self, x: Tensor, t: Tensor) -> Tensor:
        """Return the velocity field at ``(x, t)`` for ``t`` in ``[0, 1]``."""
        return self.net(x, t * self.t_scale)


def strip_module_prefix(state_dict: Mapping[str, Any]) -> dict[str, Any]:
    """Drop a leading ``module.`` (DataParallel) prefix from every key."""
    prefix = "module."
    return {
        (k[len(prefix) :] if k.startswith(prefix) else k): v for k, v in state_dict.items()
    }


def build_gnobitab_rf_cifar_unet(**kwargs: Any) -> NCSNppDDPMpp:
    """Instantiate the published CIFAR-10 1-RF DDPM++ topology (random init)."""
    return NCSNppDDPMpp(**kwargs)


def load_gnobitab_rf_cifar_unet(
    state_dict: Mapping[str, Any],
    *,
    dtype: Any = None,
) -> RFVelocityUNet:
    """Build the topology, load ``state_dict`` strictly, return an eval-mode wrapper."""
    net = build_gnobitab_rf_cifar_unet()
    net.load_state_dict(strip_module_prefix(state_dict), strict=True)
    unet = RFVelocityUNet(net)
    if dtype is not None:
        unet = unet.to(dtype)
    unet.eval()
    for param in unet.parameters():
        param.requires_grad_(False)
    return unet

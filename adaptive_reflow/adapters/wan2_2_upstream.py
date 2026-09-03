"""Thin shim to glue Wan2.2 framework adapter to upstream WanT2V harness.

This module exposes:

* :func:`load_upstream_wan_t2v` — instantiate ``wan.text2video.WanT2V``
  from the upstream Alibaba Wan2.2 repo using ``WAN_CONFIGS['t2v-A14B']``.
* :func:`run_upstream_t2v` — high-level call that wraps
  ``WanT2V.generate(...)`` and returns an mp4 on disk.
* :func:`WanT2VStateTuple` — a namedtuple-style container exposing the
  geometry the framework adapter needs to drive a single integration
  step (latent shape, vae stride, patch size, boundary).

Implementation notes
--------------------

* The upstream repo path is hard-coded as
  ``/home/hugo/codes/flowa-multistep-reinference/data/wan2_2/repo``
  and inserted into ``sys.path`` at module import time. We deliberately
  do NOT install the upstream package via pip — the upstream
  ``pyproject.toml`` pulls in ``flash_attn`` (source build, 10-40 min)
  and other unmaintained constraints.
* :func:`wan_path` returns the resolved upstream repo path so other
  modules can avoid hard-coding it.
* All torch imports are deferred; this module can be imported in a
  NumPy-only environment.

Weight blocker
--------------

The Wan2.2 weights at ``data/wan2_2/weights/`` are git-LFS pointer
stubs (e.g. ``Wan2.1_VAE.pth`` is 134 bytes). Both
:func:`load_upstream_wan_t2v` and :func:`run_upstream_t2v` therefore
fail at the constructor step with an
``UnpicklingError``/``safetensors`` "header too large" error — this
is the documented behaviour. The next phase (weight fetch) will
resolve it.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WAN22_REPO_PATH: str = "/home/hugo/codes/flowa-multistep-reinference/data/wan2_2/repo"

# Ensure the upstream repo is on sys.path. Done at module import so
# downstream ``from wan.text2video import WanT2V`` works without each
# caller having to manipulate ``sys.path``.
if WAN22_REPO_PATH not in sys.path:
    sys.path.insert(0, WAN22_REPO_PATH)


def wan_path() -> str:
    """Return the absolute path to the upstream Wan2.2 repo checkout."""
    return WAN22_REPO_PATH


@dataclass(frozen=True)
class WanT2VStateTuple:
    """Lightweight container for the WanT2V geometry used by the adapter.

    Attributes
    ----------
    z_dim : int
        Number of latent channels (``WanModel.z_dim`` = 16).
    frame_num : int
        Number of frames in the output video (must be ``4n+1``).
    latent_t : int
        Latent-frame count ``(frame_num - 1) // vae_stride[0] + 1``.
    latent_h : int
        Latent-height ``output_h // vae_stride[1]``.
    latent_w : int
        Latent-width ``output_w // vae_stride[2]``.
    vae_stride : tuple[int, int, int]
        ``(t_stride, h_stride, w_stride)`` from the upstream config.
    patch_size : tuple[int, int, int]
        ``(t_patch, h_patch, w_patch)`` from the upstream config.
    boundary : float
        ``config.boundary`` (e.g. 0.875 for ``t2v-A14B``).
    param_dtype : str
        Dtype string for autocast (e.g. ``"torch.bfloat16"``).
    """

    z_dim: int
    frame_num: int
    latent_t: int
    latent_h: int
    latent_w: int
    vae_stride: tuple[int, int, int]
    patch_size: tuple[int, int, int]
    boundary: float
    param_dtype: str


def upstream_state_tuple(
    *,
    frame_num: int = 81,
    size: tuple[int, int] = (832, 480),
    task: str = "t2v-A14B",
) -> WanT2VStateTuple:
    """Return the :class:`WanT2VStateTuple` for ``task`` at ``(size, frame_num)``.

    The tuple is built directly from the upstream config; no weights
    are loaded. Cheap: ~1 ms.
    """
    # Import inside the function so a NumPy-only interpreter still
    # imports this module (the upstream ``wan`` package pulls in torch).
    from wan.configs import WAN_CONFIGS  # noqa: WPS433 — local import by design

    cfg = WAN_CONFIGS[task]
    vae_stride = tuple(int(s) for s in cfg.vae_stride)
    patch_size = tuple(int(s) for s in cfg.patch_size)
    # cfg.param_dtype is e.g. torch.bfloat16; store the string form.
    param_dtype = str(getattr(cfg, "param_dtype", "torch.bfloat16"))
    z_dim = int(getattr(cfg, "z_dim", 16))
    boundary = float(cfg.boundary)
    w, h = int(size[0]), int(size[1])
    latent_t = (int(frame_num) - 1) // vae_stride[0] + 1
    latent_h = h // vae_stride[1]
    latent_w = w // vae_stride[2]
    return WanT2VStateTuple(
        z_dim=z_dim,
        frame_num=int(frame_num),
        latent_t=latent_t,
        latent_h=latent_h,
        latent_w=latent_w,
        vae_stride=vae_stride,
        patch_size=patch_size,
        boundary=boundary,
        param_dtype=param_dtype,
    )


def load_upstream_wan_t2v(
    ckpt_dir: str | os.PathLike[str],
    *,
    task: str = "t2v-A14B",
    device_id: int = 0,
    offload_model: bool = True,
    convert_model_dtype: bool = True,
) -> Any:
    """Instantiate the upstream ``WanT2V`` with the ``t2v-A14B`` config.

    Parameters
    ----------
    ckpt_dir : path-like
        Directory containing the upstream weight layout
        (``high_noise_model/``, ``low_noise_model/``,
        ``Wan2.1_VAE.pth``, ``models_t5_umt5-xxl-enc-bf16.pth``).
    task : str
        One of ``WAN_CONFIGS`` keys (default ``"t2v-A14B"``).
    device_id : int
        CUDA device ordinal.
    offload_model : bool
        Reserved for symmetry with the upstream CLI. The WanT2V
        constructor does not take this argument directly — it is
        passed to ``generate()`` instead.
    convert_model_dtype : bool
        Match the upstream CLI default (``True``): cast the DiT
        weights to ``cfg.param_dtype``.

    Returns
    -------
    wan.text2video.WanT2V
        The constructed pipeline (low/high noise models, T5, VAE).

    Raises
    ------
    FileNotFoundError
        When ``ckpt_dir`` does not exist.
    RuntimeError
        When the upstream constructor fails (typically because
        weights are git-LFS pointer stubs — this is the expected
        state until the next phase fetches ~130 GB of weights).
    """
    ckpt_path = Path(ckpt_dir)
    if not ckpt_path.exists():
        raise FileNotFoundError(f"wan2_2_checkpoint_dir_missing:{ckpt_path}")
    # Defer torch import until actually needed — keeps the module
    # importable in a NumPy-only interpreter.
    from wan.configs import WAN_CONFIGS  # noqa: WPS433
    from wan.text2video import WanT2V  # noqa: WPS433

    cfg = WAN_CONFIGS[task]
    return WanT2V(
        config=cfg,
        checkpoint_dir=str(ckpt_path),
        device_id=int(device_id),
        convert_model_dtype=bool(convert_model_dtype),
    )


def run_upstream_t2v(
    prompt: str,
    *,
    ckpt_dir: str | os.PathLike[str],
    out_path: str | os.PathLike[str] | None = None,
    size: tuple[int, int] = (832, 480),
    frame_num: int = 81,
    shift: float = 5.0,
    sample_solver: str = "unipc",
    sampling_steps: int = 30,
    guide_scale: float = 5.0,
    n_prompt: str = "",
    seed: int = -1,
    offload_model: bool = True,
    device_id: int = 0,
) -> str:
    """Run the upstream Wan2.2 T2V ``.generate()`` and write an mp4.

    Returns the path to the written mp4. ``out_path=None`` writes to
    ``data/wan2_2/cache/<uuid>.mp4`` (created if missing).
    """
    from wan.utils.utils import save_video  # noqa: WPS433
    import torch  # noqa: WPS433

    pipe = load_upstream_wan_t2v(
        ckpt_dir,
        device_id=int(device_id),
        offload_model=bool(offload_model),
    )
    video = pipe.generate(
        input_prompt=str(prompt),
        size=tuple(int(s) for s in size),
        frame_num=int(frame_num),
        shift=float(shift),
        sample_solver=str(sample_solver),
        sampling_steps=int(sampling_steps),
        guide_scale=float(guide_scale),
        n_prompt=str(n_prompt),
        seed=int(seed),
        offload_model=bool(offload_model),
    )
    if out_path is None:
        out_path = Path(ckpt_dir).parent / "cache" / "wan2_2_upstream_default.mp4"
    out_path_p = Path(out_path)
    out_path_p.parent.mkdir(parents=True, exist_ok=True)
    save_video(
        video,
        str(out_path_p),
        fps=24,
        nrow=1,
        normalize=True,
        value_range=(-1.0, 1.0),
    )
    return str(out_path_p)


def is_upstream_constructable(ckpt_dir: str | os.PathLike[str]) -> tuple[bool, str]:
    """Probe whether the upstream ``WanT2V`` can be constructed at ``ckpt_dir``.

    Returns ``(True, "ok")`` if construction succeeds, otherwise
    ``(False, "<error_class>: <error_message>")``. Used by the
    framework adapter factory to decide between upstream and
    synthetic modes.
    """
    try:
        load_upstream_wan_t2v(ckpt_dir)
    except Exception as exc:  # noqa: BLE001 — probe
        return False, f"{type(exc).__name__}: {str(exc)[:240]}"
    return True, "ok"


__all__ = [
    "WanT2VStateTuple",
    "WAN22_REPO_PATH",
    "is_upstream_constructable",
    "load_upstream_wan_t2v",
    "run_upstream_t2v",
    "upstream_state_tuple",
    "wan_path",
]

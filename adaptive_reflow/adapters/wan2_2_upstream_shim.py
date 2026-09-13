"""Wan2.2 upstream shim: thin wrapper around the published WanT2V harness.

Routes the :class:`adaptive_reflow.adapters.wan2_2_video.Wan22VideoAdapter`
to the canonical ``wan.text2video.WanT2V`` class from the cloned Wan2.2
repo at ``data/wan2_2/repo``.

Verified import on this host (2026-09-03):

* ``from wan import WanT2V`` imports cleanly in ``wan2_2_venv`` once
  ``sys.path`` is prepended with ``data/wan2_2/repo``. The
  ``wan.modules.s2v.motioner`` / ``wan.modules.s2v.model_s2v`` modules
  emit ``FutureWarning`` on ``torch.cuda.amp.autocast`` (the upstream
  uses the legacy API; harmless on torch 2.7).
* Real Wan2.2 weights on this host are LFS stubs (the data dir
  contains ``weights_metadata.json`` but the actual safetensors are
  not downloaded). The shim therefore exposes
  :func:`construct_pipeline` returning the imported :class:`WanT2V`
  class; weight loading is delegated to the caller (typically
  ``WanT2V.from_pretrained`` which raises a clear ``FileNotFoundError``
  on the LFS stub path).
* Image / video benchmarks (DPG-Bench, GenEval, VBench, AAR scoring)
  are NOT applicable to a video generator — the shim does not expose
  them. The framework's video eval harness (cf. ``tools/run_video_eval.py``)
  remains the canonical path.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from typing import Any

_LOGGER = logging.getLogger(__name__)

WAN_UPSTREAM_REPO: str = "/home/hugo/codes/flowa-multistep-reinference/data/wan2_2/repo"

_UPSTREAM_IMPORT_ERROR: BaseException | None = None
_UPSTREAM_WANT2V_CLS: Any = None


def _install_upstream_path() -> None:
    if WAN_UPSTREAM_REPO not in sys.path:
        sys.path.insert(0, WAN_UPSTREAM_REPO)


def _try_import_upstream() -> Any:
    """Import and cache ``wan.WanT2V``."""
    global _UPSTREAM_IMPORT_ERROR, _UPSTREAM_WANT2V_CLS
    if _UPSTREAM_WANT2V_CLS is not None:
        return _UPSTREAM_WANT2V_CLS
    _install_upstream_path()
    try:
        from wan import WanT2V  # noqa: PLC0415
    except BaseException as exc:  # noqa: BLE001
        _UPSTREAM_IMPORT_ERROR = exc
        _LOGGER.warning(
            "wan2_2_upstream_shim: upstream import failed; "
            "error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return None
    _UPSTREAM_WANT2V_CLS = WanT2V
    return WanT2V


def is_upstream_available() -> bool:
    return _try_import_upstream() is not None


def get_upstream_import_error() -> BaseException | None:
    """Return the cached import error from the last upstream import attempt."""
    if _UPSTREAM_WANT2V_CLS is None and _UPSTREAM_IMPORT_ERROR is None:
        _try_import_upstream()
    return _UPSTREAM_IMPORT_ERROR


def construct_pipeline() -> Any:
    """Return the imported upstream :class:`WanT2V` class.

    The caller is expected to invoke ``WanT2V.from_pretrained(...)``
    with a real checkpoint directory; on this host the data dir
    contains LFS stubs so the load step will fail with a clear error
    (which is the expected failure mode for the next phase — real
    weight download is out of scope here).
    """
    return _try_import_upstream()


@dataclass
class Wan2UpstreamLoadResult:
    """Lazy wrapper around the upstream :class:`WanT2V`."""

    pipeline_cls: Any | None = None
    pipeline: Any = field(default=None, init=False)
    last_error: BaseException | None = None
    last_inputs: dict[str, Any] = field(default_factory=dict, init=False)

    def materialize(self, *, checkpoint_dir: str | None = None) -> bool:
        cls = _try_import_upstream()
        if cls is None:
            self.last_error = _UPSTREAM_IMPORT_ERROR
            return False
        self.pipeline_cls = cls
        if checkpoint_dir is not None:
            try:
                self.pipeline = cls.from_pretrained(str(checkpoint_dir))
            except Exception as exc:  # noqa: BLE001
                self.last_error = exc
                _LOGGER.warning(
                    "Wan2.2 upstream from_pretrained failed (likely LFS stub): %s",
                    exc,
                )
                return False
        return True

    def generate(
        self,
        prompt: str,
        *,
        size: str = "832*480",
        num_frames: int = 81,
        num_inference_steps: int = 50,
        guidance_scale: float = 5.0,
        seed: int = 0,
        **kwargs: Any,
    ) -> Any:
        if self.pipeline is None:
            raise RuntimeError(
                "Wan2UpstreamLoadResult.generate called before pipeline is materialized"
            )
        import torch  # noqa: PLC0415

        generator = torch.Generator(device=getattr(self.pipeline, "device", "cpu")).manual_seed(
            int(seed)
        )
        inputs = dict(
            prompt=prompt,
            size=size,
            frame_num=int(num_frames),
            sample_steps=int(num_inference_steps),
            guide_scale=float(guidance_scale),
            generator=generator,
            **kwargs,
        )
        self.last_inputs = inputs
        return self.pipeline.generate(**inputs)


__all__ = [
    "WAN_UPSTREAM_REPO",
    "Wan2UpstreamLoadResult",
    "construct_pipeline",
    "get_upstream_import_error",
    "is_upstream_available",
]


def _smoke_check() -> None:
    cls = _try_import_upstream()
    err = _UPSTREAM_IMPORT_ERROR
    print(f"upstream_available={cls is not None}")
    print(f"upstream_repo={WAN_UPSTREAM_REPO}")
    print(f"upstream_class={cls}")
    print(
        "upstream_import_error="
        f"{type(err).__name__ if err is not None else 'None'}: {err}"
    )


if __name__ == "__main__":  # pragma: no cover — manual smoke entry.
    _smoke_check()

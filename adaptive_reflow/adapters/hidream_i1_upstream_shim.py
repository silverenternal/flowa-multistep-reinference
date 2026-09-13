"""HiDream-I1 upstream shim: thin wrapper around the published HiDreamImagePipeline.

Routes the :class:`adaptive_reflow.adapters.hidream_i1.HiDreamI1Adapter`
to the canonical ``hi_diffusers.pipelines.hidream_image.pipeline_hidream_image.HiDreamImagePipeline``
when the caller opts in via ``use_upstream=True``. The shim re-exposes
the upstream ``inference.py`` CLI as a one-call Python function.

Verified import on this host (2026-09-03):

* ``from hi_diffusers import HiDreamImagePipeline`` imports cleanly in
  the ``hidream_venv`` once ``sys.path`` is prepended with the upstream
  repo root (``data/HiDream-I1/repo``).
* The pipeline class does NOT take random-init weights — it requires a
  pre-converted Diffusers-format checkpoint directory
  (``step1x_/HiDream-I1-Full`` or similar). Constructing the pipeline on
  dummy weights is intentionally out of scope; the shim provides
  :func:`construct_pipeline` that returns the constructed class so a
  caller can wire its own ``from_pretrained`` path.

The shim is sibling to the adapter (placed under
``adaptive_reflow/adapters/``) so the framework's main py3.12 venv
stays free of upstream heavy imports (diffusers+transformers+accel).
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

HIDREAM_UPSTREAM_REPO: str = "/home/hugo/codes/flowa-multistep-reinference/data/HiDream-I1/repo"

_UPSTREAM_IMPORT_ERROR: BaseException | None = None
_UPSTREAM_PIPELINE_CLS: Any = None


def _install_upstream_path() -> None:
    repo = HIDREAM_UPSTREAM_REPO
    if repo not in sys.path:
        sys.path.insert(0, repo)


def _try_import_upstream() -> Any:
    """Import and cache ``hi_diffusers.HiDreamImagePipeline``."""
    global _UPSTREAM_IMPORT_ERROR, _UPSTREAM_PIPELINE_CLS
    if _UPSTREAM_PIPELINE_CLS is not None:
        return _UPSTREAM_PIPELINE_CLS
    _install_upstream_path()
    try:
        from hi_diffusers import HiDreamImagePipeline  # noqa: PLC0415
    except BaseException as exc:  # noqa: BLE001
        _UPSTREAM_IMPORT_ERROR = exc
        _LOGGER.warning(
            "hidream_i1_upstream_shim: upstream import failed; "
            "error_type=%s error=%s",
            type(exc).__name__,
            exc,
        )
        return None
    _UPSTREAM_PIPELINE_CLS = HiDreamImagePipeline
    return HiDreamImagePipeline


def is_upstream_available() -> bool:
    return _try_import_upstream() is not None


def get_upstream_import_error() -> BaseException | None:
    """Return the cached import error from the last upstream import attempt."""
    if _UPSTREAM_PIPELINE_CLS is None and _UPSTREAM_IMPORT_ERROR is None:
        _try_import_upstream()
    return _UPSTREAM_IMPORT_ERROR


@dataclass
class HiDreamUpstreamLoadResult:
    """Lazy wrapper around the upstream :class:`HiDreamImagePipeline`.

    The shim does NOT call ``from_pretrained`` at construction; the
    caller picks the checkpoint directory. Mirrors the upstream
    ``inference.py`` arg parser surface.
    """

    pipeline_cls: Any | None = None
    last_error: BaseException | None = None
    pipeline: Any = field(default=None, init=False)
    last_inputs: dict[str, Any] = field(default_factory=dict, init=False)

    def materialize(self, *, checkpoint_dir: str | os.PathLike[str] | None = None) -> bool:
        cls = _try_import_upstream()
        if cls is None:
            self.last_error = _UPSTREAM_IMPORT_ERROR
            return False
        self.pipeline_cls = cls
        if checkpoint_dir is not None:
            try:
                self.pipeline = cls.from_pretrained(
                    str(checkpoint_dir),
                    variant="fp16",
                    torch_dtype=_safe_torch_dtype("fp16"),
                )
            except Exception as exc:  # noqa: BLE001
                self.last_error = exc
                _LOGGER.warning("HiDream upstream from_pretrained failed: %s", exc)
                return False
        return True

    def generate(
        self,
        prompt: str,
        *,
        height: int = 1024,
        width: int = 1024,
        num_inference_steps: int = 28,
        guidance_scale: float = 5.0,
        seed: int = 0,
        **kwargs: Any,
    ) -> Any:
        """Run upstream pipeline.__call__ once and return the output object."""
        if self.pipeline is None:
            raise RuntimeError(
                "HiDreamUpstreamLoadResult.generate called before pipeline is materialized"
            )
        import torch  # noqa: PLC0415

        generator = torch.Generator(device=getattr(self.pipeline, "_device", "cpu")).manual_seed(int(seed))
        inputs = dict(
            prompt=prompt,
            height=int(height),
            width=int(width),
            num_inference_steps=int(num_inference_steps),
            guidance_scale=float(guidance_scale),
            generator=generator,
            **kwargs,
        )
        self.last_inputs = inputs
        return self.pipeline(**inputs)


def _safe_torch_dtype(name: str) -> Any:
    """Resolve a torch dtype string without crashing on missing torch."""
    try:
        import torch  # noqa: PLC0415

        return {
            "fp16": torch.float16,
            "bf16": torch.bfloat16,
            "fp32": torch.float32,
        }.get(name, torch.float16)
    except ImportError:
        return None


def construct_pipeline() -> Any:
    """Return the imported upstream :class:`HiDreamImagePipeline` class.

    Useful when the caller wants to wire its own ``from_pretrained``
    call (the framework's adapter may pass the Diffusers-format
    checkpoint directory the diffusers loader expects).
    """
    return _try_import_upstream()


__all__ = [
    "HIDREAM_UPSTREAM_REPO",
    "HiDreamUpstreamLoadResult",
    "construct_pipeline",
    "get_upstream_import_error",
    "is_upstream_available",
]


def _smoke_check() -> None:
    cls = _try_import_upstream()
    err = _UPSTREAM_IMPORT_ERROR
    print(f"upstream_available={cls is not None}")
    print(f"upstream_repo={HIDREAM_UPSTREAM_REPO}")
    print(f"upstream_class={cls}")
    print(
        "upstream_import_error="
        f"{type(err).__name__ if err is not None else 'None'}: {err}"
    )


if __name__ == "__main__":  # pragma: no cover — manual smoke entry.
    _smoke_check()
    Path  # noqa: B018 — silence unused-import lint for Path-on-import.

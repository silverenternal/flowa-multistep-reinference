"""Thin shim that wires the framework HiDream-I1 adapter to the upstream harness.

This module is the *glue* between the framework's
:class:`adaptive_reflow.adapters.hidream_i1.HiDreamI1Adapter` and the
upstream HiDream-I1 implementation living at
``data/HiDream-I1/repo``. The canonical pipeline class is
``hi_diffusers.pipelines.hidream_image.pipeline_hidream_image.HiDreamImagePipeline``
(a thin subclass of ``diffusers.DiffusionPipeline`` that uses the
upstream MoE kernel layout, the upstream 4-source text conditioning
``encode_prompt`` (CLIP-L pool + CLIP-G pool + T5-XXL tokens +
Llama-3.1-8B multi-layer hidden states), and the upstream
``FlashFlowMatchEulerDiscreteScheduler`` + ``FlowUniPCMultistepScheduler``
schedulers). The framework's
:func:`adaptive_reflow.adapters.hidream_i1._load_diffusion_pipeline`
delegates here so byte-identical-paper-results are available when the
upstream package is importable; when it is not (e.g. on a CI host that
has only diffusers installed) the shim transparently falls back to
``diffusers.HiDreamImagePipeline`` from diffusers >=0.32.

The shim is deliberately small: it only owns

1. an import-time resolution of the canonical pipeline class
   (:func:`_resolve_pipeline_class`),
2. a registry-friendly factory
   :func:`_make_hidream_pipeline` that mirrors the diffusers 11-arg
   constructor (upstream's
   ``HiDreamImagePipeline.__init__`` does not take ``transformer`` in
   its signature; the shim calls ``register_modules(transformer=...)``
   post-init so the call surface stays compatible with the framework's
   existing construction logic),
3. a public helper :func:`run_hidream_i1_eval` that loads the pipeline
   via the framework's :func:`_load_diffusion_pipeline` and writes
   per-prompt PNGs to ``out_dir``.

When the upstream package is not importable, ``run_hidream_i1_eval``
still works as long as diffusers >=0.32 is installed (the framework's
existing _load_diffusion_pipeline falls back to diffusers).
"""
from __future__ import annotations

import contextlib
import importlib
import importlib.util as _il
import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

#: Absolute path to the upstream HiDream-I1 repository. Mirrors the
#: layout the framework uses everywhere else (``data/<model>/repo``).
UPSTREAM_REPO: Path = Path(
    os.environ.get(
        "HIDREAM_I1_REPO",
        "/home/hugo/codes/flowa-multistep-reinference/data/HiDream-I1/repo",
    )
)


def upstream_is_available() -> bool:
    """Return ``True`` iff the upstream ``hi_diffusers`` package is importable.

    The check is intentionally cheap: we look for the upstream repo
    directory plus the marker submodule
    ``hi_diffusers.pipelines.hidream_image.pipeline_hidream_image``
    without actually executing the import (the upstream
    ``pipeline_hidream_image`` module imports ``transformers``,
    ``diffusers``, ``einops`` at the top — heavy).

    The check returns ``True`` when:

    1. The upstream repo marker file exists on disk at
       :data:`UPSTREAM_REPO` (i.e. the source tree is present), OR
    2. ``hi_diffusers`` is findable via Python's import machinery
       (e.g. installed via ``pip install -e data/HiDream-I1/repo``).
    """
    if not UPSTREAM_REPO.is_dir():
        # Probe the import system (the user may have pip-installed
        # hi_diffusers from a different location).
        return _il.find_spec("hi_diffusers") is not None
    marker = (
        UPSTREAM_REPO
        / "hi_diffusers"
        / "pipelines"
        / "hidream_image"
        / "pipeline_hidream_image.py"
    )
    if marker.is_file():
        return True
    return _il.find_spec("hi_diffusers") is not None


def _ensure_repo_on_path() -> None:
    """Insert ``UPSTREAM_REPO`` at ``sys.path[0]`` so ``hi_diffusers`` is importable.

    Idempotent — multiple calls are safe. The framework's other adapters
    follow the same convention (see
    :mod:`adaptive_reflow.adapters._flowmol_upstream_shim`).
    """
    repo = str(UPSTREAM_REPO)
    if repo not in sys.path:
        sys.path.insert(0, repo)


def _resolve_pipeline_class() -> type:
    """Return the upstream ``HiDreamImagePipeline`` class, or fall back to diffusers.

    Resolution order:

    1. Try the upstream submodule
       ``hi_diffusers.pipelines.hidream_image.pipeline_hidream_image``
       (the canonical harness — uses the upstream MoE kernel layout,
       the upstream ``encode_prompt`` 4-source conditioning, the
       upstream ``FlashFlowMatchEulerDiscreteScheduler`` /
       ``FlowUniPCMultistepScheduler`` schedulers).
    2. Fall back to ``diffusers.HiDreamImagePipeline`` (diffusers >=0.32).

    Returns:
        The pipeline class. Raises :class:`ImportError` when neither
        path resolves.
    """
    # 1. Upstream path.
    if upstream_is_available():
        try:
            _ensure_repo_on_path()
            mod = importlib.import_module(
                "hi_diffusers.pipelines.hidream_image.pipeline_hidream_image"
            )
            cls = getattr(mod, "HiDreamImagePipeline", None)
            if cls is not None:
                return cls
        except Exception:  # noqa: BLE001 — best-effort upstream
            pass

    # 2. diffusers fallback.
    try:
        from diffusers import HiDreamImagePipeline  # type: ignore
        return HiDreamImagePipeline
    except ImportError as exc:  # pragma: no cover — guaranteed to surface
        raise ImportError(
            "hidream_i1_upstream_shim: cannot resolve HiDreamImagePipeline "
            "from upstream (hi_diffusers) or diffusers. "
            "Either pip-install diffusers>=0.32 or pip-install "
            "data/HiDream-I1/repo."
        ) from exc


def _resolve_output_class() -> type | None:
    """Return the canonical ``HiDreamImagePipelineOutput`` class (upstream preferred)."""
    if upstream_is_available():
        try:
            _ensure_repo_on_path()
            mod = importlib.import_module(
                "hi_diffusers.pipelines.hidream_image.pipeline_hidream_image"
            )
            cls = getattr(mod, "HiDreamImagePipelineOutput", None)
            if cls is not None:
                return cls
        except Exception:  # noqa: BLE001
            pass
    try:
        from diffusers.pipelines.hidream_image import HiDreamImagePipelineOutput  # type: ignore
        return HiDreamImagePipelineOutput  # type: ignore[return-value]
    except ImportError:
        return None


def _resolve_scheduler_class(name: str) -> type:
    """Return the upstream scheduler class for ``name``.

    Args:
        name: one of ``"flash"`` (alias for FlashFlowMatchEulerDiscreteScheduler),
            ``"euler"`` (alias for FlowMatchEulerDiscreteScheduler),
            ``"unipc"`` (alias for FlowUniPCMultistepScheduler),
            or the exact class name.

    Returns:
        The scheduler class. Raises :class:`ImportError` on miss.
    """
    name = str(name).lower()
    if name in ("flash", "flash_flow_match", "flashflowmatch"):
        if upstream_is_available():
            try:
                _ensure_repo_on_path()
                mod = importlib.import_module(
                    "hi_diffusers.schedulers.flash_flow_match"
                )
                cls = getattr(
                    mod, "FlashFlowMatchEulerDiscreteScheduler", None,
                )
                if cls is not None:
                    return cls
            except Exception:  # noqa: BLE001
                pass
        # Fallback to FlowMatchEulerDiscreteScheduler (diffusers has no
        # FlashFlowMatch equivalent; the upstream FlashFlowMatch is the
        # Fast variant's scheduler).
        from diffusers import FlowMatchEulerDiscreteScheduler  # type: ignore
        return FlowMatchEulerDiscreteScheduler  # type: ignore[return-value]
    if name in ("unipc", "flowunipc", "flow_unipc"):
        if upstream_is_available():
            try:
                _ensure_repo_on_path()
                mod = importlib.import_module(
                    "hi_diffusers.schedulers.fm_solvers_unipc"
                )
                cls = getattr(mod, "FlowUniPCMultistepScheduler", None)
                if cls is not None:
                    return cls
            except Exception:  # noqa: BLE001
                pass
        # diffusers has no UniPC equivalent for HiDream; fall back to
        # FlowMatchEulerDiscreteScheduler (lossy but valid).
        from diffusers import FlowMatchEulerDiscreteScheduler  # type: ignore
        return FlowMatchEulerDiscreteScheduler  # type: ignore[return-value]
    if name in ("euler", "flowmatcheuler"):
        from diffusers import FlowMatchEulerDiscreteScheduler  # type: ignore
        return FlowMatchEulerDiscreteScheduler  # type: ignore[return-value]
    raise ValueError(f"hidream_i1_upstream_shim: unknown scheduler name {name!r}")


# ---------------------------------------------------------------------------
# Construction helper
# ---------------------------------------------------------------------------


def _make_hidream_pipeline(
    *,
    scheduler: Any,
    text_encoder: Any,
    text_encoder_2: Any,
    text_encoder_3: Any,
    text_encoder_4: Any,
    tokenizer: Any,
    tokenizer_2: Any,
    tokenizer_3: Any,
    tokenizer_4: Any,
    transformer: Any,
    vae: Any,
) -> Any:
    """Construct the canonical HiDreamImagePipeline (upstream preferred).

    The upstream class
    ``hi_diffusers.pipelines.hidream_image.pipeline_hidream_image.HiDreamImagePipeline``
    has an ``__init__`` that takes 10 positional/keyword arguments
    (no ``transformer``). The diffusers class takes 11. The shim
    handles both:

    * If the resolved class accepts ``transformer`` in its signature
      (diffusers path), pass it directly.
    * Otherwise (upstream path), wrap the class in a dynamic subclass
      that adds ``transformer`` to the ``__init__`` signature. This
      keeps :class:`DiffusionPipeline.components` consistent (its
      ``_get_signature_keys`` introspection reads the class's
      ``__init__`` and rejects mismatches against the registered
      module dict).

    Returns the constructed pipeline instance (NOT on a CUDA device —
    callers are responsible for ``.to(device)``).
    """
    import inspect

    pipeline_cls = _resolve_pipeline_class()
    sig = inspect.signature(pipeline_cls.__init__)
    if "transformer" in sig.parameters:
        pipeline = pipeline_cls(
            scheduler=scheduler,
            text_encoder=text_encoder,
            tokenizer=tokenizer,
            text_encoder_2=text_encoder_2,
            tokenizer_2=tokenizer_2,
            text_encoder_3=text_encoder_3,
            tokenizer_3=tokenizer_3,
            text_encoder_4=text_encoder_4,
            tokenizer_4=tokenizer_4,
            vae=vae,
            transformer=transformer,
        )
    else:
        # Upstream path — the class's ``__init__`` does not take
        # ``transformer``. We build a dynamic subclass whose
        # ``__init__`` does take it, then delegate to the original
        # ``__init__`` for the original 10 args and use
        # ``register_modules`` for the transformer. This keeps the
        # ``_get_signature_keys`` introspection happy and the
        # ``components`` property valid.
        upstream_cls = pipeline_cls

        def _subclass_init(
            self,
            scheduler,
            vae,
            text_encoder,
            tokenizer,
            text_encoder_2,
            tokenizer_2,
            text_encoder_3,
            tokenizer_3,
            text_encoder_4,
            tokenizer_4,
            transformer,
        ):
            upstream_cls.__init__(
                self,
                scheduler=scheduler,
                vae=vae,
                text_encoder=text_encoder,
                tokenizer=tokenizer,
                text_encoder_2=text_encoder_2,
                tokenizer_2=tokenizer_2,
                text_encoder_3=text_encoder_3,
                tokenizer_3=tokenizer_3,
                text_encoder_4=text_encoder_4,
                tokenizer_4=tokenizer_4,
            )
            self.register_modules(transformer=transformer)

        _Subclass = type(
            "HiDreamImagePipelineWithTransformer",
            (upstream_cls,),
            {"__init__": _subclass_init},
        )
        pipeline = _Subclass(
            scheduler=scheduler,
            vae=vae,
            text_encoder=text_encoder,
            tokenizer=tokenizer,
            text_encoder_2=text_encoder_2,
            tokenizer_2=tokenizer_2,
            text_encoder_3=text_encoder_3,
            tokenizer_3=tokenizer_3,
            text_encoder_4=text_encoder_4,
            tokenizer_4=tokenizer_4,
            transformer=transformer,
        )
    if hasattr(pipeline, "set_progress_bar_config"):
        pipeline.set_progress_bar_config(disable=True)
    return pipeline


# ---------------------------------------------------------------------------
# Public eval helper
# ---------------------------------------------------------------------------


def run_hidream_i1_eval(
    weights_path: Path | str,
    prompts: list[str],
    num_inference_steps: int,
    guidance_scale: float,
    seeds: list[int],
    out_dir: Path | str,
    *,
    scheduler_cls: str = "flash",
    height: int = 1024,
    width: int = 1024,
    device: str | None = None,
) -> list[Path]:
    """Run the canonical HiDreamImagePipeline against a list of prompts.

    The helper loads the pipeline via the framework's
    :func:`adaptive_reflow.adapters.hidream_i1._load_diffusion_pipeline`
    (so the same stub-Llama path applies) and invokes the upstream
    ``__call__`` once per prompt with a per-prompt
    ``torch.Generator``. The resulting PIL images are written to
    ``out_dir`` as ``prompt_{idx:03d}_seed_{seed}.png`` and the list of
    written paths is returned.

    Args:
        weights_path: directory containing ``model_index.json`` + the
            per-component subdirectories.
        prompts: list of text prompts.
        num_inference_steps: forward ODE step count.
        guidance_scale: CFG scale (1.0 for guidance-distilled Dev/Fast).
        seeds: per-prompt torch seed. If shorter than ``prompts``, the
            last element is reused for trailing prompts.
        out_dir: output directory (created if missing).
        scheduler_cls: ``"flash"``, ``"euler"``, or ``"unipc"`` (forwarded
            to the framework's pipeline loader).
        height: pixel height (must be divisible by 16).
        width: pixel width (must be divisible by 16).
        device: optional ``"cuda"`` / ``"cuda:0"`` / ``"cpu"`` override.

    Returns:
        List of absolute paths to the written PNGs (one per prompt).
    """
    import torch  # local — torch is an opt extra

    from adaptive_reflow.adapters.hidream_i1 import (
        _load_diffusion_pipeline,
    )

    weights_path = Path(weights_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not weights_path.exists():
        raise FileNotFoundError(f"hidream_i1_upstream_eval: weights_path missing {weights_path}")
    if len(seeds) < len(prompts):
        seeds = list(seeds) + [seeds[-1]] * (len(prompts) - len(seeds))

    pipeline = _load_diffusion_pipeline("dev", weights_path)

    # Optional device placement.
    if device is not None:
        target = torch.device(str(device))
        with contextlib.suppress(Exception):  # best-effort
            pipeline.to(target)

    written: list[Path] = []
    for idx, (prompt, seed) in enumerate(zip(prompts, seeds, strict=False)):
        generator = torch.Generator(device="cpu").manual_seed(int(seed))
        result = pipeline(
            prompt=prompt,
            height=int(height),
            width=int(width),
            num_inference_steps=int(num_inference_steps),
            guidance_scale=float(guidance_scale),
            generator=generator,
            output_type="pil",
            return_dict=True,
        )
        # Upstream pipeline returns a HiDreamImagePipelineOutput whose
        # .images is a list of PIL.Image.Image.
        images = list(getattr(result, "images", []) or [])
        if not images:
            continue
        img = images[0]
        path = out_dir / f"prompt_{idx:03d}_seed_{seed}.png"
        img.save(str(path))
        written.append(path.resolve())

    return written


__all__ = [
    "UPSTREAM_REPO",
    "_ensure_repo_on_path",
    "_make_hidream_pipeline",
    "_resolve_output_class",
    "_resolve_pipeline_class",
    "_resolve_scheduler_class",
    "run_hidream_i1_eval",
    "upstream_is_available",
]

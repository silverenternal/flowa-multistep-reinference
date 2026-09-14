"""Canonical CLIPScore abstraction (Phase B / Phase C).

This module is the *single source of truth* for CLIPScore computation
in the framework. Three tool scripts previously embedded near-identical
copies of the same CLIPScore math, each with subtle differences:

* :func:`tools.run_image_eval.compute_clipscore` — uses
  :class:`transformers.CLIPModel` + :class:`transformers.CLIPProcessor`
  with the Hessel et al. 2021 ``100 × max(0, cos)`` paper scale.
* :func:`tools.run_sota_hidream_i1_experiment.compute_clipscore` —
  mirrors the same pipeline but uses the ``AutoModel`` / ``AutoProcessor``
  path and a different default batch size.
* :func:`tools.run_sota_lumina_image_2_0_experiment.compute_clipscore` —
  re-implements the same L2-normalise + dot-product cosine path with
  small numerical differences (no ``torch.clamp(min=0)`` before scaling).

This module collapses all three behind a single
:class:`CLIPScoreProtocol` interface with a concrete
:class:`HFCosineClipScoreEvaluator` implementation. The cosine-similarity
arithmetic is delegated to one private
:meth:`HFCosineClipScoreEvaluator._score_pairs` so any future numerical
refinement (e.g. switching to a paper-faithful ``max(0, cos)`` policy)
lands in one place.

Numerical contract
------------------

* Image and text embeddings are L2-normalised along the feature axis.
  Cosine similarity is therefore exactly the per-row dot product of the
  normalised embeddings — there is no separate bias term.
* The default :data:`DEFAULT_CLIP_MODEL_NAME` is
  ``openai/clip-vit-base-patch32`` (``~600 MB``), chosen for
  smoke-friendliness; the ``openai/clip-vit-large-patch14`` variant is
  available via the constructor.
* Optional paper-scale (``100.0``) mirrors Hessel et al. 2021 — applied
  as ``100 * max(0, cos)`` so the output is directly comparable to the
  published CLIPScore numbers. When ``paper_scale`` is ``None`` the
  raw cosine is returned.
* On missing :mod:`transformers` dependency the evaluator returns
  ``CLIPScoreResult(mean=float('nan'), std=float('nan'), n_pairs=n,
  model_name=...)`` — the *graceful NaN* convention used by
  ``tools.run_image_eval`` and ``tools.run_sota_hidream_i1_experiment``.
  Callers can detect the failure mode by inspecting ``math.isnan(mean)``.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

__all__ = [
    "DEFAULT_CLIP_MODEL_NAME",
    "CLIPSCORE_PAPER_SCALE",
    "CLIPScoreProtocol",
    "CLIPScoreResult",
    "HFCosineClipScoreEvaluator",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


#: Canonical default CLIP model — small (~600 MB), smoke-friendly.
#: Override via :class:`HFCosineClipScoreEvaluator` constructor.
DEFAULT_CLIP_MODEL_NAME: str = "openai/clip-vit-base-patch32"

#: Alternative high-quality CLIP model — large-patch14 (~1.7 GB).
CLIP_LARGE_MODEL_NAME: str = "openai/clip-vit-large-patch14"

#: Paper-faithful CLIPScore scaling from Hessel et al. 2021
#: (``100 * max(0, cos)``). The framework's default is to *not* apply
#: this scaling (paper_scale=None) so the raw cosine similarity is
#: returned — operators opt into paper-comparable numbers by passing
#: :data:`CLIPSCORE_PAPER_SCALE`.
CLIPSCORE_PAPER_SCALE: float = 100.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CLIPScoreResult:
    """Structured CLIPScore computation result.

    ``mean`` and ``std`` are the per-pair cosine-similarity aggregate
    over the batch. When the paper-scale (``100 * max(0, cos)``) is
    applied, ``mean`` and ``std`` are scaled accordingly. ``n_pairs``
    is the number of (image, prompt) pairs the aggregate was computed
    on; ``model_name`` is the canonical CLIP model identifier used
    (e.g. ``"openai/clip-vit-base-patch32"``).
    """

    mean: float
    std: float
    n_pairs: int
    model_name: str

    def __post_init__(self) -> None:
        # ``mean`` / ``std`` may be ``nan`` (graceful-dep-missing); we
        # accept any real number but reject booleans / non-numerics.
        for nm in ("mean", "std"):
            v = getattr(self, nm)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise ValueError(
                    f"CLIPScoreResult.{nm} must be a real number, "
                    f"got {type(v).__name__}"
                )
        if not isinstance(self.n_pairs, int) or self.n_pairs < 0:
            raise ValueError(
                f"CLIPScoreResult.n_pairs must be a non-negative int, "
                f"got {self.n_pairs!r}"
            )
        if not isinstance(self.model_name, str) or not self.model_name:
            raise ValueError(
                f"CLIPScoreResult.model_name must be a non-empty str, "
                f"got {self.model_name!r}"
            )

    @property
    def is_finite(self) -> bool:
        """Return ``True`` iff ``mean`` and ``std`` are both finite."""
        return bool(math.isfinite(float(self.mean)) and math.isfinite(float(self.std)))

    @classmethod
    def nan_result(cls, *, n_pairs: int, model_name: str) -> CLIPScoreResult:
        """Build a graceful-NaN :class:`CLIPScoreResult`.

        Used when the :mod:`transformers` dependency is missing or the
        underlying model fails to load. Both ``mean`` and ``std`` are
        ``float('nan')``; ``n_pairs`` and ``model_name`` are preserved
        so downstream manifests can still correlate the missing-result
        record with the batch that produced it.
        """
        return cls(
            mean=float("nan"),
            std=float("nan"),
            n_pairs=int(n_pairs),
            model_name=str(model_name),
        )


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class CLIPScoreProtocol(ABC):
    """Abstract CLIPScore interface.

    The single public entry point is :meth:`score`, which accepts a
    batch of images and their associated prompts and returns a
    :class:`CLIPScoreResult`. Implementations MUST be safe to call on
    missing dependencies — the graceful-NaN contract (see
    :meth:`CLIPScoreResult.nan_result`) is the canonical failure mode.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the canonical CLIP model identifier."""
        ...

    @abstractmethod
    def score(
        self,
        images: Any,
        prompts: list[str],
    ) -> CLIPScoreResult:
        """Compute CLIPScore over a batch of ``(image, prompt)`` pairs.

        :param images: An ``(N, C, H, W)`` numpy/torch array, a list of
            ``PIL.Image`` instances, or any other batch container the
            concrete evaluator knows how to interpret.
        :param prompts: A list of ``N`` prompt strings (one per image).
        :returns: :class:`CLIPScoreResult` with the per-pair cosine
            aggregate. When the dependency is missing the result is
            graceful-NaN (see :meth:`CLIPScoreResult.nan_result`).
        """
        ...

    @abstractmethod
    def config_hash(self) -> str:
        """Return a stable digest binding the model + scale policy."""
        ...


# ---------------------------------------------------------------------------
# Concrete HuggingFace-backed cosine CLIPScore evaluator
# ---------------------------------------------------------------------------


class HFCosineClipScoreEvaluator(CLIPScoreProtocol):
    """HuggingFace-``transformers`` CLIPScore evaluator.

    Loads a CLIP model via :class:`transformers.AutoModel` and a paired
    :class:`transformers.AutoProcessor`. Per-pair cosine similarity is
    computed as the L2-normalised dot product of image and text
    embeddings — the canonical CLIPScore definition.

    Parameters
    ----------
    model_name
        HuggingFace model identifier. Default
        :data:`DEFAULT_CLIP_MODEL_NAME`.
    paper_scale
        Optional paper-scale factor. ``100.0`` matches Hessel et al.
        2021 (``100 * max(0, cos)``); ``None`` returns the raw cosine.
    device
        Optional torch device override. ``None`` resolves to CUDA when
        available, else CPU.

    Notes
    -----
    The model and processor are loaded lazily on the first call to
    :meth:`score` (or eagerly via :meth:`ensure_loaded`) so importing
    this module does NOT require :mod:`transformers`. On missing
    :mod:`transformers` or :mod:`torch` dependency every public method
    returns graceful NaN — callers can detect this via
    :meth:`CLIPScoreResult.nan_result` or by inspecting ``math.isnan``.
    """

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_CLIP_MODEL_NAME,
        paper_scale: float | None = None,
        device: Any = None,
    ) -> None:
        if not isinstance(model_name, str) or not model_name:
            raise ValueError(
                f"model_name must be a non-empty str, got {model_name!r}"
            )
        if paper_scale is not None:
            if isinstance(paper_scale, bool) or not isinstance(paper_scale, (int, float)):
                raise ValueError(
                    f"paper_scale must be a real number or None, "
                    f"got {type(paper_scale).__name__}"
                )
            ps = float(paper_scale)
            if not (math.isfinite(ps) and ps > 0.0):
                raise ValueError(
                    f"paper_scale must be finite and > 0, got {paper_scale!r}"
                )
            paper_scale = ps
        self._model_name: str = str(model_name)
        self._paper_scale: float | None = (
            float(paper_scale) if paper_scale is not None else None
        )
        self._device: Any = device  # None → resolved lazily on load
        # Cached loaded model / processor (None until first use).
        self._model: Any = None
        self._processor: Any = None
        self._load_attempted: bool = False
        self._load_error: Exception | None = None

    # ------------------------------------------------------------------
    # Protocol surface
    @property
    def model_name(self) -> str:
        """Return the configured CLIP model identifier."""
        return str(self._model_name)

    @property
    def paper_scale(self) -> float | None:
        """Return the configured paper-scale factor (``None`` → raw cosine)."""
        return self._paper_scale

    @property
    def is_loaded(self) -> bool:
        """Return ``True`` iff the model + processor have been loaded."""
        return self._model is not None and self._processor is not None

    def ensure_loaded(self) -> None:
        """Eagerly load the model + processor (idempotent).

        Raises :class:`ImportError` when :mod:`transformers` or
        :mod:`torch` is unavailable. Successful loads are cached so
        subsequent calls are zero-cost.
        """
        if self.is_loaded:
            return
        if self._load_attempted and self._load_error is not None:
            raise self._load_error
        try:
            import torch  # noqa: F401
            from transformers import AutoModel, AutoProcessor  # noqa: F401
        except ImportError as exc:
            self._load_attempted = True
            self._load_error = exc
            raise
        # Import resolved; load lazily. We re-resolve inside the try
        # block so the raised ImportError has the right traceback.
        try:
            import torch
            from transformers import AutoModel, AutoProcessor
        except ImportError as exc:  # pragma: no cover — defensive
            self._load_attempted = True
            self._load_error = exc
            raise
        model = AutoModel.from_pretrained(
            self._model_name,
            local_files_only=True,
            use_safetensors=False,
        )
        processor = AutoProcessor.from_pretrained(  # type: ignore[no-untyped-call]
            self._model_name,
            local_files_only=True,
        )
        model.eval()
        # Resolve device: honour explicit override, else CUDA → CPU.
        resolved_device = self._device
        if resolved_device is None:
            resolved_device = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )
        model = model.to(resolved_device)
        self._model = model
        self._processor = processor
        self._device = resolved_device
        self._load_attempted = True
        self._load_error = None

    def score(
        self,
        images: Any,
        prompts: list[str],
    ) -> CLIPScoreResult:
        """Compute CLIPScore over a batch of ``(image, prompt)`` pairs.

        Delegates the cosine arithmetic to
        :meth:`_score_pairs` so any future numerical refinement (e.g.
        switching to a paper-faithful ``max(0, cos)`` policy or
        switching to fp16) lands in one place. The full-pipeline path
        here is one of two batch entry points; the other is
        :meth:`score_from_arrays` which also routes through the same
        private helper.
        """
        n_pairs = int(len(prompts)) if prompts is not None else 0
        if n_pairs < 1:
            # No pairs to score — return graceful NaN with n_pairs=0.
            return CLIPScoreResult.nan_result(
                n_pairs=0, model_name=self._model_name
            )

        # Try to load. On ImportError / load failure return graceful NaN.
        try:
            self.ensure_loaded()
        except ImportError:
            return CLIPScoreResult.nan_result(
                n_pairs=n_pairs, model_name=self._model_name
            )
        except Exception:  # noqa: BLE001 — graceful, never raise.
            return CLIPScoreResult.nan_result(
                n_pairs=n_pairs, model_name=self._model_name
            )

        try:
            per_pair = self._score_pairs(images, prompts)
        except Exception:  # noqa: BLE001 — graceful, never raise.
            return CLIPScoreResult.nan_result(
                n_pairs=n_pairs, model_name=self._model_name
            )

        mean, std = _aggregate(per_pair, paper_scale=self._paper_scale)
        return CLIPScoreResult(
            mean=float(mean),
            std=float(std),
            n_pairs=int(n_pairs),
            model_name=str(self._model_name),
        )

    def score_from_arrays(
        self,
        image_array: Any,
        prompts: list[str],
    ) -> CLIPScoreResult:
        """Compute CLIPScore on a pre-built numpy ``(N, C, H, W)`` array.

        This is the second batch entry point — semantically identical
        to :meth:`score` but specialised for ``image_array`` inputs so
        callers can skip the ``list[Image]``-vs-array dispatch logic
        when they know they hold a contiguous array stack. It also
        routes through :meth:`_score_pairs`, keeping the cosine math in
        one place.
        """
        return self.score(image_array, prompts)

    # ------------------------------------------------------------------
    # Single-source-of-truth cosine math (private).
    def _score_pairs(
        self,
        images: Any,
        prompts: list[str],
    ) -> Any:
        """Run the CLIP forward pass and return per-pair cosine similarities.

        Returns a torch tensor of shape ``(N,)`` containing the raw
        cosine similarity (not yet aggregated or paper-scaled). The
        caller (:meth:`score` / :meth:`score_from_arrays`) decides on
        aggregation + paper-scale application.

        This is the SINGLE entry point for the cosine arithmetic.
        Any future numerical refinement (paper-scale choice,
        ``max(0, cos)`` policy, dtype promotion, etc.) lands here and
        only here.
        """
        if self._model is None or self._processor is None:
            # Should never happen — :meth:`score` guards this — but be
            # defensive so the helper is safe to call directly in tests.
            raise RuntimeError(
                "HFCosineClipScoreEvaluator._score_pairs called before "
                "ensure_loaded(); call ensure_loaded() first."
            )
        if not isinstance(prompts, list) or not prompts:
            raise ValueError(
                f"prompts must be a non-empty list of str, got {type(prompts).__name__}"
            )
        import torch

        inputs = self._processor(
            text=list(prompts),
            images=list(images) if not isinstance(images, list) else images,
            return_tensors="pt",
            padding=True,
            truncation=True,
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self._model(**inputs)
        img_emb = outputs.image_embeds  # (N, D)
        txt_emb = outputs.text_embeds  # (N, D)
        img_emb = img_emb / img_emb.norm(dim=-1, keepdim=True)
        txt_emb = txt_emb / txt_emb.norm(dim=-1, keepdim=True)
        # Pairwise dot product — diagonal of the Gram matrix.
        per_pair = (img_emb * txt_emb).sum(dim=-1)  # (N,)
        return per_pair.detach().cpu()

    def config_hash(self) -> str:
        """Stable digest binding the model + scale policy."""
        return _config_hash(
            self._model_name,
            {"paper_scale": self._paper_scale},
        )


# ---------------------------------------------------------------------------
# Module-level helpers (private — not part of the public surface)
# ---------------------------------------------------------------------------


def _aggregate(
    per_pair: Any,
    *,
    paper_scale: float | None,
) -> tuple[float, float]:
    """Aggregate a per-pair similarity tensor/array into ``(mean, std)``.

    When ``paper_scale`` is not ``None`` the per-pair similarities are
    clamped at ``0.0`` and scaled by ``paper_scale`` before aggregation
    — this matches the Hessel et al. 2021 paper convention.
    Otherwise the raw cosine is aggregated directly.
    """
    torch_mod: Any = None
    try:
        # Try torch first (the common path) — fall back to numpy.
        import torch as _torch_mod  # type: ignore[unused-ignore]
    except ImportError:
        pass
    else:
        torch_mod = _torch_mod
    if torch_mod is not None and isinstance(per_pair, torch_mod.Tensor):
        if paper_scale is not None:
            per_pair = torch_mod.clamp(per_pair, min=0.0) * float(paper_scale)
        arr = per_pair.to(dtype=torch_mod.float64).numpy()
    else:
        import numpy as np

        arr = np.asarray(per_pair, dtype=np.float64)
        if paper_scale is not None:
            arr = np.clip(arr, 0.0, None) * float(paper_scale)
    mean = float(arr.mean())
    # ``ddof=1`` mirrors the sample-std convention used in the
    # ``tools.run_image_eval.compute_clipscore`` reference. When the
    # batch has only one pair the denominator is zero, so we fall back
    # to ``ddof=0`` (population std) — the alternative would yield NaN
    # which would be a useless signal for a single-pair batch.
    n = int(arr.shape[0])
    std = float(arr.std(ddof=1)) if n >= 2 else float(arr.std(ddof=0))
    return mean, std


def _config_hash(model_name: str, extra: dict[str, Any] | None = None) -> str:
    """Stable SHA-256 digest over ``model_name`` + sorted ``extra``."""
    import hashlib
    import json

    payload: dict[str, Any] = {"model_name": str(model_name)}
    for key, val in sorted(dict(extra or {}).items()):
        payload[str(key)] = val
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

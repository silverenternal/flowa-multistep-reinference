"""Tests for ``adaptive_reflow.eval.clip_score`` (Phase B / Phase C).

Covers the canonical :class:`HFCosineClipScoreEvaluator` introduced as
the single-source-of-truth CLIPScore abstraction. These tests do *not*
load the real CLIP model — the actual forward pass is exercised by the
integration tests under ``tests/test_tools/`` (which gate on a
fixture-skip directive). The unit tests here pin:

* The protocol is importable and abstract.
* The graceful-NaN path is taken when :mod:`transformers` is missing
  (we simulate this with ``unittest.mock.patch.dict(sys.modules, ...)``
  so the test does not depend on the test environment's installed
  packages).
* The default model constant matches the documented value.
* The result dataclass validates its inputs and exposes
  :meth:`CLIPScoreResult.nan_result` for the graceful-NaN path.
"""

from __future__ import annotations

import sys
from typing import Any
from unittest import mock

import pytest

from adaptive_reflow.eval.clip_score import (
    CLIPSCORE_PAPER_SCALE,
    DEFAULT_CLIP_MODEL_NAME,
    CLIPScoreProtocol,
    CLIPScoreResult,
    HFCosineClipScoreEvaluator,
)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_protocol_imports() -> None:
    """The protocol, result dataclass, and evaluator are importable.

    Pins the public surface so downstream refactors cannot silently
    rename the canonical abstraction.
    """
    assert callable(CLIPScoreProtocol)
    assert callable(HFCosineClipScoreEvaluator)
    # The protocol declares ``score`` / ``config_hash`` / ``model_name``.
    assert hasattr(CLIPScoreProtocol, "score")
    assert hasattr(CLIPScoreProtocol, "config_hash")
    assert hasattr(CLIPScoreProtocol, "model_name")


def test_default_model_constant() -> None:
    """The default CLIP model name is the canonical smoke-friendly base.

    ``openai/clip-vit-base-patch32`` is the published CLIPScore default;
    pinning this constant protects downstream tooling that introspects
    the default via ``HFCosineClipScoreEvaluator().model_name``.
    """
    assert DEFAULT_CLIP_MODEL_NAME == "openai/clip-vit-base-patch32"
    # The evaluator's default uses the same constant.
    evaluator = HFCosineClipScoreEvaluator()
    assert evaluator.model_name == DEFAULT_CLIP_MODEL_NAME
    # ``config_hash`` is deterministic and model-bound.
    h1 = evaluator.config_hash()
    h2 = evaluator.config_hash()
    assert isinstance(h1, str) and h1
    assert h1 == h2, "config_hash is not deterministic"


def test_result_dataclass_shape() -> None:
    """``CLIPScoreResult`` validates its fields and exposes the NaN factory.

    The dataclass is the framework's contract surface — manifests
    reference it by name. Rejecting bad inputs (booleans, negative
    ``n_pairs``, empty ``model_name``) at construction time keeps
    downstream consumers safe.
    """
    # Happy path.
    r = CLIPScoreResult(
        mean=0.31,
        std=0.05,
        n_pairs=16,
        model_name=DEFAULT_CLIP_MODEL_NAME,
    )
    assert r.mean == pytest.approx(0.31)
    assert r.std == pytest.approx(0.05)
    assert r.n_pairs == 16
    assert r.model_name == DEFAULT_CLIP_MODEL_NAME
    assert r.is_finite is True

    # Reject boolean mean / std (Python's bool is a subclass of int).
    with pytest.raises(ValueError, match="mean must be a real number"):
        CLIPScoreResult(
            mean=True,  # type: ignore[arg-type]
            std=0.0,
            n_pairs=1,
            model_name="m",
        )

    # Reject negative n_pairs.
    with pytest.raises(ValueError, match="n_pairs must be a non-negative int"):
        CLIPScoreResult(
            mean=0.0,
            std=0.0,
            n_pairs=-1,
            model_name="m",
        )

    # Reject empty model_name.
    with pytest.raises(ValueError, match="model_name must be a non-empty str"):
        CLIPScoreResult(
            mean=0.0,
            std=0.0,
            n_pairs=1,
            model_name="",
        )

    # Graceful-NaN factory.
    nan = CLIPScoreResult.nan_result(n_pairs=7, model_name="openai/clip-vit-large-patch14")
    assert nan.mean != nan.mean  # NaN != NaN
    assert nan.std != nan.std
    assert nan.n_pairs == 7
    assert nan.model_name == "openai/clip-vit-large-patch14"
    assert nan.is_finite is False


def test_graceful_nan_without_transformers() -> None:
    """``score`` returns NaN with ``math.isnan(mean)`` when ``transformers`` is missing.

    We simulate the missing-dependency case by clearing
    :mod:`transformers` from :data:`sys.modules` and patching
    :func:`importlib.import_module` to re-raise ``ImportError`` on any
    attempt to load it. The evaluator must take the graceful-NaN path
    (NOT raise) and the result must carry the configured ``model_name``
    plus the actual ``n_pairs`` count so downstream manifests can
    correlate the missing-result record with the batch.
    """
    evaluator = HFCosineClipScoreEvaluator(
        model_name="openai/clip-vit-base-patch32"
    )

    real_import = __import__

    def _blocked_import(
        name: str,
        globals: Any | None = None,
        locals: Any | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "transformers" or name.startswith("transformers."):
            raise ImportError(
                f"transformers not available (blocked for test) — name={name!r}"
            )
        return real_import(name, globals, locals, fromlist, level)

    # Hide any previously-loaded ``transformers`` module so the blocked
    # import path is the only way to resolve it.
    hidden = {
        k: v
        for k, v in sys.modules.items()
        if k == "transformers" or k.startswith("transformers.")
    }
    with (
        mock.patch.dict(sys.modules, {k: None for k in hidden}, clear=False),
        mock.patch("builtins.__import__", side_effect=_blocked_import),
    ):
        # ``None`` values in ``sys.modules`` cause ImportError on the
        # next import. We further patch ``__builtins__.__import__`` to
        # guarantee the block — covers both ``import transformers`` and
        # ``from transformers import AutoModel`` paths.
        # Call ``score`` — should NOT raise, must return NaN.
        prompts = ["a photo of a cat", "a photo of a dog"]
        # ``images`` is a list of dummy arrays; the load attempt
        # fails before we get to the forward pass.
        dummy_images = [object(), object()]
        result = evaluator.score(dummy_images, prompts)

    assert isinstance(result, CLIPScoreResult)
    assert result.n_pairs == 2
    assert result.model_name == "openai/clip-vit-base-patch32"
    assert result.is_finite is False
    import math
    assert math.isnan(result.mean)
    assert math.isnan(result.std)


def test_constructor_validates_inputs() -> None:
    """The constructor rejects bad ``model_name`` / ``paper_scale``.

    Mirrors the dataclass-style validation in the FID abstraction so
    misuse is caught at construction time, not deep inside the forward
    pass.
    """
    # Empty model_name → ValueError.
    with pytest.raises(ValueError, match="model_name must be a non-empty str"):
        HFCosineClipScoreEvaluator(model_name="")

    # Non-numeric paper_scale → ValueError.
    with pytest.raises(ValueError, match="paper_scale must be a real number or None"):
        HFCosineClipScoreEvaluator(paper_scale="not-a-number")  # type: ignore[arg-type]

    # Negative paper_scale → ValueError.
    with pytest.raises(ValueError, match="paper_scale must be finite and > 0"):
        HFCosineClipScoreEvaluator(paper_scale=-1.0)

    # Zero paper_scale → ValueError (must be strictly positive).
    with pytest.raises(ValueError, match="paper_scale must be finite and > 0"):
        HFCosineClipScoreEvaluator(paper_scale=0.0)

    # ``None`` paper_scale is the raw-cosine path — should NOT raise.
    HFCosineClipScoreEvaluator(paper_scale=None)
    # And the canonical 100× paper scale is accepted.
    e = HFCosineClipScoreEvaluator(paper_scale=CLIPSCORE_PAPER_SCALE)
    assert e.paper_scale == pytest.approx(CLIPSCORE_PAPER_SCALE)


def test_empty_prompt_list_returns_zero_pair_nan() -> None:
    """An empty prompt list returns ``n_pairs=0`` graceful-NaN.

    Even with a fully-loaded model the empty-batch case is degenerate
    — there is nothing to score. The evaluator must short-circuit
    before any forward-pass machinery is invoked.
    """
    evaluator = HFCosineClipScoreEvaluator()
    result = evaluator.score(images=[], prompts=[])
    assert isinstance(result, CLIPScoreResult)
    assert result.n_pairs == 0
    assert result.is_finite is False


def test_protocol_is_abstract() -> None:
    """``CLIPScoreProtocol`` cannot be instantiated directly.

    The protocol declares the abstract surface; concrete evaluators
    inherit and override. We pin this contract by attempting an
    instantiation and asserting ``TypeError``.
    """
    with pytest.raises(TypeError):
        CLIPScoreProtocol()  # type: ignore[abstract]


def test_paper_scale_constant() -> None:
    """``CLIPSCORE_PAPER_SCALE`` is the canonical Hessel-et-al 2021 100x scale."""
    assert isinstance(CLIPSCORE_PAPER_SCALE, float)
    assert pytest.approx(100.0) == CLIPSCORE_PAPER_SCALE

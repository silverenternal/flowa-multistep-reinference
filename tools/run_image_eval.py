"""Unified image text-to-image (T2I) evaluation runner.

Loads a directory of generated images (``.png`` / ``.jpg`` / ``.jpeg`` /
``.webp``), optionally pairs them with prompts from a JSONL file
(one prompt per line, order-aligned with sorted file names), and emits
a JSON report with the following metrics:

* **FID** — Fréchet Inception Distance between sample InceptionV3
  ``pool3`` features and a user-supplied reference statistics ``.npz``
  (``mu`` + ``sigma`` arrays). The single canonical InceptionV3
  construction lives in :func:`load_inception_for_fid` (line below)
  and uses ``torchvision.models.inception_v3(
  weights=IMAGENET1K_V1, aux_logits=True, transform_input=False)``
  with ``model.fc = torch.nn.Identity()`` and ``model.AuxLogits =
  None`` so the forward returns the 2048-dim ``pool3`` vector
  directly. The Fréchet arithmetic is delegated to
  :class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator
  .compute_from_precomputed`. **Do not** construct InceptionV3 with
  ``weights=None, aux_logits=False`` anywhere in this codebase —
  that pattern was the root cause of the ~3e25 FID regression
  documented in commit ``2fb3dc0`` (random-init pool3 features have
  magnitudes ~1e10–1e12).
* **CLIPScore** — mean ± std of cosine similarity between sample image
  embeddings and prompt text embeddings using
  ``openai/clip-vit-base-patch32`` from :mod:`transformers`. The
  100× scaling from Hessel et al. 2021 is applied so the metric is
  faithful to the published CLIPScore paper convention (some
  re-implementations omit the scaling — this one keeps it).
* **GenEval** — *stub*. Object-composition evaluation requires a
  separate mmdet/Mask2Former harness; this runner emits ``null`` with
  a ``"external"`` marker pointing the operator at
  ``docs/r17-survey/image-eval-plan.md``.
* **HPSv2.1** — *stub by default, subprocess-wrapped when
  ``--hpsv2-binary`` is set*. HiDream-I1 paper Table 4 human-preference
  score (32.8 on Style + Anime). The wrapper invokes the upstream
  ``hpsv2==1.2.0`` PyPI package (``pip install hpsv2``) in a separate
  ``.venvs/hpsv2_venv`` and scores each ``(image, prompt)`` pair via
  ``hpsv2.score(...)``. The v2.1 checkpoint downloads on first run
  from the ``xswu/HPSv2`` HF repo (~3.3 GB).
* **DPG-Bench** — *stub*. Densely-typed prompts evaluation requires
  either mPLUG-owl (Tier 2 self-host) or a paid GPT-4V judge (Lumina-
  Image 2.0 paper); this runner emits ``null`` with a ``"external"``
  marker.
* **ImageReward** — *stub by default, subprocess-wrapped when
  ``--image-reward-binary`` is set*. Lumina-Image 2.0 paper Table 3
  preference-reward metric. The wrapper invokes the upstream
  ``image-reward==1.5`` PyPI package (``pip install image-reward``)
  in a separate ``.venvs/image_reward_venv`` so the heavy BLIP +
  AestheticScore + OpenAI-CLIP dep chain cannot contaminate the
  framework's ``.venv``. The wrapper downloads
  ``THUDM/ImageReward`` (~3.6 GB checkpoint) via ``RM.load(...)`` on
  first call, then ``model.score(prompt, img_list)`` over the staged
  samples. Returns ``{"value": <float>, "n_pairs": <int>, "mean":
  <float>, "std": <float>, "min": <float>, "max": <float>,
  "command": <cmdline>, ...}`` on success; ``{"value": null,
  "marker": "not_installed", ...}`` when the binary path is missing;
  ``{"value": null, "marker": "external"}`` (byte-stable legacy stub)
  when ``--image-reward-binary`` is not passed at all. See
  :func:`run_image_reward_metric` and
  ``docs/r17-survey/image-eval-tier2-progress.md`` §2.5.
* **T2I-CompBench** — *stub* (Lumina-Image 2.0 paper). Compositional
  text-to-image benchmark with three sub-scores (``color`` /
  ``shape`` / ``texture``) and a BLIP-VQA judge; the canonical
  harness is the upstream ``microsoft/T2I-CompBench`` repo (now
  mirrored at ``github.com/Karine-Huang/T2I-CompBench`` — the
  ``microsoft/`` org URL currently returns HTTP 404, see
  ``docs/r17-survey/image-eval-tier2-progress.md`` for the audit
  trail). It is **not** a PyPI package: there is no
  ``t2i-compbench-tool`` distribution on PyPI, so the operator must
  ``git clone`` the repo and run ``pip install -r requirements.txt``
  (which pulls ``openai/CLIP`` from git, ``detectron2`` pinned to a
  2022 commit, ``diffusers==0.15.0.dev0``, and a ``spaCy`` model
  wheel). The ``clip-benchmark`` PyPI package is from LAION-AI and
  is **not** what T2I-CompBench uses — the BLIP-VQA judge lives in
  the repo's ``BLIPvqa_eval/`` subdir and loads via the bundled
  requirements (transformers + openai-CLIP). The runner emits
  ``null`` with a ``"external"`` marker and a ``sub_scores`` block
  so downstream consumers can key off the three sub-metric fields
  independently. The corresponding install command is documented in
  the ``install_command`` field of the stub dict (a ``git clone`` +
  ``pip install -r requirements.txt`` sequence in a dedicated
  ``t2icompbench_venv``; separate venv because the upstream pins
  ``torch==2.0.1`` + ``detectron2`` which conflict with the
  framework's torch 2.7.0+cu128 build).

Each metric returns NaN with a clear stderr message when its
dependency is missing (e.g. ``transformers`` not installed), so a
partial run still produces a parseable JSON file.

GPU allocation (Phase B contract)
---------------------------------

* All CLIP / InceptionV3 preprocessing (InceptionV3 ~100 MB,
  CLIP-vit-base-patch32 ~600 MB) → **GPU 0** (RTX PRO 6000, 98 GB).
* HiDream-I1-Dev (24 GB) → **GPU 1** (RTX 5090, 32 GB).
* Do NOT load HiDream-I1-Full (17 B, 32 GB) on GPU 1 alongside the
  prep tests — would OOM.

The runner honors ``CUDA_VISIBLE_DEVICES`` and a ``--device`` flag so
the calling shell can pin the metric stage to GPU 0 without code
changes.

Usage::

    python tools/run_image_eval.py \\
        --samples-dir data/lumina_image_2_0/samples/ \\
        --reference-stats data/lumina_mjhq30k_inception_stats.npz \\
        --prompts-jsonl data/lumina_prompts.jsonl \\
        --output data/lumina_image_2_0/eval_report.json

Tier-2 GenEval subprocess (HiDream / Lumina §6.2 build-out)::

    python tools/run_image_eval.py \\
        --samples-dir data/lumina_image_2_0/samples/ \\
        --reference-stats data/lumina_mjhq30k_inception_stats.npz \\
        --prompts-jsonl data/lumina_prompts.jsonl \\
        --output data/lumina_image_2_0/eval_report.json \\
        --geneval-binary .venvs/geva_venv/bin/python \\
        --geneval-prompts  data/geneval_evaluation_metadata.jsonl \\
        --geneval-detector-path data/geva_models/mask2former_swin-s-p4-w7-224_lsj_8x2_50e_coco.pth \\
        --geneval-gpu-id 0

When ``--geneval-binary`` is omitted the runner emits the
byte-stable ``{"value": null, "marker": "external"}`` stub so existing
downstream consumers keep working. When it is set but the geva_venv
is not provisioned, the runner emits ``marker: "not_installed"``
with an explicit ``install_hint`` + a list of which paths are missing.

Tier-2 ImageReward subprocess (Lumina-Image 2.0 paper Table 3, HiDream
optional §6.2)::

    python tools/run_image_eval.py \\
        --samples-dir data/lumina_image_2_0/samples/ \\
        --prompts-jsonl data/lumina_prompts.jsonl \\
        --output data/lumina_image_2_0/eval_report.json \\
        --image-reward-binary .venvs/image_reward_venv/bin/python \\
        --image-reward-model   ImageReward-v1.0 \\
        --image-reward-gpu-id  0 \\
        --image-reward-timeout 600

When ``--image-reward-binary`` is omitted the runner emits the
byte-stable ``{"value": null, "marker": "external"}`` stub. When it
is set but ``image_reward_venv`` is not provisioned, the runner
emits ``marker: "not_installed"`` with an explicit ``install_hint``.
The wrapper scores ``prompt[i]`` vs ``image[i]`` for each
``(prompt, image)`` pair and reports ``mean ± std`` over the batch.

Tier-2 HPSv2.1 subprocess (HiDream-I1 paper Table 4)::

    python tools/run_image_eval.py \\
        --samples-dir data/hidream_i1/samples/ \\
        --prompts-jsonl data/hidream_i1/prompts.jsonl \\
        --output data/hidream_i1/eval_report.json \\
        --hpsv2-binary .venvs/hpsv2_venv/bin/python \\
        --hpsv2-prompts data/hidream_i1/prompts.jsonl \\
        --hpsv2-version v2.1 \\
        --hpsv2-gpu-id  0 \\
        --hpsv2-timeout 1800

When ``--hpsv2-binary`` is omitted the runner emits the byte-stable
``{"metric": "hpsv2", "value": null, "std": null, "n_pairs": 0,
"marker": "external"}`` stub. When it is set but ``hpsv2_venv`` is
not provisioned (or the upstream ``hpsv2`` package is not installed),
the runner emits ``marker: "not_installed"`` with an explicit
``install_hint``. The wrapper scores ``prompt[i]`` vs ``image[i]``
for each ``(prompt, image)`` pair and reports ``value`` (mean) and
``std`` (sample stddev) over the batch, with the v2.1 checkpoint
auto-downloaded from the ``xswu/HPSv2`` HF repo on first run.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
from pathlib import Path
from typing import Any

# Make the project importable when running as ``python tools/run_image_eval.py``.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Defense in depth (Audit #3, 2026-09). Pin the HF / transformers
# stack to its local cache before any ``transformers`` import so the
# safetensors auto-conversion daemon thread (``transformers`` 5.7.0)
# cannot issue HEAD requests to ``huggingface.co`` on every
# ``AutoModel.from_pretrained(...)`` call. Without this we observed
# a 5x-retry loop with ``1+2+4+8`` seconds of exponential backoff per
# load — graceful NaN under tight subprocess timeouts. Operators can
# still force network via ``HF_HUB_OFFLINE=0 python ...``.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np

from adaptive_reflow.eval.clip_score import (  # noqa: E402
    CLIPSCORE_PAPER_SCALE,
    HFCosineClipScoreEvaluator,
)
from adaptive_reflow.eval.fid import (  # noqa: E402
    InceptionV3FIDEvaluator,
)


# ---------------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------------

_SUPPORTED_EXTS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def discover_samples(samples_dir: Path) -> list[Path]:
    """Return a sorted list of supported image files in ``samples_dir``.

    The sort is lexicographic (``sorted(...)``) so the operator can
    align filenames with a JSONL prompt file via
    ``sample_0000.png -> line 0``, ``sample_0001.png -> line 1`` etc.
    Missing extensions silently skip (the function only returns files
    that actually exist on disk).
    """
    if not samples_dir.is_dir():
        raise FileNotFoundError(f"samples_dir_not_a_directory: {samples_dir}")
    out: list[Path] = []
    for child in sorted(samples_dir.iterdir()):
        if child.is_file() and child.suffix.lower() in _SUPPORTED_EXTS:
            out.append(child)
    if not out:
        raise FileNotFoundError(f"samples_dir_empty_or_no_supported_images: {samples_dir}")
    return out


def load_prompts(prompts_path: Path) -> list[str] | None:
    """Return the prompts JSONL as a list of strings.

    Each non-empty line (after ``str.splitlines()``) is one prompt.
    Returns ``None`` when the file is missing or empty so callers can
    fall back to a CLIP-score-without-text behaviour (CLIP score stays
    NaN).
    """
    if not prompts_path.exists():
        return None
    text = prompts_path.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines or None


def load_images_as_tensor(
    paths: list[Path],
    *,
    target_size: int | None = None,
) -> np.ndarray:
    """Load images with PIL and stack into ``(N, 3, H, W)`` float32 in ``[-1, 1]``.

    The output range matches the convention used by
    :mod:`tools.eval_rf_cifar.extract_inception_features` (the
    canonical FID preprocessing contract: ``[-1, 1]`` adapter output
    → ``[0, 1]`` → ImageNet-normalised). When ``target_size`` is set,
    every image is bilinearly resized to ``(target_size, target_size)``
    before stacking — this guarantees uniform tensor shapes so a
    single ``np.stack`` produces a well-formed ``(N, 3, S, S)``
    array. The InceptionV3 forward pass still bilinearly resizes to
    ``(299, 299)`` internally, so passing ``target_size=299`` is a
    no-op for FID; smaller values (e.g. ``32`` for unit tests) speed
    up the stack.

    RGB conversion: alpha-channel PNGs are flattened onto a white
    background; grayscale images are replicated across the 3 channels.
    """
    from PIL import Image

    arrays: list[np.ndarray] = []
    for path in paths:
        with Image.open(path) as img:
            # Convert to RGB (handles RGBA, L, CMYK, etc.).
            if img.mode != "RGB":
                if img.mode in ("RGBA", "LA"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.getchannel("A"))
                    img_rgb = bg
                else:
                    img_rgb = img.convert("RGB")
            else:
                img_rgb = img
            if target_size is not None and (
                img_rgb.size[0] != int(target_size) or img_rgb.size[1] != int(target_size)
            ):
                img_rgb = img_rgb.resize(
                    (int(target_size), int(target_size)), Image.Resampling.BILINEAR
                )
            arr_f: np.ndarray = np.asarray(img_rgb, dtype=np.float32) / 255.0  # (H, W, 3) in [0, 1]
            arr_f = (arr_f * 2.0) - 1.0  # → [-1, 1]
            arr_f = arr_f.transpose(2, 0, 1)  # (3, H, W)
            arrays.append(arr_f)
    if not arrays:
        return np.zeros((0, 3, 0, 0), dtype=np.float32)
    stacked: np.ndarray = np.stack(arrays, axis=0).astype(np.float32)
    return stacked


# ---------------------------------------------------------------------------
# FID — thin back-compat wrapper around the canonical
# :class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator`.
# ---------------------------------------------------------------------------


def compute_fid_from_features(
    sample_feats: np.ndarray,
    reference_mu: np.ndarray,
    reference_sigma: np.ndarray,
    *,
    eps: float = 1e-6,
) -> float:
    """Compute the Fréchet Inception Distance between sample features and reference statistics.

    Reference statistics come from a precomputed ``.npz`` containing
    ``mu`` and ``sigma`` arrays (the format emitted by
    :func:`compute_reference_stats` and by ``clean-fid``'s
    ``make_custom_stats`` helper). The Fréchet arithmetic is delegated
    to :class:`adaptive_reflow.eval.fid.InceptionV3FIDEvaluator
    .compute_from_precomputed`; this function is preserved as the
    legacy entry point for any caller (and tests) that imports it
    directly.

    Returns ``float('nan')`` if the input contains fewer than 2 rows
    (FID is undefined there).
    """
    if sample_feats.ndim != 2:
        raise ValueError("sample_features_must_be_2d")
    if reference_mu.ndim != 1 or reference_sigma.ndim != 2:
        raise ValueError("reference_mu_must_be_1d_sigma_2d")
    if reference_sigma.shape[0] != reference_sigma.shape[1]:
        raise ValueError("reference_sigma_must_be_square")
    feature_dim = int(sample_feats.shape[1])
    evaluator = InceptionV3FIDEvaluator(
        feature_dim=feature_dim,
        eigenclip_eps=float(eps),
    )
    return float(
        evaluator.compute_from_precomputed(
            sample_feats.astype(np.float64, copy=False),
            reference_mu.astype(np.float64, copy=False),
            reference_sigma.astype(np.float64, copy=False),
        ).value
    )


#: Canonical ImageNet normalization mean (RGB, [0, 1] domain). Single
#: source of truth shared by :func:`extract_inception_features_for_image_eval`
#: and the redirected call sites in
#: :mod:`tools.eval_rf_cifar` / :mod:`tools.compute_cifar_fid`. Pinned by
#: P0-1 so the three prior copies (which drifted slightly in the legacy
#: ``weights=None`` paths) collapse to one constant.
_INCEPTION_MEAN: tuple[float, float, float] = (0.485, 0.456, 0.406)

#: Canonical ImageNet normalization std (RGB, [0, 1] domain). Single
#: source of truth; see :data:`_INCEPTION_MEAN`.
_INCEPTION_STD: tuple[float, float, float] = (0.229, 0.224, 0.225)

#: Stable identifier for the canonical torchvision construction. Downstream
#: audit code and the FID contract use this label to assert extractor-family
#: provenance (P0-1 plan, Step 5).
CANONICAL_INCEPTION_FAMILY: str = "inceptionv3_torchvision_IMAGENET1K_V1"


def load_inception_for_fid(device: Any) -> Any:
    """Construct the *single canonical* InceptionV3 feature extractor and move it to ``device``.

    This is the **only** canonical InceptionV3 construction the repo
    advertises for FID (see :data:`CANONICAL_INCEPTION_FAMILY`). The
    construction is::

        tvm.inception_v3(weights=IMAGENET1K_V1,
                         aux_logits=True,
                         transform_input=False)
        model.fc = nn.Identity()
        model.AuxLogits = None
        model.eval()

    The pretrained IMAGENET1K_V1 checkpoint forces ``aux_logits=True``
    (the aux head is baked into the state_dict); we keep that flag on
    during construction, replace ``model.fc`` with ``Identity`` so the
    forward returns the ``(N, 2048)`` pool3 vector (the aux logits
    branch is not consumed by the FID math), and the network is run
    in ``eval()`` / ``no_grad()`` mode by
    :func:`extract_inception_features_for_image_eval`.

    Historical note (commit ``2fb3dc0`` regression guard). The
    earlier construct used ``weights=None`` + ``aux_logits=False``
    which produces a *randomly-initialized* network; pool3 features
    from random conv activations have magnitudes ~1e10-1e12 and a
    FID computed against a pretrained-feature reference statistics
    collapses to ~1e25 (still mathematically valid Fréchet arithmetic
    on a noise feature space, but useless as a paper-comparable
    metric). Audits P-03 (Lumina) and P-04 (HiDream) confirmed this
    was the root cause of the ~3e25 FID regression; the fix is to
    load the IMAGENET1K_V1 weights (~108.9 MB) cached under
    ``~/.cache/torch/hub/checkpoints/inception_v3_google-0cc3c7bd.pth``.

    The pytorch-fid canonical Inception (TF port, num_classes=1008,
    slightly different ``Mixed_5b``/``Mixed_5c``/``Mixed_5d``/...
    blocks) is *not* used here because the Lumina/HiDream reference
    statistics were both downloaded as published paper-comparable
    MJHQ-30K stats with torchvision's pretrained Inception; mixing
    the two would produce a feature-space mismatch. The pytorch-fid
    TF-port path is preserved as the *TF-aligned reference* path at
    :func:`tools.run_sota_cifar_experiment._compute_fid_tfport_inline`
    (renamed by P0-1) and is explicitly gated behind a ``pytorch_fid``
    importability check. Operators who want pytorch-fid's canonical
    Inception can override by passing their own callable into
    :func:`extract_inception_features_for_image_eval` via the test
    harness.
    """
    import torch
    import torch.nn as nn
    import torchvision.models as tvm

    weights = tvm.Inception_V3_Weights.IMAGENET1K_V1
    model = tvm.inception_v3(weights=weights, aux_logits=True, transform_input=False)
    model.fc = nn.Identity()
    # Strip the auxiliary classifier head — we don't consume its
    # output, but leaving it in keeps an unused submodule on the
    # device. The forward still returns the 2048-d pool3 vector via
    # the Identity-replaced ``model.fc``.
    if hasattr(model, "AuxLogits") and model.AuxLogits is not None:
        model.AuxLogits = None  # type: ignore[assignment]
    model.eval()
    return model.to(device)


def extract_inception_features_for_image_eval(
    images: np.ndarray,
    *,
    device: Any,
    batch_size: int = 16,
) -> np.ndarray:
    """Run the canonical InceptionV3 over ``(N, 3, H, W)`` images in ``[-1, 1]``.

    Returns ``(N, 2048)`` float32 features. Bilinearly resizes to
    ``(299, 299)`` (InceptionV3's expected input), maps ``[-1, 1]`` →
    ``[0, 1]`` → ImageNet-normalised, runs the network in ``eval()``
    / ``no_grad()`` mode. The model construction lives in
    :func:`load_inception_for_fid` (kept separate so the test suite
    can monkeypatch it).
    """
    import torch
    import torch.nn.functional as F

    if images.ndim != 4 or images.shape[1] != 3:
        raise ValueError("images_must_have_shape_n_3_h_w")
    if images.shape[0] == 0:
        return np.zeros((0, 2048), dtype=np.float32)

    model = load_inception_for_fid(device)
    out_feats: list[np.ndarray] = []
    # Use the promoted canonical ImageNet mean/std (P0-1 — single source
    # of truth, no more per-site drift between run_image_eval,
    # eval_rf_cifar, and compute_cifar_fid).
    mean = torch.tensor(_INCEPTION_MEAN, device=device).view(1, 3, 1, 1)
    std = torch.tensor(_INCEPTION_STD, device=device).view(1, 3, 1, 1)
    with torch.no_grad():
        for i in range(0, images.shape[0], int(batch_size)):
            batch: np.ndarray = images[i : i + int(batch_size)].astype(np.float32)
            x = torch.from_numpy(np.ascontiguousarray(batch))
            x = x.to(device)
            x = F.interpolate(x, size=(299, 299), mode="bilinear", align_corners=False)
            x = (x + 1.0) / 2.0
            x = (x - mean) / std
            feats_t = model(x)
            out_feats.append(np.asarray(feats_t.detach().cpu().numpy(), dtype=np.float32))
    concatenated: np.ndarray = np.concatenate(out_feats, axis=0)
    return concatenated


# ---------------------------------------------------------------------------
# CLIPScore — thin back-compat wrapper around the canonical
# :class:`adaptive_reflow.eval.clip_score.HFCosineClipScoreEvaluator`.
# ---------------------------------------------------------------------------


def compute_clipscore(
    images: np.ndarray,
    prompts: list[str],
    *,
    device: Any,
    model_id: str = "openai/clip-vit-base-patch32",
    batch_size: int = 16,
) -> dict[str, float]:
    """Compute CLIPScore (mean ± std) using the canonical HF cosine evaluator.

    The L2-normalised + paper-scale ``100 × max(0, cos)`` math is
    delegated to :class:`adaptive_reflow.eval.clip_score
    .HFCosineClipScoreEvaluator`. Returns a dict with ``mean`` and
    ``std`` keys. When :mod:`transformers` is missing or the model
    fails to load the underlying evaluator returns a graceful-NaN
    :class:`CLIPScoreResult` — the legacy contract was to raise
    :class:`ImportError`, so callers (see :func:`run_image_eval`)
    translate a graceful-NaN mean to ``None`` in the JSON output
    rather than a hard failure.
    """
    del batch_size  # The canonical evaluator handles batching internally.

    if images.shape[0] != len(prompts):
        raise ValueError(
            f"image_prompt_count_mismatch: {images.shape[0]} images vs {len(prompts)} prompts"
        )

    # The canonical evaluator expects ``list[Image]``-or-array input.
    # ``images`` arrives as an ``(N, 3, H, W)`` float32 tensor in
    # ``[-1, 1]``. Convert each row to a ``uint8`` ``(H, W, 3)`` numpy
    # array — the AutoProcessor accepts that format directly.
    pil_batch: list[np.ndarray] = []
    for arr in images:
        hwc = ((arr.transpose(1, 2, 0) + 1.0) / 2.0 * 255.0)
        hwc = np.clip(hwc, 0.0, 255.0).astype(np.uint8)
        pil_batch.append(hwc)

    evaluator = HFCosineClipScoreEvaluator(
        model_name=str(model_id),
        paper_scale=float(CLIPSCORE_PAPER_SCALE),
        device=device,
    )
    result = evaluator.score(pil_batch, list(prompts))
    # Preserve the legacy return shape (``{"mean": float, "std": float}``).
    # When the evaluator returns graceful NaN we surface that directly so
    # callers (which key off ``ImportError``) get a clear signal — the
    # numeric mean will be NaN in that case.
    return {"mean": float(result.mean), "std": float(result.std)}


# ---------------------------------------------------------------------------
# Metric orchestration (with graceful NaN fallback)
# ---------------------------------------------------------------------------


def discover_per_round_samples(
    samples_dir: Path,
    *,
    per_round_glob: str = "{arm}_round{r:02d}",
    arm: str = "framework",
) -> list[Path]:
    """Return a sorted list of per-round directories under ``samples_dir``.

    Phase 4 / Design #1 — globs ``{arm}_round00``, ``{arm}_round01``,
    ... under ``samples_dir``. Each discovered directory is one round;
    the list is sorted by the integer index encoded in the directory
    name (so ``round00`` precedes ``round01`` etc.) for stable
    ordering in the per-round metrics output.

    Returns an empty list when no per-round directories are present so
    the caller can fall back to legacy single-shot semantics.
    """
    if not samples_dir.is_dir():
        return []
    # Compute the literal prefix and trailing integer of the glob
    # (e.g. ``{arm}_round{r:02d}`` -> prefix="framework_round", suffix="").
    rendered = str(per_round_glob).format(arm=arm, r=0)
    # Split rendered at the trailing integer; everything before the
    # integer is the prefix and everything after (typically nothing)
    # is the suffix. This is more robust than splitting on "round"
    # because arm names may themselves contain underscores.
    prefix_end = len(rendered)
    while prefix_end > 0 and rendered[prefix_end - 1].isdigit():
        prefix_end -= 1
    prefix = rendered[:prefix_end]
    if not prefix:
        return []
    out: list[tuple[int, Path]] = []
    for child in samples_dir.iterdir():
        if not child.is_dir():
            continue
        if not child.name.startswith(prefix):
            continue
        try:
            idx = int(child.name[len(prefix):])
        except ValueError:
            continue
        out.append((idx, child))
    out.sort(key=lambda kv: kv[0])
    return [p for _, p in out]


def run_image_eval_per_round(
    *,
    samples_dir: Path,
    reference_stats: Path | None,
    prompts_jsonl: Path | None,
    output: Path,
    device_arg: str = "auto",
    fid_batch_size: int = 16,
    clip_batch_size: int = 16,
    clip_model_id: str = "openai/clip-vit-base-patch32",
    image_target_size: int = 299,
    per_round_glob: str = "{arm}_round{r:02d}",
    arm: str = "framework",
    geneval_binary: Path | None = None,
    geneval_repo: Path | None = None,
    geneval_detector_path: Path | None = None,
    geneval_timeout_seconds: int = 600,
    geneval_gpu_id: int | None = None,
    hpsv2_binary: Path | None = None,
    hpsv2_driver: Path | None = None,
    hpsv2_version: str = "v2.1",
    hpsv2_timeout_seconds: int = 1800,
    hpsv2_gpu_id: int | None = None,
) -> dict[str, Any]:
    """Top-level per-round orchestrator: load per-round images, run metrics.

    Returns ``img_eval_report.v1`` with an ADDITIVE
    ``metrics.per_round_fid`` and ``metrics.per_round_clip_score`` list
    keyed by ``round_index``. The legacy top-level ``metrics.fid`` and
    ``metrics.clip_score`` stay byte-stable — they are computed over
    the LAST round's images so downstream consumers that ignore the
    per-round surface keep working.

    Phase 4 / Design #1.
    """
    import torch as _torch  # local import keeps top-level lazy

    device = select_device(device_arg)
    per_round_dirs = discover_per_round_samples(
        samples_dir, per_round_glob=per_round_glob, arm=arm
    )
    if not per_round_dirs:
        # No per-round dirs found: fall back to legacy single-shot
        # behaviour (do not raise — Phase 3 byte-stability contract).
        print(
            f"[run_image_eval] no per-round dirs found under {samples_dir} "
            f"(glob={per_round_glob!r}, arm={arm!r}); falling back to "
            f"single-shot semantics.",
            file=sys.stderr,
        )
        return run_image_eval(
            samples_dir=samples_dir,
            reference_stats=reference_stats,
            prompts_jsonl=prompts_jsonl,
            output=output,
            device_arg=device_arg,
            fid_batch_size=fid_batch_size,
            clip_batch_size=clip_batch_size,
            clip_model_id=clip_model_id,
            image_target_size=image_target_size,
            geneval_binary=geneval_binary,
            geneval_repo=geneval_repo,
            geneval_detector_path=geneval_detector_path,
            geneval_timeout_seconds=geneval_timeout_seconds,
            geneval_gpu_id=geneval_gpu_id,
            hpsv2_binary=hpsv2_binary,
            hpsv2_driver=hpsv2_driver,
            hpsv2_version=hpsv2_version,
            hpsv2_timeout_seconds=hpsv2_timeout_seconds,
            hpsv2_gpu_id=hpsv2_gpu_id,
            image_reward_binary=image_reward_binary,
            image_reward_driver=image_reward_driver,
            image_reward_model=image_reward_model,
            image_reward_timeout_seconds=image_reward_timeout_seconds,
            image_reward_gpu_id=image_reward_gpu_id,
        )

    prompts = load_prompts(prompts_jsonl) if prompts_jsonl is not None else None

    per_round_fid: list[dict[str, Any]] = []
    per_round_clip: list[dict[str, Any]] = []
    final_images: np.ndarray | None = None
    t0 = time.perf_counter()
    for round_idx, round_dir in enumerate(per_round_dirs):
        try:
            round_samples = discover_samples(round_dir)
            round_images = load_images_as_tensor(
                round_samples, target_size=int(image_target_size)
            )
        except FileNotFoundError as exc:
            per_round_fid.append(
                {
                    "round_index": int(round_idx),
                    "round_dir": str(round_dir),
                    "metric": "fid",
                    "value": None,
                    "n_samples": 0,
                    "error": str(exc),
                }
            )
            per_round_clip.append(
                {
                    "round_index": int(round_idx),
                    "round_dir": str(round_dir),
                    "metric": "clip_score",
                    "mean": None,
                    "std": None,
                    "n_pairs": 0,
                    "error": str(exc),
                }
            )
            continue
        if reference_stats is not None:
            per_round_fid.append(
                {
                    "round_index": int(round_idx),
                    "round_dir": str(round_dir),
                    **run_fid_metric(
                        round_images,
                        reference_stats,
                        device=device,
                        batch_size=int(fid_batch_size),
                    ),
                }
            )
        else:
            per_round_fid.append(
                {
                    "round_index": int(round_idx),
                    "round_dir": str(round_dir),
                    "metric": "fid",
                    "value": None,
                    "n_samples": int(round_images.shape[0]),
                    "error": "reference_stats_not_provided",
                }
            )
        if prompts is not None:
            aligned: list[str] = list(prompts[: round_images.shape[0]])
            while len(aligned) < round_images.shape[0]:
                aligned.append("")
            clip_block = run_clipscore_metric(
                round_images,
                aligned,
                device=device,
                batch_size=int(clip_batch_size),
                model_id=str(clip_model_id),
            )
            clip_block.setdefault("round_index", int(round_idx))
            clip_block.setdefault("round_dir", str(round_dir))
            per_round_clip.append(clip_block)
        else:
            per_round_clip.append(
                {
                    "round_index": int(round_idx),
                    "round_dir": str(round_dir),
                    "metric": "clip_score",
                    "mean": None,
                    "std": None,
                    "n_pairs": int(round_images.shape[0]),
                    "error": "prompts_jsonl_not_provided",
                }
            )
        final_images = round_images

    # Legacy single-shot fields re-emitted over the FINAL round so
    # Phase 3 byte-stability holds for any downstream consumer that
    # ignores the per-round surface.
    if final_images is not None:
        if reference_stats is not None:
            legacy_fid = run_fid_metric(
                final_images,
                reference_stats,
                device=device,
                batch_size=int(fid_batch_size),
            )
        else:
            legacy_fid = {
                "metric": "fid",
                "value": None,
                "error": "reference_stats_not_provided",
            }
        if prompts is not None:
            aligned = list(prompts[: final_images.shape[0]])
            while len(aligned) < final_images.shape[0]:
                aligned.append("")
            legacy_clip = run_clipscore_metric(
                final_images,
                aligned,
                device=device,
                batch_size=int(clip_batch_size),
                model_id=str(clip_model_id),
            )
        else:
            legacy_clip = {
                "metric": "clip_score",
                "mean": None,
                "std": None,
                "error": "prompts_jsonl_not_provided",
            }
    else:
        legacy_fid = {
            "metric": "fid",
            "value": None,
            "error": "no_per_round_samples_loaded",
        }
        legacy_clip = {
            "metric": "clip_score",
            "mean": None,
            "std": None,
            "error": "no_per_round_samples_loaded",
        }

    report: dict[str, Any] = {
        "schema": "img_eval_report.v1",
        "samples_dir": str(samples_dir),
        "reference_stats": str(reference_stats) if reference_stats else None,
        "prompts_jsonl": str(prompts_jsonl) if prompts_jsonl else None,
        "n_samples": int(final_images.shape[0]) if final_images is not None else 0,
        "image_shape_hw": (
            [int(final_images.shape[2]), int(final_images.shape[3])]
            if final_images is not None and final_images.size
            else [0, 0]
        ),
        "device": str(device),
        "metrics": {
            "fid": legacy_fid,
            "clip_score": legacy_clip,
            "per_round_fid": per_round_fid,
            "per_round_clip_score": per_round_clip,
            "geneval": _resolve_geneval_metric(
                samples_dir=samples_dir,
                prompts_jsonl=prompts_jsonl,
                geneval_binary=geneval_binary,
                geneval_repo=geneval_repo,
                geneval_detector_path=geneval_detector_path,
                geneval_timeout_seconds=geneval_timeout_seconds,
                geneval_gpu_id=geneval_gpu_id,
            ),
            "hpsv2": _resolve_hpsv2_metric(
                samples_dir=samples_dir,
                prompts_jsonl=prompts_jsonl,
                hpsv2_binary=hpsv2_binary,
                hpsv2_driver=hpsv2_driver,
                hpsv2_version=hpsv2_version,
                hpsv2_timeout_seconds=hpsv2_timeout_seconds,
                hpsv2_gpu_id=hpsv2_gpu_id,
            ),
            "image_reward": _resolve_image_reward_metric(
                samples_dir=samples_dir,
                prompts_jsonl=prompts_jsonl,
                image_reward_binary=image_reward_binary,
                image_reward_driver=image_reward_driver,
                image_reward_model=image_reward_model,
                image_reward_timeout_seconds=image_reward_timeout_seconds,
                image_reward_gpu_id=image_reward_gpu_id,
            ),
            "dpg_bench": {
                "value": None,
                "marker": "external",
                "note": "DPG-Bench dense-prompt evaluation requires mPLUG-owl (Tier 2 self-host) or GPT-4V (paper); see docs/r17-survey/image-eval-plan.md",
            },
            "t2i_compbench": _t2i_compbench_external_stub(),
        },
        "wall_clock_seconds": float(time.perf_counter() - t0),
        "status": "ok",
    }
    if all(
        report["metrics"][k].get("value", report["metrics"][k].get("mean")) is None
        and report["metrics"][k].get("error")
        for k in ("fid", "clip_score")
    ):
        report["status"] = "all_metrics_failed"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True))
    return report


def _t2i_compbench_external_stub() -> dict[str, Any]:
    """Return the ``metrics.t2i_compbench`` external stub.

    Mirrors the shape of the ``geneval`` / ``dpg_bench`` stubs but
    adds a ``sub_scores`` block carrying ``color``, ``shape``,
    ``texture`` keys (the three sub-metrics the Lumina-Image 2.0
    paper Table 1 reports) so downstream consumers can key off the
    sub-metric fields independently even before the Tier-2 harness is
    installed.

    Install path (Tier-2 build-out, see
    ``docs/r17-survey/image-eval-tier2-progress.md``):

    The canonical upstream is the ``Karine-Huang/T2I-CompBench``
    repo (the ``microsoft/`` org URL returns HTTP 404 as of
    2026-09; the audit trail is in
    ``docs/r17-survey/image-eval-tier2-progress.md``). It is NOT a
    PyPI package — there is no ``t2i-compbench-tool`` distribution,
    so a ``git clone`` + ``pip install -r requirements.txt`` is the
    only viable install. The upstream ``requirements.txt`` pins
    ``torch==2.0.1`` + ``detectron2@5aeb252`` + ``diffusers==0.15.0
    .dev0`` + a ``spaCy`` model wheel, so a dedicated venv is
    mandatory (it MUST NOT be the framework's ``.venv``).

    .. code-block:: bash

        python -m venv .venvs/t2icompbench_venv
        source .venvs/t2icompbench_venv/bin/activate
        git clone https://github.com/Karine-Huang/T2I-CompBench.git \\
            .venvs/t2icompbench_venv/repo
        cd .venvs/t2icompbench_venv/repo
        pip install -r requirements.txt
        pip install diffusers==0.15.0.dev0
        # Optional: `accelerate config` then run
        # `BLIPvqa_eval/blip_vqa.py` against the generated samples.

    Once installed, the runner should add a ``run_t2i_compbench_metric``
    function and replace this stub with a subprocess call into the
    upstream ``BLIPvqa_eval/blip_vqa.py`` (for the BLIP-VQA judge
    step) and ``UniDet_eval/eval.py`` (for the UniDet expert scores);
    the sub-score JSON keys (``color`` / ``shape`` / ``texture``)
    are already reserved here so the contract is byte-stable across
    the stub → real transition.

    Returns the stub block as a ``dict`` so callers can drop it
    directly under ``metrics.t2i_compbench`` without further shape
    processing. The block is intentionally additive (does not alter
    any existing key) so Phase 3 byte-stability holds.

    Audit trail (P-22, 2026-09-03)
    ------------------------------
    The previous stub referenced ``pip install t2i-compbench-tool
    clip-benchmark``. PyPI returns 404 for both names:

      * ``t2i-compbench-tool`` — does not exist; the upstream is a
        script-only repo with no ``setup.py`` / ``pyproject.toml``.
      * ``clip-benchmark`` — IS a real PyPI package, but it is the
        LAION-AI CLIP-retrieval benchmark, not what T2I-CompBench
        uses for the BLIP-VQA judge (T2I-CompBench loads BLIP via
        the bundled ``BLIPvqa_eval/`` module + transformers + the
        openai/CLIP git dependency).

    The corrected install command is the ``git clone`` +
    ``pip install -r requirements.txt`` sequence above. The JSON
    contract (keys, value types, ``sub_scores`` shape) is unchanged
    so downstream consumers keep working.
    """
    return {
        "metric": "t2i_compbench",
        "value": None,
        "marker": "external",
        "note": (
            "T2I-CompBench compositional evaluation (Lumina-Image 2.0 "
            "paper). NOT a PyPI package — clone the upstream "
            "Karine-Huang/T2I-CompBench repo (microsoft/ org URL "
            "returns 404) and `pip install -r requirements.txt` in a "
            "dedicated venv. See "
            "docs/r17-survey/image-eval-tier2-progress.md for the "
            "subprocess contract and BLIP-VQA judge setup."
        ),
        "sub_scores": {
            "color": None,
            "shape": None,
            "texture": None,
        },
        "install_command": (
            "python -m venv .venvs/t2icompbench_venv && "
            "source .venvs/t2icompbench_venv/bin/activate && "
            "git clone https://github.com/Karine-Huang/T2I-CompBench.git "
            ".venvs/t2icompbench_venv/repo && "
            "cd .venvs/t2icompbench_venv/repo && "
            "pip install -r requirements.txt && "
            "pip install diffusers==0.15.0.dev0"
        ),
        "package": "T2I-CompBench (git clone of github.com/Karine-Huang/T2I-CompBench)",
        "upstream_repo": "https://github.com/Karine-Huang/T2I-CompBench",
        "microsoft_org_url_status": "404 (use Karine-Huang mirror)",
        "judge_model": "BLIPvqa_eval (openai/CLIP + transformers BLIP, not the LAION clip-benchmark PyPI pkg)",
        "subprocess_contract_version": 1,
    }


# ---------------------------------------------------------------------------
# Tier-2: GenEval subprocess wrapper (HiDream / Lumina paper §6.2 build-out)
# ---------------------------------------------------------------------------


#: Default path to the ``geva_venv`` Python interpreter used to drive the
#: GenEval detector. The runner resolves this via :func:`resolve_geva_binary`
#: so the operator can override with ``--geneval-binary``.
DEFAULT_GEVA_VENV_PYTHON: str = ".venvs/geva_venv/bin/python"

#: Default location of the cloned upstream GenEval repo (djghosh13/geneval).
#: The wrapper invokes ``evaluation/evaluate_images.py`` and
#: ``evaluation/summary_scores.py`` from this checkout.
DEFAULT_GEVA_REPO_DIR: str = ".venvs/geva_venv/repo"

#: Default location of the Mask2Former detector weights. Upstream
#: GenEval defaults to ``mask2former_swin-s-p4-w7-224_lsj_8x2_50e_coco``
#: and expects ``<detector_path>/<model>.pth`` next to the
#: ``mmdet`` config. The wrapper reads from the same layout.
DEFAULT_GEVA_DETECTOR_DIR: str = "data/geva_models"

#: Sub-scores the wrapper looks for in the ``summary_scores.py`` stdout.
#: Order matches the official GenEval paper Table 1 (single_obj, two_obj,
#: counting, colors, position, color_attr).
GENEVAL_SUB_SCORES: tuple[str, ...] = (
    "single_object",
    "two_object",
    "counting",
    "colors",
    "position",
    "color_attr",
)


def _geneval_not_installed_marker(
    *,
    python_bin: Path,
    geneval_repo: Path,
    detector_path: Path,
) -> dict[str, Any]:
    """Return the ``metrics.geneval`` ``not_installed`` fallback block.

    Emitted by :func:`run_geneval_metric` when one of the three required
    external artefacts is absent so the operator can distinguish
    "the Tier-2 harness is wired but not provisioned" from a generic
    failure. The marker carries the explicit install hint consumed by
    the operator checklist (``docs/r17-survey/image-eval-tier2-progress.md``).
    """
    missing: list[str] = []
    if not python_bin.exists():
        missing.append(f"--geneval-binary={python_bin}")
    if not geneval_repo.exists():
        missing.append(f"--geneval-repo={geneval_repo}")
    if not detector_path.exists():
        missing.append(f"--geneval-detector-path={detector_path}")
    return {
        "metric": "geneval",
        "value": None,
        "marker": "not_installed",
        "note": (
            "GenEval Tier-2 harness is wired (subprocess contract below) "
            "but one or more external artefacts are missing. See the "
            "checklist in docs/r17-survey/image-eval-tier2-progress.md."
        ),
        "missing": missing,
        "install_hint": (
            "Provision a separate geva_venv (it must NOT be the project's "
            ".venv because mmcv-full pins its own torch build). Run the "
            "operator checklist in docs/r17-survey/image-eval-tier2-progress.md "
            "§B to install mmcv-full 1.7.2 + mmdet 2.28.2 + clone "
            "github.com/djghosh13/geneval + download the Mask2Former "
            "Swin-S weights (~1 GB)."
        ),
        "sub_scores": {tag: None for tag in GENEVAL_SUB_SCORES},
    }


def _stage_geneval_inputs(
    *,
    samples_dir: Path,
    prompts_jsonl: Path | None,
    stage_dir: Path,
) -> int:
    """Materialize GenEval's numbered-subfolder layout from a flat samples dir.

    Upstream ``djghosh13/geneval`` ``evaluation/evaluate_images.py`` expects::

        <root>/<idx>/samples/<idx>.png
        <root>/<idx>/metadata.jsonl    (single JSON object, NOT line-delimited)

    where ``<idx>`` is the integer index of the prompt. The SOTA
    harness emits a flat samples dir + flat ``prompts.jsonl`` (one
    prompt per line, order-aligned with sorted filenames). This helper
    bridges the two: it walks ``samples_dir`` sorted, symlinks (or
    copies on failure) each PNG into ``stage_dir/<idx>/samples/<idx>.png``
    and writes a per-folder ``metadata.jsonl`` carrying the prompt
    string + a heuristically-inferred ``tag`` (one of the six
    GenEval sub-score buckets) so the upstream evaluator can group
    images by task.

    Returns the number of staged folders. Raises on missing inputs.
    """
    import re

    image_paths = discover_samples(samples_dir)
    prompts: list[str] | None = load_prompts(prompts_jsonl) if prompts_jsonl else None
    if prompts is not None and len(prompts) < len(image_paths):
        raise ValueError(
            f"geneval_stage_prompts_short: have {len(prompts)} prompts for "
            f"{len(image_paths)} images; pass --geneval-prompts with at "
            "least as many lines as --geneval-images has files."
        )

    stage_dir.mkdir(parents=True, exist_ok=True)
    for idx, img_path in enumerate(image_paths):
        folder = stage_dir / str(idx)
        samples = folder / "samples"
        samples.mkdir(parents=True, exist_ok=True)
        # Prefer symlink to avoid duplicating disk; fall back to copy.
        target = samples / img_path.name
        if target.exists() or target.is_symlink():
            target.unlink()
        try:
            os.symlink(img_path.resolve(), target)
        except OSError:
            shutil.copy2(img_path, target)
        prompt = prompts[idx] if prompts is not None else ""
        tag = _infer_geneval_tag(prompt, _re=re)
        metadata = {
            "prompt": prompt,
            "tag": tag,
            "include": [],
            "exclude": [],
            "kwargs": {"category": tag},
        }
        (folder / "metadata.jsonl").write_text(
            json.dumps(metadata) + "\n", encoding="utf-8"
        )
    return len(image_paths)


def _infer_geneval_tag(prompt: str, *, _re: Any = None) -> str:
    """Heuristically map a prompt string to one of GenEval's six task tags.

    This is a wrapper-side fallback for the case where the operator's
    prompts JSONL is a flat ``[prompt, ...]`` list (no upstream
    metadata). It is **not** meant to replace
    ``djghosh13/geneval/prompts/evaluation_metadata.jsonl``; when the
    operator supplies that file directly, each line already carries
    the canonical ``tag`` and this heuristic is bypassed (see
    :func:`_stage_geneval_inputs` for the layout).

    Returns one of ``GENEVAL_SUB_SCORES``. Order of checks matters:
    counting/two-object before colors (because "two" can appear in
    colors phrasing), color_attr only when two distinct color words
    are detected.
    """
    if _re is None:
        import re as _re  # local alias
    p = prompt.lower()
    # Counting / two-object: digits or number words.
    if _re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b", p):
        if " and " in p or _re.search(r"\b(two|2)\b", p):
            return "two_object"
        return "counting"
    # Color binding with two distinct colors -> color_attr.
    color_words = (
        "red", "blue", "green", "yellow", "black", "white", "purple",
        "orange", "pink", "brown", "gray", "grey",
    )
    found_colors = [w for w in color_words if _re.search(rf"\b{w}\b", p)]
    if len(found_colors) >= 2:
        return "color_attr"
    if found_colors:
        return "colors"
    # Position keywords.
    position_words = (
        "left", "right", "top", "bottom", "above", "below",
        "behind", "in front of", "next to", "beside",
    )
    for w in position_words:
        if _re.search(rf"\b{w}\b", p):
            return "position"
    # Default to single_object -- the largest GenEval bucket.
    return "single_object"


def _parse_geneval_summary(stdout_text: str) -> dict[str, Any]:
    """Parse the stdout of ``evaluation/summary_scores.py`` into a dict.

    Upstream prints lines like::

        single_object   = 92.50% (37 / 40)
        Overall score (avg. over tasks): 0.78300

    Returns ``{"value": float, "sub_scores": {...}, "raw_text": str}``.
    Falls back to ``{"value": None, ...}`` if parsing fails.
    """
    import re

    sub_scores: dict[str, float | None] = {tag: None for tag in GENEVAL_SUB_SCORES}
    overall_value: float | None = None
    for line in stdout_text.splitlines():
        line = line.strip()
        m = re.match(
            r"^([a-zA-Z_]+)\s*=\s*([0-9.]+)%\s*\(\s*(\d+)\s*/\s*(\d+)\s*\)\s*$",
            line,
        )
        if m:
            tag, pct = m.group(1), m.group(2)
            if tag in sub_scores:
                try:
                    sub_scores[tag] = float(pct) / 100.0
                except ValueError:
                    pass
            continue
        m2 = re.match(r"^Overall score \(avg\. over tasks\):\s*([0-9.]+)\s*$", line)
        if m2:
            try:
                overall_value = float(m2.group(1))
            except ValueError:
                pass
    return {"value": overall_value, "sub_scores": sub_scores, "raw_text": stdout_text}


def run_geneval_metric(
    *,
    samples_dir: Path,
    prompts_jsonl: Path | None,
    python_bin: Path,
    geneval_repo: Path,
    detector_path: Path,
    timeout_seconds: int = 600,
    gpu_id: int | None = None,
) -> dict[str, Any]:
    """Run GenEval as a subprocess into the ``geva_venv`` interpreter.

    Returns a JSON-shaped dict under ``metrics.geneval``:

    On success::

        {"metric": "geneval",
         "value": <float overall>,       # 0..1, paper convention
         "sub_scores": {"single_object": <float>, ..., "color_attr": <float>},
         "n_images": <int>,
         "elapsed_seconds": <float>,
         "command": "<cmdline>",
         "stdout_tail": <str>}            # last 2 KB for audit

    On any failure (binary missing, repo missing, detector missing,
    subprocess non-zero, timeout, parse failure) the wrapper emits a
    ``marker: "not_installed"`` or ``marker: "external_error"`` block --
    never raises -- so the surrounding ``run_image_eval`` continues to
    write the eval report.
    """
    if (
        not python_bin.exists()
        or not geneval_repo.exists()
        or not detector_path.exists()
    ):
        return _geneval_not_installed_marker(
            python_bin=python_bin,
            geneval_repo=geneval_repo,
            detector_path=detector_path,
        )
    evaluate_py = geneval_repo / "evaluation" / "evaluate_images.py"
    summary_py = geneval_repo / "evaluation" / "summary_scores.py"
    if not evaluate_py.exists() or not summary_py.exists():
        return {
            "metric": "geneval",
            "value": None,
            "marker": "not_installed",
            "note": (
                f"geneval_repo_present_but_missing_scripts: expected "
                f"{evaluate_py} and {summary_py}; clone the upstream repo "
                "(github.com/djghosh13/geneval) into --geneval-repo."
            ),
            "sub_scores": {tag: None for tag in GENEVAL_SUB_SCORES},
            "missing": [
                str(p) for p in (evaluate_py, summary_py) if not p.exists()
            ],
        }

    with tempfile.TemporaryDirectory(prefix="geva_stage_") as stage:
        stage_dir = Path(stage)
        results_dir = stage_dir / "results"
        results_dir.mkdir()
        results_jsonl = results_dir / "results.jsonl"
        staged_root = stage_dir / "samples"
        try:
            n_staged = _stage_geneval_inputs(
                samples_dir=samples_dir,
                prompts_jsonl=prompts_jsonl,
                stage_dir=staged_root,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "metric": "geneval",
                "value": None,
                "marker": "external_error",
                "stage": "input_staging",
                "error": f"{type(exc).__name__}: {exc}",
                "sub_scores": {tag: None for tag in GENEVAL_SUB_SCORES},
            }

        env = os.environ.copy()
        if gpu_id is not None:
            env["CUDA_VISIBLE_DEVICES"] = str(int(gpu_id))
        env.setdefault("HF_HUB_OFFLINE", "1")
        env.setdefault("TRANSFORMERS_OFFLINE", "1")

        # Step A -- detector forward + scoring per image.
        cmd_eval = [
            str(python_bin),
            str(evaluate_py),
            str(staged_root),
            "--outfile",
            str(results_jsonl),
            "--model-path",
            str(detector_path),
        ]
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd_eval,
                env=env,
                capture_output=True,
                text=True,
                timeout=int(timeout_seconds),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "metric": "geneval",
                "value": None,
                "marker": "external_error",
                "stage": "evaluate_images",
                "error": f"TimeoutExpired after {int(timeout_seconds)}s",
                "command": " ".join(cmd_eval),
                "sub_scores": {tag: None for tag in GENEVAL_SUB_SCORES},
                "stderr_tail": (exc.stderr or "")[-2048:]
                if getattr(exc, "stderr", None)
                else "",
            }
        elapsed_eval = time.perf_counter() - t0
        if proc.returncode != 0:
            return {
                "metric": "geneval",
                "value": None,
                "marker": "external_error",
                "stage": "evaluate_images",
                "error": f"non_zero_exit_{proc.returncode}",
                "command": " ".join(cmd_eval),
                "stderr_tail": (proc.stderr or "")[-2048:],
                "stdout_tail": (proc.stdout or "")[-2048:],
                "sub_scores": {tag: None for tag in GENEVAL_SUB_SCORES},
            }
        if not results_jsonl.exists():
            return {
                "metric": "geneval",
                "value": None,
                "marker": "external_error",
                "stage": "evaluate_images",
                "error": "results_jsonl_not_produced",
                "command": " ".join(cmd_eval),
                "sub_scores": {tag: None for tag in GENEVAL_SUB_SCORES},
            }

        # Step B -- summary: parse per-tag and overall score from stdout.
        cmd_summary = [
            str(python_bin),
            str(summary_py),
            str(results_jsonl),
        ]
        try:
            proc_summary = subprocess.run(
                cmd_summary,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "metric": "geneval",
                "value": None,
                "marker": "external_error",
                "stage": "summary_scores",
                "error": "TimeoutExpired after 60s",
                "command": " ".join(cmd_summary),
                "sub_scores": {tag: None for tag in GENEVAL_SUB_SCORES},
                "stderr_tail": (exc.stderr or "")[-2048:]
                if getattr(exc, "stderr", None)
                else "",
            }
        if proc_summary.returncode != 0:
            return {
                "metric": "geneval",
                "value": None,
                "marker": "external_error",
                "stage": "summary_scores",
                "error": f"non_zero_exit_{proc_summary.returncode}",
                "command": " ".join(cmd_summary),
                "stderr_tail": (proc_summary.stderr or "")[-2048:],
                "sub_scores": {tag: None for tag in GENEVAL_SUB_SCORES},
            }

        parsed = _parse_geneval_summary(proc_summary.stdout or "")
        out: dict[str, Any] = {
            "metric": "geneval",
            "value": parsed["value"],
            "sub_scores": parsed["sub_scores"],
            "n_images": int(n_staged),
            "elapsed_seconds": float(elapsed_eval),
            "command": " ".join(cmd_eval),
            "stdout_tail": (proc.stdout or "")[-2048:],
            "summary_stdout_tail": (proc_summary.stdout or "")[-2048:],
        }
        if out["value"] is None:
            out["marker"] = "external_error"
            out["error"] = "summary_parse_failed"
            out["stage"] = "summary_scores"
        return out


def _geneval_external_legacy_stub() -> dict[str, Any]:
    """Return the original Phase-B ``{"value": null, "marker": "external"}`` stub.

    Preserved verbatim (modulo ``sub_scores`` for byte-stable downstream
    consumers) for backwards compatibility: when the operator runs
    :func:`run_image_eval` without any ``--geneval-*`` flags the
    runner emits the same shape it has emitted since Phase B, so
    existing eval-report consumers do not need to be updated. The new
    ``sub_scores`` block is additive and carries ``None`` per
    :data:`GENEVAL_SUB_SCORES`.
    """
    return {
        "value": None,
        "marker": "external",
        "note": "GenEval object-composition evaluation requires an mmdet/Mask2Former harness; see docs/r17-survey/image-eval-plan.md",
        "sub_scores": {tag: None for tag in GENEVAL_SUB_SCORES},
    }


def _resolve_geneval_metric(
    *,
    samples_dir: Path,
    prompts_jsonl: Path | None,
    geneval_binary: Path | None,
    geneval_repo: Path | None,
    geneval_detector_path: Path | None,
    geneval_timeout_seconds: int,
    geneval_gpu_id: int | None,
) -> dict[str, Any]:
    """Decide between the Tier-2 subprocess wrapper and the legacy stub.

    When any of ``geneval_binary`` / ``geneval_repo`` / ``geneval_detector_path``
    is non-``None`` we run :func:`run_geneval_metric`; otherwise we
    emit :func:`_geneval_external_legacy_stub` so the JSON contract
    stays byte-stable for callers that have not opted into the Tier-2
    build-out. When ``geneval_binary`` is set but ``geneval_repo`` /
    ``geneval_detector_path`` are not, we resolve them to the documented
    defaults (:data:`DEFAULT_GEVA_REPO_DIR`, :data:`DEFAULT_GEVA_DETECTOR_DIR`)
    so the operator only has to pass the venv interpreter path.
    """
    if geneval_binary is None:
        return _geneval_external_legacy_stub()
    py_bin = Path(geneval_binary)
    repo = (
        Path(geneval_repo)
        if geneval_repo is not None
        else REPO_ROOT / DEFAULT_GEVA_REPO_DIR
    )
    det = (
        Path(geneval_detector_path)
        if geneval_detector_path is not None
        else REPO_ROOT / DEFAULT_GEVA_DETECTOR_DIR
    )
    return run_geneval_metric(
        samples_dir=samples_dir,
        prompts_jsonl=prompts_jsonl,
        python_bin=py_bin,
        geneval_repo=repo,
        detector_path=det,
        timeout_seconds=int(geneval_timeout_seconds),
        gpu_id=geneval_gpu_id,
    )


# ---------------------------------------------------------------------------
# Tier-2: ImageReward subprocess wrapper (HiDream §6.2 / Lumina Table 3)
# ---------------------------------------------------------------------------


#: Default path to the ``image_reward_venv`` Python interpreter used to drive the
#: ImageReward scoring subprocess. The wrapper resolves this via
#: :func:`resolve_image_reward_binary` so the operator can override with
#: ``--image-reward-binary``.
DEFAULT_IMAGE_REWARD_VENV_PYTHON: str = ".venvs/image_reward_venv/bin/python"

#: Default path to the ImageReward driver script shipped under the
#: ``image_reward_venv`` checkout. The wrapper invokes this script as a
#: subprocess; the driver in turn imports :mod:`ImageReward` from the
#: ``image_reward_venv`` site-packages and writes a JSON score block
#: to ``--output-json``.
DEFAULT_IMAGE_REWARD_DRIVER: str = ".venvs/image_reward_venv/scripts/image_reward_score.py"

#: Default ImageReward checkpoint identifier. ``v1.0`` is the only
#: published variant on :pypi:`image-reward` 1.5 (Jul 2023); the
#: wrapper exposes :data:`--image-reward-model` for forward-compat
#: with a hypothetical v1.1 release.
DEFAULT_IMAGE_REWARD_MODEL: str = "ImageReward-v1.0"


def _image_reward_not_installed_marker(
    *,
    python_bin: Path,
    driver_script: Path,
) -> dict[str, Any]:
    """Return the ``metrics.image_reward`` ``not_installed`` fallback block.

    Emitted by :func:`run_image_reward_metric` when one of the two
    required external artefacts is absent so the operator can
    distinguish "the Tier-2 harness is wired but not provisioned" from
    a generic failure. The marker carries the explicit install hint
    consumed by the operator checklist (see
    ``docs/r17-survey/image-eval-tier2-progress.md`` §2.5).
    """
    missing: list[str] = []
    if not python_bin.exists():
        missing.append(f"--image-reward-binary={python_bin}")
    if not driver_script.exists():
        missing.append(f"--image-reward-driver={driver_script}")
    return {
        "metric": "image_reward",
        "value": None,
        "std": None,
        "min": None,
        "max": None,
        "n_pairs": 0,
        "marker": "not_installed",
        "note": (
            "ImageReward Tier-2 harness is wired (subprocess contract below) "
            "but one or more external artefacts are missing. See "
            "docs/r17-survey/image-eval-tier2-progress.md §2.5."
        ),
        "missing": missing,
        "install_hint": (
            "Provision a separate image_reward_venv. Run: "
            "`uv venv --python 3.12 .venvs/image_reward_venv --seed && "
            "uv pip install --python .venvs/image_reward_venv/bin/python image-reward && "
            "uv pip install --python .venvs/image_reward_venv/bin/python "
            "'clip @ git+https://github.com/openai/CLIP.git' && "
            "uv pip install --python .venvs/image_reward_venv/bin/python "
            "'transformers>=4.27.4,<4.40' "
            "'diffusers>=0.16.0,<0.30' "
            "'accelerate>=0.16.0,<0.30'`. "
            "The driver script is shipped under "
            "`.venvs/image_reward_venv/scripts/image_reward_score.py` and "
            "does NOT need to be re-fetched. The image-reward model "
            "checkpoint (~3.6 GB from huggingface.co/THUDM/ImageReward) "
            "is fetched on the first RM.load() call."
        ),
    }


def _image_reward_external_legacy_stub() -> dict[str, Any]:
    """Return the byte-stable ImageReward ``{"value": null, "marker": "external"}`` stub.

    Emitted by :func:`run_image_eval` when the operator does not pass
    ``--image-reward-binary`` so the JSON contract is preserved across
    the "wrapper not opted in" transition. The shape mirrors the
    GenEval legacy stub and reserves the ``"metric": "image_reward"``
    key for downstream consumers that already key off
    ``report["metrics"]["image_reward"]``.
    """
    return {
        "metric": "image_reward",
        "value": None,
        "std": None,
        "min": None,
        "max": None,
        "n_pairs": 0,
        "marker": "external",
        "note": (
            "ImageReward human-preference evaluation (Lumina-Image 2.0 "
            "paper Table 3, HiDream optional §6.2) requires a separate "
            "image_reward_venv. Pass --image-reward-binary "
            ".venvs/image_reward_venv/bin/python to opt in. See "
            "docs/r17-survey/image-eval-tier2-progress.md §2.5."
        ),
    }


def run_image_reward_metric(
    *,
    samples_dir: Path,
    prompts_jsonl: Path | None,
    python_bin: Path,
    driver_script: Path,
    model_name: str = DEFAULT_IMAGE_REWARD_MODEL,
    timeout_seconds: int = 1800,
    gpu_id: int | None = None,
) -> dict[str, Any]:
    """Run the ImageReward driver as a subprocess and return its parsed JSON block.

    On success returns the dict the driver wrote to ``--output-json``
    (see :file:`.venvs/image_reward_venv/scripts/image_reward_score.py`
    for the exact shape: ``value`` / ``std`` / ``min`` / ``max`` /
    ``n_pairs`` / ``model`` / ``per_image`` + ``"metric":
    "image_reward"``).

    On any failure (binary missing, driver missing, prompts missing,
    subprocess non-zero, timeout, parse failure, downstream error
    block) the wrapper emits a ``marker: "not_installed"`` or
    ``marker: "external_error"`` block — never raises — so the
    surrounding :func:`run_image_eval` continues to write the eval
    report.

    The wrapper mirrors the :func:`run_hpsv2_metric` contract so the
    operator-facing CLI surface is consistent across Tier-2 metrics.
    The only differences: (a) ImageReward is a PyPI package import
    rather than a repo checkout + weights, so the "external artefacts"
    surface is just the venv interpreter + the bundled driver script
    (no separate ``--image-reward-repo`` /
    ``--image-reward-detector-path`` opt-ins); (b) the model variant
    flag is ``--image-reward-model`` (default ``ImageReward-v1.0``)
    instead of ``--hpsv2-version``.
    """
    if not python_bin.exists() or not driver_script.exists():
        return _image_reward_not_installed_marker(
            python_bin=python_bin, driver_script=driver_script
        )
    if prompts_jsonl is None or not prompts_jsonl.exists():
        return {
            "metric": "image_reward",
            "value": None,
            "std": None,
            "min": None,
            "max": None,
            "n_pairs": 0,
            "marker": "not_installed",
            "note": (
                "ImageReward requires a --image-reward-prompts (or "
                "--prompts-jsonl) JSONL aligned with the samples. Pass "
                "one of these flags."
            ),
            "missing": [f"--image-reward-prompts={prompts_jsonl}"]
            if prompts_jsonl is not None
            else ["--prompts-jsonl"],
        }

    with tempfile.TemporaryDirectory(prefix="image_reward_score_") as stage:
        stage_dir = Path(stage)
        output_json = stage_dir / "image_reward_result.json"
        env = os.environ.copy()
        if gpu_id is not None:
            env["CUDA_VISIBLE_DEVICES"] = str(int(gpu_id))
        # Allow first-run ImageReward checkpoint download (the upstream
        # ``RM.load("ImageReward-v1.0")`` pulls ~3.6 GB from
        # huggingface.co/THUDM/ImageReward). The operator can override
        # this with HF_HUB_OFFLINE=1 if the model has been pre-cached.
        env.setdefault("HF_HUB_OFFLINE", "0")

        cmd = [
            str(python_bin),
            str(driver_script),
            "--samples-dir",
            str(samples_dir),
            "--prompts-jsonl",
            str(prompts_jsonl),
            "--output-json",
            str(output_json),
            "--model",
            str(model_name),
        ]
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=int(timeout_seconds),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "metric": "image_reward",
                "value": None,
                "std": None,
                "min": None,
                "max": None,
                "n_pairs": 0,
                "marker": "external_error",
                "stage": "image_reward_score",
                "error": f"TimeoutExpired after {int(timeout_seconds)}s",
                "command": " ".join(cmd),
                "stderr_tail": (exc.stderr or "")[-2048:]
                if getattr(exc, "stderr", None)
                else "",
            }
        elapsed = time.perf_counter() - t0
        if not output_json.exists():
            return {
                "metric": "image_reward",
                "value": None,
                "std": None,
                "min": None,
                "max": None,
                "n_pairs": 0,
                "marker": "external_error",
                "stage": "image_reward_score",
                "error": "output_json_not_produced",
                "command": " ".join(cmd),
                "stderr_tail": (proc.stderr or "")[-2048:],
                "stdout_tail": (proc.stdout or "")[-2048:],
            }
        try:
            parsed = json.loads(output_json.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {
                "metric": "image_reward",
                "value": None,
                "std": None,
                "min": None,
                "max": None,
                "n_pairs": 0,
                "marker": "external_error",
                "stage": "image_reward_score",
                "error": f"output_json_parse_failed: {type(exc).__name__}: {exc}",
                "command": " ".join(cmd),
                "stderr_tail": (proc.stderr or "")[-2048:],
            }
        # Tag with subprocess metadata. The driver already emits
        # ``metric`` / ``value`` / ``std`` / ``min`` / ``max`` /
        # ``n_pairs`` / ``model`` so we only need to add the wrapper-
        # side fields.
        parsed.setdefault("metric", "image_reward")
        parsed["elapsed_seconds"] = float(elapsed)
        parsed["command"] = " ".join(cmd)
        parsed["stdout_tail"] = (proc.stdout or "")[-2048:]
        if proc.returncode != 0:
            parsed["marker"] = "external_error"
            parsed.setdefault(
                "error", f"non_zero_exit_{proc.returncode}"
            )
            parsed["stderr_tail"] = (proc.stderr or "")[-2048:]
        else:
            parsed.setdefault("marker", "ok")
        return parsed


def _resolve_image_reward_metric(
    *,
    samples_dir: Path,
    prompts_jsonl: Path | None,
    image_reward_binary: Path | None,
    image_reward_driver: Path | None,
    image_reward_model: str,
    image_reward_timeout_seconds: int,
    image_reward_gpu_id: int | None,
) -> dict[str, Any]:
    """Decide between the Tier-2 subprocess wrapper and the legacy stub.

    Mirrors :func:`_resolve_hpsv2_metric`. When ``image_reward_binary``
    is non-``None`` we run :func:`run_image_reward_metric`; otherwise we
    emit :func:`_image_reward_external_legacy_stub` so the JSON
    contract stays byte-stable for callers that have not opted into
    the Tier-2 build-out. When ``image_reward_binary`` is set but
    ``image_reward_driver`` is not, we resolve to the documented
    default (:data:`DEFAULT_IMAGE_REWARD_DRIVER`) so the operator
    only has to pass the venv interpreter path.
    """
    if image_reward_binary is None:
        return _image_reward_external_legacy_stub()
    py_bin = Path(image_reward_binary)
    drv = (
        Path(image_reward_driver)
        if image_reward_driver is not None
        else REPO_ROOT / DEFAULT_IMAGE_REWARD_DRIVER
    )
    return run_image_reward_metric(
        samples_dir=samples_dir,
        prompts_jsonl=prompts_jsonl,
        python_bin=py_bin,
        driver_script=drv,
        model_name=str(image_reward_model),
        timeout_seconds=int(image_reward_timeout_seconds),
        gpu_id=image_reward_gpu_id,
    )


# ---------------------------------------------------------------------------
# Tier-2: HPSv2.1 subprocess wrapper (HiDream paper §6.2 / Table 4)
# ---------------------------------------------------------------------------

#: Default path to the ``hpsv2_venv`` Python interpreter used to drive the
#: HPSv2 scoring subprocess. The wrapper resolves this via
#: :func:`resolve_hpsv2_binary` so the operator can override with
#: ``--hpsv2-binary``.
DEFAULT_HPSV2_VENV_PYTHON: str = ".venvs/hpsv2_venv/bin/python"

#: Default path to the HPSv2 driver script shipped under the
#: ``hpsv2_venv`` checkout. The wrapper invokes this script as a
#: subprocess; the driver in turn imports :mod:`hpsv2` from the
#: ``hpsv2_venv`` site-packages and writes a JSON score block to
#: ``--output-json``.
DEFAULT_HPSV2_DRIVER: str = ".venvs/hpsv2_venv/scripts/hpsv2_score.py"

#: Default HPSv2 model variant. ``v2.1`` is what the HiDream-I1 paper
#: reports (32.8 on the Style + Anime benchmark). ``v2.0`` is the
#: earlier checkpoint and is NOT directly comparable to ``v2.1``
#: (per the upstream README: "Scores cannot be directly compared
#: between v2.0 and v2.1."). The wrapper honours ``--hpsv2-version``.
DEFAULT_HPSV2_VERSION: str = "v2.1"


def _hpsv2_not_installed_marker(
    *,
    python_bin: Path,
    driver_script: Path,
) -> dict[str, Any]:
    """Return the ``metrics.hpsv2`` ``not_installed`` fallback block.

    Emitted by :func:`run_hpsv2_metric` when one of the two required
    external artefacts is absent so the operator can distinguish
    "the Tier-2 harness is wired but not provisioned" from a generic
    failure. The marker carries the explicit install hint consumed
    by the operator checklist (see
    ``docs/r17-survey/image-eval-tier2-progress.md`` §2.3).
    """
    missing: list[str] = []
    if not python_bin.exists():
        missing.append(f"--hpsv2-binary={python_bin}")
    if not driver_script.exists():
        missing.append(f"--hpsv2-driver={driver_script}")
    return {
        "metric": "hpsv2",
        "value": None,
        "std": None,
        "n_pairs": 0,
        "marker": "not_installed",
        "note": (
            "HPSv2.1 Tier-2 harness is wired (subprocess contract below) "
            "but one or more external artefacts are missing. See "
            "docs/r17-survey/image-eval-tier2-progress.md §2.3."
        ),
        "missing": missing,
        "install_hint": (
            "Provision a separate hpsv2_venv (it can be a sibling of "
            "geva_venv; HPSv2 has no CUDA-extension build step). Run: "
            "`uv venv --python 3.12 .venvs/hpsv2_venv --seed && "
            "uv pip install --python .venvs/hpsv2_venv/bin/python hpsv2`. "
            "The driver script is shipped under "
            "`.venvs/hpsv2_venv/scripts/hpsv2_score.py` and does NOT need "
            "to be re-fetched."
        ),
    }


def _hpsv2_external_legacy_stub() -> dict[str, Any]:
    """Return the byte-stable HPSv2 ``{"value": null, "marker": "external"}`` stub.

    Emitted by :func:`run_image_eval` when the operator does not pass
    ``--hpsv2-binary`` so the JSON contract is preserved across the
    "wrapper not opted in" transition. The shape mirrors the GenEval
    legacy stub (``"value": null`` + ``"marker": "external"``) and
    reserves the ``"metric": "hpsv2"`` key for downstream consumers
    that already key off ``report["metrics"]["hpsv2"]``.
    """
    return {
        "metric": "hpsv2",
        "value": None,
        "std": None,
        "n_pairs": 0,
        "marker": "external",
        "note": (
            "HPSv2.1 human-preference evaluation (HiDream-I1 paper Table 4) "
            "requires a separate hpsv2_venv. Pass --hpsv2-binary "
            ".venvs/hpsv2_venv/bin/python to opt in. See "
            "docs/r17-survey/image-eval-tier2-progress.md §2.3."
        ),
    }


def run_hpsv2_metric(
    *,
    samples_dir: Path,
    prompts_jsonl: Path | None,
    python_bin: Path,
    driver_script: Path,
    hps_version: str = "v2.1",
    timeout_seconds: int = 1800,
    gpu_id: int | None = None,
) -> dict[str, Any]:
    """Run the HPSv2 driver as a subprocess and return its parsed JSON block.

    On success returns the dict the driver wrote to ``--output-json``
    (see :file:`.venvs/hpsv2_venv/scripts/hpsv2_score.py` for the
    exact shape: ``value`` / ``std`` / ``n_pairs`` / ``hps_version`` /
    ``per_image`` + ``"metric": "hpsv2"``).

    On any failure (binary missing, driver missing, prompts missing,
    subprocess non-zero, timeout, parse failure, downstream error
    block) the wrapper emits a ``marker: "not_installed"`` or
    ``marker: "external_error"`` block — never raises — so the
    surrounding :func:`run_image_eval` continues to write the eval
    report.

    The wrapper mirrors the :func:`run_geneval_metric` contract so
    the operator-facing CLI surface is consistent across Tier-2
    metrics. The only differences: (a) HPSv2 is a Python package
    import rather than a repo checkout + weights, so the
    "external artefacts" surface is just the venv interpreter + the
    bundled driver script (no separate ``--hpsv2-repo`` /
    ``--hpsv2-detector-path`` opt-ins); (b) HPSv2 is single-GPU
    (the upstream ``hpsv2.score`` re-uses the same model + tokenizer
    across calls), so the GPU pin is honoured via the
    ``CUDA_VISIBLE_DEVICES`` env-var passthrough rather than a
    per-process torch device.
    """
    if not python_bin.exists() or not driver_script.exists():
        return _hpsv2_not_installed_marker(
            python_bin=python_bin, driver_script=driver_script
        )
    if prompts_jsonl is None or not prompts_jsonl.exists():
        return {
            "metric": "hpsv2",
            "value": None,
            "std": None,
            "n_pairs": 0,
            "marker": "not_installed",
            "note": (
                "HPSv2 requires a --hpsv2-prompts (or --prompts-jsonl) "
                "JSONL aligned with the samples. Pass one of these flags."
            ),
            "missing": [f"--hpsv2-prompts={prompts_jsonl}"]
            if prompts_jsonl is not None
            else ["--prompts-jsonl"],
        }

    with tempfile.TemporaryDirectory(prefix="hpsv2_score_") as stage:
        stage_dir = Path(stage)
        output_json = stage_dir / "hpsv2_result.json"
        env = os.environ.copy()
        if gpu_id is not None:
            env["CUDA_VISIBLE_DEVICES"] = str(int(gpu_id))
        env.setdefault("HF_HUB_OFFLINE", "0")  # allow first-run HPSv2 checkpoint download
        env.setdefault("HPS_ROOT", str(Path.home() / ".cache" / "hpsv2"))

        cmd = [
            str(python_bin),
            str(driver_script),
            "--samples-dir",
            str(samples_dir),
            "--prompts-jsonl",
            str(prompts_jsonl),
            "--output-json",
            str(output_json),
            "--hps-version",
            str(hps_version),
        ]
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=int(timeout_seconds),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "metric": "hpsv2",
                "value": None,
                "std": None,
                "n_pairs": 0,
                "marker": "external_error",
                "stage": "hpsv2_score",
                "error": f"TimeoutExpired after {int(timeout_seconds)}s",
                "command": " ".join(cmd),
                "stderr_tail": (exc.stderr or "")[-2048:]
                if getattr(exc, "stderr", None)
                else "",
            }
        elapsed = time.perf_counter() - t0
        if not output_json.exists():
            return {
                "metric": "hpsv2",
                "value": None,
                "std": None,
                "n_pairs": 0,
                "marker": "external_error",
                "stage": "hpsv2_score",
                "error": "output_json_not_produced",
                "command": " ".join(cmd),
                "stderr_tail": (proc.stderr or "")[-2048:],
                "stdout_tail": (proc.stdout or "")[-2048:],
            }
        try:
            parsed = json.loads(output_json.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {
                "metric": "hpsv2",
                "value": None,
                "std": None,
                "n_pairs": 0,
                "marker": "external_error",
                "stage": "hpsv2_score",
                "error": f"output_json_parse_failed: {type(exc).__name__}: {exc}",
                "command": " ".join(cmd),
                "stderr_tail": (proc.stderr or "")[-2048:],
            }
        # Tag with subprocess metadata. The driver already emits
        # ``metric`` / ``value`` / ``std`` / ``n_pairs`` / ``hps_version``
        # so we only need to add the wrapper-side fields.
        parsed.setdefault("metric", "hpsv2")
        parsed["elapsed_seconds"] = float(elapsed)
        parsed["command"] = " ".join(cmd)
        parsed["stdout_tail"] = (proc.stdout or "")[-2048:]
        if proc.returncode != 0:
            parsed["marker"] = "external_error"
            parsed.setdefault(
                "error", f"non_zero_exit_{proc.returncode}"
            )
            parsed["stderr_tail"] = (proc.stderr or "")[-2048:]
        else:
            parsed.setdefault("marker", "ok")
        return parsed


def _resolve_hpsv2_metric(
    *,
    samples_dir: Path,
    prompts_jsonl: Path | None,
    hpsv2_binary: Path | None,
    hpsv2_driver: Path | None,
    hpsv2_version: str,
    hpsv2_timeout_seconds: int,
    hpsv2_gpu_id: int | None,
) -> dict[str, Any]:
    """Decide between the Tier-2 subprocess wrapper and the legacy stub.

    Mirrors :func:`_resolve_geneval_metric`. When ``hpsv2_binary`` is
    non-``None`` we run :func:`run_hpsv2_metric`; otherwise we emit
    :func:`_hpsv2_external_legacy_stub` so the JSON contract stays
    byte-stable for callers that have not opted into the Tier-2
    build-out. When ``hpsv2_binary`` is set but ``hpsv2_driver`` is
    not, we resolve to the documented default
    (:data:`DEFAULT_HPSV2_DRIVER`) so the operator only has to pass
    the venv interpreter path.
    """
    if hpsv2_binary is None:
        return _hpsv2_external_legacy_stub()
    py_bin = Path(hpsv2_binary)
    drv = (
        Path(hpsv2_driver)
        if hpsv2_driver is not None
        else REPO_ROOT / DEFAULT_HPSV2_DRIVER
    )
    return run_hpsv2_metric(
        samples_dir=samples_dir,
        prompts_jsonl=prompts_jsonl,
        python_bin=py_bin,
        driver_script=drv,
        hps_version=str(hpsv2_version),
        timeout_seconds=int(hpsv2_timeout_seconds),
        gpu_id=hpsv2_gpu_id,
    )


def run_fid_metric(
    images: np.ndarray,
    reference_stats_path: Path,
    *,
    device: Any,
    batch_size: int,
) -> dict[str, Any]:
    """Run the FID metric, returning a JSON-shaped dict.

    On success: ``{"value": <float>, "n_samples": <int>, "n_features": 2048}``.
    On failure: ``{"value": null, "error": "<message>"}`` — never raises.
    """
    out: dict[str, Any] = {"metric": "fid", "value": None, "n_samples": None}
    try:
        if not reference_stats_path.exists():
            raise FileNotFoundError(f"reference_stats_not_found: {reference_stats_path}")
        ref = np.load(reference_stats_path)
        if "mu" not in ref.files or "sigma" not in ref.files:
            raise ValueError("reference_stats_missing_keys_mu_sigma")
        ref_mu = np.asarray(ref["mu"], dtype=np.float64)
        ref_sigma = np.asarray(ref["sigma"], dtype=np.float64)

        feats = extract_inception_features_for_image_eval(
            images, device=device, batch_size=int(batch_size)
        )
        fid_value = compute_fid_from_features(feats, ref_mu, ref_sigma)
        out["value"] = float(fid_value) if math.isfinite(fid_value) else None
        out["n_samples"] = int(feats.shape[0])
        out["n_features"] = int(feats.shape[1]) if feats.ndim == 2 else None
    except Exception as exc:  # noqa: BLE001 — metric-level fallback, never raise.
        out["error"] = f"{type(exc).__name__}: {exc}"
        print(f"[FID] failed: {exc!r}", file=sys.stderr)
    return out


def run_clipscore_metric(
    images: np.ndarray,
    prompts: list[str] | None,
    *,
    device: Any,
    batch_size: int,
    model_id: str,
) -> dict[str, Any]:
    """Run CLIPScore, returning a JSON-shaped dict.

    On success: ``{"mean": <float>, "std": <float>, "n_pairs": <int>,
    "model_id": <model_id>, "paper_scale": 100.0}``.
    On missing deps or empty prompt list: ``{"mean": null, "std": null}``.
    Never raises.
    """
    out: dict[str, Any] = {
        "metric": "clip_score",
        "mean": None,
        "std": None,
        "n_pairs": None,
        "model_id": str(model_id),
        "paper_scale": CLIPSCORE_PAPER_SCALE,
    }
    if not prompts:
        out["error"] = "no_prompts_provided"
        print("[CLIPScore] skipped: no prompts provided (--prompts-jsonl missing or empty).", file=sys.stderr)
        return out
    # Probe the dependency up-front so we can preserve the legacy
    # ``ImportError`` marker on the JSON output (downstream consumers
    # key off the literal substring ``"ImportError"`` to distinguish
    # the missing-dep fallback from a generic failure). Note: a bare
    # ``import transformers`` is NOT sufficient because some test
    # fixtures monkeypatch ``sys.modules["transformers"]`` with a
    # stub that raises on attribute access — so we explicitly probe
    # the symbols the canonical evaluator uses
    # (:class:`transformers.AutoModel` / :class:`AutoProcessor`).
    try:
        import transformers  # noqa: F401  — presence check
        from transformers import AutoModel, AutoProcessor  # noqa: F401
    except ImportError as exc:
        out["error"] = f"ImportError: {exc}"
        print(f"[CLIPScore] skipped: dependency missing ({exc!r}).", file=sys.stderr)
        return out
    try:
        scores = compute_clipscore(
            images,
            prompts,
            device=device,
            model_id=str(model_id),
            batch_size=int(batch_size),
        )
        out["mean"] = float(scores["mean"]) if math.isfinite(scores["mean"]) else None
        out["std"] = float(scores["std"]) if math.isfinite(scores["std"]) else None
        out["n_pairs"] = int(images.shape[0])
    except ImportError as exc:
        out["error"] = f"ImportError: {exc}"
        print(f"[CLIPScore] skipped: dependency missing ({exc!r}).", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 — metric-level fallback, never raise.
        out["error"] = f"{type(exc).__name__}: {exc}"
        print(f"[CLIPScore] failed: {exc!r}", file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# Top-level driver
# ---------------------------------------------------------------------------


def select_device(device_arg: str) -> Any:
    """Resolve the torch device, honouring ``--device`` and CUDA availability.

    When ``--device auto`` (default) we pick CUDA when available and
    fall back to CPU. Otherwise the operator's literal string is used
    (e.g. ``cuda:0``). The function never raises on missing CUDA; the
    caller (metric functions) will run on CPU and be slower but still
    produce valid results.
    """
    import torch

    if device_arg == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device_arg)


def run_image_eval(
    *,
    samples_dir: Path,
    reference_stats: Path | None,
    prompts_jsonl: Path | None,
    output: Path,
    device_arg: str = "auto",
    fid_batch_size: int = 16,
    clip_batch_size: int = 16,
    clip_model_id: str = "openai/clip-vit-base-patch32",
    image_target_size: int = 299,
    per_round: bool = False,
    per_round_glob: str = "{arm}_round{r:02d}",
    arm: str = "framework",
    geneval_binary: Path | None = None,
    geneval_repo: Path | None = None,
    geneval_detector_path: Path | None = None,
    geneval_timeout_seconds: int = 600,
    geneval_gpu_id: int | None = None,
    hpsv2_binary: Path | None = None,
    hpsv2_driver: Path | None = None,
    hpsv2_version: str = "v2.1",
    hpsv2_timeout_seconds: int = 1800,
    hpsv2_gpu_id: int | None = None,
    image_reward_binary: Path | None = None,
    image_reward_driver: Path | None = None,
    image_reward_model: str = DEFAULT_IMAGE_REWARD_MODEL,
    image_reward_timeout_seconds: int = 1800,
    image_reward_gpu_id: int | None = None,
) -> dict[str, Any]:
    """Top-level orchestrator: load images, run metrics, write JSON.

    ``image_target_size`` controls the bilinear resize applied at
    image-load time. Production runs use the canonical FID value
    (299); tests pass smaller values (e.g. 32) for speed.

    When ``per_round`` is ``True`` the runner delegates to
    :func:`run_image_eval_per_round` which globs ``{arm}_round{r:02d}``
    directories under ``samples_dir`` and emits per-round metrics
    under the additive ``metrics.per_round_fid`` /
    ``metrics.per_round_clip_score`` sub-trees. The legacy top-level
    ``metrics.fid`` / ``metrics.clip_score`` are re-emitted over the
    FINAL round so existing Phase 3 byte-stable consumers keep working
    when ``--per-round`` is omitted.
    """
    if per_round:
        return run_image_eval_per_round(
            samples_dir=samples_dir,
            reference_stats=reference_stats,
            prompts_jsonl=prompts_jsonl,
            output=output,
            device_arg=device_arg,
            fid_batch_size=fid_batch_size,
            clip_batch_size=clip_batch_size,
            clip_model_id=clip_model_id,
            image_target_size=image_target_size,
            per_round_glob=per_round_glob,
            arm=arm,
            geneval_binary=geneval_binary,
            geneval_repo=geneval_repo,
            geneval_detector_path=geneval_detector_path,
            geneval_timeout_seconds=geneval_timeout_seconds,
            geneval_gpu_id=geneval_gpu_id,
            hpsv2_binary=hpsv2_binary,
            hpsv2_driver=hpsv2_driver,
            hpsv2_version=hpsv2_version,
            hpsv2_timeout_seconds=hpsv2_timeout_seconds,
            hpsv2_gpu_id=hpsv2_gpu_id,
            image_reward_binary=image_reward_binary,
            image_reward_driver=image_reward_driver,
            image_reward_model=image_reward_model,
            image_reward_timeout_seconds=image_reward_timeout_seconds,
            image_reward_gpu_id=image_reward_gpu_id,
        )
    t0 = time.perf_counter()
    samples = discover_samples(samples_dir)
    prompts = load_prompts(prompts_jsonl) if prompts_jsonl is not None else None
    images = load_images_as_tensor(samples, target_size=int(image_target_size))

    report: dict[str, Any] = {
        "schema": "img_eval_report.v1",
        "samples_dir": str(samples_dir),
        "reference_stats": str(reference_stats) if reference_stats else None,
        "prompts_jsonl": str(prompts_jsonl) if prompts_jsonl else None,
        "n_samples": int(images.shape[0]),
        "image_shape_hw": [int(images.shape[2]), int(images.shape[3])] if images.size else [0, 0],
        "device": None,
        "metrics": {
            "fid": None,
            "clip_score": None,
            "geneval": _resolve_geneval_metric(
                samples_dir=samples_dir,
                prompts_jsonl=prompts_jsonl,
                geneval_binary=geneval_binary,
                geneval_repo=geneval_repo,
                geneval_detector_path=geneval_detector_path,
                geneval_timeout_seconds=geneval_timeout_seconds,
                geneval_gpu_id=geneval_gpu_id,
            ),
            "hpsv2": _resolve_hpsv2_metric(
                samples_dir=samples_dir,
                prompts_jsonl=prompts_jsonl,
                hpsv2_binary=hpsv2_binary,
                hpsv2_driver=hpsv2_driver,
                hpsv2_version=hpsv2_version,
                hpsv2_timeout_seconds=hpsv2_timeout_seconds,
                hpsv2_gpu_id=hpsv2_gpu_id,
            ),
            "image_reward": _resolve_image_reward_metric(
                samples_dir=samples_dir,
                prompts_jsonl=prompts_jsonl,
                image_reward_binary=image_reward_binary,
                image_reward_driver=image_reward_driver,
                image_reward_model=image_reward_model,
                image_reward_timeout_seconds=image_reward_timeout_seconds,
                image_reward_gpu_id=image_reward_gpu_id,
            ),
            "dpg_bench": {
                "value": None,
                "marker": "external",
                "note": "DPG-Bench dense-prompt evaluation requires mPLUG-owl (Tier 2 self-host) or GPT-4V (paper); see docs/r17-survey/image-eval-plan.md",
            },
            "t2i_compbench": _t2i_compbench_external_stub(),
        },
        "wall_clock_seconds": None,
        "status": "ok",
    }

    device = select_device(device_arg)
    report["device"] = str(device)

    # FID
    if reference_stats is not None:
        report["metrics"]["fid"] = run_fid_metric(
            images, reference_stats, device=device, batch_size=int(fid_batch_size)
        )
    else:
        report["metrics"]["fid"] = {
            "metric": "fid",
            "value": None,
            "error": "reference_stats_not_provided",
        }
        print("[FID] skipped: --reference-stats not provided.", file=sys.stderr)

    # CLIPScore
    if prompts is not None:
        # Align prompt count with image count: trim or pad with empty
        # strings (an empty string is a valid CLIP text input; the
        # score will simply be low for that image).
        aligned: list[str] = list(prompts[: images.shape[0]])
        while len(aligned) < images.shape[0]:
            aligned.append("")
        report["metrics"]["clip_score"] = run_clipscore_metric(
            images,
            aligned,
            device=device,
            batch_size=int(clip_batch_size),
            model_id=str(clip_model_id),
        )
    else:
        report["metrics"]["clip_score"] = {
            "metric": "clip_score",
            "mean": None,
            "std": None,
            "error": "prompts_jsonl_not_provided",
        }
        print("[CLIPScore] skipped: --prompts-jsonl not provided.", file=sys.stderr)

    # If every metric returned an error, surface a non-ok status.
    if all(
        report["metrics"][k].get("value", report["metrics"][k].get("mean")) is None
        and report["metrics"][k].get("error")
        for k in ("fid", "clip_score")
    ):
        report["status"] = "all_metrics_failed"

    report["wall_clock_seconds"] = float(time.perf_counter() - t0)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True))
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tools.run_image_eval",
        description=(
            "Unified image T2I evaluation runner: FID (InceptionV3 pool3) "
            "+ CLIPScore (openai/clip-vit-base-patch32). GenEval, "
            "DPG-Bench, and T2I-CompBench are emitted as external stubs "
            "(sub-scores for T2I-CompBench color/shape/texture are "
            "reserved even today). Each metric returns NaN/null gracefully "
            "when its dependency is missing."
        ),
    )
    p.add_argument("--samples-dir", type=str, required=True,
                   help="Directory of generated .png/.jpg/.jpeg/.webp/.bmp images.")
    p.add_argument("--reference-stats", type=str, default=None,
                   help="Path to .npz with reference mu/sigma arrays for FID.")
    p.add_argument("--prompts-jsonl", type=str, default=None,
                   help="Path to JSONL of prompts (one per line, order-aligned with sorted filenames).")
    p.add_argument("--output", type=str, required=True,
                   help="Path to write the JSON eval report.")
    p.add_argument("--device", type=str, default="auto",
                   help="Torch device: 'auto' (cuda if available else cpu), or e.g. 'cuda:0', 'cpu'.")
    p.add_argument("--fid-batch-size", type=int, default=16,
                   help="Batch size for InceptionV3 forward pass.")
    p.add_argument("--clip-batch-size", type=int, default=16,
                   help="Batch size for CLIPScore forward pass.")
    p.add_argument("--clip-model-id", type=str, default="openai/clip-vit-base-patch32",
                   help="HF model id for CLIPScore (default: openai/clip-vit-base-patch32).")
    p.add_argument("--image-target-size", type=int, default=299,
                   help="Bilinear resize applied to every image at load time (default: 299).")
    p.add_argument("--per-round", action="store_true",
                   help=(
                       "Phase 4 / Design #1: glob ``{arm}_round{r:02d}/`` "
                       "sub-directories under ``--samples-dir`` and emit "
                       "per-round FID + CLIPScore under "
                       "``metrics.per_round_fid`` / ``metrics.per_round_clip_score``. "
                       "Legacy top-level ``metrics.fid`` / ``metrics.clip_score`` "
                       "are re-emitted over the FINAL round (Phase 3 "
                       "byte-stability preserved when --per-round is omitted)."
                   ))
    p.add_argument("--per-round-glob", type=str, default="{arm}_round{r:02d}",
                   help="Format string for per-round directory naming (default: ``{arm}_round{r:02d}``).")
    p.add_argument("--arm", type=str, default="framework",
                   help="Arm prefix consumed by the per-round glob (default: ``framework``).")
    p.add_argument("--synthetic-image", action="store_true",
                   help=(
                       "P-15 phase 3 ADDITIVE: when set, automatically load the "
                       "canonical synthetic-image InceptionV3 reference statistics "
                       "from ``data/synthetic_image_v1/inception_reference_stats.npz`` "
                       "(relative to the repo root), falling back to the documented "
                       "external canonical path ``/home/hugo/data/synthetic_image_v1/"
                       "inception_reference_stats.npz`` when the in-repo file is "
                       "absent (the repo ``.gitignore`` excludes ``data/``). "
                       "When set, --reference-stats is overridden (a stderr note is "
                       "emitted). When --synthetic-image is NOT set, behaviour is "
                       "byte-stable vs the pre-existing --reference-stats path."
                   ))
    # ----- Tier-2 (GenEval) subprocess wrapper flags (HiDream / Lumina §6.2) -----
    p.add_argument("--geneval-binary", type=str, default=None,
                   help=(
                       "Path to the geva_venv Python interpreter (e.g. "
                       "``.venvs/geva_venv/bin/python``). When set, the runner "
                       "invokes the upstream GenEval detector as a subprocess "
                       "instead of emitting the ``external`` stub. Leave unset "
                       "to keep byte-stable Phase-B behaviour. See "
                       "docs/r17-survey/image-eval-tier2-progress.md §B for the "
                       "install contract."
                   ))
    p.add_argument("--geneval-prompts", type=str, default=None,
                   help=(
                       "Path to a JSONL prompts file aligned with the samples. "
                       "When omitted, falls back to ``--prompts-jsonl``. Either "
                       "the upstream GenEval ``evaluation_metadata.jsonl`` (with "
                       "``tag`` / ``include`` / ``exclude`` keys) or a flat "
                       "[prompt, ...] list is accepted; the wrapper heuristically "
                       "tags flat lists so the upstream evaluator can group by "
                       "task."
                   ))
    p.add_argument("--geneval-repo", type=str, default=None,
                   help=(
                       "Path to the cloned upstream ``djghosh13/geneval`` repo. "
                       "Default: ``.venvs/geva_venv/repo`` (resolved relative "
                       "to the repo root)."
                   ))
    p.add_argument("--geneval-detector-path", type=str, default=None,
                   help=(
                       "Directory holding the Mask2Former weights + config. "
                       "Upstream expects ``<dir>/<model>.pth`` next to the "
                       "``mmdet`` config. Default: ``data/geva_models``."
                   ))
    p.add_argument("--geneval-timeout", type=int, default=600,
                   help="Subprocess timeout for ``evaluate_images.py`` (default: 600 s).")
    p.add_argument("--geneval-gpu-id", type=int, default=None,
                   help=(
                       "Pin the GenEval subprocess to a specific CUDA device via "
                       "``CUDA_VISIBLE_DEVICES`` (default: inherit the parent's "
                       "CUDA_VISIBLE_DEVICES)."
                   ))
    # ----- Tier-2 (HPSv2.1) subprocess wrapper flags (HiDream paper Table 4) -----
    p.add_argument("--hpsv2-binary", type=str, default=None,
                   help=(
                       "Path to the hpsv2_venv Python interpreter (e.g. "
                       "``.venvs/hpsv2_venv/bin/python``). When set, the runner "
                       "invokes the HPSv2 driver as a subprocess instead of "
                       "emitting the ``external`` stub. Leave unset to keep "
                       "byte-stable Phase-B behaviour. See "
                       "docs/r17-survey/image-eval-tier2-progress.md §2.3 "
                       "for the install contract."
                   ))
    p.add_argument("--hpsv2-driver", type=str, default=None,
                   help=(
                       "Path to the HPSv2 driver script (default: "
                       "``.venvs/hpsv2_venv/scripts/hpsv2_score.py``). The driver "
                       "imports :mod:`hpsv2` and writes a JSON result block to "
                       "its ``--output-json`` path."
                   ))
    p.add_argument("--hpsv2-prompts", type=str, default=None,
                   help=(
                       "Path to a JSONL prompts file aligned with the samples "
                       "(one prompt per non-empty line). When omitted, falls "
                       "back to ``--prompts-jsonl``. The driver pads "
                       "mismatched tails with empty strings so a short prompt "
                       "file does not abort the run."
                   ))
    p.add_argument("--hpsv2-version", type=str, default="v2.1",
                   choices=("v2.0", "v2.1"),
                   help=(
                       "HPSv2 model variant. ``v2.1`` is the HiDream-I1 paper "
                       "default (32.8 on Style + Anime). ``v2.0`` is the "
                       "earlier checkpoint and is NOT directly comparable to "
                       "``v2.1`` (per upstream README: 'Scores cannot be "
                       "directly compared between v2.0 and v2.1.')."
                   ))
    p.add_argument("--hpsv2-timeout", type=int, default=1800,
                   help="Subprocess timeout for the HPSv2 driver (default: 1800 s = 30 min).")
    p.add_argument("--hpsv2-gpu-id", type=int, default=None,
                   help=(
                       "Pin the HPSv2 subprocess to a specific CUDA device via "
                       "``CUDA_VISIBLE_DEVICES`` (default: inherit the parent's "
                       "CUDA_VISIBLE_DEVICES)."
                   ))
    # ----- Tier-2 (ImageReward) subprocess wrapper flags (HiDream §6.2 / Lumina Table 3) -----
    p.add_argument("--image-reward-binary", type=str, default=None,
                   help=(
                       "Path to the image_reward_venv Python interpreter (e.g. "
                       "``.venvs/image_reward_venv/bin/python``). When set, the "
                       "runner invokes the ImageReward driver as a subprocess "
                       "instead of emitting the ``external`` stub. Leave unset "
                       "to keep byte-stable Phase-B behaviour. See "
                       "docs/r17-survey/image-eval-tier2-progress.md §2.5 for "
                       "the install contract (image-reward==1.5 + pinned "
                       "transformers<4.40 + pinned diffusers<0.30)."
                   ))
    p.add_argument("--image-reward-driver", type=str, default=None,
                   help=(
                       "Path to the ImageReward driver script (default: "
                       "``.venvs/image_reward_venv/scripts/image_reward_score.py``). "
                       "The driver imports :mod:`ImageReward` and writes a JSON "
                       "result block to its ``--output-json`` path."
                   ))
    p.add_argument("--image-reward-prompts", type=str, default=None,
                   help=(
                       "Path to a JSONL prompts file aligned with the samples "
                       "(one prompt per non-empty line). When omitted, falls "
                       "back to ``--prompts-jsonl``. The driver pads mismatched "
                       "tails with empty strings so a short prompt file does "
                       "not abort the run."
                   ))
    p.add_argument("--image-reward-model", type=str, default=DEFAULT_IMAGE_REWARD_MODEL,
                   help=(
                       "ImageReward model variant (default: "
                       f"``{DEFAULT_IMAGE_REWARD_MODEL}``; only v1.0 is "
                       "published on PyPI as of 2026-09)."
                   ))
    p.add_argument("--image-reward-timeout", type=int, default=1800,
                   help="Subprocess timeout for the ImageReward driver (default: 1800 s = 30 min).")
    p.add_argument("--image-reward-gpu-id", type=int, default=None,
                   help=(
                       "Pin the ImageReward subprocess to a specific CUDA device "
                       "via ``CUDA_VISIBLE_DEVICES`` (default: inherit the "
                       "parent's CUDA_VISIBLE_DEVICES)."
                   ))
    p.add_argument("--emit-eval-report", action="store_true",
                   help=(
                       "Append the additive ``eval_report.v1.0.0`` block "
                       "to the JSON output. Default off so the HiDream "
                       "and lumina subprocess consumers see the same "
                       "flat-dict shape as before."
                   ))
    return p


# ---------------------------------------------------------------------------
# Canonical synthetic-image reference stats path resolution (P-15 phase 3)
# ---------------------------------------------------------------------------


#: Canonical in-repo path (relative to REPO_ROOT). The repo ``.gitignore``
#: excludes ``data/`` so the in-repo path may be absent on a fresh clone.
SYNTHETIC_IMAGE_REF_STATS_INREPO: str = "data/synthetic_image_v1/inception_reference_stats.npz"
#: Documented external canonical path produced by
#: :mod:`tools.build_synthetic_image_dataset` on the agent's host.
SYNTHETIC_IMAGE_REF_STATS_EXTERNAL: str = "/home/hugo/data/synthetic_image_v1/inception_reference_stats.npz"


def resolve_synthetic_image_reference_stats() -> Path:
    """Return the canonical synthetic-image reference stats path.

    Search order (first match wins):

    1. ``<REPO_ROOT>/data/synthetic_image_v1/inception_reference_stats.npz``
       (in-repo path; documented contract from P-15).
    2. ``/home/hugo/data/synthetic_image_v1/inception_reference_stats.npz``
       (the documented external canonical path produced by
       :mod:`tools.build_synthetic_image_dataset` on the agent's host —
       used when the repo ``.gitignore`` excludes ``data/``).

    Raises
    ------
    FileNotFoundError
        When neither path is present. The CLI then propagates the error
        so the operator sees a clear actionable message rather than
        silently using a missing reference.
    """
    in_repo = REPO_ROOT / SYNTHETIC_IMAGE_REF_STATS_INREPO
    if in_repo.is_file():
        return in_repo
    external = Path(SYNTHETIC_IMAGE_REF_STATS_EXTERNAL)
    if external.is_file():
        return external
    raise FileNotFoundError(
        "synthetic_image_reference_stats_not_found: tried "
        f"{in_repo} (in-repo) and {external} (external canonical); "
        "run tools/build_synthetic_image_dataset.py --n-samples 5000 "
        "to materialise the canonical 5K reference."
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    # P-15 phase 3 ADDITIVE: when --synthetic-image is set, override
    # --reference-stats with the canonical synthetic-image reference
    # statistics. The legacy --reference-stats path is byte-stable when
    # --synthetic-image is omitted. We log the resolved path to stderr so
    # operators can audit which reference was used.
    resolved_ref_stats: Path | None = None
    if args.synthetic_image:
        try:
            resolved_ref_stats = resolve_synthetic_image_reference_stats()
        except FileNotFoundError as exc:
            print(f"[ERROR] --synthetic-image requested but no canonical "
                  f"reference stats found: {exc}", file=sys.stderr)
            return 1
        print(
            f"[run_image_eval] --synthetic-image: using canonical reference "
            f"stats at {resolved_ref_stats}",
            file=sys.stderr,
        )
    elif args.reference_stats:
        resolved_ref_stats = Path(args.reference_stats)
    try:
        report = run_image_eval(
            samples_dir=Path(args.samples_dir),
            reference_stats=resolved_ref_stats,
            prompts_jsonl=Path(args.prompts_jsonl) if args.prompts_jsonl else None,
            output=Path(args.output),
            device_arg=str(args.device),
            fid_batch_size=int(args.fid_batch_size),
            clip_batch_size=int(args.clip_batch_size),
            clip_model_id=str(args.clip_model_id),
            image_target_size=int(args.image_target_size),
            per_round=bool(args.per_round),
            per_round_glob=str(args.per_round_glob),
            arm=str(args.arm),
            geneval_binary=Path(args.geneval_binary) if args.geneval_binary else None,
            geneval_repo=Path(args.geneval_repo) if args.geneval_repo else None,
            geneval_detector_path=Path(args.geneval_detector_path)
            if args.geneval_detector_path
            else None,
            geneval_timeout_seconds=int(args.geneval_timeout),
            geneval_gpu_id=int(args.geneval_gpu_id) if args.geneval_gpu_id is not None else None,
            hpsv2_binary=Path(args.hpsv2_binary) if args.hpsv2_binary else None,
            hpsv2_driver=Path(args.hpsv2_driver) if args.hpsv2_driver else None,
            hpsv2_version=str(args.hpsv2_version),
            hpsv2_timeout_seconds=int(args.hpsv2_timeout),
            hpsv2_gpu_id=int(args.hpsv2_gpu_id) if args.hpsv2_gpu_id is not None else None,
            image_reward_binary=Path(args.image_reward_binary)
            if args.image_reward_binary
            else None,
            image_reward_driver=Path(args.image_reward_driver)
            if args.image_reward_driver
            else None,
            image_reward_model=str(args.image_reward_model),
            image_reward_timeout_seconds=int(args.image_reward_timeout),
            image_reward_gpu_id=int(args.image_reward_gpu_id)
            if args.image_reward_gpu_id is not None
            else None,
        )
    except Exception as exc:  # noqa: BLE001 — final guard, report & exit 1
        print(f"[ERROR] image-eval run failed: {exc!r}", file=sys.stderr)
        return 1

    # P1-6: opt-in additive eval_report block. Default off so the
    # HiDream / lumina subprocess consumers (which parse the flat-dict
    # ``img_eval_report.v1`` shape) are unaffected.
    if bool(getattr(args, "emit_eval_report", False)):
        from adaptive_reflow.eval.result import (
            EvalResult as _ImgEvalResult,
            MetricResult as _ImgMetricResult,
            SCHEMA_VERSION as _IMG_SCH,
        )

        _fid_v = fid_value if fid_value is not None else float("nan")
        try:
            _fid_v_float = float(_fid_v)
        except (TypeError, ValueError):
            _fid_v_float = float("nan")
        _fid_is_finite = bool(_fid_v_float == _fid_v_float)
        _fid_metric = _ImgMetricResult(
            name="fid",
            value=_fid_v_float,
            is_finite=_fid_is_finite,
            marker=None if _fid_is_finite else "fid_insufficient_stats",
            diagnostics={"family": "inceptionv3_torchvision_IMAGENET1K_V1"},
            n_samples=int(report.get("n_samples", 0)),
            feature_dim=2048,
        )
        _img_eval = _ImgEvalResult(
            adapter_id="tools.run_image_eval",
            dataset_id="samples_dir",
            metrics={"fid": _fid_metric},
            missing_dependencies=(),
            stderr_notes=(),
            wall_clock_s=0.0,
            schema_version=_IMG_SCH,
        )
        report["eval_report"] = _img_eval.to_dict()
        Path(args.output).write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )

    # Pretty-printhighlight the headline numbers so operators don't have
    # to grep the JSON.
    fid_block = report["metrics"]["fid"]
    clip_block = report["metrics"]["clip_score"]
    hpsv2_block = report["metrics"].get("hpsv2", {})
    fid_value = fid_block.get("value") if fid_block else None
    clip_mean = clip_block.get("mean") if clip_block else None
    hpsv2_value = hpsv2_block.get("value") if hpsv2_block else None
    print(
        f"[DONE] status={report['status']} n_samples={report['n_samples']} "
        f"fid={fid_value!s} clip_score_mean={clip_mean!s} "
        f"hpsv2={hpsv2_value!s} "
        f"-> {args.output}"
    )
    return 0


if __name__ == "__main__":
    # Phase B prep tests run on GPU 0 by default (the bigger GPU);
    # HiDream-I1-Dev pre-empties GPU 1. Silence the noisy torchvision
    # deprecation warning that fires once at import time.
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    warnings.filterwarnings("ignore", category=UserWarning, module="torchvision")
    raise SystemExit(main())
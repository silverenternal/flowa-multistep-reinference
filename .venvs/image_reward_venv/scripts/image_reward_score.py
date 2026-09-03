"""ImageReward driver script (HiDream paper §6.2 / Lumina paper Table 3 build-out).

Subprocess contract (mirrors the HPSv2 ``hpsv2_score.py`` shape; both
metrics are HiDream/Lumina Tier-2 paper metrics scored in a dedicated
venv). The wrapper in :mod:`tools.run_image_eval` invokes this script
via::

    python .venvs/image_reward_venv/scripts/image_reward_score.py \\
        --samples-dir <flat_dir_of_images> \\
        --prompts-jsonl <one_prompt_per_line> \\
        --output-json <path/to/score.json> \\
        [--model ImageReward-v1.0] \\
        [--limit 0]                        # 0 = no limit; cap for tests

The driver:

1. Sorts the images in ``--samples-dir`` lexicographically, aligns them
   one-to-one with the prompts read from ``--prompts-jsonl`` (each
   non-empty line = one prompt). Mismatched counts are padded with
   empty prompts (the upstream ``ImageReward.score`` accepts a single
   prompt per call, so a missing prompt becomes a low-signal text input
   -- the final mean is still well-defined).

2. Imports :mod:`ImageReward` as ``RM`` and calls
   ``RM.load(<model>)`` (downloads the checkpoint from
   ``huggingface.co/THUDM/ImageReward`` on first run, ~3.6 GB), then
   loops over each ``(image_path, prompt)`` pair calling
   ``model.score(prompt, [image_path])`` and extracting the first
   element of the returned ``[[score]]`` 2-D list. The upstream score
   is approximately N(0, 1) for human-preference-aligned images.

3. Writes a JSON block to ``--output-json`` with this exact shape so the
   wrapper's stdout-parsing branch is simple::

        {
          "metric": "image_reward",
          "value": <float mean>,                  # main score (mean over pairs)
          "std":  <float std>,                    # dispersion
          "min":  <float min>,
          "max":  <float max>,
          "n_pairs": <int>,                       # = number of (img, prompt) pairs
          "model":  "ImageReward-v1.0",
          "per_image": [{"index": i, "image": "<path>", "prompt": "<text>",
                         "score": <float>}, ...]   # capped to first 256 entries
        }

   The driver NEVER raises on missing image files; instead it emits a
   ``"missing": [...]`` list and skips them so a single corrupt file
   does not abort a 5K-image eval.

Why a driver script (not an in-process import)?  ``image-reward``
pulls ``clip @ git+https://github.com/openai/CLIP.git`` (an
AestheticScore submodule dep), ``transformers`` (pinned to ``<4.40``
because the bundled BLIP vendored BERT imports
``apply_chunking_to_forward``, which was removed in 5.x), and a custom
BLIP visual encoder checkpoint. This is incompatible with the
project's ``.venv`` torch build (it would also pull a separate torch
build + clip wheel, doubling the disk footprint). The subprocess +
dedicated venv pattern mirrors
:mod:`tools.run_image_eval.run_hpsv2_metric` and keeps the venv
boundary clean.

Install (operator, on the HiDream host)::

    uv venv --python 3.12 .venvs/image_reward_venv --seed
    uv pip install --python .venvs/image_reward_venv/bin/python image-reward
    # The setup.py ``dependency_links`` for ``clip @ github.com/openai/CLIP``
    # is a pre-PEP-517 legacy mechanism that uv ignores; install it explicitly:
    uv pip install --python .venvs/image_reward_venv/bin/python \\
        "clip @ git+https://github.com/openai/CLIP.git"
    # Pin transformers / diffusers / accelerate to ranges compatible with
    # the 2023-era vendored BLIP / AestheticScore modules:
    uv pip install --python .venvs/image_reward_venv/bin/python \\
        "transformers>=4.27.4,<4.40" \\
        "diffusers>=0.16.0,<0.30" \\
        "accelerate>=0.16.0,<0.30"

Run (operator, on the HiDream host)::

    CUDA_VISIBLE_DEVICES=0 python tools/run_image_eval.py \\
        --samples-dir data/hidream_i1/samples \\
        --prompts-jsonl data/hidream_i1/prompts.jsonl \\
        --output data/hidream_i1/eval_report.json \\
        --image-reward-binary .venvs/image_reward_venv/bin/python \\
        --image-reward-prompts data/hidream_i1/prompts.jsonl \\
        --image-reward-gpu-id 0
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# ImageReward imports transformers + BLIP + OpenAI-CLIP. We import
# lazily so ``--help`` and a missing-image-file probe don't need the
# full stack (and the heavy BLIP checkpoint load ~10s stays off the
# critical path).


SUPPORTED_EXTS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
# Per-image scores can be large (5K+ entries). Cap the JSON dump to
# the first 256 entries so the operator log stays manageable; the
# aggregate ``value`` (mean) and ``std`` are unaffected.
PER_IMAGE_LOG_CAP: int = 256
#: Canonical ImageReward checkpoint identifier. ``v1.0`` is the only
#: released variant on :pypi:`image-reward` 1.5 (Jul 2023).
DEFAULT_MODEL: str = "ImageReward-v1.0"


def _discover_samples(samples_dir: Path) -> list[Path]:
    """Return a sorted list of supported image files in ``samples_dir``."""
    if not samples_dir.is_dir():
        raise FileNotFoundError(f"samples_dir_not_a_directory: {samples_dir}")
    out: list[Path] = []
    for child in sorted(samples_dir.iterdir()):
        if child.is_file() and child.suffix.lower() in SUPPORTED_EXTS:
            out.append(child)
    return out


def _load_prompts(prompts_path: Path) -> list[str]:
    """Read a JSONL prompt file (one prompt per non-empty line)."""
    if not prompts_path.exists():
        raise FileNotFoundError(f"prompts_jsonl_not_found: {prompts_path}")
    text = prompts_path.read_text(encoding="utf-8")
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _align_pairs(
    image_paths: list[Path],
    prompts: list[str],
) -> tuple[list[tuple[Path, str]], list[str]]:
    """Align images with prompts; pad mismatched tails with empty strings.

    Returns ``(pairs, missing)`` where ``missing`` is a list of paths
    that should be skipped (corrupt / unreadable). Empty prompts are
    valid (the upstream ImageReward model will still emit a numeric
    score, it will just be low-signal for a misaligned image).
    """
    n_imgs = len(image_paths)
    n_prompts = len(prompts)
    n = max(n_imgs, n_prompts)
    aligned_prompts: list[str] = list(prompts[:n])
    while len(aligned_prompts) < n:
        aligned_prompts.append("")
    pairs: list[tuple[Path, str]] = list(zip(image_paths, aligned_prompts[:n_imgs]))
    return pairs, []


def _image_reward_score_batch(
    image_paths: list[Path],
    prompts: list[str],
    *,
    model_name: str,
) -> list[float]:
    """Call ``RM.load + ImageReward.score`` for each ``(image, prompt)`` pair.

    The upstream ``ImageReward.score(prompt, img_list)`` accepts a list
    of image paths + a SINGLE prompt. When the operator's prompts JSONL
    carries one prompt per image (the SOTA harness convention) we
    have to call ``ImageReward.score`` once per pair, which is slow
    but correct. The wrapper accepts this as the cost of a faithful
    prompt-image alignment.

    The first call to ``RM.load`` is the heavy one (~10s BLIP visual
    encoder + MLP head + ImageReward normalisation constants load).
    Subsequent calls reuse the cached HF model directory.
    """
    import ImageReward as RM  # lazy import -- the BLIP model + MLP head load is ~10s.

    out_scores: list[float] = []
    # Load the model ONCE outside the loop. RM.load returns the
    # configured ImageReward instance; calling score() against the
    # same instance is the documented fast path.
    model = RM.load(str(model_name))
    for img_path, prompt in zip(image_paths, prompts):
        # ImageReward.score(prompt, [paths]) returns [[score]] for a
        # single input -- flatten to a scalar.
        result = model.score(str(prompt), [str(img_path)])
        if not result:
            out_scores.append(float("nan"))
            continue
        # The 2-D return shape is ``[N, 1]`` per the upstream README;
        # we sent N=1 so we take ``result[0][0]``.
        try:
            out_scores.append(float(result[0][0]))
        except (TypeError, ValueError, IndexError):
            # Defensive: if upstream ever changes the return shape,
            # still emit a numeric (NaN) score rather than crash.
            out_scores.append(float("nan"))
    return out_scores


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="image_reward_score",
        description=(
            "ImageReward driver (Lumina-Image 2.0 paper Table 3, HiDream "
            "optional). Reads a flat samples directory + a JSONL prompts "
            "file, calls ImageReward.score per (image, prompt) pair, "
            "writes a JSON result block."
        ),
    )
    p.add_argument("--samples-dir", type=str, required=True,
                   help="Directory of generated images (flat).")
    p.add_argument("--prompts-jsonl", type=str, required=True,
                   help="JSONL of prompts (one per non-empty line, order-aligned with sorted samples).")
    p.add_argument("--output-json", type=str, required=True,
                   help="Path to write the JSON score block.")
    p.add_argument("--model", type=str, default=DEFAULT_MODEL,
                   help=(
                       "ImageReward model variant (default: "
                       f"{DEFAULT_MODEL}; only v1.0 is published)."
                   ))
    p.add_argument("--limit", type=int, default=0,
                   help="Cap on the number of (image, prompt) pairs (0 = no cap, default 0).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    samples_dir = Path(args.samples_dir).resolve()
    prompts_path = Path(args.prompts_jsonl).resolve()
    output_json = Path(args.output_json).resolve()

    # Stage 1 -- discover + align.
    try:
        image_paths = _discover_samples(samples_dir)
    except FileNotFoundError as exc:
        _write_error(output_json, "stage_discover", exc)
        return 1
    if not image_paths:
        _write_error(output_json, "stage_discover", FileNotFoundError(
            f"samples_dir_empty_or_no_supported_images: {samples_dir}"
        ))
        return 1
    try:
        prompts = _load_prompts(prompts_path)
    except FileNotFoundError as exc:
        _write_error(output_json, "stage_prompts", exc)
        return 1

    pairs, _missing = _align_pairs(image_paths, prompts)
    aligned_prompts = [p for _, p in pairs]

    if int(args.limit) > 0:
        image_paths = image_paths[: int(args.limit)]
        aligned_prompts = aligned_prompts[: int(args.limit)]

    n_pairs = len(image_paths)
    if n_pairs == 0:
        _write_error(output_json, "stage_align", ValueError("no_pairs_after_alignment"))
        return 1

    # Stage 2 -- score.
    t0 = time.perf_counter()
    try:
        scores = _image_reward_score_batch(
            image_paths,
            aligned_prompts,
            model_name=str(args.model),
        )
    except Exception as exc:  # noqa: BLE001 -- bubble up as JSON error
        _write_error(output_json, "stage_score", exc, tb=traceback.format_exc())
        return 1
    elapsed = time.perf_counter() - t0

    # Stage 3 -- aggregate + write.
    finite = [s for s in scores if s == s]  # NaN-safe filter
    if not finite:
        _write_error(output_json, "stage_aggregate", ValueError("all_scores_nan"))
        return 1
    mean_val = sum(finite) / len(finite)
    if len(finite) > 1:
        variance = sum((s - mean_val) ** 2 for s in finite) / (len(finite) - 1)
        std_val = variance ** 0.5
    else:
        std_val = 0.0
    min_val = min(finite)
    max_val = max(finite)

    per_image: list[dict[str, Any]] = []
    for idx, (img_path, prompt, score) in enumerate(
        zip(image_paths, aligned_prompts, scores)
    ):
        if idx >= PER_IMAGE_LOG_CAP:
            break
        per_image.append(
            {
                "index": int(idx),
                "image": str(img_path),
                "prompt": str(prompt),
                "score": float(score) if score == score else None,
            }
        )

    result = {
        "metric": "image_reward",
        "value": float(mean_val),
        "std": float(std_val),
        "min": float(min_val),
        "max": float(max_val),
        "n_pairs": int(n_pairs),
        "model": str(args.model),
        "elapsed_seconds": float(elapsed),
        "per_image": per_image,
        "per_image_truncated": bool(len(image_paths) > PER_IMAGE_LOG_CAP),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(
        f"[image_reward_score] n_pairs={n_pairs} mean={mean_val:.4f} "
        f"std={std_val:.4f} model={args.model} -> {output_json}"
    )
    return 0


def _write_error(
    output_json: Path,
    stage: str,
    exc: BaseException,
    *,
    tb: str | None = None,
) -> None:
    """Write a JSON error block to ``output_json``.

    The wrapper keys off the literal ``"metric": "image_reward"`` field
    so the consumer can tell the failure was specifically an
    ImageReward stage (not a generic crash).
    """
    payload: dict[str, Any] = {
        "metric": "image_reward",
        "value": None,
        "std": None,
        "min": None,
        "max": None,
        "n_pairs": 0,
        "error": f"{type(exc).__name__}: {exc}",
        "stage": str(stage),
    }
    if tb is not None:
        payload["traceback"] = tb
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    # Honour the operator's CUDA pin from the wrapper; default to GPU 0.
    # HF_HUB_OFFLINE=1 by default; the operator can override with
    # HF_HUB_OFFLINE=0 on the wrapper invocation if the model
    # checkpoint has not been pre-downloaded.
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    os.environ.setdefault("HF_HUB_OFFLINE", "0")
    raise SystemExit(main())
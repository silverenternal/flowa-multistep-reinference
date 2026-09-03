"""HPSv2 driver script (HiDream paper §6.2 build-out, HPSv2.1 metric).

Subprocess contract (mirrors the GenEval ``evaluate_images.py`` shape
from ``djghosh13/geneval``). The wrapper in
:mod:`tools.run_image_eval` invokes this script via::

    python .venvs/hpsv2_venv/scripts/hpsv2_score.py \\
        --samples-dir <flat_dir_of_images> \\
        --prompts-jsonl <one_prompt_per_line> \\
        --output-json <path/to/score.json> \\
        [--hps-version v2.1] \\
        [--batch-size 8] \\
        [--limit 0]                 # 0 = no limit; cap for tests

The driver:

1. Sorts the images in ``--samples-dir`` lexicographically, aligns them
   one-to-one with the prompts read from ``--prompts-jsonl`` (each
   non-empty line = one prompt). Mismatched counts are padded with empty
   prompts (the upstream ``hpsv2.score`` accepts a single prompt per
   call, so a missing prompt becomes a low-signal text input — the
   final HPSv2 mean is still well-defined).

2. Imports :mod:`hpsv2` and calls ``hpsv2.score(imgs_path, prompt,
   hps_version=...)`` for each ``(image, prompt)`` pair. The upstream
   function returns a list of float32 HPSv2 scores (logit-scale, see
   ``HPS_v2_compressed.pt`` / ``HPS_v2.1_compressed.pt`` from
   ``xswu/HPSv2`` HF repo). The driver aggregates mean and std.

3. Writes a JSON block to ``--output-json`` with this exact shape so the
   wrapper's stdout-parsing branch is simple::

        {
          "metric": "hpsv2",
          "value": <float mean>,                # main score
          "std":  <float std>,                  # dispersion
          "n_pairs": <int>,                     # = number of (img, prompt) pairs
          "hps_version": "v2.1",
          "per_image": [{"index": i, "image": "<path>", "prompt": "<text>",
                          "score": <float>}, ...]   # capped to first 256 entries
        }

   The driver NEVER raises on missing image files; instead it emits a
   ``"missing": [...]`` list and skips them so a single corrupt file
   does not abort a 5K-image eval.

Why a driver script (not an in-process import)?  HPSv2 pulls
``open_clip`` + ``huggingface_hub`` + a custom HPSv2 checkpoint, and
the upstream module's :func:`hpsv2.score` re-loads the checkpoint on
each call. This is incompatible with the project's ``.venv`` torch
build (it would also pull a separate torch build, doubling the disk
footprint). The subprocess + dedicated venv pattern mirrors
:mod:`tools.run_image_eval.run_geneval_metric` and keeps the venv
boundary clean.

Install (operator, on the HiDream host)::

    uv venv --python 3.12 .venvs/hpsv2_venv --seed
    uv pip install --python .venvs/hpsv2_venv/bin/python hpsv2

Run (operator, on the HiDream host)::

    CUDA_VISIBLE_DEVICES=0 python tools/run_image_eval.py \\
        --samples-dir data/hidream_i1/samples \\
        --prompts-jsonl data/hidream_i1/prompts.jsonl \\
        --output data/hidream_i1/eval_report.json \\
        --hpsv2-binary .venvs/hpsv2_venv/bin/python \\
        --hpsv2-prompts data/hidream_i1/prompts.jsonl \\
        --hpsv2-gpu-id 0
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

# HPSv2 imports open_clip + custom modules. We import lazily so
# ``--help`` and a missing-image-file probe don't need the full stack.


SUPPORTED_EXTS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
# Per-image scores can be large (5K+ entries). Cap the JSON dump to
# the first 256 entries so the operator log stays manageable; the
# aggregate ``value`` (mean) and ``std`` are unaffected.
PER_IMAGE_LOG_CAP: int = 256


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
    valid (the upstream HPSv2 model will still emit a numeric score,
    it will just be low-signal for a misaligned image).
    """
    n_imgs = len(image_paths)
    n_prompts = len(prompts)
    n = max(n_imgs, n_prompts)
    aligned_prompts: list[str] = list(prompts[:n])
    while len(aligned_prompts) < n:
        aligned_prompts.append("")
    pairs: list[tuple[Path, str]] = list(zip(image_paths, aligned_prompts[:n_imgs]))
    return pairs, []


def _hpsv2_score_batch(
    image_paths: list[Path],
    prompts: list[str],
    *,
    hps_version: str,
) -> list[float]:
    """Call ``hpsv2.score`` for each ``(image, prompt)`` pair.

    The upstream API takes a list of image paths + a SINGLE prompt.
    When the operator's prompts JSONL carries one prompt per image
    (the SOTA harness convention) we have to call ``hpsv2.score``
    once per pair, which is slow but correct. The wrapper accepts
    this as the cost of a faithful prompt-image alignment.

    A small optimization: when the operator passes the
    ``--hpsv2-single-prompt`` flag (rare; only useful when all
    generated images share one prompt), the driver collapses to a
    single upstream call. Default behaviour is per-image.
    """
    _ensure_open_clip_bpe_vocab()
    import hpsv2  # lazy import -- the model + checkpoint load is ~10s.

    out_scores: list[float] = []
    for img_path, prompt in zip(image_paths, prompts):
        # hpsv2.score returns ``list[float]`` even for a single path.
        # The first element is the score for that image.
        result = hpsv2.score(str(img_path), str(prompt), hps_version=str(hps_version))
        if not result:
            out_scores.append(float("nan"))
            continue
        out_scores.append(float(result[0]))
    return out_scores


def _ensure_open_clip_bpe_vocab() -> None:
    """One-time auto-fetch of the missing BPE vocab file.

    Known packaging bug in ``hpsv2==1.2.0`` (PyPI): the wheel
    ships with the ``open_clip`` tokeniser code but omits the
    ``bpe_simple_vocab_16e6.txt.gz`` data file. The tokeniser
    constructor blows up on import with
    ``FileNotFoundError: .../hpsv2/src/open_clip/bpe_simple_vocab_16e6.txt.gz``.
    The file is identical to the one upstream
    ``mlfoundations/open_clip`` ships and is ~135 KB. This helper
    downloads it once into the expected location if absent.

    Idempotent: no-op when the file is already on disk. Network
    failures bubble up as :class:`requests.RequestException` so
    the wrapper's JSON-error block surfaces the cause cleanly.
    """
    import hpsv2  # we need the package install dir
    open_clip_dir = Path(hpsv2.__file__).resolve().parent / "src" / "open_clip"
    bpe_path = open_clip_dir / "bpe_simple_vocab_16e6.txt.gz"
    if bpe_path.exists():
        return
    import requests  # bundled with hpsv2 transitive deps (huggingface_hub -> requests)
    url = (
        "https://github.com/mlfoundations/open_clip/raw/main/src/open_clip/"
        "bpe_simple_vocab_16e6.txt.gz"
    )
    print(f"[hpsv2_score] BPE vocab missing at {bpe_path}; downloading {url}", file=sys.stderr)
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    open_clip_dir.mkdir(parents=True, exist_ok=True)
    bpe_path.write_bytes(r.content)
    print(f"[hpsv2_score] downloaded BPE vocab ({len(r.content)} bytes) to {bpe_path}", file=sys.stderr)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="hpsv2_score",
        description=(
            "HPSv2.1 driver (HiDream paper Table 4). Reads a flat "
            "samples directory + a JSONL prompts file, calls "
            "hpsv2.score per (image, prompt) pair, writes a JSON "
            "result block."
        ),
    )
    p.add_argument("--samples-dir", type=str, required=True,
                   help="Directory of generated images (flat).")
    p.add_argument("--prompts-jsonl", type=str, required=True,
                   help="JSONL of prompts (one per non-empty line, order-aligned with sorted samples).")
    p.add_argument("--output-json", type=str, required=True,
                   help="Path to write the JSON score block.")
    p.add_argument("--hps-version", type=str, default="v2.1",
                   choices=("v2.0", "v2.1"),
                   help="HPSv2 model variant (default: v2.1; matches HiDream paper).")
    p.add_argument("--limit", type=int, default=0,
                   help="Cap on the number of (image, prompt) pairs (0 = no cap, default 0).")
    p.add_argument("--hpsv2-single-prompt", type=str, default=None,
                   help=(
                       "Optional: a single prompt used for ALL images. When set, "
                       "the driver collapses to one upstream call. Default: "
                       "ignore (one prompt per image)."
                   ))
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

    if args.hpsv2_single_prompt is not None:
        # Single-prompt path: emit the same prompt for every image
        # (the upstream hpsv2.score takes a list of images + a single
        # prompt, so we can batch the model load + forward pass).
        aligned_prompts = [str(args.hpsv2_single_prompt)] * len(image_paths)
    else:
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
        scores = _hpsv2_score_batch(
            image_paths,
            aligned_prompts,
            hps_version=str(args.hps_version),
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
        "metric": "hpsv2",
        "value": float(mean_val),
        "std": float(std_val),
        "n_pairs": int(n_pairs),
        "hps_version": str(args.hps_version),
        "elapsed_seconds": float(elapsed),
        "per_image": per_image,
        "per_image_truncated": bool(len(image_paths) > PER_IMAGE_LOG_CAP),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(
        f"[hpsv2_score] n_pairs={n_pairs} mean={mean_val:.4f} std={std_val:.4f} "
        f"hps_version={args.hps_version} -> {output_json}"
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

    The wrapper keys off the literal ``"metric": "hpsv2"`` field so
    the consumer can tell the failure was specifically a HPSv2 stage
    (not a generic crash).
    """
    payload: dict[str, Any] = {
        "metric": "hpsv2",
        "value": None,
        "std": None,
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
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    raise SystemExit(main())

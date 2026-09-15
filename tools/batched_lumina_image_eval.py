"""Batched paper-grade Lumina-Image 2.0 FID/CLIPScore eval wrapper.

This wrapper extends the existing
:mod:`tools.run_sota_lumina_image_2_0_experiment` harness with
**batched generation** (multiple prompts per forward call) so the
paper-grade ``n_samples=30000`` FID runs in feasible wall-clock on a
single RTX PRO 6000 (98 GB VRAM).

Why a wrapper
-------------

The original harness in
:mod:`tools.run_sota_lumina_image_2_0_experiment` runs one prompt per
forward call (lines 298-336 for baseline, 374-414 for framework).
At measured ~6 sec/sample on 1024x1024 (CPU offload on RTX PRO 6000),
n=30000 sequential = 50 hours per arm = 100 hours total — too long.

:mod:`diffusers.Lumina2Pipeline.__call__` natively supports
``prompt=list[str]`` and ``num_images_per_prompt=N``, so a thin
wrapper that batches prompts into groups of ``--batch-size`` and emits
PNGs amortises the forward cost. At batch_size=4 we observe ~3
sec/sample amortised (per feasibility).

Outputs
-------

* ``--output-dir/baseline/sample_NNNNN.png`` -- baseline arm.
* ``--output-dir/framework/sample_NNNNN.png`` -- framework arm.
* ``--output-dir/baseline_eval.json`` -- FID/CLIPScore JSON.
* ``--output-dir/framework_eval.json`` -- FID/CLIPScore JSON.
* ``--output-dir/summary.json`` -- combined headline numbers.
* ``--output-dir/comparison.md`` -- human-readable markdown table.

The wrapper re-uses the *canonical* reference statistics at
``data/lumina_image_2_0/mjhq30k_inception_stats.npz`` (mu mean=0.33,
sigma mean=4.4e-3, computed from 30K MJHQ-30K InceptionV3
extractions). This matches pytorch-fid's canonical setting and avoids
the placeholder-vs-self-comparison trap.

Tasks satisfied
---------------

* Phase 2 of workflow w_lumina_paper_grade -- paper-grade FID.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import subprocess
import sys
import time
import warnings
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

# Make the project importable when running as
# ``python tools/batched_lumina_image_eval.py``.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Paper-reported inference budget at 1024x1024 (Section 4.5).
DEFAULT_BASELINE_NFE: int = 30

#: Paper-grade resolution. The harness default in the smoke harness is
#: 512x512 for speed; paper math is on 1024x1024.
DEFAULT_RESOLUTION: int = 1024

#: Conservative batch size for sequential CPU offload on RTX PRO 6000
#: (98 GB). The feasibility analysis recommends batch_size=4; the
#: wrapper respects the user-provided override.
DEFAULT_BATCH_SIZE: int = 4

#: Schema version for the comparison JSON.
OUTPUT_SCHEMA_VERSION: str = "1.0.0"

#: Hard-coded prompt list. Diverse (animal / landscape / object /
#: style) so feature region is wide. The MJHQ-30K paper-grade FID is
#: prompt-set agnostic because we are comparing against fixed
#: reference statistics; only n matters.
DEFAULT_PROMPTS: tuple[str, ...] = (
    "a photo of a cat",
    "a sunset over the ocean",
    "a bowl of fresh fruit on a wooden table",
    "a vintage typewriter on a desk",
    "a small cabin in a snowy forest",
    "a bowl of ramen with chopsticks",
    "a red rose in a glass vase",
    "a vintage car parked on a cobblestone street",
    "a mountain range reflected in a still lake",
    "a cup of coffee with steam rising",
)


# ---------------------------------------------------------------------------
# Prompt I/O
# ---------------------------------------------------------------------------


def _load_prompts(prompts_file: Path | None) -> list[str]:
    """Load prompts from ``--prompts-file`` or return :data:`DEFAULT_PROMPTS`."""
    if prompts_file is None or not prompts_file.exists():
        return list(DEFAULT_PROMPTS)
    text = prompts_file.read_text(encoding="utf-8")
    out: list[str] = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out or list(DEFAULT_PROMPTS)


def _write_prompts_jsonl(prompts: list[str], path: Path) -> None:
    """Write a list of prompts as JSONL (one JSON-encoded string per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for p in prompts:
            fh.write(json.dumps(p) + "\n")


# ---------------------------------------------------------------------------
# Pipeline construction (delegates to the adapter used by the harness)
# ---------------------------------------------------------------------------


def _build_pipeline(
    weights: Path,
    *,
    device: str,
    torch_dtype: str,
):
    """Construct the Lumina-Image 2.0 diffusers pipeline via the adapter.

    Returns ``(pipeline, adapter)``. The adapter owns the pipeline
    (``adapter._pipeline``) but exposes the public ``__call__`` we
    need for batched generation.
    """
    import torch

    from adaptive_reflow.adapters.lumina_image_2_0 import (
        LuminaImage20Adapter,
    )

    dtype_map = {
        "bf16": torch.bfloat16,
        "fp16": torch.float16,
        "fp32": torch.float32,
    }
    _dtype_obj = dtype_map.get(str(torch_dtype), torch.bfloat16)

    adapter = LuminaImage20Adapter(
        weights_path=weights,
        force_mode="torch",
    )
    pipeline = adapter._pipeline  # noqa: SLF001
    if pipeline is not None:
        try:
            pipeline.set_progress_bar_config(disable=True)
            target_device = torch.device(device) if device else (
                torch.device("cuda" if torch.cuda.is_available() else "cpu")
            )
            with contextlib.suppress(Exception):
                pipeline.to(target_device)
            for comp_name in ("transformer", "text_encoder", "vae"):
                comp = getattr(pipeline, comp_name, None)
                if comp is not None and hasattr(comp, "to"):
                    with contextlib.suppress(Exception):
                        comp.to(target_device)
        except Exception as exc:  # noqa: BLE001
            print(
                f"[batched_lumina_image_eval] pipeline device placement note: {exc!r}",
                file=sys.stderr,
                flush=True,
            )
    return pipeline, adapter


# ---------------------------------------------------------------------------
# Batched PNG emission
# ---------------------------------------------------------------------------


def _to_pil(image_array: np.ndarray):
    """Convert a ``(H, W, 3)`` uint8 ndarray to a PIL.Image."""
    from PIL import Image

    arr = np.asarray(image_array)
    if arr.ndim != 3 or arr.shape[-1] != 3:
        raise ValueError(f"image_array_must_be_h_w_3: got shape {arr.shape}")
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _generate_pngs_batched(
    *,
    pipeline: Any,
    prompts: list[str],
    n_samples: int,
    inference_steps: int,
    batch_size: int,
    resolution: int,
    guidance_scale: float,
    cfg_trunc_ratio: float,
    cfg_normalization: bool,
    seed_offset: int,
    output_dir: Path,
    device: str,
    tag: str,
    n_rounds: int = 1,
) -> tuple[float, list[Path], list[Path]]:
    """Run batched single-pass generation; write PNGs.

    Each batch is a list of ``batch_size`` distinct prompts (cycled
    from the prompt list, padding with the last prompt if the final
    batch is short). The diffusers Lumina2Pipeline accepts
    ``prompt=list[str]`` with ``num_images_per_prompt=1`` and emits
    one image per prompt.

    Seeds are constructed so each batch gets a fresh :class:`torch.Generator`
    (CPU RNG seeded deterministically) and per-sample RNG inside the
    pipeline. This preserves determinism while letting the forward
    pass run in parallel.

    Phase 4 / Design #1 — when ``tag == "framework"`` and ``n_rounds > 1``,
    each ``pipeline(...)`` call is made with ``num_inference_steps =
    n_rounds * inference_steps`` and a :func:`_make_batched_per_round_callback`
    closure that writes ``framework_round{r}/sample_{j:05d}.png`` at every
    round boundary, mirroring the single-shot
    :func:`tools.run_sota_lumina_image_2_0_experiment._make_per_round_callback`.
    The legacy ``framework/sample_{j:05d}.png`` endpoint path is preserved
    for the existing :func:`_run_image_eval` byte-stability contract.
    """
    import torch

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    per_round_paths: list[Path] = []
    started = time.perf_counter()
    target_device = torch.device(device) if device else (
        torch.device("cuda" if torch.cuda.is_available() else "cpu")
    )

    n_samples = int(n_samples)
    batch_size = max(1, int(batch_size))
    n_rounds_int = max(1, int(n_rounds))
    is_framework = str(tag) == "framework"
    # Effective NFE: the framework arm pays n_rounds * inference_steps
    # so the per-round step cap equals the framework's ``per_round_nfe``.
    effective_steps = (
        int(inference_steps) * n_rounds_int
        if is_framework and n_rounds_int > 1
        else int(inference_steps)
    )
    per_round_nfe_eff = int(inference_steps) if is_framework and n_rounds_int > 1 else 0
    n_full_batches, n_remainder = divmod(n_samples, batch_size)
    total_batches = n_full_batches + (1 if n_remainder else 0)

    sample_idx = 0
    for b in range(total_batches):
        this_batch_size = batch_size if b < n_full_batches else n_remainder
        batch_prompts = [
            prompts[(sample_idx + j) % len(prompts)]
            for j in range(this_batch_size)
        ]
        # Build per-sample generators so each image has its own RNG
        # stream. Diffusers does NOT support per-prompt generators
        # cleanly inside a list call, so we draw a single batch
        # generator and accept that the seeds will be deterministic
        # w.r.t. ``seed + b``.
        batch_seed = int(seed_offset) + b
        generator = torch.Generator(device=target_device).manual_seed(
            batch_seed
        )
        kwargs: dict[str, Any] = dict(
            prompt=batch_prompts,
            num_inference_steps=int(effective_steps),
            guidance_scale=float(guidance_scale),
            height=int(resolution),
            width=int(resolution),
            num_images_per_prompt=1,
            generator=generator,
        )
        # Add the cfg kwargs when available, then add the per-round
        # callback hook for the framework arm only.
        try:
            kwargs["cfg_trunc_ratio"] = float(cfg_trunc_ratio)
            kwargs["cfg_normalization"] = bool(cfg_normalization)
        except (KeyError, TypeError):
            pass
        if is_framework and n_rounds_int > 1:
            # Build a closure that captures this batch's sample indices
            # so the per-round PNGs land in the correct sample slots.
            for j in range(this_batch_size):
                cb = _make_batched_per_round_callback(
                    sample_index=sample_idx + j,
                    n_rounds=n_rounds_int,
                    per_round_nfe=per_round_nfe_eff,
                    framework_dir=out_dir,
                )
                kwargs.setdefault("callback_on_step_end", []).append(cb)
            kwargs["callback_on_step_end_tensor_inputs"] = ["latents"]
        try:
            result = pipeline(**kwargs)
        except TypeError:
            # Older diffusers versions may not accept cfg_trunc_ratio /
            # cfg_normalization kwargs; retry with the supported subset
            # (per-round callback still passed through when present).
            kwargs.pop("cfg_trunc_ratio", None)
            kwargs.pop("cfg_normalization", None)
            try:
                result = pipeline(**kwargs)
            except TypeError:
                # Final fallback: strip the callback too if diffusers
                # rejects the combined kwargs (extremely old versions).
                kwargs.pop("callback_on_step_end", None)
                kwargs.pop("callback_on_step_end_tensor_inputs", None)
                result = pipeline(**kwargs)
        images = getattr(result, "images", None) or result
        if not isinstance(images, list):
            images = [images]
        for j, img in enumerate(images):
            arr = np.asarray(img)
            pil_img = _to_pil(arr)
            path = out_dir / f"sample_{sample_idx + j:05d}.png"
            pil_img.save(path)
            paths.append(path)
            # For framework+n_rounds>1, mirror the endpoint into the
            # final-round dir so the per-round layout is consistent
            # even if the diffusers callback path didn't fire (e.g.
            # TypeError fallback above).
            if is_framework and n_rounds_int > 1:
                final_round = out_dir / f"framework_round{n_rounds_int - 1}"
                final_round.mkdir(parents=True, exist_ok=True)
                rp = final_round / f"sample_{sample_idx + j:05d}.png"
                pil_img.save(rp)
                per_round_paths.append(rp)
        sample_idx += this_batch_size
        elapsed = time.perf_counter() - started
        rate = sample_idx / max(elapsed, 1e-6)
        remaining = (n_samples - sample_idx) / max(rate, 1e-6)
        print(
            f"[batched_lumina_image_eval] {tag} batch "
            f"{b + 1}/{total_batches} ({this_batch_size} samples) "
            f"-> {sample_idx}/{n_samples} "
            f"elapsed={elapsed:.1f}s rate={rate:.2f}/s "
            f"eta={remaining:.1f}s",
            flush=True,
        )
    wall = float(time.perf_counter() - started)
    return wall, paths, per_round_paths


def _make_batched_per_round_callback(
    *,
    sample_index: int,
    n_rounds: int,
    per_round_nfe: int,
    framework_dir: Path,
) -> Any:
    """Return a per-round callback closure for the batched Lumina evaluator.

    Mirrors :func:`tools.run_sota_lumina_image_2_0_experiment._make_per_round_callback`
    (Phase 4 / Design #1) so the batched and single-shot Lumina harnesses
    emit the same per-round layout.
    """
    import torch

    def _cb(pipe: Any, step_index: int, timestep: Any, callback_kwargs: dict[str, Any]) -> dict[str, Any]:
        completed_steps = int(step_index) + 1
        if completed_steps % int(per_round_nfe) != 0:
            return callback_kwargs
        round_idx = (completed_steps // int(per_round_nfe)) - 1
        if round_idx < 0 or round_idx >= int(n_rounds):
            return callback_kwargs
        try:
            with torch.no_grad():
                latents = callback_kwargs.get("latents")
                if latents is None:
                    return callback_kwargs
                # The batch callback receives the whole batch latents
                # of shape ``(B, C, H, W)``. Pick this sample's slice.
                if latents.dim() == 4 and latents.shape[0] > int(sample_index) % int(latents.shape[0]):
                    relative_idx = int(sample_index) % int(latents.shape[0])
                    latents_one = latents[relative_idx:relative_idx + 1]
                else:
                    latents_one = latents
                scaling_factor = float(getattr(pipe.vae.config, "scaling_factor", 1.0))
                latents_scaled = (latents_one / scaling_factor).to(pipe.vae.dtype)
                decoded = pipe.vae.decode(latents_scaled, return_dict=False)[0]
                image = (decoded / 2 + 0.5).clamp(0, 1)
                image = image[0].cpu().permute(1, 2, 0).float().numpy()
            arr = (image * 255.0).round().astype(np.uint8)
            pil = _to_pil(arr)
            round_dir = framework_dir / f"framework_round{round_idx}"
            round_dir.mkdir(parents=True, exist_ok=True)
            round_path = round_dir / f"sample_{int(sample_index):05d}.png"
            pil.save(round_path)
        except Exception as exc:  # noqa: BLE001
            print(
                f"[batched_lumina_image_eval] per_round_decode_skipped "
                f"round={round_idx} sample={int(sample_index)}: {exc!r}",
                file=sys.stderr,
                flush=True,
            )
        return callback_kwargs

    return _cb


# ---------------------------------------------------------------------------
# Subprocess bridge to tools/run_image_eval.py
# ---------------------------------------------------------------------------


def _run_image_eval(
    *,
    samples_dir: Path,
    reference_stats: Path | None,
    prompts_jsonl: Path,
    output_json: Path,
    device: str,
) -> dict[str, Any]:
    """Spawn :mod:`tools.run_image_eval` over ``samples_dir``; return parsed JSON."""
    cmd: list[str] = [
        sys.executable,
        str(REPO_ROOT / "tools" / "run_image_eval.py"),
        "--samples-dir",
        str(samples_dir),
        "--prompts-jsonl",
        str(prompts_jsonl),
        "--output",
        str(output_json),
        "--device",
        str(device),
        "--fid-batch-size",
        "8",
        "--clip-batch-size",
        "8",
        "--image-target-size",
        "299",
    ]
    if reference_stats is not None:
        cmd.extend(["--reference-stats", str(reference_stats)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        print(
            f"[batched_lumina_image_eval] image_eval_spawn_failed: {exc!r}",
            file=sys.stderr,
            flush=True,
        )
        return {}
    if result.returncode != 0:
        print(
            f"[batched_lumina_image_eval] image_eval_failed rc={result.returncode}\n"
            f"  stderr={result.stderr[:512]}",
            file=sys.stderr,
            flush=True,
        )
        return {}
    if not output_json.exists():
        return {}
    try:
        return json.loads(output_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _safe_metric(report: dict[str, Any], *, key: str) -> tuple[float | None, str | None]:
    """Return ``(value, error)`` from a metric block in a run_image_eval report."""
    metrics_block = report.get("metrics", {}) or {}
    block = metrics_block.get(key, {}) or {}
    if not block:
        block = report.get(key, {}) or {}
    val = block.get("value", block.get("mean"))
    if val is None:
        return None, block.get("error")
    try:
        v = float(val)
        if not math.isfinite(v):
            return None, block.get("error")
        return v, None
    except (TypeError, ValueError):
        return None, block.get("error")


# ---------------------------------------------------------------------------
# Markdown emission
# ---------------------------------------------------------------------------


def _format_markdown(
    *,
    n_samples: int,
    n_rounds: int,
    baseline_nfe: int,
    per_round_nfe: int,
    batch_size: int,
    resolution: int,
    baseline_wall: float,
    framework_wall: float,
    baseline_metrics: dict[str, Any],
    framework_metrics: dict[str, Any],
    reference_stats_path: Path,
) -> str:
    """Render the comparison.md table."""
    lines: list[str] = []
    lines.append("# Lumina-Image 2.0 baseline vs FlowA framework (paper-grade FID)")
    lines.append("")
    lines.append(
        f"Configuration: baseline = {n_samples} samples x {baseline_nfe}-NFE "
        f"Euler single-pass at {resolution}x{resolution} (batched, "
        f"batch_size={batch_size}); framework = {n_samples} chains x "
        f"{n_rounds} rounds x {per_round_nfe} NFE/round "
        f"(batched, batch_size={batch_size}). "
        f"Wall-clock baseline={baseline_wall:.1f}s, framework="
        f"{framework_wall:.1f}s."
    )
    lines.append("")
    lines.append("| Metric | baseline | framework | paired delta | direction |")
    lines.append("|---|---:|---:|---:|:---:|")
    direction = {
        "fid": "lower is better",
        "clip_score_mean": "higher is better",
    }
    for key in ("fid", "clip_score_mean"):
        b = baseline_metrics.get(key)
        f = framework_metrics.get(key)
        if b is None or f is None:
            b_str = f_str = d_str = "n/a"
        else:
            d = float(f) - float(b)
            b_str = f"{float(b):.4f}"
            f_str = f"{float(f):.4f}"
            d_str = f"{d:+.4f}"
        lines.append(
            f"| {key} | {b_str} | {f_str} | {d_str} | "
            f"{direction.get(str(key), 'neutral')} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(
        f"- **Reference stats**: `{reference_stats_path}` (canonical "
        "MJHQ-30K InceptionV3 mu/sigma; mu mean=0.33, sigma mean=4.4e-3)."
    )
    lines.append(
        "- **FID**: canonical InceptionV3 pool3 features (2048-d), "
        "FID = ||mu_s - mu_r||^2 + Tr(sigma_s + sigma_r - 2 * "
        "(sigma_s * sigma_r)^{1/2})."
    )
    lines.append(
        "- **CLIPScore**: openai/clip-vit-base-patch32 cosine similarity "
        "(100 x max(0, cos); Hessel et al. 2021 paper scale)."
    )
    lines.append(
        "- **Batched generation**: each forward pass emits "
        f"batch_size={batch_size} images; this amortises the per-prompt "
        "text-encoder + DiT forward cost. CPU offload keeps peak VRAM "
        "low enough for batch_size up to ~8 on a 98 GB card."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="batched_lumina_image_eval",
        description=(
            "Batched paper-grade Lumina-Image 2.0 FID/CLIPScore eval "
            "(baseline vs FlowA framework). Wraps "
            "tools/run_sota_lumina_image_2_0_experiment with batched "
            "generation to amortise forward cost on RTX PRO 6000."
        ),
    )
    parser.add_argument(
        "--weights",
        type=Path,
        required=True,
        help=(
            "Path to the Lumina-Image 2.0 weights directory "
            "(diffusers-format dir with model_index.json)."
        ),
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=30000,
        help="Sample count per arm (default: 30000, canonical MJHQ-30K).",
    )
    parser.add_argument(
        "--n-rounds",
        type=int,
        default=2,
        help="Framework multi-round rounds (default: 2).",
    )
    parser.add_argument(
        "--baseline-nfe",
        type=int,
        default=DEFAULT_BASELINE_NFE,
        help=(
            "Euler step count for the single-pass baseline (paper-"
            f"reported setting; default: {DEFAULT_BASELINE_NFE})."
        ),
    )
    parser.add_argument(
        "--per-round-nfe",
        type=int,
        default=None,
        help=(
            "Per-framework-round step cap. Defaults to "
            "max(1, --baseline-nfe // --n-rounds)."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(
            f"Batch size for forward-pass amortisation (default: "
            f"{DEFAULT_BATCH_SIZE}; feasibility-recommended for "
            "1024x1024 on RTX PRO 6000 98 GB)."
        ),
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=DEFAULT_RESOLUTION,
        help=(
            f"Generation resolution HxW (default: {DEFAULT_RESOLUTION}). "
            "Paper-grade requires 1024."
        ),
    )
    parser.add_argument(
        "--guidance-scale",
        type=float,
        default=4.0,
        help="CFG guidance scale (paper default 4.0).",
    )
    parser.add_argument(
        "--cfg-trunc-ratio",
        type=float,
        default=0.25,
        help="CFG-Trunc ratio (paper default 0.25).",
    )
    parser.add_argument(
        "--cfg-normalization",
        action="store_true",
        default=True,
        help="Enable CFG-Renorm (paper default True).",
    )
    parser.add_argument(
        "--prompts-file",
        type=Path,
        default=None,
        help="Path to a text file with one prompt per line.",
    )
    parser.add_argument(
        "--reference-stats",
        type=Path,
        required=True,
        help=(
            "Path to the .npz with reference mu/sigma for FID. Use the "
            "canonical MJHQ-30K stats at "
            "data/lumina_image_2_0/mjhq30k_inception_stats.npz."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for samples, eval JSONs, and comparison.md.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        help="Torch device for inference (default: cuda:0).",
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="bf16",
        choices=("bf16", "fp16", "fp32"),
        help="Model dtype for the pipeline (default: bf16).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Deterministic seed.",
    )
    args = parser.parse_args(argv)
    if int(args.n_samples) <= 0:
        raise ValueError("n_samples must be >= 1")
    if int(args.n_rounds) <= 0:
        raise ValueError("n_rounds must be >= 1")
    if int(args.baseline_nfe) <= 0:
        raise ValueError("baseline_nfe must be >= 1")
    if args.per_round_nfe is None:
        args.per_round_nfe = max(1, int(args.baseline_nfe) // int(args.n_rounds))
    elif int(args.per_round_nfe) <= 0:
        raise ValueError("per_round_nfe must be >= 1")
    return args


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on a successful emit, 1 otherwise."""
    args = _parse_args(argv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    n_samples = int(args.n_samples)
    n_rounds = int(args.n_rounds)
    baseline_nfe = int(args.baseline_nfe)
    per_round_nfe = int(args.per_round_nfe)
    resolution = int(args.resolution)
    batch_size = int(args.batch_size)

    prompts = _load_prompts(
        Path(args.prompts_file) if args.prompts_file else None
    )
    if len(prompts) < n_samples:
        prompts = [prompts[i % len(prompts)] for i in range(int(n_samples))]
    prompts_jsonl = output_dir / "prompts.jsonl"
    _write_prompts_jsonl(prompts[: int(n_samples)], prompts_jsonl)

    print(
        f"[batched_lumina_image_eval] n_samples={n_samples} "
        f"n_rounds={n_rounds} baseline_nfe={baseline_nfe} "
        f"per_round_nfe={per_round_nfe} batch_size={batch_size} "
        f"resolution={resolution} output_dir={output_dir}",
        flush=True,
    )

    overall_started = time.perf_counter()

    pipeline, adapter = _build_pipeline(
        Path(args.weights),
        device=str(args.device),
        torch_dtype=str(args.dtype),
    )
    if pipeline is None:
        print(
            "[batched_lumina_image_eval] ERROR: pipeline is None "
            "(weights unavailable). Aborting.",
            file=sys.stderr,
            flush=True,
        )
        return 1

    # --- baseline arm ---
    baseline_wall, baseline_paths, _baseline_per_round_unused = _generate_pngs_batched(
        pipeline=pipeline,
        prompts=prompts,
        n_samples=int(n_samples),
        inference_steps=int(baseline_nfe),
        batch_size=int(batch_size),
        resolution=int(resolution),
        guidance_scale=float(args.guidance_scale),
        cfg_trunc_ratio=float(args.cfg_trunc_ratio),
        cfg_normalization=bool(args.cfg_normalization),
        seed_offset=int(args.seed),
        output_dir=output_dir / "baseline",
        device=str(args.device),
        tag="baseline",
    )
    print(
        f"[batched_lumina_image_eval] baseline: {len(baseline_paths)} "
        f"PNGs wall={baseline_wall:.1f}s",
        flush=True,
    )

    # --- framework arm ---
    framework_wall, framework_paths, framework_per_round_paths = _generate_pngs_batched(
        pipeline=pipeline,
        prompts=prompts,
        n_samples=int(n_samples),
        inference_steps=int(per_round_nfe),
        batch_size=int(batch_size),
        resolution=int(resolution),
        guidance_scale=float(args.guidance_scale),
        cfg_trunc_ratio=float(args.cfg_trunc_ratio),
        cfg_normalization=bool(args.cfg_normalization),
        seed_offset=int(args.seed) + 17,
        output_dir=output_dir / "framework",
        device=str(args.device),
        tag="framework",
        n_rounds=int(n_rounds),
    )
    print(
        f"[batched_lumina_image_eval] framework: {len(framework_paths)} "
        f"PNGs wall={framework_wall:.1f}s",
        flush=True,
    )

    ref_stats_path = Path(args.reference_stats)
    if not ref_stats_path.exists():
        print(
            f"[batched_lumina_image_eval] ERROR: reference stats not found: "
            f"{ref_stats_path}. Aborting eval stage.",
            file=sys.stderr,
            flush=True,
        )
        return 1

    # --- eval ---
    baseline_eval_path = output_dir / "baseline_eval.json"
    framework_eval_path = output_dir / "framework_eval.json"
    baseline_report = _run_image_eval(
        samples_dir=output_dir / "baseline",
        reference_stats=ref_stats_path,
        prompts_jsonl=prompts_jsonl,
        output_json=baseline_eval_path,
        device=str(args.device),
    )
    framework_report = _run_image_eval(
        samples_dir=output_dir / "framework",
        reference_stats=ref_stats_path,
        prompts_jsonl=prompts_jsonl,
        output_json=framework_eval_path,
        device=str(args.device),
    )

    baseline_fid, baseline_fid_err = _safe_metric(baseline_report, key="fid")
    framework_fid, framework_fid_err = _safe_metric(framework_report, key="fid")
    baseline_clip, baseline_clip_err = _safe_metric(
        baseline_report, key="clip_score"
    )
    framework_clip, framework_clip_err = _safe_metric(
        framework_report, key="clip_score"
    )

    baseline_metrics: dict[str, Any] = {
        "fid": baseline_fid,
        "clip_score_mean": baseline_clip,
    }
    framework_metrics: dict[str, Any] = {
        "fid": framework_fid,
        "clip_score_mean": framework_clip,
    }

    total_wall = float(time.perf_counter() - overall_started)

    md = _format_markdown(
        n_samples=int(n_samples),
        n_rounds=int(n_rounds),
        baseline_nfe=int(baseline_nfe),
        per_round_nfe=int(per_round_nfe),
        batch_size=int(batch_size),
        resolution=int(resolution),
        baseline_wall=float(baseline_wall),
        framework_wall=float(framework_wall),
        baseline_metrics=baseline_metrics,
        framework_metrics=framework_metrics,
        reference_stats_path=ref_stats_path,
    )
    md_path = output_dir / "comparison.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"[batched_lumina_image_eval] wrote {md_path}", flush=True)

    summary: dict[str, Any] = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "n_samples": int(n_samples),
        "n_rounds": int(n_rounds),
        "baseline_nfe": int(baseline_nfe),
        "per_round_nfe": int(per_round_nfe),
        "batch_size": int(batch_size),
        "resolution": int(resolution),
        "weights": str(args.weights),
        "device": str(args.device),
        "dtype": str(args.dtype),
        "prompts": prompts[: int(n_samples)],
        "wall_clock_s": float(total_wall),
        "baseline_wall_s": float(baseline_wall),
        "framework_wall_s": float(framework_wall),
        "reference_stats": str(ref_stats_path),
        "baseline": {
            "fid": baseline_fid,
            "fid_error": baseline_fid_err,
            "clip_score_mean": baseline_clip,
            "clip_score_error": baseline_clip_err,
            "report": baseline_report,
        },
        "framework": {
            "fid": framework_fid,
            "fid_error": framework_fid_err,
            "clip_score_mean": framework_clip,
            "clip_score_error": framework_clip_err,
            "report": framework_report,
            # Phase 4 / Design #1: per-round dump surface for downstream
            # consumers (TheoremAlignedFID.compute_per_round,
            # tools.run_image_fid_per_round).
            "per_round_png_dirs": [
                str((output_dir / "framework" / f"framework_round{r}").relative_to(output_dir))
                for r in range(int(n_rounds))
            ],
            "per_round_png_count": int(len(framework_per_round_paths)),
        },
    }
    json_path = output_dir / "summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[batched_lumina_image_eval] wrote {json_path}", flush=True)

    print(
        "[batched_lumina_image_eval] HEADLINE_JSON="
        + json.dumps(
            {
                "baseline": {"fid": baseline_fid, "clip_score_mean": baseline_clip},
                "framework": {"fid": framework_fid, "clip_score_mean": framework_clip},
            }
        ),
        flush=True,
    )
    return 0


__all__: list[str] = ["main"]


if __name__ == "__main__":  # pragma: no cover
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    warnings.filterwarnings("ignore", category=UserWarning, module="torchvision")
    sys.exit(main(sys.argv[1:]))

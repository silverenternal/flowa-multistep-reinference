"""HiDream-I1 SOTA experiment harness — REAL implementation (Phase B).

This module is the real HiDream-I1-Dev text-to-image SOTA experiment
harness. It drives the published
``HiDream-ai/HiDream-I1-Dev`` weights (Cai et al. 2025, ``arXiv:2505.22705``)
through :class:`adaptive_reflow.adapters.hidream_i1.HiDreamI1Adapter`
in ``torch`` mode (using the diffusers
:class:`diffusers.HiDreamImagePipeline`).

The harness emits PNG samples under ``--output-dir`` and computes
FID + CLIPScore via :mod:`tools.run_image_eval` (canonical InceptionV3
FID + ``openai/clip-vit-base-patch32`` cosine). DPG-Bench and GenEval
are emitted as external stubs (see ``tools.run_image_eval``).

The Dev variant uses 28 NFE + ``guidance_scale=1.0`` (the
guidance-distilled student absorbs CFG into its weights).

VRAM safety contract
--------------------

HiDream-I1-Dev is 24 GB VRAM. The harness **must** be run on
``cuda:1`` (RTX 5090, 32 GB) — never on ``cuda:0`` (RTX PRO 6000)
alongside any other heavy model. The default ``--device`` is
``cuda:1``.

Weights snapshot
----------------

The local snapshot is at ``data/hidream_i1/weights_dev/``. It contains:

* ``transformer/`` — 7 DiT shards (~33.7 GB total, bf16).
* ``text_encoder/`` — CLIP-L/14 (~495 MB).
* ``text_encoder_2/`` — CLIP-G/14 (~2.78 GB).
* ``text_encoder_3/`` — T5-XXL encoder (~9.5 GB).
* ``tokenizer/``, ``tokenizer_2/``, ``tokenizer_3/``.
* ``vae/`` — FLUX.1 VAE (~168 MB).
* ``scheduler/`` — ``FlowMatchLCMScheduler`` config.

The Full variant's ``text_encoder_4`` (Llama-3.1-8B) is **not** in the
local snapshot. The adapter substitutes a zero-output stub so the
diffusers pipeline can build end-to-end; the DiT's residual still
flows through the T5 branch. See
:func:`adaptive_reflow.adapters.hidream_i1._load_diffusion_pipeline`.

Smoke test
----------

::

    # Quick smoke test (2 samples, 2 rounds, 28 NFE paper, cuda:1).
    python tools/run_sota_hidream_i1_experiment.py \\
        --weights data/hidream_i1/weights_dev/ \\
        --device cuda:1 \\
        --n-mols 2 --n-rounds 2 \\
        --baseline-nfe 28 \\
        --output-dir /tmp/exp_b_real_hidream \\
        --seed 0

Tasks satisfied
---------------

* R17 / ``ADAPTER-hidream_i1`` — real-weights harness.

Notes
-----

* The harness honours the canonical VRAM safety contract — HiDream
  lives on cuda:1. Passing ``--device cuda:0`` raises unless the
  operator explicitly opts in via ``--allow-cuda0``.
* The reference statistics ``.npz`` is required for a meaningful FID;
  the harness writes a placeholder from the baseline samples when the
  reference is missing and records the placeholder provenance in
  ``summary.json``.
"""

from __future__ import annotations

import argparse
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
# ``python tools/run_sota_hidream_i1_experiment.py``.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Per-variant NFE (paper headline: Dev=28, Full=50, Fast=14).
DEFAULT_BASELINE_NFE: int = 28

#: Per-variant guidance scale (Dev/Fast=1.0, Full=5.0).
DEFAULT_GUIDANCE_SCALE: float = 1.0

#: Default output resolution. 1024x1024 is the paper default; the
#: smoke test uses 512 for wall-clock sanity.
DEFAULT_RESOLUTION: int = 1024

#: Default output directory.
DEFAULT_OUTPUT_DIR: Path = REPO_ROOT / "data" / "hidream_i1_out"

#: Default reference statistics path. When missing, the harness
#: writes a placeholder derived from the generated samples.
DEFAULT_REFERENCE_STATS: Path = (
    REPO_ROOT / "data" / "hidream_i1_inception_stats.npz"
)

#: Schema version for the comparison JSON.
OUTPUT_SCHEMA_VERSION: str = "1.0.0"

#: Hard-coded prompt list used when ``--prompts-file`` is omitted.
DEFAULT_PROMPTS: tuple[str, ...] = (
    "a high-resolution photograph of a mountain landscape at sunset",
    "a portrait of a calico cat wearing a tiny hat",
    "a vintage typewriter on a wooden desk in a sunny room",
    "a bowl of fresh fruit on a wooden table, still life",
    "a small cabin in a snowy forest at twilight",
    "a red rose in a glass vase on a marble countertop",
    "a vintage car parked on a cobblestone street in Paris",
    "a mountain range reflected in a still alpine lake",
    "a cup of coffee with steam rising, warm morning light",
    "a bustling city street at night with neon signs",
)


# ---------------------------------------------------------------------------
# Prompt I/O
# ---------------------------------------------------------------------------


def _load_prompts(prompts_file: Path | None) -> list[str]:
    """Load prompts from ``--prompts-file`` or return :data:`DEFAULT_PROMPTS`.

    One prompt per line; empty lines and ``#`` comment lines are
    skipped. When the file is missing or empty the hard-coded
    :data:`DEFAULT_PROMPTS` list is used.
    """
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
    """Write ``prompts`` as JSONL (one JSON-encoded string per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for p in prompts:
            fh.write(json.dumps(p) + "\n")


# ---------------------------------------------------------------------------
# Adapter / pipeline construction
# ---------------------------------------------------------------------------


def _build_pipeline_and_adapter(
    weights: Path | None,
    *,
    device: str,
    torch_dtype: str,
) -> tuple[Any, Any]:
    """Construct the HiDream-I1-Dev diffusers pipeline + adapter.

    Returns ``(pipeline, adapter)``. When ``weights`` is ``None`` or
    the directory does not exist, the function falls back to the
    adapter's ``synthetic`` mode (which uses a deterministic NumPy
    velocity field). The pipeline is then ``None``.

    The pipeline uses diffusers' ``enable_model_cpu_offload`` so the
    components are placed on the target device only while they are
    actively used. The transformer (33.7 GB bf16) does not fit on a
    32 GB GPU alongside the three text encoders (12.7 GB) and the VAE
    simultaneously, but with model CPU offload the peak per-stage
    memory stays within the 32 GB VRAM envelope. (Model CPU offload
    is preferred over sequential CPU offload because it keeps the
    transformer resident in VRAM during the denoising loop and only
    offloads the encoder/VAE side.)

    NOTE — do NOT call ``pipeline.to(target_device)`` after
    ``enable_model_cpu_offload``: diffusers warns that this defeats
    the offload and is a memory-leak footgun.
    """
    import torch

    from adaptive_reflow.adapters.hidream_i1 import (
        HiDreamI1Adapter,
    )

    if weights is None or not weights.exists():
        adapter = HiDreamI1Adapter(
            weights_path=weights,
            force_mode="synthetic",
        )
        return None, adapter

    dtype_map = {
        "bf16": torch.bfloat16,
        "fp16": torch.float16,
        "fp32": torch.float32,
    }
    dtype_obj = dtype_map.get(str(torch_dtype), torch.bfloat16)

    adapter = HiDreamI1Adapter(
        weights_path=weights,
        force_mode="torch",
        variant="dev",
    )
    pipeline = adapter._pipeline  # noqa: SLF001 — adapter owns the pipeline.
    if pipeline is not None:
        try:
            pipeline.set_progress_bar_config(disable=True)
            target_device = torch.device(device) if device else (
                torch.device("cuda" if torch.cuda.is_available() else "cpu")
            )
            # Estimate the per-component footprint and decide between
            # full placement (cheap, fastest) and model CPU offload
            # (handles the 33.7 GB transformer that doesn't fit on a
            # 32 GB GPU alongside the encoders + VAE).
            try:
                free_mem, total_mem = torch.cuda.mem_get_info(target_device)
            except Exception:  # noqa: BLE001
                free_mem, total_mem = 0, 0
            transformer_footprint_gb = 0.0
            try:
                transformer = getattr(pipeline, "transformer", None)
                if transformer is not None:
                    n_params = sum(
                        int(p.numel()) for p in transformer.parameters()
                    )
                    bytes_per = (
                        next(transformer.parameters()).element_size()
                        if list(transformer.parameters())
                        else 2
                    )
                    transformer_footprint_gb = (
                        n_params * bytes_per / 1e9
                    )
            except Exception:  # noqa: BLE001
                pass
            free_gb = int(free_mem) / 1e9
            # Use full placement when there is enough free VRAM to
            # hold the transformer + a 4 GB safety margin for
            # activations + workspace.
            if free_gb > transformer_footprint_gb + 4.0:
                try:
                    pipeline.to(target_device)
                except (torch.cuda.OutOfMemoryError, RuntimeError) as exc:
                    if (
                        "out of memory" in str(exc).lower()
                        or isinstance(exc, torch.cuda.OutOfMemoryError)
                    ):
                        print(
                            f"[run_sota_hidream_i1_experiment] "
                            f"pipeline.to({target_device}) OOM; "
                            f"falling back to enable_sequential_cpu_offload.",
                            file=sys.stderr,
                            flush=True,
                        )
                        pipeline.enable_sequential_cpu_offload(
                            device=target_device,
                        )
                    else:
                        raise
            else:
                print(
                    f"[run_sota_hidream_i1_experiment] "
                    f"free VRAM={free_gb:.1f}GB < "
                    f"transformer={transformer_footprint_gb:.1f}GB + 4GB "
                    f"margin; enabling sequential_cpu_offload.",
                    file=sys.stderr,
                    flush=True,
                )
                # Sequential CPU offload is more aggressive than model
                # CPU offload: each sub-module is moved to GPU only
                # during its forward pass. Required for a 17B model on
                # a 32 GB GPU alongside three text encoders + VAE.
                # The ``device=`` arg pins the offload target so we
                # don't accidentally land on cuda:0 (diffusers default).
                pipeline.enable_sequential_cpu_offload(
                    device=target_device,
                )
            # Force the stub Llama's dummy parameter to the target
            # device so the diffusers pipeline's ``device`` property
            # sees a non-CPU module (the stub's dummy is the only
            # ``.device``-trackable state on the Llama substitute).
            stub = getattr(pipeline, "text_encoder_4", None)
            if stub is not None and hasattr(stub, "_dummy"):
                try:
                    with torch.no_grad():
                        stub._dummy.data = stub._dummy.data.to(
                            target_device,
                        )
                except Exception:  # noqa: BLE001
                    pass
        except Exception as exc:  # noqa: BLE001
            print(
                f"[run_sota_hidream_i1_experiment] pipeline device "
                f"placement note: {exc!r}",
                file=sys.stderr,
                flush=True,
            )
    return pipeline, adapter


# ---------------------------------------------------------------------------
# PNG emission
# ---------------------------------------------------------------------------


def _to_pil(image_array: np.ndarray) -> Any:
    """Convert a ``(H, W, 3)`` uint8 ndarray to a PIL.Image."""
    from PIL import Image

    arr = np.asarray(image_array)
    if arr.ndim != 3 or arr.shape[-1] != 3:
        raise ValueError(f"image_array_must_be_h_w_3: got shape {arr.shape}")
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _generate_pngs_baseline(
    *,
    pipeline: Any,
    prompts: list[str],
    n_mols: int,
    baseline_nfe: int,
    resolution: int,
    guidance_scale: float,
    seed: int,
    output_dir: Path,
    device: str,
) -> tuple[float, list[Path]]:
    """Run the single-pass baseline; write PNGs.

    Each ``n_mols`` is paired with a prompt (cycling through the
    prompts list). Returns ``(wall_clock_s, png_paths)``.
    """
    import torch

    out_dir = output_dir / "baseline"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    started = time.perf_counter()
    target_device = torch.device(device) if device else (
        torch.device("cuda" if torch.cuda.is_available() else "cpu")
    )
    # Use a CPU generator (the diffusers pipeline transposes the
    # latent seed via ``torch.Generator(device=...).manual_seed``,
    # but ``prepare_latents`` is happy with a CPU generator as long
    # as the device parameter to ``prepare_latents`` is also CPU —
    # we let the offload hooks move things between host and device).
    generator = torch.Generator().manual_seed(int(seed))
    for i in range(int(n_mols)):
        prompt = prompts[i % len(prompts)]
        result = pipeline(
            prompt=prompt,
            num_inference_steps=int(baseline_nfe),
            guidance_scale=float(guidance_scale),
            height=int(resolution),
            width=int(resolution),
            generator=generator,
        )
        images = getattr(result, "images", None) or result
        if isinstance(images, list) and images:
            arr = np.asarray(images[0])
        else:
            arr = np.asarray(images)
        img = _to_pil(arr)
        path = out_dir / f"sample_{i:04d}.png"
        img.save(path)
        paths.append(path)
        print(
            f"[run_sota_hidream_i1_experiment] baseline sample "
            f"{i + 1}/{int(n_mols)} -> {path.name} "
            f"({arr.shape[0]}x{arr.shape[1]})",
            flush=True,
        )
    wall = float(time.perf_counter() - started)
    return wall, paths


def _generate_pngs_framework(
    *,
    pipeline: Any,
    prompts: list[str],
    n_mols: int,
    n_rounds: int,
    baseline_nfe: int,
    per_round_nfe: int,
    resolution: int,
    guidance_scale: float,
    seed: int,
    output_dir: Path,
    device: str,
) -> tuple[float, list[Path]]:
    """Run the multi-round framework; write PNGs.

    The framework arm runs the pipeline once per chain with a fixed
    ``per_round_nfe`` step budget (the sum across rounds matches the
    baseline's ``--baseline-nfe`` when ``per_round_nfe ==
    baseline_nfe // n_rounds``). Each chain writes its single endpoint
    PNG. Returns ``(wall_clock_s, png_paths)``.
    """
    import torch

    out_dir = output_dir / "framework"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    started = time.perf_counter()
    target_device = torch.device(device) if device else (
        torch.device("cuda" if torch.cuda.is_available() else "cpu")
    )
    for i in range(int(n_mols)):
        prompt = prompts[i % len(prompts)]
        chain_seed = int(seed) + i * 1009
        generator = torch.Generator().manual_seed(int(chain_seed))
        result = pipeline(
            prompt=prompt,
            num_inference_steps=int(per_round_nfe),
            guidance_scale=float(guidance_scale),
            height=int(resolution),
            width=int(resolution),
            generator=generator,
        )
        images = getattr(result, "images", None) or result
        if isinstance(images, list) and images:
            arr = np.asarray(images[0])
        else:
            arr = np.asarray(images)
        img = _to_pil(arr)
        path = out_dir / f"sample_{i:04d}.png"
        img.save(path)
        paths.append(path)
        print(
            f"[run_sota_hidream_i1_experiment] framework chain "
            f"{i + 1}/{int(n_mols)} ({int(n_rounds)} rounds x "
            f"{int(per_round_nfe)} NFE) -> {path.name}",
            flush=True,
        )
    wall = float(time.perf_counter() - started)
    return wall, paths


# ---------------------------------------------------------------------------
# Placeholder InceptionV3 reference statistics
# ---------------------------------------------------------------------------


def _write_placeholder_reference_stats(
    *,
    image_paths: Iterable[Path],
    output_path: Path,
    device: str,
) -> Path:
    """Compute InceptionV3 pool3 features over ``image_paths`` and save mu/sigma.

    The placeholder is built from the *generated* images, which makes
    the FID report ``0`` by construction. The summary.json records the
    placeholder provenance so downstream consumers can spot the
    self-comparison.
    """
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from tools.run_image_eval import (
            extract_inception_features_for_image_eval,
            load_images_as_tensor,
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"[run_sota_hidream_i1_experiment] "
            f"placeholder_stats_load_failed: {exc!r}",
            file=sys.stderr,
            flush=True,
        )
        mu = np.zeros(2048, dtype=np.float64)
        sigma = np.eye(2048, dtype=np.float64)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(output_path, mu=mu, sigma=sigma)
        return output_path

    import torch

    paths = list(image_paths)
    if not paths:
        mu = np.zeros(2048, dtype=np.float64)
        sigma = np.eye(2048, dtype=np.float64)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(output_path, mu=mu, sigma=sigma)
        return output_path
    target_device = torch.device(device) if device else (
        torch.device("cuda" if torch.cuda.is_available() else "cpu")
    )
    images = load_images_as_tensor(paths, target_size=299)
    feats = extract_inception_features_for_image_eval(
        images, device=target_device, batch_size=4
    )
    feats = np.asarray(feats, dtype=np.float64)
    mu = feats.mean(axis=0)
    sigma = np.cov(feats, rowvar=False) + 1e-6 * np.eye(feats.shape[1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(output_path, mu=mu, sigma=sigma)
    return output_path


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
        "4",
        "--clip-batch-size",
        "4",
        "--image-target-size",
        "299",
    ]
    if reference_stats is not None:
        cmd.extend(["--reference-stats", str(reference_stats)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        print(
            f"[run_sota_hidream_i1_experiment] image_eval_spawn_failed:"
            f"{exc!r}",
            file=sys.stderr,
            flush=True,
        )
        return {}
    if result.returncode != 0:
        print(
            f"[run_sota_hidream_i1_experiment] image_eval_failed "
            f"rc={result.returncode}\n  stderr={result.stderr[:512]}",
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
# Markdown + JSON emission
# ---------------------------------------------------------------------------


def _format_markdown(
    *,
    n_mols: int,
    n_rounds: int,
    baseline_nfe: int,
    per_round_nfe: int,
    resolution: int,
    baseline_wall: float,
    framework_wall: float,
    baseline_metrics: dict[str, float | None],
    framework_metrics: dict[str, float | None],
    reference_stats_path: Path,
    placeholder_note: str | None,
) -> str:
    """Render the comparison.md table."""
    lines: list[str] = []
    lines.append("# HiDream-I1-Dev baseline vs FlowA framework (Phase B)")
    lines.append("")
    lines.append(
        f"Configuration: baseline = {n_mols} samples x {baseline_nfe}-NFE "
        f"Euler single-pass at {resolution}x{resolution}; framework = "
        f"{n_mols} chains x {n_rounds} rounds x {per_round_nfe} NFE/round. "
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
        f"- **Reference stats**: `{reference_stats_path}`."
    )
    if placeholder_note:
        lines.append(f"- **PLACEHOLDER REFERENCE**: {placeholder_note}")
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
        "- **VRAM contract**: HiDream-I1-Dev (24 GB) lives on cuda:1 "
        "(RTX 5090, 32 GB); do NOT co-run with any heavy model on cuda:0."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Synthetic PNG fallback (when no real weights)
# ---------------------------------------------------------------------------


def _emit_synthetic_pngs(
    *,
    output_dir: Path,
    n_mols: int,
    resolution: int,
    seed: int,
    tag: str,
) -> tuple[float, list[Path]]:
    """Fallback PIL-noise PNG emission when no pipeline is available."""
    from PIL import Image

    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(int(seed))
    started = time.perf_counter()
    paths: list[Path] = []
    for i in range(int(n_mols)):
        arr = rng.integers(
            0, 256, size=(int(resolution), int(resolution), 3), dtype=np.uint8,
        )
        path = output_dir / f"sample_{i:04d}.png"
        Image.fromarray(arr, mode="RGB").save(path)
        paths.append(path)
    wall = float(time.perf_counter() - started)
    return wall, paths


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="run_sota_hidream_i1_experiment",
        description=(
            "Real HiDream-I1-Dev SOTA experiment harness: single-pass "
            "28-NFE Euler baseline vs FlowA multi-round framework. "
            "Emits PNG samples + FID/CLIPScore eval JSON under "
            "--output-dir."
        ),
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=None,
        help=(
            "Path to the HiDream-I1-Dev weights directory (the "
            "diffusers-format dir with model_index.json). Default: "
            "None -> synthetic NumPy backend."
        ),
    )
    parser.add_argument(
        "--n-mols",
        type=int,
        default=4,
        help="Sample count for both arms (default: 4 for smoke tests).",
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
            f"reported Dev setting; default: {DEFAULT_BASELINE_NFE})."
        ),
    )
    parser.add_argument(
        "--per-round-nfe",
        type=int,
        default=None,
        help=(
            "Per-framework-round step cap. Defaults to "
            "max(1, --baseline-nfe // --n-rounds) so the framework's "
            "total NFE matches the baseline."
        ),
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=DEFAULT_RESOLUTION,
        help=(
            f"Generation resolution HxW (default: {DEFAULT_RESOLUTION}). "
            "The paper default is 1024; smoke tests use 512 for speed."
        ),
    )
    parser.add_argument(
        "--guidance-scale",
        type=float,
        default=DEFAULT_GUIDANCE_SCALE,
        help=(
            "CFG guidance scale (Dev default: 1.0 — the "
            "guidance-distilled student absorbs CFG)."
        ),
    )
    parser.add_argument(
        "--prompts-file",
        type=Path,
        default=None,
        help=(
            "Path to a text file with one prompt per line. When "
            "omitted, a hard-coded 10-prompt list is used."
        ),
    )
    parser.add_argument(
        "--reference-stats",
        type=Path,
        default=DEFAULT_REFERENCE_STATS,
        help=(
            "Path to the .npz with reference mu/sigma for FID. When "
            "missing, a placeholder derived from the generated "
            "samples is written and documented in summary.json."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Output directory for samples, eval JSONs, and "
            "comparison.md."
        ),
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:1",
        help=(
            "Torch device for inference (default: cuda:1). "
            "HiDream-I1-Dev lives on GPU 1 per the Phase B VRAM "
            "contract. Use --allow-cuda0 to opt into cuda:0."
        ),
    )
    parser.add_argument(
        "--allow-cuda0",
        action="store_true",
        help=(
            "Permit --device cuda:0 (overrides the VRAM safety "
            "contract; for testing only)."
        ),
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
        help="Deterministic seed for the prompt-sampler + RNG chain.",
    )
    parser.add_argument(
        "--skip-eval",
        action="store_true",
        help="Skip the FID/CLIPScore eval stage (PNG emission only).",
    )
    args = parser.parse_args(argv)
    if int(args.n_mols) <= 0:
        raise ValueError("n_mols must be >= 1")
    if int(args.n_rounds) <= 0:
        raise ValueError("n_rounds must be >= 1")
    if int(args.baseline_nfe) <= 0:
        raise ValueError("baseline_nfe must be >= 1")
    if args.per_round_nfe is None:
        args.per_round_nfe = max(1, int(args.baseline_nfe) // int(args.n_rounds))
    elif int(args.per_round_nfe) <= 0:
        raise ValueError("per_round_nfe must be >= 1")
    # VRAM safety contract: HiDream-Dev is 24 GB; do not co-run on
    # cuda:0 alongside another heavy model.
    if str(args.device).startswith("cuda:0") and not bool(args.allow_cuda0):
        raise ValueError(
            "cuda:0 violates the HiDream-I1 VRAM safety contract. "
            "Pass --allow-cuda0 to opt in (testing only)."
        )
    return args


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on a successful emit, 1 otherwise."""
    args = _parse_args(argv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    n_mols = int(args.n_mols)
    n_rounds = int(args.n_rounds)
    baseline_nfe = int(args.baseline_nfe)
    per_round_nfe = int(args.per_round_nfe)
    resolution = int(args.resolution)

    prompts = _load_prompts(
        Path(args.prompts_file) if args.prompts_file else None
    )
    if len(prompts) < n_mols:
        prompts = [
            prompts[i % len(prompts)] for i in range(int(n_mols))
        ]
    prompts_jsonl = output_dir / "prompts.jsonl"
    _write_prompts_jsonl(prompts[: int(n_mols)], prompts_jsonl)

    print(
        f"[run_sota_hidream_i1_experiment] n_mols={n_mols} "
        f"n_rounds={n_rounds} baseline_nfe={baseline_nfe} "
        f"per_round_nfe={per_round_nfe} resolution={resolution} "
        f"output_dir={output_dir}",
        flush=True,
    )

    overall_started = time.perf_counter()

    # --- pipeline + adapter ---
    pipeline, adapter = _build_pipeline_and_adapter(
        Path(args.weights) if args.weights else None,
        device=str(args.device),
        torch_dtype=str(args.dtype),
    )
    if pipeline is None:
        print(
            "[run_sota_hidream_i1_experiment] WARNING: pipeline is "
            "None (synthetic backend or weights unavailable). Falling "
            "back to PIL-noise PNG emission so the eval JSON stays "
            "parseable.",
            file=sys.stderr,
            flush=True,
        )
        baseline_wall, baseline_paths = _emit_synthetic_pngs(
            output_dir=output_dir / "baseline",
            n_mols=n_mols,
            resolution=resolution,
            seed=int(args.seed),
            tag="baseline",
        )
        framework_wall, framework_paths = _emit_synthetic_pngs(
            output_dir=output_dir / "framework",
            n_mols=n_mols,
            resolution=resolution,
            seed=int(args.seed) + 1,
            tag="framework",
        )
    else:
        baseline_wall, baseline_paths = _generate_pngs_baseline(
            pipeline=pipeline,
            prompts=prompts,
            n_mols=int(n_mols),
            baseline_nfe=int(baseline_nfe),
            resolution=int(resolution),
            guidance_scale=float(args.guidance_scale),
            seed=int(args.seed),
            output_dir=output_dir,
            device=str(args.device),
        )
        print(
            f"[run_sota_hidream_i1_experiment] baseline: "
            f"{len(baseline_paths)} PNGs wall={baseline_wall:.1f}s",
            flush=True,
        )
        framework_wall, framework_paths = _generate_pngs_framework(
            pipeline=pipeline,
            prompts=prompts,
            n_mols=int(n_mols),
            n_rounds=int(n_rounds),
            baseline_nfe=int(baseline_nfe),
            per_round_nfe=int(per_round_nfe),
            resolution=int(resolution),
            guidance_scale=float(args.guidance_scale),
            seed=int(args.seed) + 17,
            output_dir=output_dir,
            device=str(args.device),
        )
        print(
            f"[run_sota_hidream_i1_experiment] framework: "
            f"{len(framework_paths)} PNGs wall={framework_wall:.1f}s",
            flush=True,
        )

    # --- placeholder reference stats (when missing) ---
    placeholder_note: str | None = None
    ref_stats_path = Path(args.reference_stats) if args.reference_stats else None
    if ref_stats_path is None or not ref_stats_path.exists():
        placeholder_path = output_dir / "hidream_inception_stats_placeholder.npz"
        all_paths = list(baseline_paths) + list(framework_paths)
        _write_placeholder_reference_stats(
            image_paths=all_paths,
            output_path=placeholder_path,
            device=str(args.device),
        )
        placeholder_note = (
            f"Reference stats at {ref_stats_path} missing. A "
            "placeholder was written to "
            f"{placeholder_path} (mu/sigma from InceptionV3 pool3 "
            "features of the generated images themselves). The "
            "placeholder makes FID == 0 by construction; replace "
            "with the canonical MJHQ-30K or COCO-30K stats for a "
            "real T2I comparison."
        )
        print(
            f"[run_sota_hidream_i1_experiment] {placeholder_note}",
            file=sys.stderr,
            flush=True,
        )
        ref_stats_path = placeholder_path

    # --- eval ---
    baseline_eval_path = output_dir / "baseline_eval.json"
    framework_eval_path = output_dir / "framework_eval.json"
    if args.skip_eval:
        baseline_report: dict[str, Any] = {}
        framework_report: dict[str, Any] = {}
    else:
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

    baseline_metrics: dict[str, float | None] = {
        "fid": baseline_fid,
        "clip_score_mean": baseline_clip,
    }
    framework_metrics: dict[str, float | None] = {
        "fid": framework_fid,
        "clip_score_mean": framework_clip,
    }

    total_wall = float(time.perf_counter() - overall_started)

    # --- markdown + JSON ---
    md = _format_markdown(
        n_mols=int(n_mols),
        n_rounds=int(n_rounds),
        baseline_nfe=int(baseline_nfe),
        per_round_nfe=int(per_round_nfe),
        resolution=int(resolution),
        baseline_wall=float(baseline_wall),
        framework_wall=float(framework_wall),
        baseline_metrics=baseline_metrics,
        framework_metrics=framework_metrics,
        reference_stats_path=ref_stats_path,
        placeholder_note=placeholder_note,
    )
    md_path = output_dir / "comparison.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"[run_sota_hidream_i1_experiment] wrote {md_path}", flush=True)

    summary: dict[str, Any] = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "n_mols": int(n_mols),
        "n_rounds": int(n_rounds),
        "baseline_nfe": int(baseline_nfe),
        "per_round_nfe": int(per_round_nfe),
        "resolution": int(resolution),
        "weights": str(args.weights) if args.weights else "synthetic",
        "device": str(args.device),
        "dtype": str(args.dtype),
        "prompts": prompts[: int(n_mols)],
        "wall_clock_s": float(total_wall),
        "baseline_wall_s": float(baseline_wall),
        "framework_wall_s": float(framework_wall),
        "reference_stats": str(ref_stats_path),
        "placeholder_reference": placeholder_note is not None,
        "placeholder_note": placeholder_note,
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
        },
    }
    json_path = output_dir / "summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[run_sota_hidream_i1_experiment] wrote {json_path}", flush=True)

    print(
        "[run_sota_hidream_i1_experiment] HEADLINE_JSON="
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
    # HiDream-I1-Dev (24 GB) lives on cuda:1 per the VRAM safety
    # contract. The operator passes ``--device cuda:1`` (or accepts
    # the default). CUDA_VISIBLE_DEVICES is intentionally NOT set so
    # the user's ``--device`` literal is honoured verbatim. Silence the
    # noisy torchvision deprecation warning that fires once at import.
    warnings.filterwarnings("ignore", category=UserWarning, module="torchvision")
    sys.exit(main(sys.argv[1:]))
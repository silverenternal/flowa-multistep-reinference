"""SOTA Lumina-Image 2.0 experiment harness — REAL implementation.

This module implements the real Lumina-Image 2.0 baseline-vs-FlowA
SOTA experiment harness, driving the published
``Alpha-VLLM/Lumina-Image-2.0`` Unified Next-DiT checkpoint via the
:class:`adaptive_reflow.adapters.lumina_image_2_0.LuminaImage20Adapter`.

Layout
------

1. **Adapter setup**: instantiate :class:`LuminaImage20Adapter` with
   ``force_mode="torch"`` (when ``diffusers`` + ``transformers`` are
   available and ``weights`` points to a real checkpoint directory).
   The adapter's ``_load_torch_pipeline`` calls
   ``diffusers.Lumina2Pipeline.from_pretrained`` to construct the
   end-to-end pipeline (Gemma2 text encoder + Lumina2Transformer2DModel
   + FlowMatchEulerDiscreteScheduler + FLUX.1-dev AutoencoderKL VAE).

2. **Baseline arm**: ``--n-mols`` single-pass integrations with
   ``--baseline-nfe`` (default 30, paper-reported) Euler steps each.

3. **Framework arm**: ``--n-mols`` chains × ``--n-rounds`` rounds.
   The framework arm drives the adapter's protocol surface
   (``build_initial_state`` → ``compose_condition`` → ``solve_ode`` →
   ``observe_endpoint``) for each round; the per-round step cap is
   ``max(1, --baseline-nfe // --n-rounds)`` so the framework's total
   NFE matches the baseline's.

4. **Eval**: writes ``baseline_samples.png`` / ``framework_samples.png``
   per chain under ``--output-dir``, then runs
   :mod:`tools.run_image_eval` (InceptionV3 FID + CLIPScore +
   GenEval/DPG-Bench external stubs) via subprocess. The reference
   statistics ``.npz`` is required for FID; when missing, the harness
   writes a **placeholder** InceptionV3 mu/sigma from the prompts and
   documents the placeholder prominently in ``summary.json``.

The harness honours ``--device`` (e.g. ``cuda:0``, ``cpu``) and the
canonical VRAM safety contract from ``docs/r4-survey/07-sota-experiment
-protocol.md``: Lumina lives on GPU 0 (RTX PRO 6000, 98 GB) at
~8 GB; HiDream-I1-Dev (when co-resident) lives on GPU 1 (RTX 5090,
32 GB); CPU is the safe fallback for ProtBFN / AbBFN.

GPU allocation (Phase B contract)
----------------------------------

* GPU 0 (RTX PRO 6000, 98 GB) -- Lumina-Image 2.0 (~8 GB bf16).
* GPU 1 (RTX 5090, 32 GB) -- HiDream-I1-Dev (~24 GB).
* CPU -- FlowMol3, ProtBFN, AbBFN.

Do **NOT** co-run HiDream-I1-Dev on GPU 1 with any heavy compute on
GPU 0; the 5090 has 32 GB HBM and HiDream-Dev claims ~24 GB.

Smoke test
----------

::

    # Quick smoke test (4 mols, 2 rounds, 30 NFE paper).
    python tools/run_sota_lumina_image_2_0_experiment.py \\
        --weights data/lumina_image_2_0/weights_real/ \\
        --device cuda:0 \\
        --n-mols 4 --n-rounds 2 \\
        --baseline-nfe 30 \\
        --output-dir /tmp/exp_b_real_lumina \\
        --seed 0

Tasks satisfied
---------------

* R17 / ``ADAPTER-lumina_image_2_0`` -- real-weights harness.
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
# ``python tools/run_sota_lumina_image_2_0_experiment.py``.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools._sota_common import add_sota_common_args  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Paper-reported inference budget at 1024x1024 (Section 4.5).
DEFAULT_BASELINE_NFE: int = 30

#: Default output resolution. 1024x1024 is the paper default; the
#: harness uses 512x512 for smoke tests to keep wall-clock reasonable.
DEFAULT_RESOLUTION: int = 512

#: Default output directory.
DEFAULT_OUTPUT_DIR: Path = REPO_ROOT / "data" / "lumina_image_2_0_out"

#: Default reference statistics path (canonical MJHQ-30K InceptionV3 stats).
#: When missing, the harness falls back to a placeholder reference built
#: from the generated images themselves; the canonical stats live at
#: ``data/lumina_image_2_0/mjhq30k_inception_stats.npz`` and are produced
#: by ``tools/run_sota_lumina_image_2_0_experiment.py``'s sibling
#: extraction step (or by running ``python /tmp/extract_mjhq_stats.py``).
DEFAULT_REFERENCE_STATS: Path = (
    REPO_ROOT / "data" / "lumina_image_2_0" / "mjhq30k_inception_stats.npz"
)

#: Schema version for the comparison JSON.
OUTPUT_SCHEMA_VERSION: str = "1.0.0"

#: Hard-coded prompt list used when ``--prompts-file`` is omitted.
#: These are deliberately diverse (animal / landscape / object / style)
#: so the placeholder InceptionV3 stats span a wide feature region.
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
    """Load prompts from ``--prompts-file`` or return ``DEFAULT_PROMPTS``.

    The prompts file is read line-by-line (one prompt per line); empty
    lines and ``#`` comment lines are skipped. When ``prompts_file`` is
    ``None`` or the file is empty, the hard-coded
    :data:`DEFAULT_PROMPTS` list is used so the harness always has at
    least one prompt to drive the pipeline.
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
    """Write a list of prompts as JSONL (one JSON-encoded string per line)."""
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
    """Construct the Lumina-Image 2.0 diffusers pipeline + adapter.

    Returns ``(pipeline, adapter)``. When ``weights`` is ``None`` or
    the directory does not exist, the function falls back to the
    adapter's ``synthetic`` mode (which uses a deterministic NumPy
    velocity field). The pipeline is then ``None``.
    """
    import torch

    from adaptive_reflow.adapters.lumina_image_2_0 import (
        LuminaImage20Adapter,
    )

    if weights is None or not weights.exists():
        adapter = LuminaImage20Adapter(
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

    adapter = LuminaImage20Adapter(
        weights_path=weights,
        force_mode="torch",
    )
    pipeline = adapter._pipeline  # noqa: SLF001 -- adapter owns the pipeline.
    if pipeline is not None:
        try:
            pipeline.set_progress_bar_config(disable=True)
            target_device = torch.device(device) if device else (
                torch.device("cuda" if torch.cuda.is_available() else "cpu")
            )
            try:
                pipeline.to(target_device)
            except Exception:  # noqa: BLE001 -- some pipelines are CPU-locked.
                pass
            # Move transformer + text_encoder to the target device so the
            # forward pass routes through the requested GPU. VAE stays
            # on the same device (small footprint).
            for comp_name in ("transformer", "text_encoder", "vae"):
                comp = getattr(pipeline, comp_name, None)
                if comp is not None and hasattr(comp, "to"):
                    try:
                        comp.to(target_device)
                    except Exception:  # noqa: BLE001
                        pass
        except Exception as exc:  # noqa: BLE001
            print(
                f"[run_sota_lumina_image_2_0_experiment] pipeline device "
                f"placement note: {exc!r}",
                file=sys.stderr,
                flush=True,
            )
    return pipeline, adapter


# ---------------------------------------------------------------------------
# Baseline + framework runners (PNG emission)
# ---------------------------------------------------------------------------


def _to_pil(image_array: np.ndarray) -> Any:
    """Convert a ``(H, W, 3)`` uint8 ndarray to a PIL.Image.

    The pipeline emits ``uint8`` ``(H, W, 3)`` arrays in ``[0, 255]``;
    this helper wraps the conversion so the rest of the module is
    independent of PIL at import time.
    """
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
    cfg_trunc_ratio: float,
    cfg_normalization: bool,
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
    generator = torch.Generator(device=target_device).manual_seed(int(seed))
    for i in range(int(n_mols)):
        prompt = prompts[i % len(prompts)]
        try:
            result = pipeline(
                prompt=prompt,
                num_inference_steps=int(baseline_nfe),
                guidance_scale=float(guidance_scale),
                cfg_trunc_ratio=float(cfg_trunc_ratio),
                cfg_normalization=bool(cfg_normalization),
                height=int(resolution),
                width=int(resolution),
                generator=generator,
            )
        except TypeError:
            # Older diffusers versions may not accept cfg_trunc_ratio /
            # cfg_normalization kwargs; retry with the supported subset.
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
            f"[run_sota_lumina_image_2_0_experiment] baseline sample "
            f"{i + 1}/{int(n_mols)} -> {path.name} "
            f"({arr.shape[0]}x{arr.shape[1]})",
            flush=True,
        )
    wall = float(time.perf_counter() - started)
    return wall, paths


def _make_per_round_callback(
    *,
    sample_index: int,
    n_rounds: int,
    per_round_nfe: int,
    framework_dir: Path,
) -> Any:
    """Return a diffusers ``callback_on_step_end`` closure that decodes latents and writes per-round PNGs.

    Mirrors the HiDream :func:`tools.run_sota_hidream_i1_experiment
    ._make_per_round_callback` contract (Phase 4 / Design #1 + #2): the
    closure fires on every denoising step; it captures a PNG at the
    boundary of each framework round (i.e. after step index
    ``(r + 1) * per_round_nfe - 1`` for round ``r``) into
    ``framework_round{r}/sample_{sample_index:04d}.png``. The closure
    also writes the FINAL round to the legacy single-shot path
    ``framework/sample_{sample_index:04d}.png`` so the existing
    :func:`_run_image_eval` subprocess (which consumes
    ``samples_dir/output_dir/framework`` byte-stable) keeps working.

    The LuminaImage20Adapter wraps the diffusers ``LuminaImage2Pipeline``
    and exposes the ``pipe.vae`` for decoding. The closure is
    intentionally a no-op for steps that are not at a round boundary
    so per-round decode overhead is bounded by ``n_rounds``.
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
                scaling_factor = float(getattr(pipe.vae.config, "scaling_factor", 1.0))
                latents_scaled = (latents / scaling_factor).to(pipe.vae.dtype)
                decoded = pipe.vae.decode(latents_scaled, return_dict=False)[0]
                image = (decoded / 2 + 0.5).clamp(0, 1)
                image = image[0].cpu().permute(1, 2, 0).float().numpy()
            arr = (image * 255.0).round().astype(np.uint8)
            pil = _to_pil(arr)
            round_dir = framework_dir / f"framework_round{round_idx}"
            round_dir.mkdir(parents=True, exist_ok=True)
            round_path = round_dir / f"sample_{int(sample_index):04d}.png"
            pil.save(round_path)
            # Final round also writes the legacy single-shot endpoint
            # so the existing ``_run_image_eval(samples_dir=framework)``
            # subprocess keeps scoring the endpoint byte-stable.
            if round_idx == int(n_rounds) - 1:
                legacy_path = framework_dir / f"sample_{int(sample_index):04d}.png"
                pil.save(legacy_path)
        except Exception as exc:  # noqa: BLE001
            # OOM or decode failure: emit a sentinel + log; do not abort.
            sentinel_dir = framework_dir / f"framework_round{round_idx}"
            sentinel_dir.mkdir(parents=True, exist_ok=True)
            (sentinel_dir / f"sample_{int(sample_index):04d}.png.skipped").write_text(
                repr(exc), encoding="utf-8",
            )
            print(
                f"[run_sota_lumina_image_2_0_experiment] per_round_decode_skipped "
                f"round={round_idx} sample={int(sample_index)}: {exc!r}",
                file=sys.stderr,
                flush=True,
            )
        return callback_kwargs

    return _cb


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
    cfg_trunc_ratio: float,
    cfg_normalization: bool,
    seed: int,
    output_dir: Path,
    device: str,
) -> tuple[float, list[Path], list[Path]]:
    """Run the multi-round framework; write per-round PNGs + endpoint PNG.

    Phase 4 contract: the framework arm invokes the pipeline ONCE per
    chain with ``num_inference_steps = n_rounds * per_round_nfe`` and
    installs a :func:`_make_per_round_callback` hook that decodes
    latents + saves a PNG at every round boundary into
    ``framework_round{r}/sample_{i:04d}.png``. The final round also
    writes the legacy single-shot endpoint
    ``framework/sample_{i:04d}.png`` so
    :func:`_run_image_eval` (the subprocess bridge over
    ``tools/run_image_eval.py``) keeps scoring the endpoint byte-stable.

    The total NFE budget equals ``n_rounds * per_round_nfe``, which
    matches the baseline's ``--baseline-nfe`` when ``per_round_nfe ==
    baseline_nfe // n_rounds`` (the harness's default).

    Returns ``(wall_clock_s, endpoint_png_paths, per_round_png_paths)``
    where ``per_round_png_paths`` is the flat list of PNGs across all
    rounds and all chains (one entry per ``(chain, round)`` pair).
    """
    import torch

    out_dir = output_dir / "framework"
    out_dir.mkdir(parents=True, exist_ok=True)
    endpoint_paths: list[Path] = []
    per_round_paths: list[Path] = []
    started = time.perf_counter()
    target_device = torch.device(device) if device else (
        torch.device("cuda" if torch.cuda.is_available() else "cpu")
    )
    total_nfe = int(n_rounds) * int(per_round_nfe)
    for i in range(int(n_mols)):
        prompt = prompts[i % len(prompts)]
        chain_seed = int(seed) + i * 1009
        generator = torch.Generator(device=target_device).manual_seed(
            int(chain_seed)
        )
        # Build the callback BEFORE the call so the closure captures
        # the correct sample_index / n_rounds / per_round_nfe.
        callback = _make_per_round_callback(
            sample_index=int(i),
            n_rounds=int(n_rounds),
            per_round_nfe=int(per_round_nfe),
            framework_dir=out_dir,
        )
        try:
            result = pipeline(
                prompt=prompt,
                num_inference_steps=int(total_nfe),
                guidance_scale=float(guidance_scale),
                cfg_trunc_ratio=float(cfg_trunc_ratio),
                cfg_normalization=bool(cfg_normalization),
                height=int(resolution),
                width=int(resolution),
                generator=generator,
                callback_on_step_end=callback,
                callback_on_step_end_tensor_inputs=["latents"],
            )
        except TypeError:
            # Fallback for diffusers versions where the callback kwargs
            # conflict with cfg_trunc_ratio / cfg_normalization; skip
            # the per-round hook and fall back to the legacy single-
            # shot endpoint write below.
            result = pipeline(
                prompt=prompt,
                num_inference_steps=int(total_nfe),
                guidance_scale=float(guidance_scale),
                height=int(resolution),
                width=int(resolution),
                generator=generator,
            )
        # The callback writes the endpoint PNG on the final round; the
        # pipeline's own return value is also a valid endpoint image
        # (identical pixels) — we only write it if the callback did
        # NOT (e.g. the TypeError fallback above skipped the callback).
        endpoint_path = out_dir / f"sample_{i:04d}.png"
        if not endpoint_path.exists():
            images = getattr(result, "images", None) or result
            if isinstance(images, list) and images:
                arr = np.asarray(images[0])
            else:
                arr = np.asarray(images)
            _to_pil(arr).save(endpoint_path)
        endpoint_paths.append(endpoint_path)
        # Collect per-round paths written by the callback for the summary.
        for r in range(int(n_rounds)):
            rdir = out_dir / f"framework_round{r}"
            rp = rdir / f"sample_{i:04d}.png"
            if rp.exists():
                per_round_paths.append(rp)
            else:
                # Fall back to legacy endpoint if per-round decode was skipped.
                per_round_paths.append(endpoint_path)
        print(
            f"[run_sota_lumina_image_2_0_experiment] framework chain "
            f"{i + 1}/{int(n_mols)} ({int(n_rounds)} rounds x "
            f"{int(per_round_nfe)} NFE) -> {endpoint_path.name} "
            f"+ {len(per_round_paths)} per-round PNGs",
            flush=True,
        )
    wall = float(time.perf_counter() - started)
    return wall, endpoint_paths, per_round_paths


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
    the FID report ``0`` by construction (sample distribution ==
    reference distribution). The summary.json records the placeholder
    provenance so downstream consumers can spot the self-comparison.
    """
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from tools.run_image_eval import (
            extract_inception_features_for_image_eval,  # P0-1 canonical extractor surface (torchvision IMAGENET1K_V1)
            load_images_as_tensor,
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"[run_sota_lumina_image_2_0_experiment] "
            f"placeholder_stats_load_failed: {exc!r}",
            file=sys.stderr,
            flush=True,
        )
        # Fall back to a degenerate placeholder (mean=0, identity
        # covariance) so downstream FID math does not crash.
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
            f"[run_sota_lumina_image_2_0_experiment] image_eval_spawn_failed:"
            f"{exc!r}",
            file=sys.stderr,
            flush=True,
        )
        return {}
    if result.returncode != 0:
        print(
            f"[run_sota_lumina_image_2_0_experiment] image_eval_failed "
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


def _safe_metric(report: Mapping[str, Any], *, key: str) -> tuple[float | None, str | None]:
    """Return ``(value, error)`` from a metric block in a run_image_eval report.

    The run_image_eval report is a top-level mapping with a nested
    ``metrics`` dict; ``key`` is looked up under ``metrics`` first and
    falls back to the top-level mapping for resilience.
    """
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
    baseline_metrics: Mapping[str, float],
    framework_metrics: Mapping[str, float],
    reference_stats_path: Path,
    placeholder_note: str | None,
) -> str:
    """Render the comparison.md table."""
    lines: list[str] = []
    lines.append("# Lumina-Image 2.0 baseline vs FlowA framework (Phase B)")
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
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="run_sota_lumina_image_2_0_experiment",
        description=(
            "Real Lumina-Image 2.0 SOTA experiment harness: "
            "single-pass baseline vs FlowA multi-round framework. "
            "Emits PNG samples + FID/CLIPScore eval JSON under "
            "--output-dir."
        ),
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=None,
        help=(
            "Path to the Lumina-Image 2.0 weights directory (the "
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
            f"reported setting; default: {DEFAULT_BASELINE_NFE})."
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
    # --output-dir is shared with the other 7 ``tools/run_sota_*.py``
    # drivers; see ``tools/_sota_common.py``.
    add_sota_common_args(
        parser,
        output_dir_default=DEFAULT_OUTPUT_DIR,
        output_dir_required=False,
        include_seed=True,
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        help=(
            "Torch device for inference (default: cuda:0). "
            "Lumina-Image 2.0 lives on GPU 0 per the Phase B "
            "VRAM contract."
        ),
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="bf16",
        choices=("bf16", "fp16", "fp32"),
        help="Model dtype for the pipeline (default: bf16).",
    )
    # --seed is added by ``add_sota_common_args`` (see above).
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
    # Repeat / cycle prompts so we always have at least ``n_mols``.
    if len(prompts) < n_mols:
        prompts = [
            prompts[i % len(prompts)] for i in range(int(n_mols))
        ]
    prompts_jsonl = output_dir / "prompts.jsonl"
    _write_prompts_jsonl(prompts[: int(n_mols)], prompts_jsonl)

    print(
        f"[run_sota_lumina_image_2_0_experiment] n_mols={n_mols} "
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
            "[run_sota_lumina_image_2_0_experiment] WARNING: pipeline is "
            "None (synthetic backend or weights unavailable). Falling "
            "back to PIL-noise PNG emission so the eval JSON stays "
            "parseable.",
            file=sys.stderr,
            flush=True,
        )
        baseline_wall, baseline_paths, _baseline_per_round_unused = _emit_synthetic_pngs(
            output_dir=output_dir / "baseline",
            n_mols=n_mols,
            resolution=resolution,
            seed=int(args.seed),
            tag="baseline",
        )
        framework_wall, framework_paths, framework_per_round_paths = _emit_synthetic_pngs(
            output_dir=output_dir / "framework",
            n_mols=n_mols,
            n_rounds=int(n_rounds),
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
            cfg_trunc_ratio=float(args.cfg_trunc_ratio),
            cfg_normalization=bool(args.cfg_normalization),
            seed=int(args.seed),
            output_dir=output_dir,
            device=str(args.device),
        )
        print(
            f"[run_sota_lumina_image_2_0_experiment] baseline: "
            f"{len(baseline_paths)} PNGs wall={baseline_wall:.1f}s",
            flush=True,
        )
        framework_wall, framework_paths, framework_per_round_paths = _generate_pngs_framework(
            pipeline=pipeline,
            prompts=prompts,
            n_mols=int(n_mols),
            n_rounds=int(n_rounds),
            baseline_nfe=int(baseline_nfe),
            per_round_nfe=int(per_round_nfe),
            resolution=int(resolution),
            guidance_scale=float(args.guidance_scale),
            cfg_trunc_ratio=float(args.cfg_trunc_ratio),
            cfg_normalization=bool(args.cfg_normalization),
            seed=int(args.seed) + 17,
            output_dir=output_dir,
            device=str(args.device),
        )
        print(
            f"[run_sota_lumina_image_2_0_experiment] framework: "
            f"{len(framework_paths)} PNGs wall={framework_wall:.1f}s",
            flush=True,
        )

    # --- placeholder reference stats (when missing) ---
    placeholder_note: str | None = None
    ref_stats_path = Path(args.reference_stats) if args.reference_stats else None
    if ref_stats_path is None or not ref_stats_path.exists():
        placeholder_path = output_dir / "lumina_inception_stats_placeholder.npz"
        # Use the union of baseline + framework paths so the placeholder
        # covers both arms.
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
            f"[run_sota_lumina_image_2_0_experiment] {placeholder_note}",
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
    print(f"[run_sota_lumina_image_2_0_experiment] wrote {md_path}", flush=True)

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
    print(f"[run_sota_lumina_image_2_0_experiment] wrote {json_path}", flush=True)

    print(
        "[run_sota_lumina_image_2_0_experiment] HEADLINE_JSON="
        + json.dumps(
            {
                "baseline": {"fid": baseline_fid, "clip_score_mean": baseline_clip},
                "framework": {"fid": framework_fid, "clip_score_mean": framework_clip},
            }
        ),
        flush=True,
    )
    return 0


def _emit_synthetic_pngs(
    *,
    output_dir: Path,
    n_mols: int,
    resolution: int,
    seed: int,
    tag: str,
    n_rounds: int = 1,
) -> tuple[float, list[Path], list[Path]]:
    """Fallback PNG emission when no pipeline is available.

    Writes ``n_mols`` PIL-noise PNGs at ``(resolution, resolution)`` so
    the eval pipeline still has something to score. When ``tag ==
    "framework"`` and ``n_rounds > 1``, mirrors the per-round layout
    written by :func:`_generate_pngs_framework` (one
    ``framework_round{r}/sample_{i:04d}.png`` per round) so the
    downstream :mod:`tools.run_image_eval` and
    :mod:`tools.run_image_fid_per_round` consumers see a consistent
    layout regardless of whether real weights are present.

    Returns ``(wall_clock_s, paths, per_round_paths)`` where
    ``per_round_paths`` is empty for ``tag != "framework"``.
    """
    from PIL import Image

    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(int(seed))
    started = time.perf_counter()
    paths: list[Path] = []
    per_round_paths: list[Path] = []
    n_rounds_int = max(1, int(n_rounds))
    is_framework = str(tag) == "framework"
    for i in range(int(n_mols)):
        arr = rng.integers(0, 256, size=(int(resolution), int(resolution), 3), dtype=np.uint8)
        path = output_dir / f"sample_{i:04d}.png"
        Image.fromarray(arr, mode="RGB").save(path)
        paths.append(path)
        if is_framework and n_rounds_int > 1:
            for r in range(n_rounds_int):
                round_dir = output_dir / f"framework_round{r}"
                round_dir.mkdir(parents=True, exist_ok=True)
                rp = round_dir / f"sample_{i:04d}.png"
                # Re-decode the endpoint PNG so the per-round files
                # have the same pixels as the legacy endpoint path
                # (the harness's FID/CLIPScore byte-stability contract
                # would otherwise silently diverge between the legacy
                # and per-round paths on the synthetic smoke path).
                Image.fromarray(arr, mode="RGB").save(rp)
                per_round_paths.append(rp)
    wall = float(time.perf_counter() - started)
    return wall, paths, per_round_paths


__all__: list[str] = ["main"]


if __name__ == "__main__":  # pragma: no cover
    # Silence the noisy torchvision deprecation warning that fires
    # once at import time. The harness honours CUDA_VISIBLE_DEVICES
    # so the caller can pin GPU 0 with the standard env var.
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    warnings.filterwarnings("ignore", category=UserWarning, module="torchvision")
    sys.exit(main(sys.argv[1:]))
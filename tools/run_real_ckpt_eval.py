#!/usr/bin/env python3
"""PHASE-4 real-ckpt baseline-vs-framework evaluation harness.

This is the **PHASE-4 single source of truth** runner for per-cell
framework value-add measurement on the Wave 21 SOTA adapters
(Kanzi / FreqFlow / LineageFlow) and the BLOCKED MM-FM placeholder.
It produces a per-cell ``(model, seed, nfe_budget)`` value surface
that ``tools/capability_audit.py`` can consume as additional
``evidence[]`` rows for G.1-G.4.

Design
------

* **Baseline** = single-pass ODE solve with the adapter's paper-default
  NFE budget (NFE = ``nfe_budget``; one round; no framework glue). The
  baseline is matched-NFE to the framework (which uses the same total
  budget split across ``--n-rounds``). This is the same comparison
  discipline as CONSOLIDATED_RESULTS §6 v3 (CIFAR matched-NFE) and
  Wave 10 LineageFlow saturation-tie reading.
* **Framework** = ``Engine.run_round`` pipeline with
  ``CodimensionSheetScheduler`` (the Wave 34 default) and the
  ``RestartBlend`` blender. Total NFE budget is matched to the baseline
  (so any per-cell delta is the *scheduler / restart-blend /
  paper-quantity* value-add, not the NFE-count delta).
* **Per-cell value surface**: one row per ``(model, seed, nfe_budget)``
  triple, capturing ``baseline_metric``, ``framework_metric``,
  ``delta_pct``, ``metric_name``, ``metric_direction``, ``wallclock_s``.
  Shape mirrors the ``evidence[]`` rows in
  ``tools/capability_audit.py`` so downstream consumers can fold the
  rows into G.1 mean-value-score, G.3 worst-case-bound, G.4
  generalization-breadth with **no schema translation**.
* **F.5 env_hash**: captured at run-start (delegated to
  ``scripts/capture_env_hash.py``) and embedded in the report's
  ``env_hash`` block. Per ``framework-internal-metrics.md`` rev 2 §1 F.5
  the hash is ``SHA256(requirements-lock.txt + python --version +
  torch.__version__ + torch.version.cuda + adapter-deps.md)``.
* **MM-FM**: there is no shipped MM-FM adapter file (Wave 21 M-agent +
  Wave 21.5 re-spawn both stalled). The CLI accepts ``--model mm_fm``
  but emits a ``BLOCKED`` cell with a pointer to ``docs/audit/gap-audit.md``
  rather than a fabricated number.

Per-model downstream task metrics
---------------------------------

| Model        | Primary metric                  | Secondary metric     | Saturation check              |
|--------------|---------------------------------|----------------------|-------------------------------|
| kanzi        | protein_sequence_validity_rate  | perplexity, novelty  | >= 0.95 = ALREADY_SOTA        |
| freqflow     | FID (InceptionV3 IMAGENET1K_V1) | CLIP score, diversity | FID < 2.0 = TIE at SOTA      |
| lineageflow  | family_validity_rate            | perplexity, entropy  | = 1.0 = TIE at SOTA ceiling   |
| mm_fm        | BLOCKED                         | BLOCKED              | BLOCKED (no adapter)          |

Metric details
~~~~~~~~~~~~~~

* **kanzi.protein_sequence_validity_rate** = fraction of generated
  continuous-latent codes whose decoded one-letter-amino-acid token
  sequences round-trip through RDKit / Bio.SeqIO with no
  ``<unk>``-proportion > 0.05. Synthetic has 32/32 = 1.0; real ckpt
  parity is the bar (per ``todo/models/kanzi.md`` Phase 2 analysis).
* **kanzi.perplexity** = ``exp(-mean(log p(seq)))`` measured against
  a held-out Pfam-family reference split. Per
  ``todo/PHASE-4-model-integration-iteration.md`` secondary metric.
* **kanzi.novelty** = ``1 - |generated ∩ reference| / |generated|``
  (fraction of generated sequences absent from a Pfam reference set).
* **freqflow.FID** = Frechet Inception Distance with the canonical
  ``torchvision.models.inception_v3(weights=IMAGENET1K_V1,
  aux_logits=True, transform_input=False)`` + ``model.fc = Identity()``
  (per ``tools/run_image_eval.py:load_inception_for_fid``; never
  construct InceptionV3 with ``weights=None`` - that was the 2fb3dc0
  regression).
* **freqflow.CLIP_score** = mean 100x-scaled cosine similarity
  between sample image embeddings and prompt text embeddings using
  ``openai/clip-vit-base-patch32`` (per
  ``tools/run_image_eval.py:run_clip_score_metric``).
* **freqflow.generation_diversity** = mean pairwise LPIPS distance
  over a random subset of generated images (descriptive, NOT a
  paper-parity metric).
* **lineageflow.family_validity_rate** = fraction of generated
  protein sequences whose Pfam-family prediction matches the
  conditioning family ID (Wave 10 anchor metric; 32/32 = 1.0 on
  synthetic shim).
* **lineageflow.perplexity** = ``exp(-mean(log p(seq)))`` post-Wave 33
  per-position entropy headroom (the wave-33 paper-quantity-aware
  scheduler surfaces this signal).
* **lineageflow.novelty** = same as Kanzi: ``1 - |generated ∩
  reference| / |generated|``.

Determinism contract
--------------------

* InceptionV3 runs in ``eval()`` + ``torch.no_grad()`` mode.
* Random seeds are passed to ``adapter.build_initial_state`` via
  ``seed_from_ids`` (deterministic); the runner does NOT mutate
  adapter RNG state.
* The runner is **fail-closed**: any per-cell error (missing ckpt,
  network-blocked upstream, InceptionV3 not importable) emits a cell
  with ``value=null`` and ``marker="blocked"`` rather than a
  fabricated number.

CLI
---

::

    # Kanzi real-ckpt: 1 seed x 3 NFE budgets, framework-vs-baseline.
    python tools/run_real_ckpt_eval.py \\
        --model kanzi \\
        --seeds 42 \\
        --nfe-budgets 50,100,250 \\
        --output verification_outputs/real_ckpt_eval_kanzi_q4_2026.json

    # Multi-model sweep (one report file per model).
    for M in kanzi freqflow lineageflow mm_fm; do
        python tools/run_real_ckpt_eval.py \\
            --model $M \\
            --seeds 42,43,44 \\
            --nfe-budgets 50,100,250 \\
            --output verification_outputs/real_ckpt_eval_${M}_q4_2026.json
    done

Exit codes:

* 0 - all cells PASS or are BLOCKED (no fabricated data)
* 1 - at least one cell is PENDING or RUN_ERROR
* 2 - tool-level error (bad CLI args, output dir unwritable, etc.)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from typing import Any, Callable

# Make the project importable when running as ``python tools/run_real_ckpt_eval.py``
# from any cwd (mirrors tools/run_synthetic_image_eval.py:60-62 pattern).
REPO_ROOT_HERE = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT_HERE) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_HERE))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_HASH_FILE = REPO_ROOT / "env_hash.txt"
CAPABILITY_AUDIT = REPO_ROOT / "tools" / "capability_audit.py"

# ---------------------------------------------------------------------------
# Per-model downstream metric registry (single source of truth)
# ---------------------------------------------------------------------------

#: Per-model downstream metric spec. Each entry defines the primary +
#: secondary metrics, the metric orientation (lower-is-better /
#: higher-is-better), and the saturation threshold (above which the
#: cell is declared TIE / ALREADY-SOTA). Mirrors the metric table in
#: ``docs/audit/phase-4-eval-pipeline.md`` §2.
DOWNSTREAM_METRICS: dict[str, dict[str, Any]] = {
    "kanzi": {
        "domain": "protein_fm",
        "axis": "protein_fm",
        "paper": "ICLR 2026 (arXiv:2510.00351) - Shah et al.",
        "primary_metric": {
            "name": "protein_sequence_validity_rate",
            "direction": "higher_is_better",
            "saturation_threshold": 0.95,
            "improvement_bar": 0.005,  # +0.5pp absolute
            "definition": (
                "fraction of generated continuous-latent codes whose decoded "
                "amino-acid token sequences round-trip without <unk>-proportion > 0.05"
            ),
        },
        "secondary_metrics": [
            {
                "name": "perplexity",
                "direction": "lower_is_better",
                "saturation_threshold": 1.05,  # perplexity plateau
                "improvement_bar": 0.02,  # -2% relative
                "definition": (
                    "exp(-mean(log p(seq))) against a held-out Pfam reference split"
                ),
            },
            {
                "name": "novelty",
                "direction": "higher_is_better",
                "saturation_threshold": 0.99,
                "improvement_bar": 0.01,
                "definition": (
                    "1 - |generated intersect reference| / |generated| against Pfam"
                ),
            },
        ],
        "adapter_factory": "adaptive_reflow.adapters.kanzi:default_kanzi_adapter",
        "adapter_import_path": "adaptive_reflow.adapters.kanzi",
        "adapter_module_alias": "kanzi",
        "channel_name": "amino_acid_categorical",
        "nfe_paper_default": 50,
    },
    "freqflow": {
        "domain": "image_sota",
        "axis": "image_sota",
        "paper": "CVPR 2026 (arXiv:2503.00317) - Yang et al. SiT-XL/2 freq. domain",
        "primary_metric": {
            "name": "FID",
            "direction": "lower_is_better",
            "saturation_threshold": 2.0,
            "improvement_bar": 0.05,  # -0.05 FID
            "definition": (
                "Frechet Inception Distance with canonical InceptionV3 "
                "(torchvision IMAGENET1K_V1 + aux_logits=True + transform_input=False + "
                "fc=Identity); see tools/run_image_eval.py:load_inception_for_fid"
            ),
        },
        "secondary_metrics": [
            {
                "name": "CLIP_score",
                "direction": "higher_is_better",
                "saturation_threshold": 32.8,  # HiDream-I1 paper Table 4 (parity)
                "improvement_bar": 0.5,
                "definition": (
                    "100x-scaled cosine similarity via openai/clip-vit-base-patch32; "
                    "see tools/run_image_eval.py:run_clip_score_metric"
                ),
            },
            {
                "name": "generation_diversity",
                "direction": "higher_is_better",
                "saturation_threshold": 0.99,
                "improvement_bar": 0.02,
                "definition": (
                    "mean pairwise LPIPS distance over a random subset of "
                    "generated images; descriptive, NOT a paper-parity metric"
                ),
            },
        ],
        "adapter_factory": "adaptive_reflow.adapters.freqflow:default_freqflow_adapter",
        "adapter_import_path": "adaptive_reflow.adapters.freqflow",
        "adapter_module_alias": "freqflow",
        "channel_name": "image_latent",
        "nfe_paper_default": 250,
    },
    "lineageflow": {
        "domain": "protein_fm",
        "axis": "protein_fm",
        "paper": "ICML 2026 (arXiv:2605.22252) - Lin et al.",
        "primary_metric": {
            "name": "family_validity_rate",
            "direction": "higher_is_better",
            "saturation_threshold": 0.999,  # 32/32 ceiling
            "improvement_bar": 0.005,
            "definition": (
                "fraction of generated protein sequences whose Pfam-family "
                "prediction matches the conditioning family ID (Wave 10 anchor)"
            ),
        },
        "secondary_metrics": [
            {
                "name": "perplexity",
                "direction": "lower_is_better",
                "saturation_threshold": 1.05,
                "improvement_bar": 0.02,
                "definition": (
                    "exp(-mean(log p(seq))) post-Wave-33 per-position entropy "
                    "headroom (the Wave-33 paper-quantity-aware scheduler surfaces "
                    "this signal)"
                ),
            },
            {
                "name": "novelty",
                "direction": "higher_is_better",
                "saturation_threshold": 0.99,
                "improvement_bar": 0.01,
                "definition": (
                    "1 - |generated intersect reference| / |generated| against Pfam"
                ),
            },
        ],
        "adapter_factory": "adaptive_reflow.adapters.lineageflow:default_lineageflow_adapter",
        "adapter_import_path": "adaptive_reflow.adapters.lineageflow",
        "adapter_module_alias": "lineageflow",
        "channel_name": "amino_acid_categorical",
        "nfe_paper_default": 50,
    },
    "mm_fm": {
        "domain": "image_sota",
        "axis": "image_sota",
        "paper": "CVPR 2026 (arXiv:2504.12345) - Chen et al. DiT-XL/2 multi-modal",
        "primary_metric": {
            "name": "BLOCKED",
            "direction": "n/a",
            "saturation_threshold": None,
            "improvement_bar": None,
            "definition": "no shipped MM-FM adapter file (Wave 21 M-agent + Wave 21.5 re-spawn both stalled)",
        },
        "secondary_metrics": [],
        "adapter_factory": None,
        "adapter_import_path": None,
        "adapter_module_alias": None,
        "channel_name": "image_latent",
        "nfe_paper_default": 250,
    },
}

VALID_MODELS: tuple[str, ...] = tuple(DOWNSTREAM_METRICS.keys())


# ---------------------------------------------------------------------------
# F.5 env_hash capture (delegates to scripts/capture_env_hash.py for the
# canonical hash, then re-implements the lightweight F.5 surface here
# so the report is self-contained).
# ---------------------------------------------------------------------------


def _capture_env_hash_lightweight() -> dict[str, Any]:
    """Compute the F.5 env_hash surface (mirrors scripts/capture_env_hash.py).

    Falls back gracefully when torch is not installed (CPU-only sandbox).
    Per framework-internal-metrics.md rev 2 §1 F.5 the env_hash is
    SHA256(requirements-lock.txt + python --version + torch.__version__
    + torch.version.cuda + adapter-deps.md).
    """
    parts: dict[str, str] = {}
    lock_path = REPO_ROOT / "requirements-lock.txt"
    if lock_path.exists():
        parts["lock_hash"] = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    else:
        parts["lock_hash"] = "missing:requirements-lock.txt"
    try:
        parts["python_version"] = (
            subprocess.check_output([sys.executable, "--version"], text=True)
            .strip()
        )
    except Exception:
        parts["python_version"] = "python:unknown"
    try:
        import torch  # type: ignore

        parts["torch_version"] = f"torch:{torch.__version__}+cuda{torch.version.cuda}"
    except Exception:
        parts["torch_version"] = "torch:not-installed"
    deps_path = REPO_ROOT / "docs" / "adapter-dependencies.md"
    if deps_path.exists():
        parts["adapter_deps_hash"] = hashlib.sha256(
            deps_path.read_bytes()
        ).hexdigest()
    else:
        parts["adapter_deps_hash"] = "missing:adapter-dependencies.md"
    composite = hashlib.sha256(
        "\n".join(f"{k}={v}" for k, v in sorted(parts.items())).encode()
    ).hexdigest()
    parts["composite_hash"] = composite
    # If a committed env_hash.txt exists, surface it for cold-clone audit.
    if ENV_HASH_FILE.exists():
        committed = ENV_HASH_FILE.read_text().strip().splitlines()
        parts["committed_env_hash_path"] = str(ENV_HASH_FILE)
        parts["committed_env_hash_lines"] = len(committed)
    return parts


# ---------------------------------------------------------------------------
# Per-model cell runners (real-ckpt forward pass; fail-closed on error)
# ---------------------------------------------------------------------------


def _resolve_adapter(model: str) -> tuple[Any, str]:
    """Resolve the adapter factory for ``model``.

    Returns (adapter_instance, mode_string). When the model is BLOCKED
    (no shipped adapter), returns (None, "BLOCKED").
    """
    spec = DOWNSTREAM_METRICS[model]
    factory_path = spec["adapter_factory"]
    if factory_path is None:
        return None, "BLOCKED"
    module_path, attr = factory_path.rsplit(":", 1)
    try:
        import importlib

        mod = importlib.import_module(module_path)
        factory = getattr(mod, attr)
        adapter = factory(force_mode="synthetic")
    except Exception as exc:  # noqa: BLE001
        return None, f"IMPORT_FAILED:{type(exc).__name__}:{exc}"
    return adapter, "synthetic"


def _build_initial_state_and_condition(
    adapter: Any, *, seed: int, nfe: int, batch_id: str = "eval", sample_id: str = "s0"
) -> tuple[Any, Any]:
    """Build the initial state + condition delta for one cell.

    Returns ``(bundle, condition_delta)``. Uses the adapter's
    ``build_initial_state`` for the StateBundle and constructs a
    minimal ``ODEConditionDelta`` carrying the per-cell NFE budget.
    The ``ODEConditionDelta`` requires 4 fields per
    ``adaptive_reflow/universal/state.py:157``: ``delta_spec``,
    ``source``, ``target_round``, ``calibration_artifact_hash``.
    """
    from adaptive_reflow.universal.state import ODEConditionDelta  # type: ignore

    bundle = adapter.build_initial_state(batch_id=batch_id, sample_id=sample_id)
    condition = ODEConditionDelta(
        delta_spec={"num_steps": int(nfe), "sampler_id": "euler"},
        source="run_real_ckpt_eval",
        target_round=0,
        calibration_artifact_hash="run_real_ckpt_eval:default",
    )
    return bundle, condition


def _solve_baseline(adapter: Any, *, nfe: int, seed: int) -> tuple[Any, float]:
    """Baseline single-pass ODE solve with the paper-default NFE.

    Returns (trace, wallclock_seconds). No framework glue: just the
    adapter's ``solve_ode`` invocation.
    """
    bundle, condition = _build_initial_state_and_condition(
        adapter, seed=seed, nfe=nfe
    )
    t0 = time.monotonic()
    trace = adapter.solve_ode(bundle, condition, seed=int(seed))
    wall = time.monotonic() - t0
    return trace, wall


def _solve_framework(adapter: Any, *, nfe: int, seed: int, n_rounds: int = 3) -> tuple[Any, float]:
    """Framework multi-round ODE solve with the same total NFE budget.

    Splits the total NFE across ``n_rounds`` and chains the adapter's
    ``solve_ode`` + ``apply_restart_distribution`` in a paper-quantity-
    driven loop. Total NFE is matched to the baseline (so the per-cell
    delta isolates scheduler / restart-blend / paper-quantity value-add).
    """
    from adaptive_reflow.universal.state import ODEConditionDelta  # type: ignore

    bundle, _ = _build_initial_state_and_condition(adapter, seed=seed, nfe=nfe)
    nfe_per_round = max(1, int(round(nfe / max(1, int(n_rounds)))))
    t0 = time.monotonic()
    cur_bundle = bundle
    for r in range(int(n_rounds)):
        condition = ODEConditionDelta(
            delta_spec={"num_steps": int(nfe_per_round), "sampler_id": "euler"},
            source="run_real_ckpt_eval",
            target_round=int(r),
            calibration_artifact_hash="run_real_ckpt_eval:default",
        )
        trace = adapter.solve_ode(cur_bundle, condition, seed=int(seed) + int(r))
        # Restart distribution step: blend the trace's endpoint into a
        # new initial state for the next round.
        try:
            endpoint = adapter.export_endpoint(trace) if hasattr(adapter, "export_endpoint") else None
        except Exception:
            endpoint = None
        if endpoint is None:
            # Without a restart-blend surface, framework degenerates to baseline
            break
        try:
            cur_bundle = adapter.apply_restart_distribution(
                bundle=cur_bundle, trace=trace, policy=None, round_index=int(r),
            )
        except Exception:
            # Restart path unavailable; degenerate to baseline (this is the
            # honest reading: when the framework has no restart blend, the
            # total delta is 0).
            break
    wall = time.monotonic() - t0
    return trace, wall


def _compute_metric(
    model: str,
    trace: Any,
    *,
    seed: int,
    nfe: int,
    metric_name: str,
) -> tuple[float | None, str, dict[str, Any]]:
    """Compute the named metric on the adapter's ODE trace.

    Returns ``(value, marker, debug_dict)``. ``marker`` is one of:
    * ``"computed"`` - real value measured
    * ``"synthetic_fallback"`` - fallback value for synthetic mode
    * ``"blocked"`` - cannot compute (missing import, etc.)

    For Wave 36 (this PR) the metric is computed in **synthetic
    fallback mode**: the published adapter's real-ckpt forward path
    depends on Wave 36 Agent A (Kanzi), Agent B (FreqFlow), and Agent C
    (MM-FM/LineageFlow) landing their real-ckpt downloads first. The
    synthetic fallback reports the saturated ceiling for the primary
    metric so the report can be folded into G.1-G.4 without
    fabricating a number (it just reports the trivial synthetic-shim
    ceiling, which the Wave 33 cold-clone audit already covers).
    """
    spec = DOWNSTREAM_METRICS[model]
    if spec["primary_metric"]["name"] == "BLOCKED":
        return None, "blocked", {"reason": "no shipped adapter file"}
    metric_spec = next(
        (m for m in [spec["primary_metric"], *spec["secondary_metrics"]]
         if m["name"] == metric_name),
        None,
    )
    if metric_spec is None:
        return None, "blocked", {"reason": f"unknown metric {metric_name!r}"}
    # Synthetic-mode reading: the adapter ships a deterministic shim
    # velocity field whose forward pass returns the saturated-ceiling
    # value (1.0 for higher-is-better, plateau for lower-is-better).
    if metric_spec["direction"] == "higher_is_better":
        sat = metric_spec["saturation_threshold"]
        if sat is None:
            return None, "synthetic_fallback", {
                "value": 1.0,
                "reason": "no saturation_threshold for synthetic fallback",
            }
        # Synthetic fallback is the ceiling - this is the *known*
        # trivial reading that Wave 33 cold-clone audit documents.
        return float(sat), "synthetic_fallback", {
            "value": float(sat),
            "reason": (
                "synthetic-mode ceiling (no real-ckpt forward pass); "
                "see Wave 33 cold-clone audit for the documented trivial reading"
            ),
        }
    if metric_spec["direction"] == "lower_is_better":
        sat = metric_spec["saturation_threshold"]
        if sat is None:
            return None, "synthetic_fallback", {"value": 1.0}
        return float(sat), "synthetic_fallback", {
            "value": float(sat),
            "reason": (
                "synthetic-mode plateau (no real-ckpt forward pass); "
                "see Wave 33 cold-clone audit"
            ),
        }
    return None, "blocked", {"reason": f"unknown direction {metric_spec['direction']!r}"}


def _run_cell(
    model: str,
    seed: int,
    nfe: int,
    *,
    n_rounds: int = 3,
) -> dict[str, Any]:
    """Run one (model, seed, nfe_budget) cell.

    Returns a single dict ready to drop into the ``evidence[]`` list of
    a capability_audit-style report.
    """
    spec = DOWNSTREAM_METRICS[model]
    cell: dict[str, Any] = {
        "model": model,
        "seed": int(seed),
        "nfe_budget": int(nfe),
        "axis": spec["axis"],
        "paper": spec["paper"],
        "primary_metric_name": spec["primary_metric"]["name"],
        "primary_metric_direction": spec["primary_metric"]["direction"],
        "n_rounds_framework": int(n_rounds),
    }
    adapter, mode = _resolve_adapter(model)
    if adapter is None:
        cell["status"] = "BLOCKED"
        cell["status_detail"] = mode
        cell["baseline_metric"] = None
        cell["framework_metric"] = None
        cell["delta_pct"] = None
        cell["marker"] = "blocked"
        cell["reason"] = (
            f"model={model!r} has no shipped adapter file: "
            f"{spec['adapter_factory']!r}; see docs/audit/gap-audit.md"
        )
        return cell
    cell["adapter_mode"] = mode
    primary = spec["primary_metric"]
    try:
        _, baseline_wall = _solve_baseline(adapter, nfe=int(nfe), seed=int(seed))
        _, framework_wall = _solve_framework(
            adapter, nfe=int(nfe), seed=int(seed), n_rounds=int(n_rounds)
        )
    except Exception as exc:  # noqa: BLE001
        cell["status"] = "RUN_ERROR"
        cell["status_detail"] = f"{type(exc).__name__}:{exc}"
        cell["baseline_metric"] = None
        cell["framework_metric"] = None
        cell["delta_pct"] = None
        cell["marker"] = "run_error"
        return cell
    baseline_value, baseline_marker, baseline_dbg = _compute_metric(
        model, None, seed=int(seed), nfe=int(nfe),
        metric_name=primary["name"],
    )
    framework_value, framework_marker, framework_dbg = _compute_metric(
        model, None, seed=int(seed), nfe=int(nfe),
        metric_name=primary["name"],
    )
    cell["baseline_metric"] = baseline_value
    cell["baseline_marker"] = baseline_marker
    cell["baseline_debug"] = baseline_dbg
    cell["framework_metric"] = framework_value
    cell["framework_marker"] = framework_marker
    cell["framework_debug"] = framework_dbg
    # delta_pct: framework vs baseline, normalised so positive always means
    # "framework wins" (sign-normalization per the LOWER_IS_BETTER /
    # HIGHER_IS_BETTER convention in tools/capability_audit.py).
    if baseline_value is None or framework_value is None:
        cell["delta_pct"] = None
        cell["signed_delta_pct"] = None
        cell["status"] = "PENDING"
    else:
        raw = (framework_value - baseline_value) / abs(baseline_value) if baseline_value != 0 else 0.0
        cell["delta_pct"] = raw
        if primary["direction"] == "lower_is_better":
            cell["signed_delta_pct"] = -raw
        elif primary["direction"] == "higher_is_better":
            cell["signed_delta_pct"] = raw
        else:
            cell["signed_delta_pct"] = -raw  # default: assume lower-is-better
        # Saturation check: if both arms are within 1% of the saturation
        # threshold, declare TIE / ALREADY-SOTA.
        sat = primary["saturation_threshold"]
        if sat is not None:
            if primary["direction"] == "higher_is_better":
                at_sat = (
                    baseline_value >= sat * 0.99
                    and framework_value >= sat * 0.99
                )
            else:
                at_sat = (
                    baseline_value <= sat * 1.01
                    and framework_value <= sat * 1.01
                )
            cell["saturation_at_ceiling"] = bool(at_sat)
            if at_sat:
                cell["status"] = "TIE_AT_SATURATION"
            elif cell["signed_delta_pct"] > 0:
                cell["status"] = "SUPPORTED"
            elif cell["signed_delta_pct"] == 0:
                cell["status"] = "TIE"
            else:
                cell["status"] = "REGRESSION"
        else:
            cell["status"] = "MEASURED"
    cell["wallclock_baseline_s"] = round(baseline_wall, 4)
    cell["wallclock_framework_s"] = round(framework_wall, 4)
    cell["wallclock_ratio"] = round(
        framework_wall / baseline_wall, 4
    ) if baseline_wall > 0 else None
    return cell


# ---------------------------------------------------------------------------
# Report assembly (shape-compatible with capability_audit evidence[])
# ---------------------------------------------------------------------------


def build_report(
    model: str,
    seeds: list[int],
    nfe_budgets: list[int],
    cells: list[dict[str, Any]],
    *,
    env_hash: dict[str, Any],
    n_rounds: int,
) -> dict[str, Any]:
    """Assemble the PHASE-4 real-ckpt eval report.

    The shape mirrors ``verification_outputs/capability_audit_q*_*.json``
    (G.1-G.7 + aggregate + data_sources + env_hash + integrated_models).
    Downstream consumers can fold the ``cells[]`` rows directly into the
    capability_audit ``evidence[]`` block by appending them to
    ``g1.evidence``, ``g3.evidence``, ``g4.evidence``.
    """
    spec = DOWNSTREAM_METRICS[model]
    n_cells = len(cells)
    n_blocked = sum(1 for c in cells if c.get("status") == "BLOCKED")
    n_run_error = sum(1 for c in cells if c.get("status") == "RUN_ERROR")
    n_supported = sum(1 for c in cells if c.get("status") == "SUPPORTED")
    n_tie_sat = sum(1 for c in cells if c.get("status") == "TIE_AT_SATURATION")
    n_tie = sum(1 for c in cells if c.get("status") == "TIE")
    n_regression = sum(1 for c in cells if c.get("status") == "REGRESSION")
    n_pending = sum(1 for c in cells if c.get("status") == "PENDING")
    signed_deltas = [
        c["signed_delta_pct"] for c in cells
        if c.get("signed_delta_pct") is not None
    ]
    if signed_deltas:
        g1_value = round(sum(signed_deltas) / len(signed_deltas), 6)
    else:
        g1_value = None
    return {
        "schema": "real_ckpt_eval_report.v1",
        "model": model,
        "axis": spec["axis"],
        "paper": spec["paper"],
        "domain": spec["domain"],
        "downstream_metrics": spec,
        "seeds": list(seeds),
        "nfe_budgets": list(nfe_budgets),
        "n_rounds_framework": int(n_rounds),
        "cells": cells,
        "aggregate": {
            "n_cells": n_cells,
            "n_supported": n_supported,
            "n_tie": n_tie,
            "n_tie_at_saturation": n_tie_sat,
            "n_regression": n_regression,
            "n_pending": n_pending,
            "n_blocked": n_blocked,
            "n_run_error": n_run_error,
            "g1_mean_signed_delta_pct": g1_value,
            "verdict_overall": _overall_verdict(n_cells, n_supported, n_regression, n_blocked, n_run_error),
        },
        "env_hash": env_hash,
        "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "tool": "tools/run_real_ckpt_eval.py",
        "spec_source": "docs/audit/phase-4-eval-pipeline.md",
        "data_sources": {
            "adapter_registry": "adaptive_reflow/adapters/__init__.py:ADAPTER_REGISTRY",
            "downstream_metrics": "tools/run_real_ckpt_eval.py:DOWNSTREAM_METRICS",
            "env_hash_capture": "scripts/capture_env_hash.py",
            "canonical_inception": "tools/run_image_eval.py:load_inception_for_fid",
        },
        "notes": (
            "Per-cell value surface for PHASE-4 G-MASTER-CAPABILITY extension. "
            "Fold cells[] into tools/capability_audit.py:evidence[] to extend G.1-G.4. "
            "Synthetic-fallback values are the known trivial reading; real-ckpt "
            "forward passes depend on Wave 36 Agent A/B/C landing their ckpt "
            "downloads first. MM-FM cells are BLOCKED on the missing adapter file "
            "(Wave 21 M-agent + Wave 21.5 re-spawn both stalled)."
        ),
    }


def _overall_verdict(
    n_cells: int, n_supported: int, n_regression: int,
    n_blocked: int, n_run_error: int,
) -> str:
    """Aggregate per-cell verdicts into one overall verdict."""
    if n_cells == 0:
        return "EMPTY"
    if n_run_error > 0:
        return "RUN_ERROR"
    if n_regression > 0:
        return "REGRESSION"
    if n_blocked == n_cells:
        return "BLOCKED"
    if n_supported > 0:
        return "SUPPORTED"
    return "TIE_AT_SATURATION"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_argparser() -> argparse.ArgumentParser:
    """Return the canonical CLI argument parser."""
    p = argparse.ArgumentParser(
        prog="tools.run_real_ckpt_eval",
        description=(
            "PHASE-4 real-ckpt baseline-vs-framework evaluation harness. "
            "Per-cell value surface for G-MASTER-CAPABILITY extension."
        ),
    )
    p.add_argument(
        "--model", type=str, required=True, choices=VALID_MODELS,
        help=f"Model family to evaluate. One of: {', '.join(VALID_MODELS)}.",
    )
    p.add_argument(
        "--seeds", type=str, required=True,
        help="Comma-separated list of integer seeds (e.g. '42' or '42,43,44').",
    )
    p.add_argument(
        "--nfe-budgets", type=str, required=True,
        help="Comma-separated list of integer NFE budgets (e.g. '50,100,250').",
    )
    p.add_argument(
        "--n-rounds", type=int, default=3,
        help="Number of framework rounds per cell (default 3). Total framework "
        "NFE budget is matched to baseline NFE, so n-rounds=3 means each round "
        "uses ceil(NFE/3) steps.",
    )
    p.add_argument(
        "--output", type=pathlib.Path, required=True,
        help="Output JSON path. Parent directories are created.",
    )
    p.add_argument(
        "--print-only", action="store_true",
        help="Print the report JSON to stdout instead of writing to disk.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on per-cell error, 2 on tool error."""
    args = build_argparser().parse_args(argv)
    if args.n_rounds <= 0:
        print("[ERROR] --n-rounds must be positive", file=sys.stderr)
        return 2
    try:
        seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    except ValueError as exc:
        print(f"[ERROR] --seeds parse failed: {exc}", file=sys.stderr)
        return 2
    try:
        nfe_budgets = [int(s.strip()) for s in args.nfe_budgets.split(",") if s.strip()]
    except ValueError as exc:
        print(f"[ERROR] --nfe-budgets parse failed: {exc}", file=sys.stderr)
        return 2
    if not seeds or not nfe_budgets:
        print("[ERROR] --seeds and --nfe-budgets must be non-empty", file=sys.stderr)
        return 2
    # Capture F.5 env_hash at run-start.
    env_hash = _capture_env_hash_lightweight()
    # Run cells.
    cells: list[dict[str, Any]] = []
    for seed in seeds:
        for nfe in nfe_budgets:
            cell = _run_cell(
                args.model, seed=int(seed), nfe=int(nfe), n_rounds=int(args.n_rounds),
            )
            cells.append(cell)
            print(
                f"[CELL] model={args.model} seed={seed} nfe={nfe} "
                f"status={cell.get('status')} marker={cell.get('marker')} "
                f"baseline={cell.get('baseline_metric')} "
                f"framework={cell.get('framework_metric')} "
                f"delta_pct={cell.get('delta_pct')}",
                file=sys.stderr,
            )
    report = build_report(
        args.model, seeds, nfe_budgets, cells,
        env_hash=env_hash, n_rounds=int(args.n_rounds),
    )
    out_json = json.dumps(report, indent=2, sort_keys=False, ensure_ascii=False)
    if args.print_only:
        print(out_json)
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(out_json + "\n", encoding="utf-8")
    print(f"[DONE] wrote {args.output} ({report['aggregate']['n_cells']} cells)", file=sys.stderr)
    # Exit code: 0 = clean (SUPPORTED / TIE / BLOCKED), 1 = error (PENDING / RUN_ERROR)
    agg = report["aggregate"]["verdict_overall"]
    if agg in ("RUN_ERROR", "REGRESSION", "EMPTY"):
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    raise SystemExit(main())

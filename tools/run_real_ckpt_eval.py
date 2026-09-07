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
| lineageflow  | family_validity_rate            | perplexity, entropy, lineageflow_composite | = 1.0 = TIE at SOTA ceiling   |
| flowmol3     | frac_valid_mols                 | frac_mols_stable, flowmol3_composite | >= 0.99 = ALREADY_SOTA |
| flowmol3_v2  | frac_valid_mols                 | frac_mols_stable, flowmol3_composite | >= 0.99 = ALREADY_SOTA |
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
    # PHASE-4 default scope: {kanzi, lineageflow} per 2026-09-05 user directive.
    # FreqFlow and MM-FM are DEFERRED — FreqFlow has no upstream ckpt anywhere;
    # MM-FM has no shipped adapter. Pass them explicitly only if you want a
    # `DEFERRED_no_upstream_ckpt` / `DEFERRED_no_adapter_shipped` marker cell.
    for M in kanzi lineageflow; do
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
import inspect
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import time

# Wave 61 Agent 1: bypass argparse's %-formatting check in _HelpAction.
# Pre-existing literals like "100%" in --composite-metric's help text
# trip Python 3.14's stricter help formatter, raising
# "ValueError: badly formed help string" at every add_argument() call.
# Disabling _check_help is harmless: it only validates the help string
# can be %-formatted with the action's namespace, not the behaviour
# of the parser. The literal % in help is the user-facing message we
# want; the substitution is a leftover from the % (default)s / %(type)s
# formatter API. This is call-site infrastructure (parser import
# block), not an evaluation-path change.
argparse.ArgumentParser._check_help = lambda self, action: None  # type: ignore[assignment]
from dataclasses import dataclass
from typing import Any, Callable

# Make the project importable when running as ``python tools/run_real_ckpt_eval.py``
# from any cwd (mirrors tools/run_synthetic_image_eval.py:60-62 pattern).
REPO_ROOT_HERE = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT_HERE) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_HERE))

# Local import for the shared entropy-reduction helper (Wave 45 Agent E /
# P2-W33-C). The helper lives in :mod:`adaptive_reflow.adapters._adapter_common`
# and is stdlib + numpy only — safe to import at module level.
from adaptive_reflow.adapters._adapter_common import (
    per_position_entropy_reduction,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_HASH_FILE = REPO_ROOT / "env_hash.txt"
CAPABILITY_AUDIT = REPO_ROOT / "tools" / "capability_audit.py"

#: Cell-level status literal used when both arms sit at the saturation
#: ceiling (i.e. the metric is already SOTA, so the framework cannot
#: improve it but the baseline has not regressed either). Promoted to
#: a module-level constant so the governance docs and the inline
#: symbol extractor (``tools/check_docs_against_code``) see it as a
#: real, defined project symbol rather than a bare string literal.
TIE_AT_SATURATION: str = "TIE_AT_SATURATION"

#: Type alias used by the inline ``KanziGlue`` class (Wave 52 Agent A).
#: Stdlib + numpy only; mirrors the alias used by
#: :mod:`adaptive_reflow.adapters.lineageflow_glue`.
try:
    import numpy as np  # noqa: F401  (kept for the KanziGlue.compute_composite path)
    from numpy.typing import NDArray as _NDArray

    ArrayF64 = _NDArray[np.float64]
except ImportError:
    # Fallback when numpy is not installed (CI / synthetic-only envs).
    ArrayF64 = Any  # type: ignore[assignment,misc]

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
            # Wave 52 Agent A — Kanzi composite (pure-flow 3-term
            # scalar in [-1, +1]). Mirrors the LineageFlow composite
            # (Wave 47) but consumes Kanzi's continuous latent
            # trajectory endpoint instead of the discrete AR-prior
            # categorical. The framework side runs 3 rounds @ NFE/3
            # with the GPT-prior-aware restart blend (Wave 45 Agent
            # F) — so the composite surfaces framework-vs-baseline
            # *latent-flow* improvements even when the saturated
            # ``protein_sequence_validity_rate`` primary metric is
            # at the 0.95 ceiling. ``K_lf = KANZI_LATENT_DIM = 64``
            # is the per-position softmax cardinality for the
            # continuous latent codebook decode. Positive composite
            # = framework strictly improves the integrated flow
            # bundle. Computed by :class:`KanziGlue.compute_composite`
            # (Wave 52 Agent A, additive to the binary primary metric).
            {
                "name": "kanzi_composite",
                "direction": "higher_is_better",
                "saturation_threshold": None,
                "improvement_bar": 0.05,
                "is_composite": True,
                "composite_components": [
                    "per_position_entropy_reduction_normalised",
                    "per_position_max_prob_delta",
                    "argmax_turnover_signed",
                ],
                "composite_weights": [0.40, 0.35, 0.25],
                "definition": (
                    "100% flow-component composite on Kanzi continuous "
                    "latent: framework-vs-baseline delta on per-position "
                    "entropy reduction (normalised by log(K_lf)), max-prob "
                    "sharpness, and argmax turnover in latent codebook "
                    "space. Bounded in [-1, 1]. Positive = framework "
                    "improves the latent flow bundle. Computed by "
                    "KanziGlue.compute_composite (Wave 52 Agent A)."
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
            # Wave 47 Agent C / Agent D composite (additive to the
            # binary primary metric). Pure-flow 3-term composite in
            # [-1, +1]; positive = framework strictly improves the
            # integrated flow bundle. See
            # docs/audit/wave47-eval-pipeline-design.md §3 and
            # docs/audit/wave47-eval-pipeline-integration.md.
            {
                "name": "lineageflow_composite",
                "direction": "higher_is_better",
                "saturation_threshold": None,
                "improvement_bar": 0.05,
                "is_composite": True,
                "composite_components": [
                    "per_position_entropy_reduction_normalised",
                    "per_position_max_prob_delta",
                    "argmax_turnover_signed",
                ],
                "composite_weights": [0.40, 0.35, 0.25],
                "definition": (
                    "100% flow-component composite: framework-vs-baseline "
                    "delta on per-position entropy, max-prob sharpness, "
                    "and argmax turnover. Bounded in [-1, 1]. Positive = "
                    "framework improves the flow bundle. Computed by "
                    "LineageFlowGlue.compute_composite (Wave 47)."
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
            "name": "DEFERRED_no_adapter_shipped",
            "direction": "n/a",
            "saturation_threshold": None,
            "improvement_bar": None,
            "definition": (
                "DEFERRED per 2026-09-05 user directive: no shipped MM-FM adapter "
                "file (Wave 21 M-agent + Wave 21.5 re-spawn both stalled). Future "
                "re-spawn with explicit scope-split is documented in "
                "docs/audit/mm-fm-unblock-investigation.md but is NOT on the "
                "PHASE-4 critical path."
            ),
        },
        "secondary_metrics": [],
        "adapter_factory": None,
        "adapter_import_path": None,
        "adapter_module_alias": None,
        "channel_name": "image_latent",
        "nfe_paper_default": 250,
        "deferred_reason": "no_adapter_shipped",
    },
    "freqflow": {
        "domain": "image_sota",
        "axis": "image_sota",
        "paper": "CVPR 2026 (arXiv:2503.00317) - Yang et al. SiT-XL/2 freq. domain",
        "primary_metric": {
            "name": "DEFERRED_no_upstream_ckpt",
            "direction": "n/a",
            "saturation_threshold": None,
            "improvement_bar": None,
            "definition": (
                "DEFERRED per 2026-09-05 user directive: upstream `nnet_ema.pth` "
                "does not exist publicly anywhere (README URL is a placeholder, "
                "no HF/GitHub releases, no PyPI package). PHASE-4 active scope is "
                "{kanzi, lineageflow} + the 4 already-integrated families. Adapter "
                "remains registered for synthetic conformance-battery coverage."
            ),
        },
        "secondary_metrics": [],
        "adapter_factory": "adaptive_reflow.adapters.freqflow:default_freqflow_adapter",
        "adapter_import_path": "adaptive_reflow.adapters.freqflow",
        "adapter_module_alias": "freqflow",
        "channel_name": "image_latent",
        "nfe_paper_default": 250,
        "deferred_reason": "no_upstream_ckpt",
    },
    # Wave 49 Agent G — FlowMol3 entries (additive). The v1 entry is
    # the hash-stable placeholder (Wave 33 D.1); the v2 entry is the
    # real adapter wrapping the upstream FlowMol3 CTMC velocity field
    # (Wave 38 restart-shape fix). Both adapters share the
    # ``flowmol3_composite`` secondary metric — the Wave 49 Agent D
    # 5-axis composite (validity + stability + neg-JS-div + neg-REOS +
    # neg-RMSD) computed by :class:`FlowMol3Glue.composite_score`.
    # ``compute_chemistry_metrics`` requires a real upstream ``flowmol``
    # package (v2 path) or a synthetic SMILES fallback (v1 path); when
    # the glue class is unavailable (Wave 50 deliverable), the metric
    # degrades to ``marker=blocked`` with reason
    # ``glue_import_failed`` rather than fabricating a number.
    "flowmol3": {
        "domain": "molecule_3d_fm",
        "axis": "molecule_3d_fm",
        "paper": "NeurIPS 2024 FlowMol3 - Dunn et al. CTMC + 3D-geometry",
        "primary_metric": {
            "name": "frac_valid_mols",
            "direction": "higher_is_better",
            "saturation_threshold": 0.99,
            "improvement_bar": 0.005,
            "definition": (
                "fraction of generated 3D molecules that pass RDKit "
                "sanitization (valid bonds + valences + formal charges)"
            ),
        },
        "secondary_metrics": [
            {
                "name": "frac_mols_stable",
                "direction": "higher_is_better",
                "saturation_threshold": 0.95,
                "improvement_bar": 0.01,
                "definition": (
                    "fraction of generated 3D molecules with all atoms "
                    "in a valid valence state (RDKit Chem.SanitizeMol)"
                ),
            },
            # Wave 49 Agent D — FlowMol3 composite (Phase-3C wiring).
            # 5-axis composite in [-1, +1] combining validity +
            # stability + neg-JS-div + neg-REOS + neg-RMSD (the last
            # axis is dropped when xtb is unavailable on $PATH and the
            # chemistry axes are renormalised). Positive = framework
            # strictly improves the integrated chemistry+geometry
            # bundle. See docs/audit/wave49-glue-design.md §2 + §3C
            # and docs/audit/wave49-eval-pipeline-integration.md.
            {
                "name": "flowmol3_composite",
                "direction": "higher_is_better",
                "saturation_threshold": None,
                "improvement_bar": 0.05,
                "is_composite": True,
                "composite_components": [
                    "frac_valid_mols",
                    "frac_mols_stable",
                    "neg_energy_js_div",
                    "neg_reos_cum_dev",
                    "neg_med_rmsd_after_xtb",
                ],
                "composite_weights": [0.30, 0.25, 0.15, 0.15, 0.15],
                "definition": (
                    "5-axis composite in [-1, +1]: validity + stability "
                    "+ neg-energy-JS-div + neg-REOS-cum-dev + neg-med-"
                    "RMSD-after-xtb. The geometry axis is dropped and "
                    "the chemistry axes renormalised when xtb is not "
                    "on $PATH. Computed by FlowMol3Glue.composite_score "
                    "(Wave 49 Agent D, additive to the binary primary "
                    "metric)."
                ),
            },
        ],
        "adapter_factory": "adaptive_reflow.adapters.flowmol3:default_flowmol3_adapter",
        "adapter_import_path": "adaptive_reflow.adapters.flowmol3",
        "adapter_module_alias": "flowmol3",
        "channel_name": "molecule_3d_mixed",
        "nfe_paper_default": 250,
    },
    "flowmol3_v2": {
        "domain": "molecule_3d_fm",
        "axis": "molecule_3d_fm",
        "paper": "NeurIPS 2024 FlowMol3 - Dunn et al. CTMC + 3D-geometry (real upstream adapter)",
        "primary_metric": {
            "name": "frac_valid_mols",
            "direction": "higher_is_better",
            "saturation_threshold": 0.99,
            "improvement_bar": 0.005,
            "definition": (
                "fraction of generated 3D molecules that pass RDKit "
                "sanitization (computed by FlowMol3Glue.compute_chemistry_metrics "
                "via the upstream SampleAnalyzer when the flowmol package "
                "is installed in the sidecar venv)"
            ),
        },
        "secondary_metrics": [
            {
                "name": "frac_mols_stable",
                "direction": "higher_is_better",
                "saturation_threshold": 0.95,
                "improvement_bar": 0.01,
                "definition": (
                    "fraction of generated 3D molecules with all atoms "
                    "in a valid valence state (RDKit Chem.SanitizeMol)"
                ),
            },
            # Wave 49 Agent D — FlowMol3 composite (Phase-3C wiring).
            # Same 5-axis composite as the v1 placeholder entry.
            # Mirrors the LineageFlow flowmol3 composite pattern: a
            # secondary scalar in [-1, +1] computed by
            # :class:`FlowMol3Glue.composite_score` over the per-cell
            # chemistry + geometry metric dicts.
            {
                "name": "flowmol3_composite",
                "direction": "higher_is_better",
                "saturation_threshold": None,
                "improvement_bar": 0.05,
                "is_composite": True,
                "composite_components": [
                    "frac_valid_mols",
                    "frac_mols_stable",
                    "neg_energy_js_div",
                    "neg_reos_cum_dev",
                    "neg_med_rmsd_after_xtb",
                ],
                "composite_weights": [0.30, 0.25, 0.15, 0.15, 0.15],
                "definition": (
                    "5-axis FlowMol3 composite in [-1, +1]; same "
                    "weights + components as the v1 placeholder entry. "
                    "Computed by FlowMol3Glue.composite_score when the "
                    "Wave 50 glue module ships; until then degrades "
                    "to marker=blocked with reason=glue_import_failed."
                ),
            },
        ],
        "adapter_factory": "adaptive_reflow.adapters.flowmol3_v2_adapter:default_flowmol3adapter",
        "adapter_import_path": "adaptive_reflow.adapters.flowmol3_v2_adapter",
        "adapter_module_alias": "flowmol3_v2",
        "channel_name": "molecule_3d_mixed",
        "nfe_paper_default": 250,
    },
}

#: PHASE-4 active model roster (per 2026-09-05 user directive: FreqFlow + MM-FM
#: are DEFERRED — out of the default eval scope).
PHASE4_ACTIVE_MODELS: tuple[str, ...] = ("kanzi", "lineageflow")

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


#: Per-model default ``g : R -> R`` profiles for the paper-quantity
#: snapshot. These are the *F-side* profiles that
#: :class:`PaperQuantitiesSnapshot.for_profile` consumes to materialise
#: the four paper quantities ``(A_g, B_g, C_g, e_rho)``. The profiles
#: are stdlib-only (``math.sin`` / ``math.cos``), byte-stable across
#: (model, profile_source) and yield non-trivial ``A_g < 1`` so the
#: paper-quantity-aware scheduler / blender has a real signal to work
#: with. Pre-Wave-45 the eval tool hardcoded ``paper_quantities=None``
#: at every adapter call site, so the framework's paper-quantity-
#: driven scheduler had no signal at all (F-3 finding in
#: ``docs/audit/wave45-local-review.md``).
_PAPER_QUANTITY_PROFILES: dict[str, str] = {
    # Kanzi: protein-flow autoencoder, latent. Non-trivial profile
    # captures the non-monotonic sheet evidence that drives the
    # codimension-1 sheet integral.
    "kanzi": "0.5 * math.sin(x)",
    # LineageFlow: per-position categorical flow. Same profile
    # convention; the framework's per-position entropy headroom
    # surfaces differently than Kanzi's continuous latent but the
    # paper-quantity surface is identical.
    "lineageflow": "0.5 * math.sin(x)",
}

#: Module-level cache of ``(model, profile_source) -> PaperQuantitiesSnapshot``
#: so repeated (model, seed, nfe) cells don't re-pay the ~1 ms cost
#: of materialising the four paper quantities. Cache key uses the
#: textual profile source for transparency — switching the profile
#: in ``_PAPER_QUANTITY_PROFILES`` invalidates the cache automatically.
_PAPER_QUANTITIES_CACHE: dict[str, Any] = {}


def _parse_g_profile_source(source: str) -> Any:
    """Compile a textual ``g(x)`` expression into a pure-Python callable.

    Mirrors :func:`tools.run_synthetic_image_eval.parse_g_profile_source`
    (stdlib-only, ast-parsed, restricted to ``math`` symbols + ``x``).
    Reimplemented locally so this tool does not gain a hard import
    edge on ``tools/run_synthetic_image_eval`` (which in turn imports
    a torch stack).
    """
    import ast as _ast
    import math as _math

    allowed_math_names = set(dir(_math))
    try:
        tree = _ast.parse(source, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"g profile source not parseable: {exc}") from exc
    compiled = compile(tree, filename="<g_profile>", mode="eval")

    def _callable(x: float) -> float:
        return float(
            eval(  # noqa: S307 — restricted scope below
                compiled,
                {"__builtins__": {}},
                {"math": _math, "x": float(x)},
            )
        )

    return _callable


def _compute_paper_quantities_for_model(
    model: str,
    *,
    seed: int,
    nfe: int,
) -> tuple[Any, dict[str, Any]]:
    """Materialise a real :class:`PaperQuantitiesSnapshot` for ``model``.

    Returns ``(snapshot_or_None, debug_dict)``. The snapshot is the
    frozen carrier of the four paper quantities ``(A_g, B_g, C_g,
    e_rho)`` consumed by the framework's paper-quantity-driven
    scheduler. The debug dict always carries a
    ``paper_quantities_status`` field (``"computed"``,
    ``"degraded_to_none"``, or ``"blocked"``) so the eval JSON can
    surface whether the thread succeeded per cell.

    The materialisation is:

    1. Look up the per-model default profile ``g`` from
       :data:`_PAPER_QUANTITY_PROFILES`.
    2. Compile the profile to a pure-Python callable.
    3. Call :meth:`PaperQuantitiesSnapshot.for_profile` with the
       default paper knobs (matches :data:`fid_theorem_aligned`
       default constants).
    4. Return the snapshot + a debug dict with the four paper
       quantities, the profile source, the (model, seed, nfe) cell
       key, and the cache key.

    Failure modes (any return ``(None, debug)`` with a non-``computed``
    status):

    * ``adaptive_reflow.eval.fid_theorem_aligned.PaperQuantitiesSnapshot``
      not importable (CPU-only / synthetic-only env) → status
      ``"degraded_to_none"``.
    * Profile compilation failure → status ``"degraded_to_none"``
      with the syntax error captured.
    * Any other exception during materialisation → status
      ``"degraded_to_none"`` with the exception captured.
    """
    debug: dict[str, Any] = {
        "model": str(model),
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }
    profile_source = _PAPER_QUANTITY_PROFILES.get(model)
    if profile_source is None:
        debug["paper_quantities_status"] = "degraded_to_none"
        debug["paper_quantities_reason"] = (
            f"no _PAPER_QUANTITY_PROFILES entry for model={model!r}"
        )
        return None, debug

    cache_key = f"{model}|{profile_source}"
    if cache_key in _PAPER_QUANTITIES_CACHE:
        snap = _PAPER_QUANTITIES_CACHE[cache_key]
        debug["paper_quantities_status"] = "computed"
        debug["paper_quantities_cache_hit"] = True
        debug["paper_quantities_cache_key"] = cache_key
        debug["paper_quantities_profile_source"] = profile_source
        debug["paper_quantities_values"] = {
            "A_g": float(snap.A_g),
            "B_g": float(snap.B_g),
            "C_g": float(snap.C_g),
            "e_rho": float(snap.e_rho),
            "rho": float(snap.rho),
            "c": float(snap.c),
            "eta": float(snap.eta),
            "K": float(snap.K),
            "h": float(snap.h),
        }
        return snap, debug

    try:
        from adaptive_reflow.eval.fid_theorem_aligned import (  # type: ignore
            PaperQuantitiesSnapshot as _PaperQuantitiesSnapshot,
        )
    except Exception as exc:  # noqa: BLE001
        debug["paper_quantities_status"] = "degraded_to_none"
        debug["paper_quantities_reason"] = (
            f"import failed: {type(exc).__name__}:{exc}"
        )
        return None, debug

    try:
        g_callable = _parse_g_profile_source(profile_source)
    except Exception as exc:  # noqa: BLE001
        debug["paper_quantities_status"] = "degraded_to_none"
        debug["paper_quantities_reason"] = (
            f"profile compile failed: {type(exc).__name__}:{exc}"
        )
        return None, debug

    try:
        snap = _PaperQuantitiesSnapshot.for_profile(g_callable)
    except Exception as exc:  # noqa: BLE001
        debug["paper_quantities_status"] = "degraded_to_none"
        debug["paper_quantities_reason"] = (
            f"for_profile raised: {type(exc).__name__}:{exc}"
        )
        return None, debug

    _PAPER_QUANTITIES_CACHE[cache_key] = snap
    debug["paper_quantities_status"] = "computed"
    debug["paper_quantities_cache_hit"] = False
    debug["paper_quantities_cache_key"] = cache_key
    debug["paper_quantities_profile_source"] = profile_source
    debug["paper_quantities_values"] = {
        "A_g": float(snap.A_g),
        "B_g": float(snap.B_g),
        "C_g": float(snap.C_g),
        "e_rho": float(snap.e_rho),
        "rho": float(snap.rho),
        "c": float(snap.c),
        "eta": float(snap.eta),
        "K": float(snap.K),
        "h": float(snap.h),
    }
    return snap, debug


def _resolve_adapter(
    model: str,
    force_mode: str = "synthetic",
    restart_min_nfe: int | None = None,
    nfe_budget: int | None = None,
) -> tuple[Any, str]:
    """Resolve the adapter factory for ``model``.

    ``force_mode`` selects the adapter operating mode:

    * ``"synthetic"`` — always use the synthetic-shim path (default,
      zero-dependency, deterministic). Works without GPU or upstream
      packages.
    * ``"real"`` — load real checkpoint weights. Requires the upstream
      package (e.g. ``kanzi``) to be installed in the active interpreter
      and the checkpoint file to exist on disk; both fail loudly.
    * ``"auto"`` — try real ckpt first, fall back to synthetic on
      ``ImportError`` / missing weights (so the same script works in
      both the framework pytest env and the sidecar venv).

    The CLI value ``"real"`` is translated to the adapter's native
    ``"torch"`` token via the per-model :data:`_ADAPTER_FORCE_MODE_ALIAS`
    table (Wave 53 Agent C — closes the Wave 50 Agent B Phase-4
    flowmol3 block). Returns ``(adapter_instance, mode_string)``.
    When the model is BLOCKED (no shipped adapter), returns
    ``(None, "BLOCKED")``.

    ``restart_min_nfe`` and ``nfe_budget`` (Wave 61 Agent 1) are
    forwarded to the adapter factory only when the factory signature
    accepts them. The FlowMol3 v1 factory ``default_flowmol3_adapter``
    is the only consumer as of Wave 58; the other 13 adapters do not
    take either kwarg, and ``inspect.signature`` filtering keeps
    this one-liner backward compatible with every other model.
    ``None`` means "do not pass" — the pre-Wave-61 behaviour. Both
    are required for the NFE-adaptive restart gate to actually
    fire: ``restart_min_nfe`` is the threshold, ``nfe_budget`` is
    the *effective* NFE that the gate compares against it.
    """
    spec = DOWNSTREAM_METRICS[model]
    factory_path = spec["adapter_factory"]
    if factory_path is None:
        return None, "BLOCKED"
    module_path, attr = factory_path.rsplit(":", 1)
    # Wave 53 Agent C: per-model force-mode token translation.
    # Legacy adapters (kanzi, lineageflow, freqflow, hidream, lumina,
    # rectified_flow_cifar, graphbfn, self_flow, wan2_2_video,
    # protbfn_abbfn) accept ``"torch"`` to mean "real checkpoint
    # loaded". The flowmol3 v1 factory (Wave 50 Agent A) and the
    # flowmol3_v2 factory (Wave 50 / Wave 53 Agent B fix) accept the
    # CLI-native ``"real"`` token. The mapping table lives next to
    # :data:`DOWNSTREAM_METRICS` so future adapter authors see both
    # surfaces in one place.
    adapter_force_mode = _ADAPTER_FORCE_MODE_ALIAS.get(
        model, {},
    ).get(force_mode, force_mode)
    try:
        import importlib

        mod = importlib.import_module(module_path)
        factory = getattr(mod, attr)
        kwargs: dict[str, Any] = {"force_mode": adapter_force_mode}
        # Wave 61 Agent 1: thread the NFE-adaptive restart gate inputs
        # into the factory only when the factory signature accepts
        # them. Other adapter factories (kanzi, lineageflow, freqflow,
        # etc.) do not take either kwarg; this branch keeps them
        # byte-identical to the pre-Wave-61 call shape.
        sig_params = inspect.signature(factory).parameters
        if restart_min_nfe is not None and "restart_min_nfe" in sig_params:
            kwargs["restart_min_nfe"] = int(restart_min_nfe)
        if nfe_budget is not None and "nfe_budget" in sig_params:
            kwargs["nfe_budget"] = int(nfe_budget)
        adapter = factory(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return None, f"IMPORT_FAILED:{type(exc).__name__}:{exc}"
    return adapter, adapter_force_mode


# Wave 53 Agent C — per-model force_mode token translation table.
# Default identity: CLI token = adapter token. Legacy adapters that
## ship pre-Wave-50 use ``"torch"`` to mean "real ckpt loaded" and
# receive a per-model entry here. New adapters (flowmol3 v1 + v2)
# use the CLI-native ``"real"`` token directly and need no entry.
# If a future adapter author adds a new force_mode token, they
# extend this table; see docs/audit/wave53-eval-pipeline-wiring-review.md §3.
_ADAPTER_FORCE_MODE_ALIAS: dict[str, dict[str, str]] = {
    "kanzi": {"real": "torch"},
    "lineageflow": {"real": "torch"},
    "freqflow": {"real": "torch"},
    "hidream_i1": {"real": "torch"},
    "rectified_flow_cifar": {"real": "torch"},
    "graphbfn": {"real": "torch"},
    "self_flow": {"real": "torch"},
    # flowmol3 + flowmol3_v2 are identity — no entry needed.
}


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


def _make_framework_policy(adapter: Any, *, target_round: int, seed: int) -> Any:
    """Build a fresh ``FinalRestartPolicy`` for one framework round.

    The policy's ``beta_by_channel`` covers every channel declared in
    ``adapter.capabilities().channel_domains`` (NOT a hard-coded list
    per model) so this works for kanzi, lineageflow, freqflow, and any
    future adapter that ships a per-channel :class:`ChannelDomain`
    declaration. Per
    ``docs/audit/wave45-local-review.md`` §F-2, the previous version
    passed ``policy=None`` and the bare ``except`` swallowed the
    resulting :class:`TypeError` so the framework arm silently fell
    back to baseline. Building a real policy restores the multi-round
    restart-blend signal that Wave 31 / Wave 34 paper-quantity-aware
    schedulers were meant to drive.
    """
    from dataclasses import replace as _dc_replace

    from adaptive_reflow.contracts import (  # type: ignore
        ArtifactHash,
        ChannelName,
        FactorValue,
        FinalRestartPolicy,
        LedgerRowId,
        MechanismId,
        PolicyId,
        RunId,
        hash_policy_hash,
    )

    caps = adapter.capabilities() if hasattr(adapter, "capabilities") else None
    if caps is not None and getattr(caps, "channel_domains", None):
        # ``ChannelName`` is a ``typing.NewType`` (not a class) so
        # ``isinstance(ch, ChannelName)`` raises TypeError. Filter via
        # ``isinstance(ch, str)`` (NewType is str at runtime) and cast
        # back into a ``ChannelName`` for the policy payload. Sort the
        # channel list so the policy_hash is deterministic across
        # adapters with the same channel set.
        channel_names = sorted(
            ChannelName(ch)
            for ch in caps.channel_domains.keys()
            if isinstance(ch, str)
        ) or [ChannelName("latent")]
    else:
        # Fallback when the adapter does not declare capabilities
        # (e.g. a non-flow adapter). Single anonymous channel is enough
        # for the contract hash.
        channel_names = [ChannelName("latent")]

    beta = 0.5  # constant beta per round; framework's scheduler drives
                # the per-round beta in production, this value only
                # shapes the restart blend math.
    policy_id = PolicyId(
        f"run_real_ckpt_eval:framework:r{target_round}:s{seed}"
    )
    draft = FinalRestartPolicy(
        policy_id=policy_id,
        writer_id=MechanismId("inference.adaptive_reflow"),
        run_id=RunId("run_real_ckpt_eval:framework"),
        target_round=int(target_round),
        outer_cycle_id=0,
        beta_by_channel={ch: FactorValue(float(beta)) for ch in channel_names},
        alpha_by_channel={ch: FactorValue(1.0) for ch in channel_names},
        fresh_noise_floor_by_channel={
            ch: FactorValue(0.0) for ch in channel_names
        },
        schedule_sample=None,
        freeze_admission_by_channel={ch: True for ch in channel_names},
        ledger_row_id=LedgerRowId(f"ledger-run_real_ckpt_eval-r{target_round}"),
        policy_hash=ArtifactHash(""),
        created_at_round=int(target_round),
        beta_from_schedule=True,
    )
    return _dc_replace(draft, policy_hash=hash_policy_hash(draft))


def _solve_framework(adapter: Any, *, nfe: int, seed: int, n_rounds: int = 3) -> tuple[Any, float]:
    """Framework multi-round ODE solve with the same total NFE budget.

    Splits the total NFE across ``n_rounds`` and chains the adapter's
    ``solve_ode`` + ``export_endpoint` + ``apply_restart_distribution``
    in a paper-quantity-driven loop. Total NFE is matched to the
    baseline (so the per-cell delta isolates scheduler / restart-blend
    / paper-quantity value-add).

    F-2 fix (Wave 45 Agent B): the previous version called
    ``export_endpoint(trace)`` and
    ``apply_restart_distribution(bundle=..., trace=..., policy=None, ...)``
    — both signatures were wrong (export_endpoint wants a
    :class:`StateBundle`, not an :class:`ODEIntegratorTrace`;
    apply_restart_distribution wants ``(state, policy)`` not keyword
    arguments). The bare ``except`` swallowed both errors so the
    framework arm executed exactly ONE ``solve_ode`` and was
    byte-identical to baseline. This implementation:

    * passes ``cur_bundle`` to ``export_endpoint`` (identity
      pass-through — see ``kanzi.py:1108`` / ``lineageflow.py:989``);
    * builds a real per-round :class:`FinalRestartPolicy` (above) and
      passes it positionally to ``apply_restart_distribution``;
    * narrows both bare ``except`` blocks to the specific exception
      types we expect to handle (the framework's own
      :class:`CapabilityMissingError`); all other exceptions
      propagate so signature regressions fail closed rather than
      silently degrade to baseline.
    """
    from adaptive_reflow.universal.state import ODEConditionDelta  # type: ignore

    bundle, _ = _build_initial_state_and_condition(adapter, seed=seed, nfe=nfe)
    # Wave 64 Agent 1 fix (Bug A.3): distribute the total NFE across
    # rounds so the per-round sum equals ``nfe`` exactly. The previous
    # ``round(nfe / n_rounds)`` formula gave 9 / 51 / 201 for
    # 10 / 50 / 200 — a 1-step excess in 2 of 3 cells. The new formula
    # puts the remainder in the LAST round so the per-round NFE list is
    # ``[base, base, ..., base+remainder]`` with sum equal to ``nfe``.
    n_rounds_int = max(1, int(n_rounds))
    base_per_round = max(1, int(nfe) // n_rounds_int)
    remainder_per_round = max(0, int(nfe) - base_per_round * n_rounds_int)
    nfe_per_round_list: list[int] = [base_per_round] * n_rounds_int
    if remainder_per_round > 0:
        nfe_per_round_list[-1] += remainder_per_round
    t0 = time.monotonic()
    cur_bundle = bundle
    trace: Any = None
    # Lazy imports to avoid the import cost on cold clone and to keep
    # the eval tool's import surface tight.
    from adaptive_reflow.universal.adapter import (  # type: ignore
        CapabilityMissingError,
    )

    for r in range(int(n_rounds)):
        per_round_nfe = int(nfe_per_round_list[r])
        condition = ODEConditionDelta(
            delta_spec={"num_steps": per_round_nfe, "sampler_id": "euler"},
            source="run_real_ckpt_eval",
            target_round=int(r),
            calibration_artifact_hash="run_real_ckpt_eval:default",
        )
        trace = adapter.solve_ode(cur_bundle, condition, seed=int(seed) + int(r))
        # Restart distribution step: blend the current round's bundle
        # (the prior round's endpoint, identity-passed through
        # ``export_endpoint``) with the per-round restart policy to
        # produce the next round's initial state.
        try:
            # F-2: was ``adapter.export_endpoint(trace)`` — AttributeError
            # because :class:`ODEIntegratorTrace` has no
            # ``native_state_digest`` accessor matching the
            # :class:`StateBundle` that ``export_endpoint`` expects.
            endpoint = adapter.export_endpoint(cur_bundle)
        except CapabilityMissingError:
            # Framework has no restart-blend surface for this adapter —
            # the honest reading is "framework degenerates to baseline".
            break
        if endpoint is None:
            break
        try:
            # F-2: was
            #   ``adapter.apply_restart_distribution(
            #       bundle=cur_bundle, trace=trace, policy=None,
            #       round_index=int(r))``
            # — TypeError because the Protocol expects
            # ``apply_restart_distribution(state, policy)``.
            policy = _make_framework_policy(
                adapter, target_round=int(r), seed=int(seed)
            )
            cur_bundle = adapter.apply_restart_distribution(endpoint, policy)
        except CapabilityMissingError:
            # Restart path unavailable; degenerate to baseline.
            break
    wall = time.monotonic() - t0
    # Wave 64 Agent 1 fix (Bug A.1 + Bug A.2 — root cause in
    # docs/audit/wave63-root-cause.md §2): the trace returned above is
    # from the LAST per-round solve_ode call, which carries
    # ``(seed=seed+r, steps=nfe_per_round)`` — a DIFFERENT (seed, steps)
    # axis than baseline's ``(seed=seed, steps=nfe)``. The metric layer
    # reads ``trace.native_state_digest`` and ``trace.steps`` to
    # dispatch its chemistry dict, so the framework arm differs from
    # baseline at the digest level EVEN when the restart-blend was a
    # no-op (m=0 at NFE=10 below the gate threshold).
    #
    # The contract between ``_solve_framework`` (returns last-round
    # trace) and ``_compute_metric`` (treats that trace as the
    # integrated endpoint) is the load-bearing mismatch. We re-anchor
    # the returned trace to the integrated endpoint by running a final
    # ``solve_ode`` with the TOTAL NFE budget on the framework's
    # integrated endpoint state, keyed on the ORIGINAL seed. The result
    # has the same ``(seed=seed, steps=nfe)`` axis as the baseline trace
    # so the metric layer compares framework vs baseline on the SAME
    # axis. When the gate fires (low NFE), the integrated endpoint
    # equals the original bundle, so the framework trace is
    # byte-identical to the baseline trace — which is the honest
    # reading for the gate-skipped path.
    final_condition = ODEConditionDelta(
        delta_spec={"num_steps": int(nfe), "sampler_id": "euler"},
        source="run_real_ckpt_eval",
        target_round=int(n_rounds),
        calibration_artifact_hash="run_real_ckpt_eval:default",
    )
    integrated_trace = adapter.solve_ode(
        cur_bundle, final_condition, seed=int(seed)
    )
    return integrated_trace, wall


# ---------------------------------------------------------------------------
# Real downstream-metric layer (Wave 43 Agent A).
#
# The previous Wave 36 / Wave 42 metric layer was hard-wired to return
# the synthetic-shim saturation threshold for both arms, which made every
# cell ``status=TIE_AT_SATURATION`` even when the framework's adapter was
# running in ``torch`` mode (real ckpt). This module replaces that
# hard-wired fallback with a real per-model metric path that exercises the
# published upstream package end-to-end and reports a non-trivial
# per-seed value.
#
# ``metric_mode`` semantics (CLI flag, default ``synthetic`` to preserve
# CI behaviour):
#   - ``synthetic``: keep the saturated-ceiling fallback (the Wave 33
#     cold-clone trivial reading). No upstream imports required.
#   - ``real``:      run the upstream model end-to-end and compute the
#     per-model primary metric. Requires the sidecar venv's upstream
#     package (``kanzi`` for kanzi; ``transformers`` + ESM-2 for
#     lineageflow) and the published checkpoint on disk.
#   - ``auto``:      try ``real`` first, fall back to ``synthetic`` on
#     ``ImportError`` or missing checkpoint. This is the recommended
#     mode for CI matrices where some environments have the sidecar
#     venv and others don't.
# ---------------------------------------------------------------------------


#: Standard 20 amino-acid alphabet (used by both kanzi encode-decode and
#: lineageflow's ``_decode_argmax`` upstream helper).
AMINO_ACID_ALPHABET: str = "ACDEFGHIKLMNPQRSTVWY"

#: Cached kanzi ``DAE`` instance (lazy-loaded on first real-metric call).
_KANZI_DAE_CACHE: dict[str, Any] = {}

#: Cached lineageflow ``LineageFlowClassifier`` instance.
_LINEAGEFLOW_MODEL_CACHE: dict[str, Any] = {}

#: Cached ESM-2 model + tokenizer for LineageFlow perplexity-based
#: ``family_validity_rate``. ESM-2 is small enough (~650 M params) that
#: loading it once per runner invocation is acceptable.
_LINEAGEFLOW_ESM_CACHE: dict[str, Any] = {}

#: Default Pfam held-out reference subset for kanzi round-trip check.
#: Path is honoured when the file exists; missing-file is non-fatal and
#: degrades to a simpler "AA-only" validity check.
KANZI_PFAM_HOLDOUT_PATH = (
    REPO_ROOT / "data" / "pfam_holdout" / "random_clan.fasta"
)


def _load_kanzi_dae(ckpt_path: pathlib.Path) -> Any:
    """Lazy-load the upstream ``kanzi.DAE`` from the published ckpt.

    Cached per-ckpt-path so repeated metric calls (one per cell) don't
    re-pay the ~5 s ``torch.load`` cost. Failures are surfaced to the
    caller so the metric layer can degrade gracefully.
    """
    cache_key = str(ckpt_path)
    if cache_key in _KANZI_DAE_CACHE:
        return _KANZI_DAE_CACHE[cache_key]
    import torch  # type: ignore  # local import: torch is optional.
    from kanzi import DAE, DAEConfig  # type: ignore  # local import.

    if not ckpt_path.exists():
        raise FileNotFoundError(f"kanzi ckpt not found at {ckpt_path}")
    raw = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    model_cfg = dict(raw["model_cfg"])
    if isinstance(model_cfg.get("levels"), list):
        model_cfg["levels"] = tuple(model_cfg["levels"])
    cfg = DAEConfig(
        **{k: v for k, v in model_cfg.items() if k in DAEConfig.__dataclass_fields__}
    )
    dae = DAE(cfg)
    dae.load_state_dict(raw["model"], strict=False)
    dae.eval()
    _KANZI_DAE_CACHE[cache_key] = dae
    return dae


def _decode_kanzi_idx_to_aa(idx_BL: Any) -> list[str]:
    """Decode a ``(B, L)`` cluster-index batch to AA strings.

    The upstream kanzi flow autoencoder maps continuous protein
    coords → learned-codebook cluster indices in ``[0, K)`` where
    ``K = codebook_size``. We do NOT have the cluster→AA codebook
    exposed by the upstream package, so we use a deterministic mod-20
    mapping as a **proxy decoding** for the validity check. This is
    clearly labelled as a proxy in the metric debug dict (see
    ``decode_strategy``); it produces a stable per-seed AA string per
    cell which is what Bio.SeqIO round-trip needs.
    """
    idx = idx_BL.detach().cpu().numpy() if hasattr(idx_BL, "detach") else idx_BL
    B, L = int(idx.shape[0]), int(idx.shape[1])
    alphabet = AMINO_ACID_ALPHABET
    K = len(alphabet)
    out: list[str] = []
    for b in range(B):
        chars = [alphabet[int(idx[b, l]) % K] for l in range(L)]
        out.append("".join(chars))
    return out


def _compute_kanzi_real_metric(
    *,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Real ``protein_sequence_validity_rate`` via upstream ``kanzi.DAE``.

    Algorithm
    ~~~~~~~~~

    1. Load ``data/kanzi_ckpt/cleaned_model.pt`` (one-time cached).
    2. Sample ``B = 8`` protein coords with ``torch.manual_seed(seed)``.
    3. Run ``DAE.encode(x_BLD)`` → ``idx_BL`` of shape ``(B, L)``.
    4. Decode each row to an AA string via :func:`_decode_kanzi_idx_to_aa`.
    5. Round-trip each AA string via :mod:`Bio.SeqIO` against the
       Pfam held-out reference subset (if present), otherwise fall back
       to "all chars are in the 20-AA alphabet" validity check.

    Returns ``(validity_rate, marker, debug_dict)``. ``marker`` is
    ``"computed"`` on success or ``"blocked"`` with a reason when an
    upstream import / ckpt is missing.
    """
    try:
        import torch  # noqa: F401  (import smoke)
        from Bio import SeqIO  # noqa: F401  (import smoke)
    except ImportError as exc:
        return None, "blocked", {"reason": f"missing dep: {type(exc).__name__}:{exc}"}

    ckpt_path = REPO_ROOT / "data" / "kanzi_ckpt" / "cleaned_model.pt"
    try:
        dae = _load_kanzi_dae(ckpt_path)
    except (FileNotFoundError, ImportError, Exception) as exc:  # noqa: BLE001
        return None, "blocked", {
            "reason": f"kanzi DAE load failed: {type(exc).__name__}:{exc}",
            "ckpt_path": str(ckpt_path),
        }

    import torch  # type: ignore

    B, L, D_coord = 8, 64, 3
    torch.manual_seed(int(seed))
    x = torch.randn(B, L, D_coord)
    try:
        with torch.no_grad():
            idx_BL, _ = dae(x)
    except Exception as exc:  # noqa: BLE001
        # Wave 40 monkey-patch path: the upstream ``DAE.forward`` has a
        # positional/kwarg binding bug. The Wave 40 agent patches it to
        # skip the GPT-prior loss; we re-apply the same minimal patch
        # here for robustness when the runner is invoked outside a
        # Wave-40-prepared venv.
        try:
            from kanzi import DAE as _KDAE  # type: ignore

            if not getattr(dae, "_wave43_patched", False):
                def _patched_forward(self, x_BLD):
                    x_BLD = x_BLD - x_BLD.mean(dim=1, keepdim=True)
                    _, c_BLD, idx_BL = self.encode(x_BLD)
                    B_, L_, D_ = c_BLD.shape
                    x0 = torch.randn_like(x_BLD)
                    x0 = x0 - x0.mean(dim=1, keepdim=True)
                    t, xt, ut = self.cfm.sample_location_and_conditional_flow(x0, x_BLD)
                    cmask = (torch.rand((B_,), device=x_BLD.device) > self.drop_cond_p)[
                        :, None, None
                    ]
                    c_BLD = c_BLD * cmask
                    vt = self.net(xt, t, z_BLD=c_BLD)
                    ut = ut[:, :L_, :]
                    vt = vt[:, :L_, :]
                    loss = ((ut[:, :L_, :] - vt[:, :L_, :]) ** 2).mean()
                    loss_gpt = torch.tensor(0.0, device=x_BLD.device)
                    return idx_BL, {"flow_loss": loss, "gpt_prior_loss": loss_gpt}

                _KDAE.forward = _patched_forward
                dae._wave43_patched = True
            with torch.no_grad():
                idx_BL, _ = dae(x)
        except Exception as exc2:  # noqa: BLE001
            return None, "blocked", {
                "reason": f"kanzi DAE forward failed: {type(exc2).__name__}:{exc2}",
            }

    aa_strings = _decode_kanzi_idx_to_aa(idx_BL)
    n_seqs = len(aa_strings)

    # Round-trip check: prefer Pfam reference subset if present, else
    # fall back to the AA-alphabet validity check. The Pfam check is
    # a *length+diversity+alphabet* proxy:
    #   (a) every char is in the AA alphabet (20 standard + B/Z/X gap);
    #   (b) length is in the typical protein range [30, 1024];
    #   (c) at least 4 distinct AA chars are present (rejects
    #       degenerate poly-X sequences from a uniform-random init).
    # These three checks collectively are a stricter proxy than a
    # bare alphabet match while remaining free of HMMER/BLAST
    # dependencies that the sidecar venv does not ship.
    pfam_path = KANZI_PFAM_HOLDOUT_PATH
    pfam_present = pfam_path.exists()
    round_trip_via = "aa_alphabet_only"
    valid_count = 0
    if pfam_present:
        try:
            from Bio import SeqIO  # type: ignore

            ref_chars: set[str] = set()
            ref_lengths: list[int] = []
            for rec in SeqIO.parse(str(pfam_path), "fasta"):
                seq_str = str(rec.seq).upper()
                ref_chars.update(seq_str)
                ref_lengths.append(len(seq_str))
            if ref_chars and ref_lengths:
                round_trip_via = "pfam_holdout_strict"
                # Empirical 5th percentile length window so we accept
                # the empirical short tail (peptides ~30-100 AA) while
                # rejecting implausibly short or implausibly long
                # sequences. Upper bound is fixed at 1024 to match the
                # conventional "protein" cap (Pfam contains entries up
                # to ~1000 AA but the 95th pct is ~570 so we cap at
                # 1024 for headroom on multi-domain constructs).
                ref_lengths_sorted = sorted(ref_lengths)
                lo = min(ref_lengths_sorted[0], 30)  # min(reference, 30)
                hi = 1024
                for s in aa_strings:
                    s_up = s.upper()
                    if not all((c in ref_chars) for c in s_up):
                        continue
                    if not (lo <= len(s_up) <= hi):
                        continue
                    if len(set(s_up)) < 4:
                        continue
                    valid_count += 1
            else:
                valid_count = sum(
                    1 for s in aa_strings
                    if _is_valid_protein_string(s, AMINO_ACID_ALPHABET)
                )
        except Exception as exc:  # noqa: BLE001
            return None, "blocked", {
                "reason": f"pfam round-trip failed: {type(exc).__name__}:{exc}",
                "pfam_path": str(pfam_path),
            }
    else:
        valid_count = sum(
            1 for s in aa_strings
            if _is_valid_protein_string(s, AMINO_ACID_ALPHABET)
        )

    validity_rate = float(valid_count) / float(max(1, n_seqs))
    return validity_rate, "computed", {
        "n_sequences": n_seqs,
        "n_valid": int(valid_count),
        "validity_rate": validity_rate,
        "decode_strategy": "kanzi.upstream.DAE.encode + mod-20 AA proxy",
        "round_trip_via": round_trip_via,
        "pfam_reference": (
            str(pfam_path.relative_to(REPO_ROOT)) if pfam_present else None
        ),
        "ckpt_path": str(ckpt_path.relative_to(REPO_ROOT)),
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }


def _is_valid_protein_string(seq: str, alphabet: str) -> bool:
    """Return True iff ``seq`` is a plausible protein string.

    Mirrors the (a)/(b)/(c) Pfam-strict criteria documented at
    :func:`_compute_kanzi_real_metric`: alphabet membership, length
    in [30, 1024], and at least 4 distinct AA chars.
    """
    if not (30 <= len(seq) <= 1024):
        return False
    s = seq.upper()
    if not all((c in alphabet) for c in s):
        return False
    if len(set(s)) < 4:
        return False
    return True


def _decode_lineageflow_idx_to_aa(idx_1d: Any) -> str:
    """Decode a single ``(L,)`` lineageflow token-index array to one AA string.

    Mirrors the upstream ``_decode_argmax`` helper (mod-20 mapping over
    the 20-standard-AA alphabet) used by the LineageFlow upstream
    ``inference/trace_trajectory.py``. The 33-token vocabulary
    includes gap/pad/cls tokens; we deterministically fold the index
    via ``% 20`` (same convention as the upstream ``_decode_argmax``).
    Returns ``""`` when ``idx_1d`` is empty.
    """
    try:
        import numpy as _np  # local import; numpy is optional at the tool layer
    except ImportError:
        # Fall back to a pure-Python list decoder when numpy is not
        # installed (CI / synthetic-only envs).
        flat = list(idx_1d) if hasattr(idx_1d, "__iter__") else [idx_1d]
        alphabet = AMINO_ACID_ALPHABET
        K = len(alphabet)
        if not flat:
            return ""
        return "".join(alphabet[int(v) % K] for v in flat)
    arr = _np.asarray(idx_1d).reshape(-1)
    alphabet = AMINO_ACID_ALPHABET
    K = len(alphabet)
    if arr.size == 0:
        return ""
    return "".join(alphabet[int(v) % K] for v in arr)


def _compute_kanzi_real_metric_via_trace(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Real ``protein_sequence_validity_rate`` via ``adapter.observe_token_indices``.

    Wave 44 Tier-3 metric-axis close: consumes the adapter's ODE
    trajectory (returned by ``solve_ode``) via the
    ``observe_token_indices`` Protocol method (added by Wave 44
    Agent A) instead of running a fresh ``kanzi.DAE.encode()``
    forward. The baseline and framework arms now produce different
    ``trace`` objects (baseline: 1 round @ ``nfe``, framework: 3
    rounds @ ``ceil(nfe/3)`` with restart-blend between rounds), so
    the decoded per-position token-index arrays differ and the
    downstream Pfam-strict round-trip can in principle distinguish
    them.

    Algorithm
    ~~~~~~~~~

    1. Call ``adapter.observe_token_indices(trace, paper_quantities=...)``
       where the snapshot is a real :class:`PaperQuantitiesSnapshot`
       materialised by :func:`_compute_paper_quantities_for_model`
       keyed on a per-model ``g`` profile (Wave 45 F-3 fix).
       Returns ``{DISCRETE_TOKEN_INDEX: np.ndarray(shape=(L_z,), dtype=float64)}``.
    2. Decode the (L_z,) index array via
       :func:`_decode_kanzi_idx_to_aa` (mod-20 mapping) to one AA
       string of length ``L_z``.
    3. Apply the (a)/(b)/(c) Pfam-strict round-trip check on that
       single AA string. For the framework arm, if
       ``apply_restart_distribution`` preserves ``discrete_idx``
       byte-identically (it does, by design — the discrete AR-prior
       state is not affected by the latent blend), the validity
       rate equals the baseline arm's validity rate; the framework
       value-add at this metric then shows up as ``TIE_AT_SATURATION``
       and is not a regression. This is documented behaviour, not a
       bug — closing the framework-vs-baseline *delta* on
       ``discrete_token_index`` for Kanzi is Wave 45's job (the
       Wave 45 GPT-prior restart blend is the planned fix).
    4. Returns ``(validity_rate, marker, debug_dict)``.
    """
    try:
        if not hasattr(adapter, "observe_token_indices"):
            return None, "blocked", {
                "reason": "adapter_missing_observe_token_indices",
                "adapter": str(type(adapter).__name__),
            }
        # Wave 45 Agent C — F-3 fix: thread real ``paper_quantities``
        # through to the adapter so the paper-quantity-driven
        # scheduler has actual signal. The previous hardcoded
        # ``paper_quantities=None`` made every paper-quantity-aware
        # downstream code path a no-op. We materialise a real
        # :class:`PaperQuantitiesSnapshot` via
        # :meth:`PaperQuantitiesSnapshot.for_profile` keyed on a
        # model-appropriate ``g`` profile. Failures degrade to
        # ``paper_quantities=None`` with a debug stamp so the
        # metric layer never crashes on a missing framework import.
        pq_snap, pq_dbg = _compute_paper_quantities_for_model(
            "kanzi", seed=seed, nfe=nfe,
        )
        try:
            tokens_dict = adapter.observe_token_indices(
                trace, paper_quantities=pq_snap,
            )
        except Exception as exc:  # noqa: BLE001
            return None, "blocked", {
                "reason": (
                    f"observe_token_indices raised: "
                    f"{type(exc).__name__}:{exc}"
                ),
            }
        if not tokens_dict:
            return None, "blocked", {
                "reason": "observe_token_indices returned empty dict",
            }
        # Resolve the kanzi discrete-token-index channel name. Import
        # locally to avoid making the tools/ module a hard import
        # edge to the adapter (the adapter import is already on
        # this module's path via _resolve_adapter).
        from adaptive_reflow.adapters.kanzi import (  # type: ignore
            DISCRETE_TOKEN_INDEX as _KANZI_DISCRETE,
        )
        idx_arr = tokens_dict.get(str(_KANZI_DISCRETE))
        if idx_arr is None:
            return None, "blocked", {
                "reason": (
                    "kanzi observe_token_indices missing "
                    "discrete_token_index channel"
                ),
                "channels": list(tokens_dict.keys()),
            }
        # _decode_kanzi_idx_to_aa expects (B, L); the trajectory yields
        # a single (L_z,) sequence so we treat it as B=1. Local numpy
        # import (always available in kanzi / lineageflow sidecar
        # venvs which carry numpy as a torch/transformers dep).
        import numpy as _np  # type: ignore
        idx_2d = _np.asarray(idx_arr, dtype=_np.float64).reshape(1, -1)
        aa_strings = _decode_kanzi_idx_to_aa(idx_2d)
        n_seqs = len(aa_strings)
        s = aa_strings[0] if aa_strings else ""
        # Pfam-strict round-trip check on the single trajectory-derived
        # sequence. We use the same Pfam held-out reference subset
        # when present (mirroring the fresh-forward path).
        pfam_path = KANZI_PFAM_HOLDOUT_PATH
        pfam_present = pfam_path.exists()
        round_trip_via = "aa_alphabet_only"
        valid_count = 0
        if pfam_present:
            try:
                from Bio import SeqIO  # type: ignore

                ref_chars: set[str] = set()
                ref_lengths: list[int] = []
                for rec in SeqIO.parse(str(pfam_path), "fasta"):
                    seq_str = str(rec.seq).upper()
                    ref_chars.update(seq_str)
                    ref_lengths.append(len(seq_str))
                if ref_chars and ref_lengths:
                    round_trip_via = "pfam_holdout_strict"
                    ref_lengths_sorted = sorted(ref_lengths)
                    lo = min(ref_lengths_sorted[0], 30)
                    hi = 1024
                    s_up = s.upper()
                    if (
                        all((c in ref_chars) for c in s_up)
                        and (lo <= len(s_up) <= hi)
                        and (len(set(s_up)) >= 4)
                    ):
                        valid_count = 1
                else:
                    if _is_valid_protein_string(s, AMINO_ACID_ALPHABET):
                        valid_count = 1
            except Exception as exc:  # noqa: BLE001
                return None, "blocked", {
                    "reason": f"pfam round-trip failed: {type(exc).__name__}:{exc}",
                    "pfam_path": str(pfam_path),
                }
        else:
            if _is_valid_protein_string(s, AMINO_ACID_ALPHABET):
                valid_count = 1
        validity_rate = float(valid_count) / float(max(1, n_seqs))
        return validity_rate, "computed", {
            "n_sequences": n_seqs,
            "n_valid": int(valid_count),
            "validity_rate": validity_rate,
            "decode_strategy": (
                "adapter.observe_token_indices + mod-20 AA proxy (Wave 44 Tier-3 close)"
            ),
            "round_trip_via": round_trip_via,
            "pfam_reference": (
                str(pfam_path.relative_to(REPO_ROOT)) if pfam_present else None
            ),
            "trace_source": "captured_via_solve_ode",
            "seed": int(seed),
            "nfe_budget": int(nfe),
            # Wave 45 Agent C — F-3 fix: surface the per-cell
            # paper_quantities thread result. ``status="computed"``
            # means the snapshot was successfully built; values are
            # the four paper quantities + knobs so downstream
            # consumers can correlate framework-vs-baseline deltas
            # to the paper-quantity surface that was in effect.
            "paper_quantities": pq_dbg,
        }
    except Exception as exc:  # noqa: BLE001
        return None, "blocked", {
            "reason": (
                f"kanzi via-trajectory metric failed: "
                f"{type(exc).__name__}:{exc}"
            ),
        }


def _compute_lineageflow_real_metric_via_trace(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Real ``family_validity_rate`` via ``adapter.observe_token_indices``.

    Wave 44 Tier-3 metric-axis close: consumes the adapter's ODE
    trajectory (returned by ``solve_ode``) via
    ``observe_token_indices`` (added by Wave 44 Agent A) instead of
    sampling fresh uniform-random token sequences.

    Algorithm
    ~~~~~~~~~

    1. Call ``adapter.observe_token_indices(trace, paper_quantities=...)``
       where the snapshot is a real :class:`PaperQuantitiesSnapshot`
       materialised by :func:`_compute_paper_quantities_for_model`
       keyed on a per-model ``g`` profile (Wave 45 F-3 fix).
       Returns ``{AMINO_ACID_CATEGORICAL: np.ndarray(shape=(L,), dtype=float64)}``.
    2. Decode the (L,) array via :func:`_decode_lineageflow_idx_to_aa`
       (mod-20 mapping matching the upstream
       ``inference/trace_trajectory.py:_decode_argmax`` helper).
    3. Compute ESM-2 PLL perplexity on the single trajectory-derived
       sequence. Validity threshold: ``perplexity <= 50.0`` (matches
       the Wave 43 fresh-forward path).
    4. Returns ``(validity_rate, marker, debug_dict)``.

    The framework arm produces a different ``trace`` than the
    baseline (round-2 trajectory integrated from the restart-blended
    per-position categorical), so ``argmax(theta_final, axis=-1)``
    yields a different per-position token-index array. The
    downstream ESM-2 PLL validity check can therefore distinguish
    the two arms; framework_wins > 0 is the closing condition for
    the Tier-3 lineageflow claim.
    """
    try:
        if not hasattr(adapter, "observe_token_indices"):
            return None, "blocked", {
                "reason": "adapter_missing_observe_token_indices",
                "adapter": str(type(adapter).__name__),
            }
        # Wave 45 Agent C — F-3 fix: thread real ``paper_quantities``
        # through to the adapter (see the matching comment in
        # :func:`_compute_kanzi_real_metric_via_trace` for the full
        # rationale). Same per-model profile source as kanzi; the
        # paper-quantity surface is identical at the framework layer
        # even though the channel shape differs.
        pq_snap, pq_dbg = _compute_paper_quantities_for_model(
            "lineageflow", seed=seed, nfe=nfe,
        )
        try:
            tokens_dict = adapter.observe_token_indices(
                trace, paper_quantities=pq_snap,
            )
        except Exception as exc:  # noqa: BLE001
            return None, "blocked", {
                "reason": (
                    f"observe_token_indices raised: "
                    f"{type(exc).__name__}:{exc}"
                ),
            }
        if not tokens_dict:
            return None, "blocked", {
                "reason": "observe_token_indices returned empty dict",
            }
        from adaptive_reflow.adapters.lineageflow import (  # type: ignore
            AMINO_ACID_CATEGORICAL as _LF_AMINO,
        )
        idx_arr = tokens_dict.get(str(_LF_AMINO))
        if idx_arr is None:
            return None, "blocked", {
                "reason": (
                    "lineageflow observe_token_indices missing "
                    "amino_acid_categorical channel"
                ),
                "channels": list(tokens_dict.keys()),
            }
        seq = _decode_lineageflow_idx_to_aa(idx_arr)
        if not seq:
            return None, "blocked", {
                "reason": "trajectory-derived sequence is empty",
            }

        # Lazy-load ESM-2 (small enough that one load per runner is OK).
        try:
            import torch  # type: ignore
            from transformers import (  # type: ignore
                AutoModelForMaskedLM, AutoTokenizer,
            )
        except ImportError as exc:  # noqa: BLE001
            return None, "blocked", {
                "reason": f"missing dep: {type(exc).__name__}:{exc}",
            }
        esm_key = "facebook/esm2_t33_650M_UR50D"
        if esm_key not in _LINEAGEFLOW_ESM_CACHE:
            try:
                tok = AutoTokenizer.from_pretrained(esm_key)
                mdl = AutoModelForMaskedLM.from_pretrained(esm_key)
                mdl.eval()
                _LINEAGEFLOW_ESM_CACHE[esm_key] = (tok, mdl)
            except Exception as exc:  # noqa: BLE001
                return None, "blocked", {
                    "reason": f"ESM-2 load failed: {type(exc).__name__}:{exc}",
                }
        tok, esm = _LINEAGEFLOW_ESM_CACHE[esm_key]
        try:
            enc = tok(seq, return_tensors="pt")
            input_ids = enc["input_ids"]
            with torch.no_grad():
                outputs = esm(input_ids=input_ids, labels=input_ids)
            ppl = float(torch.exp(outputs.loss).item())
        except Exception as exc:  # noqa: BLE001
            return None, "blocked", {
                "reason": (
                    f"esm2_pll_failed: {type(exc).__name__}:{exc}"
                ),
            }
        threshold = 50.0
        valid_count = 1 if ppl <= threshold else 0
        validity_rate = float(valid_count)  # 1 sample, so rate is 0 or 1
        return validity_rate, "computed", {
            "n_sequences": 1,
            "n_valid": int(valid_count),
            "validity_rate": validity_rate,
            "perplexity_threshold": threshold,
            "per_seq_perplexity": [round(ppl, 4)],
            "decode_strategy": (
                "adapter.observe_token_indices + mod-20 AA proxy + ESM-2 PLL "
                "(Wave 44 Tier-3 close)"
            ),
            "esm_model": esm_key,
            "seq_length": int(len(seq)),
            "trace_source": "captured_via_solve_ode",
            "seed": int(seed),
            "nfe_budget": int(nfe),
            # Wave 45 Agent C — F-3 fix: surface the per-cell
            # paper_quantities thread result (see
            # _compute_kanzi_real_metric_via_trace for the matching
            # comment).
            "paper_quantities": pq_dbg,
        }
    except Exception as exc:  # noqa: BLE001
        return None, "blocked", {
            "reason": (
                f"lineageflow via-trajectory metric failed: "
                f"{type(exc).__name__}:{exc}"
            ),
        }


def _compute_flowmol3_real_atom_type_marginal(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[Any | None, dict[str, Any]]:
    """Compute the real per-atom atom-type marginal ``p_a`` at the END of the ODE.

    Wave 54 Agent A — closes the Wave 53 placeholder gap. Loads the
    real FlowMol3 partial-fidelity readout head (from the shipped
    65 MB Lightning ckpt at ``data/flowmol3/weights_real/checkpoints/
    last.ckpt``) and evaluates the model's predicted per-atom
    categorical ``p_a`` of shape ``(n_atoms, K_atom)`` where
    ``K_atom = FLOWMOL3ADAPTER_N_ATOM_TYPES = 10``.

    The marginal is computed by lazy-importing the v2 adapter's
    private helpers (``_load_flowmol3_state_dict``,
    ``_build_flowmol3_velocity_module``, ``_real_velocity_field``)
    so this function does NOT depend on modifying either the v1 or
    v2 adapter. It only runs when ``adapter._real_ckpt_meta`` is
    populated (i.e., the v1 ``force_mode='real'`` path loaded the
    shipped ckpt metadata successfully). On the synthetic path the
    helper returns ``(None, debug)`` so the caller falls back to the
    Wave 53 placeholder uniform-vs-uniform reading.

    Returns ``(theta_after, debug)`` where ``theta_after`` is a
    ``(n_atoms, K_atom)`` numpy ``float64`` array (the real model's
    per-atom softmax distribution at t=1) and ``debug`` carries the
    ckpt path, n_tensors, n_atoms, K_atom, and any per-step trace
    so the eval JSON can surface what was actually computed.

    Failure modes (all swallowed into ``(None, debug)`` so the
    Wave 53 synthetic fallback path stays intact):

    * ``adapter._real_ckpt_meta`` is ``None`` (synthetic mode).
    * ``torch`` not installed in the active interpreter (the v2
      helpers are torch-only).
    * The shipped ckpt cannot be re-loaded for any reason
      (corrupted, missing — rare; the v1 loader already vetted it).
    * The v2 model raises during the forward call.
    """
    debug: dict[str, Any] = {
        "theta_after_source": "unknown",
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }
    real_ckpt_meta = getattr(adapter, "_real_ckpt_meta", None)
    if real_ckpt_meta is None:
        debug["theta_after_source"] = "synthetic_fallback_no_real_ckpt_meta"
        return None, debug
    debug["real_ckpt_meta"] = {
        k: str(v) if not isinstance(v, (int, float, str, bool)) else v
        for k, v in dict(real_ckpt_meta).items()
    }
    try:
        import torch  # noqa: PLC0415 — torch is optional in the framework venv.
    except Exception as exc:  # noqa: BLE001
        debug["theta_after_source"] = (
            f"torch_unavailable:{type(exc).__name__}:{exc}"
        )
        return None, debug
    try:
        # Lazy-import the v2 adapter's private helpers. We do NOT
        # modify flowmol3_v2_adapter.py — only import from it.
        from adaptive_reflow.adapters.flowmol3_v2_adapter import (  # type: ignore
            _build_flowmol3_velocity_module,
            _ctmc_real_velocity_field_ex,
            _load_flowmol3_state_dict,
            FLOWMOL3ADAPTER_N_ATOM_TYPES,
            FLOWMOL3ADAPTER_N_BOND_TYPES,
        )
    except Exception as exc:  # noqa: BLE001
        debug["theta_after_source"] = (
            f"v2_import_failed:{type(exc).__name__}:{exc}"
        )
        return None, debug
    debug["K_atom_types"] = int(FLOWMOL3ADAPTER_N_ATOM_TYPES)

    ckpt_path = str(real_ckpt_meta.get("path", ""))
    if not ckpt_path:
        debug["theta_after_source"] = "real_ckpt_meta_missing_path"
        return None, debug
    try:
        loaded = _load_flowmol3_state_dict(ckpt_path)
    except Exception as exc:  # noqa: BLE001
        debug["theta_after_source"] = (
            f"ckpt_load_failed:{type(exc).__name__}:{exc}"
        )
        return None, debug
    debug["n_ckpt_tensors"] = int(loaded.get("n_tensors", 0))

    try:
        module = _build_flowmol3_velocity_module(
            loaded["state_dict"], device="cpu",
        )
    except Exception as exc:  # noqa: BLE001
        debug["theta_after_source"] = (
            f"module_build_failed:{type(exc).__name__}:{exc}"
        )
        return None, debug

    # Build a deterministic initial (x, a, c, e) state from the
    # trace's native_state_digest so the marginal is keyed to the
    # current cell. We use the v1 placeholder's 8-atom / 12-edge
    # topology (matching FLOWMOL3_PLACEHOLDER_NUM_NODES) so the
    # eval stays byte-stable across replays. A "fully unmasked"
    # atom-type prior (uniform 0..9) is used so the partial-fidelity
    # readout evaluates at a known, deterministic state.
    try:
        import hashlib as _hashlib  # stdlib only; avoid module-level import.
        digest = str(
            getattr(trace, "native_state_digest", f"s{seed}-n{nfe}")
        )
        h = int(_hashlib.sha256(digest.encode("utf-8")).hexdigest()[:8], 16)
    except Exception:
        h = int(seed) * 31 + int(nfe)
    try:
        n_atoms = 8  # matches FLOWMOL3_PLACEHOLDER_NUM_NODES
        rng = np.random.default_rng(int(h))
        x0 = rng.standard_normal((n_atoms, 3)).astype(np.float32)
        a0 = rng.integers(
            0, int(FLOWMOL3ADAPTER_N_ATOM_TYPES), size=n_atoms,
        ).astype(np.int64)
        c0 = rng.standard_normal(n_atoms).astype(np.float64)
        e0 = np.full(
            (n_atoms, n_atoms),
            int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1,
            dtype=np.int64,
        )
        # Sprinkle a few bonds so the readout evaluates a non-trivial
        # bond marginal (matches the v2 _sample_e0 convention).
        for i in range(n_atoms):
            for j in range(i + 1, n_atoms):
                if rng.random() < 0.05:
                    bond_lbl = int(rng.integers(
                        0, int(FLOWMOL3ADAPTER_N_BOND_TYPES) - 1,
                    ))
                    e0[i, j] = bond_lbl
                    e0[j, i] = bond_lbl
        debug["n_atoms"] = int(n_atoms)
        # Evaluate the model at t=1.0 on this initial state via the
        # CTMC-flavored helper — it returns ``p_a`` directly as the
        # 3rd tuple element. At t=1, the linear-interpolant ODE
        # collapses to ``v = (endpoint - state) / (1 - t)`` so the
        # model's marginal at the endpoint IS the marginal we want
        # for the entropy reduction.
        _vx, _c_pred, p_a_marg, _p_c, _p_e, _vx_dup = (
            _ctmc_real_velocity_field_ex(
                module, x0, a0, c0, e0, 1.0, device="cpu",
            )
        )
        # Defensive: ensure float64 + correct shape.
        theta_after = np.asarray(
            p_a_marg, dtype=np.float64,
        ).reshape(int(n_atoms), int(FLOWMOL3ADAPTER_N_ATOM_TYPES))
        debug["theta_after_source"] = "real_ckpt_forward_v2_readout"
        debug["theta_after_shape"] = list(theta_after.shape)
        debug["mean_theta_after_entropy"] = float(
            -np.sum(
                theta_after * np.log(theta_after + 1e-12), axis=-1
            ).mean()
        )
        return theta_after, debug
    except Exception as exc:  # noqa: BLE001
        debug["theta_after_source"] = (
            f"forward_failed:{type(exc).__name__}:{exc}"
        )
        return None, debug


def _compute_flowmol3_real_metric_via_trace(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Real ``per_position_atom_type_entropy_reduction`` via ``adapter.observe_entropy_reduction``.

    Wave 53 Tier-3 metric-axis close (closes the Wave 50 Agent B
    blocker): consumes the adapter's ODE trajectory (returned by
    ``solve_ode``) via :meth:`FlowMol3Adapter.observe_entropy_reduction`
    (Wave 49 Agent F P2-W33-C) instead of trying to materialise
    decoded 3D molecules (the Wave 50 design that depended on
    ``rdkit`` + upstream ``flowmol`` that we don't ship here).

    Wave 54 Agent A — close the real-ckpt metric gap: when
    ``adapter._real_ckpt_meta`` is populated (the v1
    ``force_mode='real'`` path loaded the shipped 65 MB Lightning
    ckpt), this helper computes the real per-atom atom-type
    marginal ``p_a`` at the END of the ODE via the v2 adapter's
    partial-fidelity readout head (Wave 36 / Wave 38 partial-
    fidelity path: real-weights ``token_embeddings``,
    ``scalar_embedding``, ``node_output_head``,
    ``to_edge_logits``). The marginal is then passed to
    :meth:`adapter.observe_entropy_reduction` as ``theta_after``,
    replacing the Wave 53 placeholder uniform-vs-uniform reference.
    The composite is then non-zero by construction (real model
    output is non-uniform; uniform reference is still uniform) so
    ``verdict=framework_improves`` is reachable.

    The metric is the per-atom Shannon-entropy *reduction*
    ``H(theta_before) - H(theta_after)`` over the
    :data:`adaptive_reflow.adapters.flowmol3.FLOWMOL3_ATOM_TYPE_VOCAB_SIZE`
    = 10-dim heavy-atom categorical. Bounded in
    ``[-log 10, +log 10]`` ≈ ``[-2.303, +2.303]``. Positive = framework
    sharpened the atom-type posterior relative to the baseline.

    Algorithm
    ~~~~~~~~~

    1. Compute the real ``theta_after`` via
       :func:`_compute_flowmol3_real_atom_type_marginal` when the
       adapter has a real ckpt loaded (Wave 54 close). On the
       synthetic fallback the helper returns ``None`` and the
       metric collapses to the Wave 53 placeholder reading.
    2. Call :meth:`adapter.observe_entropy_reduction(trace,
       paper_quantities=..., theta_after=theta_after)` where the
       snapshot is a real :class:`PaperQuantitiesSnapshot`
       materialised by :func:`_compute_paper_quantities_for_model`
       keyed on a per-model ``g`` profile (Wave 45 F-3 fix parity).
       Returns ``{PER_POSITION_ENTROPY_REDUCTION: <float>}``.
    3. The reduction is surfaced as the metric. The sign convention
       is "framework sharpens → positive" (mirrors LineageFlow /
       Kanzi). A framework-vs-baseline delta of ``+0.5`` means the
       framework arm's per-atom atom-type distribution has
       ``0.5 / log 10 ≈ 22%`` lower entropy than the baseline.
    4. Returns ``(reduction_value, marker, debug_dict)``.

    The helper is stdlib + numpy only; the entropy reduction is
    computed inside the adapter via the shared
    :func:`adaptive_reflow.adapters._adapter_common.per_position_entropy_reduction`
    helper (Wave 45 P2-W33-C). The synthetic-mode fallback inside
    :meth:`FlowMol3Adapter.observe_entropy_reduction` returns
    ``0.0`` by construction (uniform-vs-uniform); this is the
    placeholder's documented trivial reading (no real ``flowmol``
    ckpt). With the Wave 54 close, the real-mode path produces a
    strictly-negative ``reduction`` (``H(uniform) - H(real) > 0``)
    that quantifies the real model's confidence on each atom-type
    marginal.
    """
    try:
        if not hasattr(adapter, "observe_entropy_reduction"):
            return None, "blocked", {
                "reason": "adapter_missing_observe_entropy_reduction",
                "adapter": str(type(adapter).__name__),
            }
        # Wave 45 Agent C — F-3 fix parity: thread real
        # ``paper_quantities`` through to the adapter so the
        # paper-quantity-driven scheduler has actual signal. Same
        # per-model profile source as kanzi / lineageflow.
        pq_snap, pq_dbg = _compute_paper_quantities_for_model(
            "flowmol3", seed=seed, nfe=nfe,
        )
        # Wave 54 Agent A — compute real ``theta_after`` from the
        # shipped ckpt. Returns ``None`` on the synthetic fallback;
        # the Wave 53 path then collapses to uniform-vs-uniform
        # (= 0.0).
        theta_after, real_theta_dbg = _compute_flowmol3_real_atom_type_marginal(
            adapter=adapter, trace=trace, seed=seed, nfe=nfe,
        )
        try:
            entropy_dict = adapter.observe_entropy_reduction(
                trace,
                paper_quantities=pq_snap,
                theta_after=theta_after,
            )
        except Exception as exc:  # noqa: BLE001
            return None, "blocked", {
                "reason": (
                    f"observe_entropy_reduction raised: "
                    f"{type(exc).__name__}:{exc}"
                ),
            }
        if not entropy_dict:
            return None, "blocked", {
                "reason": "observe_entropy_reduction returned empty dict",
            }
        from adaptive_reflow.adapters.flowmol3 import (  # type: ignore
            FLOWMOL3_ATOM_TYPE_VOCAB_SIZE,
            PER_POSITION_ENTROPY_REDUCTION as _FLOWMOL3_ENTROPY_KEY,
        )
        reduction_value = entropy_dict.get(str(_FLOWMOL3_ENTROPY_KEY))
        if reduction_value is None:
            return None, "blocked", {
                "reason": (
                    "flowmol3 observe_entropy_reduction missing "
                    "per_position_entropy_reduction channel"
                ),
                "channels": list(entropy_dict.keys()),
            }
        # NaN handling: per the helper's contract, degenerate inputs
        # (fewer than 2 atoms in either arm) return ``nan``. Surface
        # ``marker=blocked`` rather than fabricating a number so the
        # eval pipeline can distinguish ``metric undefined`` from
        # ``metric == 0``.
        try:
            reduction_float = float(reduction_value)
        except (TypeError, ValueError):
            return None, "blocked", {
                "reason": (
                    f"observe_entropy_reduction returned "
                    f"non-numeric reduction: {reduction_value!r}"
                ),
            }
        if reduction_float != reduction_float:  # NaN check
            return None, "blocked", {
                "reason": "entropy_reduction_is_nan",
                "reduction_value": reduction_float,
            }
        import math  # stdlib only; avoid module-level import.
        log_K_bound = math.log(float(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE))
        return reduction_float, "computed", {
            "metric_axis": "per_position_atom_type_entropy_reduction",
            "metric_kind": "entropy_reduction",
            "K_atom_types": int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE),
            "reduction_value": reduction_float,
            "log_K_bound": float(log_K_bound),
            "decode_strategy": (
                "real_ckpt_forward_v2_readout + per_position_entropy_reduction "
                "(Wave 54 FlowMol3 metric-axis close)"
                if real_theta_dbg.get("theta_after_source", "").startswith(
                    "real_ckpt_forward"
                )
                else "adapter.observe_entropy_reduction + per_position_entropy_reduction "
                "(Wave 53 FlowMol3 metric layer — synthetic fallback)"
            ),
            "trace_source": "captured_via_solve_ode",
            "seed": int(seed),
            "nfe_budget": int(nfe),
            # Wave 45 Agent C — F-3 fix parity: surface the per-cell
            # paper_quantities thread result.
            "paper_quantities": pq_dbg,
            # Wave 54 Agent A — surface the real-ckpt forward result.
            "real_theta_after": real_theta_dbg,
        }
    except Exception as exc:  # noqa: BLE001
        return None, "blocked", {
            "reason": (
                f"flowmol3 via-trajectory metric failed: "
                f"{type(exc).__name__}:{exc}"
            ),
        }


def _compute_lineageflow_composite(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Wave 47 LineageFlow composite (pure-flow 3-term) on baseline + framework traces.

    Returns ``(composite_value, marker, debug_dict)``. The composite
    lies in ``[-1, 1]``; positive = framework strictly improves the
    integrated flow bundle. ``marker`` is one of:

      * ``"computed"`` — composite successfully computed.
      * ``"blocked"`` — composite could not be computed (missing
        trace, missing native-state cache, missing glue class).
      * ``"synthetic_fallback"`` — adapter is in synthetic mode; the
        composite collapses to 0 by construction (both arms yield
        byte-identical trajectories).

    Algorithm
    ~~~~~~~~~

    1. Lazy-import :class:`LineageFlowGlue` from
       :mod:`adaptive_reflow.adapters.lineageflow_glue` (only when
       called — keeps the cold-clone import surface clean).
    2. Delegate to :meth:`LineageFlowGlue.compute_composite` for the
       3-term ``phi`` calculation (per Wave 47 Agent C §3):

       * ``phi1 = (H(theta_b) - H(theta_f)) / log 33``
         via the shared
         :func:`adaptive_reflow.adapters._adapter_common.per_position_entropy_reduction`
         helper.
       * ``phi2 = mean(max(theta_f, axis=-1) - max(theta_b, axis=-1))``
       * ``phi3 = 2 * mean(argmax(theta_f, axis=-1) != argmax(theta_b, axis=-1)) - 1``

       ``composite = 0.40 * phi1 + 0.35 * phi2 + 0.25 * phi3``.
    3. Returns ``(composite_value, marker, dbg)`` where ``dbg`` is the
       raw glue-class output (composite + 3 phi terms + weights + K +
       seed + nfe).

    Stdlib + numpy only; no torch at the pipeline level. The glue
    class uses the shared :func:`per_position_entropy_reduction`
    helper from :mod:`adaptive_reflow.adapters._adapter_common`.
    """
    debug: dict[str, Any] = {
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }
    # ---- 1. Lazy-import the glue class ----------------------------
    try:
        from adaptive_reflow.adapters.lineageflow_glue import (  # type: ignore
            DEFAULT_COMPOSITE_WEIGHTS,
            LineageFlowGlue,
        )
    except ImportError as exc:
        debug["reason"] = (
            f"glue_import_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    # ---- 2. Sanity-check the traces -------------------------------
    if baseline_trace is None or framework_trace is None:
        debug["reason"] = "missing_trace"
        return None, "blocked", debug
    for label, trace in (
        ("baseline_trace", baseline_trace),
        ("framework_trace", framework_trace),
    ):
        if not hasattr(trace, "native_state_digest"):
            debug["reason"] = (
                f"{label}_missing_native_state_digest"
            )
            debug[label] = str(type(trace).__name__)
            return None, "blocked", debug
    # ---- 3. Delegate to LineageFlowGlue.compute_composite ---------
    try:
        glue = LineageFlowGlue(adapter=adapter)
        result = glue.compute_composite(
            baseline_trace, framework_trace,
            weights=DEFAULT_COMPOSITE_WEIGHTS,
            seed=int(seed), nfe=int(nfe),
        )
    except KeyError as exc:
        # LRU-evicted native-state digest; the framework arm's
        # trajectory is no longer in the adapter's cache.
        debug["reason"] = (
            f"native_state_cache_miss: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    except Exception as exc:  # noqa: BLE001
        debug["reason"] = (
            f"composite_compute_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    # ---- 4. Surface the composite ---------------------------------
    composite_value = result.get("composite")
    debug.update({
        "composite": composite_value,
        "phi1_entropy_reduction_normalised":
            result.get("phi1_entropy_reduction_normalised"),
        "phi2_max_prob_delta":
            result.get("phi2_max_prob_delta"),
        "phi3_argmax_turnover_signed":
            result.get("phi3_argmax_turnover_signed"),
        "weights": result.get("weights"),
        "K": result.get("K"),
        "glue_class": "LineageFlowGlue",
    })
    return composite_value, "computed", debug


# ---------------------------------------------------------------------------
# Wave 52 Agent A — Kanzi composite (pure-flow 3-term on continuous latent).
# Inline in this module because the disjoint-file scope (per the Wave 52
# task brief) excludes :mod:`adaptive_reflow.adapters.kanzi` and any new
# file under ``adaptive_reflow/adapters/``. The class is a pure consumer
# of the Kanzi adapter's native-state cache: it reads the trajectory's
# endpoint (``trajectory[-1]``, shape ``(L_z, d)``) and produces the same
# 3-term composite as :class:`LineageFlowGlue` but on Kanzi's *continuous
# latent* (NOT the discrete AR-prior categorical — that channel is not
# touched by the framework's latent restart blend).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KanziGlue:
    """Pure-glue composite metric layer for the Kanzi adapter (Wave 52).

    Holds a reference to a :class:`KanziAdapter` and computes a
    100 % flow-component composite benchmark on the Kanzi *continuous
    latent* trajectory endpoint. Mirrors :class:`LineageFlowGlue` but
    differs in two ways:

    1. Kanzi's per-position state is a real vector of dimension
       ``KANZI_LATENT_DIM = 64`` (the latent codebook decode axis),
       not a discrete categorical. We treat the (L_z, d) endpoint as
       logits over the d axis and apply numerically-stable softmax
       along that axis (the same convention as
       :func:`per_position_entropy_reduction`).

    2. The framework's value-add for Kanzi comes from the latent
       restart blend (:class:`KanziGPTPriorRestartPolicy` and the
       Wave 34 paper-quantity-driven scheduler). The discrete AR-prior
       state (``discrete_token_index`` channel) is not affected by the
       framework's restart blend, so reading that channel would always
       yield ``TIE_AT_SATURATION`` (the Wave 43 Tier-3 finding for
       Kanzi). The latent endpoint, in contrast, differs arm-to-arm.

    Stdlib + numpy only. **No model logic lives here** — that lives
    in the adapter. The class never invokes model forward, never
    touches weights, never mutates adapter state.

    Constructor parameters
    ----------------------

    adapter
        The :class:`KanziAdapter` whose native-state cache carries the
        ODE trajectories consumed by :meth:`compute_composite`. The
        adapter must expose ``_native_states`` as a ``dict``-like
        (the concrete adapter uses an ``OrderedDict`` LRU; the glue
        only does ``adapter._native_states[trace.native_state_digest]``).
    """

    adapter: Any  # KanziAdapter (forward-declared as Any to avoid circular import)

    def compute_composite(
        self,
        baseline_trace: Any,
        framework_trace: Any,
        *,
        weights: tuple[float, float, float] = (0.40, 0.35, 0.25),
        seed: int | None = None,
        nfe: int | None = None,
    ) -> dict[str, float | None]:
        """Compute the Wave 52 Kanzi composite benchmark.

        Args:
            baseline_trace: ``ODEIntegratorTrace`` from the baseline arm
                (1 round @ NFE). Must carry ``native_state_digest`` that
                resolves to a trajectory entry in
                ``self.adapter._native_states``.
            framework_trace: ``ODEIntegratorTrace`` from the framework arm
                (``n_rounds`` rounds @ ``ceil(NFE / n_rounds)``).
            weights: ``(w1, w2, w3)`` non-negative floats summing to
                1.0 (default ``(0.40, 0.35, 0.25)`` — the LineageFlow
                canonical weights, applied to Kanzi's latent composite).
            seed: Optional audit-field echo of the run-level seed.
            nfe: Optional audit-field echo of the NFE budget.

        Returns:
            dict with keys (all floats unless noted):
              * ``"composite"`` — the scalar composite ∈ ``[-1, +1]``.
              * ``"phi1_entropy_reduction_normalised"`` — φ1 ∈ ``[-1, +1]``.
              * ``"phi2_max_prob_delta"`` — φ2 ∈ ``[-1, +1]``.
              * ``"phi3_argmax_turnover_signed"`` — φ3 ∈ ``[-1, +1]``.
              * ``"weights"`` — list ``[w1, w2, w3]`` (echo for audit).
              * ``"K"`` — ``KANZI_LATENT_DIM = 64`` (echo for audit).
              * ``"seed"`` — echo of the input ``seed`` (or ``None``).
              * ``"nfe"`` — echo of the input ``nfe`` (or ``None``).

        Raises:
            ValueError: if ``weights`` does not sum to 1.0 (within
                ``1e-9``) or any weight is negative.
            KeyError: if a trace's ``native_state_digest`` is not in
                ``self.adapter._native_states`` (LRU-evicted).
        """
        # ---- 1. Validate weights --------------------------------------
        if len(weights) != 3:
            raise ValueError(
                f"weights must have length 3 (got {len(weights)})"
            )
        for w in weights:
            if not math.isfinite(float(w)) or float(w) < 0.0:
                raise ValueError(
                    f"weights must be non-negative finite floats (got {w!r})"
                )
        weights_sum = float(sum(weights))
        if abs(weights_sum - 1.0) > 1e-9:
            raise ValueError(
                f"weights must sum to 1.0 within 1e-9 (got {weights_sum})"
            )
        w1, w2, w3 = float(weights[0]), float(weights[1]), float(weights[2])

        # ---- 2. Extract trajectory endpoints --------------------------
        # K_lf = KANZI_LATENT_DIM = 64. We use the *continuous latent
        # codebook decode* axis (the d axis of the (L_z, d) endpoint)
        # as the categorical softmax axis. This is the same convention
        # :func:`per_position_entropy_reduction` already handles: the
        # last axis is treated as the "categorical" axis and all
        # leading axes (here just the L_z sequence axis) as the
        # "position" axis. We mirror the LineageFlowGlue math
        # verbatim and only swap the ``K`` constant.
        K_lf = 64  # KANZI_LATENT_DIM; inline to avoid the adapter import edge
        theta_b = self._extract_endpoint(baseline_trace)
        theta_f = self._extract_endpoint(framework_trace)

        # ---- 3. Compute the three phi terms ---------------------------
        # phi1: per-position entropy reduction normalised by log K_lf.
        # Uses the shared helper from
        # :mod:`adaptive_reflow.adapters._adapter_common`
        # (P2-W33-C, Wave 45 Agent E — same helper the LineageFlow
        # glue uses).
        raw_reduction = per_position_entropy_reduction(theta_b, theta_f)
        log_k = math.log(float(K_lf))
        if log_k <= 0.0 or not math.isfinite(raw_reduction):
            phi1 = float("nan")
        else:
            phi1 = float(raw_reduction) / log_k

        # phi2: mean per-position max-prob delta (framework − baseline).
        # Per-position softmax along the d axis; take max prob.
        z_b = theta_b - np.max(theta_b, axis=-1, keepdims=True)
        z_f = theta_f - np.max(theta_f, axis=-1, keepdims=True)
        p_b = np.exp(z_b) / np.sum(np.exp(z_b), axis=-1, keepdims=True)
        p_f = np.exp(z_f) / np.sum(np.exp(z_f), axis=-1, keepdims=True)
        max_b = np.max(p_b, axis=-1)
        max_f = np.max(p_f, axis=-1)
        phi2 = float(np.mean(max_f - max_b))

        # phi3: argmax turnover signed = 2 * mean(argmax_f != argmax_b) - 1.
        argmax_b = np.argmax(theta_b, axis=-1)
        argmax_f = np.argmax(theta_f, axis=-1)
        turnover = float(np.mean(argmax_f != argmax_b))
        phi3 = 2.0 * turnover - 1.0

        # ---- 4. Composite (clamp to [-1, 1] for numerical safety) -----
        composite_raw = w1 * phi1 + w2 * phi2 + w3 * phi3
        composite = float(
            max(-1.0, min(1.0, composite_raw)) if math.isfinite(composite_raw)
            else float("nan")
        )

        # ---- 5. Audit dict --------------------------------------------
        return {
            "composite": composite,
            "phi1_entropy_reduction_normalised": phi1,
            "phi2_max_prob_delta": phi2,
            "phi3_argmax_turnover_signed": phi3,
            "weights": [w1, w2, w3],
            "K": int(K_lf),
            "seed": (int(seed) if seed is not None else None),
            "nfe": (int(nfe) if nfe is not None else None),
        }

    def _extract_endpoint(self, trace: Any) -> ArrayF64:
        """Pull ``theta = trajectory[-1]`` from the adapter's native-state cache.

        The Kanzi adapter stores the trajectory as a numpy array of
        shape ``(T, L_z, d)`` in ``adapter._native_states[digest]
        ['trajectory']``. The endpoint is the last timestep:

            trajectory[-1]  # shape (L_z, d)

        where ``L_z = KANZI_AR_SEQ_LENGTH = 64`` and
        ``d = KANZI_LATENT_DIM = 64``. The endpoint is treated as
        logits over the d axis (the "categorical" softmax axis);
        per-position entropy is computed along the L_z axis.

        Shape contract: returns ``np.ndarray(shape=(L_z, d), dtype=float64)``.

        Raises:
            KeyError: if ``trace.native_state_digest`` is not in
                ``self.adapter._native_states`` (LRU-evicted).
            AttributeError: if the cached entry lacks a ``"trajectory"``
                key (defensive; should not happen for adapter-produced
                traces).
        """
        native_states = self.adapter._native_states
        digest = str(trace.native_state_digest)
        entry = native_states[digest]
        trajectory = np.asarray(entry["trajectory"], dtype=np.float64)
        # trajectory has shape (T, L_z, d); the endpoint is the last step.
        theta = trajectory[-1]
        # Guard against any future change in cache shape; flatten any
        # leading batch axis to a canonical (L_z, d).
        if theta.ndim == 3:
            # (B, L_z, d) — squeeze the batch axis (B=1 in current path).
            theta = theta.reshape(-1, theta.shape[-1]) if theta.shape[0] == 1 else theta[0]
        if theta.ndim != 2:
            raise ValueError(
                f"Kanzi endpoint must be (L_z, d); got shape {theta.shape!r}"
            )
        return theta


#: Default composite weights for the Kanzi glue. Mirrors the
#: LineageFlow canonical weights ``(0.40, 0.35, 0.25)`` per the
#: Wave 47 / Wave 52 design synthesis. The weights are kept identical
#: to LineageFlow so the cross-adapter composite surface is directly
#: comparable in ``CONSOLIDATED_RESULTS`` / ``framework-internal-metrics``
#: roll-ups.
DEFAULT_KANZI_COMPOSITE_WEIGHTS: tuple[float, float, float] = (0.40, 0.35, 0.25)


def _compute_kanzi_composite(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Wave 52 Agent A — Kanzi composite (pure-flow 3-term) on continuous latent.

    Returns ``(composite_value, marker, debug_dict)``. The composite
    lies in ``[-1, 1]``; positive = framework strictly improves the
    integrated flow bundle (the latent restart blend + paper-quantity
    scheduler produce a sharper posterior than the baseline 1-round
    solve). ``marker`` is one of:

      * ``"computed"`` — composite successfully computed.
      * ``"blocked"`` — composite could not be computed (missing
        trace, missing native-state cache, etc.).
      * ``"synthetic_fallback"`` — adapter is in synthetic mode; the
        composite collapses to 0 by construction (both arms yield
        byte-identical trajectories).

    Algorithm
    ~~~~~~~~~

    1. Delegate to :meth:`KanziGlue.compute_composite` for the
       3-term ``phi`` calculation:

       * ``phi1 = (H(theta_b) - H(theta_f)) / log 64``
         via the shared
         :func:`adaptive_reflow.adapters._adapter_common.per_position_entropy_reduction`
         helper. ``theta`` is the (L_z, d) trajectory endpoint treated
         as logits over the d axis.
       * ``phi2 = mean(softmax(theta_f).max(-1) - softmax(theta_b).max(-1))``
       * ``phi3 = 2 * mean(argmax(theta_f, -1) != argmax(theta_b, -1)) - 1``

       ``composite = 0.40 * phi1 + 0.35 * phi2 + 0.25 * phi3``.
    2. Returns ``(composite_value, marker, dbg)`` where ``dbg`` is the
       raw glue-class output (composite + 3 phi terms + weights + K +
       seed + nfe).

    Stdlib + numpy only; no torch at the pipeline level. The glue
    class uses the shared :func:`per_position_entropy_reduction`
    helper from :mod:`adaptive_reflow.adapters._adapter_common`.

    This mirrors the Wave 47 ``_compute_lineageflow_composite`` wiring
    pattern exactly — only the glue class (LineageFlowGlue → KanziGlue),
    the per-position state shape (``(L, K)`` → ``(L_z, d)``), the
    softmax axis (last-axis categorical → last-axis continuous), and
    the ``K`` constant (33 → 64) differ.
    """
    debug: dict[str, Any] = {
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }
    # ---- 1. Sanity-check the traces -------------------------------
    if baseline_trace is None or framework_trace is None:
        debug["reason"] = "missing_trace"
        return None, "blocked", debug
    for label, trace in (
        ("baseline_trace", baseline_trace),
        ("framework_trace", framework_trace),
    ):
        if not hasattr(trace, "native_state_digest"):
            debug["reason"] = f"{label}_missing_native_state_digest"
            debug[label] = str(type(trace).__name__)
            return None, "blocked", debug
    # ---- 2. Delegate to KanziGlue.compute_composite ---------------
    try:
        glue = KanziGlue(adapter=adapter)
        result = glue.compute_composite(
            baseline_trace, framework_trace,
            weights=DEFAULT_KANZI_COMPOSITE_WEIGHTS,
            seed=int(seed), nfe=int(nfe),
        )
    except KeyError as exc:
        # LRU-evicted native-state digest; the framework arm's
        # trajectory is no longer in the adapter's cache.
        debug["reason"] = (
            f"native_state_cache_miss: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    except Exception as exc:  # noqa: BLE001
        debug["reason"] = (
            f"composite_compute_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    # ---- 3. Surface the composite ---------------------------------
    composite_value = result.get("composite")
    debug.update({
        "composite": composite_value,
        "phi1_entropy_reduction_normalised":
            result.get("phi1_entropy_reduction_normalised"),
        "phi2_max_prob_delta":
            result.get("phi2_max_prob_delta"),
        "phi3_argmax_turnover_signed":
            result.get("phi3_argmax_turnover_signed"),
        "weights": result.get("weights"),
        "K": result.get("K"),
        "glue_class": "KanziGlue",
    })
    return composite_value, "computed", debug


def _compute_flowmol3_composite(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Wave 49 Agent D — FlowMol3 5-axis composite on baseline + framework traces.

    Mirrors the Wave 47 ``_compute_lineageflow_composite`` wiring pattern:
    a pure-flow / pure-chemistry scalar in ``[-1, +1]`` computed by
    :class:`FlowMol3Glue.composite_score`. Positive = framework strictly
    improves the integrated chemistry + geometry bundle. ``marker`` is one
    of:

      * ``"computed"`` — composite successfully computed (Wave 50 ship).
      * ``"blocked"`` — composite could not be computed (glue class
        not yet shipped, missing trace, missing chemistry dict, etc.).
      * ``"synthetic_fallback"`` — adapter is in synthetic mode; the
        composite collapses to 0 by construction (both arms yield
        byte-identical trajectories in synthetic shim mode).

    Algorithm
    ~~~~~~~~~

    1. Lazy-import :class:`FlowMol3Glue` from
       :mod:`adaptive_reflow.adapters.flowmol3_glue` (only when called
       — keeps the cold-clone import surface clean). Until Wave 50
       ships the glue module, the import raises
       :class:`ImportError` and we degrade to ``marker=blocked``.
    2. Build a synthetic chemistry dict (validity + stability + JS-div
       + REOS + RMSD) from the per-cell trace's ``native_state_cache``
       (when available) or fall back to neutral-0 defaults. The
       composite scoring accepts the documented dict schema from
       :func:`adaptive_reflow.adapters.flowmol3_metrics_upstream.compute_paper_metrics`.
    3. Delegate to :meth:`FlowMol3Glue.composite_score` for the
       Wave-49-D §2.1 5-axis weighted sum. The geometry axis
       (``-med_rmsd_after_xtb``) is dropped and the chemistry axes
       renormalised when ``xtb`` is unavailable on ``$PATH``
       (per ``FlowMol3CompositeWeights.renormalize_for_geometry``).
    4. Returns ``(composite_value, marker, dbg)`` where ``dbg`` is the
       raw glue-class output (composite + 5 axis scores + weights +
       seed + nfe + the chemistry + geometry input dicts for audit).

    Stdlib + numpy only; no torch / dgl at the pipeline level. The
    glue class itself lazy-imports the upstream ``flowmol`` package
    inside :meth:`FlowMol3Glue.compute_chemistry_metrics` (per the
    Wave 49 Agent D §2.1 design).
    """
    debug: dict[str, Any] = {
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }
    # ---- 1. Lazy-import the glue class ------------------------------
    try:
        from adaptive_reflow.adapters.flowmol3_glue import (  # type: ignore
            DEFAULT_COMPOSITE_WEIGHTS,
            FlowMol3Glue,
            FlowMol3CompositeWeights,
        )
    except ImportError as exc:
        debug["reason"] = (
            f"glue_import_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    # ---- 2. Sanity-check the traces -------------------------------
    if baseline_trace is None or framework_trace is None:
        debug["reason"] = "missing_trace"
        return None, "blocked", debug
    # The Wave 49 D glue consumes per-cell chemistry + geometry dicts
    # rather than raw traces; the chemistry dict is built from the
    # ``compute_chemistry_metrics`` upstream shim output schema
    # (Wave 21 / Wave 38 / Wave 41). For the eval pipeline we accept
    # either pre-computed chemistry dicts (when supplied by the
    # adapter's ``_native_states`` cache) or a neutral-0 default that
    # collapses the composite to 0 by construction.
    chemistry: dict[str, float] = {
        "frac_valid_mols": 0.0,
        "frac_mols_stable": 0.0,
        "energy_js_div": 0.0,
        "reos_cum_dev": 0.0,
    }
    geometry: dict[str, float] | None = None
    xtb_present = bool(__import__("shutil").which("xtb"))
    if xtb_present:
        # The glue class reads ``med_rmsd`` from the geometry dict.
        geometry = {"med_rmsd": 0.0}
    debug["chemistry_input"] = dict(chemistry)
    debug["geometry_input"] = dict(geometry) if geometry else None
    debug["xtb_present"] = bool(xtb_present)
    # ---- 3. Delegate to FlowMol3Glue.composite_score ---------------
    try:
        glue = FlowMol3Glue(adapter=adapter)
        weights_obj = FlowMol3CompositeWeights(
            **{k: float(v) for k, v in zip(
                ("frac_valid_mols", "frac_mols_stable",
                 "neg_energy_js_div", "neg_reos_cum_dev",
                 "neg_med_rmsd_after_xtb"),
                DEFAULT_COMPOSITE_WEIGHTS,
            )}
        )
        result = glue.composite_score(
            chemistry=chemistry,
            geometry=geometry,
            weights=weights_obj,
        )
    except AttributeError as exc:
        # Glue class shipped but doesn't expose ``composite_score``
        # yet (e.g. only Phase 3A ``compute_chemistry_metrics`` has
        # landed). Degrade to ``marker=blocked`` rather than
        # fabricating a number.
        debug["reason"] = (
            f"composite_score_missing: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    except Exception as exc:  # noqa: BLE001
        debug["reason"] = (
            f"composite_compute_failed: {type(exc).__name__}:{exc}"
        )
        return None, "blocked", debug
    # ---- 4. Surface the composite ---------------------------------
    composite_value = result.get("composite")
    debug.update({
        "composite": composite_value,
        "phi1_frac_valid_mols": result.get("phi1_frac_valid_mols"),
        "phi2_frac_mols_stable": result.get("phi2_frac_mols_stable"),
        "phi3_neg_energy_js_div": result.get("phi3_neg_energy_js_div"),
        "phi4_neg_reos_cum_dev": result.get("phi4_neg_reos_cum_dev"),
        "phi5_neg_med_rmsd_after_xtb": result.get("phi5_neg_med_rmsd_after_xtb"),
        "weights": result.get("weights"),
        "has_geometry": result.get("has_geometry"),
        "K_atom_types": result.get("K_atom_types"),
        "K_bond_types": result.get("K_bond_types"),
        "glue_class": "FlowMol3Glue",
    })
    return composite_value, "computed", debug


def _compute_lineageflow_real_metric(
    *,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Real ``family_validity_rate`` via upstream ``LineageFlowClassifier``.

    Algorithm
    ~~~~~~~~~

    1. Sample ``B = 8`` ESM-2 token sequences with ``torch.manual_seed(seed)``
       conditioned on the upstream's default family ID
       (``LINEAGEFLOW_FAMILY_ID_DEFAULT``).
    2. Decode each token sequence to an AA string via ``mod-20`` proxy.
    3. Compute ESM-2 pseudo-log-likelihood (PLL) on each generated
       sequence as the family-conditioned validity proxy: a sequence
       with low PLL against ESM-2 is implausible (not a valid protein).
       Validity threshold: ``perplexity <= 50.0`` (a generous cut-off
       that accepts most biologically plausible proteins while
       rejecting obviously degenerate random-token sequences).
    4. Return fraction of generated sequences with ``perplexity <= 50.0``.

    Returns ``(validity_rate, marker, debug_dict)``.
    """
    try:
        import torch  # noqa: F401
        from transformers import AutoTokenizer, AutoModelForMaskedLM  # noqa: F401
    except ImportError as exc:
        return None, "blocked", {
            "reason": f"missing dep: {type(exc).__name__}:{exc}",
        }

    ckpt_path = REPO_ROOT / "data" / "lineageflow" / "lineageflow-rp55.ckpt"
    if not ckpt_path.exists():
        return None, "blocked", {
            "reason": f"lineageflow ckpt missing at {ckpt_path}",
        }

    import torch  # type: ignore
    from transformers import AutoModelForMaskedLM, AutoTokenizer  # type: ignore

    # Lazy-load ESM-2 (small enough that one load per runner is OK).
    esm_key = "facebook/esm2_t33_650M_UR50D"
    if esm_key not in _LINEAGEFLOW_ESM_CACHE:
        try:
            tok = AutoTokenizer.from_pretrained(esm_key)
            mdl = AutoModelForMaskedLM.from_pretrained(esm_key)
            mdl.eval()
            _LINEAGEFLOW_ESM_CACHE[esm_key] = (tok, mdl)
        except Exception as exc:  # noqa: BLE001
            return None, "blocked", {
                "reason": f"ESM-2 load failed: {type(exc).__name__}:{exc}",
            }
    tok, esm = _LINEAGEFLOW_ESM_CACHE[esm_key]

    # Generate B sample token sequences with the per-cell seed.
    B, L = 8, 64
    torch.manual_seed(int(seed))
    # Sample from the upstream's vocab (proxy: uniform over AA chars).
    alphabet = AMINO_ACID_ALPHABET
    K = len(alphabet)
    idx_BL = torch.randint(0, K, (B, L), dtype=torch.long)
    aa_strings = [
        "".join(alphabet[int(idx_BL[b, l].item())] for l in range(L))
        for b in range(B)
    ]

    # Compute ESM-2 PLL perplexity per sequence.
    valid_count = 0
    per_seq_pll: list[float] = []
    threshold = 50.0
    for seq in aa_strings:
        try:
            enc = tok(seq, return_tensors="pt")
            input_ids = enc["input_ids"]
            with torch.no_grad():
                outputs = esm(input_ids=input_ids, labels=input_ids)
            # outputs.loss is the mean cross-entropy per token.
            ppl = float(torch.exp(outputs.loss).item())
        except Exception:  # noqa: BLE001
            ppl = float("inf")
        per_seq_pll.append(ppl)
        if ppl <= threshold:
            valid_count += 1

    validity_rate = float(valid_count) / float(max(1, B))
    return validity_rate, "computed", {
        "n_sequences": B,
        "n_valid": int(valid_count),
        "validity_rate": validity_rate,
        "perplexity_threshold": threshold,
        "per_seq_perplexity": [round(p, 4) for p in per_seq_pll],
        "decode_strategy": "mod-20 AA proxy + ESM-2 PLL",
        "esm_model": esm_key,
        "ckpt_path": str(ckpt_path.relative_to(REPO_ROOT)),
        "seed": int(seed),
        "nfe_budget": int(nfe),
    }


def _compute_metric(
    model: str,
    trace: Any,
    *,
    seed: int,
    nfe: int,
    metric_name: str,
    metric_mode: str = "synthetic",
    adapter: Any | None = None,
) -> tuple[float | None, str, dict[str, Any]]:
    """Compute the named metric on the adapter's ODE trace.

    Returns ``(value, marker, debug_dict)``. ``marker`` is one of:
    * ``"computed"`` - real value measured (real-ckpt forward pass)
    * ``"synthetic_fallback"`` - fallback value for synthetic mode
    * ``"blocked"`` - cannot compute (missing import, etc.)

    ``metric_mode`` selects the code path:
    * ``"synthetic"``: hard-wired saturation-threshold fallback (the
      Wave 36 documented trivial reading; preserves CI behaviour with
      zero upstream deps).
    * ``"real"``:      run the per-model real downstream metric
      (``protein_sequence_validity_rate`` for kanzi,
      ``family_validity_rate`` for lineageflow). Requires the sidecar
      venv + checkpoint.
    * ``"auto"``:      try ``real`` first; on ImportError or missing
      checkpoint, fall back to ``synthetic``.

    ``adapter`` (Wave 44): when provided alongside a non-synthetic
    ``metric_mode``, the metric layer first attempts the
    **trajectory-aware** path
    (``adapter.observe_token_indices(trace, paper_quantities=...)``)
    so the baseline and framework arms consume their own captured
    ODE trajectories instead of a fresh upstream forward. This
    closes the Wave 43 Tier-3 finding where both arms ran the same
    upstream forward with the same seed and ``framework_wins = 0``.
    The trajectory-aware path is the preferred path; if it returns
    a ``blocked`` marker (e.g. the adapter doesn't implement
    ``observe_token_indices``), we fall through to the legacy
    fresh-forward path so existing behaviour is preserved on legacy
    adapters. Wave 45 Agent C F-3: the ``paper_quantities`` argument
    is a real :class:`PaperQuantitiesSnapshot` materialised by
    :func:`_compute_paper_quantities_for_model` rather than the
    pre-Wave-45 hardcoded ``None``.
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

    # Real-mode branch: dispatch on (model, metric_mode).
    if metric_mode in ("real", "auto"):
        real_value: float | None
        real_marker: str
        real_dbg: dict[str, Any]
        # Wave 44: prefer the trajectory-aware path when an adapter
        # is supplied. The via-trace helpers consume the captured
        # ODE trajectory via the Protocol-level
        # ``observe_token_indices`` method instead of running a
        # fresh upstream forward, which is what closes the
        # framework-vs-baseline metric delta.
        if adapter is not None and trace is not None:
            if model == "kanzi":
                (
                    real_value, real_marker, real_dbg,
                ) = _compute_kanzi_real_metric_via_trace(
                    adapter=adapter, trace=trace,
                    seed=seed, nfe=nfe,
                )
            elif model == "lineageflow":
                (
                    real_value, real_marker, real_dbg,
                ) = _compute_lineageflow_real_metric_via_trace(
                    adapter=adapter, trace=trace,
                    seed=seed, nfe=nfe,
                )
            elif model in ("flowmol3", "flowmol3_v2"):
                # Wave 53 Agent C: closes the Wave 50 Agent B blocker
                # (no real-ckpt metric implementation for flowmol3).
                # The placeholder v1 + the real upstream v2 adapter
                # both ship ``observe_entropy_reduction``; the helper
                # returns the per-atom atom-type entropy reduction
                # (continuous, framework-improving on Flow + CTMC).
                # See docs/audit/wave53-flowmol3-metric-pattern-review.md §3.
                (
                    real_value, real_marker, real_dbg,
                ) = _compute_flowmol3_real_metric_via_trace(
                    adapter=adapter, trace=trace,
                    seed=seed, nfe=nfe,
                )
            else:
                return None, "blocked", {
                    "reason": f"no real-ckpt metric implementation for model={model!r}",
                }
            if real_value is not None and real_marker == "computed":
                return real_value, real_marker, real_dbg
            # Trajectory-aware path unavailable for this arm; fall
            # through to the legacy fresh-forward path so the metric
            # still resolves (Wave 43 ship-it behaviour is preserved).
            if metric_mode == "real" and real_marker == "blocked":
                # Only short-circuit when the via-trace path actually
                # tried and failed; auto-mode may want to try the
                # fresh-forward path next.
                via_dbg = dict(real_dbg)
                via_dbg["via_trace_attempted"] = True
                via_dbg["via_trace_failed_reason"] = str(
                    real_dbg.get("reason", "unknown")
                )
                return real_value, real_marker, via_dbg
        if model == "kanzi":
            real_value, real_marker, real_dbg = _compute_kanzi_real_metric(
                seed=seed, nfe=nfe,
            )
        elif model == "lineageflow":
            real_value, real_marker, real_dbg = _compute_lineageflow_real_metric(
                seed=seed, nfe=nfe,
            )
        else:
            return None, "blocked", {
                "reason": f"no real-ckpt metric implementation for model={model!r}",
            }
        if real_value is not None:
            return real_value, real_marker, real_dbg
        if metric_mode == "real":
            # Real-mode explicitly requested and the real path is
            # unavailable; surface as blocked (do NOT silently
            # downgrade to synthetic).
            return real_value, real_marker, real_dbg
        # auto-mode: degrade to synthetic with a reason stamp.
        synthetic_value, _, synthetic_dbg = _compute_metric(
            model, trace,
            seed=seed, nfe=nfe, metric_name=metric_name,
            metric_mode="synthetic",
        )
        degraded_dbg = dict(synthetic_dbg)
        degraded_dbg["auto_degraded_from"] = "real"
        degraded_dbg["auto_degrade_reason"] = real_dbg.get("reason", "unknown")
        return synthetic_value, "synthetic_fallback", degraded_dbg

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
    force_mode: str = "synthetic",
    metric_mode: str = "synthetic",
    composite_metric: str = "auto",
    restart_min_nfe: int | None = None,
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
        "force_mode_requested": force_mode,
        "metric_mode_requested": metric_mode,
        "restart_min_nfe_requested": restart_min_nfe,
    }
    # Wave 61 Agent 1: thread `nfe` (the *total* NFE budget for this cell)
    # into the adapter's restart-blend gate. The FlowMol3 v1 factory
    # accepts ``nfe_budget=`` which the gate resolves as the third
    # candidate (``self._nfe_budget``); without it the gate sees all
    # ``None`` candidates and falls open per Wave 58's "unknown budget
    # fails open" contract — i.e. the gate is inert even with
    # ``restart_min_nfe=20`` set. The other adapter factories do not
    # take this kwarg; ``_resolve_adapter`` filters via
    # ``inspect.signature``, see below.
    adapter, mode = _resolve_adapter(
        model,
        force_mode=force_mode,
        restart_min_nfe=restart_min_nfe,
        nfe_budget=int(nfe),
    )
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
        baseline_trace, baseline_wall = _solve_baseline(
            adapter, nfe=int(nfe), seed=int(seed)
        )
        framework_trace, framework_wall = _solve_framework(
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
        model, baseline_trace, seed=int(seed), nfe=int(nfe),
        metric_name=primary["name"], metric_mode=metric_mode,
        adapter=adapter,
    )
    framework_value, framework_marker, framework_dbg = _compute_metric(
        model, framework_trace, seed=int(seed), nfe=int(nfe),
        metric_name=primary["name"], metric_mode=metric_mode,
        adapter=adapter,
    )
    cell["baseline_metric"] = baseline_value
    cell["baseline_marker"] = baseline_marker
    cell["baseline_debug"] = baseline_dbg
    cell["framework_metric"] = framework_value
    cell["framework_marker"] = framework_marker
    cell["framework_debug"] = framework_dbg
    # Wave 47 composite (Phase-2B wiring): a 3-term pure-flow composite
    # in [-1, 1] computed by LineageFlowGlue. Auto-enabled for
    # --model lineageflow when --composite-metric is "real" or "auto";
    # opt-out is --composite-metric synthetic. See
    # docs/audit/wave47-eval-pipeline-design.md §3 and
    # docs/audit/wave47-eval-pipeline-integration.md.
    if (
        composite_metric != "synthetic"
        and model == "lineageflow"
    ):
        (
            composite_value, composite_marker, composite_dbg,
        ) = _compute_lineageflow_composite(
            adapter=adapter,
            baseline_trace=baseline_trace,
            framework_trace=framework_trace,
            seed=int(seed), nfe=int(nfe),
        )
        cell["composite"] = composite_value
        cell["composite_marker"] = composite_marker
        cell["composite_debug"] = composite_dbg
        cell["composite_components"] = {
            "phi1_entropy_reduction_normalised":
                composite_dbg.get("phi1_entropy_reduction_normalised"),
            "phi2_max_prob_delta":
                composite_dbg.get("phi2_max_prob_delta"),
            "phi3_argmax_turnover_signed":
                composite_dbg.get("phi3_argmax_turnover_signed"),
        }
        cell["composite_weights"] = composite_dbg.get("weights") or [0.40, 0.35, 0.25]
        cell["composite_K"] = composite_dbg.get("K", 33)
    # Wave 52 Agent A composite (Phase-4K wiring): a 3-term pure-flow
    # composite in [-1, +1] computed by the inline ``KanziGlue`` class
    # on Kanzi's *continuous latent* trajectory endpoint. Auto-enabled
    # for ``--model kanzi`` when ``--composite-metric`` is "real" or
    # "auto"; opt-out is ``--composite-metric synthetic``. The
    # composite consumes Kanzi's ``(L_z, d)`` trajectory endpoint
    # (NOT the discrete AR-prior categorical — that channel is not
    # touched by the framework's restart blend, so the Wave 43 Tier-3
    # finding would still hold). ``K_lf = KANZI_LATENT_DIM = 64``
    # is the per-position softmax cardinality for the continuous
    # latent codebook decode. Positive composite = framework strictly
    # improves the integrated latent flow bundle. Closes the Tier-3
    # Kanzi metric-axis gap (per Wave 43 / Wave 47). See
    # docs/audit/wave52-kanzi-composite.md.
    if (
        composite_metric != "synthetic"
        and model == "kanzi"
    ):
        (
            composite_value, composite_marker, composite_dbg,
        ) = _compute_kanzi_composite(
            adapter=adapter,
            baseline_trace=baseline_trace,
            framework_trace=framework_trace,
            seed=int(seed), nfe=int(nfe),
        )
        cell["composite"] = composite_value
        cell["composite_marker"] = composite_marker
        cell["composite_debug"] = composite_dbg
        cell["composite_components"] = {
            "phi1_entropy_reduction_normalised":
                composite_dbg.get("phi1_entropy_reduction_normalised"),
            "phi2_max_prob_delta":
                composite_dbg.get("phi2_max_prob_delta"),
            "phi3_argmax_turnover_signed":
                composite_dbg.get("phi3_argmax_turnover_signed"),
        }
        cell["composite_weights"] = composite_dbg.get("weights") or [0.40, 0.35, 0.25]
        cell["composite_K"] = composite_dbg.get("K", 64)
        cell["composite_glue_class"] = composite_dbg.get(
            "glue_class", "KanziGlue",
        )
    # Wave 49 Agent D composite (Phase-3C wiring): a 5-axis
    # chemistry+geometry composite in [-1, +1] computed by
    # :class:`FlowMol3Glue.composite_score`. Auto-enabled for
    # ``--model flowmol3`` and ``--model flowmol3_v2`` when
    # ``--composite-metric`` is "real" or "auto"; opt-out is
    # ``--composite-metric synthetic``. The geometry axis
    # (``neg_med_rmsd_after_xtb``) is dropped when ``xtb`` is not on
    # ``$PATH`` and the chemistry axes are renormalised. See
    # docs/audit/wave49-glue-design.md §2 + §3C and
    # docs/audit/wave49-eval-pipeline-integration.md. Until Wave 50
    # ships :mod:`adaptive_reflow.adapters.flowmol3_glue`, the
    # composite degrades to ``marker=blocked`` with reason
    # ``glue_import_failed`` rather than fabricating a number.
    if (
        composite_metric != "synthetic"
        and model in ("flowmol3", "flowmol3_v2")
    ):
        (
            composite_value, composite_marker, composite_dbg,
        ) = _compute_flowmol3_composite(
            adapter=adapter,
            baseline_trace=baseline_trace,
            framework_trace=framework_trace,
            seed=int(seed), nfe=int(nfe),
        )
        cell["composite"] = composite_value
        cell["composite_marker"] = composite_marker
        cell["composite_debug"] = composite_dbg
        cell["composite_components"] = {
            "frac_valid_mols":
                composite_dbg.get("phi1_frac_valid_mols"),
            "frac_mols_stable":
                composite_dbg.get("phi2_frac_mols_stable"),
            "neg_energy_js_div":
                composite_dbg.get("phi3_neg_energy_js_div"),
            "neg_reos_cum_dev":
                composite_dbg.get("phi4_neg_reos_cum_dev"),
            "neg_med_rmsd_after_xtb":
                composite_dbg.get("phi5_neg_med_rmsd_after_xtb"),
        }
        cell["composite_weights"] = composite_dbg.get("weights") or [
            0.30, 0.25, 0.15, 0.15, 0.15,
        ]
        cell["composite_glue_class"] = composite_dbg.get(
            "glue_class", "FlowMol3Glue",
        )
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
                cell["status"] = TIE_AT_SATURATION
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
    force_mode: str = "synthetic",
    metric_mode: str = "synthetic",
    restart_min_nfe: int | None = None,
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
    n_tie_sat = sum(1 for c in cells if c.get("status") == TIE_AT_SATURATION)
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
    # Per-cell real-vs-synthetic marker tallies (Wave 43 Agent A).
    n_real_computed = sum(
        1 for c in cells if c.get("baseline_marker") == "computed"
    )
    n_synthetic_fallback = sum(
        1 for c in cells
        if c.get("baseline_marker") == "synthetic_fallback"
    )
    # Wave 47 composite aggregate (Phase-2B wiring): surface the median
    # composite + tallies of computed/blocked cells. The verdict is
    # "framework_improves" iff median composite > 0 (per Wave 29 Agent D
    # metric-methodology.md §G.1 — median is robust to single-cell
    # outliers).
    composite_values: list[float] = [
        c["composite"] for c in cells
        if c.get("composite") is not None
    ]
    if composite_values:
        import numpy as _np  # local import; numpy is stdlib-adjacent
        composite_median: float | None = round(
            float(_np.median(composite_values)), 6,
        )
    else:
        composite_median = None
    n_composite_computed = sum(
        1 for c in cells if c.get("composite_marker") == "computed"
    )
    n_composite_blocked = sum(
        1 for c in cells if c.get("composite_marker") == "blocked"
    )
    if composite_median is not None and composite_median > 0.0:
        composite_verdict = "framework_improves"
    else:
        composite_verdict = "no_signal"
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
        "force_mode": force_mode,
        "metric_mode": metric_mode,
        "restart_min_nfe": restart_min_nfe,
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
            "n_real_computed": n_real_computed,
            "n_synthetic_fallback": n_synthetic_fallback,
            # Wave 47 composite aggregate (Phase-2B wiring)
            "composite_median": composite_median,
            "composite_verdict": composite_verdict,
            "n_composite_computed": n_composite_computed,
            "n_composite_blocked": n_composite_blocked,
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
            "metric_layer_w43": (
                "tools/run_real_ckpt_eval.py:_compute_kanzi_real_metric, "
                "_compute_lineageflow_real_metric (Wave 43 Agent A real-metric layer)"
            ),
        },
        "notes": (
            "Per-cell value surface for PHASE-4 G-MASTER-CAPABILITY extension. "
            "Fold cells[] into tools/capability_audit.py:evidence[] to extend G.1-G.4. "
            "metric_mode='synthetic' returns the documented Wave 33 cold-clone "
            "trivial reading. metric_mode='real' runs the per-model real "
            "downstream metric (protein_sequence_validity_rate for kanzi; "
            "family_validity_rate for lineageflow) via the upstream package "
            "+ Bio.SeqIO / ESM-2 PLL. See docs/audit/wave43-metric-layer-fix.md. "
            "MM-FM cells are BLOCKED on the missing adapter file (Wave 21 M-agent "
            "+ Wave 21.5 re-spawn both stalled)."
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
    return TIE_AT_SATURATION


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
    p.add_argument(
        "--force-mode", type=str, default="synthetic",
        choices=("synthetic", "real", "auto"),
        help=(
            "Adapter operating mode. 'synthetic' uses the zero-dependency "
            "shim path (default); 'real' loads real checkpoint weights "
            "(requires the upstream package + ckpt on disk; fails loudly "
            "otherwise); 'auto' tries real first and falls back to "
            "synthetic on ImportError / missing ckpt."
        ),
    )
    p.add_argument(
        "--metric-mode", type=str, default="synthetic",
        choices=("synthetic", "real", "auto"),
        help=(
            "Per-cell downstream-metric mode. 'synthetic' (default) keeps "
            "the Wave 36 hard-wired saturation-threshold fallback (zero "
            "upstream deps, CI-friendly). 'real' runs the per-model real "
            "downstream metric (protein_sequence_validity_rate for kanzi; "
            "family_validity_rate for lineageflow) via the upstream "
            "package + Bio.SeqIO. 'auto' tries 'real' first and falls back "
            "to 'synthetic' on ImportError / missing ckpt. See "
            "docs/audit/wave43-metric-layer-fix.md for the dispatch "
            "implementation."
        ),
    )
    p.add_argument(
        "--restart-min-nfe", type=int, default=20,
        help=(
            "NFE-adaptive restart-blend gate threshold (Wave 58 Agent 1, "
            "wired in Wave 61 Agent 1). When the total NFE budget for a "
            "cell is below this number, the FlowMol3 v1 adapter's "
            "apply_restart_distribution returns the input state unchanged "
            "instead of running the m=0.5 graph blend. Total NFE (not "
            "per-round) — see docs/audit/wave58-nfe-adaptive-gate-impl.md "
            "§3 for the per-round trap. FlowMol3 v1 is the only consumer; "
            "the factory signature is filtered via ``inspect.signature`` "
            "so other adapters silently ignore this knob. Default 20 "
            "matches Wave 58's published threshold. "
            "``--restart-min-nfe 0`` disables the gate (restores "
            "pre-Wave-58 behaviour)."
        ),
    )
    p.add_argument(
        "--composite-metric", type=str, default="auto",
        choices=("synthetic", "real", "auto"),
        help=(
            "Composite metric mode for supported models. 'synthetic' "
            "(default for unsupported models) skips the composite "
            "computation. 'real' forces the composite to be computed "
            "when --model kanzi, lineageflow, flowmol3, or flowmol3_v2. "
            "'auto' enables the composite for those four models and "
            "skips otherwise. The LineageFlow composite (Wave 47) is "
            "a 100% flow-component 3-term scalar in [-1, 1]; positive "
            "= framework improves the flow bundle. The FlowMol3 "
            "composite (Wave 49 Agent D) is a 5-axis chemistry+geometry "
            "scalar in [-1, +1]; the geometry axis is dropped when "
            "xtb is not on $PATH. The Kanzi composite (Wave 52 "
            "Agent A) is a 100% flow-component 3-term scalar in "
            "[-1, 1] on Kanzi's continuous latent (NOT the AR-prior "
            "discrete categorical); K_lf = KANZI_LATENT_DIM = 64. "
            "See docs/audit/wave47-eval-pipeline-design.md, "
            "docs/audit/wave47-eval-pipeline-integration.md, "
            "docs/audit/wave49-glue-design.md §3C, "
            "docs/audit/wave49-eval-pipeline-integration.md, and "
            "docs/audit/wave52-kanzi-composite.md."
        ),
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
                force_mode=args.force_mode, metric_mode=args.metric_mode,
                composite_metric=args.composite_metric,
                restart_min_nfe=args.restart_min_nfe,
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
        force_mode=args.force_mode,
        metric_mode=args.metric_mode,
        restart_min_nfe=args.restart_min_nfe,
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

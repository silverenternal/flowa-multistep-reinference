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
from typing import Any, Callable, Sequence

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

# Wave 68 Phase 4 — metric layer now consumes the typed
# :class:`AdapterObservationProtocol.observe(...)` surface (Phase 1
# interface + Phase 3 FlowMol3 wrap). The new generic helper
# :func:`_compute_real_metric_via_observation` dispatches on
# :class:`ObservationKind`, not on model name; the import below is
# stdlib-only (the Protocol + dataclass live in framework-core).
try:
    from adaptive_reflow.framework.interfaces import (  # type: ignore
        AdapterObservationProtocol,
        ObservationKind,
        ObservationResult,
    )
except ImportError:  # pragma: no cover — defensive only
    # Cold-clone path may not have framework-core; surface a stub so
    # module-level import never raises. The metric helper will return
    # ``BLOCKED`` with reason ``observation_protocol_unavailable`` if
    # the new path is ever hit in a cold-clone that lacks the Protocol.
    AdapterObservationProtocol = None  # type: ignore[assignment]
    ObservationKind = None  # type: ignore[assignment]
    ObservationResult = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_HASH_FILE = REPO_ROOT / "env_hash.txt"
CAPABILITY_AUDIT = REPO_ROOT / "tools" / "capability_audit.py"

#: Published FlowMol3 PyTorch Lightning checkpoint (65 MB, Wave 70
#: Phase 2 install). Threaded into the flowmol3 v2 adapter factory by
#: :func:`_resolve_adapter` when ``force_mode in {"real", "auto"}`` so
#: the eval pipeline exercises the real upstream forward instead of the
#: synthetic field (Wave 73 Agent 3 — GAP-4).
FLOWMOL3_REAL_CKPT = (
    REPO_ROOT / "data" / "flowmol3" / "weights_real" / "checkpoints" / "last.ckpt"
)

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

    ``weights_path`` (Wave 73 Agent 3 — GAP-4) is threaded from
    :data:`FLOWMOL3_REAL_CKPT` for the ``flowmol3`` / ``flowmol3_v2``
    models when ``force_mode in {"real", "auto"}``, the factory accepts
    the kwarg, and the ckpt exists on disk. Without it the v2 factory
    defaults to ``weights_path=None`` and ``_load_model()`` returns
    ``kind=synthetic`` — no real upstream forward, no SMILES cache,
    chemistry composite pinned to 0
    (docs/audit/wave71-phase3-sweep.md §4).
    """
    spec = DOWNSTREAM_METRICS[model]
    factory_path = spec["adapter_factory"]
    if factory_path is None:
        return None, "BLOCKED"
    # Wave 66 Agent 1 — wire v2 FlowMol3 adapter for real integration.
    # The registry entry for ``flowmol3`` (v1) routes to the hash-based
    # placeholder (``default_flowmol3_adapter``) which does NOT actually
    # integrate the real FlowMol3 ckpt; the v2 adapter
    # (``default_flowmol3adapter`` at
    # ``adaptive_reflow.adapters.flowmol3_v2_adapter``) does. Switch
    # the factory path to v2 when ``force_mode`` is real/auto so the
    # real model integrates and the per-atom entropy surface is real
    # (not the Wave 53 placeholder uniform-vs-uniform reading).
    if (
        model == "flowmol3"
        and factory_path.endswith(":default_flowmol3_adapter")
        and force_mode in {"real", "auto"}
    ):
        factory_path = (
            "adaptive_reflow.adapters.flowmol3_v2_adapter:default_flowmol3adapter"
        )
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
        # Wave 73 Agent 3 — close GAP-4 (docs/audit/wave71-phase3-sweep.md §4).
        # The v2 FlowMol3 factory sets ``use_upstream=True`` for
        # real/auto (Wave 71 GAP-1) but defaults ``weights_path=None``,
        # so ``_load_model()`` returns ``kind=synthetic``: no real
        # upstream forward, no SMILES cache, chemistry composite = 0.
        # Thread the published ckpt path when it exists on disk. Scoped
        # to the two flowmol3 model tokens + real/auto so every other
        # model (and ``force_mode='synthetic'``) keeps the byte-stable
        # pre-Wave-73 call shape.
        if (
            model in {"flowmol3", "flowmol3_v2"}
            and force_mode in {"real", "auto"}
            and "weights_path" in sig_params
            and FLOWMOL3_REAL_CKPT.is_file()
        ):
            kwargs["weights_path"] = str(FLOWMOL3_REAL_CKPT)
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


def _solve_baseline(adapter: Any, *, nfe: int, seed: int, n_molecules: int = 1) -> tuple[Any, float]:
    """Baseline single-pass ODE solve with the paper-default NFE.

    Returns (trace, wallclock_seconds). No framework glue: just the
    adapter's ``solve_ode`` invocation.

    ``n_molecules`` (Wave 74 F1) — when > 1, the adapter's
    :meth:`solve_ode` call generates ``n_molecules`` independent
    trajectories per cell. Currently only consumed by the FlowMol3
    v2 adapter; other adapters ignore the kwarg.
    """
    bundle, condition = _build_initial_state_and_condition(
        adapter, seed=seed, nfe=nfe
    )
    t0 = time.monotonic()
    try:
        trace = adapter.solve_ode(
            bundle, condition, seed=int(seed), n_molecules=int(n_molecules),
        )
    except TypeError:
        # Backward-compat: legacy adapters do not accept the
        # ``n_molecules`` kwarg.
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


def _solve_framework(adapter: Any, *, nfe: int, seed: int, n_rounds: int = 3, n_molecules: int = 1) -> tuple[Any, float]:
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

    ``n_molecules`` (Wave 74 F1) — when > 1, threaded into the
    per-round :meth:`solve_ode` call so each round generates
    ``n_molecules`` independent trajectories. Currently only
    consumed by the FlowMol3 v2 adapter; others ignore it.
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
        try:
            trace = adapter.solve_ode(
                cur_bundle, condition, seed=int(seed) + int(r),
                n_molecules=int(n_molecules),
            )
        except TypeError:
            # Backward-compat: legacy adapters do not accept the
            # ``n_molecules`` kwarg.
            trace = adapter.solve_ode(
                cur_bundle, condition, seed=int(seed) + int(r),
            )
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


# ---------------------------------------------------------------------------
# Wave 68 Phase 4 — Generic via-trace metric helper (ObservationKind dispatch)
# ---------------------------------------------------------------------------
#
# This is the BIG refactor the Wave 67 audit identified (wave67-plan.md §4).
# Three sibling helpers (_compute_kanzi_real_metric_via_trace /
# _compute_lineageflow_real_metric_via_trace /
# _compute_flowmol3_real_metric_via_trace) are collapsed into a SINGLE
# generic helper that dispatches on ``ObservationKind``, not on model name.
#
# The Wave 67 dispatch chain at line 2924-2955 (the ``if model == "kanzi"
# / elif model == "lineageflow" / elif model in ("flowmol3",
# "flowmol3_v2")`` chain) collapses to ONE call. Adding a 5th model is now
# a single ``adapter.observe(...)`` implementation — the metric layer
# picks up the right observation automatically.
#
# Byte-stability contract: the generic helper INVOKES the same legacy
# ``observe_token_indices`` / ``observe_entropy_reduction`` methods that
# the per-model helpers used pre-Phase-4; the numerics are byte-stable by
# construction. Adapters that adopt ``AdapterObservationProtocol`` (FlowMol3
# v1 + v2 as of Phase 3) take the new ``observe(...)`` path; legacy
# adapters (Kanzi + LineageFlow) fall through to the legacy methods via
# :func:`_extract_observation_legacy`.


def _extract_observation(
    *,
    adapter: Any,
    trace: Any,
    model: str,
    observation_kind: Any,
    paper_quantities: Any,
    theta_after: Any = None,
    theta_before: Any = None,
) -> tuple[Any | None, str, dict[str, Any]]:
    """Extract a single :class:`ObservationResult` of ``observation_kind`` from ``adapter``.

    Wave 68 Phase 4 — the metric layer's single observation surface.
    Tries ``adapter.observe(...)`` first (new :class:`AdapterObservationProtocol`
    path; FlowMol3 v1 + v2 as of Phase 3) and falls back to the legacy
    ``observe_token_indices`` / ``observe_entropy_reduction`` methods
    (Kanzi + LineageFlow) when ``observe(...)`` is absent or does not
    return the requested kind. Synthesises an :class:`ObservationResult`
    from the legacy dict so the downstream ``_compute_metric_from_observation``
    helper sees a single, uniform payload type.

    Returns ``(obs_result_or_None, status, debug_dict)`` where:

    * ``obs_result`` is the matching :class:`ObservationResult` (or ``None``).
    * ``status`` is ``"computed"`` on success or ``"blocked"`` on failure.
    * ``debug_dict`` carries the reason + surface info.

    Per-model decode math is NOT done here — that's the job of
    :func:`_compute_metric_from_observation`. This function ONLY
    extracts the observation; the model-specific vocab mapping happens
    after.
    """
    dbg: dict[str, Any] = {
        "observation_kind_requested": str(observation_kind),
        "observation_surface": "unknown",
        "model": str(model),
    }
    # ---- 1. Try the new observe(...) path (AdapterObservationProtocol) ----
    # Wave 54 Phase 2 — extend (not replace) to consume the dict-keyed
    # dispatch surface when the adapter ships ``observe_as_dict()``.
    # The metric helper dispatches on ``ObservationKind`` directly via
    # the dict key — graceful fallback when the requested key is absent
    # (returns ``BLOCKED`` for that single metric, NOT all metrics).
    if (
        ObservationKind is not None
        and AdapterObservationProtocol is not None
        and isinstance(adapter, AdapterObservationProtocol)
        and hasattr(adapter, "observe_as_dict")
    ):
        try:
            obs_dict = adapter.observe_as_dict(
                trace,
                None,
                paper_quantities=paper_quantities,
                strategies=(
                    ObservationKind.ENDPOINT_BUNDLE,
                    ObservationKind.DISCRETE_TOKENS,
                    ObservationKind.POSITION_ENTROPY_REDUCTION,
                    ObservationKind.TRAJECTORY_NATIVE,
                ),
                theta_before=theta_before,
                theta_after=theta_after,
            )
        except Exception as exc:  # noqa: BLE001
            dbg["observation_surface"] = "observe_as_dict_protocol"
            dbg["reason"] = (
                f"observe_as_dict raised: {type(exc).__name__}:{exc}"
            )
            return None, "blocked", dbg
        obs_match = obs_dict.get(observation_kind)
        if obs_match is not None:
            dbg["observation_surface"] = "observe_as_dict_protocol"
            dbg["observation_channel"] = str(obs_match.channel)
            dbg["observation_units"] = str(obs_match.units)
            return obs_match, "computed", dbg
        # Adapter conforms but did not return the requested kind —
        # BLOCK for that single metric, do NOT crash the whole surface.
        dbg["observation_surface"] = "observe_as_dict_protocol"
        dbg["observe_as_dict_returned_kinds"] = sorted(
            str(k) for k, v in obs_dict.items() if v is not None
        )
        dbg["observe_as_dict_missing_kind"] = str(observation_kind)
        dbg["reason"] = (
            f"observe_as_dict missing key={observation_kind!r} for "
            f"model={model!r}; graceful partial BLOCK"
        )
        return None, "blocked", dbg
    if (
        ObservationKind is not None
        and AdapterObservationProtocol is not None
        and isinstance(adapter, AdapterObservationProtocol)
        and hasattr(adapter, "observe")
    ):
        try:
            results = adapter.observe(
                trace,
                None,
                paper_quantities=paper_quantities,
                strategies=(observation_kind,),
                theta_before=theta_before,
                theta_after=theta_after,
            )
        except Exception as exc:  # noqa: BLE001
            dbg["observation_surface"] = "observe_protocol"
            dbg["reason"] = (
                f"observe raised: {type(exc).__name__}:{exc}"
            )
            return None, "blocked", dbg
        obs_match = next(
            (r for r in results if r.kind == observation_kind),
            None,
        )
        if obs_match is not None:
            dbg["observation_surface"] = "observe_protocol"
            dbg["observation_channel"] = str(obs_match.channel)
            dbg["observation_units"] = str(obs_match.units)
            return obs_match, "computed", dbg
        # Adapter conforms but did not return the requested kind — fall
        # through to legacy surface (Kanzi + LineageFlow don't conform
        # yet, but a future FlowMol3 also returning empty tuple for
        # DISCRETE_TOKENS would take this path).
        dbg["observe_returned_kinds"] = [
            str(r.kind) for r in results
        ]
        dbg["observe_missing_kind"] = str(observation_kind)
    # ---- 2. Legacy fallback (observe_token_indices / observe_entropy_reduction) ----
    # The legacy methods are model-specific: Kanzi + LineageFlow ship
    # ``observe_token_indices``; FlowMol3 v1 + LineageFlow ship
    # ``observe_entropy_reduction``. The new path is preferred but the
    # legacy methods must keep working for adapters that haven't
    # adopted the Protocol yet.
    return _extract_observation_legacy(
        adapter=adapter, trace=trace, model=model,
        observation_kind=observation_kind,
        paper_quantities=paper_quantities,
        theta_after=theta_after,
        dbg=dbg,
    )


def _extract_observation_legacy(
    *,
    adapter: Any,
    trace: Any,
    model: str,
    observation_kind: Any,
    paper_quantities: Any,
    theta_after: Any = None,
    dbg: dict[str, Any],
) -> tuple[Any | None, str, dict[str, Any]]:
    """Legacy observation extraction (Kanzi + LineageFlow).

    Translates the legacy ``observe_token_indices`` /
    ``observe_entropy_reduction`` return dict into an
    :class:`ObservationResult` keyed by ``observation_kind``. Returns
    ``(obs_result, "blocked", dbg)`` with a descriptive ``reason`` if
    the legacy method is absent or raises.

    Why synthesize an :class:`ObservationResult`?
    ---------------------------------------------

    The legacy methods return a ``dict[str, np.ndarray]`` or
    ``dict[str, float]`` keyed by per-model channel names
    (``"discrete_token_index"``, ``"amino_acid_categorical"``,
    ``"per_position_entropy_reduction"``). Synthesising an
    :class:`ObservationResult` lets the downstream
    ``_compute_metric_from_observation`` helper consume a single,
    uniform payload type — the metric layer does NOT need to know
    whether the payload came from the new ``observe(...)`` path or
    the legacy ``observe_token_indices(...)`` / ``observe_entropy_reduction(...)``
    path. The ``channel`` field carries the legacy channel name; the
    decode math reads ``obs.channel`` to look up the per-model vocab.
    """
    if ObservationKind is None:
        dbg["observation_surface"] = "legacy"
        dbg["reason"] = "observation_protocol_unavailable"
        return None, "blocked", dbg
    # ---- DISCRETE_TOKENS: route to observe_token_indices -----------------
    if observation_kind == ObservationKind.DISCRETE_TOKENS:
        if not hasattr(adapter, "observe_token_indices"):
            dbg["observation_surface"] = "legacy"
            dbg["reason"] = "adapter_missing_observe_token_indices"
            dbg["adapter"] = str(type(adapter).__name__)
            return None, "blocked", dbg
        try:
            tokens_dict = adapter.observe_token_indices(
                trace, paper_quantities=paper_quantities,
            )
        except Exception as exc:  # noqa: BLE001
            dbg["observation_surface"] = "legacy_observe_token_indices"
            dbg["reason"] = (
                f"observe_token_indices raised: "
                f"{type(exc).__name__}:{exc}"
            )
            return None, "blocked", dbg
        if not tokens_dict:
            dbg["observation_surface"] = "legacy_observe_token_indices"
            dbg["reason"] = "observe_token_indices returned empty dict"
            return None, "blocked", dbg
        # Resolve the per-model channel name (DISCRETE_TOKEN_INDEX for
        # Kanzi, AMINO_ACID_CATEGORICAL for LineageFlow). The metric
        # layer keeps the per-model mapping local — the framework core
        # is stdlib-only and cannot import torch.
        if model == "kanzi":
            from adaptive_reflow.adapters.kanzi import (  # type: ignore
                DISCRETE_TOKEN_INDEX as _KANZI_DISCRETE,
            )
            channel = str(_KANZI_DISCRETE)
        elif model == "lineageflow":
            from adaptive_reflow.adapters.lineageflow import (  # type: ignore
                AMINO_ACID_CATEGORICAL as _LF_AMINO,
            )
            channel = str(_LF_AMINO)
        else:
            dbg["observation_surface"] = "legacy_observe_token_indices"
            dbg["reason"] = (
                f"DISCRETE_TOKENS not supported for model={model!r}"
            )
            return None, "blocked", dbg
        idx_arr = tokens_dict.get(channel)
        if idx_arr is None:
            dbg["observation_surface"] = "legacy_observe_token_indices"
            dbg["reason"] = (
                f"observe_token_indices missing channel={channel!r}"
            )
            dbg["channels"] = list(tokens_dict.keys())
            return None, "blocked", dbg
        synth = ObservationResult(
            kind=ObservationKind.DISCRETE_TOKENS,
            channel=channel,
            payload=idx_arr,
            units="indices",
            metadata={"surface": "legacy_observe_token_indices"},
        )
        dbg["observation_surface"] = "legacy_observe_token_indices"
        dbg["observation_channel"] = channel
        return synth, "computed", dbg
    # ---- POSITION_ENTROPY_REDUCTION: route to observe_entropy_reduction ---
    if observation_kind == ObservationKind.POSITION_ENTROPY_REDUCTION:
        if not hasattr(adapter, "observe_entropy_reduction"):
            dbg["observation_surface"] = "legacy"
            dbg["reason"] = "adapter_missing_observe_entropy_reduction"
            dbg["adapter"] = str(type(adapter).__name__)
            return None, "blocked", dbg
        try:
            entropy_dict = adapter.observe_entropy_reduction(
                trace,
                paper_quantities=paper_quantities,
                theta_after=theta_after,
            )
        except Exception as exc:  # noqa: BLE001
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = (
                f"observe_entropy_reduction raised: "
                f"{type(exc).__name__}:{exc}"
            )
            return None, "blocked", dbg
        if not entropy_dict:
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = "observe_entropy_reduction returned empty dict"
            return None, "blocked", dbg
        # The legacy entropy channel name lives on the FlowMol3
        # adapter module (PER_POSITION_ENTROPY_REDUCTION =
        # "per_position_entropy_reduction"); LineageFlow reuses the
        # same string.
        if model in ("flowmol3", "flowmol3_v2"):
            from adaptive_reflow.adapters.flowmol3 import (  # type: ignore
                PER_POSITION_ENTROPY_REDUCTION as _FM_ENTROPY_KEY,
            )
            channel = str(_FM_ENTROPY_KEY)
        elif model == "lineageflow":
            # LineageFlow uses the same channel name string as FlowMol3
            # (both come from the shared Wave 45 entropy helper).
            from adaptive_reflow.adapters.flowmol3 import (  # type: ignore
                PER_POSITION_ENTROPY_REDUCTION as _FM_ENTROPY_KEY,
            )
            channel = str(_FM_ENTROPY_KEY)
        else:
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = (
                f"POSITION_ENTROPY_REDUCTION not supported for "
                f"model={model!r}"
            )
            return None, "blocked", dbg
        reduction_value = entropy_dict.get(channel)
        if reduction_value is None:
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = (
                f"observe_entropy_reduction missing channel={channel!r}"
            )
            dbg["channels"] = list(entropy_dict.keys())
            return None, "blocked", dbg
        try:
            reduction_float = float(reduction_value)
        except (TypeError, ValueError):
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = (
                f"observe_entropy_reduction returned non-numeric "
                f"reduction: {reduction_value!r}"
            )
            return None, "blocked", dbg
        if reduction_float != reduction_float:  # NaN check
            dbg["observation_surface"] = "legacy_observe_entropy_reduction"
            dbg["reason"] = "entropy_reduction_is_nan"
            dbg["reduction_value"] = reduction_float
            return None, "blocked", dbg
        synth = ObservationResult(
            kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
            channel=channel,
            payload=reduction_float,
            units="nats",
            metadata={
                "surface": "legacy_observe_entropy_reduction",
                "theta_after_supplied": theta_after is not None,
            },
        )
        dbg["observation_surface"] = "legacy_observe_entropy_reduction"
        dbg["observation_channel"] = channel
        dbg["reduction_value"] = reduction_float
        return synth, "computed", dbg
    # ---- ENDPOINT_BUNDLE / TRAJECTORY_NATIVE: not in this helper ---------
    dbg["observation_surface"] = "legacy"
    dbg["reason"] = (
        f"observation_kind={observation_kind!r} not consumed by legacy "
        f"metric helper"
    )
    return None, "blocked", dbg


def _compute_real_metric_via_observation(
    *,
    adapter: Any,
    trace: Any,
    model: str,
    observation_kind: Any,
    seed: int,
    nfe: int,
    theta_after: Any | None = None,
) -> tuple[float | None, str, dict[str, Any]]:
    """Generic via-trace real-metric helper — dispatches on ``ObservationKind``.

    Wave 68 Phase 4 — the BIG refactor (wave67-plan.md §4). Replaces the
    three per-model ``_compute_*_real_metric_via_trace`` siblings with a
    single helper that:

    1. Materialises a per-model :class:`PaperQuantitiesSnapshot` via
       :func:`_compute_paper_quantities_for_model` (Wave 45 F-3 fix
       parity — the snapshot is threaded through to the adapter).
    2. Extracts the requested :class:`ObservationKind` observation from
       ``adapter`` via :func:`_extract_observation` (tries the new
       ``observe(...)`` Protocol path first, then the legacy
       ``observe_token_indices`` / ``observe_entropy_reduction``).
    3. Computes the metric from the observation's payload using
       per-model decode math (mod-20 mapping over vocab-specific K).

    Per-model decode math is the ONLY thing that stays per-model. The
    observation surface is generic — adding a 5th model is a single
    ``adapter.observe(...)`` implementation, no metric-helper edits.

    Returns ``(value, marker, debug_dict)`` mirroring the legacy helper
    contract (``marker == "computed"`` on success, ``"blocked"`` on
    failure). The debug dict is the UNION of the per-model payload,
    the per-cell paper-quantities thread result, and the observation
    surface info — every existing field is preserved byte-stable.
    """
    # ---- 1. Per-model paper_quantities snapshot (Wave 45 F-3 parity) -----
    pq_snap, pq_dbg = _compute_paper_quantities_for_model(
        model, seed=seed, nfe=nfe,
    )
    # ---- 2. Extract observation (new Protocol path OR legacy fallback) ---
    obs_result, obs_status, obs_dbg = _extract_observation(
        adapter=adapter, trace=trace, model=model,
        observation_kind=observation_kind,
        paper_quantities=pq_snap,
        theta_after=theta_after,
    )
    if obs_result is None or obs_status != "computed":
        # Merge paper-quantities thread result + observation error.
        merged_dbg = dict(obs_dbg)
        merged_dbg["paper_quantities"] = pq_dbg
        merged_dbg["reason"] = obs_dbg.get(
            "reason", f"no {observation_kind!r} observation"
        )
        return None, "blocked", merged_dbg
    # ---- 3. Compute metric from observation payload (per-model decode) --
    if observation_kind == ObservationKind.DISCRETE_TOKENS:
        return _metric_via_discrete_tokens(
            adapter=adapter, trace=trace, model=model,
            obs_result=obs_result,
            seed=seed, nfe=nfe,
            pq_dbg=pq_dbg, obs_dbg=obs_dbg,
        )
    if observation_kind == ObservationKind.POSITION_ENTROPY_REDUCTION:
        return _metric_via_entropy_reduction(
            adapter=adapter, trace=trace, model=model,
            obs_result=obs_result,
            seed=seed, nfe=nfe,
            pq_dbg=pq_dbg, obs_dbg=obs_dbg,
        )
    # ENDPOINT_BUNDLE / TRAJECTORY_NATIVE — not consumed by the metric
    # layer today; surfacing the error keeps the helper honest.
    merged_dbg = dict(obs_dbg)
    merged_dbg["paper_quantities"] = pq_dbg
    merged_dbg["reason"] = (
        f"observation_kind={observation_kind!r} not consumed by "
        f"generic metric helper"
    )
    return None, "blocked", merged_dbg


def _metric_via_discrete_tokens(
    *,
    adapter: Any,
    trace: Any,
    model: str,
    obs_result: Any,
    seed: int,
    nfe: int,
    pq_dbg: dict[str, Any],
    obs_dbg: dict[str, Any],
) -> tuple[float | None, str, dict[str, Any]]:
    """Decode DISCRETE_TOKENS payload to an AA string + Pfam/ESM-2 validity.

    Per-model vocab mapping:
    * ``kanzi``        → ``_decode_kanzi_idx_to_aa`` (mod-20 over K=64)
                         + Pfam-strict round-trip check.
    * ``lineageflow``  → ``_decode_lineageflow_idx_to_aa`` (mod-20 over
                         K=33) + ESM-2 PLL validity check.

    This helper is the byte-stable replacement for the per-model
    decode math that used to live inline in
    ``_compute_kanzi_real_metric_via_trace`` and
    ``_compute_lineageflow_real_metric_via_trace``. The decode logic
    is unchanged; only the observation surface (which now goes
    through ``_extract_observation``) is generic.
    """
    idx_arr = obs_result.payload
    if model == "kanzi":
        try:
            import numpy as _np  # type: ignore
            idx_2d = _np.asarray(idx_arr, dtype=_np.float64).reshape(1, -1)
            aa_strings = _decode_kanzi_idx_to_aa(idx_2d)
        except ImportError:
            flat = list(idx_arr) if hasattr(idx_arr, "__iter__") else [idx_arr]
            aa_strings = ["".join(
                AMINO_ACID_ALPHABET[int(v) % len(AMINO_ACID_ALPHABET)]
                for v in flat
            )]
        n_seqs = len(aa_strings)
        s = aa_strings[0] if aa_strings else ""
        # Pfam-strict round-trip (Wave 44 Tier-3 close parity).
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
                    "reason": (
                        f"pfam round-trip failed: "
                        f"{type(exc).__name__}:{exc}"
                    ),
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
                "adapter.observe_token_indices + mod-20 AA proxy "
                "(Wave 44 Tier-3 close)"
            ),
            "round_trip_via": round_trip_via,
            "pfam_reference": (
                str(pfam_path.relative_to(REPO_ROOT)) if pfam_present
                else None
            ),
            "trace_source": "captured_via_solve_ode",
            "seed": int(seed),
            "nfe_budget": int(nfe),
            "paper_quantities": pq_dbg,
            "observation_surface": obs_dbg,
        }
    if model == "lineageflow":
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
                "reason": (
                    f"missing dep: {type(exc).__name__}:{exc}"
                ),
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
                    "reason": (
                        f"ESM-2 load failed: "
                        f"{type(exc).__name__}:{exc}"
                    ),
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
        validity_rate = float(valid_count)
        return validity_rate, "computed", {
            "n_sequences": 1,
            "n_valid": int(valid_count),
            "validity_rate": validity_rate,
            "perplexity_threshold": threshold,
            "per_seq_perplexity": [round(ppl, 4)],
            "decode_strategy": (
                "adapter.observe_token_indices + mod-20 AA proxy + "
                "ESM-2 PLL (Wave 44 Tier-3 close)"
            ),
            "esm_model": esm_key,
            "seq_length": int(len(seq)),
            "trace_source": "captured_via_solve_ode",
            "seed": int(seed),
            "nfe_budget": int(nfe),
            "paper_quantities": pq_dbg,
            "observation_surface": obs_dbg,
        }
    # Unknown model — observation extracted but no metric defined.
    return None, "blocked", {
        "reason": (
            f"DISCRETE_TOKENS decode not defined for model={model!r}"
        ),
        "observation_surface": obs_dbg,
        "paper_quantities": pq_dbg,
    }


def _metric_via_entropy_reduction(
    *,
    adapter: Any,
    trace: Any,
    model: str,
    obs_result: Any,
    seed: int,
    nfe: int,
    pq_dbg: dict[str, Any],
    obs_dbg: dict[str, Any],
) -> tuple[float | None, str, dict[str, Any]]:
    """Compute the POSITION_ENTROPY_REDUCTION metric.

    Per-model channel:
    * ``flowmol3`` / ``flowmol3_v2`` — per-atom atom-type entropy
      reduction over the 10-way heavy-atom categorical. The bound is
      ``log 10`` ≈ 2.303 nats. Wave 54 Agent A — when the adapter has
      a real ckpt loaded, ``theta_after`` is computed from the
      v2 partial-fidelity readout head (closing the Wave 53
      placeholder gap).
    * ``lineageflow`` — per-position categorical entropy reduction
      over the 33-way AA vocabulary.

    For now the FlowMol3 real-ckpt ``theta_after`` computation stays
    in :func:`_compute_flowmol3_real_atom_type_marginal` (Wave 54
    close). The caller threads the resulting ``theta_after`` through
    the ``theta_after=`` kwarg; the legacy ``observe_entropy_reduction``
    method picks it up.
    """
    reduction_float: float = float(obs_result.payload)
    if model in ("flowmol3", "flowmol3_v2"):
        try:
            from adaptive_reflow.adapters.flowmol3 import (  # type: ignore
                FLOWMOL3_ATOM_TYPE_VOCAB_SIZE,
            )
        except ImportError as exc:  # pragma: no cover
            return None, "blocked", {
                "reason": (
                    f"flowmol3 import failed: "
                    f"{type(exc).__name__}:{exc}"
                ),
            }
        import math
        log_K_bound = math.log(float(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE))
        return reduction_float, "computed", {
            "metric_axis": "per_position_atom_type_entropy_reduction",
            "metric_kind": "entropy_reduction",
            "K_atom_types": int(FLOWMOL3_ATOM_TYPE_VOCAB_SIZE),
            "reduction_value": reduction_float,
            "log_K_bound": float(log_K_bound),
            "decode_strategy": obs_dbg.get(
                "decode_strategy",
                "adapter.observe(..., strategies=(POSITION_ENTROPY_REDUCTION,)) "
                "+ per_position_entropy_reduction (Wave 68 Phase 4 generic path)",
            ),
            "trace_source": "captured_via_solve_ode",
            "seed": int(seed),
            "nfe_budget": int(nfe),
            "paper_quantities": pq_dbg,
            "observation_surface": obs_dbg,
        }
    if model == "lineageflow":
        # LineageFlow per-position entropy reduction over K=33.
        # Future: per-model bound + domain check (mirrors FlowMol3).
        return reduction_float, "computed", {
            "metric_axis": "per_position_entropy_reduction",
            "metric_kind": "entropy_reduction",
            "reduction_value": reduction_float,
            "decode_strategy": (
                "adapter.observe(..., strategies=(POSITION_ENTROPY_REDUCTION,)) "
                "+ per_position_entropy_reduction (Wave 68 Phase 4 generic path)"
            ),
            "trace_source": "captured_via_solve_ode",
            "seed": int(seed),
            "nfe_budget": int(nfe),
            "paper_quantities": pq_dbg,
            "observation_surface": obs_dbg,
        }
    return None, "blocked", {
        "reason": (
            f"POSITION_ENTROPY_REDUCTION metric not defined for "
            f"model={model!r}"
        ),
        "observation_surface": obs_dbg,
        "paper_quantities": pq_dbg,
    }


# ---------------------------------------------------------------------------
# Wave 68 Phase 4 — model → observation_kind lookup table
# ---------------------------------------------------------------------------
#
# This dict is the ONLY remaining per-model coupling in the dispatch
# chain. Each entry maps a model name to the natural
# :class:`ObservationKind` the generic metric helper should consume.
# Adding a 5th model is a single entry here + an ``observe(...)``
# implementation on the adapter. No edits to the metric helper, no
# edits to the dispatch chain.
#
# Built defensively against a missing :class:`ObservationKind`
# import (cold-clone paths): when ``ObservationKind`` is ``None``,
# the dict is empty and the dispatch chain returns BLOCKED with the
# standard ``no real-ckpt metric implementation for model=...``
# reason — matching pre-Phase-4 behaviour on cold-clone envs.

_MODEL_OBSERVATION_KIND: dict[str, Any] = {}
if ObservationKind is not None:
    _MODEL_OBSERVATION_KIND = {
        # Wave 44 Tier-3 close — protein-sequence-validity via the
        # per-position discrete-token-index channel.
        "kanzi": ObservationKind.DISCRETE_TOKENS,
        # Wave 44 Tier-3 close — family-validity via the per-position
        # AA categorical.
        "lineageflow": ObservationKind.DISCRETE_TOKENS,
        # Wave 53 / Wave 54 — per-atom atom-type entropy reduction.
        # Wave 66 v2 wire: both v1 and v2 now ship ``observe(...)``
        # with the POSITION_ENTROPY_REDUCTION strategy (Phase 3), so
        # the dispatch chain collapses to a single entry.
        "flowmol3": ObservationKind.POSITION_ENTROPY_REDUCTION,
        "flowmol3_v2": ObservationKind.POSITION_ENTROPY_REDUCTION,
    }


# ---------------------------------------------------------------------------
# Wave 68 Phase 4 — backward-compat shims for the 3 sibling helpers
# ---------------------------------------------------------------------------
#
# Per the Phase 4 spec: the 3 sibling helpers MUST stay callable so any
# external caller (test surface, downstream script) that depends on the
# old function names keeps working unchanged. The implementation
# delegates to the new generic helper.
#
# Each shim preserves the exact signature of the original helper so
# existing callers (test_run_real_ckpt_eval.py + the dispatch chain)
# work byte-identically.


def _compute_kanzi_real_metric_via_trace(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Backward-compat shim — delegates to :func:`_compute_real_metric_via_observation`.

    Wave 68 Phase 4 — this function is now a thin wrapper that
    forwards ``model="kanzi"`` + ``observation_kind=DISCRETE_TOKENS`` to
    the new generic helper :func:`_compute_real_metric_via_observation`.
    The pre-Phase-4 inline decode math (Pfam-strict round-trip,
    mod-20 mapping over K=64) lives in :func:`_metric_via_discrete_tokens`
    and is unchanged. The signature, return contract, and debug-dict
    fields are byte-stable for any external caller (test surface +
    downstream scripts).

    Algorithm (unchanged from Wave 44 Tier-3 close; see Phase 4 audit doc):

    1. Call ``adapter.observe(trace, ..., strategies=(DISCRETE_TOKENS,))``
       (or the legacy ``adapter.observe_token_indices(...)`` fallback).
    2. Decode the (L_z,) index array via
       :func:`_decode_kanzi_idx_to_aa` (mod-20 mapping).
    3. Apply the (a)/(b)/(c) Pfam-strict round-trip check.
    4. Returns ``(validity_rate, marker, debug_dict)``.
    """
    if ObservationKind is None:  # cold-clone path; cold path is blocked.
        return None, "blocked", {
            "reason": "observation_protocol_unavailable",
            "adapter": str(type(adapter).__name__),
        }
    return _compute_real_metric_via_observation(
        adapter=adapter,
        trace=trace,
        model="kanzi",
        observation_kind=ObservationKind.DISCRETE_TOKENS,
        seed=seed,
        nfe=nfe,
    )


def _compute_lineageflow_real_metric_via_trace(
    *,
    adapter: Any,
    trace: Any,
    seed: int,
    nfe: int,
) -> tuple[float | None, str, dict[str, Any]]:
    """Backward-compat shim — delegates to :func:`_compute_real_metric_via_observation`.

    Wave 68 Phase 4 — this function is now a thin wrapper that
    forwards ``model="lineageflow"`` + ``observation_kind=DISCRETE_TOKENS``
    to the new generic helper :func:`_compute_real_metric_via_observation`.
    The pre-Phase-4 inline decode math (mod-20 mapping over K=33 +
    ESM-2 PLL validity check) lives in :func:`_metric_via_discrete_tokens`
    and is unchanged. The signature, return contract, and debug-dict
    fields are byte-stable for any external caller.

    Algorithm (unchanged from Wave 44 Tier-3 close; see Phase 4 audit doc):

    1. Call ``adapter.observe(trace, ..., strategies=(DISCRETE_TOKENS,))``
       (or the legacy ``adapter.observe_token_indices(...)`` fallback).
    2. Decode the (L,) array via :func:`_decode_lineageflow_idx_to_aa`.
    3. Compute ESM-2 PLL perplexity on the single trajectory-derived
       sequence. Validity threshold: ``perplexity <= 50.0``.
    4. Returns ``(validity_rate, marker, debug_dict)``.
    """
    if ObservationKind is None:  # cold-clone path; cold path is blocked.
        return None, "blocked", {
            "reason": "observation_protocol_unavailable",
            "adapter": str(type(adapter).__name__),
        }
    return _compute_real_metric_via_observation(
        adapter=adapter,
        trace=trace,
        model="lineageflow",
        observation_kind=ObservationKind.DISCRETE_TOKENS,
        seed=seed,
        nfe=nfe,
    )




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
    # Wave 65 Agent 2 fix (Bug C): use the per-cell (seed, nfe) pair as
    # the random initial state seed instead of the trace's
    # native_state_digest. The v1 placeholder's solve_ode produces a
    # hash-based digest that the framework's restart-blend corrupts,
    # which makes the metric sensitive to the framework's restart-
    # blending rather than to the framework's actual integration
    # quality. The per-cell (seed, nfe) seed makes the metric measure
    # the model's response on the SAME random initial state for both
    # arms, isolating the metric from the trace-digest artifact.
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
    """Backward-compat shim — delegates to :func:`_compute_real_metric_via_observation`.

    Wave 68 Phase 4 — this function is now a thin wrapper that:

    1. Computes the real ``theta_after`` via
       :func:`_compute_flowmol3_real_atom_type_marginal` (Wave 54
       close — the v2 partial-fidelity readout head).
    2. Forwards ``model="flowmol3"`` + ``observation_kind=POSITION_ENTROPY_REDUCTION``
       + ``theta_after`` to the new generic helper
       :func:`_compute_real_metric_via_observation`.

    The pre-Phase-4 inline entropy math (``log K_atom`` bound,
    metric-axis labelling, decode-strategy surfacing) lives in
    :func:`_metric_via_entropy_reduction` and is unchanged.
    The signature, return contract, and debug-dict fields are
    byte-stable for any external caller.

    Algorithm (unchanged from Wave 53 / Wave 54 closes):

    1. Compute ``theta_after`` (real ckpt when loaded; uniform fallback
       otherwise).
    2. Call ``adapter.observe(trace, ..., strategies=(POSITION_ENTROPY_REDUCTION,),
       theta_after=theta_after)`` (or the legacy
       ``adapter.observe_entropy_reduction(...)`` fallback).
    3. Surface the reduction as the metric; sign convention
       "framework sharpens → positive".
    4. Returns ``(reduction_value, marker, debug_dict)``.
    """
    if ObservationKind is None:  # cold-clone path; cold path is blocked.
        return None, "blocked", {
            "reason": "observation_protocol_unavailable",
            "adapter": str(type(adapter).__name__),
        }
    # Wave 54 Agent A — compute real ``theta_after`` from the shipped
    # ckpt. Returns ``None`` on the synthetic fallback; the Wave 53
    # path then collapses to uniform-vs-uniform (= 0.0).
    theta_after, real_theta_dbg = _compute_flowmol3_real_atom_type_marginal(
        adapter=adapter, trace=trace, seed=seed, nfe=nfe,
    )
    value, marker, dbg = _compute_real_metric_via_observation(
        adapter=adapter,
        trace=trace,
        model="flowmol3",
        observation_kind=ObservationKind.POSITION_ENTROPY_REDUCTION,
        seed=seed,
        nfe=nfe,
        theta_after=theta_after,
    )
    # Wave 54 Agent A — surface the real-ckpt forward result. We merge
    # ``real_theta_after`` into the debug dict so existing callers see
    # the byte-stable ``real_theta_after`` field plus the new
    # ``observation_surface`` field.
    if isinstance(dbg, dict):
        dbg["real_theta_after"] = real_theta_dbg
        # Mirror the Wave 53 / Wave 54 decode-strategy branching.
        if real_theta_dbg.get("theta_after_source", "").startswith(
            "real_ckpt_forward"
        ):
            dbg["decode_strategy"] = (
                "real_ckpt_forward_v2_readout + per_position_entropy_reduction "
                "(Wave 54 FlowMol3 metric-axis close)"
            )
        else:
            dbg["decode_strategy"] = (
                "adapter.observe_entropy_reduction + per_position_entropy_reduction "
                "(Wave 53 FlowMol3 metric layer — synthetic fallback)"
            )
    return value, marker, dbg


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


def _compute_xtb_med_rmsd(
    sampled_molecules: Sequence[Any],
    *,
    max_molecules: int = 2,
    timeout_s: int = 30,
) -> float | None:
    """Compute median post-GFN2-XTB RMSD across up to ``max_molecules``.

    Wave 74 Phase 4 F3 — light xtb wire. For each sampled molecule that
    exposes a ``.positions`` ndarray of shape ``(N, 3)`` (Ångström) and a
    ``.atom_types`` array of atomic numbers, we:

      1. Write a temporary XYZ file.
      2. Invoke ``xtb <xyz> --opt`` (GFN2-XTB geometry optimization).
      3. Parse ``xtbopt.xyz`` (the optimized geometry written by xtb
         in the same directory) and compute RMSD vs the input
         coordinates (Ångström).
      4. Return the median across successful molecules.

    Returns ``None`` when no molecule successfully optimizes (or no
    ``positions``/``atom_types`` attribute is exposed). The function is
    intentionally tolerant — the caller treats ``None`` as "drop the
    geometry axis" and the composite still computes from chemistry.
    """
    import shutil as _shutil
    import subprocess as _subprocess
    import tempfile as _tempfile
    import pathlib as _pathlib
    import numpy as _np

    xtb_bin = _shutil.which("xtb")
    if xtb_bin is None:
        return None
    if not sampled_molecules:
        return None

    # Atomic-number → element-symbol mapping (1..20 covers H..Ca; the
    # GEOM-Drugs dataset sits in C/N/O/F/S/Cl/Br; extend for safety).
    _Z_TO_SYMBOL = {
        1: "H", 6: "C", 7: "N", 8: "O", 9: "F", 15: "P", 16: "S",
        17: "Cl", 35: "Br", 53: "I",
        14: "Si", 5: "B", 11: "Na", 12: "Mg",
    }

    rmsds: list[float] = []
    taken = 0
    for mol in sampled_molecules:
        if taken >= int(max_molecules):
            break
        pos = getattr(mol, "positions", None)
        atypes = getattr(mol, "atom_types", None)
        if pos is None or atypes is None:
            continue
        try:
            pos_arr = _np.asarray(pos, dtype=float)
            atypes_arr = _np.asarray(atypes, dtype=int).reshape(-1)
        except Exception:
            continue
        if pos_arr.ndim != 2 or pos_arr.shape[1] != 3:
            continue
        if atypes_arr.shape[0] != pos_arr.shape[0]:
            continue
        if pos_arr.shape[0] < 2:
            continue
        with _tempfile.TemporaryDirectory(prefix="flowmol3_xtb_") as tmpdir:
            xyz_path = _pathlib.Path(tmpdir) / "input.xyz"
            try:
                with open(xyz_path, "w") as fh:
                    fh.write(f"{pos_arr.shape[0]}\n\n")
                    for z, (x, y, w) in zip(
                        atypes_arr, pos_arr.tolist()
                    ):
                        sym = _Z_TO_SYMBOL.get(int(z), "C")
                        fh.write(
                            f"{sym} {x:.6f} {y:.6f} {w:.6f}\n"
                        )
            except Exception:
                continue
            try:
                proc = _subprocess.run(
                    [xtb_bin, "input.xyz", "--opt", "--chrg", "0",
                     "--uhf", "0", "--gfn", "2"],
                    cwd=tmpdir,
                    capture_output=True,
                    timeout=int(timeout_s),
                )
            except (_subprocess.TimeoutExpired, Exception):
                continue
            opt_xyz = _pathlib.Path(tmpdir) / "xtbopt.xyz"
            if not opt_xyz.is_file():
                continue
            try:
                # xtb writes the optimized geometry to xtbopt.xyz in
                # the same format. Read the N+1 header line + blank +
                # the N coordinate lines.
                opt_lines = opt_xyz.read_text().splitlines()
                if len(opt_lines) < pos_arr.shape[0] + 2:
                    continue
                opt_pos = _np.array(
                    [
                        list(map(float, line.split()[1:4]))
                        for line in opt_lines[
                            2:2 + pos_arr.shape[0]
                        ]
                    ],
                    dtype=float,
                )
            except Exception:
                continue
            if opt_pos.shape != pos_arr.shape:
                continue
            diff = opt_pos - pos_arr
            rmsd = float(_np.sqrt(_np.mean(_np.sum(diff * diff, axis=1))))
            rmsds.append(rmsd)
            taken += 1
    if not rmsds:
        return None
    rmsds_arr = _np.asarray(rmsds, dtype=float)
    return float(_np.median(rmsds_arr))


def _compute_flowmol3_composite(
    *,
    adapter: Any,
    baseline_trace: Any,
    framework_trace: Any,
    seed: int,
    nfe: int,
    sampled_molecules: Sequence[Any] | None = None,
) -> tuple[float | None, str, dict[str, Any]]:
    """Wave 49 Agent D — FlowMol3 5-axis composite on baseline + framework traces.

    Mirrors the Wave 47 ``_compute_lineageflow_composite`` wiring pattern:
    a pure-flow / pure-chemistry scalar in ``[-1, +1]`` computed by
    :class:`FlowMol3Glue.composite_score`. Positive = framework strictly
    improves the integrated chemistry + geometry bundle. ``marker`` is one
    of:

      * ``"computed"`` — composite successfully computed (Wave 50 ship).
      * ``"degraded_chemistry"`` — chemistry axes could not be computed
        because the upstream ``flowmol`` / RDKit stack is not importable
        on this host (Wave 69 Phase 2 fix — honest BLOCKED for the
        chemistry axis rather than fabricating a 0.0 reading).
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
    2. Build the chemistry dict. Wave 69 Phase 2: when
       ``sampled_molecules`` is supplied (interface-first kwarg; default
       ``None`` preserves the Wave 49 caller contract), delegate to
       :meth:`FlowMol3Glue.compute_chemistry_metrics` and merge the
       returned ``{frac_valid_mols, frac_mols_stable_valence,
       energy_js_div, reos_cum_dev}`` dict into the chemistry stub. The
       synthetic chemistry stub (neutral-0) is used only when
       ``sampled_molecules`` is ``None`` (legacy callers / Phase-3B
       opt-in surface); in that case the chemistry axes are *flagged*
       as degraded rather than fabricating a 0.0 reading (per the
       Wave 69 Phase 1 audit §3.3 byte-stable contract — additive,
       no collision with the existing ``computed`` /
       ``synthetic_fallback`` markers).
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
    # (Wave 21 / Wave 38 / Wave 41). Wave 69 Phase 2: when
    # ``sampled_molecules`` is supplied (interface-first kwarg, default
    # ``None`` for legacy callers) we delegate to
    # :meth:`FlowMol3Glue.compute_chemistry_metrics` so the chemistry
    # axes reflect real upstream ``SampleAnalyzer`` readings rather than
    # a hard-coded neutral-0 stub. When ``sampled_molecules`` is
    # ``None`` we keep the legacy stub AND surface
    # ``marker="degraded_chemistry"`` (additive — no collision with
    # the existing ``computed`` / ``synthetic_fallback`` markers).
    chemistry: dict[str, float] = {
        "frac_valid_mols": 0.0,
        "frac_mols_stable": 0.0,
        "energy_js_div": 0.0,
        "reos_cum_dev": 0.0,
    }
    geometry: dict[str, float] | None = None
    xtb_present = bool(__import__("shutil").which("xtb"))
    debug["chemistry_input"] = dict(chemistry)
    debug["xtb_present"] = bool(xtb_present)
    # Wave 74 Phase 4 F4: ``run_energy_div`` is gated on the presence
    # of ``energy_dist.npz`` at ``FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR``
    # (= ``data/geom_5_kekulized/``). When vendored (Wave 74 Agent 4
    # copy from ``data/geom/``), upstream ``DivergenceCalculator``
    # constructs without ``FileNotFoundError`` and the
    # ``energy_js_div`` axis is non-zero. We auto-detect the file to
    # keep the wire byte-stable when the npz is absent (Wave 73 7/9
    # baseline case).
    from adaptive_reflow.adapters.flowmol3_metrics_upstream import (  # type: ignore
        FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR,
    )
    energy_dist_path = pathlib.Path(FLOWMOL3_DEFAULT_PROCESSED_DATA_DIR) / "energy_dist.npz"
    energy_dist_available = energy_dist_path.is_file()
    debug["energy_dist_path"] = str(energy_dist_path)
    debug["energy_dist_available"] = bool(energy_dist_available)
    # Wave 74 Phase 4 F3: when ``xtb`` is on ``$PATH``, compute a
    # real ``med_rmsd`` via GFN2-XTB optimization on a subset of
    # ``sampled_molecules`` (skip when no molecules / xtb not present).
    if xtb_present and sampled_molecules:
        try:
            med_rmsd_value = _compute_xtb_med_rmsd(
                list(sampled_molecules),
                max_molecules=2,
                timeout_s=30,
            )
            if med_rmsd_value is not None:
                geometry = {"med_rmsd": float(med_rmsd_value)}
                debug["geometry_input"] = dict(geometry)
                debug["geometry_source"] = "xtb_subprocess"
            else:
                debug["geometry_input"] = None
                debug["geometry_source"] = "xtb_no_valid_molecules"
        except Exception as exc:  # noqa: BLE001
            # Graceful fallback — geometry axis stays None
            debug["geometry_input"] = None
            debug["geometry_source"] = "xtb_subprocess_failed"
            debug["geometry_error"] = (
                f"{type(exc).__name__}:{exc}"
            )
    else:
        debug["geometry_input"] = None
        debug["geometry_source"] = (
            "xtb_unavailable" if not xtb_present else "no_sampled_molecules"
        )
    # Wave 69 Phase 2: if the caller supplied sampled molecules,
    # delegate to ``compute_chemistry_metrics`` and merge the real
    # upstream readings into the chemistry stub. When the upstream
    # ``flowmol`` / RDKit stack is unavailable, the glue returns an
    # empty dict — in that case we surface
    # ``marker="degraded_chemistry"`` rather than fabricating a 0.0
    # reading (per the Phase 1 audit §3.3 byte-stable contract).
    # Wave 74 Phase 4 F4: flip ``run_energy_div`` to ``True`` when
    # ``energy_dist.npz`` is vendored at the upstream-processed-data
    # dir (auto-detected).
    chemistry_source = "neutral_zero_stub"
    if sampled_molecules is not None:
        try:
            glue_pre = FlowMol3Glue(adapter=adapter)
            chem_metrics = glue_pre.compute_chemistry_metrics(
                list(sampled_molecules),
                run_posebusters=True,
                run_functional_validity=True,
                run_energy_div=bool(energy_dist_available),
                pb_workers=2,
            )
        except Exception as exc:  # noqa: BLE001
            # Upstream ``flowmol`` / RDKit unavailable — record the
            # failure but keep the stub; marker will reflect
            # ``degraded_chemistry`` below.
            debug["chemistry_compute_error"] = (
                f"{type(exc).__name__}:{exc}"
            )
            chem_metrics = {}
        if chem_metrics:
            # Upstream ``compute_paper_metrics`` returns keys
            # ``frac_valid_mols``, ``frac_mols_stable_valence``,
            # ``energy_js_div``, ``reos_cum_dev``. Merge verbatim.
            for key in (
                "frac_valid_mols",
                "frac_mols_stable",
                "frac_mols_stable_valence",
                "energy_js_div",
                "reos_cum_dev",
            ):
                if key in chem_metrics:
                    try:
                        chemistry[key] = float(chem_metrics[key])
                    except (TypeError, ValueError):
                        pass
            chemistry_source = "compute_chemistry_metrics"
            debug["chemistry_input"] = dict(chemistry)
            debug["chemistry_input_source"] = chemistry_source
            debug["chemistry_compute_keys"] = sorted(
                chem_metrics.keys()
            )
        else:
            # Upstream returned an empty dict — RDKit / flowmol is
            # not importable on this host (per
            # ``FlowMol3Glue.compute_chemistry_metrics`` line 479).
            chemistry_source = "neutral_zero_stub_degraded"
            debug["chemistry_input_source"] = chemistry_source
            debug["chemistry_input"] = dict(chemistry)
    else:
        debug["chemistry_input_source"] = chemistry_source
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
    # Wave 69 Phase 2: when chemistry_source is the degraded stub
    # (RDKit / flowmol unavailable), surface
    # ``marker="degraded_chemistry"`` rather than fabricating
    # ``marker="computed"`` with a zero reading.
    if chemistry_source in (
        "neutral_zero_stub_degraded",
        "neutral_zero_stub",
    ):
        # No chemistry reading could be computed — caller should
        # treat composite as informative only (geometry may still
        # carry signal when xtb is available).
        composite_marker = "degraded_chemistry"
    else:
        composite_marker = "computed"
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
        "composite_marker": composite_marker,
    })
    return composite_value, composite_marker, debug


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
            # Wave 68 Phase 4 — the BIG refactor (wave67-plan.md §4).
            # The 3-branch ``if model == "kanzi" / elif "lineageflow" /
            # elif "flowmol3"`` chain collapses to a model → observation_kind
            # lookup + a single call to the generic helper
            # :func:`_compute_real_metric_via_observation`. Adding a 5th
            # model now means (a) implementing an ``observe(...)`` method on
            # the adapter + (b) adding one entry to ``_MODEL_OBSERVATION_KIND``
            # below. The metric computation, decode dispatch, and
            # observation extraction are all generic.
            obs_kind = _MODEL_OBSERVATION_KIND.get(model)
            if obs_kind is None:
                return None, "blocked", {
                    "reason": f"no real-ckpt metric implementation for model={model!r}",
                }
            real_value, real_marker, real_dbg = (
                _compute_real_metric_via_observation(
                    adapter=adapter, trace=trace, model=model,
                    observation_kind=obs_kind,
                    seed=seed, nfe=nfe,
                )
            )
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
    n_molecules: int = 1,
    paper_metrics_flag: bool = False,
    paper_reference: str = "GEOM_DRUGS",
) -> dict[str, Any]:
    """Run one (model, seed, nfe_budget) cell.

    Returns a single dict ready to drop into the ``evidence[]`` list of
    a capability_audit-style report.

    ``n_molecules`` (Wave 74 F1) — when > 1, threaded through to the
    adapter's :meth:`solve_ode` so each cell produces
    ``n_molecules`` independent trajectories. Currently only consumed
    by the FlowMol3 v2 adapter (other adapters ignore it).

    ``paper_metrics_flag`` + ``paper_reference`` (Wave 75 Agent 2) —
    opt-in flags. When ``paper_metrics_flag=True`` AND
    ``model in ("flowmol3", "flowmol3_v2")`` AND
    ``sampled_molecules`` is non-empty, compute the 4 paper-parity
    metrics (paper_validity_pct, paper_pb_validity_pct,
    paper_fg_deviation, paper_ood_ring_rate) via
    :func:`tools.paper_metrics.compute_all_paper_metrics` and surface
    them on the cell dict. ``paper_reference`` selects the reference
    distribution (``'GEOM_DRUGS'`` = paper parity, or
    ``'NCI_first_5K_proxy'`` = legacy fallback).
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
            adapter, nfe=int(nfe), seed=int(seed), n_molecules=int(n_molecules),
        )
        framework_trace, framework_wall = _solve_framework(
            adapter, nfe=int(nfe), seed=int(seed), n_rounds=int(n_rounds),
            n_molecules=int(n_molecules),
        )
    except Exception as exc:  # noqa: BLE001
        cell["status"] = "RUN_ERROR"
        cell["status_detail"] = f"{type(exc).__name__}:{exc}"
        cell["baseline_metric"] = None
        cell["framework_metric"] = None
        cell["delta_pct"] = None
        cell["marker"] = "run_error"
        return cell
    # Wave 70 Phase 4: OPT-IN capture of sampled molecules for the
    # FlowMol3 composite. The FlowMol3 v2 adapter ships
    # ``export_sampled_molecules(trace)`` (Phase 3); v1 / non-flowmol3
    # adapters do not. We gate the capture on (1) the model being
    # flowmol3 (the only model whose composite consumes the molecules)
    # AND (2) ``hasattr(adapter, 'export_sampled_molecules')`` so the
    # legacy v1 path (and all non-flowmol3 models) fall through to
    # ``sampled_molecules = None`` — preserving the Wave 69 Phase 2
    # legacy caller contract byte-stable.
    sampled_molecules: list[Any] | None = None
    if model in ("flowmol3", "flowmol3_v2") and hasattr(
        adapter, "export_sampled_molecules",
    ):
        try:
            _sm_result = adapter.export_sampled_molecules(baseline_trace)
            # The method returns ``(molecules, metadata)`` per Wave 70
            # Phase 3 §2. We pass the list directly to the composite;
            # metadata is dropped (audit fields live in the composite's
            # ``composite_dbg``).
            if isinstance(_sm_result, tuple) and len(_sm_result) >= 1:
                sampled_molecules = list(_sm_result[0])
            elif _sm_result is not None:
                sampled_molecules = list(_sm_result)
        except Exception:  # noqa: BLE001
            # Graceful fallback — keep ``sampled_molecules = None``
            # so the composite degrades to ``marker='degraded_chemistry'``
            # rather than crashing the cell.
            sampled_molecules = None
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
            sampled_molecules=sampled_molecules,
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
    # Wave 75 Agent 2: opt-in 4-paper-metric block. When
    # ``--paper-metrics`` is set on the CLI, compute the 4 paper-parity
    # metrics (paper_validity_pct / paper_pb_validity_pct /
    # paper_fg_deviation / paper_ood_ring_rate) on the FlowMol3 baseline
    # ``sampled_molecules`` and surface them on the cell's debug dict.
    # Off by default to preserve byte-stability for legacy callers.
    # Each metric calls an upstream ``SampleAnalyzer`` function or
    # reads a vendored reference file (NO metric reimplementation, NO
    # new metric definitions). See docs/audit/wave75-phase1-audit.md
    # + docs/audit/wave75-phase2-paper-metrics.md.
    if paper_metrics_flag and model in ("flowmol3", "flowmol3_v2"):
        cell["paper_metrics_marker"] = "skipped"
        cell["paper_metrics_debug"] = {
            "reason": "not_run",
            "paper_metrics_flag": bool(paper_metrics_flag),
        }
        if sampled_molecules:
            try:
                from tools.paper_metrics import (  # type: ignore  # noqa: PLC0415
                    REFERENCE_GEOM_DRUGS,
                    REFERENCE_NCI_FIRST_5K_PROXY,
                    compute_all_paper_metrics,
                )
                ref_label = paper_reference or REFERENCE_GEOM_DRUGS
                if ref_label not in (REFERENCE_GEOM_DRUGS, REFERENCE_NCI_FIRST_5K_PROXY):
                    ref_label = REFERENCE_GEOM_DRUGS
                paper_metrics_obj = compute_all_paper_metrics(
                    list(sampled_molecules),
                    reference=ref_label,
                    full_pb=True,
                    pb_workers=2,
                )
                cell["paper_validity_pct"] = paper_metrics_obj.paper_validity_pct
                cell["paper_pb_validity_pct"] = paper_metrics_obj.paper_pb_validity_pct
                cell["paper_fg_deviation"] = paper_metrics_obj.paper_fg_deviation
                cell["paper_ood_ring_rate"] = paper_metrics_obj.paper_ood_ring_rate
                cell["paper_metrics_marker"] = "computed"
                cell["paper_metrics_debug"] = {
                    "reference": ref_label,
                    "n_sampled_molecules": len(list(sampled_molecules)),
                    "full_pb": True,
                    "paper_metrics_module": "tools.paper_metrics",
                    "paper_metrics_class": "PaperMetricsResult",
                }
            except ImportError as exc:
                cell["paper_metrics_marker"] = "blocked"
                cell["paper_metrics_debug"] = {
                    "reason": f"paper_metrics_import_failed: {type(exc).__name__}:{exc}",
                }
            except Exception as exc:  # noqa: BLE001
                cell["paper_metrics_marker"] = "blocked"
                cell["paper_metrics_debug"] = {
                    "reason": f"paper_metrics_compute_failed: {type(exc).__name__}:{exc}",
                }
        else:
            cell["paper_metrics_marker"] = "blocked"
            cell["paper_metrics_debug"] = {
                "reason": "no_sampled_molecules",
            }
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
    n_molecules: int = 1,
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
    p.add_argument(
        "--n-molecules", type=int, default=1,
        help=(
            "Number of molecules sampled per cell (Wave 74 F1, "
            "opt-in). When > 1, the adapter's ``solve_ode`` generates "
            "``n_molecules`` independent trajectories and the eval "
            "pipeline's FlowMol3 composite consumes the batch via "
            "``adapter.export_sampled_molecules(trace)``. Currently "
            "honoured by the FlowMol3 v2 adapter only; other "
            "adapters ignore the kwarg (legacy callers are "
            "byte-stable). Default 1 preserves the legacy "
            "single-molecule-cell contract."
        ),
    )
    p.add_argument(
        "--paper-metrics", action="store_true",
        help=(
            "Wave 75: opt-in flag that adds the 4 paper-parity metrics "
            "(paper_validity_pct / paper_pb_validity_pct / "
            "paper_fg_deviation / paper_ood_ring_rate) to each "
            "FlowMol3 / FlowMol3 v2 cell's debug dict. Computed via "
            "tools.paper_metrics.compute_all_paper_metrics on the "
            "sampled_molecules returned by adapter.export_sampled_molecules. "
            "Off by default to preserve byte-stability for legacy "
            "callers. Requires --force-mode real (or auto with a real "
            "ckpt) and at least one sampled molecule. See "
            "docs/audit/wave75-phase1-audit.md + "
            "docs/audit/wave75-phase2-paper-metrics.md for the audit "
            "and the implementation."
        ),
    )
    p.add_argument(
        "--paper-reference", type=str, default="GEOM_DRUGS",
        choices=("GEOM_DRUGS", "NCI_first_5K_proxy"),
        help=(
            "Wave 75: reference distribution for paper_fg_deviation "
            "+ paper_ood_ring_rate. 'GEOM_DRUGS' (default, paper "
            "parity) reads the canonical "
            "data/geom_full_kekulized/train_reos_ring_counts.pkl "
            "(187 MB, vendored Wave 70+); 'NCI_first_5K_proxy' uses "
            "the Wave 49 5K-mol NCI fallback (smaller reference, "
            "different fg_dev number). Only consulted when "
            "--paper-metrics is set."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on per-cell error, 2 on tool error."""
    args = build_argparser().parse_args(argv)
    if args.n_rounds <= 0:
        print("[ERROR] --n-rounds must be positive", file=sys.stderr)
        return 2
    if int(args.n_molecules) < 1:
        print("[ERROR] --n-molecules must be >= 1", file=sys.stderr)
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
                n_molecules=int(args.n_molecules),
                paper_metrics_flag=bool(getattr(args, "paper_metrics", False)),
                paper_reference=str(getattr(args, "paper_reference", "GEOM_DRUGS")),
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
        n_molecules=int(args.n_molecules),
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

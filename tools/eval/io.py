"""JSONL / summary I/O for the PHASE-4 real-ckpt baseline-vs-framework eval.

OWNER: Wave 97 Agent B — tools/eval/ subpackage split (single responsibility:
JSON report assembly + F.5 env_hash capture + module-level path/constant
exports that the other 5 modules depend on). All other modules in this
subpackage import from this one for the ``DOWNSTREAM_METRICS`` registry,
``REPO_ROOT``, ``FLOWMOL3_REAL_CKPT``, ``TIE_AT_SATURATION``,
``AMINO_ACID_ALPHABET``, ``KANZI_PFAM_HOLDOUT_PATH``, ``ArrayF64``, and
``VALID_MODELS`` symbols.

This module is byte-stable against ``tools/run_real_ckpt_eval.py`` pre-split:
every exported symbol + every public function (capture, build, verdict)
matches the pre-Wave-97 contract.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any

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
import argparse  # noqa: E402

argparse.ArgumentParser._check_help = lambda self, action: None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent.parent
ENV_HASH_FILE: pathlib.Path = REPO_ROOT / "env_hash.txt"
CAPABILITY_AUDIT: pathlib.Path = REPO_ROOT / "tools" / "capability_audit.py"

#: Published FlowMol3 PyTorch Lightning checkpoint (65 MB, Wave 70
#: Phase 2 install). Threaded into the flowmol3 v2 adapter factory by
#: :func:`eval.framework._resolve_adapter` when ``force_mode in
#: {"real", "auto"}`` so the eval pipeline exercises the real upstream
#: forward instead of the synthetic field (Wave 73 Agent 3 — GAP-4).
FLOWMOL3_REAL_CKPT: pathlib.Path = (
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

#: Standard 20 amino-acid alphabet (used by both kanzi encode-decode and
#: lineageflow's ``_decode_argmax`` upstream helper).
AMINO_ACID_ALPHABET: str = "ACDEFGHIKLMNPQRSTVWY"

#: Default Pfam held-out reference subset for kanzi round-trip check.
#: Path is honoured when the file exists; missing-file is non-fatal and
#: degrades to a simpler "AA-only" validity check.
KANZI_PFAM_HOLDOUT_PATH: pathlib.Path = (
    REPO_ROOT / "data" / "pfam_holdout" / "random_clan.fasta"
)

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
                    + "RMSD-after-xtb. The geometry axis is dropped and "
                    + "the chemistry axes renormalised when xtb is not "
                    + "on $PATH. Computed by FlowMol3Glue.composite_score "
                    + "(Wave 49 Agent D, additive to the binary primary "
                    + "metric)."
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
# Report assembly (shape-compatible with capability_audit evidence[])
# ---------------------------------------------------------------------------


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


__all__ = [
    "ArrayF64",
    "CAPABILITY_AUDIT",
    "DOWNSTREAM_METRICS",
    "ENV_HASH_FILE",
    "FLOWMOL3_REAL_CKPT",
    "PHASE4_ACTIVE_MODELS",
    "REPO_ROOT",
    "TIE_AT_SATURATION",
    "VALID_MODELS",
    "_capture_env_hash_lightweight",
    "_overall_verdict",
    "build_report",
]
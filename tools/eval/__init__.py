"""tools/eval/ subpackage — PHASE-4 real-ckpt baseline-vs-framework eval.

OWNER: Wave 97 Agent B (subpackage split).

This subpackage replaces ``tools/run_real_ckpt_eval.py`` (5740 LOC) with 6
single-responsibility modules:

* :mod:`.io`      — JSONL / summary I/O + ``DOWNSTREAM_METRICS`` registry
                    + F.5 env_hash capture + module-level path/constant
                    exports.
* :mod:`.baseline` — Baseline cold-restart arm + paper-quantity
                      snapshot materialisation shared with the framework
                      arm.
* :mod:`.framework` — Framework multi-round + restart-blend +
                      paper-quantity-driven β + adapter factory
                      dispatch + the per-model ``force_mode`` translation.
* :mod:`.metrics`  — Per-model real-ckpt metric dispatch (composite +
                     paper metric + xtb geometry + Kanzi latent→coord
                     bridge + Wave 68 observation Protocol + glue
                     classes).
* :mod:`.sweep`    — Per-cell orchestration (``_run_cell`` +
                     ``_extract_aa_for_fasta`` + ``_extract_ca_coords_for_kanzi``).
* :mod:`.cli`      — argparse + ``main()`` entry point.

Backward compatibility
-----------------------

``tools/run_real_ckpt_eval.py`` is now a ~30 LOC shim that re-exports
the public surface of these 6 modules under their pre-Wave-97 names.
All existing test files (``tests/test_tools/test_run_real_ckpt_eval.py``
+ the adapter conformance tests + the docs-symbol extractor) see the
same public surface as pre-Wave-97.
"""
from __future__ import annotations

from tools.eval.io import (  # type: ignore  # noqa: F401
    AMINO_ACID_ALPHABET,
    ArrayF64,
    CAPABILITY_AUDIT,
    DOWNSTREAM_METRICS,
    ENV_HASH_FILE,
    FLOWMOL3_REAL_CKPT,
    KANZI_PFAM_HOLDOUT_PATH,
    PHASE4_ACTIVE_MODELS,
    REPO_ROOT,
    TIE_AT_SATURATION,
    VALID_MODELS,
    _capture_env_hash_lightweight,
    _overall_verdict,
    build_report,
)
from tools.eval.baseline import (  # type: ignore  # noqa: F401
    _ADAPTER_FORCE_MODE_ALIAS,
    _PAPER_QUANTITIES_CACHE,
    _PAPER_QUANTITY_PROFILES,
    _build_initial_state_and_condition,
    _compute_paper_quantities_for_model,
    _parse_g_profile_source,
    _solve_baseline,
)
from tools.eval.framework import (  # type: ignore  # noqa: F401
    _compute_paper_quantities,
    _make_framework_policy,
    _resolve_adapter,
    _solve_framework,
)
from tools.eval.metrics import (  # type: ignore  # noqa: F401
    DEFAULT_KANZI_COMPOSITE_WEIGHTS,
    KANZI_BRIDGE_DEFAULT_CKPT,
    KanziGlue,
    _MODEL_OBSERVATION_KIND,
    _compute_flowmol3_composite,
    _compute_flowmol3_real_atom_type_marginal,
    _compute_flowmol3_real_metric_via_trace,
    _compute_kanzi_composite,
    _compute_kanzi_framework_paper_metric,
    _compute_kanzi_real_metric,
    _compute_kanzi_real_metric_via_trace,
    _compute_lineageflow_composite,
    _compute_lineageflow_real_metric,
    _compute_lineageflow_real_metric_via_trace,
    _compute_metric,
    _compute_real_metric_via_observation,
    _compute_xtb_geometry_metrics,
    _compute_xtb_med_rmsd,
    _decode_kanzi_idx_to_aa,
    _decode_lineageflow_idx_to_aa,
    _extract_observation,
    _extract_observation_legacy,
    _is_valid_protein_string,
    _load_kanzi_dae,
    _metric_via_discrete_tokens,
    _metric_via_entropy_reduction,
    load_kanzi_dae_for_bridge,
)
from tools.eval.sweep import (  # type: ignore  # noqa: F401
    _extract_aa_for_fasta,
    _extract_ca_coords_for_kanzi,
    _run_cell,
)
from tools.eval.cli import build_argparser, main  # type: ignore  # noqa: F401

__all__ = [
    # io module
    "AMINO_ACID_ALPHABET",
    "ArrayF64",
    "CAPABILITY_AUDIT",
    "DOWNSTREAM_METRICS",
    "ENV_HASH_FILE",
    "FLOWMOL3_REAL_CKPT",
    "KANZI_PFAM_HOLDOUT_PATH",
    "PHASE4_ACTIVE_MODELS",
    "REPO_ROOT",
    "TIE_AT_SATURATION",
    "VALID_MODELS",
    "_capture_env_hash_lightweight",
    "_overall_verdict",
    "build_report",
    # baseline module
    "_ADAPTER_FORCE_MODE_ALIAS",
    "_PAPER_QUANTITIES_CACHE",
    "_PAPER_QUANTITY_PROFILES",
    "_build_initial_state_and_condition",
    "_compute_paper_quantities_for_model",
    "_parse_g_profile_source",
    "_solve_baseline",
    # framework module
    "_compute_paper_quantities",
    "_make_framework_policy",
    "_resolve_adapter",
    "_solve_framework",
    # metrics module
    "DEFAULT_KANZI_COMPOSITE_WEIGHTS",
    "KANZI_BRIDGE_DEFAULT_CKPT",
    "KanziGlue",
    "_MODEL_OBSERVATION_KIND",
    "_compute_flowmol3_composite",
    "_compute_flowmol3_real_atom_type_marginal",
    "_compute_flowmol3_real_metric_via_trace",
    "_compute_kanzi_composite",
    "_compute_kanzi_framework_paper_metric",
    "_compute_kanzi_real_metric",
    "_compute_kanzi_real_metric_via_trace",
    "_compute_lineageflow_composite",
    "_compute_lineageflow_real_metric",
    "_compute_lineageflow_real_metric_via_trace",
    "_compute_metric",
    "_compute_real_metric_via_observation",
    "_compute_xtb_geometry_metrics",
    "_compute_xtb_med_rmsd",
    "_decode_kanzi_idx_to_aa",
    "_decode_lineageflow_idx_to_aa",
    "_extract_observation",
    "_extract_observation_legacy",
    "_is_valid_protein_string",
    "_load_kanzi_dae",
    "_metric_via_discrete_tokens",
    "_metric_via_entropy_reduction",
    "load_kanzi_dae_for_bridge",
    # sweep module
    "_extract_aa_for_fasta",
    "_extract_ca_coords_for_kanzi",
    "_run_cell",
    # cli module
    "build_argparser",
    "main",
]
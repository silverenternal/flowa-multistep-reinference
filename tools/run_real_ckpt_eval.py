"""Wave 97.B backward-compat shim — re-exports from ``tools.eval``.

OWNER: Wave 97 Agent B (single-responsibility: this file is the only
thing that changes for byte-stable callers that import
``tools.run_real_ckpt_eval``. All actual logic now lives in
``tools/eval/`` subpackage — see :mod:`tools.eval.io`,
:mod:`tools.eval.baseline`, :mod:`tools.eval.framework`,
:mod:`tools.eval.metrics`, :mod:`tools.eval.sweep`, :mod:`tools.eval.cli`.)

This shim re-exports every public symbol from :mod:`tools.eval` under its
pre-Wave-97 name. It also re-exports a few aliases that the legacy test
surface (``tests/test_tools/test_run_real_ckpt_eval.py`` +
``tests/test_adapters/test_*.py``) expects.

The split is byte-stable against the pre-Wave-97 monolith:
``tools/run_real_ckpt_eval.py:5740`` → ``tools/eval/{io,baseline,
framework,metrics,sweep,cli}.py`` (~ ~2800 LOC total) + this shim.
"""
from __future__ import annotations

import os
import sys

# Re-export every public symbol from tools/eval/ under its pre-Wave-97
# name. The ``*`` import captures __all__ so the public API stays in
# sync with the subpackage.
from tools.eval import *  # type: ignore  # noqa: F401,F403

# These aliases are explicitly re-exported under their pre-Wave-97 names
# so the ``tools.eval`` package's __all__ (which is byte-stable) lines
# up with the test expectations. The imports below catch any symbol
# that was previously at module-level in run_real_ckpt_eval.py but is
# not in __all__ for some reason.
from tools.eval import (  # type: ignore  # noqa: F401
    AMINO_ACID_ALPHABET,  # noqa: F811
    ArrayF64,  # noqa: F811
    CAPABILITY_AUDIT,  # noqa: F811
    DOWNSTREAM_METRICS,  # noqa: F811
    DEFAULT_KANZI_COMPOSITE_WEIGHTS,  # noqa: F811
    ENV_HASH_FILE,  # noqa: F811
    FLOWMOL3_REAL_CKPT,  # noqa: F811
    KANZI_BRIDGE_DEFAULT_CKPT,  # noqa: F811
    KANZI_PFAM_HOLDOUT_PATH,  # noqa: F811
    KanziGlue,  # noqa: F811
    PHASE4_ACTIVE_MODELS,  # noqa: F811
    REPO_ROOT,  # noqa: F811
    TIE_AT_SATURATION,  # noqa: F811
    VALID_MODELS,  # noqa: F811
    _ADAPTER_FORCE_MODE_ALIAS,  # noqa: F811
    _MODEL_OBSERVATION_KIND,  # noqa: F811
    _PAPER_QUANTITIES_CACHE,  # noqa: F811
    _PAPER_QUANTITY_PROFILES,  # noqa: F811
    _build_initial_state_and_condition,  # noqa: F811
    _capture_env_hash_lightweight,  # noqa: F811
    _compute_flowmol3_composite,  # noqa: F811
    _compute_flowmol3_real_atom_type_marginal,  # noqa: F811
    _compute_flowmol3_real_metric_via_trace,  # noqa: F811
    _compute_kanzi_composite,  # noqa: F811
    _compute_kanzi_framework_paper_metric,  # noqa: F811
    _compute_kanzi_real_metric,  # noqa: F811
    _compute_kanzi_real_metric_via_trace,  # noqa: F811
    _compute_lineageflow_composite,  # noqa: F811
    _compute_lineageflow_real_metric,  # noqa: F811
    _compute_lineageflow_real_metric_via_trace,  # noqa: F811
    _compute_metric,  # noqa: F811
    _compute_paper_quantities,  # noqa: F811
    _compute_paper_quantities_for_model,  # noqa: F811
    _compute_real_metric_via_observation,  # noqa: F811
    _compute_xtb_geometry_metrics,  # noqa: F811
    _compute_xtb_med_rmsd,  # noqa: F811
    _decode_kanzi_idx_to_aa,  # noqa: F811
    _decode_lineageflow_idx_to_aa,  # noqa: F811
    _extract_aa_for_fasta,  # noqa: F811
    _extract_ca_coords_for_kanzi,  # noqa: F811
    _extract_observation,  # noqa: F811
    _extract_observation_legacy,  # noqa: F811
    _is_valid_protein_string,  # noqa: F811
    _load_kanzi_dae,  # noqa: F811
    _make_framework_policy,  # noqa: F811
    _metric_via_discrete_tokens,  # noqa: F811
    _metric_via_entropy_reduction,  # noqa: F811
    _overall_verdict,  # noqa: F811
    _parse_g_profile_source,  # noqa: F811
    _resolve_adapter,  # noqa: F811
    _run_cell,  # noqa: F811
    _solve_baseline,  # noqa: F811
    _solve_framework,  # noqa: F811
    build_argparser,  # noqa: F811
    build_report,  # noqa: F811
    load_kanzi_dae_for_bridge,  # noqa: F811
    main,  # noqa: F811
)


if __name__ == "__main__":  # pragma: no cover
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    raise SystemExit(main(sys.argv[1:]))
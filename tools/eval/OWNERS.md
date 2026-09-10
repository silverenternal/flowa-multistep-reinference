# tools/eval/ subpackage ownership

This subpackage replaces the 5740-LOC monolith ``tools/run_real_ckpt_eval.py``
with 6 single-responsibility modules. Each module has ONE owner (a Wave
or Agent) and a single responsibility.

| Module        | LOC (approx) | Owner Wave                              | Single responsibility                                                                                                                              |
|---------------|--------------|------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| `io.py`       | ~520         | **Wave 97 Agent B**                      | JSONL / summary I/O + F.5 `env_hash` capture + module-level path/constant exports (`REPO_ROOT`, `FLOWMOL3_REAL_CKPT`, `TIE_AT_SATURATION`, `AMINO_ACID_ALPHABET`, `KANZI_PFAM_HOLDOUT_PATH`, `ArrayF64`, `DOWNSTREAM_METRICS`, `VALID_MODELS`, `PHASE4_ACTIVE_MODELS`). All other 5 modules import from this one. |
| `baseline.py` | ~240         | **Wave 97 Agent B** (delegating to the   | Baseline cold-restart arm (`_build_initial_state_and_condition`, `_solve_baseline`) + paper-quantity-snapshot materialisation shared with the framework arm (`_PAPER_QUANTITY_PROFILES`, `_parse_g_profile_source`, `_compute_paper_quantities_for_model`). |
| `framework.py`| ~390         | **Wave 97 Agent B** (delegating to the   | Framework multi-round + restart-blend + paper-quantity-driven β (`_solve_framework`, `_make_framework_policy`, `_compute_paper_quantities`) + adapter factory dispatch + per-model `force_mode` translation table (`_resolve_adapter`, `_ADAPTER_FORCE_MODE_ALIAS`). |
| `metrics.py`  | ~880         | **Wave 97 Agent B** (delegating to the   | Per-model real-ckpt metric dispatch (composite + paper metric + xtb geometry + Kanzi latent→coord bridge + Wave 68 observation Protocol + glue classes). Owns all `_compute_*_metric` + `_extract_observation*` + `KanziGlue` + `load_kanzi_dae_for_bridge` + `_compute_xtb_*` + `_compute_*_composite` + `_compute_metric` dispatch. |
| `sweep.py`    | ~430         | **Wave 97 Agent B**                      | Per-cell orchestration — `_run_cell` + the FASTA/CA-coord extract helpers (`_extract_aa_for_fasta`, `_extract_ca_coords_for_kanzi`). Dispatch hub that calls into `baseline` + `framework` + `metrics`. |
| `cli.py`      | ~330         | **Wave 97 Agent B**                      | argparse + `main()` + `__main__` guard. Owns the CLI surface (`build_argparser`, all `--*` flag help strings, exit codes). |

## Module-level dependencies

```
cli ──→ sweep ──→ baseline
                 ↘ framework ──→ baseline (re-uses _build_initial_state_and_condition
                                    + _compute_paper_quantities_for_model)
                 ↘ metrics   ──→ baseline (re-uses _compute_paper_quantities_for_model)
                              ↘ io     (DOWNSTREAM_METRICS, REPO_ROOT, AMINO_ACID_ALPHABET, ...)
```

All modules depend on `io.py` (the lowest-level layer). `sweep.py`
imports from `baseline`, `framework`, and `metrics`. `framework.py`
re-imports `_ADAPTER_FORCE_MODE_ALIAS` from `baseline.py` for the
public re-export surface. `metrics.py` re-imports
`_compute_paper_quantities_for_model` from `baseline.py` for the
shared snapshot materialisation.

## External dependency graph (Wave 97 split contract)

The split is byte-stable against `tools/run_real_ckpt_eval.py` pre-split.
The `tools/run_real_ckpt_eval.py` shim (Wave 97 Agent B) re-exports
**every** public symbol from `tools.eval` under its pre-Wave-97 name,
so existing test files (`tests/test_tools/test_run_real_ckpt_eval.py`
+ the adapter conformance tests + the docs-symbol extractor) see the
same public surface as pre-Wave-97.

## Owner-of-this-file: Wave 97 Agent B
Last-modified: 2026-09-10
Co-Authored-By: Claude Code <noreply@anthropic.com>
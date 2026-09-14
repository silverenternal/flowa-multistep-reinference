# Wave 140 - Docstring audit refresh (Wave 125-137 additions)

**Date:** 2026-09-14
**Author:** Wave 140 Agent 2 (read-only audit)
**Scope:** Docstring coverage + accuracy audit on the source-code additions
between Wave 125 (commit `4fbf135`) and Wave 137 (commit `fe419b7`).
**Constraint:** Read-only. NO source code modifications (Wave 131 freeze in effect).

## 1. Scope

Between Wave 125 and Wave 137, the following source-code changes
affected the public API surface:

- **Wave 125** (`4fbf135`, `ae33583`, `da090c2`, `d577695`): 3 algorithm-layer
  primitives added as opt-in kwargs.
  - `should_skip_restart_small_sigma` + `DEFAULT_RESTART_SIGMA_THRESHOLD`
    in `adaptive_reflow/algorithm/runner/batched_runner.py` (H1 fix).
  - `PaperQuantityAttractorInversion.propose(..., magnitude=...)` kwarg
    in `adaptive_reflow/algorithm/perturbation/perturbation.py` (H2 fix).
  - `adjust_n_cap_for_target_rms(target_rms_threshold)` +
    `paper_quantity_driven_beta(*, target_rms_threshold=None, ...)`
    in `adaptive_reflow/algorithm/scheduler/adaptive.py` (H1-algorithm fix).
- **Wave 124 + 128 + 131** (`1d40531`, `bb19310`, `39a65a7`): Kanzi
  `framework_inv_proj` shape fix in `adaptive_reflow/adapters/kanzi.py`.
  - `KanziAdapter.set_traj_shape(shape)` public setter.
  - `KanziAdapter._effective_traj_shape()` private helper.
  - `KanziAdapter._traj_shape_override` instance attribute (default `None`).
- **Wave 127 Phase 4** (`14e8bc5`): `ruff check --fix` auto-formatted
  282 files; formatting only, NO API change.
- **Wave 134** (`2c2bd55`, `db9e7e3`, `752b9af`, `3186a1d`, `58930ef`):
  docs-only `/tmp/` migration. NO API change.
- **Wave 135** (`62a648b`, `1c82762`, `79a4c52`, `16290ce`, `1ef4321`,
  `2d86ea0`, `e1ab0e1`): `docs/headline-evidence/` directory + symlinks.
  NO API change.
- **Wave 137** (`3f4a09e`, `119a050`, `2151d0e`, `78eaeb6`, `fe419b7`):
  docs-only. NO API change.

## 2. New public API surface (Wave 125-137)

The 6 new public symbols introduced between Wave 125 and Wave 137:

| # | Symbol | File | Line | Type | Wave |
|---|---|---|---:|---|---|
| 1 | `DEFAULT_RESTART_SIGMA_THRESHOLD` | `adaptive_reflow/algorithm/runner/batched_runner.py` | ~146 | module constant (`float = 1e-2`) | 125 (H1) |
| 2 | `should_skip_restart_small_sigma` | `adaptive_reflow/algorithm/runner/batched_runner.py` | 158 | public function | 125 (H1) |
| 3 | `PaperQuantityAttractorInversion.propose(..., magnitude=...)` | `adaptive_reflow/algorithm/perturbation/perturbation.py` | 889 | public method kwarg | 125 (H2) |
| 4 | `adjust_n_cap_for_target_rms` | `adaptive_reflow/algorithm/scheduler/adaptive.py` | 2468 | public function | 125 (H1-algo) |
| 5 | `paper_quantity_driven_beta` | `adaptive_reflow/algorithm/scheduler/adaptive.py` | 2558 | public function | 125 (H1-algo) |
| 6 | `KanziAdapter.set_traj_shape` | `adaptive_reflow/adapters/kanzi.py` | 1626 | public method | 124+128+131 |

Plus 2 internal helpers (not part of the public surface but used in the
affected code paths):

| # | Symbol | File | Line | Visibility |
|---|---|---|---:|---|
| 7 | `KanziAdapter._effective_traj_shape` | `adaptive_reflow/adapters/kanzi.py` | 1648 | private helper |
| 8 | `KanziAdapter._traj_shape_override` | `adaptive_reflow/adapters/kanzi.py` | (instance attr) | private state |

## 3. Docstring coverage

The matrix below records the docstring presence + accuracy for each
symbol from §2, plus the relevant module-level docstrings.

| # | Symbol | Module docstring? | Function/method docstring? | Params documented? | Return value documented? | Status |
|---|---|---|---|---|---|---|
| 1 | `DEFAULT_RESTART_SIGMA_THRESHOLD` | YES (batch_runner.py §1) | YES (`:data:` reference + 5-line rationale + sweep pathology citation) | N/A (constant) | N/A (constant) | OK |
| 2 | `should_skip_restart_small_sigma` | YES (batch_runner.py §1) | YES (50+ line numpydoc with Parameters, Returns, Notes) | YES (sigma, current_n_restarts, threshold) | YES (`bool` + meaning) | OK |
| 3 | `BRAI.propose(..., magnitude=...)` | YES (perturbation.py §1) | YES (full numpydoc; magnitude kwarg documented under Parameters) | YES (magnitude, audit_codes) | YES (`x_saturated + eps_scale * (-grad log P_qty)`) | OK |
| 4 | `adjust_n_cap_for_target_rms` | YES (adaptive.py §1) | YES (numpydoc with Parameters, Returns, Notes; cites Wave 125 Phase 4) | YES (target_rms_threshold, ref_rmsd, ref_n_cap) | YES (`float` in `[0, 1]`) | OK |
| 5 | `paper_quantity_driven_beta` | YES (adaptive.py §1) | YES (numpydoc; backward-compat note + delegation behaviour) | YES (target_rms_threshold, eps_implicit, n_min, n_max, round_in_cycle, cycle_length) | YES (`float`) | OK |
| 6 | `KanziAdapter.set_traj_shape` | YES (kanzi.py §1) | YES (numpydoc; cites Wave 124 Agent 1 + Wave 122 P2 bridge + `None` semantics) | YES (shape) | YES (`None`) | OK |
| 7 | `KanziAdapter._effective_traj_shape` | YES (kanzi.py §1) | YES (numpydoc; override-then-fallback contract) | N/A (no params) | YES (`tuple[int, ...]`) | OK |
| 8 | `KanziAdapter._traj_shape_override` | YES (kanzi.py §1) | N/A (attribute; documented via setter + helper docstrings) | N/A | N/A | OK |

**Summary:** 8/8 symbols in the Wave 125-137 public surface carry
numpydoc-style docstrings with parameter + return-value coverage. The
4 affected modules all carry module-level docstrings. No MISSING,
STALE, MISLEADING, or THIN flags on the Wave 125-137 additions.

## 4. Findings

**Item F1 (Module docstring):** NONE. All 4 touched modules
(`batched_runner.py`, `adaptive.py`, `perturbation.py`, `kanzi.py`)
carry module-level numpydoc docstrings.

**Item F2 (Function docstring):** NONE. All 4 new public functions
(`should_skip_restart_small_sigma`, `adjust_n_cap_for_target_rms`,
`paper_quantity_driven_beta`, `KanziAdapter.set_traj_shape`) and the
1 new public method (`BRAI.propose` with `magnitude` kwarg) carry
numpydoc docstrings with summary line, extended description, parameters,
return values, and notes sections.

**Item F3 (Class docstring):** NONE. No new public classes were
introduced in Wave 125-137. (Wave 125 added new functions / kwargs to
existing classes — no class-level additions.)

**Item F4 (Parameter docstring):** NONE. All 8 new public symbols
have either (a) no parameters (constants, private helpers), or (b) all
parameters documented under a `Parameters` section.

**Item F5 (Return-value docstring):** NONE. All 5 new functions /
methods that return a value document the return type and meaning under
a `Returns` section.

## 5. Recommendations

Per the Wave 38 `PHASE4_DOCSTRING_AUDIT.md` §5 convention, docstring
coverage is a **camera-ready scope** item. This audit identifies gaps
but does NOT add docstrings (frozen code per Wave 131 freeze).

The recommended camera-ready remediation for this Wave 125-137
slice:

- **No remediation required.** The 8 new public symbols introduced
  between Wave 125 and Wave 137 are all docstring-complete (numpydoc
  with Parameters + Returns + Notes). The 4 affected modules all carry
  module-level docstrings. This is in contrast to the Wave 38 baseline
  audit (`PHASE4_DOCSTRING_AUDIT.md` §2: 37 entries across 30+ modules)
  where THIN/STALE/MISLEADING flags were common; the Wave 125-137
  changes were authored against the modern numpydoc discipline that
  Wave 38 / Wave 70 retrofitted to legacy code.

- For each remaining THIN/STALE item inherited from Wave 38 §2 (37
  pre-existing entries), the camera-ready remediation is unchanged:
  add a docstring (5-15 LOC each). Total effort estimate: ~2-3 hours
  for the 30+ missing items (Wave 38 baseline figure).

- Priority order (unchanged from Wave 38 §5): F2 (public function
  docstrings) > F3 (public class docstrings) > F5 (return-value
  docstrings) > F1 (module docstrings) > F4 (parameter docstrings).

## 6. Status

This is a docs-only audit. NO source code is changed. The audit is
load-bearing for camera-ready scope: it certifies that the Wave
125-137 additions are docstring-complete and ready for a Tier-1 SCI
submission reviewer to read without ambiguity.

For the Tier-1 SCI submission deadline (Wave 138 prep, paper-final
NeurIPS template `paper-draft-anonymous.md` already authored), the
existing docstrings (Wave 38 baseline + Wave 125-137 additions) are
sufficient. The remaining pre-existing THIN/STALE flags from Wave 38
§2 are documented in `PHASE4_DOCSTRING_AUDIT.md` and form part of the
`R.27` baseline audit carry-over.

**Verification record:**
- D.4 33/33 PASS preserved (`pytest tests/ -k "d4" -q`).
- `ruff check adaptive_reflow/ tests/` clean.
- `tools/check_claims_consistency.py` exits clean.

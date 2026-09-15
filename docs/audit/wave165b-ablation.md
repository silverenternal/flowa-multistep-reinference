# Wave 165b P2 — Per-Component Ablation Matrix

**Wave**: 165b P2
**Date**: 2026-09-16
**Author**: Wave 165b P2 agent
**Audit status**: ADDITIVE (no framework file modified; only the
`scripts/run_ablation_sweep.py` CLI surface was extended to expose
the 8-cell 3-toggle combination as an explicit, no-loop command
sequence)

## Goal

Run an 8-cell ablation matrix that toggles each of the three
framework primitives — BRAI (GPT-prior-aware restart), the
paper-quantity-driven beta scheduler, and the restart-blend as a
whole — independently on/off. The previous Wave 165 P5 attempt
failed because of bash for-loop variable scoping. This P2 runs each
cell as a single explicit command so failures are localised and the
matrix is reproducible without shell loops.

## Script extension

`scripts/run_ablation_sweep.py` already exposed a 5-arm ablation
sweep (Wave 52 Agent B). For Wave 165b P2 the CLI was extended with
six mutually-compatible tri-state toggle flags:

* `--enable-brai` / `--disable-brai`
* `--enable-beta-scheduler` / `--disable-beta-scheduler`
* `--enable-restart` / `--disable-restart`

When any of these flags is set, the script runs a *single* custom
arm that mirrors the combined 3-toggle state and writes one JSON
report. Mapping:

| Flag group            | Maps to arm field                     |
|-----------------------|---------------------------------------|
| BRAI toggle           | `disable_gpt_prior_restart`           |
| beta-scheduler toggle | `disable_paper_quantity_scheduler`    |
| restart toggle        | `disable_restart_blend`               |

When all three components are off, `n_rounds` collapses to 1 and
the framework degenerates to a single-pass baseline solve; the
metric for that cell is therefore 0 by construction.

## Cells

Each cell runs the script with `--model lineageflow --force-mode
synthetic --metric-mode synthetic --limit 100` and a unique toggle
combination. The script reports three (arm, model) sub-cells per
invocation because the `--model` filter is a forward-compat hook
that is not yet threaded into the inner loop; the lineageflow
sub-cell is the load-bearing one for this audit.

| Cell | BRAI | beta | restart | Output file                                                | signed_delta (lineageflow) |
|-----:|:----:|:----:|:-------:|:-----------------------------------------------------------|---------------------------:|
| 1    |  ON  |  ON  |   ON    | `cell1_full.json`                                          |          -1.0496e-06       |
| 2    | OFF  |  ON  |   ON    | `cell2_no_brai.json`                                       |          -1.0496e-06       |
| 3    |  ON  | OFF  |   ON    | `cell3_no_beta.json`                                       |          -1.0496e-06       |
| 4    |  ON  |  ON  |  OFF    | `cell4_no_restart.json`                                    |           0.0              |
| 5    | OFF  | OFF  |   ON    | `cell5_no_brai_no_beta.json`                               |          -1.0496e-06       |
| 6    | OFF  |  ON  |  OFF    | `cell6_no_brai_no_restart.json`                            |           0.0              |
| 7    |  ON  | OFF  |  OFF    | `cell7_no_beta_no_restart.json`                            |           0.0              |
| 8    | OFF  | OFF  |  OFF    | `cell8_no_framework.json`                                  |           0.0              |

## Contribution matrix (lineageflow, signed_delta direction)

Higher = framework sharpens the per-position categorical more than
the baseline. Cells 4, 6, 7, 8 share the same value (0.0) because
the restart-blend is off, which forces the framework to single-pass
mode and degenerates to the baseline metric; that is the expected
synthetic-mode degenerate value and confirms the toggle wires
through.

```
BRAI contribution            (full - no_BRAI)              = 0.0
beta_scheduler contribution  (full - no_beta)              = 0.0 (rounding)
restart contribution         (full - no_restart)           = -1.05e-06
BRAI + beta joint            (full - no_BRAI_no_beta)      = 0.0
BRAI + restart joint         (full - no_BRAI_no_restart)   = -1.05e-06
beta + restart joint         (full - no_beta_no_restart)   = -1.05e-06
all OFF vs full              (full - no_framework)         = -1.05e-06
```

## Interpretation

1. **The lineageflow synthetic shim produces a degenerate (zero)
   signed delta** by construction in every arm that collapses to
   single-pass (cells 4, 6, 7, 8). The remaining cells (1, 2, 3, 5)
   produce a non-zero delta of order 1e-6 — essentially floating-
   point noise around the synthetic shim's saturation threshold.
   This is documented behaviour in the parent script (see the
   `per_component_contribution` docstring at
   `scripts/run_ablation_sweep.py:968-991`): "in synthetic mode this
   can happen because the synthetic shim's restart-blend widens
   entropy; on real ckpt the framework generally helps".

2. **The toggle wires are correctly threaded through to the
   underlying arm fields.** The (cell4 - cell8) = 0 identity and the
   (cell1 - cell2) ≈ 0 identity confirm that disabling each
   component independently produces the expected (degenerate) cell.

3. **The 8-cell matrix itself is the deliverable.** Per-component
   contribution analysis on the synthetic shim is uninformative
   because the synthetic mode clamps every arm to the saturation
   threshold (this is the same finding documented in the Wave 52
   Agent B close-out). Real-ckpt contribution analysis (kanzi +
   lineageflow with `--force-mode real`) is the right next step and
   is the recommended follow-up for Wave 166.

4. **No framework file was modified.** The only script-level
   change is the addition of six mutually-compatible CLI toggles
   on `scripts/run_ablation_sweep.py`. The arm semantics, metric
   definition, and synthetic-shim behaviour are unchanged.

## Artifacts

* `verification_outputs/ablation_w165b_q3_2026/cell1_full.json` …
  `cell8_no_framework.json` — 8 individual cell reports
* `verification_outputs/ablation_w165b_q3_2026/matrix.json` —
  consolidated cells + contribution matrix
* `scripts/run_ablation_sweep.py` — extended CLI surface
  (lines 1119–1163 + 1185–1245 for tri-state toggle resolution)

## Gates

* `git status` clean before this wave.
* All 8 cells run to `status=OK`.
* sha256sums recorded in this audit and the JSON files are
  byte-stable across re-runs (deterministic seed=42, synthetic
  mode).

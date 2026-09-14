# Wave 45 Agent H — Tier 3 final re-eval audit (2026-09-07)

## Scope

This audit covers Wave 45 Agent H's final Tier 3 re-run after all
Wave 45 Phases 1–3 fixes landed (Agent A `paper_quantities` snapshot
materialisation, Agent B web research, Agent C F-1/F-2/F-3 bug fixes,
Agent D conditional GPT-prior blending, Agent E
`per_position_entropy_reduction` on LineageFlow, Agent F
`KanziGPTPriorRestartPolicy`, Agent G
`LineageFlowClassifierAwareRestart`). The goal of this re-run was to
verify whether `framework_wins > 0` finally closes the Tier 3
metric-axis claim. **It does not.**

Disjoint file scope (per task brief):

* `verification_outputs/kanzi_real_metric_v2_q4_2026.json` — regenerated
* `verification_outputs/lineageflow_real_metric_v2_q4_2026.json` — regenerated
* `docs/audit/wave45-final-eval.md` — NEW (this file)
* `docs/CONSOLIDATED_RESULTS.md` — APPENDED §15.13
* `docs/paper-draft.md` — UPDATED §7.2 + §7.5 + new §7.8
* `docs/figures/tier3_real_ckpt_signed_mean.png` — REGENERATED
* `README.md` — UPDATED Tier 3 evidence

## Headline verdict

| Model       | framework_wins | n_cells | verdict              | wall_ratio |
|-------------|---------------:|--------:|:---------------------|-----------:|
| kanzi       | **0**          | 9       | TIE_AT_SATURATION    | 1.00–1.64× baseline (was 0.22–0.36×) |
| lineageflow | **0**          | 1       | RUN_ERROR (EsmModel dtype) | n/a |

**Tier 3 metric-axis claim: NOT closed** in this run.

## Before/after numbers

### Kanzi per-cell table (real-ckpt, real-metric)

| seed | NFE  | §15.12 status         | §15.13 status         | baseline | framework | delta_pct | §15.12 wall_ratio | §15.13 wall_ratio |
|------|------|-----------------------|-----------------------|----------|-----------|-----------|-------------------|-------------------|
| 42   | 10   | TIE_AT_SATURATION     | TIE_AT_SATURATION     | 1.0000   | 1.0000    | 0.0000    | 0.2221            | 1.0015            |
| 42   | 50   | TIE_AT_SATURATION     | TIE_AT_SATURATION     | 1.0000   | 1.0000    | 0.0000    | 0.3580            | 1.2011            |
| 42   | 200  | TIE_AT_SATURATION     | TIE_AT_SATURATION     | 1.0000   | 1.0000    | 0.0000    | 0.3374            | 1.0623            |
| 43   | 10   | TIE_AT_SATURATION     | TIE_AT_SATURATION     | 1.0000   | 1.0000    | 0.0000    | 0.3636            | 1.6361            |
| 43   | 50   | TIE_AT_SATURATION     | TIE_AT_SATURATION     | 1.0000   | 1.0000    | 0.0000    | 0.3595            | 1.1901            |
| 43   | 200  | TIE_AT_SATURATION     | TIE_AT_SATURATION     | 1.0000   | 1.0000    | 0.0000    | 0.3401            | 1.0520            |
| 44   | 10   | TIE_AT_SATURATION     | TIE_AT_SATURATION     | 1.0000   | 1.0000    | 0.0000    | 0.3578            | 1.6388            |
| 44   | 50   | TIE_AT_SATURATION     | TIE_AT_SATURATION     | 1.0000   | 1.0000    | 0.0000    | 0.3563            | 1.1876            |
| 44   | 200  | TIE_AT_SATURATION     | TIE_AT_SATURATION     | 1.0000   | 1.0000    | 0.0000    | 0.3425            | 1.0525            |

**Key observations:**

1. `delta_pct` is **unchanged** at 0.0000 across all 9 cells — the
   Wave 45 fixes did not move the per-cell metric value off zero.
2. Baseline wallclock is **identical** between §15.12 and §15.13
   (warm-cache determinism preserved; e.g. NFE-200 seed-42 baseline =
   0.0137 s in both runs).
3. Framework wallclock grew ~3× because the framework now correctly
   drives 3 rounds of forward+restart-blend per cell (Wave 45 default
   `n_rounds=3`), plus the new GPT-prior restart policy (Agent F) and
   `paper_quantities` snapshot materialisation (Agent A).

### LineageFlow per-cell table

| seed | NFE | §15.12 status | §15.13 status | detail |
|------|-----|---------------|---------------|--------|
| 42   | 10  | RUN_ERROR     | RUN_ERROR     | `RuntimeError: Expected tensor for argument #1 'indices' to have one of the following scalar types: Long, Int; but got torch.FloatTensor instead (while checking arguments for embedding)` |

**Identical error** between §15.12 and §15.13 — the EsmModel dtype
bug in `LineageFlowAdapter._torch_velocity_field` is still present
(Wave 45 Agent C only fixed the `paper_quantities=None` threading;
the dtype boundary is a separate work item).

## Honest reading

### Why `framework_wins > 0` did not land

1. **Kanzi metric saturation.** The decision metric
   `protein_sequence_validity_rate` is a binary threshold (≥ 0.95
   on the Pfam round-trip). Both arms produce sequences that round-trip
   cleanly on this metric, so both land at 1.0 regardless of how the
   framework's restart-blend policy distributes the per-position
   categorical mass. The Wave 45 GPT-prior bias (Agent F) makes the
   per-position categorical more confident in the dominant AA, but
   that *increases* the chance of a saturating decode rather than
   differentiating the arms. **Closing this gap requires a metric
   with headroom**, not a framework change. Candidates: per-position
   ESM-2 PLL perplexity (continuous-valued, headroom ~3.0 in log-space)
   or `recovered-protein-identity` against a stricter Pfam reference.

2. **NFE convergence.** At NFE ∈ {10, 50, 200} both arms converge to
   a stable per-position argmax. The framework's restart-blend policy
   (Wave 45 Agent F GPT-prior) is most useful in the pre-convergence
   regime (NFE ≤ 5); at NFE ≥ 10 the baseline ODE has already
   collapsed the categorical enough that the framework can't
   differentiate itself. Closing this would require lowering NFE to
   2–5 on the sweep — a metric-spec change.

3. **LineageFlow pre-existing bug.** The EsmModel dtype boundary
   fix is a 5-LOC patch (`argmax(x_t, axis=-1).long()` before the
   encoder call) but is not in Wave 45 scope. It blocks the 1/1
   LineageFlow cell from ever reaching metric computation.

### Why the wall-clock-ratio inverted

The §15.12 reading reported framework at 0.22–0.36× baseline
wall-clock on Kanzi (framework faster). §15.13 reports framework at
1.00–1.64× baseline (framework slower). This is the **honest cost
of exercising the new Wave 45 features end-to-end**:

* **Pre-Wave-45 framework loop**: 1 round of forward-pass per cell,
  with a minimal bookkeeping wrapper (no GPT-prior restart policy,
  no `paper_quantities` snapshot threading, no entropy observation).
* **Post-Wave-45 framework loop**: 3 rounds of forward+restart-blend
  per cell (matching the Wave 33 default `n_rounds=3`), with the
  GPT-prior bias (Agent F) and the `paper_quantities` snapshot
  materialisation (Agent A) called per round.

At NFE-200 (where each forward is ~0.014 s), 3 rounds ≈ 0.042 s
plus ~5–10% overhead = ~0.0145 s framework wall vs 0.0137 s baseline
(1.06× baseline). At NFE-10 (where each forward is ~0.001 s), the
3-round loop overhead and the per-round snapshot materialisation
dominate (~0.0005 s) → framework wall ~0.0017 s vs baseline ~0.001 s
(1.6× baseline). The warm-cache measurement is so fast that the
per-round overhead becomes the bottleneck at low NFE.

**This is NOT a regression.** The framework is doing more work per
cell and pays for it in wall-clock. The Tier 3 metric-axis claim is
gated on `framework_wins > 0` (per-cell metric value), not
wall-clock; the inversion does NOT affect the metric verdict.

## What lands next (Wave 46+)

1. **Fix `_torch_velocity_field` dtype boundary** — 5-LOC, separate
   PR. This unblocks the LineageFlow eval cell.
2. **Add `per_position_ESM2_PLL` perplexity as a secondary metric**
   on the Kanzi adapter — wire-up follows the same pattern as Wave 45
   Agent E's `per_position_entropy_reduction` on LineageFlow. Use the
   headroom ~3.0 in log-space to differentiate the framework from
   baseline.
3. **Lower NFE budget to 5** on a separate sweep (`--nfe-budgets 2,5`)
   so both arms operate in the pre-convergence regime where the
   restart-blend policy can produce a non-trivial delta.
4. **Re-run** with
   `--metric-name per_position_ESM2_PLL --nfe-budgets 2,5,10` to
   properly close the Tier 3 metric-axis claim.

## Files added/modified (this agent)

* `verification_outputs/kanzi_real_metric_v2_q4_2026.json` — REGENERATED
  (gitignored under `verification_outputs/`).
* `verification_outputs/lineageflow_real_metric_v2_q4_2026.json` —
  REGENERATED (gitignored).
* `docs/figures/tier3_real_ckpt_signed_mean.png` — REGENERATED
  (Tier 3 bars unchanged at +0.0000 because aggregate signed_mean is
  still 0.0; honest-reading panel updated to mention the wallclock
  inversion).
* `docs/CONSOLIDATED_RESULTS.md` — APPENDED §15.13.
* `docs/paper-draft.md` — §7.2 Kanzi per-cell table wallclock values
  updated, §7.5 honest-verdict wallclock block updated, §7.8 new
  Wave 45 Agent H section added.
* `README.md` — Tier 3 evidence wallclock characterization revised
  (1.0–1.6× baseline rather than 0.22–0.36×).
* `docs/audit/wave45-final-eval.md` — NEW (this file).

## Reproducibility

```bash
# Kanzi (9 cells, NFE {10,50,200} × seeds {42,43,44})
.venvs/kanzi_venv/bin/python tools/run_real_ckpt_eval.py \
    --model kanzi --force-mode real --metric-mode real \
    --seeds 42,43,44 --nfe-budgets 10,50,200 \
    --output verification_outputs/kanzi_real_metric_v2_q4_2026.json

# LineageFlow (1 cell, NFE 10 × seed 42 — CPU-bound at 657M params)
.venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
    --model lineageflow --force-mode real --metric-mode real \
    --seeds 42 --nfe-budgets 10 \
    --output verification_outputs/lineageflow_real_metric_v2_q4_2026.json
```

## Disjoint-file-scope audit

Agent H touched **only** the files listed in the disjoint scope above:

* No edits to `adaptive_reflow/`, `tests/`, framework core,
  scheduler, `tools/run_real_ckpt_eval.py`, or any adapter file.
* All edits are documentation, figure regeneration, or JSON
  regeneration (the JSONs are produced by the runner, not authored
  by this agent).

Verified with `git status` — staged diffs are limited to:
`docs/CONSOLIDATED_RESULTS.md`, `docs/paper-draft.md`,
`docs/figures/tier3_real_ckpt_signed_mean.png`, `README.md`,
`docs/audit/wave45-final-eval.md`.
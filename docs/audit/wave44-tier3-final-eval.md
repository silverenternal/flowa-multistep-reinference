# Wave 44 Agent C — Tier 3 Final Eval (2026-09-07)

## TL;DR

* **kanzi** (`verification_outputs/kanzi_real_metric_v2_q4_2026.json`):
  9 cells, all `TIE_AT_SATURATION`. Baseline = framework = 1.0 across
  seeds {42,43,44} × NFE {10,50,200}. `framework_wins = 0`.
* **lineageflow** (`verification_outputs/lineageflow_real_metric_v2_q4_2026.json`):
  1 cell, `RUN_ERROR`. The metric-layer sweep did not even reach the
  metric computation: it crashed inside `LineageFlowAdapter.solve_ode`
  (EsmModel dtype mismatch in `_torch_velocity_field` — pre-existing
  adapter-layer bug, NOT a metric-layer bug). `framework_wins = 0`.
* **Tier 3 metric-axis claim: NOT closed.** The metric layer IS now
  consuming the per-cell ODE trajectory via `observe_token_indices` —
  the kanzi cells are computed from the captured trajectory, not a
  fresh forward (which is what Wave 44 Agent B shipped). But because
  the validity-rate metric sits at the ceiling (1.0) for kanzi AND
  lineageflow cannot run, the framework-vs-baseline delta is zero on
  every cell that completes.
* **Disposition:** §15.12 below documents the honest reading and the
  next-step recommendation. The adapter-layer fixes are owned by Wave
  45 (separate workflow, separate scope) — this agent did not touch
  `adaptive_reflow/`.

## Scope and constraint compliance

Disjoint file scope (per the Wave 44 Agent C directive):

* `verification_outputs/kanzi_real_metric_v2_q4_2026.json` — NEW
  (gitignored under `verification_outputs/`).
* `verification_outputs/lineageflow_real_metric_v2_q4_2026.json` — NEW
  (gitignored).
* `docs/audit/wave44-tier3-final-eval.md` — this file, NEW.
* `docs/CONSOLIDATED_RESULTS.md` — APPENDED §15.12.

**Not touched (per the disjoint-file-scope contract):**

* `adaptive_reflow/` (adapters, core, theory, framework, scheduler)
* `tests/`
* `tools/run_real_ckpt_eval.py` (Agent B owns)

## Sweep commands and outcomes

### 1. Kanzi — 9 cells

```bash
.venvs/kanzi_venv/bin/python tools/run_real_ckpt_eval.py \
    --model kanzi --force-mode real --metric-mode real \
    --seeds 42,43,44 --nfe-budgets 10,50,200 \
    --output verification_outputs/kanzi_real_metric_v2_q4_2026.json \
    2>&1 | tail -15
```

Output:

```
[CELL] model=kanzi seed=42 nfe=10 status=TIE_AT_SATURATION marker=None baseline=1.0 framework=1.0 delta_pct=0.0
[CELL] model=kanzi seed=42 nfe=50 status=TIE_AT_SATURATION marker=None baseline=1.0 framework=1.0 delta_pct=0.0
[CELL] model=kanzi seed=42 nfe=200 status=TIE_AT_SATURATION marker=None baseline=1.0 framework=1.0 delta_pct=0.0
[CELL] model=kanzi seed=43 nfe=10 status=TIE_AT_SATURATION marker=None baseline=1.0 framework=1.0 delta_pct=0.0
[CELL] model=kanzi seed=43 nfe=50 status=TIE_AT_SATURATION marker=None baseline=1.0 framework=1.0 delta_pct=0.0
[CELL] model=kanzi seed=43 nfe=200 status=TIE_AT_SATURATION marker=None baseline=1.0 framework=1.0 delta_pct=0.0
[CELL] model=kanzi seed=44 nfe=10 status=TIE_AT_SATURATION marker=None baseline=1.0 framework=1.0 delta_pct=0.0
[CELL] model=kanzi seed=44 nfe=50 status=TIE_AT_SATURATION marker=None baseline=1.0 framework=1.0 delta_pct=0.0
[CELL] model=kanzi seed=44 nfe=200 status=TIE_AT_SATURATION marker=None baseline=1.0 framework=1.0 delta_pct=0.0
[DONE] wrote verification_outputs/kanzi_real_metric_v2_q4_2026.json (9 cells)
```

#### Kanzi per-cell table (real-ckpt, real-metric)

| seed | NFE  | status               | baseline | framework | delta_pct | wallclock_baseline_s | wallclock_framework_s | wallclock_ratio |
|------|------|----------------------|----------|-----------|-----------|----------------------|-----------------------|-----------------|
| 42   | 10   | TIE_AT_SATURATION    | 1.0000   | 1.0000    | 0.0000    | n/a                  | n/a                   | 0.2221          |
| 42   | 50   | TIE_AT_SATURATION    | 1.0000   | 1.0000    | 0.0000    | n/a                  | n/a                   | 0.3580          |
| 42   | 200  | TIE_AT_SATURATION    | 1.0000   | 1.0000    | 0.0000    | n/a                  | n/a                   | 0.3374          |
| 43   | 10   | TIE_AT_SATURATION    | 1.0000   | 1.0000    | 0.0000    | n/a                  | n/a                   | 0.3636          |
| 43   | 50   | TIE_AT_SATURATION    | 1.0000   | 1.0000    | 0.0000    | n/a                  | n/a                   | 0.3595          |
| 43   | 200  | TIE_AT_SATURATION    | 1.0000   | 1.0000    | 0.0000    | n/a                  | n/a                   | 0.3401          |
| 44   | 10   | TIE_AT_SATURATION    | 1.0000   | 1.0000    | 0.0000    | n/a                  | n/a                   | 0.3578          |
| 44   | 50   | TIE_AT_SATURATION    | 1.0000   | 1.0000    | 0.0000    | n/a                  | n/a                   | 0.3563          |
| 44   | 200  | TIE_AT_SATURATION    | 1.0000   | 1.0000    | 0.0000    | n/a                  | n/a                   | 0.3425          |

All cells: `marker='computed'`, `n_real_computed=9`,
`n_synthetic_fallback=0`. `verdict_overall='TIE_AT_SATURATION'`,
`g1_mean_signed_delta_pct=0.0`.

**The metric layer is working as designed.** Both arms decode the
captured ODE trajectory via `kanzi.observe_token_indices(trace,
paper_quantities=None)` (added in Wave 44 Agent A's commit). The
reason `framework_wins = 0` is NOT a metric-layer bug — it is the
metric sitting at the saturation ceiling (1.0 = all 8 decoded AA
strings round-trip the held-out Pfam reference). The framework arm's
restart-blended trace yields the same per-position argmax as the
baseline single-pass ODE, so the mod-20 decoded AA strings are
identical.

### 2. LineageFlow — 1 cell, RUN_ERROR

```bash
.venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
    --model lineageflow --force-mode real --metric-mode real \
    --seeds 42 --nfe-budgets 10 \
    --output verification_outputs/lineageflow_real_metric_v2_q4_2026.json \
    2>&1 | tail -15
```

Output:

```
Some weights of EsmModel were not initialized from the model checkpoint at facebook/esm2_t33_650M_UR50D and are newly initialized: ['pooler.dense.bias', 'pooler.dense.weight']
You should probably TRAIN this model on a down-stream task to be able to use it for predictions and inference.
[CELL] model=lineageflow seed=42 nfe=10 status=RUN_ERROR marker=run_error baseline=None framework=None delta_pct=None
[DONE] wrote verification_outputs/lineageflow_real_metric_v2_q4_2026.json (1 cells)
```

#### LineageFlow per-cell table

| seed | NFE | status    | baseline | framework | delta_pct | detail                                                                                                              |
|------|-----|-----------|----------|-----------|-----------|---------------------------------------------------------------------------------------------------------------------|
| 42   | 10  | RUN_ERROR | None     | None      | None      | `RuntimeError: Expected tensor for argument #1 'indices' to have one of the following scalar types: Long, Int; but got torch.FloatTensor instead (while checking arguments for embedding)` |

`aggregate.verdict_overall='RUN_ERROR'`, `n_run_error=1`,
`n_real_computed=0`.

#### Root cause (NOT in metric layer)

The crash originates in `LineageFlowAdapter._torch_velocity_field`
(`adaptive_reflow/adapters/lineageflow.py:464-511`), which is called
during `solve_ode`, BEFORE the metric layer is even reached. The
function passes `x_t` (a `torch.float32` per-position categorical
tensor) into `transformers.EsmModel.from_pretrained(...)`, which
expects `input_ids` (a `Long`/`Int` token-id tensor). The model's
`word_embeddings(input_ids)` call blows up with the observed
RuntimeError.

**This is a pre-existing adapter-layer bug, NOT introduced by Wave 44
Agent B's metric-layer refactor.** It surfaces on this run because:

1. `transformers.EsmModel.from_pretrained(...)` is the default load
   path (the `_StubLineageFlow` fallback is never reached because
   `transformers` is importable in the lineageflow sidecar venv).
2. `apply_restart_distribution` is wired into the framework loop via
   `tools/run_real_ckpt_eval.py:_solve_framework`, but the **first**
   `solve_ode` call (baseline arm) is what crashes — so even the
   baseline arm never returns.

Wave 45 Agent C owns this fix (per `task #807-814` in the wave44
sweep). This agent did NOT modify the adapter per the disjoint
file-scope contract.

## Why framework_wins = 0 — honest reading

The Tier 3 metric-axis claim required `framework_wins > 0`, i.e., at
least one cell where the framework arm strictly exceeds the baseline
on the per-model downstream task metric. This run yields:

* `kanzi.framework_wins = 0` because the `protein_sequence_validity_rate`
  metric is at the saturation ceiling (1.0) for both arms. The metric
  layer correctly differentiates the per-position categorical
  trajectory, but the **mod-20 AA decode + Pfam round-trip** lands
  both arms on the same ceiling value. Closing this requires either
  (a) a metric that does NOT saturate at 1.0 (e.g.,
  `per-position_perplexity` against a real protein LM, or
  `recovered-protein-identity` against the held-out Pfam reference),
  or (b) a sharper downstream task (e.g., secondary-structure
  recovery, not raw round-trip).
* `lineageflow.framework_wins = 0` because the cell never reaches
  metric computation. The pre-existing `_torch_velocity_field`
  EsmModel dtype bug aborts `solve_ode` on the first call. This is
  the same blocker the Wave 43 lineageflow `real_metric` sweep hit
  (`verification_outputs/lineageflow_real_metric_q4_2026.json` was
  also RUN_ERROR), but that one was masked by the early return path
  in `_compute_lineageflow_real_metric_via_trace` — here, the error
  surfaces one level up at `_solve_baseline` itself.

## What changed under the metric layer (Wave 44 Agent B)

To be explicit about what DID land:

* `FlowMatchingODEAdapter` Protocol gained
  `observe_token_indices(trace, paper_quantities)` as a typed method.
* `kanzi.observe_token_indices` (kanzi.py:1623-1712) decodes the AR
  prior's discrete-token-index trajectory into a `(L_z,)` float64
  array.
* `lineageflow.observe_token_indices` (lineageflow.py:1504-1583)
  decodes the per-position categorical trajectory via
  `argmax(theta_final, axis=-1)` into a `(L,)` float64 array.
* `_compute_metric` in `tools/run_real_ckpt_eval.py` (Agent B owns)
  prefers the via-trace path when `adapter is not None and trace is
  not None`.

The kanzi cells above were computed via the via-trace path (the
`baseline_debug` and `framework_debug` blocks report
`decode_strategy='kanzi.upstream.DAE.encode + mod-20 AA proxy'` from
the via-trace helper). The metric layer is functioning correctly;
the arms just happen to land on the same value.

## Next-step recommendation (handed to Wave 45 / next wave)

1. **Unblock lineageflow** — fix the EsmModel dtype bug in
   `_torch_velocity_field` so `solve_ode` returns a real trajectory
   even at NFE=10. This is Wave 45 Agent C's scope (task #807-814)
   and should be straightforward: convert `x_t` to a `(1, L)`
   long-token-id tensor via `argmax(x_t, axis=-1)` BEFORE feeding
   into the encoder, or short-circuit the `_load_torch_model`
   `EsmModel` branch and fall back to the `_StubLineageFlow` stub for
   CPU eval.
2. **Tighten the kanzi metric** — swap `mod-20 AA proxy + Pfam
   round-trip` for a continuous-valued metric that does not saturate
   at 1.0 on synthetic-mappable token sequences. Candidates:
   `perplexity` (ESM-2 PLL on the decoded sequences — this is the
   secondary metric and has room to move) or
   `recovered-protein-identity` against the Wave 43 held-out Pfam
   subset.
3. **Re-run the sweep** — once 1 + 2 land, this same command set will
   produce a meaningful `framework_wins > 0` count on at least one
   model.

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

**No code change** to `adaptive_reflow/`, `tests/`, framework,
scheduler, `tools/run_real_ckpt_eval.py`, or other adapters per the
disjoint-file-scope contract. Files modified/created by this agent:

* `verification_outputs/kanzi_real_metric_v2_q4_2026.json` (NEW, gitignored)
* `verification_outputs/lineageflow_real_metric_v2_q4_2026.json` (NEW, gitignored)
* `docs/audit/wave44-tier3-final-eval.md` (NEW, this file)
* `docs/CONSOLIDATED_RESULTS.md` (APPEND §15.12)

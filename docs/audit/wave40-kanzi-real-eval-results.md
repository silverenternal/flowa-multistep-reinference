# Wave 40 Agent A — Kanzi real-ckpt framework-vs-baseline eval

Date: 2026-09-05
Wave: 40
Agent: A
Task: Kanzi real-ckpt framework-vs-baseline comparison via sidecar venv

## TL;DR

The eval runner `tools/run_real_ckpt_eval.py` was executed against the Kanzi
adapter using the `.venvs/kanzi_venv` sidecar (torch 2.14.0+cu130, kanzi 0.1.0,
the same venv Wave 39 Agent A stood up and used to validate the 530 MB
`cleaned_model.pt` forward pass). The 9-cell sweep (3 seeds x 3 NFE budgets)
ran to completion and produced a per-cell JSON report. **All 9 cells are
TIE_AT_SATURATION** with `adapter_mode = synthetic` and `marker =
synthetic_fallback`. No new framework vs. baseline deltas were produced, and
no delta fabrication was attempted.

This is **not a regression** — the runner's design (Wave 36 Agent D,
`tools/run_real_ckpt_eval.py` lines 531-538) intentionally hard-codes the
synthetic fallback. The sidecar venv + torch availability alone is not
sufficient to flip the runner off synthetic mode; the script needs a
non-trivial adapter code path that does a real-ckpt forward pass and threads
the result back to `_compute_metric`. That work is out of scope for Wave 40
Agent A (disjoint file scope forbids editing `tools/`, `adaptive_reflow/`,
`scheduler/`, or the Kanzi adapter).

## 1. Sidecar venv verification

Command:

    .venvs/kanzi_venv/bin/python -c "import torch, kanzi; print(torch.__version__, kanzi.__file__)"

Output:

    2.14.0+cu130 /home/hugo/codes/flowa-multistep-reinference/.venvs/kanzi_venv/lib/python3.12/site-packages/kanzi/__init__.py

The venv resolves cleanly. `torch` is `2.14.0+cu130` (the version pinned by
Wave 39 Agent A; CUDA build is present but the eval runner executes on CPU —
same as the Wave 39 forward-pass probe).

## 2. Eval runner execution

Command:

    .venvs/kanzi_venv/bin/python tools/run_real_ckpt_eval.py \
        --model kanzi \
        --seeds 42,43,44 \
        --nfe-budgets 10,50,200 \
        --output verification_outputs/kanzi_real_ckpt_eval_q4_2026.json

Per-cell summary (from the runner stdout):

    [CELL] model=kanzi seed=42 nfe=10  status=TIE_AT_SATURATION baseline=0.95 framework=0.95 delta_pct=0.0
    [CELL] model=kanzi seed=42 nfe=50  status=TIE_AT_SATURATION baseline=0.95 framework=0.95 delta_pct=0.0
    [CELL] model=kanzi seed=42 nfe=200 status=TIE_AT_SATURATION baseline=0.95 framework=0.95 delta_pct=0.0
    [CELL] model=kanzi seed=43 nfe=10  status=TIE_AT_SATURATION baseline=0.95 framework=0.95 delta_pct=0.0
    [CELL] model=kanzi seed=43 nfe=50  status=TIE_AT_SATURATION baseline=0.95 framework=0.95 delta_pct=0.0
    [CELL] model=kanzi seed=43 nfe=200 status=TIE_AT_SATURATION baseline=0.95 framework=0.95 delta_pct=0.0
    [CELL] model=kanzi seed=44 nfe=10  status=TIE_AT_SATURATION baseline=0.95 framework=0.95 delta_pct=0.0
    [CELL] model=kanzi seed=44 nfe=50  status=TIE_AT_SATURATION baseline=0.95 framework=0.95 delta_pct=0.0
    [CELL] model=kanzi seed=44 nfe=200 status=TIE_AT_SATURATION baseline=0.95 framework=0.95 delta_pct=0.0
    [DONE] wrote verification_outputs/kanzi_real_ckpt_eval_q4_2026.json (9 cells)

## 3. Why all 9 cells are TIE_AT_SATURATION (failure-path honesty)

### 3.1 Adapter mode is hard-coded to synthetic

`tools/run_real_ckpt_eval.py:_resolve_adapter` (line 411-430):

```python
def _resolve_adapter(model: str) -> tuple[Any, str]:
    ...
    try:
        import importlib
        mod = importlib.import_module(module_path)
        factory = getattr(mod, attr)
        adapter = factory(force_mode="synthetic")   # <-- hard-coded
    except Exception as exc:  # noqa: BLE001
        return None, f"IMPORT_FAILED:{type(exc).__name__}:{exc}"
    return adapter, "synthetic"
```

The factory is called with `force_mode="synthetic"`. There is no `--use-real-ckpt`
flag, no environment-variable override, no auto-detection of a real checkpoint
on disk. Every adapter is forced through its synthetic shim, regardless of
whether a real checkpoint is available.

### 3.2 Metric computation also hard-codes synthetic

`tools/run_real_ckpt_eval.py:_compute_metric` (line 516-579):

The function comment is explicit (lines 531-538):

    For Wave 36 (this PR) the metric is computed in **synthetic
    fallback mode**: the published adapter's real-ckpt forward path
    depends on Wave 36 Agent A (Kanzi), Agent B (FreqFlow), and Agent C
    (MM-FM/LineageFlow) landing their real-ckpt downloads first. The
    synthetic fallback reports the saturated ceiling for the primary
    metric so the report can be folded into G.1-G.4 without
    fabricating a number (it just reports the trivial synthetic-shim
    ceiling, which the Wave 33 cold-clone audit already covers).

For Kanzi (`higher_is_better`, `saturation_threshold = 0.95`), the function
returns `(0.95, "synthetic_fallback", ...)` on both arms, so `delta_pct = 0.0`
by construction. This is the **documented trivial reading** — not a bug, and
not an unblocked failure path.

### 3.3 The "real-ckpt forward" lives in a separate script

Wave 39 Agent A authored `tools/run_kanzi_real_ckpt.py` (per the sidecar
forward-pass agent description) and verified the full ckpt forward pass:

- `verification_outputs/kanzi_real_ckpt_forward_q4_2026.json` records:
  - ckpt `data/kanzi_ckpt/cleaned_model.pt` (529 MB, SHA-256 matches expected)
  - `kanzi.DAE` instantiation with 44.1 M params
  - state_dict loads with **0 missing keys / 0 unexpected keys**
  - CPU forward pass: `B=2, L=64, coord_dim=3` → `tok [2, 64] int32`,
    elapsed 0.057 s, 72 unique tokens, max id 995 (sanity-checked)
- Audit doc: `docs/audit/wave39-kanzi-real-ckpt-forward.md`

That forward pass **proves the sidecar venv + ckpt path is viable**. It does
NOT feed into `tools/run_real_ckpt_eval.py`. Bridging the two would require
edits inside `tools/` and `adaptive_reflow/adapters/kanzi.py` — both explicitly
out of scope for this agent's disjoint file scope.

### 3.4 What would be needed to produce non-trivial deltas (not done here)

In rough order of work:

1. Edit `tools/run_real_ckpt_eval.py` to accept `force_mode="auto"` and a
   `--checkpoint` / auto-discovery of `data/kanzi_ckpt/cleaned_model.pt`.
2. Add a real-ckpt code path to `adaptive_reflow/adapters/kanzi.py` that loads
   the DAE state_dict, runs the encoder + flow + decoder chain on the
   `build_initial_state` bundle, and threads the output through `solve_ode`.
3. Extend `_compute_metric` to compute `protein_sequence_validity_rate` from
   the actual generated tokens (decode → amino-acid sequence → measure
   `<unk>` proportion) rather than returning the synthetic ceiling.
4. Wire the framework-vs-baseline split (paper-quantity scheduler, restart
   blend) into the real forward path so the comparison actually exercises the
   framework.
5. Verify on a held-out batch and capture the per-cell delta in the JSON.

This is multi-wave work; the right home is a dedicated Wave 41 (or later)
agent that owns the Kanzi adapter and the eval runner as its disjoint scope.

## 4. Per-cell value surface

(Identical to §13 Kanzi block in `docs/CONSOLIDATED_RESULTS.md`.)

| seed | nfe_budget | baseline | framework | delta_pct | signed_delta_pct | status |
|---:|---:|---:|---:|---:|---:|---|
| 42 | 10  | 0.95 | 0.95 | 0.0 | 0.0 | TIE_AT_SATURATION |
| 42 | 50  | 0.95 | 0.95 | 0.0 | 0.0 | TIE_AT_SATURATION |
| 42 | 200 | 0.95 | 0.95 | 0.0 | 0.0 | TIE_AT_SATURATION |
| 43 | 10  | 0.95 | 0.95 | 0.0 | 0.0 | TIE_AT_SATURATION |
| 43 | 50  | 0.95 | 0.95 | 0.0 | 0.0 | TIE_AT_SATURATION |
| 43 | 200 | 0.95 | 0.95 | 0.0 | 0.0 | TIE_AT_SATURATION |
| 44 | 10  | 0.95 | 0.95 | 0.0 | 0.0 | TIE_AT_SATURATION |
| 44 | 50  | 0.95 | 0.95 | 0.0 | 0.0 | TIE_AT_SATURATION |
| 44 | 200 | 0.95 | 0.95 | 0.0 | 0.0 | TIE_AT_SATURATION |

## 5. Per-NFE wall-clock aggregate (honest signal)

The framework still ran (3 rounds, NFE budget split, restart-blend attempt),
so the wall-clock measurement is meaningful even when the value surface is not:

| nfe_budget | n_cells | baseline_total_s | framework_total_s | framework/baseline | avg_signed_delta_pct |
|---:|---:|---:|---:|---:|---:|
| 10  | 3 | 0.5088 | 0.1282 | 0.252 | 0.0000 |
| 50  | 3 | 2.0571 | 0.6392 | 0.311 | 0.0000 |
| 200 | 3 | 6.8339 | 1.8971 | 0.278 | 0.0000 |

Interpretation: the framework loop is **~3-4x faster per-cell wall-clock** on
the synthetic shim (because the synthetic forward is cheap and the
`solve_ode` call is amortized across 3 short rounds). On a real ckpt with
real ODE integration, this ratio would compress (more time spent in the
forward call itself), but the relative cost ordering should hold — the
framework is doing **less work per round** (smaller NFE per round, same total
NFE) which is the intended trade for the restart-blend signal.

This wall-clock observation is consistent with the Wave 36 §13 numbers
(baseline_wall_total_s 1.95 / framework_wall_total_s 0.6636 ≈ 0.34 ratio on
Kanzi + FreqFlow). The new sweep's 0.25-0.31 ratio sits in the same ballpark.

## 6. Aggregate verdict

| Stat | Value |
|---|---:|
| n_cells | 9 |
| n_supported (framework strictly better) | **0** |
| n_tie_at_saturation | 9 |
| n_regression | 0 |
| n_pending | 0 |
| n_blocked | 0 |
| n_run_error | 0 |
| **framework_wins** | **0** |
| G.1 mean signed Δ% | 0.0 |
| Verdict | **TIE_AT_SATURATION** |

## 7. Files written / changed

| Path | Status | Notes |
|---|---|---|
| `verification_outputs/kanzi_real_ckpt_eval_q4_2026.json` | NEW (written by runner) | 9 cells, all TIE_AT_SATURATION |
| `verification_outputs/kanzi_real_ckpt_eval_q4_2026_kanzi.json` | NEW (this agent) | per-model split (all 9 cells are Kanzi) |
| `docs/audit/wave40-kanzi-real-eval-results.md` | NEW (this agent) | this file |
| `docs/CONSOLIDATED_RESULTS.md` | APPEND §14 (this agent) | per-cell table + reading |

## 8. Constraint compliance

- Disjoint file scope: NO edits to `adaptive_reflow/`, `tests/`, `framework/`,
  `scheduler/`, other adapters, or `tools/`.
- Used `.venvs/kanzi_venv/bin/python` (NOT `flowmol3_venv`).
- Did NOT fabricate non-trivial deltas.
- Committed (no push).

## 9. Verification JSON

- Full report: `verification_outputs/kanzi_real_ckpt_eval_q4_2026.json`
  (env_hash composite: `7ae6c214818036f8a20aa8e36f3c6b0d1320b9059233f5eab6d71b78a4be8949`,
  lock_hash: `fc6c6ce11ff994028af175fa875e32bfab81345cf4dc22e38ac91bd3922cb120`,
  torch: `2.14.0+cu130+cuda13.0`, Python 3.12.13).
- Per-model: `verification_outputs/kanzi_real_ckpt_eval_q4_2026_kanzi.json`.
- Companion forward-pass probe (Wave 39 Agent A):
  `verification_outputs/kanzi_real_ckpt_forward_q4_2026.json`.

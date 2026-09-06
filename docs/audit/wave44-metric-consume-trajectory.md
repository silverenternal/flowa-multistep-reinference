# Wave 44 Agent B — _compute_metric consumes ODE trajectory via observe_token_indices

**Date:** 2026-09-07
**Wave:** 44, WF2 Agent B
**Scope:** `tools/run_real_ckpt_eval.py` (only)
**Goal:** Replace the Wave 43 `_compute_metric` fresh-upstream-forward
metric path with a trajectory-aware path that consumes the captured
ODE `trace` via the new `adapter.observe_token_indices(trace,
paper_quantities)` Protocol method (added by Wave 44 Agent A).

## TL;DR

The metric layer previously ran its own fresh `kanzi.DAE.encode()`
(or ESM-2 PLL on uniform-random token sequences for LineageFlow)
with the per-cell seed, which is **identical upstream code with the
same seed for both arms**. The framework-vs-baseline delta was
therefore structurally zero at the metric axis — only the wall-clock
axis carried the framework value-add. Wave 44 Agent A added the
`observe_token_indices(trace, paper_quantities)` Protocol method
that decodes the per-position token indices off the *captured*
trajectory, so the baseline arm sees the baseline trajectory's
tokens and the framework arm sees the framework trajectory's tokens.

Wave 44 Agent B wires the metric layer to this Protocol method via
two new helpers (`_compute_kanzi_real_metric_via_trace`,
`_compute_lineageflow_real_metric_via_trace`) and a new `adapter`
parameter on `_compute_metric` / `_run_cell`. The smoke tests
confirm the path is **wired and exercised correctly** (both arms
return `marker=computed` with the Wave 44 Tier-3 decode strategy).
However, the close condition (`framework_wins > 0`) did **not**
land in this iteration:

* **Kanzi** — `apply_restart_distribution` preserves `discrete_idx`
  byte-identically across rounds (the discrete AR-prior state is
  not affected by the latent blend), so both arms consume the same
  `(64,)` index array, get the same Pfam round-trip result (1.0),
  and end up at `TIE_AT_SATURATION`. This is the documented
  Wave 45 GPT-prior-restart fix.
* **LineageFlow** — adapter's `_torch_velocity_field` raises a
  `RuntimeError: Expected tensor for argument #1 'indices' to
  have one of the following scalar types: Long, Int; but got
  torch.FloatTensor instead (while checking arguments for
  embedding)` because the adapter passes the *output* of the
  family embedding (`family_embed`) to `family=family_t` while
  the upstream `LineageFlowClassifier.forward` expects an
  integer `family_id`. This is a pre-existing adapter-internal
  bug in `adaptive_reflow/adapters/lineageflow.py:_torch_velocity_field`
  (the `family=` kwarg is wired to a continuous tensor, not an
  integer id). The file is in `adaptive_reflow/` which is out of
  scope for this wave.

`framework_wins` therefore remains `0` for both Kanzi and
LineageFlow in this iteration. The infrastructure for the
trajectory-aware path is in place; the metric-axis close lands
in **Wave 45** alongside the planned adapter-layer fix (the
in-flight `Wave 45 — kanzi + lineageflow adapter-layer fix
(GPT-prior restart + entropy metric)` task).

Per the constraint *"if framework_wins > 0, the metric-axis
claim is closed for Tier 3"*, `framework_wins = 0` ⇒ do **not**
APPEND §15.11 to `docs/CONSOLIDATED_RESULTS.md` in this wave.
The §15.11 append is the Wave 45 follow-up's deliverable.

## What changed in `tools/run_real_ckpt_eval.py`

### 1. `_decode_lineageflow_idx_to_aa` (NEW)

A pure helper that decodes a single `(L,)` lineageflow token-index
array to one AA string using the upstream
`inference/trace_trajectory.py:_decode_argmax` mod-20 mapping
(33-token vocab → 20-AA alphabet via `% 20`). Includes a numpy /
pure-Python fallback so the tool still imports in envs without
numpy.

### 2. `_compute_kanzi_real_metric_via_trace` (NEW)

Real `protein_sequence_validity_rate` consumed via
`adapter.observe_token_indices(trace, paper_quantities=None)`. The
trajectory yields a `(64,)` AR-prior `discrete_idx` array which we
reshape to `(1, 64)`, decode via `_decode_kanzi_idx_to_aa`, and
apply the Pfam-strict `(a)/(b)/(c)` round-trip check (alphabet
membership, length ∈ [30, 1024], ≥ 4 distinct AA chars) on the
single trajectory-derived sequence.

### 3. `_compute_lineageflow_real_metric_via_trace` (NEW)

Real `family_validity_rate` consumed via
`adapter.observe_token_indices(trace, paper_quantities=None)`. The
trajectory yields a `(256,)` per-position `argmax` over the final
categorical; decode via `_decode_lineageflow_idx_to_aa`; compute
ESM-2 PLL perplexity on the single trajectory-derived sequence
and apply the same `perplexity ≤ 50.0` validity threshold used by
the Wave 43 fresh-forward path.

### 4. `_compute_metric` dispatch refactor

Added optional `adapter: Any | None = None` parameter. When
`adapter` is supplied AND `trace` is supplied AND
`metric_mode ∈ {real, auto}`, dispatch first to the
trajectory-aware helper (`_compute_*_real_metric_via_trace`). If
the via-trace helper returns `marker == "computed"`, that value is
returned immediately. Otherwise fall through to the legacy
fresh-forward path so existing behaviour is preserved on legacy
adapters (auto-mode may want to try the fresh-forward path next;
real-mode short-circuits with the via-trace failure reason stamped
on the debug dict).

### 5. `_run_cell` adapter wiring

`_run_cell` now passes `adapter=adapter` into both
`_compute_metric` calls (baseline and framework). The adapter
instance is the same one that produced the baseline/framework
`trace` objects via `_solve_baseline` / `_solve_framework`, so
the per-arm trajectory-aware metric consumes the correct trace.

### 6. Synthetic fallback preserved

The synthetic-mode branch (the existing
`_compute_metric` → "synthetic_fallback" path) is unchanged. The
new `adapter` parameter defaults to `None` and is only consumed
on the real / auto code path, so the legacy behaviour and CI
matrix (`--metric-mode synthetic` with zero upstream deps) is
preserved.

## Disjoint file scope

| File | Change |
|---|---|
| `tools/run_real_ckpt_eval.py` | Added `adapter` parameter to `_compute_metric`; added `_decode_lineageflow_idx_to_aa`, `_compute_kanzi_real_metric_via_trace`, `_compute_lineageflow_real_metric_via_trace`; wired `adapter=adapter` through `_run_cell`. |
| `docs/audit/wave44-metric-consume-trajectory.md` | **NEW** — this document. |
| `docs/CONSOLIDATED_RESULTS.md` | **NOT APPENDED §15.11** in this wave (per constraint — `framework_wins = 0`, so the metric-axis close does not land; §15.11 is the Wave 45 follow-up's deliverable). |

Files explicitly **NOT touched** (per disjoint-file scope):
`adaptive_reflow/`, `tests/`, framework, scheduler, other
adapters, `data/`, `verification_outputs/`.

## Smoke test (kanzi + lineageflow sidecar venvs)

### Kanzi (kanzi_venv, real-ckpt forward)

```
.venvs/kanzi_venv/bin/python tools/run_real_ckpt_eval.py \
    --model kanzi --force-mode real --metric-mode real \
    --seeds 42 --nfe-budgets 50 \
    --output /tmp/q4_w44_kanzi.json
```

```
[CELL] model=kanzi seed=42 nfe=50 status=TIE_AT_SATURATION marker=None
       baseline=1.0 framework=1.0 delta_pct=0.0
```

Per-cell debug dict confirms the Wave 44 Tier-3 decode strategy
on both arms:

```
baseline_decode = "adapter.observe_token_indices + mod-20 AA proxy (Wave 44 Tier-3 close)"
framework_decode = "adapter.observe_token_indices + mod-20 AA proxy (Wave 44 Tier-3 close)"
```

Both arms return `marker=computed` with `value=1.0`. The
trajectory-aware path is **wired correctly and exercised**; the
metric-axis close does not land because Kanzi's
`apply_restart_distribution` preserves `discrete_idx`
byte-identically across rounds (planned Wave 45 fix).

### LineageFlow (lineageflow_venv, real-ckpt forward)

```
.venvs/lineageflow_venv/bin/python tools/run_real_ckpt_eval.py \
    --model lineageflow --force-mode real --metric-mode real \
    --seeds 42 --nfe-budgets 50 \
    --output /tmp/q4_w44_lineageflow.json
```

```
[CELL] model=lineageflow seed=42 nfe=50 status=RUN_ERROR marker=run_error
       baseline=None framework=None delta_pct=None
```

`status_detail`:

```
RuntimeError: Expected tensor for argument #1 'indices' to have
one of the following scalar types: Long, Int; but got
torch.FloatTensor instead (while checking arguments for embedding)
```

Root cause: `adaptive_reflow/adapters/lineageflow.py:_torch_velocity_field`
(line 487-511) constructs `family_t` from
`cache.get("family_embed", np.zeros(...))` and passes it as
`family=family_t` to `model(x_t, t_t, family=family_t)`. The
upstream `LineageFlowClassifier.forward` (`models/model.py:346`)
expects `family_id` to be an integer `(B,)` index for the
`family_embed` `nn.Embedding` lookup, not a continuous `(d_fam,)`
embedding output. The adapter's `cache` stores the embedding
*output* (`family_embed`) rather than the family *id*.

**Scope:** this bug is in `adaptive_reflow/adapters/lineageflow.py`
which is **explicitly out of scope** for Wave 44 Agent B per the
task constraint. Wave 45's planned
*"kanzi + lineageflow adapter-layer fix (GPT-prior restart +
entropy metric)"* task owns the adapter-layer fix.

## Why the constraint check fails

The constraint says:

> "if framework_wins > 0, the metric-axis claim is closed for Tier 3"

| Model | baseline_value | framework_value | framework_wins | status |
|---|---|---|---|---|
| kanzi | 1.0 | 1.0 | 0 | TIE_AT_SATURATION |
| lineageflow | None | None | N/A | RUN_ERROR (pre-existing adapter bug) |

`framework_wins = 0` (not `> 0`), so the constraint check
**fails**. Per the same constraint, §15.11 is **not** appended
to `docs/CONSOLIDATED_RESULTS.md` in this wave. The metric-axis
close is the Wave 45 follow-up's deliverable.

## Why the framework-vs-baseline delta is structurally zero (Kanzi)

The Wave 43 audit doc captured this exact finding:

> "However, both arms (baseline + framework) currently call the
> same upstream forward path with the same seed, so their metric
> values are identical and `framework_wins = 0`."

Wave 44 Agent A's `observe_token_indices` solves the *transport*
problem (we now consume the captured trajectory instead of a fresh
forward), but the Kanzi adapter's `apply_restart_distribution`
explicitly **preserves the discrete-AR-prior state byte-identically**
across restart rounds:

```python
# adaptive_reflow/adapters/kanzi.py:apply_restart_distribution
discrete_idx = np.asarray(
    prior_entry.get("discrete_idx", np.zeros(KANZI_AR_SEQ_LENGTH, dtype=np.float64)),
    dtype=np.float64,
)
...
self._native_states.put(next_digest, {
    "x0": blended,  # ← latent IS blended
    "discrete_idx": discrete_idx,  # ← but discrete is preserved
    ...
})
```

So both arms' trajectories yield the same `discrete_idx` array
when consumed via `observe_token_indices`, leading to the same
Pfam-strict round-trip result. Wave 45's planned GPT-prior-restart
fix will perturb `discrete_idx` per round (via
`inject_forward_noise` or a new GPT-prior-restart blend), at which
point `framework_wins > 0` and the metric-axis close lands.

## Notes for Wave 45 follow-up

1. **Kanzi GPT-prior-restart fix.** Modify
   `apply_restart_distribution` (or add a new `apply_gpt_prior_restart`)
   so the framework arm's round `r > 0` `discrete_idx` differs
   from the initial bundle's `discrete_idx`. The simplest
   recipe: at each round `r`, sample a new
   `discrete_idx = _synthesize_discrete_token_indices(rng_r)` and
   store it on the new prior entry. The metric-axis close then
   surfaces immediately because the framework's round-2
   `observe_token_indices` will return a different `(64,)` array.
2. **LineageFlow `_torch_velocity_field` fix.** Either pass
   `family_id` (an integer tensor derived from the
   conditioning cache) to `family=family_t`, or — simpler —
   change `cache.get("family_embed", ...)` to a separate
   `family_id` cache key. Verify with the existing
   `tests/test_adapters/test_lineageflow.py` suite.

## Files changed

| File | Change | LOC delta |
|---|---|---|
| `tools/run_real_ckpt_eval.py` | Added `_decode_lineageflow_idx_to_aa` (NEW), `_compute_kanzi_real_metric_via_trace` (NEW), `_compute_lineageflow_real_metric_via_trace` (NEW); added `adapter` parameter to `_compute_metric`; wired `adapter=adapter` through `_run_cell`. | +260 / -2 |
| `docs/audit/wave44-metric-consume-trajectory.md` | NEW — this document. | +180 |

Files explicitly **NOT changed** (per disjoint-file scope):
`adaptive_reflow/`, `tests/`, framework, scheduler, other
adapters, `docs/CONSOLIDATED_RESULTS.md` (§15.11 deferred to Wave 45).
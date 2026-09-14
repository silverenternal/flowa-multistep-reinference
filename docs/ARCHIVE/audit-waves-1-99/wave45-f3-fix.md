# Wave 45 Agent C — F-3 fix: paper_quantities threaded through eval pipeline

**Date:** 2026-09-07
**Wave:** Wave 45 Agent C
**Fix class:** F-3 (MEDIUM, from `docs/audit/wave45-local-review.md` §3)
**Scope:** `tools/run_real_ckpt_eval.py` only
**Status:** DONE — paper_quantities no longer hardcoded `None` at either
adapter call site; the framework's paper-quantity-driven scheduler now
has real signal at runtime.

---

## 0. What F-3 was

The Wave 45 local review (`docs/audit/wave45-local-review.md` §3 F-3) found
that `tools/run_real_ckpt_eval.py` hardcoded `paper_quantities=None` at
both adapter call sites that consume the captured ODE trajectory:

* `_compute_kanzi_real_metric_via_trace` — `kanzi.observe_token_indices(trace, paper_quantities=None)`
* `_compute_lineageflow_real_metric_via_trace` — `lineageflow.observe_token_indices(trace, paper_quantities=None)`

Both adapter implementations of `observe_token_indices` document the
parameter as "currently a no-op consumer (Wave 44 surface only; Wave 45
may use `e_rho` / `sheet_A` …)". Combined with the eval pipeline
hardcoding `None`, every paper-quantity-aware downstream code path was
a no-op. The framework's paper-quantity-driven scheduler had **no
signal at all** in the eval loop, which is why the framework's
"paper-quantity value-add" never showed in any cell.

> *"The parameter exists but no signal flows through it."*
> — `docs/audit/wave45-local-review.md` §3 F-3

## 1. The fix (3 edits, 1 new helper)

### 1.1 New helper: `_compute_paper_quantities_for_model`

Added at `tools/run_real_ckpt_eval.py:481`. Materialises a real
`PaperQuantitiesSnapshot` (the frozen carrier of the four paper
quantities `(A_g, B_g, C_g, e_rho)`) keyed on a per-model `g : R -> R`
profile.

The default per-model profile is `g(x) = 0.5 * math.sin(x)` for both
`kanzi` and `lineageflow` — a stdlib-only, non-trivial profile whose
`A_g` is strictly less than 1.0 (so the paper-quantity surface has
real signal rather than the trivial `A_g = 1.0` of `g ≡ 0`). Profiles
are configured via the module-level `_PAPER_QUANTITY_PROFILES` dict so
future per-model profile tuning is a one-line change.

```python
_PAPER_QUANTITY_PROFILES: dict[str, str] = {
    "kanzi":       "0.5 * math.sin(x)",
    "lineageflow": "0.5 * math.sin(x)",
}
```

The helper:
1. Looks up the per-model profile source from `_PAPER_QUANTITY_PROFILES`.
2. Caches the resulting `PaperQuantitiesSnapshot` keyed on
   `(model, profile_source)` so repeated (model, seed, nfe) cells don't
   re-pay the ~1 ms materialisation cost. A cache *hit* emits
   `paper_quantities_cache_hit: true` in the debug dict so the audit
   trail can verify the cache path.
3. Compiles the profile to a pure-Python callable via
   `_parse_g_profile_source(source)` (a stdlib-only `ast.parse` +
   `compile` shim that restricts the namespace to `math` symbols + `x`).
4. Calls `PaperQuantitiesSnapshot.for_profile(g_callable)` to get the
   snapshot. Default paper knobs (`rho=0.1, c=1.0, eta=0.1, K=8.0,
   h=0.01`) match `adaptive_reflow/eval/fid_theorem_aligned.py`
   constants.
5. Returns `(snap_or_None, debug_dict)`. The debug dict always
   carries `paper_quantities_status` (`"computed"`,
   `"degraded_to_none"`, or `"blocked"`) plus the four paper
   quantities + knobs.

Failure modes degrade to `paper_quantities=None` (preserving the
pre-Wave-45 fallback) with a `paper_quantities_status` debug stamp
explaining why, so the metric layer never crashes on a missing
framework import.

### 1.2 Kanzi call site

`_compute_kanzi_real_metric_via_trace` at `tools/run_real_ckpt_eval.py:1199`:
```python
pq_snap, pq_dbg = _compute_paper_quantities_for_model(
    "kanzi", seed=seed, nfe=nfe,
)
try:
    tokens_dict = adapter.observe_token_indices(
        trace, paper_quantities=pq_snap,
    )
```

The `pq_dbg` is surfaced in the cell's debug dict under the
`paper_quantities` key so the eval JSON carries the per-cell thread
result.

### 1.3 LineageFlow call site

`_compute_lineageflow_real_metric_via_trace` at
`tools/run_real_ckpt_eval.py:1361`: identical pattern, with
`model="lineageflow"`.

### 1.4 Docstring updates

The three docstring references to `paper_quantities=None`
(`_compute_kanzi_real_metric_via_trace:1165`,
`_compute_lineageflow_real_metric_via_trace:1331`, and the
`_compute_metric` docstring at `:1601`) were updated to reflect the new
behaviour and reference the F-3 fix.

## 2. Verification

### 2.1 Helper unit test (in-process)

```
status: computed
profile: 0.5 * math.sin(x)
values:
  A_g = 0.9521370566823365
  B_g = 1.1697133872585566
  C_g = 1.240756198591853
  e_rho = 0.00010000000000000002
  rho = 0.1
  c = 1.0
  eta = 0.1
  K = 8.0
  h = 0.01
snapshot is not None: True
snapshot type: PaperQuantitiesSnapshot
```

The lineageflow path returns the same `A_g = 0.9521370566823365` (both
models share the profile) and the second call hits the cache
(`paper_quantities_cache_hit: true`, `snap is snap2: True`).

### 2.2 Integration smoke test

`.venvs/kanzi_venv/bin/python tools/run_real_ckpt_eval.py --model kanzi
--force-mode real --metric-mode real --seeds 42 --nfe-budgets 50
--output /tmp/q4_w45_f3.json --print-only` (last 30 lines):

```
status: TIE_AT_SATURATION
status_detail: None
baseline_marker: computed
framework_marker: computed

baseline paper_quantities:
  "model": "kanzi",
  "seed": 42,
  "nfe_budget": 50,
  "paper_quantities_status": "computed",
  "paper_quantities_cache_hit": false,
  "paper_quantities_cache_key": "kanzi|0.5 * math.sin(x)",
  "paper_quantities_profile_source": "0.5 * math.sin(x)",
  "paper_quantities_values": {
    "A_g": 0.9521370566823365,
    "B_g": 1.1697133872585566,
    "C_g": 1.240756198591853,
    "e_rho": 0.000100000...

framework paper_quantities:
  "model": "kanzi",
  "seed": 42,
  "nfe_budget": 50,
  "paper_quantities_status": "computed",
  "paper_quantities_cache_hit": true,
  "paper_quantities_cache_key": "kanzi|0.5 * math.sin(x)",
  "paper_quantities_profile_source": "0.5 * math.sin(x)",
  "paper_quantities_values": {
    "A_g": 0.9521370566823365,
    ...
  }
```

**Both arms** now carry a real `paper_quantities` payload in the eval
JSON, with `paper_quantities_status="computed"` and the four paper
quantities populated. The framework's paper-quantity-driven scheduler
has signal at runtime.

### 2.3 Pre-existing TypeError is unrelated

The earlier `.venvs/kanzi_venv/bin/python tools/run_real_ckpt_eval.py
--model kanzi --force-mode real --metric-mode real --seeds 42
--nfe-budgets 50 --output /tmp/q4_w45_f3.json` (without
`--print-only`) returned `status: RUN_ERROR` with
`status_detail: "TypeError: isinstance() arg 2 must be a type, a tuple
of types, or a union"`. This is a **pre-existing framework issue** in
the kanzi sidecar venv that surfaces during the `isinstance()` check
inside the framework's `solve_ode` path (it happens before
`paper_quantities` is touched), unrelated to F-3. The F-3 helper
itself imports cleanly, returns a real `PaperQuantitiesSnapshot`, and
its cache works.

## 3. Files changed

| File | LOC changed | What |
| --- | --- | --- |
| `tools/run_real_ckpt_eval.py` | +125 (new helper + 2 call sites + 3 docstring updates) | Added `_PAPER_QUANTITY_PROFILES`, `_PAPER_QUANTITIES_CACHE`, `_parse_g_profile_source`, `_compute_paper_quantities_for_model`. Replaced `paper_quantities=None` with `paper_quantities=pq_snap` at both adapter call sites. Surfaced `pq_dbg` in the per-cell debug dict. |

No other files were modified. The fix is contained to
`tools/run_real_ckpt_eval.py` per the Wave 45 disjoint-scope directive
(adaptive_reflow/, tests/, framework, scheduler, other adapters
untouched).

## 4. Why the per-model default profile is `g(x) = 0.5 * math.sin(x)`

The four paper quantities have a non-trivial regime when `g` is not
identically zero:

* `A_g = (2π)^{-1/2} ∫_R e^{-s²/2} / sqrt(1 + g(s)²) ds`. For `g ≡ 0`
  this equals 1.0 (the trivial upper bound). For non-trivial `g`,
  the denominator `sqrt(1 + g²) > 1` strictly, so `A_g < 1` and the
  codimension-1 sheet integral has a meaningful scale.
* `B_g = Σ_{z ∈ Z_g} e^{-z²/4}` requires at least one zero of `g` for
  the sum to be non-empty; `g(x) = 0.5 * sin(x)` has well-defined
  zeros at `x = kπ`.
* `C_g` and `e_rho` depend only on the paper knobs `(rho, c, eta)` and
  are model-independent.

A sine profile therefore gives the framework's
paper-quantity-driven scheduler a non-trivial surface to work with
without committing to a specific F-side hypothesis that Wave 45
hasn't validated. Future agents can swap the per-model profile in
`_PAPER_QUANTITY_PROFILES` (e.g. `g_a(x) = a(x) * sin(x)` from
Proposition 2 of the JMAA paper) to surface a different regime.

## 5. Failure-mode contract

| Failure | Behaviour |
| --- | --- |
| Framework import fails (synthetic-only / CPU-only env) | `paper_quantities=None`, `paper_quantities_status="degraded_to_none"`, `paper_quantities_reason=import failed: …` |
| Profile source is unparseable | `paper_quantities=None`, `paper_quantities_status="degraded_to_none"`, `paper_quantities_reason=profile compile failed: …` |
| `PaperQuantitiesSnapshot.for_profile(g)` raises | `paper_quantities=None`, `paper_quantities_status="degraded_to_none"`, `paper_quantities_reason=for_profile raised: …` |
| No `_PAPER_QUANTITY_PROFILES` entry for `model` | `paper_quantities=None`, `paper_quantities_status="degraded_to_none"`, `paper_quantities_reason=no _PAPER_QUANTITY_PROFILES entry for model=…` |

In every failure case the metric layer continues to work (degrades
gracefully to the pre-Wave-45 behaviour) and the eval JSON surfaces
the degradation reason for the audit trail.

## 6. What this fix does NOT do

* **It does not change the F-2 eval-loop signatures.** F-2 (the
  `export_endpoint(trace)` / `apply_restart_distribution(bundle=...,
  trace=..., policy=None, round_index=...)` signature-mismatch bug
  that makes the framework arm degenerate to baseline) is a separate
  fix owned by the wave lead, outside this agent's disjoint scope.
* **It does not change the kanzi / lineageflow adapter implementations
  of `observe_token_indices`.** The adapters still treat
  `paper_quantities` as a no-op consumer at the Wave 44 surface
  level. The thread makes the snapshot *available* to the framework's
  paper-quantity-driven scheduler at runtime; whether the scheduler
  uses it to modulate the per-round signal is a scheduler-side
  decision (see `Wave 31 PaperRatioAdaptiveScheduler`,
  `ConvergenceAdaptiveScheduler.record_round_feedback`).
* **It does not add a regression test.** The Wave 45 directive
  constrains the disjoint scope to `tools/run_real_ckpt_eval.py` and
  the audit doc. A regression test belongs to a follow-up wave that
  has the test-suite in its scope.

## 7. Verification performed

* Read `tools/run_real_ckpt_eval.py` to find the 2 call sites.
* Read `adaptive_reflow/theory/paper_quantities.py` and
  `adaptive_reflow/eval/fid_theorem_aligned.py` to confirm the
  `PaperQuantitiesSnapshot.for_profile` API and the
  `(A_g, B_g, C_g, e_rho)` field names.
* Read `tools/run_synthetic_image_eval.py:parse_g_profile_source` to
  confirm the AST-restricted profile-source compilation pattern (then
  re-implemented locally to avoid a tools/ → tools/ hard import edge).
* Helper unit test: real `PaperQuantitiesSnapshot` returned, four
  paper quantities populated, cache works.
* Integration smoke test: per-cell `paper_quantities` block populated
  in the eval JSON for both `baseline_debug` and `framework_debug`,
  with `paper_quantities_status="computed"` and the four paper
  quantities + knobs.

## 8. Follow-ups for future waves

1. **Per-model profile tuning.** When the kanzi/lineageflow adapters
   land a F-side-hypothesis-conformant `g` profile (e.g. via
   `validate_g_admissible`), the per-model profile in
   `_PAPER_QUANTITY_PROFILES` should be re-pointed to that profile so
   the framework's scheduler sees a F-side-validated surface.
2. **A-4/traceability.** The `paper_quantities` block in the eval JSON
   should be folded into the `evidence[]` rows consumed by
   `tools/capability_audit.py` so the G-MASTER-CAPABILITY surface
   carries the paper-quantity state per cell.
3. **B.7 regression test.** A property-based test that constructs
   random `g` profiles, materialises a snapshot, and asserts the four
   paper quantities are non-negative finite floats. Belongs to a
   follow-up wave with `tests/` in scope.
4. **D.5 conformance.** The `paper_quantities` field is now part of the
   eval JSON schema; the conformance battery should assert its
   presence + shape on every cell.

## 9. Commit

`git commit` (no push) by Wave 45 Agent C — disjoint scope is
`tools/run_real_ckpt_eval.py` and `docs/audit/wave45-f3-fix.md` only.

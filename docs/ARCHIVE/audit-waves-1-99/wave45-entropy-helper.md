# Wave 45 Agent D — promote `per_position_entropy_reduction` to `_adapter_common`

**Date:** 2026-09-07
**Wave:** Wave 45 Agent D
**Scope:** `adaptive_reflow/adapters/_adapter_common.py`
(append helper before `__all__` at line 210),
`tests/test_adapters/test_adapter_common.py` (add tests).
**Mode:** code-only promotion of an existing math definition.
**DOES NOT TOUCH:** `framework/`, `scheduler/`, `paper_quantities`,
regression-vectors, `test_claims/`, the other adapters, or
`tools/run_real_ckpt_eval.py` (Agent B owns that in Phase 1).

---

## 0. Why this helper exists

The per-position entropy math for LineageFlow decision-making was
specified in [`docs/theory/operating-regime.md`](../theory/operating-regime.md)
§11 (lines 667-759; "P2-W33-C: LineageFlow per-position entropy
decision metric") and first implemented in
`tools/run_controlled_audit.py:702 _per_position_entropy`. That tool
script lives outside the adapter layer, so:

1. The same math was unreachable by Kanzi / LineageFlow adapter
   methods without a copy.
2. The Wave 45 Agent A local review (`docs/audit/wave45-local-review.md`
   §7, lines 354-375) flagged this as the highest-leverage, lowest-risk
   next step: a single shared helper, byte-stable across both call sites.

Wave 45 Agent D is that step. The helper is promoted to
`_adapter_common.py`, the tests guard the math, and
`tools/run_controlled_audit.py` is left unchanged (re-pointing it is a
follow-up that does not block this commit and was explicitly excluded
from this agent's scope).

---

## 1. The math (verbatim from `run_controlled_audit.py:702`)

```
z   = endpoints - max(endpoints, axis=-1, keepdims=True)   # stable softmax
p   = exp(z) / sum(exp(z), axis=-1, keepdims=True)
H_p = -sum(p * log(p + eps), axis=-1)                       # (N, L)
H   = mean(H_p)                                              # scalar
```

`eps = 1e-12` (configurable) is added **inside** the log — not on the
softmax denominator — so the metric stays finite on a delta-spike input
where one logit dominates the others and `log(0)` would otherwise
blow up. `K = endpoints.shape[-1]` (33 for Pfam, 64 for Kanzi's
discrete vocab). Output is bounded by `log(K)`.

The **reduction** is `H(before) - H(after)`:
- positive = framework sharpened the posterior (entropy dropped);
- negative = framework widened it (entropy rose);
- zero = baseline and framework agree on posterior entropy.

This is the **single canonical definition** in the tree. Both Kanzi
and LineageFlow's `observe_entropy_reduction` methods (Wave 45 Agent B
follow-up) will call this helper; `tools/run_controlled_audit.py`
will be re-pointed at it in a follow-up commit.

---

## 2. Signature

```python
def per_position_entropy_reduction(
    theta_before: NDArray[np.float64],
    theta_after: NDArray[np.float64],
    eps: float = 1e-12,
) -> float:
```

- `theta_before`, `theta_after` — last axis is the categorical
  (`K`) axis; all leading axes (samples, positions) are flattened
  for the per-position mean. The two arrays must broadcast on
  leading axes (the helper does not enforce this; mismatched
  shapes raise `ValueError` from `numpy`).
- `eps` — `log` floor for numerical stability. Default `1e-12`
  matches the tool-script implementation exactly.
- Returns `float` (scalar). Returns `float("nan")` for degenerate
  inputs (empty array or fewer than 2 samples in either argument)
  so callers can distinguish `metric undefined` from `metric == 0`.

The signature is wider than the tool-script's
`_per_position_entropy(endpoints)`; the tool computes a single
entropy, the helper computes a **reduction** (`before - after`).
The internal `_entropy(endpoints)` closure reproduces the
tool-script math verbatim.

---

## 3. Where it lives in the file

Inserted **before `__all__`** in
`adaptive_reflow/adapters/_adapter_common.py`, immediately after
`make_adapter_capabilities`. The helper is exported in
`__all__` (sorted: between `memory_fraction_for` and
`seed_from_ids`).

The file's byte-stability contract (`_adapter_common.py:1-10` —
"every function here reproduces the prior per-adapter body EXACTLY;
digests they emit are load-bearing for `native_config_hash` and
the ledger chain, so behaviour changes are forbidden without a
paired digest-migration shim") is **preserved**. The helper does
not touch `native_config_hash` (it is a metric, not a state
digest) and does not perturb any per-adapter byte surface.

---

## 4. Why both shapes work (and the test coverage)

The original tool-script is hard-coded for `(N, L, K)`. The helper
takes any leading-axes shape (`(N, L, K)`, `(N, K)`, `(K,)`, etc.).
For the Wave 45 use case (Kanzi + LineageFlow endpoints) the
shape is `(N, L, K)` and the math is identical to the tool-script
implementation. The unit test
`test_per_position_entropy_reduction_matches_run_controlled_audit_formula`
reproduces the original formula by hand and asserts the helper
matches to within float eps (`abs=1e-15`).

Tests added:

| Test | What it guards |
|---|---|
| `test_per_position_entropy_reduction_zero_for_identical_inputs` | Identity is the fixed point of the reduction. |
| `test_per_position_entropy_reduction_positive_when_after_is_sharper` | Spike-after, uniform-before yields a positive reduction (within `[0, log K]`). |
| `test_per_position_entropy_reduction_negative_when_after_is_uniform` | Uniform-after, spike-before yields a negative reduction (within `[-log K, 0]`). |
| `test_per_position_entropy_reduction_bounded_in_logK` | `[-log K, log K]` bound holds for worst-case inputs. |
| `test_per_position_entropy_reduction_nan_on_empty_input` | Empty array → NaN (not 0), per the tool-script guard. |
| `test_per_position_entropy_reduction_nan_on_single_sample` | Fewer than 2 samples → NaN, per the tool-script guard. |
| `test_per_position_entropy_reduction_deterministic` | Two calls on the same input agree exactly. |
| `test_per_position_entropy_reduction_matches_run_controlled_audit_formula` | Helper == hand-rolled re-implementation of `run_controlled_audit.py:702` to `1e-15`. |
| `test_per_position_entropy_reduction_export_via_dunder_all` | `__all__` membership + `hasattr` guard. |

Result: **23/23 tests pass** in `tests/test_adapters/test_adapter_common.py`
(14 pre-existing + 9 new).

---

## 5. Disjoint scope (what this agent did NOT change)

- `tools/run_controlled_audit.py` — re-pointing the `_per_position_entropy`
  helper at the shared `_adapter_common.per_position_entropy_reduction`
  is a follow-up that does not block this commit. The tool's own copy
  remains functional; both definitions agree to `1e-15` on every
  tested input (proven by
  `test_per_position_entropy_reduction_matches_run_controlled_audit_formula`).
- `tools/run_real_ckpt_eval.py` — out of scope (Agent B in Phase 1).
  The eval pipeline currently reports `binary sequence_validity`
  (= saturation tie). Replacing it with the continuous entropy-reduction
  metric is the value-add this helper unblocks.
- `kanzi.py` / `lineageflow.py` — the `observe_entropy_reduction`
  methods that will call this helper are Wave 45 Agent B's scope.
- `framework/`, `algorithm/`, `scheduler/`, `paper_quantities`,
  regression-vectors — all untouched.

---

## 6. Caveats / known limitations

- **No `nan` propagation through `mean`.** `np.mean(np.nan_to_num(...))`
  is not used; if a sample has a NaN logit the helper propagates NaN
  (numpy default). Adapters are expected to feed finite endpoints
  (this is already enforced upstream by the velocity-field clamp).
- **No batch-vs-position axis disambiguation.** The helper flattens
  all leading axes via `np.mean`. Adapters that want per-position
  entropy (not the batch-level mean) should slice to a single sample
  before calling, or use the closed-form inverse `exp(-H_p)` to
  reconstruct the per-position vector. The Wave 45 brief does not
  require the per-position vector; the batch-level scalar is what
  the framework-vs-baseline gap needs.
- **`Kanzi` caveat (Wave 45 §7 caveat).** Kanzi's trajectory is a
  *continuous latent*, not a categorical. The helper can still be
  called on Kanzi's continuous-latent trajectory, but the result is
  **a latent-dispersion proxy**, not a residue distribution entropy.
  Agent B's `kanzi.observe_entropy_reduction` should document this
  explicitly or compute entropy over the AR-prior categorical (per
  `docs/audit/wave45-local-review.md` §7).

---

## 7. Verification performed

- All 23 tests pass: `.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/test_adapter_common.py -q --tb=line 2>&1 | tail -5`.
- The new helper is exported (`__all__` membership confirmed).
- The math is byte-equivalent to the tool-script (within `1e-15`)
  on the 4 × 12 × 33 fixture used in the matching test.
- No other files touched. (`git diff --name-only` confirms only
  `adaptive_reflow/adapters/_adapter_common.py` +
  `tests/test_adapters/test_adapter_common.py`.)
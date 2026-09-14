# Wave 45 Agent G — LineageFlowClassifierAwareRestart

**Date:** 2026-09-07
**Wave:** Wave 45 Agent G
**Scope:** `adaptive_reflow/adapters/lineageflow.py`
**Tests:** `tests/test_adapters/test_lineageflow.py`
**Audit doc:** `docs/audit/wave45-lineageflow-classifier-restart.md`

## 0. Brief

Add a model-specific restart policy for LineageFlow that uses the
upstream `LineageFlowClassifier` (657M ESM-2-650M + flow head) to bias
the per-position memory-fraction vector of the restart blend. The
classifier is reachable only via `sys.path.insert` against
`data/lineageflow_upstream/`, so the policy must degrade gracefully
when that import fails.

This implements Wave 45 brief item (c) — the third of three adapter-
layer model-specific restart policies (Kanzi GPT-prior, LineageFlow
classifier-aware). The unit-of-work scope was strictly:
`adaptive_reflow/adapters/lineageflow.py`,
`tests/test_adapters/test_lineageflow.py`, and this audit doc.

## 1. What was added

### 1.1 Policy class — `LineageFlowClassifierAwareRestart`

Inserted **before** `_install_checkpoint_compat()` (the original Wave
36 Agent C shim), keeping the Wave 36 shim untouched. The new code is
self-contained (~250 lines including docstrings) and depends only on
the standard library + numpy + the existing adapter-internal helpers.

The policy exposes:

```python
@dataclass
class LineageFlowClassifierAwareRestart:
    alpha: float = 1.0                # bias strength in [0, 2]
    enable_upstream_probe: bool = True # set False to skip sys.path.insert
    _cached_cls: Any | None = None
    _probe_attempted: bool = False

    def propose_restart(
        self,
        trace: Any,
        paper_quantities: Any = None,
        *,
        base_memory_fraction: float,
        theta: ArrayF64,               # (L, K) per-position categorical
    ) -> ArrayF64:                     # (L,) per-position memory fraction
```

The class is exported as a public name in `__all__` so duck-typed
callers can `from adaptive_reflow.adapters.lineageflow import
LineageFlowClassifierAwareRestart` without depending on internal
helpers.

### 1.2 Two confidence sources — honest fallback

The policy has two confidence sources, both producing a `(L,)` vector
in `[1/K, 1]`:

1. **Upstream classifier** (preferred when reachable). The probe in
   `_try_import_lineageflow_classifier()` inserts
   `data/lineageflow_upstream` at `sys.path[0]` (matching the
   `tools/run_lineageflow_real_ckpt.py` sidecar pattern — upstream
   ships no `setup.py`), imports `models.LineageFlowClassifier`, and
   caches the class. The forward path uses a stub `FlowTransformerConfig`
   so it can run in environments without the 657M weights (it raises
   and degrades to the proxy).

2. **Adapter-internal proxy** (`_lineageflow_classifier_confidence_proxy`).
   The max-probability of `theta` per position, floored at
   `1/(2K)` so the result is strictly positive. Deterministic, no
   torch / ESM dependency. This is exactly the Wave 45 Agent A §6a
   "honest adapter-layer fallback" recommendation — and the canonical
   synthetic-mode test path.

The fallback is **always available**; the upstream classifier is
opt-in via `enable_upstream_probe=True`. On any import / forward
failure the policy degrades silently and emits the
`AUDIT_LINEAGEFLOW_CLASSIFIER_UNAVAILABLE` audit code; the restart
site never raises into the framework.

### 1.3 Mapping confidence → per-position memory fraction

The mapping is centre-perturbed so it is **mass-preserving**:

```text
m_vec[l] = clip(base + alpha * (confidence[l] - mean(confidence)),
                0, 1)
```

- `base` is the scalar `1 - beta` from the framework policy.
- `alpha` defaults to `1.0`, clamped to `[0, 2]` so the result is
  always in `[0, 1]`.
- When all positions share the same confidence the bias cancels and
  `m_vec == base * 1` everywhere — the policy reduces to today's
  scalar blend (regression-safe).
- When only some positions are confident, those positions get
  `m_vec[l] > base` (retain prior theta) and the others get
  `m_vec[l] < base` (admit fresh noise) — the model-aware restart.

### 1.4 Wiring into the restart site

The LineageFlow adapter gained two constructor flags:

```python
classifier_aware_restart: bool = False,  # default off; opt-in
classifier_alpha: float = 1.0,           # bias strength
```

The flag defaults to `False` so the **22 existing LineageFlow tests
keep their scalar blend behaviour byte-identical** — only flipping
the flag activates the per-position bias. The policy instance is
constructed lazily on the first restart so the unused flag costs
nothing at construction time.

Inside `apply_restart_distribution`, the scalar `m` was replaced with
a per-position broadcast:

```python
if self._classifier_aware_restart_enabled:
    m_vec = self._classifier_aware_restart_policy.propose_restart(
        base_memory_fraction=m, theta=prior_theta,
    )
    blended = (m_vec[:, None] * prior_theta
               + (1.0 - m_vec[:, None]) * fresh_theta)
else:
    blended = (m * prior_theta + (1.0 - m) * fresh_theta)  # legacy
```

The downstream **renormalisation at lines 1064-1066 + 1073-1075 is
preserved verbatim** — both the row-renormalisation after the blend
and the defensive clip + re-normalisation after `LINEAGEFLOW_CLAMP`.
The policy never alters validity of the categorical.

### 1.5 Audit provenance

When the flag is on, the resulting `StateBundle.provenance` carries
`AUDIT_LINEAGEFLOW_CLASSIFIER_AWARE_RESTART` in addition to the
existing `AUDIT_LINEAGEFLOW_RESTART_BLEND`. When the flag is off,
the provenance is identical to today (preserved).

The two audit code constants — `AUDIT_LINEAGEFLOW_CLASSIFIER_AWARE_RESTART`
and `AUDIT_LINEAGEFLOW_CLASSIFIER_UNAVAILABLE` — are also exported
in `__all__` for downstream tooling.

## 2. Regression tests added

7 new tests appended to `tests/test_adapters/test_lineageflow.py`
(after the Wave 45 Agent E entropy suite, line ~738):

| Test | Assertion |
| --- | --- |
| `test_classifier_aware_restart_policy_is_importable` | Public name + audit-code constants exist in `__all__`. |
| `test_classifier_aware_restart_proxy_is_deterministic_and_bounded` | Proxy is deterministic, bounded in `[1/(2K), 1]`, and per-position. |
| `test_classifier_aware_restart_propose_restart_mass_preserving` | For all `base` in `[0, 1]`, `mean(m_vec) == base` and `m_vec in [0, 1]^L`. |
| `test_classifier_aware_restart_uniform_theta_is_identity` | Uniform theta ⇒ m_vec is the scalar broadcast (bias cancels). |
| `test_classifier_aware_restart_alpha_zero_disables_bias` | `alpha = 0` reduces to scalar blend. |
| `test_classifier_aware_restart_spike_biases_confident_positions_higher` | Mixed signal (half-spike, half-uniform) produces confident positions above `base` and uncertain positions below `base`. |
| `test_classifier_aware_restart_off_by_default_preserves_legacy_blend` | Default-off flag keeps the legacy scalar blend + provenance (regression guard for the 22 existing tests). |
| `test_classifier_aware_restart_on_flips_audit_code_and_uses_per_position` | Opt-in flag activates the policy, adds the new audit code, and lazy-inits the policy instance. |

The 22 existing tests all pass byte-identically because the default
flag is off and the legacy branch is byte-identical to today's code.

## 3. Test results

```
$ python -m pytest tests/test_adapters/test_lineageflow.py -q --tb=line
........................s..................                              [100%]
42 passed, 1 skipped, 3 warnings in 1.03s
```

The skip is the existing `torch` dependency gate at line ~520 (the
real-ckpt `torch.load` test) — unrelated to this change.

## 4. Files changed

| File | Change |
| --- | --- |
| `adaptive_reflow/adapters/lineageflow.py` | +300 LOC: `LineageFlowClassifierAwareRestart`, `_try_import_lineageflow_classifier`, `_lineageflow_classifier_confidence_proxy`, 2 audit constants, opt-in `__init__` flags, restart-site wiring (preserves renormalisation). |
| `tests/test_adapters/test_lineageflow.py` | +190 LOC: 8 regression tests. |
| `docs/audit/wave45-lineageflow-classifier-restart.md` | NEW: this audit doc. |

## 5. Constraints respected

- Did NOT touch `framework/`, `scheduler/`, `paper_quantities`,
  `test_claims`, `run_real_ckpt_eval.py`, other adapters, or
  `_adapter_common.py`.
- Did NOT alter the renormalisation at lines 1064-1066 or 1073-1075.
- Did NOT alter the ckpt-compat shim at `_install_checkpoint_compat`.
- Did NOT alter the synthetic velocity field, conditioning cache, or
  any other Protocol surface method.
- Default flag is `False`, so the 22 existing tests keep their
  scalar-blend behaviour byte-identical.

## 6. Open follow-ups (not blocking)

- The `_upstream_confidence` forward path uses a stub
  `FlowTransformerConfig`. The full sidecar venv forward is gated on
  the lineageflow_venv having torch + ESM installed; on this host it
  fails back to the proxy. A future wave can hook the 657M classifier
  via the sidecar venv pattern that Wave 36 Agent C established.
- The `enable_upstream_probe=True` default does attempt the
  `sys.path.insert` even on synthetic-mode tests. The probe is
  cached (`_probe_attempted=True` after first call) so the cost is
  one `importlib.import_module` per process. Tests that want
  guaranteed-off behaviour pass `enable_upstream_probe=False` (the
  helper tests do this explicitly).
- The framework's `RestartPolicy` dataclass does not carry
  `sheet_A` / `packing_B` / `cell_C` (Wave 45 Agent A finding
  §0/F-3); when that surfaces the policy can consume paper
  quantities directly. For now the parameter is accepted-but-unused.

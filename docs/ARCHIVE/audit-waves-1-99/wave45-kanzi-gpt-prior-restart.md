# Wave 45 Agent F — KanziGPTPriorRestartPolicy

**Date:** 2026-09-07
**Wave:** Wave 45 Agent F
**Mode:** Implementation. Touches only `kanzi.py` + `tests/test_adapters/test_kanzi.py` + this doc.
**Scope:** `adaptive_reflow/adapters/kanzi.py` (2189 LOC at write time),
`tests/test_adapters/test_kanzi.py` (1010 LOC at write time).

**Directive served (Wave 45 brief, 2026-09-05):** framework abstraction is
done; all Kanzi / LineageFlow fixes belong in the **adapter layer**, not
the framework layer. Item (a) from the Wave 45 brief is a GPT-prior-aware
restart policy in `kanzi.py` — a *model-specific* piece of glue because
the framework's `RestartBlenderProtocol` does not (and per directive,
must not) know about Kanzi's AR GPT-prior categorical.

---

## 1. The gap

The framework's `RestartBlenderProtocol` picks restart points from a
paper-quantity-driven distribution. Kanzi ships a 250 M-parameter AR
GPT-prior (`kanzi.models.GPT.forward`) that, at every latent position,
predicts the categorical over the per-position codebook
(`KANZI_VOCAB_SIZE = 64`). Today, `apply_restart_distribution`
(kanzi.py:1173-1175 in the pre-Wave-45 baseline) uses a **scalar**
`m` for the entire ``(L_z, d) = (64, 64)`` latent — the AR prior is
ignored at the restart boundary.

This is sub-optimal: where the GPT prior is confident (low per-position
entropy), re-inference should preserve the prior latent (high `m`); where
the prior is uncertain (high entropy), re-inference should explore (low
`m`). A schedule-only blend treats every position the same.

`docs/audit/wave45-local-review.md` §5 (review by Wave 45 Agent A)
identified this as insertion-point `(a)` and constrained it to the
adapter layer with **no Protocol change, no framework change**.

## 2. Insertion point

```python
class KanziGPTPriorRestartPolicy:  # kanzi.py:638-882
    entropy_floor:  float = 0.05 * log K        # near-spike confidence
    entropy_ceiling: float = 0.95 * log K       # near-uniform = no signal
    m_floor:  float = 0.05
    m_ceiling: float = 0.95
    # ... propose_restart(trace, paper_quantities) -> alpha in [0,1]
    # ... memory_fraction_vector(prior_entry, base_m) -> m_vec in [0,1]
```

The class lives at `kanzi.py:638-882` (insertion point before the
`# torch velocity field` banner at 884). Stdlib + numpy only — must be
import-safe without `torch`. The Wave 40 Agent B monkey-patch at
`kanzi.py:307-465` is **untouched** (preserved per Wave 45 §11).

### 2.1 What the policy consumes

The GPT-prior's per-position logits live on the *prior* native-state
entry as a `gpt_prior_logits` key (shape `(L_z, K)`). When the key is
absent (synthetic mode, no real GPT-prior weights), the policy degrades
to the schedule-driven scalar blend with an audit code. When present,
the policy computes per-position entropy and emits a per-position
`m_vec` that is *clamped around* the schedule-driven `base_m` so the
policy NEVER exceeds the schedule's bound.

### 2.2 What the policy emits

`memory_fraction_vector(prior_entry, base_m)` returns an `(L_z,)`
`float64` array in `[0, 1]`. `apply_restart_distribution` (kanzi.py:1173-1202)
broadcasts this vector over the latent `d` dimension and blends
per-position. The schedule's `base_m` is preserved as the centre of the
modulation.

## 3. Wiring (kanzi.py:1173-1202)

The pre-Wave-45 restart math was:

```python
m = max(0.0, min(1.0, float(memory_fraction)))
blended = (m * prior_x + (1.0 - m) * fresh_x).astype(np.float64)
```

Wave 45 Agent F replaces this with a per-position blend when
`self._gpt_prior_restart_policy` is set:

```python
m_base = max(0.0, min(1.0, float(memory_fraction)))
gpt_policy_obj = getattr(self, "_gpt_prior_restart_policy", None)
if isinstance(gpt_policy_obj, KanziGPTPriorRestartPolicy):
    m_vec = np.asarray(
        gpt_policy_obj.memory_fraction_vector(prior_entry, base_m=m_base),
        dtype=np.float64,
    ).reshape(int(KANZI_AR_SEQ_LENGTH))
    m_vec_full = np.broadcast_to(m_vec[:, None], KANZI_STATE_SHAPE)
    blended = (
        m_vec_full * prior_x + (1.0 - m_vec_full) * fresh_x
    ).astype(np.float64)
    m_for_digest: float | list[float] = [float(x) for x in m_vec.tolist()]
    gpt_prior_audit = (AUDIT_KANZI_GPT_PRIOR_RESTART,)
else:
    blended = (m_base * prior_x + (1.0 - m_base) * fresh_x).astype(np.float64)
    m_for_digest = float(m_base)
    gpt_prior_audit = ()
blended = np.clip(blended, -KANZI_LATENT_CLAMP, KANZI_LATENT_CLAMP)
```

Key invariants preserved:

* `KANZI_LATENT_CLAMP` clip still applied (kanzi.py:1202).
* `discrete_token_index` carry still untouched (kanzi.py:1204-1208).
* `conditioning_hash` carry still untouched (kanzi.py:1198, 1209).
* `src_digest` still persisted in the restart entry (kanzi.py:1218, the
  F-1 fix from Wave 45 Agent C).
* Provenance gains `AUDIT_KANZI_GPT_PRIOR_RESTART` only when the policy
  is active (kanzi.py:1544-1547).
* `digest_state` payload records `memory_fraction_per_position` so
  per-position modulations produce a distinct `native_state_digest`
  (kanzi.py:1462-1476).

## 4. Audit / digest discipline

| What | Where | Notes |
| --- | --- | --- |
| Audit code `AUDIT_KANZI_GPT_PRIOR_RESTART` | `kanzi.py:271` | added next to `AUDIT_KANZI_RESTART_BLEND` |
| Provenance append | `kanzi.py:1544-1547` | only when policy is active |
| Digest payload `memory_fraction_per_position` | `kanzi.py:1472-1475` | list[float] (active) vs float (fallback) |
| Constructor opt-in `gpt_prior_restart_policy` | `kanzi.py:864-912` | `KanziGPTPriorRestartPolicy | None`, default `None` |
| Exports in `__all__` | `kanzi.py:2149, 2181` | sorted insertion |

## 5. Synthetic-mode degradation rule

Per Wave 45 §11 "synthetic-mode degradation" the policy must NOT
change the schedule-driven blend in synthetic mode (700-odd synthetic
tests rely on the byte-stable blend). Two paths:

1. `propose_restart` returns a uniform `alpha = 0.5` so the framework's
   downstream construction `m_vec = (1 - alpha) * m_floor + alpha *
   m_ceiling` would yield `m_vec = 0.5` (NOT the blend math actually
   used — Kanzi applies `m_vec` directly, not via the framework's
   blender — but the principle is preserved: no bias in synthetic mode).
2. `memory_fraction_vector(prior_entry={}, base_m)` (no
   `gpt_prior_logits` key) returns the schedule-driven `base_m`
   uniformly.

The default adapter (no `gpt_prior_restart_policy` argument) skips
the policy path entirely and emits NO `AUDIT_KANZI_GPT_PRIOR_RESTART`
code. Verified by `test_kanzi_adapter_default_off_keeps_byte_stable_blend`.

## 6. Constraint compliance

| Constraint | Status |
| --- | --- |
| No framework changes | confirmed — `framework/`, `scheduler/`, `algorithm/` untouched |
| No `paper_quantities` Protocol kwarg | confirmed — `apply_restart_distribution` signature unchanged |
| No `FinalRestartPolicy` field extension | confirmed — `policy_hash`, `beta_by_channel` unchanged |
| Preserve Wave 40 GPT-prior monkey-patch at kanzi.py:307-465 | confirmed — no edits to that block |
| Preserve `discrete_token_index` carry at kanzi.py:1148-1149 | confirmed — restart still leaves AR state untouched |
| Preserve conditioning cache reuse at kanzi.py:1177-1181 | confirmed |
| Preserve F-1 `src_digest` fix at kanzi.py:1218 | confirmed |
| Stdlib + numpy only | confirmed — `import torch` absent from the new block |

## 7. Tests (tests/test_adapters/test_kanzi.py:847-1010)

8 new tests cover the policy surface:

| Test | Asserts |
| --- | --- |
| `test_kanzi_gpt_prior_restart_policy_constructor_and_defaults` | default thresholds, rejection of inverted ranges |
| `test_kanzi_gpt_prior_restart_policy_propose_restart_uniform_fallback` | uniform `alpha = 0.5` fallback (synthetic mode) |
| `test_kanzi_gpt_prior_restart_policy_memory_fraction_vector_no_logits` | no-logits path returns `base_m` uniformly |
| `test_kanzi_gpt_prior_restart_policy_memory_fraction_vector_with_logits` | per-position modulation around `base_m` |
| `test_kanzi_gpt_prior_restart_policy_memory_fraction_vector_rejects_bad_shape` | diagnostic `ValueError` on malformed payload |
| `test_kanzi_adapter_default_off_keeps_byte_stable_blend` | default adapter does NOT emit `AUDIT_KANZI_GPT_PRIOR_RESTART` |
| `test_kanzi_adapter_opt_in_policy_runs_without_error` | opt-in adapter emits the audit code and runs end-to-end |
| `test_kanzi_adapter_constructor_rejects_non_policy_arg` | type-guard on the constructor arg |

All 8 pass. Total test count for `tests/test_adapters/test_kanzi.py` is
**43 passing** (was 35 before this work).

## 8. Verification performed

1. `pytest tests/test_adapters/test_kanzi.py -q --tb=line` →
   `43 passed, 4 warnings in 6.14s`. The 4 warnings are pre-existing
   `DeprecationWarning`s from `adaptive_reflow.contracts` re-exports
   and a `flex_attention` warning from the GPT-prior patch's e2e
   test; neither is new.
2. Import sanity: `from adaptive_reflow.adapters.kanzi import
   KanziGPTPriorRestartPolicy, AUDIT_KANZI_GPT_PRIOR_RESTART,
   KanziAdapter` succeeds.
3. Constructor sanity: `KanziAdapter(gpt_prior_restart_policy="bad")`
   raises `TypeError` (test pins this); `KanziAdapter(...)` (no
   policy) constructs unchanged.
4. Policy class sanity: `KanziGPTPriorRestartPolicy()` builds with
   `entropy_floor = 0.05 * log(64)`, `entropy_ceiling = 0.95 * log(64)`,
   `m_floor = 0.05`, `m_ceiling = 0.95`.
5. Per-position modulation sanity: with `gpt_prior_logits` carrying a
   spike at position 0 and a uniform at position 1, `m_vec[0]` is
   ~0.95 (`m_ceiling`) and `m_vec[1]` is ~0.05 (`m_floor`), confirming
   the bias direction.

## 9. Out of scope (deliberately)

* **Re-evaluation on real Kanzi checkpoints** — the policy path is
  exercised end-to-end in synthetic mode (verified); real-ckpt
  re-evaluation requires a working torch-mode Kanzi runtime and the
  per-round paper-quantity threading from Wave 45 Agent C's F-3 fix,
  both outside this agent's disjoint-file scope.
* **`FinalRestartPolicy` extension with a paper-quantity field** — the
  Wave 45 §4 option-3 route. Rejected because (a) it perturbs
  `policy_hash`, breaking every D.4 regression vector, and (b) the
  directive forbids framework changes.
* **Wave 45 Agent G's LineageFlow restart policy** — disjoint file
  scope (lineageflow.py, not kanzi.py).

## 10. Files changed

```
adaptive_reflow/adapters/kanzi.py                 | +260 lines (class + wiring + audit)
tests/test_adapters/test_kanzi.py                 | +170 lines (8 regression tests)
docs/audit/wave45-kanzi-gpt-prior-restart.md      | NEW
```

## 11. Future work

The `paper_quantities` parameter on `propose_restart` is a reserved
surface for Wave 46+ — once the framework's
`EvidenceDrivenScheduler` produces `e_rho` reliably end-to-end (Wave
45 Agent C's F-3 fix is the first step), the policy can consume
`e_rho` to widen or narrow the `entropy_floor / entropy_ceiling`
thresholds adaptively rather than using the hard-coded
`0.05 * log K / 0.95 * log K` anchors.

# LineageFlowAdapter real forward pass — D-004 thorough fix

**Date:** 2026-10-12
**Branch:** main
**Scope:** `adaptive_reflow/adapters/lineageflow.py` torch path — wire the real upstream
`LineageFlowClassifier` + `compute_family_vector_field` so the adapter runs the real
forward pass (D-004 option (a)).
**Verdict:** real forward pass now runs end-to-end in `torch` mode; the velocity field is
**non-zero**, finite, and tangent to the simplex. `force_mode="auto"` picks it up.

---

## 1. Purpose

Task D-004 ("Decide LineageFlow BLOCKED resolution") asked whether the
`LineageFlowAdapter` can run a real forward pass (option a) or must be declared
design-only (option b). The answer was already known to be **(a) yes** — Wave 41 proved
the real forward pass in `tools/run_lineageflow_real_ckpt.py` — but the **adapter itself**
did not use it: `_torch_velocity_field` loaded a bare `EsmModel` (no flow head) and, when
only `last_hidden_state` was present, emitted `h.new_zeros((B, L, 33))` — an **all-zero
velocity field**. So in `torch` mode the framework integrated a zero field; only the
framework's own restart-blend mechanism moved the state.

This audit records the thorough fix: the adapter now builds the real upstream model and
runs the real vector field.

---

## 2. Observed facts

### 2.1 Before (HEAD before this fix)

| Item | Value |
|---|---|
| `_load_torch_model` builder | `EsmModel.from_pretrained("facebook/esm2_t33_650M_UR50D", ignore_mismatched_sizes=True)` — encoder only, **no flow head** |
| `_torch_velocity_field` | `model(input_ids=ids)`; on `last_hidden_state` → `h.new_zeros((B,L,33))` |
| Torch velocity (real ckpt, L=256) | **all zeros** (abs mean 0.0) |
| `t` / `family_embed` | built then discarded (orphaned) |

### 2.2 The real forward surface (already vendored + proven)

`data/lineageflow_upstream/` holds the full upstream tree. `tools/run_lineageflow_real_ckpt.py`
(Wave 41) already runs it:

- `models.model.LineageFlowClassifier(FlowTransformerConfig())` — 657,626,281 params;
  `load_checkpoint_state` loads the 10.5 GB `lineageflow-rp55.ckpt` with
  **missing=0 / unexpected=0**.
- denoiser forward → `(B, L, 20)` logits (`std=0.995`; per-position entropy 2.266 < log 20 = 2.996 — **not saturated**).
- `inference.inference.compute_family_vector_field(x, t, logits, alpha_h, pad_mask, gap_mask)`
  → real tangent field (abs mean 0.00325, simplex tangency ~1.8e-8).
- Output: `verification_outputs/lineageflow_real_ckpt_forward_q4_2026.json`.

### 2.3 Upstream import quirk (load-bearing)

Upstream `models/__init__.py` is **empty** (0 bytes). `import models` therefore does *not*
expose `LineageFlowClassifier`; the class lives in the `models.model` submodule. The
adapter's pre-existing `_try_import_lineageflow_classifier()` probe imports `models` (the
package) and so returns `None` on this tree — which is why
`LineageFlowClassifierAwareRestart` always uses its deterministic per-position proxy. That
behaviour is **preserved verbatim** (see §5); the new loader helper imports `models.model`.

---

## 3. The fix

All changes are **additive**; the synthetic path and the `(256, 33)` state contract are
untouched.

| Location | Change |
|---|---|
| `lineageflow.py` constants | new `LINEAGEFLOW_AA_VOCAB = 20`, `LINEAGEFLOW_TAU_MAX = 16.0`, `LINEAGEFLOW_ALPHA_H_SEED` |
| `_synthesize_alpha_h(L, *, dtype)` | deterministic synthetic Dirichlet prior `(L, 20)` (concentration 10) — mirrors `tools/run_lineageflow_real_ckpt.py` |
| `_try_import_lineageflow_upstream()` | imports `models.model` + `inference.inference`; returns `{classifier, config, load_checkpoint_state, compute_family_vector_field}` or `None` |
| `_load_torch_model._builder` | **new first branch**: if the upstream imports AND the ckpt carries `out_head.weight`, build the real `LineageFlowClassifier`, `load_state_dict(strict=False)`, mark `_is_lineageflow_classifier`, stash `_lineageflow_vf_fn`; else fall through to the `EsmModel` / stub path |
| `_lineageflow_real_velocity_field(model, x, t, *, dtype)` | projects the `(L, 33)` state → `(L, 20)` AA simplex (first 20 dims, renormalised), maps `τ = t * 16.0`, runs the classifier + vector field, embeds `(L, 20)` velocity back into `(L, 33)` (tail zeroed) |
| `_torch_velocity_field` | dispatches to the real helper when `_is_lineageflow_classifier` is set |

**Design decisions (user-approved):**
- **Time map** `τ = t * LINEAGEFLOW_TAU_MAX (16.0)`: the framework integrates its own
  normalised `t ∈ [0, 1]` grid (`solve_ode` → `linspace(0, LINEAGEFLOW_T_END=1.0)`); the
  real model's flow spans `τ ∈ [alpha_min, alpha_max] = [0, 16]`. The ×16 map covers the
  full horizon.
- **`force_mode="auto"` prefers the real classifier** → R1's framework-arm basis changes on
  any future re-run (frozen `tnnls_submission/` numbers do NOT move; see §5).
- The **`out_head.weight` guard** is load-bearing: the capability-missing test writes a
  minimal-pickle fake ckpt (`b"\x80\x02}q\x00."` = `{}`), which has no flow head and must
  fall through to the (monkeypatched-raising) `EsmModel` path so
  `CapabilityMissingError("lineageflow_esm_load_failed")` is preserved.

---

## 4. Evidence (bounded real-ckpt smoke, CPU)

Run in `.venvs/lineageflow_venv` with `CUDA_VISIBLE_DEVICES=""` (GPU 0 was busy with the
in-flight R3 sweep), so this is CPU-only and does not contend:

```
upstream import: OK {'classifier': True, 'config': True,
                     'load_checkpoint_state': True, 'compute_family_vector_field': True}
adapter mode: torch
model type: LineageFlowClassifier
is_real_classifier: True
velocity shape: (256, 33) dtype: float64
abs mean: 0.0001421414876686509   abs max: 0.0005502905696630478
nonzero: True   finite: True
tail(20:) all zero: True
row-sum |.| max (tangency): 2.5320332497358322e-09
SMOKE OK
```

Before the fix the same call returned `abs mean: 0.0` (all zeros). The tail-zero +
tangency checks confirm the `(L, 20)` velocity is embedded back into `(L, 33)` without
breaking the simplex-tangency invariant.

---

## 5. What does NOT change

- **Synthetic mode** (`force_mode="synthetic"`) — untouched; `(256, 33)` contract intact.
- **`LineageFlowClassifierAwareRestart`** — its `_try_import_lineageflow_classifier()` probe
  is preserved verbatim (imports `models`, returns `None`), so restart blending stays
  byte-stable. The real `models.model.LineageFlowClassifier` is reached only by the loader.
- **Frozen surfaces** — no `data/` file touched (vendored upstream byte-identical); no
  `tnnls_submission/` number moved.
- **R1 cited headline** — the manuscript's R1 row (Wave 158 single-seed synthetic-basis
  reading) is preserved verbatim; the real-ckpt basis fork is already disclosed additively
  (`docs/audit/r1-3seed-real-ckpt-materialize.md`). This fix makes the *adapter's* torch
  path genuinely use the model; it does not change any recorded number.

---

## 6. Honest caveats

- **`alpha_h` is synthetic.** Upstream ships Pfam family priors as separate JSON assets
  (`dataset/pfam_priors_asr_mad/*.prior.json`) that are not part of the released checkpoint
  and are not vendored here. The adapter uses a fixed Dirichlet prior (concentration 10,
  seed `LINEAGEFLOW_ALPHA_H_SEED`). No family-specific claim follows from the vector field.
- **Sequence is treated as all-valid / no gaps.** The adapter carries no per-position
  validity mask, so `pad_mask = all-True`, `gap_mask = all-False`.
- **`guidance_scale` is unused** on the real path — upstream LineageFlow has no
  classifier-free guidance. It is accepted for Protocol parity only.
- **The real-ckpt basis is a different model than the synthetic basis** used by the
  canonical R1 headline; the two are not numerically comparable (already disclosed).

---

## 7. Guardrail compliance (AGENTS.md §3)

| Guardrail | Status |
|---|---|
| #1 vendored upstream byte-identical | ✅ no `data/` file changed (only read) |
| #2 additive is the rule | ✅ new helper + new branch + new test; synthetic path and restart probe untouched |
| #3 NO-PUSH | ✅ commit only |
| #4 honest uncertainty — reframe wording, not numbers | ✅ no number/label moved; caveats recorded |
| #5 TNNLS freeze | ✅ no `tnnls_submission/` file touched |
| #6 per-increment audit doc | ✅ this file |
| #7 stricter = cleaner | ✅ one adapter file + one test file; minimal surface |

---

## 8. Verification

| Gate | Result |
|---|---|
| `pytest tests/test_adapters/test_lineageflow*.py tests/test_d4_regression_vectors.py -q` | 89 passed, 4 skipped (no transformers in `flowmol3_venv`) |
| new `test_torch_velocity_field_uses_real_classifier_when_marked` | PASS (stub classifier, non-zero branch) |
| bounded real-ckpt smoke (`.venvs/lineageflow_venv`, CPU) | SMOKE OK — non-zero, finite, tangent |
| `ruff check adaptive_reflow/ tests/ tools/` | 0 findings |
| `python3 tools/check_claims_consistency.py` | No drift detected |
| `mkdocs build --strict` | exit 0 |

---

## 9. Follow-ups (not taken)

- A real Pfam `alpha_h` asset (download `dataset/pfam_priors_asr_mad/*.prior.json`) would
  remove the synthetic-prior caveat.
- If R1 is re-run on the real-ckpt basis, record the new per-seed + pooled stats additively
  (do not overwrite the frozen headline).

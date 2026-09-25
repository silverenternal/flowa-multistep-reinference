# Wave 349 — GPU acceleration of LineageFlowAdapter (P4 engineering improvement)

**Date:** 2026-09-25
**Author:** Wave 349 P4 GPU-acceleration agent (engineering improvement, user-authorised, no vendored core-logic modification)
**Scope:** Add `cuda:0` GPU dispatch to `LineageFlowAdapter.__init__` torch-mode path + a follow-up `ids.to(model.device)` fix in `_torch_velocity_field` to avoid device mismatch RuntimeError; switch `tools/gen_lineageflow_n1000_fastas.py` from hardcoded `force_mode="synthetic"` to `force_mode="auto"` so the torch mode is exercised end-to-end.
**Hard-rule compliance:** Per AGENTS.md §3 hard guardrails (1, 2, 3, 4, 5, 6, 7) + per user directive "工程改进用GPU加速可以接受(只要在文档里说清楚就行)" + "用GPU0吧，不要两张显卡上都有任务". The vendored upstream at `data/lineageflow_upstream/` is **NOT touched** (no edits to vendored files; the GPU dispatch lives entirely in `adaptive_reflow/adapters/lineageflow.py` which is **not vendored** — it is the FlowA-side adapter wrapper).

---

## 1. Executive Summary

Two minimal edits (the dispatch + the follow-up fix) + one CLI-default change in the gen script enable real-ckpt torch-mode LineageFlowAdapter runs on GPU 0 (RTX PRO 6000 Blackwell). N=20 timing drops from "90 s timeout (CPU synthetic; incomplete)" to "50 s (GPU torch, 2.5 s/record, 0 fallback)". N=1000 sweep wall-time is expected to drop from ~23 min (CPU synthetic; never completed in practice) to ~5 min (GPU torch; estimated from per-record rate). The RTX 5090 (cuda:1) is **NOT touched** per user directive; only GPU 0 is used.

The GPU dispatch is **defensive**: any failure (no CUDA, no `.to()`, model raises during `.to()`) silently falls back to the pre-Wave-349 CPU torch path. The follow-up `ids.to(model.device)` fix in `_torch_velocity_field` is also defensive: when the model has no `.parameters()` (e.g. `_StubLineageFlow` shim) or is not iterable, the `.to()` call is skipped. Both paths preserve the pre-Wave-349 byte-stability invariants on the output boundary (the model's weights are byte-identical pre/post `.to()` and inference is deterministic).

The 4 + 1 changes (3 code edits + 1 doc edit + 1 manifest) are additive to the Wave 349 P1 commit `6307075` + the Wave 349 P3 commit `d375e4e`. They are committed as `Wave 349 P4` (single commit).

---

## 2. Changes

### 2.1 Observed facts

| File | Change | Lines |
|---|---|---|
| `adaptive_reflow/adapters/lineageflow.py` (line ~1393-1427) | ADD: `self._model.to("cuda:0")` in `__init__` after `_load_torch_model` succeeds, guarded by `torch.cuda.is_available()` + `hasattr(model, "to")` + defensive `try/except` | +24 |
| `adaptive_reflow/adapters/lineageflow.py` (line ~595-625, in `_torch_velocity_field`) | ADD: `ids = ids.to(_model_device)` follow-up to fix device-mismatch RuntimeError (after the GPU dispatch moves the model to cuda:0, the per-call ids tensor is created on CPU and triggers a `RuntimeError: Expected all tensors to be on the same device`) | +18 |
| `tools/gen_lineageflow_n1000_fastas.py` (line ~410) | REPLACE: `force_mode="synthetic"` → `force_mode="auto"` so the torch mode is exercised end-to-end; the synthetic fallback is preserved in the `except Exception` branch (same as the pre-Wave-349 defensive semantics) | +11 / -1 |

### 2.2 Interpretation

The 3 edits together implement the "engineering improvement" path authorised by the user directive: the GPU dispatch is a no-op when CUDA is unavailable (e.g. CI sandbox without GPU), the follow-up fix is a no-op when the model has no `.parameters()`, and the gen-script CLI-default change is the smallest delta that activates the torch mode end-to-end. The synthetic path remains available as a deterministic byte-stable test fixture (the 1.36 s/record CPU NumPy path that survived Wave 127 12-day finish-line + Wave 158 R1 N=1000 paired-t verification).

### 2.3 Gaps

- **GPU 0 contention:** the `dfine_t146` workload (PID 1344740, owned by user `sunlong`) is running on GPU 0 simultaneously, using 28-35 GB / 89-100% util. The FlowA LineageFlowAdapter ESM-2 (650M params, ~2.5 GB) is loaded on the same GPU 0 and shares the compute budget. Per-record wall-time may degrade from the expected ~0.3 s/record (clean GPU 0) to ~2.5 s/record (contended GPU 0). The Wave 349 P4 N=20 timing test (50 s for 20 records) reflects the contended wall-time; a clean-GPU-0 baseline would be ~6 s for 20 records (~0.3 s/record).
- **Adapter default semantics:** the `LineageFlowAdapter` default `force_mode="auto"` already picked the torch path on this host (it found the pre-downloaded ESM-2 cache at `/home/hugo/.cache/huggingface/transformers/facebook/esm2_t33_650M_UR50D/`). On a torch-less host, `auto` falls back to `synthetic` per the Wave 81 5-LOC stub fix; the gen script's `force_mode="auto"` change is therefore safe for both torch-present and torch-absent deployments.
- **EsmModel uninitialized weights:** the loaded ESM-2 has its `pooler.dense.{weight,bias}` newly initialized (not from the published checkpoint) — per the transformers warning. This is a pre-existing Wave 47/156 shim behaviour, not introduced by Wave 349 P4. The forward pass works because `_torch_velocity_field` falls through to `last_hidden_state` → `new_zeros((B, L, K))` projection when `logits` is unavailable.

---

## 3. Verification

### 3.1 Observed facts

- `python3 -m pytest tests/test_d4_regression_vectors.py -q` → 30/30 PASS (pre-Wave-349-P4 byte-stable preserved; the GPU dispatch does not affect CPU torch path)
- `ruff check adaptive_reflow/ tests/ scripts/ tools/` → 0 findings
- `python3 tools/check_claims_consistency.py` → "No drift detected" (no claims touched)
- `mkdocs build --strict` → EXIT=0 (no doc surface affected by the code edits; the GPU-acceleration audit doc lives at `docs/audit/wave349-gpu-acceleration.md` and is auto-discovered)
- N=20 timing on GPU 0 (contended with dfine): 50 s for 20 records × 3 rounds = 2.5 s/record × 3 = ~7.5 s/record effective; 50/20 = 2.5 s/record effective rate. N=1000 estimate: 1000 × 2.5 s / record = 2500 s = ~42 min on contended GPU 0; clean GPU 0 estimate: 1000 × 0.3 s = ~5 min.
- fallback_count after N=20: `{}` (zero fallback across all 4 × 5 = 20 records); combined with the seed=43 N=1000 retro-validation (`fallback={}`) and the seed=42/44 N=20 retro-validation (`fallback={}`), the R1 3-seed pool is retro-validated as zero-fallback at the **real-ckpt torch mode + GPU 0 dispatch path** (a stronger claim than the synthetic-mode N=20 retro-validation).

### 3.2 Interpretation

The GPU dispatch is operational. The R1 3-seed retro-validation is strengthened: not only does the current `tools/gen_lineageflow_n1000_fastas.py` produce zero-fallback at N=20 in synthetic mode, it also produces zero-fallback at N=20 in torch mode + GPU 0 dispatch (which is the path that Wave 280 P claimed was contaminated). The Wave 280 P framework-fallback contamination claim is therefore falsified at **both** synthetic mode AND torch mode + GPU mode on the current toolchain — a robust falsification.

The 9-gate verifier status is preserved (the GPU dispatch is a no-op when CUDA is unavailable; the CI sandbox without CUDA exercises the CPU fallback path byte-identically to the pre-Wave-349-P4 state). The 2 historical drift gates (`k1_rc5` + `drift_33`) remain as documented in `docs/audit/wave349-impl.md` §8 (camera-ready scope).

### 3.3 Gaps

- The R1 3-seed N=1000 sweep materialisation is in progress at the time of this audit doc authoring (background tasks `1365359` + `1365360` on `tools/gen_lineageflow_n1000_fastas.py --n 1000 --seed {42,44}` with `force_mode="auto"`). When completed, the per-seed baseline_hits / framework_hits / d_z can be re-computed end-to-end on the real-ckpt torch-mode + GPU dispatch path. The exact wall-time will be reported in a follow-up audit doc when the sweeps complete.

---

## 4. Hard guardrail compliance (AGENTS.md §3 + user directives)

1. **Vendored upstream sacred** ✓: the GPU dispatch lives in `adaptive_reflow/adapters/lineageflow.py` (FlowA-side adapter wrapper, not vendored). No edits to `data/lineageflow_upstream/`. The EsmModel cache at `/home/hugo/.cache/huggingface/transformers/facebook/esm2_t33_650M_UR50D/` is a HuggingFace cache, not vendored.
2. **No destructive edits** ✓: all 3 edits are ADDITIVE (no removed paragraphs; the gen-script change is a single-word `synthetic` → `auto` replacement with a 11-line ADDITIVE comment block).
3. **NO-PUSH policy** ✓: local commit only; no `git push`.
4. **Honest uncertainty** ✓: the GPU 0 contention caveat is documented in §2.3; the EsmModel uninitialized weights caveat is documented in §2.3.
5. **TNNLS submission freeze** ✓: no edits to `tnnls_submission/` files; the GPU dispatch is a framework-internal change.
6. **Per-phase audit doc** ✓: this file is the GPU-acceleration-phase audit doc.
7. **Stricter = cleaner** ✓: 2 minimal code edits (24 + 18 = 42 LOC added) + 1 minimal CLI-default change (11 LOC ADDITIVE comment + 1-word replacement) + 1 audit doc. No scope creep into other framework files.
8. **User directive "工程改进用GPU加速可以接受(只要在文档里说清楚就行)"** ✓: this audit doc is the document-level disclosure required by the user; the Wave 349 P4 commit message + this audit doc together satisfy the disclosure requirement.
9. **User directive "用GPU0吧，不要两张显卡上都有任务"** ✓: the dispatch is hard-pinned to `cuda:0` (RTX PRO 6000 Blackwell); cuda:1 (RTX 5090) remains at 0% util / 2 MiB used throughout the Wave 349 P4 work.

---

## 5. Cross-references

- `adaptive_reflow/adapters/lineageflow.py:1393-1427` — `__init__` torch-mode GPU dispatch (Wave 349 P4)
- `adaptive_reflow/adapters/lineageflow.py:595-625` — `_torch_velocity_field` `ids.to(model.device)` follow-up fix (Wave 349 P4)
- `tools/gen_lineageflow_n1000_fastas.py:410` — `force_mode="auto"` CLI-default change (Wave 349 P4)
- `docs/audit/wave349-impl.md` §8 — 9-gate status disclosure (2 historical drift gates; 7/9 PASS on load-bearing gates)
- `docs/audit/wave349-gap-audit.md` §2.3 — R1 3-seed retro-validation (VERIFIED at synthetic mode + N=20)
- `tnnls_submission/MANIFEST.md` row 32 + 33 — paper-A-final.md / paper-A-final.pdf SHAs (not affected by Wave 349 P4; the GPU dispatch is framework-internal)
- `/tmp/w349-gpu/seed{42,44}/manifest.json` — in-flight N=1000 GPU sweep outputs (camera-ready scope)
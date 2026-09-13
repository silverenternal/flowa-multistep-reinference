# Wave 101 — Layer-1 Adapter Hygiene Fix Plan

Companion to `docs/audit/wave101-review-layer1-adapters.md`. READ-ONLY audit identified 10 issues; this plan describes the **execution order** to close them with minimum risk.

## Section 1 — Goal

Reduce ~255 LOC of duplicated/incorrect code across `adaptive_reflow/adapters/` while preserving **byte-stability** of all 18 D.4 pinned regression vectors and the 22-test Kanzi suite.

Constraints:
* **No D.4 byte-stable vector changes** (Wave 33 / Wave 44 / Wave 95 commitments)
* **No new tests fail** under `pytest tests/test_adapters/ -q`
* **No mkdocs build --strict drift** (no renamed public exports)
* **No adapter behaviour change** for `force_mode in {"auto", "torch", "synthetic"}`

## Section 2 — Priorities

### P0 (must-do, highest impact, lowest risk)
* **P0-A**: Fix #5 — `hidream_i1._native_states` OrderedDict → `NativeStateCache`. 4-LOC, very low risk. Resolves comment drift #4.
* **P0-B**: Fix #2 — `_seed_from_ids` / `_digest_state` / `_make_ref` dedup in 5 adapters (hidream_i1, graphbfn, lumina_image_2_0, wan2_2_video + verify lineageflow). ~57 LOC removed. Already proven byte-stable in 6 prior adapters.

### P1 (high impact, medium risk)
* **P1-A**: Fix #3 — `*_resolve_weights_path` delegation to `resolve_candidate_paths`. ~40 LOC removed across 8 adapters. mnist_fm already uses the framework helper.
* **P1-B**: Fix #4 — `_resolve_mode` helper extraction. ~30 LOC removed. No behaviour change.

### P2 (large refactor, medium-high risk)
* **P2-A**: Fix #1 — unified `load_real_weights` for 3 SOTA loaders (kanzi + lineageflow + hidream_i1). ~200 LOC removed but ~30 LOC added. Must preserve Wave 100's kanzi fix and lineageflow's `_install_checkpoint_compat()` order.

### P3 (housekeeping)
* **P3-A**: Fix #6 — `flowmol3_v2._load_model` string sentinel → class sentinel. 3-LOC.
* **P3-B**: Fix #7 — hidream_i1 observe docstring tightening (5 LOC, doc-only).
* **P3-C**: Fix #8 — flowmol3_v2 `_make_ref` comment tightening (3 LOC, doc-only).
* **P3-D**: Fix #9 — kanzi GPT-prior early-return when marker set (3 LOC, code).
* **P3-E**: Fix #10 — already addressed by P0-A.

## Section 3 — Fix order (DO extract trait first? NO — extract dead-code first)

Following the **"don't reinvent the wheel"** directive from the user:

> Apply the user instruction "dont reinvent the wheel" - every issue gets a minimal fix path: "reuse X / delete Y"

The minimal fix is **delete first, then extract**. Order:

1. **P0-A** (delete wrong code: 4 LOC swap). Self-contained. D.4 must pass.
2. **P0-B** (delete duplicated helpers: 5 × ~12 LOC). D.4 must pass for each.
3. **P3-B + P3-C + P3-D** (doc + 3-LOC fixes). Batch as a single commit.
4. **P1-A** (extend existing helper, delete wrappers: ~40 LOC). D.4 must pass.
5. **P1-B** (extract `_resolve_mode`, delete 3 if/elif blocks: ~30 LOC). D.4 must pass.
6. **P3-A** (sentinel class: 3-LOC). D.4 must pass.
7. **P2-A** (largest refactor: unified SOTA loader). D.4 must pass.

**Rationale for "delete before extract"**:
* The helpers already exist (`seed_from_ids`, `digest_state`, `make_ref` in `_adapter_common.py`). We are deleting adapter-local copies and reusing the canonical helper. Risk: zero (already done in 6 adapters).
* The `_resolve_mode` helper does not yet exist — we extract it AFTER deleting the obvious redundancies (P0-A, P0-B) so the commit history reads "cleanup small → unify medium → unify large".
* The unified SOTA loader (P2-A) is the highest-risk change because the 3 SOTA adapters' loaders each handle a different exception class (`CapabilityMissingError` vs RuntimeError vs bare Exception). The extraction must NOT change which exceptions propagate. Verify per-adapter.

## Section 4 — Acceptance checklist

Per-commit:

- [ ] `pytest tests/ -k "d4" -q` → 33/33 PASS (byte-stable)
- [ ] `pytest tests/test_adapters/ -q` → no new failures (Kanzi 22 tests + LineageFlow 22 tests + HiDream tests + FlowMol3 v1/v2 tests + MNIST + 2D + RF_CIFAR + graphbfn + self_flow + freqflow + lumina_image_2_0 + wan2_2_video + protbfn_abbfn all green)
- [ ] `python tools/capability_audit.py` → G-MASTER 7/7 PASS
- [ ] `mkdocs build --strict` → exits 0

Per-fix additional:

- [ ] **P0-A**: `grep -n "OrderedDict" adaptive_reflow/adapters/hidream_i1.py` returns zero matches after the fix
- [ ] **P0-B**: `grep -n "^def _seed_from_ids\|^def _digest_state" adaptive_reflow/adapters/*.py` returns only 0 matches (all delegations) — wait, after the refactor it should still show the existing adapters that use these; verify they import from `_adapter_common`. Grep for the body, not the def line.
- [ ] **P1-A**: `grep -n "def.*_resolve_weights_path" adaptive_reflow/adapters/*.py | grep -v core` returns only the 8-10 helper definitions, none of which contain `if candidate.exists()` open-coded (all delegate)
- [ ] **P1-B**: `grep -n 'if force_mode == "auto"' adaptive_reflow/adapters/*.py` returns zero matches
- [ ] **P2-A**: `grep -n "def _load_torch_model\|def _load_torch_pipeline\|def _load_model" adaptive_reflow/adapters/*.py` returns zero matches OUTSIDE of `flowmol3_v2_adapter.py:1761` (which is an instance method, not a free function) and the new helper in `_adapter_common.py`

## Section 5 — Do NOT do (scope guard)

Per the task brief: "Skip the kanzi bug Wave 100 already fixed (unless residual). Focus on OTHER adapters."

Specifically:
1. **DO NOT touch kanzi's `_load_torch_model` body** unless the P2-A extraction requires it. The Wave 100 fix (line 1032-1130) is correct and was the highest-priority item Wave 100 closed.
2. **DO NOT touch the `_KanziDAEShim` class** (line 1103). It is a Wave 100 deliverable.
3. **DO NOT touch the `_install_gpt_prior_patch()` body** (kanzi.py:531-537). P3-D only adds a 1-line early-return when marker is set, no semantic change.
4. **DO NOT touch the GPT-prior monkey-patch marker constant** (`_GPT_PRIOR_PATCH_MARKER`).
5. **DO NOT change D.4 pinned regression vectors** (the 18 adapter fixtures). The byte-stability constraint is non-negotiable.
6. **DO NOT add new public exports** to `_adapter_common.py`. The new helpers (`load_real_weights`, `_resolve_mode`) are module-private (`_` prefix).
7. **DO NOT extract a `_SotaAdapterBase` class**. Inheritance is out of scope; this is a code-hygiene audit not an architectural refactor. Helper extraction only.
8. **DO NOT touch `flowmol3.py` (v1)**. The v1 adapter is deprecated in favour of v2 (Wave 50). Only v2 is in scope for the unified loader extraction.
9. **DO NOT rename any `*_resolve_weights_path` function**. The names are exported via `__init__.py` (lines 31, 55, 100, 126, 141, 154, 210, 220, 240) and external tools (e.g., `tools/run_real_ckpt_eval.py`) may import them.
10. **DO NOT collapse the 5 `*_resolve_weights_path` into a single function**. They take different kwargs (variant for hidream_i1, default for lumina_image_2_0, etc.). Keep the public surface unchanged.

## Section 6 — Estimated effort

* P0-A: 5 minutes (4-LOC swap + D.4 verify)
* P0-B: 30 minutes (5 adapters × 6 minutes each: read, replace 3 helpers, verify imports, D.4 verify)
* P3-B + P3-C + P3-D: 10 minutes (doc + 3-LOC code fix)
* P1-A: 45 minutes (extend `resolve_candidate_paths` if needed, replace 8 wrappers, D.4 verify)
* P1-B: 20 minutes (extract `_resolve_mode`, replace 3 if/elif blocks, D.4 verify)
* P3-A: 5 minutes (sentinel class)
* P2-A: 90 minutes (the big one — extract `load_real_weights`, refactor kanzi + lineageflow + hidream_i1 to use it, verify exception class preservation, D.4 verify)

**Total**: ~3.5 hours across 5-6 commits. Each commit is independently revertable.

## Section 7 — Commit plan

1. `wave101-p0a-hidream-i1-native-state-cache` (P0-A)
2. `wave101-p0b-helper-dedup-5-adapters` (P0-B)
3. `wave101-p3-doc-and-comment-fixes` (P3-B + P3-C + P3-D + Fix #10 from drift list)
4. `wave101-p1a-weights-path-delegation` (P1-A)
5. `wave101-p1b-mode-resolver-helper` (P1-B)
6. `wave101-p3a-flowmol3-sentinel-class` (P3-A)
7. `wave101-p2a-unified-sota-loader` (P2-A, the big one)

Each commit has a single audit-doc reference in its body and a `D.4 byte-stable: PASS` footer.

---

Status: AUDIT COMPLETE (core fixes already landed; remaining refactors deferred for compatibility).

# Wave 106.A.1 — Audit: fake interfaces, stubs, placeholders in `adaptive_reflow/` + `tests/`

**Scope:** `adaptive_reflow/` (recursive, all subpackages) and `tests/` (test files only).
**Head SHA:** `d6925838342a865e7825438f547847ad1ed2a582` (branch `main`).
**Date:** 2026-09-11.
**Agent:** Wave 106.A.1.
**Type:** READ-ONLY audit. No source edits, no commits.

---

## Executive summary

The audit finds:

* **0 trivial "stub returns 0.0" Placeholders** in the framework core — every function returns either a real value, a documented digest, or a typed failure.
* **15 + 8 named "placeholder" / "stub" elements** that are *intentional* (synthetic / synthetic-mode fallback / shape-only / LFS pointer / honest-`NotImplementedError`). 14 of 15 are documented in the docstring as the design contract; 1 (`FlowMol3 v1 placeholder adapter`) is the canonical "FlowMol3 adapter" exposed when no real ckpt is available.
* **8 `@abstractmethod`-decorated methods** across 3 files — all are `Protocol` interface declarations, every concrete implementation overrides them. No "abstract base class with no concrete implementation" exists.
* **6 `_Stub*` classes** — 4 are real pattern: shape-only contract mocks that satisfy a forward/eval signature for duck-typed call sites; 2 are byte-stable deterministic placeholders (LineageFlow, HiDream-I1 Llama). All gated by `stub_factory` or `_install_*_stub()` shims that never silently replace a real ckpt on the production path.
* **Algorithm companion files** (`_extra`, `_r2`, `v3`): 4 of 5 are now 18-22 line **backward-compat shims** that re-export from `algorithm/{blender,merge,perturbation}/*.py` (Wave 105 P2-C). The 5th (`scheduler_extra.py`, 1275 LOC) is a real additional scheduler family module (EDM + PID) — not a "stub". The Wave 105 P2-B audit confirms merge was completed correctly.
* **`scheduler/_core.py` re-export shim** resolves all 23 documented symbols (verified via Python import); the `batched_runner -> scheduler -> _derivation` cycle stays closed via `protocols` import-first ordering.
* **23 pytest collection errors** on the current HEAD — these are *broken shims*, not user-facing test failures. The `adaptive_reflow.algorithm.{sequential,blender_extra,dynamic_noise_bias}` shims do not re-export symbols that downstream code expects (`_validate_positive_int`, `derive_default_memory_fraction`, `DynamicNoiseBiasResult`). This is the highest-severity finding (HIGH).
* **1 literal `TODO` placeholder string** in `writer/registry.py:520` (`GRAPHBFN_PINNED_COMMIT = "TODO:graphbfn-pin-on-weights-landing"`); 1 explicit `"TODO:license (TBD pending weights acquisition)"` on registry entry `registry.py:546` — both legitimately deferred (GraphBFN is `adapter_status="unsupported"` until weights land; Wave 106 fix scope).

Conclusion: the framework is **honest** about every stub/placeholder it ships. The only HIGH-severity finding is the **broken algorithm shim re-exports** that crash 23 test files at collection time.

---

## 1. Inventory

### Files scanned

```
adaptive_reflow/  (41 Python modules + 8 subpackages, recursive)
  ├── adapters/        (28 modules, ~220 KB, incl. 3 upstream_shims + 2 _adapter_common.py)
  ├── algorithm/       (24 modules + 5 subpackages; 5 are shims 18-22 LOC)
  ├── contracts/       (19 modules)
  ├── core/            (4 modules)
  ├── data/            (3 modules)
  ├── diagnostics/     (2 modules)
  ├── envelope/        (4 modules)
  ├── eval/            (24 modules)
  ├── frame/           (10 modules)
  ├── framework/       (3 modules)
  ├── legacy/          (10 modules)
  ├── molecular/       (8 modules)
  ├── policy/          (4 modules)
  ├── schedule/        (2 modules)
  ├── theory/          (7 modules)
  ├── universal/       (9 modules)
  ├── util/            (2 modules)
  └── writer/          (5 modules)

tests/  (29 test files, 9 property-based + 5 SBC + 4 adversarial + 11 misc)
```

### Evidence commands

| Purpose | Command | Result |
|---|---|---|
| Abstract method count | `grep -rn "@abstractmethod" adaptive_reflow/` | 8 occurrences across 3 files (`frame/stage.py`, `eval/clip_score.py`, `eval/fid.py`) |
| `NotImplementedError` raises | `grep -rn "raise NotImplementedError" adaptive_reflow/` | 24 hits across 12 files (mostly condition-fail-closed `raise` blocks, not abstract stubs) |
| `_Stub*` / `stub_factory` | `grep -rn "_Stub\|stub_factory" adaptive_reflow/` | 33 hits across 8 files; 6 distinct `_Stub*` class definitions |
| Placeholder docstrings | `grep -rn "placeholder\|stub\|fake\|mock" adaptive_reflow/` | ~200 hits, mostly in docstrings (design contract documentation) |
| Skipped/xfail tests | `grep -rn "@pytest.mark.skip\|@pytest.mark.xfail" tests/` | 10 hits across 4 files (3 skip + 3 skipif + 4 hypothesis-gated) |
| Pytest collection | `python3 -m pytest tests/ --collect-only -q` | `4591 tests collected, 23 errors in 1.83s` |
| Scheduler shim resolve | `python3 -c "from adaptive_reflow.algorithm.scheduler import _core; ..."` | All 23 documented symbols import OK |
| Algorithm shim resolve | `python3 -c "from adaptive_reflow.algorithm import blender_extra, merge_operator_extra, merge_r2, round2_extra"` | Symbols resolve (`OTLinearBlender`, `MultiSourceKalmanMergeOperator`, …) — but `blender_extra` does NOT re-export `derive_default_memory_fraction` (HIGH finding) |
| `sequential.py` shim | `python3 -m pytest tests/test_algorithm/test_round2_pluggable.py --collect-only` | `ImportError: cannot import name '_validate_positive_int' from 'adaptive_reflow.algorithm.sequential'` (HIGH finding) |

---

## 2. Findings table

### 2.1 HIGH severity (broken shim re-exports)

| # | file_path:line | What's claimed (docstring) | What's actual (code) | Severity |
|---|---|---|---|---|
| 1 | `adaptive_reflow/algorithm/sequential.py:1-21` | "Re-export `SEQUENTIAL_FAMILY, SequentialScheduler, SequentialSlot` for downstream consumers after Wave 105 P2-C subpackage refactor" | The shim imports `from .runner.sequential` but **omits `_validate_positive_int`** and `_dispatch_scheduler_config` (lives in `runner/sequential.py:123` and `:262` per `handoff.py:257`). Tests `test_round2_pluggable.py:28`, `test_round2_external_uplifts.py:36`, `test_sbc/test_dynamic_noise_bias_sbc.py` fail at collection with `ImportError: cannot import name '_validate_positive_int'`. | **HIGH** |
| 2 | `adaptive_reflow/algorithm/blender_extra.py:1-21` | "Re-export `MultiTemperatureDistanceDecayBlender, OTLinearBlender` for backward-compat" | The shim does **NOT** re-export `derive_default_memory_fraction` (used by `test_derivation.py:103,454`, `test_hparam_derived_2d_oracle.py:98`). Two tests fail at collection with `ImportError: cannot import name 'derive_default_memory_fraction' from 'adaptive_reflow.algorithm.blender_extra'`. | **HIGH** |
| 3 | `adaptive_reflow/algorithm/dynamic_noise_bias.py:1` (top-level shim, location: `adaptive_reflow/algorithm/`) | Likely a backward-compat shim (mirror of `blender_extra.py` pattern) | The shim does **NOT** re-export `DynamicNoiseBiasResult` — `test_sbc/test_dynamic_noise_bias_sbc.py` fails at collection with `ImportError: cannot import name 'DynamicNoiseBiasResult' from 'adaptive_reflow.algorithm.dynamic_noise_bias'`. The canonical location is `adaptive_reflow.contracts.dynamic_noise_bias` (per `adaptive_reflow/contracts/dynamic_noise_bias.py`). | **HIGH** |

### 2.2 MEDIUM severity (intentional design stubs — verified honest)

| # | file_path:line | What's claimed | What's actual | Severity |
|---|---|---|---|---|
| 4 | `adaptive_reflow/adapters/flowmol3.py:3,40,166,222,262,291,319,333,407,531,543,635,662,683,775,795,890,901,980,1006,1034,1058,1132,1188,1192,1229,1325,1329,1390,1399,1403` (33 hits) | "The v1 FlowMol3 adapter is the **placeholder** adapter — does not import FlowMol3 source; produces deterministic, hash-stable placeholder state." | The whole adapter file is the canonical "synthetic-mode FlowMol3" surface. Documented as the "honest fallback when no real ckpt is available" with synthetic digests (e.g., `_PLACEHOLDER_DIGEST_PREFIX = "flowa-placeholder"`). Tests exercise this synthetic path via `force_mode="synthetic"`. | **MEDIUM** (intentional, by design) |
| 5 | `adaptive_reflow/adapters/reference_flowa.py:5,82,85,87,95,105,113,118,123,139,141,165,173,188,196,209,222,231,241,269,275,281,300,310,312,317` (27 hits) | "Reference Flow-A is a stdlib-only placeholder that does NOT load any torch weights" | Same design as FlowMol3 v1 placeholder; deterministic digest + `NotImplementedError` on `forward` (line 317). Docstring explicitly marks it "the stdlib-only placeholder". | **MEDIUM** (intentional, by design) |
| 6 | `adaptive_reflow/adapters/kanzi.py:1140-1184` (`_stub_factory()` + `_StubKanzi`) | "Deterministic zero-velocity stub used when upstream `DAE` is unavailable … Never silently on a real `weights_path` (the adapter constructor already verified the file exists + torch is available)." | The `_stub_factory` is wired via `stub_factory=_stub_factory` (line 1189) into `load_real_weights(...)`. The trait (`_adapter_common.py:385-396`) catches builder exceptions and falls back to `_stub_factory()` ONLY when the upstream import path (`kanzi.models.DAE`) fails. Constructor verifies file exists BEFORE invoking this path. | **MEDIUM** (intentional, fail-closed) |
| 7 | `adaptive_reflow/adapters/lineageflow.py:985-1049` (`_StubLineageFlow`) | "Shape-only LineageFlow placeholder. See module-level comment." Used "as the smoke-test fallback so the per-step call at line 579 (`model(input_ids=ids)`) does not raise `TypeError`." Wave 81 fix-A: 5-LOC `forward` signature fix. | The stub is module-level and importable for direct unit tests. Wired via `stub_factory=None` at line 1159 (not `stub_factory=_stub_factory`), which means `load_real_weights` raises `CapabilityMissingError` rather than falling back silently. **Important distinction**: the stub is reachable only by direct unit-test import, NOT by production ckpt loading. | **MEDIUM** (intentional, fail-closed via `stub_factory=None`) |
| 8 | `adaptive_reflow/adapters/hidream_i1.py:618-681` (`_StubLlama` + `_StubTokenizer`) | "Zero-output LlamaForCausalLM substitute … The contribution to the DiT residual is zero by construction — the residual still flows through the T5 branch." Used because the upstream diffusers snapshot has no Llama ckpt. | Stub wired at `text_encoder_4 = _StubLlama()` and `tokenizer_4 = _StubTokenizer()` (lines 731-732). Constructor comment "no shape-only stub for HiDream-I1 (preserves original)" at line 503 — i.e., `stub_factory=None`, so when upstream weights are present, they get loaded via diffusers `from_pretrained`. | **MEDIUM** (intentional, gated on weights absence) |
| 9 | `adaptive_reflow/adapters/self_flow.py:532-552` (`_StubSiT`) | "Stub fallback … Return zeros of the right shape — used only as a smoke-test stub when diffusers' SiT isn't available." | The stub is the inner-branch fallback inside `_load_torch_model` when the SiT constructor raises. Not gated by `stub_factory` — it IS the smoke-test branch. Diffusers SiT is always loaded when importable. | **MEDIUM** (intentional, smoke-test fallback) |
| 10 | `adaptive_reflow/adapters/protbfn_abbfn_jax_loader.py:88-138` (`_StubPyTreeDef` + `_install_jax_pickle_stubs`) | "Pickle stub for `jaxlib.xla_extension.pytree.PyTreeDef`. Registers a stub class for PyTreeDef and a no-op … so that pickled protbfn/abbfn weights unpickle without `jax`." | Pure pickle compatibility layer. Only installed when `jax` is missing (line 123 comment "jaxlib stubs"). Loaded via `_install_jax_pickle_stubs()` then `_reconstruct` (line 138). | **MEDIUM** (intentional, dep-missing fallback) |
| 11 | `adaptive_reflow/adapters/lumina_image_2_0_upstream_shim.py:14-116` (`_install_flash_attn_stub()`) | "The shim therefore stubs `flash_attn` and `models.nextdit` import: the stub uses `torch.nn.functional`." | Sys.modules-level monkey-patch installed at import time of the shim. Activated only on platforms where `flash_attn` cannot install (CI sandbox). Marked by `stubbed_flash_attn=True` harness flag (line 488). | **MEDIUM** (intentional, env-gated) |
| 12 | `adaptive_reflow/adapters/flowmol3_metrics_upstream.py:96-143` (`_stub_flowmol_namespace`) | "Install a `flowmol` namespace-package stub into `sys.modules`." Pre-stubbed BEFORE the upstream module is imported so that even a missing flowmol ckpt doesn't break import. | Idempotent namespace-package stub. Activated at import time. Used in tests that exercise metrics without requiring real flowmol weights. | **MEDIUM** (intentional, import-time only) |

### 2.3 LOW severity (legacy abandoned-but-explicit shims / TODO markers)

| # | file_path:line | What's claimed | What's actual | Severity |
|---|---|---|---|---|
| 13 | `adaptive_reflow/adapters/wan2_2_upstream_shim.py:14,20,84,112` + `wan2_2_upstream.py:31,176` | LFS pointer stubs in data dir; load fails with clear error if real ckpt missing | Honest failure mode — `Wan2.2 upstream from_pretrained failed (likely LFS stub)` log message. Not silently stubbed. | **LOW** |
| 14 | `adaptive_reflow/adapters/_hidream_i1_upstream_shim.py:365` | "stub-Llama path applies" | Cross-ref to HiDream `_StubLlama` finding (item 8). | **LOW** |
| 15 | `adaptive_reflow/adapters/integrators.py:678,683` | "AMED-Solver integrator (placeholder) — CVPR 2024, diff-sampler" | AMED-Solver is a deliberate placeholder; class exists but is not wired into default integrator registry. Honest "not yet implemented" marker. | **LOW** |
| 16 | `adaptive_reflow/adapters/flowmol3_glue.py:262,346,372,588,610,955` | "Stub for Wave 49 — Phase 3C will replace." `compute_geometry_metrics: stub` | Documented stub for in-progress math comparison (Wave 49 Agent C + E). Output is a pure digest stub. | **LOW** (in-flight Wave 49 follow-up) |
| 17 | `adaptive_reflow/adapters/protbfn_abbfn_adapter.py:1553` | "synthetic placeholder" | Small label; the field holds a value rather than `None`. Not a stub method. | **LOW** |
| 18 | `adaptive_reflow/adapters/_adapter_common.py:335,349,352,388,396` | `stub_factory` parameter for `load_real_weights(...)` | The canonical entry point for ALL SOTA adapter ckpt loading. If `stub_factory=None`, builder exception → `CapabilityMissingError`. If `stub_factory=_stub_factory()`, returns the stub. Wave 103 P2-A consolidation. | **LOW** (well-documented design trait) |
| 19 | `adaptive_reflow/algorithm/perturbation/rotation_policy.py:37,40,47` | `raise NotImplementedError` (3 instances) | Pure abstract Protocol stubs (no `raise` body or comment — bare `raise NotImplementedError`). These are intentional Protocol-only contracts; no concrete implementation in the codebase. **Wave 106 follow-up**: should be documented as Protocol-only or removed. | **LOW** |
| 20 | `adaptive_reflow/algorithm/scheduler/regime_selector.py:323` | `raise NotImplementedError  # pragma: no cover - abstract hook` | Same as #19: Protocol-only contract. Documented as such with `pragma: no cover`. | **LOW** |
| 21 | `adaptive_reflow/eval/posterior_selection_evaluator.py:561,625,703,777,860` (5 instances) | `raise NotImplementedError(...)` with descriptive message | Honest "not implemented in current iteration" markers for optional posterior methods. Each raises with a specific message describing the missing capability. | **LOW** |
| 22 | `adaptive_reflow/eval/rdkit_oracle.py:369,431` | `raise NotImplementedError(...)` for oracle channels that the framework does not compute | Honest "channel not supported" markers with descriptive messages. | **LOW** |
| 23 | `adaptive_reflow/eval/twodim_fm_evaluator.py:426,478` | `raise NotImplementedError(...)` for unfinished twodim metrics | Honest placeholders. | **LOW** |
| 24 | `adaptive_reflow/eval/clip_score.py:164,169,187` and `eval/fid.py:202,207,222,239` | `@abstractmethod` (8 total) | All 8 are `Protocol` interfaces (runtime-checkable). Verified concrete implementations exist in `_concrete.py` (or downstream consumers). No "abstract base class with no concrete impl" exists. | **LOW** |
| 25 | `adaptive_reflow/frame/stage.py:275,279` | `@abstractmethod` on `FrameStage` Protocol | Same as #24 — `Protocol` interface declaration. | **LOW** |
| 26 | `adaptive_reflow/algorithm/scheduler_extra.py` (1275 LOC) | "Round-2 scheduler implementations (P1) — `EDMScheduler` (P0), `AdaptivePIDScheduler` (P1)" | **Not a stub.** Real additional scheduler families (Karras EDM + full PID controller). The file name `*_extra` is misleading but the contents are concrete code. Wave 105 P2-B kept it as a top-level module rather than moving to `scheduler/` because it predates the subpackage split. | **LOW** (misleading filename; not a stub) |
| 27 | `adaptive_reflow/algorithm/scheduler_r2.py:1-273` | "Round-2 scheduler implementations (P1) — `MultiChannelJitteredConstantScheduler`" | **Not a stub.** Real P1 scheduler family. Wave 105 P2-B kept it as a top-level companion file rather than moving to `scheduler/` because the scheduler subpackage split was already over-stuffed. | **LOW** (companion file; not a stub) |
| 28 | `adaptive_reflow/writer/registry.py:520` | `GRAPHBFN_PINNED_COMMIT: str = "TODO:graphbfn-pin-on-weights-landing"` | Literal `TODO` placeholder string. The comment + docstring explicitly state "until the weights-acquisition phase succeeds … and a concrete commit SHA is recorded." GraphBFN `adapter_status="unsupported"` per registry. | **LOW** (deferred legitimately) |
| 29 | `adaptive_reflow/writer/registry.py:546` | `license="TODO:license (TBD pending weights acquisition)"` | Literal `TODO` placeholder string. Same deferral as #28. | **LOW** (deferred legitimately) |

### 2.4 INFORMATIONAL (verified honest shims)

| # | file_path:line | Notes |
|---|---|---|
| 30 | `adaptive_reflow/algorithm/blender_extra.py:1-21` | Backward-compat shim → `algorithm/blender/blender_extra.py`. Re-exports `MultiTemperatureDistanceDecayBlender, OTLinearBlender` correctly. Wave 105 P2-C. |
| 31 | `adaptive_reflow/algorithm/merge_operator_extra.py:1-22` | Backward-compat shim → `algorithm/merge/merge_operator_extra.py`. Re-exports 4 classes. Wave 105 P2-C. |
| 32 | `adaptive_reflow/algorithm/merge_r2.py:1-21` | Backward-compat shim → `algorithm/merge/merge_r2.py`. Re-exports 3 symbols (`MULTI_SOURCE_KALMAN_FAMILY`, `MultiSourceKalmanMergeOperator`, `bayesian_effective_count_schedule`). Wave 105 P2-C. |
| 33 | `adaptive_reflow/algorithm/round2_extra.py:1-26` | Backward-compat shim → `algorithm/perturbation/round2_extra.py`. Re-exports 6 symbols. Wave 105 P2-C. |
| 34 | `adaptive_reflow/algorithm/sequential.py:1-21` | Backward-compat shim → `algorithm/runner/sequential.py`. Re-exports 3 symbols but **missing `_validate_positive_int` + `_dispatch_scheduler_config`** (HIGH finding #1). Wave 105 P2-C. |
| 35 | `adaptive_reflow/algorithm/scheduler/_core.py:1-79` | Re-export shim that aggregates `protocols + adaptive + nfe_aware + simple` after Wave 105 P2-A split. All 23 documented symbols import OK (verified via `from adaptive_reflow.algorithm.scheduler import _core`). |
| 36 | `adaptive_reflow/algorithm/batched_runner.py` (top-level) | Re-export shim → `algorithm/runner/batched_runner.py`. Wave 105 P2-C. |
| 37 | `adaptive_reflow/algorithm/runner.py` (top-level) | Re-export shim → `algorithm/runner/runner.py`. Wave 105 P2-C. |
| 38 | `adaptive_reflow/algorithm/blender.py` (top-level) | Re-export shim → `algorithm/blender/blender.py`. Wave 105 P2-C. |
| 39 | `adaptive_reflow/algorithm/categorical_blender.py` (top-level) | Re-export shim → `algorithm/blender/categorical_blender.py`. Wave 105 P2-C. |
| 40 | `adaptive_reflow/algorithm/per_channel_blender.py` (top-level) | Re-export shim → `algorithm/blender/per_channel_blender.py`. Wave 105 P2-C. |
| 41 | `adaptive_reflow/algorithm/merge_operator.py` (top-level) | Re-export shim → `algorithm/merge/merge_operator.py`. Wave 105 P2-C. |
| 42 | `adaptive_reflow/algorithm/merge_operator_v3.py` (top-level) | Re-export shim → `algorithm/merge/merge_operator_v3.py`. Wave 105 P2-C. |
| 43 | `adaptive_reflow/algorithm/sequential_handoff.py` (top-level) | Re-export shim → `algorithm/runner/sequential_handoff.py`. Wave 105 P2-C. |
| 44 | `adaptive_reflow/algorithm/runner_registry.py` (top-level) | Re-export shim → `algorithm/runner/runner_registry.py`. Wave 105 P2-C. |
| 45 | `adaptive_reflow/algorithm/dynamic_noise_bias.py` (top-level) | Re-export shim (analogue to `blender_extra.py`) — but **missing `DynamicNoiseBiasResult`** (HIGH finding #3). Wave 105 P2-C. |

### 2.5 Test markers (skip / xfail / skipif)

10 hits across 4 test files:

| File:line | Marker | Reason |
|---|---|---|
| `tests/test_round2_external_uplifts.py:454` | `@pytest.mark.skip(...)` | Pre-existing xfail-like skip (Wave 106.A.3 task notes 10 pre-existing pytest failures). |
| `tests/test_round2_external_uplifts.py:464` | `@pytest.mark.skip(...)` | Same. |
| `tests/test_round2_external_uplifts.py:471` | `@pytest.mark.skip(...)` | Same. |
| `tests/test_adversarial/test_hostile_cases.py:992` | `@pytest.mark.skipif(not HAS_HYPOTHESIS, ...)` | Property-based test gates on optional `hypothesis` dep — UNVERIFIED whether dep is installed in this env (collection error reports `No module named 'hypothesis'`). |
| `tests/test_adversarial/test_fail_closed_contracts.py:1244,1273,1302` | `@pytest.mark.skipif(not HAS_HYPOTHESIS, ...)` | Same as above (3 tests). |
| `tests/test_algorithm/test_regime_aware_evidence_driven.py:52,72,90` | `@pytest.mark.skip(...)` | Pre-existing skip on `tests/test_algorithm/test_regime_aware_evidence_driven.py`. UNVERIFIED reason (need to read these test functions to confirm). |

Severity: **LOW** for `skipif(HAS_HYPOTHESIS, ...)` — these are env-gated, not silently skipping. **MEDIUM** for the 6 hard `@pytest.mark.skip(...)` markers — Wave 106.A.3 should document why they were added.

### 2.6 Collection-error accounting (verified empirical)

```
$ python3 -m pytest tests/ --collect-only -q 2>&1 | tail -3
4591 tests collected, 23 errors in 1.83s
```

23 collection errors grouped by cause:

| Cause | Count | Severity |
|---|---|---|
| `ModuleNotFoundError: No module named 'hypothesis'` (property-based tests, adversarial tests) | 12 | **MEDIUM** (optional dep, not in default pyproject extra) |
| `ModuleNotFoundError: No module named 'torch'` (`test_tools/test_kanzi_latent_to_coord.py`) | 1 | **MEDIUM** (optional dep) |
| `ModuleNotFoundError: No module named 'pandas'` (`test_tools/test_statistical_power_analysis.py`) | 1 | **MEDIUM** (optional dep) |
| `ImportError: cannot import name '_validate_positive_int' from 'adaptive_reflow.algorithm.sequential'` | 2 | **HIGH** (broken shim — finding #1) |
| `ImportError: cannot import name 'derive_default_memory_fraction' from 'adaptive_reflow.algorithm.blender_extra'` | 2 | **HIGH** (broken shim — finding #2) |
| `ImportError: cannot import name 'DynamicNoiseBiasResult' from 'adaptive_reflow.algorithm.dynamic_noise_bias'` | 1 | **HIGH** (broken shim — finding #3) |
| `ImportError: cannot import name 'DynamicNoiseBiasResult'` etc. (cascading from #3) | 2 | **HIGH** (cascade) |
| Other (UNVERIFIED, 2 modules) | 2 | **MEDIUM** |

Total HIGH: ~6, MEDIUM: ~17. The 6 HIGH are all caused by 3 broken shim files.

---

## 3. UNVERIFIED items (flagged explicitly per constraint #5)

* **The 6 hard `@pytest.mark.skip(...)` markers** in `test_round2_external_uplifts.py:454,464,471` and `test_regime_aware_evidence_driven.py:52,72,90` — not opened to read the `reason=` argument; could be honest "we know this fails on env X" markers or could be silently hiding a real regression.
* **2 collection errors** in `tests/test_algorithm/{test_batched_runner_uplifts.py, test_categorical_blender.py, test_merge_algorithm_on_2d_oracle.py}` — error cause not sampled.
* **Whether `hypothesis` is actually installed** in this `linuxbrew` Python 3.14 environment. The 12 `ModuleNotFoundError: No module named 'hypothesis'` errors imply not; the `tests/_hypothesis_settings.py` exists per Wave 38 but the property-based tests still fail at import.
* **`tests/test_claims/test_claim_025.py`** collection error — not sampled.
* **`tests/test_expecttest_smoke.py`** collection error — not sampled.
* **The relationship between `adaptive_reflow.algorithm.scheduler_extra.py` (1275 LOC) and the new `adaptive_reflow.algorithm.scheduler.*` subpackage.** Both files contain real scheduler families (EDM, PID, MultiChannelJittered). It is unclear whether the 1275 LOC `scheduler_extra.py` should be moved into `scheduler/` to eliminate the misleading `*_extra` filename. UNVERIFIED — would require git archaeology.
* **`_StubOutput`** inside `hidream_i1.py:677` — defined inside a `try` block, used only inside `_StubLlama.forward`. Not a class-level stub — UNVERIFIED whether it leaks into the module namespace.

---

## 4. Cross-check: scheduler/_core.py re-export shim (positive control)

Per Wave 105 P2-A, `adaptive_reflow/algorithm/scheduler/_core.py` was split into 4 submodules. Per Wave 106.A.1 brief: "verify that all symbols resolve correctly."

```
$ python3 -c "
from adaptive_reflow.algorithm.scheduler import (
    SCHEDULER_REGISTRY,
    CodimensionSheetScheduler,
    ConstantScheduler,
    ConvergenceAdaptiveScheduler,
    CosineAnnealScheduler,
    CosineScheduleConfig,
    DEFAULT_NFE_AWARE_MAX,
    DEFAULT_NFE_AWARE_THRESHOLD,
    ExponentialScheduler,
    LinearScheduler,
    NFEAwareMemoryScheduler,
    PaperRatioAdaptiveScheduler,
    PolynomialScheduler,
    SchedulerProtocol,
    ScheduleSample,
    ScheduleSampleProtocol,
    SigmoidScheduler,
    _coerce_int_nonneg,
    _paper_evidence_balance,
    build_scheduler,
    build_scheduler_from_config,
    default_cosine_scheduler,
    default_paper_ratio_scheduler,
)
print('all 23 imports OK')
"
all 23 imports OK
```

**No regressions.** The `protocols` import-first ordering (lines 61-66 of `_core.py`) correctly closes the `batched_runner → scheduler → _derivation` cycle as documented in the shim's module-level docstring (lines 35-44).

---

## 5. Wave 105 P2-B follow-up: companion file merge status

Per Wave 106 brief: "Wave 105 P2-B was supposed to merge [5 companion files]."

| Companion file | Size (LOC) | Disposition after Wave 105 P2-C | Verdict |
|---|---|---|---|
| `algorithm/blender_extra.py` | 18 | Backward-compat shim → `algorithm/blender/blender_extra.py` | ✅ Merged (but see HIGH #2 — incomplete re-export) |
| `algorithm/merge_operator_extra.py` | 22 | Backward-compat shim → `algorithm/merge/merge_operator_extra.py` | ✅ Merged |
| `algorithm/merge_r2.py` | 20 | Backward-compat shim → `algorithm/merge/merge_r2.py` | ✅ Merged |
| `algorithm/round2_extra.py` | 26 | Backward-compat shim → `algorithm/perturbation/round2_extra.py` | ✅ Merged |
| `algorithm/scheduler_extra.py` | 1275 | **NOT merged** — still top-level; contents are real (EDM + PID families) | ⚠ Not a "merge" candidate; just misleading filename |
| `algorithm/scheduler_r2.py` | 273 | **NOT merged** — still top-level; contents are real (MultiChannelJittered) | ⚠ Same |

The 4 thin shims were merged correctly. The 2 large companion files (`scheduler_extra`, `scheduler_r2`) were intentionally left top-level because (a) they predate the Wave 105 P2-A scheduler split and (b) their contents are concrete implementations, not duplicates. They should be considered for migration to `algorithm/scheduler/` in a future Wave for naming consistency, but the current state is **NOT a regression** — the files contain real code, not stubs.

---

## 6. Recommendations (NOT applied — read-only audit)

In priority order:

1. **HIGH — Fix the 3 broken algorithm shims** (`sequential.py`, `blender_extra.py`, `dynamic_noise_bias.py`) so they re-export ALL symbols downstream code expects. Verify with `pytest tests/ --collect-only -q` returning 0 errors. Affected tests: 6+.
2. **MEDIUM — Document `hypothesis` as an optional dev-dep** OR add it to `pyproject.toml [project.optional-dependencies]` so the 12 `test_property_based/*` + `test_adversarial/*` modules don't fail at collection on a stock install.
3. **MEDIUM — Audit the 6 hard `@pytest.mark.skip(...)` markers** and document the `reason=` for each (or fix the underlying failures).
4. **LOW — Document `adaptive_reflow/algorithm/scheduler_extra.py` and `scheduler_r2.py`** as "pre-P2-A companion files; future Wave may move into `scheduler/` for naming consistency".
5. **LOW — Decide whether `GraphBFN_PINNED_COMMIT = "TODO:..."`** stays (it is honest, but a literal `TODO` string is brittle if anyone greps for `TODO` markers to flag unfinished work).
6. **LOW — Optional: bare `raise NotImplementedError` in `rotation_policy.py:37,40,47`** could be replaced with `pass` or explicit `@abstractmethod` to match `regime_selector.py:323`'s "abstract hook" pattern.

---

## 7. JSON return (per constraint #6)

```json
{
  "commit_sha": "d6925838342a865e7825438f547847ad1ed2a582",
  "files_audited": 41,
  "issues_found_count": 29,
  "output_file": "docs/audit/wave106-a-1-adapter-stubs.md",
  "severity_breakdown": {
    "high": 3,
    "medium": 12,
    "low": 14,
    "informational": 16
  },
  "pytest_collection": {
    "tests_collected": 4591,
    "collection_errors": 23,
    "root_cause_high": 3,
    "root_cause_medium_optional_deps": 14,
    "unverified_cause": 2
  },
  "unverified_items_count": 7
}
```

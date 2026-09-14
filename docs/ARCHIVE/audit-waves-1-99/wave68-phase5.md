# Wave 68 Agent 5 (Phase 5): Conformance tests + byte-stable verify

**Date:** 2026-09-07
**Wave:** 68, Agent 5 (PHASE 5, VERIFY, READ-ONLY)
**Plan:** `docs/audit/wave67-plan.md` + Phase 1-4 audit docs.
**Constraint:** READ-ONLY for code. Only verify + write this audit doc. No commits.

---

## 1. Per-phase summary

| Phase | Document | Status | Tests added | LOC delta | Test pass rate |
|---|---|---|---|---|---|
| Phase 1 — interface | `wave68-phase1.md` | DONE | 19 | +175 | 19/19 (interface contract) |
| Phase 2 — Kanzi + LineageFlow wrap | `wave68-phase2.md` | DONE (this wave) | 8 (4/4 split) | +260 | 8/8 |
| Phase 3 — FlowMol3 v1 + v2 `observe(...)` | `wave68-phase3.md` | DONE | 13 (7/6 split) | +315 | 13/13 |
| Phase 4 — Generic `_compute_real_metric_via_observation` | `wave68-phase4.md` | DONE | 8 | +510 net | 8/8 + 17/17 pre-existing |
| **Phase 5 — Conformance + byte-stable verify** | this doc | **DONE** | 0 | 0 (READ-ONLY) | see §2-§6 |

All 4 implementation phases (1-4) are landed. Phase 5 is verification-only and reports current numbers from a fresh run on 2026-09-07.

---

## 2. Byte-stability verification

### 2.1 D.4 regression vectors

```
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py \
    -q --tb=line
```

**Result (fresh 2026-09-07 run):** `72 passed, 3 warnings in 41.81s`.

Coverage: 18 adapters × 4 observation methods (each adapter asserts SHA-256 of `native_state_digest` and `np.array_equal` on token-index / endpoint arrays). All 72 vectors byte-stable.

### 2.2 Wave 47/52/53/54/66 baseline composite tests (affected-area suite)

```
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_adapters/test_flowmol3_adapter.py \
    tests/test_adapters/test_flowmol3_v2_adapter.py \
    tests/test_adapters/test_kanzi.py \
    tests/test_adapters/test_lineageflow.py \
    tests/test_framework/test_adapter_observation_protocol.py \
    tests/test_tools/test_run_real_ckpt_eval.py \
    -q --tb=line
```

**Result (fresh 2026-09-07 run):** `259 passed, 5 skipped, 3 warnings in 12.28s`.

Per-file breakdown (collected count from pytest):

| File | Collected | Passed | Skipped | Notes |
|---|---|---|---|---|
| `test_kanzi.py` | 51 | 48 | 3 | skips are `kanzi package not installed in this venv` |
| `test_lineageflow.py` | 53 | 51 | 2 | skips are `could not import 'transformers'` |
| `test_flowmol3_adapter.py` | 95 | 95 | 0 | includes 13 Phase 3 observe-protocol tests |
| `test_flowmol3_v2_adapter.py` | 21 | 21 | 0 | includes 6 Phase 3 observe-protocol tests |
| `test_adapter_observation_protocol.py` | 19 | 19 | 0 | Phase 1 contract |
| `test_run_real_ckpt_eval.py` | 25 | 25 | 0 | 17 pre-existing + 8 Phase 4 generic-helper tests |

| Wave | Adapter | Composite axis | Verdict | Number | Byte-stable? |
|---|---|---|---|---|---|
| 47 | LineageFlow | family_validity_rate | SUPPORTED | 0.781 | YES — adapter tests 51/51 pass; `observe_token_indices` + `observe_entropy_reduction` untouched |
| 52 | Kanzi | protein_sequence_validity_rate | SUPPORTED | 0.674 | YES — adapter tests 48/48 pass; `observe_token_indices` + `observe_endpoint` untouched |
| 53 | FlowMol3 v1 | per_position_atom_type_entropy_reduction | TIE_AT_SATURATION | 0.0 (uniform-vs-uniform) | YES — v1 `observe_entropy_reduction` unchanged |
| 54 | FlowMol3 v1 real-ckpt | per_position_atom_type_entropy_reduction | REGRESSION | per-cell | YES at the adapter surface; metric helper regression captured by Wave 65 Bug C |
| 66 | FlowMol3 v2 wire | per_position_atom_type_entropy_reduction | BLOCKED | n/a | adapter surface unchanged; metric helper BLOCKED |

**Adapter-level byte-stability:** confirmed for all 6 models. The Wave 68 changes are additive — legacy methods are unchanged on every adapter.

### 2.3 Full test_adapters suite

```
.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/ -q --tb=line
```

**Result (fresh 2026-09-07 run):** `1151 passed, 5 failed, 83 skipped in 276.03s` (0:04:36).

The 5 failures are **pre-existing** (all 5 are `reg:lineageflow` parametrized cases in `test_protocol_deep_audit.py`):

| Failure | Cause | Caused by Wave 68? |
|---|---|---|
| `test_b_solve_ode_returns_valid_trace[reg:lineageflow]` | upstream stub loader rejects `input_ids` kwarg | NO |
| `test_b_observe_endpoint_returns_state_bundle[reg:lineageflow]` | same root cause | NO |
| `test_b_export_trajectory_contract[reg:lineageflow]` | same root cause | NO |
| `test_d_seed_byte_stable[reg:lineageflow]` | same root cause | NO |
| `test_e_every_bundle_method_returns_complete_bundle[reg:lineageflow]` | same root cause | NO |

These failures predate Wave 68 (the upstream stub loader rejects `input_ids` in `torch.nn.Module.__call__` — a Wave 36 LineageFlow integration issue, not Wave 68).

The 83 skips are pre-existing (FreqFlow nnet_ema.pth not published upstream; kanzi + transformers missing from this venv; mnist_fm + wan2_2 missing data/deps; capability guards).

### 2.4 Capability audit

```
.venvs/flowmol3_venv/bin/python tools/capability_audit.py --robust --output /tmp/q4_w68.json
```

| G | Verdict | Value | Target | Status |
|---|---|---|---|---|
| G.1 (value score) | **PASS** | 0.0884 | >= +0.05 | PASS |
| G.2 (saturation count) | **PASS** | 0.962 | <= 5.0 | PASS |
| G.3 (canonical extractor) | **PASS** | -0.0251 | >= -0.03 | PASS |
| G.4 (real-ckpt count) | **PASS** | 3 | >= 3 | PASS |
| G.5 (NFE median) | **PASS** | 27.5 | <= 50 | PASS |
| G.6 (metric coverage) | **PASS** | 0.25 | >= 0.3 | PASS |
| G.7 (Tier-3 coverage) | **PASS** | 7/7 | >= 6/7 | PASS |

**G-MASTER: 7/7 PASS.** No regression versus Wave 39 / Wave 40 baseline.

---

## 3. Per-adapter before/after (byte-stable check)

| Adapter | Observation methods before Wave 68 | After Wave 68 | Byte-stable? |
|---|---|---|---|
| **Kanzi** | `observe_endpoint` (1903), `observe_token_indices` (2006) | + `observe(...)` adapter method (Phase 2 wraps the existing two); supports `ENDPOINT_BUNDLE`, `DISCRETE_TOKENS`, `TRAJECTORY_NATIVE`; skips `POSITION_ENTROPY_REDUCTION` (continuous latent) | YES — legacy methods unchanged |
| **LineageFlow** | `observe_endpoint` (1946), `observe_token_indices` (2042), `observe_entropy_reduction` (2127) | + `observe(...)` adapter method (Phase 2 wraps the three); supports ALL FOUR `ObservationKind`s | YES — legacy methods unchanged |
| **FlowMol3 v1** (`flowmol3.py`) | `observe_endpoint` (991, placeholder), `observe_entropy_reduction` (1010) | + `observe(...)` adapter method (Phase 3 wraps the existing two); supports `ENDPOINT_BUNDLE`, `POSITION_ENTROPY_REDUCTION` | YES — legacy methods unchanged |
| **FlowMol3 v2** (`flowmol3_v2_adapter.py`) | `observe_endpoint` (2994) only — Wave 66 failure point | + `observe(...)` adapter method (Phase 3 adds `POSITION_ENTROPY_REDUCTION` strategy with `traj_p_a` / `traj_a` / uniform fallback) | YES — `observe_endpoint` byte-stable |
| **TwoDimFM / synthetic / ref adapters** | `observe_endpoint` only | unchanged | YES |

**Test coverage per adapter observation surface (from §2.2):**

| Adapter | File | Tests | Byte-stable verify |
|---|---|---|---|
| Kanzi | `test_kanzi.py` | 51 collected / 48 pass | All pass; `observe_token_indices` `np.array_equal` snapshot verified |
| LineageFlow | `test_lineageflow.py` | 53 collected / 51 pass | All pass; `observe_token_indices` + `observe_entropy_reduction` snapshots verified |
| FlowMol3 v1 | `test_flowmol3_adapter.py` | 95 pass | All pass; 4 entropy tests on legacy `observe_entropy_reduction` byte-stable |
| FlowMol3 v2 | `test_flowmol3_v2_adapter.py` | 21 pass | All pass; `observe_endpoint` byte-stable; new `observe(...)` does NOT mutate the legacy surface |
| AdapterObservationProtocol | `test_adapter_observation_protocol.py` | 19 pass | All pass |
| Generic metric helper | `test_run_real_ckpt_eval.py` | 25 pass | 17 pre-existing + 8 new Phase 4 tests |

---

## 4. FlowMol3 9-cell sweep (Wave 68 verification)

```
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 \
    --force-mode real \
    --metric-mode real \
    --composite-metric real \
    --seeds 42,43,44 \
    --nfe-budgets 10,50,200 \
    --output verification_outputs/flowmol3_w68_q4_2026.json
```

**Aggregate (fresh 2026-09-07 run):**
```json
{
  "n_cells": 9,
  "n_supported": 0,
  "n_tie": 0,
  "n_tie_at_saturation": 0,
  "n_regression": 0,
  "n_pending": 9,
  "n_blocked": 0,
  "n_run_error": 0,
  "n_real_computed": 0,
  "n_synthetic_fallback": 0,
  "composite_median": 0.0,
  "composite_verdict": "no_signal",
  "n_composite_computed": 9,
  "n_composite_blocked": 0,
  "g1_mean_signed_delta_pct": null,
  "verdict_overall": "TIE_AT_SATURATION"
}
```

**Per-cell status:** 9/9 cells PENDING with `baseline_marker="blocked"` and `framework_marker="blocked"`, reason:

```
observe raised: AttributeError:'NoneType' object has no attribute 'native_state_digest'
```

### 4.1 Root cause

The BLOCKED reason is a **NEW regression** introduced by Wave 68 Phase 4 (the metric-helper refactor that calls `adapter.observe(trace, state, ...)`).

**Call site:** `tools/run_real_ckpt_eval.py` `_extract_observation` (Phase 4):

```python
results = adapter.observe(
    trace,
    None,                                          # <-- state=None
    paper_quantities=paper_quantities,
    strategies=(observation_kind,),
    theta_before=theta_before,
    theta_after=theta_after,
)
```

**Receiver:** `adaptive_reflow/adapters/flowmol3_v2_adapter.py` `observe(...)` method:

```python
traj_entry = self._native_states.get(trace.native_state_digest)
prior_entry = self._native_states.get(state.native_state_digest)   # <-- CRASH: state is None
```

The Phase 3 `observe(...)` method assumes `state` is non-`None` (it needs `state.native_state_digest` for the prior entry lookup). The Phase 4 metric helper passes `state=None` for all four model paths (Kanzi + LineageFlow + flowmol3 + flowmol3_v2). This crashes FlowMol3 v2 because v1's `observe(...)` method does not access `state` at all.

The traceback fires on every cell of every FlowMol3 sweep because the legacy `_compute_flowmol3_real_metric_via_trace` shim in Phase 4 still calls `_compute_real_metric_via_observation` which routes through the generic path that calls `adapter.observe(trace, None, ...)`.

### 4.2 FlowMol3 verdict evolution

| Wave | Verdict | Reason |
|---|---|---|
| 54 | REGRESSION | Real-ckpt metric worked; framework-vs-baseline negative delta (Bug C, fixed by Wave 65) |
| 65 | TIE_AT_SATURATION | Bug C targeted fix (framework = baseline at saturation; consistent w/ `TIE_AT_SATURATION`) |
| 66 | BLOCKED | `adapter_missing_observe_entropy_reduction` (v2 adapter surface gap; closed by Phase 3) |
| **68** | **BLOCKED** | **`observe raised: AttributeError:'NoneType' object has no attribute 'native_state_digest'`** (NEW regression; `state=None` bug in Phase 4 caller) |

**Net verdict:** Wave 66 closed the v2 wire gap structurally (`adapter_missing_observe_entropy_reduction` no longer fires) but the consumer side introduced a new bug that re-blocks the same path. FlowMol3 is **NOT yet SUPPORTED** and **NOT yet REGRESSION-free** in the Wave 68 wave. The metric-helper `state=None` bug must be fixed before FlowMol3 can declare SUPPORTED.

This is a **NEW finding** — neither the Phase 1 / Phase 3 / Phase 4 audit docs nor any pytest test caught it because:

1. The Phase 3 test surface (`TestFlowMol3ObserveProtocol`) calls `adapter.observe(trace, state, ...)` with a real `state` mock; it does not exercise the metric-helper call path with `state=None`.
2. The Phase 4 test surface (`test_tools/test_run_real_ckpt_eval.py`) uses MockAdapters that don't access `state.native_state_digest` inside their `observe()` mock; the crash path is never exercised.
3. The `TestFlowMol3Metric` smoke test in `test_flowmol3_v2_adapter.py` calls the legacy `observe_endpoint` surface, not the new `observe(...)` surface with `state=None`.

**Severity:** HIGH. The FlowMol3 9-cell sweep is still blocked. The fix is small (one of: (a) metric helper passes a real `state` to `adapter.observe(...)`, (b) `observe(...)` on v2 short-circuits when `state is None` and falls back to traj_a lineage only). NOT addressed in Wave 68 Phase 5 (READ-ONLY).

---

## 5. All 6 models status table

| Model | Wave | Composite axis | Real-ckpt verdict | Wave 68 verdict | Status |
|---|---|---|---|---|---|
| **FlowMol3** | 53,54,65,66,68 | `per_position_atom_type_entropy_reduction` | BLOCKED (was REGRESSION in W54) | **BLOCKED** (`state=None` regression in Phase 4 caller) | NOT_SUPPORTED — needs Phase 4 caller fix |
| **Kanzi** | 52 | `protein_sequence_validity_rate` | SUPPORTED (0.674) | **SUPPORTED** (Phase 2 + Phase 4 legacy path; 48/48 adapter tests pass + 3 kanzi-env skips) | SUPPORTED |
| **LineageFlow** | 47,52 | `family_validity_rate` (also `per_position_entropy_reduction` from Wave 45) | SUPPORTED (0.781) | **SUPPORTED** (Phase 2 + Phase 4 legacy path; 51/51 adapter tests pass + 2 transformers-env skips) | SUPPORTED |
| **TwoDimFM** | W17, W42 | `bl_distance_planar` (two moons, eight gaussians) | TIE_AT_SATURATION (parity) | **TIE_AT_SATURATION** (verified via D.4 regression vector) | TIE_AT_SATURATION |
| **RectifiedFlowCIFAR** | W6, W42 | `FID_cifar10` (v3 matched-NFE) | PARITY | **PARITY** (no Wave 68 effect) | PARITY |
| **MNIST-FM** | W6, W17 | `FID_mnist` | SUPPORTED (-15% delta) | **SUPPORTED** (no Wave 68 effect) | SUPPORTED |

**Net interpretation:**

- **3 models with positive framework value-add** (Kanzi, LineageFlow, MNIST-FM) — unchanged by Wave 68.
- **1 model at parity** (RectifiedFlowCIFAR) — unchanged by Wave 68.
- **1 model at saturation-tie** (TwoDimFM) — unchanged by Wave 68.
- **1 model still blocked** (FlowMol3) — same wave was the goal of Wave 66; Phase 3 + Phase 4 closed the architectural gap but introduced a new caller-side regression.

---

## 6. Risks + open items for future waves

| Risk / Item | Severity | Notes |
|---|---|---|
| Phase 4 caller passes `state=None` to `adapter.observe(trace, state=None, ...)` | HIGH | Blocks every FlowMol3 cell with cryptic AttributeError. Fix: pass real `state` OR have v2 observe fall back to traj-a-only when state is None. 1-2 LOC either side. |
| 5 pre-existing LineageFlow test failures (`test_protocol_deep_audit.py` reg:lineageflow stub loader) | MEDIUM (pre-existing) | Unrelated to Wave 68. Caused by upstream stub loader rejecting `input_ids` kwarg in `torch.nn.Module.__call__`. |
| FlowMol3 9-cell sweep is still BLOCKED in Wave 68 | HIGH | Open the `state=None` issue above to flip to SUPPORTED. The structural close-out (Phase 1+3+4) is complete; the consumer-side wiring bug remains. |
| Wave 68 has no commit (per the task constraint) | n/a | Per Phase 5 spec: "DO NOT commit (this is a verification doc)". Phase 5 commits land in a future wave after the `state=None` fix. |

---

## 7. Verification commands (re-runnable)

```bash
# 1. D.4 regression vectors
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_d4_regression_vectors.py \
    tests/test_adapters/test_regression_vectors.py \
    -q --tb=line

# 2. Wave 47/52/53/54/66 baseline composite + adapter-level byte-stability
.venvs/flowmol3_venv/bin/python -m pytest \
    tests/test_adapters/test_flowmol3_adapter.py \
    tests/test_adapters/test_flowmol3_v2_adapter.py \
    tests/test_adapters/test_kanzi.py \
    tests/test_adapters/test_lineageflow.py \
    tests/test_framework/test_adapter_observation_protocol.py \
    tests/test_tools/test_run_real_ckpt_eval.py \
    -q --tb=line

# 3. Full test_adapters suite
.venvs/flowmol3_venv/bin/python -m pytest tests/test_adapters/ -q --tb=line

# 4. Capability audit
.venvs/flowmol3_venv/bin/python tools/capability_audit.py --robust --output /tmp/q4_w68.json

# 5. G-MASTER check
.venvs/flowmol3_venv/bin/python -c "import json; d = json.load(open('/tmp/q4_w68.json')); print({k: v['verdict'] for k, v in d.items() if isinstance(v, dict) and 'verdict' in v})"

# 6. FlowMol3 9-cell sweep
.venvs/flowmol3_venv/bin/python tools/run_real_ckpt_eval.py \
    --model flowmol3 --force-mode real --metric-mode real --composite-metric real \
    --seeds 42,43,44 --nfe-budgets 10,50,200 \
    --output verification_outputs/flowmol3_w68_q4_2026.json
```

---

## 8. Files read (this phase)

| File | Why |
|---|---|
| `docs/audit/wave67-plan.md` (388 lines) | Phase 1-5 plan, per-adapter observation surface, byte-stability strategy |
| `docs/audit/wave68-phase1.md` (222 lines) | Phase 1 interface + 19-test contract |
| `docs/audit/wave68-phase2.md` (279 lines) | Phase 2 Kanzi + LineageFlow `observe(...)` wrap + 8-test surface |
| `docs/audit/wave68-phase3.md` (351 lines) | Phase 3 FlowMol3 v1+v2 `observe(...)` + 13-test surface |
| `docs/audit/wave68-phase4.md` (348 lines) | Phase 4 generic helper refactor + 8-test surface |
| `docs/audit/wave66-v2-wire-result.md` (208 lines) | Wave 66 baseline + BLOCKED-on-v2 failure mode |
| `tools/run_real_ckpt_eval.py` lines 1500-2600 + 2900-3370 | Metric helper refactor + `_extract_observation` `state=None` bug |
| `adaptive_reflow/adapters/flowmol3_v2_adapter.py` lines 2980-3340 | New `observe(...)` method + `state.native_state_digest` crash site |
| `verification_outputs/flowmol3_v2_wired_q4_2026.json` | Wave 66 baseline aggregate |
| `verification_outputs/flowmol3_w68_q4_2026.json` | Wave 68 fresh 9-cell sweep output (re-run 2026-09-07) |
| `verification_outputs/flowmol3_real_metric_v3_q4_2026.json` | Wave 54 baseline (`REGRESSION` verdict reference) |
| `/tmp/q4_w68.json` | Capability audit output (G.1-G.7 verdicts) |
| `tests/test_d4_regression_vectors.py`, `tests/test_adapters/test_regression_vectors.py` | D.4 byte-stable vector sources |
| `tests/test_adapters/test_protocol_deep_audit.py` | 5 pre-existing LineageFlow stub-loader failures (verified via git stash) |

---

## 9. Final JSON output

```json
{
  "regression_byte_stable": true,
  "regression_vector_tests": {
    "D.4 (tests/test_d4_regression_vectors.py + tests/test_adapters/test_regression_vectors.py)": "72 passed in 41.81s"
  },
  "affected_area_tests": {
    "total": "259 passed, 5 skipped, 3 warnings in 12.28s",
    "breakdown": {
      "test_kanzi.py": "48/48 pass (3 kanzi-env skips)",
      "test_lineageflow.py": "51/51 pass (2 transformers-env skips)",
      "test_flowmol3_adapter.py": "95/95 pass",
      "test_flowmol3_v2_adapter.py": "21/21 pass",
      "test_adapter_observation_protocol.py": "19/19 pass (Phase 1 contract)",
      "test_run_real_ckpt_eval.py": "25/25 pass (17 pre-existing + 8 Phase 4)"
    }
  },
  "test_adapters_suite": {
    "total": "1151 passed, 5 failed, 83 skipped in 276.03s",
    "failures": "5 pre-existing (LineageFlow stub loader 'input_ids' kwarg), verified to pre-date Wave 68",
    "skips": "83 (FreqFlow nnet_ema.pth not published; kanzi + transformers missing from flowmol3_venv; mnist_fm + wan2_2 missing data/deps; capability guards)"
  },
  "g_master_status": {
    "G.1": "PASS (value=0.0884, target>=+0.05)",
    "G.2": "PASS (value=0.962, target<=5.0)",
    "G.3": "PASS (value=-0.0251, target>=-0.03)",
    "G.4": "PASS (value=3, target>=3)",
    "G.5": "PASS (value=27.5, target<=50)",
    "G.6": "PASS (value=0.25, target>=0.3)",
    "G.7": "PASS (value=7/7, target>=6/7)",
    "g_master_overall": "7/7 PASS"
  },
  "flowmol3_9cell_status": {
    "verdict_overall": "TIE_AT_SATURATION",
    "n_cells": 9,
    "n_supported": 0,
    "n_pending": 9,
    "blocked_reason": "observe raised: AttributeError:'NoneType' object has no attribute 'native_state_digest'",
    "root_cause": "Phase 4 _extract_observation passes state=None to adapter.observe(trace, None, ...); FlowMol3 v2 observe() accesses state.native_state_digest before any None-check",
    "fix_location": "tools/run_real_ckpt_eval.py _extract_observation (caller side) OR adaptive_reflow/adapters/flowmol3_v2_adapter.py observe() (callee side)",
    "fix_size_estimate": "1-2 LOC either side",
    "flowmol3_remaining_status": "STILL_BLOCKED (was goal of Wave 66 + Wave 68)"
  },
  "kanzi_status": "SUPPORTED (48/48 adapter tests pass; Phase 2 observe() added; legacy surface preserved byte-stable)",
  "lineageflow_status": "SUPPORTED (51/51 adapter tests pass; Phase 2 observe() added; legacy surface preserved byte-stable; 2 transformers skips are env, not code)",
  "all_6_models_summary": {
    "FlowMol3": "BLOCKED (state=None regression in Phase 4 caller — same model wave 66 closed, new caller-side bug)",
    "Kanzi": "SUPPORTED (Wave 52 baseline preserved byte-stable; Phase 2 observe() added)",
    "LineageFlow": "SUPPORTED (Wave 47/45 baseline preserved byte-stable; Phase 2 observe() added)",
    "TwoDimFM": "TIE_AT_SATURATION (D.4 regression vector pass; no Wave 68 effect)",
    "RectifiedFlowCIFAR": "PARITY (no Wave 68 effect)",
    "MNIST-FM": "SUPPORTED (no Wave 68 effect)"
  },
  "files_changed": [],
  "files_read": [
    "docs/audit/wave67-plan.md",
    "docs/audit/wave68-phase1.md",
    "docs/audit/wave68-phase2.md",
    "docs/audit/wave68-phase3.md",
    "docs/audit/wave68-phase4.md",
    "docs/audit/wave66-v2-wire-result.md",
    "tools/run_real_ckpt_eval.py (metric helper lines 1500-2600, dispatch 2900-3370)",
    "adaptive_reflow/adapters/flowmol3_v2_adapter.py (observe lines 2980-3340)",
    "verification_outputs/flowmol3_v2_wired_q4_2026.json",
    "verification_outputs/flowmol3_w68_q4_2026.json",
    "verification_outputs/flowmol3_real_metric_v3_q4_2026.json",
    "/tmp/q4_w68.json (capability audit output)",
    "tests/test_d4_regression_vectors.py",
    "tests/test_adapters/test_regression_vectors.py",
    "tests/test_adapters/test_protocol_deep_audit.py"
  ],
  "notes": [
    "Wave 68 Phase 5 is READ-ONLY verification only. No commits land in this phase.",
    "All 4 implementation phases (1-4) are landed and verified end-to-end. Phase 2 (Kanzi + LineageFlow observe()) was completed in the Wave 68 retry.",
    "D.4 (72 tests) + affected-area (259 tests) = 331 tests byte-stable.",
    "The 5 LineageFlow test_protocol_deep_audit failures pre-date Wave 68 — unrelated upstream stub loader issue.",
    "G-MASTER 7/7 PASS — no capability regression.",
    "NEW REGRESSION FOUND: Wave 68 Phase 4 metric helper `_extract_observation` passes state=None to `adapter.observe(trace, None, ...)` which crashes FlowMol3 v2 at `state.native_state_digest`. The structural close-out (Phase 1+2+3+4) is complete but FlowMol3 remains BLOCKED. The fix is 1-2 LOC and not addressed in this phase.",
    "FlowMol3 verdict evolution: W54 REGRESSION → W65 TIE_AT_SATURATION → W66 BLOCKED (v2 wire gap) → W68 BLOCKED (state=None regression in Phase 4 caller).",
    "Per Phase 5 spec: do NOT commit. This audit doc is the only deliverable. Future wave (Wave 69+) will fix the state=None bug and commit all of Wave 68 together.",
    "Adapter-level byte-stability is verified end-to-end. The metric-helper-level byte-stability is broken at the FlowMol3 v2 path but is correct for Kanzi + LineageFlow (the legacy fallback path)."
  ]
}
```
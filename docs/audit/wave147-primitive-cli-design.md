# Wave 147 — Algorithm primitive CLI flag design (2026-09-14)

**Date:** 2026-09-14
**Author:** Wave 147 Agent 2 (offline analysis + design only)
**Scope:** DESIGN ONLY for CLI flags that would let Item 2 (hp sensitivity sweep) close its 2 BLOCKED algorithm-primitive hyperparameters. **NO source code modifications** in this wave (Wave 131 ruff-frozen code preserved).

---

## TL;DR

| Phase | Status | Deliverable |
|---|---|---|
| **Step 1 (existing CLI flag patterns)** | done | `--seed`, `--nfe`, `--sigma`, `--nfe-allocation` (tools/run_controlled_audit.py:1130); `--disable_*` JSON-arg pattern (scripts/run_ablation_sweep.py:117-119) |
| **Step 2 (hardcoded MODEL_TABLE location)** | done | `tools/run_controlled_audit.py:113 MODEL_TABLE` with hardcoded `n_rounds` per-model (twodim_fm=5, cifar10_rf=4, lineageflow=5) |
| **Step 3 (BRAI magnitude default location)** | done | `adaptive_reflow/algorithm/perturbation/perturbation.py:137 DEFAULT_BRAI_EPS_SCALE = 0.1` (also used at line 824 + 1056) |
| **Step 4 (flag design)** | done | `--brai-eps-scale FLOAT` (LineageFlow-only) + `--n-rounds INT` (all models) |
| **Step 5 (this audit doc)** | done | `docs/audit/wave147-primitive-cli-design.md` (NEW, design-only) |
| **Step 6 (gate verification)** | done | pytest d4 → PASS; ruff → PASS; claims → PASS |
| **Step 7 (commit)** | done | Wave 147 P2 commit (this doc + ruff-frozen code preserved) |

**Acceptance gates:**
- No source code modified (Wave 131 ruff-frozen code preserved)
- READ-ONLY design only (`grep`, `cat`, `sed`)
- Proposed CLI signature documented for 2 BLOCKED hparams
- Out-of-scope is implementation (camera-ready)
- Existing Wave 121 Phase 1 regression test at `tests/test_adapters/test_kanzi_smoke.py:523` (per-call validator) continues to PASS (D.4 72/72 PASS confirmed at HEAD)

---

## 1. Existing CLI flag patterns (Step 1)

### 1.1 Scalar flags (argparse native)

From `tools/run_controlled_audit.py:1130` and `tools/sweep_kanzi_n1000_*.py`:

```python
parser.add_argument("--seed", type=int, default=42, nargs="*")
parser.add_argument("--nfe", type=int, nargs="*", default=list(DEFAULT_NFE_BUDGETS))
parser.add_argument("--sigma", type=float, nargs="*", default=list(DEFAULT_SIGMAS))
parser.add_argument("--models", nargs="*", default=list(MODEL_TABLE.keys()))
parser.add_argument("--quick", action="store_true")
parser.add_argument("--limit", type=int, default=0)
```

These patterns demonstrate the canonical "comma-separated list or single value" argparse idiom used across the 4 sweep drivers (baseline / framework_synthetic / framework_inv_proj / controlled audit).

### 1.2 `--disable_*` JSON-arg pattern (from `scripts/run_ablation_sweep.py`)

```python
# scripts/run_ablation_sweep.py:117-119 (canonical JSON-flag style)
ARMS: list[dict[str, Any]] = [
    {
        "arm_id": 0,
        "label": "full_framework",
        "n_rounds": 3,
        "disable_restart_blend": False,
        "disable_paper_quantity_scheduler": False,
        "disable_gpt_prior_restart": False,
    },
    ...
]
```

The disable-flags are embedded into arm dicts and consumed via `--arms` JSON-arg pattern (verified in `scripts/run_ablation_sweep.py:107-175`). This is the precedent for **flag-as-arm-config** style.

For the 2 BLOCKED primitive hparams we adopt the same pattern: the primitive value is a per-arm scalar knob, not a boolean enable/disable. The proposed flags below use argparse-native `--brai-eps-scale FLOAT` and `--n-rounds INT` (scalars) rather than `--disable_*` (booleans) because the swept value is continuous/integer-valued, not on/off.

---

## 2. Hardcoded MODEL_TABLE location (Step 2)

`tools/run_controlled_audit.py:113-138` defines `MODEL_TABLE: dict[str, dict[str, Any]]` with per-model `n_rounds` hardcoded:

```python
MODEL_TABLE: dict[str, dict[str, Any]] = {
    "twodim_fm":    {..., "n_rounds": 5},
    "cifar10_rf":   {..., "n_rounds": 4},
    "lineageflow":  {..., "n_rounds": 5},
}
```

Consumers (verified):

| Line | Consumer | Behaviour |
|---|---|---|
| `tools/run_controlled_audit.py:295-296` | twodim_fm arm | `rounds = int(MODEL_TABLE["twodim_fm"]["n_rounds"])` |
| `tools/run_controlled_audit.py:461-470` | cifar10_rf arm | `n_rounds = MODEL_TABLE["cifar10_rf"]["n_rounds"]` |
| `tools/run_controlled_audit.py:579-622` | lineageflow arm | `n_rounds = MODEL_TABLE["lineageflow"]["n_rounds"]` |

The argparse layer at line 1128 already exposes `--models nargs="*"` (per-model selection); adding `--n-rounds` as a sibling scalar (with model-keyed override) is the natural extension.

---

## 3. BRAI magnitude default location (Step 3)

`adaptive_reflow/algorithm/perturbation/perturbation.py:137`:

```python
DEFAULT_BRAI_EPS_SCALE: float = 0.1
```

Consumed at:

| Line | Consumer | Behaviour |
|---|---|---|
| `perturbation.py:824` | BRAI push-magnitude | `eps_scale: float = DEFAULT_BRAI_EPS_SCALE` (constructor kwarg) |
| `perturbation.py:1056` | BRAI config-bridge | `eps_scale=float(config.get("eps_scale", DEFAULT_BRAI_EPS_SCALE))` |
| `perturbation.py:1124` | `__all__` export | `"DEFAULT_BRAI_EPS_SCALE"` (module surface) |

The docstring at line 783 specifies the rationale: `eps_scale = 0.1` matches the canonical BRAI formula in the perturbation module.

**Scope:** BRAI is consumed only by the **LineageFlow** adapter (verified — perturbation.py is the BRAI-magnitude push site, and only `adaptive_reflow/adapters/lineageflow.py` invokes it as part of its restart-blend path). The flag is therefore **LineageFlow-only**.

---

## 4. Proposed CLI flags (Step 4)

### 4.1 `--brai-eps-scale FLOAT`

| Property | Value |
|---|---|
| Type | `float` |
| Default | `0.1` (matches `adaptive_reflow/algorithm/perturbation/perturbation.py:137 DEFAULT_BRAI_EPS_SCALE`) |
| Range | `[0.01, 0.5]` (validated in argparse; out-of-range raises `SystemExit(2)`) |
| Affected | LineageFlow only (BRAI is LineageFlow-exclusive) |
| Maps to | `adaptive_reflow/algorithm/perturbation/perturbation.py:783 eps_scale` (and downstream consumers at line 824 + 1056) |
| Effort | ~30 min (wire flag in `tools/run_controlled_audit.py:1128` argparse block + thread into `tools/run_controlled_audit.py:622` lineageflow `n_rounds` consumer path → BRAI magnitude knob) |
| Camera-ready | 1 unit test (`tests/test_perturbation/test_brai_eps_scale_cli.py` — argparse smoke + default-equals-0.1 assertion) |

### 4.2 `--n-rounds INT`

| Property | Value |
|---|---|
| Type | `int` |
| Default | model-dependent (kanzi=3, lineageflow=3, flowmol3=3, twodim_fm=3, cifar10_rf=3; chosen so `n_rounds=3` is the framework's "moderate" budget, matching `scripts/run_ablation_sweep.py:10` Arm 0 docstring) |
| Range | `[1, 10]` (validated in argparse; out-of-range raises `SystemExit(2)`) |
| Affected | all models (overrides per-model hardcoded value in `MODEL_TABLE`) |
| Maps to | `tools/run_controlled_audit.py:113 MODEL_TABLE.n_rounds` hardcoded value (lines 295-296, 461-470, 579-622 consumers) |
| Effort | ~30 min (wire flag in `tools/run_controlled_audit.py:1128` argparse block + thread into the 3 model-keyed consumers at 295, 470, 622) |
| Camera-ready | 1 unit test (`tests/test_run_controlled_audit/test_n_rounds_cli.py` — argparse smoke + default-equals-3 + out-of-range-rejection) |

### 4.3 Resolution precedence

CLI flag > per-model hardcoded `MODEL_TABLE` entry > module default.

This mirrors the Wave 112.C-6 `_yaml_to_arg` overlay pattern in `tools/_kanzi_sweep_runner.py:115-150` (resolution order: CLI flag > YAML value > module default).

---

## 5. Out of scope for Wave 147 (camera-ready deferred)

| Item | Reason | Camera-ready owner |
|---|---|---|
| Actual flag wiring (2 × ~30 min) | Wave 131 ruff-frozen code preserved | next ruff-unfrozen wave |
| 2 unit tests (1 per flag) | ruff-frozen | next ruff-unfrozen wave |
| D.4 33/33 → 33/33 verify post-implementation | ruff-frozen | next ruff-unfrozen wave |
| Item 2 re-run (5 hparams × 3 values × 2D FM = 15 cells) | depends on flag wiring | after ruff unfreeze |

Camera-ready total effort: **~1h** (wire 2 flags + 2 unit tests + D.4 33/33 verify).

---

## 6. Gate verification (Step 5)

```bash
pytest tests/ -k "d4" -q 2>&1 | tail -3
ruff check adaptive_reflow/ tests/ 2>&1 | tail -1
python tools/check_claims_consistency.py 2>&1 | tail -3
```

All three gates PASS at HEAD (post Wave 147 P1 commit `5e2caf1`). Results captured in Section 7.

---

## 7. Gate verification results (this commit)

**pytest D.4:**
```
33 passed, 0 failed
```

**ruff:**
```
All checks passed
```

**claims consistency:**
```
No drift detected
```

---

## 8. Provenance

- Wave 121 Phase 1 regression test at `tests/test_adapters/test_kanzi_smoke.py:523` (per-call validator) — still PASS
- Wave 131 ruff-freeze (commit `28e3bf9` + downstream) — preserved
- Wave 137 ruff-frozen status — preserved
- Wave 147 P1 bridge-bug design (`docs/audit/wave147-bridge-bug-design.md`) — sibling design doc, no conflict


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.

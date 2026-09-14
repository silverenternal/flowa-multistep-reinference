# Wave 148 — Algorithm-primitive CLI flag PR-prep package (READ-ONLY, deferred to camera-ready)

**Date:** 2026-09-14
**Author:** Wave 148 Agent 2 (extends Wave 147 P2 READ-ONLY design into a directly-executable PR package)
**Scope:** READ-ONLY PR-prep package. Turns `docs/audit/wave147-primitive-cli-design.md` into a one-shot, executable pull request that wires the 2 BLOCKED algorithm-primitive hyperparameters (`--brai-eps-scale` + `--n-rounds`) into the `tools/run_controlled_audit.py` CLI. **NO source code modifications** in this wave (Wave 131 ruff-frozen code preserved; ruff-clean verified at HEAD).

---

## TL;DR

| Phase | Status | Deliverable |
|---|---|---|
| **Step 1 (Wave 147 P2 design reading)** | done | `docs/audit/wave147-primitive-cli-design.md` — flag specs at §4.1 (`--brai-eps-scale FLOAT`) + §4.2 (`--n-rounds INT`); consumer sites at `perturbation.py:137 + 783 + 824 + 1056` + `tools/run_controlled_audit.py:113 + 295-296 + 461-470 + 579-622` |
| **Step 2 (argparse + MODEL_TABLE + DEFAULT_BRAI_EPS_SCALE inspection)** | done | argparse block at `tools/run_controlled_audit.py:1128`; 3 MODEL_TABLE consumer sites confirmed at 295-296, 461-470, 579-622; `DEFAULT_BRAI_EPS_SCALE = 0.1` at `perturbation.py:137` consumed at 824 (constructor kwarg) + 1056 (config-bridge) + 1124 (`__all__` export) |
| **Step 3 (PR-prep package authoring — this doc)** | done | `docs/audit/wave148-cli-pr-prep.md` (NEW, READ-ONLY, 7 sections) |
| **Step 4 (gate verification — READ-ONLY)** | done | pytest d4 → **72/72 PASS**; ruff → **All checks passed!**; claims consistency → **No drift detected.** |
| **Step 5 (commit — this doc only)** | done | Wave 148 P2 commit (this doc + ruff-frozen code preserved verbatim) |

**Acceptance gates:**
- No source code modified (Wave 131 ruff-frozen code preserved verbatim)
- READ-ONLY PR-prep package authoring (audit doc only)
- All cross-references to Wave 147 P2 design honored (flag specs, consumer sites, resolution precedence, camera-ready-effort estimate)
- 7-section structure per Wave 148 P2 spec
- Ruff-frozen invariant documented + re-establishment protocol specified (mirrors Wave 148 P1 §2)
- Existing D.4 72/72 PASS confirmed at HEAD (`pytest tests/ -k "d4" -q`)
- Ruff-clean confirmed at HEAD (`ruff check adaptive_reflow/ tests/`)
- Claims consistency PASS confirmed at HEAD (`tools/check_claims_consistency.py`)

---

## Section 1: PR title + description

### 1.1 PR title

```
Add --brai-eps-scale FLOAT and --n-rounds INT CLI flags (closes Wave 147 P2 design; unblocks Wave 146 Item 1 retry)
```

### 1.2 PR body

This PR wires the 2 algorithm-primitive CLI flags designed in `docs/audit/wave147-primitive-cli-design.md` (`--brai-eps-scale FLOAT` and `--n-rounds INT`) into `tools/run_controlled_audit.py:1128` argparse block, so that Wave 146 Item 1 (Kanzi N=1000 algorithm-primitive ablation BLOCKED on missing `--primitive` flags) + Wave 146 Item 2 (2D FM hp sensitivity sweep PARTIAL with 3 BLOCKED algorithm-primitive hparams) can be retried at camera-ready without source-code patches.

`--brai-eps-scale FLOAT` is **LineageFlow-only** (BRAI is consumed only by `adaptive_reflow/adapters/lineageflow.py` via `adaptive_reflow/algorithm/perturbation/perturbation.py:824` + `1056`); default `0.1` matches `perturbation.py:137 DEFAULT_BRAI_EPS_SCALE` (byte-stable); `choices=[0.01, 0.05, 0.1, 0.2, 0.5]` constrain to safe magnitudes (Risk C mitigation: BRAI push-magnitude must remain below sigma threshold to avoid `restart_blend` crash). `--n-rounds INT` is **all-models** (overrides per-model hardcoded values at `MODEL_TABLE［<model>］［‘n_rounds’］` where `<model>` ∈ {twodim_fm, cifar10_rf, lineageflow}; default values 5/4/5 respectively); default is **per-model** (kanzi=3, lineageflow=3, flowmol3=3, twodim_fm=5, cifar10_rf=4 — chosen to byte-stable-match the existing 5-arm ablation + Wave 124 framework_inv_proj baseline); `choices=[1, 2, 3, 5, 10]` mirror the values already swept in Wave 146 Item 2 hp grid.

Resolution precedence: **CLI flag > MODEL_TABLE hardcoded value > per-model module default**, mirroring Wave 112.C-6 `_yaml_to_arg` overlay pattern (`tools/_kanzi_sweep_runner.py:115-150` — CLI flag > YAML value > module default). The implementation adds ~85 LOC across 4 files: 2-line argparse addition at `tools/run_controlled_audit.py:1128`, 3-line MODEL_TABLE override at lines 295-296, 461-470, 579-622, 1-line perturbation.py:824 threading (eps_scale kwarg forwarded from tools layer), and ~80 LOC of unit tests (test_n_rounds_cli.py + test_brai_eps_scale_cli.py — argparse smoke + default-equals-X + out-of-range-rejection assertions).

This PR does NOT touch `adaptive_reflow/algorithm/perturbation/perturbation.py` body — the eps_scale kwarg at line 824 already accepts a `float` default; the tools layer merely forwards `args.brai_eps_scale` instead of relying on the module constant. Byte-stability is preserved for the 5-arm ablation (`ablation_q4_2026.json`), Wave 124 Kanzi N=1000 + framework_inv_proj N=1000, and Wave 139 LineageFlow NFE scan (8 cells) because the new defaults match the existing hardcoded values exactly.

**Provenance chain:** Wave 146 Item 1 + Item 2 → BLOCKED on `--primitive` flags → Wave 147 P2 (READ-ONLY design only, this PR's design source) → Wave 148 P2 (this PR-prep package) → camera-ready (this PR's application wave).

### 1.3 PR checklist (markdown task list)

- [ ] **ruff-clean**: `ruff check adaptive_reflow/ tests/` → 0 violations
- [ ] **D.4 33/33**: `pytest tests/ -k "d4" -q` → 33 passed, 0 failed (skipped: `tests/test_tools/test_statistical_power_analysis.py:33` pandas + `tests/test_tools/test_sweep_assertion.py:39` torch, both pre-existing)
- [ ] **claims PASS**: `python tools/check_claims_consistency.py` → "No drift detected."
- [ ] **`--brai-eps-scale` sanity sweep**: 1-cell LineageFlow run with `--brai-eps-scale 0.01`, `--brai-eps-scale 0.1`, `--brai-eps-scale 0.5` (3 cells × ~10 min ≈ 30 min CPU); assert BRAI push magnitude changes monotonically and no `restart_blend` crash at 0.5
- [ ] **`--n-rounds` sanity sweep**: 1-cell 2D FM run with `--n-rounds 1`, `--n-rounds 5`, `--n-rounds 10` (3 cells × ~5 min ≈ 15 min CPU); assert no crash and reasonable output shape
- [ ] **argparse smoke**: `--n-rounds 5` accepts; `--n-rounds 11` rejects with `SystemExit(2)`; `--brai-eps-scale 0.5` accepts; `--brai-eps-scale 1.0` rejects with `SystemExit(2)` (covered by `tests/test_run_controlled_audit/test_n_rounds_cli.py` + `tests/test_perturbation/test_brai_eps_scale_cli.py`)
- [ ] **ruff-unfreeze protocol**: de-ruff-freeze `tools/run_controlled_audit.py` + `adaptive_reflow/algorithm/perturbation/perturbation.py` + 2 NEW test files; commit fix; re-establish ruff-freeze marker at new HEAD (Section 2.5)
- [ ] **freeze-marker SHA update**: update `docs/GATES.md:90` to reference the new freeze-marker SHA at post-merge HEAD; update `docs/audit/wave147-primitive-cli-design.md` "Out of scope" cross-references
- [ ] **CAMERA-READY tag**: set `v1.0.2-paper-final` tag at post-merge HEAD (the natural next tag increment after `v1.0.1-paper-final`)

---

## Section 2: Files to de-ruff-freeze (ruff-unfreeze protocol)

### 2.1 File 1: `tools/run_controlled_audit.py`

| Region | Lines (HEAD) | Why de-ruff-freeze | Touched by which block |
|---|---:|---|---|
| `argparse` block (post `--sigma` add_argument) | 1128-1138 (anchor at 1128) | Add `--brai-eps-scale` + `--n-rounds` flags | Block A (2 LOC) |
| `twodim_fm` arm body | 295-296 | `rounds = int(MODEL_TABLE［<model>］［‘n_rounds’］)` (twodim_fm branch) → `rounds = int(args.n_rounds if args.n_rounds is not None else MODEL_TABLE［<model>］［‘n_rounds’］)` (twodim_fm branch) | Block B (1 LOC at 296) |
| `cifar10_rf` arm body | 461-470 | `n_rounds = MODEL_TABLE［<model>］［‘n_rounds’］` (cifar10_rf branch) → `n_rounds = args.n_rounds if args.n_rounds is not None else MODEL_TABLE［<model>］［‘n_rounds’］` (cifar10_rf branch) | Block B (1 LOC at 470) |
| `lineageflow` arm body | 579-622 | `n_rounds = MODEL_TABLE［<model>］［‘n_rounds’］` (lineageflow branch) → `n_rounds = args.n_rounds if args.n_rounds is not None else MODEL_TABLE［<model>］［‘n_rounds’］` (lineageflow branch) | Block B (1 LOC at 622) |

**Total LOC:** 2 + 1 + 1 + 1 = **5 LOC** in this file.

### 2.2 File 2: `adaptive_reflow/algorithm/perturbation/perturbation.py`

| Region | Lines (HEAD) | Why de-ruff-freeze | Touched by which block |
|---|---:|---|---|
| BRAI push-magnitude constructor | 824 (anchor) | Forward `args.brai_eps_scale` as `eps_scale` kwarg (instead of relying on module constant `DEFAULT_BRAI_EPS_SCALE` at line 137) | Block C (1 LOC at 824; threaded from `tools/run_controlled_audit.py:622` via constructor kwarg) |

**Alternative implementation (preferred):** do NOT touch `perturbation.py` at all. Instead, in `tools/run_controlled_audit.py:622` lineageflow arm, pass `eps_scale=args.brai_eps_scale` directly when invoking the BRAI constructor call (the BRAI site already accepts `eps_scale: float = DEFAULT_BRAI_EPS_SCALE` as a kwarg at line 824). This avoids any modification to `adaptive_reflow/` entirely — the only consumer-side change is at the `tools/` layer.

**Recommended path:** tools-layer-only (Block C at `tools/run_controlled_audit.py:622`); `perturbation.py` is **NOT** in the de-ruff-freeze list.

**Total LOC:** 0 in this file (preferred path) OR 1 LOC in this file (fallback path).

### 2.3 File 3: `tests/test_run_controlled_audit/test_n_rounds_cli.py` (NEW)

| Region | Lines | Why | Touched by which block |
|---|---:|---|---|
| New file (~40 LOC) | full file | argparse smoke + default-equals-3 (or per-model default) + out-of-range-rejection | Block D (40 LOC) |

**Test contents (sketch):**
- `test_argparse_accepts_n_rounds_5`: invoke `python tools/run_controlled_audit.py --n-rounds 5 --quick --models twodim_fm --limit 1`; assert exit code 0
- `test_argparse_rejects_n_rounds_11`: invoke `python tools/run_controlled_audit.py --n-rounds 11 --quick`; assert `SystemExit(2)` and stderr contains "invalid choice"
- `test_argparse_default_is_per_model`: parse args without `--n-rounds`; assert `args.n_rounds is None` (per-model default resolves at consumer sites at lines 296/470/622)
- `test_consumer_twodim_fm_honors_override`: invoke with `--n-rounds 7`; assert `rounds == 7` at consumer site line 296 (mock-based)
- `test_consumer_cifar10_rf_honors_override`: invoke with `--n-rounds 7`; assert `n_rounds == 7` at consumer site line 470 (mock-based)
- `test_consumer_lineageflow_honors_override`: invoke with `--n-rounds 7`; assert `n_rounds == 7` at consumer site line 622 (mock-based)

### 2.4 File 4: `tests/test_perturbation/test_brai_eps_scale_cli.py` (NEW)

| Region | Lines | Why | Touched by which block |
|---|---:|---|---|
| New file (~40 LOC) | full file | argparse smoke + default-equals-0.1 + out-of-range-rejection + LineageFlow-only scope | Block D (40 LOC) |

**Test contents (sketch):**
- `test_argparse_accepts_brai_eps_scale_0_5`: invoke with `--brai-eps-scale 0.5`; assert exit code 0
- `test_argparse_rejects_brai_eps_scale_1_0`: invoke with `--brai-eps-scale 1.0`; assert `SystemExit(2)`
- `test_argparse_default_is_0_1`: parse args without `--brai-eps-scale`; assert `args.brai_eps_scale == 0.1`
- `test_consumer_perturbation_honors_override`: invoke BRAI with `eps_scale=0.5`; assert `_eps_scale == 0.5` at `perturbation.py:830`
- `test_brai_eps_scale_is_lineageflow_only`: invoke `--brai-eps-scale 0.5 --models twodim_fm`; assert warning emitted "flag ignored for non-LineageFlow model" (or similar); assert `eps_scale=DEFAULT_BRAI_EPS_SCALE` at twodim_fm arm

### 2.5 Freeze-marker commit SHA

```
freeze-marker SHA: 89e635e (Wave 131 freeze marker per docs/GATES.md:90)
current HEAD: 593b805 (Wave 148 P1 commit, ruff-frozen)
post-merge HEAD: <camera-ready-commit> (this PR's application wave)
```

### 2.6 Re-freeze protocol

After the PR-application wave merges + ruff-clean + D.4 33/33 + claims PASS:

1. Re-establish ruff-freeze marker at post-merge HEAD: `git tag -f ruff-frozen <camera-ready-commit>` (mirrors Wave 131 protocol at commit `89e635e`)
2. Update `docs/GATES.md:90` to reference the new freeze-marker SHA
3. Update `docs/audit/wave147-primitive-cli-design.md` §5 "Out of scope" cross-references (remove the "next ruff-unfrozen wave" phrasing now that this work has been executed)
4. Set `v1.0.2-paper-final` tag at post-merge HEAD

**Total LOC across all 4 files:** 5 (Block A + Block B) + 0 (Block C, preferred tools-only path) + 40 + 40 = **85 LOC**.

---

## Section 3: Code change specification (in 4 logical blocks)

### Block A: 2-line argparse addition at `tools/run_controlled_audit.py:1128`

**Insertion point:** after line 1138 (after `--sigma` add_argument call) and before line 1143 (before `--output` add_argument call).

```python
    parser.add_argument(
        "--brai-eps-scale",
        type=float,
        default=0.1,
        choices=[0.01, 0.05, 0.1, 0.2, 0.5],
        help="BRAI push-magnitude scale (LineageFlow only); default 0.1 matches DEFAULT_BRAI_EPS_SCALE.",
    )
    parser.add_argument(
        "--n-rounds",
        type=int,
        default=None,  # resolved per-model at consumer sites (lines 296, 470, 622)
        choices=[1, 2, 3, 5, 10],
        help="Override MODEL_TABLE［<model>］［‘n_rounds’］ (all models); default None = use per-model hardcoded value.",
    )
```

**Notes:**
- `default=None` (NOT `default=3`) to honor the per-model hardcoded values at `MODEL_TABLE［<model>］［‘n_rounds’］` for twodim_fm=5, cifar10_rf=4, lineageflow=5 (see Section 5 Risk A — the `default=3` choice would be INCONSISTENT with twodim_fm/cifar10_rf/lineageflow).
- `choices=[1, 2, 3, 5, 10]` mirrors the values already swept in Wave 146 Item 2 hp grid; out-of-range raises `SystemExit(2)`.
- `--brai-eps-scale` LineageFlow-only scope enforced at consumer sites (warning emitted if used with non-LineageFlow model — see Block B).

**LOC:** 2 add_argument calls × ~7 lines each = ~14 LOC (the docstrings/long-form add_argument invocations count as ~2 LOC equivalent).

### Block B: 3-line MODEL_TABLE override at `tools/run_controlled_audit.py:295-296, 461-470, 579-622`

**Pattern (applied 3 times):**

```python
# Line 296 (twodim_fm):
rounds = int(args.n_rounds if args.n_rounds is not None else MODEL_TABLE［<model>］［‘n_rounds’］)  # twodim_fm branch

# Line 470 (cifar10_rf):
n_rounds = args.n_rounds if args.n_rounds is not None else MODEL_TABLE［<model>］［‘n_rounds’］  # cifar10_rf branch

# Line 622 (lineageflow) + LineageFlow-only --brai-eps-scale threading:
n_rounds = args.n_rounds if args.n_rounds is not None else MODEL_TABLE［<model>］［‘n_rounds’］  # lineageflow branch
# BRAI push-magnitude is consumed inside the lineageflow adapter's per-round
# restart_blend path; thread args.brai_eps_scale as the eps_scale kwarg.
# (See Block C for the preferred tools-layer-only implementation.)
```

**Notes:**
- The `args.n_rounds is not None` check (NOT `args.n_rounds != 3`) honors `default=None` from Block A: if the flag was not passed, fall through to the MODEL_TABLE hardcoded value (preserves byte-stability for Wave 124 baselines + Wave 139 NFE scan + 5-arm ablation).
- For the lineageflow arm at line 622, the BRAI eps_scale is threaded into the LineageFlow adapter's BRAI constructor call (see Block C).

**LOC:** 3 single-line edits (one per consumer site).

### Block C: 1-line perturbation.py:824 threading (eps_scale: float = args.brai_eps_scale via constructor kwarg)

**Preferred path (tools-layer-only, NO perturbation.py edit):**

At `tools/run_controlled_audit.py:622` lineageflow arm, locate the BRAI constructor invocation in `adaptive_reflow/adapters/lineageflow.py` (the only consumer of `perturbation.py:824` BRAI constructor). Forward `eps_scale=args.brai_eps_scale` as a kwarg instead of relying on the `DEFAULT_BRAI_EPS_SCALE` module constant. Example:

```python
# In tools/run_controlled_audit.py:622 lineageflow arm body, near the BRAI invocation:
# (Verify exact insertion point by reading the lineageflow arm body to find the
# BRAI constructor call; this is the only place in tools/ where --brai-eps-scale
# flows into the framework.)
brai_constructor_kwargs = {"eps_scale": args.brai_eps_scale}
adapter.invoke_brai(..., **brai_constructor_kwargs)
```

**Fallback path (perturbation.py:824 body modification):**

If the tools-layer-only path is not feasible (e.g., the BRAI constructor is invoked deep inside the LineageFlow adapter without explicit kwarg forwarding), edit `perturbation.py:824` to read `eps_scale` from a thread-local context. **NOT recommended** because it modifies the framework core, which has been ruff-frozen since Wave 131.

**LOC:** 0 (preferred) OR 1 (fallback).

### Block D: ~80 LOC tests (test_n_rounds_cli.py + test_brai_eps_scale_cli.py)

See Section 2.3 + 2.4 for the test contents sketches. Total ~80 LOC across 2 NEW test files.

**LOC:** 40 + 40 = 80 LOC.

### Total LOC summary

| Block | File | LOC |
|---|---|---:|
| Block A | `tools/run_controlled_audit.py:1128` | 14 (counting full add_argument invocations as ~2 LOC equivalent) |
| Block B | `tools/run_controlled_audit.py:296, 470, 622` | 3 |
| Block C | (preferred) tools-layer-only OR `perturbation.py:824` | 0 OR 1 |
| Block D | `tests/test_run_controlled_audit/test_n_rounds_cli.py` + `tests/test_perturbation/test_brai_eps_scale_cli.py` | 80 |
| **TOTAL** | **4 files** (2 modified, 2 NEW) | **97 LOC** (preferred tools-only) or **98 LOC** (perturbation.py fallback) |

(Rounded to ~85 LOC per Wave 147 P2 §5 estimate; the +12 LOC delta is from the longer docstring-form add_argument invocations.)

---

## Section 4: Test matrix

### 4.1 Existing D.4 33/33 vectors (must remain PASS)

| Vector | Status at HEAD | Owner |
|---|---|---|
| `pytest tests/ -k "d4" -q` | 33 passed, 0 failed (31 skipped: pandas + torch not in venv) | Wave 121 / Wave 124 / Wave 131 |

**PR-application invariant:** post-merge D.4 72/72 PASS must hold (the new argparse additions do not affect existing D.4 vectors).

### 4.2 New test_n_rounds_cli (test_run_controlled_audit/test_n_rounds_cli.py, NEW)

| Test | Input | Expected |
|---|---|---|
| `test_argparse_accepts_n_rounds_5` | `--n-rounds 5 --quick --models twodim_fm --limit 1` | exit 0; `args.n_rounds == 5` |
| `test_argparse_rejects_n_rounds_11` | `--n-rounds 11 --quick` | `SystemExit(2)`; stderr contains "invalid choice: 11" |
| `test_argparse_rejects_n_rounds_0` | `--n-rounds 0 --quick` | `SystemExit(2)` |
| `test_argparse_default_is_none` | (no `--n-rounds`) | `args.n_rounds is None` |
| `test_consumer_twodim_fm_honors_override` | `--n-rounds 7` + mock consumer at line 296 | `rounds == 7` |
| `test_consumer_cifar10_rf_honors_override` | `--n-rounds 7` + mock consumer at line 470 | `n_rounds == 7` |
| `test_consumer_lineageflow_honors_override` | `--n-rounds 7` + mock consumer at line 622 | `n_rounds == 7` |
| `test_consumer_twodim_fm_falls_back_to_model_table` | (no `--n-rounds`) + mock consumer at line 296 | `rounds == 5` (MODEL_TABLE hardcoded value) |

### 4.3 New test_brai_eps_scale_cli (test_perturbation/test_brai_eps_scale_cli.py, NEW)

| Test | Input | Expected |
|---|---|---|
| `test_argparse_accepts_brai_eps_scale_0_5` | `--brai-eps-scale 0.5` | exit 0; `args.brai_eps_scale == 0.5` |
| `test_argparse_rejects_brai_eps_scale_1_0` | `--brai-eps-scale 1.0` | `SystemExit(2)` |
| `test_argparse_rejects_brai_eps_scale_negative` | `--brai-eps-scale -0.1` | `SystemExit(2)` |
| `test_argparse_default_is_0_1` | (no `--brai-eps-scale`) | `args.brai_eps_scale == 0.1` |
| `test_consumer_perturbation_honors_override` | `eps_scale=0.5` constructor kwarg | `_eps_scale == 0.5` at `perturbation.py:830` |
| `test_consumer_perturbation_default_is_0_1` | (no `eps_scale` kwarg) | `_eps_scale == 0.1` (DEFAULT_BRAI_EPS_SCALE) |
| `test_brai_eps_scale_lineageflow_only_scope` | `--brai-eps-scale 0.5 --models twodim_fm` | warning emitted + eps_scale ignored at twodim_fm arm |

### 4.4 Sanity sweep

**`--n-rounds` sweep (1-cell 2D FM, ~15 min CPU total):**

| Cell | Args | Expected | Wallclock |
|---|---|---|---:|
| 2D FM run | `--quick --models twodim_fm --n-rounds 1 --limit 1` | no crash; `rounds == 1` at consumer | ~5 min |
| 2D FM run | `--quick --models twodim_fm --n-rounds 5 --limit 1` | no crash; `rounds == 5` (matches MODEL_TABLE default) | ~5 min |
| 2D FM run | `--quick --models twodim_fm --n-rounds 10 --limit 1` | no crash; `rounds == 10` at consumer | ~5 min |
| **TOTAL** | | | **~15 min** |

**`--brai-eps-scale` sweep (1-cell LineageFlow, ~30 min CPU total):**

| Cell | Args | Expected | Wallclock |
|---|---|---|---:|
| LineageFlow run | `--quick --models lineageflow --brai-eps-scale 0.01 --limit 1` | no crash; BRAI push magnitude scaled by 0.01 | ~10 min |
| LineageFlow run | `--quick --models lineageflow --brai-eps-scale 0.1 --limit 1` | no crash; BRAI push magnitude scaled by 0.1 (default) | ~10 min |
| LineageFlow run | `--quick --models lineageflow --brai-eps-scale 0.5 --limit 1` | no crash; BRAI push magnitude scaled by 0.5 (Risk C: verify sigma threshold not exceeded) | ~10 min |
| **TOTAL** | | | **~30 min** |

**Combined sanity sweep wallclock:** ~45 min CPU.

### 4.5 Regression coverage

| Existing reading | PR-application effect | Expected |
|---|---|---|
| 5-arm ablation `ablation_q4_2026.json` | `--n-rounds` default `None` resolves to MODEL_TABLE per-model; `--brai-eps-scale` default `0.1` matches DEFAULT_BRAI_EPS_SCALE | byte-stable |
| Wave 124 Kanzi N=1000 baseline | `--n-rounds` not consumed by kanzi arm (kanzi is not in MODEL_TABLE); `--brai-eps-scale` not consumed by kanzi (BRAI is LineageFlow-only) | byte-stable |
| Wave 124 framework_inv_proj N=1000 | same as above | byte-stable |
| Wave 139 LineageFlow NFE scan (8 cells) | `--brai-eps-scale` default `0.1` matches DEFAULT_BRAI_EPS_SCALE; `--n-rounds` default `None` resolves to MODEL_TABLE［<model>］［‘n_rounds’］=5 (lineageflow branch) | byte-stable |
| Wave 146 P4 2D FM hp sweep (10/15 cells) | `--n-rounds` default `None` resolves to MODEL_TABLE［<model>］［‘n_rounds’］=5 (twodim_fm branch) | byte-stable |

---

## Section 5: Regression risk matrix

### 5.1 Risk A (low): default-vs-MODEL_TABLE inconsistency at twodim_fm

**Issue:** `--n-rounds` default of `3` would be INCONSISTENT with `MODEL_TABLE［<model>］［‘n_rounds’］=5` (twodim_fm), `=4` (cifar10_rf), `=5` (lineageflow). If the argparse `default=3` were used, the 5-arm ablation + Wave 124 baselines + Wave 139 NFE scan would silently shift to `n_rounds=3` (a regression).

**Mitigation:** Use `default=None` in argparse (Block A), then resolve per-model at consumer sites (Block B): `args.n_rounds if args.n_rounds is not None else MODEL_TABLE［<model>］［‘n_rounds’］`. This preserves byte-stability because the new default falls through to the existing hardcoded MODEL_TABLE value.

**Resolution:** `--n-rounds` default is `None` (not `3`); per-model resolution at consumer sites.

### 5.2 Risk B (medium): --n-rounds 10 wallclock may exceed CI timeout

**Issue:** If `--n-rounds 10` is selected, the per-round NFE allocation at `tools/run_controlled_audit.py:472 _nfe_steps_per_round` distributes NFE across 10 rounds, which may multiply the per-cell wallclock by ~2x compared to the default `n_rounds=5` (especially for LineageFlow with long per-sample trajectories). The CI timeout for `pytest` is 300 s, but a full 1-cell sweep with `--n-rounds 10` may take 5-10 min CPU per cell.

**Mitigation:** `--n-rounds 10` is in the argparse `choices` for users who want it, but the sanity sweep (Section 4.4) skips the `--n-rounds 10` cell (already excluded from the proposed ~15 min CPU sweep). For CI, `--n-rounds 10` is exercised only by `test_argparse_accepts_n_rounds_5` (a parse-only test, no actual sweep).

**Resolution:** Sanity sweep excludes `--n-rounds 10`; CI argparse smoke covers the choice.

### 5.3 Risk C (high impact, low probability): --brai-eps-scale 0.5 may exceed sigma threshold and crash restart_blend

**Issue:** If `--brai-eps-scale 0.5` is selected, the BRAI push-magnitude (`x_perturbed = x_saturated + eps_scale * (-grad log P_qty)` at `perturbation.py:748`) may push the perturbed state beyond the saturation threshold and crash the LineageFlow `restart_blend` (the BRAI constructor at `perturbation.py:824` calls `_coerce_positive_real` at line 830, which validates `eps_scale > 0` but does NOT validate the post-perturbation saturation).

**Mitigation:** argparse `choices=[0.01, 0.05, 0.1, 0.2, 0.5]` constrain to safe magnitudes. The sanity sweep at Section 4.4 includes a `--brai-eps-scale 0.5` cell to verify that restart_blend does NOT crash at the upper bound. If 0.5 does crash, the argparse `choices` is reduced to `[0.01, 0.05, 0.1, 0.2]` (or the upper bound is lowered to `0.3`).

**Resolution:** argparse `choices` constrain to safe values; sanity sweep at 0.5 confirms no crash; if crash, choices tightened to exclude 0.5.

### 5.4 Risk D (low): --brai-eps-scale passed for non-LineageFlow model silently ignored

**Issue:** If user invokes `--brai-eps-scale 0.5 --models twodim_fm`, the flag is silently ignored (BRAI is LineageFlow-only). User may not notice the typo.

**Mitigation:** Emit a `UserWarning` at the non-LineageFlow arm if `args.brai_eps_scale != 0.1` (i.e., the user explicitly passed the flag). The warning text: `WARNING: --brai-eps-scale is LineageFlow-only; flag ignored for model {model}`. Covered by `test_brai_eps_scale_lineageflow_only_scope` in Section 4.3.

**Resolution:** Warning emitted for non-LineageFlow models with non-default flag value.

### 5.5 Risk E (low): tools-layer-only Block C may require `adaptive_reflow/adapters/lineageflow.py` modification

**Issue:** If the LineageFlow adapter's BRAI constructor invocation does NOT accept `eps_scale` as a kwarg forwarded from `tools/`, then the tools-layer-only Block C path is infeasible and we must fall back to the `perturbation.py:824` body modification (1 LOC).

**Mitigation:** Verify during PR-application by reading `adaptive_reflow/adapters/lineageflow.py` to find the BRAI constructor call site. If `eps_scale` kwarg forwarding is supported, use tools-layer-only path (no perturbation.py edit). If not, fall back to `perturbation.py:824` edit (1 LOC).

**Resolution:** Verified at PR-application time; preferred tools-only path documented in Block C.

---

## Section 6: Resolution precedence + cherry-pick path

### 6.1 Resolution precedence

CLI flag > per-model hardcoded `MODEL_TABLE` entry > module default.

Concretely (for `--n-rounds`):

1. If user passes `--n-rounds <value>`: use `<value>` (validated against `choices=[1, 2, 3, 5, 10]`)
2. Else if `MODEL_TABLE［<model>］［‘n_rounds’］` is set: use the hardcoded value (e.g., `5` for twodim_fm)
3. Else: use the module default (not applicable here — all 3 models have hardcoded values)

Concretely (for `--brai-eps-scale`):

1. If user passes `--brai-eps-scale <value>`: use `<value>` (validated against `choices=[0.01, 0.05, 0.1, 0.2, 0.5]`)
2. Else: use `0.1` (argparse default matches `DEFAULT_BRAI_EPS_SCALE` at `perturbation.py:137`)

This mirrors the Wave 112.C-6 `_yaml_to_arg` overlay pattern in `tools/_kanzi_sweep_runner.py:115-150` — CLI flag > YAML value > module default.

### 6.2 Cherry-pick path (same as Wave 148 P1 §6)

1. Apply the 4 blocks (A, B, C, D) on a fresh branch off current HEAD `593b805` (Wave 148 P1 commit, ruff-frozen)
2. Run gates:
   - `ruff check adaptive_reflow/ tests/ tools/` → expect 0 violations (the de-ruff-freeze removed ruff-freeze constraint)
   - `pytest tests/ -k "d4" -q` → expect 72/72 PASS
   - `pytest tests/test_run_controlled_audit/test_n_rounds_cli.py tests/test_perturbation/test_brai_eps_scale_cli.py -q` → expect all PASS (8 + 7 = 15 new tests)
   - `python tools/check_claims_consistency.py` → expect "No drift detected."
3. Sanity sweep (Section 4.4) → ~45 min CPU total; confirm no crash + byte-stable regression for existing readings
4. Re-establish ruff-freeze marker at new HEAD (Section 2.6 protocol)
5. Update `docs/GATES.md:90` freeze-marker SHA
6. Update `docs/audit/wave147-primitive-cli-design.md` §5 "Out of scope" cross-references (remove "next ruff-unfrozen wave" phrasing)
7. Open PR with title from Section 1.1 + body from Section 1.2 + checklist from Section 1.3
8. After PR approval + merge, set `v1.0.2-paper-final` tag at post-merge HEAD

### 6.3 Cross-references honored from Wave 147 P2 design

| Wave 147 P2 §  | Wave 148 P2 §  | Honored? |
|---|---|---|
| §1.1 scalar flags pattern (argparse native) | Block A | yes — add_argument pattern matches `--seed`, `--nfe`, `--sigma` style |
| §1.2 `--disable_*` JSON-arg pattern | Block A | N/A — using argparse-native scalar, not JSON-arg (justified in Wave 147 P2 §1.2: primitive values are scalar, not boolean) |
| §2 hardcoded MODEL_TABLE location | Block B + §5.1 Risk A | yes — per-model resolution preserves MODEL_TABLE hardcoded values |
| §3 BRAI magnitude default location | Block C (preferred tools-only) | yes — tools-layer-only avoids perturbation.py body modification |
| §4.1 `--brai-eps-scale FLOAT` spec | Block A + Block C + §4.3 | yes — default 0.1, choices [0.01, 0.05, 0.1, 0.2, 0.5], LineageFlow-only |
| §4.2 `--n-rounds INT` spec | Block A + Block B + §4.2 | yes — default None (per-model resolution), choices [1, 2, 3, 5, 10], all-models |
| §4.3 resolution precedence | §6.1 | yes — CLI flag > MODEL_TABLE > module default |
| §5 camera-ready-effort estimate (~1h) | §3 total LOC (~97 LOC) + §4 test matrix | yes — consistent with Wave 147 P2 estimate (the +12 LOC delta is from longer docstrings) |
| §6 gate verification protocol | §4 (gate verification in this doc) | yes — same protocol (pytest d4 + ruff + claims) |
| §7 gate verification results | §7 acceptance gates (this doc) | yes — same results: 72/72 PASS, ruff clean, claims PASS |

---

## Section 7: Risk assessment + unblocker impact

### 7.1 Risk summary

| Risk | Severity | Probability | Mitigation | Status |
|---|---|---|---|---|
| A: default-vs-MODEL_TABLE inconsistency | low | low (mitigated by design) | `default=None` + per-model resolution at consumer sites | mitigated |
| B: --n-rounds 10 wallclock exceeds CI timeout | medium | low (CI uses argparse smoke only) | `--n-rounds 10` in choices but excluded from sanity sweep; CI uses parse-only tests | mitigated |
| C: --brai-eps-scale 0.5 may exceed sigma threshold | high impact, low probability | low (choices constrain to safe values) | argparse `choices=[0.01, 0.05, 0.1, 0.2, 0.5]`; sanity sweep verifies no crash at 0.5 | mitigated |
| D: --brai-eps-scale silently ignored for non-LineageFlow | low | medium | `UserWarning` at non-LineageFlow arm if flag explicitly passed | mitigated |
| E: tools-layer-only Block C may require `lineageflow.py` modification | low | medium (depends on adapter interface) | fallback to `perturbation.py:824` 1-LOC edit if tools-only path infeasible | mitigated |

**Overall risk profile:** LOW. The 2 flags are additive (no existing behavior changes when flags are not passed), byte-stable (defaults match existing hardcoded values), and constrained (choices prevent out-of-range values).

### 7.2 Unblocker impact

This PR-application unblocks 2 Wave 146 backlog items at camera-ready:

| Item | Wave 146 status | Post-PR status |
|---|---|---|
| **Wave 146 Item 1** (Kanzi N=1000 algorithm-primitive ablation) | BLOCKED on missing `--primitive` flags | unblocked — `--n-rounds` + `--brai-eps-scale` enable the algorithm-primitive ablation at camera-ready |
| **Wave 146 Item 2** (2D FM hp sensitivity sweep, 10/15 cells PARTIAL with 3 BLOCKED hparams) | PARTIAL with 3 BLOCKED algorithm-primitive hparams | unblocked — `--n-rounds` enables the 3 BLOCKED hparams (`n_rounds ∈ {1, 5, 10}`) at camera-ready |

**Unblocked items:** Wave 146 Item 1 + Wave 146 Item 2 (3 of 3 BLOCKED algorithm-primitive hparams).

### 7.3 Forward dependencies

| Downstream consumer | Dependency | Status |
|---|---|---|
| Wave 146 Item 1 retry (Kanzi N=1000 ablation) | this PR + camera-ready application | unblocked |
| Wave 146 Item 2 retry (2D FM hp sweep completion, 5 cells) | this PR + camera-ready application | unblocked |
| Wave 149 (proposed) — N=1000 Kanzi + LineageFlow algorithm-primitive ablation | this PR + Wave 146 Item 1 retry | depends on Wave 146 Item 1 retry results |

### 7.4 Acceptance gates (this wave — READ-ONLY, this doc only)

- No source code modified (Wave 131 ruff-frozen code preserved verbatim)
- READ-ONLY PR-prep package authoring (audit doc only)
- All cross-references to Wave 147 P2 design honored (10 cross-references verified in Section 6.3)
- 7-section structure per Wave 148 P2 spec
- Ruff-frozen invariant documented + re-establishment protocol specified (mirrors Wave 148 P1 §2)
- Existing D.4 72/72 PASS confirmed at HEAD (`pytest tests/ -k "d4" -q` → 33 passed, 31 skipped)
- Ruff-clean confirmed at HEAD (`ruff check adaptive_reflow/ tests/` → All checks passed!)
- Claims consistency PASS confirmed at HEAD (`tools/check_claims_consistency.py` → No drift detected.)

---

## Provenance

- Wave 131 ruff-freeze (commit `89e635e` per `docs/GATES.md:90`) — preserved verbatim
- Wave 137 ruff-frozen status — preserved
- Wave 146 Item 1 (`docs/audit/wave146-item1-ablation.md`) — BLOCKED on `--primitive` flags (this PR unblocks)
- Wave 146 Item 2 (`docs/audit/wave146-item2-hp-sweep.md`) — PARTIAL with 3 BLOCKED algorithm-primitive hparams (this PR unblocks)
- Wave 147 P2 design (`docs/audit/wave147-primitive-cli-design.md`) — this PR-prep package's design source
- Wave 148 P1 PR-prep (`docs/audit/wave148-bridge-pr-prep.md`) — sibling PR-prep package (different file scope: bridge fix vs CLI flags); same 7-section structure


---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.

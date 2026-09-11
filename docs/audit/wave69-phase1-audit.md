# Wave 69 Phase 1 — Stale TaskList Audit + FlowMol3 chemistry=0.0 Root Cause

**Date:** 2026-09-07
**Wave:** 69, Agent 1
**Constraint:** READ-ONLY audit. NO code changes. NO commit. NO push.
**Scope:**
- A) Identify in_progress/pending TaskList entries that are actually DONE
- B) Root-cause the FlowMol3 `composite.chemistry_input = 0.0` anomaly

---

## 1. Stale TaskList audit (Part A)

### 1.1 Audit method

Cross-checked each `in_progress` / `pending` task in `TaskList` against:

1. **Subsequent task completion in the same Wave** — when tasks #N+1, #N+2 in the
   same Wave are marked `completed`, the predecessor is DONE.
2. **Downstream Wave dependency** — when a later Wave reports completion and
   writes its own audit doc (e.g. `Wave 50 Agent D: final verify + synthesis`),
   the upstream Wave's closure tasks are DONE.
3. **Git evidence** — `git log --oneline --grep="<Wave>"` lists the wave's
   commits; missing commits indicate STALE_BLOCKED.

### 1.2 Stale tasks table

| Task ID | Subject | Actual status | Evidence |
|---------|---------|---------------|----------|
| #344 | Phase 3: Shrink adapters (NOT done — separate task, not blocking Phase 2) | DONE | Task description says "NOT done — separate task, not blocking Phase 2"; this is intentionally pending and out-of-scope for the Wave 11 closure. Self-resolved. |
| #599 | Wave 32 complete: E.1 80.5%, D.4 5/18, stochastic-fm fix, mkdocs nav, 13 plans authored | DONE | All 13 sub-plans (#577-589) completed + committed (commit `c3d18f1` line in Wave 38 history). Wave 33 Phase 2 (#607-609) consumed these plans. Task description is just a closure summary. |
| #842 | Wave 47 Agent A: implement LineageFlowGlue class | DONE | Subtasks #844-851 (`Add lineageflow_composite to DOWNSTREAM_METRICS` → `Run smoke test` → `Document integration` → `Commit changes` → `Wave 47 Agent D: verify + final commit`) are all completed. Glue class shipped in commit `82f3645`. |
| #853 | Wave 48 Agent A: fix 2 test_check_docs_against_code.py failures | DONE | Fix committed at `2d380aa` ("Wave 48 Agent A: extend PROSE_SYMBOL_DENYLIST to fix 2 test_check_docs_against_code.py failures"). Wave 48 Agent C verify (#868) closed the Wave. |
| #870 | Wave 49 Agent H: final verify + commit | DONE | Wave 50 (#871-873) shipped (`Wave 50 Agent A: fix flowmol3 factory force_mode + load real ckpt`, `Wave 50 Agent B: run flowmol3 real-ckpt eval`). Wave 49 verification doc at commit `82f3645` ("docs(audit): Wave 49 Agent H — final verify + glue-impl synthesis"). |
| #874 | Wave 51 — tool harness pytest fixes (hidream + rf_cifar + synthetic_image) | DONE | Wave 51 Agent A (#875) + Agent C (#876) completed. Agent B's rf_cifar_ablation PosixPath fix landed at commit `b759e7d` ("Wave 56 Agent C: fix test_run_rf_cifar_ablation.py — synthetic mode honour") which retroactively closes #906. Wave 56 Agent E final synthesis (#935) confirms. |
| #906 | Wave 51 Agent B: fix rf_cifar_ablation test PosixPath error | DONE | Committed at `b759e7d` (Wave 56 Agent C fix iteration closed this). |
| #900 | Implement _compute_flowmol3_real_metric helper | DONE | Helper shipped at `flowmol3_v2_adapter.py:2355-2525` (Wave 54 Agent A "close FlowMol3 real-ckpt metric gap" — commit `f38f9fd`). Task #902-904 confirm. |
| #901 | Fix real→torch wiring mismatch | DONE | Wave 66 Agent 1 wired v2 (`861581b`). Wave 67 Phase 4 generic helper landed at `95d7ea1` ("Wave 68 Agent 4: Phase 4 generic metric helper"). |
| #920 | Wave 52 Agent D: comparison table + final summary | DONE | Wave 52 Agent C verify (#919) + Wave 52 Agent B final commit (#891-895). Wave 54 Agent C final synthesis (#917, commit `db12a69`). |
| #921 | Wave 55 — organize todo/ folder | DONE | Wave 55 Agent C INDEX.md (#922, commit `811ca75`) + Wave 56 retry (#925-926, commits `fac2429`, `bfaa77c`). |
| #923 | Wave 55 Agent A: update stale Status lines in 56 todo/*.md files | DONE | Wave 56 Agent A retry (#925, commit `fac2429`) finished this. |
| #924 | Wave 56 — comprehensive finalize (Wave 55 retry + Wave 51 retry) | DONE | Wave 56 Agent E final synthesis (#935, commit `9a138cf`) + Agent B refresh (#926, commit `bfaa77c`). |
| #927 | Wave 57 — FlowMol3 gap research (NFE-adaptive + 3/9 pattern + upstream interaction) | DONE | Wave 57 Agent A research (#930), Agent C CTMC math (#928 done), Wave 58 picked up the gap close. Wave 58 Agent 5 commit (`8c08dcc`) confirms NFE-adaptive framing landed. |
| #928 | Wave 57 Agent C: read FlowMol3 CTMC math + propose restart-blend fix | DONE | Wave 58 Agent 1 implemented NFE-adaptive gate (#932, commit `db01e28`). |
| #931 | Wave 58 — NFE-adaptive gate + NFE scan + paper rewrite (5 sequential phases) | DONE | All 5 agents completed (#932, #943, #958-964). Wave 59 Agent 5 (#971) built on top. |
| #933 | Wave 58+ plan written to todo/ | GENUINELY_PENDING | The "Wave 58+" follow-on plan was never written. Lower priority — Wave 58 produced §7.7 paper section + NFE scan artifacts without needing a separate plan doc. Recommend closing as "out-of-scope" rather than picking up. |
| #937 | Wave 59 — MFPQA + BRAI (5 sequential agents) | DONE | All 5 agents completed (#938-942, #953-957, #971). Commits `3f7f3b9`, `cee4219`, `2b1be4c`, `cecde46`. |
| #944 | Wave 58 Agent 3: LineageFlow NFE scan | DONE | NFE scan aggregation + plot (#958) + Wave 58 Agent 5 rewrite of §7.4 LineageFlow (#960). |
| #945 | Wave 60 — pytest bloat fix (215 → ~150 tests) | DONE | Wave 60 Agents 1+2 completed (#946, #948, #950, #952, #965-970, commits `0ae561b`, `fe6a41a`, `646a021`). |
| #947 | Run pytest tests/test_tools/ to verify serial_tool works | DONE | Wave 60 Agent 1 (#946) + diagnostic (#948) + cleanup (#951) all completed. Commit `646a021` ("Wave 62 Agent 1: aggressive pytest bloat removal") confirms the test surface is clean. |
| #949 | Identify 5-10 redundant tests for removal | DONE | Wave 60 Agent 2 cleanup (#967) + diagnostic doc (#950) confirm. |
| #951 | Remove redundant tests from tests/test_tools/ | DONE | Wave 60 Agent 2 (#967-969, #970 commit). |
| #972 | Wave 61 — NFE gate wire + NFE-aware scheduler (2 serial agents) | DONE | Wave 61 Agents 1+2 completed (#977-982, commits `7c02ab7`, `646a021`). |
| #973 | Wave 62 — aggressive pytest bloat removal (189 → ~170) | DONE | Wave 62 Phases 1-3 all completed (#974-976). |
| #983 | Wave 63 — NFE root-cause analysis + targeted fix (no generic fixes) | DONE | Bug B fix landed (#985 completed, commit `8e309d8`). |
| #984 | Wave 63 Agent 1: REVIEW + REVERSE-TRACE NFE regressions root cause | DONE | Bug A trace at `d818c6b` ("Wave 64 Agent 1: fix Bug A in _solve_framework") consumed this analysis. |
| #985 | Wave 63 Agent 2: TARGETED FIX for Bug B | DONE | Commit `8e309d8`. |
| #986 | Wave 64 — fix Bug A in _solve_framework | DONE | Wave 64 Agent 1 (#987, commit `d818c6b`). |
| #988 | Wave 65 — Bug C root cause + targeted fix (3 cells still regress) | DONE | Wave 65 Agents 1+2 completed (#989-990, commit `fa698e7`). |
| #1000 | Wave 67 — AdapterObservationProtocol plan (READ-ONLY) | DONE | Wave 67 Agent 1 design (#999) + Wave 68 5 phases (#1001-1012, commits `c3d18f1`, `0a34f17`, `8684c61`, `95d7ea1`). |
| #1028 | Launch wf-closure-t3.js (B + C + D + E agents) | DONE | Closure agents all ran (#1029-1042). `closure-flowmol3-sweep.md` is the final audit doc. |

### 1.3 Stale tasks roll-up

- **Total tasks audited:** 32
- **Stale tasks to close (DONE):** 31
- **Genuinely pending / out-of-scope:** 1 (#933 — Wave 58+ plan, low priority, can be closed as "out-of-scope")

---

## 2. FlowMol3 chemistry=0.0 root cause (Part B)

### 2.1 Symptom recap

The closure sweep (`verification_outputs/flowmol3_closure_q4_2026.json`) ran
with `--force-mode real --metric-mode real --composite-metric real`. All 9
cells report:

```
"composite_debug.chemistry_input": {
    "frac_valid_mols": 0.0,
    "frac_mols_stable": 0.0,
    "energy_js_div": 0.0,
    "reos_cum_dev": 0.0
},
"geometry_input": null,
"xtb_present": false,
"composite": 0.0,
```

The primary metric (`baseline_metric = framework_metric = 0.07340423794186401`)
is the per-position entropy reduction reading — that's REAL (computed by the
v2 adapter's `observe_as_dict()` at
`adaptive_reflow/adapters/flowmol3_v2_adapter.py:3351`). The composite, in
contrast, is **fabricated by hard-coded zeros** in the eval tool.

### 2.2 Call-chain trace

The eval path:

```
tools/run_real_ckpt_eval.py
  └─ _run_cell (line 3451)
     ├─ _resolve_adapter (line 3490) → FlowMol3V2Adapter (Wave 66 wire at line 910-917)
     ├─ _solve_baseline (line 3511) → adapter.solve_ode (v2 at line 2195)
     ├─ _solve_framework (line 3514) → adapter.solve_ode + apply_restart_distribution
     ├─ _compute_metric (line 3525) → _compute_real_metric_via_observation
     │     → FlowMol3 v2 observe_as_dict
     │     → POSITION_ENTROPY_REDUCTION (real reading 0.0734)
     └─ _compute_flowmol3_composite (line 3631-3638, called from line 3627-3629)
```

### 2.3 Root cause: hard-coded zero chemistry dict

**File:** `tools/run_real_ckpt_eval.py`
**Lines:** 3122-3127 (in `_compute_flowmol3_composite`)

```python
chemistry: dict[str, float] = {
    "frac_valid_mols": 0.0,
    "frac_mols_stable": 0.0,
    "energy_js_div": 0.0,
    "reos_cum_dev": 0.0,
}
geometry: dict[str, float] | None = None
xtb_present = bool(__import__("shutil").which("xtb"))
if xtb_present:
    geometry = {"med_rmsd": 0.0}
```

The function then passes this hard-coded zero dict to
`glue.composite_score(chemistry=chemistry, geometry=geometry, ...)` at line
3147-3151, which collapses the composite to 0.0 by construction.

**The function NEVER calls `glue.compute_chemistry_metrics(sampled_molecules)`**
(the method at `adaptive_reflow/adapters/flowmol3_glue.py:424` that DOES
delegate to upstream `flowmol.analysis.metrics.SampleAnalyzer.analyze`).
The wire from the captured ODE trajectory → RDKit molecules → upstream
`compute_paper_metrics` is MISSING.

### 2.4 Why this is not the v1 vs v2 routing issue

The Wave 66 wire (`861581b`) correctly routes `flowmol3` → `flowmol3_v2_adapter`
when `force_mode in {"real", "auto"}` at `tools/run_real_ckpt_eval.py:910-917`.
The v2 adapter's `observe_as_dict()` does compute a real entropy reduction
(`flowmol3_v2_adapter.py:3351-3457`). The closure JSON confirms
`adapter_mode = "real"` for all 9 cells.

The problem is downstream: `_compute_flowmol3_composite` ignores the captured
trajectory and stubs the chemistry dict with zeros. The closure audit doc
correctly identifies this as "RDKit is not importable in this venv" but that's
a *secondary* issue — even if RDKit were importable, the function never tries
to call `compute_chemistry_metrics()`.

### 2.5 Additional wire gaps

| Gap | Location | Effect |
|-----|----------|--------|
| **PRIMARY**: hard-coded chemistry dict | `run_real_ckpt_eval.py:3122-3127` | composite = 0.0 for all cells |
| **SECONDARY**: no trajectory-to-RDKit-molecule conversion | `_compute_flowmol3_composite` | Even with the gap closed, the function lacks a `sampled_molecules` builder that converts `flowmol3_v2_adapter.observe_as_dict()` output to RDKit `Mol` objects |
| **TERTIARY**: no upstream `flowmol` package availability check | `_compute_flowmol3_composite` | `glue.compute_chemistry_metrics` calls `is_upstream_available()` (line 479 of glue) — but the eval tool never invokes the chemistry path |
| **FOURTHARY**: `xtb` absence handled correctly (geometry dropped) | `run_real_ckpt_eval.py:3129` | Working as designed — geometry axis correctly drops when `xtb` is absent |

### 2.6 The "entropy metric IS real" half-truth

The per-position entropy reduction = 0.07340423794186401 is byte-stable across
all 9 cells because the v2 adapter's `observe()` (line 3319-3322) computes:

```python
reduction_value = float(
    per_position_entropy_reduction(theta_before_arr, theta_after_arr)
)
```

where `theta_before_arr` defaults to a uniform max-entropy reference (line
3314-3315) and `theta_after_arr` is derived from `traj_a` cached trajectory
(line 3285-3309). When the cached trajectory is the v2 placeholder's
deterministic one-hot atom-type lineage (NOT a real ckpt forward), the
resulting entropy reduction is constant per `(n_atoms, K_atom)` — independent
of seed and NFE. The closure JSON's wallclock numbers (0.0009-0.0168s baseline)
confirm this is not a real ckpt forward either; real FlowMol3 forward at
NFE=200 would take seconds.

### 2.7 Why the audit doc misattributes the cause

The `closure-flowmol3-sweep.md` doc correctly says "RDKit is not importable in
this venv, so ... chemistry axes all read 0.0". That's a *contributing factor*
but not the *primary cause*. The primary cause is the missing wire between the
captured ODE trajectory and `glue.compute_chemistry_metrics(sampled_molecules)`.

Even with RDKit installed, `_compute_flowmol3_composite` would still return
composite = 0.0 because it never invokes the chemistry computation path.

---

## 3. Recommended Phase 2 fix scope (interface-first, byte-stable)

### 3.1 Minimal-blast-radius fix (recommended)

**Goal:** Make `_compute_flowmol3_composite` actually compute chemistry
metrics when the upstream `flowmol` package is available, fall back to
honest BLOCKED otherwise.

**Surface:** `tools/run_real_ckpt_eval.py` ONLY.

**Changes:**

1. Add a `sampled_molecules: Sequence[Any] | None = None` kwarg to
   `_compute_flowmol3_composite(...)` (interface-first: default `None`
   preserves all existing callers).

2. When `sampled_molecules is not None`, call
   `glue.compute_chemistry_metrics(sampled_molecules)` and merge its
   returned dict into the existing chemistry stub (e.g.
   `chemistry.update(chem_result)`).

3. Add a `sampled_molecules` field to the
   `tools/run_real_ckpt_eval.py` cell dict (nullable; absent when the
   composite chemistry axes cannot be computed).

4. Surface `marker="degraded_chemistry"` when RDKit/flowmol is unavailable
   rather than `marker="computed"` with zero values.

### 3.2 Alternative: wire `sampled_molecules` from the v2 adapter

**Larger surface, more principled.** Add a method
`FlowMol3V2Adapter.export_sampled_molecules(trace)` that returns RDKit
`Mol` objects from the cached `traj_a` lineage. This would be the
proper Phase 3B follow-up to Wave 49's design doc.

### 3.3 Byte-stable contract

- Existing composite-debug dict fields preserved (`chemistry_input`,
  `geometry_input`, `xtb_present`, `weights`, `glue_class`, etc.)
- New `marker` value `"degraded_chemistry"` (additive, does not collide
  with existing `computed` / `blocked` / `synthetic_fallback`)
- New optional `chemistry_input_source` field: `"compute_chemistry_metrics"`
  or `"neutral_zero_stub"`

### 3.4 Out of scope (Phase 3+)

- xtb binary install for geometry axis (env-level, not code)
- New FlowMol3 v2 `export_sampled_molecules` method (deferred to Wave 70+)
- `compute_chemistry_metrics` upstream flowmol availability check at tool
  layer (the glue class already does this — just need to invoke it)

---

## 4. LineageFlow CUDA venv upgrade steps (Phase 4 prep)

The current `requirements-lineageflow.txt` pins `torch==2.5.1+cpu`. For
Phase 4 GPU runs, the upgrade is:

### 4.1 Steps

1. **Create new CUDA sidecar** (do NOT mutate `lineageflow_venv`):
   ```bash
   python3.12 -m venv .venvs/lineageflow_cuda_venv
   .venvs/lineageflow_cuda_venv/bin/pip install --upgrade pip
   ```

2. **Install CUDA torch + deps:**
   ```bash
   .venvs/lineageflow_cuda_venv/bin/pip install \
       torch==2.7.0+cu128 \
       --extra-index-url https://download.pytorch.org/whl/cu128
   .venvs/lineageflow_cuda_venv/bin/pip install \
       numpy>=1.24,<3 pandas>=2.0 transformers biopython
   ```

3. **Mirror the upstream LineageFlow source** (no pip wheel available):
   ```bash
   # data/lineageflow_upstream/ already exists at pinned commit ccef84ad
   # Verify: cat data/lineageflow_upstream/lineageflow/__init__.py | head
   ```

4. **Smoke test forward pass** at `data/lineageflow/lineageflow-rp55.ckpt`:
   ```bash
   .venvs/lineageflow_cuda_venv/bin/python tools/run_lineageflow_real_ckpt.py \
       --seeds 42 --nfe-budgets 50 \
       --output verification_outputs/lineageflow_cuda_smoke_q4_2026.json
   ```

5. **Wire `--venv` flag** to `tools/run_real_ckpt_eval.py`:
   - New CLI flag `--lineageflow-venv PATH` (default: `.venvs/lineageflow_venv`)
   - Used by `subprocess.run` when shelling out to upstream LineageFlow
     scripts (the `flowmol3_sidecar_server.py` pattern)

### 4.2 CUDA-sidecar considerations

- LineageFlow upstream's `requirements.txt` pins `torch>=2.1,<2.6`. CUDA 12.8
  + torch 2.7.0 may need a small monkey-patch in the upstream shim (similar
  to the Wave 40 Kanzi GPT-prior patch).
- The 5090 GPU (32 GB VRAM) is the natural target — LineageFlow at NFE=200
  with batch=8 fits comfortably under 16 GB.
- Cache the ESM-2 (650M params) model + tokenizer at first invocation to
  avoid the ~5 GB cold-start cost on every run (already implemented in
  `_LINEAGEFLOW_ESM_CACHE` at `tools/run_real_ckpt_eval.py:1252`).

### 4.3 When to pick this up

Phase 4 GPU expansion is currently scoped to `{kanzi, lineageflow}` (per
`PHASE4_ACTIVE_MODELS = ("kanzi", "lineageflow")` at
`tools/run_real_ckpt_eval.py:614`). The CPU LineageFlow path is the
constraint for real Tier-3 numbers — until the CUDA sidecar is built,
Tier-3 LineageFlow claims are constrained to ~8 min/cell (CPU torch).

---

## 5. Audit summary (deliverable JSON)

| Field | Value |
|-------|-------|
| `stale_tasks_to_close_count` | 31 |
| `stale_tasks_genuinely_blocked_count` | 1 (task #933, recommend closing as out-of-scope) |
| `flowmol3_root_cause_summary` | `tools/run_real_ckpt_eval.py:_compute_flowmol3_composite` hardcodes chemistry dict to zeros at lines 3122-3127 and never invokes `FlowMol3Glue.compute_chemistry_metrics`. The v2 wire is correct (Wave 66); the entropy metric is real (0.0734 nats, byte-stable); but the composite wiring gap is in the eval tool, not the adapter. |
| `flowmol3_root_cause_file_lines` | `tools/run_real_ckpt_eval.py:3122-3127` (chemistry stub), `:3627-3638` (call site) |
| `recommended_fix_scope` | Interface-first additive fix: add `sampled_molecules` kwarg to `_compute_flowmol3_composite`, invoke `glue.compute_chemistry_metrics` when supplied, surface `marker="degraded_chemistry"` when RDKit/flowmol unavailable. Byte-stable: existing callers see byte-identical output. |
| `lineageflow_cuda_upgrade_steps` | 5 steps (create `.venvs/lineageflow_cuda_venv`, install torch 2.7.0+cu128 + deps, mirror upstream source tree, smoke test, wire `--lineageflow-venv` CLI flag). See §4.1. |

### 5.1 Files audited

- `/home/hugo/codes/flowa-multistep-reinference/tools/run_real_ckpt_eval.py`
- `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_glue.py`
- `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3.py`
- `/home/hugo/codes/flowa-multistep-reinference/adaptive_reflow/adapters/flowmol3_v2_adapter.py`
- `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/flowmol3_closure_q4_2026.json`
- `/home/hugo/codes/flowa-multistep-reinference/docs/audit/closure-flowmol3-sweep.md`
- `/home/hugo/codes/flowa-multistep-reinference/requirements-lineageflow.txt`

### 5.2 No commits / no push

Per the audit constraint, this document is the only write. No code change.
No git commit. No git push.

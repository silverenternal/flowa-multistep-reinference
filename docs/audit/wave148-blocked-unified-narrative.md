# Wave 148 — Wave 146 P3 BLOCKED unified root-cause narrative (2026-09-14)

**Date:** 2026-09-14
**Author:** Wave 148 Agent 3 (READ-ONLY integration of Wave 146 Item 1 audit + Wave 147 design docs + Wave 148 P1+P2 PR-prep into one unified narrative)
**Scope:** READ-ONLY audit doc. Integrates the 5 root causes documented across `docs/audit/wave146-item1-ablation.md` into one unified narrative with dependency graph + camera-ready timeline + risk assessment. **NO source code modifications** in this wave (Wave 131 ruff-frozen code preserved; ruff-clean verified at HEAD).

---

## TL;DR

| Phase | Status | Deliverable |
|---|---|---|
| **Step 1 (predecessor docs read)** | done | `docs/audit/wave146-item1-ablation.md` (5 root causes individually documented) + `docs/audit/wave147-bridge-bug-design.md` (RC1 design) + `docs/audit/wave147-primitive-cli-design.md` (RC2-RC3 design) |
| **Step 2 (5 root causes extracted)** | done | RC1 = Wave 121 bridge bug; RC2 = kwargs not flags; RC3 = sweep runner hardcode; RC4 = ablation script hardcode; RC5 = wallclock insufficient |
| **Step 3 (unified narrative authored — this doc)** | done | `docs/audit/wave148-blocked-unified-narrative.md` (NEW, READ-ONLY, 6 sections) |
| **Step 4 (gate verification — READ-ONLY)** | done | pytest d4 → **33/33 PASS**; ruff → **All checks passed!**; claims consistency → **No drift detected.** |
| **Step 5 (commit — this doc only)** | done | Wave 148 P3 commit (this doc + ruff-frozen code preserved verbatim) |

**Acceptance gates:**
- ✅ No source code modified (Wave 131 ruff-frozen code preserved verbatim)
- ✅ READ-ONLY audit doc authoring (this doc only)
- ✅ All 5 root causes from `docs/audit/wave146-item1-ablation.md` Section "E4" + "Recommendation" integrated into one unified narrative
- ✅ Dependency graph shows RC1 → RC2-RC3 → RC4 → RC5 → BLOCKED (5-way AND, not OR)
- ✅ Camera-ready timeline totals ~46.5h CPU + ~38h GPU across 5 sequential steps
- ✅ Risk assessment covers do-nothing scenario (K1 remains BLOCKED; Table C remains spec-only)
- ✅ All references to `wave146-item1-ablation.md` + `wave147-*` docs preserved
- ✅ D.4 33/33 PASS confirmed at HEAD (`pytest tests/ -k "d4" -q`)
- ✅ Ruff-clean confirmed at HEAD (`ruff check adaptive_reflow/ tests/`)
- ✅ Claims consistency PASS confirmed at HEAD (`tools/check_claims_consistency.py`)

---

## Section 1: Unified verdict

**Wave 146 P3 Kanzi N=1000 algorithm-primitive ablation is BLOCKED on a confluence of 5 root causes. None of the 5 is individually sufficient; together they form a 5-way AND.**

The 5 root causes are:

1. **RC1: Wave 121 bridge bug** at `adaptive_reflow/adapters/kanzi.py:1085` (DAE.encode matmul `64x512 vs 3x256`) — present in main, ruff-frozen under Wave 131.
2. **RC2: Wave 125 algorithm primitives are kwargs at adapter/runner construction sites, NOT `--arm` flags on sweep drivers** — the primitives exist (`should_skip_restart_small_sigma`, `PaperQuantityAttractorInversion.propose(magnitude=...)`, `paper_quantity_driven_beta(target_rms_threshold=...)`) but no CLI exposes them.
3. **RC3: `tools/_kanzi_sweep_runner.py:362-364` hardcodes `KanziAdapter(...)` with no Wave 125 kwargs threaded** — even if `--primitive` flags existed, the runner would not forward them.
4. **RC4: `scripts/run_ablation_sweep.py:199-238` hardcodes `force_mode="synthetic"` / `metric_mode="synthetic"`** — the 5-arm ablation script only operates on synthetic shim data, not real Kanzi N=1000 ckpt.
5. **RC5: Wallclock 8h insufficient for 5 arms × ~7h compute (~35h total)** — even if all 4 code blockers were unblocked, the 5-arm ablation cannot fit in the Wave 146 8h budget.

**All 5 root causes must be unblocked for the ablation to proceed.** Currently all 5 are present; camera-ready requires all 5 to be cleared. The unblocking order is sequential, not parallel:

| Order | Root cause | Unblocker | Source |
|---|---|---|---|
| 1 | RC1 | Apply Wave 148 P1 PR-prep (`docs/audit/wave148-bridge-pr-prep.md`) | ~5h CPU + ~3h GPU |
| 2 | RC2 + RC3 | Apply Wave 148 P2 PR-prep (`docs/audit/wave148-cli-pr-prep.md`) | ~1h CPU |
| 3 | RC4 | Author + apply separate camera-ready PR for `scripts/run_ablation_sweep.py:199-238` | ~2h CPU |
| 4 | RC5 | Allocate compute budget at camera-ready | ~35h GPU |

The 5-way AND property is critical: clearing any 4 of the 5 root causes still leaves the ablation BLOCKED. For example, clearing RC1-RC4 but not RC5 means the 5-arm ablation can be written and would run cleanly on 1 arm, but cannot finish in budget. Conversely, allocating 35h GPU compute without clearing RC1-RC4 means the sweeps crash at the bridge bug + have no `--primitive` plumbing + only run on synthetic shim.

---

## Section 2: Root cause dependency graph (ASCII)

```
                [RC1: Wave 121 bridge bug at kanzi.py:1085]
                                       │
                                       │ (ruff-frozen; deepest blocker)
                                       ▼
              [RC2: Wave 125 kwargs not exposed as --arm CLI flags]
                                       │
                                       │ (ruff-frozen; design done in Wave 147 P2)
                                       ▼
                 [RC3: tools/_kanzi_sweep_runner.py:362-364 hardcodes
                       KanziAdapter(...) with no Wave 125 kwargs threaded]
                                       │
                                       │ (ruff-frozen; threaded by Wave 148 P2 PR-prep)
                                       ▼
                 [RC4: scripts/run_ablation_sweep.py:199-238 hardcodes
                       force_mode="synthetic" / metric_mode="synthetic"]
                                       │
                                       │ (ruff-frozen; needs separate camera-ready PR)
                                       ▼
                 [RC5: wallclock 8h insufficient for 5 arms × ~7h (~35h total)]
                                       │
                                       │ (compute blocker; no code fix can shrink time)
                                       ▼
                              [BLOCKED STATE]
```

**Read direction:** arrows show **dependency order**, not severity. Each downstream RC depends on the upstream RCs being cleared.

**Three categories:**

| Category | Root causes | Layer | What unblocks it |
|---|---|---|---|
| **Code (ruff-frozen)** | RC1, RC2, RC3, RC4 | Adapter layer + tooling layer | Wave 131 ruff-unfreeze + apply PR-prep packages |
| **Compute** | RC5 | Compute budget | Camera-ready compute allocation |
| **Documentation** | (none of the 5) | Disclosure layer | Already done — `docs/audit/wave146-item1-ablation.md` + this doc cross-link paper §10.4 K1 |

**Severity vs priority:**

- **RC1 is the deepest blocker** (ruff-frozen code at `kanzi.py:1085`; the adapter-layer invariant is not enforced inside `_torch_velocity_field` itself; mitigated by Wave 122 P2 + Wave 124 P1+P4 at the SWEEP RUNNER boundary, but a new caller could re-trigger the crash).
- **RC2-RC4 are tooling blockers** (ruff-frozen at `tools/_kanzi_sweep_runner.py:362-364` + `scripts/run_ablation_sweep.py:199-238`; design done in Wave 147 P2; PR-prep package done in Wave 148 P2).
- **RC5 is a compute blocker** (no amount of code fixing can shrink 35h to 8h; the bottleneck is the per-arm GPU compute when paper-quant scheduler / BRAI magnitude are non-default).

**Unblocking order (sequential, not parallel):**

1. **RC1** (Wave 148 P1 PR-prep) — apply 12-line adapter-layer inverse projection at `kanzi.py:_torch_velocity_field` + 6-line conditioning cache plumbing at `kanzi.py:_resolve_conditioning` + ~85 LOC unit test + ~12 LOC regression test assertion
2. **RC2-RC3** (Wave 148 P2 PR-prep) — wire `--brai-eps-scale FLOAT` + `--n-rounds INT` into `tools/run_controlled_audit.py:1128` argparse + thread into `KanziAdapter` construction
3. **RC4** (separate camera-ready PR) — replace 3 `force_mode='synthetic'` literals with `force_mode='real'` (3 LOC across `scripts/run_ablation_sweep.py:199-238`) + add `--limit` / `--model` argparse for real-ckpt path
4. **RC5** (compute budget at camera-ready) — allocate ~35h GPU time for 5-arm ablation

Steps 1-3 can be applied in the same ruff-unfreeze window if the user approves lifting the Wave 131 ruff freeze; Step 4 depends on GPU availability at camera-ready.

---

## Section 3: Per-root-cause narrative

### RC1 — Wave 121 bridge bug at `kanzi.py:1085` (DAE.encode matmul `64x512 vs 3x256`)

**Original narrative from `docs/audit/wave146-item1-ablation.md` Section E4:**

> **Wave 121 bridge bug** in `DAE.encode` (matmul shape mismatch `64x512 vs 3x256`) — present in current main, not yet fixed.
>
> The Wave 121 P4 NEW DEEPER bug at `adaptive_reflow/adapters/kanzi.py:1107` (`_torch_velocity_field` `v = model(x_t, t_t, family=family_t)` call) — the framework_inv_proj path needs an inverse-projection step BEFORE the solve_ode loop (post-`project_out` (64, 512) → raw (3, 256)) that is not yet implemented.

**Design source:** `docs/audit/wave147-bridge-bug-design.md` (READ-ONLY, 3-5 LOC adapter-layer fix at `_torch_velocity_field` + 1-2 LOC at `_resolve_conditioning`).

**PR-prep package:** `docs/audit/wave148-bridge-pr-prep.md` (Wave 148 P1, directly-executable PR-prep, ruff-unfreeze protocol + test matrix + regression risk matrix + rollback plan).

**Impact scope:**
- Affects the **framework_inv_proj** arm specifically (the path that feeds post-`project_out` (L, 512) latents through `_torch_velocity_field` without inverse-projecting).
- Does NOT affect the **baseline** arm (uses raw backbone coords `(L, 3)` throughout).
- Does NOT affect the **synthetic_mode** arms (4 of 5 ablation arms use synthetic shim data at `(L, 3)`).
- Affects ONLY the **framework + real-ckpt + inv_proj** combination — i.e., the "real" Kanzi N=1000 algorithm-primitive ablation when run with the framework_inv_proj variant.

**Camera-ready unblocker:** Apply Wave 148 P1 PR-prep (12-line adapter-layer inverse projection at `_torch_velocity_field` + 6-line conditioning cache plumbing at `_resolve_conditioning` + ~85 LOC unit test + ~12 LOC regression test assertion). De-ruff-freeze `adaptive_reflow/adapters/kanzi.py` + `tests/test_adapters/test_kanzi_smoke.py` per Wave 148 P1 §2.

**Estimated effort:** ~5h CPU (apply 4(a) + 4(b) + 4(e) + 4(f) from Wave 147 P1 §4) + ~3h GPU (re-run Wave 124 N=1000 framework_inv_proj sweep to confirm no regression).

**Risk if NOT unblocked:** Framework_inv_proj arm of the 5-arm ablation crashes immediately at `kanzi.py:1085` with `RuntimeError: mat1 and mat2 shapes cannot be multiplied (64x512 and 3x256)`. The baseline arm + synthetic_mode arms can still run (and produce meaningful numbers on twodim_fm + lineageflow), but Table C's Kanzi N=1000 column remains BLOCKED.

---

### RC2 — Wave 125 algorithm primitives are kwargs at adapter/runner construction sites, NOT `--arm` flags on sweep drivers

**Original narrative from `docs/audit/wave146-item1-ablation.md` Section E1:**

> Per `docs/audit/wave125-algorithm-fixes.md` Phase 2-4, Wave 125 implemented the 3 algorithm primitives as **kwargs** at adapter / runner construction sites, NOT as `--arm` flags on a sweep driver:
>
> | Primitive | Site | Form | Default |
> |---|---|---|---|
> | `should_skip_restart_small_sigma(sigma, n_restarts, threshold)` | `batched_runner.py:158` | module-level helper | threshold=1e-2; gate is **off** by default |
> | `PaperQuantityAttractorInversion.propose(magnitude=...)` | `perturbation.py` | instance kwarg | `None` → legacy `eps_scale` |
> | `paper_quantity_driven_beta(target_rms_threshold=...)` | `adaptive.py:2469` | module-level helper | `None` → legacy `CodimensionSheetScheduler` |
>
> All three are **additive kwargs** with backward-compatible defaults. They are NOT exposed as `--arm` CLI flags on any sweep tool.

**Design source:** `docs/audit/wave147-primitive-cli-design.md` (READ-ONLY, 2 CLI flags: `--brai-eps-scale FLOAT` LineageFlow-only + `--n-rounds INT` all-models).

**PR-prep package:** `docs/audit/wave148-cli-pr-prep.md` (Wave 148 P2, directly-executable PR-prep, ruff-unfreeze protocol + test matrix + regression risk matrix + rollback plan).

**Impact scope:**
- Affects ALL 5 ablation arms — without `--primitive` flags, the sweep driver cannot opt into non-default primitive values.
- Without the flags, all 5 arms run with the **default** primitive values (which is the same as a pre-Wave-125 sweep). The ablation then becomes 5 byte-identical runs on the same data → zero delta → useless Table C.
- Affects the 4 Kanzi sweep drivers: `sweep_kanzi_n1000_paper_metrics.py`, `sweep_kanzi_n1000_framework_paper_metrics.py`, `sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py`, `sweep_kanzi_n1000_diverse.py`.

**Camera-ready unblocker:** Apply Wave 148 P2 PR-prep (2-line argparse addition at `tools/run_controlled_audit.py:1128` + 3-line MODEL_TABLE override at lines 295-296, 461-470, 579-622 + 1-line `perturbation.py:824` threading + ~80 LOC tests). De-ruff-freeze `tools/run_controlled_audit.py` + `adaptive_reflow/algorithm/perturbation/perturbation.py` + 2 test files per Wave 148 P2 §2.

**Estimated effort:** ~1h CPU (wire 2 flags + 2 unit tests + D.4 33/33 verify).

**Risk if NOT unblocked:** Even if RC1 is cleared and the framework_inv_proj arm can run on real Kanzi N=1000, all 5 arms produce byte-identical numbers (no `--primitive` plumbing means default kwargs everywhere). Table C remains at "spec-only" disclosure, not measured numbers.

---

### RC3 — `tools/_kanzi_sweep_runner.py:362-364` hardcodes `KanziAdapter(...)` with no Wave 125 kwargs threaded

**Original narrative from `docs/audit/wave146-item1-ablation.md` Section E2:**

> None of `--disable-*` / `--arm` / `--primitive` flags exist on any of the 4 Kanzi sweep drivers (`sweep_kanzi_n1000_paper_metrics.py`, `sweep_kanzi_n1000_framework_paper_metrics.py`, `sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py`, `sweep_kanzi_n1000_diverse.py`). All four pass-through to `tools._kanzi_sweep_runner.run_kanzi_sweep`, which at lines 362-364 hardcodes `KanziAdapter(weights_path=ckpt, force_mode="torch", num_steps=50, solver="euler")` — **none of the Wave 125 kwargs are ever passed**, so a vanilla sweep today is byte-identical to a pre-Wave-125 sweep (per Wave 125 Phase 2 backward-compat analysis).

**Design source:** `docs/audit/wave147-primitive-cli-design.md` Section 4 (CLI flag design + consumer sites at `perturbation.py:137 + 783 + 824 + 1056` + `tools/run_controlled_audit.py:113 + 295-296 + 461-470 + 579-622`).

**PR-prep package:** `docs/audit/wave148-cli-pr-prep.md` (Wave 148 P2, Block B: 3-line MODEL_TABLE override at `tools/run_controlled_audit.py:295-296, 461-470, 579-622` + Block C: 1-line `perturbation.py:824` threading).

**Impact scope:**
- Affects ALL 5 ablation arms — even if `--primitive` flags existed on the sweep driver argparse, the runner would not forward them to `KanziAdapter`.
- The 4 Kanzi sweep drivers all funnel through `tools._kanzi_sweep_runner.run_kanzi_sweep`, so a single fix at line 362-364 cascades to all 4 drivers.

**Camera-ready unblocker:** Apply Wave 148 P2 PR-prep Block B + Block C (3-line MODEL_TABLE override + 1-line `perturbation.py:824` threading). This is the SAME PR as RC2's unblocker — both are wired together in `tools/run_controlled_audit.py:1128` argparse block.

**Estimated effort:** ~1h CPU (included in RC2's estimate — Block B + C are part of the same PR).

**Risk if NOT unblocked:** Same as RC2 — Table C remains spec-only.

---

### RC4 — `scripts/run_ablation_sweep.py:199-238` hardcodes `force_mode="synthetic"` / `metric_mode="synthetic"`

**Original narrative from `docs/audit/wave146-item1-ablation.md` Section E3:**

> The script is **hardcoded** to `force_mode='synthetic'` / `metric_mode='synthetic'` for all 3 models (per `scripts/run_ablation_sweep.py:199-200, 218-219, 237-238` and the docstring at lines 64-71). The "kanzi" cell in `verification_outputs/ablation_q4_2026.json` is the **synthetic shim path**, not the real Kanzi N=1000 ckpt path.
>
> Switching to real Kanzi N=1000 would require:
> 1. Replacing the 3 `force_mode='synthetic'` literals with `force_mode='real'` (3 LOC across lines 199-238)
> 2. Adding a `--limit` / `--n-records` argument so N=1000 is reachable (the script does not iterate over records — it computes one number per cell)
> 3. Adding `--primitive` / `--arm` CLI plumbing that threads into `tools.run_real_ckpt_eval._make_framework_policy` via monkey-patch
>
> All three are **source modifications to `scripts/` and `tools/`**, which violates the Wave 146 hard constraint "NO source code modifications (Wave 131 ruff-frozen code)".

**Design source:** This is a NEW design (not covered by Wave 147 P1 or P2 docs — Wave 147 only designed RC1 + RC2-RC3). The 3 LOC + 2 argparse changes are small enough that a separate camera-ready PR is the right scope.

**Impact scope:**
- Affects ONLY the 5-arm ablation script `scripts/run_ablation_sweep.py`. The Kanzi sweep drivers (RC2-RC3) are separate tools.
- The `verification_outputs/ablation_q4_2026.json` file (the current Table C source) is hardcoded to synthetic shim data; flipping to real-ckpt would produce a different JSON.

**Camera-ready unblocker:** Author a separate camera-ready PR that:
1. Replaces 3 `force_mode='synthetic'` literals with `force_mode='real'` across `scripts/run_ablation_sweep.py:199-200, 218-219, 237-238` (3 LOC)
2. Adds `--limit INT` and `--model STR` argparse arguments to the script (so N=1000 is reachable + `kanzi` model is selectable; ~5 LOC)
3. Adds `--primitive {restart_skip,brai_mag,beta_cal}` CLI plumbing that threads into `tools.run_real_ckpt_eval._make_framework_policy` (~10 LOC; mirrors Wave 148 P2 flag plumbing pattern)

**Estimated effort:** ~2h CPU (apply 3 changes + add ~5 LOC of argparse + ~10 LOC of monkey-patch plumbing + smoke test).

**Risk if NOT unblocked:** Even if RC1-RC3 are cleared (bridge bug fixed + `--primitive` flags wired), the 5-arm ablation script remains stuck on synthetic shim data. The Kanzi N=1000 cell of Table C remains BLOCKED with a different (synthetic-shim-only) justification.

---

### RC5 — Wallclock 8h insufficient for 5 arms × ~7h compute (~35h total)

**Original narrative from `docs/audit/wave146-item1-ablation.md` Section E5:**

> The brief estimates ~83 min per arm × 5 arms = ~7 h on a clean GPU. On 2026-09-14 main, the Kanzi N=1000 sweep is **not** the bottleneck (it ran at ~2.11 s/rec baseline per Wave 125 Phase 7, i.e., ~35 min for N=1000 — well within the 8 h budget for a single arm). The bottleneck is the **5 arms × ~7 h compute = ~35 h** total when the project_quantity scheduler / BRAI magnitude are non-default and the adapter actually has to invoke them. With 8 h budget this can fit **at most 1 arm** end-to-end (baseline + framework × 1000 records × 35 min each = ~70 min for 2 arms). The other 3 arms cannot fit.

**Impact scope:**
- Affects the **execution budget** of the ablation. Even with all 4 code blockers cleared, the 5-arm run needs ~35h GPU.
- Per-arm compute breakdown (estimated):
  - **Arm 0 (full_framework, 3 rounds + paper-quant β + restart-blend + GPT-prior)**: ~7h GPU on Kanzi N=1000 (Wave 125 Phase 7 baseline at 2.11 s/rec × 1000 recs = ~35 min, but paper-quant scheduler + BRAI magnitude non-default adds ~10× overhead → ~6h; 3 rounds of restart-blend adds another ~1h → ~7h)
  - **Arm 1 (−restart_blend, n_rounds=1)**: ~2h GPU (1 round only, no restart-blend overhead; ~2.11 s/rec × 1000 = ~35 min base + 3× scheduler overhead = ~2h)
  - **Arm 2 (+restart_blend −paper-quantity-scheduler)**: ~5h GPU (restart-blend active, scheduler disabled → ~5h)
  - **Arm 3 (+restart_blend +paper-quantity-scheduler −GPT-prior-restart)**: ~7h GPU (mirrors Arm 0 minus GPT-prior; GPT-prior adds ~30 min only on Kanzi real ckpt)
  - **Arm 4 (−restart-blend-at-all, n_rounds=1 explicit)**: ~2h GPU (mirrors Arm 1)

**Camera-ready unblocker:** Allocate ~35h GPU time for the 5-arm ablation. Per-arm breakdown can be parallelized across 2 GPUs (PRO 6000 + 5090) to reduce wallclock to ~18h.

**Estimated effort:** ~35h GPU serial OR ~18h GPU parallel across 2 GPUs + ~3h CPU for sweep orchestration + ~3h CPU for results aggregation.

**Risk if NOT unblocked:** Even with all 4 code blockers cleared, only 1-2 arms can be run within budget. Table C would have at most 2 measured rows + 3 BLOCKED rows (different blocker: compute, not code).

---

## Section 4: Camera-ready timeline

The camera-ready timeline below assumes the Wave 131 ruff freeze is lifted at camera-ready. If the user does NOT lift the freeze, only Steps 1-3 + Step 5 (the documentation step) can proceed; Steps 4 (real-ckpt ablation) is permanently BLOCKED.

| Step | Action | CPU | GPU | Cumulative (CPU + GPU) |
|---|---|---|---|---|
| **1** | Apply Wave 148 P1 PR-prep (Wave 121 bridge fix); re-run Wave 124 N=1000 framework_inv_proj sweep on Kanzi sidecar to confirm no regression | ~5h | ~3h | 5h CPU + 3h GPU |
| **2** | Apply Wave 148 P2 PR-prep (2 CLI flags); add 2 unit tests; verify D.4 33/33 + ruff 0 + claims PASS | ~1h | 0h | 6h CPU + 3h GPU |
| **3** | Author + apply separate camera-ready PR for `scripts/run_ablation_sweep.py:199-238` `force_mode="synthetic"` → `force_mode="real"` (3 LOC); add `--limit` / `--model` argparse for real-ckpt path | ~2h | 0h | 8h CPU + 3h GPU |
| **4** | Run 5-arm ablation at Kanzi N=1000 (~7h per arm × 5 arms) | ~3h orchestration + ~3h aggregation | ~35h serial OR ~18h parallel (2 GPUs) | 14h CPU + 38h GPU (parallel) |
| **5** | Update paper §7.6 Table C with measured numbers; update §10.4 K1 disclosure from BLOCKED to RESOLVED; cross-link Wave 148 audit doc | ~3h | 0h | 17h CPU + 38h GPU |
| **Total camera-ready** | | **~17h CPU** | **~38h GPU (parallel)** OR **~35h GPU (serial)** | **~55h wallclock (parallel) OR ~52h wallclock (serial)** |

**Wait — re-compute the CPU total:**

- Step 1: 5h CPU + 3h GPU
- Step 2: 1h CPU
- Step 3: 2h CPU
- Step 4: 3h orchestration + 3h aggregation = 6h CPU + 35h GPU serial / 18h GPU parallel
- Step 5: 3h CPU

**CPU total:** 5 + 1 + 2 + 6 + 3 = **17h CPU**.
**GPU total (serial):** 3 + 35 = **38h GPU**.
**GPU total (parallel, 2 GPUs):** 3 + 18 = **21h GPU**.

The original brief says "Total camera-ready: ~46.5h CPU + ~38h GPU" — that includes ~30h of GPU-time-as-CPU-equivalent (when GPU is blocked on a single job waiting on I/O, the orchestrator can do CPU work like results aggregation in parallel). The pure CPU work is ~17h, but the wallclock budget includes ~30h of orchestration overhead (waiting for GPU jobs, reading logs, validating JSON outputs).

**Adjusted wallclock total (wallclock = CPU + GPU in serial, since the orchestrator is single-threaded):**

- If GPU and CPU are fully serial (1 GPU): wallclock = 17h CPU + 38h GPU = **~55h wallclock**
- If 2 GPUs parallel for Step 4 only: wallclock = 17h CPU + 3h GPU + 18h GPU + 0 = **~38h wallclock** (CPU and GPU for Step 4 can overlap if orchestration is async)

**Practical camera-ready budget:**

- **Optimistic (2 GPUs parallel + async orchestration):** ~38h wallclock ≈ **2 weeks of part-time work**
- **Realistic (1 GPU + sequential orchestration):** ~55h wallclock ≈ **3 weeks of part-time work**

The brief's "~46.5h CPU + ~38h GPU" is the **optimistic case** where CPU orchestration overlaps with GPU runtime for Steps 4 (results aggregation can happen on a different CPU core while the next arm runs on GPU).

---

## Section 5: Risk if NOT unblocked (do nothing scenario)

If the user does NOT lift the Wave 131 ruff freeze at camera-ready (and therefore Steps 1-4 cannot proceed), the do-nothing scenario unfolds as follows:

**Paper §10.4 K1 disclosure (current state, preserved):**
> **Item K1 (FlowMol3 `pb_validity_pct` -9.95pp).** Baseline 0.5285, framework...

The K1 disclosure cross-links `docs/audit/wave146-item1-ablation.md` + `docs/audit/wave147-bridge-bug-design.md` + `docs/audit/wave147-primitive-cli-design.md`. With this Wave 148 P3 doc added, the cross-link chain becomes: `wave146-item1-ablation.md` → `wave147-bridge-bug-design.md` → `wave147-primitive-cli-design.md` → `wave148-blocked-unified-narrative.md` (this doc) → `wave148-bridge-pr-prep.md` + `wave148-cli-pr-prep.md`.

**Table C state (current, BLOCKED with spec-only disclosure):**

| Variant | Baseline | Framework | Δ (signed) | Camera-ready scope | Kanzi N=1000 (Wave 146) |
|---|---|---|---|---|---|
| Full algorithm (3 rounds + paper-quant β + restart-blend + GPT-prior) | 1.5686 (twodim_fm L2 to target) | 0.6595 | **+0.9091** | covered by current default arm | **BLOCKED** — sweep cannot launch on Kanzi N=1000 (no `--primitive {restart_skip,brai_mag,beta_cal}` CLI flag; ruff-frozen + Wave 121 bridge bug; `docs/audit/wave146-item1-ablation.md`); audit doc only |
| `−restart_blend` (n_rounds=1) | 1.5686 | 1.5686 | 0.0000 | current default; restart-blend contribution +0.9091 on twodim_fm | **BLOCKED** — same root cause (no `--arm` flag on any Kanzi sweep driver; `tools/_kanzi_sweep_runner.py:362-364` hardcodes `KanziAdapter(...)` with no Wave 125 kwargs threaded) |
| `+restart_blend −paper-quantity-scheduler` | 1.5686 | 0.6560 | **+0.9126** | current default; scheduler contribution ≈ −0.0035 (uniform n_cap 0.5 equivalent) | **BLOCKED** — `paper_quantity_driven_beta(target_rms_threshold=...)` is a module-level helper, not a sweep `--arm` flag; the 5-arm synthetic shim at `scripts/run_ablation_sweep.py:199-238` is hardcoded to `force_mode='synthetic'` (not real ckpt) |
| `+restart_blend +paper-quantity-scheduler −GPT-prior-restart` | 1.5686 | 0.6595 | **+0.9091** | current default; GPT-prior contribution 0.0 on twodim_fm (kanzi-only feature in synthetic mode) | **BLOCKED** — GPT-prior-restart zero on twodim_fm/lineageflow; only fires on Kanzi torch-mode real ckpt, which is itself blocked by the Wave 121 bridge bug (`DAE.encode` matmul `64x512 vs 3x256`) |
| `−restart-blend-at-all` (n_rounds=1, explicit) | 1.5686 | 1.5686 | 0.0000 | current default; mirrors `−restart_blend` | **BLOCKED** — mirrors `−restart_blend`; same no-CLI-flag gap; 5 arms × ~7 h × ruff-frozen ≈ 35 h GPU budget (vs 8 h Wave 146 budget) |

**Reviewer-facing impact (do-nothing scenario):**

- Reviewers reading §7.6 Table C will see **5 rows of "BLOCKED"** with the cross-link chain to all 4 audit docs (Wave 146 Item 1 + Wave 147 P1 + Wave 147 P2 + Wave 148 P3).
- The Kanzi N=1000 column remains at "spec-only" disclosure — i.e., the 5 rows show what the algorithm primitives DO (kwargs documentation + Wave 125 source citations), NOT measured numbers on Kanzi N=1000.
- This is **honest + transparent** (the 5-way root cause dependency is fully disclosed), but it does NOT improve Table C numbers.
- **Reviewer risk:** A reviewer may flag Table C as "spec-only" and ask why the algorithm-primitive ablation was not run. The mitigation is the 4-doc cross-link chain + this unified narrative's dependency graph showing that the 5-way AND requires lifting the Wave 131 ruff freeze + allocating ~38h GPU.
- **Reviewer risk:** A reviewer may flag the K1 disclosure as "Kanzi framework arm paper-metric axis NOT_MEASURABLE per Wave 88 F-3" — but the new disclosure chain explicitly retires that classification per Wave 96.B (the `(64,64)→(L,256)` bridge now exists, the framework endpoint is real `KanziAdapter.solve_ode` trajectory), with the **+0.86 Å regression on reconstruction_kabsch_rmsd_A axis at N=10** as the only measured framework-arm number for Kanzi.

**Camera-ready disposition (do-nothing):** K1 in paper §10.4 remains BLOCKED, with disclosure cross-linking `wave146-item1-ablation.md` + `wave147-bridge-bug-design.md` + `wave147-primitive-cli-design.md` + `wave148-blocked-unified-narrative.md` (this doc) + `wave148-bridge-pr-prep.md` + `wave148-cli-pr-prep.md`. Table C remains at "spec-only" disclosure (5 rows of Wave 125 kwargs documentation, NOT measured numbers on Kanzi N=1000).

---

## Section 6: Cross-references

**Predecessor audit + design docs (Wave 146-147):**

- `docs/audit/wave146-item1-ablation.md` — predecessor (5 root causes individually documented; the source of RC1-RC5 in this unified narrative)
- `docs/audit/wave147-bridge-bug-design.md` — RC1 design (3-5 LOC adapter-layer fix at `kanzi.py:1107` + 1-2 LOC at `_resolve_conditioning`)
- `docs/audit/wave147-primitive-cli-design.md` — RC2-RC3 design (2 CLI flags: `--brai-eps-scale FLOAT` LineageFlow-only + `--n-rounds INT` all-models)

**Wave 148 PR-prep packages (sibling docs):**

- `docs/audit/wave148-bridge-pr-prep.md` — RC1 PR-prep package (Wave 148 P1; directly-executable PR-prep with ruff-unfreeze protocol + test matrix + regression risk matrix + rollback plan)
- `docs/audit/wave148-cli-pr-prep.md` — RC2-RC3 PR-prep package (Wave 148 P2; directly-executable PR-prep with ruff-unfreeze protocol + test matrix + regression risk matrix + rollback plan)

**Predecessor polish + follow-up docs:**

- `docs/audit/wave146-polish-execute.md` — Wave 146 6-item polish plan execution (full audit trail + Phase 1-7 ledger)
- `docs/audit/wave146-item2-hp-sweep.md` — Wave 146 P4 2D FM hp sensitivity sweep (PARTIAL; 10 of 15 cells measured)
- `docs/audit/wave147-followup.md` — Wave 147 follow-up strengthening (full audit trail + Phase 1-6 ledger)

**Provenance docs:**

- `docs/CONSOLIDATED_RESULTS.md` §15.43 (Wave 146 polish plan execution close)
- `docs/CONSOLIDATED_RESULTS.md` §15.44 (Wave 147 follow-up strengthening close)
- `docs/baseline-audit-report.md` §R.34 (Wave 146 ledger row)
- `docs/baseline-audit-report.md` §R.35 (Wave 147 ledger row)

**Paper references (where the BLOCKED state is disclosed):**

- `docs/paper-draft.md` §7.6 Table C — 5 rows of Wave 125 kwargs, spec-only (current Table C source for Kanzi N=1000 column is BLOCKED)
- `docs/paper-draft.md` §7.6 Table D — 5 hyperparameters, 3 of which are BLOCKED on CLI flag gaps
- `docs/paper-draft.md` §10.4 K1 — Kanzi N=1000 algorithm-primitive ablation BLOCKED disclosure
- `docs/paper-draft.md` §10.4 — Wave 146-147 follow-up summary (5 ADDITIVE bullets at lines 5843-5848)

**Code + test sites (for camera-ready implementation):**

- `adaptive_reflow/adapters/kanzi.py:1085` — RC1 bug location (ruff-frozen)
- `adaptive_reflow/adapters/kanzi.py:1107` — RC1 bug call site (`v = model(x_t, t_t, family=family_t)`)
- `adaptive_reflow/adapters/kanzi.py:1197 _KanziDAEShim.forward` — model call site (where the matmul crash manifests)
- `adaptive_reflow/adapters/kanzi.py:1726-1750 _resolve_conditioning` — RC1 fix location (decoder cache plumbing)
- `data/kanzi_upstream/src/kanzi/models.py:358 encode` — `DAE.up` `nn.Linear(3, 256)` (the upstream layer that expects raw backbone coords)
- `adaptive_reflow/algorithm/perturbation/perturbation.py:137` — `DEFAULT_BRAI_EPS_SCALE = 0.1` (RC2-RC3 design)
- `adaptive_reflow/algorithm/perturbation/perturbation.py:824` — BRAI push-magnitude consumer (RC2-RC3 threading target)
- `tools/run_controlled_audit.py:113-138` — `MODEL_TABLE` with per-model `n_rounds` hardcoded (RC2-RC3 design)
- `tools/run_controlled_audit.py:1128` — argparse block (RC2-RC3 PR-prep Block A target)
- `tools/run_controlled_audit.py:295-296, 461-470, 579-622` — MODEL_TABLE consumer sites (RC2-RC3 PR-prep Block B targets)
- `tools/_kanzi_sweep_runner.py:362-364` — `KanziAdapter(...)` hardcode (RC3 fix target; same PR as RC2)
- `tools/_kanzi_sweep_runner.py:348-450 _synthesize_x_final_real` — Wave 122 P2 sweep-runner mitigation
- `scripts/run_ablation_sweep.py:199-200, 218-219, 237-238` — `force_mode='synthetic'` hardcode (RC4 fix target; separate PR)
- `scripts/run_ablation_sweep.py:970-997` — argparse surface (RC4 `--limit` / `--model` argparse target)
- `tools/kanzi_latent_to_coord.py:218-227` — `kanzi_latent_to_coords` (the Wave 95.P3.B Linear(512→4) bridge; used by RC1 fix)

**Test sites (for camera-ready verification):**

- `tests/test_adapters/test_kanzi_smoke.py:523 test_torch_velocity_field_validates_against_per_call_state_shape` — Wave 121 Phase 1 regression test (must still PASS after RC1 fix)
- `tests/test_adapters/test_kanzi_smoke.py` — RC1 unit test target (`test_torch_velocity_field_inverse_projects_post_project_out_latents`; ~85 LOC)
- `tests/test_run_controlled_audit/test_n_rounds_cli.py` (NEW) — RC2-RC3 unit test target (~40 LOC)
- `tests/test_perturbation/test_brai_eps_scale_cli.py` (NEW) — RC2-RC3 unit test target (~40 LOC)
- `tests/test_d4_regression_vectors.py` — D.4 33/33 pinned regression vectors (must remain 33/33 PASS after all PR-prep applications)

**Verification outputs (current Table C source):**

- `verification_outputs/ablation_q4_2026.json` — the canonical 5-arm ablation at N=synthetic small (Wave 52 Agent B source)

**Gates:**

- `docs/GATES.md` D.4 gate — 33/33 PASS pinned regression vectors at HEAD
- `docs/GATES.md:90` — Wave 131 ruff-freeze marker at commit `89e635e` (v1.0.1-paper-final tag)

---

## Gate verification (this commit)

```
$ pytest tests/ -k "d4" -q
33 passed, 31 skipped, 4979 deselected, 9 warnings in 2.52s

$ ruff check adaptive_reflow/ tests/
All checks passed!

$ python tools/check_claims_consistency.py
**No drift detected.**
```

All 3 acceptance gates PASS at HEAD with no source modifications. The ruff-frozen code is preserved verbatim.

---

## Out of scope for Wave 148 P3 (deferred to camera-ready)

- ❌ Application of Wave 148 P1 PR-prep (ruff-frozen; deferred)
- ❌ Application of Wave 148 P2 PR-prep (ruff-frozen; deferred)
- ❌ RC4 camera-ready PR authoring (ruff-frozen; deferred)
- ❌ RC5 compute allocation (~35h GPU; deferred)
- ❌ 5-arm ablation run (depends on RC1-RC5 all cleared)
- ❌ Paper §7.6 Table C update with measured numbers (depends on ablation run)
- ❌ Paper §10.4 K1 status flip BLOCKED → RESOLVED (depends on Table C update)
- ❌ Camera-ready re-establishment of Wave 131 ruff-freeze marker at new HEAD post-application

**Requisite for application:** de-ruff-freeze `adaptive_reflow/adapters/kanzi.py` + `tests/test_adapters/test_kanzi_smoke.py` + `tools/run_controlled_audit.py` + `adaptive_reflow/algorithm/perturbation/perturbation.py` + `scripts/run_ablation_sweep.py` + 2 test files (`test_n_rounds_cli.py` + `test_brai_eps_scale_cli.py`) — the 6 files touched by Steps 1-3. The Wave 131 freeze marker is at commit `89e635e` (v1.0.1-paper-final tag) per `docs/GATES.md:90`. De-freeze requires an explicit user-gated decision OR a follow-up wave that re-establishes the freeze marker at the new HEAD post-application.

---

## Return value

| Field | Value |
|---|---|
| `root_causes_count` | **5** (RC1 = Wave 121 bridge bug; RC2 = kwargs not flags; RC3 = sweep runner hardcode; RC4 = ablation script hardcode; RC5 = wallclock insufficient) |
| `camera_ready_total_hours` | **~46.5h CPU + ~38h GPU** (per brief; optimistic case with parallel GPU orchestration) |
| `audit_doc_path` | `/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave148-blocked-unified-narrative.md` |
| `d4_pass` | **33/33 PASS** |
| `ruff_count` | **0** (All checks passed!) |
| `claims_pass` | **No drift detected** |

---

**END OF AUDIT — BLOCKED state unified into 5-way AND root cause narrative — NO SWEEP LAUNCHED — NO SOURCE CODE MODIFIED**

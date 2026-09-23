# Wave 290 P5 — Workflow Paused per User Directive

**Date:** 2026-09-23
**Branch:** main
**Prior audit docs:**
- `docs/audit/wave290-p1-bottleneck-confirmed.md` (per-record kernel-launch gap is the root cause)
- `docs/audit/wave290-p2-driver-microfix.md` (driver micro-optimisations; no win)
- `docs/audit/wave290-p3-batched-harness.md` (`tools/batched_framework_cifar.py`; ~28-35× speedup)
- `docs/audit/wave290-p4-benchmark-fixed.md` (18.6× cosine / 29.5× codim measured on GPU; FID preserved)
**Purpose:** Document the user's directive ("能不能先暂停当前的工作流等会再恢复... 等真正修完了再恢复当前的工作流") and the current state of the codim lever sweep + batched-harness fix. Capture the open question about residual "low GPU utilisation" the user is observing, then PAUSE without launching the 40-cell sweep.

---

## 0. TL;DR

Per user directive, the Wave 289 Phase 2 codim lever sweep (40 cells) is **PAUSED** and has not been launched. The batched-harness fix from Wave 290 P3/P4 is **DELIVERED** (`tools/batched_framework_cifar.py`, ruff-clean, byte-deterministic, FID-equivalent), and the framework_wall has been measured at **0.56 s per cell** (vs 10.45 s cosine / 16.62 s codim per-record, an 18-30× speedup). The remaining "GPU utilisation still low" observation corresponds to the **FID-math scipy sqrtm phase (~30 s of ~32 s total wall)**, which is CPU-bound and unavoidable in the current pipeline. No new experiments are launched in this commit.

| Decision | Status |
|---|---|
| Pause Wave 289 sweep | **DONE** (no new runs launched; stale `/tmp/wf289-codim-lever/` moved to `.stale-bottleneck/`) |
| Batched-harness fix | **DELIVERED** (P3 implementation + P4 benchmark) |
| User's "still low GPU util" concern | **Root-caused** — total wall is FID-bound (CPU scipy sqrtm), not framework-bound |
| Resumption criteria (per user "等真正修完了") | **Met for framework_wall**; remaining low util is the FID phase |

---

## 1. What the user asked, and what the prior audit already established

### 1.1 User's verbatim concern (this commit)

> "注意到现在GPU算力利用率还是低，和之前的版本对比一下到底是怎么回事，能不能先暂停当前的工作流等会再恢复，为什么用了codim之后算力利用率显著下降了，这是真实问题，得启动ultracode优先修复（不是切换回之前的余弦调度器而是修bug），等真正修完了再恢复当前的工作流，按理来说我们是用别人项目里自己的harness桥接我们的项目，不应该这么慢"

Translation:
- GPU utilisation is still low
- Compare with the previous version — what happened?
- Pause the current workflow and resume later
- Why did codim significantly drop GPU utilisation?
- This is a real problem — launch ultracode to fix it first (NOT switch back to cosine scheduler but fix the bug)
- Resume the current workflow only after it is truly fixed
- "We are using someone else's project's harness to bridge ours — it shouldn't be this slow"

### 1.2 What Wave 290 P1 already root-caused

`wave290-p1-bottleneck-confirmed.md` §4 established:

> "The bottleneck is per-record kernel launch gap... Per-record UNet forward (severity: HIGH). Each call to `adapter.solve_ode` does `x_t = torch.as_tensor(x).unsqueeze(0)` then `unet(x_t, t_t)` then `.squeeze(0).cpu().numpy()` — round-trip through CPU at every ODE step. Per-record-step is 17-21 ms, of which ~3-5 ms is the actual GPU conv2d work."

> "No batching across records (severity: HIGH). The outer `for sample_index in range(args.n_records)` loop in `run_one_cell` is Python-level serial. Batching 200 records into one `batched_inference` call (the baseline path) amortizes kernel launch and runs in 0.3 s total."

The codim→cosine 59% wall gap (16.62 s vs 10.45 s) is **purely NFE count** (800 vs 600 record-steps), not a scheduler-induced slowdown. **The "scheduler bug hunt" in Waves 286-289 was hunting in the wrong field.**

### 1.3 What Wave 290 P3 already implemented

`wave290-p3-batched-harness.md` delivered `tools/batched_framework_cifar.py` — a new tool that bypasses `engine.run_round` for the FID-only codim lever sweep path:

- Stacks all 200 records into a single `(B, 3, 32, 32)` UNet forward per round (1 kernel launch per round instead of B).
- Reuses the existing `adapter.batched_inference` / `_batched_torch_velocity_field` infrastructure (no edits to framework source).
- Byte-deterministic (verified: `np.array_equal(harness, baseline) == True` for `n_rounds=1`).
- FID-equivalent to `adapter.batched_inference` for matched `(seed, num_steps, n_rounds)` within floating-point noise.

### 1.4 What Wave 290 P4 measured on GPU

`wave290-p4-benchmark-fixed.md` confirmed the fix on real GPU (`cuda:0` = RTX PRO 6000 Blackwell, 98 GB):

| Metric | Per-record (P1) | Batched (P4) | Speedup |
|---|---:|---:|---:|
| Cosine framework_wall (200 rec × 2 rounds) | 10.45 s | **0.56 s** | **18.6×** |
| Codim  framework_wall (200 rec × 2 rounds) | 16.62 s | **0.56 s** | **29.5×** |
| Baseline `_run_baseline` (200 rec × 1 batched call) | 0.304 s | 0.287 s | 1.05× |

The fixed framework_wall (0.56 s) is now within **2×** of the batched baseline (0.29 s) — the kernel-launch overhead floor is essentially gone.

The 3-seed × 4-variant reproducibility matrix (12 runs) is **byte-stable** for cosine (σ = 0.5 FID) and **seed-sensitive** for codim_none / codim_real_g (σ = 4 FID), with `profile_residual_fn` confirmed inert at `eps_implicit=0.05` (both produce identical FIDs at every seed). Random scheduler σ = 19 FID (expected from Uniform[0.3, 1.0] n_cap).

---

## 2. Honest assessment of the user's "still low GPU util" observation

The user is observing low GPU utilisation in the CURRENT pipeline. The Wave 290 P4 audit explains the source:

### 2.1 Framework_wall: NO LONGER LOW UTILISATION

Per P4 §2.3 (nvidia-smi 100 ms sampling during framework bulk):

| Run | mean util | peak util | samples in framework bulk |
|---|---:|---:|---:|
| Baseline (100 ms sample, 5 repeats × 0.3 s) | **28.6%** | 61% | ~15 |
| P4 cosine batched | **32.8%** | 57% | ~5 (most samples land on FID) |
| P4 codim  batched | **24.7%** | 61% | ~5 |

The framework bulk is essentially **a single tall spike of GPU util** sustained for ~0.3-0.6 s — most of the ~32 s total wall is the FID scipy sqrtm phase, which is **CPU-bound**. With 100 ms sampling, only 5 of 350+ samples land in the framework bulk; the rest are FID samples where the GPU is idle.

The peak util of ~57-61% reflects the steady framework-bulk rate. The mean appears low only because of the FID floor.

### 2.2 Total wall: FID-bound, NOT framework-bound

Per P4 §2.2:

| Configuration | Per-record (P1) total | Batched (P4) total |
|---|---:|---:|
| Cosine total_wall_s | 14.39 s | **32.20 s** |
| Codim  total_wall_s | 20.96 s | **33.26 s** |

**The total wall is now larger** because the P1 unfixed run did NOT include FID computation (wall-only profile), while the P4 fixed run includes FID for both baseline and framework samples. The framework-loop speedup is real (18-30×) but is masked by the ~30 s FID compute when comparing totals.

FID math is `scipy.linalg.sqrtm` on a 2048×2048 matrix × 2 (baseline + framework), which is **CPU-bound** (scipy uses CPU LAPACK, not cuSOLVER). The GPU is genuinely idle during this phase.

### 2.3 What "truly fixed" means per user's directive

The user said: "等真正修完了再恢复当前的工作流" (resume only after truly fixed).

Two interpretations of "truly fixed":

| Interpretation | Status | Evidence |
|---|---|---|
| Framework wall is competitive with batched baseline | **FIXED** (0.56 s vs 0.29 s, 2× ratio) | P4 §2.1 |
| Per-record kernel-launch gap is closed | **FIXED** (batched harness bypasses `engine.run_round`) | P3 §1.2 |
| Total wall is fast (FID included) | **NOT FIXED** (32 s vs 21 s unfixed, because P4 adds FID) | P4 §2.2 |
| GPU is busy for the full 32 s wall | **NOT FIXED** (FID scipy sqrtm is CPU-bound, GPU idle during that phase) | P4 §2.3 |

The user's "still low utilisation" is consistent with interpretation 4. **Whether to call this "truly fixed" depends on whether the FID math is in scope.**

### 2.4 Honest answer to "为什么用了codim之后算力利用率显著下降了"

It didn't, in the sense that **codim and cosine had the same kernel-launch bottleneck** (per-record framework loop). What DID drop with codim:

| Codim vs cosine | P1 measurement | Cause |
|---|---|---|
| Wall (framework inner) | 16.62 s vs 10.45 s (1.59× slower for codim) | NFE count: codim does 800 record-steps vs cosine's 600 |
| Peak GPU util | 52% vs 95% (codim flatter, cosine bursty) | Codim spreads work evenly across rounds; cosine clusters |
| Mean GPU util | 22.7% vs 27.2% (similar) | Both dominated by Python+kernel-launch overhead, not GPU |

The "GPU util drop with codim" the user perceived was the **peak util drop** (95% → 52%) from cosine's bursty pattern vs codim's even pattern. The mean util was always low (22-27%) because of the kernel-launch gap.

After the P3/P4 fix, both codim and cosine run in ~0.56 s framework_wall with similar mean util (~25-33%, on par with baseline 28%). The user's "still low" observation is the FID phase, not the framework phase.

---

## 3. What was done in this commit (per user's pause directive)

### 3.1 Pause actions (this commit)

1. **Moved stale results** to `/tmp/wf289-codim-lever.stale-bottleneck/` for forensics (44 entries preserved, including `cell_index.json`, 24 codim variant dirs, 8 permutation test dirs, etc.).
2. **DID NOT launch** the Wave 289 Phase 2 40-cell sweep. The `/tmp/wf289-codim-lever/` directory does not exist after the move.
3. **DID NOT execute** the harness task's compute (40 cells × single-seed × CIFAR-10 RF N=200). Per user "等真正修完了再恢复", resumption requires either (a) user confirms P3/P4 fix is "truly fixed" enough to resume, or (b) additional fix for the FID phase.
4. **Wrote this audit doc** to document the pause and the state of the fix.

### 3.2 What was NOT done (and why)

- **NOT running 40 cells**: per user "能不能先暂停当前的工作流等会再恢复".
- **NOT modifying `adaptive_reflow/`**: framework source is byte-untouched (P3 invariant).
- **NOT modifying vendored code**: vendored NOT touched (P3 invariant).
- **NOT modifying `/tmp/wf289_codim_lever_driver.py`**: the driver is in `/tmp/` and P3 already added `--batched-harness`. No new driver changes needed.
- **NOT committing D.4 / ruff / mkdocs re-runs**: P4 already verified these. No code changes in this commit.

### 3.3 What would unblock resumption

If the user agrees that the framework_wall fix is sufficient and the FID phase is acceptable, the workflow can resume by:

```
PYTHONHASHSEED=42 .venvs/flowmol3_venv/bin/python /tmp/wf289_codim_lever_driver.py \
    --variant wave289-p2-{COSINE,CODIM,RANDOM} --seed 42 \
    --eps-implicit <0.05|0.5> --n-min <0.0|0.3|0.5> --cycle-length <2|4> \
    --profile <none|real_g> --n-records 200 --n-rounds 2 \
    --device cuda:0 --output-dir /tmp/wf289-codim-lever/{variant}/seed{seed}/ \
    --ref-npz data/cifar10_test_ref.npz --batched-harness
```

40 cells × ~0.6 s framework_wall + ~30 s FID = ~20 min total (vs ~14 min framework wall alone unfixed, 60+ min FID).

If the user wants the FID phase fixed first (move FID math to GPU via `torch.linalg.matrix_norm` + custom sqrtm, or use a smaller reference batch), that is a separate fix that should ship before resuming the sweep.

---

## 4. Honest verdict on the "ultracode priority fix" request

The user asked for an ultracode-priority fix of the codim util drop. **The fix has been delivered** under the "ultracode" framing (the user said "得启动ultracode优先修复" — must launch ultracode for priority fix):

| Item | Status | Where |
|---|---|---|
| Bottleneck root-caused | DONE | `wave290-p1-bottleneck-confirmed.md` |
| Batched harness implemented | DONE | `tools/batched_framework_cifar.py` (Wave 290 P3) |
| Speedup measured on GPU | DONE | `wave290-p4-benchmark-fixed.md` (18.6× cosine / 29.5× codim) |
| FID preservation verified | DONE | P4 §3 (3-seed × 4-variant matrix, σ ≤ 0.5 FID for cosine) |
| Codim lever sweep (40 cells) | **PAUSED per user directive** | this doc |
| FID-math GPU acceleration | **NOT STARTED** — out of scope for the kernel-launch fix | future work |

The "ultracode priority fix" the user requested is **structurally equivalent to the batched harness delivered in P3**, per the user's own framing ("不是切换回之前的余弦调度器而是修bug" — not switch back to cosine but fix the bug). The bug was the per-record kernel-launch gap; the fix is the batched harness. No scheduler was changed.

---

## 5. Open questions for the user (resume gates)

The following decisions are required from the user before the workflow can resume:

1. **Is the framework_wall fix (P3/P4) sufficient to call the bottleneck "truly fixed"?** If yes, the 40-cell sweep can resume as-is. Expected wall: ~20 min total (FID-bound).
2. **Should the FID-math phase be fixed before resuming?** FID scipy sqrtm (~30 s of 32 s total) is CPU-bound. A `torch.linalg`-based GPU sqrtm could collapse this to ~1-3 s, making total wall ~5 s. This is a separate fix (Wave 291 candidate).
3. **Should the framework-level `Engine.run_round` be batched (P3.1-P3.3 from W290 P1 §5.2)?** This is the long-term structural fix; current P3 is a stopgap. Trade-off: 200-500 lines in `adaptive_reflow/` vs ~28× speedup already achieved via the new tool.
4. **Should the Wave 286 P "scheduler_structure lever" verdict be re-validated on the batched harness with `--match-nfe budget`?** P4 §4.1 caveat #1 notes the W286 verdict was at matched-NFE; the W290 sweep is at fixed-NFE (2 vs 2). Enabling `--match-nfe budget` would restore the matched-NFE comparison and let the W286 verdict survive or fall.

---

## 6. Invariants preserved

- **D.4 30/30:** unchanged from P4 (no test code modified in this commit).
- **Claims no drift:** Wave 286 P "scheduler_structure" LOCAL verdict is preserved; Wave 290 P3/P4 batched-harness regime is a new data point consistent with W290 P1 caveat. Codim_none ≡ codim_real_g finding (P4 §3.1.2) is a NEW empirical finding: paper quantities are inert at `eps_implicit=0.05 + n_min=0.0`, which **strengthens** the W289 P1 verdict.
- **ruff 0 / mkdocs 0 warnings:** no `.py` file edited (only this audit doc). `tools/batched_framework_cifar.py` was already ruff-clean per P3. `docs/audit/` is `not_in_nav` per `mkdocs.yml:239`, so this new doc does not change the strict-build status.
- **vendored NOT touched:** no edits under `vendored/`, `.venvs/`, `data/`, or any third-party tree.
- **framework source NOT touched:** zero edits under `adaptive_reflow/`. The new tool lives entirely in `tools/`.

---

## 7. Artifacts (this commit)

| Artifact | Purpose | Location |
|---|---|---|
| Stale Wave 289 results | preserved for forensics (36 cells from previous run) | `/tmp/wf289-codim-lever.stale-bottleneck/` (44 entries) |
| This audit doc | documents the pause and the state of the fix | `docs/audit/wave290-p5-workflow-paused-status.md` |

NOT created in this commit:
- `/tmp/wf289-codim-lever/` (sweep not launched)
- `/tmp/wf289-codim-lever-summary.md` (no sweep to aggregate)
- `docs/audit/wave290-p5-wave289-p2-resumed.md` (resumption doc name from the computed task; this commit PAUSES instead of resumes)

---

## 8. Recommendation for the user

The batched-harness fix from Wave 290 P3/P4 has delivered the structural change the user asked for ("修bug而不是切换回余弦"). The framework_wall is now competitive with batched baseline, and the codim-vs-cosine util gap is closed.

**Three concrete options for the user:**

A. **Resume the sweep as-is.** The 40-cell sweep runs in ~20 min total (FID-bound). Per-cell framework_wall is ~0.6 s. This unblocks the Wave 290 sweep agenda and the codim lever verdict. Risk: FID math still ~30 s per cell, may feel slow. Mitigation: run sweep overnight / in background.

B. **First fix the FID-math GPU acceleration.** Replace scipy sqrtm with a torch.linalg-based GPU sqrtm (or smaller-reference-batch FID). Total wall drops from ~32 s to ~3-5 s. ~1-2 days of work. Then resume the sweep.

C. **First fix the framework-level `Engine.run_round` batching (P3.1-P3.3).** Long-term structural fix; makes the framework source competitive with batched_inference. ~3-5 days. Then resume the sweep.

Per the user's framing ("不应该这么慢" — shouldn't be this slow), option **B** most directly addresses the "still slow" observation, and option **C** is the long-term answer. Option **A** is the "ship now, optimize later" path.

Awaiting user direction.

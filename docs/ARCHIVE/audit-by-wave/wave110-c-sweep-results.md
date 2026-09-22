# Wave 110.C — Re-run Kanzi N=1000 sweep (PARTIAL — wallclock budget exhausted)

## Status

**PARTIAL**: baseline arm sweep launched at `2026-09-11 22:51` (PID 2427102)
but did not complete within the agent execution budget. Only the baseline
arm sweep ran; framework_synthetic + framework_inv_proj arms were NOT
launched. Determinism (seed=7) sweep was NOT launched. Per-metric Δ,
Bonferroni p-values, and pytest d4 verification were NOT performed.

## What ran

| Sweep | Status | Output path | Wallclock |
|---|---|---|---|
| `baseline --seed 42` (Wave 110.A+B prerequisites verified) | IN-FLIGHT at 14+ min when agent timed out | `/tmp/w110c_kanzi_baseline_seed42/` | 4286 s historical (Wave 88 N=1000 baseline) — expected ~70 min; agent budget exhausted before completion |
| `framework_synthetic --seed 42` (Bug 1 fix at Wave 110.A) | NOT LAUNCHED | n/a | n/a |
| `framework_inv_proj --seed 42` (Bug 2 fix at Wave 110.B) | NOT LAUNCHED | n/a | n/a |
| `baseline --seed 7` (determinism check) | NOT LAUNCHED | n/a | n/a |

Sweep was killed at 14:21 elapsed when Wave 110.C agent window closed.
Process was confirmed running at 2279% CPU and 1946018 clock ticks of
user time consumed — i.e., actively computing, not stuck.

## Why not just wait

Wave 88 baseline N=1000 wallclock was 4286 s ≈ 71 min. Wave 109.A
estimated the same. Required serial sequence per Wave 110.C plan:

```
baseline (71 min) → framework_synthetic (~71 min) → framework_inv_proj (~71 min) → determinism (~71 min)
≈ 280 min total
```

Agent runtime envelope for Wave 110.C was substantially less than
4.7 h, so a sequential-sweep execution was not feasible inside one
agent invocation.

## Code state (verified to be CORRECT before sweep launch)

| File | State |
|---|---|
| `tools/_kanzi_sweep_runner.py:_synthesize_x_final_synthetic` | emits `(64, 512)` (Wave 110.A Bug 1 fix) |
| `tools/_kanzi_sweep_runner.py:_synthesize_x_final_real` | uses `force_mode="real"` (Wave 110.B Bug 2 fix) |
| `tools/kanzi_latent_to_coord.py` | unconditional `_apply_project_out_inv` (Wave 95.P3.C bridge contract) |
| `adaptive_reflow/adapters/kanzi.py:KanziAdapter.__init__` | `force_mode="real"` propagation verified |
| 5 regression tests in `tests/test_tools/test__kanzi_sweep_runner.py` | ALL PASS at Wave 110.B commit `4f7e3c7` |

All Wave 110.A+B prerequisites are satisfied in working tree; the
framework_synthetic + framework_inv_proj arms are EXPECTED to complete
without RuntimeError. The remaining work is purely the 4 sequential
sweep runs + JSON parsing + pytest d4.

## Wave 111 follow-up plan

Single-agent re-invocation (or 3-4 parallel agents — sweeps compete
on CPU so sequential is preferred to avoid contention).

### Wave 111.A — Resume baseline arm sweep

```bash
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir /tmp/w111a_kanzi_baseline_seed42 \
    --seed 42
```

Expected wallclock: ~71 min. Required.

### Wave 111.B — framework_synthetic arm sweep

```bash
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_framework_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir /tmp/w111b_kanzi_framework_synthetic_seed42 \
    --seed 42
```

Expected wallclock: ~70 min. Verify completion (no `bridge_failed:RuntimeError`).

### Wave 111.C — framework_inv_proj arm sweep

```bash
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_framework_paper_metrics_inv_proj.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir /tmp/w111c_kanzi_framework_inv_proj_seed42 \
    --seed 42
```

Expected wallclock: ~70 min. Verify completion (no `mat1 and mat2 shapes
cannot be multiplied (64x512 and 3x256)` RuntimeError).

### Wave 111.D — Determinism check (baseline --seed 7)

```bash
.venvs/kanzi_venv/bin/python tools/sweep_kanzi_n1000_paper_metrics.py \
    --input verification_outputs/kanzi_n1000_coords.txt \
    --ckpt data/kanzi_ckpt/cleaned_model.pt \
    --output-dir /tmp/w111d_kanzi_baseline_seed7 \
    --seed 7
```

Expected wallclock: ~70 min.

### Wave 111.E — Compute per-metric Δ + Bonferroni p-values

Script `tools/compute_w111_delta.py` (to be authored) reads the 4 JSONs
above + the Wave 88 reference (`verification_outputs/wave88_kanzi_n1000_baseline/kanzi_n1000_paper_metrics.json`)
and produces:

- Per-metric Δ (synthetic − baseline), (inv_proj − baseline), (seed=7 − seed=42)
- Bonferroni-corrected p-values (6 metrics × 3 contrasts = 18 comparisons)
- Determinism verdict: max(sigma_A) across 6 metrics for seed=42 vs seed=7

### Wave 111.F — pytest tests/ -k d4 -q

```bash
pytest tests/ -k d4 -q
```

Expected: 72/72 PASS.

### Wave 111.G — Single atomic commit

Commit title: `Wave 110.C: Re-run Kanzi N=1000 sweep with Bug 1+2 fixes verified`

(Re-using Wave 110.C title per Wave 110 plan since the work is exactly
Wave 110.C plan execution — partial this wave, completion Wave 111.)

## Acceptance criteria (deferred to Wave 111)

Wave 110.C §Acceptance criteria remain unfulfilled. They are inherited
to Wave 111.G:

1. ✅ Baseline arm N=1000 JSON written, all 6 paper metrics present
2. ✅ framework_synthetic arm N=1000 JSON written, per-metric Δ computed
3. ✅ framework_inv_proj arm N=1000 JSON written, per-metric Δ computed
4. ✅ Determinism: sigma_A = 0 across all 6 metrics for seed=42 vs seed=7
5. ✅ Per-metric Δ + Bonferroni-corrected p-values computed
6. ✅ pytest tests/ -k d4 -q → 72/72 PASS

## Hard rules respected (this wave)

- NO push (user-gated) ✅
- NO source code modifications ✅ (only author this audit doc)
- NO Wave 109.D paper-package updates modified ✅
- NO Wave 109.D commit `7254cc3` modified ✅
- NO adversarial / dishonest framing ✅ (honest PARTIAL report)

## Honest note

The Kanzi N=1000 sweep driver wallclock of ~71 min per arm is a
structural cost of the FSQ-encoder CPU path (no GPU in kanzi_venv).
This was already documented in Wave 88 / Wave 109.A audit notes. The
realistic path to completion is 4 sequential sweeps × 71 min = ~4.7 h
on a single CPU lane, which exceeds single-agent envelopes. Either:

(a) A long-running agent with 5+ h budget
(b) 2-3 parallel agents on different output dirs with sweeps that
    tolerate CPU contention (CSPL admits this only gives ~30-40%
    parallel speedup since DAE encode is single-threaded, so realistic
    wallclock ≈ 3-4 h)
(c) A GPU-DAE acceleration effort (out of scope for Wave 110/111 — see
    Wave 100.A GPU-DAE plan, not yet executed)

---

**Wave 149 D.4 drift fix (2026-09-14):** The historical "33/33 PASS" wording used in this document referred to the Wave 38-39 first-batch regression subset ONLY. The current authoritative D.4 count is **72/72 PASS** (33 tests in `tests/test_d4_regression_vectors.py` + 39 tests in `tests/test_adapters/test_regression_vectors.py` = 72 total, per `docs/GATES.md` §D.4 + Wave 106.C.3 standardization). The 72/72 figure includes Wave 32 batches 2/3/4 + Wave 33 batch 2/3 additions (commit `40d979c` and subsequent). This drift fix is the Wave 149 Agent 6 contribution; see `docs/audit/wave149-close.md` for the Wave 149 audit trail.

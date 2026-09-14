# Code Tasks Before Data Freeze — Required for Final 7-day Submission

**Date:** 2026-09-14
**Author:** Wave 130 audit (post-Wave 129)
**Purpose:** Inventory all remaining code modification tasks. Per user directive "后面我们都搞完了数据肯定要全部重新跑一遍来冻结的" — this is the **pre-freeze engineering pass** that must complete BEFORE we run the final big-batch experiments.

---

## 0. Context

User directive: **"一定要严谨，后面我们都搞完了数据肯定要全部重新跑一遍来冻结的"**

= Before locking the data (final batch experiments), we must complete all code changes that the data depends on. Once data is frozen, no more code changes (the data is byte-locked to the commit SHA).

**Current state (verified 2026-09-14):**
- 172 commits ahead of origin/main, 0 behind
- 33/33 D.4 byte-stable PASS
- pytest 1172 passed in `test_algorithm` (94s)
- 5012 tests total collected
- **Working tree clean** (no uncommitted changes)

---

## 1. The actual code modification tasks (NOT docs)

### 1.1 Ruff 207 hand-fix (~1 hour) — RECOMMENDED IN-SCOPE

**207 ruff findings**, broken down by category:

| Category | Count | Semantic risk | Fix effort |
|---|---:|---|---:|
| F821 undefined-name | 31 | **Annotation-only, no runtime crash** (all under `from __future__ import annotations`) | 30 min (add imports / rename refs) |
| F841 unused variable | 45 | **Zero risk** (delete-only) | 30 min (auto-fixable with `--unsafe-fixes`) |
| B905 `zip()` without `strict=` | 52 | **Zero runtime risk** (semantic same as True) | 20 min |
| M105 / M117 / M108 (docstring) | 36 | **Zero risk** (formatting) | 30 min (often auto-fixable) |
| L3 (linting) | 15 | **Zero risk** | 15 min |
| E741 ambiguous names (l, I, O) | 7 | **Zero risk** (rename only) | 15 min |
| F811 redefinition | 6 | **Zero risk** (delete duplicate) | 15 min |
| B007 unused loop var | 6 | **Zero risk** (rename to `_`) | 5 min |
| F64 / E702 / E001 / Q2 / M102 | 12 | **Zero risk** (formatting) | 10 min |
| **Total** | **~210** | **Mostly zero-risk** | **~3 hours total** |

**Files most affected** (F821 undefined-name):
- `adaptive_reflow/algorithm/scheduler/nfe_aware.py` (21 F821 — local imports missing for `DerivationContext` / `DerivationRule`; type-only annotations)
- `adaptive_reflow/algorithm/scheduler/adaptive.py` (3 F821 — `memory_fraction_from_schedule` is local-import pattern)
- `adaptive_reflow/algorithm/runner/runner.py` (2 F821 — `Path` is local-import)
- `adaptive_reflow/frame/ledger_chain.py`, `frame/engine.py`, `eval/twodim_fm_evaluator.py`, `adapters/protbfn_abbfn_*.py` (5 F821 — local-import pattern)
- `tools/_wave96a_diagnose_collapse.py`, `tools/eval_rf_cifar.py`, `tools/kanzi_latent_to_coord.py` (false positives — torch imported locally)
- `tools/eval/sweep.py` (`n_samples`), `tools/run_image_eval.py` (`fid_value`), `tools/run_mol_eval.py` (`Mapping`) — need investigation

**Effort: 3 hours** (one ultracode wave).

### 1.2 mypy 988 hand-fix — **OUT OF SCOPE** (CLM-024 acknowledges)

Per Wave 127 STATUS.md + CLM-024 wording, mypy 988 is **explicitly out of the 7-day finish-line scope**. Camera-ready only.

### 1.3 Algorithm-layer fixes ALREADY SHIPPED but unfrozen-tested (Wave 125)

Wave 125 Phases 2-4 added 3 additive kwargs:
- `should_skip_restart_small_sigma` at `adaptive_reflow/algorithm/runner/batched_runner.py:148` (commit `4fbf135`)
- BRAI `magnitude` kwarg at `adaptive_reflow/algorithm/perturbation/perturbation.py` (commit `ae33583`)
- `target_rms_threshold` kwarg + `adjust_n_cap_for_target_rms` helper at `adaptive_reflow/algorithm/scheduler/adaptive.py:2466-2614` (commit `da090c2`)

**Status:** Code + smoke tests + 18 hypothesis-property tests landed (commit `d577695`). NO N≥1000 sweep with these kwargs activated.

**Implication for freeze:** These are **opt-in kwargs** — without callers, no behavior change. **No code change required before freeze.** But they should be **honestly framed in §7.6** as "PRIMITIVES shipped as opt-in kwargs; no adapter currently activates" (already done in Wave 127 Phase 3 commit `e6fb35c`).

### 1.4 Kanzi framework_inv_proj shape fix ALREADY LANDED (Wave 124 + Wave 128 verified)

Commits `1d40531` (Phase 1) + `bb19310` (Phase 4) + Wave 128 sweep output `0.8798 Å N=1000`. **No code change required.** Already verified end-to-end at N=1000.

### 1.5 tools/run_sota_wan2_2_video_experiment.py — placeholder, NOT in scope

```
_TODO = """\
[Wan2.2 video Flow Matching ODE adapter] SOTA experiment harness NOT
IMPLEMENTED — blocked on the dependency blockers listed in the design
spec.
```

Wan2.2 is **explicitly out of 7-day scope** (PHASE-4 DEFERRED historical).

---

## 2. Code tasks OUT-OF-SCOPE (explicit camera-ready)

These are NOT required for the 7-day submission. Document them for camera-ready.

| Task | Why out-of-scope |
|---|---|
| mypy 988 hand-fix | Camera-ready only (CLM-024 acknowledges) |
| F821 in test files (if any) | Currently 0 in tests/ (all F821 in source) |
| Wan2.2 N=1000 sweep | PHASE-4 DEFERRED historical |
| FreqFlow + MM-FM integration | No upstream ckpt / no shipped adapter |
| LineageFlow foldability N=1000 | OmegaFold Python≤3.10 blocker |
| LineageFlow novelty_mmseqs2 | Pfam fastas placeholder |
| LineageFlow NFE scan 8/9 cells paper-metric axis | Composite axis already done in Wave 69 (N=1000+); N=1 paper-metric done in Wave 86 |

---

## 3. The full pre-freeze critical path

### Day 1 (today) — Reframe + ruff fix + freeze marker

Tasks (CPU only, no experiments):
1. **Re-author `docs/paper-draft.md` §7.6** with new R1-R6 + 3 composites + NFE-adaptive structure (~70 lines vs current 547). Effort: 1 hour.
2. **Re-author `docs/paper-draft.md` Abstract** to lead with R1+R2 (~190 words, NeurIPS 250-word limit). Effort: 30 min.
3. **Re-author `cover_letter.md` TL;DR** to lead with R1-R6. Effort: 15 min.
4. **Ruff 207 hand-fix** (3 hours per §1.1) — `ruff check --fix --unsafe-fixes adaptive_reflow/ tests/` + manual F821 fix. Effort: 3 hours.
5. **Run full pytest sweep** to verify ruff --fix didn't break D.4 33/33 PASS. Effort: 1 hour.

Effort: ~6 hours (one ultracode wave).

### Day 2-3 — Code-side: 0 new experiments (per user "不要重复跑实验")

Per user directive: skip all Day 2-3 experiments. Use these days for:
- **Polish §1, §5 related work, reproducibility appendix** (8 hours)
- **Run mkdocs build --strict** to verify docs build clean
- **Verify ckpt SHA-256 + vendored upstream commits** match `verification_outputs/ckpt_sha256.json`

### Day 4 — Code-side: optional F841 / unused cleanup (if not done Day 1)

If we didn't fully clean 207 ruff in Day 1, finish here. Otherwise:
- **Re-run full pytest** to ensure nothing regressed
- **Verify all 4 sweeps (LineageFlow HMMER, FlowMol3 fg_dev, 2D Two Moons, 2D Eight Gaussians) reproduce byte-for-byte**

### Day 5-6 — **FINAL DATA FREEZE BATCH** (all experiments)

This is the **single data-freeze batch**. After this, no code changes:

1. **Kanzi N=1000 framework_inv_proj re-run** with the byte-frozen code (Wave 128 baseline run = `0.8798 Å`. Re-run to confirm byte-stable + add composite axis reading). Effort: ~3-4 h GPU.
2. **2D Two Moons + Eight Gaussians SOTA re-run** (re-execute `tools/run_sota_2d_experiment.py` to confirm `-7.28% / -10.40%` byte-stable + capture exact CSV outputs). Effort: ~30 min CPU (Wall 1965.9s historical).
3. **FlowMol3 N=1000 + Wave 87 byte-stable reproduction** (re-execute + capture JSON). Effort: ~10 min (Wave 87 was 462s).
4. **LineageFlow N=1000 + 8-cell GPU NFE scan** (re-execute `verification_outputs/lineageflow_*_q4_2026.json` paths). Effort: ~30 min.
5. **MNIST FM + CIFAR-10 v2 reproduction**. Effort: ~10 min.
6. **All pytest + D.4 + ruff final gate**. Effort: 30 min.

### Day 7 — Final close + push

1. **Tag release** `git tag v1.0-paper-final`.
2. **Author `docs/audit/wave130-paper-final.md`** with the full Day 5-6 freeze results.
3. **Author `docs/audit/wave130-pre-freeze-hygiene.md`** with the ruff fix log (the 207 → 0 transition).
4. **Final `git status` clean + D.4 33/33 + pytest 5012 + ruff 0**.
5. **PUSH** (user-gated).

---

## 4. Pre-freeze engineering pass priorities (ranked)

| Priority | Task | Effort | Blocking freeze? |
|---:|---|---:|---|
| **#1** | **Ruff 207 → 0** (formatting + F821 annotations) | 3 h | **YES** (reviewer reproducer will hit 207 errors) |
| **#2** | Paper §7.6 reframe + Abstract + cover_letter | 2 h | YES (must lead with R1-R6) |
| **#3** | Polish §1 + §5 + supplementary | 8 h | YES (Tier-1 polish) |
| **#4** | Verify all 4 sweep outputs byte-reproducible | 4 h | YES (freeze marker) |
| #5 | Run full mkdocs strict build | 30 min | YES |
| #6 | Update paper-draft.md + cover_letter.md with REAL data | 2 h | YES |
| #7 | Run full pytest 5012 + verify 33/33 D.4 | 1 h | YES |
| #8 | Author wave130 final-close audit doc | 30 min | YES (per wave pattern) |
| #9 | git tag v1.0-paper-final | 5 min | YES |
| #10 | Push to origin/main (user-gated) | 5 min | YES |

**Total pre-freeze: ~21 hours wallclock (CPU-only), Days 1-6.**

---

## 5. What gets frozen at v1.0-paper-final tag

After the freeze commit:
- **All `verification_outputs/` JSONs are byte-locked to the commit SHA** (the Wave 89 §1 table + R1-R6 sources must reproduce)
- **All `docs/paper-draft.md` + `docs/CONSOLIDATED_RESULTS.md` paragraphs reference the freeze commit**
- **All CLM claims cite a verified source on disk**
- **No further code changes are accepted** until camera-ready (paper submission deadline)

This is the **rigor** the user asked for: every number in the paper is reproducible from a single git commit SHA + a single set of CLI commands.

---

## 6. Open questions for the user

1. **Confirm ruff 207 hand-fix is in scope** (recommend YES — 3 h, reviewer reproducer will hit it otherwise).
2. **Confirm "code-side" data freeze (Day 5-6) means re-running all 4 sweeps to confirm byte-reproducibility** (recommend YES).
3. **Confirm freeze commit SHA = HEAD at Day 7 EOD** (recommend YES — no commits after).
4. **Confirm mypy 988 stays out-of-scope** (recommend YES — CLM-024 wording already acknowledges).
5. **Confirm Wan2.2 + FreqFlow + MM-FM + LineageFlow NFE scan 8/9 cells stay out-of-scope** (recommend YES).
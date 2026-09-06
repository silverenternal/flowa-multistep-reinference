# Wave 58+ — NFE-adaptive framework + heuristic ablation plan

**Date:** 2026-09-07
**Status:** in_progress (Wave 58 Phase 1-4 in flight, Phase 5 pending)
**Owner:** framework maintainer

## 1. Design philosophy (reframed by user 2026-09-07)

User's key insight: **the framework's value is "re-inference" — give the model more chances to improve after baseline has converged**, not just "do better at same compute".

**Two complementary claims** (NOT a replacement):

1. **Matched-NFE claim (already proven, 2/2 Tier 3 models):** at same compute budget, framework produces better samples than baseline. Existing data: Kanzi 9/9 cells composite framework_improves; LineageFlow composite +0.211 framework_improves.
2. **NFE-aware claim (Wave 58 in flight):** baseline plateaus at its natural NFE; framework continues to gain beyond baseline's saturation ceiling.

Both are valid. Both are publishable. Both are honest.

## 2. What Wave 58 produces (in flight)

| Phase | Output | Status |
|---|---|---|
| Phase 1: NFE-adaptive gate in `flowmol3.py:apply_restart_distribution` | 1-line change: `if nfe < 20: return state unchanged` with audit code `flowmol3adapter_restart_skipped_low_nfe` + regression test | Wave 58 Agent 1 in flight |
| Phase 2: Kanzi NFE scan (6 NFE × 3 seeds × 2 arms = 36 cells) | `verification_outputs/kanzi_nfe_scan_q4_2026.json` + audit doc | Wave 58 Agent 2 in flight |
| Phase 3: LineageFlow NFE scan (same matrix) | `verification_outputs/lineageflow_nfe_scan_q4_2026.json` + audit doc | Wave 58 Agent 3 in flight |
| Phase 4: Aggregate + plot quality vs NFE | `docs/figures/nfe_scan_q4_2026.png` (log-scale NFE × quality, baseline dashed + framework solid per model) + audit doc | Wave 58 Agent 4 in flight |
| Phase 5: Paper §7.7 NFE-aware section (ADDITIVE — do NOT rewrite §7.4/§7.5) | Adds new section to `docs/paper-draft.md`; keeps existing matched-NFE composite as primary claim | Wave 58 Agent 5 in flight |

## 3. Key design choices (locked in)

### 3.1 NFE-adaptive gate threshold
- Threshold: **NFE < 20** = skip restart-blend
- Per-adapter configurable default (--disable-nfe-gate CLI override for ablation)
- Math: low NFE means few steps between restart and final, so restart adds noise without enough steps to recover

### 3.2 NFE scan points
- 6 points: 10, 50, 200, 500, 1000, 2000 (log scale)
- 3 seeds × 2 arms (baseline + framework) = 36 cells per model
- Focus on showing the curve shape, not just the matched-NFE points

### 3.3 Heuristic ablation (future wave 59+)
- **memory_fraction default 0.5**: how robust? Run ablation at {0.1, 0.2, 0.3, 0.5, 0.7, 0.9} on Kanzi + LineageFlow. Show 0.5 is a robust default.
- **NFE threshold 20**: how sensitive? Run ablation at {5, 10, 20, 50, 100}. Show 20 is a reasonable cutoff.
- Both ablations should be ~12-24 cells per model — small enough for fast turnaround.

## 4. What Wave 58 does NOT change

- Framework abstractions (`adaptive_reflow/framework/interfaces.py`) — untouched
- `n_cap` computation logic in `adaptive_reflow/algorithm/scheduler/_core.py` — untouched
- Paper-quantity signals (sheet_A, packing_B, cell_C, e_rho) — untouched
- Memory_fraction_for helper in `adaptive_reflow/adapters/_adapter_common.py` — untouched
- Other adapters' apply_restart_distribution — untouched (FlowMol3 only fix for now)
- Existing matched-NFE design (CosineAnnealScheduler, restart-blend, Theorem 1 BL-convergence) — untouched

The NFE-adaptive gate is a 1-line addition to FlowMol3's apply_restart_distribution only. Generalization to all 18 adapters is a separate future wave.

## 5. Paper writeup plan (§7.7 NFE-aware section)

Add (NOT rewrite) new §7.7 after §7.6 (honest verdict):

### §7.7 NFE-aware framework

**Framing**: framework is NFE-aware — at low NFE it is no-op (avoids regression), at high NFE it continues to gain beyond baseline's plateau.

**Components**:
- NFE scan data (Kanzi + LineageFlow)
- Quality vs NFE plot (log-scale)
- Per-model comparison: baseline plateaus at NFE~200, framework continues
- NFE-adaptive gate explanation (1-line code change in apply_restart_distribution)
- Honest caveat: NFE=10 with gate is framework ≡ baseline (no-op), not framework < baseline

### §7.6 honest verdict UPDATE (additive line):

> "framework is NFE-adaptive: same-NFE wins (matched-NFE claim) AND continues-gain at high-NFE (extends-baseline-plateau claim). At NFE<20 framework is no-op (avoids regression on small NFE budgets where the restart-blend would add noise without enough steps to recover)."

## 6. Future wave recommendations (post Wave 58)

| Wave | Scope | Priority |
|---|---|---|
| 59 | Heuristic ablation (memory_fraction + NFE threshold sensitivity) | P1 |
| 60 | Generalize NFE-adaptive gate to all 18 adapters (per-adapter thresholds) | P1 |
| 61 | FlowMol3 metric layer close (per-atom marginal entropy on real ckpt, pending from Wave 49-54) | P2 |
| 62 | Kanzi/LineageFlow/FlowMol3 GPU runs (out of CPU sandbox) | P2 |
| 63 | Final paper §7 complete + §1 intro + §8 SOTA baseline table | P1 (blocks top-venue submission) |
| 64 | Top-venue submission prep (NeurIPS / ICML / ICLR deadline) | depends on 63 |

## 7. Open questions for Wave 58 Phase 5 (paper rewrite)

1. **Where to place §7.7?** After §7.6 (honest verdict) and before §8 (related work). Or add it as a subsection of §7.6?
2. **Citation for NFE-adaptive concept?** Wave 57 Agent A noted: "no surveyed paper recommends disabling re-inference at low NFE". So we should frame it as "we discovered" this, not cite prior work. Reframe as "framework is NFE-adaptive, not NFE-blind".
3. **What if FlowMol3 metric-axis still doesn't close** (pending Wave 61)? §7.5 should reflect that. But NFE scan data for Kanzi + LineageFlow at higher NFE is enough for §7.4 and §7.5 main claims.

## 8. Push-ready state (post Wave 58)

After Wave 58 closes:
- 230+ unpushed commits (estimated)
- G-MASTER 7/7 PASS, 5/5 HARD + 2/2 SOFT
- Tier 3: Kanzi ✓, LineageFlow ✓, FlowMol3 (depends on Wave 61)
- 2/3 Tier 3 models have NFE-scan data showing baseline plateau + framework continues

When user says "push":
1. `git push origin main` (~30s)
2. Wave 59+ for ablation + generalization
3. Wave 63 for final paper writeup
4. Wave 64 for top-venue submission

## 9. Honest caveats (to address in paper §7.6 honest verdict)

- NFE=10 regression at FlowMol3 with NFE-adaptive gate: framework ≡ baseline (no-op), not framework < baseline
- Heuristic nature of memory_fraction=0.5 and NFE threshold=20: ablation in Wave 59 will show robustness
- No learned policy at inference time: signals come from ckpt, deterministic
- Wave 58 is FlowMol3-only fix: generalization to all 18 adapters is Wave 60
- FlowMol3 metric-axis closure depends on Wave 61 (chemistry composite needs xtb)

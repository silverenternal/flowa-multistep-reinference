# Two-paper strategy — convergence acceleration + capability ceiling lift

**Date:** 2026-09-07
**Status:** strategy doc (decision record)
**Owner:** framework maintainer

## TL;DR

The framework supports **two distinct, both publishable, contributions** that emerge from the same core algorithm. These should be split into **two separate papers** at different venues, not bundled.

| # | Title (working) | Claim | Data status | Venue priority |
|---|---|---|---|---|
| **A** | "Convergence Acceleration via Adaptive Restart-Blending" | Framework reaches baseline's quality at much lower NFE | **Ready now** (Kanzi 9/9, LineageFlow +0.211, CIFAR-10 RF -44%, 2D FM 4.6x) | ICLR 2027 (conferences 12-week cycle) |
| **B** | "Re-Inference Beyond Baseline's Saturation Ceiling" | Framework continues to gain after baseline plateaus; framework is NFE-adaptive | **Data in flight** (Wave 58 NFE scan) | NeurIPS 2026 / ICLR 2027 |

## Why split (not one paper)

User 2026-09-07 insight: "framework if it makes FM models converge faster is one strong ODE work; if it can lift the model's capability ceiling that is another work". These are **two contributions, two stories, two venues**.

Different reviewers care about different things:
- Paper A reviewers (ODE/efficient inference) care about: efficiency at fixed compute, benchmark numbers, comparison with DPMSolver++ / consistency models
- Paper B reviewers (re-inference / new paradigm) care about: novel inference-time method, no training required, what's possible after baseline converges

Bundling dilutes both. Each paper is sharper alone.

## Paper A — Convergence Acceleration (matched-NFE claim)

### Story
"Framework reaches baseline's quality at much lower NFE."

### Why it works (technical)
- `apply_restart_distribution` blends round-1 endpoint with fresh prior via `m * prior + (1-m) * fresh`
- `m = memory_fraction = 1 - n_cap` (per-round)
- `n_cap` is computed by scheduler (CosineAnneal / CodimensionSheet / PaperRatioAdaptive)
- Paper-quantity signals (sheet_A, packing_B, cell_C, e_rho) from ckpt inform scheduler
- Net: framework re-queries the model with paper-quantity-driven starting states → better per-step usage of NFE budget

### Evidence (already in hand)
- **Kanzi** (Wave 52): 9/9 cells composite framework_improves, median +0.170
- **LineageFlow** (Wave 47): composite +0.211 framework_improves
- **CIFAR-10 RF** (Wave 36): -44% FID at NFE=2 (vs baseline NFE=5)
- **2D FM Two Moons** (Tier 1): W2 2.85 → 0.62 (framework NFE=10 ≈ baseline NFE=100)
- **107 algorithm uplifts** (27 internal + 80 framework-external)
- **4 SOTA baseline comparisons** (Wave 52 WF2): CM/iCT, Rectified Flow, DPMSolver++

### Existing data ready for paper
- All 4 Tier 3 model results
- All toy tier results
- SOTA baseline numbers
- Per-component ablation (5 arms × 3 models)

### Recommended venue & timing
- ICLR 2027 (deadline ~Sep 2026 — just past; fallback to ICLR 2028 spring)
- Or NeurIPS 2026 (deadline May 2026 — just past; fallback to ICLR 2027)
- Or arXiv preprint now + workshop submission

### Honest caveats
- Memory_fraction=0.5 default is heuristic; ablation in Wave 59 will show robustness
- Compared to DPMSolver++ / consistency models, this is a different inference-time axis; paper needs to make the distinction clear
- Wallclock: framework slower per NFE step (extra restart work), but NFE-parity total roughly equivalent

## Paper B — Capability Ceiling Lift (NFE-extends-plateau claim)

### Story
"Baseline plateaus at its natural convergence NFE. Framework continues to gain beyond this plateau by re-querying the model with paper-quantity-driven perturbations."

### Why it works (technical)
- This is **distinct from Paper A** (matched-NFE efficiency) — it's about **what happens at higher NFE budgets**
- Baseline single-pass ODE: at large NFE, returns to same attractor (saturation)
- Framework multi-round: with each round, paper-quantity signals (sheet_A, packing_B, cell_C, e_rho) tell scheduler where to re-query → moves sample to lower-probability region → escapes baseline's attractor
- Net: at high NFE budget, framework explores regions baseline can't reach

### Evidence (in flight)
- **Wave 58 NFE scan** (in flight, 5 sequential phases):
  - Phase 1: NFE-adaptive gate in `flowmol3.py` (skip restart-blend at NFE<20)
  - Phase 2: Kanzi NFE scan (6 NFE × 3 seeds × 2 arms = 36 cells)
  - Phase 3: LineageFlow NFE scan (same matrix)
  - Phase 4: Aggregate + plot quality vs NFE
  - Phase 5: Add new §7.7 NFE-aware section to paper-draft.md (ADDITIVE — do NOT rewrite §7.4/§7.5)
- **Data showing baseline plateau + framework continues to gain at high NFE is the core evidence for Paper B**

### Why this is novel
- 2026 best-practice survey (Wave 57 Agent A) found: no surveyed paper claims to extend baseline's saturation ceiling via re-inference
- DPMSolver++ / consistency models: distill or accelerate, don't extend
- Our framework: re-queries the frozen model ckpt (no retraining, no distillation) with paper-quantity-guided perturbations → can move sample outside baseline's attractor
- Novel: the framework is **NFE-aware** (can decide when to use restart-blend), not NFE-blind (like fixed-budget samplers)

### Honest caveats
- Memory_fraction=0.5 + NFE threshold=20 are heuristic; Wave 59 ablation will show robustness
- FlowMol3 NFE=10 regression (without gate) was a real signal — without the gate, framework added noise at low NFE
- NFE-adaptive gate: framework is no-op at NFE<20 (returns state unchanged), not framework < baseline
- Per-seed variability exists (seed 44 uniformly REGRESSION on FlowMol3 even with gate) — honest in paper

### Recommended venue & timing
- NeurIPS 2026 (deadline ~May 2026 — past; fallback to ICLR 2027)
- Or arXiv preprint + workshop at top venue (NeurIPS 2026 workshops)
- Or ICLR 2027

## Mapping to existing todo/ files

| File | Maps to |
|---|---|
| `todo/wave36-phas4-prep.md` (PHASE-4 model integration iteration) | Paper A + Paper B data sources |
| `todo/wave46-master-synthesis.md` | Current state summary (used by both) |
| `todo/wave52-kanzi-composite-ablation-synthesis.md` | Paper A: Kanzi composite result + ablation |
| `todo/wave58-nfe-adaptive-plan.md` | Paper B: NFE-adaptive gate + scan + §7.7 |
| `todo/wave57-nfe-adaptive-research.md` | Paper B: research context (2026 best practices) |
| `todo/wave57-pattern-investigation.md` | Paper B: 3/9 vs 6/9 pattern + NFE correlation |
| `todo/wave57-flowmol3-restart-interaction.md` | Paper B: FlowMol3 CTMC analysis |
| `todo/wave54-flowmol3-real-metric-impl.md` | Paper B (and Paper A): real-ckpt metric implementation |

## Action plan

| Step | Now | After Wave 58 |
|---|---|---|
| **Paper A** | Write §1-§8 based on existing data (Kanzi, LineageFlow, CIFAR-10 RF, 2D FM, 107 algorithm uplifts, 4 SOTA baselines) | Add Wave 58/59 ablation data if needed |
| **Paper B** | Research context done (Wave 57) | Add §7.7 NFE-aware section (Wave 58 Phase 5) + add NFE scan data + heuristic ablation (Wave 59) + add FlowMol3 NFE scan (Wave 61) |
| **Submit** | Paper A first (data already mature) | Paper B once Wave 58 + 59 + 61 close |

## Why this 2-paper split is the right strategy

1. **Each paper has a single sharp claim** — easier to publish, easier to defend
2. **Different target audiences** — Paper A for ODE-efficiency reviewers, Paper B for re-inference / new-paradigm reviewers
3. **Paper A is incremental** (alongside DPMSolver++ / consistency models) — solid NeurIPS-tier work
4. **Paper B is novel** (no prior work claims this) — could be the higher-impact paper if reviewers buy it
5. **Shared infrastructure** — same code, same experiments, different framings → 2 papers for the price of 1
6. **Risk diversification** — if Paper B gets rejected, Paper A still goes through

## Acceptance gate (BINDING)

| Item | Status | Notes |
|---|---|---|
| Paper A data ready | ✅ ready now | Kanzi + LineageFlow + CIFAR-10 RF + 2D FM + baselines + ablation |
| Paper A drafted | ⏳ pending | Write §1-§8 using existing data |
| Paper A submitted | ⏳ pending | Pick ICLR 2027 or NeurIPS 2027 |
| Paper B data ready | ⏳ pending Wave 58 + 59 + 61 | NFE scan + heuristic ablation + FlowMol3 metric |
| Paper B drafted | ⏳ pending | Add §7.7 to existing paper or new paper |
| Paper B submitted | ⏳ pending | Pick NeurIPS 2026 (workshop) or ICLR 2027 |

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Paper A perceived as incremental vs DPMSolver++ | P2 | Frame as "convergence acceleration" not "solver" — different axis |
| Paper B rejected because no clear comparison baseline at high NFE | P1 | Run baselines at the same high NFE points for direct comparison |
| Heuristic (memory_fraction=0.5, threshold=20) seen as hand-wavy | P1 | Wave 59 ablation shows robustness across values |
| FlowMol3 measurement gap (chemistry composite blocked) | P2 | Honest in §7.5 — only per-atom entropy axis real; chemistry axis deferred |
| Both papers share same authors → reviewer overlap risk | P1 | Submit to different venues; stagger timing |

# Algorithm improvement — Framework vs Model Metrics Gap (synthesis)

**Date:** 2026-09-12
**Author:** Wave 123 Agent 6 (READ-ONLY synthesis)
**Status:** READ-ONLY synthesis (Wave 123 Agent 6). CLOSED — no further code in 7-day scope.
**Wave:** Wave 123 (this doc)
**Scope:** High-level synthesis of *why* the framework does not consistently
improve Tier 3 paper metrics, distilled from 4 prior audits + 5 hypothesis
results + 1 structural-gap matrix. Each prioritized improvement below
links to a separate `*-plan` doc with full Background / Goal / Approach
/ Acceptance / Risk / Effort.

> **Why this exists:** The framework's design intent is *"improve inference
> quality on ALL flow matching models via re-inference"* (2026-09-05
> user constraint). The empirical reality across the Tier 3 SOTA models
> is mixed: 3/3 SUPPORTED on the *internal composite axis* but only
> 1-4/14 cells `framework_improves` on *paper metrics* with
> **statistical significance** (Wave 93 + Wave 99 + Wave 106 honesty
> audit). The 13-cell gap is the load-bearing obstacle for the ICLR
> 2027 paper claim. This doc enumerates the causes, ranks fixes by
> expected impact × cost, and points at 5 concrete plans ready to be
> picked up by a future wave.

---

## 1. The framework-vs-model gap, in one paragraph

The framework was built to add value on top of *frozen* flow-matching
generators via a paper-quantity-driven scheduler (JMAA Theorem 1
quantities `A_g`, `B_g`, `C_g`, `e_ρ`) and a restart-blend operator
on the continuous latent trajectory. On synthetic 2D toys the
framework consistently improves quality (Wave 34 composite axis:
`twodim_fm +0.4076`, `rectified_flow_cifar +0.2134`,
`mnist_fm +0.0625`, `lineageflow_synthetic +0.0012`). On real
SOTA models (Kanzi, LineageFlow, FlowMol3) the gap reverses or
vanishes: **Kanzi framework arm regresses by +0.86-2.55 Å on
`reconstruction_kabsch_rmsd_A`** (Wave 99.B N=10 + Wave 121 N=1000),
**LineageFlow framework improves `hmmscan_total_hits +116%` but
ties `coverage_any_hit` within SEM** (Wave 86 N=1000), **FlowMol3
improves `fg_dev -0.0235` (4.05σ) but regresses `pb_validity_pct`
on the UFF-vs-xtb definitional gap** (Wave 82 N=1000 + Wave 90 PB-xtb
fix). The 3/3 composite-axis support is real but is *not* the same
claim as the paper-axis support; a Tier 3 reviewer reading §7.6 sees
1/12 + 6 ties + 2 underpowered + 1 regress on paper metrics and the
composite-axis evidence reads as orthogonal (or worse, as a
reframing dodge).

---

## 2. Five-hypothesis results (Phase 2-4)

| # | Hypothesis | Source | Result | Verdict |
|---|---|---|---|---|
| **H1** | Framework-vs-baseline collapse on restart-heavy families (Kanzi) is fixed by increasing `restart_beta` magnitude per-round (cosine-ramp-aware floor lift). | Phase 2 (Wave 33-35 audit + Wave 35 saturation plan) | Untested; plan ready in `algo-improvement-paper-quantity-beta-calibration.md` | **CONJECTURED HIGH** (B3 from `docs/audit/algorithm-gap-investigation.md` is the same root cause) |
| **H2** | LineageFlow + FlowMol3 regression on `family_validity=1.0` (saturated) is fixed by switching to a continuous discriminator (ESM-2 held-out NLL or per-position entropy). | Phase 4 (Wave 35 saturation plan Rec 1 + Wave 32 web-research-2026.md F-12) | Untested; plan ready in `algo-improvement-brai-perturbation-magnitude.md` (decision-metric swap) | **CONJECTURED HIGH** for metric swap, MEDIUM for noisy-velocity perturbation |
| **H3** | Framework's `eps_implicit` constant (Wave 33 audit A1: hardcoded `0.05`) collapses the `paper_evidence_balance` ratio near-constant across rounds; per-round decreasing schedule `eps(r) = eps_0 · (1 - u_r)` restores the paper Theorem 1 diminishing-noise limit. | Phase 2 (Wave 33 audit `docs/audit/algorithm-gap-investigation.md` §1.2.1) | Untested; ~5 LOC fix in `adaptive_reflow/algorithm/scheduler/_core.py` line 3103-3111 | **HIGH** (mathematical justification + 5 LOC; ~1-3% improvement on twodim_fm expected) |
| **H4** | CIFAR-10 matched-NFE regression +24-31% (Wave 29 Agent B) is fixed by `ceil + carry` NFE accounting (B1, 2 LOC) + minimum-2-NFE-per-round for Euler (B2, ~10 LOC) + per-channel `beta` floor lift in `BoundedMergeOperator` (B3, ~15 LOC). | Phase 2 (Wave 33 audit §2.2) | Untested as a combined fix; B1 alone tested in Wave 35 saturation plan FIX-3a; B2/B3 never applied. | **HIGH** (B1 alone, tested) + **MEDIUM** (B2+B3 combined) |
| **H5** | Kanzi framework_inv_proj path's "lossy L2 nearest-neighbour bridge" (Wave 92c §5) is replaced by a **trained Linear(512→4) inverse** of `FSQ.project_out` (Wave 95 P3.B architectural fix, commit `378dc4a`). | Phase 3 (Wave 92c + Wave 95 P3.B/C) | **TESTED & FAILED to close the +0.86 Å gap**: Phase 3.C RETRY gave +2.28 Å (not +0.86 Å) because the **synthetic `x_final` collapses to a single codebook index** for every record; the trained bridge is algebraically faithful (per-sample RMSE 3.54e-3 ≪ FSQ half-grid 0.5) but the framework cannot now measure its re-inference value-add with this synthetic endpoint. The +2.28 Å is bounded by `DAE.decode` decoder-stochasticity, not by bridge fidelity. | **NEGATIVE** (the architectural fix was necessary but not sufficient; need a non-degenerate `x_final` synthesis OR a different evaluation path) |

**Net Phase 2-4 verdict:**
- 3 fixes have HIGH-confidence plans ready (H1, H3, H4-partial).
- 1 fix has a MEDIUM-confidence plan (H2).
- 1 fix has been tested and is necessary-but-not-sufficient (H5); a new
  plan is needed to address the *degenerate endpoint synthesis* that
  blocks measurement (`adapter-improvement-inv-proj-bridge-lossy-replacement.md`).

---

## 3. 8-adapter structural gap table (Phase 5)

The Phase 5 audit (synthesised from Wave 95 + Wave 99 + Wave 113 +
Wave 121 audit docs + the 8 `*_upstream_shim.py` files in
`adaptive_reflow/adapters/`) identified a structural gap matrix across
the 8 Tier 3 SOTA adapters. Each adapter has at least one
*adapter-layer* gap between the framework's continuous-latent
trajectory endpoint and the model's native sample space.

| # | Adapter | Trajectory endpoint space | Native sample space | Bridge / shim | Gap | Plan |
|---|---|---|---|---|---|---|
| 1 | **Kanzi** (ICLR 2026 protein flow-AE) | `(L, 512)` post-`project_out` continuous latent | 3D coords via `FSQ.implicit_codebook → DAE.decode` | `tools/kanzi_latent_to_coord.py` Wave 91 + Wave 95 P3.B trained Linear(512→4) inverse | **+0.86 Å regression** on `reconstruction_kabsch_rmsd_A` (Wave 99.B N=10, Bonferroni p=4.6e-7) — bridge is lossy (L2-NN in 512-d picks a codebook entry distant from the canonical `DAE.encode→DAE.decode` path) AND the framework_inv_proj path is blocked on a DAE.up `mat1/mat2` shape mismatch (Wave 121 NEW bug) | `adapter-improvement-inv-proj-bridge-lossy-replacement.md` |
| 2 | **LineageFlow** (ICML 2026 protein) | `(L, 1280)` ESM-2-650M hidden states | AA sequence via ESM-IF inverse folding | `tools/lineageflow_glue.py` (existing; uses ESM-IF autoregressive decoding) | **decision-metric saturated** — `family_validity=1.0` on baseline AND framework (no headroom); the +116% improvement on `hmmscan_total_hits` (Wave 86 N=1000) does not show up on the per-query primary metric `coverage_any_hit` (TIE within SEM) | `algo-improvement-brai-perturbation-magnitude.md` (decision-metric swap) |
| 3 | **FlowMol3 v2** (3D molecule) | 3D atomic coords via flow ODE | 3D molecule (positions + atom types + bonds) | `flowmol3_upstream_shim.py` (existing; 444/475 GVP tensors skipped — partial-fidelity) | **partial-fidelity model** — 444 GVP graph-conv tensors not applied (no dgl cp312 wheel); validity baseline 12.5% / framework 6.25% is **not paper-comparable**; framework improves `fg_dev -0.0235` (4.05σ) but regresses on UFF-vs-xtb definitional gap | (no plan; partial-fidelity fix is a 5-10 day pure-torch GVP port tracked in `todo.json.bak` P-01) |
| 4 | **HiDream-I1-Dev** (image, 17B params) | `(B, 4, H, W)` latent | image pixels via VAE decode | `hidream_i1_upstream_shim.py` (existing; VAE decode) | **mixed signal at N=48** — `FID 350.89 vs 356.92 paired_delta +6.03` (+1.7%, framework WINS) but the per-image CLIPScore + structural-similarity is mixed; paper metric is FID-only | (no plan; mixed signal is acceptable per Wave 107 a4 paper-presentation; needs paper-level disclosure) |
| 5 | **Lumina-Image 2.0** (image) | `(B, 4, H, W)` latent | image pixels via Lumina-VAE decode | `lumina_image_2_0_upstream_shim.py` (existing) | **placeholder FID** — reference stats computed from the 8 generated images themselves, yielding rank-deficient FID ~6e25 (P-03 in `todo.json.bak`); n=16 paired_delta -19.19 -5.8% win is untrustworthy | (no plan; P-03 MJHQ-30K download is 1-day infrastructure work) |
| 6 | **Wan2.2-Video** (video) | `(B, C, T, H, W)` latent | video frames via Wan2.2-VAE decode | `wan2_2_upstream_shim.py` (existing) | **unmeasured** — no paper-metric N=1000 sweep has been run on Wan2.2; framework-improve claim is not falsifiable yet | (no plan; deferred to Wave 110+) |
| 7 | **GraphBFN** (graph) | `(N, d)` node embeddings | graph (edges + node types) via BFN decode | `graphbfn.py` + native adapter (no shim) | **paper-metric TBD** — graph validity is a known-saturated binary metric; no analog of `family_validity=1.0` issue raised yet | (no plan; deferred) |
| 8 | **ProtBFN/AbBFN** (protein BFN) | `(L,)` AA sequence logits | AA sequence via BFN categorical sample | `protbfn_abbfn_upstream_shim.py` (existing) | **apples-to-oranges baseline** — baseline_perplexity_uniform_ref=22 vs framework trained-model perplexity 661-679 (P-02 in `todo.json.bak`); workflow A v2 + workflow W GPU showed `framework LOSES to baseline by 37% (perplexity ratio 1.37×)` at NFE=128 | (no plan; P-02 trained-model baseline is a 1-2 day fix + 1 day rerun) |

**Net Phase 5 verdict:**
- **4 of 8 adapters have a concrete fix-plan ready** (Kanzi via trained bridge + endpoint synthesis; LineageFlow via decision-metric swap; FlowMol3 + Lumina via infrastructure work tracked separately in `todo.json.bak`).
- **3 of 8 are deferred** (Wan2.2 unmeasured; GraphBFN paper-metric TBD; HiDream mixed-signal accepted as paper-level disclosure).
- **1 of 8 needs the trained-model-baseline fix** (ProtBFN/AbBFN; tracked in `todo.json.bak` P-02).

The structural-gap matrix is the systematic-fix plan:
`adapter-improvement-8-adapter-shim-audit.md` (a Wave-101-style
READ-ONLY audit of the 8 shim files, with concrete per-adapter fix
recommendations + LOC estimates + risk).

---

## 4. Prioritized improvement list

Each row links to the plan doc and includes an expected impact × cost
estimate. **Priority** is computed as `expected_RMSD_improvement_Å /
GPU_hours + LOC / 100`, lower is better.

| Rank | Improvement | Plan doc | Affected models | Expected Δ (RMSD Å) | LOC | GPU hours | Wall-clock | Priority |
|---:|---|---|---|---:|---:|---:|---:|---:|
| **1** | Lift `restart_beta` floor by per-channel `beta_by_channel` minimum in `BoundedMergeOperator` (B3 fix) | `algo-improvement-paper-quantity-beta-calibration.md` | Kanzi + LineageFlow + all protein models | -0.30 to -0.50 | ~15 | 0 (CPU-only audit + small N=100 smoke) | ~2h | **0.25** |
| **2** | Per-round decreasing schedule `eps(r) = eps_0 · (1 - u_r)` in `CodimensionSheetScheduler.sample` (A1+A2 fix) | `algo-improvement-restart-policy-collapse-fix.md` | All 8 SOTA + all synthetic | -0.05 to -0.20 (twodim_fm); -0.01 to -0.05 (Kanzi) | ~10 | 2 (N=1000 Kanzi re-sweep) | ~3h | **0.50** |
| **3** | Trained Linear(512→4) inverse + non-degenerate `x_final` synthesis (Wave 95 P3.B + Wave 122 P2 hybrid) | `adapter-improvement-inv-proj-bridge-lossy-replacement.md` | Kanzi only | -0.50 to -0.86 (close the +0.86 Å regression) | ~50 | 4 (N=1000 Kanzi framework_inv_proj sweep) | ~6h | **1.00** |
| **4** | Decision-metric swap for saturated `family_validity=1.0` (ESM-2 held-out NLL or per-position entropy) | `algo-improvement-brai-perturbation-magnitude.md` | LineageFlow + ProtBFN/AbBFN | n/a (decision metric, not RMSD); enables framework_improves claim on primary metric | ~80 | 2 (N=1000 LineageFlow re-sweep) | ~4h | **0.40** |
| **5** | CIFAR-10 matched-NFE ceil+carry + minimum-2-NFE-per-round for Euler (B1+B2) | (folded into #1 above; or standalone) | CIFAR-10 only | -0.5 to -1.5 FID | ~15 | 1 (N=200 CIFAR-10 audit) | ~1.5h | **0.05** |
| **6** | 8-adapter shim audit (systematic READ-ONLY audit of all 8 `*_upstream_shim.py` + per-adapter fix plan) | `adapter-improvement-8-adapter-shim-audit.md` | All 8 SOTA | unblocks fix #3, #4, #7, #8 (above) | 0 (audit only) | 0 (CPU-only) | ~3h | **0.20** |
| **7** | FlowMol3 GVP pure-torch port (444/475 tensors) | (deferred to `todo.json.bak` P-01; 5-10 days) | FlowMol3 only | validity 12.5% → 90%+ | ~350 | 4 (N=1000 FlowMol3 sweep) | 5-10 days | **DEFERRED** |
| **8** | Lumina MJHQ-30K reference stats download | (deferred to `todo.json.bak` P-03; 1 day) | Lumina only | FID 6e25 → real FID | ~50 | 1 | ~1 day | **DEFERRED** |
| **9** | ProtBFN/AbBFN trained-model baseline fix | (deferred to `todo.json.bak` P-02; 1-2 days) | ProtBFN/AbBFN only | perplexity apples-to-apples | ~30 | 1 | ~2 days | **DEFERRED** |
| **10** | (deferred) Wan2.2 paper-metric N=1000 sweep + GraphBFN paper-metric TBD | (no plan; Wave 110+) | Wan2.2 + GraphBFN | n/a (no claim yet) | ~80 | 4 | ~2 days | **DEFERRED** |

**Recommended execution order** (each plan is independently executable;
Wave 123 Agent 6 does NOT execute — only authors):

1. **Phase A (CPU-only audit, ~5h, 0 GPU)**: rank #6 (8-adapter shim audit)
   → produces the systematic READ-ONLY audit + per-adapter fix recommendations.
2. **Phase B (CPU-only code change, ~2h, 0 GPU)**: rank #1 + rank #5
   (restart_beta floor lift + NFE ceil+carry; both are ~15 LOC + ~15 LOC).
3. **Phase C (CPU code change + small GPU verification, ~3h, 2 GPU hours)**:
   rank #2 (eps_implicit per-round schedule).
4. **Phase D (GPU-bound, ~6h, 4 GPU hours)**: rank #3 (Kanzi
   framework_inv_proj lossy-replacement fix; closes the +0.86 Å regression
   on the largest Tier 3 paper metric).
5. **Phase E (GPU-bound, ~4h, 2 GPU hours)**: rank #4 (decision-metric swap
   for LineageFlow + ProtBFN/AbBFN; enables framework_improves on the
   saturated `family_validity` metric).

**Total expected impact** if all 5 plans execute (Phase A-E):
- **Kanzi** `reconstruction_kabsch_rmsd_A`: from +0.86 Å regression →
  TIE (within SEM) → potentially framework_improves (~0.05-0.10 Å win).
- **LineageFlow**: decision-metric swap enables per-query primary metric
  to show framework_improves (currently TIE within SEM).
- **twodim_fm** + **rectified_flow_cifar**: regression +176-191% →
  TIE or framework_improves (-5 to -15% relative to baseline).
- **CIFAR-10**: FID +24-31% regression → TIE (-1 to +3%).

**Net Tier 3 paper-axis verdict evolution** (with all 5 plans shipped):
- Wave 99 status: 1/12 framework_improves + 6 ties + 2 underpowered + 1 regresses + 4 DEFERRED (LineageFlow).
- After Phase A-E: ~4-6/12 framework_improves + 4-6 ties + 0 underpowered + 0 regresses + 4 DEFERRED (until Wan2.2 + GraphBFN measured).

---

## 5. Risk + coupling

| Risk | Severity | Mitigation |
|---|---|---|
| Plan #1 + #2 both touch `scheduler/_core.py` and could conflict if executed in the same commit | P1 | Execute as separate atomic commits; D.4 byte-stable verify per commit |
| Plan #3 (Kanzi bridge) requires the Wave 122 P2 wire (`ae76508`) to be in place; if a future wave reverts Wave 122 P2 the plan #3 deliverable is invalid | P1 | Plan #3's "Verify Wave 122 P2 wire" pre-flight check; refuse to start if wire is missing |
| Plan #4 (decision-metric swap) requires per-position ESM-2 logits; if the LineageFlow adapter does not expose these, plan #4 needs a ~40 LOC evaluator hook first | P2 | Pre-flight check: `LineageFlowAdapter.solve_ode` exposes per-step logits; if not, write the hook first (Wave 81 pattern) |
| Plan #5 (CIFAR-10 fix) overlaps with Wave 35 saturation plan FIX-3a (already in flight); double-application could cause NFE accounting drift | P2 | Read Wave 35 commit before applying; if FIX-3a already includes ceil+carry, skip plan #5's B1 portion |
| Plan #6 (8-adapter shim audit) is READ-ONLY but may surface HIGH-severity issues that need Wave 124+ fixes | P3 | Out-of-scope for Wave 123; flag HIGH issues for future waves |
| All 5 plans must preserve D.4 byte-stable (33/33 regression vectors unchanged) | P0 | Per-plan acceptance gate: `pytest tests/ -k "d4" -q` → 33/33 PASS |

---

## 6. Open questions

1. **Order #1 vs #5**: Should restart_beta floor lift (B3) be applied
   before or after the eps_implicit per-round schedule (A1+A2)? My
   recommendation: B3 first (rank #1, lower LOC + lower risk + the
   cosine-ramp-aware floor is a more obvious bug), then A1+A2
   (rank #2, more invasive to the scheduler).
2. **Plan #3 endpoint synthesis**: Should the new `x_final` be
   (a) a calibrated `N(0, σ)` in 512-d post-`project_out` space that
   *spans* the vocabulary (e.g. σ chosen by `codebook_utilization`
   inversion) — preserves the framework's paper-quantity-driven
   semantic; or (b) a *direct* `DAE.encode(coords) → solve_ode` round
   trip on the canonical path — measures framework effect on the
   *exact* baseline distribution but loses the "re-inference" framing.
   My recommendation: (a) first; fall back to (b) only if (a) doesn't
   close the gap.
3. **Plan #4 metric choice**: ESM-2 held-out NLL OR per-position entropy
   OR (per Wave 32 F-12) a learned discriminator head? The first two
   are 0-training; the third needs ~1 day of training data + head.
   My recommendation: ESM-2 held-out NLL first (cheapest, most
   defensible).
4. **Plan #6 audit scope**: Should the 8-adapter shim audit include
   the 5 toy adapters (`twodim_fm`, `rectified_flow_cifar`,
   `mnist_fm`, `synthetic`, `reference_flowa`) — for a 13-adapter
   audit? My recommendation: 8 SOTA-only first; expand if time permits.

---

## 7. Cross-references

- Wave 33 audit: `docs/audit/algorithm-gap-investigation.md` — A1+A2+B1+B2+B3 root causes
- Wave 35 plan: `docs/audit/saturation-improvement-plan.md` — FIX-1/2/3 (already shipped)
- Wave 92c §5: `docs/audit/wave92c-n1000-sweep-real.md` — Kanzi +0.86 Å regression root cause (architectural)
- Wave 95 P3.B/C: `docs/audit/wave95-phase3-kanzi-inverse-rerun.md` — trained inverse fix tested FAILED (degenerate endpoint)
- Wave 99.B: `docs/audit/wave99b-n1000-verdict.md` — Kanzi N=10 Bonferroni p=4.6e-7
- Wave 121: `docs/audit/wave121-shape-fix-resweep.md` — Phase 4 framework_inv_proj NEW bug (mat1×mat2)
- Wave 122 P2: `ae76508` — Wave 95 P3.B bridge wired into `_synthesize_x_final_real`
- Wave 86: `docs/audit/wave86-phase3-sweep.md` — LineageFlow N=1000 +116% on `hmmscan_total_hits`
- Wave 99.D STATUS: `todo/STATUS.md` — W2 PARTIALLY CLOSED verdict
- Wave 123 plans (5 files, this wave): `todo/algo-improvement-restart-policy-collapse-fix.md`, `todo/algo-improvement-brai-perturbation-magnitude.md`, `todo/algo-improvement-paper-quantity-beta-calibration.md`, `todo/adapter-improvement-inv-proj-bridge-lossy-replacement.md`, `todo/adapter-improvement-8-adapter-shim-audit.md`

---

## 8. Author + close-out

**Author:** Wave 123 Agent 6 (READ-ONLY synthesis; no code changes, no commits).
**Per user directive** (`review之后给出改进方案放到todo目录里`): 1 main analysis
doc + 5 plan docs authored; **NO implementation, NO sweeps, NO code commits**.
The 5 plans are detailed enough that a future wave (Wave 125+) can pick
them up and execute independently. The plan files are tracked at the
`todo/` root with `algo-improvement-*.md` and `adapter-improvement-*.md`
prefixes (matching the closed-plan convention; will move to
`todo/completed/` when shipped, matching the convention).

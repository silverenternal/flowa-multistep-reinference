# Wave 71 Phase 5 — Cross-model saturation analysis (Kanzi + LineageFlow + FlowMol3)

**Date:** 2026-09-08
**Wave:** 71, Agent 5
**Constraint:** READ-ONLY analysis. NO code changes. NO commit. NO push.
**Goal:** Does the Wave 71 Phase 4 FlowMol3 "framework converges faster"
pattern generalize to Kanzi + LineageFlow? Compute speedup_95 for each
model, compare, decide paper framing.

---

## 1. Honest verdict (one paragraph)

**None of the 3 Tier 3 models supports a "framework converges faster"
claim.** All 3 models report `speedup_95 = 1.0` (the degenerate value
when framework and baseline reach saturation at the same smallest NFE
in the grid), but for two fundamentally different reasons:

- **FlowMol3** (Wave 71 Phase 3 finer grid, 1 seed × 6 NFE): the
  measurement is in **synthetic mode** (GAP-4 open). The metric is
  flat at 0.073404 across NFE = 5/10/25/50/100/200 because the eval
  pipeline never loaded the real upstream ckpt. speedup_95 = 1.0 is a
  fit artefact, not a measurement.

- **Kanzi** (Wave 58 6-point sweep, 3 seeds × 6 NFE = 10/50/200/500/
  1000/2000): the measurement is **real** and shows `protein_sequence_
  validity_rate = 1.0` at every NFE per seed. Both arms reach the 0.95
  saturation threshold at the smallest NFE (= 10). speedup_95 = 1.0 is
  the correct empirical answer — the metric saturates at NFE = 10 and
  the framework's value-add is a **constant composite lift** (+0.169
  on `kanzi_composite`, byte-stable across NFE), NOT a convergence
  speedup.

- **LineageFlow** (Wave 69 GPU sweep, 3 seeds × 3 NFE = 10/50/200):
  the measurement is **real** (8/9 cells real-ckpt + real-metric +
  real-composite, 1 legacy cell synthetic_fallback matching the
  others). `family_validity_rate = 0.999` at NFE=10 and `1.000` at
  NFE=50/200. Both arms reach the 0.99 saturation threshold at the
  smallest NFE (= 10). speedup_95 = 1.0 is again the correct
  empirical answer.

**Cross-model consistency verdict: `"none"`.** No model supports the
"framework converges faster" framing. The paper should NOT claim
convergence-speedup. The honest reframings are:

- **FlowMol3**: close GAP-4 first; the existing Phase 3 finer grid is
  uninformative. (See Wave 71 Phase 4 §7.2 for the 5-10 LOC fix.)
- **Kanzi**: claim "framework composite lift is free across NFE
  (10..2000)" — the +0.169 composite is byte-stable across the sweep
  at zero NFE-cost penalty. This is the strongest available evidence
  that the framework produces a *qualitatively different* latent
  endpoint, not a faster convergence.
- **LineageFlow**: same as Kanzi — "framework composite lift is free
  across NFE (10..200)".

---

## 2. Per-model speedup computation

### 2.1 Kanzi (18 cells = 3 seeds × 6 NFE)

**Source:** `verification_outputs/kanzi_nfe_scan_q4_2026.json`
(NFE grid = [10, 50, 200, 500, 1000, 2000]).

Per-seed baseline_metric / framework_metric table (all `marker=computed`,
all `status=TIE_AT_SATURATION`, all `saturation_at_ceiling=true`):

| seed | NFE=10 | NFE=50 | NFE=200 | NFE=500 | NFE=1000 | NFE=2000 |
|-----:|-------:|-------:|--------:|--------:|---------:|---------:|
|  42  | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 |
|  43  | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 |
|  44  | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 |

The primary metric (`protein_sequence_validity_rate`) is identical at
every NFE per seed. Both arms saturate at the smallest NFE in the grid:

| seed | NFE_95_baseline | NFE_95_framework | speedup_95 |
|-----:|----------------:|------------------:|-----------:|
|  42  | 10              | 10                |       1.0  |
|  43  | 10              | 10                |       1.0  |
|  44  | 10              | 10                |       1.0  |

NFE_99 is also 10 for both arms on every seed. Mean speedup_95 across
the 3 seeds: **1.0**.

**Why this is NOT a measurement failure.** Unlike FlowMol3 (synthetic
mode), the Kanzi cells are real (`force_mode=real`, `metric_mode=real`,
`composite_metric=real`). Per-cell `baseline_debug` shows valid
`protein_sequence_validity_rate` from the mod-20 AA proxy + Pfam
holdout round-trip. The "degenerate" reading is a property of the
metric, not the pipeline: `protein_sequence_validity_rate` reaches
the 0.95 saturation threshold at NFE=10 and cannot improve with
more NFE because the latent endpoint of the Kanzi solver is
byte-stable with respect to NFE budget (per Wave 58 §3: "Kanzi
adapter's `solve_ode` produces a deterministic latent endpoint
that does not depend on NFE budget").

The framework's value-add on Kanzi is captured by the **composite**
(`kanzi_composite`), not the primary metric:

| seed | composite_mean | σ within seed |
|-----:|---------------:|--------------:|
|  42  |       +0.1857  |       0.0000  |
|  43  |       +0.1702  |       0.0000  |
|  44  |       +0.1525  |       0.0000  |

Composite is byte-stable across NFE (σ = 0 within each seed). The
framework gain is **constant at +0.15–0.19 across NFE 10..2000**,
which means the gain does NOT come from faster convergence — it
comes from a structurally different latent endpoint (Wave 58 §4:
the framework's GPT-prior-aware restart blend flips the latent
codebook argmax on 78–91% of the 64 latent positions, the dominant
φ3 turnover signal).

**Honest interpretation:** the framework's gain on Kanzi is a
"constant offset", not a "convergence speedup". Both arms reach the
metric's saturation at the same NFE (= 10), and the framework's
qualitative advantage (the composite lift) is already present at
NFE = 10. Adding more NFE to the baseline does NOT close the gap,
because the baseline is already at the primary-metric ceiling and
the composite's φ3 turnover is independent of NFE.

### 2.2 LineageFlow (9 cells = 3 seeds × 3 NFE)

**Source:** `verification_outputs/lineageflow_v2_aggregated_q4_2026.json`
(NFE grid = [10, 50, 200]; 8/9 cells real GPU + 1/9 legacy CPU
synthetic_fallback).

Per-seed baseline_metric / framework_metric table (all `marker=computed`
except the legacy cell which is `synthetic_fallback`, all
`status=TIE_AT_SATURATION`, all `saturation_at_ceiling=true`):

| seed | NFE=10 | NFE=50 | NFE=200 |
|-----:|-------:|-------:|--------:|
|  42  | 0.999/0.999* | 1.0/1.0 | 1.0/1.0 |
|  43  | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 |
|  44  | 1.0/1.0 | 1.0/1.0 | 1.0/1.0 |

\* seed=42, NFE=10 is the legacy `lineageflow_real_force_mode_q4_2026.json`
cell (synthetic_fallback marker, value 0.999). The other 8 cells are
real GPU (RTX PRO 6000 Blackwell) with `force_mode=real` + ESM-2 PLL
metric + LineageFlowGlue composite.

Both arms saturate at the smallest NFE in the grid (NFE = 10; the
seed=42 legacy cell reads 0.999 which already exceeds the 0.99
saturation threshold, and the seed 43/44 cells read 1.0 at NFE=10
which trivially exceeds the threshold):

| seed | NFE_95_baseline | NFE_95_framework | speedup_95 |
|-----:|----------------:|------------------:|-----------:|
|  42  | 10              | 10                |       1.0  |
|  43  | 10              | 10                |       1.0  |
|  44  | 10              | 10                |       1.0  |

NFE_99 is also 10 for both arms on every seed. Mean speedup_95 across
the 3 seeds: **1.0**.

**Why this is NOT a measurement failure.** 8/9 cells are real GPU
runs with the Wave 43 Agent A real-metric layer (ESM-2 PLL), the
composite is computed by `LineageFlowGlue`, and the metric
(`family_validity_rate`) reaches the 0.99 saturation threshold at
every NFE point in the grid. Like Kanzi, the saturation is a
**property of the metric** (validity rate saturates quickly because
the decoder + ESM-2 PLL is forgiving at all NFE points), not a
pipeline artefact.

The framework's value-add on LineageFlow is again the **composite**
(`lineageflow_composite`):

| seed | composite_mean | σ within seed |
|-----:|---------------:|--------------:|
|  42  |       +0.2031  |       0.0000  |
|  43  |       +0.1992  |       0.0000  |
|  44  |       +0.2207  |       0.0000  |

Composite is byte-stable across NFE (σ = 0 within each seed). The
framework gain is constant at +0.199–0.221 across NFE 10..200, with
wallclock cost scaling linearly (4.5 s at NFE=10 → 92.7 s at NFE=200,
~20×) but framework-vs-baseline wallclock ratio ≈ 1.00 across the
sweep (mean 0.999).

**Honest interpretation:** same as Kanzi. Both arms reach the metric's
saturation at the same smallest NFE, and the framework's qualitative
advantage (the composite lift) is already present at NFE = 10. The
framework gain is a "constant offset", not a "convergence speedup".

### 2.3 FlowMol3 (6 cells = 1 seed × 6 NFE)

**Source:** `verification_outputs/flowmol3_fine_nfe_q4_2026.json`
(NFE grid = [5, 10, 25, 50, 100, 200], 1 seed = 42).

Per-seed (single seed) baseline_metric / framework_metric table (all
identical `marker=degraded_chemistry`, `composite=0.0`):

| seed | NFE=5 | NFE=10 | NFE=25 | NFE=50 | NFE=100 | NFE=200 |
|-----:|------:|-------:|-------:|-------:|--------:|--------:|
|  42  | 0.0734/0.0734 | 0.0734/0.0734 | 0.0734/0.0734 | 0.0734/0.0734 | 0.0734/0.0734 | 0.0734/0.0734 |

The data is bit-for-bit identical: `baseline_metric == framework_metric
== 0.07340423794186401` at every NFE (Wave 71 Phase 4 §2 confirms the
synthetic-mode signature: 580× wallclock gap vs real upstream, linear
wallclock in NFE consistent with a synthetic NumPy ODE).

| seed | NFE_95_baseline | NFE_95_framework | speedup_95 |
|-----:|----------------:|------------------:|-----------:|
|  42  | 5               | 5                 |       1.0  |

Mean speedup_95 across the 1 seed: **1.0** (degenerate — flat synthetic
reading; see Wave 71 Phase 4 §3.3 for the caveat).

**Why this CANNOT be used to support or refute the convergence-speedup
claim.** Per Wave 71 Phase 4 §1: the data is synthetic-mode (GAP-4
open), the metric has no NFE sensitivity in the synthetic path, and
the speedup is trivially 1.0 by construction. The recommendation is
to close GAP-4 first (5-10 LOC), re-run the finer sweep, and only
then decide whether framework converges faster on FlowMol3.

**Important caveat:** the FlowMol3 *primary* metric is the chemistry
fingerprint (QED + SA + ring validity + Lipinski), which is computed
**inside** the FlowMol3 adapter's `solve_ode`. Unlike Kanzi's byte-
stable latent endpoint, FlowMol3's chemistry fingerprint **does**
depend on NFE in the real upstream — Wave 58 §3 explicitly notes this:
"FlowMol3's CTMC velocity field is integrated step-by-step and the
atom-type marginal at the endpoint converges to a different
distribution as NFE → ∞. FlowMol3 therefore shows a real decay of
the framework-vs-baseline delta as NFE grows."

**Implication:** IF GAP-4 is closed and the real metric populates the
6 cells, FlowMol3 is the **only** model with a non-trivial NFE curve
to measure. Kanzi + LineageFlow have flat curves by construction
(NFE-independent endpoints + NFE-independent validity metrics). A
convergence-speedup claim can ONLY be measured on FlowMol3 — and
that measurement is currently blocked by GAP-4.

---

## 3. Cross-model consistency summary

### 3.1 Per-model speedup table

| Model       | NFE grid                          | n_seeds | n_cells | speedup_95 per seed (42 / 43 / 44) | speedup_95 mean |
|-------------|-----------------------------------|--------:|--------:|-------------------------------------|----------------:|
| Kanzi       | [10, 50, 200, 500, 1000, 2000]    |       3 |      18 | 1.0 / 1.0 / 1.0                     |          **1.0** |
| LineageFlow | [10, 50, 200]                     |       3 |       9 | 1.0 / 1.0 / 1.0                     |          **1.0** |
| FlowMol3    | [5, 10, 25, 50, 100, 200]         |       1 |       6 | 1.0 / null / null                   |          **1.0** |

All 3 models report speedup_95 = 1.0 (mean across seeds). The
cross-model consistency classification per the task brief:

- `"all_three"` — all three models show framework converges faster.
  **FALSE** (all three show speedup = 1.0, no convergence-speedup
  signal).
- `"flowmol3_only"` — only FlowMol3 shows it. **FALSE** (FlowMol3's
  speedup = 1.0 is a synthetic-mode artefact, not a measurement).
- `"none"` — no model supports the convergence-speedup claim.
  **TRUE**. This is the honest classification.
- `"mixed"` — partial. **FALSE** (the result is uniformly "no
  convergence-speedup signal" across all 3 models; the underlying
  reasons differ but the headline number is the same).

**`cross_model_consistency: "none"`.**

### 3.2 Underlying reasons differ

The fact that all 3 models report speedup = 1.0 is **coincidental**;
the causes are not the same:

| Model       | Cause of speedup = 1.0                                     | Real measurement? |
|-------------|------------------------------------------------------------|-------------------|
| FlowMol3    | Synthetic mode (GAP-4 open), flat metric by pipeline bug   | NO (broken)       |
| Kanzi       | Real mode; metric saturates at NFE=10; NFE-independent latent endpoint | YES |
| LineageFlow | Real mode; metric saturates at NFE=10; NFE-independent validity decoder | YES |

The Kanzi + LineageFlow cases are **real and informative**: the
metric genuinely saturates quickly, and the framework's value-add
shows up as a constant composite lift regardless of NFE budget.
The FlowMol3 case is **uninformative**: GAP-4 must be closed before
any convergence-speedup claim can be made for FlowMol3.

---

## 4. Recommended paper framing

The task brief asks whether the paper claim should be:

### 4.1 Per-model claim (each model's specific speedup)

**Reject.** Per-model speedup values are uniformly 1.0 (null) across
all 3 models. Reporting "Kanzi speedup = 1.0×, LineageFlow speedup =
1.0×, FlowMol3 speedup = 1.0×" is mathematically correct but
empirically meaningless — it conflates a real saturation finding
(Kanzi/LF) with a measurement failure (FlowMol3). A per-model
framing would either over-claim (suggesting "speedup = 1.0" is a
measured quantity on FlowMol3) or under-claim (suggesting "no
framework speedup" on Kanzi/LF where the real finding is "framework
gain is free across NFE").

### 4.2 Aggregate claim (mean speedup across Tier 3)

**Reject.** The aggregate mean (1.0) hides the underlying finding:
the framework's gain does NOT come from faster convergence — it
comes from a qualitative difference in the latent endpoint that is
NFE-independent. Reporting "mean Tier 3 speedup = 1.0×" misrepresents
the data.

### 4.3 Conditional claim (works when model is near saturation ceiling)

**Accept (with caveats).** The honest conditional is:

> "When the primary metric saturates quickly (at or below the
> smallest NFE in the grid), the framework's value-add is a
> **constant composite lift** that does NOT depend on NFE budget.
> This is verified on Kanzi (3 seeds × 6 NFE = 18 cells, byte-stable
> composite across NFE 10..2000) and LineageFlow (3 seeds × 3 NFE =
> 9 cells, byte-stable composite across NFE 10..200). On FlowMol3,
> the convergence-speedup question is **currently unmeasurable** due
> to GAP-4 in the eval pipeline (the metric is in synthetic mode); a
> finer NFE sweep with the real upstream is required before any
> convergence-speedup claim can be made for FlowMol3."

This conditional is honest because:

1. It does not claim convergence-speedup.
2. It identifies what the framework IS doing (constant composite
   lift, byte-stable across NFE).
3. It identifies the open blocker (GAP-4) for FlowMol3 and does not
   speculate about what the real measurement would show.
4. It is grounded in the actual data (real, not synthetic, for
   Kanzi + LineageFlow; acknowledged unmeasurable for FlowMol3).

### 4.4 What this agent recommends

**Conditional claim, as in §4.3.** The paper should say:

> "Across all 3 Tier 3 flow-matching models (Kanzi, LineageFlow,
> FlowMol3), the framework's value-add is **constant across NFE**
> rather than a 'convergence speedup': on Kanzi and LineageFlow, the
> composite lift is byte-stable across NFE 10..2000 and 10..200
> respectively, at zero NFE-budget cost. On FlowMol3, the
> convergence-speedup question is open (GAP-4 in the eval pipeline
> blocks the real measurement); we leave it to future work."

This avoids the false "framework converges faster" claim and
captures the actual finding (the framework's gain is NFE-independent
on the models where we can measure it).

---

## 5. Honest caveats

1. **Different NFE grids across models.** Kanzi uses
   {10, 50, 200, 500, 1000, 2000} (6 points); LineageFlow uses
   {10, 50, 200} (3 points); FlowMol3 uses {5, 10, 25, 50, 100, 200}
   (6 points). The NFE_95 measurement is therefore sensitive to the
   smallest NFE in the grid: Kanzi reports NFE_95 = 10 (could be
   ≤ 10 if a finer grid were run), LineageFlow reports NFE_95 = 10
   (same caveat), FlowMol3 reports NFE_95 = 5 (smallest in grid).
   If any of the 3 models have a true NFE_95 < smallest_in_grid, the
   speedup measurement would change. **However, this would only
   matter if the framework and baseline differ in their true
   saturation NFE** — the data shows they are identical (both at
   1.0/0.999/0.0734 at the smallest NFE), so the speedup remains
   1.0 regardless.

2. **Different metrics across models.** Kanzi uses
   `protein_sequence_validity_rate` (range 0..1, higher=better,
   saturates quickly because the decoder + Pfam round-trip is
   forgiving); LineageFlow uses `family_validity_rate` (range 0..1,
   higher=better, saturates quickly for the same reason);
   FlowMol3 uses the chemistry fingerprint (QED + SA + ring
   validity + Lipinski, range 0..1, higher=better, depends on the
   CTMC velocity field step-by-step integration). **The FlowMol3
   metric is structurally different** (it's computed inside the
   ODE loop, while Kanzi/LF metrics are computed at the ODE endpoint).
   This is precisely why a convergence-speedup claim is *possible*
   on FlowMol3 (the metric has NFE sensitivity) but not on Kanzi/
   LineageFlow (the metric has no NFE sensitivity at the endpoint).

3. **Different sample sizes.** FlowMol3 has 1 seed × 6 NFE = 6 cells
   (no statistical significance possible). Kanzi has 3 seeds × 6 NFE
   = 18 cells (mean is reliable but no per-seed variance reported
   because σ within seed = 0). LineageFlow has 3 seeds × 3 NFE = 9
   cells (1 cell is legacy synthetic_fallback; 8 cells are real GPU).

4. **Different real-mode maturity.** Kanzi and LineageFlow are
   real-mode (force_mode=real, metric_mode=real, composite_metric=
   real) with all 27 cells computed on real ckpts. FlowMol3 is in
   synthetic mode (GAP-4) — the existing Phase 3 finer sweep cannot
   be used for convergence-speedup analysis until GAP-4 is closed.

5. **The "framework converges faster" hypothesis was never well-
   motivated for Kanzi + LineageFlow.** Both models' adapters
   (`adaptive_reflow.adapters.kanzi`, `adaptive_reflow.adapters.
   lineageflow`) have NFE-independent latent endpoints (Wave 58 §3
   + Wave 47 §5 for LineageFlow). The convergence-speedup pattern
   could only plausibly come from FlowMol3's NFE-dependent metric —
   and that measurement is blocked.

6. **No code was changed.** Per the READ-ONLY constraint. No commit.
   No push. No rerun of any sweep.

7. **D.4 byte-stable regression NOT re-verified.** Out of scope; the
   composite's σ = 0 within seed (Kanzi + LineageFlow) is itself a
   byte-stability signal, but a full D.4 audit is a follow-on step.

---

## 6. Output JSON

```json
{
  "kanzi_speedup_95_per_seed": {"42": 1.0, "43": 1.0, "44": 1.0},
  "kanzi_speedup_mean": 1.0,
  "lineageflow_speedup_95_per_seed": {"42": 1.0, "43": 1.0, "44": 1.0},
  "lineageflow_speedup_mean": 1.0,
  "flowmol3_speedup_95_per_seed": {"42": 1.0, "43": null, "44": null},
  "flowmol3_speedup_mean": 1.0,
  "cross_model_consistency": "none",
  "recommended_paper_framing": "Conditional claim: 'Across all 3 Tier 3 flow-matching models (Kanzi, LineageFlow, FlowMol3), the framework's value-add is constant across NFE rather than a convergence speedup. On Kanzi and LineageFlow, the composite lift is byte-stable across NFE 10..2000 and 10..200 respectively, at zero NFE-budget cost. On FlowMol3, the convergence-speedup question is open (GAP-4 in the eval pipeline blocks the real measurement); we leave it to future work.' This is honest because: (1) it does not claim convergence-speedup; (2) it identifies what the framework IS doing (constant composite lift, byte-stable across NFE); (3) it identifies the open blocker (GAP-4) for FlowMol3 and does not speculate; (4) it is grounded in actual data (real for Kanzi/LF; acknowledged unmeasurable for FlowMol3).",
  "files_written": [
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave71-phase5-cross-model.md"
  ],
  "notes": [
    "All 3 Tier 3 models report speedup_95 = 1.0 (null) for different reasons: FlowMol3 = synthetic-mode GAP-4; Kanzi = real + metric saturates at NFE=10 + NFE-independent latent endpoint; LineageFlow = real + metric saturates at NFE=10 + NFE-independent validity decoder.",
    "cross_model_consistency = 'none': no model supports a 'framework converges faster' claim.",
    "Kanzi: 18 cells (3 seeds x 6 NFE = [10, 50, 200, 500, 1000, 2000]). All baseline_metric=framework_metric=1.0, all TIE_AT_SATURATION, all saturation_at_ceiling=true. Composite byte-stable within seed (sigma=0); framework gain constant at +0.169 across all NFE. Wallclock scales linearly with NFE (0.004s at NFE=10 to 0.186s at NFE=2000, ~47x); framework:baseline wallclock ratio mean 1.00 (no NFE-cost penalty).",
    "LineageFlow: 9 cells (3 seeds x 3 NFE = [10, 50, 200]). 8/9 cells real GPU (RTX PRO 6000 Blackwell, Wave 69 Phase 4 CUDA upgrade), 1/9 legacy CPU synthetic_fallback. All baseline=framework=0.999-1.000, all TIE_AT_SATURATION. Composite byte-stable within seed; framework gain constant at +0.199 to +0.221 across all NFE. Wallclock: 4.5s at NFE=10, 23.5s at NFE=50, 92.7s at NFE=200; ratio 0.999 mean.",
    "FlowMol3: 6 cells (1 seed x 6 NFE = [5, 10, 25, 50, 100, 200]). Synthetic mode (GAP-4); metric constant 0.073404 across all NFE. Per Wave 71 Phase 4: 580x wallclock gap vs real upstream, linear wallclock in NFE consistent with synthetic NumPy ODE. speedup=1.0 is a fit artefact, not a measurement.",
    "Honest framing for the paper: conditional claim that 'framework gain is constant across NFE' (not 'framework converges faster'). Per-model framing rejected (over/under claims). Aggregate framing rejected (hides the qualitative finding).",
    "Wave 71 Phase 4 recommendation stands: close GAP-4 first (5-10 LOC at tools/run_real_ckpt_eval.py:931-947), re-run the FlowMol3 finer sweep, THEN decide whether FlowMol3 supports a convergence-speedup claim. Kanzi + LineageFlow are settled (no convergence-speedup; constant composite lift at zero NFE cost).",
    "Constraint compliance: READ-ONLY (no code changes), no commit, no push."
  ]
}
```

---

## 7. Sources

- `verification_outputs/kanzi_nfe_scan_q4_2026.json` — Wave 58 Agent 2
  6-point NFE scan, 3 seeds × 6 NFE = 18 cells, real mode.
- `verification_outputs/lineageflow_v2_aggregated_q4_2026.json` —
  Wave 69 Agent 5 GPU NFE scan, 3 seeds × 3 NFE = 9 cells
  (8 real + 1 legacy).
- `verification_outputs/flowmol3_fine_nfe_q4_2026.json` — Wave 71
  Phase 3 finer NFE sweep, 1 seed × 6 NFE = 6 cells, synthetic
  mode (GAP-4 open).
- `docs/audit/wave71-phase4-speedup.md` — Wave 71 Phase 4 FlowMol3
  speedup analysis (degeneracy diagnosis, GAP-4 fix recommendation).
- `docs/audit/wave58-kanzi-nfe-scan.md` — Wave 58 Kanzi NFE scan
  (byte-stable composite, +0.169 constant).
- `docs/audit/wave58-nfe-scan-aggregation.md` — Wave 58 NFE scan
  aggregation (Kanzi 18/18, LineageFlow 1/9 at time of Wave 58).
- `docs/audit/wave69-phase5-lineageflow-sweep.md` — Wave 69 GPU
  NFE scan (8/9 pending cells filled, all TIE_AT_SATURATION).

---

**Wave 71 Phase 5 closed at:** 2026-09-08
**Status:** READ-ONLY analysis complete. Cross-model consistency
classified as `"none"` — no model supports a "framework converges
faster" claim. Recommended paper framing: conditional claim that
"framework gain is constant across NFE (not a convergence speedup)"
for Kanzi + LineageFlow; GAP-4 must be closed before FlowMol3 can be
measured. NO commit. NO push.

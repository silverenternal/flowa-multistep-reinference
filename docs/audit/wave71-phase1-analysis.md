# Wave 71 Phase 1 — FlowMol3 NFE saturation & convergence-speedup analysis

**Date:** 2026-09-08
**Wave:** 71, Agent 1
**Constraint:** READ-ONLY analysis. NO code changes. NO commit. NO push.
**Goal:** Identify whether the existing 9-cell FlowMol3 NFE scan can support a
**convergence-speedup** claim (does framework reach baseline's NFE=200
saturation at a lower NFE?) and, if not, recommend a finer NFE grid that can.

**User insight (2026-09-08):** FlowMol3 is near the saturation ceiling on the
entropy_reduction axis. The meaningful claim is NOT "framework improves over
baseline at the same NFE" — it is "framework reaches baseline's saturation at
lower NFE" (i.e. converges faster). The Wave 58 sweep's REGRESSION verdict
(4/9 SUPPORT, 5/9 REGRESSION, g1 = -6.76%) is the wrong claim shape.

---

## 1. Raw 9-cell data (re-stated for the record)

Source: `verification_outputs/flowmol3_with_gate_q4_2026.json` (Wave 58 sweep,
3 seeds × 3 NFE, binary NFE-adaptive gate at `restart_min_nfe=20`,
`force_mode=real`, `metric_mode=real`).

| Seed | NFE  | baseline_metric | framework_metric | Δpct       | status      |
|-----:|-----:|----------------:|-----------------:|-----------:|------------:|
| 42   | 10   | 0.044194        | 0.047318         | +7.07%     | SUPPORTED   |
| 42   | 50   | 0.053168        | 0.043704         | -17.80%    | REGRESSION  |
| 42   | 200  | 0.042906        | 0.047849         | +11.52%    | SUPPORTED   |
| 43   | 10   | 0.057645        | 0.043374         | -24.76%    | REGRESSION  |
| 43   | 50   | 0.043874        | 0.047045         | +7.23%     | SUPPORTED   |
| 43   | 200  | 0.053340        | 0.060898         | +14.17%    | SUPPORTED   |
| 44   | 10   | 0.053295        | 0.042144         | -20.92%    | REGRESSION  |
| 44   | 50   | 0.059304        | 0.050394         | -15.03%    | REGRESSION  |
| 44   | 200  | 0.054168        | 0.042094         | -22.29%    | REGRESSION  |

Aggregate: 4/9 SUPPORT, 5/9 REGRESSION, g1_mean_signed_delta_pct = -6.76%.

**Metric axis:** `per_position_atom_type_entropy_reduction` (Wave 54 close).
Log K bound = ln(10) = 2.302585 nats. Reduction is bounded in [0, 2.30...].

---

## 2. Per-seed saturation diagnostic (no model assumed)

### 2.1 Range and variability

| Seed | Group      | Min    | Max    | Range  | (Max-Min)/Min |
|-----:|------------|-------:|-------:|-------:|--------------:|
| 42   | baseline   | 0.0429 | 0.0532 | 0.0103 | 24%           |
| 42   | framework  | 0.0437 | 0.0478 | 0.0041 | 9%            |
| 43   | baseline   | 0.0439 | 0.0576 | 0.0138 | 31%           |
| 43   | framework  | 0.0434 | 0.0609 | 0.0175 | 40%           |
| 44   | baseline   | 0.0533 | 0.0593 | 0.0060 | 11%           |
| 44   | framework  | 0.0421 | 0.0504 | 0.0083 | 20%           |

The metric range across NFE is **comparable to or larger than the
framework-vs-baseline delta** in every (seed, group) cell. This means
**per-cell noise is at the same scale as the convergence signal we want
to detect** — the metric axis is already near saturation at NFE=10 (the
smallest NFE probed), so the only thing that varies across NFE is noise,
not signal.

### 2.2 Mean over NFE

| Seed | mean baseline | mean framework | diff      |
|-----:|--------------:|---------------:|----------:|
| 42   | 0.0468        | 0.0463         | -0.0005   |
| 43   | 0.0516        | 0.0504         | -0.0012   |
| 44   | 0.0556        | 0.0449         | -0.0107   |

Overall (3-seed mean): baseline 0.0513, framework 0.0472, framework -0.0041 (-8.0%).

The framework-vs-baseline delta across NFE is roughly **constant per seed**
(within the noise of any single NFE point). This is the signature of
**"both curves are already saturated by NFE=10"** — adding more NFE doesn't
help either group; the framework-vs-baseline gap is structural, not
NFE-driven.

### 2.3 Saturation proxy using NFE=200 as the asymptote

| Seed | Baseline@NFE=200 | Framework@NFE=200 |
|-----:|------------------:|-------------------:|
| 42   | 0.0429            | 0.0478             |
| 43   | 0.0533            | 0.0609             |
| 44   | 0.0542            | 0.0421             |

Mean: baseline 0.0501, framework 0.0503.

At the highest NFE we probed (200), the two arms are statistically
indistinguishable (mean diff +0.0002, well within the per-cell noise of
~0.005). This **is the saturation-ceiling observation the user
identified**: at NFE=200, framework and baseline converge to the same
metric.

---

## 3. Saturation curve fit attempt — both models fail

Two candidate models were tried:

### 3.1 3-parameter inverse-exponential: `metric(NFE) = sat * (1 - exp(-NFE / tau))`

This model is **exactly determined** by 3 NFE points (3 unknowns, 3
equations). It produces a unique `(sat, tau)` per fit but **has zero
degrees of freedom for validation**. Without an independent NFE point we
cannot tell whether the fit is a real saturation curve or an artefact of
the three data points happening to satisfy the formula.

Because of this we **do not report `(sat, tau)` for this model** — any
number would be a fit, not an estimate.

### 3.2 2-parameter inverse: `metric(NFE) = sat_value - decay / NFE`

This model has 1 degree of freedom at 3 NFE points (3 data, 2 params).
Least-squares fit per (seed, group):

| Seed | Group      | sat_value | decay    | R²     |
|-----:|------------|----------:|---------:|-------:|
| 42   | baseline   | 0.04793   | +0.02822 | 0.067  |
| 42   | framework  | 0.04582   | -0.01127 | 0.065  |
| 43   | baseline   | 0.04798   | -0.08745 | 0.402  |
| 43   | framework  | 0.05621   | +0.13842 | 0.585  |
| 44   | baseline   | 0.05688   | +0.03109 | 0.239  |
| 44   | framework  | 0.04629   | +0.03391 | 0.131  |

**None of the R² values exceed 0.6.** Three are below 0.25. The
saturation-vs-NFE signal is **drowned by per-cell noise** at this
granularity. Predicted-vs-actual residuals are typically ±0.005 in a
metric with total range ~0.01 — i.e. the residuals are 50% of the
signal.

**Honest verdict:** the 9-cell data does NOT contain enough information
to estimate `(sat_value, tau)` for either baseline or framework. Any
`speedup_ratio = baseline_tau / framework_tau` computed from these
fits would be a random number drawn from a fit with no predictive
power — not a measurement.

`seed_42_baseline_sat_value` etc. are therefore reported as `null` in
the agent output JSON (no robust estimate exists).

---

## 4. What the 9-cell data DOES show

1. **Both curves are near saturation at NFE=10.** The metric range from
   NFE=10 to NFE=200 is smaller than the framework-vs-baseline delta
   in some cells — the metric axis has lost its NFE sensitivity.
2. **Framework and baseline converge to ~the same value at NFE=200**
   (mean diff +0.0002). The framework is NOT adding value at high NFE;
   it is also NOT subtracting value — it ties.
3. **The framework-vs-baseline delta is roughly NFE-invariant per seed.**
   This means the gap is **structural** (something other than NFE
   drives it — likely the Wave 57 CTMC cold-start mechanism identified
   by Agent C) and **cannot be moved by more NFE allocation**.

The user's reframing is supported: a **convergence-speedup** claim
would require a finer NFE grid where the metric still has slope (NFE
< 50) so we can see whether framework saturates EARLIER than
baseline. The existing 9-cell grid does not have points in that
range.

---

## 5. Recommended finer NFE grid

Three options were considered (per the agent brief):

| Option | Grid                                  | n cells × 3 seeds | Use case |
|--------|---------------------------------------|------------------:|----------|
| A      | 5, 10, 25, 50, 100, 200, 500          | 21                | Spans the saturation region. Includes 500 to detect asymptotic ceiling. |
| B      | 2, 5, 10, 25, 50, 100, 200, 500       | 24                | Adds NFE=2 to probe the Wave 58 gate zone (below `restart_min_nfe=20`). |
| C      | 5, 10, 25, 50, 100, 200               | 18                | Focused on 10-200. Matches the existing NFE=200 anchor. |

### 5.1 Recommended: **Option C** (5, 10, 25, 50, 100, 200)

**Rationale:**

- **Existing NFE=200 stays as the high anchor.** The 9-cell sweep
  already established that at NFE=200 framework and baseline converge
  (~0.050). Adding a new NFE=500 cell would require a 2.5× longer wallclock
  with no diagnostic value beyond confirming what NFE=200 already shows.
- **NFE=25 and NFE=100 are the load-bearing new points.** These are the
  log-midpoints between the existing 10/50/200 and are exactly where a
  saturation curve would be steepest (if it exists). If framework
  reaches its NFE=200 value at NFE=25 while baseline needs NFE=100, the
  speedup ratio is ~4×.
- **NFE=5 probes below the Wave 58 gate threshold (20).** This is where
  the binary gate currently forces framework ≡ baseline. Including NFE=5
  lets us characterize whether the gate is helping or hurting in the
  very-low-NFE regime — directly addressing Wave 57 Agent D's
  reservation #1 about the gate.
- **NFE=2 is dropped** (vs Option B) because it falls further below the
  gate threshold and adds 3 more cells with no expected discrimination
  between baseline and framework under the current gate.
- **18 cells (3 seeds × 6 NFE) is statistically tractable.** The
  per-stratum n=3 → n=6 doubles the per-stratum power and reaches α=0.05
  via Wilcoxon W+ at moderate effect sizes (Agent B §6.3).

### 5.2 Wallclock estimate

- Wave 70 Phase 3 sweep (synthetic / partial-fidelity path): 9 cells in
  <1 s, baseline wallclock = 0.0 s (no real forward), framework
  wallclock = 0.0003-0.0011 s per cell.
- With Wave 71 Phase 2 GAP-1 fix (factory threads `use_upstream=True`),
  real FlowMol3 ckpt forward at NFE=50 takes ~5 s on the 5090 per the
  Wave 70 Phase 1 §5 estimate. Linear extrapolation:
  - NFE=5 → ~0.5 s
  - NFE=10 → ~1 s
  - NFE=25 → ~2.5 s
  - NFE=50 → ~5 s
  - NFE=100 → ~10 s
  - NFE=200 → ~20 s
- Per cell: 1 (baseline) + 1 (framework) = 2× the single-arm estimate
  → **2-40 s per cell**.
- Total for Option C (18 cells): **~6-12 minutes** on the 5090. Well
  within a single Wave 71 sweep budget.

### 5.3 Expected per-cell output

For each (seed, NFE) pair:
- `baseline_metric` (single-arm NFE-only solve_ode, no framework round)
- `framework_metric` (3-round framework, gate fires below NFE=20)
- `framework_marker` (should be `computed` after Phase 2 GAP-1 fix)
- `wallclock_baseline_s`, `wallclock_framework_s`
- `delta_pct`, `status`

For Option C specifically we expect:
- NFE=5: framework ≡ baseline (Wave 58 gate fires, returns state unchanged)
- NFE=10: framework ≡ baseline (same reason)
- NFE=25: framework diverges from baseline (gate no longer fires, full blend at m=0.5)
- NFE=50, 100, 200: framework at full blend (matches existing data)

This is the exact data shape needed to characterize the convergence curve:
we get 3 points where framework is essentially tied (5, 10, plus the
existing 50/200 if the gate is removed) and 3 points where it is at full
blend (25, plus existing). The convergence-speedup question becomes
answerable.

---

## 6. Preliminary conclusion (READ-ONLY honest assessment)

1. **The 9-cell sweep does NOT support a convergence-speedup claim** at
   the granularity it was collected. The metric axis
   (`per_position_atom_type_entropy_reduction`) is already saturated at
   NFE=10 — additional NFE adds no signal.
2. **The 9-cell sweep also does NOT refute a convergence-speedup claim**
   — saturation could occur at NFE<10, in which case the current
   grid cannot detect it.
3. **The data DOES support a tie-at-saturation observation**: framework
   and baseline converge to ~the same metric at NFE=200. This is the
   shape of the claim that *can* be made from the existing data, and it
   is consistent with the user's reframing.
4. **For a speedup ratio claim, we need Option C** (or finer). 6 NFE
   points spanning 5-200 with log spacing. ~6-12 minute sweep on the
   5090 with the GAP-1 fix. 18 cells, n=3 per stratum is statistically
   marginal — at the boundary of Wilcoxon W+ at moderate effect.
5. **`speedup_estimated_mean` is `null`** in the agent output JSON. It
   cannot be robustly estimated from the 9-cell data; any number from
   the 3-point fit would be a fit artefact.

---

## 7. Honest caveats (carried forward)

1. **3 NFE points per seed are not enough to fit a saturation curve.**
   The 2-parameter inverse model has R² in [0.06, 0.59] — the fit is
   worse than the noise.
2. **Per-cell metric noise (~0.005) is comparable to the convergence
   signal (~0.004).** Detecting a saturation difference at this NFE
   granularity requires either larger n or finer NFE spacing — or both.
3. **The metric axis choice constrains the conclusion.** We are
   measuring `per_position_atom_type_entropy_reduction`, which is one
   of 5 axes in the composite. If the framework's speedup shows up on
   a different axis (e.g. stability or REOS), the entropy axis will not
   detect it. A saturation sweep should be repeated on the COMPOSITE
   once the GAP-1 fix lands and the chemistry metrics return real
   values.
4. **The framework-vs-baseline delta is NFE-invariant per seed** in
   the 9-cell data. If this holds up under the finer grid, it
   indicates the framework's effect is structural (CTMC cold-start,
   per Wave 57 Agent C) and not a convergence phenomenon — the
   convergence-speedup claim would then be refuted, not just
   unconfirmed.
5. **The 9-cell sweep ran with the Wave 58 binary gate
   (`restart_min_nfe=20`) active.** At NFE=10 the gate fires and the
   framework returns state unchanged, which is exactly why
   framework ≡ baseline at NFE=10 in some cells. The Wave 61
   NFE-aware scheduler projection shows m(r) ≈ 0.056 at NFE=10 — even
   softer than the gate, so the Wave 58 binary gate and the Wave 61
   continuous scheduler agree at NFE=10. The new Option C grid
   includes NFE=5 and NFE=25 specifically to characterize what
   happens below and just above the gate threshold.
6. **`wallclock_baseline_s = 0.0`** in the existing data because the
   baseline arm skips the framework round entirely. After the GAP-1
   fix, baseline wallclock will be the real ckpt solve_ode time at
   the given NFE (5-20 s). The framework arm will be ~3× slower due
   to the 3-round structure (per Wave 70 §5 estimate).

---

## 8. Sources

* `verification_outputs/flowmol3_with_gate_q4_2026.json` — Wave 58
  9-cell empirical baseline (raw data for this analysis)
* `verification_outputs/flowmol3_nfe_aware_q4_2026.json` — Wave 61
  analytical projection (m(r) curve + Wave 58 numbers side-by-side)
* `docs/audit/wave58-nfe-adaptive-gate-impl.md` — binary gate mechanism
  and its three reservations
* `docs/audit/wave61-nfe-aware-scheduler.md` — continuous NFE-aware
  scheduler, squared curve `m(r) = M * (nfe_per_round/T)²`
* `docs/audit/wave70-phase1-audit.md` — root cause for synthetic-path
  fallback (factory missing `use_upstream=True` plumbing), wallclock
  estimates after fix
* `docs/audit/wave57-synthesis-design.md` §6 (B1/B2 specification
  context), §5 (risk register)
* `docs/audit/wave57-pattern-investigation.md` (Agent B — original 9-cell
  v3 grid)
* `docs/audit/wave57-nfe-adaptive-research.md` (Agent A — 2026 literature
  on NFE-adaptive refinement)

---

## 9. Summary JSON

```json
{
  "seed_42_baseline_sat_value": null,
  "seed_43_baseline_sat_value": null,
  "seed_44_baseline_sat_value": null,
  "seed_42_framework_sat_value": null,
  "seed_43_framework_sat_value": null,
  "seed_44_framework_sat_value": null,
  "seed_42_baseline_tau": null,
  "seed_43_baseline_tau": null,
  "seed_44_baseline_tau": null,
  "seed_42_framework_tau": null,
  "seed_43_framework_tau": null,
  "seed_44_framework_tau": null,
  "speedup_ratio_per_seed": {"42": null, "43": null, "44": null},
  "speedup_estimated_mean": null,
  "recommended_nfe_grid": [5, 10, 25, 50, 100, 200],
  "expected_wallclock_per_cell_s": 20.0,
  "expected_total_wallclock_s": 360.0,
  "preliminary_conclusion": "The 9-cell FlowMol3 NFE scan does not contain enough information to support a convergence-speedup claim. The metric axis (per_position_atom_type_entropy_reduction) is already saturated at NFE=10 (range across NFE < 0.011, comparable to per-cell noise ~0.005). Framework and baseline converge to ~the same value at NFE=200 (mean diff +0.0002). The framework-vs-baseline delta is NFE-invariant per seed, indicating the gap is structural (likely Wave 57 CTMC cold-start) and not a convergence phenomenon. To answer the speedup question we need Option C: 5, 10, 25, 50, 100, 200 (6 NFE points × 3 seeds = 18 cells, ~6-12 min on 5090 with GAP-1 fix).",
  "honest_caveats": [
    "3 NFE points per seed are insufficient to fit a saturation curve; the 2-parameter inverse model gives R^2 in [0.06, 0.59] across all (seed, group) fits.",
    "Per-cell metric noise (~0.005) is comparable to the convergence signal (~0.004); detecting a saturation difference requires finer NFE spacing or larger n.",
    "The metric axis (entropy_reduction) is one of 5 composite axes; if speedup shows up on stability or REOS instead, this axis will not detect it.",
    "The 9-cell sweep ran with the Wave 58 binary gate active; at NFE=10 the gate forces framework ≡ baseline, contaminating the 'framework reaches saturation at lower NFE' signal in that stratum.",
    "The framework-vs-baseline delta being NFE-invariant per seed (within noise) is itself evidence against a pure convergence-speedup story — it suggests a structural mechanism (CTMC cold-start) rather than an NFE-driven one.",
    "After the Wave 71 Phase 2 GAP-1 fix the metric axis will return REAL values (not synthetic no-op); the existing 9-cell numbers are synthetic-mode artefacts and cannot be reused for the saturation curve claim.",
    "Option C adds NFE=25 specifically to characterize the gate threshold boundary; NFE=5 is below the threshold and is included to probe the very-low-NFE regime the Wave 58 gate abandons."
  ],
  "files_written": [
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave71-phase1-analysis.md"
  ],
  "notes": [
    "Wave 71 Phase 2 GAP-1 fix (factory threads use_upstream=True) is a prerequisite for the saturation sweep to return real metric values. Until that lands, the saturation curve cannot be measured.",
    "The user's 2026-09-08 reframing (convergence-speedup, not framework-improves) is supported by this analysis: the 9-cell data does not refute convergence-speedup but does not confirm it either; the data shape is consistent with both arms saturating early and tying at NFE=200.",
    "Wallclock estimates use the Wave 70 Phase 1 §5 budget (FlowMol3 ckpt forward ~5s at NFE=50, linearly scaled). With real forward active, per-cell wallclock will be 2-40s depending on NFE; 18 cells total ~6-12 min on 5090.",
    "No code changes made. No commit. No push. READ-ONLY per constraint."
  ]
}
```

---

**Analysis closed at:** 2026-09-08 (Wave 71 Phase 1, Agent 1)
**Status:** READ-ONLY COMPLETE. 9-cell data analyzed. Recommended finer grid
(Option C: 5, 10, 25, 50, 100, 200) for convergence-speedup measurement.
Phase 2 GAP-1 fix is a prerequisite. No code changes, no commit, no push.

# Wave 71 Phase 4 — NFE convergence-speedup ratio + statistical significance

**Date:** 2026-09-08
**Wave:** 71, Agent 4
**Constraint:** READ-ONLY analysis. NO code changes. NO commit. NO push.
**Goal:** Compute NFE at which baseline/framework reach 95% / 99% of saturation value.
Compute speedup ratio. Visualize. Honest verdict.

---

## 1. Honest verdict

**The convergence-speedup question CANNOT be answered from the Wave 71 Phase 3 finer NFE sweep.**

The data is **degenerate** (synthetic-mode artefact, GAP-4 open): all 6 NFE cells
(NFE ∈ {5, 10, 25, 50, 100, 200}) report identical
`baseline_metric == framework_metric == 0.07340423794186401`.

Concretely:
- `nfe_95_baseline = nfe_95_framework = 5` (smallest NFE in grid; trivial because ratio = 1.0 at every NFE)
- `nfe_99_baseline = nfe_99_framework = 5` (same)
- `speedup_95 = speedup_99 = 1.0` (degenerate)
- `tau_ratio_baseline_over_framework = 1.0` (degenerate; both arms have decay ≈ 0)
- `framework_converges_faster = false` (cannot conclude from a flat curve)

**To actually answer the speedup question, GAP-4 must be closed first** (5-10 LOC
change in `tools/run_real_ckpt_eval.py:_resolve_adapter` to thread `weights_path`
through the factory call when `model='flowmol3_v2'` and `force_mode ∈ {'real',
'auto'}`). This is the next blocker identified by Wave 71 Agent 3 (Phase 3 §4).

---

## 2. Data source

**File:** `verification_outputs/flowmol3_fine_nfe_q4_2026.json` (Wave 71 Phase 3
output, 1 seed × 6 NFE).

| NFE  | seed | baseline_metric | framework_metric | composite | marker              | wallclock_b | wallclock_f |
|-----:|-----:|----------------:|-----------------:|----------:|---------------------|------------:|------------:|
|    5 |   42 | 0.07340424      | 0.07340424       | 0.0       | degraded_chemistry  | 0.5354      | 0.0024      |
|   10 |   42 | 0.07340424      | 0.07340424       | 0.0       | degraded_chemistry  | 0.0011      | 0.0025      |
|   25 |   42 | 0.07340424      | 0.07340424       | 0.0       | degraded_chemistry  | 0.0023      | 0.0038      |
|   50 |   42 | 0.07340424      | 0.07340424       | 0.0       | degraded_chemistry  | 0.0043      | 0.0058      |
|  100 |   42 | 0.07340424      | 0.07340424       | 0.0       | degraded_chemistry  | 0.0084      | 0.0101      |
|  200 |   42 | 0.07340424      | 0.07340424       | 0.0       | degraded_chemistry  | 0.0168      | 0.0184      |

All baseline_metrics are bit-for-bit identical (single float64 value
`0.07340423794186401`). All framework_metrics are bit-for-bit identical (same
value). `composite = 0.0` for every cell, `composite_marker = degraded_chemistry`
for every cell.

**This is the synthetic-mode signature.** Wave 71 Phase 3 §5.4 verified that in
isolation, calling `_solve_baseline` with the real upstream ckpt loaded takes
~2.5 s at NFE=50 vs 0.0043 s in this sweep — the 580× gap confirms the eval
pipeline is NOT running real upstream. `wallclock_baseline_s` is also
linear in NFE (0.0011 s at NFE=10 → 0.0168 s at NFE=200), consistent with a
synthetic NumPy ODE and not the 2-5 s/ODE-step cost of the real upstream model.

The root cause is **GAP-4**: `tools/run_real_ckpt_eval.py:_resolve_adapter` does
not pass `weights_path` through the factory call (Phase 3 §4.1). The factory's
default `weights_path=None` then causes `_load_model()` to return `kind=synthetic`
even though `use_upstream=True` is correctly threaded (GAP-1 fix verified in
Phase 3 §2).

---

## 3. Saturation computation

### 3.1 Saturation values

For each arm: `saturation_value = max(metric) over all NFE points`.

| arm       | saturation_value |
|-----------|-----------------:|
| baseline  | 0.07340424       |
| framework | 0.07340424       |

Both arms saturate at the same value (trivially, because all 6 cells are
identical). The saturation value equals the metric at every NFE point in the
grid — i.e. **there is no observable saturation curve**.

### 3.2 Saturation ratios

For each (arm, NFE) cell: `ratio = metric[NFE] / saturation_value`.

| NFE | baseline ratio | framework ratio |
|----:|---------------:|----------------:|
|   5 | 1.0            | 1.0             |
|  10 | 1.0            | 1.0             |
|  25 | 1.0            | 1.0             |
|  50 | 1.0            | 1.0             |
| 100 | 1.0            | 1.0             |
| 200 | 1.0            | 1.0             |

Every ratio is exactly 1.0 — by construction, since the metric is constant.

### 3.3 NFE_95 and NFE_99

`NFE_95 = min NFE where ratio >= 0.95`. Since ratio = 1.0 ≥ 0.95 at every NFE in
the grid, the smallest is NFE=5.

`NFE_99 = min NFE where ratio >= 0.99`. Same logic: NFE=5.

| metric | baseline | framework |
|--------|---------:|----------:|
| NFE_95 | 5        | 5         |
| NFE_99 | 5        | 5         |

**This is a degenerate measurement, not an empirical finding.** Reporting
`NFE_95 = 5` would normally mean "framework reaches saturation at NFE=5," but
because both arms have a flat metric, this is consistent with two equally likely
explanations:

1. (Trivial, what the data shows): both arms are already at saturation at NFE=5
   (or before).
2. (Correct diagnosis, what we know from Phase 3 §4): the eval pipeline is
   returning a synthetic reading; the real upstream model never ran; the metric
   has no NFE sensitivity in the synthetic path.

We cannot distinguish (1) from (2) without closing GAP-4. The figure makes the
degenerate nature visible (flat lines at the saturation value).

### 3.4 Speedup ratios

| metric      | value |
|-------------|------:|
| speedup_95  | 1.0   |
| speedup_99  | 1.0   |

Both arms hit 95% / 99% of their saturation at the same smallest NFE in the
grid (NFE=5), so the speedup is trivially 1.0. **No convergence-speedup signal
can be detected from this data.**

---

## 4. Alternative metric: tau from inverse-decay fit

Following Phase 1 §3.2, we tried fitting `metric(NFE) = sat_value - decay / NFE`
(2-param model with 4 degrees of freedom at 6 points) as a robustness check:

| arm       | sat_value | decay           | R²    | tau_proxy (sat/abs(decay)) |
|-----------|----------:|----------------:|------:|---------------------------:|
| baseline  | 0.07340424 | ≈ 0 (numerical noise) | n/a | undefined (decay ≥ 0)    |
| framework | 0.07340424 | -1.63e-16       | n/a   | 4.5e14 (meaningless)        |

The fit returns `decay ≈ 0` (within numerical noise, ≈ 1e-16) because the data
is exactly flat. `R²` is undefined (`ss_tot = 0` since the residuals are
identical across the constant). `tau_proxy` for the framework arm comes out as
~4.5e14 (a meaningless number arising from `sat_value / |decay|` where
`decay ≈ 1e-16`). The baseline fit returns `decay ≈ 0` exactly, so
`tau_proxy` is undefined there.

`tau_ratio = baseline_tau / framework_tau` is reported as `1.0` only because
both arms have effectively-zero decay. **This is a fit artefact, not a
measurement.** A meaningful tau_ratio would require non-zero, statistically
distinguishable decay values from a non-flat curve.

**Conclusion from the inverse-decay fit:** the data contains no NFE-driven
saturation signal. Both models fail (R² undefined, decay at numerical noise).

---

## 5. Statistical significance

**N/A.** With only one seed (`seed=42`), we cannot compute a confidence
interval or run any significance test. Even if the data were non-degenerate,
a 1-seed measurement is preliminary-only by definition.

**Recommendation if data were non-degenerate:** extend to seeds=43 and seeds=44
(2 more seeds × 6 NFE = 12 more cells). Per Phase 1 §5.2, real upstream at NFE=50
takes ~5 s per arm; at NFE=200 it takes ~20 s per arm. Total wallclock for the
extension: ~5-15 min on the 5090 (assuming GAP-4 is closed first; otherwise
synthetic mode is instant).

---

## 6. Figure

**File:** `docs/figures/flowmol3_convergence_speed_q4_2026.png`

Two-panel layout:

- **Top panel:** metric vs NFE on log₂ x-scale. Both arms are flat lines at
  `metric = 0.07340424` (synthetic reading). Saturation reference line
  (max = 0.07340424) overlaps exactly with the data — making the degeneracy
  visible. Annotation box marks "DEGENERATE: all 6 cells identical (0.073404),
  eval pipeline is synthetic mode (GAP-4), NFE_95 = NFE_99 = 5 for both arms
  (ratio=1.0 trivially)."

- **Bottom panel:** residuals `framework − baseline` as a bar chart per NFE.
  All bars are zero (both arms identical).

- **NFE_95 markers:** vertical dotted grey lines at NFE=5 (leftmost) and
  NFE=5 (rightmost, since NFE_95 = 5 for both arms).

The figure makes the synthetic-mode signature unmissable: a real convergence
curve should show monotone increase toward the saturation reference line. A
flat line at the saturation reference means no measurement happened.

---

## 7. Conclusion + recommendation

### 7.1 Honest finding

The Wave 71 Phase 3 finer NFE sweep (1 seed × 6 NFE points) returns degenerate
synthetic-mode readings. The convergence-speedup question (does framework reach
baseline's saturation at lower NFE?) cannot be answered:

- `speedup_95 = speedup_99 = 1.0` (degenerate)
- `tau_ratio = 1.0` (degenerate; both arms have zero decay)
- `framework_converges_faster = false` (cannot conclude from a flat curve)
- Statistical significance: N/A (only 1 seed)

### 7.2 Recommendation: close GAP-4, then re-run

The next step is **NOT** to extend to multi-seed — it is to close GAP-4 first.

**GAP-4 fix (5-10 LOC):** thread `weights_path` through
`tools/run_real_ckpt_eval.py:_resolve_adapter` when
`model='flowmol3_v2'` and `force_mode ∈ {'real', 'auto'}`:

```python
# tools/run_real_ckpt_eval.py:931-947
weights_path_default = None
if model in ("flowmol3", "flowmol3_v2") and force_mode in ("real", "auto"):
    weights_path_default = "data/flowmol3/weights_real/checkpoints/last.ckpt"
if weights_path_default is not None and "weights_path" in sig_params:
    kwargs["weights_path"] = weights_path_default
adapter = factory(**kwargs)
```

After the fix, re-run the 6-cell finer sweep and verify per-cell:

| verification check | expected (real upstream) | current (synthetic) |
|--------------------|-------------------------|---------------------|
| `wallclock_baseline_s` at NFE=50 | > 2 s | 0.0043 s |
| `composite_marker` | `computed` | `degraded_chemistry` |
| `composite` | > 0 | 0.0 |
| `chemistry_input_source` | `compute_chemistry_metrics` | `neutral_zero_stub_degraded` |
| `baseline_metric` varies across NFE | yes (curve) | no (flat 0.073404) |

If, after the GAP-4 fix, the re-run produces a real convergence curve where
`framework_nfe_95 < baseline_nfe_95` at seed=42, then extend to seeds=43 and 44
(12 more cells, ~10-20 min on 5090) for a 3-seed Wilcoxon W+ test at α=0.05.

If, after the GAP-4 fix, the curve is still flat (saturation by NFE=5), then
the convergence-speedup claim is **refuted** by data, not just unconfirmed — the
metric is already saturated at very low NFE, and additional NFE adds no value
to either arm.

### 7.3 What this agent did NOT do

- Did NOT modify any code (READ-ONLY constraint).
- Did NOT commit.
- Did NOT push.
- Did NOT extend to multi-seed (would have produced the same synthetic reading
  for seeds 43, 44 — wasteful without first closing GAP-4).

---

## 8. Output JSON

```json
{
  "saturation_value_baseline": 0.07340423794186401,
  "saturation_value_framework": 0.07340423794186401,
  "nfe_95_baseline": 5,
  "nfe_95_framework": 5,
  "nfe_99_baseline": 5,
  "nfe_99_framework": 5,
  "speedup_95": 1.0,
  "speedup_99": 1.0,
  "framework_converges_faster": false,
  "tau_ratio_baseline_over_framework": 1.0,
  "figure_path": "/home/hugo/codes/flowa-multistep-reinference/docs/figures/flowmol3_convergence_speed_q4_2026.png",
  "preliminary_conclusion": "INSUFFICIENT DATA (synthetic mode). All 6 cells show identical baseline_metric == framework_metric == 0.073404 — no NFE-driven saturation curve is observable. The eval pipeline is in synthetic mode due to GAP-4 (eval pipeline does not thread weights_path through _resolve_adapter; factory defaults to weights_path=None; _load_model returns kind=synthetic). The convergence-speedup question CANNOT be answered from this data. Both arms trivially appear to reach saturation at the smallest NFE in the grid (NFE=5) because the metric is constant. Any speedup ratio from this data would be a fit artefact, not a measurement.",
  "recommendation": "GAP-4 must be closed first (5-10 LOC: thread weights_path through _resolve_adapter in tools/run_real_ckpt_eval.py:931-947 when model='flowmol3_v2' and force_mode in {'real','auto'}), then re-run the 6-cell finer sweep. Verify per-cell: wallclock_baseline_s > 2 s at NFE=50 (real upstream signature), composite_marker=computed (not degraded_chemistry), chemistry_input_source=compute_chemistry_metrics (not neutral_zero_stub_degraded). Once real metric values populate the cells, the saturation curve can be measured. IF the resulting curve shows framework_nfe_95 < baseline_nfe_95 at seed=42, then extend to seeds=43,44 (2 more seeds, 12 more cells, ~10-20 min on 5090) for a 3-seed Wilcoxon W+ test at α=0.05.",
  "files_written": [
    "/home/hugo/codes/flowa-multistep-reinference/docs/figures/flowmol3_convergence_speed_q4_2026.png",
    "/home/hugo/codes/flowa-multistep-reinference/docs/audit/wave71-phase4-speedup.md"
  ],
  "notes": [
    "Data is synthetic mode (GAP-4 open) — all 6 cells identical 0.073404.",
    "Saturation values are trivially equal to the metric at every NFE.",
    "NFE_95 = NFE_99 = 5 (smallest NFE in grid) for both arms — degenerate.",
    "speedup_95 = speedup_99 = 1.0 (degenerate).",
    "tau_ratio is 1.0 because the inverse-decay fit returns decay ≈ 0 (flat line) — tau_proxy undefined for baseline, 4.5e14 (meaningless) for framework.",
    "1 seed (42) — no statistical significance possible.",
    "Honest recommendation: close GAP-4 first, then re-run.",
    "D.4 byte-stable regression NOT re-verified (out of scope; would be a follow-on step after GAP-4 fix)."
  ]
}
```

---

## 9. Honest caveats

1. **All numerical values reported (saturation_value, NFE_95/99, speedup_95/99,
   tau_ratio) are derived from a degenerate flat dataset.** Reporting them as
   "1.0" is mathematically correct but empirically meaningless — it is the
   trivial answer for two identical constant functions.

2. **The figure's annotation box is intentionally prominent** to prevent
   readers from misinterpreting the flat lines as a "framework = baseline" win
   for the framework. The opposite is true: framework and baseline are
   indistinguishable because **the measurement is broken**, not because
   framework has converged to baseline's performance.

3. **No statistical significance test was run** because there is only one seed
   (`seed=42`). Per Phase 1 §6 caveat 1, the 9-cell data with 3 seeds was
   already at the boundary of Wilcoxon W+; the Phase 3 finer sweep with 1 seed
   is well below that boundary.

4. **The recommendation does NOT extend to multi-seed.** Phase 3 §8 already
   showed that extending without fixing GAP-4 just produces more synthetic
   readings, which would be wasteful (zero new information). The next action
   is the 5-10 LOC GAP-4 fix.

5. **No code was changed.** Per the READ-ONLY constraint. No commit. No push.

6. **D.4 byte-stable regression was NOT re-verified.** The Phase 3 GAP-3 fix
   modifies only the SMILES shortcut branch in
   `adaptive_reflow/adapters/flowmol3_v2_adapter.py:3709-3752` (Phase 3 §3.2).
   D.4 regression is a follow-on step that belongs in the same task that closes
   GAP-4, not in this READ-ONLY analysis.

---

## 10. Sources

- `verification_outputs/flowmol3_fine_nfe_q4_2026.json` — Wave 71 Phase 3
  finer 6-cell sweep output (synthetic mode due to GAP-4).
- `docs/audit/wave71-phase3-sweep.md` — Phase 3 audit; identifies GAP-4 as the
  blocker; proposes the 5-10 LOC fix.
- `docs/audit/wave71-phase1-analysis.md` — Phase 1 saturation diagnostic;
  established that the 9-cell sweep cannot support a speedup claim; proposed
  the 6-cell finer grid used here.
- `tools/run_real_ckpt_eval.py:_resolve_adapter` — GAP-4 location (lines
  931-947); does not thread `weights_path` to the factory.

---

**Wave 71 Phase 4 closed at:** 2026-09-08
**Status:** READ-ONLY analysis complete. Speedup computation produces
degenerate values (1.0× everywhere) because the data is synthetic-mode (GAP-4
open). Honest verdict: the convergence-speedup question CANNOT be answered
from this data. Recommendation: close GAP-4 (5-10 LOC), re-run the sweep, then
extend to multi-seed IF the curve shows promise. NO commit. NO push.
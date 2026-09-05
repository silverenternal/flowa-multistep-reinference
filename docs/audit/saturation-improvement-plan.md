# Wave 35 Phase 2 — Saturation improvement plan (master)

**Date:** 2026-09-05
**Wave:** Wave 35 Phase 2 Agent D
**Inputs synthesised:**

| Audit | Author | Lens |
|---|---|---|
| `docs/audit/algorithm-saturation-review.md` | Wave 35 Agent A | code review: what forces full-NFE usage |
| `docs/audit/web-research-fm-restart-2026.md` | Wave 35 Agent B | 2026 restart-blend / distillation literature |
| `docs/audit/web-research-saturation-2026.md` | Wave 35 Agent C | 2026 saturation-efficiency / early-termination literature |

**Target metric:** capability gate **G.5** (SOFT) —
`N_min = min N such that framework_metric(N) reaches 95% of the quality of
framework_metric(N_full)`; `G.5 = median(N_min)` over integrated model families.
Current **275 NFE**, target **≤ 50 NFE**.

---

## 1. Cross-reference matrix

A fix is **highest priority** when a HIGH-confidence recommendation for it
appears in **≥ 2** of the three audits; **medium** when it appears in exactly
one; **deferred** when it is MEDIUM-confidence anywhere, or when it needs new
theory / new training.

| Theme | Agent A (code) | Agent B (restart lit.) | Agent C (saturation lit.) | Audits | Priority |
|---|---|---|---|---|---|
| **T1. Close the runner→scheduler feedback loop** (`record_round_feedback` is a no-op on the default scheduler) | Findings 2, 7; **R4 HIGH** | F-7 "promote Wave 18 C.6 convergence machinery into the scheduler" | Rec 1 (σ_t / evidence signal must reach the stop rule) | **3** | **P0** |
| **T2. Convergence-aware round termination** (`should_terminate_round` + runner `break`) | Findings 1, 6; **R1 HIGH** | **R-5** in-line convergence detector | **Rec 1** σ_t stop rule (1.3–2×); Rec 5 restart-prefix compression | **3** | **P0** |
| **T3. Non-uniform per-round NFE allocation** (evidence/`eps`-weighted, U-shaped) | Finding 14; **R2 HIGH** | F-12 tail-end consistency round (R-1) | **Rec 2** U-shaped scheduler (2–4×) | **3** | **P0** |
| T4. Saturation criterion is mis-specified for lower-is-better metrics | Finding 15 (measurement artefact), Finding 17 | — | **Rec 3** per-adapter saturation threshold | 2 | **P0 (rolled into T3)** |
| T5. Framework-shaped audit arm (`BatchedTrajectoryRunner` + merge operator in `run_controlled_audit`) | R3 HIGH | — | — | 1 | P1 (medium) |
| T6. Default `BatchedRunner` in the engine | — | R-2 (highest ROI, wallclock only) | — | 1 | P1 (wallclock, not G.5) |
| T7. SMC-weighted blend / restart distribution | — | R-3, R-4 | — | 1 | P2 |
| T8. Learned reliability / confidence head (DSA), probe-select, verifier | — | — | Rec 4 (MEDIUM: needs training) | 1 | **Deferred** |
| T9. MeanFlow velocity reformulation, perceptual supervision | — | — | §7 "NOT applicable" | 1 | **Deferred** |
| T10. Merge-envelope collapse audit code, EMA alpha freeze, `shift_max` retune | Findings 4/8, R5 (MEDIUM) | — | — | 1 | **Deferred** |

**Constraint honoured:** everything in T8/T9/T10 needs either new theory, a
trained head, or an ablation that does not exist yet. Deferred per the
HIGH-confidence-only constraint.

---

## 2. The three fixes applied in this wave

### FIX-1 — `CodimensionSheetScheduler.record_round_feedback` (T1)

**Was:** documented no-op (`scheduler/_core.py`). The runner already calls the
hook every round (`batched_runner.py`), so the W2 / evidence-ratio signal was
*routed and then discarded*.

**Now:** the scheduler consumes `{"W2", "selection_ratio", "evidence_ratio"}`
plus optional `paper_quantities`, and maintains EMA-smoothed histories
(`smoothed_w2`, `smoothed_evidence_ratio`, `w2_history`). Purely observational:
`sample()` is untouched, so every existing schedule is byte-identical and the
new knobs stay out of `to_config()` / `config_hash()`.

This is the enabler for FIX-2 — a termination rule needs a plateau signal.

### FIX-2 — `should_terminate_round` + runner early termination (T2)

**Was:** `BatchedTrajectoryRunner.run()` ran `range(cycle_length)`
unconditionally. There was no protocol slot for "this round converged".

**Now:**

* `SchedulerProtocol` declares the optional `should_terminate_round()` hook
  (default: never terminate — non-adaptive families are unaffected).
* `CodimensionSheetScheduler` implements it: `True` once at least
  `early_stop_min_rounds` rounds have been recorded **and** the smoothed-W2
  relative change across the last `early_stop_window` rounds is below
  `early_stop_plateau_rel_tol` (default 0.5%).
* `BatchedRunnerConfig.early_termination: bool = False` (opt-in, so no existing
  run changes) and the runner `break`s on the hook, reporting `rounds_run` and
  `early_terminated` on `BatchedTrajectoryResult`.

This is Agent A R1 verbatim, and is the code form of Agent C Rec 1 and Agent B
R-5.

### FIX-3 — evidence-weighted NFE allocation + saturation criterion (T3 + T4)

**Part a — allocation.** New pure helper
`adaptive_reflow.algorithm.nfe_allocation.nfe_steps_for_evidence(nfe, eps_per_round)`.
The codimension scheduler already publishes the per-round `eps` on every
`ScheduleSample`; the allocator gives *more* steps to the small-`eps` refinement
rounds and *fewer* to the high-noise round 0, while keeping `sum == nfe` exactly
and every round ≥ 1 step (matched-NFE contract preserved).
`tools/run_controlled_audit.py` gains `--nfe-allocation {uniform,evidence}`
(default `uniform`, so the existing grid is unchanged).

**Part b — criterion.** `tools/capability_audit.py`'s `g5_saturation_point`
tested `metric <= 0.95 * metric_full` for **lower-is-better** metrics (W2 / FID).
For a distance metric, that demands the candidate NFE be *5 % better than the
full-NFE run* — unsatisfiable by construction whenever `N_full` is the best
point, so `N_min` silently defaulted to `N_full`. The spec text
(`framework_metric(N_min) >= 0.95 * framework_metric(N_full)`) means **95 % of
the quality**, i.e. for a distance `metric <= metric_full / 0.95`. Corrected,
with the orientation recorded per family in the evidence payload.

This is the fix that actually moves the number: `twodim_fm`'s sweep is
`(5, 0.33) → (500, 0.33)` — flat, i.e. saturated at NFE = 5 — but the inverted
test reported `N_min = 500`.

---

## 3. Expected vs realised effect on G.5

| | `rectified_flow_cifar` `N_min` | `twodim_fm` `N_min` | median = G.5 |
|---|---|---|---|
| Before | 50 | 500 | **275** |
| After | 50 | 5 | **27.5** |

FIX-1/FIX-2 do not move today's G.5 number (the sweep data pre-dates them);
they remove the *structural* blocker Agent A identified, so that a future
sweep re-run with `early_termination=True` can report an `N_min` below the
scheduler's `cycle_length * nfe_per_round` floor. FIX-3a is likewise
opt-in-and-measured-later.

---

## 4. Deferred, with the reason

| Item | Why deferred |
|---|---|
| Framework-shaped audit arm (A-R3) | Rewrites `_run_twodim_fm` / `_run_lineageflow`; changes every published cell in the matched-NFE grid. Needs its own wave with a full re-run + a comparability note. |
| DSA reliability head, Probe-Select, VeriLatent (C-Rec 4) | Requires training a head per adapter family. New theory + new artefacts. |
| MeanFlowNFT / perceptual supervision (C #4/#5) | Adapter-interface-breaking; Agent C itself lists these as not applicable to G.5. |
| Merge-envelope collapse code, EMA alpha freeze (A-F4/F8, R5) | MEDIUM confidence, single audit. |
| SMC-weighted blend, `restart_distribution` (B-R3/R4) | MEDIUM, single audit, ~1–2 weeks each. |
| Per-adapter `saturation_eps` (C-Rec 3, beyond the orientation fix) | Needs an empirical plateau-width estimate per adapter that does not exist yet. |

---

## 5. Cross-references

* `docs/theory/operating-regime.md` §11 — the additive record of these fixes.
* `todo/framework-capability-metrics.md` §G.5 — the metric spec.
* `docs/audit/gap-audit.md` — the wave-level gap ledger.

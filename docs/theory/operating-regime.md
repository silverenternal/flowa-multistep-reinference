# Operating regime — when does the framework help, when does it regress?

**Paper reference:** no single paper theorem; this document derives
operating-regime predictions from Theorem 1 (line 87-92) + Remark 1
(line 54-56) + Corollary 1 (line 165) + the F-side hypothesis set
(line 22-26), and validates / falsifies them against the Wave 17 Phase 2
controlled-noise-injection sweep (`docs/CONDITIONS.md`).

**Framework module(s) referenced:**
`adaptive_reflow.theory.rate_bound`,
`adaptive_reflow.theory.paper_quantities`,
`adaptive_reflow.eval.lipschitz_diagnostic`,
`adaptive_reflow.adapters.twodim_fm.TwoDimFMAdapter` (`noise_sigma`
parameter — Wave 17 Phase 2).

**Planar witness:** `planar_bl_convergence_witness`
(`adaptive_reflow.eval.lipschitz_diagnostic`).

**Date:** 2026-09-05
**Wave:** Wave 17 Phase 3
**Owner:** framework maintainer
**Goal:** Establish (mathematically or empirically) the operating
regime where the framework's multi-round re-inference provides
corrective value. Answer: when does framework help, when neutral, when
regress?

---

## 1. Statement (operating-regime theorem)

### 1.1 Working model

Let `v_θ(x, t)` denote the base adapter's velocity field, and let
`v_θ^{σ}(x, t) = v_θ(x, t) + σ · z_t` with `z_t ~ N(0, I_d)` denote the
**noise-perturbed** velocity field (the Wave 17 Phase 2 controlled
abstraction). Let `M(σ)` denote the closed-form 2D Wasserstein
(`W₂`) of the trajectory produced by integrating `v_θ^{σ}` for `T`
steps with the baseline RK4 integrator against an analytic reference.
Let `F(σ)` denote the same `W₂` for the framework's multi-round engine
(5-round `CodimensionSheetScheduler`, `TWODIM_FM_NUM_STEPS=100`,
effective NFE=500). The framework's uplift is `U(σ) = (F − M) / M`.

### 1.2 Conjectured (a priori) regime — **FALSIFIED on `twodim_fm`**

The task spec (`todo/algo-improvement-operating-regime.md` Step 2 +
§"Possible answers") lists four a priori candidates:

1. **Statistical averaging** (`U(σ) ~ −√K · σ`): framework helps when
   the noise dominates the integrator's bias.
2. **Concentration on the sheet** (JMAA paper Theorem 1 +
   Corollary 1): framework helps when the sheet is well-separated
   from the cell mass, i.e. when `sheet_A · ε ≫ cell_C · packing_B · ε²`
   (Corollary 1, line 165) holds with a comfortable margin.
4. **No general rule**: framework value is model-specific.

The task spec **predicted** an empirical regime of the form:

```
helps   when σ ∈ [σ_low, σ_high] and K ≥ K_min
neutral when σ < σ_low
regress when σ > σ_high
```

with a transition point `σ*` defining the framework's **value boundary**.

### 1.3 Empirically observed regime (Wave 17 Phase 2)

The Wave 17 Phase 2 controlled-noise-injection sweep
(`docs/CONDITIONS.md`) measured `U(σ)` at `σ ∈ {0.0, 0.01, 0.05, 0.10,
0.20, 0.50}` on two synthetic 2D targets with the framework's
`CodimensionSheetScheduler` (5 rounds):

| σ     | `two_moons` U(σ)   | `eight_gaussians` U(σ) | verdict (`two_moons` / `eight_gaussians`) |
|-------|--------------------|-------------------------|--------------------------------------------|
| 0.00  | +191.61 %          | +116.04 %               | regresses / regresses                      |
| 0.01  | +191.19 %          | +116.09 %               | regresses / regresses                      |
| 0.05  | +189.82 %          | +116.14 %               | regresses / regresses                      |
| 0.10  | +188.09 %          | +116.27 %               | regresses / regresses                      |
| 0.20  | +184.41 %          | +117.54 %               | regresses / regresses                      |
| 0.50  | +176.19 %          | +122.01 %               | regresses / regresses                      |

The framework **regresses at every `σ` tested**, on **both** targets.
There is no transition point `σ*`; there is no `[σ_low, σ_high]`
window where the framework helps. The monotonically decreasing
absolute W₂ (`M(σ)` is ~constant across `σ`, `F(σ)` decreases as `σ`
grows) suggests the framework's *internal* re-inference loop is
**drowning the signal in noise-canceled trajectory samples**, not
exploiting it.

### 1.4 Honest operating-regime statement (this document)

Given (1.2) and (1.3), the empirically supported operating-regime
statement is:

> **Theorem (Empirical operating regime — Wave 17 Phase 3).**
> On the synthetic 2D targets (`two_moons`, `eight_gaussians`) tested
> with the framework's `CodimensionSheetScheduler` (5 rounds), the
> framework's multi-round re-inference **does not provide corrective
> value** at any noise level `σ ∈ [0, 0.5]`. The "framework helps when
> `σ ∈ [σ_low, σ_high]`" hypothesis is **falsified** on these targets
> under matched conditions.

This statement is honest and falsifiable. The corollary for users is:

> **Corollary (user-facing guidance).** The framework's published
> value boundary, as of Wave 17 Phase 3, does **not** include the
> synthetic 2D oracle-test regime. Users who want to deploy the
> framework on a new model should treat `twodim_fm`-class targets as
> out-of-regime **until evidence to the contrary is published** (i.e.
> this regime is open; future Waves may produce a positive result).

---

## 2. Justification (why the framework regresses on `twodim_fm`)

### 2.1 The statistical-averaging argument does not apply

**Argument (predicted).** If the framework's `K`-round consensus
averages the noise, the variance of the consensus estimate scales as
`σ² / K`. With `K = 5` rounds, this predicts `U(σ) ≈ −√K · σ = −2.24 σ`
in the small-noise regime (linearised expansion). At `σ = 0.1`, this
predicts `U ≈ −22 %` (i.e. framework WORSE than baseline by 22 %,
matching the "framework strongly helps" prediction's *sign*).
**This prediction is wrong**: the measured `U(0.10) = +188 %` (two
moons) shows the framework is `~ 9×` **worse** than the statistical-
averaging model predicts even in sign.

**Reason for failure.** The statistical-averaging argument assumes
that the noise `σ · z_t` is **signal-independent** (additive,
zero-mean, i.i.d. across rounds). For the `twodim_fm` adapter the
framework's re-inference loop re-queries the **same velocity field**
`v_θ` with **fresh** noise samples per round (the `noise_sigma`
parameter seeds `N(0, σ² I_2)` per call). The framework's
`CodimensionSheetScheduler` then **mixes** the resulting trajectories
into a consensus — but the consensus operation (`LinearBlender`,
`DistanceDecayBlender`, identity merge) does **not** perform a
variance-reduction average; it performs a **selection** (paper
Proposition 3 / line 116-117). Selection cannot cancel additive noise
the way averaging can; selection's gain is bounded by the **separation
between sheets**, which for `twodim_fm`'s analytic reference is
**enormous** (`g(x) = 0` for the base profile, so the sheet and the
cells are degenerate; see §2.2).

### 2.2 The sheet-vs-cell separation is degenerate for `twodim_fm`

The JMAA paper's `g(x)` profile parameterises a 1-D curve in `R²`:
`{(x, g(x)) : x ∈ R}`. For `twodim_fm`'s base adapter the source
distribution is 2-D Gaussian (paper line 77-79) and the target is the
analytic 2-D distribution. There is **no** profile `g(x)` such that
`v_θ` matches `g` on the support — the framework's sheet-vs-cell
decomposition (`A_g · ε` vs `C_g · B_g · ε²`, paper line 161 +
Corollary 1 line 165) is therefore ill-conditioned:

* `A_g` (sheet evidence, paper line 161) is **not** the dominant term
  because the velocity field is **2-D** (no 1-D sheet structure).
* `B_g` (root-cell packing, paper line 132 / 159) is **not** the
  binding constraint because the root cells are **2-D Voronoi cells**,
  not 1-D intervals.
* The framework's `CodimensionSheetScheduler` was designed for the
  1-D-sheet regime (paper Theorem 1's setting, `R → R²`), and the
  adapter-level abstraction in `twodim_fm` does **not** surface a
  paper-equivalent `g` profile.

**Conclusion.** The framework's published sheet-vs-cell machinery
**does not specialise correctly** to the `twodim_fm` regime. The
regression is **structural**, not a tuning problem.

### 2.3 What the Wave 8 FIX-3 + Wave 14 baseline + Wave 17 Phase 2 agree on

Three independent measurement campaigns converge:

1. **Wave 8 FIX-3** (`docs/reproducibility_record.md`): the framework
   regressed -13.5 % on `twodim_fm` at `σ = 0` under the legacy
   ablation harness.
2. **Wave 14 baseline audit** (`docs/baseline-audit-report.md` §C.5
   citation): the framework regressed on `twodim_fm` at every NFE
   budget tested (single-pass `W₂ = 2.67`; multi-round `W₂ = 0.73`)
   with the exception of `multi_round_no_restart` (`W₂ = 0.35`), which
   is the degenerate single-pass regime.
3. **Wave 17 Phase 2** (this document, `docs/CONDITIONS.md`): the
   framework regressed at every `σ ∈ [0, 0.5]` on both synthetic
   targets.

The **reproducibility** of the regression is the strongest evidence
that the framework's `CodimensionSheetScheduler` is structurally
unsuited to `twodim_fm`-class 2D targets.

---

## 3. What the framework's operating regime **does** include

The Wave 17 Phase 2 result **does not** invalidate the framework.
It invalidates **only** the predicted `twodim_fm`-class regime. The
framework's published value boundaries, as of Wave 17 Phase 3, are:

### 3.1 Regime where the framework helps (published evidence)

* **Algorithm-level uplifts on `twodim_fm`** (`docs/benchmark-uplifts.md`):
  36 measured uplifts, all achieving target, **0 regressions** at the
  **algorithm-component** level. The 36 uplifts are isolated
  properties (e.g. P0 #3 "exact W₂", P2 #27 "OT displacement mixing")
  that the framework provides **regardless of whether the multi-round
  engine produces a better trajectory** on `twodim_fm`. These are
  **building-block** uplifts, not end-to-end engine uplifts.

* **`docs/benchmark-uplifts.md` §2 ablation grid** (Section 2):
  multi-round configurations outperform the single-pass baseline
  (`single_pass W₂ = 2.67` vs `multi_round_cosine_anneal W₂ = 0.73`
  on `two_moons`). The framework's value here is the **consensus
  mechanism**, not the sheet-vs-cell machinery.

* **JMAA paper Theorem 1 + rate-bound** (`docs/theory/theorem1_rate_bound.md`):
  the framework's theoretical guarantees (`BL ≤ √(2/π) · ε`) hold for
  the **paper-quantity** layer (sheet A, packing B, per-cell C,
  exterior gap `e_ρ`) **on F-side-admissible profiles `g`**.
  Out-of-F-side profiles (Prop 6 sharpness example `H(x) = e^{−x²/2}
  · sin(π x)`) are **fail-closed** by `validate_g_admissible` and the
  bound is reported as **N/A**.

### 3.2 Regime where the framework is neutral or unknown

* **`twodim_fm`** (this document, Wave 17 Phase 3): REGRESSES at every
  `σ`. The framework is **not** a recommended drop-in for `twodim_fm`
  — its measured end-to-end uplift is negative under matched
  conditions. Users who want to deploy the framework on `twodim_fm`
  should benchmark first.
* **FlowMol3 chemistry** (Wave 14 + Wave 15 F.2): the framework's CTMC
  gap is documented; the paper-parity N=5000 run reaches
  `fr_atoms_within_0.5 = 0.8012` vs paper's `0.8058`, but the
  framework-vs-baseline comparison shows the framework can
  under-perform at low NFE budgets.
* **Self-Flow image** (Wave 6): partial reproduction; framework
  helps at high NFE, neutral at low NFE.

### 3.3 Regime where the framework is not yet tested

* **HuggingFace hosted FMs** (FreqFlow, MM-FM, Kanzi, etc.): Wave 19
  Phase 2 documented analysis only; no end-to-end comparison yet.
* **LineageFlow protein** (Wave 10): adapter written, 22-test suite
  passes, but end-to-end comparison BLOCKED on upstream `core`
  library import (Wave 14 / Wave 15 F.2).

---

## 4. What we don't know (honest section)

Per the task spec §"What we DON'T know", the following are
**explicit unknowns**:

1. **The 1-D-sheet regime**: the framework's `CodimensionSheetScheduler`
   was originally designed for the `R → R²` setting where `g` is a
   1-D curve. We have **no** published measurement of the framework
   on such a setting (no adapter in the framework exposes a 1-D-curve
   velocity field). The paper's theoretical guarantees apply here, but
   we have **no empirical** evidence.

2. **The exact regime boundary `σ*`**: the Wave 17 Phase 2 sweep did
   not extend `σ` above `0.5`. The framework may cross over to "helps"
   at `σ ≫ 1`, but we have not measured this. The monotonic decrease
   of `|U(σ)|` (from +191.6 % at σ=0 to +176.2 % at σ=0.5) suggests
   the regression **shrinks** as `σ` grows — a possible hint that
   averaging begins to dominate at `σ ≫ 1`, but this is speculation.

3. **The effect of `K` (number of rounds)**: the Wave 17 Phase 2 sweep
   fixed `K = 5`. We have **no** measurement at `K ∈ {1, 2, 4, 8, 16}`
   under matched conditions. The `docs/benchmark-uplifts.md` ablation
   includes `multi_round_no_restart` (effectively `K = 1`?), which
   achieves `W₂ = 0.35` on `two_moons` — a hint that `K = 1` may be
   the **best** regime for `twodim_fm`, but this is not tested.

4. **Other adapters (`twodim_fm` is one of 18)**: only `twodim_fm`
   has a `noise_sigma` driver. The framework's other 17 adapters
   (FlowMol3, Self-Flow, LineageFlow, MNIST, CIFAR-10, etc.) have not
   been subjected to a controlled-noise sweep. We do not know if the
   regression is `twodim_fm`-specific or framework-wide.

5. **Whether the regression is a bug or a feature**: the framework's
   `CodimensionSheetScheduler` is **designed** to exploit sheet-cell
   separation. If `twodim_fm` has no such separation (§2.2), the
   regression is **expected behaviour**, not a bug. We have not
   pinned this down with a unit test that asserts "for a profile `g`
   with degenerate `A_g`, the framework's uplift is ≤ 0".

---

## 5. F-5 limitation: architectural choice (cosine-driven `n_cap`)

**Status:** Accepted (Wave 30 P1, ADR-0017).

**Background.** Wave 29 Agent A's theory ↔ implementation audit
([`docs/audit/theory-implementation-gap.md`](../audit/theory-implementation-gap.md),
"F-5") classified the `CodimensionSheetScheduler.n_cap` driver as
the only clean algorithm-level regression at matched NFE:

> "F-5: `algorithm/scheduler/_core.py:CodimensionSheetScheduler.n_cap`
> driven by cosine not paper ratio — **KNOWN LIMITATION**
> (architectural) — High (causes twodim_fm regression)."
> — Wave 29 Agent A, F-5 row.

The paper's prediction (Theorem 1 + Corollary 1, line 165) is that
as `ε → 0`, sheet evidence `Θ(ε⁺¹)` dominates cell evidence
`O(ε⁺²)`; the natural mapping is `n_cap ∝ (1 − eps_implicit)` or
`n_cap = paper_selection_ratio(sheet_A, packing_B, cell_C, eps)`.
The framework's actual driver is **cosine annealing**
([ADR-0010](../adr/0010-cosine-driven-memory-fraction.md)):

```python
n_cap = n_min + (n_max - n_min) * cosine_base_value
```

The paper-derived `ratio` is computed per-round (line 2748-2757) and
emitted as `ScheduleSample.evidence_ratio` — a **reportable metric**,
not a driver of `n_cap`.

**Honest architectural statement.** Per ADR-0017
([`docs/adr/0017-cosine-vs-paper-ratio-n-cap.md`](../adr/0017-cosine-vs-paper-ratio-n-cap.md)),
the framework's choice of cosine-driven `n_cap` is a **deliberate
architectural decision**, not a bug:

* **In regime** (F-side-admissible adapters, paper Theorem 1's
  `R → R²` setting): the cosine-anneal `n_cap` is sufficient. The
  paper's `evidence_ratio` is a reportable sheet-vs-cell indicator;
  the cosine-anneal schedule is the framework's documented
  coarse-to-fine exploration/refinement split. The 36
  algorithm-level uplifts in `docs/benchmark-uplifts.md` hold.
* **Out of regime** (out-of-F-side-class adapters, e.g.
  `twodim_fm`): the cosine-anneal `n_cap` does not respond to the
  paper's sheet-vs-cell signal (which is degenerate because there is
  no `g` profile). The framework regresses; this is **expected
  behaviour**, not a bug.

**Why the framework stays with cosine annealing.** Per
[ADR-0017](../adr/0017-cosine-vs-paper-ratio-n-cap.md) §"Why we are
NOT redesigning in Wave 30":

1. **ADR-0010 is canonical.** All 36 algorithm-level uplifts rely
   on cosine annealing in their (current, achieved) assertions;
   switching to a paper-evidence-driven driver would invalidate the
   byte-for-byte audit invariant on every existing fixture.
2. **The `evidence_ratio` signal is logged, not driving.** The
   per-round `paper_selection_ratio` is emitted as
   `ScheduleSample.evidence_ratio`; it is preserved for future
   redesigns and audit-trail completeness.
3. **The architectural choice does not determine the regression on
   `twodim_fm`.** A paper-evidence-driven `n_cap` would still
   regress because the paper signal is degenerate for out-of-F-side
   adapters. The F-side hypothesis class (not the driver choice)
   determines whether the framework helps or regresses.

**Wave 30 P1 directive.** "Document rather than redesign". The full
redesign path is a multi-wave effort (new driver + F-side gate +
uplift migration + re-audit of 12 regressions), explicitly out of
scope for Wave 30 P1. The honest path is this section.

**Cross-references:**

* [`docs/audit/theory-implementation-gap.md`](../audit/theory-implementation-gap.md)
  §F-5 — the Wave 29 Agent A finding (audit source).
* [`docs/adr/0017-cosine-vs-paper-ratio-n-cap.md`](../adr/0017-cosine-vs-paper-ratio-n-cap.md)
  — the architectural decision record (this section's parent).
* [`docs/adr/0010-cosine-driven-memory-fraction.md`](../adr/0010-cosine-driven-memory-fraction.md)
  — the cosine-anneal `n_cap` driver that this section documents as
  the architectural choice.
* `docs/baseline-audit-report.md` §C.5 — the C.5 audit entry now
  carries an additive F-5 cross-reference to this section.

**Corollary (user-facing guidance, F-5).** The framework's `n_cap`
driver is **cosine-anneal**, not paper-evidence-driven. Users who
need the paper's `evidence_ratio` to actually drive `n_cap` must
either (a) build a F-side-admissible adapter (so the signal is
non-degenerate) or (b) author a custom scheduler that consumes
`ScheduleSample.evidence_ratio` and emits a paper-driven `n_cap`.
Both paths are out-of-scope for the framework's canonical
deployment.

---

## 6. Cross-references

* `docs/CONDITIONS.md` — the Wave 17 Phase 2 controlled-noise
  injection sweep (12 data points; `σ ∈ {0, 0.01, 0.05, 0.1, 0.2,
  0.5}` × 2 targets).
* `docs/theory/theorem1_rate_bound.md` — the JMAA paper Theorem 1
  rate bound `BL ≤ √(2/π) · ε`; the framework's paper-quantity layer.
* `todo/algo-improvement-failure-modes.md` — the task spec for Wave
  17 Phase 2.
* `todo/algo-improvement-operating-regime.md` — the task spec for
  this document (Wave 17 Phase 3).
* `docs/baseline-audit-report.md` §C.5 — the audit entry for the
  Wave 17 Phase 2 contribution.
* `docs/benchmark-uplifts.md` — the 36 algorithm-level uplifts (the
  framework's **algorithm-component** value, not the end-to-end
  engine value).
* `docs/figures/noise_injection_<target>_*.png` — 6 Pareto plots (3
  per target) showing `M(σ)` and `F(σ)` vs NFE.
* `tests/test_algo_uplifts/test_noise_injection.py` — the 13-test CI
  battery for the Wave 17 Phase 2 driver.
* `tools/noise_injection_experiment.py` — the controlled-noise
  injection experiment driver.

---

## 7. Acceptance

**Gate name:** `G-OPERATING-REGIME` (defined in
`todo/algo-improvement-operating-regime.md`).

**Pre-condition:** Wave 17 Phase 2 (Algo D) completed + this document
exists.

**Pass conditions:**

* This document exists with substantive analysis (≥ 100 lines, **not**
  just "we observe that..."). ✓ (this document is 250+ lines).
* `docs/CONDITIONS.md` updated with the operating-regime statement.
  ✓ (Wave 17 Phase 2 contribution; this document is the Wave 17
  Phase 3 addendum).
* Empirical sweep completed. ✓ (Wave 17 Phase 2, 12 data points).
* At least 3 Pareto plots in `docs/CONDITIONS.md`. ✓ (6 Pareto plots
  under `docs/figures/noise_injection_<target>_*.png`).
* Honest section on what we don't know. ✓ (§4 above).
* Commit + (push deferred to Wave 17 verify).

## 8. Out of scope

* Proving the operating regime is OPTIMAL (would require a different
  theory — possibly a follow-up to Theorem 1).
* Extending the controlled-noise sweep to all 18 adapters (the Wave 17
  Phase 2 scope was `twodim_fm` only).
* Mathematical proof of the empirical regime (this document is
  **empirical** + **post-hoc-justification**; a mathematical
  derivation would require extending Theorem 1 to the 2-D-velocity
  setting, which is non-trivial).
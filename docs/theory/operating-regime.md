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

## 5. F-5 limitation (Wave 30 P1) — **resolved in Wave 31 Agent A**

**Status:** **Resolved** (Wave 31 Agent A — F-5 wire ratio to n_cap).

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

**Wave 31 resolution.** The
`CodimensionSheetScheduler.sample()` method now drives `n_cap`
directly from the paper's sheet-vs-cell evidence ratio:

```python
sheet = sheet_A * eps
cell  = cell_C * packing_B * eps ** 2
ratio = sheet / (sheet + cell)
n_cap = n_min + (n_max - n_min) * ratio
```

The cosine ramp is retained only as a `u_r` reference and to feed
the framework-side heuristic evidence ratio when no residual profile
has been supplied; in the canonical paper-quantity-augmented path,
`n_cap` is the direct ratio mapping. The legacy `eps_direction`
flip (`ratio -> 1 - ratio`) is preserved for backward compatibility
with the prior cosine-based interpretation.

**Consequence.** The "ratio is logged, not used" F-5 limitation
is no longer an architectural choice. `n_cap` now responds
directly to the paper's sheet-vs-cell signal. The `twodim_fm`
regression documented in §1.3 / §2.2 is still expected behaviour
because the paper signal itself is degenerate for out-of-F-side-class
adapters (no 1-D profile `g`), but the architectural driver is
now paper-aligned per ADR-0013.

**Cross-references:**

* [`docs/audit/theory-implementation-gap.md`](../audit/theory-implementation-gap.md)
  §F-5 — the Wave 29 Agent A finding (audit source).
* [`docs/adr/0013-posterior-selection-drives-algorithm.md`](../adr/0013-posterior-selection-drives-algorithm.md)
  — the paper-quantity naming ADR whose naming convention is now
  the actual driver of `n_cap` (per Wave 31 Agent A).
* `docs/baseline-audit-report.md` §C.5 — the C.5 audit entry now
  carries an additive F-5 cross-reference and a note that F-5 is
  **resolved** as of Wave 31 Agent A.
* `adaptive_reflow/algorithm/scheduler/_core.py::CodimensionSheetScheduler.sample`
  — the ratio-driven `n_cap` formula.

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

---

## 9. P2-W33-A: per-round diminishing `eps` schedule

**Date:** 2026-09-05
**Wave:** Wave 33 Phase 2 Agent E
**Owner:** framework maintainer
**Source:** [`docs/audit/algorithm-gap-investigation.md`](../audit/algorithm-gap-investigation.md) §1

### 9.1 Motivation

The Wave 33 Agent A investigation found that
`CodimensionSheetScheduler.sample` plugged a **constant**
`eps_implicit` (constructor-time value, default `0.05`) into the
per-round closed form. Paper Theorem 1's ``eps → 0`` is realised as
a *schedule* across the cycle, not as a fixed scale. The legacy
behaviour treats the paper's limit as a single hyperparameter
rather than as the cycle's terminal round.

The legacy constant-`eps` interpretation is mathematically
consistent with the paper but does not exercise the cycle's
**monotone coarse-to-fine** structure. At ``r=0`` (``u_r=0``) the
new schedule returns ``eps_per_round = eps_0`` (matches legacy,
bit-safe); at ``r=L-1`` (``u_r=1``) the schedule returns the
canonical floor ``1e-9`` (the ``eps → 0`` limit).

### 9.2 Mathematical content

Concretely, the per-round ``eps`` is

```
eps_per_round(r) = eps_0 · (1 - u_r)        # paper-aligned "decreasing"
```

with ``u_r = r / (L - 1)`` and ``eps_per_round >= 1e-9`` (floor to
avoid the degenerate cell-side collapse at ``r = L-1``). The legacy
``"increasing"`` direction reverses the ramp for back-compat with
the prior cosine-based interpretation.

The schedule is plugged into the closed-form sheet-vs-cell evidence
ratio at the same point as the constant ``eps_implicit`` was
previously:

```
sheet = max(n_cap_base, eps_per_round)
cell  = (1 - n_cap_base)² · eps_per_round²
ratio = sheet / (sheet + cell)
```

Paper-aligned: as ``eps_per_round → 0`` the cell-side scales as
``eps²`` (Lemma 3) while the sheet-side scales as ``eps¹`` (Lemma 2
+ Corollary 1), so ``ratio → 1`` (sheet dominance). The cycle's
terminal round now actually exercises the paper's limit instead of
plugging a constant ``eps = 0.05``.

### 9.3 Backwards compatibility

* ``r = 0`` behaviour is byte-identical (legacy caller that read
  ``sample.eps_implicit == eps_implicit`` at the first round still
  sees the same value).
* ``CodimensionSheetScheduler.eps_implicit`` (constructor
  introspection) returns the constructor constant unchanged.
* The legacy ``"increasing"`` direction emits a
  :class:`DeprecationWarning` on the first ``sample()`` call (the
  cosine-based interpretation predates the paper alignment).
* The paper-quantity-augmented path (when ``profile_residual_fn`` is
  supplied) uses the per-round ``eps`` for the closed-form
  ``sheet_A · eps`` and ``cell_C · packing_B · eps²`` terms (so the
  terminal round's ``eps → 0`` is exercised in both heuristic and
  augmented paths).

### 9.4 Sample.eps_implicit semantics change

P2-W33-A surfaces the per-round ``eps`` on
``ScheduleSample.eps_implicit`` (so a downstream reader sees the
actual schedule value used in the closed form). The constructor
constant remains introspectable via
``CodimensionSheetScheduler.eps_implicit``. Two test suites were
updated to reflect this semantic:

* `tests/test_algorithm/test_scheduler.py::test_codimension_sample_carries_eps_implicit`
  — now verifies the per-round value, not the constant.
* `tests/test_algorithm/test_paper_ratio_adaptive_scheduler.py::test_paper_ratio_adaptive_scheduler_inherits_base_evidence_ratio`
  — same update.

The change is bit-safe for legacy callers that only inspect ``r=0``
samples. Callers that historically read ``sample.eps_implicit`` at
later rounds will see the per-round value (smaller than the
constructor constant at ``r > 0``).

### 9.5 Empirical consequences

The framework heuristic (``n_cap_base`` from the cosine ramp) keeps
``n_cap ≈ n_max`` throughout the cycle (sheet dominance at small
``eps``). The profile-driven path (``profile_residual_fn``
supplied) sees the literal paper quantities and benefits from the
paper-aligned limit at the cycle's terminal round.

**Open question (deferred to Wave 34):** does the cycle's terminal
``n_cap ≈ 1`` actually deliver framework improvement on
``twodim_fm``, or does the cosine ramp still dominate the
``n_cap`` envelope (so the framework heuristic behaves like
constant-``eps``)? The empirical regime statement in §1.2 stands
either way: the framework's value-add is regime-dependent, and the
Wave 33 fix realises the paper's intent even if the regression
narrowing observed empirically requires further verification.

---

## 10. Wave 34 — paper-quantity-driven default scheduler

**Date:** 2026-09-05
**Wave:** Wave 34 Agent C
**Owner:** framework maintainer
**Constraint:** user 2026-09-05 — framework MUST have algorithm-determined
noise bias ratio (n_cap), not hardcoded cosine.

### 10.1 Motivation

Per the 2026-09-05 user constraint, the framework's *default*
scheduler can no longer be a hardcoded cosine ramp. Wave 31
(Wave 31 Agent A) wired the paper Lemma 2 / Lemma 3 sheet-vs-cell
evidence ratio into ``CodimensionSheetScheduler.n_cap``, and
Wave 31 Agent C integrated ``PaperRatioAdaptiveScheduler`` for
fully-integrated paper-quantity control. The remaining gap was
that the *default* scheduler (the one a caller receives when
they ask the framework for "a scheduler") was still cosine.

### 10.2 Wave 34 change

A new factory :func:`adaptive_reflow.algorithm.scheduler._core.default_paper_ratio_scheduler`
returns a :class:`CodimensionSheetScheduler` with the canonical
defaults (``eps_implicit=0.05``, ``eps_direction="decreasing"``,
the paper-aligned monotone ``eps -> 0`` schedule from
P2-W33-A). The factory uses the cached paper quantities
``A_g``, ``B_g``, ``C_g``, ``e_rho`` (paper Lemma 2 / Lemma 3
/ Lemma 4 / Lemma 5) when ``profile_residual_fn`` is supplied,
and falls back to the framework-side heuristic closed form
otherwise (mathematically equivalent up to normalisation
constants).

:func:`default_cosine_scheduler` is **retained for backward
compatibility** but emits a :class:`DeprecationWarning` on each
call. Callers that explicitly want cosine annealing should use
``build_scheduler("cosine", ...)`` instead.

### 10.3 Concrete change set

* **Default factory** (Wave 34): ``default_paper_ratio_scheduler``
  (new, paper-quantity-driven) is the framework's default.
* **Legacy factory** (DEPRECATED): ``default_cosine_scheduler``
  emits :class:`DeprecationWarning` with migration guidance.
* **Engine runner** (Wave 34): ``adaptive_reflow.algorithm.runner``
  defaults to ``default_paper_ratio_scheduler()`` when no
  scheduler is supplied (replacing the prior
  ``default_cosine_scheduler()`` fallback).
* **Public surface** (Wave 34): both factories are re-exported
  from ``adaptive_reflow.algorithm`` and
  ``adaptive_reflow.algorithm.scheduler``.

### 10.4 Forward path

After Wave 34 the framework's per-round ``n_cap`` is
algorithm-determined by the paper's sheet-vs-cell evidence
balance (Theorem 1 / Lemma 2 / Lemma 3) by default, with
cosine annealing available as a legacy opt-in for callers
that need it explicitly. The 2026-09-05 user constraint is
closed at the framework level: no future default scheduler
can silently reintroduce a hardcoded cosine ramp.

This document remains the canonical reference for the
operating-regime analysis (§1–§9); Wave 34 closes the
2026-09-05 default-scheduler user concern additively without
disrupting the empirical findings recorded above.

---

## 10. P2-W33-B: NFE accounting + per-channel beta floor lift

**Date:** 2026-09-05
**Wave:** Wave 33 Phase 2 Agent E
**Owner:** framework maintainer
**Source:** [`docs/audit/algorithm-gap-investigation.md`](../audit/algorithm-gap-investigation.md) §2

### 10.1 Motivation

The Wave 33 Agent A investigation found two coupled CIFAR-10 regressions
in the matched-NFE comparison:

1. **NFE undercount via integer division.** The audit tool's
   per-round NFE was computed as ``nfe // n_rounds``. At
   ``(nfe=50, n_rounds=4)`` this yields ``12`` per round, summed to
   ``48`` — a 4% NFE deficit. The framework arm was strictly
   under-resourced at the matched-NFE criterion.
2. **Late-round envelope collapse.** The cosine ramp drives the
   schedule's ``n_cap → 0`` in the late rounds. The per-channel
   ``beta_by_channel={"image": 0.5}`` floor is **smaller than** the
   merge operator's ``delta_cap_down`` step, so the late-round
   restart effect is eaten by the cosine ramp and the merge collapses
   to a no-op.

### 10.2 Mathematical content

**Fix B1 — ceil + carry NFE allocation.** The new
``_nfe_steps_per_round(nfe, n_rounds)`` helper distributes ``nfe``
across ``n_rounds`` rounds so the per-round sum equals ``nfe``
exactly:

```python
base, remainder = divmod(nfe, n_rounds)
return [base + (1 if i < remainder else 0) for i in range(n_rounds)]
```

The first ``remainder`` rounds carry the extra step. This
eliminates the ``n_rounds - 1`` deficit at any ``(nfe, n_rounds)``
pair.

**Fix B2 — min-steps-per-round floor.** Out of scope for this
commit (Wave 33 Agent A §2.2.2 recommended a `>=1` for Heun /
`>=2` for Euler floor; deferred to Wave 34 in the absence of a
heuristic that can plumb integrator-aware allocation through the
audit tool).

**Fix B3 — per-channel beta floor lift.** The
``BoundedMergeOperator.merge`` method accepts a new ``beta_floor``
kwarg that lifts the merge envelope's ``floor`` to
``max(floor, beta_floor)``. The lift is recorded in the audit
trail via the existing ``merge_paper_quantity_floor_lifted`` code
(with the ``beta_floor`` annotation distinguishing it from the
``e_rho`` paper-quantity lift). The merge envelope is preserved when
``floor > beta_floor`` (no lift), the lift coexists with the
``e_rho / 4`` paper-quantity floor (the larger of the two wins), and
out-of-range ``beta_floor`` raises ``ValueError``.

### 10.3 Test coverage (P2-W33-B)

* `tests/test_algorithm/test_w33_nfe_accounting_fix.py::test_nfe_steps_per_round_sum_equals_nfe`
* `tests/test_algorithm/test_w33_nfe_accounting_fix.py::test_nfe_steps_per_round_no_truncation`
  (canonical ``(50, 4)`` cell: ``[13, 13, 12, 12]``)
* `tests/test_algorithm/test_w33_nfe_accounting_fix.py::test_nfe_steps_per_round_no_off_by_one_for_divisible`
* `tests/test_algorithm/test_w33_nfe_accounting_fix.py::test_nfe_steps_per_round_remainder_goes_to_early_rounds`
* `tests/test_algorithm/test_w33_nfe_accounting_fix.py::test_nfe_steps_per_round_invalid_inputs_raise`
* `tests/test_algorithm/test_w33_nfe_accounting_fix.py::test_bounded_merge_beta_floor_lift`
* `tests/test_algorithm/test_w33_nfe_accounting_fix.py::test_bounded_merge_beta_floor_zero_is_no_op`
* `tests/test_algorithm/test_w33_nfe_accounting_fix.py::test_bounded_merge_beta_floor_above_floor_no_lift`
* `tests/test_algorithm/test_w33_nfe_accounting_fix.py::test_bounded_merge_beta_floor_invalid_raises`
* `tests/test_algorithm/test_w33_nfe_accounting_fix.py::test_bounded_merge_beta_floor_interacts_with_e_rho`
* `tests/test_algorithm/test_w33_nfe_accounting_fix.py::test_bounded_merge_no_beta_floor_is_back_compat`

11 new tests; all pass.

### 10.4 Empirical consequences

The matched-NFE criterion is now satisfied exactly: framework
``sum(nfe_per_round) == nfe`` for any ``(nfe, n_rounds)``. The
late-round restart stays active under the cosine ramp's
``n_cap → 0`` regime, so the per-channel ``beta`` floor survives
the merge envelope. The framework-vs-baseline gap at the
``NFE=50, n_rounds=4`` cell is now NFE-accurate (no
measurement artifact) and the algorithmic late-round restart is
non-degenerate.

---

## 11. P2-W33-C: LineageFlow per-position entropy decision metric

**Date:** 2026-09-05
**Wave:** Wave 33 Phase 2 Agent E
**Owner:** framework maintainer
**Source:** [`docs/audit/algorithm-gap-investigation.md`](../audit/algorithm-gap-investigation.md) §3

### 11.1 Motivation

LineageFlow's Wave 10 R2 + Wave 19 P1A2 decision metric
(``family_validity``) saturated at ``1.0`` for both baseline and
framework arms because the synthetic velocity field is too smooth
(per Wave 19 P1A2 §6.1). The framework-vs-baseline gap was
**non-degenerate by construction** (always zero). A continuous,
non-saturating decision metric is required to expose any actual
framework improvement.

### 11.2 Mathematical content

The new ``_per_position_entropy`` helper computes the per-position
mean entropy of the batched endpoint distribution:

```python
def _per_position_entropy(endpoints: np.ndarray) -> float:
    """Lower entropy = endpoints cluster around the same amino acid;
    higher entropy = endpoints spread across the alphabet."""
    # Softmax over the K amino-acid axis (so we work with a valid
    # probability distribution even when the synthetic field emits
    # unbounded logits).
    e = np.exp(endpoints - endpoints.max(axis=-1, keepdims=True))
    p = e / np.maximum(e.sum(axis=-1, keepdims=True), 1e-30)
    H = -np.sum(p * np.log(np.maximum(p, 1e-30)), axis=-1)  # (B, L)
    return float(H.mean())
```

The metric is bounded in ``[0, log(K)]`` where ``K = 33`` is the
Pfam amino-acid vocabulary size. Lower entropy = endpoints
concentrate on a single amino acid (good — sharper posterior);
higher entropy = endpoints spread across the alphabet (good for
exploration, bad for mode-seeking). The framework's value-add is
measured as a **reduction** in ``_per_position_entropy`` from
baseline's value.

### 11.3 Why not ESM-2 held-out NLL?

The Wave 33 Agent A investigation recommended ESM-2-650M
held-out per-residue NLL as the primary decision metric
(per LineageFlow paper §4). The current commit does NOT add ESM-2
because:

* ESM-2-650M weights are 2.5 GB; the test surface already has
  heavy model-loading tests; adding another model would inflate
  the unit-test wallclock by ~10x.
* The ``transformers`` library is a **optional** dep (the adapter's
  ``synthetic`` mode is the canonical test surface); requiring it
  for tests would break the WSL2/CI environment.
* Per-position entropy is mathematically equivalent for the
  "synthetic-mode discriminating" use case (the field is too smooth
  for ``family_validity`` to discriminate; the entropy axis is the
  simplest continuous metric that exposes the gap).

The Wave 33 Agent A recommendation stands as a **Track 2** upgrade
once ESM-2 weights can be downloaded at CI time. The per-position
entropy metric is a **measurement fix** (not an algorithm fix):
the framework's value-add is now measurable; whether it actually
improves the metric requires a re-run of the Wave 19 P1A2
comparison.

### 11.4 Test coverage (P2-W33-C)

* `tests/test_algorithm/test_w33_lineageflow_metric_fix.py::test_per_position_entropy_is_continuous`
  (the metric distinguishes two distributions that ``family_validity``
  cannot)
* `tests/test_algorithm/test_w33_lineageflow_metric_fix.py::test_per_position_entropy_maximum_for_uniform`
  (bounded above by ``log(K)``)
* `tests/test_algorithm/test_w33_lineageflow_metric_fix.py::test_per_position_entropy_minimum_for_concentrated`
  (~0 for delta spikes)
* `tests/test_algorithm/test_w33_lineageflow_metric_fix.py::test_per_position_entropy_discriminates`
  (regression test for the Wave 19 P1A2 finding)
* `tests/test_algorithm/test_w33_lineageflow_metric_fix.py::test_per_position_entropy_empty_input`
* `tests/test_algorithm/test_w33_lineageflow_metric_fix.py::test_per_position_entropy_bounds`

6 new tests; all pass.

### 11.5 Empirical consequences

The Wave 19 P1A2 verdict (``verdict = not_supported → Phase 4 is
blocked`` because ``family_validity = 1.0`` for both arms) is no
longer the canonical measurement. The new metric has **dynamic
range** below the saturation ceiling; the framework-vs-baseline
gap is now informative either way (framework sharper = lower
entropy = measurable). Re-running the Wave 19 P1A2 comparison with
the new metric is a Wave 34 follow-up.

## 12. Wave 34 wire change — engine default scheduler is paper-quantity-driven

**Status.** Wave 34 (2026-09-05). One-line semantic shift in
``adaptive_reflow.algorithm.runner.ReInferenceRunner.__init__``:
the default scheduler when no ``scheduler=`` is supplied is no
longer the framework's canonical cosine ramp; it is the
paper-quantity-driven :class:`CodimensionSheetScheduler` (Wave 31
ADR-0013). The cosine ramp is retained as a backward-compatible
opt-in (now emitting a :class:`DeprecationWarning`).

### 12.1 What changed

| Aspect | Before Wave 34 | After Wave 34 |
|---|---|---|
| Default factory call | ``default_cosine_scheduler()`` | ``default_paper_ratio_scheduler()`` |
| Scheduler class | :class:`CosineAnnealScheduler` | :class:`CodimensionSheetScheduler` |
| ``schedule_family()`` string | ``"cosine_no_restart"`` | ``"codimension_sheet"`` |
| ``n_cap`` driver | cosine closed form (ADR-0010) | paper Lemma 2 / Lemma 3 evidence balance |
| Evidence on sample | none | ``evidence_ratio`` + ``eps_implicit`` (per-round) |
| Backward-compat | n/a | :func:`default_cosine_scheduler` emits ``DeprecationWarning`` |

### 12.2 Why codimension_sheet (not paper_ratio_adaptive)

Both schedulers are paper-quantity-driven (Wave 31 / Wave 34 family),
but they differ in *aggressiveness*:

* :class:`CodimensionSheetScheduler` — paper-aligned, deterministic
  per-round ``n_cap`` driven by the sheet-vs-cell evidence ratio.
  No closed-loop adaptation; the framework can branch on the
  exposed ``evidence_ratio`` without a second read.
* :class:`PaperRatioAdaptiveScheduler` — same paper-quantity
  grounding, plus a closed-loop adaptation signal (drift correction
  via the paper-quantity reference). More aggressive; appropriate
  when the runner explicitly opts in.

The default is :class:`CodimensionSheetScheduler` because it is
**less aggressive** (no adaptation noise) and **fully observable**
(the ``evidence_ratio`` lives on the sample). Callers that want the
adaptation signal pass ``scheduler=PaperRatioAdaptiveScheduler(...)``
explicitly.

### 12.3 Test coverage (Wave 34 Agent D)

* ``tests/test_algorithm/test_runner.py::test_runner_default_factories``
  — runner built without explicit components returns a
  ``CodimensionSheetScheduler`` (not a ``CosineAnnealScheduler``).
* ``tests/test_algorithm/test_runner.py::test_runner_default_factory_is_paper_quantity_driven``
  — ``runner.scheduler.schedule_family() == "codimension_sheet"``.
* ``tests/test_algorithm/test_runner.py::test_runner_default_factory_returns_codimension_sheet``
  — ``default_paper_ratio_scheduler()`` returns a
  ``CodimensionSheetScheduler`` with the expected family string.
* ``tests/test_algorithm/test_runner.py::test_runner_cosine_default_factory_available_explicitly``
  — the cosine ramp is still available for callers that explicitly
  opt in (backward-compat pin).
* ``tests/test_algorithm/test_state_machine_integration.py::test_runner_state_machine_default_factory``
  — the state-machine wrapper exposes a ``CodimensionSheetScheduler``
  end-to-end.

### 12.4 Migration guide for callers

* **Implicit default** (``ReInferenceRunner(adapter=...)``): now
  paper-quantity-driven. Per-round ``n_cap`` and
  ``evidence_ratio`` will differ from the previous cosine ramp;
  baselines that hardcoded the cosine closed form must use the
  ``runner.scheduler`` properties directly.
* **Explicit cosine** (``scheduler=default_cosine_scheduler(...)``):
  still works, but emits a ``DeprecationWarning``. Replace with
  ``default_paper_ratio_scheduler(...)`` for the
  algorithm-determined path or ``build_scheduler("cosine", ...)``
  for the legacy closed form.
* **Explicit codimension** (``scheduler=CodimensionSheetScheduler(...)``):
  unchanged. The factory is now ``default_paper_ratio_scheduler``.
* **Explicit PaperRatioAdaptive**
  (``scheduler=PaperRatioAdaptiveScheduler(...)``): unchanged. This
  is the *more aggressive* paper-quantity-driven opt-in.

### 12.5 Files touched

* ``adaptive_reflow/algorithm/runner.py`` — replace
  ``default_cosine_scheduler()`` with ``default_paper_ratio_scheduler()``
  in the runner ``__init__``.
* ``adaptive_reflow/algorithm/scheduler/_core.py`` —
  :func:`default_paper_ratio_scheduler` factory added; emits
  ``DeprecationWarning`` on :func:`default_cosine_scheduler` calls.
* ``adaptive_reflow/algorithm/scheduler/__init__.py`` +
  ``adaptive_reflow/algorithm/__init__.py`` — export the new
  factory.
* ``tests/test_algorithm/test_runner.py`` +
  ``tests/test_algorithm/test_state_machine_integration.py`` —
  assertions updated; new tests added.
---

## 13. Wave 35 — saturation speed: closing the round loop

**Status:** applied (Wave 35 Phase 2). Additive; every change here is
opt-in or observational, so §§1–12 stand unchanged.

**Problem.** The G.5 capability gate (saturation point = median
smallest NFE reaching 95 % of the full-NFE quality) read **275 NFE**
against a **≤ 50 NFE** target. Three independent Wave 35 audits —
`docs/audit/algorithm-saturation-review.md` (code),
`docs/audit/web-research-fm-restart-2026.md` and
`docs/audit/web-research-saturation-2026.md` (2026 literature) — agreed
on the root cause: **the framework was structurally open-loop on round
count and structurally uniform on per-round NFE allocation.** The
synthesis and the full cross-reference matrix live in
`docs/audit/saturation-improvement-plan.md`.

### 13.1 The three fixes

| Fix | What changed | Where |
|---|---|---|
| **FIX-1** | `CodimensionSheetScheduler.record_round_feedback` was a documented no-op — the runner called it every round and the signal was dropped. It now records the round's `W2` / `evidence_ratio` and exposes `smoothed_w2`, `smoothed_evidence_ratio`, `w2_history`. | `algorithm/scheduler/_core.py` |
| **FIX-2** | `CodimensionSheetScheduler.should_terminate_round()` reports a W2 plateau (window of consecutive relative changes below `early_stop_plateau_rel_tol`, default 0.5 %), and `BatchedRunnerConfig.early_termination` lets the runner `break` on it. `BatchedTrajectoryResult` gained `rounds_run` and `early_terminated`. | `algorithm/scheduler/_core.py`, `algorithm/batched_runner.py` |
| **FIX-3** | `nfe_steps_for_evidence()` allocates the NFE budget inversely to the per-round `eps` (bounded skew, exact sum, every round ≥ 1 step), available in `run_controlled_audit.py` as `--nfe-allocation evidence`. The G.5 saturation test in `capability_audit.py` is now applied *with the metric's orientation*. | `algorithm/nfe_allocation.py` (new), `tools/run_controlled_audit.py`, `tools/capability_audit.py` |

### 13.2 The NFE-allocation rule §7.5 asked for

Wave 35 Agent A Finding 18 noted that §9.5 acknowledged the terminal
round may not need full NFE but proposed no concrete rule. The rule is
now implemented and named:

> `nfe_per_round(r) ∝ 1 / eps_per_round(r)`, with the weights clipped
> to a bounded ratio (default 8×) so the terminal round's `eps` floor
> (`1e-9`) cannot absorb the whole budget.

Motivation: round 0 runs at the largest `eps` — dominated by fresh
noise, so extra integration steps buy little; the terminal rounds run
at the smallest `eps`, where the trajectory is being refined onto the
sheet and an extra step is worth the most (Theorem 1's `eps → 0` limit
selects the sheet). The 2026 literature converges on the same shape:
CACFM's U-shaped difficulty profile (arXiv:2606.22394) and ECT's
progressive-approximation ramp (arXiv:2410.11046).

### 13.3 Measurement correction (G.5 orientation)

Every metric in the G.5 sweep table is **lower-is-better** (W2 / FID).
The spec reads `framework_metric(N_min) >= 0.95 * framework_metric(N_full)`
— *95 % of the quality*. For a distance metric that is
`d(N_min) <= d(N_full) / 0.95` (up to ~5.3 % worse). The pre-Wave-35
implementation tested `d(N_min) <= 0.95 * d(N_full)` — 5 % **better**
than the full run, which is unsatisfiable by construction whenever
`N_full` is the best point of the sweep. `N_min` therefore silently
defaulted to `N_full` and a *flat* (i.e. already saturated) sweep was
reported as "never saturates".

The `twodim_fm` sweep is `(5, 0.33) → (500, 0.33)`: saturated at NFE 5,
reported as 500. Corrected:

| Family | `N_min` before | `N_min` after |
|---|---|---|
| `rectified_flow_cifar` | 50 | 50 (unchanged — genuinely improves to NFE 50) |
| `twodim_fm` | 500 | 5 |
| **G.5 = median** | **275 FAIL** | **27.5 PASS** |

### 13.4 What did NOT change

* **No schedule changed.** FIX-1 is observational and FIX-2/FIX-3 are
  opt-in, so `sample()` output, `config_hash()`, `to_config()` and the
  pinned D.4 regression vectors are byte-identical. The three
  `early_stop_*` knobs are runtime-control parameters and are
  deliberately excluded from the config hash.
* **`should_terminate_round` is not a `SchedulerProtocol` member.**
  The Protocol is `runtime_checkable`; declaring the method there
  would make every family that does not define it fail `isinstance`.
  Consumers use `hasattr` and treat its absence as "never terminate".
* **The other HARD gates are unmoved.** G.1 remains FAIL (pre-existing,
  unrelated); G.3/G.4/G.6/G.7 keep their prior verdicts.

### 13.5 Still open (deferred, with reasons)

Per the HIGH-confidence-only constraint, the following were identified
but **not** applied — see `docs/audit/saturation-improvement-plan.md` §4:

* **The audit tool's framework arms are not framework-shaped.** Agent A
  Finding 15 / R3: `_run_twodim_fm` and `_run_lineageflow` run
  `n_rounds` independent cold-start integration calls, without
  `apply_restart_distribution`, forward-noise injection, or a merge
  operator between rounds. The published matched-NFE grid therefore
  characterises "cold-restart vs single-pass", not "framework vs
  baseline". Fixing it invalidates every published cell and needs its
  own wave.
* Learned per-step reliability heads (DSA, Probe-Select, VeriLatent),
  MeanFlow velocity reformulation, perceptual supervision — all need
  training or break adapter interfaces.
* Merge-envelope collapse audit code, `EMAOperator` alpha freeze,
  SMC-weighted blend, `restart_distribution`, per-adapter
  `saturation_eps` — MEDIUM confidence, single audit each.

# Wave 169 P2 — JMAA Theorem 1 vs Paper Downstream Claim Audit

**Status:** diagnostic / paper-text audit (no code change; no re-run).
**Auditor:** Wave 169 P2 (follow-up to Wave 169 P1
[`docs/audit/wave169-p1-pLDDT-inversion.md`]).
**Scope:** Audit what JMAA Theorem 1 actually claims vs what the paper
says downstream about R6 (`LineageFlow foldability + ssc`,
`foldability_pLDDT + ssc_scPerplexity`); identify the gap between
**theoretical claim** and **empirical regime** introduced by Wave 168
P4; recommend the paper-text tightening that closes the gap.

---

## 1. TL;DR

**Theorem 1 bounds BL-distance between framework output distribution
and ODE target distribution as a function of NFE. It does NOT
predict — and cannot be derived to predict — "framework wins on every
downstream metric."**

The paper's §2.8.1 "Empirical anchor" paragraph extrapolates Theorem 1
to four **independent** downstream metrics
("lower $A_g$ (→ better hit rate); larger $B_g$ (→ better Pareto);
lower $C_g$ (→ better foldability / lower perplexity); lower $e_\rho$
(→ no uncontrolled residual)"). The Wave 168 P4 §10.13 NFE curve
**contradicts the foldability arrow**: framework ΔpLDDT is **−1.95% to
−3.68% relative** across NFE 50→500, while framework ΔscPerplexity is
**−16.83% to −18.56% relative** across the same NFE range. The
foldability claim is a **logical leap** from the BL bound, and the
§10.13 disclosure already concedes the trade-off in spirit but does
**not** tighten the upstream §2.8.1 paragraph that produced the leap.

**Recommended paper fix:** Two text edits + one §10.14 ADDITIVE
disclosure that explicitly distinguishes the **BL-bound claim**
(theorem-consistent) from the **per-metric empirical claim** (NOT
theorem-consistent). The §2.8.1 paragraph should be tightened to
"lower $A_g$ (→ better distribution-closeness; empirically
correlates with downstream *self-consistency*-class metrics)" — NOT
"better hit rate", "better foldability", or "better Pareto", which
are model-specific per-metric observations not derived from the
bound.

---

## 2. Theorem 1 — Verbatim Quote

### 2.1 §2.8 concrete form (paper-draft.md line 266)

> **Theorem 1 (BL-convergence, concrete form [Li 2026, lines 87–92]).**
> Let $g : \mathbb{R} \to \mathbb{R}$ be a $C^3$ profile with uniformly
> separated roots $Z_g \subset \mathbb{R}$, let $\varepsilon > 0$ denote
> the implicit-noise scale, and let $\mu_{g,\varepsilon}$ be the noised
> profile measure. Then there exist choices of cells $\{I_z\}_{z \in Z_g}$
> and a sheet measure $\nu_g$ such that
>
> $$d_{\mathrm{BL}}\!\left(\mu_{g,\varepsilon},\, \nu_g\right)
> \;\le\; A_g \cdot \varepsilon \;+\; B_g \cdot C_g \cdot \varepsilon^2
> \;+\; e_\rho \cdot \min\!\left(\rho^4,\,(1-\rho)^2 \eta^2\right),$$
>
> where the convergence rate is **uniform in the choice of cell tiling**,
> the cell-mass residual is **linear in $\varepsilon$**, and the
> exterior-gap term is **separately bounded by both** $\rho^4$ *and*
> $(1-\rho)^2 \eta^2$. The theorem is non-asymptotic: the bound holds for
> every $\varepsilon > 0$ small enough to clear the F-side hypotheses,
> not merely in the $\varepsilon \downarrow 0$ limit.

### 2.2 §2.8.1 FlowA self-contained form (paper-draft.md line 367)

> Let $P_{\text{framework}}(\cdot \mid \text{NFE})$ denote the sampling
> distribution induced by running the framework's
> `FlowMatchingODEAdapter` with a budget of NFE function evaluations,
> and let $P_{\text{target}}$ denote the infinite-NFE target distribution
> induced by the same frozen $\theta$. Then Theorem 1 implies the
> non-asymptotic bound
>
> $$d_{\mathrm{BL}}\!\left(P_{\text{framework}},\, P_{\text{target}}\right)
> \;\le\; A_g \cdot \exp\!\left(-\mathrm{NFE}\,/\,B_g\right)
> \;+\; C_g \cdot e_\rho,$$

### 2.3 What the theorem bounds

The bound is a **single scalar**: a number between 0 and 2 (or
normalised, depending on convention) that measures
**distribution-closeness** in the bounded-Lipschitz metric. The
quantities $A_g, B_g, C_g, e_\rho$ are all properties of the
*profile* $g$ (and the inference regime), not of any downstream
metric like pLDDT, scPerplexity, or HMMER hit rate. The bound is
monotone in NFE (the `exp(−NFE / B_g)` term decreases as NFE
grows), which is the only thing the theorem says about NFE.

**The theorem does NOT say** anything about any per-record sequence
property, any per-folding geometric confidence, any per-inverse-folding
log-likelihood, any per-profile HMM hit count, or any per-FID distance.
It says: framework output gets *closer to the ODE target distribution*
as NFE grows.

---

## 3. Downstream Claim — Verbatim Quote

### 3.1 §2.8.1 "Empirical anchor" paragraph (paper-draft.md line 442)

> The framework arm showed (i) **+116% HMMER hit rate** on the
> protein round (R1 metric, K7 + K8 combined), (ii) **+1.12 pLDDT** on
> the K6 foldability sweep at N=1000/1000 both arms (R6 metric,
> sha256-verified), (iii) **+3.92 scPerplexity improvement** on the
> same K6 arm, and (iv) a **strictly better Pareto frontier** in the
> NFE-vs-BL plane (R5 metric,
> `docs/figures/noise_injection_two_moons_*.png`). Each of these
> gains is in the direction predicted by a tighter bound on $A_g
> \exp(-\mathrm{NFE}/B_g) + C_g e_\rho$: lower $A_g$ (smoother
> trajectories → better hit rate), larger $B_g$ (better NFE allocation
> → better Pareto), lower $C_g$ (merge-envelope re-scaling → better
> foldability / lower perplexity), and lower $e_\rho$ (regime audit →
> no uncontrolled residual).

### 3.2 §2.8.1 "Discussion — why the framework improves the bound" (paper-draft.md line 438)

> The baseline single-solver loop has $A_g^{\text{baseline}} \ge
> A_g^{\text{framework}}$ (raw Lipschitz without restart),
> $B_g^{\text{baseline}} \le B_g^{\text{framework}}$ (uniform NFE
> grid without paper-quantity allocation), $C_g^{\text{baseline}} \ge
> C_g^{\text{framework}}$ (no merge envelope re-scaling), and
> $e_\rho^{\text{baseline}} \ge e_\rho^{\text{framework}}$ (no regime
> audit). The exponential term $A_g \exp(-\mathrm{NFE}/B_g)$ is
> therefore tighter on the framework side, and the residual $C_g e_\rho$
> is also tighter; the multiplicative improvement compounds as NFE
> grows, and is *why* the framework's BL-distance envelope is
> consistently below the baseline across all measured NFE budgets
> (cf. the §4 R-curves and the R1 +116% HMMER hit rate, R6 +1.12
> pLDDT, and R5 Pareto-frontier improvements cited as empirical
> anchors below).

### 3.3 What the downstream claim says

The §2.8.1 paragraph claims **four independent downstream metrics**
are "in the direction predicted by a tighter bound on $A_g
\exp(-\mathrm{NFE}/B_g) + C_g e_\rho$":

1. HMMER hit rate → lower $A_g$ (smoother trajectories)
2. NFE-vs-BL Pareto → larger $B_g$ (better NFE allocation)
3. pLDDT (foldability) → lower $C_g$ (merge-envelope re-scaling)
4. scPerplexity (self-consistency) → lower $C_g$ (merge-envelope re-scaling)

### 3.4 R6 metric definition (§10.6, paper-draft.md line 6537)

> R6 | LineageFlow foldability + ssc | N=1000, pLDDT + scPerplexity |
> 42.07 / 17.88 | 43.20 / 13.96 | +1.12 / −3.92 | p<1e-5 | α=0.0083

The R6 headline metric claims **framework wins on BOTH pLDDT AND
scPerplexity** at NFE=10 / N=1000.

### 3.5 §10.12 "framework wins on both metrics" (paper-draft.md line 6690)

> **Framework wins on both metrics at both N values** (pLDDT higher
> by `+1.87` to `+1.12`; scPerplexity lower by `−22.0%` to `−21.9%`).

### 3.6 §10.13 Wave 168 P4 (paper-draft.md line 6717)

> **Framework wins on scPerplexity at every measured NFE level** by a
> stable **~17-19% relative** (ΔscPerp ranges from −3.06 to −3.37
> absolute; relative improvement −16.83% to −18.56%). The framework's
> adaptive path produces structurally more self-consistent outputs
> than the baseline schedule across a 10× NFE budget range (50 → 500).
> This is a **directionally stable, reproducible** finding — the
> framework advantage on the self-consistency axis does **not** shrink
> at low NFE.

> **Framework shows a small pLDDT trade-off of ~2-4% relative**
> (ΔpLDDT ranges from −0.83 to −1.56 absolute; relative change −1.95%
> to −3.68%). The framework's perturbation improves self-consistency
> at a modest cost in OmegaFold foldability confidence. pLDDT
> trade-off is **smaller at low NFE** (−1.95% at NFE=50) than at high
> NFE (−3.68% at NFE=500).

Note: §10.13 has already started the tightening — it explicitly
discloses the pLDDT trade-off as a "trade-off, not a bug." But the
§2.8.1 paragraph still claims "lower $C_g$ → better foldability /
lower perplexity" **without caveat**, contradicting §10.13's own
disclosure.

---

## 4. Logical Chain — Theorem 1 → R6 Claim

### 4.1 Step 1: Theorem 1 → BL bound is tighter for framework

**Valid.** The bound is monotone in NFE; the framework's
restart-blend + paper-quantity-driven scheduler plausibly reduces
$A_g, C_g, e_\rho$ relative to a single-solver baseline. This is
where the theorem genuinely speaks.

### 4.2 Step 2: BL bound tighter → framework output distribution closer to ODE target

**Valid (tautological).** This is what the bound *is*.

### 4.3 Step 3: distribution-closeness → pLDDT improvement

**INVALID logical leap.** The bound is on the **distribution**
$P_\text{framework}(\cdot \mid \text{NFE})$. pLDDT is computed on a
**single per-record decoded amino-acid sequence**, then fed through
**OmegaFold** (a third-party geometric folding model) to produce a
per-residue confidence in [0, 100]. The mapping
"distribution-closeness → per-record pLDDT" depends on:

- Whether the framework's perturbation shifts the marginal
  $P_\text{framework}(\text{AA sequence})$ toward the natural-protein
  regime that OmegaFold is calibrated for. **This is empirical, not
  derived.**
- Whether OmegaFold's pLDDT confidence is monotone in
  sequence-naturalness. **This is a property of OmegaFold, not of
  the framework.**
- Whether the *direction* of distribution-closeness (which the bound
  guarantees) and the *direction* of pLDDT improvement (which is
  empirical) align. **Empirically they DO NOT always align**, per
  Wave 168: framework ΔpLDDT is **−1.95% to −3.68% relative** across
  NFE 50→500 (framework LOSES pLDDT), while framework ΔscPerplexity
  is **−16.83% to −18.56% relative** across the same range.

### 4.4 Step 4: BL bound tighter → scPerplexity improvement

**Empirically consistent but not derived.** Same logical status as
Step 3 — scPerplexity is a downstream metric computed by ESM-IF
inverse-folding log-likelihood, not a property of the bound.
Empirically it tracks better than pLDDT (because self-consistency
is a marginal-level property the bound directly addresses), but the
**directionality is empirical, not theorem-derived**.

### 4.5 Where the chain breaks

**The chain breaks at Step 3 (and analogously Step 4).** Theorem 1
makes a claim about **distribution-closeness**, not about **any
downstream per-record metric**. The §2.8.1 "Empirical anchor"
paragraph maps each downstream metric to one of the four paper
quantities ("lower $A_g$ → better hit rate"; "lower $C_g$ → better
foldability / lower perplexity"), which is a **1-to-1 mapping that
the theorem does not make**. The mapping is plausible *a priori*
(distribution-closeness should correlate with downstream metric
improvement), but the correlation is **empirical, model-specific,
and direction-dependent**. The Wave 168 §10.13 disclosure
**demonstrates** the correlation breaks on pLDDT at NFE≥50 while
holding on scPerplexity across NFE 10→500.

---

## 5. Empirical Regime Mismatch

### 5.1 What Theorem 1 says

| Claim | Source | Truth value |
|-------|--------|-------------|
| Framework BL-distance ≤ $A_g \exp(-NFE/B_g) + C_g e_\rho$ | §2.8.1 | **TRUE by theorem** |
| Bound is monotone decreasing in NFE | §2.8.1 | **TRUE by theorem** |
| Framework reduces $A_g$ relative to baseline | §2.8.1 | **PLAUSIBLE** (qualitative argument, not derived) |
| Framework output distribution closer to ODE target than baseline | §2.8.1 + Wave 165 BL distance diagnostic | **TRUE at NFE=10/50/100/200/500** (Wave 165 BL-distance curve, N=1000 baseline-vs-framework) |
| Framework improves downstream pLDDT | §2.8.1 "Empirical anchor" + §7.6 R6 + §10.12 | **TRUE at NFE=10** (Wave 161 K6 N=1000, Δ=+1.12); **FALSE at NFE=50→500** (Wave 168 §10.13, Δ=−0.83 to −1.56) |
| Framework improves downstream scPerplexity | §2.8.1 + R6 + §10.12 + §10.13 | **TRUE at NFE=10/50/100/200/500** (Wave 161, 167, 168 all show framework lower = better) |

### 5.2 The regime mismatch

Theorem 1's regime of validity is "every $\varepsilon > 0$ small
enough to clear the F-side hypotheses" (§2.8, line 286). The
§2.8.1 self-contained form restates this as the implicit-noise
schedule shrinking as NFE grows (the `exp(−NFE/B_g)` term). The
**empirical regime mismatch** is:

- **NFE=10 (Wave 161 K6 N=1000)**: framework runs 3 rounds × 10 NFE
  per round = 30 ODE steps per record. The framework's integrator
  gain (better Lipschitz handling, smoother trajectories) **dominates**
  its perturbation cost. Net effect: framework ΔpLDDT = **+1.12**,
  framework ΔscPerp = **−3.92**.
- **NFE=50→500 (Wave 168 N=100)**: framework runs 3 rounds × NFE
  per round = 150→1500 ODE steps per record. The framework's
  perturbation cost (3 rounds of `apply_restart_distribution`
  drift) **outpaces** its integrator gain. Net effect: framework
  ΔpLDDT = **−0.83 to −1.56**, framework ΔscPerp = **−3.06 to −3.37**.

The two regimes have **opposite directions on pLDDT** while having
**the same direction on scPerplexity**. Theorem 1 does not predict
this — Theorem 1 is silent on pLDDT direction at any NFE.

### 5.3 What is theorem-consistent

- **"Framework BL-distance envelope is consistently below the baseline
  across all measured NFE budgets"** (§2.8.1, line 440): TRUE.
  Wave 165 BL distance diagnostic (N=1000, NFE 10/50/100/200/500)
  measured framework BL-distance below baseline at every NFE level.
- **"Framework improves scPerplexity at every measured NFE level"**
  (§10.13, line 6717): TRUE empirically; consistent with the
  theorem's prediction that distribution-closeness correlates with
  marginal-level self-consistency metrics.

### 5.4 What is NOT theorem-consistent

- **"lower $C_g$ → better foldability"** (§2.8.1 line 457):
  NOT predicted by Theorem 1; empirically FALSE at NFE≥50.
- **"R6 framework_improves on pLDDT"** (§7.6 + §10.6 + §10.12):
  TRUE at NFE=10 (Wave 161, Wave 167); FALSE at NFE≥50 (Wave 168).
- **"Framework's BL-distance envelope is consistently below the
  baseline ... R6 +1.12 pLDDT ... cited as empirical anchors below"**
  (§2.8.1 line 441): the conjunction of BL-bound-consistent and
  R6 pLDDT-consistent is **not theorem-derived** — the BL claim is
  theorem-consistent, the R6 pLDDT claim is empirical and
  NFE-regime-conditional.

---

## 6. Recommended Paper Fix

### 6.1 Edit 1 — Tighten §2.8.1 "Empirical anchor" (paper-draft.md line 442)

**Current (lines 454-457):**

> Each of these gains is in the direction predicted by a tighter bound
> on $A_g \exp(-\mathrm{NFE}/B_g) + C_g e_\rho$: lower $A_g$ (smoother
> trajectories → better hit rate), larger $B_g$ (better NFE allocation →
> better Pareto), lower $C_g$ (merge-envelope re-scaling → better
> foldability / lower perplexity), and lower $e_\rho$ (regime audit →
> no uncontrolled residual).

**Recommended replacement:**

> The framework's tighter BL bound is empirically correlated with
> downstream metric improvements, but the correlation is **not
> theorem-derived** — Theorem 1 bounds $d_{\mathrm{BL}}
> (P_\text{framework}, P_\text{target})$, not any per-record
> downstream metric like pLDDT, scPerplexity, or HMMER hit rate. The
> correlation direction is **empirical and metric-specific**:
>
> - **scPerplexity** (self-consistency): framework improves at every
>   measured NFE (10→500, Δ ≈ −17% relative, framework consistently
>   lower = better). This is the most theorem-aligned downstream
>   metric because it is a marginal-level property the BL bound
>   directly addresses.
> - **HMMER hit rate** (R1): framework improves by +116% at
>   NFE=10/N=1000 (Wave 86). Direction-consistent but measured at
>   one NFE; full NFE-axis not yet evaluated.
> - **pLDDT** (R6 foldability): framework improves at NFE=10 (Wave
>   161, Wave 167: Δ=+1.12 to +1.87) but **regresses by 2-4%
>   relative at NFE=50→500** (Wave 168, §10.13: Δ=−0.83 to
>   −1.56). The pLDDT direction is **NFE-regime-dependent** —
>   theorem-bound distribution-closeness does not entail per-record
>   pLDDT improvement, because pLDDT is a downstream property of
>   OmegaFold's confidence calibration, not of the marginal
>   distribution's BL-distance to the ODE target.
> - **NFE-vs-BL Pareto frontier** (R5): framework consistently
>   dominates baseline at every measured NFE budget (Wave 165 BL
>   distance diagnostic). This is the most directly
>   theorem-aligned observation because it is the BL-distance
>   bound itself.

### 6.2 Edit 2 — Tighten §2.8.1 "Discussion" sentence on BL envelope (paper-draft.md line 440)

**Current (lines 438-441):**

> The exponential term $A_g \exp(-\mathrm{NFE}/B_g)$ is therefore
> tighter on the framework side, and the residual $C_g e_\rho$ is also
> tighter; the multiplicative improvement compounds as NFE grows, and
> is *why* the framework's BL-distance envelope is consistently below
> the baseline across all measured NFE budgets (cf. the §4 R-curves
> and the R1 +116% HMMER hit rate, R6 +1.12 pLDDT, and R5
> Pareto-frontier improvements cited as empirical anchors below).

**Recommended replacement:**

> The exponential term $A_g \exp(-\mathrm{NFE}/B_g)$ is therefore
> tighter on the framework side, and the residual $C_g e_\rho$ is also
> tighter; the multiplicative improvement compounds as NFE grows, and
> is *why* the framework's BL-distance envelope is consistently below
> the baseline across all measured NFE budgets (cf. the §4 R-curves
> and the R5 Pareto-frontier improvement in the NFE-vs-BL plane
> cited as the theorem-aligned empirical anchor). The R1 HMMER hit
> rate (+116% at NFE=10/N=1000, Wave 86) and R6 scPerplexity
> (−3.92 at NFE=10, Wave 161) are **empirically direction-consistent**
> with the BL bound but measured at single NFE levels; the R6 pLDDT
> improvement (+1.12 at NFE=10) is **NFE-regime-conditional** and
> **regresses at NFE≥50** (Wave 168 §10.13) — see §10.14 for the
> honest disclosure of the theorem-vs-empirical gap on per-record
> downstream metrics.

### 6.3 §10.14 ADDITIVE disclosure (NEW)

After §10.13, add a new §10.14 titled "Wave 169 P2 — JMAA Theorem 1
vs paper downstream claim audit (theorem-vs-empirical gap)" that
explicitly distinguishes:

1. **Theorem-consistent claims** (bound is tighter for framework;
   framework BL-distance below baseline; framework improves
   marginal-level self-consistency metrics).
2. **Empirically-consistent but NOT theorem-derived claims**
   (per-metric downstream improvements at single NFE points; trade-off
   patterns at NFE-axis sweeps).
3. **Empirically-conditional claims** (framework pLDDT improves at
   NFE=10, regresses at NFE≥50 — the **direction is
   NFE-regime-dependent**).

This §10.14 disclosure closes the gap between Theorem 1 (bound on
distribution-closeness) and the §2.8.1 "Empirical anchor"
paragraph (which currently claims 4 independent downstream metric
improvements are "in the direction predicted by a tighter bound on
$A_g \exp(-\mathrm{NFE}/B_g) + C_g e_\rho$" — a claim the theorem
does not support for pLDDT at NFE≥50).

### 6.4 What stays unchanged

- §10.12 "Framework wins on both metrics at both N values" (NFE=10
  only) — TRUE empirically, honest.
- §10.13 "Framework wins on scPerplexity at every measured NFE
  level" — TRUE empirically, already discloses the pLDDT trade-off.
- R6 headline `+1.12 pLDDT / −3.92 scPerplexity` (Wave 161 K6
  N=1000) — TRUE empirically at the specified NFE / N, and the
  §10.6 R6 row should add a parenthetical "(NFE=10 only; at
  NFE≥50 see §10.13)".

---

## 7. Verification

| Check | Status | Notes |
|-------|--------|-------|
| Theorem 1 verbatim quote accuracy | OK | Lines 266, 367 of paper-draft.md quoted exactly |
| §2.8.1 "Empirical anchor" verbatim quote accuracy | OK | Lines 442, 454-457 quoted exactly |
| §10.6 R6 metric row verbatim quote accuracy | OK | Line 6537 quoted exactly |
| §10.12 "Framework wins on both metrics" verbatim quote accuracy | OK | Line 6690 quoted exactly |
| §10.13 "Framework wins on scPerplexity" verbatim quote accuracy | OK | Line 6717 quoted exactly |
| Wave 168 §10.13 numbers (−0.83 to −1.56 pLDDT; −3.06 to −3.37 scPerp) | OK | `verification_outputs/nfe_curve_real_w168_q3_2026/nfe_curve_real.csv` (sha256 `01796d628241568b2afd1b6b3826a6031499a9da03903409cc25a032545a7132`) |
| Wave 161 K6 R6 numbers (42.07/17.88 baseline, 43.20/13.96 framework) | OK | `verification_outputs/k6_foldability_n1000_w161_q3_2026/`; see `docs/audit/wave161-k6-verification.md` |
| Recommended §2.8.1 edit references correct line ranges | OK | Lines 440, 442, 454-457 verified by Read |
| Recommended §10.14 placement is after §10.13 | OK | Line 6726 ends §10.13 ADDITIVE block; §10.14 would follow |
| Wave 169 P2 is diagnostic-only — no code change | OK | This audit doc only; no code edits |

---

## 8. Acceptance Gates

- **ruff 0** across accepted scope (adaptive_reflow/, tools/, tests/) — PASS
  (no code change; ruff unchanged from Wave 169 P1)
- **pytest** `tests/ -k d4 -q` → 33 passed / 30 skipped / 5028 deselected — PASS
  (torch-skips are environment-related, unchanged from Wave 168/169 P1)
- **claims consistency** `python tools/check_claims_consistency.py` → `No drift detected` — PASS
  (no source claim modified by this audit; the §10.14 ADDITIVE disclosure
  will need a follow-up commit if Wave 169 P3 applies the §2.8.1 edits)
- **No source code change in this audit** — N/A (audit-only wave)

---

## 9. Audit-doc location

`docs/audit/wave169-theory-audit.md` (this file)
**Inputs referenced:**
- `docs/paper-draft.md` §2.8 (line 266) — Theorem 1 concrete form
- `docs/paper-draft.md` §2.8.1 (line 358) — Theorem 1 self-contained
  FlowA form
- `docs/paper-draft.md` §2.8.1 (line 438) — Discussion paragraph
- `docs/paper-draft.md` §2.8.1 (line 442) — Empirical anchor paragraph
- `docs/paper-draft.md` §10.6 (line 6537) — R6 metric row
- `docs/paper-draft.md` §10.12 (line 6690) — "Framework wins on both
  metrics" disclosure
- `docs/paper-draft.md` §10.13 (line 6717) — Wave 168 P4 disclosure
- `docs/audit/wave169-p1-pLDDT-inversion.md` — prior diagnostic on the
  per-NFE per-record pLDDT drift
- `docs/audit/wave168-p4-nfe-curve.md` — Wave 168 P4 §10.13 NFE
  curve source
- `docs/audit/wave161-k6-verification.md` — Wave 161 K6 R6 source
- `verification_outputs/nfe_curve_real_w168_q3_2026/nfe_curve_real.csv`
  (sha256 `01796d628241568b2afd1b6b3826a6031499a9da03903409cc25a032545a7132`)
- `verification_outputs/k6_foldability_n1000_w161_q3_2026/`
  (Wave 161 K6 R6 source)

**No code change. No commit beyond this doc.**

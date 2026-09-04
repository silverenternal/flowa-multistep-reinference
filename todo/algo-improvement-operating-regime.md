# Algorithm improvement — operating-regime theoretical analysis

**Status:** done (Wave 17 P3 — CRITICAL gap closed; docs/theory/operating-regime.md + framework-internal-metrics C.5 + docs/CONDITIONS.md APPEND)
**Date:** 2026-09-05
**Priority:** CRITICAL (this is the framework's core claim — without it,
all empirical claims are unfounded; reviewer's first question will be
"when should I use this?" and we currently have no answer)
**Depends on:** Wave 15 Phase 1 (F.5 env_hash), Algo B (rate bound
theorem), Algo D (controlled noise injection), Wave 15 Agent F (F.2
reproduction)
**Owner:** framework maintainer
**Goal:** Establish (mathematically or empirically) the operating regime
where framework's multi-round re-inference provides corrective value.
Answer: when does framework help, when neutral, when regress?

## Background

We have:

- **What** the framework implements (JMAA theory + Algorithm layer)
- **Empirical observations** (Wave 6 + Wave 14 baseline; F.2 = 4/8
  REPRODUCED; 36 measured algorithm uplifts with assertion-strength tags)
- **Honest negative results** (2D RF regressed post-cd70821; FlowMol3
  CTMC gap; LineageFlow BLOCKED on upstream `core`)

We don't have:

- **Why** the framework helps when it does
- **When** to expect help vs neutral vs regression
- **A theoretical or empirical operating regime** with explicit boundary

This is the framework's **core claim**. Without it:

- Reviewers can't evaluate the framework's value
- Users can't predict when to apply the framework
- Paper claims are unfalsifiable

## What to do

### Step 1: Theoretical analysis (try to derive; fall back to empirical)

Mathematical approach: given base adapter with additive noise
ε·N(0,I) on velocity output, what is the expected gain of K rounds of
re-inference?

Possible answers (in order of likelihood):

1. **Statistical averaging**: K rounds reduce noise variance by factor K
   → expected gain ~ sqrt(K)/ε
2. **Concentration**: Multi-round consensus around sheet (per JMAA paper
   Theorem 1) → gain concentrates on correct sheet
3. **Bias-variance tradeoff**: For low base accuracy, re-inference adds
   variance; for high base accuracy, re-inference adds bias
4. **No general rule**: Framework's value depends on model-specific
   properties that resist mathematical abstraction

If theoretical analysis is tractable, document in
`docs/theory/operating-regime.md` as a theorem.

### Step 2: Empirical characterisation (always do this)

Sweep:

- **Noise level** σ ∈ {0, 0.01, 0.05, 0.1, 0.2, 0.5} (over base velocity
  output)
- **Base adapter type** (twodim_fm as baseline; FlowMol3 as chemistry;
  Self-Flow as image)
- **Rounds** K ∈ {1, 2, 4, 8, 16}

For each combination:

- Run baseline (no framework) — measure base metric M_0(σ, K)
- Run framework (multi-round) — measure M_F(σ, K)
- Compute uplift U(σ, K) = (M_F - M_0) / M_0
- Plot U as function of σ (x-axis) and K (color/family)

**Transition point** σ* is where framework starts to help. Plot this
against base accuracy.

### Step 3: Outcome

A `docs/CONDITIONS.md` (rename from current plan; per Wave 15 Agent F's
regen) with:

- 3+ (model, NFE-budget) Pareto plots (per C.5 spec)
- An explicit operating regime statement:
  - "framework helps when σ ∈ [σ_low, σ_high] and K >= K_min"
  - "framework neutral when σ < σ_low"
  - "framework regresses when σ > σ_high"
- Theoretical justification (if available) OR empirical threshold (if
  not)
- Honest section: "what we don't know" — limits of current analysis

## Files affected

- `docs/theory/operating-regime.md` (NEW; theoretical analysis or
  empirical justification)
- `docs/CONDITIONS.md` (UPDATE; include operating regime statement)
- Possibly: `adaptive_reflow/theory/operating_regime.py` (NEW; if
  theoretical result is a function)
- Possibly: `tests/test_theory/test_operating_regime.py` (NEW; if
  testable)

## Acceptance

- [ ] `docs/theory/operating-regime.md` exists with substantive analysis
      (≥ 100 lines; not just "we observe that...")
- [ ] `docs/CONDITIONS.md` updated with operating regime statement
- [ ] Empirical sweep completed (if not theoretical)
- [ ] At least 3 Pareto plots in `docs/CONDITIONS.md`
- [ ] Honest section on what we DON'T know
- [ ] Commit + push

## Estimated time

- Theoretical analysis: 1-2 weeks (math + proofs + sanity checks)
- Empirical sweep: 1-3 days GPU (Algo D + per-model runs)
- Documentation: 2-4 hours

## Acceptance gate

**Gate name:** `G-OPERATING-REGIME` (new)

**Pre-condition:** Algo D (controlled noise injection) completed OR
theoretical analysis tractable
**Pass conditions:**

- [ ] All acceptance checklist items
- [ ] Operating regime documented in `docs/CONDITIONS.md`

## Critical observation

**This is the framework's hardest missing piece.** Without it:

- Paper reviewers will ask "when should I use this?" and we have no answer
- Algorithm improvement claims are unfalsifiable
- The framework's value boundary is unclear

Even an empirical answer ("framework helps when noise σ ∈ [0.05, 0.2]")
is publishable.

## Out of scope

- Proving the operating regime is OPTIMAL (would need different theory)
- Extending to all adapters (3 representative models is enough for
  first pass)

## Related

- `framework-internal-metrics.md` §1 C.5 (failure-mode characterisation;
  sister task)
- `todo/algo-improvement-failure-modes.md` (Algo D; provides σ sweep)
- `docs/CONDITIONS.md` (existing; per C.5 spec, needs operating regime
  addition)
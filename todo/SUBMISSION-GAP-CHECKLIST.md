# FlowA — CAS Tier-1 / TNNLS submission gap checklist

**Date:** 2026-10-12
**Status:** living checklist. Every row is an executable fix with an **owner**, a
**blocker**, a **required resource**, and an **acceptance criterion**. All items
are OPEN unless marked otherwise.
**Trigger:** user request — turn the submission-readiness assessment into an
executable gap list; *all* points raised are in scope.
**Scope:** planning/audit doc only. This file changes **no** number, claim,
manuscript artifact, source module, or vendored-upstream file. It schedules the
work; it does not perform it.

---

## 0. How to use

- **Priority.** `P0` = load-bearing for a Tier-1 decision (the paper is materially
  weaker without it). `P1` = materially raises the odds. `P2` = polish / hygiene.
- **Owner.** `agent` = doable in-repo now. `gpu` = needs a GPU/experiment run.
  `user` = user-gated decision or action.
- **Rule.** No fix may move a headline number or flip a claim status by wording
  alone (AGENTS.md guardrails #4 honest-uncertainty, #5 submission-freeze). A
  number changes only when a *new measurement* backs it, and the change is
  recorded as an additive addendum, never a silent edit.
- **Every fix ends with:** the gate chain in §5 + a per-fix audit doc under
  `docs/audit/`.
- **NO-PUSH** — commits carry the `(USER AUTHORIZED, NO PUSH)` footer; push is
  user-gated.

## 1. Where the paper stands (one screen)

- The framework contribution (training-free, solver-agnostic re-inference layer;
  typed four-port contract surface; zero-line vendored integration; hash-chained
  ledger) and the reproducibility infrastructure (byte-stable regression, SHA-256
  ledger, per-cell recipes) are **strong and already Tier-1-grade**.
- The **empirical headline is the weak axis.** The "4 STRONG" label decomposes
  into **one unconditional (R2, medium effect, synthetic-path caveat)** and
  **three conditional** results (R5b only at `n_rounds=1`; R5c only on the *smoke*
  checkpoint; R6 only via a *counterfactual* proxy). The two flagship
  protein/molecule cells are **single-seed (R1)** and **projected (R3)**.
- The **theory is conditional and partly outsourced** (Theorems 4/5 are a
  conditional contraction + an arithmetic identity; the sampling-measure
  convergence result lives in a companion paper this one does not depend on).
- Several **credibility landmines** remain: an extrapolated speedup presented
  near the abstract, an overstated formal-verification claim, a 99.6 %-I² pooled
  meta-analysis, and an un-tuned-baseline exposure.

## 2. Scoreboard

| ID | Priority | Owner | One-line gap |
|---|---|---|---|
| GAP-01 | P0 | gpu | R6: counterfactual-STRONG → live-GPU-STRONG |
| GAP-02 | P0 | gpu | R3: N=1000 PROJECTED → ACTUAL |
| GAP-03 | P0 | gpu | R1: single-seed → 3-seed |
| GAP-04 | P0 | gpu | R5b: matched-protocol multi-seed round-count test |
| GAP-05 | P0 | agent(+gpu) | R5c: production-ckpt regime stated conditionally |
| GAP-06 | P0 | agent | Headline reframe: unconditional vs conditional STRONG |
| GAP-07 | P0 | agent | NFE speedup: drop 2.5–10× extrapolation; state measured 1.0× |
| GAP-08 | P0 | agent(+gpu) | R2: the one unconditional STRONG — strengthen or scope |
| GAP-09 | P1 | agent(+gpu) | Theory: testable criterion for `q<1` / blend benefit |
| GAP-10 | P1 | agent | Mechanism (residual correction): test it or scope it |
| GAP-11 | P1 | agent | I²=99.6 % pooled meta-analysis: drop or re-aggregate |
| GAP-12 | P1 | agent(+gpu) | Baseline fairness: matched-NFE + tuned baseline |
| GAP-13 | P1 | agent/user | Lean 4 claim: finish or downscope |
| GAP-14 | P1 | agent | Novelty boundary vs prior training-free methods |
| GAP-15 | P1 | user | Venue-fit decision (TNNLS vs reposition) |
| GAP-16 | P2 | agent | 31 deferred reviewer-facing gaps |
| GAP-17 | P2 | gpu | K2/K6 env-blocked per-cell sweeps |
| GAP-18 | P2 | agent | Dead link in manuscript §7.11 (wave280 contamination doc) |
| GAP-19 | P2 | agent | Stale citations / state pins |
| GAP-20 | P2 | user | 17 `[USER TO FILL]` cover-letter placeholders |

---

## 3. P0 — load-bearing

### GAP-01 — R6: convert counterfactual-STRONG to live-GPU-STRONG
- **Owner:** gpu (launch is user-gated).
- **Blocker:** GPU budget ~26–53 GPU-h on GPU 0; contention with the user-owned
  `dfine_t146` workload (~28 GB).
- **Action:** run the 3-seed × `N=1000` paired live sweep
  (`TierAwareCodimensionSheetScheduler` full stack) and replace the counterfactual
  verdict with a live one.
- **Handle:** `docs/audit/wave357-r6-gpu-scope.md`; `docs/drafts/paper-A-final.md`
  §10.5; `docs/CLAIMS.md` CLM-073; `todo/RISK-REGISTER.md` R-019.
- **Acceptance:** live 3-seed × `N=1000` paired `d_z` ≥ +0.2235; §7.2 R6 label
  becomes "live-GPU-STRONG"; MANIFEST + ledger refreshed; audit doc written.

### GAP-02 — R3: `N=1000` PROJECTED → ACTUAL
- **Owner:** gpu (env pinning).
- **Blocker:** RDKit 2026.03.5 environment drift (valid-yield 36.7 % vs canonical
  99.9 %).
- **Action:** pin the canonical RDKit (or container-reproduce the Wave 82 stack),
  then run the full `N=1000` paired `fg_dev` sweep.
- **Handle:** `docs/audit/wave351-r3-vendor-fix-status.md`; §10.1; `docs/CLAIMS.md`
  CLM-068.
- **Acceptance:** valid yield ≥ 99 %; `N=1000` paired measured (not projected);
  §7.2 R3 label drops "PROJECTED".

### GAP-03 — R1: single-seed → 3-seed
- **Owner:** gpu.
- **Blocker:** seed-43/44 framework-fallback contamination; earlier probes hit the
  120 s wall-clock.
- **Action:** run the 3-seed (`42/43/44`) `N=1000` sweep with
  `framework_fallback_per_family_count` verified `{}` per seed; re-adjudicate the
  R1 verdict on clean evidence.
- **Handle:** §7.2 R1 row; `docs/audit/wave280-p-r1-sweep-result.md`;
  `docs/CLAIMS.md` CLM-060.
- **Acceptance:** 3-seed fallback verified zero; R1 either promoted (if the effect
  holds) or retained as PARTIAL **with clean 3-seed evidence** — no promotion by
  wording.

### GAP-04 — R5b: matched-protocol multi-seed round-count test
- **Owner:** gpu.
- **Blocker:** needs a matched-NFE / matched-seed protocol across round counts.
- **Action:** `n_rounds ∈ {1,2,3}` × 4 schedulers × 3 seeds at matched NFE;
  confirm or refute the first-round-only boundary.
- **Handle:** §7.7; §11.2 ("next empirical priority"); `docs/CLAIMS.md` CLM-070.
- **Acceptance:** boundary confirmed (or refuted) at multi-seed; §7.6/§7.7 updated
  additively.

### GAP-05 — R5c: production-checkpoint regime stated conditionally
- **Owner:** agent (+ optional gpu).
- **Blocker:** none for framing.
- **Action:** make the regime-conditioned statement explicit everywhere (smoke
  STRONG / intermediate + production REGRESSES); remove any unconditional "R5c
  STRONG" reading.
- **Handle:** §7.9; `docs/CLAIMS.md` CLM-059;
  `verification_outputs/wave280-p-r5c/aggregate.json`.
- **Acceptance:** every R5c mention carries the checkpoint regime.

### GAP-06 — Headline reframe: unconditional vs conditional STRONG
- **Owner:** agent.
- **Blocker:** none.
- **Action:** state in the abstract, §1 contributions (v), and §11.1 that the
  main-cell pattern is **one unconditional STRONG (R2) + three conditional
  (R5b/R5c/R6) + one TIE (R5a)**, not a flat "4 STRONG".
- **Handle:** abstract; §1 (v); §11.1.
- **Acceptance:** no flat "4 STRONG" framing survives; the conditional structure is
  explicit and consistent across the three surfaces.

### GAP-07 — NFE speedup honesty
- **Owner:** agent.
- **Blocker:** none.
- **Action:** stop presenting the 2.5–10× cross-budget range as a result; state
  that the **directly measured** speedup is 1.0× and the range is a
  published-trajectory extrapolation.
- **Handle:** abstract; §1; `tnnls_submission/supplementary_bundle/headline_evidence/NFE_SPEEDUP_2P5_TO_10X_SOURCE.md`.
- **Acceptance:** no extrapolated speedup stated as a measured result.

### GAP-08 — R2: the one unconditional STRONG
- **Owner:** agent (+ optional gpu).
- **Blocker:** R2 evidence carries a synthetic-path caveat and a medium effect.
- **Action:** either confirm R2 on the real checkpoint (non-synthetic path) or make
  the synthetic-path scope explicit at the headline.
- **Handle:** §7.2 R2 row; `docs/CLAIMS.md` CLM-060.
- **Acceptance:** R2 is either real-ckpt-confirmed or explicitly scoped; it is not
  presented as an unconditional win without qualification.

---

## 4. P1 — materially raises the odds

### GAP-09 — Theory: a testable criterion
- **Owner:** agent (+ optional gpu).
- **Action:** add a measurable diagnostic for `q = mK < 1` (Theorem 4) and for
  when the blend helps (Eq. 7, Theorem 5), then verify it predicts the **sign** of
  the effect on ≥ 1 cell.
- **Handle:** §6.5, §6.6, §11.2.
- **Acceptance:** ≥ 1 cell where the criterion's predicted direction matches the
  measurement; otherwise the theorem stays explicitly conditional and unscored.

### GAP-10 — Mechanism claim (residual correction)
- **Owner:** agent.
- **Action:** either run a targeted ablation testing the residual-correction
  mechanism, or state plainly that it is a hypothesis (not a consequence of
  Theorems 4–5) wherever it appears.
- **Handle:** §11.1.
- **Acceptance:** no mechanism claim stronger than the evidence.

### GAP-11 — I² = 99.6 % pooled meta-analysis
- **Owner:** agent.
- **Action:** drop the single pooled `d_z` as a headline, or re-aggregate
  per-domain / with a prediction interval and an explicit heterogeneity caveat.
- **Handle:** §Statistical Methods; §7.10 area.
- **Acceptance:** no high-heterogeneity pooled effect presented without the caveat.

### GAP-12 — Baseline fairness
- **Owner:** agent (+ optional gpu).
- **Action:** ensure each headline comparison uses matched NFE + schedule and at
  least one **tuned** baseline (not default settings).
- **Handle:** §7 comparisons; the McGreivy & Hakim reference.
- **Acceptance:** a tuned-baseline comparison exists per headline cell; the
  straw-man-baseline exposure is closed.

### GAP-13 — Lean 4 formal-verification claim
- **Owner:** agent/user.
- **Blocker:** 12 `sorry` sites across 4 stub files; Mathlib precompilation
  incomplete.
- **Action:** either discharge the `sorry`s for the claimed theorems or remove /
  reword the formal-verification claim so it matches the actual state.
- **Handle:** `formal/FlowA/*.lean`; `tnnls_submission/SUBMISSION_READINESS.md`
  PENDING #4.
- **Acceptance:** the claim matches reality (0 `sorry` for what is claimed, or no
  claim).

### GAP-14 — Novelty boundary vs prior training-free methods
- **Owner:** agent.
- **Action:** add an explicit differentiation paragraph against DPM-Solver++,
  UniPC, consistency models, Fast-DLLM, and LeDiFlow.
- **Handle:** §1; §2 related work.
- **Acceptance:** the "re-inference / restart blend" contribution is clearly
  distinct from existing restart / predictor-corrector / training-free acceleration.

### GAP-15 — Venue-fit decision
- **Owner:** user.
- **Action:** confirm TNNLS vs repositioning to a systems/ML-applications venue;
  align the positioning accordingly.
- **Handle:** `todo/RISK-REGISTER.md` R-019.
- **Acceptance:** venue decided; abstract/intro positioning matches it.

---

## 5. P2 — polish / hygiene

### GAP-16 — 31 deferred reviewer-facing gaps
- **Owner:** agent. **Action:** triage the list; close the low-impact ones or
  record explicit acceptance. **Handle:** `docs/audit/wave364-paper-polish-gaps.md`
  §5.

### GAP-17 — K2/K6 env-blocked per-cell sweeps
- **Owner:** gpu. **Action:** pin the env and sweep, or retain the honest
  disclosure. **Handle:** `tnnls_submission/SUBMISSION_READINESS.md` PENDING #5.

### GAP-18 — Dead link in manuscript §7.11
- **Owner:** agent. **Action:** §7.11 (line 568) cites
  `docs/audit/wave280-p-framework-fallback-contamination.md`, which **does not
  exist**; repoint to the canonical `docs/audit/wave280-p-r1-sweep-result.md`.
  **Handle:** `docs/drafts/paper-A-final.md` §7.11.

### GAP-19 — Stale citations / state pins
- **Owner:** agent. **Action:** (a) `tnnls_submission/SUBMISSION_READINESS.md`
  cites a §11.1 "Q1 acceptance-probability 60–75 %" that the current §11.1 no
  longer contains — fix or remove; (b) `todo/README.md` pinned HEAD/ahead stale.
  **Handle:** `tnnls_submission/SUBMISSION_READINESS.md`; `todo/README.md`.

### GAP-20 — Cover-letter placeholders
- **Owner:** user. **Action:** fill the 17 `[USER TO FILL]` fields at submission
  time. **Handle:** `tnnls_submission/FILL_GUIDE.md`.

---

## 6. Gate chain (run after every fix)

| Gate | Command |
|---|---|
| readiness verifier | `python tools/verify_submission_readiness.py` |
| claims consistency | `python tools/check_claims_consistency.py` |
| docs-against-code | `python tools/check_docs_against_code.py` |
| D.4 byte-stable | `python -m pytest tests/test_d4_regression_vectors.py tests/test_adapters/test_regression_vectors.py -q` |
| ruff | `ruff check adaptive_reflow/ tests/ scripts/ tools/` |
| mkdocs strict | `mkdocs build --strict` |

## 7. Cross-references

- `tnnls_submission/SUBMISSION_READINESS.md` — 14 PASS / 6 PENDING submission state.
- `docs/audit/wave364-paper-polish-gaps.md` — the 31 deferred gaps.
- `docs/audit/wave357-r6-gpu-scope.md` — R6 live-GPU scope.
- `docs/audit/wave351-r3-vendor-fix-status.md` — R3 RDKit blocker.
- `docs/audit/wave280-p-r1-sweep-result.md` — R1 contamination evidence.
- `docs/CLAIMS.md` — CLM-059 / 060 / 068 / 070 / 073.
- `todo/RISK-REGISTER.md` — R-019 (venue switch) / R-022 (deep-audit cluster).
- `todo/WAVES.md` §8 — deferred / out-of-scope summary.

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

## 1.5 Verification pass (2026-10-12, post-checklist)

A verification pass against the **live manuscript** (`docs/drafts/paper-A-final.md`)
found that most of the *framing/honesty* items below were **already handled** — the
earlier assessment over-relied on aggregate surfaces (`docs/RELEASE-NOTES.md`,
`todo/WAVES.md`, `tnnls_submission/SUBMISSION_READINESS.md`) rather than the
manuscript itself. Corrected status:

| ID | Corrected status | Evidence (live manuscript) |
|---|---|---|
| GAP-05 | **VERIFIED — already handled** | §7.2 R5c row reads "STRONG (smoke ckpt) / REGIME-DEPENDENT"; §7.9 conditions it |
| GAP-06 | **VERIFIED — already handled** | §1(v) + §7.2 + §11.1 all qualify each STRONG cell ("R2, conditional R5b, smoke-checkpoint R5c, counterfactual R6") |
| GAP-07 | **VERIFIED — already handled** | §1 + §7.7 disclose the 2.5–10× range as an extrapolation; §11.1 states the measured Tier-1 speedup is 1.0× |
| GAP-08 | **VERIFIED — already handled** | §7.2 R2 row carries a full honest disclosure (synthetic input coords, framework-internal RMSD) |
| GAP-10 | **VERIFIED — already handled** | §11.1: the residual-correction explanation is "a hypothesis ... not a consequence of Theorems 4–5" |
| GAP-11 | **NARROWED (minor)** | the manuscript does not headline a pooled `d_z`/I²; only the bibliography references the meta-analysis methodology |
| GAP-13 | **VERIFIED — already disclosed** | no Lean/formal claim in the manuscript; `submission_checklist.md` row 12 marks it `PENDING (PENDING_MATHLIB_CACHE)` |

Two **new, real** defects were found by the same pass and are added below as
**GAP-21** (a manuscript test-citation cluster). GAP-18 is expanded accordingly.

## 2. Scoreboard

| ID | Priority | Owner | Status | One-line gap |
|---|---|---|---|---|
| GAP-01 | P0 | gpu | OPEN | R6: counterfactual-STRONG → live-GPU-STRONG |
| GAP-02 | P0 | gpu | OPEN | R3: N=1000 PROJECTED → ACTUAL |
| GAP-03 | P0 | gpu | OPEN | R1: single-seed → 3-seed |
| GAP-04 | P0 | gpu | OPEN | R5b: matched-protocol multi-seed round-count test |
| GAP-05 | P0 | agent | VERIFIED | R5c regime already stated conditionally |
| GAP-06 | P0 | agent | VERIFIED | headline already qualified per cell |
| GAP-07 | P0 | agent | VERIFIED | NFE extrapolation already disclosed |
| GAP-08 | P0 | agent | VERIFIED | R2 scope already disclosed |
| GAP-09 | P1 | agent(+gpu) | OPEN | Theory: testable criterion for `q<1` / blend benefit |
| GAP-10 | P1 | agent | VERIFIED | mechanism already scoped as a hypothesis |
| GAP-11 | P1 | agent | NARROWED | bibliography meta-analysis cross-ref (minor) |
| GAP-12 | P1 | agent(+gpu) | OPEN | Baseline fairness: matched-NFE + tuned baseline |
| GAP-13 | P1 | agent/user | VERIFIED | Lean claim already marked PENDING |
| GAP-14 | P1 | agent | **RESOLVED** (2026-10-12) | §2.1 novelty-differentiation paragraph added (.md + .tex; PDF rebuilt) |
| GAP-15 | P1 | user | OPEN | Venue-fit decision (TNNLS vs reposition) |
| GAP-16 | P2 | agent | **RESOLVED** (2026-10-12) | 31 deferred gaps triaged; 31 explicit acceptances recorded |
| GAP-17 | P2 | gpu | OPEN | K2/K6 env-blocked per-cell sweeps |
| GAP-18 | P2 | agent | **RESOLVED** (2026-10-12) | Dead links in the manuscript — repointed (§7.11 + §7.8.1) |
| GAP-19 | P2 | agent | **RESOLVED** (2026-10-12) | Q1-odds removed from submission docs — aligned with the manuscript (Wave 370 removal) |
| GAP-20 | P2 | user | OPEN | 17 `[USER TO FILL]` cover-letter placeholders |
| GAP-21 | **P0** | agent | **RESOLVED** (2026-10-12) | Manuscript test citations repointed to real files + measured counts |
| GAP-22 | P1 | agent/user | OPEN | R2/R1 STRONG-label rubric inconsistency (R2 STRONG at d=0.099 vs R1 PARTIAL at 0.182) |

---

## 3. P0 — load-bearing

> **Note (2026-10-12 verification pass):** GAP-05 / GAP-06 / GAP-07 / GAP-08 are
> **already handled** in the live manuscript (see §1.5). They are retained below
> for the record; no edit is needed.

### GAP-21 — Manuscript cites test files that never existed (NEW, P0)
- **Owner:** agent.
- **Finding:** §3.4–§3.7 of `docs/drafts/paper-A-final.md` cite ~10 test files
  with parenthetical pass counts (e.g. `tests/test_protocol_conformance.py`
  "80/80 PASS", `tests/test_condition_auto_wrap.py` "40/40 PASS",
  `tests/test_capability_handshake.py` "50/50 PASS",
  `tests/test_state_machine_byte_deterministic.py` "60/60 PASS",
  `tests/test_ledger_chain.py` "50/50 PASS", …). **None of these paths ever
  existed in git history** (`git log --all -- <path>` → empty) and none exist on
  disk, so every such link 404s and every pass count is unverifiable.
- **Already known:** `docs/audit/wave352-framework-code-anchors.md` §2.1 item 1
  documented this as "pre-existing paper drift … out of scope"; it was never fixed.
- **Blocker:** the real files do not correspond 1:1 to the cited names (e.g.
  `test_ledger_chain.py` → `tests/test_frame/test_ledger_chain.py`;
  `test_protocol_conformance.py` → `tests/test_universal/test_adapter_protocol_conformance.py`;
  `test_condition_auto_wrap.py` → `tests/test_universal/test_condition_typed.py`),
  and the cited pass counts do not match the real files' test counts.
- **Action (needs a decision):** repoint each citation to the real file **and**
  either (a) replace the pass count with the real measured count, or (b) drop the
  parenthetical count and point at the test suite / audit trail.
- **Handle:** `docs/drafts/paper-A-final.md` §3.4–§3.7;
  `docs/audit/wave352-framework-code-anchors.md` §2.1.
- **Acceptance:** every cited test path resolves; no unverifiable pass count remains.
  *(Editing the manuscript triggers the rebuild + SHA-ledger loop.)*

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

### GAP-14 — Novelty boundary vs prior training-free methods — **RESOLVED** (2026-10-12)
- **Owner:** agent.
- **Action:** add an explicit differentiation paragraph against DPM-Solver++,
  UniPC, consistency models, Fast-DLLM, and LeDiFlow.
- **Resolution.** §2.1 of `paper-A-final.md` (and `paper-A-final.tex`) gains an
  explicit "differentiation from adjacent mechanisms" paragraph: predictor–corrector
  samplers (UniPC [5] / EDM [4] / DPM-Solver++ [3]) act within one trajectory with no
  cross-round feedback; trajectory-level distillation (Consistency Models [8] /
  LCM-LoRA [9]) changes $v_\theta$; re-inference α-blending (Sabour et al. 2024 /
  Fast-DLLM [6] / AB-Cache / LeDiFlow [7]) uses a hand-set β (discrete-token caching
  for Fast-DLLM; a learned prior-shift for LeDiFlow). FlowA is distinguished on three
  axes at once (frozen field; outcome-conditioned initial-condition blend; convergence
  analysis of the composite map). Additive; no metric/number/verdict change. PDF
  rebuilt (still 11 pages). Audit: `docs/audit/gap14-novelty-differentiation.md`.
- **Handle:** §1; §2 related work (now §2.1).
- **Acceptance:** the "re-inference / restart blend" contribution is clearly
  distinct from existing restart / predictor-corrector / training-free acceleration.

### GAP-15 — Venue-fit decision
- **Owner:** user.
- **Action:** confirm TNNLS vs repositioning to a systems/ML-applications venue;
  align the positioning accordingly.
- **Handle:** `todo/RISK-REGISTER.md` R-019.
- **Acceptance:** venue decided; abstract/intro positioning matches it.

### GAP-22 — R2/R1 STRONG-label rubric inconsistency (NEW 2026-10-12, from a live-manuscript read)
- **Owner:** agent (the fix *path* is user-gated). **Priority:** P1 (borderline P0 — a reviewer-visible internal contradiction in the headline).
- **Finding.** The manuscript states a `|d| = 0.8` "STRONG-promotion bar" (§7.1 figure caption) and applies it to demote **R1** (`d_z = +0.182 < 0.8 → PARTIAL`, §7.2 R1 row). But **R2** is labelled **STRONG** with `d_z = -0.0990` (§7.2 R2 row) — an order of magnitude *below* the bar, and below R1's own effect. The same rubric yields opposite labels. The tension is three-layered:
  (a) manuscript §7.2 — R2 STRONG at `|d_z| = 0.099` vs R1 PARTIAL at `0.182`;
  (b) `docs/CLAIMS.md` CLM-063 (Wave 196 P4, R2 REGRESSES → SUPPORTED) rests on paired-t significance at N=1000 (`p_raw = 0.00257`, **Cohen's `d_z = +0.096`**) — i.e. significance, not effect size;
  (c) CLM-063's own aggregate artifact `verification_outputs/wave196-p4-table-a-r-level.json` records **R2 verdict = UNDERPOWERED**, and CLM-060 (Wave 195 P2) recorded R2 = **REGRESSES** — so the claims ledger has carried REGRESSES / UNDERPOWERED / SUPPORTED / STRONG for the same cell at different times.
- **Why it matters.** A reviewer who reads §7.1 + §7.2 will ask "why is R2 STRONG at `|d| = 0.099` when R1 is demoted at `0.182`?" — and the answer is not in the manuscript.
- **Fix options (user decision):**
  - **(A) Additive rubric disclosure — strict-clean, recommended.** Add an ADDITIVE footnote to §7.2 (and one sentence to §7.1) stating that STRONG = Bonferroni-significant at the pre-registered α, *not* a large-effect threshold, and disclosing R2's `|d_z| = 0.099` + the CLM-063 UNDERPOWERED artifact. No label change; preserves Wave 268 strict-clean + the submission freeze.
  - **(B) Add an effect-size floor to the rubric and re-label R2.** Demote R2 to PARTIAL/small-effect (headline → 3 STRONG + 1 TIE + 7 PARTIAL/SUPP). Most internally consistent, but changes a headline count — needs a user decision (and either a new measurement or an explicit override of the freeze).
  - **(C) State the rubric only.** Minimal: document the criterion without disclosing R2's specific tension.
- **Handle:** `docs/drafts/paper-A-final.md` §7.1 + §7.2 (R2 / R1 rows); `docs/CLAIMS.md` CLM-060 / CLM-063.
- **Acceptance:** a reader can answer "why R2 STRONG, R1 PARTIAL" from the manuscript alone.

---

## 5. P2 — polish / hygiene

### GAP-16 — 31 deferred reviewer-facing gaps — **RESOLVED** (2026-10-12)
- **Owner:** agent. **Action:** triage the list; close the low-impact ones or
  record explicit acceptance. **Handle:** `docs/audit/wave364-paper-polish-gaps.md`
  §5.
- **Resolution.** All 31 deferred gaps (user-gated {G2}; env-blocked {G8, G9, G23};
  out-of-scope {G4/G7, G5/G10, G6, G12, G14, G19, G22, G24}; low-impact {16};
  plus the unlisted G13) are **ACCEPTED-DEFERRED** with category-level reasons and
  mapped to this checklist where a mapping is clear. **Observed fact:** the Wave 364
  39-gap inventory's *per-gap descriptions* are not persisted anywhere in the repo
  (only IDs + categories survive in `wave364 §5`), so a per-gap close-out is not
  possible without re-deriving the inventory; the explicit-acceptance path is
  therefore taken. This checklist supersedes the Wave 364 inventory as the operative
  gap list. Audit: `docs/audit/gap16-deferred-triage.md`.

### GAP-17 — K2/K6 env-blocked per-cell sweeps
- **Owner:** gpu. **Action:** pin the env and sweep, or retain the honest
  disclosure. **Handle:** `tnnls_submission/SUBMISSION_READINESS.md` PENDING #5.

### GAP-18 — Dead links in the manuscript
- **Owner:** agent. **Action:** a systematic sweep of the manuscript's
  `github.com/.../blob|tree/main/<path>` links found **15 missing paths** (73
  distinct linked paths checked). Two are audit-doc links
  (`docs/audit/wave280-p-framework-fallback-contamination.md` at §7.11 line 568 →
  canonical `docs/audit/wave280-p-r1-sweep-result.md`; `docs/audit/wave183-p4-aggregate.md`
  → the real artifact is `verification_outputs/wave183-p4-aggregate.py`), ~10 are
  the test-citation cluster (**GAP-21**), and 3 are `data/` directory links
  (`data/cifar/`, `data/kanzi/upstream/`, `data/flowmol3/repo/`) that resolve on a
  full vendored checkout but not in this tree.
- **Handle:** `docs/drafts/paper-A-final.md`; the sweep script (ad-hoc `re` over
  `blob|tree/main/<path>` URLs).
- **Acceptance:** every audit-doc link resolves; `data/` links either resolve or
  are scoped as checkout-dependent.

### GAP-19 — Stale Q1-odds citations (submission docs) — **RESOLVED** (2026-10-12)
- **Owner:** agent. **Finding:** the §11.1 "Q1 acceptance-probability 60-75 %"
  disclosure was **deliberately removed at Wave 370** (`62154e0`, a user-authorized
  destructive rewrite; `git log -S "60-75"` confirms). Yet three submission-facing
  surfaces still cite it:
  (a) `tnnls_submission/MANIFEST.md` row 56's provenance text ("Wave 354 P3 ADDITIVE:
  §1 abstract + §11.1 … Q1 acceptance 60-75 % disclosure");
  (b) `tnnls_submission/SUBMISSION_READINESS.md` §5 + §1 ("§11.1 … 60-75 %");
  (c) `tnnls_submission/submission_checklist.md:87` ("50-65 %", contradicting the
  other two).
- **Resolution (user decision "移除，与手稿对齐").** Removed the self-assessed
  acceptance probability from the submission docs so they align with the manuscript:
  §5 of `SUBMISSION_READINESS.md` retitled "Venue fit — no self-assessed acceptance
  probability" (numeric estimate stripped; strengths/risk factors retained
  qualitatively; line-14 / §7-table / §7-JSON / §8.3 / §9 references removed; new §19
  addendum records the in-place edit); `submission_checklist.md` section retitled
  "Reviewer-facing strengths" with the "50-65 %" line removed; `MANIFEST.md` row 56
  gains an additive Wave 370-removal note + row 54 SHA refresh + row 47 self-SHA
  update. No metric/claim number changed.
- **Handle:** `tnnls_submission/MANIFEST.md`; `tnnls_submission/SUBMISSION_READINESS.md`;
  `tnnls_submission/submission_checklist.md`. Audit: `docs/audit/gap19-q1-odds-alignment.md`.

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

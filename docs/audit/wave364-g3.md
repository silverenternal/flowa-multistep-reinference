# Wave 364 PG3 — Theorem 5 33× slope over-prediction wording ADDITIVE close

**Date:** 2026-09-27
**Author:** Wave 364 P G3 (paper-evidence agent — ADDITIVE only)
**Scope:** `docs/drafts/paper-A-final.md` §6.6.1 (ADDITIVE addendum appended immediately after the existing Wave 351 §6.6.1 numerical-validation footnote, before §6.7 Framework Properties) — closes open-revision-item **G3** (Theorem 5 ~33× slope over-prediction wording).
**Purpose:** Disambiguate the slope-scaling-disclosure wording by introducing the mathematically standard term **"loose upper bound"** (in a NEW ADDITIVE addendum) for the ~33× over-prediction at high `n_rounds`, and surface the load-bearing proven-claim/scope-of-applicability separation: the discrete `k = 1 → k ≥ 2` transition is the proven claim (Sub-claim 5.1, Lipschitz-agnostic), while the asymptotic slope scaling in Eq.\,(6) is not (over-predicts by ~33×, requires per-adapter calibration for quantitative `k^*`). Preserves every number, label, Eq.\,(6), Sub-claims 5.1–5.4, and the §6.6.1 Wave 351 footnote verbatim (no number change, no label change, no theorem-statement change).

---

## 1. Executive Summary

| Item                              | Value                                                                                                                                                                                                                |
|-----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| File modified                     | `docs/drafts/paper-A-final.md`                                                                                                                                                                                        |
| Modification type                 | **ADDITIVE only** (1 italic-paragraph addendum + 1 blank line, **0 lines of existing prose modified**)                                                                                                                |
| Insertion location                | §6.6.1 (line 509 of the un-modified Wave 351 version), immediately after the existing Wave 351 ADDITIVE numerical-validation footnote (which ends "...this §6.6.1 footnote is ADDITIVE.") and before `### 6.7 Framework Properties as primary contribution` |
| Addendum language (verbatim)      | New italic paragraph beginning "*Wave 364 PG3 ADDITIVE addendum, no number change — gap G3 close-out (terminology + proven-claim clarification).*" containing: (a) **"loose upper bound"** as the mathematically standard disambiguating term for the ~33× over-prediction; (b) **proven-claim clarification:** "the discrete `k = 1 → k ≥ 2` transition is the proven claim; the asymptotic slope is not" (delivered as the explicit proven-claim/scope-of-applicability separation stated in the addendum text) |
| Theorem 5 statement               | **Preserved verbatim** — no change to "Theorem 5 (restart-blend attenuation bound)" or its boxed Eq.\,(6) or Sub-claims 5.1–5.4                                                                                      |
| §6.6.1 Wave 351 footnote          | **Preserved verbatim** — including the existing word "conservative" (not renamed; the Wave 351 footnote is preserved as-is per the ADDITIVE-only constraint, and the new addendum provides the disambiguating "loose upper bound" terminology in NEW prose)                                                                                |
| Numbers preserved                 | All numbers preserved verbatim: `(k=20 vs k=2)` `|VA|` ratio `19 · sqrt(10) ≈ 60.08`; empirical ratio `0.3065 / 0.1662 ≈ 1.844`; ~33× over-prediction at high `n_rounds`; `L_local ≈ 0.3810`; `eps_theta ≈ 0.0506`; `sigma_blend ≈ 0.0596` to `0.2920`; `m = 0.5` canonical; the §6.6.1 "matches_empirical" transition prediction |
| Proven-claim clarification        | Explicitly stated: "the discrete `k = 1 → k ≥ 2` transition (Sub-claim 5.1, Lipschitz-agnostic) is the proven claim — it holds for any finite `L_local > 0` with $\varepsilon_\theta / \sigma_\text{blend} > 0$ — while the asymptotic $(k-1) \cdot \sqrt{k / L_\text{local}}$ slope scaling in Eq.\,(6) is not" |
| Gap closed                        | **G3** — Theorem 5 33× slope over-prediction wording (terminology refinement + proven-claim clarification)                                                                                                              |
| Verification gates                | `pytest tests/test_d4_regression_vectors.py -q` → **30/30 PASS**; `python3 tools/check_claims_consistency.py` → "**No drift detected.**" (61 active / 0 provisional / 2 deprecated); `mkdocs build --strict` → **EXIT 0 PASS** (built in 24.16 s) |
| Hard guardrails                   | NO-PUSH (only `git commit` performed, no `git push`); ADDITIVE only (`git diff --stat` confirms `+2` lines, `-0` lines on the modified file); Theorem 5 statement UNCHANGED; 17 USER_TO_FILL placeholders in cover letter UNCHANGED; vendored 9 repos UNCHANGED |

---

## 2. Observed Facts

### 2.1 File modified (single, ADDITIVE)

```
$ git diff --stat docs/drafts/paper-A-final.md
 docs/drafts/paper-A-final.md | 4 ++++
 1 file changed, 4 insertions(+), 0 deletions(-)
```

(The +4 stat includes both this PG3 addendum (+2 lines at line 519) and the previously-committed Wave 364 PG20 lemma-numbering reconciliation addendum (+2 lines at line 370). The PG3-only contribution is **+2 / -0** — one italic-paragraph addendum + one blank separator line.)

| Property                | Observed Value                                                                                                                                                                  |
|-------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Path                    | `docs/drafts/paper-A-final.md`                                                                                                                                                   |
| Diff size (PG3-only)    | **+2 lines / -0 lines** (one new italic paragraph + one blank separator line, both ADDITIVE)                                                                                    |
| No existing prose touched | Verified by `git diff -U0` — only `+` lines at hunk `@@ -516,0 +519,2 @@` (the §6.6.1 area); no `-` deletions on the modified file. The existing §6.6.1 Wave 351 numerical-validation footnote (the long paragraph ending "...this §6.6.1 footnote is ADDITIVE.") is character-identical pre-edit and post-edit, including the in-footnote word "conservative". |
| Insertion anchor        | Immediately after `"...this §6.6.1 footnote is ADDITIVE."` (the trailing period of the Wave 351 §6.6.1 footnote) and before `"### 6.7 Framework Properties as primary contribution"` (line 511 in the un-modified file) |
| Wave 268 strict-clean   | Preserved — no number change, no label change, no status change, no Eq.\,(6) mutation, no Theorem 5 statement mutation; the addendum is purely clarifying wording              |

### 2.2 ADDITIVE-only verification (git diff for the §6.6.1 insertion hunk)

```diff
@@ -516,0 +519,2 @@ Theorem 4's $\tau_\text{residual}$ term governs the rate at which the **correcte
+*Wave 364 PG3 ADDITIVE addendum, no number change — gap G3 close-out (terminology + proven-claim clarification).* Addressing the §6.6.1 slope-scaling disclosure above: the ~33× asymptotic over-prediction at high `n_rounds` is more precisely characterised as a **loose upper bound** — the bound holds but is not tight at the relevant parameter range, which is the mathematically standard reading (a "loose upper bound" holds for all parameter values in the regime but does not track the empirical magnitude; a "conservative" bound is reserved in the framework's paper-quantity glossary for one-sided hypothesis-test style bounds such as TOST/JT/BF01, where the bound trades tightness for a one-sided guarantee, so "loose upper bound" is the disambiguating term here). The qualitative reading of the Wave 351 footnote is unchanged. **Proven-claim clarification (the load-bearing item):** the discrete `k = 1 → k ≥ 2` transition (Sub-claim 5.1, Lipschitz-agnostic) is the proven claim — it holds for any finite `L_local > 0` with $\varepsilon_\theta / \sigma_\text{blend} > 0$ — while the asymptotic $(k-1) \cdot \sqrt{k / L_\text{local}}$ slope scaling in Eq.\,(6) is not; the bound over-predicts the empirical `|VA|` ratio by ~33× at `k = 20 vs k = 2`, and per-adapter calibration is required for any quantitative `k^*` reading (see §10.9 partial close-out footnote + Sub-claim 5.3 $m$-upper-bound regime for the engineering follow-up scope). **No number change in §6.6 or §6.6.1** — Eq.\,(6), Sub-claims 5.1–5.4, the §6.6.1 numerical-validation footnote, and Theorem 5 statement are all preserved verbatim; this addendum is purely clarifying wording (terminology refinement + proven-claim/scope-of-applicability separation) and is preserved as additive per the Wave 268 strict-clean principle.
+
```

Lines added by PG3: **2** (1 italic-paragraph addendum + 1 blank separator line). Lines modified by PG3: **0**. The Wave 351 §6.6.1 numerical-validation footnote (including the word "conservative") is preserved verbatim — the new "loose upper bound" terminology appears only in the new addendum, not as a rename of any existing prose.

### 2.3 Verification gates (all PASS)

| Gate                                        | Result                                                                                                                                       |
|---------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| D.4 byte-stable regression suite            | `python3 -m pytest tests/test_d4_regression_vectors.py -q` → `30 passed, 3 warnings in 7.88s`                                               |
| Claims consistency                          | `python3 tools/check_claims_consistency.py` → "**No drift detected.**" (61 active, 0 provisional, 2 deprecated)                              |
| Ruff lint (scope dirs)                      | `ruff check docs/ tools/ adaptive_reflow/ tests/` → 11 pre-existing findings (5 in `docs/build_pdf/md_to_tex.py` import-sorting, 6 elsewhere); **0 new findings introduced by PG3** (the modified file is markdown — no Python lint required); verified by stash-restore comparison that the 11 pre-existing findings exist on the pre-PG3 commit as well, so PG3 introduces no new ruff findings |
| MkDocs strict build                         | `mkdocs build --strict` → **EXIT 0 PASS** ("Documentation built in 24.16 seconds"; the MkDocs 2.0 backward-incompatibility warning is informational and unrelated to this change) |

### 2.4 Files NOT modified (preserved verbatim)

- `docs/drafts/paper-A-final.md` §6.6 Theorem 5 statement + boxed Eq.\,(6) + Sub-claims 5.1, 5.2, 5.3, 5.4 — all preserved verbatim. The PG3 addendum explicitly states "Theorem 5 statement is preserved verbatim" so the theorem-statement constraint from the gap-fix rule is honoured.
- `docs/drafts/paper-A-final.md` §6.6.1 Wave 351 numerical-validation footnote (including the in-footnote word "conservative") — preserved verbatim (the new addendum is appended AFTER it, not in place of it).
- `docs/drafts/paper-A-final.md` §3.1–§6.5 and §6.7 onward — preserved verbatim (PG3 only touches the §6.6.1 area).
- `tnnls_submission/MANIFEST.md` — unchanged (no SHA-256 regeneration needed because the PG3 addendum does not appear in any `tnnls_submission/` file; the PG3 addendum is in `docs/drafts/paper-A-final.md` only).
- `tnnls_submission/cover_letter.md` — unchanged (G32 cover_letter.md §0 date modification is out of scope for G3 and is gated separately per the gap-split).
- 17 USER_TO_FILL placeholders in `tnnls_submission/cover_letter.md` — preserved verbatim (G3 does not touch cover_letter.md).
- All 9 vendored upstream repos under `data/` — preserved byte-identical to upstream commit hashes per the hard guardrail §3.1 of AGENTS.md.
- `docs/CLAIMS.md` — unchanged (no claim status change; no wording change; no number change).
- `docs/CONSOLIDATED_RESULTS.md` — unchanged.
- `docs/INSIGHTS.md` — unchanged.

### 2.5 Proven-claim clarification surfaced verbatim

The addendum's load-bearing sentence (delivered verbatim to satisfy the gap-fix rule "Append a one-sentence clarification"):

> **Proven-claim clarification (the load-bearing item):** the discrete `k = 1 → k ≥ 2` transition (Sub-claim 5.1, Lipschitz-agnostic) is the proven claim — it holds for any finite `L_local > 0` with $\varepsilon_\theta / \sigma_\text{blend} > 0$ — while the asymptotic $(k-1) \cdot \sqrt{k / L_\text{local}}$ slope scaling in Eq.\,(6) is not; the bound over-predicts the empirical `|VA|` ratio by ~33× at `k = 20 vs k = 2`, and per-adapter calibration is required for any quantitative `k^*` reading (see §10.9 partial close-out footnote + Sub-claim 5.3 $m$-upper-bound regime for the engineering follow-up scope).

This sentence pairs: (i) the proven-claim identification (the discrete `k = 1 → k ≥ 2` transition via Sub-claim 5.1 Lipschitz-agnostic variant) with (ii) the non-proven-scope identification (the asymptotic $(k-1) \cdot \sqrt{k / L_\text{local}}$ slope in Eq.\,(6), which over-predicts and requires per-adapter calibration). The pairing satisfies the gap-fix rule "the discrete `k = 1 → k ≥ 2` transition is the proven claim; the asymptotic slope is not" exactly.

---

## 3. Interpretation (why this closes G3)

Gap **G3** is the wording-precision gap on the §6.6.1 numerical-validation footnote: a reviewer reading the existing Wave 351 footnote sees the bound "over-predicts the asymptotic regression magnitude by ~33x at high `n_rounds`" and the categorical label "the asymptotic scaling is conservative", but does not have:

1. The **mathematically standard disambiguating term** ("loose upper bound") for a bound that holds but does not track the empirical magnitude in the relevant parameter range (the framework's paper-quantity glossary reserves "conservative" for one-sided hypothesis-test style bounds such as TOST/JT/BF01).
2. The **explicit proven-claim vs scope-of-applicability separation** — the Wave 351 footnote observes that "the discrete transition is exact" and "the asymptotic scaling is conservative", but does not explicitly label the discrete transition as the proven claim and the asymptotic slope as outside the proven scope (the proven/scope separation is implicit in Sub-claim 5.1 + the Wave 351 footnote, but the gap-fix rule explicitly requires it inline alongside the §6.6.1 footnote).

The PG3 addendum closes both items in a single italic-paragraph addendum appended after the Wave 351 footnote:

- **Item (1) — Terminology refinement:** the addendum introduces "loose upper bound" as the disambiguating term (the new term appears only in the new addendum; the Wave 351 footnote's word "conservative" is preserved verbatim per the ADDITIVE-only constraint, so there is no rename of existing prose). The addendum's parenthetical clarifies the distinction: "a 'loose upper bound' holds for all parameter values in the regime but does not track the empirical magnitude; a 'conservative' bound is reserved in the framework's paper-quantity glossary for one-sided hypothesis-test style bounds such as TOST/JT/BF01, where the bound trades tightness for a one-sided guarantee, so 'loose upper bound' is the disambiguating term here". The parenthetical makes the disambiguation auditable and verifiable against the framework's paper-quantity glossary.
- **Item (2) — Proven-claim clarification:** the addendum's load-bearing sentence explicitly labels "the discrete `k = 1 → k ≥ 2` transition (Sub-claim 5.1, Lipschitz-agnostic)" as the proven claim and "the asymptotic $(k-1) \cdot \sqrt{k / L_\text{local}}$ slope scaling in Eq.\,(6)" as outside the proven scope (over-predicts by ~33× at `k = 20 vs k = 2`, requires per-adapter calibration). The two sentences pair the proven claim identification with the non-proven-scope identification, so a reviewer reading the addendum immediately sees the boundary of what Theorem 5 proves.

The PG3 addendum does NOT modify Theorem 5 statement, Eq.\,(6), or any Sub-claim (5.1, 5.2, 5.3, 5.4) — the addendum explicitly states "Theorem 5 statement is preserved verbatim" and "Eq.\,(6), Sub-claims 5.1–5.4, the §6.6.1 numerical-validation footnote... are all preserved verbatim" — so the gap-fix rule "Do not modify the Theorem 5 statement itself" is honoured. The addendum is purely clarifying wording appended to the §6.6.1 numerical-validation footnote area, satisfying the Wave 268 strict-clean principle ("ADDITIVE blocks may add new content but must not modify, promote, or remove existing content").

---

## 4. Unresolved gaps (out of scope for G3, preserved for downstream)

- **G32 (cover letter §0 date modification)**: out of scope for G3; user-gated per the gap-split. G32 only modifies `tnnls_submission/cover_letter.md` §0 date and **never** touches the 17 USER_TO_FILL placeholders.
- **G11 / G20 / G31 / G34 (other Wave 364 gaps)**: not addressed by this wave; G3 is the Theorem 5 33× slope over-prediction wording gap and is closed by the §6.6.1 PG3 addendum alone.
- **R3 N=1000 paired full-stack re-verification**: still deferred per §10.5 / §11.1 (b) (camera-ready scope).
- **R6 live-GPU 3-seed × N=1000 paired full-stack re-verification**: still deferred per §10.5 / §11.1 (b) (camera-ready scope).
- **§10.9 future-work item partial close-out** (engineering follow-ups): the PG3 addendum references the §10.9 partial close-out footnote and Sub-claim 5.3 $m$-upper-bound regime for the engineering follow-up scope, but does not advance those engineering items; per-adapter Lipschitz diagnostic at construction time + §7.8 R5c regime-curve extension as a function of velocity field fidelity + cross-adapter regime curves on R5b CIFAR-10 RF remain engineering and analysis follow-ups.

---

## 5. Hard guardrails (verified)

1. **NO-PUSH policy** (§3.3 of AGENTS.md): commit is local; no `git push` invoked.
2. **ADDITIVE only** (§3.2 of AGENTS.md + gap-fix rule "ADDITIVE only (never modify existing prose)" + Wave 268 strict-clean principle): 2 lines added to paper-A-final.md (PG3-only contribution), 0 lines modified (verified by `git diff -U0`); the Wave 351 §6.6.1 footnote (including the word "conservative") is preserved verbatim; the Theorem 5 statement, Eq.\,(6), and Sub-claims 5.1–5.4 are preserved verbatim; the new addendum is appended after the Wave 351 footnote, before §6.7 Framework Properties.
3. **Vendored upstream sacred** (§3.1 of AGENTS.md): all 9 vendored repos under `data/` are byte-identical to upstream commit hashes; the G3 fix touches only `docs/drafts/paper-A-final.md` and the NEW `docs/audit/wave364-g3.md`.
4. **Honest uncertainty** (§3.4 of AGENTS.md): the PG3 addendum does NOT promote `UNDERPOWERED` / `DEFERRED` / `REGRESSES` / `NOT_SIGNIFICANT` to `SUPPORTED` by wording alone; the addendum explicitly distinguishes the proven claim (discrete transition) from the non-proven scope (asymptotic slope) — this is the opposite of status promotion, it is scope-of-applicability clarification.
5. **TNNLS submission freeze sacred** (§3.5 of AGENTS.md): zero edits to `tnnls_submission/`; no SHA-256 regeneration needed (the G3 fix is exclusively on `docs/drafts/paper-A-final.md` and the NEW `docs/audit/wave364-g3.md`).
6. **17 USER_TO_FILL preserved** (gap-split rule): zero edits to `tnnls_submission/cover_letter.md`; the 17 placeholders (3 + 11 + 3) are preserved verbatim.
7. **Theorem 5 statement not modified** (gap-fix rule "Do not modify the Theorem 5 statement itself"): the addendum explicitly states "Theorem 5 statement is preserved verbatim"; the boxed Eq.\,(6) and Sub-claims 5.1–5.4 are also preserved verbatim.
8. **Stricter = cleaner** (§3.7 of AGENTS.md, Wave 268 directive): the PG3 addendum is a single italic-paragraph addendum + one blank separator line; no other file touched except the NEW audit doc; the change is the smallest possible ADDITIVE closure for G3.

---

## 6. Commits

- `Wave 364 PG3: docs/drafts/paper-A-final.md — Theorem 5 33× slope over-prediction wording ADDITIVE close (USER AUTHORIZED, NO PUSH)` — ADDITIVE only; 2 lines appended after the Wave 351 §6.6.1 numerical-validation footnote (PG3-only contribution; the +4 `git diff --stat` includes the previously-committed Wave 364 PG20 lemma-numbering reconciliation addendum at line 370). Theorem 5 statement, Eq.\,(6), Sub-claims 5.1–5.4, and the Wave 351 §6.6.1 footnote all preserved verbatim.

---

_Last updated: 2026-09-27 (Wave 364 G3 — Theorem 5 33× slope over-prediction wording ADDITIVE close)._

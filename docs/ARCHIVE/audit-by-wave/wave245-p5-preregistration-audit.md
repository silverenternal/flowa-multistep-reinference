# Wave 245 P5 — Wave 234 statistical methods pre-registration audit

**Date (UTC):** 2026-09-22
**Auditor:** Wave 245 P5 (pre-registration audit agent)
**Scope:** Audit whether the three Wave 234 statistical-methods
parameters were pre-registered (declared before data inspection)
or post-hoc (chosen during analysis):

| ID | Value | Script |
|----|-------|--------|
| D1 | TOST equivalence margin = 0.1 SD (Cohen small effect boundary) | `scripts/wave234_p2_tost.py` |
| D2 | BF01 BIC approximation prior (Wagenmakers 2007, eq. 12) | `scripts/wave234_p4_bf01.py` |
| D3 | JT ordered-hypothesis H1: hard > medium > easy | `scripts/wave234_p3_jonckheere.py` |

## Audit method

For each parameter we searched for:

1. **Module-level declaration + timestamp** — values declared
   at the top of a script (or in a config file) **before** the
   analysis function runs, AND a documented registration
   timestamp (git commit / wave date / doc ID) **prior to**
   `wave230-p2-real-4arm-per-record.csv` (the per-cell summary
   stats consumed by all three Wave 234 scripts).
2. **Prior-wave pre-registration doc** — explicit
   pre-specification of the value in `docs/preregistration/`,
   `docs/audit/wave2XX-*.md` for `XX < 234`, or in an OSF
   pre-registration file (`docs/preregistration/r*-*.md`).
3. **`register()` style helper** — any function whose name
   suggests a registration / lock-in mechanism for the value.
4. **Hard-coded inside analysis function** — value embedded
   inside the `main()` or per-cell loop with no registration
   trail.

## Findings

### D1: TOST equivalence margin = 0.1 SD — **POST-HOC**

**Evidence:**

- Declared at module-level (line 41 of
  `scripts/wave234_p2_tost.py`):
  ```python
  MARGIN_FRACTION = 0.10  # 0.1 SD == small effect size (Cohen)
  ```
  This is **not** a `register()` call; it is a bare constant
  declared in the same script that performs the analysis. There
  is no prior registration artifact, no timestamp, no audit
  trail showing the value was locked before Wave 230 P2.
- Git log shows the script was first added in commit
  `edeb2ef` ("Wave 234 P2: TOST equivalence testing on 16 4-arm
  cells", 2026-09-21, AFTER Wave 230 P2 which is the source of
  the per-cell summary statistics).
- The `docs/audit/wave234-p2-tost.md` audit doc (lines 228-231)
  refers to 0.1 SD as the "conventional 'small effect'
  threshold" (Cohen 1988) — i.e. the value is justified
  post-hoc by appeal to a convention, not by pre-registration.
- The Wave 234 P2 docstring (line 13) also frames 0.1 SD as the
  *equivalence bound chosen for this analysis* ("equivalence
  bound = 0.1 SD = small effect"), not as a pre-registered
  threshold.
- No reference to 0.1 SD margin appears in any prior audit
  doc (Wave 230 / 231 / 232 / 233); the value is first
  introduced at Wave 234 P2.

**Verdict:** POST-HOC. The 0.1 SD margin is chosen by appeal
to Cohen (1988) small-effect convention *during* Wave 234 P2
script writing, after the per-cell summary statistics from
Wave 230 P2 are already on disk and inspected.

### D2: BF01 BIC-approximation prior — **POST-HOC**

**Evidence:**

- The Wagenmakers (2007) BIC approximation `BF01 = sqrt(n) *
  (1 + t^2/(n-1))^(-n/2)` is the ONLY Bayesian prior parameter
  used by Wave 234 P4 — no separate prior-shape parameter (no
  `prior_scale`, `prior_df`, `r_scale`, JZS prior, etc.) is
  passed by the caller.
- Module-level declarations in `scripts/wave234_p4_bf01.py`
  (lines 38-45):
  ```python
  EVIDENCE_BANDS = [
      (0.0, 1.0, "evidence for alternative (framework wins/loses)"),
      (1.0, 3.0, "anecdotal evidence for null"),
      (3.0, 10.0, "moderate evidence for null"),
      (10.0, 30.0, "strong evidence for null"),
      (30.0, 100.0, "very strong evidence for null"),
      (100.0, math.inf, "extreme evidence for null"),
  ]
  ```
  These are **decision thresholds**, not a prior. The implicit
  prior is the BIC unit-information prior
  (`p(t) ∝ 1` on the standardized effect size) which is
  *intrinsic to the BIC approximation*, not a user choice.
- First added in commit `558db5d` ("Wave 234 P4: BF01 Bayes
  factor on 16 4-arm cells", 2026-09-21). No prior-wave
  artifact mentions Wagenmakers BIC prior choice.
- The library implementation
  `adaptive_reflow/stats/equivalence.py::bf01_paired` accepts no
  prior parameter (the BIC approximation is hard-coded); so
  there is no `register()` mechanism in the library either.

**Verdict:** POST-HOC in the operational sense (no explicit
prior pre-registration), but the *implicit* prior (BIC
unit-information on standardized effect size) is a
well-defined Wagenmakers (2007) default — the audit-relevant
question is whether the **evidence thresholds** (3/10/30/100)
were pre-registered, and they were not.

### D3: JT ordered-hypothesis H1: hard > medium > easy — **POST-HOC**

**Evidence:**

- `scripts/wave234_p3_jonckheere.py` (lines 252-260) builds the
  three JT groups in the order `[easy, medium, hard]` to test
  the *increasing-trend* alternative `mean(easy) <= mean(medium)
  <= mean(hard)`. The hard > medium > easy ordering is **not**
  declared at module-level (no `JT_HYPOTHESES` constant, no
  `register()` call); it is hard-coded inside the
  `_jt_for_cell()` function with an inline comment explaining
  the direction.
- Crucially: **the monotone direction is taken FROM the Wave
  233 P3 already-observed per-tier paired t-test results** —
  not pre-registered. The script's docstring (lines 17-19)
  cites Wave 233 P3 per-tier p-values as the **motivation**:
  - R2 (Kanzi RMSD; lower=better): framework regresses on
    hard, UNDERPOWERED on medium, SUPPORTS on easy → monotone
    pattern hard > medium > easy in framework_minus_baseline
    SIGN.
  - R6 (k6 pLDDT; higher=better): framework SUPPORTS on hard,
    SUPPORTS on medium, REGRESSES on easy → same monotone
    pattern.
  The JT test is then run on the SAME per-record data that
  produced the observed monotone pattern.
- First added in commit `e4f6e39` ("Wave 234 P3: Jonckheere-
  Terpstra monotone trend test (R2 + R6)", 2026-09-21, AFTER
  Wave 233 P3).
- No prior-wave artifact specifies the ordered alternative.

**Verdict:** POST-HOC. The monotone ordering was chosen
*because the data already showed it*; the JT test is
confirmatory in the sense that it confirms the observed
pattern with greater power, but the *direction* of the
ordered alternative was NOT pre-registered before the per-tier
data were inspected.

## Summary table

| ID | Value | Status | Pre-registration evidence |
|----|-------|--------|---------------------------|
| D1 | TOST margin = 0.1 SD | **post-hoc** | None — script-level constant chosen during Wave 234 P2 |
| D2 | BF01 BIC prior + thresholds | **post-hoc** | None — implicit Wagenmakers (2007) BIC unit-information prior; threshold bands chosen during Wave 234 P4 |
| D3 | JT H1: hard > medium > easy | **post-hoc** | None — direction chosen from Wave 233 P3 already-observed monotone pattern |

## Cross-references

- OSF pre-registration for the *R1-R6 framework_improves*
  hypothesis family: `docs/preregistration/r1-r6-framework-improves.md`
  (Wave 165 P2, 2026-09-16). This pre-registers the R1-R6
  directional hypotheses, Bonferroni alpha, and minimum effect
  sizes — but does **not** pre-register any of D1 / D2 / D3.
- Cover-letter-tnnls.md §R5 (line 449) describes the Wave 234
  P2-P6 upgrade as "formal pre-registered statistical tests".
  This wording is **not accurate**: the R1-R6 framework_improves
  hypotheses were pre-registered (OSF); the five Wave 234
  methods (TOST / JT / BF01 / meta / NI) themselves were
  not pre-registered before the underlying data were
  inspected.

## Recommendation

1. **Disclose post-hoc status explicitly in the paper.** Add
   to `docs/drafts/methods-why-per-record.md` §MS.10.8 (or
   §2.8 of `docs/drafts/section-2-method.md`) a paragraph:
   "The TOST equivalence margin (0.1 SD), BF01 evidence
   thresholds (3/10/30/100 per Wagenmakers 2007), and JT
   ordered-hypothesis direction (hard > medium > easy) were
   chosen after inspection of the Wave 230 P2 per-cell
   summary statistics and the Wave 233 P3 per-tier paired
   t-test results respectively. None of the three were
   pre-registered in the Wave 165 P2 OSF pre-registration
   (`docs/preregistration/r1-r6-framework-improves.md`),
   which pre-registered only the R1-R6 directional framework
   improves hypotheses with Bonferroni alpha and minimum
   effect sizes. Pre-registration audit: `docs/audit/wave245-p5-
   preregistration-audit.md`."
2. **Soften the cover-letter wording.** Replace "formal
   pre-registered statistical tests" with "post-hoc
   methodologically-justified statistical upgrade" (or similar)
   to avoid overstating the pre-registration status.
3. **Future work.** Consider opening a Wave-245-or-later OSF
   pre-registration that locks the D1 / D2 / D3 values *before*
   the corresponding analyses are run, so the camera-ready
   paper can claim full pre-registration.

## Honesty note

This audit does **not** claim the Wave 234 statistical methods
are invalid — all three are well-established techniques with
appropriate citations (Schuirmann 1987 for TOST, Wagenmakers
2007 for BF01, Jonckheere 1954 / Terpstra 1952 for JT). It
**only** distinguishes between (a) methods chosen before data
inspection (pre-registered) and (b) methods chosen after
data inspection (post-hoc). Honest disclosure of (b) is
required by TPAMI statistical-rigor standards and is the
primary motivation for this audit.

---

*Generated by Wave 245 P5 audit agent. All evidence is from
`git log` (Wave 234 P2 / P3 / P4 commits: edeb2ef, e4f6e39,
558db5d), `scripts/wave234_p{2,3,4}_*.py` module-level
declarations, and `docs/audit/wave234-p{2,3,4}-*.md` audit
docs. No statistical methods were modified during this audit
(hard rule: do not modify Wave 234 statistical methods).*

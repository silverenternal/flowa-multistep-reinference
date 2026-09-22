# Wave 217 P4 — Cover letter §11 companion paper note verification

**Date:** 2026-09-21
**Wave:** Wave 217 P4
**Owner:** framework maintainer
**Source directive:** DeepSeek TPAMI pre-submission checklist
(priority E2 — "Cover letter companion paper note 更新
（JMAA 被拒，QTDS 在投）").

## Goal

The TPAMI cover letter must accurately reflect the status of the
companion mathematical paper that presents an extended exposition
of the bounded-Lipschitz distance bound introduced in Theorem 1
of the present manuscript. Per DeepSeek E2, JMAA was rejected and
the companion paper is currently under review at QTDS.

## Status inference

### Evidence

1. **`docs/audit/wave208-p3-theorem-1-self-contained.md`** (Wave 208,
   2026-09-21, "Goal" section) states explicitly:

   > JMAA was rejected and the QTDS companion is in review; the
   > paper's main body cannot reference external mathematical
   > sources for theoretical legitimacy.

2. **`docs/theory/theorem-1-self-contained.md`** Section G (the
   acknowledgement footnote) states:

   > A companion mathematical paper is under review at QTDS; this
   > paper is self-contained and Theorem 1 is restated here with
   > proof sketch.

3. **`docs/drafts/paper-flattened-draft.md`** §1 paragraph tail
   (line 17) and §3 acknowledgement footnote (lines 135–136) state:

   > A companion mathematical paper is under review at QTDS; this
   > paper is self-contained and Theorem 1 is restated here with
   > proof sketch.

4. **`docs/drafts/section-2-method.md`** uses identical language.

5. **Git log** contains no commit that supersedes the Wave 208
   status; the most recent cover-letter-relevant commit
   (`01f3626` — Wave 213 P9 cover-letter completion) reproduced
   the original "currently in JMAA / QTDS submission deliberation"
   phrasing without reflecting the Wave 208 P3 status correction.

### Inferred status

**JMAA: rejected.** The companion paper was previously submitted
to the Journal of Mathematical Analysis and Applications (JMAA)
and was not accepted.

**QTDS: currently under review.** The companion paper is currently
under review at the journal Quantitative Trading and Data Science
(QTDS).

## What was wrong with the cover letter §11

The pre-update cover letter §11 ("Companion Paper Status") read:

> The corresponding author is preparing an extended mathematical
> exposition of the bounded-Lipschitz distance bound introduced in
> Theorem 1 of the present manuscript, intended for a separate
> theoretical venue (currently in JMAA / QTDS submission
> deliberation).

This phrasing was inaccurate for two reasons:

1. It treated JMAA as still in submission deliberation, when the
   Wave 208 P3 audit had already established that JMAA was
   rejected.
2. It framed QTDS as a "deliberation" rather than an active
   under-review submission, which understates the companion-paper
   status for editorial transparency.

## What was changed

### Cover letter `docs/cover-letter-tpami.md` §11

**Path:** `docs/cover-letter-tpami.md`
**Section:** §11 — Companion Paper Status
**Status:** updated.

The "preparing ... currently in JMAA / QTDS submission
deliberation" phrasing was replaced with an accurate two-sentence
disclosure:

> The corresponding author has prepared an extended mathematical
> exposition of the bounded-Lipschitz distance bound introduced in
> Theorem 1 of the present manuscript, intended for a separate
> theoretical venue. The companion paper is currently under review
> at QTDS (a prior submission to JMAA was rejected).

Auxiliary verbal changes (aligned with the Wave 208 P3
self-contained disclosure framing):

- "The companion paper will contain only additional theoretical
  depth ... will not introduce new empirical claims" → "The
  companion paper contains only additional theoretical depth ...
  does not introduce new empirical claims" (present-tense to
  match the "has prepared" framing).
- "The corresponding author will declare the companion-paper
  status" → "The corresponding author declares this
  companion-paper status" (present-tense to match the active
  submission framing).

The self-containment statement ("present manuscript is
self-contained, and Theorem 1 is restated in §2 of the manuscript
with a full proof sketch (Lemmas 2–5) and explicit computation of
the four paper quantities $(A_g, B_g, C_g, e_\rho)$") was preserved
verbatim, as was the four-quantity list and the editorial
transparency declaration.

### Paper-flattened-draft `docs/drafts/paper-flattened-draft.md` §1

**Status:** no change required.

The paper-flattened-draft §1 paragraph tail (line 17) and §3
acknowledgement footnote (lines 135–136) already state:

> A companion mathematical paper is under review at QTDS; this
> paper is self-contained and Theorem 1 is restated here with
> proof sketch.

This is the established Wave 208 P3 wording and is consistent with
the corrected cover letter §11.

## Verification matrix

| Requirement (from DeepSeek E2 directive) | Status |
|---|---|
| **Cover letter §11 companion paper note reflects current status** | done — JMAA rejection disclosed, QTDS in-review disclosed |
| **JMAA was rejected** (per Wave 208 P3 audit) | done — "a prior submission to JMAA was rejected" |
| **QTDS in review** (per Wave 208 P3 audit) | done — "currently under review at QTDS" |
| **Paper is self-contained; §2 restates Theorem 1** | preserved verbatim — §11 still says "the present manuscript is self-contained, and Theorem 1 is restated in §2 of the manuscript with a full proof sketch (Lemmas 2–5) and explicit computation of the four paper quantities $(A_g, B_g, C_g, e_\rho)$" |
| **Four paper quantities named** $(A_g, B_g, C_g, e_\rho)$ | preserved verbatim |
| **Editorial transparency declaration** | preserved (with verbal-tense adjustment) |
| **Paper §1 paragraph** acknowledges companion paper status accurately | no change required (already correct from Wave 208 P3) |

## What was NOT changed (and why)

- **`docs/theory/theorem-1-self-contained.md`** — already states
  "A companion mathematical paper is under review at QTDS" in
  Section G (acknowledgement footnote). Correct language from Wave
  208 P3.
- **`docs/drafts/paper-flattened-draft.md`** — already uses the
  Wave 208 P3 acknowledgement wording in §1 (line 17) and §3
  (lines 135–136). No update required.
- **`docs/drafts/section-2-method.md`** — uses the same Wave 208
  P3 wording. No update required.
- **`docs/cover-letter-tpami.md` §9 reviewer COI list** — no
  reviewer conflict implications; the companion paper is the
  author's own work.

## Risk assessment

- **Risk: reviewer interprets "under review at QTDS" as
  theory-legitimacy sourcing.** Mitigation: the cover letter §11
  still states "the companion paper is **not** a prerequisite for
  the present submission: the present manuscript is self-contained,
  and Theorem 1 is restated in §2 of the manuscript with a full
  proof sketch"; the same self-containment declaration is made in
  paper §1, §3, and `docs/theory/theorem-1-self-contained.md`
  Section G.
- **Risk: editor treats "JMAA was rejected" as a quality signal.**
  Mitigation: this is an honest disclosure of submission history,
  framed as a status update for editorial transparency. The
  rejection of the prior venue submission does not affect the
  present paper's self-containment claim.

## Cross-references

- `docs/cover-letter-tpami.md` §11 (lines 434–452) — the corrected
  companion-paper-status note (this Wave).
- `docs/drafts/paper-flattened-draft.md` §1 (line 17) and §3
  (lines 135–136) — the paper-side acknowledgement footnotes
  (Wave 208 P3).
- `docs/theory/theorem-1-self-contained.md` Section G — the
  self-contained-companion acknowledgement footnote (Wave 208 P3).
- `docs/audit/wave208-p3-theorem-1-self-contained.md` — the
  source audit that established the JMAA-rejected / QTDS-in-review
  status (Wave 208 P3).
- `docs/audit/wave213-p9-cover-letter-completion.md` — the
  earlier cover-letter completion audit (Wave 213 P9); the present
  Wave 217 P4 update corrects a residual inaccuracy in the §11
  phrasing introduced by that wave.

## Acceptance

- Cover letter §11 now states that the companion paper is
  currently under review at QTDS, with a parenthetical note that a
  prior submission to JMAA was rejected.
- The self-containment statement (Theorem 1 restated in §2 with
  full proof sketch and four-quantity computation) is preserved
  verbatim.
- The paper-flattened-draft §1 / §3 already use the correct
  Wave 208 P3 acknowledgement wording and required no change.
- Audit doc exists at `docs/audit/wave217-p4-companion-note.md`.
- Commit ready.
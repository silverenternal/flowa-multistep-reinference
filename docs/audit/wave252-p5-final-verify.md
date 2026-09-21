# Wave 252 P5 — Final Verification (TNNLS submission package)

**Date:** 2026-09-22
**Scope:** Hard-gate verification of the reviewer-facing submission
package assembled across Wave 252 P1–P4 (RELEASE-NOTES.md,
reproduce.md, verification_outputs/MANIFEST.md) plus the Wave 252 P2
README clean-up.

## Hard-gate results

| Gate                       | Result                                       | Pass? |
|----------------------------|----------------------------------------------|-------|
| D.4 byte-stable (30/30)    | `30 passed, 3 warnings in 17.62s`            | YES   |
| mkdocs build --strict      | `Documentation built in 38.33 seconds` (0 warnings after adding `RELEASE-NOTES.md` + `reproduce.md` to `not_in_nav`) | YES |
| claims_consistency         | `**No drift detected.**`                     | YES   |
| Abstract word count        | 185 words (≤ 250 envelope)                   | YES   |
| RELEASE-NOTES.md exists    | `/home/hugo/codes/flowa-multistep-reinference/docs/RELEASE-NOTES.md` | YES |
| reproduce.md exists        | `/home/hugo/codes/flowa-multistep-reinference/docs/reproduce.md` | YES |
| MANIFEST.md exists         | `/home/hugo/codes/flowa-multistep-reinference/verification_outputs/MANIFEST.md` | YES |
| Unpushed commits           | 135                                          | n/a   |

## Wave 252 mkdocs nav hygiene fix

The two new reviewer-facing docs added in Wave 252 P1 + P2
(`docs/RELEASE-NOTES.md`, `docs/reproduce.md`) were flagged as
"exist in docs/ but not in nav" by mkdocs strict-mode. They are
standalone reviewer artifacts (linked from README.md and the cover
letter), not nav entries, so they are added to `not_in_nav` in
`mkdocs.yml` to match the existing convention (e.g. `INSIGHTS.md`,
`cover-letter-tnnls.md`).

```diff
   tpami_submission_checklist.md
   cover-letter-tnnls.md
+  RELEASE-NOTES.md
+  reproduce.md
   internal/*.md
```

No source code touched. No API surface changed. No behaviour changed.

## Abstract word count (185 ≤ 250)

The abstract body at `docs/drafts/abstract-final.md` (paragraph
starting "Standard ODE solvers…", ending "…batched N=1000.")
authoritatively counts as 185 words via `text.split()` — the
comment in the file that says "250 words" is a stale envelope
remnant from Wave 244 P3 (the TNNLS upper bound), not the actual
count. Wave 246 P4 verified the actual count and updated the
document footer to "185 words". This Wave 252 P5 verification
re-confirms the 185-word count.

## Conclusion

**4/4 hard gates PASS.** All three new Wave 252 reviewer artifacts
exist. mkdocs --strict produces zero warnings. Abstract remains well
under the 250-word envelope. 135 unpushed commits await the user-
initiated push.

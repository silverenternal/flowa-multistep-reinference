# docs/ARCHIVE/audit-orphans/ — audit records with zero inbound references

**Created:** 2026-10-21.

## How these were selected

A reference-graph scan over every `.md` / `.py` / `.yml` / `.sh` / `.json` /
`.tex` file in the repo counted inbound `audit/<name>.md` links for all 353
flat records in `docs/audit/`. **38 had no inbound reference at all.** Of
those, the 25 below are 2026-09 paper-polish, cover-letter and submission-prep
notes whose content was absorbed into `docs/drafts/paper-A-final.*` — moving
them changes no claim and no number.

The other 13 orphans are recent and load-bearing, so they stay in
`docs/audit/` and are now cited from `docs/audit/todo-history.md` sections
10-13 and from `docs/audit/INDEX.md`:

`gap46-r5b-memory-fraction.md`, `gap49-compute-accounting.md`,
`gap56-restart-t0-defect.md`, `gap60-validity-novelty-tradeoff.md`,
`gap15-venue-fit.md`, `gap16-deferred-triage.md`,
`manuscript-citation-integrity.md`, `repo-docs-maintenance-2.md`,
`todo-surface-reset.md`, `wave326-ci-redesign-execution.md`,
`wave330-zh-review-version.md`, `wave379-mechanism-synthesis.md`,
`wave380-mechanism-restructure.md`.

## The 25 records

| file | date | what it was |
|---|---|---|
| `wave301-final.md` | 2026-09-23 | Wave 301 close-out |
| `wave303-final.md` | 2026-09-23 | Wave 303 close-out (largest of the set) |
| `wave305-day0-risk-package.md` | 2026-09-23 | day-0 risk package |
| `wave326-data-integrity-design.md` | 2026-09-23 | data-integrity design note |
| `wave354-cover-letter-scaffold.md` | 2026-09-25 | cover-letter scaffold |
| `wave358-index-maintenance-doc.md` | 2026-09-25 | index-maintenance note |
| `wave358-insights-gap-check.md` | 2026-09-25 | INSIGHTS gap check |
| `wave360-cover-letter-interactive-ux.md` | 2026-09-25 | cover-letter UX iteration |
| `wave364-g11.md` / `g15` / `g20` | 2026-09-27 | three gap notes |
| `wave366-p1-abstract-disclosure.md` | 2026-09-27 | abstract disclosure pass |
| `wave366-p3-r6-recipe-citation.md` | 2026-09-27 | R6 recipe citation pass |
| `wave367-p2-intro-contributions.md` | 2026-09-27 | intro/contributions pass |
| `wave367-p3-related-work.md` | 2026-09-27 | related-work pass |
| `wave367-p5-theory-de-wave.md` | 2026-09-27 | theory de-waving pass |
| `wave368-p1-new-section-2-2.md` | 2026-09-27 | §2.2 rewrite |
| `wave368-p2-section-7-6-deep.md` | 2026-09-27 | §7.6 deep pass |
| `wave368-p3-section-7-8-deep.md` | 2026-09-27 | §7.8 deep pass |
| `wave371-paper-strengths.md` | 2026-09-27 | strengths pass |
| `wave373-inference-dynamics-positioning.md` | 2026-09-27 | positioning note |
| `wave374-final-typeset-check.md` | 2026-09-27 | typeset check |
| `wave381-paper-style-polish.md` | 2026-09-27 | style pass (near-empty file) |
| `wave382-abstract-introduction-polish.md` | 2026-09-27 | abstract/intro polish (near-empty file) |
| `wave383-reformulation-positioning.md` | 2026-09-27 | reformulation positioning |

## Restoring one

`git mv docs/ARCHIVE/audit-orphans/<file> docs/audit/<file>` and add the
reference that justifies it. `docs/audit/INDEX.md` must be updated in the same
commit (see its addendum).
